"""墨灵 (Moling) — Phase 4 Task ORM Model.

用于 Phase 4 调度器的幂等性检查和任务追踪（§12.5）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Phase4Task(Base, TimestampMixin):
    """Phase 4 任务记录，用于幂等性检查。

    三层幂等性防护（§12.5）：
    - Layer 1: Redis SISMEMBER executed_nonces <nonce> (快速检查)
    - Layer 2: DB 查询 phase4_tasks 表 (Redis 重启保护)
    - Layer 3: DB UNIQUE 约束 (永不失效)
    """

    __tablename__ = "phase4_tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="任务 ID",
    )
    nonce: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="幂等性令牌 (格式: ch${chapter}_${timestamp})",
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="项目 ID",
    )
    chapter_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="章节 ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="任务状态: pending / running / done / failed",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息 (任务失败时)",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始执行时间",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间",
    )

    def __repr__(self) -> str:
        return f"<Phase4Task nonce={self.nonce} status={self.status}>"
