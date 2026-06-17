"""Moling - Coherence Validation Service.

Implements pre-generation and post-generation coherence checks.
Validates: character consistency, timeline continuity, plot promise status,
world rule consistency, writing style, narrative pacing, chapter transition,
and secret consistency / debt (\"秘密债务\").
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, vault_dao
from app.errors import NotFoundError, ErrorCode, AppError
from app.models import Project, Chapter, Secret, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()


class CoherenceService:
    """Service for coherence validation (pre and post generation)."""

    async def validate_pre_generation(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Pre-generation coherence validation (7-step check).
        
        Args:
            db: Database session
            project_id: Project ID
            chapter_id: Current chapter ID (if any)
            generation_params: Generation parameters (cards, weights, mode)
            
        Returns:
            Validation result with detailed checks
        """
        result = {
            "passed": True,
            "overall_score": 1.0,
            "checks": {},
        }
        
        try:
            # Get project
            project = await project_dao.get(db, project_id)
            if project is None:
                raise NotFoundError(
                    error_code=ErrorCode.PROJECT_NOT_FOUND,
                    detail="Project not found",
                )
            
            # Get previous chapter (if any)
            previous_chapter = None
            if chapter_id:
                stmt = (
                    select(Chapter)
                    .where(
                        Chapter.project_id == project_id,
                        Chapter.chapter_number < (
                            select(Chapter.chapter_number)
                            .where(Chapter.id == chapter_id)
                            .scalar_subquery()
                        ),
                    )
                    .order_by(Chapter.chapter_number.desc())
                    .limit(1)
                )
                result = await db.execute(stmt)
                previous_chapter = result.scalar_one_or_none()
            
            # ===== Check 1: Character Behavior Consistency =====
            logger.info(f"Pre-validation: Check 1 - Character consistency for project {project_id}")
            check1 = await self._check_character_consistency(
                db, project, generation_params
            )
            result["checks"]["character_consistency"] = check1
            
            # ===== Check 2: Timeline Continuity =====
            logger.info(f"Pre-validation: Check 2 - Timeline continuity for project {project_id}")
            check2 = await self._check_timeline_continuity(
                db, project, chapter_id
            )
            result["checks"]["timeline_continuity"] = check2
            
            # ===== Check 3: Plot Promise Status Consistency =====
            logger.info(f"Pre-validation: Check 3 - Plot promise status for project {project_id}")
            check3 = await self._check_plot_promise_status(
                db, project
            )
            result["checks"]["plot_promise_status"] = check3
            
            # ===== Check 4: World Rule Consistency =====
            logger.info(f"Pre-validation: Check 4 - World rule consistency for project {project_id}")
            check4 = await self._check_world_rule_consistency(
                db, project, generation_params
            )
            result["checks"]["world_rule_consistency"] = check4
            
            # ===== Check 5: Writing Style Consistency =====
            logger.info(f"Pre-validation: Check 5 - Writing style consistency for project {project_id}")
            check5 = await self._check_writing_style_consistency(
                db, project, previous_chapter
            )
            result["checks"]["writing_style_consistency"] = check5
            
            # ===== Check 6: Narrative Pacing Rationality =====
            logger.info(f"Pre-validation: Check 6 - Narrative pacing for project {project_id}")
            check6 = await self._check_narrative_pacing(
                db, project, chapter_id
            )
            result["checks"]["narrative_pacing"] = check6
            
            # ===== Check 7: Chapter Transition Naturalness =====
            logger.info(f"Pre-validation: Check 7 - Chapter transition for project {project_id}")
            check7 = await self._check_chapter_transition(
                db, project, previous_chapter, generation_params
            )
            result["checks"]["chapter_transition"] = check7
            
            # Calculate overall result
            all_passed = all(c["passed"] for c in result["checks"].values())
            total_score = sum(c["score"] for c in result["checks"].values())
            avg_score = total_score / len(result["checks"]) if result["checks"] else 1.0
            
            result["passed"] = all_passed
            result["overall_score"] = avg_score
            
            logger.info(f"Pre-validation completed for project {project_id}: passed={all_passed}, score={avg_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Pre-validation failed: {e}", exc_info=True)
            result["passed"] = False
            result["overall_score"] = 0.0
            result["error"] = str(e)
            return result

    async def validate_post_generation(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Post-generation coherence validation (7-step check).
        
        Args:
            db: Database session
            project_id: Project ID
            chapter_id: Generated chapter ID
            generated_content: Generated chapter content
            
        Returns:
            Validation result with detailed checks
        """
        result = {
            "passed": True,
            "overall_score": 1.0,
            "checks": {},
        }
        
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
                stmt = (
                    select(Chapter)
                    .where(
                        Chapter.project_id == project_id,
                        Chapter.chapter_number == chapter.chapter_number - 1,
                    )
                )
                result = await db.execute(stmt)
                previous_chapter = result.scalar_one_or_none()
            
            # ===== Check 1: Character Behavior Consistency =====
            logger.info(f"Post-validation: Check 1 - Character consistency for chapter {chapter_id}")
            check1 = await self._check_character_consistency_post(
                db, project, chapter, generated_content
            )
            result["checks"]["character_consistency"] = check1
            
            # ===== Check 2: Timeline Continuity =====
            logger.info(f"Post-validation: Check 2 - Timeline continuity for chapter {chapter_id}")
            check2 = await self._check_timeline_continuity_post(
                db, project, chapter, generated_content
            )
            result["checks"]["timeline_continuity"] = check2
            
            # ===== Check 3: Plot Promise Status Consistency =====
            logger.info(f"Post-validation: Check 3 - Plot promise status for chapter {chapter_id}")
            check3 = await self._check_plot_promise_status_post(
                db, project, chapter, generated_content
            )
            result["checks"]["plot_promise_status"] = check3
            
            # ===== Check 4: World Rule Consistency =====
            logger.info(f"Post-validation: Check 4 - World rule consistency for chapter {chapter_id}")
            check4 = await self._check_world_rule_consistency_post(
                db, project, generated_content
            )
            result["checks"]["world_rule_consistency"] = check4
            
            # ===== Check 5: Writing Style Consistency =====
            logger.info(f"Post-validation: Check 5 - Writing style consistency for chapter {chapter_id}")
            check5 = await self._check_writing_style_consistency_post(
                db, project, previous_chapter, generated_content
            )
            result["checks"]["writing_style_consistency"] = check5
            
            # ===== Check 6: Narrative Pacing Rationality =====
            logger.info(f"Post-validation: Check 6 - Narrative pacing for chapter {chapter_id}")
            check6 = await self._check_narrative_pacing_post(
                db, project, chapter, generated_content
            )
            result["checks"]["narrative_pacing"] = check6
            
            # ===== Check 7: Chapter Transition Naturalness =====
            logger.info(f"Post-validation: Check 7 - Chapter transition for chapter {chapter_id}")
            check7 = await self._check_chapter_transition_post(
                db, project, previous_chapter, generated_content
            )
            result["checks"]["chapter_transition"] = check7
            
            # ===== Check 8: 秘密债务检查 (§5.2 第7项) =====
            logger.info(f"Post-validation: Check 8 - Secret debt for chapter {chapter_id}")
            check8 = await self._check_secret_debt(db, project, chapter)
            result["checks"]["secret_debt"] = check8
            
            # Calculate overall result
            all_passed = all(c["passed"] for c in result["checks"].values())
            total_score = sum(c["score"] for c in result["checks"].values())
            avg_score = total_score / len(result["checks"]) if result["checks"] else 1.0
            
            result["passed"] = all_passed
            result["overall_score"] = avg_score
            
            logger.info(f"Post-validation completed for chapter {chapter_id}: passed={all_passed}, score={avg_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Post-validation failed: {e}", exc_info=True)
            result["passed"] = False
            result["overall_score"] = 0.0
            result["error"] = str(e)
            return result

    # ===== Individual Check Implementations =====

    async def _check_character_consistency(
        self,
        db: AsyncSession,
        project: Project,
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check 1: Character behavior consistency (pre-generation)."""
        character_str = await self._get_character_list(db, project.id)
        cards_info = generation_params.get("cards", "无")
        mode = generation_params.get("mode", "续写")

        prompt = f"""请检查以下项目的角色设定一致性。

项目：{project.title}
角色列表：{character_str}
当前生成模式：{mode}
使用的卡牌信息：{cards_info}

请检查：
1. 角色当前状态是否符合其性格设定和角色定位？
2. 选用的卡牌与角色设定是否匹配？
3. 角色之间是否存在不合理的互动设定？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Character consistency pre-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_character_consistency_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 1: Character behavior consistency (post-generation)."""
        # Call LLM to analyze character consistency
        prompt = f"""请检查以下章节内容中的角色行为一致性。

项目：{project.title}
角色列表：{await self._get_character_list(db, project.id)}

章节内容：
{generated_content}

请检查：
1. 角色行为是否符合其性格设定？
2. 角色对话是否符合其身份和背景？
3. 角色之间的关系是否保持一致？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Character consistency check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_timeline_continuity(
        self,
        db: AsyncSession,
        project: Project,
        chapter_id: Optional[int],
    ) -> Dict[str, Any]:
        """Check 2: Timeline continuity (pre-generation)."""
        vault_events = await vault_dao.get_timeline(db, project.id)
        if not vault_events:
            return {"passed": True, "score": 1.0, "details": "vault尚无时间线事件"}

        timeline_summary = "\n".join([
            f"- [{e.importance or 'normal'}] 第{e.chapter_number}章: {e.event} — {e.description[:80] if e.description else e.event}"
            for e in vault_events[-10:]  # last 10 events
        ])

        prompt = f"""请检查以下项目的时间线连续性。

项目：{project.title}

时间线事件（最近 10 条）：
{timeline_summary}

请检查时间线是否：
1. 各事件之间的时间顺序合理
2. 没有明显的时间线跳跃或矛盾
3. 事件之间的因果关系清晰

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Timeline continuity check failed: {e}")
            return {"passed": True, "score": 0.8, "details": f"检查失败: {str(e)}"}

    async def _check_timeline_continuity_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 2: Timeline continuity (post-generation)."""
        vault_events = await vault_dao.get_timeline(db, project.id)
        timeline_summary = "\n".join([
            f"- 第{e.chapter_number}章: {e.event}"
            for e in vault_events[-10:]
        ]) if vault_events else "暂无"

        prompt = f"""请检查以下章节内容中的时间线连续性。

项目：{project.title}
当前章节：第{chapter.chapter_number}章《{chapter.title}》

现有时间线事件：
{timeline_summary}

章节内容（前2000字）：
{generated_content[:2000]}

请检查：
1. 章节内容是否与现有时间线事件冲突？
2. 章节中提到的事件是否符合时间顺序？
3. 是否有未记录但在内容中发生的重要事件？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Timeline continuity post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_plot_promise_status(
        self,
        db: AsyncSession,
        project: Project,
    ) -> Dict[str, Any]:
        """Check 3: Plot promise status consistency (pre-generation)."""
        promises = await vault_dao.get_plot_promises(db, project.id)
        active_promises = [p for p in promises if p.status in ["dormant", "active"]]

        if not promises:
            return {"passed": True, "score": 1.0, "details": "vault尚无伏笔设定"}

        promise_summary = "\n".join([
            f"- [{p.type}] {p.description[:100] or '无描述'} (状态: {p.status}, 紧迫度: {p.urgency})"
            for p in promises
        ])
        active_count = len(active_promises)

        prompt = f"""请检查以下项目的伏笔（情节承诺）状态。

项目：{project.title}
活跃伏笔数量：{active_count} 个

所有伏笔列表：
{promise_summary}

请检查：
1. 活跃伏笔的数量是否合理（不应过多未处理的伏笔）？
2. 长期未处理的伏笔是否需要关注？
3. 不同伏笔之间是否存在冲突？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []) + [f"当前活跃伏笔: {active_count}个"],
            }
        except Exception as e:
            logger.error(f"Plot promise status check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_plot_promise_status_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 3: Plot promise status consistency (post-generation)."""
        promises = await vault_dao.get_plot_promises(db, project.id)
        active_promises = [p for p in promises if p.status in ["dormant", "active"]]

        if not active_promises:
            return {"passed": True, "score": 1.0, "details": "无活跃伏笔需要检查"}

        promise_summary = "\n".join([
            f"- [{p.type}] {p.description[:100] or '无描述'} (状态: {p.status}, 紧迫度: {p.urgency})"
            for p in active_promises[:8]
        ])

        prompt = f"""请检查以下章节内容中的伏笔处理情况。

项目：{project.title}
当前章节：第{chapter.chapter_number}章《{chapter.title}》

活跃伏笔列表：
{promise_summary}

章节内容（前3000字）：
{generated_content[:3000]}

请检查：
1. 章节内容是否涉及对活跃伏笔的推进或兑现？
2. 如果有伏笔被推进，处理方式是否自然合理？
3. 是否有新的伏笔被埋下？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Plot promise post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_world_rule_consistency(
        self,
        db: AsyncSession,
        project: Project,
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check 4: World rule consistency (pre-generation)."""
        world_entries = await vault_dao.get_world_entries(db, project.id)
        if not world_entries:
            return {"passed": True, "score": 1.0, "details": "vault尚无世界观设定"}

        world_summary = "\n".join([
            f"- [{e.category}] {e.name}: {e.description[:150] or '无描述'}"
            + (f" (约束: {e.constraint[:100]})" if e.constraint else "")
            for e in world_entries
        ])

        cards_info = generation_params.get("cards", "无")

        prompt = f"""请检查以下项目的世界观规则一致性。

项目：{project.title}

世界观设定条目：
{world_summary}

本次生成使用的卡牌/设定：{cards_info}

请检查：
1. 卡牌/设定是否与世界观规则冲突？
2. 世界观各条目之间的规则是否存在矛盾？
3. 是否有违反已建立世界观设定的风险？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"World rule consistency check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_world_rule_consistency_post(
        self,
        db: AsyncSession,
        project: Project,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 4: World rule consistency (post-generation)."""
        world_entries = await vault_dao.get_world_entries(db, project.id)
        if not world_entries:
            return {"passed": True, "score": 1.0, "details": "vault尚无世界观设定"}

        world_summary = "\n".join([
            f"- [{e.category}] {e.name}: {e.description[:150] or '无描述'}"
            + (f" (约束: {e.constraint[:100]})" if e.constraint else "")
            for e in world_entries
        ])

        prompt = f"""请检查以下章节内容中是否有违反世界观设定的地方。

项目：{project.title}

世界观设定条目：
{world_summary}

章节内容：
{generated_content}

请检查：
1. 章节内容中是否有与世界观设定矛盾的描述？
2. 是否违反了世界观中的约束或规则？
3. 世界观元素的使用方式是否合理？

返回 JSON 格式：
{{"consistent": true/false, "violations": ["违规1", "违规2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("violations", []),
            }
        except Exception as e:
            logger.error(f"World rule consistency post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_writing_style_consistency(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
    ) -> Dict[str, Any]:
        """Check 5: Writing style consistency (pre-generation)."""
        if not previous_chapter or not previous_chapter.content:
            return {"passed": True, "score": 1.0, "details": "暂无前序章节内容可对比"}

        prev_content = previous_chapter.content[:2000]

        prompt = f"""请检查以下项目的文风一致性。

项目：{project.title}
前序章节标题：{previous_chapter.title}

前序章节内容（前2000字）：
{prev_content}

请分析前序章节的写作风格特征（如：句式特点、用词风格、叙述视角、对话风格等），
并评估在续写时保持风格一致需要注意的方面。

返回 JSON 格式：
{{"consistent": true/false, "issues": ["注意要点1", "注意要点2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.85),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Writing style consistency check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_writing_style_consistency_post(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 5: Writing style consistency (post-generation)."""
        if not previous_chapter or not previous_chapter.content:
            return {"passed": True, "score": 1.0, "details": "暂无前序章节内容可对比"}

        prev_content = previous_chapter.content[:2000]

        prompt = f"""请比较以下两段内容（前序章节 vs 新生成章节）的写作风格一致性。

项目：{project.title}
前序章节标题：{previous_chapter.title}

前序章节内容（前2000字）：
{prev_content}

新生成章节内容：
{generated_content[:2000]}

请检查：
1. 两段内容的文风是否一致（句式、用词、叙述视角）？
2. 是否有风格上的突变或不协调？
3. 对话风格和描写方式是否连贯？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["差异1", "差异2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.85),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Writing style consistency post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_narrative_pacing(
        self,
        db: AsyncSession,
        project: Project,
        chapter_id: Optional[int],
    ) -> Dict[str, Any]:
        """Check 6: Narrative pacing rationality (pre-generation)."""
        chapters = await chapter_dao.get_by_project(db, project.id)
        if not chapters or len(chapters) < 2:
            return {"passed": True, "score": 1.0, "details": "章节数量不足，无法评估叙事节奏"}

        pacing_summary = "\n".join([
            f"- 第{c.chapter_number}章《{c.title}》: 长度约{len(c.content or '')}字"
            for c in chapters[-5:]  # last 5 chapters
        ])

        prompt = f"""请检查以下项目的叙事节奏合理性。

项目：{project.title}

最近章节概览：
{pacing_summary}

请检查：
1. 各章节的长度分布是否合理？
2. 叙事节奏是否存在过快或过慢的问题？
3. 情节推进的速度是否平稳？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.8),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Narrative pacing check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_narrative_pacing_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 6: Narrative pacing rationality (post-generation)."""
        content_len = len(generated_content)

        prompt = f"""请检查以下章节内容的叙事节奏合理性。

项目：{project.title}
当前章节：第{chapter.chapter_number}章《{chapter.title}》
章节长度：{content_len} 字

章节内容（前3000字）：
{generated_content[:3000]}

请检查：
1. 叙事节奏是否合理（情节推进速度适中）？
2. 是否有过度拖沓或过于仓促的部分？
3. 情节点之间的过渡是否自然？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.8),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Narrative pacing post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_chapter_transition(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check 7: Chapter transition naturalness (pre-generation)."""
        if not previous_chapter or not previous_chapter.content:
            return {"passed": True, "score": 1.0, "details": "暂无前序章节，无需衔接检查"}

        prev_content = previous_chapter.content[-1000:]
        mode = generation_params.get("mode", "续写")

        prompt = f"""请检查以下项目的章节衔接自然性。

项目：{project.title}
前序章节标题：{previous_chapter.title}
生成模式：{mode}

前序章节结尾内容（末尾1000字）：
{prev_content}

请检查：
1. 前序章节结尾是否为续写提供了合理的衔接点？
2. 是否存在明显的断裂感或突兀的结尾？
3. 续写时需要注意哪些衔接要点？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["要点1", "要点2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Chapter transition check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    async def _check_chapter_transition_post(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 7: Chapter transition naturalness (post-generation)."""
        if not previous_chapter or not previous_chapter.content:
            return {"passed": True, "score": 1.0, "details": "无前序章节，无需衔接检查"}

        prev_end = previous_chapter.content[-1000:]
        new_start = generated_content[:1000]

        prompt = f"""请检查以下章节之间的衔接自然性。

项目：{project.title}
前序章节：第{previous_chapter.chapter_number}章《{previous_chapter.title}》

前序章节结尾（末尾1000字）：
{prev_end}

当前章节开头（前1000字）：
{new_start}

请检查：
1. 两章之间的衔接是否自然流畅？
2. 是否有必要的情节或逻辑过渡？
3. 场景或视角切换是否合理？

返回 JSON 格式：
{{"consistent": true/false, "issues": ["问题1", "问题2"], "score": 0.0-1.0}}
"""
        try:
            response = await self._call_llm(prompt)
            result = json.loads(response)
            return {
                "passed": result.get("consistent", True),
                "score": result.get("score", 0.9),
                "details": result.get("issues", []),
            }
        except Exception as e:
            logger.error(f"Chapter transition post-check failed: {e}")
            return {
                "passed": True,
                "score": 0.8,
                "details": f"检查失败: {str(e)}",
            }

    # ===== Check 8: 秘密债务检查 (§5.2 第7项 + §2.8.2) =====

    async def _check_secret_debt(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
    ) -> Dict[str, Any]:
        """秘密债务检查（§2.8.2 + §5.2 第7项）。

        检查项：
        1. 角色是否说出了TA不知道的秘密 → 冲突标记
        2. 角色是否对已知秘密做出了矛盾反应 → 冲突标记
        3. 秘密债务 > 30 → 建议安排揭露（非阻塞提示）

        Args:
            db: Database session
            project: Current project
            chapter: Current chapter (contains chapter_number)

        Returns:
            Dict with passed/score/details
        """
        try:
            # ---- 1. 从 DB 加载项目所有 Secret ----
            stmt = select(Secret).where(Secret.project_id == project.id)
            db_result = await db.execute(stmt)
            secrets: list[Secret] = list(db_result.scalars().all())

            if not secrets:
                logger.info("Secret debt check: no secrets found for project %s", project.id)
                return {
                    "passed": True,
                    "score": 1.0,
                    "details": [],
                }

            current_chapter = chapter.chapter_number
            details: list[Dict[str, Any]] = []

            # ---- 2. 对每个秘密计算债务 ----
            for secret in secrets:
                # 已公开的秘密不参与计算
                if secret.secrecy_level in ("revealed", "open"):
                    continue

                if secret.created_chapter is None:
                    continue

                chapters_elapsed = current_chapter - secret.created_chapter
                if chapters_elapsed < 0:
                    chapters_elapsed = 0

                unknown_count = len(secret.unknown_to) if secret.unknown_to else 0
                debt = chapters_elapsed * unknown_count

                if debt > 30:
                    detail = {
                        "secret": secret.description,
                        "secret_id": secret.id,
                        "debt": debt,
                        "chapters_elapsed": chapters_elapsed,
                        "unknown_count": unknown_count,
                        "known_by": secret.known_by,
                        "unknown_to": secret.unknown_to,
                        "suggested_fix": f"秘密「{secret.description}」的信息债务过高（{debt}），建议安排揭露",
                    }
                    details.append(detail)

            # ---- 3. LLM 检测：角色秘密泄露 / 矛盾反应 ----
            secrets_for_llm = [s for s in secrets if s.secrecy_level not in ("revealed", "open")]
            if secrets_for_llm and current_chapter > 0:
                try:
                    llm_findings = await self._check_secret_leakage_via_llm(
                        project, chapter, secrets_for_llm
                    )
                    details.extend(llm_findings)
                except Exception as e:
                    logger.warning("Secret leakage LLM check failed, skipping: %s", e)

            # ---- 4. 计算得分 ----
            has_conflicts = any(d.get("type") == "conflict" for d in details)
            high_debts = [d for d in details if d.get("debt", 0) > 30]

            if not details:
                result = {
                    "passed": True,
                    "score": 1.0,
                    "details": [],
                }
            elif has_conflicts:
                # 有冲突标记 → 不通过
                result = {
                    "passed": False,
                    "score": max(0.0, 1.0 - 0.15 * len(high_debts) - 0.3),
                    "details": details,
                }
            elif high_debts:
                # 仅有高债务建议 → 仍可通过，但扣分
                score = max(0.5, 1.0 - 0.1 * len(high_debts))
                result = {
                    "passed": True,
                    "score": round(score, 2),
                    "details": details,
                }
            else:
                result = {
                    "passed": True,
                    "score": 1.0,
                    "details": details or [],
                }

            logger.info(
                "Secret debt check completed: passed=%s, score=%.2f, details=%d",
                result["passed"], result["score"], len(details),
            )
            return result

        except Exception as e:
            logger.error("Secret debt check failed: %s", e, exc_info=True)
            return {
                "passed": True,
                "score": 0.8,
                "details": [{"error": f"秘密债务检查失败: {str(e)}"}],
            }

    async def _check_secret_leakage_via_llm(
        self,
        project: Project,
        chapter: Chapter,
        secrets: list[Secret],
    ) -> list[Dict[str, Any]]:
        """通过 LLM 检测生成的章节内容中的秘密泄露和矛盾反应。

        Returns:
            list of detail dicts with type="conflict" or type="suggestion"
        """
        # 为 LLM 构建秘密摘要
        secret_lines = []
        for s in secrets[:10]:  # 最多传 10 个秘密给 LLM
            known = ", ".join(s.known_by) if s.known_by else "无"
            unknown = ", ".join(s.unknown_to) if s.unknown_to else "无"
            secret_lines.append(
                f"- 秘密(#{s.id}): {s.description}\n"
                f"  知晓者: {known} | 不知晓者: {unknown} | "
                f"保密层级: {s.secrecy_level}"
            )
        secret_summary = "\n".join(secret_lines)

        prompt = f"""请分析以下小说章节内容中的秘密一致性问题。

项目：{project.title}
当前章节：第{chapter.chapter_number}章《{chapter.title}》

项目秘密列表：
{secret_summary}

章节内容：
{chapter.content or "（无内容）"}

请检查以下两点：
1. 是否有角色说出了TA不该知道的秘密？（即 unknown_to 中的角色提到了或明显暗示了某个秘密）
2. 是否有角色对已知的秘密做出了矛盾或不一致的反应？（即 known_by 中的角色以不符合设定/常识的方式对待这个秘密）

返回 JSON 格式（数组，无发现则返回空数组）：
[
  {{
    "type": "conflict",
    "secret_id": 1,
    "character": "角色名",
    "issue": "问题描述",
    "severity": "high" 或 "medium"
  }}
]

只返回 JSON 数组，不返回其他内容。不要添加 markdown 代码块标记。
"""
        try:
            response = await self._call_llm(prompt)
            raw = response.strip()
            # 去除可能的 markdown 代码块
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("```", 1)[0]
            findings = json.loads(raw)
            if not isinstance(findings, list):
                logger.warning("Secret leakage LLM returned non-list: %s", findings)
                return []

            details = []
            for f in findings:
                if not isinstance(f, dict):
                    continue
                detail = {
                    "type": f.get("type", "conflict"),
                    "secret": f"秘密#{f.get('secret_id', '?')} — 角色 {f.get('character', '?')}",
                    "issue": f.get("issue", ""),
                    "severity": f.get("severity", "medium"),
                    "suggested_fix": f"角色「{f.get('character', '?')}」存在秘密一致性问题",
                }
                details.append(detail)

            return details

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Secret leakage LLM parse failed: %s", e)
            return []

    # ===== Helper Methods =====

    async def _get_character_list(self, db: AsyncSession, project_id: int) -> str:
        """Get character list as formatted string."""
        characters = await vault_dao.get_characters(db, project_id)
        if not characters:
            return "暂无角色"
        return ", ".join([c.name for c in characters[:10]])

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt and return response text."""
        messages = [
            {"role": "system", "content": "你是一个专业的小说质量检查助手。"},
            {"role": "user", "content": prompt},
        ]
        
        response = await llm_client.chat(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.3,
            max_tokens=2048,
        )
        
        return response["choices"][0]["message"]["content"]


# Singleton instance
coherence_service = CoherenceService()
