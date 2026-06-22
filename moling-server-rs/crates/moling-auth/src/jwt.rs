//! JWT token generation and verification.
//!
//! Uses HS256 (HMAC-SHA256) symmetric signing matching the
//! Python `jose.jwt` implementation. Each token carries a unique
//! JTI (JWT ID) for blacklist support and token rotation (HH11).
//!
//! # Token payload
//!
//! | Field | Type   | Description                               |
//! |-------|--------|-------------------------------------------|
//! | sub   | String | User ID (UUID)                            |
//! | type  | String | `"access"` or `"refresh"`                 |
//! | email | String | User email (for convenience / audit)      |
//! | role  | String | User role: `"user"` or `"admin"`          |
//! | iat   | usize  | Issued-at timestamp (Unix epoch seconds)  |
//! | exp   | usize  | Expiration timestamp (Unix epoch seconds) |
//! | jti   | String | JWT ID — unique per-token for blacklisting|

use chrono::{TimeDelta, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use moling_core::error::{AppError, AppResult};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Default access token lifetime: 15 minutes (matches Python `ACCESS_TOKEN_EXPIRE_MINUTES`).
pub const DEFAULT_ACCESS_MINUTES: i64 = 15;

/// Default refresh token lifetime: 7 days (matches Python `REFRESH_TOKEN_EXPIRE_DAYS`).
pub const DEFAULT_REFRESH_DAYS: i64 = 7;

/// JWT algorithm in use.
const ALGORITHM: jsonwebtoken::Algorithm = jsonwebtoken::Algorithm::HS256;

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

/// Standard JWT claims carried in access and refresh tokens.
///
/// Mirrors Python `_create_access_token` / `_create_refresh_token` payload
/// with additional `email` and `role` fields for downstream authorization
/// (e.g. `require_admin` middleware) without a database round-trip.
///
/// `email` and `role` use `#[serde(default)]` for backward compatibility
/// with tokens issued before these fields were added.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    /// Subject — the user's database ID (UUID as string).
    pub sub: String,
    /// Token type: `"access"` or `"refresh"`.
    #[serde(rename = "type")]
    pub token_type: String,
    /// User email address (for audit / convenience).
    #[serde(default)]
    pub email: String,
    /// User role: `"user"` or `"admin"`.
    #[serde(default = "default_role")]
    pub role: String,
    /// Issued-at timestamp (Unix epoch seconds).
    pub iat: usize,
    /// Expiration timestamp (Unix epoch seconds).
    pub exp: usize,
    /// JWT ID — unique per-token identifier for blacklisting.
    pub jti: String,
}

/// Default role for backward-compatible deserialization.
fn default_role() -> String {
    "user".to_owned()
}

// ---------------------------------------------------------------------------
// Token generation
// ---------------------------------------------------------------------------

/// Generate a short-lived access token (default 15 min).
///
/// Returns `(token, jti)` — the JTI is needed for logout / blacklisting.
///
/// # Arguments
///
/// * `user_id` — The user's UUID.
/// * `email` — The user's email address (stored in claim for audit).
/// * `role` — The user's role (`"user"` or `"admin"`).
/// * `secret` — JWT signing secret.
pub fn generate_access_token(
    user_id: &Uuid,
    email: &str,
    role: &str,
    secret: &str,
) -> AppResult<(String, String)> {
    generate_access_token_with_ttl(user_id, email, role, secret, DEFAULT_ACCESS_MINUTES)
}

/// Generate an access token with a custom TTL in minutes.
pub fn generate_access_token_with_ttl(
    user_id: &Uuid,
    email: &str,
    role: &str,
    secret: &str,
    ttl_minutes: i64,
) -> AppResult<(String, String)> {
    let now = Utc::now();
    let iat = now.timestamp() as usize;
    let exp = (now + TimeDelta::minutes(ttl_minutes)).timestamp() as usize;
    let jti = Uuid::new_v4().to_string();

    let claims = Claims {
        sub: user_id.to_string(),
        token_type: "access".to_owned(),
        email: email.to_owned(),
        role: role.to_owned(),
        iat,
        exp,
        jti: jti.clone(),
    };

    let token = encode(
        &Header::new(ALGORITHM),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .map_err(|e| {
        tracing::error!(user_id = %user_id, "JWT: encode access token failed: {e}");
        AppError::internal("Token generation failed")
    })?;

    Ok((token, jti))
}

/// Generate a long-lived refresh token (default 7 days).
///
/// Returns `(token, jti)` — the JTI supports token rotation (HH11).
///
/// # Arguments
///
/// * `user_id` — The user's UUID.
/// * `email` — The user's email address.
/// * `role` — The user's role.
/// * `secret` — JWT signing secret.
pub fn generate_refresh_token(
    user_id: &Uuid,
    email: &str,
    role: &str,
    secret: &str,
) -> AppResult<(String, String)> {
    generate_refresh_token_with_ttl(user_id, email, role, secret, DEFAULT_REFRESH_DAYS)
}

/// Generate a refresh token with a custom TTL in days.
pub fn generate_refresh_token_with_ttl(
    user_id: &Uuid,
    email: &str,
    role: &str,
    secret: &str,
    ttl_days: i64,
) -> AppResult<(String, String)> {
    let now = Utc::now();
    let iat = now.timestamp() as usize;
    let exp = (now + TimeDelta::days(ttl_days)).timestamp() as usize;
    let jti = Uuid::new_v4().to_string();

    let claims = Claims {
        sub: user_id.to_string(),
        token_type: "refresh".to_owned(),
        email: email.to_owned(),
        role: role.to_owned(),
        iat,
        exp,
        jti: jti.clone(),
    };

    let token = encode(
        &Header::new(ALGORITHM),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .map_err(|e| {
        tracing::error!(user_id = %user_id, "JWT: encode refresh token failed: {e}");
        AppError::internal("Token generation failed")
    })?;

    Ok((token, jti))
}

// ---------------------------------------------------------------------------
// Token verification
// ---------------------------------------------------------------------------

/// Verify a JWT and return its claims.
///
/// Does **not** check the blacklist — callers must check `Blacklist::is_blacklisted`
/// separately if token revocation is required.
pub fn verify_token(token: &str, secret: &str) -> AppResult<Claims> {
    let mut validation = Validation::new(ALGORITHM);
    // Disable clock-skew leeway for deterministic expiry
    validation.leeway = 0;

    let data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )
    .map_err(|e| {
        match e.kind() {
            jsonwebtoken::errors::ErrorKind::ExpiredSignature => {
                AppError::token_expired()
            }
            _ => {
                tracing::warn!("JWT: verification failed: {e}");
                AppError::token_invalid()
            }
        }
    })?;

    Ok(data.claims)
}

/// Verify a token without requiring expiry validation.
///
/// Useful for extracting the JTI from a potentially-expired token
/// during logout / blacklisting.
pub fn decode_without_expiry(token: &str, secret: &str) -> AppResult<Claims> {
    let mut validation = Validation::new(ALGORITHM);
    validation.validate_exp = false;

    let data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )
    .map_err(|e| {
        tracing::warn!("JWT: lenient decode failed: {e}");
        AppError::token_invalid()
    })?;

    Ok(data.claims)
}

// ---------------------------------------------------------------------------
// Token rotation (HH11)
// ---------------------------------------------------------------------------

/// Information needed to revoke an old refresh token during rotation.
///
/// Returned by [`extract_rotation_info`] after verifying the old refresh token
/// before issuing a new pair. The caller should:
/// 1. Verify the token type is `"refresh"`.
/// 2. Blacklist the `old_jti` with `ttl_remaining` seconds.
/// 3. Issue new access + refresh tokens.
#[derive(Debug, Clone)]
pub struct RotationInfo {
    /// The user ID from the old refresh token.
    pub user_id: String,
    /// The old refresh token's JTI (must be blacklisted).
    pub old_jti: String,
    /// Remaining TTL in seconds for the old refresh token.
    /// Use this as the blacklist TTL to avoid storing expired entries.
    pub ttl_remaining: u64,
}

/// Verify a refresh token and extract rotation info for HH11 token rotation.
///
/// # Errors
///
/// Returns `AppError::token_invalid` if:
/// - The token cannot be decoded.
/// - The token type is not `"refresh"`.
///
/// # Example
///
/// ```ignore
/// let info = extract_rotation_info(old_refresh_token, secret)?;
/// blacklist.blacklist_token(&info.old_jti, Duration::from_secs(info.ttl_remaining)).await?;
/// let (new_access, _) = generate_access_token(&user_id, email, role, secret)?;
/// let (new_refresh, _) = generate_refresh_token(&user_id, email, role, secret)?;
/// ```
pub fn extract_rotation_info(token: &str, secret: &str) -> AppResult<RotationInfo> {
    let claims = verify_token(token, secret)?;

    if claims.token_type != "refresh" {
        return Err(AppError::with_detail(
            moling_core::error::ErrorCode::AuthInvalidToken,
            "Token is not a refresh token",
        ));
    }

    let now = Utc::now().timestamp() as usize;
    let ttl_remaining = if claims.exp > now {
        (claims.exp - now) as u64
    } else {
        0 // Already expired — no need to blacklist, just issue new tokens
    };

    Ok(RotationInfo {
        user_id: claims.sub,
        old_jti: claims.jti,
        ttl_remaining,
    })
}

// ---------------------------------------------------------------------------
// Logout helpers
// ---------------------------------------------------------------------------

/// Information extracted from a token for blacklisting during logout.
#[derive(Debug, Clone)]
pub struct BlacklistInfo {
    /// The JTI to blacklist.
    pub jti: String,
    /// Remaining TTL in seconds (for Redis key expiry).
    pub ttl_remaining: u64,
}

/// Extract blacklist info from any token (access or refresh).
///
/// Uses lenient decode (ignores expiry) so expired tokens can still
/// be logged out without error.
///
/// Returns `None` if the token cannot be decoded at all.
pub fn extract_blacklist_info(token: &str, secret: &str) -> Option<BlacklistInfo> {
    let claims = decode_without_expiry(token, secret).ok()?;
    let now = Utc::now().timestamp() as usize;
    let ttl_remaining = if claims.exp > now {
        (claims.exp - now) as u64
    } else {
        0
    };
    Some(BlacklistInfo {
        jti: claims.jti,
        ttl_remaining,
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::{thread, time::Duration};

    const TEST_SECRET: &str = "test-secret-key-for-unit-tests";
    const TEST_EMAIL: &str = "test@example.com";
    const TEST_ROLE: &str = "user";

    #[test]
    fn test_generate_and_verify_access_token() {
        let user_id = Uuid::new_v4();
        let (token, jti) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        assert!(!token.is_empty());
        assert!(!jti.is_empty());

        let claims = verify_token(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.sub, user_id.to_string());
        assert_eq!(claims.token_type, "access");
        assert_eq!(claims.email, TEST_EMAIL);
        assert_eq!(claims.role, TEST_ROLE);
        assert_eq!(claims.jti, jti);
    }

    #[test]
    fn test_generate_and_verify_refresh_token() {
        let user_id = Uuid::new_v4();
        let (token, jti) =
            generate_refresh_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        let claims = verify_token(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.sub, user_id.to_string());
        assert_eq!(claims.token_type, "refresh");
        assert_eq!(claims.email, TEST_EMAIL);
        assert_eq!(claims.role, TEST_ROLE);
        assert_eq!(claims.jti, jti);
    }

    #[test]
    fn test_expired_token_detected() {
        let user_id = Uuid::new_v4();
        // Create a token that expired 1 minute ago (negative TTL)
        let (token, _) = generate_access_token_with_ttl(
            &user_id,
            TEST_EMAIL,
            TEST_ROLE,
            TEST_SECRET,
            -1,
        )
        .unwrap();

        let result = verify_token(&token, TEST_SECRET);
        assert!(result.is_err(), "expired token should be rejected");
    }

    #[test]
    fn test_wrong_secret_rejected() {
        let user_id = Uuid::new_v4();
        let (token, _) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        let result = verify_token(&token, "wrong-secret");
        assert!(result.is_err());
    }

    #[test]
    fn test_decode_without_expiry_accepts_expired() {
        let user_id = Uuid::new_v4();
        let (token, _) = generate_access_token_with_ttl(
            &user_id,
            TEST_EMAIL,
            TEST_ROLE,
            TEST_SECRET,
            0,
        )
        .unwrap();
        thread::sleep(Duration::from_secs(1));

        let claims = decode_without_expiry(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.sub, user_id.to_string());
    }

    #[test]
    fn test_access_token_type_is_access() {
        let user_id = Uuid::new_v4();
        let (token, _) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();
        let claims = verify_token(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.token_type, "access");
    }

    #[test]
    fn test_refresh_token_type_is_refresh() {
        let user_id = Uuid::new_v4();
        let (token, _) =
            generate_refresh_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();
        let claims = verify_token(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.token_type, "refresh");
    }

    #[test]
    fn test_jti_is_unique_per_call() {
        let user_id = Uuid::new_v4();
        let (_, jti1) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();
        let (_, jti2) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();
        assert_ne!(jti1, jti2);
    }

    #[test]
    fn test_default_access_ttl_matches_python() {
        // Python ACCESS_TOKEN_EXPIRE_MINUTES = 15
        assert_eq!(DEFAULT_ACCESS_MINUTES, 15);
    }

    #[test]
    fn test_default_refresh_ttl_matches_python() {
        // Python REFRESH_TOKEN_EXPIRE_DAYS = 7
        assert_eq!(DEFAULT_REFRESH_DAYS, 7);
    }

    #[test]
    fn test_role_is_preserved_in_claims() {
        let user_id = Uuid::new_v4();
        let (token, _) =
            generate_access_token(&user_id, TEST_EMAIL, "admin", TEST_SECRET).unwrap();
        let claims = verify_token(&token, TEST_SECRET).unwrap();
        assert_eq!(claims.role, "admin");
    }

    // ------------------------------------------------------------------
    // Token rotation (HH11) tests
    // ------------------------------------------------------------------

    #[test]
    fn test_extract_rotation_info_success() {
        let user_id = Uuid::new_v4();
        let (refresh_token, jti) =
            generate_refresh_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        let info = extract_rotation_info(&refresh_token, TEST_SECRET).unwrap();
        assert_eq!(info.user_id, user_id.to_string());
        assert_eq!(info.old_jti, jti);
        assert!(info.ttl_remaining > 0);
    }

    #[test]
    fn test_extract_rotation_info_rejects_access_token() {
        let user_id = Uuid::new_v4();
        let (access_token, _) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        let result = extract_rotation_info(&access_token, TEST_SECRET);
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_rotation_info_expired_token() {
        let user_id = Uuid::new_v4();
        let (token, _) = generate_refresh_token_with_ttl(
            &user_id,
            TEST_EMAIL,
            TEST_ROLE,
            TEST_SECRET,
            -1,
        )
        .unwrap();

        let result = extract_rotation_info(&token, TEST_SECRET);
        assert!(result.is_err()); // Expired token rejected
    }

    // ------------------------------------------------------------------
    // Blacklist info extraction tests
    // ------------------------------------------------------------------

    #[test]
    fn test_extract_blacklist_info_success() {
        let user_id = Uuid::new_v4();
        let (token, jti) =
            generate_access_token(&user_id, TEST_EMAIL, TEST_ROLE, TEST_SECRET).unwrap();

        let info = extract_blacklist_info(&token, TEST_SECRET).unwrap();
        assert_eq!(info.jti, jti);
        assert!(info.ttl_remaining > 0);
    }

    #[test]
    fn test_extract_blacklist_info_expired_token() {
        let user_id = Uuid::new_v4();
        let (token, _) = generate_access_token_with_ttl(
            &user_id,
            TEST_EMAIL,
            TEST_ROLE,
            TEST_SECRET,
            -1,
        )
        .unwrap();

        // Even expired tokens can be decoded for blacklist purposes
        let info = extract_blacklist_info(&token, TEST_SECRET).unwrap();
        assert_eq!(info.ttl_remaining, 0);
    }

    #[test]
    fn test_extract_blacklist_info_invalid_token() {
        let result = extract_blacklist_info("not.a.valid.token", TEST_SECRET);
        assert!(result.is_none());
    }

    // ------------------------------------------------------------------
    // Backward compatibility: claims without email/role
    // ------------------------------------------------------------------

    #[test]
    fn test_deserialize_claims_without_email_role() {
        // Simulate a token payload from before email/role were added
        let old_style_json = serde_json::json!({
            "sub": "123e4567-e89b-12d3-a456-426614174000",
            "type": "access",
            "iat": 1700000000,
            "exp": 1800000000,
            "jti": "abc-def-ghi"
        });
        let claims: Claims = serde_json::from_value(old_style_json).unwrap();
        assert_eq!(claims.email, ""); // default
        assert_eq!(claims.role, "user"); // default
    }
}
