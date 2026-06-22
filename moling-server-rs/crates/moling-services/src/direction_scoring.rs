//! 墨灵 (Moling) — Direction Scoring Service.
//!
//! Implements direction compatibility detection and scoring:
//! 1. Entity conflict detection — contradictionary descriptions across cards
//! 2. Emotional tone conflict — tone mismatch across direction types
//! 3. Confidence scoring — aggregate score with rule-based confidence thresholds
//!
//! Score ∈ [0, 1]:
//!   > 0.7  → High confidence → adopt directly
//!   [0.3, 0.7] → Medium confidence → mark "suggested", still adopt
//!   < 0.3  → Low confidence → fallback to LLM
//!
//! Weave selection score ∈ [0, 1]:
//!   > 0.8  → Adopt rule engine result directly
//!   ≤ 0.8  → Fallback to LLM for weave mode selection
//!
//! Ported from Python `app/service/direction_scoring.py`.

use std::sync::Arc;

use moling_llm::{ChatMessage, DeepSeekClient, DEFAULT_MODEL};

use serde::{Deserialize, Serialize};
use tracing::{error, info, warn};

// Direction type constants
const DIRECTION_TYPES: [&str; 4] = ["稳妥", "有趣", "惊艳", "神之一手"];

// Direction compatibility matrix (row i, col j → DIRECTION_TYPES[i] vs DIRECTION_TYPES[j])
const DIRECTION_COMPATIBILITY_MATRIX: [[f64; 4]; 4] = [
    // 稳妥    有趣    惊艳    神之一手
    [1.0, 0.7, 0.3, 0.1], // 稳妥
    [0.7, 1.0, 0.6, 0.4], // 有趣
    [0.3, 0.6, 1.0, 0.7], // 惊艳
    [0.1, 0.4, 0.7, 1.0], // 神之一手
];

// Direction → tone mapping
const DIRECTION_TONE_MAP: [(&str, &[&str]); 4] = [
    ("稳妥", &["平静", "稳重", "保守", "温和"]),
    ("有趣", &["轻松", "诙谐", "幽默", "愉快"]),
    ("惊艳", &["戏剧性", "紧张", "冲突", "震撼"]),
    ("神之一手", &["大胆", "冒险", "激进", "颠覆"]),
];

// High conflict direction pairs
const HIGH_CONFLICT_PAIRS: [(&str, &str); 2] = [("稳妥", "神之一手"), ("神之一手", "稳妥")];

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// Minimal card representation for direction scoring.
#[derive(Debug, Clone)]
pub struct DirectionCard {
    pub id: i32,
    pub name: String,
    pub direction_type: String,
    pub direction_text: Option<String>,
    pub characters: Vec<CardCharacterRef>,
    pub plot_promises: Vec<CardPlotPromiseRef>,
    pub world_rules: Vec<CardWorldRuleRef>,
}

#[derive(Debug, Clone)]
pub struct CardCharacterRef {
    pub id: Option<String>,
    pub name: Option<String>,
    pub state_requirement: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CardPlotPromiseRef {
    pub id: Option<String>,
    pub title: Option<String>,
    pub advance_type: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CardWorldRuleRef {
    pub id: Option<String>,
    pub rule: Option<String>,
    pub constraint: Option<String>,
}

/// A single entity conflict.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntityConflict {
    pub cards: Vec<i32>,
    pub entity: String,
    pub description: String,
    pub severity: String,
}

/// Full direction conflict scoring result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectionConflictResult {
    pub has_conflict: bool,
    pub conflict_score: f64,
    pub confidence: f64,
    pub compatibility_matrix: Vec<Vec<f64>>,
    pub entity_conflicts: Vec<EntityConflict>,
    pub tone_conflicts: Vec<String>,
    pub fallback_to_llm: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub llm_result: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggested_fix: Option<String>,
}

// ---------------------------------------------------------------------------
// DirectionScoringService
// ---------------------------------------------------------------------------

/// Direction conflict scoring service.
///
/// Pure computation + LLM fallback. No database operations.
#[derive(Clone)]
pub struct DirectionScoringService {
    llm_client: Arc<DeepSeekClient>,
    llm_api_key: String,
}

impl DirectionScoringService {
    /// Create a new DirectionScoringService.
    pub fn new(llm_client: DeepSeekClient, llm_api_key: impl Into<String>) -> Self {
        Self {
            llm_client: Arc::new(llm_client),
            llm_api_key: llm_api_key.into(),
        }
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Score direction conflicts for a set of cards.
    pub async fn score_direction_conflicts(
        &self,
        cards: &[DirectionCard],
    ) -> DirectionConflictResult {
        if cards.is_empty() {
            return self.empty_result();
        }

        // 1. Build direction compatibility matrix
        let compatibility_matrix = self.compute_compatibility_matrix(cards);

        // 2. Compute compatibility statistics
        let composites = self.compute_compatibility_statistics(cards, &compatibility_matrix);

        // 3. Entity conflict detection
        let entity_conflicts = self.entity_conflict_detection(cards);

        // 4. Emotional tone conflicts
        let tone_conflicts = self.emotional_tone_conflict(cards);

        // 5. Aggregate conflict score
        let conflict_score = self.aggregate_conflict_score(
            composites.avg_compatibility,
            &entity_conflicts,
            &tone_conflicts,
            cards,
        );

        // 6. Confidence calculation
        let confidence = self.calculate_confidence(conflict_score);

        // 7. Fallback to LLM if needed
        let fallback_to_llm = confidence < 0.3;
        let llm_result = if fallback_to_llm {
            info!("Confidence {confidence:.2} < 0.3, falling back to LLM");
            self.llm_fallback(cards, &compatibility_matrix, &entity_conflicts, &tone_conflicts)
                .await
        } else {
            info!("Confidence {confidence:.2} >= 0.3, adopting rule engine result");
            None
        };

        // 8. Generate suggested fix
        let suggested_fix = self.generate_suggested_fix(
            conflict_score,
            &entity_conflicts,
            &tone_conflicts,
            llm_result.as_deref(),
        );

        DirectionConflictResult {
            has_conflict: conflict_score > 0.3,
            conflict_score: (conflict_score * 10000.0).round() / 10000.0,
            confidence: (confidence * 10000.0).round() / 10000.0,
            compatibility_matrix,
            entity_conflicts,
            tone_conflicts,
            fallback_to_llm,
            llm_result,
            suggested_fix,
        }
    }

    /// Determine whether the rule engine can be used directly.
    pub fn can_use_rule_engine(
        &self,
        compatibility_result: &DirectionConflictResult,
    ) -> (bool, f64) {
        let score = compatibility_result.conflict_score;
        let confidence = compatibility_result.confidence;
        let weave_score = 0.6 * (1.0 - score) + 0.4 * confidence;
        let can_use = weave_score > 0.8;
        (can_use, (weave_score * 10000.0).round() / 10000.0)
    }

    // ------------------------------------------------------------------
    // Static lookup methods
    // ------------------------------------------------------------------

    /// Look up direction type index in the compatibility matrix.
    pub fn direction_index(direction_type: &str) -> usize {
        DIRECTION_TYPES
            .iter()
            .position(|&dt| dt == direction_type)
            .unwrap_or(0)
    }

    /// Look up compatibility score between two direction types.
    pub fn lookup_compatibility(dir_a: &str, dir_b: &str) -> f64 {
        let i = Self::direction_index(dir_a);
        let j = Self::direction_index(dir_b);
        DIRECTION_COMPATIBILITY_MATRIX[i][j]
    }

    // ------------------------------------------------------------------
    // Internal computation methods
    // ------------------------------------------------------------------

    fn compute_compatibility_matrix(&self, cards: &[DirectionCard]) -> Vec<Vec<f64>> {
        let n = cards.len();
        let mut matrix = vec![vec![1.0; n]; n];
        for i in 0..n {
            for j in (i + 1)..n {
                let score = Self::lookup_compatibility(
                    &cards[i].direction_type,
                    &cards[j].direction_type,
                );
                matrix[i][j] = score;
                matrix[j][i] = score;
            }
        }
        matrix
    }

    fn compute_compatibility_statistics(
        &self,
        cards: &[DirectionCard],
        matrix: &[Vec<f64>],
    ) -> CompatibilityStats {
        let n = cards.len();
        if n == 0 {
            return CompatibilityStats {
                avg_compatibility: 1.0,
                min_compatibility: 1.0,
                max_compatibility: 1.0,
            };
        }

        let mut scores: Vec<f64> = Vec::new();
        for i in 0..n {
            for j in (i + 1)..n {
                scores.push(matrix[i][j]);
            }
        }

        if scores.is_empty() {
            return CompatibilityStats {
                avg_compatibility: 1.0,
                min_compatibility: 1.0,
                max_compatibility: 1.0,
            };
        }

        let total: f64 = scores.iter().sum();
        let min = scores.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        CompatibilityStats {
            avg_compatibility: total / scores.len() as f64,
            min_compatibility: min,
            max_compatibility: max,
        }
    }

    fn entity_conflict_detection(&self, cards: &[DirectionCard]) -> Vec<EntityConflict> {
        let mut conflicts: Vec<EntityConflict> = Vec::new();
        conflicts.extend(self.detect_character_conflicts(cards));
        conflicts.extend(self.detect_plot_promise_conflicts(cards));
        conflicts.extend(self.detect_world_rule_conflicts(cards));
        conflicts
    }

    fn detect_character_conflicts(&self, cards: &[DirectionCard]) -> Vec<EntityConflict> {
        let mut conflicts: Vec<EntityConflict> = Vec::new();
        let mut character_map: std::collections::HashMap<String, Vec<(usize, String)>> =
            std::collections::HashMap::new();

        for (idx, card) in cards.iter().enumerate() {
            for char_ref in &card.characters {
                let char_id = char_ref
                    .id
                    .clone()
                    .unwrap_or_else(|| char_ref.name.clone().unwrap_or_default());
                let state = char_ref.state_requirement.clone().unwrap_or_default();
                character_map
                    .entry(char_id)
                    .or_default()
                    .push((idx, state));
            }
        }

        for (char_id, entries) in &character_map {
            if entries.len() < 2 {
                continue;
            }

            let states: Vec<&str> = entries.iter().map(|(_, s)| s.as_str()).collect();
            if states.iter().collect::<std::collections::HashSet<_>>().len() > 1
                && states.iter().all(|s| !s.is_empty())
            {
                let severity = if is_state_contradictory(&states) {
                    "high"
                } else {
                    "medium"
                };
                let card_indices: Vec<i32> = entries.iter().map(|(i, _)| cards[*i].id).collect();
                let details: Vec<String> = entries
                    .iter()
                    .map(|(i, s)| {
                        format!("{}: {}", cards[*i].name, if s.is_empty() { "无" } else { s })
                    })
                    .collect();

                conflicts.push(EntityConflict {
                    cards: card_indices,
                    entity: format!("角色: {char_id}"),
                    description: format!(
                        "角色 '{char_id}' 在不同卡片中状态要求冲突: {}",
                        details.join(", ")
                    ),
                    severity: severity.to_string(),
                });
            }
        }

        conflicts
    }

    fn detect_plot_promise_conflicts(&self, cards: &[DirectionCard]) -> Vec<EntityConflict> {
        let mut conflicts: Vec<EntityConflict> = Vec::new();
        let mut promise_map: std::collections::HashMap<String, Vec<(usize, String)>> =
            std::collections::HashMap::new();

        for (idx, card) in cards.iter().enumerate() {
            for promise in &card.plot_promises {
                let pid = promise
                    .id
                    .clone()
                    .unwrap_or_else(|| promise.title.clone().unwrap_or_default());
                let advance_type = promise.advance_type.clone().unwrap_or_default();
                promise_map.entry(pid).or_default().push((idx, advance_type));
            }
        }

        for (promise_id, entries) in &promise_map {
            if entries.len() < 2 {
                continue;
            }

            let advance_types: Vec<&str> = entries.iter().map(|(_, s)| s.as_str()).collect();
            let unique: std::collections::HashSet<_> = advance_types.iter().collect();
            if unique.len() > 1 && advance_types.iter().all(|s| !s.is_empty()) {
                let card_indices: Vec<i32> = entries.iter().map(|(i, _)| cards[*i].id).collect();
                conflicts.push(EntityConflict {
                    cards: card_indices,
                    entity: format!("剧情承诺: {promise_id}"),
                    description: format!(
                        "剧情承诺 '{promise_id}' 在不同卡片中推进类型矛盾: {}",
                        advance_types.join(", ")
                    ),
                    severity: "medium".to_string(),
                });
            }
        }

        conflicts
    }

    fn detect_world_rule_conflicts(&self, cards: &[DirectionCard]) -> Vec<EntityConflict> {
        let mut conflicts: Vec<EntityConflict> = Vec::new();
        let mut rule_map: std::collections::HashMap<String, Vec<(usize, String)>> =
            std::collections::HashMap::new();

        for (idx, card) in cards.iter().enumerate() {
            for rule in &card.world_rules {
                let rid = rule
                    .id
                    .clone()
                    .unwrap_or_else(|| rule.rule.clone().unwrap_or_default());
                let constraint = rule.constraint.clone().unwrap_or_default();
                rule_map.entry(rid).or_default().push((idx, constraint));
            }
        }

        for (rule_id, entries) in &rule_map {
            if entries.len() < 2 {
                continue;
            }

            let constraints: Vec<&str> = entries.iter().map(|(_, s)| s.as_str()).collect();
            let unique: std::collections::HashSet<_> = constraints.iter().collect();
            if unique.len() > 1 && constraints.iter().all(|s| !s.is_empty()) {
                let card_indices: Vec<i32> = entries.iter().map(|(i, _)| cards[*i].id).collect();
                conflicts.push(EntityConflict {
                    cards: card_indices,
                    entity: format!("世界观规则: {rule_id}"),
                    description: format!(
                        "规则 '{rule_id}' 在不同卡片中约束矛盾: {}",
                        constraints.join(", ")
                    ),
                    severity: "low".to_string(),
                });
            }
        }

        conflicts
    }

    fn emotional_tone_conflict(&self, cards: &[DirectionCard]) -> Vec<String> {
        let mut conflicts: Vec<String> = Vec::new();
        let mut seen_pairs: std::collections::HashSet<(String, String)> =
            std::collections::HashSet::new();

        for i in 0..cards.len() {
            for j in (i + 1)..cards.len() {
                let dir_a = &cards[i].direction_type;
                let dir_b = &cards[j].direction_type;

                let mut pair = vec![dir_a.clone(), dir_b.clone()];
                pair.sort();
                let pair_key = (pair[0].clone(), pair[1].clone());

                if seen_pairs.contains(&pair_key) {
                    continue;
                }
                seen_pairs.insert(pair_key);

                let compatibility = Self::lookup_compatibility(dir_a, dir_b);
                if compatibility < 0.4 {
                    let tones_a = DIRECTION_TONE_MAP
                        .iter()
                        .find(|(dt, _)| *dt == dir_a.as_str())
                        .map(|(_, t)| t.join(", "))
                        .unwrap_or_else(|| "未知".to_string());
                    let tones_b = DIRECTION_TONE_MAP
                        .iter()
                        .find(|(dt, _)| *dt == dir_b.as_str())
                        .map(|(_, t)| t.join(", "))
                        .unwrap_or_else(|| "未知".to_string());

                    conflicts.push(format!(
                        "方向 '{dir_a}' ({tones_a}) 与方向 '{dir_b}' ({tones_b}) 情感基调冲突"
                    ));
                }
            }
        }

        conflicts
    }

    fn aggregate_conflict_score(
        &self,
        composite_score: f64,
        entity_conflicts: &[EntityConflict],
        tone_conflicts: &[String],
        cards: &[DirectionCard],
    ) -> f64 {
        // 1. Direction compatibility conflict (invert: 1 - avg = high conflict)
        let compatibility_conflict = 1.0 - composite_score;

        // 2. Entity conflict penalty
        let high_count = entity_conflicts.iter().filter(|c| c.severity == "high").count();
        let medium_count = entity_conflicts.iter().filter(|c| c.severity == "medium").count();
        let low_count = entity_conflicts.iter().filter(|c| c.severity == "low").count();

        let entity_penalty = if high_count > 0 {
            (high_count as f64 * 0.2).min(0.5)
        } else if medium_count > 0 {
            (medium_count as f64 * 0.1).min(0.3)
        } else if low_count > 0 {
            (low_count as f64 * 0.05).min(0.1)
        } else {
            0.0
        };

        // 3. Tone conflict penalty
        let tone_penalty = (tone_conflicts.len() as f64 * 0.1).min(0.3);

        // 4. High conflict pair penalty
        let mut pair_penalty: f64 = 0.0;
        for i in 0..cards.len() {
            for j in (i + 1)..cards.len() {
                let pair = (
                    cards[i].direction_type.as_str(),
                    cards[j].direction_type.as_str(),
                );
                if HIGH_CONFLICT_PAIRS.contains(&pair) {
                    pair_penalty = pair_penalty.max(0.2f64);
                }
            }
        }

        (compatibility_conflict + entity_penalty + tone_penalty + pair_penalty).min(1.0)
    }

    fn calculate_confidence(&self, conflict_score: f64) -> f64 {
        if conflict_score < 0.1 {
            0.9
        } else if conflict_score > 0.8 {
            0.85
        } else if conflict_score > 0.6 {
            0.75
        } else if conflict_score > 0.4 {
            0.5
        } else {
            0.3
        }
    }

    // ------------------------------------------------------------------
    // LLM Fallback
    // ------------------------------------------------------------------

    async fn llm_fallback(
        &self,
        cards: &[DirectionCard],
        compatibility_matrix: &[Vec<f64>],
        entity_conflicts: &[EntityConflict],
        tone_conflicts: &[String],
    ) -> Option<String> {
        let cards_summary = self.build_cards_summary(cards);
        let matrix_summary = self.build_matrix_summary(cards, compatibility_matrix);
        let entity_summary = self.build_entity_summary(entity_conflicts);
        let tone_summary = if tone_conflicts.is_empty() {
            "无".to_string()
        } else {
            tone_conflicts
                .iter()
                .map(|t| format!("- {t}"))
                .collect::<Vec<_>>()
                .join("\n")
        };

        let prompt = format!(
            r#"你是小说创作方向分析专家。请判断以下方向卡片组合是否存在冲突。

## 方向卡片信息
{cards_summary}

## 方向相容性矩阵
{matrix_summary}

## 实体冲突检测结果
{entity_summary}

## 情感基调冲突
{tone_summary}

请分析这些卡片组合的实际冲突情况，按以下 JSON 格式输出（只输出 JSON，不要其他文字）：
{{
    "assessment": "兼容 / 部分兼容 / 冲突",
    "conflict_score": 0.0-1.0,
    "reasoning": "分析推理过程",
    "suggestion": "具体的改进建议",
    "recommended_fix": "建议的解决方案描述"
}}"#
        );

        let messages = vec![
            ChatMessage::system(
                "你是专业的小说创作方向分析助手，擅长分析方向冲突并提供改进建议。输出纯 JSON。",
            ),
            ChatMessage::user(&prompt),
        ];

        match self
            .llm_client
            .chat(&messages, &self.llm_api_key, DEFAULT_MODEL, 0.3, 1024)
            .await
        {
            Ok(content) => {
                let json_start = content.find('{').unwrap_or(0);
                let json_end = content.rfind('}').map(|i| i + 1).unwrap_or(content.len());
                let json_str = &content[json_start..json_end];
                match serde_json::from_str::<serde_json::Value>(json_str) {
                    Ok(parsed) => {
                        Some(serde_json::to_string(&parsed).unwrap_or_default())
                    }
                    Err(e) => {
                        warn!("LLM response could not be parsed as JSON: {e}");
                        None
                    }
                }
            }
            Err(e) => {
                error!("LLM fallback failed: {e}");
                None
            }
        }
    }

    // ------------------------------------------------------------------
    // Summary builders
    // ------------------------------------------------------------------

    fn build_cards_summary(&self, cards: &[DirectionCard]) -> String {
        cards
            .iter()
            .enumerate()
            .map(|(i, card)| {
                let mut lines = vec![format!(
                    "卡片 {}: {} (方向: {}, 稀有度: {})",
                    i + 1,
                    card.name,
                    if card.direction_type.is_empty() {
                        "未指定"
                    } else {
                        &card.direction_type
                    },
                    "普通"
                )];
                if let Some(ref text) = card.direction_text {
                    let preview = if text.len() > 100 { &text[..100] } else { text };
                    lines.push(format!("  方向文本: {preview}"));
                }
                if !card.characters.is_empty() {
                    let names: Vec<&str> = card
                        .characters
                        .iter()
                        .filter_map(|c| c.name.as_deref())
                        .collect();
                    if !names.is_empty() {
                        lines.push(format!("  关联角色: {}", names.join(", ")));
                    }
                }
                if !card.plot_promises.is_empty() {
                    let titles: Vec<&str> = card
                        .plot_promises
                        .iter()
                        .filter_map(|p| p.title.as_deref())
                        .collect();
                    if !titles.is_empty() {
                        lines.push(format!("  关联剧情: {}", titles.join(", ")));
                    }
                }
                lines.join("\n")
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn build_matrix_summary(
        &self,
        cards: &[DirectionCard],
        matrix: &[Vec<f64>],
    ) -> String {
        let names: Vec<String> = cards
            .iter()
            .map(|c| format!("{}({})", c.name, c.direction_type))
            .collect();
        let mut lines = Vec::new();
        for i in 0..cards.len() {
            let row: Vec<String> = (0..cards.len())
                .map(|j| {
                    if i == j {
                        "-".to_string()
                    } else {
                        format!("{:.1}", matrix[i][j])
                    }
                })
                .collect();
            lines.push(format!("  {}: {}", names[i], row.join(", ")));
        }
        lines.join("\n")
    }

    fn build_entity_summary(&self, entity_conflicts: &[EntityConflict]) -> String {
        if entity_conflicts.is_empty() {
            return "无实体冲突".to_string();
        }
        entity_conflicts
            .iter()
            .map(|c| {
                let desc = if c.description.len() > 100 {
                    &c.description[..100]
                } else {
                    &c.description
                };
                format!("- [{}] {}: {desc}", c.severity.to_uppercase(), c.entity)
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn generate_suggested_fix(
        &self,
        conflict_score: f64,
        entity_conflicts: &[EntityConflict],
        tone_conflicts: &[String],
        fallback_result: Option<&str>,
    ) -> Option<String> {
        if let Some(fr) = fallback_result {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(fr) {
                if let Some(s) = parsed
                    .get("suggestion")
                    .or_else(|| parsed.get("recommended_fix"))
                    .and_then(|v| v.as_str())
                {
                    return Some(s.to_string());
                }
            }
        }

        if conflict_score < 0.3 {
            return None;
        }

        let mut fixes: Vec<String> = Vec::new();

        if !entity_conflicts.is_empty() {
            let high_entities: Vec<&str> = entity_conflicts
                .iter()
                .filter(|c| c.severity == "high")
                .map(|c| c.entity.as_str())
                .collect();
            if !high_entities.is_empty() {
                fixes.push(format!(
                    "解决高严重度实体冲突: {}。建议统一对同一实体的描述。",
                    high_entities.join(", ")
                ));
            }
        }

        if !tone_conflicts.is_empty() {
            fixes.push(
                "情感基调冲突建议: 尝试调整方向搭配，或通过叙事手法中和基调冲突。"
                    .to_string(),
            );
        }

        if conflict_score > 0.6 {
            fixes.push("高冲突评分建议: 考虑替换部分卡片以降低方向冲突。".to_string());
        }

        if fixes.is_empty() {
            None
        } else {
            Some(fixes.join("；"))
        }
    }

    fn empty_result(&self) -> DirectionConflictResult {
        DirectionConflictResult {
            has_conflict: false,
            conflict_score: 0.0,
            confidence: 1.0,
            compatibility_matrix: Vec::new(),
            entity_conflicts: Vec::new(),
            tone_conflicts: Vec::new(),
            fallback_to_llm: false,
            llm_result: None,
            suggested_fix: None,
        }
    }
}

// ---------------------------------------------------------------------------
// Helper structs and functions
// ---------------------------------------------------------------------------

#[allow(dead_code)]
struct CompatibilityStats {
    avg_compatibility: f64,
    min_compatibility: f64,
    max_compatibility: f64,
}

/// Check if multiple states are contradictory.
fn is_state_contradictory(states: &[&str]) -> bool {
    let contradictory_pairs: [(&str, &str); 10] = [
        ("生", "死"), ("活", "死"), ("在", "不在"),
        ("出现", "消失"), ("强", "弱"), ("高", "低"),
        ("有", "无"), ("是", "否"), ("觉醒", "沉睡"),
        ("清醒", "昏迷"),
    ];

    for a in states {
        for b in states {
            if a == b {
                continue;
            }
            for (ka, kb) in &contradictory_pairs {
                if (a.contains(ka) && b.contains(kb)) || (a.contains(kb) && b.contains(ka)) {
                    return true;
                }
            }
        }
    }
    false
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_service() -> DirectionScoringService {
        DirectionScoringService::new(DeepSeekClient::new(), "test-key")
    }

    #[test]
    fn test_direction_index() {
        assert_eq!(DirectionScoringService::direction_index("稳妥"), 0);
        assert_eq!(DirectionScoringService::direction_index("神之一手"), 3);
        assert_eq!(DirectionScoringService::direction_index("未知"), 0);
    }

    #[test]
    fn test_lookup_compatibility() {
        assert_eq!(
            DirectionScoringService::lookup_compatibility("稳妥", "稳妥"),
            1.0
        );
        assert_eq!(
            DirectionScoringService::lookup_compatibility("稳妥", "神之一手"),
            0.1
        );
    }

    #[test]
    fn test_is_state_contradictory() {
        assert!(is_state_contradictory(&["生", "死"]));
        assert!(is_state_contradictory(&["清醒", "昏迷"]));
        assert!(!is_state_contradictory(&["高兴", "开心"]));
    }

    #[test]
    fn test_calculate_confidence() {
        let svc = make_service();
        assert_eq!(svc.calculate_confidence(0.0), 0.9);
        assert_eq!(svc.calculate_confidence(0.5), 0.5);
        assert_eq!(svc.calculate_confidence(0.9), 0.85);
    }

    #[test]
    fn test_empty_result() {
        let svc = make_service();
        let result = svc.empty_result();
        assert!(!result.has_conflict);
        assert_eq!(result.conflict_score, 0.0);
        assert_eq!(result.confidence, 1.0);
    }
}
