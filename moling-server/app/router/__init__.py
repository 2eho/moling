"""API routers."""

from fastapi import APIRouter, Request

api_router = APIRouter()

# Import and include all sub-routers
try:
    from app.router.auth import router as auth_router
    api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
except ImportError:
    pass

try:
    from app.router.project import router as project_router
    api_router.include_router(project_router, prefix="/projects", tags=["projects"])
except ImportError:
    pass

try:
    from app.router.project_health import router as project_health_router
    api_router.include_router(project_health_router, prefix="/projects", tags=["project-health"])
except ImportError:
    pass

try:
    from app.router.chapter import router as chapter_router
    api_router.include_router(chapter_router, prefix="/projects/{project_id}", tags=["chapters"])
except ImportError:
    pass

try:
    from app.router.card import router as card_router
    api_router.include_router(card_router, prefix="/projects/{project_id}", tags=["cards"])
except ImportError:
    pass

try:
    from app.generation.router import router as generation_router
    api_router.include_router(generation_router, prefix="/generate", tags=["generation"])
except ImportError as e:
    print(f"[WARN] Generation router not loaded: {e}")
    pass

try:
    from app.router.vault import router as vault_router
    api_router.include_router(vault_router, prefix="/projects/{project_id}/vault", tags=["vault"])
except ImportError:
    pass

try:
    from app.router.health import router as health_router
    api_router.include_router(health_router, prefix="/health", tags=["health"])
except ImportError:
    pass

# /system/health 别名，供前端统一调用
@api_router.get("/system/health", tags=["health"])
async def system_health_alias(request: Request):  # FastAPI 自动注入 Request
    """系统健康检查（别名路径，供前端 /system/health 调用）。"""
    from app.router.health import health_check
    return await health_check(request)

try:
    from app.router.admin import router as admin_router
    api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
except ImportError:
    pass

try:
    from app.router.notification import router as notification_router
    api_router.include_router(notification_router, prefix="/notifications", tags=["notifications"])
except ImportError:
    pass

try:
    from app.router.setting import router as setting_router
    api_router.include_router(setting_router, prefix="/settings", tags=["settings"])
except ImportError:
    pass

try:
    from app.router.template import router as template_router
    api_router.include_router(template_router, prefix="/templates", tags=["templates"])
except ImportError:
    pass

try:
    from app.router.phase4 import router as phase4_router
    api_router.include_router(phase4_router, prefix="/phase4", tags=["phase4"])
except ImportError:
    pass

try:
    from app.router.weave import router as weave_router
    api_router.include_router(weave_router, prefix="/weave", tags=["weave"])
except ImportError:
    pass

try:
    from app.router.subscription import router as subscription_router
    api_router.include_router(subscription_router, prefix="/subscriptions", tags=["subscriptions"])
except ImportError:
    pass

try:
    from app.ingest.router import router as ingest_router
    api_router.include_router(ingest_router, tags=["import"])
except ImportError:
    pass

try:
    from app.router.genre import router as genre_router
    api_router.include_router(genre_router, prefix="/genre", tags=["genre"])
except ImportError:
    pass

try:
    from app.router.secret import router as secret_router
    api_router.include_router(secret_router, prefix="/projects/{project_id}/secrets", tags=["secrets"])
except ImportError:
    pass
