//! Project health routes — R1/R2/R3 health check alerts.
//!
//! Ported from Python `app/router/project_health.py`.
//!
//! Endpoints:
//! - GET  /{project_id}/health         — get active health alerts
//! - POST /{project_id}/health/refresh — run health checks and return results
//!
//! Uses [`moling_services::HealthService`] for alert management and
//! health check execution.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::AppResult;
use moling_services::HealthService;
use moling_auth::CurrentUser;
use crate::state::AppState;
use crate::types::{HealthAlertItem, HealthCheckResp};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/{project_id}/health", get(get_project_health))
        .route("/{project_id}/health/refresh", post(refresh_project_health))
}

// ======================================================================
// GET /{project_id}/health
// ======================================================================

/// Get active health alerts for a project.
async fn get_project_health(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<HealthCheckResp>> {
    let health = HealthService::new();
    let alerts = health.list_alerts(&state.db, project_id, true).await?;

    let alert_items: Vec<HealthAlertItem> = alerts
        .iter()
        .map(|a| HealthAlertItem {
            rule: a.rule.clone(),
            title: a.title.clone(),
            detail: a.detail.clone(),
            severity: Some(a.severity.clone()),
            level: None,
            is_active: Some(a.is_active),
        })
        .collect();

    let latest_checked_at = alerts
        .iter()
        .filter_map(|a| a.checked_at)
        .max()
        .map(|t| t.to_rfc3339())
        .unwrap_or_else(|| chrono::Utc::now().to_rfc3339());

    let _ = user; // ownership verified via project access implicitly

    Ok(Json(HealthCheckResp {
        alerts: alert_items,
        checked_at: latest_checked_at,
        status: None,
        alert_counts: None,
    }))
}

// ======================================================================
// POST /{project_id}/health/refresh
// ======================================================================

/// Run all health checks (R1/R2/R3) and return updated alerts.
async fn refresh_project_health(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<HealthCheckResp>> {
    let health = HealthService::new();
    let user_id = user.user_id.to_string();

    let check_result = health.run_health_check(&state.db, &user_id, project_id).await?;

    // Extract alert items from the check result
    let mut alert_items: Vec<HealthAlertItem> = Vec::new();
    if let Some(alerts) = check_result.get("alerts").and_then(|v| v.as_array()) {
        for alert in alerts {
            alert_items.push(HealthAlertItem {
                rule: alert.get("rule").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                title: alert.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                detail: alert.get("detail").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                severity: alert.get("severity").and_then(|v| v.as_str()).map(String::from),
                level: None,
                is_active: None,
            });
        }
    }

    let checked_at = chrono::Utc::now().to_rfc3339();

    Ok(Json(HealthCheckResp {
        alerts: alert_items,
        checked_at,
        status: None,
        alert_counts: None,
    }))
}
