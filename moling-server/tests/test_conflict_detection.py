"""墨灵 (Moling) — ConflictDetectionService 单元测试.

覆盖三类冲突检测的完整逻辑：

1. 连贯性基线冲突 (baseline)
2. 秘密矩阵冲突 (secret)
3. 人物状态机冲突 (state_machine)

以及边界场景：空卡片、空动态层、异常处理等。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import CardPool, DynamicLayer, Secret, VaultCharacter
from app.service.conflict_detection import (
    ConflictDetectionService,
    conflict_detection_service,
    _compute_confidence,
    _compute_confidence_label,
)

# ============================================================================
# Helpers — 快速构造测试用模型实例
# ============================================================================


def _make_card(
    name: str = "测试卡片",
    direction_text: str = "角色踏上新旅程",
    direction_type: str = "有趣",
    rarity: str = "rare",
    characters: list | None = None,
    **kwargs,
) -> CardPool:
    """构造一个轻量 CardPool 实例（仅填充检测所需的字段）。"""
    card = CardPool(
        name=name,
        direction_text=direction_text,
        direction_type=direction_type,
        rarity=rarity,
        characters=characters or [],
    )
    # CardPool 的 __init__ 需要 id，手动补一个
    object.__setattr__(card, "id", hash(name) % 10**6)
    for k, v in kwargs.items():
        object.__setattr__(card, k, v)
    return card


def _make_dynamic_layer(
    project_id: str = 1,
    chapter_id: str = "chap-1",
    must_hold: list[str] | None = None,
    must_not: list[str] | None = None,
    information_asymmetry: dict | None = None,
) -> DynamicLayer:
    """构造一个轻量 DynamicLayer 实例。"""
    dl = DynamicLayer(
        project_id=project_id,
        chapter_id=chapter_id,
        must_hold=must_hold or [],
        must_not=must_not or [],
        information_asymmetry=information_asymmetry or {},
    )
    object.__setattr__(dl, "id", "dl-1")
    return dl


def _make_secret(
    description: str,
    known_by: list[str] | None = None,
    unknown_to: list[str] | None = None,
    secrecy_level: str = "hidden",
) -> Secret:
    s = Secret(
        project_id=1,
        description=description,
        known_by=known_by or [],
        unknown_to=unknown_to or [],
        secrecy_level=secrecy_level,
    )
    object.__setattr__(s, "id", hash(description) % 10**6)
    return s


def _make_vault_character(
    name: str,
    current_state: str | None = None,
    state_machine: dict | None = None,
) -> VaultCharacter:
    vc = VaultCharacter(
        project_id=1,
        name=name,
        status="active",
        current_state=current_state,
        state_machine=state_machine or {},
    )
    object.__setattr__(vc, "id", f"vc-{name}")
    return vc


# ============================================================================
# Baseline Conflict Tests
# ============================================================================


class TestBaselineConflicts:
    """连贯性基线冲突 — must_hold / must_not 检测。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_no_dynamic_layer_returns_empty(self):
        """无动态层数据时返回空列表。"""
        cards = [_make_card()]
        result = await self.service._detect_baseline_conflicts(cards, None)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_must_hold_or_not_returns_empty(self):
        """must_hold 和 must_not 都为空时返回空列表。"""
        dl = _make_dynamic_layer(must_hold=[], must_not=[])
        cards = [_make_card()]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        assert result == []

    @pytest.mark.asyncio
    async def test_card_contradicts_must_hold(self):
        """卡片方向违反 must_hold 约束。"""
        dl = _make_dynamic_layer(must_hold=["师徒关系"])
        cards = [_make_card(direction_text="师徒决裂，反目成仇")]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        assert len(result) == 1
        assert result[0]["type"] == "baseline"
        assert result[0]["severity"] == "high"
        assert "师徒关系" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_card_suggests_must_not(self):
        """卡片方向直接包含 must_not 中的禁忌关键词。"""
        dl = _make_dynamic_layer(must_not=["主角死亡"])
        cards = [_make_card(direction_text="主角死亡真相大白")]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        assert len(result) == 1
        assert result[0]["type"] == "baseline"
        assert "主角死亡" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_card_no_must_not_violation(self):
        """方向文本不直接包含 must_not 关键词时无冲突。"""
        dl = _make_dynamic_layer(must_not=["主角死亡"])
        cards = [_make_card(direction_text="主角在战斗中倒下，生死不明")]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        assert result == []

    @pytest.mark.asyncio
    async def test_card_violates_multiple_constraints(self):
        """一张卡片可能同时违反多个约束。"""
        dl = _make_dynamic_layer(
            must_hold=["魔法法则设定"],
            must_not=["引入科技", "主角死亡"],
        )
        cards = [_make_card(direction_text="主角用科技武器打破了魔法法则")]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        # must_hold + must_not 可能命中多个冲突
        assert len(result) >= 1
        assert all(c["type"] == "baseline" for c in result)

    @pytest.mark.asyncio
    async def test_multiple_cards(self):
        """多张卡片时，每一张都独立检测。"""
        dl = _make_dynamic_layer(must_hold=["和平协议"])
        cards = [
            _make_card(name="卡A", direction_text="两国签署和平协议"),
            _make_card(name="卡B", direction_text="撕毁和平协议，全面开战"),
        ]
        result = await self.service._detect_baseline_conflicts(cards, dl)
        # 只有卡B应当触发冲突
        assert len(result) == 1
        assert "卡B" in result[0]["description"]

    # ── 静态工具方法  ──────────────────────────────────────────────

    def test_text_contradicts(self):
        assert ConflictDetectionService._text_contradicts(
            "师徒决裂，反目成仇", "师徒关系"
        ) is True
        assert ConflictDetectionService._text_contradicts(
            "师徒情深，互相扶持", "师徒关系"
        ) is False
        assert ConflictDetectionService._text_contradicts(
            "销毁和平协议", "和平协议"
        ) is True

    def test_text_violates_must_not(self):
        assert ConflictDetectionService._text_violates_must_not(
            "主角在战斗中倒下，生死不明", "主角死亡"
        ) is False  # 方向文本不包含完整的关键词
        assert ConflictDetectionService._text_violates_must_not(
            "主角死亡", "主角死亡"
        ) is True


# ============================================================================
# Secret Matrix Conflict Tests
# ============================================================================


class TestSecretConflicts:
    """秘密矩阵冲突检测。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_no_card_characters_returns_empty(self):
        """卡片无角色数据时返回空。"""
        db = AsyncMock()
        cards = [_make_card(characters=[])]
        result = await self.service._detect_secret_conflicts(db, 1, cards, None)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_secrets_returns_empty(self):
        """项目中无秘密时返回空。"""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
        cards = [_make_card(characters=[{"id": "c1", "name": "张三"}])]
        result = await self.service._detect_secret_conflicts(db, 1, cards, None)
        assert result == []

    @pytest.mark.asyncio
    async def test_character_unknown_to_secret(self):
        """角色不知晓秘密却出现在方向卡片中。"""
        secret = _make_secret(
            description="张三其实是卧底",
            known_by=["李四"],
            unknown_to=["张三"],
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [secret])
        ))

        cards = [_make_card(characters=[{"id": "c1", "name": "张三"}])]
        result = await self.service._detect_secret_conflicts(db, 1, cards, None)
        assert len(result) == 1
        assert result[0]["type"] == "secret"
        assert "张三" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_character_already_knows_no_conflict(self):
        """角色已知晓秘密 → 不触发冲突。"""
        secret = _make_secret(
            description="宝藏位置",
            known_by=["张三", "李四"],
            unknown_to=[],
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [secret])
        ))
        cards = [_make_card(characters=[{"id": "c1", "name": "张三"}])]
        result = await self.service._detect_secret_conflicts(db, 1, cards, None)
        assert result == []

    @pytest.mark.asyncio
    async def test_multiple_secrets_multiple_characters(self):
        """多个秘密和多个角色 — 只有真正不知道的触发冲突。"""
        secrets = [
            _make_secret("秘密A", known_by=["A"], unknown_to=["B"]),
            _make_secret("秘密B", known_by=["B"], unknown_to=["A"]),
        ]
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: secrets)
        ))
        cards = [_make_card(characters=[
            {"id": "c1", "name": "A"},
            {"id": "c2", "name": "B"},
        ])]
        result = await self.service._detect_secret_conflicts(db, 1, cards, None)
        # A 不知秘密B，B 不知秘密A → 2 个冲突
        assert len(result) == 2
        assert all(c["type"] == "secret" for c in result)


# ============================================================================
# State Machine Conflict Tests
# ============================================================================


class TestStateMachineConflicts:
    """人物状态机冲突检测。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_no_state_requirement_returns_empty(self):
        """卡片无 state_requirement 时返回空。"""
        db = AsyncMock()
        cards = [_make_card(characters=[{"id": "c1", "name": "张三"}])]  # 无 state_requirement
        result = await self.service._detect_state_machine_conflicts(db, 1, cards)
        assert result == []

    @pytest.mark.asyncio
    async def test_character_not_in_vault_returns_empty(self):
        """角色不在 vault 中时跳过。"""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [])
        ))
        cards = [_make_card(characters=[
            {"id": "c1", "name": "张三", "state_requirement": "快乐"},
        ])]
        result = await self.service._detect_state_machine_conflicts(db, 1, cards)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_current_state_returns_empty(self):
        """角色无 current_state 时跳过（无法判断）。"""
        vc = _make_vault_character("张三", current_state=None)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [vc])
        ))
        cards = [_make_card(characters=[
            {"id": "c1", "name": "张三", "state_requirement": "快乐"},
        ])]
        result = await self.service._detect_state_machine_conflicts(db, 1, cards)
        assert result == []

    @pytest.mark.asyncio
    async def test_states_conflict_detected(self):
        """当前状态和要求状态冲突时触发。"""
        vc = _make_vault_character("张三", current_state="信任")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [vc])
        ))
        cards = [_make_card(characters=[
            {"id": "c1", "name": "张三", "state_requirement": "怀疑"},
        ])]
        result = await self.service._detect_state_machine_conflicts(db, 1, cards)
        assert len(result) == 1
        assert result[0]["type"] == "state_machine"
        assert "张三" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_compatible_state_no_conflict(self):
        """状态一致时不触发。"""
        vc = _make_vault_character("张三", current_state="平静")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [vc])
        ))
        cards = [_make_card(characters=[
            {"id": "c1", "name": "张三", "state_requirement": "平静"},
        ])]
        result = await self.service._detect_state_machine_conflicts(db, 1, cards)
        assert result == []

    def test_states_conflict_utility(self):
        """_states_conflict 静态方法测试。"""
        # 直接冲突对
        assert ConflictDetectionService._states_conflict("高兴", "悲伤") is True
        assert ConflictDetectionService._states_conflict("紧张", "松弛") is True
        assert ConflictDetectionService._states_conflict("健康", "重伤") is True
        # 兼容
        assert ConflictDetectionService._states_conflict("高兴", "高兴") is False
        assert ConflictDetectionService._states_conflict("平静", "友善") is False


# ============================================================================
# Integration: detect_conflicts 主入口
# ============================================================================


class TestDetectConflicts:
    """ConflictDetectionService.detect_conflicts 集成测试。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_empty_cards(self):
        """空卡片列表应返回无冲突（含置信度字段）。"""
        db = AsyncMock()
        result = await self.service.detect_conflicts(db, 1, "chap-1", [])
        assert result == {
            "has_conflict": False,
            "conflict_score": 0.0,
            "confidence": 1.0,
            "confidence_label": "high",
            "fallback_to_llm": False,
            "llm_verdict": None,
            "conflicts": [],
        }

    @pytest.mark.asyncio
    async def test_no_conflicts_happy_path(self):
        """无冲突场景 — 所有检测均通过，置信度应为 high。"""
        dl = _make_dynamic_layer(must_hold=["和平"], must_not=["死亡"])
        vc = _make_vault_character("张三", current_state="平静")

        db = AsyncMock()

        # dynamic_layer 查询
        db.execute = AsyncMock()
        dl_result_mock = MagicMock()
        dl_result_mock.scalar_one_or_none.return_value = dl
        db.execute.return_value = dl_result_mock

        # secret 查询 — 无 secret
        secret_result_mock = MagicMock()
        secret_result_mock.scalars.return_value.all.return_value = []
        # vault char 查询
        vc_result_mock = MagicMock()
        vc_result_mock.scalars.return_value.all.return_value = [vc]

        # 按调用顺序模拟
        db.execute.side_effect = [dl_result_mock, secret_result_mock, vc_result_mock]

        cards = [
            _make_card(
                name="和平之约",
                direction_text="两国签订和平协议",
                characters=[{"id": "c1", "name": "张三", "state_requirement": "平静"}],
            )
        ]
        result = await self.service.detect_conflicts(db, 1, "chap-1", cards)
        assert result["has_conflict"] is False
        assert result["conflict_score"] == 0.0
        assert result["conflicts"] == []
        assert result["confidence"] == 1.0
        assert result["confidence_label"] == "high"
        assert result["fallback_to_llm"] is False
        assert result["llm_verdict"] is None

    @pytest.mark.asyncio
    async def test_all_three_conflict_types(self):
        """同时触发三类冲突的集成场景 — 置信度应为 high（冲突评分 > 0.7）。"""
        dl = _make_dynamic_layer(
            must_hold=["师徒关系"],
            must_not=["主角死亡"],
        )
        secret = _make_secret(
            description="师父是叛徒",
            known_by=["反派的走狗"],
            unknown_to=["徒弟"],
        )
        vc = _make_vault_character("徒弟", current_state="信任")

        db = AsyncMock()

        dl_result = MagicMock()
        dl_result.scalar_one_or_none.return_value = dl

        secret_result = MagicMock()
        secret_result.scalars.return_value.all.return_value = [secret]

        vc_result = MagicMock()
        vc_result.scalars.return_value.all.return_value = [vc]

        db.execute.side_effect = [dl_result, secret_result, vc_result]

        cards = [
            _make_card(
                name="背叛",
                direction_text="徒弟背叛师父，师徒决裂",
                characters=[
                    {"id": "c1", "name": "徒弟", "state_requirement": "怀疑"},
                ],
            )
        ]
        result = await self.service.detect_conflicts(db, 1, "chap-1", cards)
        assert result["has_conflict"] is True
        assert result["conflict_score"] > 0.0
        # 预期: baseline(师徒决裂 vs 师徒关系) + secret(徒弟不知师父是叛徒) + state_machine(信任 vs 怀疑)
        assert len(result["conflicts"]) == 3
        types = {c["type"] for c in result["conflicts"]}
        assert types == {"baseline", "secret", "state_machine"}
        # 3 conflicts (high + medium + medium) → score ~0.6875 → confidence ~0.676 → medium
        assert result["confidence"] < 0.9
        assert result["confidence"] > 0.5
        assert result["confidence_label"] == "medium"
        assert result["fallback_to_llm"] is False

    @pytest.mark.asyncio
    async def test_db_error_returns_empty(self):
        """数据库异常时应返回空冲突结果（含容错置信度）。"""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB connection lost"))
        cards = [_make_card()]
        result = await self.service.detect_conflicts(db, 1, "chap-1", cards)
        assert result["has_conflict"] is False
        assert result["conflict_score"] == 0.0
        assert result["conflicts"] == []
        assert result["confidence"] == 0.5
        assert result["confidence_label"] == "medium"
        assert result["fallback_to_llm"] is False

    @pytest.mark.asyncio
    async def test_no_dynamic_layer_still_runs_other_checks(self):
        """动态层不存在时，基线冲突跳过，其他检测继续。"""
        vc = _make_vault_character("张三", current_state="信任")

        db = AsyncMock()

        dl_result = MagicMock()
        dl_result.scalar_one_or_none.return_value = None  # 无动态层

        secret_result = MagicMock()
        secret_result.scalars.return_value.all.return_value = []

        vc_result = MagicMock()
        vc_result.scalars.return_value.all.return_value = [vc]

        db.execute.side_effect = [dl_result, secret_result, vc_result]

        cards = [_make_card(
            characters=[{"id": "c1", "name": "张三", "state_requirement": "怀疑"}],
        )]
        result = await self.service.detect_conflicts(db, 1, "chap-1", cards)
        # baseline 跳过，state_machine 检出冲突
        assert result["has_conflict"] is True
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["type"] == "state_machine"
        assert result["confidence"] > 0.0
        assert "confidence" in result
        assert "confidence_label" in result
        assert "fallback_to_llm" in result


# ============================================================================
# 工具函数 单元测试
# ============================================================================


class TestComputeConflictScore:
    """_compute_conflict_score 分数计算。"""

    def test_no_conflicts_zero(self):
        from app.service.conflict_detection import _compute_conflict_score
        assert _compute_conflict_score([]) == 0.0

    def test_single_high(self):
        from app.service.conflict_detection import _compute_conflict_score
        score = _compute_conflict_score([{"severity": "high"}])
        assert 0.0 < score <= 1.0

    def test_multiple_increases(self):
        from app.service.conflict_detection import _compute_conflict_score
        s1 = _compute_conflict_score([{"severity": "high"}])
        s2 = _compute_conflict_score([
            {"severity": "high"},
            {"severity": "medium"},
        ])
        assert s2 > s1

    def test_unknown_severity_defaults_to_low(self):
        from app.service.conflict_detection import _compute_conflict_score
        score = _compute_conflict_score([{"severity": "unknown"}])
        assert score > 0.0


class TestConflictItem:
    """_conflict_item 工厂函数。"""

    def test_default_suggested_fix_is_none(self):
        from app.service.conflict_detection import _conflict_item
        item = _conflict_item("baseline", "描述")
        assert item["suggested_fix"] is None

    def test_fields(self):
        from app.service.conflict_detection import _conflict_item
        item = _conflict_item("secret", "秘密泄露", severity="high",
                              suggested_fix="修复方法")
        assert item["type"] == "secret"
        assert item["description"] == "秘密泄露"
        assert item["severity"] == "high"
        assert item["suggested_fix"] == "修复方法"


class TestSingleton:
    """单例模式。"""

    def test_singleton_instance(self):
        assert conflict_detection_service is not None
        assert isinstance(conflict_detection_service, ConflictDetectionService)


# ============================================================================
# 置信度评分测试 (§2.4)
# ============================================================================


class TestComputeConfidence:
    """_compute_confidence U型曲线测试。"""

    def test_zero_conflict_score_max_confidence(self):
        """极低冲突 (0.0) → 置信度应为 1.0 (high)。"""
        assert _compute_confidence(0.0) == 1.0

    def test_low_conflict_score_high_confidence(self):
        """低冲突 (0.05) → 置信度应接近 1.0 (high)。"""
        conf = _compute_confidence(0.05)
        assert conf >= 0.9
        assert _compute_confidence_label(conf) == "high"

    def test_low_zone_boundary_high_confidence(self):
        """低区域边界 (0.15) → 置信度应为 0.9 (high)。"""
        conf = _compute_confidence(0.15)
        assert conf == 0.9
        assert _compute_confidence_label(conf) == "high"

    def test_mid_low_confidence(self):
        """中等冲突 (0.45) → 置信度为最低点 0.2 (low)。"""
        conf = _compute_confidence(0.45)
        assert conf == 0.2
        assert _compute_confidence_label(conf) == "low"

    def test_mid_medium_confidence(self):
        """中等冲突 (0.3) → 置信度处于中等区域。"""
        conf = _compute_confidence(0.3)
        assert 0.3 < conf < 0.9
        assert _compute_confidence_label(conf) in ("medium", "high")

    def test_high_zone_boundary_high_confidence(self):
        """高区域边界 (0.75) → 置信度应为 0.9 (high)。"""
        conf = _compute_confidence(0.75)
        assert conf == 0.9
        assert _compute_confidence_label(conf) == "high"

    def test_high_conflict_score_max_confidence(self):
        """极高冲突 (1.0) → 置信度应为 1.0 (high)。"""
        assert _compute_confidence(1.0) == 1.0

    def test_u_curve_symmetry(self):
        """U型曲线对称性 — 等距两侧置信度应相等。"""
        left = _compute_confidence(0.3)
        right = _compute_confidence(0.6)
        assert abs(left - right) < 0.01

    def test_confidence_monotonic_left_side(self):
        """左侧单调递减 — 冲突分从 0 增加到 0.45 置信度递减。"""
        prev = _compute_confidence(0.0)
        for score in [0.1, 0.2, 0.3, 0.4, 0.45]:
            cur = _compute_confidence(score)
            assert cur <= prev, f"失败于 score={score}: cur={cur} > prev={prev}"
            prev = cur

    def test_confidence_monotonic_right_side(self):
        """右侧单调递增 — 冲突分从 0.45 增加到 1.0 置信度递增。"""
        prev = _compute_confidence(0.45)
        for score in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            cur = _compute_confidence(score)
            assert cur >= prev, f"失败于 score={score}: cur={cur} < prev={prev}"
            prev = cur


class TestConfidenceLabel:
    """_compute_confidence_label 标签映射测试。"""

    def test_high_confidence_label(self):
        """>= 0.7 → high。"""
        assert _compute_confidence_label(0.7) == "high"
        assert _compute_confidence_label(0.85) == "high"
        assert _compute_confidence_label(1.0) == "high"

    def test_medium_confidence_label(self):
        """[0.3, 0.7) → medium。"""
        assert _compute_confidence_label(0.3) == "medium"
        assert _compute_confidence_label(0.5) == "medium"
        assert _compute_confidence_label(0.69) == "medium"

    def test_low_confidence_label(self):
        """< 0.3 → low。"""
        assert _compute_confidence_label(0.0) == "low"
        assert _compute_confidence_label(0.29) == "low"
        assert _compute_confidence_label(0.1) == "low"


class TestEvaluateConfidence:
    """ConflictDetectionService.evaluate_confidence 测试。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_evaluate_high_confidence(self):
        result = await self.service.evaluate_confidence(0.0, [])
        assert result["confidence"] == 1.0
        assert result["confidence_label"] == "high"
        assert result["fallback_to_llm"] is False

    @pytest.mark.asyncio
    async def test_evaluate_low_confidence_triggers_fallback(self):
        result = await self.service.evaluate_confidence(0.45, [])
        assert result["confidence"] == 0.2
        assert result["confidence_label"] == "low"
        assert result["fallback_to_llm"] is True

    @pytest.mark.asyncio
    async def test_evaluate_medium_confidence_no_fallback(self):
        result = await self.service.evaluate_confidence(0.3, [])
        assert result["confidence_label"] == "medium"
        assert result["fallback_to_llm"] is False


class TestLlmFallback:
    """LLM fallback 机制测试。"""

    def setup_method(self):
        self.service = ConflictDetectionService()

    @pytest.mark.asyncio
    async def test_no_conflicts_skip_fallback(self):
        """无冲突时跳过 LLM fallback。"""
        result = await self.service._llm_fallback_for_conflicts(
            1, "chap-1", [], [], 0.0,
        )
        assert result is None

    @pytest.mark.asyncio
    @patch("app.service.conflict_detection.llm_client")
    async def test_llm_called_on_low_confidence(self, mock_llm):
        """低置信度时调用 LLM。"""
        mock_llm.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": json.dumps({
                "verdict": "误报",
                "confidence": 0.8,
                "reasoning": "这些冲突实际上是兼容的",
            })}}],
        })

        from app.service.conflict_detection import _compute_conflict_score, _compute_confidence
        conflicts = [
            {"type": "baseline", "description": "测试冲突", "severity": "medium"},
        ]
        score = _compute_conflict_score(conflicts)
        # score ~0.375 → confidence ~0.67 → < 0.7 but >= 0.3 → no LLM
        # We need confidence < 0.3, so we need score near 0.45
        # Test directly by calling _llm_fallback_for_conflicts
        result = await self.service._llm_fallback_for_conflicts(
            1, "chap-1",
            [_make_card(name="测试", direction_text="测试方向")],
            conflicts, 0.45,
        )
        assert result is not None
        assert result["verdict"] == "误报"
        assert result["confidence"] == 0.8
        assert result["overrides"] is True
        assert result["has_conflict"] is False

    @pytest.mark.asyncio
    @patch("app.service.conflict_detection.llm_client")
    async def test_llm_call_failure_graceful_degradation(self, mock_llm):
        """LLM 调用失败时优雅降级 — 返回 None，保持原结果。"""
        mock_llm.chat = AsyncMock(side_effect=Exception("LLM service unavailable"))

        conflicts = [
            {"type": "baseline", "description": "测试冲突", "severity": "medium"},
        ]
        result = await self.service._llm_fallback_for_conflicts(
            1, "chap-1",
            [_make_card(name="测试", direction_text="测试方向")],
            conflicts, 0.45,
        )
        assert result is None

    @pytest.mark.asyncio
    @patch("app.service.conflict_detection.llm_client")
    async def test_llm_returns_real_conflict(self, mock_llm):
        """LLM 返回真实冲突时，保持原冲突结果。"""
        mock_llm.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": json.dumps({
                "verdict": "真实",
                "confidence": 0.9,
                "reasoning": "卡片方向确实与约束冲突",
            })}}],
        })

        conflicts = [
            {"type": "baseline", "description": "测试冲突", "severity": "high"},
        ]
        result = await self.service._llm_fallback_for_conflicts(
            1, "chap-1",
            [_make_card(name="测试", direction_text="测试方向")],
            conflicts, 0.45,
        )
        assert result is not None
        assert result["verdict"] == "真实"
        assert result["overrides"] is False
        assert result["has_conflict"] is True

    @pytest.mark.asyncio
    @patch("app.service.conflict_detection.llm_client")
    async def test_llm_malformed_response(self, mock_llm):
        """LLM 返回格式异常的响应时，应解析失败但返回默认结果。"""
        mock_llm.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": "这不是JSON格式的回复"}}],
        })

        conflicts = [
            {"type": "baseline", "description": "测试冲突", "severity": "medium"},
        ]
        result = await self.service._llm_fallback_for_conflicts(
            1, "chap-1",
            [_make_card(name="测试", direction_text="测试方向")],
            conflicts, 0.45,
        )
        # 无法解析时返回默认结果（verdict="无法判断", confidence=0.5）
        assert result is not None
        assert result["verdict"] == "无法判断"
        assert result["confidence"] == 0.5
        assert result["overrides"] is False

    def test_parse_llm_response_json(self):
        """解析标准 JSON 响应。"""
        content = '{"verdict": "真实", "confidence": 0.95}'
        parsed = ConflictDetectionService._parse_llm_response(content)
        assert parsed is not None
        assert parsed["verdict"] == "真实"
        assert parsed["confidence"] == 0.95

    def test_parse_llm_response_markdown_fence(self):
        """解析 Markdown 代码围栏中的 JSON。"""
        content = '```json\n{"verdict": "误报", "confidence": 0.7}\n```'
        parsed = ConflictDetectionService._parse_llm_response(content)
        assert parsed is not None
        assert parsed["verdict"] == "误报"

    def test_parse_llm_response_empty(self):
        """空内容返回 None。"""
        assert ConflictDetectionService._parse_llm_response("") is None
        assert ConflictDetectionService._parse_llm_response(None) is None
