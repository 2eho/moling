"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / config.py
全局配置管理
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

对标写作猫 Go 版 config/config.go 中采集相关配置项。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from novel_dissector.core.fetcher import AntiCrawlConfig


@dataclass
class DissectorConfig:
    """
    拆书引擎全局配置。

    典型初始化
        from novel_dissector.config import DissectorConfig, default_config
        cfg = default_config()
        cfg.anti_crawl.delay_min_ms = 2000
    """

    # ── 反爬配置 ──
    anti_crawl: AntiCrawlConfig = field(default_factory=AntiCrawlConfig)

    # ── 正文提取 ──
    extract_timeout_seconds: int = 45
    extract_max_concurrency: int = 1     # 并发请求上限
    try_trafilatura: bool = True          # 是否尝试 trafilatura 提取
    try_common_selectors: bool = True     # 是否遍历常见内容容器

    # ── 内容清洗 ──
    min_clean_chars: int = 80            # 清洗后最少字符数（低于此视为无效）

    # ── 章节拆分 ──
    default_split_strategies: list[str] = field(
        default_factory=lambda: ["chapter_regex", "paragraph"],
    )
    min_chapter_chars: int = 100          # 有效章节最少字符数
    max_chapter_chars: int = 50000        # 单章最大字符数
    min_para_chars: int = 10              # 有效段落最少字符数
    merge_short_lines: bool = True        # 是否合并短行

    # ── 输出 ──
    output_include_raw: bool = False       # 输出是否包含原始 HTML/文本（默认不包含）
    output_ensure_ascii: bool = False      # JSON 是否确保 ASCII

    # ── 存储 ──
    cache_dir: Optional[str] = None       # 缓存目录（可选）


def default_config() -> DissectorConfig:
    """返回默认配置。可直接修改字段覆盖。"""
    import copy
    return copy.deepcopy(_DEFAULT_CFG)


_DEFAULT_CFG = DissectorConfig()
