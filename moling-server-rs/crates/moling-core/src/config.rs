//! 墨灵 (Moling) — Configuration system.
//!
//! Uses [`figment`] to load settings from environment variables (prefixed
//! `MOLING_`), `.env` files (via `dotenvy`), and fallback defaults.
//! Mirrors Python `app/config.py` `Settings` class.

use figment::providers::Env;
use figment::Figment;
use serde::Deserialize;
use std::sync::LazyLock;
use std::sync::RwLock;

// ---------------------------------------------------------------------------
// Settings — all 33+ configuration fields
// ---------------------------------------------------------------------------

/// Application settings — populated from environment / `.env` file.
///
/// Ported from Python `app/config.py` with Rust-native defaults.
#[derive(Debug, Clone, Deserialize)]
pub struct Settings {
    // ---- Database ----
    #[serde(default = "default_database_url")]
    pub database_url: String,
    #[serde(default = "default_database_pool_size")]
    pub database_pool_size: u32,
    #[serde(default = "default_database_max_overflow")]
    pub database_max_overflow: u32,

    // ---- Redis ----
    #[serde(default = "default_redis_url")]
    pub redis_url: String,
    #[serde(default)]
    pub redis_password: Option<String>,

    // ---- Auth / JWT ----
    #[serde(default = "default_secret_key")]
    pub secret_key: String,
    #[serde(default = "default_algorithm")]
    pub algorithm: String,
    #[serde(default = "default_access_token_expire_minutes")]
    pub access_token_expire_minutes: i64,
    #[serde(default = "default_refresh_token_expire_days")]
    pub refresh_token_expire_days: i64,

    // ---- LLM Service ----
    #[serde(default = "default_llm_api_base")]
    pub llm_api_base: String,
    #[serde(default = "default_llm_api_key")]
    pub llm_api_key: String,
    #[serde(default)]
    pub llm_pro_keys: Option<String>,
    #[serde(default)]
    pub llm_flash_keys: Option<String>,
    #[serde(default = "default_llm_model")]
    pub llm_default_model: String,
    #[serde(default = "default_llm_model")]
    pub llm_large_model: String,
    #[serde(default = "default_llm_model")]
    pub llm_medium_model: String,
    #[serde(default = "default_llm_model")]
    pub llm_small_model: String,
    #[serde(default = "default_key_select_strategy")]
    pub key_select_strategy: String,

    // ---- Budget ----
    #[serde(default = "default_token_budget_limit")]
    pub token_budget_limit: i64,

    // ---- Celery / Worker Bridge ----
    #[serde(default = "default_celery_broker_url")]
    pub celery_broker_url: String,
    #[serde(default = "default_celery_result_backend")]
    pub celery_result_backend: String,

    // ---- CORS ----
    #[serde(default = "default_cors_origins")]
    pub cors_origins: String,

    // ---- Rate Limiting ----
    #[serde(default = "default_rate_limit_calls")]
    pub rate_limit_calls: u32,
    #[serde(default = "default_rate_limit_period")]
    pub rate_limit_period: u32,

    // ---- Monitoring ----
    #[serde(default)]
    pub sentry_dsn: Option<String>,
    #[serde(default = "default_log_level")]
    pub log_level: String,
    #[serde(default = "default_audit_log_dir")]
    pub audit_log_dir: String,

    // ---- Server ----
    #[serde(default = "default_host")]
    pub host: String,
    #[serde(default = "default_port")]
    pub port: u16,
    #[serde(default = "default_base_path")]
    pub base_path: String,

    // ---- Content Length ----
    #[serde(default = "default_max_body_size")]
    pub max_body_size: u64,

    // ---- Phase 4 ----
    #[serde(default = "default_phase4_auto_mode")]
    pub phase4_auto_mode: bool,
    #[serde(default = "default_phase4_review_timeout_hours")]
    pub phase4_review_timeout_hours: i64,

    // ---- Email (placeholder for future) ----
    #[serde(default)]
    pub smtp_host: Option<String>,
    #[serde(default)]
    pub smtp_port: Option<u16>,
}

// ---------------------------------------------------------------------------
// Default value helpers
// ---------------------------------------------------------------------------

fn default_database_url() -> String {
    "sqlite:./moling.db".into()
}
fn default_database_pool_size() -> u32 {
    20
}
fn default_database_max_overflow() -> u32 {
    10
}
fn default_redis_url() -> String {
    "redis://localhost:6379/0".into()
}
fn default_secret_key() -> String {
    "dev-secret-key-change-in-production".into()
}
fn default_algorithm() -> String {
    "HS256".into()
}
fn default_access_token_expire_minutes() -> i64 {
    60
}
fn default_refresh_token_expire_days() -> i64 {
    7
}
fn default_llm_api_base() -> String {
    "https://api.deepseek.com".into()
}
fn default_llm_api_key() -> String {
    "sk-placeholder".into()
}
fn default_llm_model() -> String {
    "deepseek-chat".into()
}
fn default_key_select_strategy() -> String {
    "least_usage".into()
}
fn default_token_budget_limit() -> i64 {
    1_000_000
}
fn default_celery_broker_url() -> String {
    "redis://localhost:6379/1".into()
}
fn default_celery_result_backend() -> String {
    "redis://localhost:6379/2".into()
}
fn default_cors_origins() -> String {
    "*".into()
}
fn default_rate_limit_calls() -> u32 {
    100
}
fn default_rate_limit_period() -> u32 {
    60
}
fn default_log_level() -> String {
    "INFO".into()
}
fn default_audit_log_dir() -> String {
    "./logs".into()
}
fn default_host() -> String {
    "0.0.0.0".into()
}
fn default_port() -> u16 {
    8000
}
fn default_base_path() -> String {
    "/api/v1".into()
}
fn default_max_body_size() -> u64 {
    10_485_760 // 10 MB
}
fn default_phase4_auto_mode() -> bool {
    true
}
fn default_phase4_review_timeout_hours() -> i64 {
    72
}

// ---------------------------------------------------------------------------
// Settings impl
// ---------------------------------------------------------------------------

impl Settings {
    /// Load settings from `.env` + environment variables with defaults.
    ///
    /// Sources (lowest to highest priority):
    /// 1. Struct-level `#[serde(default)]` fallbacks
    /// 2. `.env` file (loaded via `dotenvy`)
    /// 3. `MOLING_`-prefixed environment variables
    pub fn new() -> Result<Self, figment::Error> {
        // Load .env file if present (non-fatal if missing)
        let _ = dotenvy::dotenv();

        Figment::new()
            .merge(Env::prefixed("MOLING_"))
            .merge(Env::raw())
            .extract()
    }

    /// Parse pro/flash keys from comma-separated strings into `Vec<String>`.
    pub fn pro_keys_list(&self) -> Vec<String> {
        parse_keys(&self.llm_pro_keys)
    }

    pub fn flash_keys_list(&self) -> Vec<String> {
        parse_keys(&self.llm_flash_keys)
    }

    /// Build an [`LlmConfig`] from the current settings.
    pub fn get_effective_llm_config(&self) -> LlmConfig {
        LlmConfig {
            api_base: self.llm_api_base.clone(),
            api_key: self.llm_api_key.clone(),
            default_model: self.llm_default_model.clone(),
        }
    }
}

// ---------------------------------------------------------------------------
// Runtime overrides (matching Python `set_override` / `get_effective_llm_config`)
// ---------------------------------------------------------------------------

static OVERRIDES: LazyLock<RwLock<std::collections::HashMap<String, String>>> =
    LazyLock::new(|| RwLock::new(std::collections::HashMap::new()));

/// Set a runtime override (async-safe via `RwLock`).
///
/// Corresponds to Python `set_override()` — values set here take precedence
/// over the static [`Settings`] object.
pub fn set_override(key: impl Into<String>, value: impl Into<String>) {
    if let Ok(mut map) = OVERRIDES.write() {
        map.insert(key.into(), value.into());
    }
}

/// Remove a runtime override.
pub fn clear_override(key: &str) {
    if let Ok(mut map) = OVERRIDES.write() {
        map.remove(key);
    }
}

/// Resolve a key: override > environment > static settings.
fn resolve_override(_settings: &Settings, key: &str, fallback: &str) -> String {
    if let Ok(map) = OVERRIDES.read() {
        if let Some(v) = map.get(key) {
            return v.clone();
        }
    }
    fallback.to_owned()
}

/// Get the effective LLM configuration (override-aware).
pub fn get_effective_llm_config(settings: &Settings) -> LlmConfig {
    LlmConfig {
        api_base: resolve_override(settings, "llm_api_base", &settings.llm_api_base),
        api_key: resolve_override(settings, "llm_api_key", &settings.llm_api_key),
        default_model: resolve_override(
            settings,
            "llm_default_model",
            &settings.llm_default_model,
        ),
    }
}

// ---------------------------------------------------------------------------
// LlmConfig
// ---------------------------------------------------------------------------

/// Effective LLM configuration — resolved from settings + runtime overrides.
#[derive(Debug, Clone)]
pub struct LlmConfig {
    pub api_base: String,
    pub api_key: String,
    pub default_model: String,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Parse a comma-separated string into a list of trimmed, non-empty items.
fn parse_keys(raw: &Option<String>) -> Vec<String> {
    match raw {
        Some(s) if !s.trim().is_empty() => s
            .split(',')
            .map(str::trim)
            .filter(|k| !k.is_empty())
            .map(str::to_owned)
            .collect(),
        _ => Vec::new(),
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_keys_empty() {
        assert!(parse_keys(&None).is_empty());
        assert!(parse_keys(&Some("".into())).is_empty());
        assert!(parse_keys(&Some("  ".into())).is_empty());
    }

    #[test]
    fn parse_keys_csv() {
        let keys = parse_keys(&Some("sk-a, sk-b, sk-c".into()));
        assert_eq!(keys, vec!["sk-a", "sk-b", "sk-c"]);
    }

    #[test]
    fn defaults_are_populated() {
        let s = Settings::new().expect("default settings should load");
        assert_eq!(s.host, "0.0.0.0");
        assert_eq!(s.port, 8000);
    }

    #[test]
    fn llm_config_from_settings() {
        let s = Settings::new().unwrap();
        let cfg = s.get_effective_llm_config();
        assert_eq!(cfg.api_base, s.llm_api_base);
    }

    #[test]
    fn override_resolution() {
        let s = Settings::new().unwrap();
        set_override("llm_api_base", "https://custom.api/v1");
        let cfg = get_effective_llm_config(&s);
        assert_eq!(cfg.api_base, "https://custom.api/v1");
        clear_override("llm_api_base");

        let cfg2 = get_effective_llm_config(&s);
        assert_eq!(cfg2.api_base, s.llm_api_base);
    }
}
