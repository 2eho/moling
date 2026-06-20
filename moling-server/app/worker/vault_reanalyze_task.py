"""
墨灵 (Moling) — Vault Full Reanalysis Task.

Background Celery task for re-analyzing all chapters in a project
and rebuilding the Four Databases (四库).
"""

from __future__ import annotations

import asyncio
import logging

# ── HH8: SoftTimeLimitExceeded ──
from celery.exceptions import SoftTimeLimitExceeded
# ── HH7: 可重试异常 vs 不可重试异常 ──
from sqlalchemy.exc import SQLAlchemyError

from app.worker.celery_app import celery_app
from app.worker.db import get_worker_session
# ── HH6: 幂等性检查 ──
from app.worker.idempotency import is_duplicate, mark_completed, mark_failed as idem_mark_failed

logger = logging.getLogger(__name__)

# ── 可重试异常（网络、DB连接等瞬态问题） ──
_RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120,
                 autoretry_for=_RETRYABLE)
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
    task_key = f"vlt:{project_id}:reanalyze"

    # ── HH6: 幂等性检查 ──
    if is_duplicate(task_key):
        logger.info("Task vault_full_reanalyze already processed for project %s, skipping",
                     project_id)
        return {"status": "already_processed", "project_id": project_id}

    logger.info(
        "Starting full reanalysis for project %s (user: %s)", project_id, user_id
    )

    async def _reanalyze() -> dict:
        from app.dao import project_dao, chapter_dao
        from app.service.vault_service import VaultService

        async with get_worker_session() as db:
            # Verify project exists
            project = await project_dao.get(db, project_id)
            if project is None:
                raise ValueError(f"Project {project_id} not found")

            # Get all chapters via DAO
            chapters = await chapter_dao.get_by_project(db, project_id)

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
                        db=db,
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
                        "chapter_number": getattr(chapter, 'chapter_number', 0),
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

    try:
        result = asyncio.run(_reanalyze())

        logger.info(
            "Full reanalysis completed for project %s: %s chapters, "
            "%s created, %s updated",
            project_id,
            result["total_chapters"],
            result["total_created"],
            result["total_updated"],
        )

        mark_completed(task_key)
        return result

    except SoftTimeLimitExceeded:
        logger.error("Task vault_full_reanalyze timed out for project %s", project_id)
        idem_mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Full reanalysis failed with retryable error for project %s", project_id)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Full reanalysis failed with non-retryable error for project %s", project_id)
        idem_mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=600, autoretry_for=_RETRYABLE)
def vault_periodic_reanalyze(self) -> dict:
    """Celery Beat 定时任务：定期扫描项目，对活跃项目触发 Vault 重分析。

    每 6 小时执行一次，由 Celery Beat 调度触发。
    查找最近 6 小时内有章节更新的项目，触发 vault_full_reanalyze。
    """
    logger.info("Vault periodic reanalyze: starting scan")

    async def _run():
        async with get_worker_session() as db:
            from app.dao import project_dao

            projects = await project_dao.get_recently_active(db, hours=6)
            triggered = 0

            for project in projects:
                try:
                    # 异步触发重分析（不等待结果，避免阻塞扫描）
                    vault_full_reanalyze.delay(project_id=project.id, user_id="system")
                    triggered += 1
                except Exception as e:
                    logger.warning("Failed to trigger reanalyze for project %s: %s", project.id, e)

            return {"scanned": len(projects), "triggered": triggered}

    try:
        result = asyncio.run(_run())
        logger.info("Vault periodic reanalyze completed: %s projects triggered", result["triggered"])
        return {"status": "done", **result}

    except SoftTimeLimitExceeded:
        logger.error("Vault periodic reanalyze timed out")
        raise

    except _RETRYABLE as exc:
        logger.exception("Vault periodic reanalyze failed (retryable)")
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Vault periodic reanalyze failed (non-retryable)")
        return {"status": "failed", "error": str(exc)}
