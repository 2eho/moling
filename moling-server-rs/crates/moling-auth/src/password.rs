//! Password hashing and validation.
//!
//! Uses bcrypt (cost factor 12) matching the Python `passlib` implementation.
//! Provides complexity validation for password strength requirements.

use moling_core::error::{AppError, AppResult};

/// Bcrypt cost factor — 12 provides a good balance of security and latency.
const BCRYPT_COST: u32 = 12;

/// Minimum password length.
pub const MIN_PASSWORD_LENGTH: usize = 8;

// ---------------------------------------------------------------------------
// Hashing & verification
// ---------------------------------------------------------------------------

/// Hash a plain-text password using bcrypt with cost 12.
///
/// The resulting hash is a `$2b$`-format string suitable for storage
/// in the `password_hash` column.
pub fn hash(password: &str) -> AppResult<String> {
    bcrypt::hash(password, BCRYPT_COST).map_err(|e| {
        tracing::error!("Password: bcrypt hash failed: {e}");
        AppError::internal("Password hashing failed")
    })
}

/// Verify a plain-text password against a bcrypt hash.
///
/// Returns `Ok(true)` on match, `Ok(false)` on mismatch or if bcrypt
/// encounters an internal error (treated as verification failure, not 500).
pub fn verify(password: &str, hash: &str) -> bool {
    bcrypt::verify(password, hash).unwrap_or(false)
}

// ---------------------------------------------------------------------------
// Complexity validation
// ---------------------------------------------------------------------------

/// Validate password complexity requirements.
///
/// Requirements:
/// - Minimum 8 characters
/// - At least one uppercase letter (A-Z)
/// - At least one lowercase letter (a-z)
/// - At least one digit (0-9)
/// - At least one special character (anything not alphanumeric)
pub fn validate_complexity(password: &str) -> AppResult<()> {
    if password.len() < MIN_PASSWORD_LENGTH {
        return Err(AppError::validation_error(format!(
            "密码长度至少需要 {MIN_PASSWORD_LENGTH} 位"
        )));
    }

    let mut has_upper = false;
    let mut has_lower = false;
    let mut has_digit = false;
    let mut has_special = false;

    for ch in password.chars() {
        if ch.is_ascii_uppercase() {
            has_upper = true;
        } else if ch.is_ascii_lowercase() {
            has_lower = true;
        } else if ch.is_ascii_digit() {
            has_digit = true;
        } else {
            has_special = true;
        }
    }

    let mut missing = Vec::new();
    if !has_upper {
        missing.push("大写字母");
    }
    if !has_lower {
        missing.push("小写字母");
    }
    if !has_digit {
        missing.push("数字");
    }
    if !has_special {
        missing.push("特殊字符");
    }

    if !missing.is_empty() {
        return Err(AppError::validation_error(format!(
            "密码需包含：{}",
            missing.join("、")
        )));
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash_and_verify() {
        let hashed = hash("MyStr0ng!Pass").unwrap();
        assert!(hashed.starts_with("$2"));

        let ok = verify("MyStr0ng!Pass", &hashed);
        assert!(ok);

        let bad = verify("wrong", &hashed);
        assert!(!bad);
    }

    #[test]
    fn test_hash_is_deterministically_different() {
        // Each bcrypt hash has a unique salt
        let h1 = hash("same_password").unwrap();
        let h2 = hash("same_password").unwrap();
        assert_ne!(h1, h2);

        // Both should verify
        assert!(verify("same_password", &h1));
        assert!(verify("same_password", &h2));
    }

    #[test]
    fn test_empty_password_accepted_by_bcrypt() {
        // bcrypt 0.16 hashes empty strings — complexity validation catches this upstream
        let result = hash("");
        assert!(result.is_ok(), "bcrypt technically hashes empty strings");
        assert!(validate_complexity("").is_err());
    }

    #[test]
    fn test_validate_complexity_pass() {
        assert!(validate_complexity("Abcdef1!").is_ok());
        assert!(validate_complexity("P@ssw0rd").is_ok());
        assert!(validate_complexity("C0mpl3x!Pass").is_ok());
    }

    #[test]
    fn test_validate_complexity_too_short() {
        let err = validate_complexity("Ab1!").unwrap_err();
        assert!(err.message.contains("8"));
    }

    #[test]
    fn test_validate_complexity_missing_upper() {
        let err = validate_complexity("abcdef1!").unwrap_err();
        assert!(err.message.contains("大写字母"));
    }

    #[test]
    fn test_validate_complexity_missing_lower() {
        let err = validate_complexity("ABCDEF1!").unwrap_err();
        assert!(err.message.contains("小写字母"));
    }

    #[test]
    fn test_validate_complexity_missing_digit() {
        let err = validate_complexity("Abcdef!@").unwrap_err();
        assert!(err.message.contains("数字"));
    }

    #[test]
    fn test_validate_complexity_missing_special() {
        let err = validate_complexity("Abcdef12").unwrap_err();
        assert!(err.message.contains("特殊字符"));
    }

    #[test]
    fn test_validate_complexity_chinese_special_chars() {
        // Chinese punctuation counts as special
        assert!(validate_complexity("Abcdef1。").is_ok());
    }
}
