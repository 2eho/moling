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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_generation_task(self, generation_task_id: str) -> dict:
    """Execute an AI generation task in the background.

    This function:
    1. Creates a database session
    2. Calls the GenerationService to execute the generation
    3. Handles exceptions and retries
    """
    logger.info("Starting generation task %s", generation_task_id)

    try:
        # Create a new service instance for this task
        service = GenerationService()

        # Execute the generation (service handles db session internally)
        import asyncio
        _ = asyncio.run(service.execute_generation(
            None,  # db session created inside service
            generation_task_id,
        ))

        return {"status": "done", "task_id": generation_task_id}

    except Exception as exc:
        logger.exception("Generation task %s failed", generation_task_id)
        # Mark task as failed
        import asyncio
        asyncio.run(_mark_failed(generation_task_id, str(exc)))
        raise self.retry(exc=exc) from exc


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
