"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / splitter / base.py
拆分策略基类
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

定义 BaseSplitter 抽象基类，所有拆分策略必须继承此基类。
支持链式管道（多个 Splitter 依次处理同一文本）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from novel_dissector.models.schemas import Chapter, Paragraph, SplitGranularity


class BaseSplitter(ABC):
    """拆分策略基类。"""

    # 唯一标识
    name: str = "base"
    # 拆分的粒度标记
    granularity: SplitGranularity = SplitGranularity.CHAPTER

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @abstractmethod
    def split(self, text: str, **kwargs) -> list[Chapter]:
        """
        拆分入口。输入清洗后的文本，返回拆分后的章节列表。
        参数可覆盖初始化时的配置。
        """
        ...

    def _make_chapter(
        self,
        index: int,
        title: str,
        raw_text: str,
        heading_pattern: str = "",
    ) -> Chapter:
        """辅助方法：创建单章对象。"""
        return Chapter(
            index=index,
            title=title,
            raw_text=raw_text,
            heading_pattern=heading_pattern,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
