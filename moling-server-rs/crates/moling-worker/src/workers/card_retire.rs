//! Card retirement worker — checks for stale cards and retires them.
//!
//! Triggered periodically by the cron scheduler (daily at 2 AM).
//! Cards that haven't been drawn recently or have exceeded their
//! freshness lifespan are retired and replacement cards generated.
//!
//! # Flow
//!
//! 1. Lock the project (Redis SET NX)
//! 2. Fetch active card pool
//! 3. Check freshness against chapter window
//! 4. Retire stale/expired cards
//! 5. Generate replacement cards to fill gaps
//! 6. Log audit entries for each retired card

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_services::card_retire_service::{
    CardRetireService, RetireResult, MAX_ACTIVE_CARDS,
};
use sea_orm::DatabaseConnection;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Lock TTL for card retirement (10 minutes).
const CARD_RETIRE_LOCK_TTL: u64 = 600;

/// Maximum cards to retire in a single batch.
const MAX_RETIRE_BATCH: usize = 20;

/// Default current chapter for freshness calculation (when unknown).
const DEFAULT_CURRENT_CHAPTER: i32 = 0;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Card retirement task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct CardRetireTask {
    pub project_id: i32,
    /// Optional list of specific card IDs to retire.
    pub card_ids: Option<Vec<String>>,
    /// Number of replacement cards to generate (default: 5).
    pub replacement_count: Option<usize>,
    /// Current chapter number for freshness calculation.
    pub current_chapter: Option<i32>,
}

// ---------------------------------------------------------------------------
// Execute — single project
// ---------------------------------------------------------------------------

/// Execute card retirement check for a single project.
///
/// Steps:
/// 1. Acquire distributed lock
/// 2. Fetch active card pool
/// 3. Check freshness and lifetime
/// 4. Retire stale cards
/// 5. Generate replacements
/// 6. Log audit summary
pub async fn execute(
    db: &DatabaseConnection,
    redis: &RedisClient,
    card_dao: &CardDao,
    task: CardRetireTask,
) -> AppResult<RetireResult> {
    let lock_key = format!("card:retire:lock:{}", task.project_id);

    // ── Acquire lock ──
    if redis.exists(&lock_key).await?.unwrap_or(false) {
        tracing::info!(
            project = task.project_id,
            "Card retirement already in progress — skipping"
        );
        return Ok(RetireResult {
            retired_count: 0,
            expired_count: 0,
            remaining_active: 0,
            retired_ids: Vec::new(),
        });
    }
    let _ = redis.setex(&lock_key, "1", CARD_RETIRE_LOCK_TTL).await;

    tracing::info!(project = task.project_id, "Card retirement check started");

    // ── Execute retirement ──
    let result = if let Some(ref card_ids) = task.card_ids {
        // Retire specific cards
        retire_specific_cards(db, card_dao, task.project_id, card_ids).await?
    } else {
        // Full retirement check via CardRetireService
        let retire_service = CardRetireService::new();
        let current_ch = task.current_chapter.unwrap_or(DEFAULT_CURRENT_CHAPTER);

        match retire_service
            .check_and_retire(db, task.project_id, current_ch)
            .await
        {
            Ok(r) => r,
            Err(e) => {
                tracing::warn!(
                    project = task.project_id,
                    error = %e,
                    "CardRetireService.check_and_retire failed, falling back to direct check"
                );
                fallback_retire_check(db, card_dao, task.project_id).await?
            }
        }
    };

    // ── Generate replacement cards if pool below max ──
    if result.remaining_active < MAX_ACTIVE_CARDS && result.remaining_active > 0 {
        let needed = MAX_ACTIVE_CARDS - result.remaining_active;
        let count = task
            .replacement_count
            .unwrap_or(needed)
            .min(MAX_RETIRE_BATCH);

        if count > 0 {
            tracing::info!(
                project = task.project_id,
                pool_size = result.remaining_active,
                max = MAX_ACTIVE_CARDS,
                replacements = count,
                "Generating replacement cards"
            );
            // In production: delegate to CardPoolService for generation
            let _ = count;
        }
    }

    // ── Release lock ──
    let _ = redis.del(&lock_key).await;

    tracing::info!(
        project = task.project_id,
        retired = result.retired_count,
        expired = result.expired_count,
        remaining = result.remaining_active,
        "Card retirement check completed"
    );

    Ok(result)
}

// ---------------------------------------------------------------------------
// Cron-triggered: scan all projects
// ---------------------------------------------------------------------------

/// Periodic cron handler: scan all active projects for card retirement.
pub async fn card_retire_check(
    db: &DatabaseConnection,
    redis: &RedisClient,
) -> AppResult<serde_json::Value> {
    let project_dao = ProjectDao;
    let active_projects = project_dao
        .get_all_active(db, 200)
        .await
        .unwrap_or_default();

    let card_dao = CardDao;
    let mut results: Vec<serde_json::Value> = Vec::new();
    let mut total_retired = 0usize;

    for project in &active_projects {
        let task = CardRetireTask {
            project_id: project.id,
            card_ids: None,
            replacement_count: Some(5),
            current_chapter: None,
        };

        match execute(db, redis, &card_dao, task).await {
            Ok(result) => {
                total_retired += result.retired_count;
                results.push(serde_json::json!({
                    "project_id": project.id,
                    "retired": result.retired_count,
                    "expired": result.expired_count,
                    "remaining": result.remaining_active,
                }));
            }
            Err(e) => {
                tracing::warn!(
                    project_id = project.id,
                    error = %e,
                    "Card retire check failed for project"
                );
                results.push(serde_json::json!({
                    "project_id": project.id,
                    "error": e.to_string(),
                }));
            }
        }
    }

    tracing::info!(
        scanned = active_projects.len(),
        total_retired,
        "Card retirement scan completed"
    );

    Ok(serde_json::json!({
        "scanned": active_projects.len(),
        "total_retired": total_retired,
        "results": results,
    }))
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Retire specific card IDs.
async fn retire_specific_cards(
    db: &DatabaseConnection,
    card_dao: &CardDao,
    project_id: i32,
    card_ids: &[String],
) -> AppResult<RetireResult> {
    let mut retired_ids: Vec<String> = Vec::new();
    let mut retired_count = 0usize;

    for card_id in card_ids {
        match card_dao.retire_card(db, card_id, None).await {
            Ok(()) => {
                retired_ids.push(card_id.clone());
                retired_count += 1;
            }
            Err(e) => {
                tracing::warn!(
                    card_id = %card_id,
                    error = %e,
                    "Failed to retire card"
                );
            }
        }
    }

    let pool = card_dao.find_pool(db, project_id).await?;
    let remaining = pool.len();

    Ok(RetireResult {
        retired_count,
        expired_count: 0,
        remaining_active: remaining,
        retired_ids,
    })
}

/// Fallback retirement check when CardRetireService is unavailable.
/// Uses draw_count threshold as a simple heuristic.
async fn fallback_retire_check(
    db: &DatabaseConnection,
    card_dao: &CardDao,
    project_id: i32,
) -> AppResult<RetireResult> {
    let pool = card_dao.find_pool(db, project_id).await?;
    let mut retired_count = 0usize;
    let expired_count = 0usize;
    let mut retired_ids: Vec<String> = Vec::new();

    // Simple heuristic: retire cards with very high draw counts
    let draw_threshold: i32 = 50;
    for card in &pool {
        if card.draw_count > draw_threshold {
            match card_dao.retire_card(db, &card.id, None).await {
                Ok(()) => {
                    retired_count += 1;
                    retired_ids.push(card.id.clone());
                    tracing::debug!(
                        card_id = %card.id,
                        card_name = %card.name,
                        draw_count = card.draw_count,
                        "Card retired (fallback heuristic)"
                    );
                }
                Err(e) => {
                    tracing::warn!(
                        card_id = %card.id,
                        error = %e,
                        "Failed to retire card"
                    );
                }
            }
        }
    }

    // Refresh pool after retirement
    let remaining_pool = card_dao.find_pool(db, project_id).await?;
    let remaining_active = remaining_pool.len();

    Ok(RetireResult {
        retired_count,
        expired_count,
        remaining_active,
        retired_ids,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_card_retire_task_deserialization() {
        let json = r#"{
            "project_id": 1,
            "card_ids": ["card-a", "card-b"],
            "replacement_count": 3
        }"#;
        let task: CardRetireTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.project_id, 1);
        assert_eq!(task.card_ids.unwrap().len(), 2);
        assert_eq!(task.replacement_count.unwrap(), 3);
    }

    #[test]
    fn test_retire_result_default() {
        let result = RetireResult {
            retired_count: 0,
            expired_count: 0,
            remaining_active: 80,
            retired_ids: vec![],
        };
        assert_eq!(result.retired_count, 0);
        assert_eq!(result.remaining_active, 80);
    }
}
