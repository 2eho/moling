"""墨灵 (Moling) — DynamicLayer (动态层) ORM Model."""

from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DynamicLayer(BaseModel):
    """动态层数据 - 每章更新的流动事实层.

    存储章节的动态层数据，包括前情摘要、章节锚点、连贯性基线、
    未收束钩子、最近3章变更、秘密矩阵等。
    """

    __tablename__ = "dynamic_layers"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter_id: Mapped[str] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属章节 ID",
    )
    # 前情摘要
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="前情摘要 - 故事到哪了的自然语言总结",
    )
    # 章节锚点
    anchor_pov: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="POV - 视点角色",
    )
    anchor_location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="地点 - 场景位置",
    )
    anchor_time: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="时间 - 场景时间",
    )
    # 连贯性基线
    must_hold: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="必须保持的约束列表",
    )
    must_not: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="必须避免的约束列表",
    )
    # 未收束钩子
    unresolved_hooks: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="未解决的悬念列表",
    )
    # 最近3章变更
    recent_changes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="最近3章的变更日志",
    )
    # 秘密矩阵 (信息不对称)
    information_asymmetry: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="秘密矩阵 - 谁知道什么/谁还不知道",
    )
    # 可行性评分
    feasibility_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="可行性评分 (0-1)",
    )
    # 健康检查结果 (参考 §5.3.5)
    health_check: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="健康检查结果 (R1/R2/R3 告警)",
    )

    # ---- Relationships ----
    project = relationship("Project", back_populates="dynamic_layers", lazy="selectin")
    chapter = relationship("Chapter", back_populates="dynamic_layer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DynamicLayer id={self.id} chapter={self.chapter_id}>"
