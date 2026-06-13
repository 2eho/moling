"""
墨灵 (Moling) — genre / a5_profile_output.py
A5 套路归纳 + 去版权化 + Genre Profile 全量输出

汇总 A1-A4 分析结果，生成完整的 Genre Profile。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app.genre.models import GenreProfile
from app.genre.a1_opening import A1Result
from app.genre.a2_characters import A2Result
from app.genre.a3_hooks import A3Result
from app.genre.a4_rhythm import A4Result


# 受版权保护的知名角色名（示例，项目上线时应扩充）
_COPYRIGHTED_NAMES: set[str] = {
    "哈利·波特", "哈利波特", "赫敏", "罗恩", "邓布利多",
    "孙悟空", "唐三", "萧炎", "林动", "叶凡",
    "路明非", "楚子航", "上杉绘梨衣",
    "范闲", "陈长生", "徐凤年",
}


def A5_summarize_patterns(
    a1: A1Result,
    a2: A2Result,
    a3: A3Result,
    a4: A4Result,
    genre: str = "",
    novels_analyzed: int = 1,
) -> GenreProfile:
    """
    A5 套路归纳 + 去版权化。

    汇聚 A1-A4 结果，生成可持久化的 GenreProfile。
    自动执行去版权化过滤（移除受版权保护的角色名/设定名）。
    """
    # 去版权化过滤
    filtered_chars = _filter_copyrighted(a2.characters)
    filtered_templates = []
    for t in a2.timing_templates:
        filtered_templates.append(t)

    profile = GenreProfile(
        genre=genre,
        version="0.1",
        novels_analyzed=novels_analyzed,
        chapters_analyzed=a4.chapter_count if a4.chapter_count > 0 else len(a1.rhythm_curve),
    )

    # 黄金三章结构
    profile.golden_three_structure = {
        "opening_pattern": {
            "type": a1.opening_pattern.pattern_type,
            "confidence": a1.opening_pattern.confidence,
            "label": _pattern_label(a1.opening_pattern.pattern_type),
        },
        "rhythm_curve": a1.rhythm_curve,
        "attraction_score": a1.attraction_score,
    }

    # 角色原型
    profile.character_archetypes = [
        {
            "role_type": t.role_type,
            "chapter_range": t.chapter_range,
            "recommended_methods": t.recommended_methods,
        }
        for t in filtered_templates
    ]

    # 节奏曲线
    profile.pacing_curve = {
        "type": a4.rhythm_profile.rhythm_type,
        "slopes": a4.rhythm_profile.slopes,
        "inflection_points": a4.rhythm_profile.inflection_points,
        "confidence": a4.rhythm_profile.confidence,
    }

    # 世界观模板提取（从角色和正文中提取组织、势力、能力体系）
    profile.world_templates = _extract_world_templates(a2, genre)

    # 钩子密度
    profile.dynamic_layer_seeds = {
        "hook_density_level": a3.overall_level,
        "avg_density": a3.avg_density,
        "max_density": a3.max_density,
        "climax_chapters": a3.climax_chapters,
    }

    # 卡牌池预填（基于套路归纳的推荐方向）
    profile.card_pool_enrichment = _generate_card_seeds(a1, a3)

    return profile


def _extract_world_templates(a2: A2Result, genre: str) -> list[dict]:
    """从角色和类型信息中提取世界观模板"""
    templates: list[dict] = []
    seen_terms: set[str] = set()

    # 从角色名推断可能的世界观设定
    for c in a2.characters:
        # 寻找"XX家"、"XX宗"、"XX门"等组织名模式
        import re
        org_matches = re.findall(r'[\u4e00-\u9fff]{1,4}(?:家|宗|门|派|国|城|殿|堂|帮|盟|会)', c.name)
        for org in org_matches:
            if org not in seen_terms:
                seen_terms.add(org)
                templates.append({
                    "type": "势力/组织",
                    "name": org,
                    "introduction_timing": "通过角色对话/事件暗示",
                })

    # 根据类型添加通用世界观骨架
    genre_schemas = {
        "玄幻": [
            {"type": "修炼体系", "levels": ["练气", "筑基", "金丹", "元婴", "化神", "渡劫"],
             "introduction_method": "通过角色行为暗示（非旁白说明）"},
            {"type": "势力分布", "archetypes": ["正道大宗", "魔门/邪道", "中立势力", "远古遗迹"]},
        ],
        "都市": [
            {"type": "社会设定", "archetypes": ["豪门世家", "地下势力", "特殊机构", "民间组织"],
             "introduction_timing": "第 1-2 章通过事件暗示"},
            {"type": "特殊能力体系", "introduction_method": "主角或配角首次展示能力时揭示"},
        ],
        "仙侠": [
            {"type": "修炼体系", "levels": ["凝气", "筑基", "金丹", "元婴", "化神", "渡劫"],
             "introduction_method": "通过修炼场景逐步展示"},
        ],
    }

    for genre_key in genre_schemas:
        if genre_key in genre:
            templates.extend(genre_schemas[genre_key])

    return templates


def _pattern_label(pattern_type: str) -> str:
    labels = {
        "direct_conflict": "直接冲突开篇",
        "daily_life": "日常引入开篇",
        "flashback": "倒叙/悬疑开篇",
        "world_building": "设定引入开篇",
    }
    return labels.get(pattern_type, "未知")


def _filter_copyrighted(characters) -> list:
    """过滤受版权保护的角色名"""
    return [c for c in characters if c.name not in _COPYRIGHTED_NAMES]


def _generate_card_seeds(a1: A1Result, a3: A3Result) -> list[dict]:
    """基于分析结果生成初始卡牌方向"""
    seeds = []

    # 根据开篇模式生成
    if a1.opening_pattern.pattern_type == "direct_conflict":
        seeds.append({"direction": "主角在冲突中展现核心能力", "rarity": "rare", "tags": ["冲突", "能力展示"]})
        seeds.append({"direction": "冲突升级，引入更大威胁", "rarity": "epic", "tags": ["冲突", "升级"]})
    elif a1.opening_pattern.pattern_type == "daily_life":
        seeds.append({"direction": "日常被打破，突发事件引入", "rarity": "common", "tags": ["日常", "转折"]})
        seeds.append({"direction": "平凡生活的真相被揭示", "rarity": "rare", "tags": ["真相", "揭示"]})
    elif a1.opening_pattern.pattern_type == "flashback":
        seeds.append({"direction": "过去的事件与现在产生关联", "rarity": "rare", "tags": ["悬疑", "关联"]})
        seeds.append({"direction": "回忆中的关键人物现身", "rarity": "epic", "tags": ["回忆", "人物"]})
    elif a1.opening_pattern.pattern_type == "world_building":
        seeds.append({"direction": "世界观中的隐藏规则被触发", "rarity": "rare", "tags": ["世界观", "规则"]})
        seeds.append({"direction": "新人物的到来揭示世界的另一面", "rarity": "common", "tags": ["新人", "世界观"]})

    # 通用种子
    seeds.append({"direction": "主角面临关键选择", "rarity": "common", "tags": ["选择", "成长"]})
    seeds.append({"direction": "隐藏的敌人开始行动", "rarity": "epic", "tags": ["反派", "阴谋"]})

    return seeds


def profile_to_json(profile: GenreProfile, indent: int = 2) -> str:
    """将 GenreProfile 输出为 JSON"""
    d = asdict(profile)
    return json.dumps(d, indent=indent, ensure_ascii=False)
