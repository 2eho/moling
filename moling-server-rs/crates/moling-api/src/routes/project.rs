//! Project routes — CRUD, stats, and suggestions.

use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_core::types::Pagination;
use moling_db::dao::project_dao::ProjectDao;
use moling_auth::CurrentUser;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", post(create_project).get(list_projects))
        .route("/stats", get(get_stats))
        .route("/{project_id}", get(get_project).put(update_project).delete(delete_project))
        .route("/{project_id}/stats", get(get_single_stats))
        .route("/{project_id}/suggestions", get(get_suggestions))
}

/// POST /projects — create a new project.
#[utoipa::path(
    post,
    path = "/api/v1/projects",
    request_body = CreateProjectReq,
    responses(
        (status = 200, description = "Project created successfully", body = ProjectResp),
        (status = 401, description = "Not authenticated")
    )
)]
pub async fn create_project(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<CreateProjectReq>,
) -> AppResult<Json<ProjectResp>> {
    let dao = ProjectDao;
    let model = moling_db::entities::project::ActiveModel {
        user_id: Set(user.user_id.to_string()),
        title: Set(req.title),
        author: Set(req.author.unwrap_or_default()),
        genre: Set(req.genre.unwrap_or_default()),
        synopsis: Set(req.synopsis),
        worldview: Set(req.worldview),
        protagonist: Set(req.protagonist),
        style: Set(req.style),
        target_words: Set(req.target_words),
        frequency: Set(req.frequency),
        ..Default::default()
    };
    let p = dao.create(&state.db, model).await?;
    Ok(Json(to_resp(p)))
}

/// GET /projects — list user's projects with pagination.
#[utoipa::path(
    get,
    path = "/api/v1/projects",
    params(
        ("page" = Option<u32>, Query, description = "Page number (default: 1)"),
        ("page_size" = Option<u32>, Query, description = "Page size (default: 20)"),
    ),
    responses(
        (status = 200, description = "Paginated list of projects"),
        (status = 401, description = "Not authenticated")
    )
)]
pub async fn list_projects(
    State(state): State<AppState>,
    user: CurrentUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<PaginatedList<ProjectResp>>> {
    let dao = ProjectDao;
    let pagination = Pagination { page: pg.page, page_size: pg.page_size };
    let (items, total) = dao.find_by_user(&state.db, &user.user_id.to_string(), &pagination).await?;
    Ok(Json(PaginatedList {
        items: items.into_iter().map(to_resp).collect(),
        total,
        page: pg.page,
        page_size: pg.page_size,
    }))
}

/// GET /projects/{project_id} — get project details.
#[utoipa::path(
    get,
    path = "/api/v1/projects/{project_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
    ),
    responses(
        (status = 200, description = "Project details", body = ProjectResp),
        (status = 401, description = "Not authenticated"),
        (status = 403, description = "Access denied"),
        (status = 404, description = "Project not found")
    )
)]
pub async fn get_project(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<ProjectResp>> {
    let dao = ProjectDao;
    let p = dao.find_by_id(&state.db, project_id).await?.ok_or_else(AppError::project_not_found)?;
    if p.user_id != user.user_id.to_string() {
        return Err(AppError::project_access_denied());
    }
    Ok(Json(to_resp(p)))
}

/// PUT /projects/{project_id} — update project.
#[utoipa::path(
    put,
    path = "/api/v1/projects/{project_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
    ),
    request_body = UpdateProjectReq,
    responses(
        (status = 200, description = "Project updated", body = ProjectResp),
        (status = 401, description = "Not authenticated"),
        (status = 403, description = "Access denied"),
        (status = 404, description = "Project not found")
    )
)]
pub async fn update_project(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<UpdateProjectReq>,
) -> AppResult<Json<ProjectResp>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let dao = ProjectDao;
    let p = dao.find_by_id(&state.db, project_id).await?.ok_or_else(AppError::project_not_found)?;
    if p.user_id != user.user_id.to_string() {
        return Err(AppError::project_access_denied());
    }
    let mut active = p.into_active_model();
    if let Some(v) = req.title { active.title = Set(v); }
    if let Some(v) = req.author { active.author = Set(v); }
    if let Some(v) = req.genre { active.genre = Set(v); }
    if let Some(v) = req.synopsis { active.synopsis = Set(Some(v)); }
    if let Some(v) = req.worldview { active.worldview = Set(Some(v)); }
    if let Some(v) = req.protagonist { active.protagonist = Set(Some(v)); }
    if let Some(v) = req.style { active.style = Set(Some(v)); }
    if let Some(v) = req.target_words { active.target_words = Set(Some(v)); }
    if let Some(v) = req.frequency { active.frequency = Set(Some(v)); }
    let updated = active.update(&state.db).await.map_err(|_| AppError::internal("Update failed".to_owned()))?;
    Ok(Json(to_resp(updated)))
}

/// DELETE /projects/{project_id} — delete a project.
#[utoipa::path(
    delete,
    path = "/api/v1/projects/{project_id}",
    params(
        ("project_id" = i32, Path, description = "Project ID"),
    ),
    responses(
        (status = 204, description = "Project deleted"),
        (status = 401, description = "Not authenticated"),
        (status = 403, description = "Access denied"),
        (status = 404, description = "Project not found")
    )
)]
pub async fn delete_project(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<axum::http::StatusCode> {
    let dao = ProjectDao;
    let p = dao.find_by_id(&state.db, project_id).await?.ok_or_else(AppError::project_not_found)?;
    if p.user_id != user.user_id.to_string() {
        return Err(AppError::project_access_denied());
    }
    dao.soft_delete(&state.db, project_id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

async fn get_stats(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<ProjectStatsResp>> {
    let dao = ProjectDao;
    let count = dao.count_by_user(&state.db, &user.user_id.to_string()).await?;
    Ok(Json(ProjectStatsResp { total_projects: count, total_words: 0, total_chapters: 0 }))
}

async fn get_single_stats(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<SingleProjectStatsResp>> {
    let dao = ProjectDao;
    let p = dao.find_by_id(&state.db, project_id).await?.ok_or_else(AppError::project_not_found)?;
    if p.user_id != user.user_id.to_string() {
        return Err(AppError::project_access_denied());
    }
    Ok(Json(SingleProjectStatsResp {
        project_id: p.id,
        title: p.title,
        total_chapters: 0,
        total_words: p.word_count,
        status: p.status,
    }))
}

async fn get_suggestions(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<ProjectSuggestionResp>> {
    let dao = ProjectDao;
    let p = dao.find_by_id(&state.db, project_id).await?.ok_or_else(AppError::project_not_found)?;
    if p.user_id != user.user_id.to_string() {
        return Err(AppError::project_access_denied());
    }
    let _ = p; // suggestions logic will be added in service phase
    Ok(Json(ProjectSuggestionResp { suggestions: vec![] }))
}

fn to_resp(p: moling_db::entities::project::Model) -> ProjectResp {
    ProjectResp {
        id: p.id,
        user_id: p.user_id,
        title: p.title,
        author: p.author,
        genre: p.genre,
        synopsis: p.synopsis,
        worldview: p.worldview,
        protagonist: p.protagonist,
        style: p.style,
        word_count: p.word_count,
        target_words: p.target_words,
        status: p.status,
        creation_mode: p.creation_mode,
        created_at: p.created_at.into(),
        updated_at: p.updated_at.into(),
    }
}
