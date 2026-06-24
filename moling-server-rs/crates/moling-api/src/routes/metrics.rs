//! Prometheus-compatible metrics endpoint.
//!
//! Exposes HTTP request counters, latency summaries, and system-level health
//! gauges in the standard Prometheus exposition format (plain text).
//!
//! No external metrics crate — we build the format manually to keep the
//! dependency footprint small.

use axum::{extract::State, http::StatusCode, response::IntoResponse, routing::get, Router};

use crate::middleware::metrics;
use crate::state::AppState;

pub fn router() -> Router<AppState> {
    Router::new().route("/", get(metrics_handler))
}

/// GET /api/v1/metrics — Prometheus text-format metrics.
async fn metrics_handler(State(state): State<AppState>) -> impl IntoResponse {
    let body = build_metrics_text(&state).await;
    (
        StatusCode::OK,
        [("content-type", "text/plain; version=0.0.4")],
        body,
    )
}

/// Build the Prometheus exposition-format text.
async fn build_metrics_text(state: &AppState) -> String {
    let mut buf = String::with_capacity(2048);

    // ------------------------------------------------------------------
    // HELP/TYPE metadata
    // ------------------------------------------------------------------
    buf.push_str("# HELP moling_http_requests_total Total number of HTTP requests.\n");
    buf.push_str("# TYPE moling_http_requests_total counter\n");

    buf.push_str("# HELP moling_http_responses_total HTTP responses by status class.\n");
    buf.push_str("# TYPE moling_http_responses_total counter\n");

    buf.push_str(
        "# HELP moling_http_request_duration_microseconds Cumulative request duration.\n",
    );
    buf.push_str("# TYPE moling_http_request_duration_microseconds counter\n");

    buf.push_str("# HELP moling_http_requests_in_flight Currently active HTTP requests.\n");
    buf.push_str("# TYPE moling_http_requests_in_flight gauge\n");

    buf.push_str("# HELP moling_uptime_seconds Server uptime in seconds.\n");
    buf.push_str("# TYPE moling_uptime_seconds gauge\n");

    buf.push_str("# HELP moling_info Server version information.\n");
    buf.push_str("# TYPE moling_info gauge\n");

    buf.push_str("# HELP moling_db_health Database health (1=healthy, 0=unhealthy).\n");
    buf.push_str("# TYPE moling_db_health gauge\n");

    buf.push_str("# HELP moling_redis_health Redis health (1=healthy, 0=unhealthy).\n");
    buf.push_str("# TYPE moling_redis_health gauge\n");

    buf.push_str("# HELP moling_rate_limit_allowed_total Rate-limit checks that passed.\n");
    buf.push_str("# TYPE moling_rate_limit_allowed_total counter\n");

    buf.push_str("# HELP moling_rate_limit_blocked_total Rate-limit checks that were blocked.\n");
    buf.push_str("# TYPE moling_rate_limit_blocked_total counter\n");

    // ------------------------------------------------------------------
    // Counters — HTTP requests
    // ------------------------------------------------------------------
    let total = metrics::REQUESTS_TOTAL.load(std::sync::atomic::Ordering::Relaxed);
    buf.push_str(&format!("moling_http_requests_total {total}\n"));

    // Responses by status class
    let s2xx = metrics::RESPONSES_2XX.load(std::sync::atomic::Ordering::Relaxed);
    let s3xx = metrics::RESPONSES_3XX.load(std::sync::atomic::Ordering::Relaxed);
    let s4xx = metrics::RESPONSES_4XX.load(std::sync::atomic::Ordering::Relaxed);
    let s5xx = metrics::RESPONSES_5XX.load(std::sync::atomic::Ordering::Relaxed);

    buf.push_str(&format!(
        "moling_http_responses_total{{status_class=\"2xx\"}} {s2xx}\n"
    ));
    buf.push_str(&format!(
        "moling_http_responses_total{{status_class=\"3xx\"}} {s3xx}\n"
    ));
    buf.push_str(&format!(
        "moling_http_responses_total{{status_class=\"4xx\"}} {s4xx}\n"
    ));
    buf.push_str(&format!(
        "moling_http_responses_total{{status_class=\"5xx\"}} {s5xx}\n"
    ));

    // Duration
    let dur_sum = metrics::REQUEST_DURATION_MICROS_SUM.load(std::sync::atomic::Ordering::Relaxed);
    let dur_count = metrics::REQUEST_DURATION_COUNT.load(std::sync::atomic::Ordering::Relaxed);
    buf.push_str(&format!(
        "moling_http_request_duration_microseconds{{quantile=\"sum\"}} {dur_sum}\n"
    ));
    buf.push_str(&format!(
        "moling_http_request_duration_microseconds{{quantile=\"count\"}} {dur_count}\n"
    ));

    // In-flight
    let inflight = metrics::REQUESTS_IN_FLIGHT.load(std::sync::atomic::Ordering::Relaxed);
    buf.push_str(&format!("moling_http_requests_in_flight {inflight}\n"));

    // ------------------------------------------------------------------
    // Gauges — uptime
    // ------------------------------------------------------------------
    let uptime = metrics::uptime_seconds();
    buf.push_str(&format!("moling_uptime_seconds {uptime:.3}\n"));

    // ------------------------------------------------------------------
    // Info — version (as a gauge with label)
    // ------------------------------------------------------------------
    let version = env!("CARGO_PKG_VERSION");
    buf.push_str(&format!(
        "moling_info{{version=\"{version}\"}} 1\n"
    ));

    // ------------------------------------------------------------------
    // Health gauges
    // ------------------------------------------------------------------
    let start = std::time::Instant::now();
    let db_ok = state.db.ping().await.is_ok();
    let db_latency_ms = start.elapsed().as_millis() as u64;

    let redis_start = std::time::Instant::now();
    let redis_ok = match state.redis.ping().await {
        Ok(Some(ref pong)) => pong == "PONG",
        _ => false,
    };
    let redis_latency_ms = redis_start.elapsed().as_millis() as u64;

    buf.push_str(&format!(
        "moling_db_health{{latency_ms=\"{db_latency_ms}\"}} {}\n",
        if db_ok { 1 } else { 0 }
    ));
    buf.push_str(&format!(
        "moling_redis_health{{latency_ms=\"{redis_latency_ms}\"}} {}\n",
        if redis_ok { 1 } else { 0 }
    ));

    // ------------------------------------------------------------------
    // Rate-limit counters
    // ------------------------------------------------------------------
    let rate_limit_allowed =
        metrics::RATE_LIMIT_ALLOWED_TOTAL.load(std::sync::atomic::Ordering::Relaxed);
    let rate_limit_blocked =
        metrics::RATE_LIMIT_BLOCKED_TOTAL.load(std::sync::atomic::Ordering::Relaxed);
    buf.push_str(&format!("moling_rate_limit_allowed_total {rate_limit_allowed}\n"));
    buf.push_str(&format!("moling_rate_limit_blocked_total {rate_limit_blocked}\n"));

    buf
}
