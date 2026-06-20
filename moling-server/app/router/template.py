"""墨灵 (Moling) — 项目模板 API 路由。

实现列出模板、获取模板详情、创建/更新/删除模板、使用模板创建项目等端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.template_service import template_service
from app.schemas.template import TemplateResp, CreateTemplateReq, UpdateTemplateReq, TemplateListResp, CreateProjectFromTemplateResp
from app.models.user import User

router = APIRouter()


@router.get("", response_model=TemplateListResp)
async def list_templates(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    genre: str = Query(None, description="按题材筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateListResp:
    """获取模板列表。"""
    result = await template_service.list_templates(
        db,
        page=page,
        page_size=page_size,
        genre=genre,
    )
    return result


@router.get("/{template_id}", response_model=TemplateResp)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResp:
    """获取模板详情。"""
    result = await template_service.get_template(db, template_id)
    return result


@router.post("", response_model=TemplateResp, status_code=201)
async def create_template(
    req: CreateTemplateReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResp:
    """创建新模板（需要登录）。"""
    result = await template_service.create_template(db, req)
    return result


@router.put("/{template_id}", response_model=TemplateResp)
async def update_template(
    template_id: int,
    req: UpdateTemplateReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResp:
    """更新模板（需要登录）。"""
    result = await template_service.update_template(db, template_id, req)
    return result


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """删除模板（需要登录）。"""
    await template_service.delete_template(db, template_id)


@router.post("/{template_id}/create-project", response_model=CreateProjectFromTemplateResp, status_code=201)
async def create_project_from_template(
    template_id: int,
    title: str = Query(..., description="项目标题"),
    author: str = Query(None, description="作者"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateProjectFromTemplateResp:
    """使用模板创建新项目。"""
    result = await template_service.create_project_from_template(
        db,
        str(current_user.id),
        template_id,
        title=title,
        author=author,
    )
    return result
