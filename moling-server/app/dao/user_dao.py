"""墨灵 (Moling) — User DAO (async)."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from app.dao.base_dao import BaseDAO
from app.models.user import User

logger = logging.getLogger(__name__)


class UserDAO(BaseDAO[User]):
    """Data access for User records."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Find a user by their email address."""
        stmt = select(User).where(User.email == email, User.is_deleted == False)
        result = await db.execute(stmt)  # type: ignore[union-attr]
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        db: AsyncSession,
        username: str,
    ) -> Optional[User]:
        """Find a user by their username."""
        stmt = select(User).where(User.username == username, User.is_deleted == False)
        result = await db.execute(stmt)  # type: ignore[union-attr]
        return result.scalar_one_or_none()

    async def get_by_reset_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> Optional[User]:
        """Find a user by their password reset token."""
        stmt = select(User).where(User.reset_token == token, User.is_deleted == False)
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
        try:
            stmt = select(User).where(User.email == email, User.is_deleted == False)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception:
            logger.error("get_by_email_sync failed for email=%s", email, exc_info=True)
            raise

    def get_by_username_sync(
        self,
        db: SyncSession,
        username: str,
    ) -> Optional[User]:
        """Sync version — use with get_sync_db()."""
        try:
            stmt = select(User).where(User.username == username, User.is_deleted == False)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception:
            logger.error("get_by_username_sync failed for username=%s", username, exc_info=True)
            raise

    def create_sync(
        self,
        db: SyncSession,
        obj_in: dict | BaseModel,
    ) -> User:
        """Sync create — use with get_sync_db().
        
        Note: caller is responsible for committing the transaction.
        """
        try:
            if isinstance(obj_in, dict):
                instance = self.model_class(**obj_in)
            else:
                instance = self.model_class(**obj_in.model_dump())
            db.add(instance)
            db.flush()
            db.refresh(instance)
            return instance
        except Exception:
            logger.error("create_sync failed for model=%s", self.model_class.__name__, exc_info=True)
            raise
