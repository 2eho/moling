//! Phase4 DAO — Phase 4 task CRUD with idempotency support.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::phase4_task::{self, ActiveModel, Entity as Phase4Task, Model as Phase4TaskModel};

/// Phase 4 task data access object.
#[derive(Clone, Default)]
pub struct Phase4Dao;

impl Phase4Dao {
    /// Find a task by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: i32,
    ) -> AppResult<Option<Phase4TaskModel>> {
        Phase4Task::find_by_id(id)
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Phase4: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a task by nonce (for idempotency check).
    pub async fn find_by_nonce(
        &self,
        db: &DatabaseConnection,
        nonce: &str,
    ) -> AppResult<Option<Phase4TaskModel>> {
        Phase4Task::find()
            .filter(phase4_task::Column::Nonce.eq(nonce))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%nonce, "Phase4: database error finding by nonce: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List tasks by chapter ID, optionally filtered by state.
    pub async fn list_by_chapter(
        &self,
        db: &DatabaseConnection,
        chapter_id: &str,
        state: Option<&str>,
    ) -> AppResult<Vec<Phase4TaskModel>> {
        let mut query = Phase4Task::find()
            .filter(phase4_task::Column::ChapterId.eq(chapter_id));

        if let Some(s) = state {
            query = query.filter(phase4_task::Column::State.eq(s));
        }

        query
            .order_by_desc(phase4_task::Column::CreatedAt)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%chapter_id, "Phase4: database error listing by chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List tasks by project ID, optionally filtered by state.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        state: Option<&str>,
    ) -> AppResult<Vec<Phase4TaskModel>> {
        let mut query = Phase4Task::find()
            .filter(phase4_task::Column::ProjectId.eq(project_id));

        if let Some(s) = state {
            query = query.filter(phase4_task::Column::State.eq(s));
        }

        query
            .order_by_desc(phase4_task::Column::CreatedAt)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%project_id, "Phase4: database error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List tasks by status with pagination.
    pub async fn list_by_status(
        &self,
        db: &DatabaseConnection,
        status: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<Phase4TaskModel>> {
        Phase4Task::find()
            .filter(phase4_task::Column::State.eq(status))
            .order_by_desc(phase4_task::Column::CreatedAt)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%status, "Phase4: database error listing by status: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count tasks matching a given state.
    pub async fn count_by_status(
        &self,
        db: &DatabaseConnection,
        status: &str,
    ) -> AppResult<u64> {
        Phase4Task::find()
            .filter(phase4_task::Column::State.eq(status))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(%status, "Phase4: database error counting by status: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new phase 4 task.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<Phase4TaskModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Phase4: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing phase 4 task.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<Phase4TaskModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Phase4: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }
}
