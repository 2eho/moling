//! Project service — business logic for project CRUD, stats, and suggestions.
//!
//! Mirrors Python `app/service/project_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_core::types::Pagination;
use moling_db::dao::chapter_dao::ChapterDao;
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::vault_dao::VaultDao;
use moling_db::entities::project::{self, Model as ProjectModel};
use sea_orm::{DatabaseConnection, Set};
use serde_json::Value as Json;

/// Business logic for project operations.
#[derive(Clone)]
pub struct ProjectService {
    project_dao: ProjectDao,
    chapter_dao: ChapterDao,
    vault_dao: VaultDao,
}

impl ProjectService {
    /// Create a new service with DAO dependencies injected.
    pub fn new() -> Self {
        Self {
            project_dao: ProjectDao,
            chapter_dao: ChapterDao,
            vault_dao: VaultDao,
        }
    }

    /// Create a new project.
    ///
    /// Mirrors Python `ProjectService.create_project`.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        title: &str,
        author: &str,
        genre: &str,
        synopsis: Option<&str>,
        worldview: Option<&str>,
        protagonist: Option<&str>,
        style: Option<&str>,
        target_words: Option<i32>,
        frequency: Option<&str>,
        tags: Option<&str>,
        creation_mode: Option<&str>,
        template_id: Option<i32>,
    ) -> AppResult<ProjectModel> {
        let tags_json: Option<Json> = tags.and_then(|s| {
            if s.is_empty() { None } else { Some(Json::String(s.to_owned())) }
        });
        let model = project::ActiveModel {
            user_id: Set(user_id.to_owned()),
            title: Set(title.to_owned()),
            author: Set(author.to_owned()),
            genre: Set(genre.to_owned()),
            synopsis: Set(synopsis.map(|s| s.to_owned())),
            worldview: Set(worldview.map(|s| s.to_owned())),
            protagonist: Set(protagonist.map(|s| s.to_owned())),
            style: Set(style.map(|s| s.to_owned())),
            target_words: Set(target_words),
            frequency: Set(frequency.map(|s| s.to_owned())),
            tags: Set(tags_json),
            creation_mode: Set(creation_mode.map(|s| s.to_owned()).unwrap_or_else(|| "manual".to_owned())),
            template_id: Set(template_id),
            status: Set("draft".to_owned()),
            word_count: Set(0),
            ..Default::default()
        };
        self.project_dao.create(db, model).await
    }

    /// List projects for a user with pagination.
    ///
    /// Returns enriched projects with chapter counts. Mirrors Python `list_projects`.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        pagination: &Pagination,
    ) -> AppResult<(Vec<ProjectModel>, u64)> {
        self.project_dao
            .find_by_user(db, user_id, pagination)
            .await
    }

    /// List projects with optional status filter and simple offset/limit.
    pub async fn list_with_filter(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<ProjectModel>> {
        self.project_dao.list_by_user(db, user_id, skip, limit).await
    }

    /// Get a single project with ownership verification.
    ///
    /// Mirrors Python `ProjectService.get_project`.
    pub async fn get(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<ProjectModel> {
        let p = self
            .project_dao
            .find_by_id(db, project_id)
            .await?
            .ok_or_else(AppError::project_not_found)?;
        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }
        Ok(p)
    }

    /// Update a project with ownership verification.
    ///
    /// Mirrors Python `ProjectService.update_project`.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
        updates: ProjectUpdate,
    ) -> AppResult<ProjectModel> {
        use sea_orm::{ActiveModelTrait, IntoActiveModel};
        let p = self.get(db, user_id, project_id).await?;
        let mut active = p.into_active_model();
        if let Some(v) = updates.title {
            active.title = Set(v);
        }
        if let Some(v) = updates.author {
            active.author = Set(v);
        }
        if let Some(v) = updates.genre {
            active.genre = Set(v);
        }
        if let Some(v) = updates.synopsis {
            active.synopsis = Set(Some(v));
        }
        if let Some(v) = updates.worldview {
            active.worldview = Set(Some(v));
        }
        if let Some(v) = updates.protagonist {
            active.protagonist = Set(Some(v));
        }
        if let Some(v) = updates.style {
            active.style = Set(Some(v));
        }
        if let Some(v) = updates.target_words {
            active.target_words = Set(Some(v));
        }
        if let Some(v) = updates.frequency {
            active.frequency = Set(Some(v));
        }
        if let Some(v) = updates.tags {
            let json_val = if v.is_empty() { None } else { Some(Json::String(v)) };
            active.tags = Set(json_val);
        }
        if let Some(v) = updates.status {
            active.status = Set(v);
        }
        if let Some(v) = updates.template_id {
            active.template_id = Set(v);
        }
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update project failed: {e}")))
    }

    /// Soft-delete a project with ownership verification.
    ///
    /// Mirrors Python `ProjectService.delete_project`.
    pub async fn delete(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<()> {
        let p = self.get(db, user_id, project_id).await?;
        self.project_dao.soft_delete(db, p.id).await
    }

    /// Restore a soft-deleted project.
    pub async fn restore(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<ProjectModel> {
        use sea_orm::{ActiveModelTrait, ColumnTrait, EntityTrait, IntoActiveModel, QueryFilter};
        use moling_db::entities::project::Entity as ProjectEntity;
        use moling_db::entities::project::Column;

        let p = ProjectEntity::find_by_id(project_id)
            .filter(Column::IsDeleted.eq(true))
            .one(db)
            .await
            .map_err(|e| AppError::internal(format!("Database query failed: {e}")))?
            .ok_or_else(AppError::project_not_found)?;

        if p.user_id != user_id {
            return Err(AppError::project_access_denied());
        }

        let mut active = p.into_active_model();
        active.is_deleted = Set(false);
        active.deleted_at = Set(None);
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Restore project failed: {e}")))
    }

    /// Get project statistics for a user.
    ///
    /// Uses the DAO's aggregated stats query. Mirrors Python `get_project_stats`.
    pub async fn get_stats(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<ProjectStats> {
        let dao_stats = self.project_dao.get_stats(db, user_id).await?;
        Ok(ProjectStats {
            total_projects: dao_stats.total_projects,
            total_words: dao_stats.total_words as u64,
            total_chapters: 0, // Cross-project chapter count requires a dedicated query
            active_count: dao_stats.active_count,
            draft_count: dao_stats.draft_count,
        })
    }

    /// Get project statistics for a single project.
    pub async fn get_project_stats(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<SingleProjectStats> {
        let _p = self.get(db, user_id, project_id).await?;
        let total_chapters = self
            .chapter_dao
            .count_by_project(db, project_id)
            .await?;
        let completed_chapters = self
            .chapter_dao
            .count_by_project_and_status(db, project_id, Some("completed"))
            .await?;
        Ok(SingleProjectStats {
            project_id,
            total_chapters,
            completed_chapters,
            completion_rate: if total_chapters > 0 {
                (completed_chapters as f64 / total_chapters as f64) * 100.0
            } else {
                0.0
            },
        })
    }

    /// Get AI-powered writing suggestions for a project.
    ///
    /// Mirrors Python `ProjectService.get_suggestions`.
    pub async fn suggest(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        project_id: i32,
    ) -> AppResult<Vec<Suggestion>> {
        let _p = self.get(db, user_id, project_id).await?;
        let mut suggestions = Vec::new();

        // Suggestion type 1: Chapter completion status
        let total = self.chapter_dao.count_by_project(db, project_id).await?;
        let completed = self
            .chapter_dao
            .count_by_project_and_status(db, project_id, Some("completed"))
            .await?;

        if total > 0 {
            let completion_rate = (completed as f64 / total as f64) * 100.0;
            if completion_rate < 50.0 {
                suggestions.push(Suggestion {
                    typ: "completion".into(),
                    title: "章节完成率较低".into(),
                    content: format!(
                        "当前完成率 {:.1}%（{}/{}），建议优先完成草稿章节。",
                        completion_rate, completed, total
                    ),
                    priority: "high".into(),
                });
            }
        }

        if total > 0 && total < 5 {
            suggestions.push(Suggestion {
                typ: "completion".into(),
                title: "章节数量较少".into(),
                content: format!(
                    "当前仅有 {total} 个章节，建议继续创作以丰富故事内容。"
                ),
                priority: "medium".into(),
            });
        }

        // Suggestion type 2: Character participation balance
        let active_characters = self
            .vault_dao
            .count_characters_by_status(db, project_id, "active")
            .await?;
        if active_characters > 5 && total > 0 {
            suggestions.push(Suggestion {
                typ: "character_balance".into(),
                title: "角色数量较多".into(),
                content: format!(
                    "当前有 {active_characters} 个活跃角色，注意平衡各角色的出场时间和戏份。"
                ),
                priority: "medium".into(),
            });
        }

        // Suggestion type 3: Plot promise recycling
        let dormant_promises = self
            .vault_dao
            .count_plot_promises_by_status(db, project_id, "dormant")
            .await?;
        if dormant_promises > 3 {
            suggestions.push(Suggestion {
                typ: "plot_promise".into(),
                title: "伏笔待回收".into(),
                content: format!(
                    "有 {dormant_promises} 个伏笔处于休眠状态，建议适时回收以推进剧情。"
                ),
                priority: "medium".into(),
            });
        }

        Ok(suggestions)
    }
}

impl Default for ProjectService {
    fn default() -> Self {
        Self::new()
    }
}

/// Field-level project update payload.
///
/// Mirrors Python `UpdateProjectReq`.
#[derive(Default)]
pub struct ProjectUpdate {
    pub title: Option<String>,
    pub author: Option<String>,
    pub genre: Option<String>,
    pub synopsis: Option<String>,
    pub worldview: Option<String>,
    pub protagonist: Option<String>,
    pub style: Option<String>,
    pub target_words: Option<i32>,
    pub frequency: Option<String>,
    pub tags: Option<String>,
    pub status: Option<String>,
    pub template_id: Option<Option<i32>>,
}

/// Aggregated project statistics for a user.
///
/// Mirrors Python `ProjectStatsResp`.
pub struct ProjectStats {
    pub total_projects: u64,
    pub total_words: u64,
    pub total_chapters: u64,
    pub active_count: u64,
    pub draft_count: u64,
}

/// Statistics for a single project.
pub struct SingleProjectStats {
    pub project_id: i32,
    pub total_chapters: u64,
    pub completed_chapters: u64,
    pub completion_rate: f64,
}

/// A single writing suggestion.
///
/// Mirrors Python suggestion dict in `ProjectService.get_suggestions`.
pub struct Suggestion {
    pub typ: String,
    pub title: String,
    pub content: String,
    pub priority: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_service_construction() {
        let svc = ProjectService::new();
        let _ = svc;
    }

    #[test]
    fn test_project_update_defaults() {
        let u = ProjectUpdate::default();
        assert!(u.title.is_none());
        assert!(u.author.is_none());
        assert!(u.status.is_none());
    }

    #[test]
    fn test_project_update_all_fields() {
        let u = ProjectUpdate {
            title: Some("Test".into()),
            author: Some("Author".into()),
            genre: Some("fantasy".into()),
            synopsis: Some("A story".into()),
            worldview: None,
            protagonist: None,
            style: None,
            target_words: Some(50000),
            frequency: Some("weekly".into()),
            tags: Some("tag1,tag2".into()),
            status: Some("active".into()),
            template_id: None,
        };
        assert_eq!(u.title.unwrap(), "Test");
        assert_eq!(u.target_words.unwrap(), 50000);
    }

    #[test]
    fn test_suggestion_fields() {
        let s = Suggestion {
            typ: "completion".into(),
            title: "Test".into(),
            content: "Content".into(),
            priority: "high".into(),
        };
        assert_eq!(s.priority, "high");
    }

    #[test]
    fn test_single_project_stats() {
        let stats = SingleProjectStats {
            project_id: 1,
            total_chapters: 10,
            completed_chapters: 5,
            completion_rate: 50.0,
        };
        assert_eq!(stats.completion_rate, 50.0);
    }
}
