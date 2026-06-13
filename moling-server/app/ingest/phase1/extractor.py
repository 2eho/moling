"""
墨灵 (Moling) — Ingest Phase 1 Extractor (I1-I4)

LLM 驱动的四库提取函数：
  - I1: 角色提取
  - I2: 时间线提取
  - I3: 剧情承诺提取
  - I4: 世界观提取

每个函数支持：
  - LLM 调用（通过 LLMClient）
  - 正则模式匹配（作为 LLM 降级/补充）
  - 结构化输出解析
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from app.ingest.phase1.schemas import (
    CharacterExtraction,
    ChapterAnalysis,
    PlotPromiseExtraction,
    TimelineExtraction,
    WorldExtraction,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPT_I1_CHARACTERS = """你是一位小说分析专家。请从以下小说章节中提取所有角色信息。

要求：
1. 识别所有出现的人物，包括主要角色和次要角色
2. 统计每个角色的对话次数
3. 给出简要的角色描述
4. 为每个角色分配标签（至少一个）：主角 / 配角 / 反派 / 盟友 / 中立

以 JSON 格式输出（仅 JSON，不要其他文字）：
{{
    "characters": [
        {{
            "name": "角色名",
            "aliases": ["别名1", "别名2"],
            "dialogue_count": 对话次数,
            "description": "简要角色描述",
            "tags": ["标签1", "标签2"]
        }}
    ]
}}

章节标题：{title}
章节内容：
{content}
"""

PROMPT_I2_TIMELINE = """你是一位小说分析专家。请从以下小说章节中提取事件时间线。

要求：
1. 识别章节中的所有事件
2. 标注事件的相对时间（如"三天前""当天""一个月后"）
3. 标注涉及的角色
4. 评估事件重要性（1-5，5最重要）

以 JSON 格式输出（仅 JSON，不要其他文字）：
{{
    "events": [
        {{
            "description": "事件描述",
            "relative_time": "当天/三天前/一个月后等",
            "time_anchor": "绝对时间锚点（如果存在）",
            "characters": ["角色1", "角色2"],
            "importance": 3
        }}
    ]
}}

章节标题：{title}
章节内容：
{content}
"""

PROMPT_I3_PROMISES = """你是一位小说分析专家。请从以下小说章节中识别所有剧情承诺/伏笔/悬念。

承诺类型说明：
- explicit_promise: 明确承诺，"我答应你…""一定会…""保证…"
- implicit_promise: 暗示、伏笔，"就在这时…""却发现…"
- mystery: 悬念、未解之谜，"到底是谁…""为什么…"

以 JSON 格式输出（仅 JSON，不要其他文字）：
{{
    "promises": [
        {{
            "type": "explicit_promise / implicit_promise / mystery",
            "text": "触发的原文片段",
            "context": "前后文（各50字）",
            "related_characters": ["相关角色"]
        }}
    ]
}}

章节标题：{title}
章节内容：
{content}
"""

PROMPT_I4_WORLD = """你是一位小说分析专家。请从以下小说章节中提取世界观元素。

类别说明：
- geography: 地理/地点/场景
- magic: 修炼体系/魔法规则/超自然能力
- technology: 科技/技术
- culture: 文化/风俗/习惯
- history: 历史/传说/背景故事
- rule: 规则/设定
- organization: 组织/帮派/势力
- other: 其他

以 JSON 格式输出（仅 JSON，不要其他文字）：
{{
    "world_items": [
        {{
            "term": "术语名称",
            "description": "描述",
            "category": "类别",
            "related_terms": ["相关术语"]
        }}
    ]
}}

章节标题：{title}
章节内容：
{content}
"""

# ---------------------------------------------------------------------------
# Rule-based fallback patterns
# ---------------------------------------------------------------------------

PROMISE_REGEX_PATTERNS = [
    (r"(?:答应|承诺|保证|发誓|一定)(?:会|要|能)", "explicit_promise"),
    (r"(?:到底|究竟|难道|为什么|怎么回事|怎么(?:可能|回事))", "mystery"),
    (r"(?:忽然|突然|这时|就在此时|就在这时|却发现)", "implicit_promise"),
]

CHARACTER_REF_PATTERN = re.compile(
    r"(?:说|道|问|答|喊|叫|骂|哭|笑|嚷|吼|叹|劝|吩咐|嘱咐|告诉|解释|回答)[""\u300c]"
)

# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------


async def _llm_call(
    prompt: str,
    timeout: float = 120.0,
) -> Optional[str]:
    """调用 LLM 并返回文本响应。"""
    try:
        from app.llm.client import llm_client

        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度保证一致性
            max_tokens=2048,
        )
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return content
    except Exception as e:
        logger.warning("LLM 调用失败: %s", e)
        return None


def _extract_json(text: str) -> Optional[dict]:
    """从 LLM 响应中提取 JSON。"""
    # 尝试直接解析
    text = text.strip()
    # 移除 markdown 代码块
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试找到 JSON 对象
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("无法从 LLM 响应解析 JSON: %.200s", text)
    return None


def _truncate_content(content: str, max_chars: int = 3000) -> str:
    """截断内容到指定长度（保留完整句子）。"""
    if len(content) <= max_chars:
        return content
    truncated = content[:max_chars]
    # 在最后一个句号处截断
    last_period = max(
        truncated.rfind("。"), truncated.rfind("."),
        truncated.rfind("\n"), truncated.rfind("!")
    )
    if last_period > max_chars * 0.7:
        truncated = truncated[:last_period + 1]
    return truncated


# ---------------------------------------------------------------------------
# I1: Character extraction
# ---------------------------------------------------------------------------


async def I1_extract_characters(
    chapter_data: dict,
    timeout: float = 120.0,
) -> list[CharacterExtraction]:
    """I1 人物库提取 — 从单章中提取所有角色信息。"""
    title = chapter_data.get("title", "")
    raw_text = chapter_data.get("raw_text", "")

    # 尝试通过段落拼接内容
    if not raw_text:
        paragraphs = chapter_data.get("paragraphs", [])
        if paragraphs:
            raw_text = "\n".join(p.get("text", "") for p in paragraphs)

    if not raw_text:
        return []

    content = _truncate_content(raw_text)
    prompt = PROMPT_I1_CHARACTERS.format(title=title, content=content)

    response_text = await _llm_call(prompt, timeout)
    if response_text:
        data = _extract_json(response_text)
        if data and "characters" in data:
            chapter_index = chapter_data.get("index", 0)
            return [
                CharacterExtraction(
                    name=char.get("name", f"未知角色_{i}"),
                    aliases=char.get("aliases", []),
                    dialogue_count=char.get("dialogue_count", 0),
                    description=char.get("description", ""),
                    tags=char.get("tags", []),
                    chapter_index=chapter_index,
                )
                for i, char in enumerate(data["characters"])
            ]

    # LLM 失败时的规则降级
    return _fallback_extract_characters(raw_text, chapter_data.get("index", 0))


def _fallback_extract_characters(text: str, chapter_index: int) -> list[CharacterExtraction]:
    """规则降级：通过对话标记词识别角色。"""
    chars_found: dict[str, int] = {}
    for match in CHARACTER_REF_PATTERN.finditer(text):
        # 取匹配前的中文名字（2-4字）
        before = text[max(0, match.start() - 12):match.start()]
        name_match = re.search(r"([\u4e00-\u9fff]{2,4})$", before)
        if name_match:
            name = name_match.group(1)
            chars_found[name] = chars_found.get(name, 0) + 1

    return [
        CharacterExtraction(
            name=name,
            dialogue_count=count,
            description="",
            tags=["配角"],
            chapter_index=chapter_index,
        )
        for name, count in sorted(chars_found.items(), key=lambda x: -x[1])[:20]
    ]


# ---------------------------------------------------------------------------
# I2: Timeline extraction
# ---------------------------------------------------------------------------


async def I2_extract_timeline(
    chapter_data: dict,
    timeout: float = 120.0,
) -> list[TimelineExtraction]:
    """I2 时间线提取 — 从单章中提取事件。"""
    title = chapter_data.get("title", "")
    raw_text = chapter_data.get("raw_text", "")

    if not raw_text:
        paragraphs = chapter_data.get("paragraphs", [])
        if paragraphs:
            raw_text = "\n".join(p.get("text", "") for p in paragraphs)

    if not raw_text:
        return []

    content = _truncate_content(raw_text)
    prompt = PROMPT_I2_TIMELINE.format(title=title, content=content)

    response_text = await _llm_call(prompt, timeout)
    if response_text:
        data = _extract_json(response_text)
        if data and "events" in data:
            chapter_index = chapter_data.get("index", 0)
            return [
                TimelineExtraction(
                    description=evt.get("description", ""),
                    relative_time=evt.get("relative_time", "当天"),
                    time_anchor=evt.get("time_anchor", ""),
                    characters=evt.get("characters", []),
                    importance=evt.get("importance", 3),
                    chapter_index=chapter_index,
                )
                for evt in data["events"]
            ]

    return []


# ---------------------------------------------------------------------------
# I3: Plot promises extraction
# ---------------------------------------------------------------------------


async def I3_extract_promises(
    chapter_data: dict,
    timeout: float = 120.0,
) -> list[PlotPromiseExtraction]:
    """I3 剧情承诺提取 — 识别伏笔/悬念/承诺。"""
    title = chapter_data.get("title", "")
    raw_text = chapter_data.get("raw_text", "")

    if not raw_text:
        paragraphs = chapter_data.get("paragraphs", [])
        if paragraphs:
            raw_text = "\n".join(p.get("text", "") for p in paragraphs)

    if not raw_text:
        return []

    content = _truncate_content(raw_text)
    prompt = PROMPT_I3_PROMISES.format(title=title, content=content)

    response_text = await _llm_call(prompt, timeout)
    if response_text:
        data = _extract_json(response_text)
        if data and "promises" in data:
            chapter_index = chapter_data.get("index", 0)
            return [
                PlotPromiseExtraction(
                    type=p.get("type", "implicit_promise"),
                    text=p.get("text", ""),
                    context=p.get("context", ""),
                    chapter_index=chapter_index,
                    related_characters=p.get("related_characters", []),
                )
                for p in data["promises"]
            ]

    # LLM 失败时的正则降级
    return _fallback_extract_promises(raw_text, chapter_data.get("index", 0))


def _fallback_extract_promises(text: str, chapter_index: int) -> list[PlotPromiseExtraction]:
    """使用正则表达式提取剧情承诺。"""
    promises = []
    for pattern, ptype in PROMISE_REGEX_PATTERNS:
        for match in re.finditer(pattern, text):
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)
            promises.append(PlotPromiseExtraction(
                type=ptype,
                text=text[match.start():match.end()],
                context=text[ctx_start:ctx_end],
                chapter_index=chapter_index,
            ))
    return promises


# ---------------------------------------------------------------------------
# I4: World extraction
# ---------------------------------------------------------------------------


async def I4_extract_world(
    chapter_data: dict,
    timeout: float = 120.0,
) -> list[WorldExtraction]:
    """I4 世界观提取 — 提取世界观元素。"""
    title = chapter_data.get("title", "")
    raw_text = chapter_data.get("raw_text", "")

    if not raw_text:
        paragraphs = chapter_data.get("paragraphs", [])
        if paragraphs:
            raw_text = "\n".join(p.get("text", "") for p in paragraphs)

    if not raw_text:
        return []

    content = _truncate_content(raw_text)
    prompt = PROMPT_I4_WORLD.format(title=title, content=content)

    response_text = await _llm_call(prompt, timeout)
    if response_text:
        data = _extract_json(response_text)
        if data and "world_items" in data:
            chapter_index = chapter_data.get("index", 0)
            return [
                WorldExtraction(
                    term=item.get("term", ""),
                    description=item.get("description", ""),
                    category=item.get("category", "other"),
                    chapter_index=chapter_index,
                    related_terms=item.get("related_terms", []),
                )
                for item in data["world_items"]
                if item.get("term")
            ]

    return []


# ---------------------------------------------------------------------------
# Combined: Extract all four dimensions from a chapter
# ---------------------------------------------------------------------------


async def extract_chapter_all(
    chapter_data: dict,
    chapter_index: int,
    chapter_title: str,
    timeout: float = 120.0,
) -> ChapterAnalysis:
    """从单章中提取全部四个维度的数据（I1-I4）。"""
    try:
        chars, events, promises, world_items = await asyncio.gather(
            I1_extract_characters(chapter_data, timeout),
            I2_extract_timeline(chapter_data, timeout),
            I3_extract_promises(chapter_data, timeout),
            I4_extract_world(chapter_data, timeout),
        )

        return ChapterAnalysis(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            characters=chars,
            timeline_events=events,
            promises=promises,
            world_items=world_items,
        )
    except Exception as e:
        logger.exception("章节分析失败: %s (第 %d 章)", chapter_title, chapter_index)
        return ChapterAnalysis(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            error=str(e),
        )
