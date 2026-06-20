"""
墨灵 (Moling) — Ingest Phase 3: 确认导入

对应后端设计文档 v1.0 第十章第 10.6 节。
负责：
  - I10: 冲突校验
  - 事务性写入四库
  - 初始卡牌池生成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

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


@dataclass
class ConflictItem:
    """一条冲突记录"""
    type: str
    field: str = ""
    name: str = ""
    existing: Any = None
    incoming: Any = None
    severity: str = "medium"
    resolution_strategy: str = "keep_existing"
    detail: str = ""


@dataclass
class Phase3Input:
    """Phase 3 输入"""
    project_id: str
    job_id: str
    phase1_result: dict
    phase2_result: Optional[dict] = None
    resolve_strategy: str = "keep_existing"  # keep_existing / merge / replace


@dataclass
class Phase3Result:
    """Phase 3 输出"""
    status: str  # completed / blocked / failed / warning
    conflicts: list[dict] = field(default_factory=list)
    imported_characters: int = 0
    imported_timeline_events: int = 0
    imported_promises: int = 0
    imported_world_items: int = 0
    card_pool_generated: int = 0
    message: str = ""


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
