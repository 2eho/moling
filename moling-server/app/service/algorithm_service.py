"""Moling - Card Combination Algorithm Service.

Implements steps 1-6 of the generation pipeline:
weight allocation, vault filtering, conflict detection,
direction scoring, weaving scheme matching, and outline filling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao
from app.models import CardPool, Chapter, Project


# --- Singleton ---
class AlgorithmService:
    """Service encapsulating card combination algorithms (steps 1-6).

    Each ``_stepN_*`` method is a pure computation or a direct DAO read;
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

    # ----- Step 2: Vault Filtering ---------------------------------------------

    async def step2_vault_filter(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int | None = None,
    ) -> Dict[str, List[Any]]:
        """Filter relevant vault entities for the current generation context.

        Returns categorised vault entries:
        ``characters``, ``timeline``, ``plot_promises``, ``world``.
        """
        relevant: Dict[str, List[Any]] = {
            "characters": [],
            "timeline": [],
            "plot_promises": [],
            "world": [],
        }

        # Top 10 most relevant characters
        characters = await vault_dao.get_characters(db, project_id)
        relevant["characters"] = characters[:10]

        # Last 5 timeline events
        timeline = await vault_dao.get_timeline(db, project_id)
        relevant["timeline"] = timeline[-5:] if timeline else []

        # Active / dormant plot promises
        promises = await vault_dao.get_plot_promises(db, project_id)
        relevant["plot_promises"] = [
            p for p in promises if p.status in ("dormant", "active")
        ]

        # Top 10 world entries
        world = await vault_dao.get_world_entries(db, project_id)
        relevant["world"] = world[:10]

        return relevant

    # ----- Step 3: Conflict Detection ------------------------------------------

    async def step3_conflict_detection(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int | None = None,
        weight_map: Optional[Dict[int, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect conflicts with existing dynamic-layer entries.

        .. todo::
           Implement actual dynamic-layer conflict detection.
           Currently returns an empty list.
        """
        return []

    # ----- Step 4: Direction Conflict Scoring ----------------------------------

    async def step4_direction_conflict_scoring(
        self,
        cards: List[CardPool],
        weight_map: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """Score conflicts between the selected direction cards.

        Returns a dict with ``has_conflict``, ``conflict_score``, and
        ``conflict_reasons``.
        """
        conflicts: Dict[str, Any] = {
            "has_conflict": False,
            "conflict_score": 0.0,
            "conflict_reasons": [],
        }

        direction_types = [card.direction_type for card in cards]

        # Example: "稳妥" vs "惊艳" creates narrative tension
        if "稳妥" in direction_types and "惊艳" in direction_types:
            conflicts["has_conflict"] = True
            conflicts["conflict_score"] = 0.7
            conflicts["conflict_reasons"].append("稳妥与惊艳的方向存在张力")

        return conflicts

    # ----- Step 5: Weaving Scheme Matching -------------------------------------

    async def step5_weaving_scheme_matching(
        self,
        cards: List[CardPool],
        req_mode: str,
    ) -> Dict[str, Any]:
        """Match the best weaving scheme for the requested mode."""
        schemes: Dict[str, Dict[str, str]] = {
            "single": {
                "name": "单卡模式",
                "description": "专注于一个创作方向",
                "weaving_strategy": "focus",
            },
            "dual": {
                "name": "双卡模式",
                "description": "融合两个创作方向",
                "weaving_strategy": "blend",
            },
            "all": {
                "name": "全选模式",
                "description": "多方向综合",
                "weaving_strategy": "multi_thread",
            },
            "hybrid": {
                "name": "混合模式",
                "description": "保留部分，重抽部分",
                "weaving_strategy": "hybrid",
            },
        }
        return schemes.get(req_mode, schemes["single"])

    # ----- Step 6: Outline Template Filling ------------------------------------

    async def step6_outline_template_filling(
        self,
        project: Project,
        chapter: Optional[Chapter],
        cards: List[CardPool],
        weight_map: Dict[int, float],
        relevant_vault: Dict[str, List[Any]],
    ) -> Dict[str, Any]:
        """Fill the outline template with generation parameters."""
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

        # Vault-derived context
        character_names = [
            c.name for c in relevant_vault.get("characters", [])[:5]
        ]
        recent_events = [
            e.event
            for e in relevant_vault.get("timeline", [])[-3:]
            if relevant_vault.get("timeline")
        ]
        active_promises = [
            p.description
            for p in relevant_vault.get("plot_promises", [])[:3]
        ]

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
                "word_count": 2000,  # TODO: Make configurable
                "style": project.style or "叙事风格",
                "tone": "consistent with project",
            },
        }
        return outline


# Singleton instance
algorithm_service = AlgorithmService()
