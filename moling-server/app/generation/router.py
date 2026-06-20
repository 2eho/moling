"""异步 AI 生成路由 - Celery worker 后台执行。

所有任务持久化统一通过 generation_service 完成，
不再依赖 FastAPI BackgroundTasks（服务重启后任务丢失）。

Endpoints:
- POST /api/v1/generate/chapters/{chapter_id}/generate - 创建异步生成任务
- GET  /api/v1/generate/jobs/{job_id} - 查询任务状态
- POST /api/v1/generate/jobs/{job_id}/cancel - 取消任务
- GET  /api/v1/generate/history - 获取生成历史
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.dao import generation_dao
from app.generation.jobs_store import JobStatus, task_to_dict
from app.schemas.generation import GenerateReq
from app.service import generation_service

router = APIRouter(tags=["generation"])


@router.post("/chapters/{chapter_id}/generate")
async def generate_chapter_async(
    chapter_id: int,
    project_id: int,
    req: GenerateReq,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建异步 AI 生成任务（Celery llm 队列执行）。
    
    立即返回 job_id，前端需要轮询 /jobs/{job_id} 获取结果。
    start_generation 内部创建 DB 记录并通过 Celery delay() 分发给 worker。
    
    Args:
        chapter_id: 章节 ID（路径参数）
        project_id: 项目 ID（查询参数）
        req: 生成请求体
        
    Returns:
        {code: 0, data: {job_id: str, status: "pending"}}
    """
    result = await generation_service.start_generation(
        db=db,
        user_id=current_user["id"],
        project_id=project_id,
        chapter_id=chapter_id,
        req=req,
    )
    
    return {
        "code": 0,
        "message": "生成任务已创建",
        "data": {
            "job_id": result.task_id,
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
    # 通过 DAO 查询 GenerationTask 记录
    from app.errors import NotFoundError, PermissionError as AppPermissionError
    
    task = await generation_dao.get_by_id(db, job_id)
    
    if not task:
        raise NotFoundError(detail="任务不存在")
    
    # 检查权限（只能查看自己的任务）
    if task.user_id != current_user["id"]:
        raise AppPermissionError(detail="无权访问")
    
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
        # Service 层异常直接透传
        raise
    
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
