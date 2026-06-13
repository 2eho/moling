"""墨灵 (Moling) — Global Dependency Injection.

Provides FastAPI dependency callables for:
- Database sessions (async SQLAlchemy)
- Redis connections
- Current authenticated user (required / optional)
- Service instances (via Depends)
"""

from __future__ import annotations

import asyncio
import platform
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, Callable, Optional

# ---------------------------------------------------------------------------
# Windows: patch greenlet BEFORE importing SQLAlchemy
# ---------------------------------------------------------------------------
if platform.system() == "Windows":
    print("[DEBUG] Applying Windows greenlet patch...", file=sys.stderr)
    
    _executor = ThreadPoolExecutor(max_workers=4)

    async def _patched_greenlet_spawn(fn, *args, **kwargs):
        """Run sync callable in a thread."""
        loop = asyncio.get_running_loop()
        if kwargs:
            def wrapper():
                return fn(*args, **kwargs)
            return await loop.run_in_executor(_executor, wrapper)
        else:
            return await loop.run_in_executor(_executor, fn, *args)

    # Patch SQLAlchemy's concurrency module BEFORE it's imported
    # This ensures that when SQLAlchemy imports greenlet_spawn, it gets our version
    import sqlalchemy.util.concurrency as _conc
    _conc.have_greenlet = True
    _conc.greenlet_error = None
    _conc.greenlet_spawn = _patched_greenlet_spawn

    print("[DEBUG] Patch applied to sqlalchemy.util.concurrency", file=sys.stderr)

# ---------------------------------------------------------------------------
# Now safe to import SQLAlchemy and other modules
# ---------------------------------------------------------------------------

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Windows: also patch already-loaded SQLAlchemy modules
# ---------------------------------------------------------------------------
if platform.system() == "Windows":
    import sqlalchemy.ext.asyncio.engine as _ae
    import sqlalchemy.ext.asyncio.base as _ab
    import sqlalchemy.ext.asyncio.session as _as

    _ae.greenlet_spawn = _patched_greenlet_spawn
    _ab.greenlet_spawn = _patched_greenlet_spawn
    _as.greenlet_spawn = _patched_greenlet_spawn
    
    print("[DEBUG] Patch applied to SQLAlchemy async modules", file=sys.stderr)

from app.config import get_settings
from app.service.auth_service import AuthService
from app.service.project_service import ProjectService
from app.service.chapter_service import ChapterService
from app.service.generation_service import GenerationService
from app.service.vault_service import VaultService
from app.service.secret_service import SecretService

settings = get_settings()

# ---------------------------------------------------------------------------
# Database — Windows + SQLite 使用 aiosqlite
# ---------------------------------------------------------------------------


def _get_db_url() -> str:
    """返回适配当前平台的数据库 URL。

    Windows 上使用 SQLite 时，强制使用 aiosqlite 驱动
    （纯 Python 实现，不需要 greenlet）。
    """
    url = settings.DATABASE_URL
    if platform.system() == "Windows" and url.startswith("sqlite"):
        if "aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


engine = create_async_engine(
    _get_db_url(),
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session.

    The session is automatically committed on success and rolled back on
    any exception.  The underlying connection is returned to the pool on
    context exit.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a singleton Redis connection (or None if unavailable)."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            # Verify connectivity
            await _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

oauth2_scheme = HTTPBearer(auto_error=True)
oauth2_scheme_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> dict:
    """Decode the JWT access token and return the authenticated user claims.

    Raises ``401`` if the token is missing, malformed, or expired.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
            )
        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "username": payload.get("username", ""),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        oauth2_scheme_optional
    ),
) -> dict | None:
    """Like ``get_current_user`` but returns ``None`` when no token is supplied.

    Useful for endpoints that behave differently for authenticated vs.
    anonymous users (e.g. public project listing).
    """
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "username": payload.get("username", ""),
        }
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Service Dependencies — inject via Depends()
# ---------------------------------------------------------------------------


def get_auth_service() -> AuthService:
    """Return an AuthService instance.

    Uses a module-level singleton for efficiency (AuthService is stateless).
    Override this dependency in tests to inject a mock.
    """
    return AuthService()


def get_project_service() -> ProjectService:
    """Return a ProjectService instance."""
    return ProjectService()


def get_chapter_service() -> ChapterService:
    """Return a ChapterService instance."""
    return ChapterService()


def get_generation_service() -> GenerationService:
    """Return a GenerationService instance."""
    return GenerationService()


def get_vault_service() -> VaultService:
    """Return a VaultService instance."""
    return VaultService()


def get_secret_service() -> SecretService:
    """Return a SecretService instance."""
    return SecretService()
