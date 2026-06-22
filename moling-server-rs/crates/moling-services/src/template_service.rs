//! Template service — CRUD for templates and create-project-from-template.
//!
//! Mirrors Python `app/service/template_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::project_dao::ProjectDao;
use moling_db::dao::template_dao::TemplateDao;
use moling_db::entities::project::Model as ProjectModel;
use moling_db::entities::template::Model as TemplateModel;
use sea_orm::{DatabaseConnection, Set};
use serde_json::Value as Json;

/// Business logic for template operations.
#[derive(Clone)]
pub struct TemplateService {
    template_dao: TemplateDao,
    project_dao: ProjectDao,
}

impl TemplateService {
    pub fn new() -> Self {
        Self {
            template_dao: TemplateDao,
            project_dao: ProjectDao,
        }
    }

    /// List templates with pagination, optionally filtered by genre.
    ///
    /// Mirrors Python `TemplateService.list_templates`.
    pub async fn list(
        &self,
        db: &DatabaseConnection,
        genre: Option<&str>,
        skip: u64,
        limit: u64,
    ) -> AppResult<TemplateListResult> {
        let filter_genre = genre.unwrap_or("");
        let templates = self
            .template_dao
            .list_by_genre(db, filter_genre, skip, limit)
            .await?;
        let total = self.template_dao.count_by_genre(db, filter_genre).await?;
        Ok(TemplateListResult {
            items: templates,
            total,
            skip,
            limit,
        })
    }

    /// Get a single template by ID.
    ///
    /// Mirrors Python `TemplateService.get_template`.
    pub async fn get(
        &self,
        db: &DatabaseConnection,
        id: &str,
    ) -> AppResult<TemplateModel> {
        self.template_dao
            .find_by_id(db, id)
            .await?
            .ok_or_else(|| AppError::not_found("模板不存在".to_owned()))
    }

    /// Create a new template.
    ///
    /// Mirrors Python `TemplateService.create_template`.
    pub async fn create(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        name: &str,
        description: &str,
        genre: &str,
        structure: Option<Json>,
    ) -> AppResult<TemplateModel> {
        let model = moling_db::entities::template::ActiveModel {
            id: Set(uuid::Uuid::new_v4().to_string()),
            name: Set(name.to_owned()),
            description: Set(description.to_owned()),
            genre: Set(genre.to_owned()),
            structure: Set(structure),
            created_by: Set(Some(user_id.to_owned())),
            ..Default::default()
        };
        self.template_dao.create(db, model).await
    }

    /// Update a template.
    ///
    /// Mirrors Python `TemplateService.update_template`.
    pub async fn update(
        &self,
        db: &DatabaseConnection,
        id: &str,
        name: Option<&str>,
        description: Option<&str>,
        genre: Option<&str>,
        structure: Option<Json>,
    ) -> AppResult<TemplateModel> {
        use sea_orm::{ActiveModelTrait, IntoActiveModel};
        let t = self.get(db, id).await?;
        let mut a = t.into_active_model();
        if let Some(v) = name {
            a.name = Set(v.to_owned());
        }
        if let Some(v) = description {
            a.description = Set(v.to_owned());
        }
        if let Some(v) = genre {
            a.genre = Set(v.to_owned());
        }
        if let Some(v) = structure {
            a.structure = Set(Some(v));
        }
        a.update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update template failed: {e}")))
    }

    /// Delete a template.
    ///
    /// Mirrors Python `TemplateService.delete_template`.
    pub async fn delete(&self, db: &DatabaseConnection, id: &str) -> AppResult<()> {
        self.template_dao.delete(db, id).await.map(|_| ())
    }

    /// Create a project from a template.
    ///
    /// Mirrors Python `TemplateService.create_project_from_template`.
    pub async fn create_project(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        template_id: &str,
        title: &str,
        author: Option<&str>,
        template_numeric_id: i32,
    ) -> AppResult<ProjectModel> {
        let tmpl = self.get(db, template_id).await?;
        let model = moling_db::entities::project::ActiveModel {
            user_id: Set(user_id.to_owned()),
            title: Set(title.to_owned()),
            author: Set(author.map(|a| a.to_owned()).unwrap_or_default()),
            genre: Set(tmpl.genre),
            creation_mode: Set("from_template".to_owned()),
            template_id: Set(Some(template_numeric_id)),
            status: Set("draft".to_owned()),
            word_count: Set(0),
            ..Default::default()
        };
        self.project_dao.create(db, model).await
    }

    /// Search templates by keyword in name or description.
    ///
    /// Currently delegates to genre-based listing; full-text search can
    /// be added when the template schema is extended.
    pub async fn search(
        &self,
        db: &DatabaseConnection,
        _query: &str,
        skip: u64,
        limit: u64,
    ) -> AppResult<Vec<TemplateModel>> {
        self.template_dao.list_by_genre(db, "", skip, limit).await
    }

    /// Get recommended templates (newest first, across all genres).
    pub async fn recommend(
        &self,
        db: &DatabaseConnection,
        limit: u64,
    ) -> AppResult<Vec<TemplateModel>> {
        self.template_dao.list_by_genre(db, "", 0, limit).await
    }
}

impl Default for TemplateService {
    fn default() -> Self {
        Self::new()
    }
}

/// Paginated template list result.
pub struct TemplateListResult {
    pub items: Vec<TemplateModel>,
    pub total: u64,
    pub skip: u64,
    pub limit: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_template_service_constructs() {
        let _ = TemplateService::new();
    }

    #[test]
    fn test_template_list_result() {
        let r = TemplateListResult {
            items: vec![],
            total: 0,
            skip: 0,
            limit: 20,
        };
        assert_eq!(r.total, 0);
    }
}
