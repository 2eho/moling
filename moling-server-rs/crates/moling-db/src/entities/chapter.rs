//! SeaORM entity for Chapter — mirrors Python `app/models/chapter.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "chapters")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    #[sea_orm(column_name = "project_id", indexed)]
    pub project_id: i32,
    pub title: String,
    #[sea_orm(column_type = "Text")]
    pub content: Option<String>,
    pub chapter_number: i32,
    #[sea_orm(default_value = r#""draft""#)]
    pub status: String,
    #[sea_orm(default_value = r#""pending""#)]
    pub phase4_status: String,
    #[sea_orm(default_value = "0")]
    pub word_count: i32,
    pub confirmed_at: Option<DateTimeUtc>,
    pub used_card_ids: Option<Json>,
    pub generation_mode: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub generation_prompt: Option<String>,
    pub generation_weights: Option<Json>,
    #[sea_orm(column_type = "Text")]
    pub generation_result: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub error_message: Option<String>,
    #[sea_orm(default_value = "0")]
    pub retry_count: i32,
    pub generation_duration: Option<i32>,
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
    #[sea_orm(has_many = "super::dynamic_layer::Entity")]
    DynamicLayer,
    #[sea_orm(has_many = "super::generation_task::Entity")]
    GenerationTask,
    #[sea_orm(has_many = "super::draw_history::Entity")]
    DrawHistory,
    #[sea_orm(has_many = "super::vault_changelog::Entity")]
    VaultChangelog,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::project::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Project.def()
    }
}
