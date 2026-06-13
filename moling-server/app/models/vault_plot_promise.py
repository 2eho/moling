"""墨灵 (Moling) — Vault Plot Promise (伏笔/情节承诺) ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class VaultPlotPromise(BaseModel):
    """A plot promise / foreshadowing element that tracks narrative debt."""

    __tablename__ = "vault_plot_promises"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    # B8: 补充缺失字段
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="承诺标题",
    )
    redeem_window: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="兑现窗口 (章节数)",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="置信度 (0-1)",
    )
    # 原有字段 - B8: 枚举值对齐
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="伏笔/承诺描述",
    )
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="类型: mystery / promise / foreshadowing / arc / subplot",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="dormant",
        nullable=False,
        comment="状态: dormant / active / advancing / resolved / abandoned",
    )
    urgency: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="紧迫度 0-10",
    )
    related_characters: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="相关角色名列表",
    )
    planted_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="埋下伏笔的章节号",
    )
    advancement_log: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="推进日志 (事件列表, 含 event_type)",
    )

    def __repr__(self) -> str:
        return f"<VaultPlotPromise id={self.id} type={self.type} status={self.status}>"
