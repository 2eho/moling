"""墨灵 (Moling) — Generation API Router.

Provides endpoints for AI text generation tasks.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
from app.service import generation_service

router = APIRouter(prefix="/generation", tags=["generation"])


@router.post("", response_model=GenerationResp, status_code=201)
async def start_generation(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: Optional[int] = Query(None, description="Chapter ID (optional)"),
    req: GenerateReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> GenerationResp:
    """Start an AI generation task."""
    return await generation_service.start_generation(
        db, current_user["id"], project_id, chapter_id, req
    )


@router.get("/{task_id}", response_model=TaskStatusResp)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TaskStatusResp:
    """Get generation task status."""
    return await generation_service.get_task_status(db, current_user["id"], task_id)


@router.delete("/{task_id}", status_code=204)
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Cancel a generation task."""
    await generation_service.cancel_task(db, current_user["id"], task_id)
