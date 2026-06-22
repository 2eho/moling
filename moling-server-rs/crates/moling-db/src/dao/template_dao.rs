//! Template DAO — template CRUD with genre-based queries.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::template::{self, ActiveModel, Entity as Template, Model as TemplateModel};

/// Template data access object.
#[derive(Clone, Default)]
pub struct TemplateDao;

impl TemplateDao {
    /// Find a template by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<TemplateModel>> {
        Template::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Template: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List templates by genre with pagination.
    pub async fn list_by_genre(
        &self,
        db: &DatabaseConnection,
        genre: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<TemplateModel>> {
        Template::find()
            .filter(template::Column::Genre.eq(genre))
            .order_by_desc(template::Column::CreatedAt)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(%genre, "Template: database error listing by genre: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count templates by genre.
    pub async fn count_by_genre(
        &self,
        db: &DatabaseConnection,
        genre: &str,
    ) -> AppResult<u64> {
        Template::find()
            .filter(template::Column::Genre.eq(genre))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(%genre, "Template: database error counting by genre: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new template.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<TemplateModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Template: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing template.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<TemplateModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Template: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Hard-delete a template.
    pub async fn delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<u64> {
        let result = Template::delete_by_id(id.to_owned())
            .exec(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Template: database error deleting: {e}");
                AppError::internal("Database delete failed")
            })?;
        Ok(result.rows_affected)
    }
}
