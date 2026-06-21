"""墨灵 (Moling) — Ingest Job DAO.

封装 IngestJob 的数据库访问，避免 Service 层绕过 DAO 直接 select()。
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.dao.base_dao import BaseDAO
from app.ingest.models import IngestJob
from app.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


class IngestJobDAO(BaseDAO[IngestJob]):
    """IngestJob 数据访问对象。"""

    def __init__(self) -> None:
        super().__init__(IngestJob)

    async def get_by_project(
        self,
        db: AsyncSession,
        project_id: str,
    ) -> list[IngestJob]:
        """按项目 ID 查询导入任务列表（ID 倒序）。"""
        try:
            stmt = (
                select(IngestJob)
                .where(IngestJob.project_id == project_id)
                .order_by(IngestJob.id.desc())
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"IngestJobDAO.get_by_project({project_id}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))

    async def list_by_status(
        self,
        db: AsyncSession,
        status: str,
        *,
        limit: int = 50,
    ) -> list[IngestJob]:
        """按状态查询导入任务列表。"""
        try:
            return await self.get_multi(
                db,
                filters={"current_phase": status},
                limit=limit,
                order_by="id",
                descending=True,
            )
        except SQLAlchemyError as e:
            logger.error(f"IngestJobDAO.list_by_status({status}) failed: {e}")
            raise AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))


# Module-level singleton
ingest_dao = IngestJobDAO()
