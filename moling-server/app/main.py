"""墨灵 (Moling) — FastAPI Application Entry Point."""

from __future__ import annotations

import platform  # noqa: E402 — needed for Windows check

# CRITICAL: import dependencies FIRST so that the Windows greenlet_spawn
# monkey-patch is applied before any SQLAlchemy imports load.
import app.dependencies  # noqa: E402  -- must be early

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.errors import AppError


# ---------------------------------------------------------------------------
# Lifespan — manage connection pools
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle for database and Redis connections."""
    from app.dependencies import engine, async_session_factory, get_redis
    from app.models.base import Base
    from app.config import get_settings

    settings = get_settings()

    # --- 自动创建数据库表（开发环境，Windows 用同步引擎避免 greenlet 问题）---
    if platform.system() == "Windows":
        # Windows：用同步引擎创建表，完全避开 greenlet
        try:
            from sqlalchemy import create_engine
            sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
            sync_engine = create_engine(sync_url, echo=False)
            Base.metadata.create_all(bind=sync_engine)
            sync_engine.dispose()
            print("[OK] Database tables created (Windows sync engine)")
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            raise
    else:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[OK] Database tables created (async run_sync)")
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            raise

    # --- Redis 连接（失败时优雅降级）---
    try:
        redis_conn = await get_redis()
        _app.state.redis = redis_conn
        print("[OK] Redis connected")
    except Exception as e:
        _app.state.redis = None
        print(f"[WARN] Redis unavailable (ignored): {e}")

    # --- 从数据库加载 LLM 配置（覆盖内存）---
    # Windows 上暂时跳过（避免 greenlet 问题）
    if platform.system() != "Windows":
        try:
            from sqlalchemy import select
            from app.config import set_override
            from app.models.system_config import SystemConfig
            
            # 使用异步 session 查询 system_config 表
            from app.dependencies import async_session_factory
            async with async_session_factory() as session:
                result = await session.execute(
                    select(SystemConfig).where(
                        SystemConfig.key.in_(["llm_api_key", "llm_api_base", "llm_model"])
                    )
                )
                rows = result.scalars().all()
                config_dict = {row.key: row.value for row in rows}
                
                if config_dict.get("llm_api_key"):
                    set_override("llm_api_key", config_dict["llm_api_key"])
                    print(f"[OK] LLM config loaded from DB (model: {config_dict.get('llm_model', 'N/A')})")
                else:
                    print("[INFO] No LLM config in DB, using .env defaults")
        except Exception as e:
            print(f"[WARN] Failed to load LLM config from DB (ignored): {e}")
    else:
        print("[INFO] Skipping LLM config load on Windows (greenlet issue)")

    _app.state.db_engine = engine

    yield

    # --- Shutdown ---
    try:
        if hasattr(engine, 'dispose') and callable(getattr(engine, 'dispose')):
            # 直接用同步方式 dispose（避免 greenlet）
            engine.dispose()
    except Exception as e:
        print(f"[WARN] Engine dispose failed (ignored): {e}")
    if _app.state.redis is not None:
        try:
            await _app.state.redis.aclose()
        except Exception as e:
            print(f"[WARN] Redis close failed (ignored): {e}")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Moling API",
    description="墨灵 — AI 小说创作平台后端服务",
    version=__version__,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

from app.middleware import (
    AuditLogMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    ResponseFormatMiddleware,
)
from app.config import get_settings
from app import __version__

settings = get_settings()

# 1. Request ID — 为每个请求注入唯一标识（必须在最外层）
app.add_middleware(RequestIDMiddleware)

# 2. CORS — 跨域配置（根据环境动态设置）
_cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []

if settings.ENVIRONMENT == "production":
    # 生产环境：只允许配置的域名（若配置了 "*" 则放行所有）
    if "*" in _cors_origins:
        allow_origins = ["*"]
    else:
        allow_origins = _cors_origins
else:
    # 开发/测试环境：允许配置的域名 + localhost
    allow_origins = _cors_origins + [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate Limit — 请求频率限制（从配置读取）
rate_limit_calls = getattr(settings, 'RATE_LIMIT_CALLS', 1000)
rate_limit_period = getattr(settings, 'RATE_LIMIT_PERIOD', 60)
app.add_middleware(RateLimitMiddleware, calls=rate_limit_calls, period=rate_limit_period)

# 4. Audit Log — 审计日志（需要在认证之前以记录所有请求）
app.add_middleware(AuditLogMiddleware)

# 5. Response Format — 统一响应格式（必须在最内层，包装最终响应）
app.add_middleware(ResponseFormatMiddleware, version=__version__)

# ---------------------------------------------------------------------------
# Static files — serve docs/ at /docs-static
# ---------------------------------------------------------------------------

import os  # noqa: E402
from pathlib import Path  # noqa: E402

static_docs_dir = Path(__file__).resolve().parent.parent / "docs"
if static_docs_dir.is_dir():
    app.mount("/docs-static", StaticFiles(directory=str(static_docs_dir)), name="docs")

# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Translate any ``AppError`` subclass into the unified error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code.value,  # 使用数字业务码
            "message": exc.detail,
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", ""),
                "timestamp": int(__import__("time").time() * 1000),
                "version": __version__,
            },
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak internals."""
    # 打印实际异常信息用于调试
    import traceback
    traceback.print_exc()
    
    # 在开发环境下返回详细错误信息
    error_detail = traceback.format_exc() if settings.ENVIRONMENT == "development" else str(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 50001,  # INTERNAL_ERROR 的数字码
            "message": "服务器内部错误",
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", ""),
                "timestamp": int(__import__("time").time() * 1000),
                "version": __version__,
                "error_detail": error_detail if settings.ENVIRONMENT == "development" else None,
            },
        },
    )


# ---------------------------------------------------------------------------
# Prometheus Metrics — 性能指标收集
# ---------------------------------------------------------------------------

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    
    # 创建 Prometheus instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/api/v1/health", "/api/v1/system/health", "/metrics"],
        env_var_name="ENABLE_METRICS",
    )
    
    # Instrument the app
    instrumentator.instrument(app)
    print("[OK] Prometheus metrics enabled at /metrics")
except ImportError:
    print("[WARN] prometheus-fastapi-instrumentator not installed, metrics disabled")


# ---------------------------------------------------------------------------
# Sentry — 错误监控
# ---------------------------------------------------------------------------

try:
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    import sentry_sdk
    from app.config import get_settings
    
    settings = get_settings()
    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)
    
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            environment=settings.ENVIRONMENT,
            release=__version__,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        print(f"[OK] Sentry initialized (env: {settings.ENVIRONMENT})")
    else:
        print("[INFO] Sentry DSN not configured, error tracking disabled")
except ImportError:
    print("[WARN] sentry-sdk not installed, error tracking disabled")


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------

from app.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
