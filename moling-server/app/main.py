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
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

settings = get_settings()

# 初始化 slowapi limiter（用于端点级速率限制）
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter

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

# 2.5 SlowAPI Middleware — 支持端点级速率限制装饰器
app.add_middleware(SlowAPIMiddleware)

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
    """Translate any ``AppError`` subclass into the unified error envelope.

    Logs to moling_errors.log for auditability and debugging.
    """
    _write_error_log(request, exc)

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


def _write_error_log(request: Request, exc: Exception) -> None:
    """写入增强的错误日志，包含请求体、用户 ID、日志轮转。

    日志文件 moling_errors.log 超过 10MB 自动备份为 moling_errors.log.1。
    """
    import traceback
    import os
    from pathlib import Path

    log_path = Path("moling_errors.log")

    # ---- 日志轮转：超过 10MB 自动备份 ----
    try:
        if log_path.exists() and log_path.stat().st_size > 10 * 1024 * 1024:
            backup_path = Path("moling_errors.log.1")
            if backup_path.exists():
                backup_path.unlink()
            log_path.rename(backup_path)
    except Exception:
        pass

    # ---- 构建增强日志内容 ----
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"[{__import__('datetime').datetime.now()}]")
    lines.append(f"  Method: {request.method}")
    lines.append(f"  Path: {request.url.path}")
    lines.append(f"  Query: {str(request.query_params)}")

    # 用户 ID
    try:
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            # 尝试从 JWT token 提取
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                from jose import jwt
                from app.config import get_settings
                s = get_settings()
                payload = jwt.decode(token, s.SECRET_KEY, algorithms=[s.ALGORITHM],
                                     options={"verify_exp": False})
                user_id = payload.get("sub", "unknown")
            else:
                user_id = "anonymous"
        lines.append(f"  User: {user_id}")
    except Exception:
        lines.append(f"  User: unknown")

    # 请求体（截断超过 2000 字符的内容）
    try:
        body = getattr(request.state, "body", None)
        if body is None:
            # 无法获取已消费的请求体，记录客户端 IP 作为替代
            client_ip = request.client.host if request.client else "unknown"
            lines.append(f"  Client IP: {client_ip}")
        else:
            body_str = str(body)
            if len(body_str) > 2000:
                body_str = body_str[:2000] + f"... [truncated, total {len(body_str)} chars]"
            lines.append(f"  Body: {body_str}")
    except Exception:
        lines.append(f"  Body: <unavailable>")

    # 客户端 IP
    try:
        if request.client:
            lines.append(f"  Client IP: {request.client.host}")
    except Exception:
        pass

    # 请求头（只记录关键头，不含敏感信息）
    try:
        safe_headers = {}
        for key in ["user-agent", "content-type", "x-forwarded-for", "referer"]:
            val = request.headers.get(key)
            if val:
                safe_headers[key] = val
        if safe_headers:
            lines.append(f"  Headers: {safe_headers}")
    except Exception:
        pass

    # Traceback
    lines.append(traceback.format_exc())

    # ---- 写入日志文件 ----
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak internals."""
    import traceback
    traceback.print_exc()
    _write_error_log(request, exc)

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
# Sentry — 错误监控和性能监控
# ---------------------------------------------------------------------------

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from app.config import get_settings
    
    settings = get_settings()
    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)
    
    if sentry_dsn:
        # 根据环境设置采样率
        # 生产环境建议 0.2，开发环境可以设为 1.0
        if settings.ENVIRONMENT == "production":
            traces_sample_rate = 0.2
            profiles_sample_rate = 0.2
        else:
            traces_sample_rate = 1.0
            profiles_sample_rate = 1.0
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            environment=settings.ENVIRONMENT,
            release=f"moling@{__version__}",
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=True,  # 捕获用户 IP 等基本信息
        )
        print(f"[OK] Sentry initialized (env: {settings.ENVIRONMENT}, traces: {traces_sample_rate})")
    else:
        print("[INFO] Sentry DSN not configured, error tracking disabled")
except ImportError:
    print("[WARN] sentry-sdk not installed, error tracking disabled")


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------

from app.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# OpenAPI 规范自动保存（开发模式下）
# ---------------------------------------------------------------------------

def _save_openapi_schema():
    """保存 OpenAPI 规范到静态文件（开发模式下）"""
    from app.config import get_settings
    settings = get_settings()
    
    if settings.ENVIRONMENT != "production":
        import json
        from pathlib import Path
        
        # 保存到项目根目录
        output_path = Path(__file__).resolve().parent.parent.parent / "openapi.json"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
            print(f"[OK] OpenAPI 规范已保存到：{output_path}")
        except Exception as e:
            print(f"[WARN] 保存 OpenAPI 规范失败：{e}")


# 在应用启动时保存 OpenAPI 规范
_save_openapi_schema()

