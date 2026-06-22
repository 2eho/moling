//! Health check route — system-level liveness/readiness probe.
//!
//! Matches the Python backend's `/api/v1/health` response shape:
//! ```json
//! {
//!   "status": "ok" | "degraded",
//!   "version": "0.1.0",
//!   "timestamp": 1710000000,
//!   "uptime_seconds": 12345.6,
//!   "checks": { "database": "connected", "redis": "connected", "worker": "connected" },
//!   "database": "connected",
//!   "code": 0,
//!   "message": "All systems operational"
//! }
//! ```

use axum::{extract::State, routing::get, Json, Router};
use moling_core::error::AppResult;
use serde_json::{json, Value};
use std::time::Instant;

use crate::middleware::metrics;
use crate::state::AppState;

pub fn router() -> Router<AppState> {
    Router::new().route("/", get(health_check))
}

/// GET /api/v1/health — system health check with latency probes.
async fn health_check(State(state): State<AppState>) -> AppResult<Json<Value>> {
    let now_ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let mut checks = serde_json::Map::new();
    let mut overall_healthy = true;

    // ── 1. Database ──────────────────────────────────────────────────
    let db_start = Instant::now();
    let db_ok = state.db.ping().await.is_ok();
    let db_latency_ms = db_start.elapsed().as_millis() as u64;

    checks.insert(
        "database".into(),
        json!({
            "status": if db_ok { "connected" } else { "disconnected" },
            "latency_ms": db_latency_ms,
        }),
    );
    if !db_ok {
        overall_healthy = false;
    }

    // ── 2. Redis ─────────────────────────────────────────────────────
    let redis_start = Instant::now();
    let redis_result = tokio::time::timeout(
        std::time::Duration::from_secs(2),
        state.redis.ping(),
    )
    .await
    .unwrap_or(Ok(None));
    let redis_latency_ms = redis_start.elapsed().as_millis() as u64;

    let redis_ok = matches!(&redis_result, Ok(Some(pong)) if pong == "PONG");
    checks.insert(
        "redis".into(),
        json!({
            "status": if redis_ok { "connected" } else { "disconnected" },
            "latency_ms": redis_latency_ms,
        }),
    );
    if !redis_ok {
        overall_healthy = false;
    }

    // ── 3. Worker queue ──────────────────────────────────────────────
    // Placeholder — the Rust worker crate is not yet implemented.
    // When moling-worker is built, this will check Celery/worker health.
    let worker_status = "no_workers"; // honest: workers are not yet ported
    checks.insert(
        "worker".into(),
        json!({
            "status": worker_status,
            "latency_ms": null,
        }),
    );
    // Worker is not critical for overall health at this stage.

    // ── 4. Aggregate ─────────────────────────────────────────────────
    let status = if overall_healthy { "ok" } else { "degraded" };
    let db_status = checks["database"]["status"].as_str().unwrap_or("disconnected");
    let db_code: u8 = if db_status == "connected" { 0 } else { 1 };

    let failed: Vec<&str> = checks
        .iter()
        .filter_map(|(k, v)| {
            if v["status"].as_str() != Some("connected") {
                Some(k.as_str())
            } else {
                None
            }
        })
        .collect();

    let message = if overall_healthy {
        "All systems operational".to_string()
    } else {
        format!("Degraded: {}", failed.join(", "))
    };

    let uptime = metrics::uptime_seconds();
    let start_time = metrics::start_time_secs();

    Ok(Json(json!({
        "status": status,
        "version": env!("CARGO_PKG_VERSION"),
        "timestamp": now_ts,
        "uptime_seconds": uptime,
        "start_time_unix": start_time,
        "checks": checks,
        "database": db_status,
        "code": db_code,
        "message": message,
        "data": {
            "status": status,
            "uptime_seconds": uptime,
        },
    })))
}
