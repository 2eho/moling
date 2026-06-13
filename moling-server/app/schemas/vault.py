"""墨灵 (Moling) — Vault-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CharacterResp(BaseModel):
    """Vault character response."""

    id: int = Field(..., description="角色 ID")
    project_id: int = Field(..., description="所属项目 ID")
    name: str = Field(..., description="角色名称")
    role: str = Field(..., description="角色定位")
    faction: Optional[str] = Field(default=None, description="所属阵营")
    status: str = Field(default="active", description="角色状态")
    emotion: Optional[str] = Field(default=None, description="当前情绪")
    traits: Optional[list] = Field(default=None, description="性格特征")
    description: Optional[str] = Field(default=None, description="角色描述")
    background: Optional[str] = Field(default=None, description="角色背景")
    relationships: Optional[list] = Field(default=None, description="人际关系")
    state_machine: Optional[dict] = Field(default=None, description="状态机数据")
    chapter_count: int = Field(default=0, description="已出场章节数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class TimelineResp(BaseModel):
    """Vault timeline event response."""

    id: int = Field(..., description="事件 ID")
    project_id: int = Field(..., description="所属项目 ID")
    chapter_number: int = Field(..., description="事件章节号")
    event: str = Field(..., description="事件标题")
    description: str = Field(..., description="事件描述")
    is_key_event: bool = Field(default=False, description="是否关键事件")
    impact: Optional[str] = Field(default=None, description="事件影响")
    characters_involved: Optional[list] = Field(default=None, description="涉及角色")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class PlotPromiseResp(BaseModel):
    """Vault plot promise response."""

    id: int = Field(..., description="伏笔 ID")
    project_id: int = Field(..., description="所属项目 ID")
    description: str = Field(..., description="伏笔描述")
    type: str = Field(..., description="伏笔类型")
    status: str = Field(default="dormant", description="伏笔状态")
    urgency: int = Field(default=0, description="紧迫度")
    related_characters: Optional[list] = Field(default=None, description="相关角色")
    planted_chapter: Optional[int] = Field(default=None, description="埋下章节")
    advancement_log: Optional[list] = Field(default=None, description="推进日志")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class WorldResp(BaseModel):
    """Vault world entry response."""

    id: int = Field(..., description="条目 ID")
    project_id: int = Field(..., description="所属项目 ID")
    term: str = Field(..., description="术语名称")
    description: str = Field(..., description="条目描述")
    category: str = Field(..., description="类别")
    change_type: Optional[str] = Field(default=None, description="变更类型")
    rules: Optional[list] = Field(default=None, description="相关规则")
    reference_chapters: Optional[list] = Field(default=None, description="引用章节")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
