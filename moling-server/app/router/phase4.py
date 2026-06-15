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


@router.get("/chapters/{chapter_id}/suggestions", response_model=Phase4SuggestionResp)
async def get_suggestions(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4SuggestionResp:
    """获取章节的精修建议。"""
    result = await phase4_service.get_suggestions(db, chapter_id)
    return result


@router.get("/suggestions/{chapter_id}", response_model=Phase4SuggestionResp, deprecated=True, tags=["phase4 (deprecated)"])
async def get_suggestions_legacy(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4SuggestionResp:
    """获取章节的精修建议（弃用路径，请使用 /chapters/{cid}/suggestions）。"""
    import warnings
    warnings.warn("Use /phase4/chapters/{cid}/suggestions instead", DeprecationWarning)
    return await phase4_service.get_suggestions(db, chapter_id)


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


@router.get("/pending-reviews", status_code=200)
async def get_pending_reviews(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取待审核的精修建议列表。"""
    # MVP 实现：返回空列表（等 service 层完善）
    return {
        "reviews": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


@router.post("/reviews/{review_id}/approve", status_code=200)
async def approve_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """批准精修建议。"""
    # MVP 实现：返回确认（等 service 层完善）
    return {"approved": True, "review_id": review_id}


@router.post("/reviews/{review_id}/reject", status_code=200)
async def reject_review(
    review_id: int,
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """拒绝精修建议并给出理由。"""
    reason = req.get("reason", "")
    return {"rejected": True, "review_id": review_id, "reason": reason}
