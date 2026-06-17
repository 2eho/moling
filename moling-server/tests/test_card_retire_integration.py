"""墨灵 (Moling) — 卡牌淘汰集成测试.

Phase 4 写入完成后自动触发卡牌淘汰检查的完整测试。

测试策略（Windows 兼容）：
- 使用 MagicMock 模拟数据库会话
- 使用 AsyncMock 模拟异步数据库操作
- 所有测试全平台可运行
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.card_pool import CardPool
from app.service.card_retire_service import (
    CardRetireService,
    RetireResult,
    MAX_ACTIVE_CARDS,
    FRESHNESS_LIFESPAN,
)


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def retire_service() -> CardRetireService:
    return CardRetireService()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_card(
    card_id: int,
    freshness_chapter: int = 0,
    status: str = "active",
    is_active: bool = True,
) -> MagicMock:
    card = MagicMock(spec=CardPool)
    card.id = card_id
    card.project_id = "1"
    card.freshness_chapter = freshness_chapter
    card.status = status
    card.is_active = is_active
    card.draw_count = 0
    card.retired_chapter = None
    return card


def _mock_active_result(cards: list[MagicMock]) -> MagicMock:
    """Mock for the first execute (fetching active cards)."""
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = cards
    result.scalars.return_value = scalars_result
    return result


# ====================================================================
# Tests — Core Logic
# ====================================================================


class TestCheckAndRetire:
    """卡牌淘汰核心逻辑测试."""

    @pytest.mark.asyncio
    async def test_retire_when_over_capacity(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 1: 卡牌池超过上限时正确淘汰超出部分的卡牌.

        使用 current_chapter=0 避免新鲜期淘汰干扰。
        """
        n_total = MAX_ACTIVE_CARDS + 5
        all_cards = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(n_total)
        ]

        # 第一次 execute：获取活跃卡牌 → 返回全部卡牌
        # 第二次 execute：获取需退役的卡牌（id.in_）→ 返回超出上限的5张
        excess_cards = all_cards[MAX_ACTIVE_CARDS:]
        mock_db.execute.side_effect = [
            _mock_active_result(all_cards),
            _mock_active_result(excess_cards),
        ]

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=0,
        )

        assert result.retired_count == 5, (
            f"Expected 5 retired, got {result.retired_count} "
            f"(expired={result.expired_count}, remaining={result.remaining_active})"
        )
        assert result.remaining_active == MAX_ACTIVE_CARDS
        assert result.expired_count == 0
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_retire_when_under_capacity(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 2: 卡牌池未超上限且新鲜期未过，不淘汰."""
        fresh_chapter = 10
        cards = [
            _make_card(card_id=i, freshness_chapter=fresh_chapter)
            for i in range(10)
        ]
        mock_db.execute.return_value = _mock_active_result(cards)

        # 当前章节还远未超过新鲜期
        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=fresh_chapter,
        )

        assert result.retired_count == 0
        assert result.expired_count == 0
        assert result.remaining_active == 10
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_retire_when_freshness_not_expired(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 3: 新鲜期未过的不淘汰."""
        fresh_chapter = 8
        cards = [
            _make_card(card_id=i, freshness_chapter=fresh_chapter)
            for i in range(5)
        ]
        mock_db.execute.return_value = _mock_active_result(cards)

        # current_chapter 还在新鲜期内
        current = fresh_chapter + FRESHNESS_LIFESPAN - 1
        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=current,
        )

        assert result.retired_count == 0
        assert result.expired_count == 0
        assert result.remaining_active == 5

    @pytest.mark.asyncio
    async def test_empty_pool_silent_pass(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 4: 空卡牌池静默通过，返回 0。"""
        mock_db.execute.return_value = _mock_active_result([])

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=10,
        )

        assert result.retired_count == 0
        assert result.expired_count == 0
        assert result.remaining_active == 0
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_active_no_retire(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 5: 所有卡牌 active 且未超上限、新鲜期内，不淘汰."""
        fresh_chapter = 10
        cards = [
            _make_card(card_id=i, freshness_chapter=fresh_chapter)
            for i in range(30)
        ]
        mock_db.execute.return_value = _mock_active_result(cards)

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=fresh_chapter,
        )

        assert result.retired_count == 0
        assert result.remaining_active == 30

    @pytest.mark.asyncio
    async def test_idempotent_multiple_calls(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 6: 幂等性 — 重复调用不重复退役已退役的卡牌."""
        # 第一次调用：85张卡，5张超出上限
        n_total = MAX_ACTIVE_CARDS + 5
        all_cards = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(n_total)
        ]
        excess_cards = all_cards[MAX_ACTIVE_CARDS:]

        mock_db.execute.side_effect = [
            _mock_active_result(all_cards),
            _mock_active_result(excess_cards),
        ]

        result1 = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=0,
        )
        assert result1.retired_count == 5
        assert result1.remaining_active == MAX_ACTIVE_CARDS

        # 第二次调用：只有 MAX_ACTIVE_CARDS 张仍在 active
        remaining = all_cards[:MAX_ACTIVE_CARDS]
        mock_db.execute.side_effect = [
            _mock_active_result(remaining),
        ]

        result2 = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=0,
        )

        assert result2.retired_count == 0
        assert result2.remaining_active == MAX_ACTIVE_CARDS

    @pytest.mark.asyncio
    async def test_database_exception_degradation(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 7: 数据库异常降级 — 不抛异常，返回空结果."""
        mock_db.execute.side_effect = Exception("DB connection lost")

        # 不应抛出异常
        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=10,
        )

        assert isinstance(result, RetireResult)
        assert result.retired_count == 0

    @pytest.mark.asyncio
    async def test_retired_card_status_correct(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 8: 退役后卡牌字段被正确设置. """
        n_total = MAX_ACTIVE_CARDS + 3
        all_cards = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(n_total)
        ]
        excess_cards = all_cards[MAX_ACTIVE_CARDS:]

        mock_db.execute.side_effect = [
            _mock_active_result(all_cards),
            _mock_active_result(excess_cards),
        ]

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=10,
        )

        assert result.retired_count == 3

        for card in excess_cards:
            assert card.is_active is False
            assert card.status == "retired"
            assert card.retired_chapter == 10

        mock_db.flush.assert_called_once()


# ====================================================================
# Tests — Freshness Expiry
# ====================================================================


class TestFreshnessExpiry:
    """新鲜期相关测试."""

    @pytest.mark.asyncio
    async def test_expired_freshness_retired(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 9: 新鲜期过期的卡牌被正确淘汰."""
        cards = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(5)
        ]
        mock_db.execute.side_effect = [
            _mock_active_result(cards),
            _mock_active_result(cards),  # 所有5张都要退役
        ]

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=FRESHNESS_LIFESPAN,
        )

        assert result.expired_count == 5
        assert result.retired_count == 5

    @pytest.mark.asyncio
    async def test_freshness_default_when_none(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 10: freshness_chapter=None 时视为 fresh（不淘汰）. """
        card = MagicMock(spec=CardPool)
        card.id = 1
        card.project_id = "1"
        card.freshness_chapter = None  # 未设置新鲜期
        card.status = "active"
        card.is_active = True
        card.draw_count = 0
        card.retired_chapter = None

        mock_db.execute.side_effect = [
            _mock_active_result([card]),
            _mock_active_result([card]),  # 如果触发退役
        ]

        # 当前章节很大，但 freshness_chapter=None => 视为 0，过期
        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=FRESHNESS_LIFESPAN,
        )

        # freshness_chapter=None → 视为 0，已过期（0 + 4 <= 4）
        assert result.expired_count == 1
        assert result.retired_count == 1

    @pytest.mark.asyncio
    async def test_mixed_expired_and_fresh(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 11: 部分过期 + 部分新鲜，只淘汰过期的."""
        # 3张过期卡（freshness_chapter=0，当前 chapter=FRESHNESS_LIFESPAN)
        # 2张新鲜卡（freshness_chapter=当前 chapter）
        expired = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(3)
        ]
        fresh = [
            _make_card(card_id=10 + i, freshness_chapter=FRESHNESS_LIFESPAN)
            for i in range(2)
        ]
        all_cards = expired + fresh

        mock_db.execute.side_effect = [
            _mock_active_result(all_cards),
            _mock_active_result(expired),
        ]

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=FRESHNESS_LIFESPAN,
        )

        assert result.retired_count == 3
        assert result.expired_count == 3
        assert result.remaining_active == 2  # 2张新鲜卡保留


# ====================================================================
# Tests — Integration with Phase 4
# ====================================================================


class TestPhase4Integration:
    """Phase 4 集成场景测试."""

    @pytest.mark.asyncio
    async def test_phase4_integration_error_degraded(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 12: check_and_retire 异常不会传播到调用方."""
        mock_db.execute.side_effect = RuntimeError("Unexpected error")

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=5,
        )

        assert isinstance(result, RetireResult)
        assert result.retired_count == 0

    @pytest.mark.asyncio
    async def test_retire_oldest_first(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 13: 上限淘汰时优先淘汰 freshness_chapter 最小（最新鲜期最老）的卡牌. """
        # 10张卡牌，freshness_chapter 依次为 0-9
        # 上限设为 4，应淘汰 freshness_chapter 最小的 6 张（0-5）
        n_total = 10
        cards = [
            _make_card(card_id=i, freshness_chapter=i) for i in range(n_total)
        ]

        # 预期被淘汰的：freshness_chapter 0-5（按排序，最旧的6张）
        expected_retired = cards[:6]

        mock_db.execute.side_effect = [
            _mock_active_result(cards),
            _mock_active_result(expected_retired),
        ]

        with patch(
            "app.service.card_retire_service.MAX_ACTIVE_CARDS", 4,
        ):
            result = await retire_service.check_and_retire(
                mock_db, project_id=1, current_chapter=3,  # 新鲜期不过期
            )

        assert result.retired_count == 6
        assert result.remaining_active == 4
        # 验证被淘汰的是 freshness_chapter 最小的 6 张
        for card in expected_retired:
            assert card.status == "retired"
            assert card.is_active is False

    @pytest.mark.asyncio
    async def test_cap_then_expiry_combined(
        self, retire_service: CardRetireService, mock_db: MagicMock
    ):
        """Test 14: 同时触发上限淘汰和新鲜期淘汰，结果正确叠加."""
        # 83张卡，freshness_chapter=0 → 全部过期
        # 上限 80，所以 3 张被上限淘汰，80 张被新鲜期淘汰
        n_total = MAX_ACTIVE_CARDS + 3  # 83
        all_cards = [
            _make_card(card_id=i, freshness_chapter=0) for i in range(n_total)
        ]

        # 上限淘汰 3 张（前 3 张）
        cap_retired = all_cards[:3]
        # 剩下 80 张全部过期
        remaining_after_cap = all_cards[3:]

        mock_db.execute.side_effect = [
            _mock_active_result(all_cards),
            _mock_active_result(all_cards),  # 所有卡牌都退役
        ]

        result = await retire_service.check_and_retire(
            mock_db, project_id=1, current_chapter=FRESHNESS_LIFESPAN,
        )

        # 83 张全部退役（3 张上限 + 80 张过期）
        assert result.retired_count == n_total
        assert result.expired_count == MAX_ACTIVE_CARDS  # 80 张过期
        assert result.remaining_active == 0
