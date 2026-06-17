"""
墨灵 (Moling) — 拆书爬虫引擎 / Genre Profile 分析

对应后端设计文档 v1.0 第九章「拆书引擎（离线）」。
与 app.ingest (连载书导入引擎) 完全独立：

  ┌─────────────────────────────────────────────────────┐
  │ app.ingest (管线 A / §10)                         │
  │ 定位：用户导入自己的小说继续写                       │
  │ 核心：dissect → 四库提取 → 动态层 → 续写           │
  │ 代码：app/ingest/scraper/ + phase1/2/3/            │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │ app.genre (管线 B / §9)                            │
  │ 定位：爬取热门网文分析套路 → 冷启动新书              │
  │ 核心：A1→A2→A3→A4→A5 → Genre Profile               │
  │ 代码：app/genre/                                    │
  └─────────────────────────────────────────────────────┘

用法：
    from app.genre import run_full_analysis

    chapters = ["第一章正文...", "第二章正文...", ...]
    profile = run_full_analysis(chapters, genre="玄幻")

    print(profile.character_archetypes)
"""

from __future__ import annotations

from app.genre.a1_opening import A1_analyze_opening, A1Result, OpeningPattern
from app.genre.a2_characters import A2_cluster_characters, A2Result, CharacterEntry, CharacterTimingTemplate
from app.genre.a3_hooks import A3_quantify_hooks, A3Result, ChapterHookResult
from app.genre.a4_rhythm import A4_fit_rhythm_curve, A4Result, RhythmProfile
from app.genre.a5_profile_output import A5_summarize_patterns, profile_to_json
from app.genre.models import GenreProfile


def run_full_analysis(
    chapters: list[str],
    genre: str = "",
    novels_analyzed: int = 1,
) -> GenreProfile:
    """
    完整执行 A1→A2→A3→A4→A5 拆书分析管线。

    参数
        chapters        — 章节正文列表（每章一个字符串）
        genre           — 小说类型（如 "玄幻"、"都市"）
        novels_analyzed — 已分析的小说数量（计数用）

    返回
        GenreProfile 对象（可调 .json() 输出）
    """
    # A1: 黄金三章结构提取
    a1 = A1_analyze_opening(chapters[:3])

    # A2: 角色出场模式聚类
    a2 = A2_cluster_characters(chapters[:3])

    # A3: 钩子密度量化
    a3 = A3_quantify_hooks(chapters[:5])  # 最多分析前5章

    # A4: 节奏曲线拟合（依赖 A3 的密度曲线）
    a4 = A4_fit_rhythm_curve(chapters[:5], a3.density_curve)

    # A5: 套路归纳 + 去版权化 → Genre Profile
    profile = A5_summarize_patterns(
        a1=a1,
        a2=a2,
        a3=a3,
        a4=a4,
        genre=genre,
        novels_analyzed=novels_analyzed,
    )

    return profile


# --- Cold Start & Data Retirement ---
from app.genre.cold_start_loader import (
    ColdStartLoader,
    DataRetirementManager,
    PrefillResult,
    VaultPrefill,
    DynamicLayerPrefill,
    CardPrefill,
    CharacterPrototype,
    cold_start_loader,
)

__all__ = [
    "run_full_analysis",
    "GenreProfile",
    "ColdStartLoader",
    "DataRetirementManager",
    "PrefillResult",
    "VaultPrefill",
    "DynamicLayerPrefill",
    "CardPrefill",
    "CharacterPrototype",
    "cold_start_loader",
    "A1Result", "A2Result", "A3Result", "A4Result",
    "A1_analyze_opening",
    "A2_cluster_characters",
    "A3_quantify_hooks",
    "A4_fit_rhythm_curve",
    "A5_summarize_patterns",
    "profile_to_json",
]

__version__ = "0.1.0"
