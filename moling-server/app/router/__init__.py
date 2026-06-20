"""API routers."""

import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Import and include all sub-routers.
# Import failures are logged at ERROR level — never silently swallowed.

_ROUTER_REGISTRY = [
    ("app.router.auth",            "auth_router",           "/auth",                        ["auth"]),
    ("app.router.project",         "project_router",        "/projects",                    ["projects"]),
    ("app.router.project_health",  "project_health_router",  "/projects",                    ["project-health"]),
    ("app.router.chapter",         "chapter_router",        "/projects/{project_id}",        ["chapters"]),
    ("app.router.card",            "card_router",           "/projects/{project_id}",        ["cards"]),
    ("app.generation.router",      "generation_router",     "/generate",                     ["generation"]),
    ("app.router.generation",      "generation_status_router","/generation",                 ["generation"]),
    ("app.router.vault",           "vault_router",          "/projects/{project_id}/vault",  ["vault"]),
    ("app.router.health",          "health_router",         "/health",                       ["health"]),
    ("app.router.admin",           "admin_router",          "/admin",                        ["admin"]),
    ("app.router.notification",    "notification_router",   "/notifications",                ["notifications"]),
    ("app.router.setting",         "setting_router",        "/settings",                     ["settings"]),
    ("app.router.template",        "template_router",       "/templates",                    ["templates"]),
    ("app.router.phase4",          "phase4_router",         "/phase4",                       ["phase4"]),
    ("app.router.weave",           "weave_router",          "/weave",                        ["weave"]),
    ("app.router.subscription",    "subscription_router",   "/subscriptions",                ["subscriptions"]),
    ("app.ingest.router",          "ingest_router",         "",                              ["import"]),
    ("app.router.genre",           "genre_router",          "/genre",                        ["genre"]),
    ("app.router.secret",          "secret_router",         "/projects/{project_id}/secrets",["secrets"]),
]

_loaded_count = 0
_failed_count = 0

for module_path, attr_name, prefix, tags in _ROUTER_REGISTRY:
    try:
        mod = __import__(module_path, fromlist=[attr_name])
        router = getattr(mod, "router", None)
        if router is None:
            logger.error("Router '%s' loaded but has no 'router' attribute", module_path)
            _failed_count += 1
            continue
        api_router.include_router(router, prefix=prefix, tags=tags)
        _loaded_count += 1
    except ImportError as e:
        logger.error("Failed to load router %s: %s", module_path, e, exc_info=True)
        _failed_count += 1

logger.info(
    "Router loading complete: %d loaded, %d failed",
    _loaded_count, _failed_count,
)

# /system/health 别名，供前端统一调用
@api_router.get("/system/health", tags=["health"])
async def system_health_alias(request: Request):  # FastAPI 自动注入 Request
    """系统健康检查（别名路径，供前端 /system/health 调用）。"""
    from app.router.health import health_check
    return await health_check(request)
