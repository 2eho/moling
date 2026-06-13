"""澧ㄧ伒 (Moling) 鈥?Card Pool / Draw Record DAO."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.card_pool import CardPool
from app.models.draw_history import DrawHistory as DrawRecord


class CardDAO(BaseDAO[CardPool]):
    """Data access for CardPool and DrawRecord."""

    def __init__(self) -> None:
        super().__init__(CardPool)

    # ---- CardPool ----

    async def get_active_cards(
        self,
        db: AsyncSession,
        project_id: int,
        count: int = 20,
    ) -> list[CardPool]:
        """Get active cards for a project, ordered by rarity (highest first)."""
        rarity_order = func.case(
            (CardPool.rarity == "legendary", 0),
            (CardPool.rarity == "epic", 1),
            (CardPool.rarity == "rare", 2),
            else_=3,
        )

        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.status == "active",
            )
            .order_by(rarity_order, func.random())
            .limit(count)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_rarity(
        self,
        db: AsyncSession,
        project_id: int,
        rarity: str,
    ) -> list[CardPool]:
        """Get all cards of a specific rarity in a project."""
        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.rarity == rarity,
            )
            .order_by(CardPool.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- DrawRecord ----

    async def get_draw_history(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int] = None,
    ) -> list[DrawRecord]:
        """Get draw records for a project, optionally filtered by chapter."""
        stmt = (
            select(DrawRecord)
            .where(DrawRecord.project_id == project_id)
            .order_by(DrawRecord.drawn_at.desc())
        )
        if chapter_id is not None:
            stmt = stmt.where(DrawRecord.chapter_id == chapter_id)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_draw(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int] = None,
    ) -> Optional[DrawRecord]:
        """Get the most recent draw record for a project / chapter."""
        stmt = (
            select(DrawRecord)
            .where(DrawRecord.project_id == project_id)
            .order_by(DrawRecord.drawn_at.desc())
            .limit(1)
        )
        if chapter_id is not None:
            stmt = stmt.where(DrawRecord.chapter_id == chapter_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_draw_record(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> DrawRecord:
        """Create a new draw record."""
        db_obj = DrawRecord(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
