//! CORS middleware — configurable cross-origin resource sharing.
//!
//! Wraps [`tower_http::cors::CorsLayer`] with settings from the application
//! configuration. Default allows all origins in development.

use tower_http::cors::{AllowHeaders, AllowOrigin, CorsLayer};

/// Build a [`CorsLayer`] from the given allowed origins string.
///
/// The `origins` parameter can be `"*"` (allow all via mirroring) or a
/// comma-separated list of allowed origins.
///
/// Uses [`AllowOrigin::mirror_request`] for `"*"` to support requests
/// with `credentials: "include"` (CORS spec forbids `*` with credentials).
pub fn cors_middleware(origins: &str) -> CorsLayer {
    let allow_origin = if origins == "*" {
        AllowOrigin::mirror_request()
    } else {
        let origins_vec: Vec<_> = origins
            .split(',')
            .map(|s| s.trim().to_owned())
            .filter(|s| !s.is_empty())
            .collect();
        if origins_vec.is_empty() || origins_vec.iter().any(|o| o == "*") {
            AllowOrigin::mirror_request()
        } else {
            AllowOrigin::list(origins_vec.into_iter().filter_map(|o| {
                o.parse::<axum::http::HeaderValue>().ok()
            }))
        }
    };

    CorsLayer::new()
        .allow_origin(allow_origin)
        .allow_methods([
            axum::http::Method::GET,
            axum::http::Method::POST,
            axum::http::Method::PUT,
            axum::http::Method::PATCH,
            axum::http::Method::DELETE,
            axum::http::Method::OPTIONS,
        ])
        .allow_headers(AllowHeaders::mirror_request())
        .allow_credentials(true)
}
