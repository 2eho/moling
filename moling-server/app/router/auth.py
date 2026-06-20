"""墨灵 (Moling) — 认证 API 路由。

实现用户注册、登录、刷新令牌、获取当前用户、登出等端点。
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.dependencies import get_current_user, get_db, get_sync_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import LoginReq, LogoutReq, PasswordResetReq, PasswordResetRequestReq, RefreshReq, RegisterReq, TokenResp, UpdateProfileReq, UserResp
from app.service import auth_service
from sqlalchemy.orm import Session as SyncSession

router = APIRouter()

settings = get_settings()

# Bearer token 提取器
_security = HTTPBearer()

# 导入 slowapi limiter（共享实例，位于 app/limiter.py 避免循环导入）
from app.limiter import limiter


@router.post("/register", response_model=TokenResp, status_code=201)
@limiter.limit("3/minute")  # 注册限制：3 次/分钟
async def register(
    request: Request,
    req: RegisterReq,
    db: SyncSession = Depends(get_sync_db),
) -> TokenResp:
    """注册新用户并返回令牌。"""
    return auth_service.register_sync(db, req)


@router.post("/login", response_model=TokenResp)
@limiter.limit("5/minute")  # 登录限制：5 次/分钟
async def login(
    request: Request,
    req: LoginReq,
    db: SyncSession = Depends(get_sync_db),
) -> TokenResp:
    """使用邮箱和密码登录并返回令牌。"""
    return auth_service.login_sync(db, req)


@router.post("/refresh", response_model=TokenResp)
async def refresh(
    req: RefreshReq,
    db: AsyncSession = Depends(get_db),
) -> TokenResp:
    """使用刷新令牌获取新的访问令牌。"""
    return await auth_service.refresh_tokens(db, req.refresh_token)


@router.get("/me", response_model=UserResp)
def get_me(
    current_user=Depends(get_current_user),
) -> UserResp:
    """获取当前登录用户的信息。"""
    return current_user


@router.post("/password-reset-request", status_code=200)
@limiter.limit("3/minute")  # 密码重置请求限制：3 次/分钟
async def password_reset_request(
    request: Request,
    req: PasswordResetRequestReq,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """请求密码重置（发送重置邮件）。"""
    return await auth_service.request_password_reset(db, req)


@router.post("/password-reset", status_code=200)
async def password_reset(
    req: PasswordResetReq,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """使用令牌重置密码。"""
    return await auth_service.reset_password(db, req)


@router.put("/me", response_model=UserResp)
async def update_me(
    req: UpdateProfileReq,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResp:
    """更新当前用户的资料（用户名、头像）。"""
    return await auth_service.update_profile(db, current_user.id, req)


@router.post("/logout", status_code=200)
async def logout(
    req: LogoutReq,
) -> dict:
    """登出用户（将 token 加入黑名单）。"""
    return await auth_service.logout(req.access_token, req.refresh_token)
