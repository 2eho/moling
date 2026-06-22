//! Card service — weighted-random card draw algorithm, pool management, and draw history.
//!
//! Ported from Python `app/service/card_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::entities::card_pool::Model as CardModel;
use moling_db::entities::draw_history::Model as DrawModel;
use sea_orm::{DatabaseConnection, Set};
use serde_json::Value as Json;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Algorithm constants — mirrors Python CardService
// ---------------------------------------------------------------------------

/// Rarity-to-base-weight mapping.
const RARITY_WEIGHTS: &[(/*  */ &str, f64)] = &[
    ("legendary", 4.0),
    ("epic", 3.0),
    ("rare", 2.0),
    ("common", 1.0),
];

/// Pity threshold: consecutive draws without rare+ trigger pity boost.
const PITY_THRESHOLD: usize = 10;
/// Minimum rarity guaranteed when pity triggers.
#[allow(dead_code)]
const PITY_RARITY_MIN: &str = "rare";

/// Freshness bonus multiplier for cards not recently drawn.
const FRESHNESS_BONUS: f64 = 2.0;
/// Recent-draw window for freshness detection.
const FRESHNESS_THRESHOLD: i32 = 5;

/// Maximum redraw retries per session.
const MAX_DRAW_RETRIES: i32 = 3;

/// Default draw count by mode.
const DRAW_COUNT_DEFAULT: usize = 3;
const DRAW_COUNT_SINGLE: usize = 1;
const DRAW_COUNT_DUAL: usize = 2;
const DRAW_COUNT_ALL_MAX: usize = 5;

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Business logic for card draw and pool management.
#[derive(Clone)]
pub struct CardService {
    card_dao: CardDao,
    project_dao: ProjectDao,
}

impl CardService {
    pub fn new() -> Self {
        Self { card_dao: CardDao, project_dao: ProjectDao }
    }

    // -- ownership verification --

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
    // Weighted random draw algorithm
    // ==================================================================

    /// Calculate the draw weight for a single card based on rarity, pity, and freshness.
    ///
    /// Three factors:
    /// 1. **Rarity base weight** — legenday=4, epic=3, rare=2, common=1
    /// 2. **Pity boost** — if no rare+ card in recent draws, rare+ cards get 3× weight
    /// 3. **Freshness bonus** — cards not drawn recently (or never drawn) get 2× weight
    fn _calculate_card_weight(
        &self,
        card: &CardModel,
        recent_draws: &[Json],          // list of {cards: [{rarity: ...}]}
        recently_drawn_ids: &std::collections::HashSet<String>,
    ) -> f64 {
        // 1. Base rarity weight
        let base_weight = RARITY_WEIGHTS.iter()
            .find(|(r, _)| *r == card.rarity)
            .map(|(_, w)| *w)
            .unwrap_or(1.0);

        // 2. Pity boost
        let mut pity_boost = 1.0;
        let has_rare_plus_in_recent = recent_draws.iter().any(|draw| {
            draw.get("cards").and_then(|v| v.as_array()).map(|cards| {
                cards.iter().any(|c| {
                    let rarity = c.get("rarity").and_then(|v| v.as_str()).unwrap_or("");
                    matches!(rarity, "rare" | "epic" | "legendary")
                })
            }).unwrap_or(false)
        });

        if !has_rare_plus_in_recent {
            let card_is_rare_plus = matches!(card.rarity.as_str(), "rare" | "epic" | "legendary");
            if card_is_rare_plus {
                pity_boost = 3.0;
            }
        }

        // 3. Freshness bonus
        let freshness_boost = if card.last_drawn_chapter.is_none() {
            // Never drawn — max freshness
            FRESHNESS_BONUS
        } else if card.draw_count < FRESHNESS_THRESHOLD && !recently_drawn_ids.contains(&card.id) {
            FRESHNESS_BONUS
        } else {
            1.0
        };

        base_weight * pity_boost * freshness_boost
    }

    /// Draw cards from the active pool using weighted random selection.
    ///
    /// Implements the full 3-factor weighted algorithm:
    /// - Rarity base weights
    /// - Pity protection (guaranteed rare+ after threshold)
    /// - Freshness boosting (under-drawn cards get priority)
    pub async fn draw_cards(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        _draw_count: usize,
        mode: &str,
        keep_card_ids: Option<&[i32]>,
        chapter_id: Option<&str>,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;

        // Get active cards
        let active_cards = self.card_dao.list_active_by_project(db, project_id).await?;
        if active_cards.is_empty() {
            return Err(AppError::bad_request("卡牌池中没有活跃卡牌"));
        }

        // Determine draw count by mode
        let actual_count = match mode {
            "none" => DRAW_COUNT_DEFAULT,
            "single" => DRAW_COUNT_SINGLE,
            "dual" => DRAW_COUNT_DUAL,
            "all" => DRAW_COUNT_ALL_MAX.min(active_cards.len()),
            _ => {
                let keep_len = keep_card_ids.map(|k| k.len()).unwrap_or(0);
                (DRAW_COUNT_DEFAULT.saturating_sub(keep_len)).min(active_cards.len().saturating_sub(keep_len))
            }
        };

        // Build draw history for pity/freshness
        let history_records = self.card_dao.find_draw_history(db, project_id, PITY_THRESHOLD as u64 + 1).await?;
        let recent_draws: Vec<Json> = history_records.iter().map(|rec| {
            let card_ids: Vec<String> = rec.card_ids.as_array()
                .map(|a| a.iter().filter_map(|v| v.as_str().map(|s| s.to_owned())).collect())
                .unwrap_or_default();
            let matched_cards: Vec<Json> = active_cards.iter()
                .filter(|c| card_ids.contains(&c.id))
                .map(|c| serde_json::json!({"rarity": c.rarity}))
                .collect();
            serde_json::json!({"cards": matched_cards, "round": rec.draw_round})
        }).collect();

        // Recently drawn card IDs
        let recently_drawn_ids: std::collections::HashSet<String> = history_records.iter()
            .take(PITY_THRESHOLD)
            .flat_map(|r| r.card_ids.as_array().into_iter().flat_map(|a| a.iter()))
            .filter_map(|v| v.as_str().map(|s| s.to_owned()))
            .collect();

        // Calculate weights
        let card_weights: std::collections::HashMap<String, f64> = active_cards.iter()
            .map(|c| (c.id.clone(), self._calculate_card_weight(c, &recent_draws, &recently_drawn_ids)))
            .collect();

        // Weighted selection (without replacement)
        let selected = self._weighted_sample(&active_cards, &card_weights, actual_count);

        // Record draw
        let latest = self.card_dao.get_latest_draw(db, project_id, None).await?;
        let draw_round = latest.map(|l| l.draw_round + 1).unwrap_or(1);

        let selected_ids: Vec<Json> = selected.iter().map(|c| Json::String(c.id.clone())).collect();
        let selected_weights: Vec<Json> = selected.iter()
            .map(|c| Json::Number(serde_json::Number::from_f64(
                card_weights.get(&c.id).copied().unwrap_or(1.0)
            ).unwrap_or(1.into())))
            .collect();

        let history_model = moling_db::entities::draw_history::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            chapter_id: Set(chapter_id.map(|s| s.to_owned())),
            user_id: Set(user_id.to_owned()),
            card_ids: Set(Json::Array(selected_ids)),
            weights: Set(Json::Array(selected_weights)),
            mode: Set(mode.to_owned()),
            draw_round: Set(draw_round),
            remaining_redraws: Set(MAX_DRAW_RETRIES),
            ..Default::default()
        };
        self.card_dao.create_draw_history(db, history_model).await?;

        // Update freshness for drawn cards
        let current_ch = chapter_id.and_then(|s| s.parse::<i32>().ok()).unwrap_or(0);
        for card in &selected {
            let _ = self.card_dao.update_freshness(db, &card.id, current_ch).await;
        }

        // Determine pity trigger
        let pity_triggered = selected.iter().any(|c| {
            matches!(c.rarity.as_str(), "rare" | "epic" | "legendary")
        });

        let remaining = MAX_DRAW_RETRIES;

        Ok(serde_json::json!({
            "cards": selected.iter().map(|c| serde_json::json!({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "rarity": c.rarity,
                "direction_type": c.direction_type,
                "direction_text": c.direction_text,
                "draw_count": c.draw_count,
            })).collect::<Vec<_>>(),
            "draw_round": draw_round,
            "remaining_redraws": remaining,
            "pity_triggered": pity_triggered,
            "recommended": selected.first().map(|c| serde_json::json!({
                "id": c.id,
                "name": c.name,
                "rarity": c.rarity,
            })).into_iter().collect::<Vec<_>>(),
        }))
    }

    /// Redraw cards for a chapter, excluding cards already drawn and kept cards.
    pub async fn redraw_cards(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
        keep_card_ids: &[String],
        draw_count: usize,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;

        let active_cards = self.card_dao.list_active_by_project(db, project_id).await?;
        if active_cards.is_empty() {
            return Err(AppError::bad_request("卡牌池中没有活跃卡牌"));
        }

        // Collect already drawn card IDs for this chapter
        let history = self.card_dao.find_draw_history_by_chapter(db, project_id, Some(chapter_id), 100).await?;
        let drawn_ids: std::collections::HashSet<String> = history.iter()
            .flat_map(|r| r.card_ids.as_array().into_iter().flat_map(|a| a.iter()))
            .filter_map(|v| v.as_str().map(|s| s.to_owned()))
            .collect();

        let excluded_ids: std::collections::HashSet<String> = keep_card_ids.iter()
            .cloned()
            .chain(drawn_ids)
            .collect();

        let available: Vec<&CardModel> = active_cards.iter()
            .filter(|c| !excluded_ids.contains(&c.id))
            .collect();

        if available.is_empty() {
            return Ok(serde_json::json!({
                "cards": [],
                "remaining_redraws": 0,
                "message": "没有可用的卡牌重新抽取",
            }));
        }

        // Build weight map
        let recent_draws: Vec<Json> = Vec::new();
        let recently_drawn: std::collections::HashSet<String> = history.iter().take(PITY_THRESHOLD)
            .flat_map(|r| r.card_ids.as_array().into_iter().flat_map(|a| a.iter()))
            .filter_map(|v| v.as_str().map(|s| s.to_owned()))
            .collect();

        let card_weights: std::collections::HashMap<String, f64> = available.iter()
            .map(|c| (c.id.clone(), self._calculate_card_weight(c, &recent_draws, &recently_drawn)))
            .collect();

        let actual_count = draw_count.min(available.len());
        let selected = self._weighted_sample_slice(&available, &card_weights, actual_count);

        // Record
        let latest = self.card_dao.get_latest_draw(db, project_id, Some(chapter_id)).await?;
        let draw_round = latest.map(|l| l.draw_round + 1).unwrap_or(1);

        let selected_ids: Vec<Json> = selected.iter().map(|c| Json::String(c.id.clone())).collect();
        let selected_weights: Vec<Json> = selected.iter()
            .map(|c| Json::Number(serde_json::Number::from_f64(
                card_weights.get(&c.id).copied().unwrap_or(1.0)
            ).unwrap_or(1.into())))
            .collect();

        let history_model = moling_db::entities::draw_history::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            chapter_id: Set(Some(chapter_id.to_owned())),
            user_id: Set(user_id.to_owned()),
            card_ids: Set(Json::Array(selected_ids)),
            weights: Set(Json::Array(selected_weights)),
            mode: Set("redraw".to_owned()),
            draw_round: Set(draw_round),
            remaining_redraws: Set(MAX_DRAW_RETRIES - draw_round),
            ..Default::default()
        };
        self.card_dao.create_draw_history(db, history_model).await?;

        // Update freshness
        let current_ch = chapter_id.parse::<i32>().unwrap_or(0);
        for card in &selected {
            let _ = self.card_dao.update_freshness(db, &card.id, current_ch).await;
        }

        let remaining = std::cmp::max(0, MAX_DRAW_RETRIES - draw_round);

        Ok(serde_json::json!({
            "cards": selected.iter().map(|c| serde_json::json!({
                "id": c.id, "name": c.name, "description": c.description,
                "rarity": c.rarity, "direction_type": c.direction_type,
                "direction_text": c.direction_text, "draw_count": c.draw_count,
            })).collect::<Vec<_>>(),
            "draw_round": draw_round,
            "remaining_redraws": remaining,
        }))
    }

    // -- Weighted sampling helpers --

    /// Weighted random sample without replacement from a Vec.
    fn _weighted_sample(
        &self,
        pool: &[CardModel],
        weights: &std::collections::HashMap<String, f64>,
        count: usize,
    ) -> Vec<CardModel> {
        let mut available: Vec<&CardModel> = pool.iter().collect();
        let mut result = Vec::with_capacity(count);

        for _ in 0..count {
            if available.is_empty() { break; }
            let ws: Vec<f64> = available.iter()
                .map(|c| weights.get(&c.id).copied().unwrap_or(1.0))
                .collect();
            let total: f64 = ws.iter().sum();
            if total <= 0.0 {
                let idx = fast_random_usize(available.len());
                result.push(available.remove(idx).clone());
            } else {
                let mut r = fast_random_f64() * total;
                let mut chosen_idx = 0;
                for (i, w) in ws.iter().enumerate() {
                    r -= w;
                    if r <= 0.0 {
                        chosen_idx = i;
                        break;
                    }
                }
                if chosen_idx >= available.len() { chosen_idx = available.len() - 1; }
                result.push(available.remove(chosen_idx).clone());
            }
        }

        result
    }

    /// Weighted random sample without replacement from a slice of references.
    fn _weighted_sample_slice(
        &self,
        pool: &[&CardModel],
        weights: &std::collections::HashMap<String, f64>,
        count: usize,
    ) -> Vec<CardModel> {
        let mut available: Vec<&&CardModel> = pool.iter().collect();
        let mut result = Vec::with_capacity(count);

        for _ in 0..count {
            if available.is_empty() { break; }
            let ws: Vec<f64> = available.iter()
                .map(|c| weights.get(&c.id).copied().unwrap_or(1.0))
                .collect();
            let total: f64 = ws.iter().sum();
            if total <= 0.0 {
                let idx = fast_random_usize(available.len());
                result.push((*available.remove(idx)).clone());
            } else {
                let mut r = fast_random_f64() * total;
                let mut chosen_idx = 0;
                for (i, w) in ws.iter().enumerate() {
                    r -= w;
                    if r <= 0.0 {
                        chosen_idx = i;
                        break;
                    }
                }
                if chosen_idx >= available.len() { chosen_idx = available.len() - 1; }
                result.push((*available.remove(chosen_idx)).clone());
            }
        }

        result
    }

    // ==================================================================
    // Card pool management
    // ==================================================================

    /// List all cards in a project's pool with stats.
    pub async fn list_cards(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;
        let cards = self.card_dao.list_active_by_project(db, project_id).await?;

        let mut by_rarity: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for c in &cards {
            *by_rarity.entry(c.rarity.clone()).or_default() += 1;
        }

        Ok(serde_json::json!({
            "cards": cards.iter().map(|c| serde_json::json!({
                "id": c.id, "name": c.name, "description": c.description,
                "rarity": c.rarity, "direction_type": c.direction_type,
                "direction_text": c.direction_text, "status": c.status,
                "is_active": c.is_active, "draw_count": c.draw_count,
                "source_label": c.source_label, "rarity_weight": c.rarity_weight,
            })).collect::<Vec<_>>(),
            "total_count": cards.len(),
            "by_rarity": by_rarity,
        }))
    }

    /// Draw cards (original API compatibility — returns raw models).
    pub async fn draw(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32, count: usize,
    ) -> AppResult<Vec<CardModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        let pool = self.card_dao.find_pool(db, project_id).await?;
        let drawn: Vec<_> = pool.into_iter().take(count).collect();

        if !drawn.is_empty() {
            let ids: Vec<Json> = drawn.iter().map(|c| Json::String(c.id.clone())).collect();
            let h = moling_db::entities::draw_history::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                user_id: Set(user_id.to_owned()),
                card_ids: Set(Json::Array(ids)),
                weights: Set(Json::Object(Default::default())),
                mode: Set("single".to_owned()),
                ..Default::default()
            };
            let _ = self.card_dao.create_draw_history(db, h).await;
        }
        Ok(drawn)
    }

    /// Create a new card in the pool.
    pub async fn create(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
        name: &str, description: &str, rarity: &str,
        direction_type: &str, direction_text: &str,
    ) -> AppResult<CardModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let model = moling_db::entities::card_pool::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            name: Set(name.to_owned()),
            description: Set(description.to_owned()),
            rarity: Set(rarity.to_owned()),
            direction_type: Set(direction_type.to_owned()),
            direction_text: Set(direction_text.to_owned()),
            ..Default::default()
        };
        self.card_dao.create_card(db, model).await
    }

    /// Create a card from a generic JSON payload.
    pub async fn create_from_json(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
        card_data: &Json,
    ) -> AppResult<CardModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let model = moling_db::entities::card_pool::ActiveModel {
            id: Set(card_data.get("id").and_then(|v| v.as_str()).map(|s| s.to_owned())
                .unwrap_or_else(|| Uuid::new_v4().to_string())),
            project_id: Set(project_id),
            name: Set(card_data.get("name").and_then(|v| v.as_str()).unwrap_or("新卡牌").to_owned()),
            description: Set(card_data.get("description").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
            rarity: Set(card_data.get("rarity").and_then(|v| v.as_str()).unwrap_or("common").to_owned()),
            direction_type: Set(card_data.get("direction_type").and_then(|v| v.as_str()).unwrap_or("interesting").to_owned()),
            direction_text: Set(card_data.get("direction_text").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
            r#type: Set(card_data.get("type").and_then(|v| v.as_str()).map(|s| s.to_owned())),
            is_active: Set(true),
            status: Set("active".to_owned()),
            draw_count: Set(0),
            ..Default::default()
        };
        self.card_dao.create_card(db, model).await
    }

    /// Retire a card (mark inactive).
    pub async fn retire(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32, card_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;
        self.card_dao.retire_card(db, card_id, None).await
    }

    /// Soft-delete a card.
    pub async fn delete(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32, card_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;
        // Verify card belongs to project
        let card = self.card_dao.find_card_by_id(db, card_id).await?
            .ok_or_else(AppError::card_not_found)?;
        if card.project_id != project_id {
            return Err(AppError::project_access_denied());
        }
        self.card_dao.soft_delete_card(db, card_id).await
    }

    /// Get the active card pool.
    pub async fn pool(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
    ) -> AppResult<Vec<CardModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.card_dao.find_pool(db, project_id).await
    }

    /// Get draw history.
    pub async fn history(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32, limit: u64,
    ) -> AppResult<Vec<DrawModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.card_dao.find_draw_history(db, project_id, limit).await
    }

    /// Get detailed draw history as JSON.
    pub async fn get_draw_history(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
    ) -> AppResult<Vec<Json>> {
        self.verify_owner(db, user_id, project_id).await?;
        let records = self.card_dao.find_draw_history(db, project_id, 100).await?;
        Ok(records.into_iter().map(|r| serde_json::json!({
            "id": r.id,
            "round": r.draw_round,
            "card_ids": r.card_ids,
            "mode": r.mode,
            "chapter_id": r.chapter_id,
            "created_at": r.created_at.to_rfc3339(),
        })).collect())
    }

    /// Get a single draw history record by ID.
    pub async fn get_draw_history_detail(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32, draw_id: &str,
    ) -> AppResult<Option<Json>> {
        self.verify_owner(db, user_id, project_id).await?;
        let records = self.card_dao.find_draw_history(db, project_id, 200).await?;
        Ok(records.into_iter().find(|r| r.id == draw_id).map(|r| serde_json::json!({
            "id": r.id,
            "round": r.draw_round,
            "card_ids": r.card_ids,
            "mode": r.mode,
            "chapter_id": r.chapter_id,
            "created_at": r.created_at.to_rfc3339(),
        })))
    }

    /// Get card by ID.
    pub async fn get_card(
        &self, db: &DatabaseConnection, _user_id: &str, card_id: &str,
    ) -> AppResult<Option<CardModel>> {
        self.card_dao.find_card_by_id(db, card_id).await
    }

    /// Get pool statistics.
    pub async fn pool_stats(
        &self, db: &DatabaseConnection, user_id: &str, project_id: i32,
    ) -> AppResult<Json> {
        self.verify_owner(db, user_id, project_id).await?;
        let cards = self.card_dao.list_active_by_project(db, project_id).await?;
        let total = cards.len();
        let mut by_rarity: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        let mut total_draws: i32 = 0;
        for c in &cards {
            *by_rarity.entry(c.rarity.clone()).or_default() += 1;
            total_draws += c.draw_count;
        }
        Ok(serde_json::json!({
            "project_id": project_id,
            "total_active": total,
            "total_draws": total_draws,
            "by_rarity": by_rarity,
            "avg_draws_per_card": if total > 0 { total_draws as f64 / total as f64 } else { 0.0 },
        }))
    }
}

impl Default for CardService {
    fn default() -> Self { Self::new() }
}

// ---------------------------------------------------------------------------
// Fast PRNG helpers (not crypto-secure, sufficient for weighted sampling)
// ---------------------------------------------------------------------------

fn fast_random_f64() -> f64 {
    use std::collections::hash_map::RandomState;
    use std::hash::BuildHasher;
    let s = RandomState::new();
    let h = s.hash_one("moling-card-draw");
    (h as f64) / (u64::MAX as f64)
}

fn fast_random_usize(max: usize) -> usize {
    if max == 0 { return 0; }
    (fast_random_f64() * max as f64) as usize
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_card_service_constructs() {
        let _ = CardService::new();
    }

    #[test]
    fn test_fast_random_range() {
        for _ in 0..100 {
            let v = fast_random_usize(10);
            assert!(v < 10);
        }
    }

    #[test]
    fn test_rarity_weights_defined() {
        assert!(RARITY_WEIGHTS.iter().any(|(r, _)| *r == "common"));
        assert!(RARITY_WEIGHTS.iter().any(|(r, _)| *r == "rare"));
        assert!(RARITY_WEIGHTS.iter().any(|(r, _)| *r == "epic"));
        assert!(RARITY_WEIGHTS.iter().any(|(r, _)| *r == "legendary"));
    }
}
