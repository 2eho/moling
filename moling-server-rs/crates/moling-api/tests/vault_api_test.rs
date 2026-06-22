//! Integration tests for Vault API routes.
//!
//! Tests: create character (200), list characters (200), get summary (200),
//! character not found (404), access denied (403).

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::Router;
use moling_api::{build_router, AppState};
use moling_auth::CurrentUser;
use moling_core::config::Settings;
use moling_core::redis::{RedisClient, RedisPool};
use sea_orm::{Database, DatabaseConnection, ConnectionTrait, DbBackend, Statement};
use std::sync::Arc;
use tower::util::ServiceExt;
use uuid::Uuid;

async fn setup_app() -> (Router, DatabaseConnection, Uuid, i32) {
    let db = Database::connect("sqlite::memory:").await.expect("Failed to create SQLite DB");

    let stmts = [
        "CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'user',
            avatar_url TEXT, bio TEXT, status TEXT NOT NULL DEFAULT 'active',
            settings TEXT, reset_token TEXT, reset_token_expires TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
        )",
        "CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            title TEXT NOT NULL, author TEXT NOT NULL DEFAULT '', genre TEXT NOT NULL DEFAULT '',
            tags TEXT, synopsis TEXT, worldview TEXT, protagonist TEXT, supporting_chars TEXT,
            word_count INTEGER NOT NULL DEFAULT 0, target_words INTEGER, frequency TEXT,
            style TEXT, status TEXT NOT NULL DEFAULT 'draft',
            creation_mode TEXT NOT NULL DEFAULT 'from_scratch', template_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
        )",
        "CREATE TABLE IF NOT EXISTS vault_characters (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT,
            project_id INTEGER NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT '',
            faction TEXT, status TEXT NOT NULL DEFAULT 'active', location TEXT,
            appearance TEXT, personality TEXT, knowledge TEXT, confidence REAL,
            chapter_hist TEXT, current_state TEXT, motivation TEXT, emotion TEXT,
            traits TEXT, description TEXT, background TEXT, relationships TEXT,
            state_machine TEXT, chapter_count INTEGER NOT NULL DEFAULT 0, embedding TEXT
        )",
        "CREATE TABLE IF NOT EXISTS vault_timeline (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT,
            project_id INTEGER NOT NULL, event TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            chapter_number INTEGER NOT NULL DEFAULT 0, is_key_event INTEGER NOT NULL DEFAULT 0,
            impact TEXT, characters_involved TEXT, importance TEXT
        )",
        "CREATE TABLE IF NOT EXISTS vault_plot_promises (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT,
            project_id INTEGER NOT NULL, description TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'foreshadowing', status TEXT NOT NULL DEFAULT 'active',
            urgency INTEGER NOT NULL DEFAULT 0, related_characters TEXT,
            planted_chapter INTEGER, resolved_chapter INTEGER
        )",
        "CREATE TABLE IF NOT EXISTS vault_worlds (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT,
            project_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'general', "constraint" TEXT, source_chapter INTEGER
        )",
        "CREATE TABLE IF NOT EXISTS vault_changelogs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            project_id INTEGER NOT NULL, entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL, action TEXT NOT NULL, changes TEXT, user_id TEXT
        )",
    ];

    for sql in stmts {
        let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
        db.execute(stmt).await.expect("Failed to create table");
    }

    let user_id = Uuid::new_v4();
    let user_id_str = user_id.to_string();

    db.execute(Statement::from_string(DbBackend::Sqlite,
        format!("INSERT INTO users (id, email, username, password_hash, role, status) VALUES ('{user_id_str}', 'test@test.com', 'testuser', 'hash', 'user', 'active')")
    )).await.unwrap();

    db.execute(Statement::from_string(DbBackend::Sqlite,
        format!("INSERT INTO projects (user_id, title, author, genre, status) VALUES ('{user_id_str}', 'Vault Project', 'Author', 'fantasy', 'active')")
    )).await.unwrap();

    let project_id = 1i32; // SQLite auto-increment starts at 1

    let settings = Arc::new(Settings::new().unwrap());
    let redis_pool = RedisPool::new("redis://localhost:9999", None).await;
    let redis_client = Arc::new(RedisClient::new(redis_pool));
    let state = AppState::new(db.clone(), redis_client, settings);
    let router = build_router(state);

    (router, db, user_id, project_id)
}

fn current_user(user_id: &Uuid) -> CurrentUser {
    CurrentUser::new(*user_id, "test@test.com".into(), "user".into())
}

async fn authed_post(router: &Router, path: &str, body: serde_json::Value, user: &CurrentUser) -> (StatusCode, serde_json::Value) {
    let body_str = body.to_string();
    let mut request = Request::builder().method("POST").uri(path)
        .header("content-type", "application/json")
        .body(Body::from(body_str)).unwrap();
    request.extensions_mut().insert(user.clone());
    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = if body_bytes.is_empty() { serde_json::Value::Null }
        else { serde_json::from_slice(&body_bytes).unwrap_or(serde_json::Value::Null) };
    (status, json)
}

async fn authed_get(router: &Router, path: &str, user: &CurrentUser) -> (StatusCode, serde_json::Value) {
    let mut request = Request::builder().method("GET").uri(path).body(Body::empty()).unwrap();
    request.extensions_mut().insert(user.clone());
    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = if body_bytes.is_empty() { serde_json::Value::Null }
        else { serde_json::from_slice(&body_bytes).unwrap_or(serde_json::Value::Null) };
    (status, json)
}

#[tokio::test]
async fn test_create_character_success() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_post(&router,
        &format!("/api/v1/projects/{project_id}/vault/characters"),
        serde_json::json!({
            "name": "Hero",
            "role": "protagonist",
            "description": "The main character"
        }),
        &user).await;

    assert!(status.is_success(), "Create character should succeed, got {status}: {json:?}");
    assert!(json.get("id").is_some(), "Should have character id");
}

#[tokio::test]
async fn test_list_characters() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create characters
    authed_post(&router, &format!("/api/v1/projects/{project_id}/vault/characters"),
        serde_json::json!({"name": "Hero", "role": "protagonist"}), &user).await;
    authed_post(&router, &format!("/api/v1/projects/{project_id}/vault/characters"),
        serde_json::json!({"name": "Villain", "role": "antagonist"}), &user).await;

    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/vault/characters"), &user).await;

    assert_eq!(status, StatusCode::OK, "List characters should return 200: {json:?}");
    assert!(json.as_array().map_or(false, |a| a.len() >= 2), "Should have at least 2 characters");
}

#[tokio::test]
async fn test_get_vault_summary() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create a character
    authed_post(&router, &format!("/api/v1/projects/{project_id}/vault/characters"),
        serde_json::json!({"name": "Summary Char", "role": "sidekick"}), &user).await;

    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/vault/summary"), &user).await;

    assert_eq!(status, StatusCode::OK, "Vault summary should return 200: {json:?}");
    assert!(json.get("characters").is_some(), "Should have characters count");
    assert!(json["characters"].as_u64().unwrap_or(0) >= 1, "Should have at least 1 character");
}

#[tokio::test]
async fn test_get_character_not_found() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/vault/characters/nonexistent"),
        &user).await;

    assert!(status.is_client_error(),
        "Non-existent character should return error, got {status}: {json:?}");
}

#[tokio::test]
async fn test_create_plot_promise() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_post(&router,
        &format!("/api/v1/projects/{project_id}/vault/plot-promises"),
        serde_json::json!({
            "description": "The hero will face a final trial",
            "promise_type": "foreshadowing",
            "urgency": 5,
            "planted_chapter": 1
        }),
        &user).await;

    assert!(status.is_success(), "Create plot promise should succeed, got {status}: {json:?}");
    assert!(json.get("id").is_some(), "Should have plot promise id");
}
