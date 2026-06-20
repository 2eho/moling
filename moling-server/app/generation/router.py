"""异步 AI 生成路由 - 将生成任务改为后台执行。

所有任务持久化统一通过 generation_service 完成，
不再依赖内存 dict。

Endpoints:
- POST /api/v1/generate/chapters/{chapter_id}/generate - 创建异步生成任务
- GET  /api/v1/generate/jobs/{job_id} - 查询任务状态
- POST /api/v1/generate/jobs/{job_id}/cancel - 取消任务
- GET  /api/v1/generate/history - 获取生成历史
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.generation.jobs_store import JobStatus, task_to_dict
from app.models.generation_task import GenerationTask
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
    实际的 DB 持久化在后台任务中通过 generation_service 完成。
    
    Args:
        chapter_id: 章节 ID（路径参数）
        project_id: 项目 ID（查询参数）
        req: 生成请求体
        
    Returns:
        {code: 0, data: {job_id: str, status: "pending"}}
    """
    # 预分配任务 ID，立即返回，不做任何 DB 写入
    job_id = f"gen_{uuid.uuid4().hex[:12]}"
    
    # 添加后台任务（注意：后台任务中需要创建新的数据库 session）
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
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询异步生成任务状态（从数据库读取）。
    
    Returns:
        任务详细信息，包括 status, progress, result, error 等字段。
    """
    # 从数据库查询 GenerationTask 记录
    stmt = select(GenerationTask).where(GenerationTask.id == job_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查权限（只能查看自己的任务）
    if task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问")
    
    # 转换为前端期望的 dict 格式
    job_dict = task_to_dict(task)
    
    return {"code": 0, "message": "success", "data": job_dict}


@router.post("/jobs/{job_id}/cancel")
async def cancel_generation_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消异步生成任务（通过 service 层操作数据库）。
    
    Returns:
        取消后的任务状态。
    """
    try:
        await generation_service.cancel_task(db, current_user["id"], job_id)
    except Exception as e:
        # 将 service 层的业务异常转换为 HTTP 异常
        from app.errors import NotFoundError, PermissionError as AppPermissionError
        if isinstance(e, NotFoundError):
            raise HTTPException(status_code=404, detail="任务不存在")
        if isinstance(e, AppPermissionError):
            detail = str(e.detail) if hasattr(e, 'detail') and e.detail else "无权操作"
            raise HTTPException(status_code=403, detail=detail)
        raise HTTPException(status_code=400, detail=str(e))
    
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
    
    DB 持久化统一通过 generation_service.start_generation 完成，
    不再手动调用 update_job。
    """
    from app.dependencies import async_session_factory
    
    # 创建新的数据库 session
    async with async_session_factory() as db:
        try:
            # 直接调用 service 层，传入预分配的 task_id
            # service 内部会创建 GenerationTask 记录并执行完整 pipeline
            await generation_service.start_generation(
                db,
                user_id=user_id,
                project_id=project_id,
                chapter_id=chapter_id,
                req=req,
                task_id=job_id,
            )
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[ERROR] Generation task {job_id} failed: {error_detail}")
            
            # pipeline 执行失败时，execute_generation_pipeline 已设置
            # task.status = "failed" + task.error_message 并 commit
            # 此处只需捕获异常并记录日志
