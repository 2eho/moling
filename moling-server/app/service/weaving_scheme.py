"""墨灵 (Moling) — 编织方案匹配增强 (Step 5).

提供三种编织模式(因果链/平行交替/主线+支线) + 规则引擎 +
LLM fallback 选择机制。
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_effective_llm_config
from app.llm.client import llm_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class WeavingPattern:
    """编织模式数据类。

    Attributes:
        name: 模式名称 (因果链 / 平行交替 / 主线+支线 / ...)
        mode:  适用模式标识 (single / dual / all / hybrid)
        prompt_instruction: LLM 指令文本（含模板占位符）
        outline_template:   大纲模板（dict，每段含 name / weight / description）
        description:        模式描述
    """

    name: str
    mode: str
    prompt_instruction: str
    outline_template: dict
    description: str = ""


# ---------------------------------------------------------------------------
# 服务类
# ---------------------------------------------------------------------------


class WeavingSchemeService:
    """编织方案匹配增强服务。

    职责：
    - 根据卡片数量/权重/方向选择最合适的编织模式
    - 规则引擎为主，LLM fallback 为辅
    - 填充 prompt 指令和大纲模板中的变量
    """

    # 置信度阈值 — 低于此值时触发 LLM fallback
    CONFIDENCE_THRESHOLD: float = 0.3
    # 权重差距阈值 — 超过此值认为是"一主一副"
    WEIGHT_GAP_THRESHOLD: float = 0.20

    # ------------------------------------------------------------------
    # 公开入口
    # ------------------------------------------------------------------

    async def match_scheme(
        self,
        cards: List[Any],
        weight_map: Dict[int, float],
        req_mode: str = "single",
    ) -> dict:
        """主入口：根据卡片、权重和请求模式匹配编织方案。

        Args:
            cards:       CardPool ORM 对象列表（至少含 id / direction_text /
                         direction_type / name / characters / timeline_point）
            weight_map:  卡片 id → 权重 (0~1) 的映射
            req_mode:    请求模式 — none / single / dual / all / hybrid

        Returns:
            {
                "mode": str,
                "selected_scheme": dict,     # WeavingPattern dict
                "selection_method": "rule"|"llm",
                "selection_confidence": float,
                "alternatives": [dict, ...],
                "prompt_instruction": str,
                "outline_template": dict,
            }
        """
        logger.info(
            "匹配编织方案: mode=%s, cards_count=%d, weights=%s",
            req_mode,
            len(cards),
            weight_map,
        )

        if not cards:
            return self._build_no_card_result(req_mode)

        # 无编织 / 单卡 — 仅返回一段式
        if req_mode in ("none", "single"):
            return self._build_single_result(cards, weight_map, req_mode)

        if req_mode == "dual":
            return await self._match_dual(cards, weight_map)

        if req_mode == "all":
            return await self._match_all(cards, weight_map)

        # hybrid: 按权重排序后取前 2~3 张卡
        return await self._match_hybrid(cards, weight_map)

    # ------------------------------------------------------------------
    # 编织模式模板库
    # ------------------------------------------------------------------

    def _weaving_patterns(self) -> List[WeavingPattern]:
        """返回所有可用的编织模式模板（不可变数据）。"""
        return [
            # ---- 单段式（默认兜底） ----
            WeavingPattern(
                name="单段式",
                mode="single",
                prompt_instruction="本章为单一线索推进，不涉及多线编织。",
                outline_template={
                    "part1": {
                        "name": "单线推进",
                        "weight": 1.0,
                        "description": "单一叙事线索推进",
                    },
                },
                description="单一线索推进，不涉及多线编织",
            ),
            # ---- 因果链：Cause → Effect → Revelation ----
            WeavingPattern(
                name="因果链",
                mode="single",
                prompt_instruction=(
                    "本章按以下三段式结构推进：\n"
                    "第一段【因】: 角色行动或事件触发（展示原因）\n"
                    "第二段【果】: 触发后的连锁反应（推进后果）\n"
                    "第三段【揭示】: 新的信息/认知浮现（为下一章埋钩子）"
                ),
                outline_template={
                    "part1": {
                        "name": "因",
                        "weight": 0.35,
                        "description": "角色行动/事件触发",
                    },
                    "part2": {
                        "name": "果",
                        "weight": 0.40,
                        "description": "连锁反应/后果推进",
                    },
                    "part3": {
                        "name": "揭示",
                        "weight": 0.25,
                        "description": "新信息浮现/章尾钩子",
                    },
                },
                description="因果链编织模式：因→果→揭示三段式结构",
            ),
            # ---- 平行交替：Dual Narrative Interweaving ----
            WeavingPattern(
                name="平行交替",
                mode="dual",
                prompt_instruction=(
                    "本章有两条平行叙事线交替推进：\n"
                    "A线（主）: {main_card_direction}\n"
                    "B线（副）: {side_card_direction}\n"
                    "\n"
                    "以 A1→B1→A2→B2→A3→交汇 的节奏推进\n"
                    "每条片段 300-500 字，交替 ≥ 2 轮\n"
                    "A线和B线在章末交汇"
                ),
                outline_template={
                    "segment1": {"name": "A线第一段", "weight": 0.20},
                    "segment2": {"name": "B线第一段", "weight": 0.20},
                    "segment3": {"name": "A线第二段(推进)", "weight": 0.20},
                    "segment4": {"name": "B线第二段(推进)", "weight": 0.20},
                    "segment5": {"name": "双线交汇/章尾钩子", "weight": 0.20},
                },
                description="平行交替编织模式：双线交替推进后交汇",
            ),
            # ---- 主线+支线 ----
            WeavingPattern(
                name="主线+支线",
                mode="dual",
                prompt_instruction=(
                    "本章包含一条主线推进 + 一条支线点缀：\n"
                    "主线（权重{main_weight}）: {main_card_direction}\n"
                    "支线（权重{side_weight}）: {side_card_direction}\n"
                    "主线占 70% 篇幅，支线占 30% 篇幅"
                ),
                outline_template={
                    "part1": {"name": "主线启动", "weight": 0.25},
                    "part2": {"name": "支线插入", "weight": 0.15},
                    "part3": {"name": "主线推进", "weight": 0.30},
                    "part4": {"name": "主线高潮/冲突", "weight": 0.20},
                    "part5": {"name": "支线回扣/章尾钩子", "weight": 0.10},
                },
                description="主线+支线编织模式：主线为主，支线为辅",
            ),
            # ---- 因果链扩展（三卡） ----
            WeavingPattern(
                name="因果链扩展",
                mode="all",
                prompt_instruction=(
                    "本章按三段式因果链展开，三张卡分别对应：\n"
                    "第一段【因 - {card_1_name}】: {card_1_direction}\n"
                    "第二段【果 - {card_2_name}】: {card_2_direction}\n"
                    "第三段【揭示 - {card_3_name}】: {card_3_direction}\n"
                    "\n"
                    "三段之间需有清晰的因果递进关系"
                ),
                outline_template={
                    "part1": {
                        "name": "因",
                        "weight": 0.30,
                        "description": "三卡中最具「因」属性的段落",
                    },
                    "part2": {
                        "name": "果",
                        "weight": 0.40,
                        "description": "因果连锁反应的展开",
                    },
                    "part3": {
                        "name": "揭示/交汇",
                        "weight": 0.30,
                        "description": "三卡交汇/章尾钩子",
                    },
                },
                description="因果链扩展模式：三卡按因果递进排列",
            ),
            # ---- 平行交替+交汇（三卡） ----
            WeavingPattern(
                name="平行交替+交汇",
                mode="all",
                prompt_instruction=(
                    "本章有三条空间分布不同的叙事线交替推进：\n"
                    "A线: {card_a_direction}\n"
                    "B线: {card_b_direction}\n"
                    "C线: {card_c_direction}\n"
                    "\n"
                    "以 A→B→C→A→B→交汇 的节奏推进\n"
                    "三线在章末交汇"
                ),
                outline_template={
                    "segment1": {"name": "A线叙事", "weight": 0.15},
                    "segment2": {"name": "B线叙事", "weight": 0.15},
                    "segment3": {"name": "C线叙事", "weight": 0.15},
                    "segment4": {"name": "A线推进", "weight": 0.15},
                    "segment5": {"name": "B线推进", "weight": 0.15},
                    "segment6": {"name": "三线交汇/章尾钩子", "weight": 0.25},
                },
                description="平行交替+交汇模式：三线交替推进后交汇",
            ),
            # ---- 主线+双支线（三卡） ----
            WeavingPattern(
                name="主线+双支线",
                mode="all",
                prompt_instruction=(
                    "本章包含一条主线推进 + 两条支线点缀：\n"
                    "主线: {main_card_direction}\n"
                    "支线1: {side_card_1_direction}\n"
                    "支线2: {side_card_2_direction}\n"
                    "主线占 60% 篇幅，两条支线各占 20% 篇幅"
                ),
                outline_template={
                    "part1": {"name": "主线启动", "weight": 0.20},
                    "part2": {"name": "支线1插入", "weight": 0.10},
                    "part3": {"name": "主线推进", "weight": 0.25},
                    "part4": {"name": "支线2插入", "weight": 0.10},
                    "part5": {"name": "主线高潮/冲突", "weight": 0.20},
                    "part6": {"name": "双支线回扣/章尾钩子", "weight": 0.15},
                },
                description="主线+双支线模式：一条主线为主，两条支线为辅",
            ),
        ]

    # ------------------------------------------------------------------
    # 双卡模式匹配
    # ------------------------------------------------------------------

    async def _match_dual(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> dict:
        """双卡模式（Mode 2）编织方案匹配。"""
        sorted_cards = self._sort_by_weight(cards, weight_map)
        selected, method, confidence, alternatives = self._select_by_rules(
            sorted_cards, weight_map
        )

        if method == "llm":
            try:
                selected, confidence = await self._select_by_llm(
                    sorted_cards, weight_map
                )
                method = "llm"
            except Exception as exc:
                logger.warning("LLM fallback 失败，使用规则兜底: %s", exc)
                # LLM 失败时退回到第一个可用备选，并标记为规则选择
                selected = alternatives[0] if alternatives else self._get_pattern(
                    "单段式"
                )
                method = "rule"
                confidence = self._calc_confidence(sorted_cards, weight_map)

        prompt = self._build_prompt_instruction(selected, sorted_cards, weight_map)

        return {
            "mode": "dual",
            "selected_scheme": asdict(selected),
            "selection_method": method,
            "selection_confidence": round(confidence, 4),
            "alternatives": [asdict(a) for a in alternatives],
            "prompt_instruction": prompt,
            "outline_template": selected.outline_template,
        }

    # ------------------------------------------------------------------
    # 三卡模式匹配
    # ------------------------------------------------------------------

    async def _match_all(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> dict:
        """三卡（全选）模式（Mode 3）编织方案匹配。"""
        sorted_cards = self._sort_by_weight(cards, weight_map)
        selected, method, confidence, alternatives = self._select_by_rules(
            sorted_cards, weight_map
        )

        if method == "llm":
            try:
                selected, confidence = await self._select_by_llm(
                    sorted_cards, weight_map
                )
                method = "llm"
            except Exception as exc:
                logger.warning("LLM fallback 失败(all模式)，使用规则兜底: %s", exc)
                selected = alternatives[0] if alternatives else self._get_pattern(
                    "单段式"
                )
                method = "rule"
                confidence = self._calc_confidence(sorted_cards, weight_map)

        prompt = self._build_prompt_instruction(selected, sorted_cards, weight_map)

        return {
            "mode": "all",
            "selected_scheme": asdict(selected),
            "selection_method": method,
            "selection_confidence": round(confidence, 4),
            "alternatives": [asdict(a) for a in alternatives],
            "prompt_instruction": prompt,
            "outline_template": selected.outline_template,
        }

    # ------------------------------------------------------------------
    # 混合模式匹配
    # ------------------------------------------------------------------

    async def _match_hybrid(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> dict:
        """混合模式：按权重排序后降级为 dual 或 all 处理。"""
        sorted_cards = self._sort_by_weight(cards, weight_map)

        if len(sorted_cards) <= 1:
            return self._build_single_result(sorted_cards, weight_map, "hybrid")

        if len(sorted_cards) == 2:
            return await self._match_dual(sorted_cards, weight_map)

        return await self._match_all(sorted_cards, weight_map)

    # ------------------------------------------------------------------
    # 规则引擎 (§3.6.4)
    # ------------------------------------------------------------------

    def _select_by_rules(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> Tuple[WeavingPattern, str, float, List[WeavingPattern]]:
        """规则引擎选择编织模式。

        Returns:
            (selected_pattern, method, confidence, alternatives)
        """
        patterns = self._weaving_patterns()
        card_count = len(cards)

        if card_count <= 1:
            pat = self._get_pattern("单段式")
            return pat, "rule", 1.0, []

        # ---- 置信度计算 ----
        confidence = self._calc_confidence(cards, weight_map)

        if card_count == 2:
            return self._rules_dual(cards, weight_map, patterns, confidence)

        # card_count == 3
        return self._rules_all(cards, weight_map, patterns, confidence)

    def _rules_dual(
        self,
        cards: List[Any],
        weight_map: Dict[int, float],
        patterns: List[WeavingPattern],
        confidence: float,
    ) -> Tuple[WeavingPattern, str, float, List[WeavingPattern]]:
        """双卡规则判断。"""
        if confidence < self.CONFIDENCE_THRESHOLD:
            pat_main = self._get_pattern("平行交替")
            alt1 = self._get_pattern("因果链")
            alt2 = self._get_pattern("主线+支线")
            return pat_main, "llm", confidence, [alt1, alt2]

        weights = [weight_map.get(self._card_id(c), 0.0) for c in cards]
        weight_gap = abs(weights[0] - weights[1])
        same_pov = self._check_same_pov(cards)

        # 使用 math.isclose 处理浮点精度（如 0.60-0.40=0.199999…）
        if weight_gap >= self.WEIGHT_GAP_THRESHOLD or math.isclose(
            weight_gap, self.WEIGHT_GAP_THRESHOLD
        ):
            # 权重差距大 → 主线+支线
            pat = self._get_pattern("主线+支线")
            alt1 = self._get_pattern("平行交替")
            alt2 = self._get_pattern("因果链")
            return pat, "rule", confidence, [alt1, alt2]

        if same_pov:
            # 同 POV → 因果链
            pat = self._get_pattern("因果链")
            alt1 = self._get_pattern("主线+支线")
            alt2 = self._get_pattern("平行交替")
        else:
            # 不同 POV/场景 → 平行交替
            pat = self._get_pattern("平行交替")
            alt1 = self._get_pattern("因果链")
            alt2 = self._get_pattern("主线+支线")

        return pat, "rule", confidence, [alt1, alt2]

    def _rules_all(
        self,
        cards: List[Any],
        weight_map: Dict[int, float],
        patterns: List[WeavingPattern],
        confidence: float,
    ) -> Tuple[WeavingPattern, str, float, List[WeavingPattern]]:
        """三卡规则判断。"""
        if confidence < self.CONFIDENCE_THRESHOLD:
            pat = self._get_pattern("平行交替+交汇")
            alt1 = self._get_pattern("因果链扩展")
            alt2 = self._get_pattern("主线+双支线")
            return pat, "llm", confidence, [alt1, alt2]

        # 检查是否有时序关系
        has_temporal = self._check_temporal_relation(cards)

        if has_temporal:
            pat = self._get_pattern("因果链扩展")
            alt1 = self._get_pattern("平行交替+交汇")
            alt2 = self._get_pattern("主线+双支线")
            return pat, "rule", confidence, [alt1, alt2]

        # 检查是否是"一主二副"
        is_one_main_two_side = self._check_one_main_two_side(cards, weight_map)

        if is_one_main_two_side:
            pat = self._get_pattern("主线+双支线")
            alt1 = self._get_pattern("平行交替+交汇")
            alt2 = self._get_pattern("因果链扩展")
            return pat, "rule", confidence, [alt1, alt2]

        # 默认：空间分布不同 → 平行交替+交汇
        pat = self._get_pattern("平行交替+交汇")
        alt1 = self._get_pattern("因果链扩展")
        alt2 = self._get_pattern("主线+双支线")
        return pat, "rule", confidence, [alt1, alt2]

    # ------------------------------------------------------------------
    # LLM fallback
    # ------------------------------------------------------------------

    async def _select_by_llm(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> Tuple[WeavingPattern, float]:
        """使用 LLM 选择最佳编织模式。"""
        patterns = self._weaving_patterns()

        # 根据卡片数量过滤可用模式
        card_count = len(cards)
        if card_count <= 1:
            return self._get_pattern("单段式"), 1.0
        elif card_count == 2:
            eligible = [p for p in patterns if p.mode in ("single", "dual")]
        else:
            eligible = [p for p in patterns if p.mode in ("single", "dual", "all")]

        # 构建 LLM prompt
        cards_info = "\n".join(
            f"- 卡片{i+1}: [{self._card_name(c)}] "
            f"方向文本: {self._card_text(c)} "
            f"类型: {self._card_type(c)} "
            f"权重: {weight_map.get(self._card_id(c), 0.0):.2f}"
            for i, c in enumerate(cards)
        )

        patterns_desc = "\n".join(
            f"{i+1}. {p.name}: {p.description}"
            for i, p in enumerate(eligible)
        )

        prompt = (
            f"你是一个小说编织模式选择专家。请根据以下卡片信息，从可选模式中选择最合适的编织模式。\n\n"
            f"卡片信息：\n{cards_info}\n\n"
            f"可选编织模式：\n{patterns_desc}\n\n"
            f"请严格按 JSON 格式输出，不要包含额外文字：\n"
            f'{{"selected": "<模式名称>", "confidence": <0-1的置信度>}}\n'
            f"示例：{{\"selected\": \"平行交替\", \"confidence\": 0.85}}"
        )

        try:
            config = get_effective_llm_config()
            response = await llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个小说编织模式选择专家。只输出JSON，不要额外内容。",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=config.get("model", "deepseek-chat"),
                temperature=0.3,
                max_tokens=512,
            )

            raw = response["choices"][0]["message"]["content"].strip()
            logger.debug("LLM 编织模式选择响应: %s", raw)

            # 尝试提取 JSON
            parsed = self._extract_json(raw)
            pattern_name = parsed.get("selected", "")
            llm_confidence = float(parsed.get("confidence", 0.5))

            selected = next(
                (p for p in eligible if p.name == pattern_name),
                None,
            )
            if selected is None:
                logger.warning(
                    "LLM 返回的模式名称 '%s' 不在可选列表中，使用默认",
                    pattern_name,
                )
                selected = eligible[0] if eligible else self._get_pattern("单段式")

            return selected, llm_confidence

        except Exception as exc:
            logger.error("LLM 编织模式选择失败: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Prompt 指令 / 模板填充
    # ------------------------------------------------------------------

    def _build_prompt_instruction(
        self,
        pattern: WeavingPattern,
        cards: List[Any],
        weight_map: Dict[int, float],
    ) -> str:
        """填充 prompt_instruction 和 outline_template 中的模板变量。"""
        if not cards:
            return pattern.prompt_instruction

        sorted_cards = self._sort_by_weight(cards, weight_map)
        context = {}

        # 通用变量
        if len(sorted_cards) >= 1:
            context["card_a_direction"] = self._card_text(sorted_cards[0])
            context["card_1_name"] = self._card_name(sorted_cards[0])
            context["card_1_direction"] = self._card_text(sorted_cards[0])
            context["main_card_direction"] = self._card_text(sorted_cards[0])

        if len(sorted_cards) >= 2:
            context["card_b_direction"] = self._card_text(sorted_cards[1])
            context["card_2_name"] = self._card_name(sorted_cards[1])
            context["card_2_direction"] = self._card_text(sorted_cards[1])
            context["side_card_direction"] = self._card_text(sorted_cards[1])

        if len(sorted_cards) >= 3:
            context["card_c_direction"] = self._card_text(sorted_cards[2])
            context["card_3_name"] = self._card_name(sorted_cards[2])
            context["card_3_direction"] = self._card_text(sorted_cards[2])
            context["side_card_1_direction"] = self._card_text(sorted_cards[1])
            context["side_card_2_direction"] = self._card_text(sorted_cards[2])

        # 权重变量
        if len(sorted_cards) >= 2:
            w0 = weight_map.get(self._card_id(sorted_cards[0]), 0.0)
            w1 = weight_map.get(self._card_id(sorted_cards[1]), 0.0)
            main_w = max(w0, w1)
            side_w = min(w0, w1)
            context["main_weight"] = f"{main_w:.2f}"
            context["side_weight"] = f"{side_w:.2f}"

        # 执行模板替换
        prompt = pattern.prompt_instruction
        for key, val in context.items():
            placeholder = "{" + key + "}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(val))

        return prompt

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _card_id(card: Any) -> int:
        """安全获取卡片 ID。"""
        return getattr(card, "id", 0)

    @staticmethod
    def _card_name(card: Any) -> str:
        """安全获取卡片名称。"""
        return getattr(card, "name", "未知卡片")

    @staticmethod
    def _card_text(card: Any) -> str:
        """安全获取方向文本。"""
        return getattr(card, "direction_text", "")

    @staticmethod
    def _card_type(card: Any) -> str:
        """安全获取方向类型。"""
        return getattr(card, "direction_type", "")

    @staticmethod
    def _card_characters(card: Any) -> list:
        """安全获取卡片关联角色列表。"""
        val = getattr(card, "characters", None)
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    @staticmethod
    def _card_timeline(card: Any) -> str:
        """安全获取时间线关键点。"""
        return getattr(card, "timeline_point", "") or ""

    @staticmethod
    def _sort_by_weight(
        cards: List[Any], weight_map: Dict[int, float]
    ) -> List[Any]:
        """按权重降序排序卡片。"""
        return sorted(
            cards,
            key=lambda c: weight_map.get(getattr(c, "id", 0), 0),
            reverse=True,
        )

    def _get_pattern(self, name: str) -> WeavingPattern:
        """按名称查找编织模式，找不到时返回单段式。"""
        patterns = self._weaving_patterns()
        for p in patterns:
            if p.name == name:
                return p
        logger.warning("编织模式 '%s' 未找到，返回单段式", name)
        return patterns[0]

    def _calc_confidence(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> float:
        """计算规则选择的置信度（权重均值）。"""
        if not cards:
            return 0.0
        weights = [weight_map.get(self._card_id(c), 0.0) for c in cards]
        avg = sum(weights) / len(weights) if weights else 0.0
        return min(max(avg, 0.0), 1.0)

    def _check_same_pov(self, cards: List[Any]) -> bool:
        """检查两张卡是否关联到相同角色（同一 POV）。"""
        char_sets = []
        for c in cards:
            chars = self._card_characters(c)
            ids = {ch.get("id") for ch in chars if isinstance(ch, dict) and ch.get("id")}
            if not ids:
                # 没有角色信息时默认不同 POV
                return False
            char_sets.append(ids)

        if len(char_sets) < 2:
            return False

        # 检查是否有交集
        return bool(char_sets[0] & char_sets[1])

    def _check_temporal_relation(self, cards: List[Any]) -> bool:
        """检查三张卡是否有明确的时序关系（通过 timeline_point 字段）。"""
        timelines = [self._card_timeline(c) for c in cards]
        non_empty = [t for t in timelines if t.strip()]
        # 至少两张卡有时间线信息 → 认为存在时序关系
        return len(non_empty) >= 2

    def _check_one_main_two_side(
        self, cards: List[Any], weight_map: Dict[int, float]
    ) -> bool:
        """检查是否为一主二副（最高权重 ≥ 次高 + 20%）。"""
        if len(cards) < 3:
            return False
        sorted_cards = self._sort_by_weight(cards, weight_map)
        w0 = weight_map.get(self._card_id(sorted_cards[0]), 0.0)
        w1 = weight_map.get(self._card_id(sorted_cards[1]), 0.0)
        w2 = weight_map.get(self._card_id(sorted_cards[2]), 0.0)

        # 最高权重比次高 + 次次高还多 20% 以上
        return w0 >= (w1 + w2) * 0.8 and w0 > w1

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从 LLM 响应文本中提取 JSON。"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # 尝试提取 ```json ... ``` 块
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 { ... }
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

    # ------------------------------------------------------------------
    # 辅助构建方法
    # ------------------------------------------------------------------

    def _build_no_card_result(self, req_mode: str) -> dict:
        """无卡片时的兜底结果。"""
        pattern = self._get_pattern("单段式")
        return {
            "mode": req_mode,
            "selected_scheme": asdict(pattern),
            "selection_method": "rule",
            "selection_confidence": 1.0,
            "alternatives": [],
            "prompt_instruction": pattern.prompt_instruction,
            "outline_template": pattern.outline_template,
        }

    def _build_single_result(
        self, cards: List[Any], weight_map: Dict[int, float], req_mode: str
    ) -> dict:
        """单卡/无编织模式的结果。"""
        pattern = self._get_pattern("单段式")
        prompt = self._build_prompt_instruction(pattern, cards, weight_map)
        return {
            "mode": req_mode,
            "selected_scheme": asdict(pattern),
            "selection_method": "rule",
            "selection_confidence": 1.0,
            "alternatives": [],
            "prompt_instruction": prompt,
            "outline_template": pattern.outline_template,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

weaving_scheme_service = WeavingSchemeService()
