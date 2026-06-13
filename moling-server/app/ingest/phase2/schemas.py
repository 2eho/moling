"""
墨灵 (Moling) — Ingest Phase 2 数据模型
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChapterAnchor:
    """I5 章节锚点"""
    chapter_index: int
    chapter_title: str
    opening_hook: bool = False
    midpoint_turn: Optional[dict] = None
    closing_cliff: bool = False
    action_peak: Optional[float] = None


@dataclass
class OpenHook:
    """I7 未收束钩子"""
    type: str
    text: str
    context: str = ""
    chapter_index: int = 0
    created_at: str = ""
    age_in_chapters: int = 0
    stale: bool = False


@dataclass
class FeasibilityReport:
    """I9 可行性基线评估"""
    plot_density: float = 0.0
    loose_thread_count: int = 0
    continuation_confidence: float = 0.0
    coherence: dict = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class Phase2Input:
    """Phase 2 输入"""
    chapters: list[dict]
    characters: list[dict] = field(default_factory=list)
    timeline_events: list[dict] = field(default_factory=list)
    promises: list[dict] = field(default_factory=list)
    world_items: list[dict] = field(default_factory=list)
    recent_n: int = 3


@dataclass
class Phase2Result:
    """Phase 2 完整输出"""
    chapter_anchors: list[ChapterAnchor] = field(default_factory=list)
    coherence: dict = field(default_factory=dict)
    open_hooks: list[OpenHook] = field(default_factory=list)
    recent_changes: list[str] = field(default_factory=list)
    feasibility: FeasibilityReport = field(default_factory=FeasibilityReport)
