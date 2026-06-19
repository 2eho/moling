"""
墨灵 (Moling) — Vault Full Reanalysis Task.

Background Celery task for re-analyzing all chapters in a project
and rebuilding the Four Databases (四库).
"""

from __future__ import annotations

import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def vault_full_reanalyze(self, project_id: int, user_id: str) -> dict:
    """Full reanalysis of all chapters in a project.

    This task:
    1. Fetches all chapters for the project
    2. Extracts entities (characters, locations, items) from each chapter
    3. Updates the Four Databases (characters, timeline, plot promises, world)
    4. Returns summary of changes

    Args:
        project_id: The project ID to reanalyze.
        user_id: The user ID who initiated the reanalysis.
    """
    logger.info(
        "Starting full reanalysis for project %s (user: %s)", project_id, user_id
    )

    try:
        import asyncio
        from sqlalchemy import select, func
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from app.config import get_settings
        from app.dao import chapter_dao, project_dao
        from app.models.chapter import Chapter
        from app.service.vault_service import VaultService

        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        SessionLocal = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async def _reanalyze() -> dict:
            async with SessionLocal() as db:
                # Verify project exists
                project = await project_dao.get(db, project_id)
                if project is None:
                    raise ValueError(f"Project {project_id} not found")

                # Get all chapters
                stmt = (
                    select(Chapter)
                    .where(Chapter.project_id == project_id)
                    .order_by(Chapter.chapter_number)
                )
                result = await db.execute(stmt)
                chapters = list(result.scalars().all())

                if not chapters:
                    return {
                        "status": "done",
                        "project_id": project_id,
                        "total_chapters": 0,
                        "total_created": 0,
                        "total_updated": 0,
                        "message": "No chapters found in project",
                    }

                vault = VaultService()
                total_created = 0
                total_updated = 0
                total_entities = 0
                chapter_results = []

                for chapter in chapters:
                    try:
                        r = await vault.update_from_chapter(
                            project_id=project_id,
                            chapter_id=chapter.id,
                        )
                        chapter_results.append(r)
                        total_created += r.get("created", 0)
                        total_updated += r.get("updated", 0)
                        total_entities += r.get("total_entities", 0)
                    except Exception as e:
                        logger.warning(
                            "Failed to reanalyze chapter %s: %s", chapter.id, e
                        )
                        chapter_results.append({
                            "chapter_id": chapter.id,
                            "chapter_number": chapter.chapter_number,
                            "error": str(e),
                        })

                return {
                    "status": "done",
                    "project_id": project_id,
                    "total_chapters": len(chapters),
                    "total_created": total_created,
                    "total_updated": total_updated,
                    "total_entities_found": total_entities,
                    "chapter_results": chapter_results,
                    "message": (
                        f"Reanalysis complete: {len(chapters)} chapters processed, "
                        f"{total_created} created, {total_updated} updated"
                    ),
                }

        result = asyncio.run(_reanalyze())

        logger.info(
            "Full reanalysis completed for project %s: %s chapters, "
            "%s created, %s updated",
            project_id,
            result["total_chapters"],
            result["total_created"],
            result["total_updated"],
        )

        return result

    except Exception as exc:
        logger.exception("Full reanalysis failed for project %s", project_id)
        raise self.retry(exc=exc) from exc
