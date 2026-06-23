use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};

/// Immutable audit trail for system_config changes.
/// Written by `SystemConfigDao::upsert_versioned` on every value change.
#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "system_config_audit")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: i64,

    pub config_key: String,
    pub version: i32,
    pub old_value: Option<String>,
    pub new_value: String,
    pub changed_by: Option<String>,

    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub changed_at: DateTimeUtc,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {}

impl ActiveModelBehavior for ActiveModel {}
