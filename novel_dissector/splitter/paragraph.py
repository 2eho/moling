"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / splitter / paragraph.py
段落拆分器
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

提供两种粒度的段落拆分：
  - DoubleNewlineSplitter  — 双换行符分段（最常用）
  - ParagraphSplitter      — 自然段 + 语义段（智能合并）
"""

from __future__ import annotations

import re
from typing import Optional

from novel_dissector.splitter.base import BaseSplitter
from novel_dissector.models.schemas import (
    Chapter,
    Paragraph,
    SplitGranularity,
)


# =========================================================================
# 双换行符分段
# =========================================================================

class DoubleNewlineSplitter(BaseSplitter):
    """
    最简单的按双换行符分段策略。
    不对已有的 Chapter 做二次拆分，只是重新分配段的边界。
    """

    name: str = "double_newline"
    granularity: SplitGranularity = SplitGranularity.PARAGRAPH

    def split(self, text: str, **kwargs) -> list[Chapter]:
        """直接把文本按双换行切分，每段作为一章（极少用）。"""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        chapters = []
        for i, para in enumerate(paragraphs):
            stripped = para.strip()
            if not stripped:
                continue
            par = Paragraph(index=i, text=stripped)
            chapters.append(
                Chapter(
                    index=i + 1,
                    title=f"段落{i+1}",
                    raw_text=stripped,
                    paragraphs=[par],
                )
            )
        return chapters


# =========================================================================
# 自然段拆分器
# =========================================================================

class ParagraphSplitter(BaseSplitter):
    """
    对已有章节内的文本进行段落拆分。
    用于 Pipeline 中作为第二道工序（已有 chapter 对象时）。

    拆分逻辑
      1. 按换行符分割得到候选段落
      2. 合并连续短行（对话/续行，<15 字符 + 不以句号结尾）
      3. 空行跳过
      4. 合并过短段落到前一段
    """

    name: str = "paragraph"
    granularity: SplitGranularity = SplitGranularity.PARAGRAPH

    def __init__(
        self,
        min_para_chars: int = 10,
        merge_short_lines: bool = True,
        short_line_threshold: int = 15,
    ):
        super().__init__()
        self.min_para_chars = min_para_chars
        self.merge_short_lines = merge_short_lines
        self.short_line_threshold = short_line_threshold

    def split(self, text: str, **kwargs) -> list[Chapter]:
        """
        将文本拆分为带段落信息的单章列表。
        若输入是单段文本，返回单章的段落列表。
        """
        # 先按章节标题分段
        from novel_dissector.splitter.chapter import ChapterRegexSplitter
        chapter_splitter = ChapterRegexSplitter(
            min_chapter_chars=1,
        )
        chapters = chapter_splitter.split(text)
        return [self._split_paragraphs(ch) for ch in chapters]

    def split_chapter(self, chapter: Chapter) -> Chapter:
        """对单个 Chapter 对象进行段落拆分。"""
        return self._split_paragraphs(chapter)

    def _split_paragraphs(self, chapter: Chapter) -> Chapter:
        lines = chapter.raw_text.split("\n") if chapter.raw_text else []
        raw_paras: list[str] = []
        buffer = ""

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if buffer:
                    raw_paras.append(buffer)
                    buffer = ""
                continue

            # 场景分隔标记（*** / ★★★ / ———）
            if re.match(r'^[\*★\-\~＝]{3,}$', stripped):
                if buffer:
                    raw_paras.append(buffer)
                raw_paras.append(stripped)
                buffer = ""
                continue

            if self.merge_short_lines and len(stripped) < self.short_line_threshold:
                # 短行 → 合并到 buffer
                if buffer and not buffer.endswith(("。", "！", "？", "”", "》", "」", ")")):
                    buffer += stripped
                else:
                    if buffer:
                        raw_paras.append(buffer)
                    buffer = stripped
            else:
                if buffer:
                    raw_paras.append(buffer)
                buffer = stripped

        if buffer:
            raw_paras.append(buffer)

        # 构建 Paragraph 对象
        paras: list[Paragraph] = []
        pi = 0
        for raw in raw_paras:
            raw = raw.strip()
            if len(raw) < self.min_para_chars:
                # 合并到前一段
                if paras:
                    paras[-1] = Paragraph(
                        index=paras[-1].index,
                        text=paras[-1].text + "\n" + raw,
                        char_count=paras[-1].char_count + len(raw),
                    )
                continue
            pi += 1
            paras.append(Paragraph(index=pi, text=raw))

        chapter.paragraphs = paras
        chapter.word_count = sum(p.char_count for p in paras)
        return chapter
