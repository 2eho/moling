"""
墨灵 (Moling) — Ingest Phase 1 Merger

合并去重算法：
  - 角色合并（精确匹配、别名匹配、简称匹配）
  - 事件合并（编辑距离 + 关键词重叠）
  - 剧情承诺合并
  - 世界观合并
"""

from __future__ import annotations

import logging
from typing import Any

from app.ingest.phase1.schemas import (
    MergedCharacter,
    MergedPlotPromise,
    MergedTimelineEvent,
    MergedWorldItem,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Character merge / dedup
# ════════════════════════════════════════════════════════════════


def merge_characters(entries: list[dict]) -> list[MergedCharacter]:
    """
    角色合并去重算法。

    策略：
    1. 精确匹配：角色名完全一致 → 直接合并
    2. 别名匹配：角色名是另一个条目的别名 → 合并
    3. 简称匹配："陈道临" ↔ "陈道临长老" → 包含关系合并
    4. 每个合并操作后，保留最早出现的章节索引为主索引。
    """
    merged: dict[str, MergedCharacter] = {}
    alias_map: dict[str, str] = {}  # 别名 → 主名

    for entry in entries:
        name = entry.get("name", "")
        aliases = entry.get("aliases", [])
        chapter_idx = entry.get("chapter_index", 0)

        if not name:
            continue

        # 已存在精确匹配
        if name in merged:
            existing = merged[name]
            if chapter_idx not in existing.chapters_active:
                existing.chapters_active.append(chapter_idx)
            existing.dialogue_count += entry.get("dialogue_count", 0)
            for a in aliases:
                if a and a not in existing.aliases and a != name:
                    existing.aliases.append(a)
            _update_character_description(existing, entry)
            continue

        # 别名匹配
        found = False
        if name in alias_map:
            primary = alias_map[name]
            existing = merged[primary]
            if chapter_idx not in existing.chapters_active:
                existing.chapters_active.append(chapter_idx)
            existing.dialogue_count += entry.get("dialogue_count", 0)
            if name not in existing.aliases:
                existing.aliases.append(name)
            _update_character_description(existing, entry)
            found = True

        # 简称匹配（双向）
        if not found:
            for existing_name in list(merged.keys()):
                if name in existing_name or existing_name in name:
                    primary = existing_name if len(existing_name) >= len(name) else name
                    alias = name if primary == existing_name else existing_name
                    if primary != existing_name:
                        # 需要重命名
                        entry_to_move = merged.pop(existing_name)
                        entry_to_move.name = primary
                        if alias not in entry_to_move.aliases:
                            entry_to_move.aliases.append(alias)
                        merged[primary] = entry_to_move
                    else:
                        if alias not in merged[primary].aliases:
                            merged[primary].aliases.append(alias)
                    alias_map[alias] = primary
                    found = True
                    break

        if not found:
            # 创建新条目
            new_entry = MergedCharacter(
                name=name,
                aliases=[a for a in aliases if a and a != name],
                first_appearance=chapter_idx,
                chapters_active=[chapter_idx],
                dialogue_count=entry.get("dialogue_count", 0),
                description=entry.get("description", ""),
                tags=entry.get("tags", []),
            )
            merged[name] = new_entry
            for alias in aliases:
                if alias and alias != name:
                    alias_map[alias] = name

    return list(merged.values())


def _update_character_description(existing: MergedCharacter, entry: dict):
    """合并角色描述（保留更详细的那个）。"""
    new_desc = entry.get("description", "")
    if new_desc and len(new_desc) > len(existing.description):
        existing.description = new_desc
    for tag in entry.get("tags", []):
        if tag and tag not in existing.tags:
            existing.tags.append(tag)


# ════════════════════════════════════════════════════════════════
# Event merge / dedup
# ════════════════════════════════════════════════════════════════


def merge_similar_events(events: list[dict]) -> list[MergedTimelineEvent]:
    """
    相似事件合并。

    使用关键词重叠度计算相似性。
    相似度 > 0.75 的两个事件视为同一事件，合并。
    """
    merged: list[MergedTimelineEvent] = []
    for event in events:
        is_dup = False
        for existing in merged:
            similarity = _compute_event_similarity(event, existing)
            if similarity > 0.75:
                _merge_event(existing, event)
                is_dup = True
                break
        if not is_dup:
            merged.append(MergedTimelineEvent(
                description=event.get("description", ""),
                relative_time=event.get("relative_time", "当天"),
                time_anchor=event.get("time_anchor", ""),
                characters=event.get("characters", []),
                importance=event.get("importance", 3),
                chapter_index=event.get("chapter_index", 0),
                is_key_event=event.get("importance", 3) >= 4,
            ))
    return merged


def _compute_event_similarity(a: dict, b: MergedTimelineEvent) -> float:
    """计算两个事件描述的相似度。"""
    desc_a = a.get("description", "")
    desc_b = b.description
    if not desc_a or not desc_b:
        return 0.0

    # 关键词重叠（简单分词：按常见分隔符分割）
    import re
    words_a = set(re.findall(r"[\u4e00-\u9fff\w]+", desc_a))
    words_b = set(re.findall(r"[\u4e00-\u9fff\w]+", desc_b))
    overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)

    # 角色重叠
    chars_a = set(a.get("characters", []))
    chars_b = set(b.characters)
    char_overlap = len(chars_a & chars_b) / max(len(chars_a | chars_b), 1) if chars_a or chars_b else 0.5

    return 0.6 * overlap + 0.4 * char_overlap


def _merge_event(existing: MergedTimelineEvent, new_event: dict):
    """合并两个事件（保留更多信息的一方）。"""
    new_desc = new_event.get("description", "")
    if new_desc and len(new_desc) > len(existing.description):
        existing.description = new_desc

    # 保留更高的重要性
    new_importance = new_event.get("importance", 3)
    if new_importance > existing.importance:
        existing.importance = new_importance

    # 合并角色列表
    for char in new_event.get("characters", []):
        if char and char not in existing.characters:
            existing.characters.append(char)

    # 保留较早的章节索引
    new_chapter = new_event.get("chapter_index", 0)
    if new_chapter < existing.chapter_index:
        existing.chapter_index = new_chapter

    existing.is_key_event = existing.importance >= 4


# ════════════════════════════════════════════════════════════════
# Promise merge
# ════════════════════════════════════════════════════════════════


def merge_promises(promises: list[dict]) -> list[MergedPlotPromise]:
    """
    合并剧情承诺（按类型+文本去重）。
    """
    seen: set[tuple[str, str]] = set()
    merged: list[MergedPlotPromise] = []

    for p in promises:
        ptype = p.get("type", "implicit_promise")
        text = p.get("text", "")
        key = (ptype, text[:50])  # 用前50字符作为去重键

        if key in seen:
            continue
        seen.add(key)

        merged.append(MergedPlotPromise(
            type=ptype,
            text=text,
            context=p.get("context", ""),
            chapter_index=p.get("chapter_index", 0),
            status="dormant",
            urgency=5,
            related_characters=p.get("related_characters", []),
        ))

    return merged


# ════════════════════════════════════════════════════════════════
# World item merge
# ════════════════════════════════════════════════════════════════


def merge_world_items(items: list[dict]) -> list[MergedWorldItem]:
    """
    合并世界观条目（按术语名去重）。
    """
    merged: dict[str, MergedWorldItem] = {}

    for item in items:
        term = item.get("term", "")
        if not term:
            continue

        if term in merged:
            existing = merged[term]
            # 合并描述（保留更详细的）
            new_desc = item.get("description", "")
            if new_desc and len(new_desc) > len(existing.description):
                existing.description = new_desc
            # 合并引用章节
            ch_idx = item.get("chapter_index", 0)
            if ch_idx not in existing.reference_chapters:
                existing.reference_chapters.append(ch_idx)
            # 合并相关术语
            for rt in item.get("related_terms", []):
                if rt and rt not in existing.related_terms and rt != term:
                    existing.related_terms.append(rt)
        else:
            ch_idx = item.get("chapter_index", 0)
            merged[term] = MergedWorldItem(
                term=term,
                description=item.get("description", ""),
                category=item.get("category", "other"),
                first_appearance=ch_idx,
                reference_chapters=[ch_idx],
                related_terms=[
                    rt for rt in item.get("related_terms", [])
                    if rt and rt != term
                ],
            )

    return list(merged.values())
