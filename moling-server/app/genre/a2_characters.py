"""
墨灵 (Moling) — genre / a2_characters.py
A2 角色出场模式聚类

对应文档 §9.4.2
提取角色名、首次出场位置、出场方式，输出角色出场时序模板。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ── 出场方式正则 ──
_PATTERN_ACTION = re.compile(r'[就便一]?\s*(?:推|走|跑|跳|冲|站|坐|躺|踢|打|抓|拿|拔|抽|举)', re.DOTALL)
_PATTERN_DIALOG_PREFIX = re.compile(r'[""「『\'](.+?)[""」』\'].*?说')
_PATTERN_DESC_MARKER = re.compile(r'(?:只见|但见|却见|看到|一个|一位|一名|一身)')
_PATTERN_MYSTERY = re.compile(r'(?:黑暗中|阴影里|暗中|突然|莫名|不知)')

# 角色名提取
_CHARACTER_PREFIX = re.compile(r'([\u4e00-\u9fff]{2,4})(?:说|道|问|喊|叫|骂|哭|笑|叹|想|寻思)')


@dataclass
class CharacterEntry:
    name: str
    first_chapter: int = 0
    first_position: int = 0           # 首次出场的字数位置
    intro_method: str = "unknown"     # action/dialog/description/mystery
    chapter_count: int = 0            # 出场章节数
    dialogue_count: int = 0           # 对话次数


@dataclass
class CharacterTimingTemplate:
    """角色出场时序模板"""
    role_type: str = ""
    chapter_range: str = ""           # 推荐出场章节范围
    position_range: str = ""          # 推荐字数位置范围
    recommended_methods: list[str] = field(default_factory=list)


@dataclass 
class A2Result:
    characters: list[CharacterEntry] = field(default_factory=list)
    timing_templates: list[CharacterTimingTemplate] = field(default_factory=list)
    role_clusters: dict[str, list[CharacterEntry]] = field(default_factory=dict)
    total_novels_analyzed: int = 0


def A2_cluster_characters(chapters: list[str]) -> A2Result:
    """
    A2 角色出场模式聚类主流程。

    输入：多本小说的前 3 章文本列表（已拼接为列表）
    输出：角色出场时序模板
    """
    all_entries: list[CharacterEntry] = []
    chapter_count = len(chapters)

    for ch_idx, text in enumerate(chapters):
        entries = _extract_from_chapter(text, ch_idx + 1)
        all_entries.extend(entries)

    # 合并同名角色
    merged = _merge_characters(all_entries)

    # 聚类角色类型
    clusters = _cluster_by_role(merged, chapter_count)

    # 生成时序模板
    templates = _build_templates(clusters)

    return A2Result(
        characters=merged,
        timing_templates=templates,
        role_clusters=clusters,
        total_novels_analyzed=1,
    )


def _extract_from_chapter(text: str, chapter_index: int) -> list[CharacterEntry]:
    """从单章提取角色信息"""
    entries: list[CharacterEntry] = []
    seen: set[str] = set()

    for match in _CHARACTER_PREFIX.finditer(text):
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)

        pos = match.start()
        method = _detect_intro_method(text[max(0, pos - 50):pos + 50])
        entries.append(CharacterEntry(
            name=name,
            first_chapter=chapter_index,
            first_position=pos,
            intro_method=method,
            chapter_count=1,
            dialogue_count=1,
        ))

    return entries


def _detect_intro_method(context: str) -> str:
    """检测出场方式"""
    if _PATTERN_MYSTERY.search(context):
        return "mystery"
    if _PATTERN_DESC_MARKER.search(context):
        return "description"
    if _PATTERN_DIALOG_PREFIX.search(context):
        return "dialog"
    if _PATTERN_ACTION.search(context):
        return "action"
    return "unknown"


def _merge_characters(entries: list[CharacterEntry]) -> list[CharacterEntry]:
    """合并同名角色"""
    merged: dict[str, CharacterEntry] = {}
    for e in entries:
        if e.name in merged:
            existing = merged[e.name]
            existing.chapter_count = max(existing.chapter_count, e.chapter_count)
            existing.dialogue_count += e.dialogue_count
        else:
            merged[e.name] = e
    return list(merged.values())


def _cluster_by_role(entries: list[CharacterEntry], total_chapters: int) -> dict[str, list[CharacterEntry]]:
    """按角色类型聚类"""
    clusters: dict[str, list[CharacterEntry]] = {
        "protagonist": [],
        "core_supporting": [],
        "early_antagonist": [],
        "mysterious": [],
    }

    for e in entries:
        if e.first_chapter == 1 and e.first_position < 500:
            clusters["protagonist"].append(e)
        elif e.first_chapter == 1 and e.first_position >= 500:
            clusters["core_supporting"].append(e)
        elif e.first_chapter in (2, 3):
            clusters["early_antagonist"].append(e)
        else:
            clusters["mysterious"].append(e)

    return {k: v for k, v in clusters.items() if v}


def _build_templates(clusters: dict[str, list[CharacterEntry]]) -> list[CharacterTimingTemplate]:
    """生成时序模板"""
    role_map = {
        "protagonist": ("主角", "第1章前500字", "action/dialog"),
        "core_supporting": ("核心配角", "第1章后半~第2章前半", "dialog/description"),
        "early_antagonist": ("初期对手", "第2~3章", "action/conflict"),
        "mysterious": ("神秘角色", "第3章引入", "mystery/description"),
    }

    templates = []
    for cluster_key, members in clusters.items():
        if cluster_key not in role_map:
            continue
        label, chapter_range, methods = role_map[cluster_key]
        methods_list = methods.split("/")
        # 统计实际出场方式分布
        method_counts: dict[str, int] = {}
        for m in members:
            method_counts[m.intro_method] = method_counts.get(m.intro_method, 0) + 1
        top_methods = sorted(method_counts, key=method_counts.get, reverse=True)[:2]

        templates.append(CharacterTimingTemplate(
            role_type=label,
            chapter_range=chapter_range,
            recommended_methods=top_methods or methods_list,
        ))

    return templates
