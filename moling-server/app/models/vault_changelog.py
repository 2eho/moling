"""墨灵 (Moling) — Vault Changelog (四库变更日志) ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class VaultChangelog(BaseModel):
    """四库变更日志 - 追溯四库变更历史.

    记录每次 Phase 4 收纳后对四库的变更操作。
    """

    __tablename__ = "vault_changelogs"

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联章节 ID",
    )
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="变更类型: add / update / delete / archive",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="实体类型: character / timeline / plot_promise / world / secret",
    )
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="实体 ID (UUID)",
    )
    field_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="变更的字段名",
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="旧值",
    )
    new_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="新值",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="变更原因 (LLM 提取的变更说明)",
    )
    meta_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="额外元数据",
    )

    # ---- Relationships ----
    project = relationship("Project", back_populates="vault_changelogs", lazy="selectin")
    chapter = relationship("Chapter", back_populates="vault_changelogs", lazy="selectin")

    def __repr__(self) -> str:
        return f"<VaultChangelog id={self.id} type={self.change_type} entity={self.entity_type}>"
