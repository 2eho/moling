"""
墨灵 (Moling) — 连载书导入引擎（Ingest Engine）

对应后端设计文档 v1.0 第十章「连载书导入引擎」。

模块职责
  - Phase 0: 分章与预览（由 app.ingest.scraper 实现）
  - Phase 1: 全量四库分析（异步 LLM 调用）
  - Phase 2: 近三章动态层分析
  - Phase 3: 确认导入与事务写入

当前实现状态
  ✅ Phase 0 — 完整实现（含 URL 采集、HTML 提取、章节拆分、段落拆分、目录遍历）
  ❌ Phase 1 — 待实现
  ❌ Phase 2 — 待实现
  ❌ Phase 3 — 待实现
"""

from app.ingest.scraper import (
    dissect_html,
    dissect_from_url,
    dissect_text,
    DissectResult,
    DissectorConfig,
    default_config,
    Chapter,
    Paragraph,
)
from app.ingest.scraper.core.toc_crawler import (
    TOCFetcher,
    ChapterBatchCrawler,
)

__all__ = [
    "dissect_html",
    "dissect_from_url",
    "dissect_text",
    "DissectResult",
    "DissectorConfig",
    "default_config",
    "Chapter",
    "Paragraph",
    "TOCFetcher",
    "ChapterBatchCrawler",
]
