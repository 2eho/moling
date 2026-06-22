//! Card pool service — pool lifecycle management: freshness checking, batch retirement,
//! and replacement card generation.
//!
//! Ported from Python `app/service/card_pool_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::entities::card_pool::Model as CardModel;
use sea_orm::{DatabaseConnection, IntoActiveModel, Set};
use serde_json::Value as Json;

// ---------------------------------------------------------------------------
// Constants — mirrors Python CardPoolService
// ---------------------------------------------------------------------------

/// Each draw reduces freshness score by this amount (capped).
const FRESHNESS_DRAW_PENALTY: f64 = 0.12;
/// Each chapter since creation reduces freshness score.
const FRESHNESS_AGE_PENALTY_PER_CHAPTER: f64 = 0.04;
/// Cards with score below this threshold are stale.
const FRESHNESS_STALE_THRESHOLD: f64 = 0.35;
/// Maximum caps to ensure a minimum floor.
const MAX_DRAW_PENALTY: f64 = 0.6;
const MAX_AGE_PENALTY: f64 = 0.25;

/// Replacement generation config.
const REPLACEMENT_DIRECTIONS: &[&str] = &["stable", "interesting", "stunning", "divine"];
const REPLACEMENT_CATEGORIES: &[&str] = &["character", "plot", "world", "conflict", "theme"];

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Service for card pool lifecycle management.
///
/// Handles freshness evaluation, batch retirement, and replacement card generation
/// for background worker consumption.
#[derive(Clone)]
pub struct CardPoolService {
    card_dao: CardDao,
    project_dao: ProjectDao,
}

impl CardPoolService {
    pub fn new() -> Self {
        Self { card_dao: CardDao, project_dao: ProjectDao }
    }

    // -- ownership helper --

    async fn verify_owner(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
    ) -> AppResult<()> {
        let p = self.project_dao.find_by_id(db, project_id).await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(())
    }

    // ==================================================================
    // Freshness calculations
    // ==================================================================

    /// Calculate freshness score for a single card in [0.0, 1.0].
    ///
    /// Higher score = fresher / should be retained.
    ///
    /// Formula:
    ///   score = 1.0 - min(draws × 0.12, 0.6) - min(chapter × 0.04, 0.25) + (never_drawn ? 0.1 : 0)
    pub fn calc_freshness_score(card: &CardModel) -> f64 {
        let mut score = 1.0;

        // Draw count penalty
        let draws = card.draw_count as f64;
        let draw_penalty = (draws * FRESHNESS_DRAW_PENALTY).min(MAX_DRAW_PENALTY);
        score -= draw_penalty;

        // Age penalty
        if let Some(fc) = card.freshness_chapter {
            let age_penalty = (fc as f64 * FRESHNESS_AGE_PENALTY_PER_CHAPTER).min(MAX_AGE_PENALTY);
            score -= age_penalty;
        }

        // Never-drawn bonus
        if card.draw_count == 0 {
            score += 0.1;
        }

        score.clamp(0.0, 1.0)
    }

    // ==================================================================
    // Freshness checking
    // ==================================================================

    /// Evaluate freshness of all active cards in a project.
    ///
    /// Returns a dict with project_id, total_cards, fresh_count, stale_count,
    /// and stale_cards (list of card IDs below the freshness threshold).
    pub async fn check_freshness(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Json> {
        let cards = self.card_dao.list_active_by_project(db, project_id).await?;

        let mut stale_ids: Vec<String> = Vec::new();
        for card in &cards {
            let score = Self::calc_freshness_score(card);
            if score < FRESHNESS_STALE_THRESHOLD {
                stale_ids.push(card.id.clone());
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "total_cards": cards.len(),
            "fresh_count": cards.len() - stale_ids.len(),
            "stale_count": stale_ids.len(),
            "stale_cards": stale_ids,
            "freshness_scores": cards.iter().map(|c| serde_json::json!({
                "card_id": c.id,
                "name": c.name,
                "score": (Self::calc_freshness_score(c) * 100.0).round() / 100.0,
                "draws": c.draw_count,
                "freshness_chapter": c.freshness_chapter,
            })).collect::<Vec<_>>(),
        }))
    }

    /// Check freshness for a user's project (with ownership verification).
    pub async fn check_freshness_for_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;
        self.check_freshness(db, project_id).await
    }

    // ==================================================================
    // Batch retirement
    // ==================================================================

    /// Mark cards as retired (is_active=false, status='retired').
    ///
    /// Returns the count and IDs of retired cards.
    pub async fn retire_cards(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        card_ids: &[String],
    ) -> AppResult<Json> {
        if card_ids.is_empty() {
            return Ok(serde_json::json!({
                "project_id": project_id,
                "retired_count": 0,
                "retired_ids": [],
            }));
        }

        let cards = self.card_dao.get_by_ids(db, project_id, card_ids).await?;

        let mut retired_ids: Vec<String> = Vec::new();
        for card in &cards {
            let mut active = card.clone().into_active_model();
            active.is_active = Set(false);
            active.status = Set("retired".to_owned());
            active.retired_chapter = Set(Some(0));
            if let Err(e) = self.card_dao.update_card(db, active).await {
                tracing::warn!("Failed to retire card {}: {}", card.id, e);
            } else {
                retired_ids.push(card.id.clone());
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "retired_count": retired_ids.len(),
            "retired_ids": retired_ids,
        }))
    }

    /// Batch retire using the efficient batch update method.
    pub async fn batch_retire(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        card_ids: &[String],
    ) -> AppResult<u64> {
        self.card_dao.batch_retire(db, project_id, card_ids, false).await
    }

    // ==================================================================
    // Replacement card generation
    // ==================================================================

    /// Generate placeholder replacement cards to fill gaps in the pool.
    ///
    /// Analyzes the current pool for under-represented direction types
    /// and categories, then produces placeholder card dicts compatible
    /// with the CardPool model.
    ///
    /// Returns a list of card dictionaries (not persisted).
    pub async fn generate_replacements(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        count: usize,
    ) -> AppResult<Vec<Json>> {
        let existing = self.card_dao.list_active_by_project(db, project_id).await?;

        // Build direction-type frequency map
        let mut direction_counts: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for card in &existing {
            *direction_counts.entry(card.direction_type.clone()).or_default() += 1;
        }

        // Determine under-represented directions
        let avg_per_direction = std::cmp::max(1, existing.len() / REPLACEMENT_DIRECTIONS.len());
        let under_repr: Vec<&str> = REPLACEMENT_DIRECTIONS.iter()
            .filter(|d| direction_counts.get(&d[..]).copied().unwrap_or(0) < avg_per_direction)
            .copied()
            .collect();
        let pool_directions: Vec<&str> = if under_repr.is_empty() {
            REPLACEMENT_DIRECTIONS.to_vec()
        } else {
            under_repr
        };

        let mut replacements: Vec<Json> = Vec::with_capacity(count);
        for i in 0..count {
            let direction = pool_directions[i % pool_directions.len()];
            let category = REPLACEMENT_CATEGORIES[i % REPLACEMENT_CATEGORIES.len()];

            replacements.push(serde_json::json!({
                "project_id": project_id.to_string(),
                "name": format!("替换卡 {}", i + 1),
                "description": "",
                "rarity": "common",
                "direction_type": direction,
                "direction_text": format!("参考 {} 方向，{} 类别生成新灵感", direction, category),
                "category": category,
                "type": "auto_replacement",
                "source_label": "卡池替换",
                "is_active": true,
                "status": "active",
                "tags": [category, direction],
                "draw_count": 0,
                "pick_count": 0,
            }));
        }

        Ok(replacements)
    }

    /// Generate replacements and immediately create them in the database.
    pub async fn generate_and_create_replacements(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        count: usize,
    ) -> AppResult<Json> {
        let replacements = self.generate_replacements(db, project_id, count).await?;

        let mut created: Vec<Json> = Vec::new();
        for card_data in &replacements {
            let model = moling_db::entities::card_pool::ActiveModel {
                id: Set(uuid::Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                name: Set(card_data.get("name").and_then(|v| v.as_str()).unwrap_or("替换卡").to_owned()),
                description: Set(card_data.get("description").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
                rarity: Set(card_data.get("rarity").and_then(|v| v.as_str()).unwrap_or("common").to_owned()),
                direction_type: Set(card_data.get("direction_type").and_then(|v| v.as_str()).unwrap_or("stable").to_owned()),
                direction_text: Set(card_data.get("direction_text").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
                source_label: Set("卡池替换".to_owned()),
                r#type: Set(Some("auto_replacement".to_owned())),
                is_active: Set(true),
                status: Set("active".to_owned()),
                tags: Set(card_data.get("tags").cloned()),
                draw_count: Set(0),
                pick_count: Set(0),
                ..Default::default()
            };
            match self.card_dao.create_card(db, model).await {
                Ok(card) => {
                    created.push(serde_json::json!({
                        "id": card.id, "name": card.name, "rarity": card.rarity,
                    }));
                }
                Err(e) => {
                    tracing::warn!("Failed to create replacement card: {e}");
                }
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "requested": count,
            "created": created.len(),
            "cards": created,
        }))
    }

    // ==================================================================
    // Pool stats and health
    // ==================================================================

    /// Get comprehensive pool statistics.
    pub async fn pool_stats(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;
        let cards = self.card_dao.list_active_by_project(db, project_id).await?;

        let total = cards.len();
        let mut by_rarity: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        let mut by_direction: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        let mut total_draws: i32 = 0;
        let mut stale_count = 0;

        for c in &cards {
            *by_rarity.entry(c.rarity.clone()).or_default() += 1;
            *by_direction.entry(c.direction_type.clone()).or_default() += 1;
            total_draws += c.draw_count;
            if Self::calc_freshness_score(c) < FRESHNESS_STALE_THRESHOLD {
                stale_count += 1;
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "total_active": total,
            "stale_count": stale_count,
            "fresh_count": total - stale_count,
            "total_draws": total_draws,
            "avg_draws_per_card": if total > 0 { total_draws as f64 / total as f64 } else { 0.0 },
            "by_rarity": by_rarity,
            "by_direction": by_direction,
            "pool_health": if total > 0 {
                format!("{:.0}%", ((total - stale_count) as f64 / total as f64 * 100.0))
            } else {
                "N/A".to_owned()
            },
        }))
    }

    /// Refresh the card pool: retire stale cards and generate replacements.
    pub async fn refresh_pool(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Json> {
        // Check freshness
        let freshness = self.check_freshness(db, project_id).await?;
        let stale_ids: Vec<String> = freshness.get("stale_cards")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|v| v.as_str().map(|s| s.to_owned())).collect())
            .unwrap_or_default();

        let stale_count = stale_ids.len();

        // Retire stale cards
        let retire_result = if !stale_ids.is_empty() {
            self.retire_cards(db, project_id, &stale_ids).await?
        } else {
            serde_json::json!({"retired_count": 0, "retired_ids": []})
        };

        // Generate replacements
        let replacements = self.generate_and_create_replacements(db, project_id, stale_count.max(3)).await?;

        Ok(serde_json::json!({
            "project_id": project_id,
            "before": freshness,
            "retired": retire_result,
            "replacements": replacements,
        }))
    }
}

impl Default for CardPoolService {
    fn default() -> Self { Self::new() }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test_card(id: &str, draws: i32, freshness_ch: Option<i32>) -> CardModel {
        CardModel {
            id: id.to_owned(),
            project_id: 1,
            name: "Test".to_owned(),
            description: String::new(),
            rarity: "common".to_owned(),
            direction_type: "stable".to_owned(),
            direction_text: String::new(),
            draw_count: draws,
            freshness_chapter: freshness_ch,
            is_active: true,
            status: "active".to_owned(),
            r#type: None,
            source_label: "初始卡池".to_owned(),
            pick_count: 0,
            last_drawn_chapter: None,
            source_chapter: None,
            tags: None,
            retired_chapter: None,
            rarity_weight: None,
            characters: None,
            plot_promises: None,
            timeline_point: None,
            world_rules: None,
            current_story_state: None,
            unresolved_hooks: None,
            dynamic_conflict_score: None,
            remaining_lifetime: None,
            embedding: None,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            is_deleted: false,
            deleted_at: None,
        }
    }

    #[test]
    fn test_card_pool_service_constructs() {
        let _ = CardPoolService::new();
    }

    #[test]
    fn test_calc_freshness_score_baseline() {
        let model = make_test_card("test", 0, Some(2));
        let score = CardPoolService::calc_freshness_score(&model);
        // 1.0 - 0.0 - (2 * 0.04) + 0.1 = 1.02 → clamped to 1.0
        assert!((score - 1.0).abs() < 0.01, "Expected ~1.0, got {}", score);
    }

    #[test]
    fn test_calc_freshness_score_stale() {
        let model = make_test_card("stale", 8, Some(10));
        let score = CardPoolService::calc_freshness_score(&model);
        // 1.0 - min(8*0.12, 0.6) - min(10*0.04, 0.25) + 0.0 = 1.0 - 0.6 - 0.25 = 0.15
        assert!(score < FRESHNESS_STALE_THRESHOLD, "Expected stale, got {}", score);
    }
}
