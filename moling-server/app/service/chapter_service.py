"""Moling - Chapter Service.

Business logic for chapter CRUD operations.
"""

from typing import Optional

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


# Singleton instance
chapter_service = ChapterService()
