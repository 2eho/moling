//! Chapter DAO — chapter CRUD with project scoping.

use chrono::Utc;
use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, IntoActiveModel, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect, Set};

use crate::entities::chapter::{self, Entity as Chapter, Model as ChapterModel};

/// Chapter data access object.
#[derive(Clone, Default)]
pub struct ChapterDao;

impl ChapterDao {
    /// Find chapters for a project (paginated, ordered by chapter_number ascending).
    pub async fn find_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<ChapterModel>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false))
            .order_by_asc(chapter::Column::ChapterNumber)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Database error fetching chapters: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List chapters in a project with pagination (offset/limit).
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<ChapterModel>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false))
            .order_by_asc(chapter::Column::ChapterNumber)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Database error listing chapters: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a single chapter by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<ChapterModel>> {
        Chapter::find_by_id(id.to_owned())
            .filter(chapter::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Database error finding chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a chapter by its chapter_number within a project.
    pub async fn find_by_number(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_number: i32,
    ) -> AppResult<Option<ChapterModel>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::ChapterNumber.eq(chapter_number))
            .filter(chapter::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, chapter_number, "Database error finding chapter by number: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get the most recent (highest chapter_number) chapter in a project.
    pub async fn get_current(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Option<ChapterModel>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false))
            .order_by_desc(chapter::Column::ChapterNumber)
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Database error getting current chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get only the content of a chapter by project_id and chapter_number.
    pub async fn find_content_by_number(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_number: i32,
    ) -> AppResult<Option<String>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::ChapterNumber.eq(chapter_number))
            .filter(chapter::Column::IsDeleted.eq(false))
            .select_only()
            .column(chapter::Column::Content)
            .into_tuple::<(Option<String>,)>()
            .one(db)
            .await
            .map(|r| r.and_then(|(content,)| content))
            .map_err(|e| {
                tracing::error!(project_id, chapter_number, "Database error fetching chapter content: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find the highest chapter_number in a project (for auto-increment).
    pub async fn max_chapter_number(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Option<i32>> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false))
            .select_only()
            .column_as(chapter::Column::ChapterNumber.max(), "max_num")
            .into_tuple::<(Option<i32>,)>()
            .one(db)
            .await
            .map(|r| r.and_then(|(v,)| v))
            .map_err(|e| {
                tracing::error!(project_id, "Database error querying max chapter: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Confirm a chapter — set its confirmed_at timestamp and update status.
    pub async fn confirm(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<ChapterModel> {
        let chapter = self
            .find_by_id(db, id)
            .await?
            .ok_or_else(AppError::chapter_not_found)?;

        let mut active = chapter.into_active_model();
        active.confirmed_at = Set(Some(Utc::now().into()));
        active.status = Set("completed".to_owned());
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Database error confirming chapter: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Reorder chapters — update chapter_number for a list of (chapter_id, new_number) pairs.
    /// Each pair updates the chapter_number of the specified chapter.
    pub async fn reorder(
        &self,
        db: &DatabaseConnection,
        reorders: &[(&str, i32)],
    ) -> AppResult<u64> {
        let mut updated: u64 = 0;
        for (chapter_id, new_number) in reorders {
            let chapter = self
                .find_by_id(db, chapter_id)
                .await?
                .ok_or_else(AppError::chapter_not_found)?;

            let mut active = chapter.into_active_model();
            active.chapter_number = Set(*new_number);
            active.update(db).await.map_err(|e| {
                tracing::error!(chapter_id, new_number, "Database error reordering chapter: {e}");
                AppError::internal("Database update failed")
            })?;
            updated += 1;
        }
        Ok(updated)
    }

    /// Create a new chapter.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: chapter::ActiveModel,
    ) -> AppResult<ChapterModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Database error creating chapter: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing chapter.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: chapter::ActiveModel,
    ) -> AppResult<ChapterModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Database error updating chapter: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Soft-delete a chapter.
    pub async fn soft_delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        let chapter = self
            .find_by_id(db, id)
            .await?
            .ok_or_else(AppError::chapter_not_found)?;

        let mut active = chapter.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now().into()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Database error soft-deleting chapter: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Count chapters in a project.
    pub async fn count_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<u64> {
        Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Database error counting chapters: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count chapters in a project, optionally filtered by status.
    pub async fn count_by_project_and_status(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        status: Option<&str>,
    ) -> AppResult<u64> {
        let mut query = Chapter::find()
            .filter(chapter::Column::ProjectId.eq(project_id))
            .filter(chapter::Column::IsDeleted.eq(false));
        if let Some(s) = status {
            query = query.filter(chapter::Column::Status.eq(s));
        }
        query.count(db).await.map_err(|e| {
            tracing::error!(project_id, "Database error counting chapters by status: {e}");
            AppError::internal("Database query failed")
        })
    }
}
