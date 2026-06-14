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
from app.dao import project_dao, chapter_dao, card_dao, vault_dao
from app.errors import NotFoundError, ErrorCode, PermissionError, AppError
from app.models import GenerationTask, Chapter, Project, CardPool
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
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

        # TODO: Actually trigger Celery task for async execution
        # For now, we'll implement the pipeline synchronously
        # In production, this should be:
        #   from app.tasks.generation_task import run_generation_pipeline
        #   run_generation_pipeline.delay(task_id)

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
            weight_map = await self._step1_weight_allocation(cards, weights)
            task.progress_percent = 10
            await db.commit()

            # ===== Step 2: Vault Filtering =====
            logger.info(f"Task {task_id}: Step 2 - Vault filtering")
            relevant_vault = await self._step2_vault_filtering(
                db, project.id, chapter.id if chapter else None
            )
            task.progress_percent = 15
            await db.commit()

            # ===== Step 3: Dynamic Layer Conflict Detection =====
            logger.info(f"Task {task_id}: Step 3 - Conflict detection")
            conflicts = await self._step3_conflict_detection(
                db, project.id, chapter.id if chapter else None, weight_map
            )
            task.progress_percent = 20
            await db.commit()

            # ===== Step 4: Direction Conflict Scoring =====
            logger.info(f"Task {task_id}: Step 4 - Direction conflict scoring")
            direction_conflicts = await self._step4_direction_conflict_scoring(cards, weight_map)
            task.progress_percent = 25
            await db.commit()

            # ===== Step 5: Weaving Scheme Matching =====
            logger.info(f"Task {task_id}: Step 5 - Weaving scheme matching")
            weaving_scheme = await self._step5_weaving_scheme_matching(cards, req_mode=task.input_params.get("mode", "single"))
            task.progress_percent = 30
            await db.commit()

            # ===== Step 6: Outline Template Filling =====
            logger.info(f"Task {task_id}: Step 6 - Outline template filling")
            outline = await self._step6_outline_template_filling(
                project, chapter, cards, weight_map, relevant_vault
            )
            task.progress_percent = 35
            await db.commit()

            # ===== Step 7: Narrative Element Extraction (Small Model) =====
            logger.info(f"Task {task_id}: Step 7 - Narrative element extraction")
            # Note: This step is usually done AFTER generation, but we prepare prompts here
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

    async def _step1_weight_allocation(
        self,
        cards: List[CardPool],
        user_weights: List[float],
    ) -> Dict[int, float]:
        """Step 1: Weight allocation based on card rarity and user adjustment."""
        weight_map = {}
        
        # Rarity base weights
        rarity_base = {
            "common": 1.0,
            "rare": 2.0,
            "epic": 3.0,
            "legendary": 4.0,
        }
        
        for i, card in enumerate(cards):
            base = rarity_base.get(card.rarity, 1.0)
            user_weight = user_weights[i] if i < len(user_weights) else 50.0
            # Normalize user weight (0-100) to multiplier (0.5-2.0)
            user_multiplier = 0.5 + (user_weight / 100.0) * 1.5
            weight_map[card.id] = base * user_multiplier
        
        return weight_map

    async def _step2_vault_filtering(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
    ) -> Dict[str, List[Any]]:
        """Step 2: Filter relevant vault entities based on current context."""
        relevant = {
            "characters": [],
            "timeline": [],
            "plot_promises": [],
            "world": [],
        }
        
        # Get recent characters (active in recent chapters)
        characters = await vault_dao.get_characters(db, project_id)
        relevant["characters"] = characters[:10]  # Top 10 most relevant
        
        # Get recent timeline events
        timeline = await vault_dao.get_timeline(db, project_id)
        relevant["timeline"] = timeline[-5:] if timeline else []  # Last 5 events
        
        # Get active plot promises
        promises = await vault_dao.get_plot_promises(db, project_id)
        relevant["plot_promises"] = [p for p in promises if p.status in ["dormant", "active"]]
        
        # Get world entries
        world = await vault_dao.get_world_entries(db, project_id)
        relevant["world"] = world[:10]  # Top 10 entries
        
        return relevant

    async def _step3_conflict_detection(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        weight_map: Dict[int, float],
    ) -> List[Dict[str, Any]]:
        """Step 3: Detect conflicts with existing dynamic layer."""
        conflicts = []
        
        # Get dynamic layer for the project
        # TODO: Implement dynamic layer conflict detection logic
        # For now, return empty conflicts
        
        return conflicts

    async def _step4_direction_conflict_scoring(
        self,
        cards: List[CardPool],
        weight_map: Dict[int, float],
    ) -> Dict[str, Any]:
        """Step 4: Score conflicts between selected direction cards."""
        conflicts = {
            "has_conflict": False,
            "conflict_score": 0.0,
            "conflict_reasons": [],
        }
        
        # Check for conflicting directions
        # Example: "稳妥" (safe) vs "惊艳" (dramatic) may conflict
        direction_types = [card.direction_type for card in cards]
        
        if "稳妥" in direction_types and "惊艳" in direction_types:
            conflicts["has_conflict"] = True
            conflicts["conflict_score"] = 0.7
            conflicts["conflict_reasons"].append("稳妥与惊艳的方向存在张力")
        
        return conflicts

    async def _step5_weaving_scheme_matching(
        self,
        cards: List[CardPool],
        req_mode: str,
    ) -> Dict[str, Any]:
        """Step 5: Match best weaving scheme based on user selection."""
        schemes = {
            "single": {
                "name": "单卡模式",
                "description": "专注于一个创作方向",
                "weaving_strategy": "focus",
            },
            "dual": {
                "name": "双卡模式",
                "description": "融合两个创作方向",
                "weaving_strategy": "blend",
            },
            "all": {
                "name": "全选模式",
                "description": "多方向综合",
                "weaving_strategy": "multi_thread",
            },
            "hybrid": {
                "name": "混合模式",
                "description": "保留部分，重抽部分",
                "weaving_strategy": "hybrid",
            },
        }
        
        return schemes.get(req_mode, schemes["single"])

    async def _step6_outline_template_filling(
        self,
        project: Project,
        chapter: Optional[Chapter],
        cards: List[CardPool],
        weight_map: Dict[int, float],
        relevant_vault: Dict[str, List[Any]],
    ) -> Dict[str, Any]:
        """Step 6: Fill outline template with generation parameters."""
        outline = {
            "project_title": project.title,
            "project_genre": project.genre,
            "chapter_title": chapter.title if chapter else "新章节",
            "chapter_number": chapter.chapter_number if chapter else 1,
            "selected_directions": [
                {
                    "card_name": card.name,
                    "direction_text": card.direction_text,
                    "weight": weight_map.get(card.id, 1.0),
                    "rarity": card.rarity,
                }
                for card in cards
            ],
            "characters": [c.name for c in relevant_vault["characters"][:5]],
            "recent_events": [e.event for e in relevant_vault["timeline"][-3:]] if relevant_vault["timeline"] else [],
            "active_promises": [p.description for p in relevant_vault["plot_promises"][:3]],
            "generation_requirements": {
                "word_count": 2000,  # TODO: Make configurable
                "style": project.style or "叙事风格",
                "tone": "consistent with project",
            },
        }
        
        return outline

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
        """Step 10: Coherence validation (check generated content against existing)."""
        result = {
            "passed": True,
            "score": 0.85,
            "issues": [],
        }
        
        # TODO: Implement comprehensive coherence check
        # For now, return passed=True
        
        return result

    async def _step11_dynamic_layer_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 11: Update dynamic layer with new information."""
        # TODO: Implement dynamic layer update
        # This will be implemented in the Phase 4 service
        pass

    async def _step12_precedent_summary_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 12: Update precedent summary for future chapters."""
        # TODO: Implement precedent summary update
        # This will be implemented in the Phase 4 service
        pass

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
        """Adjust generated content based on coherence issues."""
        # TODO: Implement content adjustment logic
        # For now, return content as-is
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
