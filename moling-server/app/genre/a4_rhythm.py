"""
墨灵 (Moling) — genre / a4_rhythm.py
A4 节奏曲线拟合

对应文档 §9.4.4 + 后端设计文档 §9.7
利用 A1 的初期节奏和 A3 的密度曲线，拟合全篇叙事节奏画像。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── 动作/情绪词词典 ──
_ACTION_WORDS = re.compile(r'(?:杀|战|逃|追|攻|挡|斗|拔|冲|撞|劈|砍|刺|斩|爆|轰)')
_EMOTION_WORDS = re.compile(r'(?:悲|喜|怒|哀|惊|惧|爱|恨|愁|痛|苦|乐|欢|伤|绝望|希望|感动|愤怒)')


@dataclass
class RhythmPoint:
    chapter: int = 0
    relative_pos: float = 0.0          # 0.0–1.0
    tension: float = 0.0


@dataclass
class RhythmProfile:
    rhythm_type: str = "steady"        # fast_paced / slow_paced / wave / crescendo / diminuendo / steady
    slopes: list[float] = field(default_factory=list)
    inflection_points: list[dict] = field(default_factory=list)
    avg_slope: float = 0.0
    confidence: float = 0.0


@dataclass
class A4Result:
    rhythm_profile: RhythmProfile = field(default_factory=RhythmProfile)
    chapter_count: int = 0
    hook_density: str = ""


def A4_fit_rhythm_curve(
    chapters: list[str],
    hook_density_curve: list[float],
) -> A4Result:
    """
    A4 节奏曲线拟合主流程。

    输入：
      chapters           — 小说章节文本列表
      hook_density_curve — A3 输出的钩子密度曲线

    输出：
      节奏画像：类型 + 分段斜率 + 拐点 + 置信度
    """
    if not chapters:
        return A4Result(chapter_count=0)

    chapter_count = len(chapters)

    # Step 1: 计算前 3 章的张力曲线（A1 补充）
    initial_rhythm = _compute_initial_rhythm(chapters[:3])

    # Step 2: 合并张力数据
    x = [i / max(chapter_count, 1) for i in range(chapter_count)]
    y: list[float] = []

    for i in range(chapter_count):
        if i < len(initial_rhythm):
            y.append(initial_rhythm[i].tension * 2.0)  # 前3章加权 2x
        else:
            idx_in_density = i - len(initial_rhythm)
            if idx_in_density < len(hook_density_curve):
                y.append(hook_density_curve[idx_in_density])
            else:
                y.append(0.0)

    max_y = max(y) if y else 1
    y = [v / max_y for v in y] if max_y > 0 else y

    # Step 3: 分段线性拟合（少章时降级为简单均值模型）
    k_segments = 5
    segment_size = max(chapter_count // k_segments, 1)
    slopes: list[float] = []
    inflection_points: list[dict] = []

    if chapter_count >= 10:
        # 正常模式：分段线性回归
        for j in range(k_segments):
            start = j * segment_size
            end = min((j + 1) * segment_size, chapter_count)
            if end - start < 2:
                continue
            seg_x = x[start:end]
            seg_y = y[start:end]
            n = len(seg_x)
            sum_x = sum(seg_x)
            sum_y = sum(seg_y)
            sum_xy = sum(xi * yi for xi, yi in zip(seg_x, seg_y))
            sum_xx = sum(xi * xi for xi in seg_x)
            denom = n * sum_xx - sum_x * sum_x
            slope = (n * sum_xy - sum_x * sum_y) / max(denom, 0.0001)
            slopes.append(round(slope, 4))
    else:
        # 降级模式：3-9 章 → 简单张力趋势
        # 用前 1/3 vs 后 1/3 的张力均值差 估算整体斜率
        mid = max(chapter_count // 3, 1)
        front_avg = sum(y[:mid]) / mid if y[:mid] else 0
        back_avg = sum(y[-mid:]) / mid if y[-mid:] else 0
        trend = back_avg - front_avg
        slopes = [round(trend, 4)]

    # Step 4: 拐点检测
    for j in range(1, len(slopes)):
        change = abs(slopes[j] - slopes[j - 1])
        if change > 0.3:
            inflection_points.append({
                "segment": j,
                "position": round(j * segment_size / max(chapter_count, 1), 4),
                "slope_change": round(change, 4),
            })

    # Step 5: 节奏类型判定
    avg_slope = sum(slopes) / max(len(slopes), 1)
    max_slope = max(slopes) if slopes else 0
    _ = min(slopes) if slopes else 0
    sign_changes = sum(
        1 for j in range(1, len(slopes))
        if slopes[j] * slopes[j - 1] < 0
    )
    is_monotonic_inc = all(slopes[j] >= slopes[j - 1] for j in range(1, len(slopes)))
    is_monotonic_dec = all(slopes[j] <= slopes[j - 1] for j in range(1, len(slopes)))

    rhythm_type = "steady"
    if avg_slope > 0.3 or max_slope > 0.8:
        rhythm_type = "fast_paced"
    elif avg_slope < 0.1 and max_slope < 0.3:
        rhythm_type = "slow_paced"
    elif sign_changes >= 2:
        rhythm_type = "wave"
    elif is_monotonic_inc and slopes[-1] > 0.3:
        rhythm_type = "crescendo"
    elif is_monotonic_dec and slopes[0] > 0.3:
        rhythm_type = "diminuendo"

    profile = RhythmProfile(
        rhythm_type=rhythm_type,
        slopes=slopes,
        inflection_points=inflection_points,
        avg_slope=round(avg_slope, 4),
        confidence=round(max(0.3, 1.0 - len(inflection_points) * 0.1), 2),
    )

    return A4Result(
        rhythm_profile=profile,
        chapter_count=chapter_count,
    )


def _compute_initial_rhythm(chapters: list[str], window_count: int = 10) -> list[RhythmPoint]:
    """计算前三章的张力曲线"""
    points: list[RhythmPoint] = []

    for ch_idx, chapter in enumerate(chapters):
        chapter_len = len(chapter)
        for w in range(window_count):
            start = (chapter_len * w) // window_count
            end = (chapter_len * (w + 1)) // window_count
            window_text = chapter[start:end]
            wl = max(len(window_text), 1)

            action_count = len(_ACTION_WORDS.findall(window_text))
            emotion_count = len(_EMOTION_WORDS.findall(window_text))
            sentences = [s for s in re.split(r'[。！？!?\n]+', window_text) if s.strip()]
            short_count = sum(1 for s in sentences if len(s) <= 15)
            short_ratio = short_count / max(len(sentences), 1)

            action_density = action_count / wl
            emotion_density = emotion_count / wl
            tension = 0.5 * action_density + 0.3 * emotion_density + 0.2 * short_ratio

            points.append(RhythmPoint(
                chapter=ch_idx + 1,
                relative_pos=round((ch_idx * window_count + w) / (3 * window_count), 4),
                tension=round(tension, 4),
            ))

    return points
