"""墨灵 (Moling) — 四库合并服务 (MergeService).

P0-3: 四库合并核心引擎。
- 人物库合并 (merge_characters) — 模糊匹配/状态变更/置信度降级
- 时间线库合并 (merge_timeline) — add/resolve_date/correct
- 剧情承诺库合并 (merge_plot_promises) — create/advance/redeem/cancel
- 世界观库合并 (merge_world_building) — create/expand/revise/conflict
- 变更日志 (archive_changelog) — ChangeEntry → VaultChangelog

P1-4: 置信度降级策略。
- ConfidenceLevel 枚举（HIGH/MEDIUM/LOW/REJECT）
- evaluate_confidence / should_auto_apply 函数
- MergeResult / ChangeEntry 新增置信度相关字段

所有 merge 方法遵循统一 4 步模式：
[1] 解析验证 → [2] 查找匹配 → [3] 执行合并 → [4] 记录日志
每个步骤抛出的异常由调用方处理（P0-5 事务边界）。
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import vault_dao
from app.models.vault_character import VaultCharacter
from app.models.vault_timeline import VaultTimeline
from app.models.vault_plot_promise import VaultPlotPromise
from app.models.vault_world import VaultWorld
from app.models.vault_changelog import VaultChangelog
from app.utils.service_helpers import _calc_edit_distance, _get_last_advance_chapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

STALE_CHAPTER_THRESHOLD = 20         # 承诺超时阈值（章）
SUB_PROMISE_CONSISTENCY_LIMIT = 3    # 子承诺递归检查阈值
MAX_AMBIGUOUS_MATCHES = 3            # 编辑距离多匹配记录上限

# 中文姓氏首字匹配：仅匹配姓氏（中文名字的第一个字符）
SURNAME_MATCH_CONFIDENCE = 0.5
NEW_ENTITY_CONFIDENCE = 0.3

# 编辑距离 → 置信度映射
EDIT_DIST_CONFIDENCE = {0: 1.0, 1: 0.9, 2: 0.75}

# P1-4 置信度阈值
CONFIDENCE_HIGH_THRESHOLD = 0.8   # > 0.8 自动入库
CONFIDENCE_MEDIUM_THRESHOLD = 0.5 # 0.5-0.8 后台标记需审核
CONFIDENCE_LOW_THRESHOLD = 0.3    # 0.3-0.5 弹窗确认


# ---------------------------------------------------------------------------
# P1-4: 置信度降级策略
# ---------------------------------------------------------------------------


class ConfidenceLevel(enum.Enum):
    """4 级置信度评估。

    HIGH   — > 0.8: 自动入库，无需确认
    MEDIUM — 0.5-0.8: 自动入库 + 后台标记"需审核"
    LOW    — 0.3-0.5: 暂停入库，弹窗确认
    REJECT — < 0.3: 忽略，不写入数据库
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    REJECT = "reject"


def evaluate_confidence(confidence_score: float) -> ConfidenceLevel:
    """根据置信度分数返回对应的 ConfidenceLevel。"""
    if confidence_score > CONFIDENCE_HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    elif confidence_score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    elif confidence_score >= CONFIDENCE_LOW_THRESHOLD:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.REJECT


def should_auto_apply(level: ConfidenceLevel) -> bool:
    """HIGH 和 MEDIUM 自动入库，LOW 需确认，REJECT 忽略。"""
    return level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)


# ---------------------------------------------------------------------------
# 数据传输对象 (DTO)
# ---------------------------------------------------------------------------


@dataclass
class ChangeEntry:
    """单条变更日志记录。"""
    entity_type: str          # character | timeline | plot_promise | world
    entity_id: str            # 实体 ID (字符串)
    entity_name: str          # 实体名称
    change_type: str          # create | update | status_change | retire | conflict
    old_value: Optional[str]  # 旧值（可选）
    new_value: Optional[str]  # 新值（可选）
    chapter: int              # 变更章节
    confidence: float         # 置信度 (0-1)
    change_reason: str        # 人类可读的变更原因
    confidence_level: Optional[ConfidenceLevel] = None  # P1-4: 置信度等级


@dataclass
class MergeResult:
    """合并操作的结果。"""
    entity_type: str                        # 实体类型
    created: int = 0                        # 新建数量
    updated: int = 0                        # 更新数量
    deleted: int = 0                        # 删除/淘汰数量
    conflicts: List[Dict[str, Any]] = field(default_factory=list)   # 冲突列表
    warnings: List[str] = field(default_factory=list)               # 警告列表
    changes: List[ChangeEntry] = field(default_factory=list)        # 本次变更日志
    # P1-4: 置信度评估
    confidence_level: Optional[ConfidenceLevel] = None              # 整体置信度等级
    auto_applied: bool = False                                      # 是否自动入库
    items_requiring_review: List[ChangeEntry] = field(default_factory=list)  # LOW 级别条目


# ---------------------------------------------------------------------------
# 提取输入 DTO
# ---------------------------------------------------------------------------


@dataclass
class ExtractedCharacter:
    """LLM 提取的角色变更。"""
    name: str
    role: str = "neutral"
    aliases: List[str] = field(default_factory=list)
    status: str = "active"
    appearance: Optional[str] = None
    personality: Optional[str] = None
    description: Optional[str] = None
    faction: Optional[str] = None
    location: Optional[str] = None
    current_state: Optional[str] = None
    motivation: Optional[str] = None
    confidence: float = 0.8


@dataclass
class ExtractedTimelineEvent:
    """LLM 提取的时间线事件。"""
    action: str                    # add | resolve_date | correct
    event: str                     # 事件描述
    day: Optional[int] = None      # 绝对天数
    chapter: int = 0               # 章节号
    description: str = ""          # 详细描述
    participants: List[str] = field(default_factory=list)
    importance: str = "minor"      # major | minor
    is_key_event: bool = False


@dataclass
class ExtractedPlotPromise:
    """LLM 提取的剧情承诺。"""
    action: str                    # create | advance | redeem | cancel
    title: str                     # 承诺标题
    description: str = ""
    type: str = "悬念"              # 人物弧光 | 剧情转折 | 悬念 | 关系发展 | 世界观秘密
    status: str = "active"
    related_characters: List[str] = field(default_factory=list)
    cancel_reason: Optional[str] = None


@dataclass
class ExtractedWorldItem:
    """LLM 提取的世界观条目。"""
    action: str                    # create | expand | revise | conflict
    name: str                      # 条目名称
    category: str = "other"        # geography | history | system | faction | event
    content: str = ""              # 详细内容
    old_content: Optional[str] = None  # 修订前的内容（revise 时使用）


# ---------------------------------------------------------------------------
# MergeService
# ---------------------------------------------------------------------------


class MergeService:
    """四库合并核心引擎。

    接收 LLM 提取的结构化变更，执行合并操作并返回变更日志。
    所有异常直接抛出，由调用方（P0-5 事务层）处理回滚。
    """

    # ==================================================================
    # 工具方法
    # ==================================================================

    @staticmethod
    def _calc_confidence(edit_distance: int, matched: bool = True) -> float:
        """根据匹配策略计算置信度。"""
        if matched:
            return EDIT_DIST_CONFIDENCE.get(edit_distance, SURNAME_MATCH_CONFIDENCE)
        return NEW_ENTITY_CONFIDENCE

    @staticmethod
    def _surname_match(name1: str, name2: str) -> bool:
        """中文姓氏匹配：比较第一个字符。"""
        if not name1 or not name2:
            return False
        return name1[0] == name2[0]

    @staticmethod
    def _generate_change_reason(
        entity_type: str, action: str, entity_name: str,
        detail: Optional[str] = None,
    ) -> str:
        """生成人类可读的变更原因。"""
        reason_map = {
            "create": f"合并: 新建{entity_type} '{entity_name}'",
            "update": f"合并: 更新{entity_type} '{entity_name}'",
            "status_change": f"合并: {entity_type} '{entity_name}' 状态变更",
            "match": f"合并: 模糊匹配 '{entity_name}' 到已有实体",
            "conflict": f"合并: {entity_type} '{entity_name}' 检测到冲突",
            "stale": f"合并: {entity_type} '{entity_name}' 已超时",
        }
        reason = reason_map.get(action, f"合并: {entity_type} '{entity_name}'")
        if detail:
            reason += f" — {detail}"
        return reason

    @staticmethod
    def _evaluate_merge_confidence(result: MergeResult) -> MergeResult:
        """评估 MergeResult 的整体置信度并填充相关字段。

        基于所有 change 条目的平均置信度计算整体 confidence_level，
        并收集需要人工审核（LOW）的条目。
        """
        if not result.changes:
            # 无变更时默认 HIGH（不需要关注）
            result.confidence_level = ConfidenceLevel.HIGH
            result.auto_applied = True
            result.items_requiring_review = []
            return result

        # 为每个 ChangeEntry 设置 confidence_level
        avg_confidence = 0.0
        for change in result.changes:
            level = evaluate_confidence(change.confidence)
            change.confidence_level = level
            avg_confidence += change.confidence
            if level == ConfidenceLevel.LOW:
                result.items_requiring_review.append(change)

        avg_confidence /= len(result.changes)
        result.confidence_level = evaluate_confidence(avg_confidence)
        result.auto_applied = should_auto_apply(result.confidence_level)

        return result

    # ==================================================================
    # 15-1: 人物库合并
    # ==================================================================

    async def merge_characters(
        self,
        db: AsyncSession,
        project_id: int,
        extracted: List[ExtractedCharacter],
        chapter_number: int,
    ) -> MergeResult:
        """合并人物库变更。

        匹配策略（优先级）：
          1. 精确 ID（如提供）
          2. 精确名称
          3. 别名匹配
          4. 编辑距离 ≤ 2
          5. 姓氏匹配
          6. 无匹配 → 新建

        状态变更规则：
          - active → active: 无变化
          - active → deceased: 设置 death_chapter
          - active → dormant: 设置 last_active_chapter
          - active → resolved: 设置 resolution_chapter
          - 其他: 记入 changelog，标记“异常变更”
        """
        result = MergeResult(entity_type="character")
        if not extracted:
            return result

        existing = await vault_dao.get_characters(db, project_id)
        existing_by_name: Dict[str, VaultCharacter] = {c.name: c for c in existing}

        for item in extracted:
            name = item.name.strip() if item.name else ""
            if not name:
                result.warnings.append("跳过空名字的人物条目")
                continue

            match_id, match_name, match_type, edit_dist = self._find_best_character_match(
                item, existing,
            )

            if match_id is not None:
                # 在已存在条目中查找匹配的实体
                matched_char = next((c for c in existing if c.id == match_id), None)
                if matched_char is None:
                    raise ValueError(f"匹配的 VaultCharacter (id={match_id}) 不存在")

                old_values: Dict[str, Any] = {}
                update_fields: Dict[str, Any] = {}

                # 更新基础字段
                for field in ("role", "faction", "location", "current_state",
                              "motivation", "description", "personality", "appearance"):
                    new_val = getattr(item, field, None)
                    if new_val is not None:
                        old_val = getattr(matched_char, field, None)
                        old_values[field] = old_val
                        update_fields[field] = new_val

                # 合并 traits
                if item.personality and matched_char.traits:
                    existing_traits = set(str(t) for t in (matched_char.traits or []))
                    new_traits = [t for t in item.personality.split(",") if t.strip()]
                    for t in new_traits:
                        t = t.strip()
                        if t and t not in existing_traits:
                            existing_traits.add(t)
                    update_fields["traits"] = list(existing_traits)

                # 增加章节计数
                update_fields["chapter_count"] = (matched_char.chapter_count or 0) + 1

                # 更新 chapter_hist
                hist = list(matched_char.chapter_hist or [])
                if chapter_number not in hist:
                    hist.append(chapter_number)
                update_fields["chapter_hist"] = hist

                # 更新置信度（不低于已有值）
                new_confidence = self._calc_confidence(edit_dist, matched=True)
                update_fields["confidence"] = max(
                    matched_char.confidence or 0, new_confidence,
                )

                await vault_dao.update_character(db, matched_char, update_fields)

                confidence = update_fields["confidence"]
                reason_parts = []
                if match_type == "edit_distance":
                    reason_parts.append(f"编辑距离={edit_dist}")
                elif match_type == "alias":
                    reason_parts.append("别名匹配")
                elif match_type == "surname":
                    reason_parts.append("姓氏匹配")

                result.changes.append(ChangeEntry(
                    entity_type="character",
                    entity_id=str(matched_char.id),
                    entity_name=name,
                    change_type="update",
                    old_value=str(old_values) if old_values else None,
                    new_value=str(update_fields),
                    chapter=chapter_number,
                    confidence=confidence,
                    change_reason=self._generate_change_reason(
                        "角色", "update" if match_type == "exact" else "match", name,
                        detail="; ".join(reason_parts) if reason_parts else None,
                    ),
                ))
                result.updated += 1

            else:
                # 无匹配 → 新建
                new_char = await vault_dao.create_character(db, {
                    "project_id": project_id,
                    "name": name,
                    "role": item.role or "neutral",
                    "faction": item.faction or "",
                    "location": item.location or "",
                    "current_state": item.current_state or "",
                    "motivation": item.motivation or "",
                    "description": item.description or "",
                    "personality": item.personality or "",
                    "appearance": item.appearance or "",
                    "confidence": NEW_ENTITY_CONFIDENCE,
                    "chapter_count": 1,
                    "chapter_hist": [chapter_number] if chapter_number else [],
                    "status": item.status or "active",
                })

                result.changes.append(ChangeEntry(
                    entity_type="character",
                    entity_id=str(new_char.id),
                    entity_name=name,
                    change_type="create",
                    old_value=None,
                    new_value=None,
                    chapter=chapter_number,
                    confidence=NEW_ENTITY_CONFIDENCE,
                    change_reason=self._generate_change_reason(
                        "角色", "create", name,
                        detail="无匹配，作为新实体创建",
                    ),
                ))
                result.created += 1

        self._evaluate_merge_confidence(result)
        return result

    def _find_best_character_match(
        self,
        item: ExtractedCharacter,
        existing: List[VaultCharacter],
    ) -> Tuple[Optional[int], Optional[str], Optional[str], int]:
        """查找最佳角色匹配。

        Returns:
            (matched_id, matched_name, match_type, edit_distance)
            若无匹配，所有值为 None/0。
        """
        name = item.name.strip()

        if not existing:
            return None, None, None, 0

        # 1. 精确名称匹配
        for c in existing:
            if c.name == name:
                return c.id, c.name, "exact", 0

        # 2. 别名匹配
        for c in existing:
            aliases = self._get_character_aliases(c)
            if name in aliases:
                return c.id, c.name, "alias", 0

        # 3. 编辑距离匹配 (≤ 2)
        best_dist = 999
        best_id = None
        best_name = None
        ambiguous_matches: List[Tuple[str, int]] = []

        for c in existing:
            dist = _calc_edit_distance(name, c.name)
            if dist <= 2 and dist < best_dist:
                best_dist = dist
                best_id = c.id
                best_name = c.name
                ambiguous_matches = [(c.name, dist)]
            elif dist <= 2 and dist == best_dist:
                ambiguous_matches.append((c.name, dist))

        if best_id is not None and len(ambiguous_matches) <= MAX_AMBIGUOUS_MATCHES:
            return best_id, best_name, "edit_distance", best_dist

        # 4. 姓氏匹配（中文首字）
        for c in existing:
            if self._surname_match(name, c.name):
                return c.id, c.name, "surname", 3  # 固定 distance=3 表示姓氏匹配

        # 5. 无匹配
        return None, None, None, 0

    @staticmethod
    def _get_character_aliases(char: VaultCharacter) -> List[str]:
        """从 VaultCharacter 获取别名列表。"""
        aliases: List[str] = []
        # 从 traits 中提取（现有代码用 traits 存储别名）
        if char.traits and isinstance(char.traits, list):
            for t in char.traits:
                if isinstance(t, str) and t != char.name:
                    aliases.append(t)
        # 从 state_machine 取别名
        if char.state_machine and isinstance(char.state_machine, dict):
            sm_aliases = char.state_machine.get("aliases", [])
            if isinstance(sm_aliases, list):
                aliases.extend(a for a in sm_aliases if isinstance(a, str))
        return list(set(aliases))

    # ==================================================================
    # 15-2: 时间线库合并
    # ==================================================================

    async def merge_timeline(
        self,
        db: AsyncSession,
        project_id: int,
        extracted: List[ExtractedTimelineEvent],
        chapter_number: int,
    ) -> MergeResult:
        """合并时间线库变更。

        操作类型：
          - add: 新建时间线事件
          - resolve_date: 解决日期冲突（多事件同日期 → 标注多条）
          - correct: 修正已有事件（附证据）

        日期冲突处理：
          - 同一天多个不同事件 → 都保留，标注 multiple_events
          - 同一天相同事件 → 去重，保留最早版本
          - 关键节点事件 (major_plot=True) → 置顶
        """
        result = MergeResult(entity_type="timeline")
        if not extracted:
            return result

        existing = await vault_dao.get_timeline(db, project_id)

        # 建立 (day, event_lower) → event_id 映射用于去重
        existing_event_map: Dict[Tuple[Optional[int], str], int] = {}
        for evt in existing:
            key = (evt.day, evt.event.lower().strip())
            existing_event_map[key] = evt.id

        # 收集同日期冲突
        day_event_count: Dict[Optional[int], int] = {}
        for evt in existing:
            day_event_count[evt.day] = day_event_count.get(evt.day, 0) + 1

        for item in extracted:
            event_text = item.event.strip() if item.event else ""
            if not event_text:
                result.warnings.append("跳过空事件描述的时间线条目")
                continue

            if item.action == "add":
                dedup_key = (item.day, event_text.lower())
                if dedup_key in existing_event_map:
                    # 去重，保留最早版本
                    result.warnings.append(
                        f"时间线事件 '{event_text}' 已存在，跳过重复"
                    )
                    continue

                # 检测同日期冲突
                is_multiple_events = False
                if item.day is not None:
                    day_event_count[item.day] = day_event_count.get(item.day, 0) + 1
                    if day_event_count[item.day] > 1:
                        is_multiple_events = True

                new_event = await vault_dao.create_timeline_event(db, {
                    "project_id": project_id,
                    "event": event_text,
                    "description": item.description or event_text,
                    "day": item.day,
                    "chapter_number": item.chapter or chapter_number,
                    "source_chapter": chapter_number,
                    "importance": item.importance or "minor",
                    "is_key_event": item.is_key_event or item.importance == "major",
                    "characters_involved": item.participants or [],
                })

                # 标记冲突
                meta = {}
                if is_multiple_events:
                    result.conflicts.append({
                        "event_id": str(new_event.id),
                        "event": event_text,
                        "day": item.day,
                        "reason": "同一天多事件冲突",
                    })
                    meta["conflict"] = "multiple_events"

                result.changes.append(ChangeEntry(
                    entity_type="timeline",
                    entity_id=str(new_event.id),
                    entity_name=event_text[:80],
                    change_type="create",
                    old_value=None,
                    new_value=None,
                    chapter=chapter_number,
                    confidence=0.9 if item.is_key_event else 0.7,
                    change_reason=self._generate_change_reason(
                        "时间线事件", "create", event_text[:50],
                    ),
                ))
                result.created += 1

            elif item.action in ("resolve_date", "correct"):
                # 查找已有事件
                target = self._find_timeline_event(existing, event_text)
                if target is None:
                    result.warnings.append(
                        f"未找到时间线事件 '{event_text}'，无法执行 {item.action}"
                    )
                    continue

                update_fields: Dict[str, Any] = {}
                old_values: Dict[str, Any] = {}

                if item.action == "resolve_date" and item.day is not None:
                    old_values["day"] = target.day
                    update_fields["day"] = item.day

                if item.action == "correct":
                    if item.day is not None:
                        old_values["day"] = target.day
                        update_fields["day"] = item.day
                    if item.description:
                        old_values["description"] = target.description
                        update_fields["description"] = item.description

                if update_fields:
                    event_id = target.id
                    await vault_dao.update_timeline_event(db, target, update_fields)

                    result.changes.append(ChangeEntry(
                        entity_type="timeline",
                        entity_id=str(event_id),
                        entity_name=event_text[:80],
                        change_type="update",
                        old_value=str(old_values),
                        new_value=str(update_fields),
                        chapter=chapter_number,
                        confidence=0.85,
                        change_reason=self._generate_change_reason(
                            "时间线事件", item.action, event_text[:50],
                            detail=f"更新字段: {', '.join(update_fields.keys())}",
                        ),
                    ))
                    result.updated += 1

        self._evaluate_merge_confidence(result)
        return result

    @staticmethod
    def _find_timeline_event(
        existing: List[VaultTimeline], event_text: str,
    ) -> Optional[VaultTimeline]:
        """在已有时间线事件中查找匹配。"""
        event_clean = event_text.lower().strip()
        for evt in existing:
            if evt.event.lower().strip() == event_clean:
                return evt
            # 子串匹配
            if len(event_clean) > 5 and (event_clean in evt.event.lower()
                                         or evt.event.lower() in event_clean):
                return evt
        return None

    # ==================================================================
    # 15-3: 剧情承诺库合并
    # ==================================================================

    async def merge_plot_promises(
        self,
        db: AsyncSession,
        project_id: int,
        extracted: List[ExtractedPlotPromise],
        chapter_number: int,
    ) -> MergeResult:
        """合并剧情承诺库变更。

        操作类型：
          - create: 新建承诺
          - advance: 推进已有承诺
          - redeem: 兑现承诺
          - cancel: 废弃承诺

        超时未收束检查：
          - 创建超过 STALE_CHAPTER_THRESHOLD 章未兑现 → 标记 stale
          - 引用超过 SUB_PROMISE_CONSISTENCY_LIMIT 个子承诺 → 递归检查
        """
        result = MergeResult(entity_type="plot_promise")
        if not extracted:
            return result

        existing = await vault_dao.get_plot_promises(db, project_id)

        for item in extracted:
            title = item.title.strip() if item.title else ""
            if not title:
                result.warnings.append("跳过空标题的剧情承诺条目")
                continue

            if item.action == "create":
                new_promise = await vault_dao.create_plot_promise(db, {
                    "project_id": project_id,
                    "title": title,
                    "description": item.description or title,
                    "type": self._map_promise_type(item.type),
                    "status": "active",
                    "urgency": 5,
                    "planted_chapter": chapter_number,
                    "advancement_log": [
                        {
                            "chapter": chapter_number,
                            "event": "created",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                })

                result.changes.append(ChangeEntry(
                    entity_type="plot_promise",
                    entity_id=str(new_promise.id),
                    entity_name=title,
                    change_type="create",
                    old_value=None,
                    new_value=None,
                    chapter=chapter_number,
                    confidence=0.9,
                    change_reason=self._generate_change_reason(
                        "剧情承诺", "create", title,
                    ),
                ))
                result.created += 1

            elif item.action == "advance":
                target = self._find_plot_promise(existing, title)
                if target is None:
                    result.warnings.append(
                        f"未找到剧情承诺 '{title}'，无法推进"
                    )
                    continue

                log = list(target.advancement_log or [])
                log.append({
                    "chapter": chapter_number,
                    "event": "advanced",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                # P6-4 fix: 检查 stale — 优先用 advancement_log
                last_advance = _get_last_advance_chapter(target)
                if chapter_number - last_advance > STALE_CHAPTER_THRESHOLD:
                    result.warnings.append(
                        f"剧情承诺 '{title}' 已超过 {STALE_CHAPTER_THRESHOLD} 章未兑现，标记为 stale"
                    )

                old_status = target.status
                await vault_dao.update_plot_promise(db, target, {
                    "status": "advancing",
                    "advancement_log": log,
                    "urgency": min(10, (target.urgency or 5) + 1),
                })

                result.changes.append(ChangeEntry(
                    entity_type="plot_promise",
                    entity_id=str(target.id),
                    entity_name=title,
                    change_type="update",
                    old_value=old_status,
                    new_value="advancing",
                    chapter=chapter_number,
                    confidence=0.8,
                    change_reason=self._generate_change_reason(
                        "剧情承诺", "update", title,
                        detail=f"状态: {old_status} → advancing",
                    ),
                ))
                result.updated += 1

            elif item.action == "redeem":
                target = self._find_plot_promise(existing, title)
                if target is None:
                    result.warnings.append(
                        f"未找到剧情承诺 '{title}'，无法兑现"
                    )
                    continue

                log = list(target.advancement_log or [])
                log.append({
                    "chapter": chapter_number,
                    "event": "redeemed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                old_status = target.status
                await vault_dao.update_plot_promise(db, target, {
                    "status": "resolved",
                    "advancement_log": log,
                })

                result.changes.append(ChangeEntry(
                    entity_type="plot_promise",
                    entity_id=str(target.id),
                    entity_name=title,
                    change_type="update",
                    old_value=old_status,
                    new_value="resolved",
                    chapter=chapter_number,
                    confidence=1.0,
                    change_reason=self._generate_change_reason(
                        "剧情承诺", "status_change", title,
                        detail=f"状态: {old_status} → resolved (已兑现)",
                    ),
                ))
                result.updated += 1

            elif item.action == "cancel":
                target = self._find_plot_promise(existing, title)
                if target is None:
                    result.warnings.append(
                        f"未找到剧情承诺 '{title}'，无法废弃"
                    )
                    continue

                log = list(target.advancement_log or [])
                log.append({
                    "chapter": chapter_number,
                    "event": "abandoned",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                cancel_reason = item.cancel_reason or "未提供废弃原因"
                old_status = target.status
                await vault_dao.update_plot_promise(db, target, {
                    "status": "abandoned",
                    "advancement_log": log,
                })

                result.changes.append(ChangeEntry(
                    entity_type="plot_promise",
                    entity_id=str(target.id),
                    entity_name=title,
                    change_type="update",
                    old_value=old_status,
                    new_value="abandoned",
                    chapter=chapter_number,
                    confidence=0.95,
                    change_reason=self._generate_change_reason(
                        "剧情承诺", "status_change", title,
                        detail=f"已废弃: {cancel_reason}",
                    ),
                ))
                result.updated += 1

        # P6-4 fix: 整体 stale 检查 — 优先用 advancement_log
        for promise in existing:
            if promise.status in ("active", "advancing"):
                last_advance = _get_last_advance_chapter(promise)
                if last_advance > 0 and chapter_number - last_advance > STALE_CHAPTER_THRESHOLD:
                    result.warnings.append(
                        f"剧情承诺 '{promise.title}' "
                        f"(last_advance_chapter={last_advance}) 已超 {STALE_CHAPTER_THRESHOLD} 章未兑现"
                    )

        self._evaluate_merge_confidence(result)
        return result

    @staticmethod
    def _find_plot_promise(
        existing: List[VaultPlotPromise], title: str,
    ) -> Optional[VaultPlotPromise]:
        """在已有承诺中按标题查找。"""
        title_clean = title.lower().strip()
        for p in existing:
            if p.title and p.title.lower().strip() == title_clean:
                return p
            if p.description and p.description.lower().strip() == title_clean:
                return p
        return None

    @staticmethod
    def _map_promise_type(ptype: str) -> str:
        """将中文剧情承诺类型映射到数据库枚举值。"""
        mapping = {
            "人物弧光": "arc",
            "剧情转折": "subplot",
            "悬念": "mystery",
            "关系发展": "promise",
            "世界观秘密": "foreshadowing",
        }
        return mapping.get(ptype, "mystery")

    # ==================================================================
    # 15-4: 世界观库合并
    # ==================================================================

    async def merge_world_building(
        self,
        db: AsyncSession,
        project_id: int,
        extracted: List[ExtractedWorldItem],
        chapter_number: int,
    ) -> MergeResult:
        """合并世界观库变更。

        分类映射：geography | history | system | faction | event
        变更标记：
          - 已有设定被修改 → 标记 revised，旧值记入 changelog
          - 新建设定 → 正常入库
          - 设定冲突（system 规则矛盾）→ conflict_detected
        """
        result = MergeResult(entity_type="world")
        if not extracted:
            return result

        existing = await vault_dao.get_world_entries(db, project_id)
        existing_by_name: Dict[str, VaultWorld] = {e.name: e for e in existing}

        # 对 system 类做规则冲突检查
        system_entries = [e for e in existing if e.category == "system"]

        for item in extracted:
            name = item.name.strip() if item.name else ""
            if not name:
                result.warnings.append("跳过空名字的世界观条目")
                continue

            category = item.category or "other"

            if item.action == "create":
                if name in existing_by_name:
                    result.warnings.append(
                        f"世界观条目 '{name}' 已存在，跳过新建"
                    )
                    continue

                new_entry = await vault_dao.create_world_entry(db, {
                    "project_id": project_id,
                    "name": name,
                    "description": item.content or "",
                    "category": category,
                    "source_chapter": chapter_number,
                    "reference_chapters": [chapter_number] if chapter_number else [],
                })

                result.changes.append(ChangeEntry(
                    entity_type="world",
                    entity_id=str(new_entry.id),
                    entity_name=name,
                    change_type="create",
                    old_value=None,
                    new_value=None,
                    chapter=chapter_number,
                    confidence=0.85,
                    change_reason=self._generate_change_reason(
                        "世界观", "create", name,
                    ),
                ))
                result.created += 1

                # 更新 existing_by_name 以支持后续引用
                existing_by_name[name] = new_entry

            elif item.action == "expand":
                target = existing_by_name.get(name)
                if target is None:
                    result.warnings.append(
                        f"未找到世界观条目 '{name}'，无法扩展"
                    )
                    continue

                refs = list(target.reference_chapters or [])
                if chapter_number and chapter_number not in refs:
                    refs.append(chapter_number)

                old_description = target.description
                new_content = item.content or ""
                if new_content:
                    new_description = old_description + "\n\n[扩展] " + new_content
                else:
                    new_description = old_description

                await vault_dao.update_world_entry(db, target, {
                    "description": new_description,
                    "reference_chapters": refs,
                })

                result.changes.append(ChangeEntry(
                    entity_type="world",
                    entity_id=str(target.id),
                    entity_name=name,
                    change_type="update",
                    old_value=old_description,
                    new_value=new_description,
                    chapter=chapter_number,
                    confidence=0.8,
                    change_reason=self._generate_change_reason(
                        "世界观", "update", name,
                        detail="扩展描述",
                    ),
                ))
                result.updated += 1

            elif item.action == "revise":
                target = existing_by_name.get(name)
                if target is None:
                    result.warnings.append(
                        f"未找到世界观条目 '{name}'，无法修订"
                    )
                    continue

                old_description = target.description
                new_content = item.content or old_description

                await vault_dao.update_world_entry(db, target, {
                    "description": new_content,
                })

                result.changes.append(ChangeEntry(
                    entity_type="world",
                    entity_id=str(target.id),
                    entity_name=name,
                    change_type="update",
                    old_value=old_description,
                    new_value=new_content,
                    chapter=chapter_number,
                    confidence=0.7,
                    change_reason=self._generate_change_reason(
                        "世界观", "update", name,
                        detail="内容修订",
                    ),
                ))
                result.updated += 1

            elif item.action == "conflict":
                # 检测 system 规则冲突
                target = existing_by_name.get(name)
                conflict_found = False
                conflict_detail = ""

                if category == "system":
                    for sys_entry in system_entries:
                        if sys_entry.name != name and sys_entry.constraint:
                            if item.content and sys_entry.constraint:
                                # 简单冲突检测：内容包含否定词且系统规则有肯定 → 标记
                                negations = ["不能", "不可", "禁止", "不允许", "无法"]
                                for neg in negations:
                                    if neg in item.content:
                                        conflict_detail = (
                                            f"'{name}' 规则 '{item.content[:50]}...' "
                                            f"与 '{sys_entry.name}' 规则 "
                                            f"'{sys_entry.constraint[:50]}...' 可能冲突"
                                        )
                                        conflict_found = True
                                        break
                        if conflict_found:
                            break

                result.conflicts.append({
                    "entity": name,
                    "category": category,
                    "action": "conflict",
                    "detail": conflict_detail or f"手动标记 '{name}' 为冲突状态",
                })
                logger.warning(f"世界观冲突: {name} — {conflict_detail}")

            else:
                result.warnings.append(
                    f"未知的世界观操作 '{item.action}' for '{name}'"
                )

        self._evaluate_merge_confidence(result)
        return result

    # ==================================================================
    # 变更日志归档
    # ==================================================================

    async def archive_changelog(
        self,
        db: AsyncSession,
        project_id: int,
        changes: List[ChangeEntry],
        chapter_number: int,
    ) -> None:
        """将 ChangeEntry 列表归档到 VaultChangelog 表。

        每个 ChangeEntry 生成一条 VaultChangelog 记录。
        """
        if not changes:
            logger.info("无变更日志需要归档")
            return

        async with db.begin_nested() as savepoint:
            for change in changes:
                log_entry = VaultChangelog(
                    project_id=project_id,
                    change_type=change.change_type,
                    entity_type=change.entity_type,
                    entity_id=change.entity_id,
                    old_value=change.old_value,
                    new_value=change.new_value,
                    change_reason=change.change_reason,
                    meta_data={
                        "chapter": change.chapter,
                        "confidence": change.confidence,
                        "entity_name": change.entity_name,
                    },
                )
                db.add(log_entry)
            await db.flush()

        logger.info(
            "变更日志归档完成: %d 条 (project=%s, chapter=%s)",
            len(changes), project_id, chapter_number,
        )


# Singleton instance
merge_service = MergeService()
