"""墨灵 (Moling) — Admin Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SystemStatsResp(BaseModel):
    """System overview statistics."""

    total_users: int = Field(default=0, description="总用户数")
    active_users: int = Field(default=0, description="活跃用户数")
    total_projects: int = Field(default=0, description="总项目数")
    total_chapters: int = Field(default=0, description="总章节数")
    total_words: int = Field(default=0, description="总字数")
    generation_tasks_today: int = Field(default=0, description="今日生成任务数")


class LlmUsageResp(BaseModel):
    """LLM usage statistics."""

    total_requests: int = Field(default=0, description="总请求数")
    total_tokens: int = Field(default=0, description="总 Token 数")
    requests_today: int = Field(default=0, description="今日请求数")
    tokens_today: int = Field(default=0, description="今日 Token 数")


class LLMConfigReq(BaseModel):
    """Request body for saving LLM configuration."""

    api_key: str = Field(..., description="LLM API Key")
    api_base: str = Field(default="https://api.deepseek.com", description="LLM API Base URL")
    model: str = Field(default="deepseek-chat", description="Default model")


class LLMConfigResp(BaseModel):
    """Response for LLM configuration endpoints."""

    api_base: str = Field(..., description="LLM API Base URL")
    model: str = Field(..., description="Default model")
    is_configured: bool = Field(..., description="Whether LLM is configured")
    api_key_masked: str = Field(default="", description="Masked API key for display")


class AdminStatsResp(BaseModel):
    """Admin statistics response."""

    user_count: int = Field(..., description="总用户数")
    project_count: int = Field(..., description="总项目数")
    chapter_count: int = Field(..., description="总章节数")
    task_count: int = Field(..., description="总任务数")


class UserManageResp(BaseModel):
    """User management response."""

    id: int = Field(..., description="用户 ID")
    email: str = Field(..., description="邮箱")
    username: str = Field(..., description="用户名")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class ProjectManageResp(BaseModel):
    """Project management response."""

    id: int = Field(..., description="项目 ID")
    title: str = Field(..., description="项目标题")
    user_id: int = Field(..., description="用户 ID")
    status: str = Field(..., description="状态")
    chapter_count: int = Field(default=0, description="章节数")
    word_count: int = Field(default=0, description="字数")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
