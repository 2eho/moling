"""澧ㄧ伒 (Moling) 鈥?Chapter DAO."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.chapter import Chapter


class ChapterDAO(BaseDAO[Chapter]):
    """Data access for Chapter records."""

    def __init__(self) -> None:
        super().__init__(Chapter)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Chapter]:
        """List chapters in a project ordered by chapter_number ascending."""
        stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_number(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_number: int,
    ) -> Optional[Chapter]:
        """Find a chapter by its number within a project."""
        stmt = (
            select(Chapter)
            .where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == chapter_number,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> Optional[Chapter]:
        """Get the most recent (highest chapter_number) chapter."""
        stmt = (
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_max_chapter_number(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Return the highest chapter number in a project (0 if empty)."""
        stmt = (
            select(func.coalesce(func.max(Chapter.chapter_number), 0))
            .where(Chapter.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_content(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_number: int,
    ) -> str | None:
        """Get the raw content of a chapter by project_id and chapter_number."""
        stmt = (
            select(Chapter.content)
            .where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == chapter_number,
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        return row[0] if row else None

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: int,
        *,
        status: str | None = None,
    ) -> int:
        """Count chapters in a project, optionally filtered by status."""
        stmt = select(func.count()).select_from(Chapter).where(
            Chapter.project_id == project_id
        )
        if status is not None:
            stmt = stmt.where(Chapter.status == status)
        result = await db.execute(stmt)
        return result.scalar_one()
