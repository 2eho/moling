"""墨灵 (Moling) — 用户设置 API 路由。

实现获取设置、更新设置、修改密码、获取/更新个人资料等端点。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.setting_service import setting_service
from app.schemas.setting import UserSettings

router = APIRouter()


class ChangePasswordReq(BaseModel):
    """Request body for changing password."""

    old_password: str
    new_password: str


class UpdateProfileReq(BaseModel):
    """Request body for updating user profile."""

    username: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


@router.get("", response_model=UserSettings)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserSettings:
    """获取当前用户的设置。"""
    result = await setting_service.get_settings(
        db,
        int(current_user["id"]),
    )
    return result


@router.put("", response_model=UserSettings)
async def update_settings(
    settings_update: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserSettings:
    """更新当前用户的设置（部分更新）。"""
    result = await setting_service.update_settings(
        db,
        int(current_user["id"]),
        settings_update,
    )
    return result


@router.post("/change-password", status_code=200)
async def change_password(
    req: ChangePasswordReq,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """修改密码（需要验证旧密码）。"""
    result = await setting_service.change_password(
        db,
        int(current_user["id"]),
        req.old_password,
        req.new_password,
    )
    return result


@router.get("/profile", response_model=dict)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取当前用户的个人资料。"""
    result = await setting_service.get_profile(
        db,
        int(current_user["id"]),
    )
    return result


@router.put("/profile", response_model=dict)
async def update_profile(
    req: UpdateProfileReq,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """更新当前用户的个人资料。"""
    result = await setting_service.update_profile(
        db,
        int(current_user["id"]),
        username=req.username,
        bio=req.bio,
        avatar_url=req.avatar_url,
    )
    return result
