"""墨灵 (Moling) — Template DAO."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.template import Template


class TemplateDAO(BaseDAO[Template]):
    """Data access object for Template model."""

    def __init__(self):
        super().__init__(Template)

    async def get_by_genre(
        self,
        db: AsyncSession,
        genre: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Template]:
        """Get templates by genre."""
        stmt = (
            select(Template)
            .where(Template.genre == genre)
            .order_by(Template.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_genre(
        self,
        db: AsyncSession,
        genre: str,
    ) -> int:
        """Count templates by genre."""
        stmt = select(func.count()).select_from(Template).where(Template.genre == genre)
        result = await db.execute(stmt)
        return result.scalar_one()


# Singleton instance
template_dao = TemplateDAO()
