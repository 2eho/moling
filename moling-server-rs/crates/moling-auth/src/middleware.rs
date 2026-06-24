//! Auth middleware — Axum middleware for JWT bearer token verification.
//!
//! Provides three middleware functions:
//! - [`require_auth`] — rejects unauthenticated requests (401).
//! - [`optional_auth`] — extracts the user if a valid token is present,
//!   but allows unauthenticated requests to proceed.
//! - [`require_admin`] — rejects requests without admin role (403).
//!
//! All middleware functions inject [`CurrentUser`] into request extensions
//! on success.

use axum::extract::Request;
use axum::http::header;
use axum::middleware::Next;
use axum::response::Response;
use moling_core::error::AppError;
use std::sync::Arc;

use crate::extractor::CurrentUser;
use crate::jwt;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// AuthConfig
// ---------------------------------------------------------------------------

/// Configuration for the auth middleware.
#[derive(Clone)]
pub struct AuthConfig {
    /// JWT signing secret (HMAC key).
    pub secret: Arc<String>,
}

impl AuthConfig {
    /// Create a new auth config from a JWT secret.
    pub fn new(secret: impl Into<String>) -> Self {
        Self {
            secret: Arc::new(secret.into()),
        }
    }
}

// ---------------------------------------------------------------------------
// Middleware — require_auth
// ---------------------------------------------------------------------------

/// Middleware that **requires** a valid Bearer token.
///
/// Extracts the token from the `Authorization` header, verifies it, and
/// injects [`CurrentUser`] into request extensions. Returns 401 if the token
/// is missing, invalid, or expired.
///
/// # Usage
///
/// ```ignore
/// use axum::{Router, middleware};
/// let app = Router::new()
///     .route("/me", get(me_handler))
///     .layer(middleware::from_fn_with_state(
///         auth_config,
///         require_auth,
///     ));
/// ```
pub async fn require_auth(
    axum::extract::State(config): axum::extract::State<AuthConfig>,
    mut request: Request,
    next: Next,
) -> Result<Response, AppError> {
    // Extract the Bearer token
    let token = extract_bearer_token(request.headers())?;

    // Verify the JWT
    let claims = jwt::verify_token(&token, &config.secret)?;

    // Parse the user_id from the claims
    let user_id = Uuid::parse_str(&claims.sub).map_err(|e| {
        tracing::warn!(sub = %claims.sub, "Auth: invalid user_id in JWT: {e}");
        AppError::token_invalid()
    })?;

    // Inject CurrentUser into extensions (includes email + role)
    request
        .extensions_mut()
        .insert(CurrentUser::new(user_id, claims.email, claims.role));

    let response = next.run(request).await;
    Ok(response)
}

// ---------------------------------------------------------------------------
// Middleware — optional_auth
// ---------------------------------------------------------------------------

/// Middleware that **optionally** extracts a Bearer token.
///
/// If a valid token is present, injects [`CurrentUser`] into request
/// extensions. If no token or an invalid token is present, the request
/// proceeds unauthenticated (no rejection).
pub async fn optional_auth(
    axum::extract::State(config): axum::extract::State<AuthConfig>,
    mut request: Request,
    next: Next,
) -> Response {
    // Try to extract and verify — silently skip on failure
    if let Ok(token) = extract_bearer_token(request.headers())
        && let Ok(claims) = jwt::verify_token(&token, &config.secret)
            && let Ok(user_id) = Uuid::parse_str(&claims.sub) {
                request
                    .extensions_mut()
                    .insert(CurrentUser::new(user_id, claims.email, claims.role));
            }

    next.run(request).await
}

// ---------------------------------------------------------------------------
// Middleware — require_admin
// ---------------------------------------------------------------------------

/// Middleware that **requires** an admin-role Bearer token.
///
/// First performs the same JWT verification as [`require_auth`], then
/// additionally checks that the token's `role` claim is `"admin"`.
/// Returns 401 if the token is missing/invalid, 403 if the user is
/// authenticated but lacks the admin role.
///
/// # Usage
///
/// ```ignore
/// use axum::{Router, middleware};
/// let app = Router::new()
///     .route("/admin/users", get(list_users_handler))
///     .layer(middleware::from_fn_with_state(
///         auth_config.clone(),
///         require_admin,
///     ));
/// ```
pub async fn require_admin(
    axum::extract::State(config): axum::extract::State<AuthConfig>,
    mut request: Request,
    next: Next,
) -> Result<Response, AppError> {
    // Step 1: Extract and verify the JWT (same as require_auth)
    let token = extract_bearer_token(request.headers())?;
    let claims = jwt::verify_token(&token, &config.secret)?;

    // Step 2: Check admin role
    if claims.role != "admin" {
        tracing::warn!(
            user_id = %claims.sub,
            role = %claims.role,
            "Auth: admin access denied — insufficient role"
        );
        return Err(AppError::new(
            moling_core::error::ErrorCode::AuthInsufficientPermissions,
        ));
    }

    // Step 3: Parse user_id and inject CurrentUser
    let user_id = Uuid::parse_str(&claims.sub).map_err(|e| {
        tracing::warn!(sub = %claims.sub, "Auth: invalid user_id in JWT: {e}");
        AppError::token_invalid()
    })?;

    request
        .extensions_mut()
        .insert(CurrentUser::new(user_id, claims.email, claims.role));

    let response = next.run(request).await;
    Ok(response)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Extract the Bearer token from the Authorization header.
///
/// Returns `AppError` (401) if the header is missing or malformed.
fn extract_bearer_token(headers: &axum::http::HeaderMap) -> Result<String, AppError> {
    let header_value = headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .ok_or_else(AppError::unauthorized)?;

    // Must start with "Bearer "
    let token = header_value
        .strip_prefix("Bearer ")
        .ok_or_else(AppError::unauthorized)?;

    if token.is_empty() {
        return Err(AppError::unauthorized());
    }

    Ok(token.to_owned())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::http::HeaderValue;

    fn make_headers(bearer: Option<&str>) -> axum::http::HeaderMap {
        let mut headers = axum::http::HeaderMap::new();
        if let Some(b) = bearer {
            headers.insert(
                header::AUTHORIZATION,
                HeaderValue::from_str(&format!("Bearer {b}")).unwrap(),
            );
        }
        headers
    }

    #[test]
    fn test_extract_valid_bearer() {
        let headers = make_headers(Some("my-token-123"));
        let token = extract_bearer_token(&headers).unwrap();
        assert_eq!(token, "my-token-123");
    }

    #[test]
    fn test_extract_missing_header() {
        let headers = make_headers(None);
        let result = extract_bearer_token(&headers);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_wrong_prefix() {
        let mut headers = axum::http::HeaderMap::new();
        headers.insert(
            header::AUTHORIZATION,
            HeaderValue::from_static("Basic dXNlcjpwYXNz"),
        );
        let result = extract_bearer_token(&headers);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_empty_token() {
        let mut headers = axum::http::HeaderMap::new();
        headers.insert(
            header::AUTHORIZATION,
            HeaderValue::from_static("Bearer "),
        );
        let result = extract_bearer_token(&headers);
        assert!(result.is_err());
    }
}
