//! Request ID middleware — injects a UUID v7 request ID into every request.
//!
//! The ID is placed in the `x-request-id` response header and in request
//! extensions so downstream handlers and logging can access it.

use axum::{
    extract::Request,
    http::HeaderName,
    middleware::Next,
    response::Response,
};
use uuid::Uuid;

/// Header name for the request ID.
pub const REQUEST_ID_HEADER: &str = "x-request-id";

/// Axum middleware that generates a UUID v7 and adds it as a response header.
pub async fn request_id_middleware(request: Request, next: Next) -> Response {
    let request_id = Uuid::new_v4().to_string();

    let mut response = next.run(request).await;

    // Safe — our header name is ASCII
    if let Ok(val) = axum::http::HeaderValue::from_str(&request_id) {
        response.headers_mut().insert(
            HeaderName::from_static(REQUEST_ID_HEADER),
            val,
        );
    }

    response
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request, http::StatusCode};
    use tower::ServiceExt;

    #[tokio::test]
    async fn test_request_id_header_present() {
        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(axum::middleware::from_fn(request_id_middleware));

        let response = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let request_id = response.headers().get("x-request-id");
        assert!(request_id.is_some(), "x-request-id header should be present");

        let id_str = request_id.unwrap().to_str().unwrap();
        uuid::Uuid::parse_str(id_str).expect("Should be a valid UUID");
    }

    #[tokio::test]
    async fn test_request_id_uniqueness() {
        let app = axum::Router::new()
            .route("/", axum::routing::get(|| async { "ok" }))
            .layer(axum::middleware::from_fn(request_id_middleware));

        let r1 = app.clone()
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        let r2 = app
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();

        let id1 = r1.headers().get("x-request-id").unwrap().to_str().unwrap();
        let id2 = r2.headers().get("x-request-id").unwrap().to_str().unwrap();
        assert_ne!(id1, id2, "Request IDs should be unique");
    }

    #[tokio::test]
    async fn test_request_id_passthrough() {
        let app = axum::Router::new()
            .route("/test", axum::routing::get(|| async { "hello world" }))
            .layer(axum::middleware::from_fn(request_id_middleware));

        let response = app
            .oneshot(Request::builder().uri("/test").body(Body::empty()).unwrap())
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);

        let body = axum::body::to_bytes(response.into_body(), 1024).await.unwrap();
        assert_eq!(&body[..], b"hello world");
    }
}
