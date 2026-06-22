//! Database connection pool — Postgres + SQLite support.
//!
//! Uses SeaORM's `DatabaseConnection` with configurable pool size and
//! overflow.  Provides a health-check utility.

use moling_core::error::AppError;
use sea_orm::{ConnectOptions, Database, DatabaseConnection};
use std::time::Duration;

/// Database pool configuration.
#[derive(Debug, Clone)]
pub struct PoolConfig {
    /// Database URL (e.g. `postgres://user:pass@localhost/moling` or
    /// `sqlite:./moling.db`).
    pub url: String,
    /// Maximum number of connections in the pool.
    pub max_connections: u32,
    /// Maximum number of connections beyond `max_connections` that can be
    /// created temporarily.
    pub max_overflow: u32,
    /// Maximum time (seconds) to wait for a connection from the pool.
    pub acquire_timeout_secs: u64,
    /// Maximum idle time (seconds) before a connection is closed.
    pub idle_timeout_secs: u64,
    /// SQL statement logging (set to true only for debugging).
    pub sqlx_logging: bool,
}

impl Default for PoolConfig {
    fn default() -> Self {
        Self {
            url: "sqlite:./moling.db".into(),
            max_connections: 20,
            max_overflow: 10,
            acquire_timeout_secs: 30,
            idle_timeout_secs: 300,
            sqlx_logging: false,
        }
    }
}

/// Wrapper around SeaORM's `DatabaseConnection` with health-check support.
#[derive(Clone)]
pub struct DatabasePool {
    pub conn: DatabaseConnection,
    config: PoolConfig,
}

impl DatabasePool {
    /// Create a new connection pool from the given configuration.
    ///
    /// # Errors
    ///
    /// Returns `AppError` if the database is unreachable or the URL is
    /// malformed.
    pub async fn new(config: PoolConfig) -> Result<Self, AppError> {
        let mut opts = ConnectOptions::new(config.url.clone());
        opts.max_connections(config.max_connections)
            .min_connections(2)
            .connect_timeout(Duration::from_secs(config.acquire_timeout_secs))
            .idle_timeout(Duration::from_secs(config.idle_timeout_secs))
            .sqlx_logging(config.sqlx_logging);

        let conn = Database::connect(opts).await.map_err(|e| {
            tracing::error!(url = %config.url, "Failed to connect to database: {e}");
            AppError::internal(format!("Database connection failed: {e}"))
        })?;

        tracing::info!(
            url = %config.url,
            max = config.max_connections,
            "Database pool created"
        );

        Ok(Self { conn, config })
    }

    /// Health-check: execute `SELECT 1` and return `true` if the database
    /// is reachable.
    pub async fn health_check(&self) -> bool {
        use sea_orm::{ConnectionTrait, Statement};

        let stmt = Statement::from_string(
            self.conn.get_database_backend(),
            "SELECT 1".to_owned(),
        );
        self.conn
            .execute(stmt)
            .await
            .map(|_| true)
            .unwrap_or(false)
    }

    /// Return a reference to the pool configuration.
    pub fn config(&self) -> &PoolConfig {
        &self.config
    }
}
