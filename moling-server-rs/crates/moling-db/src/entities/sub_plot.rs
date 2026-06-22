//! SeaORM entity for SubPlot — mirrors Python `app/models/sub_plot.py`.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "sub_plots")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    pub project_id: i32,
    pub title: String,
    #[sea_orm(default_value = r#""active""#)]
    pub status: String,
    #[sea_orm(default_value = "1")]
    pub created_chapter: i32,
    #[sea_orm(default_value = "1")]
    pub last_advancement_chapter: i32,
    #[sea_orm(default_value = r#""green""#)]
    pub health_status: String,
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
    #[sea_orm(has_many = "super::sub_plot_status_log::Entity")]
    StatusLog,
}

impl ActiveModelBehavior for ActiveModel {}
