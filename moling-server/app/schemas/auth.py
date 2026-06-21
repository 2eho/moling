"""墨灵 (Moling) — Auth-related Pydantic Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterReq(BaseModel):
    """User registration request body."""

    email: EmailStr = Field(..., description="注册邮箱")
    nickname: str = Field(
        ..., min_length=2, max_length=50, description="用户昵称"
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="密码 (至少 8 位)"
    )


class LoginReq(BaseModel):
    """User login request body."""

    email: EmailStr = Field(..., description="登录邮箱")
    password: str = Field(..., description="密码")


class RefreshReq(BaseModel):
    """Token refresh request body."""

    refresh_token: str = Field(..., description="刷新令牌")


class UserResp(BaseModel):
    """User response (public-facing, no password hash)."""

    id: str = Field(..., description="用户 ID (UUID)")
    email: str = Field(..., description="邮箱")
    nickname: str = Field(..., validation_alias="username", description="用户昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像 URL")
    status: str = Field(default="active", description="用户状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class TokenResp(BaseModel):
    """Authentication token response."""

    access_token: str = Field(..., description="访问令牌 (JWT, 短期)")
    refresh_token: str = Field(..., description="刷新令牌 (长期)")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(default=900, description="访问令牌过期时间(秒)")
    user: UserResp = Field(..., description="当前用户信息")

    @property
    def id(self) -> str:
        """Convenience alias for ``user.id``."""
        return self.user.id


class UpdateProfileReq(BaseModel):
    """Update user profile request body."""

    username: str | None = Field(default=None, min_length=2, max_length=50, description="用户昵称")
    avatar_url: str | None = Field(default=None, max_length=500, description="头像 URL")


class PasswordResetRequestReq(BaseModel):
    """Password reset request body (step 1: request reset)."""

    email: EmailStr = Field(..., description="注册邮箱")


class PasswordResetReq(BaseModel):
    """Password reset request body (step 2: actually reset)."""

    token: str = Field(..., min_length=32, max_length=128, description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码 (至少 8 位)")


class LogoutReq(BaseModel):
    """User logout request body."""

    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
