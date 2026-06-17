"""Moling — Dynamic-Layer Conflict Detection Service (Step 3).

Detects three types of conflicts between direction cards and the dynamic layer:

1. **Baseline conflict** — card direction vs dynamic layer must_hold / must_not.
2. **Secret matrix conflict** — card direction would cause a character to reveal
   something they do not (yet) know.
3. **State machine conflict** — card direction is incompatible with a character's
   current narrative state.

Usage::

    from app.service.conflict_detection import ConflictDetectionService

    result = await ConflictDetectionService().detect_conflicts(
        db, project_id, chapter_id, cards, weight_map
    )
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_effective_llm_config
from app.llm.client import llm_client
from app.models import CardPool, DynamicLayer, Secret, VaultCharacter

logger = logging.getLogger(__name__)

# ============================================================================
# Confidence scoring constants (§2.4)
# ============================================================================

# U-curve shape: low and high conflict → high confidence; middle → lowest
_CONFIDENCE_LOW_ZONE = 0.15       # below this: high-confidence plateau
_CONFIDENCE_HIGH_ZONE = 0.75      # above this: high-confidence plateau
_CONFIDENCE_CENTER = 0.45         # midpoint of the middle zone (lowest point)
_CONFIDENCE_HALF_RANGE = 0.30     # half-range of the middle zone
_CONFIDENCE_MIN = 0.2             # minimum confidence at the center
_CONFIDENCE_PLATEAU_HIGH = 0.9    # confidence at edges of middle zone
_CONFIDENCE_PEAK = 1.0            # confidence at extremes

# Confidence thresholds
_CONFIDENCE_HIGH_THRESHOLD = 0.7   # >= 0.7 → "high"
_CONFIDENCE_MEDIUM_THRESHOLD = 0.3 # >= 0.3 → "medium", < 0.3 → "low"


# ---------------------------------------------------------------------------
# Confidence helpers (§2.4)
# ---------------------------------------------------------------------------


def _compute_confidence(conflict_score: float) -> float:
    """Compute confidence from conflict_score using a U-curve model (§2.4).

    The U-curve ensures that both very low conflict scores (clear pass) and
    very high conflict scores (clear fail) yield high confidence, while
    ambiguous middle-range scores yield lower confidence.

    Returns
    -------
    float
        Confidence value in [0, 1].
    """
    if conflict_score <= 0.0:
        return _CONFIDENCE_PEAK

    if conflict_score <= _CONFIDENCE_LOW_ZONE:
        # Near-zero conflict → high confidence, tapering from 1.0 to 0.9
        t = conflict_score / _CONFIDENCE_LOW_ZONE  # 0→1
        return round(_CONFIDENCE_PEAK - (_CONFIDENCE_PEAK - _CONFIDENCE_PLATEAU_HIGH) * t, 4)

    if conflict_score >= _CONFIDENCE_HIGH_ZONE:
        if conflict_score >= 1.0:
            return _CONFIDENCE_PEAK
        # Near-max conflict → high confidence, rising from 0.9 to 1.0
        t = (conflict_score - _CONFIDENCE_HIGH_ZONE) / (1.0 - _CONFIDENCE_HIGH_ZONE)  # 0→1
        return round(_CONFIDENCE_PLATEAU_HIGH + (_CONFIDENCE_PEAK - _CONFIDENCE_PLATEAU_HIGH) * t, 4)

    # Middle zone: U-shaped parabola
    # Vertex at center (t=0), minimum = CONFIDENCE_MIN
    # Passes through low_zone and high_zone edges (t=-1, t=1) at CONFIDENCE_PLATEAU_HIGH
    t = (conflict_score - _CONFIDENCE_CENTER) / _CONFIDENCE_HALF_RANGE  # -1 to 1
    confidence = _CONFIDENCE_PLATEAU_HIGH - (_CONFIDENCE_PLATEAU_HIGH - _CONFIDENCE_MIN) * (1.0 - t * t)
    return round(confidence, 4)


def _compute_confidence_label(confidence: float) -> str:
    """Map a numeric confidence value to a human-readable label.

    Returns
    -------
    str
        ``"high"``, ``"medium"``, or ``"low"``.
    """
    if confidence >= _CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    if confidence >= _CONFIDENCE_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Conflict severity helpers
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.3}


def _compute_conflict_score(conflicts: List[Dict[str, Any]]) -> float:
    """Aggregate individual conflict severities into a 0-1 score.

    Uses a diminishing-returns model so that many low-severity conflicts
    contribute less than a single high-severity one.
    """
    if not conflicts:
        return 0.0
    raw = sum(
        _SEVERITY_WEIGHTS.get(c.get("severity", "low"), 0.3) for c in conflicts
    )
    # Normalise: 1 - exp(-raw) maps [0, +inf) → [0, 1)
    return round(1.0 - 1.0 / (1.0 + raw), 4)


def _conflict_item(
    conflict_type: str,
    description: str,
    severity: str = "medium",
    suggested_fix: Optional[str] = None,
) -> Dict[str, Any]:
    """Factory for a single conflict dict."""
    return {
        "type": conflict_type,
        "description": description,
        "severity": severity,
        "suggested_fix": suggested_fix,
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ConflictDetectionService:
    """Detects dynamic-layer conflicts for generated direction cards."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def detect_conflicts(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
        cards: List[CardPool],
        weight_map: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """Run all three conflict detectors, compute confidence, and optionally
        fall back to LLM for low-confidence results.

        Parameters
        ----------
        db:
            SQLAlchemy async session.
        project_id:
            Target project UUID.
        chapter_id:
            Target chapter UUID.
        cards:
            Direction cards selected for the current generation round.
        weight_map:
            Card-id → weight mapping (unused by conflict detection but
            accepted for interface compatibility with the pipeline).

        Returns
        -------
        dict with keys ``has_conflict``, ``conflict_score``, ``confidence``,
        ``confidence_label``, ``fallback_to_llm``, ``llm_verdict``,
        ``conflicts``.
        """
        logger.info(
            "Conflict detection start: project=%s chapter=%s cards=%d",
            project_id, chapter_id, len(cards),
        )

        # ── early exit when there are no cards to check ──────────────
        if not cards:
            logger.info("No cards to check — returning empty conflict result.")
            return {
                "has_conflict": False,
                "conflict_score": 0.0,
                "confidence": 1.0,
                "confidence_label": "high",
                "fallback_to_llm": False,
                "llm_verdict": None,
                "conflicts": [],
            }

        conflicts: List[Dict[str, Any]] = []

        try:
            # Load dynamic layer once and share across all sub-checks.
            dynamic_layer = await self._load_dynamic_layer(db, project_id, chapter_id)

            # ── 1. Baseline conflicts ────────────────────────────────
            base_conflicts = await self._detect_baseline_conflicts(
                cards, dynamic_layer,
            )
            conflicts.extend(base_conflicts)

            # ── 2. Secret matrix conflicts ───────────────────────────
            secret_conflicts = await self._detect_secret_conflicts(
                db, project_id, cards, dynamic_layer,
            )
            conflicts.extend(secret_conflicts)

            # ── 3. State machine conflicts ───────────────────────────
            state_conflicts = await self._detect_state_machine_conflicts(
                db, project_id, cards,
            )
            conflicts.extend(state_conflicts)

        except Exception:
            logger.exception(
                "Conflict detection failed for project=%s chapter=%s — "
                "returning empty conflict result",
                project_id, chapter_id,
            )
            return {
                "has_conflict": False,
                "conflict_score": 0.0,
                "confidence": 0.5,
                "confidence_label": "medium",
                "fallback_to_llm": False,
                "llm_verdict": None,
                "conflicts": [],
            }

        has_conflict = len(conflicts) > 0
        conflict_score = _compute_conflict_score(conflicts)

        # ── Compute confidence via U-curve (§2.4) ───────────────────
        confidence = _compute_confidence(conflict_score)
        confidence_label = _compute_confidence_label(confidence)

        result: Dict[str, Any] = {
            "has_conflict": has_conflict,
            "conflict_score": conflict_score,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "fallback_to_llm": False,
            "llm_verdict": None,
            "conflicts": conflicts,
        }

        # ── LLM fallback for low-confidence results (§2.4) ──────────
        if confidence < _CONFIDENCE_MEDIUM_THRESHOLD:
            logger.info(
                "Confidence=%.4f < 0.3 — triggering LLM fallback "
                "for project=%s chapter=%s",
                confidence, project_id, chapter_id,
            )
            llm_result = await self._llm_fallback_for_conflicts(
                project_id, chapter_id, cards, conflicts, conflict_score,
            )
            result["fallback_to_llm"] = True
            if llm_result is not None:
                result["llm_verdict"] = llm_result.get("verdict")
                result["confidence"] = llm_result.get("confidence", confidence)
                result["confidence_label"] = _compute_confidence_label(
                    result["confidence"]
                )
                # Accept LLM overrides: mark conflicts as overridden if LLM says so
                if llm_result.get("overrides"):
                    result["has_conflict"] = llm_result.get("has_conflict", has_conflict)
                    result["conflict_score"] = llm_result.get("conflict_score", conflict_score)
                    result["conflicts"] = llm_result.get("conflicts", conflicts)

        logger.info(
            "Conflict detection complete: has_conflict=%s score=%s "
            "confidence=%s label=%s fallback=%s count=%d",
            has_conflict, conflict_score, confidence, confidence_label,
            result["fallback_to_llm"], len(conflicts),
        )

        return result

    # ------------------------------------------------------------------
    # Public confidence evaluation
    # ------------------------------------------------------------------

    async def evaluate_confidence(
        self,
        conflict_score: float,
        cards: List[CardPool],
    ) -> Dict[str, Any]:
        """Public method to evaluate confidence for a given conflict score.

        This can be called independently by other services to assess
        confidence without running full conflict detection.

        Parameters
        ----------
        conflict_score:
            A pre-computed conflict score in [0, 1].
        cards:
            Direction cards (used for context, not evaluated here).

        Returns
        -------
        dict with keys ``confidence``, ``confidence_label``, ``fallback_to_llm``.
        """
        confidence = _compute_confidence(conflict_score)
        confidence_label = _compute_confidence_label(confidence)
        fallback_to_llm = confidence < _CONFIDENCE_MEDIUM_THRESHOLD

        logger.debug(
            "evaluate_confidence: score=%.4f confidence=%.4f label=%s fallback=%s "
            "cards=%d",
            conflict_score, confidence, confidence_label, fallback_to_llm, len(cards),
        )

        return {
            "confidence": confidence,
            "confidence_label": confidence_label,
            "fallback_to_llm": fallback_to_llm,
        }

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    async def _load_dynamic_layer(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
    ) -> Optional[DynamicLayer]:
        """Fetch the dynamic layer for the given project+chapter."""
        stmt = select(DynamicLayer).where(
            DynamicLayer.project_id == project_id,
            DynamicLayer.chapter_id == chapter_id,
        )
        result = await db.execute(stmt)
        layer = result.scalar_one_or_none()
        if layer is None:
            logger.debug(
                "No dynamic layer found for project=%s chapter=%s",
                project_id, chapter_id,
            )
        return layer

    # ------------------------------------------------------------------
    # LLM fallback for low-confidence results (§2.4)
    # ------------------------------------------------------------------

    async def _llm_fallback_for_conflicts(
        self,
        project_id: str,
        chapter_id: str,
        cards: List[CardPool],
        conflicts: List[Dict[str, Any]],
        conflict_score: float,
    ) -> Optional[Dict[str, Any]]:
        """Fall back to LLM when rule-based confidence is low.

        Constructs a prompt describing the detected conflicts and asks the
        LLM to judge whether they are genuine narrative conflicts.

        Parameters
        ----------
        project_id:
            Target project UUID (for logging context).
        chapter_id:
            Target chapter UUID (for logging context).
        cards:
            Direction cards that triggered the conflicts.
        conflicts:
            The list of detected conflict items.
        conflict_score:
            The aggregated conflict score.

        Returns
        -------
        dict with keys ``verdict``, ``confidence``, ``overrides``,
        ``has_conflict``, ``conflict_score``, ``conflicts``,
        or ``None`` if the LLM call fails.
        """
        if not conflicts:
            logger.debug("No conflicts to fallback on — skipping LLM call.")
            return None

        try:
            # Build a concise prompt with conflict details
            cards_summary = "\n".join(
                f"- 卡片「{c.name}」: {c.direction_text or '无方向文本'}"
                for c in cards
            )
            conflicts_summary = "\n".join(
                f"- [{c.get('type', 'unknown')}] {c.get('description', '')} "
                f"(严重度: {c.get('severity', 'medium')})"
                for c in conflicts
            )

            system_prompt = (
                "你是一个专业的叙事冲突分析助手。你的任务是判断一组方向卡片与故事动态层之间 "
                "的冲突是否真实存在。"
                "\n\n"
                "请分析以下冲突列表，判断它们是否是真正的叙事冲突：\n"
                "1. 如果冲突是真实的（例如，卡片方向确实会破坏故事连贯性），请回答「真实」\n"
                "2. 如果冲突是误报（例如，卡片方向实际上与约束兼容），请回答「误报」\n"
                "3. 给出一个 0-1 的置信度分数，表示你对判断的把握程度\n\n"
                "请以 JSON 格式回复，格式如下：\n"
                '{"verdict": "真实" 或 "误报", "confidence": 0.0-1.0, '
                '"reasoning": "简要分析原因"}'
            )

            user_prompt = (
                f"项目ID: {project_id}\n"
                f"章节ID: {chapter_id}\n"
                f"冲突评分: {conflict_score:.4f}\n\n"
                f"方向卡片列表:\n{cards_summary}\n\n"
                f"检测到的冲突:\n{conflicts_summary}"
            )

            logger.info(
                "LLM fallback: calling LLM for project=%s chapter=%s "
                "conflict_score=%.4f conflicts=%d",
                project_id, chapter_id, conflict_score, len(conflicts),
            )

            response = await llm_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=get_effective_llm_config()["model"],
                temperature=0.3,
                max_tokens=1024,
            )

            content = response["choices"][0]["message"]["content"]
            logger.debug("LLM fallback response: %s", content[:200])

            # Parse JSON from the response
            parsed = self._parse_llm_response(content)

            if parsed is None:
                logger.warning("LLM fallback: failed to parse response, using defaults")
                return {
                    "verdict": "无法判断",
                    "confidence": 0.5,
                    "overrides": False,
                    "has_conflict": len(conflicts) > 0,
                    "conflict_score": conflict_score,
                    "conflicts": conflicts,
                }

            verdict = parsed.get("verdict", "无法判断")
            llm_confidence = float(parsed.get("confidence", 0.5))
            llm_confidence = max(0.0, min(1.0, llm_confidence))

            logger.info(
                "LLM fallback result: verdict=%s confidence=%.4f",
                verdict, llm_confidence,
            )

            # If LLM says "误报" (false positive), override the conflicts
            is_false_positive = "误报" in verdict or "false" in verdict.lower()

            return {
                "verdict": verdict,
                "confidence": llm_confidence,
                "overrides": is_false_positive,
                "has_conflict": not is_false_positive if is_false_positive
                else len(conflicts) > 0,
                "conflict_score": conflict_score if not is_false_positive else 0.0,
                "conflicts": conflicts if not is_false_positive else [],
            }

        except Exception:
            logger.exception(
                "LLM fallback failed for project=%s chapter=%s — "
                "graceful degradation, keeping original result",
                project_id, chapter_id,
            )
            return None

    @staticmethod
    def _parse_llm_response(content: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response, handling markdown code fences."""
        if not content:
            return None

        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding {...} object directly
        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    # ------------------------------------------------------------------
    # Detection 1: Baseline conflicts
    # ------------------------------------------------------------------

    async def _detect_baseline_conflicts(
        self,
        cards: List[CardPool],
        dynamic_layer: Optional[DynamicLayer],
    ) -> List[Dict[str, Any]]:
        """Check card directions against must_hold / must_not constraints.

        **must_hold** items are things that **must** remain true — if a card
        direction contradicts one, it is a **high** severity conflict.

        **must_not** items are things that **must not** happen — if a card
        direction looks like it would cause one, it is a **high** severity
        conflict.
        """
        if dynamic_layer is None:
            return []

        must_hold: List[str] = dynamic_layer.must_hold or []
        must_not: List[str] = dynamic_layer.must_not or []

        if not must_hold and not must_not:
            return []

        conflicts: List[Dict[str, Any]] = []

        for card in cards:
            direction_text = card.direction_text or ""

            # ── Check must_hold violations ──────────────────────────
            for constraint in must_hold:
                if self._text_contradicts(direction_text, constraint):
                    conflicts.append(
                        _conflict_item(
                            conflict_type="baseline",
                            description=(
                                f"卡片「{card.name}」的方向与连贯性约束"
                                f"「{constraint}」冲突"
                            ),
                            severity="high",
                            suggested_fix=(
                                f"调整方向以避免违反「{constraint}」，"
                                f"或在方向中明确保持该约束"
                            ),
                        )
                    )

            # ── Check must_not violations ────────────────────────────
            for constraint in must_not:
                if self._text_violates_must_not(direction_text, constraint):
                    conflicts.append(
                        _conflict_item(
                            conflict_type="baseline",
                            description=(
                                f"卡片「{card.name}」的方向暗示了"
                                f"应避免的「{constraint}」"
                            ),
                            severity="high",
                            suggested_fix=(
                                f"调整方向以避开「{constraint}」"
                            ),
                        )
                    )

        return conflicts

    @staticmethod
    def _text_contradicts(text: str, constraint: str) -> bool:
        """Check if *text* contradicts a must_hold *constraint*.

        Heuristic: return ``True`` when the direction text contains the
        constraint's core keyword AND any of the known contradiction verbs.
        This allows "师徒决裂" to match constraint "师徒关系" because
        "师徒" is a core substring of both.
        """
        contradict_verbs = [
            "决裂", "反目", "摧毁", "打破", "背叛", "破坏",
            "失去", "放弃", "终结", "推翻", "废除", "消亡",
            "不再", "不再有", "销毁", "撕毁", "打破",
        ]

        # Extract the shortest meaningful core from the constraint
        # by scanning for common relationship / state suffixes.
        core = constraint
        for suffix in ["关系", "协议", "设定", "状态", "约定", "同盟", "规则"]:
            if constraint.endswith(suffix) and len(constraint) > len(suffix):
                core = constraint[: -len(suffix)]
                break

        if core not in text:
            return False

        return any(verb in text for verb in contradict_verbs)

    @staticmethod
    def _text_violates_must_not(text: str, constraint: str) -> bool:
        """Check if *text* suggests or directly mentions a must_not constraint."""
        return constraint in text

    # ------------------------------------------------------------------
    # Detection 2: Secret matrix conflicts
    # ------------------------------------------------------------------

    async def _detect_secret_conflicts(
        self,
        db: AsyncSession,
        project_id: str,
        cards: List[CardPool],
        dynamic_layer: Optional[DynamicLayer],
    ) -> List[Dict[str, Any]]:
        """Check whether a card direction would cause a character to reveal
        something they do not (yet) know.

        The secret matrix is stored in two places:

        * ``DynamicLayer.information_asymmetry`` — a cached summary of
          who-knows-what for the current chapter.
        * ``Secret`` table — the full set of secrets with their
          ``known_by`` / ``unknown_to`` lists.

        This detector uses the ``Secret`` table for accuracy.
        """
        # ── Collect all unique character names referenced across cards ─
        card_character_names: set = set()
        for card in cards:
            for char in (card.characters or []):
                name = char.get("name") if isinstance(char, dict) else None
                if name:
                    card_character_names.add(name)

        if not card_character_names:
            return []

        # ── Load all secrets for the project ────────────────────────
        stmt = select(Secret).where(Secret.project_id == project_id)
        result = await db.execute(stmt)
        secrets: List[Secret] = list(result.scalars().all())

        if not secrets:
            return []

        conflicts: List[Dict[str, Any]] = []

        for secret in secrets:
            known_set = set(secret.known_by or [])
            unknown_set = set(secret.unknown_to or [])

            # Which of the card's characters do NOT yet know this secret?
            characters_who_should_not_know = (
                card_character_names & unknown_set
            )

            for char_name in characters_who_should_not_know:
                # A character who does not know the secret is involved
                # in this card — there is a risk they would reveal it.
                card_names_hint = ", ".join(
                    c.name for c in cards
                )
                conflicts.append(
                    _conflict_item(
                        conflict_type="secret",
                        description=(
                            f"角色「{char_name}」尚不知晓秘密"
                            f"「{secret.description[:60]}…」"
                            f"，但出现在卡片方向中（涉及卡片："
                            f"{card_names_hint}），可能导致信息泄露"
                        ),
                        severity="medium",
                        suggested_fix=(
                            f"确保方向中「{char_name}」的行为不涉及该秘密"
                            f"，或先在故事中铺垫TA获得该信息的契机"
                        ),
                    )
                )

        return conflicts

    # ------------------------------------------------------------------
    # Detection 3: State machine conflicts
    # ------------------------------------------------------------------

    async def _detect_state_machine_conflicts(
        self,
        db: AsyncSession,
        project_id: str,
        cards: List[CardPool],
    ) -> List[Dict[str, Any]]:
        """Check whether a card's character state requirement conflicts
        with the character's current state as recorded in the vault.

        Each ``CardPool.characters`` entry can contain a
        ``state_requirement`` field (e.g. ``"紧张"``, ``"松弛"``,
        ``"重伤"``).

        The ``VaultCharacter.current_state`` reflects the character's
        actual narrative state.  When the two differ significantly, a
        state-machine conflict is raised.
        """
        # ── Build a lookup: character name → state requirement ──────
        char_state_req: Dict[str, str] = {}
        for card in cards:
            for char_entry in (card.characters or []):
                if not isinstance(char_entry, dict):
                    continue
                name = char_entry.get("name")
                req = char_entry.get("state_requirement")
                if name and req:
                    char_state_req[name] = req

        if not char_state_req:
            return []

        # ── Load vault characters for the project ───────────────────
        stmt = select(VaultCharacter).where(
            VaultCharacter.project_id == project_id,
        )
        result = await db.execute(stmt)
        vault_chars: List[VaultCharacter] = list(result.scalars().all())

        # Build a name → VaultCharacter dict
        char_map: Dict[str, VaultCharacter] = {
            vc.name: vc for vc in vault_chars
        }

        conflicts: List[Dict[str, Any]] = []

        for char_name, state_req in char_state_req.items():
            vc = char_map.get(char_name)
            if vc is None:
                logger.debug(
                    "Character %r not found in vault — skipping state check",
                    char_name,
                )
                continue

            current_state = (vc.current_state or "").strip().lower()
            req_state_lower = state_req.strip().lower()

            if not current_state:
                # No recorded state → cannot detect a conflict
                continue

            # ── Detect obvious incompatibility ──────────────────────
            if self._states_conflict(current_state, req_state_lower):
                conflicts.append(
                    _conflict_item(
                        conflict_type="state_machine",
                        description=(
                            f"角色「{char_name}」当前状态为"
                            f"「{vc.current_state}」，但卡片要求状态为"
                            f"「{state_req}」，两者存在冲突"
                        ),
                        severity="medium",
                        suggested_fix=(
                            f"将卡片中「{char_name}」的状态要求改为"
                            f"「{vc.current_state}」，或先完成状态转换"
                        ),
                    )
                )

        return conflicts

    @staticmethod
    def _states_conflict(current: str, required: str) -> bool:
        """Return ``True`` when *current* and *required* are semantically
        incompatible.

        Uses a simple antonym-pair heuristic.  Expand the antonyms dict
        as needed for the project's domain.
        """
        # ── Define common antonym pairs ─────────────────────────────
        antonym_pairs = [
            ("高兴", "悲伤"), ("快乐", "痛苦"), ("平静", "愤怒"),
            ("紧张", "松弛"), ("放松", "焦虑"), ("开心", "难过"),
            ("健康", "受伤"), ("健康", "重伤"), ("活着", "死亡"),
            ("清醒", "昏迷"), ("友善", "敌对"), ("信任", "怀疑"),
        ]

        for a, b in antonym_pairs:
            if (a in current and b in required) or (b in current and a in required):
                return True

        # Direct equality → no conflict
        if current == required:
            return False

        return False


# Singleton instance for ``Depends()`` injection
conflict_detection_service = ConflictDetectionService()
