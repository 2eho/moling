"""
墨灵 (Moling) — Ingest Phase 3 Conflict Check (I10)

冲突校验规则：
1. 角色冲突：同名不同设定
2. 时间线冲突：同一事件时间不一致
3. 世界观冲突：同一设定不同规则
4. 章节覆盖检测
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.vault_dao import (
    VaultCharacterDAO,
    VaultTimelineDAO,
    VaultWorldDAO,
)
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_world import VaultWorld

logger = logging.getLogger(__name__)

# Module-level DAO singletons
_vault_char_dao = VaultCharacterDAO()
_vault_timeline_dao = VaultTimelineDAO()
_vault_world_dao = VaultWorldDAO()


async def I10_conflict_check(
    db: AsyncSession,
    project_id: str,
    new_data: dict,
) -> list[dict]:
    """
    I10 冲突校验。

    将新导入的分析结果与系统已有数据对比，检测冲突。
    """
    conflicts: list[dict] = []

    # 1. 角色冲突
    char_conflicts = await _check_character_conflicts(db, project_id, new_data)
    conflicts.extend(char_conflicts)

    # 2. 时间线冲突
    timeline_conflicts = await _check_timeline_conflicts(db, project_id, new_data)
    conflicts.extend(timeline_conflicts)

    # 3. 世界观冲突
    world_conflicts = await _check_world_conflicts(db, project_id, new_data)
    conflicts.extend(world_conflicts)

    # 4. 章节覆盖检测
    chapter_conflicts = _check_chapter_overlap(new_data)
    conflicts.extend(chapter_conflicts)

    return conflicts


async def _check_character_conflicts(
    db: AsyncSession,
    project_id: str,
    new_data: dict,
) -> list[dict]:
    """检查角色冲突：同名不同设定。"""
    conflicts = []

    # 获取系统已有角色 (通过 DAO 封装，不直接 select())
    existing_characters = await _vault_char_dao.get_by_project(db, project_id)
    existing_chars = {c.name: c for c in existing_characters}

    # 新导入的角色
    new_chars = {}
    for c in new_data.get("characters", []):
        name = c.get("name", "")
        if name:
            new_chars[name] = c

    for name, new_char in new_chars.items():
        if name in existing_chars:
            old_char = existing_chars[name]
            # 检查描述差异
            new_desc = new_char.get("description", "")
            old_desc = old_char.description or ""
            if new_desc and old_desc and new_desc != old_desc:
                conflicts.append({
                    "type": "character_conflict",
                    "field": "description",
                    "name": name,
                    "existing": old_desc[:100],
                    "incoming": new_desc[:100],
                    "severity": "medium",
                    "resolution_strategy": "keep_existing / merge / replace",
                })

            # 检查标签差异
            new_tags = set(new_char.get("tags", []))
            old_tags = set(old_char.traits or [])
            if new_tags and old_tags and new_tags != old_tags:
                conflicts.append({
                    "type": "character_conflict",
                    "field": "tags",
                    "name": name,
                    "existing": list(old_tags),
                    "incoming": list(new_tags),
                    "severity": "low",
                    "resolution_strategy": "merge_tags",
                })

    return conflicts


async def _check_timeline_conflicts(
    db: AsyncSession,
    project_id: str,
    new_data: dict,
) -> list[dict]:
    """检查时间线冲突。"""
    conflicts = []

    # 获取已有时间线 (通过 DAO 封装，不直接 select())
    existing_events_list = await _vault_timeline_dao.get_by_project(db, project_id)
    existing_events = {e.event[:30]: e for e in existing_events_list}

    for new_event in new_data.get("timeline_events", []):
        desc = new_event.get("description", "")[:30]
        if desc in existing_events:
            old_event = existing_events[desc]
            conflicts.append({
                "type": "timeline_conflict",
                "event": desc,
                "existing_time": old_event.event,
                "incoming_time": new_event.get("description", ""),
                "severity": "high",
                "resolution_strategy": "use_newer / keep_original / manual_review",
            })

    return conflicts


async def _check_world_conflicts(
    db: AsyncSession,
    project_id: str,
    new_data: dict,
) -> list[dict]:
    """检查世界观冲突。"""
    conflicts = []

    # 获取已有世界观条目 (通过 DAO 封装，不直接 select())
    existing_terms_list = await _vault_world_dao.get_by_project(db, project_id)
    existing_terms = {w.term: w for w in existing_terms_list}

    for new_item in new_data.get("world_items", []):
        term = new_item.get("term", "")
        if term in existing_terms:
            old_item = existing_terms[term]
            new_desc = new_item.get("description", "")
            old_desc = old_item.description or ""
            if new_desc and old_desc and new_desc != old_desc:
                conflicts.append({
                    "type": "world_conflict",
                    "field": "description",
                    "name": term,
                    "existing": old_desc[:100],
                    "incoming": new_desc[:100],
                    "severity": "medium",
                    "resolution_strategy": "keep_existing / merge / replace",
                })

    return conflicts


def _check_chapter_overlap(new_data: dict) -> list[dict]:
    """检查章节覆盖冲突。"""
    conflicts = []

    existing_chapter_count = new_data.get("existing_chapter_count", 0)
    new_chapter_count = new_data.get("chapter_count", 0)

    if existing_chapter_count > 0 and new_chapter_count <= existing_chapter_count:
        conflicts.append({
            "type": "overwrite_warning",
            "detail": f"新导入 {new_chapter_count} 章 ≤ 已有 {existing_chapter_count} 章",
            "severity": "warning",
            "resolution_strategy": "confirm_overwrite / cancel",
        })

    return conflicts
