from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — populated from environment / .env file."""

    # ---- Environment ----
    ENVIRONMENT: str = "development"  # development | staging | production

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://moling:moling@localhost:5432/moling"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Auth / JWT ----
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- LLM Service ----
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_API_KEY: str = "sk-placeholder"

    # ---- Celery ----
    # 使用不同的 Redis DB 避免混用
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"  # DB 1: Broker
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"  # DB 2: Result Backend

    # ---- CORS ----
    # 生产环境应在 .env 中配置具体的允许域名
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    # ---- Rate Limiting ----
    RATE_LIMIT_CALLS: int = 1000  # 每个周期允许的请求数（开发环境设为 1000）
    RATE_LIMIT_PERIOD: int = 60  # 周期（秒）

    # ---- Archive ----
    # 动态层存档目录
    ARCHIVE_DIR: str = "./archives"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # 允许环境变量中存在未定义的字段，避免启动错误
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of Settings.

    The `lru_cache` decorator ensures the `.env` file is read only once
    and the Settings object is reused for the lifetime of the process.
    """
    return Settings()


# ---- Database-backed overrides (for admin panel) ----

_OVERRIDES: dict[str, str | None] = {
    "llm_api_key": None,
    "llm_api_base": None,
    "llm_model": None,
}


def set_override(key: str, value: str | None) -> None:
    """Set a runtime override for a config value.

    When set, this value takes precedence over the Settings object.
    Used by the admin panel to update config at runtime.
    """
    _OVERRIDES[key] = value
    # Bust the Settings cache so next get_effective() picks up the change
    get_settings.cache_clear()


def get_effective_llm_config() -> dict[str, str]:
    """Get the effective LLM configuration (DB override > env var)."""
    s = get_settings()
    return {
        "api_key": _OVERRIDES.get("llm_api_key") or s.LLM_API_KEY,
        "api_base": _OVERRIDES.get("llm_api_base") or s.LLM_API_BASE,
        "model": _OVERRIDES.get("llm_model") or "deepseek-chat",
    }
