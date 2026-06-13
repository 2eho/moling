"""墨灵 (Moling) — Declarative Base & Mixins.

All ORM models inherit from ``BaseModel`` which combines:
- The SQLAlchemy ``DeclarativeBase``
- A UUID primary key (``id``)
- ``created_at`` / ``updated_at`` timestamps
"""

from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import DateTime, String, func
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
