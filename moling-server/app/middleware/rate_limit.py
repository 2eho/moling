"""Rate Limit Middleware — API 请求频率限制."""

from __future__ import annotations

import json
import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.errors import ErrorCode


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的基于内存的速率限制中间件.

    注意: 生产环境应使用 Redis 实现分布式速率限制.
    """

    def __init__(
        self,
        app,
        calls: int = 100,
        period: int = 60,
        by_ip: bool = True,
    ):
        """
        Args:
            calls: 在指定时间段内允许的请求次数
            period: 时间段（秒）
            by_ip: 是否按 IP 地址限制（否则按用户 ID）
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.by_ip = by_ip
        self._visitors: dict[str, list[float]] = {}
        self._last_cleanup: float = time.time()
        self._cleanup_interval: int = 300  # 每 5 分钟清理一次过期记录

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取访问者标识
        identifier = self._get_identifier(request)

        # 检查速率限制
        if not self._is_allowed(identifier):
            return Response(
                content=json.dumps({
                    "code": ErrorCode.RATE_LIMIT_EXCEEDED.value,
                    "message": ErrorCode.RATE_LIMIT_EXCEEDED.message,
                    "data": None,
                }),
                status_code=429,
                media_type="application/json",
            )

        # 记录请求
        self._record_request(identifier)

        # 处理请求
        response = await call_next(request)
        return response

    def _get_identifier(self, request: Request) -> str:
        """获取访问者标识."""
        if self.by_ip:
            # 尝试获取真实 IP（考虑代理）
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.client.host if request.client else "unknown"
        else:
            # 按用户 ID（需要从 token 中解析，这里简化为 IP）
            return request.client.host if request.client else "unknown"

    def _is_allowed(self, identifier: str) -> bool:
        """检查是否允许请求."""
        now = time.time()

        # 定时清理：清除超过 period * 2 未活跃的访问者记录，防止内存泄漏
        self._cleanup_stale_visitors(now)

        # 清理当前访问者的过期记录
        if identifier in self._visitors:
            self._visitors[identifier] = [
                t for t in self._visitors[identifier] if now - t < self.period
            ]

        # 检查请求次数
        if identifier not in self._visitors:
            return True

        return len(self._visitors[identifier]) < self.calls

    def _cleanup_stale_visitors(self, now: float) -> None:
        """清理超过 period * 2 未活跃的访问者记录，防止 _visitors dict 无限增长."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now

        threshold = self.period * 2
        stale = [
            ident
            for ident, timestamps in self._visitors.items()
            if not timestamps or now - max(timestamps) > threshold
        ]
        for ident in stale:
            del self._visitors[ident]

    def _record_request(self, identifier: str) -> None:
        """记录请求时间戳."""
        now = time.time()
        if identifier not in self._visitors:
            self._visitors[identifier] = []
        self._visitors[identifier].append(now)
