"""异步 AI 生成路由 - 将生成任务改为后台执行。

Endpoints:
- POST /api/v1/generate/chapters/{chapter_id}/generate - 创建异步生成任务
- GET  /api/v1/generate/jobs/{job_id} - 查询任务状态
- POST /api/v1/generate/jobs/{job_id}/cancel - 取消任务
- GET  /api/v1/generate/history - 获取生成历史
"""

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.generation.jobs_store import (
    create_job,
    get_job,
    update_job,
    JobStatus,
)
from app.schemas.generation import GenerateReq
from app.service import generation_service

router = APIRouter(tags=["generation"])


@router.post("/chapters/{chapter_id}/generate")
async def generate_chapter_async(
    chapter_id: int,
    project_id: int,
    req: GenerateReq,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建异步 AI 生成任务（新接口）。
    
    立即返回 job_id，前端需要轮询 /jobs/{job_id} 获取结果。
    
    Args:
        chapter_id: 章节 ID（路径参数）
        project_id: 项目 ID（查询参数）
        req: 生成请求体
        
    Returns:
        {code: 0, data: {job_id: str, status: "pending"}}
    """
    # 创建任务
    job_id = f"gen_{uuid.uuid4().hex[:12]}"
    create_job(job_id, chapter_id, current_user["id"])
    
    # 添加后台任务（注意：这里需要传递 db 的 new session，因为 db 会在请求结束后关闭）
    background_tasks.add_task(
        _run_generation_task,
        job_id=job_id,
        chapter_id=chapter_id,
        project_id=project_id,
        req=req,
        user_id=current_user["id"],
    )
    
    return {
        "code": 0,
        "message": "生成任务已创建",
        "data": {
            "job_id": job_id,
            "status": "pending",
        }
    }


@router.get("/jobs/{job_id}")
async def get_generation_job(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """查询异步生成任务状态。
    
    Returns:
        任务详细信息，包括 status, progress, result, error 等字段。
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查权限（只能查看自己的任务）
    if job["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    return {"code": 0, "message": "success", "data": job}


@router.post("/jobs/{job_id}/cancel")
async def cancel_generation_job(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """取消异步生成任务。
    
    Returns:
        取消后的任务状态。
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查权限（只能取消自己的任务）
    if job["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    # 只允许取消 pending 或 running 状态的任务
    if job["status"] not in (JobStatus.pending, JobStatus.running):
        raise HTTPException(status_code=400, detail="当前状态不支持取消")
    
    update_job(job_id, status=JobStatus.cancelled, progress={"percent": 0, "stage": "已取消"})
    
    return {"code": 0, "message": "success", "data": {"status": "cancelled"}}


@router.get("/history")
async def get_generation_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
):
    """获取异步生成任务历史（从数据库读取）。"""
    from app.service import generation_service
    history = await generation_service.get_history(
        db, current_user["id"], page, page_size
    )
    return {"code": 0, "message": "success", "data": {"history": history, "total": len(history), "page": page, "page_size": page_size}}


async def _run_generation_task(
    job_id: str,
    chapter_id: int,
    project_id: int,
    req: GenerateReq,
    user_id: int,
):
    """后台执行 AI 生成任务。
    
    注意：这里需要创建新的数据库 session，因为 FastAPI 的 Depends(get_db)
    会在请求结束后关闭 session。
    """
    from app.dependencies import async_session_factory
    
    # 创建新的数据库 session
    async with async_session_factory() as db:
        try:
            update_job(job_id, status=JobStatus.running, progress={"percent": 10, "stage": "AI分析中..."})
            
            # 执行生成（复用现有逻辑）
            result = await generation_service.start_generation(
                db, user_id, project_id, chapter_id, req
            )
            
            update_job(
                job_id,
                status=JobStatus.completed,
                progress={"percent": 100, "stage": "生成完成"},
                result=result,
            )
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[ERROR] Generation task {job_id} failed: {error_detail}")
            
            update_job(
                job_id,
                status=JobStatus.failed,
                error=str(e),
            )
