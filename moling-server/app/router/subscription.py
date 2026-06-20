"""
墨灵 (Moling) — Subscription (订阅) Router.

Endpoints for subscription plans and checkout (basic stub).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.dao.subscription_dao import plan_dao, user_subscription_dao
from app.errors import NotFoundError, ConflictError
from app.models.subscription import UserSubscription
from app.schemas.subscription import PlanResp, CreateSubscriptionReq, SubscriptionResp
from app.models.user import User

router = APIRouter()


@router.get("/plans", response_model=list[PlanResp])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanResp]:
    """List all active subscription plans."""
    plans = await plan_dao.get_active_plans(db)
    return [PlanResp.model_validate(p) for p in plans]


@router.post("/create-checkout", response_model=dict)
async def create_checkout(
    plan_id: int = Query(..., description="订阅方案 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """创建支付结算会话，返回合理的占位数据。"""
    plan = await plan_dao.get(db, plan_id)

    if not plan:
        raise NotFoundError(detail="Plan not found")

    checkout_id = str(uuid.uuid4())

    return {
        "checkout_id": checkout_id,
        "checkout_url": f"/checkout/{checkout_id}",
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "price": plan.price,
            "currency": plan.currency,
            "interval": plan.interval,
        },
        "status": "pending",
        "message": "请前往支付页面完成付款",
    }


@router.post("", response_model=SubscriptionResp, status_code=201)
async def create_subscription(
    req: CreateSubscriptionReq,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResp:
    """Create a new subscription for the current user."""
    user_id = str(current_user["id"])

    # Check if user already has an active subscription
    existing = await user_subscription_dao.get_by_user(db, user_id)
    if existing:
        raise ConflictError(detail="User already has an active subscription")

    # Get plan
    plan = await plan_dao.get(db, req.plan_id)
    if not plan:
        raise NotFoundError(detail="Plan not found")

    # Calculate end date
    now = datetime.now(timezone.utc)
    if plan.interval == "month":
        end_date = now + timedelta(days=30)
    elif plan.interval == "year":
        end_date = now + timedelta(days=365)
    else:
        end_date = now + timedelta(days=30)

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=str(req.plan_id),
        status="active",
        start_date=now,
        end_date=end_date,
        auto_renew=req.auto_renew if hasattr(req, "auto_renew") else True,
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return SubscriptionResp.model_validate(subscription)


@router.get("/current", response_model=dict)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user's active subscription."""
    user_id = str(current_user["id"])
    subscription = await user_subscription_dao.get_by_user(db, user_id)

    if not subscription:
        return {
            "has_subscription": False,
            "subscription": None,
        }

    return {
        "has_subscription": True,
        "subscription": SubscriptionResp.model_validate(subscription),
    }


@router.get("/payment-history", response_model=dict)
async def get_payment_history(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取用户支付历史记录。"""
    user_id = str(current_user["id"])
    skip = (page - 1) * page_size

    subscriptions = await user_subscription_dao.list_by_user(
        db, user_id, skip=skip, limit=page_size
    )
    total = await user_subscription_dao.count(db, filters={"user_id": user_id})

    items = []
    for sub in subscriptions:
        items.append({
            "id": sub.id,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "amount": 0.0,
            "currency": "CNY",
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "auto_renew": sub.auto_renew if hasattr(sub, "auto_renew") else True,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
