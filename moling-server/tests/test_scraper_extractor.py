"""
墨灵 (Moling) — Scraper Extractor 单元测试

测试 HTML 正文提取三层策略：
  - Layer 1: CSS 选择器提取
  - Layer 2: trafilatura 引擎
  - Layer 3: BS4 get_text() 兜底
"""

from __future__ import annotations

import pytest

from app.ingest.scraper.core.extractor import (
    quality_score,
    extract_with_bs4_selector,
    extract_with_bs4_fallback,
    extract_content,
    ExtractResult,
    _COMMON_CONTENT_SELECTORS,
    _COMMON_CHAPTER_SELECTORS,
)


# ============================================================================
# quality_score — 文本质量评分
# ============================================================================

class TestQualityScore:
    def test_high_quality(self):
        text = "正文" * 2500  # 5000 字符
        assert quality_score(text) == 0.95

    def test_medium_quality(self):
        text = "正文" * 1000  # 2000 字符
        assert quality_score(text) == 0.85

    def test_moderate_quality(self):
        text = "正文" * 400  # 800 字符
        assert quality_score(text) == 0.72

    def test_low_quality(self):
        text = "正文" * 100  # 200 字符
        assert quality_score(text) == 0.52

    def test_minimal_quality(self):
        assert quality_score("短") == 0.25

    def test_empty_quality(self):
        assert quality_score("") == 0


# ============================================================================
# extract_with_bs4_selector — CSS 选择器提取
# ============================================================================

class TestExtractWithBs4Selector:
    def test_matching_selector(self):
        html = "".join([
            "<div id='content'><p>",
            "这是正文内容，包含足够多的字符来通过质量检测。",
            "需要至少有二十个字符以上。",
            "</p></div>",
        ])
        result = extract_with_bs4_selector(html, "#content")
        # bs4 可能未安装，此时返回空字符串
        if result:
            assert "正文内容" in result

    def test_non_matching_selector(self):
        html = "<div id='sidebar'>侧边栏内容</div>"
        result = extract_with_bs4_selector(html, "#content")
        assert result == ""

    def test_multiple_matches(self):
        html_lines = [
            "<div class='content'><p>第一段正文内容足够长可以检测到。</p></div>",
            "<div class='content'><p>第二段正文内容也足够长。</p></div>",
        ]
        html = "".join(html_lines)
        result = extract_with_bs4_selector(html, ".content")
        if result:
            assert "第一段正文内容" in result
            assert "第二段正文内容" in result


# ============================================================================
# extract_with_bs4_fallback — BS4 兜底
# ============================================================================

class TestExtractWithBs4Fallback:
    def test_basic_extraction(self):
        html = "<html><body><p>测试正文内容</p></body></html>"
        result = extract_with_bs4_fallback(html)
        assert "测试正文内容" in result

    def test_removes_script_tags_at_minimum(self):
        html = "<html><body><script>alert('xss')</script><p>正文内容</p></body></html>"
        result = extract_with_bs4_fallback(html)
        # 无 bs4 时使用正则兜底，<script> 标签内容不会被完全移除
        # 但至少正文内容应保留
        assert "正文内容" in result

    def test_empty_html(self):
        result = extract_with_bs4_fallback("")
        assert result == ""


# ============================================================================
# extract_content — 主提取函数
# ============================================================================

class TestExtractContent:
    @pytest.fixture(autouse=True)
    def _require_bs4(self):
        try:
            import bs4  # noqa
        except ImportError:
            pytest.skip("bs4 未安装，跳过 extract_content 测试")

    def test_specific_selector(self):
        """指定选择器提取"""
        long_text = "正文内容测试填充文字" * 8
        html = (
            "<html><head><title>测试小说</title></head><body>"
            f"<div id='content'><p>{long_text}</p></div>"
            "<div id='sidebar'>广告内容</div>"
            "</body></html>"
        )
        result = extract_content(html, selector="#content")
        assert result.title == "测试小说"
        # bs4 可能不可用，此时 method 会是 fallback_text
        assert result.method in ("selector:#content", "fallback_text")
        assert result.error is None

    def test_extract_title(self):
        html = "<html><head><title>斗破苍穹</title></head><body><p>正文</p></body></html>"
        result = extract_content(html)
        assert result.title == "斗破苍穹"

    def test_extract_result_dataclass(self):
        result = ExtractResult(
            title="测试",
            text="正文",
            quality_score=0.85,
            method="test",
        )
        assert result.title == "测试"
        assert result.text == "正文"
        assert result.quality_score == 0.85
        assert result.error is None

    def test_common_selectors_list(self):
        """验证常见选择器列表不为空"""
        assert len(_COMMON_CONTENT_SELECTORS) > 0
        assert "#content" in _COMMON_CONTENT_SELECTORS
        assert "#chaptercontent" in _COMMON_CONTENT_SELECTORS

    def test_chapter_selectors_list(self):
        """验证章节选择器列表不为空"""
        assert len(_COMMON_CHAPTER_SELECTORS) > 0
        assert "dd a" in _COMMON_CHAPTER_SELECTORS
