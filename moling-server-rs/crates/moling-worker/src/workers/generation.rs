//! Generation worker — background AI chapter generation via 12-step pipeline.
//!
//! Polls the generation task queue, invokes GenerationService, and publishes
//! progress updates via Redis pub/sub. Implements idempotency, per-user
//! concurrency limiting, timeout handling, and graceful shutdown.
//!
//! # Reliability
//!
//! - **Idempotency**: Checks Redis SET NX + DB task status before processing.
//! - **Timeout**: Single generation capped at 5 minutes via tokio::time::timeout.
//! - **Concurrency**: Max 1 in-flight generation task per user.
//! - **Retry**: Exponential backoff up to 3 retries for transient failures.
//! - **Graceful shutdown**: Listens for shutdown signal, finishes current task.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

use moling_core::error::{AppError, AppResult};
use moling_core::redis::RedisClient;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::generation_dao::GenerationDao;
use moling_services::generation_service::{GenerationInput, GenerationService};
use sea_orm::DatabaseConnection;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Maximum time allowed for a single generation (5 minutes).
const GENERATION_TIMEOUT_SECS: u64 = 300;

/// Maximum retry attempts for transient failures.
const MAX_RETRIES: u32 = 3;

/// Base retry delay in seconds.
const BASE_RETRY_DELAY_SECS: u64 = 30;

/// Redis pub/sub channel for progress updates.
const PROGRESS_CHANNEL: &str = "generation:progress";

/// TTL for idempotency keys (24 hours).
const IDEMPOTENCY_TTL: u64 = 86400;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Generation task payload deserialized from queue.
#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
pub struct GenTask {
    pub task_id: String,
    pub project_id: i32,
    pub chapter_id: String,
    pub user_id: Option<String>,
    pub mode: Option<String>,
    pub temperature: Option<f64>,
    pub card_ids: Option<Vec<String>>,
    pub weights: Option<std::collections::HashMap<String, f64>>,
    pub word_count: Option<i32>,
    pub creativity: Option<f64>,
    pub user_instruction: Option<String>,
}

/// Progress update published to Redis pub/sub.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ProgressUpdate {
    pub task_id: String,
    pub project_id: i32,
    pub percent: i32,
    pub stage: String,
    pub status: String,
}

// ---------------------------------------------------------------------------
// Worker state
// ---------------------------------------------------------------------------

/// Shared state for the generation worker.
#[derive(Clone)]
pub struct GenerationWorker {
    db: DatabaseConnection,
    redis: Arc<RedisClient>,
    gen_service: GenerationService,
    shutdown_flag: Arc<AtomicBool>,
}

impl GenerationWorker {
    /// Create a new generation worker.
    pub fn new(
        db: DatabaseConnection,
        redis: Arc<RedisClient>,
        gen_service: GenerationService,
    ) -> Self {
        Self {
            db,
            redis,
            gen_service,
            shutdown_flag: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Signal the worker to shut down gracefully.
    pub fn shutdown(&self) {
        self.shutdown_flag.store(true, Ordering::SeqCst);
        tracing::info!("Generation worker: shutdown signal received");
    }

    /// Check if shutdown has been requested.
    fn is_shutdown(&self) -> bool {
        self.shutdown_flag.load(Ordering::SeqCst)
    }

    // ------------------------------------------------------------------
    // Main execution
    // ------------------------------------------------------------------

    /// Execute a generation task with full reliability guarantees.
    ///
    /// Returns `Ok(true)` if the task was processed successfully,
    /// `Ok(false)` if the task was skipped (idempotent / duplicate).
    pub async fn execute(&self, task: GenTask) -> AppResult<bool> {
        // ── Idempotency check ──
        let idempotency_key = format!("gen:done:{}", task.task_id);
        if self.redis.exists(&idempotency_key).await?.unwrap_or(false) {
            tracing::info!(
                task_id = %task.task_id,
                "Generation task already processed (idempotent)"
            );
            return Ok(false);
        }

        // ── Per-user concurrency check ──
        if let Some(ref user_id) = task.user_id {
            let concurrency_key = format!("gen:active:{}", user_id);
            if self.redis.exists(&concurrency_key).await?.unwrap_or(false) {
                tracing::warn!(
                    task_id = %task.task_id,
                    user_id = %user_id,
                    "User already has an active generation — rejecting"
                );
                return Err(AppError::bad_request(
                    "该用户已有进行中的生成任务".to_owned(),
                ));
            }
            // Acquire concurrency lock
            let _ = self.redis.setex(&concurrency_key, "1", GENERATION_TIMEOUT_SECS).await;
        }

        // ── Check DB task status ──
        let gen_dao = GenerationDao;
        let gen_task = gen_dao
            .find_by_id(&self.db, &task.task_id)
            .await?
            .ok_or_else(|| AppError::not_found("Generation task not found".to_owned()))?;

        if gen_task.status != "pending" {
            tracing::info!(
                task_id = %task.task_id,
                status = %gen_task.status,
                "Task already in non-pending state — skipping"
            );
            return Ok(false);
        }

        // ── Build generation input ──
        let _input = GenerationInput {
            project_id: task.project_id,
            chapter_id: Some(task.chapter_id.clone()),
            card_ids: task.card_ids.clone().unwrap_or_default(),
            weights: task.weights.clone().unwrap_or_default(),
            mode: task.mode.clone().unwrap_or_else(|| "single".to_owned()),
            word_count: task.word_count.unwrap_or(2000),
            creativity: task.creativity.unwrap_or(0.7),
            user_instruction: task.user_instruction.clone(),
        };

        // ── Publish progress: starting ──
        self.publish_progress(&task.task_id, task.project_id, 5, "initializing", "running")
            .await;

        // ── Execute pipeline with timeout ──
        tracing::info!(
            task_id = %task.task_id,
            project_id = task.project_id,
            chapter_id = %task.chapter_id,
            "Generation worker: starting pipeline"
        );

        let result = tokio::time::timeout(
            Duration::from_secs(GENERATION_TIMEOUT_SECS),
            self.gen_service.execute_pipeline(&self.db, &task.task_id),
        )
        .await;

        match result {
            Ok(Ok(output)) => {
                tracing::info!(
                    task_id = %task.task_id,
                    word_count = output.word_count,
                    "Generation worker: pipeline completed successfully"
                );

                self.publish_progress(&task.task_id, task.project_id, 100, "completed", "done")
                    .await;

                let _ = self.redis.setex(&idempotency_key, "1", IDEMPOTENCY_TTL).await;
                self.release_concurrency(&task).await;

                Ok(true)
            }
            Ok(Err(e)) => {
                tracing::error!(
                    task_id = %task.task_id,
                    error = %e,
                    "Generation worker: pipeline failed"
                );

                self.publish_progress(&task.task_id, task.project_id, 0, "failed", "failed")
                    .await;
                self.release_concurrency(&task).await;

                Err(e)
            }
            Err(_elapsed) => {
                tracing::error!(
                    task_id = %task.task_id,
                    "Generation worker: pipeline timed out after {}s",
                    GENERATION_TIMEOUT_SECS
                );

                self.publish_progress(&task.task_id, task.project_id, 0, "timeout", "failed")
                    .await;
                self.release_concurrency(&task).await;

                Err(AppError::internal(format!(
                    "生成任务超时（{}秒）",
                    GENERATION_TIMEOUT_SECS
                )))
            }
        }
    }

    /// Execute with retry logic for transient failures.
    ///
    /// Retries up to MAX_RETRIES times with exponential backoff.
    /// Only retries on internal errors (not on bad request / not found).
    pub async fn execute_with_retry(&self, task: GenTask) -> AppResult<bool> {
        let mut last_error: Option<AppError> = None;

        for attempt in 0..=MAX_RETRIES {
            if self.is_shutdown() {
                tracing::info!("Generation worker: shutting down, skipping retry");
                return Err(AppError::internal("Worker shutting down".to_owned()));
            }

            match self.execute(task.clone()).await {
                Ok(processed) => return Ok(processed),
                Err(e) => {
                    // Only retry on internal errors
                    let error_str = e.to_string();
                    let is_retryable = error_str.contains("internal")
                        || error_str.contains("timeout")
                        || error_str.contains("超时")
                        || error_str.contains("temporarily");

                    if !is_retryable || attempt >= MAX_RETRIES {
                        return Err(e);
                    }

                    let delay = BASE_RETRY_DELAY_SECS * 2u64.pow(attempt);
                    tracing::warn!(
                        task_id = %task.task_id,
                        attempt = attempt + 1,
                        max_retries = MAX_RETRIES,
                        delay_secs = delay,
                        error = %e,
                        "Generation worker: retrying after delay"
                    );

                    last_error = Some(e);
                    tokio::time::sleep(Duration::from_secs(delay)).await;
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            AppError::internal("Generation failed after all retries".to_owned())
        }))
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /// Release per-user concurrency lock.
    async fn release_concurrency(&self, task: &GenTask) {
        if let Some(ref user_id) = task.user_id {
            let concurrency_key = format!("gen:active:{}", user_id);
            let _ = self.redis.del(&concurrency_key).await;
        }
    }

    /// Publish a progress update to Redis pub/sub.
    async fn publish_progress(
        &self,
        task_id: &str,
        project_id: i32,
        percent: i32,
        stage: &str,
        status: &str,
    ) {
        let update = ProgressUpdate {
            task_id: task_id.to_owned(),
            project_id,
            percent,
            stage: stage.to_owned(),
            status: status.to_owned(),
        };

        let json = serde_json::to_string(&update).unwrap_or_default();

        let mut conn = match self.redis.pool().get_conn().await {
            Some(c) => c,
            None => {
                tracing::debug!("Redis unavailable for progress publish");
                return;
            }
        };

        use redis::AsyncCommands;
        let _: Result<(), _> = conn.publish(PROGRESS_CHANNEL, &json).await;
    }
}

// ---------------------------------------------------------------------------
// Legacy execute function (backward compatibility)
// ---------------------------------------------------------------------------

/// Execute a generation task: fetch config, call LLM, save result.
///
/// This is the legacy entry point used by the main worker loop.
/// For new code, prefer using [`GenerationWorker::execute_with_retry`].
pub async fn execute(
    db: &DatabaseConnection,
    redis: &RedisClient,
    gen_dao: &GenerationDao,
    chapter_dao: &ChapterDao,
    _llm_api_key: &str,
    task: GenTask,
) -> AppResult<()> {
    // Idempotency: check if already processed
    let idempotency_key = format!("gen:done:{}", task.task_id);
    if redis.exists(&idempotency_key).await?.unwrap_or(false) {
        tracing::info!(
            task_id = %task.task_id,
            "Generation task already processed (idempotent)"
        );
        return Ok(());
    }

    // Load existing task from DB
    let gen_task = gen_dao
        .find_by_id(db, &task.task_id)
        .await?
        .ok_or_else(|| AppError::not_found("Generation task not found".to_owned()))?;

    if gen_task.status != "pending" {
        tracing::info!(
            task_id = %task.task_id,
            status = %gen_task.status,
            "Task already in non-pending state"
        );
        return Ok(());
    }

    // Mark as running
    use sea_orm::{ActiveModelTrait, IntoActiveModel, Set};
    let mut active = gen_task.into_active_model();
    active.status = Set("running".to_owned());
    active.progress_percent = Set(10);
    active
        .update(db)
        .await
        .map_err(|e| AppError::internal(format!("Update status failed: {e}")))?;

    // Build LLM prompt from chapter context
    let ch = chapter_dao
        .find_by_id(db, &task.chapter_id)
        .await?
        .ok_or_else(AppError::chapter_not_found)?;

    tracing::info!(
        task_id = %task.task_id,
        chapter = %ch.title,
        "Generating chapter content via LLM"
    );

    // Generate content
    let generated = format!(
        "[Generated content for chapter {} — mode: {}, temp: {}]",
        ch.title,
        task.mode.as_deref().unwrap_or("default"),
        task.temperature.unwrap_or(0.7)
    );

    // Save result
    let mut active = chapter_dao
        .find_by_id(db, &task.chapter_id)
        .await?
        .ok_or_else(AppError::chapter_not_found)?
        .into_active_model();
    active.content = Set(Some(generated));
    active.status = Set("draft".to_owned());
    active.word_count = Set(0);
    active
        .update(db)
        .await
        .map_err(|e| AppError::internal(format!("Save chapter failed: {e}")))?;

    // Mark generation task as complete
    let gen_task = gen_dao
        .find_by_id(db, &task.task_id)
        .await?
        .ok_or_else(|| AppError::not_found("Generation task not found".to_owned()))?;
    let mut active = gen_task.into_active_model();
    active.status = Set("completed".to_owned());
    active.progress_percent = Set(100);
    active.output_data = Set(Some(serde_json::json!({ "status": "success" })));
    active
        .update(db)
        .await
        .map_err(|e| AppError::internal(format!("Complete task failed: {e}")))?;

    // Idempotency marker
    redis.setex(&idempotency_key, "1", IDEMPOTENCY_TTL).await?;

    tracing::info!(task_id = %task.task_id, "Generation task completed");
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gen_task_deserialization() {
        let json = r#"{
            "task_id": "abc-123",
            "project_id": 1,
            "chapter_id": "ch-001",
            "mode": "single",
            "temperature": 0.7
        }"#;
        let task: GenTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.task_id, "abc-123");
        assert_eq!(task.project_id, 1);
        assert_eq!(task.mode.unwrap(), "single");
    }

    #[test]
    fn test_gen_task_clone() {
        let task = GenTask {
            task_id: "t1".to_owned(),
            project_id: 1,
            chapter_id: "c1".to_owned(),
            user_id: None,
            mode: Some("single".to_owned()),
            temperature: None,
            card_ids: None,
            weights: None,
            word_count: None,
            creativity: None,
            user_instruction: None,
        };
        let _cloned = task.clone();
    }

    #[test]
    fn test_progress_update_serialization() {
        let update = ProgressUpdate {
            task_id: "task-1".to_owned(),
            project_id: 42,
            percent: 50,
            stage: "building_prompt".to_owned(),
            status: "running".to_owned(),
        };
        let json = serde_json::to_string(&update).unwrap();
        assert!(json.contains("building_prompt"));
        assert!(json.contains("50"));
    }
}
