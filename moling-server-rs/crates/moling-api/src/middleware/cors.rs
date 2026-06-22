//! CORS middleware — configurable cross-origin resource sharing.
//!
//! Wraps [`tower_http::cors::CorsLayer`] with settings from the application
//! configuration. Default allows all origins in development.

use tower_http::cors::{AllowHeaders, AllowMethods, AllowOrigin, CorsLayer, ExposeHeaders};

/// Build a [`CorsLayer`] from the given allowed origins string.
///
/// The `origins` parameter can be `"*"` (allow all) or a comma-separated
/// list of allowed origins.
pub fn cors_middleware(origins: &str) -> CorsLayer {
    let allow_origin = if origins == "*" {
        AllowOrigin::any()
    } else {
        let origins_vec: Vec<_> = origins
            .split(',')
            .map(|s| s.trim().to_owned())
            .filter(|s| !s.is_empty())
            .collect();
        if origins_vec.is_empty() || origins_vec.iter().any(|o| o == "*") {
            AllowOrigin::any()
        } else {
            AllowOrigin::list(origins_vec.into_iter().map(|o| {
                o.parse::<axum::http::HeaderValue>().unwrap()
            }))
        }
    };

    CorsLayer::new()
        .allow_origin(allow_origin)
        .allow_methods(AllowMethods::any())
        .allow_headers(AllowHeaders::any())
        .expose_headers(ExposeHeaders::any())
}
