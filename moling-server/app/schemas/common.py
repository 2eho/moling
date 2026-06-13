"""墨灵 (Moling) — Common Pydantic Schemas."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationReq(BaseModel):
    """Query parameters for paginated list endpoints."""

    page: int = Field(default=1, ge=1, description="页码 (从 1 开始)")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PaginatedResp(BaseModel, Generic[T]):
    """Paginated list response wrapper."""

    items: list[T] = Field(default=[], description="当前页数据列表")
    total: int = Field(default=0, ge=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=20, ge=1, description="每页条数")


class SuccessResp(BaseModel):
    """Generic success response for side-effect-only operations."""

    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="提示信息")
    data: Optional[dict] = Field(default=None, description="返回数据")
