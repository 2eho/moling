"""墨灵 (Moling) — Subscription (订阅) ORM Model."""

from sqlalchemy import Boolean, Float, JSON, String
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
