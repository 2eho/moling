//! Data Access Objects — type-safe database query layer.
//!
//! Each DAO wraps SeaORM entity operations with domain-specific queries
//! and automatic soft-delete filtering.

use moling_core::error::AppResult;
use moling_core::types::Pagination;
use sea_orm::{DatabaseConnection, EntityTrait};

/// Generic CRUD operations for any SeaORM entity.
#[async_trait::async_trait]
#[allow(async_fn_in_trait)]
pub trait BaseDao<E>
where
    E: EntityTrait,
    E::Model: Send + Sync,
{
    /// Find entity by primary key.
    async fn find_by_id(&self, db: &DatabaseConnection, id: &str) -> AppResult<Option<E::Model>>;

    /// Find all entities with pagination and optional soft-delete filtering.
    async fn find_all(
        &self,
        db: &DatabaseConnection,
        pagination: &Pagination,
    ) -> AppResult<Vec<E::Model>>;

    /// Insert a new entity.
    async fn create(&self, db: &DatabaseConnection, model: E::ActiveModel) -> AppResult<E::Model>;

    /// Update an existing entity.
    async fn update(&self, db: &DatabaseConnection, model: E::ActiveModel) -> AppResult<E::Model>;

    /// Hard-delete an entity.
    async fn delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<u64>;

    /// Count total entities (optionally excluding soft-deleted).
    async fn count(&self, db: &DatabaseConnection) -> AppResult<u64>;
}

/// Marker trait for entities that support soft-delete via `is_deleted` column.
#[allow(async_fn_in_trait)]
pub trait SoftDeletableDao {
    /// Soft-delete: set `is_deleted = true` and `deleted_at = now()`.
    async fn soft_delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()>;
}

pub mod card_dao;
pub mod chapter_dao;
pub mod dynamic_layer_dao;
pub mod generation_dao;
pub mod health_alert_dao;
pub mod ingest_dao;
pub mod notification_dao;
pub mod phase4_dao;
pub mod project_dao;
pub mod secret_dao;
pub mod subscription_dao;
pub mod system_config_dao;
pub mod template_dao;
pub mod user_dao;
pub mod vault_dao;
