"""Subscription DAO — Plan and UserSubscription data access."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.subscription import Plan, UserSubscription


class PlanDAO(BaseDAO[Plan]):
    """Data access for subscription plans."""

    def __init__(self) -> None:
        super().__init__(Plan)

    async def get_active_plans(
        self,
        db: AsyncSession,
    ) -> list[Plan]:
        """List all active (published) plans ordered by price."""
        stmt = (
            select(Plan)
            .where(Plan.is_active == True)  # noqa: E712
            .order_by(Plan.price)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


class UserSubscriptionDAO(BaseDAO[UserSubscription]):
    """Data access for user subscriptions."""

    def __init__(self) -> None:
        super().__init(UserSubscription)

    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> Optional[UserSubscription]:
        """Get the active subscription for a user."""
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == "active",
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_plan(
        self,
        db: AsyncSession,
        user_id: str,
        plan_id: str,
    ) -> Optional[UserSubscription]:
        """Get a specific user-plan subscription record."""
        stmt = select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.plan_id == plan_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[UserSubscription]:
        """List all subscriptions for a user, newest first."""
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .order_by(UserSubscription.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Singleton instances
plan_dao = PlanDAO()
user_subscription_dao = UserSubscriptionDAO()
