//! Application state — shared across all handlers.
//!
//! Holds the database connection, Redis client, and loaded settings.
//! Wrapped in [`axum::extract::State`] for dependency injection into handlers.

use moling_core::config::Settings;
use moling_core::redis::RedisClient;
use sea_orm::DatabaseConnection;
use std::sync::Arc;

/// Shared application state accessible via `State<AppState>` in handlers.
///
/// All fields are [`Arc`]'d to allow cheap cloning across requests.
#[derive(Clone)]
pub struct AppState {
    /// SeaORM database connection.
    pub db: DatabaseConnection,
    /// Redis client for blacklist / lockout / rate-limiting.
    pub redis: Arc<RedisClient>,
    /// Loaded application settings (JWT secret, LLM config, etc.).
    pub settings: Arc<Settings>,
}

impl AppState {
    /// Create a new [`AppState`] from its components.
    pub fn new(db: DatabaseConnection, redis: Arc<RedisClient>, settings: Arc<Settings>) -> Self {
        Self { db, redis, settings }
    }
}
