"""墨灵 (Moling) — Chapter-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateChapterReq(BaseModel):
    """Create a new chapter. chapter_number 为可选，后端自动计算。"""

    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    chapter_number: Optional[int] = Field(default=None, ge=1, description="章节序号（可选，后端自动计算）")


class UpdateChapterReq(BaseModel):
    """Update an existing chapter (all fields optional)."""

    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    content: Optional[str] = Field(default=None, description="章节正文内容")


class ChapterResp(BaseModel):
    """Chapter response (without dynamic_layer)."""

    id: str = Field(..., description="章节 ID (UUID)")
    project_id: str = Field(..., description="所属项目 ID (UUID)")
    title: str = Field(..., description="章节标题")
    content: Optional[str] = Field(default=None, description="章节正文")
    chapter_number: int = Field(..., description="章节序号")
    status: str = Field(default="draft", description="章节状态")
    phase4_status: str = Field(default="none", description="四阶段精修状态")
    word_count: int = Field(default=0, description="本章字数")
    confirmed_at: Optional[datetime] = Field(default=None, description="确认收纳时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class ChapterConfirmReq(BaseModel):
    """Request body for chapter confirmation."""

    comment: Optional[str] = Field(default=None, max_length=500, description="确认备注")


class ChapterReviseReq(BaseModel):
    """Request body for chapter revision/rejection."""

    reason: Optional[str] = Field(default=None, max_length=500, description="修订原因")


class AgentInstructionReq(BaseModel):
    """Request body for AI agent instruction during chapter generation."""

    type: str = Field(..., min_length=1, max_length=50, description="指令类型")
    content: str = Field(..., min_length=1, description="指令内容")


class SyncGenerateReq(BaseModel):
    """Request body for the deprecated sync generation endpoint."""

    card_ids: list[str] = Field(..., description="选中的卡片 ID 列表")
    weights: list[float] = Field(default=[], description="对应权重")
    mode: str = Field(
        default="single",
        pattern=r"^(none|single|dual|all|hybrid)$",
        description="抽取模式",
    )
    creativity: int = Field(default=5, ge=1, le=10, description="创意程度")
    word_count: int = Field(default=2000, ge=500, le=5000, description="目标字数")


class RedrawCardsReq(BaseModel):
    """Request body for redrawing cards."""

    keep_card_ids: list[int] = Field(default=[], description="保留的卡片 ID 列表")
    draw_count: int = Field(default=3, ge=1, le=10, description="抽取数量")
