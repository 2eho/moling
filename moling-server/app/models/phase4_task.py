"""墨灵 (Moling) — Phase 4 Task ORM Model.

用于 Phase 4 调度器的幂等性检查和任务追踪（§12.5）。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Phase4State(str, Enum):
    """Phase 4 调度器完整状态机定义 (§12.1)."""

    IDLE = "idle"                # 初始状态，等待任务
    QUEUED = "queued"            # 已入队列
    LOCKING = "locking"          # 获取分布式锁
    EXTRACTING = "extracting"    # 调用 LLM 提取
    VERIFYING = "verifying"      # SourceText/Grounding 验证
    MERGING = "merging"          # 四库合并
    COMMITTING = "committing"    # 事务提交
    DONE = "done"                # 完成
    FAILED = "failed"            # 失败（不可恢复）
    RETRY = "retry"              # 可重试失败


class Phase4Task(Base, TimestampMixin):
    """Phase 4 任务记录，用于幂等性检查和状态机追踪。

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
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目 ID",
    )
    chapter_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="章节 ID (UUID)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="任务状态: pending / running / done / failed",
    )
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=Phase4State.IDLE.value,
        comment="状态机状态: idle/queued/locking/extracting/verifying/merging/committing/done/failed/retry",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息 (任务失败时)",
    )
    safety_check: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="SourceText 内容安全验证结果 (§11.6)",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="重试次数 (最多 5 次)",
    )
    retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="下次重试时间 (指数退避)",
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="最后一次错误信息",
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
        return f"<Phase4Task nonce={self.nonce} state={self.state}>"
