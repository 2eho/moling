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
