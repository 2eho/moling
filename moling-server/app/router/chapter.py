"""墨灵 (Moling) — Chapter API Router.

Provides endpoints for chapter CRUD operations within a project.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.chapter import CreateChapterReq, ChapterResp, UpdateChapterReq
from app.schemas.generation import GenerateReq
from app.service import chapter_service, generation_service

router = APIRouter(tags=["chapters"])


@router.post("/chapters", response_model=ChapterResp, status_code=201)
async def create_chapter(
    project_id: int,
    req: CreateChapterReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Create a new chapter in a project."""
    return await chapter_service.create_chapter(db, current_user["id"], project_id, req)


@router.get("/chapters", response_model=list[ChapterResp])
async def list_chapters(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ChapterResp]:
    """List chapters in a project."""
    return await chapter_service.list_chapters(db, current_user["id"], project_id)


@router.get("/chapters/current", response_model=ChapterResp)
async def get_current_chapter(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Get the current (first) chapter in a project."""
    chapters = await chapter_service.list_chapters(db, current_user["id"], project_id)
    if not chapters:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No chapters found")
    return chapters[0]


@router.get("/chapters/{chapter_id}", response_model=ChapterResp)
async def get_chapter(
    project_id: int,
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Get single chapter by ID."""
    return await chapter_service.get_chapter(db, current_user["id"], project_id, chapter_id)


@router.put("/chapters/{chapter_id}", response_model=ChapterResp)
async def update_chapter(
    project_id: int,
    chapter_id: int = ...,
    req: UpdateChapterReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Update chapter by ID."""
    return await chapter_service.update_chapter(db, current_user["id"], project_id, chapter_id, req)


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(
    project_id: int,
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete chapter by ID."""
    await chapter_service.delete_chapter(db, current_user["id"], project_id, chapter_id)


@router.post("/chapters/reorder", response_model=list[ChapterResp])
async def reorder_chapters(
    project_id: int,
    chapter_numbers: list[int] = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ChapterResp]:
    """Reorder chapters by providing new chapter numbers."""
    return await chapter_service.reorder_chapters(db, current_user["id"], project_id, chapter_numbers)


@router.post("/chapters/{chapter_id}/confirm", response_model=ChapterResp)
async def confirm_chapter(
    project_id: int,
    chapter_id: int = ...,
    confirm_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Confirm a chapter and trigger Phase 4 processing."""
    return await chapter_service.confirm_chapter(
        db, current_user["id"], project_id, chapter_id, confirm_data
    )


@router.post("/chapters/{chapter_id}/revise", response_model=ChapterResp)
async def revise_chapter(
    project_id: int,
    chapter_id: int = ...,
    revise_data: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChapterResp:
    """Mark a chapter for revision (reject/revise)."""
    return await chapter_service.revise_chapter(
        db, current_user["id"], project_id, chapter_id, revise_data
    )


@router.get("/chapters/{chapter_id}/suggestions", response_model=dict)
async def get_chapter_suggestions(
    project_id: int,
    chapter_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取章节的创作建议。"""
    suggestions = await chapter_service.get_suggestions(
        db, current_user["id"], project_id, chapter_id
    )
    return suggestions


@router.post("/chapters/{chapter_id}/agent", response_model=dict)
async def send_agent_instruction(
    project_id: int,
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


@router.post("/chapters/{chapter_id}/generate", response_model=dict, status_code=201)
async def generate_chapter_content(
    project_id: int,
    chapter_id: int,
    req: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Start AI generation for a chapter (接口映射文档 4.5 节)."""
    generate_req = GenerateReq(**req)
    result = await generation_service.start_generation(
        db, current_user["id"], project_id, chapter_id, generate_req
    )
    return result


@router.post("/chapters/{chapter_id}/redraw", response_model=dict)
async def redraw_chapter_cards(
    project_id: int,
    chapter_id: int,
    data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """重抽卡牌（接口映射文档 4.4.3 节).
    
    排除本章已抽卡，重新抽取。
    请求参数：{keep_card_ids: list[int], draw_count: int = 3}
    响应：{cards: list, remaining_redraws: int}
    """
    # TODO: 实现重抽逻辑，调用 card_service.redraw()
    # 当前返回占位符响应
    return {
        "cards": [],
        "remaining_redraws": 3,
        "message": "重抽功能待实现",
    }
