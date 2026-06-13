"""墨灵 (Moling) — Phase 4 (四阶段精修) API 路由。

实现获取精修建议、应用精修、查询任务状态等端点。
可能需要调用 LLM 服务。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.phase4_service import phase4_service
from app.schemas.phase4 import Phase4SuggestionResp, ApplyPhase4Req, Phase4TaskResp

router = APIRouter()


@router.get("/suggestions/{chapter_id}", response_model=Phase4SuggestionResp)
async def get_suggestions(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4SuggestionResp:
    """获取章节的精修建议。"""
    result = await phase4_service.get_suggestions(db, chapter_id)
    return result


@router.post("/apply", status_code=200)
async def apply_suggestions(
    req: ApplyPhase4Req,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """应用精修建议到章节。"""
    result = await phase4_service.apply_suggestions(db, req)
    return result


@router.get("/tasks/{task_id}", response_model=Phase4TaskResp)
async def get_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4TaskResp:
    """查询 Phase 4 任务状态。"""
    result = await phase4_service.get_task_status(db, task_id)
    return result


@router.get("/chapters/{chapter_id}/tasks", response_model=list[Phase4TaskResp])
async def list_chapter_tasks(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[Phase4TaskResp]:
    """查询章节的所有 Phase 4 任务。"""
    result = await phase4_service.list_chapter_tasks(db, chapter_id)
    return result


@router.get("/projects/{project_id}/tasks", response_model=list[Phase4TaskResp])
async def list_project_tasks(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[Phase4TaskResp]:
    """查询项目的所有 Phase 4 任务。"""
    result = await phase4_service.list_project_tasks(db, project_id)
    return result
