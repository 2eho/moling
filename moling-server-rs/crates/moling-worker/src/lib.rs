//! 墨灵 (Moling) — Background worker crate.
//!
//! Provides a Redis-backed task queue, cron scheduler, and 9
//! domain-specific workers for async processing:
//!
//! | Worker | Module | Trigger |
//! |--------|--------|---------|
//! | Generation | `workers::generation` | Queue (BRPOPLPUSH) |
//! | Phase4 | `workers::phase4` | Queue (post-confirm) |
//! | Vault Reanalyze | `workers::vault_reanalyze` | Cron / Manual |
//! | Card Retire | `workers::card_retire` | Cron (daily) |
//! | Health Notify | `workers::health_notify` | Cron (every 10min) |
//! | Import | `workers::import_task` | Queue (phased) |
//! | Analysis | `workers::analysis` | Queue (on-demand) |
//! | Notification | `workers::notification` | Queue (async delivery) |
//! | Coherence | `workers::coherence` | Cron / Manual (batch scan) |
//!
//! # Usage
//!
//! ```ignore
//! use moling_worker::{TaskQueue, CronScheduler};
//! let queue = TaskQueue::new(redis_client);
//! queue.push("generation", &task_json).await?;
//! ```

pub mod queue;
pub mod scheduler;
pub mod workers;

pub use queue::{DeadLetterAction, Priority, TaskMeta, TaskQueue, TaskStatus};
pub use scheduler::{CronExpr, CronField, CronScheduler};
