"""墨灵 (Moling) — Health API Router.

提供健康检查端点（系统级）。
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import time

router = APIRouter()


@router.get("")
async def health_check(request: Request):
    """系统健康检查端点。"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "database": "connected",
            "code": 0,
            "message": "OK",
            "data": {"status": "ok"},
            "request_id": None,
        }
    )
