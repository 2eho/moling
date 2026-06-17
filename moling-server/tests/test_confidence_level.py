"""墨灵 (Moling) — P1-4 置信度降级策略单元测试.

测试 ConfidenceLevel 枚举、evaluate_confidence、should_auto_apply、
MergeResult/ChangeEntry 置信度字段、及 Phase4 集成。
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.merge_service import (
    ChangeEntry,
    ConfidenceLevel,
    MergeResult,
    evaluate_confidence,
    should_auto_apply,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    CONFIDENCE_LOW_THRESHOLD,
)
from app.service.phase4_service import Phase4Service


# ====================================================================
# 1-4: 4 级区间边界值测试
# ====================================================================


class TestConfidenceBoundaries:
    """4 级置信度区间边界值测试。"""

    @pytest.mark.parametrize("score", [
        0.81, 0.9, 0.95, 1.0,
        CONFIDENCE_HIGH_THRESHOLD + 0.01,
        0.99,
    ])
    def test_confidence_high_above_08(self, score: float):
        """[1] > 0.8 → HIGH"""
        assert evaluate_confidence(score) == ConfidenceLevel.HIGH

    @pytest.mark.parametrize("score", [
        0.5, 0.6, 0.7, 0.79, 0.8,
        CONFIDENCE_MEDIUM_THRESHOLD,
        CONFIDENCE_HIGH_THRESHOLD,
    ])
    def test_confidence_medium_05_to_08(self, score: float):
        """[2] 0.5-0.8 → MEDIUM"""
        assert evaluate_confidence(score) == ConfidenceLevel.MEDIUM

    @pytest.mark.parametrize("score", [
        0.3, 0.35, 0.4, 0.45, 0.49,
        CONFIDENCE_LOW_THRESHOLD,
        CONFIDENCE_MEDIUM_THRESHOLD - 0.01,
    ])
    def test_confidence_low_03_to_05(self, score: float):
        """[3] 0.3-0.5 → LOW"""
        assert evaluate_confidence(score) == ConfidenceLevel.LOW

    @pytest.mark.parametrize("score", [
        0.0, 0.1, 0.2, 0.29,
        CONFIDENCE_LOW_THRESHOLD - 0.01,
        -0.1,
    ])
    def test_confidence_reject_below_03(self, score: float):
        """[4] < 0.3 → REJECT"""
        assert evaluate_confidence(score) == ConfidenceLevel.REJECT


# ====================================================================
# 5-8: 自动应用 / 需审核 / 忽略
# ====================================================================


class TestAutoApply:
    """should_auto_apply 行为测试。"""

    def test_high_auto_apply(self):
        """[5] HIGH → 自动入库"""
        assert should_auto_apply(ConfidenceLevel.HIGH) is True

    def test_medium_auto_apply(self):
        """[6] MEDIUM → 自动入库（后台标记）"""
        assert should_auto_apply(ConfidenceLevel.MEDIUM) is True

    def test_low_requires_confirmation(self):
        """[7] LOW → 不自动入库，需弹窗确认"""
        assert should_auto_apply(ConfidenceLevel.LOW) is False

    def test_reject_ignored(self):
        """[8] REJECT → 忽略"""
        assert should_auto_apply(ConfidenceLevel.REJECT) is False


# ====================================================================
# 9: MergeResult 置信度评估
# ====================================================================


class TestMergeResultConfidence:
    """MergeResult 整体置信度计算测试。"""

    def test_average_confidence_high(self):
        """多个 HIGH 条目 → 整体 HIGH。"""
        result = MergeResult(entity_type="character")
        result.changes = [
            ChangeEntry(
                entity_type="character", entity_id="1", entity_name="林峰",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.95, change_reason="新建",
            ),
            ChangeEntry(
                entity_type="character", entity_id="2", entity_name="苏暮雪",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.9, change_reason="新建",
            ),
        ]
        from app.service.merge_service import MergeService
        MergeService._evaluate_merge_confidence(result)

        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.auto_applied is True
        assert len(result.items_requiring_review) == 0

    def test_mixed_confidence_levels(self):
        """[11] 混合置信度条目 → 正确识别需审核条目。"""
        result = MergeResult(entity_type="character")
        result.changes = [
            ChangeEntry(
                entity_type="character", entity_id="1", entity_name="林峰",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.95, change_reason="新建",
            ),
            ChangeEntry(
                entity_type="character", entity_id="2", entity_name="模糊匹配人物",
                change_type="update", old_value="old", new_value="new",
                chapter=1, confidence=0.35, change_reason="模糊匹配",
            ),
            ChangeEntry(
                entity_type="character", entity_id="3", entity_name="低置信条目",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.4, change_reason="新建",
            ),
        ]
        from app.service.merge_service import MergeService
        MergeService._evaluate_merge_confidence(result)

        # 平均置信度 = (0.95 + 0.35 + 0.4) / 3 ≈ 0.567 → MEDIUM
        assert result.confidence_level == ConfidenceLevel.MEDIUM
        assert result.auto_applied is True
        # 应该有 2 个 LOW 条目需要审核
        assert len(result.items_requiring_review) == 2
        for item in result.items_requiring_review:
            assert item.confidence_level == ConfidenceLevel.LOW
            assert item.confidence < CONFIDENCE_MEDIUM_THRESHOLD

    def test_empty_changes_default_high(self):
        """[10] 空变更列表 → 默认 HIGH，自动入库。"""
        result = MergeResult(entity_type="character")
        from app.service.merge_service import MergeService
        MergeService._evaluate_merge_confidence(result)

        assert result.confidence_level == ConfidenceLevel.HIGH
        assert result.auto_applied is True
        assert result.items_requiring_review == []

    def test_single_low_item_determines_auto_applied(self):
        """只有一个 LOW 条目 → 不自动入库。"""
        result = MergeResult(entity_type="character")
        result.changes = [
            ChangeEntry(
                entity_type="character", entity_id="1", entity_name="模糊匹配",
                change_type="update", old_value="old", new_value="new",
                chapter=1, confidence=0.3, change_reason="模糊匹配",
            ),
        ]
        from app.service.merge_service import MergeService
        MergeService._evaluate_merge_confidence(result)

        assert result.confidence_level == ConfidenceLevel.LOW
        assert result.auto_applied is False
        assert len(result.items_requiring_review) == 1

    def test_all_rejected_items(self):
        """全部 REJECT 条目 → 不自动入库。"""
        result = MergeResult(entity_type="character")
        result.changes = [
            ChangeEntry(
                entity_type="character", entity_id="1", entity_name="噪音1",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.1, change_reason="噪音",
            ),
            ChangeEntry(
                entity_type="character", entity_id="2", entity_name="噪音2",
                change_type="create", old_value=None, new_value=None,
                chapter=1, confidence=0.2, change_reason="噪音",
            ),
        ]
        from app.service.merge_service import MergeService
        MergeService._evaluate_merge_confidence(result)

        assert result.confidence_level == ConfidenceLevel.REJECT
        assert result.auto_applied is False
        # LOW 和 REJECT 中，REJECT 级别条目不进入 items_requiring_review
        # （只有 LOW 需要审核）
        assert len(result.items_requiring_review) == 0


# ====================================================================
# ChangeEntry / MergeResult 字段存在性测试
# ====================================================================


class TestConfidenceFieldsExist:
    """[12] 前端过滤字段存在性测试。"""

    def test_change_entry_has_confidence_level(self):
        """ChangeEntry 有 confidence_level 字段，默认为 None。"""
        entry = ChangeEntry(
            entity_type="character", entity_id="1", entity_name="林峰",
            change_type="create", old_value=None, new_value=None,
            chapter=1, confidence=0.9, change_reason="新建",
        )
        # 新增字段存在且默认为 None
        assert hasattr(entry, "confidence_level")
        assert entry.confidence_level is None

        # 赋值后正确存储
        entry.confidence_level = ConfidenceLevel.HIGH
        assert entry.confidence_level == ConfidenceLevel.HIGH

    def test_merge_result_has_confidence_fields(self):
        """MergeResult 有 confidence_level / auto_applied / items_requiring_review。"""
        result = MergeResult(entity_type="character")
        assert hasattr(result, "confidence_level")
        assert hasattr(result, "auto_applied")
        assert hasattr(result, "items_requiring_review")

        # 默认值
        assert result.confidence_level is None
        assert result.auto_applied is False
        assert result.items_requiring_review == []

    def test_change_entry_backward_compatible(self):
        """ChangeEntry 现有字段不变，新增字段可选。"""
        # 不传 confidence_level 也能正常创建
        entry = ChangeEntry(
            entity_type="character", entity_id="1", entity_name="林峰",
            change_type="update", old_value="旧值", new_value="新值",
            chapter=5, confidence=0.9, change_reason="更新",
        )
        assert entry.confidence == 0.9
        assert entry.entity_type == "character"
        assert entry.change_type == "update"


# ====================================================================
# Phase4 集成测试
# ====================================================================


class TestPhase4ConfidenceIntegration:
    """Phase4 置信度评估集成测试。"""

    def test_evaluate_phase4_confidence_high(self):
        """全部 HIGH 置信度条目 → 整体 HIGH。"""
        changes = {
            "characters": {
                "created": [
                    {"id": "1", "name": "林峰", "confidence": 0.95},
                    {"id": "2", "name": "苏暮雪", "confidence": 0.9},
                ],
                "updated": [],
                "status_changed": [],
            },
            "timeline": {"added": 2},
            "plot_promises": {"created": 1, "advanced": 0, "redeemed": 0},
            "world": {"created": 1, "expanded": 0},
            "card_pool": {"added": 2},
        }
        result = Phase4Service._evaluate_phase4_confidence(changes)
        assert result["level"] == "high"
        assert result["auto_applied"] is True
        assert len(result["items_requiring_review"]) == 0

    def test_evaluate_phase4_confidence_mixed(self):
        """混合置信度 → 需审核条目正确识别。"""
        changes = {
            "characters": {
                "created": [
                    {"id": "1", "name": "林峰", "confidence": 0.95},
                ],
                "updated": [
                    {"id": "2", "name": "模糊人物", "confidence": 0.35},
                ],
                "status_changed": [
                    {"id": "3", "name": "更改状态", "confidence": 0.4},
                ],
            },
            "timeline": {"added": 0},
            "plot_promises": {"created": 0, "advanced": 0, "redeemed": 0},
            "world": {"created": 0, "expanded": 0},
            "card_pool": {"added": 0},
        }
        result = Phase4Service._evaluate_phase4_confidence(changes)
        assert len(result["items_requiring_review"]) == 2
        for item in result["items_requiring_review"]:
            assert item["confidence"] < CONFIDENCE_MEDIUM_THRESHOLD
            assert item["confidence_level"] == "low"

    def test_evaluate_phase4_confidence_empty(self):
        """无变更 → 整体 HIGH。"""
        changes = {
            "characters": {"created": [], "updated": [], "status_changed": []},
            "timeline": {"added": 0},
            "plot_promises": {"created": 0, "advanced": 0, "redeemed": 0},
            "world": {"created": 0, "expanded": 0},
            "card_pool": {"added": 0},
        }
        result = Phase4Service._evaluate_phase4_confidence(changes)
        assert result["level"] == "high"
        assert result["auto_applied"] is True
        assert result["items_requiring_review"] == []
        assert result["total_items"] == 0

    def test_character_items_get_confidence_level(self):
        """角色变更条目自动获得 confidence_level 字段。"""
        changes = {
            "characters": {
                "created": [
                    {"id": "1", "name": "林峰", "confidence": 0.95},
                    {"id": "2", "name": "龙套", "confidence": 0.3},
                ],
                "updated": [],
                "status_changed": [],
            },
            "timeline": {"added": 0},
            "plot_promises": {"created": 0, "advanced": 0, "redeemed": 0},
            "world": {"created": 0, "expanded": 0},
            "card_pool": {"added": 0},
        }
        result = Phase4Service._evaluate_phase4_confidence(changes)
        # 验证条目被注入了 confidence_level
        created_items = changes["characters"]["created"]
        assert created_items[0]["confidence_level"] == "high"
        assert created_items[1]["confidence_level"] == "low"


# ====================================================================
# 额外的边界条件测试
# ====================================================================


class TestConfidenceEdgeCases:
    """边界值和极端输入测试。"""

    def test_confidence_exact_thresholds(self):
        """精确边界值测试。"""
        # 0.8 → MEDIUM（>= 0.5 且 <= 0.8）
        assert evaluate_confidence(0.8) == ConfidenceLevel.MEDIUM
        # 0.5 → MEDIUM（>= 0.5）
        assert evaluate_confidence(0.5) == ConfidenceLevel.MEDIUM
        # 0.3 → LOW（>= 0.3）
        assert evaluate_confidence(0.3) == ConfidenceLevel.LOW
        # 0.0 → REJECT
        assert evaluate_confidence(0.0) == ConfidenceLevel.REJECT

    def test_confidence_negative(self):
        """负值 → REJECT。"""
        assert evaluate_confidence(-0.5) == ConfidenceLevel.REJECT

    def test_confidence_above_one(self):
        """> 1.0 → 仍按 HIGH 处理（浮点溢出）。"""
        assert evaluate_confidence(1.5) == ConfidenceLevel.HIGH
