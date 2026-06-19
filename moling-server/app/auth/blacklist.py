"""JWT Token Blacklist — 实现 JWT 登出立即失效.

使用 Redis 存储已登出的 token JTI (JWT ID)，实现：
1. 用户登出时，将 token JTI 加入黑名单
2. 验证 token 时，检查是否在黑名单中
3. 利用 Redis TTL 自动过期，避免存储过期数据

Fallback: 如果 Redis 不可用，则跳过黑名单检查（降级处理）。
"""

from __future__ import annotations

import logging

from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Redis 连接（延迟初始化）
# ---------------------------------------------------------------------------

_redis_client = None


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
    redis_conn = _get_redis()
    if redis_conn is None:
        logging.warning("Redis 不可用，跳过黑名单操作")
        return False
    
    try:
        # 使用 setex 设置带 TTL 的 key
        # key 格式: blacklist:{jti}
        # value: "1" (任意非空值)
        # TTL: expires_in 秒
        redis_conn.setex(f"blacklist:{jti}", expires_in, "1")
        return True
    except Exception as e:
        logging.error(f"加入黑名单失败: {e}")
        return False


def is_blacklisted(jti: str) -> bool:
    """
    检查 JWT Token 是否在黑名单中.
    
    Args:
        jti: JWT ID
        
    Returns:
        bool: 如果在黑名单中返回 True，否则返回 False
               如果 Redis 不可用，返回 False（降级处理）
    """
    redis_conn = _get_redis()
    if redis_conn is None:
        # Redis 不可用，降级处理：不阻止请求
        return False
    
    try:
        # 检查 key 是否存在
        return redis_conn.exists(f"blacklist:{jti}") == 1
    except Exception as e:
        logging.error(f"检查黑名单失败: {e}")
        # 检查时失败，降级处理：不阻止请求
        return False


def remove_from_blacklist(jti: str) -> bool:
    """
    从黑名单中移除 token (可选，用于管理员撤销封禁等场景).
    
    Args:
        jti: JWT ID
        
    Returns:
        bool: 是否成功移除
    """
    redis_conn = _get_redis()
    if redis_conn is None:
        return False
    
    try:
        redis_conn.delete(f"blacklist:{jti}")
        return True
    except Exception as e:
        logging.error(f"从黑名单移除失败: {e}")
        return False
