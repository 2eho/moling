//! Generation routes — trigger AI generation, check job status, cancel, history.

use axum::{extract::{Path, State}, routing::{get, post}, Json, Router};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::generation_dao::GenerationDao;
use moling_auth::CurrentUser;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/chapters/{chapter_id}/generate", post(generate))
        .route("/jobs/{job_id}", get(get_job))
        .route("/jobs/{job_id}/cancel", post(cancel_job))
        .route("/history", get(get_history))
}

/// POST /generation/chapters/{chapter_id}/generate — trigger chapter generation.
#[utoipa::path(
    post,
    path = "/api/v1/generation/chapters/{chapter_id}/generate",
    params(
        ("chapter_id" = String, Path, description = "Chapter ID to generate content for"),
    ),
    request_body = GenerateReq,
    responses(
        (status = 200, description = "Generation job created", body = GenerationJobResp),
        (status = 401, description = "Not authenticated")
    )
)]
pub async fn generate(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(chapter_id): Path<String>,
    Json(req): Json<GenerateReq>,
) -> AppResult<Json<GenerationJobResp>> {
    let dao = GenerationDao;
    let task_id = uuid::Uuid::new_v4();
    let model = moling_db::entities::generation_task::ActiveModel {
        id: Set(task_id),
        project_id: Set(0), // Will be filled by service
        chapter_id: Set(Some(chapter_id)),
        user_id: Set("".into()),
        task_type: Set(req.mode.unwrap_or_else(|| "generate_chapter".into())),
        status: Set("pending".into()),
        input_params: Set(serde_json::json!({"temperature": req.temperature.unwrap_or(0.7)})),
        ..Default::default()
    };
    let job = dao.create(&state.db, model).await?;
    Ok(Json(GenerationJobResp {
        id: job.id.to_string(), project_id: job.project_id,
        chapter_id: job.chapter_id, task_type: job.task_type,
        status: job.status, progress_percent: job.progress_percent,
        created_at: job.created_at.into(),
    }))
}

/// GET /generation/jobs/{job_id} — get generation job status.
#[utoipa::path(
    get,
    path = "/api/v1/generation/jobs/{job_id}",
    params(
        ("job_id" = String, Path, description = "Job ID"),
    ),
    responses(
        (status = 200, description = "Job status", body = GenerationJobResp),
        (status = 404, description = "Job not found")
    )
)]
pub async fn get_job(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(job_id): Path<String>,
) -> AppResult<Json<GenerationJobResp>> {
    let dao = GenerationDao;
    let job = dao.find_by_id(&state.db, &job_id).await?.ok_or_else(AppError::generation_task_not_found)?;
    Ok(Json(GenerationJobResp {
        id: job.id.to_string(), project_id: job.project_id,
        chapter_id: job.chapter_id, task_type: job.task_type,
        status: job.status, progress_percent: job.progress_percent,
        created_at: job.created_at.into(),
    }))
}

/// POST /generation/jobs/{job_id}/cancel — cancel a generation job.
async fn cancel_job(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(job_id): Path<String>,
) -> AppResult<Json<MessageResponse>> {
    let dao = GenerationDao;
    let job = dao.find_by_id(&state.db, &job_id).await?.ok_or_else(AppError::generation_task_not_found)?;
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let mut active = job.into_active_model();
    active.status = Set("cancelled".into());
    active.update(&state.db).await.map_err(|_| AppError::internal("Cancel failed".to_owned()))?;
    Ok(Json(MessageResponse { message: "Job cancelled".into() }))
}

/// GET /generation/history — list generation history.
async fn get_history(
    State(state): State<AppState>,
    _user: CurrentUser,
) -> AppResult<Json<Vec<GenerationJobResp>>> {
    let dao = GenerationDao;
    let jobs = dao.list_by_status(&state.db, "pending", 20).await?;
    let list: Vec<_> = jobs.into_iter().map(|j| GenerationJobResp {
        id: j.id.to_string(), project_id: j.project_id,
        chapter_id: j.chapter_id, task_type: j.task_type,
        status: j.status, progress_percent: j.progress_percent,
        created_at: j.created_at.into(),
    }).collect();
    Ok(Json(list))
}
