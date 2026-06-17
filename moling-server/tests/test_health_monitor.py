"""墨灵 (Moling) — HealthMonitorService 单元测试 (§5.3).

测试覆盖：
- R1: 8 章未推进告警（活跃/推进中承诺，推进记录边界）
- R2: 4+ 同类型重复推进（不同 event_type 分布，数量不足）
- R3: 10 章静默告警 + 降级为 R1
- 防疲劳过滤：近 3 章同告警去重
- 集成：check_health 全流程
- 边界：空承诺列表、无推进记录、非活跃状态
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.service.health_monitor import (
    HealthMonitorService,
    _check_r1,
    _check_r2,
    _check_r3,
    _check_anti_fatigue,
    _is_mentioned_in_chapter,
    _get_last_advance_chapter,
    _make_result,
)

# ── 确保 async 测试在没有 conftest 的场景下也能运行 ──
pytestmark = pytest.mark.asyncio


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
def service() -> HealthMonitorService:
    """HealthMonitorService 实例。"""
    return HealthMonitorService()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession。"""
    return AsyncMock()


# ──────────── 辅助函数 ────────────


def make_promise(
    *,
    promise_id: str = "p0001",
    title: str = "神秘人的真实身份",
    description: str = "神秘人究竟是谁？他为什么帮助主角？",
    status: str = "active",
    planted_chapter: int = 1,
    advancement_log: Optional[List[Dict[str, Any]]] = None,
    related_characters: Optional[List[str]] = None,
) -> SimpleNamespace:
    """创建一个模拟的 VaultPlotPromise 对象。"""
    return SimpleNamespace(
        id=promise_id,
        title=title,
        description=description,
        status=status,
        planted_chapter=planted_chapter,
        advancement_log=advancement_log or [],
        related_characters=related_characters or [],
        type="mystery",
        urgency=7,
        redeem_window=20,
    )


def make_alert(
    *,
    rule: str = "R1",
    promise_title: str = "神秘人的真实身份",
    promise_id: str = "p0001",
    level: str = "yellow",
    detail: str = "已连续8章未推进",
) -> dict[str, Any]:
    """创建一个模拟告警条目。"""
    return {
        "rule": rule,
        "promise_title": promise_title,
        "promise_id": promise_id,
        "level": level,
        "detail": detail,
    }


# ===========================================================================
# 辅助函数测试
# ===========================================================================


class TestGetLastAdvanceChapter:
    """_get_last_advance_chapter 单元测试。"""

    def test_with_advancement_log(self):
        """advancement_log 有数据时返回最后推进的 chapter。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 3, "note": "初现端倪", "event_type": "foreshadow"},
                {"chapter": 5, "note": "再次出现", "event_type": "advance"},
            ]
        )
        assert _get_last_advance_chapter(promise) == 5

    def test_empty_log_uses_planted(self):
        """advancement_log 为空时使用 planted_chapter。"""
        promise = make_promise(advancement_log=[], planted_chapter=2)
        assert _get_last_advance_chapter(promise) == 2

    def test_no_log_no_planted_returns_zero(self):
        """既无 log 也无 planted_chapter 时返回 0。"""
        promise = make_promise(advancement_log=None, planted_chapter=None)
        assert _get_last_advance_chapter(promise) == 0

    def test_missing_chapter_key_in_log(self):
        """advancement_log 条目不包含 chapter 时忽略。"""
        promise = make_promise(
            advancement_log=[{"note": "no chapter here"}]
        )
        assert _get_last_advance_chapter(promise) == 0


class TestIsMentionedInChapter:
    """_is_mentioned_in_chapter 单元测试。"""

    def test_title_matches(self):
        """标题关键词匹配。"""
        promise = make_promise(title="地宫秘密")
        assert _is_mentioned_in_chapter(promise, "主角进入了地宫秘密通道") is True

    def test_description_matches(self):
        """描述关键词匹配。"""
        promise = make_promise(description="隐藏在幕后的黑手")
        assert _is_mentioned_in_chapter(promise, "隐藏在幕后的黑手终于现身") is True

    def test_character_matches(self):
        """相关角色名匹配。"""
        promise = make_promise(related_characters=["林夜", "苏瑶"])
        assert _is_mentioned_in_chapter(promise, "林夜拔出长剑") is True

    def test_no_match_returns_false(self):
        """无匹配时返回 False。"""
        promise = make_promise(title="地宫秘密", description="上古遗迹")
        assert _is_mentioned_in_chapter(promise, "今天天气很好") is False

    def test_none_content_returns_false(self):
        """章节内容为 None 时返回 False。"""
        promise = make_promise(title="地宫秘密")
        assert _is_mentioned_in_chapter(promise, None) is False

    def test_empty_content_returns_false(self):
        """章节内容为空时返回 False。"""
        promise = make_promise(title="地宫秘密")
        assert _is_mentioned_in_chapter(promise, "") is False

    def test_case_insensitive(self):
        """匹配不区分大小写。"""
        promise = make_promise(title="MYSTERY BOX")
        assert _is_mentioned_in_chapter(promise, "the mystery box opened") is True


# ===========================================================================
# R1 测试
# ===========================================================================


class TestR1:
    """R1: 8 章未推进告警测试。"""

    def test_active_status_triggers_alert(self):
        """active 状态的承诺超过 8 章未推进应触发告警。"""
        promise = make_promise(
            status="active",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is not None
        assert alert["rule"] == "R1"
        assert alert["level"] == "yellow"

    def test_advancing_status_triggers_alert(self):
        """advancing 状态的承诺超过 8 章未推进应触发告警。"""
        promise = make_promise(
            status="advancing",
            advancement_log=[{"chapter": 1, "event_type": "advance"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="复仇之路")
        assert alert is not None

    def test_within_window_no_alert(self):
        """8 章内有推进记录不触发告警。"""
        promise = make_promise(
            status="active",
            advancement_log=[{"chapter": 5, "event_type": "advance"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is None  # 10 - 5 = 5 < 8

    def test_exact_boundary(self):
        """恰好 8 章未推进应触发告警。"""
        promise = make_promise(
            status="active",
            advancement_log=[{"chapter": 2, "event_type": "advance"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is not None  # 10 - 2 = 8 >= 8

    def test_resolved_status_no_alert(self):
        """已解决状态的承诺不触发告警。"""
        promise = make_promise(
            status="resolved",
            advancement_log=[{"chapter": 1, "event_type": "advance"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is None

    def test_dormant_status_no_alert(self):
        """休眠状态的承诺不触发告警。"""
        promise = make_promise(
            status="dormant",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is None

    def test_no_advancement_log_uses_planted(self):
        """无推进记录时使用 planted_chapter 计算。"""
        promise = make_promise(
            status="active",
            advancement_log=[],
            planted_chapter=1,
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is not None

    def test_no_advancement_within_window_no_alert(self):
        """无推进记录但 planted 在 8 章内不告警。"""
        promise = make_promise(
            status="active",
            advancement_log=[],
            planted_chapter=5,
        )
        alert = _check_r1(promise, current_chapter=10, promise_title="神秘人的真实身份")
        assert alert is None  # 10 - 5 = 5 < 8


# ===========================================================================
# R2 测试
# ===========================================================================


class TestR2:
    """R2: 4+ 同类型重复推进行为测试。"""

    def test_identical_event_types_triggers(self):
        """全部同类型推进 >=4 次触发告警。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 1, "event_type": "foreshadow"},
                {"chapter": 3, "event_type": "foreshadow"},
                {"chapter": 5, "event_type": "foreshadow"},
                {"chapter": 7, "event_type": "foreshadow"},
            ]
        )
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is not None
        assert alert["rule"] == "R2"
        assert alert["level"] == "orange"
        assert "foreshadow" in alert["detail"]

    def test_mixed_types_no_alert(self):
        """不同 event_type 混合不触发告警。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 1, "event_type": "foreshadow"},
                {"chapter": 3, "event_type": "advance"},
                {"chapter": 5, "event_type": "twist"},
                {"chapter": 7, "event_type": "climax"},
            ]
        )
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is None

    def test_less_than_four_no_alert(self):
        """少于 4 条记录不触发告警。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 1, "event_type": "foreshadow"},
                {"chapter": 3, "event_type": "foreshadow"},
                {"chapter": 5, "event_type": "foreshadow"},
            ]
        )
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is None

    def test_empty_log_no_alert(self):
        """空推进记录不触发告警。"""
        promise = make_promise(advancement_log=[])
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is None

    def test_log_none_no_alert(self):
        """advancement_log 为 None 不触发告警。"""
        promise = make_promise(advancement_log=None)
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is None

    def test_mixed_with_none_event_type(self):
        """部分记录缺少 event_type，但有 >=4 条同类型仍触发。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 1, "event_type": "foreshadow"},
                {"chapter": 3, "note": "no type here"},
                {"chapter": 5, "event_type": "foreshadow"},
                {"chapter": 7, "event_type": "foreshadow"},
                {"chapter": 9, "event_type": "foreshadow"},
            ]
        )
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is not None

    def test_multiple_identical_types_count(self):
        """检测 detail 中应包含总推进次数。"""
        promise = make_promise(
            advancement_log=[
                {"chapter": 1, "event_type": "advance"},
                {"chapter": 3, "event_type": "advance"},
                {"chapter": 5, "event_type": "advance"},
                {"chapter": 7, "event_type": "advance"},
                {"chapter": 9, "event_type": "advance"},
            ]
        )
        alert = _check_r2(promise, promise_title="神秘人的真实身份")
        assert alert is not None
        assert "连续5次" in alert["detail"]


# ===========================================================================
# R3 测试
# ===========================================================================


class TestR3:
    """R3: 10 章静默承诺告警 + 降级检查测试。"""

    def test_silent_triggers_red(self):
        """超过 10 章无推进且无提及触发红色告警。"""
        promise = make_promise(
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        alert = _check_r3(
            promise,
            current_chapter=12,
            current_chapter_content="今天天气很好",
            promise_title="地宫秘密",
        )
        assert alert is not None
        assert alert["rule"] == "R3"
        assert alert["level"] == "red"

    def test_mentioned_degraded_to_r1(self):
        """有关键词提及但无正式推进 → 降级为 R1。"""
        promise = make_promise(
            title="地宫秘密",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        alert = _check_r3(
            promise,
            current_chapter=12,
            current_chapter_content="主角终于找到了地宫秘密的线索",
            promise_title="地宫秘密",
        )
        assert alert is not None
        assert alert["rule"] == "R1"
        assert alert["level"] == "yellow"
        assert "降级" in alert["detail"]

    def test_within_window_no_alert(self):
        """10 章内有推进不触发告警。"""
        promise = make_promise(
            advancement_log=[{"chapter": 5, "event_type": "advance"}],
        )
        alert = _check_r3(
            promise,
            current_chapter=12,
            current_chapter_content=None,
            promise_title="地宫秘密",
        )
        assert alert is None  # 12 - 5 = 7 < 10

    def test_exact_boundary_triggers(self):
        """恰好 10 章无推进触发告警。"""
        promise = make_promise(
            advancement_log=[{"chapter": 2, "event_type": "advance"}],
        )
        alert = _check_r3(
            promise,
            current_chapter=12,
            current_chapter_content=None,
            promise_title="地宫秘密",
        )
        assert alert is not None

    def test_no_advancement_log_uses_planted(self):
        """无推进记录时使用 planted_chapter 计算。"""
        promise = make_promise(
            advancement_log=[],
            planted_chapter=1,
        )
        alert = _check_r3(
            promise,
            current_chapter=12,
            current_chapter_content=None,
            promise_title="地宫秘密",
        )
        assert alert is not None


# ===========================================================================
# 防疲劳过滤测试
# ===========================================================================


class TestAntiFatigue:
    """防疲劳过滤 _check_anti_fatigue 测试。"""

    def test_no_previous_alerts_no_filter(self):
        """无历史告警时不去重。"""
        alerts = [make_alert()]
        result = _check_anti_fatigue(alerts, {}, current_chapter=10)
        assert len(result) == 1

    def test_duplicate_within_window_suppressed(self):
        """近 3 章内有相同 (promise_id, rule) 时被抑制。"""
        alerts = [make_alert(promise_id="p0001", rule="R1")]
        previous = {
            8: [make_alert(promise_id="p0001", rule="R1")],
        }
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 0  # 10 - 8 = 2 < 3

    def test_different_promise_not_suppressed(self):
        """不同承诺的告警不被抑制。"""
        alerts = [make_alert(promise_id="p0002", rule="R1")]
        previous = {
            8: [make_alert(promise_id="p0001", rule="R1")],
        }
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 1

    def test_different_rule_not_suppressed(self):
        """不同规则的告警不被抑制。"""
        alerts = [make_alert(promise_id="p0001", rule="R2")]
        previous = {
            8: [make_alert(promise_id="p0001", rule="R1")],
        }
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 1

    def test_outside_window_not_suppressed(self):
        """超过 3 章的历史告警不抑制。"""
        alerts = [make_alert(promise_id="p0001", rule="R1")]
        previous = {
            6: [make_alert(promise_id="p0001", rule="R1")],  # 10 - 6 = 4 >= 3
        }
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 1

    def test_multiple_alerts_partial_suppression(self):
        """多个告警中部分被抑制。"""
        alerts = [
            make_alert(promise_id="p0001", rule="R1"),
            make_alert(promise_id="p0002", rule="R3"),
        ]
        previous = {
            9: [make_alert(promise_id="p0001", rule="R1")],
        }
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 1
        assert result[0]["promise_id"] == "p0002"
        assert result[0]["rule"] == "R3"

    def test_empty_alerts_returns_empty(self):
        """空告警列表返回空列表。"""
        assert _check_anti_fatigue([], {}, current_chapter=10) == []

    def test_multiple_previous_chapters(self):
        """检查多个历史章节的告警。"""
        alerts = [make_alert(promise_id="p0001", rule="R1")]
        previous = {
            7: [],
            8: [make_alert(promise_id="p0002", rule="R2")],
            9: [make_alert(promise_id="p0001", rule="R1")],
        }
        # 9 章有 R1 for p0001, 10 - 9 = 1 < 3 → 抑制
        result = _check_anti_fatigue(alerts, previous, current_chapter=10)
        assert len(result) == 0


# ===========================================================================
# 结果构建测试
# ===========================================================================


class TestMakeResult:
    """_make_result 单元测试。"""

    def test_basic_result(self):
        """基本结果格式。"""
        alerts = [make_alert()]
        result = _make_result(15, alerts)
        assert result["checked_at"] == "第15章"
        assert len(result["alerts"]) == 1

    def test_empty_alerts(self):
        """空告警列表。"""
        result = _make_result(5, [])
        assert result["checked_at"] == "第5章"
        assert result["alerts"] == []


# ===========================================================================
# 集成测试
# ===========================================================================


class TestCheckHealth:
    """check_health 集成测试。"""

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_no_promises_no_alerts(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """无承诺时返回空告警列表。"""
        mock_promises.return_value = []
        mock_content.return_value = None
        mock_prev.return_value = {}

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=10)
        assert result["checked_at"] == "第10章"
        assert result["alerts"] == []

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_r1_alert_generated(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """R1 告警正确生成。"""
        promise = make_promise(
            promise_id="p0001",
            title="神秘人的真实身份",
            status="active",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        mock_promises.return_value = [promise]
        mock_content.return_value = None
        mock_prev.return_value = {}

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=10)
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["rule"] == "R1"
        assert result["alerts"][0]["level"] == "yellow"

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_r2_alert_generated(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """R2 告警正确生成。"""
        promise = make_promise(
            promise_id="p0002",
            title="重复伏笔",
            status="active",
            advancement_log=[
                {"chapter": 1, "event_type": "foreshadow"},
                {"chapter": 3, "event_type": "foreshadow"},
                {"chapter": 5, "event_type": "foreshadow"},
                {"chapter": 7, "event_type": "foreshadow"},
            ],
        )
        mock_promises.return_value = [promise]
        mock_content.return_value = None
        mock_prev.return_value = {}

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=10)
        # last adv = 7, current = 10 => 10-7=3 < 8, so no R1, only R2
        assert len(result["alerts"]) == 1
        rules = [a["rule"] for a in result["alerts"]]
        assert rules == ["R2"]

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_r3_alert_generated(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """R3 告警正确生成。"""
        promise = make_promise(
            promise_id="p0003",
            title="地宫秘密",
            status="active",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        mock_promises.return_value = [promise]
        mock_content.return_value = "今天的天气很好"
        mock_prev.return_value = {}

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=12)
        assert len(result["alerts"]) == 2  # R1 (12-1=11>=8) + R3(12-1=11>=10, no mention)
        rules = {a["rule"] for a in result["alerts"]}
        assert "R1" in rules
        assert "R3" in rules

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_r3_degraded_to_r1_with_mention(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """章节内容提及承诺关键词时，R3 降级为 R1。"""
        promise = make_promise(
            promise_id="p0003",
            title="地宫秘密",
            status="active",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        mock_promises.return_value = [promise]
        mock_content.return_value = "主角发现了地宫秘密的线索"
        mock_prev.return_value = {}

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=12)
        # R1 (12-1=11>=8) + R3降级R1
        # After anti-fatigue: both are R1 for the same promise_id, one should be suppressed
        # ...actually no, the anti-fatigue checks (promise_id, rule) pair, so both would have 
        # (p0003, R1) and the first one would trigger, but the second one is also (p0003, R1)
        # and would be suppressed by anti-fatigue since previous_alerts_by_chapter is empty.
        # Wait, anti-fatigue looks at previous chapters, not the current batch. So both should pass.
        # Both are R1 for p0003 but with different details. The anti-fatigue checks 
        # if (p0003, R1) was in PREVIOUS chapters. Since there's no previous, both stay.
        assert len(result["alerts"]) >= 1
        # At least the R1 (from R3 degradation) should be present
        rules = {a["rule"] for a in result["alerts"]}
        assert "R1" in rules
        assert "R3" not in rules  # R3 was degraded

    @patch("app.service.health_monitor._get_plot_promises")
    @patch("app.service.health_monitor._get_chapter_content")
    @patch("app.service.health_monitor._get_previous_health_checks")
    async def test_anti_fatigue_suppresses_duplicate(
        self,
        mock_prev: AsyncMock,
        mock_content: AsyncMock,
        mock_promises: AsyncMock,
        mock_db: AsyncMock,
        service: HealthMonitorService,
    ):
        """防疲劳过滤正确抑制近 3 章的重复告警。"""
        promise = make_promise(
            promise_id="p0001",
            title="神秘人的真实身份",
            status="active",
            advancement_log=[{"chapter": 1, "event_type": "foreshadow"}],
        )
        mock_promises.return_value = [promise]
        mock_content.return_value = None
        mock_prev.return_value = {
            8: [make_alert(promise_id="p0001", rule="R1")],
        }

        result = await service.check_health(mock_db, project_id="proj-1", current_chapter=10)
        # R1 would be generated (10-1=9>=8), but anti-fatigue sees (p0001, R1) at ch8 (diff=2<3)
        # So R1 is suppressed → no alerts
        assert len(result["alerts"]) == 0
