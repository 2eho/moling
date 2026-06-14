"""墨灵 (Moling) — User DAO (async)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SyncSession

from app.dao.base_dao import BaseDAO
from app.models.user import User


class UserDAO(BaseDAO[User]):
    """Data access for User records."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(
        self,
        db: SyncSession,  # type: ignore[override]
        email: str,
    ) -> Optional[User]:
        """Find a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)  # type: ignore[union-attr]
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        db: SyncSession,  # type: ignore[override]
        username: str,
    ) -> Optional[User]:
        """Find a user by their username."""
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)  # type: ignore[union-attr]
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Sync versions (for Windows + aiosslite workaround)
    # ------------------------------------------------------------------

    def get_by_email_sync(
        self,
        db: SyncSession,
        email: str,
    ) -> Optional[User]:
        """Sync version — use with get_sync_db()."""
        stmt = select(User).where(User.email == email)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_username_sync(
        self,
        db: SyncSession,
        username: str,
    ) -> Optional[User]:
        """Sync version — use with get_sync_db()."""
        stmt = select(User).where(User.username == username)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def create_sync(
        self,
        db: SyncSession,
        obj_in: dict | BaseModel,
    ) -> User:
        """Sync create — use with get_sync_db()."""
        if isinstance(obj_in, dict):
            instance = self.model_class(**obj_in)
        else:
            instance = self.model_class(**obj_in.model_dump())
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
