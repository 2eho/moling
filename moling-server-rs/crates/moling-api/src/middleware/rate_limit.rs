//! Rate limiting middleware — sliding-window counter via Redis ZSET + Lua.
//!
//! When Redis is unavailable the middleware allows all requests through
//! (graceful degradation).  Rate-limit configuration is read from
//! [`moling_core::config::Settings`] (environment variables
//! `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECS` or the `MOLING_`-prefixed
//! equivalents).

use axum::{
    extract::{Request, State},
    middleware::Next,
    response::Response,
};
use moling_core::error::AppError;
use moling_core::rate_limiter::{RateLimiter, RedisRateLimiter};

use crate::state::AppState;

/// Extract the client IP from the request.
///
/// Prefers `x-forwarded-for` header (taking the first IP in the chain),
/// falls back to the socket address, and ultimately to `127.0.0.1`.
fn extract_client_ip(request: &Request) -> String {
    // Prefer x-forwarded-for header (reverse-proxy / load-balancer)
    if let Some(fwd) = request
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
    {
        // Take the first IP in the chain (client origin)
        if let Some(ip) = fwd.split(',').next() {
            let ip = ip.trim();
            if !ip.is_empty() {
                return ip.to_owned();
            }
        }
    }

    // Fallback: use the socket address if available
    request
        .extensions()
        .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
        .map(|ci| ci.0.ip().to_string())
        .unwrap_or_else(|| "127.0.0.1".into())
}

/// Sliding-window rate limiter middleware — Redis-backed for multi-worker
/// deployments.
///
/// Uses a Lua script executed atomically inside Redis (ZSET-based sliding
/// window).  Configuration is read from [`AppState::settings`]:
///
/// | Setting | Env var | Default |
/// |---------|---------|---------|
/// | `rate_limit_requests` | `RATE_LIMIT_REQUESTS` / `MOLING_RATE_LIMIT_REQUESTS` | 100 |
/// | `rate_limit_window_secs` | `RATE_LIMIT_WINDOW_SECS` / `MOLING_RATE_LIMIT_WINDOW_SECS` | 60 |
///
/// # Fallback
///
/// If Redis is unavailable, the request is allowed through — we never block
/// legitimate traffic because of an infrastructure issue.
///
/// # Metrics
///
/// On every check the middleware increments either
/// [`super::metrics::RATE_LIMIT_ALLOWED_TOTAL`] or
/// [`super::metrics::RATE_LIMIT_BLOCKED_TOTAL`].
pub async fn rate_limit_middleware(
    State(state): State<AppState>,
    request: Request,
    next: Next,
) -> Result<Response, AppError> {
    let limiter = RedisRateLimiter::new(state.redis.clone());
    let client_ip = extract_client_ip(&request);
    let key = format!("rate_limit:{client_ip}");

    let max_requests = state.settings.rate_limit_requests;
    let window_secs = state.settings.rate_limit_window_secs;

    let result = limiter
        .check_rate_limit(&key, max_requests, window_secs)
        .await?;

    if result.allowed {
        super::metrics::increment_rate_limit_allowed();
        Ok(next.run(request).await)
    } else {
        super::metrics::increment_rate_limit_blocked();
        Err(AppError::rate_limit())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};

    #[test]
    fn test_extract_client_ip_from_forwarded_for() {
        let req = Request::builder()
            .uri("/")
            .header("x-forwarded-for", "10.0.0.1, 10.0.0.2")
            .body(Body::empty())
            .unwrap();
        let ip = extract_client_ip(&req);
        assert_eq!(ip, "10.0.0.1");
    }

    #[test]
    fn test_extract_client_ip_single_forwarded_for() {
        let req = Request::builder()
            .uri("/")
            .header("x-forwarded-for", "203.0.113.42")
            .body(Body::empty())
            .unwrap();
        let ip = extract_client_ip(&req);
        assert_eq!(ip, "203.0.113.42");
    }

    #[test]
    fn test_extract_client_ip_fallback() {
        let req = Request::builder()
            .uri("/")
            .body(Body::empty())
            .unwrap();
        let ip = extract_client_ip(&req);
        // Should fall back to 127.0.0.1 when no headers/extensions present
        assert_eq!(ip, "127.0.0.1");
    }

    #[test]
    fn test_extract_client_ip_empty_forwarded_for() {
        let req = Request::builder()
            .uri("/")
            .header("x-forwarded-for", "")
            .body(Body::empty())
            .unwrap();
        let ip = extract_client_ip(&req);
        assert_eq!(ip, "127.0.0.1"); // falls back when empty
    }
}
