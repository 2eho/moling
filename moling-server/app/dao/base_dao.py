"""墨灵 (Moling) — Generic Base DAO with CRUD operations (async)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from app.models.base import BaseModel as MolingModel

ModelT = TypeVar("ModelT", bound=MolingModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseDAO(Generic[ModelT]):
    """Generic CRUD data access object (async).

    Usage::

        class UserDAO(BaseDAO[User]):
            def __init__(self):
                super().__init__(User)
    """

    def __init__(self, model_class: type[ModelT]):
        self.model_class = model_class

    # ---- Query builders ----

    def _apply_filters(
        self,
        stmt: Select,
        filters: Optional[dict[str, Any]] = None,
    ) -> Select:
        """Apply WHERE conditions from a filter dict.

        Supports: ``{"field": value}`` → ``WHERE field = value``
        """
        if filters:
            for field, value in filters.items():
                column = getattr(self.model_class, field, None)
                if column is not None:
                    stmt = stmt.where(column == value)
        return stmt

    # ---- CRUD ----

    async def get(
        self,
        db: AsyncSession,
        id: Any,
        *,
        include_deleted: bool = False,
    ) -> Optional[ModelT]:
        """Retrieve a single record by primary key.

        By default excludes soft-deleted records when the model supports it.
        Pass ``include_deleted=True`` to bypass this filter (e.g. for restore).
        """
        stmt = select(self.model_class).where(self.model_class.id == id)

        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            stmt = stmt.where(self.model_class.is_deleted == False)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def get_sync(
        self,
        db: SyncSession,
        id: Any,
    ) -> Optional[ModelT]:
        """Sync retrieve — use with get_sync_db() to avoid Windows greenlet issues."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        descending: bool = True,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        """Retrieve a paginated list of records with optional filters.

        By default excludes soft-deleted records when the model supports it.
        """
        stmt = select(self.model_class)

        if not include_deleted and hasattr(self.model_class, 'is_deleted'):
            stmt = stmt.where(self.model_class.is_deleted == False)

        stmt = self._apply_filters(stmt, filters)

        if order_by:
            column = getattr(self.model_class, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            if hasattr(self.model_class, 'created_at'):
                stmt = stmt.order_by(self.model_class.created_at.desc())
            else:
                pass  # 不排序

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaT | dict[str, Any],
    ) -> ModelT:
        """Create a new record from a Pydantic schema or plain dict."""
        if isinstance(obj_in, BaseModel):
            create_data = obj_in.model_dump(exclude_unset=True)
        else:
            create_data = obj_in

        db_obj = self.model_class(**create_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelT,
        obj_in: UpdateSchemaT | dict[str, Any],
    ) -> ModelT:
        """Update an existing record (partial update)."""
        if isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        id: Any,
        *,
        soft: bool = True,
    ) -> Optional[ModelT]:
        """Delete a record.

        When the model has ``is_deleted`` attribute and ``soft=True`` (default),
        performs a soft delete by setting ``is_deleted=True`` and
        ``deleted_at=now()``.

        Set ``soft=False`` to perform a physical/hard delete regardless of
        soft-delete support.
        """
        db_obj = await self.get(db, id, include_deleted=True)
        if db_obj is None:
            return None

        if soft and hasattr(db_obj, 'is_deleted'):
            db_obj.is_deleted = True
            db_obj.deleted_at = datetime.now(timezone.utc)
            await db.flush()
            await db.refresh(db_obj)
        else:
            await db.delete(db_obj)
            await db.flush()

        return db_obj

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[dict[str, Any]] = None,
    ) -> int:
        """Count records matching the optional filters."""
        stmt = select(func.count()).select_from(self.model_class)
        stmt = self._apply_filters(stmt, filters)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def restore(
        self,
        db: AsyncSession,
        id: Any,
    ) -> Optional[ModelT]:
        """Restore a soft-deleted record.

        Clears ``is_deleted`` and ``deleted_at``.  Returns ``None`` if the
        record does not exist or the model does not support soft-delete.
        """
        db_obj = await self.get(db, id, include_deleted=True)
        if db_obj is None or not hasattr(db_obj, 'is_deleted'):
            return None

        if not db_obj.is_deleted:
            return db_obj  # Already active — no-op

        db_obj.is_deleted = False
        db_obj.deleted_at = None
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
