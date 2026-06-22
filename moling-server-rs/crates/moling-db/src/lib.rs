//! 墨灵 (Moling) — Database layer.
//!
//! Provides SeaORM entities, DAO (Data Access Object) implementations,
//! connection pool management, and database migrations.
//!
//! # Architecture
//!
//! - `entities/` — SeaORM ActiveModel/Entity definitions matching the
//!   existing PostgreSQL schema (22+ tables).
//! - `dao/` — Type-safe data access objects with CRUD, soft-delete,
//!   pagination, and domain-specific queries.
//! - `pool.rs` — Async connection pool with health-check support.
//! - `migration/` — SeaORM migrations (equivalent to 8 Alembic scripts).

pub mod dao;
pub mod entities;
pub mod migration;
pub mod pool;
