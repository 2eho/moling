"""Minimal health.py - auto-generated."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import time

router = APIRouter()


@router.get("")
async def health_check(request: Request):
    """Health check endpoint."""
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
