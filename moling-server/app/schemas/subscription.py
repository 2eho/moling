"""墨灵 (Moling) — Subscription (订阅) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanResp(BaseModel):
    """Plan detail response."""

    id: int
    name: str
    price: float
    currency: str
    interval: str
    features: dict
    is_active: bool

    model_config = {"from_attributes": True}


class CreateSubscriptionReq(BaseModel):
    """Create subscription request."""

    plan_id: int = Field(..., description="订阅方案 ID")
    auto_renew: bool = Field(default=True, description="是否自动续费")


class SubscriptionResp(BaseModel):
    """Subscription detail response."""

    id: int
    user_id: int
    plan_id: int
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_renew: bool
    created_at: datetime

    model_config = {"from_attributes": True}
