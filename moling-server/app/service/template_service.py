"""墨灵 (Moling) — Template Service.

业务逻辑：列出模板、获取模板详情、使用模板创建项目等。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import template_dao, project_dao
from app.errors import ErrorCode, NotFoundError
from app.models import Project
from app.schemas.template import TemplateResp, CreateTemplateReq, UpdateTemplateReq


class TemplateService:
    """Service for template operations."""

    async def list_templates(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        genre: Optional[str] = None,
    ) -> dict:
        """List templates with pagination."""
        skip = (page - 1) * page_size
        
        if genre:
            templates = await template_dao.get_by_genre(db, genre, skip=skip, limit=page_size)
            total = await template_dao.count_by_genre(db, genre)
        else:
            templates = await template_dao.get_multi(db, skip=skip, limit=page_size)
            total = await template_dao.count(db)
        
        return {
            "items": [TemplateResp.model_validate(t) for t in templates],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def get_template(
        self,
        db: AsyncSession,
        template_id: int,
    ) -> TemplateResp:
        """Get single template by ID."""
        template = await template_dao.get(db, template_id)
        
        if template is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Template not found",
            )
        
        return TemplateResp.model_validate(template)

    async def create_template(
        self,
        db: AsyncSession,
        req: CreateTemplateReq,
    ) -> TemplateResp:
        """Create a new template."""
        template = await template_dao.create(db, req)
        await db.commit()
        await db.refresh(template)
        
        return TemplateResp.model_validate(template)

    async def update_template(
        self,
        db: AsyncSession,
        template_id: int,
        req: UpdateTemplateReq,
    ) -> TemplateResp:
        """Update an existing template."""
        template = await template_dao.get(db, template_id)
        
        if template is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Template not found",
            )
        
        updated = await template_dao.update(db, template, req)
        await db.commit()
        await db.refresh(updated)
        
        return TemplateResp.model_validate(updated)

    async def delete_template(
        self,
        db: AsyncSession,
        template_id: int,
    ) -> None:
        """Delete a template."""
        template = await template_dao.get(db, template_id)
        
        if template is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Template not found",
            )
        
        await db.delete(template)
        await db.commit()

    async def create_project_from_template(
        self,
        db: AsyncSession,
        user_id: int,
        template_id: int,
        *,
        title: str,
        author: Optional[str] = None,
    ) -> dict:
        """Create a new project based on a template."""
        template = await template_dao.get(db, template_id)
        
        if template is None:
            raise NotFoundError(
                error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND,
                detail="Template not found",
            )
        
        # Create project with template data
        project = Project(
            user_id=user_id,
            title=title,
            author=author or "",
            genre=template.genre,
            tags=[],
            synopsis="",  # User can update later
            worldview="",  # User can update later
            protagonist="",  # User can update later
            supporting_chars=[],  # User can update later
            word_count=0,
            chapter_count=0,
            target_words=None,
            frequency=None,
            style=None,
            status="draft",
            creation_mode="template",
            template_id=template.id,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return {
            "id": project.id,
            "title": project.title,
            "genre": project.genre,
            "template_id": template.id,
            "message": "项目已创建，请根据模板结构完善内容",
        }


# Singleton instance
template_service = TemplateService()
