"""墨灵 (Moling) — Project ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Project(BaseModel):
    """A novel / writing project owned by a user."""

    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户 ID",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="作品标题",
    )
    author: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="作者署名",
    )
    genre: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="作品类型/题材",
    )
    cover_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="封面 URL",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="作品描述",
    )
    method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="创作方法: 卡牌组合 / 大纲导出 / 自由创作",
    )
    chapter_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="章节数量",
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="当前总字数",
    )
    target_words: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="目标总字数",
    )
    frequency: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="更新频率: daily / weekly / custom",
    )
    style: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="写作风格",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
        comment="项目状态: draft / active / completed / archived",
    )
    creation_mode: Mapped[str] = mapped_column(
        String(20),
        default="from_scratch",
        nullable=False,
        comment="创建模式: from_scratch / from_template",
    )
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="使用的模板 ID (预留)",
    )

    # ---- Relationships ----
    owner = relationship("User", back_populates="projects", lazy="selectin")
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Project id={self.id} title={self.title!r}>"
