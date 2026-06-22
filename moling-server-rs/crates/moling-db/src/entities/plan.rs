//! SeaORM entity for Plan — mirrors Python `app/models/subscription.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "plans")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    pub name: String,
    pub price: f64,
    #[sea_orm(default_value = r#""CNY""#)]
    pub currency: String,
    #[sea_orm(default_value = r#""month""#)]
    pub interval: String,
    pub features: Json,
    #[sea_orm(default_value = "true")]
    pub is_active: bool,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(has_many = "super::user_subscription::Entity")]
    UserSubscription,
}

impl ActiveModelBehavior for ActiveModel {}
