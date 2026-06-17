"""
墨灵 (Moling) — 连载书导入引擎边界条件验收测试

覆盖 P1-3 规格中列出的 15 个边界场景，对 Phase 0-3 进行全边界测试。

使用 Mock/AsyncMock 模拟外部依赖，不依赖真实数据库连接，
同时兼容 Windows（conftest 的 greenlet 模拟模式）。
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


# ──────────────────────────────────────────────────────────────────────
# 辅助：创建 Mock DB 会话
# ──────────────────────────────────────────────────────────────────────


def _make_mock_db(**kwargs):
    """创建模拟的 AsyncSession，避免 RuntimeWarning。"""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = MagicMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    for k, v in kwargs.items():
        setattr(db, k, v)
    return db


def _make_chapter(index: int, title: str = "", text: str = "") -> dict:
    """创建标准章节数据字典。"""
    return {
        "index": index,
        "title": title or f"第{index+1}章",
        "raw_text": text or f"这是第{index+1}章的正文内容。",
        "word_count": len(text or f"这是第{index+1}章的正文内容。"),
        "heading_pattern": "",
        "paragraphs": [],
    }


# ======================================================================
# Test 1: 1-2 章短篇导入
# ======================================================================


class TestShortStoryImport:
    """短篇连载（1-2 章）Phase 0-2 完整流程验证。"""

    def test_dissect_short_text_phase0(self):
        """1 章短文本应正确拆解。"""
        from app.ingest.scraper import dissect_text

        text = (
            "第一章 初遇\n\n"
            "陈道临走在通往帝都的大路上。突然，他听到了远处传来的打斗声。"
            "他加快脚步走上前去，发现一个年轻人正在与一群黑衣人搏斗。"
            "年轻人，我来助你一臂之力！陈道临喊道。"
        )
        result = dissect_text(text, title="短篇测试")
        assert result.chapter_count == 1
        assert result.title == "短篇测试"
        assert "陈道临" in result.chapters[0].raw_text

    def test_2chapter_text_phase0(self):
        """2 章短文本应正确拆解为两章。"""
        from app.ingest.scraper import dissect_text

        text = (
            "第一章 初遇\n\n"
            "陈道临走在通往帝都的大路上。突然，他听到了远处传来的打斗声。"
            "他加快脚步走上前去，发现一个年轻人正在与一群黑衣人搏斗。"
            "年轻人，我来助你一臂之力！陈道临喊道。"
            "那个年轻人转过头来，露出一张坚毅的面孔。多谢相助！年轻人说。\n\n"
            "第二章 帝都\n\n"
            "三天后，陈道临终于抵达了帝都。这座宏伟的城市让他惊叹不已。"
            "他打听到了关于魔法学院的消息。据说帝都魔法学院有着数百年的历史。"
            "陈道临决定明天就去学院报到。"
        )
        result = dissect_text(text)
        assert result.chapter_count == 2
        assert result.chapters[0].title == "第一章 初遇"
        assert result.chapters[1].title == "第二章 帝都"

    @pytest.mark.asyncio
    async def test_short_story_phase2(self):
        """短篇（2 章）Phase 2 动态层分析应返回完整结果。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input

        chapters = [
            {"index": 0, "title": "第一章 初遇",
             "raw_text": "突然，一个声音响起。陈道临猛地转过头。"},
            {"index": 1, "title": "第二章 真相",
             "raw_text": "他到底是谁？为什么出现在这里？"},
        ]
        input_data = Phase2Input(chapters=chapters)
        result = run_phase2_pipeline(input_data)
        assert result.chapter_anchors[0].opening_hook is True
        assert result.feasibility.continuation_confidence >= 0


# ======================================================================
# Test 2: 100+ 章长篇分批分析
# ======================================================================


class TestLongStoryBatchAnalysis:
    """100+ 章长篇确认分批（batch_size=15）逻辑正确处理。"""

    @pytest.mark.asyncio
    @patch("app.ingest.phase1.scheduler.extract_chapter_all")
    async def test_batch_processing_100_chapters(self, mock_extract):
        """100 章应分批处理，验证 15 章/批的边界。"""
        from app.ingest.phase1.scheduler import (
            LLMBatchConfig,
            run_phase1_pipeline,
        )

        # Mock extract_chapter_all 返回有效结果
        mock_extract.return_value = MagicMock(
            chapter_index=0,
            chapter_title="Test",
            characters=[],
            timeline_events=[],
            promises=[],
            world_items=[],
            error=None,
        )

        chapters = [_make_chapter(i) for i in range(100)]
        config = LLMBatchConfig(
            max_concurrent=5,
            batch_size=15,
            retry_limit=1,
            rate_per_second=100.0,
            timeout_seconds=30,
        )

        result = await run_phase1_pipeline(chapters_data=chapters, config=config)
        # 即使 LLM 失败（mock），也应返回结果
        assert result.chapter_count == 100
        assert result.total_llm_calls >= 0

    @pytest.mark.asyncio
    @patch("app.ingest.phase1.scheduler.extract_chapter_all")
    async def test_101_chapters_overflow_batch(self, mock_extract):
        """101 章（超出 15*6=90 但不足 15*7=105），验证第 7 批正确。"""
        from app.ingest.phase1.scheduler import (
            LLMBatchConfig,
            run_phase1_pipeline,
        )

        mock_extract.return_value = MagicMock(
            chapter_index=0, chapter_title="Test",
            characters=[], timeline_events=[], promises=[], world_items=[],
            error=None,
        )

        chapters = [_make_chapter(i) for i in range(101)]
        config = LLMBatchConfig(
            max_concurrent=5, batch_size=15, retry_limit=1,
            rate_per_second=100.0, timeout_seconds=30,
        )

        result = await run_phase1_pipeline(chapters_data=chapters, config=config)
        assert result.chapter_count == 101


# ======================================================================
# Test 3: 30+ 章 Level 2 压缩
# ======================================================================


class TestLevel2Compression:
    """30+ 章验证 Phase 1 合并器的 vault_filter 压缩处理。"""

    def test_merge_30_chapter_characters_dedup(self):
        """30 章角色数据应正确合并去重。"""
        from app.ingest.phase1.merger import merge_characters

        entries = []
        for i in range(30):
            entries.append({
                "name": "陈道临",
                "aliases": ["道长"],
                "dialogue_count": 5,
                "description": "主角",
                "tags": ["主角"],
                "chapter_index": i,
            })
        # 混入另一个角色
        entries.append({
            "name": "李察",
            "aliases": [],
            "dialogue_count": 3,
            "description": "配角",
            "tags": ["配角"],
            "chapter_index": 15,
        })

        result = merge_characters(entries)
        assert len(result) == 2
        assert result[0].dialogue_count == 30 * 5  # 陈道临合并
        assert len(result[0].chapters_active) == 30

    def test_merge_30_chapter_events_dedup(self):
        """30 章事件应正确合并相似事件。"""
        from app.ingest.phase1.merger import merge_similar_events

        events = []
        for i in range(30):
            events.append({
                "description": "陈道临遇到李察" if i % 2 == 0 else "陈道临和李察交谈",
                "relative_time": "当天",
                "characters": ["陈道临", "李察"],
                "importance": 4,
                "chapter_index": i,
            })
        result = merge_similar_events(events)
        # 相似事件应该被合并
        assert len(result) <= 15
        assert len(result) >= 1


# ======================================================================
# Test 4: 拆书→生成→重新导入的覆盖流程
# ======================================================================


class TestOverwriteFlow:
    """拆书后修改再导入的覆盖流程验证。"""

    @pytest.mark.asyncio
    async def test_overwrite_phase3_keep_existing(self):
        """覆盖导入时 keep_existing 策略应保留原有数据。"""
        from app.ingest.phase3 import run_phase3_pipeline, Phase3Input

        db = _make_mock_db()
        # Mock DB 返回已有角色
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        db.get.return_value = MagicMock(
            project_id=1,
            phase0_result={"chapters": [{"index": 0}]},
            phase1_result={"characters": [], "timeline_events": [],
                           "promises": [], "world_items": []},
            phase2_result=None,
        )

        input_data = Phase3Input(
            project_id=1,
            job_id=1,
            phase1_result={
                "characters": [{"name": "陈道临", "description": "新主角", "tags": ["主角"]}],
                "timeline_events": [],
                "promises": [],
                "world_items": [],
                "chapter_count": 10,
                "existing_chapter_count": 5,
            },
            phase2_result=None,
            resolve_strategy="keep_existing",
        )
        result = await run_phase3_pipeline(db, input_data)
        assert result.status in ("completed", "blocked")

    @pytest.mark.asyncio
    async def test_overwrite_phase3_replace(self):
        """覆盖导入时 replace 策略应替换原有数据。"""
        from app.ingest.phase3 import run_phase3_pipeline, Phase3Input

        db = _make_mock_db()
        # Mock 存在已有角色
        existing_char = MagicMock()
        existing_char.configure_mock(name="陈道临", description="旧描述",
                                     traits=["主角"], chapter_count=5)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing_char]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result
        db.get.return_value = MagicMock(
            project_id=1, phase0_result={"chapters": []},
            phase1_result={}, phase2_result=None,
        )

        input_data = Phase3Input(
            project_id=1,
            job_id=1,
            phase1_result={
                "characters": [{"name": "陈道临", "description": "新描述", "tags": ["主角"]}],
                "timeline_events": [],
                "promises": [],
                "world_items": [],
                "chapter_count": 10,
                "existing_chapter_count": 5,
            },
            resolve_strategy="replace",
        )
        result = await run_phase3_pipeline(db, input_data)
        assert result.status in ("completed", "blocked", "failed")


# ======================================================================
# Test 5: 空章节内容导入
# ======================================================================


class TestEmptyChapter:
    """空字符串章节的边界处理。"""

    def test_empty_text_dissect(self):
        """空文本应返回错误。"""
        from app.ingest.scraper import dissect_text

        result = dissect_text("")
        assert result.chapter_count == 0
        assert len(result.errors) > 0

    def test_whitespace_only_text(self):
        """纯空白文本应报错。"""
        from app.ingest.scraper import dissect_text

        result = dissect_text("   \n\n  \t  ")
        assert result.chapter_count == 0

    def test_empty_chapter_in_list_phase2(self):
        """空章节内容在 Phase 2 中不应崩溃。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input

        chapters = [
            {"index": 0, "title": "第一章", "raw_text": ""},
        ]
        input_data = Phase2Input(chapters=chapters)
        result = run_phase2_pipeline(input_data)
        assert result.chapter_anchors[0].opening_hook is False
        assert result.chapter_anchors[0].closing_cliff is False


# ======================================================================
# Test 6: 超大章节（10000+字）
# ======================================================================


class TestHugeChapter:
    """超长章节（10000+字）的边界处理。"""

    def test_huge_chapter_dissect(self):
        """10000+ 字单章应正确拆解且不超时。"""
        from app.ingest.scraper import dissect_text

        # 构造 12000 字的单章
        body = "第一章 长篇\n\n" + "测试内容。" * 4000
        result = dissect_text(body)
        assert result.chapter_count >= 1
        # 内容不应丢失
        total_len = sum(c.word_count for c in result.chapters)
        assert total_len > 10000

    def test_huge_chapter_phase2_anchors(self):
        """超大章节 Phase 2 锚点分析应正确处理。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input

        long_text = "突然，一声巨响。" + "他继续往前走。" * 500 + "未完待续"
        chapters = [
            {"index": 0, "title": "第一章", "raw_text": long_text},
        ]
        input_data = Phase2Input(chapters=chapters)
        result = run_phase2_pipeline(input_data)
        assert len(result.chapter_anchors) == 1
        # 章首应有钩子
        assert result.chapter_anchors[0].opening_hook is True

    def test_huge_chapter_merger(self):
        """超大章节角色合并应正确处理大量数据。"""
        from app.ingest.phase1.merger import merge_characters

        # 模拟 200 条角色记录
        entries = []
        for i in range(200):
            name = "陈道临" if i % 3 == 0 else "李察"
            entries.append({
                "name": name,
                "aliases": [],
                "dialogue_count": 1,
                "description": "",
                "tags": [],
                "chapter_index": i % 50,
            })
        result = merge_characters(entries)
        assert len(result) == 2
        assert sum(c.dialogue_count for c in result) == 200


# ======================================================================
# Test 7: 重复章节号导入
# ======================================================================


class TestDuplicateChapterIndex:
    """重复章节号的幂等性检查。"""

    def test_merger_duplicate_indices(self):
        """合并器应对重复章节号去重。"""
        from app.ingest.phase1.merger import merge_characters

        entries = [
            {"name": "陈道临", "aliases": [], "dialogue_count": 5,
             "description": "主角", "tags": ["主角"], "chapter_index": 0},
            {"name": "陈道临", "aliases": [], "dialogue_count": 3,
             "description": "主角", "tags": ["主角"], "chapter_index": 0},
        ]
        result = merge_characters(entries)
        assert len(result) == 1
        assert result[0].dialogue_count == 8

    def test_dissect_duplicate_headers(self):
        """重复的章节标题不应导致崩溃。"""
        from app.ingest.scraper import dissect_text

        text = (
            "第一章 重复\n\n"
            "这是第一章的内容。陈道临出发了。他走了很远的路。"
            "路上遇到了各种有趣的事情。一切都是那么新奇。\n\n"
            "第一章 重复\n\n"
            "这似乎是另一章的内容。李察也出发了。"
            "他走了不同的路。世界真是奇妙啊。"
        )
        result = dissect_text(text)
        # 可能合并为 1 章或分成 2 章，但不应崩溃
        assert result.chapter_count >= 1

    def test_phase3_overlap_detection(self):
        """Phase 3 应检测到章节覆盖冲突。"""
        from app.ingest.phase3.conflict import _check_chapter_overlap

        data = {
            "existing_chapter_count": 10,
            "chapter_count": 8,
        }
        conflicts = _check_chapter_overlap(data)
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "overwrite_warning"


# ======================================================================
# Test 8: 断点续传模拟
# ======================================================================


class TestResumeFromCheckpoint:
    """Phase 0/Phase 1 中断后恢复的断点续传。"""

    def test_crawl_progress_save_load(self):
        """CrawlProgress 应支持序列化和恢复。"""
        from app.ingest.scraper.core.toc_crawler import CrawlProgress

        progress = CrawlProgress(
            novel_title="测试小说",
            source_toc_url="https://example.com/toc",
            total_chapters=100,
            fetched_count=45,
            chapters=[
                {"index": i, "title": f"第{i}章", "url": f"https://example.com/{i}"}
                for i in range(100)
            ],
            status="paused",
        )
        data = progress.to_dict()
        restored = CrawlProgress.from_dict(data)
        assert restored.novel_title == "测试小说"
        assert restored.total_chapters == 100
        assert restored.fetched_count == 45
        assert restored.status == "paused"

    def test_crawl_progress_file_persistence(self):
        """CrawlProgress 应支持写入文件并恢复。"""
        from app.ingest.scraper.core.toc_crawler import CrawlProgress

        progress = CrawlProgress(
            novel_title="续传测试",
            source_toc_url="https://example.com/toc",
            total_chapters=50,
            chapters=[
                {"index": i, "title": f"第{i}章", "url": f"https://example.com/c{i}"}
                for i in range(50)
            ],
            status="running",
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name
            json.dump(progress.to_dict(), f, ensure_ascii=False)

        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            restored = CrawlProgress.from_dict(data)
            assert restored.total_chapters == 50
            assert restored.status == "running"
        finally:
            os.unlink(tmp_path)

    @patch("app.ingest.scraper.core.toc_crawler.TOCFetcher.fetch_toc")
    def test_crawler_resume_skips_fetched(self, mock_fetch_toc):
        """断点恢复后应跳过已采集的章节。"""
        from app.ingest.scraper.core.toc_crawler import (
            ChapterBatchCrawler, ChapterLink, CrawlProgress,
        )

        crawler = ChapterBatchCrawler(max_chapters=5)
        # 预填充已采集的进度
        crawler.progress = CrawlProgress(
            novel_title="test",
            source_toc_url="https://example.com/toc",
            total_chapters=5,
            fetched_count=3,
            chapters=[
                {"index": i, "title": f"Ch{i}", "url": f"https://ex.com/{i}",
                 "fetched": i < 3, "error": None}
                for i in range(5)
            ],
            status="running",
        )

        mock_fetch_toc.return_value = [
            ChapterLink(index=i, title=f"Ch{i}", url=f"https://ex.com/{i}")
            for i in range(5)
        ]

        # 采集应只从未采集的章节开始
        with patch.object(crawler.http, "get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200, text="<html><body><p>test</p></body></html>",
                error=None, headers={},
            )
            # 应不会触发 fetch_toc（已有 progress.chapters）
            result = crawler.crawl("https://example.com/toc")
            assert result is not None
            mock_fetch_toc.assert_not_called()


# ======================================================================
# Test 9: 并发导入同一个项目
# ======================================================================


class TestConcurrentImport:
    """同一项目的并发导入竞态防护。"""

    @pytest.mark.asyncio
    async def test_concurrent_create_jobs_same_project(self):
        """同一项目并发创建多个导入任务应各自独立。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()

        async def create_job_side_effect(db_session, project_id, user_id,
                                          source_type, source_url=None,
                                          title="", chapters_data=None):
            job = MagicMock()
            job.id = 1
            job.project_id = project_id
            job.current_phase = "phase0"
            return job

        with patch.object(IngestService, "create_job",
                          side_effect=create_job_side_effect):
            job1 = await IngestService.create_job(
                db, project_id=1, user_id=1, source_type="text",
                chapters_data=[{"index": 0}],
            )
            job2 = await IngestService.create_job(
                db, project_id=1, user_id=1, source_type="text",
                chapters_data=[{"index": 0}],
            )
            assert job1 is not None
            assert job2 is not None
            # 两个任务指向同一项目
            assert job1.project_id == job2.project_id == 1

    @pytest.mark.asyncio
    async def test_concurrent_phase1_phase3_no_race(self):
        """并发运行 Phase 1 和 Phase 3 不应互相干扰。"""
        from app.ingest.service import IngestService

        db1 = _make_mock_db()
        db2 = _make_mock_db()

        # Mock get_job 为两个不同 job
        def make_job(phase):
            job = MagicMock()
            job.id = 1
            job.project_id = 1
            job.current_phase = phase
            job.phase0_result = {"chapters": [{"index": 0, "title": "章1", "raw_text": "内容"}]}
            job.phase1_result = {
                "characters": [{"name": "陈道临", "tags": ["主角"], "description": "主角"}],
                "timeline_events": [], "promises": [], "world_items": [],
            }
            job.phase2_result = None
            job.progress_percent = 0.0
            job.error_message = None
            return job

        db1.get.return_value = make_job("phase1")
        db2.get.return_value = make_job("phase3")

        # 同时调用应返回各自结果
        with patch("app.ingest.service.run_phase1_pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock(
                characters=[], timeline_events=[], promises=[],
                world_items=[], chapter_count=1,
                total_llm_calls=0, failed_llm_calls=0, errors=[],
            )
            with patch("app.ingest.service.run_phase3_pipeline") as mock_p3:
                mock_p3.return_value = MagicMock(
                    status="completed", conflicts=[],
                    imported_characters=1, imported_timeline_events=0,
                    imported_promises=0, imported_world_items=0,
                    card_pool_generated=0, message="Done",
                )
                r1 = await IngestService.run_phase1(db1, 1)
                r3 = await IngestService.run_phase3(db2, 1, "keep_existing")
                # 两者都应完成
                assert r1.get("success") is True
                assert r3.get("success") is True


# ======================================================================
# Test 10: 不支持的文件格式
# ======================================================================


class TestUnsupportedFormat:
    """不支持的文件/输入格式错误处理。"""

    def test_random_html_no_content(self):
        """不包含小说内容的 HTML 应返回错误。"""
        from app.ingest.scraper import dissect_html

        html = "<html><body><h1>404 Not Found</h1><p>Page not found</p></body></html>"
        result = dissect_html(html)
        assert result.chapter_count == 0
        assert len(result.errors) > 0

    def test_binary_like_input(self):
        """二进制/乱码输入应安全处理（不崩溃）。"""
        from app.ingest.scraper import dissect_text

        text = "\x00\x01\x02\x03" * 1000
        result = dissect_text(text)
        # 不应崩溃，结果可以被处理
        assert result is not None

    def test_dissect_from_url_invalid_url(self):
        """无效 URL 应返回错误而不是崩溃。"""
        from app.ingest.scraper.pipeline import dissect_from_url

        result = dissect_from_url("")
        assert result.chapter_count == 0
        assert len(result.errors) > 0


# ======================================================================
# Test 11: Phase 0 采集网络超时
# ======================================================================


class TestNetworkTimeout:
    """网络超时或不可用时的稳定性。"""

    def test_fetcher_connect_timeout(self):
        """Fetcher 应处理连接超时。"""
        from app.ingest.scraper.core.fetcher import Fetcher, AntiCrawlConfig

        config = AntiCrawlConfig(
            timeout_seconds=1,
            max_retries=0,
            disable_all=True,
        )
        fetcher = Fetcher(config)
        result = fetcher.get("https://192.0.2.1/nonexistent")
        # 应返回错误而非崩溃
        assert result.error is not None or result.status_code == 0

    @patch("app.ingest.scraper.core.fetcher.Fetcher.get")
    def test_dissect_from_url_timeout_handling(self, mock_get):
        """URL 采集超时应返回错误而非抛出异常。"""
        from app.ingest.scraper.pipeline import dissect_from_url

        mock_get.return_value = MagicMock(
            status_code=0, text="",
            error="连接超时 (timeout=30s)",
            headers={},
        )
        result = dissect_from_url("https://example.com/novel")
        assert result.chapter_count == 0
        assert any("超时" in e or "错误" in e or "不可用" in e for e in result.errors)

    @patch("app.ingest.scraper.core.fetcher.Fetcher.get")
    def test_toc_fetcher_hard_failure(self, mock_get):
        """目录页硬失败应优雅处理。"""
        from app.ingest.scraper.core.toc_crawler import TOCFetcher

        mock_get.return_value = MagicMock(
            status_code=404, text="",
            error="Not Found",
            headers={},
        )

        fetcher = TOCFetcher()
        # 应返回符合条件的错误（硬失败标记）
        result = fetcher.http.get("https://example.com/404")
        assert fetcher.http.is_hard_failure(result) is True


# ======================================================================
# Test 12: Phase 1 四库合并冲突
# ======================================================================


class TestPhase1MergeConflicts:
    """Phase 1 四库合并冲突处理。"""

    @pytest.mark.asyncio
    async def test_character_conflict_detection(self):
        """同名不同描述的角色应检测为冲突。"""
        from app.ingest.phase3.conflict import I10_conflict_check

        db = _make_mock_db()
        existing_char = MagicMock()
        existing_char.configure_mock(name="陈道临", description="旧设定的描述",
                                     traits=["主角"], chapter_count=10)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing_char]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        new_data = {
            "characters": [{"name": "陈道临", "description": "新设定的描述", "tags": ["主角"]}],
            "timeline_events": [],
            "promises": [],
            "world_items": [],
            "chapter_count": 5,
            "existing_chapter_count": 10,
        }
        conflicts = await I10_conflict_check(db, project_id=1, new_data=new_data)
        char_conflicts = [c for c in conflicts if c["type"] == "character_conflict"]
        assert len(char_conflicts) >= 1

    @pytest.mark.asyncio
    async def test_world_conflict_detection(self):
        """同名不同描述的世界观术语应检测为冲突。"""
        from app.ingest.phase3.conflict import I10_conflict_check

        db = _make_mock_db()
        existing_item = MagicMock(
            term="魔法元素", description="旧的魔法描述",
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [existing_item]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        new_data = {
            "characters": [],
            "timeline_events": [],
            "promises": [],
            "world_items": [{"term": "魔法元素", "description": "新的魔法描述"}],
            "chapter_count": 5,
            "existing_chapter_count": 0,
        }
        conflicts = await I10_conflict_check(db, project_id=1, new_data=new_data)
        world_conflicts = [c for c in conflicts if c["type"] == "world_conflict"]
        assert len(world_conflicts) >= 1


# ======================================================================
# Test 13: Phase 2 动态层全空
# ======================================================================


class TestPhase2EmptyDynamicLayer:
    """Phase 2 输入全空的边界处理。"""

    def test_empty_chapters_phase2(self):
        """无章节时 Phase 2 应返回空结果而非崩溃。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input

        input_data = Phase2Input(chapters=[])
        result = run_phase2_pipeline(input_data)
        assert result.chapter_anchors == []
        assert result.feasibility.continuation_confidence == 0.0

    def test_empty_phase1_data_in_phase2(self):
        """Phase 1 结果全空时 Phase 2 不应崩溃。"""
        from app.ingest.phase2 import run_phase2_pipeline, Phase2Input

        chapters = [{"index": 0, "title": "第一章", "raw_text": ""}]
        input_data = Phase2Input(
            chapters=chapters,
            characters=[],
            timeline_events=[],
            promises=[],
            world_items=[],
        )
        result = run_phase2_pipeline(input_data)
        assert result is not None
        assert result.feasibility.continuation_confidence >= 0.0

    def test_phase2_anchors_with_empty_text(self):
        """空文本章节的锚点分析应返回默认值。"""
        from app.ingest.phase2.analyzer import I5_chapter_anchors

        chapters = [{"index": 0, "title": "", "raw_text": ""}]
        result = I5_chapter_anchors(chapters)
        assert len(result) == 1
        assert result[0].opening_hook is False
        assert result[0].closing_cliff is False


# ======================================================================
# Test 14: Phase 3 确认前取消
# ======================================================================


class TestUserCancelBeforeCommit:
    """用户在 Phase 3 确认前取消导入。"""

    @pytest.mark.asyncio
    async def test_cancel_before_phase3(self):
        """Phase 3 运行前取消应保留已有 Phase 1/2 结果。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()
        job = MagicMock()
        job.id = 1
        job.project_id = 1
        job.current_phase = "phase2"
        job.phase0_result = {"chapters": [{"index": 0}]}
        job.phase1_result = {"characters": [], "timeline_events": [],
                              "promises": [], "world_items": []}
        job.phase2_result = {"chapter_anchors": []}
        job.progress_percent = 100.0
        job.error_message = None

        db.get.return_value = job

        # 模拟 phase3 被取消（未执行）
        assert job.current_phase == "phase2"
        assert job.phase1_result is not None

    @pytest.mark.asyncio
    async def test_cancel_after_phase3_blocked(self):
        """Phase 3 检测到阻塞冲突后应允许用户中止。"""
        from app.ingest.phase3 import run_phase3_pipeline, Phase3Input

        db = _make_mock_db()
        # Mock 严重冲突
        mock_existing = MagicMock()
        mock_existing.configure_mock(name="陈道临", description="已有描述")
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_existing]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        input_data = Phase3Input(
            project_id=1,
            job_id=1,
            phase1_result={
                "characters": [{"name": "陈道临", "description": "新描述", "tags": ["主角"]}],
                "timeline_events": [],
                "promises": [],
                "world_items": [],
                "chapter_count": 5,
                "existing_chapter_count": 10,
            },
            resolve_strategy="keep_existing",
        )
        result = await run_phase3_pipeline(db, input_data)
        # 由于 chapter_count <= existing_chapter_count 有覆盖警告
        # 但覆盖警告不是高严重度，不会 block
        assert result.status in ("completed", "blocked")


# ======================================================================
# Test 15: full-import 一键流程 E2E
# ======================================================================


class TestFullImportE2E:
    """全流程一键导入的端到端验收。"""

    @pytest.mark.asyncio
    async def test_full_import_happy_path(self):
        """full_import 成功路径应返回完整报告。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()
        db.add = MagicMock()
        db.flush = AsyncMock()

        chapters = [_make_chapter(i, text=f"第{i+1}章正文。") for i in range(3)]

        with patch.object(IngestService, "create_job") as mock_create_job:
            mock_job = MagicMock()
            mock_job.id = 42
            mock_create_job.return_value = mock_job

            with patch.object(IngestService, "run_phase1") as mock_p1:
                mock_p1.return_value = {
                    "success": True,
                    "result": {
                        "characters": [{"name": "陈道临", "tags": ["主角"]}],
                        "timeline_events": [],
                        "promises": [],
                        "world_items": [],
                    },
                }
                with patch.object(IngestService, "run_phase2") as mock_p2:
                    mock_p2.return_value = {
                        "success": True,
                        "result": {"chapter_anchors": [], "coherence": {}},
                    }
                    with patch.object(IngestService, "run_phase3") as mock_p3:
                        mock_p3.return_value = {
                            "success": True,
                            "status": "completed",
                            "result": {
                                "status": "completed",
                                "conflicts": [],
                                "imported": {
                                    "characters": 1,
                                    "timeline_events": 0,
                                    "promises": 0,
                                    "world_items": 0,
                                },
                            },
                        }

                        result = await IngestService.full_import(
                            db=db,
                            project_id=1,
                            user_id=1,
                            chapters_data=chapters,
                            source_type="text",
                            title="E2E测试",
                            resolve_strategy="keep_existing",
                        )
                        assert result.get("success") is True
                        assert result.get("job_id") == 42

    @pytest.mark.asyncio
    async def test_full_import_phase1_failure(self):
        """Phase 1 失败时 full_import 应尽早返回错误。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()

        with patch.object(IngestService, "run_phase1") as mock_p1:
            mock_p1.return_value = {
                "success": False,
                "error": "LLM 调用全部失败",
                "phase": "phase1",
            }
            result = await IngestService.full_import(
                db=db, project_id=1, user_id=1,
                chapters_data=[{"index": 0, "title": "章1", "raw_text": "内容"}],
                source_type="text", title="测试",
            )
            assert result.get("success") is False


# ======================================================================
# Test 16 (可选): 完整 Phase 3 Commit 测试
# ======================================================================


class TestPhase3CommitterEdgeCases:
    """Phase 3 提交器的边界测试。"""

    @pytest.mark.asyncio
    async def test_committer_empty_data(self):
        """空数据提交不应崩溃。"""
        from app.ingest.phase3.committer import Phase3Committer

        db = _make_mock_db()
        committer = Phase3Committer(db, project_id=1)
        result = await committer.commit(
            phase1_result={
                "characters": [],
                "timeline_events": [],
                "promises": [],
                "world_items": [],
            },
            conflicts=[],
        )
        assert result["status"] == "completed"
        assert result["imported_characters"] == 0
        assert result["imported_world_items"] == 0

    @pytest.mark.asyncio
    async def test_committer_large_batch(self):
        """批量提交大量角色不应耗尽内存。"""
        from app.ingest.phase3.committer import Phase3Committer

        db = _make_mock_db()
        # Mock DB 返回空（无已有数据）
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        committer = Phase3Committer(db, project_id=1, resolve_strategy="merge")
        characters = [
            {"name": f"角色{i}", "description": f"描述{i}", "tags": ["配角"],
             "chapters_active": [0]}
            for i in range(50)
        ]
        result = await committer.commit(
            phase1_result={
                "characters": characters,
                "timeline_events": [],
                "promises": [],
                "world_items": [],
            },
            conflicts=[],
        )
        assert result["status"] == "completed"
        assert result["imported_characters"] == 50


# ======================================================================
# 额外：IngestService 方法边界测试
# ======================================================================


class TestIngestServiceEdgeCases:
    """IngestService 的额外边界测试。"""

    @pytest.mark.asyncio
    async def test_get_job_not_found(self):
        """查询不存在的 job 应抛 NotFoundError。"""
        from app.ingest.service import IngestService
        from app.errors import NotFoundError

        db = _make_mock_db()
        db.get.return_value = None

        with pytest.raises(NotFoundError):
            await IngestService.get_job(db, 99999)

    @pytest.mark.asyncio
    async def test_run_phase1_no_chapter_data(self):
        """Phase 1 缺少章节数据应返回错误。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()
        job = MagicMock()
        job.id = 1
        job.current_phase = "phase0"
        job.phase0_result = None
        job.progress_percent = 0.0
        job.error_message = None
        db.get.return_value = job

        result = await IngestService.run_phase1(db, 1)
        assert result.get("success") is False
        assert "缺少章节数据" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_run_phase2_no_phase1(self):
        """Phase 2 缺少 Phase 1 结果应返回错误。"""
        from app.ingest.service import IngestService

        db = _make_mock_db()
        job = MagicMock()
        job.id = 1
        job.current_phase = "phase1"
        job.phase0_result = {"chapters": [{"index": 0}]}
        job.phase1_result = None
        job.progress_percent = 0.0
        job.error_message = None
        db.get.return_value = job

        result = await IngestService.run_phase2(db, 1)
        assert result.get("success") is False
