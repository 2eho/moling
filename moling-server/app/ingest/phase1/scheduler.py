"""
墨灵 (Moling) — Ingest Phase 1 LLM Scheduler

并行 LLM 调用调度器，管理：
- 并发控制（Semaphore）
- 速率限制
- 指数退避重试
- 进度追踪
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from app.ingest.phase1.schemas import (
    ChapterAnalysis,
    Phase1Progress,
    Phase1Result,
)
from app.ingest.phase1.extractor import extract_chapter_all
from app.ingest.phase1.merger import (
    merge_characters,
    merge_similar_events,
    merge_promises,
    merge_world_items,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMBatchConfig:
    """LLM 调用批次配置"""
    max_concurrent: int = 5
    batch_size: int = 10
    retry_limit: int = 3
    rate_per_second: float = 2.0
    timeout_seconds: float = 120.0


class LLMScheduler:
    """LLM 调用调度器 — 管理并行调用、限速、重试"""

    def __init__(self, config: Optional[LLMBatchConfig] = None):
        self.config = config or LLMBatchConfig()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self.progress = {"completed": 0, "total": 0, "failed": 0}
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def rate_limit(self):
        """速率限制：确保不超过 rate_per_second"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self.config.rate_per_second
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def call_with_retry(
        self,
        chapter_data: dict,
        chapter_index: int,
        chapter_title: str,
    ) -> ChapterAnalysis:
        """带重试的 LLM 调用 — 提取单章全部四库数据"""
        last_error = None
        for attempt in range(self.config.retry_limit):
            try:
                async with self.semaphore:
                    await self.rate_limit()
                    analysis = await extract_chapter_all(
                        chapter_data=chapter_data,
                        chapter_index=chapter_index,
                        chapter_title=chapter_title,
                        timeout=self.config.timeout_seconds,
                    )
                    async with self._lock:
                        self.progress["completed"] += 1
                    return analysis
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 调用失败 (第 %d 章, 尝试 %d/%d): %s",
                    chapter_index, attempt + 1, self.config.retry_limit, e,
                )
                if attempt < self.config.retry_limit - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)

        # 所有重试失败
        async with self._lock:
            self.progress["failed"] += 1
        return ChapterAnalysis(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            error=str(last_error) if last_error else "LLM 调用全部重试失败",
        )

    def get_progress_percent(self) -> float:
        """获取当前进度百分比"""
        total = self.progress["total"]
        if total == 0:
            return 0.0
        done = self.progress["completed"] + self.progress["failed"]
        return round(done / total * 100, 1)


async def run_phase1_pipeline(
    chapters_data: list[dict],
    config: Optional[LLMBatchConfig] = None,
    progress_callback: Optional[Callable[[Phase1Progress], Coroutine[Any, Any, None]]] = None,
) -> Phase1Result:
    """
    运行 Phase 1 全量四库分析流水线。

    流程：
    1. 分发每章到 LLM 并行提取（I1-I4）
    2. 收集所有结果
    3. 合并去重
    4. 返回 Phase1Result
    """
    cfg = config or LLMBatchConfig()
    scheduler = LLMScheduler(cfg)
    total = len(chapters_data)
    scheduler.progress["total"] = total * 4  # 每章 4 个子任务

    if progress_callback:
        await progress_callback(Phase1Progress(
            status="running",
            progress_percent=0.0,
            completed_chapters=0,
            total_chapters=total,
            current_task="准备分析...",
        ))

    # Step 1: 并行提取每章数据
    tasks = []
    for ch_data in chapters_data:
        ch_index = ch_data.get("index", 0)
        ch_title = ch_data.get("title", f"第{ch_index+1}章")
        task = scheduler.call_with_retry(ch_data, ch_index, ch_title)
        tasks.append(task)

    # 分批处理以避免内存暴涨 + 支持进度回调
    all_analyses: list[ChapterAnalysis] = []
    batch_size = cfg.batch_size
    for batch_start in range(0, len(tasks), batch_size):
        batch = tasks[batch_start:batch_start + batch_size]
        if progress_callback:
            await progress_callback(Phase1Progress(
                status="running",
                progress_percent=scheduler.get_progress_percent(),
                completed_chapters=batch_start,
                total_chapters=total,
                failed_calls=scheduler.progress["failed"],
                current_task=f"分析第 {batch_start+1}-{min(batch_start+batch_size, total)} 章...",
            ))
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        for result in batch_results:
            if isinstance(result, ChapterAnalysis):
                all_analyses.append(result)
            elif isinstance(result, Exception):
                logger.error("批次执行异常: %s", result)

    if progress_callback:
        await progress_callback(Phase1Progress(
            status="running",
            progress_percent=90.0,
            completed_chapters=total,
            total_chapters=total,
            failed_calls=scheduler.progress["failed"],
            current_task="合并去重分析结果...",
        ))

    # Step 2: 收集所有原始提取结果
    all_characters = []
    all_events = []
    all_promises = []
    all_world_items = []

    for analysis in all_analyses:
        if analysis.error:
            continue
        for c in analysis.characters:
            all_characters.append({
                "name": c.name,
                "aliases": c.aliases,
                "dialogue_count": c.dialogue_count,
                "description": c.description,
                "tags": c.tags,
                "chapter_index": c.chapter_index,
            })
        for e in analysis.timeline_events:
            all_events.append({
                "description": e.description,
                "relative_time": e.relative_time,
                "time_anchor": e.time_anchor,
                "characters": e.characters,
                "importance": e.importance,
                "chapter_index": e.chapter_index,
            })
        for p in analysis.promises:
            all_promises.append({
                "type": p.type,
                "text": p.text,
                "context": p.context,
                "chapter_index": p.chapter_index,
                "related_characters": p.related_characters,
            })
        for w in analysis.world_items:
            all_world_items.append({
                "term": w.term,
                "description": w.description,
                "category": w.category,
                "chapter_index": w.chapter_index,
                "related_terms": w.related_terms,
            })

    # Step 3: 合并去重
    merged_chars = merge_characters(all_characters)
    merged_events = merge_similar_events(all_events)
    merged_promises_list = merge_promises(all_promises)
    merged_world = merge_world_items(all_world_items)

    # Step 4: 构建结果
    result = Phase1Result(
        characters=merged_chars,
        timeline_events=merged_events,
        promises=merged_promises_list,
        world_items=merged_world,
        chapter_count=total,
        total_llm_calls=scheduler.progress["completed"],
        failed_llm_calls=scheduler.progress["failed"],
    )

    # 收集错误
    for analysis in all_analyses:
        if analysis.error:
            result.errors.append(
                f"第 {analysis.chapter_index+1} 章「{analysis.chapter_title}」: {analysis.error}"
            )

    if progress_callback:
        await progress_callback(Phase1Progress(
            status="completed",
            progress_percent=100.0,
            completed_chapters=total,
            total_chapters=total,
            failed_calls=scheduler.progress["failed"],
            result=result,
            current_task="分析完成",
        ))

    return result
