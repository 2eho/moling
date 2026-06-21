"""API routers."""

import logging
from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Import and include all sub-routers.
# Import failures are logged at ERROR level — never silently swallowed.

_ROUTER_REGISTRY = [
    ("app.router.auth",            "router",  "/auth",                        ["auth"]),
    ("app.router.project",         "router",  "/projects",                    ["projects"]),
    ("app.router.project_health",  "router",  "/projects",                    ["project-health"]),
    ("app.router.chapter",         "router",  "/projects/{project_id}",        ["chapters"]),
    ("app.router.card",            "router",  "/projects/{project_id}",        ["cards"]),
    ("app.router.generation",      "router",  "/generation",                  ["generation"]),
    ("app.router.vault",           "router",  "/projects/{project_id}/vault",  ["vault"]),
    ("app.router.health",          "router",  "/health",                      ["health"]),
    ("app.router.admin",           "admin_router", "/admin",                  ["admin"]),
    ("app.router.notification",    "router",  "/notifications",               ["notifications"]),
    ("app.router.setting",         "router",  "/settings",                    ["settings"]),
    ("app.router.template",        "router",  "/templates",                   ["templates"]),
    ("app.router.phase4",          "router",  "/phase4",                      ["phase4"]),
    ("app.router.weave",           "router",  "/weave",                       ["weave"]),
    ("app.router.subscription",    "router",  "/subscriptions",               ["subscriptions"]),
    ("app.ingest.router",          "router",  "",                             ["import"]),
    ("app.router.genre",           "router",  "/genre",                       ["genre"]),
    ("app.router.secret",          "router",  "/projects/{project_id}/secrets",["secrets"]),
]

_loaded_count = 0
_failed_count = 0

for module_path, attr_name, prefix, tags in _ROUTER_REGISTRY:
    try:
        mod = __import__(module_path, fromlist=[attr_name])
        router = getattr(mod, attr_name, None)
        if router is None:
            logger.error("Router '%s' loaded but has no '%s' attribute", module_path, attr_name)
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
