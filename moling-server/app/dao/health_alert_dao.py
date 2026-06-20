"""墨灵 (Moling) — Health Alert DAO."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.base_dao import BaseDAO
from app.models.health_alert import HealthAlert


class HealthAlertDAO(BaseDAO[HealthAlert]):
    """Data access for HealthAlert (健康检查告警)."""

    def __init__(self) -> None:
        super().__init__(HealthAlert)

    # ---- Read ----

    async def list_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[HealthAlert]:
        """List all health alerts for a project, newest first."""
        stmt = (
            select(HealthAlert)
            .where(HealthAlert.project_id == project_id)
            .order_by(HealthAlert.id.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_active_by_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[HealthAlert]:
        """List active (unresolved) health alerts for a project."""
        stmt = (
            select(HealthAlert)
            .where(
                HealthAlert.project_id == project_id,
                HealthAlert.is_active == True,
            )
            .order_by(HealthAlert.id.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_severity(
        self,
        db: AsyncSession,
        project_id: int,
        severity: str,
    ) -> list[HealthAlert]:
        """List alerts filtered by severity (info / warning / critical)."""
        stmt = (
            select(HealthAlert)
            .where(
                HealthAlert.project_id == project_id,
                HealthAlert.severity == severity,
            )
            .order_by(HealthAlert.id.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Write ----

    async def create_alert(
        self,
        db: AsyncSession,
        obj_in: dict,
    ) -> HealthAlert:
        """Create a new health alert."""
        alert = HealthAlert(**obj_in)
        db.add(alert)
        await db.flush()
        await db.refresh(alert)
        return alert

    async def resolve_alerts_by_rule(
        self,
        db: AsyncSession,
        project_id: int,
        rule: str,
    ) -> int:
        """Mark all active alerts for a given rule as resolved. Returns update count."""
        stmt = (
            update(HealthAlert)
            .where(
                HealthAlert.project_id == project_id,
                HealthAlert.rule == rule,
                HealthAlert.is_active == True,
            )
            .values(is_active=False)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def update_checked_at(
        self,
        db: AsyncSession,
        alert_id: int,
    ) -> None:
        """Update the checked_at timestamp for a specific alert."""
        stmt = (
            update(HealthAlert)
            .where(HealthAlert.id == alert_id)
            .values(checked_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        await db.flush()


# Singleton
health_alert_dao = HealthAlertDAO()
