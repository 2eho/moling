"""墨灵 (Moling) — Notification (通知) ORM Model."""

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Notification(Base, TimestampMixin, SoftDeleteMixin):
    """A notification for a user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收通知的用户 ID",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="通知类型: phase4_failed / phase4_stuck / health_alert / payment_success / payment_failed / system_announcement",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="通知标题",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="通知正文",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否已读",
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="关联项目 ID（可选）",
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.type!r}>"
