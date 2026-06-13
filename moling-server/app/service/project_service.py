"""Moling - Project Service.

Business logic for project CRUD + chapter count enrichment.
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao
from app.errors import NotFoundError, ErrorCode, PermissionError
from app.models import Project
from app.schemas.project import CreateProjectReq, UpdateProjectReq, ProjectResp, ProjectStatsResp

settings = get_settings()


class ProjectService:
    """Service for project operations."""

    async def create_project(
        self,
        db: AsyncSession,
        user_id: int,
        req: CreateProjectReq,
    ) -> ProjectResp:
        """Create a new project."""
        # Create project instance
        project = Project(
            user_id=user_id,
            title=req.title,
            author=req.author,
            genre=req.genre,
            tags=req.tags,
            synopsis=req.synopsis,
            worldview=req.worldview,
            protagonist=req.protagonist,
            supporting_chars=req.supporting_chars,
            word_count=0,
            chapter_count=0,
            target_words=req.target_words,
            frequency=req.frequency,
            style=req.style,
            status="draft",
            creation_mode=req.creation_mode,
            template_id=req.template_id,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return ProjectResp.model_validate(project)

    async def list_projects(
        self,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> dict:
        """List projects with pagination."""
        # Build query
        stmt = select(Project).where(Project.user_id == user_id)
        
        if status:
            stmt = stmt.where(Project.status == status)
        
        # Count total
        count_stmt = select(func.count()).select_from(Project).where(Project.user_id == user_id)
        if status:
            count_stmt = count_stmt.where(Project.status == status)
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.order_by(Project.updated_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(stmt)
        projects = list(result.scalars().all())
        
        # Enrich with chapter count
        for project in projects:
            chapters_stmt = select(func.count()).select_from(project.chapters.property.mapper.class_).where(
                project.chapters.property.mapper.class_.project_id == project.id
            )
            chapters_result = await db.execute(chapters_stmt)
            project.chapter_count = chapters_result.scalar_one()
        
        return {
            "items": [ProjectResp.model_validate(p) for p in projects],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def get_project(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int,
    ) -> ProjectResp:
        """Get single project with ownership check."""
        project = await project_dao.get(db, project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.PROJECT_ACCESS_DENIED,
                detail="Not authorized to access this project",
            )
        
        # Enrich with chapter count
        chapters_stmt = select(func.count()).select_from(project.chapters.property.mapper.class_).where(
            project.chapters.property.mapper.class_.project_id == project.id
        )
        chapters_result = await db.execute(chapters_stmt)
        project.chapter_count = chapters_result.scalar_one()
        
        return ProjectResp.model_validate(project)

    async def update_project(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int,
        req: UpdateProjectReq,
    ) -> ProjectResp:
        """Update project with ownership check."""
        project = await project_dao.get(db, project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.PROJECT_ACCESS_DENIED,
                detail="Not authorized to update this project",
            )
        
        # Update fields
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(project, field):
                setattr(project, field, value)
        
        await db.commit()
        await db.refresh(project)
        
        return ProjectResp.model_validate(project)

    async def delete_project(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int,
    ) -> None:
        """Delete project with ownership check."""
        project = await project_dao.get(db, project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.PROJECT_ACCESS_DENIED,
                detail="Not authorized to delete this project",
            )
        
        await db.delete(project)
        await db.commit()

    async def get_project_stats(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> ProjectStatsResp:
        """Get project statistics for a user."""
        stats = await project_dao.get_stats(db, user_id)
        return ProjectStatsResp(**stats)


# Singleton instance
project_service = ProjectService()
