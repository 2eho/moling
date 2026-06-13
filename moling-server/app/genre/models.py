"""
墨灵 (Moling) — genre / models.py
拆书爬虫引擎数据模型定义

对应文档 §9.5 Genre Profile 数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenreProfile:
    """类型知识库 — A5 最终输出"""
    genre: str = ""
    version: str = "0.1"
    chapters_analyzed: int = 0
    novels_analyzed: int = 0
    golden_three_structure: dict[str, Any] = field(default_factory=dict)
    character_archetypes: list[dict] = field(default_factory=list)
    world_templates: list[dict] = field(default_factory=list)
    pacing_curve: dict[str, list[float]] = field(default_factory=dict)
    card_pool_enrichment: list[dict] = field(default_factory=list)
    dynamic_layer_seeds: dict[str, Any] = field(default_factory=dict)
    style_fingerprint: dict[str, Any] = field(default_factory=dict)
