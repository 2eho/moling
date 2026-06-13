"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
app.ingest.scraper / core / toc_crawler.py
目录页遍历器
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

从网文目录页提取所有章节链接，逐章采集并合并为一个
DissectResult。支持进度追踪和断点恢复。

设计
  TOCFetcher            — 目录解析 + 链接提取
  ChapterBatchCrawler   — 逐章采集 + 进度管理

依赖
  - requests + beautifulsoup4（可选，缺失时降级）
  - app.ingest.scraper.core.fetcher — 复用反爬策略

参考
  - 写作猫 adapter_default.go 的 extractChapterURLs
  - 墨灵后端设计文档 v1.0 十 章 10.2 Phase 0
"""

from __future__ import annotations

import json
import os
import re
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urljoin, urlparse


logger = logging.getLogger(__name__)

from app.ingest.scraper.core.fetcher import Fetcher, AntiCrawlConfig, FetchResult
from app.ingest.scraper.models.schemas import DissectResult

# ---------------------------------------------------------------------------
# 常见章节链接选择器（来自 extractor.py，追加更多模式）
# ---------------------------------------------------------------------------

_COMMON_TOC_SELECTORS: list[str] = [
    "dd a",
    ".listmain a",
    "#list a",
    ".chapterlist a",
    ".border_chapter a",
    ".booklist a",
    ".mulu a",
    ".directory a",
    ".chapter a",
    ".catalog a",
    "#chapters a",
    ".chapters a",
    ".chapter-list a",
    "ul.chapter li a",
    ".volume-list a",
    "#readlist a",
    ".book-content a",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ChapterLink:
    """单章链接"""
    index: int
    title: str
    url: str
    fetched: bool = False
    error: Optional[str] = None


@dataclass
class CrawlProgress:
    """采集进度（支持断点恢复）"""
    novel_title: str = ""
    source_toc_url: str = ""
    total_chapters: int = 0
    fetched_count: int = 0
    error_count: int = 0
    chapters: list[dict] = field(default_factory=list)  # ChapterLink dicts
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "idle"  # idle | running | paused | done | failed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlProgress":
        return cls(**data)


# ---------------------------------------------------------------------------
# TOCFetcher — 目录页解析
# ---------------------------------------------------------------------------


class TOCFetcher:
    """
    解析目录页 HTML，提取章节链接列表。

    用法
        fetcher = TOCFetcher()
        links = fetcher.fetch_toc("https://example.com/novel/1/")
        for link in links:
            print(link.title, link.url)
    """

    def __init__(self, anti_crawl: Optional[AntiCrawlConfig] = None):
        self.http = Fetcher(anti_crawl or AntiCrawlConfig(
            delay_min_ms=500,
            delay_jitter_ms=1500,
        ))

    def fetch_toc(
        self,
        url: str,
        selectors: Optional[list[str]] = None,
        title_limit: int = 60,
    ) -> list[ChapterLink]:
        """
        从目录页提取章节链接。

        参数
            url         — 目录页 URL
            selectors   — CSS 选择器列表（默认 _COMMON_TOC_SELECTORS）
            title_limit — 标题最大长度（超长截断）

        返回
            有序的 ChapterLink 列表（按目录页出现顺序）
        """
        result = self.http.get(url)
        if self.http.is_hard_failure(result):
            raise RuntimeError(f"目录页请求失败: {result.error or result.status_code}")

        html = result.text
        if not html:
            raise RuntimeError("目录页 HTML 为空")

        selectors = selectors or _COMMON_TOC_SELECTORS
        links = self._extract_links(html, url, selectors, title_limit)

        if not links:
            raise RuntimeError(
                f"无法从 {url} 提取章节链接，未匹配任何选择器。"
                f"尝试的选择器: {selectors[:5]}..."
            )

        return links

    def _extract_links(
        self,
        html: str,
        base_url: str,
        selectors: list[str],
        title_limit: int,
    ) -> list[ChapterLink]:
        """使用 BeautifulSoup 提取链接。"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("toc_crawler 需要 beautifulsoup4: pip install beautifulsoup4")

        soup = BeautifulSoup(html, "html.parser")

        # 尝试每个选择器，取匹配数量最多的
        best_links: list[tuple[str, str]] = []
        best_count = 0

        for selector in selectors:
            anchors = soup.select(selector)
            if not anchors:
                continue

            candidates: list[tuple[str, str]] = []
            for a in anchors:
                href = a.get("href", "").strip()
                title = a.get_text(strip=True)
                if not href or not title:
                    continue
                # 过滤掉非章节链接（太短/包含特殊字符）
                if len(title) < 2 or len(title) > title_limit:
                    continue
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                candidates.append((title, href))

            if len(candidates) > best_count:
                best_count = len(candidates)
                best_links = candidates

        # 去重（保留首次出现）
        seen_urls: set[str] = set()
        unique_links: list[tuple[str, str]] = []
        for title, href in best_links:
            if href not in seen_urls:
                seen_urls.add(href)
                unique_links.append((title, href))

        return [
            ChapterLink(index=i + 1, title=title, url=href)
            for i, (title, href) in enumerate(unique_links)
        ]


# ---------------------------------------------------------------------------
# ChapterBatchCrawler — 批量采集
# ---------------------------------------------------------------------------


class ChapterBatchCrawler:
    """
    批量采集小说章节。

    用法
        crawler = ChapterBatchCrawler()
        result = crawler.crawl("https://example.com/novel/1/")
        print(f"采集了 {result.chapter_count} 章")

    支持进度管理：
        crawler = ChapterBatchCrawler()
        crawler.load_progress("progress.json")   # 恢复断点
        result = crawler.crawl(toc_url)
        crawler.save_progress("progress.json")   # 保存进度
    """

    def __init__(
        self,
        anti_crawl: Optional[AntiCrawlConfig] = None,
        max_consecutive_errors: int = 5,
        max_chapters: Optional[int] = None,
    ):
        self.http = Fetcher(anti_crawl or AntiCrawlConfig())
        self.toc = TOCFetcher(anti_crawl)
        self.max_consecutive_errors = max_consecutive_errors
        self.max_chapters = max_chapters
        self.progress = CrawlProgress()

    # ── 进度管理 ─────────────────────────────────────

    def save_progress(self, path: str) -> None:
        """将当前进度写入 JSON 文件（断点恢复用）。"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.progress.to_dict(), f, ensure_ascii=False, indent=2)

    def load_progress(self, path: str) -> bool:
        """从 JSON 文件恢复进度。"""
        if not os.path.isfile(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.progress = CrawlProgress.from_dict(data)
        return True

    # ── 主入口 ────────────────────────────────────────

    def crawl(
        self,
        toc_url: str,
        split_strategies: Optional[list[str]] = None,
        start_from: int = 0,
        callback=None,
    ) -> DissectResult:
        """
        执行完整采集流程。

        参数
            toc_url          — 目录页 URL
            split_strategies — 拆分策略（默认 chapter_regex + paragraph）
            start_from       — 起始章节索引（跳过已采集的）
            callback         — 进度回调 callback(fetched, total, chapter_title)

        返回
            合并后的 DissectResult
        """
        from datetime import datetime, timezone

        if split_strategies is None:
            split_strategies = ["chapter_regex", "paragraph"]

        # 1. 解析目录
        if not self.progress.chapters:
            links = self.toc.fetch_toc(toc_url)
            if self.max_chapters:
                links = links[:self.max_chapters]

            self.progress = CrawlProgress(
                source_toc_url=toc_url,
                total_chapters=len(links),
                chapters=[asdict(link) for link in links],
                status="running",
                started_at=datetime.now(timezone.utc).isoformat(),
            )
        else:
            # 断点恢复：重建 ChapterLink 对象
            links = [
                ChapterLink(**ch) for ch in self.progress.chapters
            ]

        # 2. 逐章采集
        merged = DissectResult(
            title=self.progress.novel_title or "",
            source_url=toc_url,
            content_source="batch_crawl",
            split_strategies_used=split_strategies,
        )

        consecutive_errors = 0
        for link in links[start_from:]:
            if link.fetched:
                continue
            if self.max_consecutive_errors and consecutive_errors >= self.max_consecutive_errors:
                merged.errors.append(
                    f"连续 {consecutive_errors} 章采集失败，采集终止"
                )
                break

            try:
                from app.ingest.scraper.pipeline import dissect_from_url
                ch_result = dissect_from_url(
                    url=link.url,
                    split_strategies=split_strategies,
                )
                if ch_result.chapters:
                    merged.chapters.extend(ch_result.chapters)
                    merged.errors.extend(ch_result.errors)
                    link.fetched = True
                    consecutive_errors = 0
                    self.progress.fetched_count += 1
                else:
                    link.error = f"拆解结果为空 (errors={ch_result.errors})"
                    merged.errors.append(f"第{link.index}章 {link.title}: {link.error}")
                    consecutive_errors += 1
                    self.progress.error_count += 1
            except Exception as exc:
                link.error = str(exc)
                merged.errors.append(f"第{link.index}章 {link.title}: {exc}")
                consecutive_errors += 1
                self.progress.error_count += 1

            # 进度回调
            if callback:
                callback(self.progress.fetched_count, self.progress.total_chapters, link.title)

        # 3. 完成
        merged._recalc()
        self.progress.status = "done" if not merged.errors else "failed"
        self.progress.completed_at = datetime.now(timezone.utc).isoformat()

        # 从第一章提取书名
        if not merged.title and merged.chapters:
            # 尝试从 URL 页面标题提取
            try:
                toc_result = self.http.get(toc_url)
                if toc_result.text:
                    import re as _re
                    m = _re.search(r'<title>(.*?)</title>', toc_result.text)
                    if m:
                        merged.title = _re.sub(r'[_\-\|].*$', '', m.group(1)).strip()
            except Exception as e:
                logger.warning(f"Failed to extract title from TOC page: {e}")
            self.progress.novel_title = merged.title

        return merged


__all__ = [
    "TOCFetcher",
    "ChapterBatchCrawler",
    "ChapterLink",
    "CrawlProgress",
    "_COMMON_TOC_SELECTORS",
]
