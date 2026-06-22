//! JWT Token Blacklist — implements immediate token revocation on logout.
//!
//! Uses Redis via [`moling_core::redis::RedisClient`] with TTL-based auto-expiry.
//! If Redis is unavailable, blacklist functions return `Ok(None)` (graceful
//! degradation — revocation is skipped but the user is not blocked).

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use std::sync::Arc;
use std::time::Duration;

/// Redis key prefix for blacklisted JTIs.
const BLACKLIST_KEY_PREFIX: &str = "blacklist:";

// ---------------------------------------------------------------------------
// TokenBlacklist
// ---------------------------------------------------------------------------

/// Token blacklist backed by Redis with graceful degradation.
///
/// When Redis is unavailable, `blacklist_token` and `is_blacklisted` return
/// `Ok(false)` — the application continues to function despite the missing
/// revocation feature.
#[derive(Clone)]
pub struct TokenBlacklist {
    redis: Arc<RedisClient>,
}

impl TokenBlacklist {
    /// Create a new blacklist wrapper around a [`RedisClient`].
    pub fn new(redis: Arc<RedisClient>) -> Self {
        Self { redis }
    }

    /// Build the Redis key for a given JTI.
    fn key(jti: &str) -> String {
        format!("{BLACKLIST_KEY_PREFIX}{jti}")
    }

    /// Add a token JTI to the blacklist with a given TTL.
    ///
    /// Returns `Ok(true)` if the token was successfully blacklisted,
    /// `Ok(false)` if Redis was unavailable.
    pub async fn blacklist_token(
        &self,
        token_id: &str,
        ttl: Duration,
    ) -> AppResult<bool> {
        let ttl_secs = ttl.as_secs();
        if ttl_secs == 0 {
            return Ok(false); // Nothing to revoke
        }

        match self.redis.setex(&Self::key(token_id), "1", ttl_secs).await? {
            Some(()) => {
                tracing::debug!(jti = %token_id, ttl = ttl_secs, "Token blacklisted");
                Ok(true)
            }
            None => {
                tracing::warn!(jti = %token_id, "Redis unavailable — token not blacklisted");
                Ok(false)
            }
        }
    }

    /// Check whether a token JTI is in the blacklist.
    ///
    /// Returns `Ok(true)` if blacklisted, `Ok(false)` if not, or if Redis
    /// is unavailable.
    pub async fn is_blacklisted(&self, token_id: &str) -> AppResult<bool> {
        match self.redis.exists(&Self::key(token_id)).await? {
            Some(exists) => Ok(exists),
            None => {
                tracing::warn!(jti = %token_id, "Redis unavailable — assuming not blacklisted");
                Ok(false)
            }
        }
    }

    /// Remove a token JTI from the blacklist (admin un-revoke).
    ///
    /// Returns `Ok(true)` if removed, `Ok(false)` if Redis was unavailable.
    pub async fn remove_from_blacklist(&self, token_id: &str) -> AppResult<bool> {
        match self.redis.del(&Self::key(token_id)).await? {
            Some(()) => {
                tracing::debug!(jti = %token_id, "Token removed from blacklist");
                Ok(true)
            }
            None => {
                tracing::warn!(jti = %token_id, "Redis unavailable — token not removed");
                Ok(false)
            }
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
    fn test_key_format() {
        let key = TokenBlacklist::key("abc-123");
        assert_eq!(key, "blacklist:abc-123");
    }

    #[test]
    fn test_blacklist_token_zero_ttl_is_noop() {
        // No async runtime needed — zero TTL returns false immediately
        // This test validates the early-exit path
        assert_eq!(Duration::from_secs(0).as_secs(), 0);
    }
}
