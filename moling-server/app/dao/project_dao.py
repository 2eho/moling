"""Project DAO."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.project import Project


class ProjectDAO(BaseDAO[Project]):
    """Data access for Project records."""

    def __init__(self) -> None:
        super().__init__(Project)

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """List projects owned by a specific user, newest first."""
        stmt = (
            select(Project)
            .where(Project.user_id == user_id, Project.is_deleted == False)
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_active(
        self,
        db: AsyncSession,
        limit: int = 200,
    ) -> list[Project]:
        """List all active (non-deleted) projects across all users.

        Used by Celery Beat periodic tasks for system-wide scans.
        """
        stmt = (
            select(Project)
            .where(Project.is_deleted == False, Project.status == "active")
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_recently_active(
        self,
        db: AsyncSession,
        hours: int = 6,
        limit: int = 200,
    ) -> list[Project]:
        """List projects updated within the last N hours.

        Used by Celery Beat periodic tasks for targeted scans.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(Project)
            .where(
                Project.is_deleted == False,
                Project.status == "active",
                Project.updated_at >= cutoff,
            )
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """Count projects owned by a specific user."""
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.is_deleted == False)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_stats(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> dict:
        """Return aggregated project statistics for a user."""
        # Total count
        total = await self.count_by_user(db, user_id)

        # Active count
        active_stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.status == "active", Project.is_deleted == False)
        )
        active_result = await db.execute(active_stmt)
        active_count = active_result.scalar_one()

        # Draft count
        draft_stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.status == "draft", Project.is_deleted == False)
        )
        draft_result = await db.execute(draft_stmt)
        draft_count = draft_result.scalar_one()

        # Total words
        words_stmt = (
            select(func.coalesce(func.sum(Project.word_count), 0))
            .where(Project.user_id == user_id, Project.is_deleted == False)
        )
        words_result = await db.execute(words_stmt)
        total_words = words_result.scalar_one()

        return {
            "total_projects": total,
            "active_count": active_count,
            "draft_count": draft_count,
            "total_words": total_words,
        }
