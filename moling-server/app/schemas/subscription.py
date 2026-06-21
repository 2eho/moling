"""墨灵 (Moling) — Subscription (订阅) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlanResp(BaseModel):
    """Plan detail response."""

    id: str  # String(36) UUID — matches Plan model PK
    name: str
    price: float
    currency: str
    interval: str
    features: dict
    is_active: bool

    model_config = {"from_attributes": True}


class CreateSubscriptionReq(BaseModel):
    """Create subscription request."""

    plan_id: str = Field(..., description="订阅方案 ID (UUID)")
    auto_renew: bool = Field(default=True, description="是否自动续费")


class SubscriptionResp(BaseModel):
    """Subscription detail response."""

    id: str
    user_id: str
    plan_id: str
    status: str
    start_date: datetime
    end_date: datetime | None = None
    auto_renew: bool
    created_at: datetime

    model_config = {"from_attributes": True}
