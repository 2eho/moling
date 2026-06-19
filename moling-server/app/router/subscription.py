"""
澧ㄧ伒 (Moling) 鈥?Subscription (璁㈤槄) Router.

Endpoints for subscription plans and checkout (basic stub).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
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
    plan_id: int = Query(..., description="订阅方案 ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """创建支付结算会话，返回合理的占位数据。"""
    # 查询方案信息
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # 生成占位 checkout 数据
    import uuid
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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResp:
    """Create a new subscription for the current user."""
    # Check if user already has an active subscription
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == str(current_user.id),
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
        user_id=str(current_user.id),
        plan_id=str(req.plan_id),
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
            UserSubscription.user_id == str(current_user.id),
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


@router.get("/payment-history", response_model=dict)
async def get_payment_history(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取用户支付历史记录。"""
    # 查询数据库中的订阅记录作为支付历史
    result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == str(current_user.id))
        .order_by(UserSubscription.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    subscriptions = result.scalars().all()

    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(UserSubscription)
        .where(UserSubscription.user_id == str(current_user.id))
    )
    total = count_result.scalar() or 0

    items = []
    for sub in subscriptions:
        items.append({
            "id": sub.id,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "amount": 0.0,  # 金额暂不追踪，后续对接支付网关
            "currency": "CNY",
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "auto_renew": sub.auto_renew if hasattr(sub, 'auto_renew') else True,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
