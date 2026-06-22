//! Admin routes — LLM config, stats, users, projects management.
//!
//! Mirrors Python `app/router/admin.py`.

use axum::{
    extract::{Path, Query, State},
    routing::{get, patch, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use sea_orm::PaginatorTrait;
use moling_db::dao::{
    system_config_dao::SystemConfigDao,
    user_dao::UserDao,
};
use moling_db::entities::{chapter, generation_task};
use moling_auth::AdminUser;
use moling_core::types::Pagination;
use sea_orm::{ColumnTrait, EntityTrait, QueryFilter};
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/llm-config", get(get_llm_config).post(update_llm_config))
        .route("/llm-config/test", post(test_llm_connection))
        .route("/llm-usage", get(get_llm_usage))
        .route("/stats", get(get_stats))
        .route("/users", get(list_users))
        .route("/users/{user_id}", patch(update_user))
        .route("/projects", get(list_all_projects))
}

// ---------------------------------------------------------------------------
// LLM Config
// ---------------------------------------------------------------------------

/// GET /admin/llm-config — get current LLM configuration.
///
/// Reads from system_config table (DB) with env fallback.
/// Mirrors Python `get_llm_config`.
async fn get_llm_config(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> AppResult<Json<serde_json::Value>> {
    let env_cfg = state.settings.get_effective_llm_config();
    let config_dao = SystemConfigDao;

    let api_base = config_dao
        .find_by_key(&state.db, "llm_api_base")
        .await?
        .map(|c| c.value)
        .unwrap_or_else(|| env_cfg.api_base.clone());

    let model = config_dao
        .find_by_key(&state.db, "llm_model")
        .await?
        .map(|c| c.value)
        .unwrap_or_else(|| env_cfg.default_model.clone());

    let api_key = config_dao
        .find_by_key(&state.db, "llm_api_key")
        .await?
        .map(|c| c.value);

    let is_configured = api_key.is_some()
        && !api_key.as_deref().unwrap_or("").is_empty()
        && api_key.as_deref().unwrap_or("") != "sk-placeholder";

    let api_key_masked = mask_key(api_key.as_deref().unwrap_or(""));

    Ok(Json(serde_json::json!({
        "api_base": api_base,
        "model": model,
        "is_configured": is_configured,
        "api_key_masked": api_key_masked,
    })))
}

/// POST /admin/llm-config — update LLM configuration, persists to DB.
///
/// Mirrors Python `save_llm_config`.
async fn update_llm_config(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<serde_json::Value>,
) -> AppResult<Json<serde_json::Value>> {
    let config_dao = SystemConfigDao;

    if let Some(v) = body.get("api_base").and_then(|v| v.as_str()) {
        config_dao.upsert(&state.db, "llm_api_base", v, "LLM API地址").await?;
        moling_core::config::set_override("llm_api_base", v);
    }
    if let Some(v) = body.get("api_key").and_then(|v| v.as_str()) {
        config_dao.upsert(&state.db, "llm_api_key", v, "LLM API密钥").await?;
        moling_core::config::set_override("llm_api_key", v);
    }
    if let Some(v) = body.get("model").and_then(|v| v.as_str()) {
        config_dao.upsert(&state.db, "llm_model", v, "LLM 模型名称").await?;
        moling_core::config::set_override("llm_model", v);
    }

    let api_key = body
        .get("api_key")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    Ok(Json(serde_json::json!({
        "api_base": body.get("api_base").and_then(|v| v.as_str()).unwrap_or(""),
        "model": body.get("model").and_then(|v| v.as_str()).unwrap_or(""),
        "is_configured": !api_key.is_empty() && api_key != "sk-placeholder",
        "api_key_masked": mask_key(api_key),
    })))
}

/// POST /admin/llm-config/test — test LLM API connection.
///
/// Verifies that API key and base URL are configured.
/// Note: Full HTTP connectivity test requires an HTTP client (reqwest).
/// Currently returns configuration status check.
/// Mirrors Python `test_llm_connection`.
async fn test_llm_connection(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> AppResult<Json<serde_json::Value>> {
    let config_dao = SystemConfigDao;
    let env_cfg = state.settings.get_effective_llm_config();

    let api_key = config_dao
        .find_by_key(&state.db, "llm_api_key")
        .await?
        .map(|c| c.value)
        .unwrap_or_else(|| env_cfg.api_key.clone());

    let api_base = config_dao
        .find_by_key(&state.db, "llm_api_base")
        .await?
        .map(|c| c.value)
        .unwrap_or_else(|| env_cfg.api_base.clone());

    if api_key.is_empty() || api_key == "sk-placeholder" {
        return Ok(Json(serde_json::json!({
            "ok": false,
            "msg": "API Key 未配置",
        })));
    }

    if api_base.is_empty() {
        return Ok(Json(serde_json::json!({
            "ok": false,
            "msg": "API Base URL 未配置",
        })));
    }

    Ok(Json(serde_json::json!({
        "ok": true,
        "msg": "配置已就绪",
        "api_base": api_base,
        "note": "完整连接测试需要 HTTP 客户端 (reqwest)，请通过管理面板手动测试。",
    })))
}

/// GET /admin/llm-usage — get LLM usage statistics.
///
/// Stub for now; in production would query TokenBudgetManager and KeyManager.
async fn get_llm_usage(
    _admin: AdminUser,
) -> AppResult<Json<serde_json::Value>> {
    Ok(Json(serde_json::json!({
        "status": "not_available",
        "note": "LLM 用量统计功能尚未接入 TokenBudgetManager。",
    })))
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

/// GET /admin/stats — get system-wide statistics.
///
/// Queries actual database counts. Mirrors Python `get_admin_stats`.
async fn get_stats(
    State(state): State<AppState>,
    _admin: AdminUser,
) -> AppResult<Json<serde_json::Value>> {
    let user_count = UserDao.count(&state.db).await.unwrap_or(0);

    let project_count: u64 = moling_db::entities::project::Entity::find()
        .filter(moling_db::entities::project::Column::IsDeleted.eq(false))
        .count(&state.db)
        .await
        .unwrap_or(0);

    // Global chapter count (all users)
    let chapter_count: u64 = chapter::Entity::find()
        .count(&state.db)
        .await
        .unwrap_or(0);

    let generation_jobs: u64 = generation_task::Entity::find()
        .count(&state.db)
        .await
        .unwrap_or(0);

    Ok(Json(serde_json::json!({
        "users": user_count,
        "projects": project_count,
        "chapters": chapter_count,
        "generation_jobs": generation_jobs,
    })))
}

// ---------------------------------------------------------------------------
// User Management
// ---------------------------------------------------------------------------

/// GET /admin/users — list all users (admin only).
///
/// Supports pagination via `page` and `page_size` query params.
/// Mirrors Python `get_users`.
async fn list_users(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let pagination = Pagination {
        page: pg.page,
        page_size: pg.page_size,
    };
    let (users, total) = UserDao.list(&state.db, &pagination).await?;

    let items: Vec<serde_json::Value> = users
        .iter()
        .map(|u| {
            serde_json::json!({
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "status": u.status,
                "avatar_url": u.avatar_url,
                "created_at": u.created_at,
                "updated_at": u.updated_at,
            })
        })
        .collect();

    Ok(Json(serde_json::json!({
        "items": items,
        "total": total,
        "page": pg.page,
        "page_size": pg.page_size,
        "total_pages": (total as f64 / pg.page_size as f64).ceil() as u64,
    })))
}

/// PATCH /admin/users/{user_id} — update a user (role, status, etc.).
///
/// Mirrors Python `update_user`.
async fn update_user(
    State(state): State<AppState>,
    _admin: AdminUser,
    Path(user_id): Path<String>,
    Json(req): Json<AdminUpdateUserReq>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel, Set};

    let user = UserDao
        .find_by_id(&state.db, &user_id)
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;

    let mut active = user.into_active_model();
    let mut updated_fields = Vec::new();

    if let Some(role) = &req.role {
        active.role = Set(role.clone());
        updated_fields.push("role");
    }
    if let Some(status) = &req.status {
        active.status = Set(status.clone());
        updated_fields.push("status");
    }

    active.update(&state.db).await.map_err(|e| {
        AppError::internal(format!("更新用户失败: {e}"))
    })?;

    Ok(Json(serde_json::json!({
        "success": true,
        "user_id": user_id,
        "updated_fields": updated_fields,
    })))
}

// ---------------------------------------------------------------------------
// Project Management
// ---------------------------------------------------------------------------

/// GET /admin/projects — list all projects (admin only).
///
/// Supports pagination. Mirrors Python `get_projects`.
async fn list_all_projects(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::QueryOrder;

    let paginator = moling_db::entities::project::Entity::find()
        .filter(moling_db::entities::project::Column::IsDeleted.eq(false))
        .order_by_desc(moling_db::entities::project::Column::UpdatedAt)
        .paginate(&state.db, pg.page_size as u64);

    let total = paginator.num_items().await.map_err(|e| {
        AppError::internal(format!("Database error counting projects: {e}"))
    })?;

    let items: Vec<serde_json::Value> = paginator
        .fetch_page(pg.page as u64 - 1)
        .await
        .map_err(|e| AppError::internal(format!("Database error listing projects: {e}")))?
        .iter()
        .map(|p| {
            serde_json::json!({
                "id": p.id,
                "user_id": p.user_id,
                "title": p.title,
                "author": p.author,
                "genre": p.genre,
                "status": p.status,
                "word_count": p.word_count,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
        })
        .collect();

    Ok(Json(serde_json::json!({
        "items": items,
        "total": total,
        "page": pg.page,
        "page_size": pg.page_size,
        "total_pages": (total as f64 / pg.page_size as f64).ceil() as u64,
    })))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Mask an API key for display: show first 4 + last 4 characters.
fn mask_key(key: &str) -> String {
    if key.len() < 8 {
        return "未配置".to_owned();
    }
    format!("{}****{}", &key[..4], &key[key.len() - 4..])
}
