"""
墨灵 (Moling) — Card Retire Service.

Phase 4 写入完成后自动触发卡牌淘汰检查，确保卡牌池不超过上限，
新鲜期过期卡牌自动退役。

集成点：``phase4_service.run_phase4()`` 最后一步调用
``check_and_retire()``，与 Phase 4 写入在同一事务中。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_pool import CardPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 活跃卡牌池上限（超出后淘汰最旧的）
MAX_ACTIVE_CARDS: int = 80

# 卡牌新鲜期 = CARD_FRESHNESS_WINDOW × CARD_FRESHNESS_MULTIPLIER（取整）
CARD_FRESHNESS_WINDOW: int = 3
CARD_FRESHNESS_MULTIPLIER: float = 1.5

# 新鲜期过期的阈值章节数
FRESHNESS_LIFESPAN: int = int(CARD_FRESHNESS_WINDOW * CARD_FRESHNESS_MULTIPLIER)  # 4


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class RetireResult:
    """卡牌淘汰结果。"""

    retired_count: int = 0
    """本批实际淘汰的卡牌数"""

    expired_count: int = 0
    """因新鲜期过期被加入淘汰候选的卡牌数"""

    remaining_active: int = 0
    """淘汰后剩余的活跃卡牌数"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CardRetireService:
    """卡牌淘汰服务。

    负责检查卡牌池新鲜度并在 Phase 4 写入完成后触发淘汰。
    """

    async def check_and_retire(
        self,
        db: AsyncSession,
        project_id: int,
        current_chapter: int = 0,
    ) -> RetireResult:
        """执行卡牌淘汰检查与退役操作。

        流程：
        1. 获取当前活跃卡牌（status='active' AND is_active=True）
        2. 将 project_id 转换为 str（CardPool.project_id 字段类型为 str）
        3. 计算每张卡牌的新鲜期剩余
        4. 上限检查：活跃池 > MAX_ACTIVE_CARDS(80) → 淘汰最旧的差额
        5. 新鲜期检查：新鲜期已过 → 标记为过期并加入淘汰候选
        6. 执行淘汰：status='retired', is_active=False, retired_chapter=current_chapter
        7. 返回 RetireResult

        Args:
            db: 数据库异步会话（与 Phase 4 同一事务）
            project_id: 项目 ID
            current_chapter: 当前章节号（用于新鲜期计算和退役标记）

        Returns:
            RetireResult: 淘汰结果
        """
        try:
            # 1. 获取当前活跃卡牌
            pid = str(project_id)
            stmt = (
                select(CardPool)
                .where(
                    CardPool.project_id == pid,
                    CardPool.is_active == True,
                    CardPool.status == "active",
                )
            )
            result = await db.execute(stmt)
            active_cards: list[CardPool] = list(result.scalars().all())
            active_count = len(active_cards)

            if active_count == 0:
                logger.info(f"No active cards for project {project_id}, skipping retire")
                return RetireResult(remaining_active=0)

            # 2. 为每张卡牌计算"新鲜期过期章节"
            #    新鲜期过期章节 = freshness_chapter + FRESHNESS_LIFESPAN
            #    如果 freshness_chapter 为 None，使用默认值 0
            card_freshness: list[tuple[CardPool, int]] = []
            for card in active_cards:
                fc = card.freshness_chapter or 0
                expiry_chapter = fc + FRESHNESS_LIFESPAN
                card_freshness.append((card, expiry_chapter))

            # 3. 按过期章节排序（过期早的在前，优先淘汰）
            card_freshness.sort(key=lambda x: x[1])

            # 4. 收集需要淘汰的卡牌 ID
            retire_ids: list[int] = []

            # 4a. 上限检查：超出上限的部分
            if active_count > MAX_ACTIVE_CARDS:
                excess = active_count - MAX_ACTIVE_CARDS
                for card, _ in card_freshness[:excess]:
                    if card.id not in retire_ids:
                        retire_ids.append(card.id)
                logger.info(
                    f"Project {project_id}: pool size {active_count} > "
                    f"MAX_ACTIVE_CARDS({MAX_ACTIVE_CARDS}), retiring {excess} excess cards"
                )

            # 4b. 新鲜期检查：新鲜期已过的卡牌
            expired_count = 0
            for card, expiry in card_freshness:
                if current_chapter >= expiry and card.id not in retire_ids:
                    retire_ids.append(card.id)
                    expired_count += 1

            if expired_count > 0:
                logger.info(
                    f"Project {project_id}: {expired_count} cards expired "
                    f"(current_chapter={current_chapter})"
                )

            # 5. 如果没有需要淘汰的卡牌，直接返回
            if not retire_ids:
                return RetireResult(
                    retired_count=0,
                    expired_count=0,
                    remaining_active=active_count,
                )

            # 6. 执行淘汰
            stmt_update = (
                select(CardPool)
                .where(
                    CardPool.project_id == pid,
                    CardPool.id.in_(retire_ids),
                )
            )
            result_update = await db.execute(stmt_update)
            cards_to_retire = list(result_update.scalars().all())

            now = datetime.now(timezone.utc)
            for card in cards_to_retire:
                card.is_active = False
                card.status = "retired"
                card.retired_chapter = current_chapter

            await db.flush()

            retired_count = len(cards_to_retire)
            remaining_active = active_count - retired_count

            logger.info(
                f"Project {project_id}: retired {retired_count} cards "
                f"({expired_count} expired, {retired_count - expired_count} "
                f"by cap), {remaining_active} remaining active"
            )

            return RetireResult(
                retired_count=retired_count,
                expired_count=expired_count,
                remaining_active=remaining_active,
            )

        except Exception as e:
            logger.error(
                f"Card retire check failed for project {project_id}: {e}",
                exc_info=True,
            )
            # 错误降级：不抛异常，返回空结果
            return RetireResult()


# Singleton instance
card_retire_service = CardRetireService()
