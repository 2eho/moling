"""墨灵 (Moling) — Phase 4 (四阶段精修) Pydantic Schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, Field


class Phase4SuggestionResp(BaseModel):
    """Phase 4 精修建议响应。"""

    chapter_id: int = Field(..., description="章节 ID")
    suggestions: list[dict] = Field(..., description="精修建议列表")
    overall_score: float = Field(..., description="总体评分")
    details: dict = Field(..., description="详细分析结果")


class ApplyPhase4Req(BaseModel):
    """应用 Phase 4 精修请求。"""

    chapter_id: int = Field(..., description="章节 ID")
    suggestion_ids: list[str] = Field(..., description="要应用的建议 ID 列表")
    auto_apply: bool = Field(default=False, description="是否自动应用所有建议")


class RejectReviewReq(BaseModel):
    """拒绝 Phase 4 精修建议请求。"""

    reason: Optional[str] = Field(default=None, max_length=500, description="拒绝原因")


class Phase4TaskResp(BaseModel):
    """Phase 4 任务响应 — P1-3 修复: status 统一为 state (Phase4State 枚举)。"""

    id: int
    nonce: str
    project_id: str
    chapter_id: str
    state: str
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class ApplyPhase4Resp(BaseModel):
    """Phase 4 应用精修响应。"""

    message: Optional[str] = None
    task_id: Optional[int] = None


class PendingReviewItem(BaseModel):
    """待审核精修建议条目。"""

    id: int
    nonce: str
    project_id: Optional[str] = None
    chapter_id: Optional[str] = None
    status: Optional[str] = None
    state: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


class PendingReviewsResp(BaseModel):
    """待审核精修建议列表响应。"""

    reviews: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ApproveReviewResp(BaseModel):
    """批准精修建议响应。"""

    approved: bool
    review_id: int
    state: str


class RejectReviewResp(BaseModel):
    """拒绝精修建议响应。"""

    rejected: bool
    review_id: int
    reason: str
    state: str


class RetryTaskResp(BaseModel):
    """重试异常任务响应。"""

    success: bool
    task_id: int
    state: str
