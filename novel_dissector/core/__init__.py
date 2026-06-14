"""novel_dissector / core 包"""
from novel_dissector.core.cleaner import (
    clean_html,
    clean_chapter_content,
    is_chapter_heading,
    is_ad_line,
    is_numeric_line,
    KNOWN_AD_PATTERNS,
    extract_title_from_html,
)
from novel_dissector.core.fetcher import (
    Fetcher,
    AntiCrawlConfig,
    FetchResult,
)
from novel_dissector.core.extractor import (
    extract_content,
    ExtractResult,
)
from novel_dissector.core.toc_crawler import (
    TOCFetcher,
    ChapterBatchCrawler,
    ChapterLink,
    CrawlProgress,
)
from novel_dissector.core.style_analyzer import (
    StyleFingerprint,
    analyze_style,
    analyze_style_from_chapters,
    analyze_style_from_result,
)
from novel_dissector.core.style_prompt_builder import (
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