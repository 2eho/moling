"""墨灵 (Moling) — Admin API Router.

Provides admin endpoints for:
- LLM configuration (GET/POST /admin/llm-config)
- LLM connection test (POST /admin/llm-config/test)
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import set_override, get_effective_llm_config
from app.dependencies import get_db
from app.models.system_config import SystemConfig
from app.schemas.admin import LLMConfigReq, LLMConfigResp

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
async def get_llm_config(db: AsyncSession = Depends(get_db)):
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
async def save_llm_config(req: LLMConfigReq, db: AsyncSession = Depends(get_db)):
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
async def test_llm_connection(db: AsyncSession = Depends(get_db)):
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
