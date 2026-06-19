"""墨灵 (Moling) — Phase 4 Task DAO."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.phase4_task import Phase4Task


class Phase4DAO(BaseDAO[Phase4Task]):
    """Data access object for Phase4Task model."""

    def __init__(self):
        super().__init__(Phase4Task)

    async def get_by_nonce(
        self,
        db: AsyncSession,
        nonce: str,
    ) -> Phase4Task | None:
        """Get task by nonce (for idempotency check)."""
        stmt = select(Phase4Task).where(Phase4Task.nonce == nonce)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_chapter(
        self,
        db: AsyncSession,
        chapter_id: str,
        *,
        status: str | None = None,
    ) -> list[Phase4Task]:
        """Get tasks by chapter ID."""
        stmt = select(Phase4Task).where(Phase4Task.chapter_id == chapter_id)
        
        if status:
            stmt = stmt.where(Phase4Task.status == status)
        
        stmt = stmt.order_by(Phase4Task.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
        *,
        status: str | None = None,
    ) -> list[Phase4Task]:
        """Get tasks by project ID."""
        stmt = select(Phase4Task).where(Phase4Task.project_id == project_id)
        
        if status:
            stmt = stmt.where(Phase4Task.status == status)
        
        stmt = stmt.order_by(Phase4Task.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Singleton instance
phase4_dao = Phase4DAO()
