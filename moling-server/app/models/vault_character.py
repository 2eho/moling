"""墨灵 (Moling) — Vault Character (角色库) ORM Model."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class VaultCharacter(BaseModel, SoftDeleteMixin):
    """A character managed in the project's vault."""

    __tablename__ = "vault_characters"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="角色名称",
    )
    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="角色定位: protagonist / ally / neutral / opponent / antagonist",
    )
    faction: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="所属阵营/势力",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="角色状态: active / inactive / deceased",
    )
    # B5: 补充缺失字段
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="当前位置",
    )
    appearance: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="外貌描述",
    )
    personality: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="性格描述",
    )
    knowledge: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="知识/能力列表",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="置信度 (0-1)",
    )
    chapter_hist: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="章节历史 (出场章节列表)",
    )
    current_state: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="当前状态",
    )
    motivation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="动机/目标",
    )
    # 原有字段
    emotion: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="当前情绪状态",
    )
    traits: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="性格特征数组",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="角色描述",
    )
    background: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="角色背景故事",
    )
    relationships: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [],
        comment="人际关系 (JSON 数组)",
    )
    state_machine: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="状态机数据 (情感/状态转换)",
    )
    chapter_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="已出场章节数",
    )
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        JSON,
        nullable=True,
        comment="语义嵌入向量 (JSON 数组)",
    )

    def __repr__(self) -> str:
        return f"<VaultCharacter id={self.id} name={self.name!r}>"
