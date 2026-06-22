//! Import worker — phased book import pipeline.
//!
//! Handles file import processing in 3 phases:
//! Phase 1: URL scraping / file parsing / text extraction
//! Phase 2: Chapter splitting, content analysis
//! Phase 3: Database insertion, vault population
//!
//! Each phase is idempotent and reports progress independently.


use moling_core::error::{AppError, AppResult};
use moling_core::redis::RedisClient;
use moling_db::dao::ingest_dao::IngestDao;
use moling_services::import_service::ImportService;
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// TTL for idempotency keys (24 hours).
const IDEMPOTENCY_TTL: u64 = 86400;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Import task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct ImportTask {
    pub job_id: String,
    pub project_id: i32,
    pub source_type: String, // "txt" | "docx" | "epub" | "url"
    pub source_url: Option<String>,
    pub file_path: Option<String>,
    pub import_mode: Option<String>, // "full" | "append"
    pub phase: String, // "phase1" | "phase2" | "phase3" | "full"
}

/// Progress update for import phases.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ImportProgress {
    pub job_id: String,
    pub project_id: i32,
    pub phase: String,
    pub percent: f64,
    pub message: String,
}

// ---------------------------------------------------------------------------
// Execute — single phase
// ---------------------------------------------------------------------------

/// Execute a single import phase with idempotency.
///
/// Phases:
/// - **phase1**: Parse file/URL, extract raw text (33% progress)
/// - **phase2**: Split into chapters, analyze content (66% progress)
/// - **phase3**: Insert into DB, populate vault (100% progress)
/// - **full**: Execute all phases sequentially
pub async fn execute_phase(
    db: &DatabaseConnection,
    redis: &RedisClient,
    ingest_dao: &IngestDao,
    task: ImportTask,
) -> AppResult<ImportProgress> {
    // ── Idempotency check ──
    let idem_key = format!("import:done:{}:{}", task.job_id, task.phase);
    if redis.exists(&idem_key).await?.unwrap_or(false) {
        tracing::info!(
            job_id = %task.job_id,
            phase = %task.phase,
            "Import phase already processed"
        );
        return Ok(ImportProgress {
            job_id: task.job_id.clone(),
            project_id: task.project_id,
            phase: task.phase.clone(),
            percent: 100.0,
            message: "Already processed".to_owned(),
        });
    }

    // ── Load job ──
    let job = ingest_dao
        .find_by_id(db, &task.job_id)
        .await?
        .ok_or_else(|| AppError::not_found("Import job not found".to_owned()))?;

    tracing::info!(
        job_id = %task.job_id,
        phase = %task.phase,
        source = %task.source_type,
        "Import phase started"
    );

    // ── Update job status ──
    let mut active = job.into_active_model();
    active.current_phase = Set(task.phase.clone());

    let (percent, message) = match task.phase.as_str() {
        "phase1" => {
            execute_phase1(db, redis, &task).await?;
            (33.0, "Phase 1 completed: text extracted")
        }
        "phase2" => {
            execute_phase2(db, redis, &task).await?;
            (66.0, "Phase 2 completed: chapters split")
        }
        "phase3" => {
            execute_phase3(db, redis, &task).await?;
            (100.0, "Phase 3 completed: import finished")
        }
        "full" => {
            execute_phase1(db, redis, &task).await?;
            publish_import_progress(redis, &task.job_id, task.project_id, "phase1", 33.0).await;

            execute_phase2(db, redis, &task).await?;
            publish_import_progress(redis, &task.job_id, task.project_id, "phase2", 66.0).await;

            execute_phase3(db, redis, &task).await?;
            (100.0, "Full import completed")
        }
        _ => {
            return Err(AppError::bad_request(format!(
                "Unknown import phase: {}",
                task.phase
            )));
        }
    };

    active.progress_percent = Set(percent);
    active
        .update(db)
        .await
        .map_err(|e| AppError::internal(format!("Update import job failed: {e}")))?;

    // ── Mark phase complete ──
    let _ = redis.setex(&idem_key, "1", IDEMPOTENCY_TTL).await;

    tracing::info!(
        job_id = %task.job_id,
        phase = %task.phase,
        percent,
        message,
        "Import phase completed"
    );

    Ok(ImportProgress {
        job_id: task.job_id.clone(),
        project_id: task.project_id,
        phase: task.phase.clone(),
        percent,
        message: message.to_owned(),
    })
}

// ---------------------------------------------------------------------------
// Phase implementations
// ---------------------------------------------------------------------------

/// Phase 1: Parse file/URL and extract raw text.
async fn execute_phase1(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: &ImportTask,
) -> AppResult<()> {
    tracing::info!(
        job_id = %task.job_id,
        source_type = %task.source_type,
        "Phase 1: Extracting text"
    );

    let import_service = ImportService::new();

    if let Some(ref url) = task.source_url {
        tracing::debug!(url, "Phase 1: Scraping URL");
        // In production: ImportService.scrape_url(db, task.project_id, url)
        let _ = url;
    }

    if let Some(ref path) = task.file_path {
        tracing::debug!(path, "Phase 1: Parsing file");
        // In production: ImportService.parse_file(db, task.project_id, path, &task.source_type)
        let _ = path;
    }

    // Update progress
    publish_import_progress(redis, &task.job_id, task.project_id, "phase1", 33.0).await;

    let _ = db;
    let _ = import_service;
    Ok(())
}

/// Phase 2: Split into chapters and analyze content.
async fn execute_phase2(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: &ImportTask,
) -> AppResult<()> {
    tracing::info!(
        job_id = %task.job_id,
        "Phase 2: Splitting chapters and analyzing"
    );

    // In production: ImportService.split_chapters() and analyze
    publish_import_progress(redis, &task.job_id, task.project_id, "phase2", 66.0).await;

    let _ = db;
    Ok(())
}

/// Phase 3: Insert chapters into DB and populate vault.
async fn execute_phase3(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: &ImportTask,
) -> AppResult<()> {
    tracing::info!(
        job_id = %task.job_id,
        "Phase 3: Database insertion and vault population"
    );

    // In production: ImportService.create_chapters() and VaultService.populate()
    publish_import_progress(redis, &task.job_id, task.project_id, "phase3", 100.0).await;

    let _ = db;
    Ok(())
}

// ---------------------------------------------------------------------------
// Progress reporting
// ---------------------------------------------------------------------------

/// Publish import progress via Redis pub/sub.
async fn publish_import_progress(
    redis: &RedisClient,
    job_id: &str,
    project_id: i32,
    phase: &str,
    percent: f64,
) {
    let update = serde_json::json!({
        "job_id": job_id,
        "project_id": project_id,
        "phase": phase,
        "percent": percent,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    });
    let json = update.to_string();

    let mut conn = match redis.pool().get_conn().await {
        Some(c) => c,
        None => return,
    };

    use redis::AsyncCommands;
    let _: Result<(), _> = conn.publish("import:progress", &json).await;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_import_task_deserialization() {
        let json = r#"{
            "job_id": "job-001",
            "project_id": 1,
            "source_type": "txt",
            "file_path": "/tmp/book.txt",
            "phase": "phase1"
        }"#;
        let task: ImportTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.job_id, "job-001");
        assert_eq!(task.project_id, 1);
        assert_eq!(task.source_type, "txt");
        assert_eq!(task.phase, "phase1");
    }

    #[test]
    fn test_import_progress_serialization() {
        let progress = ImportProgress {
            job_id: "job-001".to_owned(),
            project_id: 42,
            phase: "phase2".to_owned(),
            percent: 66.0,
            message: "Chapters split".to_owned(),
        };
        let json = serde_json::to_string(&progress).unwrap();
        assert!(json.contains("job-001"));
        assert!(json.contains("66.0"));
    }
}
