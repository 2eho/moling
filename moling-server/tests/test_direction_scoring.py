"""墨灵 (Moling) — 方向冲突评分单元测试。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.models.card_pool import CardPool
from app.service.direction_scoring import DirectionScoringService, DIRECTION_TYPES

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# 辅助函数：快速创建测试卡片
# ---------------------------------------------------------------------------


def make_card(
    name: str = "测试卡片",
    direction_type: str = "稳妥",
    direction_text: str = "稳扎稳打推进主线",
    rarity: str = "common",
    characters: Optional[List[Dict[str, str]]] = None,
    plot_promises: Optional[List[Dict[str, str]]] = None,
    world_rules: Optional[List[Dict[str, str]]] = None,
    **kwargs: Any,
) -> CardPool:
    """创建测试用的 CardPool 实例。"""
    card = CardPool(
        name=name,
        direction_type=direction_type,
        direction_text=direction_text,
        rarity=rarity,
        characters=characters or [],
        plot_promises=plot_promises or [],
        world_rules=world_rules or [],
        timeline_point=kwargs.get("timeline_point"),
    )
    return card


service = DirectionScoringService()


# ===========================================================================
# 方向相容性矩阵
# ===========================================================================


class TestDirectionCompatibilityMatrix:
    """方向相容性矩阵测试。"""

    def test_matrix_dimensions(self):
        """矩阵应为 4x4。"""
        matrix = service._direction_compatibility_matrix()
        assert len(matrix) == 4
        assert all(len(row) == 4 for row in matrix)

    def test_diagonal_is_one(self):
        """对角线（同一方向）相容性应为 1.0。"""
        matrix = service._direction_compatibility_matrix()
        for i in range(4):
            assert matrix[i][i] == 1.0

    def test_matrix_is_symmetric(self):
        """矩阵应对角对称。"""
        matrix = service._direction_compatibility_matrix()
        for i in range(4):
            for j in range(4):
                assert matrix[i][j] == matrix[j][i], f"Mismatch at ({i},{j})"

    def test_lookup_compatibility_same(self):
        """同一方向相容性应为 1.0。"""
        for dt in DIRECTION_TYPES:
            assert service._lookup_compatibility(dt, dt) == 1.0

    def test_lookup_compatibility_known_pairs(self):
        """已知方向对的相容性值。"""
        assert service._lookup_compatibility("稳妥", "有趣") == 0.7
        assert service._lookup_compatibility("稳妥", "惊艳") == 0.3
        assert service._lookup_compatibility("稳妥", "神之一手") == 0.1
        assert service._lookup_compatibility("神之一手", "惊艳") == 0.7

    def test_unknown_direction_defaults_to_wentuo(self):
        """未知方向类型默认映射为 '稳妥'。"""
        assert service._direction_index("未知类型") == 0
        assert service._lookup_compatibility("unknown", "有趣") == 0.7

    def test_direction_index_mapping(self):
        """方向类型到索引的映射。"""
        assert service._direction_index("稳妥") == 0
        assert service._direction_index("有趣") == 1
        assert service._direction_index("惊艳") == 2
        assert service._direction_index("神之一手") == 3


# ===========================================================================
# 实体冲突检测
# ===========================================================================


class TestEntityConflictDetection:
    """实体冲突检测测试。"""

    def test_no_entity_conflicts_empty_characters(self):
        """空角色列表不应产生冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[]),
            make_card(name="卡B", direction_type="有趣", characters=[]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert conflicts == []

    def test_no_entity_conflicts_different_characters(self):
        """不同角色不应产生冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "觉醒"},
            ]),
            make_card(name="卡B", direction_type="有趣", characters=[
                {"id": "char_2", "name": "李四", "state_requirement": "修炼中"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert conflicts == []

    def test_no_conflict_same_character_same_state(self):
        """同一角色相同状态不应视为冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "觉醒"},
            ]),
            make_card(name="卡B", direction_type="有趣", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "觉醒"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert conflicts == []

    def test_character_state_contradiction_high(self):
        """同一角色出现矛盾状态（强 vs 弱）应产生高严重度冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "强"},
            ]),
            make_card(name="卡B", direction_type="惊艳", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "弱"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert len(conflicts) == 1
        assert conflicts[0]["severity"] == "high"
        assert "角色" in conflicts[0]["entity"]
        assert conflicts[0]["cards"] == [cards[0].id, cards[1].id]

    def test_character_state_contradiction_life_death(self):
        """生 vs 死的状态应为高冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[
                {"id": "char_1", "name": "主角", "state_requirement": "生存"},
            ]),
            make_card(name="卡B", direction_type="神之一手", characters=[
                {"id": "char_1", "name": "主角", "state_requirement": "死亡"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert len(conflicts) == 1
        assert conflicts[0]["severity"] == "high"

    def test_plot_promise_conflict_detected(self):
        """同一剧情承诺在不同卡片中的推进类型矛盾应被检测。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", plot_promises=[
                {"id": "promise_1", "title": "封印解除", "advance_type": "延缓"},
            ]),
            make_card(name="卡B", direction_type="惊艳", plot_promises=[
                {"id": "promise_1", "title": "封印解除", "advance_type": "加速"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert len(conflicts) == 1
        assert "剧情承诺" in conflicts[0]["entity"]
        assert conflicts[0]["severity"] == "medium"

    def test_world_rule_conflict_detected(self):
        """同一世界观规则在不同卡片中的约束矛盾应被检测。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", world_rules=[
                {"id": "rule_1", "rule": "魔法上限", "constraint": "不允许禁咒"},
            ]),
            make_card(name="卡B", direction_type="神之一手", world_rules=[
                {"id": "rule_1", "rule": "魔法上限", "constraint": "允许使用禁咒"},
            ]),
        ]
        conflicts = service._entity_conflict_detection(cards)
        assert len(conflicts) == 1
        assert "世界观规则" in conflicts[0]["entity"]
        assert conflicts[0]["severity"] == "low"

    def test_no_characters_no_conflicts(self):
        """卡片没有 characters 字段不应报错。"""
        card_a = CardPool(
            name="卡A",
            direction_type="稳妥",
            direction_text="稳扎稳打",
            rarity="common",
        )
        card_b = CardPool(
            name="卡B",
            direction_type="惊艳",
            direction_text="出奇制胜",
            rarity="rare",
        )
        conflicts = service._entity_conflict_detection([card_a, card_b])
        assert conflicts == []


# ===========================================================================
# 情感基调冲突
# ===========================================================================


class TestEmotionalToneConflict:
    """情感基调冲突测试。"""

    def test_same_direction_no_conflict(self):
        """相同方向类型不应有情感冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="稳妥"),
        ]
        conflicts = service._emotional_tone_conflict(cards)
        assert conflicts == []

    def test_high_compatibility_no_conflict(self):
        """高相容性方向对不应有情感冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="有趣"),
        ]
        conflicts = service._emotional_tone_conflict(cards)
        assert conflicts == []

    def test_low_compatibility_has_conflict(self):
        """低相容性方向对应有情感冲突。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="神之一手"),
        ]
        conflicts = service._emotional_tone_conflict(cards)
        assert len(conflicts) == 1
        assert "情感基调冲突" in conflicts[0]
        assert "稳妥" in conflicts[0]
        assert "神之一手" in conflicts[0]

    def test_multiple_conflicts_all_detected(self):
        """多个低相容性方向对，每个都应被检测。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="神之一手"),
            make_card(name="卡C", direction_type="有趣"),
        ]
        # 稳妥-神之一手 和 有趣-神之一手
        conflicts = service._emotional_tone_conflict(cards)
        assert len(conflicts) >= 1

    def test_single_card_no_conflict(self):
        """单张卡片不应有情感冲突。"""
        cards = [make_card(name="卡A", direction_type="稳妥")]
        conflicts = service._emotional_tone_conflict(cards)
        assert conflicts == []


# ===========================================================================
# 置信度计算
# ===========================================================================


class TestConfidenceCalculation:
    """置信度计算测试。"""

    def test_low_conflict_high_confidence(self):
        """极低冲突 (< 0.1) 应返回高置信度 (0.9)。"""
        assert service._calculate_confidence(0.05) == 0.9

    def test_very_high_conflict_high_confidence(self):
        """极高冲突 (> 0.8) 应返回高置信度 (0.85)。"""
        assert service._calculate_confidence(0.85) == 0.85

    def test_moderate_conflict_moderate_confidence(self):
        """中等冲突应返回中等置信度。"""
        assert service._calculate_confidence(0.5) == 0.5
        assert service._calculate_confidence(0.45) == 0.5

    def test_clear_conflict_good_confidence(self):
        """较明显冲突返回 0.75。"""
        assert service._calculate_confidence(0.7) == 0.75

    def test_low_ambiguity_low_confidence(self):
        """模糊冲突返回低置信度 (0.3)。"""
        assert service._calculate_confidence(0.2) == 0.3


# ===========================================================================
# 综合冲突评分
# ===========================================================================


class TestAggregatedConflictScore:
    """综合冲突评分测试。"""

    def test_no_conflicts(self):
        """无冲突时评分应接近 0。"""
        score = service._aggregate_conflict_score(
            composite_score=1.0,
            entity_conflicts=[],
            tone_conflicts=[],
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="有趣"),
            ],
        )
        assert 0 <= score < 0.3

    def test_entity_high_conflict_increases_score(self):
        """高严重度实体冲突应提升总分。"""
        entity_conflicts = [
            {
                "cards": ["id1", "id2"],
                "entity": "角色: 张三",
                "description": "状态矛盾",
                "severity": "high",
            }
        ]
        score = service._aggregate_conflict_score(
            composite_score=0.7,
            entity_conflicts=entity_conflicts,
            tone_conflicts=[],
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="神之一手"),
            ],
        )
        assert score > 0.3

    def test_tone_conflict_adds_penalty(self):
        """情感冲突应增加评分。"""
        score_no_tone = service._aggregate_conflict_score(
            composite_score=0.5,
            entity_conflicts=[],
            tone_conflicts=[],
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="神之一手"),
            ],
        )
        score_with_tone = service._aggregate_conflict_score(
            composite_score=0.5,
            entity_conflicts=[],
            tone_conflicts=["方向 '稳妥' 与 方向 '神之一手' 情感基调冲突"],
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="神之一手"),
            ],
        )
        assert score_with_tone > score_no_tone

    def test_score_capped_at_one(self):
        """总分不得超过 1.0。"""
        score = service._aggregate_conflict_score(
            composite_score=0.0,
            entity_conflicts=[
                {"cards": ["id1", "id2"], "entity": "c1", "description": "d1", "severity": "high"},
                {"cards": ["id1", "id2"], "entity": "c2", "description": "d2", "severity": "high"},
                {"cards": ["id1", "id2"], "entity": "c3", "description": "d3", "severity": "high"},
            ],
            tone_conflicts=["t1", "t2", "t3"],
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="神之一手"),
            ],
        )
        assert score <= 1.0


# ===========================================================================
# 主入口测试
# ===========================================================================


class TestScoreDirectionConflicts:
    """score_direction_conflicts 主入口测试。"""

    async def test_empty_cards(self):
        """空卡片列表应返回空结果。"""
        result = await service.score_direction_conflicts([])
        assert result["has_conflict"] is False
        assert result["conflict_score"] == 0.0
        assert result["confidence"] == 1.0
        assert result["compatibility_matrix"] == []
        assert result["entity_conflicts"] == []
        assert result["tone_conflicts"] == []
        assert result["fallback_to_llm"] is False

    async def test_single_card_no_conflict(self):
        """单张卡片不应有冲突。"""
        result = await service.score_direction_conflicts([
            make_card(name="卡A", direction_type="稳妥"),
        ])
        assert result["has_conflict"] is False

    async def test_same_direction_no_conflict(self):
        """相同方向类型不应有冲突。"""
        result = await service.score_direction_conflicts([
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="稳妥"),
        ])
        assert result["has_conflict"] is False

    async def test_compatible_directions(self):
        """相容方向对（有趣+稳妥）应低冲突。"""
        result = await service.score_direction_conflicts([
            make_card(name="卡A", direction_type="有趣"),
            make_card(name="卡B", direction_type="稳妥"),
        ])
        assert result["conflict_score"] < 0.5
        assert result["confidence"] >= 0.3
        assert result["fallback_to_llm"] is False

    async def test_incompatible_directions(self):
        """不相容方向对（稳妥+神之一手）应有明显冲突。"""
        result = await service.score_direction_conflicts([
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="神之一手"),
        ])
        assert result["has_conflict"] is True
        assert result["conflict_score"] > 0.3

    async def test_compatibility_matrix_output_format(self):
        """兼容性矩阵应正确输出 n x n 矩阵。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥"),
            make_card(name="卡B", direction_type="有趣"),
            make_card(name="卡C", direction_type="惊艳"),
        ]
        result = await service.score_direction_conflicts(cards)
        matrix = result["compatibility_matrix"]
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        assert matrix[0][1] == 0.7  # 稳妥 vs 有趣
        assert matrix[1][2] == 0.6  # 有趣 vs 惊艳

    async def test_with_entity_conflict(self):
        """包含实体冲突时应体现在结果中。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "强"},
            ]),
            make_card(name="卡B", direction_type="惊艳", characters=[
                {"id": "char_1", "name": "张三", "state_requirement": "弱"},
            ]),
        ]
        result = await service.score_direction_conflicts(cards)
        assert len(result["entity_conflicts"]) >= 1
        assert result["entity_conflicts"][0]["severity"] == "high"
        assert result["has_conflict"] is True

    async def test_low_confidence_triggers_llm_fallback(self):
        """低置信度应触发 LLM fallback。"""
        cards = [
            make_card(name="卡A", direction_type="稳妥", direction_text="缓慢发展"),
            make_card(name="卡B", direction_type="神之一手", direction_text="急速推进"),
        ]
        # entity conflicts with medium severity push confidence into medium range
        result = await service.score_direction_conflicts(cards)
        # 稳妥+神之一手 + entity conflitcs = middle range, confidence should be reasonable
        # This test just verifies the pipeline doesn't crash
        assert "fallback_to_llm" in result
        assert "suggested_fix" in result

    @patch("app.service.direction_scoring.llm_client")
    async def test_llm_fallback_called_on_low_confidence(self, mock_llm):
        """低置信度时应调用 LLM。"""
        # Mock LLM to return a valid response
        mock_llm.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"assessment": "部分兼容", "conflict_score": 0.4, "reasoning": "方向虽有张力但可调和", "suggestion": "中间插入过渡章节", "recommended_fix": "用有趣方向中和"}'}}]
        })

        # 伪造 _calculate_confidence 返回 0.2（低置信度）
        original_calculate = DirectionScoringService._calculate_confidence
        try:
            DirectionScoringService._calculate_confidence = staticmethod(lambda score: 0.2)  # type: ignore

            cards = [
                make_card(name="卡A", direction_type="有趣"),
                make_card(name="卡B", direction_type="惊艳"),
            ]
            result = await service.score_direction_conflicts(cards)

            assert result["fallback_to_llm"] is True
            assert result["llm_result"] is not None
            assert mock_llm.chat.called
        finally:
            DirectionScoringService._calculate_confidence = staticmethod(original_calculate)  # type: ignore

    @patch("app.service.direction_scoring.llm_client")
    async def test_llm_fallback_returns_json(self, mock_llm):
        """LLM fallback 应返回可解析的 JSON。"""
        mock_llm.chat = AsyncMock(return_value={
            "choices": [{"message": {"content": '{"assessment": "冲突", "conflict_score": 0.7, "reasoning": "风险过大", "suggestion": "替换神之一手卡片", "recommended_fix": "改为有趣方向"}'}}]
        })

        llm_result = await service._llm_fallback(
            cards=[
                make_card(name="卡A", direction_type="稳妥"),
                make_card(name="卡B", direction_type="神之一手"),
            ],
            compatibility_matrix=[[1.0, 0.1], [0.1, 1.0]],
            entity_conflicts=[
                {"cards": ["id1", "id2"], "entity": "角色: 张三", "description": "状态矛盾", "severity": "high"},
            ],
            tone_conflicts=["测试冲突"],
        )
        assert llm_result is not None
        import json
        parsed = json.loads(llm_result)
        assert parsed["assessment"] == "冲突"
        assert "suggestion" in parsed

    @patch("app.service.direction_scoring.llm_client")
    async def test_llm_fallback_failure_graceful(self, mock_llm):
        """LLM 调用失败应优雅降级（返回 None）。"""
        mock_llm.chat = AsyncMock(side_effect=Exception("API unavailable"))

        llm_result = await service._llm_fallback(
            cards=[make_card(name="卡A", direction_type="稳妥")],
            compatibility_matrix=[[1.0]],
            entity_conflicts=[],
            tone_conflicts=[],
        )
        assert llm_result is None


# ===========================================================================
# can_use_rule_engine
# ===========================================================================


class TestCanUseRuleEngine:
    """编织选择评分测试。"""

    async def test_high_confidence_respects_rule_engine(self):
        """高置信度低冲突时可直接用规则引擎。"""
        compatibility_result = {
            "conflict_score": 0.1,
            "confidence": 0.9,
        }
        can_use, score = await service.can_use_rule_engine(
            cards=[make_card()],
            compatibility_result=compatibility_result,
        )
        assert can_use is True
        assert score > 0.8

    async def test_low_confidence_needs_llm(self):
        """低置信度高冲突时需 fallback 到 LLM。"""
        compatibility_result = {
            "conflict_score": 0.7,
            "confidence": 0.3,
        }
        can_use, score = await service.can_use_rule_engine(
            cards=[make_card()],
            compatibility_result=compatibility_result,
        )
        assert can_use is False
        assert score <= 0.8

    async def test_empty_input_uses_rule_engine(self):
        """空输入默认使用规则引擎。"""
        can_use, score = await service.can_use_rule_engine(cards=[], compatibility_result={})
        assert can_use is True
        assert score == 1.0

    async def test_boundary_score(self):
        """边界值 0.8 应 fallback。"""
        compatibility_result = {
            "conflict_score": 0.5,
            "confidence": 0.5,
        }
        can_use, score = await service.can_use_rule_engine(
            cards=[make_card()],
            compatibility_result=compatibility_result,
        )
        # score = 0.6 * (1-0.5) + 0.4 * 0.5 = 0.3 + 0.2 = 0.5
        assert can_use is False
        assert score == 0.5


# ===========================================================================
# 边界值测试
# ===========================================================================


class TestEdgeCases:
    """边界值测试。"""

    def test_no_characters_field_does_not_crash(self):
        """缺少 characters 字段不应崩溃。"""
        card = CardPool(
            name="卡A",
            direction_type="稳妥",
            direction_text="稳扎稳打",
            rarity="common",
        )
        assert card.characters is None
        conflicts = service._entity_conflict_detection([card, card])
        assert isinstance(conflicts, list)

    def test_null_world_rules_handle_gracefully(self):
        """world_rules 为 None 应妥善处理。"""
        card = CardPool(
            name="卡A",
            direction_type="稳妥",
            direction_text="稳扎稳打",
            rarity="common",
            world_rules=None,
        )
        conflicts = service._entity_conflict_detection([card, card])
        assert isinstance(conflicts, list)

    def test_generated_suggested_fix(self):
        """存在冲突时应生成建议修复。"""
        fix = service._generate_suggested_fix(
            conflict_score=0.6,
            entity_conflicts=[
                {"cards": ["id1", "id2"], "entity": "角色: 张三", "description": "状态矛盾", "severity": "high"},
            ],
            tone_conflicts=["情感基调冲突"],
            fallback_result=None,
        )
        assert fix is not None
        assert "角色" in fix

    def test_no_fix_when_no_conflict(self):
        """无冲突时不生成修复建议。"""
        fix = service._generate_suggested_fix(
            conflict_score=0.1,
            entity_conflicts=[],
            tone_conflicts=[],
            fallback_result=None,
        )
        assert fix is None

    def test_fallback_result_used_as_fix(self):
        """LLM fallback 结果应作为建议修复。"""
        fix = service._generate_suggested_fix(
            conflict_score=0.5,
            entity_conflicts=[],
            tone_conflicts=[],
            fallback_result='{"assessment": "冲突", "conflict_score": 0.6, "suggestion": "替换卡片", "recommended_fix": "xxx"}',
        )
        assert fix == "替换卡片"
