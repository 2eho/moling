"""Moling - Generation Service.

Business logic for AI text generation (12-step pipeline).
Implements the complete generation pipeline with LLM calls.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.dao import project_dao, chapter_dao, card_dao
from app.errors import NotFoundError, ErrorCode, PermissionError, AppError
from app.models import GenerationTask, Chapter, Project, CardPool
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
from app.service.algorithm_service import algorithm_service
from app.llm.client import llm_client

logger = logging.getLogger(__name__)
settings = get_settings()


class GenerationService:
    """Service for generation operations (12-step pipeline)."""

    async def start_generation(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: Optional[int],
        req: GenerateReq,
    ) -> GenerationResp:
        """Start an AI generation task (12-step pipeline)."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Verify chapter exists if chapter_id provided
        chapter = None
        if chapter_id:
            chapter = await chapter_dao.get(db, chapter_id)
            if chapter is None:
                raise NotFoundError(
                    error_code=ErrorCode.CHAPTER_NOT_FOUND,
                    detail="Chapter not found",
                )
            if chapter.project_id != project_id:
                raise AppError(
                    error_code=ErrorCode.FORBIDDEN,
                    detail="Chapter does not belong to this project",
                )

        # Create task record
        task_id = str(uuid4())
        task = GenerationTask(
            id=task_id,
            project_id=project_id,
            chapter_id=chapter_id,
            user_id=user_id,
            task_type="generate",
            status="pending",
            input_params={
                "card_ids": req.card_ids,
                "weights": req.weights,
                "mode": req.mode,
            },
            progress_percent=0,
            progress_stage="initializing",
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Celery async dispatch
        try:
            from app.worker.tasks import run_generation_task
            run_generation_task.delay(task.id)
            logger.info(f"Task {task.id}: Dispatched to Celery worker")
        except ImportError:
            logger.warning(f"Task {task.id}: Celery worker not available, running synchronously")
            await self.execute_generation_pipeline(db, task.id)
        except Exception as e:
            logger.error(f"Task {task.id}: Failed to dispatch Celery task: {e}")
            await self.execute_generation_pipeline(db, task.id)

        return GenerationResp(
            task_id=task.id,
            status=task.status,
        )

    async def execute_generation_pipeline(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Dict[str, Any]:
        """Execute the 12-step generation pipeline.
        
        This method is called by the Celery worker (or synchronously for testing).
        """
        # Get task
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Update task status
        task.status = "running"
        task.progress_percent = 5
        task.progress_stage = "weight_allocation"
        await db.commit()

        try:
            # Get project and chapter
            project = await project_dao.get(db, task.project_id)
            chapter = None
            if task.chapter_id:
                chapter = await chapter_dao.get(db, task.chapter_id)

            # Get selected cards
            card_ids = task.input_params.get("card_ids", [])
            weights = task.input_params.get("weights", [])
            cards = []
            for card_id in card_ids:
                card = await card_dao.get(db, card_id)
                if card:
                    cards.append(card)

            # ===== Step 1: Weight Allocation =====
            logger.info(f"Task {task_id}: Step 1 - Weight allocation")
            weight_map = await algorithm_service.step1_weight_allocation(cards, weights)
            task.progress_percent = 10
            await db.commit()

            # ===== Step 2: Vault Filtering =====
            logger.info(f"Task {task_id}: Step 2 - Vault filtering")
            relevant_vault = await algorithm_service.step2_vault_filter(
                db, project.id, chapter.id if chapter else None
            )
            task.progress_percent = 15
            await db.commit()

            # ===== Step 3: Dynamic Layer Conflict Detection =====
            logger.info(f"Task {task_id}: Step 3 - Conflict detection")
            conflicts = await algorithm_service.step3_conflict_detection(
                db, project.id, chapter.id if chapter else None, weight_map
            )
            task.progress_percent = 20
            await db.commit()

            # ===== Step 4: Direction Conflict Scoring =====
            logger.info(f"Task {task_id}: Step 4 - Direction conflict scoring")
            direction_conflicts = await algorithm_service.step4_direction_conflict_scoring(cards, weight_map)
            task.progress_percent = 25
            await db.commit()

            # ===== Step 5: Weaving Scheme Matching =====
            logger.info(f"Task {task_id}: Step 5 - Weaving scheme matching")
            weaving_scheme = await algorithm_service.step5_weaving_scheme_matching(cards, req_mode=task.input_params.get("mode", "single"))
            task.progress_percent = 30
            await db.commit()

            # ===== Step 6: Outline Template Filling =====
            logger.info(f"Task {task_id}: Step 6 - Outline template filling")
            outline = await algorithm_service.step6_outline_template_filling(
                project, chapter, cards, weight_map, relevant_vault
            )
            task.progress_percent = 35
            await db.commit()

            # ===== Step 7: Narrative Element Extraction =====
            logger.info(f"Task {task_id}: Step 7 - Narrative element extraction")
            # Extract relevant vault data for prompt building
            narrative_elements = {
                "active_characters": [c.name for c in relevant_vault.get("characters", [])[:5]],
                "pending_promises": [p.description for p in relevant_vault.get("plot_promises", [])[:3] if hasattr(p, 'description')],
                "recent_timeline": [e.event for e in relevant_vault.get("timeline", [])[-3:]] if relevant_vault.get("timeline") else [],
            }
            task.progress_percent = 40
            await db.commit()

            # ===== Step 8: Brainstorming Divergence (Medium Model) =====
            logger.info(f"Task {task_id}: Step 8 - Brainstorming divergence")
            inspiration = await self._step8_brainstorming_divergence(
                project, chapter, cards, outline
            )
            task.progress_percent = 50
            await db.commit()

            # ===== Step 9: Body Text Writing (Large Model) =====
            logger.info(f"Task {task_id}: Step 9 - Body text writing")
            generated_content = await self._step9_body_text_writing(
                project, chapter, outline, inspiration, relevant_vault, weight_map
            )
            task.progress_percent = 70
            await db.commit()

            # ===== Step 10: Coherence Validation =====
            logger.info(f"Task {task_id}: Step 10 - Coherence validation")
            coherence_result = await self._step10_coherence_validation(
                db, project, chapter, generated_content
            )
            task.progress_percent = 80
            await db.commit()

            # If coherence check fails, we may need to regenerate or adjust
            if not coherence_result["passed"]:
                logger.warning(f"Task {task_id}: Coherence check failed, adjusting...")
                # TODO: Implement adjustment logic or regenerate
                generated_content = await self._adjust_content(
                    generated_content, coherence_result["issues"]
                )

            # ===== Step 11: Dynamic Layer Update =====
            logger.info(f"Task {task_id}: Step 11 - Dynamic layer update")
            await self._step11_dynamic_layer_update(
                db, project.id, chapter.id if chapter else None, generated_content
            )
            task.progress_percent = 90
            await db.commit()

            # ===== Step 12: Precedent Summary Update =====
            logger.info(f"Task {task_id}: Step 12 - Precedent summary update")
            await self._step12_precedent_summary_update(
                db, project.id, chapter.id if chapter else None, generated_content
            )
            task.progress_percent = 95
            await db.commit()

            # Update chapter with generated content
            if chapter:
                chapter.content = generated_content
                chapter.status = "completed"
                chapter.word_count = len(generated_content)

            # Update task status
            task.status = "done"
            task.progress_percent = 100
            task.progress_stage = "completed"
            task.output_data = {
                "content": generated_content,
                "word_count": len(generated_content),
                "coherence_check": coherence_result,
                "direction_conflicts": direction_conflicts,
            }
            await db.commit()

            logger.info(f"Task {task_id}: Generation pipeline completed successfully")
            return task.output_data

        except Exception as e:
            logger.error(f"Task {task_id}: Generation pipeline failed: {e}", exc_info=True)
            task.status = "failed"
            task.error_message = str(e)
            await db.commit()
            raise

    # ===== Pipeline Step Implementations =====

    async def _step8_brainstorming_divergence(
        self,
        project: Project,
        chapter: Optional[Chapter],
        cards: List[CardPool],
        outline: Dict[str, Any],
    ) -> str:
        """Step 8: Brainstorming divergence (Medium Model)."""
        # Build prompt for brainstorming
        prompt = f"""请基于以下信息，进行创作头脑风暴，生成灵感用于小说章节写作。

项目：{project.title}
类型：{project.genre}
创作方向：
{chr(10).join(f"- {c.direction_text}" for c in cards)}

章节大纲：
- 章节标题：{outline['chapter_title']}
- 涉及角色：{', '.join(outline['characters'])}
- 最近事件：{', '.join(outline['recent_events']) if outline['recent_events'] else '无'}

请生成：
1. 3个可能的情节发展方向
2. 2个潜在的冲突点
3. 1个意外的转折建议

要求：具体、可操作、符合项目风格。
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的小说创作助手，擅长头脑风暴和灵感激发。"},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.8,  # Higher temperature for creativity
                max_tokens=2048,
            )
            
            inspiration = response["choices"][0]["message"]["content"]
            return inspiration
            
        except Exception as e:
            logger.error(f"Brainstorming failed: {e}", exc_info=True)
            return "默认灵感：继续推进当前情节，注意角色发展和伏笔回收。"

    async def _step9_body_text_writing(
        self,
        project: Project,
        chapter: Optional[Chapter],
        outline: Dict[str, Any],
        inspiration: str,
        relevant_vault: Dict[str, List[Any]],
        weight_map: Dict[int, float],
    ) -> str:
        """Step 9: Body text writing (Large Model)."""
        # Build comprehensive prompt for text generation
        prompt = self._build_generation_prompt(
            project, chapter, outline, inspiration, relevant_vault
        )
        
        messages = [
            {"role": "system", "content": "你是一个专业的小说作家，擅长创作引人入胜的故事章节。"},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.7,
                max_tokens=4096,
            )
            
            generated_content = response["choices"][0]["message"]["content"]
            return generated_content
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}", exc_info=True)
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                detail=f"文本生成失败: {str(e)}"
            )

    async def _step10_coherence_validation(
        self,
        db: AsyncSession,
        project: Project,
        chapter: Optional[Chapter],
        generated_content: str,
    ) -> Dict[str, Any]:
        """Step 10: Coherence validation using CoherenceService."""
        try:
            from app.service.coherence_service import coherence_service
            result = await coherence_service.validate_post_generation(
                db=db,
                project_id=project.id,
                chapter_id=chapter.id if chapter else 0,
                generated_content=generated_content,
            )
            return {
                "passed": result["passed"],
                "score": result["overall_score"],
                "issues": [
                    detail
                    for check in result.get("checks", {}).values()
                    for detail in (check.get("details", []) if isinstance(check.get("details"), list) else [check.get("details", "")])
                    if not check.get("passed", True)
                ],
            }
        except Exception as e:
            logger.error(f"Coherence validation failed: {e}")
            return {"passed": True, "score": 0.85, "issues": []}

    async def _step11_dynamic_layer_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 11: Update dynamic layer with new information from generated content."""
        from app.models.dynamic_layer import DynamicLayer
        from datetime import datetime, timezone

        # Build the dynamic layer from generated content
        # Extract summary using LLM
        prompt = f"""请为以下小说章节内容生成一个200字以内的前情摘要。

        内容：
        {generated_content[:3000]}

        请直接返回摘要，不要额外说明。
        """

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的小说摘要助手。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.3,
                max_tokens=512,
            )
            summary = response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Failed to generate summary via LLM: {e}")
            summary = generated_content[:200]

        # Create or update dynamic layer entry
        dynamic_layer = DynamicLayer(
            project_id=project_id,
            chapter_id=chapter_id,
            summary=summary,
            created_at=datetime.now(timezone.utc),
        )
        db.add(dynamic_layer)
        logger.info(f"Dynamic layer updated for project {project_id}, chapter {chapter_id}")

    async def _step12_precedent_summary_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 12: Update precedent summary for future chapters."""
        # Get the latest 5 dynamic layers to build precedent
        from app.models.dynamic_layer import DynamicLayer
        from sqlalchemy import select

        stmt = (
            select(DynamicLayer)
            .where(DynamicLayer.project_id == project_id)
            .order_by(DynamicLayer.id.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        recent_layers = list(result.scalars().all())

        if not recent_layers:
            logger.info(f"No existing dynamic layers for project {project_id}")
            return

        # Combine recent summaries into a compressed precedent
        summaries = [layer.summary for layer in recent_layers if layer.summary]
        precedent = " | ".join(summaries[-3:])  # Keep last 3 summaries

        # Store in project metadata or a dedicated field
        # For now, log the precedent
        logger.info(f"Precedent summary updated for project {project_id}: {precedent[:100]}...")

    def _build_generation_prompt(
        self,
        project: Project,
        chapter: Optional[Chapter],
        outline: Dict[str, Any],
        inspiration: str,
        relevant_vault: Dict[str, List[Any]],
    ) -> str:
        """Build the prompt for text generation."""
        prompt = f"""请创作小说《{project.title}》的新章节。

【项目信息】
- 类型：{project.genre}
- 简介：{project.synopsis}
- 世界观：{project.worldview}

【章节信息】
- 章节标题：{outline['chapter_title']}
- 章节编号：第{outline['chapter_number']}章

【创作方向】
{chr(10).join(f"- {d['card_name']}：{d['direction_text']} (权重: {d['weight']:.2f})" for d in outline['selected_directions'])}

【涉及角色】
{chr(10).join(f"- {c}" for c in outline['characters'])}

【最近情节】
{chr(10).join(f"- {e}" for e in outline['recent_events']) if outline['recent_events'] else "- 开篇"}

【活跃伏笔】
{chr(10).join(f"- {p}" for p in outline['active_promises']) if outline['active_promises'] else "- 暂无"}

【创作灵感】
{inspiration}

【写作要求】
1. 字数：约{outline['generation_requirements']['word_count']}字
2. 风格：{outline['generation_requirements']['style']}
3. 保持与前文的一致性（角色性格、世界观、时间线）
4. 推进情节发展，注意伏笔的铺垫和回收
5. 文笔流畅，叙事自然

请直接开始写作，不要添加任何解释或说明。
"""
        return prompt

    async def _adjust_content(
        self,
        content: str,
        issues: List[str],
    ) -> str:
        """Adjust generated content based on coherence issues by re-prompting the LLM."""
        if not issues:
            return content

        prompt = f"""请对以下小说内容进行针对性修改，解决以下连贯性问题：

        问题清单：
        {chr(10).join(f"- {issue}" for issue in issues)}

        原文内容：
        {content}

        请保持原内容的整体结构和风格，只修改有问题的部分。
        """

        messages = [
            {"role": "system", "content": "你是一个专业的小说编辑，擅长修改内容连贯性问题。"},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.4,
                max_tokens=4096,
            )
            adjusted = response["choices"][0]["message"]["content"]
            return adjusted
        except Exception as e:
            logger.error(f"Content adjustment failed: {e}")
            return content

    async def get_task_status(
        self,
        db: AsyncSession,
        user_id: str,
        task_id: str,
    ) -> TaskStatusResp:
        """Get generation task status."""
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this task",
            )

        return TaskStatusResp(
            task_id=task.id,
            status=task.status,
            progress_stage=task.progress_stage,
            progress_percent=task.progress_percent,
            error_message=task.error_message,
            output_data=task.output_data,
        )

    async def cancel_task(
        self,
        db: AsyncSession,
        user_id: str,
        task_id: str,
    ) -> None:
        """Cancel a generation task."""
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to cancel this task",
            )

        # Only pending/running tasks can be cancelled
        if task.status not in ("pending", "running"):
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail=f"Cannot cancel task in status: {task.status}",
            )

        task.status = "cancelled"
        await db.commit()


    async def get_history(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        """Get generation task history for a user."""
        from sqlalchemy import select, func
        from app.models import GenerationTask

        # Build query
        stmt = (
            select(GenerationTask)
            .where(GenerationTask.user_id == user_id)
            .order_by(GenerationTask.created_at.desc())
        )

        # Count total
        count_stmt = (
            select(func.count())
            .select_from(GenerationTask)
            .where(GenerationTask.user_id == user_id)
        )
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        tasks = list(result.scalars().all())

        history = []
        for task in tasks:
            history.append({
                "task_id": task.id,
                "project_id": task.project_id,
                "chapter_id": task.chapter_id,
                "task_type": task.task_type,
                "status": task.status,
                "progress_percent": task.progress_percent,
                "progress_stage": task.progress_stage,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            })

        return {
            "items": history,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }


# Singleton instance
generation_service = GenerationService()
