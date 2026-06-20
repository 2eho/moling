"""墨灵 (Moling) — Health API Router.

提供健康检查端点（系统级）。
"""

import logging
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """系统健康检查端点 — 实际检测数据库连通性。"""
    db_status = "disconnected"
    try:
        result = await db.execute(text("SELECT 1"))
        row = result.scalar()
        db_status = "connected" if row == 1 else "disconnected"
        db_code = 0
    except Exception as e:
        logger.warning(f"Health check: database unreachable — {e}")
        db_status = "disconnected"
        db_code = 1

    overall_status = "ok" if db_status == "connected" else "degraded"

    return JSONResponse(
        status_code=200,
        content={
            "status": overall_status,
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "database": db_status,
            "code": db_code,
            "message": "OK" if db_status == "connected" else "Database connectivity check failed",
            "data": {"status": overall_status},
            "request_id": None,
        },
    )
