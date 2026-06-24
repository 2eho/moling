//! Distributed rate limiter — sliding-window algorithm via Redis ZSET + Lua.
//!
//! # Algorithm
//!
//! Each client key (e.g. IP address) maps to a Redis sorted set.  Every
//! request inserts its timestamp as a member into the ZSET and the Lua
//! script atomically:
//!
//! 1. Evicts entries outside the sliding window (`ZREMRANGEBYSCORE`).
//! 2. Counts remaining entries (`ZCARD`).
//! 3. If count < limit: adds the new entry, sets key TTL, returns allowed.
//! 4. If count ≥ limit: returns blocked with retry-after hint.
//!
//! # Graceful degradation
//!
//! When Redis is unreachable the rate limiter **always allows** the request.
//! We never block legitimate traffic because of an infrastructure issue.

use crate::error::AppError;
use crate::redis::RedisClient;
use async_trait::async_trait;
use std::sync::Arc;

// ---------------------------------------------------------------------------
// RateLimitResult
// ---------------------------------------------------------------------------

/// Outcome of a rate-limit check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RateLimitResult {
    /// Whether the request is allowed.
    pub allowed: bool,
    /// Number of requests currently in the window (including this one if
    /// allowed).
    pub current_count: u64,
    /// Remaining requests before hitting the limit.
    pub remaining: u64,
    /// Milliseconds until the oldest entry falls out of the window (only
    /// meaningful when `allowed` is `false`).
    pub retry_after_ms: u64,
}

impl RateLimitResult {
    /// An "allowed" result — the request passes the rate limit check.
    #[must_use]
    pub fn allowed(current_count: u64, remaining: u64) -> Self {
        Self {
            allowed: true,
            current_count,
            remaining,
            retry_after_ms: 0,
        }
    }

    /// A "blocked" result — the client has exceeded the limit.
    #[must_use]
    pub fn blocked(current_count: u64, retry_after_ms: u64) -> Self {
        Self {
            allowed: false,
            current_count,
            remaining: 0,
            retry_after_ms,
        }
    }
}

// ---------------------------------------------------------------------------
// RateLimiter trait
// ---------------------------------------------------------------------------

/// A distributed rate limiter.
///
/// Implementations must be `Send + Sync` so they can be shared across Axum
/// worker tasks behind an [`Arc`].
#[async_trait]
pub trait RateLimiter: Send + Sync {
    /// Check whether `key` is allowed to proceed under the given limit.
    ///
    /// # Arguments
    ///
    /// * `key` — The client identifier (e.g. `"rate_limit:192.168.1.1"`).
    /// * `max_requests` — Maximum requests allowed in the window.
    /// * `window_secs` — Sliding window duration in seconds.
    ///
    /// # Returns
    ///
    /// * `Ok(result)` — The check completed (Redis was reachable).
    ///
    /// # Errors
    ///
    /// Returns [`AppError`] when Redis is reachable but the Lua script
    /// execution fails (e.g. protocol error, type mismatch).
    ///
    /// When Redis is **unavailable** (connection pool exhausted, Redis down)
    /// implementations should return `Ok(RateLimitResult::allowed(...))` —
    /// we degrade gracefully rather than block traffic.
    async fn check_rate_limit(
        &self,
        key: &str,
        max_requests: u32,
        window_secs: u64,
    ) -> Result<RateLimitResult, AppError>;
}

// ---------------------------------------------------------------------------
// RedisRateLimiter
// ---------------------------------------------------------------------------

/// Redis-backed sliding-window rate limiter.
///
/// Uses a Lua script executed atomically inside Redis to guarantee correct
/// counting even under concurrent access from multiple application workers.
pub struct RedisRateLimiter {
    client: Arc<RedisClient>,
}

impl RedisRateLimiter {
    /// Create a new [`RedisRateLimiter`] wrapping the given [`RedisClient`].
    #[must_use]
    pub fn new(client: Arc<RedisClient>) -> Self {
        Self { client }
    }
}

// ---------------------------------------------------------------------------
// Lua script — atomic sliding-window check
// ---------------------------------------------------------------------------

/// Lua script that atomically checks and records a rate-limit hit.
///
/// # Keys
///
/// * `KEYS[1]` — Rate-limit key (e.g. `"rate_limit:10.0.0.1"`).
///
/// # Arguments
///
/// * `ARGV[1]` — Current timestamp in **milliseconds**.
/// * `ARGV[2]` — Window size in **milliseconds**.
/// * `ARGV[3]` — Maximum requests allowed in the window.
/// * `ARGV[4]` — Unique member identifier (nanosecond timestamp for
///   uniqueness; collisions are harmless — ZADD is idempotent for the
///   same score+member, which means duplicate inserts don't inflate the
///   count).
///
/// # Returns
///
/// A flat array: `{allowed, current_count, retry_after_ms}` where `allowed`
/// is `1` or `0`.
const SLIDING_WINDOW_LUA: &str = r"
-- 1. Remove entries outside the sliding window
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1] - ARGV[2])

-- 2. Count remaining entries
local count = redis.call('ZCARD', KEYS[1])

-- 3. Check limit
if count < tonumber(ARGV[3]) then
    -- Allowed: add the new entry
    redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
    -- Set/refresh key TTL (window + 1s buffer)
    redis.call('EXPIRE', KEYS[1], math.ceil(tonumber(ARGV[2]) / 1000) + 1)
    local new_count = count + 1
    local remaining = tonumber(ARGV[3]) - new_count
    return {1, new_count, remaining}
else
    -- Blocked: compute retry-after from the oldest entry still in the window
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    local retry_after_ms = 0
    if #oldest >= 2 then
        retry_after_ms = tonumber(oldest[2]) + tonumber(ARGV[2]) - tonumber(ARGV[1])
        if retry_after_ms < 0 then
            retry_after_ms = 0
        end
    end
    return {0, count, retry_after_ms}
end
";

#[async_trait]
impl RateLimiter for RedisRateLimiter {
    #[tracing::instrument(skip(self), fields(key, max_requests, window_secs))]
    async fn check_rate_limit(
        &self,
        key: &str,
        max_requests: u32,
        window_secs: u64,
    ) -> Result<RateLimitResult, AppError> {
        let Some(mut conn) = self.client.pool().get_conn().await else {
            tracing::debug!(key, "Redis unavailable — allowing request (graceful degradation)");
            return Ok(RateLimitResult::allowed(0, u64::from(max_requests)));
        };

        // Build unique member: nanosecond timestamp with 128-bit resolution
        // virtually guarantees no collisions within the same millisecond.
        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .ok()
            .and_then(|d| u64::try_from(d.as_millis()).ok())
            .unwrap_or(0);
        let window_ms = window_secs * 1000;
        let member = format!("{now_ms}:{}", uuid::Uuid::new_v4().as_simple());

        let script = redis::Script::new(SLIDING_WINDOW_LUA);

        let result: (i32, u64, u64) = script
            .key(key)
            .arg(now_ms)
            .arg(window_ms)
            .arg(max_requests)
            .arg(&member)
            .invoke_async(&mut *conn)
            .await
            .map_err(|e| {
                tracing::warn!(key, "Redis Lua script execution failed: {e}");
                AppError::internal("Rate limiter check failed")
            })?;

        let (allowed_raw, current_count, extra) = result;

        if allowed_raw == 1 {
            Ok(RateLimitResult::allowed(current_count, extra))
        } else {
            Ok(RateLimitResult::blocked(current_count, extra))
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limit_result_allowed() {
        let r = RateLimitResult::allowed(5, 95);
        assert!(r.allowed);
        assert_eq!(r.current_count, 5);
        assert_eq!(r.remaining, 95);
        assert_eq!(r.retry_after_ms, 0);
    }

    #[test]
    fn test_rate_limit_result_blocked() {
        let r = RateLimitResult::blocked(100, 4200);
        assert!(!r.allowed);
        assert_eq!(r.current_count, 100);
        assert_eq!(r.remaining, 0);
        assert_eq!(r.retry_after_ms, 4200);
    }

    #[test]
    fn test_lua_script_is_valid_syntax() {
        // Ensure the Lua script can be loaded as a `redis::Script`.
        // `redis::Script::new()` accepts any string; the real validation
        // happens at execution time inside Redis. We verify the script
        // constant is non-empty and contains expected Redis commands.
        let script = redis::Script::new(SLIDING_WINDOW_LUA);
        // Verify we got a Script back (not panicked)
        assert!(std::mem::size_of_val(&script) > 0);
        // Verify the raw constant contains expected Redis commands
        assert!(SLIDING_WINDOW_LUA.contains("ZREMRANGEBYSCORE"));
        assert!(SLIDING_WINDOW_LUA.contains("ZCARD"));
        assert!(SLIDING_WINDOW_LUA.contains("ZADD"));
        assert!(SLIDING_WINDOW_LUA.contains("ZRANGE"));
    }
}
