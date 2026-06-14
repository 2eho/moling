"""
墨灵 (Moling) — Card Retire Tasks.

Background tasks for card lifecycle management:
- Check card freshness
- Retire old cards
- Generate replacement cards
- Update card pool statistics
"""

from __future__ import annotations

import logging

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1)
def check_card_freshness(self, project_id: int) -> dict:
    """Check freshness of cards in a project's card pool.

    This task:
    1. Calculates freshness scores for all cards
    2. Identifies cards below threshold
    3. Marks them for retirement
    """
    logger.info("Checking card freshness for project %s", project_id)

    try:
        from app.service.card_pool_service import CardPoolService

        service = CardPoolService()
        result = service.check_freshness(project_id)

        return {"status": "done", "project_id": project_id, "checked": result}

    except Exception as exc:
        logger.exception("Card freshness check failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=1)
def retire_cards(self, project_id: int, card_ids: list[int]) -> dict:
    """Retire specified cards from the card pool.

    This task:
    1. Marks cards as retired
    2. Updates card pool statistics
    3. Triggers replacement card generation
    """
    logger.info("Retiring %d cards for project %s", len(card_ids), project_id)

    try:
        from app.service.card_pool_service import CardPoolService

        service = CardPoolService()
        result = service.retire_cards(project_id, card_ids)

        return {"status": "done", "project_id": project_id, "retired": result}

    except Exception as exc:
        logger.exception("Card retirement failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=1)
def generate_replacement_cards(self, project_id: int, count: int = 5) -> dict:
    """Generate replacement cards for retired ones.

    This task:
    1. Analyzes current card pool
    2. Identifies gaps
    3. Generates new cards to fill gaps
    """
    logger.info("Generating %d replacement cards for project %s", count, project_id)

    try:
        from app.service.card_pool_service import CardPoolService

        service = CardPoolService()
        result = service.generate_replacements(project_id, count)

        return {
            "status": "done",
            "project_id": project_id,
            "generated": len(result),
        }

    except Exception as exc:
        logger.exception("Replacement card generation failed")
        raise self.retry(exc=exc) from exc
