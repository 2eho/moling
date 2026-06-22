//! CurrentUser extractor — Axum [`FromRequestParts`] impl.
//!
//! Extracts the authenticated user from request extensions injected by
//! the auth middleware. Routes that require authentication should use
//! `CurrentUser` as a handler parameter.
//!
//! # Extractors
//!
//! | Extractor             | Rejection | Use case                              |
//! |-----------------------|-----------|---------------------------------------|
//! | [`CurrentUser`]       | 401       | Routes requiring authentication       |
//! | [`OptionalCurrentUser`] | never   | Routes that optionally personalize    |
//! | [`AdminUser`]         | 403       | Admin-only routes                     |

use axum::extract::FromRequestParts;
use axum::http::request::Parts;
use moling_core::error::{AppError, ErrorCode};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// CurrentUser
// ---------------------------------------------------------------------------

/// Authenticated user identity extracted from request extensions.
///
/// Injected by the auth middleware after successful JWT verification.
/// Handlers that require authentication should declare this as a parameter:
///
/// ```ignore
/// async fn my_handler(user: CurrentUser) -> impl IntoResponse {
///     format!("Hello, {} ({})", user.email, user.user_id)
/// }
/// ```
#[derive(Debug, Clone)]
pub struct CurrentUser {
    /// The authenticated user's UUID.
    pub user_id: Uuid,
    /// The user's email address (from JWT claims).
    pub email: String,
    /// The user's role: `"user"` or `"admin"` (from JWT claims).
    pub role: String,
}

impl CurrentUser {
    /// Create a new CurrentUser from the JWT claims data.
    pub fn new(user_id: Uuid, email: String, role: String) -> Self {
        Self {
            user_id,
            email,
            role,
        }
    }
}

// ---------------------------------------------------------------------------
// FromRequestParts impl for CurrentUser
// ---------------------------------------------------------------------------

impl<S> FromRequestParts<S> for CurrentUser
where
    S: Send + Sync,
{
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        _state: &S,
    ) -> Result<Self, Self::Rejection> {
        parts
            .extensions
            .get::<CurrentUser>()
            .cloned()
            .ok_or_else(AppError::unauthorized)
    }
}

// ---------------------------------------------------------------------------
// OptionalCurrentUser
// ---------------------------------------------------------------------------

/// Optional authenticated user identity.
///
/// For routes that work with or without authentication (e.g. public endpoints
/// that optionally personalize content). Returns `None` when no auth token
/// is present, never rejects the request.
#[derive(Debug, Clone)]
pub struct OptionalCurrentUser {
    /// May be `None` for unauthenticated requests.
    pub user: Option<CurrentUser>,
}

impl<S> FromRequestParts<S> for OptionalCurrentUser
where
    S: Send + Sync,
{
    type Rejection = std::convert::Infallible;

    async fn from_request_parts(
        parts: &mut Parts,
        _state: &S,
    ) -> Result<Self, Self::Rejection> {
        let user = parts.extensions.get::<CurrentUser>().cloned();
        Ok(Self { user })
    }
}

// ---------------------------------------------------------------------------
// AdminUser
// ---------------------------------------------------------------------------

/// Authenticated admin user — rejects non-admin users with 403.
///
/// Requires that the authenticated user has `role == "admin"` in their
/// JWT claims. Use this for admin-only endpoints:
///
/// ```ignore
/// async fn delete_user(admin: AdminUser, Path(user_id): Path<Uuid>) -> impl IntoResponse {
///     // Only admins can reach this handler
/// }
/// ```
#[derive(Debug, Clone)]
pub struct AdminUser {
    /// The admin's UUID.
    pub user_id: Uuid,
    /// The admin's email address.
    pub email: String,
}

impl AdminUser {
    /// Create a new AdminUser (caller must have already verified the role).
    pub fn new(user_id: Uuid, email: String) -> Self {
        Self { user_id, email }
    }
}

impl<S> FromRequestParts<S> for AdminUser
where
    S: Send + Sync,
{
    type Rejection = AppError;

    async fn from_request_parts(
        parts: &mut Parts,
        _state: &S,
    ) -> Result<Self, Self::Rejection> {
        let current = parts
            .extensions
            .get::<CurrentUser>()
            .ok_or_else(AppError::unauthorized)?;

        if current.role != "admin" {
            return Err(AppError::new(ErrorCode::AuthInsufficientPermissions));
        }

        Ok(Self {
            user_id: current.user_id,
            email: current.email.clone(),
        })
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_current_user_creation() {
        let user_id = Uuid::new_v4();
        let user = CurrentUser::new(user_id, "admin@moling.io".into(), "admin".into());
        assert_eq!(user.user_id, user_id);
        assert_eq!(user.email, "admin@moling.io");
        assert_eq!(user.role, "admin");
    }

    #[test]
    fn test_admin_user_creation() {
        let user_id = Uuid::new_v4();
        let admin = AdminUser::new(user_id, "root@moling.io".into());
        assert_eq!(admin.user_id, user_id);
        assert_eq!(admin.email, "root@moling.io");
    }
}
