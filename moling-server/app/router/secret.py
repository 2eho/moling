"""
澧ㄧ伒 (Moling) 鈥?Secret (绉樺瘑鐭╅樀) Router.

Endpoints for managing project secrets and character-secret relationships.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.schemas.secret import SecretResp, UpdateSecretReq, UpdateSecretsByCharacterReq
from app.service.secret_service import secret_service

router = APIRouter()


@router.get("", response_model=list[SecretResp])
async def list_secrets(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SecretResp]:
    """List all secrets for a project."""
    return await secret_service.list_secrets(db, project_id)


@router.get("/character/{character_name}", response_model=dict)
async def get_secrets_by_character(
    project_id: int,
    character_name: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get secrets known to and unknown by a character (query by name)."""
    return await secret_service.get_secrets_by_character_name(
        db, project_id, character_name
    )


@router.put("/character/{character_id}", response_model=dict)
async def update_secrets_by_character(
    project_id: int,
    character_id: int,
    data: UpdateSecretsByCharacterReq,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update secrets for a character (by ID, for backward compatibility)."""
    result = await secret_service.update_secrets_by_character(
        db, project_id, character_id, data
    )
    return result


@router.patch("/{secret_id}", response_model=dict)
async def update_secret(
    project_id: int,
    secret_id: int,
    data: UpdateSecretReq,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a specific secret (edit known_by, unknown_to, debt_count)."""
    result = await secret_service.update_secret(
        db, project_id, secret_id, data
    )
    return result
