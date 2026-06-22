//! System Config DAO — key-value configuration store with upsert support.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, Set};

use crate::entities::system_config::{self, ActiveModel, Entity as SystemConfig, Model as SystemConfigModel};

/// System config data access object.
#[derive(Clone, Default)]
pub struct SystemConfigDao;

impl SystemConfigDao {
    /// Retrieve a config entry by its key.
    pub async fn find_by_key(
        &self,
        db: &DatabaseConnection,
        key: &str,
    ) -> AppResult<Option<SystemConfigModel>> {
        SystemConfig::find_by_id(key.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%key, "SystemConfig: database error finding by key: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Retrieve multiple config entries by their keys.
    /// Returns a HashMap keyed by the SystemConfig key.
    pub async fn find_by_keys(
        &self,
        db: &DatabaseConnection,
        keys: &[String],
    ) -> AppResult<std::collections::HashMap<String, SystemConfigModel>> {
        if keys.is_empty() {
            return Ok(std::collections::HashMap::new());
        }
        let rows = SystemConfig::find()
            .filter(system_config::Column::Key.is_in(keys.to_vec()))
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!("SystemConfig: database error finding by keys: {e}");
                AppError::internal("Database query failed")
            })?;
        let mut map = std::collections::HashMap::with_capacity(rows.len());
        for row in rows {
            map.insert(row.key.clone(), row);
        }
        Ok(map)
    }

    /// Insert or update a config entry. Returns the inserted/updated model.
    pub async fn upsert(
        &self,
        db: &DatabaseConnection,
        key: &str,
        value: &str,
        description: &str,
    ) -> AppResult<SystemConfigModel> {
        if let Some(existing) = self.find_by_key(db, key).await? {
            // Update existing entry.
            use sea_orm::IntoActiveModel;
            let mut active = existing.into_active_model();
            active.value = Set(value.to_owned());
            if !description.is_empty() {
                active.description = Set(Some(description.to_owned()));
            }
            active.update(db).await.map_err(|e| {
                tracing::error!(%key, "SystemConfig: database error updating: {e}");
                AppError::internal("Database update failed")
            })
        } else {
            // Insert new entry.
            let model = ActiveModel {
                key: Set(key.to_owned()),
                value: Set(value.to_owned()),
                description: Set(if description.is_empty() {
                    None
                } else {
                    Some(description.to_owned())
                }),
                ..Default::default()
            };
            model.insert(db).await.map_err(|e| {
                tracing::error!(%key, "SystemConfig: database error inserting: {e}");
                AppError::internal("Database insert failed")
            })
        }
    }

    /// Insert or update multiple config entries at once.
    pub async fn upsert_batch(
        &self,
        db: &DatabaseConnection,
        configs: &std::collections::HashMap<String, String>,
        description: &str,
    ) -> AppResult<()> {
        for (key, value) in configs {
            self.upsert(db, key, value, description).await?;
        }
        Ok(())
    }
}
