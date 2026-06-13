"""墨灵 (Moling) — Notification (通知) Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationResp(BaseModel):
    """Notification detail response."""

    id: int
    user_id: int
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool
    project_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
