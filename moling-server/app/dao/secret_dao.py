"""墨灵 (Moling) — Secret DAO."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.secret import Secret


class SecretDAO(BaseDAO[Secret]):
    """Data access for Secret (秘密矩阵)."""

    def __init__(self) -> None:
        super().__init__(Secret)

    # ---- Read ----

    async def get_by_id(
        self,
        db: AsyncSession,
        secret_id: int,
    ) -> Optional[Secret]:
        """Get a single secret by primary key."""
        return await self.get(db, secret_id)

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[Secret]:
        """List all secrets for a project."""
        stmt = (
            select(Secret)
            .where(Secret.project_id == project_id)
            .order_by(Secret.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_secrecy_level(
        self,
        db: AsyncSession,
        project_id: int,
        level: str,
    ) -> list[Secret]:
        """List secrets filtered by secrecy_level (hidden / partial / revealed)."""
        stmt = (
            select(Secret)
            .where(
                Secret.project_id == project_id,
                Secret.secrecy_level == level,
            )
            .order_by(Secret.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Write ----

    async def update_by_id(
        self,
        db: AsyncSession,
        secret_id: int,
        obj_in: dict,
    ) -> Optional[Secret]:
        """Update a secret by id, returning the refreshed object."""
        secret = await self.get(db, secret_id)
        if secret is None:
            return None
        for field, value in obj_in.items():
            if hasattr(secret, field) and field != "id":
                setattr(secret, field, value)
        await db.flush()
        await db.refresh(secret)
        return secret

    async def batch_create(
        self,
        db: AsyncSession,
        objs_in: list[dict],
    ) -> list[Secret]:
        """Batch create secrets, returning the created objects."""
        secrets = [Secret(**data) for data in objs_in]
        db.add_all(secrets)
        await db.flush()
        for s in secrets:
            await db.refresh(s)
        return secrets

    async def batch_update(
        self,
        db: AsyncSession,
        updates: list[dict],
    ) -> int:
        """Batch update secrets. Each dict must contain 'id' plus fields to update.
        Returns total number of rows updated.
        """
        total = 0
        for upd in updates:
            secret_id = upd.pop("id")
            stmt = (
                update(Secret)
                .where(Secret.id == secret_id)
                .values(**upd)
            )
            result = await db.execute(stmt)
            total += result.rowcount
        await db.flush()
        return total

    # ---- Aggregation ----

    async def calculate_debt_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Sum the debt of all secrets in a project."""
        stmt = (
            select(func.coalesce(func.sum(Secret.debt), 0))
            .where(Secret.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def count_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> int:
        """Count secrets in a project."""
        stmt = (
            select(func.count())
            .select_from(Secret)
            .where(Secret.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()


# Singleton
secret_dao = SecretDAO()
