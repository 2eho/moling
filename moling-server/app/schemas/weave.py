"""墨灵 (Moling) — Weave (编织) Pydantic Schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class WeaveSuggestionResp(BaseModel):
    """Weave 编织建议响应。"""

    project_id: str = Field(..., description="项目 ID (UUID)")
    suggestions: list[dict] = Field(..., description="编织建议列表")
    overview: str = Field(..., description="整体分析概述")


class ApplyWeaveReq(BaseModel):
    """应用 Weave 编织请求。"""

    project_id: str = Field(..., description="项目 ID (UUID)")
    suggestion_ids: list[str] = Field(..., description="要应用的建议 ID 列表")
    target_chapter_ids: list[str] = Field(..., description="目标章节 ID 列表 (UUID)")


class WeaveAnalysisResp(BaseModel):
    """Weave 编织分析结果响应。"""

    project_id: str = Field(..., description="项目 ID (UUID)")
    plot_threads: list[dict] = Field(..., description="情节线索")
    character_arcs: list[dict] = Field(..., description="人物弧光")
    timeline_consistency: dict = Field(..., description="时间线一致性")
    unresolved_promises: list[dict] = Field(..., description="未兑现的承诺")
    created_at: str

    model_config = {"from_attributes": True}
