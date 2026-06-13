"""
墨灵 (Moling) — genre / a3_hooks.py
A3 钩子密度量化

对应文档 §9.4.3
逐章分析钩子的位置、类型和密度，输出钩子密度曲线。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ── 钩子类型与关键词模式 ──
HOOK_PATTERNS: dict[str, tuple[float, list[str]]] = {
    "cliffhanger": (1.0, [
        r'(?:到底|怎么回事|真相|秘密|究竟|难道)',
        r'(?:未完待续|下一章|预知后事|且看下回)',
        r'(?:电话挂断|声音消失|陷入黑暗|一切结束)',
    ]),
    "info_hook": (0.8, [
        r'(?:原来|竟然|发现|认出|身世|真相|其实)',
        r'(?:读者知道|只有.*知道|谁也不知道|没人知道)',
        r'(?:三年前|那场意外|失踪.*年|不知道的事)',
    ]),
    "countdown": (1.2, [
        r'(?:还剩|倒计时|距离.*还有|限.*时间|必须在)',
        r'(?:毒发|爆炸|死期|截止|最后.*机会)',
        r'(?:危险|来不及|快跑|小心|当心|快走)',
    ]),
    "cognitive_twist": (1.5, [
        r'(?:反转|背叛|欺骗|原来如此|竟然是他|真相大白)',
        r'(?:颠覆|大跌眼镜|出乎意料|没想到)',
        r'(?:诱饵|陷阱|圈套|上当|被骗)',
    ]),
}

# 章尾检测（最后 200 字）
_CLOSING_REGION = 200


@dataclass
class ChapterHookResult:
    chapter: int = 0
    total_score: float = 0.0
    hook_density: float = 0.0           # 归一化密度
    hook_count: int = 0
    hook_types: dict[str, int] = field(default_factory=dict)  # 类型计数
    closing_hook: bool = False          # 章尾是否有钩子


@dataclass
class A3Result:
    chapter_hooks: list[ChapterHookResult] = field(default_factory=list)
    density_curve: list[float] = field(default_factory=list)
    avg_density: float = 0.0
    max_density: float = 0.0
    overall_level: str = "low"          # low / medium / high / very_high
    climax_chapters: list[int] = field(default_factory=list)


def A3_quantify_hooks(chapters: list[str]) -> A3Result:
    """
    A3 钩子密度量化主流程。

    输入：小说的前 3 章全文列表
    输出：每章钩子详情 + 全篇统计
    """
    total = len(chapters)
    chapter_results: list[ChapterHookResult] = []

    for ch_idx, text in enumerate(chapters):
        result = _score_chapter(text, ch_idx + 1)
        chapter_results.append(result)

    all_densities = [r.hook_density for r in chapter_results]
    all_scores = [r.total_score for r in chapter_results]
    avg_density = sum(all_densities) / max(len(all_densities), 1)
    max_density = max(all_densities) if all_densities else 0

    # 识别高潮章节（密度 > 平均 × 2）
    threshold = avg_density * 2.0 if avg_density > 0 else 0.5
    climax_chapters = [
        r.chapter for r in chapter_results
        if r.total_score > threshold
    ]

    # 全局等级
    if avg_density < 1.0:
        overall_level = "low"
    elif avg_density < 3.0:
        overall_level = "medium"
    elif avg_density < 6.0:
        overall_level = "high"
    else:
        overall_level = "very_high"

    return A3Result(
        chapter_hooks=chapter_results,
        density_curve=all_densities,
        avg_density=round(avg_density, 4),
        max_density=round(max_density, 4),
        overall_level=overall_level,
        climax_chapters=climax_chapters,
    )


def _score_chapter(text: str, chapter_index: int) -> ChapterHookResult:
    """对单章进行钩子评分"""
    if not text:
        return ChapterHookResult(chapter=chapter_index)

    total_score = 0.0
    hook_count = 0
    hook_types: dict[str, int] = {}
    closing_hook = False

    for hook_type, (weight, patterns) in HOOK_PATTERNS.items():
        for pattern_str in patterns:
            matches = re.findall(pattern_str, text)
            if matches:
                count = len(matches)
                score = weight * count
                total_score += score
                hook_count += count
                hook_types[hook_type] = hook_types.get(hook_type, 0) + count

    # 章尾钩子检测
    closing_text = text[-_CLOSING_REGION:]
    for hook_type, (_, patterns) in HOOK_PATTERNS.items():
        for pattern_str in patterns:
            if re.search(pattern_str, closing_text):
                closing_hook = True
                break
        if closing_hook:
            break

    # 密度 = 总分 / 文本长度 × 1000
    density = round(total_score / max(len(text), 1) * 1000, 4)

    return ChapterHookResult(
        chapter=chapter_index,
        total_score=round(total_score, 2),
        hook_density=density,
        hook_count=hook_count,
        hook_types=hook_types,
        closing_hook=closing_hook,
    )
