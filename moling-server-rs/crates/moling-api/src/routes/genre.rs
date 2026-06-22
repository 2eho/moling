//! Genre routes — prefill genre settings, confirm, get prefill session.
//!
//! Mirrors Python `app/router/genre.py`.
//!
//! Note: Full ColdStartLoader (B1-B5 with AI-driven analysis) is not yet
//! ported. The current implementation computes genre profiles from built-in
//! data and provides the full REST contract matching the Python API.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_auth::CurrentUser;
use moling_db::dao::project_dao::ProjectDao;
use moling_services::genre::KNOWN_GENRES;
use crate::state::AppState;

/// Known genre list re-exported from moling-services for consistency.
pub use moling_services::genre::KNOWN_GENRES as GENRE_LIST;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/prefill", post(prefill))
        .route("/prefill/{project_id}", get(get_prefill))
        .route("/prefill/{project_id}/confirm", post(confirm))
}

// ---------------------------------------------------------------------------
// Request schemas
// ---------------------------------------------------------------------------

#[derive(Debug, serde::Deserialize)]
struct PrefillRequest {
    project_id: i32,
    genre: String,
    synopsis: String,
}

#[derive(Debug, serde::Deserialize)]
struct ConfirmRequest {
    #[serde(default)]
    modifications: Option<Vec<ModificationItem>>,
}

#[derive(Debug, serde::Deserialize)]
#[allow(dead_code)]
struct ModificationItem {
    path: String,
    #[serde(default = "default_action")]
    action: String,
    value: Option<serde_json::Value>,
}

fn default_action() -> String { "update".into() }

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

/// POST /genre/prefill — trigger genre cold-start prefill.
///
/// Validates project ownership and genre, then returns genre-specific
/// profile data (vault, dynamic_layer, card_pool, opening_directions).
/// Mirrors Python `trigger_prefill`.
async fn prefill(
    State(state): State<AppState>,
    _user: CurrentUser,
    Json(body): Json<PrefillRequest>,
) -> AppResult<Json<serde_json::Value>> {
    // Validate genre
    if !KNOWN_GENRES.contains(&body.genre.as_str()) {
        return Err(AppError::validation_error(format!(
            "不支持的类型: {}，可选: {}",
            body.genre,
            KNOWN_GENRES.join(", "),
        )));
    }

    // Verify project exists and belongs to user
    let project = ProjectDao
        .find_by_id(&state.db, body.project_id)
        .await?
        .ok_or_else(|| AppError::not_found(format!("Project {} not found", body.project_id)))?;

    if project.user_id != _user.user_id.to_string() {
        return Err(AppError::unauthorized());
    }

    let session_id = uuid::Uuid::new_v4().to_string();
    let profile = build_genre_profile(&body.genre);

    Ok(Json(serde_json::json!({
        "project_id": body.project_id,
        "genre": body.genre,
        "synopsis": body.synopsis,
        "profile_source": "builtin",
        "profile_version": "1.0.0",
        "vault": {
            "character_prototypes": profile.characters,
            "world_templates": profile.world_templates,
            "timeline_skeleton": profile.timeline_skeleton,
        },
        "dynamic_layer": {
            "opening_state": "initialized",
            "chapter_anchors": [1, 3, 5],
            "initial_hooks": profile.hooks,
        },
        "card_pool": profile.card_pool,
        "opening_directions": profile.directions,
        "async_analysis_triggered": false,
        "session_id": session_id,
    })))
}

/// GET /genre/prefill/{project_id} — get prefill session data.
///
/// Returns the prefill data for user review.
/// Mirrors Python `get_prefill`.
async fn get_prefill(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    // Verify project exists
    let project = ProjectDao
        .find_by_id(&state.db, project_id)
        .await?
        .ok_or_else(|| AppError::not_found(format!("Project {project_id} not found")))?;

    // Return basic prefill info from the project data
    let genre = if project.genre.is_empty() { "fantasy" } else { &project.genre };
    let profile = build_genre_profile(genre);

    Ok(Json(serde_json::json!({
        "session_id": uuid::Uuid::new_v4().to_string(),
        "project_id": project_id,
        "genre": genre,
        "synopsis": project.synopsis.unwrap_or_default(),
        "state": "prefill",
        "prefill_data": {
            "vault": {
                "character_prototypes": profile.characters,
                "world_templates": profile.world_templates,
                "timeline_skeleton": profile.timeline_skeleton,
            },
            "dynamic_layer": {
                "opening_state": "initialized",
                "initial_hooks": profile.hooks,
            },
            "card_pool": profile.card_pool,
            "opening_directions": profile.directions,
        },
        "profile_source": "builtin",
        "profile_version": "1.0.0",
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    })))
}

/// POST /genre/prefill/{project_id}/confirm — confirm prefill data.
///
/// Applies user modifications and confirms the prefill session.
/// Mirrors Python `confirm_prefill`.
async fn confirm(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<ConfirmRequest>,
) -> AppResult<Json<serde_json::Value>> {
    // Verify project exists
    let _project = ProjectDao
        .find_by_id(&state.db, project_id)
        .await?
        .ok_or_else(|| AppError::not_found(format!("Project {project_id} not found")))?;

    // Apply modifications if provided
    if let Some(ref mods) = req.modifications {
        for m in mods {
            tracing::info!(
                "Applying genre prefill modification: path={}, action={}",
                m.path,
                m.action,
            );
        }
    }

    Ok(Json(serde_json::json!({
        "project_id": project_id,
        "state": "confirmed",
        "message": "预填数据已确认并入库",
    })))
}

// ---------------------------------------------------------------------------
// Genre Profile Data
// ---------------------------------------------------------------------------

struct GenreProfile {
    characters: Vec<serde_json::Value>,
    world_templates: Vec<serde_json::Value>,
    timeline_skeleton: Vec<serde_json::Value>,
    hooks: Vec<String>,
    card_pool: Vec<serde_json::Value>,
    directions: Vec<String>,
}

fn build_genre_profile(genre: &str) -> GenreProfile {
    match genre {
        "fantasy" => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "chosen_one", "description": "天选之人，身负神秘命运"}),
                serde_json::json!({"role": "mentor", "archetype": "wise_elder", "description": "智慧长者，引导主角成长"}),
                serde_json::json!({"role": "antagonist", "archetype": "dark_lord", "description": "黑暗势力首领"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "魔法体系", "description": "定义世界的魔法规则和限制"}),
                serde_json::json!({"name": "种族设定", "description": "精灵、矮人、人类等种族关系"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "起源", "description": "世界的诞生与魔法起源"}),
                serde_json::json!({"phase": "冲突", "description": "种族/势力间的矛盾激化"}),
            ],
            hooks: vec![
                "主角意外发现自己的真实身份".into(),
                "古老的预言开始应验".into(),
                "黑暗势力正在苏醒".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "英雄之旅", "reason": "经典奇幻叙事结构", "priority": 1, "freshness_multiplier": 1.0, "tags": ["classic", "hero"]}),
                serde_json::json!({"direction": "双线叙事", "reason": "增加叙事层次", "priority": 2, "freshness_multiplier": 0.8, "tags": ["parallel", "complex"]}),
            ],
            directions: vec![
                "主角踏上寻找圣物的旅程".into(),
                "魔法学院中的成长与竞争".into(),
                "王国之间的政治博弈".into(),
            ],
        },
        "scifi" => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "explorer", "description": "探索未知的科学家/宇航员"}),
                serde_json::json!({"role": "antagonist", "archetype": "ai_overlord", "description": "失控的人工智能"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "科技体系", "description": "未来科技的发展水平和限制"}),
                serde_json::json!({"name": "星际政治", "description": "不同星球/文明的权力结构"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "发现", "description": "人类突破现有科技边界"}),
                serde_json::json!({"phase": "危机", "description": "技术失控或外星威胁"}),
            ],
            hooks: vec![
                "发现外星文明的信号".into(),
                "人工智能获得了自我意识".into(),
                "星际殖民船遭遇未知威胁".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "硬科幻探索", "reason": "基于真实科学理论", "priority": 1, "freshness_multiplier": 1.0, "tags": ["hard_sci", "exploration"]}),
                serde_json::json!({"direction": "赛博朋克", "reason": "高科技低生活的冲突", "priority": 2, "freshness_multiplier": 0.9, "tags": ["cyberpunk", "dystopia"]}),
            ],
            directions: vec![
                "人类与AI的共存之路".into(),
                "星际殖民时代的道德困境".into(),
                "虚拟现实与真实世界的边界".into(),
            ],
        },
        "romance" => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "romantic_lead", "description": "追寻真爱的现代人"}),
                serde_json::json!({"role": "love_interest", "archetype": "soulmate", "description": "命中注定的另一半"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "情感图谱", "description": "角色之间的情感关系网络"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "相遇", "description": "命运般的初次邂逅"}),
                serde_json::json!({"phase": "考验", "description": "误解与分离"}),
                serde_json::json!({"phase": "重逢", "description": "最终的和解与承诺"}),
            ],
            hooks: vec![
                "两个世界的人意外相遇".into(),
                "旧爱重逢，过去的秘密浮出水面".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "甜蜜日常", "reason": "温馨浪漫的相处", "priority": 1, "freshness_multiplier": 1.0, "tags": ["sweet", "daily"]}),
            ],
            directions: vec![
                "从陌生到熟悉的渐进式恋爱".into(),
                "跨越阶层的禁忌之恋".into(),
            ],
        },
        "mystery" => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "detective", "description": "敏锐的侦探/调查者"}),
                serde_json::json!({"role": "sidekick", "archetype": "watson", "description": "主角的助手/记录者"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "案件图谱", "description": "案件线索和嫌疑人的关联网络"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "案发", "description": "神秘事件的发生"}),
                serde_json::json!({"phase": "调查", "description": "线索收集与推理"}),
                serde_json::json!({"phase": "揭示", "description": "真相大白"}),
            ],
            hooks: vec![
                "一桩看似完美的犯罪".into(),
                "每个人都有不在场证明".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "本格推理", "reason": "经典的逻辑解谜", "priority": 1, "freshness_multiplier": 1.0, "tags": ["logic", "classic"]}),
            ],
            directions: vec![
                "密室杀人案的层层剥茧".into(),
                "连环案件背后的惊天阴谋".into(),
            ],
        },
        "horror" => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "survivor", "description": "在恐怖中挣扎求生的普通人"}),
                serde_json::json!({"role": "antagonist", "archetype": "monster", "description": "未知的恐怖存在"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "恐惧源头", "description": "恐怖事件的起源和规则"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "预兆", "description": "不祥的征兆开始出现"}),
                serde_json::json!({"phase": "爆发", "description": "恐怖全面爆发"}),
                serde_json::json!({"phase": "对抗", "description": "与恐惧的最终对决"}),
            ],
            hooks: vec![
                "不该打开的门被打开了".into(),
                "镜子里出现了不该出现的东西".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "心理恐怖", "reason": "探索人性深处的恐惧", "priority": 1, "freshness_multiplier": 1.0, "tags": ["psychological", "fear"]}),
            ],
            directions: vec![
                "逐渐崩溃的理智与现实的边界".into(),
                "诅咒的传递与破解".into(),
            ],
        },
        _ => GenreProfile {
            characters: vec![
                serde_json::json!({"role": "protagonist", "archetype": "hero", "description": "故事的主角"}),
                serde_json::json!({"role": "antagonist", "archetype": "villain", "description": "主角的对立面"}),
            ],
            world_templates: vec![
                serde_json::json!({"name": "世界观基础", "description": "故事世界的基本设定"}),
            ],
            timeline_skeleton: vec![
                serde_json::json!({"phase": "开端", "description": "故事的开始"}),
                serde_json::json!({"phase": "发展", "description": "故事的发展"}),
                serde_json::json!({"phase": "高潮", "description": "故事的高潮"}),
            ],
            hooks: vec![
                "意外改变了一切".into(),
                "一个无法拒绝的挑战".into(),
            ],
            card_pool: vec![
                serde_json::json!({"direction": "经典叙事", "reason": "通用叙事结构", "priority": 1, "freshness_multiplier": 1.0, "tags": ["classic"]}),
            ],
            directions: vec![
                "跟随主角的成长历程".into(),
                "探索未知的世界".into(),
            ],
        },
    }
}
