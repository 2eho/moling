"""
墨灵 (Moling) — Card Retire Tasks.

Background tasks for card lifecycle management:
- Check card freshness
- Retire old cards
- Generate replacement cards
- Update card pool statistics

Uses ``get_worker_session()`` from ``app.worker.db`` for unified
database session management.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session
from app.worker.idempotency import is_duplicate, mark_completed, mark_failed

logger = logging.getLogger(__name__)

# ── P2 加固：区分可重试/不可重试/超时异常 ──
_RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def check_card_freshness(self, project_id: int) -> dict:
    """Check freshness of cards in a project's card pool.

    This task:
    1. Calculates freshness scores for all cards
    2. Identifies cards below threshold
    3. Marks them for retirement
    """
    task_key = f"task:{project_id}:check_card_freshness"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Checking card freshness for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.check_freshness(db, project_id)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {"status": "done", "project_id": project_id, "checked": result}

    except SoftTimeLimitExceeded:
        logger.error("Card freshness check timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Card freshness check failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Card freshness check failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def retire_cards(self, project_id: int, card_ids: list[int]) -> dict:
    """Retire specified cards from the card pool.

    This task:
    1. Marks cards as retired
    2. Updates card pool statistics
    3. Triggers replacement card generation
    """
    task_key = f"task:{project_id}:retire_cards"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Retiring %d cards for project %s", len(card_ids), project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.retire_cards(db, project_id, card_ids)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {"status": "done", "project_id": project_id, "retired": result}

    except SoftTimeLimitExceeded:
        logger.error("Card retirement timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Card retirement failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Card retirement failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, autoretry_for=_RETRYABLE)
def generate_replacement_cards(self, project_id: int, count: int = 5) -> dict:
    """Generate replacement cards for retired ones.

    This task:
    1. Analyzes current card pool
    2. Identifies gaps
    3. Generates new cards to fill gaps
    """
    task_key = f"task:{project_id}:generate_replacement_cards"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Generating %d replacement cards for project %s", count, project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.generate_replacements(db, project_id, count)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        return {
            "status": "done",
            "project_id": project_id,
            "generated": len(result),
        }

    except SoftTimeLimitExceeded:
        logger.error("Replacement card generation timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Replacement card generation failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Replacement card generation failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=180, autoretry_for=_RETRYABLE)
def card_retire_check(self) -> dict:
    """Celery Beat 定时任务：扫描所有活跃项目，检查是否有需要退休的卡片。

    每天执行一次（凌晨 2 点），由 Celery Beat 调度触发。
    对每个活跃项目的卡片池进行新鲜度检查，标记并退休过期卡片。
    """
    task_key = f"task:beat:card_retire_check:{datetime.now().strftime('%Y-%m-%d')}"
    if is_duplicate(task_key):
        return {"status": "already_processed"}

    logger.info("Card retire check: starting daily scan")

    async def _run():
        async with get_worker_session() as db:
            from app.dao import project_dao
            from app.service.card_pool_service import CardPoolService

            projects = await project_dao.get_all_active(db)
            service = CardPoolService()
            results = []

            for project in projects:
                try:
                    freshness = await service.check_freshness(db, project.id)
                    expired_count = freshness.get("expired", 0)
                    if expired_count > 0:
                        logger.info("Project %s: %s cards expired", project.id, expired_count)
                    results.append({
                        "project_id": project.id,
                        "checked": freshness.get("total", 0),
                        "expired": expired_count,
                    })
                except Exception as e:
                    logger.warning("Card retire check failed for project %s: %s", project.id, e)
                    results.append({"project_id": project.id, "error": str(e)})

            return {"scanned": len(projects), "results": results}

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        logger.info("Card retire check completed: scanned %s projects", result["scanned"])
        return {"status": "done", **result}

    except SoftTimeLimitExceeded:
        logger.error("Card retire check timed out")
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Card retire check failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Card retire check failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "error": str(exc)}
