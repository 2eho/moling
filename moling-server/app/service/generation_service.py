"""Moling - Generation Service.

Business logic for AI text generation (calls LLM API).
"""

from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, card_dao
from app.errors import NotFoundError, ErrorCode, PermissionError
from app.models import GenerationTask
from app.schemas.generation import GenerateReq, GenerationResp, TaskStatusResp
from app.llm.client import llm_client

settings = get_settings()


class GenerationService:
    """Service for generation operations."""

    async def start_generation(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: Optional[int],
        req: GenerateReq,
    ) -> GenerationResp:
        """Start an AI generation task."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )

        # Create task record
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            id=task_id,
            project_id=project_id,
            chapter_id=chapter_id,
            user_id=user_id,
            task_type="generate",
            status="pending",
            input_params={
                "card_ids": req.card_ids,
                "weights": req.weights,
                "mode": req.mode,
            },
            progress_percent=0,
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # TODO: Actually call LLM API (async via Celery or background task)
        # For now, just return the task ID
        # In production, this should trigger a Celery task or background job

        return GenerationResp(
            task_id=task.id,
            status=task.status,
        )

    async def get_task_status(
        self,
        db: AsyncSession,
        user_id: str,
        task_id: str,
    ) -> TaskStatusResp:
        """Get generation task status."""
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this task",
            )

        return TaskStatusResp(
            task_id=task.id,
            status=task.status,
            progress_stage=task.progress_stage,
            progress_percent=task.progress_percent,
            error_message=task.error_message,
            output_data=task.output_data,
        )

    async def cancel_task(
        self,
        db: AsyncSession,
        user_id: str,
        task_id: str,
    ) -> None:
        """Cancel a generation task."""
        stmt = select(GenerationTask).where(GenerationTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.TASK_NOT_FOUND,
                detail="Task not found",
            )

        # Verify ownership
        if task.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to cancel this task",
            )

        # Only pending/running tasks can be cancelled
        if task.status not in ("pending", "running"):
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail=f"Cannot cancel task in status: {task.status}",
            )

        task.status = "cancelled"
        await db.commit()


# Singleton instance
generation_service = GenerationService()
