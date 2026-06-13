"""墨灵 (Moling) — Weave (编织) Service.

业务逻辑：获取编织建议、应用编织等。
分析项目的情节线索、人物弧光、时间线等，提供整合建议。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import project_dao, chapter_dao, vault_dao
from app.errors import ErrorCode, NotFoundError, ValidationError
from app.schemas.weave import WeaveSuggestionResp, ApplyWeaveReq, WeaveAnalysisResp


class WeaveService:
    """Service for Weave operations."""

    async def get_suggestions(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> WeaveSuggestionResp:
        """获取项目的编织建议（分析情节、人物、时间线等）。"""
        # Check if project exists
        project = await project_dao.get(db, project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        # Get project's chapters
        chapters_result = await chapter_dao.get_by_project(db, project_id)
        chapters = chapters_result if isinstance(chapters_result, list) else []
        
        # Get vault entries for context
        characters = await vault_dao.get_by_project_and_type(db, project_id, "character")
        plots = await vault_dao.get_by_project_and_type(db, project_id, "plot")
        
        # TODO: 实际应调用 LLM 服务进行深度分析
        # 这里返回模拟数据作为框架
        suggestions = [
            {
                "id": "weave_1",
                "type": "plot_thread",
                "priority": "high",
                "description": "副线剧情需要与主线更紧密地交织",
                "affected_chapters": [ch.id for ch in chapters[:3]] if chapters else [],
                "suggestion": "在第3章引入副线人物的视角，增强与主线的关联",
            },
            {
                "id": "weave_2",
                "type": "character_arc",
                "priority": "medium",
                "description": "主角人物弧光在第5-8章进展缓慢",
                "affected_chapters": [ch.id for ch in chapters[4:8]] if len(chapters) > 4 else [],
                "suggestion": "在对话和内心独白中强化主角的成长轨迹",
            },
            {
                "id": "weave_3",
                "type": "timeline",
                "priority": "low",
                "description": "时间线跳跃可能影响读者理解",
                "affected_chapters": [ch.id for ch in chapters[2:5]] if len(chapters) > 2 else [],
                "suggestion": "考虑增加时间标记或过渡段落",
            },
        ]
        
        overview = f"项目《{project.title}》 currently has {len(chapters)} chapters. "
        overview += f"Detected {len(characters)} characters and {len(plots)} plot elements. "
        overview += "Overall weaving score: 7.2/10. Main issues: plot thread integration (6.5), "
        overview += "character arc consistency (7.0), timeline clarity (8.0)."
        
        return WeaveSuggestionResp(
            project_id=project_id,
            suggestions=suggestions,
            overview=overview,
        )

    async def apply_suggestions(
        self,
        db: AsyncSession,
        req: ApplyWeaveReq,
    ) -> dict:
        """应用编织建议到指定章节。"""
        # Check if project exists
        project = await project_dao.get(db, req.project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        # Validate chapter IDs
        for chapter_id in req.target_chapter_ids:
            chapter = await chapter_dao.get(db, chapter_id)
            if chapter is None or chapter.project_id != req.project_id:
                raise ValidationError(
                    error_code=ErrorCode.CHAPTER_NOT_FOUND,
                    detail=f"Chapter {chapter_id} not found in project",
                )
        
        # TODO: 实际应根据 suggestion_ids 应用具体的修改
        # 这里返回模拟结果
        applied_count = len(req.suggestion_ids)
        chapter_count = len(req.target_chapter_ids)
        
        return {
            "message": f"已应用 {applied_count} 条建议到 {chapter_count} 个章节",
            "applied_count": applied_count,
            "chapter_count": chapter_count,
            "project_id": req.project_id,
        }

    async def analyze_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> WeaveAnalysisResp:
        """深度分析项目的编织质量。"""
        # Check if project exists
        project = await project_dao.get(db, project_id)
        
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        
        # Get project data
        chapters_result = await chapter_dao.get_by_project(db, project_id)
        chapters = chapters_result if isinstance(chapters_result, list) else []
        
        characters = await vault_dao.get_by_project_and_type(db, project_id, "character")
        plots = await vault_dao.get_by_project_and_type(db, project_id, "plot")
        timelines = await vault_dao.get_by_project_and_type(db, project_id, "timeline")
        
        # TODO: 实际应调用 LLM 进行深度分析
        # 模拟分析结果
        plot_threads = [
            {
                "id": "thread_1",
                "name": "主线：寻宝之旅",
                "chapters": [ch.id for ch in chapters[:5]] if chapters else [],
                "status": "active",
                "completion": 0.6,
            },
            {
                "id": "thread_2",
                "name": "副线：家族秘辛",
                "chapters": [ch.id for ch in chapters[2:7]] if len(chapters) > 2 else [],
                "status": "active",
                "completion": 0.4,
            },
        ]
        
        character_arcs = [
            {
                "character_id": ch.id if isinstance(ch, object) else ch,
                "name": "主角",
                "arc_type": "growth",
                "progress": 0.65,
                "chapters_involved": [ch.id for ch in chapters[:8]] if len(chapters) > 0 else [],
            }
        ]
        
        timeline_consistency = {
            "score": 8.0,
            "issues": [],
            "suggestions": ["时间线清晰，无需调整"],
        }
        
        unresolved_promises = [
            {
                "id": "promise_1",
                "description": "第一章提到的神秘信件来源",
                "mentioned_in": [chapters[0].id if chapters else None],
                "status": "unresolved",
                "priority": "high",
            }
        ]
        
        return WeaveAnalysisResp(
            project_id=project_id,
            plot_threads=plot_threads,
            character_arcs=character_arcs,
            timeline_consistency=timeline_consistency,
            unresolved_promises=unresolved_promises,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# Singleton instance
weave_service = WeaveService()
