"""
墨灵 (Moling) — ingest / router.py
连载书导入引擎 API 路由

对应后端设计文档 v1.0 第十章 Phase 0-3 全部 API 接口。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.ingest.service import IngestService

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingest"])


# ════════════════════════════════════════════════════════════════
# Phase 0: 采集与分章
# ════════════════════════════════════════════════════════════════


@router.post("/url")
async def ingest_from_url(
    url: str = Query(..., description="目标章节 URL"),
    split_strategies: Optional[str] = Query(
        default=None,
        description="拆分策略，逗号分隔，如 'chapter_regex,paragraph'",
    ),
):
    """从单章 URL 采集并拆解。对应 Phase 0 的 URL 采集路径。"""
    strategies = split_strategies.split(",") if split_strategies else None
    return await IngestService.dissect_url(url, strategies)


@router.post("/html")
async def ingest_from_html(
    raw_html: str = Query(..., description="完整 HTML 页面源码"),
    source_url: str = Query(default="", description="来源 URL（可选）"),
    split_strategies: Optional[str] = Query(
        default=None,
        description="拆分策略，逗号分隔",
    ),
):
    """从 HTML 源码拆解。对应 Phase 0 的 HTML 输入路径。"""
    strategies = split_strategies.split(",") if split_strategies else None
    return await IngestService.dissect_html(raw_html, source_url, strategies)


@router.post("/text")
async def ingest_from_text(
    text: str = Query(..., description="小说正文纯文本"),
    title: str = Query(default="", description="书名（可选）"),
    split_strategies: Optional[str] = Query(
        default=None,
        description="拆分策略，逗号分隔",
    ),
):
    """从纯文本拆解。对应 Phase 0 的粘贴/手动输入路径。"""
    strategies = split_strategies.split(",") if split_strategies else None
    return await IngestService.dissect_text(text, title, strategies)


@router.get("/toc")
async def fetch_toc(
    toc_url: str = Query(..., description="目录页 URL"),
    max_chapters: Optional[int] = Query(
        default=None,
        description="最大章节数限制",
    ),
):
    """解析目录页，返回章节链接预览。对应 Phase 0 的目录解析步骤。"""
    return await IngestService.fetch_toc(toc_url, max_chapters)


@router.post("/crawl")
async def batch_crawl(
    toc_url: str = Query(..., description="目录页 URL"),
    max_chapters: Optional[int] = Query(
        default=None,
        description="最大章节数限制",
    ),
    split_strategies: Optional[str] = Query(
        default=None,
        description="拆分策略，逗号分隔",
    ),
):
    """从目录页批量采集并拆解全部章节。对应 Phase 0 的全量自动采集路径。"""
    strategies = split_strategies.split(",") if split_strategies else None
    return await IngestService.batch_crawl(toc_url, max_chapters, strategies)


# ════════════════════════════════════════════════════════════════
# Job Management
# ════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/jobs")
async def create_ingest_job(
    project_id: int,
    source_type: str = Query(..., description="导入来源: url / html / text / file"),
    source_url: Optional[str] = Query(None, description="来源 URL"),
    title: str = Query("", description="作品名称"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建一个导入任务，并关联项目。"""
    job = await IngestService.create_job(
        db=db,
        project_id=project_id,
        user_id=int(user["id"]),
        source_type=source_type,
        source_url=source_url,
        title=title,
    )
    return {
        "success": True,
        "job_id": job.id,
        "status": "created",
        "current_phase": job.current_phase,
    }


@router.get("/projects/{project_id}/jobs")
async def list_ingest_jobs(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取项目的所有导入任务。"""
    jobs = await IngestService.get_jobs_for_project(db, project_id)
    return {
        "success": True,
        "jobs": [
            {
                "id": j.id,
                "source_type": j.source_type,
                "title": j.title,
                "total_chapters": j.total_chapters,
                "current_phase": j.current_phase,
                "progress_percent": j.progress_percent,
                "error_message": j.error_message,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/jobs/{job_id}")
async def get_ingest_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取导入任务详情。"""
    job = await IngestService.get_job(db, job_id)
    return {
        "success": True,
        "job": {
            "id": job.id,
            "project_id": job.project_id,
            "source_type": job.source_type,
            "title": job.title,
            "total_chapters": job.total_chapters,
            "current_phase": job.current_phase,
            "progress_percent": job.progress_percent,
            "error_message": job.error_message,
            "has_phase1_result": job.phase1_result is not None,
            "has_phase2_result": job.phase2_result is not None,
            "has_phase3_result": job.phase3_result is not None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        },
    }


# ════════════════════════════════════════════════════════════════
# Phase 1: 全量四库分析
# ════════════════════════════════════════════════════════════════


@router.post("/jobs/{job_id}/phase1")
async def run_phase1(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 1 全量四库分析（异步）。"""
    return await IngestService.run_phase1(db, job_id)


@router.get("/jobs/{job_id}/phase1/result")
async def get_phase1_result(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Phase 1 分析结果。"""
    job = await IngestService.get_job(db, job_id)
    return {
        "success": True,
        "status": job.current_phase,
        "progress_percent": job.progress_percent,
        "result": job.phase1_result,
        "error": job.error_message,
    }


# ════════════════════════════════════════════════════════════════
# Phase 2: 近三章动态层分析
# ════════════════════════════════════════════════════════════════


@router.post("/jobs/{job_id}/phase2")
async def run_phase2(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 2 近三章动态层分析。"""
    return await IngestService.run_phase2(db, job_id)


@router.get("/jobs/{job_id}/phase2/result")
async def get_phase2_result(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Phase 2 分析结果。"""
    job = await IngestService.get_job(db, job_id)
    return {
        "success": True,
        "status": job.current_phase,
        "progress_percent": job.progress_percent,
        "result": job.phase2_result,
        "error": job.error_message,
    }


# ════════════════════════════════════════════════════════════════
# Phase 3: 确认导入
# ════════════════════════════════════════════════════════════════


@router.post("/jobs/{job_id}/phase3")
async def run_phase3(
    job_id: int,
    resolve_strategy: str = Query(
        default="keep_existing",
        description="冲突解决策略: keep_existing / merge / replace",
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 3 确认导入（冲突校验 + 事务写入 + 卡牌池生成）。"""
    return await IngestService.run_phase3(db, job_id, resolve_strategy)


@router.get("/jobs/{job_id}/phase3/result")
async def get_phase3_result(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取 Phase 3 导入结果。"""
    job = await IngestService.get_job(db, job_id)
    return {
        "success": True,
        "status": job.current_phase,
        "progress_percent": job.progress_percent,
        "result": job.phase3_result,
        "error": job.error_message,
    }


# ════════════════════════════════════════════════════════════════
# 全流程一键导入
# ════════════════════════════════════════════════════════════════


@router.post("/projects/{project_id}/full-import")
async def full_import(
    project_id: int,
    text: str = Query(..., description="小说正文纯文本"),
    title: str = Query("", description="作品名称"),
    resolve_strategy: str = Query(
        default="keep_existing",
        description="冲突解决策略: keep_existing / merge / replace",
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    全流程一键导入。

    1. 先通过 Phase 0 分章
    2. 自动串联 Phase 1 → Phase 2 → Phase 3
    3. 返回完整导入报告
    """
    # Step 1: Phase 0 — 分章
    dissect_result = await IngestService.dissect_text(text, title)
    if not dissect_result.get("success"):
        return dissect_result

    chapters_data = dissect_result.get("chapters", [])
    if not chapters_data:
        return {"success": False, "error": "未能拆解出章节内容"}

    # Step 2-4: Phase 1 → 2 → 3 自动串联
    return await IngestService.full_import(
        db=db,
        project_id=project_id,
        user_id=int(user["id"]),
        chapters_data=chapters_data,
        source_type="text",
        title=title,
        resolve_strategy=resolve_strategy,
    )
