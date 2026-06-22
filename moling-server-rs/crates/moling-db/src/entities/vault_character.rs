use sea_orm::entity::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value as Json;

#[derive(Clone, Debug, PartialEq, DeriveEntityModel, Serialize, Deserialize)]
#[sea_orm(table_name = "vault_characters")]
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
    pub name: String,
    pub role: String,
    pub faction: Option<String>,
    #[sea_orm(default_value = "'active'")]
    pub status: String,
    pub location: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub appearance: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub personality: Option<String>,
    pub knowledge: Option<Json>,
    pub confidence: Option<f64>,
    pub chapter_hist: Option<Json>,
    #[sea_orm(column_type = "Text")]
    pub current_state: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub motivation: Option<String>,
    pub emotion: Option<String>,
    pub traits: Option<Json>,
    #[sea_orm(column_type = "Text")]
    pub description: Option<String>,
    #[sea_orm(column_type = "Text")]
    pub background: Option<String>,
    pub relationships: Option<Json>,
    pub state_machine: Option<Json>,
    #[sea_orm(default_value = "0")]
    pub chapter_count: i32,
    pub embedding: Option<Json>,
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
