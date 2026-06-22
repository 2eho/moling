//! Migration stubs for remaining Alembic equivalents (m0004-m0008).
//! All assume the schema already exists from Python Alembic.

use sea_orm_migration::prelude::*;

macro_rules! stub_migration {
    ($name:ident, $label:expr) => {
        pub struct $name;

        impl MigrationName for $name {
            fn name(&self) -> &str { $label }
        }

        #[async_trait::async_trait]
        impl MigrationTrait for $name {
            async fn up(&self, _manager: &SchemaManager) -> Result<(), DbErr> {
                tracing::info!(concat!($label, ": Schema assumed to exist"));
                Ok(())
            }
            async fn down(&self, _manager: &SchemaManager) -> Result<(), DbErr> { Ok(()) }
        }
    };
}

stub_migration!(M0004AlignModels, "m0004_align_models");
stub_migration!(M0005SystemConfig, "m0005_system_config");
stub_migration!(M0006DropStatus, "m0006_drop_status");
stub_migration!(M0007UserRole, "m0007_user_role");
stub_migration!(M0008SubPlots, "m0008_sub_plots");
