"""
墨灵 (Moling) — Import Tasks.

Background tasks for importing novels/books:
- Parse uploaded files
- Extract chapters
- Analyze content
- Create project structure

Uses ``get_worker_session()`` from ``app.worker.db`` for unified
database session management.
"""

from __future__ import annotations

import asyncio
import logging

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session

logger = logging.getLogger(__name__)

# ── P2 加固：区分可重试/不可重试/超时异常 ──
_RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def import_book_task(self, project_id: int, file_path: str, import_mode: str) -> dict:
    """Import a book from file.

    This task:
    1. Parse the uploaded file (txt, docx, epub)
    2. Split into chapters
    3. Extract metadata
    4. Create project and chapters
    """
    logger.info("Starting book import for project %s from %s", project_id, file_path)

    async def _run():
        async with get_worker_session() as db:
            from app.service.import_service import ImportService

            service = ImportService()
            return await service.import_book(db, project_id, file_path, import_mode)

    try:
        result = asyncio.run(_run())
        logger.info("Book import completed for project %s", project_id)
        return {"status": "done", "project_id": project_id, "result": result}

    except SoftTimeLimitExceeded:
        logger.error("Book import timed out for project %s", project_id)
        raise

    except _RETRYABLE as exc:
        logger.exception("Book import failed (retryable) for project %s", project_id)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Book import failed (non-retryable) for project %s", project_id)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, autoretry_for=_RETRYABLE)
def analyze_import_content(self, project_id: int) -> dict:
    """Analyze imported content for suggestions."""
    logger.info("Analyzing import content for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.import_service import ImportService

            service = ImportService()
            return await service.analyze_content(db, project_id)

    try:
        result = asyncio.run(_run())
        return {"status": "done", "project_id": project_id, "analysis": result}

    except SoftTimeLimitExceeded:
        logger.error("Import analysis timed out for project %s", project_id)
        raise

    except _RETRYABLE as exc:
        logger.exception("Import analysis failed (retryable)")
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Import analysis failed (non-retryable)")
        return {"status": "failed", "project_id": project_id, "error": str(exc)}
