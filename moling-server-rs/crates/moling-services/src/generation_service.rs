//! Generation service — 12-step AI chapter generation pipeline.
//!
//! Mirrors Python `app/service/generation_service.py`.
//! Delegates LLM calls to [`moling_llm`] and data access to [`moling_db`].
//!
//! ## Pipeline Steps
//!
//! 1. validate_pre_generation  — verify project state, permissions, quota
//! 2. load_context             — load project context (confirmed chapters, anchors)
//! 3. draw_cards               — draw direction cards for this generation
//! 4. build_weave_scheme       — generate weaving scheme from cards
//! 5. assemble_vault_data      — load four-vault data (characters/promises/timeline/world)
//! 6. build_generation_prompt  — assemble 5-layer prompt via PromptService
//! 7. call_llm                 — invoke DeepSeekClient
//! 8. parse_response           — parse LLM response (content + metadata)
//! 9. run_coherence_check      — coherence validation (Groups A/B/C)
//! 10. compute_direction_score — direction scoring against card weights
//! 11. save_chapter            — persist generated chapter
//! 12. update_phase4           — Phase4 vault collection update

use std::collections::HashMap;
use std::sync::Arc;

use moling_core::error::{AppError, AppResult};
use moling_db::dao::card_dao::CardDao;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_db::dao::generation_dao::GenerationDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::card_pool::Model as CardModel;
use moling_db::entities::chapter::Model as ChapterModel;
use moling_db::entities::dynamic_layer::Model as DynamicLayerModel;
use moling_db::entities::generation_task::Model as GenTask;
use moling_db::entities::project::Model as ProjectModel;
use moling_db::entities::vault_character::Model as VaultCharacterModel;
use moling_db::entities::vault_plot_promise::Model as VaultPlotPromiseModel;
use moling_db::entities::vault_timeline::Model as VaultTimelineModel;
use moling_db::entities::vault_world::Model as VaultWorldModel;
use moling_llm::budget::ContextBudget;
use moling_llm::client::{ChatMessage, DeepSeekClient};
use moling_llm::key_rotator::{KeyRotator, Pool};
use moling_llm::prompt::{
    DirectionCard, PromptService, VaultCharacter, VaultPlotPromise,
    VaultTimelineEvent, VaultWorldEntry, WeavingScheme,
};
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Input parameters for a generation run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationInput {
    /// Project ID.
    pub project_id: i32,
    /// Optional chapter ID (None = generate new chapter).
    pub chapter_id: Option<String>,
    /// Card IDs selected for this generation.
    pub card_ids: Vec<String>,
    /// Direction weights keyed by card ID.
    pub weights: HashMap<String, f64>,
    /// Generation mode ("single" | "continuation" | "rewrite").
    pub mode: String,
    /// Target word count.
    pub word_count: i32,
    /// Temperature for LLM generation (0.0–1.0).
    pub creativity: f64,
    /// User-provided optional instruction.
    pub user_instruction: Option<String>,
}

impl Default for GenerationInput {
    fn default() -> Self {
        Self {
            project_id: 0,
            chapter_id: None,
            card_ids: Vec::new(),
            weights: HashMap::new(),
            mode: "single".to_owned(),
            word_count: 2000,
            creativity: 0.7,
            user_instruction: None,
        }
    }
}

/// Output from a generation run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationOutput {
    /// Generated text content.
    pub content: String,
    /// Word count of generated content.
    pub word_count: i32,
    /// Coherence check result.
    pub coherence_check: CoherenceResult,
    /// Direction scoring results.
    pub direction_conflicts: Vec<DirectionConflict>,
    /// Saved chapter model.
    pub chapter: Option<ChapterModel>,
    /// Generation task model.
    pub task: GenTask,
}

/// Configuration for generation behaviour.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    /// Maximum retry attempts for LLM calls.
    pub max_retries: u32,
    /// Default temperature for brainstorming.
    pub brainstorming_temperature: f64,
    /// Default temperature for body writing.
    pub writing_temperature: f64,
    /// Max tokens for LLM output.
    pub max_output_tokens: u32,
    /// Max tokens for brainstorming.
    pub brainstorming_max_tokens: u32,
    /// Model name override (None = use default).
    pub model: Option<String>,
    /// Whether to run coherence checks.
    pub enable_coherence_check: bool,
    /// Whether to auto-adjust on coherence failure.
    pub auto_adjust: bool,
}

impl Default for GenerationConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            brainstorming_temperature: 0.8,
            writing_temperature: 0.7,
            max_output_tokens: 4096,
            brainstorming_max_tokens: 2048,
            model: None,
            enable_coherence_check: true,
            auto_adjust: true,
        }
    }
}

/// A chapter draft before persistence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChapterDraft {
    /// Chapter title.
    pub title: String,
    /// Chapter content.
    pub content: String,
    /// Chapter number.
    pub chapter_number: i32,
    /// Word count.
    pub word_count: i32,
    /// Card IDs used.
    pub used_card_ids: Vec<String>,
    /// Generation mode.
    pub generation_mode: String,
    /// Generation prompt sent to LLM.
    pub generation_prompt: Option<String>,
    /// Weights used.
    pub generation_weights: Option<Json>,
    /// Full LLM response.
    pub generation_result: Option<String>,
}

/// Outcome of a coherence check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceResult {
    /// Whether the content passed coherence validation.
    pub passed: bool,
    /// Overall score (0.0–1.0).
    pub score: f64,
    /// Version identifier ("v2-grouped").
    pub version: String,
    /// Detected issues (flattened).
    pub issues: Vec<String>,
    /// Per-group details.
    pub groups: Vec<CoherenceGroup>,
}

/// A single coherence check group result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceGroup {
    /// Group name (A=narrative, B=writing, C=continuity).
    pub group: String,
    /// Whether the group passed.
    pub passed: bool,
    /// Score for this group.
    pub score: f64,
    /// Issues detected in this group.
    pub issues: Vec<String>,
}

/// A direction conflict between cards.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectionConflict {
    /// Source card name.
    pub card_a: String,
    /// Conflicting card name.
    pub card_b: String,
    /// Conflict description.
    pub conflict: String,
    /// Severity (0.0–1.0).
    pub severity: f64,
}

/// Outline template used during Step 6.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct OutlineTemplate {
    pub chapter_title: String,
    pub chapter_number: i32,
    pub characters: Vec<String>,
    pub recent_events: Vec<String>,
    pub summary: String,
    pub anchor_pov: String,
    pub anchor_location: String,
    pub anchor_time: String,
    pub must_hold: Vec<String>,
    pub must_not: Vec<String>,
    pub unresolved_hooks: Vec<String>,
    pub selected_directions: Vec<Json>,
    pub weaving_scheme: Option<Json>,
    pub generation_requirements: Option<Json>,
}

// ---------------------------------------------------------------------------
// GenerationService
// ---------------------------------------------------------------------------

/// Business logic for AI chapter generation — 12-step pipeline.
#[derive(Clone)]
pub struct GenerationService {
    gen_dao: GenerationDao,
    project_dao: ProjectDao,
    chapter_dao: ChapterDao,
    card_dao: CardDao,
    vault_dao: VaultDao,
    dynamic_layer_dao: DynamicLayerDao,
    llm_client: Arc<DeepSeekClient>,
    key_rotator: Option<Arc<KeyRotator>>,
    config: GenerationConfig,
}

impl GenerationService {
    /// Create a new GenerationService with default configuration.
    pub fn new() -> Self {
        Self {
            gen_dao: GenerationDao,
            project_dao: ProjectDao,
            chapter_dao: ChapterDao,
            card_dao: CardDao,
            vault_dao: VaultDao,
            dynamic_layer_dao: DynamicLayerDao,
            llm_client: Arc::new(DeepSeekClient::new()),
            key_rotator: None,
            config: GenerationConfig::default(),
        }
    }

    /// Create a service with custom LLM client and key rotator.
    pub fn with_llm(mut self, client: DeepSeekClient, rotator: Option<KeyRotator>) -> Self {
        self.llm_client = Arc::new(client);
        self.key_rotator = rotator.map(Arc::new);
        self
    }

    /// Set generation configuration.
    pub fn with_config(mut self, config: GenerationConfig) -> Self {
        self.config = config;
        self
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    /// Verify project ownership.
    async fn verify_owner(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<ProjectModel> {
        let p = self
            .project_dao
            .find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(p)
    }

    /// Get the next available API key from the key rotator, or a placeholder.
    fn get_api_key(&self, pool: Pool) -> Option<String> {
        self.key_rotator.as_ref().and_then(|kr| kr.next(pool))
    }

    /// Get the effective model name.
    fn model_name(&self) -> &str {
        self.config
            .model
            .as_deref()
            .unwrap_or(moling_llm::client::DEFAULT_MODEL)
    }

    // ------------------------------------------------------------------
    // Public API — task lifecycle
    // ------------------------------------------------------------------

    /// Start a generation task. Creates a task record and dispatches to the pipeline.
    ///
    /// Returns the created generation task. The actual generation runs via
    /// [`execute_pipeline`].
    pub async fn start_generation(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        input: &GenerationInput,
        task_id: Option<&str>,
    ) -> AppResult<GenTask> {
        let _project = self
            .verify_owner(db, user_id, input.project_id)
            .await?;

        // Validate chapter if provided
        if let Some(ref ch_id) = input.chapter_id {
            let ch = self
                .chapter_dao
                .find_by_id(db, ch_id)
                .await?
                .ok_or_else(AppError::chapter_not_found)?;
            if ch.project_id != input.project_id {
                return Err(AppError::bad_request("章节不属于该项目".to_owned()));
            }
        }

        let tid = task_id
            .map(|s| s.to_owned())
            .unwrap_or_else(|| Uuid::new_v4().to_string());
        let uuid =
            Uuid::parse_str(&tid).map_err(|_| AppError::bad_request("无效的任务ID格式".to_owned()))?;

        let model = moling_db::entities::generation_task::ActiveModel {
            id: Set(uuid),
            project_id: Set(input.project_id),
            chapter_id: Set(input.chapter_id.clone()),
            user_id: Set(user_id.to_owned()),
            task_type: Set(input.mode.clone()),
            status: Set("pending".to_owned()),
            input_params: Set(serde_json::to_value(input).unwrap_or_default()),
            progress_percent: Set(0),
            progress_stage: Set(Some("initializing".to_owned())),
            ..Default::default()
        };

        let task = self.gen_dao.create(db, model).await?;
        tracing::info!(task_id = %task.id, project_id = input.project_id, "Generation task created");
        Ok(task)
    }

    /// Execute the full 12-step generation pipeline for a task.
    ///
    /// Returns the generation output on success. On failure, the task status
    /// is set to "failed" and the error is propagated.
    pub async fn execute_pipeline(
        &self,
        db: &DatabaseConnection,
        task_id: &str,
    ) -> AppResult<GenerationOutput> {
        let task = self
            .gen_dao
            .find_by_id(db, task_id)
            .await?
            .ok_or_else(AppError::generation_task_not_found)?;

        // Mark as running
        let mut task_active = task.clone().into_active_model();
        task_active.status = Set("running".to_owned());
        task_active.progress_percent = Set(5);
        task_active.progress_stage = Set(Some("weight_allocation".to_owned()));
        let task = task_active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新任务状态失败: {e}"))
        })?;

        // Parse input parameters
        let input: GenerationInput = serde_json::from_value(task.input_params.clone())
            .unwrap_or_default();

        // Execute pipeline steps, catching errors to mark task as failed
        match self.run_pipeline(db, &task, &input).await {
            Ok(output) => {
                tracing::info!(task_id = %task.id, "Generation pipeline completed");
                Ok(output)
            }
            Err(e) => {
                tracing::error!(task_id = %task.id, error = %e, "Generation pipeline failed");
                // Mark task as failed
                let mut fail_active = task.into_active_model();
                fail_active.status = Set("failed".to_owned());
                fail_active.error_message = Set(Some(format!("{e}")));
                let _ = fail_active.update(db).await;
                Err(e)
            }
        }
    }

    /// Internal pipeline runner — all 12 steps.
    async fn run_pipeline(
        &self,
        db: &DatabaseConnection,
        task: &GenTask,
        input: &GenerationInput,
    ) -> AppResult<GenerationOutput> {
        // ── Step 1: validate_pre_generation ──
        tracing::info!(task_id = %task.id, "Step 1: validate_pre_generation");
        let project = self.step1_validate(db, task, input).await?;
        self.update_progress(db, task, 10, "weight_allocation").await?;

        // ── Step 2: load_context ──
        tracing::info!(task_id = %task.id, "Step 2: load_context");
        let (chapter, recent_layers) = self
            .step2_load_context(db, task, &project)
            .await?;
        self.update_progress(db, task, 15, "vault_filtering").await?;

        // ── Step 3: draw_cards ──
        tracing::info!(task_id = %task.id, "Step 3: draw_cards");
        let cards = self.step3_draw_cards(db, task, input).await?;
        self.update_progress(db, task, 20, "conflict_detection").await?;

        // ── Step 4: build_weave_scheme ──
        tracing::info!(task_id = %task.id, "Step 4: build_weave_scheme");
        let weight_map = self
            .step4_weight_allocation(&cards, &input.weights)
            .await?;
        let _weaving_scheme = self
            .step4_build_weave_scheme(&cards, &weight_map, &input.mode)
            .await?;
        self.update_progress(db, task, 25, "direction_scoring").await?;

        // ── Step 5: assemble_vault_data ──
        tracing::info!(task_id = %task.id, "Step 5: assemble_vault_data");
        let vault_data = self
            .step5_assemble_vault(db, project.id, &cards)
            .await?;
        self.update_progress(db, task, 30, "weaving_scheme").await?;

        // ── Step 6: build_generation_prompt ──
        tracing::info!(task_id = %task.id, "Step 6: build_generation_prompt");
        let outline = self
            .step6_build_outline(
                &project,
                chapter.as_ref(),
                &cards,
                &weight_map,
                &vault_data,
                &recent_layers,
                input.word_count,
            )
            .await?;
        let (generation_prompt, _llm_prompt_char_count) = self
            .step6_build_prompt(&project, chapter.as_ref(), &outline, &vault_data, &cards, &weight_map)
            .await?;
        self.update_progress(db, task, 40, "narrative_extraction").await?;

        // ── Step 7: call_llm ──
        tracing::info!(task_id = %task.id, "Step 7: call_llm");
        let generated_content = self
            .step7_call_llm(&project, chapter.as_ref(), &outline, &vault_data, &weight_map, input.creativity)
            .await?;
        self.update_progress(db, task, 70, "coherence_validation").await?;

        // ── Step 8: parse_response ──
        tracing::info!(task_id = %task.id, "Step 8: parse_response");
        let (content, _meta) = self
            .step8_parse_response(&generated_content)
            .await?;
        self.update_progress(db, task, 75, "coherence_validation").await?;

        // ── Step 9: run_coherence_check ──
        let coherence_result = if self.config.enable_coherence_check {
            tracing::info!(task_id = %task.id, "Step 9: run_coherence_check");
            self.step9_coherence_check(db, &project, chapter.as_ref(), &content)
                .await?
        } else {
            CoherenceResult {
                passed: true,
                score: 1.0,
                version: "v2-grouped-skipped".to_owned(),
                issues: Vec::new(),
                groups: Vec::new(),
            }
        };

        // Auto-adjust on coherence failure
        let final_content = if !coherence_result.passed && self.config.auto_adjust {
            tracing::warn!(task_id = %task.id, "Coherence check failed, adjusting...");
            self.adjust_content(&content, &coherence_result.issues)
                .await
                .unwrap_or_else(|_| content.clone())
        } else {
            content
        };
        self.update_progress(db, task, 80, "coherence_validation").await?;

        // ── Step 10: compute_direction_score ──
        tracing::info!(task_id = %task.id, "Step 10: compute_direction_score");
        let direction_conflicts = self
            .step10_compute_direction_score(&cards, &weight_map, &final_content)
            .await?;
        self.update_progress(db, task, 85, "direction_scoring").await?;

        // ── Step 11: save_chapter ──
        tracing::info!(task_id = %task.id, "Step 11: save_chapter");
        let draft = ChapterDraft {
            title: outline.chapter_title.clone(),
            content: final_content.clone(),
            chapter_number: outline.chapter_number,
            word_count: final_content.chars().count() as i32,
            used_card_ids: input.card_ids.clone(),
            generation_mode: input.mode.clone(),
            generation_prompt: Some(generation_prompt),
            generation_weights: Some(serde_json::to_value(&weight_map).unwrap_or_default()),
            generation_result: Some(generated_content),
        };
        let saved_chapter = self
            .step11_save_chapter(db, task, &draft)
            .await?;
        self.update_progress(db, task, 90, "dynamic_layer_update").await?;

        // ── Step 12: update_phase4 ──
        tracing::info!(task_id = %task.id, "Step 12: update_phase4");
        self.step12_update_phase4(db, project.id, saved_chapter.as_ref())
            .await?;
        self.update_progress(db, task, 95, "completed").await?;

        // Mark task done
        let mut done_active = {
            let latest = self.gen_dao.find_by_id(db, &task.id.to_string()).await?.ok_or_else(AppError::generation_task_not_found)?;
            latest.into_active_model()
        };
        done_active.status = Set("done".to_owned());
        done_active.progress_percent = Set(100);
        done_active.progress_stage = Set(Some("completed".to_owned()));
        done_active.output_data = Set(Some(serde_json::json!({
            "content": final_content,
            "word_count": final_content.chars().count(),
            "coherence_check": coherence_result,
            "direction_conflicts": direction_conflicts,
        })));
        let final_task = done_active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新任务完成状态失败: {e}"))
        })?;

        Ok(GenerationOutput {
            content: final_content,
            word_count: draft.word_count,
            coherence_check: coherence_result,
            direction_conflicts,
            chapter: saved_chapter,
            task: final_task,
        })
    }

    /// Update task progress (percentage + stage label).
    async fn update_progress(
        &self,
        db: &DatabaseConnection,
        task: &GenTask,
        percent: i32,
        stage: &str,
    ) -> AppResult<()> {
        let current = self
            .gen_dao
            .find_by_id(db, &task.id.to_string())
            .await?
            .ok_or_else(AppError::generation_task_not_found)?;
        let mut active = current.into_active_model();
        active.progress_percent = Set(percent);
        active.progress_stage = Set(Some(stage.to_owned()));
        active.update(db).await.map_err(|e| {
            AppError::internal(format!("更新进度失败: {e}"))
        })?;
        Ok(())
    }

    // ==================================================================
    // Pipeline Step Implementations
    // ==================================================================

    /// Step 1: Validate pre-generation conditions — project state, permissions, quota.
    pub async fn step1_validate(
        &self,
        db: &DatabaseConnection,
        task: &GenTask,
        input: &GenerationInput,
    ) -> AppResult<ProjectModel> {
        let project = self
            .project_dao
            .find_by_id(db, input.project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;

        // Check project is not deleted
        if project.is_deleted {
            return Err(AppError::bad_request("项目已被删除".to_owned()));
        }

        // Count pending/running tasks — limit concurrent generations
        let pending_tasks = self
            .gen_dao
            .list_by_status(db, "pending", 50)
            .await?
            .into_iter()
            .filter(|t| t.project_id == input.project_id)
            .count();
        let running_tasks = self
            .gen_dao
            .list_by_status(db, "running", 50)
            .await?
            .into_iter()
            .filter(|t| t.project_id == input.project_id && t.id != task.id)
            .count();

        if pending_tasks + running_tasks > 3 {
            return Err(AppError::bad_request(
                "该项目已有过多进行中的生成任务，请等待完成后再试".to_owned(),
            ));
        }

        tracing::info!(
            project_id = project.id,
            project_title = %project.title,
            "Pre-generation validation passed"
        );
        Ok(project)
    }

    /// Step 2: Load project context — confirmed chapters, dynamic layers, anchors.
    pub async fn step2_load_context(
        &self,
        db: &DatabaseConnection,
        task: &GenTask,
        project: &ProjectModel,
    ) -> AppResult<(Option<ChapterModel>, Vec<DynamicLayerModel>)> {
        // Load chapter if specified
        let chapter = if let Some(ref ch_id) = task.chapter_id {
            self.chapter_dao
                .find_by_id(db, ch_id)
                .await?
        } else {
            // Get current (latest) chapter
            self.chapter_dao
                .get_current(db, project.id)
                .await?
        };

        // Load recent dynamic layers for context
        let recent_layers = self
            .dynamic_layer_dao
            .list_recent_by_project(db, project.id, 5)
            .await?;

        if let Some(ref ch) = chapter {
            tracing::info!(
                chapter_id = %ch.id,
                chapter_number = ch.chapter_number,
                "Loaded chapter context"
            );
        }

        Ok((chapter, recent_layers))
    }

    /// Step 3: Draw direction cards for this generation.
    pub async fn step3_draw_cards(
        &self,
        db: &DatabaseConnection,
        _task: &GenTask,
        input: &GenerationInput,
    ) -> AppResult<Vec<CardModel>> {
        if input.card_ids.is_empty() {
            // Auto-draw from active pool
            let active = self
                .card_dao
                .get_active_cards(db, input.project_id, 3)
                .await?;
            tracing::info!(count = active.len(), "Auto-drew cards from active pool");
            Ok(active)
        } else {
            // Use specified cards
            let cards = self
                .card_dao
                .get_by_ids(db, input.project_id, &input.card_ids)
                .await?;
            if cards.is_empty() {
                return Err(AppError::bad_request("指定的卡牌不存在".to_owned()));
            }
            tracing::info!(count = cards.len(), "Using specified cards");
            Ok(cards)
        }
    }

    /// Step 4a: Weight allocation — normalize direction weights.
    pub async fn step4_weight_allocation(
        &self,
        cards: &[CardModel],
        input_weights: &HashMap<String, f64>,
    ) -> AppResult<HashMap<String, f64>> {
        let mut weight_map: HashMap<String, f64> = HashMap::new();

        if input_weights.is_empty() {
            // Equal weight distribution
            let w = 1.0 / cards.len().max(1) as f64;
            for card in cards {
                weight_map.insert(card.id.clone(), w);
            }
        } else {
            // Use provided weights, normalize
            let total: f64 = input_weights.values().sum();
            if total > 0.0 {
                for (id, w) in input_weights {
                    weight_map.insert(id.clone(), w / total);
                }
            } else {
                for card in cards {
                    weight_map.insert(card.id.clone(), 1.0 / cards.len().max(1) as f64);
                }
            }
        }

        tracing::info!(cards = cards.len(), weights = ?weight_map, "Weight allocation complete");
        Ok(weight_map)
    }

    /// Step 4b: Build weaving scheme from cards and weights.
    pub async fn step4_build_weave_scheme(
        &self,
        cards: &[CardModel],
        weight_map: &HashMap<String, f64>,
        mode: &str,
    ) -> AppResult<WeavingScheme> {
        let order: Vec<String> = cards
            .iter()
            .map(|c| c.name.clone())
            .collect();

        let emphasis = cards
            .iter()
            .max_by(|a, b| {
                let wa = weight_map.get(&a.id).copied().unwrap_or(0.0);
                let wb = weight_map.get(&b.id).copied().unwrap_or(0.0);
                wa.partial_cmp(&wb).unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|c| format!("重点方向: {}", c.direction_text));

        let description = match mode {
            "continuation" => Some("续写模式：在前文基础上推进情节，保持风格一致".to_owned()),
            "rewrite" => Some("重写模式：在保持情节骨架的前提下重写本章".to_owned()),
            _ => Some(format!(
                "融合{}张卡牌方向，生成新章节",
                cards.len()
            )),
        };

        tracing::info!(
            mode = %mode,
            cards = cards.len(),
            order = ?order,
            "Weaving scheme built"
        );

        Ok(WeavingScheme {
            description,
            order,
            emphasis,
        })
    }

    /// Step 5: Assemble vault data — characters, plot promises, timeline, world.
    pub async fn step5_assemble_vault(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        _cards: &[CardModel],
    ) -> AppResult<VaultFilteredData> {
        let characters = self
            .vault_dao
            .find_characters(db, project_id)
            .await?;

        let plot_promises = self
            .vault_dao
            .find_plot_promises(db, project_id)
            .await?;

        let timeline = self
            .vault_dao
            .find_timeline_events(db, project_id)
            .await?;

        let world_entries = self
            .vault_dao
            .find_world_entries(db, project_id)
            .await?;

        tracing::info!(
            characters = characters.len(),
            promises = plot_promises.len(),
            timeline = timeline.len(),
            world = world_entries.len(),
            "Vault data assembled"
        );

        Ok(VaultFilteredData {
            characters,
            plot_promises,
            timeline,
            world_entries,
        })
    }

    /// Step 6a: Build outline template from project/chapter/cards/vault data.
    pub async fn step6_build_outline(
        &self,
        project: &ProjectModel,
        chapter: Option<&ChapterModel>,
        cards: &[CardModel],
        weight_map: &HashMap<String, f64>,
        vault: &VaultFilteredData,
        recent_layers: &[DynamicLayerModel],
        word_count: i32,
    ) -> AppResult<OutlineTemplate> {
        // Determine chapter number
        let chapter_number = chapter
            .map(|c| c.chapter_number + 1)
            .unwrap_or(1);

        let chapter_title = chapter
            .map(|c| format!("第{}章", c.chapter_number + 1))
            .unwrap_or_else(|| "第1章".to_owned());

        // Active characters (top 5)
        let characters: Vec<String> = vault
            .characters
            .iter()
            .take(5)
            .map(|c| c.name.clone())
            .collect();

        // Recent events from timeline (last 3)
        let recent_events: Vec<String> = vault
            .timeline
            .iter()
            .rev()
            .take(3)
            .map(|t| t.event.clone())
            .collect();

        // Extract dynamic layer data
        let latest_layer = recent_layers.first();
        let summary = latest_layer
            .and_then(|l| l.summary.clone())
            .unwrap_or_default();
        let anchor_pov = latest_layer
            .and_then(|l| l.anchor_pov.clone())
            .unwrap_or_else(|| "不限".to_owned());
        let anchor_location = latest_layer
            .and_then(|l| l.anchor_location.clone())
            .unwrap_or_else(|| "不限".to_owned());
        let anchor_time = latest_layer
            .and_then(|l| l.anchor_time.clone())
            .unwrap_or_else(|| "当前".to_owned());

        let must_hold: Vec<String> = latest_layer
            .and_then(|l| l.must_hold.as_ref())
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_owned())).collect())
            .unwrap_or_default();

        let must_not: Vec<String> = latest_layer
            .and_then(|l| l.must_not.as_ref())
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_owned())).collect())
            .unwrap_or_default();

        let unresolved_hooks: Vec<String> = latest_layer
            .and_then(|l| l.unresolved_hooks.as_ref())
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| {
                        v.as_object()
                            .and_then(|o| o.get("description"))
                            .and_then(|d| d.as_str())
                            .map(|s| s.to_owned())
                            .or_else(|| v.as_str().map(|s| s.to_owned()))
                    })
                    .collect()
            })
            .unwrap_or_default();

        // Selected directions from cards
        let selected_directions: Vec<Json> = cards
            .iter()
            .map(|c| {
                serde_json::json!({
                    "card_name": c.name,
                    "card_id": c.id,
                    "direction_type": c.direction_type,
                    "direction_text": c.direction_text,
                    "weight": weight_map.get(&c.id).copied().unwrap_or(1.0),
                })
            })
            .collect();

        let gen_req = serde_json::json!({
            "word_count": word_count.to_string(),
            "style": project.style.clone().unwrap_or_default(),
        });

        tracing::info!(
            chapter_number,
            characters = ?characters,
            "Outline template built"
        );

        Ok(OutlineTemplate {
            chapter_title,
            chapter_number,
            characters,
            recent_events,
            summary,
            anchor_pov,
            anchor_location,
            anchor_time,
            must_hold,
            must_not,
            unresolved_hooks,
            selected_directions,
            weaving_scheme: None,
            generation_requirements: Some(gen_req),
        })
    }

    /// Step 6b: Build the full 5-layer generation prompt via PromptService.
    pub async fn step6_build_prompt(
        &self,
        project: &ProjectModel,
        _chapter: Option<&ChapterModel>,
        outline: &OutlineTemplate,
        vault: &VaultFilteredData,
        cards: &[CardModel],
        weight_map: &HashMap<String, f64>,
    ) -> AppResult<(String, usize)> {
        // Convert vault entities to prompt types
        let prompt_chars: Vec<VaultCharacter> = vault
            .characters
            .iter()
            .map(|c| VaultCharacter {
                name: c.name.clone(),
                role: Some(c.role.clone()),
                description: c.description.clone(),
                traits: c.traits.as_ref().and_then(|v| {
                    v.as_array()
                        .map(|arr| arr.iter().filter_map(|x| x.as_str().map(|s| s.to_owned())).collect())
                }).unwrap_or_default(),
                emotion: c.emotion.clone(),
            })
            .collect();

        let prompt_promises: Vec<VaultPlotPromise> = vault
            .plot_promises
            .iter()
            .map(|p| VaultPlotPromise {
                description: p.description.clone(),
                promise_type: Some(p.r#type.clone()),
                status: Some(p.status.clone()),
                urgency: Some(p.urgency.to_string()),
            })
            .collect();

        let prompt_timeline: Vec<VaultTimelineEvent> = vault
            .timeline
            .iter()
            .rev()
            .take(3)
            .map(|t| VaultTimelineEvent {
                event: t.event.clone(),
                description: Some(t.description.clone()),
                chapter_number: Some(t.chapter_number as u32),
                is_key_event: t.is_key_event,
                impact: t.impact.clone(),
            })
            .collect();

        let prompt_world: Vec<VaultWorldEntry> = vault
            .world_entries
            .iter()
            .map(|w| VaultWorldEntry {
                term: w.name.clone(),
                description: Some(w.description.clone()),
                category: Some(w.category.clone()),
            })
            .collect();

        let prompt_cards: Vec<DirectionCard> = cards
            .iter()
            .map(|c| DirectionCard {
                name: c.name.clone(),
                direction_type: Some(c.direction_type.clone()),
                direction_text: Some(c.direction_text.clone()),
                rarity: Some(c.rarity.clone()),
            })
            .collect();

        // Assemble via PromptService
        let pov = outline.anchor_pov.as_str();
        let loc = outline.anchor_location.as_str();
        let time = outline.anchor_time.as_str();
        let pov_opt = (pov != "不限" && !pov.is_empty()).then_some(pov);
        let loc_opt = (loc != "不限" && !loc.is_empty()).then_some(loc);
        let time_opt = (time != "当前" && !time.is_empty()).then_some(time);

        let prompt = PromptService::build_full_prompt(
            outline.chapter_number as u32,
            &project.title,
            &outline.chapter_title,
            pov_opt,
            loc_opt,
            time_opt,
            &outline.summary,
            &outline.must_hold,
            &outline.must_not,
            &outline.unresolved_hooks,
            &prompt_chars,
            &prompt_promises,
            &prompt_timeline,
            &prompt_world,
            &prompt_cards,
            weight_map,
            None, // weaving scheme
            None, // style fingerprint
        );

        let char_count = prompt.chars().count();

        // Context budget check
        let budget = ContextBudget::check_and_truncate(
            &prompt,
            self.config.model.as_deref(),
            self.config.max_output_tokens as usize,
            None,
        );

        tracing::info!(
            prompt_chars = char_count,
            estimated_tokens = budget.estimated_input_tokens,
            within_budget = budget.within_budget,
            "Generation prompt built"
        );

        Ok((budget.truncated_prompt, char_count))
    }

    /// Step 7: Call LLM for body text generation.
    pub async fn step7_call_llm(
        &self,
        project: &ProjectModel,
        chapter: Option<&ChapterModel>,
        outline: &OutlineTemplate,
        vault: &VaultFilteredData,
        weight_map: &HashMap<String, f64>,
        creativity: f64,
    ) -> AppResult<String> {
        // Build the prompt for body writing (includes inspiration injection)
        let (base_prompt, _) = self
            .step6_build_prompt(project, chapter, outline, vault, &[], weight_map)
            .await?;

        // Add writing requirements
        let gen_req = outline
            .generation_requirements
            .as_ref()
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();
        let word_count = gen_req
            .get("word_count")
            .and_then(|v| v.as_str())
            .unwrap_or("2500-3500");
        let style = gen_req
            .get("style")
            .and_then(|v| v.as_str())
            .unwrap_or("");

        let writing_req = if style.is_empty() {
            format!("【写作要求】\n字数 {word_count}\n结尾留钩子 / 至少推进一个未收束悬念\n")
        } else {
            format!("【写作要求】\n字数 {word_count} / 风格: {style}\n结尾留钩子 / 至少推进一个未收束悬念\n")
        };

        let full_prompt = base_prompt.replace(
            "请直接开始写作，不要添加任何解释或说明。",
            &format!("{writing_req}\n请直接开始写作，不要添加任何解释或说明。"),
        );

        // Run context budget check on final prompt
        let budget = ContextBudget::check_and_truncate(
            &full_prompt,
            self.config.model.as_deref(),
            self.config.max_output_tokens as usize,
            None,
        );

        let messages = vec![
            ChatMessage::system("你是一个专业的小说作家，擅长创作引人入胜的故事章节。"),
            ChatMessage::user(budget.truncated_prompt),
        ];

        // Get API key
        let api_key = self
            .get_api_key(Pool::Pro)
            .unwrap_or_else(|| "sk-placeholder".to_owned());

        let response = self
            .llm_client
            .chat(
                &messages,
                &api_key,
                self.model_name(),
                creativity,
                self.config.max_output_tokens,
            )
            .await
            .map_err(|e| {
                tracing::error!(error = %e, "LLM call failed in step 7");
                // Mark key as having an error if rotator available
                if let Some(ref kr) = self.key_rotator {
                    kr.mark_error(&api_key, "other");
                }
                AppError::internal(format!("文本生成失败: {e}"))
            })?;

        // Mark key success
        if let Some(ref kr) = self.key_rotator {
            kr.mark_success(&api_key);
        }

        tracing::info!(
            response_len = response.chars().count(),
            "LLM body text generation complete"
        );

        Ok(response)
    }

    /// Step 8: Parse LLM response — extract content and metadata.
    pub async fn step8_parse_response(
        &self,
        response: &str,
    ) -> AppResult<(String, Option<Json>)> {
        // Try to split title from content
        let content = response.trim().to_owned();

        // Basic metadata extraction (chapter title if present as first line)
        let mut meta = serde_json::Map::new();
        let first_line = content.lines().next().unwrap_or("").trim();

        // Detect if first line looks like a chapter title pattern
        if first_line.starts_with("第") && first_line.contains('章') {
            meta.insert("detected_title".to_owned(), Json::String(first_line.to_owned()));
        }

        let metadata = if meta.is_empty() {
            None
        } else {
            Some(Json::Object(meta))
        };

        tracing::info!(
            content_len = content.chars().count(),
            has_meta = metadata.is_some(),
            "Response parsed"
        );

        Ok((content, metadata))
    }

    /// Step 9: Coherence validation — Groups A/B/C.
    ///
    /// Group A: narrative consistency (characters, plot)
    /// Group B: writing quality (style, grammar)
    /// Group C: continuity (with previous chapters)
    pub async fn step9_coherence_check(
        &self,
        _db: &DatabaseConnection,
        project: &ProjectModel,
        chapter: Option<&ChapterModel>,
        content: &str,
    ) -> AppResult<CoherenceResult> {
        let mut groups: Vec<CoherenceGroup> = Vec::new();

        // Group A — Narrative consistency
        let group_a = self
            .check_group_narrative_consistency(project, content)
            .await
            .unwrap_or_else(|e| {
                tracing::warn!(error = %e, "Group A check failed");
                CoherenceGroup {
                    group: "A".to_owned(),
                    passed: false,
                    score: 0.0,
                    issues: vec![format!("叙事一致性检查异常: {e}")],
                }
            });
        groups.push(group_a);

        // Group B — Writing quality (only if Group A passed)
        if groups.last().map(|g| g.passed).unwrap_or(false) || content.len() < 500 {
            let group_b = self
                .check_group_writing_quality(content)
                .await
                .unwrap_or_else(|e| {
                    tracing::warn!(error = %e, "Group B check failed");
                    CoherenceGroup {
                        group: "B".to_owned(),
                        passed: false,
                        score: 0.0,
                        issues: vec![format!("写作质量检查异常: {e}")],
                    }
                });
            groups.push(group_b);
        }

        // Group C — Continuity with previous chapters
        if let Some(ch) = chapter {
            let prev_content = ch.content.as_deref().unwrap_or("");
            let group_c = self
                .check_group_continuity(project, prev_content, content)
                .await
                .unwrap_or_else(|e| {
                    tracing::warn!(error = %e, "Group C check failed");
                    CoherenceGroup {
                        group: "C".to_owned(),
                        passed: false,
                        score: 0.0,
                        issues: vec![format!("连续性检查异常: {e}")],
                    }
                });
            groups.push(group_c);
        }

        let all_passed = groups.iter().all(|g| g.passed);
        let avg_score = if groups.is_empty() {
            1.0
        } else {
            groups.iter().map(|g| g.score).sum::<f64>() / groups.len() as f64
        };

        let issues: Vec<String> = groups
            .iter()
            .flat_map(|g| g.issues.iter().cloned())
            .collect();

        tracing::info!(
            passed = all_passed,
            score = avg_score,
            groups = groups.len(),
            issues = issues.len(),
            "Coherence check complete"
        );

        Ok(CoherenceResult {
            passed: all_passed,
            score: avg_score,
            version: "v2-grouped".to_owned(),
            issues,
            groups,
        })
    }

    /// Group A check: narrative consistency.
    async fn check_group_narrative_consistency(
        &self,
        project: &ProjectModel,
        content: &str,
    ) -> AppResult<CoherenceGroup> {
        let prompt = format!(
            "你是一位小说连贯性审查专家。\n\n\
             【作品】{title}（{genre}）\n\n\
             【新生成内容】\n{content}\n\n\
             请检查以下方面：\n\
             1. 角色行为是否一致\n\
             2. 情节是否有逻辑矛盾\n\
             3. 设定是否前后冲突\n\n\
             如无问题请回复「通过」。如有问题请逐一列出。",
            title = project.title,
            genre = project.genre,
        );

        let messages = vec![
            ChatMessage::system("你是一位小说结构专家，精通情节设计。请使用中文回答。"),
            ChatMessage::user(prompt),
        ];

        let api_key = self
            .get_api_key(Pool::Flash)
            .unwrap_or_else(|| "sk-placeholder".to_owned());

        let response = self
            .llm_client
            .chat(&messages, &api_key, self.model_name(), 0.3, 1024)
            .await
            .map_err(|e| AppError::internal(format!("Group A check failed: {e}")))?;

        let passed = response.contains("通过") && !response.contains("问题");
        let issues: Vec<String> = if passed {
            Vec::new()
        } else {
            response
                .lines()
                .filter(|l| l.trim().starts_with('-') || l.trim().starts_with("•"))
                .map(|l| l.trim().trim_start_matches('-').trim_start_matches('•').trim().to_owned())
                .filter(|s| !s.is_empty())
                .collect()
        };

        Ok(CoherenceGroup {
            group: "A".to_owned(),
            passed,
            score: if passed { 1.0 } else { 0.6 },
            issues,
        })
    }

    /// Group B check: writing quality.
    async fn check_group_writing_quality(&self, content: &str) -> AppResult<CoherenceGroup> {
        // Quick heuristic checks (no LLM call for performance)
        let mut issues: Vec<String> = Vec::new();

        // Check minimum length
        if content.chars().count() < 100 {
            issues.push("内容过短，可能不完整".to_owned());
        }

        // Check for excessive repetition
        let lines: Vec<&str> = content.lines().collect();
        if lines.len() > 10 {
            let mut repeat_count = 0;
            for i in 1..lines.len() {
                if lines[i].trim() == lines[i - 1].trim() && !lines[i].trim().is_empty() {
                    repeat_count += 1;
                }
            }
            if repeat_count > 2 {
                issues.push(format!("检测到{repeat_count}处连续重复行"));
            }
        }

        let passed = issues.is_empty();
        Ok(CoherenceGroup {
            group: "B".to_owned(),
            passed,
            score: if passed { 1.0 } else { 0.7 },
            issues,
        })
    }

    /// Group C check: continuity with previous chapter.
    async fn check_group_continuity(
        &self,
        _project: &ProjectModel,
        prev_content: &str,
        content: &str,
    ) -> AppResult<CoherenceGroup> {
        if prev_content.is_empty() {
            return Ok(CoherenceGroup {
                group: "C".to_owned(),
                passed: true,
                score: 1.0,
                issues: Vec::new(),
            });
        }

        // Truncate to avoid context overflow
        let prev_snippet: String = prev_content.chars().take(1000).collect();
        let new_snippet: String = content.chars().take(2000).collect();

        let prompt = format!(
            "你是一位小说连续性审查专家。\n\n\
             【前文结尾】\n{prev_snippet}\n\n\
             【新章开头】\n{new_snippet}\n\n\
             检查新章是否自然地接续了前文。重点检查：\n\
             1. 时间线是否连续\n\
             2. 场景切换是否合理\n\
             3. 角色状态是否一致\n\n\
             如无问题请回复「通过」。"
        );

        let messages = vec![
            ChatMessage::system("你是一位小说连续性审查专家。请使用中文回答。"),
            ChatMessage::user(prompt),
        ];

        let api_key = self
            .get_api_key(Pool::Flash)
            .unwrap_or_else(|| "sk-placeholder".to_owned());

        let response = self
            .llm_client
            .chat(&messages, &api_key, self.model_name(), 0.3, 512)
            .await
            .map_err(|e| AppError::internal(format!("Group C check failed: {e}")))?;

        let passed = response.contains("通过") && !response.contains("问题");
        let issues: Vec<String> = if passed {
            Vec::new()
        } else {
            response
                .lines()
                .filter(|l| l.trim().starts_with('-') || l.trim().starts_with("•"))
                .map(|l| l.trim().trim_start_matches('-').trim_start_matches('•').trim().to_owned())
                .filter(|s| !s.is_empty())
                .collect()
        };

        Ok(CoherenceGroup {
            group: "C".to_owned(),
            passed,
            score: if passed { 1.0 } else { 0.5 },
            issues,
        })
    }

    /// Step 10: Compute direction scores and detect conflicts.
    pub async fn step10_compute_direction_score(
        &self,
        cards: &[CardModel],
        weight_map: &HashMap<String, f64>,
        content: &str,
    ) -> AppResult<Vec<DirectionConflict>> {
        let mut conflicts: Vec<DirectionConflict> = Vec::new();

        // Check pairwise card direction conflicts
        for (i, card_a) in cards.iter().enumerate() {
            for card_b in cards.iter().skip(i + 1) {
                // Simple heuristic: if two cards have opposing direction types
                // (e.g., "conflict" vs "harmony"), flag as potential conflict
                let type_a = &card_a.direction_type;
                let type_b = &card_b.direction_type;

                let opposing_pairs: &[(&str, &str)] = &[
                    ("冲突", "和谐"),
                    ("悲剧", "喜剧"),
                    ("黑暗", "光明"),
                    ("紧张", "轻松"),
                    ("阴谋", "坦诚"),
                ];

                for (opp_a, opp_b) in opposing_pairs {
                    if (type_a.contains(opp_a) && type_b.contains(opp_b))
                        || (type_a.contains(opp_b) && type_b.contains(opp_a))
                    {
                        let wa = weight_map.get(&card_a.id).copied().unwrap_or(0.0);
                        let wb = weight_map.get(&card_b.id).copied().unwrap_or(0.0);
                        let severity = (wa * wb).sqrt().min(1.0);

                        conflicts.push(DirectionConflict {
                            card_a: card_a.name.clone(),
                            card_b: card_b.name.clone(),
                            conflict: format!(
                                "方向冲突：{}（{}）↔ {}（{}）",
                                card_a.name, type_a, card_b.name, type_b
                            ),
                            severity,
                        });
                        break;
                    }
                }
            }
        }

        // Content-based quick check: verify keywords from each card appear
        for card in cards {
            let name_in_content = content.contains(&card.name);
            let direction_words: Vec<&str> = card.direction_text.split(['，', '、', '。']).collect();
            let direction_coverage = direction_words
                .iter()
                .filter(|w| w.len() >= 2 && content.contains(*w))
                .count();

            if !name_in_content && direction_coverage == 0 {
                tracing::warn!(
                    card = %card.name,
                    "Card direction may not be reflected in content"
                );
            }
        }

        tracing::info!(conflicts = conflicts.len(), "Direction scoring complete");
        Ok(conflicts)
    }

    /// Step 11: Save generated chapter.
    pub async fn step11_save_chapter(
        &self,
        db: &DatabaseConnection,
        task: &GenTask,
        draft: &ChapterDraft,
    ) -> AppResult<Option<ChapterModel>> {
        let chapter_id = task
            .chapter_id
            .clone()
            .unwrap_or_else(|| Uuid::new_v4().to_string());

        // Check if chapter already exists
        let existing = self.chapter_dao.find_by_id(db, &chapter_id).await?;

        let chapter = if let Some(ch) = existing {
            // Update existing chapter
            tracing::info!(chapter_id = %ch.id, "Updating existing chapter");
            let mut active = ch.into_active_model();
            active.title = Set(draft.title.clone());
            active.content = Set(Some(draft.content.clone()));
            active.word_count = Set(draft.word_count);
            active.status = Set("completed".to_owned());
            active.used_card_ids = Set(Some(Json::Array(
                draft.used_card_ids.iter().map(|id| Json::String(id.clone())).collect(),
            )));
            active.generation_mode = Set(Some(draft.generation_mode.clone()));
            active.generation_prompt = Set(draft.generation_prompt.clone());
            active.generation_weights = Set(draft.generation_weights.clone());
            active.generation_result = Set(draft.generation_result.clone());
            active.update(db).await.map_err(|e| {
                AppError::internal(format!("保存章节失败: {e}"))
            })?
        } else {
            // Create new chapter
            tracing::info!(chapter_id = %chapter_id, "Creating new chapter");
            let model = moling_db::entities::chapter::ActiveModel {
                id: Set(chapter_id),
                project_id: Set(task.project_id),
                title: Set(draft.title.clone()),
                content: Set(Some(draft.content.clone())),
                chapter_number: Set(draft.chapter_number),
                status: Set("completed".to_owned()),
                word_count: Set(draft.word_count),
                used_card_ids: Set(Some(Json::Array(
                    draft.used_card_ids.iter().map(|id| Json::String(id.clone())).collect(),
                ))),
                generation_mode: Set(Some(draft.generation_mode.clone())),
                generation_prompt: Set(draft.generation_prompt.clone()),
                generation_weights: Set(draft.generation_weights.clone()),
                generation_result: Set(draft.generation_result.clone()),
                ..Default::default()
            };
            self.chapter_dao.create(db, model).await?
        };

        tracing::info!(
            chapter_id = %chapter.id,
            chapter_number = chapter.chapter_number,
            word_count = chapter.word_count,
            "Chapter saved"
        );

        Ok(Some(chapter))
    }

    /// Step 12: Phase4 vault update — create dynamic layer entry for this generation.
    pub async fn step12_update_phase4(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter: Option<&ChapterModel>,
    ) -> AppResult<()> {
        let Some(chapter) = chapter else {
            return Ok(());
        };

        let content = chapter.content.as_deref().unwrap_or("");
        if content.is_empty() {
            return Ok(());
        }

        // Generate summary via LLM
        let summary = self
            .generate_summary(content)
            .await
            .unwrap_or_else(|_| {
                content.chars().take(200).collect::<String>()
            });

        // Create dynamic layer entry
        let layer_id = Uuid::new_v4().to_string();
        let layer_model = moling_db::entities::dynamic_layer::ActiveModel {
            id: Set(layer_id),
            project_id: Set(project_id),
            chapter_id: Set(chapter.id.clone()),
            summary: Set(Some(summary)),
            anchor_pov: Set(None),
            anchor_location: Set(None),
            anchor_time: Set(None),
            must_hold: Set(None),
            must_not: Set(None),
            unresolved_hooks: Set(None),
            recent_changes: Set(None),
            information_asymmetry: Set(None),
            feasibility_score: Set(None),
            health_check: Set(None),
            ..Default::default()
        };

        self.dynamic_layer_dao
            .create(db, layer_model)
            .await?;

        tracing::info!(
            project_id,
            chapter_id = %chapter.id,
            "Phase4 dynamic layer updated"
        );

        Ok(())
    }

    // ------------------------------------------------------------------
    // Helpers for individual sub-steps
    // ------------------------------------------------------------------

    /// Generate a summary of the provided content via LLM.
    async fn generate_summary(&self, content: &str) -> AppResult<String> {
        let snippet: String = content.chars().take(3000).collect();
        let prompt = format!(
            "请为以下小说章节内容生成一个200字以内的前情摘要。\n\n内容：\n{snippet}\n\n请直接返回摘要，不要额外说明。"
        );

        let messages = vec![
            ChatMessage::system("你是一个专业的小说摘要助手。"),
            ChatMessage::user(prompt),
        ];

        let api_key = self
            .get_api_key(Pool::Flash)
            .unwrap_or_else(|| "sk-placeholder".to_owned());

        self.llm_client
            .chat(&messages, &api_key, self.model_name(), 0.3, 512)
            .await
            .map_err(|e| AppError::internal(format!("生成摘要失败: {e}")))
    }

    /// Adjust content based on coherence issues by re-prompting the LLM.
    async fn adjust_content(&self, content: &str, issues: &[String]) -> AppResult<String> {
        if issues.is_empty() {
            return Ok(content.to_owned());
        }

        let issues_text = issues
            .iter()
            .map(|i| format!("- {i}"))
            .collect::<Vec<_>>()
            .join("\n");

        // Truncate content to avoid context overflow
        let content_snippet: String = content.chars().take(4000).collect();

        let prompt = format!(
            "请对以下小说内容进行针对性修改，解决以下连贯性问题：\n\n\
             问题清单：\n{issues_text}\n\n\
             原文内容：\n{content_snippet}\n\n\
             请保持原内容的整体结构和风格，只修改有问题的部分。"
        );

        let messages = vec![
            ChatMessage::system("你是一个专业的小说编辑，擅长修改内容连贯性问题。"),
            ChatMessage::user(prompt),
        ];

        let api_key = self
            .get_api_key(Pool::Pro)
            .unwrap_or_else(|| "sk-placeholder".to_owned());

        self.llm_client
            .chat(&messages, &api_key, self.model_name(), 0.4, self.config.max_output_tokens)
            .await
            .map_err(|e| AppError::internal(format!("内容调整失败: {e}")))
    }

    // ------------------------------------------------------------------
    // Public API — task management
    // ------------------------------------------------------------------

    /// Get generation task status by ID.
    pub async fn get_task_status(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        task_id: &str,
    ) -> AppResult<GenTask> {
        let task = self
            .gen_dao
            .find_by_id(db, task_id)
            .await?
            .ok_or_else(AppError::generation_task_not_found)?;

        if task.user_id != user_id {
            return Err(AppError::project_access_denied());
        }

        Ok(task)
    }

    /// Cancel a pending or running generation task.
    pub async fn cancel_task(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        task_id: &str,
    ) -> AppResult<()> {
        let task = self
            .gen_dao
            .find_by_id(db, task_id)
            .await?
            .ok_or_else(AppError::generation_task_not_found)?;

        if task.user_id != user_id {
            return Err(AppError::project_access_denied());
        }

        if task.status != "pending" && task.status != "running" {
            return Err(AppError::bad_request(format!(
                "无法取消状态为 {} 的任务",
                task.status
            )));
        }

        let mut active = task.into_active_model();
        active.status = Set("cancelled".to_owned());
        active.progress_stage = Set(Some("cancelled".to_owned()));
        active.update(db).await.map_err(|e| {
            AppError::internal(format!("取消任务失败: {e}"))
        })?;

        tracing::info!(task_id, "Generation task cancelled");
        Ok(())
    }

    /// Get generation task history for a user.
    pub async fn get_history(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        page: u64,
        page_size: u64,
    ) -> AppResult<Vec<GenTask>> {
        // List by status "done" and filter by user
        let tasks = self
            .gen_dao
            .list_by_status(db, "done", page_size * page)
            .await?;

        let user_tasks: Vec<GenTask> = tasks
            .into_iter()
            .filter(|t| t.user_id == user_id)
            .skip(((page - 1) * page_size) as usize)
            .take(page_size as usize)
            .collect();

        Ok(user_tasks)
    }
}

impl Default for GenerationService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Supporting types
// ---------------------------------------------------------------------------

/// Assembled vault data for prompt building (Step 5 output).
#[derive(Debug, Clone)]
pub struct VaultFilteredData {
    /// Characters from the character vault.
    pub characters: Vec<VaultCharacterModel>,
    /// Plot promises (foreshadowing hooks).
    pub plot_promises: Vec<VaultPlotPromiseModel>,
    /// Timeline events.
    pub timeline: Vec<VaultTimelineModel>,
    /// World-building entries.
    pub world_entries: Vec<VaultWorldModel>,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generation_config_defaults() {
        let config = GenerationConfig::default();
        assert_eq!(config.max_retries, 3);
        assert_eq!(config.brainstorming_temperature, 0.8);
        assert_eq!(config.writing_temperature, 0.7);
        assert!(config.enable_coherence_check);
        assert!(config.auto_adjust);
    }

    #[test]
    fn test_generation_input_defaults() {
        let input = GenerationInput::default();
        assert_eq!(input.project_id, 0);
        assert!(input.chapter_id.is_none());
        assert!(input.card_ids.is_empty());
        assert_eq!(input.mode, "single");
    }

    #[test]
    fn test_coherence_result_serialization() {
        let result = CoherenceResult {
            passed: true,
            score: 0.95,
            version: "v2-grouped".to_owned(),
            issues: vec![],
            groups: vec![CoherenceGroup {
                group: "A".to_owned(),
                passed: true,
                score: 0.95,
                issues: vec![],
            }],
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("v2-grouped"));
        assert!(json.contains("passed"));
    }

    #[test]
    fn test_generation_service_constructs() {
        let _svc = GenerationService::new();
    }

    #[test]
    fn test_direction_conflict_serde() {
        let conflict = DirectionConflict {
            card_a: "A".to_owned(),
            card_b: "B".to_owned(),
            conflict: "方向冲突".to_owned(),
            severity: 0.7,
        };
        let json = serde_json::to_string(&conflict).unwrap();
        let back: DirectionConflict = serde_json::from_str(&json).unwrap();
        assert_eq!(back.card_a, "A");
        assert!((back.severity - 0.7).abs() < 0.001);
    }

    #[test]
    fn test_chapter_draft_default() {
        let draft = ChapterDraft {
            title: "第一章".to_owned(),
            content: "测试内容".to_owned(),
            chapter_number: 1,
            word_count: 4,
            used_card_ids: vec![],
            generation_mode: "single".to_owned(),
            generation_prompt: None,
            generation_weights: None,
            generation_result: None,
        };
        assert_eq!(draft.chapter_number, 1);
        assert_eq!(draft.title, "第一章");
    }

    #[test]
    fn test_step4_weight_allocation_uniform() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let svc = GenerationService::new();
            // Create test cards using the correct id type (String)
            let cards = vec![];
            let weights = HashMap::new();
            let result = svc.step4_weight_allocation(&cards, &weights).await.unwrap();
            assert!(result.is_empty());
        });
    }
}
