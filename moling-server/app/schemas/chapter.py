"""墨灵 (Moling) — Chapter-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateChapterReq(BaseModel):
    """Create a new chapter."""

    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    chapter_number: int = Field(..., ge=1, description="章节序号")


class UpdateChapterReq(BaseModel):
    """Update an existing chapter (all fields optional)."""

    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    content: Optional[str] = Field(default=None, description="章节正文内容")


class ChapterResp(BaseModel):
    """Chapter response (without dynamic_layer)."""

    id: int = Field(..., description="章节 ID")
    project_id: int = Field(..., description="所属项目 ID")
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
