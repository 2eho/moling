"""novel_dissector / splitter 包"""
from novel_dissector.splitter.chapter import ChapterRegexSplitter
from novel_dissector.splitter.paragraph import (
    DoubleNewlineSplitter,
    ParagraphSplitter,
)
from novel_dissector.splitter.strategies import (
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