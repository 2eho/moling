"""app.ingest.scraper / core 包"""
from app.ingest.scraper.core.cleaner import (
    clean_html,
    clean_chapter_content,
    is_chapter_heading,
    is_ad_line,
    is_numeric_line,
    KNOWN_AD_PATTERNS,
    extract_title_from_html,
)
from app.ingest.scraper.core.fetcher import (
    Fetcher,
    AntiCrawlConfig,
    FetchResult,
)
from app.ingest.scraper.core.extractor import (
    extract_content,
    ExtractResult,
)
from app.ingest.scraper.core.toc_crawler import (
    TOCFetcher,
    ChapterBatchCrawler,
    ChapterLink,
    CrawlProgress,
)
from app.ingest.scraper.core.style_analyzer import (
    StyleFingerprint,
    analyze_style,
    analyze_style_from_chapters,
    analyze_style_from_result,
)
from app.ingest.scraper.core.style_prompt_builder import (
    fingerprint_to_prompt,
    fingerprint_to_compact,
)

__all__ = [
    "clean_html",
    "clean_chapter_content",
    "is_chapter_heading",
    "is_ad_line",
    "is_numeric_line",
    "KNOWN_AD_PATTERNS",
    "extract_title_from_html",
    "Fetcher",
    "AntiCrawlConfig",
    "FetchResult",
    "extract_content",
    "ExtractResult",
    "TOCFetcher",
    "ChapterBatchCrawler",
    "ChapterLink",
    "CrawlProgress",
    "StyleFingerprint",
    "analyze_style",
    "analyze_style_from_chapters",
    "analyze_style_from_result",
    "fingerprint_to_prompt",
    "fingerprint_to_compact",
]