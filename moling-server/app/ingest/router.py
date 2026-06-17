"""
墨灵 (Moling) — import / router.py
导入功能 API 路由

对应接口映射文档第七节"导入"的要求。
保留 Phase 0-3 全部功能。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.ingest.service import IngestService

router = APIRouter(prefix="/projects/{project_id}/import", tags=["Import"])


# ═══════════════════════════════════════════════════════════════
# 7.1 提交导入任务（对应 Phase 0）
# ═══════════════════════════════════════════════════════════════


@router.post("")
async def submit_import(
    project_id: int,
    body: Optional[dict] = None,
    text: Optional[str] = Query(default=None, description="粘贴文本导入"),
    file: Optional[UploadFile] = File(default=None, description="上传文件导入"),
    split_strategies: Optional[str] = Query(
        default=None,
        description="拆分策略，逗号分隔，如 'chapter_regex,paragraph'",
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    提交导入任务。
    
    - 粘贴文本：传入 text 参数
    - 上传文件：传入 file 参数（multipart/form-data）
    - 对应 Phase 0 的采集与分章
    """
    # 兼容 JSON body 方式（前端 POST JSON body 如 {"text":"...","source_type":"novel"}）
    source_type = "text"
    if body is not None:
        text = body.get("text", text)
        source_type = body.get("source_type", source_type)

    # 如果没有 text，尝试从 file 读取
    if not text and not file:
        raise HTTPException(status_code=400, detail="请提供 text 参数或上传文件")
    
    # 如果从文件上传，读取文件内容
    if file:
        try:
            # 读取上传的文件内容
            content = await file.read()
            text = content.decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
        finally:
            await file.close()
    
    strategies = split_strategies.split(",") if split_strategies else None
    
    # Phase 0: 从纯文本拆解
    dissect_result = await IngestService.dissect_text(text, "", strategies)
    if not dissect_result.get("success"):
        return dissect_result
    
    chapters_data = dissect_result.get("chapters", [])
    if not chapters_data:
        return {"success": False, "error": "未能拆解出章节内容"}
    
    # 创建导入任务
    job = await IngestService.create_job(
        db=db,
        project_id=project_id,
        user_id=int(user["id"]),
        source_type=source_type,
        source_url=None,
        title="",
    )
    
    # 保存章节数据到 job（需要实现）
    # TODO: 将 chapters_data 保存到 job 中
    
    return {
        "success": True,
        "job_id": job.id,
        "status": "created",
    }


# ═══════════════════════════════════════════════════════════════
# 7.2 轮询导入进度
# ═══════════════════════════════════════════════════════════════


@router.get("/{job_id}")
async def get_import_job(
    project_id: int,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取导入任务详情和进度。对应 7.2 轮询导入进度。"""
    job = await IngestService.get_job(db, job_id)
    
    # 构建响应，匹配接口映射文档 7.2
    result = {}
    conflicts = []
    
    if job.phase1_result:
        result["characters"] = job.phase1_result.get("characters", [])
        result["timeline"] = job.phase1_result.get("timeline", [])
        result["commitments"] = job.phase1_result.get("plot_promises", [])
        result["world"] = job.phase1_result.get("world", [])
    
    if job.phase3_result:
        conflicts = job.phase3_result.get("conflicts", [])
    
    return {
        "success": True,
        "status": job.current_phase,
        "progress": {
            "phase": job.current_phase,
            "percent": job.progress_percent,
        },
        "result": result,
        "conflicts": conflicts,
        "error": job.error_message,
    }


# ═══════════════════════════════════════════════════════════════
# Job Management（保留现有功能）
# ═══════════════════════════════════════════════════════════════


@router.get("")
async def list_import_jobs(
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


# ═══════════════════════════════════════════════════════════════
# Phase 1: 全量四库分析
# ═══════════════════════════════════════════════════════════════


@router.post("/{job_id}/phase1")
async def run_phase1(
    project_id: int,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 1 全量四库分析（异步）。对应 7.3 执行 Phase 1。"""
    return await IngestService.run_phase1(db, job_id)


@router.get("/{job_id}/phase1/result")
async def get_phase1_result(
    project_id: int,
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


# ═══════════════════════════════════════════════════════════════
# Phase 2: 近三章动态层分析
# ═══════════════════════════════════════════════════════════════


@router.post("/{job_id}/phase2")
async def run_phase2(
    project_id: int,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 2 近三章动态层分析。对应 7.4 执行 Phase 2。"""
    return await IngestService.run_phase2(db, job_id)


@router.get("/{job_id}/phase2/result")
async def get_phase2_result(
    project_id: int,
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


# ═══════════════════════════════════════════════════════════════
# Phase 3: 确认导入
# ═══════════════════════════════════════════════════════════════


@router.post("/{job_id}/confirm")
async def confirm_import(
    project_id: int,
    job_id: int,
    resolve_strategy: str = Query(
        default="keep_existing",
        description="冲突解决策略: keep_existing / merge / replace",
    ),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """执行 Phase 3 确认导入（冲突校验 + 事务写入 + 卡牌池生成）。对应 7.5 确认导入。"""
    return await IngestService.run_phase3(db, job_id, resolve_strategy)


@router.get("/{job_id}/phase3/result")
async def get_phase3_result(
    project_id: int,
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


# ═══════════════════════════════════════════════════════════════
# 全流程一键导入（保留现有功能）
# ═══════════════════════════════════════════════════════════════


@router.post("/full-import")
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
