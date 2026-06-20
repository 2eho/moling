"""墨灵 (Moling) — Vault Timeline (时间线) ORM Model."""

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class VaultTimeline(BaseModel, SoftDeleteMixin):
    """A single event / entry in the project's timeline."""

    __tablename__ = "vault_timeline"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    # B6: 补充缺失字段
    day: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="绝对时间线天数",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="事件标题",
    )
    precedes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="前驱事件 ID 列表",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="置信度 (0-1)",
    )
    source_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="来源章节号",
    )
    importance: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="重要性: critical / major / minor",
    )
    # 原有字段
    chapter_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="事件发生的章节号",
    )
    event: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="事件摘要",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="事件详细描述",
    )
    is_key_event: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否关键事件",
    )
    impact: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="事件影响描述",
    )
    characters_involved: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="涉及角色名列表",
    )

    def __repr__(self) -> str:
        return f"<VaultTimeline id={self.id} ch#{self.chapter_number} event={self.event!r}>"
