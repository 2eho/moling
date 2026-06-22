//! Health service — system health check and monitoring (R1/R2/R3).
//!
//! Mirrors Python `app/service/health_service.py`.
//!
//! R1: Character consistency check
//! R2: Timeline continuity check
//! R3: Plot promise debt check

use moling_core::error::{AppError, AppResult};
use moling_db::dao::health_alert_dao::HealthAlertDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::health_alert::Model as HealthAlertModel;
use sea_orm::{DatabaseConnection, Set};

/// System health status.
#[derive(Clone)]
pub struct HealthService {
    health_alert_dao: HealthAlertDao,
    vault_dao: VaultDao,
    project_dao: ProjectDao,
}

impl HealthService {
    pub fn new() -> Self {
        Self {
            health_alert_dao: HealthAlertDao,
            vault_dao: VaultDao,
            project_dao: ProjectDao,
        }
    }

    // ---- Infrastructure checks ----

    /// Check database connectivity.
    pub async fn check_db(&self, db: &DatabaseConnection) -> AppResult<bool> {
        db.ping().await.map(|_| true).or(Ok(false))
    }

    /// Check Redis connectivity (delegates to pool health).
    pub fn check_redis(&self, redis_pool: &moling_core::redis::RedisPool) -> bool {
        redis_pool.is_available()
    }

    /// Full health check: database + Redis.
    pub async fn full_check(
        &self,
        db: &DatabaseConnection,
        redis_pool: &moling_core::redis::RedisPool,
    ) -> AppResult<HealthStatus> {
        let db_ok = self.check_db(db).await?;
        Ok(HealthStatus {
            database: db_ok,
            redis: self.check_redis(redis_pool),
            status: if db_ok { "healthy" } else { "degraded" }.to_owned(),
        })
    }

    // ---- R1/R2/R3 Project Health Checks ----

    /// Run all health checks (R1/R2/R3) for a project.
    ///
    /// Mirrors Python `HealthService.run_health_check`.
    pub async fn run_health_check(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<serde_json::Value> {
        // Verify project ownership
        let project = self.project_dao.find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if project.user_id != user_id {
            return Err(AppError::project_access_denied());
        }

        let mut result = serde_json::json!({
            "project_id": project_id,
            "checks": {},
            "alerts": [],
        });

        // R1: Character consistency
        let r1 = self.check_r1(db, project_id).await?;
        result["checks"]["R1"] = serde_json::json!({
            "passed": r1.passed,
            "score": r1.score,
            "details": r1.details,
        });

        // R2: Timeline continuity
        let r2 = self.check_r2(db, project_id).await?;
        result["checks"]["R2"] = serde_json::json!({
            "passed": r2.passed,
            "score": r2.score,
            "details": r2.details,
        });

        // R3: Plot promise debt
        let r3 = self.check_r3(db, project_id).await?;
        result["checks"]["R3"] = serde_json::json!({
            "passed": r3.passed,
            "score": r3.score,
            "details": r3.details,
        });

        // Collect and create alerts for failed checks
        let mut alerts = Vec::new();
        let checks = [(r1, "R1"), (r2, "R2"), (r3, "R3")];
        for (check, rule) in &checks {
            if !check.passed {
                for alert_detail in &check.alert_details {
                    let alert = self.create_alert(
                        db, project_id, rule,
                        &alert_detail.title,
                        &alert_detail.detail,
                        &alert_detail.severity,
                    ).await?;
                    alerts.push(serde_json::json!({
                        "id": alert.id,
                        "rule": alert.rule,
                        "title": alert.title,
                        "severity": alert.severity,
                    }));
                }
            }
        }
        result["alerts"] = serde_json::json!(alerts);

        Ok(result)
    }

    /// R1: Check character behavior consistency.
    async fn check_r1(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<CheckResult> {
        let characters = self.vault_dao.find_characters(db, project_id).await?;

        if characters.is_empty() {
            return Ok(CheckResult {
                passed: true,
                score: 1.0,
                details: "No characters to check".into(),
                alert_details: vec![],
            });
        }

        // Check for consistency issues
        let mut alert_details = Vec::new();
        let mut score: f64 = 1.0;
        // Check: characters with very low chapter count
        let low_appearance: Vec<_> = characters
            .iter()
            .filter(|c| c.chapter_count < 2 && characters.len() > 5)
            .collect();
        if !low_appearance.is_empty() {
            score = (score - 0.15_f64).max(0.0);
            alert_details.push(AlertDetail {
                title: "低出场率角色".into(),
                detail: format!(
                    "{} 个角色出场次数不足，可能被遗忘",
                    low_appearance.len()
                ),
                severity: "warning".into(),
            });
        }

        // Check: duplicate character names
        let names: Vec<&str> = characters.iter().map(|c| c.name.as_str()).collect();
        let mut seen = std::collections::HashSet::new();
        let mut duplicates = Vec::new();
        for name in &names {
            if !seen.insert(*name) {
                duplicates.push(*name);
            }
        }
        if !duplicates.is_empty() {
            score = (score - 0.2_f64).max(0.0);
            alert_details.push(AlertDetail {
                title: "重复角色名".into(),
                detail: format!("检测到重复角色名: {}", duplicates.join(", ")),
                severity: "critical".into(),
            });
        }

        Ok(CheckResult {
            passed: score >= 0.7,
            score: score.max(0.0),
            details: format!("角色一致性得分: {:.2}", score),
            alert_details,
        })
    }

    /// R2: Check timeline continuity.
    async fn check_r2(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<CheckResult> {
        let events = self.vault_dao.find_timeline_events(db, project_id).await?;

        if events.len() < 2 {
            return Ok(CheckResult {
                passed: true,
                score: 1.0,
                details: "Timeline events insufficient for continuity check".into(),
                alert_details: vec![],
            });
        }

        let mut alert_details = Vec::new();
        let mut score: f64 = 1.0;
        // Check: events in chronological order by chapter_number
        let chapter_numbers: Vec<i32> = events.iter().map(|e| e.chapter_number).collect();
        let mut sorted = chapter_numbers.clone();
        sorted.sort();

        if chapter_numbers != sorted {
            score = (score - 0.4_f64).max(0.0);
            alert_details.push(AlertDetail {
                title: "时间线顺序问题".into(),
                detail: "时间线事件的章节顺序不一致，可能存在时间线冲突".into(),
                severity: "warning".into(),
            });
        }

        Ok(CheckResult {
            passed: score >= 0.7,
            score: score.max(0.0),
            details: if score >= 0.95 {
                "时间线连续性检查通过".into()
            } else {
                format!("时间线连续性得分: {:.2}", score)
            },
            alert_details,
        })
    }

    /// R3: Check plot promise debt.
    async fn check_r3(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<CheckResult> {
        let promises = self.vault_dao.find_plot_promises(db, project_id).await?;

        if promises.is_empty() {
            return Ok(CheckResult {
                passed: true,
                score: 1.0,
                details: "No plot promises to check".into(),
                alert_details: vec![],
            });
        }

        let total = promises.len();
        let dormant_count = promises.iter().filter(|p| p.status == "dormant").count();
        let active_count = promises.iter().filter(|p| p.status == "active").count();
        let resolved_count = promises.iter().filter(|p| p.status == "resolved").count();
        let unresolved = dormant_count + active_count;
        let resolved_rate = resolved_count as f64 / total as f64;

        let debt_threshold: usize = 10;

        let mut alert_details = Vec::new();
        let mut score: f64 = 1.0;        let mut passed = true;

        if unresolved > debt_threshold {
            score = 0.5;
            passed = false;
            alert_details.push(AlertDetail {
                title: "伏笔债务警告".into(),
                detail: format!(
                    "当前有 {unresolved} 个未回收的伏笔，建议尽快回收部分伏笔"
                ),
                severity: "critical".into(),
            });
        } else if unresolved as f64 > debt_threshold as f64 * 0.7 {
            score = 0.7;
            alert_details.push(AlertDetail {
                title: "伏笔债务提醒".into(),
                detail: format!(
                    "当前有 {unresolved} 个未回收的伏笔，建议关注伏笔回收"
                ),
                severity: "warning".into(),
            });
        }

        Ok(CheckResult {
            passed,
            score: score.max(0.0),
            details: if passed {
                format!("伏笔债务健康: {unresolved} 个未回收伏笔，回收率 {:.1}%", resolved_rate * 100.0)
            } else {
                format!("伏笔债务过高: {unresolved} 个未回收伏笔")
            },
            alert_details,
        })
    }

    // ---- Alert management ----

    /// Create a health alert.
    pub async fn create_alert(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        rule: &str,
        title: &str,
        detail: &str,
        severity: &str,
    ) -> AppResult<HealthAlertModel> {
        let model = moling_db::entities::health_alert::ActiveModel {
            project_id: Set(project_id),
            rule: Set(rule.to_owned()),
            title: Set(title.to_owned()),
            detail: Set(detail.to_owned()),
            severity: Set(severity.to_owned()),
            is_active: Set(true),
            ..Default::default()
        };
        self.health_alert_dao.create(db, model).await
    }

    /// List health alerts for a project.
    ///
    /// Mirrors Python `HealthService.get_alerts`.
    pub async fn list_alerts(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        active_only: bool,
    ) -> AppResult<Vec<HealthAlertModel>> {
        if active_only {
            self.health_alert_dao.list_active_by_project(db, project_id).await
        } else {
            self.health_alert_dao.list_by_project(db, project_id).await
        }
    }

    /// List alerts filtered by severity level.
    ///
    /// Severity levels: "info", "warning", "critical".
    pub async fn list_alerts_by_severity(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        severity: &str,
    ) -> AppResult<Vec<HealthAlertModel>> {
        self.health_alert_dao.list_by_severity(db, project_id, severity).await
    }

    /// Auto-resolve all active alerts for a given rule in a project.
    ///
    /// Called when a health check passes after previously failing.
    pub async fn resolve_by_rule(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        rule: &str,
    ) -> AppResult<u64> {
        self.health_alert_dao.resolve_by_rule(db, project_id, rule).await
    }

    /// Update the checked_at timestamp for an alert.
    pub async fn touch_alert(
        &self,
        db: &DatabaseConnection,
        alert_id: i32,
    ) -> AppResult<()> {
        self.health_alert_dao.update_checked_at(db, alert_id).await
    }

    /// Get health monitor summary for a project.
    pub async fn monitor(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        user_id: &str,
    ) -> AppResult<serde_json::Value> {
        // Run all checks
        let check_result = self.run_health_check(db, user_id, project_id).await?;

        // Get all active alerts
        let active_alerts = self.list_alerts(db, project_id, true).await?;
        let critical_count = active_alerts.iter().filter(|a| a.severity == "critical").count();
        let warning_count = active_alerts.iter().filter(|a| a.severity == "warning").count();

        Ok(serde_json::json!({
            "project_id": project_id,
            "status": if critical_count > 0 { "critical" } else if warning_count > 0 { "warning" } else { "healthy" },
            "alert_counts": {
                "total": active_alerts.len(),
                "critical": critical_count,
                "warning": warning_count,
            },
            "last_check": check_result,
        }))
    }
}

impl Default for HealthService {
    fn default() -> Self {
        Self::new()
    }
}

/// System health response.
pub struct HealthStatus {
    pub status: String,
    pub database: bool,
    pub redis: bool,
}

/// Internal check result for R1/R2/R3.
struct CheckResult {
    passed: bool,
    score: f64,
    details: String,
    alert_details: Vec<AlertDetail>,
}

/// Detail for an alert within a check result.
struct AlertDetail {
    title: String,
    detail: String,
    severity: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_service_constructs() {
        let _ = HealthService::new();
    }

    #[test]
    fn test_health_status() {
        let status = HealthStatus {
            status: "healthy".into(),
            database: true,
            redis: true,
        };
        assert_eq!(status.status, "healthy");
        assert!(status.database);
    }
}
