"""
澧ㄧ伒 (Moling) 鈥?Subscription (璁㈤槄) Router.

Endpoints for subscription plans and checkout (basic stub).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.subscription import Plan, UserSubscription
from app.schemas.subscription import PlanResp, CreateSubscriptionReq, SubscriptionResp

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


@router.post("", response_model=SubscriptionResp, status_code=201)
async def create_subscription(
    req: CreateSubscriptionReq,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResp:
    """Create a new subscription for the current user."""
    # Check if user already has an active subscription
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == int(current_user["id"]),
            UserSubscription.status.in_(["active", "trialing"]),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("User already has an active subscription")

    # Get plan
    result = await db.execute(
        select(Plan).where(Plan.id == req.plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise ValueError("Plan not found")

    # Create subscription
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    if plan.interval == "month":
        end_date = now + timedelta(days=30)
    elif plan.interval == "year":
        end_date = now + timedelta(days=365)
    else:
        end_date = now + timedelta(days=30)

    subscription = UserSubscription(
        user_id=int(current_user["id"]),
        plan_id=req.plan_id,
        status="active",
        start_date=now,
        end_date=end_date,
        auto_renew=req.auto_renew if hasattr(req, 'auto_renew') else True,
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return SubscriptionResp.model_validate(subscription)


@router.get("/current", response_model=dict)
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user's active subscription."""
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == int(current_user["id"]),
            UserSubscription.status.in_(["active", "trialing"]),
        ).order_by(UserSubscription.created_at.desc())
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return {
            "has_subscription": False,
            "subscription": None,
        }

    return {
        "has_subscription": True,
        "subscription": SubscriptionResp.model_validate(subscription),
    }


@router.get("/payment-history")
async def get_payment_history(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取用户支付历史记录。"""
    return [
        # 示例: 先返回空数据，后续接入数据库
    ]
