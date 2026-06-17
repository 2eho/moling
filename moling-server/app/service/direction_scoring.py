"""墨灵 (Moling) — Step 4: 方向冲突评分增强。

实现方向相容性检测：
1. 实体冲突检测 — 卡片之间是否引用了同一实体但存在矛盾描述
2. 情感冲突检测 — 卡片方向之间的情感基调是否冲突
3. 置信度评分 — 综合评分，传统算法置信度阈值

评分 ∈ [0, 1]:
  > 0.7  → 高置信度 → 直接采用
  [0.3, 0.7] → 中等置信度 → 标记为"建议"，但采用
  < 0.3  → 低置信度 → fallback 到 LLM

编织选择评分 ∈ [0, 1]:
  > 0.8  → 直接采用规则引擎的结果
  ≤ 0.8  → fallback 到 LLM 选编织模式
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_effective_llm_config, get_settings
from app.llm.client import llm_client
from app.models.card_pool import CardPool

logger = logging.getLogger(__name__)
settings = get_settings()

# 方向类型枚举
DIRECTION_TYPES = ["稳妥", "有趣", "惊艳", "神之一手"]

# 方向相容性矩阵 (行 i, 列 j → DIRECTION_TYPES[i] vs DIRECTION_TYPES[j])
_DIRECTION_COMPATIBILITY_MATRIX: List[List[float]] = [
    # 稳妥    有趣    惊艳    神之一手
    [1.0, 0.7, 0.3, 0.1],  # 稳妥
    [0.7, 1.0, 0.6, 0.4],  # 有趣
    [0.3, 0.6, 1.0, 0.7],  # 惊艳
    [0.1, 0.4, 0.7, 1.0],  # 神之一手
]

# 方向 → 情感基调映射
_DIRECTION_TONE_MAP: Dict[str, List[str]] = {
    "稳妥": ["平静", "稳重", "保守", "温和"],
    "有趣": ["轻松", "诙谐", "幽默", "愉快"],
    "惊艳": ["戏剧性", "紧张", "冲突", "震撼"],
    "神之一手": ["大胆", "冒险", "激进", "颠覆"],
}

# 高冲突方向对（内在固有冲突）
_HIGH_CONFLICT_PAIRS = [
    ("稳妥", "神之一手"),
    ("神之一手", "稳妥"),
]


class DirectionScoringService:
    """方向冲突评分服务。

    纯计算 + LLM fallback，不涉及数据库操作。
    """

    @staticmethod
    def _direction_compatibility_matrix() -> List[List[float]]:
        """获取方向相容性矩阵的深拷贝。"""
        return [row[:] for row in _DIRECTION_COMPATIBILITY_MATRIX]

    @staticmethod
    def _direction_index(direction_type: str) -> int:
        """将方向类型转为矩阵索引，未知类型默认 0 (稳妥)。"""
        try:
            return DIRECTION_TYPES.index(direction_type)
        except ValueError:
            logger.warning("未知方向类型 '%s'，默认映射为 '稳妥'", direction_type)
            return 0

    @staticmethod
    def _lookup_compatibility(dir_a: str, dir_b: str) -> float:
        """查询两个方向类型的相容性评分。"""
        i = DirectionScoringService._direction_index(dir_a)
        j = DirectionScoringService._direction_index(dir_b)
        return _DIRECTION_COMPATIBILITY_MATRIX[i][j]

    # ------------------------------------------------------------------
    # 主要入口
    # ------------------------------------------------------------------

    async def score_direction_conflicts(
        self,
        cards: List[CardPool],
        weight_map: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """对一组方向卡进行全面的冲突评分。

        Args:
            cards: 待评分的方向卡片列表。
            weight_map: 卡片 ID → 权重 的映射（可选）。

        Returns:
            包含冲突评分、置信度、建议等的字典。
        """
        if not cards:
            return self._empty_result()

        # 1. 构建方向相容性矩阵
        compatibility_matrix = self._compute_compatibility_matrix(cards)

        composites = self._compute_compatibility_statistics(cards, compatibility_matrix)

        # 2. 实体冲突检测
        entity_conflicts = self._entity_conflict_detection(cards)

        # 3. 情感基调冲突
        tone_conflicts = self._emotional_tone_conflict(cards)

        # 4. 综合冲突评分
        conflict_score = self._aggregate_conflict_score(
            composite_score=composites["avg_compatibility"],
            entity_conflicts=entity_conflicts,
            tone_conflicts=tone_conflicts,
            cards=cards,
        )

        # 5. 置信度计算
        confidence = self._calculate_confidence(conflict_score)

        # 6. 判断是否需要 fallback 到 LLM
        fallback_to_llm = confidence < 0.3
        llm_result = None

        if fallback_to_llm:
            logger.info("置信度 %.2f < 0.3，fallback 到 LLM", confidence)
            llm_result = await self._llm_fallback(cards, compatibility_matrix, entity_conflicts, tone_conflicts)
        else:
            logger.info("置信度 %.2f >= 0.3，采用规则引擎结果", confidence)

        # 7. 生成建议修复方案
        suggested_fix = self._generate_suggested_fix(
            conflict_score=conflict_score,
            entity_conflicts=entity_conflicts,
            tone_conflicts=tone_conflicts,
            fallback_result=llm_result,
        )

        return {
            "has_conflict": conflict_score > 0.3,
            "conflict_score": round(conflict_score, 4),
            "confidence": round(confidence, 4),
            "compatibility_matrix": compatibility_matrix,
            "entity_conflicts": entity_conflicts,
            "tone_conflicts": tone_conflicts,
            "fallback_to_llm": fallback_to_llm,
            "llm_result": llm_result,
            "suggested_fix": suggested_fix,
        }

    async def can_use_rule_engine(
        self,
        cards: List[CardPool],
        compatibility_result: dict,
    ) -> Tuple[bool, float]:
        """判断是否可以直接使用规则引擎，还是需要 fallback 到 LLM。

        Returns:
            (can_use, score): can_use=True 表示直接采用规则引擎。
        """
        if not cards or not compatibility_result:
            return True, 1.0

        score = compatibility_result.get("conflict_score", 0.0)
        confidence = compatibility_result.get("confidence", 0.0)

        # 编织选择评分 = 冲突评分和置信度的加权平均
        weave_score = 0.6 * (1.0 - score) + 0.4 * confidence

        can_use = weave_score > 0.8
        return can_use, round(weave_score, 4)

    # ------------------------------------------------------------------
    # 内部计算方法
    # ------------------------------------------------------------------

    def _compute_compatibility_matrix(self, cards: List[CardPool]) -> List[List[float]]:
        """计算卡片间的方向相容性矩阵。"""
        n = len(cards)
        matrix = [[1.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                score = self._lookup_compatibility(
                    cards[i].direction_type, cards[j].direction_type
                )
                matrix[i][j] = score
                matrix[j][i] = score

        return matrix

    def _compute_compatibility_statistics(
        self,
        cards: List[CardPool],
        compatibility_matrix: List[List[float]],
    ) -> Dict[str, Any]:
        """计算相容性统计指标。"""
        n = len(cards)
        if n == 0:
            return {"avg_compatibility": 1.0, "min_compatibility": 1.0, "max_compatibility": 1.0}

        scores = []
        for i in range(n):
            for j in range(i + 1, n):
                scores.append(compatibility_matrix[i][j])

        if not scores:
            return {"avg_compatibility": 1.0, "min_compatibility": 1.0, "max_compatibility": 1.0}

        return {
            "avg_compatibility": sum(scores) / len(scores),
            "min_compatibility": min(scores),
            "max_compatibility": max(scores),
        }

    def _entity_conflict_detection(self, cards: List[CardPool]) -> List[Dict[str, Any]]:
        """检测卡片之间是否存在实体冲突。

        检查维度：
        - 角色 (characters): 同一角色在不同卡片中的状态要求是否矛盾
        - 剧情承诺 (plot_promises): 同一剧情承诺在不同卡片中的推进类型是否矛盾
        - 世界观规则 (world_rules): 同一世界观规则在不同卡片中的约束是否矛盾
        """
        conflicts: List[Dict[str, Any]] = []

        conflicts.extend(self._detect_character_conflicts(cards))
        conflicts.extend(self._detect_plot_promise_conflicts(cards))
        conflicts.extend(self._detect_world_rule_conflicts(cards))

        return conflicts

    def _detect_character_conflicts(self, cards: List[CardPool]) -> List[Dict[str, Any]]:
        """检测角色描述冲突。"""
        conflicts: List[Dict[str, Any]] = []
        # entity_id → [(card_index, state_requirement)]
        character_map: Dict[str, List[Tuple[int, str]]] = {}

        for idx, card in enumerate(cards):
            if not card.characters:
                continue
            for char in card.characters:
                char_id = char.get("id") or char.get("name", "")
                state = char.get("state_requirement", "")
                if char_id not in character_map:
                    character_map[char_id] = []
                character_map[char_id].append((idx, state))

        for char_id, entries in character_map.items():
            if len(entries) < 2:
                continue

            card_indices = [e[0] for e in entries]
            states = [e[1] for e in entries]

            if len(set(states)) > 1 and all(states):
                severity = "high" if self._is_state_contradictory(states) else "medium"
                conflicts.append({
                    "cards": [cards[i].id for i in card_indices],
                    "entity": f"角色: {char_id}",
                    "description": f"角色 '{char_id}' 在不同卡片中状态要求冲突: {', '.join(f'{c.name}: {s}' for c, s in zip([cards[i] for i in card_indices], states))}",
                    "severity": severity,
                })

        return conflicts

    @staticmethod
    def _is_state_contradictory(states: List[str]) -> bool:
        """判断多个状态描述是否存在明显矛盾。"""
        contradictory_pairs = [
            ("生", "死"), ("活", "死"), ("在", "不在"),
            ("出现", "消失"), ("强", "弱"), ("高", "低"),
            ("有", "无"), ("是", "否"), ("觉醒", "沉睡"),
            ("清醒", "昏迷"), ("成功", "失败"),
        ]
        for a in states:
            for b in states:
                if a == b:
                    continue
                if any(
                    (keyword_a in a and keyword_b in b)
                    or (keyword_b in a and keyword_a in b)
                    for keyword_a, keyword_b in contradictory_pairs
                ):
                    return True
        return False

    @staticmethod
    def _detect_plot_promise_conflicts(cards: List[CardPool]) -> List[Dict[str, Any]]:
        """检测剧情承诺冲突。"""
        conflicts: List[Dict[str, Any]] = []
        promise_map: Dict[str, List[Tuple[int, str]]] = {}

        for idx, card in enumerate(cards):
            if not card.plot_promises:
                continue
            for promise in card.plot_promises:
                promise_id = promise.get("id") or promise.get("title", "")
                advance_type = promise.get("advance_type", "")
                if promise_id not in promise_map:
                    promise_map[promise_id] = []
                promise_map[promise_id].append((idx, advance_type))

        for promise_id, entries in promise_map.items():
            if len(entries) < 2:
                continue

            card_indices = [e[0] for e in entries]
            advance_types = [e[1] for e in entries]

            if len(set(advance_types)) > 1 and all(advance_types):
                conflicts.append({
                    "cards": [cards[i].id for i in card_indices],
                    "entity": f"剧情承诺: {promise_id}",
                    "description": f"剧情承诺 '{promise_id}' 在不同卡片中推进类型矛盾: {', '.join(advance_types)}",
                    "severity": "medium",
                })

        return conflicts

    @staticmethod
    def _detect_world_rule_conflicts(cards: List[CardPool]) -> List[Dict[str, Any]]:
        """检测世界观规则冲突。"""
        conflicts: List[Dict[str, Any]] = []
        rule_map: Dict[str, List[Tuple[int, str]]] = {}

        for idx, card in enumerate(cards):
            if not card.world_rules:
                continue
            for rule in card.world_rules:
                rule_id = rule.get("id") or rule.get("rule", "")
                constraint = rule.get("constraint", "")
                if rule_id not in rule_map:
                    rule_map[rule_id] = []
                rule_map[rule_id].append((idx, constraint))

        for rule_id, entries in rule_map.items():
            if len(entries) < 2:
                continue

            card_indices = [e[0] for e in entries]
            constraints = [e[1] for e in entries]

            if len(set(constraints)) > 1 and all(constraints):
                conflicts.append({
                    "cards": [cards[i].id for i in card_indices],
                    "entity": f"世界观规则: {rule_id}",
                    "description": f"规则 '{rule_id}' 在不同卡片中约束矛盾: {', '.join(constraints)}",
                    "severity": "low",
                })

        return conflicts

    @staticmethod
    def _emotional_tone_conflict(cards: List[CardPool]) -> List[str]:
        """检测卡片方向之间的情感基调冲突。"""
        conflicts: List[str] = []
        seen_types = set()

        for i, card_a in enumerate(cards):
            for j, card_b in enumerate(cards):
                if j <= i:
                    continue

                pair_key = tuple(sorted([card_a.direction_type, card_b.direction_type]))
                if pair_key in seen_types:
                    continue
                seen_types.add(pair_key)

                dir_a = card_a.direction_type
                dir_b = card_b.direction_type

                compatibility = DirectionScoringService._lookup_compatibility(dir_a, dir_b)

                if compatibility < 0.4:
                    tones_a = _DIRECTION_TONE_MAP.get(dir_a, [])
                    tones_b = _DIRECTION_TONE_MAP.get(dir_b, [])
                    conflicts.append(
                        f"方向 '{dir_a}' ({', '.join(tones_a)}) 与 "
                        f"方向 '{dir_b}' ({', '.join(tones_b)}) 情感基调冲突"
                    )

        return conflicts

    @staticmethod
    def _aggregate_conflict_score(
        composite_score: float,
        entity_conflicts: List[Dict[str, Any]],
        tone_conflicts: List[str],
        cards: List[CardPool],
    ) -> float:
        """综合多个维度的冲突评分。"""
        # 1. 方向相容性评分（0-1，值越小冲突越大）
        #    将 avg_compatibility 反转：1 - avg 使得高冲突 = 高分数
        compatibility_conflict = 1.0 - composite_score

        # 2. 实体冲突评分
        entity_penalty = 0.0
        high_count = sum(1 for c in entity_conflicts if c["severity"] == "high")
        medium_count = sum(1 for c in entity_conflicts if c["severity"] == "medium")
        low_count = sum(1 for c in entity_conflicts if c["severity"] == "low")

        if high_count > 0:
            entity_penalty = min(0.5, high_count * 0.2)
        elif medium_count > 0:
            entity_penalty = min(0.3, medium_count * 0.1)
        elif low_count > 0:
            entity_penalty = min(0.1, low_count * 0.05)

        # 3. 情感冲突评分
        tone_penalty = min(0.3, len(tone_conflicts) * 0.1)

        # 4. 检查是否有高冲突方向对
        pair_penalty = 0.0
        for i in range(len(cards)):
            for j in range(i + 1, len(cards)):
                pair = (cards[i].direction_type, cards[j].direction_type)
                if pair in _HIGH_CONFLICT_PAIRS:
                    pair_penalty = max(pair_penalty, 0.2)

        total = compatibility_conflict + entity_penalty + tone_penalty + pair_penalty
        return min(1.0, total)

    @staticmethod
    def _calculate_confidence(conflict_score: float) -> float:
        """计算置信度评分。

        基于冲突评分的置信度计算：
        - 极低冲突 (score < 0.1) → 高置信度
        - 极高冲突 (score > 0.8) → 高置信度（明确有冲突）
        - 中等冲突 → 中等置信度
        """
        if conflict_score < 0.1:
            # 几乎没有冲突，信心很高
            return 0.9
        elif conflict_score > 0.8:
            # 冲突非常明确，信心也很高
            return 0.85
        elif conflict_score > 0.6:
            # 冲突较明显
            return 0.75
        elif conflict_score > 0.4:
            # 冲突较模糊
            return 0.5
        else:
            # 冲突不明确，低置信度
            return 0.3

    # ------------------------------------------------------------------
    # LLM Fallback
    # ------------------------------------------------------------------

    async def _llm_fallback(
        self,
        cards: List[CardPool],
        compatibility_matrix: List[List[float]],
        entity_conflicts: List[Dict[str, Any]],
        tone_conflicts: List[str],
    ) -> Optional[str]:
        """当规则引擎置信度不足时，调用 LLM 进行冲突判断。"""
        cards_summary = self._build_cards_summary(cards)
        matrix_summary = self._build_matrix_summary(cards, compatibility_matrix)
        entity_summary = self._build_entity_summary(entity_conflicts)
        tone_summary = "\n".join(f"- {t}" for t in tone_conflicts) if tone_conflicts else "无"

        prompt = f"""你是小说创作方向分析专家。请判断以下方向卡片组合是否存在冲突。

## 方向卡片信息
{cards_summary}

## 方向相容性矩阵
{matrix_summary}

## 实体冲突检测结果
{entity_summary}

## 情感基调冲突
{tone_summary}

请分析这些卡片组合的实际冲突情况，按以下 JSON 格式输出（只输出 JSON，不要其他文字）：
{{
    "assessment": "兼容 / 部分兼容 / 冲突",
    "conflict_score": 0.0-1.0,
    "reasoning": "分析推理过程",
    "suggestion": "具体的改进建议",
    "recommended_fix": "建议的解决方案描述"
}}"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是专业的小说创作方向分析助手，擅长分析方向冲突并提供改进建议。输出纯 JSON。",
                },
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=get_effective_llm_config()["model"],
                temperature=0.3,
                max_tokens=1024,
            )
            content = response["choices"][0]["message"]["content"]

            # 提取 JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(content[json_start:json_end])
                return json.dumps(parsed, ensure_ascii=False, indent=2)

            logger.warning("LLM 返回内容未能解析为 JSON: %s", content[:200])
            return None

        except json.JSONDecodeError as e:
            logger.error("LLM 返回 JSON 解析失败: %s", e)
            return None
        except Exception as e:
            logger.error("LLM fallback 调用失败: %s", e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _build_cards_summary(cards: List[CardPool]) -> str:
        """构建卡片摘要文本。"""
        lines = []
        for i, card in enumerate(cards):
            lines.append(f"卡片 {i + 1}: {card.name} (方向: {card.direction_type}, 稀有度: {card.rarity})")
            lines.append(f"  方向文本: {card.direction_text[:100]}")
            if card.characters:
                char_names = [c.get("name", "") for c in card.characters]
                lines.append(f"  关联角色: {', '.join(char_names)}")
            if card.plot_promises:
                promise_titles = [p.get("title", "") for p in card.plot_promises]
                lines.append(f"  关联剧情: {', '.join(promise_titles)}")
        return "\n".join(lines)

    @staticmethod
    def _build_matrix_summary(
        cards: List[CardPool],
        compatibility_matrix: List[List[float]],
    ) -> str:
        """构建相容性矩阵摘要文本。"""
        lines = []
        names = [f"{c.name}({c.direction_type})" for c in cards]
        for i in range(len(cards)):
            row_entries = []
            for j in range(len(cards)):
                if i == j:
                    row_entries.append("-")
                else:
                    row_entries.append(f"{compatibility_matrix[i][j]:.1f}")
            lines.append(f"  {names[i]}: {', '.join(row_entries)}")
        return "\n".join(lines)

    @staticmethod
    def _build_entity_summary(entity_conflicts: List[Dict[str, Any]]) -> str:
        """构建实体冲突摘要文本。"""
        if not entity_conflicts:
            return "无实体冲突"
        lines = []
        for c in entity_conflicts:
            lines.append(f"- [{c['severity'].upper()}] {c['entity']}: {c['description'][:100]}")
        return "\n".join(lines)

    @staticmethod
    def _generate_suggested_fix(
        conflict_score: float,
        entity_conflicts: List[Dict[str, Any]],
        tone_conflicts: List[str],
        fallback_result: Optional[str],
    ) -> Optional[str]:
        """生成建议修复方案。"""
        if fallback_result:
            try:
                parsed = json.loads(fallback_result)
                return parsed.get("suggestion") or parsed.get("recommended_fix")
            except (json.JSONDecodeError, TypeError):
                return None

        if conflict_score < 0.3:
            return None  # 无冲突，无需修复

        fixes = []

        if entity_conflicts:
            high_entities = [c["entity"] for c in entity_conflicts if c["severity"] == "high"]
            if high_entities:
                fixes.append(f"解决高严重度实体冲突: {', '.join(high_entities)}。建议统一对同一实体的描述。")

        if tone_conflicts:
            fixes.append("情感基调冲突建议: 尝试调整方向搭配，或通过叙事手法中和基调冲突。")

        if conflict_score > 0.6:
            fixes.append("高冲突评分建议: 考虑替换部分卡片以降低方向冲突。")

        return "；".join(fixes) if fixes else None

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """返回空结果（无卡片时）。"""
        return {
            "has_conflict": False,
            "conflict_score": 0.0,
            "confidence": 1.0,
            "compatibility_matrix": [],
            "entity_conflicts": [],
            "tone_conflicts": [],
            "fallback_to_llm": False,
            "llm_result": None,
            "suggested_fix": None,
        }


# Singleton instance
direction_scoring_service = DirectionScoringService()
