//! Notification DAO — notification CRUD with read-status management.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::notification::{self, ActiveModel, Entity as Notification, Model as NotificationModel};

/// Notification data access object.
#[derive(Clone, Default)]
pub struct NotificationDao;

impl NotificationDao {
    /// Find a notification by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: i32,
    ) -> AppResult<Option<NotificationModel>> {
        Notification::find_by_id(id)
            .filter(notification::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Notification: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List notifications for a user with pagination and optional read filter.
    pub async fn list_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
        is_read: Option<bool>,
    ) -> AppResult<Vec<NotificationModel>> {
        let mut query = Notification::find()
            .filter(notification::Column::UserId.eq(user_id))
            .filter(notification::Column::IsDeleted.eq(false));

        if let Some(read) = is_read {
            query = query.filter(notification::Column::IsRead.eq(read));
        }

        query
            .order_by_desc(notification::Column::CreatedAt)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, "Notification: database error listing by user: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Count notifications for a user, with optional read filter.
    pub async fn count_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        is_read: Option<bool>,
    ) -> AppResult<u64> {
        let mut query = Notification::find()
            .filter(notification::Column::UserId.eq(user_id))
            .filter(notification::Column::IsDeleted.eq(false));

        if let Some(read) = is_read {
            query = query.filter(notification::Column::IsRead.eq(read));
        }

        query.count(db).await.map_err(|e| {
            tracing::error!(user_id, "Notification: database error counting: {e}");
            AppError::internal("Database query failed")
        })
    }

    /// Create a new notification.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<NotificationModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Notification: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Mark a single notification as read (with user ownership check).
    pub async fn mark_as_read(
        &self,
        db: &DatabaseConnection,
        notification_id: i32,
        user_id: &str,
    ) -> AppResult<Option<NotificationModel>> {
        use sea_orm::{IntoActiveModel, Set};
        let entity = Notification::find()
            .filter(notification::Column::Id.eq(notification_id))
            .filter(notification::Column::UserId.eq(user_id))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%notification_id, "Notification: database error finding for mark-read: {e}");
                AppError::internal("Database query failed")
            })?
            .ok_or_else(|| AppError::not_found("通知不存在"))?;

        let mut active = entity.into_active_model();
        active.is_read = Set(true);
        let updated = active.update(db).await.map_err(|e| {
            tracing::error!(%notification_id, "Notification: database error marking as read: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(Some(updated))
    }

    /// Mark all unread notifications as read for a user.
    /// Returns the number of notifications updated.
    pub async fn mark_all_as_read(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<u64> {
        use sea_orm::sea_query::Expr;
        let result = Notification::update_many()
            .filter(notification::Column::UserId.eq(user_id))
            .filter(notification::Column::IsRead.eq(false))
            .col_expr(notification::Column::IsRead, Expr::value(true))
            .exec(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, "Notification: database error marking all as read: {e}");
                AppError::internal("Database update failed")
            })?;
        Ok(result.rows_affected)
    }

    /// Hard-delete a notification (with user ownership check).
    pub async fn delete_by_user(
        &self,
        db: &DatabaseConnection,
        notification_id: i32,
        user_id: &str,
    ) -> AppResult<Option<NotificationModel>> {
        use sea_orm::ModelTrait;
        let entity = Notification::find()
            .filter(notification::Column::Id.eq(notification_id))
            .filter(notification::Column::UserId.eq(user_id))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%notification_id, "Notification: database error finding for delete: {e}");
                AppError::internal("Database query failed")
            })?;

        if let Some(e) = entity {
            let deleted = e.clone();
            e.delete(db).await.map_err(|err| {
                tracing::error!(%notification_id, "Notification: database error deleting: {err}");
                AppError::internal("Database delete failed")
            })?;
            Ok(Some(deleted))
        } else {
            Ok(None)
        }
    }
}
