//! Rate limiting middleware — sliding-window counter via Redis.
//!
//! When Redis is unavailable the middleware allows all requests through
//! (graceful degradation).  Rate-limit configuration is read from the
//! [`RateLimitConfig`] struct rather than hard-coded.

use axum::{
    extract::{Request, State},
    middleware::Next,
    response::Response,
};
use moling_core::error::AppError;
use moling_core::redis::RedisClient;
use std::sync::Arc;

/// Configuration for the rate limiter.
#[derive(Clone)]
pub struct RateLimitConfig {
    /// Maximum requests allowed in the window.
    pub max_requests: u32,
    /// Window duration in seconds.
    pub window_seconds: u64,
    /// Redis key prefix (e.g. "rate_limit:").
    pub key_prefix: String,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            max_requests: 100,
            window_seconds: 60,
            key_prefix: "rate_limit:".into(),
        }
    }
}

/// Sliding-window rate limiter middleware — Redis-backed for multi-worker
/// deployments.
///
/// Keyed by client IP address (derived from `x-forwarded-for` or
/// `axum`'s `ConnectInfo`).  On the first request in a window the key is
/// created with a TTL; subsequent requests increment the counter.
///
/// # Fallback
///
/// If Redis is unavailable (`incr` returns `None`) the request is allowed
/// through — we never block legitimate traffic because of an infra issue.
pub async fn rate_limit_middleware(
    State(redis): State<Arc<RedisClient>>,
    request: Request,
    next: Next,
) -> Result<Response, AppError> {
    let config = RateLimitConfig::default();
    let client_ip = extract_client_ip(&request);
    let key = format!("{}{client_ip}", config.key_prefix);

    // Increment and check
    let count = match redis.incr(&key).await? {
        Some(c) => c,
        None => {
            // Redis unavailable — allow through (graceful degradation)
            return Ok(next.run(request).await);
        }
    };

    // Set expiry on first hit in this window
    if count == 1 {
        let _ = redis.expire(&key, config.window_seconds as i64).await?;
    }

    if count > config.max_requests as i64 {
        return Err(AppError::rate_limit());
    }

    Ok(next.run(request).await)
}

/// Extract the client IP from the request.
///
/// Prefers `x-forwarded-for` header (taking the first IP in the chain),
/// falls back to the socket address, and ultimately to `127.0.0.1`.
pub(crate) fn extract_client_ip(request: &Request) -> String {
    // Prefer x-forwarded-for header (reverse-proxy / load-balancer)
    if let Some(fwd) = request
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
    {
        // Take the first IP in the chain (client origin)
        let ip = fwd.split(',').next().unwrap_or("unknown").trim();
        if !ip.is_empty() {
            return ip.to_owned();
        }
    }

    // Fallback: use the socket address if available
    request
        .extensions()
        .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
        .map(|ci| ci.0.ip().to_string())
        .unwrap_or_else(|| "127.0.0.1".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};

    #[test]
    fn test_rate_limit_config_defaults() {
        let config = RateLimitConfig::default();
        assert_eq!(config.max_requests, 100);
        assert_eq!(config.window_seconds, 60);
        assert_eq!(config.key_prefix, "rate_limit:");
    }

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
    fn test_extract_client_ip_fallback() {
        let req = Request::builder()
            .uri("/")
            .body(Body::empty())
            .unwrap();
        let ip = extract_client_ip(&req);
        assert!(!ip.is_empty(), "Should have a fallback IP");
    }
}
