"""澧ㄧ伒 (Moling) 鈥?Generation Task DAO."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.generation_task import GenerationTask


class GenerationDAO(BaseDAO[GenerationTask]):
    """Data access for GenerationTask records.

    Note: GenerationTask uses a UUID string as primary key, so the
    inherited ``get(id)`` works with string IDs.
    """

    def __init__(self) -> None:
        super().__init__(GenerationTask)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[GenerationTask]:
        """List generation tasks for a project, newest first."""
        stmt = (
            select(GenerationTask)
            .where(GenerationTask.project_id == project_id)
            .order_by(GenerationTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_chapter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
    ) -> list[GenerationTask]:
        """List generation tasks for a specific chapter."""
        stmt = (
            select(GenerationTask)
            .where(
                GenerationTask.project_id == project_id,
                GenerationTask.chapter_id == chapter_id,
            )
            .order_by(GenerationTask.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        db: AsyncSession,
        status: str,
        limit: int = 20,
    ) -> list[GenerationTask]:
        """List generation tasks with a specific status (for worker polling)."""
        stmt = (
            select(GenerationTask)
            .where(GenerationTask.status == status)
            .order_by(GenerationTask.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_chapter_and_type(
        self,
        db: AsyncSession,
        chapter_id: int,
        task_type: str,
    ) -> Optional[GenerationTask]:
        """Get the latest generation task for a chapter with a specific type."""
        stmt = (
            select(GenerationTask)
            .where(
                GenerationTask.chapter_id == chapter_id,
                GenerationTask.task_type == task_type,
            )
            .order_by(GenerationTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Optional[GenerationTask]:
        """Get a generation task by ID."""
        return await self.get(db, task_id)
