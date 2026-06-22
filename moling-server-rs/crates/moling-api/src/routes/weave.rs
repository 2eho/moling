//! Weave routes — narrative patterns, suggestions, apply, analyze.
//!
//! Mirrors Python `app/router/weave.py`.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::AppResult;
use moling_auth::CurrentUser;
use moling_services::WeaveService;
use crate::state::AppState;
use crate::types::WeaveApplyReq;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/patterns", get(get_patterns))
        .route("/suggestions/{project_id}", get(get_suggestions))
        .route("/apply", post(apply_pattern))
        .route("/analyze/{project_id}", get(analyze))
}

/// GET /weave/patterns — list available narrative weave patterns.
///
/// Mirrors Python `list_weave_patterns`.
async fn get_patterns(_user: CurrentUser) -> AppResult<Json<serde_json::Value>> {
    let svc = WeaveService::new();
    svc.patterns().await.map(Json)
}

/// GET /weave/suggestions/{project_id} — get weave-based narrative suggestions.
///
/// Analyzes project chapters, characters, plot promises, and timelines
/// to generate concrete weaving suggestions.
/// Mirrors Python `get_suggestions`.
async fn get_suggestions(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let svc = WeaveService::new();
    svc.suggestions(&state.db, project_id).await.map(Json)
}

/// POST /weave/apply — apply a weave pattern to target chapters.
///
/// Records the applied pattern on target chapters for traceability.
/// Mirrors Python `apply_suggestions`.
async fn apply_pattern(
    State(state): State<AppState>,
    _user: CurrentUser,
    Json(req): Json<WeaveApplyReq>,
) -> AppResult<Json<serde_json::Value>> {
    let svc = WeaveService::new();
    svc.apply(&state.db, req.pattern, &req.target_chapter_ids)
        .await
        .map(Json)
}

/// GET /weave/analyze/{project_id} — deep analysis of narrative structure.
///
/// Analyzes plot threads, character arcs, timeline consistency, and
/// unresolved promises.
/// Mirrors Python `analyze_project`.
async fn analyze(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let svc = WeaveService::new();
    svc.analyze(&state.db, project_id).await.map(Json)
}
