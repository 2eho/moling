"""墨灵 (Moling) — Secret (秘密矩阵) ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class Secret(BaseModel, SoftDeleteMixin):
    """A secret / hidden truth in the project's narrative."""

    __tablename__ = "secrets"

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="秘密描述",
    )
    known_by: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [],
        comment="已知晓该秘密的角色名列表",
    )
    unknown_to: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [],
        comment="不知晓该秘密的角色名列表",
    )
    secrecy_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="hidden",
        comment="保密层级: hidden / partial / revealed",
    )
    created_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="秘密创建时的章节号",
    )
    debt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="叙事债务值",
    )

    def __repr__(self) -> str:
        return f"<Secret id={self.id} project={self.project_id}>"
