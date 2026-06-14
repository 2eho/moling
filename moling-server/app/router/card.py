"""澧ㄧ伒 (Moling) 鈥?Card API Router.

Provides endpoints for card pool management and card draw operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.card import DrawCardReq, CardResp, DrawCardResp, CardPoolListResp
from app.service import card_service

router = APIRouter(tags=["cards"])


@router.get("", response_model=CardPoolListResp)
async def list_cards(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardPoolListResp:
    """List all cards in a project's card pool."""
    return await card_service.list_cards(db, current_user["id"], project_id)


@router.post("/draw", response_model=DrawCardResp)
async def draw_cards(
    project_id: int = Query(..., description="Project ID"),
    req: DrawCardReq = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DrawCardResp:
    """Draw cards from the pool (Phase 4 algorithm)."""
    return await card_service.draw_cards(db, current_user["id"], project_id, req)


@router.post("", response_model=CardResp, status_code=201)
async def create_card(
    project_id: int = Query(..., description="Project ID"),
    card_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CardResp:
    """Create a custom card in the pool."""
    return await card_service.create_card(db, current_user["id"], project_id, card_data)


@router.post("/{card_id}/retire", status_code=204)
async def retire_card(
    project_id: int = Query(..., description="Project ID"),
    card_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Retire a card (set is_active=False)."""
    await card_service.retire_card(db, current_user["id"], project_id, card_id)


@router.get("/history", response_model=list)
async def get_draw_history(
    project_id: int = Query(..., description="Project ID"),
    chapter_id: Optional[int] = Query(None, description="Filter by chapter"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list:
    """Get draw history for a project."""
    # TODO: implement get_draw_history in service
    return []
