"""墨灵 (Moling) — Card API Router.

Provides endpoints for card pool management and card draw operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.card import DrawCardReq, CardResp, DrawCardResp, CardPoolListResp
from app.service import card_service

router = APIRouter(tags=["cards"])


@router.get("/cards", response_model=CardPoolListResp)
async def list_cards(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardPoolListResp:
    """List all cards in a project's card pool."""
    return await card_service.list_cards(db, current_user["id"], project_id)


@router.post("/cards/draw", response_model=DrawCardResp)
async def draw_cards(
    project_id: int,
    req: DrawCardReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DrawCardResp:
    """Draw cards from the pool (Phase 4 algorithm)."""
    return await card_service.draw_cards(db, current_user["id"], project_id, req)


@router.post("/cards", response_model=CardResp, status_code=201)
async def create_card(
    project_id: int,
    card_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardResp:
    """Create a custom card in the pool."""
    return await card_service.create_card(db, current_user["id"], project_id, card_data)


@router.post("/cards/{card_id}/retire", status_code=204)
async def retire_card(
    project_id: int,
    card_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Retire a card (set is_active=False)."""
    await card_service.retire_card(db, current_user["id"], project_id, card_id)


@router.get("/cards/pool", response_model=CardPoolListResp)
async def get_card_pool(
    project_id: int,
    count: int = Query(3, ge=1, le=10, description="Number of cards to draw from pool"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardPoolListResp:
    """Get cards from the project's card pool (for drawing UI)."""
    return await card_service.list_cards(db, current_user["id"], project_id)


@router.get("/cards/history", response_model=list)
async def get_draw_history(
    project_id: int,
    chapter_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list:
    """Get draw history for a project."""
    return await card_service.get_draw_history(
        db, current_user["id"], project_id, chapter_id
    )


@router.get("/cards/draw-history", response_model=list)
async def list_draw_history(
    project_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    chapter_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list:
    """获取项目的抽卡历史记录（分页）。"""
    return await card_service.get_draw_history(
        db, current_user["id"], project_id, chapter_id
    )


@router.get("/cards/draw-history/{draw_id}", response_model=dict)
async def get_draw_history_detail(
    project_id: int,
    draw_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取单条抽卡历史详情。"""
    result = await card_service.get_draw_history_detail(
        db, current_user["id"], project_id, draw_id
    )
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="抽卡记录不存在")
    return result
