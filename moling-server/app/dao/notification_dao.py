"""墨灵 (Moling) — Notification DAO."""

from __future__ import annotations

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.notification import Notification


class NotificationDAO(BaseDAO[Notification]):
    """Data access object for Notification model."""

    def __init__(self):
        super().__init__(Notification)

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
        is_read: bool | None = None,
    ) -> list[Notification]:
        """Get notifications for a specific user with pagination."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        
        stmt = stmt.order_by(Notification.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        is_read: bool | None = None,
    ) -> int:
        """Count notifications for a specific user."""
        stmt = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id
        )
        
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)
        
        result = await db.execute(stmt)
        return result.scalar_one()

    async def mark_as_read(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int,
    ) -> Notification | None:
        """Mark a notification as read (with user ownership check)."""
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> int:
        """Mark all notifications as read for a user. Returns count of updated."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        return result.rowcount

    async def delete_by_user(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int,
    ) -> Notification | None:
        """Delete a notification (with user ownership check)."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if notification:
            await db.delete(notification)
            await db.flush()
        
        return notification


# Singleton instance
notification_dao = NotificationDAO()
