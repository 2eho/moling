"""Moling - Generation Service.

Business logic for AI text generation (12-step pipeline).
Implements the complete generation pipeline with LLM calls.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, card_dao, generation_dao, dynamic_layer_dao
from app.errors import NotFoundError, ErrorCode, AppError
from app.utils.security import verify_project_ownership
from app.models import GenerationTask, Chapter, Project, CardPool
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
from app.service.algorithm_service import algorithm_service
from app.service.prompt_service import prompt_service
from app.llm.client import llm_client
from app.llm.context_budget import context_budget
from app.core.service_registry import (
    service_registry,
    RunGenTaskSentinel,
    HealthMonitorServiceSentinel,
    Phase4SchedulerSentinel,
    CoherenceServiceSentinel,
)

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
        project = await verify_project_ownership(db, project_id, user_id)

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
                "word_count": req.word_count,
                "creativity": req.creativity,
            },
            progress_percent=0,
            progress_stage="initializing",
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Celery async dispatch
        try:
            run_generation_task = service_registry.get(RunGenTaskSentinel)
            run_generation_task.delay(task.id)
            logger.info(f"Task {task.id}: Dispatched to Celery worker")
        except RuntimeError:
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
        # Get task via DAO
        task = await generation_dao.get(db, task_id)
        
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Update task status
        task.status = "running"
        task.progress_percent = 5
        task.progress_stage = "weight_allocation"
        await db.commit()

        async with db.begin_nested() as savepoint:
            try:
                # Get project and chapter
                project = await project_dao.get(db, task.project_id)
                chapter = None
                if task.chapter_id:
                    chapter = await chapter_dao.get(db, task.chapter_id)
    
                # Get selected cards
                card_ids = task.input_params.get("card_ids", [])
                weights = task.input_params.get("weights", [])
                cards = await card_dao.get_by_ids_any(db, card_ids)
    
                # ===== Step 1: Weight Allocation =====
                logger.info(f"Task {task_id}: Step 1 - Weight allocation")
                weight_map = await algorithm_service.step1_weight_allocation(cards, weights)
                task.progress_percent = 10
                await db.flush()
    
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
                await db.flush()
    
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
                await db.flush()
    
                # ===== Step 4: Direction Conflict Scoring =====
                logger.info(f"Task {task_id}: Step 4 - Direction conflict scoring")
                direction_conflicts = await algorithm_service.step4_direction_conflict_scoring(cards, weight_map)
                task.progress_percent = 25
                await db.flush()
    
                # ===== Step 5: Weaving Scheme Matching =====
                logger.info(f"Task {task_id}: Step 5 - Weaving scheme matching")
                weaving_scheme = await algorithm_service.step5_weaving_scheme_matching(
                    cards, req_mode=task.input_params.get("mode", "single"),
                    weight_map=weight_map,
                )
                task.progress_percent = 30
                await db.flush()
    
                # ===== Step 6: Outline Template Filling =====
                logger.info(f"Task {task_id}: Step 6 - Outline template filling")
                outline = await algorithm_service.step6_outline_template_filling(
                    project, chapter, cards, weight_map, relevant_vault,
                    word_count=task.input_params.get("word_count", 2000),
                )
                task.progress_percent = 35
                await db.flush()
    
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
                await db.flush()
    
                # ===== Step 8: Brainstorming Divergence (Medium Model) =====
                logger.info(f"Task {task_id}: Step 8 - Brainstorming divergence")
                inspiration = await self._step8_brainstorming_divergence(
                    project, chapter, cards, outline
                )
                task.progress_percent = 50
                await db.flush()

                # ===== Step 8.5: Pre-generation Coherence Validation (§5.1) =====
                # v1 的 validate_pre_generation 已被移除。
                # 预检查功能已整合到 Step 10 的 v2 分组检查中
                #（_check_group_narrative_consistency / _check_group_writing_quality /
                #  _check_group_continuity），在生成后通过 validate_post_generation 执行。
                logger.info(
                    f"Task {task_id}: Step 8.5 - Pre-generation validation "
                    f"(migrated to v2 post-generation grouped checks in Step 10)"
                )

                # ===== Step 9: Body Text Writing (Large Model) =====
                logger.info(f"Task {task_id}: Step 9 - Body text writing")
                generated_content = await self._step9_body_text_writing(
                    project, chapter, outline, inspiration, relevant_vault, weight_map
                )
                task.progress_percent = 70
                await db.flush()
    
                # ===== Step 10: Coherence Validation =====
                logger.info(f"Task {task_id}: Step 10 - Coherence validation")
                coherence_result = await self._step10_coherence_validation(
                    db, project, chapter, generated_content
                )
                task.progress_percent = 80
                await db.flush()
    
                # If coherence check fails, attempt adjustment before falling back
                if not coherence_result["passed"]:
                    logger.warning(f"Task {task_id}: Coherence check failed, adjusting...")
                    generated_content = await self._adjust_content(
                        generated_content, coherence_result["issues"]
                    )
    
                # ===== Step 11: Dynamic Layer Update =====
                logger.info(f"Task {task_id}: Step 11 - Dynamic layer update")
                await self._step11_dynamic_layer_update(
                    db, project.id, chapter.id if chapter else None, generated_content
                )
                task.progress_percent = 90
                await db.flush()
    
                # ===== Step 12: Precedent Summary Update =====
                logger.info(f"Task {task_id}: Step 12 - Precedent summary update")
                await self._step12_precedent_summary_update(
                    db, project.id, chapter.id if chapter else None, generated_content
                )
                task.progress_percent = 95
                await db.flush()
    
                # Update chapter with generated content
                if chapter:
                    chapter.content = generated_content
                    chapter.status = "completed"
                    chapter.word_count = len(generated_content)
    
                # ===== Post-Pipeline: Health Monitor (§5.3) =====
                # 子情节健康监控 R1/R2/R3 — 纯算法，零 LLM 成本
                logger.info(f"Task {task_id}: Running health monitor")
                try:
                    health_monitor_service = service_registry.get(HealthMonitorServiceSentinel)
                    health_result = await health_monitor_service.check_health(
                        db,
                        project_id=project.id,
                        current_chapter=chapter.chapter_number if chapter else 1,
                    )
                    if health_result.get("alerts"):
                        logger.warning(
                            f"Task {task_id}: Health alerts — {len(health_result['alerts'])} issues"
                        )
                except Exception as e:
                    logger.error(f"Task {task_id}: Health monitor failed (non-blocking): {e}")
    
                # ===== Post-Pipeline: Phase 4 Scheduling (§11) =====
                # Phase 4 自动编排 — 异步调度，不阻塞主流程
                logger.info(f"Task {task_id}: Scheduling Phase 4")
                try:
                    phase4_scheduler = service_registry.get(Phase4SchedulerSentinel)
                    import asyncio
                    card_ids_for_phase4 = task.input_params.get("card_ids", [])
                    asyncio.create_task(
                        phase4_scheduler.schedule_phase4(
                            db,
                            project_id=project.id,
                            chapter_id=chapter.id if chapter else 0,
                            chapter_text=generated_content,
                            card_ids=card_ids_for_phase4 if card_ids_for_phase4 else None,
                        )
                    )
                except Exception as e:
                    logger.error(f"Task {task_id}: Phase 4 scheduling failed (non-blocking): {e}")
    
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
                await db.flush()
    
                logger.info(f"Task {task_id}: Generation pipeline completed successfully")
                return task.output_data
    
            except Exception as e:
                await savepoint.rollback()
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
            project, chapter, outline, inspiration, relevant_vault, weight_map
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
            coherence_service = service_registry.get(CoherenceServiceSentinel)
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
            logger.error(f"Coherence validation failed: {e}", exc_info=True)
            return {
                "passed": False,
                "score": 0.0,
                "version": "v2-grouped",
                "issues": [f"连贯性校验服务异常: {str(e)}。请重试或手动审核。"],
                "groups": [],
            }

    async def _step11_dynamic_layer_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 11: Update dynamic layer with new information from generated content."""
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

        # Create or update dynamic layer entry via DAO
        dynamic_layer = await dynamic_layer_dao.create(db, {
            "project_id": project_id,
            "chapter_id": chapter_id,
            "summary": summary,
            "created_at": datetime.now(timezone.utc),
        })
        logger.info(f"Dynamic layer updated for project {project_id}, chapter {chapter_id}")

    async def _step12_precedent_summary_update(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generated_content: str,
    ) -> None:
        """Step 12: Update precedent summary for future chapters."""
        # Get the latest 5 dynamic layers via DAO
        recent_layers = await dynamic_layer_dao.get_recent_by_project(db, project_id, limit=5)

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
        weight_map: Optional[Dict[int, float]] = None,
    ) -> str:
        """Build generation prompt via PromptService + context budget check (§3.5).

        Delegates to prompt_service.build_full_prompt() — the canonical
        implementation of the 4-layer prompt architecture — then runs a
        context-window budget check before returning.

        All field accesses are None-safe.
        """
        # ── Extract Layer 0 / 1 data ──
        chapter_num = outline.get("chapter_number") or (
            chapter.chapter_number if chapter else None
        ) or "?"
        project_name = project.title
        chapter_title = (
            outline.get("chapter_title")
            or (chapter.title if chapter else None)
            or ""
        )

        # Dynamic layer
        dl = relevant_vault.get("dynamic_layer", {}) or {}

        def _dl_get(key: str, fallback_from_outline: str = ""):
            """Safe dynamic layer access: dict or ORM model."""
            val = dl.get(key) if isinstance(dl, dict) else getattr(dl, key, None)
            return val if val else outline.get(key, fallback_from_outline)

        summary = _dl_get("summary") or outline.get("summary") or ""
        pov = _dl_get("anchor_pov") or outline.get("anchor_pov") or "不限"
        location = _dl_get("anchor_location") or outline.get("anchor_location") or "不限"
        time_str = _dl_get("anchor_time") or outline.get("anchor_time") or "当前"

        must_hold = _dl_get("must_hold") or outline.get("must_hold") or []
        must_not = _dl_get("must_not") or outline.get("must_not") or []

        raw_hooks = _dl_get("unresolved_hooks") or outline.get("unresolved_hooks") or []
        unresolved_hooks: list[str] = []
        for h in raw_hooks:
            if isinstance(h, dict):
                unresolved_hooks.append(h.get("description", str(h)))
            else:
                unresolved_hooks.append(str(h))

        # ── Extract Layer 2 data (vault, normalize to dicts) ──
        characters: list[dict] = []
        vault_chars = relevant_vault.get("characters", []) or []
        for c in vault_chars:
            if isinstance(c, dict):
                characters.append({
                    "name": c.get("name", ""),
                    "role": c.get("role", ""),
                    "description": c.get("description", "") or c.get("personality", "") or "",
                    "traits": c.get("traits", []),
                    "emotion": c.get("current_state", "") or c.get("emotion", ""),
                })
            else:
                characters.append({
                    "name": getattr(c, "name", "?"),
                    "description": getattr(c, "description", ""),
                })

        plot_promises: list[dict] = []
        vault_promises = relevant_vault.get("plot_promises", []) or []
        for p in vault_promises:
            if isinstance(p, dict):
                plot_promises.append({
                    "description": p.get("description", ""),
                    "type": p.get("type", ""),
                    "status": p.get("status", ""),
                    "urgency": p.get("urgency", 0),
                })
            else:
                plot_promises.append({
                    "description": getattr(p, "description", ""),
                    "type": "",
                    "status": getattr(p, "status", ""),
                    "urgency": getattr(p, "urgency", 0),
                })

        timeline: list[dict] = []
        vault_timeline = relevant_vault.get("timeline", []) or []
        for e in vault_timeline[-3:]:
            if isinstance(e, dict):
                timeline.append({
                    "event": e.get("event", ""),
                    "chapter_number": e.get("chapter_number", ""),
                    "description": e.get("description", ""),
                    "impact": e.get("impact", ""),
                })
            else:
                timeline.append({
                    "event": getattr(e, "event", ""),
                    "chapter_number": getattr(e, "chapter_number", ""),
                    "description": getattr(e, "description", ""),
                    "impact": "",
                })

        world_rules: list[dict] = []
        vault_world = relevant_vault.get("world", []) or []
        for w in vault_world:
            if isinstance(w, dict):
                world_rules.append({
                    "term": w.get("name", ""),
                    "description": w.get("constraint", "") or w.get("description", "") or "",
                })
            else:
                world_rules.append({
                    "term": getattr(w, "name", ""),
                    "description": getattr(w, "constraint", "") or getattr(w, "description", ""),
                })

        # ── Extract Layer 3 data ──
        cards: list[dict] = []
        selected_dirs = outline.get("selected_directions", []) or []
        for d in selected_dirs:
            cards.append({
                "name": d.get("card_name", d.get("name", "")),
                "direction_type": d.get("direction_type", ""),
                "direction_text": d.get("direction_text", d.get("description", "")),
            })

        weaving_scheme = outline.get("weaving_scheme") or None
        if isinstance(weaving_scheme, dict):
            weaving_scheme = weaving_scheme
        elif weaving_scheme:
            weaving_scheme = {"description": str(weaving_scheme)}

        # ── Weight map conversion (int key → str key for PromptService) ──
        prompt_weight_map: Dict[str, float] = {}
        if weight_map:
            for d in selected_dirs:
                card_name = d.get("card_name", d.get("name", ""))
                card_id = d.get("card_id", d.get("id", 0))
                if card_id in weight_map:
                    prompt_weight_map[card_name] = weight_map[card_id]
                elif card_name:
                    prompt_weight_map[card_name] = d.get("weight", 1.0)

        # ── Style fingerprint (Layer 4) ──
        style_fingerprint = outline.get("style_fingerprint") or None

        # ── Delegate to PromptService (canonical 4-layer assembly) ──
        prompt = prompt_service.build_full_prompt(
            chapter_number=chapter_num,
            project_name=project_name,
            chapter_title=chapter_title,
            pov_character=pov,
            location=location,
            time_period=time_str,
            summary=summary,
            must_hold=must_hold,
            must_not=must_not,
            unresolved_hooks=unresolved_hooks,
            characters=characters,
            plot_promises=plot_promises,
            timeline=timeline,
            world_rules=world_rules,
            cards=cards,
            weight_map=prompt_weight_map,
            weaving_scheme=weaving_scheme,
            style_fingerprint=style_fingerprint,
        )

        # Append inspiration (the old code's section 3c) — PromptService
        # doesn't have a dedicated field for this; inject before writing reqs.
        if inspiration:
            prompt = prompt.replace(
                "请直接开始写作，不要添加任何解释或说明。",
                f"【创作灵感】\n{inspiration}\n\n请直接开始写作，不要添加任何解释或说明。",
            )

        # Append writing requirements — PromptService doesn't have a dedicated
        # Layer 5 for this; inject after Layer 3.
        gen_req = outline.get("generation_requirements", {}) or {}
        word_count = gen_req.get("word_count", "2500-3500")
        style = gen_req.get("style", project.style or "") or ""
        style_line = f" / 风格: {style}" if style else ""
        writing_req = (
            f"【写作要求】\n"
            f"字数 {word_count}{style_line}\n"
            f"结尾留钩子 / 至少推进一个未收束悬念\n"
        )
        prompt = prompt.replace(
            "请直接开始写作，不要添加任何解释或说明。",
            f"{writing_req}\n请直接开始写作，不要添加任何解释或说明。",
        )

        # ── Context window budget check (§3.5 safety) ──
        model = getattr(settings, "LLM_MODEL", None) or "deepseek-v4-pro"
        budget = context_budget.check_and_truncate(
            prompt,
            model=model,
            max_output_tokens=4096,
        )
        final_prompt = budget.truncated_prompt

        logger.info(
            "Generation prompt assembled: %d chars → ~%d tokens (budget: %s, remaining: %+d, "
            "truncations: %s)",
            len(prompt),
            budget.estimated_input_tokens,
            "OK" if budget.within_budget else "OVER",
            budget.remaining_tokens,
            [t.get("layer", "?") for t in budget.truncations],
        )

        return final_prompt

    async def _adjust_content(
        self,
        content: str,
        issues: List[str],
    ) -> str:
        """Adjust generated content based on coherence issues by re-prompting the LLM."""
        if not issues:
            return content

        issues_text = "\n".join(f"- {issue}" for issue in issues)
        prompt = f"""请对以下小说内容进行针对性修改，解决以下连贯性问题：

        问题清单：
        {issues_text}

        原文内容：
        {content}

        请保持原内容的整体结构和风格，只修改有问题的部分。
        """

        # Check context budget — truncate content if too long
        model = getattr(settings, "LLM_MODEL", None) or "deepseek-v4-pro"
        budget = context_budget.check(
            prompt, model=model, max_output_tokens=4096
        )
        if not budget.within_budget:
            overflow_tokens = abs(budget.remaining_tokens)
            overflow_chars = overflow_tokens * 2  # conservative Chinese char estimate
            # Keep at least 2000 chars of content
            keep_chars = max(2000, len(content) - overflow_chars - len(issues_text))
            truncated_content = content[:keep_chars]
            logger.warning(
                "Adjust content prompt too long (%d tokens), truncating content from %d → %d chars",
                budget.estimated_input_tokens, len(content), keep_chars,
            )
            prompt = f"""请对以下小说内容进行针对性修改，解决以下连贯性问题：

        问题清单：
        {issues_text}

        原文内容（截取）：
        {truncated_content}
        ...（后续内容请参考原章节，仅修改上述问题涉及的部分）

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
        task = await generation_dao.get(db, task_id)

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise AppError(
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
        task = await generation_dao.get(db, task_id)

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise AppError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to cancel this task",
            )

        # Only pending/running tasks can be cancelled
        if task.status not in ("pending", "running"):
            raise AppError(
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
    ) -> dict:
        """Get generation task history for a user (via DAO)."""
        skip = (page - 1) * page_size
        filters = {"user_id": user_id}

        total = await generation_dao.count(db, filters=filters)
        tasks = await generation_dao.get_multi(
            db, filters=filters, skip=skip, limit=page_size,
            order_by="created_at", descending=True,
        )

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
