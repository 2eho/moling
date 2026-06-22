//! 墨灵 (Moling) — Application entry point.
//!
//! Startup sequence:
//! 1. Load settings from environment / `.env`
//! 2. Initialise tracing with `RUST_LOG` filter
//! 3. Create database connection pool (SeaORM + SQLite/PostgreSQL)
//! 4. Create Redis connection pool
//! 5. Initialise DeepSeekClient + KeyRotator (LLM)
//! 6. Build AppState (shared state for all handlers)
//! 7. Assemble Axum router via [`moling_api::build_router`]
//! 8. Mount middleware stack (cors, trace, request-id, rate-limit, content-length-limit, audit)
//! 9. Start background workers (TaskQueue + CronScheduler)
//!10. Bind TCP listener and serve on 0.0.0.0:8000
//!11. Graceful shutdown on SIGTERM / SIGINT

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;

use moling_api::AppState;
use moling_core::config::Settings;
use moling_core::redis::RedisClient;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::generation_dao::GenerationDao;
use moling_db::dao::ingest_dao::IngestDao;
use moling_db::dao::phase4_dao::Phase4Dao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::pool::{DatabasePool, PoolConfig};
use moling_llm::client::DeepSeekClient;
use moling_llm::key_rotator::KeyRotator;
use moling_worker::queue::TaskQueue;
use moling_worker::scheduler::CronScheduler;
use moling_worker::workers::analysis::AnalysisTask;
use moling_worker::workers::coherence::CoherenceTask;
use moling_worker::workers::generation::GenTask;
use moling_worker::workers::import_task::ImportTask;
use moling_worker::workers::notification::NotificationTask;
use moling_worker::workers::phase4::Phase4Task;
use sea_orm::DatabaseConnection;
use tracing_subscriber::EnvFilter;

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ── Step 1: Load settings ──────────────────────────────────────────
    let _ = dotenvy::dotenv();
    let settings = match Settings::new() {
        Ok(s) => {
            println!("[OK] Settings loaded");
            s
        }
        Err(e) => {
            eprintln!("[ERROR] Failed to load settings: {e}");
            return Err(e.into());
        }
    };

    // ── Step 2: Initialise tracing ─────────────────────────────────────
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(&settings.log_level));

    tracing_subscriber::fmt()
        .with_env_filter(env_filter)
        .with_target(true)
        .with_thread_ids(true)
        .json()
        .init();

    tracing::info!(version = env!("CARGO_PKG_VERSION"), "Moling server starting");

    // ── Step 3: Database connection pool ────────────────────────────────
    let pool_config = PoolConfig {
        url: settings.database_url.clone(),
        max_connections: settings.database_pool_size,
        max_overflow: settings.database_max_overflow,
        sqlx_logging: false,
        ..Default::default()
    };

    let pool = DatabasePool::new(pool_config).await?;
    tracing::info!(url = %settings.database_url, "Database pool created");

    // ── Step 4: Redis connection pool ───────────────────────────────────
    let redis_pool = moling_core::redis::RedisPool::new(
        &settings.redis_url,
        settings.redis_password.as_deref(),
    )
    .await;
    let redis_client = Arc::new(RedisClient::new(redis_pool));
    tracing::info!(url = %settings.redis_url, "Redis client ready");

    // ── Step 5: Initialise LLM client + KeyRotator ──────────────────────
    let _llm_client = Arc::new(DeepSeekClient::new());
    let _key_rotator = Arc::new(KeyRotator::new());
    tracing::info!(
        base = %settings.llm_api_base,
        model = %settings.llm_default_model,
        strategy = %settings.key_select_strategy,
        "LLM client initialised"
    );

    // ── Step 6: Build AppState ──────────────────────────────────────────
    let state = AppState::new(
        pool.conn.clone(),
        redis_client.clone(),
        Arc::new(settings.clone()),
    );

    // ── Step 7: Build router (all routes + middleware via moling_api) ───
    let router = moling_api::build_router(state.clone());

    // ── Step 8: Health check endpoint on root ───────────────────────────
    let health_router = axum::Router::new()
        .route("/", axum::routing::get(health_handler))
        .with_state(state.clone());
    let app = health_router.merge(router);

    // ── Step 9: Start background workers ────────────────────────────────
    let task_queue = Arc::new(TaskQueue::new(redis_client.clone()));

    // Cron scheduler with Redis-backed dedup (60-second tick)
    let mut scheduler = CronScheduler::with_redis(redis_client.clone())
        .with_tick_interval(60);

    // Register cron-triggered periodic tasks
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("coherence_scan", "0 */6 * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::coherence::coherence_batch_scan(&db, &redis)
                        .await
                    {
                        Ok(v) => {
                            tracing::info!(?v, "Cron coherence_scan done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron coherence_scan failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("health_notify", "*/10 * * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::health_notify::health_auto_notify(&db, &redis)
                        .await
                    {
                        Ok(v) => {
                            tracing::info!(?v, "Cron health_notify done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron health_notify failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("vault_reanalyze", "0 */6 * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::vault_reanalyze::vault_periodic_reanalyze(
                        &db, &redis,
                    )
                    .await
                    {
                        Ok(v) => {
                            tracing::info!(?v, "Cron vault_reanalyze done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron vault_reanalyze failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("card_retire", "0 2 * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::card_retire::card_retire_check(&db, &redis).await
                    {
                        Ok(v) => {
                            tracing::info!(?v, "Cron card_retire done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron card_retire failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("phase4_auto", "0 * * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::phase4::phase4_auto_advance(&db, &redis).await {
                        Ok(v) => {
                            tracing::info!(?v, "Cron phase4_auto_advance done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron phase4_auto_advance failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }
    {
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        scheduler
            .add_task("notification_flush", "*/5 * * * *", move || {
                let db = db.clone();
                let redis = redis.clone();
                async move {
                    match moling_worker::workers::notification::flush_pending(&db, &redis).await {
                        Ok(v) => {
                            tracing::debug!(?v, "Cron notification_flush done");
                            Ok(())
                        }
                        Err(e) => {
                            tracing::error!(%e, "Cron notification_flush failed");
                            Ok(())
                        }
                    }
                }
            })
            .await
            .ok();
    }

    scheduler.start();
    tracing::info!(
        cron_task_count = scheduler.task_count().await,
        "Cron scheduler started"
    );

    // Spawn worker background task (fire-and-forget, non-blocking)
    let _worker_handle = tokio::spawn({
        let queue = task_queue.clone();
        let db = pool.conn.clone();
        let redis = redis_client.clone();
        async move {
            tracing::info!("Background worker task queue started");
            loop {
                match queue.pop_priority("generation", Duration::from_secs(5)).await {
                    Ok(Some((priority, task_json))) => {
                        tracing::info!(
                            priority = ?priority,
                            task_preview = %task_json.chars().take(120).collect::<String>(),
                            "Dequeued task"
                        );
                        // Dispatch to appropriate worker based on task payload
                        if let Err(e) = dispatch_task(&db, &redis, &task_json).await {
                            tracing::warn!(error = %e, "Task dispatch failed, moving to dead letter / retry");
                            let _ = queue.dead_letter("generation", &task_json, &e.to_string()).await;
                        } else {
                            let _ = queue.acknowledge("generation", &task_json).await;
                        }
                    }
                    Ok(None) => {
                        // Idle — sleep briefly before polling again
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                    Err(e) => {
                        tracing::warn!(error = %e, "TaskQueue dequeue error");
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                }
            }
        }
    });

    tracing::info!("Workers initialised");

    // ── Step 10: Bind and serve ─────────────────────────────────────────
    let addr: SocketAddr = format!("{}:{}", settings.host, settings.port).parse()?;
    println!("[OK] Listening on http://{addr}");

    let listener = tokio::net::TcpListener::bind(addr).await?;

    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    // ── Step 11: Graceful shutdown cleanup ──────────────────────────────
    tracing::info!("Server shut down gracefully");
    Ok(())
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

/// Root-level health check handler.
///
/// Returns JSON with `status` ("healthy" | "degraded" | "unhealthy"),
/// version, database connectivity, Redis availability, and timestamp.
async fn health_handler(
    axum::extract::State(state): axum::extract::State<AppState>,
) -> axum::Json<serde_json::Value> {
    let db_ok = state.db.ping().await.is_ok();
    let redis_ok = state.redis.pool().is_available();

    let status = if db_ok && redis_ok {
        "healthy"
    } else if db_ok || redis_ok {
        "degraded"
    } else {
        "unhealthy"
    };

    axum::Json(serde_json::json!({
        "status": status,
        "version": env!("CARGO_PKG_VERSION"),
        "database": db_ok,
        "redis": redis_ok,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    }))
}

// ---------------------------------------------------------------------------
// Task dispatch — routes dequeued tasks to the right worker module
// ---------------------------------------------------------------------------

/// Parse the task JSON payload and route to the corresponding worker.
///
/// Supported task types: generation, phase4, import, analysis, notification,
/// coherence. Each worker receives the parsed task struct along with database
/// and Redis handles. Errors are propagated back to the main loop for retry /
/// dead-letter handling.
async fn dispatch_task(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task_json: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let payload: serde_json::Value = serde_json::from_str(task_json)?;
    let task_type = payload
        .get("task_type")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let task_id = payload
        .get("task_id")
        .or_else(|| payload.get("id"))
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    match task_type.as_str() {
        // ── Generation ──────────────────────────────────────────────
        "generation" => {
            let task: GenTask = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse generation task: {e}"))?;
            let gen_dao = GenerationDao;
            let chapter_dao = ChapterDao;
            moling_worker::workers::generation::execute(
                db, redis, &gen_dao, &chapter_dao, "", task,
            )
            .await?;
        }

        // ── Phase4 ──────────────────────────────────────────────────
        "phase4" => {
            let task: Phase4Task = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse phase4 task: {e}"))?;
            let phase4_dao = Phase4Dao;
            let vault_dao = VaultDao;
            let chapter_dao = ChapterDao;
            moling_worker::workers::phase4::execute(
                db, redis, &phase4_dao, &vault_dao, &chapter_dao, task,
            )
            .await?;
        }

        // ── Import ──────────────────────────────────────────────────
        "import" => {
            let task: ImportTask = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse import task: {e}"))?;
            let ingest_dao = IngestDao;
            moling_worker::workers::import_task::execute_phase(
                db, redis, &ingest_dao, task,
            )
            .await?;
        }

        // ── Analysis ────────────────────────────────────────────────
        "analysis" => {
            let task: AnalysisTask = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse analysis task: {e}"))?;
            moling_worker::workers::analysis::execute(db, redis, task).await?;
        }

        // ── Notification ────────────────────────────────────────────
        "notification" => {
            let task: NotificationTask = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse notification task: {e}"))?;
            moling_worker::workers::notification::execute_single(db, redis, task)
                .await?;
        }

        // ── Coherence ───────────────────────────────────────────────
        "coherence" => {
            let task: CoherenceTask = serde_json::from_value(payload)
                .map_err(|e| format!("Failed to parse coherence task: {e}"))?;
            moling_worker::workers::coherence::execute(db, redis, task).await?;
        }

        other => {
            tracing::warn!(task_id, task_type = other, "Unknown task type, skipping");
            return Err(format!("Unknown task type: {other}").into());
        }
    }

    tracing::info!(task_id, task_type, "Task dispatched and completed successfully");
    Ok(())
}

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------

/// Wait for SIGTERM or SIGINT, then return to trigger graceful shutdown.
async fn shutdown_signal() {
    use tokio::signal;

    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            println!("\n[INFO] SIGINT received, shutting down gracefully...");
        }
        _ = terminate => {
            println!("\n[INFO] SIGTERM received, shutting down gracefully...");
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_defaults() {
        let s = Settings::new().expect("Default settings should load");
        assert_eq!(s.host, "0.0.0.0");
        assert_eq!(s.port, 8000);
    }

    #[test]
    fn test_llm_client_creation() {
        let _client = DeepSeekClient::new();
        // Client creates successfully with default config
    }

    #[test]
    fn test_key_rotator_creation() {
        let rotator = KeyRotator::new();
        // New rotator starts empty — no keys loaded yet
        let pro_status = rotator.pool_status(moling_llm::key_rotator::Pool::Pro);
        let flash_status = rotator.pool_status(moling_llm::key_rotator::Pool::Flash);
        assert_eq!(pro_status.total, 0);
        assert_eq!(flash_status.total, 0);
    }
}
