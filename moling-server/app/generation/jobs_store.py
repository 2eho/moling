"""任务存储模块 - 异步 AI 生成任务管理。

使用 GenerationTask ORM 模型 + PostgreSQL 持久化。
不再使用内存 dict 存储任务状态。
"""

from enum import Enum

from app.models.generation_task import GenerationTask


class JobStatus(str, Enum):
    """任务状态枚举（与 GenerationTask.status 字段对应）。
    
    注意：GenerationTask 中使用 "done" 表示完成状态，
    而非本枚举中的 "completed"，映射时需转换。
    """
    pending = "pending"
    running = "running"
    completed = "completed"       # API 输出时映射为 "done"
    failed = "failed"
    cancelled = "cancelled"


# GenerationTask.status -> JobStatus 映射表
_STATUS_MAP = {
    "pending": JobStatus.pending,
    "running": JobStatus.running,
    "done": JobStatus.completed,
    "failed": JobStatus.failed,
    "cancelled": JobStatus.cancelled,
}


def task_to_dict(task: GenerationTask) -> dict:
    """将 GenerationTask ORM 模型转换为前端期望的 dict 格式。
    
    Args:
        task: GenerationTask ORM 实例
        
    Returns:
        与旧版内存存储相同结构的 dict
    """
    return {
        "job_id": task.id,
        "chapter_id": task.chapter_id,
        "user_id": task.user_id,
        "status": _STATUS_MAP.get(task.status, task.status),
        "progress": {
            "percent": task.progress_percent,
            "stage": task.progress_stage or "等待中...",
        },
        "result": task.output_data,
        "error": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
