"""墨灵 (Moling) — Chapter ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class Chapter(BaseModel, SoftDeleteMixin):
    """A single chapter within a project."""

    __tablename__ = "chapters"

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="章节标题",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="章节正文内容",
    )
    chapter_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="章节序号 (从 1 开始)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
        comment="章节状态: draft / generating / completed / revised",
    )
    phase4_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="四阶段精修状态: pending / running / done / failed / skipped",
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="本章字数",
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="确认收纳时间",
    )
    # B3: 生成相关字段
    used_card_ids: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="使用的卡片 ID 列表",
    )
    generation_mode: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="生成模式: 单卡 / 双卡 / 全选 / 自选+输入",
    )
    generation_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="生成提示词",
    )
    generation_weights: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="卡片权重配置",
    )
    generation_result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="生成结果 (LLM 返回的正文)",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="重试次数",
    )
    generation_duration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="生成时长 (秒)",
    )

    # ---- Relationships ----
    project = relationship("Project", back_populates="chapters", lazy="selectin")
    dynamic_layer = relationship("DynamicLayer", back_populates="chapter", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} project={self.project_id} #{self.chapter_number}>"
