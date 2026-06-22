//! Cron scheduler — periodic task execution with cron expressions and dedup.
//!
//! Manages recurring tasks like vault reanalysis, card retirement,
//! and health monitoring. Uses in-memory scheduling with background tokio tasks.
//!
//! # Task Deduplication
//!
//! Uses Redis SET NX to ensure a scheduled task is not dispatched multiple
//! times within the same period. Each task gets a unique run key based on
//! the task name and current time window.

use chrono::{DateTime, Datelike, Timelike, Utc};
use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use std::fmt;
use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tokio::task::JoinHandle;

// ---------------------------------------------------------------------------
// CronExpr
// ---------------------------------------------------------------------------

/// Simple cron expression parser supporting: minute hour dom month dow
///
/// Supports step values with `/` (e.g. `*/10` = every 10 minutes),
/// comma-separated lists, and wildcards.
#[derive(Debug, Clone)]
pub struct CronExpr {
    pub minute: CronField,
    pub hour: CronField,
    pub dom: CronField,
    pub month: CronField,
    pub dow: CronField,
}

/// A cron field supporting wildcard `*`, step `*/N`, or comma-separated values.
#[derive(Debug, Clone)]
pub enum CronField {
    Wildcard,
    Step(u32),
    Values(Vec<u32>),
}

impl CronExpr {
    /// Parse a 5-field cron expression (e.g. "0 */6 * * *" or "*/10 * * * *").
    pub fn parse(expr: &str) -> Result<Self, String> {
        let parts: Vec<&str> = expr.split_whitespace().collect();
        if parts.len() != 5 {
            return Err(format!(
                "Invalid cron expression: expected 5 fields, got {}",
                parts.len()
            ));
        }
        Ok(Self {
            minute: parse_cron_field(parts[0], 0, 59)?,
            hour: parse_cron_field(parts[1], 0, 23)?,
            dom: parse_cron_field(parts[2], 1, 31)?,
            month: parse_cron_field(parts[3], 1, 12)?,
            dow: parse_cron_field(parts[4], 0, 6)?,
        })
    }

    /// Check whether this cron expression matches the given datetime.
    pub fn matches(&self, dt: &DateTime<Utc>) -> bool {
        matches_field(&self.minute, dt.minute())
            && matches_field(&self.hour, dt.hour())
            && matches_field(&self.dom, dt.day())
            && matches_field(&self.month, dt.month())
            && matches_field(&self.dow, dt.weekday().num_days_from_sunday())
    }

    /// Human-readable description of this cron schedule.
    pub fn describe(&self) -> String {
        let min = describe_field(&self.minute, "min");
        let hr = describe_field(&self.hour, "h");
        let dom = describe_field(&self.dom, "day");
        format!("At {min} of {hr} on {dom}")
    }
}

fn parse_cron_field(s: &str, min: u32, max: u32) -> Result<CronField, String> {
    if s == "*" {
        return Ok(CronField::Wildcard);
    }
    if let Some(step_str) = s.strip_prefix("*/") {
        let step: u32 = step_str
            .parse()
            .map_err(|e| format!("Invalid step value '{step_str}': {e}"))?;
        if step == 0 || step > max {
            return Err(format!("Step value {step} out of range [{min},{max}]"));
        }
        return Ok(CronField::Step(step));
    }
    let values: Result<Vec<u32>, _> = s
        .split(',')
        .map(|v| {
            v.parse::<u32>().map_err(|e| {
                format!("Invalid cron field value '{v}': {e}")
            })
        })
        .collect();
    let vals = values?;
    for &v in &vals {
        if v < min || v > max {
            return Err(format!("Value {v} out of range [{min},{max}]"));
        }
    }
    Ok(CronField::Values(vals))
}

fn matches_field(field: &CronField, value: u32) -> bool {
    match field {
        CronField::Wildcard => true,
        CronField::Step(step) => value % step == 0,
        CronField::Values(vals) => vals.contains(&value),
    }
}

fn describe_field(field: &CronField, unit: &str) -> String {
    match field {
        CronField::Wildcard => format!("every {unit}"),
        CronField::Step(n) => format!("every {n}{unit}"),
        CronField::Values(vals) => {
            let list: Vec<String> = vals.iter().map(|v| format!("{v}{unit}")).collect();
            list.join(",")
        }
    }
}

// ---------------------------------------------------------------------------
// ScheduledTask
// ---------------------------------------------------------------------------

/// A scheduled task handler — async function with Redis-based dedup.
type AsyncTaskFn = Arc<
    dyn Fn() -> Pin<Box<dyn Future<Output = AppResult<()>> + Send>>
        + Send
        + Sync,
>;

struct ScheduledTask {
    name: String,
    cron: CronExpr,
    handler: AsyncTaskFn,
    /// Redis client for dedup (optional).
    redis: Option<Arc<RedisClient>>,
    /// Deduplication window in seconds (defaults to 60).
    dedup_window_secs: u64,
}

// ---------------------------------------------------------------------------
// CronScheduler
// ---------------------------------------------------------------------------

/// In-memory cron scheduler with Redis-based task deduplication.
///
/// Checks scheduled tasks every 30 seconds and spawns handlers on match.
/// Each task is wrapped with a dedup check: a Redis key `cron:run:{name}:{window}`
/// is SET NX before execution to prevent double-dispatch.
pub struct CronScheduler {
    tasks: Arc<RwLock<Vec<ScheduledTask>>>,
    _handle: Option<JoinHandle<()>>,
    redis: Option<Arc<RedisClient>>,
    tick_interval_secs: u64,
}

impl CronScheduler {
    /// Create a new scheduler without Redis (no dedup).
    pub fn new() -> Self {
        Self {
            tasks: Arc::new(RwLock::new(Vec::new())),
            _handle: None,
            redis: None,
            tick_interval_secs: 30,
        }
    }

    /// Create a scheduler with Redis-backed dedup.
    pub fn with_redis(redis: Arc<RedisClient>) -> Self {
        Self {
            tasks: Arc::new(RwLock::new(Vec::new())),
            _handle: None,
            redis: Some(redis),
            tick_interval_secs: 30,
        }
    }

    /// Set the tick interval (how often to check for due tasks).
    pub fn with_tick_interval(mut self, secs: u64) -> Self {
        self.tick_interval_secs = secs;
        self
    }

    /// Add a recurring task with a cron expression.
    ///
    /// The handler should be an async function. Dedup is enabled if Redis
    /// is configured on the scheduler.
    pub async fn add_task<F, Fut>(
        &self,
        name: &str,
        cron_expr: &str,
        handler: F,
    ) -> Result<(), String>
    where
        F: Fn() -> Fut + Send + Sync + 'static,
        Fut: Future<Output = AppResult<()>> + Send + 'static,
    {
        let cron = CronExpr::parse(cron_expr)?;
        let wrapped: AsyncTaskFn = Arc::new(move || Box::pin(handler()));
        let mut tasks = self.tasks.write().await;
        tasks.push(ScheduledTask {
            name: name.to_owned(),
            cron,
            handler: wrapped,
            redis: self.redis.clone(),
            dedup_window_secs: 60,
        });
        tracing::info!(name, cron_expr, "Scheduled task registered");
        Ok(())
    }

    /// Add a task with a custom dedup window.
    pub async fn add_task_with_dedup<F, Fut>(
        &self,
        name: &str,
        cron_expr: &str,
        handler: F,
        dedup_window_secs: u64,
    ) -> Result<(), String>
    where
        F: Fn() -> Fut + Send + Sync + 'static,
        Fut: Future<Output = AppResult<()>> + Send + 'static,
    {
        let cron = CronExpr::parse(cron_expr)?;
        let wrapped: AsyncTaskFn = Arc::new(move || Box::pin(handler()));
        let mut tasks = self.tasks.write().await;
        tasks.push(ScheduledTask {
            name: name.to_owned(),
            cron,
            handler: wrapped,
            redis: self.redis.clone(),
            dedup_window_secs,
        });
        tracing::info!(name, cron_expr, dedup_window_secs, "Scheduled task registered with dedup");
        Ok(())
    }

    /// Start polling for scheduled tasks. Runs in a background tokio task.
    ///
    /// Every tick, checks all registered tasks against the current time.
    /// When a task matches and dedup passes, the handler is spawned.
    pub fn start(&mut self) {
        let tasks = self.tasks.clone();
        let tick = self.tick_interval_secs;
        let _redis = self.redis.clone();

        let handle = tokio::spawn(async move {
            loop {
                tokio::time::sleep(Duration::from_secs(tick)).await;
                let now = Utc::now();
                let window_key = format!(
                    "cron:tick:{}",
                    now.format("%Y%m%d%H%M")
                );

                let tasks_guard = tasks.read().await;
                for task in tasks_guard.iter() {
                    if !task.cron.matches(&now) {
                        continue;
                    }

                    // Dedup check via Redis (if available)
                    if let Some(ref r) = task.redis {
                        let dedup_key = format!(
                            "cron:run:{}:{}",
                            task.name,
                            now.timestamp() / task.dedup_window_secs as i64
                        );
                        let already_run = r.exists(&dedup_key)
                            .await
                            .unwrap_or(Some(false))
                            .unwrap_or(false);
                        if already_run {
                            tracing::debug!(
                                name = %task.name,
                                "Scheduled task already ran in this window — skipping"
                            );
                            continue;
                        }
                        // Mark as running
                        let _ = r.setex(&dedup_key, "1", task.dedup_window_secs * 2).await;
                    }

                    tracing::info!(
                        name = %task.name,
                        window = %window_key,
                        "Scheduler: triggering task"
                    );
                    let handler = task.handler.clone();
                    let task_name = task.name.clone();
                    tokio::spawn(async move {
                        match handler().await {
                            Ok(()) => {
                                tracing::debug!(name = %task_name, "Scheduled task completed");
                            }
                            Err(e) => {
                                tracing::error!(name = %task_name, error = %e, "Scheduled task failed");
                            }
                        }
                    });
                }
            }
        });

        self._handle = Some(handle);
        tracing::info!("Cron scheduler started (tick={}s)", tick);
    }

    /// Stop the scheduler's background task.
    pub fn stop(&mut self) {
        if let Some(handle) = self._handle.take() {
            handle.abort();
        }
        tracing::info!("Cron scheduler stopped");
    }

    /// Get the number of registered tasks.
    pub async fn task_count(&self) -> usize {
        self.tasks.read().await.len()
    }
}

impl Default for CronScheduler {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Debug for CronScheduler {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("CronScheduler").finish()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_cron_wildcard() {
        let expr = CronExpr::parse("* * * * *").unwrap();
        let now = Utc::now();
        assert!(expr.matches(&now));
    }

    #[test]
    fn test_parse_cron_specific_hour() {
        let expr = CronExpr::parse("0 3 * * *").unwrap();
        let dt = Utc::now()
            .with_hour(3)
            .unwrap()
            .with_minute(0)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(expr.matches(&dt));

        let dt2 = Utc::now()
            .with_hour(12)
            .unwrap()
            .with_minute(0)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(!expr.matches(&dt2));
    }

    #[test]
    fn test_parse_cron_step() {
        let expr = CronExpr::parse("*/10 * * * *").unwrap();
        // minute 0 should match
        let dt = Utc::now()
            .with_minute(0)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(expr.matches(&dt));
        // minute 10 should match
        let dt2 = Utc::now()
            .with_minute(10)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(expr.matches(&dt2));
        // minute 7 should not match
        let dt3 = Utc::now()
            .with_minute(7)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(!expr.matches(&dt3));
    }

    #[test]
    fn test_parse_cron_comma_list() {
        let expr = CronExpr::parse("0,30 * * * *").unwrap();
        let dt0 = Utc::now()
            .with_minute(0)
            .unwrap()
            .with_second(0)
            .unwrap();
        let dt30 = Utc::now()
            .with_minute(30)
            .unwrap()
            .with_second(0)
            .unwrap();
        let dt15 = Utc::now()
            .with_minute(15)
            .unwrap()
            .with_second(0)
            .unwrap();
        assert!(expr.matches(&dt0));
        assert!(expr.matches(&dt30));
        assert!(!expr.matches(&dt15));
    }

    #[test]
    fn test_parse_cron_invalid_field_count() {
        assert!(CronExpr::parse("* * *").is_err());
        assert!(CronExpr::parse("* * * *").is_err());
    }

    #[test]
    fn test_cron_describe() {
        let expr = CronExpr::parse("0 3 * * *").unwrap();
        let desc = expr.describe();
        assert!(desc.contains("3h"));
    }

    #[test]
    fn test_step_field_out_of_range() {
        assert!(CronExpr::parse("*/60 * * * *").is_err()); // min range 0-59
        assert!(CronExpr::parse("* */24 * * *").is_err()); // hour range 0-23
    }
}
