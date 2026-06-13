"""app.ingest.scraper / splitter 包"""
from app.ingest.scraper.splitter.chapter import ChapterRegexSplitter
from app.ingest.scraper.splitter.paragraph import (
    DoubleNewlineSplitter,
    ParagraphSplitter,
)
from app.ingest.scraper.splitter.strategies import (
    register_strategy,
    get_strategy,
    list_strategies,
    split_text,
)

__all__ = [
    "ChapterRegexSplitter",
    "DoubleNewlineSplitter",
    "ParagraphSplitter",
    "register_strategy",
    "get_strategy",
    "list_strategies",
    "split_text",
]