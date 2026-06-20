"""墨灵 (Moling) — Phase 4 (四阶段精修) Pydantic Schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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
    """Phase 4 任务响应。"""

    id: int
    nonce: str
    project_id: str
    chapter_id: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}
