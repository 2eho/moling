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
        limit: int = 50,
    ) -> list[DrawRecord]:
        """Get draw records for a project, optionally filtered by chapter."""
        stmt = (
            select(DrawRecord)
            .where(DrawRecord.project_id == project_id)
            .order_by(DrawRecord.created_at.desc(), DrawRecord.drawn_at.desc())
            .limit(limit)
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

    async def list_active_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[CardPool]:
        """List all active cards for a project, ordered by rarity desc then id asc."""
        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.is_active == True,
            )
            .order_by(CardPool.rarity.desc(), CardPool.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Synchronous methods for Celery workers ----

    def list_active_by_project_sync(
        self,
        db,  # sync Session
        project_id: int,
    ) -> list[CardPool]:
        """Synchronous: list all active cards for a project."""
        from sqlalchemy.orm import Session as SyncSession

        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.is_active == True,
            )
            .order_by(CardPool.rarity.desc(), CardPool.id.asc())
        )
        result = db.execute(stmt)
        return list(result.scalars().all())

    def get_active_cards_sync(
        self,
        db,  # sync Session
        project_id: int,
        count: int = 20,
    ) -> list[CardPool]:
        """Synchronous: get active cards for a project."""
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
        result = db.execute(stmt)
        return list(result.scalars().all())

    def list_by_project_sync(
        self,
        db,  # sync Session
        project_id: int,
    ) -> list[CardPool]:
        """Synchronous: list all cards for a project."""
        stmt = (
            select(CardPool)
            .where(CardPool.project_id == project_id)
            .order_by(CardPool.id.asc())
        )
        result = db.execute(stmt)
        return list(result.scalars().all())

    def get_by_ids_sync(
        self,
        db,  # sync Session
        project_id: int,
        card_ids: list[int],
    ) -> list[CardPool]:
        """Synchronous: get cards by their IDs within a project."""
        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.id.in_(card_ids),
            )
        )
        result = db.execute(stmt)
        return list(result.scalars().all())

    def batch_update_is_active_sync(
        self,
        db,  # sync Session
        project_id: int,
        card_ids: list[int],
        is_active: bool,
    ) -> int:
        """Synchronous: batch update is_active flag, returns updated count."""
        from sqlalchemy import update
        stmt = (
            update(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.id.in_(card_ids),
            )
            .values(is_active=is_active)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount
