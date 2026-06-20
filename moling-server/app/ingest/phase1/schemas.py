"""
墨灵 (Moling) — Ingest Phase 1 Schemas

定义 Phase 1 全量四库分析的输入/输出数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ──────────────────────────────────────────────── 提取结果（单章级别）


@dataclass
class CharacterExtraction:
    """I1 角色提取 — 单章结果"""
    name: str
    aliases: list[str] = field(default_factory=list)
    dialogue_count: int = 0
    description: str = ""
    tags: list[str] = field(default_factory=list)
    chapter_index: int = 0


@dataclass
class TimelineExtraction:
    """I2 时间线提取 — 单章结果"""
    description: str
    relative_time: str = ""
    time_anchor: str = ""
    characters: list[str] = field(default_factory=list)
    importance: int = 3  # 1-5
    chapter_index: int = 0


@dataclass
class PlotPromiseExtraction:
    """I3 剧情承诺提取 — 单章结果"""
    type: str  # explicit_promise / implicit_promise / mystery
    text: str
    context: str = ""
    chapter_index: int = 0
    related_characters: list[str] = field(default_factory=list)


@dataclass
class WorldExtraction:
    """I4 世界观提取 — 单章结果"""
    term: str
    description: str = ""
    category: str = "other"  # geography / magic / technology / culture / history / rule / other
    chapter_index: int = 0
    related_terms: list[str] = field(default_factory=list)


@dataclass
class ChapterAnalysis:
    """单章的全部分析结果"""
    chapter_index: int
    chapter_title: str
    characters: list[CharacterExtraction] = field(default_factory=list)
    timeline_events: list[TimelineExtraction] = field(default_factory=list)
    promises: list[PlotPromiseExtraction] = field(default_factory=list)
    world_items: list[WorldExtraction] = field(default_factory=list)
    error: Optional[str] = None


# ──────────────────────────────────────────────── 合并后结果（全书级别）


@dataclass
class MergedCharacter:
    """合并去重后的角色"""
    name: str
    aliases: list[str] = field(default_factory=list)
    first_appearance: int = 0
    chapters_active: list[int] = field(default_factory=list)
    dialogue_count: int = 0
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class MergedTimelineEvent:
    """合并后的时间线事件"""
    description: str
    relative_time: str = ""
    time_anchor: str = ""
    characters: list[str] = field(default_factory=list)
    importance: int = 3
    chapter_index: int = 0
    is_key_event: bool = False


@dataclass
class MergedPlotPromise:
    """合并后的剧情承诺"""
    type: str
    text: str
    context: str = ""
    chapter_index: int = 0
    status: str = "dormant"  # dormant / active / advancing / resolved / abandoned
    urgency: int = 5  # 0-10
    related_characters: list[str] = field(default_factory=list)


@dataclass
class MergedWorldItem:
    """合并后的世界观条目"""
    term: str
    description: str = ""
    category: str = "other"
    first_appearance: int = 0
    reference_chapters: list[int] = field(default_factory=list)
    related_terms: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────── 输入/输出


@dataclass
class Phase1Input:
    """Phase 1 输入 — 由 Phase 0 产生的拆解结果"""
    project_id: str
    chapters: list[dict]  # DissectResult.chapters 的 dict 格式
    total_chapters: int = 0


@dataclass
class Phase1Result:
    """Phase 1 完整输出"""
    characters: list[MergedCharacter] = field(default_factory=list)
    timeline_events: list[MergedTimelineEvent] = field(default_factory=list)
    promises: list[MergedPlotPromise] = field(default_factory=list)
    world_items: list[MergedWorldItem] = field(default_factory=list)
    chapter_count: int = 0
    total_llm_calls: int = 0
    failed_llm_calls: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class Phase1Progress:
    """Phase 1 进度（用于轮询）"""
    status: str = "pending"  # pending / running / completed / failed
    phase: str = "phase1"
    progress_percent: float = 0.0
    completed_chapters: int = 0
    total_chapters: int = 0
    failed_calls: int = 0
    current_task: str = ""
    result: Optional[Phase1Result] = None
    error: Optional[str] = None


def chapter_analysis_to_dict(analysis: ChapterAnalysis) -> dict:
    """将 ChapterAnalysis 转为字典"""
    return {
        "chapter_index": analysis.chapter_index,
        "chapter_title": analysis.chapter_title,
        "characters": [
            {"name": c.name, "aliases": c.aliases, "dialogue_count": c.dialogue_count,
             "description": c.description, "tags": c.tags, "chapter_index": c.chapter_index}
            for c in analysis.characters
        ],
        "timeline_events": [
            {"description": e.description, "relative_time": e.relative_time,
             "time_anchor": e.time_anchor, "characters": e.characters,
             "importance": e.importance, "chapter_index": e.chapter_index}
            for e in analysis.timeline_events
        ],
        "promises": [
            {"type": p.type, "text": p.text, "context": p.context,
             "chapter_index": p.chapter_index, "related_characters": p.related_characters}
            for p in analysis.promises
        ],
        "world_items": [
            {"term": w.term, "description": w.description, "category": w.category,
             "chapter_index": w.chapter_index, "related_terms": w.related_terms}
            for w in analysis.world_items
        ],
        "error": analysis.error,
    }
