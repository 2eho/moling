"""墨灵 (Moling) — Generation Task Pydantic Schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerateReq(BaseModel):
    """Request body to start an AI generation task."""

    card_ids: list[int] = Field(
        default=[], description="选中的卡片 ID 列表"
    )
    weights: list[float] = Field(
        default=[], description="对应权重"
    )
    mode: str = Field(
        default="single",
        pattern=r"^(none|single|dual|all|hybrid)$",
        description="抽取模式",
    )


class GenerationResp(BaseModel):
    """Response returned immediately after submitting a generation task."""

    task_id: str = Field(..., description="生成任务 ID (UUID)")
    status: str = Field(default="pending", description="任务状态")


class TaskStatusResp(BaseModel):
    """Polling response for generation task progress."""

    task_id: str = Field(..., description="生成任务 ID (UUID)")
    status: str = Field(..., description="任务状态")
    progress_stage: Optional[str] = Field(default=None, description="当前进度阶段")
    progress_percent: int = Field(default=0, description="进度百分比")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    output_data: Optional[dict] = Field(default=None, description="输出数据")
