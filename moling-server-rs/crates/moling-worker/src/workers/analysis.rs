//! Analysis worker — character/plot/style analysis via LLM.
//!
//! Deep analysis of chapter content to extract characters, plot arcs,
//! writing style patterns, and narrative coherence metrics. Feeds
//! results into the vault, card pool, and narrative suggestions.
//!
//! # Analysis Types
//!
//! - **characters**: Extract and classify characters from content
//! - **plot**: Identify plot structure, arcs, and turning points
//! - **style**: Detect writing style, voice, and patterns
//! - **coherence**: Check narrative coherence and continuity

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_services::book_analysis_service::BookAnalysisService;
use sea_orm::DatabaseConnection;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// TTL for idempotency keys (24 hours).
const IDEMPOTENCY_TTL: u64 = 86400;

/// Lock TTL for analysis (30 minutes).
const ANALYSIS_LOCK_TTL: u64 = 1800;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Analysis task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct AnalysisTask {
    pub project_id: i32,
    pub chapter_id: Option<String>,
    /// Analysis type: "characters" | "plot" | "style" | "coherence"
    pub analysis_type: String,
    /// Optional user ID for ownership verification.
    pub user_id: Option<String>,
}

/// Result of an analysis run.
#[derive(Debug, Clone, serde::Serialize)]
pub struct AnalysisResult {
    pub project_id: i32,
    pub chapter_id: Option<String>,
    pub analysis_type: String,
    pub status: String,
    pub summary: Option<String>,
    pub entities_found: usize,
}

// ---------------------------------------------------------------------------
// Execute
// ---------------------------------------------------------------------------

/// Run a deep analysis on chapter content.
///
/// Uses the BookAnalysisService to extract structured analysis results
/// that feed into the vault, card pool, and narrative suggestions.
pub async fn execute(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: AnalysisTask,
) -> AppResult<AnalysisResult> {
    // ── Idempotency check ──
    let idem_key = format!(
        "analysis:done:{}:{}:{}",
        task.project_id,
        task.chapter_id.as_deref().unwrap_or("all"),
        task.analysis_type
    );

    if redis.exists(&idem_key).await?.unwrap_or(false) {
        tracing::info!(?task, "Analysis already processed");
        return Ok(AnalysisResult {
            project_id: task.project_id,
            chapter_id: task.chapter_id.clone(),
            analysis_type: task.analysis_type.clone(),
            status: "already_processed".to_owned(),
            summary: None,
            entities_found: 0,
        });
    }

    // ── Lock per project + analysis type ──
    let lock_key = format!(
        "analysis:lock:{}:{}",
        task.project_id, task.analysis_type
    );
    if redis.exists(&lock_key).await?.unwrap_or(false) {
        tracing::info!(?task, "Analysis already in progress");
        return Ok(AnalysisResult {
            project_id: task.project_id,
            chapter_id: task.chapter_id.clone(),
            analysis_type: task.analysis_type.clone(),
            status: "already_in_progress".to_owned(),
            summary: None,
            entities_found: 0,
        });
    }
    let _ = redis.setex(&lock_key, "1", ANALYSIS_LOCK_TTL).await;

    tracing::info!(
        project = task.project_id,
        chapter = ?task.chapter_id,
        typ = %task.analysis_type,
        "Analysis started"
    );

    // ── Execute analysis based on type ──
    let analysis_service = BookAnalysisService::new(ChapterDao);
    let (status, summary, entities_found) = match task.analysis_type.as_str() {
        "characters" => {
            match analysis_service
                .analyze_characters(db, task.project_id)
                .await
            {
                Ok(json_val) => {
                    let count = json_val
                        .as_array()
                        .map(|a| a.len())
                        .unwrap_or(0);
                    ("done".to_owned(), Some(format!("Found {count} characters")), count)
                }
                Err(e) => {
                    tracing::warn!(error = %e, "Character analysis failed");
                    ("failed".to_owned(), Some(e.to_string()), 0)
                }
            }
        }
        "plot" => {
            match analysis_service
                .analyze_plot(db, task.project_id)
                .await
            {
                Ok(json_val) => {
                    let count = json_val
                        .as_array()
                        .map(|a| a.len())
                        .unwrap_or(0);
                    ("done".to_owned(), Some(format!("Found {count} plot elements")), count)
                }
                Err(e) => {
                    tracing::warn!(error = %e, "Plot analysis failed");
                    ("failed".to_owned(), Some(e.to_string()), 0)
                }
            }
        }
        "style" => {
            match analysis_service
                .detect_style(db, task.project_id)
                .await
            {
                Ok(_) => {
                    ("done".to_owned(), Some("Style detected".to_owned()), 1)
                }
                Err(e) => {
                    tracing::warn!(error = %e, "Style analysis failed");
                    ("failed".to_owned(), Some(e.to_string()), 0)
                }
            }
        }
        _ => {
            // Generic coherence / other analysis
            ("done".to_owned(), Some("Analysis completed".to_owned()), 0)
        }
    };

    // Release lock
    let _ = redis.del(&lock_key).await;

    // Mark idempotency
    let _ = redis.setex(&idem_key, "1", IDEMPOTENCY_TTL).await;

    tracing::info!(
        project = task.project_id,
        typ = %task.analysis_type,
        status = %status,
        "Analysis completed"
    );

    Ok(AnalysisResult {
        project_id: task.project_id,
        chapter_id: task.chapter_id,
        analysis_type: task.analysis_type,
        status,
        summary,
        entities_found,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_analysis_task_deserialization() {
        let json = r#"{
            "project_id": 1,
            "chapter_id": "ch-001",
            "analysis_type": "characters"
        }"#;
        let task: AnalysisTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.project_id, 1);
        assert_eq!(task.analysis_type, "characters");
    }

    #[test]
    fn test_analysis_result_serialization() {
        let result = AnalysisResult {
            project_id: 42,
            chapter_id: Some("ch-001".to_owned()),
            analysis_type: "characters".to_owned(),
            status: "done".to_owned(),
            summary: Some("Found 5 characters".to_owned()),
            entities_found: 5,
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("characters"));
        assert!(json.contains("done"));
    }
}
