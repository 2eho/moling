"""墨灵 (Moling) — Secret (秘密矩阵) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SecretResp(BaseModel):
    """Secret detail response."""

    id: str = Field(description="密钥 ID（UUID 格式）")
    project_id: int = Field(description="所属项目 ID")
    description: str = Field(description="秘密内容描述")
    known_by: list[str] = Field(description="已知该秘密的角色列表")
    unknown_to: list[str] = Field(description="未知该秘密的角色列表")
    secrecy_level: str = Field(description="保密等级")
    created_chapter: int | None = Field(default=None, description="创建该秘密的章节号")
    debt: int = Field(description="秘密债值（未揭示的秘密计数）")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")

    model_config = {"from_attributes": True}


class UpdateSecretReq(BaseModel):
    """Request body for updating a secret."""

    description: str | None = Field(default=None, description="秘密内容描述")
    known_by: list[str] | None = Field(default=None, description="已知该秘密的角色列表")
    unknown_to: list[str] | None = Field(default=None, description="未知该秘密的角色列表")
    secrecy_level: str | None = Field(default=None, description="保密等级")
    debt: int | None = Field(default=None, description="秘密债值（未揭示的秘密计数）")


class SecretItemUpdate(BaseModel):
    """A secret item in the update request."""

    id: int | None = Field(default=None, description="密钥项 ID")
    content: str | None = Field(default=None, description="秘密内容")
    related_characters: list[str] | None = Field(default=None, description="关联角色列表")
    confidence: float | None = Field(default=None, description="置信度")
    secrecy_level: str | None = Field(default=None, description="保密等级")


class UpdateSecretsByCharacterReq(BaseModel):
    """Request body for updating secrets by character."""

    character_id: int = Field(description="角色 ID")
    character_name: str = Field(description="角色名称")
    secrets: list[SecretItemUpdate] = Field(description="要更新的秘密列表")
