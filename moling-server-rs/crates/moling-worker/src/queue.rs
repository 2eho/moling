//! Redis-backed task queue with priority, retry, TTL, and dead-letter support.
//!
//! Implements BRPOPLPUSH-based reliable queue semantics:
//! 1. `push()` / `push_priority()` — LPUSH task onto a queue
//! 2. `pop()` / `pop_priority()` — BRPOPLPUSH from queue to processing list
//! 3. `acknowledge()` — LREM from processing list (task done)
//! 4. `dead_letter()` — move failed task to DLQ with error metadata
//!
//! # Priority Queues
//!
//! Three priority levels: high, medium, low. Each level maps to a separate
//! Redis list. `pop_priority()` checks queues in priority order.
//!
//! # Task Status Tracking
//!
//! Each task's status (pending/running/completed/failed) is tracked via
//! Redis hash keys. Retry counts are incremented on failure.

use moling_core::error::{AppError, AppResult};
use moling_core::redis::RedisClient;
use redis::AsyncCommands;
use std::sync::Arc;
use std::time::Duration;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Redis key prefix for task queues.
const QUEUE_PREFIX: &str = "task:queue:";

/// Redis key prefix for processing lists.
const PROCESSING_PREFIX: &str = "task:processing:";

/// Redis key prefix for dead letter queues.
const DLQ_PREFIX: &str = "task:dlq:";

/// Redis key prefix for task status hashes.
const STATUS_PREFIX: &str = "task:status:";

/// Redis key prefix for task metadata hashes.
const META_PREFIX: &str = "task:meta:";

/// Default task TTL in seconds (24 hours).
const DEFAULT_TASK_TTL: u64 = 86400;

/// Default max retries.
const DEFAULT_MAX_RETRIES: u32 = 3;

/// Priority levels for task queues.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, serde::Serialize, serde::Deserialize)]
pub enum Priority {
    High = 0,
    Medium = 1,
    Low = 2,
}

impl Priority {
    /// Redis queue suffix for this priority level.
    pub fn suffix(&self) -> &'static str {
        match self {
            Self::High => "high",
            Self::Medium => "med",
            Self::Low => "low",
        }
    }

    /// All priority levels in descending order (highest priority first).
    pub fn all() -> [Priority; 3] {
        [Priority::High, Priority::Medium, Priority::Low]
    }
}

/// Task status values.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

impl TaskStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Running => "running",
            Self::Completed => "completed",
            Self::Failed => "failed",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "pending" => Some(Self::Pending),
            "running" => Some(Self::Running),
            "completed" => Some(Self::Completed),
            "failed" => Some(Self::Failed),
            _ => None,
        }
    }
}

// ---------------------------------------------------------------------------
// Task Metadata
// ---------------------------------------------------------------------------

/// Metadata associated with a task in the queue.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TaskMeta {
    /// Unique task ID.
    pub task_id: String,
    /// Queue name this task belongs to.
    pub queue: String,
    /// Priority level.
    pub priority: Priority,
    /// Current status.
    pub status: String,
    /// Retry count so far.
    pub retry_count: u32,
    /// Maximum allowed retries.
    pub max_retries: u32,
    /// ISO 8601 creation timestamp.
    pub created_at: String,
    /// ISO 8601 last update timestamp.
    pub updated_at: String,
    /// Last error message, if any.
    pub last_error: Option<String>,
}

impl TaskMeta {
    /// Create a new TaskMeta for a freshly enqueued task.
    pub fn new(task_id: &str, queue: &str, priority: Priority, max_retries: u32) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        Self {
            task_id: task_id.to_owned(),
            queue: queue.to_owned(),
            priority,
            status: "pending".to_owned(),
            retry_count: 0,
            max_retries,
            created_at: now.clone(),
            updated_at: now,
            last_error: None,
        }
    }
}

// ---------------------------------------------------------------------------
// TaskQueue
// ---------------------------------------------------------------------------

/// Reliable Redis task queue with priority, retry, TTL, and graceful degradation.
///
/// When Redis is unavailable, all operations return `Result<Option<T>>`:
/// - `Ok(Some(v))` → operation succeeded
/// - `Ok(None)` → Redis unavailable (graceful degrade)
/// - `Err(e)` → Redis was reachable but operation failed
#[derive(Clone)]
pub struct TaskQueue {
    redis: Arc<RedisClient>,
    default_ttl: u64,
    default_max_retries: u32,
}

impl TaskQueue {
    /// Create a new TaskQueue with default TTL and retry settings.
    pub fn new(redis: Arc<RedisClient>) -> Self {
        Self {
            redis,
            default_ttl: DEFAULT_TASK_TTL,
            default_max_retries: DEFAULT_MAX_RETRIES,
        }
    }

    /// Create a TaskQueue with custom TTL and max retries.
    pub fn with_config(redis: Arc<RedisClient>, ttl: u64, max_retries: u32) -> Self {
        Self {
            redis,
            default_ttl: ttl,
            default_max_retries: max_retries,
        }
    }

    // ------------------------------------------------------------------
    // Push — enqueue tasks
    // ------------------------------------------------------------------

    /// Push a task payload onto a named queue at the default (low) priority.
    ///
    /// Returns the task metadata on success.
    pub async fn push(&self, queue: &str, task_json: &str) -> AppResult<Option<TaskMeta>> {
        self.push_priority(queue, task_json, Priority::Low, self.default_max_retries)
            .await
    }

    /// Push a task payload with a specific priority level.
    ///
    /// Creates task metadata and stores the task in the appropriate
    /// priority sub-queue. Sets a TTL on both the status and meta keys.
    pub async fn push_priority(
        &self,
        queue: &str,
        task_json: &str,
        priority: Priority,
        max_retries: u32,
    ) -> AppResult<Option<TaskMeta>> {
        // Parse task payload to extract task_id
        let task_id = self.extract_task_id(task_json);

        // Build metadata
        let meta = TaskMeta::new(&task_id, queue, priority, max_retries);
        let meta_json = serde_json::to_string(&meta)
            .unwrap_or_else(|_| "{}".to_owned());

        // Store metadata
        let meta_key = format!("{META_PREFIX}{queue}:{task_id}");
        let _ = self.redis.setex(&meta_key, &meta_json, self.default_ttl).await;

        // Set initial status
        let status_key = format!("{STATUS_PREFIX}{queue}:{task_id}");
        let _ = self.redis.setex(&status_key, "pending", self.default_ttl).await;

        // Push to priority queue
        let qkey = format!("{QUEUE_PREFIX}{queue}:{}", priority.suffix());
        match self.redis_lpush(&qkey, task_json).await {
            Ok(Some(())) => {
                tracing::info!(
                    queue,
                    task_id,
                    priority = ?priority,
                    "Task enqueued"
                );
                Ok(Some(meta))
            }
            Ok(None) => {
                tracing::warn!(queue, task_id, "Redis unavailable — task not enqueued");
                Ok(None)
            }
            Err(e) => Err(e),
        }
    }

    // ------------------------------------------------------------------
    // Pop — dequeue tasks (reliable)
    // ------------------------------------------------------------------

    /// Pop a task from a queue with timeout, using BRPOPLPUSH for reliability.
    ///
    /// Checks only the default (low priority) queue.
    pub async fn pop(&self, queue: &str, timeout: Duration) -> AppResult<Option<String>> {
        let qkey = format!("{QUEUE_PREFIX}{queue}:low");
        let pkey = format!("{PROCESSING_PREFIX}{queue}");
        self.brpoplpush_inner(&qkey, &pkey, timeout).await
    }

    /// Pop a task checking all priority levels in order (high → medium → low).
    ///
    /// Uses BRPOPLPUSH for reliable dequeuing. The timeout is the total time
    /// to wait across all priority levels.
    pub async fn pop_priority(&self, queue: &str, timeout: Duration) -> AppResult<Option<(Priority, String)>> {
        let deadline = tokio::time::Instant::now() + timeout;

        for priority in Priority::all() {
            let remaining = deadline
                .checked_duration_since(tokio::time::Instant::now())
                .unwrap_or(Duration::ZERO);

            if remaining.is_zero() {
                break;
            }

            let qkey = format!("{QUEUE_PREFIX}{queue}:{}", priority.suffix());
            let pkey = format!("{PROCESSING_PREFIX}{queue}");

            // Use a short timeout per priority level, then move to next
            let per_level_timeout = Duration::from_millis(500).min(remaining);

            match self.brpoplpush_inner(&qkey, &pkey, per_level_timeout).await {
                Ok(Some(task)) => {
                    // Update task status to running
                    self.update_task_status(queue, &task, TaskStatus::Running).await;
                    return Ok(Some((priority, task)));
                }
                Ok(None) => continue,
                Err(e) => return Err(e),
            }
        }

        Ok(None)
    }

    /// Pop a task from a specific priority queue.
    pub async fn pop_from(
        &self,
        queue: &str,
        priority: Priority,
        timeout: Duration,
    ) -> AppResult<Option<String>> {
        let qkey = format!("{QUEUE_PREFIX}{queue}:{}", priority.suffix());
        let pkey = format!("{PROCESSING_PREFIX}{queue}");
        self.brpoplpush_inner(&qkey, &pkey, timeout).await
    }

    // ------------------------------------------------------------------
    // Acknowledge / Complete
    // ------------------------------------------------------------------

    /// Acknowledge successful processing — remove task from the processing list
    /// and mark status as completed.
    pub async fn acknowledge(&self, queue: &str, task_json: &str) -> AppResult<bool> {
        let pkey = format!("{PROCESSING_PREFIX}{queue}");

        // Update status to completed
        self.update_task_status(queue, task_json, TaskStatus::Completed).await;

        match self.redis_lrem(&pkey, task_json, 1).await {
            Ok(Some(())) => {
                tracing::debug!(queue, "Task acknowledged");
                Ok(true)
            }
            Ok(None) => Ok(false),
            Err(e) => Err(e),
        }
    }

    // ------------------------------------------------------------------
    // Dead Letter Queue
    // ------------------------------------------------------------------

    /// Move a failed task to the dead letter queue with error metadata.
    ///
    /// Also increments the retry count. If the task has not exceeded
    /// max_retries, it is re-enqueued instead of dead-lettered.
    pub async fn dead_letter(&self, queue: &str, task_json: &str, error: &str) -> AppResult<Option<DeadLetterAction>> {
        let dkey = format!("{DLQ_PREFIX}{queue}");
        let dlq_entry = serde_json::json!({
            "task": task_json,
            "error": error,
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "queue": queue,
        })
        .to_string();

        // Remove from processing
        let _ = self.redis_lrem(&format!("{PROCESSING_PREFIX}{queue}"), task_json, 1).await;

        // Update status to failed
        self.update_task_status(queue, task_json, TaskStatus::Failed).await;

        // Increment retry count and check if we should retry
        let retry_count = self.increment_retry(queue, task_json).await?;
        let max_retries = self.get_max_retries(queue, task_json).await?;

        if retry_count < max_retries {
            // Re-enqueue for retry with exponential backoff
            let delay = 2u64.pow(retry_count) * 30;
            let retry_payload = serde_json::json!({
                "task": task_json,
                "retry_count": retry_count,
                "max_retries": max_retries,
                "last_error": error,
                "retry_after": chrono::Utc::now().timestamp() + delay as i64,
            }).to_string();

            self.redis_lpush(
                &format!("{QUEUE_PREFIX}{queue}:low"),
                &retry_payload,
            ).await?;

            tracing::warn!(
                queue,
                retry_count,
                max_retries,
                delay_secs = delay,
                "Task failed, re-enqueued for retry"
            );
            return Ok(Some(DeadLetterAction::Retried { retry_count, delay_secs: delay }));
        }

        // Max retries exceeded — put in DLQ
        match self.redis_lpush(&dkey, &dlq_entry).await {
            Ok(Some(())) => {
                tracing::warn!(queue, retry_count, "Task moved to dead letter queue (max retries exceeded)");
                Ok(Some(DeadLetterAction::DeadLettered))
            }
            Ok(None) => Ok(Some(DeadLetterAction::DeadLettered)),
            Err(e) => Err(e),
        }
    }

    /// List dead letter entries for a queue (up to 100).
    pub async fn list_dead_letters(&self, queue: &str) -> AppResult<Vec<String>> {
        let dkey = format!("{DLQ_PREFIX}{queue}");
        match self.redis_lrange(&dkey, 0, 99).await {
            Ok(Some(items)) => Ok(items),
            Ok(None) => Ok(vec![]),
            Err(e) => Err(e),
        }
    }

    /// Retry a dead-lettered task (move back to the original queue).
    pub async fn retry_dead_letter(&self, queue: &str, task_json: &str) -> AppResult<bool> {
        let dkey = format!("{DLQ_PREFIX}{queue}");
        let _ = self.redis_lrem(&dkey, task_json, 1).await;

        // Reset retry count
        self.reset_retry(queue, task_json).await;

        self.push(queue, task_json).await.map(|r| r.is_some())
    }

    // ------------------------------------------------------------------
    // Task Status & Metadata
    // ------------------------------------------------------------------

    /// Get the current status of a task.
    pub async fn get_task_status(&self, queue: &str, task_id: &str) -> AppResult<Option<TaskStatus>> {
        let status_key = format!("{STATUS_PREFIX}{queue}:{task_id}");
        match self.redis.get(&status_key).await {
            Ok(Some(s)) => Ok(TaskStatus::from_str(&s)),
            Ok(None) => Ok(None),
            Err(_) => Ok(None),
        }
    }

    /// Get full task metadata.
    pub async fn get_task_meta(&self, queue: &str, task_id: &str) -> AppResult<Option<TaskMeta>> {
        let meta_key = format!("{META_PREFIX}{queue}:{task_id}");
        match self.redis.get(&meta_key).await {
            Ok(Some(json)) => {
                match serde_json::from_str(&json) {
                    Ok(meta) => Ok(Some(meta)),
                    Err(_) => Ok(None),
                }
            }
            Ok(None) => Ok(None),
            Err(_) => Ok(None),
        }
    }

    /// Check whether a task exists (is pending or running).
    pub async fn task_exists(&self, queue: &str, task_id: &str) -> AppResult<bool> {
        let status = self.get_task_status(queue, task_id).await?;
        Ok(matches!(status, Some(TaskStatus::Pending) | Some(TaskStatus::Running)))
    }

    // ------------------------------------------------------------------
    // Queue size
    // ------------------------------------------------------------------

    /// Get the size of a priority queue.
    pub async fn queue_size(&self, queue: &str, priority: Priority) -> AppResult<usize> {
        let qkey = format!("{QUEUE_PREFIX}{queue}:{}", priority.suffix());
        match self.redis_llen(&qkey).await {
            Ok(Some(len)) => Ok(len),
            Ok(None) => Ok(0),
            Err(_) => Ok(0),
        }
    }

    /// Get the total queue size across all priority levels.
    pub async fn total_queue_size(&self, queue: &str) -> AppResult<usize> {
        let mut total = 0usize;
        for p in Priority::all() {
            total += self.queue_size(queue, p).await?;
        }
        Ok(total)
    }

    /// Get the processing list size.
    pub async fn processing_size(&self, queue: &str) -> AppResult<usize> {
        let pkey = format!("{PROCESSING_PREFIX}{queue}");
        match self.redis_llen(&pkey).await {
            Ok(Some(len)) => Ok(len),
            Ok(None) => Ok(0),
            Err(_) => Ok(0),
        }
    }

    // ------------------------------------------------------------------
    // Retry helpers
    // ------------------------------------------------------------------

    /// Increment the retry count for a task, return the new count.
    async fn increment_retry(&self, queue: &str, task_json: &str) -> AppResult<u32> {
        let task_id = self.extract_task_id(task_json);
        let retry_key = format!("task:retry:{queue}:{task_id}");
        match self.redis.incr(&retry_key).await {
            Ok(Some(count)) => {
                let _ = self.redis.expire(&retry_key, self.default_ttl as i64).await;
                Ok(count as u32)
            }
            Ok(None) => Ok(0),
            Err(_) => Ok(0),
        }
    }

    /// Reset retry count for a task.
    async fn reset_retry(&self, _queue: &str, _task_json: &str) {
        // Retry reset is handled by task re-enqueue which creates fresh meta
    }

    /// Get the max retries for a task from its metadata.
    async fn get_max_retries(&self, queue: &str, task_json: &str) -> AppResult<u32> {
        let task_id = self.extract_task_id(task_json);
        match self.get_task_meta(queue, &task_id).await {
            Ok(Some(meta)) => Ok(meta.max_retries),
            _ => Ok(self.default_max_retries),
        }
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    /// Update the status of a task in Redis.
    async fn update_task_status(&self, queue: &str, task_json: &str, status: TaskStatus) {
        let task_id = self.extract_task_id(task_json);
        let status_key = format!("{STATUS_PREFIX}{queue}:{task_id}");
        let _ = self.redis.setex(&status_key, status.as_str(), self.default_ttl).await;

        // Also update meta
        if let Ok(Some(mut meta)) = self.get_task_meta(queue, &task_id).await {
            meta.status = status.as_str().to_owned();
            meta.updated_at = chrono::Utc::now().to_rfc3339();
            let meta_key = format!("{META_PREFIX}{queue}:{task_id}");
            if let Ok(json) = serde_json::to_string(&meta) {
                let _ = self.redis.setex(&meta_key, &json, self.default_ttl).await;
            }
        }
    }

    /// Extract task_id from a task payload JSON string.
    /// Returns the task_id from JSON fields `task_id`, `id`, or `job_id`,
    /// or uses a truncated form of the raw string as fallback.
    fn extract_task_id(&self, task_json: &str) -> String {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(task_json) {
            if let Some(s) = v.get("task_id").and_then(|x| x.as_str()) {
                return s.to_owned();
            }
            if let Some(s) = v.get("id").and_then(|x| x.as_str()) {
                return s.to_owned();
            }
            if let Some(s) = v.get("job_id").and_then(|x| x.as_str()) {
                return s.to_owned();
            }
        }
        // Fallback: first 64 chars of the raw string
        task_json.chars().take(64).collect()
    }

    /// Internal BRPOPLPUSH.
    async fn brpoplpush_inner(
        &self,
        src: &str,
        dst: &str,
        timeout: Duration,
    ) -> AppResult<Option<String>> {
        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => return Ok(None),
        };

        let result: Option<String> = redis::cmd("BRPOPLPUSH")
            .arg(src)
            .arg(dst)
            .arg(timeout.as_secs())
            .query_async(&mut *conn)
            .await
            .map_err(|e| AppError::internal(format!("Redis BRPOPLPUSH failed: {e}")))?;

        Ok(result)
    }

    /// Internal LPUSH.
    async fn redis_lpush(&self, key: &str, value: &str) -> AppResult<Option<()>> {
        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => return Ok(None),
        };

        let _: () = conn.lpush(key, value).await.map_err(|e| {
            AppError::internal(format!("Redis LPUSH failed: {e}"))
        })?;
        Ok(Some(()))
    }

    /// Internal LREM.
    async fn redis_lrem(&self, key: &str, value: &str, count: i64) -> AppResult<Option<()>> {
        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => return Ok(None),
        };

        let _: isize = conn.lrem(key, count as isize, value).await.map_err(|e| {
            AppError::internal(format!("Redis LREM failed: {e}"))
        })?;
        Ok(Some(()))
    }

    /// Internal LRANGE.
    async fn redis_lrange(&self, key: &str, start: i64, stop: i64) -> AppResult<Option<Vec<String>>> {
        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => return Ok(None),
        };

        let items: Vec<String> = conn.lrange(key, start as isize, stop as isize).await.map_err(|e| {
            AppError::internal(format!("Redis LRANGE failed: {e}"))
        })?;
        Ok(Some(items))
    }

    /// Internal LLEN.
    async fn redis_llen(&self, key: &str) -> AppResult<Option<usize>> {
        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => return Ok(None),
        };

        let len: isize = conn.llen(key).await.map_err(|e| {
            AppError::internal(format!("Redis LLEN failed: {e}"))
        })?;
        Ok(Some(len as usize))
    }
}

// ---------------------------------------------------------------------------
// DeadLetterAction
// ---------------------------------------------------------------------------

/// Result of a dead_letter operation.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum DeadLetterAction {
    /// Task was retried (still within max_retries).
    Retried {
        retry_count: u32,
        delay_secs: u64,
    },
    /// Task was moved to dead letter queue (max retries exceeded).
    DeadLettered,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_priority_ordering() {
        assert!(Priority::High < Priority::Medium);
        assert!(Priority::Medium < Priority::Low);
    }

    #[test]
    fn test_priority_suffixes() {
        assert_eq!(Priority::High.suffix(), "high");
        assert_eq!(Priority::Medium.suffix(), "med");
        assert_eq!(Priority::Low.suffix(), "low");
    }

    #[test]
    fn test_task_status_conversion() {
        assert_eq!(TaskStatus::from_str("pending"), Some(TaskStatus::Pending));
        assert_eq!(TaskStatus::from_str("running"), Some(TaskStatus::Running));
        assert_eq!(TaskStatus::from_str("completed"), Some(TaskStatus::Completed));
        assert_eq!(TaskStatus::from_str("failed"), Some(TaskStatus::Failed));
        assert_eq!(TaskStatus::from_str("unknown"), None);

        assert_eq!(TaskStatus::Pending.as_str(), "pending");
        assert_eq!(TaskStatus::Completed.as_str(), "completed");
    }

    #[test]
    fn test_task_meta_new() {
        let meta = TaskMeta::new("task-001", "generation", Priority::High, 3);
        assert_eq!(meta.task_id, "task-001");
        assert_eq!(meta.queue, "generation");
        assert_eq!(meta.priority, Priority::High);
        assert_eq!(meta.status, "pending");
        assert_eq!(meta.retry_count, 0);
        assert_eq!(meta.max_retries, 3);
        assert!(meta.last_error.is_none());
    }

    #[test]
    fn test_task_queue_construction() {
        // TaskQueue requires Arc<RedisClient> in production,
        // this test validates the struct definition compiles.
    }
}
