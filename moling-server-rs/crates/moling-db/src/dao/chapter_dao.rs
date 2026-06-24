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
        active.confirmed_at = Set(Some(Utc::now()));
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
        // Extract id before consuming model
        let id = match &model.id {
            sea_orm::ActiveValue::Set(v) => v.clone(),
            sea_orm::ActiveValue::Unchanged(v) => v.clone(),
            _ => return Err(AppError::internal("Chapter id must be set".to_owned())),
        };
        // Use Entity::insert instead of ActiveModel::insert to avoid SQLite RETURNING issue
        use sea_orm::EntityTrait;
        chapter::Entity::insert(model)
            .exec(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error creating chapter: {e}");
                AppError::internal("Database insert failed")
            })?;
        // Retrieve the inserted model via primary key
        self.find_by_id(db, &id)
            .await?
            .ok_or_else(|| AppError::internal("Chapter inserted but not found".to_owned()))
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
        active.deleted_at = Set(Some(Utc::now()));
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

#[cfg(test)]
mod tests {
    use super::*;
    use sea_orm::{ConnectionTrait, Database, DbBackend, Statement};

    async fn setup() -> DatabaseConnection {
        let db = Database::connect("sqlite::memory:").await.unwrap();
        let sqls = [
            "CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                title TEXT NOT NULL, author TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft', creation_mode TEXT NOT NULL DEFAULT 'from_scratch',
                word_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0
            )",
            "CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY, project_id INTEGER NOT NULL,
                title TEXT NOT NULL, content TEXT, chapter_number INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft', phase4_status TEXT NOT NULL DEFAULT 'pending',
                word_count INTEGER NOT NULL DEFAULT 0, confirmed_at TEXT,
                used_card_ids TEXT, generation_mode TEXT, generation_prompt TEXT,
                generation_weights TEXT, generation_result TEXT, error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0, generation_duration INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
            )",
        ];
        for sql in sqls {
            db.execute(Statement::from_string(DbBackend::Sqlite, sql.to_owned()))
                .await
                .unwrap();
        }
        db
    }

    #[tokio::test]
    async fn test_insert_chapter() {
        let db = setup().await;
        db.execute(Statement::from_string(DbBackend::Sqlite,
            "INSERT INTO projects (id, user_id, title, status) VALUES (1, 'u1', 'Test', 'active')"))
            .await.unwrap();

        let now = chrono::Utc::now();
        let model = chapter::ActiveModel {
            id: Set("ch-test-1".into()),
            project_id: Set(1),
            title: Set("Chapter One".into()),
            content: Set(None),
            chapter_number: Set(1),
            status: Set("draft".into()),
            phase4_status: Set("pending".into()),
            word_count: Set(0),
            confirmed_at: Set(None),
            used_card_ids: Set(None),
            generation_mode: Set(None),
            generation_prompt: Set(None),
            generation_weights: Set(None),
            generation_result: Set(None),
            error_message: Set(None),
            retry_count: Set(0),
            generation_duration: Set(None),
            created_at: Set(now),
            updated_at: Set(now),
            is_deleted: Set(false),
            deleted_at: Set(None),
        };

        let created = ChapterDao.create(&db, model).await;
        assert!(created.is_ok(), "Chapter insert failed: {:?}", created.err());
        let ch = created.unwrap();
        assert_eq!(ch.id, "ch-test-1");
        assert_eq!(ch.title, "Chapter One");
    }
}
