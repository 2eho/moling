//! Phase4 routes — suggestions, apply, task management, reviews, retry.
//!
//! Phase 4 (四阶段精修) handles the storage/收纳 pipeline:
//! LLM analysis → vault merge → dynamic layer → card pool → archive.
//!
//! Uses [`moling_db::dao::phase4_dao::Phase4Dao`] for task queries and
//! [`moling_services::Phase4Service`] for pipeline execution.

use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::phase4_dao::Phase4Dao;
use moling_llm::DeepSeekClient;
use moling_services::Phase4Service;
use moling_auth::CurrentUser;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        // Suggestions
        .route("/chapters/{chapter_id}/suggestions", get(get_suggestions))
        // Apply
        .route("/apply", post(apply_suggestions))
        // Task queries
        .route("/tasks/{task_id}", get(get_task_status))
        .route("/chapters/{chapter_id}/tasks", get(list_chapter_tasks))
        .route("/projects/{project_id}/tasks", get(list_project_tasks))
        // Reviews
        .route("/pending-reviews", get(get_pending_reviews))
        .route("/reviews/{review_id}/approve", post(approve_review))
        .route("/reviews/{review_id}/reject", post(reject_review))
        // Retry
        .route("/tasks/{task_id}/retry", post(retry_task))
}

fn pdao() -> Phase4Dao { Phase4Dao }

// ======================================================================
// Suggestions
// ======================================================================

/// GET /phase4/chapters/{chapter_id}/suggestions — get Phase 4 suggestions for a chapter.
async fn get_suggestions(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(chapter_id): Path<String>,
) -> AppResult<Json<serde_json::Value>> {
    let llm = DeepSeekClient::with_base_url(&state.settings.llm_api_base);
    let phase4 = Phase4Service::with_default_model(llm, state.settings.llm_api_key.clone());
    let result = phase4.get_suggestions(&state.db, &chapter_id).await?;
    Ok(Json(result))
}

// ======================================================================
// Apply
// ======================================================================

/// POST /phase4/apply — apply selected Phase 4 suggestions.
async fn apply_suggestions(
    State(state): State<AppState>,
    _user: CurrentUser,
    Json(req): Json<ApplyPhase4Req>,
) -> AppResult<Json<serde_json::Value>> {
    let suggestion_ids: Vec<String> = req.suggestions.iter()
        .filter_map(|v| v.get("id").and_then(|id| id.as_str().map(String::from)))
        .collect();

    let llm = DeepSeekClient::with_base_url(&state.settings.llm_api_base);
    let phase4 = Phase4Service::with_default_model(llm, state.settings.llm_api_key.clone());
    let result = phase4.apply_suggestions(
        &state.db,
        &req.chapter_id,
        &suggestion_ids,
        req.auto_apply,
    ).await?;
    Ok(Json(result))
}

// ======================================================================
// Task Status
// ======================================================================

/// GET /phase4/tasks/{task_id} — get a single Phase 4 task status.
async fn get_task_status(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(task_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let task = pdao().find_by_id(&state.db, task_id).await?
        .ok_or_else(|| AppError::not_found("Phase4 task not found".to_owned()))?;
    Ok(Json(serde_json::json!({
        "id": task.id,
        "nonce": task.nonce,
        "project_id": task.project_id,
        "chapter_id": task.chapter_id,
        "status": task.status,
        "state": task.state,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "started_at": task.started_at.map(|t| t.to_rfc3339()),
        "completed_at": task.completed_at.map(|t| t.to_rfc3339()),
        "created_at": task.created_at.to_rfc3339(),
    })))
}

/// GET /phase4/chapters/{chapter_id}/tasks — list tasks for a chapter.
async fn list_chapter_tasks(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(chapter_id): Path<String>,
) -> AppResult<Json<serde_json::Value>> {
    let tasks = pdao().list_by_chapter(&state.db, &chapter_id, None).await?;
    let items: Vec<_> = tasks.iter().map(|t| serde_json::json!({
        "id": t.id,
        "nonce": t.nonce,
        "project_id": t.project_id,
        "chapter_id": t.chapter_id,
        "status": t.status,
        "state": t.state,
        "error_message": t.error_message,
        "retry_count": t.retry_count,
        "created_at": t.created_at.to_rfc3339(),
        "completed_at": t.completed_at.map(|d| d.to_rfc3339()),
    })).collect();
    Ok(Json(serde_json::json!(items)))
}

/// GET /phase4/projects/{project_id}/tasks — list tasks for a project.
async fn list_project_tasks(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let tasks = pdao().list_by_project(&state.db, project_id, None).await?;
    let items: Vec<_> = tasks.iter().map(|t| serde_json::json!({
        "id": t.id,
        "nonce": t.nonce,
        "project_id": t.project_id,
        "chapter_id": t.chapter_id,
        "status": t.status,
        "state": t.state,
        "error_message": t.error_message,
        "retry_count": t.retry_count,
        "created_at": t.created_at.to_rfc3339(),
        "completed_at": t.completed_at.map(|d| d.to_rfc3339()),
    })).collect();
    Ok(Json(serde_json::json!(items)))
}

// ======================================================================
// Reviews
// ======================================================================

/// GET /phase4/pending-reviews — list pending review tasks for current user's projects.
async fn get_pending_reviews(
    State(state): State<AppState>,
    _user: CurrentUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let skip = ((pg.page.saturating_sub(1)) as u64) * (pg.page_size as u64);
    let tasks = pdao().list_by_status(&state.db, "reviewing", skip, pg.page_size as u64).await?;
    let total = pdao().count_by_status(&state.db, "reviewing").await?;
    let reviews: Vec<_> = tasks.iter().map(|t| serde_json::json!({
        "id": t.id,
        "nonce": t.nonce,
        "project_id": t.project_id,
        "chapter_id": t.chapter_id,
        "status": t.status,
        "state": t.state,
        "error_message": t.error_message,
        "retry_count": t.retry_count,
        "started_at": t.started_at.map(|d| d.to_rfc3339()),
        "completed_at": t.completed_at.map(|d| d.to_rfc3339()),
        "created_at": t.created_at.to_rfc3339(),
    })).collect();
    Ok(Json(serde_json::json!({
        "reviews": reviews,
        "total": total,
        "page": pg.page,
        "page_size": pg.page_size,
    })))
}

/// POST /phase4/reviews/{review_id}/approve — approve a review task.
async fn approve_review(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(review_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let task = pdao().find_by_id(&state.db, review_id).await?
        .ok_or_else(|| AppError::not_found("Review task not found".to_owned()))?;
    use sea_orm::{IntoActiveModel, Set};
    let mut active = task.into_active_model();
    active.state = Set("done".to_owned());
    active.status = Set("approved".to_owned());
    let updated = pdao().update(&state.db, active).await?;
    Ok(Json(serde_json::json!({
        "approved": true,
        "review_id": review_id,
        "state": updated.state,
    })))
}

/// POST /phase4/reviews/{review_id}/reject — reject a review task.
async fn reject_review(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(review_id): Path<i32>,
    Json(body): Json<serde_json::Value>,
) -> AppResult<Json<serde_json::Value>> {
    let task = pdao().find_by_id(&state.db, review_id).await?
        .ok_or_else(|| AppError::not_found("Review task not found".to_owned()))?;
    let reason = body.get("reason").and_then(|v| v.as_str()).unwrap_or("Review rejected");
    use sea_orm::{IntoActiveModel, Set};
    let mut active = task.into_active_model();
    active.state = Set("failed".to_owned());
    active.status = Set("rejected".to_owned());
    active.error_message = Set(Some(reason.to_owned()));
    let updated = pdao().update(&state.db, active).await?;
    Ok(Json(serde_json::json!({
        "rejected": true,
        "review_id": review_id,
        "reason": reason,
        "state": updated.state,
    })))
}

// ======================================================================
// Retry
// ======================================================================

/// POST /phase4/tasks/{task_id}/retry — retry a failed Phase 4 task.
async fn retry_task(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(task_id): Path<i32>,
) -> AppResult<Json<MessageResponse>> {
    let task = pdao().find_by_id(&state.db, task_id).await?
        .ok_or_else(|| AppError::not_found("Phase4 task not found".to_owned()))?;
    let retry_count = task.retry_count;
    use sea_orm::{IntoActiveModel, Set};
    let mut active = task.into_active_model();
    active.state = Set("queued".to_owned());
    active.error_message = Set(None);
    active.retry_count = Set(retry_count + 1);
    pdao().update(&state.db, active).await?;
    Ok(Json(MessageResponse { message: format!("Task {} retry queued", task_id) }))
}
