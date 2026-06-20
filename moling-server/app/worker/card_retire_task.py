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

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session

logger = logging.getLogger(__name__)

# ── P2 加固：区分可重试/不可重试/超时异常 ──
_RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=1, autoretry_for=_RETRYABLE)
def check_card_freshness(self, project_id: int) -> dict:
    """Check freshness of cards in a project's card pool.

    This task:
    1. Calculates freshness scores for all cards
    2. Identifies cards below threshold
    3. Marks them for retirement
    """
    logger.info("Checking card freshness for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.check_freshness(db, project_id)

    try:
        result = asyncio.run(_run())
        return {"status": "done", "project_id": project_id, "checked": result}

    except SoftTimeLimitExceeded:
        logger.error("Card freshness check timed out for project %s", project_id)
        raise

    except _RETRYABLE as exc:
        logger.exception("Card freshness check failed (retryable)")
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Card freshness check failed (non-retryable)")
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, autoretry_for=_RETRYABLE)
def retire_cards(self, project_id: int, card_ids: list[int]) -> dict:
    """Retire specified cards from the card pool.

    This task:
    1. Marks cards as retired
    2. Updates card pool statistics
    3. Triggers replacement card generation
    """
    logger.info("Retiring %d cards for project %s", len(card_ids), project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.retire_cards(db, project_id, card_ids)

    try:
        result = asyncio.run(_run())
        return {"status": "done", "project_id": project_id, "retired": result}

    except SoftTimeLimitExceeded:
        logger.error("Card retirement timed out for project %s", project_id)
        raise

    except _RETRYABLE as exc:
        logger.exception("Card retirement failed (retryable)")
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Card retirement failed (non-retryable)")
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, autoretry_for=_RETRYABLE)
def generate_replacement_cards(self, project_id: int, count: int = 5) -> dict:
    """Generate replacement cards for retired ones.

    This task:
    1. Analyzes current card pool
    2. Identifies gaps
    3. Generates new cards to fill gaps
    """
    logger.info("Generating %d replacement cards for project %s", count, project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.card_pool_service import CardPoolService

            service = CardPoolService()
            return await service.generate_replacements(db, project_id, count)

    try:
        result = asyncio.run(_run())
        return {
            "status": "done",
            "project_id": project_id,
            "generated": len(result),
        }

    except SoftTimeLimitExceeded:
        logger.error("Replacement card generation timed out for project %s", project_id)
        raise

    except _RETRYABLE as exc:
        logger.exception("Replacement card generation failed (retryable)")
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Replacement card generation failed (non-retryable)")
        return {"status": "failed", "project_id": project_id, "error": str(exc)}
