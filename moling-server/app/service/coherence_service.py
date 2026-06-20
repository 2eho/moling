"""Moling - Coherence Validation Service.

Implements post-generation coherence checks using v2 grouped checks
(3 merged LLM calls instead of 8 individual checks).

Validates: narrative consistency (character + timeline + plot promise),
writing quality (world rule + style + pacing + baseline),
and continuity (chapter transition + secret debt).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, vault_dao, secret_dao, dynamic_layer_dao
from app.errors import NotFoundError, ErrorCode, AppError
from app.models import Project, Chapter, Secret
from app.llm.client import llm_client
from app.schemas.coherence import (
    CoherenceCheckItem,
    CoherenceGroupCheck,
    CoherenceValidationResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class CoherenceService:
    """Service for coherence validation (post-generation, v2 grouped checks)."""

    async def validate_post_generation(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Post-generation coherence validation (3 grouped LLM calls, v2).
        
        Groups the 8 individual checks into 3 merged LLM calls:
          Group A: Narrative Consistency (character + timeline + plot promise)
          Group B: Writing Quality (world rule + style + pacing + baseline)
          Group C: Continuity (chapter transition + secret debt)
        
        All 3 groups share an identical prompt prefix built by
        _build_coherence_context, enabling DeepSeek transparent prefix
        caching: the shared prefix is billed only once after the first
        group completes.
        
        Returns a dict matching CoherenceValidationResult schema for backward
        compatibility with the pipeline's _step10_coherence_validation.
        
        Returns:
            Dict with keys: passed, overall_score, version, groups
        """
        result = CoherenceValidationResult()
        result.version = "v2-grouped"
        
        try:
            # Get project and chapter
            project = await project_dao.get(db, project_id)
            if project is None:
                raise NotFoundError(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    detail="Project not found",
                )
            
            chapter = await chapter_dao.get(db, chapter_id)
            if chapter is None:
                raise NotFoundError(
                    error_code=ErrorCode.CHAPTER_NOT_FOUND,
                    detail="Chapter not found",
                )
            
            # Get previous chapter
            previous_chapter = None
            if chapter.chapter_number > 1:
                previous_chapter = await chapter_dao.get_by_number(
                    db, project_id, chapter.chapter_number - 1
                )
            
            # Build shared context ONCE — all 3 groups reuse this
            ctx = await self._build_coherence_context(
                db, project, chapter, generated_content
            )
            
            # ===== Group A: Narrative Consistency =====
            logger.info(f"Post-validation: Group A - Narrative consistency for chapter {chapter_id}")
            group_a = await self._check_group_narrative_consistency(
                ctx, project, chapter
            )
            result.groups.append(group_a)
            
            # ===== Group B: Writing Quality + Baseline Compliance =====
            logger.info(f"Post-validation: Group B - Writing quality for chapter {chapter_id}")
            group_b = await self._check_group_writing_quality(
                ctx, project, chapter, previous_chapter
            )
            result.groups.append(group_b)
            
            # ===== Group C: Continuity =====
            logger.info(f"Post-validation: Group C - Continuity for chapter {chapter_id}")
            group_c = await self._check_group_continuity(
                db, ctx, project, chapter, previous_chapter, generated_content
            )
            result.groups.append(group_c)
            
            # Calculate overall result
            all_passed = all(g.passed for g in result.groups)
            total_score = sum(g.score for g in result.groups)
            avg_score = total_score / len(result.groups) if result.groups else 1.0
            
            result.passed = all_passed
            result.overall_score = round(avg_score, 2)
            
            logger.info(
                f"Post-validation completed for chapter {chapter_id}: "
                f"passed={all_passed}, score={avg_score:.2f}"
            )
            return result.model_dump()
            
        except Exception as e:
            logger.error(f"Post-validation failed: {e}", exc_info=True)
            result.passed = False
            result.overall_score = 0.0
            return result.model_dump()

    # ===== Grouped Check Implementations (v2 merged) =====

    async def _build_coherence_context(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, str]:
        """Build shared context dict used as the common prefix for all 3 groups.

        DeepSeek transparent prefix caching: all 3 groups share this exact
        prefix text, so Groups B and C automatically benefit from cache hits
        once the public prefix is detected and persisted by the API layer.

        Returns a dict with pre-formatted string sections:
          - shared_prefix: the complete prefix text (identical across groups)
          - character_list, timeline_summary, promise_summary, world_summary,
            baseline_text: individual sections for flexible re-assembly
        """
        # Character list
        characters = await vault_dao.get_characters(db, project.id)
        character_list = ", ".join([c.name for c in characters[:10]]) if characters else "暂无角色"

        # Timeline events (last 10)
        vault_events = await vault_dao.get_timeline(db, project.id)
        timeline_summary = "\n".join([
            f"- 第{e.chapter_number}章: {e.event}"
            for e in vault_events[-10:]
        ]) if vault_events else "暂无"

        # Active plot promises (top 8)
        promises = await vault_dao.get_plot_promises(db, project.id)
        active_promises = [p for p in promises if p.status in ["dormant", "active"]]
        promise_summary = "\n".join([
            f"- [{p.type}] {p.description[:100] or '无描述'} (状态: {p.status}, 紧迫度: {p.urgency})"
            for p in active_promises[:8]
        ]) if active_promises else "无活跃伏笔"

        # World rules
        world_entries = await vault_dao.get_world_entries(db, project.id)
        world_summary = "\n".join([
            f"- [{e.category}] {e.name}: {e.description[:150] or '无描述'}"
            + (f" (约束: {e.constraint[:100]})" if e.constraint else "")
            for e in world_entries[:8]
        ]) if world_entries else "无世界观设定"

        # Dynamic layer baseline (must_hold / must_not) — §5.2 item ⑤
        latest_dl = await dynamic_layer_dao.get_latest_by_project(db, str(project.id))

        must_hold_list = (latest_dl.must_hold or []) if latest_dl else []
        must_not_list = (latest_dl.must_not or []) if latest_dl else []

        baseline_text = ""
        if must_hold_list or must_not_list:
            must_hold_str = "\n".join(f"  - {item}" for item in must_hold_list) if must_hold_list else "无"
            must_not_str = "\n".join(f"  - {item}" for item in must_not_list) if must_not_list else "无"
            baseline_text = (
                f"【连贯性基线】\n"
                f"必须保持(must_hold):\n{must_hold_str}\n"
                f"必须避免(must_not):\n{must_not_str}\n"
            )

        # Assemble the shared prefix — IDENTICAL for all 3 groups
        content_len = len(generated_content)
        shared_prefix = (
            f"项目：{project.title}\n"
            f"当前章节：第{chapter.chapter_number}章《{chapter.title}》\n"
            f"章节长度：{content_len} 字\n\n"
            f"【本章全文】\n"
            f"{generated_content[:4000]}\n\n"
            f"【全量剧本数据】\n"
            f"角色列表：{character_list}\n\n"
            f"时间线事件：\n{timeline_summary}\n\n"
            f"活跃伏笔：\n{promise_summary}\n\n"
            f"世界观设定：\n{world_summary}\n\n"
            f"{baseline_text}"
        )

        return {
            "shared_prefix": shared_prefix,
            "character_list": character_list,
            "timeline_summary": timeline_summary,
            "promise_summary": promise_summary,
            "world_summary": world_summary,
            "baseline_text": baseline_text,
            "must_hold": must_hold_list,
            "must_not": must_not_list,
        }

    async def _check_group_narrative_consistency(
        self,
        ctx: Dict[str, str],
        project: Project,
        chapter: Chapter,
    ) -> CoherenceGroupCheck:
        """Group A: Narrative Consistency - merged check for Character + Timeline + Plot Promise.

        Uses the shared context from _build_coherence_context and appends
        only the Group-A-specific check instructions, enabling DeepSeek
        prefix caching across groups.

        Cross-referencing benefit: character location vs timeline events,
        plot promise implications for character behavior.
        """
        group = CoherenceGroupCheck(
            group_name="narrative_consistency",
            display_name="叙事一致性",
        )

        try:
            prompt = f"""{ctx["shared_prefix"]}
【检查项目 — 叙事一致性】
请对本章内容执行以下 3 项检查：

检查 1 — 角色行为一致性
角色列表：{ctx["character_list"]}
检查角色行为是否符合其性格设定和当前状态。

检查 2 — 时间线连续性
现有时间线事件：
{ctx["timeline_summary"]}
检查事件顺序是否合理，是否存在时间逻辑矛盾。

检查 3 — 伏笔状态
活跃伏笔列表：
{ctx["promise_summary"]}
检查本章是否推进了活跃伏笔，或产生了新伏笔。

请逐项检查，并返回如下 JSON 格式（只返回 JSON，不要其他内容）：
{{
  "checks": [
    {{
      "check_name": "character_consistency",
      "display_name": "角色行为一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "timeline_continuity",
      "display_name": "时间线连续性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "plot_promise_status",
      "display_name": "伏笔状态",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现（如角色出现在时间线矛盾的位置）"]或[]
}}
"""
            response = await self._call_llm(prompt, max_tokens=3072)
            result = json.loads(response)
            raw_checks = result.get("checks", []) if isinstance(result, dict) else []

            for raw in raw_checks:
                group.checks.append(CoherenceCheckItem(
                    check_name=raw.get("check_name", "unknown"),
                    display_name=raw.get("display_name", ""),
                    passed=raw.get("passed", True),
                    score=raw.get("score", 0.9),
                    issues=raw.get("issues", []),
                ))

            group.cross_cutting_issues = result.get("cross_cutting_issues", []) if isinstance(result, dict) else []

            # Aggregate group score
            if group.checks:
                group.score = round(sum(c.score for c in group.checks) / len(group.checks), 2)
                group.passed = all(c.passed for c in group.checks)

        except Exception as e:
            logger.error(f"Group A (narrative consistency) failed: {e}", exc_info=True)
            group.checks = [
                CoherenceCheckItem(check_name="character_consistency", display_name="角色行为一致性", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="timeline_continuity", display_name="时间线连续性", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="plot_promise_status", display_name="伏笔状态", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
            ]
            group.passed = False
            group.score = 0.0

        return group

    async def _check_group_writing_quality(
        self,
        ctx: Dict[str, str],
        project: Project,
        chapter: Chapter,
        previous_chapter: Optional[Chapter],
    ) -> CoherenceGroupCheck:
        """Group B: Writing Quality + Baseline Compliance (§5.2 item ⑤).

        Merged check for World Rule + Style + Pacing + must_hold/must_not.
        Uses shared context from _build_coherence_context.
        """
        group = CoherenceGroupCheck(
            group_name="writing_quality",
            display_name="写作质量",
        )

        try:
            # Previous chapter style reference
            prev_style_ref = ""
            if previous_chapter and previous_chapter.content:
                prev_style_ref = previous_chapter.content[:1500]

            # Build baseline section and instructions
            if ctx.get("baseline_text"):
                baseline_section = ctx["baseline_text"]
                baseline_instruction = """【检查 4 — 连贯性基线校验】
检查本章内容是否违反了 must_hold（必须保持）和 must_not（必须避免）的硬约束。如有违反，需定位到具体段落并引用被违反的基线条目。如无基线约束，此项直接通过。"""
            else:
                baseline_section = "【连贯性基线】\n无基线约束设定（此项直接通过）\n"
                baseline_instruction = ""

            prompt = f"""请对以下小说章节内容执行写作质量检查，并以 JSON 格式返回结果。

{ctx["shared_prefix"]}

【检查 1 — 世界观规则一致性】
世界观设定条目：
{ctx["world_summary"]}
检查内容是否与世界观设定一致，有无违规描述。

【检查 2 — 文风一致性】
前序章节内容（前1500字，无前序章节则检查文风内部一致性）：
{prev_style_ref or "（无前序章节）"}

【检查 3 — 叙事节奏合理性】

{baseline_section}
{baseline_instruction}

请逐项检查，并返回如下 JSON 格式（只返回 JSON，不要其他内容）：
{{
  "checks": [
    {{
      "check_name": "world_rule_consistency",
      "display_name": "世界观规则一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体违规描述"]或[]
    }},
    {{
      "check_name": "writing_style_consistency",
      "display_name": "文风一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体差异描述"]或[]
    }},
    {{
      "check_name": "narrative_pacing",
      "display_name": "叙事节奏",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "baseline_compliance",
      "display_name": "连贯性基线校验",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["违反的基线条目及定位段落"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现（如基线约束与世界观规则的联动问题）"]或[]
}}
"""
            response = await self._call_llm(prompt, max_tokens=3072)
            result = json.loads(response)
            raw_checks = result.get("checks", []) if isinstance(result, dict) else []

            for raw in raw_checks:
                group.checks.append(CoherenceCheckItem(
                    check_name=raw.get("check_name", "unknown"),
                    display_name=raw.get("display_name", ""),
                    passed=raw.get("passed", True),
                    score=raw.get("score", 0.9),
                    issues=raw.get("issues", []),
                ))

            group.cross_cutting_issues = result.get("cross_cutting_issues", []) if isinstance(result, dict) else []

            if group.checks:
                group.score = round(sum(c.score for c in group.checks) / len(group.checks), 2)
                group.passed = all(c.passed for c in group.checks)

        except Exception as e:
            logger.error(f"Group B (writing quality) failed: {e}", exc_info=True)
            group.checks = [
                CoherenceCheckItem(check_name="world_rule_consistency", display_name="世界观规则一致性", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="writing_style_consistency", display_name="文风一致性", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="narrative_pacing", display_name="叙事节奏", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="baseline_compliance", display_name="连贯性基线校验", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
            ]
            group.passed = False
            group.score = 0.0

        return group

    async def _check_group_continuity(
        self,
        db: AsyncSession,
        ctx: Dict[str, str],
        project: Project,
        chapter: Chapter,
        previous_chapter: Optional[Chapter],
        generated_content: str,
    ) -> CoherenceGroupCheck:
        """Group C: Continuity - merged check for Chapter Transition + Secret Debt.

        Uses the shared context for the prefix, then appends the
        dynamic secret debt data (rule-based calculation per §5.2 item ⑦).

        Rule-based secret debt calculation is done before the LLM call;
        the LLM handles secret leakage detection and chapter transition quality.
        """
        group = CoherenceGroupCheck(
            group_name="continuity",
            display_name="连续性",
        )

        try:
            # --- Chapter transition context ---
            prev_end = ""
            if previous_chapter and previous_chapter.content:
                prev_end = previous_chapter.content[-1000:]

            new_start = generated_content[:1000]

            # --- Secret debt calculation (rule-based, §2.8.2 + §5.2) ---
            secrets = await secret_dao.list_by_project(db, project.id)

            secret_debt_issues: list[str] = []
            secrets_for_llm: list[Secret] = []

            if secrets:
                current_chapter_num = chapter.chapter_number
                for secret in secrets:
                    if secret.secrecy_level in ("revealed", "open"):
                        continue
                    if secret.created_chapter is None:
                        continue

                    secrets_for_llm.append(secret)
                    chapters_elapsed = max(0, current_chapter_num - secret.created_chapter)
                    unknown_count = len(secret.unknown_to) if secret.unknown_to else 0
                    debt = chapters_elapsed * unknown_count

                    if debt > 30:
                        secret_debt_issues.append(
                            f"秘密「{secret.description}」信息债务过高（{debt} = {chapters_elapsed}章 × {unknown_count}人不知晓），建议安排揭露"
                        )

            # --- Build LLM prompt for transition + secret leakage ---
            secret_lines = []
            for s in secrets_for_llm[:10]:
                known = ", ".join(s.known_by) if s.known_by else "无"
                unknown = ", ".join(s.unknown_to) if s.unknown_to else "无"
                secret_lines.append(
                    f"- 秘密(#{s.id}): {s.description}\n"
                    f"  知晓者: {known} | 不知晓者: {unknown} | "
                    f"保密层级: {s.secrecy_level}"
                )
            secret_summary = "\n".join(secret_lines) if secret_lines else "无未公开秘密"

            # Dynamic section for Group C — appended AFTER shared prefix
            dynamic_section = f"""
【检查 1 — 章节衔接自然性】
前序章节结尾（末尾1000字）：
{prev_end or "（无前序章节，此项直接通过）"}

当前章节开头（前1000字）：
{new_start}

【检查 2 — 秘密债务一致性】
项目秘密列表（未公开）：
{secret_summary}

请逐项检查：
- 章节衔接：两章之间的衔接是否自然流畅？场景/视角切换是否合理？
- 秘密债务：是否有角色说出了TA不该知道的秘密？或做出了对已知秘密的矛盾反应？
"""

            prompt = f"""{ctx["shared_prefix"]}
{dynamic_section}
返回如下 JSON 格式（只返回 JSON，不要其他内容，不要 markdown 代码块）：
{{
  "checks": [
    {{
      "check_name": "chapter_transition",
      "display_name": "章节衔接",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "secret_debt",
      "display_name": "秘密债务",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现（如秘密泄露影响章节衔接）"]或[]
}}
"""
            response = await self._call_llm(prompt, max_tokens=3072)
            result = json.loads(response)
            raw_checks = result.get("checks", []) if isinstance(result, dict) else []

            for raw in raw_checks:
                issues = raw.get("issues", [])
                # Append rule-based secret debt issues to the secret_debt check
                if raw.get("check_name") == "secret_debt" and secret_debt_issues:
                    issues = issues + secret_debt_issues
                group.checks.append(CoherenceCheckItem(
                    check_name=raw.get("check_name", "unknown"),
                    display_name=raw.get("display_name", ""),
                    passed=raw.get("passed", True),
                    score=raw.get("score", 0.9),
                    issues=issues,
                ))

            group.cross_cutting_issues = result.get("cross_cutting_issues", []) if isinstance(result, dict) else []

            if group.checks:
                group.score = round(sum(c.score for c in group.checks) / len(group.checks), 2)
                group.passed = all(c.passed for c in group.checks)

        except Exception as e:
            logger.error(f"Group C (continuity) failed: {e}", exc_info=True)
            group.checks = [
                CoherenceCheckItem(check_name="chapter_transition", display_name="章节衔接", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
                CoherenceCheckItem(check_name="secret_debt", display_name="秘密债务", passed=False, score=0.0, issues=["LLM 调用失败，无法完成检查。请重试或手动审核。"]),
            ]
            group.passed = False
            group.score = 0.0

        return group

    # ===== Helper Methods =====

    async def _get_character_list(self, db: AsyncSession, project_id: int) -> str:
        """Get character list as formatted string."""
        characters = await vault_dao.get_characters(db, project_id)
        if not characters:
            return "暂无角色"
        return ", ".join([c.name for c in characters[:10]])

    async def _call_llm(self, prompt: str, max_tokens: int = 2048) -> str:
        """Call LLM with prompt and return cleaned response text.

        Args:
            prompt: The user prompt to send
            max_tokens: Max output tokens (2048 default, 3072 for grouped checks)

        Returns:
            Cleaned response text string
        """
        messages = [
            {"role": "system", "content": "你是一个专业的小说质量检查助手。"},
            {"role": "user", "content": prompt},
        ]
        
        response = await llm_client.chat(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.3,
            max_tokens=max_tokens,
        )
        
        raw = response["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()


# Singleton instance
coherence_service = CoherenceService()
