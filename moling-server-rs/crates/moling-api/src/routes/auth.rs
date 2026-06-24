//! Auth routes — registration, login, token refresh, logout, password reset.

use axum::{extract::State, routing::post, Json, Router};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::user_dao::UserDao;
use moling_auth::{generate_access_token, generate_refresh_token, verify_token, hash, TokenBlacklist};
use crate::state::AppState;
use crate::types::*;

/// Build auth router: `/auth/*`
pub fn router() -> Router<AppState> {
    Router::new()
        .route("/register", post(register))
        .route("/login", post(login))
        .route("/refresh", post(refresh))
        .route("/logout", post(logout))
        .route("/me", axum::routing::get(get_me))
        .route("/password-reset-request", post(password_reset_request))
        .route("/password-reset", post(password_reset))
        .route("/me", axum::routing::put(update_me))
}

/// POST /auth/register — register a new user.
///
/// Creates a new user account and returns JWT tokens.
#[utoipa::path(
    post,
    path = "/api/v1/auth/register",
    request_body = RegisterReq,
    responses(
        (status = 200, description = "Registration successful", body = TokenResp),
        (status = 409, description = "Email or username already exists"),
        (status = 422, description = "Validation error")
    )
)]
pub async fn register(
    State(state): State<AppState>,
    Json(req): Json<RegisterReq>,
) -> AppResult<Json<TokenResp>> {
    let dao = UserDao;
    if dao.email_exists(&state.db, &req.email).await? {
        return Err(AppError::conflict("该邮箱已被注册".to_owned()));
    }
    if dao.username_exists(&state.db, &req.nickname).await? {
        return Err(AppError::conflict("该用户名已被使用".to_owned()));
    }
    moling_auth::validate_complexity(&req.password)?;

    let hashed = hash(&req.password)?;
    let now = chrono::Utc::now();
    let user_id = uuid::Uuid::new_v4().to_string();

    let model = moling_db::entities::user::ActiveModel {
        id: sea_orm::Set(user_id.clone()),
        email: sea_orm::Set(req.email.clone()),
        username: sea_orm::Set(req.nickname.clone()),
        password_hash: sea_orm::Set(hashed),
        status: sea_orm::Set("active".into()),
        created_at: sea_orm::Set(now),
        updated_at: sea_orm::Set(now),
        ..Default::default()
    };
    let user = dao.create(&state.db, model).await?;

    let secret = &state.settings.secret_key;
    let uid = uuid::Uuid::parse_str(&user.id).map_err(|_| AppError::internal("Invalid user id".to_owned()))?;
    let (access_token, _) = generate_access_token(&uid, secret, &user.email, "user")?;
    let (refresh_token, _) = generate_refresh_token(&uid, secret, &user.email, "user")?;

    Ok(Json(TokenResp {
        access_token,
        refresh_token,
        token_type: "bearer".into(),
        expires_in: state.settings.access_token_expire_minutes * 60,
        user: user_to_resp(&user),
    }))
}

/// POST /auth/login — authenticate and return tokens.
///
/// Returns JWT access + refresh tokens on success.
#[utoipa::path(
    post,
    path = "/api/v1/auth/login",
    request_body = LoginReq,
    responses(
        (status = 200, description = "Login successful", body = TokenResp),
        (status = 401, description = "Invalid credentials"),
        (status = 423, description = "Account locked")
    )
)]
pub async fn login(
    State(state): State<AppState>,
    Json(req): Json<LoginReq>,
) -> AppResult<Json<TokenResp>> {
    let dao = UserDao;
    let user = dao.find_by_email(&state.db, &req.email)
        .await?
        .ok_or_else(AppError::unauthorized)?;

    if !moling_auth::password::verify(&req.password, &user.password_hash) {
        return Err(AppError::unauthorized());
    }

    if user.status != "active" {
        return Err(AppError::forbidden());
    }

    let secret = &state.settings.secret_key;
    let uid = uuid::Uuid::parse_str(&user.id).map_err(|_| AppError::internal("Invalid user id".to_owned()))?;
    let (access_token, _) = generate_access_token(&uid, secret, &user.email, "user")?;
    let (refresh_token, _) = generate_refresh_token(&uid, secret, &user.email, "user")?;

    Ok(Json(TokenResp {
        access_token,
        refresh_token,
        token_type: "bearer".into(),
        expires_in: state.settings.access_token_expire_minutes * 60,
        user: user_to_resp(&user),
    }))
}

/// POST /auth/refresh — refresh an access token using a refresh token.
#[utoipa::path(
    post,
    path = "/api/v1/auth/refresh",
    request_body = RefreshReq,
    responses(
        (status = 200, description = "Token refreshed successfully", body = TokenResp),
        (status = 401, description = "Invalid or expired refresh token")
    )
)]
pub async fn refresh(
    State(state): State<AppState>,
    Json(req): Json<RefreshReq>,
) -> AppResult<Json<TokenResp>> {
    let secret = &state.settings.secret_key;
    let claims = verify_token(&req.refresh_token, secret)?;
    if claims.token_type != "refresh" {
        return Err(AppError::token_invalid());
    }

    let dao = UserDao;
    let user = dao.find_by_id(&state.db, &claims.sub).await?
        .ok_or_else(AppError::unauthorized)?;

    let uid = uuid::Uuid::parse_str(&user.id).map_err(|_| AppError::internal("Invalid user id".to_owned()))?;
    let (access_token, _) = generate_access_token(&uid, secret, &user.email, "user")?;
    let (new_refresh_token, _) = generate_refresh_token(&uid, secret, &user.email, "user")?;

    Ok(Json(TokenResp {
        access_token,
        refresh_token: new_refresh_token,
        token_type: "bearer".into(),
        expires_in: state.settings.access_token_expire_minutes * 60,
        user: user_to_resp(&user),
    }))
}

/// POST /auth/logout — blacklist tokens and log out.
#[utoipa::path(
    post,
    path = "/api/v1/auth/logout",
    request_body = LogoutReq,
    responses(
        (status = 200, description = "Logged out successfully", body = MessageResponse)
    )
)]
pub async fn logout(
    State(state): State<AppState>,
    Json(req): Json<LogoutReq>,
) -> AppResult<Json<MessageResponse>> {
    let blacklist = TokenBlacklist::new(state.redis.clone());
    let secret = &state.settings.secret_key;

    if let Ok(claims) = moling_auth::jwt::decode_without_expiry(&req.access_token, secret) {
        let ttl = std::time::Duration::from_secs(
            claims.exp.saturating_sub(chrono::Utc::now().timestamp() as usize) as u64,
        );
        let _ = blacklist.blacklist_token(&claims.jti, ttl).await;
    }
    if let Ok(claims) = moling_auth::jwt::decode_without_expiry(&req.refresh_token, secret) {
        let ttl = std::time::Duration::from_secs(
            claims.exp.saturating_sub(chrono::Utc::now().timestamp() as usize) as u64,
        );
        let _ = blacklist.blacklist_token(&claims.jti, ttl).await;
    }

    Ok(Json(MessageResponse { message: "Successfully logged out".into() }))
}

/// GET /auth/me — get current user profile.
#[utoipa::path(
    get,
    path = "/api/v1/auth/me",
    responses(
        (status = 200, description = "Current user profile", body = UserResp),
        (status = 401, description = "Not authenticated")
    )
)]
pub async fn get_me(
    State(state): State<AppState>,
    user: moling_auth::CurrentUser,
) -> AppResult<Json<UserResp>> {
    let dao = UserDao;
    let found = dao.find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    Ok(Json(user_to_resp(&found)))
}

/// PUT /auth/me — update current user profile.
#[utoipa::path(
    put,
    path = "/api/v1/auth/me",
    request_body = UpdateProfileReq,
    responses(
        (status = 200, description = "Profile updated", body = UserResp),
        (status = 401, description = "Not authenticated"),
        (status = 404, description = "User not found")
    )
)]
pub async fn update_me(
    State(state): State<AppState>,
    user: moling_auth::CurrentUser,
    Json(req): Json<UpdateProfileReq>,
) -> AppResult<Json<UserResp>> {
    use sea_orm::{ActiveModelTrait, IntoActiveModel, Set};
    let dao = UserDao;
    let found = dao.find_by_id(&state.db, &user.user_id.to_string())
        .await?
        .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))?;
    let mut active = found.into_active_model();
    if let Some(name) = &req.username {
        active.username = Set(name.clone());
    }
    if let Some(av) = &req.avatar_url {
        active.avatar_url = Set(Some(av.clone()));
    }
    let updated = active.update(&state.db).await.map_err(|e| {
        AppError::internal(format!("更新用户资料失败: {e}"))
    })?;
    Ok(Json(user_to_resp(&updated)))
}

/// POST /auth/password-reset-request — request a password reset.
#[utoipa::path(
    post,
    path = "/api/v1/auth/password-reset-request",
    request_body = PasswordResetRequestReq,
    responses(
        (status = 200, description = "Reset request processed", body = MessageResponse)
    )
)]
pub async fn password_reset_request(
    State(state): State<AppState>,
    Json(req): Json<PasswordResetRequestReq>,
) -> AppResult<Json<MessageResponse>> {
    let dao = UserDao;
    if let Some(user) = dao.find_by_email(&state.db, &req.email).await? {
        use sea_orm::{ActiveModelTrait, IntoActiveModel, Set};
        let token = uuid::Uuid::new_v4().to_string();
        let expires = chrono::Utc::now() + chrono::TimeDelta::hours(24);
        let mut active = user.into_active_model();
        active.reset_token = Set(Some(token));
        active.reset_token_expires = Set(Some(expires));
        let _ = active.update(&state.db).await;
    }
    Ok(Json(MessageResponse { message: "If the email exists, a reset link has been sent.".into() }))
}

/// POST /auth/password-reset — reset password with token.
#[utoipa::path(
    post,
    path = "/api/v1/auth/password-reset",
    request_body = PasswordResetReq,
    responses(
        (status = 200, description = "Password reset successful", body = MessageResponse),
        (status = 401, description = "Invalid or expired reset token"),
        (status = 422, description = "Password does not meet complexity requirements")
    )
)]
pub async fn password_reset(
    State(state): State<AppState>,
    Json(req): Json<PasswordResetReq>,
) -> AppResult<Json<MessageResponse>> {
    use sea_orm::{ActiveModelTrait, ColumnTrait, EntityTrait, IntoActiveModel, QueryFilter, Set};
    moling_auth::validate_complexity(&req.new_password)?;
    let user = moling_db::entities::user::Entity::find()
        .filter(moling_db::entities::user::Column::ResetToken.eq(&req.token))
        .one(&state.db)
        .await
        .map_err(|_| AppError::token_invalid())?
        .ok_or_else(AppError::token_invalid)?;

    if user.reset_token_expires.is_none_or(|e| e < chrono::Utc::now()) {
        return Err(AppError::token_invalid());
    }

    let hashed = hash(&req.new_password)?;
    let mut active = user.into_active_model();
    active.password_hash = Set(hashed);
    active.reset_token = Set(None);
    active.reset_token_expires = Set(None);
    active.update(&state.db).await.map_err(|_| AppError::internal("Password reset failed".to_owned()))?;

    Ok(Json(MessageResponse { message: "Password reset successful.".into() }))
}

fn user_to_resp(u: &moling_db::entities::user::Model) -> UserResp {
    UserResp {
        id: u.id.clone(),
        email: u.email.clone(),
        nickname: u.username.clone(),
        avatar_url: u.avatar_url.clone(),
        status: u.status.clone(),
        created_at: u.created_at,
        updated_at: u.updated_at,
    }
}
