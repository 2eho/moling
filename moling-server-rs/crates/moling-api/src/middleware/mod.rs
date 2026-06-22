//! Middleware registry — assembles all middleware layers for the Axum app.
//!
//! The [`build_middleware_stack`] function returns a [`tower::ServiceBuilder`]
//! that wraps the router with all middleware in the correct order (outermost first).

use axum::Router;
use moling_core::redis::RedisClient;
use tower::ServiceBuilder;
use tower_http::trace::TraceLayer;
use std::sync::Arc;

pub mod audit_log;
pub mod content_length;
pub mod cors;
pub mod metrics;
pub mod rate_limit;
pub mod request_id;
pub mod response_format;
pub mod sentry;

/// Build the complete middleware stack.
///
/// Order (outermost → innermost):
/// 1. Request ID — UUID for every request
/// 2. Metrics — HTTP request counters & latency
/// 3. CORS — cross-origin headers
/// 4. Sentry — error capture (5xx logging)
/// 5. Audit log — request/response metadata
/// 6. Response format — timing + logging
/// 7. Content length — body size limit
/// 8. Rate limit — Redis-backed counter
/// 9. Trace — tower-http tracing
pub fn build_middleware_stack(
    router: Router,
    redis: Arc<RedisClient>,
) -> Router {
    let cors_layer = cors::cors_middleware("*");

    router
        .layer(
            ServiceBuilder::new()
                .layer(cors_layer)
                .layer(axum::middleware::from_fn(request_id::request_id_middleware))
                .layer(axum::middleware::from_fn(metrics::metrics_middleware))
                .layer(axum::middleware::from_fn(sentry::sentry_middleware))
                .layer(axum::middleware::from_fn(audit_log::audit_log_middleware))
                .layer(axum::middleware::from_fn(response_format::response_format_middleware))
                .layer(axum::middleware::from_fn(content_length::content_length_middleware))
                .layer(axum::middleware::from_fn_with_state(
                    redis,
                    rate_limit::rate_limit_middleware,
                ))
                .layer(TraceLayer::new_for_http())
                .into_inner(),
        )
}
