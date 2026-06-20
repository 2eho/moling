"""Moling - Card Combination Algorithm Service.

Implements steps 1-6 of the generation pipeline:
weight allocation, vault filtering, conflict detection,
direction scoring, weaving scheme matching, and outline filling.

Each step delegates to a dedicated service module for Single Responsibility.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao
from app.models import CardPool, Chapter, Project
from app.service.conflict_detection import conflict_detection_service
from app.service.direction_scoring import direction_scoring_service
from app.service.vault_filter import vault_filter_service
from app.service.weaving_scheme import weaving_scheme_service


# --- Singleton ---
class AlgorithmService:
    """Service encapsulating card combination algorithms (steps 1-6).

    Each ``_stepN_*`` method delegates to a dedicated service module;
    the results are consumed by ``GenerationService.execute_generation_pipeline``.
    """

    # Rarity base weights (matching card_service.RARITY_WEIGHTS)
    RARITY_BASE = {
        "common": 1.0,
        "rare": 2.0,
        "epic": 3.0,
        "legendary": 4.0,
    }

    # ----- Step 1: Weight Allocation -------------------------------------------

    async def step1_weight_allocation(
        self,
        cards: List[CardPool],
        user_weights: List[float],
    ) -> Dict[int, float]:
        """Allocate weights based on card rarity and user adjustment.

        Returns a map of ``card_id → final_weight``.
        """
        weight_map: Dict[int, float] = {}

        for i, card in enumerate(cards):
            base = self.RARITY_BASE.get(card.rarity, 1.0)
            user_weight = user_weights[i] if i < len(user_weights) else 50.0
            # Normalise user weight (0-100) to multiplier (0.5-2.0)
            user_multiplier = 0.5 + (user_weight / 100.0) * 1.5
            weight_map[card.id] = base * user_multiplier

        return weight_map

    # ----- Step 2: Vault Filtering (§3.4) --------------------------------------

    async def step2_vault_filter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int | None = None,
        cards: Optional[List[CardPool]] = None,
        chapter_number: int | None = None,
    ) -> Dict[str, Any]:
        """Filter relevant vault entities for the current generation context.

        Uses VaultFilterService for ID-based filtering with hierarchical
        compression (§3.4). Falls back to simple Top-N when no cards provided.

        Returns categorised vault entries as serialized dicts:
        ``characters``, ``timeline``, ``plot_promises``, ``world``,
        ``compression_level``, ``token_estimate``.
        """
        if cards:
            return await vault_filter_service.filter_by_cards(
                db=db,
                project_id=project_id,
                cards=cards,
                chapter_number=chapter_number,
            )

        # Fallback: use VaultFilterService.filter_all when no cards provided
        # (applies identical hierarchical compression as the normal path)
        from app.service.vault_filter import vault_filter_service
        return await vault_filter_service.filter_all(
            db=db,
            project_id=project_id,
            chapter_number=chapter_number,
        )

    # ----- Step 3: Conflict Detection (§3.3) -----------------------------------

    async def step3_conflict_detection(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int | None = None,
        weight_map: Optional[Dict[int, float]] = None,
        cards: Optional[List[CardPool]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect conflicts with existing dynamic-layer entries.

        Delegates to ConflictDetectionService for:
        - Baseline coherence conflicts (must_hold / must_not)
        - Secret matrix conflicts (information asymmetry)
        - Character state machine conflicts

        Returns a list of conflict dicts with ``type``, ``description``,
        ``severity``, and ``suggested_fix``.
        """
        if not cards:
            return []

        result = await conflict_detection_service.detect_conflicts(
            db=db,
            project_id=project_id,
            chapter_id=chapter_id or 0,
            cards=cards,
            weight_map=weight_map,
        )
        return result.get("conflicts", [])

    # ----- Step 4: Direction Conflict Scoring (§3.3) ---------------------------

    async def step4_direction_conflict_scoring(
        self,
        cards: List[CardPool],
        weight_map: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """Score conflicts between the selected direction cards.

        Delegates to DirectionScoringService for:
        - Direction compatibility matrix
        - Entity conflict detection
        - Emotional tone conflict detection
        - Confidence scoring with LLM fallback
        """
        return await direction_scoring_service.score_direction_conflicts(
            cards=cards,
            weight_map=weight_map,
        )

    # ----- Step 5: Weaving Scheme Matching (§3.6) ------------------------------

    async def step5_weaving_scheme_matching(
        self,
        cards: List[CardPool],
        req_mode: str,
        weight_map: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """Match the best weaving scheme for the requested mode.

        Delegates to WeavingSchemeService for:
        - Causal chain (§3.6.1)
        - Parallel interweaving (§3.6.2)
        - Main + side quest (§3.6.3)
        - Rule-based selection with LLM fallback (§3.6.4)
        """
        # Backward compatibility: when weight_map not provided, create uniform weights
        if weight_map is None:
            weight_map = {card.id: 1.0 for card in cards}

        return await weaving_scheme_service.match_scheme(
            cards=cards,
            weight_map=weight_map,
            req_mode=req_mode,
        )

    # ----- Step 6: Outline Template Filling ------------------------------------

    async def step6_outline_template_filling(
        self,
        project: Project,
        chapter: Optional[Chapter],
        cards: List[CardPool],
        weight_map: Dict[int, float],
        relevant_vault: Dict[str, Any],
        word_count: int = 2000,
    ) -> Dict[str, Any]:
        """Fill the outline template with generation parameters.

        Args:
            word_count: Target word count from the generation request
                (default 2000, range 500–5000).
        """
        def safe_get(items: list, attr: str, default: str = "") -> Any:
            """Get attribute from model or dict items."""
            results = []
            for item in items[:5]:
                if isinstance(item, dict):
                    results.append(item.get(attr, default))
                else:
                    results.append(getattr(item, attr, default))
            return results

        # Build selected-directions list
        directions = [
            {
                "card_name": card.name,
                "direction_text": card.direction_text,
                "weight": weight_map.get(card.id, 1.0),
                "rarity": card.rarity,
            }
            for card in cards
        ]

        # Vault-derived context (supports both dict and model items)
        vault_chars = relevant_vault.get("characters", [])
        vault_timeline = relevant_vault.get("timeline", [])
        vault_promises = relevant_vault.get("plot_promises", [])

        character_names = safe_get(vault_chars, "name")

        # Recent events from timeline
        recent_events = []
        if vault_timeline:
            for e in vault_timeline[-3:]:
                if isinstance(e, dict):
                    recent_events.append(e.get("event", ""))
                else:
                    recent_events.append(getattr(e, "event", ""))

        # Active promises
        active_promises = safe_get(vault_promises, "description")

        outline: Dict[str, Any] = {
            "project_title": project.title,
            "project_genre": project.genre,
            "chapter_title": chapter.title if chapter else "新章节",
            "chapter_number": chapter.chapter_number if chapter else 1,
            "selected_directions": directions,
            "characters": character_names,
            "recent_events": recent_events,
            "active_promises": active_promises,
            "generation_requirements": {
                "word_count": word_count,
                "style": project.style or "叙事风格",
                "tone": "consistent with project",
            },
        }
        return outline


# Singleton instance
algorithm_service = AlgorithmService()
