"""
墨灵 (Moling) — Ingest Phase 2: 近三章动态层分析

对应后端设计文档 v1.0 第十章第 10.5 节。
分析最近 N 章的结构与连贯性：
  - I5: 章节锚点分析
  - I6: 连贯性基线评估
  - I7: 未收束钩子识别
  - I8: 最近变更摘要
  - I9: 可行性基线评估
"""

from __future__ import annotations

from app.ingest.phase2.schemas import (
    ChapterAnchor,
    FeasibilityReport,
    OpenHook,
    Phase2Input,
    Phase2Result,
)
from app.ingest.phase2.analyzer import (
    I5_chapter_anchors,
    I6_coherence_baseline,
    I7_open_hooks,
    I8_recent_changes,
    I9_feasibility_check,
)

__all__ = [
    "Phase2Input",
    "Phase2Result",
    "ChapterAnchor",
    "OpenHook",
    "FeasibilityReport",
    "run_phase2_pipeline",
    "I5_chapter_anchors",
    "I6_coherence_baseline",
    "I7_open_hooks",
    "I8_recent_changes",
    "I9_feasibility_check",
]


# ──────────────────────────────────────────────── 流水线


def run_phase2_pipeline(input_data: Phase2Input) -> Phase2Result:
    """
    运行 Phase 2 动态层分析流水线。

    全部使用规则/算法分析，不需要 LLM 调用。
    """
    chapters = input_data.chapters
    recent_n = input_data.recent_n

    # I5: 章节锚点分析
    anchors = I5_chapter_anchors(chapters, recent_n)

    # I6: 连贯性基线评估
    coherence = I6_coherence_baseline(chapters, recent_n)

    # I7: 未收束钩子识别
    hooks = I7_open_hooks(chapters, recent_n)

    # I8: 最近变更摘要
    changes = I8_recent_changes(chapters, recent_n)

    # I9: 可行性基线评估
    feasibility = I9_feasibility_check(
        chapters=chapters,
        recent_n=recent_n,
        open_hooks=hooks,
        coherence=coherence,
    )

    return Phase2Result(
        chapter_anchors=anchors,
        coherence=coherence,
        open_hooks=hooks,
        recent_changes=changes,
        feasibility=feasibility,
    )
