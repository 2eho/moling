"""墨灵 (Moling) — Phase 4 (四阶段精修) API 路由。

实现获取精修建议、应用精修、查询任务状态等端点。
可能需要调用 LLM 服务。
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.errors import NotFoundError, ForbiddenError
from app.service.phase4_service import phase4_service
from app.schemas.phase4 import Phase4SuggestionResp, ApplyPhase4Req, Phase4TaskResp, RejectReviewReq
from app.models.phase4_task import Phase4State
from app.dao.phase4_dao import phase4_dao
from app.dao import project_dao

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


# 兼容层：旧路径（已弃用）
@router.get("/suggestions/{chapter_id}", deprecated=True)
async def get_suggestions_deprecated(
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Phase4SuggestionResp:
    """【已弃用】请使用 /chapters/{chapter_id}/suggestions。"""
    import warnings
    warnings.warn("路径 /suggestions/{chapter_id} 已弃用，请使用 /chapters/{chapter_id}/suggestions", DeprecationWarning)
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


@router.get("/pending-reviews", status_code=200)
async def get_pending_reviews(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取待审核的精修建议列表。从 Phase4Task 表查询 status='reviewing' 的记录。"""
    skip = (page - 1) * page_size

    tasks = await phase4_dao.list_by_status(db, "reviewing", skip=skip, limit=page_size)
    total = await phase4_dao.count_by_status(db, "reviewing")

    reviews = []
    for t in tasks:
        reviews.append({
            "id": t.id,
            "nonce": t.nonce,
            "project_id": t.project_id,
            "chapter_id": t.chapter_id,
            "status": t.status,
            "state": t.state,
            "error_message": t.error_message,
            "retry_count": t.retry_count,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/reviews/{review_id}/approve", status_code=200)
async def approve_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """批准精修建议，将任务状态更新为 'approved'。"""
    task = await phase4_dao.get(db, review_id)

    if not task:
        raise NotFoundError(detail=f"Review task {review_id} not found")

    # Verify project ownership
    project = await project_dao.get(db, int(task.project_id))
    if project is None:
        raise NotFoundError(detail="Project not found")
    if str(project.user_id) != str(current_user.id):
        raise ForbiddenError(detail="Not authorized to approve this review")

    task.status = "approved"
    task.state = Phase4State.DONE.value
    await db.commit()

    return {
        "approved": True,
        "review_id": review_id,
        "status": task.status,
    }


@router.post("/reviews/{review_id}/reject", status_code=200)
async def reject_review(
    review_id: int,
    req: RejectReviewReq,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """拒绝精修建议，记录原因，更新状态为 'rejected'。"""
    reason = req.reason or ""
    task = await phase4_dao.get(db, review_id)

    if not task:
        raise NotFoundError(detail=f"Review task {review_id} not found")

    # Verify project ownership
    project = await project_dao.get(db, int(task.project_id))
    if project is None:
        raise NotFoundError(detail="Project not found")
    if str(project.user_id) != str(current_user.id):
        raise ForbiddenError(detail="Not authorized to reject this review")

    task.status = "rejected"
    task.state = Phase4State.FAILED.value
    task.error_message = reason or "Review rejected"
    task.last_error = reason or "Review rejected"
    await db.commit()

    return {
        "rejected": True,
        "review_id": review_id,
        "reason": reason,
        "status": task.status,
    }


@router.post("/tasks/{task_id}/retry", status_code=200)
async def retry_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """重置任务状态为 'queued'，允许重新执行。"""
    task = await phase4_dao.get(db, task_id)

    if not task:
        raise NotFoundError(detail=f"Task {task_id} not found")

    task.status = "queued"
    task.state = Phase4State.QUEUED.value
    task.error_message = None
    task.last_error = None
    await db.commit()

    return {
        "success": True,
        "task_id": task_id,
        "status": task.status,
        "state": task.state,
    }
