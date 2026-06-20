"""墨灵 (Moling) — Context Window Budget Manager.

按算法文档 §3.5 的 Prompt 分层组装规范，在发往 LLM 之前检查
最终的 prompt 是否超出模型上下文窗口，并提供按优先级的分层截断策略。

分层优先级（§3.2 Lost-in-the-Middle 保护）：
  Layer 0 — 系统指令            → 从不截断（~50 字，可忽略）
  Layer 1 — 动态层 / 故事状态   → 从不截断（最高优先级，没有它 AI 不知道故事在哪儿）
  Layer 2 — 四库过滤上下文       → 超限时逐条目压缩
  Layer 3 — 本章方向 / 编织方案  → 保留头部
  Layer 4 — 风格约束             → 可抛弃（优先级最低）

Token 估算约定（与 vault_filter._CHARS_PER_TOKEN 保持一致）：
  中文：≈ 2 chars/token
  英文：≈ 4 chars/token
  混合文本使用保守估计 2 chars/token。

安全因子：0.85 — 为 max_tokens（输出）留出 15% 余量。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────
_CHARS_PER_TOKEN = 2         # 中文字符与 token 的保守换算（≈ 0.5 token/char）
_SAFETY_FACTOR = 0.85        # 上下文窗口利用的安全因子
_DEFAULT_MAX_TOKENS = 128_000  # DeepSeek V3 上下文窗口
_DEEPSEEK_V3_WINDOW = 128_000
_DEEPSEEK_R1_WINDOW = 128_000

# 模型窗口映射
_MODEL_WINDOWS: dict[str, int] = {
    "deepseek-chat":       _DEEPSEEK_V3_WINDOW,
    "deepseek-v3":         _DEEPSEEK_V3_WINDOW,
    "deepseek-v4-pro":     _DEEPSEEK_V3_WINDOW,
    "deepseek-v4-flash":   _DEEPSEEK_V3_WINDOW,
    "deepseek-reasoner":   _DEEPSEEK_R1_WINDOW,
    "deepseek-r1":         _DEEPSEEK_R1_WINDOW,
}


@dataclass
class BudgetResult:
    """上下文预算检查结果。"""

    within_budget: bool
    estimated_input_tokens: int
    available_tokens: int
    model_window: int
    max_output_tokens: int
    remaining_tokens: int
    truncated_prompt: str
    truncations: list[dict[str, str]] = field(default_factory=list)
    # 截断记录: [{layer: "Layer 2", field: "characters", from: 15, to: 5}, ...]


class ContextBudget:
    """LLM 上下文窗口预算管理器。"""

    # ── 公开入口 ──────────────────────────────────

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算文本所占 token 数（保守估计）。"""
        if not text:
            return 0
        return max(1, len(text) // _CHARS_PER_TOKEN)

    @staticmethod
    def get_model_window(model: str | None) -> int:
        """获取模型的上下文窗口 token 数。"""
        if model is None:
            return _DEFAULT_MAX_TOKENS
        return _MODEL_WINDOWS.get(model, _DEFAULT_MAX_TOKENS)

    @staticmethod
    def check(
        prompt: str,
        model: str | None = None,
        max_output_tokens: int = 4096,
    ) -> BudgetResult:
        """检查 prompt 是否在上下文窗口安全范围内。

        Args:
            prompt: 组装好的完整 prompt 文本。
            model: 模型名称（用于查询上下文窗口大小）。
            max_output_tokens: LLM 预计输出的最大 token 数。

        Returns:
            BudgetResult，其中 within_budget 表示是否在安全范围内。
        """
        model_window = ContextBudget.get_model_window(model)
        safe_window = int(model_window * _SAFETY_FACTOR)
        estimated_input = ContextBudget.estimate_tokens(prompt)
        available = safe_window - max_output_tokens
        remaining = available - estimated_input

        result = BudgetResult(
            within_budget=remaining >= 0,
            estimated_input_tokens=estimated_input,
            available_tokens=available,
            model_window=model_window,
            max_output_tokens=max_output_tokens,
            remaining_tokens=remaining,
            truncated_prompt=prompt,
        )

        if not result.within_budget:
            logger.warning(
                "Context budget exceeded: input=%d tokens, available=%d tokens, "
                "model=%s, max_output=%d, overflow=%d tokens",
                estimated_input,
                available,
                model or "default",
                max_output_tokens,
                abs(remaining),
            )

        return result

    @staticmethod
    def check_and_truncate(
        prompt: str,
        model: str | None = None,
        max_output_tokens: int = 4096,
        # ── 分层截断参数 ──
        layer2_max_chars_per_char: int = 200,   # 人物条目最大字符数（初始值）
        layer2_min_chars_per_char: int = 100,    # 人物条目最小字符数（极限压缩）
        layer2_max_promises: int = 8,             # 剧情承诺最多条数
        layer2_max_timeline: int = 3,             # 时间线最多条数
        layer2_max_world: int = 8,                # 世界观最多条数
    ) -> BudgetResult:
        """检查 prompt 并执行分层截断。

        与 check() 的不同：当超限时，执行逐层渐进截断直到进入预算。
        截断遵循算法文档 §3.2 的优先级规则。

        Returns:
            BudgetResult with truncated_prompt populated.
        """
        result = ContextBudget.check(prompt, model, max_output_tokens)
        if result.within_budget:
            return result

        truncated = prompt
        overflow_tokens = abs(result.remaining_tokens)
        overflow_chars = overflow_tokens * _CHARS_PER_TOKEN

        logger.info(
            "Applying layered truncation: overflow=%d tokens (~%d chars)",
            overflow_tokens, overflow_chars,
        )

        # ── 逐层截断 ──
        # 优先级（从低到高）：
        #   1. Layer 4 风格约束 → 完全删除
        #   2. Layer 2 四库数据 → 逐条目压缩
        #   3. Layer 3 方向 → 压缩创作灵感
        #   4. Layer 1 动态层 → NEVER（最高优先级）

        # 步骤 1: 删除 Layer 4
        result, truncated = ContextBudget._truncate_layer4(truncated, result)

        # 步骤 2: 压缩 Layer 3 创作灵感
        result, truncated = ContextBudget._truncate_layer3(truncated, result, model, max_output_tokens)

        # 步骤 3: 压缩 Layer 2 四库
        result, truncated = ContextBudget._truncate_layer2(
            truncated, result, model, max_output_tokens,
            layer2_max_chars_per_char, layer2_min_chars_per_char,
            layer2_max_promises, layer2_max_timeline, layer2_max_world,
        )

        # 步骤 4: 最终检查 — 如果还是超限，记录严重告警但不截断 Layer 1
        final = ContextBudget.check(truncated, model, max_output_tokens)
        if not final.within_budget:
            logger.error(
                "CRITICAL: Context still over budget after all truncations! "
                "input=%d tokens, available=%d. Layer 1 may be truncated by model.",
                final.estimated_input_tokens,
                final.available_tokens,
            )
        result = final
        result.truncated_prompt = truncated

        return result

    # ── 内部分层截断 ──────────────────────────────

    @staticmethod
    def _truncate_layer4(prompt: str, current: BudgetResult) -> tuple[BudgetResult, str]:
        """删除 Layer 4 风格约束（最低优先级）。"""
        if "=== Layer 4 ===" in prompt or "[Layer 4:" in prompt:
            new_prompt = prompt
            for marker in ("=== Layer 4 ===", "[Layer 4:", "【风格约束】"):
                idx = new_prompt.find(marker)
                if idx > 0:
                    # 找到下一个分隔符或行尾
                    next_marker = new_prompt.find("\n\n", idx)
                    if next_marker == -1:
                        next_marker = len(new_prompt)
                    new_prompt = new_prompt[:idx].rstrip() + new_prompt[next_marker:]
                    logger.info("Truncated Layer 4 (style constraints)")
                    current.truncations.append({"layer": "Layer 4", "action": "removed"})
                    break
            return current, new_prompt
        return current, prompt

    @staticmethod
    def _truncate_layer3(
        prompt: str,
        current: BudgetResult,
        model: str | None,
        max_output_tokens: int,
    ) -> tuple[BudgetResult, str]:
        """压缩 Layer 3 创作灵感部分（保留方向 + 编织方案，压缩灵感）。"""
        new = ContextBudget.check(prompt, model, max_output_tokens)
        if new.within_budget:
            return new, prompt

        # 尝试去掉创作灵感部分
        if "【创作灵感】" in prompt:
            idx = prompt.find("【创作灵感】")
            next_section = prompt.find("=== ", idx + 1)
            if next_section == -1:
                next_section = prompt.find("【写作要求】", idx + 1)
            if next_section == -1:
                next_section = prompt.find("\n\n", idx + len("【创作灵感】"))
            if next_section > idx:
                new_prompt = prompt[:idx].rstrip() + "\n\n" + prompt[next_section:].lstrip()
                logger.info("Truncated Layer 3 inspiration (kept direction + weaving)")
                current.truncations.append({"layer": "Layer 3", "field": "inspiration", "action": "removed"})
                return ContextBudget.check(new_prompt, model, max_output_tokens), new_prompt

        return new, prompt

    @staticmethod
    def _truncate_layer2(
        prompt: str,
        current: BudgetResult,
        model: str | None,
        max_output_tokens: int,
        max_chars_per_char: int,
        min_chars_per_char: int,
        max_promises: int,
        max_timeline: int,
        max_world: int,
    ) -> tuple[BudgetResult, str]:
        """压缩 Layer 2 四库数据（逐条目截断直到进入预算）。"""
        new = ContextBudget.check(prompt, model, max_output_tokens)
        if new.within_budget:
            return new, prompt

        # 渐进式压缩策略：每轮减少 1 条/20 字符，直到进入预算或达到下限
        truncated = prompt
        current_chars_per_char = max_chars_per_char
        current_max_promises = max_promises
        current_max_timeline = max_timeline
        current_max_world = max_world

        MAX_ROUNDS = 10  # 防止死循环

        for round_idx in range(MAX_ROUNDS):
            before = truncated

            # 压缩人物条目
            truncated = ContextBudget._truncate_characters(truncated, current_chars_per_char)
            # 压缩剧情承诺条目数
            truncated = ContextBudget._truncate_section(truncated, "【相关剧情承诺】", current_max_promises)
            # 压缩时间线条目数
            truncated = ContextBudget._truncate_section(truncated, "【时间线参考】", current_max_timeline)
            # 压缩世界观条目数
            truncated = ContextBudget._truncate_section(truncated, "【世界观规则】", current_max_world)

            new = ContextBudget.check(truncated, model, max_output_tokens)
            if new.within_budget:
                logger.info(
                    "Layer 2 truncation round %d: now within budget "
                    "(chars_per_char=%d, promises=%d, timeline=%d, world=%d)",
                    round_idx + 1,
                    current_chars_per_char,
                    current_max_promises,
                    current_max_timeline,
                    current_max_world,
                )
                current.truncations.append({
                    "layer": "Layer 2",
                    "action": "compressed",
                    "chars_per_character": current_chars_per_char,
                    "max_promises": current_max_promises,
                    "max_timeline": current_max_timeline,
                    "max_world": current_max_world,
                })
                return new, truncated

            if truncated == before:
                # 没有变化，已经无法继续压缩
                logger.warning("Layer 2 truncation stalled at round %d", round_idx + 1)
                break

            # 下一轮更激进地压缩
            current_chars_per_char = max(min_chars_per_char, current_chars_per_char - 20)
            current_max_promises = max(1, current_max_promises - 1)
            current_max_timeline = max(1, current_max_timeline - 1)
            current_max_world = max(1, current_max_world - 1)

        return new, truncated

    @staticmethod
    def _truncate_characters(prompt: str, max_chars: int) -> str:
        """截断人物描述字段到指定字符数。"""
        import re

        # 匹配形如 【角色名】\n  描述: ...\n  当前状态: ... 的段落
        # 策略：对每个角色的"描述"和"当前状态"行截断
        def truncate_char_block(match: re.Match) -> str:
            block = match.group(0)
            lines = block.split("\n")
            result_lines = []
            for line in lines:
                if line.startswith("  描述: ") and len(line) > max_chars + 10:
                    result_lines.append(line[:max_chars + 10] + "…")
                elif line.startswith("  当前状态: ") and len(line) > max_chars + 10:
                    result_lines.append(line[:max_chars + 10] + "…")
                elif line.startswith("  ") and len(line) > max_chars:
                    result_lines.append(line[:max_chars] + "…")
                else:
                    result_lines.append(line)
            return "\n".join(result_lines)

        return re.sub(
            r"【[^】]+】\n(?:\s{2,3}.*\n?)+",
            truncate_char_block,
            prompt,
        )

    @staticmethod
    def _truncate_section(prompt: str, section_header: str, max_entries: int) -> str:
        """截断指定 section 的条目数到 max_entries 条。"""
        import re

        idx = prompt.find(section_header)
        if idx == -1:
            return prompt

        # 找到 section 内容
        section_start = idx
        # 找到下一个 section 的开始
        next_section = prompt.find("\n【", section_start + len(section_header))
        if next_section == -1:
            next_section = prompt.find("\n=", section_start + len(section_header))
        if next_section == -1:
            next_section = len(prompt)

        section_content = prompt[section_start:next_section]
        entries = [e.strip() for e in section_content.split("\n- ") if e.strip()]

        if len(entries) <= max_entries:
            return prompt

        # 保留前 max_entries 条
        kept = entries[:max_entries]
        new_section = section_header + "\n" + "\n".join(f"- {e}" for e in kept if not e.startswith(section_header))
        return prompt[:section_start] + new_section + prompt[next_section:]


# ── 单例 ──────────────────────────────────────────
context_budget = ContextBudget()
