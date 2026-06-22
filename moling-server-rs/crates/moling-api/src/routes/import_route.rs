//! Import routes — file import and phased import pipeline.
//!
//! Mirrors Python `app/ingest/router.py` with 10 endpoints:
//!
//! | Method | Path | Handler | Description |
//! |--------|------|---------|-------------|
//! | POST   | `/`                  | `submit_import`      | Submit text, create ingest job |
//! | GET    | `/`                  | `list_import_jobs`   | List jobs for project |
//! | GET    | `/{job_id}`          | `get_import_job`     | Job status + progress |
//! | POST   | `/{job_id}/phase1`   | `run_phase1`         | Run Phase 1 extraction |
//! | GET    | `/{job_id}/phase1/result` | `get_phase1_result` | Phase 1 results |
//! | POST   | `/{job_id}/phase2`   | `run_phase2`         | Run Phase 2 analysis |
//! | GET    | `/{job_id}/phase2/result` | `get_phase2_result` | Phase 2 results |
//! | POST   | `/{job_id}/confirm`  | `confirm_import`     | Confirm → Phase 3 commit |
//! | GET    | `/{job_id}/phase3/result` | `get_phase3_result` | Phase 3 results |
//! | POST   | `/full-import`       | `full_import`        | Full pipeline in one call |
//!
//! All endpoints are nested under `/api/v1/projects/{project_id}/import`.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_auth::CurrentUser;
use moling_services::{ImportService, split_chapters};
use moling_db::dao::ingest_dao::IngestDao;
use sea_orm::{IntoActiveModel, Set};
use crate::state::AppState;
use crate::types::*;

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

/// Build the import router.
///
/// Static routes (`/full-import`) are registered before parameterized ones
/// (`/{job_id}`) so Axum's trie-based router resolves them correctly.
pub fn router() -> Router<AppState> {
    Router::new()
        // Collection-level
        .route("/", post(submit_import).get(list_import_jobs))
        // Full-import shortcut (must come before `/{job_id}`)
        .route("/full-import", post(full_import))
        // Job-level
        .route("/{job_id}", get(get_import_job))
        .route("/{job_id}/phase1", post(run_phase1))
        .route("/{job_id}/phase1/result", get(get_phase1_result))
        .route("/{job_id}/phase2", post(run_phase2))
        .route("/{job_id}/phase2/result", get(get_phase2_result))
        .route("/{job_id}/confirm", post(confirm_import))
        .route("/{job_id}/phase3/result", get(get_phase3_result))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn import_svc() -> ImportService {
    ImportService::new()
}

fn ingest_dao() -> IngestDao {
    IngestDao
}

/// Extract raw text stored in a job's `phase0_result` JSON.
/// The `submit_import` handler stores `{"raw_text": "..."}` there.
fn raw_text_from_job(job: &moling_db::entities::ingest_job::Model) -> AppResult<String> {
    job.phase0_result
        .as_ref()
        .and_then(|v| v.get("raw_text").and_then(|t| t.as_str()))
        .map(|s| s.to_owned())
        .ok_or_else(|| AppError::bad_request("导入任务的原始文本不存在，请重新提交".to_owned()))
}

/// Split raw text into chapter pairs for phase2/phase3 consumption.
fn chapters_from_job(job: &moling_db::entities::ingest_job::Model) -> AppResult<Vec<(String, String)>> {
    let text = raw_text_from_job(job)?;
    Ok(split_chapters(&text))
}

/// Build the full job-status response matching Python `IngestJobStatusResp`.
fn build_job_status(job: &moling_db::entities::ingest_job::Model) -> ImportJobStatusResp {
    let mut result = serde_json::json!({});
    let mut conflicts: Vec<serde_json::Value> = Vec::new();

    if let Some(ref p1) = job.phase1_result {
        result["characters"] = p1.get("characters").cloned().unwrap_or(serde_json::json!([]));
        result["timeline"] = p1.get("timeline").cloned().unwrap_or(serde_json::json!([]));
        result["commitments"] = p1.get("plot_promises").cloned().unwrap_or(serde_json::json!([]));
        result["world"] = p1.get("world").cloned().unwrap_or(serde_json::json!([]));
    }

    if let Some(ref p3) = job.phase3_result {
        conflicts = p3
            .get("conflicts")
            .and_then(|c| c.as_array())
            .map(|a| a.clone())
            .unwrap_or_default();
    }

    ImportJobStatusResp {
        success: true,
        status: job.current_phase.clone(),
        progress: ImportProgress {
            phase: job.current_phase.clone(),
            percent: job.progress_percent,
        },
        result,
        conflicts,
        error: job.error_message.clone(),
    }
}

/// Build a phase-status response matching Python `PhaseStatusResp`.
fn build_phase_status(
    job: &moling_db::entities::ingest_job::Model,
    result_field: Option<&serde_json::Value>,
) -> PhaseStatusResp {
    PhaseStatusResp {
        success: true,
        status: job.current_phase.clone(),
        progress_percent: job.progress_percent,
        result: result_field.cloned(),
        error: job.error_message.clone(),
    }
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// POST /projects/{project_id}/import
///
/// Submit a new import job with raw text. The text is stored in
/// `phase0_result.raw_text` for later phases to consume.
///
/// Matches Python `submit_import` (Phase 0).
pub async fn submit_import(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<SubmitImportReq>,
) -> AppResult<Json<ImportJobResp>> {
    let svc = import_svc();

    // Validate: must have text
    if req.text.trim().is_empty() {
        return Err(AppError::validation_error("请提供 text 参数".to_owned()));
    }

    // Create the ingest job record
    let job = svc
        .file_import(
            &state.db,
            &user.user_id.to_string(),
            project_id,
            &req.source_type,
            None, // source_url
            &req.title,
        )
        .await?;

    // Store raw text in phase0_result so subsequent phases can access it
    let mut active = job.into_active_model();
    active.phase0_result = Set(Some(serde_json::json!({
        "raw_text": req.text,
        "source_type": req.source_type,
        "title": req.title,
    })));
    let job = ingest_dao().update(&state.db, active).await?;

    tracing::info!(
        job_id = %job.id,
        project_id,
        source_type = %req.source_type,
        "Import job submitted"
    );

    Ok(Json(ImportJobResp {
        success: true,
        job_id: job.id,
        status: job.current_phase,
    }))
}

/// GET /projects/{project_id}/import/{job_id}
///
/// Get the status and progress of an import job.
///
/// Matches Python `get_import_job` (7.2 轮询导入进度).
pub async fn get_import_job(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<ImportJobStatusResp>> {
    let job = import_svc().get_job(&state.db, &job_id).await?;
    Ok(Json(build_job_status(&job)))
}

/// GET /projects/{project_id}/import
///
/// List all import jobs for a project.
///
/// Matches Python `list_import_jobs`.
pub async fn list_import_jobs(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<ImportJobListResp>> {
    let jobs = import_svc().list_jobs(&state.db, project_id).await?;
    Ok(Json(ImportJobListResp {
        success: true,
        jobs: jobs
            .into_iter()
            .map(|j| ImportJobSummary {
                id: j.id,
                source_type: j.source_type,
                title: j.title,
                total_chapters: j.total_chapters,
                current_phase: j.current_phase,
                progress_percent: j.progress_percent,
                error_message: j.error_message,
                created_at: j.created_at,
            })
            .collect(),
    }))
}

// ---- Phase 1 ----

/// POST /projects/{project_id}/import/{job_id}/phase1
///
/// Run Phase 1: extraction and merging (chapter splitting + word counts).
///
/// Matches Python `run_phase1` (7.3 执行 Phase 1).
pub async fn run_phase1(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<PhaseRunResp>> {
    let svc = import_svc();
    let job = svc.get_job(&state.db, &job_id).await?;
    let raw_text = raw_text_from_job(&job)?;

    svc.phase1(&state.db, &job_id, &raw_text).await?;

    Ok(Json(PhaseRunResp {
        success: true,
        message: format!("Phase 1 已完成，任务 {job_id}"),
    }))
}

/// GET /projects/{project_id}/import/{job_id}/phase1/result
///
/// Get Phase 1 analysis results.
///
/// Matches Python `get_phase1_result`.
pub async fn get_phase1_result(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<PhaseStatusResp>> {
    let job = import_svc().get_job(&state.db, &job_id).await?;
    Ok(Json(build_phase_status(&job, job.phase1_result.as_ref())))
}

// ---- Phase 2 ----

/// POST /projects/{project_id}/import/{job_id}/phase2
///
/// Run Phase 2: chapter structure and style analysis.
///
/// Matches Python `run_phase2` (7.4 执行 Phase 2).
pub async fn run_phase2(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<PhaseRunResp>> {
    let svc = import_svc();
    let job = svc.get_job(&state.db, &job_id).await?;
    let chapters = chapters_from_job(&job)?;

    svc.phase2(&state.db, &job_id, &chapters).await?;

    Ok(Json(PhaseRunResp {
        success: true,
        message: format!("Phase 2 已完成，任务 {job_id}"),
    }))
}

/// GET /projects/{project_id}/import/{job_id}/phase2/result
///
/// Get Phase 2 analysis results.
///
/// Matches Python `get_phase2_result`.
pub async fn get_phase2_result(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<PhaseStatusResp>> {
    let job = import_svc().get_job(&state.db, &job_id).await?;
    Ok(Json(build_phase_status(&job, job.phase2_result.as_ref())))
}

// ---- Phase 3 (confirm) ----

/// POST /projects/{project_id}/import/{job_id}/confirm
///
/// Confirm the import and run Phase 3: write chapters to database.
///
/// Accepts an optional `resolve_strategy` in the JSON body
/// ("keep_existing" / "merge" / "replace").
///
/// Matches Python `confirm_import` (7.5 确认导入).
pub async fn confirm_import(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
    Json(body): Json<serde_json::Value>,
) -> AppResult<Json<PhaseRunResp>> {
    let svc = import_svc();
    let job = svc.get_job(&state.db, &job_id).await?;
    let chapters = chapters_from_job(&job)?;

    // Extract resolve_strategy from body (defaults to "keep_existing")
    let _strategy = body
        .get("resolve_strategy")
        .and_then(|v| v.as_str())
        .unwrap_or("keep_existing");

    svc.phase3(&state.db, &job_id, &chapters).await?;

    Ok(Json(PhaseRunResp {
        success: true,
        message: format!("Phase 3 已完成，任务 {job_id} — 策略: {_strategy}"),
    }))
}

/// GET /projects/{project_id}/import/{job_id}/phase3/result
///
/// Get Phase 3 commit results.
///
/// Matches Python `get_phase3_result`.
pub async fn get_phase3_result(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, job_id)): Path<(i32, String)>,
) -> AppResult<Json<PhaseStatusResp>> {
    let job = import_svc().get_job(&state.db, &job_id).await?;
    Ok(Json(build_phase_status(&job, job.phase3_result.as_ref())))
}

// ---- Full Import ----

/// POST /projects/{project_id}/import/full-import
///
/// Run the entire import pipeline in one call:
/// Phase 1 (extraction) → Phase 2 (analysis) → Phase 3 (commit).
///
/// Matches Python `full_import` (全流程一键导入).
pub async fn full_import(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<SubmitImportReq>,
) -> AppResult<Json<ImportJobResp>> {
    let svc = import_svc();

    // Validate: must have text
    if req.text.trim().is_empty() {
        return Err(AppError::validation_error("请提供 text 参数".to_owned()));
    }

    let job = svc
        .full_import(
            &state.db,
            &user.user_id.to_string(),
            project_id,
            &req.source_type,
            None, // source_url
            &req.title,
            &req.text,
        )
        .await?;

    tracing::info!(
        job_id = %job.id,
        project_id,
        "Full import pipeline completed"
    );

    Ok(Json(ImportJobResp {
        success: true,
        job_id: job.id,
        status: job.current_phase,
    }))
}
