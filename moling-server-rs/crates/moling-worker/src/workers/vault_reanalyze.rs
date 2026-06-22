//! Vault reanalysis worker — periodic full-vault reanalysis.
//!
//! Triggered by the cron scheduler (every 6 hours) or manually.
//! Runs vault update on all chapters to refresh vault entries
//! (characters, timeline events, plot promises, world entries).
//!
//! # Flow
//!
//! 1. Acquire distributed lock (Redis SET NX, 30min TTL)
//! 2. Fetch all chapters for the project
//! 3. For each chapter, run VaultService.update_from_chapter()
//! 4. Track created/updated/total entity counts
//! 5. Release lock

use moling_core::error::{AppError, AppResult};
use moling_core::redis::RedisClient;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_services::vault_service::VaultService;
use sea_orm::DatabaseConnection;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Lock TTL for vault reanalysis (30 minutes).
const VAULT_REANALYZE_LOCK_TTL: u64 = 1800;

/// Maximum chapters to process in a single reanalysis run.
const MAX_CHAPTERS: u64 = 200;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Vault reanalysis task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct VaultReanalyzeTask {
    pub project_id: i32,
    pub trigger: String, // "cron" | "manual"
    pub user_id: Option<String>,
}

/// Summary of a reanalysis run.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ReanalyzeSummary {
    pub project_id: i32,
    pub total_chapters: usize,
    pub total_created: usize,
    pub total_updated: usize,
    pub total_entities: usize,
    pub chapter_results: Vec<serde_json::Value>,
}

// ---------------------------------------------------------------------------
// Execute — single project
// ---------------------------------------------------------------------------

/// Execute a full vault reanalysis for a project.
///
/// Steps:
/// 1. Lock the project (Redis SET NX, 30min TTL)
/// 2. Fetch all chapters
/// 3. Run VaultService.update_from_chapter() on each
/// 4. Merge results into vault
/// 5. Release lock
pub async fn execute(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: VaultReanalyzeTask,
) -> AppResult<ReanalyzeSummary> {
    let lock_key = format!("vault:reanalyze:lock:{}", task.project_id);

    // ── Idempotency: only one reanalysis per project at a time ──
    if redis.exists(&lock_key).await?.unwrap_or(false) {
        tracing::info!(
            project = task.project_id,
            "Vault reanalysis already in progress"
        );
        return Ok(ReanalyzeSummary {
            project_id: task.project_id,
            total_chapters: 0,
            total_created: 0,
            total_updated: 0,
            total_entities: 0,
            chapter_results: vec![],
        });
    }

    // ── Acquire lock ──
    let _ = redis.setex(&lock_key, "1", VAULT_REANALYZE_LOCK_TTL).await;

    tracing::info!(
        project = task.project_id,
        trigger = %task.trigger,
        "Vault reanalysis started"
    );

    // ── Verify project exists ──
    let project_dao = ProjectDao;
    let _project = project_dao
        .find_by_id(db, task.project_id)
        .await?
        .ok_or_else(AppError::project_not_found)?;

    // ── Fetch all chapters ──
    let chapter_dao = ChapterDao;
    let chapters = chapter_dao
        .list_by_project(db, task.project_id, 0, MAX_CHAPTERS)
        .await?;

    if chapters.is_empty() {
        tracing::info!(
            project = task.project_id,
            "No chapters found — nothing to reanalyze"
        );
        let _ = redis.del(&lock_key).await;
        return Ok(ReanalyzeSummary {
            project_id: task.project_id,
            total_chapters: 0,
            total_created: 0,
            total_updated: 0,
            total_entities: 0,
            chapter_results: vec![],
        });
    }

    // ── Process each chapter ──
    let user_id = task.user_id.as_deref().unwrap_or("system");
    let vault_service = VaultService::new();
    let mut total_created = 0usize;
    let mut total_updated = 0usize;
    let mut total_entities = 0usize;
    let mut chapter_results: Vec<serde_json::Value> = Vec::new();

    for chapter in &chapters {
        match vault_service
            .update_from_chapter(db, user_id, task.project_id, &chapter.id)
            .await
        {
            Ok(result) => {
                total_created += result.created;
                total_updated += result.updated;
                total_entities += result.total_entities;

                chapter_results.push(serde_json::json!({
                    "chapter_id": chapter.id,
                    "chapter_number": chapter.chapter_number,
                    "created": result.created,
                    "updated": result.updated,
                    "entities": result.total_entities,
                }));
            }
            Err(e) => {
                tracing::warn!(
                    chapter_id = %chapter.id,
                    error = %e,
                    "Failed to reanalyze chapter"
                );
                chapter_results.push(serde_json::json!({
                    "chapter_id": chapter.id,
                    "chapter_number": chapter.chapter_number,
                    "error": e.to_string(),
                }));
            }
        }
    }

    // ── Release lock ──
    let _ = redis.del(&lock_key).await;

    tracing::info!(
        project = task.project_id,
        total_chapters = chapters.len(),
        total_created,
        total_updated,
        "Vault reanalysis completed"
    );

    Ok(ReanalyzeSummary {
        project_id: task.project_id,
        total_chapters: chapters.len(),
        total_created,
        total_updated,
        total_entities,
        chapter_results,
    })
}

// ---------------------------------------------------------------------------
// Cron-triggered: scan all recently active projects
// ---------------------------------------------------------------------------

/// Periodic cron handler: scan recently active projects and trigger reanalysis.
pub async fn vault_periodic_reanalyze(
    db: &DatabaseConnection,
    redis: &RedisClient,
) -> AppResult<serde_json::Value> {
    let project_dao = ProjectDao;

    // Find projects active in the last 6 hours
    let recent_projects = project_dao
        .get_recently_active(db, 6, 200)
        .await
        .unwrap_or_default();

    let mut triggered = 0usize;

    for project in &recent_projects {
        let task = VaultReanalyzeTask {
            project_id: project.id,
            trigger: "cron".to_owned(),
            user_id: Some("system".to_owned()),
        };

        match execute(db, redis, task).await {
            Ok(summary) => {
                tracing::info!(
                    project_id = project.id,
                    chapters = summary.total_chapters,
                    created = summary.total_created,
                    "Vault periodic reanalyze: project processed"
                );
                triggered += 1;
            }
            Err(e) => {
                tracing::warn!(
                    project_id = project.id,
                    error = %e,
                    "Vault periodic reanalyze: failed for project"
                );
            }
        }
    }

    tracing::info!(
        scanned = recent_projects.len(),
        triggered,
        "Vault periodic reanalyze completed"
    );

    Ok(serde_json::json!({
        "scanned": recent_projects.len(),
        "triggered": triggered,
    }))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_reanalyze_task_deserialization() {
        let json = r#"{
            "project_id": 42,
            "trigger": "manual",
            "user_id": "user-abc"
        }"#;
        let task: VaultReanalyzeTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.project_id, 42);
        assert_eq!(task.trigger, "manual");
        assert_eq!(task.user_id.unwrap(), "user-abc");
    }

    #[test]
    fn test_reanalyze_summary_serialization() {
        let summary = ReanalyzeSummary {
            project_id: 1,
            total_chapters: 10,
            total_created: 5,
            total_updated: 3,
            total_entities: 8,
            chapter_results: vec![],
        };
        let json = serde_json::to_string(&summary).unwrap();
        assert!(json.contains("10"));
        assert!(json.contains("5"));
    }
}
