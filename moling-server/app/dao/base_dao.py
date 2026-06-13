"""澧ㄧ伒 (Moling) 鈥?Generic Base DAO with CRUD operations.

Uses SQLAlchemy 2.0 ``Mapped`` style and async sessions.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel as MolingModel

ModelT = TypeVar("ModelT", bound=MolingModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseDAO(Generic[ModelT]):
    """Generic CRUD data access object.

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

        Supports: ``{"field": value}`` 鈫?``WHERE field = value``
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
    ) -> Optional[ModelT]:
        """Retrieve a single record by primary key."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await db.execute(stmt)
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
    ) -> list[ModelT]:
        """Retrieve a paginated list of records with optional filters."""
        stmt = select(self.model_class)
        stmt = self._apply_filters(stmt, filters)

        if order_by:
            column = getattr(self.model_class, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            # UUID 主键不支持 desc() 排序，改用 created_at
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
    ) -> Optional[ModelT]:
        """Delete a record by primary key and return it (or None if not found)."""
        db_obj = await self.get(db, id)
        if db_obj:
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
