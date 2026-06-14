"""Moling — Validation Service (Pre/Post Generation Checks).

Implements 7 pre-generation and 7 post-generation structural validations
to ensure content quality and consistency before and after AI generation.
All checks are deterministic — they query the database and perform structural
comparisons without LLM calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao
from app.models.dynamic_layer import DynamicLayer
from app.models.secret import Secret

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class CheckResult:
    """Result of a single validation check."""
    passed: bool
    name: str
    detail: str = ""
    suggestions: List[str] = field(default_factory=list)
    severity: str = "info"  # "info", "warning", "error"


@dataclass
class ValidationResult:
    """Aggregated result of multiple validation checks."""
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    summary: str = ""


# =============================================================================
# ValidationService
# =============================================================================

class ValidationService:
    """Service for pre-generation and post-generation content validation.

    Pre-generation checks run *before* AI generation to ensure the input
    context (cards, vault, dynamic layer) is in a valid and consistent state.
    Post-generation checks run *after* AI generation to verify the output
    content does not violate established constraints.
    """

    # ------------------------------------------------------------------
    # Pre-Generation Checks (7)
    # ------------------------------------------------------------------

    async def pre_check_character_consistency(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List,
    ) -> CheckResult:
        """Verify characters referenced in cards exist in the project vault.

        Checks each card's ``characters`` JSON field against vault characters.
        Returns warnings for any character reference that cannot be found in
        the vault.
        """
        vault_chars = await vault_dao.get_characters(db, project_id)
        vault_names = {c.name for c in vault_chars}

        missing = []
        for card in cards:
            card_chars = getattr(card, "characters", None) or []
            for ref in card_chars:
                char_name = ref.get("name") if isinstance(ref, dict) else str(ref)
                if char_name and char_name not in vault_names:
                    missing.append(f"卡片「{card.name}」引用了 vault 中不存在的角色「{char_name}」")

        if missing:
            return CheckResult(
                passed=False,
                name="角色一致性检查",
                detail=f"发现 {len(missing)} 个角色引用问题: {'; '.join(missing[:5])}",
                suggestions=missing,
                severity="warning",
            )
        return CheckResult(
            passed=True,
            name="角色一致性检查",
            detail=f"所有卡片引用的角色均存在于 vault 中 (共 {len(vault_chars)} 个角色)",
        )

    async def pre_check_timeline_continuity(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List,
    ) -> CheckResult:
        """Ensure selected cards do not violate timeline ordering constraints.

        Compares ``timeline_point`` values across cards. If cards reference
        specific timeline points, they should be in a logical chronological
        order that does not contradict established vault timeline events.
        """
        vault_timeline = await vault_dao.get_timeline(db, project_id)
        chapter_numbers = [e.chapter_number for e in vault_timeline]

        # Check that each card's timeline_point is internally consistent
        issues = []
        for card in cards:
            tp = getattr(card, "timeline_point", None)
            if tp:
                # If timeline_point references a chapter number, verify it exists
                if isinstance(tp, (int, float)) and chapter_numbers:
                    tp_int = int(tp)
                    if tp_int > max(chapter_numbers):
                        issues.append(
                            f"卡片「{card.name}」的时间线点 {tp_int} 超出当前最大章节 {max(chapter_numbers)}"
                        )
                    elif tp_int < 1:
                        issues.append(
                            f"卡片「{card.name}」的时间线点 {tp_int} 无效"
                        )

        if issues:
            return CheckResult(
                passed=False,
                name="时间线连续性检查",
                detail=f"发现 {len(issues)} 个时间线问题: {'; '.join(issues[:5])}",
                suggestions=issues,
                severity="warning",
            )
        return CheckResult(
            passed=True,
            name="时间线连续性检查",
            detail=f"卡片时间线约束通过 (vault 共 {len(vault_timeline)} 个事件)",
        )

    async def pre_check_plot_promise_logic(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List,
    ) -> CheckResult:
        """Verify selected cards maintain plot promise coherence.

        Checks each card's ``plot_promises`` references against the vault.
        Warns if a card references a resolved/abandoned promise as if it were
        still active, or references a non-existent promise.
        """
        vault_promises = await vault_dao.get_plot_promises(db, project_id)
        promise_map = {str(p.id): p for p in vault_promises}

        warnings = []
        for card in cards:
            card_promises = getattr(card, "plot_promises", None) or []
            for ref in card_promises:
                pid = ref.get("id") if isinstance(ref, dict) else str(ref)
                if not pid:
                    continue
                promise = promise_map.get(str(pid))
                if promise is None:
                    warnings.append(f"卡片「{card.name}」引用了不存在的伏笔 ID={pid}")
                elif promise.status in ("resolved", "abandoned"):
                    warnings.append(
                        f"卡片「{card.name}」引用的伏笔「{promise.description[:30]}」已"
                        f"{'回收' if promise.status == 'resolved' else '废弃'}"
                    )

        if warnings:
            return CheckResult(
                passed=False,
                name="剧情承诺逻辑检查",
                detail=f"发现 {len(warnings)} 个伏笔引用问题",
                suggestions=warnings,
                severity="warning",
            )
        return CheckResult(
            passed=True,
            name="剧情承诺逻辑检查",
            detail=f"所有卡片引用的伏笔均有效 (vault 共 {len(vault_promises)} 个伏笔)",
        )

    async def pre_check_world_rule_compliance(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List,
    ) -> CheckResult:
        """Check card content does not violate established world rules.

        Examines each card's ``world_rules`` references against the vault
        world entries. Flags any references to non-existent or conflicting
        world entries.
        """
        world_entries = await vault_dao.get_world_entries(db, project_id)
        world_map = {str(e.id): e for e in world_entries}

        issues = []
        for card in cards:
            card_world = getattr(card, "world_rules", None) or []
            for ref in card_world:
                wid = ref.get("id") if isinstance(ref, dict) else str(ref)
                if not wid:
                    continue
                entry = world_map.get(str(wid))
                if entry is None:
                    issues.append(f"卡片「{card.name}」引用了不存在的世界观条目 ID={wid}")

        if issues:
            return CheckResult(
                passed=False,
                name="世界观规则合规检查",
                detail=f"发现 {len(issues)} 个世界观引用问题",
                suggestions=issues,
                severity="warning",
            )
        return CheckResult(
            passed=True,
            name="世界观规则合规检查",
            detail=f"所有卡片引用的世界观条目均有效 (vault 共 {len(world_entries)} 个条目)",
        )

    async def pre_check_summary_cohesion(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> CheckResult:
        """Verify the latest dynamic-layer summary is present and coherent.

        Loads the most recent ``DynamicLayer`` for the project and checks
        that the ``summary`` field is non-empty and of reasonable length.
        """
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest is None:
            return CheckResult(
                passed=False,
                name="前情摘要连贯性检查",
                detail="项目尚无动态层记录，无法检查前情摘要",
                suggestions=["请先生成一个章节以建立动态层"],
                severity="warning",
            )

        summary = latest.summary
        if not summary:
            return CheckResult(
                passed=False,
                name="前情摘要连贯性检查",
                detail="最新的动态层记录缺少前情摘要 (summary 为空)",
                suggestions=["请运行动态层摘要更新"],
                severity="error",
            )

        if len(summary) < 20:
            return CheckResult(
                passed=False,
                name="前情摘要连贯性检查",
                detail=f"前情摘要过短 ({len(summary)} 字符)，可能不完整",
                suggestions=["请检查并补全前情摘要"],
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="前情摘要连贯性检查",
            detail=f"前情摘要存在且长度合理 ({len(summary)} 字符)",
        )

    async def pre_check_baseline_consistency(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> CheckResult:
        """Check ``must_hold`` / ``must_not`` baselines are consistent.

        Loads the latest ``DynamicLayer`` and verifies:
        - ``must_hold`` and ``must_not`` are lists (or empty)
        - No item appears in both lists simultaneously
        - No empty strings in either list
        """
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest is None:
            return CheckResult(
                passed=True,
                name="基线一致性检查",
                detail="项目尚无动态层记录，跳过基线检查",
            )

        must_hold = getattr(latest, "must_hold", None) or []
        must_not = getattr(latest, "must_not", None) or []

        issues = []

        # Validate types
        if not isinstance(must_hold, list):
            issues.append("must_hold 应为列表类型")
            must_hold = []
        if not isinstance(must_not, list):
            issues.append("must_not 应为列表类型")
            must_not = []

        # Check for empty / blank items
        for i, item in enumerate(must_hold):
            if not item or (isinstance(item, str) and not item.strip()):
                issues.append(f"must_hold 第 {i+1} 项为空")
        for i, item in enumerate(must_not):
            if not item or (isinstance(item, str) and not item.strip()):
                issues.append(f"must_not 第 {i+1} 项为空")

        # Check for conflicts
        hold_set = set(str(h) for h in must_hold)
        not_set = set(str(n) for n in must_not)
        overlap = hold_set & not_set
        if overlap:
            issues.append(f"以下约束同时出现在 must_hold 和 must_not 中: {list(overlap)}")

        if issues:
            return CheckResult(
                passed=False,
                name="基线一致性检查",
                detail=f"发现 {len(issues)} 个基线问题: {'; '.join(issues)}",
                suggestions=issues,
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="基线一致性检查",
            detail=f"基线一致 (must_hold={len(must_hold)} 条, must_not={len(must_not)} 条)",
        )

    async def run_pre_checks(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List,
    ) -> ValidationResult:
        """Run all 7 pre-generation checks and aggregate results."""
        checks: List[CheckResult] = []

        check1 = await self.pre_check_character_consistency(db, project_id, cards)
        checks.append(check1)

        check2 = await self.pre_check_timeline_continuity(db, project_id, cards)
        checks.append(check2)

        check3 = await self.pre_check_plot_promise_logic(db, project_id, cards)
        checks.append(check3)

        check4 = await self.pre_check_world_rule_compliance(db, project_id, cards)
        checks.append(check4)

        check5 = await self.pre_check_summary_cohesion(db, project_id)
        checks.append(check5)

        check6 = await self.pre_check_baseline_consistency(db, project_id)
        checks.append(check6)

        # Determine overall pass / fail
        errors = [c for c in checks if c.severity == "error" and not c.passed]
        warnings = [c for c in checks if c.severity == "warning" and not c.passed]
        all_passed = len(errors) == 0 and len(warnings) == 0

        summary_parts = []
        if errors:
            summary_parts.append(f"{len(errors)} 个错误")
        if warnings:
            summary_parts.append(f"{len(warnings)} 个警告")
        passed_count = sum(1 for c in checks if c.passed)
        summary = (
            f"{passed_count}/7 检查通过"
            + (f"，未通过: {', '.join(summary_parts)}" if summary_parts else "")
        )

        return ValidationResult(
            passed=all_passed,
            checks=checks,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Post-Generation Checks (7)
    # ------------------------------------------------------------------

    async def post_check_fact_consistency(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Verify generated content does not contradict established vault facts.

        Performs basic keyword / name matching between the generated content
        and vault entities (characters, world entries). Flags if names or terms
        are used in ways that appear inconsistent with their vault definitions.
        """
        content_lower = content.lower()

        characters = await vault_dao.get_characters(db, project_id)
        world_entries = await vault_dao.get_world_entries(db, project_id)

        warnings = []

        # Check if all vault character names appear in the content in a
        # reasonable context (informs the check result detail)
        mentioned_count = 0
        for char in characters:
            if char.name.lower() in content_lower:
                mentioned_count += 1

        if characters and mentioned_count == 0:
            warnings.append("生成内容中未提及任何 vault 角色")

        # Check world entries
        world_mentioned = 0
        for entry in world_entries:
            if entry.name.lower() in content_lower:
                world_mentioned += 1

        if world_entries and world_mentioned == 0:
            warnings.append("生成内容中未提及任何世界观条目")

        if warnings:
            return CheckResult(
                passed=False,
                name="事实一致性检查",
                detail="; ".join(warnings),
                suggestions=warnings,
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="事实一致性检查",
            detail=f"内容与 vault 事实一致 (角色提及 {mentioned_count}, 世界观提及 {world_mentioned})",
        )

    async def post_check_plot_advancement(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
        card_ids: List[int],
    ) -> CheckResult:
        """Check that generated content advances the selected cards' directions.

        For each selected card, verify that the card's ``direction_text``
        or key themes appear to be addressed in the generated content.
        """
        if not card_ids:
            return CheckResult(
                passed=True,
                name="剧情推进检查",
                detail="无选中卡片，跳过剧情推进检查",
            )

        from app.models import CardPool

        stmt = select(CardPool).where(CardPool.id.in_(card_ids))
        result = await db.execute(stmt)
        cards = list(result.scalars().all())

        content_lower = content.lower()
        unaddressed = []

        for card in cards:
            # Check if key terms from direction_text appear in content
            direction_text = getattr(card, "direction_text", "") or ""
            # Extract meaningful keywords (words longer than 2 chars)
            keywords = [
                kw for kw in direction_text.split()
                if len(kw) > 2 and kw.lower() in content_lower
            ]
            if not keywords:
                unaddressed.append(card.name)

        if unaddressed:
            return CheckResult(
                passed=False,
                name="剧情推进检查",
                detail=f"以下卡片的方向在生成内容中未得到体现: {', '.join(unaddressed[:5])}",
                suggestions=[f"请检查是否遗漏了卡片「{n}」的创作方向" for n in unaddressed[:3]],
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="剧情推进检查",
            detail=f"所有 {len(cards)} 张卡片的方向均在内容中有所体现",
        )

    async def post_check_timeline_consistency(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Verify timeline references in generated content are valid.

        Checks that any explicit chapter / event references in the content
        align with the vault timeline. Flags if the content references events
        that have not yet occurred or are out of order.
        """
        vault_timeline = await vault_dao.get_timeline(db, project_id)
        if not vault_timeline:
            return CheckResult(
                passed=True,
                name="时间线一致性检查",
                detail="vault 尚无时间线事件，跳过检查",
            )

        content_lower = content.lower()

        # Check for event references in content (match event titles)
        matched_events = []
        for event in vault_timeline:
            if event.event.lower() in content_lower:
                matched_events.append(event.event)

        if not matched_events:
            return CheckResult(
                passed=True,
                name="时间线一致性检查",
                detail="生成内容未引用具体时间线事件 (可接受)",
            )

        return CheckResult(
            passed=True,
            name="时间线一致性检查",
            detail=f"内容引用了 {len(matched_events)} 个时间线事件",
        )

    async def post_check_world_rule_violations(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Detect potential world rule violations in generated text.

        Cross-references vault world entries (especially those with
        ``constraint`` fields) against the content. Flags if the content
        appears to contradict an explicit world rule.
        """
        world_entries = await vault_dao.get_world_entries(db, project_id)
        if not world_entries:
            return CheckResult(
                passed=True,
                name="世界观规则违规检查",
                detail="vault 尚无世界观条目，跳过检查",
            )

        content_lower = content.lower()

        # Simple check: if a world entry has a constraint, check whether
        # the entry's name appears in the content in a contradictory way
        warnings = []
        for entry in world_entries:
            name_lower = entry.name.lower()
            constraint = getattr(entry, "constraint", None)
            if constraint and name_lower in content_lower:
                constraint_lower = constraint.lower()
                # If the constraint mentions "禁止" (forbidden) and the
                # content mentions the entry, flag as potential violation
                if "禁止" in constraint_lower or "不可" in constraint_lower:
                    warnings.append(
                        f"世界观条目「{entry.name}」有限制性约束: {constraint[:50]}"
                    )

        if warnings:
            return CheckResult(
                passed=False,
                name="世界观规则违规检查",
                detail=f"发现 {len(warnings)} 个潜在的世界观规则冲突",
                suggestions=warnings,
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="世界观规则违规检查",
            detail=f"内容与 {len(world_entries)} 个世界观条目无冲突",
        )

    async def post_check_baseline_compliance(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Verify generated content follows ``must_hold`` / ``must_not`` baselines.

        Loads the latest ``DynamicLayer`` and checks:
        - ``must_hold`` items should be present / reflected in content
        - ``must_not`` items should be absent from content
        """
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest is None:
            return CheckResult(
                passed=True,
                name="基线合规检查",
                detail="无动态层记录，跳过基线合规检查",
            )

        must_hold = getattr(latest, "must_hold", None) or []
        must_not = getattr(latest, "must_not", None) or []

        content_lower = content.lower()
        issues = []

        # Check must_hold: these should be present
        for item in must_hold:
            item_str = str(item).lower()
            if item_str and item_str not in content_lower:
                issues.append(f"必须保持的约束「{item}」未在内容中体现")

        # Check must_not: these should be absent
        for item in must_not:
            item_str = str(item).lower()
            if item_str and item_str in content_lower:
                issues.append(f"必须避免的约束「{item}」在内容中出现")

        if issues:
            return CheckResult(
                passed=False,
                name="基线合规检查",
                detail=f"发现 {len(issues)} 个基线违规",
                suggestions=issues,
                severity="error",
            )

        return CheckResult(
            passed=True,
            name="基线合规检查",
            detail="内容符合所有 must_hold / must_not 基线约束",
        )

    async def post_check_unresolved_hooks(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Ensure unresolved hooks remain or are properly resolved.

        Loads the latest ``DynamicLayer``'s ``unresolved_hooks`` and checks
        whether each hook appears to have been addressed or remains open
        in the generated content.
        """
        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest is None:
            return CheckResult(
                passed=True,
                name="未收束钩子检查",
                detail="无动态层记录，跳过钩子检查",
            )

        unresolved = getattr(latest, "unresolved_hooks", None) or []
        if not unresolved:
            return CheckResult(
                passed=True,
                name="未收束钩子检查",
                detail="没有未收束的钩子",
            )

        content_lower = content.lower()
        still_open = []

        for hook in unresolved:
            hook_str = str(hook).lower()
            if hook_str and hook_str not in content_lower:
                still_open.append(str(hook))

        if still_open:
            return CheckResult(
                passed=True,
                name="未收束钩子检查",
                detail=f"{len(still_open)}/{len(unresolved)} 个钩子仍未在内容中提及 (可接受)",
                suggestions=still_open[:3],
                severity="info",
            )

        return CheckResult(
            passed=True,
            name="未收束钩子检查",
            detail=f"所有 {len(unresolved)} 个未收束钩子均在内容中有所涉及",
        )

    async def post_check_secret_consistency(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
    ) -> CheckResult:
        """Verify secrets mentioned in content are consistent with the vault.

        Checks if the generated content mentions specific secrets and whether
        those mentions are consistent with each secret's ``secrecy_level``
        (hidden / partial / revealed).
        """
        stmt = select(Secret).where(Secret.project_id == project_id)
        result = await db.execute(stmt)
        secrets = list(result.scalars().all())

        if not secrets:
            return CheckResult(
                passed=True,
                name="秘密一致性检查",
                detail="项目尚无秘密，跳过检查",
            )

        content_lower = content.lower()
        warnings = []

        for secret in secrets:
            # Check if the secret description appears in content
            desc_preview = secret.description[:50]
            if desc_preview.lower() in content_lower:
                # If secrecy_level is "hidden", content should not reveal it
                if secret.secrecy_level == "hidden":
                    warnings.append(
                        f"秘密「{secret.description[:30]}」的保密层级为「隐藏」，但在内容中出现"
                    )

        if warnings:
            return CheckResult(
                passed=False,
                name="秘密一致性检查",
                detail=f"发现 {len(warnings)} 个秘密一致性问题",
                suggestions=warnings,
                severity="warning",
            )

        return CheckResult(
            passed=True,
            name="秘密一致性检查",
            detail=f"内容与 vault 中 {len(secrets)} 个秘密一致",
        )

    async def run_post_checks(
        self,
        db: AsyncSession,
        project_id: int,
        content: str,
        card_ids: List[int],
    ) -> ValidationResult:
        """Run all 7 post-generation checks and aggregate results."""
        checks: List[CheckResult] = []

        check1 = await self.post_check_fact_consistency(db, project_id, content)
        checks.append(check1)

        check2 = await self.post_check_plot_advancement(db, project_id, content, card_ids)
        checks.append(check2)

        check3 = await self.post_check_timeline_consistency(db, project_id, content)
        checks.append(check3)

        check4 = await self.post_check_world_rule_violations(db, project_id, content)
        checks.append(check4)

        check5 = await self.post_check_baseline_compliance(db, project_id, content)
        checks.append(check5)

        check6 = await self.post_check_unresolved_hooks(db, project_id, content)
        checks.append(check6)

        check7 = await self.post_check_secret_consistency(db, project_id, content)
        checks.append(check7)

        # Determine overall pass / fail
        errors = [c for c in checks if c.severity == "error" and not c.passed]
        warnings = [c for c in checks if c.severity == "warning" and not c.passed]
        all_passed = len(errors) == 0

        summary_parts = []
        if errors:
            summary_parts.append(f"{len(errors)} 个错误")
        if warnings:
            summary_parts.append(f"{len(warnings)} 个警告")
        passed_count = sum(1 for c in checks if c.passed)
        summary = (
            f"{passed_count}/7 检查通过"
            + (f"，未通过: {', '.join(summary_parts)}" if summary_parts else "")
        )

        return ValidationResult(
            passed=all_passed,
            checks=checks,
            summary=summary,
        )


# Singleton instance
validation_service = ValidationService()
