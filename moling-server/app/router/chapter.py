"""墨灵 (Moling) — Chapter API Router.

Provides endpoints for chapter CRUD operations within a project.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.chapter import CreateChapterReq, ChapterResp, UpdateChapterReq
from app.service import chapter_service

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.post("", response_model=ChapterResp, status_code=201)
async def create_chapter(
    project_id: int = Query(..., description="Project ID"),
    req: CreateChapterReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Create a new chapter in a project."""
    return await chapter_service.create_chapter(db, current_user["id"], project_id, req)


@router.get("", response_model=list[ChapterResp])
async def list_chapters(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ChapterResp]:
    """List chapters in a project."""
    return await chapter_service.list_chapters(db, current_user["id"], project_id)


@router.get("/{chapter_id}", response_model=ChapterResp)
async def get_chapter(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Get single chapter by ID."""
    return await chapter_service.get_chapter(db, current_user["id"], project_id, chapter_id)


@router.put("/{chapter_id}", response_model=ChapterResp)
async def update_chapter(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    req: UpdateChapterReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Update chapter by ID."""
    return await chapter_service.update_chapter(db, current_user["id"], project_id, chapter_id, req)


@router.delete("/{chapter_id}", status_code=204)
async def delete_chapter(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete chapter by ID."""
    await chapter_service.delete_chapter(db, current_user["id"], project_id, chapter_id)


@router.post("/reorder", response_model=list[ChapterResp])
async def reorder_chapters(
    project_id: int = Query(..., description="Project ID"),
    chapter_numbers: list[int] = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ChapterResp]:
    """Reorder chapters by providing new chapter numbers."""
    return await chapter_service.reorder_chapters(db, current_user["id"], project_id, chapter_numbers)


@router.post("/{chapter_id}/confirm", response_model=ChapterResp)
async def confirm_chapter(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    confirm_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Confirm a chapter and trigger Phase 4 processing."""
    return await chapter_service.confirm_chapter(
        db, current_user["id"], project_id, chapter_id, confirm_data
    )


@router.post("/{chapter_id}/revise", response_model=ChapterResp)
async def revise_chapter(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    revise_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Mark a chapter for revision (reject/revise)."""
    return await chapter_service.revise_chapter(
        db, current_user["id"], project_id, chapter_id, revise_data
    )


@router.get("/{chapter_id}/suggestions", response_model=dict)
async def get_chapter_suggestions(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取章节的创作建议。"""
    suggestions = await chapter_service.get_suggestions(
        db, current_user["id"], project_id, chapter_id
    )
    return suggestions


@router.post("/{chapter_id}/agent", response_model=dict)
async def send_agent_instruction(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: int = ...,
    instruction: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """向 AI 发送指令（用于章节生成过程中的干预）。"""
    result = await chapter_service.send_agent_instruction(
        db, current_user["id"], project_id, chapter_id, instruction
    )
    return result
