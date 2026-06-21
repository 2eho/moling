"""
墨灵 (Moling) — Ingest Phase 3: 确认导入

对应后端设计文档 v1.0 第十章第 10.6 节。
负责：
  - I10: 冲突校验
  - 事务性写入四库
  - 初始卡牌池生成
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.phase3.conflict import I10_conflict_check
from app.ingest.phase3.committer import Phase3Committer

__all__ = [
    "Phase3Input",
    "Phase3Result",
    "ConflictItem",
    "run_phase3_pipeline",
    "I10_conflict_check",
]


# ──────────────────────────────────────────────── 数据模型


class ConflictItem(BaseModel):
    """一条冲突记录"""
    type: str = Field(description="冲突类型: character_conflict / timeline_conflict / world_conflict / overwrite_warning")
    field: str = Field(default="", description="冲突字段名")
    name: str = Field(default="", description="冲突项名称")
    existing: Any = Field(default=None, description="已有值")
    incoming: Any = Field(default=None, description="新导入值")
    severity: str = Field(default="medium", description="严重程度: low / medium / high / critical")
    resolution_strategy: str = Field(default="keep_existing", description="建议解决策略")
    detail: str = Field(default="", description="冲突详情")


class Phase3Input(BaseModel):
    """Phase 3 输入"""
    project_id: str = Field(description="项目 ID")
    job_id: str = Field(description="导入任务 ID")
    phase1_result: dict[str, Any] = Field(description="Phase 1 四库分析结果")
    phase2_result: Optional[dict[str, Any]] = Field(default=None, description="Phase 2 动态层结果")
    resolve_strategy: str = Field(default="keep_existing", description="冲突解决策略: keep_existing / merge / replace")


class Phase3Result(BaseModel):
    """Phase 3 输出"""
    status: str = Field(description="导入状态: completed / blocked / failed / warning")
    conflicts: list[dict[str, Any]] = Field(default_factory=list, description="冲突列表")
    imported_characters: int = Field(default=0, description="已导入角色数")
    imported_timeline_events: int = Field(default=0, description="已导入时间线事件数")
    imported_promises: int = Field(default=0, description="已导入承诺数")
    imported_world_items: int = Field(default=0, description="已导入世界观条目数")
    card_pool_generated: int = Field(default=0, description="生成的卡牌数")
    message: str = Field(default="", description="结果消息")


# ──────────────────────────────────────────────── 流水线


async def run_phase3_pipeline(
    db: AsyncSession,
    input_data: Phase3Input,
) -> Phase3Result:
    """
    运行 Phase 3 确认导入流水线。

    流程：
    1. I10: 冲突校验
    2. 事务性四库写入
    3. 初始卡牌池生成
    """
    project_id = input_data.project_id
    phase1 = input_data.phase1_result
    strategy = input_data.resolve_strategy

    # Step 1: 冲突校验
    conflicts = await I10_conflict_check(db, project_id, phase1)

    # 检查是否有必须人工介入的冲突
    critical_conflicts = [c for c in conflicts if c["severity"] in ("high", "critical")]
    if critical_conflicts:
        return Phase3Result(
            status="blocked",
            conflicts=conflicts,
            message="存在需要人工确认的冲突",
        )

    # Step 2: 事务写入
    committer = Phase3Committer(db, project_id, strategy)
    commit_result = await committer.commit(phase1, conflicts)

    if commit_result["status"] == "failed":
        return Phase3Result(
            status="failed",
            message=commit_result.get("message", "导入失败"),
        )

    return Phase3Result(
        status=commit_result["status"],
        conflicts=conflicts,
        imported_characters=commit_result.get("imported_characters", 0),
        imported_timeline_events=commit_result.get("imported_timeline_events", 0),
        imported_promises=commit_result.get("imported_promises", 0),
        imported_world_items=commit_result.get("imported_world_items", 0),
        card_pool_generated=commit_result.get("card_pool_generated", 0),
        message=commit_result.get("message", "导入完成"),
    )
