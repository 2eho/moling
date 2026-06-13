"""墨灵 (Moling) — Phase 4 (四阶段精修) Service.

业务逻辑：获取精修建议、应用精修、查询任务状态等。
可能需要调用 LLM 服务进行文本分析。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import phase4_dao, chapter_dao
from app.errors import ErrorCode, NotFoundError, ValidationError
from app.schemas.phase4 import Phase4SuggestionResp, ApplyPhase4Req, Phase4TaskResp


class Phase4Service:
    """Service for Phase 4 operations."""

    async def get_suggestions(
        self,
        db: AsyncSession,
        chapter_id: int,
    ) -> Phase4SuggestionResp:
        """获取章节的精修建议（可能需要调用 LLM）。"""
        # Check if chapter exists
        chapter = await chapter_dao.get(db, chapter_id)
        
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        # TODO: 实际应调用 LLM 服务分析章节内容
        # 这里返回模拟数据作为框架
        suggestions = [
            {
                "id": "suggestion_1",
                "type": "coherence",
                "severity": "medium",
                "description": "章节开头与上文衔接不够自然",
                "original_text": chapter.content[:100] if chapter.content else "",
                "suggested_text": "建议重写开头，增加过渡段落",
                "position": {"start": 0, "end": 100},
            },
            {
                "id": "suggestion_2",
                "type": "consistency",
                "severity": "high",
                "description": "人物性格描述前后不一致",
                "original_text": "",
                "suggested_text": "请检查人物对话和行为的连贯性",
                "position": {"start": 0, "end": 0},
            },
        ]
        
        return Phase4SuggestionResp(
            chapter_id=chapter_id,
            suggestions=suggestions,
            overall_score=7.5,
            details={
                "coherence": 7.0,
                "consistency": 6.5,
                "pacing": 8.0,
                "style": 8.5,
            },
        )

    async def apply_suggestions(
        self,
        db: AsyncSession,
        req: ApplyPhase4Req,
    ) -> dict:
        """应用精修建议到章节。"""
        # Check if chapter exists
        chapter = await chapter_dao.get(db, req.chapter_id)
        
        if chapter is None:
            raise NotFoundError(
                error_code=ErrorCode.CHAPTER_NOT_FOUND,
                detail="Chapter not found",
            )
        
        # TODO: 实际应根据 suggestion_ids 应用具体的修改
        # 这里返回模拟结果
        applied_count = len(req.suggestion_ids)
        
        # Create a Phase4 task record for tracking
        from app.models.phase4_task import Phase4Task
        
        task = Phase4Task(
            nonce=f"ch{req.chapter_id}_{int(datetime.now(timezone.utc).timestamp())}",
            project_id=str(chapter.project_id),
            chapter_id=str(req.chapter_id),
            status="done",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        
        db.add(task)
        await db.commit()
        
        return {
            "message": f"已应用 {applied_count} 条建议",
            "applied_count": applied_count,
            "chapter_id": req.chapter_id,
        }

    async def get_task_status(
        self,
        db: AsyncSession,
        task_id: int,
    ) -> Phase4TaskResp:
        """查询 Phase 4 任务状态。"""
        task = await phase4_dao.get(db, task_id)
        
        if task is None:
            raise NotFoundError(
                error_code=ErrorCode.GENERATION_TASK_NOT_FOUND,
                detail="Phase 4 task not found",
            )
        
        return Phase4TaskResp.model_validate(task)

    async def list_chapter_tasks(
        self,
        db: AsyncSession,
        chapter_id: int,
    ) -> list[Phase4TaskResp]:
        """查询章节的所有 Phase 4 任务。"""
        tasks = await phase4_dao.get_by_chapter(db, str(chapter_id))
        return [Phase4TaskResp.model_validate(t) for t in tasks]

    async def list_project_tasks(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> list[Phase4TaskResp]:
        """查询项目的所有 Phase 4 任务。"""
        tasks = await phase4_dao.get_by_project(db, str(project_id))
        return [Phase4TaskResp.model_validate(t) for t in tasks]


# Singleton instance
phase4_service = Phase4Service()
