"""
墨灵 (Moling) — Phase 4 自动收纳任务.

定时执行 Phase 4 自动收纳流程：
- 触发卡池分析
- 执行四库更新
- 卡牌充实
- 健康检查
"""

from __future__ import annotations

import asyncio
import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def run_phase4_analysis(self, project_id: int) -> dict:
    """Trigger Phase 4 analysis for a project.

    This task:
    1. Analyzes the card pool
    2. Identifies entities to store in vault
    3. Updates vault entries
    """
    logger.info("Starting Phase 4 analysis for project %s", project_id)

    try:
        from app.service.phase4_service import Phase4Service

        service = Phase4Service()
        result = asyncio.run(
            asyncio.ensure_future(service.analyze_project(project_id))
        )

        logger.info("Phase 4 analysis completed for project %s", project_id)
        return {"status": "done", "project_id": project_id, "result": result}

    except Exception as exc:
        logger.exception("Phase 4 analysis failed for project %s", project_id)
        raise self.retry(exc=exc) from exc
