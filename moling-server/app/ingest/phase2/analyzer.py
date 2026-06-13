"""
墨灵 (Moling) — Ingest Phase 2 Analyzer (I5-I9)

纯规则/算法分析，无需 LLM 调用：
  - I5: 章节锚点分析（章首钩子、章中转折、章末钩子、动作高潮）
  - I6: 连贯性基线评估（角色连贯性、时间线、情节、文风）
  - I7: 未收束钩子识别（遍历全篇悬念/承诺）
  - I8: 最近变更摘要（新增角色、重大事件）
  - I9: 可行性基线评估（情节密度、散线数、续写信心）
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.ingest.phase2.schemas import (
    ChapterAnchor,
    FeasibilityReport,
    OpenHook,
)


# ════════════════════════════════════════════════════════════════
# I5: Chapter Anchors
# ════════════════════════════════════════════════════════════════


def I5_chapter_anchors(
    chapters: list[dict],
    recent_n: int = 3,
) -> list[ChapterAnchor]:
    """
    I5 章节锚点分析。

    分析最近 N 章的结构锚点：
    - opening_hook: 章首钩子（前 200 字内是否有悬念/冲突）
    - midpoint_turn: 章中转折点
    - closing_cliff: 章末钩子
    - action_peak: 动作高潮位置
    """
    anchors = []
    recent_chapters = chapters[-recent_n:] if len(chapters) >= recent_n else chapters

    for ch in recent_chapters:
        content = _get_chapter_text(ch)
        char_count = len(content)

        # 章首钩子
        opening = content[:min(200, char_count)]
        opening_hook = bool(re.search(
            r"(?:突然|竟然|做梦也没想到|一声|就在这时|意想不到|诡异|奇怪)",
            opening,
        ))

        # 章中转折点
        mid_start = char_count // 3
        mid_end = char_count * 2 // 3
        mid = content[mid_start:mid_end] if mid_end > mid_start else ""
        midpoint_turn = _detect_turn(mid)

        # 章末钩子
        closing = content[-min(200, char_count):]
        closing_cliff = _detect_cliffhanger(closing)

        # 动作高潮位置
        action_peak = _detect_action_peak(content)

        anchors.append(ChapterAnchor(
            chapter_index=ch.get("index", 0),
            chapter_title=ch.get("title", ""),
            opening_hook=opening_hook,
            midpoint_turn=midpoint_turn,
            closing_cliff=closing_cliff,
            action_peak=action_peak,
        ))

    return anchors


def _detect_turn(text: str) -> Optional[dict]:
    """检测章节中是否有情节转向。"""
    turn_signals = [
        (r"但(?:是|却|他没想到)", "but"),
        (r"然而", "however"),
        (r"突然", "suddenly"),
        (r"转折", "twist"),
        (r"就在这时", "at_that_moment"),
        (r"命运(?:的)?转折", "fate_twist"),
    ]
    for pattern, name in turn_signals:
        match = re.search(pattern, text)
        if match:
            pos = match.start() / max(len(text), 1)
            return {"trigger": match.group(), "type": name, "position": round(pos, 4)}
    return None


def _detect_cliffhanger(text: str) -> bool:
    """检测章末是否有悬念。"""
    cliff_signals = [
        r"未完待续", r"预知后事", r"且听下回",
        r"到底(?:是|会|要|能)", r"就在这时",
        r"突然", r"一个声音(?:响|传)起",
        r"究竟", r"没想到", r"谁能想到",
    ]
    return any(re.search(s, text) for s in cliff_signals)


def _detect_action_peak(content: str) -> Optional[float]:
    """检测动作/冲突最密集的位置（相对位置 0.0-1.0）。"""
    if not content:
        return None

    action_signals = re.finditer(
        r"(?:战斗|厮杀|对决|爆发|碰撞|攻击|防御|闪避|冲刺|怒吼)",
        content,
    )
    positions = [m.start() / max(len(content), 1) for m in action_signals]
    if not positions:
        return None

    # 返回信号最密集的区域的中位位置
    from statistics import median
    return round(median(positions), 4)


# ════════════════════════════════════════════════════════════════
# I6: Coherence Baseline
# ════════════════════════════════════════════════════════════════


def I6_coherence_baseline(
    chapters: list[dict],
    recent_n: int = 3,
) -> dict:
    """
    I6 连贯性基线评估。

    评估最近 N 章与已有内容的连贯性：
    - character_coherence: 角色出场是否与设定一致
    - plot_coherence: 情节是否自然推进
    - style_coherence: 文风是否突变
    """
    if len(chapters) <= recent_n:
        return {
            "character_coherence": 1.0,
            "plot_coherence": 1.0,
            "style_coherence": 1.0,
            "overall": 1.0,
            "status": "new_work",
        }

    recent_chapters = chapters[-recent_n:]
    previous_chapters = chapters[:-recent_n]

    # 角色连贯性
    recent_chars = _extract_names_set("\n".join(_get_chapter_text(c) for c in recent_chapters))
    prev_chars = _extract_names_set(
        "\n".join(_get_chapter_text(c) for c in previous_chapters[-10:])
    )
    if prev_chars:
        overlap = len(recent_chars & prev_chars) / max(len(recent_chars | prev_chars), 1)
        char_coherence = round(overlap, 4)
    else:
        char_coherence = 1.0

    # 情节连贯性：检查近章中有无与之前矛盾的事件
    plot_coherence = _evaluate_plot_coherence(recent_chapters, previous_chapters)

    # 文风连贯性：词频分布对比
    style_coherence = _evaluate_style_coherence(recent_chapters, previous_chapters)

    overall = round(
        0.40 * char_coherence +
        0.35 * plot_coherence +
        0.25 * style_coherence,
        4,
    )

    return {
        "character_coherence": char_coherence,
        "plot_coherence": round(plot_coherence, 4),
        "style_coherence": round(style_coherence, 4),
        "overall": overall,
        "status": "coherent" if overall >= 0.6 else "potential_issues",
    }


def _extract_names_set(text: str) -> set[str]:
    """从文本中提取可能的人物名字（2-4字中文）。"""
    # 使用简单的启发式规则
    names = set()
    # 寻找"说/道/问"前面的2-4字词语
    for match in re.finditer(r"([\u4e00-\u9fff]{2,4})(?:说|道|问|答|喊|叫)", text):
        names.add(match.group(1))
    return names


def _evaluate_plot_coherence(
    recent: list[dict],
    previous: list[dict],
) -> float:
    """评估情节连贯性。"""
    # 检查是否有时间/地点矛盾的标记
    contradiction_patterns = [
        r"前文说过", r"前面提到", r"之前不是",
        r"矛盾", r"不一致",
    ]
    recent_text = "\n".join(_get_chapter_text(c) for c in recent)
    contradictions = sum(
        1 for p in contradiction_patterns if re.search(p, recent_text)
    )
    if contradictions > 0:
        return max(0.0, 1.0 - contradictions * 0.2)
    return 1.0


def _evaluate_style_coherence(
    recent: list[dict],
    previous: list[dict],
) -> float:
    """评估文风连贯性（基于常见词分布）。"""
    recent_text = "\n".join(_get_chapter_text(c) for c in recent)
    prev_text = "\n".join(_get_chapter_text(c) for c in previous[-5:])

    if not prev_text or not recent_text:
        return 1.0

    # 对比标点使用分布
    def get_punct_dist(text: str) -> dict[str, float]:
        total = max(len(text), 1)
        puncts = {
            "，": text.count("，"),
            "。": text.count("。"),
            "？": text.count("？"),
            "！": text.count("！"),
            "：": text.count("："),
            "；": text.count("；"),
            "……": text.count("……") / 2,  # 每个……算半个
            "——": text.count("——") / 2,
        }
        return {k: v / total for k, v in puncts.items()}

    recent_dist = get_punct_dist(recent_text)
    prev_dist = get_punct_dist(prev_text)

    # 计算 JS 散度简化版（余弦相似度）
    all_keys = set(recent_dist.keys()) | set(prev_dist.keys())
    dot_product = sum(recent_dist.get(k, 0) * prev_dist.get(k, 0) for k in all_keys)
    norm_recent = sum(v ** 2 for v in recent_dist.values()) ** 0.5
    norm_prev = sum(v ** 2 for v in prev_dist.values()) ** 0.5

    if norm_recent == 0 or norm_prev == 0:
        return 1.0

    cosine = dot_product / (norm_recent * norm_prev)
    return round(max(0.5, min(1.0, cosine)), 4)


# ════════════════════════════════════════════════════════════════
# I7: Open Hooks Detection
# ════════════════════════════════════════════════════════════════


def I7_open_hooks(
    chapters: list[dict],
    recent_n: int = 3,
) -> list[OpenHook]:
    """
    I7 未收束钩子识别。

    遍历全篇中出现的悬念/承诺/伏笔，检查在最近 N 章中是否被收束。
    返回未收束的钩子列表。
    """
    all_hooks: list[OpenHook] = []

    # 从前文部分提取所有钩子
    previous_chapters = chapters[:-recent_n] if len(chapters) > recent_n else []
    for ch in previous_chapters:
        ch_hooks = _extract_hooks_from_chapter(ch)
        all_hooks.extend(ch_hooks)

    # 最近文本（用于检查是否已收束）
    recent_chapters = chapters[-recent_n:] if len(chapters) >= recent_n else chapters
    recent_text = "\n".join(_get_chapter_text(c) for c in recent_chapters)

    # 检查每个钩子是否已被收束
    open_hooks = []
    total_chapters = len(chapters)
    for hook in all_hooks:
        if not _is_hook_resolved(hook, recent_text):
            age = total_chapters - hook.chapter_index
            open_hooks.append(OpenHook(
                type=hook.type,
                text=hook.text,
                context=hook.context,
                chapter_index=hook.chapter_index,
                created_at=hook.created_at,
                age_in_chapters=age,
                stale=age > 20,
            ))

    # 按过期程度排序（最老的优先）
    return sorted(open_hooks, key=lambda h: -h.age_in_chapters)


def _extract_hooks_from_chapter(chapter: dict) -> list[OpenHook]:
    """从单章中提取悬念/承诺。"""
    content = _get_chapter_text(chapter)
    hooks = []
    ch_index = chapter.get("index", 0)
    ch_title = chapter.get("title", "")

    # 疑问式悬念
    for match in re.finditer(r"(?:到底|为什么|难道|怎么(?:回事|可能|会这样))", content):
        ctx_start = max(0, match.start() - 30)
        ctx_end = min(len(content), match.end() + 30)
        hooks.append(OpenHook(
            type="mystery",
            text=content[max(0, match.start()-10):match.end()+10],
            context=content[ctx_start:ctx_end],
            chapter_index=ch_index,
            created_at=f"第{ch_index+1}章 {ch_title}",
        ))

    # 承诺式悬念
    for match in re.finditer(r"(?:一定(?:会|要|回来|找到)|答应你|等我|保证|发誓)", content):
        ctx_start = max(0, match.start() - 30)
        ctx_end = min(len(content), match.end() + 30)
        hooks.append(OpenHook(
            type="promise",
            text=content[max(0, match.start()-10):match.end()+10],
            context=content[ctx_start:ctx_end],
            chapter_index=ch_index,
            created_at=f"第{ch_index+1}章 {ch_title}",
        ))

    return hooks


def _is_hook_resolved(hook: OpenHook, recent_text: str) -> bool:
    """检查钩子是否已被收束。"""
    resolution_keywords = {
        "到底": ["原来", "真相是", "结果是", "终于", "最终"],
        "为什么": ["因为", "原因是", "原来"],
        "一定": ["做到了", "实现了", "完成了", "回来了", "成功了"],
        "难道": ["原来", "果然", "确实"],
    }

    for trigger, resolutions in resolution_keywords.items():
        if trigger in hook.text:
            return any(r in recent_text for r in resolutions)
    return False


# ════════════════════════════════════════════════════════════════
# I8: Recent Changes Summary
# ════════════════════════════════════════════════════════════════


def I8_recent_changes(
    chapters: list[dict],
    recent_n: int = 3,
) -> list[str]:
    """
    I8 最近变更摘要。

    输出最近 N 章的关键变更点列表：
    - 新增角色
    - 重大事件
    - 场景切换
    - 关系变化
    """
    if len(chapters) <= recent_n:
        return ["作品导入，全新分析"]

    recent = chapters[-recent_n:]
    previous = chapters[:-recent_n]

    changes: list[str] = []
    recent_prev_text = "\n".join(_get_chapter_text(c) for c in previous[-10:])

    for ch in recent:
        content = _get_chapter_text(ch)
        ch_index = ch.get("index", 0)
        ch_title = ch.get("title", f"第{ch_index+1}章")

        # 新增角色
        current_chars = _extract_names_set(content)
        prev_chars = _extract_names_set(recent_prev_text)
        new_chars = current_chars - prev_chars
        for char in list(new_chars)[:3]:  # 最多3个
            changes.append(f"【新角色】{char} 在第 {ch_index+1} 章「{ch_title}」中出现")

        # 重大事件
        for para in content.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if re.search(r"(?:终于|竟然|突然|最后|关键时刻|没想到|原来如此)", para):
                changes.append(
                    f"【事件】第 {ch_index+1} 章：{para[:50]}..."
                )
                break  # 每章最多一个事件

    return changes[:15]  # 限制数量


# ════════════════════════════════════════════════════════════════
# I9: Feasibility Check
# ════════════════════════════════════════════════════════════════


def I9_feasibility_check(
    chapters: list[dict],
    recent_n: int = 3,
    open_hooks: Optional[list[OpenHook]] = None,
    coherence: Optional[dict] = None,
) -> FeasibilityReport:
    """
    I9 可行性基线评估。

    评估文章续写的可行性。
    """
    if not chapters:
        return FeasibilityReport(
            continuation_confidence=0.0,
            recommendation="无可用章节数据",
        )

    recent_chapters = chapters[-recent_n:] if len(chapters) >= recent_n else chapters
    total_chars = sum(len(_get_chapter_text(c)) for c in recent_chapters)

    # 情节密度
    event_count = sum(
        len(re.findall(r"(?:终于|突然|最后|发现|原来|竟然)", _get_chapter_text(ch)))
        for ch in recent_chapters
    )
    plot_density = event_count / max(total_chars / 1000, 1)

    # 散线数量
    thread_count = len(open_hooks) if open_hooks else 0

    # 续写信心分
    coherence_overall = coherence.get("overall", 0.5) if coherence else 0.5
    continuation_confidence = round(
        0.5 * min(plot_density / 5.0, 1.0) -   # 情节密度高加分
        0.3 * min(thread_count / 10.0, 1.0) +  # 散线多扣分
        0.2 * coherence_overall,                 # 连贯性加分
        4,
    )
    continuation_confidence = max(0.0, min(1.0, continuation_confidence))

    # 建议
    if continuation_confidence < 0.3:
        recommendation = "建议先收束部分伏笔后再续写"
    elif continuation_confidence < 0.6:
        recommendation = "可以续写，建议注意主线集中度"
    else:
        recommendation = "续写可行性良好"

    return FeasibilityReport(
        plot_density=round(plot_density, 2),
        loose_thread_count=thread_count,
        continuation_confidence=continuation_confidence,
        coherence=coherence or {},
        recommendation=recommendation,
    )


# ════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════


def _get_chapter_text(chapter: dict) -> str:
    """从章节 dict 中获取纯文本内容。"""
    raw_text = chapter.get("raw_text", "")
    if raw_text:
        return raw_text

    paragraphs = chapter.get("paragraphs", [])
    if paragraphs:
        return "\n".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in paragraphs
        )

    # 尝试其他字段
    return chapter.get("content", "")
