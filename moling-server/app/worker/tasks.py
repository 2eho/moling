"""
墨灵 (Moling) — Celery Tasks.

Background task definitions executed by Celery workers.  Each task receives a
``generation_task_id`` (UUID string) and updates the database via the Service layer
as processing progresses.

Graceful degradation: if the broker is unreachable when a task is submitted,
the caller in ``generation_service`` marks the task as ``failed``.
"""

from __future__ import annotations

import logging
import platform

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.service.generation_service import GenerationService
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_db_url() -> str:
    """返回适配当前平台的数据库 URL（Windows + SQLite 用 aiosqlite）。"""
    settings = get_settings()
    url = settings.DATABASE_URL
    if platform.system() == "Windows" and url.startswith("sqlite"):
        if "aiosqlite" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _create_session_factory() -> async_sessionmaker[AsyncSession]:
    """Build an async sessionmaker from settings (called once per task)."""
    engine = create_async_engine(_get_db_url(), echo=False, pool_size=2)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


_session_factory = _create_session_factory()


# ---------------------------------------------------------------------------
# Task: run_generation_task
# ---------------------------------------------------------------------------


async def _run_pipeline(service: GenerationService, generation_task_id: str) -> dict:
    """Run the generation pipeline with a proper database session."""
    async with _session_factory() as db:
        return await service.execute_generation_pipeline(db, generation_task_id)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_generation_task(self, generation_task_id: str) -> dict:
    """Execute an AI generation task in the background.

    This function:
    1. Checks idempotency — skips if task is already ``done`` in DB
    2. Creates a database session
    3. Calls the GenerationService to execute the generation
    4. Handles exceptions and retries
    """
    logger.info("Starting generation task %s", generation_task_id)

    # ── P1 加固：幂等性检查 ──
    # 防止 visibility_timeout 超时重投递 → 同一任务被多个 worker 重复执行
    import asyncio
    from uuid import UUID

    task_uuid = UUID(generation_task_id)
    status = asyncio.run(_get_task_status(task_uuid))
    if status == "done":
        logger.info("Task %s already done, skipping (idempotent)", generation_task_id)
        return {"status": "already_done", "task_id": generation_task_id}

    try:
        # Create a new service instance for this task
        service = GenerationService()

        # Execute the generation pipeline with a proper db session
        _ = asyncio.run(_run_pipeline(service, generation_task_id))

        return {"status": "done", "task_id": generation_task_id}

    except Exception as exc:
        logger.exception("Generation task %s failed", generation_task_id)
        # Mark task as failed
        asyncio.run(_mark_failed(generation_task_id, str(exc)))
        raise self.retry(exc=exc) from exc


async def _get_task_status(task_uuid):
    """Query the DB for a generation task's current status (for idempotency)."""
    from app.dao import generation_dao
    async with _session_factory() as db:
        task = await generation_dao.get(db, task_uuid)
        return task.status if task else None


async def _mark_failed(task_id: str, error_message: str) -> None:
    """Mark a generation task as failed."""
    from uuid import UUID
    from app.dao import generation_dao

    task_uuid = UUID(task_id)
    async with _session_factory() as db:
        task = await generation_dao.get(db, task_uuid)
        if task:
            await generation_dao.update(
                db,
                task,
                {"status": "failed", "error_message": error_message},
            )
            await db.commit()
