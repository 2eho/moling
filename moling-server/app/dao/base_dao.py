"""墨灵 (Moling) — Generic Base DAO with CRUD operations (async).

DAO 方法命名约定 (R3 架构加固):
- get(id) — 按主键获取单条记录
- get_sync(id) — 同步版 get（用于 Celery worker）
- get_multi(*, skip, limit, filters, order_by) — 分页列表查询（offset/limit）
- list_cursor(*, cursor, cursor_field, limit, filters, order) — 游标分页列表查询
- count(filters) — 按条件计数
- create(obj_in) — 创建单条记录（flush, 不 commit）
- update(db_obj, obj_in) — 部分更新单条记录（flush, 不 commit）
- delete(id, soft) — 软删除/物理删除单条记录
- restore(id) — 恢复软删除记录
- batch_create(data_list) — 批量创建（子类按需实现）
- get_by_*(value) — 按唯一键获取单条（子类实现）
- list_by_*(value, *, offset, limit) — 按条件列表查询（子类实现）
- count_by_*(value) — 按条件计数（子类实现）

DAO 层契约:
- 禁止 DAO 内部 commit() — 事务由调用方（Service/Router）管理
- 禁止 DAO 内部创建 Session/Engine — 接受 db 参数
- 所有 DAO 方法必须有 try/except 并记录日志
- 子类 DAO 使用模块级单例 (xxx_dao = XxxDAO())，不使用类级单例
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

from app.errors import AppError, ErrorCode
from app.models.base import BaseModel as MolingModel

logger = logging.getLogger(__name__)

# 全局默认最大查询数量，防止单次查询拉取过多数据
DEFAULT_MAX_LIMIT = 500

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
        try:
            stmt = select(self.model_class).where(self.model_class.id == id)

            if not include_deleted and hasattr(self.model_class, 'is_deleted'):
                stmt = stmt.where(self.model_class.is_deleted == False)

            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"DAO get({id}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

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
        The ``limit`` parameter is clamped to ``DEFAULT_MAX_LIMIT`` (500).
        """
        # 上限钳制，防止一次性拉取过多数据
        limit = min(limit, DEFAULT_MAX_LIMIT)

        try:
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
        except SQLAlchemyError as e:
            logger.error(f"DAO get_multi({self.model_class.__name__}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaT | dict[str, Any],
    ) -> ModelT:
        """Create a new record from a Pydantic schema or plain dict."""
        try:
            if isinstance(obj_in, BaseModel):
                create_data = obj_in.model_dump(exclude_unset=True)
            else:
                create_data = obj_in

            db_obj = self.model_class(**create_data)
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"DAO create({self.model_class.__name__}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelT,
        obj_in: UpdateSchemaT | dict[str, Any],
    ) -> ModelT:
        """Update an existing record (partial update)."""
        try:
            if isinstance(obj_in, BaseModel):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field, value in update_data.items():
                setattr(db_obj, field, value)

            await db.flush()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"DAO update({self.model_class.__name__}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

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
        try:
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
        except SQLAlchemyError as e:
            logger.error(f"DAO delete({id}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[dict[str, Any]] = None,
        *,
        include_deleted: bool = False,
    ) -> int:
        """Count records matching the optional filters.

        By default excludes soft-deleted records when the model supports it.
        """
        try:
            stmt = select(func.count()).select_from(self.model_class)

            if not include_deleted and hasattr(self.model_class, 'is_deleted'):
                stmt = stmt.where(self.model_class.is_deleted == False)

            stmt = self._apply_filters(stmt, filters)
            result = await db.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            logger.error(f"DAO count({self.model_class.__name__}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def restore(
        self,
        db: AsyncSession,
        id: Any,
    ) -> Optional[ModelT]:
        """Restore a soft-deleted record.

        Clears ``is_deleted`` and ``deleted_at``.  Returns ``None`` if the
        record does not exist or the model does not support soft-delete.
        """
        try:
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
        except SQLAlchemyError as e:
            logger.error(f"DAO restore({id}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def list_cursor(
        self,
        db: AsyncSession,
        *,
        cursor: Any = None,
        cursor_field: str = "id",
        limit: int = 50,
        filters: dict[str, Any] | None = None,
        order: str = "desc",
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], Any | None]:
        """游标分页查询，返回 (items, next_cursor)。

        Args:
            cursor: 上一页最后一条的 cursor_field 值，None 表示第一页
            cursor_field: 用作游标的字段名（默认 "id"）
            limit: 每页条数（最大 200，默认 50）
            filters: 额外的等值过滤条件
            order: "asc" 或 "desc"
            include_deleted: 是否包含软删除记录

        Returns:
            (items, next_cursor) — next_cursor 为 None 表示没有更多数据
        """
        _CURSOR_MAX_LIMIT = 200
        limit = min(max(limit, 1), _CURSOR_MAX_LIMIT)

        try:
            column = getattr(self.model_class, cursor_field, None)
            if column is None:
                raise ValueError(f"Model {self.model_class.__name__} has no field '{cursor_field}'")

            stmt = select(self.model_class)

            if not include_deleted and hasattr(self.model_class, 'is_deleted'):
                stmt = stmt.where(self.model_class.is_deleted == False)

            stmt = self._apply_filters(stmt, filters)

            # 游标条件
            if cursor is not None:
                if order == "desc":
                    stmt = stmt.where(column < cursor)
                else:
                    stmt = stmt.where(column > cursor)

            # 排序
            stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())

            # 多取一条判断是否有下一页
            stmt = stmt.limit(limit + 1)

            result = await db.execute(stmt)
            rows = list(result.scalars().all())

            has_more = len(rows) > limit
            items = rows[:limit]
            next_cursor = getattr(items[-1], cursor_field) if has_more and items else None

            return items, next_cursor

        except (SQLAlchemyError, ValueError) as e:
            logger.error(f"DAO list_cursor({self.model_class.__name__}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))
