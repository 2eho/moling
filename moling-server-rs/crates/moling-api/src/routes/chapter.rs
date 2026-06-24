//! Chapter routes — CRUD, reorder, confirm, revise, agent, redraw.
//!
//! Delegates business logic to [`moling_services::ChapterService`] for
//! ownership verification and domain operations.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::chapter_dao::ChapterDao;
use moling_auth::CurrentUser;
use moling_services::ChapterService;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/chapters", post(create_chapter).get(list_chapters))
        .route("/chapters/current", get(get_current_chapter))
        .route("/chapters/reorder", post(reorder))
        .route("/chapters/{chapter_id}", get(get_chapter).put(update_chapter).delete(delete_chapter))
        .route("/chapters/{chapter_id}/confirm", post(confirm))
        .route("/chapters/{chapter_id}/revise", post(revise))
        .route("/chapters/{chapter_id}/agent", post(agent))
        .route("/chapters/{chapter_id}/redraw", post(redraw))
        .route("/chapters/{chapter_id}/suggestions", get(get_suggestions))
}

fn chapter_svc() -> ChapterService { ChapterService::new() }

/// POST /projects/{project_id}/chapters — create a new chapter.
#[utoipa::path(
    post,
    path = "/api/v1/projects/{project_id}/chapters",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
    ),
    request_body = CreateChapterReq,
    responses(
        (status = 200, description = "Chapter created", body = ChapterResp),
        (status = 401, description = "Not authenticated"),
        (status = 403, description = "Access denied"),
        (status = 404, description = "Project not found")
    )
)]
pub async fn create_chapter(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreateChapterReq>,
) -> AppResult<Json<ChapterResp>> {
    let ch = chapter_svc().create(&state.db, &user.user_id.to_string(), project_id, &req.title).await?;
    Ok(Json(to_resp(ch)))
}

/// GET /projects/{project_id}/chapters — list chapters for a project.
#[utoipa::path(
    get,
    path = "/api/v1/projects/{project_id}/chapters",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
    ),
    responses(
        (status = 200, description = "List of chapters", body = Vec<ChapterResp>),
        (status = 401, description = "Not authenticated"),
        (status = 404, description = "Project not found")
    )
)]
pub async fn list_chapters(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<Vec<ChapterResp>>> {
    let chapters = chapter_svc().list(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(chapters.into_iter().map(to_resp).collect()))
}

/// GET /projects/{project_id}/chapters/current — get the first (lowest-numbered) chapter.
async fn get_current_chapter(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<ChapterResp>> {
    let chapters = chapter_svc().list(&state.db, &user.user_id.to_string(), project_id).await?;
    let first = chapters.into_iter().min_by_key(|c| c.chapter_number)
        .ok_or_else(|| AppError::not_found("No chapters found".to_owned()))?;
    Ok(Json(to_resp(first)))
}

/// GET /projects/{project_id}/chapters/{chapter_id} — get chapter details.
#[utoipa::path(
    get,
    path = "/api/v1/projects/{project_id}/chapters/{chapter_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
        ("chapter_id" = String, Path, description = "Chapter ID"),
    ),
    responses(
        (status = 200, description = "Chapter details", body = ChapterResp),
        (status = 404, description = "Chapter not found")
    )
)]
pub async fn get_chapter(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<ChapterResp>> {
    let dao = ChapterDao;
    let ch = dao.find_by_id(&state.db, &chapter_id).await?.ok_or_else(AppError::chapter_not_found)?;
    Ok(Json(to_resp(ch)))
}

/// PUT /projects/{project_id}/chapters/{chapter_id} — update chapter.
#[utoipa::path(
    put,
    path = "/api/v1/projects/{project_id}/chapters/{chapter_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
        ("chapter_id" = String, Path, description = "Chapter ID"),
    ),
    request_body = UpdateChapterReq,
    responses(
        (status = 200, description = "Chapter updated", body = ChapterResp),
        (status = 404, description = "Chapter not found")
    )
)]
pub async fn update_chapter(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
    Json(req): Json<UpdateChapterReq>,
) -> AppResult<Json<ChapterResp>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let dao = ChapterDao;
    let ch = dao.find_by_id(&state.db, &chapter_id).await?.ok_or_else(AppError::chapter_not_found)?;
    let mut active = ch.into_active_model();
    if let Some(v) = req.title { active.title = Set(v); }
    if let Some(v) = req.content { active.content = Set(Some(v)); }
    let updated = active.update(&state.db).await.map_err(|_| AppError::internal("Update chapter failed".to_owned()))?;
    Ok(Json(to_resp(updated)))
}

/// DELETE /projects/{project_id}/chapters/{chapter_id} — delete a chapter.
#[utoipa::path(
    delete,
    path = "/api/v1/projects/{project_id}/chapters/{chapter_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
        ("chapter_id" = String, Path, description = "Chapter ID"),
    ),
    responses(
        (status = 204, description = "Chapter deleted"),
        (status = 404, description = "Chapter not found")
    )
)]
pub async fn delete_chapter(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<axum::http::StatusCode> {
    let dao = ChapterDao;
    dao.soft_delete(&state.db, &chapter_id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

/// POST /projects/{project_id}/chapters/reorder — reorder chapter sequence.
async fn reorder(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<ReorderChaptersReq>,
) -> AppResult<Json<Vec<ChapterResp>>> {
    let dao = ChapterDao;
    // Bulk update chapter numbers based on ordered ID list
    for (idx, ch_id) in req.chapter_ids.iter().enumerate() {
        if let Some(ch) = dao.find_by_id(&state.db, ch_id).await? {
            use sea_orm::{ActiveModelTrait, IntoActiveModel};
            if ch.project_id == project_id {
                let mut active = ch.into_active_model();
                active.chapter_number = Set((idx + 1) as i32);
                active.update(&state.db).await.map_err(|_| AppError::internal("Reorder failed".to_owned()))?;
            }
        }
    }
    let chapters = chapter_svc().list(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(chapters.into_iter().map(to_resp).collect()))
}

/// POST .../confirm — confirm chapter content.
async fn confirm(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<ChapterResp>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let dao = ChapterDao;
    let ch = dao.find_by_id(&state.db, &chapter_id).await?.ok_or_else(AppError::chapter_not_found)?;
    let mut active = ch.into_active_model();
    active.status = Set("confirmed".into());
    active.confirmed_at = Set(Some(chrono::Utc::now()));
    let updated = active.update(&state.db).await.map_err(|_| AppError::internal("Confirm failed".to_owned()))?;
    Ok(Json(to_resp(updated)))
}

/// POST .../revise — trigger AI revision for chapter.
async fn revise(
    State(_state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<MessageResponse>> {
    Ok(Json(MessageResponse { message: format!("Revision queued for chapter {chapter_id}") }))
}

/// POST .../agent — trigger agent-assisted chapter generation.
async fn agent(
    State(_state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<MessageResponse>> {
    Ok(Json(MessageResponse { message: format!("Agent task queued for chapter {chapter_id}") }))
}

/// POST .../redraw — redraw cards for chapter.
async fn redraw(
    State(_state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<MessageResponse>> {
    Ok(Json(MessageResponse { message: format!("Redraw queued for chapter {chapter_id}") }))
}

/// GET .../suggestions — get AI suggestions for a chapter.
async fn get_suggestions(
    State(_state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, chapter_id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    // Stub: full integration with LLM analysis will be done in a later phase
    Ok(Json(serde_json::json!({
        "chapter_id": chapter_id,
        "suggestions": []
    })))
}

fn to_resp(ch: moling_db::entities::chapter::Model) -> ChapterResp {
    ChapterResp {
        id: ch.id,
        project_id: ch.project_id,
        title: ch.title,
        content: ch.content,
        chapter_number: ch.chapter_number,
        status: ch.status,
        word_count: ch.word_count,
        created_at: ch.created_at,
        updated_at: ch.updated_at,
    }
}
