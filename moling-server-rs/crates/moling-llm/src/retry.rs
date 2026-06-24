//! Retry policy with exponential backoff, jitter, and Retry-After support.
//!
//! The [`RetryPolicy`] provides:
//! - Exponential backoff with configurable min/max bounds
//! - Randomized jitter to avoid thundering herd on recovery
//! - `Retry-After` header extraction from HTTP 429 responses
//! - Pre-flight rate limit gating via [`RateLimitTracker`](crate::client::RateLimitTracker)
//!
//! # Integration with KeyRotator
//!
//! When a 429 is encountered, the caller should:
//! 1. Call [`mark_rate_limit`] on the [`KeyRotator`](crate::key_rotator::KeyRotator) to cool the key
//! 2. Try the next available key from the same pool
//! 3. Wait for the backoff duration (with Retry-After honored) before retrying

use crate::client::RateLimitTracker;
use std::time::Duration;

/// Default jitter factor: ±30% of the computed backoff.
const DEFAULT_JITTER_FACTOR: f64 = 0.3;

// ---------------------------------------------------------------------------
// RetryPolicy
// ---------------------------------------------------------------------------

/// Configurable retry policy for LLM API calls.
///
/// # Example
///
/// ```ignore
/// let policy = RetryPolicy::new()
///     .with_max_retries(5)
///     .with_jitter_factor(0.2);
///
/// let wait = policy.backoff(2, None);     // 3rd attempt, no Retry-After
/// let wait = policy.backoff(0, Some(15)); // 1st retry, server says wait 15s
/// ```
#[derive(Debug, Clone)]
pub struct RetryPolicy {
    /// Maximum number of retry attempts (total attempts = max_retries + 1).
    pub max_retries: u32,
    /// Minimum backoff duration.
    pub min_backoff: Duration,
    /// Maximum backoff duration (caps exponential growth).
    pub max_backoff: Duration,
    /// Jitter factor: backoff ± (jitter_factor * backoff).
    /// 0.3 means backoff is randomly adjusted by ±30%.
    pub jitter_factor: f64,
}

impl RetryPolicy {
    /// Create a new retry policy with sensible defaults.
    ///
    /// Defaults: 3 retries, 1s min backoff, 10s max backoff, 30% jitter.
    pub fn new() -> Self {
        Self {
            max_retries: 3,
            min_backoff: Duration::from_secs(1),
            max_backoff: Duration::from_secs(10),
            jitter_factor: DEFAULT_JITTER_FACTOR,
        }
    }

    /// Set the maximum number of retry attempts.
    pub fn with_max_retries(mut self, retries: u32) -> Self {
        self.max_retries = retries;
        self
    }

    /// Set the minimum backoff duration.
    pub fn with_min_backoff(mut self, backoff: Duration) -> Self {
        self.min_backoff = backoff;
        self
    }

    /// Set the maximum backoff duration.
    pub fn with_max_backoff(mut self, backoff: Duration) -> Self {
        self.max_backoff = backoff;
        self
    }

    /// Set the jitter factor (0.0 = no jitter, 0.3 = ±30%, 0.5 = ±50%).
    pub fn with_jitter_factor(mut self, factor: f64) -> Self {
        self.jitter_factor = factor.clamp(0.0, 1.0);
        self
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Compute the backoff duration for the given attempt number.
    ///
    /// If `retry_after` is provided (from a server `Retry-After` header),
    /// it takes priority over exponential backoff. Otherwise, exponential
    /// backoff with jitter is computed.
    ///
    /// # Arguments
    /// * `attempt` — Zero-based retry attempt number (0 = first retry).
    /// * `retry_after` — Optional duration in seconds from server.
    pub fn backoff(&self, attempt: u32, retry_after: Option<u64>) -> Duration {
        if let Some(secs) = retry_after
            && secs > 0
        {
            let d = Duration::from_secs(secs);
            tracing::debug!(
                attempt,
                retry_after_secs = secs,
                "Using server-specified Retry-After"
            );
            return d;
        }

        let base = self.min_backoff * 2u32.pow(attempt);
        let capped = base.min(self.max_backoff);
        let jitter_range = self.jitter_factor * capped.as_secs_f64();
        let jitter = rand::random::<f64>() * jitter_range;
        // Random sign: subtract or add the jitter
        let signed_jitter = if rand::random::<bool>() { jitter } else { -jitter };
        let jittered = Duration::from_secs_f64((capped.as_secs_f64() + signed_jitter).max(0.0));

        tracing::debug!(
            attempt,
            base_secs = base.as_secs(),
            capped_secs = capped.as_secs(),
            jitter_secs = signed_jitter,
            final_secs = jittered.as_secs_f64(),
            "Computed exponential backoff with jitter"
        );

        jittered
    }

    /// Check if the given attempt should be retried.
    ///
    /// Returns `true` if `attempt < max_retries` AND the error is retryable.
    pub fn should_retry(&self, attempt: u32, is_retryable_error: bool) -> bool {
        attempt < self.max_retries && is_retryable_error
    }

    /// Pre-flight rate limit check.
    ///
    /// Checks whether the given API key can make a request based on the
    /// [`RateLimitTracker`]. If blocked, returns the recommended wait time
    /// in seconds.
    ///
    /// # Returns
    /// * `None` if the request can proceed immediately.
    /// * `Some(wait_secs)` if the request should be delayed.
    pub fn check_rate_limit(
        tracker: &RateLimitTracker,
        key: &str,
        estimated_tokens: u32,
    ) -> Option<f64> {
        if tracker.can_make_request(key, estimated_tokens) {
            None
        } else {
            let wait = tracker.get_wait_time(key);
            tracing::warn!(
                key = %crate::client::mask_key(key),
                wait_secs = wait,
                "Pre-flight rate limit: key blocked"
            );
            Some(wait)
        }
    }
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Retry-After header extraction
// ---------------------------------------------------------------------------

/// Extract `Retry-After` value from HTTP response headers.
///
/// Parses the value as a relative delay in seconds (the format used by
/// DeepSeek and most OpenAI-compatible APIs). Returns `None` if no valid
/// header is found or the value is zero/negative.
pub fn extract_retry_after(headers: &reqwest::header::HeaderMap) -> Option<u64> {
    headers
        .get(reqwest::header::RETRY_AFTER)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.trim().parse::<u64>().ok())
        .and_then(|secs| if secs > 0 { Some(secs) } else { None })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_policy_defaults() {
        let policy = RetryPolicy::new();
        assert_eq!(policy.max_retries, 3);
        assert_eq!(policy.min_backoff, Duration::from_secs(1));
        assert_eq!(policy.max_backoff, Duration::from_secs(10));
        assert!((policy.jitter_factor - 0.3).abs() < 0.01);
    }

    #[test]
    fn test_backoff_retry_after_priority() {
        let policy = RetryPolicy::new();
        // Retry-After should take priority over exponential backoff
        let wait = policy.backoff(2, Some(15));
        assert_eq!(wait, Duration::from_secs(15));
    }

    #[test]
    fn test_backoff_exponential_growth() {
        let policy = RetryPolicy::new().with_jitter_factor(0.0); // no jitter for determinism
        let a0 = policy.backoff(0, None);
        let a1 = policy.backoff(1, None);
        let a2 = policy.backoff(2, None);

        assert_eq!(a0, Duration::from_secs(1)); // 1s
        assert_eq!(a1, Duration::from_secs(2)); // 2s
        assert!(a2 <= policy.max_backoff); // capped
    }

    #[test]
    fn test_backoff_capped_at_max() {
        let policy = RetryPolicy::new().with_jitter_factor(0.0);
        let wait = policy.backoff(10, None);
        assert!(wait <= policy.max_backoff);
    }

    #[test]
    fn test_backoff_jitter_range() {
        // With jitter, backoff should vary but stay within ±jitter_factor
        let policy = RetryPolicy::new().with_jitter_factor(0.3);
        let min_expected = Duration::from_secs_f64(0.7);  // 1.0 - 0.3
        let max_expected = Duration::from_secs_f64(1.3);  // 1.0 + 0.3

        // Run multiple times to verify jitter stays in range
        for _ in 0..20 {
            let wait = policy.backoff(0, None);
            assert!(
                wait >= min_expected && wait <= max_expected,
                "Backoff {wait:?} out of range [{min_expected:?}, {max_expected:?}]"
            );
        }
    }

    #[test]
    fn test_backoff_minimum_zero() {
        // Very first attempt (0) with Retry-After 0 should still compute backoff
        let policy = RetryPolicy::new().with_jitter_factor(0.0);
        let wait = policy.backoff(0, Some(0));
        // Retry-After of 0 is ignored, falls back to exponential
        assert_eq!(wait, Duration::from_secs(1));
    }

    #[test]
    fn test_should_retry() {
        let policy = RetryPolicy::new();
        // Within retry limit, retryable error
        assert!(policy.should_retry(0, true));
        assert!(policy.should_retry(2, true));
        // Exceeded retry limit
        assert!(!policy.should_retry(3, true));
        // Within limit but non-retryable error
        assert!(!policy.should_retry(0, false));
    }

    #[test]
    fn test_extract_retry_after_seconds() {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::RETRY_AFTER,
            "30".parse().unwrap(),
        );
        assert_eq!(extract_retry_after(&headers), Some(30));
    }

    #[test]
    fn test_extract_retry_after_empty() {
        let headers = reqwest::header::HeaderMap::new();
        assert_eq!(extract_retry_after(&headers), None);
    }

    #[test]
    fn test_extract_retry_after_zero() {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            reqwest::header::RETRY_AFTER,
            "0".parse().unwrap(),
        );
        assert_eq!(extract_retry_after(&headers), None);
    }

    #[test]
    fn test_check_rate_limit_passes() {
        let tracker = RateLimitTracker::new();
        let wait = RetryPolicy::check_rate_limit(&tracker, "test-key", 100);
        assert!(wait.is_none());
    }

    #[test]
    fn test_policy_builder() {
        let policy = RetryPolicy::new()
            .with_max_retries(5)
            .with_min_backoff(Duration::from_secs(2))
            .with_max_backoff(Duration::from_secs(60))
            .with_jitter_factor(0.5);

        assert_eq!(policy.max_retries, 5);
        assert_eq!(policy.min_backoff, Duration::from_secs(2));
        assert_eq!(policy.max_backoff, Duration::from_secs(60));
        assert!((policy.jitter_factor - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_jitter_factor_clamped() {
        let policy = RetryPolicy::new().with_jitter_factor(1.5);
        assert!((policy.jitter_factor - 1.0).abs() < 0.01);

        let policy = RetryPolicy::new().with_jitter_factor(-0.5);
        assert!((policy.jitter_factor - 0.0).abs() < 0.01);
    }
}
