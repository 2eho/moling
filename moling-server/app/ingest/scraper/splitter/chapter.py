"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
app.ingest.scraper / splitter / chapter.py
章节拆分器
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

一种策略：
  1. ChapterRegexSplitter  — 标准正则拆分（快、准、零依赖）

借鉴来源
  - 写作猫 adapter_default.go 的 extractChapterURLs 正则模式
  - 墨灵后端设计文档 v1.0 第十章 10.3.1 完整正则模式
  - Anning01/novel-split 的章节识别算法
  - 知乎专栏《小说章节分割从入门到精通》
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Optional

from app.ingest.scraper.splitter.base import BaseSplitter
from app.ingest.scraper.models.schemas import Chapter, SplitGranularity


# =========================================================================
# 中文小说章节标题正则模式
# =========================================================================

# -------- 核心模式（按优先级排列） --------

# 1. 标准中文编号：第X章 / 第X回 / 第X卷
CHAPTER_CN_PATTERN = re.compile(
    r'^第[零一二三四五六七八九十百千万\d]+[章回卷节部]',
)

# 2. 卷号 + 章号组合：卷一 第一章 / 第一部 第3章
CHAPTER_VOLUME_COMBO = re.compile(
    r'^第[零一二三四五六七八九十百千万0-9零○〇]+[卷部集]\s*第\d+[章回]',
)

# 3. 中文数字+章：三章 / 五章（无"第"字头）
CHAPTER_CN_SHORT_PATTERN = re.compile(
    r'^[零一二三四五六七八九十百千万]+章',
)

# 4. 非中文编号：Chapter X / ChapterX / CH X
CHAPTER_EN_PATTERN = re.compile(
    r'^(?:Chapter|Ch|CH|ch|chap|SECTION|Sec)\s*[\.:：]?\s*(\d+)',
    re.IGNORECASE,
)

# 5. 纯数字编号：001 / 1. / 1、
CHAPTER_NUM_PATTERN = re.compile(
    r'^(\d{1,4})\s*[\.、．:：\s]?\s*',
)

# 6. 特殊章节标记：序章 / 楔子 / 引子 / 尾声 / 番外 / 后记 / 前言
CHAPTER_SPECIAL_PATTERN = re.compile(
    r'^\s*(序章|楔子|引子|尾声|番外(篇)?|后记|前言|题记|代序|代跋|外传|第零章)',
)

# 7. 分隔符模式：*** / ★★★ / ——— / === / ~~~ / •••
CHAPTER_SEPARATOR_PATTERN = re.compile(
    r'^[*\•\-\_\=\~\#★]{3,}$',
)

# 8. 括号数字：(1) / ［1］ / 【1】
CHAPTER_BRACKET_NUM_PATTERN = re.compile(
    r'^[\(\[（［【]\d+[\)\]）］】]',
)

# -------- 章节过滤模式 --------

# 当一行看起来合理但实际不是章节标题时跳过
CHAPTER_SKIP_PATTERNS = [
    re.compile(r'^http[s]?://'),           # URL
    re.compile(r'^[A-Za-z0-9_.-]+@'),     # 邮箱
    re.compile(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}'),  # 日期
]

# -------- 卷级拆分 --------
VOLUME_CN_PATTERN = re.compile(
    r'^第[零一二三四五六七八九十百千万\d]+[卷部]',
)


# =========================================================================
# ChapterRegexSplitter
# =========================================================================

class ChapterRegexSplitter(BaseSplitter):
    """
    基于正则表达式的章节拆分器（纯标准库，零依赖）。

    使用说明
      splitter = ChapterRegexSplitter(
          min_chapter_chars=100,    # 单章最少字符数（过滤空章节/检测点）
          max_chapter_chars=50000,  # 单章最大字符数（大章节强制分割）
          detect_volume=True,       # 是否检测卷/部
      )
      chapters = splitter.split(cleaned_text)

    策略
      1. 按优先级依次尝试 8 种章节标题匹配模式（合并自后端设计文档 v1.0 完整正则模式）
      2. 匹配到的位置作为章节分隔点
      3. 两个分隔点之间的文本作为一章
      4. 未匹配到任何章节标记 → 全书当作单章返回
      5. 卷级拆分在章节拆分之前
    """

    name: str = "chapter_regex"
    granularity: SplitGranularity = SplitGranularity.CHAPTER

    def __init__(
        self,
        min_chapter_chars: int = 100,
        max_chapter_chars: int = 50000,
        detect_volume: bool = True,
    ):
        super().__init__()
        self.min_chapter_chars = min_chapter_chars
        self.max_chapter_chars = max_chapter_chars
        self.detect_volume = detect_volume

    def split(self, text: str, **kwargs) -> list[Chapter]:
        if not text or not text.strip():
            return []

        min_chars = kwargs.get("min_chapter_chars", self.min_chapter_chars)
        max_chars = kwargs.get("max_chapter_chars", self.max_chapter_chars)
        detect_vol = kwargs.get("detect_volume", self.detect_volume)

        lines = text.split("\n")

        # ---- Step 1: 识别分割点 ----
        split_indices: list[int] = []  # 行号列表
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_chapter_heading(stripped):
                split_indices.append(i)

        # 没有章节分割 → 全书视为一章
        if not split_indices:
            return [self._make_chapter(1, "", text)]

        # ---- Step 2: 按分割点组块 ----
        chapters: list[Chapter] = []
        for seg_idx, start_line in enumerate(split_indices):
            end_line = split_indices[seg_idx + 1] if seg_idx + 1 < len(split_indices) else len(lines)
            heading = lines[start_line].strip()
            content_lines = lines[start_line:end_line]

            raw = "\n".join(line.strip() for line in content_lines if line.strip())

            # 过滤短章节（可能是检测点/空壳）
            if len(raw) < min_chars and seg_idx < len(split_indices) - 1:
                continue

            # 超长章节截断处理（罕见但存在）
            if len(raw) > max_chars and seg_idx < len(split_indices) - 1:
                # 在内部继续按第4级模式拆分
                sub_chapters = self._split_oversize(raw, heading, max_chars)
                chapters.extend(sub_chapters)
            else:
                chapters.append(
                    self._make_chapter(
                        index=seg_idx + 1,
                        title=heading,
                        raw_text=raw,
                        heading_pattern=self._pattern_name(heading),
                    )
                )

        if not chapters:
            chapters.append(self._make_chapter(1, "", text))

        return chapters

    # ── 内部辅助 ──────────────────────────────────────

    @staticmethod
    def _is_chapter_heading(line: str) -> bool:
        """检测是否章节标题行。"""
        for skip in CHAPTER_SKIP_PATTERNS:
            if skip.match(line):
                return False
        if CHAPTER_CN_PATTERN.match(line):
            return True
        if CHAPTER_VOLUME_COMBO.match(line):
            return True
        if CHAPTER_SPECIAL_PATTERN.match(line):
            return True
        if CHAPTER_EN_PATTERN.match(line):
            return True
        if CHAPTER_CN_SHORT_PATTERN.match(line):
            return True
        if CHAPTER_SEPARATOR_PATTERN.match(line):
            return True
        if CHAPTER_BRACKET_NUM_PATTERN.match(line):
            return True
        if CHAPTER_NUM_PATTERN.match(line):
            # 纯数字篇章：检查是否超过 4 位（过长的数字不是章节编号）
            m = CHAPTER_NUM_PATTERN.match(line)
            num_str = m.group(1)
            if len(num_str) <= 4:
                return True
        return False

    @staticmethod
    def _pattern_name(line: str) -> str:
        if CHAPTER_CN_PATTERN.match(line):
            return "cn_numbered"
        if CHAPTER_VOLUME_COMBO.match(line):
            return "volume_combo"
        if CHAPTER_SPECIAL_PATTERN.match(line):
            return "special"
        if CHAPTER_EN_PATTERN.match(line):
            return "en_numbered"
        if CHAPTER_CN_SHORT_PATTERN.match(line):
            return "cn_short"
        if CHAPTER_SEPARATOR_PATTERN.match(line):
            return "separator"
        if CHAPTER_BRACKET_NUM_PATTERN.match(line):
            return "bracket_num"
        if CHAPTER_NUM_PATTERN.match(line):
            return "numeric"
        return "unknown"

    @staticmethod
    def _split_oversize(text: str, heading: str, max_chars: int) -> list[Chapter]:
        """超长章节按空行再分。"""
        parts = re.split(r'\n\s*\n', text, maxsplit=3)
        chapters = []
        for pi, part in enumerate(parts):
            if part.strip():
                suffix = f"（续{pi}）" if pi > 0 else ""
                chapters.append(
                    Chapter(
                        index=pi + 1,
                        title=f"{heading}{suffix}",
                        raw_text=part.strip(),
                        heading_pattern="oversize_continuation",
                    )
                )
        return chapters
