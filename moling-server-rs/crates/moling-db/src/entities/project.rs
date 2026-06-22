//! SeaORM entity for Project — mirrors Python `app/models/project.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "projects")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = true)]
    pub id: i32,
    #[sea_orm(column_name = "user_id", indexed)]
    pub user_id: String,
    pub title: String,
    pub author: String,
    pub genre: String,
    pub tags: Option<Json>,
    pub synopsis: Option<String>,
    pub worldview: Option<String>,
    pub protagonist: Option<String>,
    pub supporting_chars: Option<Json>,
    #[sea_orm(default_value = "0")]
    pub word_count: i32,
    pub target_words: Option<i32>,
    pub frequency: Option<String>,
    pub style: Option<String>,
    #[sea_orm(default_value = r#""draft""#)]
    pub status: String,
    #[sea_orm(default_value = r#""from_scratch""#)]
    pub creation_mode: String,
    pub template_id: Option<i32>,
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
        belongs_to = "super::user::Entity",
        from = "Column::UserId",
        to = "super::user::Column::Id"
    )]
    User,
    #[sea_orm(has_many = "super::chapter::Entity")]
    Chapter,
    #[sea_orm(has_many = "super::generation_task::Entity")]
    GenerationTask,
    #[sea_orm(has_many = "super::draw_history::Entity")]
    DrawHistory,
    #[sea_orm(has_many = "super::health_alert::Entity")]
    HealthAlert,
    #[sea_orm(has_many = "super::secret::Entity")]
    Secret,
    #[sea_orm(has_many = "super::notification::Entity")]
    Notification,
    #[sea_orm(has_many = "super::card_pool::Entity")]
    CardPool,
    #[sea_orm(has_many = "super::vault_character::Entity")]
    VaultCharacter,
    #[sea_orm(has_many = "super::vault_timeline::Entity")]
    VaultTimeline,
    #[sea_orm(has_many = "super::vault_plot_promise::Entity")]
    VaultPlotPromise,
    #[sea_orm(has_many = "super::vault_world::Entity")]
    VaultWorld,
    #[sea_orm(has_many = "super::vault_changelog::Entity")]
    VaultChangelog,
    #[sea_orm(has_many = "super::dynamic_layer::Entity")]
    DynamicLayer,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::user::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::User.def()
    }
}
