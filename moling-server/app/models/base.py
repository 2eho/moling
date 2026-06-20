"""墨灵 (Moling) — Declarative Base & Mixins.

All ORM models inherit from ``BaseModel`` which combines:
- The SQLAlchemy ``DeclarativeBase``
- A UUID primary key (``id``)
- ``created_at`` / ``updated_at`` timestamps

Optional mixins:
- ``SoftDeleteMixin`` — 软删除支持（is_deleted + deleted_at）
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for metadata sharing (used by Alembic)."""

    pass


class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Abstract base model with a UUID primary key."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class SoftDeleteMixin:
    """Mixin that adds soft-delete support.

    模型继承此 Mixin 后，BaseDAO 的 delete 方法将自动采用软删除：
    - 设置 ``is_deleted = True`` 和 ``deleted_at = now()``
    - get_multi 默认过滤已删除记录
    - 提供 restore 方法恢复已删除记录
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="软删除标记",
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间",
    )
