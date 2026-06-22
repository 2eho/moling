//! 墨灵 (Moling) — Logging / tracing initialization.
//!
//! Startup sequence:
//! 1. Configure tracing subscriber (fmt layer: pretty or JSON)
//! 2. If ``SENTRY_DSN`` is set, initialise Sentry + tracing integration
//! 3. If ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, add OTLP export layer
//!
//! All integrations are controlled by environment variables and default to
//! disabled — no-op when the corresponding env var is unset.

use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::EnvFilter;
use opentelemetry::trace::TracerProvider as _;

/// Sentry guard — must be kept alive for the lifetime of the process.
///
/// Dropping this guard shuts down the Sentry SDK and flushes pending events.
/// Store it in a static or pass it to the server main.
pub struct SentryGuard {
    inner: Option<sentry::ClientInitGuard>,
}

impl SentryGuard {
    /// Returns `Some(guard)` if Sentry is configured, `None` otherwise.
    pub fn new() -> Self {
        let dsn = match std::env::var("SENTRY_DSN") {
            Ok(v) if !v.is_empty() => v,
            _ => {
                tracing::info!("Sentry disabled (SENTRY_DSN not set)");
                return Self { inner: None };
            }
        };

        let environment = std::env::var("SENTRY_ENVIRONMENT")
            .unwrap_or_else(|_| {
                std::env::var("ENVIRONMENT")
                    .unwrap_or_else(|_| "development".to_string())
            });

        let release = std::env::var("SENTRY_RELEASE")
            .unwrap_or_else(|_| format!("moling@{}", env!("CARGO_PKG_VERSION")));

        // traces_sample_rate: 0.2 in production, 1.0 in dev
        let traces_sample_rate: f32 = if environment == "production" { 0.2 } else { 1.0 };

        let guard = sentry::init(sentry::ClientOptions {
            dsn: Some(dsn.parse().expect("Invalid SENTRY_DSN")),
            environment: Some(environment.into()),
            release: Some(release.into()),
            traces_sample_rate,
            ..Default::default()
        });

        tracing::info!(
            traces_sample_rate,
            sentry_enabled = true,
            "Sentry initialised"
        );

        Self { inner: Some(guard) }
    }
}

impl Default for SentryGuard {
    fn default() -> Self {
        Self::new()
    }
}

/// Initialize the tracing/logging system with optional Sentry and OTel layers.
/// Called once at application startup.
///
/// Layers (innermost → outermost):
/// - `tracing-fmt` (pretty or JSON, to stdout)
/// - `tracing-opentelemetry` (if ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set)
/// - `tracing-sentry` (if ``SENTRY_DSN`` is set)
///
/// Respects:
/// - ``RUST_LOG`` env var (default "info")
/// - ``MOLING_LOG_FORMAT`` env var ("pretty" | "json", default "pretty")
///
/// Returns a [`SentryGuard`] that must be kept alive — dropping it flushes and
/// shuts down Sentry.
pub fn init_tracing() -> SentryGuard {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info"));

    let log_format = std::env::var("MOLING_LOG_FORMAT")
        .unwrap_or_else(|_| "pretty".to_string());

    let sentry_guard = SentryGuard::new();

    // Pre-build OTel provider (independent of subscriber type S)
    let otel_provider = OtelProvider::new();

    // Layer factories — called per-branch for fresh concrete types
    let json_fmt = || {
        tracing_subscriber::fmt::layer()
            .json()
            .with_target(true)
            .with_file(true)
            .with_line_number(true)
    };
    let pretty_fmt = || {
        tracing_subscriber::fmt::layer()
            .with_target(true)
            .with_file(true)
            .with_line_number(true)
    };

    // Router: 2 (fmt) × 2 (otel) = 4 leaf branches.
    // Sentry is integrated via client auto-hook, not as a tracing layer
    // (avoids impl-Layer + SentryLayer type composition issues).
    let registry = tracing_subscriber::registry();

    if log_format == "json" {
        if let Some(ref otel) = otel_provider {
            registry
                .with(env_filter)
                .with(json_fmt())
                .with(otel.make_layer())
                .init();
        } else {
            registry
                .with(env_filter)
                .with(json_fmt())
                .init();
        }
    } else {
        if let Some(ref otel) = otel_provider {
            registry
                .with(env_filter)
                .with(pretty_fmt())
                .with(otel.make_layer())
                .init();
        } else {
            registry
                .with(env_filter)
                .with(pretty_fmt())
                .init();
        }
    }

    tracing::info!(
        format = %log_format,
        sentry = sentry_guard.inner.is_some(),
        otel = otel_provider.is_some(),
        "Moling tracing initialised"
    );

    sentry_guard
}

// ---------------------------------------------------------------------------
// OpenTelemetry helpers
// ---------------------------------------------------------------------------

/// Pre-built OTel provider — created once, reused across subscriber arms.
///
/// Provider creation (exporter + tracer) is independent of the subscriber
/// type `S`.  The layer for a specific subscriber type is built on demand
/// via [`make_layer`].
struct OtelProvider {
    /// Kept alive for the process lifetime.
    _provider: opentelemetry_sdk::trace::TracerProvider,
    tracer: opentelemetry_sdk::trace::Tracer,
}

impl OtelProvider {
    fn new() -> Option<Self> {
        let endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").ok()?;
        if endpoint.is_empty() {
            return None;
        }

        let service_name = std::env::var("OTEL_SERVICE_NAME")
            .unwrap_or_else(|_| "moling-server-rs".to_string());

        let result = (|| -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
            use opentelemetry::KeyValue;
            use opentelemetry_sdk::Resource;
            use opentelemetry_otlp::WithExportConfig;

            let exporter = opentelemetry_otlp::SpanExporter::builder()
                .with_http()
                .with_endpoint(&endpoint)
                .build()?;

            let provider = opentelemetry_sdk::trace::TracerProvider::builder()
                .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
                .with_resource(Resource::new([KeyValue::new(
                    "service.name",
                    service_name,
                )]))
                .build();

            let tracer = provider.tracer("moling");

            Ok(Self {
                _provider: provider,
                tracer,
            })
        })();

        match result {
            Ok(this) => {
                tracing::info!(
                    otel_endpoint = %endpoint,
                    "OpenTelemetry OTLP export enabled"
                );
                Some(this)
            }
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    "Failed to initialise OpenTelemetry — tracing continues without OTLP"
                );
                None
            }
        }
    }

    /// Build a tracing layer for subscriber type `S`.
    ///
    /// Each match arm in `init_tracing` has a different concrete subscriber
    /// type; calling this method in each arm produces the correct
    /// `OpenTelemetryLayer<S>` for that arm.
    fn make_layer<S>(&self) -> impl tracing_subscriber::layer::Layer<S> + Send + Sync
    where
        S: tracing::Subscriber
            + for<'span> tracing_subscriber::registry::LookupSpan<'span>
            + Send
            + Sync
            + 'static,
    {
        tracing_opentelemetry::layer().with_tracer(self.tracer.clone())
    }
}
