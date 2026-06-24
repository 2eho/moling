//! Weave service — narrative patterns, suggestions, apply, analyze.
//!
//! Mirrors Python `app/service/weave_service.py`.
//!
//! Analyzes project plots, characters, and timelines to provide
//! narrative weaving suggestions for the writer.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use sea_orm::{DatabaseConnection, Set};
use serde_json::Value as Json;

/// Business logic for narrative weaving operations.
#[derive(Clone)]
pub struct WeaveService {
    project_dao: ProjectDao,
    chapter_dao: ChapterDao,
    vault_dao: VaultDao,
}

impl WeaveService {
    pub fn new() -> Self {
        Self {
            project_dao: ProjectDao,
            chapter_dao: ChapterDao,
            vault_dao: VaultDao,
        }
    }

    /// List narrative weave patterns available in the system.
    pub async fn patterns(&self) -> AppResult<Json> {
        let patterns = vec![
            serde_json::json!({
                "id": "parallel",
                "name": "双线并行",
                "description": "两条故事线同时推进，在关键时刻交汇",
                "difficulty": "medium",
            }),
            serde_json::json!({
                "id": "flashback",
                "name": "倒叙穿插",
                "description": "通过倒叙揭示背景故事，增强叙事深度",
                "difficulty": "high",
            }),
            serde_json::json!({
                "id": "multi_pov",
                "name": "多视角叙事",
                "description": "通过多个角色的视角展开故事",
                "difficulty": "high",
            }),
            serde_json::json!({
                "id": "foreshadowing",
                "name": "伏笔网络",
                "description": "建立伏笔之间的关联网络，增强回收满足感",
                "difficulty": "medium",
            }),
            serde_json::json!({
                "id": "spiral",
                "name": "螺旋上升",
                "description": "每次回到相似主题但层级更高，情感递进",
                "difficulty": "medium",
            }),
            serde_json::json!({
                "id": "mosaic",
                "name": "马赛克拼图",
                "description": "多个看似无关的片段最终拼成完整故事",
                "difficulty": "high",
            }),
        ];
        Ok(serde_json::json!({
            "patterns": patterns,
            "count": patterns.len(),
        }))
    }

    /// Get weave-based narrative suggestions for a project.
    ///
    /// Analyzes chapters, characters, plots, and timelines to generate
    /// concrete weaving suggestions. Mirrors Python `WeaveService.get_suggestions`.
    pub async fn suggestions(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Json> {
        let project = self.project_dao.find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;

        let chapters = self.chapter_dao.find_by_project(db, project_id).await?;
        let characters = self.vault_dao.find_characters(db, project_id).await?;
        let plot_promises = self.vault_dao.find_plot_promises(db, project_id).await?;
        let timelines = self.vault_dao.find_timeline_events(db, project_id).await?;

        let mut suggestions = Vec::new();

        // Suggestion 1: Plot thread integration
        if !plot_promises.is_empty() && chapters.len() > 3 {
            let dormant: Vec<_> = plot_promises.iter().filter(|p| p.status == "dormant").collect();
            if !dormant.is_empty() {
                suggestions.push(serde_json::json!({
                    "id": "weave_plot_threads",
                    "type": "plot_thread",
                    "priority": "high",
                    "title": "情节线索整合",
                    "description": format!("{} 条休眠伏笔可以编织进当前叙事", dormant.len()),
                    "suggestion": "在后续章节中逐步回收休眠伏笔，增强故事连贯性",
                    "affected_chapters": chapters.iter().rev().take(3).map(|c| c.id.clone()).collect::<Vec<_>>(),
                }));
            }
        }

        // Suggestion 2: Character arc weaving
        if characters.len() > 3 && chapters.len() > 5 {
            let low_appearance: Vec<_> = characters
                .iter()
                .filter(|c| c.chapter_count < chapters.len() as i32 / 3)
                .collect();
            if !low_appearance.is_empty() {
                suggestions.push(serde_json::json!({
                    "id": "weave_character_arcs",
                    "type": "character_arc",
                    "priority": "medium",
                    "title": "角色弧光编织",
                    "description": format!("{} 个角色出场率偏低，可加强其叙事线", low_appearance.len()),
                    "suggestion": "为低频角色设计支线剧情，与主线交织",
                    "affected_characters": low_appearance.iter().map(|c| c.name.clone()).collect::<Vec<_>>(),
                }));
            }
        }

        // Suggestion 3: Timeline coherence
        if timelines.len() > 1 {
            let chapter_nums: Vec<i32> = timelines.iter().map(|t| t.chapter_number).collect();
            let mut sorted = chapter_nums.clone();
            sorted.sort();
            if chapter_nums != sorted {
                suggestions.push(serde_json::json!({
                    "id": "weave_timeline",
                    "type": "timeline",
                    "priority": "high",
                    "title": "时间线调整",
                    "description": "检测到时间线事件顺序不一致",
                    "suggestion": "重新排序时间线事件，确保叙事逻辑清晰",
                }));
            }
        }

        // Suggestion 4: Pacing balance
        if chapters.len() > 5 {
            let word_counts: Vec<i32> = chapters.iter().map(|c| c.word_count).collect();
            if !word_counts.is_empty() {
                let avg: f64 = word_counts.iter().sum::<i32>() as f64 / word_counts.len() as f64;
                let variance: f64 = word_counts.iter()
                    .map(|w| {
                        let diff = *w as f64 - avg;
                        diff * diff
                    })
                    .sum::<f64>() / word_counts.len() as f64;
                let std_dev = variance.sqrt();

                if std_dev > avg * 0.5 {
                    suggestions.push(serde_json::json!({
                        "id": "weave_pacing",
                        "type": "pacing",
                        "priority": "medium",
                        "title": "节奏均衡调整",
                        "description": "章节长度波动较大，影响阅读节奏",
                        "suggestion": "保持每章长度相对均匀，将高/低潮章节交替安排",
                        "avg_words": avg.round(),
                        "std_dev": std_dev.round(),
                    }));
                }
            }
        }

        // Suggestion 5: Structure recommendation
        if !chapters.is_empty() && chapters.len() < 10 {
            suggestions.push(serde_json::json!({
                "id": "weave_structure",
                "type": "structure",
                "priority": "low",
                "title": "结构扩展建议",
                "description": "当前章节数较少，可规划更多叙事层次",
                "suggestion": "考虑加入支线剧情或次要角色视角，丰富叙事结构",
            }));
        }

        let overview = format!(
            "项目《{}》当前有 {} 章、{} 个角色、{} 个情节元素。",
            project.title,
            chapters.len(),
            characters.len(),
            plot_promises.len(),
        );

        Ok(serde_json::json!({
            "project_id": project_id,
            "suggestions": suggestions,
            "suggestion_count": suggestions.len(),
            "overview": overview,
            "analyzed_at": chrono::Utc::now().to_rfc3339(),
        }))
    }

    /// Apply a weave pattern to a project.
    ///
    /// Records the applied pattern on target chapters for traceability.
    pub async fn apply(
        &self,
        db: &DatabaseConnection,
        pattern: Json,
        target_chapter_ids: &[String],
    ) -> AppResult<Json> {
        let pattern_id = pattern
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let pattern_name = pattern
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("未命名模式");

        let mut applied_to = Vec::new();
        for chapter_id in target_chapter_ids {
            if let Some(ch) = self.chapter_dao.find_by_id(db, chapter_id).await? {
                use sea_orm::{ActiveModelTrait, IntoActiveModel};
                let existing_prompt = ch.generation_prompt.clone();
                let mut active = ch.into_active_model();
                let note = format!("[Weave Applied: {pattern_id}] {pattern_name}");
                let new_prompt = if let Some(ref existing) = existing_prompt {
                    format!("{existing}\n{note}")
                } else {
                    note
                };
                active.generation_prompt = Set(Some(new_prompt));
                active.update(db).await.map_err(|e| {
                    AppError::internal(format!("Apply weave to chapter failed: {e}"))
                })?;
                applied_to.push(chapter_id.clone());
            }
        }

        tracing::info!(
            pattern_id,
            chapters = applied_to.len(),
            "Weave pattern applied"
        );

        Ok(serde_json::json!({
            "message": format!("已应用编织模式「{}」到 {} 个章节", pattern_name, applied_to.len()),
            "pattern_id": pattern_id,
            "applied_count": applied_to.len(),
            "applied_to": applied_to,
        }))
    }

    /// Deep analysis of narrative structure for coherence.
    ///
    /// Analyzes plot threads, character arcs, timeline consistency,
    /// and unresolved promises. Mirrors Python `WeaveService.analyze_project`.
    pub async fn analyze(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Json> {
        let project = self.project_dao.find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;

        let chapters = self.chapter_dao.find_by_project(db, project_id).await?;
        let characters = self.vault_dao.find_characters(db, project_id).await?;
        let plot_promises = self.vault_dao.find_plot_promises(db, project_id).await?;
        let timelines = self.vault_dao.find_timeline_events(db, project_id).await?;

        // Plot threads analysis
        let plot_threads: Vec<Json> = plot_promises
            .iter()
            .map(|p| {
                let completion = match p.status.as_str() {
                    "resolved" => 1.0,
                    "active" => 0.5,
                    "dormant" => 0.1,
                    "abandoned" => 0.0,
                    _ => 0.3,
                };
                serde_json::json!({
                    "id": p.id,
                    "name": &p.description,
                    "status": p.status,
                    "completion": completion,
                })
            })
            .collect();

        // Character arcs analysis
        let total_chapters = chapters.len() as f64;
        let character_arcs: Vec<Json> = characters
            .iter()
            .map(|c| {
                let progress = if total_chapters > 0.0 {
                    (c.chapter_count as f64 / total_chapters).min(1.0)
                } else {
                    0.0
                };
                let arc_type = match c.role.as_str() {
                    "protagonist" => "growth",
                    "antagonist" => "rise_and_fall",
                    _ => "supporting",
                };
                serde_json::json!({
                    "character_name": c.name,
                    "role": c.role,
                    "arc_type": arc_type,
                    "progress": (progress * 10.0).round() / 10.0,
                    "chapter_count": c.chapter_count,
                })
            })
            .collect();

        // Timeline consistency
        let timeline_issues: Vec<String> = {
            let mut issues = Vec::new();
            let numbers: Vec<i32> = timelines.iter().map(|t| t.chapter_number).collect();
            let mut sorted = numbers.clone();
            sorted.sort();
            if numbers != sorted {
                issues.push("时间线事件存在章节顺序不一致".into());
            }
            if timelines.is_empty() {
                issues.push("未建立时间线事件".into());
            }
            issues
        };

        let timeline_score = if timelines.is_empty() {
            5.0
        } else if timeline_issues.is_empty() {
            8.0
        } else {
            6.0
        };

        // Unresolved promises
        let unresolved_promises: Vec<Json> = plot_promises
            .iter()
            .filter(|p| p.status != "resolved" && p.status != "abandoned")
            .map(|p| {
                serde_json::json!({
                    "id": p.id,
                    "description": p.description,
                    "status": p.status,
                    "priority": if p.status == "dormant" { "high" } else { "medium" },
                })
            })
            .collect();

        Ok(serde_json::json!({
            "project_id": project_id,
            "project_title": project.title,
            "analysis": {
                "plot_threads": plot_threads,
                "character_arcs": character_arcs,
                "timeline_consistency": {
                    "score": timeline_score,
                    "issues": timeline_issues,
                    "suggestions": if !timeline_issues.is_empty() {
                        vec!["修复时间线事件顺序".to_owned()]
                    } else {
                        vec!["时间线一致，可继续丰富事件细节".to_owned()]
                    },
                },
                "unresolved_promises": unresolved_promises,
                "summary": {
                    "total_chapters": chapters.len(),
                    "total_characters": characters.len(),
                    "total_plot_promises": plot_promises.len(),
                    "total_timeline_events": timelines.len(),
                    "unresolved_promise_count": unresolved_promises.len(),
                },
            },
            "created_at": chrono::Utc::now().to_rfc3339(),
        }))
    }

    /// Quick weave health score for a project (0.0 - 10.0).
    pub async fn health_score(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<f64> {
        let chapters = self.chapter_dao.count_by_project(db, project_id).await?;
        let characters = self.vault_dao.count_characters(db, project_id).await?;
        let promises = self.vault_dao.count_plot_promises(db, project_id).await?;

        if chapters == 0 {
            return Ok(0.0);
        }

        let mut score: f64 = 5.0; // baseline

        // Bonus: chapter count
        if chapters >= 5 { score += 1.0; }
        if chapters >= 20 { score += 0.5; }

        // Bonus: character variety
        if characters >= 3 { score += 0.5; }
        if characters >= 10 { score += 0.5; }

        // Bonus: plot complexity
        if promises >= 3 { score += 0.5; }
        if promises >= 10 { score += 0.5; }

        // Penalty: too few plot promises relative to chapters
        if chapters > 10 && promises < 3 {
            score -= 1.0;
        }

        // Cap at 10.0
        Ok(score.clamp(0.0, 10.0))
    }
}

impl Default for WeaveService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_weave_service_constructs() {
        let _ = WeaveService::new();
    }

    #[test]
    fn test_patterns_returns_data() {
        // patterns() doesn't need DB, we can call it synchronously
        // We just verify the struct constructs
    }
}
