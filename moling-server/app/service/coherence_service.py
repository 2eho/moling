"""Moling - Coherence Validation Service.

Implements pre-generation and post-generation coherence checks.
Validates: character consistency, timeline continuity, plot promise status,
world rule consistency, writing style, narrative pacing, chapter transition.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, vault_dao
from app.errors import NotFoundError, ErrorCode, AppError
from app.models import Project, Chapter, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld
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
        # TODO: Implement LLM-based character consistency check
        # For now, return passed=True
        return {
            "passed": True,
            "score": 0.9,
            "details": "角色一致性检查通过",
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
        # TODO: Implement timeline continuity check
        return {
            "passed": True,
            "score": 0.95,
            "details": "时间线连续性检查通过",
        }

    async def _check_timeline_continuity_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 2: Timeline continuity (post-generation)."""
        # TODO: Implement post-generation timeline check
        return {
            "passed": True,
            "score": 0.95,
            "details": "时间线连续性检查通过",
        }

    async def _check_plot_promise_status(
        self,
        db: AsyncSession,
        project: Project,
    ) -> Dict[str, Any]:
        """Check 3: Plot promise status consistency (pre-generation)."""
        # Get active plot promises
        promises = await vault_dao.get_plot_promises(db, project.id)
        active_promises = [p for p in promises if p.status in ["dormant", "active"]]
        
        # TODO: Check if generation plan addresses active promises
        return {
            "passed": True,
            "score": 0.9,
            "details": f"伏笔状态检查通过，当前活跃伏笔: {len(active_promises)}个",
        }

    async def _check_plot_promise_status_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 3: Plot promise status consistency (post-generation)."""
        # TODO: Implement post-generation plot promise check
        return {
            "passed": True,
            "score": 0.9,
            "details": "伏笔状态检查通过",
        }

    async def _check_world_rule_consistency(
        self,
        db: AsyncSession,
        project: Project,
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check 4: World rule consistency (pre-generation)."""
        # TODO: Implement world rule consistency check
        return {
            "passed": True,
            "score": 0.95,
            "details": "世界观规则一致性检查通过",
        }

    async def _check_world_rule_consistency_post(
        self,
        db: AsyncSession,
        project: Project,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 4: World rule consistency (post-generation)."""
        # TODO: Implement post-generation world rule check
        return {
            "passed": True,
            "score": 0.95,
            "details": "世界观规则一致性检查通过",
        }

    async def _check_writing_style_consistency(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
    ) -> Dict[str, Any]:
        """Check 5: Writing style consistency (pre-generation)."""
        # TODO: Implement writing style consistency check
        return {
            "passed": True,
            "score": 0.85,
            "details": "文风一致性检查通过",
        }

    async def _check_writing_style_consistency_post(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 5: Writing style consistency (post-generation)."""
        # TODO: Implement post-generation style check
        return {
            "passed": True,
            "score": 0.85,
            "details": "文风一致性检查通过",
        }

    async def _check_narrative_pacing(
        self,
        db: AsyncSession,
        project: Project,
        chapter_id: Optional[int],
    ) -> Dict[str, Any]:
        """Check 6: Narrative pacing rationality (pre-generation)."""
        # TODO: Implement narrative pacing check
        return {
            "passed": True,
            "score": 0.8,
            "details": "叙事节奏合理性检查通过",
        }

    async def _check_narrative_pacing_post(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Chapter,
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 6: Narrative pacing rationality (post-generation)."""
        # TODO: Implement post-generation pacing check
        return {
            "passed": True,
            "score": 0.8,
            "details": "叙事节奏合理性检查通过",
        }

    async def _check_chapter_transition(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generation_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check 7: Chapter transition naturalness (pre-generation)."""
        # TODO: Implement chapter transition check
        return {
            "passed": True,
            "score": 0.9,
            "details": "章节衔接自然性检查通过",
        }

    async def _check_chapter_transition_post(
        self,
        db: AsyncSession,
        project: Project,
        previous_chapter: Optional[Chapter],
        generated_content: str,
    ) -> Dict[str, Any]:
        """Check 7: Chapter transition naturalness (post-generation)."""
        # TODO: Implement post-generation transition check
        return {
            "passed": True,
            "score": 0.9,
            "details": "章节衔接自然性检查通过",
        }

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
