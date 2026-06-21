"""
墨灵 (Moling) — Ingest Phase 2 数据模型
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChapterAnchor(BaseModel):
    """I5 章节锚点"""
    chapter_index: int = Field(description="章节索引")
    chapter_title: str = Field(description="章节标题")
    opening_hook: bool = Field(default=False, description="是否有开篇钩子")
    midpoint_turn: Optional[dict[str, Any]] = Field(default=None, description="中点转折信息")
    closing_cliff: bool = Field(default=False, description="是否有结尾悬念")
    action_peak: Optional[float] = Field(default=None, description="动作峰值强度")


class OpenHook(BaseModel):
    """I7 未收束钩子"""
    type: str = Field(description="钩子类型")
    text: str = Field(description="钩子文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    created_at: str = Field(default="", description="创建时间")
    age_in_chapters: int = Field(default=0, description="已存在章节数")
    stale: bool = Field(default=False, description="是否已过时")


class FeasibilityReport(BaseModel):
    """I9 可行性基线评估"""
    plot_density: float = Field(default=0.0, description="情节密度")
    loose_thread_count: int = Field(default=0, description="未收束线索数")
    continuation_confidence: float = Field(default=0.0, description="续写信心 0-1")
    coherence: dict[str, Any] = Field(default_factory=dict, description="连贯性指标")
    recommendation: str = Field(default="", description="可行性建议")


class Phase2Input(BaseModel):
    """Phase 2 输入"""
    chapters: list[dict[str, Any]] = Field(description="章节数据列表")
    characters: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 角色结果")
    timeline_events: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 时间线结果")
    promises: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 承诺结果")
    world_items: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 世界观结果")
    recent_n: int = Field(default=3, description="分析的最近章节数")


class Phase2Result(BaseModel):
    """Phase 2 完整输出"""
    chapter_anchors: list[ChapterAnchor] = Field(default_factory=list, description="章节锚点列表")
    coherence: dict[str, Any] = Field(default_factory=dict, description="连贯性分析结果")
    open_hooks: list[OpenHook] = Field(default_factory=list, description="未收束钩子列表")
    recent_changes: list[str] = Field(default_factory=list, description="最近变更摘要")
    feasibility: FeasibilityReport = Field(default_factory=FeasibilityReport, description="可行性评估")
