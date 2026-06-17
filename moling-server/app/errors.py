"""墨灵 (Moling) — Business Exception Hierarchy.

All domain-level errors inherit from AppError and carry:
- A machine-readable ErrorCode enum value
- An HTTP status code mapped automatically
- A human-readable Chinese message
"""

from __future__ import annotations

from enum import Enum
from fastapi import HTTPException, status


class ErrorCode(int, Enum):
    """Machine-readable error codes (数字格式).

    格式: HTTP状态码 * 100 + 序号
    例如: 40001 = 400(Bad Request) * 100 + 01
    """

    # ---- Auth (401xx) ----
    AUTH_INVALID_CREDENTIALS = 40101
    AUTH_TOKEN_EXPIRED = 40102
    AUTH_INVALID_TOKEN = 40103
    AUTH_INSUFFICIENT_PERMISSIONS = 40301

    # ---- User (409xx) ----
    USER_NOT_FOUND = 40401
    USER_EMAIL_EXISTS = 40901
    USER_USERNAME_EXISTS = 40902

    # ---- Project (404xx) ----
    PROJECT_NOT_FOUND = 40402
    PROJECT_ACCESS_DENIED = 40302

    # ---- Chapter (404xx) ----
    CHAPTER_NOT_FOUND = 40403
    CHAPTER_NUMBER_EXISTS = 40904

    # ---- Card Pool / Card (404xx) ----
    CARD_POOL_NOT_FOUND = 40404
    CARD_NOT_FOUND = 40405

    # ---- Vault (404xx) ----
    VAULT_ENTRY_NOT_FOUND = 40406

    # ---- Generation (409xx) ----
    GENERATION_TASK_NOT_FOUND = 40407
    GENERATION_IN_PROGRESS = 40903

    # ---- General (4xx/5xx) ----
    INVALID_REQUEST = 40001
    VALIDATION_ERROR = 42201
    RATE_LIMIT_EXCEEDED = 42901
    INTERNAL_ERROR = 50001

    @property
    def message(self) -> str:
        """Return the Chinese human-readable message for this error code."""
        return _ERROR_MESSAGES[self]


_ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.AUTH_INVALID_CREDENTIALS: "邮箱或密码错误",
    ErrorCode.AUTH_TOKEN_EXPIRED: "登录已过期，请重新登录",
    ErrorCode.AUTH_INVALID_TOKEN: "无效的认证令牌",
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: "权限不足",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.USER_EMAIL_EXISTS: "该邮箱已被注册",
    ErrorCode.USER_USERNAME_EXISTS: "该用户名已被使用",
    ErrorCode.PROJECT_NOT_FOUND: "项目不存在",
    ErrorCode.PROJECT_ACCESS_DENIED: "无权访问该项目",
    ErrorCode.CHAPTER_NOT_FOUND: "章节不存在",
    ErrorCode.CHAPTER_NUMBER_EXISTS: "章节编号已存在",
    ErrorCode.CARD_POOL_NOT_FOUND: "卡池不存在",
    ErrorCode.CARD_NOT_FOUND: "卡片不存在",
    ErrorCode.VAULT_ENTRY_NOT_FOUND: "四库条目不存在",
    ErrorCode.GENERATION_TASK_NOT_FOUND: "生成任务不存在",
    ErrorCode.GENERATION_IN_PROGRESS: "正在生成中，请稍后再试",
    ErrorCode.INVALID_REQUEST: "请求参数无效",
    ErrorCode.VALIDATION_ERROR: "请求参数验证失败",
    ErrorCode.RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后再试",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
}

# ---- HTTP Status Code Mapping ----

_ERROR_TO_STATUS: dict[ErrorCode, int] = {
    ErrorCode.AUTH_INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
    ErrorCode.USER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.USER_EMAIL_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.USER_USERNAME_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.PROJECT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.PROJECT_ACCESS_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.CHAPTER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CHAPTER_NUMBER_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.CARD_POOL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CARD_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.VAULT_ENTRY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.GENERATION_TASK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.GENERATION_IN_PROGRESS: status.HTTP_409_CONFLICT,
    ErrorCode.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
    ErrorCode.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


# ---- Exception Classes ----

class AppError(HTTPException):
    """Base application error — all domain exceptions inherit from this."""

    def __init__(
        self,
        error_code: ErrorCode,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.error_code = error_code
        status_code = _ERROR_TO_STATUS.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.detail = detail or error_code.message
        super().__init__(status_code=status_code, detail=self.detail, headers=headers)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.PROJECT_NOT_FOUND,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


class VaultNotFoundError(AppError):
    """Vault entry not found (404)."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(ErrorCode.VAULT_ENTRY_NOT_FOUND, detail)


class AuthError(AppError):
    """Authentication failure (401)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.AUTH_INVALID_CREDENTIALS,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


class PermissionError(AppError):
    """Insufficient permissions (403)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


class ValidationError(AppError):
    """Request validation failure (422)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


class RateLimitError(AppError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


class ConflictError(AppError):
    """Resource conflict (409)."""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.USER_EMAIL_EXISTS,
        detail: str | None = None,
    ) -> None:
        super().__init__(error_code, detail)


# ---------------------------------------------------------------------------
# Backward Compatibility Aliases
# ---------------------------------------------------------------------------

# Backward compat aliases
ForbiddenError = PermissionError   # correct spelling
ForbiddenError = PermissionError   # common misspelling used in services
