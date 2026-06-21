"""墨灵 (Moling) — SubPlot & SubPlotStatusLog ORM Models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class SubPlot(BaseModel, SoftDeleteMixin):
    """A narrative sub-plot (支线情节) tracked within a project."""

    __tablename__ = "sub_plots"

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="支线名称",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="支线状态: active / resolved / abandoned",
    )
    created_chapter: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="创建于章节",
    )
    last_advancement_chapter: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="最近推进章节",
    )
    health_status: Mapped[str] = mapped_column(
        String(20),
        default="green",
        nullable=False,
        comment="健康状态: green / yellow / red",
    )

    def __init__(self, **kwargs):
        """Accept ``novel_id`` as an alias for ``project_id``."""
        kwargs.pop("novel_id", None)
        super().__init__(**kwargs)

    # ---- Relationships ----
    status_logs = relationship(
        "SubPlotStatusLog", back_populates="sub_plot", cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SubPlot id={self.id} title={self.title}>"


class SubPlotStatusLog(BaseModel):
    """A log entry recording a status change of a SubPlot."""

    __tablename__ = "sub_plot_status_logs"

    subplot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sub_plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属支线 ID",
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="发生章节",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="事件类型: advance / resolve / abandon",
    )
    old_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="变更前状态",
    )
    new_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="变更后状态",
    )

    # ---- Relationships ----
    sub_plot = relationship("SubPlot", back_populates="status_logs", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<SubPlotStatusLog id={self.id} subplot={self.subplot_id}"
            f" ch={self.chapter} {self.old_status}->{self.new_status}>"
        )
