//! Generation DAO — generation task CRUD and status-based queries.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, QuerySelect};
use uuid::Uuid;

use crate::entities::generation_task::{self, ActiveModel, Entity as GenerationTask, Model as GenerationTaskModel};

/// Generation task data access object.
#[derive(Clone, Default)]
pub struct GenerationDao;

impl GenerationDao {
    /// Find a generation task by ID (UUID string).
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<GenerationTaskModel>> {
        let uuid = Uuid::parse_str(id).map_err(|e| {
            tracing::warn!(%id, "Generation: invalid UUID format: {e}");
            AppError::bad_request("Invalid task ID format")
        })?;
        GenerationTask::find_by_id(uuid)
            .filter(generation_task::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Generation: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List generation tasks for a project, newest first, with pagination.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<GenerationTaskModel>> {
        GenerationTask::find()
            .filter(generation_task::Column::ProjectId.eq(project_id))
            .filter(generation_task::Column::IsDeleted.eq(false))
            .order_by_desc(generation_task::Column::CreatedAt)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Generation: database error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List generation tasks for a specific chapter.
    pub async fn list_by_chapter(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<Vec<GenerationTaskModel>> {
        GenerationTask::find()
            .filter(generation_task::Column::ProjectId.eq(project_id))
            .filter(generation_task::Column::ChapterId.eq(chapter_id))
            .filter(generation_task::Column::IsDeleted.eq(false))
            .order_by_desc(generation_task::Column::CreatedAt)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %chapter_id, "Generation: database error listing by chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List generation tasks with a specific status (for worker polling).
    pub async fn list_by_status(
        &self,
        db: &DatabaseConnection,
        status: &str,
        limit: u64,
    ) -> AppResult<Vec<GenerationTaskModel>> {
        GenerationTask::find()
            .filter(generation_task::Column::Status.eq(status))
            .filter(generation_task::Column::IsDeleted.eq(false))
            .order_by_asc(generation_task::Column::CreatedAt)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%status, "Generation: database error listing by status: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get the latest generation task for a chapter with a specific type.
    pub async fn find_by_chapter_and_type(
        &self,
        db: &DatabaseConnection,
        chapter_id: &str,
        task_type: &str,
    ) -> AppResult<Option<GenerationTaskModel>> {
        GenerationTask::find()
            .filter(generation_task::Column::ChapterId.eq(chapter_id))
            .filter(generation_task::Column::TaskType.eq(task_type))
            .filter(generation_task::Column::IsDeleted.eq(false))
            .order_by_desc(generation_task::Column::CreatedAt)
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%chapter_id, %task_type, "Generation: database error finding by chapter and type: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new generation task.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<GenerationTaskModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Generation: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing generation task.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<GenerationTaskModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Generation: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Soft-delete a generation task.
    pub async fn soft_delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use sea_orm::{IntoActiveModel, Set};
        use chrono::Utc;

        let entity = self.find_by_id(db, id).await?.ok_or_else(|| {
            AppError::generation_task_not_found()
        })?;

        let mut active = entity.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now().into()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Generation: database error soft-deleting: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }
}
