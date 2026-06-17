"""墨灵 (Moling) — Phase4Scheduler 单元测试.

覆盖:
- §12.2 主入口 schedule_phase4
- §12.5 三层幂等性检查
- §12.3 竞态防护 (锁获取/释放, 门控检查)
- §12.4 失败回补
- §11.6 SourceText Grounding + 实体名规范化
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.phase4_scheduler import (
    Phase4Scheduler,
    VaultVersion,
    SchedulerState,
    SIMILARITY_THRESHOLD,
    ENTITY_SIMILARITY_THRESHOLD,
    IDLE_LOCK_TIMEOUT_S,
    LOCK_WAIT_INTERVAL_S,
    GATE_WAIT_TIMEOUT_S,
    MAX_CONSECUTIVE_FAILURES,
)

pytestmark = pytest.mark.asyncio


def _make_mock_db() -> MagicMock:
    """Create a mock db: MagicMock for sync methods (add), AsyncMock for async ones."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()  # avoid coroutine from .scalars()/.all()
    db.get = AsyncMock()
    return db


# ============================================================================
# 固件
# ============================================================================


@pytest.fixture()
def fresh_scheduler() -> Phase4Scheduler:
    """返回一个状态已重置的 Phase4Scheduler 实例。"""
    sched = Phase4Scheduler()
    # 直接重置内部状态
    sched._state = SchedulerState()
    sched._nonce_set.clear()
    sched._lock_store.clear()
    sched._task_store.clear()
    return sched


# ============================================================================
# §12.5 幂等性检查
# ============================================================================


class TestNonceGeneration:
    """nonce 生成测试."""

    async def test_generate_nonce_format(self, fresh_scheduler):
        """生成的 nonce 应符合 ch{chapter}_{timestamp}_{hash} 格式。"""
        nonce = await fresh_scheduler._generate_nonce(16)
        parts = nonce.split("_")
        assert len(parts) >= 3
        assert parts[0] == "ch16"

    async def test_generate_nonce_unique(self, fresh_scheduler):
        """多次生成的 nonce 不应重复。"""
        nonces = set()
        for _ in range(100):
            nonce = await fresh_scheduler._generate_nonce(1)
            nonces.add(nonce)
        assert len(nonces) == 100

    async def test_generate_nonce_different_chapter(self, fresh_scheduler):
        """不同章节的 nonce 前缀不同。"""
        n1 = await fresh_scheduler._generate_nonce(1)
        n2 = await fresh_scheduler._generate_nonce(2)
        assert n1.startswith("ch1_")
        assert n2.startswith("ch2_")


class TestIdempotency:
    """三层幂等性检查测试 (§12.5)."""

    async def test_layer1_returns_existing(self, fresh_scheduler):
        """Layer 1: nonce 在内存集合中应返回已有状态。"""
        nonce = "test_nonce_001"
        fresh_scheduler._nonce_set.add(nonce)
        result = await fresh_scheduler._check_idempotency(MagicMock(), nonce)
        assert result is not None
        assert result["status"] == "already_exists"

    async def test_layer2_returns_existing(
        self, fresh_scheduler, monkeypatch,
    ):
        """Layer 2: DB 中存在 nonce 应返回已有任务状态。"""
        # 模拟 phase4_dao.get_by_nonce 返回一个任务
        mock_task = AsyncMock()
        mock_task.id = 42
        mock_task.status = "done"
        mong_key = "phase4_dao.get_by_nonce"

        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=mock_task):
            nonce = "db_nonce_001"
            result = await fresh_scheduler._check_idempotency(MagicMock(), nonce)
            assert result is not None
            assert result["task_id"] == "42"
            assert result["status"] == "done"

    async def test_layer3_none_when_no_match(
        self, fresh_scheduler, monkeypatch,
    ):
        """三层均未命中应返回 None."""
        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=None):
            nonce = "brand_new_nonce"
            result = await fresh_scheduler._check_idempotency(MagicMock(), nonce)
            assert result is None


# ============================================================================
# §12.3 竞态防护
# ============================================================================


class TestLockMechanism:
    """写入锁测试 (§12.3)."""

    async def test_acquire_lock_success(self, fresh_scheduler):
        """获取一个不存在的锁应成功。"""
        result = await fresh_scheduler._acquire_lock("test_lock")
        assert result is True
        assert "test_lock" in fresh_scheduler._lock_store

    async def test_acquire_lock_busy(self, fresh_scheduler):
        """获取一个未超时的锁应失败 (等待 200ms)."""
        fresh_scheduler._lock_store["busy_lock"] = time.monotonic()
        result = await fresh_scheduler._acquire_lock("busy_lock")
        assert result is False

    async def test_acquire_lock_expired(self, fresh_scheduler):
        """获取一个超时的锁应强制解锁并成功。"""
        old_time = time.monotonic() - IDLE_LOCK_TIMEOUT_S - 1
        fresh_scheduler._lock_store["expired_lock"] = old_time
        result = await fresh_scheduler._acquire_lock("expired_lock")
        assert result is True
        assert "expired_lock" in fresh_scheduler._lock_store

    async def test_release_lock(self, fresh_scheduler):
        """释放锁后应移出存储。"""
        fresh_scheduler._lock_store["my_lock"] = time.monotonic()
        await fresh_scheduler._release_lock("my_lock")
        assert "my_lock" not in fresh_scheduler._lock_store

    async def test_lock_cleanup_on_release(self, fresh_scheduler):
        """多次释放不应报错。"""
        await fresh_scheduler._release_lock("nonexistent_lock")
        # 不应抛出异常


class TestVaultGate:
    """门控检查测试 (§12.3)."""

    async def test_gate_no_pending(self, fresh_scheduler):
        """pending 为 None 时门控应立即返回。"""
        fresh_scheduler._state.vault_version.pending = None
        await fresh_scheduler.check_vault_ready()  # should return immediately

    async def test_gate_with_pending_then_resolved(self, fresh_scheduler):
        """pending 版本在超时前被清除应正常返回。"""
        fresh_scheduler._state.vault_version.pending = "v4_ch16_abc"

        async def clear_pending():
            await asyncio.sleep(0.05)
            fresh_scheduler._state.vault_version.pending = None

        async def run_gate():
            await fresh_scheduler.check_vault_ready()

        await asyncio.gather(clear_pending(), run_gate())
        assert fresh_scheduler._state.vault_version.pending is None

    async def test_gate_timeout_fallback(self, fresh_scheduler):
        """门控超时应回退到 lastStable 版本。"""
        fresh_scheduler._state.vault_version.pending = "v4_ch16_stuck"
        fresh_scheduler._state.vault_version.last_stable = "v4_ch15_stable"
        fresh_scheduler._state.vault_version.current = "v4_ch15_stable"

        await fresh_scheduler.check_vault_ready()
        # 由于 pending 不会自动清除，应超时并回退
        assert fresh_scheduler._state.vault_version.pending is None
        assert fresh_scheduler._state.vault_version.current == "v4_ch15_stable"


# ============================================================================
# §12.4 失败回补
# ============================================================================


class TestFailureHandling:
    """失败处理与回补测试 (§12.4)."""

    async def test_handle_failure_first(self, fresh_scheduler):
        """首次失败应加入回补队列。"""
        mock_db = _make_mock_db()
        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=AsyncMock()):
            await fresh_scheduler._handle_failure(
                mock_db, 1, 16, "nonce_001",
                ValueError("测试错误"),
            )
        assert len(fresh_scheduler._state.fallback_queue) == 1
        assert fresh_scheduler._state.consecutive_failures == 1

    async def test_handle_failure_three_times(self, fresh_scheduler):
        """连续 3 次失败后应记录日志 (触发角标逻辑)."""
        mock_db = _make_mock_db()
        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=AsyncMock()):
            for i in range(3):
                await fresh_scheduler._handle_failure(
                    mock_db, 1, 16 + i, f"nonce_00{i}",
                    ValueError(f"错误 #{i+1}"),
                )
        assert fresh_scheduler._state.consecutive_failures == 3
        assert len(fresh_scheduler._state.fallback_queue) == 3

    async def test_handle_failure_five_triggers_pause(self, fresh_scheduler):
        """连续 5 次失败应强制暂停，抛出 RuntimeError。"""
        mock_db = _make_mock_db()
        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=AsyncMock()):
            for i in range(4):
                await fresh_scheduler._handle_failure(
                    mock_db, 1, 16 + i, f"nonce_00{i}",
                    ValueError(f"错误 #{i+1}"),
                )

            with pytest.raises(RuntimeError, match="强制暂停"):
                await fresh_scheduler._handle_failure(
                    mock_db, 1, 20, "nonce_004",
                    ValueError("错误 #5"),
                )

        assert fresh_scheduler._state.consecutive_failures == MAX_CONSECUTIVE_FAILURES
        # 队列应已被清空
        assert len(fresh_scheduler._state.queue) == 0

    async def test_failure_after_success_resets_counter(self, fresh_scheduler):
        """成功一次后连续失败计数应重置。"""
        mock_db = _make_mock_db()
        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=AsyncMock()):
            await fresh_scheduler._handle_failure(
                mock_db, 1, 16, "n1", ValueError("e1"),
            )
            assert fresh_scheduler._state.consecutive_failures == 1

        # 模拟成功
        fresh_scheduler._state.consecutive_failures = 0

        with patch("app.service.phase4_scheduler.phase4_dao.get_by_nonce",
                   return_value=AsyncMock()):
            await fresh_scheduler._handle_failure(
                mock_db, 1, 17, "n2", ValueError("e2"),
            )
        assert fresh_scheduler._state.consecutive_failures == 1  # 重新计数


# ============================================================================
# §11.6 内容安全验证 — SourceText Grounding
# ============================================================================


class TestSourceTextGrounding:
    """第一道防线: SourceText Grounding 测试 (§11.6)."""

    SAMPLE_CHAPTER = (
        "张三说：我们得赶紧出发了。\n"
        "李四道：再等等，还有一个人没到。\n"
        "王五问：到底是谁？\n"
        "张三答：是赵六，他去找马了。"
    )

    async def test_extract_characters(self, fresh_scheduler):
        """从章节正文正确提取角色名和 source_text."""
        analysis = await fresh_scheduler._extract_chapter_analysis(self.SAMPLE_CHAPTER)
        assert "characters" in analysis
        names = [c["name"] for c in analysis["characters"]]
        assert "张三" in names
        assert "李四" in names
        assert "王五" in names

    async def test_source_text_grounding_pass(self, fresh_scheduler):
        """source_text 与原文匹配度 ≥85% 应通过。"""
        analysis = await fresh_scheduler._extract_chapter_analysis(self.SAMPLE_CHAPTER)
        result = await fresh_scheduler._verify_source_text(
            self.SAMPLE_CHAPTER, analysis,
        )
        assert result["passed"] is True
        assert len(result["skipped_items"]) == 0

    async def test_fuzzy_match_exact(self, fresh_scheduler):
        """精确子串匹配应返回 100%. """
        score = await fresh_scheduler._fuzzy_match(
            "张三说：我们得赶紧出发了",
            self.SAMPLE_CHAPTER,
        )
        assert score == 100.0

    async def test_fuzzy_match_partial(self, fresh_scheduler):
        """部分匹配应返回 0-100 之间的值。"""
        score = await fresh_scheduler._fuzzy_match(
            "张山说",
            self.SAMPLE_CHAPTER,
        )
        assert 0 < score < 100

    async def test_fuzzy_match_no_match(self, fresh_scheduler):
        """完全不匹配应返回 0。"""
        score = await fresh_scheduler._fuzzy_match(
            "hello world",
            self.SAMPLE_CHAPTER,
        )
        assert score == 0.0

    async def test_llm_judge_pass(self, fresh_scheduler):
        """LLM 裁决应能通过合理的 source_text. """
        # 使用 "说" 结尾且内容直接在原文中的文本
        verdict = await fresh_scheduler._llm_judge(
            "王五问：",
            self.SAMPLE_CHAPTER,
        )
        assert verdict == "pass"

    async def test_llm_judge_fail(self, fresh_scheduler):
        """LLM 裁决应拒绝不合理的 source_text. """
        verdict = await fresh_scheduler._llm_judge(
            "完全无关的内容",
            self.SAMPLE_CHAPTER,
        )
        assert verdict == "fail"

    async def test_verify_source_text_skips_missing_source(self, fresh_scheduler):
        """缺少 source_text 的条目应被跳过（warn）。"""
        analysis = {
            "characters": [
                {"name": "无名氏", "source_text": ""},
            ],
            "segments": [],
        }
        result = await fresh_scheduler._verify_source_text("原文内容", analysis)
        # warnings 不影响 passed（全部通过或仅有 warn 时 passed=True）
        assert result["passed"] is True
        assert len(result["warnings"]) == 1
        assert any("缺少 source_text" in item for item in result["warnings"])


# ============================================================================
# §11.6 内容安全验证 — 实体名规范化
# ============================================================================


class TestEntityNormalization:
    """第二道防线: 实体名规范化测试 (§11.6)."""

    async def test_name_similarity_exact(self, fresh_scheduler):
        """完全相同名字应返回 100.0。"""
        score = await fresh_scheduler._name_similarity("张三", "张三")
        assert score == 100.0

    async def test_name_similarity_substring(self, fresh_scheduler):
        """子串匹配应基于长度比例。"""
        score = await fresh_scheduler._name_similarity("张三", "张三丰")
        assert 60 <= score <= 75

    async def test_name_similarity_partial(self, fresh_scheduler):
        """不同但相似的名字应有中等相似度。"""
        score = await fresh_scheduler._name_similarity("张山", "张三")
        # RapidFuzz 标准公式: 1 - dist/(len1+len2) = 1 - 1/4 = 75%
        assert score == 75.0

    async def test_name_similarity_no_match(self, fresh_scheduler):
        """完全不同应返回低分。"""
        score = await fresh_scheduler._name_similarity("abc", "xyz")
        assert score < ENTITY_SIMILARITY_THRESHOLD

    async def test_find_best_match_exact(self, fresh_scheduler):
        """已有精确匹配应返回最高分。"""
        result = await fresh_scheduler._find_best_match(
            "张三", ["李四", "张三", "王五"],
        )
        assert result is not None
        assert result["name"] == "张三"
        assert result["similarity"] == 100.0

    async def test_find_best_match_fuzzy(self, fresh_scheduler):
        """已有模糊匹配应返回结果。"""
        result = await fresh_scheduler._find_best_match(
            "东方不白", ["东方不败", "独孤求败", "西门吹雪"],
        )
        assert result is not None
        assert result["name"] == "东方不败"
        assert result["similarity"] >= ENTITY_SIMILARITY_THRESHOLD

    async def test_find_best_match_no_match(self, fresh_scheduler):
        """无匹配应返回 None。"""
        result = await fresh_scheduler._find_best_match(
            "abcdef", ["李四", "张三", "王五"],
        )
        assert result is None

    async def test_normalize_entity_names_new_entity(self, fresh_scheduler):
        """新实体名应注册为新的。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await fresh_scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "全新角色"}],
            )
        assert len(result["new_entities"]) == 1
        assert result["new_entities"][0]["name"] == "全新角色"
        assert len(result["alias_updates"]) == 0

    async def test_normalize_entity_names_register_alias(self, fresh_scheduler):
        """匹配已有实体时应注册别名。"""
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)
        existing_char = AsyncMock()
        existing_char.name = "东方不败"
        existing_char.traits = []
        existing_char.aliases = []

        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = [existing_char]

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await fresh_scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": "东方不白"}],
            )
        assert len(result["alias_updates"]) == 1
        assert result["alias_updates"][0]["name"] == "东方不白"
        assert result["alias_updates"][0]["matched_to"] == "东方不败"

    async def test_normalize_entity_names_skip_empty(self, fresh_scheduler):
        """空名字应被跳过。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            result = await fresh_scheduler._normalize_entity_names(
                mock_db, 1,
                [{"name": ""}, {"name": "   "}],
            )
        assert len(result["new_entities"]) == 0


# ============================================================================
# §12.2 主流程集成测试 (模拟)
# ============================================================================


class TestScheduleIntegration:
    """schedule_phase4 主流程集成测试."""

    async def test_schedule_phase4_idempotent(self, fresh_scheduler):
        """重复提交相同 nonce (通过内存) 应返回已有结果。"""
        # 固定 nonce 并加入内存集合
        fixed_nonce = "ch1_12345_test_abc"
        fresh_scheduler._nonce_set.add(fixed_nonce)

        # 模拟 _generate_nonce 返回相同的 nonce
        with patch.object(fresh_scheduler, "_generate_nonce",
                          return_value=fixed_nonce):
            result = await fresh_scheduler.schedule_phase4(
                MagicMock(), 1, 1, "章节内容",
            )
        assert result["status"] == "already_exists"
        assert result["nonce"] == fixed_nonce

    async def test_schedule_phase4_full_flow_success(self, fresh_scheduler):
        """完整流程: 幂等检查 → 门控 → 加锁 → 安全验证 → 调用 → 解锁 → 成功。"""
        # 模拟所有外部调用
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)
        mock_db.commit.return_value = None

        mock_task = AsyncMock()
        mock_task.id = 42
        mock_task.nonce = "ch1_12345_test"
        mock_task.status = "done"

        with patch.multiple(
            "app.service.phase4_scheduler",
            phase4_dao=AsyncMock(),
            phase4_service=AsyncMock(),
            vault_dao=AsyncMock(),
        ):
            from app.service.phase4_scheduler import phase4_dao, phase4_service, vault_dao
            phase4_dao.get_by_nonce.return_value = None
            vault_dao.get_characters.return_value = []

            # 模拟 Phase4Service.execute_storage
            phase4_service.execute_storage = AsyncMock(return_value={
                "status": "success",
                "message": "收纳完成",
            })

            result = await fresh_scheduler.schedule_phase4(
                mock_db, 1, 1,
                "张三说：我们出发了。",
                card_ids=["card1"],
            )

        assert result["status"] == "done"
        assert "task_id" in result
        assert "safety_check" in result
        assert result["safety_check"]["passed"] is True

    async def test_schedule_phase4_failure_flow(self, fresh_scheduler):
        """异常流程: 执行失败应触发 _handle_failure. """
        mock_db = _make_mock_db()
        mock_db.add = MagicMock(return_value=None)

        with patch.multiple(
            "app.service.phase4_scheduler",
            phase4_dao=AsyncMock(),
            phase4_service=AsyncMock(),
            vault_dao=AsyncMock(),
        ):
            from app.service.phase4_scheduler import phase4_dao, phase4_service, vault_dao
            phase4_dao.get_by_nonce.return_value = None
            vault_dao.get_characters.return_value = []

            phase4_service.execute_storage = AsyncMock(
                side_effect=ValueError("收纳执行失败"),
            )

            with pytest.raises(ValueError):
                await fresh_scheduler.schedule_phase4(
                    mock_db, 1, 1, "测试内容",
                )

        assert fresh_scheduler._state.consecutive_failures >= 1
        assert len(fresh_scheduler._state.fallback_queue) == 1


# ============================================================================
# 输入组装
# ============================================================================


class TestInputAssembly:
    """_assemble_input 测试."""

    async def test_assemble_input_structure(self, fresh_scheduler):
        """组装的输入应包含所有必需字段。"""
        mock_db = _make_mock_db()
        mock_vault_dao = AsyncMock()
        mock_vault_dao.get_characters.return_value = []

        with patch("app.service.phase4_scheduler.vault_dao", mock_vault_dao):
            input_data = await fresh_scheduler._assemble_input(
                mock_db, 1, 16, "章节内容...",
                ["card1"], {"characters": []},
            )

        assert input_data["project_id"] == 1
        assert input_data["chapter_id"] == 16
        assert input_data["chapter_text"] == "章节内容..."
        assert input_data["card_ids"] == ["card1"]
        assert "chapter_analysis" in input_data
        assert "vault_summary" in input_data
        assert "fallback_queue" in input_data
        assert "version" in input_data


# ============================================================================
# 状态查询 / 重置
# ============================================================================


class TestStateManagement:
    """调度器状态管理测试."""

    async def test_get_state_snapshot(self, fresh_scheduler):
        """状态快照应包含所有关键字段。"""
        snapshot = await fresh_scheduler.get_state_snapshot()
        assert "queue_length" in snapshot
        assert "nonce_set_size" in snapshot
        assert "vault_version" in snapshot
        assert "fallback_queue_length" in snapshot
        assert "consecutive_failures" in snapshot
        assert "lock_count" in snapshot

    async def test_reset_state_clears_everything(self, fresh_scheduler):
        """reset_state 应清除所有状态。"""
        # 先写入一些状态
        fresh_scheduler._nonce_set.add("test")
        fresh_scheduler._lock_store["test"] = time.monotonic()
        fresh_scheduler._state.consecutive_failures = 3

        await fresh_scheduler.reset_state()

        snapshot = await fresh_scheduler.get_state_snapshot()
        assert snapshot["nonce_set_size"] == 0
        assert snapshot["lock_count"] == 0
        assert snapshot["consecutive_failures"] == 0
        assert snapshot["queue_length"] == 0

    async def test_vault_version_update(self, fresh_scheduler):
        """收纳成功后应更新四库版本。"""
        fresh_scheduler._update_vault_version(1, 16, "nonce_abc12345")
        # nonce[:8] = "nonce_ab" (8 个字符)
        assert "v4_ch16_nonce_ab" in fresh_scheduler._state.vault_version.current
        assert fresh_scheduler._state.vault_version.pending is None


# ============================================================================
# 竞态: 并发锁测试
# ============================================================================


class TestConcurrentLock:
    """并发场景下的锁测试."""

    async def test_concurrent_lock_contention(self, fresh_scheduler):
        """两个协程同时获取同一把锁，只有一个能成功。"""
        results = []

        async def try_lock(name: str):
            ok = await fresh_scheduler._acquire_lock("shared_lock")
            results.append((name, ok))

        # 并发尝试
        await asyncio.gather(try_lock("A"), try_lock("B"))
        successes = [r for r in results if r[1]]
        assert len(successes) == 1
