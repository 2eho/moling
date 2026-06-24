//! Card DAO — card pool CRUD, draw history, freshness, and retirement.

use moling_core::error::{AppError, AppResult};
use sea_orm::{ActiveModelTrait, ColumnTrait, DatabaseConnection, EntityTrait, IntoActiveModel, PaginatorTrait, QueryFilter, QueryOrder, QuerySelect, Set};

use crate::entities::{
    card_pool::{self, Entity as CardPool, Model as CardPoolModel},
    draw_history::{self, Entity as DrawHistory, Model as DrawHistoryModel},
};

/// Card data access object.
#[derive(Clone, Default)]
pub struct CardDao;

impl CardDao {
    // -- Card Pool --

    /// List all active cards for a project ordered by draw_count descending.
    pub async fn find_pool(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<CardPoolModel>> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .filter(card_pool::Column::IsActive.eq(true))
            .order_by_desc(card_pool::Column::DrawCount)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error listing pool: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all non-deleted cards for a project ordered by id.
    pub async fn list_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<CardPoolModel>> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .order_by_asc(card_pool::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error listing by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get active cards for a project, ordered by rarity (highest first) then random.
    /// Used for card drawing. Returns up to `count` cards.
    pub async fn get_active_cards(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        count: u64,
    ) -> AppResult<Vec<CardPoolModel>> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::Status.eq("active"))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .order_by_asc(card_pool::Column::Id) // deterministic fallback
            .limit(count)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error getting active cards: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get all cards of a specific rarity in a project.
    pub async fn get_by_rarity(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        rarity: &str,
    ) -> AppResult<Vec<CardPoolModel>> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::Rarity.eq(rarity))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .order_by_asc(card_pool::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, %rarity, "Card: error getting by rarity: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// List all active (is_active=true, not deleted) cards for a project.
    pub async fn list_active_by_project(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
    ) -> AppResult<Vec<CardPoolModel>> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::IsActive.eq(true))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .order_by_asc(card_pool::Column::Id)
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error listing active by project: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Fetch cards by their IDs within a project.
    pub async fn get_by_ids(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        card_ids: &[String],
    ) -> AppResult<Vec<CardPoolModel>> {
        if card_ids.is_empty() {
            return Ok(Vec::new());
        }
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::Id.is_in(card_ids.to_vec()))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error getting by ids: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Fetch cards by their IDs across all projects.
    pub async fn get_by_ids_any(
        &self,
        db: &DatabaseConnection,
        card_ids: &[String],
    ) -> AppResult<Vec<CardPoolModel>> {
        if card_ids.is_empty() {
            return Ok(Vec::new());
        }
        CardPool::find()
            .filter(card_pool::Column::Id.is_in(card_ids.to_vec()))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!("Card: error getting by ids any: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn find_card_by_id(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<Option<CardPoolModel>> {
        CardPool::find_by_id(id.to_owned())
            .filter(card_pool::Column::IsDeleted.eq(false))
            .one(db)
            .await
            .map_err(|e| {
                tracing::error!(%id, "Card: error finding card: {e}");
                AppError::internal("Database query failed")
            })
    }

    pub async fn create_card(
        &self,
        db: &DatabaseConnection,
        model: card_pool::ActiveModel,
    ) -> AppResult<CardPoolModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Card: error creating card: {e}");
            AppError::internal("Database insert failed")
        })
    }

    pub async fn update_card(
        &self,
        db: &DatabaseConnection,
        model: card_pool::ActiveModel,
    ) -> AppResult<CardPoolModel> {
        model.update(db).await.map_err(|e| {
            tracing::error!("Card: error updating card: {e}");
            AppError::internal("Database update failed")
        })
    }

    pub async fn soft_delete_card(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        use chrono::Utc;
        let card = self
            .find_card_by_id(db, id)
            .await?
            .ok_or_else(AppError::card_not_found)?;
        let mut active = card.into_active_model();
        active.is_deleted = Set(true);
        active.deleted_at = Set(Some(Utc::now()));
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Card: error soft-deleting: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Retire a card (mark is_active = false, set retired_chapter).
    pub async fn retire_card(
        &self,
        db: &DatabaseConnection,
        id: &str,
        retired_chapter: Option<i32>,
    ) -> AppResult<()> {
        let card = self
            .find_card_by_id(db, id)
            .await?
            .ok_or_else(AppError::card_not_found)?;
        let mut active = card.into_active_model();
        active.is_active = Set(false);
        if let Some(ch) = retired_chapter {
            active.retired_chapter = Set(Some(ch));
        }
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Card: error retiring: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    /// Batch update is_active flag for a list of card IDs.
    /// Returns the number of cards updated.
    pub async fn batch_retire(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        card_ids: &[String],
        is_active: bool,
    ) -> AppResult<u64> {
        if card_ids.is_empty() {
            return Ok(0);
        }
        use sea_orm::sea_query::Expr;
        let result = CardPool::update_many()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::Id.is_in(card_ids.to_vec()))
            .col_expr(card_pool::Column::IsActive, Expr::value(is_active))
            .exec(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error batch retiring: {e}");
                AppError::internal("Database update failed")
            })?;
        Ok(result.rows_affected)
    }

    /// Update freshness: increment draw_count, update last_drawn_chapter, adjust remaining_lifetime.
    pub async fn update_freshness(
        &self,
        db: &DatabaseConnection,
        id: &str,
        current_chapter: i32,
    ) -> AppResult<()> {
        let card = self
            .find_card_by_id(db, id)
            .await?
            .ok_or_else(AppError::card_not_found)?;
        let current_draw: i32 = card.draw_count;
        let current_remaining = card.remaining_lifetime;
        let mut active = card.into_active_model();
        active.draw_count = Set(current_draw + 1);
        active.last_drawn_chapter = Set(Some(current_chapter));
        // Decrease remaining lifetime by 1 if set
        if let Some(remaining) = current_remaining
            && remaining > 0
        {
            active.remaining_lifetime = Set(Some(remaining - 1));
        }
        active.update(db).await.map_err(|e| {
            tracing::error!(%id, "Card: error updating freshness: {e}");
            AppError::internal("Database update failed")
        })?;
        Ok(())
    }

    pub async fn count_pool(&self, db: &DatabaseConnection, project_id: i32) -> AppResult<u64> {
        CardPool::find()
            .filter(card_pool::Column::ProjectId.eq(project_id))
            .filter(card_pool::Column::IsDeleted.eq(false))
            .count(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error counting pool: {e}");
                AppError::internal("Database query failed")
            })
    }

    // -- Draw History --

    pub async fn find_draw_history(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        limit: u64,
    ) -> AppResult<Vec<DrawHistoryModel>> {
        DrawHistory::find()
            .filter(draw_history::Column::ProjectId.eq(project_id))
            .order_by_desc(draw_history::Column::DrawnAt)
            .limit(Some(limit))
            .all(db)
            .await
            .map_err(|e| {
                tracing::error!(project_id, "Card: error listing history: {e}");
                AppError::internal("Database query failed")
            })
    }

    /// Get draw history for a project, optionally filtered by chapter.
    pub async fn find_draw_history_by_chapter(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: Option<&str>,
        limit: u64,
    ) -> AppResult<Vec<DrawHistoryModel>> {
        let mut query = DrawHistory::find()
            .filter(draw_history::Column::ProjectId.eq(project_id))
            .order_by_desc(draw_history::Column::DrawnAt)
            .limit(limit);

        if let Some(cid) = chapter_id {
            query = query.filter(draw_history::Column::ChapterId.eq(cid));
        }

        query.all(db).await.map_err(|e| {
            tracing::error!(project_id, "Card: error listing history by chapter: {e}");
            AppError::internal("Database query failed")
        })
    }

    /// Get the most recent draw record for a project, optionally scoped to a chapter.
    pub async fn get_latest_draw(
        &self,
        db: &DatabaseConnection,
        project_id: i32,
        chapter_id: Option<&str>,
    ) -> AppResult<Option<DrawHistoryModel>> {
        let mut query = DrawHistory::find()
            .filter(draw_history::Column::ProjectId.eq(project_id))
            .order_by_desc(draw_history::Column::DrawnAt)
            .limit(1);

        if let Some(cid) = chapter_id {
            query = query.filter(draw_history::Column::ChapterId.eq(cid));
        }

        query.one(db).await.map_err(|e| {
            tracing::error!(project_id, "Card: error getting latest draw: {e}");
            AppError::internal("Database query failed")
        })
    }

    pub async fn create_draw_history(
        &self,
        db: &DatabaseConnection,
        model: draw_history::ActiveModel,
    ) -> AppResult<DrawHistoryModel> {
        model.insert(db).await.map_err(|e| {
            tracing::error!("Card: error creating draw history: {e}");
            AppError::internal("Database insert failed")
        })
    }
}
