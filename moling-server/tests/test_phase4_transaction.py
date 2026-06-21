"""墨灵 (Moling) — P0-5 事务原子性保证测试.

覆盖 savepoint 嵌套事务的各种场景：
- 正常流程提交成功
- 合并失败回滚 savepoint，主事务不中断
- LLM 调用失败不触发事务
- savepoint 内部分失败 + 部分成功
- 并发事务不互相影响
- 变更日志随 savepoint 回滚
- 卡牌淘汰随 savepoint 回滚
- 主事务 commit 失败 → 完全回滚
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.phase4_service import Phase4Service


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def phase4_service() -> Phase4Service:
    """Create Phase4Service instance."""
    return Phase4Service()


@pytest.fixture
def mock_db():
    """Mock database session with savepoint support."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.get = AsyncMock()
    # savepoint (begin_nested → sp with async commit/rollback)
    mock_sp = MagicMock()
    mock_sp.commit = AsyncMock()
    mock_sp.rollback = AsyncMock()
    db.begin_nested = AsyncMock(return_value=mock_sp)
    return db


@pytest.fixture
def sample_extraction_json() -> dict:
    """Sample LLM response as parsed dict."""
    return {
        "character_updates": [
            {
                "action": "create",
                "name": "林峰",
                "changes": [{"role": "protagonist"}],
                "confidence": 0.95,
            },
        ],
        "timeline_updates": [
            {
                "action": "add",
                "event": "林峰返回城镇",
                "day": 1,
                "chapter": 1,
                "participants": ["林峰"],
                "importance": "major",
            },
        ],
        "plot_promise_updates": [
            {
                "action": "create",
                "title": "幽冥教封印松动",
                "type": "剧情转折",
                "status": "active",
            },
        ],
        "world_updates": [
            {
                "action": "create",
                "name": "幽冥教",
                "category": "faction",
                "content": "被封印百年的邪教",
            },
        ],
        "card_pool_entries": [],
    }


@pytest.fixture
def full_mock_dependencies(mock_db, sample_extraction_json):
    """Set up all mocked dependencies for a successful run_phase4 flow."""
    from app.models.chapter import Chapter

    mock_chapter = MagicMock(spec=Chapter)
    mock_chapter.id = "ch-uuid"
    mock_chapter.chapter_number = 1

    mock_db.get = AsyncMock(return_value=mock_chapter)

    patches = {
        "vault_dao": patch("app.service.phase4_service.vault_dao"),
        "card_dao": patch("app.service.phase4_service.card_dao"),
        "chapter_dao": patch("app.service.phase4_service.chapter_dao"),
        "card_retire_service": patch(
            "app.service.phase4_service.card_retire_service"
        ),
    }

    mocks = {}
    for name, p in patches.items():
        mocker = p.start()
        mocks[name] = mocker

    from app.models.vault_character import VaultCharacter

    mock_existing_char = MagicMock(spec=VaultCharacter)
    mock_existing_char.id = "char-uuid"
    mock_existing_char.name = "苏暮雪"
    mock_existing_char.chapter_count = 2

    mocks["vault_dao"].get_characters = AsyncMock(return_value=[mock_existing_char])
    mocks["vault_dao"].get_timeline = AsyncMock(return_value=[])
    mocks["vault_dao"].get_plot_promises = AsyncMock(return_value=[])
    mocks["vault_dao"].get_world_entries = AsyncMock(return_value=[])
    mocks["vault_dao"].create_character = AsyncMock()
    mocks["vault_dao"].update_character = AsyncMock()
    mocks["vault_dao"].create_timeline_event = AsyncMock()
    mocks["vault_dao"].create_plot_promise = AsyncMock()
    mocks["vault_dao"].create_world_entry = AsyncMock()

    mocks["card_dao"].get_active_cards = AsyncMock(return_value=[])

    mocks["chapter_dao"].get = AsyncMock(return_value=mock_chapter)

    mocks["card_retire_service"].check_and_retire = AsyncMock(
        return_value=MagicMock(
            retired_count=0, expired_count=0, remaining_active=10
        )
    )

    yield mock_db, mock_chapter, mocks, sample_extraction_json

    for p in patches.values():
        p.stop()


# ====================================================================
# Test 1: 正常流程提交成功
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_normal_flow(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """正常流程：LLM 调用 → savepoint → commit 全部成功。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # 验证返回结构完整
    assert "version" in result
    assert result["version"].startswith("v4_ch1_")
    assert result["chapter"] == 1
    assert "changes" in result
    assert "summary" in result
    assert "characters" in result["changes"]
    assert "timeline" in result["changes"]

    # 验证事务流程
    # LLM 调用后创建了 savepoint
    mock_db.begin_nested.assert_called_once()
    sp = await mock_db.begin_nested()
    sp.commit.assert_called_once()  # savepoint 被提交
    sp.rollback.assert_not_called()  # savepoint 未被回滚

    # 主事务提交
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()  # 主事务未被回滚


# ====================================================================
# Test 2: 合并失败回滚 savepoint，主事务不中断
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_merge_failure_savepoint_rollback(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """合并失败 → savepoint 回滚 → 主事务继续提交。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # 让 _merge_characters 抛出异常
        mocks["vault_dao"].get_characters.side_effect = ValueError("角色合并失败")

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 回滚了
    sp = await mock_db.begin_nested()
    sp.rollback.assert_called_once()
    sp.commit.assert_not_called()

    # 主事务仍然提交（savepoint 回滚不中断主事务）
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

    # 返回的 result 标记了合并失败
    assert "合并操作失败" in result["summary"]


# ====================================================================
# Test 3: LLM 调用失败不触发事务
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_llm_failure_no_transaction(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """LLM 调用失败 → savepoint 不被创建，不消耗事务资源。"""
    mock_db, mock_chapter, mocks, _ = full_mock_dependencies

    with patch.object(
        phase4_service, "_call_extraction_llm",
        side_effect=RuntimeError("LLM 服务不可用"),
    ):
        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # LLM 失败后不创建 savepoint
    mock_db.begin_nested.assert_not_called()
    # 主事务没有被提交（没有事务逻辑在 LLM 失败后执行）
    # 但 db.commit() 仍被调用（主事务外层）
    # 实际上，由于 LLM 失败在 try 块中，outer catch 的 db.rollback() 被调用
    mock_db.rollback.assert_called_once()

    # 返回优雅降级结果
    assert "summary" in result


# ====================================================================
# Test 4: savepoint 内部分失败 + 部分成功
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_partial_savepoint_failure(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """savepoint 内部部分操作成功、部分失败 → 整体回滚 savepoint。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    # 重置 get_characters 的调用记录
    mocks["vault_dao"].get_characters.reset_mock()

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # 让 世界观创建（第 4 个合并操作）失败
        # 此时角色、时间线、承诺已成功，世界观失败
        mocks["vault_dao"].create_world_entry.side_effect = ValueError(
            "世界观创建失败"
        )

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 整个回滚（部分成功也要整体回滚）
    sp = await mock_db.begin_nested()
    sp.rollback.assert_called_once()
    sp.commit.assert_not_called()

    # 主事务不中断
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

    # 返回合并失败标记
    assert "合并操作失败" in result["summary"]


# ====================================================================
# Test 5: 并发事务不互相影响
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_concurrent_isolation(
    phase4_service: Phase4Service,
):
    """两个独立事务并发执行不互相影响。"""
    from app.models.chapter import Chapter

    # 创建两个独立的 mock session
    db1 = _make_concurrent_mock_db()
    db2 = _make_concurrent_mock_db()

    extraction = {
        "character_updates": [{"action": "create", "name": "角色A", "changes": [], "confidence": 0.9}],
        "timeline_updates": [],
        "plot_promise_updates": [],
        "world_updates": [],
        "card_pool_entries": [],
    }

    mock_chapter = MagicMock(spec=Chapter)
    mock_chapter.id = "ch-uuid"
    mock_chapter.chapter_number = 1
    db1.get = AsyncMock(return_value=mock_chapter)
    db2.get = AsyncMock(return_value=mock_chapter)

    async def run_with_db(db, project_id):
        with patch("app.service.phase4_service.vault_dao") as vd, \
             patch("app.service.phase4_service.card_dao") as cd, \
             patch("app.service.phase4_service.chapter_dao") as chd, \
             patch.object(phase4_service, "_call_extraction_llm") as llm:

            chd.get = AsyncMock(return_value=mock_chapter)
            vd.get_characters = AsyncMock(return_value=[])
            vd.get_timeline = AsyncMock(return_value=[])
            vd.get_plot_promises = AsyncMock(return_value=[])
            vd.get_world_entries = AsyncMock(return_value=[])
            vd.create_character = AsyncMock()
            vd.create_timeline_event = AsyncMock()
            vd.create_plot_promise = AsyncMock()
            vd.create_world_entry = AsyncMock()
            cd.get_active_cards = AsyncMock(return_value=[])
            llm.return_value = extraction

            return await phase4_service.run_phase4(
                db, project_id=project_id, chapter_id=1,
                chapter_text="测试", card_ids=[],
            )

    import asyncio
    results = await asyncio.gather(
        run_with_db(db1, 1),
        run_with_db(db2, 2),
    )

    # 两个事务各自独立完成
    assert len(results) == 2
    for r in results:
        assert "version" in r
        assert r["version"].startswith("v4_ch1_")

    # db1 和 db2 各自有自己的 begin_nested 和 commit
    db1.begin_nested.assert_called_once()
    db2.begin_nested.assert_called_once()

    sp1 = await db1.begin_nested()
    sp2 = await db2.begin_nested()
    sp1.commit.assert_called_once()
    sp2.commit.assert_called_once()

    db1.commit.assert_called_once()
    db2.commit.assert_called_once()


def _make_concurrent_mock_db():
    """Create an independent mock db instance for concurrent test."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.get = AsyncMock()
    mock_sp = MagicMock()
    mock_sp.commit = AsyncMock()
    mock_sp.rollback = AsyncMock()
    db.begin_nested = AsyncMock(return_value=mock_sp)
    return db


# ====================================================================
# Test 6: 变更日志随 savepoint 回滚
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_changelog_rolls_back_with_savepoint(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """合并失败 → savepoint 回滚 → 变更日志不持久化。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # 在 savepoint 内所有操作完成后，_archive_changelog 抛出异常
        # 触发 savepoint 回滚，撤销所有合并和卡牌充实操作
        with patch.object(
            phase4_service, "_archive_changelog",
            side_effect=ValueError("变更日志写入失败"),
        ):
            result = await phase4_service.run_phase4(
                mock_db, project_id=1, chapter_id=1,
                chapter_text="测试正文", card_ids=[],
            )

    # savepoint 回滚（变更日志的 db.add 被回滚）
    sp = await mock_db.begin_nested()
    sp.rollback.assert_called_once()
    sp.commit.assert_not_called()

    # 主事务继续
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

    # 验证 result 标记了合并失败
    assert "合并操作失败" in result["summary"]


# ====================================================================
# Test 7: 卡牌淘汰随 savepoint 回滚
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_card_retire_rolls_back_with_savepoint(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """合并失败 → savepoint 回滚 → 卡牌淘汰变更不持久化。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # 所有 savepoint 内操作成功（合并、卡牌充实、变更日志、卡牌淘汰都执行了）
        # 但 savepoint 提交失败 → 整个 savepoint 回滚 → 所有操作被撤销
        sp = await mock_db.begin_nested()
        sp.commit.side_effect = RuntimeError("savepoint 提交失败")

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 提交失败 → savepoint 回滚
    sp = await mock_db.begin_nested()
    sp.commit.assert_called_once()  # 调用了但失败了
    sp.rollback.assert_called_once()

    # 主事务继续
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

    assert "合并操作失败" in result["summary"]


# ====================================================================
# Test 8: 主事务 commit 失败 → 完全回滚
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_main_commit_failure_full_rollback(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """db.commit() 失败 → 主事务完全回滚。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # savepoint 成功，但主事务 commit 失败
        mock_db.commit.side_effect = RuntimeError("数据库写入失败")

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 自身提交成功（sp.commit 被调用）
    sp = await mock_db.begin_nested()
    sp.commit.assert_called_once()
    sp.rollback.assert_not_called()

    # 主事务完全回滚
    mock_db.rollback.assert_called_once()

    # 返回值包含错误信息
    assert "Phase 4 执行出错" in result["summary"]


# ====================================================================
# Test 9: 空 LLM 结果 + 空合并
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_empty_merge_commits_successfully(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """LLM 返回空提取结果 → savepoint 内无操作 → 提交无异常。"""
    mock_db, mock_chapter, mocks, _ = full_mock_dependencies

    empty_parsed = {
        "character_updates": [],
        "timeline_updates": [],
        "plot_promise_updates": [],
        "world_updates": [],
        "card_pool_entries": [],
    }

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = empty_parsed

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 创建并提交成功
    sp = await mock_db.begin_nested()
    sp.commit.assert_called_once()
    sp.rollback.assert_not_called()

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()

    # summary 显示"无变更"
    assert result["summary"] == "无变更"
    assert result["changes"]["characters"]["created"] == []
    assert result["changes"]["card_pool"]["added"] == 0


# ====================================================================
# Test 10: savepoint 创建本身失败
# ====================================================================


@pytest.mark.asyncio
async def test_transaction_savepoint_creation_failure(
    phase4_service: Phase4Service,
    full_mock_dependencies,
):
    """begin_nested() 抛出异常 → outer catch 处理完全回滚。"""
    mock_db, mock_chapter, mocks, extraction_json = full_mock_dependencies

    with patch.object(phase4_service, "_call_extraction_llm") as mock_llm:
        mock_llm.return_value = extraction_json

        # savepoint 创建失败
        mock_db.begin_nested.side_effect = RuntimeError("无法创建 savepoint")

        result = await phase4_service.run_phase4(
            mock_db, project_id=1, chapter_id=1,
            chapter_text="测试正文", card_ids=[],
        )

    # savepoint 没有被创建（抛出异常）
    # 主事务被完全回滚
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()

    # 返回值包含错误
    assert "Phase 4 执行出错" in result["summary"]
