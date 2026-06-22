//! Health Alert DAO — health check alert CRUD and resolution.

use chrono::Utc;
use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, QueryFilter, QueryOrder, Set};

use crate::entities::health_alert::{self, ActiveModel, Entity as HealthAlert, Model as HealthAlertModel};

/// Health alert data access object.
#[derive(Clone, Default)]
pub struct HealthAlertDao;

impl HealthAlertDao {
    /// Find a health alert by ID.
    pub async fn find_by_id(
        &self,
        db: &DatabaseConnection,
        id: i32,
    ) -> AppResult<Option<HealthAlertModel>> {
        HealthAlert::find_by_id(id)
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "HealthAlert: database error finding by id: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all health alerts for a project, newest first.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<HealthAlertModel>> {
        HealthAlert::find()
            .filter(health_alert::Column::ProjectId.eq(project_id))
            .order_by_desc(health_alert::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "HealthAlert: database error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List active (unresolved) health alerts for a project.
    pub async fn list_active_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<HealthAlertModel>> {
        HealthAlert::find()
            .filter(health_alert::Column::ProjectId.eq(project_id))
            .filter(health_alert::Column::IsActive.eq(true))
            .order_by_desc(health_alert::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "HealthAlert: database error listing active: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List alerts filtered by severity (info / warning / critical).
    pub async fn list_by_severity(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        severity: &str,
    ) -> AppResult<Vec<HealthAlertModel>> {
        HealthAlert::find()
            .filter(health_alert::Column::ProjectId.eq(project_id))
            .filter(health_alert::Column::Severity.eq(severity))
            .order_by_desc(health_alert::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %severity, "HealthAlert: database error listing by severity: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Create a new health alert.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        model: ActiveModel,
    ) -> AppResult<HealthAlertModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("HealthAlert: database error creating: {e}");
            AppError::internal("Database insert failed")
        })
    }

    /// Mark all active alerts for a given rule as resolved.
    /// Returns the number of alerts updated.
    pub async fn resolve_by_rule(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        rule: &str,
    ) -> AppResult<u64> {
        use sea_orm::sea_query::Expr;
        let result = HealthAlert::update_many()
            .filter(health_alert::Column::ProjectId.eq(project_id))
            .filter(health_alert::Column::Rule.eq(rule))
            .filter(health_alert::Column::IsActive.eq(true))
            .col_expr(health_alert::Column::IsActive, Expr::value(false))
            .exec(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %rule, "HealthAlert: database error resolving by rule: {e}");
                AppError::internal("Database update failed")
            })?;
        Ok(result.rows_affected)
    }

    /// Update the checked_at timestamp for a specific alert.
    pub async fn update_checked_at(
        &self,
        db: &DatabaseConnection,
        alert_id: i32,
    ) -> AppResult<()> {
        let entity = self.find_by_id(db, alert_id).await?.ok_or_else(|| {
            AppError::not_found("健康告警不存在")
        })?;

        use sea_orm::IntoActiveModel;
        let mut active = entity.into_active_model();
        active.checked_at = Set(Some(Utc::now().into()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%alert_id, "HealthAlert: database error updating checked_at: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }
}
