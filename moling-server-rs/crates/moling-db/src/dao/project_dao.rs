//! Project DAO — project CRUD with ownership filtering and statistics.

use chrono::{Duration, Utc};
use moling_core::error::{AppError, AppResult};
use moling_core::types::Pagination;
use sea_orm::{ColumnTrait, DatabaseConnection, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::project::{self, Entity as Project, Model as ProjectModel};

/// Aggregated project statistics for a user.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ProjectStats {
    pub total_projects: u64,
    pub active_count: u64,
    pub draft_count: u64,
    pub total_words: i64,
}

/// Project data access object.
#[derive(Clone, Default)]
pub struct ProjectDao;

impl ProjectDao {
    /// Find projects owned by a user (paginated, excluding soft-deleted).
    pub async fn find_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        pagination: &Pagination,
    ) -> AppResult<(Vec<ProjectModel>, u64)> {
        let paginator = Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::IsDeleted.eq(false))
            .order_by_desc(project::Column::UpdatedAt)
            .paginate(db, pagination.limit());

        let total = paginator.num_items().await.map_err(|e| {
            tracing::error!("Database error counting projects: {e}");
            AppError::internal("Database query failed")
        })?;

        let items = paginator
            .fetch_page(pagination.page as u64 - 1)
            .await
            .map_err(|e| {
                tracing::error!("Database error fetching projects: {e}");
                AppError::internal("Database query failed")
            })?;

        Ok((items, total))
    }

    /// List projects by user with simple offset/limit, newest first.
    pub async fn list_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<ProjectModel>> {
        Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::IsDeleted.eq(false))
            .order_by_desc(project::Column::UpdatedAt)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, "Database error listing user projects: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a single project by ID (excluding soft-deleted).
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: i32,
    ) -> AppResult<Option<ProjectModel>> {
        Project::find_by_id(id)
            .filter(project::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Database error finding project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all active (non-deleted, status="active") projects across all users.
    pub async fn get_all_active(
        &self,
        db: &DatabaseConnection,
        limit: u64,
    ) -> AppResult<Vec<ProjectModel>> {
        Project::find()
            .filter(project::Column::IsDeleted.eq(false))
            .filter(project::Column::Status.eq("active"))
            .order_by_desc(project::Column::UpdatedAt)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error listing all active projects: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List projects updated within the last N hours (active, non-deleted only).
    pub async fn get_recently_active(
        &self,
        db: &DatabaseConnection,
        hours: i64,
        limit: u64,
    ) -> AppResult<Vec<ProjectModel>> {
        let cutoff = Utc::now() - Duration::hours(hours);
        Project::find()
            .filter(project::Column::IsDeleted.eq(false))
            .filter(project::Column::Status.eq("active"))
            .filter(project::Column::UpdatedAt.gte(cutoff.naive_utc()))
            .order_by_desc(project::Column::UpdatedAt)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error listing recently active projects: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Return aggregated project statistics for a user (total, active, draft, words).
    /// Executes all count queries in parallel via tokio::try_join! to reduce latency.
    pub async fn get_stats(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<ProjectStats> {
        let total_fut = Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::IsDeleted.eq(false))
            .count(db);

        let active_fut = Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::Status.eq("active"))
            .filter(project::Column::IsDeleted.eq(false))
            .count(db);

        let draft_fut = Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::Status.eq("draft"))
            .filter(project::Column::IsDeleted.eq(false))
            .count(db);

        let words_fut = Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::IsDeleted.eq(false))
            .select_only()
            .column_as(project::Column::WordCount.sum(), "total_words")
            .into_tuple::<(Option<i64>,)>()
            .one(db);

        let (total, active_count, draft_count, total_words) = tokio::try_join!(
            total_fut, active_fut, draft_fut, words_fut
        )
        .map_err(|e| {
            tracing::error!(user_id, "Database error computing stats: {e}");
            AppError::internal("Database query failed")
        })?;

        let total_words = total_words.and_then(|(v,)| v).unwrap_or(0);

        Ok(ProjectStats {
            total_projects: total,
            active_count,
            draft_count,
            total_words,
        })
    }

    /// Create a new project.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: project::ActiveModel,
    ) -> AppResult<ProjectModel> {
        use sea_orm::ActiveModelTrait;
        model.insert(db).await.map_err(|e| {
            tracing::error!("Database error creating project: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing project.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: project::ActiveModel,
    ) -> AppResult<ProjectModel> {
        use sea_orm::ActiveModelTrait;
        model.update(db).await.map_err(|e| {
            tracing::error!("Database error updating project: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Soft-delete a project.
    pub async fn soft_delete(&self, db: &DatabaseConnection, id: i32) -> AppResult<()> {
        use sea_orm::{ActiveModelTrait, IntoActiveModel, Set};

        let project = self
            .find_by_id(db, id)
            .await?
            .ok_or_else(AppError::project_not_found)?;

        let mut active = project.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Database error soft-deleting project: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Count total projects for a user.
    pub async fn count_by_user(&self, db: &DatabaseConnection, user_id: &str) -> AppResult<u64> {
        Project::find()
            .filter(project::Column::UserId.eq(user_id))
            .filter(project::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error counting user projects: {e}");
                AppError::internal("Database query failed")
            })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use moling_core::types::Pagination;
    use sea_orm::{ConnectionTrait, Database, DatabaseConnection, DbBackend, Set, Statement};

    async fn setup_db() -> DatabaseConnection {
        let db = Database::connect("sqlite::memory:").await.unwrap();

        let stmt = Statement::from_string(
            DbBackend::Sqlite,
            "CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                genre TEXT NOT NULL DEFAULT '',
                tags TEXT,
                synopsis TEXT,
                worldview TEXT,
                protagonist TEXT,
                supporting_chars TEXT,
                word_count INTEGER NOT NULL DEFAULT 0,
                target_words INTEGER,
                frequency TEXT,
                style TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                creation_mode TEXT NOT NULL DEFAULT 'from_scratch',
                template_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT
            );",
        );
        db.execute(stmt).await.unwrap();
        db
    }

    fn make_project(user_id: &str, title: &str, status: &str) -> project::ActiveModel {
        project::ActiveModel {
            user_id: Set(user_id.to_owned()),
            title: Set(title.to_owned()),
            author: Set("Test Author".to_owned()),
            genre: Set("fantasy".to_owned()),
            status: Set(status.to_owned()),
            word_count: Set(0),
            creation_mode: Set("from_scratch".to_owned()),
            created_at: Set(chrono::Utc::now()),
            updated_at: Set(chrono::Utc::now()),
            is_deleted: Set(false),
            ..Default::default()
        }
    }

    #[tokio::test]
    async fn test_project_create_and_find() {
        let db = setup_db().await;
        let dao = ProjectDao;
        let user_id = uuid::Uuid::new_v4().to_string();

        let created = dao.create(&db, make_project(&user_id, "My Novel", "draft")).await.unwrap();
        assert!(created.id > 0);
        assert_eq!(created.title, "My Novel");

        let found = dao.find_by_id(&db, created.id).await.unwrap().unwrap();
        assert_eq!(found.title, "My Novel");
        assert_eq!(found.user_id, user_id);

        let pagination = Pagination { page: 1, page_size: 10 };
        let (items, total) = dao.find_by_user(&db, &user_id, &pagination).await.unwrap();
        assert_eq!(total, 1);
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].id, created.id);

        let items = dao.list_by_user(&db, &user_id, 0, 10).await.unwrap();
        assert_eq!(items.len(), 1);
    }

    #[tokio::test]
    async fn test_project_soft_delete() {
        let db = setup_db().await;
        let dao = ProjectDao;
        let user_id = uuid::Uuid::new_v4().to_string();

        let created = dao.create(&db, make_project(&user_id, "Delete Me", "draft")).await.unwrap();
        let pid = created.id;

        assert!(dao.find_by_id(&db, pid).await.unwrap().is_some());
        assert_eq!(dao.count_by_user(&db, &user_id).await.unwrap(), 1);

        dao.soft_delete(&db, pid).await.unwrap();

        assert!(dao.find_by_id(&db, pid).await.unwrap().is_none());
        assert_eq!(dao.count_by_user(&db, &user_id).await.unwrap(), 0);
    }

    #[tokio::test]
    async fn test_project_stats() {
        let db = setup_db().await;
        let dao = ProjectDao;
        let user_id = uuid::Uuid::new_v4().to_string();

        dao.create(&db, make_project(&user_id, "Draft Project", "draft")).await.unwrap();
        dao.create(&db, make_project(&user_id, "Active Project 1", "active")).await.unwrap();
        dao.create(&db, make_project(&user_id, "Active Project 2", "active")).await.unwrap();

        let stats = dao.get_stats(&db, &user_id).await.unwrap();
        assert_eq!(stats.total_projects, 3);
        assert_eq!(stats.draft_count, 1);
        assert_eq!(stats.active_count, 2);

        let active_projects = dao.get_all_active(&db, 10).await.unwrap();
        assert_eq!(active_projects.len(), 2);

        let recent = dao.get_recently_active(&db, 24, 10).await.unwrap();
        assert_eq!(recent.len(), 2);
    }
}
