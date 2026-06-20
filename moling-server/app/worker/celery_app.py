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

# ── Celery configuration ──
celery_app.conf.update(
    # ── Serialization ──
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # ── Reliability ──
    task_track_started=True,
    task_acks_late=True,            # 任务完成后才确认，防止 worker 崩溃丢失
    worker_prefetch_multiplier=1,   # 每次只取 1 个任务，避免长任务堆积
    result_expires=3600 * 24 * 7,   # 结果保留 7 天
    # ── P1 加固：超时控制 ──
    task_time_limit=600,            # 硬超时 10 分钟（SIGKILL，不可捕获）
    task_soft_time_limit=540,       # 软超时 9 分钟（抛出 SoftTimeLimitExceeded，可捕获清理）
    # ── P1 加固：任务队列分离 ──
    # LLM 耗时任务（pipeline 可达 5-10 分钟）路由到独立队列，
    # 避免阻塞 health / import 等实时短任务
    task_create_missing_queues=True,
    task_default_queue="default",
    task_routes={
        "app.worker.tasks.run_generation_task": {"queue": "llm"},
    },
    # ── P1 加固：故障恢复 ──
    task_reject_on_worker_lost=True,    # worker 丢失时自动重新投递
    # 死信等效配置（Redis broker 不支持 RabbitMQ 的 x-dead-letter-exchange，
    # 通过 visibility_timeout + task 级 max_retries 实现等效行为）
    broker_transport_options={
        "visibility_timeout": 3600,     # 1 小时；超时后未 ack 的任务重新入队
    },
    worker_max_tasks_per_child=50,      # 每 worker 处理 50 个任务后重启，防止内存泄漏
    task_store_errors_even_if_ignored=True,
)
