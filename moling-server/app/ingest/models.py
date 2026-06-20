"""
墨灵 (Moling) — Ingest 数据模型

记录连载书导入任务的状态和进度。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class IngestJob(BaseModel):
    """连载书导入任务 — 追踪整个导入流程的状态。"""

    __tablename__ = "ingest_jobs"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="发起导入的用户 ID",
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="导入来源: url / html / text / file",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="来源 URL（可选）",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        default="",
        nullable=False,
        comment="导入作品名称",
    )
    total_chapters: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="总章节数",
    )
    current_phase: Mapped[str] = mapped_column(
        String(20),
        default="phase0",
        nullable=False,
        comment="当前阶段: phase0 / phase1 / phase2 / phase3 / completed / failed",
    )
    phase0_result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Phase 0 拆解结果缓存",
    )
    phase1_result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Phase 1 四库分析结果缓存",
    )
    phase2_result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Phase 2 动态层分析结果缓存",
    )
    phase3_result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Phase 3 导入结果",
    )
    progress_percent: Mapped[float] = mapped_column(
        Float(precision=2),
        default=0.0,
        nullable=False,
        comment="当前阶段进度百分比",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )

    def __repr__(self) -> str:
        return f"<IngestJob id={self.id} project={self.project_id} phase={self.current_phase}>"
