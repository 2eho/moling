"""
墨灵 (Moling) — ingest / service.py
导入引擎 Service 层

处理连载书导入的业务逻辑编排。
实现 Phase 0-3 全部功能。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.scraper import (
    dissect_from_url as _dissect_from_url,
    dissect_html as _dissect_html,
    dissect_text as _dissect_text,
    DissectResult,
)
from app.ingest.scraper.core.toc_crawler import (
    TOCFetcher,
    ChapterBatchCrawler,
)
from app.ingest.models import IngestJob
from app.ingest.phase1 import (
    LLMBatchConfig,
    Phase1Result,
    run_phase1_pipeline,
)
from app.ingest.phase2 import (
    run_phase2_pipeline,
    Phase2Input,
    Phase2Result,
)
from app.ingest.phase3 import (
    run_phase3_pipeline,
    Phase3Input,
    Phase3Result,
)
from app.errors import NotFoundError, ErrorCode

logger = logging.getLogger(__name__)


class IngestService:
    """连载书导入服务 — 编排 Phase 0-3 全部流程。"""

    # ════════════════════════════════════════════════════════════════
    # Phase 0: 采集与分章
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def dissect_url(
        url: str,
        split_strategies: Optional[list[str]] = None,
    ) -> dict:
        """从单章 URL 采集并拆解。"""
        if split_strategies is None:
            split_strategies = ["chapter_regex", "paragraph"]
        result = _dissect_from_url(url=url, split_strategies=split_strategies)
        return _format_result(result, source_type="url")

    @staticmethod
    async def dissect_html(
        raw_html: str,
        source_url: str = "",
        split_strategies: Optional[list[str]] = None,
    ) -> dict:
        """从 HTML 源码拆解。"""
        if split_strategies is None:
            split_strategies = ["chapter_regex", "paragraph"]
        result = _dissect_html(
            raw_html=raw_html,
            source_url=source_url,
            split_strategies=split_strategies,
        )
        return _format_result(result, source_type="html")

    @staticmethod
    async def dissect_text(
        text: str,
        title: str = "",
        split_strategies: Optional[list[str]] = None,
    ) -> dict:
        """从纯文本拆解。"""
        if split_strategies is None:
            split_strategies = ["chapter_regex", "paragraph"]
        result = _dissect_text(text=text, title=title, split_strategies=split_strategies)
        return _format_result(result, source_type="text")

    @staticmethod
    async def fetch_toc(
        toc_url: str,
        max_chapters: Optional[int] = None,
    ) -> dict:
        """解析目录页，返回章节列表预览。"""
        try:
            fetcher = TOCFetcher()
            links = fetcher.fetch_toc(toc_url)
            if max_chapters and len(links) > max_chapters:
                links = links[:max_chapters]
            return {
                "success": True,
                "novel_title": "",
                "chapter_count": len(links),
                "chapters": [
                    {"index": link.index, "title": link.title, "url": link.url}
                    for link in links
                ],
            }
        except Exception as exc:
            logger.exception("目录解析失败")
            return {"success": False, "error": str(exc), "chapter_count": 0, "chapters": []}

    @staticmethod
    async def batch_crawl(
        toc_url: str,
        max_chapters: Optional[int] = None,
        split_strategies: Optional[list[str]] = None,
    ) -> dict:
        """从目录页批量采集并拆解全部章节。"""
        if split_strategies is None:
            split_strategies = ["chapter_regex", "paragraph"]
        try:
            crawler = ChapterBatchCrawler(max_chapters=max_chapters)
            result = crawler.crawl(toc_url=toc_url, split_strategies=split_strategies)
            return _format_result(result, source_type="batch_crawl")
        except Exception as exc:
            logger.exception("批量采集失败")
            return {"success": False, "error": str(exc), "chapter_count": 0, "chapters": []}

    # ════════════════════════════════════════════════════════════════
    # Job Management
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def create_job(
        db: AsyncSession,
        project_id: int,
        user_id: int,
        source_type: str,
        source_url: Optional[str] = None,
        title: str = "",
        chapters_data: Optional[list[dict]] = None,
    ) -> IngestJob:
        """创建一个新的导入任务。"""
        job = IngestJob(
            project_id=project_id,
            user_id=user_id,
            source_type=source_type,
            source_url=source_url,
            title=title,
            total_chapters=len(chapters_data) if chapters_data else 0,
            current_phase="phase0",
            phase0_result={"chapters": chapters_data} if chapters_data else None,
            progress_percent=100.0 if chapters_data else 0.0,
        )
        db.add(job)
        await db.flush()
        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_id: int) -> IngestJob:
        """获取导入任务详情。"""
        job = await db.get(IngestJob, job_id)
        if not job:
            raise NotFoundError(ErrorCode.PROJECT_NOT_FOUND, "导入任务不存在")
        return job

    @staticmethod
    async def get_jobs_for_project(
        db: AsyncSession, project_id: int
    ) -> list[IngestJob]:
        """获取项目的所有导入任务。"""
        result = await db.execute(
            select(IngestJob)
            .where(IngestJob.project_id == project_id)
            .order_by(IngestJob.id.desc())
        )
        return list(result.scalars().all())

    # ════════════════════════════════════════════════════════════════
    # Phase 1: 全量四库分析
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def run_phase1(
        db: AsyncSession,
        job_id: int,
        chapters_data: Optional[list[dict]] = None,
    ) -> dict:
        """
        执行 Phase 1 全量四库分析。

        参数:
            job_id: 导入任务 ID
            chapters_data: 章节数据列表（如为 None，从 job.phase0_result 读取）
        """
        job = await IngestService.get_job(db, job_id)

        # 确定章节数据来源
        if chapters_data is None:
            if job.phase0_result and "chapters" in job.phase0_result:
                chapters_data = job.phase0_result["chapters"]
            else:
                return {
                    "success": False,
                    "error": "缺少章节数据，请先完成 Phase 0 拆解",
                }

        # 更新任务状态
        job.current_phase = "phase1"
        job.progress_percent = 0.0
        await db.flush()

        try:
            # 配置 LLM 批处理
            config = LLMBatchConfig(
                max_concurrent=5,
                batch_size=10,
                retry_limit=3,
                rate_per_second=2.0,
            )

            # 运行 Phase 1 流水线
            result: Phase1Result = await run_phase1_pipeline(
                chapters_data=chapters_data,
                config=config,
            )

            # 保存结果
            result_dict = {
                "characters": [
                    {
                        "name": c.name,
                        "aliases": c.aliases,
                        "first_appearance": c.first_appearance,
                        "chapters_active": c.chapters_active,
                        "dialogue_count": c.dialogue_count,
                        "description": c.description,
                        "tags": c.tags,
                    }
                    for c in result.characters
                ],
                "timeline_events": [
                    {
                        "description": e.description,
                        "relative_time": e.relative_time,
                        "time_anchor": e.time_anchor,
                        "characters": e.characters,
                        "importance": e.importance,
                        "chapter_index": e.chapter_index,
                        "is_key_event": e.is_key_event,
                    }
                    for e in result.timeline_events
                ],
                "promises": [
                    {
                        "type": p.type,
                        "text": p.text,
                        "context": p.context,
                        "chapter_index": p.chapter_index,
                        "status": p.status,
                        "urgency": p.urgency,
                        "related_characters": p.related_characters,
                    }
                    for p in result.promises
                ],
                "world_items": [
                    {
                        "term": w.term,
                        "description": w.description,
                        "category": w.category,
                        "first_appearance": w.first_appearance,
                        "reference_chapters": w.reference_chapters,
                        "related_terms": w.related_terms,
                    }
                    for w in result.world_items
                ],
                "chapter_count": result.chapter_count,
                "total_llm_calls": result.total_llm_calls,
                "failed_llm_calls": result.failed_llm_calls,
                "errors": result.errors,
            }

            job.phase1_result = result_dict
            job.progress_percent = 100.0
            await db.flush()

            return {
                "success": True,
                "phase": "phase1",
                "job_id": job.id,
                "status": "completed",
                "result": result_dict,
            }

        except Exception as exc:
            logger.exception("Phase 1 分析失败")
            job.current_phase = "failed"
            job.error_message = str(exc)
            await db.flush()
            return {"success": False, "error": str(exc), "phase": "phase1"}

    # ════════════════════════════════════════════════════════════════
    # Phase 2: 近三章动态层分析
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def run_phase2(
        db: AsyncSession,
        job_id: int,
    ) -> dict:
        """
        执行 Phase 2 近三章动态层分析。
        需要 Phase 1 结果作为输入。
        """
        job = await IngestService.get_job(db, job_id)

        if not job.phase1_result:
            return {
                "success": False,
                "error": "缺少 Phase 1 结果，请先完成四库分析",
            }

        if not job.phase0_result or "chapters" not in job.phase0_result:
            return {
                "success": False,
                "error": "缺少章节数据",
            }

        job.current_phase = "phase2"
        job.progress_percent = 0.0
        await db.flush()

        try:
            chapters_data = job.phase0_result["chapters"]
            phase1_data = job.phase1_result

            phase2_input = Phase2Input(
                chapters=chapters_data,
                characters=phase1_data.get("characters", []),
                timeline_events=phase1_data.get("timeline_events", []),
                promises=phase1_data.get("promises", []),
                world_items=phase1_data.get("world_items", []),
            )

            result: Phase2Result = await run_phase2_pipeline(phase2_input)

            result_dict = {
                "chapter_anchors": [
                    {
                        "chapter_index": a.chapter_index,
                        "chapter_title": a.chapter_title,
                        "opening_hook": a.opening_hook,
                        "midpoint_turn": a.midpoint_turn,
                        "closing_cliff": a.closing_cliff,
                        "action_peak": a.action_peak,
                    }
                    for a in result.chapter_anchors
                ],
                "coherence": result.coherence,
                "open_hooks": [
                    {
                        "type": h.type,
                        "text": h.text,
                        "chapter_index": h.chapter_index,
                        "age_in_chapters": h.age_in_chapters,
                        "stale": h.stale,
                    }
                    for h in result.open_hooks
                ],
                "recent_changes": result.recent_changes,
                "feasibility": {
                    "plot_density": result.feasibility.plot_density,
                    "loose_thread_count": result.feasibility.loose_thread_count,
                    "continuation_confidence": result.feasibility.continuation_confidence,
                    "recommendation": result.feasibility.recommendation,
                },
            }

            job.phase2_result = result_dict
            job.progress_percent = 100.0
            await db.flush()

            return {
                "success": True,
                "phase": "phase2",
                "job_id": job.id,
                "status": "completed",
                "result": result_dict,
            }

        except Exception as exc:
            logger.exception("Phase 2 分析失败")
            job.current_phase = "failed"
            job.error_message = str(exc)
            await db.flush()
            return {"success": False, "error": str(exc), "phase": "phase2"}

    # ════════════════════════════════════════════════════════════════
    # Phase 3: 确认导入
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def run_phase3(
        db: AsyncSession,
        job_id: int,
        resolve_strategy: str = "keep_existing",
    ) -> dict:
        """
        执行 Phase 3 确认导入。

        流程：
        1. 冲突校验（与现有四库数据对比）
        2. 事务性写入四库
        3. 生成初始卡牌池

        resolve_strategy: 冲突解决策略
            - keep_existing: 保留现有数据
            - merge: 合并
            - replace: 用新数据替换
        """
        job = await IngestService.get_job(db, job_id)

        if not job.phase1_result:
            return {"success": False, "error": "缺少 Phase 1 结果"}

        job.current_phase = "phase3"
        job.progress_percent = 0.0
        await db.flush()

        try:
            phase3_input = Phase3Input(
                project_id=job.project_id,
                job_id=job.id,
                phase1_result=job.phase1_result,
                phase2_result=job.phase2_result,
                resolve_strategy=resolve_strategy,
            )

            result: Phase3Result = await run_phase3_pipeline(
                db=db,
                input_data=phase3_input,
            )

            result_dict = {
                "status": result.status,
                "conflicts": result.conflicts,
                "imported": {
                    "characters": result.imported_characters,
                    "timeline_events": result.imported_timeline_events,
                    "promises": result.imported_promises,
                    "world_items": result.imported_world_items,
                },
                "card_pool_generated": result.card_pool_generated,
                "message": result.message,
            }

            job.phase3_result = result_dict
            job.current_phase = "completed" if result.status == "completed" else "failed"
            job.progress_percent = 100.0
            if result.status == "blocked":
                job.error_message = "存在需要人工确认的冲突"
            await db.flush()

            return {
                "success": result.status in ("completed", "warning"),
                "phase": "phase3",
                "job_id": job.id,
                "status": result.status,
                "result": result_dict,
            }

        except Exception as exc:
            logger.exception("Phase 3 导入失败")
            job.current_phase = "failed"
            job.error_message = str(exc)
            await db.flush()
            return {"success": False, "error": str(exc), "phase": "phase3"}

    # ════════════════════════════════════════════════════════════════
    # 全流程一键导入
    # ════════════════════════════════════════════════════════════════

    @staticmethod
    async def full_import(
        db: AsyncSession,
        project_id: int,
        user_id: int,
        chapters_data: list[dict],
        source_type: str = "text",
        title: str = "",
        resolve_strategy: str = "keep_existing",
    ) -> dict:
        """
        全流程导入：Phase 1 → Phase 2 → Phase 3 自动串联。
        """
        # 创建任务
        job = await IngestService.create_job(
            db=db,
            project_id=project_id,
            user_id=user_id,
            source_type=source_type,
            title=title,
            chapters_data=chapters_data,
        )
        await db.flush()

        # Phase 1
        phase1_result = await IngestService.run_phase1(db, job.id)
        if not phase1_result.get("success"):
            return phase1_result

        # Phase 2
        phase2_result = await IngestService.run_phase2(db, job.id)
        if not phase2_result.get("success"):
            return phase2_result

        # Phase 3
        phase3_result = await IngestService.run_phase3(db, job.id, resolve_strategy)

        return {
            "success": phase3_result.get("success", False),
            "job_id": job.id,
            "phase1": phase1_result,
            "phase2": phase2_result,
            "phase3": phase3_result,
        }


# ════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════


def _format_result(result: DissectResult, source_type: str) -> dict:
    """将 DissectResult 转为 API 响应格式。"""
    chapters_data = []
    for ch in result.chapters:
        paras = []
        if ch.paragraphs:
            paras = [
                {
                    "index": p.index,
                    "text": p.text,
                    "char_count": p.char_count,
                    "is_dialogue": p.is_dialogue,
                }
                for p in ch.paragraphs
            ]
        chapters_data.append({
            "index": ch.index,
            "title": ch.title,
            "raw_text": ch.raw_text,
            "word_count": ch.word_count,
            "heading_pattern": ch.heading_pattern,
            "paragraphs": paras,
        })

    return {
        "success": not result.errors,
        "title": result.title,
        "source_url": result.source_url,
        "source_type": source_type,
        "chapter_count": result.chapter_count,
        "paragraph_count": result.paragraph_count,
        "total_word_count": result.total_word_count,
        "chapters": chapters_data,
        "errors": result.errors,
        "stats": result.stats,
    }
