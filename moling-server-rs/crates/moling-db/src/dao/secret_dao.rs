//! Secret DAO — secret (秘密矩阵) CRUD and batch operations.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect, Set};

use crate::entities::secret::{self, ActiveModel, Entity as Secret, Model as SecretModel};

/// Secret data access object.
#[derive(Clone, Default)]
pub struct SecretDao;

impl SecretDao {
    /// Find a single secret by primary key.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<SecretModel>> {
        Secret::find_by_id(id.to_owned())
            .filter(secret::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Secret: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all secrets for a project, ordered by id ascending.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<SecretModel>> {
        Secret::find()
            .filter(secret::Column::ProjectId.eq(project_id))
            .filter(secret::Column::IsDeleted.eq(false))
            .order_by_asc(secret::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Secret: database error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List secrets filtered by secrecy_level (hidden / partial / revealed).
    pub async fn list_by_secrecy_level(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        level: &str,
    ) -> AppResult<Vec<SecretModel>> {
        Secret::find()
            .filter(secret::Column::ProjectId.eq(project_id))
            .filter(secret::Column::SecrecyLevel.eq(level))
            .filter(secret::Column::IsDeleted.eq(false))
            .order_by_asc(secret::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %level, "Secret: database error listing by level: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new secret.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<SecretModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Secret: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing secret.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<SecretModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Secret: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Soft-delete a secret.
    pub async fn soft_delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use sea_orm::IntoActiveModel;
        use chrono::Utc;

        let entity = self.find_by_id(db, id).await?.ok_or_else(|| {
            AppError::not_found("秘密不存在")
        })?;

        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Secret: database error soft-deleting: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Batch create secrets, returning the created models.
    pub async fn batch_create(
        &self,
        db: &DatabaseConnection,
        models: Vec<ActiveModel>,
    ) -> AppResult<Vec<SecretModel>> {
        let mut results = Vec::with_capacity(models.len());
        for model in models {
            let created = model.insert(db).await.map_err(|e| {
                tracing::error!("Secret: database error batch creating: {e}");
                AppError::internal("Database insert failed")
            })?;
            results.push(created);
        }
        Ok(results)
    }

    /// Batch update secrets. Each model must have its primary key set.
    /// Returns the total number of rows updated.
    pub async fn batch_update(
        &self,
        db: &DatabaseConnection,
        updates: Vec<ActiveModel>,
    ) -> AppResult<u64> {
        let mut total: u64 = 0;
        for model in updates {
            model.update(db).await.map_err(|e| {
                tracing::error!("Secret: database error batch updating: {e}");
                AppError::internal("Database update failed")
            })?;
            total += 1;
        }
        Ok(total)
    }

    /// Sum the debt of all non-deleted secrets in a project.
    pub async fn calculate_debt_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<i32> {
        use sea_orm::entity::*;
        Secret::find()
            .filter(secret::Column::ProjectId.eq(project_id))
            .filter(secret::Column::IsDeleted.eq(false))
            .select_only()
            .column_as(secret::Column::Debt.sum(), "total_debt")
            .into_tuple::<(Option<i32>,)>()
            .one(db)
            .await
            .map(|r| r.and_then(|(v,)| v).unwrap_or(0))
            .map_err(|e| {
                tracing::error!(project_id, "Secret: database error calculating debt: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count non-deleted secrets in a project.
    pub async fn count_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        Secret::find()
            .filter(secret::Column::ProjectId.eq(project_id))
            .filter(secret::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Secret: database error counting: {e}");
                AppError::internal("Database query failed")
            })
    }
}
