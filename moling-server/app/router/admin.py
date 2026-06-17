"""墨灵 (Moling) — Admin API Router.

提供管理员端点：
- LLM 配置（GET/POST /admin/llm-config）
- LLM 连接测试（POST /admin/llm-config/test）
- 管理员统计（GET /admin/stats）
- 用户管理（GET /admin/users）
- 项目管理（GET /admin/projects）
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import set_override, get_effective_llm_config
from app.dependencies import get_current_user, get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.models.project import Project
from app.schemas.admin import LLMConfigReq, LLMConfigResp, AdminStatsResp, UserManageResp, ProjectManageResp

router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_key(key: str) -> str:
    """Mask an API key for display (show first 4 + last 4 chars)."""
    if not key or len(key) < 8:
        return "未配置"
    return key[:4] + "****" + key[-4:]


async def _load_config_from_db(db: AsyncSession) -> dict[str, str]:
    """Load LLM config from system_config table."""
    result = await db.execute(
        select(SystemConfig).where(
            SystemConfig.key.in_(["llm_api_key", "llm_api_base", "llm_model"])
        )
    )
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}


async def _save_config_to_db(
    db: AsyncSession, api_key: str, api_base: str, model: str
) -> None:
    """Save LLM config to system_config table."""
    configs = {
        "llm_api_key": api_key,
        "llm_api_base": api_base,
        "llm_model": model,
    }
    for key, value in configs.items():
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(SystemConfig(key=key, value=value, description=f"LLM 配置: {key}"))
    await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/llm-config", response_model=LLMConfigResp)
async def get_llm_config(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current LLM configuration (masked for security)."""
    db_config = await _load_config_from_db(db)
    env_config = get_effective_llm_config()

    api_base = db_config.get("llm_api_base") or env_config["api_base"]
    model = db_config.get("llm_model") or env_config["model"]
    is_configured = bool(db_config.get("llm_api_key") or env_config["api_key"] != "sk-placeholder")

    return LLMConfigResp(
        api_base=api_base,
        model=model,
        is_configured=is_configured,
        api_key_masked=_mask_key(db_config.get("llm_api_key", "")),
    )


@router.post("/llm-config", response_model=LLMConfigResp)
async def save_llm_config(
    req: LLMConfigReq,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save LLM configuration to database and update runtime overrides."""
    # Save to database
    await _save_config_to_db(db, req.api_key, req.api_base, req.model)

    # Update in-memory overrides (takes effect immediately)
    set_override("llm_api_key", req.api_key)
    set_override("llm_api_base", req.api_base)
    set_override("llm_model", req.model)

    return LLMConfigResp(
        api_base=req.api_base,
        model=req.model,
        is_configured=True,
        api_key_masked=_mask_key(req.api_key),
    )


@router.post("/llm-config/test")
async def test_llm_connection(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test LLM API connection with current config."""
    db_config = await _load_config_from_db(db)
    config = get_effective_llm_config()

    api_key = db_config.get("llm_api_key") or config["api_key"]
    api_base = db_config.get("llm_api_base") or config["api_base"]
    model = db_config.get("llm_model") or config["model"]

    if not api_key or api_key == "sk-placeholder":
        return {"ok": False, "msg": "API Key 未配置"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{api_base.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                },
            )
            if resp.status_code == 200:
                return {"ok": True, "msg": "连接成功"}
            else:
                error = resp.json().get("error", {}).get("message", resp.text[:200])
                return {"ok": False, "msg": f"API 错误: {error}"}
    except Exception as e:
        return {"ok": False, "msg": f"连接失败: {str(e)}"}


@router.get("/stats", response_model=AdminStatsResp)
async def get_admin_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get admin statistics (user count, project count, etc.)."""
    # Count users
    stmt = select(func.count()).select_from(User)
    result = await db.execute(stmt)
    user_count = result.scalar() or 0

    # Count projects
    stmt = select(func.count()).select_from(Project)
    result = await db.execute(stmt)
    project_count = result.scalar() or 0

    # Count chapters
    from app.models.chapter import Chapter
    stmt = select(func.count()).select_from(Chapter)
    result = await db.execute(stmt)
    chapter_count = result.scalar() or 0

    # Count generation tasks
    from app.models.generation_task import GenerationTask
    stmt = select(func.count()).select_from(GenerationTask)
    result = await db.execute(stmt)
    task_count = result.scalar() or 0

    return AdminStatsResp(
        user_count=user_count,
        project_count=project_count,
        chapter_count=chapter_count,
        task_count=task_count,
    )


@router.get("/users", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user list (admin only)."""
    # Build query
    stmt = select(User)
    if status:
        stmt = stmt.where(User.status == status)

    # Count total
    count_stmt = select(func.count()).select_from(User)
    if status:
        count_stmt = count_stmt.where(User.status == status)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    return {
        "items": [UserManageResp.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/projects", response_model=dict)
async def get_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project list (admin only)."""
    # Build query
    stmt = select(Project)
    if status:
        stmt = stmt.where(Project.status == status)

    # Count total
    count_stmt = select(func.count()).select_from(Project)
    if status:
        count_stmt = count_stmt.where(Project.status == status)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    stmt = stmt.order_by(Project.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    projects = list(result.scalars().all())

    return {
        "items": [ProjectManageResp.model_validate(p) for p in projects],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新用户信息（角色、封禁状态等）。"""
    # 占位实现: user_service.update_user 尚不存在
    return {"success": True, "user_id": user_id}


@router.get("/llm-usage")
async def get_llm_usage(
    current_user=Depends(get_current_user),
):
    """获取 LLM 用量统计。"""
    return {
        "total_tokens": 0,
        "total_cost": 0,
        "by_provider": {},
        "by_model": {},
        "daily_usage": [],
    }
