"""墨灵 (Moling) — 通知 API 路由。

实现列出通知、标记已读、删除通知等端点。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.service.notification_service import notification_service
from app.schemas.notification import NotificationResp

router = APIRouter()


@router.get("", response_model=dict)
async def list_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_read: bool = Query(None, description="已读状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取当前用户的通知列表。"""
    result = await notification_service.list_notifications(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        is_read=is_read,
    )
    return result


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """获取未读通知数量。"""
    result = await notification_service.get_unread_count(
        db,
        current_user.id,
    )
    return result


@router.post("/{notification_id}/read", response_model=NotificationResp)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> NotificationResp:
    """标记通知为已读。"""
    result = await notification_service.mark_as_read(
        db,
        current_user.id,
        notification_id,
    )
    return result


@router.post("/read-all", response_model=dict)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """标记所有通知为已读。"""
    result = await notification_service.mark_all_as_read(
        db,
        current_user.id,
    )
    return result


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    """删除通知。"""
    await notification_service.delete_notification(
        db,
        current_user.id,
        notification_id,
    )
