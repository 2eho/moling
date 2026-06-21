"""墨灵 (Moling) — Notification (通知) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class NotificationResp(BaseModel):
    """Notification detail response."""

    id: int = Field(..., description="通知 ID")
    user_id: str = Field(..., description="用户 ID (UUID)")
    type: str = Field(..., description="通知类型")
    title: str = Field(..., description="通知标题")
    content: str | None = Field(default=None, description="通知正文")
    message: str | None = Field(default=None, description="通知消息内容（兼容前端 message 字段）")
    is_read: bool = Field(default=False, description="是否已读")
    project_id: str | None = Field(default=None, description="关联项目 ID (UUID)")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def set_message(self):
        if self.message is None and self.content is not None:
            self.message = self.content
        return self
