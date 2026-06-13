"""
app.ingest.scraper — 纯 Python 书籍拆解引擎

全栈纯 Python 实现，零外部重量级运行时依赖（无需 Playwright / Node / Go）。
核心能力：
  1. 从 HTML 中提取并清洗小说正文（反爬、广告过滤、Unicode 解码）
  2. 按章节拆分（正则 + 分层策略）
  3. 按段落/自然段拆分
  4. 支持自定义拆分策略（插件式）
  5. 输出结构化 JSON（分层书稿结构）

架构概要
  core/      — 基础层：网络请求、正文提取、文本清洗
  splitter/  — 拆分层：章节/段落/自定义策略
  models/    — 模型层：数据类定义
  pipeline   — 编排层：全流程管线
  config     — 配置管理
  export     — 输出格式化

典型用法
    import app.ingest.scraper as nd

    # 从 HTML 全文拆
    result = nd.dissect_html(
        raw_html=html_str,
        source_url="https://example.com/novel/123",
        split_strategies=["chapter", "paragraph"],
    )

    # 从 URL 采集并拆
    result = nd.dissect_from_url(
        url="https://example.com/novel/123",
        split_strategies=["chapter"],
    )

    # 直接拆已清洗的纯文本
    result = nd.dissect_text(
        text="...",
        split_strategies=["chapter"],
    )

    # 输出为 JSON
    print(result.json(indent=2))
"""

from app.ingest.scraper.pipeline import (
    dissect_html,
    dissect_from_url,
    dissect_text,
    DissectResult,
)
from app.ingest.scraper.models.schemas import (
    Chapter,
    Paragraph,
    Volume,
    SplitStrategy,
)
from app.ingest.scraper.config import DissectorConfig, default_config
from app.ingest.scraper.splitter.strategies import (
    register_strategy,
    get_strategy,
    list_strategies,
)

__all__ = [
    "dissect_html",
    "dissect_from_url",
    "dissect_text",
    "DissectResult",
    "Chapter",
    "Paragraph",
    "Volume",
    "SplitStrategy",
    "DissectorConfig",
    "default_config",
    "register_strategy",
    "get_strategy",
    "list_strategies",
]
