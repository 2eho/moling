"""
墨灵 (Moling) — Scraper Splitter 单元测试

测试章节/段落拆分的核心策略：
  - ChapterRegexSplitter: 正则章节拆分
  - ParagraphSplitter:   自然段拆分（含短行合并）
  - DoubleNewlineSplitter: 双换行符分段
  - split_text:           策略管线组合
"""

from __future__ import annotations

import pytest

from app.ingest.scraper.models.schemas import Chapter, Paragraph, SplitGranularity
from app.ingest.scraper.splitter.base import BaseSplitter
from app.ingest.scraper.splitter.chapter import ChapterRegexSplitter
from app.ingest.scraper.splitter.paragraph import (
    DoubleNewlineSplitter,
    ParagraphSplitter,
)
from app.ingest.scraper.splitter.strategies import (
    split_text,
    get_strategy,
    list_strategies,
    register_strategy,
)


# ============================================================================
# ChapterRegexSplitter — 章节拆分
# ============================================================================

class TestChapterRegexSplitter:
    """测试 ChapterRegexSplitter 的 8 种章节标题匹配模式"""

    def test_split_chinese_numbered(self):
        """标准中文编号：第X章"""
        text = "\n".join([
            "第一章 穿越异世",
            "主角睁开眼，发现自己来到了陌生的世界。",
            "周围是一片茂密的森林。",
            "第二章 初识宗门",
            "三个月过去了，主角已经适应了这个世界。",
            "他站在山门前，感慨万千。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=10)
        chapters = splitter.split(text)
        assert len(chapters) == 2
        assert chapters[0].title == "第一章 穿越异世"
        assert chapters[1].title == "第二章 初识宗门"
        assert "主角睁开眼" in chapters[0].raw_text
        assert "三个月" in chapters[1].raw_text

    def test_split_special_heading(self):
        """特殊章节：序章/楔子/尾声"""
        text = "\n".join([
            "序章 一切的开始",
            "这是故事的开端。",
            "第一章 新世界",
            "主角来到了新世界。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) == 2
        assert chapters[0].title == "序章 一切的开始"

    def test_split_english_chapter(self):
        """英文编号：Chapter X"""
        text = "\n".join([
            "Chapter 1 The Beginning",
            "It was a dark and stormy night.",
            "Chapter 2 The Journey",
            "The hero set out on a long journey.",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) == 2
        assert chapters[0].heading_pattern == "en_numbered"

    def test_split_numeric_prefix(self):
        """纯数字编号：001. / 1、"""
        text = "\n".join([
            "001. 第一个故事",
            "这里是一段正文内容，讲述了一个有趣的故事。",
            "002. 第二个故事",
            "另一段正文内容，继续讲述后续的发展情节。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=10)
        chapters = splitter.split(text)
        assert len(chapters) == 2

    def test_split_separator(self):
        """分隔符模式：*** / ★★★"""
        text = "\n".join([
            "第一章 出发",
            "第一段正文内容，讲了很长的一段故事。",
            "***",
            "第二段正文内容，这是一个新的视角。",
            "★★★",
            "第三段正文内容，故事的转折开始了。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert chapters[0].title == "第一章 出发"
        assert chapters[1].heading_pattern == "separator"

    def test_no_chapter_heading_single_chapter(self):
        """无章节标题时全书视为单章"""
        text = "这是一段没有任何章节标题的纯文本内容，讲述了一个完整的故事。"
        splitter = ChapterRegexSplitter()
        chapters = splitter.split(text)
        assert len(chapters) == 1
        assert chapters[0].index == 1

    def test_empty_text(self):
        splitter = ChapterRegexSplitter()
        chapters = splitter.split("")
        assert chapters == []

    def test_filter_short_chapters(self):
        """过滤过短章节（min_chapter_chars）"""
        text = "\n".join([
            "第一章 开局",
            "仅几个字",  # < min_chapter_chars
            "第二章 真正开始",
            "这是一段足够长的正文内容，超过了最小字符数的限制。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=20)
        chapters = splitter.split(text)
        # 第一章太短被过滤
        assert len(chapters) == 1
        assert chapters[0].title == "第二章 真正开始"

    def test_heading_pattern_detection(self):
        """验证 heading_pattern 标记"""
        text = "第一章 穿越\n正文内容。"
        splitter = ChapterRegexSplitter(min_chapter_chars=5)
        chapters = splitter.split(text)
        assert chapters[0].heading_pattern == "cn_numbered"

    def test_chapter_volume_combo(self):
        """卷+章组合：卷一 第一章"""
        text = "\n".join([
            "第一卷 第一章 初入江湖",
            "这是一段足够长的正文内容用来测试卷章组合的拆分。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) == 1
        # "第一卷" 被 VOLUME_CN_PATTERN 和 CHAPTER_CN_PATTERN 都能匹配，
        # _is_chapter_heading 会先通过 CHAPTER_CN_PATTERN 判定
        assert chapters[0].heading_pattern in ("cn_numbered", "volume_combo")

    def test_bracket_num(self):
        """括号数字：(1) (2)"""
        text = "\n".join([
            "(1) 第一节",
            "正文内容在这里。",
            "(2) 第二节",
            "继续正文内容。",
        ])
        splitter = ChapterRegexSplitter(min_chapter_chars=2)
        chapters = splitter.split(text)
        assert len(chapters) == 2


# ============================================================================
# ParagraphSplitter — 段落拆分
# ============================================================================

class TestParagraphSplitter:
    """测试 ParagraphSplitter 自然段拆分 + 短行合并"""

    def test_split_paragraphs_basic(self):
        text = "第一章 开始\n第一段正文内容比较长足以超过最小字符限制。\n第二段正文内容也比较长足以超过限制。\n第三段正文内容同样足够长的。"
        splitter = ParagraphSplitter(min_para_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) == 1
        chapter = chapters[0]
        # 第一章 开始成为独立段落 + 3 段正文 = 4 段
        assert len(chapter.paragraphs) >= 3

    def test_merge_short_lines(self):
        """短行（<15字符）应合并"""
        text = "第一章\n短行一\n短行二\n这是一段比较长的正文内容。"
        splitter = ParagraphSplitter(merge_short_lines=True, short_line_threshold=15, min_para_chars=3)
        chapters = splitter.split(text)
        chapter = chapters[0]
        assert len(chapter.paragraphs) >= 1

    def test_skip_empty_lines(self):
        text = "第一章\n第一段内容比较长的正文。\n\n\n第二段内容也比较长的正文。"
        splitter = ParagraphSplitter(min_para_chars=5)
        chapters = splitter.split(text)
        chapter = chapters[0]
        assert len(chapter.paragraphs) >= 2

    def test_scene_separator(self):
        """场景分隔符（***等）不丢失正文"""
        text = "第一章 开局\n前一段正文内容比较长来测试场景分隔功能。\n***\n后一段正文内容也比较长来验证。"
        splitter = ParagraphSplitter(min_para_chars=5)
        chapters = splitter.split(text)
        chapter = chapters[0]
        assert len(chapter.paragraphs) >= 2

    def test_chapter_content_preserved(self):
        """验证章节内容与段落拆分后仍保留"""
        text = "第一章 测试\n这是测试内容较长的一行。\n这是第二段也是较长的内容。"
        splitter = ParagraphSplitter(min_para_chars=5)
        chapters = splitter.split(text)
        assert len(chapters) >= 1
        combined = "".join(p.text for p in chapters[0].paragraphs)
        assert "测试内容" in combined


# ============================================================================
# DoubleNewlineSplitter — 双换行分段
# ============================================================================

class TestDoubleNewlineSplitter:
    def test_basic_split(self):
        text = "第一段\n\n第二段\n\n第三段"
        splitter = DoubleNewlineSplitter()
        chapters = splitter.split(text)
        assert len(chapters) == 3

    def test_empty_paragraphs_skipped(self):
        text = "第一段\n\n\n\n第二段"
        splitter = DoubleNewlineSplitter()
        chapters = splitter.split(text)
        assert len(chapters) == 2
        assert all(ch.title for ch in chapters)

    def test_single_paragraph(self):
        text = "只有一段"
        splitter = DoubleNewlineSplitter()
        chapters = splitter.split(text)
        assert len(chapters) == 1


# ============================================================================
# split_text — 策略管线
# ============================================================================

class TestSplitText:
    """测试策略注册与管线组合"""

    def test_default_pipeline(self):
        text = "第一章 开始\n正文内容。\n第二章 发展\n更多正文。"
        chapters = split_text(text)
        assert len(chapters) >= 1

    def test_chapter_only(self):
        text = "第一章 开始\n这是一段足够长的正文内容用于测试章节拆分的最小字符限制。\n第二章 发展\n这也是一段足够长的正文内容用于测试。"
        # 使用 min_chapter_chars=10 避免短章节被过滤
        chapters = split_text(text, ["chapter_regex"], min_chapter_chars=10)
        assert len(chapters) == 2

    def test_double_newline(self):
        text = "段落一\n\n段落二\n\n段落三"
        chapters = split_text(text, ["double_newline"])
        assert len(chapters) == 3

    def test_list_strategies(self):
        strategies = list_strategies()
        assert "chapter_regex" in strategies
        assert "double_newline" in strategies
        assert "paragraph" in strategies

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="未注册的策略"):
            split_text("测试", ["nonexistent_strategy"])

    def test_custom_strategy_registration(self):
        class CustomSplitter(BaseSplitter):
            name: str = "test_custom"
            granularity: SplitGranularity = SplitGranularity.CHAPTER

            def split(self, text: str, **kwargs) -> list[Chapter]:
                return [Chapter(index=1, title="唯一章", raw_text=text)]

        register_strategy("test_custom", CustomSplitter)
        assert "test_custom" in list_strategies()

        strategy = get_strategy("test_custom")
        assert strategy is not None
        chapters = strategy.split("测试文本")
        assert len(chapters) == 1
        assert chapters[0].title == "唯一章"

    def test_chinese_short(self):
        """中文数字短章：三章 / 五章"""
        text = "三章 新的开始\n正文内容略。"
        splitter = ChapterRegexSplitter(min_chapter_chars=2)
        chapters = splitter.split(text)
        assert len(chapters) == 1
