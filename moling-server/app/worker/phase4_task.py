"""
墨灵 (Moling) — Phase 4 自动收纳任务.

定时执行 Phase 4 自动收纳流程：
- 触发卡池分析
- 执行四库更新
- 卡牌充实
- 健康检查
"""

from __future__ import annotations

import logging

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def run_phase4_analysis(self, project_id: int) -> dict:
    """Trigger Phase 4 analysis for a project.

    This task:
    1. Analyzes the card pool
    2. Identifies entities to store in vault
    3. Updates vault entries
    """
    logger.info("Starting Phase 4 analysis for project %s", project_id)

    try:
        import asyncio
        from app.service.phase4_service import Phase4Service

        service = Phase4Service()
        result = asyncio.run(service.analyze_project(project_id))

        logger.info("Phase 4 analysis completed for project %s", project_id)
        return {"status": "done", "project_id": project_id, "result": result}

    except Exception as exc:
        logger.exception("Phase 4 analysis failed for project %s", project_id)
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=1)
def update_vault_entries(self, project_id: int, chapter_id: int) -> dict:
    """Update vault entries after chapter generation.

    This task:
    1. Extracts entities from the chapter
    2. Updates corresponding vault entries
    3. Adjusts confidence scores
    """
    logger.info(
        "Updating vault for project %s, chapter %s", project_id, chapter_id
    )

    try:
        import asyncio
        from app.service.vault_service import VaultService

        service = VaultService()
        result = asyncio.run(service.update_from_chapter(project_id, chapter_id))

        return {"status": "done", "project_id": project_id, "chapter_id": chapter_id}

    except Exception as exc:
        logger.exception("Vault update failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def execute_phase4_storage(self, task_id: int) -> dict:
    """Execute the full Phase 4 storage pipeline for a confirmed chapter.

    Full pipeline:
    1. Calls LLM to analyze chapter content (角色/时间线/剧情承诺/世界观)
    2. Updates DynamicLayer (摘要、锚点、未收束钩子)
    3. Updates four vault databases (角色库/时间线库/伏笔库/世界观库)
    4. Updates CardPool weights and generates new cards
    5. Marks Phase4Task and chapter as completed

    Args:
        task_id: Phase4Task record ID
    """
    logger.info("Starting Phase 4 full storage pipeline for task %s", task_id)

    try:
        import asyncio
        from app.service.phase4_service import Phase4Service

        service = Phase4Service()

        # 创建独立 DB session 执行异步操作
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async def _run():
            async with SessionLocal() as db:
                return await service.execute_storage(db, task_id)

        result = asyncio.run(_run())

        logger.info("Phase 4 full storage completed for task %s", task_id)
        return {
            "status": "done",
            "task_id": task_id,
            "result": result,
        }

    except Exception as exc:
        logger.exception("Phase 4 full storage failed for task %s", task_id)
        raise self.retry(exc=exc) from exc
