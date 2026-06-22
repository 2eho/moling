//! SeaORM entity for IngestJob — mirrors Python `app/ingest/models.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "ingest_jobs")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: String,

    #[sea_orm(indexed)]
    pub project_id: i32,

    #[sea_orm(indexed)]
    pub user_id: String,

    pub source_type: String,
    pub source_url: Option<String>,

    #[sea_orm(default_value = "")]
    pub title: String,

    #[sea_orm(default_value = "0")]
    pub total_chapters: i32,

    #[sea_orm(default_value = r#""phase0""#)]
    pub current_phase: String,

    pub phase0_result: Option<Json>,
    pub phase1_result: Option<Json>,
    pub phase2_result: Option<Json>,
    pub phase3_result: Option<Json>,

    #[sea_orm(default_value = "0.0")]
    pub progress_percent: f64,

    #[sea_orm(column_type = "Text")]
    pub error_message: Option<String>,

    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,

    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(
        belongs_to = "super::project::Entity",
        from = "Column::ProjectId",
        to = "super::project::Column::Id",
        on_delete = "Cascade"
    )]
    Project,
    #[sea_orm(
        belongs_to = "super::user::Entity",
        from = "Column::UserId",
        to = "super::user::Column::Id",
        on_delete = "Cascade"
    )]
    User,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::project::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Project.def()
    }
}

impl Related<super::user::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::User.def()
    }
}
