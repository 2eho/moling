//! 墨灵 (Moling) — Dynamic-Layer Conflict Detection Service.
//!
//! Detects three types of conflicts between direction cards and the dynamic layer:
//!
//! 1. **Baseline conflict** — card direction vs dynamic layer `must_hold` / `must_not`.
//! 2. **Secret matrix conflict** — card direction would cause a character to reveal
//!    something they do not (yet) know.
//! 3. **State machine conflict** — card direction is incompatible with a character's
//!    current narrative state.
//!
//! Ported from Python `app/service/conflict_detection.py`.

use std::sync::Arc;

use moling_core::error::AppResult;
use moling_db::dao::secret_dao::SecretDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_llm::{ChatMessage, DeepSeekClient, DEFAULT_MODEL};

use sea_orm::DatabaseConnection;
use serde::{Deserialize, Serialize};
use tracing::{debug, error, info, warn};

// ============================================================================
// Confidence scoring constants (mirrors Python §2.4)
// ============================================================================

const CONFIDENCE_LOW_ZONE: f64 = 0.15;
const CONFIDENCE_HIGH_ZONE: f64 = 0.75;
const CONFIDENCE_CENTER: f64 = 0.45;
const CONFIDENCE_HALF_RANGE: f64 = 0.30;
const CONFIDENCE_MIN: f64 = 0.2;
const CONFIDENCE_PLATEAU_HIGH: f64 = 0.9;
const CONFIDENCE_PEAK: f64 = 1.0;

const CONFIDENCE_HIGH_THRESHOLD: f64 = 0.7;
const CONFIDENCE_MEDIUM_THRESHOLD: f64 = 0.3;

const SEVERITY_WEIGHTS_HIGH: f64 = 1.0;
const SEVERITY_WEIGHTS_MEDIUM: f64 = 0.6;
const SEVERITY_WEIGHTS_LOW: f64 = 0.3;

// ---------------------------------------------------------------------------
// Confidence helpers
// ---------------------------------------------------------------------------

/// Compute confidence from conflict_score using a U-curve model (§2.4).
///
/// The U-curve ensures that both very low conflict scores (clear pass) and
/// very high conflict scores (clear fail) yield high confidence, while
/// ambiguous middle-range scores yield lower confidence.
pub fn compute_confidence(conflict_score: f64) -> f64 {
    if conflict_score <= 0.0 {
        return CONFIDENCE_PEAK;
    }

    if conflict_score <= CONFIDENCE_LOW_ZONE {
        let t = conflict_score / CONFIDENCE_LOW_ZONE;
        return ((CONFIDENCE_PEAK - (CONFIDENCE_PEAK - CONFIDENCE_PLATEAU_HIGH) * t) * 10000.0)
            .round() / 10000.0;
    }

    if conflict_score >= CONFIDENCE_HIGH_ZONE {
        if conflict_score >= 1.0 {
            return CONFIDENCE_PEAK;
        }
        let t = (conflict_score - CONFIDENCE_HIGH_ZONE) / (1.0 - CONFIDENCE_HIGH_ZONE);
        return ((CONFIDENCE_PLATEAU_HIGH
            + (CONFIDENCE_PEAK - CONFIDENCE_PLATEAU_HIGH) * t)
            * 10000.0)
            .round() / 10000.0;
    }

    let t = (conflict_score - CONFIDENCE_CENTER) / CONFIDENCE_HALF_RANGE;
    let confidence =
        CONFIDENCE_PLATEAU_HIGH - (CONFIDENCE_PLATEAU_HIGH - CONFIDENCE_MIN) * (1.0 - t * t);
    (confidence * 10000.0).round() / 10000.0
}

/// Map a numeric confidence value to a human-readable label.
pub fn compute_confidence_label(confidence: f64) -> &'static str {
    if confidence >= CONFIDENCE_HIGH_THRESHOLD {
        "high"
    } else if confidence >= CONFIDENCE_MEDIUM_THRESHOLD {
        "medium"
    } else {
        "low"
    }
}

// ---------------------------------------------------------------------------
// Conflict severity helpers
// ---------------------------------------------------------------------------

fn severity_weight(severity: &str) -> f64 {
    match severity {
        "high" => SEVERITY_WEIGHTS_HIGH,
        "medium" => SEVERITY_WEIGHTS_MEDIUM,
        _ => SEVERITY_WEIGHTS_LOW,
    }
}

fn compute_conflict_score(conflicts: &[ConflictItem]) -> f64 {
    if conflicts.is_empty() {
        return 0.0;
    }
    let raw: f64 = conflicts.iter().map(|c| severity_weight(&c.severity)).sum();
    ((1.0 - 1.0 / (1.0 + raw)) * 10000.0).round() / 10000.0
}

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// A single detected conflict.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictItem {
    #[serde(rename = "type")]
    pub conflict_type: String,
    pub description: String,
    pub severity: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub suggested_fix: Option<String>,
}

impl ConflictItem {
    pub fn new(
        conflict_type: impl Into<String>,
        description: impl Into<String>,
        severity: impl Into<String>,
        suggested_fix: Option<String>,
    ) -> Self {
        Self {
            conflict_type: conflict_type.into(),
            description: description.into(),
            severity: severity.into(),
            suggested_fix,
        }
    }
}

/// Full conflict detection result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictDetectionResult {
    pub has_conflict: bool,
    pub conflict_score: f64,
    pub confidence: f64,
    pub confidence_label: String,
    pub fallback_to_llm: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub llm_verdict: Option<String>,
    pub conflicts: Vec<ConflictItem>,
}

impl ConflictDetectionResult {
    pub fn empty() -> Self {
        Self {
            has_conflict: false,
            conflict_score: 0.0,
            confidence: 1.0,
            confidence_label: "high".to_string(),
            fallback_to_llm: false,
            llm_verdict: None,
            conflicts: Vec::new(),
        }
    }
}

/// Contextual information about a character referenced by a card.
#[derive(Debug, Clone)]
pub struct CardCharacterInfo {
    name: String,
    state_requirement: Option<String>,
}

/// Minimal card info for conflict detection.
#[derive(Debug, Clone)]
pub struct CardInfo {
    pub id: i32,
    pub name: String,
    pub direction_text: Option<String>,
    pub direction_type: Option<String>,
    pub characters: Vec<CardCharacterInfo>,
}

// ---------------------------------------------------------------------------
// ConflictDetectionService
// ---------------------------------------------------------------------------

/// Detects dynamic-layer conflicts for generated direction cards.
#[derive(Clone)]
pub struct ConflictDetectionService {
    vault_dao: VaultDao,
    secret_dao: SecretDao,
    dynamic_layer_dao: DynamicLayerDao,
    llm_client: Arc<DeepSeekClient>,
    llm_api_key: String,
}

impl ConflictDetectionService {
    /// Create a new ConflictDetectionService.
    pub fn new(
        vault_dao: VaultDao,
        secret_dao: SecretDao,
        dynamic_layer_dao: DynamicLayerDao,
        llm_client: DeepSeekClient,
        llm_api_key: impl Into<String>,
    ) -> Self {
        Self {
            vault_dao,
            secret_dao,
            dynamic_layer_dao,
            llm_client: Arc::new(llm_client),
            llm_api_key: llm_api_key.into(),
        }
    }

    // ------------------------------------------------------------------
    // Public entry point
    // ------------------------------------------------------------------

    /// Run all three conflict detectors, compute confidence, and optionally
    /// fall back to LLM for low-confidence results.
    pub async fn detect_conflicts(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: &str,
        cards: &[CardInfo],
    ) -> ConflictDetectionResult {
        info!(
            "Conflict detection start: project={project_id} chapter={chapter_id} cards={}",
            cards.len()
        );

        if cards.is_empty() {
            info!("No cards to check — returning empty conflict result.");
            return ConflictDetectionResult::empty();
        }

        let mut conflicts: Vec<ConflictItem> = Vec::new();

        // Load dynamic layer once
        let dynamic_layer = match self
            .dynamic_layer_dao
            .find_by_chapter(db, chapter_id)
            .await
        {
            Ok(dl) => dl,
            Err(e) => {
                error!("Conflict detection failed: {e}");
                let mut result = ConflictDetectionResult::empty();
                result.confidence = 0.5;
                result.confidence_label = "medium".to_string();
                return result;
            }
        };

        // 1. Baseline conflicts
        if let Ok(base) = self
            .detect_baseline_conflicts(cards, dynamic_layer.as_ref())
            .await
        {
            conflicts.extend(base);
        }

        // 2. Secret matrix conflicts
        if let Ok(secret) = self
            .detect_secret_conflicts(db, project_id, cards)
            .await
        {
            conflicts.extend(secret);
        }

        // 3. State machine conflicts
        if let Ok(state) = self
            .detect_state_machine_conflicts(db, project_id, cards)
            .await
        {
            conflicts.extend(state);
        }

        let has_conflict = !conflicts.is_empty();
        let conflict_score = compute_conflict_score(&conflicts);
        let confidence = compute_confidence(conflict_score);
        let confidence_label = compute_confidence_label(confidence).to_string();

        let mut result = ConflictDetectionResult {
            has_conflict,
            conflict_score,
            confidence,
            confidence_label: confidence_label.clone(),
            fallback_to_llm: false,
            llm_verdict: None,
            conflicts,
        };

        // LLM fallback for low-confidence results
        if confidence < CONFIDENCE_MEDIUM_THRESHOLD {
            info!(
                "Confidence={confidence:.4} < 0.3 — triggering LLM fallback for project={project_id} chapter={chapter_id}"
            );
            if let Some(llm_result) = self
                .llm_fallback_for_conflicts(project_id, chapter_id, cards, &result.conflicts, conflict_score)
                .await
            {
                result.fallback_to_llm = true;
                result.llm_verdict = llm_result.get("verdict").and_then(|v| v.as_str().map(String::from));
                if let Some(c) = llm_result.get("confidence").and_then(|v| v.as_f64()) {
                    result.confidence = c;
                    result.confidence_label = compute_confidence_label(c).to_string();
                }
                if llm_result
                    .get("overrides")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false)
                {
                    if let Some(hc) = llm_result.get("has_conflict").and_then(|v| v.as_bool()) {
                        result.has_conflict = hc;
                    }
                    if let Some(cs) = llm_result.get("conflict_score").and_then(|v| v.as_f64()) {
                        result.conflict_score = cs;
                    }
                    if let Some(new_conflicts) = llm_result.get("conflicts").and_then(|v| v.as_array()) {
                        result.conflicts = new_conflicts
                            .iter()
                            .filter_map(|c| serde_json::from_value::<ConflictItem>(c.clone()).ok())
                            .collect();
                    }
                }
            }
        }

        info!(
            "Conflict detection complete: has_conflict={has_conflict} score={conflict_score} confidence={confidence} label={confidence_label} count={}",
            result.conflicts.len()
        );
        result
    }

    /// Public method to evaluate confidence for a given conflict score.
    pub fn evaluate_confidence(&self, conflict_score: f64) -> serde_json::Value {
        let confidence = compute_confidence(conflict_score);
        let confidence_label = compute_confidence_label(confidence);
        let fallback_to_llm = confidence < CONFIDENCE_MEDIUM_THRESHOLD;
        debug!(
            "evaluate_confidence: score={conflict_score:.4} confidence={confidence:.4} label={confidence_label} fallback={fallback_to_llm}"
        );
        serde_json::json!({
            "confidence": confidence,
            "confidence_label": confidence_label,
            "fallback_to_llm": fallback_to_llm,
        })
    }

    // ------------------------------------------------------------------
    // LLM fallback
    // ------------------------------------------------------------------

    async fn llm_fallback_for_conflicts(
        &self,
        project_id: i32,
        chapter_id: &str,
        cards: &[CardInfo],
        conflicts: &[ConflictItem],
        conflict_score: f64,
    ) -> Option<serde_json::Map<String, serde_json::Value>> {
        if conflicts.is_empty() {
            debug!("No conflicts to fallback on — skipping LLM call.");
            return None;
        }

        let cards_summary: String = cards
            .iter()
            .map(|c| {
                format!(
                    "- 卡片「{}」: {}",
                    c.name,
                    c.direction_text.as_deref().unwrap_or("无方向文本")
                )
            })
            .collect::<Vec<_>>()
            .join("\n");

        let conflicts_summary: String = conflicts
            .iter()
            .map(|c| {
                format!(
                    "- [{}] {} (严重度: {})",
                    c.conflict_type, c.description, c.severity
                )
            })
            .collect::<Vec<_>>()
            .join("\n");

        let system_prompt = "你是一个专业的叙事冲突分析助手。你的任务是判断一组方向卡片与故事动态层之间的冲突是否真实存在。\n\n请分析以下冲突列表，判断它们是否是真正的叙事冲突：\n1. 如果冲突是真实的（例如，卡片方向确实会破坏故事连贯性），请回答「真实」\n2. 如果冲突是误报（例如，卡片方向实际上与约束兼容），请回答「误报」\n3. 给出一个 0-1 的置信度分数，表示你对判断的把握程度\n\n请以 JSON 格式回复，格式如下：\n{\"verdict\": \"真实\" 或 \"误报\", \"confidence\": 0.0-1.0, \"reasoning\": \"简要分析原因\"}";

        let user_prompt = format!(
            "项目ID: {project_id}\n章节ID: {chapter_id}\n冲突评分: {conflict_score:.4}\n\n方向卡片列表:\n{cards_summary}\n\n检测到的冲突:\n{conflicts_summary}"
        );

        let messages = vec![
            ChatMessage::system(system_prompt),
            ChatMessage::user(&user_prompt),
        ];

        let response = match self
            .llm_client
            .chat(&messages, &self.llm_api_key, DEFAULT_MODEL, 0.3, 1024)
            .await
        {
            Ok(r) => r,
            Err(e) => {
                warn!("LLM fallback failed: {e}");
                return None;
            }
        };

        let parsed: serde_json::Value = match parse_llm_response(&response) {
            Some(v) => v,
            None => {
                warn!("LLM fallback: failed to parse response, using defaults");
                let mut map = serde_json::Map::new();
                map.insert("verdict".to_string(), serde_json::Value::String("无法判断".to_string()));
                map.insert("confidence".to_string(), serde_json::json!(0.5));
                map.insert("overrides".to_string(), serde_json::Value::Bool(false));
                map.insert(
                    "has_conflict".to_string(),
                    serde_json::Value::Bool(!conflicts.is_empty()),
                );
                map.insert("conflict_score".to_string(), serde_json::json!(conflict_score));
                return Some(map);
            }
        };

        let verdict = parsed
            .get("verdict")
            .and_then(|v| v.as_str())
            .unwrap_or("无法判断");
        let llm_confidence = parsed
            .get("confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.5)
            .clamp(0.0, 1.0);

        info!("LLM fallback result: verdict={verdict} confidence={llm_confidence:.4}");

        let is_false_positive =
            verdict.contains("误报") || verdict.to_lowercase().contains("false");

        let mut map = serde_json::Map::new();
        map.insert("verdict".to_string(), serde_json::Value::String(verdict.to_string()));
        map.insert("confidence".to_string(), serde_json::json!(llm_confidence));
        map.insert(
            "overrides".to_string(),
            serde_json::Value::Bool(is_false_positive),
        );
        map.insert(
            "has_conflict".to_string(),
            serde_json::Value::Bool(if is_false_positive { false } else { !conflicts.is_empty() }),
        );
        map.insert(
            "conflict_score".to_string(),
            serde_json::json!(if is_false_positive { 0.0 } else { conflict_score }),
        );
        Some(map)
    }

    // ------------------------------------------------------------------
    // Detection 1: Baseline conflicts
    // ------------------------------------------------------------------

    async fn detect_baseline_conflicts(
        &self,
        cards: &[CardInfo],
        dynamic_layer: Option<&moling_db::entities::dynamic_layer::Model>,
    ) -> AppResult<Vec<ConflictItem>> {
        let dl = match dynamic_layer {
            Some(dl) => dl,
            None => return Ok(Vec::new()),
        };

        let must_hold: Vec<String> = dl.must_hold.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();
        let must_not: Vec<String> = dl.must_not.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();

        if must_hold.is_empty() && must_not.is_empty() {
            return Ok(Vec::new());
        }

        let mut conflicts: Vec<ConflictItem> = Vec::new();

        for card in cards {
            let direction_text = card.direction_text.as_deref().unwrap_or("");

            for constraint in &must_hold {
                if text_contradicts(direction_text, constraint) {
                    conflicts.push(ConflictItem::new(
                        "baseline",
                        format!(
                            "卡片「{}」的方向与连贯性约束「{constraint}」冲突",
                            card.name
                        ),
                        "high",
                        Some(format!(
                            "调整方向以避免违反「{constraint}」，或在方向中明确保持该约束"
                        )),
                    ));
                }
            }

            for constraint in &must_not {
                if text_violates_must_not(direction_text, constraint) {
                    conflicts.push(ConflictItem::new(
                        "baseline",
                        format!(
                            "卡片「{}」的方向暗示了应避免的「{constraint}」",
                            card.name
                        ),
                        "high",
                        Some(format!("调整方向以避开「{constraint}」")),
                    ));
                }
            }
        }

        Ok(conflicts)
    }

    // ------------------------------------------------------------------
    // Detection 2: Secret matrix conflicts
    // ------------------------------------------------------------------

    async fn detect_secret_conflicts(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[CardInfo],
    ) -> AppResult<Vec<ConflictItem>> {
        let card_character_names: std::collections::HashSet<String> = cards
            .iter()
            .flat_map(|c| &c.characters)
            .map(|ch| ch.name.clone())
            .collect();

        if card_character_names.is_empty() {
            return Ok(Vec::new());
        }

        let secrets = self.secret_dao.list_by_project(db, project_id).await?;
        if secrets.is_empty() {
            return Ok(Vec::new());
        }

        let mut conflicts: Vec<ConflictItem> = Vec::new();

        for secret in &secrets {
            let unknown_set: std::collections::HashSet<String> = secret
                .unknown_to
                .as_array()
                .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                .unwrap_or_default();

            let characters_who_should_not_know = card_character_names
                .intersection(&unknown_set)
                .collect::<Vec<_>>();

            let card_names_hint: String = cards
                .iter()
                .map(|c| c.name.as_str())
                .collect::<Vec<_>>()
                .join(", ");

            for char_name in characters_who_should_not_know {
                let desc_preview = if secret.description.len() > 60 {
                    &secret.description[..60]
                } else {
                    &secret.description
                };
                conflicts.push(ConflictItem::new(
                    "secret",
                    format!(
                        "角色「{char_name}」尚不知晓秘密「{desc_preview}…」，但出现在卡片方向中（涉及卡片：{card_names_hint}），可能导致信息泄露"
                    ),
                    "medium",
                    Some(format!(
                        "确保方向中「{char_name}」的行为不涉及该秘密，或先在故事中铺垫TA获得该信息的契机"
                    )),
                ));
            }
        }

        Ok(conflicts)
    }

    // ------------------------------------------------------------------
    // Detection 3: State machine conflicts
    // ------------------------------------------------------------------

    async fn detect_state_machine_conflicts(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[CardInfo],
    ) -> AppResult<Vec<ConflictItem>> {
        let mut char_state_req: std::collections::HashMap<String, String> =
            std::collections::HashMap::new();

        for card in cards {
            for char_entry in &card.characters {
                if let Some(ref req) = char_entry.state_requirement
                    && !req.is_empty() {
                        char_state_req.insert(char_entry.name.clone(), req.clone());
                    }
            }
        }

        if char_state_req.is_empty() {
            return Ok(Vec::new());
        }

        let vault_chars = self.vault_dao.find_characters(db, project_id).await?;
        let char_map: std::collections::HashMap<&str, &moling_db::entities::vault_character::Model> =
            vault_chars.iter().map(|c| (c.name.as_str(), c)).collect();

        let mut conflicts: Vec<ConflictItem> = Vec::new();

        for (char_name, state_req) in &char_state_req {
            let vc = match char_map.get(char_name.as_str()) {
                Some(vc) => vc,
                None => {
                    debug!("Character '{char_name}' not found in vault — skipping state check");
                    continue;
                }
            };

            let current_state = vc
                .current_state
                .as_deref()
                .unwrap_or("")
                .trim()
                .to_lowercase();

            if current_state.is_empty() {
                continue;
            }

            let req_state_lower = state_req.trim().to_lowercase();

            if states_conflict(&current_state, &req_state_lower) {
                conflicts.push(ConflictItem::new(
                    "state_machine",
                    format!(
                        "角色「{char_name}」当前状态为「{}」，但卡片要求状态为「{state_req}」，两者存在冲突",
                        vc.current_state.as_deref().unwrap_or("")
                    ),
                    "medium",
                    Some(format!(
                        "将卡片中「{char_name}」的状态要求改为「{}」，或先完成状态转换",
                        vc.current_state.as_deref().unwrap_or("")
                    )),
                ));
            }
        }

        Ok(conflicts)
    }
}

// ---------------------------------------------------------------------------
// Static text analysis helpers
// ---------------------------------------------------------------------------

/// Check if *text* contradicts a must_hold *constraint* (heuristic).
fn text_contradicts(text: &str, constraint: &str) -> bool {
    let contradict_verbs = [
        "决裂", "反目", "摧毁", "打破", "背叛", "破坏",
        "失去", "放弃", "终结", "推翻", "废除", "消亡",
        "不再", "不再有", "销毁", "撕毁",
    ];

    // Extract core from constraint by stripping known suffixes
    let core = constraint;
    let core = core
        .strip_suffix("关系")
        .or_else(|| core.strip_suffix("协议"))
        .or_else(|| core.strip_suffix("设定"))
        .or_else(|| core.strip_suffix("状态"))
        .or_else(|| core.strip_suffix("约定"))
        .or_else(|| core.strip_suffix("同盟"))
        .or_else(|| core.strip_suffix("规则"))
        .unwrap_or(core);

    if !text.contains(core) {
        return false;
    }

    contradict_verbs.iter().any(|verb| text.contains(verb))
}

/// Check if *text* suggests or directly mentions a must_not constraint.
fn text_violates_must_not(text: &str, constraint: &str) -> bool {
    text.contains(constraint)
}

/// Return `true` when *current* and *required* are semantically incompatible.
fn states_conflict(current: &str, required: &str) -> bool {
    if current == required {
        return false;
    }

    let antonym_pairs: [(&str, &str); 12] = [
        ("高兴", "悲伤"), ("快乐", "痛苦"), ("平静", "愤怒"),
        ("紧张", "松弛"), ("放松", "焦虑"), ("开心", "难过"),
        ("健康", "受伤"), ("健康", "重伤"), ("活着", "死亡"),
        ("清醒", "昏迷"), ("友善", "敌对"), ("信任", "怀疑"),
    ];

    for (a, b) in &antonym_pairs {
        if (current.contains(a) && required.contains(b))
            || (current.contains(b) && required.contains(a))
        {
            return true;
        }
    }

    false
}

// ---------------------------------------------------------------------------
// LLM response parser
// ---------------------------------------------------------------------------

/// Parse LLM JSON response, handling markdown code fences.
pub fn parse_llm_response(content: &str) -> Option<serde_json::Value> {
    if content.is_empty() {
        return None;
    }

    // Try direct JSON parse first
    if let Ok(v) = serde_json::from_str::<serde_json::Value>(content) {
        return Some(v);
    }

    // Try extracting JSON from markdown code block
    let re = regex_lite::Regex::new(r"```(?:json)?\s*\n?(.*?)\n?```").ok()?;
    if let Some(caps) = re.captures(content)
        && let Some(m) = caps.get(1)
            && let Ok(v) = serde_json::from_str::<serde_json::Value>(m.as_str()) {
                return Some(v);
            }

    // Try finding {...} object directly
    let brace_re = regex_lite::Regex::new(r"\{.*\}").ok()?;
    if let Some(m) = brace_re.find(content)
        && let Ok(v) = serde_json::from_str::<serde_json::Value>(m.as_str()) {
            return Some(v);
        }

    None
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_confidence_zero() {
        assert_eq!(compute_confidence(0.0), CONFIDENCE_PEAK);
    }

    #[test]
    fn test_compute_confidence_one() {
        assert_eq!(compute_confidence(1.0), CONFIDENCE_PEAK);
    }

    #[test]
    fn test_compute_confidence_middle() {
        let conf = compute_confidence(0.5);
        assert!(conf < CONFIDENCE_PLATEAU_HIGH);
        assert!(conf >= CONFIDENCE_MIN);
    }

    #[test]
    fn test_confidence_label() {
        assert_eq!(compute_confidence_label(0.9), "high");
        assert_eq!(compute_confidence_label(0.5), "medium");
        assert_eq!(compute_confidence_label(0.1), "low");
    }

    #[test]
    fn test_conflict_score_empty() {
        assert_eq!(compute_conflict_score(&[]), 0.0);
    }

    #[test]
    fn test_text_contradicts() {
        assert!(text_contradicts("师徒决裂", "师徒关系"));
        assert!(!text_contradicts("师徒重逢", "师徒关系"));
    }

    #[test]
    fn test_text_violates_must_not() {
        assert!(text_violates_must_not("主角死亡", "主角死亡"));
        assert!(!text_violates_must_not("主角生存", "主角死亡"));
    }

    #[test]
    fn test_states_conflict() {
        assert!(states_conflict("高兴", "悲伤"));
        assert!(states_conflict("活着", "死亡"));
        assert!(!states_conflict("健康", "健康"));
        assert!(!states_conflict("平静", "放松"));
    }

    #[test]
    fn test_parse_llm_response_json() {
        let result = parse_llm_response(r#"{"verdict": "真实", "confidence": 0.8}"#);
        assert!(result.is_some());
        let v = result.unwrap();
        assert_eq!(v["verdict"], "真实");
    }

    #[test]
    fn test_parse_llm_response_fenced() {
        let result = parse_llm_response("```json\n{\"verdict\": \"误报\"}\n```");
        assert!(result.is_some());
    }

    #[test]
    fn test_conflict_result_empty() {
        let result = ConflictDetectionResult::empty();
        assert!(!result.has_conflict);
        assert_eq!(result.conflict_score, 0.0);
        assert_eq!(result.confidence, 1.0);
    }
}
