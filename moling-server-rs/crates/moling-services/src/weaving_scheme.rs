//! 墨灵 (Moling) — Weaving Scheme Matching Service (编织方案匹配).
//!
//! Provides three weaving patterns (因果链/平行交替/主线+支线) + rule engine
//! + LLM fallback selection mechanism.
//!
//! Ported from Python `app/service/weaving_scheme.py`.

use std::sync::Arc;

use moling_llm::{ChatMessage, DeepSeekClient, DEFAULT_MODEL};

use serde::{Deserialize, Serialize};
use tracing::{info, warn};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CONFIDENCE_THRESHOLD: f64 = 0.3;
const WEIGHT_GAP_THRESHOLD: f64 = 0.20;

// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

/// A weaving pattern definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeavingPattern {
    pub name: String,
    pub mode: String,
    pub prompt_instruction: String,
    pub outline_template: serde_json::Value,
    pub description: String,
}

/// Minimal card info for weaving scheme matching.
#[derive(Debug, Clone)]
pub struct WeaveCard {
    pub id: i32,
    pub name: String,
    pub direction_text: Option<String>,
    pub direction_type: Option<String>,
    pub characters: Vec<serde_json::Value>,
    pub timeline_point: Option<String>,
}

/// Full weaving scheme result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeavingSchemeResult {
    pub mode: String,
    pub selected_scheme: serde_json::Value,
    pub selection_method: String,
    pub selection_confidence: f64,
    pub alternatives: Vec<serde_json::Value>,
    pub prompt_instruction: String,
    pub outline_template: serde_json::Value,
}

// ---------------------------------------------------------------------------
// WeavingSchemeService
// ---------------------------------------------------------------------------

/// Weaving scheme matching service.
///
/// Responsibilities:
/// - Select the best weaving pattern based on card count/weight/direction
/// - Rule engine as primary, LLM fallback as secondary
/// - Fill prompt instruction and outline template variables
#[derive(Clone)]
pub struct WeavingSchemeService {
    llm_client: Arc<DeepSeekClient>,
    llm_api_key: String,
}

impl WeavingSchemeService {
    /// Create a new WeavingSchemeService.
    pub fn new(llm_client: DeepSeekClient, llm_api_key: impl Into<String>) -> Self {
        Self {
            llm_client: Arc::new(llm_client),
            llm_api_key: llm_api_key.into(),
        }
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Main entry point: match weaving scheme based on cards, weights, and mode.
    pub async fn match_scheme(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
        req_mode: &str,
    ) -> WeavingSchemeResult {
        info!(
            "Matching weaving scheme: mode={req_mode}, cards_count={}, weights={weight_map:?}",
            cards.len()
        );

        if cards.is_empty() {
            return self.build_no_card_result(req_mode);
        }

        match req_mode {
            "none" | "single" => self.build_single_result(cards, weight_map, req_mode),
            "dual" => self.match_dual(cards, weight_map).await,
            "all" => self.match_all(cards, weight_map).await,
            _ => self.match_hybrid(cards, weight_map).await,
        }
    }

    // ------------------------------------------------------------------
    // Weaving pattern template library
    // ------------------------------------------------------------------

    /// Returns all available weaving patterns (immutable data).
    pub fn weaving_patterns(&self) -> Vec<WeavingPattern> {
        vec![
            WeavingPattern {
                name: "单段式".into(),
                mode: "single".into(),
                prompt_instruction: "本章为单一线索推进，不涉及多线编织。".into(),
                outline_template: serde_json::json!({
                    "part1": {"name": "单线推进", "weight": 1.0, "description": "单一叙事线索推进"}
                }),
                description: "单一线索推进，不涉及多线编织".into(),
            },
            WeavingPattern {
                name: "因果链".into(),
                mode: "single".into(),
                prompt_instruction: "本章按以下三段式结构推进：\n第一段【因】: 角色行动或事件触发（展示原因）\n第二段【果】: 触发后的连锁反应（推进后果）\n第三段【揭示】: 新的信息/认知浮现（为下一章埋钩子）".into(),
                outline_template: serde_json::json!({
                    "part1": {"name": "因", "weight": 0.35, "description": "角色行动/事件触发"},
                    "part2": {"name": "果", "weight": 0.40, "description": "连锁反应/后果推进"},
                    "part3": {"name": "揭示", "weight": 0.25, "description": "新信息浮现/章尾钩子"}
                }),
                description: "因果链编织模式：因→果→揭示三段式结构".into(),
            },
            WeavingPattern {
                name: "平行交替".into(),
                mode: "dual".into(),
                prompt_instruction: "本章有两条平行叙事线交替推进：\nA线（主）: {main_card_direction}\nB线（副）: {side_card_direction}\n\n以 A1→B1→A2→B2→A3→交汇 的节奏推进\n每条片段 300-500 字，交替 ≥ 2 轮\nA线和B线在章末交汇".into(),
                outline_template: serde_json::json!({
                    "segment1": {"name": "A线第一段", "weight": 0.20},
                    "segment2": {"name": "B线第一段", "weight": 0.20},
                    "segment3": {"name": "A线第二段(推进)", "weight": 0.20},
                    "segment4": {"name": "B线第二段(推进)", "weight": 0.20},
                    "segment5": {"name": "双线交汇/章尾钩子", "weight": 0.20}
                }),
                description: "平行交替编织模式：双线交替推进后交汇".into(),
            },
            WeavingPattern {
                name: "主线+支线".into(),
                mode: "dual".into(),
                prompt_instruction: "本章包含一条主线推进 + 一条支线点缀：\n主线（权重{main_weight}）: {main_card_direction}\n支线（权重{side_weight}）: {side_card_direction}\n主线占 70% 篇幅，支线占 30% 篇幅".into(),
                outline_template: serde_json::json!({
                    "part1": {"name": "主线启动", "weight": 0.25},
                    "part2": {"name": "支线插入", "weight": 0.15},
                    "part3": {"name": "主线推进", "weight": 0.30},
                    "part4": {"name": "主线高潮/冲突", "weight": 0.20},
                    "part5": {"name": "支线回扣/章尾钩子", "weight": 0.10}
                }),
                description: "主线+支线编织模式：主线为主，支线为辅".into(),
            },
            WeavingPattern {
                name: "因果链扩展".into(),
                mode: "all".into(),
                prompt_instruction: "本章按三段式因果链展开，三张卡分别对应：\n第一段【因 - {card_1_name}】: {card_1_direction}\n第二段【果 - {card_2_name}】: {card_2_direction}\n第三段【揭示 - {card_3_name}】: {card_3_direction}\n\n三段之间需有清晰的因果递进关系".into(),
                outline_template: serde_json::json!({
                    "part1": {"name": "因", "weight": 0.30, "description": "三卡中最具「因」属性的段落"},
                    "part2": {"name": "果", "weight": 0.40, "description": "因果连锁反应的展开"},
                    "part3": {"name": "揭示/交汇", "weight": 0.30, "description": "三卡交汇/章尾钩子"}
                }),
                description: "因果链扩展模式：三卡按因果递进排列".into(),
            },
            WeavingPattern {
                name: "平行交替+交汇".into(),
                mode: "all".into(),
                prompt_instruction: "本章有三条空间分布不同的叙事线交替推进：\nA线: {card_a_direction}\nB线: {card_b_direction}\nC线: {card_c_direction}\n\n以 A→B→C→A→B→交汇 的节奏推进\n三线在章末交汇".into(),
                outline_template: serde_json::json!({
                    "segment1": {"name": "A线叙事", "weight": 0.15},
                    "segment2": {"name": "B线叙事", "weight": 0.15},
                    "segment3": {"name": "C线叙事", "weight": 0.15},
                    "segment4": {"name": "A线推进", "weight": 0.15},
                    "segment5": {"name": "B线推进", "weight": 0.15},
                    "segment6": {"name": "三线交汇/章尾钩子", "weight": 0.25}
                }),
                description: "平行交替+交汇模式：三线交替推进后交汇".into(),
            },
            WeavingPattern {
                name: "主线+双支线".into(),
                mode: "all".into(),
                prompt_instruction: "本章包含一条主线推进 + 两条支线点缀：\n主线: {main_card_direction}\n支线1: {side_card_1_direction}\n支线2: {side_card_2_direction}\n主线占 60% 篇幅，两条支线各占 20% 篇幅".into(),
                outline_template: serde_json::json!({
                    "part1": {"name": "主线启动", "weight": 0.20},
                    "part2": {"name": "支线1插入", "weight": 0.10},
                    "part3": {"name": "主线推进", "weight": 0.25},
                    "part4": {"name": "支线2插入", "weight": 0.10},
                    "part5": {"name": "主线高潮/冲突", "weight": 0.20},
                    "part6": {"name": "双支线回扣/章尾钩子", "weight": 0.15}
                }),
                description: "主线+双支线模式：一条主线为主，两条支线为辅".into(),
            },
        ]
    }

    // ------------------------------------------------------------------
    // Mode matching
    // ------------------------------------------------------------------

    async fn match_dual(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> WeavingSchemeResult {
        let sorted_cards = self.sort_by_weight(cards, weight_map);
        let (mut selected, mut method, mut confidence, alternatives) =
            self.select_by_rules(&sorted_cards, weight_map);

        if method == "llm" {
            match self.select_by_llm(&sorted_cards, weight_map).await {
                Ok((pat, conf)) => {
                    selected = pat;
                    confidence = conf;
                    method = "llm".to_string();
                }
                Err(e) => {
                    warn!("LLM fallback failed, using rule-based default: {e}");
                    selected = alternatives
                        .first()
                        .cloned()
                        .unwrap_or_else(|| self.get_pattern("单段式"));
                    method = "rule".to_string();
                    confidence = self.calc_confidence(&sorted_cards, weight_map);
                }
            }
        }

        let prompt = self.build_prompt_instruction(&selected, &sorted_cards, weight_map);

        WeavingSchemeResult {
            mode: "dual".into(),
            selected_scheme: serde_json::to_value(&selected).unwrap_or_default(),
            selection_method: method.to_string(),
            selection_confidence: (confidence * 10000.0).round() / 10000.0,
            alternatives: alternatives
                .iter()
                .map(|a| serde_json::to_value(a).unwrap_or_default())
                .collect(),
            prompt_instruction: prompt,
            outline_template: selected.outline_template,
        }
    }

    async fn match_all(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> WeavingSchemeResult {
        let sorted_cards = self.sort_by_weight(cards, weight_map);
        let (mut selected, mut method, mut confidence, alternatives) =
            self.select_by_rules(&sorted_cards, weight_map);

        if method == "llm" {
            match self.select_by_llm(&sorted_cards, weight_map).await {
                Ok((pat, conf)) => {
                    selected = pat;
                    confidence = conf;
                    method = "llm".to_string();
                }
                Err(e) => {
                    warn!("LLM fallback failed (all mode), using rule-based default: {e}");
                    selected = alternatives
                        .first()
                        .cloned()
                        .unwrap_or_else(|| self.get_pattern("单段式"));
                    method = "rule".to_string();
                    confidence = self.calc_confidence(&sorted_cards, weight_map);
                }
            }
        }

        let prompt = self.build_prompt_instruction(&selected, &sorted_cards, weight_map);

        WeavingSchemeResult {
            mode: "all".into(),
            selected_scheme: serde_json::to_value(&selected).unwrap_or_default(),
            selection_method: method.to_string(),
            selection_confidence: (confidence * 10000.0).round() / 10000.0,
            alternatives: alternatives
                .iter()
                .map(|a| serde_json::to_value(a).unwrap_or_default())
                .collect(),
            prompt_instruction: prompt,
            outline_template: selected.outline_template,
        }
    }

    async fn match_hybrid(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> WeavingSchemeResult {
        let sorted_cards = self.sort_by_weight(cards, weight_map);

        if sorted_cards.len() <= 1 {
            return self.build_single_result(&sorted_cards, weight_map, "hybrid");
        }

        if sorted_cards.len() == 2 {
            return self.match_dual(&sorted_cards, weight_map).await;
        }

        self.match_all(&sorted_cards, weight_map).await
    }

    // ------------------------------------------------------------------
    // Rule engine
    // ------------------------------------------------------------------

    fn select_by_rules(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> (WeavingPattern, String, f64, Vec<WeavingPattern>) {
        let card_count = cards.len();

        if card_count <= 1 {
            let pat = self.get_pattern("单段式");
            return (pat, "rule".into(), 1.0, Vec::new());
        }

        let confidence = self.calc_confidence(cards, weight_map);

        if card_count == 2 {
            self.rules_dual(cards, weight_map, confidence)
        } else {
            self.rules_all(cards, weight_map, confidence)
        }
    }

    fn rules_dual(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
        confidence: f64,
    ) -> (WeavingPattern, String, f64, Vec<WeavingPattern>) {
        if confidence < CONFIDENCE_THRESHOLD {
            let pat = self.get_pattern("平行交替");
            let alt1 = self.get_pattern("因果链");
            let alt2 = self.get_pattern("主线+支线");
            return (pat, "llm".into(), confidence, vec![alt1, alt2]);
        }

        let w0 = weight_map.get(&cards[0].id).copied().unwrap_or(0.0);
        let w1 = weight_map.get(&cards[1].id).copied().unwrap_or(0.0);
        let weight_gap = (w0 - w1).abs();
        let same_pov = self.check_same_pov(cards);

        if weight_gap >= WEIGHT_GAP_THRESHOLD
            || (weight_gap - WEIGHT_GAP_THRESHOLD).abs() < 1e-10
        {
            let pat = self.get_pattern("主线+支线");
            let alt1 = self.get_pattern("平行交替");
            let alt2 = self.get_pattern("因果链");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        } else if same_pov {
            let pat = self.get_pattern("因果链");
            let alt1 = self.get_pattern("主线+支线");
            let alt2 = self.get_pattern("平行交替");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        } else {
            let pat = self.get_pattern("平行交替");
            let alt1 = self.get_pattern("因果链");
            let alt2 = self.get_pattern("主线+支线");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        }
    }

    fn rules_all(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
        confidence: f64,
    ) -> (WeavingPattern, String, f64, Vec<WeavingPattern>) {
        if confidence < CONFIDENCE_THRESHOLD {
            let pat = self.get_pattern("平行交替+交汇");
            let alt1 = self.get_pattern("因果链扩展");
            let alt2 = self.get_pattern("主线+双支线");
            return (pat, "llm".into(), confidence, vec![alt1, alt2]);
        }

        let has_temporal = self.check_temporal_relation(cards);

        if has_temporal {
            let pat = self.get_pattern("因果链扩展");
            let alt1 = self.get_pattern("平行交替+交汇");
            let alt2 = self.get_pattern("主线+双支线");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        } else if self.check_one_main_two_side(cards, weight_map) {
            let pat = self.get_pattern("主线+双支线");
            let alt1 = self.get_pattern("平行交替+交汇");
            let alt2 = self.get_pattern("因果链扩展");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        } else {
            let pat = self.get_pattern("平行交替+交汇");
            let alt1 = self.get_pattern("因果链扩展");
            let alt2 = self.get_pattern("主线+双支线");
            (pat, "rule".into(), confidence, vec![alt1, alt2])
        }
    }

    // ------------------------------------------------------------------
    // LLM fallback
    // ------------------------------------------------------------------

    async fn select_by_llm(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> Result<(WeavingPattern, f64), String> {
        let patterns = self.weaving_patterns();
        let card_count = cards.len();

        if card_count <= 1 {
            return Ok((self.get_pattern("单段式"), 1.0));
        }

        let eligible: Vec<&WeavingPattern> = if card_count == 2 {
            patterns
                .iter()
                .filter(|p| p.mode == "single" || p.mode == "dual")
                .collect()
        } else {
            patterns
                .iter()
                .filter(|p| p.mode == "single" || p.mode == "dual" || p.mode == "all")
                .collect()
        };

        let cards_info: String = cards
            .iter()
            .enumerate()
            .map(|(i, c)| {
                format!(
                    "- 卡片{}: [{}] 方向文本: {} 类型: {} 权重: {:.2}",
                    i + 1,
                    c.name,
                    c.direction_text.as_deref().unwrap_or(""),
                    c.direction_type.as_deref().unwrap_or(""),
                    weight_map.get(&c.id).copied().unwrap_or(0.0)
                )
            })
            .collect::<Vec<_>>()
            .join("\n");

        let patterns_desc: String = eligible
            .iter()
            .enumerate()
            .map(|(i, p)| format!("{}. {}: {}", i + 1, p.name, p.description))
            .collect::<Vec<_>>()
            .join("\n");

        let prompt = format!(
            "你是一个小说编织模式选择专家。请根据以下卡片信息，从可选模式中选择最合适的编织模式。\n\n\
             卡片信息：\n{cards_info}\n\n\
             可选编织模式：\n{patterns_desc}\n\n\
             请严格按 JSON 格式输出，不要包含额外文字：\n\
             {{\"selected\": \"<模式名称>\", \"confidence\": <0-1的置信度>}}\n\
             示例：{{\"selected\": \"平行交替\", \"confidence\": 0.85}}"
        );

        let messages = vec![
            ChatMessage::system("你是一个小说编织模式选择专家。只输出JSON，不要额外内容。"),
            ChatMessage::user(&prompt),
        ];

        let response = self
            .llm_client
            .chat(&messages, &self.llm_api_key, DEFAULT_MODEL, 0.3, 512)
            .await
            .map_err(|e| format!("LLM call failed: {e}"))?;

        let parsed = Self::extract_json(&response)
            .map_err(|e| format!("JSON parse failed: {e}"))?;

        let pattern_name = parsed
            .get("selected")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let llm_confidence = parsed
            .get("confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5);

        let selected = eligible
            .iter()
            .find(|p| p.name == pattern_name)
            .copied()
            .cloned()
            .unwrap_or_else(|| {
                warn!("LLM returned unknown pattern '{pattern_name}', using default");
                eligible.first().copied().cloned().unwrap_or_else(|| self.get_pattern("单段式"))
            });

        Ok((selected, llm_confidence))
    }

    // ------------------------------------------------------------------
    // Prompt instruction filling
    // ------------------------------------------------------------------

    fn build_prompt_instruction(
        &self,
        pattern: &WeavingPattern,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> String {
        if cards.is_empty() {
            return pattern.prompt_instruction.clone();
        }

        let sorted_cards = self.sort_by_weight(cards, weight_map);
        let mut context: std::collections::HashMap<String, String> =
            std::collections::HashMap::new();

        if sorted_cards.len() >= 1 {
            let text = sorted_cards[0].direction_text.as_deref().unwrap_or("");
            let name = &sorted_cards[0].name;
            context.insert("card_a_direction".into(), text.to_string());
            context.insert("card_1_name".into(), name.clone());
            context.insert("card_1_direction".into(), text.to_string());
            context.insert("main_card_direction".into(), text.to_string());
        }

        if sorted_cards.len() >= 2 {
            let text1 = sorted_cards[1].direction_text.as_deref().unwrap_or("");
            let name1 = &sorted_cards[1].name;
            context.insert("card_b_direction".into(), text1.to_string());
            context.insert("card_2_name".into(), name1.clone());
            context.insert("card_2_direction".into(), text1.to_string());
            context.insert("side_card_direction".into(), text1.to_string());

            let w0 = weight_map.get(&sorted_cards[0].id).copied().unwrap_or(0.0);
            let w1 = weight_map.get(&sorted_cards[1].id).copied().unwrap_or(0.0);
            let (main_w, side_w) = if w0 >= w1 { (w0, w1) } else { (w1, w0) };
            context.insert("main_weight".into(), format!("{main_w:.2}"));
            context.insert("side_weight".into(), format!("{side_w:.2}"));
        }

        if sorted_cards.len() >= 3 {
            let text2 = sorted_cards[2].direction_text.as_deref().unwrap_or("");
            let name2 = &sorted_cards[2].name;
            context.insert("card_c_direction".into(), text2.to_string());
            context.insert("card_3_name".into(), name2.clone());
            context.insert("card_3_direction".into(), text2.to_string());
            context.insert(
                "side_card_1_direction".into(),
                sorted_cards[1].direction_text.as_deref().unwrap_or("").to_string(),
            );
            context.insert(
                "side_card_2_direction".into(),
                sorted_cards[2].direction_text.as_deref().unwrap_or("").to_string(),
            );
        }

        let mut prompt = pattern.prompt_instruction.clone();
        for (key, val) in &context {
            let placeholder = format!("{{{key}}}");
            prompt = prompt.replace(&placeholder, val);
        }

        prompt
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    fn get_pattern(&self, name: &str) -> WeavingPattern {
        let patterns = self.weaving_patterns();
        for p in &patterns {
            if p.name == name {
                return p.clone();
            }
        }
        warn!("Weaving pattern '{name}' not found, returning single-segment");
        patterns[0].clone()
    }

    fn sort_by_weight(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> Vec<WeaveCard> {
        let mut sorted = cards.to_vec();
        sorted.sort_by(|a, b| {
            let wa = weight_map.get(&a.id).copied().unwrap_or(0.0);
            let wb = weight_map.get(&b.id).copied().unwrap_or(0.0);
            wb.partial_cmp(&wa).unwrap_or(std::cmp::Ordering::Equal)
        });
        sorted
    }

    fn calc_confidence(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> f64 {
        if cards.is_empty() {
            return 0.0;
        }
        let total: f64 = cards.iter().map(|c| weight_map.get(&c.id).copied().unwrap_or(0.0)).sum();
        let avg = total / cards.len() as f64;
        avg.clamp(0.0, 1.0)
    }

    fn check_same_pov(&self, cards: &[WeaveCard]) -> bool {
        if cards.len() < 2 {
            return false;
        }

        let char_sets: Vec<std::collections::HashSet<String>> = cards
            .iter()
            .map(|c| {
                c.characters
                    .iter()
                    .filter_map(|ch| {
                        ch.as_object()
                            .and_then(|obj| obj.get("id"))
                            .and_then(|v| v.as_str())
                            .map(String::from)
                    })
                    .collect()
            })
            .collect();

        if char_sets.len() < 2 {
            return false;
        }

        if char_sets[0].is_empty() || char_sets[1].is_empty() {
            return false;
        }

        !char_sets[0].is_disjoint(&char_sets[1])
    }

    fn check_temporal_relation(&self, cards: &[WeaveCard]) -> bool {
        let timelines: Vec<&str> = cards
            .iter()
            .filter_map(|c| c.timeline_point.as_deref())
            .filter(|t| !t.trim().is_empty())
            .collect();
        timelines.len() >= 2
    }

    fn check_one_main_two_side(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
    ) -> bool {
        if cards.len() < 3 {
            return false;
        }
        let sorted = self.sort_by_weight(cards, weight_map);
        let w0 = weight_map.get(&sorted[0].id).copied().unwrap_or(0.0);
        let w1 = weight_map.get(&sorted[1].id).copied().unwrap_or(0.0);
        let w2 = weight_map.get(&sorted[2].id).copied().unwrap_or(0.0);
        w0 >= (w1 + w2) * 0.8 && w0 > w1
    }

    /// Extract JSON from LLM response text.
    pub fn extract_json(text: &str) -> Result<serde_json::Value, String> {
        let text = text.trim();

        // Try direct parse
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(text) {
            return Ok(v);
        }

        // Try extracting from markdown code fence
        let re = regex_lite::Regex::new(r"```(?:json)?\s*(\{.*?\})\s*```")
            .map_err(|e| e.to_string())?;
        if let Some(caps) = re.captures(text) {
            if let Some(m) = caps.get(1) {
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(m.as_str()) {
                    return Ok(v);
                }
            }
        }

        // Try extracting first { ... }
        let brace_re = regex_lite::Regex::new(r"(\{.*\})").map_err(|e| e.to_string())?;
        if let Some(m) = brace_re.find(text) {
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(m.as_str()) {
                return Ok(v);
            }
        }

        Err(format!("Failed to extract JSON from: {}", &text[..text.len().min(200)]))
    }

    // ------------------------------------------------------------------
    // Result builders
    // ------------------------------------------------------------------

    fn build_no_card_result(&self, req_mode: &str) -> WeavingSchemeResult {
        let pattern = self.get_pattern("单段式");
        WeavingSchemeResult {
            mode: req_mode.to_string(),
            selected_scheme: serde_json::to_value(&pattern).unwrap_or_default(),
            selection_method: "rule".into(),
            selection_confidence: 1.0,
            alternatives: Vec::new(),
            prompt_instruction: pattern.prompt_instruction,
            outline_template: pattern.outline_template,
        }
    }

    fn build_single_result(
        &self,
        cards: &[WeaveCard],
        weight_map: &std::collections::HashMap<i32, f64>,
        req_mode: &str,
    ) -> WeavingSchemeResult {
        let pattern = self.get_pattern("单段式");
        let prompt = self.build_prompt_instruction(&pattern, cards, weight_map);
        WeavingSchemeResult {
            mode: req_mode.to_string(),
            selected_scheme: serde_json::to_value(&pattern).unwrap_or_default(),
            selection_method: "rule".into(),
            selection_confidence: 1.0,
            alternatives: Vec::new(),
            prompt_instruction: prompt,
            outline_template: pattern.outline_template,
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_service() -> WeavingSchemeService {
        WeavingSchemeService::new(DeepSeekClient::new(), "test-key")
    }

    fn make_card(id: i32, name: &str, text: &str, dtype: &str) -> WeaveCard {
        WeaveCard {
            id,
            name: name.into(),
            direction_text: Some(text.into()),
            direction_type: Some(dtype.into()),
            characters: Vec::new(),
            timeline_point: None,
        }
    }

    #[test]
    fn test_weaving_patterns_count() {
        let svc = make_service();
        let patterns = svc.weaving_patterns();
        assert!(patterns.len() >= 7);
    }

    #[test]
    fn test_get_pattern() {
        let svc = make_service();
        let pat = svc.get_pattern("因果链");
        assert_eq!(pat.name, "因果链");
        assert!(pat.prompt_instruction.contains("因"));
    }

    #[test]
    fn test_get_pattern_fallback() {
        let svc = make_service();
        let pat = svc.get_pattern("不存在的模式");
        assert_eq!(pat.name, "单段式");
    }

    #[test]
    fn test_calc_confidence() {
        let svc = make_service();
        let cards = vec![make_card(1, "A", "text", "稳妥")];
        let mut weights = std::collections::HashMap::new();
        weights.insert(1, 0.8);
        let conf = svc.calc_confidence(&cards, &weights);
        assert!((conf - 0.8).abs() < 0.01);
    }

    #[test]
    fn test_build_no_card_result() {
        let svc = make_service();
        let result = svc.build_no_card_result("single");
        assert_eq!(result.mode, "single");
        assert_eq!(result.selection_method, "rule");
        assert_eq!(result.selection_confidence, 1.0);
    }

    #[test]
    fn test_extract_json_direct() {
        let result = WeavingSchemeService::extract_json(
            r#"{"selected": "平行交替", "confidence": 0.85}"#,
        );
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["selected"], "平行交替");
    }

    #[test]
    fn test_extract_json_fenced() {
        let result = WeavingSchemeService::extract_json(
            "```json\n{\"selected\": \"因果链\"}\n```",
        );
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["selected"], "因果链");
    }
}
