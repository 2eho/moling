"""
墨灵 (Moling) — Book Analysis Tasks.

Background tasks for analyzing books:
- Character extraction
- Plot analysis
- Style detection
- World-building analysis

Note: The BookAnalysisService methods are synchronous (internally bridge
async DAO calls via asyncio.run), so these Celery tasks call them directly
without need for an explicit asyncio wrapper.
"""

from __future__ import annotations

import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1)
def analyze_book_characters(self, project_id: int) -> dict:
    """Analyze characters in a book."""
    logger.info("Analyzing characters for project %s", project_id)

    try:
        from app.service.book_analysis_service import BookAnalysisService

        service = BookAnalysisService()
        result = service.analyze_characters(project_id)

        return {"status": "done", "project_id": project_id, "characters": result}

    except Exception as exc:
        logger.exception("Character analysis failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=1)
def analyze_book_plot(self, project_id: int) -> dict:
    """Analyze plot structure of a book."""
    logger.info("Analyzing plot for project %s", project_id)

    try:
        from app.service.book_analysis_service import BookAnalysisService

        service = BookAnalysisService()
        result = service.analyze_plot(project_id)

        return {"status": "done", "project_id": project_id, "plot": result}

    except Exception as exc:
        logger.exception("Plot analysis failed")
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True, max_retries=1)
def detect_writing_style(self, project_id: int) -> dict:
    """Detect writing style of a book."""
    logger.info("Detecting writing style for project %s", project_id)

    try:
        from app.service.book_analysis_service import BookAnalysisService

        service = BookAnalysisService()
        result = service.detect_style(project_id)

        return {"status": "done", "project_id": project_id, "style": result}

    except Exception as exc:
        logger.exception("Style detection failed")
        raise self.retry(exc=exc) from exc
