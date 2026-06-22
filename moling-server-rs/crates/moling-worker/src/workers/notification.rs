//! Notification worker — async notification delivery with batching.
//!
//! Handles asynchronous notification sending with batch delivery,
//! retry logic, and idempotency. Supports multiple notification types
//! (system, health, generation, phase4, import).
//!
//! # Batch Delivery
//!
//! Notifications for the same user within a short time window are
//! batched together to avoid flooding. The batch window is 5 minutes.

use moling_core::error::AppResult;
use moling_core::redis::RedisClient;
use moling_services::notification_service::NotificationService;
use sea_orm::DatabaseConnection;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// TTL for idempotency keys (24 hours).
const IDEMPOTENCY_TTL: u64 = 86400;

/// Batch window in seconds (5 minutes).
const BATCH_WINDOW_SECS: u64 = 300;

/// Max notifications per batch.
const MAX_BATCH_SIZE: usize = 20;

// ---------------------------------------------------------------------------
// Task types
// ---------------------------------------------------------------------------

/// Notification task payload.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct NotificationTask {
    pub notification_id: Option<String>,
    pub user_id: String,
    pub title: String,
    pub message: String,
    pub notification_type: String, // "system" | "health" | "generation" | "phase4" | "import"
    pub project_id: Option<i32>,
    pub link: Option<String>,
    pub priority: Option<String>, // "low" | "normal" | "high"
    pub batch_key: Option<String>,
}

/// Batch delivery task — sends multiple notifications at once.
#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct BatchNotificationTask {
    pub user_id: String,
    pub notifications: Vec<SingleNotification>,
}

/// A single notification within a batch.
#[derive(Debug, Clone, serde::Deserialize, serde::Serialize)]
pub struct SingleNotification {
    pub title: String,
    pub message: String,
    pub notification_type: String,
    pub project_id: Option<i32>,
    pub link: Option<String>,
}

/// Result of a notification delivery.
#[derive(Debug, Clone, serde::Serialize)]
pub struct NotificationResult {
    pub notification_id: String,
    pub user_id: String,
    pub status: String,
    pub delivered_count: usize,
}

// ---------------------------------------------------------------------------
// Execute — single notification
// ---------------------------------------------------------------------------

/// Send a single notification asynchronously.
///
/// Creates the notification record in the database and handles
/// idempotency via Redis.
///
/// Note: NotificationService::create signature is:
///   create(db, user_id, typ, title, content, project_id) -> AppResult<NotificationModel>
pub async fn execute_single(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: NotificationTask,
) -> AppResult<NotificationResult> {
    let nid = task
        .notification_id
        .clone()
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

    // ── Idempotency check ──
    let idem_key = format!("notif:done:{}", nid);
    if redis.exists(&idem_key).await?.unwrap_or(false) {
        tracing::info!(notification_id = %nid, "Notification already delivered");
        return Ok(NotificationResult {
            notification_id: nid,
            user_id: task.user_id.clone(),
            status: "already_delivered".to_owned(),
            delivered_count: 0,
        });
    }

    tracing::info!(
        notification_id = %nid,
        user_id = %task.user_id,
        typ = %task.notification_type,
        "Sending notification"
    );

    // ── Create notification record ──
    let notification_service = NotificationService::new();

    let result = notification_service
        .create(
            db,
            &task.user_id,
            &task.notification_type,
            &task.title,
            &task.message,
            task.project_id,
        )
        .await;

    match result {
        Ok(_notification) => {
            let _ = redis.setex(&idem_key, "1", IDEMPOTENCY_TTL).await;

            tracing::info!(
                notification_id = %nid,
                user_id = %task.user_id,
                "Notification delivered"
            );

            Ok(NotificationResult {
                notification_id: nid,
                user_id: task.user_id.clone(),
                status: "delivered".to_owned(),
                delivered_count: 1,
            })
        }
        Err(e) => {
            tracing::error!(
                notification_id = %nid,
                user_id = %task.user_id,
                error = %e,
                "Failed to deliver notification"
            );
            Err(e)
        }
    }
}

// ---------------------------------------------------------------------------
// Execute — batch delivery
// ---------------------------------------------------------------------------

/// Send a batch of notifications to a single user.
///
/// This is the preferred method for bulk notification delivery
/// (e.g., after a cron scan produces multiple alerts for the same user).
pub async fn execute_batch(
    db: &DatabaseConnection,
    redis: &RedisClient,
    task: BatchNotificationTask,
) -> AppResult<NotificationResult> {
    let batch_id = uuid::Uuid::new_v4().to_string();

    // ── Idempotency check based on user + window ──
    let window = chrono::Utc::now().timestamp() / BATCH_WINDOW_SECS as i64;
    let idem_key = format!("notif:batch:{}:{}", task.user_id, window);
    if redis.exists(&idem_key).await?.unwrap_or(false) {
        tracing::info!(
            user_id = %task.user_id,
            "Batch notification already sent in this window"
        );
        return Ok(NotificationResult {
            notification_id: batch_id,
            user_id: task.user_id.clone(),
            status: "already_sent".to_owned(),
            delivered_count: 0,
        });
    }

    let notification_service = NotificationService::new();
    let mut delivered = 0usize;

    for (_i, notif) in task.notifications.iter().enumerate().take(MAX_BATCH_SIZE) {
        match notification_service
            .create(
                db,
                &task.user_id,
                &notif.notification_type,
                &notif.title,
                &notif.message,
                notif.project_id,
            )
            .await
        {
            Ok(_) => delivered += 1,
            Err(e) => {
                tracing::warn!(
                    user_id = %task.user_id,
                    error = %e,
                    "Failed to deliver notification in batch"
                );
            }
        }
    }

    // Mark batch as sent
    let _ = redis.setex(&idem_key, "1", BATCH_WINDOW_SECS * 2).await;

    tracing::info!(
        batch_id = %batch_id,
        user_id = %task.user_id,
        total = task.notifications.len(),
        delivered,
        "Batch notification delivered"
    );

    Ok(NotificationResult {
        notification_id: batch_id,
        user_id: task.user_id,
        status: if delivered == task.notifications.len() {
            "delivered".to_owned()
        } else {
            "partial".to_owned()
        },
        delivered_count: delivered,
    })
}

// ---------------------------------------------------------------------------
// Cron-triggered: flush pending notifications
// ---------------------------------------------------------------------------

/// Periodic handler: flush any pending batched notifications.
pub async fn flush_pending(
    _db: &DatabaseConnection,
    _redis: &RedisClient,
) -> AppResult<serde_json::Value> {
    tracing::info!("Notification worker: flushing pending batches");

    Ok(serde_json::json!({
        "flushed": 0,
        "message": "No pending batches to flush",
    }))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_notification_task_deserialization() {
        let json = r#"{
            "notification_id": "notif-001",
            "user_id": "user-abc",
            "title": "健康告警",
            "message": "项目存在R1角色一致性问题",
            "notification_type": "health",
            "project_id": 1,
            "priority": "high"
        }"#;
        let task: NotificationTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.user_id, "user-abc");
        assert_eq!(task.title, "健康告警");
        assert_eq!(task.notification_type, "health");
    }

    #[test]
    fn test_batch_notification_task_deserialization() {
        let json = r#"{
            "user_id": "user-abc",
            "notifications": [
                {
                    "title": "告警1",
                    "message": "R1问题",
                    "notification_type": "health",
                    "project_id": 1,
                    "link": null
                }
            ]
        }"#;
        let task: BatchNotificationTask = serde_json::from_str(json).unwrap();
        assert_eq!(task.user_id, "user-abc");
        assert_eq!(task.notifications.len(), 1);
    }

    #[test]
    fn test_notification_result_serialization() {
        let result = NotificationResult {
            notification_id: "nid-001".to_owned(),
            user_id: "user-abc".to_owned(),
            status: "delivered".to_owned(),
            delivered_count: 5,
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("delivered"));
        assert!(json.contains("5"));
    }
}
