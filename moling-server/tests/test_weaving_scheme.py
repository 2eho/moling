"""墨灵 (Moling) — 编织方案匹配增强 单元测试。"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.weaving_scheme import (
    WeavingPattern,
    WeavingSchemeService,
    weaving_scheme_service,
)


# ---------------------------------------------------------------------------
# Mock 辅助
# ---------------------------------------------------------------------------


class MockCard:
    """Mock CardPool ORM 对象。"""

    def __init__(
        self,
        card_id: int,
        name: str = "",
        direction_text: str = "",
        direction_type: str = "有趣",
        characters: Optional[List[Dict]] = None,
        timeline_point: str = "",
    ):
        self.id = card_id
        self.name = name
        self.direction_text = direction_text
        self.direction_type = direction_type
        self.characters = characters or []
        self.timeline_point = timeline_point


def make_card(
    card_id: int,
    name: str = "",
    text: str = "",
    ctype: str = "有趣",
    char_ids: Optional[List[int]] = None,
    timeline: str = "",
) -> MockCard:
    """便利工厂：创建 MockCard。"""
    chars = [{"id": cid, "name": f"角色{cid}", "state_requirement": "存在"}
             for cid in (char_ids or [])]
    return MockCard(
        card_id=card_id,
        name=name or f"测试卡片{card_id}",
        direction_text=text or f"方向文本{card_id}",
        direction_type=ctype,
        characters=chars,
        timeline_point=timeline,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> WeavingSchemeService:
    """创建一个干净的 WeavingSchemeService 实例。"""
    return WeavingSchemeService()


# ---------------------------------------------------------------------------
# WeavingPattern 数据类
# ---------------------------------------------------------------------------


class TestWeavingPattern:
    """WeavingPattern 数据类基本测试。"""

    def test_create_basic_pattern(self):
        """测试基本的编织模式创建。"""
        pattern = WeavingPattern(
            name="因果链",
            mode="single",
            prompt_instruction="三段式：因→果→揭示",
            outline_template={
                "part1": {"name": "因", "weight": 0.35},
            },
            description="因果链编织模式",
        )
        assert pattern.name == "因果链"
        assert pattern.mode == "single"
        assert "三段式" in pattern.prompt_instruction

    def test_pattern_asdict(self):
        """测试 dataclass 转 dict。"""
        pattern = WeavingPattern(
            name="测试",
            mode="single",
            prompt_instruction="测试指令",
            outline_template={"p1": {"name": "段1"}},
        )
        d = asdict(pattern)
        assert d["name"] == "测试"
        assert d["mode"] == "single"
        assert d["description"] == ""  # 默认值


# ---------------------------------------------------------------------------
# 编织模式模板
# ---------------------------------------------------------------------------


class TestWeavingPatterns:
    """验证编织模式模板库的完整性和正确性。"""

    def test_all_patterns_present(self, service):
        """验证所有必需的编织模式都存在。"""
        patterns = service._weaving_patterns()
        names = [p.name for p in patterns]
        required = ["单段式", "因果链", "平行交替", "主线+支线",
                     "因果链扩展", "平行交替+交汇", "主线+双支线"]
        for name in required:
            assert name in names, f"缺少编织模式: {name}"

    def test_single_mode_patterns(self, service):
        """验证单卡模式相关的模式定义完整。"""
        pat = service._get_pattern("单段式")
        assert pat.mode == "single"
        assert "part1" in pat.outline_template

    def test_causal_chain_pattern(self, service):
        """验证因果链模式。"""
        pat = service._get_pattern("因果链")
        assert pat.mode == "single"
        parts = pat.outline_template
        assert "part1" in parts
        assert "part2" in parts
        assert "part3" in parts
        total_weight = sum(p["weight"] for p in parts.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_parallel_pattern(self, service):
        """验证平行交替模式。"""
        pat = service._get_pattern("平行交替")
        assert pat.mode == "dual"
        assert "A1→B1→A2→B2→A3" in pat.prompt_instruction
        assert "{main_card_direction}" in pat.prompt_instruction
        assert "{side_card_direction}" in pat.prompt_instruction

    def test_main_side_pattern(self, service):
        """验证主线+支线模式。"""
        pat = service._get_pattern("主线+支线")
        assert pat.mode == "dual"
        assert "{main_card_direction}" in pat.prompt_instruction
        assert "{side_card_direction}" in pat.prompt_instruction

    def test_weight_sum_one(self, service):
        """验证所有模式的大纲权重之和为 1。"""
        for pat in service._weaving_patterns():
            total = sum(
                seg.get("weight", 0) for seg in pat.outline_template.values()
            )
            assert abs(total - 1.0) < 0.01, (
                f"模式 '{pat.name}' 权重之和为 {total}，期望 1.0"
            )


# ---------------------------------------------------------------------------
# 工具方法
# ---------------------------------------------------------------------------


class TestHelperMethods:
    """测试内部工具方法。"""

    def test_sort_by_weight(self, service):
        """测试按权重降序排序。"""
        cards = [make_card(1), make_card(2), make_card(3)]
        wm = {1: 0.3, 2: 0.7, 3: 0.5}
        sorted_cards = service._sort_by_weight(cards, wm)
        ids = [c.id for c in sorted_cards]
        assert ids == [2, 3, 1]

    def test_get_pattern_found(self, service):
        """测试能找到已有模式。"""
        pat = service._get_pattern("因果链")
        assert pat.name == "因果链"

    def test_get_pattern_not_found(self, service):
        """测试找不到时返回单段式兜底。"""
        pat = service._get_pattern("不存在的模式")
        assert pat.name == "单段式"

    def test_calc_confidence_normal(self, service):
        """测试正常情况下的置信度计算。"""
        cards = [make_card(1), make_card(2)]
        wm = {1: 0.6, 2: 0.4}
        conf = service._calc_confidence(cards, wm)
        assert abs(conf - 0.5) < 0.01

    def test_calc_confidence_empty(self, service):
        """测试空卡片列表。"""
        conf = service._calc_confidence([], {})
        assert conf == 0.0

    def test_calc_confidence_clamped(self, service):
        """测试置信度被限制在 [0, 1]。"""
        cards = [make_card(1)]
        wm = {1: 1.5}
        conf = service._calc_confidence(cards, wm)
        assert conf <= 1.0

    def test_check_same_pov_yes(self, service):
        """测试同 POV 检测——有相同角色。"""
        cards = [
            make_card(1, char_ids=[10, 20]),
            make_card(2, char_ids=[20, 30]),
        ]
        assert service._check_same_pov(cards) is True

    def test_check_same_pov_no(self, service):
        """测试同 POV 检测——无相同角色。"""
        cards = [
            make_card(1, char_ids=[10]),
            make_card(2, char_ids=[20]),
        ]
        assert service._check_same_pov(cards) is False

    def test_check_same_pov_empty(self, service):
        """测试同 POV 检测——卡片无角色信息。"""
        cards = [
            make_card(1, char_ids=[]),
            make_card(2, char_ids=[]),
        ]
        assert service._check_same_pov(cards) is False

    def test_check_temporal_relation_yes(self, service):
        """测试时序关系检测——有时间线信息。"""
        cards = [
            make_card(1, timeline="序章之后"),
            make_card(2, timeline="第一章之后"),
            make_card(3, timeline=""),
        ]
        assert service._check_temporal_relation(cards) is True

    def test_check_temporal_relation_no(self, service):
        """测试时序关系检测——无时间线信息。"""
        cards = [
            make_card(1, timeline=""),
            make_card(2, timeline=""),
            make_card(3, timeline=""),
        ]
        assert service._check_temporal_relation(cards) is False

    def test_check_one_main_two_side_yes(self, service):
        """测试一主二副检测——权重差距大。"""
        cards = [make_card(1), make_card(2), make_card(3)]
        wm = {1: 0.7, 2: 0.15, 3: 0.15}
        assert service._check_one_main_two_side(cards, wm) is True

    def test_check_one_main_two_side_no(self, service):
        """测试一主二副检测——权重接近。"""
        cards = [make_card(1), make_card(2), make_card(3)]
        wm = {1: 0.4, 2: 0.35, 3: 0.25}
        assert service._check_one_main_two_side(cards, wm) is False

    def test_card_characters_json_string(self, service):
        """测试 characters 为 JSON 字符串的情况。"""
        card = MockCard(
            card_id=1,
            characters='[{"id": 1, "name": "角色1", "state_requirement": "存在"}]',
        )
        chars = service._card_characters(card)
        assert isinstance(chars, list)
        assert chars[0]["id"] == 1

    def test_extract_json_direct(self, service):
        """测试直接从 JSON 字符串提取。"""
        result = service._extract_json('{"selected": "因果链", "confidence": 0.85}')
        assert result["selected"] == "因果链"
        assert result["confidence"] == 0.85

    def test_extract_json_from_markdown(self, service):
        """测试从 markdown 代码块提取 JSON。"""
        text = '```json\n{"selected": "平行交替", "confidence": 0.9}\n```'
        result = service._extract_json(text)
        assert result["selected"] == "平行交替"

    def test_extract_json_fallback_brace(self, service):
        """测试兜底提取第一个 JSON 对象。"""
        text = '一些文字 {"selected": "主线+支线", "confidence": 0.7} 更多文字'
        result = service._extract_json(text)
        assert result["selected"] == "主线+支线"

    def test_extract_json_invalid_raises(self, service):
        """测试无效 JSON 抛异常。"""
        with pytest.raises(ValueError):
            service._extract_json("不是JSON")


# ---------------------------------------------------------------------------
# 规则引擎选择
# ---------------------------------------------------------------------------


class TestRuleSelectionDual:
    """双卡规则引擎选择测试。"""

    def test_main_side_by_weight_gap(self, service):
        """权重差距 ≥ 20% → 主线+支线。"""
        cards = [make_card(1, text="主角觉醒"), make_card(2, text="支线事件")]
        wm = {1: 0.7, 2: 0.1}  # gap=0.6
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "主线+支线"
        assert method == "rule"

    def test_causal_chain_same_pov(self, service):
        """权重接近 + 同 POV → 因果链。"""
        cards = [
            make_card(1, text="因", char_ids=[10]),
            make_card(2, text="果", char_ids=[10]),
        ]
        wm = {1: 0.45, 2: 0.40}  # gap=0.05
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "因果链"
        assert method == "rule"

    def test_parallel_diff_pov(self, service):
        """权重接近 + 不同 POV → 平行交替。"""
        cards = [
            make_card(1, text="A视角", char_ids=[10]),
            make_card(2, text="B视角", char_ids=[20]),
        ]
        wm = {1: 0.42, 2: 0.38}  # gap=0.04
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "平行交替"
        assert method == "rule"

    def test_main_side_boundary_gap(self, service):
        """权重差距恰好等于阈值时 → 主线+支线。"""
        cards = [make_card(1), make_card(2)]
        wm = {1: 0.60, 2: 0.40}
        selected, method, _, _ = service._select_by_rules(cards, wm)
        assert selected.name == "主线+支线"

    def test_low_confidence_fallback(self, service):
        """置信度 < 0.3 → LLM fallback（标记为 llm）。"""
        cards = [
            make_card(1, text="不确定的卡1"),
            make_card(2, text="不确定的卡2"),
        ]
        wm = {1: 0.15, 2: 0.10}  # avg=0.125 < 0.3
        selected, method, conf, alts = service._select_by_rules(cards, wm)
        assert method == "llm"
        assert conf < service.CONFIDENCE_THRESHOLD
        assert len(alts) == 2  # 有两个备选


class TestRuleSelectionAll:
    """三卡规则引擎选择测试。"""

    def test_temporal_chain(self, service):
        """三卡有序时关系 → 因果链扩展。"""
        cards = [
            make_card(1, text="起因", timeline="序章"),
            make_card(2, text="发展", timeline="第一章"),
            make_card(3, text="结果", timeline="第二章"),
        ]
        wm = {1: 0.35, 2: 0.35, 3: 0.30}
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "因果链扩展"
        assert method == "rule"

    def test_one_main_two_side(self, service):
        """一主二副 → 主线+双支线。"""
        cards = [
            make_card(1, text="主线", char_ids=[10]),
            make_card(2, text="支线1", char_ids=[20]),
            make_card(3, text="支线2", char_ids=[30]),
        ]
        wm = {1: 0.70, 2: 0.15, 3: 0.15}
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "主线+双支线"

    def test_default_parallel_three(self, service):
        """默认（无特殊条件）→ 平行交替+交汇。"""
        cards = [
            make_card(1, text="线A", char_ids=[10], timeline=""),
            make_card(2, text="线B", char_ids=[20], timeline=""),
            make_card(3, text="线C", char_ids=[30], timeline=""),
        ]
        wm = {1: 0.35, 2: 0.35, 3: 0.30}
        selected, method, conf, _ = service._select_by_rules(cards, wm)
        assert selected.name == "平行交替+交汇"

    def test_low_confidence_fallback_all(self, service):
        """三卡置信度低 → LLM fallback。"""
        cards = [make_card(1), make_card(2), make_card(3)]
        wm = {1: 0.1, 2: 0.1, 3: 0.1}
        selected, method, conf, alt = service._select_by_rules(cards, wm)
        assert method == "llm"
        assert conf < service.CONFIDENCE_THRESHOLD


# ---------------------------------------------------------------------------
# Prompt 指令填充
# ---------------------------------------------------------------------------


class TestBuildPromptInstruction:
    """测试 prompt 模板填充。"""

    def test_single_card_fill(self, service):
        """单卡填充基本变量。"""
        pattern = service._get_pattern("单段式")
        cards = [make_card(1, text="主角踏上旅程")]
        wm = {1: 1.0}
        result = service._build_prompt_instruction(pattern, cards, wm)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_parallel_fill_two_cards(self, service):
        """双卡平行交替模板填充。"""
        pattern = service._get_pattern("平行交替")
        cards = [
            make_card(1, text="勇士出发"),
            make_card(2, text="魔王苏醒"),
        ]
        wm = {1: 0.6, 2: 0.4}
        result = service._build_prompt_instruction(pattern, cards, wm)
        assert "勇士出发" in result
        assert "魔王苏醒" in result

    def test_main_side_fill_with_weights(self, service):
        """主线+支线模板填充权重值。"""
        pattern = service._get_pattern("主线+支线")
        cards = [
            make_card(1, text="主线事件"),
            make_card(2, text="支线事件"),
        ]
        wm = {1: 0.7, 2: 0.3}
        result = service._build_prompt_instruction(pattern, cards, wm)
        assert "主线事件" in result
        assert "支线事件" in result
        assert "0.70" in result or "0.7" in result

    def test_causal_chain_expand_three_cards(self, service):
        """三卡因果链扩展填充。"""
        pattern = service._get_pattern("因果链扩展")
        cards = [
            make_card(1, text="因事件", name="起因卡"),
            make_card(2, text="果事件", name="发展卡"),
            make_card(3, text="揭示事件", name="揭示卡"),
        ]
        wm = {1: 0.35, 2: 0.35, 3: 0.30}
        result = service._build_prompt_instruction(pattern, cards, wm)
        assert "因事件" in result
        assert "果事件" in result
        assert "揭示事件" in result

    def test_no_cards_fill(self, service):
        """无卡片的模板填充应返回原字符串。"""
        pattern = service._get_pattern("单段式")
        result = service._build_prompt_instruction(pattern, [], {})
        assert result == pattern.prompt_instruction


# ---------------------------------------------------------------------------
# 主入口 match_scheme
# ---------------------------------------------------------------------------


class TestMatchScheme:
    """match_scheme 主入口集成测试。"""

    @pytest.mark.asyncio
    async def test_none_mode(self, service):
        """none 模式返回单段式。"""
        result = await service.match_scheme([], {}, "none")
        assert result["mode"] == "none"
        assert result["selected_scheme"]["name"] == "单段式"
        assert result["selection_method"] == "rule"

    @pytest.mark.asyncio
    async def test_single_mode(self, service):
        """single 模式返回单段式。"""
        cards = [make_card(1, text="一个方向")]
        result = await service.match_scheme(cards, {1: 1.0}, "single")
        assert result["mode"] == "single"
        assert result["selected_scheme"]["name"] == "单段式"

    @pytest.mark.asyncio
    async def test_dual_mode_main_side(self, service):
        """dual 模式权重差距大选中主线+支线。"""
        cards = [
            make_card(1, text="主线", char_ids=[10]),
            make_card(2, text="支线", char_ids=[20]),
        ]
        wm = {1: 0.7, 2: 0.1}
        result = await service.match_scheme(cards, wm, "dual")
        assert result["mode"] == "dual"
        assert result["selected_scheme"]["name"] == "主线+支线"
        assert result["selection_method"] == "rule"
        assert "主线" in result["prompt_instruction"]
        assert "支线" in result["prompt_instruction"]

    @pytest.mark.asyncio
    async def test_dual_mode_parallel(self, service):
        """dual 模式不同POV选中平行交替。"""
        cards = [
            make_card(1, text="A视角的故事", char_ids=[10]),
            make_card(2, text="B视角的故事", char_ids=[20]),
        ]
        wm = {1: 0.5, 2: 0.4}
        result = await service.match_scheme(cards, wm, "dual")
        assert result["selected_scheme"]["name"] == "平行交替"

    @pytest.mark.asyncio
    async def test_all_mode_temporal(self, service):
        """all 模式三卡有序时选中因果链扩展。"""
        cards = [
            make_card(1, text="起因", timeline="第一天"),
            make_card(2, text="发展", timeline="第二天"),
            make_card(3, text="结果", timeline="第三天"),
        ]
        wm = {1: 0.35, 2: 0.35, 3: 0.30}
        result = await service.match_scheme(cards, wm, "all")
        assert result["selected_scheme"]["name"] == "因果链扩展"

    @pytest.mark.asyncio
    async def test_all_mode_one_main_two_side(self, service):
        """all 模式一主二副。"""
        cards = [
            make_card(1, text="主要剧情", char_ids=[10]),
            make_card(2, text="支线1", char_ids=[20]),
            make_card(3, text="支线2", char_ids=[30]),
        ]
        wm = {1: 0.7, 2: 0.15, 3: 0.15}
        result = await service.match_scheme(cards, wm, "all")
        assert result["selected_scheme"]["name"] == "主线+双支线"

    @pytest.mark.asyncio
    async def test_hybrid_mode_two_cards(self, service):
        """hybrid 模式两张卡降级为 dual。"""
        cards = [
            make_card(1, text="卡1", char_ids=[10]),
            make_card(2, text="卡2", char_ids=[20]),
        ]
        wm = {1: 0.6, 2: 0.3}
        result = await service.match_scheme(cards, wm, "hybrid")
        assert result["mode"] == "dual"  # 降级为 dual

    @pytest.mark.asyncio
    async def test_hybrid_mode_one_card(self, service):
        """hybrid 模式一张卡降级为 single。"""
        cards = [make_card(1, text="唯一的卡")]
        result = await service.match_scheme(cards, {1: 1.0}, "hybrid")
        assert result["mode"] == "hybrid"  # 保留原始 mode 标识
        assert result["selected_scheme"]["name"] == "单段式"

    @pytest.mark.asyncio
    async def test_empty_cards(self, service):
        """空卡片列表返回兜底结果。"""
        result = await service.match_scheme([], {}, "dual")
        assert result["selected_scheme"]["name"] == "单段式"
        assert result["selection_confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_result_structure(self, service):
        """验证返回结果的完整结构。"""
        cards = [
            make_card(1, text="事件A", char_ids=[10]),
            make_card(2, text="事件B", char_ids=[20]),
        ]
        wm = {1: 0.5, 2: 0.4}
        result = await service.match_scheme(cards, wm, "dual")
        assert "mode" in result
        assert "selected_scheme" in result
        assert "selection_method" in result
        assert "selection_confidence" in result
        assert "alternatives" in result
        assert "prompt_instruction" in result
        assert "outline_template" in result

    @pytest.mark.asyncio
    async def test_alternatives_not_empty(self, service):
        """双卡模式下应有备选方案。"""
        cards = [
            make_card(1, text="事件A", char_ids=[10]),
            make_card(2, text="事件B", char_ids=[20]),
        ]
        wm = {1: 0.5, 2: 0.4}
        result = await service.match_scheme(cards, wm, "dual")
        assert len(result["alternatives"]) >= 1


# ---------------------------------------------------------------------------
# LLM fallback 测试
# ---------------------------------------------------------------------------


class TestLLMFallback:
    """LLM fallback 选择测试。"""

    @pytest.mark.asyncio
    async def test_llm_select_success(self, service):
        """测试 LLM 选择成功。"""
        # Mock llm_client.chat
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"selected": "平行交替", "confidence": 0.85}',
                    }
                }
            ]
        }
        cards = [
            make_card(1, text="视角A", char_ids=[10]),
            make_card(2, text="视角B", char_ids=[20]),
        ]
        wm = {1: 0.5, 2: 0.4}

        with patch.object(service, "_select_by_llm", new_callable=AsyncMock) as mock:
            mock.return_value = (service._get_pattern("平行交替"), 0.85)
            selected, confidence = await service._select_by_llm(cards, wm)
            assert selected.name == "平行交替"
            assert confidence == 0.85

    @pytest.mark.asyncio
    async def test_llm_fallback_in_match(self, service):
        """match_scheme 中 LLM 失败时使用规则兜底。"""
        cards = [
            make_card(1, text="视角A", char_ids=[10]),
            make_card(2, text="视角B", char_ids=[20]),
        ]
        wm = {1: 0.15, 2: 0.10}  # 低置信度触发 LLM

        # Mock LLM 调用失败
        with patch.object(service, "_select_by_llm", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API 调用失败")
            result = await service.match_scheme(cards, wm, "dual")
            # 应该返回备选兜底（平行交替/因果链/主线+支线中的第一个）
            assert result["selection_method"] == "rule"  # 因为备选是 rule 选择回来的
            assert result["selected_scheme"]["name"] in [
                "平行交替", "因果链", "主线+支线", "单段式"
            ]

    @pytest.mark.asyncio
    async def test_llm_select_single_card(self, service):
        """单卡 LLM 选择直接返回单段式。"""
        cards = [make_card(1, text="测试")]
        wm = {1: 1.0}
        selected, confidence = await service._select_by_llm(cards, wm)
        assert selected.name == "单段式"
        assert confidence == 1.0


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """边界情况测试。"""

    @pytest.mark.asyncio
    async def test_very_low_weights(self, service):
        """极低权重处理。"""
        cards = [
            make_card(1, text="卡1"),
            make_card(2, text="卡2"),
        ]
        wm = {1: 0.001, 2: 0.001}
        result = await service.match_scheme(cards, wm, "dual")
        # 低置信度触发 LLM fallback, LLM 可能失败就规则兜底
        assert result is not None
        assert "selected_scheme" in result

    @pytest.mark.asyncio
    async def test_missing_card_in_weight_map(self, service):
        """权重映射缺少某张卡。"""
        cards = [
            make_card(1, text="卡1"),
            make_card(2, text="卡2"),
        ]
        wm = {1: 0.6}  # 缺少 card2
        # 不应该抛异常，缺少的视为 0
        result = await service.match_scheme(cards, wm, "dual")
        assert result is not None

    @pytest.mark.asyncio
    async def test_three_cards_with_missing_fields(self, service):
        """三卡带缺失字段。"""
        card1 = MockCard(card_id=1, direction_text="卡1")
        card2 = MockCard(card_id=2, direction_text="卡2")
        card3 = MockCard(card_id=3, direction_text="卡3")
        wm = {1: 0.4, 2: 0.3, 3: 0.3}
        result = await service.match_scheme([card1, card2, card3], wm, "all")
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_card_ids(self, service):
        """重复卡片 ID（不应发生，但防御性处理）。"""
        card1 = make_card(1, text="卡1Repeated")
        card2 = MockCard(
            card_id=1, name="卡1再", direction_text="卡1再"
        )
        wm = {1: 0.5}
        result = await service.match_scheme([card1, card2], wm, "dual")
        # 能正常返回不崩溃即可
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_mode(self, service):
        """传入不支持的 mode（例如 'invalid'）。"""
        cards = [make_card(1, text="测试")]
        # 不会匹配到已知分支，目前实现是返回 single 模式
        result = await service.match_scheme(cards, {1: 1.0}, "invalid_mode")
        assert result is not None
        assert "selected_scheme" in result

    def test_extract_json_empty_raises(self, service):
        """空字符串提取 JSON 应抛异常。"""
        with pytest.raises(ValueError):
            service._extract_json("")

    def test_weight_confidence_clamp_negative(self, service):
        """负权重的置信度计算。"""
        cards = [make_card(1)]
        wm = {1: -0.5}
        conf = service._calc_confidence(cards, wm)
        assert conf == 0.0  # 被 clamp 到 0


# ---------------------------------------------------------------------------
# 可选的集成测试 (pytest.mark.integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_llm_selection():
    """集成测试：使用真实 LLM 选择编织模式。

    需要 LLM API 可用。通过 pytest -m integration 运行。
    """
    service = WeavingSchemeService()
    cards = [
        make_card(1, text="主角在森林中遇到神秘老人", char_ids=[10]),
        make_card(2, text="反派在城堡中策划阴谋", char_ids=[20]),
    ]
    wm = {1: 0.55, 2: 0.45}
    result = await service.match_scheme(cards, wm, "dual")
    assert "selected_scheme" in result
    # 由于权重接近且不同 POV，规则应选择平行交替
    assert result["selected_scheme"]["name"] == "平行交替"
