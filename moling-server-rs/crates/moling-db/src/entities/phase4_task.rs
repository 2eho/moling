//! SeaORM entity for Phase4Task — mirrors Python `app/models/phase4_task.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "phase4_tasks")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = true)]
    pub id: i32,
    #[sea_orm(unique, indexed)]
    pub nonce: String,
    #[sea_orm(column_name = "project_id", indexed)]
    pub project_id: i32,
    #[sea_orm(indexed)]
    pub chapter_id: String,
    #[sea_orm(default_value = r#""pending""#)]
    pub status: String,
    #[sea_orm(default_value = r#""idle""#)]
    pub state: String,
    #[sea_orm(column_type = "Text")]
    pub error_message: Option<String>,
    pub safety_check: Option<Json>,
    #[sea_orm(default_value = "0")]
    pub retry_count: i32,
    pub retry_at: Option<DateTimeUtc>,
    #[sea_orm(column_type = "Text")]
    pub last_error: Option<String>,
    pub started_at: Option<DateTimeUtc>,
    pub completed_at: Option<DateTimeUtc>,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {}

impl ActiveModelBehavior for ActiveModel {}
