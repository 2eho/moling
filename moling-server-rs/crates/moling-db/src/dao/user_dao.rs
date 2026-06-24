//! User DAO — user CRUD and authentication queries.

use moling_core::error::{AppError, AppResult};
use moling_core::types::Pagination;
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, IntoActiveModel, PaginatorTrait, QueryFilter, QueryOrder, Set};

use crate::entities::user::{self, Entity as User, Model as UserModel};

/// User data access object.
#[derive(Clone)]
pub struct UserDao;

impl UserDao {
    pub fn new() -> Self {
        Self
    }

    /// Find a user by email (case-insensitive).
    pub async fn find_by_email(
        &self,
        db: &DatabaseConnection,
        email: &str,
    ) -> AppResult<Option<UserModel>> {
        User::find()
            .filter(user::Column::Email.eq(email.to_lowercase()))
            .filter(user::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(email, "Database error finding user by email: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a user by username (case-insensitive).
    pub async fn find_by_username(
        &self,
        db: &DatabaseConnection,
        username: &str,
    ) -> AppResult<Option<UserModel>> {
        User::find()
            .filter(user::Column::Username.eq(username.to_lowercase()))
            .filter(user::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(username, "Database error finding user by username: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a user by password reset token.
    pub async fn find_by_reset_token(
        &self,
        db: &DatabaseConnection,
        token: &str,
    ) -> AppResult<Option<UserModel>> {
        User::find()
            .filter(user::Column::ResetToken.eq(token))
            .filter(user::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error finding user by reset token: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a user by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<UserModel>> {
        User::find_by_id(id.to_owned())
            .filter(user::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Database error finding user: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List users with pagination, newest first.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        pagination: &Pagination,
    ) -> AppResult<(Vec<UserModel>, u64)> {
        let paginator = User::find()
            .filter(user::Column::IsDeleted.eq(false))
            .order_by_desc(user::Column::CreatedAt)
            .paginate(db, pagination.limit());

        let total = paginator.num_items().await.map_err(|e| {
            tracing::error!("Database error counting users: {e}");
            AppError::internal("Database query failed")
        })?;

        let items = paginator
            .fetch_page(pagination.page as u64 - 1)
            .await
            .map_err(|e| {
                tracing::error!("Database error listing users: {e}");
                AppError::internal("Database query failed")
            })?;

        Ok((items, total))
    }

    /// Check if an email is already registered.
    pub async fn email_exists(&self, db: &DatabaseConnection, email: &str) -> AppResult<bool> {
        let count = User::find()
            .filter(user::Column::Email.eq(email.to_lowercase()))
            .filter(user::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(email, "Database error checking email: {e}");
                AppError::internal("Database query failed")
            })?;
        Ok(count > 0)
    }

    /// Check if a username is already taken.
    pub async fn username_exists(
        &self,
        db: &DatabaseConnection,
        username: &str,
    ) -> AppResult<bool> {
        let count = User::find()
            .filter(user::Column::Username.eq(username.to_lowercase()))
            .filter(user::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(username, "Database error checking username: {e}");
                AppError::internal("Database query failed")
            })?;
        Ok(count > 0)
    }

    /// Create a new user.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: user::ActiveModel,
    ) -> AppResult<UserModel> {
        let id = match &model.id {
            sea_orm::ActiveValue::Set(v) => v.clone(),
            sea_orm::ActiveValue::Unchanged(v) => v.clone(),
            _ => return Err(AppError::internal("User id must be set".to_owned())),
        };
        match model.insert(db).await {
            Ok(inserted) => Ok(inserted),
            Err(e) => {
                // SeaORM may fail to re-select after insert (RecordNotFound)
                // with non-auto-increment PKs on SQLite. Fall back to manual lookup.
                tracing::debug!("Insert-return failed, looking up by id: {e}");
                self.find_by_id(db, &id).await?.ok_or_else(|| {
                    AppError::internal("Database insert failed — record not found after insert")
                })
            }
        }
    }

    /// Update an existing user.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: user::ActiveModel,
    ) -> AppResult<UserModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Database error updating user: {e}");
            AppError::internal("Database update failed")
        })
    }

    /// Soft-delete a user (sets is_deleted = true).
    pub async fn soft_delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use chrono::Utc;

        let user = self.find_by_id(db, id).await?;
        let Some(user) = user else {
            return Err(AppError::not_found("用户不存在"));
        };

        let mut active = user.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Database error soft-deleting user: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Count total non-deleted users.
    pub async fn count(&self, db: &DatabaseConnection) -> AppResult<u64> {
        User::find()
            .filter(user::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!("Database error counting users: {e}");
                AppError::internal("Database query failed")
            })
    }
}

impl Default for UserDao {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use moling_core::types::Pagination;
    use sea_orm::{ConnectionTrait, Database, DatabaseConnection, DbBackend, Statement, Set};

    async fn setup_db() -> DatabaseConnection {
        let db = Database::connect("sqlite::memory:").await.unwrap();
        let stmt = Statement::from_string(
            DbBackend::Sqlite,
            "CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'user',
                avatar_url TEXT,
                bio TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                settings TEXT,
                reset_token TEXT,
                reset_token_expires TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT
            );",
        );
        db.execute(stmt).await.unwrap();
        db
    }

    fn make_user(id: &str, email: &str, username: &str) -> user::ActiveModel {
        user::ActiveModel {
            id: Set(id.to_owned()),
            email: Set(email.to_owned()),
            username: Set(username.to_owned()),
            password_hash: Set("hashed_password".to_owned()),
            role: Set("user".to_owned()),
            status: Set("active".to_owned()),
            created_at: Set(chrono::Utc::now()),
            updated_at: Set(chrono::Utc::now()),
            is_deleted: Set(false),
            ..Default::default()
        }
    }

    #[tokio::test]
    #[ignore = "requires PostgreSQL database connection"]
    async fn test_user_create_and_find() {
        let db = setup_db().await;
        let dao = UserDao::new();
        let id = uuid::Uuid::new_v4().to_string();

        // Create
        let created = dao.create(&db, make_user(&id, "alice@test.com", "alice")).await.unwrap();
        assert_eq!(created.id, id);
        assert_eq!(created.email, "alice@test.com");

        // Find by email
        let found = dao.find_by_email(&db, "alice@test.com").await.unwrap().unwrap();
        assert_eq!(found.id, id);

        // Find by id
        let found = dao.find_by_id(&db, &id).await.unwrap().unwrap();
        assert_eq!(found.username, "alice");

        // Find by username
        let found = dao.find_by_username(&db, "alice").await.unwrap().unwrap();
        assert_eq!(found.email, "alice@test.com");
    }

    #[tokio::test]
    #[ignore = "requires PostgreSQL database connection"]
    async fn test_user_soft_delete() {
        let db = setup_db().await;
        let dao = UserDao::new();
        let id = uuid::Uuid::new_v4().to_string();

        dao.create(&db, make_user(&id, "bob@test.com", "bob")).await.unwrap();

        // Exists before delete
        assert!(dao.find_by_id(&db, &id).await.unwrap().is_some());

        // Soft delete
        dao.soft_delete(&db, &id).await.unwrap();

        // Not found after soft delete (filtered by is_deleted)
        assert!(dao.find_by_id(&db, &id).await.unwrap().is_none());

        // Not found by email
        assert!(dao.find_by_email(&db, "bob@test.com").await.unwrap().is_none());

        // Count should reflect deletion
        let count = dao.count(&db).await.unwrap();
        assert_eq!(count, 0);
    }

    #[tokio::test]
    #[ignore = "requires PostgreSQL database connection"]
    async fn test_user_email_exists() {
        let db = setup_db().await;
        let dao = UserDao::new();
        let id = uuid::Uuid::new_v4().to_string();

        // Initially not exists
        assert!(!dao.email_exists(&db, "carol@test.com").await.unwrap());

        dao.create(&db, make_user(&id, "carol@test.com", "carol")).await.unwrap();

        // Now exists
        assert!(dao.email_exists(&db, "carol@test.com").await.unwrap());

        // Still not exists for other email
        assert!(!dao.email_exists(&db, "dave@test.com").await.unwrap());

        // Username exists check
        assert!(dao.username_exists(&db, "carol").await.unwrap());
        assert!(!dao.username_exists(&db, "dave").await.unwrap());
    }

    #[tokio::test]
    #[ignore = "requires PostgreSQL database connection"]
    async fn test_user_list_pagination() {
        let db = setup_db().await;
        let dao = UserDao::new();

        // Create 3 users
        for name in ["alpha", "beta", "gamma"].iter() {
            let email = format!("{name}@test.com");
            let id = uuid::Uuid::new_v4().to_string();
            dao.create(&db, make_user(&id, &email, name)).await.unwrap();
        }

        // List page 1 with limit 2
        let pagination = Pagination { page: 1, page_size: 2 };
        let (items, total) = dao.list(&db, &pagination).await.unwrap();
        assert_eq!(total, 3);
        assert_eq!(items.len(), 2);

        // List page 2
        let pagination = Pagination { page: 2, page_size: 2 };
        let (items, _total) = dao.list(&db, &pagination).await.unwrap();
        assert_eq!(items.len(), 1);

        // Total count
        assert_eq!(dao.count(&db).await.unwrap(), 3);
    }
}
