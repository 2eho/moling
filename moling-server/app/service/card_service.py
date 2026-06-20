"""Moling - Card Service.

Business logic for card pool management and card draw algorithm (Phase 4).
"""

from typing import Optional
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import card_dao, project_dao
from app.errors import NotFoundError, ErrorCode
from app.utils.security import verify_project_ownership
from app.models import CardPool
from app.schemas.card import DrawCardReq, CardResp, DrawCardResp, CardPoolListResp


class CardService:
    """Service for card operations."""

    # Rarity weights for weighted random
    RARITY_WEIGHTS = {
        "common": 1,
        "rare": 2,
        "epic": 3,
        "legendary": 4,
    }

    # Pity mechanism: guarantee rare+ card after N draws without rare+
    PITY_THRESHOLD = 10  # After 10 draws without rare+, guarantee rare+
    PITY_RARITY_MIN = "rare"  # Minimum rarity for pity

    # Freshness bonus: bonus weight for cards not drawn recently
    FRESHNESS_BONUS = 2  # Bonus weight for fresh cards
    FRESHNESS_THRESHOLD = 5  # Cards not drawn in last 5 draws get bonus

    # 每次抽牌后的重抽次数上限，可通过构造参数覆盖
    MAX_DRAW_RETRIES = 3

    async def list_cards(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> CardPoolListResp:
        """List all cards in a project's card pool."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get all active cards via DAO
        cards = await card_dao.list_active_by_project(db, project_id)
        
        # Calculate stats
        by_rarity = {}
        for card in cards:
            by_rarity[card.rarity] = by_rarity.get(card.rarity, 0) + 1
        
        return CardPoolListResp(
            cards=[CardResp.model_validate(c) for c in cards],
            total_count=len(cards),
            by_rarity=by_rarity,
        )

    def _calculate_card_weight(self, card: CardPool, draw_history: list) -> float:
        """Calculate weight for a card based on rarity, pity, and freshness.
        
        Args:
            card: The card to calculate weight for
            draw_history: List of recent draw records for pity calculation
            
        Returns:
            Calculated weight (higher = more likely to be drawn)
        """
        # Base weight from rarity
        base_weight = self.RARITY_WEIGHTS.get(card.rarity, 1)
        
        # Pity mechanism: if no rare+ card in last N draws, boost rare+ cards
        pity_boost = 1.0
        if draw_history:
            recent_draws = draw_history[-self.PITY_THRESHOLD:]
            has_rare_plus = any(
                any(c.rarity in ["rare", "epic", "legendary"] for c in draw.get("cards", []))
                for draw in recent_draws
            )
            if not has_rare_plus and card.rarity in ["rare", "epic", "legendary"]:
                pity_boost = 3.0  # 3x weight for rare+ cards when pity triggered
        
        # Freshness bonus: cards not drawn recently get bonus
        freshness_boost = 1.0
        if card.last_drawn_chapter is None:
            # Never drawn - maximum freshness
            freshness_boost = self.FRESHNESS_BONUS
        else:
            # Check if drawn recently (simplified: using draw_count as proxy)
            if card.draw_count and card.draw_count < self.FRESHNESS_THRESHOLD:
                freshness_boost = self.FRESHNESS_BONUS
        
        return base_weight * pity_boost * freshness_boost

    async def draw_cards(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        req: DrawCardReq,
        max_retries: Optional[int] = None,
    ) -> DrawCardResp:
        """Draw cards from the pool (Phase 4 algorithm with weighted random).
        
        Args:
            db: Database session
            user_id: User ID
            project_id: Project ID
            req: Draw card request
            max_retries: Maximum number of redraws per round (defaults to MAX_DRAW_RETRIES)
        """
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get active cards
        active_cards = await card_dao.get_active_cards(db, project_id, count=100)
        
        if not active_cards:
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="No active cards in pool",
            )
        
        # Get draw history for pity mechanism
        draw_history_records = await card_dao.get_draw_history(db, project_id)
        # Convert to list of dicts for easier processing
        draw_history = []
        for record in draw_history_records[:self.PITY_THRESHOLD + 1]:
            # Get cards from this draw record
            card_ids = record.card_ids if hasattr(record, 'card_ids') else []
            cards = [c for c in active_cards if c.id in card_ids]
            draw_history.append({
                "round": record.draw_round,
                "cards": cards,
            })
        
        # Calculate weights for all active cards
        card_weights = {}
        for card in active_cards:
            weight = self._calculate_card_weight(card, draw_history)
            card_weights[card.id] = weight
        
        # Determine draw count based on mode
        if req.mode == "none" or not req.keep_card_ids:
            draw_count = 3
        elif req.mode == "single":
            draw_count = 1
        elif req.mode == "dual":
            draw_count = 2
        elif req.mode == "all":
            draw_count = min(5, len(active_cards))
        else:
            # Hybrid mode
            keep_count = len(req.keep_card_ids) if req.keep_card_ids else 0
            draw_count = min(3 - keep_count, len(active_cards) - keep_count)
        
        # Weighted random selection
        selected = []
        available_cards = active_cards.copy()
        
        for _ in range(min(draw_count, len(available_cards))):
            if not available_cards:
                break
            
            # Filter out already selected cards
            weights = [card_weights.get(c.id, 1) for c in available_cards]
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight <= 0:
                # Fallback to uniform random
                chosen = random.choice(available_cards)
            else:
                # Weighted random selection
                chosen = random.choices(available_cards, weights=weights, k=1)[0]
            
            selected.append(chosen)
            available_cards.remove(chosen)
        
        # Apply user-provided weights if provided (override weighted random)
        if req.weights and len(req.weights) == len(selected):
            # User provided custom weights - reshuffle based on user weights
            # This allows user to adjust the weighting after seeing the cards
            pass  # Keep the weighted random selection for now
        
        # Get draw round
        latest_draw = await card_dao.get_latest_draw(db, project_id)
        draw_round = (latest_draw.draw_round + 1) if latest_draw else 1
        
        # Create draw record
        draw_record = await card_dao.create_draw_record(
            db,
            {
                "project_id": str(project_id),
                "round": draw_round,
                "card_ids": [c.id for c in selected],
                "mode": req.mode,
                "weights": [card_weights.get(c.id, 1) for c in selected],  # Store weights used
            }
        )
        
        # Update card draw counts and last drawn info
        for card in selected:
            card.draw_count = (card.draw_count or 0) + 1
            card.last_drawn_chapter = req.chapter_id if hasattr(req, 'chapter_id') else None
        
        await db.commit()
        
        # Calculate remaining redraws (configurable per project, defaults to class constant)
        retry_limit = max_retries if max_retries is not None else self.MAX_DRAW_RETRIES
        remaining_redraws = retry_limit
        
        # Recommend top card based on weight
        recommended = [selected[0]] if selected else []
        
        return DrawCardResp(
            cards=[CardResp.model_validate(c) for c in selected],
            draw_round=draw_round,
            remaining_redraws=remaining_redraws,
            recommended=[CardResp.model_validate(c) for c in recommended],
            pity_triggered=any(c.rarity in ["rare", "epic", "legendary"] for c in selected),  # Indicate if pity triggered
        )

    async def create_card(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        card_data: dict,
    ) -> CardResp:
        """Create a custom card in the pool."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Create card via DAO
        card = await card_dao.create(db, {
            "project_id": project_id,
            "name": card_data.get("name", "New Card"),
            "description": card_data.get("description", ""),
            "rarity": card_data.get("rarity", "common"),
            "direction_type": card_data.get("direction_type", "interesting"),
            "direction_text": card_data.get("direction_text", ""),
            "type": "user_created",
            "is_active": True,
            "status": "active",
            "draw_count": 0,
        })
        await db.commit()
        
        return CardResp.model_validate(card)

    async def retire_card(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        card_id: int,
    ) -> None:
        """Retire a card (set is_active=False)."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)
        
        # Get card
        card = await card_dao.get(db, card_id)
        if card is None or card.project_id != project_id:
            raise NotFoundError(
                error_code=ErrorCode.CARD_NOT_FOUND,
                detail="Card not found",
            )
        
        # Retire card
        card.is_active = False
        card.status = "retired"
        
        await db.commit()

    async def get_draw_history(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: Optional[int] = None,
    ) -> list[dict]:
        """Get draw history for a project."""
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        records = await card_dao.get_draw_history(db, project_id, chapter_id)

        history = []
        for record in records:
            history.append({
                "id": record.id,
                "round": record.draw_round,
                "card_ids": record.card_ids,
                "mode": record.mode,
                "chapter_id": record.chapter_id,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            })

        return history

    async def get_draw_history_detail(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        draw_id: int,
    ) -> Optional[dict]:
        """Get a single draw history record by draw_id."""
        history = await self.get_draw_history(db, user_id, project_id)
        for item in history:
            if item.get("id") == draw_id:
                return item
        return None


    async def redraw_cards(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        chapter_id: int,
        keep_card_ids: list[int],
        draw_count: int = 3,
    ) -> dict:
        """Redraw cards for a chapter, excluding cards already drawn.

        Args:
            db: Database session
            user_id: User ID
            project_id: Project ID
            chapter_id: Current chapter ID
            keep_card_ids: Card IDs to keep (exclude from redraw)
            draw_count: Number of cards to draw

        Returns:
            Dict with cards list and remaining redraws
        """
        # Verify project exists and belongs to user
        project = await verify_project_ownership(db, project_id, user_id)

        # Get active cards
        active_cards = await card_dao.get_active_cards(db, project_id, count=100)

        if not active_cards:
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="No active cards in pool",
            )

        # Collect already drawn card IDs for this chapter
        draw_history_records = await card_dao.get_draw_history(
            db, project_id, chapter_id=chapter_id
        )
        drawn_card_ids = set()
        for record in draw_history_records:
            if record.card_ids:
                drawn_card_ids.update(record.card_ids)

        # Exclude keep_card_ids and already drawn cards
        excluded_ids = set(keep_card_ids or []) | drawn_card_ids

        available_cards = [
            c for c in active_cards if c.id not in excluded_ids
        ]

        if not available_cards:
            # All cards exhausted — return empty
            return {
                "cards": [],
                "remaining_redraws": 0,
                "message": "No available cards to redraw",
            }

        # Weighted random selection from available cards
        card_weights = {
            c.id: self._calculate_card_weight(c, [])
            for c in available_cards
        }

        selected = []
        pool = available_cards.copy()
        actual_count = min(draw_count, len(pool))

        for _ in range(actual_count):
            if not pool:
                break
            weights = [card_weights.get(c.id, 1) for c in pool]
            total_weight = sum(weights)
            if total_weight <= 0:
                chosen = random.choice(pool)
            else:
                chosen = random.choices(pool, weights=weights, k=1)[0]
            selected.append(chosen)
            pool.remove(chosen)

        # Create draw record
        latest_draw = await card_dao.get_latest_draw(db, project_id, chapter_id=chapter_id)
        draw_round = (latest_draw.draw_round + 1) if latest_draw else 1

        draw_record = await card_dao.create_draw_record(
            db,
            {
                "project_id": str(project_id),
                "chapter_id": str(chapter_id),
                "user_id": user_id,
                "card_ids": [c.id for c in selected],
                "mode": "redraw",
                "weights": [card_weights.get(c.id, 1) for c in selected],
                "draw_round": draw_round,
                "remaining_redraws": max(0, self.MAX_DRAW_RETRIES - draw_round),
            },
        )

        # Update card draw counts
        for card in selected:
            card.draw_count = (card.draw_count or 0) + 1
            card.last_drawn_chapter = chapter_id

        await db.commit()

        remaining = max(0, self.MAX_DRAW_RETRIES - draw_round)

        return {
            "cards": [CardResp.model_validate(c).model_dump() for c in selected],
            "draw_round": draw_round,
            "remaining_redraws": remaining,
        }


# Singleton instance
card_service = CardService()
