"""墨灵 (Moling) — Weave (编织) API 路由。

实现获取编织建议、应用编织、分析项目编织质量等端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.weave_service import weave_service
from app.schemas.weave import WeaveSuggestionResp, ApplyWeaveReq, WeaveAnalysisResp

router = APIRouter()


@router.get("/suggestions/{project_id}", response_model=WeaveSuggestionResp)
async def get_suggestions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WeaveSuggestionResp:
    """获取项目的编织建议。"""
    result = await weave_service.get_suggestions(db, project_id)
    return result


@router.post("/apply", status_code=200)
async def apply_suggestions(
    req: ApplyWeaveReq,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """应用编织建议到指定章节。"""
    result = await weave_service.apply_suggestions(db, req)
    return result


@router.get("/analyze/{project_id}", response_model=WeaveAnalysisResp)
async def analyze_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WeaveAnalysisResp:
    """深度分析项目的编织质量。"""
    result = await weave_service.analyze_project(db, project_id)
    return result
