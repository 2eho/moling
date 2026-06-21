"""
墨灵 (Moling) — Ingest 引擎 Pydantic 数据模型

定义 Phase 间传递数据的类型安全模型。
所有 Phase 入口/出口均使用 Pydantic BaseModel，替代原先的裸 dict 传递。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════
# Phase 1 — 提取结果（单章级别）
# ══════════════════════════════════════════════════════════════════════


class CharacterExtractionData(BaseModel):
    """I1 角色提取 — 单章结果"""

    name: str = Field(description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="角色别名列表")
    dialogue_count: int = Field(default=0, description="对话句数")
    description: str = Field(default="", description="角色描述")
    tags: list[str] = Field(default_factory=list, description="角色标签（主角/反派/盟友等）")
    chapter_index: int = Field(default=0, description="所属章节索引")


class TimelineExtractionData(BaseModel):
    """I2 时间线提取 — 单章结果"""

    description: str = Field(description="事件描述")
    relative_time: str = Field(default="", description="相对时间")
    time_anchor: str = Field(default="", description="时间锚点")
    characters: list[str] = Field(default_factory=list, description="涉及角色")
    importance: int = Field(default=3, description="重要性 1-5")
    chapter_index: int = Field(default=0, description="所属章节索引")


class PlotPromiseExtractionData(BaseModel):
    """I3 剧情承诺提取 — 单章结果"""

    type: str = Field(description="承诺类型: explicit_promise / implicit_promise / mystery")
    text: str = Field(description="承诺文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    related_characters: list[str] = Field(default_factory=list, description="相关角色")


class WorldExtractionData(BaseModel):
    """I4 世界观提取 — 单章结果"""

    term: str = Field(description="世界观术语")
    description: str = Field(default="", description="术语描述")
    category: str = Field(default="other", description="分类: geography / magic / technology / culture / history / rule / other")
    chapter_index: int = Field(default=0, description="所属章节索引")
    related_terms: list[str] = Field(default_factory=list, description="相关术语")


class ChapterAnalysisData(BaseModel):
    """单章的全部分析结果"""

    chapter_index: int = Field(description="章节索引")
    chapter_title: str = Field(description="章节标题")
    characters: list[CharacterExtractionData] = Field(default_factory=list, description="角色提取结果")
    timeline_events: list[TimelineExtractionData] = Field(default_factory=list, description="时间线提取结果")
    promises: list[PlotPromiseExtractionData] = Field(default_factory=list, description="剧情承诺提取结果")
    world_items: list[WorldExtractionData] = Field(default_factory=list, description="世界观提取结果")
    error: str | None = Field(default=None, description="该章错误信息")


# ══════════════════════════════════════════════════════════════════════
# Phase 1 — 合并后结果（全书级别）
# ══════════════════════════════════════════════════════════════════════


class MergedCharacterData(BaseModel):
    """合并去重后的角色"""

    name: str = Field(description="角色名称")
    aliases: list[str] = Field(default_factory=list, description="角色别名")
    first_appearance: int = Field(default=0, description="首次出场章节")
    chapters_active: list[int] = Field(default_factory=list, description="活跃章节列表")
    dialogue_count: int = Field(default=0, description="总对话数")
    description: str = Field(default="", description="角色描述")
    tags: list[str] = Field(default_factory=list, description="角色标签")


class MergedTimelineEventData(BaseModel):
    """合并后的时间线事件"""

    description: str = Field(description="事件描述")
    relative_time: str = Field(default="", description="相对时间")
    time_anchor: str = Field(default="", description="时间锚点")
    characters: list[str] = Field(default_factory=list, description="涉及角色")
    importance: int = Field(default=3, description="重要性 1-5")
    chapter_index: int = Field(default=0, description="关键章节索引")
    is_key_event: bool = Field(default=False, description="是否为关键事件")


class MergedPlotPromiseData(BaseModel):
    """合并后的剧情承诺"""

    type: str = Field(description="承诺类型")
    text: str = Field(description="承诺文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    status: str = Field(default="dormant", description="状态: dormant / active / advancing / resolved / abandoned")
    urgency: int = Field(default=5, ge=0, le=10, description="紧迫度 0-10")
    related_characters: list[str] = Field(default_factory=list, description="相关角色")


class MergedWorldItemData(BaseModel):
    """合并后的世界观条目"""

    term: str = Field(description="术语")
    description: str = Field(default="", description="描述")
    category: str = Field(default="other", description="分类")
    first_appearance: int = Field(default=0, description="首次出场章节")
    reference_chapters: list[int] = Field(default_factory=list, description="引用章节")
    related_terms: list[str] = Field(default_factory=list, description="相关术语")


# ══════════════════════════════════════════════════════════════════════
# Phase 1 — 输入 / 输出 / 进度
# ══════════════════════════════════════════════════════════════════════


class Phase1InputModel(BaseModel):
    """Phase 1 输入 — 由 Phase 0 产生的拆解结果"""

    project_id: str = Field(description="项目 ID")
    chapters: list[dict[str, Any]] = Field(description="拆解后的章节数据列表")
    total_chapters: int = Field(default=0, description="总章节数")


class Phase1ResultModel(BaseModel):
    """Phase 1 完整输出 — 全量四库分析结果"""

    characters: list[MergedCharacterData] = Field(default_factory=list, description="合并后的角色列表")
    timeline_events: list[MergedTimelineEventData] = Field(default_factory=list, description="合并后的时间线事件")
    promises: list[MergedPlotPromiseData] = Field(default_factory=list, description="合并后的剧情承诺")
    world_items: list[MergedWorldItemData] = Field(default_factory=list, description="合并后的世界观条目")
    chapter_count: int = Field(default=0, description="已分析章节数")
    total_llm_calls: int = Field(default=0, description="LLM 调用总数")
    failed_llm_calls: int = Field(default=0, description="LLM 调用失败数")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")


class Phase1ProgressModel(BaseModel):
    """Phase 1 进度（用于轮询）"""

    status: str = Field(default="pending", description="状态: pending / running / completed / failed")
    phase: str = Field(default="phase1", description="阶段标识")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    completed_chapters: int = Field(default=0, description="已完成章节数")
    total_chapters: int = Field(default=0, description="总章节数")
    failed_calls: int = Field(default=0, description="失败调用数")
    current_task: str = Field(default="", description="当前任务描述")
    result: Phase1ResultModel | None = Field(default=None, description="分析结果（完成时填入）")
    error: str | None = Field(default=None, description="错误信息")


# ══════════════════════════════════════════════════════════════════════
# Phase 2 — 输入 / 输出
# ══════════════════════════════════════════════════════════════════════


class ChapterAnchorData(BaseModel):
    """I5 章节锚点"""

    chapter_index: int = Field(description="章节索引")
    chapter_title: str = Field(description="章节标题")
    opening_hook: bool = Field(default=False, description="是否有开篇钩子")
    midpoint_turn: dict[str, Any] | None = Field(default=None, description="中点转折信息")
    closing_cliff: bool = Field(default=False, description="是否有结尾悬念")
    action_peak: float | None = Field(default=None, description="动作峰值强度")


class OpenHookData(BaseModel):
    """I7 未收束钩子"""

    type: str = Field(description="钩子类型")
    text: str = Field(description="钩子文本")
    context: str = Field(default="", description="上下文")
    chapter_index: int = Field(default=0, description="所属章节索引")
    created_at: str = Field(default="", description="创建时间")
    age_in_chapters: int = Field(default=0, description="已存在章节数")
    stale: bool = Field(default=False, description="是否已过时")


class FeasibilityReportData(BaseModel):
    """I9 可行性基线评估"""

    plot_density: float = Field(default=0.0, description="情节密度")
    loose_thread_count: int = Field(default=0, description="未收束线索数")
    continuation_confidence: float = Field(default=0.0, description="续写信心 0-1")
    coherence: dict[str, Any] = Field(default_factory=dict, description="连贯性指标")
    recommendation: str = Field(default="", description="可行性建议")


class Phase2InputModel(BaseModel):
    """Phase 2 输入"""

    chapters: list[dict[str, Any]] = Field(description="章节数据列表")
    characters: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 角色结果")
    timeline_events: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 时间线结果")
    promises: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 承诺结果")
    world_items: list[dict[str, Any]] = Field(default_factory=list, description="Phase 1 世界观结果")
    recent_n: int = Field(default=3, description="分析的最近章节数")


class Phase2ResultModel(BaseModel):
    """Phase 2 完整输出"""

    chapter_anchors: list[ChapterAnchorData] = Field(default_factory=list, description="章节锚点列表")
    coherence: dict[str, Any] = Field(default_factory=dict, description="连贯性分析结果")
    open_hooks: list[OpenHookData] = Field(default_factory=list, description="未收束钩子列表")
    recent_changes: list[str] = Field(default_factory=list, description="最近变更摘要")
    feasibility: FeasibilityReportData = Field(default_factory=FeasibilityReportData, description="可行性评估")


# ══════════════════════════════════════════════════════════════════════
# Phase 3 — 输入 / 输出
# ══════════════════════════════════════════════════════════════════════


class ConflictItemModel(BaseModel):
    """一条冲突记录"""

    type: str = Field(description="冲突类型: character_conflict / timeline_conflict / world_conflict / overwrite_warning")
    field: str = Field(default="", description="冲突字段名")
    name: str = Field(default="", description="冲突项名称")
    existing: Any = Field(default=None, description="已有值")
    incoming: Any = Field(default=None, description="新导入值")
    severity: str = Field(default="medium", description="严重程度: low / medium / high / critical")
    resolution_strategy: str = Field(default="keep_existing", description="建议解决策略")
    detail: str = Field(default="", description="冲突详情")


class Phase3InputModel(BaseModel):
    """Phase 3 输入"""

    project_id: str = Field(description="项目 ID")
    job_id: str = Field(description="导入任务 ID")
    phase1_result: dict[str, Any] = Field(description="Phase 1 四库分析结果")
    phase2_result: dict[str, Any] | None = Field(default=None, description="Phase 2 动态层结果")
    resolve_strategy: str = Field(default="keep_existing", description="冲突解决策略: keep_existing / merge / replace")


class Phase3ResultModel(BaseModel):
    """Phase 3 输出"""

    status: str = Field(description="导入状态: completed / blocked / failed / warning")
    conflicts: list[dict[str, Any]] = Field(default_factory=list, description="冲突列表")
    imported_characters: int = Field(default=0, description="已导入角色数")
    imported_timeline_events: int = Field(default=0, description="已导入时间线事件数")
    imported_promises: int = Field(default=0, description="已导入承诺数")
    imported_world_items: int = Field(default=0, description="已导入世界观条目数")
    card_pool_generated: int = Field(default=0, description="生成的卡牌数")
    message: str = Field(default="", description="结果消息")
