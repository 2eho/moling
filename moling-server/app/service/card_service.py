"""Moling - Card Service.

Business logic for card pool management and card draw algorithm (Phase 4).
"""

from typing import Optional
import random

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import card_dao, project_dao
from app.errors import NotFoundError, ErrorCode, PermissionError
from app.models import CardPool
from app.schemas.card import DrawCardReq, CardResp, DrawCardResp, CardPoolListResp


class CardService:
    """Service for card operations."""

    async def list_cards(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
    ) -> CardPoolListResp:
        """List all cards in a project's card pool."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )
        
        # Get all active cards
        stmt = (
            select(CardPool)
            .where(
                CardPool.project_id == project_id,
                CardPool.is_active == True,
            )
            .order_by(CardPool.rarity.desc(), CardPool.id.asc())
        )
        result = await db.execute(stmt)
        cards = list(result.scalars().all())
        
        # Calculate stats
        by_rarity = {}
        for card in cards:
            by_rarity[card.rarity] = by_rarity.get(card.rarity, 0) + 1
        
        return CardPoolListResp(
            cards=[CardResp.model_validate(c) for c in cards],
            total_count=len(cards),
            by_rarity=by_rarity,
        )

    async def draw_cards(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: int,
        req: DrawCardReq,
    ) -> DrawCardResp:
        """Draw cards from the pool (Phase 4 algorithm)."""
        # Verify project exists and belongs to user
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )
        
        # Get active cards
        active_cards = await card_dao.get_active_cards(db, project_id, count=100)
        
        if not active_cards:
            raise PermissionError(
                error_code=ErrorCode.INVALID_REQUEST,
                detail="No active cards in pool",
            )
        
        # Apply draw algorithm based on mode
        if req.mode == "none" or not req.keep_card_ids:
            # Random draw (default 3 cards)
            draw_count = 3
            selected = random.sample(active_cards, min(draw_count, len(active_cards)))
        elif req.mode == "single":
            # Single card draw
            selected = [random.choice(active_cards)]
        elif req.mode == "dual":
            # Draw 2 cards
            selected = random.sample(active_cards, min(2, len(active_cards)))
        elif req.mode == "all":
            # Use all cards (up to 5)
            selected = active_cards[:5]
        else:
            # Hybrid mode (keep some, draw some)
            keep_count = len(req.keep_card_ids)
            draw_count = min(3 - keep_count, len(active_cards) - keep_count)
            available = [c for c in active_cards if c.id not in req.keep_card_ids]
            selected = random.sample(available, min(draw_count, len(available)))
        
        # Apply weights if provided
        if req.weights and len(req.weights) == len(selected):
            # Weighted random selection (simplified)
            total_weight = sum(req.weights)
            normalized_weights = [w / total_weight for w in req.weights]
            selected = random.choices(selected, weights=normalized_weights, k=len(selected))
        
        # Get draw round
        latest_draw = await card_dao.get_latest_draw(db, project_id)
        draw_round = (latest_draw.round + 1) if latest_draw else 1
        
        # Create draw record
        draw_record = await card_dao.create_draw_record(
            db,
            {
                "project_id": project_id,
                "round": draw_round,
                "card_ids": [c.id for c in selected],
                "mode": req.mode,
            }
        )
        
        # Update card draw counts
        for card in selected:
            card.draw_count = (card.draw_count or 0) + 1
            card.last_drawn_chapter = req.get("chapter_id")
        
        await db.commit()
        
        return DrawCardResp(
            cards=[CardResp.model_validate(c) for c in selected],
            draw_round=draw_round,
            remaining_redraws=3,  # TODO: make configurable
            recommended=[CardResp.model_validate(c) for c in selected[:1]],  # simplified
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
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )
        
        # Create card
        card = CardPool(
            project_id=project_id,
            name=card_data.get("name", "New Card"),
            description=card_data.get("description", ""),
            rarity=card_data.get("rarity", "common"),
            direction_type=card_data.get("direction_type", "interesting"),
            direction_text=card_data.get("direction_text", ""),
            type="user_created",
            is_active=True,
            status="active",
            draw_count=0,
        )
        
        db.add(card)
        await db.commit()
        await db.refresh(card)
        
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
        project = await project_dao.get(db, project_id)
        if project is None:
            raise NotFoundError(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                detail="Project not found",
            )
        if project.user_id != user_id:
            raise PermissionError(
                error_code=ErrorCode.FORBIDDEN,
                detail="Not authorized to access this project",
            )
        
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


# Singleton instance
card_service = CardService()
