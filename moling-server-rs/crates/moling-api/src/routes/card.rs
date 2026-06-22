//! Card routes — draw, create, retire, pool, history.
//!
//! Delegates draw logic to [`moling_services::CardService`] for weighted
//! random selection with pity protection and freshness bonuses.

use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use moling_db::dao::card_dao::CardDao;
use moling_auth::CurrentUser;
use moling_services::CardService;
use sea_orm::Set;
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/cards/draw", post(draw_cards))
        .route("/cards", post(create_card))
        .route("/cards/{id}/retire", post(retire_card))
        .route("/cards/pool", get(get_pool))
        .route("/cards/history", get(get_history))
        .route("/cards/draw-history", get(list_draw_history))
        .route("/cards/draw-history/{draw_id}", get(get_draw_history_detail))
}

fn card_svc() -> CardService { CardService::new() }

/// POST /projects/{project_id}/cards/draw — draw cards with weighted random algorithm.
async fn draw_cards(
    State(state): State<AppState>,
    user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<DrawCardsReq>,
) -> AppResult<Json<serde_json::Value>> {
    let count = req.count.unwrap_or(3) as usize;
    let mode = req.mode.as_deref().unwrap_or("default");
    let result = card_svc().draw_cards(
        &state.db,
        &user.user_id.to_string(),
        project_id,
        count,
        mode,
        None,
        None,
    ).await?;
    Ok(Json(result))
}

async fn create_card(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
    Json(req): Json<CreateCardReq>,
) -> AppResult<Json<serde_json::Value>> {
    let dao = CardDao;
    let id = uuid::Uuid::new_v4().to_string();
    let model = moling_db::entities::card_pool::ActiveModel {
        id: Set(id), project_id: Set(project_id), name: Set(req.name),
        description: Set(req.description), rarity: Set(req.rarity),
        direction_type: Set(req.direction_type), direction_text: Set(req.direction_text),
        ..Default::default()
    };
    let c = dao.create_card(&state.db, model).await?;
    Ok(Json(serde_json::to_value(c).unwrap()))
}

async fn retire_card(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_pid, id)): Path<(i32, String)>,
) -> AppResult<Json<MessageResponse>> {
    let dao = CardDao;
    dao.retire_card(&state.db, &id, None).await?;
    Ok(Json(MessageResponse { message: "Card retired".into() }))
}

async fn get_pool(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let pool = CardDao.find_pool(&state.db, project_id).await?;
    Ok(Json(serde_json::to_value(pool).unwrap()))
}

/// GET /projects/{project_id}/cards/history — get recent draw history.
async fn get_history(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
) -> AppResult<Json<serde_json::Value>> {
    let history = CardDao.find_draw_history(&state.db, project_id, 50).await?;
    Ok(Json(serde_json::to_value(history).unwrap()))
}

/// GET /projects/{project_id}/cards/draw-history — paginated draw history.
async fn list_draw_history(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path(project_id): Path<i32>,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let limit = pg.page_size as u64;
    let offset = ((pg.page.saturating_sub(1)) as u64) * limit;
    // For simplicity, fetch all and paginate in-memory
    let all = CardDao.find_draw_history(&state.db, project_id, 200).await?;
    let total = all.len() as u64;
    let items: Vec<_> = all.into_iter().skip(offset as usize).take(limit as usize).collect();
    Ok(Json(serde_json::json!({ "items": items, "total": total, "page": pg.page, "page_size": pg.page_size })))
}

/// GET /projects/{project_id}/cards/draw-history/{draw_id} — single draw detail.
async fn get_draw_history_detail(
    State(state): State<AppState>,
    _user: CurrentUser,
    Path((_project_id, draw_id)): Path<(i32, String)>,
) -> AppResult<Json<serde_json::Value>> {
    use sea_orm::EntityTrait;
    let detail = moling_db::entities::draw_history::Entity::find_by_id(draw_id)
        .one(&state.db)
        .await
        .map_err(|_| AppError::internal("Database query failed".to_owned()))?
        .ok_or_else(|| AppError::not_found("Draw history not found".to_owned()))?;
    Ok(Json(serde_json::to_value(detail).unwrap()))
}
