"""System configuration model — stores key-value settings for the admin panel."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemConfig(Base):
    """System-wide configuration key-value store.

    Used for admin-managed settings like LLM API keys, model selection, etc.
    Values are encrypted/stored server-side, never exposed to client browsers.
    """

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(
        String(128), primary_key=True, comment="配置键名"
    )
    value: Mapped[str] = mapped_column(
        Text, default="", comment="配置值（加密存储）"
    )
    description: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment="配置说明"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
