"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / core / extractor.py
正文内容提取模块
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

从 HTML 中智能提取正文的两层策略（对标 Go 版 adapter_default.go
的 fetchChapterContent + extractor_client.py + Python extractor/app.py）：

  Layer 1 — CSS 选择器提取（精确位点）
  Layer 2 — trafilatura 引擎（通用正文提取）
  Layer 3 — BeautifulSoup get_text() 兜底

零运行时依赖：trafilatura 和 bs4 均为可选安装，缺失时自动跳过。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from novel_dissector.core.cleaner import clean_html


# ──────────────────────────────────────────────────────── Common Selectors

# 20+ 种常见中文小说网站正文容器（来自写作猫源站种子数据的积累）
_COMMON_CONTENT_SELECTORS: list[str] = [
    "#content",
    "#chaptercontent",
    "#booktxt",
    "#BookText",
    "#readcontent",
    ".content",
    ".chapter-content",
    ".chapter_content",
    ".read-content",
    ".txtnav",
    ".showtxt",
    "#content_1",
    "#content_2",
    ".content_detail",
    "#chapterContent",
    "#chapter_content",
    ".chapter-content-box",
    ".content_main",
    "#TextContent",
    "#articlecontent",
    ".article-content",
    ".novel-content",
    "#novelcontent",
    ".body_text",
]

# 9 种常见章节链接容器
_COMMON_CHAPTER_SELECTORS: list[str] = [
    "dd a",
    ".listmain a",
    "#list a",
    ".chapterlist a",
    ".border_chapter a",
    ".booklist a",
    ".mulu a",
    ".directory a",
    ".chapter a",
]


# ──────────────────────────────────────────────────────── Result Model


@dataclass
class ExtractResult:
    title: str = ""
    text: str = ""
    quality_score: float = 0.0
    method: str = ""
    error: Optional[str] = None


def quality_score(text: str) -> float:
    """基于文本长度的质量评分（对标 Python extractor/app.py quality_score）。"""
    size = len(text or "")
    if size >= 5000:
        return 0.95
    if size >= 2000:
        return 0.85
    if size >= 800:
        return 0.72
    if size >= 200:
        return 0.52
    return 0.25 if size else 0


# ──────────────────────────────────────────────────────── Extractors


def extract_with_bs4_selector(html: str, selector: str) -> str:
    """使用 BeautifulSoup 的 CSS 选择器提取。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        selected = "\n".join(
            node.get_text("\n").strip()
            for node in soup.select(selector)
        )
        return selected
    except Exception:
        return ""


def extract_with_trafilatura(html: str, url: Optional[str] = None) -> str:
    """使用 trafilatura 引擎提取正文。"""
    try:
        import trafilatura
    except ImportError:
        return ""
    try:
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        return (extracted or "").strip()
    except Exception:
        return ""


def extract_with_bs4_fallback(html: str) -> str:
    """BeautifulSoup get_text() 兜底（无选择器）。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # 无 bs4：使用极简正则提取
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    try:
        soup = BeautifulSoup(html, "html.parser")
        # 移除 script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text("\n").strip()
    except Exception:
        return ""


# ──────────────────────────────────────────────────────── 主函数


def extract_content(
    html: str,
    selector: Optional[str] = None,
    url: Optional[str] = None,
    try_trafilatura: bool = True,
    try_common_selectors: bool = True,
) -> ExtractResult:
    """
    从 HTML 中提取正文，按优先级尝试：
      1. 指定 CSS 选择器（精度最高）
      2. 遍历 20+ 种常见中文小说站内容容器
      3. trafilatura 引擎（通用性最好）
      4. BS4 get_text() 兜底
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title and soup.title.string else "").strip()
    title = re.sub(r'\s+', '', title)  # 紧凑化

    # Layer 1: 指定选择器
    if selector:
        text = extract_with_bs4_selector(html, selector)
        if len(text.strip()) >= 20:
            return ExtractResult(
                title=title,
                text=text.strip(),
                quality_score=quality_score(text),
                method=f"selector:{selector}",
            )

    # Layer 2: 常见容器遍历
    if try_common_selectors:
        for sel in _COMMON_CONTENT_SELECTORS:
            text = extract_with_bs4_selector(html, sel)
            if len(text.strip()) >= 80:
                return ExtractResult(
                    title=title,
                    text=text.strip(),
                    quality_score=quality_score(text),
                    method=f"common_selector:{sel}",
                )

    # Layer 3: trafilatura
    if try_trafilatura:
        text = extract_with_trafilatura(html, url)
        if len(text) >= 80:
            return ExtractResult(
                title=title,
                text=text,
                quality_score=quality_score(text),
                method="trafilatura",
            )

    # Layer 4: bs4 兜底
    text = extract_with_bs4_fallback(html)
    score = quality_score(text)
    result = ExtractResult(
        title=title, text=text, quality_score=score, method="fallback_text",
    )
    if not text or len(text) < 80:
        result.error = "正文过短"
    return result


__all__ = [
    "extract_content",
    "ExtractResult",
    "quality_score",
    "_COMMON_CONTENT_SELECTORS",
    "_COMMON_CHAPTER_SELECTORS",
]
