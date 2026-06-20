"""墨灵 (Moling) — User ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class User(BaseModel, SoftDeleteMixin):
    """Platform user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="登录邮箱",
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="用户昵称",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt 哈希后的密码",
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="头像 URL",
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="个人简介",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="用户状态: active / disabled / admin",
    )

    settings: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=lambda: {},
        nullable=True,
        comment="用户设置 (JSONB)",
    )
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="密码重置令牌",
    )
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="密码重置令牌过期时间",
    )

    # ---- Relationships ----
    projects = relationship("Project", back_populates="owner", lazy="selectin")
    generation_tasks = relationship("GenerationTask", back_populates="user", lazy="selectin")
    draw_histories = relationship("DrawHistory", back_populates="user", lazy="selectin")
    notifications = relationship("Notification", back_populates="user", lazy="selectin")
    templates = relationship("Template", back_populates="user", lazy="selectin")
    user_subscriptions = relationship("UserSubscription", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
