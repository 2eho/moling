//! Ingest DAO — ingest job CRUD and status-based queries.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::ingest_job::{self, ActiveModel, Entity as IngestJob, Model as IngestJobModel};

/// Ingest job data access object.
#[derive(Clone, Default)]
pub struct IngestDao;

impl IngestDao {
    /// Find an ingest job by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<IngestJobModel>> {
        IngestJob::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Ingest: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List ingest jobs for a project, newest first.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<IngestJobModel>> {
        IngestJob::find()
            .filter(ingest_job::Column::ProjectId.eq(project_id))
            .order_by_desc(ingest_job::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Ingest: database error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List ingest jobs by current phase status.
    pub async fn list_by_status(
        &self,
        db: &DatabaseConnection,
        status: &str,
        limit: u64,
    ) -> AppResult<Vec<IngestJobModel>> {
        IngestJob::find()
            .filter(ingest_job::Column::CurrentPhase.eq(status))
            .order_by_desc(ingest_job::Column::Id)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%status, "Ingest: database error listing by status: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new ingest job.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<IngestJobModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Ingest: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing ingest job.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<IngestJobModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Ingest: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }
}
