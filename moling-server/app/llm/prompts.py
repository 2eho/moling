"""
墨灵 (Moling) — Prompt Template Library.

Organises prompt templates by generation scenario.  Each function returns a
list of message dicts suitable for ``LLMClient.chat()``.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# System prompt presets
# ---------------------------------------------------------------------------

_SYSTEM_WRITER = (
    "你是一位资深小说创作助手，擅长文学创作、角色塑造和情节设计。"
    "请根据用户的需求提供高质量、富有创意的写作内容。"
    "你的回答应当使用中文。"
)

_SYSTEM_WORLD_BUILDER = (
    "你是一位世界观构建专家，擅长设计虚构世界的规则、历史和地理。"
    "请根据用户的需求创建详细而自洽的世界设定。"
    "你的回答应当使用中文。"
)

_SYSTEM_CRITIQUE = (
    "你是一位资深文学编辑，擅长分析文本并提供建设性反馈。"
    "请从情节逻辑、角色塑造、节奏控制和语言表达等维度进行点评。"
    "你的回答应当使用中文。"
)


# ---------------------------------------------------------------------------
# Prompt Library
# ---------------------------------------------------------------------------


class PromptLibrary:
    """Collection of prompt templates organised by scenario."""

    # ==================================================================
    # Character Generation
    # ==================================================================

    @staticmethod
    def generate_character(genre: str, role: str, traits: list[str]) -> list[dict[str, str]]:
        """Create a detailed character profile."""
        return [
            {"role": "system", "content": _SYSTEM_WRITER},
            {
                "role": "user",
                "content": (
                    f"请为一部 {genre} 小说创建一个{role}角色。\n\n"
                    f"性格特征：{'、'.join(traits) if traits else '自由创作'}\n\n"
                    "请提供以下信息：\n"
                    "1. 角色姓名及含义\n"
                    "2. 外貌描述\n"
                    "3. 性格特点\n"
                    "4. 背景故事\n"
                    "5. 动机与目标\n"
                    "6. 人际关系\n"
                    "7. 成长弧光\n"
                ),
            },
        ]

    # ==================================================================
    # Plot / Chapter Generation
    # ==================================================================

    @staticmethod
    def generate_chapter(
        project_title: str,
        genre: str,
        chapter_number: int,
        chapter_title: str,
        synopsis: str,
        previous_summary: str = "",
        direction_hints: str = "",
    ) -> list[dict[str, str]]:
        """Generate content for a new chapter."""
        messages = [
            {"role": "system", "content": _SYSTEM_WRITER},
            {
                "role": "user",
                "content": (
                    f"你正在创作小说《{project_title}》（{genre}）。\n\n"
                    f"请撰写第 {chapter_number} 章：「{chapter_title}」\n\n"
                    f"故事简介：{synopsis}\n\n"
                ),
            },
        ]

        if previous_summary:
            messages.append({
                "role": "assistant",
                "content": f"上一章概要：{previous_summary}",
            })

        if direction_hints:
            messages.append({
                "role": "user",
                "content": f"创作方向提示：{direction_hints}",
            })

        return messages

    # ==================================================================
    # World Building
    # ==================================================================

    @staticmethod
    def generate_world_entry(
        term: str,
        category: str,
        genre: str,
        existing_rules: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Create a detailed world-building entry."""
        messages = [
            {"role": "system", "content": _SYSTEM_WORLD_BUILDER},
            {
                "role": "user",
                "content": (
                    f"请为一部 {genre} 小说设计世界设定条目。\n\n"
                    f"条目名称：{term}\n"
                    f"类别：{category}\n\n"
                    "请提供：\n"
                    "1. 详细描述\n"
                    "2. 相关规则\n"
                    "3. 与其他设定的关联\n"
                ),
            },
        ]

        if existing_rules:
            messages.append({
                "role": "user",
                "content": f"已有规则参考：{'、'.join(existing_rules)}",
            })

        return messages

    # ==================================================================
    # Plot Analysis / Critique
    # ==================================================================

    @staticmethod
    def analyze_plot(
        project_title: str,
        chapters_content: str,
    ) -> list[dict[str, str]]:
        """Analyse plot consistency and health."""
        return [
            {"role": "system", "content": _SYSTEM_CRITIQUE},
            {
                "role": "user",
                "content": (
                    f"请分析小说《{project_title}》的情节健康度。\n\n"
                    f"已有章节内容：\n{chapters_content}\n\n"
                    "请从以下维度分析：\n"
                    "1. 情节逻辑一致性\n"
                    "2. 伏笔与铺垫\n"
                    "3. 节奏控制\n"
                    "4. 角色动机合理性\n"
                    "5. 潜在问题预警\n"
                ),
            },
        ]

    # ==================================================================
    # Card Direction Description Generation
    # ==================================================================

    @staticmethod
    def generate_card_description(
        name: str,
        direction_type: str,
        direction_text: str,
        genre: str,
    ) -> list[dict[str, str]]:
        """Expand a card direction into a rich description."""
        return [
            {"role": "system", "content": _SYSTEM_WRITER},
            {
                "role": "user",
                "content": (
                    f"请为一张创作方向卡撰写描述。\n\n"
                    f"卡片名称：{name}\n"
                    f"方向类型：{direction_type}\n"
                    f"方向提示：{direction_text}\n"
                    f"作品题材：{genre}\n\n"
                    f"请用生动具体的语言描述这个创作方向，"
                    f"让作者能立即获得灵感。"
                ),
            },
        ]
