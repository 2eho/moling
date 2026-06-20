"""Moling - Project Service.

Business logic for project CRUD + chapter count enrichment.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, vault_dao
from app.errors import NotFoundError, ErrorCode
from app.utils.security import verify_project_ownership
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
        """List projects with pagination (via DAO)."""
        filters: dict = {"user_id": user_id}
        if status:
            filters["status"] = status

        total = await project_dao.count(db, filters=filters)
        projects = await project_dao.get_multi(
            db, filters=filters,
            skip=(page - 1) * page_size, limit=page_size,
            order_by="updated_at", descending=True,
        )
        
        # Enrich with chapter count
        for project in projects:
            project.chapter_count = await chapter_dao.count_by_project(db, int(project.id))
        
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
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Enrich with chapter count
        project.chapter_count = await chapter_dao.count_by_project(db, int(project.id))
        
        return ProjectResp.model_validate(project)

    async def update_project(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int,
        req: UpdateProjectReq,
    ) -> ProjectResp:
        """Update project with ownership check."""
        project = await verify_project_ownership(db, project_id, user_id)
        
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
        project = await verify_project_ownership(db, project_id, user_id)
        
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

    async def get_suggestions(
        self,
        db: AsyncSession,
        user_id: int,
        project_id: int,
    ) -> dict:
        """Get AI-powered writing suggestions for a project."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        suggestions = []

        # Suggestion type 1: Chapter completion status
        completed_count = await chapter_dao.count_by_project(db, int(project_id), status="completed")
        total_chapters = await chapter_dao.count_by_project(db, int(project_id))

        if total_chapters > 0:
            completion_rate = (completed_count / total_chapters) * 100
            if completion_rate < 50:
                suggestions.append({
                    "type": "completion",
                    "title": "章节完成率较低",
                    "content": f"当前完成率 {completion_rate:.1f}%（{completed_count}/{total_chapters}），建议优先完成草稿章节。",
                    "priority": "high",
                })

        # Suggestion type 2: Character participation
        active_characters = await vault_dao.count_characters_by_status(
            db, int(project_id), "active"
        )

        if active_characters > 5 and total_chapters > 0:
            suggestions.append({
                "type": "character_balance",
                "title": "角色数量较多",
                "content": f"当前有 {active_characters} 个活跃角色，注意平衡各角色的出场时间和戏份。",
                "priority": "medium",
            })

        # Suggestion type 3: Plot promise recycling
        dormant_promises = await vault_dao.count_plot_promises_by_status(
            db, int(project_id), "dormant"
        )

        if dormant_promises > 3:
            suggestions.append({
                "type": "plot_promise",
                "title": "伏笔待回收",
                "content": f"有 {dormant_promises} 个伏笔处于休眠状态，建议适时回收以推进剧情。",
                "priority": "medium",
            })

        return {
            "success": True,
            "project_id": project_id,
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
        }


# Singleton instance
project_service = ProjectService()
