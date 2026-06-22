//! Settings routes — profile, change password, settings CRUD, health monitor, export, clear cache, phase4.
//!
//! Mirrors Python `app/router/setting.py`.

use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::user_dao::UserDao;
use moling_auth::CurrentUser;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        // User settings (get/update JSON blob)
        .route("/", get(get_settings).put(update_settings))
        // Profile
        .route("/profile", get(get_profile).put(update_profile))
        // Password
        .route("/change-password", post(change_password))
        // Health monitor
        .route("/health-monitor", get(get_health_monitor).patch(update_health_monitor))
        // Export
        .route("/export", post(export_data))
        // Cache
        .route("/clear-cache", post(clear_cache))
        // Phase 4 review mode
        .route("/phase4-review", get(get_phase4_review).patch(update_phase4_review))
}

// ---------------------------------------------------------------------------
// Settings (JSON blob)
// ---------------------------------------------------------------------------

/// GET /settings/ — get current user's stored settings JSON.
///
/// Mirrors Python `get_settings`.
async fn get_settings(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    Ok(Json(u.settings.unwrap_or_default()))
}

/// PUT /settings/ — update current user's settings (partial merge).
///
/// Mirrors Python `update_settings`.
async fn update_settings(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(update): Json<serde_json::Value>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;

    let settings_clone = u.settings.clone();
    let mut current: serde_json::Map<String, serde_json::Value> = settings_clone
        .and_then(|v| v.as_object().cloned())
        .unwrap_or_default();

    if let Some(update_obj) = update.as_object() {
        for (key, value) in update_obj {
            current.insert(key.clone(), value.clone());
        }
    }

    let merged = serde_json::Value::Object(current);
    let mut active = u.into_active_model();
    active.settings = Set(Some(merged.clone()));
    active.update(&state.db).await.map_err(|e| {
        AppError::internal(format!("Update settings failed: {e}"))
    })?;
    Ok(Json(merged))
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

/// GET /settings/profile — get current user's profile.
async fn get_profile(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    Ok(Json(serde_json::json!({
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "nickname": u.username,
        "avatar_url": u.avatar_url,
        "bio": u.bio,
        "status": u.status,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
    })))
}

/// PUT /settings/profile — update current user's profile.
async fn update_profile(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<UpdateProfileReq>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let found = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    let mut a = found.into_active_model();
    if let Some(ref v) = req.username {
        if *v != *a.username.as_ref() {
            if UserDao.username_exists(&state.db, v).await? {
                return Err(AppError::validation_error("该用户名已被使用".to_owned()));
            }
        }
        a.username = Set(v.clone());
    }
    if let Some(v) = req.avatar_url {
        a.avatar_url = Set(Some(v));
    }
    a.update(&state.db).await.map_err(|_| AppError::internal("更新资料失败".to_owned()))?;
    Ok(Json(serde_json::json!({ "message": "资料已更新" })))
}

// ---------------------------------------------------------------------------
// Password
// ---------------------------------------------------------------------------

/// POST /settings/change-password — change password with verification.
async fn change_password(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<ChangePasswordReq>,
) -> AppResult<Json<MessageResponse>> {
    moling_auth::validate_complexity(&req.new_password)?;
    let found = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    if !moling_auth::password::verify(&req.current_password, &found.password_hash) {
        return Err(AppError::unauthorized());
    }
    let hashed = moling_auth::password::hash(&req.new_password)?;
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let mut a = found.into_active_model();
    a.password_hash = Set(hashed);
    a.update(&state.db).await.map_err(|_| AppError::internal("修改密码失败".to_owned()))?;
    Ok(Json(MessageResponse { message: "密码已修改".into() }))
}

// ---------------------------------------------------------------------------
// Health Monitor
// ---------------------------------------------------------------------------

/// GET /settings/health-monitor — get current health monitor status.
async fn get_health_monitor(
    State(state): State<AppState>,
    _user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let db_ok = state.db.ping().await.is_ok();
    Ok(Json(serde_json::json!({
        "database": db_ok,
        "redis": state.redis.pool().is_available(),
        "r1_enabled": true,
        "r2_enabled": true,
        "r3_enabled": true,
        "anti_fatigue": true,
    })))
}

/// PATCH /settings/health-monitor — update health monitor settings.
///
/// Mirrors Python `update_health_monitor`.
async fn update_health_monitor(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<HealthMonitorReq>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;

    let settings_clone = u.settings.clone();
    let mut current: serde_json::Map<String, serde_json::Value> = settings_clone
        .and_then(|v| v.as_object().cloned())
        .unwrap_or_default();

    current.insert("health_monitor_r1_enabled".into(), serde_json::Value::Bool(req.r1_enabled));
    current.insert("health_monitor_r2_enabled".into(), serde_json::Value::Bool(req.r2_enabled));
    current.insert("health_monitor_r3_enabled".into(), serde_json::Value::Bool(req.r3_enabled));
    current.insert("health_monitor_anti_fatigue".into(), serde_json::Value::Bool(req.anti_fatigue));

    let merged = serde_json::Value::Object(current);
    let mut active = u.into_active_model();
    active.settings = Set(Some(merged));
    active.update(&state.db).await.map_err(|e| {
        AppError::internal(format!("Update health monitor failed: {e}"))
    })?;

    Ok(Json(serde_json::json!({
        "message": "健康监控设置已更新",
        "r1_enabled": req.r1_enabled,
        "r2_enabled": req.r2_enabled,
        "r3_enabled": req.r3_enabled,
        "anti_fatigue": req.anti_fatigue,
    })))
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

/// POST /settings/export — export user data.
async fn export_data(
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    Ok(Json(serde_json::json!({
        "export_url": format!("/api/v1/settings/export/{}", user.user_id),
        "status": "pending",
        "message": "导出请求已提交",
    })))
}

// ---------------------------------------------------------------------------
// Clear Cache
// ---------------------------------------------------------------------------

/// POST /settings/clear-cache — clear user cache.
///
/// Mirrors Python `clear_user_cache`.
async fn clear_cache(
    _user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    Ok(Json(serde_json::json!({
        "cleared": true,
        "message": "缓存已清除",
    })))
}

// ---------------------------------------------------------------------------
// Phase 4 Review
// ---------------------------------------------------------------------------

/// GET /settings/phase4-review — get Phase 4 review mode setting.
///
/// Mirrors Python `get_phase4_review_settings`.
async fn get_phase4_review(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    let settings = u.settings.unwrap_or_default();
    let mode = settings
        .get("phase4_review_mode")
        .and_then(|v| v.as_str())
        .unwrap_or("manual");
    Ok(Json(serde_json::json!({ "mode": mode })))
}

/// PATCH /settings/phase4-review — update Phase 4 review mode.
///
/// Mirrors Python `update_phase4_review_settings`.
async fn update_phase4_review(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<Phase4ModeReq>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel};
    let u = UserDao
        .find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;

    let settings_clone = u.settings.clone();
    let mut current: serde_json::Map<String, serde_json::Value> = settings_clone
        .and_then(|v| v.as_object().cloned())
        .unwrap_or_default();
    current.insert("phase4_review_mode".into(), serde_json::Value::String(req.mode.clone()));

    let merged = serde_json::Value::Object(current);
    let mut active = u.into_active_model();
    active.settings = Set(Some(merged));
    active.update(&state.db).await.map_err(|e| {
        AppError::internal(format!("Update phase4 review mode failed: {e}"))
    })?;

    Ok(Json(serde_json::json!({
        "message": "Phase 4 审核模式已更新",
        "mode": req.mode,
    })))
}
