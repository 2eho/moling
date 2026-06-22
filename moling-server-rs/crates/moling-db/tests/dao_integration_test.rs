//! Integration tests for moling-db DAOs — compile-time type validation.
//!
//! Verifies that all 10 new DAO structs, their methods, and ActiveModel
//! builders compile correctly against their SeaORM entities.

use moling_db::dao::dynamic_layer_dao::DynamicLayerDao;
use moling_db::dao::generation_dao::GenerationDao;
use moling_db::dao::health_alert_dao::HealthAlertDao;
use moling_db::dao::ingest_dao::IngestDao;
use moling_db::dao::notification_dao::NotificationDao;
use moling_db::dao::phase4_dao::Phase4Dao;
use moling_db::dao::secret_dao::SecretDao;
use moling_db::dao::subscription_dao::{PlanDao, UserSubscriptionDao};
use moling_db::dao::system_config_dao::SystemConfigDao;
use moling_db::dao::template_dao::TemplateDao;
use moling_db::entities::{
    dynamic_layer, generation_task, health_alert, ingest_job,
    notification, phase4_task, plan, secret, system_config,
    template, user_subscription,
};
use sea_orm::Set;

// =========================================================================
// SecretDao
// =========================================================================

#[test]
fn test_secret_dao_compile() {
    let _dao = SecretDao;
    let _model = secret::ActiveModel {
        id: Set("s-1".into()),
        project_id: Set(1),
        description: Set("test".into()),
        known_by: Set(serde_json::json!([])),
        unknown_to: Set(serde_json::json!([])),
        secrecy_level: Set("hidden".into()),
        debt: Set(0),
        ..Default::default()
    };
}

// =========================================================================
// GenerationDao
// =========================================================================

#[test]
fn test_generation_dao_compile() {
    let _dao = GenerationDao;
    let _model = generation_task::ActiveModel {
        id: Set(uuid::Uuid::new_v4()),
        project_id: Set(1),
        user_id: Set("user-1".into()),
        task_type: Set("generate_chapter".into()),
        status: Set("pending".into()),
        input_params: Set(serde_json::json!({})),
        ..Default::default()
    };
}

// =========================================================================
// HealthAlertDao
// =========================================================================

#[test]
fn test_health_alert_dao_compile() {
    let _dao = HealthAlertDao;
    let _model = health_alert::ActiveModel {
        project_id: Set(1),
        rule: Set("debt_over_10".into()),
        title: Set("Test Alert".into()),
        detail: Set("Details".into()),
        severity: Set("warning".into()),
        ..Default::default()
    };
}

// =========================================================================
// NotificationDao
// =========================================================================

#[test]
fn test_notification_dao_compile() {
    let _dao = NotificationDao;
    let _model = notification::ActiveModel {
        user_id: Set("user-1".into()),
        r#type: Set("info".into()),
        title: Set("Test Notification".into()),
        ..Default::default()
    };
}

// =========================================================================
// TemplateDao
// =========================================================================

#[test]
fn test_template_dao_compile() {
    let _dao = TemplateDao;
    let _model = template::ActiveModel {
        id: Set("tmpl-1".into()),
        name: Set("Test Template".into()),
        description: Set("A test".into()),
        genre: Set("fantasy".into()),
        ..Default::default()
    };
}

// =========================================================================
// SubscriptionDao (Plan + UserSubscription)
// =========================================================================

#[test]
fn test_subscription_dao_compile() {
    let _plan_dao = PlanDao;
    let _us_dao = UserSubscriptionDao;

    let _plan = plan::ActiveModel {
        id: Set("plan-1".into()),
        name: Set("Pro".into()),
        price: Set(29.99),
        features: Set(serde_json::json!({"chapters": 100})),
        ..Default::default()
    };

    let _us = user_subscription::ActiveModel {
        id: Set("us-1".into()),
        user_id: Set("user-1".into()),
        plan_id: Set("plan-1".into()),
        ..Default::default()
    };
}

// =========================================================================
// Phase4Dao
// =========================================================================

#[test]
fn test_phase4_dao_compile() {
    let _dao = Phase4Dao;
    let _model = phase4_task::ActiveModel {
        nonce: Set("nonce-123".into()),
        project_id: Set(1),
        chapter_id: Set("ch-1".into()),
        status: Set("pending".into()),
        state: Set("idle".into()),
        ..Default::default()
    };
}

// =========================================================================
// DynamicLayerDao
// =========================================================================

#[test]
fn test_dynamic_layer_dao_compile() {
    let _dao = DynamicLayerDao;
    let _model = dynamic_layer::ActiveModel {
        id: Set("dl-1".into()),
        project_id: Set(1),
        chapter_id: Set("ch-1".into()),
        summary: Set(Some("Chapter summary".into())),
        ..Default::default()
    };
}

// =========================================================================
// IngestDao
// =========================================================================

#[test]
fn test_ingest_dao_compile() {
    let _dao = IngestDao;
    let _model = ingest_job::ActiveModel {
        id: Set("ing-1".into()),
        project_id: Set(1),
        user_id: Set("user-1".into()),
        source_type: Set("url".into()),
        title: Set("Test Ingest".into()),
        ..Default::default()
    };
}

// =========================================================================
// SystemConfigDao
// =========================================================================

#[test]
fn test_system_config_dao_compile() {
    let _dao = SystemConfigDao;
    let _model = system_config::ActiveModel {
        key: Set("llm_api_key".into()),
        value: Set("sk-12345".into()),
        description: Set(Some("LLM API Key".into())),
        ..Default::default()
    };
}
