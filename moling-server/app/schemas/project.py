"""墨灵 (Moling) — Project-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CreateProjectReq(BaseModel):
    """Create a new project."""

    title: str = Field(..., min_length=1, max_length=200, description="作品标题")
    author: str = Field(..., min_length=1, max_length=100, description="作者署名")
    genre: str = Field(..., max_length=50, description="作品类型/题材")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")
    synopsis: Optional[str] = Field(default=None, description="作品简介")
    worldview: Optional[str] = Field(default=None, description="世界观设定")
    protagonist: Optional[str] = Field(default=None, description="主角简介")
    supporting_chars: Optional[list] = Field(default=None, description="配角列表")
    target_words: Optional[int] = Field(default=None, ge=1000, description="目标总字数")
    frequency: Optional[str] = Field(default=None, max_length=20, description="更新频率")
    style: Optional[str] = Field(default=None, max_length=50, description="写作风格")
    creation_mode: str = Field(
        default="from_scratch",
        pattern=r"^(from_scratch|from_template)$",
        description="创建模式",
    )
    template_id: Optional[str] = Field(default=None, description="模板 ID (UUID)")


class UpdateProjectReq(BaseModel):
    """Update an existing project (all fields optional)."""

    title: Optional[str] = Field(default=None, max_length=200, description="作品标题")
    author: Optional[str] = Field(default=None, max_length=100, description="作者署名")
    genre: Optional[str] = Field(default=None, max_length=50, description="作品类型/题材")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")
    synopsis: Optional[str] = Field(default=None, description="作品简介")
    worldview: Optional[str] = Field(default=None, description="世界观设定")
    protagonist: Optional[str] = Field(default=None, description="主角简介")
    supporting_chars: Optional[list] = Field(default=None, description="配角列表")
    word_count: Optional[int] = Field(default=None, ge=0, description="当前总字数")
    target_words: Optional[int] = Field(default=None, ge=1000, description="目标总字数")
    frequency: Optional[str] = Field(default=None, max_length=20, description="更新频率")
    style: Optional[str] = Field(default=None, max_length=50, description="写作风格")
    status: Optional[str] = Field(
        default=None,
        pattern=r"^(draft|active|completed|archived)$",
        description="项目状态",
    )


class ProjectResp(BaseModel):
    """Project response (all fields except user_id)."""

    id: int = Field(..., description="项目 ID")
    title: str = Field(..., description="作品标题")
    author: str = Field(..., description="作者署名")
    genre: str = Field(..., description="作品类型/题材")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")
    synopsis: Optional[str] = Field(default=None, description="作品简介")
    worldview: Optional[str] = Field(default=None, description="世界观设定")
    protagonist: Optional[str] = Field(default=None, description="主角简介")
    supporting_chars: Optional[list] = Field(default=None, description="配角列表")
    word_count: int = Field(default=0, description="当前总字数")
    chapters: int = Field(default=0, description="章节数")
    target_words: Optional[int] = Field(default=None, description="目标总字数")
    frequency: Optional[str] = Field(default=None, description="更新频率")
    style: Optional[str] = Field(default=None, description="写作风格")
    status: str = Field(default="draft", description="项目状态")
    creation_mode: str = Field(default="from_scratch", description="创建模式")
    template_id: Optional[int] = Field(default=None, description="模板 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}

    @field_validator("chapters", mode="before")
    @classmethod
    def chapters_as_int(cls, v):
        """chapters can be list (SQLAlchemy relationship) or int (pre-computed)."""
        if isinstance(v, (list, tuple)):
            return len(v)
        return v or 0


class ProjectStatsResp(BaseModel):
    """Aggregated project statistics for a user."""

    total_projects: int = Field(default=0, description="总项目数")
    active_count: int = Field(default=0, description="进行中项目数")
    draft_count: int = Field(default=0, description="草稿项目数")
    total_words: int = Field(default=0, description="总字数")


class ProjectListResp(BaseModel):
    """Paginated project list response."""

    items: list[ProjectResp] = Field(..., description="项目列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class SingleProjectStatsResp(BaseModel):
    """Single project statistics."""

    project_id: int = Field(..., description="项目 ID")
    title: str = Field(..., description="项目标题")
    total_chapters: int = Field(..., description="总章节数")
    total_words: int = Field(..., description="总字数")
    status: str = Field(..., description="项目状态")
