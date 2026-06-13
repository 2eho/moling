"""
墨灵 (Moling) — Ingest Phase 1: 全量四库分析

对应后端设计文档 v1.0 第十章第 10.4 节。
从已拆解的章节中提取四库数据：
  - I1: 人物库提取
  - I2: 时间线提取
  - I3: 剧情承诺提取
  - I4: 世界观提取
"""

from app.ingest.phase1.schemas import (
    Phase1Input,
    Phase1Result,
    Phase1Progress,
    CharacterExtraction,
    TimelineExtraction,
    PlotPromiseExtraction,
    WorldExtraction,
    MergedCharacter,
    MergedTimelineEvent,
    MergedPlotPromise,
    MergedWorldItem,
)
from app.ingest.phase1.extractor import (
    I1_extract_characters,
    I2_extract_timeline,
    I3_extract_promises,
    I4_extract_world,
    extract_chapter_all,
)
from app.ingest.phase1.merger import (
    merge_characters,
    merge_similar_events,
    merge_promises,
    merge_world_items,
)
from app.ingest.phase1.scheduler import (
    LLMBatchConfig,
    LLMScheduler,
    run_phase1_pipeline,
)

__all__ = [
    "Phase1Input",
    "Phase1Result",
    "Phase1Progress",
    "CharacterExtraction",
    "TimelineExtraction",
    "PlotPromiseExtraction",
    "WorldExtraction",
    "MergedCharacter",
    "MergedTimelineEvent",
    "MergedPlotPromise",
    "MergedWorldItem",
    "I1_extract_characters",
    "I2_extract_timeline",
    "I3_extract_promises",
    "I4_extract_world",
    "extract_chapter_all",
    "merge_characters",
    "merge_similar_events",
    "merge_promises",
    "merge_world_items",
    "LLMBatchConfig",
    "LLMScheduler",
    "run_phase1_pipeline",
]
