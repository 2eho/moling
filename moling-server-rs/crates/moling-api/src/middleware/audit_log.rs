//! Audit log middleware — logs request/response metadata.
//!
//! Captures method, path, status code, latency, and optionally a
//! truncated request body (up to 10 KB). Response bodies are not
//! read to avoid buffering overhead.

use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
};
use std::time::Instant;
use tracing::info;

/// Maximum request body bytes to capture for audit logging.
const MAX_BODY_LOG_BYTES: usize = 10_240; // 10 KB

/// Audit log middleware.
///
/// Logs structured JSON lines at INFO level with the following fields:
/// - `http.method`, `http.path`, `http.status_code`, `latency_ms`
/// - `http.request_body` (truncated to 10 KB)
pub async fn audit_log_middleware(request: Request, next: Next) -> Response {
    let method = request.method().to_string();
    let path = request.uri().path().to_owned();

    // Capture a truncated copy of the request body for logging
    let body_snippet = capture_body_snippet(&request);

    let start = Instant::now();
    let response = next.run(request).await;
    let latency_ms = start.elapsed().as_millis();

    let status = response.status().as_u16();

    info!(
        http.method = %method,
        http.path = %path,
        http.status_code = status,
        latency_ms = latency_ms,
        http.request_body = %body_snippet,
        "HTTP request"
    );

    response
}

/// Extract up to `MAX_BODY_LOG_BYTES` of the request body for audit logging.
///
/// Currently returns a placeholder — full body capture requires buffering
/// middleware ordering (`RequestBodyLimitLayer`).
fn capture_body_snippet(request: &Request) -> String {
    use axum::body::HttpBody;

    let body = request.body();
    if body.size_hint().lower() > MAX_BODY_LOG_BYTES as u64 {
        return format!("<body too large: >{} bytes>", body.size_hint().lower());
    }

    "<body capture deferred>".into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::{Request, StatusCode}};
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_audit_log_passthrough() {
        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(axum::middleware::from_fn(audit_log_middleware));

        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_audit_log_preserves_status() {
        let app = axum::Router::new()
            .route(
                "/created",
                axum::routing::post(|| async { (StatusCode::CREATED, "created") }),
            )
            .layer(axum::middleware::from_fn(audit_log_middleware));

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/created")
                    .body(Body::from("test data"))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::CREATED);
    }

    #[tokio::test]
    async fn test_audit_log_error_status() {
        let app = axum::Router::new()
            .route(
                "/error",
                axum::routing::get(|| async { (StatusCode::INTERNAL_SERVER_ERROR, "error") }),
            )
            .layer(axum::middleware::from_fn(audit_log_middleware));

        let response = app
            .oneshot(Request::builder().uri("/error").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }
}
