"""墨灵 (Moling) — Template Pydantic Schemas (reserved for future use)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TemplateResp(BaseModel):
    """Project template response."""

    id: str = Field(..., description="模板 ID (UUID)")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    genre: str = Field(..., description="适用题材")
    target_words: Optional[int] = Field(default=None, description="建议目标字数")
    style: Optional[str] = Field(default=None, description="建议写作风格")

    model_config = {"from_attributes": True}


class CreateTemplateReq(BaseModel):
    """Request body for creating a template."""

    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    genre: str = Field(..., description="适用题材")
    structure: Optional[dict] = Field(default=None, description="模板结构 (JSON)")


class UpdateTemplateReq(BaseModel):
    """Request body for updating a template."""

    name: Optional[str] = Field(default=None, description="模板名称")
    description: Optional[str] = Field(default=None, description="模板描述")
    genre: Optional[str] = Field(default=None, description="适用题材")
    structure: Optional[dict] = Field(default=None, description="模板结构 (JSON)")
