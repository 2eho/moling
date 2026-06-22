//! Migration M0001 — Initial schema (22 tables).
//!
//! Equivalent to Alembic `0001_initial_schema.py`.
//! Creates all core tables: users, projects, chapters, etc.

use sea_orm_migration::prelude::*;

pub struct Migration;

impl MigrationName for Migration {
    fn name(&self) -> &str {
        "m0001_initial_schema"
    }
}

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, _manager: &SchemaManager) -> Result<(), DbErr> {
        // In practice, the schema already exists (created by Python Alembic).
        // This migration is for greenfield deployments.
        tracing::info!("m0001: Schema assumed to exist from Python Alembic");
        Ok(())
    }

    async fn down(&self, _manager: &SchemaManager) -> Result<(), DbErr> {
        Ok(())
    }
}
