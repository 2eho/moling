"""
墨灵 (Moling) — Book Analysis Tasks.

Background tasks for analyzing books:
- Character extraction
- Plot analysis
- Style detection
- World-building analysis

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
from app.worker.idempotency import is_duplicate, mark_completed, mark_failed

logger = logging.getLogger(__name__)

# ── P2 加固：区分可重试/不可重试/超时异常 ──
_RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def analyze_book_characters(self, project_id: int) -> dict:
    """Analyze characters in a book."""
    task_key = f"task:{project_id}:analyze_book_characters"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Analyzing characters for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.book_analysis_service import BookAnalysisService

            service = BookAnalysisService()
            return await service.analyze_characters(db, project_id)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {"status": "done", "project_id": project_id, "characters": result}

    except SoftTimeLimitExceeded:
        logger.error("Character analysis timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Character analysis failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Character analysis failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def analyze_book_plot(self, project_id: int) -> dict:
    """Analyze plot structure of a book."""
    task_key = f"task:{project_id}:analyze_book_plot"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Analyzing plot for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.book_analysis_service import BookAnalysisService

            service = BookAnalysisService()
            return await service.analyze_plot(db, project_id)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {"status": "done", "project_id": project_id, "plot": result}

    except SoftTimeLimitExceeded:
        logger.error("Plot analysis timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Plot analysis failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Plot analysis failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def detect_writing_style(self, project_id: int) -> dict:
    """Detect writing style of a book."""
    task_key = f"task:{project_id}:detect_writing_style"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Detecting writing style for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.book_analysis_service import BookAnalysisService

            service = BookAnalysisService()
            return await service.detect_style(db, project_id)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {"status": "done", "project_id": project_id, "style": result}

    except SoftTimeLimitExceeded:
        logger.error("Style detection timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Style detection failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Style detection failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}
