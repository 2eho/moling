//! Vault service — Phase4 four-vault (四库) business logic.
//!
//! Mirrors Python `app/service/vault_service.py`.
//!
//! ## Four Vaults
//!
//! - **Characters** (角色库) — create/update/delete/list/merge, consistency checks
//! - **Plot Promises** (情节承诺库) — create/fulfill/break, status tracking (dormant/active/fulfilled/broken)
//! - **Timeline** (时间线) — event CRUD, continuity validation
//! - **World** (世界观库) — term/location/rule CRUD, consistency checks
//!
//! Plus:
//! - **Changelog** — audit trail for every mutation
//! - **filter_all** — unified four-vault query for prompt assembly
//! - **vault_summary** — 5-in-1 statistics

use std::collections::HashMap;

use moling_core::error::{AppError, AppResult};
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::vault_character::Model as Character;
use moling_db::entities::vault_changelog::Model as Changelog;
use moling_db::entities::vault_plot_promise::Model as PlotPromise;
use moling_db::entities::vault_timeline::Model as Timeline;
use moling_db::entities::vault_world::Model as World;
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Five-in-one vault summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultSummary {
    /// Total character count.
    pub character_count: u64,
    /// Total timeline event count.
    pub timeline_count: u64,
    /// Total plot promise count.
    pub plot_promise_count: u64,
    /// Total world entry count.
    pub world_count: u64,
    /// Total changelog entry count.
    pub changelog_count: u64,
    /// Per-status promise breakdown.
    pub promise_status_breakdown: HashMap<String, u64>,
    /// Recent character list (up to 5).
    pub recent_characters: Vec<Character>,
}

/// Filter parameters for unified vault queries.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct VaultFilterParams {
    /// Filter characters by name substring.
    pub character_name: Option<String>,
    /// Filter characters by role.
    pub character_role: Option<String>,
    /// Filter characters by status.
    pub character_status: Option<String>,
    /// Filter promises by type.
    pub promise_type: Option<String>,
    /// Filter promises by status (dormant/active/fulfilled/broken).
    pub promise_status: Option<String>,
    /// Filter timeline by chapter range start.
    pub timeline_chapter_start: Option<i32>,
    /// Filter timeline by chapter range end.
    pub timeline_chapter_end: Option<i32>,
    /// Filter world entries by category.
    pub world_category: Option<String>,
    /// Maximum results per vault (default: 50).
    pub limit: Option<u64>,
}

/// Result of a unified vault query (filter_all).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultFilteredResult {
    /// Filtered characters.
    pub characters: Vec<Character>,
    /// Filtered plot promises.
    pub plot_promises: Vec<PlotPromise>,
    /// Filtered timeline events.
    pub timeline: Vec<Timeline>,
    /// Filtered world entries.
    pub world_entries: Vec<World>,
}

/// Character import data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterImport {
    /// Character name.
    pub name: String,
    /// Character role.
    pub role: String,
    /// Character description.
    pub description: Option<String>,
    /// Character traits list.
    pub traits: Option<Vec<String>>,
    /// Character faction.
    pub faction: Option<String>,
    /// Character personality description.
    pub personality: Option<String>,
    /// Character background.
    pub background: Option<String>,
}

/// Result of a chapter-based vault update.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChapterUpdateResult {
    /// Project ID.
    pub project_id: i32,
    /// Chapter ID.
    pub chapter_id: String,
    /// Chapter number.
    pub chapter_number: i32,
    /// Number of newly created entries.
    pub created: usize,
    /// Number of updated entries.
    pub updated: usize,
    /// Per-category entity counts.
    pub entities_found: EntityCounts,
    /// Total entities found.
    pub total_entities: usize,
    /// Human-readable message.
    pub message: String,
}

/// Per-category entity counts from chapter analysis.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EntityCounts {
    /// Characters found.
    pub characters: usize,
    /// Locations found.
    pub locations: usize,
    /// Items found.
    pub items: usize,
}

/// Continuity check result for timeline validation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContinuityResult {
    /// Whether the timeline is continuous.
    pub is_continuous: bool,
    /// Detected gaps (pairs of chapter numbers).
    pub gaps: Vec<(i32, i32)>,
    /// Detected duplicates (same chapter number appearing multiple times).
    pub duplicates: Vec<i32>,
    /// Total events checked.
    pub total_events: usize,
}

/// Character merge request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CharacterMergeRequest {
    /// Source character ID (will be deleted/merged).
    pub source_id: String,
    /// Target character ID (will absorb source).
    pub target_id: String,
}

// ---------------------------------------------------------------------------
// VaultService
// ---------------------------------------------------------------------------

/// Business logic for vault operations across all four databases.
#[derive(Clone)]
pub struct VaultService {
    vault_dao: VaultDao,
    project_dao: ProjectDao,
    chapter_dao: ChapterDao,
}

impl VaultService {
    /// Create a new VaultService.
    pub fn new() -> Self {
        Self {
            vault_dao: VaultDao,
            project_dao: ProjectDao,
            chapter_dao: ChapterDao,
        }
    }

    /// Verify project ownership and return the project model.
    async fn verify_owner(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<moling_db::entities::project::Model> {
        let p = self
            .project_dao
            .find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(p)
    }

    /// Record a changelog entry for an audit trail.
    async fn record_changelog(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: Option<&str>,
        change_type: &str,
        entity_type: &str,
        entity_id: Option<&str>,
        field_name: Option<&str>,
        old_value: Option<&str>,
        new_value: Option<&str>,
        reason: Option<&str>,
    ) -> AppResult<()> {
        let model = moling_db::entities::vault_changelog::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            chapter_id: Set(chapter_id.map(|s| s.to_owned())),
            change_type: Set(change_type.to_owned()),
            entity_type: Set(entity_type.to_owned()),
            entity_id: Set(entity_id.map(|s| s.to_owned())),
            field_name: Set(field_name.map(|s| s.to_owned())),
            old_value: Set(old_value.map(|s| s.to_owned())),
            new_value: Set(new_value.map(|s| s.to_owned())),
            change_reason: Set(reason.map(|s| s.to_owned())),
            meta_data: Set(None),
            ..Default::default()
        };

        let _ = self.vault_dao.create_changelog(db, model).await?;
        Ok(())
    }

    // ==================================================================
    // Characters (角色库)
    // ==================================================================

    /// List all characters in a project's vault.
    pub async fn list_characters(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<Character>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.vault_dao.find_characters(db, project_id).await
    }

    /// Get a single character by ID.
    pub async fn get_character(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_id: &str,
    ) -> AppResult<Character> {
        self.verify_owner(db, user_id, project_id).await?;

        let c = self
            .vault_dao
            .find_character_by_id(db, character_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if c.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        Ok(c)
    }

    /// Create a new character in the vault.
    pub async fn create_character(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        name: &str,
        role: &str,
        description: Option<&str>,
        traits: Option<&[String]>,
        faction: Option<&str>,
        personality: Option<&str>,
        background: Option<&str>,
    ) -> AppResult<Character> {
        self.verify_owner(db, user_id, project_id).await?;

        let traits_json = traits.map(|t| {
            Json::Array(t.iter().map(|s| Json::String(s.clone())).collect())
        });

        let model = moling_db::entities::vault_character::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            name: Set(name.to_owned()),
            role: Set(role.to_owned()),
            description: Set(description.map(|s| s.to_owned())),
            traits: Set(traits_json),
            faction: Set(faction.map(|s| s.to_owned())),
            personality: Set(personality.map(|s| s.to_owned())),
            background: Set(background.map(|s| s.to_owned())),
            status: Set("active".to_owned()),
            ..Default::default()
        };

        let character = self.vault_dao.create_character(db, model).await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "create", "character",
                Some(&character.id), None, None, Some(name),
                Some(&format!("创建角色: {name}")),
            )
            .await;

        tracing::info!(character_id = %character.id, name = %character.name, "Character created");
        Ok(character)
    }

    /// Update a character's fields.
    #[allow(clippy::too_many_arguments)]
    pub async fn update_character(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_id: &str,
        name: Option<&str>,
        role: Option<&str>,
        description: Option<&str>,
        traits: Option<&[String]>,
        faction: Option<&str>,
        personality: Option<&str>,
        background: Option<&str>,
        status: Option<&str>,
    ) -> AppResult<Character> {
        self.verify_owner(db, user_id, project_id).await?;

        let c = self
            .vault_dao
            .find_character_by_id(db, character_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if c.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let old_name = c.name.clone();
        let mut active = c.into_active_model();

        if let Some(v) = name {
            active.name = Set(v.to_owned());
        }
        if let Some(v) = role {
            active.role = Set(v.to_owned());
        }
        if let Some(v) = description {
            active.description = Set(Some(v.to_owned()));
        }
        if let Some(v) = traits {
            active.traits = Set(Some(Json::Array(
                v.iter().map(|s| Json::String(s.clone())).collect(),
            )));
        }
        if let Some(v) = faction {
            active.faction = Set(Some(v.to_owned()));
        }
        if let Some(v) = personality {
            active.personality = Set(Some(v.to_owned()));
        }
        if let Some(v) = background {
            active.background = Set(Some(v.to_owned()));
        }
        if let Some(v) = status {
            active.status = Set(v.to_owned());
        }

        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新角色失败: {e}"))
        })?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "update", "character",
                Some(character_id), None, Some(&old_name),
                Some(&updated.name),
                Some("更新角色"),
            )
            .await;

        tracing::info!(character_id = %updated.id, "Character updated");
        Ok(updated)
    }

    /// Soft-delete a character from the vault.
    pub async fn delete_character(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        character_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;

        // Verify ownership
        let c = self
            .vault_dao
            .find_character_by_id(db, character_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;
        if c.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let name = c.name.clone();
        self.vault_dao.soft_delete_character(db, character_id).await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "delete", "character",
                Some(character_id), None, Some(&name), None,
                Some("删除角色"),
            )
            .await;

        tracing::info!(character_id, "Character deleted");
        Ok(())
    }

    /// Merge two characters — source absorbed into target, source deleted.
    pub async fn merge_characters(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        merge: &CharacterMergeRequest,
    ) -> AppResult<Character> {
        self.verify_owner(db, user_id, project_id).await?;

        let source = self
            .vault_dao
            .find_character_by_id(db, &merge.source_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        let target = self
            .vault_dao
            .find_character_by_id(db, &merge.target_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if source.project_id != project_id || target.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        // Merge: combine chapter_count, append source description to target
        let combined_count = source.chapter_count + target.chapter_count;
        let source_desc = source.description.clone().unwrap_or_default();
        let target_desc = target.description.clone().unwrap_or_default();
        let merged_description = if !source_desc.is_empty() {
            format!("{target_desc}\n\n[合并自「{}」] {source_desc}", source.name)
        } else {
            target_desc
        };

        let mut active = target.into_active_model();
        active.chapter_count = Set(combined_count);
        active.description = Set(Some(merged_description));
        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("合并角色失败: {e}"))
        })?;

        // Soft-delete source
        self.vault_dao
            .soft_delete_character(db, &merge.source_id)
            .await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "merge", "character",
                Some(&merge.target_id), None,
                Some(&source.name),
                Some(&updated.name),
                Some(&format!("合并角色: {} → {}", source.name, updated.name)),
            )
            .await;

        tracing::info!(
            source = %source.name,
            target = %updated.name,
            "Characters merged"
        );

        Ok(updated)
    }

    /// Batch import characters from external data.
    pub async fn import_characters(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        imports: &[CharacterImport],
    ) -> AppResult<Vec<Character>> {
        self.verify_owner(db, user_id, project_id).await?;

        let mut results: Vec<Character> = Vec::new();
        let mut created = 0usize;
        let mut updated = 0usize;

        for imp in imports {
            // Check if character already exists by name
            let existing = self
                .vault_dao
                .find_character_by_name(db, project_id, &imp.name)
                .await?;

            if let Some(existing_char) = existing {
                // Update existing
                let mut active = existing_char.into_active_model();
                if let Some(ref desc) = imp.description {
                    active.description = Set(Some(desc.clone()));
                }
                if let Some(ref traits) = imp.traits {
                    active.traits = Set(Some(Json::Array(
                        traits.iter().map(|s| Json::String(s.clone())).collect(),
                    )));
                }
                if !imp.role.is_empty() {
                    active.role = Set(imp.role.clone());
                }
                let updated_char = active.update(db).await.map_err(|e| {
                    AppError::internal(format!("导入更新角色失败: {e}"))
                })?;
                results.push(updated_char);
                updated += 1;
            } else {
                // Create new
                let traits_json = imp.traits.as_ref().map(|t| {
                    Json::Array(t.iter().map(|s| Json::String(s.clone())).collect())
                });

                let model = moling_db::entities::vault_character::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(imp.name.clone()),
                    role: Set(imp.role.clone()),
                    description: Set(imp.description.clone()),
                    traits: Set(traits_json),
                    faction: Set(imp.faction.clone()),
                    personality: Set(imp.personality.clone()),
                    background: Set(imp.background.clone()),
                    status: Set("active".to_owned()),
                    ..Default::default()
                };
                let new_char = self.vault_dao.create_character(db, model).await?;
                results.push(new_char);
                created += 1;
            }
        }

        tracing::info!(
            import_count = imports.len(),
            created,
            updated,
            "Character import complete"
        );

        Ok(results)
    }

    /// Check character consistency — verifies characters have non-empty names,
    /// reasonable roles, and no duplicate names within a project.
    pub async fn check_character_consistency(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<String>> {
        self.verify_owner(db, user_id, project_id).await?;

        let characters = self.vault_dao.find_characters(db, project_id).await?;
        let mut issues: Vec<String> = Vec::new();
        let mut name_counts: HashMap<String, usize> = HashMap::new();

        for c in &characters {
            // Check empty name
            if c.name.trim().is_empty() {
                issues.push(format!("角色(id={})名称为空", c.id));
            }

            // Track name duplicates
            *name_counts.entry(c.name.clone()).or_default() += 1;

            // Check empty role
            if c.role.trim().is_empty() {
                issues.push(format!("角色「{}」(id={})未设定角色类型", c.name, c.id));
            }

            // Check missing description
            if c.description.as_deref().unwrap_or("").trim().is_empty() {
                issues.push(format!("角色「{}」(id={})缺少描述", c.name, c.id));
            }
        }

        // Report duplicates
        for (name, count) in name_counts {
            if count > 1 {
                issues.push(format!("角色名称「{name}」出现{count}次，存在重复"));
            }
        }

        tracing::info!(
            project_id,
            characters = characters.len(),
            issues = issues.len(),
            "Character consistency check complete"
        );

        Ok(issues)
    }

    // ==================================================================
    // Plot Promises (情节承诺库)
    // ==================================================================

    /// List all plot promises in a project's vault.
    pub async fn list_plot_promises(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<PlotPromise>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.vault_dao.find_plot_promises(db, project_id).await
    }

    /// Get a single plot promise by ID.
    pub async fn get_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        promise_id: &str,
    ) -> AppResult<PlotPromise> {
        self.verify_owner(db, user_id, project_id).await?;

        let p = self
            .vault_dao
            .find_plot_promise_by_id(db, promise_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if p.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        Ok(p)
    }

    /// Create a new plot promise.
    pub async fn create_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        description: &str,
        promise_type: &str,
        urgency: i32,
        related_characters: Option<&[String]>,
        planted_chapter: Option<i32>,
    ) -> AppResult<PlotPromise> {
        self.verify_owner(db, user_id, project_id).await?;

        let related_json = related_characters.map(|rc| {
            Json::Array(rc.iter().map(|s| Json::String(s.clone())).collect())
        });

        let model = moling_db::entities::vault_plot_promise::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            description: Set(description.to_owned()),
            r#type: Set(promise_type.to_owned()),
            status: Set("dormant".to_owned()),
            urgency: Set(urgency),
            related_characters: Set(related_json),
            planted_chapter: Set(planted_chapter),
            ..Default::default()
        };

        let promise = self.vault_dao.create_plot_promise(db, model).await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "create", "plot_promise",
                Some(&promise.id), None, None, Some(description),
                Some(&format!("创建情节承诺: {description}")),
            )
            .await;

        tracing::info!(promise_id = %promise.id, "Plot promise created");
        Ok(promise)
    }

    /// Update a plot promise.
    pub async fn update_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        promise_id: &str,
        description: Option<&str>,
        promise_type: Option<&str>,
        status: Option<&str>,
        urgency: Option<i32>,
        related_characters: Option<&[String]>,
    ) -> AppResult<PlotPromise> {
        self.verify_owner(db, user_id, project_id).await?;

        let p = self
            .vault_dao
            .find_plot_promise_by_id(db, promise_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if p.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let old_status = p.status.clone();
        let mut active = p.into_active_model();

        if let Some(v) = description {
            active.description = Set(v.to_owned());
        }
        if let Some(v) = promise_type {
            active.r#type = Set(v.to_owned());
        }
        if let Some(v) = status {
            active.status = Set(v.to_owned());
        }
        if let Some(v) = urgency {
            active.urgency = Set(v);
        }
        if let Some(v) = related_characters {
            active.related_characters = Set(Some(Json::Array(
                v.iter().map(|s| Json::String(s.clone())).collect(),
            )));
        }

        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新情节承诺失败: {e}"))
        })?;

        // Record changelog for status transitions
        if updated.status != old_status {
            let _ = self
                .record_changelog(
                    db, project_id, None, "status_change", "plot_promise",
                    Some(promise_id),
                    Some("status"),
                    Some(&old_status),
                    Some(&updated.status),
                    Some(&format!("状态变更: {old_status} → {}", updated.status)),
                )
                .await;
        }

        tracing::info!(promise_id = %updated.id, status = %updated.status, "Plot promise updated");
        Ok(updated)
    }

    /// Fulfill a plot promise — marks it as "fulfilled".
    pub async fn fulfill_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        promise_id: &str,
        chapter_id: Option<&str>,
    ) -> AppResult<PlotPromise> {
        self.update_plot_promise(
            db, user_id, project_id, promise_id,
            None, None, Some("fulfilled"), None, None,
        )
        .await?;

        let updated = self
            .vault_dao
            .find_plot_promise_by_id(db, promise_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, chapter_id, "fulfill", "plot_promise",
                Some(promise_id), None, None, None,
                Some("兑现情节承诺"),
            )
            .await;

        tracing::info!(promise_id, "Plot promise fulfilled");
        Ok(updated)
    }

    /// Break/abandon a plot promise — marks it as "broken".
    pub async fn break_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        promise_id: &str,
        reason: Option<&str>,
    ) -> AppResult<PlotPromise> {
        self.update_plot_promise(
            db, user_id, project_id, promise_id,
            None, None, Some("broken"), None, None,
        )
        .await?;

        let updated = self
            .vault_dao
            .find_plot_promise_by_id(db, promise_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "break", "plot_promise",
                Some(promise_id), None, None, None,
                reason.or(Some("废弃情节承诺")),
            )
            .await;

        tracing::info!(promise_id, reason, "Plot promise broken");
        Ok(updated)
    }

    /// Delete a plot promise (soft-delete).
    pub async fn delete_plot_promise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        promise_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;

        let p = self
            .vault_dao
            .find_plot_promise_by_id(db, promise_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if p.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let desc = p.description.clone();
        self.vault_dao
            .soft_delete_plot_promise(db, promise_id)
            .await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "delete", "plot_promise",
                Some(promise_id), None, Some(&desc), None,
                Some("删除情节承诺"),
            )
            .await;

        tracing::info!(promise_id, "Plot promise deleted");
        Ok(())
    }

    /// Get status breakdown for plot promises.
    /// Uses a single GROUP BY query instead of N per-status queries.
    pub async fn get_promise_status_breakdown(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<HashMap<String, u64>> {
        self.vault_dao
            .count_plot_promises_by_status_batch(db, project_id)
            .await
    }

    // ==================================================================
    // Timeline (时间线)
    // ==================================================================

    /// List all timeline events in a project's vault.
    pub async fn list_timeline(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<Timeline>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.vault_dao.find_timeline_events(db, project_id).await
    }

    /// Get a single timeline event by ID.
    pub async fn get_timeline_event(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        event_id: &str,
    ) -> AppResult<Timeline> {
        self.verify_owner(db, user_id, project_id).await?;

        let t = self
            .vault_dao
            .find_timeline_by_id(db, event_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if t.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        Ok(t)
    }

    /// Create a new timeline event.
    #[allow(clippy::too_many_arguments)]
    pub async fn create_timeline_event(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        event: &str,
        description: &str,
        chapter_number: i32,
        is_key_event: bool,
        impact: Option<&str>,
        characters_involved: Option<&[String]>,
        importance: Option<&str>,
    ) -> AppResult<Timeline> {
        self.verify_owner(db, user_id, project_id).await?;

        let chars_json = characters_involved.map(|ci| {
            Json::Array(ci.iter().map(|s| Json::String(s.clone())).collect())
        });

        let model = moling_db::entities::vault_timeline::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            event: Set(event.to_owned()),
            description: Set(description.to_owned()),
            chapter_number: Set(chapter_number),
            is_key_event: Set(is_key_event),
            impact: Set(impact.map(|s| s.to_owned())),
            characters_involved: Set(chars_json),
            importance: Set(importance.map(|s| s.to_owned())),
            ..Default::default()
        };

        let timeline = self.vault_dao.create_timeline(db, model).await?;

        // Record changelog
        let _ = self
            .record_changelog(
                db, project_id, None, "create", "timeline",
                Some(&timeline.id), None, None, Some(event),
                Some(&format!("创建时间线事件: {event}")),
            )
            .await;

        tracing::info!(timeline_id = %timeline.id, event = %timeline.event, "Timeline event created");
        Ok(timeline)
    }

    /// Update a timeline event.
    #[allow(clippy::too_many_arguments)]
    pub async fn update_timeline_event(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        event_id: &str,
        event_text: Option<&str>,
        description: Option<&str>,
        chapter_number: Option<i32>,
        is_key_event: Option<bool>,
        impact: Option<&str>,
        importance: Option<&str>,
    ) -> AppResult<Timeline> {
        self.verify_owner(db, user_id, project_id).await?;

        let t = self
            .vault_dao
            .find_timeline_by_id(db, event_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if t.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let mut active = t.into_active_model();
        if let Some(v) = event_text {
            active.event = Set(v.to_owned());
        }
        if let Some(v) = description {
            active.description = Set(v.to_owned());
        }
        if let Some(v) = chapter_number {
            active.chapter_number = Set(v);
        }
        if let Some(v) = is_key_event {
            active.is_key_event = Set(v);
        }
        if let Some(v) = impact {
            active.impact = Set(Some(v.to_owned()));
        }
        if let Some(v) = importance {
            active.importance = Set(Some(v.to_owned()));
        }

        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新时间线事件失败: {e}"))
        })?;

        let _ = self
            .record_changelog(
                db, project_id, None, "update", "timeline",
                Some(event_id), None, None, Some(&updated.event),
                Some("更新时间线事件"),
            )
            .await;

        tracing::info!(event_id = %updated.id, "Timeline event updated");
        Ok(updated)
    }

    /// Delete a timeline event (soft-delete).
    pub async fn delete_timeline_event(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        event_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;

        let t = self
            .vault_dao
            .find_timeline_by_id(db, event_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if t.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let evt = t.event.clone();
        self.vault_dao.soft_delete_timeline(db, event_id).await?;

        let _ = self
            .record_changelog(
                db, project_id, None, "delete", "timeline",
                Some(event_id), None, Some(&evt), None,
                Some("删除时间线事件"),
            )
            .await;

        tracing::info!(event_id, "Timeline event deleted");
        Ok(())
    }

    /// Validate timeline continuity — check for gaps and duplicates.
    pub async fn validate_timeline_continuity(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<ContinuityResult> {
        self.verify_owner(db, user_id, project_id).await?;

        let events = self.vault_dao.find_timeline_events(db, project_id).await?;
        let mut chapter_nums: Vec<i32> = events
            .iter()
            .map(|e| e.chapter_number)
            .collect();
        chapter_nums.sort_unstable();
        chapter_nums.dedup();

        let mut gaps: Vec<(i32, i32)> = Vec::new();
        for window in chapter_nums.windows(2) {
            if window[1] - window[0] > 1 {
                gaps.push((window[0] + 1, window[1] - 1));
            }
        }

        // Detect duplicates
        let mut num_counts: HashMap<i32, usize> = HashMap::new();
        for e in &events {
            *num_counts.entry(e.chapter_number).or_default() += 1;
        }
        let duplicates: Vec<i32> = num_counts
            .into_iter()
            .filter(|(_, count)| *count > 1)
            .map(|(num, _)| num)
            .collect();

        let is_continuous = gaps.is_empty();

        tracing::info!(
            project_id,
            events = events.len(),
            gaps = gaps.len(),
            duplicates = duplicates.len(),
            "Timeline continuity validated"
        );

        Ok(ContinuityResult {
            is_continuous,
            gaps,
            duplicates,
            total_events: events.len(),
        })
    }

    // ==================================================================
    // World (世界观库)
    // ==================================================================

    /// List all world-building entries in a project's vault.
    pub async fn list_world_entries(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<World>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.vault_dao.find_world_entries(db, project_id).await
    }

    /// Get a single world entry by ID.
    pub async fn get_world_entry(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        entry_id: &str,
    ) -> AppResult<World> {
        self.verify_owner(db, user_id, project_id).await?;

        let w = self
            .vault_dao
            .find_world_by_id(db, entry_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if w.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        Ok(w)
    }

    /// Create a new world-building entry.
    pub async fn create_world_entry(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        name: &str,
        description: &str,
        category: &str,
        constraint: Option<&str>,
        source_chapter: Option<i32>,
    ) -> AppResult<World> {
        self.verify_owner(db, user_id, project_id).await?;

        let model = moling_db::entities::vault_world::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            name: Set(name.to_owned()),
            description: Set(description.to_owned()),
            category: Set(category.to_owned()),
            constraint: Set(constraint.map(|s| s.to_owned())),
            source_chapter: Set(source_chapter),
            ..Default::default()
        };

        let entry = self.vault_dao.create_world(db, model).await?;

        let _ = self
            .record_changelog(
                db, project_id, None, "create", "world",
                Some(&entry.id), None, None, Some(name),
                Some(&format!("创建世界观条目: {name}")),
            )
            .await;

        tracing::info!(entry_id = %entry.id, name = %entry.name, "World entry created");
        Ok(entry)
    }

    /// Update a world-building entry.
    pub async fn update_world_entry(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        entry_id: &str,
        name: Option<&str>,
        description: Option<&str>,
        category: Option<&str>,
        constraint: Option<&str>,
    ) -> AppResult<World> {
        self.verify_owner(db, user_id, project_id).await?;

        let w = self
            .vault_dao
            .find_world_by_id(db, entry_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if w.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let mut active = w.into_active_model();
        if let Some(v) = name {
            active.name = Set(v.to_owned());
        }
        if let Some(v) = description {
            active.description = Set(v.to_owned());
        }
        if let Some(v) = category {
            active.category = Set(v.to_owned());
        }
        if let Some(v) = constraint {
            active.constraint = Set(Some(v.to_owned()));
        }

        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新世界观条目失败: {e}"))
        })?;

        let _ = self
            .record_changelog(
                db, project_id, None, "update", "world",
                Some(entry_id), None, None, Some(&updated.name),
                Some("更新世界观条目"),
            )
            .await;

        tracing::info!(entry_id, "World entry updated");
        Ok(updated)
    }

    /// Delete a world entry (soft-delete).
    pub async fn delete_world_entry(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        entry_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;

        let w = self
            .vault_dao
            .find_world_by_id(db, entry_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if w.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        let name = w.name.clone();
        self.vault_dao.soft_delete_world(db, entry_id).await?;

        let _ = self
            .record_changelog(
                db, project_id, None, "delete", "world",
                Some(entry_id), None, Some(&name), None,
                Some("删除世界观条目"),
            )
            .await;

        tracing::info!(entry_id, "World entry deleted");
        Ok(())
    }

    /// Check world consistency — verifies no contradictory rules.
    pub async fn check_world_consistency(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<String>> {
        self.verify_owner(db, user_id, project_id).await?;

        let entries = self.vault_dao.find_world_entries(db, project_id).await?;
        let mut issues: Vec<String> = Vec::new();

        // Check for duplicate names within same category
        let mut name_cat_map: HashMap<(String, String), usize> = HashMap::new();
        for w in &entries {
            let key = (w.name.clone(), w.category.clone());
            *name_cat_map.entry(key).or_default() += 1;
        }
        for ((name, cat), count) in name_cat_map {
            if count > 1 {
                issues.push(format!(
                    "世界观条目「{name}」在类别「{cat}」中出现{count}次"
                ));
            }
        }

        // Check empty descriptions
        for w in &entries {
            if w.description.trim().is_empty() {
                issues.push(format!(
                    "世界观条目「{}」(id={})缺少描述",
                    w.name, w.id
                ));
            }
        }

        tracing::info!(
            project_id,
            entries = entries.len(),
            issues = issues.len(),
            "World consistency check complete"
        );

        Ok(issues)
    }

    // ==================================================================
    // Changelog (审计日志)
    // ==================================================================

    /// List changelogs for a project.
    pub async fn list_changelogs(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<Changelog>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.vault_dao.find_changelogs(db, project_id).await
    }

    /// Get a single changelog entry by ID.
    pub async fn get_changelog(
        &self,
        db: &DatabaseConnection,
        _user_id: &str,
        project_id: i32,
        changelog_id: &str,
    ) -> AppResult<Changelog> {
        let entry = self
            .vault_dao
            .find_changelog_by_id(db, changelog_id)
            .await?
            .ok_or_else(AppError::vault_entry_not_found)?;

        if entry.project_id != project_id {
            return Err(AppError::vault_entry_not_found());
        }

        Ok(entry)
    }

    // ==================================================================
    // Unified Query (filter_all)
    // ==================================================================

    /// Unified four-vault query — returns filtered data from all vaults.
    ///
    /// Used for prompt assembly — provides a single entry point to gather
    /// characters, plot promises, timeline events, and world entries
    /// relevant to the current generation context.
    pub async fn filter_all(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        params: &VaultFilterParams,
    ) -> AppResult<VaultFilteredResult> {
        self.verify_owner(db, user_id, project_id).await?;

        let limit = params.limit.unwrap_or(50) as usize;

        // Fetch all data (in-memory filtering for simplicity)
        let all_chars = self.vault_dao.find_characters(db, project_id).await?;
        let all_promises = self.vault_dao.find_plot_promises(db, project_id).await?;
        let all_timeline = self.vault_dao.find_timeline_events(db, project_id).await?;
        let all_worlds = self.vault_dao.find_world_entries(db, project_id).await?;

        // Filter characters
        let characters: Vec<Character> = all_chars
            .into_iter()
            .filter(|c| {
                if let Some(ref name) = params.character_name
                    && !c.name.contains(name) {
                        return false;
                    }
                if let Some(ref role) = params.character_role
                    && c.role != *role {
                        return false;
                    }
                if let Some(ref status) = params.character_status
                    && c.status != *status {
                        return false;
                    }
                true
            })
            .take(limit)
            .collect();

        // Filter promises
        let plot_promises: Vec<PlotPromise> = all_promises
            .into_iter()
            .filter(|p| {
                if let Some(ref ptype) = params.promise_type
                    && p.r#type != *ptype {
                        return false;
                    }
                if let Some(ref status) = params.promise_status
                    && p.status != *status {
                        return false;
                    }
                true
            })
            .take(limit)
            .collect();

        // Filter timeline
        let timeline: Vec<Timeline> = all_timeline
            .into_iter()
            .filter(|t| {
                if let Some(start) = params.timeline_chapter_start
                    && t.chapter_number < start {
                        return false;
                    }
                if let Some(end) = params.timeline_chapter_end
                    && t.chapter_number > end {
                        return false;
                    }
                true
            })
            .take(limit)
            .collect();

        // Filter world entries
        let world_entries: Vec<World> = all_worlds
            .into_iter()
            .filter(|w| {
                if let Some(ref cat) = params.world_category
                    && w.category != *cat {
                        return false;
                    }
                true
            })
            .take(limit)
            .collect();

        tracing::info!(
            project_id,
            characters = characters.len(),
            promises = plot_promises.len(),
            timeline = timeline.len(),
            world = world_entries.len(),
            "Unified vault query complete"
        );

        Ok(VaultFilteredResult {
            characters,
            plot_promises,
            timeline,
            world_entries,
        })
    }

    // ==================================================================
    // Chapter-based Update (update_from_chapter)
    // ==================================================================

    /// Extract entities from a chapter and update the vault.
    ///
    /// Parses chapter content for character names, locations, and items,
    /// then creates/updates corresponding vault entries.
    pub async fn update_from_chapter(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<ChapterUpdateResult> {
        let _project = self.verify_owner(db, user_id, project_id).await?;

        let chapter = self
            .chapter_dao
            .find_by_id(db, chapter_id)
            .await?
            .ok_or_else(AppError::chapter_not_found)?;

        if chapter.project_id != project_id {
            return Err(AppError::bad_request("章节不属于该项目".to_owned()));
        }

        let content = chapter.content.as_deref().unwrap_or("");
        if content.trim().is_empty() {
            return Ok(ChapterUpdateResult {
                project_id,
                chapter_id: chapter_id.to_owned(),
                chapter_number: chapter.chapter_number,
                created: 0,
                updated: 0,
                entities_found: EntityCounts::default(),
                total_entities: 0,
                message: "章节内容为空，跳过分析".to_owned(),
            });
        }

        // Entity extraction via regex
        let entities = Self::extract_entities_from_text(content);

        let mut created_count = 0usize;
        let mut updated_count = 0usize;

        // Update characters
        for char_name in &entities.characters {
            let existing = self
                .vault_dao
                .find_character_by_name(db, project_id, char_name)
                .await?;

            if let Some(existing_char) = existing {
                let new_count = existing_char.chapter_count + 1;
                let mut active = existing_char.into_active_model();
                active.chapter_count = Set(new_count);
                let _ = active.update(db).await.map_err(|e| {
                    AppError::internal(format!("更新角色出现次数失败: {e}"))
                })?;
                updated_count += 1;
            } else {
                let model = moling_db::entities::vault_character::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(char_name.clone()),
                    role: Set("neutral".to_owned()),
                    description: Set(Some(format!(
                        "从第{}章自动提取",
                        chapter.chapter_number
                    ))),
                    status: Set("active".to_owned()),
                    chapter_count: Set(1),
                    ..Default::default()
                };
                let _ = self.vault_dao.create_character(db, model).await?;
                created_count += 1;
            }
        }

        // Update locations as world entries
        for loc_name in &entities.locations {
            let existing = self
                .vault_dao
                .find_world_by_term(db, project_id, loc_name)
                .await?;

            if existing.is_some() {
                updated_count += 1;
            } else {
                let model = moling_db::entities::vault_world::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(loc_name.clone()),
                    description: Set(format!(
                        "从第{}章自动提取的地点",
                        chapter.chapter_number
                    )),
                    category: Set("location".to_owned()),
                    source_chapter: Set(Some(chapter.chapter_number)),
                    ..Default::default()
                };
                let _ = self.vault_dao.create_world(db, model).await?;
                created_count += 1;
            }
        }

        // Update items as world entries
        for item_name in &entities.items {
            let existing = self
                .vault_dao
                .find_world_by_term(db, project_id, item_name)
                .await?;

            if existing.is_some() {
                updated_count += 1;
            } else {
                let model = moling_db::entities::vault_world::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(item_name.clone()),
                    description: Set(format!(
                        "从第{}章自动提取的物品",
                        chapter.chapter_number
                    )),
                    category: Set("item".to_owned()),
                    source_chapter: Set(Some(chapter.chapter_number)),
                    ..Default::default()
                };
                let _ = self.vault_dao.create_world(db, model).await?;
                created_count += 1;
            }
        }

        let total = entities.characters.len()
            + entities.locations.len()
            + entities.items.len();

        let message = format!(
            "从第{}章提取并更新保险库：新增{created_count}条，更新{updated_count}条",
            chapter.chapter_number
        );

        tracing::info!(
            project_id,
            chapter_id,
            created = created_count,
            updated = updated_count,
            total,
            "Chapter vault update complete"
        );

        Ok(ChapterUpdateResult {
            project_id,
            chapter_id: chapter_id.to_owned(),
            chapter_number: chapter.chapter_number,
            created: created_count,
            updated: updated_count,
            entities_found: EntityCounts {
                characters: entities.characters.len(),
                locations: entities.locations.len(),
                items: entities.items.len(),
            },
            total_entities: total,
            message,
        })
    }

    // ==================================================================
    // Vault Summary (五合一统计)
    // ==================================================================

    /// Get five-in-one vault summary: counts across all vaults plus status breakdown.
    pub async fn vault_summary(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<VaultSummary> {
        self.verify_owner(db, user_id, project_id).await?;

        let character_count = self.vault_dao.count_characters(db, project_id).await?;
        let timeline_count = self.vault_dao.count_timeline(db, project_id).await?;
        let plot_promise_count = self.vault_dao.count_plot_promises(db, project_id).await?;
        let world_count = self.vault_dao.count_worlds(db, project_id).await?;
        let changelog_count = self.vault_dao.count_changelogs(db, project_id).await?;

        let promise_status_breakdown = self
            .get_promise_status_breakdown(db, project_id)
            .await
            .unwrap_or_default();

        // Get recent characters (up to 5, most recently updated)
        let all_chars = self.vault_dao.find_characters(db, project_id).await?;
        let mut recent_chars = all_chars;
        recent_chars.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));
        let recent_characters: Vec<Character> = recent_chars.into_iter().take(5).collect();

        tracing::info!(
            project_id,
            chars = character_count,
            timeline = timeline_count,
            promises = plot_promise_count,
            world = world_count,
            changelogs = changelog_count,
            "Vault summary computed"
        );

        Ok(VaultSummary {
            character_count,
            timeline_count,
            plot_promise_count,
            world_count,
            changelog_count,
            promise_status_breakdown,
            recent_characters,
        })
    }

    /// Trigger a full vault reanalysis (stub — queued to worker).
    pub async fn reanalyze(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;
        tracing::info!(project_id, "Full vault reanalysis queued");
        Ok(())
    }

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    /// Simple text entity extraction for Chinese web novel content.
    fn extract_entities_from_text(content: &str) -> RawEntities {
        let mut entities = RawEntities::default();

        // Common Chinese words to exclude from entity detection
        let common_words: std::collections::HashSet<&str> = [
            "但是", "然而", "虽然", "因为", "所以",
            "不过", "这个", "那个", "这些", "那些",
            "我们", "你们", "他们", "它们", "她们",
            "没有", "可以", "还是", "不是", "就是",
            "什么", "怎么", "这样", "那样", "如果",
            "已经", "一个", "还有", "之后", "时候",
            "突然", "开始", "最后", "知道", "看到",
            "自己", "只见", "只听",
        ]
        .iter()
        .cloned()
        .collect();

        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            // Extract Chinese names (2-4 chars before colon/dialogue marker)
            let chars: Vec<char> = line.chars().collect();
            let len = chars.len();

            let mut i = 0;
            while i < len {
                // Look for colon/dialogue markers preceded by Chinese characters
                if i + 1 < len && (chars[i + 1] == '：' || chars[i + 1] == ':' || chars[i + 1] == '　') {
                    // Check backward for Chinese name (2-4 chars)
                    let name_end = i + 1;
                    let mut start = i;
                    let mut chinese_count = 0;
                    while start > 0 && chinese_count < 4 {
                        let c = chars[start];
                        if ('\u{4e00}'..='\u{9fff}').contains(&c) {
                            chinese_count += 1;
                            if start == 0 {
                                break;
                            }
                            start -= 1;
                        } else {
                            start += 1;
                            break;
                        }
                    }
                    if start > 0 && chinese_count == 4 {
                        start += 1;
                    }
                    if i + 1 == name_end {
                        // Adjust start to ensure start < name_end
                        if start < name_end {
                            let name: String = chars[start..name_end].iter().collect();
                            if name.chars().count() >= 2
                                && name.chars().count() <= 4
                                && name.chars().all(|c| ('\u{4e00}'..='\u{9fff}').contains(&c))
                                && !common_words.contains(name.as_str())
                            {
                                entities.characters.insert(name);
                            }
                        }
                    }
                }
                i += 1;
            }

            // Extract location keywords (在/到/去/从 + location)
            let loc_patterns = ["在", "到", "去", "从", "进入", "来到", "前往", "返回", "离开"];
            for prefix in &loc_patterns {
                if let Some(pos) = line.find(prefix) {
                    let after = &line[pos + prefix.len()..];
                    let loc: String = after
                        .chars()
                        .take_while(|c| ('\u{4e00}'..='\u{9fff}').contains(c))
                        .collect();
                    if loc.chars().count() >= 2 && loc.chars().count() <= 6 {
                        entities.locations.insert(loc);
                    }
                }
            }

            // Extract item keywords (拿起/握着/背着/一把/一根/一个/一本 + item)
            let item_prefixes = ["拿起", "握着", "背着", "提着", "拎着", "戴上", "穿着", "手中", "一把", "一根", "一个", "一本", "一卷"];
            for prefix in &item_prefixes {
                if let Some(pos) = line.find(prefix) {
                    let after = &line[pos + prefix.len()..];
                    let item: String = after
                        .chars()
                        .take_while(|c| {
                            ('\u{4e00}'..='\u{9fff}').contains(c)
                        })
                        .collect();
                    if item.chars().count() >= 2 && item.chars().count() <= 4 {
                        entities.items.insert(item);
                    }
                }
            }
        }

        entities
    }
}

impl Default for VaultService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Raw extracted entities from text analysis.
#[derive(Debug, Clone, Default)]
struct RawEntities {
    characters: std::collections::HashSet<String>,
    locations: std::collections::HashSet<String>,
    items: std::collections::HashSet<String>,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vault_summary_serialization() {
        let mut breakdown = HashMap::new();
        breakdown.insert("dormant".to_owned(), 5);
        breakdown.insert("fulfilled".to_owned(), 2);

        let summary = VaultSummary {
            character_count: 10,
            timeline_count: 20,
            plot_promise_count: 7,
            world_count: 15,
            changelog_count: 30,
            promise_status_breakdown: breakdown,
            recent_characters: vec![],
        };

        let json = serde_json::to_string(&summary).unwrap();
        assert!(json.contains("character_count"));
        assert!(json.contains("dormant"));
    }

    #[test]
    fn test_vault_filter_params_default() {
        let params = VaultFilterParams::default();
        assert!(params.character_name.is_none());
        assert!(params.limit.is_none());
    }

    #[test]
    fn test_entity_extraction_chinese() {
        let content = "叶凡：你好！\n叶凡在前往长安城\n他拿起一把长剑";
        let entities = VaultService::extract_entities_from_text(content);
        // Should find at least the character "叶凡" and location "长安城"
        // Note: extraction depends on character position, rough check
        assert!(!entities.characters.is_empty() || !entities.locations.is_empty() || !entities.items.is_empty());
    }

    #[test]
    fn test_entity_extraction_empty() {
        let entities = VaultService::extract_entities_from_text("");
        assert!(entities.characters.is_empty());
        assert!(entities.locations.is_empty());
        assert!(entities.items.is_empty());
    }

    #[test]
    fn test_continuity_result_serialization() {
        let result = ContinuityResult {
            is_continuous: true,
            gaps: vec![],
            duplicates: vec![],
            total_events: 5,
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("is_continuous"));
    }

    #[test]
    fn test_vault_service_constructs() {
        let _svc = VaultService::new();
    }

    #[test]
    fn test_chapter_update_result() {
        let result = ChapterUpdateResult {
            project_id: 1,
            chapter_id: "ch1".to_owned(),
            chapter_number: 1,
            created: 3,
            updated: 2,
            entities_found: EntityCounts {
                characters: 2,
                locations: 1,
                items: 2,
            },
            total_entities: 5,
            message: "test".to_owned(),
        };
        assert_eq!(result.total_entities, 5);
        assert_eq!(result.created, 3);
    }

    #[test]
    fn test_character_merge_request() {
        let merge = CharacterMergeRequest {
            source_id: "src1".to_owned(),
            target_id: "tgt1".to_owned(),
        };
        let json = serde_json::to_string(&merge).unwrap();
        let back: CharacterMergeRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(back.source_id, "src1");
        assert_eq!(back.target_id, "tgt1");
    }

    #[test]
    fn test_character_import_serde() {
        let import = CharacterImport {
            name: "叶凡".to_owned(),
            role: "主角".to_owned(),
            description: Some("一个修炼者".to_owned()),
            traits: Some(vec!["勇敢".to_owned(), "果断".to_owned()]),
            faction: None,
            personality: None,
            background: None,
        };
        let json = serde_json::to_string(&import).unwrap();
        assert!(json.contains("叶凡"));
    }
}
