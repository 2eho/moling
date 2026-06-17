"""墨灵 (Moling) — Phase 4 Service 单元测试.

Tests for the Phase 4 core service methods (§11.4-§11.7):
- LLM extraction prompt building and parsing
- Four database merge operations
- Card pool enrichment
- Changelog archiving
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.phase4_service import (
    Phase4Service,
    EXTRACTION_SCHEMA,
    CHARACTER_FUZZY_THRESHOLD,
    CARD_FRESHNESS_WINDOW,
)


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def phase4_service() -> Phase4Service:
    """Create Phase4Service instance."""
    return Phase4Service()


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock database session (add is sync, flush/commit/refresh/execute are async)."""
    return _make_mock_db()


def _make_mock_db() -> MagicMock:
    """Create a mock db: MagicMock for sync methods (add), AsyncMock for async ones."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()  # avoid coroutine from .scalars()/.all()
    db.get = AsyncMock()
    return db


@pytest.fixture
def sample_chapter_text() -> str:
    """Sample chapter text for testing."""
    return """
    第一章 重逢
    
    林峰站在城门前，望着熟悉的城墙，心中百感交集。
    "我终于回来了。"他低声说道。
    
    城门口的守卫拦住了他："站住！身份凭证呢？"
    林峰从怀中掏出一块令牌，上面刻着一朵金色的莲花。
    守卫看到令牌，脸色大变，恭敬地让开了路。
    
    走进城中，林峰发现一切都变了。街道上行人稀少，
    到处弥漫着一股诡异的气氛。他皱了皱眉，加快了脚步。
    
    在一家茶馆前，他看到了一个熟悉的身影——苏暮雪。
    她依然穿着那件淡蓝色的长裙，只是眉宇间多了一丝忧愁。
    
    "暮雪。"林峰轻声唤道。
    苏暮雪转过头，眼中闪过惊喜："林峰！你终于回来了！"
    
    两人相对而坐，苏暮雪讲述了这些年发生的事。
    自从林峰离开后，青云宗被一股神秘势力渗透，
    长老会中出现了内鬼，宗主下落不明。
    
    林峰握紧拳头："是谁干的？"
    苏暮雪摇头："不清楚，但我们怀疑与'幽冥教'有关。"
    
    "幽冥教..."林峰喃喃道，"那个被封印百年的邪教？"
    苏暮雪点头："封印正在松动，我们需要你的力量。"
    """


@pytest.fixture
def sample_extraction_json() -> str:
    """Sample LLM response JSON."""
    return json.dumps(
        {
            "character_updates": [
                {
                    "action": "create",
                    "name": "林峰",
                    "changes": [
                        {"role": "protagonist"},
                        {"description": "归来的强者，青云宗弟子"},
                        {"personality": "坚毅、冷静"},
                        {"current_state": "刚刚返回城镇"},
                    ],
                    "confidence": 0.95,
                },
                {
                    "action": "update",
                    "name": "苏暮雪",
                    "changes": [
                        {"emotion": "忧愁"},
                        {"current_state": "在茶馆与林峰重逢"},
                    ],
                    "confidence": 0.9,
                },
            ],
            "timeline_updates": [
                {
                    "action": "add",
                    "event": "林峰返回城镇",
                    "day": 1,
                    "chapter": 1,
                    "participants": ["林峰"],
                    "importance": "major",
                },
                {
                    "action": "add",
                    "event": "林峰与苏暮雪在茶馆重逢",
                    "day": 1,
                    "chapter": 1,
                    "participants": ["林峰", "苏暮雪"],
                    "importance": "major",
                },
            ],
            "plot_promise_updates": [
                {
                    "action": "create",
                    "title": "幽冥教封印松动",
                    "type": "剧情转折",
                    "status": "active",
                },
                {
                    "action": "create",
                    "title": "青云宗内鬼之谜",
                    "type": "悬念",
                    "status": "active",
                },
            ],
            "world_updates": [
                {
                    "action": "create",
                    "name": "幽冥教",
                    "category": "faction",
                    "content": "被封印百年的邪教，正在试图重新崛起",
                },
                {
                    "action": "create",
                    "name": "青云宗",
                    "category": "faction",
                    "content": "林峰所属的宗门，现在被神秘势力渗透",
                },
            ],
            "card_pool_entries": [
                {
                    "type": "剧情",
                    "title": "幽冥教的阴谋",
                    "description": "探索幽冥教重新崛起背后的真相",
                    "rarity": "epic",
                    "source_chapter": 1,
                },
                {
                    "type": "人物",
                    "title": "林峰的过去",
                    "description": "探索林峰离开这些年的经历",
                    "rarity": "rare",
                    "source_chapter": 1,
                },
            ],
        },
        ensure_ascii=False,
    )


# ====================================================================
# Tests: Edit Distance
# ====================================================================


class TestEditDistance:
    """Test the edit distance calculation used for character fuzzy matching."""

    def test_exact_match(self, phase4_service: Phase4Service):
        assert phase4_service._calc_edit_distance("林峰", "林峰") == 0

    def test_one_char_difference(self, phase4_service: Phase4Service):
        assert phase4_service._calc_edit_distance("林峰", "林峰峰") == 1

    def test_completely_different(self, phase4_service: Phase4Service):
        assert phase4_service._calc_edit_distance("林峰", "苏暮雪") == 3

    def test_empty_string(self, phase4_service: Phase4Service):
        assert phase4_service._calc_edit_distance("", "林峰") == 2
        assert phase4_service._calc_edit_distance("林峰", "") == 2

    def test_threshold_behavior(self, phase4_service: Phase4Service):
        # 编辑距离 < 3 应该被视为可能的匹配
        assert phase4_service._calc_edit_distance("林峰", "林丰") < CHARACTER_FUZZY_THRESHOLD
        # 编辑距离 >= 3 应该被视为不同
        assert phase4_service._calc_edit_distance("林峰", "苏暮雪") >= CHARACTER_FUZZY_THRESHOLD


# ====================================================================
# Tests: Extraction Prompt Building
# ====================================================================


@pytest.mark.asyncio
async def test_build_extraction_prompt(
    phase4_service: Phase4Service, mock_db: AsyncMock, sample_chapter_text: str
):
    """测试构建 extraction prompt 包含所有必要部分。"""
    prompt = await phase4_service._build_extraction_prompt(
        mock_db, 1, sample_chapter_text, ["card_1", "card_2"]
    )

    # 包含章节正文
    assert sample_chapter_text in prompt
    # 包含灵感卡 ID
    assert "card_1" in prompt
    assert "card_2" in prompt
    # 包含 JSON schema 说明
    assert "character_updates" in prompt
    assert "timeline_updates" in prompt
    assert "plot_promise_updates" in prompt
    assert "world_updates" in prompt
    assert "card_pool_entries" in prompt
    # 包含注意事项
    assert "编辑距离" in prompt or "枚举值" in prompt


@pytest.mark.asyncio
async def test_get_vault_summary_async(
    phase4_service: Phase4Service,
):
    """测试获取四库摘要。"""
    mock_db = _make_mock_db()

    # Mock vault_dao methods
    from app.models.vault_character import VaultCharacter
    from app.models.vault_timeline import VaultTimeline

    mock_char = MagicMock(spec=VaultCharacter)
    mock_char.id = "char-uuid-1"
    mock_char.name = "林峰"

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_char])
        mock_vault_dao.get_timeline = AsyncMock(return_value=[])
        mock_vault_dao.get_plot_promises = AsyncMock(return_value=[])
        mock_vault_dao.get_world_entries = AsyncMock(return_value=[])

        summary = await phase4_service._get_vault_summary_async(mock_db, 1)

        # 包含人物库信息
        assert "人物库" in summary
        assert "林峰" in summary
        # 时间线应为空
        assert "时间线库" in summary


# ====================================================================
# Tests: LLM Response Parsing
# ====================================================================


class TestParseExtractionResult:
    """Test parsing LLM response JSON."""

    def test_valid_json(self, phase4_service: Phase4Service, sample_extraction_json: str):
        """测试正常 JSON 解析。"""
        result = phase4_service._parse_extraction_result(sample_extraction_json)
        assert len(result["character_updates"]) == 2
        assert len(result["timeline_updates"]) == 2
        assert len(result["plot_promise_updates"]) == 2
        assert len(result["world_updates"]) == 2
        assert len(result["card_pool_entries"]) == 2

    def test_empty_response(self, phase4_service: Phase4Service):
        """测试空响应。"""
        result = phase4_service._parse_extraction_result("")
        assert all(len(v) == 0 for v in result.values())

    def test_non_json_response(self, phase4_service: Phase4Service):
        """测试非 JSON 响应。"""
        result = phase4_service._parse_extraction_result("这是纯文本，不是JSON")
        assert all(len(v) == 0 for v in result.values())

    def test_markdown_wrapped_json(self, phase4_service: Phase4Service):
        """测试被 markdown 包装的 JSON。"""
        simple_json = (
            '{"character_updates": ['
            '{"action": "create", "name": "林峰", "changes": [], "confidence": 0.95},'
            '{"action": "update", "name": "苏暮雪", "changes": [], "confidence": 0.9}'
            "]}"
        )
        wrapped = f"```json\n{simple_json}\n```"
        result = phase4_service._parse_extraction_result(wrapped)
        assert len(result["character_updates"]) == 2

    def test_partial_result(self, phase4_service: Phase4Service):
        """测试只有部分字段的 JSON。"""
        partial = json.dumps({"character_updates": [{"action": "create", "name": "林峰"}]})
        result = phase4_service._parse_extraction_result(partial)
        assert len(result["character_updates"]) == 1
        assert len(result["timeline_updates"]) == 0

    def test_invalid_items_filtered(self, phase4_service: Phase4Service):
        """测试非 dict 条目被过滤。"""
        bad_data = json.dumps(
            {
                "character_updates": [
                    {"action": "create", "name": "林峰"},
                    "not a dict",
                    None,
                ]
            }
        )
        result = phase4_service._parse_extraction_result(bad_data)
        assert len(result["character_updates"]) == 1


# ====================================================================
# Tests: Character Merging (§11.7 [15])
# ====================================================================


@pytest.mark.asyncio
async def test_merge_characters_create(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试创建新角色。"""
    from app.models.vault_character import VaultCharacter

    mock_char = MagicMock(spec=VaultCharacter)
    mock_char.id = "new-uuid"
    mock_char.name = "林峰"
    mock_char.chapter_count = 0

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[])
        mock_vault_dao.create_character = AsyncMock(return_value=mock_char)

        updates = [
            {
                "action": "create",
                "name": "林峰",
                "changes": [{"role": "protagonist"}],
                "confidence": 0.95,
            }
        ]
        result = await phase4_service._merge_characters(
            mock_db, 1, updates, chapter_number=1
        )

        assert len(result["created"]) == 1
        assert result["created"][0]["name"] == "林峰"
        assert len(result["updated"]) == 0

        # 验证 create_character 被调用
        mock_vault_dao.create_character.assert_called_once()


@pytest.mark.asyncio
async def test_merge_characters_fuzzy_match(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试角色模糊匹配（编辑距离 < 3）。"""
    from app.models.vault_character import VaultCharacter

    mock_existing = MagicMock(spec=VaultCharacter)
    mock_existing.id = "existing-uuid"
    mock_existing.name = "林峰"
    mock_existing.chapter_count = 1

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_existing])
        mock_vault_dao.update_character = AsyncMock(return_value=mock_existing)

        updates = [
            {
                "action": "create",
                "name": "林丰",  # 编辑距离 1，应匹配到"林峰"
                "changes": [{"role": "protagonist"}],
                "confidence": 0.9,
            }
        ]
        result = await phase4_service._merge_characters(
            mock_db, 1, updates, chapter_number=2
        )

        assert len(result["updated"]) == 1  # 模糊匹配成功 → update
        assert len(result["created"]) == 0  # 不是新创建
        mock_vault_dao.create_character.assert_not_called()
        mock_vault_dao.update_character.assert_called_once()


@pytest.mark.asyncio
async def test_merge_characters_update(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试更新已有角色。"""
    from app.models.vault_character import VaultCharacter

    mock_existing = MagicMock(spec=VaultCharacter)
    mock_existing.id = "existing-uuid"
    mock_existing.name = "苏暮雪"
    mock_existing.chapter_count = 2

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_existing])
        mock_vault_dao.update_character = AsyncMock(return_value=mock_existing)

        updates = [
            {
                "action": "update",
                "name": "苏暮雪",
                "changes": [{"emotion": "忧愁"}],
                "confidence": 0.9,
            }
        ]
        result = await phase4_service._merge_characters(
            mock_db, 1, updates, chapter_number=3
        )

        assert len(result["updated"]) == 1
        assert result["updated"][0]["name"] == "苏暮雪"


@pytest.mark.asyncio
async def test_merge_characters_status_change(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试角色状态变更和 state_machine 记录。"""
    from app.models.vault_character import VaultCharacter

    mock_existing = MagicMock(spec=VaultCharacter)
    mock_existing.id = "existing-uuid"
    mock_existing.name = "反派"
    mock_existing.status = "active"
    mock_existing.state_machine = None

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_existing])
        mock_vault_dao.update_character = AsyncMock(return_value=mock_existing)

        updates = [
            {
                "action": "status_change",
                "name": "反派",
                "changes": [{"status": "deceased"}],
                "confidence": 0.98,
            }
        ]
        result = await phase4_service._merge_characters(
            mock_db, 1, updates, chapter_number=5
        )

        assert len(result["status_changed"]) == 1
        assert result["status_changed"][0]["from"] == "active"
        assert result["status_changed"][0]["to"] == "deceased"

        # 验证 state_machine 被更新
        call_args = mock_vault_dao.update_character.call_args[0]
        obj_in = call_args[2]  # 第三个位置参数是 obj_in
        assert "state_machine" in obj_in


@pytest.mark.asyncio
async def test_merge_characters_remove(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试角色退场标记。"""
    from app.models.vault_character import VaultCharacter

    mock_existing = MagicMock(spec=VaultCharacter)
    mock_existing.id = "existing-uuid"
    mock_existing.name = "配角"
    mock_existing.status = "active"

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_existing])
        mock_vault_dao.update_character = AsyncMock(return_value=mock_existing)

        updates = [
            {
                "action": "remove",
                "name": "配角",
                "changes": [],
                "confidence": 0.95,
            }
        ]
        result = await phase4_service._merge_characters(
            mock_db, 1, updates, chapter_number=6
        )

        assert len(result["status_changed"]) == 1
        assert result["status_changed"][0]["to"] == "deceased"

        call_args = mock_vault_dao.update_character.call_args[0]
        assert call_args[2]["status"] == "deceased"


# ====================================================================
# Tests: Timeline Merging (§11.7 [16])
# ====================================================================


@pytest.mark.asyncio
async def test_merge_timeline_add(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试新增时间线事件。"""
    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_timeline = AsyncMock(return_value=[])
        mock_vault_dao.create_timeline_event = AsyncMock()

        updates = [
            {
                "action": "add",
                "event": "林峰返回城镇",
                "day": 1,
                "chapter": 1,
                "participants": ["林峰"],
                "importance": "major",
            }
        ]
        result = await phase4_service._merge_timeline(
            mock_db, 1, updates, chapter_id=1, chapter_number=1
        )

        assert result["added"] == 1
        mock_vault_dao.create_timeline_event.assert_called_once()


@pytest.mark.asyncio
async def test_merge_timeline_resolve_date(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试绑定时间线日期。"""
    from app.models.vault_timeline import VaultTimeline

    mock_event = MagicMock(spec=VaultTimeline)
    mock_event.id = "event-uuid"
    mock_event.event = "林峰返回城镇"

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_timeline = AsyncMock(return_value=[mock_event])
        mock_vault_dao.update_timeline_event = AsyncMock()

        updates = [
            {
                "action": "resolve_date",
                "event": "林峰返回城镇",
                "day": 3,
                "chapter": 1,
            }
        ]
        result = await phase4_service._merge_timeline(
            mock_db, 1, updates, chapter_id=1, chapter_number=1
        )

        assert result["added"] == 0  # 不是 add，不计数
        mock_vault_dao.update_timeline_event.assert_called_once()


# ====================================================================
# Tests: Plot Promise Merging (§11.7 [17])
# ====================================================================


@pytest.mark.asyncio
async def test_merge_plot_promises_create(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试创建新剧情承诺。"""
    for action in ("create", "advance", "redeem", "cancel"):
        mock_db.reset_mock()

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_plot_promises = AsyncMock(return_value=[])
        mock_vault_dao.create_plot_promise = AsyncMock()

        updates = [
            {
                "action": "create",
                "title": "幽冥教封印松动",
                "type": "剧情转折",
                "status": "active",
            }
        ]
        result = await phase4_service._merge_plot_promises(
            mock_db, 1, updates, chapter_number=1
        )

        assert result["created"] == 1
        mock_vault_dao.create_plot_promise.assert_called_once()

        # 验证 advancement_log 被初始化
        call_args = mock_vault_dao.create_plot_promise.call_args[0]
        obj_in = call_args[1]  # 第二个位置参数是 obj_in
        assert "advancement_log" in obj_in
        assert len(obj_in["advancement_log"]) == 1


@pytest.mark.asyncio
async def test_merge_plot_promises_advance(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试推进剧情承诺。"""
    from app.models.vault_plot_promise import VaultPlotPromise

    mock_promise = MagicMock(spec=VaultPlotPromise)
    mock_promise.id = "promise-uuid"
    mock_promise.title = "幽冥教封印松动"
    mock_promise.description = "幽冥教封印松动"
    mock_promise.status = "active"
    mock_promise.urgency = 5
    mock_promise.advancement_log = [{"chapter": 1, "event": "created"}]

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_plot_promises = AsyncMock(return_value=[mock_promise])
        mock_vault_dao.update_plot_promise = AsyncMock()

        updates = [
            {
                "action": "advance",
                "title": "幽冥教封印松动",
                "type": "剧情转折",
                "status": "advancing",
            }
        ]
        result = await phase4_service._merge_plot_promises(
            mock_db, 1, updates, chapter_number=2
        )

        assert result["advanced"] == 1
        mock_vault_dao.update_plot_promise.assert_called_once()

        # 验证 status 被更新为 advancing
        call_args = mock_vault_dao.update_plot_promise.call_args[0]
        assert call_args[2]["status"] == "advancing"


@pytest.mark.asyncio
async def test_merge_plot_promises_redeem(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试回收剧情承诺。"""
    from app.models.vault_plot_promise import VaultPlotPromise

    mock_promise = MagicMock(spec=VaultPlotPromise)
    mock_promise.id = "promise-uuid"
    mock_promise.title = "青云宗内鬼之谜"
    mock_promise.description = "青云宗内鬼之谜"
    mock_promise.status = "advancing"
    mock_promise.urgency = 7
    mock_promise.advancement_log = []

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_plot_promises = AsyncMock(return_value=[mock_promise])
        mock_vault_dao.update_plot_promise = AsyncMock()

        updates = [
            {
                "action": "redeem",
                "title": "青云宗内鬼之谜",
                "type": "悬念",
                "status": "resolved",
            }
        ]
        result = await phase4_service._merge_plot_promises(
            mock_db, 1, updates, chapter_number=10
        )

        assert result["redeemed"] == 1
        call_args = mock_vault_dao.update_plot_promise.call_args[0]
        assert call_args[2]["status"] == "resolved"


# ====================================================================
# Tests: Promise Type Mapping
# ====================================================================


class TestMapPromiseType:
    """Test promise type Chinese-to-English mapping."""

    def test_maps_all_types(self, phase4_service: Phase4Service):
        assert phase4_service._map_promise_type("人物弧光") == "arc"
        assert phase4_service._map_promise_type("剧情转折") == "subplot"
        assert phase4_service._map_promise_type("悬念") == "mystery"
        assert phase4_service._map_promise_type("关系发展") == "promise"
        assert phase4_service._map_promise_type("世界观秘密") == "foreshadowing"

    def test_unknown_type_defaults(self, phase4_service: Phase4Service):
        assert phase4_service._map_promise_type("未知类型") == "mystery"


# ====================================================================
# Tests: World Merging (§11.7 [18])
# ====================================================================


@pytest.mark.asyncio
async def test_merge_world_create(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试创建世界观条目。"""
    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_world_entries = AsyncMock(return_value=[])
        mock_vault_dao.create_world_entry = AsyncMock()

        updates = [
            {
                "action": "create",
                "name": "幽冥教",
                "category": "faction",
                "content": "被封印百年的邪教",
            }
        ]
        result = await phase4_service._merge_world(
            mock_db, 1, updates, chapter_number=1
        )

        assert result["created"] == 1
        mock_vault_dao.create_world_entry.assert_called_once()


@pytest.mark.asyncio
async def test_merge_world_expand(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试扩展世界观条目。"""
    from app.models.vault_world import VaultWorld

    mock_entry = MagicMock(spec=VaultWorld)
    mock_entry.id = "world-uuid"
    mock_entry.name = "幽冥教"
    mock_entry.description = "初始描述"
    mock_entry.reference_chapters = [1]
    mock_entry.related_entities = []

    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao:
        mock_vault_dao.get_world_entries = AsyncMock(return_value=[mock_entry])
        mock_vault_dao.update_world_entry = AsyncMock()

        updates = [
            {
                "action": "expand",
                "name": "幽冥教",
                "category": "faction",
                "content": "幽冥教的教主据说拥有不死之身",
            }
        ]
        result = await phase4_service._merge_world(
            mock_db, 1, updates, chapter_number=3
        )

        assert result["expanded"] == 1
        mock_vault_dao.update_world_entry.assert_called_once()

        # 验证 description 被追加
        call_args = mock_vault_dao.update_world_entry.call_args[0]
        obj_in = call_args[2]  # 第三个位置参数是 obj_in
        assert "初始描述" in obj_in["description"]
        assert "幽冥教的教主" in obj_in["description"]


# ====================================================================
# Tests: Card Pool Enrichment (§11.7 [19])
# ====================================================================


@pytest.mark.asyncio
async def test_enrich_card_pool(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试卡牌池充实。"""
    with patch("app.service.phase4_service.card_dao") as mock_card_dao:
        mock_card_dao.get_active_cards = AsyncMock(return_value=[])

        entries = [
            {
                "type": "剧情",
                "title": "幽冥教的阴谋",
                "description": "探索幽冥教重新崛起背后的真相",
                "rarity": "epic",
                "source_chapter": 1,
            },
            {
                "type": "人物",
                "title": "林峰的过去",
                "description": "探索林峰离开这些年的经历",
                "rarity": "rare",
                "source_chapter": 1,
            },
        ]
        result = await phase4_service._enrich_card_pool(
            mock_db, 1, entries, chapter_number=1
        )

        assert result["added"] == 2


@pytest.mark.asyncio
async def test_enrich_card_pool_duplicate_title(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试重复标题不被添加。"""
    from app.models.card_pool import CardPool

    mock_card = MagicMock(spec=CardPool)
    mock_card.name = "幽冥教的阴谋"

    with patch("app.service.phase4_service.card_dao") as mock_card_dao:
        mock_card_dao.get_active_cards = AsyncMock(return_value=[mock_card])

        entries = [
            {
                "type": "剧情",
                "title": "幽冥教的阴谋",  # 已存在
                "description": "重复的卡牌",
                "rarity": "common",
                "source_chapter": 2,
            }
        ]
        result = await phase4_service._enrich_card_pool(
            mock_db, 1, entries, chapter_number=2
        )

        assert result["added"] == 0  # 重复标题不被添加


# ====================================================================
# Tests: Changelog Archiving (§11.7 [20])
# ====================================================================


@pytest.mark.asyncio
async def test_archive_changelog(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试变更日志归档。"""
    changes = {
        "characters": {
            "created": [{"id": "char-1", "name": "林峰"}],
            "updated": [{"id": "char-2", "name": "苏暮雪", "changes": ["情绪变更"]}],
            "status_changed": [
                {
                    "id": "char-3",
                    "name": "反派",
                    "from": "active",
                    "to": "deceased",
                }
            ],
        },
        "timeline": {"added": 2},
        "plot_promises": {"created": 1, "advanced": 1, "redeemed": 0},
        "world": {"created": 1, "expanded": 0},
        "card_pool": {"added": 2},
    }

    await phase4_service._archive_changelog(
        mock_db,
        project_id=1,
        chapter_id=1,
        version="v4_ch1_1712345678",
        chapter_number=1,
        changes=changes,
    )

    # 验证 db.add 被调用了足够次数
    # 3 (角色) + 1 (时间线) + 2 (剧情承诺) + 1 (世界观) + 1 (卡牌) = 8
    assert mock_db.add.call_count >= 8


# ====================================================================
# Tests: Run Phase 4 (End-to-End)
# ====================================================================


@pytest.mark.asyncio
async def test_run_phase4_success(
    phase4_service: Phase4Service, mock_db: AsyncMock, sample_extraction_json: str
):
    """测试完整的 Phase 4 流程。"""
    from app.models.chapter import Chapter

    mock_chapter = MagicMock(spec=Chapter)
    mock_chapter.id = "chapter-uuid"
    mock_chapter.chapter_number = 1

    mock_db.get = AsyncMock(return_value=mock_chapter)

    # Mock vault_dao 方法 - 让 "苏暮雪" 作为已有角色存在
    with patch("app.service.phase4_service.vault_dao") as mock_vault_dao, \
         patch("app.service.phase4_service.card_dao") as mock_card_dao, \
         patch("app.service.phase4_service.chapter_dao") as mock_chapter_dao, \
         patch.object(phase4_service, "_call_extraction_llm") as mock_llm:

        from app.models.vault_character import VaultCharacter
        mock_existing_char = MagicMock(spec=VaultCharacter)
        mock_existing_char.id = "char-su"
        mock_existing_char.name = "苏暮雪"
        mock_existing_char.chapter_count = 2

        mock_chapter_dao.get = AsyncMock(return_value=mock_chapter)
        mock_vault_dao.get_characters = AsyncMock(return_value=[mock_existing_char])
        mock_vault_dao.get_timeline = AsyncMock(return_value=[])
        mock_vault_dao.get_plot_promises = AsyncMock(return_value=[])
        mock_vault_dao.get_world_entries = AsyncMock(return_value=[])
        mock_vault_dao.create_character = AsyncMock()
        mock_vault_dao.update_character = AsyncMock()
        mock_vault_dao.create_timeline_event = AsyncMock()
        mock_vault_dao.create_plot_promise = AsyncMock()
        mock_vault_dao.create_world_entry = AsyncMock()
        mock_card_dao.get_active_cards = AsyncMock(return_value=[])

        mock_llm.return_value = sample_extraction_json

        result = await phase4_service.run_phase4(
            mock_db,
            project_id=1,
            chapter_id=1,
            chapter_text="测试章节正文",
            card_ids=["card-1", "card-2"],
        )

        # 验证返回格式
        assert "version" in result
        assert result["version"].startswith("v4_ch1_")
        assert result["chapter"] == 1
        assert "changes" in result
        assert "characters" in result["changes"]
        assert "timeline" in result["changes"]
        assert "plot_promises" in result["changes"]
        assert "world" in result["changes"]
        assert "card_pool" in result["changes"]
        assert "summary" in result

        # 验证变更数量
        assert len(result["changes"]["characters"]["created"]) == 1
        assert len(result["changes"]["characters"]["updated"]) == 1
        assert result["changes"]["timeline"]["added"] == 2
        assert result["changes"]["plot_promises"]["created"] == 2
        assert result["changes"]["world"]["created"] == 2
        assert result["changes"]["card_pool"]["added"] == 2


@pytest.mark.asyncio
async def test_run_phase4_llm_failure_graceful_degradation(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试 LLM 调用失败时的优雅降级。"""
    from app.models.chapter import Chapter

    mock_chapter = MagicMock(spec=Chapter)
    mock_chapter.id = "chapter-uuid"
    mock_chapter.chapter_number = 1

    mock_db.get = AsyncMock(return_value=mock_chapter)

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm, \
         patch("app.service.phase4_service.chapter_dao") as mock_chapter_dao:

        mock_chapter_dao.get = AsyncMock(return_value=mock_chapter)
        # LLM 调用返回空的 JSON 降级结果
        mock_llm.return_value = json.dumps(phase4_service._empty_extraction_result())

        result = await phase4_service.run_phase4(
            mock_db,
            project_id=1,
            chapter_id=1,
            chapter_text="测试章节正文",
            card_ids=[],
        )

        # 即使 LLM 返回空，仍然应该得到有效的返回格式
        assert "version" in result
        assert result["changes"]["card_pool"]["added"] == 0


@pytest.mark.asyncio
async def test_run_phase4_corrupted_llm_response(
    phase4_service: Phase4Service, mock_db: AsyncMock
):
    """测试 LLM 返回损坏数据时的容错。"""
    from app.models.chapter import Chapter

    mock_chapter = MagicMock(spec=Chapter)
    mock_chapter.id = "chapter-uuid"
    mock_chapter.chapter_number = 1
    mock_db.get = AsyncMock(return_value=mock_chapter)

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm, \
         patch("app.service.phase4_service.chapter_dao") as mock_chapter_dao:

        mock_chapter_dao.get = AsyncMock(return_value=mock_chapter)
        # 损坏的 JSON
        mock_llm.return_value = "这不是有效的JSON{{{"

        result = await phase4_service.run_phase4(
            mock_db,
            project_id=1,
            chapter_id=1,
            chapter_text="test",
            card_ids=[],
        )

        # 解析失败应该返回空结果，不抛异常
        assert "version" in result


# ====================================================================
# Tests: Empty Extraction Result
# ====================================================================


class TestEmptyExtractionResult:
    """Test empty extraction result helper."""

    def test_returns_empty_dicts(self, phase4_service: Phase4Service):
        result = phase4_service._empty_extraction_result()
        for key in (
            "character_updates",
            "timeline_updates",
            "plot_promise_updates",
            "world_updates",
            "card_pool_entries",
        ):
            assert key in result
            assert result[key] == []
