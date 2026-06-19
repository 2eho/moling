"""Audit Log Middleware — 记录所有 API 调用的审计日志."""

from __future__ import annotations

import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class AuditLogMiddleware(BaseHTTPMiddleware):
    """审计日志中间件 — 记录所有 API 请求/响应信息."""

    # 不需要记录审计日志的路径（如健康检查、静态文件等）
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs-static",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否需要记录审计日志
        if self._should_skip_audit(request):
            return await call_next(request)

        # 记录请求开始时间
        start_time = time.time()

        # 读取请求体并缓存到 request.state（用于错误日志等场景）
        try:
            body_bytes = await request.body()
            request.state.body = body_bytes.decode("utf-8", errors="replace") if body_bytes else None
        except Exception:
            request.state.body = None

        # 提取请求信息
        audit_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "method": request.method,
            "path": str(request.url.path),
            "query": str(request.query_params) if request.query_params else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "request_id": getattr(request.state, "request_id", None),
        }

        # 尝试获取用户信息
        user = await self._get_current_user(request)
        if user:
            audit_entry["user_id"] = user.get("id")
            audit_entry["user_email"] = user.get("email")
            request.state.user_id = user.get("id")

        # 处理请求
        try:
            response = await call_next(request)

            # 记录响应信息
            audit_entry["status_code"] = response.status_code
            audit_entry["duration_ms"] = int((time.time() - start_time) * 1000)

            # 记录审计日志（这里简单打印，生产环境应写入数据库或日志系统）
            self._write_audit_log(audit_entry)

            return response

        except Exception as exc:
            # 记录异常信息
            audit_entry["status_code"] = 500
            audit_entry["error"] = str(exc)
            audit_entry["duration_ms"] = int((time.time() - start_time) * 1000)

            self._write_audit_log(audit_entry)
            raise

    def _should_skip_audit(self, request: Request) -> bool:
        """检查是否应该跳过审计日志记录."""
        path = str(request.url.path)

        # 检查是否在排除列表中
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True

        return False

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP 地址."""
        # 尝试从代理头获取真实 IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _get_current_user(self, request: Request) -> dict | None:
        """尝试从请求中获取当前用户信息."""
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        try:
            token = auth_header[7:]
            from jose import jwt
            from app.config import get_settings
            s = get_settings()
            payload = jwt.decode(
                token, s.SECRET_KEY, algorithms=[s.ALGORITHM],
                options={"verify_exp": False},  # 审计日志允许过期 token
            )
            return {
                "id": payload.get("sub"),
                "email": payload.get("email", ""),
            }
        except Exception:
            return None

    def _write_audit_log(self, audit_entry: dict) -> None:
        """写入审计日志."""
        # 这里简单打印，生产环境应:
        # 1. 写入数据库 audit_logs 表
        # 2. 发送到日志系统（如 ELK）
        # 3. 发送到消息队列进行异步处理

        # 敏感信息过滤（避免记录密码等）
        if "password" in str(audit_entry.get("query", "")).lower():
            audit_entry["query"] = "[FILTERED]"

        print(f"[AUDIT] {json.dumps(audit_entry, ensure_ascii=False)}")
