"""墨灵 (Moling) — Secret (秘密矩阵) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SecretResp(BaseModel):
    """Secret detail response."""

    id: str  # String(36) UUID — matches Secret model PK
    project_id: int
    description: str
    known_by: list[str]
    unknown_to: list[str]
    secrecy_level: str
    created_chapter: Optional[int] = None
    debt: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateSecretReq(BaseModel):
    """Request body for updating a secret."""

    description: Optional[str] = None
    known_by: Optional[list[str]] = None
    unknown_to: Optional[list[str]] = None
    secrecy_level: Optional[str] = None
    debt: Optional[int] = None


class SecretItemUpdate(BaseModel):
    """A secret item in the update request."""

    id: Optional[int] = None
    content: Optional[str] = None
    related_characters: Optional[list[str]] = None
    confidence: Optional[float] = None
    secrecy_level: Optional[str] = None


class UpdateSecretsByCharacterReq(BaseModel):
    """Request body for updating secrets by character."""

    character_id: int
    character_name: str
    secrets: list[SecretItemUpdate]
