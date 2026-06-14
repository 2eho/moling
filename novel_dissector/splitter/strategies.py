"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / splitter / strategies.py
策略注册与工厂
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

提供：
  - register_strategy()  — 注册自定义拆分策略
  - get_strategy()        — 按名称获取策略实例
  - list_strategies()     — 列出所有已注册策略
  - split_text()          — 便捷函数：对文本执行拆分管线

设计意图：策略引擎让用户可以注册自己的拆分逻辑，
不限于内置的章节/段落拆分器。注册后的策略可通过名称引用。
"""

from __future__ import annotations

from typing import Any, Optional

from novel_dissector.models.schemas import Chapter, SplitGranularity
from novel_dissector.splitter.base import BaseSplitter
from novel_dissector.splitter.chapter import ChapterRegexSplitter
from novel_dissector.splitter.paragraph import (
    DoubleNewlineSplitter,
    ParagraphSplitter,
)

# =========================================================================
# 策略注册表（线程安全 — 初始化时一次性填充）
# =========================================================================

_REGISTRY: dict[str, type[BaseSplitter]] = {}
_DEFAULT_INSTANCES: dict[str, BaseSplitter] = {}


def _register_default(name: str, cls: type[BaseSplitter], **kwargs):
    """注册默认策略及其实例。"""
    _REGISTRY[name] = cls
    _DEFAULT_INSTANCES[name] = cls(**kwargs)


# 注册内置策略
_register_default("chapter_regex", ChapterRegexSplitter)
_register_default("double_newline", DoubleNewlineSplitter)
_register_default("paragraph", ParagraphSplitter)


# =========================================================================
# 公开 API
# =========================================================================


def register_strategy(name: str, splitter_cls: type[BaseSplitter], **kwargs) -> None:
    """
    注册自定义拆分策略。
    注册后可通过 get_strategy(name) 或 split_text(text, strategies=[name]) 使用。

    示例
        class MySplitter(BaseSplitter):
            name = "my_splitter"
            def split(self, text, **kwargs):
                return [Chapter(index=1, title="唯一章", raw_text=text)]

        register_strategy("my_splitter", MySplitter)
    """
    _REGISTRY[name] = splitter_cls
    _DEFAULT_INSTANCES[name] = splitter_cls(**kwargs)


def get_strategy(name: str) -> Optional[BaseSplitter]:
    """
    按名称获取策略实例。
    返回一个浅拷贝副本（避免多线程共享状态）。
    """
    instance = _DEFAULT_INSTANCES.get(name)
    if instance is None:
        return None
    return instance.__class__(**instance.kwargs)


def list_strategies() -> list[str]:
    """列出所有已注册策略名。"""
    return list(_REGISTRY.keys())


def split_text(
    text: str,
    strategies: Optional[list[str]] = None,
    **kwargs,
) -> list[Chapter]:
    """
    便捷函数：使用指定策略管线拆分文本。

    参数
        text       — 清洗后的纯文本
        strategies — 策略管线，按顺序依次处理。
                     默认 ["chapter_regex", "paragraph"]：
                       1. chapter_regex → 按章节标题拆
                       2. paragraph → 每章内再拆段落

    返回
        最终的 Chapter 列表。如果最后一个策略是段落级，则每个
        Chapter 内部会包含 paragraphs 列表。

    示例
        chapters = split_text(cleaned_text)
        chapters = split_text(cleaned_text, ["chapter_regex"])
        chapters = split_text(cleaned_text, ["chapter_regex", "double_newline"])
    """
    if not strategies:
        strategies = ["chapter_regex", "paragraph"]

    chapters: list[Chapter] = []
    current_text = text

    for idx, strategy_name in enumerate(strategies):
        splitter = get_strategy(strategy_name)
        if splitter is None:
            raise ValueError(f"未注册的策略: {strategy_name}。可用: {list_strategies()}")

        if idx == 0:
            # 第一道：对原文本拆分
            chapters = splitter.split(current_text, **kwargs)
        else:
            # 后续道：对每章分别拆分（如段落拆分）
            if splitter.granularity in (
                SplitGranularity.PARAGRAPH,
                SplitGranularity.SENTENCE,
            ):
                # 段/句级拆分器 → 作用于每章
                if hasattr(splitter, "split_chapter"):
                    chapters = [splitter.split_chapter(ch) for ch in chapters]
                else:
                    new_chapters = []
                    for ch in chapters:
                        sub_chapters = splitter.split(ch.raw_text, **kwargs)
                        new_chapters.extend(sub_chapters)
                    chapters = new_chapters
            else:
                # 再次章节级拆分 → 作用于全文本
                chapters = splitter.split(current_text, **kwargs)

    return chapters
