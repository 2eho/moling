"""
墨灵 (Moling) — Worker Task Idempotency Helpers.

Provides Redis-backed idempotency guards for Celery tasks.  Uses a sync Redis
client (same pattern as ``app.auth.blacklist``) to survive Celery's sync worker
context.

Keys are automatically expired after 24 hours so stale locks never persist.

Usage::

    from app.worker.idempotency import is_duplicate, mark_processing, mark_completed

    task_key = f"imp:{project_id}:import_book_task"

    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    mark_processing(task_key)

    try:
        # ... do work ...
        mark_completed(task_key)
    except Exception:
        mark_failed(task_key)
        raise
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Redis connection (lazy, one per worker process) ──────────────

_redis_client: Optional[object] = None
_redis_unavailable: bool = False


def _get_redis():
    """Get a sync Redis client (lazy init, graceful degradation)."""
    global _redis_client, _redis_unavailable

    if _redis_unavailable:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        import redis

        _redis_client = redis.Redis(
            host=settings.REDIS_HOST or "localhost",
            port=settings.REDIS_PORT or 6379,
            db=settings.REDIS_DB or 0,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _redis_client.ping()
        logger.info("Idempotency Redis connected (host=%s, db=%d)",
                     settings.REDIS_HOST, settings.REDIS_DB)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for idempotency — tasks will NOT be idempotent: %s", exc)
        _redis_unavailable = True
        _redis_client = None
        return None


# ── TTL ──────────────────────────────────────────────────────────

_IDEMPOTENCY_TTL = 86400  # 24 hours — long enough to cover any realistic task


# ── Public API ────────────────────────────────────────────────────

def is_duplicate(task_key: str) -> bool:
    """Return True if *task_key* was already seen (duplicate submission)."""
    r = _get_redis()
    if r is None:
        return False  # Degrade: allow execution when Redis is down

    try:
        # Use SETNX → True means key didn't exist (first time)
        # Mark as "processing" atomically
        acquired = r.set(task_key, "processing", nx=True, ex=_IDEMPOTENCY_TTL)
        return not bool(acquired)
    except Exception as exc:
        logger.warning("Idempotency check failed for %s: %s", task_key, exc)
        return False  # Degrade: allow execution on Redis error


def mark_processing(task_key: str) -> bool:
    """Mark *task_key* as processing (used after is_duplicate check passes)."""
    r = _get_redis()
    if r is None:
        return False

    try:
        return bool(r.set(task_key, "processing", ex=_IDEMPOTENCY_TTL))
    except Exception as exc:
        logger.warning("Idempotency mark_processing failed for %s: %s", task_key, exc)
        return False


def mark_completed(task_key: str) -> bool:
    """Mark *task_key* as completed."""
    r = _get_redis()
    if r is None:
        return False

    try:
        return bool(r.set(task_key, "completed", ex=_IDEMPOTENCY_TTL))
    except Exception as exc:
        logger.warning("Idempotency mark_completed failed for %s: %s", task_key, exc)
        return False


def mark_failed(task_key: str) -> bool:
    """Mark *task_key* as failed (allows retry)."""
    r = _get_redis()
    if r is None:
        return False

    try:
        return bool(r.set(task_key, "failed", ex=_IDEMPOTENCY_TTL))
    except Exception as exc:
        logger.warning("Idempotency mark_failed failed for %s: %s", task_key, exc)
        return False


def clear_task_key(task_key: str) -> bool:
    """Remove *task_key* from Redis (e.g. to allow re-submission)."""
    r = _get_redis()
    if r is None:
        return False

    try:
        r.delete(task_key)
        return True
    except Exception as exc:
        logger.warning("Idempotency clear_task_key failed for %s: %s", task_key, exc)
        return False
