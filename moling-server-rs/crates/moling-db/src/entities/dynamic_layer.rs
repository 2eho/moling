//! SeaORM entity for DynamicLayer — mirrors Python `app/models/dynamic_layer.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "dynamic_layers")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    #[sea_orm(column_name = "project_id", indexed)]
    pub project_id: i32,
    #[sea_orm(column_name = "chapter_id", indexed)]
    pub chapter_id: String,
    #[sea_orm(column_type = "Text")]
    pub summary: Option<String>,
    pub anchor_pov: Option<String>,
    pub anchor_location: Option<String>,
    pub anchor_time: Option<String>,
    pub must_hold: Option<Json>,
    pub must_not: Option<Json>,
    pub unresolved_hooks: Option<Json>,
    pub recent_changes: Option<Json>,
    pub information_asymmetry: Option<Json>,
    pub feasibility_score: Option<f64>,
    pub health_check: Option<Json>,
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
        belongs_to = "super::chapter::Entity",
        from = "Column::ChapterId",
        to = "super::chapter::Column::Id",
        on_delete = "Cascade"
    )]
    Chapter,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::project::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Project.def()
    }
}

impl Related<super::chapter::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Chapter.def()
    }
}
