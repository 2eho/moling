"""
墨灵 (Moling) — Celery Application Instance.

Configured from ``app.config.Settings``.  The broker defaults to Redis on
localhost; override via the ``CELERY_BROKER_URL`` environment variable.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "moling",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks",
        "app.worker.phase4_task",
        "app.worker.import_task",
        "app.worker.book_analysis_task",
        "app.worker.card_retire_task",
        "app.worker.vault_reanalyze_task",
    ],
)

# Optional Celery configuration overrides
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600 * 24 * 7,  # 7 days
)
