"""墨灵 (Moling) — Generation Task ORM Model."""

import uuid
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GenerationTask(Base, TimestampMixin):
    """An AI generation / revision task.

    Unlike most models, ``id`` is a UUID string (not auto-increment integer)
    so that the frontend can display a stable task reference immediately.
    """

    __tablename__ = "generation_tasks"

    id: Mapped[str] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        comment="任务唯一标识 (UUID)",
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联章节 ID (可为空)",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="发起任务用户 ID",
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="任务类型: generate / phase4 / revise / analyze",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="任务状态: pending / running / done / failed / cancelled",
    )
    input_params: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="输入参数 (JSON)",
    )
    output_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="输出数据 (JSON, 任务完成时填充)",
    )
    progress_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="当前进度阶段描述",
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="进度百分比 0-100",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息 (任务失败时)",
    )

    def __repr__(self) -> str:
        return f"<GenerationTask id={self.id} type={self.task_type} status={self.status}>"
