"""墨灵 (Moling) — Vault Filter Service (四库过滤算法增强).

Step 2 of the Phase 4 algorithm pipeline: receives a list of CardPool cards,
extracts all referenced vault IDs (characters, plot promises, timeline, world),
fetches only the matching vault records, applies hierarchical compression based
on chapter progress, and returns a structured context payload for LLM generation.

Usage:
    filter_result = await vault_filter_service.filter_by_cards(
        db, project_id=1, cards=selected_cards, chapter_number=15
    )
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao
from app.dao.vault_dao import VaultDAO
from app.errors import AppError
from app.models.card_pool import CardPool
from app.models.vault_character import VaultCharacter
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_timeline import VaultTimeline
from app.models.vault_world import VaultWorld

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# 常量
# ────────────────────────────────────────────────────────────────
_CHARACTER_MAX_CHARS = 300       # 人物条目最大字数
_TIMELINE_WINDOW = 3             # 时间线 ± 条数
_COMPRESSION_LEVEL_1 = 1        # 全文模式
_COMPRESSION_LEVEL_2 = 2        # 压缩模式（仅 current_state）
_COMPRESSION_THRESHOLD = 30     # 30 章后切换到 Level 2
_CHARS_PER_TOKEN = 2             # 中文字符与 token 的粗略换算


class VaultFilterService:
    """四库过滤服务 —— 根据卡池卡片 ID 精准提取保险库数据并执行层级压缩。"""

    def __init__(self, dao: Optional[VaultDAO] = None) -> None:
        """初始化，默认使用全局 VaultDAO 实例。

        Args:
            dao: 可注入的 VaultDAO，方便单元测试时 Mock。
        """
        from app.dao import vault_dao as _default_dao
        self._dao = dao or _default_dao

    # ================================================================
    # 公开入口
    # ================================================================

    async def filter_all(
        self,
        db: AsyncSession,
        project_id: int,
        chapter_number: Optional[int] = None,
        max_characters: int = 10,
        max_timeline: int = 5,
        max_world: int = 10,
    ) -> dict[str, Any]:
        """No-card fallback: fetch Top-N vault entries with compression.

        Used when no cards are selected (e.g., Vibe Writing free-input mode).
        Applies the same hierarchical compression as filter_by_cards.

        Args:
            db: SQLAlchemy async session.
            project_id: 项目 ID.
            chapter_number: 当前章节号，决定压缩层级.
            max_characters: 最多取多少人物.
            max_timeline: 时间线最近 N 条.
            max_world: 最多取多少世界观规则.

        Returns:
            dict 同 filter_by_cards 格式。
        """
        logger.info(
            "VaultFilterService.filter_all: project_id=%s, chapter=%s",
            project_id, chapter_number,
        )

        # Fetch all items (no card ID filter)
        characters = list(await self._dao.get_characters(db, project_id))[
            :max_characters
        ]
        timeline = list(await self._dao.get_timeline(db, project_id))[-max_timeline:]
        promises = [
            p for p in (await self._dao.get_plot_promises(db, project_id))
            if p.status in ("dormant", "active")
        ]
        world = list(await self._dao.get_world_entries(db, project_id))[
            :max_world
        ]

        # Apply identical compression pipeline
        compression_level = self._determine_compression_level(chapter_number)
        compressed_characters = self._compress_characters(
            characters, compression_level
        )
        token_estimate = self._estimate_tokens(
            compressed_characters, timeline, promises, world
        )

        result: dict[str, Any] = {
            "characters": compressed_characters,
            "timeline": [self._serialize_timeline_event(e) for e in timeline],
            "plot_promises": [self._serialize_promise(p) for p in promises],
            "world": [self._serialize_world_entry(w) for w in world],
            "compression_level": compression_level,
            "token_estimate": token_estimate,
        }

        logger.info(
            "VaultFilterService.filter_all result: chars=%d, timeline=%d, "
            "promises=%d, world=%d, level=%d, tokens=%d",
            len(result["characters"]),
            len(result["timeline"]),
            len(result["plot_promises"]),
            len(result["world"]),
            result["compression_level"],
            result["token_estimate"],
        )

        return result

    async def filter_by_cards(
        self,
        db: AsyncSession,
        project_id: int,
        cards: List[CardPool],
        chapter_number: Optional[int] = None,
    ) -> dict[str, Any]:
        """主入口：根据卡片集合过滤四库内容。

        Args:
            db: SQLAlchemy async session.
            project_id: 项目 ID.
            cards: 已选中的方向卡片列表.
            chapter_number: 当前章节号，用于决定压缩层级.

        Returns:
            dict 包含 characters / timeline / plot_promises / world /
            compression_level / token_estimate.
        """
        logger.info(
            "VaultFilterService.filter_by_cards called: project_id=%s, cards=%d, chapter=%s",
            project_id, len(cards), chapter_number,
        )

        try:
            # Step 1: 提取所有卡片引用的 ID
            ids = self._extract_card_ids(cards)

            logger.debug(
                "Extracted IDs: chars=%d, promises=%d, timeline_points=%d, world_rules=%d",
                len(ids["character_ids"]),
                len(ids["promise_ids"]),
                len(ids["timeline_points"]),
                len(ids["world_rule_ids"]),
            )

            # Step 2: 按 ID 并行提取四库内容
            characters = await self._fetch_filtered_characters(
                db, project_id, ids["character_ids"]
            )
            timeline = await self._fetch_filtered_timeline(
                db, project_id, ids["timeline_points"]
            )
            promises = await self._fetch_filtered_promises(
                db, project_id, ids["promise_ids"]
            )
            world = await self._fetch_filtered_world(
                db, project_id, ids["world_rule_ids"]
            )

            # Step 3: 确定压缩层级
            compression_level = self._determine_compression_level(chapter_number)

            # Step 4: 应用层级压缩
            compressed_characters = self._compress_characters(
                characters, compression_level
            )

            # 估算 Token
            token_estimate = self._estimate_tokens(
                compressed_characters, timeline, promises, world
            )

            result: dict[str, Any] = {
                "characters": compressed_characters,
                "timeline": [self._serialize_timeline_event(e) for e in timeline],
                "plot_promises": [self._serialize_promise(p) for p in promises],
                "world": [self._serialize_world_entry(w) for w in world],
                "compression_level": compression_level,
                "token_estimate": token_estimate,
            }

            logger.info(
                "VaultFilterService result: chars=%d, timeline=%d, promises=%d, "
                "world=%d, level=%d, tokens=%d",
                len(result["characters"]),
                len(result["timeline"]),
                len(result["plot_promises"]),
                len(result["world"]),
                result["compression_level"],
                result["token_estimate"],
            )

            return result

        except AppError:
            raise
        except Exception as exc:
            logger.exception("VaultFilterService.filter_by_cards failed: %s", exc)
            raise

    # ================================================================
    # Step 1: 提取卡片 ID
    # ================================================================

    def _extract_card_ids(self, cards: List[CardPool]) -> dict[str, Any]:
        """从卡片列表中提取所有引用的 ID 集合。

        遍历每张卡的 characters / plot_promises / timeline_point / world_rules
        字段，收集去重后的 ID 集合。
        """
        character_ids: Set[str] = set()
        promise_ids: Set[str] = set()
        timeline_points: Set[str] = set()
        world_rule_ids: Set[str] = set()

        for card in cards:
            # 角色
            if card.characters and isinstance(card.characters, list):
                for char_ref in card.characters:
                    cid = self._safe_get_id(char_ref)
                    if cid:
                        character_ids.add(cid)

            # 剧情承诺
            if card.plot_promises and isinstance(card.plot_promises, list):
                for prom_ref in card.plot_promises:
                    pid = self._safe_get_id(prom_ref)
                    if pid:
                        promise_ids.add(pid)

            # 时间线关键点
            if card.timeline_point:
                tpoint = str(card.timeline_point).strip()
                if tpoint:
                    timeline_points.add(tpoint)

            # 世界观规则
            if card.world_rules and isinstance(card.world_rules, list):
                for wr_ref in card.world_rules:
                    wid = self._safe_get_id(wr_ref)
                    if wid:
                        world_rule_ids.add(wid)

        return {
            "character_ids": list(character_ids),
            "promise_ids": list(promise_ids),
            "timeline_points": list(timeline_points),
            "world_rule_ids": list(world_rule_ids),
        }

    # ================================================================
    # Step 2: 按 ID 过滤提取
    # ================================================================

    async def _fetch_filtered_characters(
        self,
        db: AsyncSession,
        project_id: int,
        character_ids: List[str],
    ) -> List[VaultCharacter]:
        """按 character_ids 列表提取人物（≤300字/人）。

        单条查询而非逐条 get_character，减少 N+1 问题。
        """
        if not character_ids:
            return []

        return await vault_dao.get_characters_by_ids(
            db, project_id, [int(cid) for cid in character_ids]
        )

    async def _fetch_filtered_timeline(
        self,
        db: AsyncSession,
        project_id: int,
        timeline_points: List[str],
    ) -> List[VaultTimeline]:
        """按 timeline_points ±3 提取时间线事件。

        支持两种格式：
        - 纯数字 → 视为 chapter_number
        - 非数字 → 视为事件描述关键词（LIKE 模糊匹配）
        """
        if not timeline_points:
            return []

        # 先获取项目的全部时间线（已按 chapter_number 排序）
        all_events = await self._dao.get_timeline(db, project_id)
        if not all_events:
            return []

        matched_event_ids: Set[str] = set()

        for point in timeline_points:
            # 尝试按 chapter_number 匹配
            chapter_numbers: List[int] = []
            raw_numbers = point.replace("，", ",").replace("、", ",").split(",")
            for rn in raw_numbers:
                rn = rn.strip()
                try:
                    chapter_numbers.append(int(rn))
                except ValueError:
                    # 非数字，尝试事件描述模糊匹配
                    pass

            if chapter_numbers:
                for cn in chapter_numbers:
                    for idx, evt in enumerate(all_events):
                        if evt.chapter_number == cn:
                            window_start = max(0, idx - _TIMELINE_WINDOW)
                            window_end = min(len(all_events), idx + _TIMELINE_WINDOW + 1)
                            for i in range(window_start, window_end):
                                matched_event_ids.add(str(all_events[i].id))
                            break
            else:
                # 作为事件描述关键词模糊匹配
                point_lower = point.lower()
                for idx, evt in enumerate(all_events):
                    if point_lower in evt.event.lower() or point_lower in evt.description.lower():
                        window_start = max(0, idx - _TIMELINE_WINDOW)
                        window_end = min(len(all_events), idx + _TIMELINE_WINDOW + 1)
                        for i in range(window_start, window_end):
                            matched_event_ids.add(str(all_events[i].id))

        # 按 ID 过滤并保持排序
        return [
            evt for evt in all_events
            if str(evt.id) in matched_event_ids
        ]

    async def _fetch_filtered_promises(
        self,
        db: AsyncSession,
        project_id: int,
        promise_ids: List[str],
    ) -> List[VaultPlotPromise]:
        """按 promise_ids 列表提取剧情承诺全文。"""
        if not promise_ids:
            return []

        return await vault_dao.get_plot_promises_by_ids(
            db, project_id, [int(pid) for pid in promise_ids]
        )

    async def _fetch_filtered_world(
        self,
        db: AsyncSession,
        project_id: int,
        world_rule_ids: List[str],
    ) -> List[VaultWorld]:
        """按 world_rule_ids 列表提取世界观条目原文。"""
        if not world_rule_ids:
            return []

        return await vault_dao.get_world_entries_by_ids(
            db, project_id, [int(wid) for wid in world_rule_ids]
        )

    # ================================================================
    # Step 3: 层级压缩
    # ================================================================

    @staticmethod
    def _determine_compression_level(chapter_number: Optional[int]) -> int:
        """根据章节号确定压缩层级。

        - Level 1（默认）: 全文注入，适用于前期/中期（≤30章）
        - Level 2（30章后）: 人物只保留"当前状态"字段
        """
        if chapter_number is None:
            return _COMPRESSION_LEVEL_1
        return (
            _COMPRESSION_LEVEL_1
            if chapter_number <= _COMPRESSION_THRESHOLD
            else _COMPRESSION_LEVEL_2
        )

    @staticmethod
    def _compress_characters(
        characters: List[VaultCharacter],
        compression_level: int,
    ) -> List[dict[str, Any]]:
        """对人物列表应用层级压缩。

        Level 1: 全文（含 300 字截断）
        Level 2: 仅保留 id, name, role, status, current_state
        """
        if compression_level == _COMPRESSION_LEVEL_2:
            return [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "role": c.role,
                    "status": c.status,
                    "current_state": c.current_state or "",
                }
                for c in characters
            ]

        # Level 1: 全文，但限制字数
        result: List[dict[str, Any]] = []
        for c in characters:
            serialized = VaultFilterService._serialize_character(c)
            # 截断长文本字段以控制总字数
            serialized = VaultFilterService._truncate_character_fields(
                serialized, max_chars=_CHARACTER_MAX_CHARS
            )
            result.append(serialized)
        return result

    # ================================================================
    # 序列化辅助
    # ================================================================

    @staticmethod
    def _serialize_character(char: VaultCharacter) -> dict[str, Any]:
        """将 VaultCharacter ORM 对象转换为可序列化的字典。"""
        return {
            "id": str(char.id),
            "name": char.name,
            "role": char.role,
            "faction": char.faction or "",
            "status": char.status,
            "location": char.location or "",
            "appearance": char.appearance or "",
            "personality": char.personality or "",
            "knowledge": char.knowledge or [],
            "confidence": char.confidence,
            "current_state": char.current_state or "",
            "motivation": char.motivation or "",
            "emotion": char.emotion or "",
            "traits": char.traits or [],
            "description": char.description or "",
            "background": char.background or "",
            "relationships": char.relationships or [],
            "state_machine": char.state_machine or {},
        }

    @staticmethod
    def _truncate_character_fields(
        data: dict[str, Any],
        max_chars: int = _CHARACTER_MAX_CHARS,
    ) -> dict[str, Any]:
        """截断人物字典中的长文本字段，确保条目总长度不超过 max_chars。

        优先保留结构化字段（id, name, role, status），
        截断 description / background / personality / appearance 等长文本。
        """
        text_fields = [
            "description",
            "background",
            "personality",
            "appearance",
            "motivation",
        ]
        # 先计算非文本字段的基础长度
        base_len = sum(
            len(str(v))
            for k, v in data.items()
            if k not in text_fields and v is not None
        )
        available = max_chars - base_len
        if available <= 0:
            # 基础字段已超限，清空所有文本字段
            for field in text_fields:
                data[field] = ""
            return data

        # 按优先级分配字符给文本字段
        priority = ["description", "personality", "background", "motivation", "appearance"]
        for field in priority:
            if field not in data or not data[field]:
                continue
            if available <= 0:
                data[field] = ""
                continue
            raw = str(data[field])
            if len(raw) <= available:
                available -= len(raw)
            else:
                data[field] = raw[:available] + "…" if available > 1 else ""
                available = 0

        return data

    @staticmethod
    def _serialize_timeline_event(event: VaultTimeline) -> dict[str, Any]:
        """将 VaultTimeline ORM 对象转换为可序列化的字典。"""
        return {
            "id": str(event.id),
            "event": event.event,
            "description": event.description,
            "chapter_number": event.chapter_number,
            "day": event.day,
            "importance": event.importance or "",
            "is_key_event": event.is_key_event,
            "impact": event.impact or "",
            "characters_involved": event.characters_involved or [],
            "precedes": event.precedes or [],
        }

    @staticmethod
    def _serialize_promise(promise: VaultPlotPromise) -> dict[str, Any]:
        """将 VaultPlotPromise ORM 对象转换为可序列化的字典。"""
        return {
            "id": str(promise.id),
            "description": promise.description,
            "type": promise.type,
            "title": promise.title or "",
            "status": promise.status,
            "urgency": promise.urgency,
            "advancement_log": promise.advancement_log or [],
            "related_characters": promise.related_characters or [],
            "planted_chapter": promise.planted_chapter,
            "redeem_window": promise.redeem_window,
        }

    @staticmethod
    def _serialize_world_entry(entry: VaultWorld) -> dict[str, Any]:
        """将 VaultWorld ORM 对象转换为可序列化的字典。"""
        return {
            "id": str(entry.id),
            "name": entry.name,
            "description": entry.description,
            "category": entry.category,
            "constraint": entry.constraint or "",
            "related_entities": entry.related_entities or [],
            "source_chapter": entry.source_chapter,
            "reference_chapters": entry.reference_chapters or [],
        }

    # ================================================================
    # Token 估算
    # ================================================================

    @staticmethod
    def _estimate_tokens(
        characters: List[dict],
        timeline: List[VaultTimeline],
        promises: List[VaultPlotPromise],
        world: List[VaultWorld],
    ) -> int:
        """估算四库内容的 Token 数量（按中文字符 ÷ 2 粗略计算）。"""
        total_chars = sum(
            len(str(v))
            for c in characters
            for v in c.values()
            if v is not None
        )
        total_chars += sum(
            len(str(v))
            for evt in [
                {
                    "event": e.event,
                    "description": e.description,
                    "impact": e.impact or "",
                }
                for e in timeline
            ]
            for v in evt.values()
            if v is not None
        )
        total_chars += sum(
            len(str(v))
            for p in promises
            for v in [
                p.description,
                p.title or "",
                " ".join(str(log) for log in (p.advancement_log or [])),
            ]
            if v
        )
        total_chars += sum(
            len(str(v))
            for w in world
            for v in [
                w.name,
                w.description,
                w.constraint or "",
            ]
            if v
        )
        return max(1, total_chars // _CHARS_PER_TOKEN)

    # ================================================================
    # 内部工具
    # ================================================================

    @staticmethod
    def _safe_get_id(ref: Any) -> Optional[str]:
        """从引用对象或字典中安全提取 'id'。

        CardPool 的 JSON 字段可能反序列化为 dict 或 对象。
        """
        if ref is None:
            return None
        if isinstance(ref, dict):
            raw = ref.get("id")
        elif hasattr(ref, "id"):
            raw = ref.id
        else:
            return None
        return str(raw).strip() if raw else None


# 单例
vault_filter_service = VaultFilterService()
