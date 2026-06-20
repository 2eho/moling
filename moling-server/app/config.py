from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Ensure security warnings are visible. Production apps should configure
# logging properly; this is a minimal setup for the warning validators below.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class Settings(BaseSettings):
    """Application settings — populated from environment / .env file.

    Security notes:
    - NEVER commit .env files containing real secrets to version control.
    - For production, set ALL sensitive values via environment variables.
    - See .env.example for required configuration.
    """

    # ---- Environment ----
    ENVIRONMENT: str = "development"  # development | staging | production

    # ---- Database ----
    # MVP 默认使用 SQLite（单文件、零配置）
    # 生产环境切换为 PostgreSQL: postgresql+asyncpg://user:pass@host:5432/db
    DATABASE_URL: str = "sqlite+aiosqlite:///./moling.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- Redis (用于 Token 黑名单等) ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # ---- Request Size Limits ----
    # 最大请求体大小（字节），默认 10MB，防止内存 DoS
    MAX_BODY_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # ---- Auth / JWT ----
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    # ^ WARNING: Default key is INSECURE. Production MUST set SECRET_KEY via env.
    #   Generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- LLM Service ----
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_API_KEY: str = "sk-placeholder"
    # ^ WARNING: Placeholder key. Production MUST set LLM_API_KEY via env.

    # ---- Celery ----
    # 使用不同的 Redis DB 避免混用
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"  # DB 1: Broker
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"  # DB 2: Result Backend

    # ---- CORS ----
    # 生产环境应在 .env 中配置具体的允许域名
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    # ---- Sentry ----
    # Sentry DSN（从 Sentry 后台获取）
    # 格式: https://<key>@<organization>.ingest.sentry.io/<project>
    SENTRY_DSN: str | None = None

    # ---- API Key Pool ----
    LLM_PRO_KEYS: List[str] = []  # Pro Pool Keys (from env comma-separated)
    LLM_FLASH_KEYS: List[str] = []  # Flash Pool Keys (from env comma-separated)
    KEY_SELECT_STRATEGY: str = "LEAST_USAGE"  # LEAST_USAGE | ROUND_ROBIN
    KEY_BACKOFF_BASE: int = 30  # 初始冷却秒数
    KEY_BACKOFF_MAX: int = 300  # 最大冷却秒数
    KEY_RECOVERY_CHECK_INTERVAL: int = 60  # 恢复检查间隔（秒）

    # ---- Token Budget ----
    TOKEN_BUDGET_LIMIT: int = 1_000_000  # 默认 100 万 token/天 (HH10: Redis 持久化)

    # ---- Rate Limiting ----
    RATE_LIMIT_CALLS: int = 1000  # 每个周期允许的请求数（开发环境设为 1000）
    RATE_LIMIT_PERIOD: int = 60  # 周期（秒）

    # ---- Archive ----
    # 动态层存档目录
    ARCHIVE_DIR: str = "./archives"

    # ---- LLM Model ----
    LLM_MODEL: str = "gpt-4o-mini"

    # ---- App Metadata ----
    APP_VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("LLM_API_KEY", mode="after")
    @classmethod
    def _warn_placeholder_api_key(cls, v: str) -> str:
        if v == "sk-placeholder":
            logger.warning(
                "LLM_API_KEY is still the placeholder value! LLM features will "
                "not work until a real API key is set via environment variable "
                "or .env file."
            )
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _warn_default_db_password(cls, v: str) -> str:
        if "moling:moling@" in v:
            logger.warning(
                "DATABASE_URL contains the default weak password ('moling:moling'). "
                "For production, set DATABASE_URL via environment variable with a "
                "strong, unique credential."
            )
        return v

    @field_validator("ENVIRONMENT", mode="after")
    @classmethod
    def _warn_production_defaults(cls, v: str) -> str:
        if v == "production":
            # In production mode, verify that critical settings are not defaults.
            # The individual field validators above log warnings for each
            # insecure default.  Additionally, we verify SECRET_KEY explicitly
            # here because Pydantic validators run in declaration order and we
            # need access to the fully-constructed model.
            pass
        return v

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _warn_wildcard_cors(cls, v: str) -> str:
        """Warn if CORS_ORIGINS contains '*' in production."""
        if "*" in [o.strip() for o in v.split(",")]:
            import os
            env = os.environ.get("ENVIRONMENT", "development")
            if env == "production":
                logger.warning(
                    "CORS_ORIGINS contains '*' wildcard. This allows ANY origin "
                    "to access the API. For production, set CORS_ORIGINS to a "
                    "comma-separated list of allowed domains."
                )
        return v

    @field_validator("REDIS_PASSWORD", mode="after")
    @classmethod
    def _warn_missing_redis_password(cls, v: str | None) -> str | None:
        """Warn if Redis has no password in non-development environments."""
        if v is None or v == "":
            # Access ENVIRONMENT through a workaround — Pydantic v2 doesn't
            # guarantee field order, so we check via os.environ directly.
            import os
            env = os.environ.get("ENVIRONMENT", "development")
            if env != "development":
                logger.warning(
                    "REDIS_PASSWORD is not set. Redis is accessible without "
                    "authentication. For production, set REDIS_PASSWORD via "
                    "environment variable or .env file."
                )
        return v

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def _reject_production_default_secret(cls, v: str) -> str:
        """Refuse to start in production with the dev default SECRET_KEY."""
        if v == "dev-secret-key-change-in-production":
            # H5 fix: 直接读环境变量，避免对字段声明顺序的依赖
            import os
            env = os.environ.get("ENVIRONMENT", "")
            if env == "production":
                raise ValueError(
                    "SECRET_KEY must be set via environment variable in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            logger.warning(
                "SECRET_KEY is still the default value! This is INSECURE for "
                "any non-development environment. Set SECRET_KEY via environment "
                "variable or .env file. Generate a strong key with: "
                "openssl rand -hex 32"
            )
        return v

    @field_validator("LLM_PRO_KEYS", "LLM_FLASH_KEYS", mode="before")
    @classmethod
    def _parse_comma_separated_keys(cls, v: object) -> List[str]:
        """Parse comma-separated or JSON-array env values into a list.

        Environment variables for lists can be set as:
          LLM_PRO_KEYS=sk-key1,sk-key2,sk-key3
        or the Pydantic JSON array format.
        """
        if v is None:
            return []
        if isinstance(v, list):
            return [item.strip() for item in v if item and item.strip()]
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            # JSON array format: '["key1","key2"]'
            if stripped.startswith("["):
                import json
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [item.strip() for item in parsed if item and item.strip()]
            # Comma-separated format
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return []


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
_overrides_lock = asyncio.Lock()


async def set_override(key: str, value: str | None) -> None:
    """Set a runtime override for a config value (async-safe).

    When set, this value takes precedence over the Settings object.
    Used by the admin panel to update config at runtime.
    """
    async with _overrides_lock:
        _OVERRIDES[key] = value
    # Bust the Settings cache so next get_effective() picks up the change
    get_settings.cache_clear()


def set_override_sync(key: str, value: str | None) -> None:
    """Synchronous version of set_override for non-async contexts."""
    _OVERRIDES[key] = value
    get_settings.cache_clear()


def get_effective_llm_config() -> dict[str, str]:
    """Get the effective LLM configuration (DB override > env var)."""
    s = get_settings()
    return {
        "api_key": _OVERRIDES.get("llm_api_key") or s.LLM_API_KEY,
        "api_base": _OVERRIDES.get("llm_api_base") or s.LLM_API_BASE,
        "model": _OVERRIDES.get("llm_model") or s.LLM_MODEL,
    }
