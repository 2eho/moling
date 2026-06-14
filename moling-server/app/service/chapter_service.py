"""Moling - Chapter Service.

Business logic for chapter CRUD operations.
"""

from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import chapter_dao, project_dao
from app.errors import NotFoundError, ErrorCode, PermissionError
from app.models import Chapter, Project
from app.schemas.chapter import CreateChapterReq, UpdateChapterReq, ChapterResp


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
        
        # Check if chapter number already exists
        existing = await chapter_dao.get_by_number(db, project_id, req.chapter_number)
        if existing:
            raise PermissionError(
                error_code=ErrorCode.CHAPTER_NUMBER_EXISTS,
                detail=f"Chapter number {req.chapter_number} already exists",
            )
        
        # Create chapter
        chapter = Chapter(
            project_id=project_id,
            title=req.title,
            chapter_number=req.chapter_number,
            content=None,
            status="draft",
            phase4_status="pending",
            word_count=0,
        )
        
        db.add(chapter)
        
        # Update project chapter count
        project.chapter_count = (project.chapter_count or 0) + 1
        
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
        
        await db.commit()
        await db.refresh(chapter)
        
        # TODO: Trigger Phase 4 asynchronous processing here
        # This would typically be done via a background task or message queue
        # For now, we just mark it as processing
        
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
