"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / export.py
输出格式支持
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

提供 DissectResult 的多种输出格式，方便下游后端消费：
  - JSON（默认，含 .json() 方法）
  - 简化摘要 JSON（不含正文，只含元数据）
  - 纯文本拼接（恢复为 TXT 格式）
  - Markdown 格式
  - 分片输出（适合流式/分页 API）
"""

from __future__ import annotations

import json
from typing import Any, Optional

from novel_dissector.models.schemas import DissectResult


def to_summary_json(result: DissectResult, indent: int = 2) -> str:
    """
    生成摘要 JSON（不含正文，只含章节级元数据）。

    格式
        {
          "title": "...",
          "chapter_count": 10,
          "total_word_count": 50000,
          "chapters": [
            {"index": 1, "title": "第一章 穿越", "word_count": 5200},
            ...
          ]
        }
    """
    summary: dict[str, Any] = {
        "title": result.title,
        "source_url": result.source_url,
        "content_source": result.content_source,
        "chapter_count": result.chapter_count,
        "paragraph_count": result.paragraph_count,
        "total_word_count": result.total_word_count,
        "strategies": result.split_strategies_used,
        "errors": result.errors,
        "chapters": [
            {
                "index": ch.index,
                "title": ch.title,
                "word_count": ch.word_count,
                "heading_pattern": ch.heading_pattern,
                "paragraph_count": len(ch.paragraphs) if ch.paragraphs else 0,
            }
            for ch in result.chapters
        ],
    }
    if result.volumes:
        summary["volumes"] = [
            {
                "index": v.index,
                "title": v.title,
                "word_count": v.word_count,
                "chapter_count": len(v.chapters),
            }
            for v in result.volumes
        ]
    return json.dumps(summary, indent=indent, ensure_ascii=False)


def to_plain_text(result: DissectResult, include_heading: bool = True) -> str:
    """
    将 DissectResult 拼接为纯文本（如 TXT 文件格式）。
    """
    lines: list[str] = []
    for ch in result.chapters:
        if include_heading and ch.title:
            lines.append(ch.title)
            lines.append("")
        if ch.paragraphs:
            for para in ch.paragraphs:
                lines.append(para.text)
                lines.append("")
        else:
            lines.append(ch.raw_text)
            lines.append("")
    return "\n".join(lines)


def to_markdown(result: DissectResult) -> str:
    """
    将 DissectResult 转换为 Markdown 格式。
    """
    lines: list[str] = []
    if result.title:
        lines.append(f"# {result.title}")
        lines.append("")

    for ch in result.chapters:
        if ch.title:
            lines.append(f"## {ch.title}")
        else:
            lines.append(f"## 第{ch.index}章")
        lines.append("")

        if ch.paragraphs:
            for para in ch.paragraphs:
                lines.append(para.text)
                lines.append("")
        else:
            lines.append(ch.raw_text)
            lines.append("")

    return "\n".join(lines)


def to_chunks(
    result: DissectResult,
    max_chunk_chapters: int = 5,
    include_meta: bool = True,
) -> list[dict[str, Any]]:
    """
    分片输出：将结果分为多个小数据块，适合流式/分页 API。

    参数
        max_chunk_chapters — 每块最多包含的章节数
        include_meta       — 每块是否包含元数据

    返回 JSON-serializable 的 dict 列表
    """
    chunks: list[dict[str, Any]] = []
    for i in range(0, len(result.chapters), max_chunk_chapters):
        batch = result.chapters[i:i + max_chunk_chapters]
        chunk: dict[str, Any] = {
            "chunk_index": len(chunks),
            "chapter_start": batch[0].index if batch else 0,
            "chapter_end": batch[-1].index if batch else 0,
            "chapter_count": len(batch),
            "chapters": [
                {
                    "index": ch.index,
                    "title": ch.title,
                    "word_count": ch.word_count,
                    "paragraphs": [
                        {
                            "index": p.index,
                            "text": p.text,
                            "char_count": p.char_count,
                        }
                        for p in (ch.paragraphs or [])
                    ],
                }
                for ch in batch
            ],
        }
        if include_meta:
            chunk["meta"] = {
                "title": result.title,
                "source_url": result.source_url,
                "total_chapters": result.chapter_count,
                "total_chunks": (result.chapter_count + max_chunk_chapters - 1) // max_chunk_chapters,
            }
        chunks.append(chunk)
    return chunks
