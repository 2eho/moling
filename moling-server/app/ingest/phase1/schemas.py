"""
墨灵 (Moling) — Ingest Phase 1 Schemas

定义 Phase 1 全量四库分析的输入/输出数据结构。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────── 提取结果（单章级别）


class CharacterExtraction(BaseModel):
    """I1 角色提取 — 单章结果"""
    name: str = Field(description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="角色别名列表")
    dialogue_count: int = Field(default=0, description="对话句数")
    description: str = Field(default="", description="角色描述")
    tags: list[str] = Field(default_factory=list, description="角色标签（主角/反派/盟友等）")
    chapter_index: int = Field(default=0, description="所属章节索引")


class TimelineExtraction(BaseModel):
    """I2 时间线提取 — 单章结果"""
    description: str = Field(description="事件描述")
    relative_time: str = Field(default="", description="相对时间")
    time_anchor: str = Field(default="", description="时间锚点")
    characters: list[str] = Field(default_factory=list, description="涉及角色")
    importance: int = Field(default=3, description="重要性 1-5")
    chapter_index: int = Field(default=0, description="所属章节索引")


class PlotPromiseExtraction(BaseModel):
    """I3 剧情承诺提取 — 单章结果"""
    type: str = Field(description="承诺类型: explicit_promise / implicit_promise / mystery")
    text: str = Field(description="承诺文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    related_characters: list[str] = Field(default_factory=list, description="相关角色")


class WorldExtraction(BaseModel):
    """I4 世界观提取 — 单章结果"""
    term: str = Field(description="世界观术语")
    description: str = Field(default="", description="术语描述")
    category: str = Field(default="other", description="分类: geography / magic / technology / culture / history / rule / other")
    chapter_index: int = Field(default=0, description="所属章节索引")
    related_terms: list[str] = Field(default_factory=list, description="相关术语")


class ChapterAnalysis(BaseModel):
    """单章的全部分析结果"""
    chapter_index: int = Field(description="章节索引")
    chapter_title: str = Field(description="章节标题")
    characters: list[CharacterExtraction] = Field(default_factory=list, description="角色提取结果")
    timeline_events: list[TimelineExtraction] = Field(default_factory=list, description="时间线提取结果")
    promises: list[PlotPromiseExtraction] = Field(default_factory=list, description="剧情承诺提取结果")
    world_items: list[WorldExtraction] = Field(default_factory=list, description="世界观提取结果")
    error: Optional[str] = Field(default=None, description="该章错误信息")


# ──────────────────────────────────────────────── 合并后结果（全书级别）


class MergedCharacter(BaseModel):
    """合并去重后的角色"""
    name: str = Field(description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="角色别名")
    first_appearance: int = Field(default=0, description="首次出场章节")
    chapters_active: list[int] = Field(default_factory=list, description="活跃章节列表")
    dialogue_count: int = Field(default=0, description="总对话数")
    description: str = Field(default="", description="角色描述")
    tags: list[str] = Field(default_factory=list, description="角色标签")


class MergedTimelineEvent(BaseModel):
    """合并后的时间线事件"""
    description: str = Field(description="事件描述")
    relative_time: str = Field(default="", description="相对时间")
    time_anchor: str = Field(default="", description="时间锚点")
    characters: list[str] = Field(default_factory=list, description="涉及角色")
    importance: int = Field(default=3, description="重要性 1-5")
    chapter_index: int = Field(default=0, description="关键章节索引")
    is_key_event: bool = Field(default=False, description="是否为关键事件")


class MergedPlotPromise(BaseModel):
    """合并后的剧情承诺"""
    type: str = Field(description="承诺类型")
    text: str = Field(description="承诺文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    status: str = Field(default="dormant", description="状态: dormant / active / advancing / resolved / abandoned")
    urgency: int = Field(default=5, ge=0, le=10, description="紧迫度 0-10")
    related_characters: list[str] = Field(default_factory=list, description="相关角色")


class MergedWorldItem(BaseModel):
    """合并后的世界观条目"""
    term: str = Field(description="术语")
    description: str = Field(default="", description="描述")
    category: str = Field(default="other", description="分类")
    first_appearance: int = Field(default=0, description="首次出场章节")
    reference_chapters: list[int] = Field(default_factory=list, description="引用章节")
    related_terms: list[str] = Field(default_factory=list, description="相关术语")


# ──────────────────────────────────────────────── 输入/输出


class Phase1Input(BaseModel):
    """Phase 1 输入 — 由 Phase 0 产生的拆解结果"""
    project_id: str = Field(description="项目 ID")
    chapters: list[dict[str, Any]] = Field(description="拆解后的章节数据列表")
    total_chapters: int = Field(default=0, description="总章节数")


class Phase1Result(BaseModel):
    """Phase 1 完整输出"""
    characters: list[MergedCharacter] = Field(default_factory=list, description="合并后的角色列表")
    timeline_events: list[MergedTimelineEvent] = Field(default_factory=list, description="合并后的时间线事件")
    promises: list[MergedPlotPromise] = Field(default_factory=list, description="合并后的剧情承诺")
    world_items: list[MergedWorldItem] = Field(default_factory=list, description="合并后的世界观条目")
    chapter_count: int = Field(default=0, description="已分析章节数")
    total_llm_calls: int = Field(default=0, description="LLM 调用总数")
    failed_llm_calls: int = Field(default=0, description="LLM 调用失败数")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")


class Phase1Progress(BaseModel):
    """Phase 1 进度（用于轮询）"""
    status: str = Field(default="pending", description="状态: pending / running / completed / failed")
    phase: str = Field(default="phase1", description="阶段标识")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    completed_chapters: int = Field(default=0, description="已完成章节数")
    total_chapters: int = Field(default=0, description="总章节数")
    failed_calls: int = Field(default=0, description="失败调用数")
    current_task: str = Field(default="", description="当前任务描述")
    result: Optional[Phase1Result] = Field(default=None, description="分析结果（完成时填入）")
    error: Optional[str] = Field(default=None, description="错误信息")
