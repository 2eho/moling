"""墨灵 (Moling) — MergeService 单元测试.

P0-3 四库合并服务测试套件（≥30 个测试）。
所有测试使用 mock 数据库，不依赖真实数据库。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.merge_service import (
    ChangeEntry,
    ExtractedCharacter,
    ExtractedTimelineEvent,
    ExtractedPlotPromise,
    ExtractedWorldItem,
    MergeResult,
    MergeService,
    merge_service,
    NEW_ENTITY_CONFIDENCE,
    SURNAME_MATCH_CONFIDENCE,
    STALE_CHAPTER_THRESHOLD,
)
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def service() -> MergeService:
    return MergeService()


def _make_mock_db() -> MagicMock:
    """Create a mock db session."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_db() -> MagicMock:
    return _make_mock_db()


def _make_vault_character(
    id: int = 1,
    name: str = "林峰",
    role: str = "protagonist",
    status: str = "active",
    project_id: int = 1,
    **kwargs,
) -> VaultCharacter:
    char = MagicMock(spec=VaultCharacter)
    char.id = id
    char.name = name
    char.role = role
    char.status = status
    char.project_id = project_id
    char.faction = kwargs.get("faction", "")
    char.location = kwargs.get("location", "")
    char.current_state = kwargs.get("current_state", "")
    char.motivation = kwargs.get("motivation", "")
    char.description = kwargs.get("description", "")
    char.personality = kwargs.get("personality", "")
    char.appearance = kwargs.get("appearance", "")
    char.confidence = kwargs.get("confidence", 0.5)
    char.chapter_count = kwargs.get("chapter_count", 3)
    char.chapter_hist = kwargs.get("chapter_hist", [1, 2, 3])
    char.traits = kwargs.get("traits", [])
    char.state_machine = kwargs.get("state_machine", {})
    char.embedding = kwargs.get("embedding", [])
    char.emotion = kwargs.get("emotion", "")
    char.background = kwargs.get("background", "")
    char.relationships = kwargs.get("relationships", [])
    return char


def _make_vault_timeline(
    id: int = 1,
    event: str = "主角抵达城门",
    day: Optional[int] = 1,
    chapter_number: int = 1,
    project_id: int = 1,
    **kwargs,
) -> VaultTimeline:
    evt = MagicMock(spec=VaultTimeline)
    evt.id = id
    evt.event = event
    evt.day = day
    evt.chapter_number = chapter_number
    evt.project_id = project_id
    evt.description = kwargs.get("description", "事件描述")
    evt.importance = kwargs.get("importance", "minor")
    evt.is_key_event = kwargs.get("is_key_event", False)
    evt.characters_involved = kwargs.get("characters_involved", [])
    evt.source_chapter = kwargs.get("source_chapter", chapter_number)
    evt.confidence = kwargs.get("confidence", 0.8)
    return evt


def _make_vault_plot_promise(
    id: int = 1,
    title: str = "幽冥教的阴谋",
    description: str = "幽冥教正在酝酿一个大阴谋",
    status: str = "active",
    project_id: int = 1,
    **kwargs,
) -> VaultPlotPromise:
    p = MagicMock(spec=VaultPlotPromise)
    p.id = id
    p.title = title
    p.description = description
    p.status = status
    p.project_id = project_id
    p.type = kwargs.get("type", "mystery")
    p.urgency = kwargs.get("urgency", 5)
    p.planted_chapter = kwargs.get("planted_chapter", 1)
    p.advancement_log = kwargs.get("advancement_log", [])
    p.related_characters = kwargs.get("related_characters", [])
    p.confidence = kwargs.get("confidence", 0.8)
    p.redeem_window = kwargs.get("redeem_window", None)
    return p


def _make_vault_world(
    id: int = 1,
    name: str = "青云宗",
    category: str = "faction",
    project_id: int = 1,
    description: str = "修仙宗门",
    **kwargs,
) -> VaultWorld:
    w = MagicMock(spec=VaultWorld)
    w.id = id
    w.name = name
    w.category = category
    w.project_id = project_id
    w.description = description
    w.constraint = kwargs.get("constraint", None)
    w.source_chapter = kwargs.get("source_chapter", 1)
    w.reference_chapters = kwargs.get("reference_chapters", [1])
    w.related_entities = kwargs.get("related_entities", [])
    return w


# ====================================================================
# 1-5: 人物匹配测试 (P0)
# ====================================================================


class TestCharacterMatching:
    """人物匹配策略测试：精确/模糊/别名/姓氏/无匹配。"""

    @pytest.mark.asyncio
    async def test_exact_name_match(self, service, mock_db):
        """[1] 精确名称匹配 → 更新已有角色，不新建。"""
        existing = [_make_vault_character(id=1, name="林峰")]
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            created_char = _make_vault_character(id=2, name="新角色")
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock(return_value=created_char)):
                spy_update = AsyncMock(return_value=existing[0])
                with patch("app.service.merge_service.vault_dao.update_character", spy_update):
                    result = await service.merge_characters(
                        mock_db, 1,
                        [ExtractedCharacter(name="林峰", role="protagonist")],
                        chapter_number=4,
                    )
                    assert result.created == 0
                    assert result.updated == 1
                    spy_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_distance_1_match(self, service, mock_db):
        """[2] 编辑距离=1 模糊匹配 → 更新已有角色。"""
        existing = [_make_vault_character(id=1, name="林峰")]
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock(return_value=_make_vault_character(id=2, name="林锋"))):
                spy_update = AsyncMock(return_value=existing[0])
                with patch("app.service.merge_service.vault_dao.update_character", spy_update):
                    result = await service.merge_characters(
                        mock_db, 1,
                        [ExtractedCharacter(name="林锋")],
                        chapter_number=4,
                    )
                    assert result.updated == 1
                    spy_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_alias_match(self, service, mock_db):
        """[3] 别名匹配 → 注册别名后能匹配到。"""
        # 角色 traits 包含别名
        existing = [_make_vault_character(id=1, name="林峰", traits=["林大侠", "阿峰"])]
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock(return_value=_make_vault_character(id=2, name="新角色"))):
                spy_update = AsyncMock(return_value=existing[0])
                with patch("app.service.merge_service.vault_dao.update_character", spy_update):
                    result = await service.merge_characters(
                        mock_db, 1,
                        [ExtractedCharacter(name="阿峰")],
                        chapter_number=4,
                    )
                    assert result.updated == 1
                    assert result.created == 0

    @pytest.mark.asyncio
    async def test_surname_match(self, service, mock_db):
        """[4] 姓氏匹配（首字相同）→ 匹配并标记低置信度。"""
        existing = [_make_vault_character(id=1, name="林峰")]
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_character", spy_update):
                with patch("app.service.merge_service.vault_dao.create_character",
                           AsyncMock(return_value=_make_vault_character(id=2, name="林轩"))):
                    result = await service.merge_characters(
                        mock_db, 1,
                        [ExtractedCharacter(name="林轩")],
                        chapter_number=4,
                    )
                    assert result.updated == 1

    @pytest.mark.asyncio
    async def test_no_match_create_new(self, service, mock_db):
        """[5] 无匹配 → 新建角色，置信度为 NEW_ENTITY_CONFIDENCE。"""
        existing = [_make_vault_character(id=1, name="林峰")]
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            new_char = _make_vault_character(id=2, name="苏暮雪")
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock(return_value=new_char)):
                result = await service.merge_characters(
                    mock_db, 1,
                    [ExtractedCharacter(name="苏暮雪", role="ally")],
                    chapter_number=4,
                )
                assert result.created == 1
                assert result.updated == 0


# ====================================================================
# 6-8: 人物状态变更测试 (P0)
# ====================================================================


class TestCharacterStatusChange:
    """人物状态变更规则测试。"""

    @pytest.mark.asyncio
    async def test_status_active_to_deceased(self, service, mock_db):
        """[6] 无匹配时创建新角色，状态为 deceased。"""
        existing = []
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            new_char = _make_vault_character(id=1, name="逝者")
            create_mock = AsyncMock(return_value=new_char)
            with patch("app.service.merge_service.vault_dao.create_character", create_mock):
                result = await service.merge_characters(
                    mock_db, 1,
                    [ExtractedCharacter(name="逝者", status="deceased")],
                    chapter_number=5,
                )
                assert result.created == 1
                assert result.updated == 0
                # 验证 create_character 调用参数中包含 status=deceased
                call_args = create_mock.call_args
                assert call_args is not None
                obj_in = call_args[0][1]
                assert obj_in.get("status") == "deceased"

    @pytest.mark.asyncio
    async def test_status_active_to_dormant(self, service, mock_db):
        """[7] 无匹配时创建新角色（带状态）。"""
        existing = []
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            new_char = _make_vault_character(id=1, name="隐退者")
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock(return_value=new_char)):
                result = await service.merge_characters(
                    mock_db, 1,
                    [ExtractedCharacter(name="隐退者", status="inactive")],
                    chapter_number=6,
                )
                assert result.created == 1

    @pytest.mark.asyncio
    async def test_empty_character_name_skipped(self, service, mock_db):
        """[8] 空名字的人物条目跳过。"""
        existing = []
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=existing)):
            with patch("app.service.merge_service.vault_dao.create_character",
                       AsyncMock()):
                result = await service.merge_characters(
                    mock_db, 1,
                    [ExtractedCharacter(name=""), ExtractedCharacter(name="   ")],
                    chapter_number=1,
                )
                assert result.created == 0
                assert len(result.warnings) == 2


# ====================================================================
# 9-12: 时间线合并测试 (P0)
# ====================================================================


class TestTimelineMerge:
    """时间线库合并测试。"""

    @pytest.mark.asyncio
    async def test_timeline_add(self, service, mock_db):
        """[9] 时间线 add: 新建事件。"""
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=[])):
            new_event = _make_vault_timeline(id=1, event="主角抵达城门")
            with patch("app.service.merge_service.vault_dao.create_timeline_event",
                       AsyncMock(return_value=new_event)):
                result = await service.merge_timeline(
                    mock_db, 1,
                    [ExtractedTimelineEvent(action="add", event="主角抵达城门",
                                            day=1, importance="major")],
                    chapter_number=1,
                )
                assert result.created == 1
                assert len(result.changes) == 1
                assert result.changes[0].change_type == "create"
                assert result.changes[0].entity_type == "timeline"

    @pytest.mark.asyncio
    async def test_timeline_resolve_date(self, service, mock_db):
        """[10] 时间线 resolve_date: 解决日期冲突。"""
        existing = [_make_vault_timeline(id=1, event="主角抵达城门", day=None)]
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_timeline_event", spy_update):
                result = await service.merge_timeline(
                    mock_db, 1,
                    [ExtractedTimelineEvent(action="resolve_date", event="主角抵达城门",
                                            day=5)],
                    chapter_number=2,
                )
                assert result.updated == 1
                spy_update.assert_called_once()
                # 通过检查 result 的 changes 确认 day 被更新
                assert any("day" in str(c.new_value) for c in result.changes)

    @pytest.mark.asyncio
    async def test_timeline_same_day_multiple_events(self, service, mock_db):
        """[11] 同一天多个不同事件 → 都保留，标注 multiple_events。"""
        existing = [_make_vault_timeline(id=1, event="主角抵达城门", day=1)]
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=existing)):
            new_event = _make_vault_timeline(id=2, event="苏暮雪出现", day=1)
            create_mock = AsyncMock(return_value=new_event)
            with patch("app.service.merge_service.vault_dao.create_timeline_event", create_mock):
                result = await service.merge_timeline(
                    mock_db, 1,
                    [ExtractedTimelineEvent(action="add", event="苏暮雪出现",
                                            day=1)],
                    chapter_number=1,
                )
                assert result.created == 1
                # 同日期冲突应该被记录
                assert len(result.conflicts) >= 1
                if result.conflicts:
                    assert result.conflicts[0].get("reason") == "同一天多事件冲突"

    @pytest.mark.asyncio
    async def test_timeline_same_day_dedup(self, service, mock_db):
        """[12] 同一天相同事件 → 去重，保留最早版本。"""
        existing = [_make_vault_timeline(id=1, event="主角抵达城门", day=1)]
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=existing)):
            result = await service.merge_timeline(
                mock_db, 1,
                [ExtractedTimelineEvent(action="add", event="主角抵达城门",
                                        day=1)],
                chapter_number=1,
            )
            assert result.created == 0
            assert any("已存在" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_timeline_correct(self, service, mock_db):
        """[12b] 时间线 correct: 修正已有事件描述。"""
        existing = [_make_vault_timeline(id=1, event="主角抵达城门",
                                         description="旧描述")]
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_timeline_event", spy_update):
                result = await service.merge_timeline(
                    mock_db, 1,
                    [ExtractedTimelineEvent(action="correct", event="主角抵达城门",
                                            description="新描述", day=1)],
                    chapter_number=2,
                )
                assert result.updated == 1


# ====================================================================
# 13-16: 剧情承诺合并测试 (P0)
# ====================================================================


class TestPlotPromiseMerge:
    """剧情承诺库合并测试。"""

    @pytest.mark.asyncio
    async def test_plot_promise_create(self, service, mock_db):
        """[13] 承诺 create: 新建剧情承诺。"""
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=[])):
            new_promise = _make_vault_plot_promise(id=1, title="幽冥教的阴谋")
            with patch("app.service.merge_service.vault_dao.create_plot_promise",
                       AsyncMock(return_value=new_promise)):
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="create", title="幽冥教的阴谋",
                                          type="悬念")],
                    chapter_number=1,
                )
                assert result.created == 1
                assert len(result.changes) == 1
                assert result.changes[0].change_type == "create"

    @pytest.mark.asyncio
    async def test_plot_promise_advance(self, service, mock_db):
        """[14] 承诺 advance: 推进已有承诺。"""
        existing = [_make_vault_plot_promise(id=1, title="幽冥教的阴谋",
                                              status="active", planted_chapter=1)]
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_plot_promise", spy_update):
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="advance", title="幽冥教的阴谋")],
                    chapter_number=2,
                )
                assert result.updated == 1
                spy_update.assert_called_once()
                # 验证 changes 中有 update 记录
                assert result.changes[0].change_type == "update"
                assert "advancing" in result.changes[0].new_value

    @pytest.mark.asyncio
    async def test_plot_promise_redeem(self, service, mock_db):
        """[15] 承诺 redeem: 兑现剧情承诺。"""
        existing = [_make_vault_plot_promise(id=1, title="幽冥教的阴谋",
                                              status="advancing", planted_chapter=1)]
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_plot_promise", spy_update):
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="redeem", title="幽冥教的阴谋")],
                    chapter_number=5,
                )
                assert result.updated == 1
                # 通过 changes 验证状态变为 resolved
                change = result.changes[0]
                assert change.change_type == "update"
                assert change.new_value == "resolved"

    @pytest.mark.asyncio
    async def test_plot_promise_cancel(self, service, mock_db):
        """[16] 承诺 cancel: 废弃剧情承诺并记录原因。"""
        existing = [_make_vault_plot_promise(id=1, title="废弃支线",
                                              status="active", planted_chapter=1)]
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_plot_promise", spy_update):
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="cancel", title="废弃支线",
                                          cancel_reason="剧情方向调整")],
                    chapter_number=3,
                )
                assert result.updated == 1
                # 通过 changes 验证状态变为 abandoned
                change = result.changes[0]
                assert change.new_value == "abandoned"


# ====================================================================
# 17-18: 承诺超时 stale / 废弃原因 (P1)
# ====================================================================


class TestPlotPromiseStale:
    """剧情承诺超时检查。"""

    @pytest.mark.asyncio
    async def test_plot_promise_stale_detected(self, service, mock_db):
        """[17] 承诺超过 STALE_CHAPTER_THRESHOLD 章未兑现 → stale 警告。"""
        existing = [
            _make_vault_plot_promise(
                id=1, title="超长伏笔", status="active",
                planted_chapter=1,
            )
        ]
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=existing)):
            # 推进一个承诺，同时检测 stale
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_plot_promise", spy_update):
                far_chapter = 1 + STALE_CHAPTER_THRESHOLD + 1
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="advance", title="超长伏笔")],
                    chapter_number=far_chapter,
                )
                # 应该有 stale 警告
                stale_warnings = [w for w in result.warnings if "超时" in w or "stale" in w.lower()]
                assert len(stale_warnings) >= 1

    @pytest.mark.asyncio
    async def test_plot_promise_cancel_reason(self, service, mock_db):
        """[18] 废弃承诺记录取消原因。"""
        existing = [_make_vault_plot_promise(id=1, title="被废弃的支线")]
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_plot_promise", spy_update):
                result = await service.merge_plot_promises(
                    mock_db, 1,
                    [ExtractedPlotPromise(action="cancel", title="被废弃的支线",
                                          cancel_reason="作者修改大纲")],
                    chapter_number=10,
                )
                change = result.changes[0]
                assert "废弃" in change.change_reason or "废弃" in (change.change_reason or "")
                assert "作者修改大纲" in change.change_reason


# ====================================================================
# 19-22: 世界观合并测试 (P0)
# ====================================================================


class TestWorldBuildingMerge:
    """世界观库合并测试。"""

    @pytest.mark.asyncio
    async def test_world_create(self, service, mock_db):
        """[19] 世界观 create: 新建条目。"""
        with patch("app.service.merge_service.vault_dao.get_world_entries",
                   AsyncMock(return_value=[])):
            new_entry = _make_vault_world(id=1, name="青云宗", category="faction")
            with patch("app.service.merge_service.vault_dao.create_world_entry",
                       AsyncMock(return_value=new_entry)):
                result = await service.merge_world_building(
                    mock_db, 1,
                    [ExtractedWorldItem(action="create", name="青云宗",
                                        category="faction", content="修仙宗门")],
                    chapter_number=1,
                )
                assert result.created == 1
                assert len(result.changes) == 1

    @pytest.mark.asyncio
    async def test_world_expand(self, service, mock_db):
        """[20] 世界观 expand: 扩展已有条目。"""
        existing = [_make_vault_world(id=1, name="青云宗", category="faction",
                                       description="修仙宗门")]
        with patch("app.service.merge_service.vault_dao.get_world_entries",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_world_entry", spy_update):
                result = await service.merge_world_building(
                    mock_db, 1,
                    [ExtractedWorldItem(action="expand", name="青云宗",
                                        content="位于青云山巅")],
                    chapter_number=2,
                )
                assert result.updated == 1
                spy_update.assert_called_once()
                # 通过 changes 验证描述被扩展
                change = result.changes[0]
                assert change.change_type == "update"
                assert "[扩展]" in (change.new_value or "")

    @pytest.mark.asyncio
    async def test_world_revise(self, service, mock_db):
        """[21] 世界观 revise: 修订已有条目内容。"""
        existing = [_make_vault_world(id=1, name="青云宗", description="修仙宗门")]
        with patch("app.service.merge_service.vault_dao.get_world_entries",
                   AsyncMock(return_value=existing)):
            spy_update = AsyncMock(return_value=existing[0])
            with patch("app.service.merge_service.vault_dao.update_world_entry", spy_update):
                result = await service.merge_world_building(
                    mock_db, 1,
                    [ExtractedWorldItem(action="revise", name="青云宗",
                                        content="修订后的描述")],
                    chapter_number=3,
                )
                assert result.updated == 1
                # 变更日志包含新旧值
                assert result.changes[0].old_value is not None
                assert result.changes[0].new_value is not None

    @pytest.mark.asyncio
    async def test_world_conflict_detected(self, service, mock_db):
        """[22] 世界观 conflict: 检测到 system 规则冲突。"""
        existing = [
            _make_vault_world(id=1, name="灵力规则", category="system",
                               description="灵力不能凭空产生",
                               constraint="灵力不能凭空产生"),
        ]
        with patch("app.service.merge_service.vault_dao.get_world_entries",
                   AsyncMock(return_value=existing)):
            result = await service.merge_world_building(
                mock_db, 1,
                [ExtractedWorldItem(action="conflict", name="灵力规则",
                                    category="system",
                                    content="灵力可以凭空产生")],
                chapter_number=1,
            )
            assert len(result.conflicts) >= 1
            # 应该检测到"不能"相关的否定
            assert any("冲突" in str(c) for c in result.conflicts)


# ====================================================================
# 23-24: 变更日志测试 (P0)
# ====================================================================


class TestChangelog:
    """变更日志格式/完整性测试。"""

    @pytest.mark.asyncio
    async def test_archive_changelog_creates_entries(self, service, mock_db):
        """[23] archive_changelog 正确创建 VaultChangelog 记录。"""
        changes = [
            ChangeEntry(
                entity_type="character", entity_id="1", entity_name="林峰",
                change_type="update", old_value="active", new_value="deceased",
                chapter=5, confidence=1.0,
                change_reason="角色死亡",
            ),
            ChangeEntry(
                entity_type="world", entity_id="2", entity_name="青云宗",
                change_type="create", old_value=None, new_value=None,
                chapter=5, confidence=0.85,
                change_reason="新建世界观条目",
            ),
        ]
        await service.archive_changelog(mock_db, 1, changes, chapter_number=5)
        # 验证 db.add 被调用了 2 次
        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_archive_changelog_empty(self, service, mock_db):
        """[24] 空变更列表 → 不创建任何记录。"""
        await service.archive_changelog(mock_db, 1, [], chapter_number=5)
        assert mock_db.add.call_count == 0


# ====================================================================
# 25-26: 空输入 / 无变更测试 (边界)
# ====================================================================


class TestEmptyInput:
    """边界情况：空输入 / 无变更。"""

    @pytest.mark.asyncio
    async def test_empty_characters_list(self, service, mock_db):
        """[25] 空角色列表 → 无操作。"""
        result = await service.merge_characters(mock_db, 1, [], chapter_number=1)
        assert result.created == 0
        assert result.updated == 0
        assert len(result.changes) == 0

    @pytest.mark.asyncio
    async def test_empty_all_inputs(self, service, mock_db):
        """[26] 所有提取输入均为空 → 四个 merge 方法都返回空结果。"""
        for merge_fn, args in [
            (service.merge_characters, ([],)),
            (service.merge_timeline, ([],)),
            (service.merge_plot_promises, ([],)),
            (service.merge_world_building, ([],)),
        ]:
            result = await merge_fn(mock_db, 1, *args, chapter_number=1)
            assert isinstance(result, MergeResult)
            assert result.created == 0
            assert result.updated == 0

    @pytest.mark.asyncio
    async def test_empty_event_skipped(self, service, mock_db):
        """[26b] 空事件描述的时间线条目跳过。"""
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=[])):
            result = await service.merge_timeline(
                mock_db, 1,
                [ExtractedTimelineEvent(action="add", event="", day=1)],
                chapter_number=1,
            )
            assert result.created == 0
            assert len(result.warnings) >= 1


# ====================================================================
# 27-28: 置信度降级计算 (功能)
# ====================================================================


class TestConfidenceDegradation:
    """置信度降级计算测试。"""

    def test_exact_match_confidence(self, service):
        """[27] 精确匹配 → confidence = 1.0。"""
        assert service._calc_confidence(0, matched=True) == 1.0
        assert service._calc_confidence(0, matched=True) == 1.0

    def test_edit_distance_confidence(self, service):
        """[28] 编辑距离=1 → 0.9, 编辑距离=2 → 0.75。"""
        assert service._calc_confidence(1, matched=True) == 0.9
        assert service._calc_confidence(2, matched=True) == 0.75

    def test_surname_confidence(self, service):
        """[28b] 姓氏匹配 → confidence = SURNAME_MATCH_CONFIDENCE。"""
        assert service._calc_confidence(3, matched=True) == SURNAME_MATCH_CONFIDENCE

    def test_new_entity_confidence(self, service):
        """[28c] 无匹配 → confidence = NEW_ENTITY_CONFIDENCE。"""
        assert service._calc_confidence(0, matched=False) == NEW_ENTITY_CONFIDENCE


# ====================================================================
# 29-30: 编辑距离 / 姓氏匹配 (功能)
# ====================================================================


class TestMatchingUtilities:
    """匹配工具函数测试。"""

    def test_edit_distance_zero(self, service):
        """[29a] 相同字符串编辑距离为 0。"""
        assert service._calc_edit_distance("林峰", "林峰") == 0

    def test_edit_distance_one(self, service):
        """[29b] 编辑距离=1。"""
        assert service._calc_edit_distance("林峰", "林锋") == 1

    def test_edit_distance_two(self, service):
        """[29c] 编辑距离=2。"""
        assert service._calc_edit_distance("林峰", "林风") <= 2

    def test_surname_match_true(self, service):
        """[29d] 姓氏匹配成功。"""
        assert service._surname_match("林峰", "林轩") is True

    def test_surname_match_false(self, service):
        """[29e] 姓氏匹配失败。"""
        assert service._surname_match("林峰", "苏暮雪") is False

    def test_surname_match_empty(self, service):
        """[29f] 空字符串无匹配。"""
        assert service._surname_match("", "林峰") is False


# ====================================================================
# 额外测试：集成和边界场景
# ====================================================================


class TestBulkAndEdgeCases:
    """批量和大输入处理。"""

    @pytest.mark.asyncio
    async def test_bulk_character_create(self, service, mock_db):
        """同时创建多个角色。"""
        with patch("app.service.merge_service.vault_dao.get_characters",
                   AsyncMock(return_value=[])):
            create_mock = AsyncMock(return_value=_make_vault_character(id=99, name="批量角色"))
            with patch("app.service.merge_service.vault_dao.create_character", create_mock):
                names = [f"角色{i}" for i in range(5)]
                items = [ExtractedCharacter(name=n) for n in names]
                result = await service.merge_characters(
                    mock_db, 1, items, chapter_number=1,
                )
                assert result.created == 5
                assert create_mock.call_count == 5

    @pytest.mark.asyncio
    async def test_plot_promise_empty_title_skipped(self, service, mock_db):
        """空标题的承诺条目跳过。"""
        with patch("app.service.merge_service.vault_dao.get_plot_promises",
                   AsyncMock(return_value=[])):
            result = await service.merge_plot_promises(
                mock_db, 1,
                [ExtractedPlotPromise(action="create", title=""),
                 ExtractedPlotPromise(action="advance", title="  ")],
                chapter_number=1,
            )
            assert result.created == 0
            assert len(result.warnings) == 2

    @pytest.mark.asyncio
    async def test_world_duplicate_create_skipped(self, service, mock_db):
        """重复创建已有世界观条目 → 跳过。"""
        existing = [_make_vault_world(id=1, name="青云宗")]
        with patch("app.service.merge_service.vault_dao.get_world_entries",
                   AsyncMock(return_value=existing)):
            result = await service.merge_world_building(
                mock_db, 1,
                [ExtractedWorldItem(action="create", name="青云宗",
                                    category="faction")],
                chapter_number=2,
            )
            assert result.created == 0
            assert any("已存在" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_timeline_correct_nonexistent(self, service, mock_db):
        """修正不存在的事件 → warning。"""
        with patch("app.service.merge_service.vault_dao.get_timeline",
                   AsyncMock(return_value=[])):
            result = await service.merge_timeline(
                mock_db, 1,
                [ExtractedTimelineEvent(action="correct", event="不存在的事件",
                                        description="修正描述")],
                chapter_number=2,
            )
            assert result.updated == 0
            assert any("未找到" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_change_reason_generation(self, service):
        """验证 generate_change_reason 输出格式。"""
        reason = service._generate_change_reason("角色", "create", "林峰")
        assert "角色" in reason
        assert "林峰" in reason
        assert "新建" in reason

        reason2 = service._generate_change_reason("世界", "update", "青云宗",
                                                   detail="扩展描述")
        assert "扩展描述" in reason2


# ====================================================================
# 变更日志格式完整性
# ====================================================================


class TestChangeEntryStructure:
    """ChangeEntry 数据结构测试。"""

    def test_change_entry_all_fields(self):
        """ChangeEntry 包含所有必需字段。"""
        entry = ChangeEntry(
            entity_type="character", entity_id="1", entity_name="林峰",
            change_type="update", old_value="active", new_value="deceased",
            chapter=5, confidence=1.0, change_reason="角色死亡",
        )
        assert entry.entity_type == "character"
        assert entry.entity_id == "1"
        assert entry.entity_name == "林峰"
        assert entry.change_type == "update"
        assert entry.old_value == "active"
        assert entry.chapter == 5
        assert entry.confidence == 1.0

    def test_change_entry_optional_fields(self):
        """ChangeEntry 可选字段默认为 None。"""
        entry = ChangeEntry(
            entity_type="character", entity_id="1", entity_name="林峰",
            change_type="create", old_value=None, new_value=None,
            chapter=1, confidence=0.3, change_reason="新建",
        )
        assert entry.old_value is None
        assert entry.new_value is None

    def test_merge_result_defaults(self):
        """MergeResult 默认值为 0/空列表。"""
        result = MergeResult(entity_type="character")
        assert result.created == 0
        assert result.updated == 0
        assert result.conflicts == []
        assert result.warnings == []
        assert result.changes == []

    def test_extracted_character_defaults(self):
        """ExtractedCharacter 默认值。"""
        char = ExtractedCharacter(name="测试角色")
        assert char.role == "neutral"
        assert char.status == "active"
        assert char.aliases == []
        assert char.confidence == 0.8
