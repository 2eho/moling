"""墨灵 (Moling) — Health Alert (健康检查告警) ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class HealthAlert(Base, TimestampMixin):
    """A health / consistency alert for a project's narrative."""

    __tablename__ = "health_alerts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    rule: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="触发的规则名称",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="告警标题",
    )
    detail: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="告警详细信息",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="严重程度: info / warning / critical",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否活跃 (未解决)",
    )
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后检查时间",
    )

    def __repr__(self) -> str:
        return f"<HealthAlert id={self.id} rule={self.rule!r} severity={self.severity}>"
