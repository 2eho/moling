"""
墨灵 (Moling) — Card Pool Service.

Card lifecycle management for background worker (Celery) consumption:
- Freshness checking and stale card identification
- Card retirement (deactivation)
- Replacement card placeholder generation

Uses async SQLAlchemy sessions provided by ``get_worker_session()``
in ``app/worker/db.py``.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import card_dao
from app.models.card_pool import CardPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Each draw reduces the freshness score by this amount (capped)
FRESHNESS_DRAW_PENALTY = 0.12
# Each chapter since creation reduces the score
FRESHNESS_AGE_PENALTY_PER_CHAPTER = 0.04
# Cards with score below this threshold are considered stale
FRESHNESS_STALE_THRESHOLD = 0.35
# Max penalty caps so base score always has minimal floor
MAX_DRAW_PENALTY = 0.6
MAX_AGE_PENALTY = 0.25

# Replacement generation
REPLACEMENT_DIRECTIONS = ["stable", "interesting", "stunning", "divine"]
REPLACEMENT_CATEGORIES = ["character", "plot", "world", "conflict", "theme"]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CardPoolService:
    """Service for card pool lifecycle management.

    Operates on the ``CardPool`` model and uses **asynchronous** SQLAlchemy
    sessions provided by the worker via ``get_worker_session()``.
    """

    # ---------------------------------------------------------------- private

    @staticmethod
    def _calc_freshness_score(card: CardPool) -> float:
        """Calculate a freshness score in [0.0, 1.0] for a single card.

        Factors (higher score = fresher / should be retained):

        * **Base**: 1.0
        * **Draw penalty**: each time the card was drawn reduces freshness
        * **Age penalty**: cards created earlier (lower ``freshness_chapter``)
          are penalised more heavily
        """
        score = 1.0

        # Draw count penalty
        draws = card.draw_count or 0
        draw_penalty = min(draws * FRESHNESS_DRAW_PENALTY, MAX_DRAW_PENALTY)
        score -= draw_penalty

        # Age penalty — older cards are more likely to be stale
        if card.freshness_chapter is not None:
            age_penalty = min(
                card.freshness_chapter * FRESHNESS_AGE_PENALTY_PER_CHAPTER,
                MAX_AGE_PENALTY,
            )
            score -= age_penalty

        # Never-drawn cards get a small bonus
        if (card.draw_count or 0) == 0:
            score += 0.1

        return max(0.0, min(1.0, score))

    # ---------------------------------------------------------------- public

    async def check_freshness(self, db: AsyncSession, project_id: int) -> dict[str, Any]:
        """Evaluate freshness of all active cards in *project_id*.

        Returns a dict with:
          ``project_id``, ``total_cards``, ``fresh_count``, ``stale_count``,
          ``stale_cards`` (list of card IDs below the freshness threshold).
        """
        cards = await card_dao.list_active_by_project(db, project_id)

        stale_ids: list[int] = []
        for card in cards:
            score = self._calc_freshness_score(card)
            if score < FRESHNESS_STALE_THRESHOLD:
                stale_ids.append(card.id)

        return {
            "project_id": project_id,
            "total_cards": len(cards),
            "fresh_count": len(cards) - len(stale_ids),
            "stale_count": len(stale_ids),
            "stale_cards": stale_ids,
        }

    async def retire_cards(
        self,
        db: AsyncSession,
        project_id: int,
        card_ids: list[int],
    ) -> dict[str, Any]:
        """Mark *card_ids* as retired for the given project.

        Sets ``is_active=False`` and ``status='retired'`` on each card.
        Returns a dict with ``project_id``, ``retired_count``, ``retired_ids``.
        """
        cards = await card_dao.get_by_ids(db, project_id, card_ids)

        now_chapter = 0
        for card in cards:
            card.is_active = False
            card.status = "retired"
            card.retired_chapter = now_chapter

        await db.commit()

        return {
            "project_id": project_id,
            "retired_count": len(cards),
            "retired_ids": [c.id for c in cards],
        }

    async def generate_replacements(
        self,
        db: AsyncSession,
        project_id: int,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate *count* placeholder cards to fill gaps in the pool.

        Analyses the current pool for under-represented direction types
        and categories, then produces placeholder card dicts with fields
        compatible with the ``CardPool`` model.

        Returns a list of card dictionaries (not persisted).
        """
        # Fetch existing active cards to analyse coverage
        existing_cards = await card_dao.list_active_by_project(db, project_id)

        # Build direction-type frequency map
        direction_counts: dict[str, int] = {}
        for card in existing_cards:
            dt = card.direction_type
            direction_counts[dt] = direction_counts.get(dt, 0) + 1

        # Determine which directions are under-represented
        avg_per_direction = max(
            1,
            len(existing_cards) // len(REPLACEMENT_DIRECTIONS),
        )
        under_repr_directions = [
            d
            for d in REPLACEMENT_DIRECTIONS
            if direction_counts.get(d, 0) < avg_per_direction
        ]
        # Fallback to all directions if none are under-represented
        pool_directions = (
            under_repr_directions
            if under_repr_directions
            else list(REPLACEMENT_DIRECTIONS)
        )

        replacements: list[dict[str, Any]] = []
        for i in range(count):
            direction = pool_directions[i % len(pool_directions)]
            category = REPLACEMENT_CATEGORIES[i % len(REPLACEMENT_CATEGORIES)]

            replacements.append(
                {
                    "project_id": str(project_id),
                    "name": f"替换卡 {i + 1}",
                    "description": "",
                    "rarity": "common",
                    "direction": direction,
                    "direction_type": direction,
                    "direction_text": f"参考 {direction} 方向，{category} 类别生成新灵感",
                    "category": category,
                    "content": f"替换卡 {i + 1}: 方向={direction}, 类别={category}",
                    "layer": 0,
                    "type": "auto_replacement",
                    "source_label": "卡池替换",
                    "is_active": True,
                    "status": "active",
                    "tags": [category, direction],
                    "draw_count": 0,
                    "pick_count": 0,
                }
            )

        return replacements


# Singleton instance
card_pool_service = CardPoolService()
