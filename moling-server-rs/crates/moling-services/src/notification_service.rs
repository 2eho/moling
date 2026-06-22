//! Notification service — create, mark-read, broadcast to users.
//!
//! Mirrors Python `app/service/notification_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::notification_dao::NotificationDao;
use moling_db::entities::notification::Model as NotificationModel;
use sea_orm::{DatabaseConnection, Set};

/// Business logic for notification operations.
#[derive(Clone)]
pub struct NotificationService {
    dao: NotificationDao,
}

impl NotificationService {
    pub fn new() -> Self {
        Self {
            dao: NotificationDao,
        }
    }

    /// List notifications for a user with pagination and optional read filter.
    ///
    /// Mirrors Python `NotificationService.list_notifications`.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
        is_read: Option<bool>,
    ) -> AppResult<NotificationListResult> {
        let notifications = self
            .dao
            .list_by_user(db, user_id, skip, limit, is_read)
            .await?;
        let total = self.dao.count_by_user(db, user_id, is_read).await?;
        let unread_count = self.dao.count_by_user(db, user_id, Some(false)).await?;
        Ok(NotificationListResult {
            items: notifications,
            total,
            unread_count,
            skip,
            limit,
        })
    }

    /// Get a single notification with ownership check.
    ///
    /// Mirrors Python `NotificationService.get_notification`.
    pub async fn get(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        notification_id: i32,
    ) -> AppResult<NotificationModel> {
        let notification = self
            .dao
            .find_by_id(db, notification_id)
            .await?
            .ok_or_else(|| AppError::not_found("通知不存在".to_owned()))?;
        if notification.user_id != user_id {
            return Err(AppError::not_found("通知不存在".to_owned()));
        }
        Ok(notification)
    }

    /// Count unread notifications for a user.
    ///
    /// Mirrors Python `NotificationService.get_unread_count`.
    pub async fn unread_count(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<u64> {
        self.dao.count_by_user(db, user_id, Some(false)).await
    }

    /// Mark a single notification as read (with ownership check).
    ///
    /// Mirrors Python `NotificationService.mark_as_read`.
    pub async fn mark_read(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        notification_id: i32,
    ) -> AppResult<NotificationModel> {
        self.dao
            .mark_as_read(db, notification_id, user_id)
            .await?
            .ok_or_else(|| AppError::not_found("通知不存在".to_owned()))
    }

    /// Mark all notifications as read for a user.
    ///
    /// Mirrors Python `NotificationService.mark_all_as_read`.
    pub async fn mark_all_read(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<u64> {
        self.dao.mark_all_as_read(db, user_id).await
    }

    /// Delete a notification (with ownership check).
    ///
    /// Mirrors Python `NotificationService.delete_notification`.
    pub async fn delete(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        notification_id: i32,
    ) -> AppResult<()> {
        self.dao
            .delete_by_user(db, notification_id, user_id)
            .await?;
        Ok(())
    }

    /// Create a notification (for system events or broadcasts).
    ///
    /// Also provided as a convenience for other services and batch operations.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        typ: &str,
        title: &str,
        content: &str,
        project_id: Option<i32>,
    ) -> AppResult<NotificationModel> {
        let model = moling_db::entities::notification::ActiveModel {
            user_id: Set(user_id.to_owned()),
            r#type: Set(typ.to_owned()),
            title: Set(title.to_owned()),
            content: Set(Some(content.to_owned())),
            project_id: Set(project_id),
            ..Default::default()
        };
        self.dao.create(db, model).await
    }

    /// Broadcast a notification to multiple users.
    pub async fn broadcast(
        &self,
        db: &DatabaseConnection,
        user_ids: &[String],
        typ: &str,
        title: &str,
        content: &str,
    ) -> AppResult<usize> {
        let mut count = 0;
        for uid in user_ids {
            if self
                .create(db, uid, typ, title, content, None)
                .await
                .is_ok()
            {
                count += 1;
            }
        }
        Ok(count)
    }

    /// List notifications filtered by project ID.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<NotificationModel>> {
        // We use the DAO's list_by_user and filter client-side since there's
        // no dedicated project-filtered DAO method yet.
        let all = self
            .dao
            .list_by_user(db, user_id, skip, limit, None)
            .await?;
        Ok(all
            .into_iter()
            .filter(|n| n.project_id == Some(project_id))
            .collect())
    }
}

impl Default for NotificationService {
    fn default() -> Self {
        Self::new()
    }
}

/// Paginated notification list with unread count.
pub struct NotificationListResult {
    pub items: Vec<NotificationModel>,
    pub total: u64,
    pub unread_count: u64,
    pub skip: u64,
    pub limit: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_notif_service_constructs() {
        let _ = NotificationService::new();
    }

    #[test]
    fn test_notification_list_result() {
        let r = NotificationListResult {
            items: vec![],
            total: 0,
            unread_count: 0,
            skip: 0,
            limit: 20,
        };
        assert_eq!(r.unread_count, 0);
    }
}
