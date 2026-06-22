//! 墨灵 (Moling) — Validation Service (Pre/Post Generation Checks).
//!
//! Implements pre-generation and post-generation structural validations
//! to ensure content quality and consistency before and after AI generation.
//! All checks are deterministic — they query the database and perform
//! structural comparisons without LLM calls.
//!
//! Ported from Python `app/service/validation_service.py`.

use moling_db::dao::vault_dao::VaultDao;
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_db::dao::secret_dao::SecretDao;

use sea_orm::DatabaseConnection;
use serde::Serialize;

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// Result of a single validation check.
#[derive(Debug, Clone, Serialize)]
pub struct CheckResult {
    pub passed: bool,
    pub name: String,
    pub detail: String,
    pub suggestions: Vec<String>,
    pub severity: String,
}

/// Aggregated result of multiple validation checks.
#[derive(Debug, Clone, Serialize)]
pub struct ValidationResult {
    pub passed: bool,
    pub checks: Vec<CheckResult>,
    pub summary: String,
}

/// Minimal card representation for validation.
#[derive(Debug, Clone)]
pub struct ValidationCard {
    pub name: String,
    pub characters: Vec<ValidationCharRef>,
    pub plot_promises: Vec<ValidationPromiseRef>,
    pub world_rules: Vec<ValidationWorldRef>,
    pub timeline_point: Option<i32>,
}

#[derive(Debug, Clone)]
pub struct ValidationCharRef {
    pub name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ValidationPromiseRef {
    pub id: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ValidationWorldRef {
    pub id: Option<String>,
}

// ---------------------------------------------------------------------------
// ValidationService
// ---------------------------------------------------------------------------

/// Service for pre-generation and post-generation content validation.
#[derive(Clone)]
pub struct ValidationService {
    vault_dao: VaultDao,
    #[allow(dead_code)]
    card_dao: CardDao,
    dynamic_layer_dao: DynamicLayerDao,
    secret_dao: SecretDao,
}

impl ValidationService {
    /// Create a new ValidationService.
    pub fn new(
        vault_dao: VaultDao,
        card_dao: CardDao,
        dynamic_layer_dao: DynamicLayerDao,
        secret_dao: SecretDao,
    ) -> Self {
        Self {
            vault_dao,
            card_dao,
            dynamic_layer_dao,
            secret_dao,
        }
    }

    // ------------------------------------------------------------------
    // Pre-Generation Checks
    // ------------------------------------------------------------------

    /// Verify characters referenced in cards exist in the project vault.
    pub async fn pre_check_character_consistency(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[ValidationCard],
    ) -> CheckResult {
        let vault_chars = match self.vault_dao.find_characters(db, project_id).await {
            Ok(c) => c,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "角色一致性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let vault_names: std::collections::HashSet<&str> =
            vault_chars.iter().map(|c| c.name.as_str()).collect();

        let mut missing: Vec<String> = Vec::new();
        for card in cards {
            for char_ref in &card.characters {
                if let Some(ref name) = char_ref.name {
                    if !vault_names.contains(name.as_str()) {
                        missing.push(format!(
                            "卡片「{}」引用了 vault 中不存在的角色「{name}」",
                            card.name
                        ));
                    }
                }
            }
        }

        if !missing.is_empty() {
            let count = missing.len();
            let first_five: Vec<String> = missing.iter().take(5).cloned().collect();
            CheckResult {
                passed: false,
                name: "角色一致性检查".to_string(),
                detail: format!("发现 {count} 个角色引用问题: {}", first_five.join("; ")),
                suggestions: missing,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "角色一致性检查".to_string(),
                detail: format!(
                    "所有卡片引用的角色均存在于 vault 中 (共 {} 个角色)",
                    vault_chars.len()
                ),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Ensure selected cards do not violate timeline ordering constraints.
    pub async fn pre_check_timeline_continuity(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[ValidationCard],
    ) -> CheckResult {
        let vault_timeline = match self.vault_dao.find_timeline_events(db, project_id).await {
            Ok(t) => t,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "时间线连续性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let chapter_numbers: Vec<i32> =
            vault_timeline.iter().map(|e| e.chapter_number).collect();
        let max_chapter = chapter_numbers.iter().max().copied().unwrap_or(0);

        let mut issues: Vec<String> = Vec::new();
        for card in cards {
            if let Some(tp) = card.timeline_point {
                if !chapter_numbers.is_empty() && tp > max_chapter {
                    issues.push(format!(
                        "卡片「{}」的时间线点 {tp} 超出当前最大章节 {max_chapter}",
                        card.name
                    ));
                } else if tp < 1 {
                    issues.push(format!("卡片「{}」的时间线点 {tp} 无效", card.name));
                }
            }
        }

        if !issues.is_empty() {
            CheckResult {
                passed: false,
                name: "时间线连续性检查".to_string(),
                detail: format!(
                    "发现 {} 个时间线问题: {}",
                    issues.len(),
                    issues.iter().take(5).cloned().collect::<Vec<_>>().join("; ")
                ),
                suggestions: issues,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "时间线连续性检查".to_string(),
                detail: format!("卡片时间线约束通过 (vault 共 {} 个事件)", vault_timeline.len()),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Verify selected cards maintain plot promise coherence.
    pub async fn pre_check_plot_promise_logic(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[ValidationCard],
    ) -> CheckResult {
        let vault_promises = match self.vault_dao.find_plot_promises(db, project_id).await {
            Ok(p) => p,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "剧情承诺逻辑检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let promise_map: std::collections::HashMap<String, &moling_db::entities::vault_plot_promise::Model> =
            vault_promises.iter().map(|p| (p.id.clone(), p)).collect();

        let mut warnings: Vec<String> = Vec::new();
        for card in cards {
            for promise_ref in &card.plot_promises {
                let pid = match &promise_ref.id {
                    Some(id) => id.clone(),
                    None => continue,
                };

                match promise_map.get(&pid) {
                    None => {
                        warnings.push(format!(
                            "卡片「{}」引用了不存在的伏笔 ID={pid}",
                            card.name
                        ));
                    }
                    Some(promise) => {
                        if promise.status == "resolved" || promise.status == "abandoned" {
                            let status_label = if promise.status == "resolved" {
                                "回收"
                            } else {
                                "废弃"
                            };
                            let desc_preview = if promise.description.len() > 30 {
                                &promise.description[..30]
                            } else {
                                &promise.description
                            };
                            warnings.push(format!(
                                "卡片「{}」引用的伏笔「{desc_preview}」已{status_label}",
                                card.name
                            ));
                        }
                    }
                }
            }
        }

        if !warnings.is_empty() {
            CheckResult {
                passed: false,
                name: "剧情承诺逻辑检查".to_string(),
                detail: format!("发现 {} 个伏笔引用问题", warnings.len()),
                suggestions: warnings,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "剧情承诺逻辑检查".to_string(),
                detail: format!(
                    "所有卡片引用的伏笔均有效 (vault 共 {} 个伏笔)",
                    vault_promises.len()
                ),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Check card content does not violate established world rules.
    pub async fn pre_check_world_rule_compliance(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[ValidationCard],
    ) -> CheckResult {
        let world_entries = match self.vault_dao.find_world_entries(db, project_id).await {
            Ok(w) => w,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "世界观规则合规检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let world_map: std::collections::HashMap<String, &moling_db::entities::vault_world::Model> =
            world_entries.iter().map(|e| (e.id.clone(), e)).collect();

        let mut issues: Vec<String> = Vec::new();
        for card in cards {
            for world_ref in &card.world_rules {
                let wid = match &world_ref.id {
                    Some(id) => id.clone(),
                    None => continue,
                };
                if !world_map.contains_key(&wid) {
                    issues.push(format!(
                        "卡片「{}」引用了不存在的世界观条目 ID={wid}",
                        card.name
                    ));
                }
            }
        }

        if !issues.is_empty() {
            CheckResult {
                passed: false,
                name: "世界观规则合规检查".to_string(),
                detail: format!("发现 {} 个世界观引用问题", issues.len()),
                suggestions: issues,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "世界观规则合规检查".to_string(),
                detail: format!(
                    "所有卡片引用的世界观条目均有效 (vault 共 {} 个条目)",
                    world_entries.len()
                ),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Verify the latest dynamic-layer summary is present and coherent.
    pub async fn pre_check_summary_cohesion(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> CheckResult {
        let latest = match self
            .dynamic_layer_dao
            .find_latest_by_project(db, project_id)
            .await
        {
            Ok(l) => l,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "前情摘要连贯性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let dl = match latest {
            Some(dl) => dl,
            None => {
                return CheckResult {
                    passed: false,
                    name: "前情摘要连贯性检查".to_string(),
                    detail: "项目尚无动态层记录，无法检查前情摘要".to_string(),
                    suggestions: vec!["请先生成一个章节以建立动态层".to_string()],
                    severity: "warning".to_string(),
                };
            }
        };

        let summary = dl.summary.as_deref().unwrap_or("");
        if summary.is_empty() {
            CheckResult {
                passed: false,
                name: "前情摘要连贯性检查".to_string(),
                detail: "最新的动态层记录缺少前情摘要 (summary 为空)".to_string(),
                suggestions: vec!["请运行动态层摘要更新".to_string()],
                severity: "error".to_string(),
            }
        } else if summary.len() < 20 {
            CheckResult {
                passed: false,
                name: "前情摘要连贯性检查".to_string(),
                detail: format!("前情摘要过短 ({} 字符)，可能不完整", summary.len()),
                suggestions: vec!["请检查并补全前情摘要".to_string()],
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "前情摘要连贯性检查".to_string(),
                detail: format!("前情摘要存在且长度合理 ({} 字符)", summary.len()),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Check must_hold / must_not baselines are consistent.
    pub async fn pre_check_baseline_consistency(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> CheckResult {
        let latest = match self
            .dynamic_layer_dao
            .find_latest_by_project(db, project_id)
            .await
        {
            Ok(l) => l,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "基线一致性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let dl = match latest {
            Some(dl) => dl,
            None => {
                return CheckResult {
                    passed: true,
                    name: "基线一致性检查".to_string(),
                    detail: "项目尚无动态层记录，跳过基线检查".to_string(),
                    suggestions: Vec::new(),
                    severity: "info".to_string(),
                };
            }
        };

        let must_hold: Vec<String> = dl.must_hold.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();
        let must_not: Vec<String> = dl.must_not.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();

        let mut issues: Vec<String> = Vec::new();

        // Check for empty items
        for (i, item) in must_hold.iter().enumerate() {
            if item.trim().is_empty() {
                issues.push(format!("must_hold 第 {} 项为空", i + 1));
            }
        }
        for (i, item) in must_not.iter().enumerate() {
            if item.trim().is_empty() {
                issues.push(format!("must_not 第 {} 项为空", i + 1));
            }
        }

        // Check for overlap
        let hold_set: std::collections::HashSet<&str> =
            must_hold.iter().map(|s| s.as_str()).collect();
        let not_set: std::collections::HashSet<&str> =
            must_not.iter().map(|s| s.as_str()).collect();
        let overlap: Vec<&&str> = hold_set.intersection(&not_set).collect();
        if !overlap.is_empty() {
            issues.push(format!(
                "以下约束同时出现在 must_hold 和 must_not 中: {:?}",
                overlap
            ));
        }

        if !issues.is_empty() {
            CheckResult {
                passed: false,
                name: "基线一致性检查".to_string(),
                detail: format!("发现 {} 个基线问题: {}", issues.len(), issues.join("; ")),
                suggestions: issues,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "基线一致性检查".to_string(),
                detail: format!(
                    "基线一致 (must_hold={} 条, must_not={} 条)",
                    must_hold.len(),
                    must_not.len()
                ),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    // ------------------------------------------------------------------
    // Post-Generation Checks
    // ------------------------------------------------------------------

    /// Verify generated content does not contradict established vault facts.
    pub async fn post_check_fact_consistency(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        content: &str,
    ) -> CheckResult {
        let content_lower = content.to_lowercase();

        let characters = match self.vault_dao.find_characters(db, project_id).await {
            Ok(c) => c,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "事实一致性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let world_entries = match self.vault_dao.find_world_entries(db, project_id).await {
            Ok(w) => w,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "事实一致性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let mut warnings: Vec<String> = Vec::new();

        let mentioned_count = characters
            .iter()
            .filter(|c| content_lower.contains(&c.name.to_lowercase()))
            .count();

        if !characters.is_empty() && mentioned_count == 0 {
            warnings.push("生成内容中未提及任何 vault 角色".to_string());
        }

        let world_mentioned = world_entries
            .iter()
            .filter(|e| content_lower.contains(&e.name.to_lowercase()))
            .count();

        if !world_entries.is_empty() && world_mentioned == 0 {
            warnings.push("生成内容中未提及任何世界观条目".to_string());
        }

        if !warnings.is_empty() {
            CheckResult {
                passed: false,
                name: "事实一致性检查".to_string(),
                detail: warnings.join("; "),
                suggestions: warnings,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "事实一致性检查".to_string(),
                detail: format!(
                    "内容与 vault 事实一致 (角色提及 {mentioned_count}, 世界观提及 {world_mentioned})"
                ),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Verify generated content follows must_hold / must_not baselines.
    pub async fn post_check_baseline_compliance(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        content: &str,
    ) -> CheckResult {
        let latest = match self
            .dynamic_layer_dao
            .find_latest_by_project(db, project_id)
            .await
        {
            Ok(l) => l,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "基线合规检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        let dl = match latest {
            Some(dl) => dl,
            None => {
                return CheckResult {
                    passed: true,
                    name: "基线合规检查".to_string(),
                    detail: "无动态层记录，跳过基线合规检查".to_string(),
                    suggestions: Vec::new(),
                    severity: "info".to_string(),
                };
            }
        };

        let must_hold: Vec<String> = dl.must_hold.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();
        let must_not: Vec<String> = dl.must_not.as_ref()
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();
        let content_lower = content.to_lowercase();

        let mut issues: Vec<String> = Vec::new();

        for item in &must_hold {
            let item_lower = item.to_lowercase();
            if !item_lower.is_empty() && !content_lower.contains(&item_lower) {
                issues.push(format!("必须保持的约束「{item}」未在内容中体现"));
            }
        }

        for item in &must_not {
            let item_lower = item.to_lowercase();
            if !item_lower.is_empty() && content_lower.contains(&item_lower) {
                issues.push(format!("必须避免的约束「{item}」在内容中出现"));
            }
        }

        if !issues.is_empty() {
            CheckResult {
                passed: false,
                name: "基线合规检查".to_string(),
                detail: format!("发现 {} 个基线违规", issues.len()),
                suggestions: issues,
                severity: "error".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "基线合规检查".to_string(),
                detail: "内容符合所有 must_hold / must_not 基线约束".to_string(),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    /// Verify secrets mentioned in content are consistent with the vault.
    pub async fn post_check_secret_consistency(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        content: &str,
    ) -> CheckResult {
        let secrets = match self.secret_dao.list_by_project(db, project_id).await {
            Ok(s) => s,
            Err(e) => {
                return CheckResult {
                    passed: false,
                    name: "秘密一致性检查".to_string(),
                    detail: format!("检查异常: {e}"),
                    suggestions: Vec::new(),
                    severity: "error".to_string(),
                };
            }
        };

        if secrets.is_empty() {
            return CheckResult {
                passed: true,
                name: "秘密一致性检查".to_string(),
                detail: "项目尚无秘密，跳过检查".to_string(),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            };
        }

        let content_lower = content.to_lowercase();
        let mut warnings: Vec<String> = Vec::new();

        for secret in &secrets {
            let desc_preview = if secret.description.len() > 50 {
                &secret.description[..50]
            } else {
                &secret.description
            };

            if desc_preview.to_lowercase().contains(&content_lower) && secret.secrecy_level == "hidden" {
                let short_desc = if secret.description.len() > 30 {
                    &secret.description[..30]
                } else {
                    &secret.description
                };
                warnings.push(format!(
                    "秘密「{short_desc}」的保密层级为「隐藏」，但在内容中出现"
                ));
            }
        }

        if !warnings.is_empty() {
            CheckResult {
                passed: false,
                name: "秘密一致性检查".to_string(),
                detail: format!("发现 {} 个秘密一致性问题", warnings.len()),
                suggestions: warnings,
                severity: "warning".to_string(),
            }
        } else {
            CheckResult {
                passed: true,
                name: "秘密一致性检查".to_string(),
                detail: format!("内容与 vault 中 {} 个秘密一致", secrets.len()),
                suggestions: Vec::new(),
                severity: "info".to_string(),
            }
        }
    }

    // ------------------------------------------------------------------
    // Aggregated check runners
    // ------------------------------------------------------------------

    /// Run all 6 pre-generation checks and aggregate results.
    pub async fn run_pre_checks(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        cards: &[ValidationCard],
    ) -> ValidationResult {
        let mut checks: Vec<CheckResult> = Vec::new();

        checks.push(self.pre_check_character_consistency(db, project_id, cards).await);
        checks.push(self.pre_check_timeline_continuity(db, project_id, cards).await);
        checks.push(self.pre_check_plot_promise_logic(db, project_id, cards).await);
        checks.push(self.pre_check_world_rule_compliance(db, project_id, cards).await);
        checks.push(self.pre_check_summary_cohesion(db, project_id).await);
        checks.push(self.pre_check_baseline_consistency(db, project_id).await);

        self.aggregate_results(checks)
    }

    /// Run all post-generation checks and aggregate results.
    pub async fn run_post_checks(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        content: &str,
    ) -> ValidationResult {
        let mut checks: Vec<CheckResult> = Vec::new();

        checks.push(self.post_check_fact_consistency(db, project_id, content).await);
        checks.push(self.post_check_baseline_compliance(db, project_id, content).await);
        checks.push(self.post_check_secret_consistency(db, project_id, content).await);

        self.aggregate_results(checks)
    }

    /// Aggregate individual check results into a ValidationResult.
    fn aggregate_results(&self, checks: Vec<CheckResult>) -> ValidationResult {
        let errors: Vec<&CheckResult> = checks
            .iter()
            .filter(|c| c.severity == "error" && !c.passed)
            .collect();
        let warnings: Vec<&CheckResult> = checks
            .iter()
            .filter(|c| c.severity == "warning" && !c.passed)
            .collect();
        let all_passed = errors.is_empty() && warnings.is_empty();

        let mut summary_parts: Vec<String> = Vec::new();
        if !errors.is_empty() {
            summary_parts.push(format!("{} 个错误", errors.len()));
        }
        if !warnings.is_empty() {
            summary_parts.push(format!("{} 个警告", warnings.len()));
        }

        let passed_count = checks.iter().filter(|c| c.passed).count();
        let summary = format!(
            "{}/{} 检查通过{}",
            passed_count,
            checks.len(),
            if summary_parts.is_empty() {
                String::new()
            } else {
                format!("，未通过: {}", summary_parts.join(", "))
            }
        );

        ValidationResult {
            passed: all_passed,
            checks,
            summary,
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_check_result_passed() {
        let cr = CheckResult {
            passed: true,
            name: "test".into(),
            detail: "detail".into(),
            suggestions: vec![],
            severity: "info".into(),
        };
        assert!(cr.passed);
        assert_eq!(cr.severity, "info");
    }

    #[test]
    fn test_aggregate_all_passed() {
        let svc = ValidationService::new(
            VaultDao::default(),
            CardDao::default(),
            DynamicLayerDao::default(),
            SecretDao::default(),
        );
        let checks = vec![CheckResult {
            passed: true,
            name: "测试1".into(),
            detail: "通过".into(),
            suggestions: vec![],
            severity: "info".into(),
        }];
        let result = svc.aggregate_results(checks);
        assert!(result.passed);
        assert_eq!(result.checks.len(), 1);
    }

    #[test]
    fn test_aggregate_with_warning() {
        let svc = ValidationService::new(
            VaultDao::default(),
            CardDao::default(),
            DynamicLayerDao::default(),
            SecretDao::default(),
        );
        let checks = vec![
            CheckResult {
                passed: true,
                name: "测试1".into(),
                detail: "通过".into(),
                suggestions: vec![],
                severity: "info".into(),
            },
            CheckResult {
                passed: false,
                name: "测试2".into(),
                detail: "警告".into(),
                suggestions: vec!["fix".into()],
                severity: "warning".into(),
            },
        ];
        let result = svc.aggregate_results(checks);
        assert!(!result.passed);
    }
}
