"""
墨灵 (Moling) — genre / cold_start_loader.py
拆书引擎冷启动加载器。

B1→B5 完整流程：
  B1: 用户选择类型 → 匹配 Genre Profile / 通用模板 → 异步 A1-A5 分析
  B2: 预填四库（角色原型/世界观/时间线骨架）
  B3: 预填动态层（开局状态/章节锚点/初始钩子）
  B4: 预填卡牌池（15-20 条增强方向）
  B5: 用户审核 → 确认入库

输入: 用户选择的类型 + 故事梗概
输出: 预填的四库数据 + 动态层 + 卡牌池 + 3 个开篇方向
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, declarative_base

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CharacterPrototype:
    """角色原型"""
    name: str
    role: str          # 主角/配角/反派
    archetype: str     # 英雄/导师/影子/信使...
    traits: list[str] = field(default_factory=list)
    motivation: str = ""
    suggested_status: str = "active"


@dataclass
class VaultPrefill:
    """预填四库结果"""
    character_prototypes: list[dict] = field(default_factory=list)
    world_templates: list[dict] = field(default_factory=list)
    timeline_skeleton: list[dict] = field(default_factory=list)


@dataclass
class DynamicLayerPrefill:
    """预填动态层结果"""
    opening_state: dict[str, Any] = field(default_factory=dict)
    chapter_anchors: list[dict] = field(default_factory=list)
    initial_hooks: list[dict] = field(default_factory=list)


@dataclass
class CardPrefill:
    """预填卡牌"""
    direction: str = ""
    reason: str = ""
    priority: float = 0.0
    freshness_multiplier: float = 1.0
    tags: list[str] = field(default_factory=list)


@dataclass
class PrefillResult:
    """B1-B5 完整预填结果"""
    genre: str = ""
    synopsis: str = ""
    profile_source: str = ""           # "db_profile" | "template" | "llm_generated"
    profile_version: str = ""
    vault: VaultPrefill = field(default_factory=VaultPrefill)
    dynamic_layer: DynamicLayerPrefill = field(default_factory=DynamicLayerPrefill)
    card_pool: list[CardPrefill] = field(default_factory=list)
    opening_directions: list[str] = field(default_factory=list)
    async_analysis_triggered: bool = False


# ---------------------------------------------------------------------------
# Known genres
# ---------------------------------------------------------------------------

KNOWN_GENRES = {"玄幻", "仙侠", "都市", "科幻", "言情", "悬疑", "历史", "游戏"}

# ---------------------------------------------------------------------------
# Genre 通用模板（无 Profile 时的降级基座）
# ---------------------------------------------------------------------------

_GENRE_TEMPLATES: dict[str, dict[str, Any]] = {
    "玄幻": {
        "opening_state": {"status": "凡人", "realm": "无修为", "location": "偏远村落"},
        "world_archetypes": ["修炼体系", "势力分布", "远古遗迹"],
        "typical_pacing": "fast_paced",
        "opening_directions": [
            "主角意外获得上古传承，踏上修炼之路",
            "宗门被灭，主角背负血仇逃亡",
            "平凡少年觉醒隐藏血脉，震惊全城",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "主角遭遇意外变故"},
            {"chapter": 3, "type": "goal_hook", "description": "主角确立修炼目标"},
            {"chapter": 5, "type": "conflict_hook", "description": "首次正面冲突爆发"},
        ],
        "card_directions": [
            "主角在绝境中突破修为瓶颈",
            "隐藏的宗门秘辛被揭露",
            "主角意外获得神器/秘宝",
            "敌对势力暗中布局伏击",
            "主角的隐藏身世逐现端倪",
            "修炼之路上的关键选择",
            "远古遗迹中的生死试炼",
            "正邪势力的第一次正面交锋",
            "主角在绝境中获得神秘力量",
            "隐藏大能的暗中观察与考验",
            "血脉觉醒引发的天地异象",
            "各方势力对主角的争夺与拉拢",
            "修炼资源争夺中的暗流涌动",
        ],
    },
    "仙侠": {
        "opening_state": {"status": "凡人", "realm": "凝气期", "location": "修仙宗门"},
        "world_archetypes": ["修炼体系", "仙门势力", "天材地宝"],
        "typical_pacing": "steady",
        "opening_directions": [
            "资质平庸的弟子意外获得仙缘",
            "宗门大比中一鸣惊人",
            "误入禁地发现上古传承",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "主角展现不合常理的特质"},
            {"chapter": 3, "type": "goal_hook", "description": "主角得知修仙的真正目标"},
            {"chapter": 6, "type": "conflict_hook", "description": "宗门内部矛盾激化"},
        ],
        "card_directions": [
            "主角在修炼中突破自身极限",
            "宗门藏经阁中的秘密被发现",
            "灵药/法宝的争夺战",
            "同门师兄弟的恩怨情仇",
            "仙界秘闻的逐渐浮出水面",
            "渡劫时的心魔考验",
            "正邪对抗中的立场选择",
            "前世今生的因果纠葛",
            "师门长辈的暗中算计与考验",
            "仙缘在关键时刻的意外出现",
            "禁地探险中的生死危机",
            "灵根资质引发的宗门之争",
        ],
    },
    "都市": {
        "opening_state": {"status": "普通市民", "occupation": "学生/职员", "location": "现代都市"},
        "world_archetypes": ["社会势力", "特殊能力体系", "豪门世家"],
        "typical_pacing": "wave",
        "opening_directions": [
            "平凡生活中的意外转折改变命运",
            "隐藏身份被意外揭露",
            "遭遇不公后的觉醒与反击",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "日常生活被突然打破"},
            {"chapter": 2, "type": "goal_hook", "description": "主角确立目标/方向"},
            {"chapter": 4, "type": "conflict_hook", "description": "遭遇首个主要对手"},
        ],
        "card_directions": [
            "主角在职场/校园中展现过人能力",
            "都市暗流下的阴谋浮现",
            "主角的过去被逐渐揭开",
            "亲情/友情/爱情的考验",
            "特殊能力在关键时刻觉醒",
            "社会地位的激烈角逐",
            "隐藏的势力开始行动",
            "关键人物的背叛与真相",
            "豪门恩怨中的复杂博弈",
            "都市传说背后的真实事件",
            "主角的商业帝国从零开始",
            "地下势力的暗中交锋与谈判",
        ],
    },
    "科幻": {
        "opening_state": {"status": "普通公民", "era": "未来纪元", "location": "星际城市"},
        "world_archetypes": ["科技体系", "星际势力", "外星文明"],
        "typical_pacing": "fast_paced",
        "opening_directions": [
            "末日浩劫中的生存与挣扎",
            "星际探索中发现未知威胁",
            "人工智能/基因改造引发的伦理危机",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "科技改变生活的震撼展示"},
            {"chapter": 2, "type": "goal_hook", "description": "主角发现世界的真相"},
            {"chapter": 4, "type": "conflict_hook", "description": "重大危机全面爆发"},
        ],
        "card_directions": [
            "高科技装备的首次实战应用",
            "星际政治联盟的复杂博弈",
            "未知外星文明的第一类接触",
            "基因改造/人工智能的伦理困境",
            "末日生存中的艰难抉择",
            "时空穿越引发的蝴蝶效应",
            "虚拟与现实边界的模糊",
            "宇宙级灾难的倒计时",
            "星际殖民中的生存危机",
            "人工智能的觉醒与反叛",
            "宇宙深处的远古遗迹被发现",
            "平行宇宙中的另一面自己",
        ],
    },
    "言情": {
        "opening_state": {"status": "单身", "occupation": "职场新人/学生", "location": "都市"},
        "world_archetypes": ["人物关系网", "情感冲突模式", "社会阶层"],
        "typical_pacing": "wave",
        "opening_directions": [
            "命运般的邂逅带来生命转折",
            "被迫联姻/契约关系中的假戏真做",
            "久别重逢后的爱恨纠葛",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "男女主角的首次相遇"},
            {"chapter": 3, "type": "goal_hook", "description": "情感目标的明确化"},
            {"chapter": 5, "type": "conflict_hook", "description": "误会/外部阻力出现"},
        ],
        "card_directions": [
            "男女主角的甜蜜互动日常",
            "情敌/第三者的介入挑战",
            "家族反对带来的情感考验",
            "职场/学业上的相互扶持",
            "误会加深后的情感危机",
            "关键时刻的真情告白",
            "外部事件的感情催化作用",
            "身份悬殊带来的现实困境",
            "前任归来引发的感情波澜",
            "假戏真做后的真心流露",
            "久别重逢时的物是人非",
            "社会压力下的爱情坚守",
        ],
    },
    "悬疑": {
        "opening_state": {"status": "调查者", "occupation": "侦探/记者/普通人", "location": "案发现场"},
        "world_archetypes": ["案件线索网", "人物关系网", "隐藏势力"],
        "typical_pacing": "crescendo",
        "opening_directions": [
            "离奇案件的调查揭开冰山一角",
            "主角意外卷入惊天阴谋",
            "失踪/死亡事件的真相追寻",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "离奇案件的首次出现"},
            {"chapter": 2, "type": "goal_hook", "description": "主角决定深入调查"},
            {"chapter": 4, "type": "conflict_hook", "description": "调查遭遇阻碍/威胁"},
        ],
        "card_directions": [
            "关键线索的意外发现",
            "嫌疑人/证人的神秘死亡",
            "主角自身秘密与案件关联",
            "时间压力下的紧迫调查",
            "隐藏势力的暗中操控",
            "反转/真相的逐步揭露",
            "连环案件间的隐秘联系",
            "正邪难辨的人物立场",
            "目击者的离奇失踪",
            "看似无关的多起案件终于关联",
            "主角被迫与凶手正面周旋",
            "证据链中的致命破绽被发现",
        ],
    },
    "历史": {
        "opening_state": {"status": "平民/小官", "era": "古代中国", "location": "都城/边疆"},
        "world_archetypes": ["历史事件", "势力格局", "社会阶层"],
        "typical_pacing": "steady",
        "opening_directions": [
            "穿越/重生后的历史命运改变",
            "乱世中的崛起与争霸",
            "历史事件背后的阴谋与权谋",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "主角穿越/重生后的适应"},
            {"chapter": 3, "type": "goal_hook", "description": "主角确立历史改变目标"},
            {"chapter": 6, "type": "conflict_hook", "description": "首次卷入历史事件漩涡"},
        ],
        "card_directions": [
            "历史事件的关键节点介入",
            "朝堂权谋的智慧博弈",
            "战争场面的宏大描写",
            "历史人物的结识与合作",
            "现代知识在古代的应用",
            "势力联盟的结盟与背叛",
            "民生改善与科技推广",
            "历史命运的蝴蝶效应",
            "穿越者身份的秘密与暴露风险",
            "历史洪流下的个人命运抉择",
            "宫廷斗争中的步步为营",
            "边疆战事中的英雄崛起",
        ],
    },
    "游戏": {
        "opening_state": {"status": "新手玩家", "game_level": "1", "location": "新手村"},
        "world_archetypes": ["游戏系统", "职业体系", "副本秘境"],
        "typical_pacing": "fast_paced",
        "opening_directions": [
            "全息网游中的隐藏职业/天赋觉醒",
            "游戏与现实交错的危机降临",
            "竞技场上的逆袭与封神之路",
        ],
        "chapter_anchors": [
            {"chapter": 1, "type": "opening_hook", "description": "游戏世界的沉浸式引入"},
            {"chapter": 2, "type": "goal_hook", "description": "主角发现隐藏优势"},
            {"chapter": 4, "type": "conflict_hook", "description": "首次重大副本/PVP挑战"},
        ],
        "card_directions": [
            "隐藏职业/技能的意外获得",
            "竞技场/排行榜上的激烈竞争",
            "游戏公会中的团队配合",
            "稀有装备/道具的争夺战",
            "游戏系统漏洞的发现与利用",
            "NPC背后的隐藏剧情线",
            "高难度副本的首杀挑战",
            "游戏与现实世界的交集事件",
            "玩家之间的联盟与背叛",
            "游戏版本更新带来的格局变化",
            "隐藏地图中的终极BOSS战",
            "职业联赛中的逆袭与封神",
        ],
    },
}

# ---------------------------------------------------------------------------
# LLM prompt templates
# ---------------------------------------------------------------------------

_PROMPT_CHARACTER_GEN = """你是一位资深网文编辑。基于以下小说信息，生成 3-5 个角色原型。
每个角色需要包含：name（中文名）、role（主角/配角/反派）、archetype（英雄/导师/影子/信使/守护者/诱惑者/盟友/小丑）、traits（3-5个性格特征词）、motivation（核心动机）、suggested_status（active/pending）。

类型：{genre}
梗概：{synopsis}

请以 JSON 数组格式输出，不要其他内容。
"""

_PROMPT_WORLD_TEMPLATES = """你是一位资深世界观架构师。基于以下小说信息，生成 3-6 个世界观设定模板。
每个模板需要包含：name（设定名称）、type（类型）、description（简要描述）、introduction_timing（推荐引入时机）。

类型：{genre}
梗概：{synopsis}

请以 JSON 数组格式输出，不要其他内容。
"""

_PROMPT_TIMELINE_SKELETON = """你是一位资深网文节奏规划师。基于以下小说信息，生成一个 20 章的故事时间线骨架。
每章一个条目，包含：chapter（章节号）、title（章节标题建议）、key_event（核心事件）、tension_level（张力等级 1-10）。

类型：{genre}
梗概：{synopsis}

请以 JSON 数组格式输出，不要其他内容。
"""

_PROMPT_OPENING_DIRECTIONS = """你是一位资深网文编辑。基于以下小说信息，生成 3 个有差异化的开篇方向。
开篇方向应体现 genre 的特点，每个方向一句话。

类型：{genre}
梗概：{synopsis}

请以 JSON 字符串数组格式输出，不要其他内容。
"""


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class GenreProfileModel:
    """数据库 genre_profiles 表模型（非 ORM，使用原始 SQL 操作）"""
    __tablename__ = "genre_profiles"


_GENRE_PROFILES_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS genre_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre TEXT NOT NULL UNIQUE,
    profile_json TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '0.1',
    novels_analyzed INTEGER NOT NULL DEFAULT 0,
    chapters_analyzed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_PREFILL_SESSIONS_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS prefill_sessions (
    id TEXT PRIMARY KEY,
    project_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    synopsis TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft',
    prefill_data_json TEXT,
    profile_source TEXT DEFAULT 'template',
    profile_version TEXT DEFAULT '0.1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id)
)
"""

_CARD_RETIREMENT_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS card_retirement_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    trigger_count INTEGER NOT NULL DEFAULT 0,
    current_weight REAL NOT NULL DEFAULT 1.0,
    consecutive_zero_hits INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    last_trigger_type TEXT,
    last_triggered_at TIMESTAMP,
    archived_at TIMESTAMP,
    retired_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


async def _ensure_tables(db: AsyncSession) -> None:
    """Ensure required tables exist."""
    from sqlalchemy import text
    for sql in [_GENRE_PROFILES_CREATE_SQL, _PREFILL_SESSIONS_CREATE_SQL, _CARD_RETIREMENT_CREATE_SQL]:
        await db.execute(text(sql))
    await db.commit()


# ---------------------------------------------------------------------------
# ColdStartLoader
# ---------------------------------------------------------------------------


class ColdStartLoader:
    """
    拆书引擎冷启动加载器。

    输入: 用户选择的类型 + 故事梗概
    输出: 预填的四库数据 + 动态层 + 卡牌池 + 3 个开篇方向
    """

    def __init__(self, llm_client=None) -> None:
        self._llm = llm_client
        self._templates = _GENRE_TEMPLATES

    # ------------------------------------------------------------------
    # B1: 类型选择 → Genre Profile 加载
    # ------------------------------------------------------------------

    async def load_genre_profile(
        self,
        genre: str,
        db: Optional[AsyncSession] = None,
    ) -> tuple[dict[str, Any], str, bool]:
        """
        B1: 加载 Genre Profile。

        1. 从 DB 查询 genre_profiles 表匹配 genre
        2. 有已分析的 Profile → 返回
        3. 无 → 使用通用模板
        4. 返回 (profile_dict, source, triggered_async_analysis)

        Source 取值: "db_profile" | "template"
        """
        genre = genre.strip()
        if genre not in KNOWN_GENRES:
            genre = self._fuzzy_match_genre(genre)

        profile: Optional[dict[str, Any]] = None
        source = "template"

        # Try DB first
        if db is not None:
            profile = await self._query_db_profile(db, genre)

        if profile is not None:
            source = "db_profile"
            logger.info("B1: 从 DB 加载 Genre Profile [genre=%s, version=%s]", genre, profile.get("version", "0.1"))
        else:
            # Use template
            profile = self._build_template_profile(genre)
            logger.info("B1: 使用通用模板 [genre=%s]", genre)

        triggered_async = False
        if source == "template" and db is not None:
            # 异步触发 A1-A5 补全分析
            asyncio.ensure_future(self._trigger_async_analysis_genre(db, genre))
            triggered_async = True
            logger.info("B1: 异步触发 A1-A5 分析补全 [genre=%s]", genre)

        return profile, source, triggered_async

    def _fuzzy_match_genre(self, genre: str) -> str:
        """模糊匹配 genre 到已知类型"""
        for known in KNOWN_GENRES:
            if known in genre or genre in known:
                return known
        return "玄幻"  # 默认

    async def _query_db_profile(
        self, db: AsyncSession, genre: str
    ) -> Optional[dict[str, Any]]:
        """从 DB 查询已分析的 Genre Profile"""
        from sqlalchemy import text

        row = await db.execute(
            text("SELECT profile_json, version FROM genre_profiles WHERE genre = :genre"),
            {"genre": genre},
        )
        result = row.fetchone()
        if result:
            try:
                profile = json.loads(result[0])
                profile["version"] = result[1]
                return profile
            except (json.JSONDecodeError, TypeError):
                logger.warning("B1: DB profile JSON 解析失败 [genre=%s]", genre)
                return None
        return None

    def _build_template_profile(self, genre: str) -> dict[str, Any]:
        """基于通用模板构建 Profile"""
        tpl = self._templates.get(genre, self._templates["玄幻"])

        profile = {
            "genre": genre,
            "version": "0.1",
            "golden_three_structure": {
                "opening_pattern": {"type": "template", "label": f"{genre}通用开篇模式"},
                "rhythm_curve": [],
                "attraction_score": 0.5,
            },
            "character_archetypes": [
                {
                    "role_type": "主角",
                    "chapter_range": "第1章前500字",
                    "recommended_methods": ["action", "dialog"],
                },
                {
                    "role_type": "核心配角",
                    "chapter_range": "第1章后半~第2章前半",
                    "recommended_methods": ["dialog", "description"],
                },
            ],
            "world_templates": [
                {"type": wt, "name": wt, "introduction_timing": "通过角色行为暗示"}
                for wt in tpl["world_archetypes"]
            ],
            "pacing_curve": {
                "type": tpl.get("typical_pacing", "steady"),
                "confidence": 0.5,
            },
            "dynamic_layer_seeds": {
                "hook_density_level": "medium",
                "avg_density": 0.0,
                "max_density": 0.0,
            },
            "card_pool_enrichment": [
                {"direction": d, "rarity": "common", "tags": [genre, "通用"]}
                for d in tpl["card_directions"]
            ],
        }
        return profile

    async def _trigger_async_analysis_genre(
        self, db: AsyncSession, genre: str
    ) -> None:
        """异步触发 A1-A5 分析管线补全 Genre Profile"""
        try:
            from app.genre import run_full_analysis

            # 在后台执行 A1-A5 分析
            # 实际应该从采集的样本章节执行，这里用示例章节触发
            sample_chapters = [
                f"【{genre}小说第一章示例】这是一个引人入胜的开篇..."
            ]
            profile = run_full_analysis(sample_chapters, genre=genre)

            # 更新 DB
            from sqlalchemy import text
            profile_json = json.dumps(profile.json() if hasattr(profile, "json") else {}, ensure_ascii=False)
            await db.execute(
                text("""
                    INSERT INTO genre_profiles (genre, profile_json, version, novels_analyzed, chapters_analyzed)
                    VALUES (:genre, :profile_json, :version, :novels, :chapters)
                    ON CONFLICT(genre) DO UPDATE SET
                        profile_json = :profile_json,
                        version = :version,
                        novels_analyzed = :novels,
                        chapters_analyzed = :chapters,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {
                    "genre": genre,
                    "profile_json": profile_json,
                    "version": "0.1",
                    "novels": 1,
                    "chapters": 0,
                },
            )
            await db.commit()
            logger.info("B1: 异步 A1-A5 分析完成 [genre=%s]", genre)
        except Exception as e:
            logger.error("B1: 异步分析失败 [genre=%s, error=%s]", genre, e)

    # ------------------------------------------------------------------
    # B2: 预填四库
    # ------------------------------------------------------------------

    async def prefill_vault(
        self,
        db: AsyncSession,
        project_id: int,
        profile: dict[str, Any],
        synopsis: str,
    ) -> VaultPrefill:
        """
        B2: 预填四库数据。

        1. 角色原型：根据 genre + synopsis 生成 3-5 个角色原型
        2. 世界观模板：genre 对应的基础世界观设定
        3. 时间线骨架：genre 典型的故事进程骨架
        """
        genre = profile.get("genre", "")
        vault = VaultPrefill()

        # 角色原型生成
        vault.character_prototypes = await self._generate_characters(genre, synopsis)

        # 世界观模板
        vault.world_templates = profile.get("world_templates", [])
        if not vault.world_templates:
            tpl = self._templates.get(genre, self._templates["玄幻"])
            vault.world_templates = [
                {"type": wt, "name": wt, "introduction_timing": "通过角色行为暗示"}
                for wt in tpl["world_archetypes"]
            ]

        # 时间线骨架
        vault.timeline_skeleton = await self._generate_timeline(genre, synopsis)

        return vault

    async def _generate_characters(
        self, genre: str, synopsis: str
    ) -> list[dict]:
        """使用 LLM 生成角色原型，失败时使用模板降级"""
        if self._llm is not None:
            try:
                prompt = _PROMPT_CHARACTER_GEN.format(genre=genre, synopsis=synopsis[:500])
                resp = await self._llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=1024,
                    pool="pro",
                )
                content = resp["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                logger.warning("B2: LLM 角色生成失败，使用模板降级 [error=%s]", e)

        # 降级：使用类型模板
        return self._fallback_characters(genre)

    def _fallback_characters(self, genre: str) -> list[dict]:
        """LLM 失败时的角色模板降级"""
        templates = {
            "玄幻": [
                {"name": "林风", "role": "主角", "archetype": "英雄", "traits": ["坚韧", "正直", "天赋异禀"], "motivation": "为家族复仇并攀登修炼巅峰"},
                {"name": "云长老", "role": "配角", "archetype": "导师", "traits": ["智慧", "深藏不露", "慈祥"], "motivation": "培养下一代强者"},
                {"name": "血煞", "role": "反派", "archetype": "影子", "traits": ["阴险", "狠毒", "野心勃勃"], "motivation": "夺取远古传承称霸天下"},
            ],
            "都市": [
                {"name": "秦明", "role": "主角", "archetype": "英雄", "traits": ["冷静", "睿智", "深藏不露"], "motivation": "守护家人并揭开身世之谜"},
                {"name": "苏婉", "role": "配角", "archetype": "盟友", "traits": ["温柔", "坚强", "聪慧"], "motivation": "帮助主角实现目标"},
                {"name": "赵天龙", "role": "反派", "archetype": "诱惑者", "traits": ["傲慢", "阴险", "有权势"], "motivation": "维护既得利益不惜一切手段"},
            ],
        }
        return templates.get(genre, templates["玄幻"])

    async def _generate_timeline(
        self, genre: str, synopsis: str
    ) -> list[dict]:
        """使用 LLM 生成时间线骨架，失败时使用模板降级"""
        if self._llm is not None:
            try:
                prompt = _PROMPT_TIMELINE_SKELETON.format(genre=genre, synopsis=synopsis[:500])
                resp = await self._llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2048,
                    pool="pro",
                )
                content = resp["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                logger.warning("B2: LLM 时间线生成失败，使用模板降级 [error=%s]", e)

        # 降级：标准 5 章骨架
        tpl = self._templates.get(genre, self._templates["玄幻"])
        return [
            {"chapter": 1, "title": f"开端", "key_event": f"引入主角和{genre}世界观", "tension_level": 5},
            {"chapter": 3, "title": "发展", "key_event": "主角遭遇第一个挑战", "tension_level": 6},
            {"chapter": 5, "title": "小高潮", "key_event": "首次冲突/对决", "tension_level": 8},
            {"chapter": 10, "title": "转折", "key_event": "重大秘密被发现", "tension_level": 7},
            {"chapter": 20, "title": "阶段性落幕", "key_event": "第一个大目标的达成或失败", "tension_level": 9},
        ]

    # ------------------------------------------------------------------
    # B3: 预填动态层
    # ------------------------------------------------------------------

    async def prefill_dynamic_layer(
        self,
        profile: dict[str, Any],
        synopsis: str,
    ) -> DynamicLayerPrefill:
        """
        B3: 预填动态层。

        1. 开局状态：genre 典型开局
        2. 章节锚点：开局钩子 + 目标钩子 + 冲突钩子
        3. 初始钩子：3 个 genre 相关的故事钩子
        """
        genre = profile.get("genre", "")
        tpl = self._templates.get(genre, self._templates["玄幻"])

        # 开局状态
        opening_state = dict(tpl.get("opening_state", {}))
        opening_state["genre"] = genre
        opening_state["synopsis_summary"] = synopsis[:100] + "..." if len(synopsis) > 100 else synopsis

        # 章节锚点
        chapter_anchors = list(tpl.get("chapter_anchors", []))

        # 初始钩子
        initial_hooks = self._build_initial_hooks(genre, synopsis)

        return DynamicLayerPrefill(
            opening_state=opening_state,
            chapter_anchors=chapter_anchors,
            initial_hooks=initial_hooks,
        )

    def _build_initial_hooks(self, genre: str, synopsis: str) -> list[dict]:
        """根据 genre 和梗概生成初始钩子"""
        base_hooks = {
            "玄幻": [
                {"type": "mystery", "text": f"主角身上的隐藏秘密与{synopsis[:30]}...有关", "chapter": 1},
                {"type": "countdown", "text": "一场即将到来的灭顶之灾", "chapter": 3},
                {"type": "info_hook", "text": "远古传承的真相被逐步揭开", "chapter": 5},
            ],
            "都市": [
                {"type": "mystery", "text": f"主角的过去与{synopsis[:30]}...中的秘密有关", "chapter": 1},
                {"type": "countdown", "text": "迫在眉睫的重大危机", "chapter": 2},
                {"type": "cognitive_twist", "text": "看似平静的日常下暗流汹涌", "chapter": 4},
            ],
        }
        return base_hooks.get(genre, [
            {"type": "mystery", "text": f"故事的核心谜团与{synopsis[:30]}...相关", "chapter": 1},
            {"type": "info_hook", "text": "隐藏在表面之下的真相", "chapter": 3},
            {"type": "countdown", "text": "倒计时的危机即将爆发", "chapter": 5},
        ])

    # ------------------------------------------------------------------
    # B4: 预填卡牌池
    # ------------------------------------------------------------------

    async def prefill_card_pool(
        self,
        db: AsyncSession,
        project_id: int,
        profile: dict[str, Any],
        synopsis: str,
        card_count: int = 15,
    ) -> list[CardPrefill]:
        """
        B4: 预填卡牌池。

        1. 根据 genre 选取 15-20 条增强方向
        2. 根据 synopsis 个性化排序（相关度高的优先）
        3. 每条卡牌设置初始权重（freshness_multiplier=1.0）
        """
        genre = profile.get("genre", "")
        tpl = self._templates.get(genre, self._templates["玄幻"])
        directions = list(tpl.get("card_directions", []))

        # 补充通用方向
        common_directions = [
            "主角面临道德困境与艰难选择",
            "隐藏的敌人终于露出真面目",
            "关键人物的真实身份被揭露",
            "主角的核心信念受到考验",
            "意外的盟友在最需要时出现",
        ]
        directions.extend(common_directions)

        # 根据梗概关键词排序（个性化）
        scored = self._score_card_directions(directions, synopsis)
        scored.sort(key=lambda x: x[1], reverse=True)

        # 取前 card_count 条
        cards = []
        for i, (direction, score) in enumerate(scored[:card_count]):
            cards.append(CardPrefill(
                direction=direction,
                reason=f"基于{genre}类型分析，与故事梗概相关度 {score:.1%}",
                priority=round(1.0 - (i / max(len(scored), 1)), 2),
                freshness_multiplier=1.0,
                tags=[genre, "初版"],
            ))

        return cards

    def _score_card_directions(
        self, directions: list[str], synopsis: str
    ) -> list[tuple[str, float]]:
        """根据梗概对每一条方向打分"""
        synopsis_keywords = set(self._extract_keywords(synopsis))
        scored = []

        for direction in directions:
            dir_keywords = set(self._extract_keywords(direction))
            if not dir_keywords:
                scored.append((direction, 0.5))
                continue

            overlap = len(synopsis_keywords & dir_keywords)
            score = 0.3 + (overlap / max(len(dir_keywords), 1)) * 0.7
            scored.append((direction, round(min(score, 1.0), 2)))

        return scored

    def _extract_keywords(self, text: str) -> list[str]:
        """简单关键词提取：提取 2-4 字中文词组"""
        import re
        # Extract all 2-4 character Chinese substrings via sliding window
        chars = re.findall(r'[\u4e00-\u9fff]', text)
        words_set: set[str] = set()
        for i in range(len(chars)):
            for length in (2, 3, 4):
                if i + length <= len(chars):
                    words_set.add("".join(chars[i:i+length]))
        # 去除常见停用词
        stopwords = {"一个", "没有", "什么", "自己", "这个", "那个", "可以", "我们", "他们", "不是", "就是", "知道", "不会", "已经", "还是"}
        return [w for w in words_set if w not in stopwords]

    # ------------------------------------------------------------------
    # B5: 用户审核 & 入库
    # ------------------------------------------------------------------

    async def create_prefill_session(
        self,
        db: AsyncSession,
        project_id: int,
        genre: str,
        synopsis: str,
        prefill: PrefillResult,
    ) -> str:
        """创建预填会话（B5 阶段）"""
        from sqlalchemy import text

        session_id = str(uuid4())
        await db.execute(
            text("""
                INSERT INTO prefill_sessions (id, project_id, genre, synopsis, state, prefill_data_json, profile_source, profile_version)
                VALUES (:id, :project_id, :genre, :synopsis, 'draft', :data_json, :source, :version)
                ON CONFLICT(project_id) DO UPDATE SET
                    id = :id,
                    genre = :genre,
                    synopsis = :synopsis,
                    state = 'draft',
                    prefill_data_json = :data_json,
                    profile_source = :source,
                    profile_version = :version,
                    updated_at = CURRENT_TIMESTAMP
            """),
            {
                "id": session_id,
                "project_id": project_id,
                "genre": genre,
                "synopsis": synopsis,
                "data_json": self._prefill_to_json(prefill),
                "source": prefill.profile_source,
                "version": prefill.profile_version,
            },
        )
        await db.commit()
        return session_id

    def _prefill_to_json(self, prefill: PrefillResult) -> str:
        """序列化预填结果为 JSON"""
        data = {
            "genre": prefill.genre,
            "synopsis": prefill.synopsis,
            "profile_source": prefill.profile_source,
            "profile_version": prefill.profile_version,
            "vault": asdict(prefill.vault),
            "dynamic_layer": asdict(prefill.dynamic_layer),
            "card_pool": [
                {
                    "direction": c.direction,
                    "reason": c.reason,
                    "priority": c.priority,
                    "freshness_multiplier": c.freshness_multiplier,
                    "tags": c.tags,
                }
                for c in prefill.card_pool
            ],
            "opening_directions": prefill.opening_directions,
        }
        return json.dumps(data, ensure_ascii=False)

    async def get_prefill_session(
        self, db: AsyncSession, project_id: int
    ) -> Optional[dict[str, Any]]:
        """获取预填会话（B5 审核用）"""
        from sqlalchemy import text

        row = await db.execute(
            text("""
                SELECT id, project_id, genre, synopsis, state, prefill_data_json, profile_source, profile_version, created_at, updated_at
                FROM prefill_sessions WHERE project_id = :project_id
            """),
            {"project_id": project_id},
        )
        result = row.fetchone()
        if result is None:
            return None

        session = {
            "id": result[0],
            "project_id": result[1],
            "genre": result[2],
            "synopsis": result[3],
            "state": result[4],
            "prefill_data": json.loads(result[5]) if result[5] else None,
            "profile_source": result[6],
            "profile_version": result[7],
            "created_at": str(result[8]) if result[8] else None,
            "updated_at": str(result[9]) if result[9] else None,
        }
        return session

    async def confirm_prefill(
        self,
        db: AsyncSession,
        project_id: int,
        modifications: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """用户确认预填数据并入库（B5 最终步骤）"""
        from sqlalchemy import text

        # 获取会话
        session = await self.get_prefill_session(db, project_id)
        if session is None:
            raise ValueError(f"Project {project_id} 没有未确认的预填数据")

        if session["state"] != "draft":
            raise ValueError(f"Project {project_id} 的预填数据已经确认过")

        # 应用用户修改
        prefill_data = session["prefill_data"]
        if modifications and prefill_data:
            prefill_data = self._apply_modifications(prefill_data, modifications)

        # 更新状态
        await db.execute(
            text("UPDATE prefill_sessions SET state = 'confirmed', prefill_data_json = :data_json, updated_at = CURRENT_TIMESTAMP WHERE project_id = :project_id"),
            {
                "project_id": project_id,
                "data_json": json.dumps(prefill_data, ensure_ascii=False) if prefill_data else session.get("prefill_data_json"),
            },
        )

        # 入库到项目表
        await db.execute(
            text("UPDATE projects SET synopsis = :synopsis, genre = :genre, updated_at = CURRENT_TIMESTAMP WHERE id = :project_id"),
            {
                "project_id": project_id,
                "synopsis": session["synopsis"],
                "genre": session["genre"],
            },
        )

        await db.commit()

        return {
            "project_id": project_id,
            "state": "confirmed",
            "message": "预填数据已确认并入库",
        }

    def _apply_modifications(
        self, prefill_data: dict[str, Any], modifications: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """应用用户对预填数据的修改"""
        result = dict(prefill_data)
        for mod in modifications:
            path = mod.get("path", "").split(".")
            action = mod.get("action", "update")
            value = mod.get("value")

            if action == "update":
                self._set_nested_path(result, path, value)
            elif action == "delete":
                self._delete_nested_path(result, path)
            elif action == "add":
                self._add_to_nested_path(result, path, value)

        return result

    def _set_nested_path(
        self, data: Any, path: list[str], value: Any
    ) -> None:
        """Set a value at a nested dict/list path (in-place)."""
        current = data
        for i, key in enumerate(path[:-1]):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError, TypeError):
                    return
            else:
                return
            if current is None:
                return

        last_key = path[-1]
        if isinstance(current, dict):
            current[last_key] = value
        elif isinstance(current, list):
            try:
                current[int(last_key)] = value
            except (ValueError, IndexError, TypeError):
                pass

    def _delete_nested_path(
        self, data: Any, path: list[str]
    ) -> None:
        """Delete an item at a nested path (in-place)."""
        if len(path) < 2:
            return
        parent_path = path[:-1]
        target = path[-1]
        parent = self._resolve_path(data, parent_path)
        if isinstance(parent, dict):
            parent.pop(target, None)
        elif isinstance(parent, list):
            try:
                idx = int(target)
                if 0 <= idx < len(parent):
                    parent.pop(idx)
            except (ValueError, IndexError):
                pass

    def _add_to_nested_path(
        self, data: Any, path: list[str], value: Any
    ) -> None:
        """Add an item to a list at a nested path (in-place)."""
        target = self._resolve_path(data, path)
        if isinstance(target, list) and value is not None:
            target.append(value)

    def _resolve_path(self, data: Any, path: list[str]) -> Any:
        """Walk a nested dict/list path and return the target container."""
        current = data
        for key in path:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (ValueError, IndexError, TypeError):
                    return None
            else:
                return None
        return current

    # ------------------------------------------------------------------
    # 完整 B1-B5 流程
    # ------------------------------------------------------------------

    async def run_cold_start(
        self,
        db: AsyncSession,
        project_id: int,
        genre: str,
        synopsis: str,
    ) -> PrefillResult:
        """
        完整执行 B1-B5 冷启动流程。

        返回 PrefillResult 供前端展示 + 触发异步分析。
        """
        result = PrefillResult(genre=genre, synopsis=synopsis)

        # B1: 加载 Profile
        profile, profile_source, async_triggered = await self.load_genre_profile(genre, db)
        result.profile_source = profile_source
        result.profile_version = profile.get("version", "0.1")
        result.async_analysis_triggered = async_triggered

        # B2: 预填四库
        result.vault = await self.prefill_vault(db, project_id, profile, synopsis)

        # B3: 预填动态层
        result.dynamic_layer = await self.prefill_dynamic_layer(profile, synopsis)

        # B4: 预填卡牌池
        result.card_pool = await self.prefill_card_pool(db, project_id, profile, synopsis)

        # 开篇方向（3 个）
        result.opening_directions = await self._generate_opening_directions(genre, synopsis)

        # B5: 创建预填会话
        await self.create_prefill_session(db, project_id, genre, synopsis, result)

        return result

    async def _generate_opening_directions(
        self, genre: str, synopsis: str
    ) -> list[str]:
        """生成 3 个开篇方向"""
        if self._llm is not None:
            try:
                prompt = _PROMPT_OPENING_DIRECTIONS.format(genre=genre, synopsis=synopsis[:500])
                resp = await self._llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=512,
                    pool="pro",
                )
                content = resp["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, list) and len(parsed) >= 3:
                    return parsed[:3]
            except Exception as e:
                logger.warning("B3: LLM 开篇方向生成失败，使用模板降级 [error=%s]", e)

        # 降级
        tpl = self._templates.get(genre, self._templates["玄幻"])
        return tpl.get("opening_directions", ["开始你的故事..."])


# ---------------------------------------------------------------------------
# DataRetirementManager
# ---------------------------------------------------------------------------


class DataRetirementManager:
    """
    数据退役管理器。

    4 个退役触发器:
    A: 连续 3 次零命中 → 退役（权重 80%→50%→20%→0%）
    B: 超过 100 章未使用 → 归档
    C: 引擎版本更新 → 旧版数据标记退役
    D: 用户手动指定 → 即时退役

    权重衰减：
    - 首次触发: 80% 权重
    - 二次触发: 50% 权重
    - 三次触发: 20% 权重
    - 四次触发: 0% 权重（归档，不可用）
    """

    WEIGHT_DECAY_STEPS = [1.0, 0.8, 0.5, 0.2, 0.0]
    MAX_ZERO_HITS = 3
    MAX_UNUSED_CHAPTERS = 100

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 权重衰减
    # ------------------------------------------------------------------

    def compute_weight(self, trigger_count: int) -> float:
        """
        根据触发次数计算当前权重。

        首次触发 → 0.8, 二次 → 0.5, 三次 → 0.2, 四次 → 0.0
        """
        step_idx = min(trigger_count, len(self.WEIGHT_DECAY_STEPS) - 1)
        return self.WEIGHT_DECAY_STEPS[step_idx]

    # ------------------------------------------------------------------
    # 触发器 A: 连续 3 次零命中
    # ------------------------------------------------------------------

    async def trigger_a_zero_hits(self, card_id: str) -> bool:
        """
        触发器 A: 记录一次零命中。连续 3 次 → 触发权重衰减。

        返回 True 表示触发了退役动作。
        """
        tracker = await self._get_or_create_tracker(card_id)
        tracker["consecutive_zero_hits"] = tracker.get("consecutive_zero_hits", 0) + 1

        if tracker["consecutive_zero_hits"] >= self.MAX_ZERO_HITS:
            # 触发衰减
            return await self._apply_weight_decay(card_id, "A: consecutive_zero_hits")
        else:
            await self._update_tracker(card_id, {
                "consecutive_zero_hits": tracker["consecutive_zero_hits"],
            })
            return False

    # ------------------------------------------------------------------
    # 触发器 B: 超过 100 章未使用
    # ------------------------------------------------------------------

    async def trigger_b_unused_chapters(
        self, card_id: str, current_chapter_count: int, last_used_chapter: int
    ) -> bool:
        """
        触发器 B: 超过 100 章未使用 → 归档。

        current_chapter_count: 作品当前章节总数
        last_used_chapter: 该卡牌最后被使用的章节号
        """
        unused = current_chapter_count - last_used_chapter
        if unused >= self.MAX_UNUSED_CHAPTERS:
            return await self._archive_card(card_id, f"B: {unused} 章未使用 (上限{self.MAX_UNUSED_CHAPTERS}章)")
        return False

    # ------------------------------------------------------------------
    # 触发器 C: 引擎版本更新
    # ------------------------------------------------------------------

    async def trigger_c_engine_update(self, card_id: str, profile_version: str) -> bool:
        """
        触发器 C: 引擎版本更新 → 旧版数据标记退役。

        profile_version: 当前 Genre Profile 版本号
        比较版本号决定是否退役。
        """
        # 获取卡牌创建时的 Profile 版本
        from sqlalchemy import text
        row = await self.db.execute(
            text("SELECT profile_version FROM prefill_sessions ps "
                 "JOIN card_retirement_tracker cr ON ps.project_id = cr.project_id "
                 "WHERE cr.card_id = :card_id"),
            {"card_id": card_id},
        )
        result = row.fetchone()
        if result and result[0] != profile_version:
            # 版本不同，标记为需升级
            return await self._mark_retired(card_id, f"C: Profile 版本变更 [old={result[0]}, new={profile_version}]")
        return False

    # ------------------------------------------------------------------
    # 触发器 D: 用户手动指定
    # ------------------------------------------------------------------

    async def trigger_d_manual(self, card_id: str, reason: str = "") -> bool:
        """
        触发器 D: 用户手动指定 → 即时退役。
        """
        return await self._mark_retired(card_id, f"D: 用户手动 [reason={reason}]")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _get_or_create_tracker(self, card_id: str) -> dict[str, Any]:
        """获取或创建卡牌退役跟踪记录"""
        from sqlalchemy import text

        row = await self.db.execute(
            text("SELECT * FROM card_retirement_tracker WHERE card_id = :card_id"),
            {"card_id": card_id},
        )
        result = row.fetchone()
        if result:
            return {
                "id": result[0],
                "card_id": result[1],
                "project_id": result[2],
                "trigger_count": result[3],
                "current_weight": result[4],
                "consecutive_zero_hits": result[5],
                "status": result[6],
            }

        # 创建新记录
        await self.db.execute(
            text("""
                INSERT INTO card_retirement_tracker (card_id, trigger_count, current_weight, consecutive_zero_hits, status)
                VALUES (:card_id, 0, 1.0, 0, 'active')
            """),
            {"card_id": card_id},
        )
        await self.db.commit()
        return {
            "card_id": card_id,
            "trigger_count": 0,
            "current_weight": 1.0,
            "consecutive_zero_hits": 0,
            "status": "active",
        }

    async def _update_tracker(self, card_id: str, updates: dict[str, Any]) -> None:
        """更新跟踪记录"""
        from sqlalchemy import text
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["card_id"] = card_id
        await self.db.execute(
            text(f"UPDATE card_retirement_tracker SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE card_id = :card_id"),
            updates,
        )
        await self.db.commit()

    async def _apply_weight_decay(self, card_id: str, reason: str) -> bool:
        """应用权重衰减"""
        from sqlalchemy import text

        row = await self.db.execute(
            text("SELECT trigger_count FROM card_retirement_tracker WHERE card_id = :card_id"),
            {"card_id": card_id},
        )
        result = row.fetchone()
        trigger_count = (result[0] if result else 0) + 1
        new_weight = self.compute_weight(trigger_count)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if new_weight <= 0.0:
            # 归档
            await self.db.execute(
                text("""
                    UPDATE card_retirement_tracker SET
                        trigger_count = :trigger_count,
                        current_weight = :weight,
                        status = 'retired',
                        last_trigger_type = :reason,
                        last_triggered_at = :now,
                        archived_at = :now,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE card_id = :card_id
                """),
                {
                    "card_id": card_id,
                    "trigger_count": trigger_count,
                    "weight": new_weight,
                    "reason": reason,
                    "now": now,
                },
            )
        else:
            await self.db.execute(
                text("""
                    UPDATE card_retirement_tracker SET
                        trigger_count = :trigger_count,
                        current_weight = :weight,
                        consecutive_zero_hits = 0,
                        last_trigger_type = :reason,
                        last_triggered_at = :now,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE card_id = :card_id
                """),
                {
                    "card_id": card_id,
                    "trigger_count": trigger_count,
                    "weight": new_weight,
                    "reason": reason,
                    "now": now,
                },
            )

        await self.db.commit()

        logger.info("DataRetirement: 权重衰减 applied [card_id=%s, weight=%.1f, reason=%s]", card_id, new_weight, reason)
        return new_weight <= 0.0

    async def _archive_card(self, card_id: str, reason: str) -> bool:
        """归档卡牌"""
        from sqlalchemy import text

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await self.db.execute(
            text("""
                UPDATE card_retirement_tracker SET
                    status = 'archived',
                    current_weight = 0.0,
                    last_trigger_type = :reason,
                    last_triggered_at = :now,
                    archived_at = :now,
                    updated_at = CURRENT_TIMESTAMP
                WHERE card_id = :card_id
            """),
            {"card_id": card_id, "reason": reason, "now": now},
        )
        await self.db.commit()

        logger.info("DataRetirement: 卡牌归档 [card_id=%s, reason=%s]", card_id, reason)
        return True

    async def _mark_retired(self, card_id: str, reason: str) -> bool:
        """标记已退役"""
        from sqlalchemy import text

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await self.db.execute(
            text("""
                UPDATE card_retirement_tracker SET
                    status = 'retired',
                    current_weight = 0.0,
                    last_trigger_type = :reason,
                    last_triggered_at = :now,
                    archived_at = :now,
                    updated_at = CURRENT_TIMESTAMP
                WHERE card_id = :card_id
            """),
            {"card_id": card_id, "reason": reason, "now": now},
        )
        await self.db.commit()

        logger.info("DataRetirement: 卡牌退役 [card_id=%s, reason=%s]", card_id, reason)
        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_retired_cards(self, project_id: Optional[int] = None) -> list[dict[str, Any]]:
        """获取已退役/已归档的卡牌列表"""
        from sqlalchemy import text

        if project_id is not None:
            row = await self.db.execute(
                text("""
                    SELECT card_id, project_id, trigger_count, current_weight, consecutive_zero_hits,
                           status, last_trigger_type, last_triggered_at, archived_at, retired_by
                    FROM card_retirement_tracker
                    WHERE project_id = :project_id AND status IN ('retired', 'archived')
                    ORDER BY archived_at DESC
                """),
                {"project_id": project_id},
            )
        else:
            row = await self.db.execute(
                text("""
                    SELECT card_id, project_id, trigger_count, current_weight, consecutive_zero_hits,
                           status, last_trigger_type, last_triggered_at, archived_at, retired_by
                    FROM card_retirement_tracker
                    WHERE status IN ('retired', 'archived')
                    ORDER BY archived_at DESC
                """),
            )

        results = []
        for r in row.fetchall():
            results.append({
                "card_id": r[0],
                "project_id": r[1],
                "trigger_count": r[2],
                "current_weight": r[3],
                "consecutive_zero_hits": r[4],
                "status": r[5],
                "last_trigger_type": r[6],
                "last_triggered_at": str(r[7]) if r[7] else None,
                "archived_at": str(r[8]) if r[8] else None,
                "retired_by": r[9],
            })
        return results

    async def get_card_weight(self, card_id: str) -> float:
        """获取卡牌当前权重"""
        from sqlalchemy import text

        row = await self.db.execute(
            text("SELECT current_weight FROM card_retirement_tracker WHERE card_id = :card_id"),
            {"card_id": card_id},
        )
        result = row.fetchone()
        return result[0] if result else 1.0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

cold_start_loader = ColdStartLoader()
