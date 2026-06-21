"""墨灵 (Moling) — CardPool (卡池) ORM Model."""

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class CardPool(BaseModel, SoftDeleteMixin):
    """A direction card in a project's card pool.

    卡片池存储用于生成章节灵感的卡片。
    每张卡片包含一个方向文本和方向类型，用户可以通过抽卡来获取创作灵感。
    """

    __tablename__ = "card_pools"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    # B4: 补充缺失字段
    type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="卡片类型: 系统生成 / 用户创建 / 导入",
    )
    source_label: Mapped[str] = mapped_column(
        String(50),
        default="初始卡池",
        nullable=False,
        comment="来源标签",
    )
    pick_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="被选取次数",
    )
    last_drawn_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="最后抽取章节号",
    )
    source_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="来源章节号 (Phase 4 自动生成时记录)",
    )
    tags: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="标签数组",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="是否激活 ( retired 后设为 False)",
    )
    retired_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="退役章节号",
    )
    # 原有字段
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="卡片名称",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="卡片描述",
    )
    rarity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="稀有度: common / rare / epic / legendary",
    )
    # B4: direction_type 枚举值对齐
    direction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="方向类型: 稳妥 / 有趣 / 惊艳 / 神之一手",
    )
    direction_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="方向指示文本",
    )
    # B13: 补充 8 个算法字段
    rarity_weight: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="稀有度权重: 1 / 2 / 3 / 4",
    )
    characters: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="关联角色列表 [{id, name, state_requirement}]",
    )
    plot_promises: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="关联剧情承诺列表 [{id, title, advance_type}]",
    )
    timeline_point: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="时间线关键点",
    )
    world_rules: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="关联世界观规则列表 [{id, rule, constraint}]",
    )
    current_story_state: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="当前故事状态",
    )
    unresolved_hooks: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="未收束钩子列表",
    )
    dynamic_conflict_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="动态冲突评分 (0-1)",
    )
    # 生命周期字段
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="状态: active / retired / archived",
    )
    freshness_chapter: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="新鲜度章节号 (卡片创建时章节)",
    )
    draw_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="被抽取次数",
    )
    remaining_lifetime: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="剩余寿命 (章节数, 过期后失效)",
    )
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        JSON,
        nullable=True,
        comment="语义嵌入向量 (1536 维, JSON 数组)",
    )

    # ---- Relationships ----
    project = relationship("Project", back_populates="card_pools", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CardPool id={self.id} name={self.name!r} rarity={self.rarity}>"
