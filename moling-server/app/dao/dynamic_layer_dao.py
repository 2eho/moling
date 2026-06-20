"""墨灵 (Moling) — DynamicLayer DAO."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.dynamic_layer import DynamicLayer


class DynamicLayerDAO(BaseDAO[DynamicLayer]):
    """Data access for DynamicLayer (dynamic context per chapter)."""

    def __init__(self) -> None:
        super().__init__(DynamicLayer)

    async def get_by_chapter(
        self,
        db: AsyncSession,
        chapter_id: str,
    ) -> Optional[DynamicLayer]:
        """Get the dynamic layer for a specific chapter."""
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.chapter_id == chapter_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_by_project(
        self,
        db: AsyncSession,
        project_id: str,
        limit: int = 5,
    ) -> list[DynamicLayer]:
        """Get the most recent dynamic layers for a project."""
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> DynamicLayer | None:
        """Get the single most recent dynamic layer for a project."""
        layers = await self.get_recent_by_project(db, project_id, limit=1)
        return layers[0] if layers else None

    async def get_health_check_history(
        self,
        db: AsyncSession,
        project_id: int,
        limit: int = 20,
        *,
        start_chapter: int | None = None,
        end_chapter: int | None = None,
    ) -> list[dict]:
        """Get health check history with chapter numbers for a project.

        Returns list of dicts with keys: health_check, chapter_number, checked_at

        Optionally filter by chapter_number range: start_chapter <= n < end_chapter.
        """
        from app.models.chapter import Chapter

        stmt = (
            select(
                DynamicLayer.health_check,
                Chapter.chapter_number,
                DynamicLayer.created_at.label("checked_at"),
            )
            .join(Chapter, DynamicLayer.chapter_id == Chapter.id)
            .where(DynamicLayer.project_id == project_id)
            .where(DynamicLayer.health_check.isnot(None))
            .order_by(DynamicLayer.created_at.desc())
            .limit(limit)
        )
        if start_chapter is not None:
            stmt = stmt.where(Chapter.chapter_number >= start_chapter)
        if end_chapter is not None:
            stmt = stmt.where(Chapter.chapter_number < end_chapter)

        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "health_check": row.health_check,
                "chapter_number": row.chapter_number,
                "checked_at": row.checked_at,
            }
            for row in rows
        ]


# Singleton
dynamic_layer_dao = DynamicLayerDAO()
