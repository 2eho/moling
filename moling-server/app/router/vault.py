"""墨灵 (Moling) — Vault API Router.

Provides endpoints for the Four Databases (四库): Characters, Timeline, Plot Promises, World Building.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.vault import CharacterResp, TimelineResp, PlotPromiseResp, WorldResp
from app.service import vault_service

router = APIRouter(prefix="/vault", tags=["vault"])


# =========== Characters ===========


@router.get("/characters", response_model=list[CharacterResp])
async def list_characters(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CharacterResp]:
    """List all characters in a project's vault."""
    return await vault_service.list_characters(db, current_user["id"], project_id)


@router.post("/characters", response_model=CharacterResp, status_code=201)
async def create_character(
    project_id: int = Query(..., description="Project ID"),
    character_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CharacterResp:
    """Create a new character in the vault."""
    return await vault_service.create_character(db, current_user["id"], project_id, character_data)


@router.put("/characters/{character_id}", response_model=CharacterResp)
async def update_character(
    project_id: int = Query(..., description="Project ID"),
    character_id: int = ...,
    character_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CharacterResp:
    """Update a character in the vault."""
    return await vault_service.update_character(
        db, current_user["id"], project_id, character_id, character_data
    )


@router.delete("/characters/{character_id}", status_code=204)
async def delete_character(
    project_id: int = Query(..., description="Project ID"),
    character_id: int = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a character from the vault."""
    await vault_service.delete_character(db, current_user["id"], project_id, character_id)


# =========== Timeline ===========


@router.get("/timeline", response_model=list[TimelineResp])
async def list_timeline(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[TimelineResp]:
    """List all timeline events in a project's vault."""
    return await vault_service.list_timeline(db, current_user["id"], project_id)


@router.post("/timeline", response_model=TimelineResp, status_code=201)
async def create_timeline_event(
    project_id: int = Query(..., description="Project ID"),
    event_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TimelineResp:
    """Create a new timeline event in the vault."""
    return await vault_service.create_timeline_event(db, current_user["id"], project_id, event_data)


# =========== Plot Promises ===========


@router.get("/plot-promises", response_model=list[PlotPromiseResp])
async def list_plot_promises(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PlotPromiseResp]:
    """List all plot promises in a project's vault."""
    return await vault_service.list_plot_promises(db, current_user["id"], project_id)


@router.post("/plot-promises", response_model=PlotPromiseResp, status_code=201)
async def create_plot_promise(
    project_id: int = Query(..., description="Project ID"),
    promise_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlotPromiseResp:
    """Create a new plot promise in the vault."""
    return await vault_service.create_plot_promise(db, current_user["id"], project_id, promise_data)


# =========== World Building ===========


@router.get("/world", response_model=list[WorldResp])
async def list_world_entries(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[WorldResp]:
    """List all world-building entries in a project's vault."""
    return await vault_service.list_world_entries(db, current_user["id"], project_id)


@router.post("/world", response_model=WorldResp, status_code=201)
async def create_world_entry(
    project_id: int = Query(..., description="Project ID"),
    entry_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorldResp:
    """Create a new world-building entry in the vault."""
    return await vault_service.create_world_entry(db, current_user["id"], project_id, entry_data)
