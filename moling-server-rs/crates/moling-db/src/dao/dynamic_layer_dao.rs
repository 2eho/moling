//! Dynamic Layer DAO — dynamic context layer CRUD and health-check history.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, QuerySelect};
use sea_orm::prelude::DateTimeUtc;

use crate::entities::dynamic_layer::{self, ActiveModel, Entity as DynamicLayer, Model as DynamicLayerModel};

/// Dynamic layer data access object.
#[derive(Clone, Default)]
pub struct DynamicLayerDao;

impl DynamicLayerDao {
    /// Find a dynamic layer by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<DynamicLayerModel>> {
        DynamicLayer::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "DynamicLayer: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get the dynamic layer for a specific chapter.
    pub async fn find_by_chapter(
        &self,
        db: &DatabaseConnection,
        chapter_id: &str,
    ) -> AppResult<Option<DynamicLayerModel>> {
        DynamicLayer::find()
            .filter(dynamic_layer::Column::ChapterId.eq(chapter_id))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%chapter_id, "DynamicLayer: database error finding by chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get the most recent dynamic layers for a project.
    pub async fn list_recent_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        limit: u64,
    ) -> AppResult<Vec<DynamicLayerModel>> {
        DynamicLayer::find()
            .filter(dynamic_layer::Column::ProjectId.eq(project_id))
            .order_by_desc(dynamic_layer::Column::Id)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "DynamicLayer: database error listing recent: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get the single most recent dynamic layer for a project.
    pub async fn find_latest_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Option<DynamicLayerModel>> {
        let layers = self.list_recent_by_project(db, project_id, 1).await?;
        Ok(layers.into_iter().next())
    }

    /// Get health check history joined with chapter numbers for a project.
    /// Returns tuples of (health_check_json, chapter_number, checked_at).
    pub async fn get_health_check_history(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        limit: u64,
        start_chapter: Option<i32>,
        end_chapter: Option<i32>,
    ) -> AppResult<Vec<(serde_json::Value, i32, DateTimeUtc)>> {
        use crate::entities::chapter;
        use sea_orm::{JoinType, QuerySelect, RelationTrait};

        let mut query = DynamicLayer::find()
            .select_only()
            .column(dynamic_layer::Column::HealthCheck)
            .column_as(chapter::Column::ChapterNumber, "chapter_number")
            .column_as(dynamic_layer::Column::CreatedAt, "checked_at")
            .join_rev(
                JoinType::InnerJoin,
                chapter::Relation::DynamicLayer.def().rev(),
            )
            .filter(dynamic_layer::Column::ProjectId.eq(project_id))
            .filter(dynamic_layer::Column::HealthCheck.is_not_null())
            .order_by_desc(dynamic_layer::Column::CreatedAt)
            .limit(limit);

        if let Some(start) = start_chapter {
            query = query.filter(chapter::Column::ChapterNumber.gte(start));
        }
        if let Some(end) = end_chapter {
            query = query.filter(chapter::Column::ChapterNumber.lt(end));
        }

        query
            .into_tuple::<(serde_json::Value, i32, DateTimeUtc)>()
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "DynamicLayer: database error fetching health check history: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new dynamic layer.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<DynamicLayerModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("DynamicLayer: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing dynamic layer.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<DynamicLayerModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("DynamicLayer: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }
}
