"""墨灵 (Moling) — Subscription (订阅) Pydantic Schemas."""

from __future__ import annotations

from pydantic import BaseModel


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
