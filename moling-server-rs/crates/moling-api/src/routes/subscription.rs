//! Subscription routes — plans, checkout, create, current subscription, payment history.
//!
//! Mirrors Python `app/router/subscription.py`.

use axum::{
    extract::{Query, State},
    routing::{get, post},
    Json, Router,
};
use moling_core::error::{AppError, AppResult};
use sea_orm::PaginatorTrait;
use moling_db::dao::subscription_dao::{PlanDao, UserSubscriptionDao};
use moling_auth::CurrentUser;
use sea_orm::{ColumnTrait, EntityTrait, QueryFilter};
use crate::state::AppState;
use crate::types::*;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/plans", get(list_plans))
        .route("/create-checkout", post(create_checkout))
        .route("/", post(create_subscription))
        .route("/current", get(get_current))
        .route("/history", get(get_history))
        .route("/payment-history", get(get_payment_history))
}

/// GET /subscriptions/plans — list available subscription plans.
///
/// Mirrors Python `list_plans`.
async fn list_plans(
    State(state): State<AppState>,
) -> AppResult<Json<serde_json::Value>> {
    let plans = PlanDao.list_active_plans(&state.db).await?;
    Ok(Json(serde_json::to_value(plans)?))
}

/// POST /subscriptions/create-checkout — create a payment checkout session.
///
/// Verifies the plan exists before returning checkout data.
/// Mirrors Python `create_checkout`.
async fn create_checkout(
    State(state): State<AppState>,
    _user: CurrentUser,
    Query(req): Query<CreateCheckoutReq>,
) -> AppResult<Json<serde_json::Value>> {
    let plan = PlanDao
        .find_by_id(&state.db, &req.plan_id)
        .await?
        .ok_or_else(|| AppError::not_found("订阅计划不存在".to_owned()))?;

    let checkout_id = uuid::Uuid::new_v4().to_string();
    Ok(Json(serde_json::json!({
        "checkout_id": checkout_id,
        "checkout_url": format!("/checkout/{}", checkout_id),
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "price": plan.price,
            "currency": plan.currency,
            "interval": plan.interval,
        },
        "status": "pending",
        "message": "请前往支付页面完成付款",
    })))
}

/// POST /subscriptions/ — create a new subscription for the current user.
///
/// Checks for existing active subscription, validates the plan,
/// calculates end date, and creates the subscription.
/// Mirrors Python `create_subscription`.
async fn create_subscription(
    State(state): State<AppState>,
    user: CurrentUser,
    Json(req): Json<CreateSubscriptionReq>,
) -> AppResult<Json<serde_json::Value>> {
    let user_id = user.user_id.to_string();

    // Check if user already has an active subscription
    if let Some(existing) = UserSubscriptionDao.get_by_user(&state.db, &user_id).await?
        && existing.status == "active" {
            return Err(AppError::validation_error("您已有活跃的订阅".to_owned()));
        }

    // Verify plan exists
    let plan = PlanDao
        .find_by_id(&state.db, &req.plan_id)
        .await?
        .ok_or_else(|| AppError::not_found("订阅计划不存在".to_owned()))?;

    let now = chrono::Utc::now();
    let days = match plan.interval.as_str() {
        "year" => 365,
        "month" => 30,
        _ => 30,
    };
    let end_date = now + chrono::Duration::days(days);

    use sea_orm::Set;
    let model = moling_db::entities::user_subscription::ActiveModel {
        id: Set(uuid::Uuid::new_v4().to_string()),
        user_id: Set(user_id),
        plan_id: Set(req.plan_id),
        status: Set("active".to_owned()),
        start_date: Set(now),
        end_date: Set(Some(end_date)),
        auto_renew: Set(req.auto_renew.unwrap_or(true)),
        ..Default::default()
    };

    let sub = UserSubscriptionDao.create(&state.db, model).await?;
    Ok(Json(serde_json::to_value(sub)?))
}

/// GET /subscriptions/current — get current user's subscription.
///
/// Mirrors Python `get_current_subscription`.
async fn get_current(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let sub = UserSubscriptionDao
        .get_by_user(&state.db, &user.user_id.to_string())
        .await?;

    match sub {
        None => Ok(Json(serde_json::json!({
            "has_subscription": false,
            "subscription": null,
        }))),
        Some(s) => Ok(Json(serde_json::json!({
            "has_subscription": true,
            "subscription": serde_json::to_value(s)?,
        }))),
    }
}

/// GET /subscriptions/history — list subscription history (simple).
///
/// Returns all subscriptions for the user, newest first.
async fn get_history(
    State(state): State<AppState>,
    user: CurrentUser,
) -> AppResult<Json<serde_json::Value>> {
    let history = UserSubscriptionDao
        .list_by_user(&state.db, &user.user_id.to_string(), 0, 20)
        .await?;
    Ok(Json(serde_json::to_value(history)?))
}

/// GET /subscriptions/payment-history — paginated payment history.
///
/// Mirrors Python `get_payment_history`.
async fn get_payment_history(
    State(state): State<AppState>,
    user: CurrentUser,
    Query(pg): Query<PaginationQuery>,
) -> AppResult<Json<serde_json::Value>> {
    let skip = (pg.page as u64 - 1) * pg.page_size as u64;
    let subscriptions = UserSubscriptionDao
        .list_by_user(&state.db, &user.user_id.to_string(), skip, pg.page_size as u64)
        .await?;
    let total: u64 = moling_db::entities::user_subscription::Entity::find()
        .filter(moling_db::entities::user_subscription::Column::UserId.eq(user.user_id.to_string()))
        .count(&state.db)
        .await
        .unwrap_or(0);

    let items: Vec<serde_json::Value> = subscriptions
        .iter()
        .map(|sub| {
            serde_json::json!({
                "id": sub.id,
                "plan_id": sub.plan_id,
                "status": sub.status,
                "amount": 0.0,
                "currency": "CNY",
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "auto_renew": sub.auto_renew,
                "created_at": sub.created_at,
            })
        })
        .collect();

    Ok(Json(serde_json::json!({
        "items": items,
        "total": total,
        "page": pg.page,
        "page_size": pg.page_size,
    })))
}
