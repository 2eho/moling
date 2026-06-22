//! Health notification worker — periodic health monitoring and alerting.
//!
//! Checks database connectivity, Redis connectivity, and project health
//! metrics (R1/R2/R3). Creates HealthAlert records for detected issues.
//!
//! # Schedule
//!
//! Triggered by the cron scheduler every 10 minutes.
//! For each active project, runs health checks and generates alerts.
//!
//! # R1/R2/R3 Rules
//!
//! - **R1**: Character consistency — characters appearing/disappearing without cause
//! - **R2**: Timeline continuity — events out of order or missing transitions
//! - **R3**: Plot promise debt — promises left unfulfilled beyond window

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use moling_db::dao::health_alert_dao::HealthAlertDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_services::health_monitor::{HealthMonitorService};
use moling_services::health_service::HealthService;
use sea_orm::{DatabaseConnection, Set};

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Health check task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct HealthNotifyTask {
    /// Optional project ID to scope the check.
    pub project_id: Option<i32>,
    /// Run specific checks (e.g. ["R1", "R2"]). Empty = all.
    pub checks: Option<Vec<String>>,
    /// Current chapter number for freshness-based checks.
    pub current_chapter: Option<i32>,
}

/// Result of a health check on a single project.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ProjectHealthResult {
    pub project_id: i32,
    pub project_title: String,
    pub db_ok: bool,
    pub redis_ok: bool,
    pub alerts: Vec<serde_json::Value>,
    pub alert_count: usize,
}

// ---------------------------------------------------------------------------
// Execute — single project
// ---------------------------------------------------------------------------

/// Execute a health check for a single project and create alerts.
pub async fn execute(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: HealthNotifyTask,
) -> AppResult<ProjectHealthResult> {
    let project_id = task.project_id.unwrap_or(0);

    // ── Infrastructure checks ──
    let health_service = HealthService::new();
    let db_ok = health_service.check_db(db).await.unwrap_or(false);
    let redis_ok = health_service.check_redis(redis.pool());

    if !db_ok {
        tracing::warn!("Health check: database connectivity lost");
    }
    if !redis_ok {
        tracing::warn!("Health check: Redis unavailable");
    }

    // ── Project-specific checks ──
    let mut alerts: Vec<serde_json::Value> = Vec::new();
    let mut project_title = String::new();

    if project_id > 0 {
        // Load project
        let project_dao = ProjectDao;
        if let Ok(Some(project)) = project_dao.find_by_id(db, project_id).await {
            project_title = project.title.clone();

            // Run R1/R2/R3 via HealthMonitorService
            let checks_to_run = task.checks.clone().unwrap_or_default();

            if checks_to_run.is_empty()
                || checks_to_run.iter().any(|c| c == "R1" || c == "R2" || c == "R3")
            {
                match run_health_monitor_check(db, project_id, task.current_chapter).await {
                    Ok(project_alerts) => alerts.extend(project_alerts),
                    Err(e) => tracing::warn!(project_id, error = %e, "Health monitor check failed"),
                }
            }

            // Persist alerts to DB
            if !alerts.is_empty() {
                persist_alerts(db, project_id, &alerts).await;
            }
        }
    }

    if alerts.is_empty() && db_ok && redis_ok {
        tracing::debug!("Health check: all systems healthy for project {}", project_id);
    }

    Ok(ProjectHealthResult {
        project_id,
        project_title,
        db_ok,
        redis_ok,
        alert_count: alerts.len(),
        alerts,
    })
}

// ---------------------------------------------------------------------------
// Cron-triggered: scan all projects
// ---------------------------------------------------------------------------

/// Periodic cron handler: scan all active projects and run health checks.
pub async fn health_auto_notify(
    db: &DatabaseConnection,
    redis: &RedisClient,
) -> AppResult<serde_json::Value> {
    let project_dao = ProjectDao;
    let active_projects = project_dao
        .get_all_active(db, 200)
        .await
        .unwrap_or_default();

    let mut total_alerts = 0usize;
    let mut results: Vec<serde_json::Value> = Vec::new();

    for project in &active_projects {
        let task = HealthNotifyTask {
            project_id: Some(project.id),
            checks: None,
            current_chapter: None,
        };

        match execute(db, redis, task).await {
            Ok(result) => {
                total_alerts += result.alert_count;
                if result.alert_count > 0 {
                    tracing::info!(
                        project_id = project.id,
                        alerts = result.alert_count,
                        "Health issues detected"
                    );
                }
                results.push(serde_json::json!({
                    "project_id": project.id,
                    "title": result.project_title,
                    "db_ok": result.db_ok,
                    "redis_ok": result.redis_ok,
                    "alerts": result.alert_count,
                }));
            }
            Err(e) => {
                tracing::warn!(
                    project_id = project.id,
                    error = %e,
                    "Health check failed for project"
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
        total_alerts,
        "Health auto-notify completed"
    );

    Ok(serde_json::json!({
        "scanned": active_projects.len(),
        "total_alerts": total_alerts,
        "results": results,
    }))
}

// ---------------------------------------------------------------------------
// Health Monitor Check
// ---------------------------------------------------------------------------

/// Run the full HealthMonitorService check (R1+R2+R3 combined).
async fn run_health_monitor_check(
    db: &DatabaseConnection,
    project_id: i32,
    current_chapter: Option<i32>,
) -> AppResult<Vec<serde_json::Value>> {
    let monitor = HealthMonitorService::new(VaultDao, ChapterDao);
    let chapter = current_chapter.unwrap_or(1);

    match monitor
        .check_health(db, project_id, chapter, None)
        .await
    {
        Ok(result) => Ok(result
            .alerts
            .into_iter()
            .map(|a| {
                serde_json::json!({
                    "rule": a.rule,
                    "level": a.level,
                    "detail": a.detail,
                    "promise_title": a.promise_title,
                })
            })
            .collect()),
        Err(e) => {
            tracing::warn!(project_id, error = %e, "Health monitor check_health failed");
            Ok(Vec::new())
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Persist health alerts to the database.
async fn persist_alerts(
    db: &DatabaseConnection,
    project_id: i32,
    alerts: &[serde_json::Value],
) {
    let health_alert_dao = HealthAlertDao;

    for alert in alerts {
        let rule = alert
            .get("rule")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let severity = alert
            .get("level")
            .and_then(|v| v.as_str())
            .unwrap_or("warning");
        let detail = alert
            .get("detail")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let title = alert
            .get("promise_title")
            .and_then(|v| v.as_str())
            .unwrap_or("Health Alert");

        let model = moling_db::entities::health_alert::ActiveModel {
            project_id: Set(project_id),
            rule: Set(rule.to_owned()),
            title: Set(title.to_owned()),
            detail: Set(detail.to_owned()),
            severity: Set(severity.to_owned()),
            ..Default::default()
        };

        if let Err(e) = health_alert_dao.create(db, model).await {
            tracing::warn!(project_id, error = %e, "Failed to persist health alert");
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
    fn test_health_notify_task_deserialization() {
        let json = r#"{
            "project_id": 1,
            "checks": ["R1", "R2"]
        }"#;
        let task: HealthNotifyTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.project_id, Some(1));
        assert_eq!(task.checks.unwrap().len(), 2);
    }

    #[test]
    fn test_project_health_result_serialization() {
        let result = ProjectHealthResult {
            project_id: 1,
            project_title: "测试项目".to_owned(),
            db_ok: true,
            redis_ok: true,
            alerts: vec![],
            alert_count: 0,
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("测试项目"));
        assert!(json.contains("db_ok"));
    }
}
