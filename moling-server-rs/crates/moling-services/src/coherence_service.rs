//! 墨灵 (Moling) — Coherence Validation Service.
//!
//! Implements post-generation coherence checks using v2 grouped checks
//! (3 merged LLM calls instead of 8 individual checks).
//!
//! Validates: narrative consistency (character + timeline + plot promise),
//! writing quality (world rule + style + pacing + baseline),
//! and continuity (chapter transition + secret debt).
//!
//! Ported from Python `app/service/coherence_service.py`.

use std::sync::Arc;

use moling_core::error::{AppError, AppResult};
use moling_db::dao::{chapter_dao::ChapterDao, secret_dao::SecretDao, vault_dao::VaultDao};
use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_llm::{ChatMessage, DeepSeekClient, DEFAULT_MODEL};

use sea_orm::DatabaseConnection;
use serde::{Deserialize, Serialize};
use tracing::{error, info};

// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

/// A single coherence check item.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceCheckItem {
    pub check_name: String,
    pub display_name: String,
    pub passed: bool,
    pub score: f64,
    pub issues: Vec<String>,
}

/// A grouped coherence check result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceGroupCheck {
    pub group_name: String,
    pub display_name: String,
    pub passed: bool,
    pub score: f64,
    pub checks: Vec<CoherenceCheckItem>,
    #[serde(default)]
    pub cross_cutting_issues: Vec<String>,
}

/// Overall coherence validation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceValidationResult {
    pub passed: bool,
    pub overall_score: f64,
    pub version: String,
    pub groups: Vec<CoherenceGroupCheck>,
}

impl Default for CoherenceValidationResult {
    fn default() -> Self {
        Self {
            passed: true,
            overall_score: 1.0,
            version: "v2-grouped".to_string(),
            groups: Vec::new(),
        }
    }
}

/// Context built once and shared across the three grouped LLM checks.
#[derive(Debug, Clone)]
struct CoherenceContext {
    shared_prefix: String,
    character_list: String,
    timeline_summary: String,
    promise_summary: String,
    world_summary: String,
    baseline_text: String,
    #[allow(dead_code)]
    must_hold: Vec<String>,
    #[allow(dead_code)]
    must_not: Vec<String>,
}

// ---------------------------------------------------------------------------
// CoherenceService
// ---------------------------------------------------------------------------

/// Service for coherence validation (post-generation, v2 grouped checks).
#[derive(Clone)]
pub struct CoherenceService {
    vault_dao: VaultDao,
    chapter_dao: ChapterDao,
    secret_dao: SecretDao,
    dynamic_layer_dao: DynamicLayerDao,
    llm_client: Arc<DeepSeekClient>,
    llm_api_key: String,
}

impl CoherenceService {
    /// Create a new CoherenceService.
    pub fn new(
        vault_dao: VaultDao,
        chapter_dao: ChapterDao,
        secret_dao: SecretDao,
        dynamic_layer_dao: DynamicLayerDao,
        llm_client: DeepSeekClient,
        llm_api_key: impl Into<String>,
    ) -> Self {
        Self {
            vault_dao,
            chapter_dao,
            secret_dao,
            dynamic_layer_dao,
            llm_client: Arc::new(llm_client),
            llm_api_key: llm_api_key.into(),
        }
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Post-generation coherence validation with 3 grouped LLM calls.
    ///
    /// Groups the 8 individual checks into 3 merged LLM calls:
    /// - Group A: Narrative Consistency (character + timeline + plot promise)
    /// - Group B: Writing Quality (world rule + style + pacing + baseline)
    /// - Group C: Continuity (chapter transition + secret debt)
    ///
    /// Returns a `CoherenceValidationResult` with passed/failed status and scores.
    pub async fn validate_post_generation(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: &str,
        generated_content: &str,
        project_title: &str,
        _chapter_title: &str,
        chapter_number: i32,
    ) -> CoherenceValidationResult {
        let mut result = CoherenceValidationResult::default();

        // Get chapter
        let chapter = match self.chapter_dao.find_by_id(db, chapter_id).await {
            Ok(Some(ch)) => ch,
            Ok(None) => {
                result.passed = false;
                result.overall_score = 0.0;
                error!("Chapter not found: {chapter_id}");
                return result;
            }
            Err(e) => {
                result.passed = false;
                result.overall_score = 0.0;
                error!("Error fetching chapter {chapter_id}: {e}");
                return result;
            }
        };

        // Get previous chapter
        let previous_chapter = if chapter_number > 1 {
            match self
                .chapter_dao
                .find_by_number(db, project_id, chapter_number - 1)
                .await
            {
                Ok(prev) => prev,
                Err(_) => None,
            }
        } else {
            None
        };

        // Build shared context once — all 3 groups reuse this
        let ctx = match self
            .build_coherence_context(
                db,
                project_id,
                project_title,
                &chapter.title,
                chapter_number,
                generated_content,
            )
            .await
        {
            Ok(ctx) => ctx,
            Err(e) => {
                error!("Failed to build coherence context: {e}");
                result.passed = false;
                result.overall_score = 0.0;
                return result;
            }
        };

        // Group A: Narrative Consistency
        info!("Post-validation: Group A - Narrative consistency for chapter {chapter_id}");
        let group_a = self
            .check_group_narrative_consistency(&ctx)
            .await;
        result.groups.push(group_a);

        // Group B: Writing Quality
        info!("Post-validation: Group B - Writing quality for chapter {chapter_id}");
        let group_b = self
            .check_group_writing_quality(
                &ctx,
                previous_chapter.as_ref(),
            )
            .await;
        result.groups.push(group_b);

        // Group C: Continuity
        info!("Post-validation: Group C - Continuity for chapter {chapter_id}");
        let group_c = self
            .check_group_continuity(
                db,
                &ctx,
                project_id,
                chapter_number,
                previous_chapter.as_ref(),
                generated_content,
            )
            .await;
        result.groups.push(group_c);

        // Calculate overall result
        let all_passed = result.groups.iter().all(|g| g.passed);
        let total_score: f64 = result.groups.iter().map(|g| g.score).sum();
        let group_count = result.groups.len();
        let avg_score = if group_count > 0 {
            total_score / group_count as f64
        } else {
            1.0
        };

        result.passed = all_passed;
        result.overall_score = (avg_score * 100.0).round() / 100.0;

        info!(
            "Post-validation completed for chapter {chapter_id}: passed={all_passed}, score={avg_score:.2}"
        );
        result
    }

    // ------------------------------------------------------------------
    // Context Building
    // ------------------------------------------------------------------

    /// Build shared context dict used as the common prefix for all 3 groups.
    ///
    /// DeepSeek transparent prefix caching: all 3 groups share this exact
    /// prefix text, so Groups B and C automatically benefit from cache hits.
    async fn build_coherence_context(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        project_title: &str,
        chapter_title: &str,
        chapter_number: i32,
        generated_content: &str,
    ) -> AppResult<CoherenceContext> {
        // Character list
        let characters = self.vault_dao.find_characters(db, project_id).await?;
        let character_list: String = if characters.is_empty() {
            "暂无角色".to_string()
        } else {
            characters
                .iter()
                .take(10)
                .map(|c| c.name.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        };

        // Timeline events (last 10)
        let vault_events = self.vault_dao.find_timeline_events(db, project_id).await?;
        let timeline_summary: String = if vault_events.is_empty() {
            "暂无".to_string()
        } else {
            vault_events
                .iter()
                .rev()
                .take(10)
                .map(|e| format!("- 第{}章: {}", e.chapter_number, e.event))
                .collect::<Vec<_>>()
                .join("\n")
        };

        // Active plot promises (top 8)
        let promises = self.vault_dao.find_plot_promises(db, project_id).await?;
        let active_promises: Vec<_> = promises
            .iter()
            .filter(|p| p.status == "dormant" || p.status == "active")
            .collect();
        let promise_summary: String = if active_promises.is_empty() {
            "无活跃伏笔".to_string()
        } else {
            active_promises
                .iter()
                .take(8)
                .map(|p| {
                    let desc = p.description.as_str();
                    let desc_preview = if desc.len() > 100 { &desc[..100] } else { desc };
                    format!(
                        "- [{}] {} (状态: {}, 紧迫度: {})",
                        p.r#type, desc_preview, p.status, p.urgency
                    )
                })
                .collect::<Vec<_>>()
                .join("\n")
        };

        // World rules
        let world_entries = self.vault_dao.find_world_entries(db, project_id).await?;
        let world_summary: String = if world_entries.is_empty() {
            "无世界观设定".to_string()
        } else {
            world_entries
                .iter()
                .take(8)
                .map(|e| {
                    let desc = e.description.as_str();
                    let desc_preview = if desc.len() > 150 { &desc[..150] } else { desc };
                    let mut line = format!("- [{}] {}: {}", e.category, e.name, desc_preview);
                    if let Some(ref constraint) = e.constraint {
                        if !constraint.is_empty() {
                            let c = if constraint.len() > 100 {
                                &constraint[..100]
                            } else {
                                constraint
                            };
                            line.push_str(&format!(" (约束: {c})"));
                        }
                    }
                    line
                })
                .collect::<Vec<_>>()
                .join("\n")
        };

        // Dynamic layer baseline
        let latest_dl = self
            .dynamic_layer_dao
            .find_latest_by_project(db, project_id)
            .await?;
        let (must_hold_list, must_not_list, baseline_text) =
            if let Some(ref dl) = latest_dl {
                let mh: Vec<String> = dl.must_hold.as_ref()
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                    .unwrap_or_default();
                let mn: Vec<String> = dl.must_not.as_ref()
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                    .unwrap_or_default();
                let text = if !mh.is_empty() || !mn.is_empty() {
                    let mh_str = if mh.is_empty() {
                        "无".to_string()
                    } else {
                        mh.iter()
                            .map(|item| format!("  - {item}"))
                            .collect::<Vec<_>>()
                            .join("\n")
                    };
                    let mn_str = if mn.is_empty() {
                        "无".to_string()
                    } else {
                        mn.iter()
                            .map(|item| format!("  - {item}"))
                            .collect::<Vec<_>>()
                            .join("\n")
                    };
                    format!(
                        "【连贯性基线】\n必须保持(must_hold):\n{mh_str}\n必须避免(must_not):\n{mn_str}\n"
                    )
                } else {
                    String::new()
                };
                (mh, mn, text)
            } else {
                (Vec::new(), Vec::new(), String::new())
            };

        let content_len = generated_content.len();
        let content_preview = if generated_content.len() > 4000 {
            &generated_content[..4000]
        } else {
            generated_content
        };

        let shared_prefix = format!(
            "项目：{project_title}\n\
             当前章节：第{chapter_number}章《{chapter_title}》\n\
             章节长度：{content_len} 字\n\n\
             【本章全文】\n\
             {content_preview}\n\n\
             【全量剧本数据】\n\
             角色列表：{character_list}\n\n\
             时间线事件：\n{timeline_summary}\n\n\
             活跃伏笔：\n{promise_summary}\n\n\
             世界观设定：\n{world_summary}\n\n\
             {baseline_text}"
        );

        Ok(CoherenceContext {
            shared_prefix,
            character_list,
            timeline_summary,
            promise_summary,
            world_summary,
            baseline_text,
            must_hold: must_hold_list,
            must_not: must_not_list,
        })
    }

    // ------------------------------------------------------------------
    // Group A: Narrative Consistency
    // ------------------------------------------------------------------

    async fn check_group_narrative_consistency(
        &self,
        ctx: &CoherenceContext,
    ) -> CoherenceGroupCheck {
        let mut group = CoherenceGroupCheck {
            group_name: "narrative_consistency".to_string(),
            display_name: "叙事一致性".to_string(),
            passed: true,
            score: 1.0,
            checks: Vec::new(),
            cross_cutting_issues: Vec::new(),
        };

        let prompt = format!(
            r#"{}
【检查项目 — 叙事一致性】
请对本章内容执行以下 3 项检查：

检查 1 — 角色行为一致性
角色列表：{}
检查角色行为是否符合其性格设定和当前状态。

检查 2 — 时间线连续性
现有时间线事件：
{}
检查事件顺序是否合理，是否存在时间逻辑矛盾。

检查 3 — 伏笔状态
活跃伏笔列表：
{}
检查本章是否推进了活跃伏笔，或产生了新伏笔。

请逐项检查，并返回如下 JSON 格式（只返回 JSON，不要其他内容）：
{{
  "checks": [
    {{
      "check_name": "character_consistency",
      "display_name": "角色行为一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "timeline_continuity",
      "display_name": "时间线连续性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "plot_promise_status",
      "display_name": "伏笔状态",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现"]或[]
}}"#,
            ctx.shared_prefix, ctx.character_list, ctx.timeline_summary, ctx.promise_summary
        );

        match self.call_llm_json(&prompt, 3072).await {
            Ok(result) => {
                if let Some(checks) = result.get("checks").and_then(|c| c.as_array()) {
                    for raw in checks {
                        group.checks.push(CoherenceCheckItem {
                            check_name: raw
                                .get("check_name")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            display_name: raw
                                .get("display_name")
                                .and_then(|v| v.as_str())
                                .unwrap_or("")
                                .to_string(),
                            passed: raw.get("passed").and_then(|v| v.as_bool()).unwrap_or(true),
                            score: raw.get("score").and_then(|v| v.as_f64()).unwrap_or(0.9),
                            issues: raw
                                .get("issues")
                                .and_then(|v| v.as_array())
                                .map(|arr| {
                                    arr.iter()
                                        .filter_map(|i| i.as_str().map(String::from))
                                        .collect()
                                })
                                .unwrap_or_default(),
                        });
                    }
                }
                if let Some(cci) = result
                    .get("cross_cutting_issues")
                    .and_then(|v| v.as_array())
                {
                    group.cross_cutting_issues = cci
                        .iter()
                        .filter_map(|i| i.as_str().map(String::from))
                        .collect();
                }

                if !group.checks.is_empty() {
                    let total: f64 = group.checks.iter().map(|c| c.score).sum();
                    group.score = (total / group.checks.len() as f64 * 100.0).round() / 100.0;
                    group.passed = group.checks.iter().all(|c| c.passed);
                }
            }
            Err(e) => {
                error!("Group A (narrative consistency) failed: {e}");
                group.checks = vec![
                    CoherenceCheckItem {
                        check_name: "character_consistency".to_string(),
                        display_name: "角色行为一致性".to_string(),
                        passed: false, score: 0.0,
                        issues: vec!["LLM 调用失败，无法完成检查。请重试或手动审核。".to_string()],
                    },
                    CoherenceCheckItem {
                        check_name: "timeline_continuity".to_string(),
                        display_name: "时间线连续性".to_string(),
                        passed: false, score: 0.0,
                        issues: vec!["LLM 调用失败，无法完成检查。请重试或手动审核。".to_string()],
                    },
                    CoherenceCheckItem {
                        check_name: "plot_promise_status".to_string(),
                        display_name: "伏笔状态".to_string(),
                        passed: false, score: 0.0,
                        issues: vec!["LLM 调用失败，无法完成检查。请重试或手动审核。".to_string()],
                    },
                ];
                group.passed = false;
                group.score = 0.0;
            }
        }

        group
    }

    // ------------------------------------------------------------------
    // Group B: Writing Quality + Baseline Compliance
    // ------------------------------------------------------------------

    async fn check_group_writing_quality(
        &self,
        ctx: &CoherenceContext,
        previous_chapter: Option<&moling_db::entities::chapter::Model>,
    ) -> CoherenceGroupCheck {
        let mut group = CoherenceGroupCheck {
            group_name: "writing_quality".to_string(),
            display_name: "写作质量".to_string(),
            passed: true,
            score: 1.0,
            checks: Vec::new(),
            cross_cutting_issues: Vec::new(),
        };

        let prev_style_ref = previous_chapter
            .and_then(|ch| ch.content.as_deref())
            .map(|content| {
                if content.len() > 1500 {
                    &content[..1500]
                } else {
                    content
                }
            })
            .unwrap_or("");

        let (baseline_section, baseline_instruction) = if !ctx.baseline_text.is_empty() {
            (
                ctx.baseline_text.clone(),
                "【检查 4 — 连贯性基线校验】\n检查本章内容是否违反了 must_hold（必须保持）和 must_not（必须避免）的硬约束。如有违反，需定位到具体段落并引用被违反的基线条目。如无基线约束，此项直接通过。".to_string(),
            )
        } else {
            (
                "【连贯性基线】\n无基线约束设定（此项直接通过）\n".to_string(),
                String::new(),
            )
        };

        let prompt = format!(
            r#"请对以下小说章节内容执行写作质量检查，并以 JSON 格式返回结果。

{}

【检查 1 — 世界观规则一致性】
世界观设定条目：
{}
检查内容是否与世界观设定一致，有无违规描述。

【检查 2 — 文风一致性】
前序章节内容（前1500字，无前序章节则检查文风内部一致性）：
{}

【检查 3 — 叙事节奏合理性】

{}
{}

请逐项检查，并返回如下 JSON 格式（只返回 JSON，不要其他内容）：
{{
  "checks": [
    {{
      "check_name": "world_rule_consistency",
      "display_name": "世界观规则一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体违规描述"]或[]
    }},
    {{
      "check_name": "writing_style_consistency",
      "display_name": "文风一致性",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体差异描述"]或[]
    }},
    {{
      "check_name": "narrative_pacing",
      "display_name": "叙事节奏",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "baseline_compliance",
      "display_name": "连贯性基线校验",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["违反的基线条目及定位段落"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现"]或[]
}}"#,
            ctx.shared_prefix,
            ctx.world_summary,
            if prev_style_ref.is_empty() { "（无前序章节）" } else { prev_style_ref },
            baseline_section,
            baseline_instruction,
        );

        match self.call_llm_json(&prompt, 3072).await {
            Ok(result) => {
                if let Some(checks) = result.get("checks").and_then(|c| c.as_array()) {
                    for raw in checks {
                        group.checks.push(CoherenceCheckItem {
                            check_name: raw.get("check_name").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
                            display_name: raw.get("display_name").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                            passed: raw.get("passed").and_then(|v| v.as_bool()).unwrap_or(true),
                            score: raw.get("score").and_then(|v| v.as_f64()).unwrap_or(0.9),
                            issues: raw.get("issues").and_then(|v| v.as_array())
                                .map(|arr| arr.iter().filter_map(|i| i.as_str().map(String::from)).collect())
                                .unwrap_or_default(),
                        });
                    }
                }
                if let Some(cci) = result.get("cross_cutting_issues").and_then(|v| v.as_array()) {
                    group.cross_cutting_issues = cci.iter().filter_map(|i| i.as_str().map(String::from)).collect();
                }
                if !group.checks.is_empty() {
                    let total: f64 = group.checks.iter().map(|c| c.score).sum();
                    group.score = (total / group.checks.len() as f64 * 100.0).round() / 100.0;
                    group.passed = group.checks.iter().all(|c| c.passed);
                }
            }
            Err(e) => {
                error!("Group B (writing quality) failed: {e}");
                group.checks = vec![
                    CoherenceCheckItem { check_name: "world_rule_consistency".into(), display_name: "世界观规则一致性".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                    CoherenceCheckItem { check_name: "writing_style_consistency".into(), display_name: "文风一致性".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                    CoherenceCheckItem { check_name: "narrative_pacing".into(), display_name: "叙事节奏".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                    CoherenceCheckItem { check_name: "baseline_compliance".into(), display_name: "连贯性基线校验".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                ];
                group.passed = false;
                group.score = 0.0;
            }
        }

        group
    }

    // ------------------------------------------------------------------
    // Group C: Continuity
    // ------------------------------------------------------------------

    async fn check_group_continuity(
        &self,
        db: &DatabaseConnection,
        ctx: &CoherenceContext,
        project_id: i32,
        chapter_number: i32,
        previous_chapter: Option<&moling_db::entities::chapter::Model>,
        generated_content: &str,
    ) -> CoherenceGroupCheck {
        let mut group = CoherenceGroupCheck {
            group_name: "continuity".to_string(),
            display_name: "连续性".to_string(),
            passed: true,
            score: 1.0,
            checks: Vec::new(),
            cross_cutting_issues: Vec::new(),
        };

        // Chapter transition context
        let prev_end = previous_chapter
            .and_then(|ch| ch.content.as_deref())
            .map(|content| {
                if content.len() > 1000 {
                    &content[content.len() - 1000..]
                } else {
                    content
                }
            })
            .unwrap_or("");

        let new_start = if generated_content.len() > 1000 {
            &generated_content[..1000]
        } else {
            generated_content
        };

        // Secret debt calculation (rule-based)
        let secrets = match self.secret_dao.list_by_project(db, project_id).await {
            Ok(s) => s,
            Err(e) => {
                error!("Failed to load secrets for continuity check: {e}");
                Vec::new()
            }
        };

        let mut secret_debt_issues: Vec<String> = Vec::new();
        let mut secrets_for_llm: Vec<&moling_db::entities::secret::Model> = Vec::new();

        for secret in &secrets {
            if secret.secrecy_level == "revealed" || secret.secrecy_level == "open" {
                continue;
            }
            let created_ch = match secret.created_chapter {
                Some(ch) => ch,
                None => continue,
            };

            secrets_for_llm.push(secret);
            let chapters_elapsed = std::cmp::max(0, chapter_number - created_ch);
            let unknown_count = secret.unknown_to.as_array()
                .map(|arr| arr.len())
                .unwrap_or(0) as i32;

            let debt = chapters_elapsed * unknown_count;
            if debt > 30 {
                secret_debt_issues.push(format!(
                    "秘密「{}」信息债务过高（{debt} = {chapters_elapsed}章 × {unknown_count}人不知晓），建议安排揭露",
                    secret.description
                ));
            }
        }

        // Build secret summary for LLM
        let secret_summary: String = if secrets_for_llm.is_empty() {
            "无未公开秘密".to_string()
        } else {
            secrets_for_llm
                .iter()
                .take(10)
                .map(|s| {
                    let known = s.known_by.as_array()
                        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>().join(", "))
                        .unwrap_or_else(|| "无".to_string());
                    let unknown = s.unknown_to.as_array()
                        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>().join(", "))
                        .unwrap_or_else(|| "无".to_string());
                    format!(
                        "- 秘密(#{}): {}\n  知晓者: {} | 不知晓者: {} | 保密层级: {}",
                        s.id, s.description, known, unknown, s.secrecy_level
                    )
                })
                .collect::<Vec<_>>()
                .join("\n")
        };

        let dynamic_section = format!(
            r#"
【检查 1 — 章节衔接自然性】
前序章节结尾（末尾1000字）：
{}

当前章节开头（前1000字）：
{}

【检查 2 — 秘密债务一致性】
项目秘密列表（未公开）：
{}

请逐项检查：
- 章节衔接：两章之间的衔接是否自然流畅？场景/视角切换是否合理？
- 秘密债务：是否有角色说出了TA不该知道的秘密？或做出了对已知秘密的矛盾反应？
"#,
            if prev_end.is_empty() { "（无前序章节，此项直接通过）" } else { prev_end },
            new_start,
            secret_summary,
        );

        let prompt = format!(
            r#"{}
{}
返回如下 JSON 格式（只返回 JSON，不要其他内容，不要 markdown 代码块）：
{{
  "checks": [
    {{
      "check_name": "chapter_transition",
      "display_name": "章节衔接",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }},
    {{
      "check_name": "secret_debt",
      "display_name": "秘密债务",
      "passed": true/false,
      "score": 0.0-1.0,
      "issues": ["具体问题描述"]或[]
    }}
  ],
  "cross_cutting_issues": ["跨维度发现"]或[]
}}"#,
            ctx.shared_prefix, dynamic_section
        );

        match self.call_llm_json(&prompt, 3072).await {
            Ok(result) => {
                if let Some(checks) = result.get("checks").and_then(|c| c.as_array()) {
                    for raw in checks {
                        let mut issues: Vec<String> = raw
                            .get("issues")
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|i| i.as_str().map(String::from))
                                    .collect()
                            })
                            .unwrap_or_default();

                        if raw.get("check_name").and_then(|v| v.as_str()) == Some("secret_debt") {
                            issues.extend(secret_debt_issues.clone());
                        }

                        group.checks.push(CoherenceCheckItem {
                            check_name: raw.get("check_name").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
                            display_name: raw.get("display_name").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                            passed: raw.get("passed").and_then(|v| v.as_bool()).unwrap_or(true),
                            score: raw.get("score").and_then(|v| v.as_f64()).unwrap_or(0.9),
                            issues,
                        });
                    }
                }
                if let Some(cci) = result.get("cross_cutting_issues").and_then(|v| v.as_array()) {
                    group.cross_cutting_issues = cci.iter().filter_map(|i| i.as_str().map(String::from)).collect();
                }
                if !group.checks.is_empty() {
                    let total: f64 = group.checks.iter().map(|c| c.score).sum();
                    group.score = (total / group.checks.len() as f64 * 100.0).round() / 100.0;
                    group.passed = group.checks.iter().all(|c| c.passed);
                }
            }
            Err(e) => {
                error!("Group C (continuity) failed: {e}");
                group.checks = vec![
                    CoherenceCheckItem { check_name: "chapter_transition".into(), display_name: "章节衔接".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                    CoherenceCheckItem { check_name: "secret_debt".into(), display_name: "秘密债务".into(), passed: false, score: 0.0, issues: vec!["LLM 调用失败".into()] },
                ];
                group.passed = false;
                group.score = 0.0;
            }
        }

        group
    }

    // ------------------------------------------------------------------
    // LLM Helpers
    // ------------------------------------------------------------------

    /// Call LLM and parse JSON response.
    async fn call_llm_json(&self, prompt: &str, max_tokens: u32) -> AppResult<serde_json::Value> {
        let messages = vec![
            ChatMessage::system("你是一个专业的小说质量检查助手。"),
            ChatMessage::user(prompt),
        ];

        let response = self
            .llm_client
            .chat(
                &messages,
                &self.llm_api_key,
                DEFAULT_MODEL,
                0.3,
                max_tokens,
            )
            .await?;

        let cleaned = clean_json_response(&response);
        let parsed: serde_json::Value = serde_json::from_str(&cleaned).map_err(|e| {
            error!("Failed to parse LLM JSON response: {e}");
            AppError::internal(format!("LLM response parse failed: {e}"))
        })?;

        Ok(parsed)
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Clean LLM response by stripping markdown code fences.
pub fn clean_json_response(raw: &str) -> String {
    let mut cleaned = raw.trim().to_string();
    if cleaned.starts_with("```") {
        if let Some(after_newline) = cleaned.find('\n') {
            cleaned = cleaned[after_newline + 1..].to_string();
        } else {
            cleaned = cleaned[3..].to_string();
        }
        if let Some(end) = cleaned.rfind("```") {
            cleaned = cleaned[..end].to_string();
        }
    }
    cleaned.trim().to_string()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_json_response_no_fences() {
        let input = r#"{"key": "value"}"#;
        assert_eq!(clean_json_response(input), r#"{"key": "value"}"#);
    }

    #[test]
    fn test_clean_json_response_with_fences() {
        let input = "```json\n{\"key\": \"value\"}\n```";
        assert_eq!(clean_json_response(input), r#"{"key": "value"}"#);
    }

    #[test]
    fn test_coherence_check_item_defaults() {
        let item = CoherenceCheckItem {
            check_name: "test".into(),
            display_name: "测试".into(),
            passed: true,
            score: 0.5,
            issues: vec![],
        };
        assert!(item.passed);
        assert_eq!(item.score, 0.5);
    }

    #[test]
    fn test_validation_result_default() {
        let result = CoherenceValidationResult::default();
        assert!(result.passed);
        assert_eq!(result.overall_score, 1.0);
        assert_eq!(result.version, "v2-grouped");
    }
}
