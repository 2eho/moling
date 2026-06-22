//! 墨灵 (Moling) — Centralized error system.
//!
//! Ported from Python `app/errors.py` — all domain-level errors carry
//! a machine-readable [`ErrorCode`] and produce a JSON response matching
//! the Python format:
//! ```json
//! {"code": "PROJECT_NOT_FOUND", "message": "项目不存在", "detail": null}
//! ```

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use std::fmt;

// ---------------------------------------------------------------------------
// ErrorCode — machine-readable error codes
// ---------------------------------------------------------------------------

/// Machine-readable error codes — ported from Python `ErrorCode` enum.
///
/// Serialised as `SCREAMING_SNAKE_CASE` to match the Python JSON format.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    // ---- Auth (401xx) ----
    #[serde(rename = "AUTH_INVALID_CREDENTIALS")]
    AuthInvalidCredentials,
    #[serde(rename = "AUTH_TOKEN_EXPIRED")]
    AuthTokenExpired,
    #[serde(rename = "AUTH_INVALID_TOKEN")]
    AuthInvalidToken,
    #[serde(rename = "AUTH_INSUFFICIENT_PERMISSIONS")]
    AuthInsufficientPermissions,

    // ---- User (404xx / 409xx) ----
    #[serde(rename = "USER_NOT_FOUND")]
    UserNotFound,
    #[serde(rename = "USER_EMAIL_EXISTS")]
    UserEmailExists,
    #[serde(rename = "USER_USERNAME_EXISTS")]
    UserUsernameExists,

    // ---- Project (404xx / 403xx) ----
    #[serde(rename = "PROJECT_NOT_FOUND")]
    ProjectNotFound,
    #[serde(rename = "PROJECT_ACCESS_DENIED")]
    ProjectAccessDenied,

    // ---- Chapter (404xx / 409xx) ----
    #[serde(rename = "CHAPTER_NOT_FOUND")]
    ChapterNotFound,
    #[serde(rename = "CHAPTER_NUMBER_EXISTS")]
    ChapterNumberExists,

    // ---- Card Pool / Card (404xx) ----
    #[serde(rename = "CARD_POOL_NOT_FOUND")]
    CardPoolNotFound,
    #[serde(rename = "CARD_NOT_FOUND")]
    CardNotFound,

    // ---- Vault (404xx) ----
    #[serde(rename = "VAULT_ENTRY_NOT_FOUND")]
    VaultEntryNotFound,

    // ---- Generation (404xx / 409xx) ----
    #[serde(rename = "GENERATION_TASK_NOT_FOUND")]
    GenerationTaskNotFound,
    #[serde(rename = "GENERATION_IN_PROGRESS")]
    GenerationInProgress,

    // ---- Permission (403xx) ----
    #[serde(rename = "FORBIDDEN")]
    Forbidden,

    // ---- General (4xx / 5xx) ----
    #[serde(rename = "INVALID_REQUEST")]
    InvalidRequest,
    #[serde(rename = "VALIDATION_ERROR")]
    ValidationError,
    #[serde(rename = "RATE_LIMIT_EXCEEDED")]
    RateLimitExceeded,
    #[serde(rename = "INTERNAL_ERROR")]
    InternalError,
}

impl fmt::Display for ErrorCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let msg = self.chinese_message();
        write!(f, "{msg}")
    }
}

impl ErrorCode {
    /// Return the Chinese human-readable message (mirrors Python `_ERROR_MESSAGES`).
    pub fn chinese_message(self) -> &'static str {
        match self {
            Self::AuthInvalidCredentials => "邮箱或密码错误",
            Self::AuthTokenExpired => "登录已过期，请重新登录",
            Self::AuthInvalidToken => "无效的认证令牌",
            Self::AuthInsufficientPermissions => "权限不足",
            Self::Forbidden => "权限不足",
            Self::UserNotFound => "用户不存在",
            Self::UserEmailExists => "该邮箱已被注册",
            Self::UserUsernameExists => "该用户名已被使用",
            Self::ProjectNotFound => "项目不存在",
            Self::ProjectAccessDenied => "无权访问该项目",
            Self::ChapterNotFound => "章节不存在",
            Self::ChapterNumberExists => "章节编号已存在",
            Self::CardPoolNotFound => "卡池不存在",
            Self::CardNotFound => "卡片不存在",
            Self::VaultEntryNotFound => "四库条目不存在",
            Self::GenerationTaskNotFound => "生成任务不存在",
            Self::GenerationInProgress => "正在生成中，请稍后再试",
            Self::InvalidRequest => "请求参数无效",
            Self::ValidationError => "请求参数验证失败",
            Self::RateLimitExceeded => "请求过于频繁，请稍后再试",
            Self::InternalError => "服务器内部错误",
        }
    }

    /// Map to an HTTP status code (mirrors Python `_ERROR_TO_STATUS`).
    pub fn http_status(self) -> StatusCode {
        match self {
            Self::AuthInvalidCredentials
            | Self::AuthTokenExpired
            | Self::AuthInvalidToken => StatusCode::UNAUTHORIZED,

            Self::AuthInsufficientPermissions
            | Self::Forbidden
            | Self::ProjectAccessDenied => StatusCode::FORBIDDEN,

            Self::UserNotFound
            | Self::ProjectNotFound
            | Self::ChapterNotFound
            | Self::CardPoolNotFound
            | Self::CardNotFound
            | Self::VaultEntryNotFound
            | Self::GenerationTaskNotFound => StatusCode::NOT_FOUND,

            Self::UserEmailExists
            | Self::UserUsernameExists
            | Self::ChapterNumberExists
            | Self::GenerationInProgress => StatusCode::CONFLICT,

            Self::InvalidRequest => StatusCode::BAD_REQUEST,
            Self::ValidationError => StatusCode::UNPROCESSABLE_ENTITY,
            Self::RateLimitExceeded => StatusCode::TOO_MANY_REQUESTS,
            Self::InternalError => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

// ---------------------------------------------------------------------------
// AppError — the domain-level error type
// ---------------------------------------------------------------------------

/// Application error with code, message, and optional detail.
///
/// Implements [`IntoResponse`] so it can be returned directly from Axum handlers.
#[derive(Debug)]
pub struct AppError {
    pub code: ErrorCode,
    pub message: String,
    pub detail: Option<String>,
}

impl AppError {
    // -- constructors --

    pub fn new(code: ErrorCode) -> Self {
        let message = code.chinese_message().to_owned();
        Self {
            code,
            message,
            detail: None,
        }
    }

    pub fn with_detail(code: ErrorCode, detail: impl Into<String>) -> Self {
        let message = code.chinese_message().to_owned();
        Self {
            code,
            message,
            detail: Some(detail.into()),
        }
    }

    /// 404 Not Found
    pub fn not_found(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::ProjectNotFound,
            message: msg.into(),
            detail: None,
        }
    }

    /// 401 Unauthorized
    pub fn unauthorized() -> Self {
        Self::new(ErrorCode::AuthInvalidCredentials)
    }

    /// 403 Forbidden
    pub fn forbidden() -> Self {
        Self::new(ErrorCode::Forbidden)
    }

    /// 400 Bad Request
    pub fn bad_request(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::InvalidRequest,
            message: msg.into(),
            detail: None,
        }
    }

    /// 409 Conflict
    pub fn conflict(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::UserEmailExists,
            message: msg.into(),
            detail: None,
        }
    }

    /// 422 Validation Error
    pub fn validation_error(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::ValidationError,
            message: msg.into(),
            detail: None,
        }
    }

    /// 429 Rate Limit Exceeded
    pub fn rate_limit() -> Self {
        Self::new(ErrorCode::RateLimitExceeded)
    }

    /// 500 Internal Server Error
    pub fn internal(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::InternalError,
            message: msg.into(),
            detail: None,
        }
    }

    // -- domain-specific constructors --

    pub fn token_expired() -> Self {
        Self::new(ErrorCode::AuthTokenExpired)
    }

    pub fn token_invalid() -> Self {
        Self::new(ErrorCode::AuthInvalidToken)
    }

    pub fn project_not_found() -> Self {
        Self::new(ErrorCode::ProjectNotFound)
    }

    pub fn project_access_denied() -> Self {
        Self::new(ErrorCode::ProjectAccessDenied)
    }

    pub fn chapter_not_found() -> Self {
        Self::new(ErrorCode::ChapterNotFound)
    }

    pub fn card_not_found() -> Self {
        Self::new(ErrorCode::CardNotFound)
    }

    pub fn vault_entry_not_found() -> Self {
        Self::new(ErrorCode::VaultEntryNotFound)
    }

    pub fn generation_task_not_found() -> Self {
        Self::new(ErrorCode::GenerationTaskNotFound)
    }

    pub fn generation_in_progress() -> Self {
        Self::new(ErrorCode::GenerationInProgress)
    }

    pub fn validation_failed(msg: impl Into<String>) -> Self {
        Self {
            code: ErrorCode::ValidationError,
            message: msg.into(),
            detail: None,
        }
    }

    // -- accessors --

    pub fn status(&self) -> StatusCode {
        self.code.http_status()
    }
}

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.detail {
            Some(d) => write!(f, "{} — {d}", self.message),
            None => write!(f, "{}", self.message),
        }
    }
}

// ---------------------------------------------------------------------------
// std::error::Error
// ---------------------------------------------------------------------------

impl std::error::Error for AppError {}

// ---------------------------------------------------------------------------
// axum IntoResponse — JSON response matching Python format
// ---------------------------------------------------------------------------

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = self.status();
        let body = serde_json::json!({
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        });

        (status, axum::Json(body)).into_response()
    }
}

// ---------------------------------------------------------------------------
// Convenience type alias
// ---------------------------------------------------------------------------

/// Result with AppError as the error type — used across all handlers.
pub type AppResult<T> = std::result::Result<T, AppError>;
