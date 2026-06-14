"""
墨灵 (Moling) — Book Analysis Service.

提供创作项目的分析工具：
- 角色提取与关系映射
- 情节结构分析
- 写作风格检测

所有方法均为同步，便于 Celery Worker 直接调用（无需 await）。
使用 app.dependencies 中的同步数据库引擎以避免 Windows greenlet 问题。
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.dao import chapter_dao

logger = logging.getLogger(__name__)

# --- 正则常量 ---

# 中文人名：2~3 个汉字（常见姓氏+名字）
_CHINESE_NAME_RE = re.compile(r"[\u4e00-\u9fff]{2,3}")

# 英文专有名词：首字母大写的单词或短语（2 词以内）
_ENGLISH_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b")

# 对话引导词（用于粗估对话比例）
_DIALOGUE_END_RE = re.compile(r'["""」』\u201d]')

# 句末标点
_SENTENCE_END_RE = re.compile(r"[。！？.!?\u3002\uff01\uff1f]")

# 常用词/停用词（中文小说常见虚词，过滤角色误匹配）
_STOP_NAMES: set[str] = {
    "但是", "因为", "如果", "虽然", "而且", "然后", "可以", "没有",
    "那个", "这个", "什么", "怎么", "还是", "只是", "不是", "就是",
    "一个", "我们", "他们", "你们", "自己", "知道", "看见", "听到",
    "出来", "起来", "过来", "回去", "进来", "出去", "开始", "继续",
    "突然", "终于", "然后", "那么", "这样", "那样", "先生", "小姐",
    "时候", "地方", "东西", "已经", "还是", "因为", "所以", "虽然",
    "但是", "如果", "觉得", "以为", "以为", "不过", "恐怕", "难道",
    "可能", "应该", "能够", "愿意", "必须", "需要", "可以", "希望",
    "想法", "主意", "办法", "问题", "情况", "消息", "事情", "原因",
    "结果", "过程", "经过", "关系", "目的", "意义", "目的", "This",
    "That", "What", "When", "Where", "Which", "Who", "How", "The",
}


class BookAnalysisService:
    """书籍分析服务。

    提供三种分析能力：
    1. analyze_characters — 角色提取及其关系图谱
    2. analyze_plot — 情节结构与漏洞检测
    3. detect_style — 写作风格量化分析
    """

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def analyze_characters(self, project_id: int) -> dict:
        """分析项目中的角色信息。

        逐章扫描正文，提取中英文角色名；统计各角色在全书中出现的
        章节分布、首次出现章节、共现关系，并生成简要档案描述。

        Args:
            project_id: 项目 ID

        Returns:
            dict: {
                "project_id": int,
                "characters": [
                    {
                        "name": str,            # 角色名
                        "mentions": int,        # 总提及次数
                        "first_chapter": int,   # 首次出现的章节号
                        "associated_with": [...],  # 共现角色列表
                        "profile": str,         # 简要档案描述
                    },
                ],
                "total_chapters": int,
            }
        """
        chapters = self._get_chapters_sync(project_id)
        if not chapters:
            logger.info("Project %s has no chapters, returning empty result", project_id)
            return {
                "project_id": project_id,
                "characters": [],
                "total_chapters": 0,
            }

        # ---- Step 1: 提取各章节角色提及 ----
        # chapter_characters: dict[chapter_number, Counter[name -> count]]
        chapter_characters: Dict[int, Counter[str]] = {}
        # all_mentions: name -> total count
        all_mentions: Counter[str] = Counter()
        # first_chapter: name -> chapter number
        first_chapter: Dict[str, int] = {}

        for ch in chapters:
            content = ch.content or ""
            cn_num = ch.chapter_number

            names = self._extract_names(content)
            if not names:
                continue

            # 过滤停用词
            filtered = [n for n in names if n not in _STOP_NAMES and len(n.strip()) >= 2]

            if filtered:
                cnt = Counter(filtered)
                chapter_characters[cn_num] = cnt
                all_mentions.update(cnt)

                for name in filtered:
                    if name not in first_chapter:
                        first_chapter[name] = cn_num

        # ---- Step 2: 构建共现关系 ----
        # co_occur: name -> Counter[other_name]
        co_occur: Dict[str, Counter[str]] = defaultdict(Counter)
        for ch_num, char_counter in chapter_characters.items():
            names_in_chapter = list(char_counter.keys())
            for i, name_a in enumerate(names_in_chapter):
                for name_b in names_in_chapter[i + 1:]:
                    co_occur[name_a][name_b] += 1
                    co_occur[name_b][name_a] += 1

        # ---- Step 3: 按总提及次数降序排列 ----
        sorted_names = sorted(all_mentions.keys(), key=lambda n: all_mentions[n], reverse=True)

        characters = []
        for name in sorted_names:
            total = all_mentions[name]
            fc = first_chapter.get(name, 0)
            # 共现角色按共现次数降序排列，取前 10
            associated = [
                {"name": other, "co_occurrences": count}
                for other, count in co_occur.get(name, Counter()).most_common(10)
            ]

            # 简单档案：提及次数、首次出现章节、共现角色数量
            aux_info = []
            if fc:
                aux_info.append(f"首次出现于第{fc}章")
            if associated:
                top_assoc = associated[0]["name"]
                aux_info.append(f"常与「{top_assoc}」同场出现")
            profile = f"全书提及{total}次。" + "；".join(aux_info) if aux_info else f"全书提及{total}次。"

            characters.append({
                "name": name,
                "mentions": total,
                "first_chapter": fc,
                "associated_with": associated,
                "profile": profile,
            })

        logger.info(
            "Character analysis complete for project %s: %d characters found",
            project_id, len(characters),
        )

        return {
            "project_id": project_id,
            "characters": characters,
            "total_chapters": len(chapters),
        }

    def analyze_plot(self, project_id: int) -> dict:
        """分析项目的情节结构。

        扫描各章节内容，识别情节结构标志（章节过渡、语气变化），
        检测潜在的情节漏洞（未解决的线索/承诺）。

        Args:
            project_id: 项目 ID

        Returns:
            dict: {
                "project_id": int,
                "structure": {
                    "act_count": int,        # 推测的幕数
                    "pacing": [...],         # 各章节节奏评分
                    "climax_chapter": int | None,  # 推测的高潮章节
                },
                "plot_points": [...],       # 识别到的情节点
                "potential_gaps": [...],    # 潜在的情节漏洞
            }
        """
        chapters = self._get_chapters_sync(project_id)
        if not chapters:
            return {
                "project_id": project_id,
                "structure": {"act_count": 0, "pacing": [], "climax_chapter": None},
                "plot_points": [],
                "potential_gaps": [],
            }

        # ---- Step 1: 逐章分析 ----
        chapter_metrics: List[dict] = []
        for ch in chapters:
            content = ch.content or ""
            metrics = self._analyze_chapter_metrics(content)
            metrics["chapter_number"] = ch.chapter_number
            metrics["title"] = ch.title or ""
            chapter_metrics.append(metrics)

        # ---- Step 2: 推测幕结构 ----
        act_count, _ = self._detect_acts(chapter_metrics)
        # 高潮章节 = 综合评分（字数+情感波动最大）的章节
        climax = self._find_climax(chapter_metrics)

        # ---- Step 3: 构建节奏数据 ----
        pacing = []
        for m in chapter_metrics:
            pacing.append({
                "chapter": m["chapter_number"],
                "title": m["title"],
                "word_count": m["word_count"],
                "sentence_count": m["sentence_count"],
                "dialogue_ratio": m["dialogue_ratio"],
                "action_intensity": m["action_intensity"],
                "tone_score": m["tone_score"],
            })

        # ---- Step 4: 情节点识别 ----
        plot_points = self._detect_plot_points(chapter_metrics)

        # ---- Step 5: 潜在情节漏洞检测 ----
        potential_gaps = self._detect_plot_gaps(chapter_metrics, chapters)

        logger.info(
            "Plot analysis complete for project %s: %d acts, climax at ch.%s",
            project_id, act_count, climax,
        )

        return {
            "project_id": project_id,
            "structure": {
                "act_count": act_count,
                "pacing": pacing,
                "climax_chapter": climax,
            },
            "plot_points": plot_points,
            "potential_gaps": potential_gaps,
        }

    def detect_style(self, project_id: int) -> dict:
        """检测项目的写作风格。

        计算各章节的平均句长、对话比例、段落长度模式，
        并识别常见重复短语。

        Args:
            project_id: 项目 ID

        Returns:
            dict: {
                "project_id": int,
                "style_profile": {
                    "avg_sentence_length": float,   # 全项目平均句长（字）
                    "dialogue_ratio": float,        # 对话占比（0~1）
                    "paragraph_pattern": str,       # 段落长度模式描述
                    "common_phrases": [...],        # 高频短语列表
                },
            }
        """
        chapters = self._get_chapters_sync(project_id)
        if not chapters:
            return {
                "project_id": project_id,
                "style_profile": {
                    "avg_sentence_length": 0.0,
                    "dialogue_ratio": 0.0,
                    "paragraph_pattern": "无内容",
                    "common_phrases": [],
                },
            }

        # ---- Step 1: 汇总各章指标 ----
        total_sentences = 0
        total_chars = 0
        total_dialogue_chars = 0
        paragraph_lengths: List[int] = []
        all_text_parts: List[str] = []

        for ch in chapters:
            content = ch.content or ""

            # 句长
            sentences = _SENTENCE_END_RE.split(content)
            sentences = [s.strip() for s in sentences if s.strip()]
            sent_count = len(sentences)
            char_count = len(content.replace(" ", "").replace("\n", "").replace("\r", ""))

            total_sentences += sent_count
            total_chars += char_count

            # 对话字符数
            # 简单策略：统计引号内的字符比例
            dialogue_chars = self._count_dialogue_chars(content)
            total_dialogue_chars += dialogue_chars

            # 段落长度
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            paragraph_lengths.extend(len(p) for p in paragraphs)

            # 收集正文文本（去掉对话）供短语分析
            non_dialogue = _DIALOGUE_END_RE.sub("", content)
            all_text_parts.append(non_dialogue)

        # ---- Step 2: 计算全项目指标 ----
        avg_sentence_length = total_chars / max(total_sentences, 1)
        dialogue_ratio = total_dialogue_chars / max(total_chars, 1)

        # ---- Step 3: 段落模式 ----
        paragraph_pattern = self._describe_paragraph_lengths(paragraph_lengths)

        # ---- Step 4: 常见短语 ----
        common_phrases = self._find_common_phrases(all_text_parts)

        logger.info(
            "Style analysis complete for project %s: avg_len=%.1f, dialogue=%.1f%%",
            project_id, avg_sentence_length, dialogue_ratio * 100,
        )

        return {
            "project_id": project_id,
            "style_profile": {
                "avg_sentence_length": round(avg_sentence_length, 2),
                "dialogue_ratio": round(dialogue_ratio, 4),
                "paragraph_pattern": paragraph_pattern,
                "common_phrases": common_phrases,
            },
        }

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_chapters_sync(project_id: int) -> list:
        """同步获取项目所有章节（按章节号升序）。

        通过 ``asyncio.run()`` 桥接异步 DAO，适用于 Celery Worker 等同步环境。
        """
        from app.dependencies import async_session_factory

        async def _fetch() -> list:
            async with async_session_factory() as db:
                chapters = await chapter_dao.get_by_project(
                    db, project_id, skip=0, limit=9999,
                )
                return list(chapters)

        return asyncio.run(_fetch())

    @staticmethod
    def _extract_names(text: str) -> List[str]:
        """从文本中提取可能的人名（中文 + 英文）。"""
        if not text:
            return []
        names: List[str] = []
        # 中文候选
        for match in _CHINESE_NAME_RE.finditer(text):
            names.append(match.group())
        # 英文候选
        for match in _ENGLISH_NAME_RE.finditer(text):
            names.append(match.group())
        return names

    @staticmethod
    def _count_dialogue_chars(text: str) -> int:
        """粗略统计文本中的对话字符数。

        使用引号（中文双引号/单引号/英文双引号）作为对话标识。
        """
        in_dialogue = False
        count = 0
        for ch in text:
            if ch in ('"', '\u201c', '\u201d', '\u300c', '\u300d', '\uff07'):
                in_dialogue = not in_dialogue
            elif in_dialogue:
                count += 1
        return count

    @staticmethod
    def _detect_acts(metrics: List[dict]) -> Tuple[int, List[int]]:
        """根据章节指标推测幕结构。

        使用对话比例和动作强度的梯度变化来识别幕边界。
        幕边界 = 对话比例 + 动作强度同时出现显著变化的章节。

        Returns:
            (act_count, act_boundary_chapters)
        """
        if len(metrics) < 3:
            return 1, []

        boundaries = []
        for i in range(1, len(metrics)):
            prev = metrics[i - 1]
            curr = metrics[i]
            # 计算变化幅度
            dr_delta = abs(curr["dialogue_ratio"] - prev["dialogue_ratio"])
            ai_delta = abs(curr["action_intensity"] - prev["action_intensity"])
            tone_delta = abs(curr["tone_score"] - prev["tone_score"])
            # 如果多个指标同时显著变化，认为是幕边界
            if dr_delta > 0.15 and ai_delta > 0.15:
                boundaries.append(curr["chapter_number"])
            elif tone_delta > 0.3 and (dr_delta > 0.1 or ai_delta > 0.1):
                boundaries.append(curr["chapter_number"])

        act_count = len(boundaries) + 1
        return act_count, boundaries

    @staticmethod
    def _find_climax(metrics: List[dict]) -> Optional[int]:
        """找到最可能的高潮章节。

        高潮章节 = 字数 + 动作强度 + 情感波动（句数）综合得分最高的章节。
        """
        if not metrics:
            return None

        # 归一化后加权评分
        word_counts = [m["word_count"] for m in metrics]
        intensities = [m["action_intensity"] for m in metrics]
        sentence_counts = [m["sentence_count"] for m in metrics]

        max_wc = max(word_counts) if word_counts else 1
        max_int = max(intensities) if intensities else 1
        max_sc = max(sentence_counts) if sentence_counts else 1

        best_score = -1.0
        best_chapter = None

        for m in metrics:
            score = (
                (m["word_count"] / max_wc) * 0.3
                + (m["action_intensity"] / max_int) * 0.4
                + (m["sentence_count"] / max_sc) * 0.3
            )
            if score > best_score:
                best_score = score
                best_chapter = m["chapter_number"]

        return best_chapter

    @staticmethod
    def _analyze_chapter_metrics(content: str) -> dict:
        """分析单个章节的量化指标。"""
        sentences = _SENTENCE_END_RE.split(content)
        sentences = [s.strip() for s in sentences if s.strip()]
        sent_count = len(sentences)

        word_count = len(content.replace(" ", "").replace("\n", "").replace("\r", ""))

        # 对话句数比例
        dialogue_sentences = sum(1 for s in sentences if '"' in s or '\u201c' in s or '\u300c' in s)
        dialogue_ratio = dialogue_sentences / max(sent_count, 1)

        # 动作强度：使用感叹号/问号/动作词汇密度
        action_markers = len(re.findall(r"[！!]", content))
        question_markers = len(re.findall(r"[？?]", content))
        action_keywords = len(re.findall(r"打|杀|冲|跑|跳|喊|叫|哭|笑|怒|吼", content))
        total_markers = action_markers + question_markers + action_keywords
        action_intensity = total_markers / max(word_count, 1) * 100  # 每百字标记数

        # 语气评分：正面/负面词汇比例
        positive_words = len(re.findall(r"高兴|快乐|开心|兴奋|激动|幸福|美好|希望|微笑|喜悦", content))
        negative_words = len(re.findall(r"悲伤|痛苦|愤怒|恐惧|绝望|焦虑|孤独|哭泣|仇恨|后悔", content))
        tone_ratio = (positive_words - negative_words) / max(positive_words + negative_words, 1)
        tone_score = max(-1.0, min(1.0, tone_ratio))  # 归一化到 [-1, 1]

        return {
            "word_count": word_count,
            "sentence_count": sent_count,
            "dialogue_ratio": dialogue_ratio,
            "action_intensity": action_intensity,
            "tone_score": tone_score,
        }

    @staticmethod
    def _detect_plot_points(metrics: List[dict]) -> List[dict]:
        """识别情节点（关键转折、悬念、高潮前奏）。"""
        plot_points = []

        for m in metrics:
            ch = m["chapter_number"]
            title = m.get("title", "")

            # 开篇（第1章总是情节点）
            if ch == 1:
                plot_points.append({
                    "chapter": ch,
                    "title": title,
                    "type": "opening",
                    "description": f"第{ch}章「{title or '无标题'}」：故事开篇。",
                })
                continue

            # 动作强度突增 => 冲突/高潮
            if m["action_intensity"] > 2.0:
                plot_points.append({
                    "chapter": ch,
                    "title": title,
                    "type": "conflict",
                    "description": f"第{ch}章动作强度高（{m['action_intensity']:.1f}），可能为冲突场景。",
                })

            # 语气大幅偏负面 => 转折/低谷
            if m["tone_score"] < -0.5:
                plot_points.append({
                    "chapter": ch,
                    "title": title,
                    "type": "turning_point",
                    "description": f"第{ch}章语气偏负面（{m['tone_score']:.2f}），可能为故事转折或低谷。",
                })

            # 对话比例极高 => 揭示/对话密集
            if m["dialogue_ratio"] > 0.6:
                plot_points.append({
                    "chapter": ch,
                    "title": title,
                    "type": "revelation",
                    "description": f"第{ch}章对话比例高（{m['dialogue_ratio']:.0%}），可能为信息揭示场景。",
                })

        return plot_points

    @staticmethod
    def _detect_plot_gaps(
        metrics: List[dict],
        chapters: list,
    ) -> List[dict]:
        """检测潜在的情节漏洞。

        策略：
        1. 开头提及的角色但结尾章节未出现 => 角色失踪
        2. 章节间有明显的语句中断/内容缺失
        3. 最后一章的章节号与章节数不符（暗示有缺失章节）
        """
        gaps: List[dict] = []

        if len(chapters) < 2:
            return gaps

        # 1. 提取前 1/3 章节中出现的角色，检查是否在最后 1/3 出现
        third = max(len(chapters) // 3, 1)
        early_names: set[str] = set()
        late_names: set[str] = set()

        for ch in chapters[:third]:
            names = BookAnalysisService._extract_names(ch.content or "")
            early_names.update(n for n in names if n not in _STOP_NAMES)

        for ch in chapters[-third:]:
            names = BookAnalysisService._extract_names(ch.content or "")
            late_names.update(n for n in names if n not in _STOP_NAMES)

        missing_names = early_names - late_names
        if missing_names:
            top_missing = list(missing_names)[:5]
            gaps.append({
                "type": "missing_character",
                "severity": "medium",
                "description": f"前{third}章登场的角色在最后{third}章未再出现："
                               f"「{'」、「'.join(top_missing)}」等。",
                "suggestion": "建议检查是否有未收尾的角色线。",
            })

        # 2. 章节内容完整性检查
        for i, ch in enumerate(chapters):
            content = (ch.content or "").strip()
            if not content:
                gaps.append({
                    "type": "empty_chapter",
                    "severity": "low",
                    "description": f"第{ch.chapter_number}章内容为空，"
                                   f"标题为「{ch.title or '无标题'}」。",
                    "suggestion": "建议补充该章节内容。",
                })
            elif len(content) < 50:
                gaps.append({
                    "type": "short_chapter",
                    "severity": "low",
                    "description": f"第{ch.chapter_number}章内容过短（{len(content)}字）。",
                    "suggestion": "建议检查章节是否完整。",
                })

        # 3. 章节编号连续性检查
        chapter_numbers = [ch.chapter_number for ch in chapters]
        expected = list(range(1, len(chapters) + 1))
        if chapter_numbers != expected:
            gaps.append({
                "type": "chapter_gap",
                "severity": "medium",
                "description": "章节序号不连续，可能存在缺失章节。",
                "suggestion": "请检查章节列表确认完整性。",
            })

        return gaps

    @staticmethod
    def _describe_paragraph_lengths(lengths: List[int]) -> str:
        """根据段落长度分布生成可读的描述。"""
        if not lengths:
            return "无段落数据"

        avg_len = sum(lengths) / len(lengths)
        max_len = max(lengths)
        # 短段落比例
        short_ratio = sum(1 for l in lengths if l < 50) / len(lengths)
        long_ratio = sum(1 for l in lengths if l > 500) / len(lengths)

        parts: List[str] = []
        if short_ratio > 0.5:
            parts.append("以短段落为主")
        elif short_ratio > 0.3:
            parts.append("短段落较多")
        else:
            parts.append("段落长度适中")

        if long_ratio > 0.2:
            parts.append("含有较多长段落")

        parts.append(f"平均段落长度约{avg_len:.0f}字")

        return "，".join(parts)

    @staticmethod
    def _find_common_phrases(text_parts: List[str], min_freq: int = 3) -> List[dict]:
        """识别高频常见短语（2~4 字组合）。

        通过统计相邻词组的共现频率找出可能的常用表达。
        """
        all_text = " ".join(text_parts)
        if not all_text.strip():
            return []

        # 提取连续汉字序列
        chinese_chars = re.findall(r"[\u4e00-\u9fff]+", all_text)
        flat = "".join(chinese_chars)
        if len(flat) < 10:
            return []

        phrase_counter: Counter[str] = Counter()

        # 统计 2~4 字短语
        for length in (2, 3, 4):
            for i in range(len(flat) - length + 1):
                phrase = flat[i:i + length]
                phrase_counter[phrase] += 1

        # 过滤：保留 >= min_freq 且不是纯叠词的短语
        common: List[dict] = []
        for phrase, count in phrase_counter.most_common(30):
            if count < min_freq:
                break
            # 跳过纯叠词（如"哈哈哈"）
            if len(set(phrase)) == 1:
                continue
            common.append({"phrase": phrase, "frequency": count})

        return common[:20]  # 最多返回 20 个


# ---- Singleton ----
book_analysis_service = BookAnalysisService()
