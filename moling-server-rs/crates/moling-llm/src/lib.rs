//! 墨灵 (Moling) — LLM client crate.
//!
//! Provides:
//! - [`DeepSeekClient`] — API client with streaming, retry, and rate limiting
//! - [`KeyRotator`] — dual-pool API key rotation with health tracking
//! - [`TokenBudget`] / [`ContextBudget`] — token estimation and context window management
//! - [`PromptService`] — 5-layer structured prompt assembly for chapter generation
//! - [`PromptBuilder`] — convenience wrappers for common prompt types
//! - [`VaultAgent`] — domain-specific prompts for Plot/Character/Dialogue/Style/World agents
//! - [`PromptLibrary`] — pre-built chat message templates

pub mod budget;
pub mod client;
pub mod key_rotator;
pub mod prompt;
pub mod retry;

// ---------------------------------------------------------------------------
// Re-exports — primary API
// ---------------------------------------------------------------------------

pub use budget::{ContextBudget, TokenBudget, TruncationConfig, BudgetResult, TruncationRecord};
pub use client::{ChatMessage, DeepSeekClient, RateLimitTracker, DEFAULT_BASE_URL, DEFAULT_MODEL};
pub use key_rotator::{
    KeyHealth, KeyRotator, KeySnapshot, Pool, PoolStatus, SelectionStrategy,
};
pub use prompt::{
    ChapterContext, DirectionCard, DirectionContext, PromptBuilder, PromptLibrary,
    PromptService, StyleFingerprint, VaultAgent, VaultCharacter, VaultPlotPromise,
    VaultTimelineEvent, VaultWorldEntry, WeavingScheme,
};
pub use retry::{extract_retry_after, RetryPolicy};
