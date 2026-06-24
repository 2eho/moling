//! Template routes — CRUD + create project from template.
//!
//! Mirrors Python `app/router/template.py`.

use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::template_dao::TemplateDao;
use moling_auth::CurrentUser;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", post(create_template).get(list_templates))
        .route("/{id}", get(get_template).put(update_template).delete(delete_template))
        .route("/{template_id}/create-project", post(create_project_from_template))
}

/// Query params for template listing.
#[derive(Debug, serde::Deserialize)]
struct TemplateListQuery {
    #[serde(default = "default_page")]
    page: u32,
    #[serde(default = "default_page_size")]
    page_size: u32,
    genre: Option<String>,
}

/// POST /templates/ — create a new template.
async fn create_template(
    State(state): State<AppState>,
    _user: CurrentUser,
    Json(req): Json<CreateTemplateReq>,
) -> AppResult<Json<serde_json::Value>> {
    let dao = TemplateDao;
    let id = uuid::Uuid::new_v4().to_string();
    let model = moling_db::entities::template::ActiveModel {
        id: Set(id),
        name: Set(req.name),
        description: Set(req.description),
        genre: Set(req.genre),
        structure: Set(req.structure),
        created_by: Set(Some(_user.user_id.to_string())),
        ..Default::default()
    };
    let t = dao.create(&state.db, model).await?;
    Ok(Json(serde_json::to_value(t)?))
}

/// GET /templates/ — list templates with pagination and optional genre filter.
///
/// Mirrors Python `list_templates`.
async fn list_templates(
    State(state): State<AppState>,
    _user: CurrentUser,
    Query(q): Query<TemplateListQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let skip = (q.page as u64 - 1) * q.page_size as u64;
    let genre = q.genre.as_deref().unwrap_or("");
    let items = TemplateDao.list_by_genre(&state.db, genre, skip, q.page_size as u64).await?;
    let total = TemplateDao.count_by_genre(&state.db, genre).await?;
    Ok(Json(serde_json::json!({
        "items": items,
        "total": total,
        "page": q.page,
        "page_size": q.page_size,
    })))
}

/// GET /templates/{id} — get a template by ID.
async fn get_template(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(id): Path<String>,
) -> AppResult<Json<serde_json::Value>> {
    let t = TemplateDao.find_by_id(&state.db, &id).await?.ok_or_else(|| AppError::not_found("模板不存在".to_owned()))?;
    Ok(Json(serde_json::to_value(t)?))
}

/// PUT /templates/{id} — update a template.
async fn update_template(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(id): Path<String>,
    Json(req): Json<UpdateTemplateReq>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let t = TemplateDao.find_by_id(&state.db, &id).await?.ok_or_else(|| AppError::not_found("模板不存在".to_owned()))?;
    let mut a = t.into_active_model();
    if let Some(v) = req.name { a.name = Set(v); }
    if let Some(v) = req.description { a.description = Set(v); }
    if let Some(v) = req.genre { a.genre = Set(v); }
    if let Some(v) = req.structure { a.structure = Set(Some(v)); }
    let u = a.update(&state.db).await.map_err(|_| AppError::internal("更新模板失败".to_owned()))?;
    Ok(Json(serde_json::to_value(u)?))
}

/// DELETE /templates/{id} — delete a template.
async fn delete_template(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(id): Path<String>,
) -> AppResult<axum::http::StatusCode> {
    TemplateDao.delete(&state.db, &id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

/// POST /templates/{template_id}/create-project — create a project from a template.
///
/// Mirrors Python `create_project_from_template` (template_id in path).
async fn create_project_from_template(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(template_id): Path<String>,
    Query(req): Query<CreateProjectFromTemplateQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let tmpl = TemplateDao.find_by_id(&state.db, &template_id).await?.ok_or_else(|| AppError::not_found("模板不存在".to_owned()))?;
    let dao = moling_db::dao::project_dao::ProjectDao;
    let model = moling_db::entities::project::ActiveModel {
        user_id: Set(_user.user_id.to_string()),
        title: Set(req.title),
        author: Set(req.author.unwrap_or_default()),
        genre: Set(tmpl.genre),
        creation_mode: Set("from_template".into()),
        template_id: Set(None),
        status: Set("draft".into()),
        word_count: Set(0),
        ..Default::default()
    };
    let p = dao.create(&state.db, model).await?;
    Ok(Json(serde_json::to_value(p)?))
}

/// Query for create-project-from-template.
#[derive(Debug, serde::Deserialize)]
struct CreateProjectFromTemplateQuery {
    title: String,
    author: Option<String>,
}
