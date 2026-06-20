"""墨灵 (Moling) — 安全验证工具函数。

提供跨 service 复用的权限验证逻辑，消除重复的 project 所有权检查。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ErrorCode, NotFoundError, PermissionError
from app.models.project import Project


async def verify_project_ownership(
    db: AsyncSession,
    project_id: int,
    user_id: str,
) -> Project:
    """验证项目存在且属于当前用户，否则抛异常。

    将以下 10+ 行的样板代码：
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(...)
        if project.user_id != user_id:
            raise PermissionError(...)

    替换为一行：
        project = await verify_project_ownership(db, project_id, user_id)

    Args:
        db: 数据库会话
        project_id: 项目 ID
        user_id: 用户 ID (UUID 字符串)

    Returns:
        验证通过后的 Project 实例

    Raises:
        NotFoundError: 项目不存在
        PermissionError: 项目不属于当前用户
    """
    from app.dao.project_dao import project_dao

    project = await project_dao.get(db, project_id)
    if project is None:
        raise NotFoundError(
            error_code=ErrorCode.PROJECT_NOT_FOUND,
            detail="项目不存在",
        )
    if project.user_id != user_id:
        raise PermissionError(
            error_code=ErrorCode.PROJECT_ACCESS_DENIED,
            detail="无权访问该项目",
        )
    return project
