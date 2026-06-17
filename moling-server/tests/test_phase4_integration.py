"""
Phase 4 集成测试（E2E）

验证完整生成流水线：
1. 用户输入 → 2. LLM生成 → 3. Phase 4收纳 → 4. 健康监控

测试策略：
- 数据库测试：仅在 Linux/macOS 可运行（Windows greenlet 局限）
- 纯逻辑测试：全平台可运行（SourceTextGrounding）
- URL: sqlite+aiosqlite:// (内存数据库)
"""

import platform
import asyncio

import pytest

IS_WINDOWS = platform.system() == "Windows"


# ===================================================================
# 纯逻辑测试（全平台）
# ===================================================================

class TestSourceTextGrounding:
    """测试内容安全验证"""

    @pytest.mark.asyncio
    async def test_grounding_pass(self):
        """Source Text Grounding 通过（实体在原文中有匹配）。"""
        from app.service.phase4_scheduler import Phase4Scheduler

        scheduler = Phase4Scheduler()

        # 构造 chapter_analysis（类似 _extract_chapter_analysis 的输出）
        analysis = {
            "characters": [
                {"name": "张三", "source_text": "张三", "role": "主角"},
                {"name": "城门大战", "source_text": "城门与敌人大战", "type": "event"},
            ],
            "segments": ["城门", "大战", "张三"],
        }
        chapter_text = "张三在城门与敌人大战，表现出色。"

        result = await scheduler._verify_source_text(chapter_text, analysis)

        assert result["passed"] is True
        assert len(result.get("skipped_items", [])) == 0
        print("✅ Source Text Grounding 通过测试")

    @pytest.mark.asyncio
    async def test_grounding_skip_missing_source(self):
        """缺少 source_text 的条目被跳过。"""
        from app.service.phase4_scheduler import Phase4Scheduler

        scheduler = Phase4Scheduler()
        analysis = {
            "characters": [
                {"name": "王五", "source_text": "", "role": "反派"},
            ],
            "segments": [],
        }
        chapter_text = "张三在城门与敌人大战。"

        result = await scheduler._verify_source_text(chapter_text, analysis)

        assert result["passed"] is False
        assert len(result.get("skipped_items", [])) > 0
        print("✅ Source Text Grounding 缺失 source_text 跳过测试")

    @pytest.mark.asyncio
    async def test_grounding_empty_analysis(self):
        """空分析结果应通过验证。"""
        from app.service.phase4_scheduler import Phase4Scheduler

        scheduler = Phase4Scheduler()
        analysis = {"characters": [], "segments": []}
        chapter_text = ""

        result = await scheduler._verify_source_text(chapter_text, analysis)

        assert result["passed"] is True
        print("✅ Source Text Grounding 空分析通过测试")


# ===================================================================
# 数据库集成测试（仅 Linux/macOS）
# ===================================================================

if not IS_WINDOWS:
    from unittest.mock import AsyncMock, patch
    from datetime import datetime, timezone
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select

    from app.models.base import Base

    # ------------------------------------------------------------------
    # 辅助函数
    # ------------------------------------------------------------------

    async def ensure_project(db, pid="proj-test-001"):
        from app.models import Project
        if await db.get(Project, pid) is None:
            db.add(Project(
                id=pid, title="测试项目", genre="玄幻",
                novel_style="热血", status="active",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
            await db.commit()

    async def ensure_chapter(db, cid="ch-test-001", pid="proj-test-001"):
        from app.models import Chapter
        if await db.get(Chapter, cid) is None:
            db.add(Chapter(
                id=cid, project_id=pid, novel_id=pid,
                chapter_number=1, title="第一章", content="测试内容",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
            await db.commit()

    # ------------------------------------------------------------------
    # Fixture
    # ------------------------------------------------------------------

    @pytest.fixture(scope="module")
    def event_loop():
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture()
    def memory_db():
        async def _make():
            engine = create_async_engine("sqlite+aiosqlite://", echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            from sqlalchemy.ext.asyncio import async_sessionmaker
            factory = async_sessionmaker(engine, expire_on_commit=False)
            session = factory()
            return session, engine
        return _make

    # ------------------------------------------------------------------
    # Phase 4 完整流水线测试
    # ------------------------------------------------------------------

    class TestPhase4FullPipeline:
        """测试完整 Phase 4 流水线"""

        @pytest.mark.asyncio
        async def test_full_pipeline_success(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)
                await ensure_chapter(db)

                from app.models import Character, PlotPromise

                db.add(Character(
                    id="char-001", project_id="proj-test-001", novel_id="proj-test-001",
                    name="张三", role="主角", status="active",
                    first_seen_chapter=1, visible_to_user=True,
                ))
                db.add(PlotPromise(
                    id="promise-001", project_id="proj-test-001", novel_id="proj-test-001",
                    promise_type="悬念", content="张三的身世之谜",
                    status="active", created_chapter=1, last_mentioned_chapter=1,
                ))
                await db.commit()

                mock_llm_response = """
                {
                    "characters": [
                        {"name": "张三", "status_change": "active", "evidence": "受伤"},
                        {"name": "李四", "role": "新角色", "status": "active", "first_seen": "首次"}
                    ],
                    "timeline": [
                        {"action": "add", "event": "城门大战", "chapter": 5}
                    ],
                    "plot_promises": [
                        {"action": "advance", "promise_id": "promise-001", "progress": "进一步展开"}
                    ],
                    "world": []
                }
                """

                with patch("app.service.phase4_service.call_llm", new_callable=AsyncMock) as m:
                    m.return_value = mock_llm_response
                    from app.service.phase4_service import phase4_service

                    result = await phase4_service.run_phase4(
                        db=db, project_id="proj-test-001",
                        chapter_id="ch-test-001",
                        chapter_text="张三在城门与敌人大战，想起幼时片段。李四首次出现。",
                        card_ids=[],
                    )

                assert result is not None
                for k in ("characters", "timeline", "plot_promises", "world"):
                    assert k in result

                # 验证李四被创建
                stmt = select(Character).where(Character.name == "李四")
                r = await db.execute(stmt)
                lisi = r.scalar_one_or_none()
                assert lisi is not None, "李四应被创建"
                assert lisi.role == "新角色"

                print("✅ 完整流水线测试通过")
            finally:
                await session.close()
                await engine.dispose()

        @pytest.mark.asyncio
        async def test_llm_failure_degradation(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)
                await ensure_chapter(db)

                with patch("app.service.phase4_service.call_llm", new_callable=AsyncMock) as m:
                    m.side_effect = Exception("LLM服务不可用")
                    from app.service.phase4_service import phase4_service

                    result = await phase4_service.run_phase4(
                        db=db, project_id="proj-test-001",
                        chapter_id="ch-test-001", chapter_text="测试", card_ids=[],
                    )

                assert result is not None, "失败时应优雅降级"
                print("✅ LLM失败降级测试通过")
            finally:
                await session.close()
                await engine.dispose()

    # ------------------------------------------------------------------
    # 调度器集成测试
    # ------------------------------------------------------------------

    class TestPhase4SchedulerIntegration:
        """测试调度器集成"""

        @pytest.mark.asyncio
        async def test_idempotent_dedup(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)
                await ensure_chapter(db)

                from app.service.phase4_scheduler import phase4_scheduler

                with patch.object(
                    phase4_scheduler._phase4_service, "run_phase4", new_callable=AsyncMock,
                ) as mock_run:
                    mock_run.return_value = {"characters": {}, "timeline": {}, "plot_promises": {}, "world": {}}

                    r1 = await phase4_scheduler.schedule_phase4(
                        db=db, project_id="proj-test-001",
                        chapter_id="ch-test-001", chapter_text="测试",
                    )
                    r2 = await phase4_scheduler.schedule_phase4(
                        db=db, project_id="proj-test-001",
                        chapter_id="ch-test-001", chapter_text="测试",
                    )

                assert r1["status"] in ("success", "queued")
                if isinstance(r2, dict) and "status" in r2:
                    assert r2["status"] in ("already_done", "success", "queued")
                assert mock_run.call_count == 1, f"期望1次，实际{mock_run.call_count}"
                print("✅ 调度器幂等去重测试通过")
            finally:
                await session.close()
                await engine.dispose()

        @pytest.mark.asyncio
        async def test_concurrent_lock(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)
                await ensure_chapter(db, cid="ch-lock-01")

                from app.service.phase4_scheduler import phase4_scheduler

                with patch.object(
                    phase4_scheduler._phase4_service, "run_phase4", new_callable=AsyncMock,
                ) as mock_run:
                    async def slow_run(*a, **kw):
                        await asyncio.sleep(0.05)
                        return {"characters": {}, "timeline": {}, "plot_promises": {}, "world": {}}
                    mock_run.side_effect = slow_run

                    results = await asyncio.gather(
                        phase4_scheduler.schedule_phase4(
                            db=db, project_id="proj-test-001", chapter_id="ch-lock-01", chapter_text="A",
                        ),
                        phase4_scheduler.schedule_phase4(
                            db=db, project_id="proj-test-001", chapter_id="ch-lock-01", chapter_text="B",
                        ),
                        return_exceptions=True,
                    )

                successes = [
                    r for r in results
                    if isinstance(r, dict) and r.get("status") in ("success", "queued")
                ]
                assert len(successes) >= 1
                print("✅ 调度器写锁机制测试通过")
            finally:
                await session.close()
                await engine.dispose()

    # ------------------------------------------------------------------
    # 健康监控集成测试
    # ------------------------------------------------------------------

    class TestHealthMonitorIntegration:
        """测试健康监控集成"""

        @pytest.mark.asyncio
        async def test_health_r1_alert(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)

                from app.models import SubPlot, SubPlotStatusLog

                db.add(SubPlot(
                    id="sp-001", project_id="proj-test-001", novel_id="proj-test-001",
                    title="张三的身世之谜", status="active",
                    created_chapter=1, last_advancement_chapter=1, health_status="green",
                ))
                db.add(SubPlotStatusLog(
                    id="log-001", subplot_id="sp-001", project_id="proj-test-001",
                    chapter=1, event_type="advance", old_status="active", new_status="active",
                ))
                await db.commit()

                from app.service.health_monitor import health_monitor_service

                result = await health_monitor_service.check_health(
                    db=db, project_id="proj-test-001", current_chapter=10,
                )

                assert len(result["alerts"]) > 0
                r1 = [a for a in result["alerts"] if a.get("rule") == "R1"]
                assert len(r1) > 0
                assert r1[0].get("severity") == "yellow"

                sp = await db.get(SubPlot, "sp-001")
                await db.refresh(sp)
                assert sp.health_status == "yellow"
                print("✅ 健康监控 R1 告警测试通过")
            finally:
                await session.close()
                await engine.dispose()

        @pytest.mark.asyncio
        async def test_health_within_window_no_alert(self, memory_db):
            factory = memory_db
            session, engine = await factory()
            try:
                db = session
                await ensure_project(db)

                from app.models import SubPlot, SubPlotStatusLog

                db.add(SubPlot(
                    id="sp-002", project_id="proj-test-001", novel_id="proj-test-001",
                    title="李四的复仇", status="active",
                    created_chapter=8, last_advancement_chapter=8, health_status="green",
                ))
                db.add(SubPlotStatusLog(
                    id="log-002", subplot_id="sp-002", project_id="proj-test-001",
                    chapter=8, event_type="advance", old_status="active", new_status="active",
                ))
                await db.commit()

                from app.service.health_monitor import health_monitor_service

                result = await health_monitor_service.check_health(
                    db=db, project_id="proj-test-001", current_chapter=10,
                )

                r1 = [a for a in result["alerts"] if a.get("subplot_id") == "sp-002"]
                assert len(r1) == 0
                print("✅ 窗口内无告警测试通过")
            finally:
                await session.close()
                await engine.dispose()

else:
    # Windows: 数据库测试占位（自动跳过）
    class TestPhase4FullPipeline:
        @pytest.mark.skip(reason="Windows: greenlet 不可用，跳过数据库测试")
        def test_placeholder(self):
            pass

    class TestPhase4SchedulerIntegration:
        @pytest.mark.skip(reason="Windows: greenlet 不可用，跳过数据库测试")
        def test_placeholder(self):
            pass

    class TestHealthMonitorIntegration:
        @pytest.mark.skip(reason="Windows: greenlet 不可用，跳过数据库测试")
        def test_placeholder(self):
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
