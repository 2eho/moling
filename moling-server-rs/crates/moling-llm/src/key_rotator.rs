//! API Key rotator — multi-key load balancing with error marking and dual-pool support.
//!
//! Manages Pro Pool and Flash Pool API keys with:
//! - Round-robin or least-usage selection strategy
//! - Exponential backoff cooldown (30s → 60s → 120s → 300s)
//! - Auto-recovery when cooldown expires
//! - Per-key health tracking with consecutive error counting
//!
//! Mirrors the Python `KeyManager` from `app/llm/key_manager.py`.

use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::RwLock;

/// Duration (in seconds) for exponential backoff levels.
const BACKOFF_SCHEDULE: [u64; 4] = [30, 60, 120, 300];

/// Maximum consecutive errors before forcing cooldown (even for non-rate-limit errors).
const MAX_CONSECUTIVE_ERRORS: usize = 3;

// ---------------------------------------------------------------------------
// Strategy
// ---------------------------------------------------------------------------

/// Key selection strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SelectionStrategy {
    /// Select the key with the fewest usage count.
    LeastUsage,
    /// Select keys in round-robin order.
    RoundRobin,
}

impl SelectionStrategy {
    /// Parse from a string (case-insensitive).
    pub fn parse(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "round_robin" | "roundrobin" | "rr" => Self::RoundRobin,
            _ => Self::LeastUsage,
        }
    }
}

// ---------------------------------------------------------------------------
// Pool
// ---------------------------------------------------------------------------

/// API key pool identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Pool {
    /// Pro pool (typically 9 keys).
    Pro,
    /// Flash pool (typically 6 keys).
    Flash,
}

impl Pool {
    /// Parse from a string (case-insensitive).
    pub fn parse(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "pro" => Some(Self::Pro),
            "flash" => Some(Self::Flash),
            _ => None,
        }
    }
}

impl std::fmt::Display for Pool {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pro => write!(f, "pro"),
            Self::Flash => write!(f, "flash"),
        }
    }
}

// ---------------------------------------------------------------------------
// KeyHealth
// ---------------------------------------------------------------------------

/// Health state for a single API key.
#[derive(Debug, Clone)]
pub struct KeyHealth {
    /// The API key (potentially masked).
    pub key: String,
    /// Which pool this key belongs to.
    pub pool: Pool,
    /// Total successful usage count.
    pub usage_count: usize,
    /// Consecutive error count.
    pub consecutive_errors: usize,
    /// When the last error occurred.
    pub last_error_at: Option<std::time::Instant>,
    /// Cooldown expiration time (None = not cooling).
    pub cooling_until: Option<std::time::Instant>,
    /// Current backoff level (0 = healthy, 1 = 30s, 2 = 60s, 3 = 120s, 4 = 300s).
    pub backoff_level: u32,
    /// Whether the key is currently healthy.
    pub is_healthy: bool,
}

impl KeyHealth {
    fn new(key: String, pool: Pool) -> Self {
        Self {
            key,
            pool,
            usage_count: 0,
            consecutive_errors: 0,
            last_error_at: None,
            cooling_until: None,
            backoff_level: 0,
            is_healthy: true,
        }
    }
}

// ---------------------------------------------------------------------------
// KeyRotator
// ---------------------------------------------------------------------------

/// Thread-safe API key rotator with dual-pool support and health tracking.
///
/// Keys are distributed according to the configured [`SelectionStrategy`].
/// Keys that encounter errors are placed on exponentially-increasing cooldown.
///
/// # Example
///
/// ```ignore
/// let rotator = KeyRotator::new()
///     .with_pro_keys(vec!["sk-pro-1".into(), "sk-pro-2".into()])
///     .with_flash_keys(vec!["sk-flash-1".into()])
///     .with_strategy(SelectionStrategy::LeastUsage);
///
/// let key = rotator.next(Pool::Pro).unwrap();
/// // Use key for API call...
/// rotator.mark_success(&key);
/// ```
pub struct KeyRotator {
    /// All key health states, indexed by key string.
    health: RwLock<HashMap<String, KeyHealth>>,
    /// Pro pool key list (ordered).
    pro_keys: RwLock<Vec<String>>,
    /// Flash pool key list (ordered).
    flash_keys: RwLock<Vec<String>>,
    /// Round-robin cursor per pool.
    rr_cursor: [AtomicUsize; 2], // 0 = Pro, 1 = Flash
    /// Selection strategy.
    strategy: SelectionStrategy,
}

impl KeyRotator {
    /// Create a new empty rotator with the default strategy (LeastUsage).
    pub fn new() -> Self {
        Self {
            health: RwLock::new(HashMap::new()),
            pro_keys: RwLock::new(Vec::new()),
            flash_keys: RwLock::new(Vec::new()),
            rr_cursor: [AtomicUsize::new(0), AtomicUsize::new(0)],
            strategy: SelectionStrategy::LeastUsage,
        }
    }

    /// Create a new rotator from a single list of keys (assigned to Pro pool).
    ///
    /// This constructor exists for backward compatibility with single-pool usage.
    pub fn from_keys(keys: Vec<String>) -> Self {
        let rotator = Self::new();
        {
            let mut health = rotator.health.write().unwrap_or_else(|e| e.into_inner());
            let mut pro = rotator.pro_keys.write().unwrap_or_else(|e| e.into_inner());
            for key in keys {
                health.insert(key.clone(), KeyHealth::new(key.clone(), Pool::Pro));
                pro.push(key);
            }
        }
        rotator
    }

    /// Set the Pro pool keys.
    pub fn with_pro_keys(self, keys: Vec<String>) -> Self {
        {
            let mut health = self.health.write().unwrap_or_else(|e| e.into_inner());
            let mut pro = self.pro_keys.write().unwrap_or_else(|e| e.into_inner());
            for key in keys {
                health
                    .entry(key.clone())
                    .or_insert_with(|| KeyHealth::new(key.clone(), Pool::Pro));
                if !pro.contains(&key) {
                    pro.push(key);
                }
            }
        }
        self
    }

    /// Set the Flash pool keys.
    pub fn with_flash_keys(self, keys: Vec<String>) -> Self {
        {
            let mut health = self.health.write().unwrap_or_else(|e| e.into_inner());
            let mut flash = self.flash_keys.write().unwrap_or_else(|e| e.into_inner());
            for key in keys {
                health
                    .entry(key.clone())
                    .or_insert_with(|| KeyHealth::new(key.clone(), Pool::Flash));
                if !flash.contains(&key) {
                    flash.push(key);
                }
            }
        }
        self
    }

    /// Set the selection strategy.
    pub fn with_strategy(mut self, strategy: SelectionStrategy) -> Self {
        self.strategy = strategy;
        self
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Get the next available API key from the specified pool.
    ///
    /// Returns `None` if the pool is empty or all keys are on cooldown.
    /// In the "all cooldown" case, returns the key with the earliest cooldown
    /// expiry as a fallback.
    pub fn next(&self, pool: Pool) -> Option<String> {
        let pool_idx = pool_index(pool);
        let keys = self.pool_keys(pool);
        if keys.is_empty() {
            return None;
        }

        let health = self.health.read().unwrap_or_else(|e| e.into_inner());
        let now = std::time::Instant::now();

        // Auto-recover keys whose cooldown has expired;
        // exclude keys still on active cooldown
        let healthy_keys: Vec<&String> = keys
            .iter()
            .filter(|k| {
                match health.get(*k) {
                    Some(h) if !h.is_healthy => {
                        // Unhealthy: include only if cooldown has expired
                        h.cooling_until.map_or(false, |c| now >= c)
                    }
                    Some(_) => true, // healthy
                    None => false,
                }
            })
            .collect();

        if healthy_keys.is_empty() {
            // All keys on cooldown — return earliest recovery
            let earliest = keys
                .iter()
                .filter_map(|k| {
                    health
                        .get(k)
                        .map(|h| (k, h.cooling_until.unwrap_or(now)))
                })
                .min_by_key(|(_, cooldown)| *cooldown)
                .map(|(k, _)| k.clone());

            if let Some(ref key) = earliest {
                tracing::warn!(
                    pool = %pool,
                    key = %mask_key(key),
                    "All API keys on cooldown, reusing earliest"
                );
            }
            return earliest;
        }

        match self.strategy {
            SelectionStrategy::LeastUsage => {
                // Select key with minimum usage_count among healthy keys
                let selected = healthy_keys
                    .iter()
                    .min_by_key(|k| {
                        health.get(k.as_str()).map(|h| h.usage_count).unwrap_or(usize::MAX)
                    })
                    .map(|k| (*k).clone());

                // Increment usage count
                if let Some(ref sel) = selected {
                    drop(health);
                    if let Ok(mut h) = self.health.write()
                        && let Some(state) = h.get_mut(sel)
                    {
                        state.usage_count += 1;
                    }
                }
                selected
            }
            SelectionStrategy::RoundRobin => {
                let len = healthy_keys.len();
                let idx = self.rr_cursor[pool_idx].load(Ordering::Relaxed) % len;
                let selected = healthy_keys[idx].clone();
                self.rr_cursor[pool_idx].store((idx + 1) % len, Ordering::Relaxed);

                // Increment usage count
                drop(health);
                if let Ok(mut h) = self.health.write()
                    && let Some(state) = h.get_mut(&selected)
                {
                    state.usage_count += 1;
                }
                Some(selected)
            }
        }
    }

    /// Backward-compatible method: get next key from Pro pool.
    /// Returns `None` if no keys are available.
    pub fn next_pro(&self) -> Option<String> {
        self.next(Pool::Pro)
    }

    /// Backward-compatible method: get next key from Flash pool.
    pub fn next_flash(&self) -> Option<String> {
        self.next(Pool::Flash)
    }

    /// Mark a key as having encountered an error.
    ///
    /// - Rate limit errors (error_type = "rate_limit"): immediately cooldown
    ///   the key with exponential backoff.
    /// - Other errors: increment consecutive error counter; cooldown after
    ///   `MAX_CONSECUTIVE_ERRORS` consecutive failures.
    pub fn mark_error(&self, key: &str, error_type: &str) {
        if let Ok(mut health) = self.health.write()
            && let Some(state) = health.get_mut(key)
        {
            state.consecutive_errors += 1;
            state.last_error_at = Some(std::time::Instant::now());

            let should_cool = error_type == "rate_limit"
                || state.consecutive_errors >= MAX_CONSECUTIVE_ERRORS;

            if should_cool {
                let level =
                    usize::min(state.backoff_level as usize, BACKOFF_SCHEDULE.len() - 1);
                let duration = Duration::from_secs(BACKOFF_SCHEDULE[level]);
                state.cooling_until =
                    Some(std::time::Instant::now() + duration);
                state.backoff_level = (level + 1) as u32;
                state.is_healthy = false;

                tracing::warn!(
                    key = %mask_key(key),
                    backoff_level = state.backoff_level,
                    errors = state.consecutive_errors,
                    error_type,
                    "API key placed on cooldown"
                );
            }
        }
    }

    /// Mark a key as having succeeded.
    ///
    /// Resets error count, clears cooldown, and sets backoff level to 0.
    pub fn mark_success(&self, key: &str) {
        if let Ok(mut health) = self.health.write()
            && let Some(state) = health.get_mut(key)
        {
            state.consecutive_errors = 0;
            state.last_error_at = None;
            state.is_healthy = true;
            state.cooling_until = None;
            state.backoff_level = 0;
        }
    }

    /// Get the health snapshot for a key (may return masked key in snapshot).
    pub fn get_health(&self, key: &str) -> Option<KeyHealth> {
        let health = self.health.read().unwrap_or_else(|e| e.into_inner());
        health.get(key).cloned()
    }

    /// Get pool status overview.
    pub fn pool_status(&self, pool: Pool) -> PoolStatus {
        let health = self.health.read().unwrap_or_else(|e| e.into_inner());
        let keys = self.pool_keys(pool);
        let now = std::time::Instant::now();

        let total = keys.len();
        let healthy_count = keys
            .iter()
            .filter(|k| {
                health
                    .get(*k)
                    .map(|h| h.is_healthy || h.cooling_until.is_some_and(|c| now >= c))
                    .unwrap_or(false)
            })
            .count();
        let cooling_count = keys
            .iter()
            .filter(|k| {
                health
                    .get(*k)
                    .map(|h| !h.is_healthy && h.cooling_until.is_some_and(|c| now < c))
                    .unwrap_or(false)
            })
            .count();

        let key_snapshots: Vec<KeySnapshot> = keys
            .iter()
            .filter_map(|k| {
                health.get(k).map(|h| KeySnapshot {
                    key: mask_key(k),
                    is_healthy: h.is_healthy,
                    usage_count: h.usage_count,
                    consecutive_errors: h.consecutive_errors,
                    backoff_level: h.backoff_level,
                    cooling_until: h.cooling_until,
                })
            })
            .collect();

        PoolStatus {
            pool,
            total,
            healthy: healthy_count,
            cooling: cooling_count,
            keys: key_snapshots,
        }
    }

    /// Number of available (non-cooldown) keys in a pool.
    pub fn available_count(&self, pool: Pool) -> usize {
        let health = self.health.read().unwrap_or_else(|e| e.into_inner());
        let keys = self.pool_keys(pool);
        let now = std::time::Instant::now();
        keys.iter()
            .filter(|k| {
                health
                    .get(*k)
                    .map(|h| h.is_healthy || h.cooling_until.is_some_and(|c| now >= c))
                    .unwrap_or(false)
            })
            .count()
    }

    /// Total number of keys in a pool.
    pub fn total_count(&self, pool: Pool) -> usize {
        self.pool_keys(pool).len()
    }

    // ------------------------------------------------------------------
    // Internal
    // ------------------------------------------------------------------

    fn pool_keys(&self, pool: Pool) -> Vec<String> {
        match pool {
            Pool::Pro => self.pro_keys.read().unwrap_or_else(|e| e.into_inner()).clone(),
            Pool::Flash => self.flash_keys.read().unwrap_or_else(|e| e.into_inner()).clone(),
        }
    }
}

impl Default for KeyRotator {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Pool status types
// ---------------------------------------------------------------------------

/// Snapshot of pool health status.
#[derive(Debug, Clone)]
pub struct PoolStatus {
    /// Which pool.
    pub pool: Pool,
    /// Total number of keys.
    pub total: usize,
    /// Number of healthy keys.
    pub healthy: usize,
    /// Number of keys currently cooling.
    pub cooling: usize,
    /// Per-key snapshots.
    pub keys: Vec<KeySnapshot>,
}

/// Snapshot of a single key's state.
#[derive(Debug, Clone)]
pub struct KeySnapshot {
    /// Masked key string.
    pub key: String,
    /// Whether the key is healthy.
    pub is_healthy: bool,
    /// Usage count.
    pub usage_count: usize,
    /// Consecutive errors.
    pub consecutive_errors: usize,
    /// Backoff level.
    pub backoff_level: u32,
    /// Cooldown expiration time.
    pub cooling_until: Option<std::time::Instant>,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Map Pool enum to array index for rr_cursor.
fn pool_index(pool: Pool) -> usize {
    match pool {
        Pool::Pro => 0,
        Pool::Flash => 1,
    }
}

/// Mask an API key, showing only the first 8 characters.
fn mask_key(key: &str) -> String {
    if key.len() > 8 {
        format!("{}...", &key[..8])
    } else {
        key.to_owned()
    }
}

// Re-export Duration as std for internal use.
use std::time::Duration;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_round_robin_distribution() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into(), "sk-c".into()])
            .with_strategy(SelectionStrategy::RoundRobin);
        assert_eq!(rotator.next(Pool::Pro).unwrap(), "sk-a");
        assert_eq!(rotator.next(Pool::Pro).unwrap(), "sk-b");
        assert_eq!(rotator.next(Pool::Pro).unwrap(), "sk-c");
        assert_eq!(rotator.next(Pool::Pro).unwrap(), "sk-a");
    }

    #[test]
    fn test_least_usage_distribution() {
        let rotator =
            KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into(), "sk-c".into()])
                .with_strategy(SelectionStrategy::LeastUsage);
        // All start at 0 usage; first selected gets incremented, so next call picks another
        let first = rotator.next(Pool::Pro).unwrap();
        let second = rotator.next(Pool::Pro).unwrap();
        assert_ne!(first, second);
    }

    #[test]
    fn test_error_marking() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into()])
            .with_strategy(SelectionStrategy::RoundRobin);
        rotator.mark_error("sk-a", "rate_limit");
        // sk-a should be on cooldown, sk-b selected
        let next = rotator.next(Pool::Pro).unwrap();
        assert_eq!(next, "sk-b");
    }

    #[test]
    fn test_consecutive_errors_cooldown() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into()]);
        // 3 consecutive non-rate-limit errors should trigger cooldown
        rotator.mark_error("sk-a", "other");
        rotator.mark_error("sk-a", "other");
        rotator.mark_error("sk-a", "other");
        let next = rotator.next(Pool::Pro).unwrap();
        assert_eq!(next, "sk-b");
    }

    #[test]
    fn test_success_resets_errors() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into()]);
        rotator.mark_error("sk-a", "other");
        rotator.mark_error("sk-a", "other");
        rotator.mark_success("sk-a");

        let health = rotator.get_health("sk-a").unwrap();
        assert_eq!(health.consecutive_errors, 0);
        assert!(health.is_healthy);
        assert_eq!(health.backoff_level, 0);
    }

    #[test]
    fn test_empty_keys() {
        let rotator = KeyRotator::new();
        assert!(rotator.next(Pool::Pro).is_none());
    }

    #[test]
    fn test_dual_pool() {
        let rotator = KeyRotator::new()
            .with_pro_keys(vec!["sk-pro".into()])
            .with_flash_keys(vec!["sk-flash".into()]);

        assert_eq!(rotator.next(Pool::Pro).unwrap(), "sk-pro");
        assert_eq!(rotator.next(Pool::Flash).unwrap(), "sk-flash");
        assert_eq!(rotator.total_count(Pool::Pro), 1);
        assert_eq!(rotator.total_count(Pool::Flash), 1);
    }

    #[test]
    fn test_available_count() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into()]);
        assert_eq!(rotator.available_count(Pool::Pro), 2);
        assert_eq!(rotator.total_count(Pool::Pro), 2);
    }

    #[test]
    fn test_pool_status() {
        let rotator = KeyRotator::from_keys(vec!["sk-a".into(), "sk-b".into()]);
        let status = rotator.pool_status(Pool::Pro);
        assert_eq!(status.total, 2);
        assert_eq!(status.healthy, 2);
        assert_eq!(status.cooling, 0);
    }

    #[test]
    fn test_strategy_parsing() {
        assert_eq!(
            SelectionStrategy::parse("round_robin"),
            SelectionStrategy::RoundRobin
        );
        assert_eq!(
            SelectionStrategy::parse("LEAST_USAGE"),
            SelectionStrategy::LeastUsage
        );
        assert_eq!(
            SelectionStrategy::parse("unknown"),
            SelectionStrategy::LeastUsage
        );
    }

    #[test]
    fn test_mask_key() {
        assert_eq!(mask_key("sk-abcdefghijklmn"), "sk-abcde...");
        assert_eq!(mask_key("short"), "short");
    }
}
