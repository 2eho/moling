//! Global error handler — maps [`AppError`] to HTTP responses.
//!
//! [`AppError`] already implements [`axum::response::IntoResponse`] with
//! the correct JSON format matching the Python API. This module provides
//! a handler for any remaining unhandled errors that Axum may encounter.

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use moling_core::error::AppError;
use serde_json::json;

/// Convert an unhandled error into an Axum response.
///
/// If the error is already an [`AppError`], use its built-in response.
/// Otherwise, return a generic 500 Internal Server Error.
pub fn handle_error(err: axum::BoxError) -> Response {
    // Try to downcast to AppError
    if let Some(app_err) = err.downcast_ref::<AppError>() {
        // AppError already has IntoResponse — but we can't call it directly.
        // Reconstruct the error response.
        let status = app_err.code.http_status();
        let body = json!({
            "code": app_err.code,
            "message": app_err.message,
            "detail": app_err.detail,
        });
        (status, Json(body)).into_response()
    } else {
        tracing::error!(error = %err, "Unhandled internal error");
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": null
            })),
        )
            .into_response()
    }
}
