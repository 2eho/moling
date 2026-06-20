"""墨灵 (Moling) — Unified Worker Database Session Management.

Provides a single, canonical way for Celery workers to obtain database
sessions.  All six worker modules MUST use this module instead of creating
their own engines / session factories.

Usage::

    from app.worker.db import get_worker_session

    async with get_worker_session() as db:
        # do work with `db` (an AsyncSession)
        await db.commit()

The session is automatically committed on success, rolled back on exception,
and closed in all cases.  The underlying engine is disposed at worker shutdown
via the ``worker_shutdown`` Celery signal.
"""

from __future__ import annotations

import asyncio
import logging
import platform
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine & session factory (lazy, created once per worker process)
# ---------------------------------------------------------------------------

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_db_url() -> str:
    """Return the platform-appropriate async database URL."""
    settings = get_settings()
    url = settings.DATABASE_URL
    # Windows + SQLite → aiosqlite driver
    if platform.system() == "Windows" and url.startswith("sqlite"):
        if "aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    # PostgreSQL → prefer psycopg (both async and sync)
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return url


def _ensure_engine() -> async_sessionmaker[AsyncSession]:
    """Lazily build the engine and session factory (one per worker process)."""
    global _engine, _session_factory

    if _session_factory is not None:
        return _session_factory

    url = _get_db_url()
    pool_size = 2  # Workers are single-threaded; keep pool small

    _engine = create_async_engine(
        url,
        echo=False,
        pool_size=pool_size,
        max_overflow=5,
        pool_pre_ping=True,  # Detect stale connections
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    logger.info("Worker engine created (pool=%d, url=%s)", pool_size, url[:40])
    return _session_factory


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_worker_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager yielding a transactional :class:`AsyncSession`.

    On exit the session is committed (success) or rolled back (exception),
    then closed.  The underlying connection is returned to the pool — the
    engine itself is disposed only at worker shutdown.
    """
    factory = _ensure_engine()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def dispose_worker_engine() -> None:
    """Dispose the worker engine (called at Celery worker shutdown).

    This is registered via the ``worker_shutdown`` signal so connections
    and the connection pool are properly released.
    """
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Disposing worker engine…")
        # The Celery worker runs in a sync context, so use asyncio.run
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_engine.dispose())
            else:
                asyncio.run(_engine.dispose())
        except RuntimeError:
            asyncio.run(_engine.dispose())
        _engine = None
        _session_factory = None


# ---------------------------------------------------------------------------
# Celery signal handlers
# ---------------------------------------------------------------------------

try:
    from celery.signals import worker_shutdown

    @worker_shutdown.connect
    def _on_worker_shutdown(**kwargs):
        dispose_worker_engine()

except ImportError:
    logger.debug("Celery signals unavailable; engine will leak on shutdown")
