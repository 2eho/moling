//! 墨灵 (Moling) — Authentication crate.
//!
//! Provides JWT token generation/verification, password hashing/validation,
//! token blacklisting, login lockout, Axum auth middleware, and the
//! `CurrentUser` request extractor.
//!
//! # Modules
//!
//! - [`jwt`] — HS256 JWT access/refresh token lifecycle with token rotation (HH11).
//! - [`password`] — bcrypt hashing and complexity validation.
//! - [`blacklist`] — Redis-backed token revocation (logout).
//! - [`lockout`] — Redis-backed brute-force login protection.
//! - [`middleware`] — Axum middleware (`require_auth` / `optional_auth` / `require_admin`).
//! - [`extractor`] — `CurrentUser` / `OptionalCurrentUser` / `AdminUser` request extractors.
//!
//! # Quick start
//!
//! ```ignore
//! use moling_auth::{
//!     jwt::{generate_access_token, generate_refresh_token, verify_token, extract_rotation_info},
//!     password,
//!     blacklist::TokenBlacklist,
//!     lockout::LoginLockout,
//!     middleware::{require_auth, optional_auth, require_admin, AuthConfig},
//!     extractor::{CurrentUser, OptionalCurrentUser, AdminUser},
//! };
//! ```

pub mod blacklist;
pub mod extractor;
pub mod jwt;
pub mod lockout;
pub mod middleware;
pub mod password;

// Re-export key types for convenient top-level access
pub use blacklist::TokenBlacklist;
pub use extractor::{AdminUser, CurrentUser, OptionalCurrentUser};
pub use jwt::{
    decode_without_expiry, extract_blacklist_info, extract_rotation_info,
    generate_access_token, generate_access_token_with_ttl, generate_refresh_token,
    generate_refresh_token_with_ttl, verify_token, BlacklistInfo, Claims, RotationInfo,
};
pub use lockout::LoginLockout;
pub use middleware::{optional_auth, require_admin, require_auth, AuthConfig};
pub use password::{hash, validate_complexity, verify};
