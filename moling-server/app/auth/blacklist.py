"""JWT Token Blacklist — 实现 JWT 登出立即失效.

使用 Redis 存储已登出的 token JTI (JWT ID)，实现：
1. 用户登出时，将 token JTI 加入黑名单
2. 验证 token 时，检查是否在黑名单中
3. 利用 Redis TTL 自动过期，避免存储过期数据

S4 fix: Redis 不可用时启用内存后备缓存，避免黑名单完全失效。
"""

from __future__ import annotations

import logging
import time
from threading import Lock

from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Redis 连接（延迟初始化）
# ---------------------------------------------------------------------------

_redis_client = None

# S4 fix: 内存后备缓存 — Redis 不可用时在本地保持最近黑名单的 JTI
_MEMORY_FALLBACK: dict[str, float] = {}  # jti → 过期时间戳 (epoch)
_MEMORY_FALLBACK_MAX = 500               # 最大容量
_MEMORY_FALLBACK_LOCK = Lock()


def _get_redis():
    """获取 Redis 客户端（延迟初始化，失败时返回 None）。"""
    global _redis_client
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
        )
        # 测试连接
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logging.warning(f"Redis 连接失败，黑名单功能禁用: {e}")
        _redis_client = None
        return None


# ---------------------------------------------------------------------------
# 黑名单操作
# ---------------------------------------------------------------------------


def add_to_blacklist(jti: str, expires_in: int) -> bool:
    """
    将 JWT Token 加入黑名单.
    
    Args:
        jti: JWT ID (从 token payload 中获取)
        expires_in: token 剩余有效期（秒），用于设置 Redis key 的 TTL
        
    Returns:
        bool: 是否成功加入黑名单
    """
    expiry = time.time() + expires_in
    redis_ok = False
    
    redis_conn = _get_redis()
    if redis_conn is not None:
        try:
            redis_conn.setex(f"blacklist:{jti}", expires_in, "1")
            redis_ok = True
        except Exception as e:
            logging.error(f"加入 Redis 黑名单失败: {e}")
    
    # S4 fix: 同时写入内存后备缓存
    with _MEMORY_FALLBACK_LOCK:
        _MEMORY_FALLBACK[jti] = expiry
        # 清理过期和超出容量限制的条目
        now = time.time()
        expired = [k for k, v in _MEMORY_FALLBACK.items() if v <= now]
        for k in expired:
            del _MEMORY_FALLBACK[k]
        # 如仍超量，淘汰最旧的
        if len(_MEMORY_FALLBACK) > _MEMORY_FALLBACK_MAX:
            oldest = sorted(_MEMORY_FALLBACK.items(), key=lambda x: x[1])[
                :len(_MEMORY_FALLBACK) - _MEMORY_FALLBACK_MAX
            ]
            for k, _ in oldest:
                del _MEMORY_FALLBACK[k]
    
    return redis_ok


def is_blacklisted(jti: str) -> bool:
    """
    检查 JWT Token 是否在黑名单中.
    
    Args:
        jti: JWT ID
        
    Returns:
        bool: 如果在黑名单中返回 True，否则返回 False
    """
    # 1. 优先查 Redis（权威来源）
    redis_conn = _get_redis()
    if redis_conn is not None:
        try:
            return redis_conn.exists(f"blacklist:{jti}") == 1
        except Exception as e:
            logging.error(f"检查 Redis 黑名单失败: {e}")
            # Redis 查询失败，继续检查后备缓存
    
    # 2. S4 fix: Redis 不可用时使用内存后备缓存
    with _MEMORY_FALLBACK_LOCK:
        expiry = _MEMORY_FALLBACK.get(jti)
        if expiry is not None:
            if time.time() < expiry:
                logging.warning("使用内存黑名单后备缓存阻止 token (jti=%s...)", jti[:8])
                return True
            del _MEMORY_FALLBACK[jti]  # 已过期，清理
    
    return False


def remove_from_blacklist(jti: str) -> bool:
    """
    从黑名单中移除 token (可选，用于管理员撤销封禁等场景).
    
    Args:
        jti: JWT ID
        
    Returns:
        bool: 是否成功移除
    """
    ok = False
    redis_conn = _get_redis()
    if redis_conn is not None:
        try:
            redis_conn.delete(f"blacklist:{jti}")
            ok = True
        except Exception as e:
            logging.error(f"从 Redis 黑名单移除失败: {e}")
    
    with _MEMORY_FALLBACK_LOCK:
        _MEMORY_FALLBACK.pop(jti, None)
    
    return ok
