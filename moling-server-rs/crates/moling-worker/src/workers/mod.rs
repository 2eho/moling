//! Worker modules — background task implementations.
//!
//! Each worker handles a specific domain of async processing:
//! generation, Phase4 pipeline, vault reanalysis, card retirement,
//! health monitoring, book import, LLM analysis, notification delivery,
//! and coherence checking.

pub mod analysis;
pub mod card_retire;
pub mod coherence;
pub mod generation;
pub mod health_notify;
pub mod import_task;
pub mod notification;
pub mod phase4;
pub mod vault_reanalyze;
