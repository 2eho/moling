//! Notification routes — list, unread count, read, read-all, delete.

use axum::{extract::{Path, Query, State}, routing::{delete, get, post}, Json, Router};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::notification_dao::NotificationDao;
use moling_auth::CurrentUser;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(list_notifications))
        .route("/unread-count", get(unread_count))
        .route("/{id}/read", post(mark_as_read))
        .route("/read-all", post(mark_all_read))
        .route("/{id}", delete(delete_notification))
}

async fn list_notifications(
    State(state): State<AppState>,
    user: CurrentUser,
    Query(q): Query<NotificationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let dao = NotificationDao;
    let skip = (q.page as u64 - 1) * q.page_size as u64;
    let items = dao.list_by_user(&state.db, &user.user_id.to_string(), skip, q.page_size as u64, q.is_read).await?;
    let total = dao.count_by_user(&state.db, &user.user_id.to_string(), q.is_read).await?;
    Ok(Json(serde_json::json!({ "items": items, "total": total, "page": q.page, "page_size": q.page_size })))
}

async fn unread_count(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let dao = NotificationDao;
    let count = dao.count_by_user(&state.db, &user.user_id.to_string(), Some(false)).await?;
    Ok(Json(serde_json::json!({ "unread_count": count })))
}

async fn mark_as_read(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let dao = NotificationDao;
    dao.mark_as_read(&state.db, id, &user.user_id.to_string()).await?.ok_or_else(|| AppError::not_found("通知不存在".to_owned()))?;
    Ok(Json(serde_json::json!({ "message": "Marked as read" })))
}

async fn mark_all_read(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let dao = NotificationDao;
    let count = dao.mark_all_as_read(&state.db, &user.user_id.to_string()).await?;
    Ok(Json(serde_json::json!({ "updated": count })))
}

async fn delete_notification(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(id): Path<i32>,
) -> AppResult<axum::http::StatusCode> {
    let dao = NotificationDao;
    dao.delete_by_user(&state.db, id, &user.user_id.to_string()).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}
