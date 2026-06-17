"""墨灵 (Moling) — VaultFilterService 单元测试。

测试覆盖：
- 正常场景：多卡片 ID 提取、四库过滤、层级压缩
- 边界场景：空列表、不存在的 ID、特殊 timeline_point
- 压缩逻辑：Level 1 全文 vs Level 2 仅 current_state
- Token 估算、300 字截断
- 异常场景：DAO 异常传播
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.service.vault_filter import VaultFilterService


# ── 确保 async 测试在没有 conftest 的场景下也能运行 ──


@pytest.fixture(scope="session")
def event_loop():
    """会话级别事件循环（兼容 --noconftest）。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def service() -> VaultFilterService:
    """提供未注入 DAO 的 VaultFilterService 实例（使用默认 DAO）。"""
    return VaultFilterService()


@pytest.fixture
def mock_dao() -> MagicMock:
    """Mock VaultDAO 实例，所有方法为 AsyncMock。"""
    dao = MagicMock()
    dao.get_characters = AsyncMock()
    dao.get_character = AsyncMock()
    dao.get_timeline = AsyncMock()
    dao.get_timeline_event = AsyncMock()
    dao.get_plot_promises = AsyncMock()
    dao.get_plot_promise = AsyncMock()
    dao.get_world_entries = AsyncMock()
    dao.get_world_entry = AsyncMock()
    return dao


@pytest.fixture
def svc(mock_dao) -> VaultFilterService:
    """注入 Mock DAO 的 VaultFilterService。"""
    return VaultFilterService(dao=mock_dao)


@pytest.fixture
def mock_db():
    """Mock AsyncSession。"""
    return AsyncMock()


# ──────────── 辅助函数 ────────────
# 使用 SimpleNamespace 而非 MagicMock，避免 MagicMock 属性再返回 Mock 对象的问题。


def make_card(
    *,
    char_refs: Optional[List[dict]] = None,
    prom_refs: Optional[List[dict]] = None,
    timeline_pt: Optional[str] = None,
    world_refs: Optional[List[dict]] = None,
) -> SimpleNamespace:
    """创建一个模拟的 CardPool 对象。"""
    return SimpleNamespace(
        characters=char_refs or [],
        plot_promises=prom_refs or [],
        timeline_point=timeline_pt,
        world_rules=world_refs or [],
    )


def make_char(**overrides) -> SimpleNamespace:
    """创建一个模拟的 VaultCharacter 对象。"""
    defaults = dict(
        id="c0001",
        name="林夜",
        role="protagonist",
        faction="天剑宗",
        status="active",
        location="剑锋山",
        appearance="黑衣黑发，眼神锐利",
        personality="沉稳果断，重情重义",
        knowledge=["剑术", "阵法"],
        confidence=0.85,
        current_state="正在突破筑基期",
        motivation="复仇与守护宗门",
        emotion="坚定",
        traits=["勇敢", "忠诚"],
        description="天剑宗首席弟子，身负血海深仇的天才剑修。"
                    "年少时目睹满门被灭，幸存后隐忍修炼十余年，如今已是筑基期巅峰。",
        background="自幼在天剑宗长大，十八岁时宗门遭魔教突袭，师父为护他而牺牲。"
                   "此后立誓复仇，日夜苦修。",
        relationships=[{"target": "苏瑶", "type": "同门"}],
        state_machine={"current": "复仇者", "transitions": []},
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_timeline(**overrides) -> SimpleNamespace:
    """创建一个模拟的 VaultTimeline 对象。"""
    defaults = dict(
        id="t0001",
        event="宗门被灭",
        description="天剑宗遭遇魔教夜袭，掌门战死",
        chapter_number=5,
        day=30,
        importance="critical",
        is_key_event=True,
        impact="主角失去所有亲人",
        characters_involved=["林夜"],
        precedes=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_promise(**overrides) -> SimpleNamespace:
    """创建一个模拟的 VaultPlotPromise 对象。"""
    defaults = dict(
        id="p0001",
        description="林夜必将手刃仇人",
        type="promise",
        title="复仇之誓",
        status="active",
        urgency=8,
        advancement_log=[],
        related_characters=["林夜"],
        planted_chapter=5,
        redeem_window=20,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_world(**overrides) -> SimpleNamespace:
    """创建一个模拟的 VaultWorld 对象。"""
    defaults = dict(
        id="w0001",
        name="筑基期",
        description="修真境界第二阶，可御剑飞行",
        category="rule",
        constraint="筑基需大量灵气",
        related_entities=[],
        source_chapter=1,
        reference_chapters=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def mock_execute(
    scenario: str,
    characters: List | None = None,
    promises: List | None = None,
    world: List | None = None,
):
    """创建模拟的 db.execute 返回工厂函数。"""
    def _execute(stmt):
        r = MagicMock()
        stmt_str = str(stmt)
        if "vault_characters" in stmt_str:
            r.scalars.return_value.all.return_value = characters or []
        elif "vault_plot_promises" in stmt_str:
            r.scalars.return_value.all.return_value = promises or []
        elif "vault_world" in stmt_str:
            r.scalars.return_value.all.return_value = world or []
        else:
            r.scalars.return_value.all.return_value = []
        return r
    return _execute


# ===========================================================================
# Tests
# ===========================================================================


class TestExtractCardIds:
    """_extract_card_ids 单元测试。"""

    def test_empty_cards(self, service):
        """空卡片列表应返回全部空列表。"""
        result = service._extract_card_ids([])
        assert result == {
            "character_ids": [],
            "promise_ids": [],
            "timeline_points": [],
            "world_rule_ids": [],
        }

    def test_single_card_all_fields(self, service):
        """一张卡片包含所有引用字段。"""
        card = make_card(
            char_refs=[{"id": "c001"}, {"id": "c002"}],
            prom_refs=[{"id": "p001"}],
            timeline_pt="15",
            world_refs=[{"id": "w001"}, {"id": "w002"}],
        )
        result = service._extract_card_ids([card])
        assert sorted(result["character_ids"]) == ["c001", "c002"]
        assert result["promise_ids"] == ["p001"]
        assert result["timeline_points"] == ["15"]
        assert sorted(result["world_rule_ids"]) == ["w001", "w002"]

    def test_multiple_cards_dedup(self, service):
        """多张卡片引用同一 ID 应去重。"""
        c1 = make_card(char_refs=[{"id": "c001"}, {"id": "c002"}])
        c2 = make_card(char_refs=[{"id": "c001"}, {"id": "c003"}])
        result = service._extract_card_ids([c1, c2])
        assert sorted(result["character_ids"]) == ["c001", "c002", "c003"]

    def test_null_fields_ignored(self, service):
        """None / 空列表字段应被安全忽略。"""
        card = make_card()
        result = service._extract_card_ids([card])
        assert result["character_ids"] == []
        assert result["promise_ids"] == []
        assert result["timeline_points"] == []
        assert result["world_rule_ids"] == []

    def test_timeline_point_as_string(self, service):
        """timeline_point 作为字符串处理。"""
        card = make_card(timeline_pt="15")
        result = service._extract_card_ids([card])
        assert result["timeline_points"] == ["15"]


@pytest.mark.asyncio
class TestFetchFilteredCharacters:
    """_fetch_filtered_characters 单元测试。"""

    async def test_empty_ids_returns_empty(self, svc, mock_db):
        """空的 ID 列表应直接返回空列表。"""
        result = await svc._fetch_filtered_characters(mock_db, 1, [])
        assert result == []

    async def test_match_characters(self, svc, mock_db):
        """正确匹配并返回指定 ID 的人物。"""
        char_a = make_char(id="c001", name="林夜")
        char_b = make_char(id="c002", name="苏瑶")
        mock_db.execute.side_effect = mock_execute(
            "characters", characters=[char_a, char_b]
        )

        result = await svc._fetch_filtered_characters(mock_db, 1, ["c001", "c002"])
        assert len(result) == 2
        assert result[0].id == "c001"
        assert result[1].id == "c002"

    async def test_partial_match(self, svc, mock_db):
        """部分 ID 不存在时应只返回存在的。"""
        char_a = make_char(id="c001", name="林夜")
        mock_db.execute.side_effect = mock_execute(
            "characters", characters=[char_a]
        )

        result = await svc._fetch_filtered_characters(
            mock_db, 1, ["c001", "c999"]
        )
        assert len(result) == 1
        assert result[0].id == "c001"


@pytest.mark.asyncio
class TestFetchFilteredTimeline:
    """_fetch_filtered_timeline 单元测试。"""

    async def test_empty_points_returns_empty(self, svc, mock_dao, mock_db):
        """空的 timeline_points 应直接返回空。"""
        result = await svc._fetch_filtered_timeline(mock_db, 1, [])
        assert result == []

    async def test_match_by_chapter_number(self, svc, mock_dao, mock_db):
        """按 chapter_number 匹配并返回 ±3 事件。"""
        events = [make_timeline(id=f"t{i:04d}", chapter_number=i) for i in range(1, 11)]
        mock_dao.get_timeline.return_value = events

        result = await svc._fetch_filtered_timeline(mock_db, 1, ["5"])

        # Chapter 5 is at index 4, ±3 → indices 1-7 → chapters 2-8
        assert len(result) == 7
        chapters = [e.chapter_number for e in result]
        assert chapters == [2, 3, 4, 5, 6, 7, 8]

    async def test_match_by_keyword(self, svc, mock_dao, mock_db):
        """按关键词模糊匹配并返回 ±3 事件。"""
        events = [
            make_timeline(id="t0001", event="宗门被灭", chapter_number=5),
            make_timeline(id="t0002", event="拜师学艺", chapter_number=1),
        ]
        mock_dao.get_timeline.return_value = events

        result = await svc._fetch_filtered_timeline(mock_db, 1, ["宗门"])

        # "宗门" matches t0001 at idx 0, ±3 from idx 0 → [0, 1]
        assert len(result) == 2

    async def test_multi_point_dedup(self, svc, mock_dao, mock_db):
        """多个 timeline_point 应合并去重。"""
        events = [make_timeline(id=f"t{i:04d}", chapter_number=i) for i in range(1, 10)]
        mock_dao.get_timeline.return_value = events

        result = await svc._fetch_filtered_timeline(mock_db, 1, ["4", "5"])

        # Chapter 4 (= idx 3, ±3 → idx 0-6, ch 1-7)
        # Chapter 5 (= idx 4, ±3 → idx 1-7, ch 2-8)
        # Union = ch 1-8
        chapters = sorted(set(e.chapter_number for e in result))
        assert chapters == [1, 2, 3, 4, 5, 6, 7, 8]


@pytest.mark.asyncio
class TestFetchFilteredPromises:
    """_fetch_filtered_promises 单元测试。"""

    async def test_empty_returns_empty(self, svc, mock_db):
        result = await svc._fetch_filtered_promises(mock_db, 1, [])
        assert result == []

    async def test_match_promises(self, svc, mock_db):
        p1 = make_promise(id="p001")
        p2 = make_promise(id="p002")
        mock_db.execute.side_effect = mock_execute(
            "promises", promises=[p1, p2]
        )

        result = await svc._fetch_filtered_promises(mock_db, 1, ["p001", "p002"])
        assert len(result) == 2

    async def test_partial_match(self, svc, mock_db):
        p1 = make_promise(id="p001")
        mock_db.execute.side_effect = mock_execute(
            "promises", promises=[p1]
        )

        result = await svc._fetch_filtered_promises(mock_db, 1, ["p001", "p999"])
        assert len(result) == 1
        assert result[0].id == "p001"


@pytest.mark.asyncio
class TestFetchFilteredWorld:
    """_fetch_filtered_world 单元测试。"""

    async def test_empty_returns_empty(self, svc, mock_db):
        result = await svc._fetch_filtered_world(mock_db, 1, [])
        assert result == []

    async def test_match_world_entries(self, svc, mock_db):
        w1 = make_world(id="w001", name="筑基期")
        w2 = make_world(id="w002", name="金丹期")
        mock_db.execute.side_effect = mock_execute(
            "world", world=[w1, w2]
        )

        result = await svc._fetch_filtered_world(mock_db, 1, ["w001", "w002"])
        assert len(result) == 2


class TestCompression:
    """层级压缩测试。"""

    def test_determine_level_default(self, service):
        """无 chapter_number 时默认返回 Level 1。"""
        assert service._determine_compression_level(None) == 1

    def test_determine_level_below_threshold(self, service):
        """≤30 章应返回 Level 1。"""
        assert service._determine_compression_level(1) == 1
        assert service._determine_compression_level(15) == 1
        assert service._determine_compression_level(30) == 1

    def test_determine_level_above_threshold(self, service):
        """30 章以上应返回 Level 2。"""
        assert service._determine_compression_level(31) == 2
        assert service._determine_compression_level(50) == 2

    def test_compress_level1_full_text(self, service):
        """Level 1 应包含所有字段（有字数限制）。"""
        chars = [make_char(
            description="这是一段很长的描述。" * 50,
        )]
        result = service._compress_characters(chars, 1)
        assert len(result) == 1
        entry = result[0]
        assert "id" in entry
        assert "name" in entry
        assert "description" in entry
        assert "background" in entry
        assert "personality" in entry
        assert "current_state" in entry

    def test_compress_level2_minimal(self, service):
        """Level 2 应只保留 id, name, role, status, current_state。"""
        chars = [make_char()]
        result = service._compress_characters(chars, 2)
        assert len(result) == 1
        entry = result[0]
        assert list(entry.keys()) == ["id", "name", "role", "status", "current_state"]
        assert entry["name"] == "林夜"

    def test_compress_level2_empty_current_state(self, service):
        """Level 2 中 current_state 为空时返回空字符串。"""
        chars = [make_char(current_state=None)]
        result = service._compress_characters(chars, 2)
        assert result[0]["current_state"] == ""

    def test_compress_empty_list(self, service):
        """空人物列表应返回空列表。"""
        assert service._compress_characters([], 1) == []
        assert service._compress_characters([], 2) == []

    def test_truncate_character_fields_long_text(self, service):
        """超过 300 字的人物详情应被截断。"""
        long_desc = "测" * 500
        chars = [make_char(description=long_desc)]
        result = service._compress_characters(chars, 1)
        # 验证 description 被截断了
        assert len(result[0]["description"]) <= 300


class TestTokenEstimate:
    """Token 估算测试。"""

    def test_minimum_one(self, service):
        """即使空内容也应返回至少 1 token。"""
        assert service._estimate_tokens([], [], [], []) == 1

    def test_estimate_with_data(self, service):
        """有内容时应正确估算 token。"""
        chars = [{"name": "林夜", "description": "天剑宗首席弟子。"}]
        events = [make_timeline(event="宗门被灭", description="魔教夜袭")]
        promises = [make_promise(description="复仇之誓")]
        world = [make_world(description="筑基期是修真第二阶")]

        tokens = service._estimate_tokens(chars, events, promises, world)
        assert tokens >= 1


@pytest.mark.asyncio
class TestFilterByCards:
    """filter_by_cards 集成测试。"""

    async def test_full_pipeline_level1(self, svc, mock_dao, mock_db):
        """完整的 Level 1 全流程。"""
        char_a = make_char(id="c001", name="林夜")
        char_b = make_char(id="c002", name="苏瑶")
        events = [make_timeline(id="t0001", chapter_number=5)]
        prom = make_promise(id="p001")
        world_entry = make_world(id="w001")
        card = make_card(
            char_refs=[{"id": "c001"}, {"id": "c002"}],
            prom_refs=[{"id": "p001"}],
            timeline_pt="5",
            world_refs=[{"id": "w001"}],
        )

        mock_dao.get_timeline.return_value = events
        mock_db.execute.side_effect = mock_execute(
            "all",
            characters=[char_a, char_b],
            promises=[prom],
            world=[world_entry],
        )

        result = await svc.filter_by_cards(mock_db, 1, [card], chapter_number=15)

        assert result["compression_level"] == 1
        assert len(result["characters"]) == 2
        assert len(result["timeline"]) == 1
        assert len(result["plot_promises"]) == 1
        assert len(result["world"]) == 1
        assert result["token_estimate"] > 0

    async def test_full_pipeline_level2(self, svc, mock_dao, mock_db):
        """完整的 Level 2 压缩流程。"""
        char_a = make_char(id="c001", name="林夜", current_state="正在突破筑基期")
        events = [make_timeline(id="t0001", chapter_number=5)]
        card = make_card(
            char_refs=[{"id": "c001"}],
            timeline_pt="5",
        )

        mock_dao.get_timeline.return_value = events
        mock_db.execute.side_effect = mock_execute(
            "all",
            characters=[char_a],
            promises=[],
            world=[],
        )

        result = await svc.filter_by_cards(mock_db, 1, [card], chapter_number=45)

        assert result["compression_level"] == 2
        assert len(result["characters"]) == 1
        # Level 2 只保留五个字段
        char_entry = result["characters"][0]
        assert list(char_entry.keys()) == ["id", "name", "role", "status", "current_state"]

    async def test_empty_cards(self, svc, mock_dao, mock_db):
        """空卡片列表应返回空结果。"""
        result = await svc.filter_by_cards(mock_db, 1, [], chapter_number=15)
        assert result["characters"] == []
        assert result["timeline"] == []
        assert result["plot_promises"] == []
        assert result["world"] == []
        assert result["compression_level"] == 1
        assert result["token_estimate"] >= 1

    async def test_no_matching_ids(self, svc, mock_dao, mock_db):
        """卡片引用不存在的 ID 应返回空结果（不崩溃）。"""
        card = make_card(
            char_refs=[{"id": "c999"}],
            timeline_pt="999",
        )
        mock_dao.get_timeline.return_value = []
        mock_db.execute.side_effect = mock_execute(
            "all",
            characters=[],
            promises=[],
            world=[],
        )

        result = await svc.filter_by_cards(mock_db, 1, [card], chapter_number=15)
        assert result["characters"] == []
        assert result["timeline"] == []

    async def test_dao_exception_propagates(self, svc, mock_dao, mock_db):
        """DAO 异常应向上传播。"""
        mock_dao.get_timeline.side_effect = RuntimeError("DB connection lost")
        mock_db.execute.side_effect = mock_execute(
            "all",
            characters=[],
            promises=[],
            world=[],
        )

        card = make_card(timeline_pt="5")
        with pytest.raises(RuntimeError):
            await svc.filter_by_cards(mock_db, 1, [card], chapter_number=1)


class TestSerialization:
    """序列化辅助方法测试。"""

    def test_serialize_character(self, service):
        """人物序列化应包含所有预期字段。"""
        char = make_char()
        result = service._serialize_character(char)
        expected_keys = {
            "id", "name", "role", "faction", "status", "location",
            "appearance", "personality", "knowledge", "confidence",
            "current_state", "motivation", "emotion", "traits",
            "description", "background", "relationships", "state_machine",
        }
        assert set(result.keys()) == expected_keys
        assert result["name"] == "林夜"

    def test_serialize_timeline_event(self, service):
        """时间线序列化应包含所有预期字段。"""
        event = make_timeline()
        result = service._serialize_timeline_event(event)
        assert result["event"] == "宗门被灭"
        assert result["chapter_number"] == 5
        assert "description" in result
        assert "importance" in result

    def test_serialize_promise(self, service):
        """剧情承诺序列化应包含所有预期字段。"""
        promise = make_promise()
        result = service._serialize_promise(promise)
        assert result["type"] == "promise"
        assert result["status"] == "active"

    def test_serialize_world(self, service):
        """世界观条目序列化应包含所有预期字段。"""
        entry = make_world()
        result = service._serialize_world_entry(entry)
        assert result["name"] == "筑基期"
        assert result["category"] == "rule"


class TestSafeGetId:
    """_safe_get_id 工具方法测试。"""

    def test_dict_with_id(self, service):
        assert service._safe_get_id({"id": "abc123"}) == "abc123"

    def test_dict_without_id(self, service):
        assert service._safe_get_id({"name": "test"}) is None

    def test_dict_none_id(self, service):
        assert service._safe_get_id({"id": None}) is None

    def test_none_input(self, service):
        assert service._safe_get_id(None) is None

    def test_simple_namespace_with_id(self, service):
        obj = SimpleNamespace(id="obj_id")
        assert service._safe_get_id(obj) == "obj_id"

    def test_object_without_id(self, service):
        obj = SimpleNamespace()
        result = service._safe_get_id(obj)
        assert result is None
