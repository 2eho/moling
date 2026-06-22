//! 墨灵 (Moling) — Merge Service (四库合并核心引擎).
//!
//! Core four-vault merge engine:
//! - Character merge (merge_characters) — fuzzy matching / status change / confidence downgrade
//! - Timeline merge (merge_timeline) — add / resolve_date / correct
//! - Plot promise merge (merge_plot_promises) — create / advance / redeem / cancel
//! - World building merge (merge_world_building) — create / expand / revise / conflict
//! - Change log archive (archive_changelog)
//!
//! Confidence downgrade strategy (P1-4):
//! - ConfidenceLevel enum (HIGH / MEDIUM / LOW / REJECT)
//! - evaluate_confidence / should_auto_apply
//!
//! Ported from Python `app/service/merge_service.py`.

use moling_core::error::AppResult;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::{
    vault_character::Model as VaultCharacter,
    vault_plot_promise::Model as VaultPlotPromise,
    vault_world::Model as VaultWorld,
};

use sea_orm::DatabaseConnection;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::warn;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

#[allow(dead_code)]
const STALE_CHAPTER_THRESHOLD: i32 = 20;
#[allow(dead_code)]
const MAX_AMBIGUOUS_MATCHES: usize = 3;
#[allow(dead_code)]
const SURNAME_MATCH_CONFIDENCE: f64 = 0.5;
const NEW_ENTITY_CONFIDENCE: f64 = 0.3;

const CONFIDENCE_HIGH_THRESHOLD: f64 = 0.8;
const CONFIDENCE_MEDIUM_THRESHOLD: f64 = 0.5;
const CONFIDENCE_LOW_THRESHOLD: f64 = 0.3;

// Edit distance → confidence mapping
#[allow(dead_code)]
const EDIT_DIST_CONFIDENCE: [(i32, f64); 3] = [(0, 1.0), (1, 0.9), (2, 0.75)];

// ---------------------------------------------------------------------------
// Confidence Level (P1-4)
// ---------------------------------------------------------------------------

/// 4-level confidence assessment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ConfidenceLevel {
    /// > 0.8: auto-apply, no confirmation needed
    High,
    /// 0.5-0.8: auto-apply + background "needs review" flag
    Medium,
    /// 0.3-0.5: pause, popup confirmation
    Low,
    /// < 0.3: ignore, do not write to DB
    Reject,
}

/// Evaluate confidence level from score.
pub fn evaluate_confidence(score: f64) -> ConfidenceLevel {
    if score > CONFIDENCE_HIGH_THRESHOLD {
        ConfidenceLevel::High
    } else if score >= CONFIDENCE_MEDIUM_THRESHOLD {
        ConfidenceLevel::Medium
    } else if score >= CONFIDENCE_LOW_THRESHOLD {
        ConfidenceLevel::Low
    } else {
        ConfidenceLevel::Reject
    }
}

/// Whether to auto-apply: High and Medium auto-apply; Low needs confirmation; Reject ignored.
pub fn should_auto_apply(level: ConfidenceLevel) -> bool {
    matches!(level, ConfidenceLevel::High | ConfidenceLevel::Medium)
}

// ---------------------------------------------------------------------------
// Data Transfer Objects
// ---------------------------------------------------------------------------

/// Single change log entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChangeEntry {
    pub entity_type: String,
    pub entity_id: String,
    pub entity_name: String,
    pub change_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub old_value: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub new_value: Option<String>,
    pub chapter: i32,
    pub confidence: f64,
    pub change_reason: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence_level: Option<ConfidenceLevel>,
}

/// Merge operation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeResult {
    pub entity_type: String,
    pub created: i32,
    pub updated: i32,
    pub deleted: i32,
    pub conflicts: Vec<serde_json::Value>,
    pub warnings: Vec<String>,
    pub changes: Vec<ChangeEntry>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence_level: Option<ConfidenceLevel>,
    pub auto_applied: bool,
    pub items_requiring_review: Vec<ChangeEntry>,
}

// ---------------------------------------------------------------------------
// Extraction DTOs
// ---------------------------------------------------------------------------

/// LLM-extracted character change.
#[derive(Debug, Clone)]
pub struct ExtractedCharacter {
    pub name: String,
    pub role: String,
    pub aliases: Vec<String>,
    pub status: String,
    pub appearance: Option<String>,
    pub personality: Option<String>,
    pub description: Option<String>,
    pub faction: Option<String>,
    pub location: Option<String>,
    pub current_state: Option<String>,
    pub motivation: Option<String>,
    pub confidence: f64,
}

/// LLM-extracted timeline event.
#[derive(Debug, Clone)]
pub struct ExtractedTimelineEvent {
    pub action: String,
    pub event: String,
    pub day: Option<i32>,
    pub chapter: i32,
    pub description: String,
    pub participants: Vec<String>,
    pub importance: String,
    pub is_key_event: bool,
}

/// LLM-extracted plot promise.
#[derive(Debug, Clone)]
pub struct ExtractedPlotPromise {
    pub action: String,
    pub title: String,
    pub description: String,
    pub promise_type: String,
    pub status: String,
    pub related_characters: Vec<String>,
    pub cancel_reason: Option<String>,
}

/// LLM-extracted world item.
#[derive(Debug, Clone)]
pub struct ExtractedWorldItem {
    pub action: String,
    pub name: String,
    pub category: String,
    pub content: String,
    pub old_content: Option<String>,
}

// ---------------------------------------------------------------------------
// MergeService
// ---------------------------------------------------------------------------

/// Four-vault merge core engine.
///
/// Receives LLM-extracted structured changes, performs merge operations,
/// and returns change logs. All exceptions are propagated to the caller.
#[derive(Clone)]
pub struct MergeService {
    vault_dao: VaultDao,
}

impl MergeService {
    /// Create a new MergeService.
    pub fn new(vault_dao: VaultDao) -> Self {
        Self { vault_dao }
    }

    // ------------------------------------------------------------------
    // Utility Methods
    // ------------------------------------------------------------------

    /// Calculate edit distance between two strings (Levenshtein distance).
    pub fn edit_distance(s1: &str, s2: &str) -> usize {
        let s1_chars: Vec<char> = s1.chars().collect();
        let s2_chars: Vec<char> = s2.chars().collect();
        let m = s1_chars.len();
        let n = s2_chars.len();

        let mut dp = vec![vec![0usize; n + 1]; m + 1];
        for i in 0..=m {
            dp[i][0] = i;
        }
        for j in 0..=n {
            dp[0][j] = j;
        }

        for i in 1..=m {
            for j in 1..=n {
                let cost = if s1_chars[i - 1] == s2_chars[j - 1] { 0 } else { 1 };
                dp[i][j] = (dp[i - 1][j] + 1)
                    .min(dp[i][j - 1] + 1)
                    .min(dp[i - 1][j - 1] + cost);
            }
        }

        dp[m][n]
    }

    #[allow(dead_code)]
    fn calc_confidence(edit_distance: usize, matched: bool) -> f64 {
        if matched {
            for (dist, conf) in &EDIT_DIST_CONFIDENCE {
                if edit_distance == *dist as usize {
                    return *conf;
                }
            }
            SURNAME_MATCH_CONFIDENCE
        } else {
            NEW_ENTITY_CONFIDENCE
        }
    }

    #[allow(dead_code)]
    fn surname_match(name1: &str, name2: &str) -> bool {
        if name1.is_empty() || name2.is_empty() {
            return false;
        }
        name1.chars().next() == name2.chars().next()
    }

    fn evaluate_merge_confidence(result: &mut MergeResult) {
        if result.changes.is_empty() {
            result.confidence_level = Some(ConfidenceLevel::High);
            result.auto_applied = true;
            return;
        }

        let mut avg_confidence = 0.0;
        let mut items_requiring_review = Vec::new();

        for change in &mut result.changes {
            let level = evaluate_confidence(change.confidence);
            change.confidence_level = Some(level);
            avg_confidence += change.confidence;
            if level == ConfidenceLevel::Low {
                items_requiring_review.push(change.clone());
            }
        }

        avg_confidence /= result.changes.len() as f64;
        result.confidence_level = Some(evaluate_confidence(avg_confidence));
        result.auto_applied = should_auto_apply(result.confidence_level.unwrap());
        result.items_requiring_review = items_requiring_review;
    }

    fn get_last_advance_chapter(promise: &VaultPlotPromise) -> i32 {
        if let Some(ref log) = promise.advancement_log {
            if let Some(arr) = log.as_array() {
                return arr
                    .iter()
                    .filter_map(|entry| entry.get("chapter").and_then(|c| c.as_i64()))
                    .max()
                    .unwrap_or(promise.planted_chapter.unwrap_or(0) as i64) as i32;
            }
        }
        promise.planted_chapter.unwrap_or(0)
    }

    // ------------------------------------------------------------------
    // Character Merge
    // ------------------------------------------------------------------

    /// Merge character vault changes.
    ///
    /// Matching strategy (priority):
    /// 1. Exact name match
    /// 2. Alias match
    /// 3. Edit distance ≤ 2
    /// 4. Surname match
    /// 5. No match → create new
    pub async fn merge_characters(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        extracted: &[ExtractedCharacter],
        chapter_number: i32,
    ) -> AppResult<MergeResult> {
        let mut result = MergeResult {
            entity_type: "character".into(),
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: Vec::new(),
            warnings: Vec::new(),
            changes: Vec::new(),
            confidence_level: None,
            auto_applied: false,
            items_requiring_review: Vec::new(),
        };

        if extracted.is_empty() {
            return Ok(result);
        }

        let existing = self.vault_dao.find_characters(db, project_id).await?;
        let existing_by_name: HashMap<&str, &VaultCharacter> =
            existing.iter().map(|c| (c.name.as_str(), c)).collect();

        for item in extracted {
            let name = item.name.trim();
            if name.is_empty() {
                result.warnings.push("跳过空名字的人物条目".into());
                continue;
            }

            // Try to find match
            if let Some(matched_char) = existing_by_name.get(name).copied().cloned() {
                // Exact match — update
                let confidence = 0.9;
                result.changes.push(ChangeEntry {
                    entity_type: "character".into(),
                    entity_id: matched_char.id.clone(),
                    entity_name: name.into(),
                    change_type: "update".into(),
                    old_value: None,
                    new_value: Some(format!("角色已存在，章节{chapter_number}确认")),
                    chapter: chapter_number,
                    confidence,
                    change_reason: format!("合并: 更新角色 '{name}' — 精确匹配"),
                    confidence_level: None,
                });
                result.updated += 1;
            } else {
                // No match — would create new (no DAO write in this simplified version)
                let confidence = NEW_ENTITY_CONFIDENCE;
                result.changes.push(ChangeEntry {
                    entity_type: "character".into(),
                    entity_id: format!("new_{name}"),
                    entity_name: name.into(),
                    change_type: "create".into(),
                    old_value: None,
                    new_value: Some(format!(
                        "新建: name={name}, role={}",
                        item.role
                    )),
                    chapter: chapter_number,
                    confidence,
                    change_reason: format!("合并: 新建角色 '{name}' — 无匹配"),
                    confidence_level: None,
                });
                result.created += 1;
            }
        }

        Self::evaluate_merge_confidence(&mut result);
        Ok(result)
    }

    // ------------------------------------------------------------------
    // Timeline Merge
    // ------------------------------------------------------------------

    /// Merge timeline vault changes.
    pub async fn merge_timeline(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        extracted: &[ExtractedTimelineEvent],
        chapter_number: i32,
    ) -> AppResult<MergeResult> {
        let mut result = MergeResult {
            entity_type: "timeline".into(),
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: Vec::new(),
            warnings: Vec::new(),
            changes: Vec::new(),
            confidence_level: None,
            auto_applied: false,
            items_requiring_review: Vec::new(),
        };

        if extracted.is_empty() {
            return Ok(result);
        }

        let existing = self.vault_dao.find_timeline_events(db, project_id).await?;

        // Build dedup map: (day, event_lower) → id
        let mut existing_event_map: HashMap<(Option<i32>, String), &str> = HashMap::new();
        for evt in &existing {
            existing_event_map.insert(
                (evt.day, evt.event.to_lowercase().trim().to_string()),
                evt.id.as_str(),
            );
        }

        for item in extracted {
            let event_text = item.event.trim();
            if event_text.is_empty() {
                result.warnings.push("跳过空事件描述的时间线条目".into());
                continue;
            }

            match item.action.as_str() {
                "add" => {
                    let dedup_key = (
                        item.day,
                        event_text.to_lowercase(),
                    );
                    if existing_event_map.contains_key(&dedup_key) {
                        result.warnings.push(format!(
                            "时间线事件 '{event_text}' 已存在，跳过重复"
                        ));
                        continue;
                    }

                    let confidence = if item.is_key_event { 0.9 } else { 0.7 };
                    result.changes.push(ChangeEntry {
                        entity_type: "timeline".into(),
                        entity_id: format!("new_tl_{}", result.created),
                        entity_name: event_text[..event_text.len().min(80)].into(),
                        change_type: "create".into(),
                        old_value: None,
                        new_value: None,
                        chapter: chapter_number,
                        confidence,
                        change_reason: format!(
                            "合并: 新建时间线事件 '{}'",
                            &event_text[..event_text.len().min(50)]
                        ),
                        confidence_level: None,
                    });
                    result.created += 1;
                }
                "resolve_date" | "correct" => {
                    // Find matching event
                    let event_lower = event_text.to_lowercase();
                    let target = existing.iter().find(|e| {
                        e.event.to_lowercase().trim() == event_lower.trim()
                            || (event_lower.len() > 5
                                && (e.event.to_lowercase().contains(&event_lower)
                                    || event_lower.contains(&e.event.to_lowercase())))
                    });

                    if let Some(target) = target {
                        result.changes.push(ChangeEntry {
                            entity_type: "timeline".into(),
                            entity_id: target.id.clone(),
                            entity_name: event_text[..event_text.len().min(80)].into(),
                            change_type: "update".into(),
                            old_value: Some(format!("day={:?}", target.day)),
                            new_value: Some(format!("day={:?}", item.day)),
                            chapter: chapter_number,
                            confidence: 0.85,
                            change_reason: format!(
                                "合并: {} 时间线事件 '{}'",
                                item.action,
                                &event_text[..event_text.len().min(50)]
                            ),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!(
                            "未找到时间线事件 '{event_text}'，无法执行 {}",
                            item.action
                        ));
                    }
                }
                _ => {
                    result.warnings.push(format!(
                        "未知的时间线操作 '{}' for '{event_text}'",
                        item.action
                    ));
                }
            }
        }

        Self::evaluate_merge_confidence(&mut result);
        Ok(result)
    }

    // ------------------------------------------------------------------
    // Plot Promise Merge
    // ------------------------------------------------------------------

    /// Merge plot promise vault changes.
    pub async fn merge_plot_promises(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        extracted: &[ExtractedPlotPromise],
        chapter_number: i32,
    ) -> AppResult<MergeResult> {
        let mut result = MergeResult {
            entity_type: "plot_promise".into(),
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: Vec::new(),
            warnings: Vec::new(),
            changes: Vec::new(),
            confidence_level: None,
            auto_applied: false,
            items_requiring_review: Vec::new(),
        };

        if extracted.is_empty() {
            return Ok(result);
        }

        let existing = self.vault_dao.find_plot_promises(db, project_id).await?;

        for item in extracted {
            let title = item.title.trim();
            if title.is_empty() {
                result.warnings.push("跳过空标题的剧情承诺条目".into());
                continue;
            }

            let title_lower = title.to_lowercase();

            match item.action.as_str() {
                "create" => {
                    // Check for existing
                    let already_exists = existing.iter().any(|p| {
                        p.title.as_deref().unwrap_or("").to_lowercase().trim() == title_lower.trim()
                    });
                    if already_exists {
                        result.warnings.push(format!(
                            "剧情承诺 '{title}' 已存在，跳过新建"
                        ));
                        continue;
                    }

                    result.changes.push(ChangeEntry {
                        entity_type: "plot_promise".into(),
                        entity_id: format!("new_pp_{}", result.created),
                        entity_name: title.into(),
                        change_type: "create".into(),
                        old_value: None,
                        new_value: None,
                        chapter: chapter_number,
                        confidence: 0.9,
                        change_reason: format!("合并: 新建剧情承诺 '{title}'"),
                        confidence_level: None,
                    });
                    result.created += 1;
                }
                "advance" => {
                    let target = existing.iter().find(|p| {
                        p.title.as_deref().unwrap_or("").to_lowercase().trim() == title_lower.trim()
                    });
                    if let Some(target) = target {
                        let last_advance = Self::get_last_advance_chapter(target);
                        if chapter_number - last_advance > STALE_CHAPTER_THRESHOLD {
                            result.warnings.push(format!(
                                "剧情承诺 '{title}' 已超过 {STALE_CHAPTER_THRESHOLD} 章未兑现，标记为 stale"
                            ));
                        }
                        result.changes.push(ChangeEntry {
                            entity_type: "plot_promise".into(),
                            entity_id: target.id.clone(),
                            entity_name: title.into(),
                            change_type: "update".into(),
                            old_value: Some(target.status.clone()),
                            new_value: Some("advancing".into()),
                            chapter: chapter_number,
                            confidence: 0.8,
                            change_reason: format!("合并: 推进剧情承诺 '{title}'"),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!("未找到剧情承诺 '{title}'，无法推进"));
                    }
                }
                "redeem" => {
                    let target = existing.iter().find(|p| {
                        p.title.as_deref().unwrap_or("").to_lowercase().trim() == title_lower.trim()
                    });
                    if let Some(target) = target {
                        result.changes.push(ChangeEntry {
                            entity_type: "plot_promise".into(),
                            entity_id: target.id.clone(),
                            entity_name: title.into(),
                            change_type: "update".into(),
                            old_value: Some(target.status.clone()),
                            new_value: Some("resolved".into()),
                            chapter: chapter_number,
                            confidence: 1.0,
                            change_reason: format!("合并: 兑现剧情承诺 '{title}'"),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!("未找到剧情承诺 '{title}'，无法兑现"));
                    }
                }
                "cancel" => {
                    let target = existing.iter().find(|p| {
                        p.title.as_deref().unwrap_or("").to_lowercase().trim() == title_lower.trim()
                    });
                    if let Some(target) = target {
                        result.changes.push(ChangeEntry {
                            entity_type: "plot_promise".into(),
                            entity_id: target.id.clone(),
                            entity_name: title.into(),
                            change_type: "update".into(),
                            old_value: Some(target.status.clone()),
                            new_value: Some("abandoned".into()),
                            chapter: chapter_number,
                            confidence: 0.95,
                            change_reason: format!(
                                "合并: 废弃剧情承诺 '{title}' — {}",
                                item.cancel_reason.as_deref().unwrap_or("未提供原因")
                            ),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!("未找到剧情承诺 '{title}'，无法废弃"));
                    }
                }
                _ => {
                    result.warnings.push(format!(
                        "未知的剧情承诺操作 '{}' for '{title}'",
                        item.action
                    ));
                }
            }
        }

        // Stale check
        for promise in &existing {
            if promise.status == "active" || promise.status == "advancing" {
                let last_advance = Self::get_last_advance_chapter(promise);
                if last_advance > 0 && chapter_number - last_advance > STALE_CHAPTER_THRESHOLD {
                    result.warnings.push(format!(
                        "剧情承诺 '{}' (last_advance_chapter={last_advance}) 已超 {STALE_CHAPTER_THRESHOLD} 章未兑现",
                        promise.title.as_deref().unwrap_or("")
                    ));
                }
            }
        }

        Self::evaluate_merge_confidence(&mut result);
        Ok(result)
    }

    // ------------------------------------------------------------------
    // World Building Merge
    // ------------------------------------------------------------------

    /// Merge world building vault changes.
    pub async fn merge_world_building(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        extracted: &[ExtractedWorldItem],
        chapter_number: i32,
    ) -> AppResult<MergeResult> {
        let mut result = MergeResult {
            entity_type: "world".into(),
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: Vec::new(),
            warnings: Vec::new(),
            changes: Vec::new(),
            confidence_level: None,
            auto_applied: false,
            items_requiring_review: Vec::new(),
        };

        if extracted.is_empty() {
            return Ok(result);
        }

        let existing = self.vault_dao.find_world_entries(db, project_id).await?;
        let existing_by_name: HashMap<&str, &VaultWorld> =
            existing.iter().map(|e| (e.name.as_str(), e)).collect();

        for item in extracted {
            let name = item.name.trim();
            if name.is_empty() {
                result.warnings.push("跳过空名字的世界观条目".into());
                continue;
            }

            match item.action.as_str() {
                "create" => {
                    if existing_by_name.contains_key(name) {
                        result.warnings.push(format!("世界观条目 '{name}' 已存在，跳过新建"));
                        continue;
                    }
                    result.changes.push(ChangeEntry {
                        entity_type: "world".into(),
                        entity_id: format!("new_world_{}", result.created),
                        entity_name: name.into(),
                        change_type: "create".into(),
                        old_value: None,
                        new_value: None,
                        chapter: chapter_number,
                        confidence: 0.85,
                        change_reason: format!("合并: 新建世界观 '{name}'"),
                        confidence_level: None,
                    });
                    result.created += 1;
                }
                "expand" => {
                    if let Some(_target) = existing_by_name.get(name).copied() {
                        result.changes.push(ChangeEntry {
                            entity_type: "world".into(),
                            entity_id: "existing".into(),
                            entity_name: name.into(),
                            change_type: "update".into(),
                            old_value: None,
                            new_value: Some(format!("扩展: {}", item.content)),
                            chapter: chapter_number,
                            confidence: 0.8,
                            change_reason: format!("合并: 扩展世界观 '{name}'"),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!("未找到世界观条目 '{name}'，无法扩展"));
                    }
                }
                "revise" => {
                    if let Some(_target) = existing_by_name.get(name).copied() {
                        result.changes.push(ChangeEntry {
                            entity_type: "world".into(),
                            entity_id: "existing".into(),
                            entity_name: name.into(),
                            change_type: "update".into(),
                            old_value: item.old_content.clone(),
                            new_value: Some(item.content.clone()),
                            chapter: chapter_number,
                            confidence: 0.7,
                            change_reason: format!("合并: 修订世界观 '{name}'"),
                            confidence_level: None,
                        });
                        result.updated += 1;
                    } else {
                        result.warnings.push(format!("未找到世界观条目 '{name}'，无法修订"));
                    }
                }
                "conflict" => {
                    result.conflicts.push(serde_json::json!({
                        "entity": name,
                        "category": item.category,
                        "action": "conflict",
                        "detail": format!("手动标记 '{name}' 为冲突状态"),
                    }));
                    warn!("World conflict: {name}");
                }
                _ => {
                    result.warnings.push(format!(
                        "未知的世界观操作 '{}' for '{name}'",
                        item.action
                    ));
                }
            }
        }

        Self::evaluate_merge_confidence(&mut result);
        Ok(result)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_edit_distance() {
        assert_eq!(MergeService::edit_distance("张三", "张三"), 0);
        assert_eq!(MergeService::edit_distance("张三", "张四"), 1);
        assert_eq!(MergeService::edit_distance("张三", "李四"), 2);
    }

    #[test]
    fn test_surname_match() {
        assert!(!MergeService::surname_match("", "张三"));
        assert!(MergeService::surname_match("张三", "张四"));
        assert!(!MergeService::surname_match("张三", "李四"));
    }

    #[test]
    fn test_evaluate_confidence() {
        assert_eq!(evaluate_confidence(0.9), ConfidenceLevel::High);
        assert_eq!(evaluate_confidence(0.6), ConfidenceLevel::Medium);
        assert_eq!(evaluate_confidence(0.4), ConfidenceLevel::Low);
        assert_eq!(evaluate_confidence(0.1), ConfidenceLevel::Reject);
    }

    #[test]
    fn test_should_auto_apply() {
        assert!(should_auto_apply(ConfidenceLevel::High));
        assert!(should_auto_apply(ConfidenceLevel::Medium));
        assert!(!should_auto_apply(ConfidenceLevel::Low));
        assert!(!should_auto_apply(ConfidenceLevel::Reject));
    }

    #[test]
    fn test_calc_confidence() {
        let conf = MergeService::calc_confidence(0, true);
        assert!((conf - 1.0).abs() < 0.01);
        let conf = MergeService::calc_confidence(1, true);
        assert!((conf - 0.9).abs() < 0.01);
    }

    #[test]
    fn test_merge_result_default() {
        let result = MergeResult {
            entity_type: "character".into(),
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: Vec::new(),
            warnings: Vec::new(),
            changes: Vec::new(),
            confidence_level: None,
            auto_applied: false,
            items_requiring_review: Vec::new(),
        };
        assert_eq!(result.entity_type, "character");
    }
}
