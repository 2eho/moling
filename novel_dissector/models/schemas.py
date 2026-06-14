"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / models / schemas.py
数据模型定义
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

全部基于 dataclasses + 标准库，零外部依赖。若下游项目使用
Pydantic v2，可通过 model_validate 或 construct 直接转换。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


# ──────────────────────────────────────────────── 枚举


class SplitGranularity(str, Enum):
    """拆分粒度"""
    VOLUME = "volume"          # 卷/部
    CHAPTER = "chapter"        # 章
    SECTION = "section"        # 节（章内分节）
    PARAGRAPH = "paragraph"    # 段落
    SENTENCE = "sentence"      # 句子


class ContentSource(str, Enum):
    """内容来源"""
    RAW_HTML = "raw_html"
    URL = "url"
    TEXT = "text"
    FILE = "file"


class SplitStrategy(str, Enum):
    """预设拆分策略标识"""
    CHAPTER_REGEX = "chapter_regex"
    CHAPTER_NLP = "chapter_nlp"
    DOUBLE_NEWLINE = "double_newline"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    CUSTOM = "custom"


# ──────────────────────────────────────────────── 模型


@dataclass
class Paragraph:
    """自然段落"""
    index: int                         # 段落序号（章内自增）
    text: str                          # 段落正文
    char_count: int = 0                # 字符数
    is_dialogue: bool = False          # 是否纯对话段落
    is_scene_break: bool = False       # 是否场景分隔（如 ★★★）

    def __post_init__(self):
        if not self.char_count:
            self.char_count = len(self.text)
        self.is_dialogue = bool(
            self.text and (
                self.text.startswith("\u201c") or
                self.text.startswith("'") or
                self.text.startswith("\"") or
                self.text.startswith("\u300c")
            )
        )


@dataclass
class Section:
    """节（章内子段）"""
    index: int
    title: str = ""
    paragraphs: list[Paragraph] = field(default_factory=list)
    word_count: int = 0

    def __post_init__(self):
        if not self.word_count:
            self.word_count = sum(p.char_count for p in self.paragraphs)


@dataclass
class Chapter:
    """单章"""
    index: int
    title: str
    raw_text: str = ""                # 拆分前原始文本
    sections: list[Section] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)  # 当不分节时
    word_count: int = 0
    heading_pattern: str = ""         # 匹配到的章节标题模式（用于调试）

    def __post_init__(self):
        if not self.word_count:
            self.word_count = len(self.raw_text)
            if self.paragraphs:
                self.word_count = sum(p.char_count for p in self.paragraphs)
            elif self.sections:
                self.word_count = sum(s.word_count for s in self.sections)


@dataclass
class Volume:
    """卷/部"""
    index: int
    title: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    word_count: int = 0

    def __post_init__(self):
        if not self.word_count:
            self.word_count = sum(c.word_count for c in self.chapters)


@dataclass
class DissectResult:
    """全量拆解结果"""
    title: str = ""
    author: str = ""
    source_url: str = ""
    content_source: str = ""           # ContentSource 值
    volumes: list[Volume] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)  # 当不分卷时
    chapter_count: int = 0
    paragraph_count: int = 0
    total_word_count: int = 0
    split_strategies_used: list[str] = field(default_factory=list)  # 用到的策略名
    errors: list[str] = field(default_factory=list)        # 非致命警告
    stats: dict[str, Any] = field(default_factory=dict)    # 扩展统计

    def __post_init__(self):
        self._recalc()

    def _recalc(self):
        """重新计算汇总统计"""
        if self.volumes:
            self.chapters = [ch for v in self.volumes for ch in v.chapters]
        self.chapter_count = len(self.chapters)
        self.paragraph_count = sum(
            len(c.paragraphs) if c.paragraphs else len(c.sections)
            for c in self.chapters
        )
        self.total_word_count = sum(c.word_count for c in self.chapters)

    def json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """输出为 JSON 字符串，供下游后端消费"""
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=ensure_ascii,
        )

    def to_dict(self) -> dict[str, Any]:
        """递归转为普通字典"""
        d = asdict(self)
        if not d.get("volumes"):
            d.pop("volumes", None)
        if not d.get("chapters"):
            d.pop("chapters", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DissectResult":
        """从字典重建（可对接 Pydantic model_validate）"""
        def _paragraphs(items: list[dict]) -> list[Paragraph]:
            return [Paragraph(**p) for p in items]
        def _sections(items: list[dict]) -> list[Section]:
            return [Section(**s, paragraphs=_paragraphs(s.get("paragraphs", []))) for s in items]
        def _chapters(items: list[dict]) -> list[Chapter]:
            return [
                Chapter(
                    **{k: v for k, v in c.items() if k not in ("paragraphs", "sections")},
                    paragraphs=_paragraphs(c.get("paragraphs", [])),
                    sections=_sections(c.get("sections", [])),
                )
                for c in items
            ]
        data["chapters"] = _chapters(data.get("chapters", []))
        data["volumes"] = [
            Volume(**v, chapters=_chapters(v.get("chapters", [])))
            for v in data.get("volumes", [])
        ]
        return cls(**data)
