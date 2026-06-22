//! Error-capture middleware — integrates Sentry SDK with tracing pipeline.
//!
//! When a 5xx response is produced by any downstream handler, this middleware:
//! 1. Emits a ``tracing::error!`` event (picked up by ``tracing-sentry`` layer)
//! 2. Captures the event directly via the Sentry SDK when active
//!
//! # Configuration
//!
//! | Env var              | Description                | Default          |
//! |----------------------|----------------------------|------------------|
//! | ``SENTRY_DSN``       | Sentry project DSN         | (disabled)       |
//! | ``SENTRY_ENVIRONMENT``| Environment tag           | ``ENVIRONMENT``  |
//! | ``SENTRY_RELEASE``    | Release version           | ``moling@ver``   |
//!
//! # Usage
//!
//! The middleware is added via ``build_router()``.  Sentry is initialised
//! in ``moling_core::logging::init_tracing()`` — this middleware only needs
//! to attach per-request context.

use axum::{extract::Request, middleware::Next, response::Response};

/// Middleware that captures 5xx server errors with request context.
///
/// Runs **after** all handler logic — inspects the response status and emits
/// a structured error event with method, URI, and status.
/// The ``tracing-sentry`` layer forwards these events to Sentry when enabled.
pub async fn sentry_middleware(request: Request, next: Next) -> Response {
    let method = request.method().clone();
    let uri = request.uri().clone();
    let request_id = request
        .headers()
        .get("x-request-id")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();

    // Add a breadcrumb for this request (no-op if Sentry is not configured)
    sentry::add_breadcrumb(sentry::Breadcrumb {
        ty: "http".into(),
        category: Some("request".into()),
        message: Some(format!("{} {}", method, uri)),
        data: {
            let mut map = sentry::protocol::Map::new();
            if !request_id.is_empty() {
                map.insert(
                    "request_id".into(),
                    sentry::protocol::Value::String(request_id.clone()),
                );
            }
            map
        },
        ..Default::default()
    });

    let response = next.run(request).await;

    let status = response.status();
    if status.is_server_error() {
        tracing::error!(
            method = %method,
            uri = %uri,
            status = status.as_u16(),
            request_id = %request_id,
            "HTTP server error — captured by sentry middleware",
        );

        // Direct Sentry SDK capture (no-op if Sentry is not initialised)
        sentry::capture_message(
            &format!(
                "5xx server error: {} {} → {} (request_id={})",
                method,
                uri,
                status.as_u16(),
                request_id,
            ),
            sentry::Level::Error,
        );
    }

    response
}
