"""Moling - 4-Layer Prompt Assembly Service.

Implements the structured 4-layer prompt architecture:
Layer 0: System instruction
Layer 1: Dynamic context (summary, anchors, hooks)
Layer 2: Vault data (characters, promises, timeline, world)
Layer 3: Card fusion direction
Layer 4: Style constraints
"""

from typing import Any, Dict, List, Optional


class PromptService:
    """Service for building structured 4-layer prompts for LLM generation."""

    # ───────── Layer 0: System Instruction ─────────

    def build_layer0(self, chapter_number: int) -> str:
        """Build Layer 0: system instruction (~50 chars)."""
        return f"你是一位专业的网络小说作家。撰写第{chapter_number}章。"

    # ───────── Layer 1: Dynamic Layer ─────────

    def build_layer1(
        self,
        project_name: str,
        chapter_title: str,
        pov_character: Optional[str],
        location: Optional[str],
        time_period: Optional[str],
        summary: str,
        must_hold: List[str],
        must_not: List[str],
        unresolved_hooks: List[str],
    ) -> str:
        """Build Layer 1: dynamic context — summary, anchors, hooks (~500 chars).

        Args:
            project_name: 项目/小说名称
            chapter_title: 当前章节标题
            pov_character: 视点角色 (POV)
            location: 场景地点
            time_period: 场景时间
            summary: 前情摘要
            must_hold: 必须保持的约束列表
            must_not: 必须避免的约束列表
            unresolved_hooks: 未解决的悬念列表
        """
        parts = [f"【项目】{project_name}", f"【章节】{chapter_title}"]

        # Chapter anchors (POV / location / time)
        anchors = []
        if pov_character:
            anchors.append(f"视点：{pov_character}")
        if location:
            anchors.append(f"地点：{location}")
        if time_period:
            anchors.append(f"时间：{time_period}")
        if anchors:
            parts.append(f"【锚点】{' | '.join(anchors)}")

        # Previous chapter summary
        if summary:
            parts.append(f"【前情摘要】\n{summary}")

        # Coherence baseline
        if must_hold:
            parts.append(
                "【必须保持】\n" + "\n".join(f"- {item}" for item in must_hold)
            )
        if must_not:
            parts.append(
                "【必须避免】\n" + "\n".join(f"- {item}" for item in must_not)
            )

        # Top unresolved hooks (cap at 3)
        active_hooks = unresolved_hooks[:3] if unresolved_hooks else []
        if active_hooks:
            parts.append(
                "【未收束钩子】\n" + "\n".join(f"- {h}" for h in active_hooks)
            )

        return "\n\n".join(parts)

    # ───────── Layer 2: Vault Filtered Data ─────────

    def build_layer2(
        self,
        characters: List[Dict[str, Any]],
        plot_promises: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]],
        world_rules: List[Dict[str, Any]],
    ) -> str:
        """Build Layer 2: vault filtered data — characters, promises, timeline, world (~1500 chars).

        Args:
            characters: 角色列表，每个角色可含 name, role, description, traits, emotion
            plot_promises: 伏笔列表，每个伏笔可含 description, type, status, urgency
            timeline: 时间线事件列表，每个事件可含 event, description, impact
            world_rules: 世界观规则列表，每个规则可含 term, description, category
        """
        sections = []

        # ── Characters ──
        if characters:
            char_lines = []
            for c in characters:
                name = c.get("name", "?")
                role = c.get("role", "")
                desc = c.get("description", "")
                traits = c.get("traits", [])
                emotion = c.get("emotion", "")

                line = f"- {name}"
                if role:
                    line += f" ({role})"
                if desc:
                    line += f"：{desc}"
                if traits:
                    line += f"；特质：{', '.join(traits[:3])}"
                if emotion:
                    line += f"；情绪：{emotion}"
                char_lines.append(line)
            sections.append("【角色信息】\n" + "\n".join(char_lines))

        # ── Plot Promises ──
        if plot_promises:
            promise_lines = []
            for p in plot_promises:
                desc = p.get("description", "?")
                ptype = p.get("type", "")
                status = p.get("status", "")
                urgency = p.get("urgency", "")
                line = f"- {desc}"
                if ptype:
                    line += f" [{ptype}]"
                if status:
                    line += f" ({status})"
                if urgency:
                    line += f" 紧迫度：{urgency}"
                promise_lines.append(line)
            sections.append("【相关伏笔】\n" + "\n".join(promise_lines))

        # ── Timeline ──
        if timeline:
            timeline_lines = []
            for t in timeline:
                event = t.get("event", "?")
                tdesc = t.get("description", "")
                impact = t.get("impact", "")
                line = f"- {event}"
                if tdesc:
                    line += f"：{tdesc}"
                if impact:
                    line += f" (影响：{impact})"
                timeline_lines.append(line)
            sections.append("【时间线参考】\n" + "\n".join(timeline_lines))

        # ── World Rules ──
        if world_rules:
            world_lines = []
            for w in world_rules:
                term = w.get("term", "?")
                wdesc = w.get("description", "")
                category = w.get("category", "")
                line = f"- {term}"
                if category:
                    line += f" [{category}]"
                if wdesc:
                    line += f"：{wdesc}"
                world_lines.append(line)
            sections.append("【世界观规则】\n" + "\n".join(world_lines))

        return "\n\n".join(sections) if sections else "（暂无 vault 数据）"

    # ───────── Layer 3: Card Fusion Direction ─────────

    def build_layer3(
        self,
        cards: List[Dict[str, Any]],
        weight_map: Dict[str, float],
        weaving_scheme: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build Layer 3: card fusion direction (~300 chars).

        Args:
            cards: 已选卡牌列表，每张卡牌可含 name, direction_type, direction_text, rarity
            weight_map: 卡牌名称 -> 权重的映射
            weaving_scheme: 编织方案（可选），描述如何融合多张卡牌的方向
        """
        parts = []

        if cards:
            card_lines = []
            for card in cards:
                name = card.get("name", "?")
                dtype = card.get("direction_type", "")
                dtext = card.get("direction_text", "")
                weight = weight_map.get(name, 1.0)
                line = f"- {name}"
                if dtype:
                    line += f" [{dtype}]"
                line += f" (权重: {weight:.2f})"
                if dtext:
                    line += f"\n  方向：{dtext}"
                card_lines.append(line)

            parts.append("【卡牌融合方向】\n" + "\n".join(card_lines))

        if weaving_scheme:
            scheme_desc = weaving_scheme.get("description", "")
            scheme_order = weaving_scheme.get("order", [])
            scheme_emphasis = weaving_scheme.get("emphasis", "")
            scheme_lines = []
            if scheme_desc:
                scheme_lines.append(f"方案：{scheme_desc}")
            if scheme_order:
                scheme_lines.append(f"融合顺序：{' → '.join(str(s) for s in scheme_order)}")
            if scheme_emphasis:
                scheme_lines.append(f"侧重：{scheme_emphasis}")
            if scheme_lines:
                parts.append("【编织方案】\n" + "\n".join(scheme_lines))

        return "\n\n".join(parts) if parts else "（暂无卡牌方向）"

    # ───────── Layer 4: Style Constraints ─────────

    def build_layer4(
        self,
        style_fingerprint: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build Layer 4: style constraints (~200 chars).

        Args:
            style_fingerprint: 可选文风指纹字典，包含 avg_sentence_length,
                               dialogue_ratio, dominant_pov 等维度
        """
        if not style_fingerprint:
            return ""

        lines = ["【风格约束】"]

        # Sentence complexity
        avg_len = style_fingerprint.get("avg_sentence_length")
        if avg_len:
            if avg_len < 30:
                lines.append("- 句式偏好：短句为主，简洁明快")
            elif avg_len < 50:
                lines.append("- 句式偏好：中等句长，张弛有度")
            else:
                lines.append("- 句式偏好：长句为主，细腻描写")

        # Dialogue ratio
        dia_ratio = style_fingerprint.get("dialogue_ratio")
        if dia_ratio is not None:
            if dia_ratio > 0.4:
                lines.append("- 对话偏好：对话驱动，占比高")
            elif dia_ratio > 0.2:
                lines.append("- 对话偏好：对话与叙述均衡")
            else:
                lines.append("- 对话偏好：叙述为主，对话精炼")

        # POV
        pov = style_fingerprint.get("dominant_pov", "")
        if pov:
            pov_map = {
                "first": "第一人称视角",
                "second": "第二人称视角",
                "third": "第三人称视角",
            }
            pov_label = pov_map.get(pov, f"{pov}视角")
            lines.append(f"- 视角偏好：{pov_label}")

        # Paragraph rhythm
        avg_para = style_fingerprint.get("avg_paragraph_length")
        if avg_para:
            if avg_para < 100:
                lines.append("- 段落节奏：短段落，节奏快")
            elif avg_para < 250:
                lines.append("- 段落节奏：中等段落，节奏适中")
            else:
                lines.append("- 段落节奏：长段落，节奏舒缓")

        # Punctuation density hints
        excl = style_fingerprint.get("exclamation_density", 0)
        if excl > 5:
            lines.append("- 标点风格：情感强烈，感叹号使用偏多")

        if len(lines) == 1:
            return ""  # Only the header, no actual constraints

        return "\n".join(lines)

    # ───────── Combined Full Prompt ─────────

    def build_full_prompt(
        self,
        chapter_number: int,
        project_name: str,
        chapter_title: str,
        pov_character: Optional[str] = None,
        location: Optional[str] = None,
        time_period: Optional[str] = None,
        summary: str = "",
        must_hold: Optional[List[str]] = None,
        must_not: Optional[List[str]] = None,
        unresolved_hooks: Optional[List[str]] = None,
        characters: Optional[List[Dict[str, Any]]] = None,
        plot_promises: Optional[List[Dict[str, Any]]] = None,
        timeline: Optional[List[Dict[str, Any]]] = None,
        world_rules: Optional[List[Dict[str, Any]]] = None,
        cards: Optional[List[Dict[str, Any]]] = None,
        weight_map: Optional[Dict[str, float]] = None,
        weaving_scheme: Optional[Dict[str, Any]] = None,
        style_fingerprint: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the full structured prompt combining all 5 layers.

        Args:
            chapter_number: 章节号
            project_name: 项目名称
            chapter_title: 章节标题
            pov_character: 视点角色
            location: 场景地点
            time_period: 场景时间
            summary: 前情摘要
            must_hold: 必须保持的约束列表
            must_not: 必须避免的约束列表
            unresolved_hooks: 未收束钩子列表
            characters: 角色信息列表
            plot_promises: 伏笔列表
            timeline: 时间线事件列表
            world_rules: 世界观规则列表
            cards: 已选卡牌列表
            weight_map: 卡牌权重映射
            weaving_scheme: 编织方案
            style_fingerprint: 文风指纹

        Returns:
            组装好的完整 prompt 字符串
        """
        must_hold = must_hold or []
        must_not = must_not or []
        unresolved_hooks = unresolved_hooks or []
        characters = characters or []
        plot_promises = plot_promises or []
        timeline = timeline or []
        world_rules = world_rules or []
        cards = cards or []
        weight_map = weight_map or {}

        layer0 = self.build_layer0(chapter_number)
        layer1 = self.build_layer1(
            project_name=project_name,
            chapter_title=chapter_title,
            pov_character=pov_character,
            location=location,
            time_period=time_period,
            summary=summary,
            must_hold=must_hold,
            must_not=must_not,
            unresolved_hooks=unresolved_hooks,
        )
        layer2 = self.build_layer2(
            characters=characters,
            plot_promises=plot_promises,
            timeline=timeline,
            world_rules=world_rules,
        )
        layer3 = self.build_layer3(
            cards=cards,
            weight_map=weight_map,
            weaving_scheme=weaving_scheme,
        )
        layer4 = self.build_layer4(style_fingerprint=style_fingerprint)

        sections = [
            f"=== Layer 0 ===\n{layer0}",
            f"=== Layer 1 ===\n{layer1}",
            f"=== Layer 2 ===\n{layer2}",
            f"=== Layer 3 ===\n{layer3}",
        ]
        if layer4:
            sections.append(f"=== Layer 4 ===\n{layer4}")

        sections.append(
            "请直接开始写作，不要添加任何解释或说明。"
        )

        return "\n\n".join(sections)


# Singleton instance
prompt_service = PromptService()
