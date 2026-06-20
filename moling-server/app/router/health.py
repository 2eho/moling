"""墨灵 (Moling) — Health API Router.

提供健康检查端点（系统级），验证数据库、Redis、Celery 连通性。
"""

import logging
import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """系统健康检查端点 — 检测数据库、Redis、Celery 连通性。"""
    checks = {}
    overall_healthy = True

    # ── 1. Database ──
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = "connected"
        else:
            checks["database"] = "disconnected"
            overall_healthy = False
    except Exception as e:
        logger.warning(f"Health check: database unreachable — {e}")
        checks["database"] = "disconnected"
        overall_healthy = False

    # ── 2. Redis ──
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        pong = await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = "connected" if pong else "disconnected"
    except Exception as e:
        logger.warning(f"Health check: Redis unreachable — {e}")
        checks["redis"] = "disconnected"
        overall_healthy = False

    # ── 3. Celery ──
    try:
        from celery.execute import send_task
        from app.worker.celery_app import celery_app

        result = celery_app.control.ping(timeout=3)
        checks["celery"] = "connected" if result else "no_workers"
        if not result:
            overall_healthy = False
    except Exception as e:
        logger.warning(f"Health check: Celery unreachable — {e}")
        checks["celery"] = "unreachable"
        overall_healthy = False

    # ── 4. Aggregate ──
    status = "ok" if overall_healthy else "degraded"
    db_code = 0 if checks.get("database") == "connected" else 1

    return JSONResponse(
        status_code=200,
        content={
            "status": status,
            "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "1.0.0",
            "timestamp": int(time.time()),
            "checks": checks,
            "database": checks["database"],
            "code": db_code,
            "message": "All systems operational" if overall_healthy else f"Degraded: {', '.join(k for k, v in checks.items() if v != 'connected')}",
            "data": {"status": status},
            "request_id": None,
        },
    )
