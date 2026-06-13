"""墨灵 (Moling) — Project API Router.

Provides endpoints for project CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.project import CreateProjectReq, ProjectResp, ProjectStatsResp, UpdateProjectReq
from app.service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResp, status_code=201)
async def create_project(
    req: CreateProjectReq,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Create a new project."""
    return await project_service.create_project(db, current_user["id"], req)


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """List projects with pagination."""
    return await project_service.list_projects(db, current_user["id"], page, page_size, status)


@router.get("/stats", response_model=ProjectStatsResp)
async def get_project_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectStatsResp:
    """Get project statistics for current user."""
    return await project_service.get_project_stats(db, current_user["id"])


@router.get("/{project_id}", response_model=ProjectResp)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Get single project by ID."""
    return await project_service.get_project(db, current_user["id"], project_id)


@router.put("/{project_id}", response_model=ProjectResp)
async def update_project(
    project_id: int,
    req: UpdateProjectReq,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectResp:
    """Update project by ID."""
    return await project_service.update_project(db, current_user["id"], project_id, req)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete project by ID."""
    await project_service.delete_project(db, current_user["id"], project_id)
