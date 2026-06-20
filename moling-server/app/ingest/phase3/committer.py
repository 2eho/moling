"""
墨灵 (Moling) — Ingest Phase 3 Committer

事务性写入：
1. 角色库写入（upsert）
2. 时间线写入
3. 剧情承诺写入
4. 世界观写入
5. 初始卡牌池生成
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld
from app.models.card_pool import CardPool
from app.models.chapter import Chapter

logger = logging.getLogger(__name__)


class Phase3Committer:
    """Phase 3 事务写入执行器"""

    def __init__(
        self,
        db: AsyncSession,
        project_id: str,
        resolve_strategy: str = "keep_existing",
    ):
        self.db = db
        self.project_id = project_id
        self.resolve_strategy = resolve_strategy

    async def commit(self, phase1_result: dict, conflicts: list[dict]) -> dict:
        """
        执行事务性写入。

        遵循冲突解决策略：
        - keep_existing: 跳过冲突项，保留现有数据
        - merge: 合并新旧数据
        - replace: 用新数据替换

        使用 SQLAlchemy savepoint 保护每个子步骤，
        异常时执行显式 rollback 确保已 flush 的数据被回滚。
        """
        imported_counts = {
            "imported_characters": 0,
            "imported_timeline_events": 0,
            "imported_promises": 0,
            "imported_world_items": 0,
            "card_pool_generated": 0,
            "status": "completed",
            "message": "导入完成",
        }
        failed_steps: dict[str, str] = {}

        try:
            # 1. 写入角色库（savepoint 保护）
            try:
                async with self.db.begin_nested() as sp_char:
                    char_count = await self._commit_characters(
                        phase1_result.get("characters", []),
                        conflicts,
                    )
                    imported_counts["imported_characters"] = char_count
            except Exception as e:
                logger.warning("角色库写入失败，已回滚: %s", e)
                failed_steps["characters"] = str(e)

            # 2. 写入时间线（savepoint 保护）
            try:
                async with self.db.begin_nested() as sp_timeline:
                    timeline_count = await self._commit_timeline(
                        phase1_result.get("timeline_events", []),
                        conflicts,
                    )
                    imported_counts["imported_timeline_events"] = timeline_count
            except Exception as e:
                logger.warning("时间线写入失败，已回滚: %s", e)
                failed_steps["timeline"] = str(e)

            # 3. 写入剧情承诺（savepoint 保护）
            try:
                async with self.db.begin_nested() as sp_promise:
                    promise_count = await self._commit_promises(
                        phase1_result.get("promises", []),
                        conflicts,
                    )
                    imported_counts["imported_promises"] = promise_count
            except Exception as e:
                logger.warning("剧情承诺写入失败，已回滚: %s", e)
                failed_steps["promises"] = str(e)

            # 4. 写入世界观（savepoint 保护）
            try:
                async with self.db.begin_nested() as sp_world:
                    world_count = await self._commit_world(
                        phase1_result.get("world_items", []),
                        conflicts,
                    )
                    imported_counts["imported_world_items"] = world_count
            except Exception as e:
                logger.warning("世界观写入失败，已回滚: %s", e)
                failed_steps["world"] = str(e)

            # 5. 生成初始卡牌池（savepoint 保护）
            try:
                async with self.db.begin_nested() as sp_card:
                    card_count = await self._generate_card_pool(phase1_result)
                    imported_counts["card_pool_generated"] = card_count
            except Exception as e:
                logger.warning("卡牌池生成失败，已回滚: %s", e)
                failed_steps["card_pool"] = str(e)

        except Exception as e:
            logger.exception("Phase 3 事务提交失败，执行全局回滚")
            await self.db.rollback()
            return {
                **imported_counts,
                "status": "failed",
                "message": f"导入失败: {str(e)}",
                "failed_steps": failed_steps,
            }

        if failed_steps:
            imported_counts["status"] = "partial"
            imported_counts["message"] = "部分导入成功"
            imported_counts["failed_steps"] = failed_steps

        return imported_counts

    async def _commit_characters(
        self,
        characters: list[dict],
        conflicts: list[dict],
    ) -> int:
        """写入角色库。"""
        count = 0
        conflict_names = {
            c["name"] for c in conflicts if c["type"] == "character_conflict"
            and c.get("severity") != "low"
        }

        for char_data in characters:
            name = char_data.get("name", "")
            if not name:
                continue

            # 检查是否与已有角色冲突
            result = await self.db.execute(
                select(VaultCharacter).where(
                    VaultCharacter.project_id == self.project_id,
                    VaultCharacter.name == name,
                )
            )
            existing = result.scalar_one_or_none()

            if existing and name in conflict_names:
                if self.resolve_strategy == "keep_existing":
                    continue
                elif self.resolve_strategy == "replace":
                    # 更新现有角色
                    self._update_character(existing, char_data)
                elif self.resolve_strategy == "merge":
                    # 合并描述
                    if char_data.get("description") and len(char_data["description"]) > len(existing.description or ""):
                        existing.description = char_data["description"]
                    existing.chapter_count += 1
                continue

            if existing and name not in conflict_names:
                # 无冲突的合并
                existing.chapter_count += 1
                count += 1
                continue

            # 创建新角色
            role = "ally"
            if "主角" in char_data.get("tags", []):
                role = "protagonist"
            elif "反派" in char_data.get("tags", []):
                role = "antagonist"
            elif "对手" in char_data.get("tags", []):
                role = "opponent"
            elif "中立" in char_data.get("tags", []):
                role = "neutral"

            new_char = VaultCharacter(
                project_id=self.project_id,
                name=name,
                role=role,
                description=char_data.get("description", ""),
                traits=char_data.get("tags", []),
                chapter_count=len(char_data.get("chapters_active", [])),
            )
            self.db.add(new_char)
            count += 1

        return count

    async def _commit_timeline(
        self,
        events: list[dict],
        conflicts: list[dict],
    ) -> int:
        """写入时间线。"""
        count = 0
        conflict_descs = {
            c.get("event", "") for c in conflicts if c["type"] == "timeline_conflict"
        }

        for event in events:
            desc = event.get("description", "")
            if not desc:
                continue

            # 检查冲突
            if desc[:30] in conflict_descs:
                if self.resolve_strategy == "keep_existing":
                    continue

            new_event = VaultTimeline(
                project_id=self.project_id,
                chapter_number=event.get("chapter_index", 0) + 1,
                event=desc[:300],
                description=desc,
                is_key_event=event.get("is_key_event", False) or event.get("importance", 3) >= 4,
                characters_involved=event.get("characters", []),
            )
            self.db.add(new_event)
            count += 1

        return count

    async def _commit_promises(self, promises: list[dict], conflicts: list[dict]) -> int:
        """写入剧情承诺。"""
        count = 0
        for promise in promises:
            new_promise = VaultPlotPromise(
                project_id=self.project_id,
                description=promise.get("text", ""),
                type=promise.get("type", "foreshadowing"),
                status=promise.get("status", "dormant"),
                urgency=promise.get("urgency", 5),
                related_characters=promise.get("related_characters", []),
                planted_chapter=promise.get("chapter_index", 0) + 1,
            )
            self.db.add(new_promise)
            count += 1
        return count

    async def _commit_world(self, items: list[dict], conflicts: list[dict]) -> int:
        """写入世界观。"""
        count = 0
        conflict_terms = {
            c["name"] for c in conflicts if c["type"] == "world_conflict"
        }

        for item in items:
            term = item.get("term", "")
            if not term:
                continue

            if term in conflict_terms:
                if self.resolve_strategy == "keep_existing":
                    continue

            new_item = VaultWorld(
                project_id=self.project_id,
                term=term,
                description=item.get("description", ""),
                category=item.get("category", "other"),
                reference_chapters=item.get("reference_chapters", []),
            )
            self.db.add(new_item)
            count += 1

        return count

    async def _generate_card_pool(self, phase1_result: dict) -> int:
        """
        从四库分析结果生成初始卡牌池。

        策略：
        - 主要角色 → 角色灵感卡
        - 关键事件 → 情节灵感卡
        - 世界观元素 → 设定灵感卡
        """
        count = 0

        # 角色卡
        for char in phase1_result.get("characters", [])[:10]:
            name = char.get("name", "")
            desc = char.get("description", "")
            if not name:
                continue

            # 根据角色标签确定稀有度
            tags = char.get("tags", [])
            if "主角" in tags:
                rarity = "epic"
                direction = "惊艳"
            elif "反派" in tags:
                rarity = "rare"
                direction = "有趣"
            else:
                rarity = "common"
                direction = "稳妥"

            card = CardPool(
                project_id=self.project_id,
                name=f"角色·{name}",
                description=desc[:200] if desc else f"角色「{name}」的灵感卡片",
                rarity=rarity,
                direction_type=direction,
                direction_text=f"围绕角色「{name}」展开情节",
                status="active",
            )
            self.db.add(card)
            count += 1

        # 剧情卡（关键事件）
        for event in phase1_result.get("timeline_events", [])[:5]:
            desc = event.get("description", "")
            if not desc:
                continue

            card = CardPool(
                project_id=self.project_id,
                name=f"情节·{desc[:30]}",
                description=desc[:200],
                rarity="rare",
                direction_type="有趣",
                direction_text=f"基于关键情节「{desc[:50]}」展开",
                status="active",
            )
            self.db.add(card)
            count += 1

        return count

    def _update_character(self, existing: VaultCharacter, new_data: dict):
        """更新已有角色的字段。"""
        if new_data.get("description"):
            existing.description = new_data["description"]
        if new_data.get("tags"):
            existing.traits = new_data["tags"]
        existing.chapter_count += 1
