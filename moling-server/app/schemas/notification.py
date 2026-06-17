"""墨灵 (Moling) — Notification (通知) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class NotificationResp(BaseModel):
    """Notification detail response."""

    id: int
    user_id: int
    type: str
    title: str
    content: Optional[str] = None
    message: Optional[str] = Field(default=None, description="通知消息内容（兼容前端 message 字段）")
    is_read: bool
    project_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_message(self):
        if self.message is None and self.content is not None:
            self.message = self.content
        return self
