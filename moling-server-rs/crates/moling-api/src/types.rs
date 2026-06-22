//! Request and response types for all API endpoints.
//!
//! Mirrors Python `app/schemas/` Pydantic models with Rust-native Serde derives.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

// =========================================================================
// Common — pagination, API wrapper
// =========================================================================

/// Standard paginated list response.
#[derive(Debug, Serialize)]
pub struct PaginatedList<T: Serialize> {
    pub items: Vec<T>,
    pub total: u64,
    pub page: u32,
    pub page_size: u32,
}

/// Standard API wrapper matching Python `{"detail": ...}` pattern for
/// success responses (errors use AppError's own format).
#[derive(Debug, Serialize)]
pub struct ApiResponse<T: Serialize> {
    pub data: T,
}

/// Simple message response.
#[derive(Debug, Serialize, ToSchema)]
pub struct MessageResponse {
    pub message: String,
}

// =========================================================================
// Auth
// =========================================================================

#[derive(Debug, Deserialize, ToSchema)]
pub struct RegisterReq {
    pub email: String,
    pub nickname: String,
    pub password: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct LoginReq {
    pub email: String,
    pub password: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct RefreshReq {
    pub refresh_token: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct LogoutReq {
    pub access_token: String,
    pub refresh_token: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct PasswordResetRequestReq {
    pub email: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct PasswordResetReq {
    pub token: String,
    pub new_password: String,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateProfileReq {
    pub username: Option<String>,
    pub avatar_url: Option<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct UserResp {
    pub id: String,
    pub email: String,
    pub nickname: String,
    pub avatar_url: Option<String>,
    pub status: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct TokenResp {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: i64,
    pub user: UserResp,
}

// =========================================================================
// Project
// =========================================================================

#[derive(Debug, Deserialize, ToSchema)]
pub struct CreateProjectReq {
    pub title: String,
    pub author: Option<String>,
    pub genre: Option<String>,
    pub synopsis: Option<String>,
    pub worldview: Option<String>,
    pub protagonist: Option<String>,
    pub style: Option<String>,
    pub target_words: Option<i32>,
    pub frequency: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateProjectReq {
    pub title: Option<String>,
    pub author: Option<String>,
    pub genre: Option<String>,
    pub synopsis: Option<String>,
    pub worldview: Option<String>,
    pub protagonist: Option<String>,
    pub style: Option<String>,
    pub target_words: Option<i32>,
    pub frequency: Option<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ProjectResp {
    pub id: i32,
    pub user_id: String,
    pub title: String,
    pub author: String,
    pub genre: String,
    pub synopsis: Option<String>,
    pub worldview: Option<String>,
    pub protagonist: Option<String>,
    pub style: Option<String>,
    pub word_count: i32,
    pub target_words: Option<i32>,
    pub status: String,
    pub creation_mode: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct ProjectStatsResp {
    pub total_projects: u64,
    pub total_words: u64,
    pub total_chapters: u64,
}

#[derive(Debug, Serialize)]
pub struct SingleProjectStatsResp {
    pub project_id: i32,
    pub title: String,
    pub total_chapters: u64,
    pub total_words: i32,
    pub status: String,
}

#[derive(Debug, Serialize)]
pub struct ProjectSuggestionResp {
    pub suggestions: Vec<String>,
}

// =========================================================================
// Chapter
// =========================================================================

#[derive(Debug, Deserialize, ToSchema)]
pub struct CreateChapterReq {
    pub title: String,
    pub content: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct UpdateChapterReq {
    pub title: Option<String>,
    pub content: Option<String>,
}

#[derive(Debug, Deserialize, ToSchema)]
pub struct ReorderChaptersReq {
    pub chapter_ids: Vec<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ChapterResp {
    pub id: String,
    pub project_id: i32,
    pub title: String,
    pub content: Option<String>,
    pub chapter_number: i32,
    pub status: String,
    pub word_count: i32,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// =========================================================================
// Vault
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct CreateCharacterReq {
    pub name: String,
    pub role: Option<String>,
    pub description: Option<String>,
    pub traits: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateCharacterReq {
    pub name: Option<String>,
    pub role: Option<String>,
    pub description: Option<String>,
    pub traits: Option<serde_json::Value>,
    pub faction: Option<String>,
    pub personality: Option<String>,
    pub background: Option<String>,
    pub status: Option<String>,
}

// -- Plot Promise types --

#[derive(Debug, Deserialize)]
pub struct CreatePlotPromiseReq {
    pub description: String,
    #[serde(default = "default_promise_type")]
    pub promise_type: String,
    #[serde(default)]
    pub urgency: i32,
    pub related_characters: Option<Vec<String>>,
    pub planted_chapter: Option<i32>,
}

fn default_promise_type() -> String { "foreshadowing".into() }

#[derive(Debug, Deserialize)]
pub struct UpdatePlotPromiseReq {
    pub description: Option<String>,
    pub promise_type: Option<String>,
    pub status: Option<String>,
    pub urgency: Option<i32>,
    pub related_characters: Option<Vec<String>>,
}

// -- Timeline types --

#[derive(Debug, Deserialize)]
pub struct CreateTimelineReq {
    pub event: String,
    pub description: String,
    #[serde(default)]
    pub chapter_number: i32,
    #[serde(default)]
    pub is_key_event: bool,
    pub impact: Option<String>,
    pub characters_involved: Option<Vec<String>>,
    pub importance: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateTimelineReq {
    pub event: Option<String>,
    pub description: Option<String>,
    pub chapter_number: Option<i32>,
    pub is_key_event: Option<bool>,
    pub impact: Option<String>,
    pub importance: Option<String>,
}

// -- World types --

#[derive(Debug, Deserialize)]
pub struct CreateWorldReq {
    pub name: String,
    pub description: String,
    #[serde(default = "default_world_category")]
    pub category: String,
    pub constraint: Option<String>,
    pub source_chapter: Option<i32>,
}

fn default_world_category() -> String { "general".into() }

#[derive(Debug, Deserialize)]
pub struct UpdateWorldReq {
    pub name: Option<String>,
    pub description: Option<String>,
    pub category: Option<String>,
    pub constraint: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct VaultSummaryResp {
    pub characters: u64,
    pub timelines: u64,
    pub plot_promises: u64,
    pub worlds: u64,
}

// =========================================================================
// Card
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct DrawCardsReq {
    pub count: Option<i32>,
    pub mode: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct CreateCardReq {
    pub name: String,
    pub description: String,
    pub rarity: String,
    pub direction_type: String,
    pub direction_text: String,
}

// =========================================================================
// Generation
// =========================================================================

#[derive(Debug, Deserialize, ToSchema)]
pub struct GenerateReq {
    pub mode: Option<String>,
    pub temperature: Option<f64>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct GenerationJobResp {
    pub id: String,
    pub project_id: i32,
    pub chapter_id: Option<String>,
    pub task_type: String,
    pub status: String,
    pub progress_percent: i32,
    pub created_at: DateTime<Utc>,
}

// =========================================================================
// Secret
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct CreateSecretReq {
    pub description: String,
    pub secrecy_level: Option<String>,
    pub known_by: Option<serde_json::Value>,
    pub unknown_to: Option<serde_json::Value>,
    pub debt: Option<i32>,
    pub created_chapter: Option<i32>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateSecretReq {
    pub description: Option<String>,
    pub secrecy_level: Option<String>,
    pub known_by: Option<serde_json::Value>,
    pub unknown_to: Option<serde_json::Value>,
    pub debt: Option<i32>,
}

// =========================================================================
// Template
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct CreateTemplateReq {
    pub name: String,
    pub description: String,
    pub genre: String,
    pub structure: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateTemplateReq {
    pub name: Option<String>,
    pub description: Option<String>,
    pub genre: Option<String>,
    pub structure: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
pub struct CreateProjectFromTemplateReq {
    pub template_id: String,
    pub title: String,
}

// =========================================================================
// Setting
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct ChangePasswordReq {
    pub current_password: String,
    pub new_password: String,
}

// =========================================================================
// Subscription
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct CreateCheckoutReq {
    pub plan_id: String,
}

#[derive(Debug, Deserialize)]
pub struct CreateSubscriptionReq {
    pub plan_id: String,
    #[serde(default = "default_auto_renew")]
    pub auto_renew: Option<bool>,
}

fn default_auto_renew() -> Option<bool> { Some(true) }

// =========================================================================
// Phase4
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct ApplyPhase4Req {
    pub chapter_id: String,
    pub suggestions: Vec<serde_json::Value>,
    #[serde(default)]
    pub auto_apply: bool,
}

// =========================================================================
// Weave
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct WeaveApplyReq {
    pub pattern: serde_json::Value,
    pub target_chapter_ids: Vec<String>,
}

// =========================================================================
// Admin
// =========================================================================

#[derive(Debug, Serialize)]
pub struct AdminStatsResp {
    pub users: u64,
    pub projects: u64,
    pub chapters: u64,
    pub generation_jobs: u64,
}

#[derive(Debug, Deserialize)]
pub struct AdminUpdateUserReq {
    pub role: Option<String>,
    pub status: Option<String>,
}

// =========================================================================
// Setting — health monitor, phase4 mode
// =========================================================================

#[derive(Debug, Deserialize)]
pub struct HealthMonitorReq {
    pub r1_enabled: bool,
    pub r2_enabled: bool,
    pub r3_enabled: bool,
    pub anti_fatigue: bool,
}

#[derive(Debug, Deserialize)]
pub struct Phase4ModeReq {
    pub mode: String,
}

// =========================================================================
// Notification filter query
// =========================================================================

/// Query parameters for notification listing with optional is_read filter.
#[derive(Debug, Deserialize)]
pub struct NotificationQuery {
    #[serde(default = "default_page")]
    pub page: u32,
    #[serde(default = "default_page_size")]
    pub page_size: u32,
    pub is_read: Option<bool>,
}

// =========================================================================
// Import — matches Python `app/schemas/ingest.py`
// =========================================================================

/// Submit an import job (Phase 0 — text ingestion + chapter splitting).
#[derive(Debug, Deserialize, ToSchema)]
pub struct SubmitImportReq {
    /// Raw text to import (novel body).
    pub text: String,
    /// Work title (optional, defaults to empty).
    #[serde(default)]
    pub title: String,
    /// Source type: "text", "markdown", etc.
    #[serde(default = "default_source_type")]
    pub source_type: String,
    /// Comma-separated split strategies, e.g. "chapter_regex,paragraph".
    #[serde(default)]
    pub split_strategies: Option<String>,
}

fn default_source_type() -> String {
    "text".into()
}

/// Response for a newly created import job.
#[derive(Debug, Serialize, ToSchema)]
pub struct ImportJobResp {
    pub success: bool,
    pub job_id: String,
    pub status: String,
}

/// Full import job status response (matches Python `IngestJobStatusResp`).
#[derive(Debug, Serialize, ToSchema)]
pub struct ImportJobStatusResp {
    pub success: bool,
    pub status: String,
    pub progress: ImportProgress,
    pub result: serde_json::Value,
    pub conflicts: Vec<serde_json::Value>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ImportProgress {
    pub phase: String,
    pub percent: f64,
}

/// List of import jobs for a project.
#[derive(Debug, Serialize, ToSchema)]
pub struct ImportJobListResp {
    pub success: bool,
    pub jobs: Vec<ImportJobSummary>,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct ImportJobSummary {
    pub id: String,
    pub source_type: String,
    pub title: String,
    pub total_chapters: i32,
    pub current_phase: String,
    pub progress_percent: f64,
    pub error_message: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Response after triggering a phase run.
#[derive(Debug, Serialize, ToSchema)]
pub struct PhaseRunResp {
    pub success: bool,
    pub message: String,
}

/// Response for a phase result poll.
#[derive(Debug, Serialize, ToSchema)]
pub struct PhaseStatusResp {
    pub success: bool,
    pub status: String,
    pub progress_percent: f64,
    pub result: Option<serde_json::Value>,
    pub error: Option<String>,
}

/// Query parameters for paginated listing.
#[derive(Debug, Deserialize)]
pub struct PaginationQuery {
    #[serde(default = "default_page")]
    pub page: u32,
    #[serde(default = "default_page_size")]
    pub page_size: u32,
}

pub fn default_page() -> u32 { 1 }
pub fn default_page_size() -> u32 { 20 }

// =========================================================================
// Project Health
// =========================================================================

/// A single health alert item.
#[derive(Debug, Serialize)]
pub struct HealthAlertItem {
    pub rule: String,
    pub title: String,
    pub detail: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub severity: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub level: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_active: Option<bool>,
}

/// Health check response.
#[derive(Debug, Serialize)]
pub struct HealthCheckResp {
    pub alerts: Vec<HealthAlertItem>,
    pub checked_at: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub alert_counts: Option<HealthAlertCounts>,
}

/// Health alert counts summary.
#[derive(Debug, Serialize)]
pub struct HealthAlertCounts {
    pub total: usize,
    pub critical: usize,
    pub warning: usize,
}
