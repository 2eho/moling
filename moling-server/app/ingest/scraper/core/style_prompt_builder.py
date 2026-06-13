"""
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
novel_dissector / core / style_prompt_builder.py
文风 Prompt 注入器
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

将 StyleFingerprint 转译为 LLM 可理解的自然语言风格约束指令，
用于生文时注入 Prompt，确保续写内容与原作文风一致。

两种使用模式：
  1. fingerprint_to_prompt(fp) → 约束指令文本
  2. fingerprint_to_compact(fp) → 紧凑参数表（用于 API 参数传递）

输出格式示例：
  【风格约束】
  - 语体倾向：第三人称全知叙事
  - 句式特征：平均句长 28 字，句式偏长
  - 对话密度：约占 25%，以对话推动情节
  - 段落节奏：段落长度变化大，短段落用于紧张场景
  - 标点风格：感叹号密集，情绪充沛
"""

from __future__ import annotations

from typing import Any, Optional

from app.ingest.scraper.core.style_analyzer import StyleFingerprint


# ────────────────────────────────────────────────────────
# 公开 API
# ────────────────────────────────────────────────────────


def fingerprint_to_prompt(fp: StyleFingerprint | dict[str, Any]) -> str:
    """
    将文风指纹转译为 LLM Prompt 风格约束指令块。

    输入
        fp — StyleFingerprint 对象 或 其 to_dict() 输出

    返回
        可直接插入 Prompt 的自然语言约束段落

    示例
        constraint = fingerprint_to_prompt(result.stats["style_fingerprint"])
        prompt = f"...【风格约束】\\n{constraint}..."
    """
    if isinstance(fp, dict):
        data = fp
    else:
        data = fp.to_dict()

    lines: list[str] = []
    lines.append("【风格约束】")

    # ① 视角
    pov_line = _describe_pov(data)
    if pov_line:
        lines.append(f"- {pov_line}")

    # ② 句式特征
    sentence_line = _describe_sentence(data)
    if sentence_line:
        lines.append(f"- {sentence_line}")

    # ③ 对话密度
    dialogue_line = _describe_dialogue(data)
    if dialogue_line:
        lines.append(f"- {dialogue_line}")

    # ④ 段落节奏
    rhythm_line = _describe_paragraph_rhythm(data)
    if rhythm_line:
        lines.append(f"- {rhythm_line}")

    # ⑤ 标点与情绪
    punct_line = _describe_punctuation(data)
    if punct_line:
        lines.append(f"- {punct_line}")

    # ⑥ 整体概括
    summary = _summarize_style(data)
    if summary:
        lines.append(f"- 整体风格倾向：{summary}")

    return "\n".join(lines)


def fingerprint_to_compact(fp: StyleFingerprint | dict[str, Any]) -> dict[str, Any]:
    """
    将文风指纹转为紧凑参数表，适合 API 参数传递。

    返回的 dict 可直接用于：
      - 项目配置字段存储
      - API 响应的 style_fingerprint 字段
      - 前端展示
    """
    if isinstance(fp, StyleFingerprint):
        d = fp.to_dict()
    else:
        d = dict(fp)

    # 添加可读摘要
    summary_lines: list[str] = []
    pov = _describe_pov(d)
    if pov:
        summary_lines.append(pov)
    sentence = _describe_sentence(d)
    if sentence:
        summary_lines.append(sentence)
    dialogue = _describe_dialogue(d)
    if dialogue:
        summary_lines.append(dialogue)

    d["_summary"] = "；".join(summary_lines)
    return d


# ────────────────────────────────────────────────────────
# 内部描述函数
# ────────────────────────────────────────────────────────


def _describe_pov(data: dict[str, Any]) -> str:
    """视角描述"""
    pov = data.get("dominant_pov", "")
    first = data.get("first_person_ratio", 0)
    third = data.get("third_person_ratio", 0)

    if pov == "first":
        return '第一人称叙事（「我」视角）'
    elif pov == "second":
        return '第二人称叙事（「你」视角）'
    elif pov == "third":
        if third > 0.95:
            return '第三人称全知叙事（纯「他/她」视角）'
        elif first > 0.1:
            return '混合视角（第三人称为主，穿插第一人称）'
        return "第三人称叙事"
    return ""


def _describe_sentence(data: dict[str, Any]) -> str:
    """句式特征描述"""
    avg = data.get("avg_sentence_length", 0)
    std = data.get("sentence_length_std", 0)

    if avg <= 0:
        return ""

    parts = [f"平均句长 {avg:.0f} 字"]

    # 句式长短分类
    if avg >= 35:
        parts.append("句式偏长，多用复杂句")
    elif avg >= 25:
        parts.append("句式适中，长短句交错")
    elif avg >= 15:
        parts.append("句式偏短，节奏明快")
    else:
        parts.append("短句为主，简洁直接")

    # 句长变化
    cv = std / max(avg, 1)
    if cv > 0.6:
        parts.append("句式变化丰富")
    elif cv < 0.3:
        parts.append("句式较为统一")

    return "，".join(parts)


def _describe_dialogue(data: dict[str, Any]) -> str:
    """对话密度描述"""
    ratio = data.get("dialogue_ratio", 0)

    if ratio <= 0:
        return ""

    ratio_pct = ratio * 100

    if ratio_pct >= 50:
        return f"对话密集，对话占比约 {ratio_pct:.0f}%，以对话驱动故事"
    elif ratio_pct >= 30:
        return f"对话占比约 {ratio_pct:.0f}%，对话与叙事并重"
    elif ratio_pct >= 15:
        return f"对话占比约 {ratio_pct:.0f}%，以叙事为主、对话为辅"
    else:
        return f"对话较少（占比约 {ratio_pct:.0f}%），以叙述和描写为主"


def _describe_paragraph_rhythm(data: dict[str, Any]) -> str:
    """段落节奏描述"""
    avg = data.get("avg_paragraph_length", 0)
    cv = data.get("para_length_cv", 0)
    q25 = data.get("para_length_q25", 0)
    q75 = data.get("para_length_q75", 0)

    if avg <= 0:
        return ""

    parts = [f"段落平均长度 {avg:.0f} 字"]

    # 段落长短
    if avg >= 120:
        parts.append("段落偏长，适合铺陈描写")
    elif avg >= 60:
        parts.append("段落适中")
    else:
        parts.append("段落偏短，节奏紧凑")

    # 变化程度
    if cv > 0.8:
        parts.append("段落长度变化大，长短交替营造节奏感")
    elif cv > 0.4:
        parts.append("段落长度有一定变化")
    elif cv < 0.3:
        parts.append("段落长度均匀，风格平稳")

    # 展示分布
    parts.append(f"（下四分位 {q25:.0f} 字，上四分位 {q75:.0f} 字）")

    return "，".join(parts)


def _describe_punctuation(data: dict[str, Any]) -> str:
    """标点与情绪风格描述"""
    excl = data.get("exclamation_density", 0)
    quest = data.get("question_density", 0)
    ellipsis = data.get("ellipsis_density", 0)

    traits: list[str] = []

    if excl > 15:
        traits.append("感叹号密集，情绪充沛")
    elif excl > 5:
        traits.append("感叹号使用适度")
    elif excl < 1:
        traits.append("感叹号极少，情绪内敛")

    if quest > 8:
        traits.append("问句密集，多用疑问/设问")
    elif quest > 2:
        traits.append("问句使用适度")

    if ellipsis > 3:
        traits.append("省略号频繁，留白较多")

    if not traits:
        traits.append("标点使用均衡")

    return "，".join(traits)


def _summarize_style(data: dict[str, Any]) -> str:
    """整体风格概括"""
    traits: list[str] = []

    pov = data.get("dominant_pov", "")
    if pov == "first":
        traits.append("第一人称")
    else:
        traits.append("第三人称")

    avg = data.get("avg_sentence_length", 0)
    if avg > 30:
        traits.append("长句叙事")
    elif avg < 18:
        traits.append("短句快节奏")

    dialog = data.get("dialogue_ratio", 0)
    if dialog > 0.4:
        traits.append("对话驱动")
    elif dialog < 0.1:
        traits.append("叙述主导")

    excl = data.get("exclamation_density", 0)
    if excl > 15:
        traits.append("情绪外放")
    elif excl < 2:
        traits.append("情绪内敛")

    return " · ".join(traits) if traits else "均衡"


__all__ = [
    "fingerprint_to_prompt",
    "fingerprint_to_compact",
]
