"""
墨灵 (Moling) — genre / a1_opening.py
A1 黄金三章结构提取

对应后端设计文档 §9.4
检测开篇模式类型（直接冲突/日常引入/倒叙悬疑/设定引入）+ 初期节奏曲线。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── 冲突词（扩展版：覆盖网文常见动作词）──
_HIGH_CONFLICT_WORDS = re.compile(
    r'(?:杀|战|逃|追|危|险|斗|攻|挡|死|灭|毁|'
    r'踹|踢|打|砸|劈|砍|刺|捅|射|爆|轰|'
    r'抓|掐|勒|锁|扣|压|按|扯|撕|咬|'
    r'撞|冲|扑|翻|滚|躲|闪|避)'
)
_DAILY_WORDS = re.compile(r'(?:起床|吃饭|教室|办公室|阳光|清晨|学校|家|食堂|街道)')
_PAST_WORDS = re.compile(r'(?:曾经|当年|那年|三年前|往事|回忆起|想起|记得|那年|过去|从前)')
_DEFINE_PATTERNS = re.compile(r'(?:叫|称|为|名为|所谓|就是|是指)')


@dataclass
class OpeningPattern:
    pattern_type: str = ""      # direct_conflict / daily_life / flashback / world_building
    confidence: float = 0.0


@dataclass 
class A1Result:
    opening_pattern: OpeningPattern = field(default_factory=OpeningPattern)
    rhythm_curve: list[dict] = field(default_factory=list)
    attraction_score: float = 0.0


def A1_analyze_opening(chapters: list[str]) -> A1Result:
    """
    A1 黄金三章结构提取主流程。
    输入：前 3-5 章文本列表
    """
    if not chapters:
        return A1Result()

    ch1_text = chapters[0] if chapters else ""

    # Step 1: 特征提取
    features = _extract_opening_features(ch1_text[:2000])

    # Step 2: 规则评分
    scores = {
        "direct_conflict": _score_direct_conflict(features),
        "daily_life": _score_daily_life(features),
        "flashback": _score_flashback(features),
        "world_building": _score_world_building(features),
    }

    pattern_type = max(scores, key=scores.get)
    confidence = scores[pattern_type]

    # 修正：当直接冲突和倒叙得分接近时，优先冲突（冲突是更强信号）
    conflict_score = scores.get("direct_conflict", 0)
    flashback_score = scores.get("flashback", 0)
    if conflict_score > 0.3 and abs(conflict_score - flashback_score) <= 0.2:
        pattern_type = "direct_conflict"
        confidence = conflict_score

    # Step 3: 初期节奏曲线
    rhythm_points = _compute_initial_rhythm(chapters[:3])

    # Step 4: 吸引力评分
    attraction = _compute_attraction(pattern_type, confidence, rhythm_points)

    return A1Result(
        opening_pattern=OpeningPattern(pattern_type=pattern_type, confidence=round(confidence, 2)),
        rhythm_curve=rhythm_points,
        attraction_score=round(attraction, 2),
    )


def _extract_opening_features(text: str) -> dict[str, Any]:
    """提取开篇特征"""
    sentences = [s for s in re.split(r'[。！？!?\n]+', text) if s.strip()]
    total_sentences = max(len(sentences), 1)

    short_sentences = sum(1 for s in sentences if len(s) <= 15)
    long_sentences = sum(1 for s in sentences if len(s) >= 30)
    action_verbs = len(re.findall(r'(?:杀|战|逃|追|攻|挡|斗|拔|冲|打|踢|拿)', text))
    total_verbs = len(re.findall(r'(?:是|有|在|说|道|来|去|能|会|要|想|做|看|听|走|跑|跳|站|坐|吃|喝|拿|放|打|杀|战|斗)', text))

    proper_nouns = len(re.findall(r'[\u4e00-\u9fff]{2,4}(?:星|界|域|宗|门|派|国|城|山|河|海|大陆)', text))
    total_chars = max(len(text), 1)

    return {
        "text": text,
        "conflict_count": len(_HIGH_CONFLICT_WORDS.findall(text[:500])),
        "daily_count": len(_DAILY_WORDS.findall(text[:500])),
        "past_count": len(_PAST_WORDS.findall(text)),
        "define_count": len(_DEFINE_PATTERNS.findall(text[:300])),
        "proper_noun_density": proper_nouns / total_chars * 100,
        "short_sentence_ratio": short_sentences / total_sentences,
        "long_sentence_ratio": long_sentences / total_sentences,
        "action_verb_ratio": action_verbs / max(total_verbs, 1),
    }


def _score_direct_conflict(f: dict) -> float:
    score = 0.0
    if f["conflict_count"] >= 2: score += 0.4
    if f["action_verb_ratio"] > 0.4: score += 0.3
    if f["short_sentence_ratio"] > 0.6: score += 0.3
    return min(score, 1.0)


def _score_daily_life(f: dict) -> float:
    score = 0.0
    if f["conflict_count"] < 1: score += 0.3
    if f["daily_count"] >= 2: score += 0.4
    if f["long_sentence_ratio"] > 0.4: score += 0.3
    return min(score, 1.0)


def _score_flashback(f: dict) -> float:
    score = 0.0
    if f["past_count"] >= 2: score += 0.5
    if f["conflict_count"] < 2: score += 0.2
    if f["short_sentence_ratio"] > 0.5: score += 0.3
    return min(score, 1.0)


def _score_world_building(f: dict) -> float:
    score = 0.0
    if f["proper_noun_density"] > 15: score += 0.4
    if f["define_count"] >= 3: score += 0.3
    if f["daily_count"] < 2: score += 0.3
    return min(score, 1.0)


def _compute_initial_rhythm(chapters: list[str], window_count: int = 10) -> list[dict]:
    """计算前三章的节奏曲线"""
    points = []
    for ch_idx, chapter in enumerate(chapters):
        chapter_len = len(chapter)
        for w in range(window_count):
            start = (chapter_len * w) // window_count
            end = (chapter_len * (w + 1)) // window_count
            window_text = chapter[start:end]
            wl = max(len(window_text), 1)

            action_count = len(re.findall(r'(?:杀|战|逃|追|攻|挡|斗)', window_text))
            emotion_count = len(re.findall(r'(?:悲|喜|怒|哀|惊|惧|爱|恨)', window_text))
            sentences = [s for s in re.split(r'[。！？!?\n]+', window_text) if s.strip()]
            short_ratio = sum(1 for s in sentences if len(s) <= 15) / max(len(sentences), 1)

            tension = 0.5 * (action_count / wl) + 0.3 * (emotion_count / wl) + 0.2 * short_ratio
            points.append({
                "chapter": ch_idx + 1,
                "relative_pos": round((ch_idx * window_count + w) / (3 * window_count), 4),
                "tension": round(tension, 4),
            })
    return points


def _compute_attraction(pattern_type: str, confidence: float, rhythm: list[dict]) -> float:
    """计算开篇吸引力评分"""
    base = confidence * 0.5
    # 前3个点的平均张力
    if rhythm:
        avg_tension = sum(p["tension"] for p in rhythm[:3]) / min(len(rhythm), 3)
        base += avg_tension * 0.3
    # 结尾有钩子加分
    if rhythm and len(rhythm) > 2 and rhythm[-1]["tension"] > 0.1:
        base += 0.2
    return min(base, 1.0)
