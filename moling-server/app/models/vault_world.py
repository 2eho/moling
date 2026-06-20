"""墨灵 (Moling) — Vault World (世界观条目) ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class VaultWorld(BaseModel, SoftDeleteMixin):
    """A single term / rule entry in the project's world-building vault."""

    __tablename__ = "vault_world"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="术语/条目名称",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="条目详细描述",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="类别: geography / magic / technology / culture / history / rule / other",
    )
    # B9: 补充缺失字段
    related_entities: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="相关实体列表",
    )
    source_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="来源章节号",
    )
    # B9: 使用 constraint 字段而非 rules[]
    constraint: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="约束/规则描述",
    )
    reference_chapters: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="引用章节号列表",
    )

    def __repr__(self) -> str:
        return f"<VaultWorld id={self.id} name={self.name!r}>"
