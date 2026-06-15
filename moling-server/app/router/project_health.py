"""墨灵 (Moling) — Project Health API Router.

提供项目级健康告警端点：
- GET /{project_id}/health - 获取项目健康告警
- POST /{project_id}/health/refresh - 刷新项目健康告警
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.dependencies import get_db, get_current_user
from app.schemas.health import HealthCheckResp, HealthAlertItem
from app.service import health_service
from app.errors import NotFoundError, ErrorCode, AppError

router = APIRouter(tags=["project-health"])


@router.get("/{project_id}/health", response_model=HealthCheckResp)
async def get_project_health(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> HealthCheckResp:
    """获取项目健康告警。

    返回项目的健康告警列表（R1/R2/R3规则检查结果）。

    Args:
        project_id: 项目 ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        HealthCheckResp: 包含告警列表和检查时间
    """
    # 验证项目存在且属于当前用户
    from app.dao import project_dao
    project = await project_dao.get(db, project_id)
    if project is None:
        raise NotFoundError(
            error_code=ErrorCode.PROJECT_NOT_FOUND,
            detail="Project not found",
        )
    if project.user_id != current_user.id:
        raise AppError(
            error_code=ErrorCode.PROJECT_ACCESS_DENIED,
            detail="Not authorized to access this project",
        )

    # 获取活跃告警
    alerts = await health_service.get_alerts(db, project_id, active_only=True)

    # 转换为响应格式
    alert_items = []
    latest_checked_at = None
    for alert in alerts:
        alert_items.append(HealthAlertItem(
            rule=alert.rule,
            title=alert.title,
            detail=alert.detail,
        ))
        if alert.checked_at:
            if latest_checked_at is None or alert.checked_at > latest_checked_at:
                latest_checked_at = alert.checked_at

    # 如果没有告警或没有检查时间，使用当前时间
    if latest_checked_at is None:
        latest_checked_at = datetime.now(timezone.utc)

    return HealthCheckResp(
        alerts=alert_items,
        checked_at=latest_checked_at,
    )


@router.post("/{project_id}/health/refresh", response_model=HealthCheckResp)
async def refresh_project_health(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> HealthCheckResp:
    """刷新项目健康告警。

    运行所有健康检查（R1/R2/R3）并返回最新的告警列表。

    Args:
        project_id: 项目 ID
        db: 数据库会话
        current_user: 当前认证用户

    Returns:
        HealthCheckResp: 包含最新告警列表和检查时间
    """
    # 运行健康检查
    result = await health_service.run_health_check(
        db, str(current_user.id), project_id
    )

    # 转换为响应格式
    alert_items = []
    for alert in result.get("alerts", []):
        alert_items.append(HealthAlertItem(
            rule=alert.get("rule", ""),
            title=alert.get("title", ""),
            detail=alert.get("detail", ""),
        ))

    checked_at = datetime.now(timezone.utc)
    if result.get("checked_at"):
        try:
            checked_at = datetime.fromisoformat(result["checked_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    return HealthCheckResp(
        alerts=alert_items,
        checked_at=checked_at,
    )
