//! Prompt templates — 5-layer structured prompt assembly and vault agent prompts.
//!
//! Implements the full prompt architecture matching Python's
//! `prompt_service.py` and `prompts/generation.py`:
//!
//! - [`PromptService`] — 5-layer assembly (Layer 0–4) for chapter generation
//! - [`PromptBuilder`] — convenience wrappers for chapter/direction/revision/analysis
//! - [`VaultAgent`] — domain-specific prompts for Plot/Character/Dialogue/Style/World agents
//! - [`PromptLibrary`] — pre-built message templates

use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// Context for chapter generation (convenience struct for [`PromptBuilder`]).
#[derive(Debug, Clone)]
pub struct ChapterContext {
    /// Genre of the work (e.g. "玄幻", "都市").
    pub genre: String,
    /// Writing style description.
    pub style: String,
    /// Summary of the previous chapter.
    pub previous_summary: Option<String>,
    /// List of active character names.
    pub active_characters: Vec<String>,
    /// Pending plot secrets / unresolved hooks.
    pub pending_secrets: Vec<String>,
    /// Card direction texts.
    pub card_directions: Vec<String>,
    /// Optional user-provided instruction.
    pub user_instruction: Option<String>,
}

/// Context for chapter direction generation.
#[derive(Debug, Clone)]
pub struct DirectionContext {
    /// The card direction text.
    pub card_text: String,
    /// Optional broader chapter context.
    pub chapter_context: Option<String>,
}

// ---------------------------------------------------------------------------
// Vault entry types (for Layer 2)
// ---------------------------------------------------------------------------

/// A character entry from the vault.
#[derive(Debug, Clone, Default)]
pub struct VaultCharacter {
    pub name: String,
    pub role: Option<String>,
    pub description: Option<String>,
    pub traits: Vec<String>,
    pub emotion: Option<String>,
}

/// A plot promise (foreshadowing) entry.
#[derive(Debug, Clone, Default)]
pub struct VaultPlotPromise {
    pub description: String,
    pub promise_type: Option<String>,
    pub status: Option<String>,
    pub urgency: Option<String>,
}

/// A timeline event entry.
#[derive(Debug, Clone, Default)]
pub struct VaultTimelineEvent {
    pub event: String,
    pub description: Option<String>,
    pub chapter_number: Option<u32>,
    pub is_key_event: bool,
    pub impact: Option<String>,
}

/// A world-building entry.
#[derive(Debug, Clone, Default)]
pub struct VaultWorldEntry {
    pub term: String,
    pub description: Option<String>,
    pub category: Option<String>,
}

// ---------------------------------------------------------------------------
// Card and weaving types (for Layer 3)
// ---------------------------------------------------------------------------

/// A direction card for generation.
#[derive(Debug, Clone, Default)]
pub struct DirectionCard {
    pub name: String,
    pub direction_type: Option<String>,
    pub direction_text: Option<String>,
    pub rarity: Option<String>,
}

/// A weaving scheme describing how to fuse multiple cards.
#[derive(Debug, Clone, Default)]
pub struct WeavingScheme {
    pub description: Option<String>,
    pub order: Vec<String>,
    pub emphasis: Option<String>,
}

/// Style fingerprint dimensions (for Layer 4).
#[derive(Debug, Clone, Default)]
pub struct StyleFingerprint {
    /// Average sentence length (characters).
    pub avg_sentence_length: Option<f64>,
    /// Dialogue ratio (0.0–1.0).
    pub dialogue_ratio: Option<f64>,
    /// Dominant point-of-view ("first", "second", "third").
    pub dominant_pov: Option<String>,
    /// Average paragraph length (characters).
    pub avg_paragraph_length: Option<f64>,
    /// Exclamation mark density (per 1000 chars).
    pub exclamation_density: Option<f64>,
}

// ===========================================================================
// PromptService — 5-layer prompt assembly
// ===========================================================================

/// Service for building structured 5-layer prompts.
///
/// Mirrors Python `PromptService` from `app/service/prompt_service.py`.
///
/// Layers:
/// - **Layer 0**: System instruction (~50 chars)
/// - **Layer 1**: Dynamic context — summary, anchors, hooks (~500 chars)
/// - **Layer 2**: Vault filtered data — characters, promises, timeline, world (~1500 chars)
/// - **Layer 3**: Card fusion direction (~300 chars)
/// - **Layer 4**: Style constraints (~200 chars, can be dropped)
pub struct PromptService;

impl PromptService {
    // ------------------------------------------------------------------
    // Layer 0: System Instruction
    // ------------------------------------------------------------------

    /// Build Layer 0: system instruction.
    ///
    /// A short (~50 char) role-setting line for the LLM.
    pub fn build_layer0(chapter_number: u32) -> String {
        format!("你是一位专业的网络小说作家。撰写第{chapter_number}章。")
    }

    // ------------------------------------------------------------------
    // Layer 1: Dynamic Context
    // ------------------------------------------------------------------

    /// Build Layer 1: dynamic context — summary, anchors, hooks.
    ///
    /// ~500 chars. Includes project name, chapter title, POV/location/time
    /// anchors, previous chapter summary, coherence constraints, and
    /// unresolved hooks.
    pub fn build_layer1(
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

        // Anchors (POV / location / time)
        let mut anchors: Vec<String> = Vec::new();
        if let Some(pov) = pov_character {
            if !pov.is_empty() {
                anchors.push(format!("视点：{pov}"));
            }
        }
        if let Some(loc) = location {
            if !loc.is_empty() {
                anchors.push(format!("地点：{loc}"));
            }
        }
        if let Some(time) = time_period {
            if !time.is_empty() {
                anchors.push(format!("时间：{time}"));
            }
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
            parts.push(format!(
                "【必须保持】\n{}",
                must_hold.iter().map(|h| format!("- {h}")).collect::<Vec<_>>().join("\n")
            ));
        }
        if !must_not.is_empty() {
            parts.push(format!(
                "【必须避免】\n{}",
                must_not.iter().map(|n| format!("- {n}")).collect::<Vec<_>>().join("\n")
            ));
        }

        // Top unresolved hooks (cap at 3)
        let active_hooks: Vec<&String> = unresolved_hooks.iter().take(3).collect();
        if !active_hooks.is_empty() {
            parts.push(format!(
                "【未收束钩子】\n{}",
                active_hooks.iter().map(|h| format!("- {h}")).collect::<Vec<_>>().join("\n")
            ));
        }

        parts.join("\n\n")
    }

    // ------------------------------------------------------------------
    // Layer 2: Vault Filtered Data
    // ------------------------------------------------------------------

    /// Build Layer 2: vault filtered data.
    ///
    /// Includes characters, plot promises, timeline events, and world rules.
    /// ~1500 chars target.
    pub fn build_layer2(
        characters: &[VaultCharacter],
        plot_promises: &[VaultPlotPromise],
        timeline: &[VaultTimelineEvent],
        world_rules: &[VaultWorldEntry],
    ) -> String {
        let mut sections: Vec<String> = Vec::new();

        // ── Characters ──
        if !characters.is_empty() {
            let char_lines: Vec<String> = characters
                .iter()
                .map(|c| {
                    let mut line = format!("- {}", c.name);
                    if let Some(ref role) = c.role {
                        if !role.is_empty() {
                            line.push_str(&format!(" ({role})"));
                        }
                    }
                    if let Some(ref desc) = c.description {
                        if !desc.is_empty() {
                            line.push_str(&format!("：{desc}"));
                        }
                    }
                    if !c.traits.is_empty() {
                        line.push_str(&format!(
                            "；特质：{}",
                            c.traits.iter().take(3).cloned().collect::<Vec<_>>().join("、")
                        ));
                    }
                    if let Some(ref emotion) = c.emotion {
                        if !emotion.is_empty() {
                            line.push_str(&format!("；情绪：{emotion}"));
                        }
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
                        if !ptype.is_empty() {
                            line.push_str(&format!(" [{ptype}]"));
                        }
                    }
                    if let Some(ref status) = p.status {
                        if !status.is_empty() {
                            line.push_str(&format!(" ({status})"));
                        }
                    }
                    if let Some(ref urgency) = p.urgency {
                        if !urgency.is_empty() {
                            line.push_str(&format!(" 紧迫度：{urgency}"));
                        }
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
                        if !tdesc.is_empty() {
                            line.push_str(&format!("：{tdesc}"));
                        }
                    }
                    if t.is_key_event {
                        line.push_str(" ⭐（关键事件）");
                    }
                    if let Some(ref impact) = t.impact {
                        if !impact.is_empty() {
                            line.push_str(&format!(" (影响：{impact})"));
                        }
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
                        if !category.is_empty() {
                            line.push_str(&format!(" [{category}]"));
                        }
                    }
                    if let Some(ref wdesc) = w.description {
                        if !wdesc.is_empty() {
                            line.push_str(&format!("：{wdesc}"));
                        }
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

    // ------------------------------------------------------------------
    // Layer 3: Card Fusion Direction
    // ------------------------------------------------------------------

    /// Build Layer 3: card fusion direction.
    ///
    /// Includes card details with weights and optional weaving scheme.
    /// ~300 chars target.
    pub fn build_layer3(
        cards: &[DirectionCard],
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
                        if !dtype.is_empty() {
                            line.push_str(&format!(" [{dtype}]"));
                        }
                    }
                    line.push_str(&format!(" (权重: {weight:.2})"));
                    if let Some(ref dtext) = card.direction_text {
                        if !dtext.is_empty() {
                            line.push_str(&format!("\n  方向：{dtext}"));
                        }
                    }
                    line
                })
                .collect();
            parts.push(format!("【卡牌融合方向】\n{}", card_lines.join("\n")));
        }

        if let Some(scheme) = weaving_scheme {
            let mut scheme_lines: Vec<String> = Vec::new();
            if let Some(ref desc) = scheme.description {
                if !desc.is_empty() {
                    scheme_lines.push(format!("方案：{desc}"));
                }
            }
            if !scheme.order.is_empty() {
                scheme_lines.push(format!(
                    "融合顺序：{}",
                    scheme.order.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(" → ")
                ));
            }
            if let Some(ref emphasis) = scheme.emphasis {
                if !emphasis.is_empty() {
                    scheme_lines.push(format!("侧重：{emphasis}"));
                }
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

    // ------------------------------------------------------------------
    // Layer 4: Style Constraints
    // ------------------------------------------------------------------

    /// Build Layer 4: style constraints.
    ///
    /// ~200 chars. Can be fully dropped during context budget truncation.
    /// Returns an empty string if no fingerprint is provided or no constraints
    /// are applicable.
    pub fn build_layer4(style_fingerprint: Option<&StyleFingerprint>) -> String {
        let fp = match style_fingerprint {
            Some(fp) => fp,
            None => return String::new(),
        };

        let mut lines: Vec<String> = vec!["【风格约束】".to_owned()];

        // Sentence complexity
        if let Some(avg_len) = fp.avg_sentence_length {
            if avg_len < 30.0 {
                lines.push("- 句式偏好：短句为主，简洁明快".to_owned());
            } else if avg_len < 50.0 {
                lines.push("- 句式偏好：中等句长，张弛有度".to_owned());
            } else {
                lines.push("- 句式偏好：长句为主，细腻描写".to_owned());
            }
        }

        // Dialogue ratio
        if let Some(dia_ratio) = fp.dialogue_ratio {
            if dia_ratio > 0.4 {
                lines.push("- 对话偏好：对话驱动，占比高".to_owned());
            } else if dia_ratio > 0.2 {
                lines.push("- 对话偏好：对话与叙述均衡".to_owned());
            } else {
                lines.push("- 对话偏好：叙述为主，对话精炼".to_owned());
            }
        }

        // POV
        if let Some(ref pov) = fp.dominant_pov {
            if !pov.is_empty() {
                let pov_label = match pov.as_str() {
                    "first" => "第一人称视角",
                    "second" => "第二人称视角",
                    "third" => "第三人称视角",
                    _ => &format!("{pov}视角"),
                };
                lines.push(format!("- 视角偏好：{pov_label}"));
            }
        }

        // Paragraph rhythm
        if let Some(avg_para) = fp.avg_paragraph_length {
            if avg_para < 100.0 {
                lines.push("- 段落节奏：短段落，节奏快".to_owned());
            } else if avg_para < 250.0 {
                lines.push("- 段落节奏：中等段落，节奏适中".to_owned());
            } else {
                lines.push("- 段落节奏：长段落，节奏舒缓".to_owned());
            }
        }

        // Punctuation density
        if let Some(excl) = fp.exclamation_density {
            if excl > 5.0 {
                lines.push("- 标点风格：情感强烈，感叹号使用偏多".to_owned());
            }
        }

        if lines.len() == 1 {
            return String::new(); // Only header, no actual constraints
        }

        lines.join("\n")
    }

    // ------------------------------------------------------------------
    // Combined Full Prompt
    // ------------------------------------------------------------------

    /// Build the full structured prompt combining all 5 layers.
    ///
    /// This is the primary entry point — assembles Layer 0 through Layer 4
    /// with proper section markers that enable [`ContextBudget`]'s layered
    /// truncation.
    ///
    /// # Arguments
    /// See individual `build_layer*` methods for parameter details.
    #[allow(clippy::too_many_arguments)]
    pub fn build_full_prompt(
        chapter_number: u32,
        project_name: &str,
        chapter_title: &str,
        pov_character: Option<&str>,
        location: Option<&str>,
        time_period: Option<&str>,
        summary: &str,
        must_hold: &[String],
        must_not: &[String],
        unresolved_hooks: &[String],
        characters: &[VaultCharacter],
        plot_promises: &[VaultPlotPromise],
        timeline: &[VaultTimelineEvent],
        world_rules: &[VaultWorldEntry],
        cards: &[DirectionCard],
        weight_map: &HashMap<String, f64>,
        weaving_scheme: Option<&WeavingScheme>,
        style_fingerprint: Option<&StyleFingerprint>,
    ) -> String {
        let layer0 = Self::build_layer0(chapter_number);
        let layer1 = Self::build_layer1(
            project_name,
            chapter_title,
            pov_character,
            location,
            time_period,
            summary,
            must_hold,
            must_not,
            unresolved_hooks,
        );
        let layer2 = Self::build_layer2(characters, plot_promises, timeline, world_rules);
        let layer3 = Self::build_layer3(cards, weight_map, weaving_scheme);
        let layer4 = Self::build_layer4(style_fingerprint);

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
}

// ===========================================================================
// PromptBuilder — convenience wrappers
// ===========================================================================

/// Builder for structured LLM prompts.
///
/// Provides quick methods for common prompt types: chapter generation,
/// direction cards, revision, and vault analysis.
pub struct PromptBuilder;

impl PromptBuilder {
    /// Build a chapter generation prompt from a [`ChapterContext`].
    pub fn build_chapter_prompt(ctx: &ChapterContext) -> String {
        let mut parts: Vec<String> = Vec::new();

        parts.push(format!(
            "你是一位专业的{}小说作家，写作风格为{}。",
            ctx.genre, ctx.style
        ));

        if let Some(ref summary) = ctx.previous_summary {
            parts.push(format!("【上一章概要】\n{summary}"));
        }

        if !ctx.active_characters.is_empty() {
            parts.push(format!(
                "【当前活跃角色】{}",
                ctx.active_characters.join("、")
            ));
        }

        if !ctx.pending_secrets.is_empty() {
            parts.push(format!(
                "【待推进悬念】\n{}",
                ctx.pending_secrets
                    .iter()
                    .enumerate()
                    .map(|(i, s)| format!("{}. {s}", i + 1))
                    .collect::<Vec<_>>()
                    .join("\n")
            ));
        }

        if !ctx.card_directions.is_empty() {
            parts.push(format!(
                "【创作方向卡】\n{}",
                ctx.card_directions.join("\n")
            ));
        }

        if let Some(ref instruction) = ctx.user_instruction {
            parts.push(format!("【用户指示】\n{instruction}"));
        }

        parts.push("请续写下一章内容（1000-2000字），保持情节连贯和人物行为一致：".to_owned());
        parts.join("\n\n")
    }

    /// Build a direction prompt from a card.
    pub fn build_direction_prompt(ctx: &DirectionContext) -> String {
        let mut prompt = format!(
            "你正在创作一部小说。\n\n【创作方向卡】\n{}\n\n请根据此方向卡，生成3个可行的具体情节发展方案（每个50-100字）：",
            ctx.card_text
        );
        if let Some(ref context) = ctx.chapter_context {
            if !context.is_empty() {
                prompt.push_str(&format!("\n\n【当前上下文】\n{context}"));
            }
        }
        prompt
    }

    /// Build a revision prompt.
    pub fn build_revision_prompt(original: &str, feedback: &str) -> String {
        format!(
            "请根据以下反馈修改文本：\n\n【修改要求】\n{feedback}\n\n【原文本】\n{original}\n\n请输出修改后的完整文本："
        )
    }

    /// Build an analysis prompt for vault extraction.
    ///
    /// Supports analysis types: "characters", "timeline", "plot_promises", "world",
    /// or a generic fallback for unknown types.
    pub fn build_analysis_prompt(text: &str, analysis_type: &str) -> String {
        let instruction = match analysis_type {
            "characters" => "提取所有出场角色及其行为、关系变化。",
            "timeline" => "提取所有时间线事件，标注时间点。",
            "plot_promises" => "识别所有伏笔设定及其当前状态。",
            "world" => "提取所有世界观细节、规则、设定。",
            _ => "综合分析：提取角色、事件、伏笔和世界观信息。",
        };

        format!(
            "你是一位小说分析专家。请仔细阅读以下文本，{instruction}\n\n【文本内容】\n{text}\n\n请输出结构化的分析结果。"
        )
    }

    // ------------------------------------------------------------------
    // Coherence check
    // ------------------------------------------------------------------

    /// Build a coherence check prompt.
    ///
    /// Used to verify that a newly generated chapter is consistent with
    /// the preceding story state.
    pub fn build_coherence_check_prompt(
        previous_summary: &str,
        new_content: &str,
        character_states: &str,
    ) -> String {
        format!(
            "你是一位小说连贯性审查专家。\n\n\
             【前情摘要】\n{previous_summary}\n\n\
             【角色状态】\n{character_states}\n\n\
             【新生成内容】\n{new_content}\n\n\
             请检查以下方面：\n\
             1. 情节连续性 — 事件发展是否符合前情\n\
             2. 角色一致性 — 角色行为是否符合其设定\n\
             3. 伏笔衔接 — 是否有矛盾或遗漏的伏笔\n\
             4. 节奏连贯 — 章节间节奏是否顺畅\n\n\
             如有问题请详细指出，如无问题请回复「通过」。"
        )
    }

    // ------------------------------------------------------------------
    // Direction scoring
    // ------------------------------------------------------------------

    /// Build a direction scoring prompt.
    ///
    /// Used to evaluate and rank candidate plot directions for a chapter.
    pub fn build_direction_scoring_prompt(
        directions: &[String],
        story_context: &str,
    ) -> String {
        let direction_items: String = directions
            .iter()
            .enumerate()
            .map(|(i, d)| format!("{}. {d}", i + 1))
            .collect::<Vec<_>>()
            .join("\n");

        format!(
            "你是一位小说编审。\n\n\
             【故事上下文】\n{story_context}\n\n\
             【候选方向】\n{direction_items}\n\n\
             请对每个候选方向打分（1-10分），考虑以下维度：\n\
             - 与现有情节的衔接度\n\
             - 角色发展的合理性\n\
             - 悬念铺垫的有效性\n\
             - 读者期待值\n\n\
             输出格式：\n\
             方向1: X分 - 简要理由\n\
             方向2: X分 - 简要理由\n\
             ...\n\
             推荐方向：方向N"
        )
    }
}

// ===========================================================================
// VaultAgent — domain-specific agent prompts
// ===========================================================================

/// Vault agent prompts for domain-specific content generation and analysis.
///
/// Provides prompts for five vault agents:
/// - **Plot** — story structure, conflicts, pacing
/// - **Character** — personality, arcs, relationships
/// - **Dialogue** — speech patterns, subtext, voice
/// - **Style** — prose rhythm, sentence variety, literary devices
/// - **World** — setting rules, consistency, lore
pub struct VaultAgent;

impl VaultAgent {
    // ------------------------------------------------------------------
    // Plot Agent
    // ------------------------------------------------------------------

    /// System prompt for the Plot agent.
    pub fn plot_system_prompt() -> &'static str {
        "你是一位小说结构专家，精通情节设计、冲突编排和节奏控制。你的建议应当具体、可操作，并附有推理。请使用中文回答。"
    }

    /// Generate a plot analysis prompt.
    pub fn plot_analyze(project_title: &str, genre: &str, chapters_content: &str) -> String {
        format!(
            "请分析小说《{project_title}》（{genre}）的情节健康度。\n\n\
             已有章节内容：\n{chapters_content}\n\n\
             请从以下维度分析：\n\
             1. 情节逻辑一致性 — 事件因果链条是否完整\n\
             2. 伏笔与铺垫 — 哪些伏笔已埋下、哪些可回收\n\
             3. 节奏控制 — 高潮与舒缓段落的分布\n\
             4. 角色动机合理性 — 行为是否与其目标一致\n\
             5. 潜在问题预警 — 情节漏洞、逻辑矛盾\n\n\
             输出结构化分析报告。"
        )
    }

    /// Generate a plot suggestion prompt.
    pub fn plot_suggest(story_state: &str, goal: &str) -> String {
        format!(
            "根据当前故事状态，为达成以下目标提供情节建议。\n\n\
             【故事状态】\n{story_state}\n\n\
             【目标】{goal}\n\n\
             请提供3个具体的情节发展方案，每个方案包含：\n\
             - 核心创意（1句话）\n\
             - 实施步骤（3-5步）\n\
             - 预期效果\n\
             - 潜在风险"
        )
    }

    // ------------------------------------------------------------------
    // Character Agent
    // ------------------------------------------------------------------

    /// System prompt for the Character agent.
    pub fn character_system_prompt() -> &'static str {
        "你是一位角色塑造专家，精通人物弧光设计、性格一致性和关系网络构建。你的建议应当基于具体情境，而非泛泛而谈。请使用中文回答。"
    }

    /// Generate a character creation prompt.
    pub fn character_create(genre: &str, role: &str, traits: &[String]) -> String {
        let traits_str = if traits.is_empty() {
            "自由创作".to_owned()
        } else {
            traits.join("、")
        };
        format!(
            "请为一部 {genre} 小说创建一个{role}角色。\n\n\
             性格特征：{traits_str}\n\n\
             请提供以下信息：\n\
             1. 角色姓名及含义\n\
             2. 外貌描述\n\
             3. 性格特点（含优缺点）\n\
             4. 背景故事（含关键事件）\n\
             5. 动机与目标（短期+长期）\n\
             6. 人际关系（与其他角色的互动模式）\n\
             7. 成长弧光（预期的变化轨迹）"
        )
    }

    /// Generate a character consistency check prompt.
    pub fn character_consistency_check(
        character_name: &str,
        character_profile: &str,
        chapter_content: &str,
    ) -> String {
        format!(
            "请检查角色「{character_name}」在新章中的表现是否符合其设定。\n\n\
             【角色设定】\n{character_profile}\n\n\
             【章节内容】\n{chapter_content}\n\n\
             检查要点：\n\
             1. 言行是否符合性格设定\n\
             2. 决策是否与动机一致\n\
             3. 情感反应是否合理\n\
             4. 与其他角色的互动是否符合关系设定\n\n\
             如有偏差请详细指出并给出修改建议。"
        )
    }

    // ------------------------------------------------------------------
    // Dialogue Agent
    // ------------------------------------------------------------------

    /// System prompt for the Dialogue agent.
    pub fn dialogue_system_prompt() -> &'static str {
        "你是一位对话写作专家，精通角色语音设计、潜台词表达和对话节奏。你的建议应当具体到词句层面。请使用中文回答。"
    }

    /// Generate a dialogue review prompt.
    pub fn dialogue_review(
        character_names: &[String],
        dialogue_text: &str,
        context: &str,
    ) -> String {
        let chars = character_names.join("、");
        format!(
            "请审查以下对话片段。\n\n\
             【出场角色】{chars}\n\
             【对话上下文】{context}\n\n\
             【对话内容】\n{dialogue_text}\n\n\
             审查要点：\n\
             1. 每人语音是否有辨识度\n\
             2. 对话是否推进了情节或揭示了角色\n\
             3. 是否有冗余或生硬的台词\n\
             4. 潜台词/弦外之音是否到位\n\
             5. 对话节奏如何\n\n\
             输出修改建议，必要时给出改写示例。"
        )
    }

    /// Generate a character voice definition prompt.
    pub fn dialogue_voice_define(character_name: &str, character_profile: &str) -> String {
        format!(
            "请为角色「{character_name}」设计其独特语音特征。\n\n\
             【角色设定】\n{character_profile}\n\n\
             请从以下维度定义：\n\
             1. 口头禅或惯用表达\n\
             2. 句式特点（长短、复杂程度）\n\
             3. 词汇范围（文雅/粗犷/专业/口语）\n\
             4. 对话习惯（直爽/迂回/沉默/话多）\n\
             5. 情绪表达方式\n\n\
             输出为主标记，可直接用于后续对话生成。"
        )
    }

    // ------------------------------------------------------------------
    // Style Agent
    // ------------------------------------------------------------------

    /// System prompt for the Style agent.
    pub fn style_system_prompt() -> &'static str {
        "你是一位文学风格分析专家，精通汉语文学的各种文体风格、修辞手法和叙事技巧。请使用中文回答。"
    }

    /// Generate a style analysis prompt.
    pub fn style_analyze(text: &str) -> String {
        format!(
            "请分析以下文本的文学风格特征。\n\n\
             【文本内容】\n{text}\n\n\
             请从以下维度分析：\n\
             1. 句长分布 — 平均句长、句长变化\n\
             2. 对话占比 — 对话与叙述的比例\n\
             3. 叙事视角 — 人称、内聚焦/外聚焦\n\
             4. 修辞手法 — 比喻、排比、设问等的使用\n\
             5. 段落节奏 — 段落长度、段落间过渡方式\n\
             6. 语言调性 — 严肃/诙谐/诗意/平实\n\n\
             输出结构化的文风指纹。"
        )
    }

    /// Generate a style imitation prompt.
    pub fn style_imitate(content: &str, style_reference: &str) -> String {
        format!(
            "请将以下内容改写为指定的文风。\n\n\
             【目标文风】\n{style_reference}\n\n\
             【待改写内容】\n{content}\n\n\
             要求：\n\
             - 保持原意不变\n\
             - 贴合目标文风的句式、节奏和用词\n\
             - 不要添加或删除关键信息\n\n\
             输出改写后的全文。"
        )
    }

    // ------------------------------------------------------------------
    // World Agent
    // ------------------------------------------------------------------

    /// System prompt for the World agent.
    pub fn world_system_prompt() -> &'static str {
        "你是一位世界观构建专家，擅长设计虚构世界的规则体系、历史脉络和地理设定。你的设定应当自洽且富有创意。请使用中文回答。"
    }

    /// Generate a world entry creation prompt.
    pub fn world_create(term: &str, category: &str, genre: &str) -> String {
        format!(
            "请为一部 {genre} 小说设计世界设定条目。\n\n\
             条目名称：{term}\n\
             类别：{category}\n\n\
             请提供：\n\
             1. 详细描述（200-300字）\n\
             2. 相关规则或约束\n\
             3. 与其他设定的关联\n\
             4. 对故事情节的可能影响\n\
             5. 潜在的冲突来源"
        )
    }

    /// Generate a world consistency check prompt.
    pub fn world_consistency_check(
        world_rules: &str,
        chapter_content: &str,
    ) -> String {
        format!(
            "请检查以下章节内容是否与世界观设定一致。\n\n\
             【世界观规则】\n{world_rules}\n\n\
             【章节内容】\n{chapter_content}\n\n\
             检查要点：\n\
             1. 是否有违反世界规则的情节\n\
             2. 角色能力是否超出设定范围\n\
             3. 物品/道具是否符合设定\n\
             4. 时间和空间逻辑是否一致\n\n\
             如有矛盾请指出并给出修正建议。"
        )
    }
}

// ===========================================================================
// PromptLibrary — pre-built message templates
// ===========================================================================

/// Collection of pre-built prompt templates organised by scenario.
///
/// Mirrors Python `PromptLibrary` from `app/llm/prompts.py`.
pub struct PromptLibrary;

/// System prompt presets (private).
const SYSTEM_WRITER: &str =
    "你是一位资深小说创作助手，擅长文学创作、角色塑造和情节设计。请根据用户的需求提供高质量、富有创意的写作内容。你的回答应当使用中文。";

const SYSTEM_WORLD_BUILDER: &str =
    "你是一位世界观构建专家，擅长设计虚构世界的规则、历史和地理。请根据用户的需求创建详细而自洽的世界设定。你的回答应当使用中文。";

const SYSTEM_CRITIQUE: &str =
    "你是一位资深文学编辑，擅长分析文本并提供建设性反馈。请从情节逻辑、角色塑造、节奏控制和语言表达等维度进行点评。你的回答应当使用中文。";

impl PromptLibrary {
    /// Build a system writer message.
    pub fn system_writer() -> super::client::ChatMessage {
        super::client::ChatMessage::system(SYSTEM_WRITER)
    }

    /// Build a system world-builder message.
    pub fn system_world_builder() -> super::client::ChatMessage {
        super::client::ChatMessage::system(SYSTEM_WORLD_BUILDER)
    }

    /// Build a system critique message.
    pub fn system_critique() -> super::client::ChatMessage {
        super::client::ChatMessage::system(SYSTEM_CRITIQUE)
    }

    /// Generate a detailed character profile.
    pub fn generate_character(
        genre: &str,
        role: &str,
        traits: &[String],
    ) -> Vec<super::client::ChatMessage> {
        let traits_str = if traits.is_empty() {
            "自由创作".to_owned()
        } else {
            traits.join("、")
        };
        vec![
            Self::system_writer(),
            super::client::ChatMessage::user(format!(
                "请为一部 {genre} 小说创建一个{role}角色。\n\n\
                 性格特征：{traits_str}\n\n\
                 请提供以下信息：\n\
                 1. 角色姓名及含义\n\
                 2. 外貌描述\n\
                 3. 性格特点\n\
                 4. 背景故事\n\
                 5. 动机与目标\n\
                 6. 人际关系\n\
                 7. 成长弧光"
            )),
        ]
    }

    /// Generate content for a new chapter.
    pub fn generate_chapter(
        project_title: &str,
        genre: &str,
        chapter_number: u32,
        chapter_title: &str,
        synopsis: &str,
        previous_summary: &str,
        direction_hints: &str,
    ) -> Vec<super::client::ChatMessage> {
        let mut messages = vec![
            Self::system_writer(),
            super::client::ChatMessage::user(format!(
                "你正在创作小说《{project_title}》（{genre}）。\n\n\
                 请撰写第 {chapter_number} 章：「{chapter_title}」\n\n\
                 故事简介：{synopsis}"
            )),
        ];

        if !previous_summary.is_empty() {
            messages.push(super::client::ChatMessage::assistant(format!(
                "上一章概要：{previous_summary}"
            )));
        }

        if !direction_hints.is_empty() {
            messages.push(super::client::ChatMessage::user(format!(
                "创作方向提示：{direction_hints}"
            )));
        }

        messages
    }

    /// Create a detailed world-building entry.
    pub fn generate_world_entry(
        term: &str,
        category: &str,
        genre: &str,
        existing_rules: Option<&[String]>,
    ) -> Vec<super::client::ChatMessage> {
        let mut messages = vec![
            Self::system_world_builder(),
            super::client::ChatMessage::user(format!(
                "请为一部 {genre} 小说设计世界设定条目。\n\n\
                 条目名称：{term}\n\
                 类别：{category}\n\n\
                 请提供：\n\
                 1. 详细描述\n\
                 2. 相关规则\n\
                 3. 与其他设定的关联"
            )),
        ];

        if let Some(rules) = existing_rules {
            if !rules.is_empty() {
                messages.push(super::client::ChatMessage::user(format!(
                    "已有规则参考：{}",
                    rules.join("、")
                )));
            }
        }

        messages
    }

    /// Analyse plot consistency and health.
    pub fn analyze_plot(
        project_title: &str,
        chapters_content: &str,
    ) -> Vec<super::client::ChatMessage> {
        vec![
            Self::system_critique(),
            super::client::ChatMessage::user(format!(
                "请分析小说《{project_title}》的情节健康度。\n\n\
                 已有章节内容：\n{chapters_content}\n\n\
                 请从以下维度分析：\n\
                 1. 情节逻辑一致性\n\
                 2. 伏笔与铺垫\n\
                 3. 节奏控制\n\
                 4. 角色动机合理性\n\
                 5. 潜在问题预警"
            )),
        ]
    }

    /// Expand a card direction into a rich description.
    pub fn generate_card_description(
        name: &str,
        direction_type: &str,
        direction_text: &str,
        genre: &str,
    ) -> Vec<super::client::ChatMessage> {
        vec![
            Self::system_writer(),
            super::client::ChatMessage::user(format!(
                "请为一张创作方向卡撰写描述。\n\n\
                 卡片名称：{name}\n\
                 方向类型：{direction_type}\n\
                 方向提示：{direction_text}\n\
                 作品题材：{genre}\n\n\
                 请用生动具体的语言描述这个创作方向，让作者能立即获得灵感。"
            )),
        ]
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // ── ChapterContext helpers ──

    fn sample_chapter_context() -> ChapterContext {
        ChapterContext {
            genre: "玄幻".into(),
            style: "细腻".into(),
            previous_summary: Some("主角突破境界，引来天劫。".into()),
            active_characters: vec!["叶凡".into(), "姬紫月".into()],
            pending_secrets: vec!["神秘玉佩的来历尚未揭晓".into()],
            card_directions: vec!["增加感情戏冲突".into()],
            user_instruction: Some("主角需要在这一章遇到一个转折点".into()),
        }
    }

    // ── PromptBuilder tests ──

    #[test]
    fn test_build_chapter_prompt() {
        let prompt = PromptBuilder::build_chapter_prompt(&sample_chapter_context());
        assert!(prompt.contains("玄幻"));
        assert!(prompt.contains("叶凡"));
        assert!(prompt.contains("神秘玉佩"));
        assert!(prompt.contains("转折点"));
    }

    #[test]
    fn test_build_direction_prompt() {
        let ctx = DirectionContext {
            card_text: "主角发现了一个隐藏的秘境".into(),
            chapter_context: Some("当前处于中期转折阶段".into()),
        };
        let prompt = PromptBuilder::build_direction_prompt(&ctx);
        assert!(prompt.contains("秘境"));
        assert!(prompt.contains("3个"));
        assert!(prompt.contains("中期转折"));
    }

    #[test]
    fn test_build_revision_prompt() {
        let prompt = PromptBuilder::build_revision_prompt("原文内容", "请缩短到500字");
        assert!(prompt.contains("原文内容"));
        assert!(prompt.contains("500字"));
    }

    #[test]
    fn test_build_analysis_prompt_characters() {
        let prompt = PromptBuilder::build_analysis_prompt("章节内容...", "characters");
        assert!(prompt.contains("角色"));
        assert!(prompt.contains("章节内容"));
    }

    #[test]
    fn test_build_analysis_prompt_default() {
        let prompt = PromptBuilder::build_analysis_prompt("test", "unknown");
        assert!(prompt.contains("综合分析"));
    }

    #[test]
    fn test_build_coherence_check_prompt() {
        let prompt = PromptBuilder::build_coherence_check_prompt(
            "前情摘要",
            "新内容",
            "角色状态",
        );
        assert!(prompt.contains("连贯性审查"));
        assert!(prompt.contains("前情摘要"));
        assert!(prompt.contains("新内容"));
    }

    #[test]
    fn test_build_direction_scoring_prompt() {
        let prompt = PromptBuilder::build_direction_scoring_prompt(
            &["方向A".into(), "方向B".into()],
            "故事上下文",
        );
        assert!(prompt.contains("方向A"));
        assert!(prompt.contains("方向B"));
        assert!(prompt.contains("打分"));
    }

    // ── PromptService tests ──

    #[test]
    fn test_build_layer0() {
        let layer = PromptService::build_layer0(42);
        assert!(layer.contains("42"));
        assert!(layer.contains("网络小说作家"));
    }

    #[test]
    fn test_build_layer1_basic() {
        let layer = PromptService::build_layer1(
            "测试项目",
            "测试章节",
            Some("张三"),
            Some("长安城"),
            Some("黄昏"),
            "前情提要...",
            &["保持A".into()],
            &["避免B".into()],
            &["悬念1".into(), "悬念2".into()],
        );
        assert!(layer.contains("测试项目"));
        assert!(layer.contains("测试章节"));
        assert!(layer.contains("张三"));
        assert!(layer.contains("长安城"));
        assert!(layer.contains("黄昏"));
        assert!(layer.contains("保持A"));
        assert!(layer.contains("避免B"));
        assert!(layer.contains("悬念1"));
        // Should cap unresolved hooks at 3
        assert!(!layer.contains("悬念3"));
    }

    #[test]
    fn test_build_layer2_empty() {
        let layer =
            PromptService::build_layer2(&[], &[], &[], &[]);
        assert!(layer.contains("暂无 vault 数据"));
    }

    #[test]
    fn test_build_layer2_with_data() {
        let characters = vec![VaultCharacter {
            name: "叶凡".into(),
            role: Some("主角".into()),
            description: Some("一个修炼者".into()),
            traits: vec!["勇敢".into(), "果断".into()],
            emotion: Some("坚定".into()),
        }];
        let promises = vec![VaultPlotPromise {
            description: "神秘玉佩的秘密".into(),
            promise_type: Some("主线".into()),
            status: Some("活跃".into()),
            urgency: Some("高".into()),
        }];
        let timeline = vec![VaultTimelineEvent {
            event: "突破金丹境".into(),
            description: Some("成功突破".into()),
            chapter_number: Some(5),
            is_key_event: true,
            impact: Some("实力大增".into()),
        }];
        let world = vec![VaultWorldEntry {
            term: "灵气".into(),
            description: Some("修炼的基础能量".into()),
            category: Some("能量体系".into()),
        }];

        let layer = PromptService::build_layer2(&characters, &promises, &timeline, &world);
        assert!(layer.contains("叶凡"));
        assert!(layer.contains("主角"));
        assert!(layer.contains("神秘玉佩"));
        assert!(layer.contains("突破金丹境"));
        assert!(layer.contains("关键事件"));
        assert!(layer.contains("灵气"));
    }

    #[test]
    fn test_build_layer3_empty() {
        let layer = PromptService::build_layer3(&[], &HashMap::new(), None);
        assert!(layer.contains("暂无卡牌方向"));
    }

    #[test]
    fn test_build_layer3_with_cards() {
        let cards = vec![DirectionCard {
            name: "感情升温".into(),
            direction_type: Some("感情".into()),
            direction_text: Some("主角与女主关系更进一步".into()),
            rarity: Some("稀有".into()),
        }];
        let mut weights = HashMap::new();
        weights.insert("感情升温".to_owned(), 0.8);

        let layer = PromptService::build_layer3(&cards, &weights, None);
        assert!(layer.contains("感情升温"));
        assert!(layer.contains("0.80"));
        assert!(layer.contains("关系更进一步"));
    }

    #[test]
    fn test_build_layer4_empty() {
        let layer = PromptService::build_layer4(None);
        assert!(layer.is_empty());
    }

    #[test]
    fn test_build_layer4_with_fingerprint() {
        let fp = StyleFingerprint {
            avg_sentence_length: Some(25.0),
            dialogue_ratio: Some(0.5),
            dominant_pov: Some("third".into()),
            avg_paragraph_length: Some(80.0),
            exclamation_density: Some(6.0),
        };
        let layer = PromptService::build_layer4(Some(&fp));
        assert!(layer.contains("短句为主"));
        assert!(layer.contains("对话驱动"));
        assert!(layer.contains("第三人称"));
        assert!(layer.contains("短段落"));
        assert!(layer.contains("感叹号"));
    }

    #[test]
    fn test_build_full_prompt() {
        let prompt = PromptService::build_full_prompt(
            10,
            "测试小说",
            "第十章标题",
            Some("主角"),
            Some("京城"),
            Some("午夜"),
            "前一章概要",
            &["保持连贯".into()],
            &["避免突兀".into()],
            &["悬念X".into()],
            &[],
            &[],
            &[],
            &[],
            &[],
            &HashMap::new(),
            None,
            None,
        );
        assert!(prompt.contains("=== Layer 0 ==="));
        assert!(prompt.contains("=== Layer 1 ==="));
        assert!(prompt.contains("=== Layer 2 ==="));
        assert!(prompt.contains("=== Layer 3 ==="));
        assert!(prompt.contains("直接开始写作"));
    }

    // ── VaultAgent tests ──

    #[test]
    fn test_plot_system_prompt() {
        let p = VaultAgent::plot_system_prompt();
        assert!(p.contains("小说结构"));
    }

    #[test]
    fn test_character_system_prompt() {
        let p = VaultAgent::character_system_prompt();
        assert!(p.contains("角色塑造"));
    }

    #[test]
    fn test_dialogue_system_prompt() {
        let p = VaultAgent::dialogue_system_prompt();
        assert!(p.contains("对话写作"));
    }

    #[test]
    fn test_style_system_prompt() {
        let p = VaultAgent::style_system_prompt();
        assert!(p.contains("文学风格"));
    }

    #[test]
    fn test_world_system_prompt() {
        let p = VaultAgent::world_system_prompt();
        assert!(p.contains("世界观构建"));
    }

    #[test]
    fn test_plot_analyze() {
        let prompt = VaultAgent::plot_analyze("测试", "玄幻", "内容");
        assert!(prompt.contains("测试"));
        assert!(prompt.contains("情节健康度"));
    }

    #[test]
    fn test_character_create() {
        let prompt = VaultAgent::character_create("玄幻", "主角", &["勇敢".into()]);
        assert!(prompt.contains("玄幻"));
        assert!(prompt.contains("主角"));
        assert!(prompt.contains("勇敢"));
    }

    #[test]
    fn test_dialogue_review() {
        let prompt =
            VaultAgent::dialogue_review(&["A".into()], "对话内容", "上下文");
        assert!(prompt.contains("A"));
        assert!(prompt.contains("对话内容"));
    }

    #[test]
    fn test_style_analyze() {
        let prompt = VaultAgent::style_analyze("测试文本");
        assert!(prompt.contains("句长分布"));
        assert!(prompt.contains("文学风格"));
    }

    #[test]
    fn test_world_create() {
        let prompt = VaultAgent::world_create("魔法", "体系", "奇幻");
        assert!(prompt.contains("魔法"));
        assert!(prompt.contains("体系"));
        assert!(prompt.contains("奇幻"));
    }

    // ── PromptLibrary tests ──

    #[test]
    fn test_generate_character() {
        let msgs = PromptLibrary::generate_character("玄幻", "主角", &["勇敢".into()]);
        assert_eq!(msgs.len(), 2);
        assert_eq!(msgs[0].role, "system");
        assert_eq!(msgs[1].role, "user");
        assert!(msgs[1].content.contains("玄幻"));
    }

    #[test]
    fn test_generate_chapter() {
        let msgs = PromptLibrary::generate_chapter(
            "测试", "玄幻", 1, "第一章", "简介", "前情", "方向",
        );
        assert!(msgs.len() >= 2);
        assert_eq!(msgs[0].role, "system");
    }

    #[test]
    fn test_generate_world_entry() {
        let msgs =
            PromptLibrary::generate_world_entry("魔法", "体系", "奇幻", None);
        assert_eq!(msgs.len(), 2);
        assert!(msgs[1].content.contains("魔法"));
    }

    #[test]
    fn test_analyze_plot() {
        let msgs = PromptLibrary::analyze_plot("测试", "内容");
        assert_eq!(msgs.len(), 2);
        assert!(msgs[1].content.contains("情节健康度"));
    }

    #[test]
    fn test_generate_card_description() {
        let msgs = PromptLibrary::generate_card_description(
            "卡片名", "剧情", "方向说明", "玄幻",
        );
        assert_eq!(msgs.len(), 2);
        assert!(msgs[1].content.contains("卡片名"));
    }
}
