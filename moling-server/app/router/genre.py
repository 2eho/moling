"""墨灵 (Moling) — Genre 冷启动 API 路由。

实现 B1-B5 用户交互接口：
  POST /api/v1/genre/prefill              → 触发 B1-B5 并返回预填数据
  GET  /api/v1/genre/prefill/{project_id}  → 获取预填结果供用户审核
  POST /api/v1/genre/prefill/{project_id}/confirm  → 用户确认并入库
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_current_user, get_db
from app.errors import AppError, NotFoundError, ValidationError
from app.genre.cold_start_loader import ColdStartLoader, DataRetirementManager, KNOWN_GENRES
from app.schemas.auth import UserResp
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PrefillRequest(BaseModel):
    """触发冷启动请求"""
    project_id: int
    genre: str = Field(..., min_length=1, max_length=20)
    synopsis: str = Field(..., min_length=10, max_length=2000)

    @field_validator("genre")
    @classmethod
    def validate_genre(cls, v: str) -> str:
        if v not in KNOWN_GENRES:
            raise ValueError(f"不支持的类型: {v}，可选: {', '.join(sorted(KNOWN_GENRES))}")
        return v


class PrefillResponse(BaseModel):
    """预填数据响应"""
    project_id: int
    genre: str
    synopsis: str
    profile_source: str
    profile_version: str
    vault: dict[str, Any]
    dynamic_layer: dict[str, Any]
    card_pool: list[dict[str, Any]]
    opening_directions: list[str]
    async_analysis_triggered: bool
    session_id: str


class PrefillSessionResponse(BaseModel):
    """预填会话详情响应"""
    session_id: str
    project_id: int
    genre: str
    synopsis: str
    state: str
    prefill_data: Optional[dict[str, Any]] = None
    profile_source: str
    profile_version: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ModificationItem(BaseModel):
    """用户修改项"""
    path: str
    action: str = "update"  # update / delete / add
    value: Any = None


class ConfirmRequest(BaseModel):
    """确认预填请求（可选修改）"""
    modifications: Optional[list[ModificationItem]] = None


class ConfirmResponse(BaseModel):
    """确认入库响应"""
    project_id: int
    state: str = "confirmed"
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/prefill", response_model=PrefillResponse)
async def trigger_prefill(
    req: PrefillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResp = Depends(get_current_user),
):
    """
    B1-B5 完整冷启动流程。

    1. 验证用户对项目的所有权
    2. 执行 B1-B5 冷启动
    3. 返回预填数据供前端展示
    """
    from app.dao import project_dao
    from app.errors import PermissionError

    project = await project_dao.get(db, str(req.project_id))
    if project is None:
        raise NotFoundError(detail=f"Project {req.project_id} not found")
    if project.user_id != str(current_user.id):
        raise PermissionError(detail="无权访问该项目")
    try:
        loader = ColdStartLoader()

        # Ensure tables exist
        from app.genre.cold_start_loader import _ensure_tables
        await _ensure_tables(db)

        # Run cold start
        result = await loader.run_cold_start(
            db=db,
            project_id=req.project_id,
            genre=req.genre,
            synopsis=req.synopsis,
        )

        # Get session for session_id
        session = await loader.get_prefill_session(db, req.project_id)
        session_id = session["id"] if session else ""

        card_pool_data = [
            {
                "direction": c.direction,
                "reason": c.reason,
                "priority": c.priority,
                "freshness_multiplier": c.freshness_multiplier,
                "tags": c.tags,
            }
            for c in result.card_pool
        ]

        return PrefillResponse(
            project_id=req.project_id,
            genre=result.genre,
            synopsis=result.synopsis,
            profile_source=result.profile_source,
            profile_version=result.profile_version,
            vault={
                "character_prototypes": result.vault.character_prototypes,
                "world_templates": result.vault.world_templates,
                "timeline_skeleton": result.vault.timeline_skeleton,
            },
            dynamic_layer={
                "opening_state": result.dynamic_layer.opening_state,
                "chapter_anchors": result.dynamic_layer.chapter_anchors,
                "initial_hooks": result.dynamic_layer.initial_hooks,
            },
            card_pool=card_pool_data,
            opening_directions=result.opening_directions,
            async_analysis_triggered=result.async_analysis_triggered,
            session_id=session_id,
        )
    except AppError:
        raise
    except Exception as e:
        from app.errors import ErrorCode
        logger.error("冷启动失败: project_id=%d, genre=%s, error=%s", req.project_id, req.genre, e)
        raise AppError(ErrorCode.INTERNAL_ERROR, detail=f"冷启动失败: {str(e)}")


@router.get("/prefill/{project_id}", response_model=PrefillSessionResponse)
async def get_prefill(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResp = Depends(get_current_user),
):
    """获取预填结果供用户审核（B5 审核界面用）。"""
    try:
        loader = ColdStartLoader()
        session = await loader.get_prefill_session(db, project_id)
        if session is None:
            raise NotFoundError(detail=f"Project {project_id} 没有预填数据")

        return PrefillSessionResponse(
            session_id=session["id"],
            project_id=session["project_id"],
            genre=session["genre"],
            synopsis=session["synopsis"],
            state=session["state"],
            prefill_data=session["prefill_data"],
            profile_source=session["profile_source"],
            profile_version=session["profile_version"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )
    except AppError:
        raise
    except Exception as e:
        from app.errors import ErrorCode
        logger.error("获取预填数据失败: project_id=%d, error=%s", project_id, e)
        raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))


@router.post("/prefill/{project_id}/confirm", response_model=ConfirmResponse)
async def confirm_prefill(
    project_id: int,
    req: ConfirmRequest = ConfirmRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: UserResp = Depends(get_current_user),
):
    """用户确认预填数据并入库（B5 最终步骤）。"""
    try:
        loader = ColdStartLoader()
        mods = None
        if req.modifications:
            mods = [m.model_dump() for m in req.modifications]
        result = await loader.confirm_prefill(db, project_id, modifications=mods)
        return ConfirmResponse(**result)
    except ValueError as e:
        raise ValidationError(detail=str(e))
    except AppError:
        raise
    except Exception as e:
        from app.errors import ErrorCode
        logger.error("确认预填失败: project_id=%d, error=%s", project_id, e)
        raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))
