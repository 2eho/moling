"""Phase 4 Store — dual-mode Redis / memory backend.

Provides a unified interface for nonce tracking, distributed locking,
and task state storage.  When Redis is available the store uses it
for durability and cross-worker coordination; when Redis is absent
it falls back to in-memory dicts (suitable for single-worker dev).

Implements the contracts described in §12.5 of the algorithm doc:
- Nonce deduplication (SISMEMBER / set lookup)
- Distributed locking (SET NX EX / dict+asyncio.Lock)
- Task state persistence (HSET / dict)
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# In-memory fallback (used when Redis is unavailable)
# ---------------------------------------------------------------------------

class _MemoryStore:
    """Thread-safe in-memory store backing the same interface as Redis."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._nonce_set: Set[str] = set()
        self._nonce_cache: OrderedDict[str, bool] = OrderedDict()
        self._locks: Dict[str, str] = {}       # resource_key → owner_id
        self._tasks: Dict[str, Dict[str, Any]] = {}

    async def sismember(self, key: str, member: str) -> bool:
        async with self._lock:
            if member in self._nonce_cache:
                return self._nonce_cache[member]
            present = member in self._nonce_set
            self._nonce_cache[member] = present
            if len(self._nonce_cache) > 1000:
                self._nonce_cache.popitem(last=False)
            return present

    async def sadd(self, key: str, member: str) -> bool:
        async with self._lock:
            was_new = member not in self._nonce_set
            self._nonce_set.add(member)
            self._nonce_cache[member] = True
            return was_new

    async def setnx_ex(self, lock_key: str, owner_id: str, ttl: int = 30) -> bool:
        """Atomically set *lock_key* to *owner_id* if not already held."""
        async with self._lock:
            if lock_key in self._locks:
                return False
            self._locks[lock_key] = owner_id
            return True

    async def get_lock_owner(self, lock_key: str) -> Optional[str]:
        async with self._lock:
            return self._locks.get(lock_key)

    async def release_lock(self, lock_key: str) -> None:
        async with self._lock:
            self._locks.pop(lock_key, None)

    async def hset_task(self, task_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            self._tasks[task_id] = data

    async def hget_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._tasks.get(task_id)


# ---------------------------------------------------------------------------
# Redis-backed store
# ---------------------------------------------------------------------------

class _RedisStore:
    """Redis-backed store using the application's shared Redis connection."""

    _NONCE_PREFIX = "phase4:nonces"
    _LOCK_PREFIX = "phase4:lock"
    _TASK_PREFIX = "phase4:task"

    def __init__(self, redis) -> None:
        self._redis = redis

    async def sismember(self, key: str, member: str) -> bool:
        return bool(await self._redis.sismember(key, member))

    async def sadd(self, key: str, member: str) -> bool:
        return bool(await self._redis.sadd(key, member))

    async def setnx_ex(self, lock_key: str, owner_id: str, ttl: int = 30) -> bool:
        return bool(await self._redis.set(lock_key, owner_id, nx=True, ex=ttl))

    async def get_lock_owner(self, lock_key: str) -> Optional[str]:
        val = await self._redis.get(lock_key)
        return val.decode("utf-8") if val else None

    async def release_lock(self, lock_key: str) -> None:
        await self._redis.delete(lock_key)

    async def hset_task(self, task_id: str, data: Dict[str, Any]) -> None:
        import json
        await self._redis.set(
            f"{self._TASK_PREFIX}:{task_id}",
            json.dumps(data, default=str),
            ex=3600,  # TTL 1 hour
        )

    async def hget_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        import json
        val = await self._redis.get(f"{self._TASK_PREFIX}:{task_id}")
        if val:
            return json.loads(val.decode("utf-8") if isinstance(val, bytes) else val)
        return None


# ---------------------------------------------------------------------------
# Unified backend
# ---------------------------------------------------------------------------

class Phase4Store:
    """Dual-mode store: Redis if available, otherwise in-memory.

    Usage from Phase4Scheduler::

        store = Phase4Store()
        await store.init(redis)       # redis = None → memory mode
        await store.check_nonce(...)
    """

    def __init__(self) -> None:
        self._backend: _MemoryStore | _RedisStore = _MemoryStore()
        self._use_redis = False

    async def init(self, redis) -> None:
        """Initialise the store; pass *redis* client or None for memory mode."""
        if redis is not None:
            try:
                await redis.ping()
                self._backend = _RedisStore(redis)
                self._use_redis = True
                logger.info("Phase4Store: using Redis backend")
            except Exception:
                logger.warning("Phase4Store: Redis ping failed, using memory backend")
        else:
            logger.info("Phase4Store: Redis not available, using memory backend")

    @property
    def backend_type(self) -> str:
        return "redis" if self._use_redis else "memory"

    # -- nonce -----------------------------------------------------------------

    async def check_nonce(self, nonce: str) -> bool:
        """Return True if *nonce* was already seen (deduplication)."""
        return await self._backend.sismember("phase4:nonces", nonce)

    async def record_nonce(self, nonce: str) -> bool:
        """Record *nonce*; returns True if it was new."""
        return await self._backend.sadd("phase4:nonces", nonce)

    # -- lock ------------------------------------------------------------------

    async def acquire_lock(self, resource: str, owner_id: str, ttl: int = 30) -> bool:
        lock_key = f"phase4:lock:{resource}"
        return await self._backend.setnx_ex(lock_key, owner_id, ttl)

    async def get_lock_owner(self, resource: str) -> Optional[str]:
        return await self._backend.get_lock_owner(f"phase4:lock:{resource}")

    async def release_lock(self, resource: str) -> None:
        await self._backend.release_lock(f"phase4:lock:{resource}")

    # -- task ------------------------------------------------------------------

    async def save_task(self, task_id: str, data: Dict[str, Any]) -> None:
        await self._backend.hset_task(task_id, data)

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await self._backend.hget_task(task_id)
