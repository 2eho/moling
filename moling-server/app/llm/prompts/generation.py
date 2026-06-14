"""Moling - Prompt Architecture (4-Layer Injection).

Implements 4-layer prompt injection for LLM generation:
1. Character Layer - Character info injection
2. Timeline Layer - Timeline events injection
3. PlotPromise Layer - Plot promises injection
4. World Layer - World building rules injection
5. Combine all layers into final prompt
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao import project_dao, vault_dao, chapter_dao
from app.models import Project, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld

logger = logging.getLogger(__name__)
settings = get_settings()


class PromptArchitecture:
    """Service for building 4-layer injection prompts."""

    async def build_generation_prompt(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: Optional[int],
        generation_params: Dict[str, Any],
    ) -> str:
        """Build complete generation prompt with 4-layer injection.
        
        Args:
            db: Database session
            project_id: Project ID
            chapter_id: Current chapter ID (if any)
            generation_params: Generation parameters (cards, weights, mode)
            
        Returns:
            Complete prompt with all layers injected
        """
        # Get project
        project = await project_dao.get(db, project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        # ===== Layer 1: Character Layer =====
        logger.info(f"Building prompt: Layer 1 - Character")
        character_layer = await self._build_character_layer(
            db, project_id
        )

        # ===== Layer 2: Timeline Layer =====
        logger.info(f"Building prompt: Layer 2 - Timeline")
        timeline_layer = await self._build_timeline_layer(
            db, project_id, chapter_id
        )

        # ===== Layer 3: PlotPromise Layer =====
        logger.info(f"Building prompt: Layer 3 - PlotPromise")
        plot_promise_layer = await self._build_plot_promise_layer(
            db, project_id
        )

        # ===== Layer 4: World Layer =====
        logger.info(f"Building prompt: Layer 4 - World")
        world_layer = await self._build_world_layer(
            db, project_id
        )

        # ===== Combine all layers into final prompt =====
        logger.info(f"Building prompt: Combining all layers")
        final_prompt = await self._combine_layers(
            db, project, chapter_id, generation_params,
            character_layer, timeline_layer,
            plot_promise_layer, world_layer
        )

        return final_prompt

    async def _build_character_layer(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> str:
        """Layer 1: Character Layer injection.
        
        Returns formatted character info for prompt injection.
        """
        characters = await vault_dao.get_characters(db, project_id)
        
        if not characters:
            return "【角色层】暂无角色信息。"

        # Format character info
        char_lines = []
        for char in characters[:10]:  # Top 10 most relevant
            line = f"- {char.name}（{char.role}）"
            if char.traits:
                line += f" - 特征：{', '.join(char.traits)}"
            if char.emotion:
                line += f" - 当前情绪：{char.emotion}"
            char_lines.append(line)

        layer = "【角色层】\n" + "\n".join(char_lines)
        return layer

    async def _build_timeline_layer(
        self,
        db: AsyncSession,
        project_id: int,
        current_chapter_id: Optional[int],
    ) -> str:
        """Layer 2: Timeline Layer injection.
        
        Returns formatted timeline events for prompt injection.
        """
        events = await vault_dao.get_timeline(db, project_id)
        
        if not events:
            return "【时间线层】暂无时间线事件。"

        # Get current chapter number
        current_chapter_num = 0
        if current_chapter_id:
            chapter = await chapter_dao.get(db, current_chapter_id)
            if chapter:
                current_chapter_num = chapter.chapter_number

        # Filter events up to current chapter
        relevant_events = events
        if current_chapter_num > 0:
            relevant_events = [e for e in events if e.chapter_number <= current_chapter_num]

        # Format timeline info
        event_lines = []
        for event in relevant_events[-5:]:  # Last 5 events
            line = f"- 第{event.chapter_number}章：{event.event}"
            if event.description:
                line += f" - {event.description}"
            if event.is_key_event:
                line += " ⭐（关键事件）"
            event_lines.append(line)

        layer = "【时间线层】\n" + "\n".join(event_lines)
        return layer

    async def _build_plot_promise_layer(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> str:
        """Layer 3: PlotPromise Layer injection.
        
        Returns formatted plot promises for prompt injection.
        """
        promises = await vault_dao.get_plot_promises(db, project_id)
        
        if not promises:
            return "【伏笔层】暂无伏笔信息。"

        # Categorize promises by status
        dormant = [p for p in promises if p.status == "dormant"]
        active = [p for p in promises if p.status == "active"]
        resolved = [p for p in promises if p.status == "resolved"]

        # Format plot promise info
        promise_lines = []
        
        if active:
            promise_lines.append("【活跃伏笔】")
            for p in active[:5]:  # Top 5 active
                line = f"- {p.description}"
                if p.urgency:
                    line += f"（紧急度：{p.urgency}）"
                promise_lines.append(line)

        if dormant:
            promise_lines.append("\n【休眠伏笔】")
            for p in dormant[:3]:  # Top 3 dormant
                line = f"- {p.description}"
                promise_lines.append(line)

        if resolved:
            promise_lines.append("\n【已回收伏笔】")
            for p in resolved[-3:]:  # Last 3 resolved
                line = f"- {p.description}"
                promise_lines.append(line)

        layer = "【伏笔层】\n" + "\n".join(promise_lines)
        return layer

    async def _build_world_layer(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> str:
        """Layer 4: World Layer injection.
        
        Returns formatted world building rules for prompt injection.
        """
        entries = await vault_dao.get_world_entries(db, project_id)
        
        if not entries:
            return "【世界观层】暂无世界观设定。"

        # Format world info
        world_lines = []
        for entry in entries[:10]:  # Top 10 entries
            line = f"- {entry.term}"
            if entry.description:
                line += f"：{entry.description}"
            if entry.category:
                line += f"（{entry.category}）"
            world_lines.append(line)

        layer = "【世界观层】\n" + "\n".join(world_lines)
        return layer

    async def _combine_layers(
        self,
        db: AsyncSession,
        project: Project,
        chapter_id: Optional[int],
        generation_params: Dict[str, Any],
        character_layer: str,
        timeline_layer: str,
        plot_promise_layer: str,
        world_layer: str,
    ) -> str:
        """Combine all 4 layers into final prompt.
        
        Returns complete prompt for LLM generation.
        """
        # Build final prompt
        prompt_parts = []

        # ===== Project info =====
        prompt_parts.append(f"# 项目信息\n")
        prompt_parts.append(f"标题：{project.title}")
        prompt_parts.append(f"类型：{project.genre}")
        prompt_parts.append(f"简介：{project.synopsis}")
        if project.worldview:
            prompt_parts.append(f"世界观：{project.worldview}")
        prompt_parts.append("")

        # ===== Generation direction =====
        prompt_parts.append("# 创作方向\n")
        card_ids = generation_params.get("card_ids", [])
        weights = generation_params.get("weights", [])
        mode = generation_params.get("mode", "single")
        
        prompt_parts.append(f"编织模式：{mode}")
        # 添加卡牌方向信息
        if card_ids:
            from app.dao import card_dao
            for idx, cid in enumerate(card_ids):
                card = await card_dao.get(db, cid)
                if card:
                    weight_info = f" (权重: {weights[idx]})" if idx < len(weights) else ""
                    prompt_parts.append(
                        f"- 方向卡牌{idx + 1}：{card.name}{weight_info}"
                    )
                    if card.direction_text:
                        prompt_parts.append(f"  方向说明：{card.direction_text}")
                    if card.direction_type:
                        prompt_parts.append(f"  方向类型：{card.direction_type}")
        prompt_parts.append("")

        # ===== Layer 1: Character =====
        prompt_parts.append(character_layer)
        prompt_parts.append("")

        # ===== Layer 2: Timeline =====
        prompt_parts.append(timeline_layer)
        prompt_parts.append("")

        # ===== Layer 3: PlotPromise =====
        prompt_parts.append(plot_promise_layer)
        prompt_parts.append("")

        # ===== Layer 4: World =====
        prompt_parts.append(world_layer)
        prompt_parts.append("")

        # ===== Generation requirements =====
        prompt_parts.append("# 写作要求\n")
        prompt_parts.append("1. 保持与已有设定的一致性")
        prompt_parts.append("2. 推进情节发展，注意伏笔的铺垫和回收")
        prompt_parts.append("3. 角色行为符合其性格和设定")
        prompt_parts.append("4. 文笔流畅，叙事自然")
        prompt_parts.append("5. 注意章节间的衔接")
        prompt_parts.append("\n请直接开始写作，不要添加任何解释或说明。")

        # Combine all parts
        final_prompt = "\n".join(prompt_parts)
        
        logger.info(f"Built final prompt with {len(final_prompt)} characters")
        return final_prompt

    async def build_analysis_prompt(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_id: int,
        chapter_content: str,
    ) -> str:
        """Build prompt for content analysis (used by Phase 4).
        
        Returns prompt for LLM to analyze chapter content.
        """
        # Get project
        project = await project_dao.get(db, project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        # Build analysis prompt
        prompt = f"""请分析以下小说章节内容，提取关键信息用于更新四库。

项目信息：
- 标题：{project.title}
- 类型：{project.genre}

章节内容：
{chapter_content}

请提取以下信息，并以 JSON 格式返回：

1. "characters": 新增或更新的角色列表
2. "timeline_events": 新增的时间线事件列表
3. "plot_promises": 新增或更新的伏笔列表
4. "world_elements": 新增或更新的世界观元素列表
5. "summary": 本章节的内容摘要（200字以内）
6. "anchors": 章节锚点（pov, location, time）

注意：
- 只提取本章节中首次出现或发生变更的信息
- 请确保返回的是有效的 JSON 格式
"""

        return prompt


# Singleton instance
prompt_architecture = PromptArchitecture()
