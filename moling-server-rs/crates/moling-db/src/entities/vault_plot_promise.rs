use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "vault_plot_promises")]
pub struct Model {
    #[sea_orm(primary_key, auto_increment = false)]
    pub id: String,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub created_at: DateTimeUtc,
    #[sea_orm(default_expr = "Expr::current_timestamp()")]
    pub updated_at: DateTimeUtc,
    #[sea_orm(default_value = "false", indexed)]
    pub is_deleted: bool,
    pub deleted_at: Option<DateTimeUtc>,
    pub project_id: i32,
    pub title: Option<String>,
    pub redeem_window: Option<i32>,
    pub confidence: Option<f64>,
    #[sea_orm(column_type = "Text")]
    pub description: String,
    #[sea_orm(column_name = "type")]
    pub r#type: String,
    #[sea_orm(default_value = "'dormant'")]
    pub status: String,
    #[sea_orm(default_value = "0")]
    pub urgency: i32,
    pub related_characters: Option<Json>,
    pub planted_chapter: Option<i32>,
    pub advancement_log: Option<Json>,
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

impl Related<super::project::Entity> for Entity {
    fn to() -> RelationDef {
        Relation::Project.def()
    }
}

impl ActiveModelBehavior for ActiveModel {}
