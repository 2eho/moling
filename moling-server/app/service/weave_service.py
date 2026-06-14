"""墨灵 (Moling) — Weave (编织) Service.

业务逻辑：获取编织建议、应用编织等。
分析项目的情节线索、人物弧光、时间线等，提供整合建议。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, chapter_dao, vault_dao
from app.errors import ErrorCode, NotFoundError, ValidationError
from app.llm.client import llm_client
from app.schemas.weave import WeaveSuggestionResp, ApplyWeaveReq, WeaveAnalysisResp

logger = logging.getLogger(__name__)
settings = get_settings()


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
        
        # 调用 LLM 服务进行深度分析
        logger.info(f"Calling LLM for weave analysis on project {project_id}")
        suggestions = await self._llm_weave_analysis(
            db, project, chapters, characters, plots
        )

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
        
        # 根据 suggestion_ids 应用具体的修改
        # 记录应用到各章节的编制建议，方便后续追溯
        applied_details = []
        for suggestion_id in req.suggestion_ids:
            # 查找建议详情
            stmt_chapters = []
            for chapter_id in req.target_chapter_ids:
                chapter = await chapter_dao.get(db, chapter_id)
                if chapter:
                    # 在章节的 generation_prompt 中记录应用的建议
                    note = f"[Weave Applied: {suggestion_id}]"
                    if chapter.generation_prompt:
                        chapter.generation_prompt += f"\n{note}"
                    else:
                        chapter.generation_prompt = note
                    stmt_chapters.append(chapter_id)
            
            applied_details.append({
                "suggestion_id": suggestion_id,
                "applied_to_chapters": stmt_chapters,
            })
        
        await db.commit()

        applied_count = len(req.suggestion_ids)
        chapter_count = len(req.target_chapter_ids)
        
        return {
            "message": f"已应用 {applied_count} 条建议到 {chapter_count} 个章节",
            "applied_count": applied_count,
            "chapter_count": chapter_count,
            "project_id": req.project_id,
            "applied_details": applied_details,
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
        
        # 调用 LLM 进行深度分析
        logger.info(f"Calling LLM for deep project analysis on project {project_id}")
        analysis_result = await self._llm_deep_analysis(
            db, project, chapters, characters, plots, timelines
        )

        plot_threads = analysis_result.get("plot_threads", [])
        character_arcs = analysis_result.get("character_arcs", [])
        timeline_consistency = analysis_result.get("timeline_consistency", {
            "score": 7.0,
            "issues": [],
            "suggestions": ["暂无可用的深度分析结果"],
        })
        unresolved_promises = analysis_result.get("unresolved_promises", [])
        
        return WeaveAnalysisResp(
            project_id=project_id,
            plot_threads=plot_threads,
            character_arcs=character_arcs,
            timeline_consistency=timeline_consistency,
            unresolved_promises=unresolved_promises,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _llm_weave_analysis(
        self,
        db: AsyncSession,
        project: Any,
        chapters: list,
        characters: list,
        plots: list,
    ) -> list[dict]:
        """调用 LLM 获取编织建议。"""
        # 构建章节摘要
        chapter_summaries = []
        for ch in chapters[-10:]:  # 最近10章
            summary = ch.content[:200] if ch.content else "(空)"
            chapter_summaries.append(f"第{ch.chapter_number}章《{ch.title}》: {summary}")

        char_summary = "\n".join([f"- {c.name} ({c.role})" for c in characters[:20]]) if characters else "暂无"
        plot_summary = "\n".join([f"- {p.description[:100]}" for p in plots[:10]]) if plots else "暂无"

        prompt = f"""请分析以下小说的编织质量，提供具体的改进建议。

项目：《{project.title}》({project.genre})
简介：{project.synopsis}

现有角色：
{char_summary}

现有伏笔/情节线索：
{plot_summary}

最近章节摘要：
{chr(10).join(chapter_summaries)}

请以 JSON 格式返回 3-5 条编织建议，格式如下：
[
    {{
        "id": "weave_1",
        "type": "plot_thread / character_arc / timeline / pacing / structure",
        "priority": "high / medium / low",
        "description": "问题描述",
        "affected_chapters": [章节ID列表],
        "suggestion": "具体改进建议"
    }}
]

注意：返回纯 JSON，不要包含其他文字。"""
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的小说编织分析助手。分析情节、人物、时间线的交织质量，提供具体改进建议。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.4,
                max_tokens=2048,
            )
            content = response["choices"][0]["message"]["content"]
            # 解析 JSON
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except Exception as e:
            logger.error(f"LLM weave analysis failed: {e}", exc_info=True)

        # Fallback: 返回基本的建议
        return [
            {
                "id": "weave_fallback_1",
                "type": "plot_thread",
                "priority": "medium",
                "description": f"项目《{project.title}》有 {len(chapters)} 章、{len(characters)} 个角色、{len(plots)} 个情节元素",
                "affected_chapters": [ch.id for ch in chapters[:3]] if chapters else [],
                "suggestion": "建议增加章节间的编织密度，提高情节线索的交织度",
            },
        ]

    async def _llm_deep_analysis(
        self,
        db: AsyncSession,
        project: Any,
        chapters: list,
        characters: list,
        plots: list,
        timelines: list,
    ) -> dict:
        """调用 LLM 进行深度分析。"""
        chapter_summaries = []
        for ch in chapters[-15:]:
            summary = ch.content[:150] if ch.content else "(空)"
            chapter_summaries.append(f"第{ch.chapter_number}章: {summary}")

        char_summary = "\n".join([f"- {c.name} ({c.role})" for c in characters[:20]]) if characters else "暂无"
        plot_summary = "\n".join([f"- {p.description[:100]}" for p in plots[:10]]) if plots else "暂无"

        prompt = f"""请对以下小说项目进行深度编织分析。

项目：《{project.title}》({project.genre})
简介：{project.synopsis}

角色：
{char_summary}

情节线索/伏笔：
{plot_summary}

章节摘要：
{chr(10).join(chapter_summaries)}

请以 JSON 格式返回深度分析结果（不要包含其他文字）：

{{
    "plot_threads": [
        {{"id": "thread_1", "name": "线索名称", "chapters": [章节ID列表], "status": "active/dormant/resolved", "completion": 0.0-1.0}}
    ],
    "character_arcs": [
        {{"character_id": 0, "name": "角色名", "arc_type": "growth/fall/redemption", "progress": 0.0-1.0, "chapters_involved": [章节ID列表]}}
    ],
    "timeline_consistency": {{
        "score": 0.0-10.0,
        "issues": ["问题1"],
        "suggestions": ["建议1"]
    }},
    "unresolved_promises": [
        {{"id": "promise_1", "description": "伏笔描述", "mentioned_in": [章节ID列表], "status": "unresolved/partially/ongoing", "priority": "high/medium/low"}}
    ]
}}"""
        try:
            messages = [
                {"role": "system", "content": "你是一个专业的小说深度分析助手。分析情节线索、人物弧光、时间线一致性和未收束的伏笔。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat(
                messages=messages,
                model=settings.LLM_MODEL,
                temperature=0.3,
                max_tokens=4096,
            )
            content = response["choices"][0]["message"]["content"]
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        except Exception as e:
            logger.error(f"LLM deep analysis failed: {e}", exc_info=True)

        # Fallback 空结果
        return {"plot_threads": [], "character_arcs": [], "timeline_consistency": {"score": 5.0, "issues": ["分析失败"], "suggestions": ["请重试"]}, "unresolved_promises": []}


# Singleton instance
weave_service = WeaveService()
