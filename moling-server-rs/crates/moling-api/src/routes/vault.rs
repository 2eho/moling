//! Vault routes — characters, plot promises, timeline, worlds CRUD.
//!
//! Delegates business logic to [`moling_services::VaultService`] for
//! ownership verification, changelog recording, and consistency checks.

use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::AppResult;
use moling_auth::CurrentUser;
use moling_services::{VaultService, VaultFilterParams};
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        // Characters
        .route("/characters", get(list_characters).post(create_character))
        .route("/characters/{id}", get(get_character).put(update_character).delete(delete_character))
        // Plot Promises
        .route("/plot-promises", get(list_plot_promises).post(create_plot_promise))
        .route("/plot-promises/{id}", get(get_plot_promise).put(update_plot_promise).delete(delete_plot_promise))
        // Timeline
        .route("/timeline", get(list_timeline).post(create_timeline))
        .route("/timeline/{id}", get(get_timeline).put(update_timeline).delete(delete_timeline))
        // World
        .route("/world", get(list_worlds).post(create_world))
        .route("/world/{id}", get(get_world).put(update_world).delete(delete_world))
        // Summary & analysis
        .route("/summary", get(get_summary))
        .route("/full-reanalyze", post(full_reanalyze))
        .route("/filter", get(filter_all))
}

fn svc() -> VaultService { VaultService::new() }

// ======================================================================
// Characters
// ======================================================================

async fn list_characters(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let items = svc().list_characters(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(serde_json::to_value(items)?))
}

async fn create_character(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreateCharacterReq>,
) -> AppResult<Json<serde_json::Value>> {
    let traits: Option<Vec<String>> = req.traits.and_then(|v| {
        v.as_array().map(|arr| arr.iter().filter_map(|x| x.as_str().map(String::from)).collect())
    });
    let c = svc().create_character(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &req.name,
        &req.role.unwrap_or_default(),
        req.description.as_deref(),
        traits.as_deref(),
        None, None, None,
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn get_character(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().get_character(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn update_character(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
    Json(req): Json<UpdateCharacterReq>,
) -> AppResult<Json<serde_json::Value>> {
    let traits: Option<Vec<String>> = req.traits.and_then(|v| {
        v.as_array().map(|arr| arr.iter().filter_map(|x| x.as_str().map(String::from)).collect())
    });
    let c = svc().update_character(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &id,
        req.name.as_deref(),
        req.role.as_deref(),
        req.description.as_deref(),
        traits.as_deref(),
        req.faction.as_deref(),
        req.personality.as_deref(),
        req.background.as_deref(),
        req.status.as_deref(),
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn delete_character(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<axum::http::StatusCode> {
    svc().delete_character(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

// ======================================================================
// Plot Promises
// ======================================================================

async fn list_plot_promises(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let items = svc().list_plot_promises(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(serde_json::to_value(items)?))
}

async fn create_plot_promise(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreatePlotPromiseReq>,
) -> AppResult<Json<serde_json::Value>> {
    let related: Option<Vec<String>> = req.related_characters;
    let c = svc().create_plot_promise(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &req.description,
        &req.promise_type,
        req.urgency,
        related.as_deref(),
        req.planted_chapter,
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn get_plot_promise(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().get_plot_promise(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn update_plot_promise(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
    Json(req): Json<UpdatePlotPromiseReq>,
) -> AppResult<Json<serde_json::Value>> {
    let related: Option<Vec<String>> = req.related_characters;
    let c = svc().update_plot_promise(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &id,
        req.description.as_deref(),
        req.promise_type.as_deref(),
        req.status.as_deref(),
        req.urgency,
        related.as_deref(),
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn delete_plot_promise(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<axum::http::StatusCode> {
    svc().delete_plot_promise(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

// ======================================================================
// Timeline
// ======================================================================

async fn list_timeline(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let items = svc().list_timeline(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(serde_json::to_value(items)?))
}

async fn create_timeline(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreateTimelineReq>,
) -> AppResult<Json<serde_json::Value>> {
    let chars: Option<Vec<String>> = req.characters_involved;
    let c = svc().create_timeline_event(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &req.event,
        &req.description,
        req.chapter_number,
        req.is_key_event,
        req.impact.as_deref(),
        chars.as_deref(),
        req.importance.as_deref(),
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn get_timeline(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().get_timeline_event(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn update_timeline(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
    Json(req): Json<UpdateTimelineReq>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().update_timeline_event(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &id,
        req.event.as_deref(),
        req.description.as_deref(),
        req.chapter_number,
        req.is_key_event,
        req.impact.as_deref(),
        req.importance.as_deref(),
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn delete_timeline(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<axum::http::StatusCode> {
    svc().delete_timeline_event(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

// ======================================================================
// World
// ======================================================================

async fn list_worlds(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let items = svc().list_world_entries(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(serde_json::to_value(items)?))
}

async fn create_world(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreateWorldReq>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().create_world_entry(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &req.name,
        &req.description,
        &req.category,
        req.constraint.as_deref(),
        req.source_chapter,
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn get_world(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().get_world_entry(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn update_world(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
    Json(req): Json<UpdateWorldReq>,
) -> AppResult<Json<serde_json::Value>> {
    let c = svc().update_world_entry(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        &id,
        req.name.as_deref(),
        req.description.as_deref(),
        req.category.as_deref(),
        req.constraint.as_deref(),
    ).await?;
    Ok(Json(serde_json::to_value(c)?))
}

async fn delete_world(
    State(state): State<AppState>,
    user: CurrentUser,
    Path((project_id, id)): Path<(i32, String)>,
) -> AppResult<axum::http::StatusCode> {
    svc().delete_world_entry(&state.db, &user.user_id.to_string(), project_id, &id).await?;
    Ok(axum::http::StatusCode::NO_CONTENT)
}

// ======================================================================
// Summary & Reanalyze
// ======================================================================

async fn get_summary(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<VaultSummaryResp>> {
    let summary = svc().vault_summary(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(VaultSummaryResp {
        characters: summary.character_count,
        timelines: summary.timeline_count,
        plot_promises: summary.plot_promise_count,
        worlds: summary.world_count,
    }))
}

/// POST /projects/{project_id}/vault/full-reanalyze — trigger full vault reanalysis.
async fn full_reanalyze(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<MessageResponse>> {
    svc().reanalyze(&state.db, &user.user_id.to_string(), project_id).await?;
    Ok(Json(MessageResponse { message: format!("Full reanalysis queued for project {project_id}") }))
}

/// GET /projects/{project_id}/vault/filter — unified four-vault filter.
async fn filter_all(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Query(params): Query<VaultFilterParams>,
) -> AppResult<Json<serde_json::Value>> {
    let result = svc().filter_all(&state.db, &user.user_id.to_string(), project_id, &params).await?;
    Ok(Json(serde_json::to_value(result)?))
}
