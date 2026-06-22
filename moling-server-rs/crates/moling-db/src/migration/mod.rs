//! SeaORM migrations — equivalent to Alembic migration scripts.
//!
//! Migrations are applied in order:
//! 1. m0001_initial.rs — Initial schema (22 tables)
//! 2. m0002_ingest_jobs.rs — Ingest job tracking
//! 3. m0004_align_models.rs — Model alignment (no 0003)
//! 4. m0005_system_config.rs — System config created_at
//! 5. m0006_drop_status.rs — Drop Phase4 status column
//! 6. m0007_user_role.rs — User role column
//! 7. m0008_sub_plots.rs — Sub-plot tracking
//!
//! Note: These are for reference. In practice, we use the existing DB schema
//! and SeaORM auto-discovers the schema at runtime. Manual migrations are
//! only needed for new deployments.

pub mod m0001_initial;
pub mod m0002_ingest_jobs;
pub mod m0004_align_models;
pub mod m0004_m0008;
pub mod m0005_system_config;
pub mod m0006_drop_status;
pub mod m0007_user_role;
pub mod m0008_sub_plots;
