//! Phase4Scheduler — Actor-based background task for Phase4 storage execution.
//!
//! Mirrors Python `app/service/phase4_scheduler.py` (1,338 lines).
//!
//! Architecture:
//! ```text
//! Phase4Scheduler (独立 tokio task)
//!   ├── mpsc::Receiver<Phase4Task>  — incoming task queue
//!   ├── Phase4Store                — nonce dedup + distributed lock
//!   ├── tokio::sync::Semaphore     — concurrency limit
//!   ├── Exponential backoff        — [10, 30, 60, 120, 300]s, max 5 retries
//!   └── SourceText Grounding       — edit distance validation (threshold 85%)
//! ```

use std::collections::VecDeque;
use std::num::NonZeroUsize;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, Semaphore};
use tokio::time::sleep;

use moling_core::error::{AppError, AppResult};
use moling_core::redis::RedisClient;
use sea_orm::DatabaseConnection;

use crate::phase4_service::Phase4Service;
use crate::phase4_store::Phase4Store;

// ---------------------------------------------------------------------------
// Task & State types
// ---------------------------------------------------------------------------

/// A Phase4 storage task to be processed by the scheduler.
#[derive(Debug, Clone)]
pub struct Phase4Task {
    /// Unique idempotency key (UUID or hash).
    pub nonce: String,
    /// Project ID.
    pub project_id: i32,
    /// Chapter ID that triggered Phase4 storage.
    pub chapter_id: String,
    /// Chapter full text for extraction.
    pub chapter_text: String,
    /// Optional card IDs to filter by.
    pub card_ids: Option<Vec<String>>,
    /// Whether to force processing even if already done.
    pub force: bool,
}

/// Task execution result.
#[derive(Debug, Clone)]
pub struct TaskResult {
    pub nonce: String,
    pub success: bool,
    pub message: String,
    pub retry_count: u32,
}

/// Scheduler global state.
#[derive(Debug, Clone)]
pub struct SchedulerStats {
    pub queue_size: usize,
    pub total_processed: u64,
    pub total_failed: u64,
    pub total_retried: u64,
    pub consecutive_failures: u32,
    pub active_tasks: u32,
}

// ---------------------------------------------------------------------------
// Retry configuration
// ---------------------------------------------------------------------------

/// Exponential backoff delays for retries (seconds).
const RETRY_BACKOFF_SECS: [u64; 5] = [10, 30, 60, 120, 300];

/// Maximum number of retry attempts.
const MAX_RETRIES: u32 = 5;

/// Maximum consecutive failures before alerting.
const MAX_CONSECUTIVE_FAILURES: u32 = 10;

/// Default distributed lock TTL (seconds).
const DEFAULT_LOCK_TTL: u64 = 30;

/// Maximum concurrent Phase4 tasks.
const DEFAULT_CONCURRENCY: usize = 3;

/// Nonce cache size for deduplication.
const NONCE_CACHE_SIZE: usize = 1000;

// ---------------------------------------------------------------------------
// Phase4Scheduler
// ---------------------------------------------------------------------------

/// Actor-based Phase4 scheduler.
///
/// Spawned as a background tokio task, it receives tasks via an mpsc channel,
/// acquires distributed locks, executes Phase4 storage, and handles retries.
#[derive(Clone)]
pub struct Phase4Scheduler {
    /// Sender for enqueuing new tasks.
    sender: mpsc::Sender<Phase4Task>,
    /// Semaphore controlling concurrent task execution.
    semaphore: Arc<Semaphore>,
}

struct SchedulerInner {
    receiver: mpsc::Receiver<Phase4Task>,
    semaphore: Arc<Semaphore>,
    store: Phase4Store,
    phase4: Phase4Service,
    db: DatabaseConnection,
    /// Pending tasks queue.
    #[allow(dead_code)]
    pending: VecDeque<Phase4Task>,
    /// Nonce deduplication cache (LRU-style).
    nonce_cache: lru::LruCache<String, bool>,
    /// Statistics.
    total_processed: u64,
    total_failed: u64,
    total_retried: u64,
    consecutive_failures: u32,
    active_tasks: u32,
}

impl Phase4Scheduler {
    /// Create a new scheduler (not yet started).
    pub fn new(capacity: usize, concurrency: usize) -> Self {
        let (tx, _rx) = mpsc::channel::<Phase4Task>(capacity.max(64));
        let semaphore = Arc::new(Semaphore::new(concurrency.max(1).min(8)));

        Self {
            sender: tx,
            semaphore,
        }
    }

    /// Get a sender for enqueuing tasks.
    pub fn sender(&self) -> mpsc::Sender<Phase4Task> {
        self.sender.clone()
    }

    /// Start the scheduler as a background task.
    /// Consumes `self` — after start, use the `sender()` to enqueue tasks.
    ///
    /// Returns a JoinHandle that can be awaited for graceful shutdown.
    pub fn start(
        mut self,
        redis_client: Option<RedisClient>,
        phase4: Phase4Service,
        db: DatabaseConnection,
    ) -> tokio::task::JoinHandle<()> {
        // Re-create the channel so we can move the receiver into the task.
        let (tx, rx) = mpsc::channel::<Phase4Task>(256);
        self.sender = tx;
        let semaphore = self.semaphore.clone();

        tokio::spawn(async move {
            let mut store = Phase4Store::new();
            if let Err(e) = store.init(redis_client).await {
                tracing::error!("Phase4Scheduler: store init failed: {e}");
            }

            let nonce_cache_size = NonZeroUsize::new(NONCE_CACHE_SIZE).unwrap();

            let mut inner = SchedulerInner {
                receiver: rx,
                semaphore,
                store,
                phase4,
                db,
                pending: VecDeque::new(),
                nonce_cache: lru::LruCache::new(nonce_cache_size),
                total_processed: 0,
                total_failed: 0,
                total_retried: 0,
                consecutive_failures: 0,
                active_tasks: 0,
            };

            tracing::info!(
                "Phase4Scheduler: started (backend={}, concurrency={})",
                inner.store.backend_type(),
                DEFAULT_CONCURRENCY,
            );

            // Main event loop
            while let Some(task) = inner.receiver.recv().await {
                inner.handle_task(task).await;
            }

            tracing::info!("Phase4Scheduler: channel closed, shutting down");
        })
    }

    /// Enqueue a task for processing (non-blocking).
    pub async fn enqueue(&self, task: Phase4Task) -> AppResult<()> {
        self.sender
            .send(task)
            .await
            .map_err(|_| AppError::internal("Phase4Scheduler: channel closed"))
    }

    /// Try to enqueue a task, returning false if the channel is full.
    pub fn try_enqueue(&self, task: Phase4Task) -> bool {
        self.sender.try_send(task).is_ok()
    }
}

impl SchedulerInner {
    async fn handle_task(&mut self, task: Phase4Task) {
        // 1. Nonce deduplication
        if let Some(&cached) = self.nonce_cache.get(&task.nonce) {
            if cached {
                tracing::debug!("Phase4Scheduler: duplicate nonce {}", task.nonce);
                return;
            }
        }

        match self.store.check_nonce(&task.nonce).await {
            Ok(true) => {
                self.nonce_cache.put(task.nonce.clone(), true);
                tracing::debug!("Phase4Scheduler: duplicate nonce {}", task.nonce);
                return;
            }
            Ok(false) => {
                self.nonce_cache.put(task.nonce.clone(), false);
            }
            Err(e) => {
                tracing::error!("Phase4Scheduler: nonce check failed for {}: {e}", task.nonce);
            }
        }

        // 2. Acquire semaphore permit
        let _permit = self.semaphore.clone().acquire_owned().await;
        self.active_tasks += 1;

        // 3. Distributed lock on project
        let lock_key = format!("{}:{}", task.project_id, task.chapter_id);
        let owner_id = task.nonce.clone();

        let locked = match self.store.acquire_lock(&lock_key, &owner_id, DEFAULT_LOCK_TTL).await {
            Ok(l) => l,
            Err(e) => {
                tracing::error!("Phase4Scheduler: lock acquire failed: {e}");
                self.active_tasks -= 1;
                return;
            }
        };

        if !locked {
            tracing::debug!(
                "Phase4Scheduler: lock held for project={} chapter={}",
                task.project_id, task.chapter_id
            );
            self.active_tasks -= 1;
            return;
        }

        // 4. Execute with retry
        let result = self.execute_with_retry(&task, &lock_key, &owner_id).await;

        // 5. Record nonce
        if let Err(e) = self.store.record_nonce(&task.nonce).await {
            tracing::error!("Phase4Scheduler: failed to record nonce {}: {e}", task.nonce);
        }

        // 6. Update stats
        if result.success {
            self.total_processed += 1;
            self.consecutive_failures = 0;
            tracing::info!(
                "Phase4Scheduler: task {} completed (project={}, chapter={})",
                task.nonce, task.project_id, task.chapter_id
            );
        } else {
            self.total_failed += 1;
            self.consecutive_failures += 1;
            tracing::error!(
                "Phase4Scheduler: task {} failed after {} retries: {}",
                task.nonce, result.retry_count, result.message
            );

            if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES {
                tracing::error!(
                    "Phase4Scheduler: {} consecutive failures — ALERT",
                    self.consecutive_failures
                );
            }
        }

        self.active_tasks -= 1;
    }

    async fn execute_with_retry(
        &mut self,
        task: &Phase4Task,
        lock_key: &str,
        owner_id: &str,
    ) -> TaskResult {
        let mut retries = 0u32;
        let card_ids_ref: Option<&[String]> = task.card_ids.as_deref();

        loop {
            match self
                .phase4
                .run_phase4(
                    &self.db,
                    task.project_id,
                    &task.chapter_id,
                    &task.chapter_text,
                    card_ids_ref,
                )
                .await
            {
                Ok(_) => {
                    // Release lock on success
                    let _ = self.store.release_lock(lock_key, owner_id).await;
                    return TaskResult {
                        nonce: task.nonce.clone(),
                        success: true,
                        message: "ok".to_string(),
                        retry_count: retries,
                    };
                }
                Err(e) => {
                    if retries >= MAX_RETRIES {
                        let _ = self.store.release_lock(lock_key, owner_id).await;
                        return TaskResult {
                            nonce: task.nonce.clone(),
                            success: false,
                            message: format!("{e}"),
                            retry_count: retries,
                        };
                    }

                    let delay = RETRY_BACKOFF_SECS[retries as usize];
                    tracing::warn!(
                        "Phase4Scheduler: task {} attempt {}/{} failed: {e}. Retrying in {}s",
                        task.nonce, retries + 1, MAX_RETRIES + 1, delay
                    );

                    self.total_retried += 1;
                    sleep(Duration::from_secs(delay)).await;
                    retries += 1;
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Editable distance helper (SourceText Grounding)
// ---------------------------------------------------------------------------

/// Compute Levenshtein distance between two strings.
pub fn levenshtein_distance(a: &str, b: &str) -> usize {
    let a_chars: Vec<char> = a.chars().collect();
    let b_chars: Vec<char> = b.chars().collect();
    let m = a_chars.len();
    let n = b_chars.len();

    let mut dp = vec![vec![0usize; n + 1]; m + 1];
    for i in 0..=m { dp[i][0] = i; }
    for j in 0..=n { dp[0][j] = j; }

    for i in 1..=m {
        for j in 1..=n {
            let cost = if a_chars[i - 1] == b_chars[j - 1] { 0 } else { 1 };
            dp[i][j] = (dp[i - 1][j] + 1)
                .min(dp[i][j - 1] + 1)
                .min(dp[i - 1][j - 1] + cost);
        }
    }
    dp[m][n]
}

/// Compute similarity as 1 - (edit_distance / max_len).
/// Returns a value in [0.0, 1.0].
pub fn text_similarity(a: &str, b: &str) -> f64 {
    let max_len = a.chars().count().max(b.chars().count()).max(1);
    let dist = levenshtein_distance(a, b);
    1.0 - (dist as f64 / max_len as f64)
}

/// Default threshold for SourceText Grounding — similarity must be >= this value.
pub const SOURCE_TEXT_SIMILARITY_THRESHOLD: f64 = 0.85;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_levenshtein_identical() {
        assert_eq!(levenshtein_distance("hello", "hello"), 0);
    }

    #[test]
    fn test_levenshtein_single() {
        assert_eq!(levenshtein_distance("hello", "hallo"), 1);
    }

    #[test]
    fn test_levenshtein_completely_different() {
        assert_eq!(levenshtein_distance("abc", "xyz"), 3);
    }

    #[test]
    fn test_levenshtein_chinese() {
        assert_eq!(levenshtein_distance("你好世界", "你好世界"), 0);
        assert_eq!(levenshtein_distance("你好世界", "你好地球"), 2);  // 世界→地球 = 2 edits
    }

    #[test]
    fn test_text_similarity_perfect() {
        assert!((text_similarity("完全相同", "完全相同") - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_text_similarity_high() {
        let sim = text_similarity("林风拔出屠天剑", "林风缓缓拔出屠天剑");
        assert!(sim > 0.7, "similarity should be high: {sim}");
    }

    #[test]
    fn test_text_similarity_low() {
        let sim = text_similarity("林风吃饭", "小明跑步");
        assert!(sim < 0.5, "similarity should be low: {sim}");
    }

    #[test]
    fn test_similarity_threshold() {
        // Short text: "林风" vs "林峰" — 1 edit out of 4 chars = 0.75
        let sim = text_similarity("林风", "林峰");
        assert!(sim < SOURCE_TEXT_SIMILARITY_THRESHOLD);
    }
}
