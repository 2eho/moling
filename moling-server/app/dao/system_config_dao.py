"""SystemConfig DAO — key-value configuration store.

SystemConfig uses ``key`` (string) as primary key, not the standard
UUID ``id`` column. Therefore it needs its own DAO rather than
inheriting from BaseDAO.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig


class SystemConfigDAO:
    """Data access for SystemConfig key-value records."""

    def __init__(self) -> None:
        self.model_class = SystemConfig

    async def get_by_key(
        self, db: AsyncSession, key: str
    ) -> Optional[SystemConfig]:
        """Retrieve a config entry by its key."""
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_keys(
        self, db: AsyncSession, keys: Sequence[str]
    ) -> dict[str, SystemConfig]:
        """Retrieve multiple config entries by their keys.

        Returns a dict keyed by the SystemConfig key, so callers can
        use ``result.get("llm_api_key")`` without iterating.
        """
        if not keys:
            return {}
        stmt = select(SystemConfig).where(SystemConfig.key.in_(list(keys)))
        result = await db.execute(stmt)
        return {row.key: row for row in result.scalars().all()}

    async def upsert(
        self, db: AsyncSession, key: str, value: str, description: str = ""
    ) -> SystemConfig:
        """Insert or update a config entry."""
        existing = await self.get_by_key(db, key)
        if existing:
            existing.value = value
            if description:
                existing.description = description
        else:
            existing = SystemConfig(key=key, value=value, description=description)
            db.add(existing)
        await db.flush()
        return existing

    async def upsert_batch(
        self,
        db: AsyncSession,
        configs: dict[str, str],
        description: str = "",
    ) -> None:
        """Insert or update multiple config entries at once."""
        for key, value in configs.items():
            await self.upsert(db, key, value, description)
