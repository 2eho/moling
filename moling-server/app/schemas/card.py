"""墨灵 (Moling) — Card / Card Draw Pydantic Schemas."""

from __future__ import annotations


from pydantic import BaseModel, Field


class DrawCardReq(BaseModel):
    """Request body for card draw operation."""

    chapter_id: str = Field(
        default="", description="章节 ID（前端必传）"
    )
    keep_card_ids: list[str] = Field(
        default=[], description="要保留的卡片 ID 列表"
    )
    draw_count: int = Field(
        default=3, ge=1, le=10, description="抽卡数量"
    )
    weights: list[float] = Field(
        default=[], description="各卡片的抽取权重"
    )
    mode: str = Field(
        default="single",
        pattern=r"^(none|single|dual|all|hybrid)$",
        description="抽取模式",
    )


class CardResp(BaseModel):
    """Card response (public-facing)."""

    id: str = Field(..., description="卡片 ID (UUID)")
    project_id: str = Field(..., description="所属项目 ID")
    name: str = Field(..., description="卡片名称")
    description: str = Field(..., description="卡片描述")
    rarity: str = Field(..., description="稀有度")
    direction_type: str = Field(..., description="方向类型")
    direction_text: str = Field(..., description="方向指示文本")
    freshness_chapter: int | None = Field(default=None, description="新鲜度章节号")
    status: str = Field(default="active", description="卡片状态")

    model_config = {"from_attributes": True}


class DrawCardResp(BaseModel):
    """Response for a successful card draw."""

    cards: list[CardResp] = Field(..., description="本次抽到的卡片列表")
    draw_round: int = Field(..., description="当前抽卡轮次")
    remaining_redraws: int = Field(..., description="剩余重抽次数")
    recommended: list[CardResp] = Field(default=[], description="推荐保留的卡片")
    pity_triggered: bool = Field(default=False, description="是否触发保底机制")


class CardPoolListResp(BaseModel):
    """Response for card pool listing."""

    cards: list[CardResp] = Field(default=[], description="卡片列表")
    total_count: int = Field(default=0, description="卡片总数")
    by_rarity: dict[str, int] = Field(default_factory=dict, description="按稀有度分类统计")
