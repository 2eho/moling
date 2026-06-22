//! Response format middleware — adds standard JSON envelope.
//!
//! Wraps successful JSON responses in `{"data": ...}` to match the
//! Python API convention. Error responses (produced by [`AppError`])
//! are left untouched.

use axum::{
    extract::Request,
    middleware::Next,
    response::Response,
};
use std::time::Instant;
use tracing::info;

/// Middleware that logs response metadata and passes through the response
/// unchanged (the actual JSON envelope is applied at the handler level via
/// [`crate::types::ApiResponse`]).
pub async fn response_format_middleware(request: Request, next: Next) -> Response {
    let method = request.method().clone();
    let uri = request.uri().clone();
    let start = Instant::now();

    let response = next.run(request).await;

    let elapsed_ms = start.elapsed().as_millis();
    let status = response.status().as_u16();

    info!(
        method = %method,
        uri = %uri,
        status = status,
        duration_ms = elapsed_ms,
        "Request complete"
    );

    response
}
