"""墨灵 (Moling) — Notification Service.

业务逻辑：列出通知、标记已读、删除通知等。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import notification_dao
from app.errors import ErrorCode, NotFoundError
from app.schemas.notification import NotificationResp


class NotificationService:
    """Service for notification operations."""

    async def list_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        is_read: Optional[bool] = None,
    ) -> dict:
        """List notifications for a user with pagination."""
        skip = (page - 1) * page_size
        
        notifications = await notification_dao.get_by_user(
            db, user_id, skip=skip, limit=page_size, is_read=is_read
        )
        
        total = await notification_dao.count_by_user(db, user_id, is_read=is_read)
        unread_count = await notification_dao.count_by_user(db, user_id, is_read=False)
        
        return {
            "items": [NotificationResp.model_validate(n) for n in notifications],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "unread_count": unread_count,
        }

    async def get_notification(
        self,
        db: AsyncSession,
        user_id: int,
        notification_id: int,
    ) -> NotificationResp:
        """Get a single notification (with ownership check)."""
        notification = await notification_dao.get(db, notification_id)
        
        if notification is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Notification not found",
            )
        
        if notification.user_id != user_id:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Notification not found",
            )
        
        return NotificationResp.model_validate(notification)

    async def mark_as_read(
        self,
        db: AsyncSession,
        user_id: int,
        notification_id: int,
    ) -> NotificationResp:
        """Mark a notification as read."""
        notification = await notification_dao.mark_as_read(db, notification_id, user_id)
        
        if notification is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Notification not found",
            )
        
        return NotificationResp.model_validate(notification)

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> dict:
        """Mark all notifications as read for a user."""
        updated_count = await notification_dao.mark_all_as_read(db, user_id)
        await db.commit()
        
        return {
            "updated_count": updated_count,
            "message": f"已标记 {updated_count} 条通知为已读",
        }

    async def delete_notification(
        self,
        db: AsyncSession,
        user_id: int,
        notification_id: int,
    ) -> None:
        """Delete a notification (with ownership check)."""
        notification = await notification_dao.delete_by_user(db, notification_id, user_id)
        
        if notification is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Notification not found",
            )
        
        await db.commit()

    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> dict:
        """Get unread notification count for a user."""
        count = await notification_dao.count_by_user(db, user_id, is_read=False)
        return {"unread_count": count}


# Singleton instance
notification_service = NotificationService()
