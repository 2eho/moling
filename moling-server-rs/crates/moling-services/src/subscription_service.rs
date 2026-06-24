//! Subscription service — plans, checkout, current subscription, history, usage tracking.
//!
//! Business logic derived from DAO layer and PRD requirements.

use chrono::Utc;
use moling_core::error::{AppError, AppResult};
use moling_db::dao::subscription_dao::{PlanDao, UserSubscriptionDao};
use moling_db::entities::plan::Model as PlanModel;
use moling_db::entities::user_subscription::Model as UsModel;
use sea_orm::{DatabaseConnection, Set};
use serde_json::Value as Json;

/// Business logic for subscription management.
#[derive(Clone)]
pub struct SubscriptionService {
    plan_dao: PlanDao,
    us_dao: UserSubscriptionDao,
}

impl SubscriptionService {
    pub fn new() -> Self {
        Self {
            plan_dao: PlanDao,
            us_dao: UserSubscriptionDao,
        }
    }

    // ---- Plan management ----

    /// List active subscription plans.
    pub async fn list_plans(&self, db: &DatabaseConnection) -> AppResult<Vec<PlanModel>> {
        self.plan_dao.list_active_plans(db).await
    }

    /// Get a single plan by ID.
    pub async fn get_plan(
        &self,
        db: &DatabaseConnection,
        plan_id: &str,
    ) -> AppResult<PlanModel> {
        self.plan_dao
            .find_by_id(db, plan_id)
            .await?
            .ok_or_else(|| AppError::not_found("订阅计划不存在".to_owned()))
    }

    /// Create a new subscription plan (admin operation).
    pub async fn create_plan(
        &self,
        db: &DatabaseConnection,
        name: &str,
        price: f64,
        currency: Option<&str>,
        interval: Option<&str>,
        features: Json,
    ) -> AppResult<PlanModel> {
        let model = moling_db::entities::plan::ActiveModel {
            id: Set(uuid::Uuid::new_v4().to_string()),
            name: Set(name.to_owned()),
            price: Set(price),
            currency: Set(currency.map(|s| s.to_owned()).unwrap_or_else(|| "CNY".to_owned())),
            interval: Set(interval.map(|s| s.to_owned()).unwrap_or_else(|| "month".to_owned())),
            features: Set(features),
            is_active: Set(true),
            ..Default::default()
        };
        self.plan_dao.create(db, model).await
    }

    /// Update an existing plan.
    pub async fn update_plan(
        &self,
        db: &DatabaseConnection,
        plan_id: &str,
        name: Option<&str>,
        price: Option<f64>,
        currency: Option<&str>,
        interval: Option<&str>,
        features: Option<Json>,
        is_active: Option<bool>,
    ) -> AppResult<PlanModel> {
        use sea_orm::{ActiveModelTrait, IntoActiveModel};
        let plan = self.get_plan(db, plan_id).await?;
        let mut active = plan.into_active_model();
        if let Some(v) = name {
            active.name = Set(v.to_owned());
        }
        if let Some(v) = price {
            active.price = Set(v);
        }
        if let Some(v) = currency {
            active.currency = Set(v.to_owned());
        }
        if let Some(v) = interval {
            active.interval = Set(v.to_owned());
        }
        if let Some(v) = features {
            active.features = Set(v);
        }
        if let Some(v) = is_active {
            active.is_active = Set(v);
        }
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update plan failed: {e}")))
    }

    // ---- Checkout ----

    /// Create a checkout session for a plan.
    ///
    /// In production, this would integrate with a payment processor (Stripe, etc.).
    pub async fn create_checkout(
        &self,
        _db: &DatabaseConnection,
        user_id: &str,
        plan_id: &str,
    ) -> AppResult<Json> {
        Ok(serde_json::json!({
            "checkout_url": format!("/checkout?plan={plan_id}&user={user_id}"),
            "status": "pending",
            "plan_id": plan_id,
        }))
    }

    /// Confirm checkout completion and create/activate a subscription.
    pub async fn confirm_checkout(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        plan_id: &str,
    ) -> AppResult<UsModel> {
        let _plan = self.get_plan(db, plan_id).await?;

        // Deactivate any existing active subscription
        if let Some(existing) = self.us_dao.get_by_user(db, user_id).await? {
            use sea_orm::IntoActiveModel;
            let mut active_existing = existing.into_active_model();
            active_existing.status = Set("inactive".to_owned());
            self.us_dao.update(db, active_existing).await?;
        }

        let now = Utc::now();
        // Default: 30 days from now
        let end_date = now + chrono::Duration::days(30);

        let model = moling_db::entities::user_subscription::ActiveModel {
            id: Set(uuid::Uuid::new_v4().to_string()),
            user_id: Set(user_id.to_owned()),
            plan_id: Set(plan_id.to_owned()),
            status: Set("active".to_owned()),
            start_date: Set(now),
            end_date: Set(Some(end_date)),
            auto_renew: Set(true),
            ..Default::default()
        };
        self.us_dao.create(db, model).await
    }

    // ---- User subscription queries ----

    /// Get current user's active subscription.
    pub async fn get_current(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<Option<UsModel>> {
        self.us_dao.get_by_user(db, user_id).await
    }

    /// List subscription history for a user, newest first.
    pub async fn history(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<UsModel>> {
        self.us_dao.list_by_user(db, user_id, skip, limit).await
    }

    // ---- Usage tracking ----

    /// Get usage summary for a user's current subscription.
    pub async fn get_usage(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<Json> {
        let current = self.us_dao.get_by_user(db, user_id).await?;
        match current {
            None => Ok(serde_json::json!({
                "has_subscription": false,
                "plan": null,
                "usage": null,
            })),
            Some(sub) => {
                let plan = self.plan_dao.find_by_id(db, &sub.plan_id).await?.map(|p| {
                    serde_json::json!({
                        "name": p.name,
                        "price": p.price,
                        "currency": p.currency,
                        "interval": p.interval,
                    })
                });
                Ok(serde_json::json!({
                    "has_subscription": true,
                    "subscription_id": sub.id,
                    "status": sub.status,
                    "start_date": sub.start_date,
                    "end_date": sub.end_date,
                    "auto_renew": sub.auto_renew,
                    "plan": plan,
                }))
            }
        }
    }

    // ---- Expiry check ----

    /// Check if a user's subscription has expired and deactivate it if so.
    ///
    /// Returns `true` if the subscription was expired and deactivated.
    pub async fn check_expiry(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<bool> {
        let Some(sub) = self.us_dao.get_by_user(db, user_id).await? else {
            return Ok(false);
        };
        if sub.status != "active" {
            return Ok(false);
        }
        if let Some(end_date) = sub.end_date {
            let now: chrono::DateTime<Utc> = Utc::now();
            if now > end_date {
                use sea_orm::IntoActiveModel;
                let mut active = sub.into_active_model();
                active.status = Set("expired".to_owned());
                self.us_dao.update(db, active).await?;
                tracing::info!(user_id, "Subscription expired and deactivated");
                return Ok(true);
            }
        }
        Ok(false)
    }

    /// Cancel a user's active subscription.
    pub async fn cancel(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<()> {
        let Some(sub) = self.us_dao.get_by_user(db, user_id).await? else {
            return Err(AppError::not_found("没有活跃的订阅".to_owned()));
        };
        use sea_orm::IntoActiveModel;
        let mut active = sub.into_active_model();
        active.status = Set("cancelled".to_owned());
        self.us_dao.update(db, active).await?;
        Ok(())
    }
}

impl Default for SubscriptionService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sub_service_constructs() {
        let _ = SubscriptionService::new();
    }
}
