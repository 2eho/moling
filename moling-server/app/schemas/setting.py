"""墨灵 (Moling) — Settings Schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    """User preferences stored as JSONB on the User model."""

    ai_model: str = Field(default="deepseek-v4-pro", description="AI模型")
    writing_style: str = Field(default="auto", description="写作风格")
    target_words_per_chapter: int = Field(default=3000, ge=500, le=10000)
    auto_coherence: bool = Field(default=True)
    auto_save: bool = Field(default=True, description="自动保存")
    auto_save_draft: bool = Field(default=True, validation_alias="auto_save", description="自动保存草稿")
    dark_mode: bool = Field(default=True, description="深色模式")
    theme: str = Field(default="light", validation_alias="dark_mode", description="主题")
    font_size: str = Field(default="中")
    cooldown_redraws: int = Field(default=3, ge=1, le=10)
    health_monitor_enabled: bool = Field(default=True)
    phase4_review_mode: str = Field(default="auto")
    nickname: Optional[str] = Field(default=None, description="用户昵称")
    bio: Optional[str] = Field(default=None, description="个人简介")
    email: Optional[str] = Field(default=None, description="邮箱")
    language: str = Field(default="zh-CN", description="语言")
    creativity: float = Field(default=0.7, ge=0.0, le=1.0, description="创造力")
    word_count: int = Field(default=0, description="总字数")
    target_words: Optional[int] = Field(default=None, description="目标总字数")
    update_frequency: Optional[str] = Field(default=None, description="更新频率")


class HealthMonitorReq(BaseModel):
    """Update health monitoring rules."""

    enabled: bool = Field(..., description="是否启用健康监控")
    rules: list[str] = Field(default=[], description="监控规则列表")


class Phase4ReviewReq(BaseModel):
    """Update Phase 4 review mode settings."""

    enabled: bool = Field(..., description="是否启用 Phase 4 审核")
    auto_approve: bool = Field(default=False, description="是否自动通过")
