//! 墨灵 (Moling) — Vault Filter Service (四库过滤算法).
//!
//! Step 2 of the Phase 4 algorithm pipeline: receives a list of CardPool cards,
//! extracts all referenced vault IDs (characters, plot promises, timeline, world),
//! fetches only the matching vault records, applies hierarchical compression based
//! on chapter progress, and returns a structured context payload.
//!
//! Ported from Python `app/service/vault_filter.py`.

use moling_core::error::AppResult;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::{
    vault_character::Model as VaultCharacter,
    vault_plot_promise::Model as VaultPlotPromise,
    vault_timeline::Model as VaultTimeline,
    vault_world::Model as VaultWorld,
};

use sea_orm::DatabaseConnection;
use serde::Serialize;
use tracing::{debug, info};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CHARACTER_MAX_CHARS: usize = 300;
const TIMELINE_WINDOW: usize = 3;
const COMPRESSION_LEVEL_1: i32 = 1;
const COMPRESSION_LEVEL_2: i32 = 2;
const COMPRESSION_THRESHOLD: i32 = 30;
const CHARS_PER_TOKEN: usize = 2;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// Result of a vault filter operation.
#[derive(Debug, Clone, Serialize)]
pub struct VaultFilterResult {
    pub characters: Vec<serde_json::Value>,
    pub timeline: Vec<serde_json::Value>,
    pub plot_promises: Vec<serde_json::Value>,
    pub world: Vec<serde_json::Value>,
    pub compression_level: i32,
    pub token_estimate: u64,
}

/// Minimal card representation for vault filtering.
#[derive(Debug, Clone)]
pub struct FilterCard {
    pub name: Option<String>,
    pub characters: Vec<FilterCharRef>,
    pub plot_promises: Vec<FilterPromiseRef>,
    pub world_rules: Vec<FilterWorldRef>,
    pub timeline_points: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct FilterCharRef {
    pub id: Option<String>,
}

#[derive(Debug, Clone)]
pub struct FilterPromiseRef {
    pub id: Option<String>,
}

#[derive(Debug, Clone)]
pub struct FilterWorldRef {
    pub id: Option<String>,
}

// ---------------------------------------------------------------------------
// VaultFilterService
// ---------------------------------------------------------------------------

/// Vault filter service — extracts vault IDs from cards, fetches matching
/// records, and applies hierarchical compression.
#[derive(Clone)]
pub struct VaultFilterService {
    vault_dao: VaultDao,
}

impl VaultFilterService {
    /// Create a new VaultFilterService.
    pub fn new(vault_dao: VaultDao) -> Self {
        Self { vault_dao }
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// No-card fallback: fetch Top-N vault entries with compression.
    ///
    /// Used when no cards are selected (e.g., Vibe Writing free-input mode).
    pub async fn filter_all(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_number: Option<i32>,
        max_characters: usize,
        max_timeline: usize,
        max_world: usize,
    ) -> AppResult<VaultFilterResult> {
        info!("VaultFilterService.filter_all: project_id={project_id}, chapter={chapter_number:?}");

        let characters: Vec<VaultCharacter> = self
            .vault_dao
            .find_characters(db, project_id)
            .await?
            .into_iter()
            .take(max_characters)
            .collect();

        let all_timeline = self.vault_dao.find_timeline_events(db, project_id).await?;
        let timeline: Vec<VaultTimeline> = all_timeline
            .into_iter()
            .rev()
            .take(max_timeline)
            .rev()
            .collect();

        let promises: Vec<VaultPlotPromise> = self
            .vault_dao
            .find_plot_promises(db, project_id)
            .await?
            .into_iter()
            .filter(|p| p.status == "dormant" || p.status == "active")
            .collect();

        let world: Vec<VaultWorld> = self
            .vault_dao
            .find_world_entries(db, project_id)
            .await?
            .into_iter()
            .take(max_world)
            .collect();

        let compression_level = Self::determine_compression_level(chapter_number);
        let compressed_characters = Self::compress_characters(&characters, compression_level);
        let serialized_timeline: Vec<serde_json::Value> = timeline
            .iter()
            .map(Self::serialize_timeline_event)
            .collect();
        let serialized_promises: Vec<serde_json::Value> = promises
            .iter()
            .map(Self::serialize_promise)
            .collect();
        let serialized_world: Vec<serde_json::Value> = world
            .iter()
            .map(Self::serialize_world_entry)
            .collect();

        let token_estimate = Self::estimate_tokens(
            &compressed_characters,
            &timeline,
            &promises,
            &world,
        );

        info!(
            "VaultFilterService.filter_all result: chars={}, timeline={}, promises={}, world={}, level={compression_level}, tokens={token_estimate}",
            compressed_characters.len(),
            serialized_timeline.len(),
            serialized_promises.len(),
            serialized_world.len(),
        );

        Ok(VaultFilterResult {
            characters: compressed_characters,
            timeline: serialized_timeline,
            plot_promises: serialized_promises,
            world: serialized_world,
            compression_level,
            token_estimate,
        })
    }

    /// Main entry point: filter vault by cards with ID-based extraction.
    pub async fn filter_by_cards(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[FilterCard],
        chapter_number: Option<i32>,
    ) -> AppResult<VaultFilterResult> {
        info!(
            "VaultFilterService.filter_by_cards called: project_id={project_id}, cards={}, chapter={chapter_number:?}",
            cards.len()
        );

        // Step 1: Extract all card-referenced IDs
        let ids = self.extract_card_ids(cards);

        debug!(
            "Extracted IDs: chars={}, promises={}, timeline_points={}, world_rules={}",
            ids.character_ids.len(),
            ids.promise_ids.len(),
            ids.timeline_points.len(),
            ids.world_rule_ids.len(),
        );

        // Step 2: Fetch filtered vault records
        let characters = self
            .fetch_filtered_characters(db, project_id, &ids.character_ids)
            .await?;
        let timeline = self
            .fetch_filtered_timeline(db, project_id, &ids.timeline_points)
            .await?;
        let promises = self
            .fetch_filtered_promises(db, project_id, &ids.promise_ids)
            .await?;
        let world = self
            .fetch_filtered_world(db, project_id, &ids.world_rule_ids)
            .await?;

        // Step 3: Determine compression level
        let compression_level = Self::determine_compression_level(chapter_number);

        // Step 4: Apply hierarchical compression
        let compressed_characters = Self::compress_characters(&characters, compression_level);

        let token_estimate =
            Self::estimate_tokens(&compressed_characters, &timeline, &promises, &world);

        let result = VaultFilterResult {
            characters: compressed_characters,
            timeline: timeline.iter().map(Self::serialize_timeline_event).collect(),
            plot_promises: promises.iter().map(Self::serialize_promise).collect(),
            world: world.iter().map(Self::serialize_world_entry).collect(),
            compression_level,
            token_estimate,
        };

        info!(
            "VaultFilterService result: chars={}, timeline={}, promises={}, world={}, level={}, tokens={}",
            result.characters.len(),
            result.timeline.len(),
            result.plot_promises.len(),
            result.world.len(),
            result.compression_level,
            result.token_estimate,
        );

        Ok(result)
    }

    // ------------------------------------------------------------------
    // Step 1: Extract Card IDs
    // ------------------------------------------------------------------

    /// Extract all referenced IDs from cards.
    pub fn extract_card_ids(&self, cards: &[FilterCard]) -> ExtractedIds {
        let mut character_ids: Vec<String> = Vec::new();
        let mut promise_ids: Vec<String> = Vec::new();
        let mut timeline_points: Vec<String> = Vec::new();
        let mut world_rule_ids: Vec<String> = Vec::new();

        for card in cards {
            // Characters
            for char_ref in &card.characters {
                if let Some(ref cid) = char_ref.id {
                    let trimmed = cid.trim();
                    if !trimmed.is_empty() {
                        character_ids.push(trimmed.to_string());
                    }
                }
            }

            // Plot promises
            for prom_ref in &card.plot_promises {
                if let Some(ref pid) = prom_ref.id {
                    let trimmed = pid.trim();
                    if !trimmed.is_empty() {
                        promise_ids.push(trimmed.to_string());
                    }
                }
            }

            // Timeline points
            for tp in &card.timeline_points {
                let trimmed = tp.trim();
                if !trimmed.is_empty() {
                    timeline_points.push(trimmed.to_string());
                }
            }

            // World rules
            for wr_ref in &card.world_rules {
                if let Some(ref wid) = wr_ref.id {
                    let trimmed = wid.trim();
                    if !trimmed.is_empty() {
                        world_rule_ids.push(trimmed.to_string());
                    }
                }
            }
        }

        // Deduplicate
        character_ids.sort();
        character_ids.dedup();
        promise_ids.sort();
        promise_ids.dedup();
        timeline_points.sort();
        timeline_points.dedup();
        world_rule_ids.sort();
        world_rule_ids.dedup();

        ExtractedIds {
            character_ids,
            promise_ids,
            timeline_points,
            world_rule_ids,
        }
    }

    // ------------------------------------------------------------------
    // Step 2: Fetch filtered vault data
    // ------------------------------------------------------------------

    async fn fetch_filtered_characters(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        character_ids: &[String],
    ) -> AppResult<Vec<VaultCharacter>> {
        if character_ids.is_empty() {
            return Ok(Vec::new());
        }

        let all_chars = self.vault_dao.find_characters(db, project_id).await?;
        let id_set: std::collections::HashSet<&str> =
            character_ids.iter().map(|s| s.as_str()).collect();

        Ok(all_chars
            .into_iter()
            .filter(|c| id_set.contains(c.id.as_str()))
            .collect())
    }

    async fn fetch_filtered_timeline(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        timeline_points: &[String],
    ) -> AppResult<Vec<VaultTimeline>> {
        if timeline_points.is_empty() {
            return Ok(Vec::new());
        }

        let all_events = self.vault_dao.find_timeline_events(db, project_id).await?;
        if all_events.is_empty() {
            return Ok(Vec::new());
        }

        let mut matched_ids: std::collections::HashSet<String> = std::collections::HashSet::new();

        for point in timeline_points {
            // Try parsing chapter numbers
            let parts: Vec<&str> = point.split(&[',', '，', '、'][..]).collect();
            let mut found_by_number = false;

            for part in &parts {
                let trimmed = part.trim();
                if let Ok(cn) = trimmed.parse::<i32>() {
                    found_by_number = true;
                    for (idx, evt) in all_events.iter().enumerate() {
                        if evt.chapter_number == cn {
                            let start = idx.saturating_sub(TIMELINE_WINDOW);
                            let end = std::cmp::min(all_events.len(), idx + TIMELINE_WINDOW + 1);
                            for i in start..end {
                                matched_ids.insert(all_events[i].id.clone());
                            }
                            break;
                        }
                    }
                }
            }

            if !found_by_number {
                // Fuzzy match by event description
                let point_lower = point.to_lowercase();
                for (idx, evt) in all_events.iter().enumerate() {
                    if evt.event.to_lowercase().contains(&point_lower)
                        || evt.description.to_lowercase().contains(&point_lower)
                    {
                        let start = idx.saturating_sub(TIMELINE_WINDOW);
                        let end = std::cmp::min(all_events.len(), idx + TIMELINE_WINDOW + 1);
                        for i in start..end {
                            matched_ids.insert(all_events[i].id.clone());
                        }
                    }
                }
            }
        }

        Ok(all_events
            .into_iter()
            .filter(|e| matched_ids.contains(&e.id))
            .collect())
    }

    async fn fetch_filtered_promises(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        promise_ids: &[String],
    ) -> AppResult<Vec<VaultPlotPromise>> {
        if promise_ids.is_empty() {
            return Ok(Vec::new());
        }

        let all = self.vault_dao.find_plot_promises(db, project_id).await?;
        let id_set: std::collections::HashSet<&str> =
            promise_ids.iter().map(|s| s.as_str()).collect();

        Ok(all
            .into_iter()
            .filter(|p| id_set.contains(p.id.as_str()))
            .collect())
    }

    async fn fetch_filtered_world(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        world_rule_ids: &[String],
    ) -> AppResult<Vec<VaultWorld>> {
        if world_rule_ids.is_empty() {
            return Ok(Vec::new());
        }

        let all = self.vault_dao.find_world_entries(db, project_id).await?;
        let id_set: std::collections::HashSet<&str> =
            world_rule_ids.iter().map(|s| s.as_str()).collect();

        Ok(all
            .into_iter()
            .filter(|w| id_set.contains(w.id.as_str()))
            .collect())
    }

    // ------------------------------------------------------------------
    // Step 3: Compression
    // ------------------------------------------------------------------

    /// Determine compression level based on chapter number.
    pub fn determine_compression_level(chapter_number: Option<i32>) -> i32 {
        match chapter_number {
            None => COMPRESSION_LEVEL_1,
            Some(cn) if cn <= COMPRESSION_THRESHOLD => COMPRESSION_LEVEL_1,
            _ => COMPRESSION_LEVEL_2,
        }
    }

    /// Apply hierarchical compression to character list.
    pub fn compress_characters(
        characters: &[VaultCharacter],
        compression_level: i32,
    ) -> Vec<serde_json::Value> {
        if compression_level == COMPRESSION_LEVEL_2 {
            characters
                .iter()
                .map(|c| {
                    serde_json::json!({
                        "id": c.id,
                        "name": c.name,
                        "role": c.role,
                        "status": c.status,
                        "current_state": c.current_state.as_deref().unwrap_or(""),
                    })
                })
                .collect()
        } else {
            characters
                .iter()
                .map(|c| {
                    let serialized = Self::serialize_character(c);
                    Self::truncate_character_fields(serialized, CHARACTER_MAX_CHARS)
                })
                .collect()
        }
    }

    // ------------------------------------------------------------------
    // Serialization helpers
    // ------------------------------------------------------------------

    /// Serialize a VaultCharacter to JSON.
    pub fn serialize_character(char: &VaultCharacter) -> serde_json::Value {
        serde_json::json!({
            "id": char.id,
            "name": char.name,
            "role": char.role,
            "faction": char.faction.as_deref().unwrap_or(""),
            "status": char.status,
            "location": char.location.as_deref().unwrap_or(""),
            "appearance": char.appearance.as_deref().unwrap_or(""),
            "personality": char.personality.as_deref().unwrap_or(""),
            "knowledge": char.knowledge,
            "confidence": char.confidence,
            "current_state": char.current_state.as_deref().unwrap_or(""),
            "motivation": char.motivation.as_deref().unwrap_or(""),
            "emotion": char.emotion.as_deref().unwrap_or(""),
            "traits": char.traits,
            "description": char.description.as_deref().unwrap_or(""),
            "background": char.background.as_deref().unwrap_or(""),
            "relationships": char.relationships,
            "state_machine": char.state_machine,
        })
    }

    /// Truncate long text fields to stay within character budget.
    pub fn truncate_character_fields(
        data: serde_json::Value,
        max_chars: usize,
    ) -> serde_json::Value {
        let text_fields = [
            "description",
            "background",
            "personality",
            "appearance",
            "motivation",
        ];

        let base_len: usize = data
            .as_object()
            .map(|obj| {
                obj.iter()
                    .filter(|(k, _)| !text_fields.contains(&k.as_str()))
                    .map(|(_, v)| v.to_string().len())
                    .sum()
            })
            .unwrap_or(0);

        let mut available = max_chars.saturating_sub(base_len);
        if available == 0 {
            let mut obj = data.as_object().cloned().unwrap_or_default();
            for field in &text_fields {
                obj.insert(field.to_string(), serde_json::Value::String(String::new()));
            }
            return serde_json::Value::Object(obj);
        }

        let priority = [
            "description",
            "personality",
            "background",
            "motivation",
            "appearance",
        ];

        let mut obj = data.as_object().cloned().unwrap_or_default();
        for field in &priority {
            if let Some(val) = obj.get(*field) {
                let raw = val.as_str().unwrap_or("");
                if available == 0 {
                    obj.insert(field.to_string(), serde_json::Value::String(String::new()));
                } else if raw.len() <= available {
                    available -= raw.len();
                } else if available > 1 {
                    // Find char boundary to avoid splitting multi-byte UTF-8 characters
                    let mut boundary = available;
                    while boundary > 0 && !raw.is_char_boundary(boundary) {
                        boundary -= 1;
                    }
                    obj.insert(
                        field.to_string(),
                        serde_json::Value::String(format!("{}…", &raw[..boundary])),
                    );
                    available = 0;
                } else {
                    obj.insert(field.to_string(), serde_json::Value::String(String::new()));
                    available = 0;
                }
            }
        }

        serde_json::Value::Object(obj)
    }

    /// Serialize a VaultTimeline to JSON.
    pub fn serialize_timeline_event(event: &VaultTimeline) -> serde_json::Value {
        serde_json::json!({
            "id": event.id,
            "event": event.event,
            "description": event.description,
            "chapter_number": event.chapter_number,
            "day": event.day,
            "importance": event.importance.as_deref().unwrap_or(""),
            "is_key_event": event.is_key_event,
            "impact": event.impact.as_deref().unwrap_or(""),
            "characters_involved": event.characters_involved,
            "precedes": event.precedes,
        })
    }

    /// Serialize a VaultPlotPromise to JSON.
    pub fn serialize_promise(promise: &VaultPlotPromise) -> serde_json::Value {
        serde_json::json!({
            "id": promise.id,
            "description": promise.description,
            "type": promise.r#type,
            "title": promise.title.as_deref().unwrap_or(""),
            "status": promise.status,
            "urgency": promise.urgency,
            "advancement_log": promise.advancement_log,
            "related_characters": promise.related_characters,
            "planted_chapter": promise.planted_chapter,
            "redeem_window": promise.redeem_window,
        })
    }

    /// Serialize a VaultWorld to JSON.
    pub fn serialize_world_entry(entry: &VaultWorld) -> serde_json::Value {
        serde_json::json!({
            "id": entry.id,
            "name": entry.name,
            "description": entry.description,
            "category": entry.category,
            "constraint": entry.constraint.as_deref().unwrap_or(""),
            "related_entities": entry.related_entities,
            "source_chapter": entry.source_chapter,
            "reference_chapters": entry.reference_chapters,
        })
    }

    // ------------------------------------------------------------------
    // Token Estimation
    // ------------------------------------------------------------------

    /// Estimate token count from vault content (Chinese chars / 2 ≈ tokens).
    pub fn estimate_tokens(
        characters: &[serde_json::Value],
        timeline: &[VaultTimeline],
        promises: &[VaultPlotPromise],
        world: &[VaultWorld],
    ) -> u64 {
        let mut total_chars: usize = 0;

        for c in characters {
            total_chars += c.to_string().len();
        }

        for e in timeline {
            total_chars += e.event.len() + e.description.len();
            total_chars += e.impact.as_deref().unwrap_or("").len();
        }

        for p in promises {
            total_chars += p.description.len();
            total_chars += p.title.as_deref().unwrap_or("").len();
            if let Some(ref log) = p.advancement_log {
                total_chars += log.to_string().len();
            }
        }

        for w in world {
            total_chars += w.name.len() + w.description.len();
            total_chars += w.constraint.as_deref().unwrap_or("").len();
        }

        std::cmp::max(1, total_chars / CHARS_PER_TOKEN) as u64
    }
}

// ---------------------------------------------------------------------------
// Helper types
// ---------------------------------------------------------------------------

/// Extracted ID sets from cards.
#[derive(Debug, Clone, Default)]
pub struct ExtractedIds {
    pub character_ids: Vec<String>,
    pub promise_ids: Vec<String>,
    pub timeline_points: Vec<String>,
    pub world_rule_ids: Vec<String>,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_determine_compression_level() {
        assert_eq!(VaultFilterService::determine_compression_level(None), 1);
        assert_eq!(
            VaultFilterService::determine_compression_level(Some(5)),
            1
        );
        assert_eq!(
            VaultFilterService::determine_compression_level(Some(30)),
            1
        );
        assert_eq!(
            VaultFilterService::determine_compression_level(Some(31)),
            2
        );
    }

    #[test]
    fn test_truncate_character_fields() {
        let data = serde_json::json!({
            "id": "1",
            "name": "张三",
            "role": "主角",
            "description": "很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长的描述",
            "personality": "温和"
        });
        let result = VaultFilterService::truncate_character_fields(data, 300);
        let desc = result["description"].as_str().unwrap_or("");
        assert!(desc.len() <= 350); // Allow some overhead for the "…" suffix
    }

    #[test]
    fn test_estimate_tokens_empty() {
        let tokens = VaultFilterService::estimate_tokens(&[], &[], &[], &[]);
        assert_eq!(tokens, 1); // Minimum
    }

    #[test]
    fn test_serialize_timeline_event() {
        let event = VaultTimeline {
            id: "1".into(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            is_deleted: false,
            deleted_at: None,
            project_id: 1,
            event: "测试事件".into(),
            description: "描述".into(),
            chapter_number: 1,
            day: Some(1),
            importance: Some("major".into()),
            is_key_event: true,
            characters_involved: None,
            precedes: None,
            impact: Some("大".into()),
            title: None,
            confidence: None,
            source_chapter: None,
        };
        let json = VaultFilterService::serialize_timeline_event(&event);
        assert_eq!(json["event"], "测试事件");
        assert_eq!(json["chapter_number"], 1);
    }
}
