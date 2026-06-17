"""
墨灵 (Moling) — API Key Pool 轮转管理.

实现 Pro Pool (9 Keys) + Flash Pool (6 Keys) 双池管理,
支持 LEAST_USAGE / ROUND_ROBIN 选择策略,
Key 健康度检测 + 指数退避冷却.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NoAvailableKeyError(Exception):
    """当 Pool 中所有 Key 都处于冷却/不健康状态时抛出."""

    def __init__(self, pool: str, message: Optional[str] = None) -> None:
        self.pool = pool
        self.message = message or f"Pool [{pool}] 中没有可用的 API Key"
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Key 健康模型
# ---------------------------------------------------------------------------


@dataclass
class KeyHealth:
    """单个 API Key 的健康状态."""

    key: str
    pool: str  # "pro" | "flash"
    usage_count: int = 0
    consecutive_errors: int = 0
    last_error_at: Optional[datetime] = None
    cooling_until: Optional[datetime] = None  # 冷却到期时间
    backoff_level: int = 0  # 0=正常, 1=30s, 2=60s, 3=120s, 4=300s
    is_healthy: bool = True


# 指数退避时间表（秒）
_BACKOFF_SCHEDULE = [30, 60, 120, 300]


# ---------------------------------------------------------------------------
# KeyManager
# ---------------------------------------------------------------------------


class KeyManager:
    """
    双池 API Key 管理器.

    职责:
    1. 管理 Pro Pool（9 keys） + Flash Pool（6 keys）
    2. 提供 LEAST_USAGE / ROUND_ROBIN 选择策略
    3. 监控 Key 健康度（错误计数 + 冷却状态）
    4. 指数退避冷却（30s→60s→120s→300s）
    5. 自动恢复：冷却期满后重新加入可用池
    """

    def __init__(
        self,
        pro_keys: Optional[List[str]] = None,
        flash_keys: Optional[List[str]] = None,
        strategy: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self._pro_keys: List[str] = pro_keys if pro_keys is not None else settings.LLM_PRO_KEYS
        self._flash_keys: List[str] = flash_keys if flash_keys is not None else settings.LLM_FLASH_KEYS
        self._strategy: str = (strategy or settings.KEY_SELECT_STRATEGY).upper()

        # 健康状态
        self._health: Dict[str, KeyHealth] = {}
        for k in self._pro_keys:
            self._health[k] = KeyHealth(key=k, pool="pro")
        for k in self._flash_keys:
            self._health[k] = KeyHealth(key=k, pool="flash")

        # 轮询游标（每个 Pool 独立）
        self._rr_index: Dict[str, int] = {"pro": 0, "flash": 0}

        # 线程安全
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def select_key(self, pool: str = "pro") -> str:
        """从指定 Pool 中选择一个健康的 Key.

        Args:
            pool: "pro" 或 "flash".

        Returns:
            选中的 Key 字符串.

        Raises:
            NoAvailableKeyError: Pool 中无可用 Key.
        """
        async with self._lock:
            keys = self._get_pool_keys(pool)
            if not keys:
                raise NoAvailableKeyError(pool, f"Pool [{pool}] 为空，没有配置任何 Key")

            # 惰性恢复：检查冷却期是否已过
            now = datetime.now(timezone.utc)
            for key in keys:
                health = self._health[key]
                if not health.is_healthy and health.cooling_until:
                    if now >= health.cooling_until:
                        self._recover_key(health)
                        logger.info("Key %s 冷却期满，已自动恢复", _mask_key(key))

            # 过滤出健康的 Key
            healthy_keys = [k for k in keys if self._health[k].is_healthy]
            if not healthy_keys:
                raise NoAvailableKeyError(pool, f"Pool [{pool}] 所有 Key 均不可用")

            if self._strategy == "ROUND_ROBIN":
                return self._round_robin_select(healthy_keys, pool)
            # LEAST_USAGE（默认）
            return self._least_usage_select(healthy_keys)

    async def report_success(self, key: str) -> None:
        """报告一次成功的调用."""
        async with self._lock:
            health = self._health.get(key)
            if health is None:
                return
            health.consecutive_errors = 0
            health.last_error_at = None
            health.is_healthy = True
            # 成功调用后重置冷却
            health.cooling_until = None
            health.backoff_level = 0

    async def report_error(self, key: str, error_type: str = "other") -> None:
        """报告一次失败的调用.

        - 429 错误：立即冷却并指数退避.
        - 其他错误：累计错误计数，连续 3 次后冷却 300s.
        """
        async with self._lock:
            health = self._health.get(key)
            if health is None:
                return

            health.consecutive_errors += 1
            health.last_error_at = datetime.now(timezone.utc)

            if error_type == "rate_limit" or health.consecutive_errors >= 3:
                self._cool_down(health)
                logger.warning(
                    "Key %s 已冷却 (backoff_level=%d, errors=%d)",
                    _mask_key(key),
                    health.backoff_level,
                    health.consecutive_errors,
                )

    async def get_health(self, key: str) -> Optional[KeyHealth]:
        """获取指定 Key 的健康状态（快照）. """
        async with self._lock:
            h = self._health.get(key)
            if h is None:
                return None
            return KeyHealth(**{**h.__dict__})  # 浅拷贝快照

    async def get_pool_status(self, pool: str) -> Dict[str, object]:
        """获取指定 Pool 的整体状态概览. """
        async with self._lock:
            keys = self._get_pool_keys(pool)
            total = len(keys)
            healthy = sum(1 for k in keys if self._health[k].is_healthy)
            cooling = sum(
                1
                for k in keys
                if not self._health[k].is_healthy
                and self._health[k].cooling_until is not None
            )
            return {
                "pool": pool,
                "total": total,
                "healthy": healthy,
                "cooling": cooling,
                "keys": [
                    {
                        "key": _mask_key(k),
                        "is_healthy": self._health[k].is_healthy,
                        "usage_count": self._health[k].usage_count,
                        "consecutive_errors": self._health[k].consecutive_errors,
                        "backoff_level": self._health[k].backoff_level,
                        "cooling_until": (
                            self._health[k].cooling_until.isoformat()
                            if self._health[k].cooling_until
                            else None
                        ),
                    }
                    for k in keys
                ],
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_pool_keys(self, pool: str) -> List[str]:
        if pool == "pro":
            return self._pro_keys
        elif pool == "flash":
            return self._flash_keys
        raise ValueError(f"Unknown pool: {pool}")

    def _least_usage_select(self, healthy_keys: List[str]) -> str:
        """选择 usage_count 最低的 Key."""
        selected = min(healthy_keys, key=lambda k: self._health[k].usage_count)
        self._health[selected].usage_count += 1
        logger.debug("LEAST_USAGE 选择 Key: %s", _mask_key(selected))
        return selected

    def _round_robin_select(self, healthy_keys: List[str], pool: str) -> str:
        """轮询选择 Key."""
        index = self._rr_index[pool] % len(healthy_keys)
        selected = healthy_keys[index]
        self._rr_index[pool] = (self._rr_index[pool] + 1) % len(healthy_keys)
        self._health[selected].usage_count += 1
        logger.debug("ROUND_ROBIN 选择 Key: %s", _mask_key(selected))
        return selected

    def _cool_down(self, health: KeyHealth) -> None:
        """应用指数退避冷却."""
        level = min(health.backoff_level, len(_BACKOFF_SCHEDULE) - 1)
        duration = _BACKOFF_SCHEDULE[level]
        health.backoff_level = level + 1  # 下次退避升级
        health.cooling_until = datetime.now(timezone.utc) + timedelta(seconds=duration)
        health.is_healthy = False

    def _recover_key(self, health: KeyHealth) -> None:
        """恢复 Key 为健康状态."""
        health.is_healthy = True
        health.cooling_until = None
        # 保持 backoff_level 不变，下次错误会从当前级别继续退避
        logger.info("Key %s 已恢复健康", _mask_key(health.key))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_key(key: str) -> str:
    """脱敏 Key，仅显示前 8 位."""
    return f"{key[:8]}..." if len(key) > 8 else key


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

key_manager = KeyManager()
