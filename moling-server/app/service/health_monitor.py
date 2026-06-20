"""墨灵 (Moling) — 子情节健康监控服务 (§5.3).

纯算法/SQL 实现，零 LLM 成本。检测子情节承诺的健康状况，
生成 R1/R2/R3 告警并支持防疲劳过滤。

Usage:
    result = await health_monitor_service.check_health(
        db, project_id="proj-xxx", current_chapter=15
    )
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Set, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_plot_promise import VaultPlotPromise

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
R1_CHAPTER_WINDOW = 8       # R1: 8 章未推进
R2_MIN_REPEATED = 4         # R2: 最少 4 次同类推进触发
R3_CHAPTER_WINDOW = 10      # R3: 10 章静默
ANTI_FATIGUE_WINDOW = 3     # 防疲劳窗口（同一告警 3 章内不重复）


class HealthMonitorService:
    """子情节健康监控服务。

    对项目中所有活跃/推进中的 VaultPlotPromise 执行三条健康规则检查，
    结果由调用方决定是否持久化到 DynamicLayer.health_check 字段。
    """

    # ================================================================
    # 公开入口
    # ================================================================

    @staticmethod
    async def check_health(
        db: AsyncSession,
        project_id: str,
        current_chapter: int,
    ) -> dict[str, Any]:
        """主入口：执行健康检查并返回结果。

        Args:
            db: SQLAlchemy async session.
            project_id: 项目 ID.
            current_chapter: 当前章节号.

        Returns:
            dict: {
                "checked_at": "第15章",
                "alerts": [
                    {
                        "rule": "R1",
                        "promise_title": "...",
                        "promise_id": 1,
                        "level": "yellow",
                        "detail": "8章未推进"
                    },
                    ...
                ]
            }
        """
        logger.info(
            "check_health called: project=%s, current_chapter=%s",
            project_id, current_chapter,
        )

        try:
            # 1. 获取项目中所有剧情承诺
            promises = await _get_plot_promises(db, project_id)
            if not promises:
                logger.info("No plot promises found for project %s", project_id)
                return _make_result(current_chapter, [])

            # 2. 获取最新章节内容（用于 R3 降级检查）
            current_chapter_content = await _get_chapter_content(
                db, project_id, current_chapter,
            )

            # 3. 获取近几章的已有健康检查结果（用于防疲劳）
            previous_alerts_by_chapter = await _get_previous_health_checks(
                db, project_id, current_chapter,
            )

            # 4. 对每个承诺执行 R1/R2/R3 检测
            alerts: list[dict[str, Any]] = []
            for promise in promises:
                promise_alerts = await _check_promise(
                    promise, current_chapter, current_chapter_content,
                )
                alerts.extend(promise_alerts)

            # 5. 防疲劳过滤
            alerts = _check_anti_fatigue(
                alerts, previous_alerts_by_chapter, current_chapter,
            )

            result = _make_result(current_chapter, alerts)
            logger.info("Health check complete: %d alerts", len(alerts))
            return result

        except Exception:
            logger.exception("check_health failed")
            raise


# ================================================================
# R1 / R2 / R3 检测逻辑
# ================================================================


async def _check_promise(
    promise: VaultPlotPromise,
    current_chapter: int,
    current_chapter_content: Optional[str],
) -> list[dict[str, Any]]:
    """对单个承诺执行 R1 / R2 / R3 检测。

    Args:
        promise: VaultPlotPromise 实例.
        current_chapter: 当前章节号.
        current_chapter_content: 当前章节正文（用于 R3 降级判断）.

    Returns:
        该承诺触发的告警列表.
    """
    alerts: list[dict[str, Any]] = []
    promise_title = promise.title or promise.description[:50]

    # R1: 8 章未推进告警
    r1 = _check_r1(promise, current_chapter, promise_title)
    if r1:
        alerts.append(r1)

    # R2: 4+ 同类型重复推进
    r2 = _check_r2(promise, promise_title)
    if r2:
        alerts.append(r2)

    # R3: 10 章静默 + 降级检查
    r3 = _check_r3(promise, current_chapter, current_chapter_content, promise_title)
    if r3:
        alerts.append(r3)

    return alerts


def _get_last_advance_chapter(promise: VaultPlotPromise) -> int:
    """获取承诺最后一次推进的章节号。

    若有 advancement_log，取最后一条记录的 chapter 值；
    否则用 planted_chapter 兜底。
    """
    if promise.advancement_log and isinstance(promise.advancement_log, list):
        last_entry = promise.advancement_log[-1]
        if isinstance(last_entry, dict):
            return last_entry.get("chapter", 0) or 0
    return promise.planted_chapter or 0


def _check_r1(
    promise: VaultPlotPromise,
    current_chapter: int,
    promise_title: str,
) -> Optional[dict[str, Any]]:
    """R1: 8 章未推进告警（🟡 黄色）。

    活跃/推进中的承诺，最近 8 章内没有任何推进记录。
    """
    if promise.status not in ("active", "advancing"):
        return None

    last_chapter = _get_last_advance_chapter(promise)

    if current_chapter - last_chapter >= R1_CHAPTER_WINDOW:
        return {
            "rule": "R1",
            "promise_title": promise_title,
            "promise_id": str(promise.id),
            "level": "yellow",
            "detail": f"已连续{R1_CHAPTER_WINDOW}章未推进（上次推进: 第{last_chapter}章）",
        }
    return None


def _check_r2(
    promise: VaultPlotPromise,
    promise_title: str,
) -> Optional[dict[str, Any]]:
    """R2: 4+ 同类型重复推进行为（🟠 橙色）。

    承诺 >=4 条推进记录，但所有记录都是同一 event_type。
    含义：子情节在"原地踏步"——比如连续 4 次都是"伏笔"，没有推进。
    """
    log = promise.advancement_log or []
    if not isinstance(log, list):
        return None

    if len(log) < R2_MIN_REPEATED:
        return None

    # 提取所有记录的 event_type，跳过缺失 event_type 的记录
    event_types: Set[str] = set()
    for entry in log:
        if not isinstance(entry, dict):
            continue
        et = entry.get("event_type")
        if et:
            event_types.add(et)

    # 只有一条记录有 event_type 但总记录 >= R2_MIN_REPEATED 还不够，
    # 需要所有 >= R2_MIN_REPEATED 条记录都有相同的 event_type
    if len(event_types) == 1:
        repeated_type = event_types.pop()
        return {
            "rule": "R2",
            "promise_title": promise_title,
            "promise_id": str(promise.id),
            "level": "orange",
            "detail": f"连续{len(log)}次同类推进（{repeated_type}），子情节原地踏步",
        }
    return None


def _check_r3(
    promise: VaultPlotPromise,
    current_chapter: int,
    current_chapter_content: Optional[str],
    promise_title: str,
) -> Optional[dict[str, Any]]:
    """R3: 10 章静默承诺告警（🔴 红色）+ 降级检查。

    超过 10 章既无推进、在最新章节中也无提及。
    降级：如果有关键词提及但无正式推进记录 → 降级为 R1（🟡 黄色）。
    """
    last_chapter = _get_last_advance_chapter(promise)

    if current_chapter - last_chapter < R3_CHAPTER_WINDOW:
        return None

    # 检查最新章节中是否有关键词提及
    mentioned = _is_mentioned_in_chapter(promise, current_chapter_content)

    if mentioned:
        # 降级为 R1
        logger.debug(
            "R3 degraded to R1: promise=%s, current=%s, last=%s",
            promise.id, current_chapter, last_chapter,
        )
        return {
            "rule": "R1",
            "promise_title": promise_title,
            "promise_id": str(promise.id),
            "level": "yellow",
            "detail": (
                f"已连续{R3_CHAPTER_WINDOW}章未推进（上次推进: 第{last_chapter}章），"
                f"但最新章节有关键词提及（降级自 R3）"
            ),
        }

    return {
        "rule": "R3",
        "promise_title": promise_title,
        "promise_id": str(promise.id),
        "level": "red",
        "detail": f"已连续{R3_CHAPTER_WINDOW}章静默，无推进也无关键词提及",
    }


def _is_mentioned_in_chapter(
    promise: VaultPlotPromise,
    chapter_content: Optional[str],
) -> bool:
    """检查承诺的相关关键词是否在章节内容中被提及。

    关键词来源：title, description（前 50 字）, related_characters。

    Args:
        promise: VaultPlotPromise 实例.
        chapter_content: 章节正文.

    Returns:
        True 如果任意关键词被提及.
    """
    if not chapter_content:
        return False

    content_lower = chapter_content.lower()

    # 提取关键词
    keywords: list[str] = []
    if promise.title:
        keywords.append(promise.title)
    if promise.description:
        keywords.append(promise.description[:50])
    if promise.related_characters and isinstance(promise.related_characters, list):
        for char in promise.related_characters:
            if isinstance(char, str) and char.strip():
                keywords.append(char)

    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in content_lower:
            logger.debug("Keyword matched: '%s' in chapter content", kw[:20])
            return True
    return False


# ================================================================
# 防疲劳过滤
# ================================================================


def _check_anti_fatigue(
    alerts: list[dict[str, Any]],
    previous_alerts_by_chapter: dict[int, list[dict[str, Any]]],
    current_chapter: int,
) -> list[dict[str, Any]]:
    """防疲劳过滤：同一承诺的同一规则告警每 3 章最多出现 1 次。

    对于当前生成的每条告警，检查近 3 章内（current-1 ~ current-3）
    是否已有相同的 (promise_id, rule) 告警。若有，则跳过。

    Args:
        alerts: 当前生成的全部告警列表.
        previous_alerts_by_chapter: {chapter_number: [alert, ...]} 历史告警.
        current_chapter: 当前章节号.

    Returns:
        过滤后的告警列表.
    """
    if not alerts:
        return []

    # 构建近 3 章已有的 (promise_id, rule) 集合
    previously_reported: Set[Tuple[str, str]] = set()
    for ch in range(current_chapter - 1, current_chapter - ANTI_FATIGUE_WINDOW - 1, -1):
        chapter_alerts = previous_alerts_by_chapter.get(ch, [])
        for alert in chapter_alerts:
            pid = alert.get("promise_id")
            rule = alert.get("rule")
            if pid and rule:
                previously_reported.add((pid, rule))

    if not previously_reported:
        return alerts

    filtered: list[dict[str, Any]] = []
    suppressed_count = 0
    for alert in alerts:
        key = (alert.get("promise_id"), alert.get("rule"))
        if key in previously_reported:
            suppressed_count += 1
            logger.debug(
                "Anti-fatigue suppressed: promise_id=%s rule=%s",
                key[0], key[1],
            )
        else:
            filtered.append(alert)

    if suppressed_count:
        logger.info("Anti-fatigue suppressed %d alerts", suppressed_count)

    return filtered


# ================================================================
# 数据库查询辅助
# ================================================================


async def _get_plot_promises(
    db: AsyncSession, project_id: str,
) -> list[VaultPlotPromise]:
    """获取项目的所有剧情承诺。"""
    from app.dao import vault_dao as _vault_dao
    return await _vault_dao.get_plot_promises(db, project_id)


async def _get_chapter_content(
    db: AsyncSession,
    project_id: str | int,
    chapter_number: int,
) -> Optional[str]:
    """获取指定章节的正文内容。

    Args:
        db: 数据库会话.
        project_id: 项目 ID.
        chapter_number: 章节号.

    Returns:
        章节正文，如果不存在返回 None.
    """
    from app.dao import chapter_dao

    return await chapter_dao.get_content(db, int(project_id), chapter_number)


async def _get_previous_health_checks(
    db: AsyncSession,
    project_id: str,
    current_chapter: int,
) -> dict[int, list[dict[str, Any]]]:
    """获取近几章 DynamicLayer 中存储的历史健康检查结果。

    用于防疲劳过滤。最多获取过去 ANTI_FATIGUE_WINDOW 章的数据。

    Args:
        db: 数据库会话.
        project_id: 项目 ID.
        current_chapter: 当前章节号.

    Returns:
        {chapter_number: [alert, ...]} 映射.
    """
    if current_chapter <= 1:
        return {}

    start_chapter = max(1, current_chapter - ANTI_FATIGUE_WINDOW)

    from app.dao import dynamic_layer_dao

    rows = await dynamic_layer_dao.get_health_check_history(
        db,
        project_id=int(project_id),
        limit=ANTI_FATIGUE_WINDOW * 5,
        start_chapter=start_chapter,
        end_chapter=current_chapter,
    )

    previous: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        hc = row["health_check"]
        ch = row["chapter_number"]
        if hc and isinstance(hc, dict) and hc.get("alerts"):
            previous[ch] = hc["alerts"]

    return previous


# ================================================================
# 结果构建
# ================================================================


def _make_result(
    current_chapter: int,
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    """构建标准格式的健康检查结果。"""
    return {
        "checked_at": f"第{current_chapter}章",
        "alerts": alerts,
    }


# 单例
health_monitor_service = HealthMonitorService()

# 注册到 ServiceRegistry（打破循环依赖）
from app.core.service_registry import service_registry, HealthMonitorServiceSentinel
service_registry.register(HealthMonitorServiceSentinel, health_monitor_service)
