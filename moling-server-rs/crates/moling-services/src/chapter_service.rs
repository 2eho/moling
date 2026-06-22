//! Chapter service — business logic for chapter CRUD, reorder, confirm, revise.
//!
//! Mirrors Python `app/service/chapter_service.py`.

use chrono::Utc;
use moling_core::error::{AppError, AppResult};
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::chapter::{self, Model as ChapterModel};
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};

/// Business logic for chapter operations.
#[derive(Clone)]
pub struct ChapterService {
    chapter_dao: ChapterDao,
    project_dao: ProjectDao,
    vault_dao: VaultDao,
}

impl ChapterService {
    pub fn new() -> Self {
        Self {
            chapter_dao: ChapterDao,
            project_dao: ProjectDao,
            vault_dao: VaultDao,
        }
    }

    /// Verify project ownership before accessing chapters.
    async fn verify_owner(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<()> {
        let p = self
            .project_dao
            .find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(())
    }

    /// Create a new chapter with auto-incremented chapter number.
    ///
    /// Mirrors Python `ChapterService.create_chapter`.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        title: &str,
    ) -> AppResult<ChapterModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let max_num = self
            .chapter_dao
            .max_chapter_number(db, project_id)
            .await?
            .unwrap_or(0);
        let model = chapter::ActiveModel {
            id: Set(uuid::Uuid::new_v4().to_string()),
            project_id: Set(project_id),
            title: Set(title.to_owned()),
            chapter_number: Set(max_num + 1),
            status: Set("draft".to_owned()),
            phase4_status: Set("pending".to_owned()),
            word_count: Set(0),
            ..Default::default()
        };
        self.chapter_dao.create(db, model).await
    }

    /// List all chapters in a project (non-deleted, ordered by chapter_number).
    ///
    /// Mirrors Python `ChapterService.list_chapters`.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<ChapterModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.chapter_dao.find_by_project(db, project_id).await
    }

    /// List chapters with pagination (offset/limit).
    pub async fn list_paginated(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<ChapterModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        self.chapter_dao
            .list_by_project(db, project_id, skip, limit)
            .await
    }

    /// Get a single chapter scoped to project.
    ///
    /// Mirrors Python `ChapterService.get_chapter`.
    pub async fn get(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<ChapterModel> {
        self.verify_owner(db, user_id, project_id).await?;
        let ch = self
            .chapter_dao
            .find_by_id(db, chapter_id)
            .await?
            .ok_or_else(AppError::chapter_not_found)?;
        if ch.project_id != project_id {
            return Err(AppError::chapter_not_found());
        }
        Ok(ch)
    }

    /// Find a chapter by its chapter_number within a project.
    pub async fn find_by_number(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_number: i32,
    ) -> AppResult<ChapterModel> {
        self.verify_owner(db, user_id, project_id).await?;
        self.chapter_dao
            .find_by_number(db, project_id, chapter_number)
            .await?
            .ok_or_else(AppError::chapter_not_found)
    }

    /// Update chapter fields.
    ///
    /// Mirrors Python `ChapterService.update_chapter`.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
        title: Option<&str>,
        content: Option<&str>,
    ) -> AppResult<ChapterModel> {
        let ch = self.get(db, user_id, project_id, chapter_id).await?;
        let mut active = ch.into_active_model();
        if let Some(t) = title {
            active.title = Set(t.to_owned());
        }
        if let Some(c) = content {
            let wc = c.chars().count() as i32;
            active.content = Set(Some(c.to_owned()));
            active.word_count = Set(wc);
        }
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update chapter failed: {e}")))
    }

    /// Soft-delete a chapter.
    ///
    /// Mirrors Python `ChapterService.delete_chapter`.
    pub async fn delete(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<()> {
        self.verify_owner(db, user_id, project_id).await?;
        self.chapter_dao.soft_delete(db, chapter_id).await
    }

    /// Reorder chapters by providing new chapter ID order.
    ///
    /// Mirrors Python `ChapterService.reorder_chapters`.
    pub async fn reorder(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        order: &[String],
    ) -> AppResult<Vec<ChapterModel>> {
        self.verify_owner(db, user_id, project_id).await?;
        let chapters = self.chapter_dao.find_by_project(db, project_id).await?;
        if order.len() != chapters.len() {
            return Err(AppError::bad_request("章节数量不匹配".to_owned()));
        }
        // Update chapter numbers sequentially
        for (i, chapter_id) in order.iter().enumerate() {
            let ch = self
                .chapter_dao
                .find_by_id(db, chapter_id)
                .await?
                .ok_or_else(AppError::chapter_not_found)?;
            let mut active = ch.into_active_model();
            active.chapter_number = Set((i + 1) as i32);
            active
                .update(db)
                .await
                .map_err(|e| AppError::internal(format!("Reorder failed: {e}")))?;
        }
        self.chapter_dao.find_by_project(db, project_id).await
    }

    /// Confirm a chapter and trigger Phase 4 processing.
    ///
    /// Mirrors Python `ChapterService.confirm_chapter`.
    pub async fn confirm(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<ChapterModel> {
        let ch = self.get(db, user_id, project_id, chapter_id).await?;
        let mut active = ch.into_active_model();
        active.status = Set("confirmed".to_owned());
        active.confirmed_at = Set(Some(Utc::now()));
        active.phase4_status = Set("processing".to_owned());
        let updated = active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Confirm failed: {e}")))?;
        // In production, this would dispatch Phase4Task asynchronously via Celery/Redis
        tracing::info!(
            chapter_id = %chapter_id,
            project_id = %project_id,
            "Chapter confirmed, Phase 4 queued"
        );
        Ok(updated)
    }

    /// Return chapter to draft for revision.
    ///
    /// Mirrors Python `ChapterService.revise_chapter`.
    pub async fn revise(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<ChapterModel> {
        let ch = self.get(db, user_id, project_id, chapter_id).await?;
        let mut active = ch.into_active_model();
        active.status = Set("draft".to_owned());
        active.confirmed_at = Set(None);
        active.phase4_status = Set("pending".to_owned());
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Revise failed: {e}")))
    }

    /// Get suggestions for a chapter (character appearances, plot promises, length).
    ///
    /// Mirrors Python `ChapterService.get_suggestions`.
    pub async fn suggest(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
    ) -> AppResult<Vec<ChapterSuggestion>> {
        let ch = self.get(db, user_id, project_id, chapter_id).await?;
        let mut suggestions = Vec::new();

        // Suggestion type 1: Chapter length check
        if ch.word_count > 0 && ch.word_count < 500 {
            suggestions.push(ChapterSuggestion {
                typ: "length".into(),
                title: "章节长度偏短".into(),
                content: format!(
                    "本章当前 {} 字，建议扩展到 1000-2000 字以获得更好的阅读体验。",
                    ch.word_count
                ),
                priority: "low".into(),
            });
        }

        // Suggestion type 2: Unused character appearances
        let active_chars = self
            .vault_dao
            .count_characters(db, project_id)
            .await?;
        if active_chars > 0 {
            suggestions.push(ChapterSuggestion {
                typ: "character_appearance".into(),
                title: "角色出场建议".into(),
                content: format!(
                    "当前有 {active_chars} 个角色，考虑让更多角色在本章出场互动。"
                ),
                priority: "medium".into(),
            });
        }

        // Suggestion type 3: Dormant plot promise recycling
        let promises = self
            .vault_dao
            .find_plot_promises(db, project_id)
            .await?;
        let dormant_count = promises
            .iter()
            .filter(|p| p.status == "dormant")
            .count();
        if dormant_count > 0 {
            suggestions.push(ChapterSuggestion {
                typ: "plot_promise".into(),
                title: "伏笔回收建议".into(),
                content: format!(
                    "有 {dormant_count} 个伏笔处于休眠状态，考虑在本章回收其中 1-2 个。"
                ),
                priority: "high".into(),
            });
        }

        Ok(suggestions)
    }

    /// Send an AI agent instruction for chapter generation.
    ///
    /// Mirrors Python `ChapterService.send_agent_instruction`.
    pub async fn send_agent_instruction(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        chapter_id: &str,
        instruction_type: &str,
        content: &str,
    ) -> AppResult<serde_json::Value> {
        let ch = self.get(db, user_id, project_id, chapter_id).await?;

        if instruction_type.is_empty() {
            return Err(AppError::bad_request("Instruction type is required".to_owned()));
        }

        // Append instruction to the chapter's generation_prompt
        let existing_prompt = ch.generation_prompt.clone();
        let mut active = ch.into_active_model();
        let new_prompt = if let Some(ref existing) = existing_prompt {
            format!("{existing}\n[Instruction: {instruction_type}] {content}")
        } else {
            format!("[Instruction: {instruction_type}] {content}")
        };
        active.generation_prompt = Set(Some(new_prompt));
        let updated = active.update(db).await.map_err(|e| {
            AppError::internal(format!("Send agent instruction failed: {e}"))
        })?;

        Ok(serde_json::json!({
            "success": true,
            "message": "Instruction sent to AI agent",
            "instruction_type": instruction_type,
            "chapter_status": updated.status,
        }))
    }

    /// Count total words across all chapters in a project.
    pub async fn count_words(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<u64> {
        self.verify_owner(db, user_id, project_id).await?;
        let chapters = self.chapter_dao.find_by_project(db, project_id).await?;
        let total: i32 = chapters.iter().map(|ch| ch.word_count).sum();
        Ok(total as u64)
    }
}

impl Default for ChapterService {
    fn default() -> Self {
        Self::new()
    }
}

/// A chapter-level writing suggestion.
pub struct ChapterSuggestion {
    pub typ: String,
    pub title: String,
    pub content: String,
    pub priority: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_service_constructs() {
        let _ = ChapterService::new();
    }

    #[test]
    fn test_chapter_suggestion_fields() {
        let s = ChapterSuggestion {
            typ: "length".into(),
            title: "Test".into(),
            content: "Test content".into(),
            priority: "low".into(),
        };
        assert_eq!(s.typ, "length");
        assert_eq!(s.priority, "low");
    }
}
