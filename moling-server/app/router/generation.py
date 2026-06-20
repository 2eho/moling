"""墨灵 (Moling) — Generation API Router.

Provides endpoints for AI text generation task status and cancellation.
Auth check happens via Depends(get_current_user) BEFORE any resource lookup.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.generation import TaskStatusResp
from app.service import generation_service
from app.errors import NotFoundError, PermissionError as AppPermissionError

router = APIRouter(tags=["generation"])


@router.get("/{task_id}", response_model=TaskStatusResp)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TaskStatusResp:
    """Get generation task status.

    Authentication is checked first via Depends(get_current_user).
    Returns 401 if not authenticated, 404 if task not found,
    403 if task belongs to another user.
    """
    try:
        return await generation_service.get_task_status(db, current_user.id, task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="任务不存在")
    except AppPermissionError:
        raise HTTPException(status_code=403, detail="无权访问此任务")


@router.delete("/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Cancel a generation task.

    Authentication is checked first via Depends(get_current_user).
    Returns 401 if not authenticated, 404 if task not found,
    403 if task belongs to another user.
    """
    try:
        await generation_service.cancel_task(db, current_user.id, task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="任务不存在")
    except AppPermissionError:
        detail = "无权操作此任务"
        raise HTTPException(status_code=403, detail=detail)

    return {"status": "cancelled", "task_id": task_id}


@router.get("/history", response_model=list[dict])
async def get_generation_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> list[dict]:
    """Get generation task history."""
    history = await generation_service.get_history(
        db, current_user.id, page, page_size
    )
    return history
