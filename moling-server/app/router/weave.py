"""墨灵 (Moling) — Weave (编织) API 路由。

实现获取编织建议、应用编织、分析项目编织质量、获取编织模式列表等端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.weave_service import weave_service
from app.schemas.weave import WeaveSuggestionResp, ApplyWeaveReq, WeaveAnalysisResp, ApplyWeaveResp
from app.models.user import User

router = APIRouter()

WEAVE_PATTERNS = [
    {"id": "foreshadowing", "name": "伏笔埋设", "description": "在前期章节埋下伏笔，后期回收"},
    {"id": "character_arc", "name": "角色弧光", "description": "角色成长轨迹的编织"},
    {"id": "subplot_interweave", "name": "副线交织", "description": "多条副线交替推进"},
    {"id": "cliffhanger", "name": "悬念钩子", "description": "章节结尾设置悬念"},
    {"id": "callback", "name": "回调呼应", "description": "与前期情节/对话呼应"},
    {"id": "mirror_scene", "name": "镜像场景", "description": "相似场景的对比呈现"},
]


@router.get("/patterns", response_model=list[dict])
async def list_weave_patterns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """获取可用的编织模式列表。"""
    return WEAVE_PATTERNS


@router.get("/suggestions/{project_id}", response_model=WeaveSuggestionResp)
async def get_suggestions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeaveSuggestionResp:
    """获取项目的编织建议。"""
    result = await weave_service.get_suggestions(db, project_id)
    return result


@router.post("/apply", response_model=ApplyWeaveResp, status_code=200)
async def apply_suggestions(
    req: ApplyWeaveReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """应用编织建议到指定章节。"""
    result = await weave_service.apply_suggestions(db, req)
    return result


@router.get("/analyze/{project_id}", response_model=WeaveAnalysisResp)
async def analyze_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeaveAnalysisResp:
    """深度分析项目的编织质量。"""
    result = await weave_service.analyze_project(db, project_id)
    return result
