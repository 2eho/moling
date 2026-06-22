//! Content length middleware — enforces maximum request body size.
//!
//! Rejects requests whose `content-length` header exceeds the configured
//! maximum before the body is read.

use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
};
use moling_core::error::AppError;

/// Default maximum body size (10 MB).
pub const DEFAULT_MAX_BODY_SIZE: u64 = 10_485_760;

/// Configuration for content-length limiting.
#[derive(Clone)]
pub struct ContentLengthConfig {
    /// Maximum allowed request body size in bytes.
    pub max_size: u64,
}

impl Default for ContentLengthConfig {
    fn default() -> Self {
        Self {
            max_size: DEFAULT_MAX_BODY_SIZE,
        }
    }
}

/// Middleware that rejects requests exceeding the configured body size limit.
///
/// Checks the `Content-Length` header — if absent, the request is allowed
/// through (size will be checked by the streaming body reader later).
pub async fn content_length_middleware(request: Request, next: Next) -> Result<Response, AppError> {
    if let Some(len) = request
        .headers()
        .get("content-length")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.parse::<u64>().ok())
    {
        let config = ContentLengthConfig::default();
        if len > config.max_size {
            return Err(AppError::bad_request(format!(
                "请求体过大，最大允许 {} MB",
                config.max_size / 1_048_576
            )));
        }
    }

    Ok(next.run(request).await)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::{Request, StatusCode}};
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_allows_normal_request() {
        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(axum::middleware::from_fn(content_length_middleware));

        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_rejects_oversized_content_length() {
        let app = axum::Router::new()
            .route("/", axum::routing::post(|| async { "ok" }))
            .layer(axum::middleware::from_fn(content_length_middleware));

        let huge_body = vec![0u8; 20_000_000]; // 20 MB > 10 MB limit
        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/")
                    .header("content-length", "20000000")
                    .body(Body::from(huge_body))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_allows_missing_content_length() {
        let app = axum::Router::new()
            .route("/", axum::routing::post(|| async { "ok" }))
            .layer(axum::middleware::from_fn(content_length_middleware));

        let response = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/")
                    .body(Body::from("small body"))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }
}
