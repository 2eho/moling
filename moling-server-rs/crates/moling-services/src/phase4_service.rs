//! Phase4 service — 收纳 (ingestion) pipeline: LLM analysis → four-vault merge →
//! dynamic layer update → card pool enrichment → confidence evaluation → changelog archive.
//!
//! Ported from Python `app/service/phase4_service.py` (2396 lines).

use std::sync::Arc;

use chrono::Utc;
use moling_core::error::{AppError, AppResult};
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_db::dao::phase4_dao::Phase4Dao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::{
    card_pool::{self, Model as CardPoolModel},
    dynamic_layer::{self},
    phase4_task::{self},
    vault_changelog::{self},
    vault_character::{self, Model as VaultCharacterModel},
    vault_plot_promise::{self},
    vault_timeline::{self},
    vault_world::{self},
};
use moling_llm::{ChatMessage, DeepSeekClient};
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};
use serde_json::Value as Json;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Constants — mirrors Python §11.7
// ---------------------------------------------------------------------------

/// Edit distance threshold for character fuzzy matching.
const CHARACTER_FUZZY_THRESHOLD: usize = 3;
/// Card freshness window in chapters.
#[allow(dead_code)]
const CARD_FRESHNESS_WINDOW: i32 = 3;
/// Card freshness multiplier.
#[allow(dead_code)]
const CARD_FRESHNESS_MULTIPLIER: f64 = 1.5;

/// Single Phase 4 change entry (character, timeline, promise, world).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Phase4Change {
    pub change_type: String,
    pub entity_type: String,
    pub entity_id: Option<String>,
    pub name: Option<String>,
    pub details: Json,
}

/// Result of a Phase 4 run.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Phase4Result {
    pub version: String,
    pub chapter: i32,
    pub changes: Json,
    pub summary: String,
    pub confidence: Option<Json>,
}

/// Phase 4 suggestion for content quality improvement.
#[derive(Debug, Clone, serde::Serialize)]
pub struct Phase4Suggestion {
    pub id: String,
    pub suggestion_type: String,
    pub title: String,
    pub description: String,
    pub priority: String,
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Business logic for Phase 4 storage/收纳 operations.
#[derive(Clone)]
pub struct Phase4Service {
    phase4_dao: Phase4Dao,
    vault_dao: VaultDao,
    card_dao: CardDao,
    dynamic_layer_dao: DynamicLayerDao,
    chapter_dao: ChapterDao,
    project_dao: ProjectDao,
    llm_client: Arc<DeepSeekClient>,
    api_key: String,
    model: String,
}

impl Phase4Service {
    /// Create a new Phase4Service with all DAOs and LLM configuration.
    pub fn new(llm_client: DeepSeekClient, api_key: String, model: String) -> Self {
        Self {
            phase4_dao: Phase4Dao,
            vault_dao: VaultDao,
            card_dao: CardDao,
            dynamic_layer_dao: DynamicLayerDao,
            chapter_dao: ChapterDao,
            project_dao: ProjectDao,
            llm_client: Arc::new(llm_client),
            api_key,
            model,
        }
    }

    /// Create with default model name.
    pub fn with_default_model(llm_client: DeepSeekClient, api_key: String) -> Self {
        Self::new(llm_client, api_key, moling_llm::DEFAULT_MODEL.to_owned())
    }

    // -- ownership verification --

    async fn verify_owner(&self, db: &DatabaseConnection, user_id: &str, project_id: i32) -> AppResult<()> {
        let p = self.project_dao.find_by_id(db, project_id).await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(())
    }

    // ==================================================================
    // §11.4 Public API — Phase 4 main entry
    // ==================================================================

    /// Confirm storage request, create a Phase4Task with idempotency guard.
    pub async fn confirm_storage(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
        nonce: &str,
    ) -> AppResult<Json> {
        // 1. Verify project ownership
        self.verify_owner(db, user_id, project_id).await?;

        // 2. Verify chapter
        let chapter = self.chapter_dao.find_by_id(db, chapter_id).await?
            .ok_or_else(AppError::chapter_not_found)?;
        if chapter.project_id != project_id {
            return Err(AppError::bad_request("章节不属于该项目"));
        }
        if chapter.content.is_none() {
            return Err(AppError::bad_request("章节无内容可收纳"));
        }

        // 3. Idempotency check via nonce
        if let Some(existing) = self.phase4_dao.find_by_nonce(db, nonce).await? {
            return Ok(serde_json::json!({
                "task_id": existing.id,
                "state": existing.state,
                "message": "该收纳任务已存在",
            }));
        }

        // 4. Create task
        let model = phase4_task::ActiveModel {
            nonce: Set(nonce.to_owned()),
            project_id: Set(project_id),
            chapter_id: Set(chapter_id.to_owned()),
            state: Set("idle".to_owned()),
            status: Set("pending".to_owned()),
            ..Default::default()
        };
        let task = self.phase4_dao.create(db, model).await?;

        // 5. Update chapter phase4_status
        use sea_orm::IntoActiveModel;
        let mut chapter_active = chapter.into_active_model();
        chapter_active.phase4_status = Set("pending".to_owned());
        chapter_active.update(db).await.map_err(|e| AppError::internal(format!("更新章节状态失败: {e}")))?;

        Ok(serde_json::json!({
            "task_id": task.id,
            "state": task.state,
            "message": "收纳任务已创建，正在处理中",
        }))
    }

    /// Execute storage pipeline: LLM analysis → vault merge → card pool → archive.
    pub async fn execute_storage(
        &self,
        db: &DatabaseConnection,
        task_id: i32,
    ) -> AppResult<Json> {
        // 1. Get task
        let task = self.phase4_dao.find_by_id(db, task_id).await?
            .ok_or_else(AppError::generation_task_not_found)?;

        // 2. Set to extracting
        let mut task_active = task.clone().into_active_model();
        task_active.state = Set("extracting".to_owned());
        task_active.started_at = Set(Some(Utc::now()));
        self.phase4_dao.update(db, task_active).await?;

        // Fetch chapter and project
        let chapter = self.chapter_dao.find_by_id(db, &task.chapter_id).await?
            .ok_or_else(AppError::chapter_not_found)?;
        let project = self.project_dao.find_by_id(db, task.project_id).await?
            .ok_or_else(AppError::project_not_found)?;

        let chapter_number = chapter.chapter_number;
        let _chapter_content = chapter.content.clone().unwrap_or_default();

        // 3. LLM analysis
        tracing::info!(chapter_id = %chapter.id, "Analyzing chapter content with LLM");
        let analysis = self._analyze_chapter_content(db, &project, &chapter).await?;

        // 4. Update dynamic layer
        tracing::info!(chapter_id = %chapter.id, "Updating dynamic layer");
        self._update_dynamic_layer(db, task.project_id, &task.chapter_id, &analysis).await?;

        // 5. Update vault entities
        tracing::info!(project_id = task.project_id, "Updating vault entities");
        self._update_vault_entities(db, task.project_id, chapter_number, &analysis).await?;

        // 6. Update card pool
        tracing::info!(project_id = task.project_id, "Updating card pool");
        self._update_card_pool(db, task.project_id, &analysis).await?;

        // 7. Mark done
        let chapter_id_for_log = task.chapter_id.clone();
        let mut final_active = task.into_active_model();
        final_active.state = Set("done".to_owned());
        final_active.completed_at = Set(Some(Utc::now()));
        self.phase4_dao.update(db, final_active).await?;

        // Also update chapter
        use sea_orm::IntoActiveModel;
        let mut ch_active = chapter.into_active_model();
        ch_active.phase4_status = Set("done".to_owned());
        ch_active.update(db).await.map_err(|e| AppError::internal(format!("更新章节状态失败: {e}")))?;

        tracing::info!(chapter_id = %chapter_id_for_log, "Phase 4 storage completed");

        Ok(serde_json::json!({
            "status": "success",
            "message": "收纳完成",
            "analysis": analysis,
        }))
    }

    /// Phase 4 main entry: run the full extraction → merge pipeline (§11.4).
    ///
    /// This is the worker-facing entry that runs the complete pipeline:
    /// LLM extraction → four-vault merge → card pool enrichment →
    /// confidence evaluation → changelog archive → card retirement.
    pub async fn run_phase4(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: &str,
        chapter_text: &str,
        card_ids: Option<&[String]>,
    ) -> AppResult<Json> {
        let chapter = self.chapter_dao.find_by_id(db, chapter_id).await?
            .ok_or_else(AppError::chapter_not_found)?;
        let chapter_number = chapter.chapter_number;

        let mut result = serde_json::json!({
            "version": "",
            "chapter": chapter_number,
            "changes": {
                "characters": {"created": [], "updated": [], "status_changed": []},
                "timeline": {"added": 0},
                "plot_promises": {"created": 0, "advanced": 0, "redeemed": 0},
                "world": {"created": 0, "expanded": 0},
                "card_pool": {"added": 0},
            },
            "summary": "",
        });

        // Step [14]: LLM extraction (outside transaction)
        tracing::info!("Step [14]: Building extraction prompt and calling LLM");
        let card_ids_vec: Vec<String> = card_ids.map(|s| s.to_vec()).unwrap_or_default();
        let parsed = self._call_extraction_llm(db, project_id, chapter_text, &card_ids_vec).await;

        // Step [15]: Merge characters
        tracing::info!("Step [15]: Merging character updates");
        let char_result = self._merge_characters(
            db, project_id,
            parsed.get("character_updates").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]),
            chapter_number,
        ).await?;
        result["changes"]["characters"] = serde_json::to_value(&char_result).unwrap_or_default();

        // Step [16]: Merge timeline
        tracing::info!("Step [16]: Merging timeline updates");
        let timeline_result = self._merge_timeline(
            db, project_id,
            parsed.get("timeline_updates").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]),
            chapter_id, chapter_number,
        ).await?;
        result["changes"]["timeline"] = serde_json::to_value(&timeline_result).unwrap_or_default();

        // Step [17]: Merge plot promises
        tracing::info!("Step [17]: Merging plot promise updates");
        let promise_result = self._merge_plot_promises(
            db, project_id,
            parsed.get("plot_promise_updates").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]),
            chapter_number,
        ).await?;
        result["changes"]["plot_promises"] = serde_json::to_value(&promise_result).unwrap_or_default();

        // Step [18]: Merge world
        tracing::info!("Step [18]: Merging world updates");
        let world_result = self._merge_world(
            db, project_id,
            parsed.get("world_updates").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]),
            chapter_number,
        ).await?;
        result["changes"]["world"] = serde_json::to_value(&world_result).unwrap_or_default();

        // Step [18a]: Confidence evaluation
        tracing::info!("Step [18a]: Evaluating confidence levels");
        let confidence_result = self._evaluate_phase4_confidence(&result["changes"]);
        result["confidence"] = confidence_result;

        // Step [19]: Enrich card pool
        tracing::info!("Step [19]: Enriching card pool");
        let card_result = self._enrich_card_pool(
            db, project_id,
            parsed.get("card_pool_entries").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]),
            chapter_number,
        ).await?;
        result["changes"]["card_pool"] = serde_json::to_value(&card_result).unwrap_or_default();

        // Build version and summary
        let timestamp = Utc::now().timestamp();
        let version = format!("v4_ch{}_{}", chapter_number, timestamp);
        result["version"] = serde_json::Value::String(version.clone());

        let mut summary_parts: Vec<String> = Vec::new();
        if let Some(created) = char_result.get("created").and_then(|v| v.as_array())
            && !created.is_empty() { summary_parts.push(format!("新增角色 {} 个", created.len())); }
        if let Some(updated) = char_result.get("updated").and_then(|v| v.as_array())
            && !updated.is_empty() { summary_parts.push(format!("更新角色 {} 个", updated.len())); }
        if let Some(sc) = char_result.get("status_changed").and_then(|v| v.as_array())
            && !sc.is_empty() { summary_parts.push(format!("角色状态变更 {} 个", sc.len())); }
        if timeline_result.get("added").and_then(|v| v.as_i64()).unwrap_or(0) > 0 {
            summary_parts.push(format!("新增时间线事件 {} 个", timeline_result["added"]));
        }
        if promise_result.get("created").and_then(|v| v.as_i64()).unwrap_or(0) > 0 {
            summary_parts.push(format!("新增伏笔 {} 个", promise_result["created"]));
        }
        if promise_result.get("advanced").and_then(|v| v.as_i64()).unwrap_or(0) > 0 {
            summary_parts.push(format!("推进伏笔 {} 个", promise_result["advanced"]));
        }
        if world_result.get("created").and_then(|v| v.as_i64()).unwrap_or(0) > 0 {
            summary_parts.push(format!("新增世界设定 {} 个", world_result["created"]));
        }
        if card_result.get("added").and_then(|v| v.as_i64()).unwrap_or(0) > 0 {
            summary_parts.push(format!("新增卡牌 {} 张", card_result["added"]));
        }
        let summary = if summary_parts.is_empty() { "无变更".to_owned() } else { summary_parts.join("、") };
        result["summary"] = serde_json::Value::String(summary.clone());

        // Step [20]: Archive changelog
        tracing::info!("Step [20]: Archiving changelog");
        self._archive_changelog(db, project_id, chapter_id, &version, chapter_number, &result["changes"]).await?;

        // Step [21]: Card retirement check (degraded)
        if let Err(e) = self._check_and_retire_cards_inline(db, project_id, chapter_number).await {
            tracing::error!("Card retire check failed (degraded): {e}");
        }

        tracing::info!("Phase 4 completed: {}", summary);
        Ok(result)
    }

    // ==================================================================
    // §11.5 LLM calling utilities
    // ==================================================================

    /// Unified LLM call + JSON parse (P7-2 fix).
    ///
    /// Calls the LLM with the given messages, extracts and parses JSON from the response.
    /// Returns `default_result` on failure.
    async fn _call_llm_and_parse(
        &self,
        messages: &[ChatMessage],
        default_result: Json,
    ) -> Json {
        match self.llm_client.chat(
            messages,
            &self.api_key,
            &self.model,
            0.3,
            4096,
        ).await {
            Ok(content) => {
                let json_start = content.find('{');
                let json_end = content.rfind('}').map(|i| i + 1).unwrap_or(0);
                if let (Some(start), end) = (json_start, json_end)
                    && end > start {
                        let json_str = &content[start..end];
                        match serde_json::from_str::<Json>(json_str) {
                            Ok(parsed) => return parsed,
                            Err(e) => {
                                tracing::warn!("LLM response JSON parse failed: {e}");
                                return serde_json::json!({"raw_analysis": content});
                            }
                        }
                    }
                serde_json::json!({"raw_analysis": content})
            }
            Err(e) => {
                tracing::error!("LLM extraction call failed: {e}");
                default_result
            }
        }
    }

    /// Call LLM to analyze chapter content (old-style analysis).
    async fn _analyze_chapter_content(
        &self,
        _db: &DatabaseConnection,
        project: &moling_db::entities::project::Model,
        chapter: &moling_db::entities::chapter::Model,
    ) -> AppResult<Json> {
        let prompt = self._build_analysis_prompt(project, chapter);
        let messages = [
            ChatMessage::system("你是一个专业的小说内容分析助手。请分析章节内容，提取关键信息。"),
            ChatMessage::user(prompt),
        ];
        let default_result = serde_json::json!({
            "characters": [],
            "timeline_events": [],
            "plot_promises": [],
            "world_elements": [],
            "summary": "",
            "anchors": {},
        });
        Ok(self._call_llm_and_parse(&messages, default_result).await)
    }

    /// Build the analysis prompt for chapter content.
    fn _build_analysis_prompt(
        &self,
        project: &moling_db::entities::project::Model,
        chapter: &moling_db::entities::chapter::Model,
    ) -> String {
        let content = chapter.content.as_deref().unwrap_or("");
        let genre = &project.genre;
        let synopsis = project.synopsis.as_deref().unwrap_or("");

        format!(
            r#"请分析以下小说章节内容，提取关键信息。

项目信息：
- 标题：{title}
- 作者：{author}
- 类型：{genre}
- 简介：{synopsis}

章节信息：
- 章节标题：{chapter_title}
- 章节编号：{chapter_number}

章节内容：
{content}

请提取以下信息，并以 JSON 格式返回：

1. "characters": 新增或更新的角色列表，每个角色包含：name, role, description, traits, emotion, relationships
2. "timeline_events": 新增的时间线事件列表，每个事件包含：event, description, is_key_event, impact, characters_involved
3. "plot_promises": 新增或更新的伏笔列表，每个伏笔包含：description, type, status, urgency, related_characters
4. "world_elements": 新增或更新的世界观元素列表，每个元素包含：term, description, category, rules
5. "summary": 本章节的内容摘要（200字以内）
6. "anchors": 章节锚点，包含：pov（视点角色）, location（地点）, time（时间）

注意：
- 只提取本章节中首次出现或发生变更的信息
- 如果某类信息没有新增或变更，返回空数组
- 请确保返回的是有效的 JSON 格式
"#,
            title = project.title,
            author = project.author,
            genre = genre,
            synopsis = synopsis,
            chapter_title = chapter.title,
            chapter_number = chapter.chapter_number,
            content = content,
        )
    }

    /// Build the extraction prompt for four-vault changes (§11.5).
    async fn _build_extraction_prompt(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_text: &str,
        card_ids: &[String],
    ) -> String {
        let vault_summary = self._get_vault_summary(db, project_id).await;

        let schema_json = serde_json::json!({
            "character_updates": [
                {"action": "create|update|status_change|remove", "name": "角色名称", "changes": ["变更描述"], "confidence": 0.95}
            ],
            "timeline_updates": [
                {"action": "add|resolve_date|correct", "event": "事件描述", "day": 16, "chapter": 16, "participants": ["角色名"], "importance": "major|minor"}
            ],
            "plot_promise_updates": [
                {"action": "create|advance|redeem|cancel|escalate", "title": "承诺标题", "type": "人物弧光|剧情转折|悬念|关系发展|世界观秘密", "status": "active|advancing|redeemed|abandoned"}
            ],
            "world_updates": [
                {"action": "create|expand|clarify|connect", "name": "条目名称", "category": "geography|history|system|faction|event", "content": "详细内容"}
            ],
            "card_pool_entries": [
                {"type": "剧情|人物|场景|对话", "title": "卡牌标题", "description": "卡牌描述", "rarity": "common|rare|epic", "source_chapter": 16}
            ],
        });
        let card_ids_str = card_ids.join(", ");
        let schema_str = serde_json::to_string_pretty(&schema_json).unwrap_or_default();

        format!(
            r#"你是一个小说分析专家。分析以下新章节的内容，提取它对四库的变更。

当前四库上下文：
{vault_summary}

新章节正文：
{chapter_text}

本次使用的灵感卡 ID：
{card_ids_str}

请输出 JSON，格式如下：

{schema_str}

注意：
- character_updates.changes 字段描述具体的变更内容（如"新增","性格由X变为Y","状态由active变为deceased"等）
- timeline_updates 中 day 字段为绝对时间线天数
- plot_promise_updates.type 的枚举值为：人物弧光、剧情转折、悬念、关系发展、世界观秘密
- world_updates.category 的枚举值为：geography、history、system、faction、event
- card_pool_entries.rarity 的枚举值为：common、rare、epic
- 只提取本章节中首次出现或发生变更的信息
- 如果某类信息没有新增或变更，返回空数组
- 请确保返回的是有效的 JSON 格式，不要包含 markdown 代码块标记"#
        )
    }

    /// Build vault summary string for the extraction prompt.
    async fn _get_vault_summary(&self, db: &DatabaseConnection, project_id: i32) -> String {
        let mut parts: Vec<String> = Vec::new();

        // Characters
        match self.vault_dao.find_characters(db, project_id).await {
            Ok(chars) => {
                if chars.is_empty() {
                    parts.push("人物库：(空)".to_owned());
                } else {
                    let list: Vec<String> = chars.iter()
                        .map(|c| format!("  - ID: {}, 名称: {}", c.id, c.name))
                        .collect();
                    parts.push(format!("人物库：\n{}", list.join("\n")));
                }
            }
            Err(_) => { parts.push("人物库：(加载失败)".to_owned()); }
        }

        // Timeline (last 10)
        match self.vault_dao.find_timeline_events(db, project_id).await {
            Ok(tl) => {
                if tl.is_empty() {
                    parts.push("时间线库：(空)".to_owned());
                } else {
                    let list: Vec<String> = tl.iter().rev().take(10).rev()
                        .map(|t| format!("  - ID: {}, 事件: {}, 章节: ch{}", t.id, t.event, t.chapter_number))
                        .collect();
                    parts.push(format!("时间线库（最近10条）：\n{}", list.join("\n")));
                }
            }
            Err(_) => { parts.push("时间线库：(加载失败)".to_owned()); }
        }

        // Plot promises (last 10)
        match self.vault_dao.find_plot_promises(db, project_id).await {
            Ok(pp) => {
                if pp.is_empty() {
                    parts.push("剧情承诺库：(空)".to_owned());
                } else {
                    let list: Vec<String> = pp.iter().rev().take(10).rev()
                        .map(|p| format!("  - ID: {}, 描述: {}, 状态: {}", p.id, &p.description[..p.description.len().min(50)], p.status))
                        .collect();
                    parts.push(format!("剧情承诺库（最近10条）：\n{}", list.join("\n")));
                }
            }
            Err(_) => { parts.push("剧情承诺库：(加载失败)".to_owned()); }
        }

        // World (last 10)
        match self.vault_dao.find_world_entries(db, project_id).await {
            Ok(w) => {
                if w.is_empty() {
                    parts.push("世界观库：(空)".to_owned());
                } else {
                    let list: Vec<String> = w.iter().rev().take(10).rev()
                        .map(|e| format!("  - ID: {}, 名称: {}, 类别: {}", e.id, e.name, e.category))
                        .collect();
                    parts.push(format!("世界观库（最近10条）：\n{}", list.join("\n")));
                }
            }
            Err(_) => { parts.push("世界观库：(加载失败)".to_owned()); }
        }

        parts.join("\n")
    }

    /// Call LLM to extract four-vault changes (§11.5).
    async fn _call_extraction_llm(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_text: &str,
        card_ids: &[String],
    ) -> Json {
        let prompt = self._build_extraction_prompt(db, project_id, chapter_text, card_ids).await;
        let messages = [
            ChatMessage::system("你是一个小说分析专家。分析以下新章节的内容，提取它对四库的变更。请严格按照 JSON 格式输出，不要包含 markdown 代码块标记或其他格式。你的回答应当使用中文。"),
            ChatMessage::user(prompt),
        ];
        self._call_llm_and_parse(&messages, Self::_empty_extraction_result()).await
    }

    /// Return an empty extraction result.
    fn _empty_extraction_result() -> Json {
        serde_json::json!({
            "character_updates": [],
            "timeline_updates": [],
            "plot_promise_updates": [],
            "world_updates": [],
            "card_pool_entries": [],
        })
    }

    // ==================================================================
    // Dynamic Layer update
    // ==================================================================

    /// Update the dynamic layer for a chapter based on analysis results.
    async fn _update_dynamic_layer(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: &str,
        analysis: &Json,
    ) -> AppResult<()> {
        let existing = self.dynamic_layer_dao.find_by_chapter(db, chapter_id).await?;

        if let Some(dl) = existing {
            // Update existing
            let mut active = dl.clone().into_active_model();

            if let Some(summary) = analysis.get("summary").and_then(|v| v.as_str()) {
                active.summary = Set(Some(summary.to_owned()));
            }

            let anchors = analysis.get("anchors");
            if let Some(pov) = anchors.and_then(|a| a.get("pov")).and_then(|v| v.as_str()) {
                active.anchor_pov = Set(Some(pov.to_owned()));
            }
            if let Some(loc) = anchors.and_then(|a| a.get("location")).and_then(|v| v.as_str()) {
                active.anchor_location = Set(Some(loc.to_owned()));
            }
            if let Some(time) = anchors.and_then(|a| a.get("time")).and_then(|v| v.as_str()) {
                active.anchor_time = Set(Some(time.to_owned()));
            }

            // Unresolved hooks: collect dormant/active/advancing promises
            let promises = analysis.get("plot_promises").and_then(|v| v.as_array());
            let mut unresolved: Vec<Json> = Vec::new();
            if let Some(promises) = promises {
                for p in promises {
                    let status = p.get("status").and_then(|v| v.as_str()).unwrap_or("dormant");
                    if matches!(status, "dormant" | "active" | "advancing") {
                        unresolved.push(serde_json::json!({
                            "description": p.get("description").unwrap_or(&Json::Null),
                            "type": p.get("type").unwrap_or(&Json::String("mystery".into())),
                            "status": status,
                            "urgency": p.get("urgency").unwrap_or(&serde_json::Value::Number(5.into())),
                            "related_characters": p.get("related_characters").unwrap_or(&Json::Null),
                        }));
                    }
                }
            }
            // Merge with existing hooks (dedup)
            let existing_hooks: Vec<Json> = dl.unresolved_hooks
                .as_ref()
                .and_then(|v| v.as_array()).cloned()
                .unwrap_or_default();
            let existing_descs: std::collections::HashSet<String> = existing_hooks.iter()
                .filter_map(|h| h.get("description").and_then(|v| v.as_str()).map(|s| s.to_owned()))
                .collect();
            let mut merged = existing_hooks.clone();
            for hook in &unresolved {
                if let Some(desc) = hook.get("description").and_then(|v| v.as_str())
                    && !existing_descs.contains(desc) {
                        merged.push(hook.clone());
                    }
            }
            // Remove resolved/abandoned hooks
            let active_descs: std::collections::HashSet<String> = promises.map(|ps| {
                ps.iter().filter_map(|p| {
                    let status = p.get("status").and_then(|v| v.as_str()).unwrap_or("");
                    if !matches!(status, "resolved" | "abandoned") {
                        p.get("description").and_then(|v| v.as_str()).map(|s| s.to_owned())
                    } else {
                        None
                    }
                }).collect()
            }).unwrap_or_default();
            merged.retain(|h| {
                h.get("description").and_then(|v| v.as_str())
                    .map(|d| active_descs.contains(d) || !promises.map(|ps| {
                        ps.iter().any(|p| p.get("description").and_then(|v| v.as_str()) == Some(d))
                    }).unwrap_or(false))
                    .unwrap_or(true)
            });
            merged.truncate(20);
            active.unresolved_hooks = Set(Some(Json::Array(merged)));

            // Recent changes (keep last 3)
            let mut recent: Vec<Json> = dl.recent_changes
                .as_ref()
                .and_then(|v| v.as_array()).cloned()
                .unwrap_or_default();
            recent.push(serde_json::json!({
                "chapter_id": chapter_id,
                "timestamp": Utc::now().to_rfc3339(),
                "changes": analysis,
            }));
            recent.truncate(3);
            active.recent_changes = Set(Some(Json::Array(recent)));

            self.dynamic_layer_dao.update(db, active).await?;
        } else {
            // Create new dynamic layer
            let model = dynamic_layer::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                chapter_id: Set(chapter_id.to_owned()),
                summary: Set(analysis.get("summary").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                anchor_pov: Set(analysis.get("anchors").and_then(|a| a.get("pov")).and_then(|v| v.as_str()).map(|s| s.to_owned())),
                anchor_location: Set(analysis.get("anchors").and_then(|a| a.get("location")).and_then(|v| v.as_str()).map(|s| s.to_owned())),
                anchor_time: Set(analysis.get("anchors").and_then(|a| a.get("time")).and_then(|v| v.as_str()).map(|s| s.to_owned())),
                ..Default::default()
            };
            self.dynamic_layer_dao.create(db, model).await?;
        }

        Ok(())
    }

    // ==================================================================
    // Vault entity update dispatcher
    // ==================================================================

    /// Dispatch vault entity updates across all four vaults.
    async fn _update_vault_entities(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_number: i32,
        analysis: &Json,
    ) -> AppResult<()> {
        // 1. Characters
        if let Some(chars) = analysis.get("characters").and_then(|v| v.as_array()) {
            for char_data in chars {
                self._update_or_create_character(db, project_id, char_data).await?;
            }
        }

        // 2. Timeline events
        if let Some(events) = analysis.get("timeline_events").and_then(|v| v.as_array()) {
            for event_data in events {
                self._create_timeline_event(db, project_id, event_data).await?;
            }
        }

        // 3. Plot promises
        if let Some(promises) = analysis.get("plot_promises").and_then(|v| v.as_array()) {
            for promise_data in promises {
                self._update_or_create_plot_promise(db, project_id, promise_data, chapter_number).await?;
            }
        }

        // 4. World elements
        if let Some(worlds) = analysis.get("world_elements").and_then(|v| v.as_array()) {
            for world_data in worlds {
                self._update_or_create_world_element(db, project_id, world_data).await?;
            }
        }

        Ok(())
    }

    /// Update or create a character from analysis data.
    async fn _update_or_create_character(
        &self, db: &DatabaseConnection, project_id: i32, char_data: &Json,
    ) -> AppResult<()> {
        let name = char_data.get("name").and_then(|v| v.as_str()).unwrap_or("");
        if name.is_empty() { return Ok(()); }

        let existing = self.vault_dao.find_character_by_name(db, project_id, name).await?;

        if let Some(c) = existing {
            let mut active = c.clone().into_active_model();
            if let Some(desc) = char_data.get("description").and_then(|v| v.as_str()) {
                active.description = Set(Some(desc.to_owned()));
            }
            if let Some(traits) = char_data.get("traits") {
                active.traits = Set(Some(traits.clone()));
            }
            if let Some(emotion) = char_data.get("emotion").and_then(|v| v.as_str()) {
                active.emotion = Set(Some(emotion.to_owned()));
            }
            if let Some(rels) = char_data.get("relationships") {
                active.relationships = Set(Some(rels.clone()));
            }
            active.chapter_count = Set(c.chapter_count + 1);
            self.vault_dao.update_character(db, active).await?;
        } else {
            let model = vault_character::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                name: Set(name.to_owned()),
                role: Set(char_data.get("role").and_then(|v| v.as_str()).unwrap_or("neutral").to_owned()),
                description: Set(char_data.get("description").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                traits: Set(char_data.get("traits").cloned()),
                emotion: Set(char_data.get("emotion").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                relationships: Set(char_data.get("relationships").cloned()),
                chapter_count: Set(1),
                ..Default::default()
            };
            self.vault_dao.create_character(db, model).await?;
        }
        Ok(())
    }

    /// Create a timeline event from analysis data.
    async fn _create_timeline_event(
        &self, db: &DatabaseConnection, project_id: i32, event_data: &Json,
    ) -> AppResult<()> {
        let event = event_data.get("event").and_then(|v| v.as_str()).unwrap_or("");
        if event.is_empty() { return Ok(()); }

        let model = vault_timeline::ActiveModel {
            id: Set(Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            event: Set(event.to_owned()),
            description: Set(event_data.get("description").and_then(|v| v.as_str()).unwrap_or(event).to_owned()),
            is_key_event: Set(event_data.get("is_key_event").and_then(|v| v.as_bool()).unwrap_or(false)),
            impact: Set(event_data.get("impact").and_then(|v| v.as_str()).map(|s| s.to_owned())),
            characters_involved: Set(event_data.get("characters_involved").cloned()),
            chapter_number: Set(0),
            ..Default::default()
        };
        self.vault_dao.create_timeline(db, model).await?;
        Ok(())
    }

    /// Update or create a plot promise from analysis data.
    async fn _update_or_create_plot_promise(
        &self, db: &DatabaseConnection, project_id: i32, promise_data: &Json, chapter_number: i32,
    ) -> AppResult<()> {
        let description = promise_data.get("description").and_then(|v| v.as_str()).unwrap_or("");
        if description.is_empty() { return Ok(()); }

        let promise_type = promise_data.get("type").and_then(|v| v.as_str()).unwrap_or("mystery");
        let related_chars = promise_data.get("related_characters").and_then(|v| v.as_array());

        // Strategy 1: exact description match (first 80 chars)
        let fragment = &description[..description.len().min(80)];
        let mut existing = self.vault_dao.find_promise_by_description(db, project_id, fragment).await?;

        // Strategy 2: type + character match
        if existing.is_none()
            && let Some(chars) = related_chars {
                let statuses = ["dormant".to_owned(), "active".to_owned(), "advancing".to_owned()];
                for char_val in chars {
                    if let Some(char_name) = char_val.as_str()
                        && let Some(p) = self.vault_dao.find_promise_by_type_and_char(
                            db, project_id, promise_type, char_name, &statuses,
                        ).await? {
                            existing = Some(p);
                            break;
                        }
                }
            }

        if let Some(p) = existing {
            let mut active = p.into_active_model();
            if let Some(status) = promise_data.get("status").and_then(|v| v.as_str()) {
                active.status = Set(status.to_owned());
            }
            if let Some(urgency) = promise_data.get("urgency").and_then(|v| v.as_i64()) {
                active.urgency = Set(urgency as i32);
            }
            self.vault_dao.update_plot_promise(db, active).await?;
        } else {
            let model = vault_plot_promise::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                description: Set(description.to_owned()),
                r#type: Set(Self::_map_promise_type(promise_type).to_owned()),
                status: Set(promise_data.get("status").and_then(|v| v.as_str()).unwrap_or("dormant").to_owned()),
                urgency: Set(promise_data.get("urgency").and_then(|v| v.as_i64()).unwrap_or(5) as i32),
                related_characters: Set(promise_data.get("related_characters").cloned()),
                planted_chapter: Set(Some(chapter_number)),
                advancement_log: Set(Some(serde_json::json!([{
                    "chapter": chapter_number,
                    "event": "created",
                    "timestamp": Utc::now().to_rfc3339(),
                }]))),
                ..Default::default()
            };
            self.vault_dao.create_plot_promise(db, model).await?;
        }
        Ok(())
    }

    /// Update or create a world element from analysis data.
    async fn _update_or_create_world_element(
        &self, db: &DatabaseConnection, project_id: i32, world_data: &Json,
    ) -> AppResult<()> {
        let term = world_data.get("term").and_then(|v| v.as_str()).unwrap_or("");
        if term.is_empty() { return Ok(()); }

        let existing = self.vault_dao.find_world_by_term(db, project_id, term).await?;

        if let Some(w) = existing {
            let mut active = w.into_active_model();
            if let Some(desc) = world_data.get("description").and_then(|v| v.as_str()) {
                active.description = Set(desc.to_owned());
            }
            if let Some(rules) = world_data.get("rules") {
                active.constraint = Set(rules.as_str().map(|s| s.to_owned()));
            }
            self.vault_dao.update_world(db, active).await?;
        } else {
            let model = vault_world::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                name: Set(term.to_owned()),
                description: Set(world_data.get("description").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
                category: Set(world_data.get("category").and_then(|v| v.as_str()).unwrap_or("concept").to_owned()),
                reference_chapters: Set(Some(Json::Array(vec![]))),
                ..Default::default()
            };
            self.vault_dao.create_world(db, model).await?;
        }
        Ok(())
    }

    /// Update card pool weights based on analysis.
    async fn _update_card_pool(
        &self, db: &DatabaseConnection, project_id: i32, analysis: &Json,
    ) -> AppResult<()> {
        // Create new cards from characters and promises
        let mut new_card_count = 0;

        if let Some(chars) = analysis.get("characters").and_then(|v| v.as_array()) {
            for char_data in chars {
                let name = char_data.get("name").and_then(|v| v.as_str()).unwrap_or("");
                if name.is_empty() { continue; }
                let model = card_pool::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(format!("{}的故事", name)),
                    description: Set(format!("探索{}的更多故事", name)),
                    rarity: Set("common".to_owned()),
                    direction_type: Set("interesting".to_owned()),
                    direction_text: Set(format!("围绕{}展开情节", name)),
                    is_active: Set(true),
                    status: Set("active".to_owned()),
                    draw_count: Set(0),
                    source_label: Set("Phase4".to_owned()),
                    ..Default::default()
                };
                if let Err(e) = self.card_dao.create_card(db, model).await {
                    tracing::warn!("Failed to create character card: {e}");
                } else {
                    new_card_count += 1;
                }
            }
        }

        if let Some(promises) = analysis.get("plot_promises").and_then(|v| v.as_array()) {
            for promise_data in promises {
                let desc = promise_data.get("description").and_then(|v| v.as_str()).unwrap_or("");
                if desc.is_empty() { continue; }
                let title = &desc[..desc.len().min(20)];
                let model = card_pool::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    name: Set(format!("伏笔：{}", title)),
                    description: Set(format!("回收或推进伏笔：{}", desc)),
                    rarity: Set("rare".to_owned()),
                    direction_type: Set("interesting".to_owned()),
                    direction_text: Set(format!("处理伏笔：{}", &desc[..desc.len().min(50)])),
                    is_active: Set(true),
                    status: Set("active".to_owned()),
                    draw_count: Set(0),
                    source_label: Set("Phase4".to_owned()),
                    ..Default::default()
                };
                if let Err(e) = self.card_dao.create_card(db, model).await {
                    tracing::warn!("Failed to create promise card: {e}");
                } else {
                    new_card_count += 1;
                }
            }
        }

        tracing::info!(new_card_count, "Card pool updated from Phase 4 analysis");
        Ok(())
    }

    // ==================================================================
    // §11.7 [15]: Character merge with fuzzy matching
    // ==================================================================

    async fn _merge_characters(
        &self, db: &DatabaseConnection, project_id: i32,
        updates: &[Json], chapter_number: i32,
    ) -> AppResult<Json> {
        let mut created: Vec<Json> = Vec::new();
        let mut updated: Vec<Json> = Vec::new();
        let mut status_changed: Vec<Json> = Vec::new();

        let all_chars = self.vault_dao.find_characters(db, project_id).await?;

        for update in updates {
            let action = update.get("action").and_then(|v| v.as_str()).unwrap_or("");
            let name = update.get("name").and_then(|v| v.as_str()).unwrap_or("");
            let confidence = update.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.8);
            let changes = update.get("changes").and_then(|v| v.as_array());

            if name.is_empty() { continue; }

            match action {
                "create" => {
                    // Fuzzy match: edit distance < threshold → update existing
                    let mut matched: Option<&VaultCharacterModel> = None;
                    let mut matched_name = "";
                    let mut best_dist = CHARACTER_FUZZY_THRESHOLD;

                    for existing in &all_chars {
                        let dist = calc_edit_distance(name, &existing.name);
                        if dist < best_dist {
                            best_dist = dist;
                            matched = Some(existing);
                            matched_name = &existing.name;
                        }
                    }

                    if let Some(mc) = matched {
                        // Fuzzy match success → update
                        let mut update_fields = Self::_extract_change_fields(changes);
                        update_fields.insert("chapter_count".to_owned(), Json::Number(((mc.chapter_count + 1) as i64).into()));

                        let mut active = mc.clone().into_active_model();
                        Self::_apply_character_updates(&mut active, &update_fields);
                        self.vault_dao.update_character(db, active).await?;

                        updated.push(serde_json::json!({
                            "id": mc.id,
                            "name": matched_name,
                            "changes": changes,
                        }));
                        tracing::info!("Character fuzzy matched: '{}' → '{}' (edit_distance={})", name, matched_name, best_dist);
                    } else {
                        // Create new
                        let model = vault_character::ActiveModel {
                            id: Set(Uuid::new_v4().to_string()),
                            project_id: Set(project_id),
                            name: Set(name.to_owned()),
                            role: Set(Self::_extract_change(changes, "role", "neutral").to_owned()),
                            faction: Set(Self::_extract_change_opt(changes, "faction")),
                            location: Set(Self::_extract_change_opt(changes, "location")),
                            current_state: Set(Self::_extract_change_opt(changes, "current_state")),
                            motivation: Set(Self::_extract_change_opt(changes, "motivation")),
                            description: Set(Self::_extract_change_opt(changes, "description")),
                            personality: Set(Self::_extract_change_opt(changes, "personality")),
                            confidence: Set(Some(confidence)),
                            chapter_count: Set(1),
                            chapter_hist: Set(if chapter_number > 0 { Some(Json::Array(vec![Json::Number(chapter_number.into())])) } else { None }),
                            ..Default::default()
                        };
                        let new_char = self.vault_dao.create_character(db, model).await?;
                        created.push(serde_json::json!({"id": new_char.id, "name": name}));
                        tracing::info!("Character created: {}", name);
                    }
                }
                "update" => {
                    let existing = all_chars.iter().find(|c| c.name == name);
                    if let Some(ec) = existing {
                        let mut update_fields = Self::_extract_change_fields(changes);
                        update_fields.insert("chapter_count".to_owned(), Json::Number(((ec.chapter_count + 1) as i64).into()));

                        let mut active = ec.clone().into_active_model();
                        Self::_apply_character_updates(&mut active, &update_fields);
                        self.vault_dao.update_character(db, active).await?;

                        updated.push(serde_json::json!({
                            "id": ec.id, "name": name, "changes": changes,
                        }));
                        tracing::info!("Character updated: {}", name);
                    }
                }
                "status_change" => {
                    let existing = all_chars.iter().find(|c| c.name == name);
                    if let Some(ec) = existing {
                        let old_status = ec.status.clone();
                        let new_status = Self::_extract_change(changes, "status", "inactive");

                        let mut state_machine = ec.state_machine.clone().unwrap_or(Json::Object(Default::default()));
                        let mut history: Vec<Json> = state_machine.get("history")
                            .and_then(|v| v.as_array()).cloned().unwrap_or_default();
                        history.push(serde_json::json!({
                            "from": old_status,
                            "to": new_status,
                            "chapter": chapter_number,
                            "reason": changes.map(|c| serde_json::to_string(c).unwrap_or_default()).unwrap_or_default(),
                        }));
                        if let Some(obj) = state_machine.as_object_mut() {
                            obj.insert("history".to_owned(), Json::Array(history));
                            obj.insert("current".to_owned(), Json::String(new_status.to_owned()));
                        }

                        let mut active = ec.clone().into_active_model();
                        active.status = Set(new_status.to_owned());
                        active.state_machine = Set(Some(state_machine));
                        self.vault_dao.update_character(db, active).await?;

                        status_changed.push(serde_json::json!({
                            "id": ec.id, "name": name, "from": old_status, "to": new_status,
                        }));
                        tracing::info!("Character status changed: {}: {} → {}", name, old_status, new_status);
                    }
                }
                "remove" => {
                    let existing = all_chars.iter().find(|c| c.name == name);
                    if let Some(ec) = existing {
                        let old_status = ec.status.clone();
                        let mut active = ec.clone().into_active_model();
                        active.status = Set("deceased".to_owned());
                        self.vault_dao.update_character(db, active).await?;
                        status_changed.push(serde_json::json!({
                            "id": ec.id, "name": name, "from": old_status, "to": "deceased",
                        }));
                        tracing::info!("Character marked as deceased: {}", name);
                    }
                }
                _ => {}
            }
        }

        Ok(serde_json::json!({
            "created": created,
            "updated": updated,
            "status_changed": status_changed,
        }))
    }

    /// Extract a single change value from a changes array.
    fn _extract_change(changes: Option<&Vec<Json>>, key: &str, default: &str) -> String {
        if let Some(arr) = changes {
            for change in arr {
                if let Some(obj) = change.as_object()
                    && let Some(val) = obj.get(key).and_then(|v| v.as_str()) {
                        return val.to_owned();
                    }
                if let Some(s) = change.as_str()
                    && let Some(stripped) = s.strip_prefix(&format!("{}:", key)) {
                        return stripped.trim().to_owned();
                    }
            }
        }
        default.to_owned()
    }

    fn _extract_change_opt(changes: Option<&Vec<Json>>, key: &str) -> Option<String> {
        let val = Self::_extract_change(changes, key, "");
        if val.is_empty() { None } else { Some(val) }
    }

    /// Extract all change fields as a JSON map.
    fn _extract_change_fields(changes: Option<&Vec<Json>>) -> serde_json::Map<String, Json> {
        let mut map = serde_json::Map::new();
        if let Some(arr) = changes {
            for change in arr {
                if let Some(obj) = change.as_object() {
                    for (k, v) in obj {
                        map.insert(k.clone(), v.clone());
                    }
                } else if let Some(s) = change.as_str()
                    && let Some(colon) = s.find(':') {
                        let key = s[..colon].trim().to_owned();
                        let val = s[colon + 1..].trim().to_owned();
                        map.insert(key, Json::String(val));
                    }
            }
        }
        map
    }

    /// Apply extracted change fields to a character active model.
    fn _apply_character_updates(
        active: &mut vault_character::ActiveModel,
        fields: &serde_json::Map<String, Json>,
    ) {
        let string_fields: [&str; 12] = ["role", "faction", "location", "current_state", "motivation",
            "description", "personality", "emotion", "status", "background", "appearance", "name"];
        for key in &string_fields {
            if let Some(v) = fields.get(*key).and_then(|v| v.as_str()) {
                match *key {
                    "role" => active.role = Set(v.to_owned()),
                    "faction" => active.faction = Set(Some(v.to_owned())),
                    "location" => active.location = Set(Some(v.to_owned())),
                    "current_state" => active.current_state = Set(Some(v.to_owned())),
                    "motivation" => active.motivation = Set(Some(v.to_owned())),
                    "description" => active.description = Set(Some(v.to_owned())),
                    "personality" => active.personality = Set(Some(v.to_owned())),
                    "emotion" => active.emotion = Set(Some(v.to_owned())),
                    "status" => active.status = Set(v.to_owned()),
                    "background" => active.background = Set(Some(v.to_owned())),
                    "appearance" => active.appearance = Set(Some(v.to_owned())),
                    "name" => active.name = Set(v.to_owned()),
                    _ => {}
                }
            }
        }
        if let Some(v) = fields.get("traits") { active.traits = Set(Some(v.clone())); }
        if let Some(v) = fields.get("relationships") { active.relationships = Set(Some(v.clone())); }
        if let Some(v) = fields.get("state_machine") { active.state_machine = Set(Some(v.clone())); }
        if let Some(v) = fields.get("chapter_count").and_then(|v| v.as_i64()) { active.chapter_count = Set(v as i32); }
        if let Some(v) = fields.get("confidence").and_then(|v| v.as_f64()) { active.confidence = Set(Some(v)); }
    }

    /// Map Chinese promise type to enum value.
    fn _map_promise_type(ptype: &str) -> &str {
        match ptype {
            "人物弧光" => "arc",
            "剧情转折" => "subplot",
            "悬念" => "mystery",
            "关系发展" => "promise",
            "世界观秘密" => "foreshadowing",
            _ => "mystery",
        }
    }

    // ==================================================================
    // §11.7 [16]: Timeline merge
    // ==================================================================

    async fn _merge_timeline(
        &self, db: &DatabaseConnection, project_id: i32,
        updates: &[Json], _chapter_id: &str, chapter_number: i32,
    ) -> AppResult<Json> {
        let mut added: i64 = 0;

        for update in updates {
            let action = update.get("action").and_then(|v| v.as_str()).unwrap_or("add");

            if action == "add" {
                let event = update.get("event").and_then(|v| v.as_str()).unwrap_or("");
                if event.is_empty() { continue; }

                let model = vault_timeline::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    event: Set(event.to_owned()),
                    description: Set(update.get("description").and_then(|v| v.as_str()).unwrap_or(event).to_owned()),
                    day: Set(update.get("day").and_then(|v| v.as_i64()).map(|v| v as i32)),
                    chapter_number: Set(chapter_number),
                    source_chapter: Set(Some(chapter_number)),
                    importance: Set(update.get("importance").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                    characters_involved: Set(update.get("participants").cloned()),
                    is_key_event: Set(update.get("importance").and_then(|v| v.as_str()) == Some("major")),
                    ..Default::default()
                };
                self.vault_dao.create_timeline(db, model).await?;
                added += 1;
                tracing::info!("Timeline event added: {}", &event[..event.len().min(50)]);
            } else if action == "resolve_date" || action == "correct" {
                let event_name = update.get("event").and_then(|v| v.as_str()).unwrap_or("");
                if event_name.is_empty() { continue; }

                if let Ok(events) = self.vault_dao.find_timeline_events(db, project_id).await
                    && let Some(target) = events.iter().find(|e| e.event == event_name) {
                        let mut active = target.clone().into_active_model();
                        if let Some(day) = update.get("day").and_then(|v| v.as_i64()) {
                            active.day = Set(Some(day as i32));
                        }
                        if action == "correct"
                            && let Some(desc) = update.get("description").and_then(|v| v.as_str()) {
                                active.description = Set(desc.to_owned());
                            }
                        if let Err(e) = self.vault_dao.update_timeline(db, active).await {
                            tracing::warn!("Failed to {} timeline event '{}': {}", action, event_name, e);
                        }
                    }
            }
        }

        Ok(serde_json::json!({"added": added}))
    }

    // ==================================================================
    // §11.7 [17]: Plot promise merge
    // ==================================================================

    async fn _merge_plot_promises(
        &self, db: &DatabaseConnection, project_id: i32,
        updates: &[Json], chapter_number: i32,
    ) -> AppResult<Json> {
        let mut created: i64 = 0;
        let mut advanced: i64 = 0;
        let mut redeemed: i64 = 0;

        for update in updates {
            let action = update.get("action").and_then(|v| v.as_str()).unwrap_or("");
            let title = update.get("title").and_then(|v| v.as_str()).unwrap_or("");

            match action {
                "create" => {
                    if title.is_empty() { continue; }
                    let model = vault_plot_promise::ActiveModel {
                        id: Set(Uuid::new_v4().to_string()),
                        project_id: Set(project_id),
                        title: Set(Some(title.to_owned())),
                        description: Set(title.to_owned()),
                        r#type: Set(Self::_map_promise_type(update.get("type").and_then(|v| v.as_str()).unwrap_or("悬念")).to_owned()),
                        status: Set("active".to_owned()),
                        urgency: Set(5),
                        planted_chapter: Set(Some(chapter_number)),
                        advancement_log: Set(Some(serde_json::json!([{
                            "chapter": chapter_number,
                            "event": "created",
                            "timestamp": Utc::now().to_rfc3339(),
                        }]))),
                        ..Default::default()
                    };
                    self.vault_dao.create_plot_promise(db, model).await?;
                    created += 1;
                    tracing::info!("Plot promise created: {}", title);
                }
                "advance" | "redeem" | "cancel" => {
                    if title.is_empty() { continue; }
                    if let Ok(promises) = self.vault_dao.find_plot_promises(db, project_id).await {
                        let target = promises.iter().find(|p| {
                            p.title.as_deref() == Some(title) ||
                            (p.description.contains(title))
                        });
                        if let Some(t) = target {
                            let event_name = match action {
                                "advance" => "advanced",
                                "redeem" => "redeemed",
                                _ => "abandoned",
                            };
                            let new_status = match action {
                                "advance" => "advancing",
                                "redeem" => "resolved",
                                _ => "abandoned",
                            };

                            let mut log = t.advancement_log.clone().unwrap_or(Json::Array(vec![]));
                            if let Some(arr) = log.as_array_mut() {
                                arr.push(serde_json::json!({
                                    "chapter": chapter_number,
                                    "event": event_name,
                                    "timestamp": Utc::now().to_rfc3339(),
                                }));
                            }

                            let new_urgency = if action == "advance" {
                                std::cmp::min(10, t.urgency + 1)
                            } else {
                                t.urgency
                            };

                            let mut active = t.clone().into_active_model();
                            active.status = Set(new_status.to_owned());
                            active.advancement_log = Set(Some(log));
                            active.urgency = Set(new_urgency);
                            self.vault_dao.update_plot_promise(db, active).await?;

                            match action {
                                "advance" => advanced += 1,
                                "redeem" => redeemed += 1,
                                _ => {}
                            }
                            tracing::info!("Plot promise {}: {}", action, title);
                        }
                    }
                }
                _ => {}
            }
        }

        Ok(serde_json::json!({
            "created": created,
            "advanced": advanced,
            "redeemed": redeemed,
        }))
    }

    // ==================================================================
    // §11.7 [18]: World merge
    // ==================================================================

    async fn _merge_world(
        &self, db: &DatabaseConnection, project_id: i32,
        updates: &[Json], chapter_number: i32,
    ) -> AppResult<Json> {
        let mut created: i64 = 0;
        let mut expanded: i64 = 0;

        for update in updates {
            let action = update.get("action").and_then(|v| v.as_str()).unwrap_or("");
            let name = update.get("name").and_then(|v| v.as_str()).unwrap_or("");
            if name.is_empty() { continue; }

            match action {
                "create" => {
                    let model = vault_world::ActiveModel {
                        id: Set(Uuid::new_v4().to_string()),
                        project_id: Set(project_id),
                        name: Set(name.to_owned()),
                        description: Set(update.get("content").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
                        category: Set(update.get("category").and_then(|v| v.as_str()).unwrap_or("other").to_owned()),
                        source_chapter: Set(Some(chapter_number)),
                        reference_chapters: Set(if chapter_number > 0 { Some(Json::Array(vec![Json::Number(chapter_number.into())])) } else { None }),
                        ..Default::default()
                    };
                    self.vault_dao.create_world(db, model).await?;
                    created += 1;
                    tracing::info!("World entry created: {}", name);
                }
                "expand" | "clarify" => {
                    if let Ok(entries) = self.vault_dao.find_world_entries(db, project_id).await
                        && let Some(target) = entries.iter().find(|e| e.name == name) {
                            let mut refs: Vec<Json> = target.reference_chapters
                                .as_ref().and_then(|v| v.as_array()).cloned()
                                .unwrap_or_default();
                            if chapter_number > 0 && !refs.iter().any(|r| r.as_i64() == Some(chapter_number as i64)) {
                                refs.push(Json::Number(chapter_number.into()));
                            }

                            let new_content = update.get("content").and_then(|v| v.as_str()).unwrap_or("");
                            let new_desc = if new_content.is_empty() {
                                target.description.clone()
                            } else {
                                format!("{}\n\n[更新] {}", target.description, new_content)
                            };

                            let mut active = target.clone().into_active_model();
                            active.reference_chapters = Set(Some(Json::Array(refs)));
                            active.description = Set(new_desc);
                            self.vault_dao.update_world(db, active).await?;
                            expanded += 1;
                            tracing::info!("World entry {}: {}", action, name);
                        }
                }
                "connect" => {
                    let content = update.get("content").and_then(|v| v.as_str()).unwrap_or("");
                    if content.is_empty() { continue; }
                    if let Ok(entries) = self.vault_dao.find_world_entries(db, project_id).await
                        && let Some(target) = entries.iter().find(|e| e.name == name) {
                            let mut related: Vec<Json> = target.related_entities
                                .as_ref().and_then(|v| v.as_array()).cloned()
                                .unwrap_or_default();
                            if !related.iter().any(|r| r.as_str() == Some(content)) {
                                related.push(Json::String(content.to_owned()));
                            }
                            let mut active = target.clone().into_active_model();
                            active.related_entities = Set(Some(Json::Array(related)));
                            self.vault_dao.update_world(db, active).await?;
                            expanded += 1;
                            tracing::info!("World entry connected: {} <-> {}", name, content);
                        }
                }
                _ => {}
            }
        }

        Ok(serde_json::json!({"created": created, "expanded": expanded}))
    }

    // ==================================================================
    // §11.7 [19]: Card pool enrichment
    // ==================================================================

    async fn _enrich_card_pool(
        &self, db: &DatabaseConnection, project_id: i32,
        entries: &[Json], chapter_number: i32,
    ) -> AppResult<Json> {
        let mut added: i64 = 0;

        // Get existing titles for dedup
        let existing_titles: std::collections::HashSet<String> = match self.card_dao.list_active_by_project(db, project_id).await {
            Ok(cards) => cards.into_iter().map(|c| c.name).collect(),
            Err(e) => {
                tracing::error!("Card dedup fetch failed: {e}");
                std::collections::HashSet::new()
            }
        };

        for entry in entries {
            let title = entry.get("title").and_then(|v| v.as_str()).unwrap_or("");
            if title.is_empty() || existing_titles.contains(title) { continue; }

            let rarity = entry.get("rarity").and_then(|v| v.as_str()).unwrap_or("common");
            let rarity_weight: i32 = match rarity {
                "epic" => 3,
                "rare" => 2,
                _ => 1,
            };

            let model = card_pool::ActiveModel {
                id: Set(Uuid::new_v4().to_string()),
                project_id: Set(project_id),
                name: Set(title.to_owned()),
                description: Set(entry.get("description").and_then(|v| v.as_str()).unwrap_or("").to_owned()),
                rarity: Set(rarity.to_owned()),
                direction_type: Set("interesting".to_owned()),
                direction_text: Set(entry.get("description").and_then(|v| v.as_str()).unwrap_or(title).to_owned()),
                source_label: Set("Phase4".to_owned()),
                source_chapter: Set(Some(chapter_number)),
                freshness_chapter: Set(Some(chapter_number)),
                rarity_weight: Set(Some(rarity_weight)),
                r#type: Set(entry.get("type").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                is_active: Set(true),
                status: Set("active".to_owned()),
                tags: Set(Some(serde_json::json!(["phase4", entry.get("type").unwrap_or(&Json::String("剧情".into())), rarity]))),
                ..Default::default()
            };

            if let Err(e) = self.card_dao.create_card(db, model).await {
                tracing::warn!("Failed to add card '{}': {}", title, e);
            } else {
                added += 1;
                tracing::info!("Card pool entry added: {} (rarity={})", title, rarity);
            }
        }

        tracing::info!("Card pool enriched: {} new cards added", added);
        Ok(serde_json::json!({"added": added}))
    }

    // ==================================================================
    // §11.7 [18a]: Confidence evaluation (P1-4)
    // ==================================================================

    fn _evaluate_phase4_confidence(&self, changes: &Json) -> Json {
        let mut items_requiring_review: Vec<Json> = Vec::new();
        let mut level_counts: std::collections::HashMap<String, i64> = [
            ("high".to_owned(), 0),
            ("medium".to_owned(), 0),
            ("low".to_owned(), 0),
            ("reject".to_owned(), 0),
        ].into();

        // Evaluate character changes
        if let Some(chars) = changes.get("characters") {
            for key in &["created", "updated", "status_changed"] {
                if let Some(items) = chars.get(key).and_then(|v| v.as_array()) {
                    for item in items {
                        let confidence = item.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.8);
                        let level = evaluate_confidence(confidence);
                        *level_counts.entry(level.to_owned()).or_insert(0) += 1;
                        if level == "low" {
                            items_requiring_review.push(serde_json::json!({
                                "type": format!("character_{}", key),
                                "name": item.get("name"),
                                "id": item.get("id"),
                                "confidence": confidence,
                                "confidence_level": level,
                            }));
                        }
                    }
                }
            }
        }

        // Evaluate timeline changes (default 0.7)
        if let Some(added) = changes.get("timeline").and_then(|t| t.get("added")).and_then(|v| v.as_i64())
            && added > 0 {
                let level = evaluate_confidence(0.7);
                *level_counts.entry(level.to_owned()).or_insert(0) += added;
            }

        // Evaluate promise changes (default 0.8)
        if let Some(promises) = changes.get("plot_promises") {
            for key in &["created", "advanced", "redeemed"] {
                if let Some(count) = promises.get(key).and_then(|v| v.as_i64())
                    && count > 0 {
                        let level = evaluate_confidence(0.8);
                        *level_counts.entry(level.to_owned()).or_insert(0) += count;
                    }
            }
        }

        // Evaluate world changes (default 0.7)
        if let Some(world) = changes.get("world") {
            for key in &["created", "expanded"] {
                if let Some(count) = world.get(key).and_then(|v| v.as_i64())
                    && count > 0 {
                        let level = evaluate_confidence(0.7);
                        *level_counts.entry(level.to_owned()).or_insert(0) += count;
                    }
            }
        }

        // Evaluate card changes (default 0.85)
        if let Some(added) = changes.get("card_pool").and_then(|c| c.get("added")).and_then(|v| v.as_i64())
            && added > 0 {
                let level = evaluate_confidence(0.85);
                *level_counts.entry(level.to_owned()).or_insert(0) += added;
            }

        // Overall level
        let total_items: i64 = level_counts.values().sum();
        let overall_level = if total_items == 0 {
            "high"
        } else {
            let score_map: std::collections::HashMap<&str, f64> = [
                ("high", 1.0), ("medium", 0.65), ("low", 0.4), ("reject", 0.15),
            ].into();
            let weighted_sum: f64 = level_counts.iter()
                .map(|(k, v)| (*v as f64) * score_map.get(k.as_str()).copied().unwrap_or(0.0))
                .sum();
            let avg_score = weighted_sum / total_items as f64;
            evaluate_confidence(avg_score)
        };

        serde_json::json!({
            "level": overall_level,
            "auto_applied": should_auto_apply(overall_level),
            "levels": level_counts,
            "items_requiring_review": items_requiring_review,
            "total_items": total_items,
        })
    }

    // ==================================================================
    // §11.7 [20]: Changelog archive
    // ==================================================================

    async fn _archive_changelog(
        &self, db: &DatabaseConnection, project_id: i32, chapter_id: &str,
        version: &str, chapter_number: i32, changes: &Json,
    ) -> AppResult<()> {
        let timestamp = Utc::now();

        // Character changes
        if let Some(chars) = changes.get("characters") {
            for key in &["created", "updated", "status_changed"] {
                if let Some(items) = chars.get(key).and_then(|v| v.as_array()) {
                    for item in items {
                        let change_type = if *key == "created" { "add" } else { "update" };
                        let name = item.get("name").and_then(|v| v.as_str()).unwrap_or("");
                        let entity_id = item.get("id").and_then(|v| v.as_str());

                        let reason = match *key {
                            "created" => format!("Phase 4 新增角色: {}", name),
                            "updated" => format!("Phase 4 更新角色: {}", name),
                            _ => format!("Phase 4 状态变更: {}: {} → {}",
                                name,
                                item.get("from").and_then(|v| v.as_str()).unwrap_or(""),
                                item.get("to").and_then(|v| v.as_str()).unwrap_or("")),
                        };

                        let log = vault_changelog::ActiveModel {
                            id: Set(Uuid::new_v4().to_string()),
                            project_id: Set(project_id),
                            chapter_id: Set(Some(chapter_id.to_owned())),
                            change_type: Set(change_type.to_owned()),
                            entity_type: Set("character".to_owned()),
                            entity_id: Set(entity_id.map(|s| s.to_owned())),
                            change_reason: Set(Some(reason)),
                            field_name: Set(if *key == "status_changed" { Some("status".to_owned()) } else { None }),
                            old_value: Set(item.get("from").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                            new_value: Set(item.get("to").and_then(|v| v.as_str()).map(|s| s.to_owned())),
                            meta_data: Set(Some(serde_json::json!({
                                "version": version,
                                "chapter": chapter_number,
                                "timestamp": timestamp.to_rfc3339(),
                            }))),
                            ..Default::default()
                        };
                        self.vault_dao.create_changelog(db, log).await?;
                    }
                }
            }
        }

        // Timeline changes
        if let Some(added) = changes.get("timeline").and_then(|t| t.get("added")).and_then(|v| v.as_i64())
            && added > 0 {
                let log = vault_changelog::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    chapter_id: Set(Some(chapter_id.to_owned())),
                    change_type: Set("add".to_owned()),
                    entity_type: Set("timeline".to_owned()),
                    change_reason: Set(Some(format!("Phase 4 新增 {} 个时间线事件", added))),
                    meta_data: Set(Some(serde_json::json!({
                        "version": version, "chapter": chapter_number,
                        "timestamp": timestamp.to_rfc3339(), "count": added,
                    }))),
                    ..Default::default()
                };
                self.vault_dao.create_changelog(db, log).await?;
            }

        // Promise changes
        if let Some(promises) = changes.get("plot_promises") {
            for (action, label) in &[("created", "新增"), ("advanced", "推进"), ("redeemed", "回收")] {
                if let Some(count) = promises.get(action).and_then(|v| v.as_i64())
                    && count > 0 {
                        let log = vault_changelog::ActiveModel {
                            id: Set(Uuid::new_v4().to_string()),
                            project_id: Set(project_id),
                            chapter_id: Set(Some(chapter_id.to_owned())),
                            change_type: Set(if *action == "created" { "add" } else { "update" }.to_owned()),
                            entity_type: Set("plot_promise".to_owned()),
                            change_reason: Set(Some(format!("Phase 4 {} {} 个剧情承诺", label, count))),
                            meta_data: Set(Some(serde_json::json!({
                                "version": version, "chapter": chapter_number,
                                "timestamp": timestamp.to_rfc3339(), "count": count, "action": action,
                            }))),
                            ..Default::default()
                        };
                        self.vault_dao.create_changelog(db, log).await?;
                    }
            }
        }

        // World changes
        if let Some(world) = changes.get("world") {
            for (action, label) in &[("created", "新增"), ("expanded", "扩展")] {
                if let Some(count) = world.get(action).and_then(|v| v.as_i64())
                    && count > 0 {
                        let log = vault_changelog::ActiveModel {
                            id: Set(Uuid::new_v4().to_string()),
                            project_id: Set(project_id),
                            chapter_id: Set(Some(chapter_id.to_owned())),
                            change_type: Set(if *action == "created" { "add" } else { "update" }.to_owned()),
                            entity_type: Set("world".to_owned()),
                            change_reason: Set(Some(format!("Phase 4 {} {} 个世界观条目", label, count))),
                            meta_data: Set(Some(serde_json::json!({
                                "version": version, "chapter": chapter_number,
                                "timestamp": timestamp.to_rfc3339(), "count": count, "action": action,
                            }))),
                            ..Default::default()
                        };
                        self.vault_dao.create_changelog(db, log).await?;
                    }
            }
        }

        // Card pool changes
        if let Some(added) = changes.get("card_pool").and_then(|c| c.get("added")).and_then(|v| v.as_i64())
            && added > 0 {
                let log = vault_changelog::ActiveModel {
                    id: Set(Uuid::new_v4().to_string()),
                    project_id: Set(project_id),
                    chapter_id: Set(Some(chapter_id.to_owned())),
                    change_type: Set("add".to_owned()),
                    entity_type: Set("card".to_owned()),
                    change_reason: Set(Some(format!("Phase 4 新增 {} 张卡牌", added))),
                    meta_data: Set(Some(serde_json::json!({
                        "version": version, "chapter": chapter_number,
                        "timestamp": timestamp.to_rfc3339(), "count": added,
                    }))),
                    ..Default::default()
                };
                self.vault_dao.create_changelog(db, log).await?;
            }

        tracing::info!("Changelog archived: version={}, chapter={}", version, chapter_number);
        Ok(())
    }

    /// Inline card retirement check (used from run_phase4).
    async fn _check_and_retire_cards_inline(
        &self, db: &DatabaseConnection, project_id: i32, current_chapter: i32,
    ) -> AppResult<()> {
        const MAX_ACTIVE_CARDS: usize = 80;
        const FRESHNESS_LIFESPAN: i32 = 4; // CARD_FRESHNESS_WINDOW * CARD_FRESHNESS_MULTIPLIER

        let active_cards = self.card_dao.list_active_by_project(db, project_id).await?;
        let active_count = active_cards.len();
        if active_count == 0 { return Ok(()); }

        // Calculate freshness expiry per card
        let mut card_freshness: Vec<(&CardPoolModel, i32)> = active_cards.iter()
            .map(|c| {
                let fc = c.freshness_chapter.unwrap_or(0);
                (c, fc + FRESHNESS_LIFESPAN)
            })
            .collect();
        card_freshness.sort_by_key(|(_, expiry)| *expiry);

        let mut retire_ids: Vec<String> = Vec::new();

        // Cap check
        if active_count > MAX_ACTIVE_CARDS {
            let excess = active_count - MAX_ACTIVE_CARDS;
            for (card, _) in card_freshness.iter().take(excess) {
                if !retire_ids.contains(&card.id) {
                    retire_ids.push(card.id.clone());
                }
            }
        }

        // Freshness expiry check
        for (card, expiry) in &card_freshness {
            if current_chapter >= *expiry && !retire_ids.contains(&card.id) {
                retire_ids.push(card.id.clone());
            }
        }

        if retire_ids.is_empty() { return Ok(()); }

        // Execute retirement
        for card_id in &retire_ids {
            if let Err(e) = self.card_dao.retire_card(db, card_id, Some(current_chapter)).await {
                tracing::warn!("Failed to retire card {}: {}", card_id, e);
            }
        }

        tracing::info!("Card retire: {} cards retired, {} remaining", retire_ids.len(), active_count - retire_ids.len());
        Ok(())
    }

    // ==================================================================
    // Public API: suggestions, task status, project analysis
    // ==================================================================

    /// Get suggestions for chapter quality improvement.
    pub async fn get_suggestions(
        &self, db: &DatabaseConnection, chapter_id: &str,
    ) -> AppResult<Json> {
        let chapter = self.chapter_dao.find_by_id(db, chapter_id).await?
            .ok_or_else(AppError::chapter_not_found)?;

        let mut suggestions: Vec<Json> = Vec::new();
        let mut details = serde_json::json!({});

        // 1. Check content
        if chapter.content.as_deref().unwrap_or("").is_empty() {
            suggestions.push(serde_json::json!({
                "id": "no_content", "type": "warning",
                "title": "章节内容为空",
                "description": "当前章节没有正文内容，请先生成内容。",
                "priority": "high",
            }));
            return Ok(serde_json::json!({
                "chapter_id": chapter_id,
                "suggestions": suggestions,
                "overall_score": 0.0,
                "details": details,
            }));
        }

        // 2. Word count
        let word_count = chapter.word_count.max(chapter.content.as_deref().unwrap_or("").len() as i32);
        details["word_count"] = serde_json::Value::Number(word_count.into());
        if word_count < 500 {
            suggestions.push(serde_json::json!({
                "id": "length_too_short", "type": "length",
                "title": "章节长度偏短",
                "description": format!("本章 {} 字，建议扩展到 1500-3000 字。", word_count),
                "priority": "medium",
            }));
        }

        // 3. Active character count
        if let Ok(chars) = self.vault_dao.find_characters(db, chapter.project_id).await {
            let active_count = chars.iter().filter(|c| c.status == "active").count();
            details["character_count"] = serde_json::Value::Number(active_count.into());
            if active_count > 5 {
                suggestions.push(serde_json::json!({
                    "id": "too_many_characters", "type": "character",
                    "title": "活跃角色较多",
                    "description": format!("当前有 {} 个活跃角色，注意避免角色过多导致读者混淆。", active_count),
                    "priority": "low",
                }));
            }
        }

        // 4. Dormant promises
        if let Ok(promises) = self.vault_dao.find_plot_promises(db, chapter.project_id).await {
            let dormant_count = promises.iter().filter(|p| p.status == "dormant").count();
            details["dormant_promises"] = serde_json::Value::Number(dormant_count.into());
            if dormant_count > 0 {
                let priority = if dormant_count > 3 { "high" } else { "medium" };
                suggestions.push(serde_json::json!({
                    "id": "dormant_promises", "type": "plot",
                    "title": "休眠伏笔提醒",
                    "description": format!("有 {} 个伏笔处于休眠状态，考虑在本章或后续章节回收。", dormant_count),
                    "priority": priority,
                }));
            }
        }

        // 5. Overall score
        let mut overall_score: f64 = 1.0;
        for s in &suggestions {
            if let Some(id) = s.get("id").and_then(|v| v.as_str()) {
                overall_score += match id {
                    "no_content" => -1.0,
                    "length_too_short" => -0.3,
                    "too_many_characters" => -0.1,
                    _ => 0.0,
                };
            }
        }
        overall_score = overall_score.max(0.0).min(1.0);
        details["overall_score"] = serde_json::Value::Number(serde_json::Number::from_f64((overall_score * 100.0).round() / 100.0).unwrap_or(0.into()));

        Ok(serde_json::json!({
            "chapter_id": chapter_id,
            "suggestions": suggestions,
            "overall_score": (overall_score * 100.0).round() / 100.0,
            "details": details,
        }))
    }

    /// Apply selected suggestions to a chapter.
    pub async fn apply_suggestions(
        &self, db: &DatabaseConnection, chapter_id: &str,
        suggestion_ids: &[String], auto_apply: bool,
    ) -> AppResult<Json> {
        let chapter = self.chapter_dao.find_by_id(db, chapter_id).await?
            .ok_or_else(AppError::chapter_not_found)?;

        let mut applied: Vec<Json> = Vec::new();
        let mut skipped: Vec<Json> = Vec::new();

        for sid in suggestion_ids {
            match sid.as_str() {
                "no_content" => {
                    skipped.push(serde_json::json!({"id": sid, "reason": "无法自动修复，请在生成后重试"}));
                }
                "length_too_short" => {
                    let mut active = chapter.clone().into_active_model();
                    let new_prompt = format!("{}\n[Phase4] 建议扩展本文字数至 1500+",
                        chapter.generation_prompt.as_deref().unwrap_or(""));
                    active.generation_prompt = Set(Some(new_prompt));
                    active.update(db).await.map_err(|e| AppError::internal(format!("更新章节失败: {e}")))?;
                    applied.push(serde_json::json!({"id": sid, "action": "标记为需扩展章节"}));
                }
                "too_many_characters" => {
                    applied.push(serde_json::json!({"id": sid, "action": "已记录角色密度提醒"}));
                }
                "dormant_promises" => {
                    applied.push(serde_json::json!({"id": sid, "action": "已标记伏笔回收建议"}));
                }
                _ => {
                    skipped.push(serde_json::json!({"id": sid, "reason": "未知建议类型"}));
                }
            }
        }

        // Update phase4_status
        let mut active = chapter.into_active_model();
        active.phase4_status = Set(if auto_apply { "done".to_owned() } else { "running".to_owned() });
        active.update(db).await.map_err(|e| AppError::internal(format!("更新章节状态失败: {e}")))?;

        Ok(serde_json::json!({
            "success": true,
            "chapter_id": chapter_id,
            "applied_count": applied.len(),
            "skipped_count": skipped.len(),
            "applied": applied,
            "skipped": skipped,
        }))
    }

    /// Get storage task status.
    pub async fn get_storage_status(
        &self, db: &DatabaseConnection, _user_id: &str, task_id: i32,
    ) -> AppResult<Json> {
        let task = self.phase4_dao.find_by_id(db, task_id).await?
            .ok_or_else(AppError::generation_task_not_found)?;

        Ok(serde_json::json!({
            "task_id": task.id,
            "state": task.state,
            "error_message": task.error_message,
            "started_at": task.started_at.map(|t| t.to_rfc3339()),
            "completed_at": task.completed_at.map(|t| t.to_rfc3339()),
        }))
    }

    /// Get task status (full detail).
    pub async fn get_task_status(&self, db: &DatabaseConnection, task_id: i32) -> AppResult<Json> {
        let task = self.phase4_dao.find_by_id(db, task_id).await?
            .ok_or_else(AppError::generation_task_not_found)?;

        Ok(serde_json::json!({
            "id": task.id,
            "nonce": task.nonce,
            "project_id": task.project_id,
            "chapter_id": task.chapter_id,
            "state": task.state,
            "error_message": task.error_message,
            "started_at": task.started_at.map(|t| t.to_rfc3339()),
            "completed_at": task.completed_at.map(|t| t.to_rfc3339()),
            "created_at": task.created_at.to_rfc3339(),
        }))
    }

    /// List tasks for a chapter.
    pub async fn list_chapter_tasks(
        &self, db: &DatabaseConnection, chapter_id: &str,
    ) -> AppResult<Vec<Json>> {
        let tasks = self.phase4_dao.list_by_chapter(db, chapter_id, None).await?;
        Ok(tasks.into_iter().map(|t| serde_json::json!({
            "id": t.id, "nonce": t.nonce, "project_id": t.project_id,
            "chapter_id": t.chapter_id, "status": t.status,
            "error_message": t.error_message,
            "started_at": t.started_at.map(|s| s.to_rfc3339()),
            "completed_at": t.completed_at.map(|c| c.to_rfc3339()),
            "created_at": t.created_at.to_rfc3339(),
        })).collect())
    }

    /// List tasks for a project.
    pub async fn list_project_tasks(
        &self, db: &DatabaseConnection, project_id: i32,
    ) -> AppResult<Vec<Json>> {
        let tasks = self.phase4_dao.list_by_project(db, project_id, None).await?;
        Ok(tasks.into_iter().map(|t| serde_json::json!({
            "id": t.id, "nonce": t.nonce, "project_id": t.project_id,
            "chapter_id": t.chapter_id, "status": t.status,
            "error_message": t.error_message,
            "started_at": t.started_at.map(|s| s.to_rfc3339()),
            "completed_at": t.completed_at.map(|c| c.to_rfc3339()),
            "created_at": t.created_at.to_rfc3339(),
        })).collect())
    }

    /// Analyze the full project: scan all cards, extract entities, compute confidence.
    pub async fn analyze_project(
        &self, db: &DatabaseConnection, project_id: i32,
    ) -> AppResult<Json> {
        // Verify project
        let _project = self.project_dao.find_by_id(db, project_id).await?
            .ok_or_else(AppError::project_not_found)?;

        // Get active cards
        let cards = self.card_dao.list_active_by_project(db, project_id).await?;

        // Entity extraction
        let mut entities: serde_json::Map<String, Json> = serde_json::Map::from_iter([
            ("characters".to_owned(), Json::Array(vec![])),
            ("locations".to_owned(), Json::Array(vec![])),
            ("items".to_owned(), Json::Array(vec![])),
            ("events".to_owned(), Json::Array(vec![])),
        ]);

        let mut seen_names: std::collections::HashMap<String, std::collections::HashSet<String>> = [
            ("characters".to_owned(), std::collections::HashSet::new()),
            ("locations".to_owned(), std::collections::HashSet::new()),
            ("items".to_owned(), std::collections::HashSet::new()),
            ("events".to_owned(), std::collections::HashSet::new()),
        ].into();

        for card in &cards {
            // Characters from card.characters
            if let Some(chars) = &card.characters
                && let Some(arr) = chars.as_array() {
                    for char_val in arr {
                        let name = match char_val {
                            Json::Object(obj) => obj.get("name").and_then(|v| v.as_str()).unwrap_or(""),
                            _ => char_val.as_str().unwrap_or(""),
                        };
                        if !name.is_empty() && seen_names.get_mut("characters").map(|s| s.insert(name.to_owned())).unwrap_or(false)
                            && let Some(arr) = entities.get_mut("characters").and_then(|v| v.as_array_mut()) {
                                arr.push(serde_json::json!({
                                    "name": name, "source_card_id": card.id,
                                    "source_card_name": card.name, "card_rarity": card.rarity,
                                }));
                            }
                    }
                }

            // Locations and items from text fields
            let text = format!("{} {}", card.direction_text, card.description);
            let location_kw = ["地", "城", "宫", "殿", "塔", "山", "河", "湖", "海", "森林", "洞穴", "村", "镇", "市"];
            let item_kw = ["剑", "刀", "盾", "戒", "书", "卷", "药", "石", "符", "阵", "器", "宝", "杖", "镜"];

            for kw in &location_kw {
                for (idx, _) in text.match_indices(kw) {
                    let start = idx.saturating_sub(6);
                    let end = (idx + kw.len() + 2).min(text.len());
                    let candidate = text[start..end].trim().to_owned();
                    if !candidate.is_empty() && seen_names.get_mut("locations").map(|s| s.insert(candidate.clone())).unwrap_or(false)
                        && let Some(arr) = entities.get_mut("locations").and_then(|v| v.as_array_mut()) {
                            arr.push(serde_json::json!({"name": candidate, "source_card_id": card.id}));
                        }
                }
            }
            for kw in &item_kw {
                for (idx, _) in text.match_indices(kw) {
                    let start = idx.saturating_sub(4);
                    let end = (idx + kw.len() + 2).min(text.len());
                    let candidate = text[start..end].trim().to_owned();
                    if !candidate.is_empty() && seen_names.get_mut("items").map(|s| s.insert(candidate.clone())).unwrap_or(false)
                        && let Some(arr) = entities.get_mut("items").and_then(|v| v.as_array_mut()) {
                            arr.push(serde_json::json!({"name": candidate, "source_card_id": card.id}));
                        }
                }
            }

            // Events from plot_promises
            if let Some(promises) = &card.plot_promises
                && let Some(arr) = promises.as_array() {
                    for p in arr {
                        let event_name = match p {
                            Json::Object(obj) => obj.get("title").or(obj.get("description")).and_then(|v| v.as_str()).unwrap_or(""),
                            _ => p.as_str().unwrap_or(""),
                        };
                        if !event_name.is_empty() && seen_names.get_mut("events").map(|s| s.insert(event_name.to_owned())).unwrap_or(false)
                            && let Some(arr) = entities.get_mut("events").and_then(|v| v.as_array_mut()) {
                                arr.push(serde_json::json!({
                                    "name": event_name, "source_card_id": card.id,
                                    "source_card_name": card.name,
                                }));
                            }
                    }
                }
        }

        // Compute confidence per entity
        for (etype, items) in entities.iter_mut() {
            if let Some(arr) = items.as_array_mut() {
                for entity in arr {
                    let rarity = entity.get("card_rarity").and_then(|v| v.as_str()).unwrap_or("");
                    let mut confidence: f64 = 0.5;
                    confidence += match rarity {
                        "legendary" => 0.3,
                        "epic" => 0.2,
                        "rare" => 0.1,
                        _ => 0.0,
                    };
                    if etype == "characters"
                        && let Some(name) = entity.get("name").and_then(|v| v.as_str()) {
                            let len = name.chars().count();
                            if (2..=4).contains(&len) { confidence += 0.1; }
                        }
                    confidence = confidence.min(1.0);
                    if let Some(obj) = entity.as_object_mut() {
                        obj.insert("confidence".to_owned(), Json::Number(serde_json::Number::from_f64((confidence * 100.0).round() / 100.0).unwrap_or(0.into())));
                    }
                }
            }
        }

        // Sort each type by confidence descending
        for items in entities.values_mut() {
            if let Some(arr) = items.as_array_mut() {
                arr.sort_by(|a, b| {
                    let ca = a.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let cb = b.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    cb.partial_cmp(&ca).unwrap_or(std::cmp::Ordering::Equal)
                });
            }
        }

        let total_entities: usize = entities.values().filter_map(|v| v.as_array()).map(|a| a.len()).sum();

        // Mark idle tasks as analyzed
        let pending_tasks = self.phase4_dao.list_by_project(db, project_id, Some("idle")).await?;
        for task in pending_tasks {
            let mut active = task.into_active_model();
            active.state = Set("analyzed".to_owned());
            let _ = self.phase4_dao.update(db, active).await;
        }

        Ok(serde_json::json!({
            "project_id": project_id,
            "total_cards_analyzed": cards.len(),
            "total_entities_found": total_entities,
            "entities_by_type": {
                "characters": entities.get("characters").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                "locations": entities.get("locations").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                "items": entities.get("items").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                "events": entities.get("events").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            },
            "entities": entities,
            "summary": format!(
                "分析完成：扫描 {} 张卡牌，发现 {} 个实体（{} 角色 / {} 地点 / {} 物品 / {} 事件）",
                cards.len(), total_entities,
                entities.get("characters").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                entities.get("locations").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                entities.get("items").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                entities.get("events").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            ),
        }))
    }

    /// Get suggestions (old API compatibility).
    pub async fn suggestions(&self, _db: &DatabaseConnection) -> AppResult<Json> {
        Ok(serde_json::json!({ "suggestions": [], "count": 0 }))
    }

    /// Apply suggestions (old API compatibility).
    pub async fn apply(&self, _db: &DatabaseConnection, suggestions: &[Json]) -> AppResult<usize> {
        for s in suggestions {
            tracing::info!(suggestion = %s, "Phase4 suggestion applied");
        }
        Ok(suggestions.len())
    }

    /// List Phase 4 tasks with optional status filter (old API compatibility).
    pub async fn tasks(&self, db: &DatabaseConnection, status: Option<&str>) -> AppResult<Json> {
        let tasks = if let Some(s) = status {
            self.phase4_dao.list_by_status(db, s, 0, 20).await?
        } else {
            vec![]
        };
        Ok(serde_json::to_value(tasks).unwrap_or_default())
    }

    /// List pending reviews (old API compatibility).
    pub async fn reviews(&self, _db: &DatabaseConnection) -> AppResult<Json> {
        Ok(serde_json::json!({ "reviews": [], "count": 0 }))
    }

    /// Retry a failed Phase 4 task (old API compatibility).
    pub async fn retry(&self, db: &DatabaseConnection, task_id: i32) -> AppResult<()> {
        self.phase4_dao.find_by_id(db, task_id).await?
            .ok_or_else(|| AppError::not_found("任务不存在".to_owned()))?;
        tracing::info!(task_id, "Phase4 task retry queued");
        Ok(())
    }
}

impl Default for Phase4Service {
    fn default() -> Self {
        Self::new(
            DeepSeekClient::new(),
            String::new(),
            moling_llm::DEFAULT_MODEL.to_owned(),
        )
    }
}

// ==================================================================
// Free functions — confidence evaluation helpers
// ==================================================================

/// Evaluate confidence level from a score (0.0-1.0).
fn evaluate_confidence(score: f64) -> &'static str {
    if score >= 0.8 { "high" }
    else if score >= 0.5 { "medium" }
    else if score >= 0.3 { "low" }
    else { "reject" }
}

/// Determine if auto-apply is allowed for a confidence level.
fn should_auto_apply(level: &str) -> bool {
    matches!(level, "high" | "medium")
}

/// Calculate Levenshtein edit distance between two strings.
fn calc_edit_distance(a: &str, b: &str) -> usize {
    let a_chars: Vec<char> = a.chars().collect();
    let b_chars: Vec<char> = b.chars().collect();
    let n = a_chars.len();
    let m = b_chars.len();

    if n == 0 { return m; }
    if m == 0 { return n; }

    let mut prev: Vec<usize> = (0..=m).collect();
    let mut curr = vec![0usize; m + 1];

    for i in 1..=n {
        curr[0] = i;
        for j in 1..=m {
            let cost = if a_chars[i - 1] == b_chars[j - 1] { 0 } else { 1 };
            curr[j] = (prev[j] + 1)
                .min(curr[j - 1] + 1)
                .min(prev[j - 1] + cost);
        }
        std::mem::swap(&mut prev, &mut curr);
    }

    prev[m]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_phase4_service_constructs() {
        let _ = Phase4Service::default();
    }

    #[test]
    fn test_calc_edit_distance() {
        assert_eq!(calc_edit_distance("abc", "abc"), 0);
        assert_eq!(calc_edit_distance("abc", "abd"), 1);
        assert_eq!(calc_edit_distance("", "abc"), 3);
        assert_eq!(calc_edit_distance("张三", "张三"), 0);
        assert_eq!(calc_edit_distance("张三", "张四"), 1);
    }

    #[test]
    fn test_evaluate_confidence() {
        assert_eq!(evaluate_confidence(0.9), "high");
        assert_eq!(evaluate_confidence(0.7), "medium");
        assert_eq!(evaluate_confidence(0.4), "low");
        assert_eq!(evaluate_confidence(0.2), "reject");
    }

    #[test]
    fn test_should_auto_apply() {
        assert!(should_auto_apply("high"));
        assert!(should_auto_apply("medium"));
        assert!(!should_auto_apply("low"));
        assert!(!should_auto_apply("reject"));
    }

    #[test]
    fn test_map_promise_type() {
        assert_eq!(Phase4Service::_map_promise_type("人物弧光"), "arc");
        assert_eq!(Phase4Service::_map_promise_type("剧情转折"), "subplot");
        assert_eq!(Phase4Service::_map_promise_type("悬念"), "mystery");
        assert_eq!(Phase4Service::_map_promise_type("未知"), "mystery");
    }
}
