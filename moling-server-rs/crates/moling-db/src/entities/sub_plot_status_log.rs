//! SeaORM entity for SubPlotStatusLog.

use sea_orm::entity::prelude::*;
use sea_orm::prelude::DateTimeUtc;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "sub_plot_status_logs")]
pub struct Model {
    #[sea_orm(primary_key)]
    pub id: String,
    pub subplot_id: String,
    pub project_id: i32,
    pub chapter: i32,
    pub event_type: String,
    pub old_status: String,
    pub new_status: String,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
}

#[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
pub enum Relation {
    #[sea_orm(
        belongs_to = "super::sub_plot::Entity",
        from = "Column::SubplotId",
        to = "super::sub_plot::Column::Id",
        on_delete = "Cascade"
    )]
    SubPlot,
}

impl ActiveModelBehavior for ActiveModel {}

impl Related<super::sub_plot::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::SubPlot.def()
    }
}
