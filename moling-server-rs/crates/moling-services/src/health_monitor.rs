//! 墨灵 (Moling) — Health Monitor Service (健康监控调度).
//!
//! Pure algorithm / SQL implementation, zero LLM cost. Detects sub-plot
//! promise health and generates R1/R2/R3 alerts with anti-fatigue filtering.
//!
//! Ported from Python `app/service/health_monitor.py`.

use moling_core::error::AppResult;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::entities::vault_plot_promise::Model as VaultPlotPromise;

use sea_orm::DatabaseConnection;
use serde::Serialize;
use std::collections::{HashMap, HashSet};
use tracing::{debug, info};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const R1_CHAPTER_WINDOW: i32 = 8;
const R2_MIN_REPEATED: usize = 4;
const R3_CHAPTER_WINDOW: i32 = 10;
const ANTI_FATIGUE_WINDOW: i32 = 3;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// A single health alert.
#[derive(Debug, Clone, Serialize)]
pub struct HealthAlert {
    pub rule: String,
    pub promise_title: String,
    pub promise_id: String,
    pub level: String,
    pub detail: String,
}

/// Health check result.
#[derive(Debug, Clone, Serialize)]
pub struct HealthCheckResult {
    pub checked_at: String,
    pub alerts: Vec<HealthAlert>,
}

// ---------------------------------------------------------------------------
// HealthMonitorService
// ---------------------------------------------------------------------------

/// Sub-plot health monitor service.
///
/// Runs three health rules against all active/advancing VaultPlotPromises.
/// Results can be persisted to DynamicLayer.health_check by the caller.
#[derive(Clone)]
pub struct HealthMonitorService {
    vault_dao: VaultDao,
    chapter_dao: ChapterDao,
}

impl HealthMonitorService {
    /// Create a new HealthMonitorService.
    pub fn new(vault_dao: VaultDao, chapter_dao: ChapterDao) -> Self {
        Self {
            vault_dao,
            chapter_dao,
        }
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Main entry point: run health check and return results.
    ///
    /// # Arguments
    /// * `db` - Database connection
    /// * `project_id` - Project ID
    /// * `current_chapter` - Current chapter number
    /// * `previous_health_checks` - Optional map of chapter_number → alerts for anti-fatigue
    pub async fn check_health(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        current_chapter: i32,
        previous_health_checks: Option<&HashMap<i32, Vec<HealthAlert>>>,
    ) -> AppResult<HealthCheckResult> {
        info!(
            "check_health called: project={project_id}, current_chapter={current_chapter}"
        );

        // 1. Get all plot promises for the project
        let promises = self.vault_dao.find_plot_promises(db, project_id).await?;
        if promises.is_empty() {
            info!("No plot promises found for project {project_id}");
            return Ok(HealthCheckResult {
                checked_at: format!("第{current_chapter}章"),
                alerts: Vec::new(),
            });
        }

        // 2. Get current chapter content (for R3 degradation check)
        let current_chapter_content = self
            .chapter_dao
            .find_by_number(db, project_id, current_chapter)
            .await
            .ok()
            .flatten()
            .and_then(|ch| ch.content);

        // 3. Run R1/R2/R3 on each promise
        let mut alerts: Vec<HealthAlert> = Vec::new();
        for promise in &promises {
            let promise_alerts = self.check_promise(
                promise,
                current_chapter,
                current_chapter_content.as_deref(),
            );
            alerts.extend(promise_alerts);
        }

        // 4. Anti-fatigue filtering
        alerts = self.anti_fatigue_filter(alerts, previous_health_checks, current_chapter);

        let result = HealthCheckResult {
            checked_at: format!("第{current_chapter}章"),
            alerts,
        };

        info!("Health check complete: {} alerts", result.alerts.len());
        Ok(result)
    }

    // ------------------------------------------------------------------
    // R1 / R2 / R3 Detection
    // ------------------------------------------------------------------

    /// Check a single promise against R1, R2, and R3 rules.
    fn check_promise(
        &self,
        promise: &VaultPlotPromise,
        current_chapter: i32,
        current_chapter_content: Option<&str>,
    ) -> Vec<HealthAlert> {
        let mut alerts: Vec<HealthAlert> = Vec::new();
        let promise_title = promise
            .title
            .as_deref()
            .unwrap_or(&promise.description[..promise.description.len().min(50)])
            .to_string();

        // R1: 8-chapter no-progress alert
        if let Some(r1) = self.check_r1(promise, current_chapter, &promise_title) {
            alerts.push(r1);
        }

        // R2: 4+ same-type repeated advancement
        if let Some(r2) = self.check_r2(promise, &promise_title) {
            alerts.push(r2);
        }

        // R3: 10-chapter silence + degradation check
        if let Some(r3) = self.check_r3(promise, current_chapter, current_chapter_content, &promise_title)
        {
            alerts.push(r3);
        }

        alerts
    }

    /// R1: 8 chapters without advancement (🟡 yellow).
    fn check_r1(
        &self,
        promise: &VaultPlotPromise,
        current_chapter: i32,
        promise_title: &str,
    ) -> Option<HealthAlert> {
        if promise.status != "active" && promise.status != "advancing" {
            return None;
        }

        let last_chapter = self.get_last_advance_chapter(promise);

        if current_chapter - last_chapter >= R1_CHAPTER_WINDOW {
            Some(HealthAlert {
                rule: "R1".to_string(),
                promise_title: promise_title.to_string(),
                promise_id: promise.id.clone(),
                level: "yellow".to_string(),
                detail: format!(
                    "已连续{R1_CHAPTER_WINDOW}章未推进（上次推进: 第{last_chapter}章）"
                ),
            })
        } else {
            None
        }
    }

    /// R2: 4+ same-type repeated advancement (🟠 orange).
    fn check_r2(
        &self,
        promise: &VaultPlotPromise,
        promise_title: &str,
    ) -> Option<HealthAlert> {
        let log = match &promise.advancement_log {
            Some(log) => log,
            None => return None,
        };

        let log_array = match log.as_array() {
            Some(arr) => arr,
            None => return None,
        };

        if log_array.len() < R2_MIN_REPEATED {
            return None;
        }

        let mut event_types: HashSet<&str> = HashSet::new();
        for entry in log_array {
            if let Some(event) = entry.get("event").and_then(|v| v.as_str()) {
                event_types.insert(event);
            }
        }

        if event_types.len() == 1 {
            let repeated_type = event_types.iter().next().copied().unwrap_or("unknown");
            Some(HealthAlert {
                rule: "R2".to_string(),
                promise_title: promise_title.to_string(),
                promise_id: promise.id.clone(),
                level: "orange".to_string(),
                detail: format!(
                    "连续{}次同类推进（{repeated_type}），子情节原地踏步",
                    log_array.len()
                ),
            })
        } else {
            None
        }
    }

    /// R3: 10 chapters silence (🔴 red) + degradation check.
    fn check_r3(
        &self,
        promise: &VaultPlotPromise,
        current_chapter: i32,
        current_chapter_content: Option<&str>,
        promise_title: &str,
    ) -> Option<HealthAlert> {
        let last_chapter = self.get_last_advance_chapter(promise);

        if current_chapter - last_chapter < R3_CHAPTER_WINDOW {
            return None;
        }

        let mentioned = self.is_mentioned_in_chapter(promise, current_chapter_content);

        if mentioned {
            // Degrade to R1
            debug!(
                "R3 degraded to R1: promise={}, current={current_chapter}, last={last_chapter}",
                promise.id
            );
            Some(HealthAlert {
                rule: "R1".to_string(),
                promise_title: promise_title.to_string(),
                promise_id: promise.id.clone(),
                level: "yellow".to_string(),
                detail: format!(
                    "已连续{R3_CHAPTER_WINDOW}章未推进（上次推进: 第{last_chapter}章），但最新章节有关键词提及（降级自 R3）"
                ),
            })
        } else {
            Some(HealthAlert {
                rule: "R3".to_string(),
                promise_title: promise_title.to_string(),
                promise_id: promise.id.clone(),
                level: "red".to_string(),
                detail: format!(
                    "已连续{R3_CHAPTER_WINDOW}章静默，无推进也无关键词提及"
                ),
            })
        }
    }

    // ------------------------------------------------------------------
    // Anti-Fatigue Filter
    // ------------------------------------------------------------------

    /// Anti-fatigue filter: same (promise_id, rule) alert max once per 3 chapters.
    fn anti_fatigue_filter(
        &self,
        alerts: Vec<HealthAlert>,
        previous_alerts_by_chapter: Option<&HashMap<i32, Vec<HealthAlert>>>,
        current_chapter: i32,
    ) -> Vec<HealthAlert> {
        if alerts.is_empty() {
            return alerts;
        }

        // Build set of previously reported (promise_id, rule) pairs
        let mut previously_reported: HashSet<(String, String)> = HashSet::new();

        if let Some(previous) = previous_alerts_by_chapter {
            for ch in (current_chapter - ANTI_FATIGUE_WINDOW..current_chapter).rev() {
                if let Some(chapter_alerts) = previous.get(&ch) {
                    for alert in chapter_alerts {
                        let pid = alert.promise_id.clone();
                        let rule = alert.rule.clone();
                        if !pid.is_empty() && !rule.is_empty() {
                            previously_reported.insert((pid, rule));
                        }
                    }
                }
            }
        }

        if previously_reported.is_empty() {
            return alerts;
        }

        let mut filtered = Vec::new();
        let mut suppressed_count = 0;

        for alert in alerts {
            let key = (alert.promise_id.clone(), alert.rule.clone());
            if previously_reported.contains(&key) {
                suppressed_count += 1;
                debug!(
                    "Anti-fatigue suppressed: promise_id={}, rule={}",
                    key.0, key.1
                );
            } else {
                filtered.push(alert);
            }
        }

        if suppressed_count > 0 {
            info!("Anti-fatigue suppressed {suppressed_count} alerts");
        }

        filtered
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /// Get the last chapter number where the promise was advanced.
    fn get_last_advance_chapter(&self, promise: &VaultPlotPromise) -> i32 {
        if let Some(ref log) = promise.advancement_log {
            if let Some(arr) = log.as_array() {
                let max_ch = arr
                    .iter()
                    .filter_map(|entry| entry.get("chapter").and_then(|c| c.as_i64()))
                    .max()
                    .unwrap_or(0);
                return max_ch as i32;
            }
        }
        promise.planted_chapter.unwrap_or(0)
    }

    /// Check if the promise's keywords are mentioned in the current chapter.
    fn is_mentioned_in_chapter(
        &self,
        promise: &VaultPlotPromise,
        chapter_content: Option<&str>,
    ) -> bool {
        let content = match chapter_content {
            Some(c) => c,
            None => return false,
        };

        let content_lower = content.to_lowercase();

        // Build keyword list
        let mut keywords: Vec<String> = Vec::new();
        if let Some(ref title) = promise.title {
            keywords.push(title.to_lowercase());
        }
        let desc = &promise.description;
        let desc_keyword: String = desc.chars().take(50).collect();
        if !desc_keyword.is_empty() {
            keywords.push(desc_keyword.to_lowercase());
        }
        if let Some(ref related) = promise.related_characters {
            if let Some(arr) = related.as_array() {
                for item in arr {
                    if let Some(name) = item.as_str() {
                        keywords.push(name.to_lowercase());
                    }
                }
            }
        }

        for kw in &keywords {
            if !kw.is_empty() && content_lower.contains(kw) {
                debug!("Keyword matched: '{kw}' in chapter content",);
                return true;
            }
        }

        false
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_service() -> HealthMonitorService {
        HealthMonitorService::new(VaultDao::default(), ChapterDao::default())
    }

    #[test]
    fn test_anti_fatigue_empty_alerts() {
        let svc = make_service();
        let result = svc.anti_fatigue_filter(vec![], None, 10);
        assert!(result.is_empty());
    }

    #[test]
    fn test_anti_fatigue_no_previous() {
        let svc = make_service();
        let alerts = vec![HealthAlert {
            rule: "R1".into(),
            promise_title: "测试".into(),
            promise_id: "1".into(),
            level: "yellow".into(),
            detail: "test".into(),
        }];
        let result = svc.anti_fatigue_filter(alerts.clone(), None, 10);
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn test_anti_fatigue_suppresses_duplicate() {
        let svc = make_service();
        let alerts = vec![HealthAlert {
            rule: "R1".into(),
            promise_title: "测试".into(),
            promise_id: "1".into(),
            level: "yellow".into(),
            detail: "test".into(),
        }];

        let mut previous: HashMap<i32, Vec<HealthAlert>> = HashMap::new();
        previous.insert(
            8,
            vec![HealthAlert {
                rule: "R1".into(),
                promise_title: "测试".into(),
                promise_id: "1".into(),
                level: "yellow".into(),
                detail: "old".into(),
            }],
        );

        let result = svc.anti_fatigue_filter(alerts, Some(&previous), 10);
        assert_eq!(result.len(), 0);
    }

    #[test]
    fn test_anti_fatigue_allows_different_rule() {
        let svc = make_service();
        let alerts = vec![HealthAlert {
            rule: "R2".into(),
            promise_title: "测试".into(),
            promise_id: "1".into(),
            level: "orange".into(),
            detail: "different".into(),
        }];

        let mut previous: HashMap<i32, Vec<HealthAlert>> = HashMap::new();
        previous.insert(
            8,
            vec![HealthAlert {
                rule: "R1".into(),
                promise_title: "测试".into(),
                promise_id: "1".into(),
                level: "yellow".into(),
                detail: "old".into(),
            }],
        );

        let result = svc.anti_fatigue_filter(alerts, Some(&previous), 10);
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn test_get_last_advance_chapter_planted() {
        let svc = make_service();
        let promise = VaultPlotPromise {
            id: "1".into(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            is_deleted: false,
            deleted_at: None,
            confidence: None,
            project_id: 1,
            description: "test".into(),
            r#type: "mystery".into(),
            title: Some("test".into()),
            status: "active".into(),
            urgency: 5,
            advancement_log: None,
            related_characters: None,
            planted_chapter: Some(5),
            redeem_window: None,
        };
        assert_eq!(svc.get_last_advance_chapter(&promise), 5);
    }

    #[test]
    fn test_is_mentioned_in_chapter() {
        let svc = make_service();
        let promise = VaultPlotPromise {
            id: "1".into(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            is_deleted: false,
            deleted_at: None,
            confidence: None,
            project_id: 1,
            description: "神秘玉佩的秘密".into(),
            r#type: "mystery".into(),
            title: Some("玉佩之谜".into()),
            status: "active".into(),
            urgency: 5,
            advancement_log: None,
            related_characters: Some(serde_json::json!(["张三"])),
            planted_chapter: Some(1),
            redeem_window: None,
        };

        assert!(svc.is_mentioned_in_chapter(
            &promise,
            Some("张三发现了一块神秘玉佩。"),
        ));
        assert!(!svc.is_mentioned_in_chapter(
            &promise,
            Some("李四在街上散步。"),
        ));
    }
}
