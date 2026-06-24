//! Prompt service — builds structured 4-layer LLM prompts for chapter generation.
//!
//! Implements the layered prompt architecture:
//!
//! | Layer | Name             | Priority    | Content                                  |
//! |-------|------------------|-------------|------------------------------------------|
//! | 0     | System           | Never drop  | Writer persona + chapter number          |
//! | 1     | Dynamic Context  | Never drop  | Summary, POV, anchors, must-hold/avoid   |
//! | 2     | Vault Data       | Compress    | Characters, promises, timeline, world    |
//! | 3     | Card Fusion      | Compress    | Selected direction cards + weaving       |
//! | 4     | Style            | Drop first  | Sentence length, dialogue ratio, POV     |
//!
//! Token budget cooperation: Layer 3/4 are designed to be safely dropped
//! or compressed by [`moling_llm::budget::ContextBudget`].

use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Supporting data types for prompt building
// ---------------------------------------------------------------------------

/// Character information for Layer 2 vault data.
#[derive(Debug, Clone, Default)]
pub struct CharacterInfo {
    pub name: String,
    pub role: Option<String>,
    pub description: Option<String>,
    pub traits: Vec<String>,
    pub emotion: Option<String>,
}

/// Plot promise / foreshadowing information for Layer 2.
#[derive(Debug, Clone, Default)]
pub struct PlotPromiseInfo {
    pub description: String,
    pub promise_type: Option<String>,
    pub status: Option<String>,
    pub urgency: Option<String>,
}

/// Timeline event for Layer 2.
#[derive(Debug, Clone, Default)]
pub struct TimelineEventInfo {
    pub event: String,
    pub description: Option<String>,
    pub impact: Option<String>,
}

/// World-building rule/term for Layer 2.
#[derive(Debug, Clone, Default)]
pub struct WorldRuleInfo {
    pub term: String,
    pub description: Option<String>,
    pub category: Option<String>,
}

/// Style fingerprint for Layer 4 constraints.
///
/// Derived from corpus analysis — used to enforce stylistic consistency.
#[derive(Debug, Clone, Default)]
pub struct StyleFingerprint {
    /// Average sentence length in characters.
    pub avg_sentence_length: Option<f64>,
    /// Dialogue ratio (0.0–1.0) — fraction of text that is dialogue.
    pub dialogue_ratio: Option<f64>,
    /// Dominant POV: "first", "second", "third".
    pub dominant_pov: Option<String>,
    /// Average paragraph length in characters.
    pub avg_paragraph_length: Option<f64>,
    /// Exclamation mark density (per 1000 chars).
    pub exclamation_density: Option<f64>,
}

/// A direction card for Layer 3 fusion.
#[derive(Debug, Clone, Default)]
pub struct CardInfo {
    pub name: String,
    pub direction_type: Option<String>,
    pub direction_text: Option<String>,
    pub rarity: Option<String>,
}

/// Weaving scheme describing how to fuse multiple direction cards.
#[derive(Debug, Clone, Default)]
pub struct WeavingScheme {
    pub description: Option<String>,
    pub order: Vec<String>,
    pub emphasis: Option<String>,
}

// ---------------------------------------------------------------------------
// PromptContext — chapter-generation context (backward-compatible + extended)
// ---------------------------------------------------------------------------

/// Prompt building context: genre, style, previous content, vault data.
#[derive(Debug, Clone, Default)]
pub struct PromptContext {
    pub genre: String,
    pub style: String,
    pub previous_chapter_summary: Option<String>,
    pub active_characters: Vec<String>,
    pub active_secrets: Vec<String>,
    pub user_instruction: Option<String>,
}

/// Full prompt assembly input — all layers at once.
#[derive(Debug, Clone, Default)]
pub struct FullPromptInput {
    // Layer 0
    pub chapter_number: i32,

    // Layer 1
    pub project_name: String,
    pub chapter_title: String,
    pub pov_character: Option<String>,
    pub location: Option<String>,
    pub time_period: Option<String>,
    pub summary: String,
    pub must_hold: Vec<String>,
    pub must_not: Vec<String>,
    pub unresolved_hooks: Vec<String>,

    // Layer 2
    pub characters: Vec<CharacterInfo>,
    pub plot_promises: Vec<PlotPromiseInfo>,
    pub timeline: Vec<TimelineEventInfo>,
    pub world_rules: Vec<WorldRuleInfo>,

    // Layer 3
    pub cards: Vec<CardInfo>,
    pub weight_map: HashMap<String, f64>,
    pub weaving_scheme: Option<WeavingScheme>,

    // Layer 4
    pub style_fingerprint: Option<StyleFingerprint>,
}

// ---------------------------------------------------------------------------
// PromptService
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct PromptService;

impl PromptService {
    pub fn new() -> Self {
        Self
    }

    // ─────────────────────────────────────────────────────────────────
    // Layer 0: System Instruction
    // ─────────────────────────────────────────────────────────────────

    /// Build Layer 0: system instruction (~50 chars).
    ///
    /// Sets the writer persona and chapter context.
    pub fn build_layer0(&self, chapter_number: i32) -> String {
        format!("你是一位专业的网络小说作家。撰写第{chapter_number}章。")
    }

    // ─────────────────────────────────────────────────────────────────
    // Layer 1: Dynamic Context
    // ─────────────────────────────────────────────────────────────────

    /// Build Layer 1: dynamic context — summary, anchors, hooks (~500 chars).
    ///
    /// This layer is **NEVER** truncated by the budget system.
    pub fn build_layer1(
        &self,
        project_name: &str,
        chapter_title: &str,
        pov_character: Option<&str>,
        location: Option<&str>,
        time_period: Option<&str>,
        summary: &str,
        must_hold: &[String],
        must_not: &[String],
        unresolved_hooks: &[String],
    ) -> String {
        let mut parts: Vec<String> = Vec::new();

        parts.push(format!("【项目】{project_name}"));
        parts.push(format!("【章节】{chapter_title}"));

        // Chapter anchors (POV / location / time)
        let mut anchors: Vec<String> = Vec::new();
        if let Some(pov) = pov_character {
            anchors.push(format!("视点：{pov}"));
        }
        if let Some(loc) = location {
            anchors.push(format!("地点：{loc}"));
        }
        if let Some(time) = time_period {
            anchors.push(format!("时间：{time}"));
        }
        if !anchors.is_empty() {
            parts.push(format!("【锚点】{}", anchors.join(" | ")));
        }

        // Previous chapter summary
        if !summary.is_empty() {
            parts.push(format!("【前情摘要】\n{summary}"));
        }

        // Coherence baseline
        if !must_hold.is_empty() {
            let items: Vec<String> = must_hold.iter().map(|item| format!("- {item}")).collect();
            parts.push(format!("【必须保持】\n{}", items.join("\n")));
        }
        if !must_not.is_empty() {
            let items: Vec<String> = must_not.iter().map(|item| format!("- {item}")).collect();
            parts.push(format!("【必须避免】\n{}", items.join("\n")));
        }

        // Top unresolved hooks (cap at 3)
        let active_hooks: Vec<&String> = unresolved_hooks.iter().take(3).collect();
        if !active_hooks.is_empty() {
            let items: Vec<String> = active_hooks.iter().map(|h| format!("- {h}")).collect();
            parts.push(format!("【未收束钩子】\n{}", items.join("\n")));
        }

        parts.join("\n\n")
    }

    // ─────────────────────────────────────────────────────────────────
    // Layer 2: Vault Filtered Data
    // ─────────────────────────────────────────────────────────────────

    /// Build Layer 2: vault filtered data — characters, promises, timeline, world (~1500 chars).
    ///
    /// This layer can be progressively compressed by the budget system.
    pub fn build_layer2(
        &self,
        characters: &[CharacterInfo],
        plot_promises: &[PlotPromiseInfo],
        timeline: &[TimelineEventInfo],
        world_rules: &[WorldRuleInfo],
    ) -> String {
        let mut sections: Vec<String> = Vec::new();

        // ── Characters ──
        if !characters.is_empty() {
            let char_lines: Vec<String> = characters
                .iter()
                .map(|c| {
                    let mut line = format!("- {}", c.name);
                    if let Some(ref role) = c.role {
                        line.push_str(&format!(" ({role})"));
                    }
                    if let Some(ref desc) = c.description {
                        line.push_str(&format!("：{desc}"));
                    }
                    if !c.traits.is_empty() {
                        line.push_str(&format!(
                            "；特质：{}",
                            c.traits
                                .iter()
                                .take(3)
                                .cloned()
                                .collect::<Vec<_>>()
                                .join("、")
                        ));
                    }
                    if let Some(ref emotion) = c.emotion {
                        line.push_str(&format!("；情绪：{emotion}"));
                    }
                    line
                })
                .collect();
            sections.push(format!("【角色信息】\n{}", char_lines.join("\n")));
        }

        // ── Plot Promises ──
        if !plot_promises.is_empty() {
            let promise_lines: Vec<String> = plot_promises
                .iter()
                .map(|p| {
                    let mut line = format!("- {}", p.description);
                    if let Some(ref ptype) = p.promise_type {
                        line.push_str(&format!(" [{ptype}]"));
                    }
                    if let Some(ref status) = p.status {
                        line.push_str(&format!(" ({status})"));
                    }
                    if let Some(ref urgency) = p.urgency {
                        line.push_str(&format!(" 紧迫度：{urgency}"));
                    }
                    line
                })
                .collect();
            sections.push(format!("【相关伏笔】\n{}", promise_lines.join("\n")));
        }

        // ── Timeline ──
        if !timeline.is_empty() {
            let timeline_lines: Vec<String> = timeline
                .iter()
                .map(|t| {
                    let mut line = format!("- {}", t.event);
                    if let Some(ref tdesc) = t.description {
                        line.push_str(&format!("：{tdesc}"));
                    }
                    if let Some(ref impact) = t.impact {
                        line.push_str(&format!(" (影响：{impact})"));
                    }
                    line
                })
                .collect();
            sections.push(format!("【时间线参考】\n{}", timeline_lines.join("\n")));
        }

        // ── World Rules ──
        if !world_rules.is_empty() {
            let world_lines: Vec<String> = world_rules
                .iter()
                .map(|w| {
                    let mut line = format!("- {}", w.term);
                    if let Some(ref category) = w.category {
                        line.push_str(&format!(" [{category}]"));
                    }
                    if let Some(ref wdesc) = w.description {
                        line.push_str(&format!("：{wdesc}"));
                    }
                    line
                })
                .collect();
            sections.push(format!("【世界观规则】\n{}", world_lines.join("\n")));
        }

        if sections.is_empty() {
            "（暂无 vault 数据）".to_owned()
        } else {
            sections.join("\n\n")
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Layer 3: Card Fusion Direction
    // ─────────────────────────────────────────────────────────────────

    /// Build Layer 3: card fusion direction (~300 chars).
    ///
    /// Cards carry weights from the direction-scoring pipeline.
    pub fn build_layer3(
        &self,
        cards: &[CardInfo],
        weight_map: &HashMap<String, f64>,
        weaving_scheme: Option<&WeavingScheme>,
    ) -> String {
        let mut parts: Vec<String> = Vec::new();

        if !cards.is_empty() {
            let card_lines: Vec<String> = cards
                .iter()
                .map(|card| {
                    let weight = weight_map.get(&card.name).copied().unwrap_or(1.0);
                    let mut line = format!("- {}", card.name);
                    if let Some(ref dtype) = card.direction_type {
                        line.push_str(&format!(" [{dtype}]"));
                    }
                    line.push_str(&format!(" (权重: {weight:.2})"));
                    if let Some(ref dtext) = card.direction_text {
                        line.push_str(&format!("\n  方向：{dtext}"));
                    }
                    line
                })
                .collect();
            parts.push(format!("【卡牌融合方向】\n{}", card_lines.join("\n")));
        }

        if let Some(scheme) = weaving_scheme {
            let mut scheme_lines: Vec<String> = Vec::new();
            if let Some(ref desc) = scheme.description {
                scheme_lines.push(format!("方案：{desc}"));
            }
            if !scheme.order.is_empty() {
                scheme_lines.push(format!(
                    "融合顺序：{}",
                    scheme
                        .order
                        .iter()
                        .map(|s| s.as_str())
                        .collect::<Vec<_>>()
                        .join(" → ")
                ));
            }
            if let Some(ref emphasis) = scheme.emphasis {
                scheme_lines.push(format!("侧重：{emphasis}"));
            }
            if !scheme_lines.is_empty() {
                parts.push(format!("【编织方案】\n{}", scheme_lines.join("\n")));
            }
        }

        if parts.is_empty() {
            "（暂无卡牌方向）".to_owned()
        } else {
            parts.join("\n\n")
        }
    }

    // ─────────────────────────────────────────────────────────────────
    // Layer 4: Style Constraints
    // ─────────────────────────────────────────────────────────────────

    /// Build Layer 4: style constraints (~200 chars).
    ///
    /// This is the **first** layer to be dropped when the token budget
    /// is exceeded. Returns empty string if no fingerprint provided.
    pub fn build_layer4(&self, style_fingerprint: Option<&StyleFingerprint>) -> String {
        let fp = match style_fingerprint {
            Some(f) => f,
            None => return String::new(),
        };

        let mut lines: Vec<String> = vec!["【风格约束】".to_owned()];

        // Sentence complexity
        if let Some(avg_len) = fp.avg_sentence_length {
            let desc = if avg_len < 30.0 {
                "句式偏好：短句为主，简洁明快"
            } else if avg_len < 50.0 {
                "句式偏好：中等句长，张弛有度"
            } else {
                "句式偏好：长句为主，细腻描写"
            };
            lines.push(format!("- {desc}"));
        }

        // Dialogue ratio
        if let Some(dia_ratio) = fp.dialogue_ratio {
            let desc = if dia_ratio > 0.4 {
                "对话偏好：对话驱动，占比高"
            } else if dia_ratio > 0.2 {
                "对话偏好：对话与叙述均衡"
            } else {
                "对话偏好：叙述为主，对话精炼"
            };
            lines.push(format!("- {desc}"));
        }

        // POV
        if let Some(ref pov) = fp.dominant_pov {
            let pov_label = match pov.as_str() {
                "first" => "第一人称视角",
                "second" => "第二人称视角",
                "third" => "第三人称视角",
                other => other,
            };
            lines.push(format!("- 视角偏好：{pov_label}"));
        }

        // Paragraph rhythm
        if let Some(avg_para) = fp.avg_paragraph_length {
            let desc = if avg_para < 100.0 {
                "段落节奏：短段落，节奏快"
            } else if avg_para < 250.0 {
                "段落节奏：中等段落，节奏适中"
            } else {
                "段落节奏：长段落，节奏舒缓"
            };
            lines.push(format!("- {desc}"));
        }

        // Punctuation density hints
        if let Some(excl) = fp.exclamation_density
            && excl > 5.0 {
                lines.push("- 标点风格：情感强烈，感叹号使用偏多".to_owned());
            }

        if lines.len() == 1 {
            return String::new(); // Only the header, no actual constraints
        }

        lines.join("\n")
    }

    // ─────────────────────────────────────────────────────────────────
    // Full Prompt Assembly
    // ─────────────────────────────────────────────────────────────────

    /// Build the full structured prompt combining all 5 layers.
    ///
    /// The output includes layer markers (`=== Layer N ===`) which are used
    /// by [`moling_llm::budget::ContextBudget`] for targeted truncation.
    ///
    /// Returns a prompt string ready to send to the LLM.
    pub fn build_full_prompt(&self, input: &FullPromptInput) -> String {
        let layer0 = self.build_layer0(input.chapter_number);
        let layer1 = self.build_layer1(
            &input.project_name,
            &input.chapter_title,
            input.pov_character.as_deref(),
            input.location.as_deref(),
            input.time_period.as_deref(),
            &input.summary,
            &input.must_hold,
            &input.must_not,
            &input.unresolved_hooks,
        );
        let layer2 = self.build_layer2(
            &input.characters,
            &input.plot_promises,
            &input.timeline,
            &input.world_rules,
        );
        let layer3 = self.build_layer3(
            &input.cards,
            &input.weight_map,
            input.weaving_scheme.as_ref(),
        );
        let layer4 = self.build_layer4(input.style_fingerprint.as_ref());

        let mut sections = vec![
            format!("=== Layer 0 ===\n{layer0}"),
            format!("=== Layer 1 ===\n{layer1}"),
            format!("=== Layer 2 ===\n{layer2}"),
            format!("=== Layer 3 ===\n{layer3}"),
        ];
        if !layer4.is_empty() {
            sections.push(format!("=== Layer 4 ===\n{layer4}"));
        }

        sections.push("请直接开始写作，不要添加任何解释或说明。".to_owned());

        sections.join("\n\n")
    }

    /// Estimate the token count for a full prompt using the character heuristic.
    ///
    /// Delegates to [`moling_llm::budget::TokenBudget::estimate`].
    pub fn estimate_tokens(&self, prompt: &str) -> usize {
        moling_llm::budget::TokenBudget::estimate(prompt)
    }

    // ─────────────────────────────────────────────────────────────────
    // Legacy / Simple prompt builders (backward-compatible)
    // ─────────────────────────────────────────────────────────────────

    /// Build a chapter-generation prompt from context (simplified, backward-compatible).
    pub fn build_chapter_prompt(&self, ctx: &PromptContext) -> String {
        let mut parts = Vec::new();
        parts.push(format!(
            "你是一位{}小说作家，风格：{}。",
            ctx.genre, ctx.style
        ));
        parts.push("请根据以下信息续写下一章：".into());

        if let Some(ref summary) = ctx.previous_chapter_summary {
            parts.push(format!("上一章情节概要：{summary}"));
        }
        if !ctx.active_characters.is_empty() {
            parts.push(format!(
                "当前活跃角色：{}",
                ctx.active_characters.join("、")
            ));
        }
        if !ctx.active_secrets.is_empty() {
            parts.push(format!("当前悬念：{}", ctx.active_secrets.join("；")));
        }
        if let Some(ref instruction) = ctx.user_instruction {
            parts.push(format!("用户指示：{instruction}"));
        }
        parts.push("请生成下一章内容（1000-2000字），保持情节连贯，人物行为一致：".into());
        parts.join("\n")
    }

    /// Build a prompt for card-based direction.
    pub fn build_direction_prompt(&self, card_text: &str) -> String {
        format!(
            "你正在写小说。根据以下创作方向卡，构思下一步情节发展：\n{card_text}\n请生成 3 个可行的情节发展方案（每个 50 字以内）。"
        )
    }

    /// Build a revision prompt.
    pub fn build_revision_prompt(&self, original: &str, instruction: &str) -> String {
        format!("请根据以下指示修改文本：\n{instruction}\n\n原文本：\n{original}\n\n修改后的文本：")
    }

    /// Build a vault-analysis prompt for extracting characters, timeline, promises, world details.
    pub fn build_analysis_prompt(&self, chapter_content: &str, project_context: &str) -> String {
        format!(
            "请分析以下章节内容，提取：\n1) 人物出场与行为\n2) 时间线事件\n3) 伏笔设定\n4) 世界观细节\n\n项目背景：{project_context}\n\n章节内容：\n{chapter_content}"
        )
    }

    /// Build a character-specific prompt for individual character analysis.
    pub fn build_character_prompt(
        &self,
        character_name: &str,
        character_role: Option<&str>,
        character_description: Option<&str>,
        recent_appearances: &[String],
    ) -> String {
        let mut parts: Vec<String> = Vec::new();
        parts.push(format!("你正在分析小说角色「{character_name}」。"));

        if let Some(role) = character_role {
            parts.push(format!("角色定位：{role}"));
        }
        if let Some(desc) = character_description {
            parts.push(format!("角色描述：{desc}"));
        }

        if !recent_appearances.is_empty() {
            let recent = recent_appearances.join("\n---\n");
            parts.push(format!("近期出场记录：\n{recent}"));
        }

        parts.push(
            "请分析该角色的：\n\
             1) 当前心理状态与动机\n\
             2) 与其他角色的关系动态\n\
             3) 可能的发展方向\n\
             4) 潜在的冲突点"
                .to_owned(),
        );

        parts.join("\n\n")
    }

    /// Build a plot promise prompt for advancing, redeeming, or canceling a promise.
    pub fn build_plot_promise_prompt(
        &self,
        promise_description: &str,
        promise_type: Option<&str>,
        action: PlotPromiseAction,
        context: Option<&str>,
    ) -> String {
        let action_label = match action {
            PlotPromiseAction::Advance => "推进",
            PlotPromiseAction::Redeem => "兑现",
            PlotPromiseAction::Cancel => "取消/废除",
        };

        let mut parts: Vec<String> = Vec::new();
        parts.push(format!("伏笔：{promise_description}"));

        if let Some(ptype) = promise_type {
            parts.push(format!("类型：{ptype}"));
        }

        if let Some(ctx) = context {
            parts.push(format!("上下文：{ctx}"));
        }

        parts.push(format!(
            "请在下一章中{action_label}这个伏笔。\n\
             要求：\n\
             1) 自然地融入情节\n\
             2) 保持与已有设定的连贯性\n\
             3) 不要过于突兀"
        ));

        parts.join("\n\n")
    }

    /// Build a world-building integration prompt.
    pub fn build_world_building_prompt(
        &self,
        world_rules: &[WorldRuleInfo],
        current_scene: Option<&str>,
    ) -> String {
        let mut parts: Vec<String> = Vec::new();
        parts.push("请确保下一章的创作符合以下世界观设定：".to_owned());

        let rules_text: Vec<String> = world_rules
            .iter()
            .map(|w| {
                let mut line = format!("- {}", w.term);
                if let Some(ref desc) = w.description {
                    line.push_str(&format!("：{desc}"));
                }
                if let Some(ref cat) = w.category {
                    line.push_str(&format!("（类别：{cat}）"));
                }
                line
            })
            .collect();
        parts.push(rules_text.join("\n"));

        if let Some(scene) = current_scene {
            parts.push(format!("\n当前场景：{scene}"));
        }

        parts.push(
            "请在写作中：\n\
             1) 自然地展示世界观要素\n\
             2) 避免违反已设定的规则\n\
             3) 可以通过角色视角逐步揭示世界观"
                .to_owned(),
        );

        parts.join("\n\n")
    }

    /// Build a genre-aware writing style prompt.
    pub fn build_genre_style_prompt(
        &self,
        genre: &str,
        style: Option<&str>,
        additional_notes: &[String],
    ) -> String {
        let genre_guidance = match genre {
            "fantasy" | "奇幻" => "注重氛围渲染，描写细腻，魔法/超自然元素自然融入",
            "scifi" | "科幻" => "注重逻辑自洽，科技设定清晰，推理性强",
            "romance" | "言情" => "注重情感描写，内心活动丰富，对话自然流畅",
            "horror" | "悬疑" | "恐怖" => "注重氛围营造，节奏控制，信息逐步释放",
            "martial" | "武侠" | "仙侠" => "注重动作描写，招式清晰，意境深远",
            "urban" | "都市" => "注重生活质感，对话真实，情节紧凑",
            "historical" | "历史" => "注重历史细节，语言得体，背景真实",
            _ => "注重情节推进，人物塑造鲜明",
        };

        let mut parts: Vec<String> = Vec::new();
        parts.push(format!("类型：{genre}"));
        parts.push(format!("写作指导：{genre_guidance}"));

        if let Some(st) = style {
            parts.push(format!("文风要求：{st}"));
        }

        if !additional_notes.is_empty() {
            parts.push(
                "额外要求：\n".to_owned()
                    + &additional_notes
                        .iter()
                        .map(|n| format!("- {n}"))
                        .collect::<Vec<_>>()
                        .join("\n"),
            );
        }

        parts.join("\n\n")
    }
}

impl Default for PromptService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// PlotPromiseAction enum
// ---------------------------------------------------------------------------

/// Action to perform on a plot promise.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlotPromiseAction {
    /// Advance the promise (move it forward without full resolution).
    Advance,
    /// Redeem/fulfill the promise.
    Redeem,
    /// Cancel or negate the promise.
    Cancel,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // ── Layer 0 tests ──

    #[test]
    fn test_layer0() {
        let svc = PromptService::new();
        let l0 = svc.build_layer0(42);
        assert!(l0.contains("42"));
        assert!(l0.contains("网络小说作家"));
    }

    // ── Layer 1 tests ──

    #[test]
    fn test_layer1_full() {
        let svc = PromptService::new();
        let l1 = svc.build_layer1(
            "测试小说",
            "第3章 黎明",
            Some("张三"),
            Some("王城"),
            Some("清晨"),
            "上一章主角逃出了城堡。",
            &["必须保持主角性格一致".to_owned()],
            &["避免引入新角色".to_owned()],
            &["钩子1".to_owned(), "钩子2".to_owned()],
        );
        assert!(l1.contains("测试小说"));
        assert!(l1.contains("第3章 黎明"));
        assert!(l1.contains("张三"));
        assert!(l1.contains("王城"));
        assert!(l1.contains("清晨"));
        assert!(l1.contains("必须保持"));
        assert!(l1.contains("必须避免"));
        assert!(l1.contains("钩子1"));
        assert!(l1.contains("钩子2"));
    }

    #[test]
    fn test_layer1_minimal() {
        let svc = PromptService::new();
        let l1 = svc.build_layer1("项目", "标题", None, None, None, "", &[], &[], &[]);
        assert!(l1.contains("项目"));
        assert!(l1.contains("标题"));
        // Should not contain anchor section
        assert!(!l1.contains("锚点"));
    }

    #[test]
    fn test_layer1_hooks_capped_at_3() {
        let svc = PromptService::new();
        let hooks: Vec<String> = (1..=5).map(|i| format!("钩子{i}")).collect();
        let l1 = svc.build_layer1("p", "c", None, None, None, "", &[], &[], &hooks);
        assert!(l1.contains("钩子1"));
        assert!(l1.contains("钩子3"));
        assert!(!l1.contains("钩子4")); // capped
        assert!(!l1.contains("钩子5")); // capped
    }

    // ── Layer 2 tests ──

    #[test]
    fn test_layer2_full() {
        let svc = PromptService::new();
        let characters = vec![CharacterInfo {
            name: "Alice".into(),
            role: Some("主角".into()),
            description: Some("勇敢的战士".into()),
            traits: vec!["勇敢".into(), "善良".into(), "冲动".into(), "幽默".into()],
            emotion: Some("焦虑".into()),
        }];
        let promises = vec![PlotPromiseInfo {
            description: "国王的秘密".into(),
            promise_type: Some("人物".into()),
            status: Some("pending".into()),
            urgency: Some("高".into()),
        }];
        let timeline = vec![TimelineEventInfo {
            event: "大战爆发".into(),
            description: Some("王国军队与黑暗势力交战".into()),
            impact: Some("改变了王国格局".into()),
        }];
        let world = vec![WorldRuleInfo {
            term: "魔法石".into(),
            description: Some("蕴含魔力的石头".into()),
            category: Some("物品".into()),
        }];

        let l2 = svc.build_layer2(&characters, &promises, &timeline, &world);
        assert!(l2.contains("Alice"));
        assert!(l2.contains("主角"));
        assert!(l2.contains("勇敢")); // trait
        assert!(l2.contains("焦虑")); // emotion
        assert!(!l2.contains("幽默")); // trait capped at 3
        assert!(l2.contains("国王的秘密"));
        assert!(l2.contains("大战爆发"));
        assert!(l2.contains("魔法石"));
    }

    #[test]
    fn test_layer2_empty() {
        let svc = PromptService::new();
        let l2 = svc.build_layer2(&[], &[], &[], &[]);
        assert!(l2.contains("暂无 vault 数据"));
    }

    // ── Layer 3 tests ──

    #[test]
    fn test_layer3_with_cards_and_scheme() {
        let svc = PromptService::new();
        let cards = vec![CardInfo {
            name: "反转卡".into(),
            direction_type: Some("plot".into()),
            direction_text: Some("剧情出现意外转折".into()),
            rarity: Some("rare".into()),
        }];
        let mut weight_map = HashMap::new();
        weight_map.insert("反转卡".to_owned(), 2.5);

        let scheme = WeavingScheme {
            description: Some("反转为主".into()),
            order: vec!["反差描写".into(), "情绪深度".into()],
            emphasis: Some("情感冲击".into()),
        };

        let l3 = svc.build_layer3(&cards, &weight_map, Some(&scheme));
        assert!(l3.contains("反转卡"));
        assert!(l3.contains("2.50"));
        assert!(l3.contains("反转为主"));
        assert!(l3.contains("反差描写 → 情绪深度"));
        assert!(l3.contains("情感冲击"));
    }

    #[test]
    fn test_layer3_empty() {
        let svc = PromptService::new();
        let l3 = svc.build_layer3(&[], &HashMap::new(), None);
        assert!(l3.contains("暂无卡牌方向"));
    }

    // ── Layer 4 tests ──

    #[test]
    fn test_layer4_full() {
        let svc = PromptService::new();
        let fp = StyleFingerprint {
            avg_sentence_length: Some(25.0),
            dialogue_ratio: Some(0.5),
            dominant_pov: Some("third".into()),
            avg_paragraph_length: Some(80.0),
            exclamation_density: Some(6.0),
        };
        let l4 = svc.build_layer4(Some(&fp));
        assert!(l4.contains("风格约束"));
        assert!(l4.contains("短句为主"));
        assert!(l4.contains("对话驱动"));
        assert!(l4.contains("第三人称视角"));
        assert!(l4.contains("短段落"));
        assert!(l4.contains("感叹号"));
    }

    #[test]
    fn test_layer4_none() {
        let svc = PromptService::new();
        assert_eq!(svc.build_layer4(None), "");
    }

    #[test]
    fn test_layer4_empty_fingerprint() {
        let svc = PromptService::new();
        let fp = StyleFingerprint::default();
        assert_eq!(svc.build_layer4(Some(&fp)), "");
    }

    #[test]
    fn test_layer4_medium_sentence() {
        let svc = PromptService::new();
        let fp = StyleFingerprint {
            avg_sentence_length: Some(40.0),
            ..Default::default()
        };
        let l4 = svc.build_layer4(Some(&fp));
        assert!(l4.contains("中等句长"));
    }

    #[test]
    fn test_layer4_long_sentence() {
        let svc = PromptService::new();
        let fp = StyleFingerprint {
            avg_sentence_length: Some(60.0),
            ..Default::default()
        };
        let l4 = svc.build_layer4(Some(&fp));
        assert!(l4.contains("长句为主"));
    }

    // ── Full prompt tests ──

    #[test]
    fn test_build_full_prompt() {
        let svc = PromptService::new();
        let input = FullPromptInput {
            chapter_number: 5,
            project_name: "测试项目".into(),
            chapter_title: "第五章 决战".into(),
            pov_character: Some("主角".into()),
            location: Some("战场".into()),
            time_period: Some("黄昏".into()),
            summary: "上一章战斗开始。".into(),
            must_hold: vec!["保持紧张感".into()],
            must_not: vec!["不要死亡".into()],
            unresolved_hooks: vec!["神秘人物身份".into()],
            characters: vec![CharacterInfo {
                name: "战士".into(),
                role: Some("主角".into()),
                ..Default::default()
            }],
            plot_promises: vec![],
            timeline: vec![],
            world_rules: vec![],
            cards: vec![],
            weight_map: HashMap::new(),
            weaving_scheme: None,
            style_fingerprint: Some(StyleFingerprint {
                avg_sentence_length: Some(35.0),
                ..Default::default()
            }),
        };

        let prompt = svc.build_full_prompt(&input);
        assert!(prompt.contains("=== Layer 0 ==="));
        assert!(prompt.contains("=== Layer 1 ==="));
        assert!(prompt.contains("=== Layer 2 ==="));
        assert!(prompt.contains("=== Layer 3 ==="));
        assert!(prompt.contains("=== Layer 4 ==="));
        assert!(prompt.contains("网络小说作家"));
        assert!(prompt.contains("测试项目"));
        assert!(prompt.contains("不要添加任何解释"));
    }

    #[test]
    fn test_build_full_prompt_no_layer4() {
        let svc = PromptService::new();
        let input = FullPromptInput {
            chapter_number: 1,
            project_name: "项目".into(),
            chapter_title: "标题".into(),
            ..Default::default()
        };
        let prompt = svc.build_full_prompt(&input);
        assert!(prompt.contains("=== Layer 0 ==="));
        assert!(!prompt.contains("=== Layer 4 ==="));
    }

    // ── Legacy / simple builder tests ──

    #[test]
    fn test_build_chapter_prompt() {
        let svc = PromptService::new();
        let ctx = PromptContext {
            genre: "fantasy".into(),
            style: "epic".into(),
            previous_chapter_summary: Some("The hero arrived at the castle.".into()),
            active_characters: vec!["Gandalf".into()],
            active_secrets: vec!["The ring is lost".into()],
            user_instruction: Some("Make it dramatic".into()),
        };
        let prompt = svc.build_chapter_prompt(&ctx);
        assert!(prompt.contains("fantasy"));
        assert!(prompt.contains("Gandalf"));
        assert!(prompt.contains("dramatic"));
    }

    #[test]
    fn test_build_direction_prompt() {
        let svc = PromptService::new();
        let p = svc.build_direction_prompt("introduce a plot twist");
        assert!(p.contains("创作方向"));
    }

    #[test]
    fn test_build_revision_prompt() {
        let svc = PromptService::new();
        let p = svc.build_revision_prompt("old text", "make it shorter");
        assert!(p.contains("old text"));
        assert!(p.contains("make it shorter"));
    }

    // ── Character prompt tests ──

    #[test]
    fn test_build_character_prompt() {
        let svc = PromptService::new();
        let p = svc.build_character_prompt(
            "Alice",
            Some("主角"),
            Some("勇敢的战士"),
            &["章节1出场".into(), "章节2战斗".into()],
        );
        assert!(p.contains("Alice"));
        assert!(p.contains("主角"));
        assert!(p.contains("勇敢的战士"));
        assert!(p.contains("章节1出场"));
        assert!(p.contains("章节2战斗"));
        assert!(p.contains("心理状态"));
    }

    // ── Plot promise prompt tests ──

    #[test]
    fn test_build_plot_promise_prompt_advance() {
        let svc = PromptService::new();
        let p = svc.build_plot_promise_prompt(
            "国王的秘密身份",
            Some("人物"),
            PlotPromiseAction::Advance,
            Some("国王最近行为古怪"),
        );
        assert!(p.contains("国王的秘密身份"));
        assert!(p.contains("人物"));
        assert!(p.contains("推进"));
        assert!(p.contains("行为古怪"));
    }

    #[test]
    fn test_build_plot_promise_prompt_redeem() {
        let svc = PromptService::new();
        let p = svc.build_plot_promise_prompt("预言应验", None, PlotPromiseAction::Redeem, None);
        assert!(p.contains("兑现"));
    }

    #[test]
    fn test_build_plot_promise_prompt_cancel() {
        let svc = PromptService::new();
        let p = svc.build_plot_promise_prompt("预言应验", None, PlotPromiseAction::Cancel, None);
        assert!(p.contains("取消"));
    }

    // ── World-building prompt tests ──

    #[test]
    fn test_build_world_building_prompt() {
        let svc = PromptService::new();
        let rules = vec![WorldRuleInfo {
            term: "魔力".into(),
            description: Some("世界中的能量源".into()),
            category: Some("魔法".into()),
        }];
        let p = svc.build_world_building_prompt(&rules, Some("魔法学院"));
        assert!(p.contains("魔力"));
        assert!(p.contains("能量源"));
        assert!(p.contains("魔法学院"));
        assert!(p.contains("世界观设定"));
    }

    // ── Genre/style prompt tests ──

    #[test]
    fn test_build_genre_style_prompt() {
        let svc = PromptService::new();
        let p = svc.build_genre_style_prompt("奇幻", Some("史诗"), &["注意节奏".into()]);
        assert!(p.contains("奇幻"));
        assert!(p.contains("史诗"));
        assert!(p.contains("氛围渲染"));
        assert!(p.contains("注意节奏"));
    }

    #[test]
    fn test_build_genre_style_prompt_scifi() {
        let svc = PromptService::new();
        let p = svc.build_genre_style_prompt("scifi", None, &[]);
        assert!(p.contains("逻辑自洽"));
    }

    #[test]
    fn test_build_genre_style_prompt_unknown() {
        let svc = PromptService::new();
        let p = svc.build_genre_style_prompt("unknown_genre", None, &[]);
        assert!(p.contains("情节推进"));
    }

    // ── Token estimation test ──

    #[test]
    fn test_estimate_tokens() {
        let svc = PromptService::new();
        let tokens = svc.estimate_tokens("Hello world test");
        assert!(tokens > 0);
    }

    // ── PromptContext Default ──

    #[test]
    fn test_prompt_context_default() {
        let ctx = PromptContext::default();
        assert!(ctx.genre.is_empty());
        assert!(ctx.active_characters.is_empty());
    }
}
