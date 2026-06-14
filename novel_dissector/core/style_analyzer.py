"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / core / style_analyzer.py
文风指纹分析器
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

从已拆解的 DissectResult 中提取 7 维文风指纹（style fingerprint），
用于生成阶段的风格约束注入。

设计原则
  - Step 1 维度：零外部依赖（纯正则+标准库统计）
  - Step 2 维度：依赖 jieba 分词（词汇偏好、内容分类）
  - 所有维度输出为可序列化的 float 值，便于跨作品迁移

当前实现（Step 1 — 5 维，零依赖）：
  ① 句式复杂度   — 平均句长 + 句长标准差
  ② 对话占比     — 对话段落数 / 总段落数
  ③ 段落节奏     — 段落长度分布（均值/CV/四分位）
  ④ 时态/视角     — 第一/第二/第三人称代词比例
  ⑤ 标点特征     — 感叹号/省略号/问号/逗号密度

待实现（Step 2 — 2 维，需 jieba）：
  ⑥ 词汇偏好     — TF-IDF Top 高频实词
  ⑦ 内容分类比   — 描写/叙事/心理/对话的比例

参考
  - 写作猫卡牌组合算法文档 §9.5 Genre Profile tone 字段扩展
  - stylometric 经典特征集（Burrows' Delta, 句长分布等）
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ────────────────────────────────────────────────────────
# 正则模式
# ────────────────────────────────────────────────────────

# 句子分割：中文句号/问号/感叹号/省略号/分号/冒号 + 换行
_SENTENCE_SPLIT = re.compile(r'[。！？!?…\n]+')

# 人称代词
_PRONOUN_FIRST = re.compile(r'[我我们咱咱们]')
_PRONOUN_SECOND = re.compile(r'[你你们您]')
_PRONOUN_THIRD = re.compile(r'[他她它他们她们它们祂]')

# 标点
_PUNCT_EXCLAMATION = re.compile(r'[！!]')
_PUNCT_ELLIPSIS = re.compile(r'[……]{2,}')
_PUNCT_QUESTION = re.compile(r'[？?]')
_PUNCT_COMMA = re.compile(r'[，,]')

# 心理描写指示词
_PSYCH_INDICATORS = re.compile(
    r'(?:觉得|感到|知道|明白|意识到|忽然|突然|心想|想道|'
    r'寻思|琢磨|回忆|想起|忘记|记得|怀疑|相信|希望|害怕)'
)

# 动作描写指示词
_ACTION_INDICATORS = re.compile(
    r'(?:走|跑|跳|拿|放|推|拉|打|踢|抓|握|举|抬|'
    r'转|看|望|盯|瞪|瞥|扫|瞄|闻|听|说)'
)


# ────────────────────────────────────────────────────────
# 数据模型
# ────────────────────────────────────────────────────────


@dataclass
class StyleFingerprint:
    """
    文风指纹 — 7 维可序列化结构。

    所有值归一化到合理范围，便于跨作品比较和 prompt 注入。
    """
    # ── Step 1 维度（零依赖） ──

    # ① 句式复杂度
    avg_sentence_length: float = 0.0          # 平均句长（字符数）
    sentence_length_std: float = 0.0          # 句长标准差

    # ② 对话占比
    dialogue_ratio: float = 0.0               # 对话段落比例

    # ③ 段落节奏
    avg_paragraph_length: float = 0.0         # 平均段落长度
    para_length_cv: float = 0.0               # 段落长度变异系数（CV）
    para_length_q25: float = 0.0              # 段落长度下四分位
    para_length_q75: float = 0.0              # 段落长度上四分位

    # ④ 时态/视角
    first_person_ratio: float = 0.0           # 第一人称代词比例
    second_person_ratio: float = 0.0          # 第二人称代词比例
    third_person_ratio: float = 0.0           # 第三人称代词比例
    dominant_pov: str = ""                    # dominant POV: "first"/"second"/"third"

    # ⑤ 标点特征
    exclamation_density: float = 0.0          # 感叹号密度（每千字）
    ellipsis_density: float = 0.0             # 省略号密度
    question_density: float = 0.0             # 问号密度
    comma_density: float = 0.0                # 逗号密度

    # ── Step 2 维度（需 jieba，预留） ──
    top_content_words: list[str] = field(default_factory=list)   # ⑥ 高频实词
    description_ratio: float = 0.0            # ⑦ 描写占比
    narrative_ratio: float = 0.0              # ⑦ 叙事占比
    psychological_ratio: float = 0.0          # ⑦ 心理占比

    # ── 元数据 ──
    sample_chars: int = 0                     # 分析样本总字符数
    analyzed_chapters: int = 0                # 分析章节数

    def to_dict(self) -> dict[str, Any]:
        """递归转为普通字典（排除空值 Step 2 字段）。"""
        d = asdict(self)
        # 清理 Step 2 的空值
        if not self.top_content_words:
            d.pop("top_content_words", None)
        if self.description_ratio == 0.0 and self.narrative_ratio == 0.0 and self.psychological_ratio == 0.0:
            for k in ("description_ratio", "narrative_ratio", "psychological_ratio"):
                d.pop(k, None)
        return d

    @classmethod
    def empty(cls) -> "StyleFingerprint":
        return cls()


# ────────────────────────────────────────────────────────
# 分析器
# ────────────────────────────────────────────────────────


def analyze_style(
    text: str,
    chapter_count: int = 0,
) -> StyleFingerprint:
    """
    对整篇文本进行文风分析，返回 StyleFingerprint。

    参数
        text           — 拆解后的全文纯文本（已清洗）
        chapter_count  — 章节数（纯统计用）

    返回
        StyleFingerprint 对象（可序列化为 JSON）
    """
    if not text or not text.strip():
        return StyleFingerprint.empty()

    fp = StyleFingerprint()
    fp.sample_chars = len(text)
    fp.analyzed_chapters = chapter_count

    # ── ① 句式复杂度 ──
    _analyze_sentence_complexity(text, fp)

    # ── ③ 段落节奏 ──
    _analyze_paragraph_rhythm(text, fp)

    # ── ④ 时态/视角 ──
    _analyze_pov(text, fp)

    # ── ⑤ 标点特征 ──
    _analyze_punctuation(text, fp)

    return fp


def analyze_style_from_chapters(
    chapters_texts: list[str],
) -> StyleFingerprint:
    """
    从章节文本列表进行文风分析。

    适用于拆解后的 DissectResult.chapters 输入。
    先统计对话占比（需要段落级数据），再做全文本分析。
    """
    text = "\n\n".join(chapters_texts)
    fp = analyze_style(text, chapter_count=len(chapters_texts))
    return fp


def analyze_style_from_result(
    result,
) -> StyleFingerprint:
    """
    从 DissectResult 对象进行文风分析。

    利用已有的段落级数据（is_dialogue），准确计算对话占比。
    """
    from novel_dissector.models.schemas import DissectResult

    # 拼接全文
    all_texts: list[str] = []
    dialogue_count = 0
    total_paras = 0

    for ch in result.chapters:
        for ch_text in (ch.raw_text,):
            if ch_text:
                all_texts.append(ch_text)
        if ch.paragraphs:
            for p in ch.paragraphs:
                total_paras += 1
                if p.is_dialogue:
                    dialogue_count += 1
        elif ch.raw_text:
            # 使用段落级数据时退回到散装段落
            paras = ch.raw_text.split("\n")
            total_paras += len(paras)

    text = "\n".join(all_texts)
    fp = analyze_style(text, chapter_count=result.chapter_count)
    fp.sample_chars = result.total_word_count

    # 覆盖对话占比（利用已有 is_dialogue 字段，更精确）
    if total_paras > 0:
        fp.dialogue_ratio = round(dialogue_count / total_paras, 4)

    return fp


# ────────────────────────────────────────────────────────
# 内部辅助
# ────────────────────────────────────────────────────────


def _analyze_sentence_complexity(text: str, fp: StyleFingerprint) -> None:
    """计算句式复杂度。"""
    sentences = _SENTENCE_SPLIT.split(text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 1]

    if not sentences:
        return

    lengths = [len(s) for s in sentences]
    n = len(lengths)
    mean = sum(lengths) / n

    variance = sum((x - mean) ** 2 for x in lengths) / n
    std = math.sqrt(variance)

    fp.avg_sentence_length = round(mean, 2)
    fp.sentence_length_std = round(std, 2)


def _analyze_paragraph_rhythm(text: str, fp: StyleFingerprint) -> None:
    """计算段落节奏。"""
    paras = [p.strip() for p in text.split("\n") if p.strip()]

    if not paras:
        return

    lengths = [len(p) for p in paras]
    n = len(lengths)
    lengths_sorted = sorted(lengths)

    mean = sum(lengths) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in lengths) / n)

    fp.avg_paragraph_length = round(mean, 2)
    fp.para_length_cv = round(std / mean, 4) if mean > 0 else 0.0
    fp.para_length_q25 = float(lengths_sorted[n // 4]) if n >= 4 else float(lengths_sorted[0])
    fp.para_length_q75 = float(lengths_sorted[3 * n // 4]) if n >= 4 else float(lengths_sorted[-1])


def _analyze_pov(text: str, fp: StyleFingerprint) -> None:
    """分析时态/视角。"""
    chars = len(text)
    if chars == 0:
        return

    first = len(_PRONOUN_FIRST.findall(text))
    second = len(_PRONOUN_SECOND.findall(text))
    third = len(_PRONOUN_THIRD.findall(text))
    total = first + second + third

    if total == 0:
        return

    fp.first_person_ratio = round(first / total, 4)
    fp.second_person_ratio = round(second / total, 4)
    fp.third_person_ratio = round(third / total, 4)

    if first > second and first > third:
        fp.dominant_pov = "first"
    elif second > first and second > third:
        fp.dominant_pov = "second"
    else:
        fp.dominant_pov = "third"


def _analyze_punctuation(text: str, fp: StyleFingerprint) -> None:
    """分析标点特征。"""
    chars = max(len(text), 1)
    thousand_chars = chars / 1000.0

    fp.exclamation_density = round(len(_PUNCT_EXCLAMATION.findall(text)) / thousand_chars, 4)
    fp.ellipsis_density = round(len(_PUNCT_ELLIPSIS.findall(text)) / thousand_chars, 4)
    fp.question_density = round(len(_PUNCT_QUESTION.findall(text)) / thousand_chars, 4)
    fp.comma_density = round(len(_PUNCT_COMMA.findall(text)) / thousand_chars, 4)


# ── 公开 API ──

__all__ = [
    "StyleFingerprint",
    "analyze_style",
    "analyze_style_from_chapters",
    "analyze_style_from_result",
]
