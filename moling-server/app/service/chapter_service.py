"""Moling - Chapter Service.

Business logic for chapter CRUD operations.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import chapter_dao, project_dao
from app.errors import NotFoundError, ErrorCode
from app.utils.security import verify_project_ownership
from app.models import Chapter
from app.schemas.chapter import CreateChapterReq, UpdateChapterReq, ChapterResp

logger = logging.getLogger(__name__)


class ChapterService:
    """Service for chapter operations."""

    async def create_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        req: CreateChapterReq,
    ) -> ChapterResp:
        """Create a new chapter."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # 自动计算章节序号：取最大 chapter_number + 1
        max_num = await chapter_dao.get_max_chapter_number(db, project_id)
        chapter_number = max_num + 1
        
        # Create chapter
        chapter = Chapter(
            project_id=project_id,
            title=req.title,
            chapter_number=chapter_number,
            content=None,
            status="draft",
            phase4_status="pending",
            word_count=0,
        )
        
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
        
        return ChapterResp.model_validate(chapter)

    async def list_chapters(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> list[ChapterResp]:
        """List chapters in a project."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        chapters = await chapter_dao.get_by_project(db, project_id)
        return [ChapterResp.model_validate(c) for c in chapters]

    async def get_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
    ) -> ChapterResp:
        """Get single chapter."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        return ChapterResp.model_validate(chapter)

    async def update_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        req: UpdateChapterReq,
    ) -> ChapterResp:
        """Update chapter."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        # Update fields
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(chapter, field):
                setattr(chapter, field, value)
        
        # Update word count if content changed
        if "content" in update_data and update_data["content"]:
            chapter.word_count = len(update_data["content"])
        
        await db.commit()
        await db.refresh(chapter)
        
        return ChapterResp.model_validate(chapter)

    async def delete_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
    ) -> None:
        """Delete chapter."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        await db.delete(chapter)
        
        # Update project chapter count
        project.chapter_count = max(0, (project.chapter_count or 0) - 1)
        
        await db.commit()

    async def reorder_chapters(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_numbers: list[int],
    ) -> list[ChapterResp]:
        """Reorder chapters by providing new chapter numbers."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get all chapters
        chapters = await chapter_dao.get_by_project(db, project_id)
        
        if len(chapter_numbers) != len(chapters):
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="Number of chapter numbers must match number of chapters",
            )
        
        # Update chapter numbers
        for chapter, new_number in zip(chapters, chapter_numbers):
            chapter.chapter_number = new_number
        
        await db.commit()
        
        # Return reordered chapters
        chapters = await chapter_dao.get_by_project(db, project_id)
        return [ChapterResp.model_validate(c) for c in chapters]

    async def confirm_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        confirm_data: Optional[dict] = None,
    ) -> ChapterResp:
        """Confirm a chapter and trigger Phase 4 processing.
        
        This marks the chapter as confirmed and triggers asynchronous Phase 4
        processing to update the four databases (四库) and dynamic layer.
        """
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        # Update chapter status to confirmed
        chapter.status = "confirmed"
        chapter.confirmed_at = datetime.now(timezone.utc)
        chapter.phase4_status = "processing"
        await db.flush()
        
        # 创建 Phase4Task 记录（带 nonce 实现幂等性保护）
        from uuid import uuid4
        from datetime import datetime as dt
        from app.models.phase4_task import Phase4Task
        
        # 生成 nonce: ch${chapter_id}_${timestamp}_${uuid_suffix}
        nonce = f"ch{chapter_id}_{int(dt.now().timestamp())}_{uuid4().hex[:8]}"
        phase4_task = Phase4Task(
            nonce=nonce,
            project_id=str(project_id),
            chapter_id=str(chapter_id),
            status="pending",
        )
        db.add(phase4_task)
        await db.flush()
        await db.refresh(phase4_task)
        
        await db.commit()
        await db.refresh(chapter)
        
        # 异步触发 Phase 4 完整收纳管线（Phase4Service 完整流程）
        # 共 4 步：LLM 分析 → 动态层 → 四库 → 卡牌池
        # 使用优雅降级：Celery 不可用时走同步快速通路
        try:
            from app.worker.phase4_task import execute_phase4_storage
            execute_phase4_storage.delay(phase4_task.id)
            logger.info(
                f"Phase 4 full pipeline dispatched for chapter {chapter_id} "
                f"(task_id={phase4_task.id}, nonce={nonce})"
            )
        except ImportError as e:
            logger.warning(
                f"Phase 4 Celery task not available, falling back to basic vault update: {e}"
            )
            try:
                from app.worker.phase4_task import update_vault_entries
                update_vault_entries.delay(project_id, chapter_id)
            except Exception as e:
                logger.error(f"后台vault更新失败: {e}")
        except Exception as e:
            logger.error(
                f"Failed to dispatch Phase 4 task for chapter {chapter_id}: {e}",
                exc_info=True,
            )
            # 优雅降级：即使 Phase 4 失败，章节确认仍然成功
        
        return ChapterResp.model_validate(chapter)

    async def revise_chapter(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        revise_data: Optional[dict] = None,
    ) -> ChapterResp:
        """Mark a chapter for revision (reject/revise).
        
        This returns the chapter to draft status for further editing.
        Phase 4 processing is NOT triggered.
        """
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        # Update chapter status back to draft for revision
        chapter.status = "draft"
        chapter.confirmed_at = None
        chapter.phase4_status = "pending"
        
        await db.commit()
        await db.refresh(chapter)
        
        return ChapterResp.model_validate(chapter)

    async def get_suggestions(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
    ) -> dict:
        """Get AI-powered suggestions for a chapter."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )

        # Generate suggestions based on chapter content and vault data
        suggestions = []

        # Suggestion type 1: Check for unused characters
        from app.dao import vault_dao
        characters = await vault_dao.get_characters(db, project_id)
        active_characters = [c for c in characters if c.status == "active"]

        if active_characters:
            suggestions.append({
                "type": "character_appearance",
                "title": "角色出场建议",
                "content": f"当前有 {len(active_characters)} 个活跃角色，考虑在本章让更多角色出场互动。",
                "priority": "medium",
            })

        # Suggestion type 2: Check for dormant plot promises
        promises = await vault_dao.get_plot_promises(db, project_id)
        dormant = [p for p in promises if p.status == "dormant"]

        if dormant:
            suggestions.append({
                "type": "plot_promise",
                "title": "伏笔回收建议",
                "content": f"有 {len(dormant)} 个伏笔处于休眠状态，考虑在本章回收其中 1-2 个。",
                "priority": "high",
            })

        # Suggestion type 3: Check chapter length
        if chapter.word_count > 0 and chapter.word_count < 500:
            suggestions.append({
                "type": "length",
                "title": "章节长度偏短",
                "content": f"本章当前 {chapter.word_count} 字，建议扩展到 1000-2000 字以获得更好的阅读体验。",
                "priority": "low",
            })

        return {
            "success": True,
            "chapter_id": chapter_id,
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
        }

    async def send_agent_instruction(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        instruction: dict,
    ) -> dict:
        """Send instruction to AI agent for chapter generation.
        
        This is used to intervene during the generation process.
        """
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get chapter
        chapter = await chapter_dao.get(db, chapter_id)
        if chapter is None or chapter.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )

        # Validate instruction
        instruction_type = instruction.get("type", "")
        content = instruction.get("content", "")

        if not instruction_type:
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="Instruction type is required",
            )

        # Process instruction (in a real implementation, this would send to LLM or task queue)
        # For now, we just save it to the chapter's generation_prompt
        if chapter.generation_prompt:
            chapter.generation_prompt += f"\n[Instruction: {instruction_type}] {content}"
        else:
            chapter.generation_prompt = f"[Instruction: {instruction_type}] {content}"

        await db.commit()
        await db.refresh(chapter)

        return {
            "success": True,
            "message": "Instruction sent to AI agent",
            "instruction_type": instruction_type,
            "chapter_status": chapter.status,
        }


# Singleton instance
chapter_service = ChapterService()
