//! System Config DAO — key-value configuration with versioned audit trail.
//!
//! Every update increments a version column (optimistic lock) and an
//! append-only audit log records who changed what when.

use moling_core::error::{AppError, AppResult};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, IntoActiveModel,
    QueryFilter, QueryOrder, QuerySelect, Set,
};

use crate::entities::system_config::{
    self, ActiveModel, Entity as SystemConfig,
    Model as SystemConfigModel,
};
use crate::entities::system_config_audit::{
    self as audit_entity, ActiveModel as AuditActiveModel,
    Entity as SystemConfigAudit,
};

/// System config data access object.
#[derive(Clone, Default)]
pub struct SystemConfigDao;

impl SystemConfigDao {
    // ── KV CRUD ──────────────────────────────────────────────────────────

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

    // ── Versioned Upsert (optimistic lock) ───────────────────────────────

    /// Insert or update a config entry with version increment.
    ///
    /// If `expected_version` is provided, the write is rejected when the
    /// database version does not match — this is the optimistic lock.
    pub async fn upsert_versioned(
        &self,
        db: &DatabaseConnection,
        key: &str,
        value: &str,
        description: &str,
        expected_version: Option<i32>,
        operator: Option<&str>,
    ) -> AppResult<SystemConfigModel> {
        if let Some(existing) = self.find_by_key(db, key).await? {
            // Version check (optimistic lock)
            if let Some(expected) = expected_version
                && existing.version != expected
            {
                return Err(AppError::conflict(format!(
                    "配置 '{key}' 已被他人修改 (期望 v{expected}, 当前 v{})",
                    existing.version
                )));
            }

            let new_version = existing.version + 1;
            let old_value = existing.value.clone();
            let mut active = existing.into_active_model();
            active.value = Set(value.to_owned());
            active.version = Set(new_version);
            if !description.is_empty() {
                active.description = Set(Some(description.to_owned()));
            }

            let updated = active.update(db).await.map_err(|e| {
                tracing::error!(%key, "SystemConfig: database error updating: {e}");
                AppError::internal("Database update failed")
            })?;

            // Write audit log
            self.write_audit(db, key, new_version, Some(&old_value), value, operator)
                .await?;

            Ok(updated)
        } else {
            let model = ActiveModel {
                key: Set(key.to_owned()),
                value: Set(value.to_owned()),
                version: Set(1),
                description: Set(if description.is_empty() {
                    None
                } else {
                    Some(description.to_owned())
                }),
                ..Default::default()
            };
            let inserted = model.insert(db).await.map_err(|e| {
                tracing::error!(%key, "SystemConfig: database error inserting: {e}");
                AppError::internal("Database insert failed")
            })?;

            self.write_audit(db, key, 1, None, value, operator).await?;

            Ok(inserted)
        }
    }

    /// Simple upsert without version check (backward compat).
    pub async fn upsert(
        &self,
        db: &DatabaseConnection,
        key: &str,
        value: &str,
        description: &str,
    ) -> AppResult<SystemConfigModel> {
        self.upsert_versioned(db, key, value, description, None, Some("api"))
            .await
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

    // ── Audit Log ────────────────────────────────────────────────────────

    /// Write an audit entry.
    pub async fn write_audit(
        &self,
        db: &DatabaseConnection,
        config_key: &str,
        version: i32,
        old_value: Option<&str>,
        new_value: &str,
        operator: Option<&str>,
    ) -> AppResult<()> {
        let entry = AuditActiveModel {
            config_key: Set(config_key.to_owned()),
            version: Set(version),
            old_value: Set(old_value.map(|s| s.to_owned())),
            new_value: Set(new_value.to_owned()),
            changed_by: Set(operator.map(|s| s.to_owned())),
            ..Default::default()
        };
        entry.insert(db).await.map_err(|e| {
            tracing::error!(%config_key, "SystemConfig: audit log write error: {e}");
            AppError::internal("Audit log write failed")
        })?;
        Ok(())
    }

    /// Query audit log for a config key, newest first.
    pub async fn get_audit_log(
        &self,
        db: &DatabaseConnection,
        config_key: &str,
        limit: u64,
    ) -> AppResult<Vec<crate::entities::system_config_audit::Model>> {
        SystemConfigAudit::find()
            .filter(audit_entity::Column::ConfigKey.eq(config_key.to_owned()))
            .order_by_desc(audit_entity::Column::ChangedAt)
            .limit(Some(limit))
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%config_key, "SystemConfig: audit log query error: {e}");
                AppError::internal("Audit log query failed")
            })
    }
}
