"""墨灵 (Moling) — Subscription (订阅) ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Plan(BaseModel):
    """A subscription plan / pricing tier."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="套餐名称",
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="价格",
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="CNY",
        comment="货币单位",
    )
    interval: Mapped[str] = mapped_column(
        String(20),
        default="month",
        comment="计费周期: month / year",
    )
    features: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="套餐功能列表",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否上架",
    )

    def __repr__(self) -> str:
        return f"<Plan id={self.id} name={self.name!r}>"


class UserSubscription(BaseModel):
    """A user's subscription record."""

    __tablename__ = "user_subscriptions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户 ID",
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="方案 ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        comment="状态: active / trialing / canceled / expired",
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="订阅开始时间",
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="订阅结束时间",
    )
    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否自动续费",
    )

    def __repr__(self) -> str:
        return f"<UserSubscription id={self.id} user_id={self.user_id}>"
