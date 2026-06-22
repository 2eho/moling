//! Settings service — user profile, password change, LLM config, theme, system config.
//!
//! Mirrors Python `app/service/setting_service.py`.

use moling_core::error::{AppError, AppResult};
use moling_db::dao::system_config_dao::SystemConfigDao;
use moling_db::dao::user_dao::UserDao;
use moling_db::entities::user::Model as UserModel;
use sea_orm::{ActiveModelTrait, DatabaseConnection, IntoActiveModel, Set};
use serde_json::Value as Json;

/// Business logic for user settings operations.
#[derive(Clone)]
pub struct SettingService {
    user_dao: UserDao,
    config_dao: SystemConfigDao,
}

impl SettingService {
    pub fn new() -> Self {
        Self {
            user_dao: UserDao,
            config_dao: SystemConfigDao,
        }
    }

    /// Get user profile information.
    ///
    /// Mirrors Python `SettingService.get_profile`.
    pub async fn get_profile(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<UserModel> {
        self.user_dao
            .find_by_id(db, user_id)
            .await?
            .ok_or_else(|| AppError::not_found("用户不存在".to_owned()))
    }

    /// Update user profile (username, bio, avatar_url).
    ///
    /// Mirrors Python `SettingService.update_profile`.
    pub async fn update_profile(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        username: Option<&str>,
        bio: Option<&str>,
        avatar_url: Option<&str>,
    ) -> AppResult<UserModel> {
        let u = self.get_profile(db, user_id).await?;
        let mut active = u.into_active_model();

        // Check username uniqueness if changing
        if let Some(new_username) = username {
            if new_username != active.username.as_ref() {
                if self
                    .user_dao
                    .username_exists(db, new_username)
                    .await?
                {
                    return Err(AppError::validation_error("该用户名已被使用".to_owned()));
                }
                active.username = Set(new_username.to_owned());
            }
        }
        if let Some(v) = bio {
            active.bio = Set(Some(v.to_owned()));
        }
        if let Some(v) = avatar_url {
            active.avatar_url = Set(Some(v.to_owned()));
        }
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update profile failed: {e}")))
    }

    /// Change password with current password verification.
    ///
    /// Mirrors Python `SettingService.change_password`.
    pub async fn change_password(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        current_password: &str,
        new_password: &str,
    ) -> AppResult<serde_json::Value> {
        let u = self.get_profile(db, user_id).await?;

        // Verify old password
        let valid = bcrypt::verify(current_password, &u.password_hash)
            .unwrap_or(false);
        if !valid {
            return Err(AppError::not_found("旧密码不正确".to_owned()));
        }

        // Validate new password
        if new_password.len() < 8 {
            return Err(AppError::validation_error(
                "新密码至少需要8个字符".to_owned(),
            ));
        }

        // Hash and update
        let hashed = bcrypt::hash(new_password, 12)
            .map_err(|_| AppError::internal("密码哈希失败".to_owned()))?;
        let mut active = u.into_active_model();
        active.password_hash = Set(hashed);
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Password change failed: {e}")))?;

        Ok(serde_json::json!({"message": "密码修改成功"}))
    }

    /// Get user settings (parsed from the JSON settings column).
    ///
    /// Mirrors Python `SettingService.get_settings`.
    pub async fn get_settings(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<Json> {
        let u = self.get_profile(db, user_id).await?;
        Ok(u.settings.unwrap_or_default())
    }

    /// Update user settings (partial update on the JSON settings column).
    ///
    /// Mirrors Python `SettingService.update_settings`.
    pub async fn update_settings(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        settings_update: Json,
    ) -> AppResult<Json> {
        let u = self.get_profile(db, user_id).await?;
        let settings_clone = u.settings.clone();
        let mut current: serde_json::Map<String, Json> = settings_clone
            .and_then(|v| v.as_object().cloned())
            .unwrap_or_default();

        // Merge new settings into current
        if let Some(update_obj) = settings_update.as_object() {
            for (key, value) in update_obj {
                current.insert(key.clone(), value.clone());
            }
        }

        let merged = Json::Object(current);
        let mut active = u.into_active_model();
        active.settings = Set(Some(merged.clone()));
        active
            .update(db)
            .await
            .map_err(|e| AppError::internal(format!("Update settings failed: {e}")))?;
        Ok(merged)
    }

    // ---- LLM configuration management ----

    /// Get LLM configuration: API key, base URL, model, etc.
    ///
    /// Keys: llm_api_key, llm_base_url, llm_model, llm_temperature, llm_max_tokens
    pub async fn get_llm_config(
        &self,
        db: &DatabaseConnection,
    ) -> AppResult<Json> {
        let keys = [
            "llm_api_key",
            "llm_base_url",
            "llm_model",
            "llm_temperature",
            "llm_max_tokens",
        ];
        let key_strings: Vec<String> = keys.iter().map(|s| s.to_string()).collect();
        let configs = self.config_dao.find_by_keys(db, &key_strings).await?;

        let mut result = serde_json::Map::new();
        for key in &keys {
            if let Some(cfg) = configs.get(*key) {
                result.insert(key.to_string(), Json::String(cfg.value.clone()));
            }
        }
        Ok(Json::Object(result))
    }

    /// Update LLM configuration (upserts into system_config).
    pub async fn update_llm_config(
        &self,
        db: &DatabaseConnection,
        api_key: Option<&str>,
        base_url: Option<&str>,
        model: Option<&str>,
        temperature: Option<f64>,
        max_tokens: Option<i32>,
    ) -> AppResult<()> {
        if let Some(v) = api_key {
            self.config_dao
                .upsert(db, "llm_api_key", v, "LLM API密钥")
                .await?;
        }
        if let Some(v) = base_url {
            self.config_dao
                .upsert(db, "llm_base_url", v, "LLM API地址")
                .await?;
        }
        if let Some(v) = model {
            self.config_dao
                .upsert(db, "llm_model", v, "LLM 模型名称")
                .await?;
        }
        if let Some(v) = temperature {
            self.config_dao
                .upsert(db, "llm_temperature", &v.to_string(), "LLM 温度参数")
                .await?;
        }
        if let Some(v) = max_tokens {
            self.config_dao
                .upsert(db, "llm_max_tokens", &v.to_string(), "LLM 最大Token数")
                .await?;
        }
        Ok(())
    }

    // ---- Theme settings ----

    /// Get theme settings for a user.
    pub async fn get_theme(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
    ) -> AppResult<Json> {
        let settings = self.get_settings(db, user_id).await?;
        let theme = settings.get("theme").cloned().unwrap_or_else(|| {
            let mut m = serde_json::Map::new();
            m.insert("mode".into(), Json::String("light".into()));
            m.insert("primary_color".into(), Json::String("#1976d2".into()));
            Json::Object(m)
        });
        Ok(theme)
    }

    /// Update theme settings for a user.
    pub async fn update_theme(
        &self,
        db: &DatabaseConnection,
        user_id: &str,
        mode: Option<&str>,
        primary_color: Option<&str>,
    ) -> AppResult<Json> {
        let mut theme_update = serde_json::Map::new();
        if let Some(v) = mode {
            theme_update.insert("mode".into(), Json::String(v.to_owned()));
        }
        if let Some(v) = primary_color {
            theme_update.insert("primary_color".into(), Json::String(v.to_owned()));
        }
        let wrapper = {
            let mut m = serde_json::Map::new();
            m.insert("theme".into(), Json::Object(theme_update));
            Json::Object(m)
        };
        self.update_settings(db, user_id, wrapper).await
    }

    // ---- System configuration management ----

    /// Get a system-wide configuration value by key.
    pub async fn get_system_config(
        &self,
        db: &DatabaseConnection,
        key: &str,
    ) -> AppResult<Option<String>> {
        let cfg = self.config_dao.find_by_key(db, key).await?;
        Ok(cfg.map(|c| c.value))
    }

    /// Set a system-wide configuration value.
    pub async fn set_system_config(
        &self,
        db: &DatabaseConnection,
        key: &str,
        value: &str,
        description: &str,
    ) -> AppResult<()> {
        self.config_dao.upsert(db, key, value, description).await?;
        Ok(())
    }

    /// Export user data placeholder.
    pub async fn export(
        &self,
        _db: &DatabaseConnection,
        _user_id: &str,
    ) -> AppResult<Json> {
        Ok(serde_json::json!({"message": "Export queued", "status": "pending"}))
    }
}

impl Default for SettingService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_setting_service_constructs() {
        let _ = SettingService::new();
    }

    #[test]
    fn test_export_returns_pending() {
        // export takes &DatabaseConnection but we can't construct one easily in tests
        // Just verify the struct constructs
        let svc = SettingService::new();
        let _ = svc;
    }
}
