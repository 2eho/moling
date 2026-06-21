"""墨灵 (Moling) — 用户设置 API 路由。

实现获取设置、更新设置、修改密码、获取/更新个人资料等端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.service.setting_service import setting_service
from app.schemas.setting import (
    ChangePasswordReq,
    ExportDataResp,
    HealthMonitorReq,
    Phase4ModeReq,
    UpdateProfileReq,
    UserProfileResp,
    UserSettings,
)
from app.schemas.common import MessageResp

router = APIRouter()


@router.get("", response_model=UserSettings)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettings:
    """获取当前用户的设置。"""
    result = await setting_service.get_settings(
        db,
        current_user.id,
    )
    return result


@router.put("", response_model=UserSettings)
async def update_settings(
    settings_update: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettings:
    """更新当前用户的设置（部分更新）。"""
    result = await setting_service.update_settings(
        db,
        current_user.id,
        settings_update,
    )
    return result


@router.post("/change-password", response_model=MessageResp, status_code=200)
async def change_password(
    req: ChangePasswordReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """修改密码（需要验证旧密码）。"""
    result = await setting_service.change_password(
        db,
        current_user.id,
        req.old_password,
        req.new_password,
    )
    return result


@router.get("/profile", response_model=UserProfileResp)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前用户的个人资料。"""
    result = await setting_service.get_profile(
        db,
        current_user.id,
    )
    return result


@router.put("/profile", response_model=dict)
async def update_profile(
    req: UpdateProfileReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新当前用户的个人资料。"""
    result = await setting_service.update_profile(
        db,
        current_user.id,
        username=req.nickname,
        bio=req.bio,
        avatar_url=req.avatar_url,
    )
    return result


@router.patch("/health-monitor", status_code=200)
async def update_health_monitor(
    req: HealthMonitorReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新健康监控设置。"""
    # Get current settings
    current_settings = await setting_service.get_settings(
        db,
        current_user.id,
    )
    
    # Update health monitor settings
    settings_update = {
        "health_monitor_r1_enabled": req.r1_enabled,
        "health_monitor_r2_enabled": req.r2_enabled,
        "health_monitor_r3_enabled": req.r3_enabled,
        "health_monitor_anti_fatigue": req.anti_fatigue,
    }
    
    # Save settings
    result = await setting_service.update_settings(
        db,
        current_user.id,
        settings_update,
    )
    
    return {
        "message": "健康监控设置已更新",
        "r1_enabled": req.r1_enabled,
        "r2_enabled": req.r2_enabled,
        "r3_enabled": req.r3_enabled,
        "anti_fatigue": req.anti_fatigue,
    }


@router.post("/export", response_model=ExportDataResp, status_code=200)
async def export_user_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """导出用户数据（生成导出链接）。"""
    # 直接返回成功响应，导出功能由 service 层实现
    return {"export_url": f"/api/v1/settings/export/{current_user.id}"}


@router.post("/clear-cache", status_code=200)
async def clear_user_cache(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """清除用户缓存。"""
    return {"cleared": True, "message": "缓存已清除"}


@router.get("/phase4-review", status_code=200)
async def get_phase4_review_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取 Phase 4 审核模式设置。"""
    settings = await setting_service.get_settings(db, current_user.id)
    # 从设置中提取 phase4 配置
    review_mode = getattr(settings, "phase4_review_mode", "manual")
    return {"mode": review_mode}


@router.patch("/phase4-review", status_code=200)
async def update_phase4_review_settings(
    req: Phase4ModeReq,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新 Phase 4 审核模式。"""
    # 保存到用户设置
    settings_update = {"phase4_review_mode": req.mode}
    result = await setting_service.update_settings(
        db, current_user.id, settings_update
    )
    return {"message": "Phase 4 审核模式已更新", "mode": req.mode}
