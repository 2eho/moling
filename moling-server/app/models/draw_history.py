"""墨灵 (Moling) — Draw History (抽卡历史) ORM Model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DrawHistory(BaseModel):
    """Record of a card draw action by a user (draw_history)."""

    __tablename__ = "draw_history"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联章节 ID (可为空)",
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="抽卡用户 ID",
    )
    # B10: 补充 cards_drawn 快照
    cards_drawn: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="抽取的卡片快照列表",
    )
    card_ids: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [],
        comment="抽取的卡片 ID 列表",
    )
    weights: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [],
        comment="各卡片的权重",
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        default="single",
        nullable=False,
        comment="抽取模式: none / single / dual / all / hybrid",
    )
    draw_round: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="当前是第几轮抽卡 (1-based)",
    )
    remaining_redraws: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="剩余重抽次数",
    )
    drawn_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="抽卡时间",
    )

    # ---- Relationships ----
    project = relationship("Project", back_populates="draw_histories", lazy="selectin")
    chapter = relationship("Chapter", back_populates="draw_histories", lazy="selectin")
    user = relationship("User", back_populates="draw_histories", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DrawHistory id={self.id} project={self.project_id} round={self.draw_round}>"
