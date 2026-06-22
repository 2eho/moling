//! SeaORM entity for CardPool — mirrors Python `app/models/card_pool.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "card_pool")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    #[sea_orm(column_name = "project_id", indexed)]
    pub project_id: i32,
    #[sea_orm(column_name = "type")]
    pub r#type: Option<String>,
    #[sea_orm(default_value = r#""初始卡池""#)]
    pub source_label: String,
    #[sea_orm(default_value = "0")]
    pub pick_count: i32,
    pub last_drawn_chapter: Option<i32>,
    pub source_chapter: Option<i32>,
    pub tags: Option<Json>,
    #[sea_orm(default_value = "true")]
    pub is_active: bool,
    pub retired_chapter: Option<i32>,
    pub name: String,
    #[sea_orm(column_type = "Text")]
    pub description: String,
    pub rarity: String,
    pub direction_type: String,
    #[sea_orm(column_type = "Text")]
    pub direction_text: String,
    pub rarity_weight: Option<i32>,
    pub characters: Option<Json>,
    pub plot_promises: Option<Json>,
    pub timeline_point: Option<String>,
    pub world_rules: Option<Json>,
    #[sea_orm(column_type = "Text")]
    pub current_story_state: Option<String>,
    pub unresolved_hooks: Option<Json>,
    pub dynamic_conflict_score: Option<f64>,
    #[sea_orm(default_value = r#""active""#)]
    pub status: String,
    pub freshness_chapter: Option<i32>,
    #[sea_orm(default_value = "0")]
    pub draw_count: i32,
    pub remaining_lifetime: Option<i32>,
    pub embedding: Option<Json>,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
    #[sea_orm(default_value = "false", indexed)]
    pub is_deleted: bool,
    pub deleted_at: Option<DateTimeUtc>,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(
        belongs_to = "super::project::Entity",
        from = "Column::ProjectId",
        to = "super::project::Column::Id"
    )]
    Project,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::project::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Project.def()
    }
}
