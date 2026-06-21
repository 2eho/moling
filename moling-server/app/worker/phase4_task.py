"""
墨灵 (Moling) — Phase 4 自动收纳任务.

定时执行 Phase 4 自动收纳流程：
- 触发卡池分析
- 执行四库更新
- 卡牌充实
- 健康检查

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


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300, autoretry_for=_RETRYABLE)
def run_phase4_analysis(self, project_id: int) -> dict:
    """Trigger Phase 4 analysis for a project.

    This task:
    1. Analyzes the card pool
    2. Identifies entities to store in vault
    3. Updates vault entries
    """
    task_key = f"task:{project_id}:run_phase4_analysis"
    if is_duplicate(task_key):
        return {"status": "already_processed", "project_id": project_id}

    logger.info("Starting Phase 4 analysis for project %s", project_id)

    async def _run():
        async with get_worker_session() as db:
            from app.service.phase4_service import Phase4Service

            service = Phase4Service()
            return await service.analyze_project(db, project_id)

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        logger.info("Phase 4 analysis completed for project %s", project_id)
        return {"status": "done", "project_id": project_id, "result": result}

    except SoftTimeLimitExceeded:
        logger.error("Phase 4 analysis timed out for project %s", project_id)
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Phase 4 analysis failed (retryable) for project %s", project_id)
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Phase 4 analysis failed (non-retryable) for project %s", project_id)
        mark_failed(task_key)
        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=600, autoretry_for=_RETRYABLE)
def phase4_auto_advance(self) -> dict:
    """Celery Beat 定时任务：扫描所有启用了自动审核的项目，触发 Phase 4 自动推进。

    每小时执行一次，由 Celery Beat 调度触发。
    查找 phase4_review_mode="auto" 的项目，检查是否有待推进的章节，
    如有则触发 Phase 4 分析流水线。
    """
    task_key = f"task:beat:phase4_auto_advance:{datetime.now().strftime('%Y-%m-%d-%H')}"
    if is_duplicate(task_key):
        return {"status": "already_processed"}

    logger.info("Phase 4 auto-advance: starting periodic scan")

    async def _run():
        async with get_worker_session() as db:
            from app.dao import project_dao
            from app.service.phase4_service import Phase4Service

            # 查找所有活跃项目
            projects = await project_dao.get_all_active(db)
            service = Phase4Service()
            results = []

            for project in projects:
                try:
                    # 检查项目是否设置了自动审核模式
                    if getattr(project, "phase4_review_mode", "manual") == "auto":
                        logger.debug("Auto-advancing project %s", project.id)
                        result = await service.analyze_project(db, project.id)
                        results.append({"project_id": project.id, "status": "done", "result": result})
                except Exception as e:
                    logger.warning("Auto-advance failed for project %s: %s", project.id, e)
                    results.append({"project_id": project.id, "status": "failed", "error": str(e)})

            return {"scanned": len(projects), "processed": len(results), "results": results}

    try:
        result = asyncio.run(_run())
        mark_completed(task_key)
        logger.info("Phase 4 auto-advance completed: scanned %s projects", result["scanned"])
        return {"status": "done", **result}

    except SoftTimeLimitExceeded:
        logger.error("Phase 4 auto-advance timed out")
        mark_failed(task_key)
        raise

    except _RETRYABLE as exc:
        logger.exception("Phase 4 auto-advance failed (retryable)")
        mark_failed(task_key)
        raise self.retry(exc=exc) from exc

    except Exception as exc:
        logger.exception("Phase 4 auto-advance failed (non-retryable)")
        mark_failed(task_key)
        return {"status": "failed", "error": str(exc)}
