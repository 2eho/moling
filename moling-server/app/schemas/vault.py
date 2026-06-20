"""墨灵 (Moling) — Vault-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ========== Create Schemas ==========


class CharacterCreate(BaseModel):
    """Vault character create request."""

    name: str = Field(..., min_length=1, max_length=100, description="角色名称")
    role: str = Field(..., description="角色定位")
    faction: Optional[str] = Field(default=None, max_length=100, description="所属阵营")
    status: str = Field(default="active", description="角色状态")
    emotion: Optional[str] = Field(default=None, max_length=50, description="当前情绪")
    traits: Optional[list] = Field(default=None, description="性格特征")
    description: Optional[str] = Field(default=None, description="角色描述")
    background: Optional[str] = Field(default=None, description="角色背景")
    relationships: Optional[list] = Field(default=None, description="人际关系")
    state_machine: Optional[dict] = Field(default=None, description="状态机数据")
    location: Optional[str] = Field(default=None, max_length=200, description="当前位置")
    appearance: Optional[str] = Field(default=None, description="外貌描述")
    personality: Optional[str] = Field(default=None, description="性格描述")
    knowledge: Optional[list] = Field(default=None, description="知识/能力列表")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")
    chapter_hist: Optional[list] = Field(default=None, description="章节历史")
    current_state: Optional[str] = Field(default=None, description="当前状态")
    motivation: Optional[str] = Field(default=None, description="动机/目标")


class TimelineCreate(BaseModel):
    """Vault timeline event create request."""

    chapter_number: int = Field(..., ge=0, description="事件章节号")
    event: str = Field(..., min_length=1, max_length=300, description="事件标题")
    description: str = Field(..., min_length=1, description="事件描述")
    is_key_event: bool = Field(default=False, description="是否关键事件")
    impact: Optional[str] = Field(default=None, max_length=200, description="事件影响")
    characters_involved: Optional[list] = Field(default=None, description="涉及角色")
    day: Optional[int] = Field(default=None, description="绝对时间线天数")
    title: Optional[str] = Field(default=None, max_length=200, description="事件标题")
    importance: Optional[str] = Field(default=None, description="重要性")
    source_chapter: Optional[int] = Field(default=None, description="来源章节号")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")


class PlotPromiseCreate(BaseModel):
    """Vault plot promise create request."""

    description: str = Field(..., min_length=1, description="伏笔描述")
    type: str = Field(..., description="伏笔类型")
    status: str = Field(default="dormant", description="伏笔状态")
    urgency: int = Field(default=0, ge=0, le=10, description="紧迫度")
    related_characters: Optional[list] = Field(default=None, description="相关角色")
    planted_chapter: Optional[int] = Field(default=None, description="埋下章节")
    advancement_log: Optional[list] = Field(default=None, description="推进日志")
    title: Optional[str] = Field(default=None, max_length=200, description="承诺标题")
    redeem_window: Optional[int] = Field(default=None, description="兑现窗口")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")


class WorldCreate(BaseModel):
    """Vault world entry create request."""

    name: str = Field(..., min_length=1, max_length=200, description="术语名称")
    description: str = Field(..., min_length=1, description="条目描述")
    category: str = Field(..., description="类别")
    change_type: Optional[str] = Field(default=None, description="变更类型")
    rules: Optional[list] = Field(default=None, description="相关规则")
    reference_chapters: Optional[list] = Field(default=None, description="引用章节")
    related_entities: Optional[list] = Field(default=None, description="相关实体列表")
    source_chapter: Optional[int] = Field(default=None, description="来源章节号")
    constraint: Optional[str] = Field(default=None, description="约束/规则描述")


# ========== Update Schemas ==========


class CharacterUpdate(BaseModel):
    """Vault character partial update (all fields optional)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="角色名称")
    role: Optional[str] = Field(default=None, description="角色定位")
    faction: Optional[str] = Field(default=None, max_length=100, description="所属阵营")
    status: Optional[str] = Field(default=None, description="角色状态")
    emotion: Optional[str] = Field(default=None, max_length=50, description="当前情绪")
    traits: Optional[list] = Field(default=None, description="性格特征")
    description: Optional[str] = Field(default=None, description="角色描述")
    background: Optional[str] = Field(default=None, description="角色背景")
    relationships: Optional[list] = Field(default=None, description="人际关系")
    state_machine: Optional[dict] = Field(default=None, description="状态机数据")
    location: Optional[str] = Field(default=None, max_length=200, description="当前位置")
    appearance: Optional[str] = Field(default=None, description="外貌描述")
    personality: Optional[str] = Field(default=None, description="性格描述")
    knowledge: Optional[list] = Field(default=None, description="知识/能力列表")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")
    chapter_hist: Optional[list] = Field(default=None, description="章节历史")
    current_state: Optional[str] = Field(default=None, description="当前状态")
    motivation: Optional[str] = Field(default=None, description="动机/目标")


class TimelineUpdate(BaseModel):
    """Vault timeline event partial update (all fields optional)."""

    chapter_number: Optional[int] = Field(default=None, ge=0, description="事件章节号")
    event: Optional[str] = Field(default=None, min_length=1, max_length=300, description="事件标题")
    description: Optional[str] = Field(default=None, min_length=1, description="事件描述")
    is_key_event: Optional[bool] = Field(default=None, description="是否关键事件")
    impact: Optional[str] = Field(default=None, max_length=200, description="事件影响")
    characters_involved: Optional[list] = Field(default=None, description="涉及角色")
    day: Optional[int] = Field(default=None, description="绝对时间线天数")
    title: Optional[str] = Field(default=None, max_length=200, description="事件标题")
    importance: Optional[str] = Field(default=None, description="重要性")
    source_chapter: Optional[int] = Field(default=None, description="来源章节号")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")


class PlotPromiseUpdate(BaseModel):
    """Vault plot promise partial update (all fields optional)."""

    description: Optional[str] = Field(default=None, min_length=1, description="伏笔描述")
    type: Optional[str] = Field(default=None, description="伏笔类型")
    status: Optional[str] = Field(default=None, description="伏笔状态")
    urgency: Optional[int] = Field(default=None, ge=0, le=10, description="紧迫度")
    related_characters: Optional[list] = Field(default=None, description="相关角色")
    planted_chapter: Optional[int] = Field(default=None, description="埋下章节")
    advancement_log: Optional[list] = Field(default=None, description="推进日志")
    title: Optional[str] = Field(default=None, max_length=200, description="承诺标题")
    redeem_window: Optional[int] = Field(default=None, description="兑现窗口")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")


class WorldUpdate(BaseModel):
    """Vault world entry partial update (all fields optional)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200, description="术语名称")
    description: Optional[str] = Field(default=None, min_length=1, description="条目描述")
    category: Optional[str] = Field(default=None, description="类别")
    change_type: Optional[str] = Field(default=None, description="变更类型")
    rules: Optional[list] = Field(default=None, description="相关规则")
    reference_chapters: Optional[list] = Field(default=None, description="引用章节")
    related_entities: Optional[list] = Field(default=None, description="相关实体列表")
    source_chapter: Optional[int] = Field(default=None, description="来源章节号")
    constraint: Optional[str] = Field(default=None, description="约束/规则描述")


# ========== Response Schemas ==========


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

    id: str = Field(..., description="事件 ID (UUID)")
    project_id: str = Field(..., description="所属项目 ID")
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

    id: str = Field(..., description="条目 ID (UUID)")
    project_id: str = Field(..., description="所属项目 ID")
    name: str = Field(..., description="术语名称")
    description: str = Field(..., description="条目描述")
    category: str = Field(..., description="类别")
    change_type: Optional[str] = Field(default=None, description="变更类型")
    rules: Optional[list] = Field(default=None, description="相关规则")
    reference_chapters: Optional[list] = Field(default=None, description="引用章节")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
