//! 墨灵 (Moling) — Service / business logic layer.
//!
//! Each service module encapsulates domain-specific business rules,
//! delegating data access to the moling-db DAO layer.

#![allow(
    clippy::too_many_arguments,
    clippy::needless_range_loop,
    clippy::large_enum_variant,
    clippy::unnecessary_sort_by,
    clippy::manual_clamp
)]

pub mod algorithm_service;
pub mod book_analysis_service;
pub mod card_pool_service;
pub mod card_retire_service;
pub mod card_service;
pub mod chapter_service;
pub mod coherence_service;
pub mod conflict_detection;
pub mod direction_scoring;
pub mod generation_service;
pub mod genre;
pub mod health_monitor;
pub mod health_service;
pub mod import_service;
pub mod merge_service;
pub mod notification_service;
pub mod phase4_scheduler;
pub mod phase4_service;
pub mod phase4_store;
pub mod project_service;
pub mod prompt_service;
pub mod secret_service;
pub mod setting_service;
pub mod subscription_service;
pub mod template_service;
pub mod validation_service;
pub mod vault_filter;
pub mod vault_service;
pub mod weave_service;
pub mod weaving_scheme;

// Re-export key structs for convenience
pub use algorithm_service::AlgorithmService;
pub use book_analysis_service::BookAnalysisService;
pub use card_pool_service::CardPoolService;
pub use card_retire_service::{CardRetireService, RetireResult, RetireAuditEntry};
pub use card_service::CardService;
pub use chapter_service::{ChapterService, ChapterSuggestion};
pub use coherence_service::{CoherenceCheckItem, CoherenceGroupCheck, CoherenceValidationResult, CoherenceService};
pub use conflict_detection::{ConflictDetectionService, ConflictDetectionResult, ConflictItem};
pub use direction_scoring::{DirectionScoringService, DirectionConflictResult, DirectionCard, EntityConflict};
pub use generation_service::{
    ChapterDraft, CoherenceGroup, CoherenceResult, DirectionConflict, GenerationConfig,
    GenerationInput, GenerationOutput, GenerationService,
};
pub use genre::{GenreService, GenreProfile, PrefillResult, KNOWN_GENRES};
pub use health_monitor::{HealthMonitorService, HealthCheckResult, HealthAlert};
pub use health_service::{HealthService, HealthStatus};
pub use import_service::ImportService;
pub use import_service::split_chapters;
pub use merge_service::{MergeService, MergeResult, ChangeEntry, ConfidenceLevel, ExtractedCharacter, ExtractedTimelineEvent, ExtractedPlotPromise, ExtractedWorldItem};
pub use notification_service::NotificationService;
pub use phase4_scheduler::{Phase4Scheduler, Phase4Task, TaskResult, SchedulerStats, text_similarity, SOURCE_TEXT_SIMILARITY_THRESHOLD};
pub use phase4_service::{Phase4Service, Phase4Change, Phase4Result, Phase4Suggestion};
pub use phase4_store::Phase4Store;
pub use project_service::{ProjectService, ProjectUpdate, ProjectStats, Suggestion};
pub use prompt_service::{
    CardInfo, CharacterInfo, FullPromptInput, PlotPromiseAction, PlotPromiseInfo,
    PromptContext, PromptService, StyleFingerprint, TimelineEventInfo, WeavingScheme,
    WorldRuleInfo,
};
pub use secret_service::{
    PartialReveal, SecrecyLevel, SecrecyMatrixResult, SecretChainNode, SecretConflict,
    SecretDebtDetail, SecretDebtSummary, SecretMatrixEntry, SecretService,
};
pub use setting_service::SettingService;
pub use subscription_service::SubscriptionService;
pub use template_service::TemplateService;
pub use validation_service::{ValidationService, ValidationResult, CheckResult, ValidationCard};
pub use vault_filter::{VaultFilterService, VaultFilterResult, FilterCard, ExtractedIds};
pub use vault_service::{
    ChapterUpdateResult, CharacterImport, CharacterMergeRequest, ContinuityResult, EntityCounts,
    VaultFilterParams, VaultFilteredResult, VaultService, VaultSummary,
};
pub use weave_service::WeaveService;
pub use weaving_scheme::{WeavingSchemeService, WeavingSchemeResult, WeavingPattern, WeaveCard};
