//! Login lockout — brute-force protection via Redis counters.
//!
//! After 5 consecutive failed login attempts for the same email address,
//! further attempts are blocked for 15 minutes. Successful login resets
//! the counter.

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use std::sync::Arc;

/// Maximum failed attempts before lockout.
const MAX_ATTEMPTS: i64 = 5;

/// Lockout duration in seconds (15 minutes).
const LOCKOUT_SECONDS: i64 = 900;

/// Redis key prefix for failed-attempt counters.
const ATTEMPT_KEY_PREFIX: &str = "login_attempts:";

/// Redis key prefix for lockout flags.
const LOCK_KEY_PREFIX: &str = "login_locked:";

// ---------------------------------------------------------------------------
// LoginLockout
// ---------------------------------------------------------------------------

/// Login lockout manager backed by Redis with graceful degradation.
///
/// When Redis is unavailable, `is_locked` always returns `Ok(false)` —
/// the application allows login attempts to proceed (no lockout enforcement).
#[derive(Clone)]
pub struct LoginLockout {
    redis: Arc<RedisClient>,
}

impl LoginLockout {
    /// Create a new lockout manager around a [`RedisClient`].
    pub fn new(redis: Arc<RedisClient>) -> Self {
        Self { redis }
    }

    /// Build the attempt-counter key for an email address.
    fn attempt_key(email: &str) -> String {
        format!("{ATTEMPT_KEY_PREFIX}{}", email.to_lowercase())
    }

    /// Build the lockout-flag key for an email address.
    fn lock_key(email: &str) -> String {
        format!("{LOCK_KEY_PREFIX}{}", email.to_lowercase())
    }

    /// Record a failed login attempt for the given email.
    ///
    /// Increments the Redis counter and sets the lockout flag if the
    /// threshold is reached.
    pub async fn record_failed_attempt(&self, email: &str) -> AppResult<()> {
        let akey = Self::attempt_key(email);

        // Increment counter (returns None if Redis unavailable — graceful)
        let count = match self.redis.incr(&akey).await? {
            Some(c) => c,
            None => return Ok(()), // Redis unavailable, skip
        };

        // Set expiry on first attempt (re-sets on subsequent calls safely)
        if count == 1 {
            let _ = self.redis.expire(&akey, LOCKOUT_SECONDS).await?;
        }

        tracing::debug!(email, count, "Failed login attempt recorded");

        // Lock if threshold reached
        if count >= MAX_ATTEMPTS {
            let _ = self
                .redis
                .setex(&Self::lock_key(email), "1", LOCKOUT_SECONDS as u64)
                .await?;
            tracing::warn!(email, count, "Account locked due to too many failed attempts");
        }

        Ok(())
    }

    /// Check whether the email is currently locked out.
    ///
    /// Returns `Ok(true)` if locked, `Ok(false)` if not locked or Redis
    /// is unavailable.
    pub async fn is_locked(&self, email: &str) -> AppResult<bool> {
        match self.redis.exists(&Self::lock_key(email)).await? {
            Some(exists) => Ok(exists),
            None => {
                // Redis unavailable — allow login (graceful degradation)
                Ok(false)
            }
        }
    }

    /// Reset the failed-attempt counter and lockout flag.
    ///
    /// Called after a successful login.
    pub async fn reset_attempts(&self, email: &str) -> AppResult<()> {
        let _ = self.redis.del(&Self::attempt_key(email)).await?;
        let _ = self.redis.del(&Self::lock_key(email)).await?;
        Ok(())
    }

    /// Return the number of remaining attempts before lockout.
    ///
    /// Returns `None` if Redis is unavailable.
    pub async fn remaining_attempts(&self, email: &str) -> AppResult<Option<i64>> {
        match self.redis.get(&Self::attempt_key(email)).await? {
            Some(val) => {
                let count: i64 = val.parse().unwrap_or(0);
                Ok(Some((MAX_ATTEMPTS - count).max(0)))
            }
            None => Ok(None),
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
        let akey = LoginLockout::attempt_key("User@Example.Com");
        assert_eq!(akey, "login_attempts:user@example.com");

        let lkey = LoginLockout::lock_key("User@Example.Com");
        assert_eq!(lkey, "login_locked:user@example.com");
    }

    #[test]
    fn test_max_attempts() {
        assert_eq!(MAX_ATTEMPTS, 5);
    }

    #[test]
    fn test_lockout_duration() {
        assert_eq!(LOCKOUT_SECONDS, 900); // 15 minutes
    }
}
