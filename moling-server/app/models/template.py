"""墨灵 (Moling) — Template ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Template(BaseModel):
    """A project template for writing."""

    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="模板名称",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="模板描述",
    )
    genre: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="适用题材",
    )
    structure: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="模板结构 (JSON)",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者用户 ID",
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} name={self.name!r}>"
