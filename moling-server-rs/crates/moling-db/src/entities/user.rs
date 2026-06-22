//! SeaORM entity for User — mirrors Python `app/models/user.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "users")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    #[sea_orm(unique)]
    pub email: String,
    #[sea_orm(unique)]
    pub username: String,
    pub password_hash: String,
    #[sea_orm(default_value = r#""user""#)]
    pub role: String,
    pub avatar_url: Option<String>,
    pub bio: Option<String>,
    #[sea_orm(default_value = r#""active""#)]
    pub status: String,
    pub settings: Option<Json>,
    pub reset_token: Option<String>,
    pub reset_token_expires: Option<DateTimeUtc>,
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
    #[sea_orm(has_many = "super::project::Entity")]
    Project,
    #[sea_orm(has_many = "super::generation_task::Entity")]
    GenerationTask,
    #[sea_orm(has_many = "super::draw_history::Entity")]
    DrawHistory,
    #[sea_orm(has_many = "super::notification::Entity")]
    Notification,
    #[sea_orm(has_many = "super::template::Entity")]
    Template,
    #[sea_orm(has_many = "super::user_subscription::Entity")]
    UserSubscription,
}

impl ActiveModelBehavior for ActiveModel {}
