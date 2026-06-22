//! HTTP request metrics middleware — collects counters for the Prometheus
//! `/api/v1/metrics` endpoint.
//!
//! All counters use [`std::sync::atomic::AtomicU64`] for lock-free, wait-free
//! updates from any thread.  No external metrics crate required.

use axum::{extract::Request, middleware::Next, response::Response};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

// ---------------------------------------------------------------------------
// Global atomic counters — exposed to the metrics endpoint
// ---------------------------------------------------------------------------

/// Total number of HTTP requests received (including those that errored).
pub static REQUESTS_TOTAL: AtomicU64 = AtomicU64::new(0);

/// Number of HTTP requests currently being processed.
pub static REQUESTS_IN_FLIGHT: AtomicU64 = AtomicU64::new(0);

/// Number of 2xx (OK) responses.
pub static RESPONSES_2XX: AtomicU64 = AtomicU64::new(0);

/// Number of 3xx (redirect) responses.
pub static RESPONSES_3XX: AtomicU64 = AtomicU64::new(0);

/// Number of 4xx (client error) responses.
pub static RESPONSES_4XX: AtomicU64 = AtomicU64::new(0);

/// Number of 5xx (server error) responses.
pub static RESPONSES_5XX: AtomicU64 = AtomicU64::new(0);

/// Cumulative request duration in microseconds.
pub static REQUEST_DURATION_MICROS_SUM: AtomicU64 = AtomicU64::new(0);

/// Number of requests that contributed to the duration sum.
pub static REQUEST_DURATION_COUNT: AtomicU64 = AtomicU64::new(0);

// ---------------------------------------------------------------------------
// Uptime tracking
// ---------------------------------------------------------------------------

/// Server start instant — set once by `record_start_time()` at boot.
static START_INSTANT: std::sync::OnceLock<Instant> = std::sync::OnceLock::new();

/// Record the server start time.  Call once in `main()` / `build_router()`.
pub fn record_start_time() {
    let _ = START_INSTANT.set(Instant::now());
}

/// Server uptime in seconds (fractional).
pub fn uptime_seconds() -> f64 {
    START_INSTANT
        .get()
        .map(|t| t.elapsed().as_secs_f64())
        .unwrap_or(0.0)
}

/// Approximate Unix timestamp of server start.
pub fn start_time_secs() -> i64 {
    START_INSTANT
        .get()
        .and_then(|start| {
            std::time::UNIX_EPOCH
                .elapsed()
                .ok()
                .map(|since_epoch| since_epoch.as_secs() as i64 - start.elapsed().as_secs() as i64)
        })
        .unwrap_or(0)
}

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

/// Axum middleware that records per-request metrics.
///
/// Tracks: total requests, in-flight count, response status class, and
/// request duration.  All counters are updated with [`Ordering::Relaxed`]
/// for minimal overhead — metrics consumers accept eventual consistency.
pub async fn metrics_middleware(request: Request, next: Next) -> Response {
    REQUESTS_TOTAL.fetch_add(1, Ordering::Relaxed);
    REQUESTS_IN_FLIGHT.fetch_add(1, Ordering::Relaxed);

    let start = Instant::now();
    let response = next.run(request).await;
    let duration_us = start.elapsed().as_micros() as u64;

    REQUEST_DURATION_MICROS_SUM.fetch_add(duration_us, Ordering::Relaxed);
    REQUEST_DURATION_COUNT.fetch_add(1, Ordering::Relaxed);
    REQUESTS_IN_FLIGHT.fetch_sub(1, Ordering::Relaxed);

    let status = response.status().as_u16();
    match status {
        200..=299 => { RESPONSES_2XX.fetch_add(1, Ordering::Relaxed); }
        300..=399 => { RESPONSES_3XX.fetch_add(1, Ordering::Relaxed); }
        400..=499 => { RESPONSES_4XX.fetch_add(1, Ordering::Relaxed); }
        _ => { RESPONSES_5XX.fetch_add(1, Ordering::Relaxed); }
    }

    response
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_metrics_counters_increment() {
        let before_total = REQUESTS_TOTAL.load(Ordering::Relaxed);
        let before_2xx = RESPONSES_2XX.load(Ordering::Relaxed);

        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(axum::middleware::from_fn(metrics_middleware));

        let _response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let after_total = REQUESTS_TOTAL.load(Ordering::Relaxed);
        let after_2xx = RESPONSES_2XX.load(Ordering::Relaxed);

        assert!(after_total > before_total, "REQUESTS_TOTAL should increment");
        assert!(after_2xx > before_2xx, "RESPONSES_2XX should increment");
    }

    #[tokio::test]
    async fn test_metrics_4xx_counted() {
        let before_4xx = RESPONSES_4XX.load(Ordering::Relaxed);

        let app = axum::Router::new()
            .route(
                "/",
                axum::routing::get(|| async { axum::http::StatusCode::NOT_FOUND }),
            )
            .layer(axum::middleware::from_fn(metrics_middleware));

        let _response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let after_4xx = RESPONSES_4XX.load(Ordering::Relaxed);
        assert!(after_4xx > before_4xx, "RESPONSES_4XX should increment");
    }

    #[tokio::test]
    async fn test_uptime_recording() {
        record_start_time();
        let uptime = uptime_seconds();
        assert!(uptime >= 0.0, "Uptime should be non-negative");
        let start_time = start_time_secs();
        assert!(start_time > 0, "Start time should be positive");
    }
}
