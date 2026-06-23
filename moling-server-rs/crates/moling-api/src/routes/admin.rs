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
use serde::Deserialize;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/llm-config", get(get_llm_config).post(update_llm_config))
        .route("/llm-config/test", post(test_llm_connection))
        .route("/llm-config/audit", get(get_config_audit_log))
        .route("/llm-usage", get(get_llm_usage))
        .route("/stats", get(get_stats))
        .route("/users", get(list_users))
        .route("/users/{user_id}", patch(update_user))
        .route("/projects", get(list_all_projects))
}

// ---------------------------------------------------------------------------
// LLM Config
// ---------------------------------------------------------------------------

/// POST /admin/llm-config request body.
#[derive(Debug, Deserialize)]
struct UpdateLlmConfigReq {
    api_base: Option<String>,
    api_key: Option<String>,
    model: Option<String>,
    /// Version for optimistic lock (optional).
    version: Option<i32>,
}

/// GET /admin/llm-config — get current LLM configuration.
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

    let config_row = config_dao
        .find_by_key(&state.db, "llm_api_key")
        .await?;

    let api_key = config_row.as_ref().map(|c| c.value.as_str()).unwrap_or("");
    let version = config_row.as_ref().map(|c| c.version).unwrap_or(1);

    let is_configured = !api_key.is_empty() && api_key != "sk-placeholder";

    Ok(Json(serde_json::json!({
        "api_base": api_base,
        "model": model,
        "is_configured": is_configured,
        "api_key_masked": mask_key(api_key),
        "version": version,
    })))
}

/// POST /admin/llm-config — update LLM configuration with versioned upsert.
async fn update_llm_config(
    State(state): State<AppState>,
    _admin: AdminUser,
    Json(body): Json<UpdateLlmConfigReq>,
) -> AppResult<Json<serde_json::Value>> {
    let config_dao = SystemConfigDao;
    let operator = Some("admin");
    let ex_ver = body.version;

    if let Some(ref v) = body.api_base {
        config_dao.upsert_versioned(&state.db, "llm_api_base", v, "llm_api_base", ex_ver, operator).await?;
        moling_core::config::set_override("llm_api_base", v);
    }
    if let Some(ref v) = body.api_key {
        config_dao.upsert_versioned(&state.db, "llm_api_key", v, "llm_api_key", ex_ver, operator).await?;
        moling_core::config::set_override("llm_api_key", v);
    }
    if let Some(ref v) = body.model {
        config_dao.upsert_versioned(&state.db, "llm_model", v, "llm_model", ex_ver, operator).await?;
        moling_core::config::set_override("llm_model", v);
    }

    // Re-read to get updated version (clone before consuming)
    let key_row = config_dao.find_by_key(&state.db, "llm_api_key").await?;
    let new_version = key_row.as_ref().map(|c| c.version).unwrap_or(1);
    let is_configured = key_row
        .as_ref()
        .map(|c| !c.value.is_empty() && c.value != "sk-placeholder")
        .unwrap_or(false);
    let masked = mask_key(key_row.as_ref().map(|c| c.value.as_str()).unwrap_or(""));

    Ok(Json(serde_json::json!({
        "api_base": body.api_base.unwrap_or_default(),
        "model": body.model.unwrap_or_default(),
        "is_configured": is_configured,
        "api_key_masked": masked,
        "version": new_version,
    })))
}

/// POST /admin/llm-config/test — test LLM API connection with real HTTP call.
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

    // Real HTTP test: call /models endpoint
    let url = format!("{}/models", api_base.trim_end_matches('/'));
    match reqwest::Client::new()
        .get(&url)
        .bearer_auth(&api_key)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            let body: serde_json::Value = resp.json().await.unwrap_or_default();
            let available_count = body["data"]
                .as_array()
                .map(|a| a.len())
                .unwrap_or(0);
            Ok(Json(serde_json::json!({
                "ok": true,
                "msg": format!("连接成功 · {} 个可用模型", available_count),
                "available_models": available_count,
            })))
        }
        Ok(resp) => {
            Ok(Json(serde_json::json!({
                "ok": false,
                "msg": format!("HTTP {} — 请检查 API Key 和地址是否正确", resp.status()),
            })))
        }
        Err(e) => {
            Ok(Json(serde_json::json!({
                "ok": false,
                "msg": format!("连接失败: {}", e),
            })))
        }
    }
}

/// GET /admin/llm-config/audit — get audit trail for LLM config changes.
async fn get_config_audit_log(
    State(state): State<AppState>,
    _admin: AdminUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let config_dao = SystemConfigDao;

    // Collect audit logs for all three config keys
    let keys = ["llm_api_base", "llm_api_key", "llm_model"];
    let mut all_logs = Vec::new();
    for key in &keys {
        let logs = config_dao
            .get_audit_log(&state.db, key, pg.page_size as u64)
            .await?;
        for log in logs {
            all_logs.push(serde_json::json!({
                "config_key": log.config_key,
                "version": log.version,
                "old_value_masked": log.old_value.map(|v| mask_key_if_key(&v, key)),
                "changed_by": log.changed_by,
                "changed_at": log.changed_at,
            }));
        }
    }

    all_logs.sort_by(|a, b| {
        b["changed_at"]
            .as_str()
            .cmp(&a["changed_at"].as_str())
    });
    all_logs.truncate(pg.page_size as usize);

    Ok(Json(serde_json::json!({
        "items": all_logs,
        "total": all_logs.len(),
    })))
}

/// GET /admin/llm-usage — get LLM usage statistics.
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

fn mask_key(key: &str) -> String {
    if key.len() < 8 {
        return "未配置".to_owned();
    }
    format!("{}****{}", &key[..4], &key[key.len() - 4..])
}

/// Mask API key in audit log; other values shown in full.
fn mask_key_if_key(value: &str, config_key: &str) -> String {
    if config_key.contains("api_key") || config_key.contains("secret") {
        mask_key(value)
    } else {
        value.to_owned()
    }
}
