"""
墨灵 (Moling) — Import Tasks.

Background tasks for importing novels/books:
- Parse uploaded files
- Extract chapters
- Analyze content
- Create project structure
"""

from __future__ import annotations

import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def import_book_task(self, project_id: int, file_path: str, import_mode: str) -> dict:
    """Import a book from file.

    This task:
    1. Parse the uploaded file (txt, docx, epub)
    2. Split into chapters
    3. Extract metadata
    4. Create project and chapters
    """
    logger.info("Starting book import for project %s from %s", project_id, file_path)

    try:
        import asyncio
        from app.service.import_service import ImportService

        service = ImportService()
        result = asyncio.run(service.import_book(project_id, file_path, import_mode))

        logger.info("Book import completed for project %s", project_id)
        return {"status": "done", "project_id": project_id, "result": result}

    except Exception as exc:
        logger.exception("Book import failed for project %s", project_id)
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True)
def analyze_import_content(self, project_id: int) -> dict:
    """Analyze imported content for suggestions.

    This task:
    1. Analyzes chapter structure
    2. Extracts style information
    3. Generates import suggestions
    """
    logger.info("Analyzing import content for project %s", project_id)

    try:
        import asyncio
        from app.service.import_service import ImportService

        service = ImportService()
        result = asyncio.run(service.analyze_content(project_id))

        return {"status": "done", "project_id": project_id, "analysis": result}

    except Exception as exc:
        logger.exception("Import analysis failed")
        raise self.retry(exc=exc) from exc
