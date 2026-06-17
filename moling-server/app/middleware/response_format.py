"""Response Format Middleware — 统一所有 JSON 响应的格式.

使用 ASGI 级别拦截（而非 BaseHTTPMiddleware），确保在所有路由上
（包括使用了 @limiter.limit / response_model 的端点）都能可靠读取响应 body。

统一格式: {code: number, message: string, data: any, meta: object}
"""

from __future__ import annotations

import json
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ResponseFormatMiddleware:
    """统一响应格式中间件（ASGI 级别）.

    拦截所有 JSONResponse，包装为统一格式:
    {
        "code": 0,
        "message": "success",
        "data": <原始响应数据>,
        "meta": { "request_id": "", "timestamp": 0, "version": "", "elapsed_ms": 0 }
    }
    """

    def __init__(self, app: ASGIApp, version: str = "1.0.0") -> None:
        self.app = app
        self.version = version

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI 入口：拦截 HTTP 响应，包装 JSON body。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        request_id = self._extract_request_id(scope)

        # 收集响应（拦截 send 调用）
        raw_status_code = 200
        raw_headers: list[tuple[bytes, bytes]] = []
        raw_body_chunks: list[bytes] = []

        async def intercepted_send(message: Message) -> None:
            nonlocal raw_status_code, raw_headers
            if message["type"] == "http.response.start":
                raw_status_code = message["status"]
                raw_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                raw_body_chunks.append(message.get("body", b""))

        await self.app(scope, receive, intercepted_send)

        # 合并 body
        raw_body = b"".join(raw_body_chunks)

        # 判断是否是 JSON 响应
        content_type = self._get_header(raw_headers, b"content-type")
        is_json = content_type and (b"application/json" in content_type or b"application/problem+json" in content_type)

        # 只有 JSON 成功响应需要包装
        if not is_json:
            await self._send_raw(send, raw_status_code, raw_headers, raw_body)
            return

        # 解析 body
        body_data = self._parse_body(raw_body)
        if body_data is None:
            await self._send_raw(send, raw_status_code, raw_headers, raw_body)
            return

        # 检查是否已经是统一格式
        if self._is_unified_format(body_data):
            # 补充 meta 信息
            if "meta" not in body_data:
                body_data["meta"] = self._build_meta(request_id, start_time)
            await self._send_json(send, raw_status_code, raw_headers, body_data)
            return

        # 成功响应才包装
        if 200 <= raw_status_code < 300:
            unified_body = {
                "code": 0,
                "message": "success",
                "data": body_data,
                "meta": self._build_meta(request_id, start_time),
            }
            await self._send_json(send, raw_status_code, raw_headers, unified_body)
        else:
            # 错误响应保持原样
            await self._send_raw(send, raw_status_code, raw_headers, raw_body)

    # ---- 辅助方法 ----

    def _extract_request_id(self, scope: Scope) -> str:
        """从请求 scope 中提取 request_id。"""
        # 尝试从 state 中获取（由 RequestIDMiddleware 注入）
        # ASGI 级别没有 state，需要从 scope 中读取
        headers = dict(scope.get("headers", []))
        # 如果前端传了 X-Request-ID，就用它
        rid = headers.get(b"x-request-id", b"")
        if rid:
            return rid.decode("utf-8", errors="ignore")
        return ""

    def _get_header(self, headers: list[tuple[bytes, bytes]], key: bytes) -> bytes | None:
        for k, v in headers:
            if k.lower() == key.lower():
                return v
        return None

    def _parse_body(self, body: bytes) -> dict | list | None:
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _is_unified_format(self, data: dict | list) -> bool:
        """检查数据是否已经是统一格式。"""
        return (
            isinstance(data, dict)
            and "code" in data
            and "message" in data
            and "data" in data
        )

    def _build_meta(self, request_id: str, start_time: float) -> dict:
        """构建元数据。"""
        timestamp = int(time.time() * 1000)
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "request_id": request_id,
            "timestamp": timestamp,
            "version": self.version,
            "elapsed_ms": elapsed_ms,
        }

    async def _send_raw(
        self,
        send: Send,
        status_code: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
    ) -> None:
        """发送原始响应（不包装）。"""
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })

    async def _send_json(
        self,
        send: Send,
        status_code: int,
        original_headers: list[tuple[bytes, bytes]],
        data: dict,
    ) -> None:
        """发送 JSON 响应，更新 content-length。"""
        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        # 更新 content-length
        new_headers = [
            (k, v) for k, v in original_headers
            if k.lower() != b"content-length"
        ]
        new_headers.append((b"content-length", str(len(body_bytes)).encode("ascii")))
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": new_headers,
        })
        await send({
            "type": "http.response.body",
            "body": body_bytes,
        })
