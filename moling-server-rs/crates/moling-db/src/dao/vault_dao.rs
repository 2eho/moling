//! Vault DAO — four-vault CRUD, summary, and health-check operations.
//!
//! Handles: characters, timelines, plot promises, worlds, and changelogs.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, IntoActiveModel, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect, Set};

use crate::entities::{
    vault_character::{self, Entity as VaultCharacter, Model as VaultCharacterModel},
    vault_changelog::{self, Entity as VaultChangelog, Model as VaultChangelogModel},
    vault_plot_promise::{self, Entity as VaultPlotPromise, Model as VaultPlotPromiseModel},
    vault_timeline::{self, Entity as VaultTimeline, Model as VaultTimelineModel},
    vault_world::{self, Entity as VaultWorld, Model as VaultWorldModel},
};

/// Unified summary of vault contents for a project.
#[derive(Debug, Clone, serde::Serialize)]
pub struct VaultSummary {
    pub character_count: u64,
    pub timeline_count: u64,
    pub plot_promise_count: u64,
    pub world_count: u64,
    pub changelog_count: u64,
}

/// Unified Vault Data Access Object — covers all four vaults plus changelogs.
#[derive(Clone, Default)]
pub struct VaultDao;

// =========================================================================
// Characters
// =========================================================================

impl VaultDao {
    pub async fn find_characters(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<VaultCharacterModel>> {
        VaultCharacter::find()
            .filter(vault_character::Column::ProjectId.eq(project_id))
            .filter(vault_character::Column::IsDeleted.eq(false))
            .order_by_asc(vault_character::Column::Name)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: database error listing characters: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_character_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<VaultCharacterModel>> {
        VaultCharacter::find_by_id(id.to_owned())
            .filter(vault_character::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Vault: database error finding character: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a character by name within a project.
    pub async fn find_character_by_name(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        name: &str,
    ) -> AppResult<Option<VaultCharacterModel>> {
        VaultCharacter::find()
            .filter(vault_character::Column::ProjectId.eq(project_id))
            .filter(vault_character::Column::Name.eq(name))
            .filter(vault_character::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %name, "Vault: database error finding character by name: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Batch fetch characters by their IDs within a project.
    pub async fn find_characters_by_ids(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        ids: &[String],
    ) -> AppResult<Vec<VaultCharacterModel>> {
        if ids.is_empty() {
            return Ok(Vec::new());
        }
        VaultCharacter::find()
            .filter(vault_character::Column::ProjectId.eq(project_id))
            .filter(vault_character::Column::Id.is_in(ids.to_vec()))
            .filter(vault_character::Column::IsDeleted.eq(false))
            .order_by_asc(vault_character::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: database error fetching characters by ids: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_character(
        &self,
        db: &DatabaseConnection,
        model: vault_character::ActiveModel,
    ) -> AppResult<VaultCharacterModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Vault: database error creating character: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn update_character(
        &self,
        db: &DatabaseConnection,
        model: vault_character::ActiveModel,
    ) -> AppResult<VaultCharacterModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Vault: database error updating character: {e}");
            AppError::internal("Database update failed")
        })
    }

    pub async fn soft_delete_character(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<()> {
        use chrono::Utc;
        let entity = self.find_character_by_id(db, id).await?;
        let Some(entity) = entity else {
            return Err(AppError::vault_entry_not_found());
        };
        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Vault: database error soft-deleting character: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    pub async fn count_characters(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        VaultCharacter::find()
            .filter(vault_character::Column::ProjectId.eq(project_id))
            .filter(vault_character::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error counting characters: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count characters filtered by status.
    pub async fn count_characters_by_status(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        status: &str,
    ) -> AppResult<u64> {
        VaultCharacter::find()
            .filter(vault_character::Column::ProjectId.eq(project_id))
            .filter(vault_character::Column::Status.eq(status))
            .filter(vault_character::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %status, "Vault: error counting characters by status: {e}");
                AppError::internal("Database query failed")
            })
    }
}

// =========================================================================
// Timeline
// =========================================================================

impl VaultDao {
    pub async fn find_timeline_events(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<VaultTimelineModel>> {
        VaultTimeline::find()
            .filter(vault_timeline::Column::ProjectId.eq(project_id))
            .filter(vault_timeline::Column::IsDeleted.eq(false))
            .order_by_asc(vault_timeline::Column::ChapterNumber)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error listing timeline: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_timeline_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<VaultTimelineModel>> {
        VaultTimeline::find_by_id(id.to_owned())
            .filter(vault_timeline::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Vault: error finding timeline event: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_timeline(
        &self,
        db: &DatabaseConnection,
        model: vault_timeline::ActiveModel,
    ) -> AppResult<VaultTimelineModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Vault: error creating timeline: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn update_timeline(
        &self,
        db: &DatabaseConnection,
        model: vault_timeline::ActiveModel,
    ) -> AppResult<VaultTimelineModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Vault: error updating timeline: {e}");
            AppError::internal("Database update failed")
        })
    }

    pub async fn soft_delete_timeline(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use chrono::Utc;
        let entity = self.find_timeline_by_id(db, id).await?;
        let Some(entity) = entity else {
            return Err(AppError::vault_entry_not_found());
        };
        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Vault: error soft-deleting timeline: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    pub async fn count_timeline(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        VaultTimeline::find()
            .filter(vault_timeline::Column::ProjectId.eq(project_id))
            .filter(vault_timeline::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error counting timeline: {e}");
                AppError::internal("Database query failed")
            })
    }
}

// =========================================================================
// Plot Promises
// =========================================================================

impl VaultDao {
    pub async fn find_plot_promises(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<VaultPlotPromiseModel>> {
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .order_by_desc(vault_plot_promise::Column::Urgency)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error listing plot promises: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_plot_promise_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<VaultPlotPromiseModel>> {
        VaultPlotPromise::find_by_id(id.to_owned())
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Vault: error finding plot promise: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Batch fetch plot promises by their IDs within a project.
    pub async fn find_plot_promises_by_ids(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        ids: &[String],
    ) -> AppResult<Vec<VaultPlotPromiseModel>> {
        if ids.is_empty() {
            return Ok(Vec::new());
        }
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::Id.is_in(ids.to_vec()))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .order_by_asc(vault_plot_promise::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error fetching promises by ids: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a plot promise by a fragment of its description.
    pub async fn find_promise_by_description(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        fragment: &str,
    ) -> AppResult<Option<VaultPlotPromiseModel>> {
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::Description.contains(fragment))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error finding promise by description: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a plot promise by type, related character, and statuses.
    pub async fn find_promise_by_type_and_char(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        promise_type: &str,
        char_name: &str,
        statuses: &[String],
    ) -> AppResult<Option<VaultPlotPromiseModel>> {
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::Type.eq(promise_type))
            .filter(vault_plot_promise::Column::RelatedCharacters.is_not_null())
            .filter(vault_plot_promise::Column::Status.is_in(statuses.to_vec()))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %promise_type, %char_name, "Vault: error finding promise by type and char: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_plot_promise(
        &self,
        db: &DatabaseConnection,
        model: vault_plot_promise::ActiveModel,
    ) -> AppResult<VaultPlotPromiseModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Vault: error creating plot promise: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn update_plot_promise(
        &self,
        db: &DatabaseConnection,
        model: vault_plot_promise::ActiveModel,
    ) -> AppResult<VaultPlotPromiseModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Vault: error updating plot promise: {e}");
            AppError::internal("Database update failed")
        })
    }

    pub async fn soft_delete_plot_promise(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<()> {
        use chrono::Utc;
        let entity = self.find_plot_promise_by_id(db, id).await?;
        let Some(entity) = entity else {
            return Err(AppError::vault_entry_not_found());
        };
        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Vault: error soft-deleting plot promise: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    pub async fn count_plot_promises(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error counting plot promises: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count plot promises filtered by status.
    pub async fn count_plot_promises_by_status(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        status: &str,
    ) -> AppResult<u64> {
        VaultPlotPromise::find()
            .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
            .filter(vault_plot_promise::Column::Status.eq(status))
            .filter(vault_plot_promise::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %status, "Vault: error counting promises by status: {e}");
                AppError::internal("Database query failed")
            })
    }
}

// =========================================================================
// Worlds
// =========================================================================

impl VaultDao {
    pub async fn find_world_entries(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<VaultWorldModel>> {
        VaultWorld::find()
            .filter(vault_world::Column::ProjectId.eq(project_id))
            .filter(vault_world::Column::IsDeleted.eq(false))
            .order_by_asc(vault_world::Column::Category)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error listing world entries: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_world_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<VaultWorldModel>> {
        VaultWorld::find_by_id(id.to_owned())
            .filter(vault_world::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Vault: error finding world entry: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a world entry by its term/name within a project.
    pub async fn find_world_by_term(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        term: &str,
    ) -> AppResult<Option<VaultWorldModel>> {
        VaultWorld::find()
            .filter(vault_world::Column::ProjectId.eq(project_id))
            .filter(vault_world::Column::Name.eq(term))
            .filter(vault_world::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %term, "Vault: error finding world by term: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Batch fetch world entries by their IDs within a project.
    pub async fn find_worlds_by_ids(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        ids: &[String],
    ) -> AppResult<Vec<VaultWorldModel>> {
        if ids.is_empty() {
            return Ok(Vec::new());
        }
        VaultWorld::find()
            .filter(vault_world::Column::ProjectId.eq(project_id))
            .filter(vault_world::Column::Id.is_in(ids.to_vec()))
            .filter(vault_world::Column::IsDeleted.eq(false))
            .order_by_asc(vault_world::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error fetching worlds by ids: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_world(
        &self,
        db: &DatabaseConnection,
        model: vault_world::ActiveModel,
    ) -> AppResult<VaultWorldModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Vault: error creating world entry: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn update_world(
        &self,
        db: &DatabaseConnection,
        model: vault_world::ActiveModel,
    ) -> AppResult<VaultWorldModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Vault: error updating world entry: {e}");
            AppError::internal("Database update failed")
        })
    }

    pub async fn soft_delete_world(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use chrono::Utc;
        let entity = self.find_world_by_id(db, id).await?;
        let Some(entity) = entity else {
            return Err(AppError::vault_entry_not_found());
        };
        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Vault: error soft-deleting world entry: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    pub async fn count_worlds(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        VaultWorld::find()
            .filter(vault_world::Column::ProjectId.eq(project_id))
            .filter(vault_world::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error counting world entries: {e}");
                AppError::internal("Database query failed")
            })
    }
}

// =========================================================================
// Changelogs
// =========================================================================

impl VaultDao {
    pub async fn find_changelogs(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<VaultChangelogModel>> {
        VaultChangelog::find()
            .filter(vault_changelog::Column::ProjectId.eq(project_id))
            .order_by_desc(vault_changelog::Column::CreatedAt)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error listing changelogs: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_changelog_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<VaultChangelogModel>> {
        VaultChangelog::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Vault: error finding changelog: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_changelog(
        &self,
        db: &DatabaseConnection,
        model: vault_changelog::ActiveModel,
    ) -> AppResult<VaultChangelogModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Vault: error creating changelog: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn count_changelogs(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        VaultChangelog::find()
            .filter(vault_changelog::Column::ProjectId.eq(project_id))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Vault: error counting changelogs: {e}");
                AppError::internal("Database query failed")
            })
    }
}

// =========================================================================
// Summary & Health Check
// =========================================================================

impl VaultDao {
    /// Combined summary counts for all four vault entities + changelogs.
    pub async fn summary(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<VaultSummary> {
        let (character_count, timeline_count, plot_promise_count, world_count, changelog_count) = tokio::try_join!(
            self.count_characters(db, project_id),
            self.count_timeline(db, project_id),
            self.count_plot_promises(db, project_id),
            self.count_worlds(db, project_id),
            self.count_changelogs(db, project_id),
        )
        .map_err(|e| {
            tracing::error!(project_id, "Vault: error computing summary: {e}");
            AppError::internal("Database query failed")
        })?;

        Ok(VaultSummary {
            character_count,
            timeline_count,
            plot_promise_count,
            world_count,
            changelog_count,
        })
    }

    /// Simple health check — verifies all four vault tables are reachable.
    pub async fn health_check(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<bool> {
        // Query one row from each vault table to verify reachability.
        let results = tokio::try_join!(
            VaultCharacter::find()
                .filter(vault_character::Column::ProjectId.eq(project_id))
                .limit(1)
                .count(db),
            VaultTimeline::find()
                .filter(vault_timeline::Column::ProjectId.eq(project_id))
                .limit(1)
                .count(db),
            VaultPlotPromise::find()
                .filter(vault_plot_promise::Column::ProjectId.eq(project_id))
                .limit(1)
                .count(db),
            VaultWorld::find()
                .filter(vault_world::Column::ProjectId.eq(project_id))
                .limit(1)
                .count(db),
        );

        match results {
            Ok(_) => Ok(true),
            Err(e) => {
                tracing::error!(project_id, "Vault: health check failed: {e}");
                Ok(false)
            }
        }
    }
}
