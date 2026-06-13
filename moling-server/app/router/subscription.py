"""
澧ㄧ伒 (Moling) 鈥?Subscription (璁㈤槄) Router.

Endpoints for subscription plans and checkout (basic stub).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.subscription import Plan
from app.schemas.subscription import PlanResp

router = APIRouter()


@router.get("/plans", response_model=list[PlanResp])
async def list_plans(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanResp]:
    """List all active subscription plans."""
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.price)
    )
    plans = result.scalars().all()
    return [PlanResp.model_validate(p) for p in plans]


@router.post("/create-checkout", response_model=dict)
async def create_checkout(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Stub endpoint for creating a checkout session (coming soon)."""
    return {
        "checkout_url": None,
        "message": "Coming soon",
    }
