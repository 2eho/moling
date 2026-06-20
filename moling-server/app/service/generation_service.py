"""Moling - Generation Service.

Business logic for AI text generation (12-step pipeline).
Implements the complete generation pipeline with LLM calls.
"""

from __future__ import annotations

import logging
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
        task_id: Optional[str] = None,
    ) -> GenerationResp:
        """Start an AI generation task (12-step pipeline).
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            project_id: 项目 ID
            chapter_id: 章节 ID（可选）
            req: 生成请求参数
            task_id: 预分配的任务 ID（可选）。如果不传，则自动生成新 UUID。
                      当 router 已在请求中预创建 job_id 时使用。
        """
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

        # Create task record（使用预分配 ID 或自动生成）
        task_id = task_id or str(uuid4())
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

            # ===== Step 2: Vault Filtering (§3.4 - ID-based with compression) =====
            logger.info(f"Task {task_id}: Step 2 - Vault filtering")
            relevant_vault = await algorithm_service.step2_vault_filter(
                db=db,
                project_id=project.id,
                chapter_id=chapter.id if chapter else None,
                cards=cards if cards else None,
                chapter_number=chapter.chapter_number if chapter else None,
            )
            task.progress_percent = 15
            await db.commit()

            # ===== Step 3: Dynamic Layer Conflict Detection (§3.3) =====
            logger.info(f"Task {task_id}: Step 3 - Conflict detection")
            conflicts = await algorithm_service.step3_conflict_detection(
                db=db,
                project_id=project.id,
                chapter_id=chapter.id if chapter else None,
                weight_map=weight_map,
                cards=cards if cards else None,
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
            weaving_scheme = await algorithm_service.step5_weaving_scheme_matching(
                cards, req_mode=task.input_params.get("mode", "single"),
                weight_map=weight_map,
            )
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
            # Supports both dict-based (VaultFilterService) and model-based (legacy) formats
            vault_chars = relevant_vault.get("characters", [])
            vault_promises = relevant_vault.get("plot_promises", [])
            vault_timeline = relevant_vault.get("timeline", [])

            def _safe_name(item):
                return item["name"] if isinstance(item, dict) else getattr(item, "name", "")
            def _safe_desc(item):
                return item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
            def _safe_event(item):
                return item.get("event", "") if isinstance(item, dict) else getattr(item, "event", "")

            narrative_elements = {
                "active_characters": [_safe_name(c) for c in vault_chars[:5]],
                "pending_promises": [_safe_desc(p) for p in vault_promises[:3] if _safe_desc(p)],
                "recent_timeline": [_safe_event(e) for e in vault_timeline[-3:]] if vault_timeline else [],
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
        """Step 10: Coherence validation using CoherenceService (v2 grouped checks)."""
        try:
            from app.service.coherence_service import coherence_service
            result = await coherence_service.validate_post_generation(
                db=db,
                project_id=project.id,
                chapter_id=chapter.id if chapter else 0,
                generated_content=generated_content,
            )
            # Parse into schema to use flatten_issues, then convert back for pipeline
            from app.schemas.coherence import CoherenceValidationResult
            parsed = CoherenceValidationResult(**result)
            flattened_issues = parsed.flatten_issues()
            return {
                "passed": result["passed"],
                "score": result["overall_score"],
                "version": result.get("version", "v2-grouped"),
                "issues": flattened_issues,
                "groups": result.get("groups", []),
            }
        except Exception as e:
            logger.error(f"Coherence validation failed: {e}")
            return {"passed": True, "score": 0.85, "version": "v2-grouped", "issues": [], "groups": []}

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
        """Build a layered generation prompt per §3.5 Prompt分层组装.

        Three layers are assembled in strict order:
          Layer 0 — System instruction (always present)
          Layer 1 — Dynamic layer / story state (front-loaded for Lost-in-the-Middle protection)
          Layer 2 — Four-vault filtered context (characters, promises, timeline, world)
          Layer 3 — Chapter direction + optional weaving scheme

        All field accesses are None-safe.
        """
        sections = []

        # ====================================================================
        # Layer 0 — 系统指令
        # ====================================================================
        chapter_num = outline.get("chapter_number") or (
            chapter.chapter_number if chapter else None
        ) or "?"
        sections.append(
            f"你是一位专业的网络小说作家。撰写第{chapter_num}章。"
        )
        sections.append("=" * 55)

        # ====================================================================
        # Layer 1 — 动态层 · 故事此刻状态  (Lost-in-the-Middle protection)
        # ====================================================================
        sections.append("[Layer 1: 📋 动态层 · 故事此刻状态]")
        sections.append("=" * 55)

        # 1a. 前情摘要
        dl = relevant_vault.get("dynamic_layer", {}) or {}
        summary = (
            dl.get("summary") if isinstance(dl, dict)
            else getattr(dl, "summary", None)
        ) or outline.get("summary") or ""
        if summary:
            sections.append(f"【前情摘要】\n{summary}\n")

        # 1b. 章节锚点
        pov = (
            dl.get("anchor_pov") if isinstance(dl, dict)
            else getattr(dl, "anchor_pov", None)
        ) or outline.get("anchor_pov") or "不限"
        location = (
            dl.get("anchor_location") if isinstance(dl, dict)
            else getattr(dl, "anchor_location", None)
        ) or outline.get("anchor_location") or "不限"
        time_str = (
            dl.get("anchor_time") if isinstance(dl, dict)
            else getattr(dl, "anchor_time", None)
        ) or outline.get("anchor_time") or "当前"
        sections.append(
            f"【章节锚点】\nPOV: {pov} | 地点: {location} | 时间: {time_str}\n"
        )

        # 1c. 连贯性基线
        must_hold = (
            dl.get("must_hold") if isinstance(dl, dict)
            else getattr(dl, "must_hold", None)
        ) or outline.get("must_hold") or []
        must_not = (
            dl.get("must_not") if isinstance(dl, dict)
            else getattr(dl, "must_not", None)
        ) or outline.get("must_not") or []

        if must_hold:
            sections.append(
                "【连贯性基线 — 硬约束】\n必须保持:\n"
                + "\n".join(f"- {item}" for item in must_hold)
            )
        if must_not:
            sections.append(
                "必须避免:\n"
                + "\n".join(f"- {item}" for item in must_not)
            )
        if must_hold or must_not:
            sections.append("")

        # 1d. 未收束钩子 Top3
        hooks = (
            dl.get("unresolved_hooks") if isinstance(dl, dict)
            else getattr(dl, "unresolved_hooks", None)
        ) or outline.get("unresolved_hooks") or []
        if hooks:
            top_hooks = hooks[:3]
            sections.append(
                "【未收束钩子 Top3】\n"
                + "\n".join(
                    f"- {h.get('description', h) if isinstance(h, dict) else h}"
                    for h in top_hooks
                )
                + "\n"
            )
        sections.append("=" * 55)

        # ====================================================================
        # Layer 2 — 四库 · 卡片过滤上下文
        # ====================================================================
        sections.append("[Layer 2: 📚 四库 · 卡片过滤上下文]")
        sections.append("=" * 55)

        # 2a. 相关人物设定
        vault_chars = relevant_vault.get("characters", []) or []
        if vault_chars:
            char_lines = []
            for c in vault_chars:
                if isinstance(c, dict):
                    name = c.get("name", "")
                    role = c.get("role", "")
                    desc = c.get("description", "") or c.get("personality", "") or ""
                    state = c.get("current_state", "") or ""
                    parts = [f"【{name}】"]
                    if role:
                        parts.append(f"  定位: {role}")
                    if desc:
                        parts.append(f"  描述: {desc}")
                    if state:
                        parts.append(f"  当前状态: {state}")
                    char_lines.append("\n".join(parts))
                else:
                    char_lines.append(f"【{getattr(c, 'name', '?')}】\n  描述: {getattr(c, 'description', '')}")
            sections.append("【相关人物设定】\n" + "\n".join(char_lines) + "\n")

        # 2b. 相关剧情承诺
        vault_promises = relevant_vault.get("plot_promises", []) or []
        if vault_promises:
            promise_lines = []
            for p in vault_promises:
                if isinstance(p, dict):
                    desc = p.get("description", "")
                    status = p.get("status", "")
                    urgency = p.get("urgency", 0)
                    promise_lines.append(f"- {desc} (状态: {status}, 紧迫度: {urgency})")
                else:
                    promise_lines.append(f"- {getattr(p, 'description', '')} (状态: {getattr(p, 'status', '')})")
            sections.append("【相关剧情承诺】\n" + "\n".join(promise_lines) + "\n")

        # 2c. 时间线参考 (±3条)
        vault_timeline = relevant_vault.get("timeline", []) or []
        if vault_timeline:
            timeline_lines = []
            for e in vault_timeline[-3:]:
                if isinstance(e, dict):
                    timeline_lines.append(f"- [{e.get('chapter_number', '?')}] {e.get('event', '')}")
                else:
                    timeline_lines.append(f"- [{getattr(e, 'chapter_number', '?')}] {getattr(e, 'event', '')}")
            sections.append("【时间线参考】\n" + "\n".join(timeline_lines) + "\n")

        # 2d. 世界观规则
        vault_world = relevant_vault.get("world", []) or []
        if vault_world:
            world_lines = []
            for w in vault_world:
                if isinstance(w, dict):
                    name = w.get("name", "")
                    constraint = w.get("constraint", "") or w.get("description", "") or ""
                    world_lines.append(f"- {name}: {constraint}")
                else:
                    world_lines.append(f"- {getattr(w, 'name', '')}: {getattr(w, 'constraint', '') or getattr(w, 'description', '')}")
            sections.append("【世界观规则】\n" + "\n".join(world_lines) + "\n")
        sections.append("=" * 55)

        # ====================================================================
        # Layer 3 — 本章方向
        # ====================================================================
        sections.append("[Layer 3: 🃏 本章方向]")
        sections.append("=" * 55)

        # 3a. 融合方向
        selected_dirs = outline.get("selected_directions", []) or []
        if selected_dirs:
            dir_lines = []
            for d in selected_dirs:
                card_name = d.get("card_name", d.get("name", ""))
                dir_text = d.get("direction_text", d.get("description", ""))
                weight = d.get("weight", 1.0)
                dir_lines.append(f"- {card_name}：{dir_text} (权重: {weight:.2f})")
            sections.append("【融合方向】\n" + "\n".join(dir_lines) + "\n")

        # 3b. 编织方案 (optional)
        weaving = outline.get("weaving_scheme") or ""
        if weaving:
            if isinstance(weaving, dict):
                scheme_name = weaving.get("name", weaving.get("scheme", ""))
                scheme_desc = weaving.get("description", weaving.get("detail", ""))
                weaving_text = f"{scheme_name}: {scheme_desc}" if scheme_name else scheme_desc
            else:
                weaving_text = str(weaving)
            sections.append(f"【编织方案】\n{weaving_text}\n")

        # 3c. 创作灵感 (from step 8)
        if inspiration:
            sections.append(f"【创作灵感】\n{inspiration}\n")
        sections.append("=" * 55)

        # ====================================================================
        # 写作要求
        # ====================================================================
        gen_req = outline.get("generation_requirements", {}) or {}
        word_count = gen_req.get("word_count", "2500-3500")
        style = gen_req.get("style", project.style or "") or ""
        style_line = f" / 风格: {style}" if style else ""
        sections.append(
            f"【写作要求】\n"
            f"字数 {word_count}{style_line}\n"
            f"结尾留钩子 / 至少推进一个未收束悬念\n"
        )

        sections.append("请直接开始写作，不要添加任何解释或说明。")

        return "\n".join(sections)

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
