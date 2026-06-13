"""
墨灵 (Moling) — Celery Worker Package.

Background task processing for AI generation and revision tasks.
"""

from app.worker.celery_app import celery_app
from app.worker.tasks import run_generation_task

__all__ = [
    "celery_app",
    "run_generation_task",
]
