"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / pipeline.py
全流程编排管线
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

提供三个入口函数：
  dissect_html(html, ...)       — 从 HTML 字符串拆解
  dissect_from_url(url, ...)    — 从 URL 采集并拆解
  dissect_text(text, ...)       — 从纯文本直接拆解

每个入口返回统一的 DissectResult 数据结构。
"""

from __future__ import annotations

import logging
from typing import Optional

from novel_dissector.models.schemas import (
    Chapter,
    ContentSource,
    DissectResult,
    SplitStrategy,
)
from novel_dissector.core.cleaner import (
    clean_html,
    extract_title_from_html,
)
from novel_dissector.core.fetcher import Fetcher, AntiCrawlConfig, FetchResult
from novel_dissector.core.extractor import extract_content
from novel_dissector.core.style_analyzer import analyze_style_from_result
from novel_dissector.splitter.strategies import split_text
from novel_dissector.config import DissectorConfig, default_config

logger = logging.getLogger(__name__)


# =========================================================================
# 入口函数
# =========================================================================


def dissect_html(
    raw_html: str,
    source_url: str = "",
    split_strategies: Optional[list[str]] = None,
    config: Optional[DissectorConfig] = None,
    **kwargs,
) -> DissectResult:
    """
    从 HTML 字符串拆解书籍。

    流程：HTML → 正文提取（选择器/trafilatura）→ 清洗 → 章节拆分 → 段落拆分

    参数
        raw_html          — 完整 HTML 页面内容
        source_url        — 来源 URL（用于 trafilatura 和后继追踪）
        split_strategies  — 拆分策略管线（默认 ["chapter_regex", "paragraph"]）
        config            — 全局配置（默认 default_config()）
        **kwargs          — 透传给拆分策略的额外参数

    返回
        DissectResult（含 .json() 方法）
    """
    cfg = config or default_config()
    if split_strategies is None:
        split_strategies = cfg.default_split_strategies

    result = DissectResult(
        source_url=source_url,
        content_source=ContentSource.RAW_HTML.value,
        split_strategies_used=split_strategies,
    )

    try:
        # Step 1: 提取标题
        result.title = extract_title_from_html(raw_html)

        # Step 2: 正文提取
        extracted = extract_content(
            html=raw_html,
            url=source_url,
            try_trafilatura=cfg.try_trafilatura,
            try_common_selectors=cfg.try_common_selectors,
        )
        if extracted.error:
            result.errors.append(f"正文提取: {extracted.error}")

        if not extracted.text or len(extracted.text.strip()) < cfg.min_clean_chars:
            result.errors.append("正文提取结果过短，可能未能正确提取内容")
            return result

        result.stats["extract_method"] = extracted.method
        result.stats["extract_quality_score"] = extracted.quality_score

        # Step 3: 清洗
        cleaned_text = clean_html(extracted.text)
        if not cleaned_text or len(cleaned_text) < cfg.min_clean_chars:
            result.errors.append("清洗后文本过短")
            return result

        result.stats["raw_chars"] = len(raw_html)
        result.stats["extracted_chars"] = len(extracted.text)
        result.stats["cleaned_chars"] = len(cleaned_text)

        # Step 4: 拆分
        chapters = split_text(
            cleaned_text,
            strategies=split_strategies,
            min_chapter_chars=cfg.min_chapter_chars,
            max_chapter_chars=cfg.max_chapter_chars,
            min_para_chars=cfg.min_para_chars,
            merge_short_lines=cfg.merge_short_lines,
            **kwargs,
        )

        result.chapters = chapters
        result._recalc()

        # Step 5: 文风分析
        try:
            style_fp = analyze_style_from_result(result)
            result.stats["style_fingerprint"] = style_fp.to_dict()
        except Exception:
            logger.exception("文风分析异常（非致命）")

    except Exception as exc:
        logger.exception("拆解过程异常")
        result.errors.append(f"拆解异常: {exc}")

    return result


def dissect_from_url(
    url: str,
    split_strategies: Optional[list[str]] = None,
    config: Optional[DissectorConfig] = None,
    anti_crawl_config: Optional[AntiCrawlConfig] = None,
    **kwargs,
) -> DissectResult:
    """
    从 URL 采集 HTML 并拆解。

    流程：HTTP 请求（带反爬）→ HTML → dissect_html

    参数
        url               — 目标页面地址（目录页或首章页）
        split_strategies  — 拆分策略管线
        config            — 全局配置
        anti_crawl_config — 反爬配置（覆盖 config.anti_crawl）
        **kwargs          — 透传给拆分策略

    返回
        DissectResult
    """
    cfg = config or default_config()
    if anti_crawl_config:
        cfg.anti_crawl = anti_crawl_config

    result = DissectResult(
        source_url=url,
        content_source=ContentSource.URL.value,
        split_strategies_used=split_strategies or cfg.default_split_strategies,
    )

    try:
        fetcher = Fetcher(cfg.anti_crawl)
        fetch_result = fetcher.get(url)

        if fetcher.is_hard_failure(fetch_result):
            result.errors.append(f"源站不可用: status={fetch_result.status_code}, error={fetch_result.error}")
            return result

        if fetch_result.error:
            result.errors.append(f"请求有警告: {fetch_result.error}")

        result.stats["fetch_status"] = fetch_result.status_code
        result.stats["fetch_elapsed_ms"] = fetch_result.elapsed_ms
        result.stats["fetch_text_length"] = len(fetch_result.text)

        # 透传给 dissect_html
        html_result = dissect_html(
            raw_html=fetch_result.text,
            source_url=url,
            split_strategies=split_strategies,
            config=cfg,
            **kwargs,
        )
        # 合并结果
        result.title = html_result.title
        result.chapters = html_result.chapters
        result.errors.extend(html_result.errors)
        result.stats.update(html_result.stats)
        result._recalc()

    except Exception as exc:
        logger.exception("URL 采集拆解异常")
        result.errors.append(f"URL 采集拆解异常: {exc}")

    return result


def dissect_text(
    text: str,
    title: str = "",
    split_strategies: Optional[list[str]] = None,
    config: Optional[DissectorConfig] = None,
    **kwargs,
) -> DissectResult:
    """
    从纯文本直接拆解（适用于已有清洗后的文本）。

    参数
        text              — 清洗后的纯文本
        title             — 书名（可选）
        split_strategies  — 拆分策略管线
        config            — 全局配置
        **kwargs          — 透传给拆分策略

    返回
        DissectResult
    """
    cfg = config or default_config()
    if split_strategies is None:
        split_strategies = cfg.default_split_strategies

    result = DissectResult(
        title=title,
        content_source=ContentSource.TEXT.value,
        split_strategies_used=split_strategies,
    )

    try:
        if not text or len(text.strip()) < cfg.min_clean_chars:
            result.errors.append("输入文本过短")
            return result

        cleaned = text.strip()
        result.stats["input_chars"] = len(cleaned)

        chapters = split_text(
            cleaned,
            strategies=split_strategies,
            min_chapter_chars=cfg.min_chapter_chars,
            max_chapter_chars=cfg.max_chapter_chars,
            min_para_chars=cfg.min_para_chars,
            merge_short_lines=cfg.merge_short_lines,
            **kwargs,
        )

        result.chapters = chapters
        result._recalc()

        # 文风分析
        try:
            style_fp = analyze_style_from_result(result)
            result.stats["style_fingerprint"] = style_fp.to_dict()
        except Exception:
            logger.exception("文风分析异常（非致命）")

    except Exception as exc:
        logger.exception("文本拆解异常")
        result.errors.append(f"文本拆解异常: {exc}")

    return result
