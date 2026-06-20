"""
墨灵 (Moling) — Scraper Cleaner 单元测试

测试 HTML 清洗管线的 8 道工序：
  1. 移除 script/style/noscript 标签块
  2. 块级标签转换 + 移除剩余 HTML 标签
  3. HTML 实体解码
  4. Unicode 转义解码
  5. 换行符归一化
  6. 空白合并
  7. 广告/干扰行过滤
  8. 多余空行合并
"""

from __future__ import annotations

import pytest

from app.ingest.scraper.core.cleaner import (
    remove_blocks,
    strip_html_tags,
    decode_html_entities,
    decode_unicode_escapes,
    is_numeric_line,
    is_ad_line,
    is_chapter_heading,
    clean_html,
    clean_chapter_content,
    extract_title_from_html,
)


# ============================================================================
# remove_blocks — 移除标签块
# ============================================================================

class TestRemoveBlocks:
    def test_remove_script_block(self):
        html = "<div>正文</div><script>alert('广告')</script><p>继续</p>"
        result = remove_blocks(html, "script")
        assert "<script>" not in result
        assert "alert" not in result
        assert "正文" in result
        assert "继续" in result

    def test_remove_style_block(self):
        html = "<style>.ad{display:none}</style><p>正文</p>"
        result = remove_blocks(html, "style")
        assert "<style>" not in result
        assert ".ad" not in result
        assert "正文" in result

    def test_remove_noscript_block(self):
        html = "<noscript>请启用 JavaScript</noscript><p>正文</p>"
        result = remove_blocks(html, "noscript")
        assert "<noscript>" not in result
        assert "JavaScript" not in result
        assert "正文" in result

    def test_remove_multiple_same_tag(self):
        html = "<script>a</script>正文<script>b</script>"
        result = remove_blocks(html, "script")
        assert "<script>" not in result
        assert "a" not in result
        assert "b" not in result
        assert "正文" in result


# ============================================================================
# strip_html_tags — 块级标签换行 + 去标签
# ============================================================================

class TestStripHtmlTags:
    def test_br_to_newline(self):
        html = "第一行<br>第二行<br/>第三行"
        result = strip_html_tags(html)
        assert "\n" in result
        assert "第一行" in result
        assert "第二行" in result
        assert "第三行" in result

    def test_block_tags_to_newline(self):
        html = "<p>一段</p><p>二段</p>"
        result = strip_html_tags(html)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "一段" in result
        assert "二段" in result

    def test_div_to_newline(self):
        html = "<div>第一块</div><div>第二块</div>"
        result = strip_html_tags(html)
        assert "\n" in result
        assert "第一块" in result
        assert "第二块" in result

    def test_h_tags_to_newline(self):
        html = "<h1>标题一</h1><h2>标题二</h2>"
        result = strip_html_tags(html)
        assert "\n" in result
        assert "标题一" in result
        assert "标题二" in result

    def test_li_to_newline(self):
        html = "<ul><li>项目一</li><li>项目二</li></ul>"
        result = strip_html_tags(html)
        assert "\n" in result
        assert "项目一" in result
        assert "项目二" in result


# ============================================================================
# decode_html_entities — HTML 实体解码
# ============================================================================

class TestDecodeHtmlEntities:
    def test_nbsp_to_space(self):
        result = decode_html_entities("你好&nbsp;世界")
        assert " " in result
        assert "&nbsp;" not in result

    def test_amp_to_ampersand(self):
        result = decode_html_entities("A &amp; B")
        assert result == "A & B"

    def test_lt_gt(self):
        result = decode_html_entities("&lt;tag&gt;")
        assert result == "<tag>"

    def test_quot_apos(self):
        result = decode_html_entities("&quot;你好&quot;")
        assert result == '"你好"'
        result2 = decode_html_entities("&apos;你好&apos;")
        assert result2 == "'你好'"

    def test_numeric_entity(self):
        result = decode_html_entities("&#20013;&#25991;")
        assert result == "中文"

    def test_hex_numeric_entity(self):
        result = decode_html_entities("&#x4E2D;&#x6587;")
        assert result == "中文"


# ============================================================================
# decode_unicode_escapes — Unicode 转义解码
# ============================================================================

class TestDecodeUnicodeEscapes:
    def test_decode_chinese(self):
        result = decode_unicode_escapes("\\u4E2D\\u6587")
        assert result == "中文"

    def test_decode_mixed(self):
        result = decode_unicode_escapes("Hello \\u4E16\\u754C")
        assert result == "Hello 世界"

    def test_no_escape_passthrough(self):
        result = decode_unicode_escapes("普通文本")
        assert result == "普通文本"


# ============================================================================
# is_numeric_line — 纯数字行检测
# ============================================================================

class TestIsNumericLine:
    def test_pure_digits(self):
        assert is_numeric_line("123") is True

    def test_digits_with_spaces(self):
        assert is_numeric_line("  42  ") is True

    def test_not_pure_numeric(self):
        assert is_numeric_line("第123章") is False

    def test_empty_line(self):
        assert is_numeric_line("") is False
        assert is_numeric_line("   ") is False

    def test_number_with_punctuation(self):
        assert is_numeric_line("123.") is False


# ============================================================================
# is_ad_line — 广告行检测
# ============================================================================

class TestIsAdLine:
    def test_known_ad_pattern(self):
        assert is_ad_line("本章未完，请点击下一页继续阅读") is True

    def test_domain_ad(self):
        assert is_ad_line("请记住本书首发域名：example.com") is True

    def test_genius_ad(self):
        assert is_ad_line("天才一秒记住本站地址") is True

    def test_report_ad(self):
        assert is_ad_line("章节错误，点此举报") is True

    def test_not_ad(self):
        assert is_ad_line("主角缓缓睁开眼睛，发现自己躺在陌生的床上。") is False

    def test_case_insensitive_ad(self):
        assert is_ad_line("BookMark this page") is True


# ============================================================================
# is_chapter_heading — 章节标题检测
# ============================================================================

class TestIsChapterHeading:
    def test_chinese_numbered(self):
        assert is_chapter_heading("第一章 穿越") is True
        assert is_chapter_heading("第3章 觉醒") is True
        assert is_chapter_heading("第十一章 大战") is True
        assert is_chapter_heading("第一百二十三章") is True

    def test_section_heading(self):
        assert is_chapter_heading("第1节 初识") is True

    def test_special_heading(self):
        assert is_chapter_heading("序章") is True
        assert is_chapter_heading("楔子") is True
        assert is_chapter_heading("尾声") is True
        assert is_chapter_heading("番外") is True
        assert is_chapter_heading("引子") is True

    def test_numeric_heading(self):
        assert is_chapter_heading("001. 开局") is True
        assert is_chapter_heading("1、开局") is True

    def test_not_heading(self):
        assert is_chapter_heading("主角缓缓站起身") is False
        assert is_chapter_heading("他已经很久没有回来了") is False


# ============================================================================
# clean_html — 完整清洗管线
# ============================================================================

class TestCleanHtml:
    def test_basic_cleaning(self):
        html = """
        <html><head><title>测试</title></head>
        <body>
        <p>第一章 穿越</p>
        <p>主角睁开眼，发现自己来到了一个陌生的世界。</p>
        <script>console.log('ad')</script>
        <p>周围是一片茂密的森林，远处隐约可见一座巍峨的城池。</p>
        </body></html>
        """
        result = clean_html(html)
        assert "console.log" not in result
        assert "第一章 穿越" in result
        assert "主角睁开眼" in result
        assert "茂密的森林" in result

    def test_removes_ad_lines(self):
        text = "主角开始修炼。\n本章未完，请点击下一页继续阅读\n功法运转。"
        result = clean_html(text)
        assert "本章未完" not in result
        assert "主角开始修炼" in result
        assert "功法运转" in result

    def test_removes_short_lines(self):
        text = "主角\n修炼\n功法\n天下无敌\n战力惊天"
        result = clean_html(text)
        assert "天下无敌" in result
        assert "战力惊天" in result
        # 短行 <4 字符被过滤
        lines = result.split("\n")
        assert all(len(line) >= 4 for line in lines)

    def test_normalizes_newlines(self):
        html = "第一章内容\r\n第二章内容\r第三章内容\n第四章内容"
        result = clean_html(html)
        # 归一化后不应有 \r
        assert "\r" not in result
        assert "第一章内容" in result
        assert "第四章内容" in result

    def test_merges_consecutive_spaces(self):
        html = "主角    缓缓     睁开   眼睛"
        result = clean_html(html)
        assert "主角 缓缓 睁开 眼睛" in result
        assert "    " not in result

    def test_empty_input(self):
        result = clean_html("")
        assert result == ""

    def test_full_chapter_text(self):
        html = """
        <html><body>
        <h1>第三章 初入宗门</h1>
        <p>陈道临站在宏伟的山门前，心中感慨万千。</p>
        <p>三日前，他还只是一个普通的打工仔，如今却站在了修仙宗门的门前。</p>
        <p>守门弟子看了他一眼，道："你就是新来的外门弟子？"</p>
        <p>陈道临点了点头，递上了令牌。</p>
        <p>本章未完，请点击下一页继续阅读</p>
        </body></html>
        """
        result = clean_html(html)
        assert "第三章 初入宗门" in result
        assert "陈道临" in result
        assert "守门弟子" in result
        assert "本章未完" not in result


# ============================================================================
# clean_chapter_content — 去除章节标题
# ============================================================================

class TestCleanChapterContent:
    def test_remove_heading(self):
        text = "第三章 初入宗门\n陈道临站在山门前。\n守门弟子看了他一眼。"
        result = clean_chapter_content(text)
        assert "第三章 初入宗门" not in result
        assert "陈道临站在山门前" in result
        assert "守门弟子看了他一眼" in result

    def test_keep_body_only(self):
        text = "序章\n这是故事的开始。\n一切从这里展开。"
        result = clean_chapter_content(text)
        assert "序章" not in result
        assert "故事的开始" in result
        assert "从这里展开" in result


# ============================================================================
# extract_title_from_html — 提取标题
# ============================================================================

class TestExtractTitleFromHtml:
    def test_from_title_tag(self):
        html = "<html><head><title>斗破苍穹</title></head><body></body></html>"
        result = extract_title_from_html(html)
        assert result == "斗破苍穹"

    def test_no_title(self):
        html = "<html><body>无标题</body></html>"
        result = extract_title_from_html(html)
        assert result == ""

    def test_from_og_title(self):
        html = '<meta property="og:title" content="全职高手"/>'
        result = extract_title_from_html(html)
        assert result == "全职高手"
