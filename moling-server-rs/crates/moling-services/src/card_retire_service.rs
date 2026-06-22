//! Card retire service — automatic card retirement checks after Phase 4 writes.
//!
//! Ensures the card pool stays within configured limits and freshness-expired
//! cards are automatically retired. Called from `phase4_service.run_phase4()`.
//!
//! Ported from Python `app/service/card_retire_service.py`.

use moling_core::error::AppResult;
use moling_db::dao::card_dao::CardDao;
use sea_orm::DatabaseConnection;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Constants — mirrors Python CardRetireService
// ---------------------------------------------------------------------------

/// Maximum number of active cards allowed in a project pool.
pub const MAX_ACTIVE_CARDS: usize = 80;

/// Freshness window in chapters.
pub const CARD_FRESHNESS_WINDOW: i32 = 3;

/// Freshness multiplier for lifespan calculation.
pub const CARD_FRESHNESS_MULTIPLIER: f64 = 1.5;

/// Card freshness lifespan in chapters (window × multiplier).
pub const FRESHNESS_LIFESPAN: i32 = 4; // int(3 * 1.5) = 4

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// Result of a card retirement check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetireResult {
    /// Number of cards actually retired in this batch.
    pub retired_count: usize,
    /// Number of cards expired due to freshness.
    pub expired_count: usize,
    /// Remaining active cards after retirement.
    pub remaining_active: usize,
    /// IDs of retired cards.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub retired_ids: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetireAuditEntry {
    pub card_id: String,
    pub card_name: String,
    pub retired_at: String,
    pub reason: String,
    pub current_chapter: i32,
    pub freshness_chapter: Option<i32>,
    pub draw_count: i32,
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Card retirement service.
///
/// Responsible for checking card pool freshness and triggering retirement
/// after Phase 4 writes complete.
#[derive(Clone, Default)]
pub struct CardRetireService {
    card_dao: CardDao,
}

impl CardRetireService {
    pub fn new() -> Self {
        Self { card_dao: CardDao }
    }

    // ==================================================================
    // Main check-and-retire flow
    // ==================================================================

    /// Execute card retirement check and retirement operations.
    ///
    /// Flow:
    /// 1. Get active cards (status='active' AND is_active=true)
    /// 2. Calculate each card's freshness expiry chapter
    /// 3. Cap check: if pool > MAX_ACTIVE_CARDS, retire the oldest excess
    /// 4. Freshness check: retire cards past their freshness lifespan
    /// 5. Execute retirement: status='retired', is_active=false
    /// 6. Return RetireResult
    ///
    /// # Arguments
    /// * `db` - Database connection (same transaction as Phase 4)
    /// * `project_id` - Project ID
    /// * `current_chapter` - Current chapter number for freshness calculation
    pub async fn check_and_retire(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        current_chapter: i32,
    ) -> AppResult<RetireResult> {
        // 1. Get active cards
        let active_cards = match self.card_dao.list_active_by_project(db, project_id).await {
            Ok(cards) => cards,
            Err(e) => {
                tracing::error!("Card retire: failed to fetch active cards: {e}");
                return Ok(RetireResult {
                    retired_count: 0,
                    expired_count: 0,
                    remaining_active: 0,
                    retired_ids: Vec::new(),
                });
            }
        };

        let active_count = active_cards.len();
        if active_count == 0 {
            tracing::info!("No active cards for project {}, skipping retire", project_id);
            return Ok(RetireResult {
                retired_count: 0,
                expired_count: 0,
                remaining_active: 0,
                retired_ids: Vec::new(),
            });
        }

        // 2. Calculate freshness expiry per card
        let mut card_expiry: Vec<(String, i32)> = active_cards.iter()
            .map(|c| {
                let fc = c.freshness_chapter.unwrap_or(0);
                (c.id.clone(), fc + FRESHNESS_LIFESPAN)
            })
            .collect();

        // 3. Sort by expiry (earliest first, priority retire)
        card_expiry.sort_by_key(|(_, expiry)| *expiry);

        // 4. Collect retirement candidates
        let mut retire_ids: Vec<String> = Vec::new();

        // 4a. Cap check
        if active_count > MAX_ACTIVE_CARDS {
            let excess = active_count - MAX_ACTIVE_CARDS;
            for (id, _) in card_expiry.iter().take(excess) {
                if !retire_ids.contains(id) {
                    retire_ids.push(id.clone());
                }
            }
            tracing::info!(
                "Project {}: pool size {} > MAX_ACTIVE_CARDS({}), retiring {} excess cards",
                project_id, active_count, MAX_ACTIVE_CARDS, excess
            );
        }

        // 4b. Freshness expiry check
        let mut expired_count = 0;
        for (id, expiry) in &card_expiry {
            if current_chapter >= *expiry && !retire_ids.contains(id) {
                retire_ids.push(id.clone());
                expired_count += 1;
            }
        }

        if expired_count > 0 {
            tracing::info!(
                "Project {}: {} cards expired (current_chapter={})",
                project_id, expired_count, current_chapter
            );
        }

        // 5. No retirements needed
        if retire_ids.is_empty() {
            return Ok(RetireResult {
                retired_count: 0,
                expired_count: 0,
                remaining_active: active_count,
                retired_ids: Vec::new(),
            });
        }

        // 6. Execute retirement
        let mut successful_ids: Vec<String> = Vec::new();
        for card_id in &retire_ids {
            match self.card_dao.retire_card(db, card_id, Some(current_chapter)).await {
                Ok(()) => {
                    successful_ids.push(card_id.clone());
                }
                Err(e) => {
                    tracing::warn!("Failed to retire card {}: {}", card_id, e);
                }
            }
        }

        let retired_count = successful_ids.len();
        let remaining_active = active_count.saturating_sub(retired_count);

        tracing::info!(
            "Project {}: retired {} cards ({} expired, {} by cap), {} remaining active",
            project_id, retired_count, expired_count,
            retired_count.saturating_sub(expired_count), remaining_active
        );

        Ok(RetireResult {
            retired_count,
            expired_count,
            remaining_active,
            retired_ids: successful_ids,
        })
    }

    // ==================================================================
    // Audit and reporting
    // ==================================================================

    /// Generate a retirement audit log for a project.
    ///
    /// Returns audit entries with reason, timestamps, and card metadata
    /// for all cards that would be retired at the given chapter.
    pub async fn audit_retirement_candidates(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        current_chapter: i32,
    ) -> AppResult<Vec<RetireAuditEntry>> {
        let active_cards = match self.card_dao.list_active_by_project(db, project_id).await {
            Ok(cards) => cards,
            Err(_) => return Ok(Vec::new()),
        };

        let now = chrono::Utc::now().to_rfc3339();
        let mut entries: Vec<RetireAuditEntry> = Vec::new();

        // Cap-based candidates
        if active_cards.len() > MAX_ACTIVE_CARDS {
            let excess = active_cards.len() - MAX_ACTIVE_CARDS;
            let mut sorted: Vec<_> = active_cards.iter().collect();
            sorted.sort_by_key(|c| c.freshness_chapter.unwrap_or(0));

            for card in sorted.iter().take(excess) {
                entries.push(RetireAuditEntry {
                    card_id: card.id.clone(),
                    card_name: card.name.clone(),
                    retired_at: now.clone(),
                    reason: "pool_cap_exceeded".to_owned(),
                    current_chapter,
                    freshness_chapter: card.freshness_chapter,
                    draw_count: card.draw_count,
                });
            }
        }

        // Freshness-based candidates
        for card in &active_cards {
            let fc = card.freshness_chapter.unwrap_or(0);
            let expiry = fc + FRESHNESS_LIFESPAN;
            if current_chapter >= expiry {
                // Don't double-count
                if !entries.iter().any(|e| e.card_id == card.id) {
                    entries.push(RetireAuditEntry {
                        card_id: card.id.clone(),
                        card_name: card.name.clone(),
                        retired_at: now.clone(),
                        reason: "freshness_expired".to_owned(),
                        current_chapter,
                        freshness_chapter: card.freshness_chapter,
                        draw_count: card.draw_count,
                    });
                }
            }
        }

        Ok(entries)
    }

    /// Calculate how many more chapters until each active card expires.
    ///
    /// Returns a list of (card_id, card_name, chapters_until_expiry).
    pub async fn expiry_timeline(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        current_chapter: i32,
    ) -> AppResult<Vec<serde_json::Value>> {
        let active_cards = match self.card_dao.list_active_by_project(db, project_id).await {
            Ok(cards) => cards,
            Err(_) => return Ok(Vec::new()),
        };

        let timeline: Vec<serde_json::Value> = active_cards.iter()
            .map(|c| {
                let fc = c.freshness_chapter.unwrap_or(0);
                let expiry = fc + FRESHNESS_LIFESPAN;
                let remaining = std::cmp::max(0, expiry - current_chapter);
                serde_json::json!({
                    "card_id": c.id,
                    "card_name": c.name,
                    "freshness_chapter": c.freshness_chapter,
                    "expiry_chapter": expiry,
                    "chapters_until_expiry": remaining,
                    "expired": remaining == 0,
                    "draw_count": c.draw_count,
                })
            })
            .collect();

        Ok(timeline)
    }

    /// Check if a project's pool has reached critical capacity (>90%).
    pub async fn is_pool_critical(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<bool> {
        let count = self.card_dao.count_pool(db, project_id).await?;
        Ok(count as usize > (MAX_ACTIVE_CARDS as f64 * 0.9) as usize)
    }

    /// Get retirement-ready summary for a project.
    pub async fn retirement_summary(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        current_chapter: i32,
    ) -> AppResult<serde_json::Value> {
        let active_cards = match self.card_dao.list_active_by_project(db, project_id).await {
            Ok(cards) => cards,
            Err(_) => {
                return Ok(serde_json::json!({
                    "error": "Failed to fetch cards",
                    "project_id": project_id,
                }))
            }
        };

        let total = active_cards.len();
        let over_cap = total.saturating_sub(MAX_ACTIVE_CARDS);

        let mut expired_count = 0;
        let mut next_expiry_in = i32::MAX;
        for card in &active_cards {
            let fc = card.freshness_chapter.unwrap_or(0);
            let expiry = fc + FRESHNESS_LIFESPAN;
            if current_chapter >= expiry {
                expired_count += 1;
            } else {
                next_expiry_in = next_expiry_in.min(expiry - current_chapter);
            }
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "current_chapter": current_chapter,
            "max_active_cards": MAX_ACTIVE_CARDS,
            "freshness_lifespan": FRESHNESS_LIFESPAN,
            "total_active": total,
            "over_cap": over_cap,
            "expired": expired_count,
            "total_candidates": over_cap + expired_count,
            "next_expiry_in_chapters": if next_expiry_in == i32::MAX { serde_json::Value::Null } else { serde_json::Value::Number(next_expiry_in.into()) },
            "pool_utilization_pct": if MAX_ACTIVE_CARDS > 0 { (total as f64 / MAX_ACTIVE_CARDS as f64 * 100.0).round() } else { 0.0 },
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retire_result_defaults() {
        let r = RetireResult {
            retired_count: 0,
            expired_count: 0,
            remaining_active: 5,
            retired_ids: Vec::new(),
        };
        assert_eq!(r.retired_count, 0);
        assert_eq!(r.expired_count, 0);
        assert_eq!(r.remaining_active, 5);
    }

    #[test]
    fn test_freshness_lifespan_calculation() {
        assert_eq!(FRESHNESS_LIFESPAN, 4);
        assert!((CARD_FRESHNESS_WINDOW as f64 * CARD_FRESHNESS_MULTIPLIER) as i32 == 4);
    }

    #[test]
    fn test_card_retire_service_constructs() {
        let _ = CardRetireService::new();
        let _ = CardRetireService::default();
    }

    #[test]
    fn test_is_pool_critical_calculation() {
        // 90% of 80 = 72, so 73+ should be critical
        assert!((MAX_ACTIVE_CARDS as f64 * 0.9) as usize == 72);
    }

    #[test]
    fn test_retire_audit_entry_serialization() {
        let entry = RetireAuditEntry {
            card_id: "abc".to_owned(),
            card_name: "Test".to_owned(),
            retired_at: "2024-01-01T00:00:00Z".to_owned(),
            reason: "freshness_expired".to_owned(),
            current_chapter: 10,
            freshness_chapter: Some(5),
            draw_count: 3,
        };
        let json = serde_json::to_value(&entry).unwrap();
        assert_eq!(json["card_id"], "abc");
        assert_eq!(json["reason"], "freshness_expired");
        assert_eq!(json["current_chapter"], 10);
    }
}
