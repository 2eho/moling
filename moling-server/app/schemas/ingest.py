"""墨灵 (Moling) — Ingest (导入) Pydantic Schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class IngestJobSummary(BaseModel):
    """导入任务摘要（列表项）"""

    id: str = Field(description="任务 ID")
    source_type: str = Field(description="导入来源类型: text / url / markdown")
    title: str = Field(description="作品名称")
    total_chapters: int = Field(description="章节总数")
    current_phase: str = Field(description="当前阶段: phase0 / phase1 / phase2 / phase3 / completed / failed")
    progress_percent: float = Field(description="进度百分比 0-100")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: Optional[str] = Field(default=None, description="创建时间 ISO 格式")


class IngestJobListResp(BaseModel):
    """导入任务列表响应"""

    success: bool = Field(description="是否成功")
    jobs: list[IngestJobSummary] = Field(default_factory=list, description="任务列表")


class IngestStartResp(BaseModel):
    """提交导入任务响应"""

    success: bool = Field(description="是否成功")
    job_id: Optional[str] = Field(default=None, description="任务 ID")
    status: Optional[str] = Field(default=None, description="任务状态")
    error: Optional[str] = Field(default=None, description="错误信息")


class ProgressInfo(BaseModel):
    """导入进度信息"""

    phase: str = Field(description="当前阶段")
    percent: float = Field(description="进度百分比")


class JobResult(BaseModel):
    """任务结果（四库 + 承诺）"""

    characters: Optional[list[dict[str, Any]]] = Field(default=None, description="角色列表")
    timeline: Optional[list[dict[str, Any]]] = Field(default=None, description="时间线事件")
    commitments: Optional[list[dict[str, Any]]] = Field(default=None, description="剧情承诺")
    world: Optional[list[dict[str, Any]]] = Field(default=None, description="世界观元素")


class IngestJobStatusResp(BaseModel):
    """导入任务详情响应（GET /{job_id}）"""

    success: bool = Field(description="是否成功")
    status: Optional[str] = Field(default=None, description="当前阶段")
    progress: Optional[ProgressInfo] = Field(default=None, description="进度信息")
    result: Optional[JobResult] = Field(default=None, description="四库分析结果")
    conflicts: Optional[list[dict[str, Any]]] = Field(default=None, description="冲突列表")
    error: Optional[str] = Field(default=None, description="错误信息")


class PhaseRunResp(BaseModel):
    """Phase 执行响应（POST /phase1, /phase2, /confirm）"""

    success: bool = Field(description="是否成功")
    phase: Optional[str] = Field(default=None, description="阶段名")
    job_id: Optional[str] = Field(default=None, description="任务 ID")
    status: Optional[str] = Field(default=None, description="执行状态")
    result: Optional[dict[str, Any]] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class PhaseStatusResp(BaseModel):
    """Phase 状态查询响应（GET /phaseN/result）"""

    success: bool = Field(description="是否成功")
    status: Optional[str] = Field(default=None, description="当前阶段")
    progress_percent: Optional[float] = Field(default=None, description="进度百分比")
    result: Optional[dict[str, Any]] = Field(default=None, description="分析结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class FullImportResp(BaseModel):
    """一键全流程导入响应（POST /full-import）"""

    success: bool = Field(description="是否成功")
    job_id: Optional[str] = Field(default=None, description="任务 ID")
    phase1: Optional[dict[str, Any]] = Field(default=None, description="Phase 1 结果")
    phase2: Optional[dict[str, Any]] = Field(default=None, description="Phase 2 结果")
    phase3: Optional[dict[str, Any]] = Field(default=None, description="Phase 3 结果")
    error: Optional[str] = Field(default=None, description="错误信息")
