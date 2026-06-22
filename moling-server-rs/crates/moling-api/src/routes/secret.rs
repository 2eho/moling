//! Secret routes — CRUD + by-character lookup.

use axum::{extract::{Path, State}, routing::{get, post}, Json, Router};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::secret_dao::SecretDao;
use moling_auth::CurrentUser;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", post(create_secret).get(list_secrets))
        .route("/{secret_id}", get(get_secret).put(update_secret).delete(delete_secret))
        .route("/by-character/{character_id}", get(by_character))
}

async fn create_secret(State(state): State<AppState>, _user: CurrentUser, Path(project_id): Path<i32>, Json(req): Json<CreateSecretReq>) -> AppResult<Json<serde_json::Value>> {
    let dao = SecretDao;
    let id = uuid::Uuid::new_v4().to_string();
    let model = moling_db::entities::secret::ActiveModel {
        id: Set(id), project_id: Set(project_id), description: Set(req.description),
        secrecy_level: Set(req.secrecy_level.unwrap_or_else(|| "hidden".into())),
        known_by: Set(req.known_by.unwrap_or(serde_json::json!([]))),
        unknown_to: Set(req.unknown_to.unwrap_or(serde_json::json!([]))),
        debt: Set(req.debt.unwrap_or(0)), created_chapter: Set(req.created_chapter),
        ..Default::default()
    };
    let s = dao.create(&state.db, model).await?;
    Ok(Json(serde_json::to_value(s).unwrap()))
}

async fn list_secrets(State(state): State<AppState>, _user: CurrentUser, Path(project_id): Path<i32>) -> AppResult<Json<serde_json::Value>> {
    let items = SecretDao.list_by_project(&state.db, project_id).await?;
    Ok(Json(serde_json::to_value(items).unwrap()))
}

async fn get_secret(State(state): State<AppState>, _user: CurrentUser, Path((_pid, secret_id)): Path<(i32, String)>) -> AppResult<Json<serde_json::Value>> {
    let s = SecretDao.find_by_id(&state.db, &secret_id).await?.ok_or_else(|| AppError::not_found("Secret not found".to_owned()))?;
    Ok(Json(serde_json::to_value(s).unwrap()))
}

async fn update_secret(State(state): State<AppState>, _user: CurrentUser, Path((_pid, secret_id)): Path<(i32, String)>, Json(req): Json<UpdateSecretReq>) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let s = SecretDao.find_by_id(&state.db, &secret_id).await?.ok_or_else(|| AppError::not_found("Secret not found".to_owned()))?;
    let mut a = s.into_active_model();
    if let Some(v) = req.description { a.description = Set(v); }
    if let Some(v) = req.secrecy_level { a.secrecy_level = Set(v); }
    if let Some(v) = req.known_by { a.known_by = Set(v); }
    if let Some(v) = req.unknown_to { a.unknown_to = Set(v); }
    if let Some(v) = req.debt { a.debt = Set(v); }
    let u = a.update(&state.db).await.map_err(|_| AppError::internal("Update secret failed".to_owned()))?;
    Ok(Json(serde_json::to_value(u).unwrap()))
}

async fn delete_secret(State(state): State<AppState>, _user: CurrentUser, Path((_pid, secret_id)): Path<(i32, String)>) -> AppResult<axum::http::StatusCode> {
    SecretDao.soft_delete(&state.db, &secret_id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

/// GET /projects/{project_id}/secrets/by-character/{character_id} — list secrets known by a character.
async fn by_character(State(state): State<AppState>, _user: CurrentUser, Path((project_id, character_id)): Path<(i32, String)>) -> AppResult<Json<serde_json::Value>> {
    let all = SecretDao.list_by_project(&state.db, project_id).await?;
    let filtered: Vec<_> = all.into_iter().filter(|s| {
        s.known_by.as_array().map_or(false, |arr| arr.iter().any(|v| v.as_str() == Some(&character_id)))
    }).collect();
    Ok(Json(serde_json::to_value(filtered).unwrap()))
}
