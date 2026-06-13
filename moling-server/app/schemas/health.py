"""墨灵 (Moling) — Health Alert Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthAlertResp(BaseModel):
    """Health alert response."""

    id: int = Field(..., description="告警 ID")
    rule: str = Field(..., description="触发的规则名称")
    title: str = Field(..., description="告警标题")
    detail: str = Field(..., description="告警详情")
    severity: str = Field(..., description="严重程度")
    is_active: bool = Field(default=True, description="是否活跃")
    checked_at: Optional[datetime] = Field(default=None, description="最后检查时间")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
