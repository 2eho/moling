"""Content-Length Limit Middleware — 防止大请求体内存 DoS 攻击.

在请求到达路由之前根据 Content-Length 头拦截超大请求，
返回 413 Request Entity Too Large，避免路由层解析整个 body 后再拒绝。
"""

from __future__ import annotations

import json
import time
from typing import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 默认最大请求体大小: 10MB
DEFAULT_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


class ContentLengthLimitMiddleware:
    """ASGI 中间件：根据 Content-Length 头限制请求体大小.

    特点：
    - ASGI 级别拦截，覆盖所有路由（包括 multipart 上传、JSON body 等）
    - 返回 413 并在 meta 中指明限制值，便于前端展示友好提示
    - 跳过没有 Content-Length 的请求（如 GET），由下游自行处理
    """

    def __init__(
        self,
        app: ASGIApp,
        max_size: int = DEFAULT_MAX_SIZE,
        excluded_paths: tuple[str, ...] | None = None,
    ) -> None:
        self.app = app
        self.max_size = max_size
        self.excluded_paths = excluded_paths or ()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 提取 Content-Length
        headers = dict(scope.get("headers", []))
        content_length_raw = headers.get(b"content-length")

        if content_length_raw is not None:
            try:
                content_length = int(content_length_raw.decode("ascii"))
            except (ValueError, UnicodeDecodeError):
                # 非法的 Content-Length 值，拒绝请求
                await self._send_413(send, "Invalid Content-Length header")
                return

            if content_length > self.max_size:
                # 检查是否在排除列表中
                path = scope.get("path", "")
                if not any(path.startswith(ep) for ep in self.excluded_paths):
                    await self._send_413(send, content_length)
                    return

        await self.app(scope, receive, send)

    async def _send_413(self, send: Send, actual_or_msg: int | str) -> None:
        """发送 413 Request Entity Too Large 响应。"""
        if isinstance(actual_or_msg, int):
            detail = (
                f"Request body too large. "
                f"Max: {self.max_size} bytes, "
                f"received Content-Length: {actual_or_msg} bytes."
            )
        else:
            detail = str(actual_or_msg)

        body_data = {
            "code": 41301,
            "message": detail,
            "data": None,
            "meta": {
                "request_id": "",
                "timestamp": int(time.time() * 1000),
                "version": "1.0.0",
                "max_size": self.max_size,
            },
        }
        body_bytes = json.dumps(body_data, ensure_ascii=False).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body_bytes)).encode("ascii")),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body_bytes,
        })
