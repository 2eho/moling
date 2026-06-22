//! Subscription DAO — plan and user subscription data access.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, QuerySelect};

use crate::entities::plan::{self, ActiveModel as PlanActiveModel, Entity as Plan, Model as PlanModel};
use crate::entities::user_subscription::{
    self, ActiveModel as UsActiveModel, Entity as UserSubscription, Model as UserSubscriptionModel,
};

/// Subscription plan data access object.
#[derive(Clone, Default)]
pub struct PlanDao;

impl PlanDao {
    /// List all active (published) plans ordered by price.
    pub async fn list_active_plans(
        &self,
        db: &DatabaseConnection,
    ) -> AppResult<Vec<PlanModel>> {
        Plan::find()
            .filter(plan::Column::IsActive.eq(true))
            .order_by_asc(plan::Column::Price)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!("Plan: database error listing active plans: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a plan by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<PlanModel>> {
        Plan::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Plan: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new plan.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: PlanActiveModel,
    ) -> AppResult<PlanModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Plan: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing plan.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: PlanActiveModel,
    ) -> AppResult<PlanModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Plan: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }
}

/// User subscription data access object.
#[derive(Clone, Default)]
pub struct UserSubscriptionDao;

impl UserSubscriptionDao {
    /// Get the active subscription for a user.
    pub async fn get_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<Option<UserSubscriptionModel>> {
        UserSubscription::find()
            .filter(user_subscription::Column::UserId.eq(user_id))
            .filter(user_subscription::Column::Status.eq("active"))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, "UserSubscription: database error finding active: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get a specific user-plan subscription record.
    pub async fn get_by_user_and_plan(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        plan_id: &str,
    ) -> AppResult<Option<UserSubscriptionModel>> {
        UserSubscription::find()
            .filter(user_subscription::Column::UserId.eq(user_id))
            .filter(user_subscription::Column::PlanId.eq(plan_id))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, %plan_id, "UserSubscription: database error finding by user and plan: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all subscriptions for a user, newest first.
    pub async fn list_by_user(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<UserSubscriptionModel>> {
        UserSubscription::find()
            .filter(user_subscription::Column::UserId.eq(user_id))
            .order_by_desc(user_subscription::Column::StartDate)
            .offset(skip)
            .limit(limit)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(user_id, "UserSubscription: database error listing by user: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Find a subscription by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<UserSubscriptionModel>> {
        UserSubscription::find_by_id(id.to_owned())
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "UserSubscription: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new user subscription.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: UsActiveModel,
    ) -> AppResult<UserSubscriptionModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("UserSubscription: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Update an existing user subscription.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        model: UsActiveModel,
    ) -> AppResult<UserSubscriptionModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("UserSubscription: database error updating: {e}");
            AppError::internal("Database update failed")
        })
    }
}
