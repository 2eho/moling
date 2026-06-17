"""任务存储模块 - 用于异步 AI 生成任务管理。

MVP 版本使用内存存储，生产环境建议迁移到 Redis 或 PostgreSQL。
"""

from typing import Dict, Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """任务状态枚举。"""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# 内存存储（MVP 用，生产环境改用 Redis/PostgreSQL）
jobs_store: Dict[str, dict] = {}


def create_job(job_id: str, chapter_id: int, user_id: str) -> dict:
    """创建新任务并记录到存储中。
    
    Args:
        job_id: 任务唯一标识符
        chapter_id: 关联的章节 ID
        user_id: 发起任务的用户 ID
        
    Returns:
        创建的任务字典
    """
    jobs_store[job_id] = {
        "job_id": job_id,
        "chapter_id": chapter_id,
        "user_id": user_id,
        "status": JobStatus.pending,
        "progress": {"percent": 0, "stage": "等待中..."},
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return jobs_store[job_id]


def get_job(job_id: str) -> Optional[dict]:
    """根据任务 ID 获取任务信息。
    
    Args:
        job_id: 任务唯一标识符
        
    Returns:
        任务字典，如果不存在则返回 None
    """
    return jobs_store.get(job_id)


def update_job(job_id: str, **kwargs) -> Optional[dict]:
    """更新任务信息。
    
    Args:
        job_id: 任务唯一标识符
        **kwargs: 要更新的字段（如 status, progress, result, error 等）
        
    Returns:
        更新后的任务字典，如果任务不存在则返回 None
    """
    if job_id in jobs_store:
        jobs_store[job_id].update(kwargs)
        jobs_store[job_id]["updated_at"] = datetime.utcnow().isoformat()
        return jobs_store[job_id]
    return None
