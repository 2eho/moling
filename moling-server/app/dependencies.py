"""墨灵 (Moling) — Global Dependency Injection.

Provides FastAPI dependency callables for:
- Database sessions (async SQLAlchemy)
- Redis connections
- Current authenticated user (required / optional)
- Service instances (via Depends)
"""

from __future__ import annotations

import platform

# ---------------------------------------------------------------------------
# Windows greenlet 猴子补丁 — 必须在所有 SQLAlchemy 导入之前执行
# ---------------------------------------------------------------------------
if platform.system() == "Windows":
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    _executor = ThreadPoolExecutor(max_workers=4)

    def _asyncio_greenlet_spawn(fn, *args, **kwargs):
        """用线程池替代 greenlet，返回可 await 的 Future。"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            _executor,
            lambda: fn(*args, **kwargs),
        )

    # 补丁：sqlalchemy.util.concurrency
    import sqlalchemy.util.concurrency as _conc
    _conc.greenlet_spawn = _asyncio_greenlet_spawn
    _conc._not_implemented = lambda: None

    # 补丁：sqlalchemy.ext.asyncio.base 中的 _greenlet_spawn
    try:
        import sqlalchemy.ext.asyncio.base as _async_base
        _async_base._greenlet_spawn = _asyncio_greenlet_spawn
    except Exception:
        pass

    print("[OK] Applied Windows greenlet patch (thread pool fallback)")

# ---------------------------------------------------------------------------
# Windows 事件系统补丁 — 修复 _get_exec_once_mutex 返回 None 的问题
# ---------------------------------------------------------------------------
if platform.system() == "Windows":
    import contextlib
    import sqlalchemy.event.attr as _event_attr

    def _patched_get_exec_once_mutex():
        """返回可用的上下文管理器，替代 None。"""
        return contextlib.nullcontext()

    # 修补所有包含 _get_exec_once_mutex 的类
    _patched_classes = 0
    for _name in dir(_event_attr):
        _obj = getattr(_event_attr, _name, None)
        if isinstance(_obj, type) and hasattr(_obj, '_get_exec_once_mutex'):
            try:
                setattr(_obj, '_get_exec_once_mutex', staticmethod(_patched_get_exec_once_mutex))
                _patched_classes += 1
            except Exception:
                pass

    # 同时修补所有已有实例（如果有）
    # 遍历 sqlalchemy.event.registry 中的实例...
    print(f"[OK] Patched _get_exec_once_mutex on {_patched_classes} class(es)")

# ---------------------------------------------------------------------------
# 正式导入
# ---------------------------------------------------------------------------

from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Database — Windows + SQLite 使用 aiosqlite（无需 greenlet）
# ---------------------------------------------------------------------------


def _get_db_url() -> str:
    """返回适配当前平台的数据库 URL。

    - Windows + SQLite：强制使用 aiosqlite 驱动
    - PostgreSQL：异步和同步引擎都使用 psycopg 3.x
      （psycopg 原生支持异步，不依赖 greenlet）
    """
    url = settings.DATABASE_URL
    # PostgreSQL：强制使用 psycopg 驱动（异步/同步均支持）
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return url


# 对于 SQLite，使用 NullPool 避免线程池问题
_db_url = _get_db_url()
_is_sqlite = _db_url.startswith("sqlite+aiosqlite")

if _is_sqlite:
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        _db_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        _db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# ---------------------------------------------------------------------------
# 同步引擎（Windows 上 auth 等操作使用，完全避开 greenlet）
# 注意：PostgreSQL 同步引擎必须用 psycopg2/psycopg 驱动，不能用 asyncpg
# ---------------------------------------------------------------------------

_sync_url = settings.DATABASE_URL
if _sync_url.startswith("postgresql"):
    # PostgreSQL 同步引擎：把 asyncpg 换成 psycopg (psycopg3)
    _sync_url = _sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif _sync_url.startswith("sqlite"):
    _sync_url = _sync_url.replace("sqlite+aiosqlite://", "sqlite://")

_sync_engine = create_engine(_sync_url, echo=False)
_sync_session_factory = sessionmaker(bind=_sync_engine, expire_on_commit=False)


def get_sync_db() -> Generator["Session", None, None]:
    """提供同步数据库会话（用于 Windows 上避开 async + greenlet 问题）。"""
    with _sync_session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class _SyncAsyncSessionWrapper:
    """将同步 SQLAlchemy Session 包装为可 await 的伪异步 Session。

    Windows 上 aiosqlite + greenlet 存在兼容问题，此类用线程池
    执行同步操作，让上层 async/await 代码无需修改。
    """

    def __init__(self, sync_session: Session):
        self._sync = sync_session

    def __getattr__(self, name: str):
        """代理所有属性访问到内部同步 session。"""
        return getattr(self._sync, name)

    async def commit(self):
        from asyncio import get_event_loop
        loop = get_event_loop()
        await loop.run_in_executor(None, self._sync.commit)

    async def rollback(self):
        from asyncio import get_event_loop
        loop = get_event_loop()
        await loop.run_in_executor(None, self._sync.rollback)

    async def close(self):
        from asyncio import get_event_loop
        loop = get_event_loop()
        await loop.run_in_executor(None, self._sync.close)

    async def refresh(self, instance, attribute_names=None):
        from asyncio import get_event_loop
        loop = get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._sync.refresh(instance, attribute_names),
        )

    async def execute(self, *args, **kwargs):
        from asyncio import get_event_loop
        loop = get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync.execute(*args, **kwargs),
        )

    async def flush(self, *args, **kwargs):
        from asyncio import get_event_loop
        loop = get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync.flush(*args, **kwargs),
        )

    def add(self, instance):
        self._sync.add(instance)

    def add_all(self, instances):
        self._sync.add_all(instances)

    async def delete(self, instance):
        from asyncio import get_event_loop
        loop = get_event_loop()
        await loop.run_in_executor(None, lambda: self._sync.delete(instance))

    async def merge(self, instance):
        from asyncio import get_event_loop
        loop = get_event_loop()
        return await loop.run_in_executor(None, lambda: self._sync.merge(instance))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session.

    The session is automatically committed on success and rolled back on
    error. Always closes the session in the ``finally`` block.

    Windows: 使用同步 session + 线程池包装，避开 aiosqlite greenlet 问题。
    """
    if platform.system() == "Windows" and _is_sqlite:
        with _sync_session_factory() as session:
            wrapped = _SyncAsyncSessionWrapper(session)
            try:
                yield wrapped  # type: ignore[misc]
                await wrapped.commit()
            except Exception:
                await wrapped.rollback()
                raise
            finally:
                await wrapped.close()
    else:
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
# Redis — used for rate limiting, session cache, and card pool state
# ---------------------------------------------------------------------------

async def get_redis() -> aioredis.Redis:
    """Return a Redis connection client (singleton per app)."""
    r = await aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3,
    )
    return r


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------

_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    db: Session = Depends(get_sync_db),
):
    """Extract and validate the JWT, returning the authenticated user.

    Raises 401 if the token is missing, expired, invalid, or blacklisted.
    NOTE: Uses sync DB to avoid Windows + aiosqlite greenlet issues.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti is not None:
        from app.auth.blacklist import is_blacklisted
        
        if is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.dao.user_dao import UserDAO
    from app.schemas.auth import UserResp
    dao = UserDAO()
    # Use sync get to avoid Windows greenlet+aiosqlite issues
    user = dao.get_sync(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResp.model_validate(user)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    db: Session = Depends(get_sync_db),
):
    """Like ``get_current_user()`` but returns ``None`` instead of 401."""
    if credentials is None:
        return None

    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
