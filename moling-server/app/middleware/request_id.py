"""Request ID Middleware — 为每个请求注入唯一标识."""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求添加唯一的 X-Request-ID 标识."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取或生成 Request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # 将 request_id 存储到 request state
        request.state.request_id = request_id

        # 处理请求
        response: Response = await call_next(request)

        # 在响应头中返回 Request ID
        response.headers["X-Request-ID"] = request_id

        return response
