"""墨灵 (Moling) — Vault API Router.

Provides endpoints for the Four Databases (四库): Characters, Timeline, Plot Promises, World Building.
"""

from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas.vault import CharacterResp, TimelineResp, PlotPromiseResp, WorldResp
from app.service import vault_service

router = APIRouter(tags=["vault"])


# =========== Characters ===========


@router.get("/characters", response_model=list[CharacterResp])
async def list_characters(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[CharacterResp]:
    """List all characters in a project's vault."""
    return await vault_service.list_characters(db, current_user.id, project_id)


@router.get("/characters/{character_id}", response_model=CharacterResp)
async def get_character(
    project_id: int,
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CharacterResp:
    """Get a single character by ID."""
    return await vault_service.get_character(db, current_user.id, project_id, character_id)


@router.post("/characters", response_model=CharacterResp, status_code=201)
async def create_character(
    project_id: int,
    character_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CharacterResp:
    """Create a new character in the vault."""
    return await vault_service.create_character(db, current_user.id, project_id, character_data)


@router.put("/characters/{character_id}", response_model=CharacterResp)
async def update_character(
    project_id: int,
    character_id: int,
    character_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CharacterResp:
    """Update a character in the vault."""
    return await vault_service.update_character(
        db, current_user.id, project_id, character_id, character_data
    )


@router.delete("/characters/{character_id}", status_code=204)
async def delete_character(
    project_id: int,
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a character from the vault."""
    await vault_service.delete_character(db, current_user.id, project_id, character_id)


# =========== Timeline ===========


@router.get("/timeline", response_model=list[TimelineResp])
async def list_timeline(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[TimelineResp]:
    """List all timeline events in a project's vault."""
    return await vault_service.list_timeline(db, current_user.id, project_id)


@router.get("/timeline/{event_id}", response_model=TimelineResp)
async def get_timeline_event(
    project_id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TimelineResp:
    """Get a single timeline event by ID."""
    return await vault_service.get_timeline_event(db, current_user.id, project_id, event_id)


@router.post("/timeline", response_model=TimelineResp, status_code=201)
async def create_timeline_event(
    project_id: int,
    event_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TimelineResp:
    """Create a new timeline event in the vault."""
    return await vault_service.create_timeline_event(db, current_user.id, project_id, event_data)


@router.put("/timeline/{event_id}", response_model=TimelineResp)
async def update_timeline_event(
    project_id: int,
    event_id: int,
    event_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TimelineResp:
    """Update a timeline event in the vault."""
    return await vault_service.update_timeline_event(
        db, current_user.id, project_id, event_id, event_data
    )


@router.delete("/timeline/{event_id}", status_code=204)
async def delete_timeline_event(
    project_id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a timeline event from the vault."""
    await vault_service.delete_timeline_event(db, current_user.id, project_id, event_id)


# =========== Plot Promises ===========


@router.get("/plot-promises", response_model=list[PlotPromiseResp])
async def list_plot_promises(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PlotPromiseResp]:
    """List all plot promises in a project's vault."""
    return await vault_service.list_plot_promises(db, current_user.id, project_id)


@router.get("/plot-promises/{promise_id}", response_model=PlotPromiseResp)
async def get_plot_promise(
    project_id: int,
    promise_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlotPromiseResp:
    """Get a single plot promise by ID."""
    return await vault_service.get_plot_promise(db, current_user.id, project_id, promise_id)


@router.post("/plot-promises", response_model=PlotPromiseResp, status_code=201)
async def create_plot_promise(
    project_id: int,
    promise_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlotPromiseResp:
    """Create a new plot promise in the vault."""
    return await vault_service.create_plot_promise(db, current_user.id, project_id, promise_data)


@router.put("/plot-promises/{promise_id}", response_model=PlotPromiseResp)
async def update_plot_promise(
    project_id: int,
    promise_id: int,
    promise_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PlotPromiseResp:
    """Update a plot promise in the vault."""
    return await vault_service.update_plot_promise(
        db, current_user.id, project_id, promise_id, promise_data
    )


@router.delete("/plot-promises/{promise_id}", status_code=204)
async def delete_plot_promise(
    project_id: int,
    promise_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a plot promise from the vault."""
    await vault_service.delete_plot_promise(db, current_user.id, project_id, promise_id)


# =========== World Building ===========


@router.get("/world", response_model=list[WorldResp])
async def list_world_entries(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[WorldResp]:
    """List all world-building entries in a project's vault."""
    return await vault_service.list_world_entries(db, current_user.id, project_id)


@router.get("/world/{entry_id}", response_model=WorldResp)
async def get_world_entry(
    project_id: int,
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorldResp:
    """Get a single world-building entry by ID."""
    return await vault_service.get_world_entry(db, current_user.id, project_id, entry_id)


@router.post("/world", response_model=WorldResp, status_code=201)
async def create_world_entry(
    project_id: int,
    entry_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorldResp:
    """Create a new world-building entry in the vault."""
    return await vault_service.create_world_entry(db, current_user.id, project_id, entry_data)


@router.put("/world/{entry_id}", response_model=WorldResp)
async def update_world_entry(
    project_id: int,
    entry_id: int,
    entry_data: dict = ...,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorldResp:
    """Update a world-building entry in the vault."""
    return await vault_service.update_world_entry(
        db, current_user.id, project_id, entry_id, entry_data
    )


@router.delete("/world/{entry_id}", status_code=204)
async def delete_world_entry(
    project_id: int,
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> None:
    """Delete a world-building entry from the vault."""
    await vault_service.delete_world_entry(db, current_user.id, project_id, entry_id)


@router.get("/summary", response_model=dict)
async def get_vault_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """获取四库总览（角色、时间线、伏笔、世界观的统计数据）。"""
    summary = await vault_service.get_summary(db, current_user.id, project_id)
    return summary


@router.post("/full-reanalyze", status_code=202)
async def full_reanalyze(
    project_id: int,
    req: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """全量重新分析项目内容，更新四库数据。

    创建 Celery 异步任务执行全量分析，返回 task_id 用于轮询进度。
    Celery broker 不可用时优雅降级，返回占位 task_id。
    """
    import uuid

    user_id = str(current_user.id)

    # 生成 task_id；如果 Celery/Redis 可用则提交异步任务
    task_id = f"reanalyze-{project_id}-{uuid.uuid4()}"
    try:
        # 快速检测 Redis 是否可用（避免 Celery 长时间重试阻塞请求）
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        redis_available = s.connect_ex(("localhost", 6379)) == 0
        s.close()

        if redis_available:
            from app.worker.vault_reanalyze_task import vault_full_reanalyze
            celery_task = vault_full_reanalyze.delay(
                project_id=project_id,
                user_id=user_id,
            )
            task_id = str(celery_task.id)
    except Exception:
        pass  # Celery/Redis 不可用，使用占位 task_id

    return {
        "status": "accepted",
        "task_id": task_id,
        "project_id": project_id,
        "message": "全量分析已提交至后台队列，可通过 task_id 查询进度",
    }
