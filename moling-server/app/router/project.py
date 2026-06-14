"""墨灵 (Moling) — Project API Router.

Provides endpoints for project CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.project import CreateProjectReq, ProjectResp, ProjectStatsResp, UpdateProjectReq
from app.schemas.health import HealthAlertResp
from app.service import project_service

router = APIRouter(tags=["projects"])


@router.post("", response_model=ProjectResp, status_code=201)
async def create_project(
    req: CreateProjectReq,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Create a new project."""
    return await project_service.create_project(db, current_user.id, req)


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """List projects with pagination."""
    return await project_service.list_projects(db, current_user.id, page, page_size, status)


@router.get("/stats", response_model=ProjectStatsResp)
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectStatsResp:
    """Get project statistics for current user."""
    return await project_service.get_project_stats(db, current_user.id)


@router.get("/{project_id}", response_model=ProjectResp)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Get single project by ID."""
    return await project_service.get_project(db, current_user.id, project_id)


@router.put("/{project_id}", response_model=ProjectResp)
async def update_project(
    project_id: int,
    req: UpdateProjectReq,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Update project by ID."""
    return await project_service.update_project(db, current_user.id, project_id, req)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete project by ID."""
    await project_service.delete_project(db, current_user.id, project_id)


@router.get("/{project_id}/suggestions", response_model=dict)
async def get_project_suggestions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取项目的创作建议（基于四库分析）。"""
    suggestions = await project_service.get_suggestions(
        db, current_user.id, project_id
    )
    return suggestions


# ============ Project Secrets ============

@router.get("/{project_id}/secrets", response_model=list[dict])
async def list_project_secrets(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """获取项目的秘密矩阵列表。"""
    from app.service.secret_service import secret_service
    return await secret_service.list_secrets(db, project_id)


@router.get("/{project_id}/secrets/{role}", response_model=dict)
async def get_project_secrets_by_role(
    project_id: int,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """按角色查询秘密。"""
    from app.service.secret_service import secret_service
    return await secret_service.get_secrets_by_role(db, project_id, role)


@router.put("/{project_id}/secrets/{secret_id}", response_model=dict)
async def update_project_secret(
    project_id: int,
    secret_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """更新项目的秘密。"""
    from app.service.secret_service import secret_service
    return await secret_service.update_secret(db, project_id, secret_id, data)


# ============ Project Cards History ============

@router.get("/{project_id}/cards/history", response_model=list[dict])
async def get_project_card_history(
    project_id: int,
    chapter_id: Optional[int] = Query(None, description="按章节过滤"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """获取项目的抽卡历史。"""
    from app.service.card_service import card_service
    return await card_service.get_draw_history(db, current_user.id, project_id, chapter_id)


# ============ Project Health ============

@router.get("/{project_id}/health", response_model=dict)
async def get_project_health(
    project_id: int,
    active_only: bool = Query(default=True, description="仅返回活跃告警"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取项目的健康告警列表。"""
    from app.service.health_service import health_service
    alerts = await health_service.get_alerts(db, project_id, active_only)
    from app.schemas.health import HealthAlertResp
    return {
        "success": True,
        "alerts": [HealthAlertResp.model_validate(a) for a in alerts],
    }


@router.post("/{project_id}/health/refresh", response_model=dict)
async def refresh_project_health(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """手动触发项目的健康检查。"""
    from app.service.health_service import health_service
    result = await health_service.run_check(db, project_id)
    return result
