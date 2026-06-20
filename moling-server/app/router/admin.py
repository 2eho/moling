"""墨灵 (Moling) — Admin API Router.

提供管理员端点：
- LLM 配置（GET/POST /admin/llm-config）
- LLM 连接测试（POST /admin/llm-config/test）
- 管理员统计（GET /admin/stats）
- 用户管理（GET /admin/users）
- 项目管理（GET /admin/projects）
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import set_override, get_effective_llm_config
from app.dao import (
    user_dao,
    project_dao,
    chapter_dao,
    generation_dao,
    system_config_dao,
)
from app.dependencies import get_current_user, get_db, require_admin
from app.errors import ErrorCode, NotFoundError
from app.schemas.admin import LLMConfigReq, LLMConfigResp, AdminStatsResp, UserManageResp, ProjectManageResp, UpdateUserReq

logger = logging.getLogger(__name__)
admin_router = APIRouter(tags=["admin"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_key(key: str) -> str:
    """Mask an API key for display (show first 4 + last 4 chars)."""
    if not key or len(key) < 8:
        return "未配置"
    return key[:4] + "****" + key[-4:]


async def _load_config_from_db(db: AsyncSession) -> dict[str, str]:
    """Load LLM config from system_config table via DAO."""
    configs = await system_config_dao.get_by_keys(
        db, ["llm_api_key", "llm_api_base", "llm_model"]
    )
    return {key: row.value for key, row in configs.items()}


async def _save_config_to_db(
    db: AsyncSession, api_key: str, api_base: str, model: str
) -> None:
    """Save LLM config to system_config table via DAO."""
    await system_config_dao.upsert_batch(
        db,
        {
            "llm_api_key": api_key,
            "llm_api_base": api_base,
            "llm_model": model,
        },
        description="LLM 配置",
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@admin_router.get("/llm-config", response_model=LLMConfigResp)
async def get_llm_config(
    _admin=Depends(require_admin),
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


@admin_router.post("/llm-config", response_model=LLMConfigResp)
async def save_llm_config(
    req: LLMConfigReq,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Save LLM configuration to database and update runtime overrides."""
    # Save to database
    await _save_config_to_db(db, req.api_key, req.api_base, req.model)

    # Update in-memory overrides (takes effect immediately)
    await set_override("llm_api_key", req.api_key)
    await set_override("llm_api_base", req.api_base)
    await set_override("llm_model", req.model)

    return LLMConfigResp(
        api_base=req.api_base,
        model=req.model,
        is_configured=True,
        api_key_masked=_mask_key(req.api_key),
    )


@admin_router.post("/llm-config/test")
async def test_llm_connection(
    _admin=Depends(require_admin),
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


@admin_router.get("/stats", response_model=AdminStatsResp)
async def get_admin_stats(
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get admin statistics (user count, project count, etc.)."""
    user_count = await user_dao.count(db)
    project_count = await project_dao.count(db)
    chapter_count = await chapter_dao.count(db)
    task_count = await generation_dao.count(db)

    return AdminStatsResp(
        user_count=user_count,
        project_count=project_count,
        chapter_count=chapter_count,
        task_count=task_count,
    )


@admin_router.get("/users", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user list (admin only)."""
    filters = {"status": status} if status else None
    skip = (page - 1) * page_size

    total = await user_dao.count(db, filters=filters)
    users = await user_dao.get_multi(
        db, skip=skip, limit=page_size, filters=filters, order_by="created_at"
    )

    return {
        "items": [UserManageResp.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@admin_router.get("/projects", response_model=dict)
async def get_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get project list (admin only)."""
    filters = {"status": status} if status else None
    skip = (page - 1) * page_size

    total = await project_dao.count(db, filters=filters)
    projects = await project_dao.get_multi(
        db, skip=skip, limit=page_size, filters=filters, order_by="updated_at"
    )

    return {
        "items": [ProjectManageResp.model_validate(p) for p in projects],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@admin_router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UpdateUserReq,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Update user info (role, ban status, etc.)."""
    user = await user_dao.get(db, user_id)
    if not user:
        raise NotFoundError(ErrorCode.USER_NOT_FOUND)

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        await db.commit()
        await db.refresh(user)

    return {"success": True, "user_id": user_id, "updated_fields": list(update_data.keys())}


@admin_router.get("/llm-usage")
async def get_llm_usage(
    _admin=Depends(require_admin),
):
    """获取 LLM 用量统计 — 从 TokenBudgetManager 和 KeyManager 查询实时数据。"""
    try:
        from app.llm.client import llm_client
        from app.llm.key_manager import key_manager

        # Token 用量（来自 TokenBudgetManager — Redis 持久化）
        budget_status = await llm_client.budget_manager.get_budget_status()

        # 密钥池健康状态（来自 KeyManager）
        pool_pro = await key_manager.get_pool_status("pro")

        return {
            "status": "ok",
            "budget": {
                "daily": budget_status["daily"],
                "monthly": budget_status["monthly"],
            },
            "key_pool": {
                "pool": pool_pro["pool"],
                "total_keys": pool_pro["total"],
                "healthy": pool_pro["healthy"],
            },
            "note": "用量数据来自 Redis 持久化的 TokenBudgetManager。多 worker 共享，服务重启不丢数据。",
        }
    except Exception as e:
        logger.error(f"Failed to query LLM usage: {e}", exc_info=True)
        return {
            "status": "NOT_IMPLEMENTED",
            "error": str(e),
            "note": "LLM 用量统计功能不可用。请检查 LLM 客户端配置和服务状态。",
        }
