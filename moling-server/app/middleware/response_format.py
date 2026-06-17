"""Response Format Middleware — 统一所有响应的格式.

实现统一响应格式: {code: number, message: string, data: any, meta: object}
"""

from __future__ import annotations

import json
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class ResponseFormatMiddleware(BaseHTTPMiddleware):
    """统一响应格式中间件.

    将所有响应包装为统一格式:
    {
        "code": 0,           # 业务码，0 表示成功
        "message": "success", # 提示信息
        "data": {},           # 实际数据
        "meta": {             # 元数据
            "request_id": "",
            "timestamp": 0,
            "version": ""
        }
    }
    """

    def __init__(self, app: ASGIApp, version: str = "1.0.0"):
        super().__init__(app)
        self.version = version

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 如果是流式响应或不是 JSON 响应，直接返回
        if not isinstance(response, JSONResponse):
            return response

        # 获取响应内容
        response_body = None
        if hasattr(response, 'body'):
            body_attr = response.body
            # 检查是否是协程或异步迭代器
            import inspect
            if inspect.iscoroutine(body_attr):
                response_body = await body_attr
            elif inspect.isasyncgen(body_attr):
                chunks = []
                async for chunk in body_attr:
                    chunks.append(chunk)
                response_body = b''.join(chunks)
            else:
                response_body = body_attr
        
        if not response_body:
            return response

        try:
            body_data = json.loads(response_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response

        # 检查是否已经是统一格式
        if self._is_unified_format(body_data):
            # 补充 meta 信息
            body_data["meta"] = self._build_meta(request, start_time)
            response.body = json.dumps(body_data, ensure_ascii=False).encode("utf-8")
            response.headers["content-length"] = str(len(response.body))
            return response

        # 包装为统一格式
        status_code = response.status_code

        if status_code >= 200 and status_code < 300:
            # 成功响应
            unified_body = {
                "code": 0,
                "message": "success",
                "data": body_data,
                "meta": self._build_meta(request, start_time),
            }
        else:
            # 错误响应 - 保持原样（已由异常处理器处理）
            return response

        # 创建新的响应
        return JSONResponse(
            content=unified_body,
            status_code=status_code,
            headers=dict(response.headers),
        )

    def _is_unified_format(self, data: dict) -> bool:
        """检查数据是否已经是统一格式."""
        return (
            isinstance(data, dict)
            and "code" in data
            and "message" in data
            and "data" in data
        )

    def _build_meta(self, request: Request, start_time: float) -> dict:
        """构建元数据."""
        request_id = getattr(request.state, "request_id", "")
        timestamp = int(time.time() * 1000)
        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "request_id": request_id,
            "timestamp": timestamp,
            "version": self.version,
            "elapsed_ms": elapsed_ms,
        }
