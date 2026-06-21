"""墨灵 (Moling) — Template Pydantic Schemas (reserved for future use)."""

from __future__ import annotations


from pydantic import BaseModel, Field


class TemplateResp(BaseModel):
    """Project template response."""

    id: str = Field(..., description="模板 ID (UUID)")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    genre: str = Field(..., description="适用题材")
    target_words: int | None = Field(default=None, description="建议目标字数")
    style: str | None = Field(default=None, description="建议写作风格")

    model_config = {"from_attributes": True}


class CreateTemplateReq(BaseModel):
    """Request body for creating a template."""

    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    genre: str = Field(..., description="适用题材")
    structure: dict | None = Field(default=None, description="模板结构 (JSON)")


class UpdateTemplateReq(BaseModel):
    """Request body for updating a template."""

    name: str | None = Field(default=None, description="模板名称")
    description: str | None = Field(default=None, description="模板描述")
    genre: str | None = Field(default=None, description="适用题材")
    structure: dict | None = Field(default=None, description="模板结构 (JSON)")


class TemplateListResp(BaseModel):
    """Paginated template list response."""

    items: list[TemplateResp] = Field(..., description="模板列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class CreateProjectFromTemplateResp(BaseModel):
    """Response for creating a project from a template."""

    id: int = Field(..., description="项目 ID")
    title: str = Field(..., description="项目标题")
    genre: str = Field(..., description="作品题材")
    template_id: str = Field(..., description="模板 ID (UUID)")
    message: str = Field(..., description="结果消息")
