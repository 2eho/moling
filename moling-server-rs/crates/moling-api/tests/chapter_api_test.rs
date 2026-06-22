//! Integration tests for Chapter API routes.
//!
//! Tests: create chapter (200), list chapters (200), get chapter (200),
//! chapter not found (404), create without auth (401).

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
        "CREATE TABLE IF NOT EXISTS chapters (
            id TEXT PRIMARY KEY, project_id INTEGER NOT NULL,
            title TEXT NOT NULL, content TEXT, chapter_number INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft', phase4_status TEXT NOT NULL DEFAULT 'pending',
            word_count INTEGER NOT NULL DEFAULT 0, confirmed_at TEXT, used_card_ids TEXT,
            generation_mode TEXT, generation_prompt TEXT, generation_weights TEXT,
            generation_result TEXT, error_message TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
            generation_duration INTEGER,
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
    ];

    for sql in stmts {
        let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
        db.execute(stmt).await.expect("Failed to create table");
    }

    let user_id = Uuid::new_v4();
    let user_id_str = user_id.to_string();

    // Insert user
    let insert_user = format!(
        "INSERT INTO users (id, email, username, password_hash, role, status) VALUES ('{user_id_str}', 'test@test.com', 'testuser', 'hash', 'user', 'active')"
    );
    db.execute(Statement::from_string(DbBackend::Sqlite, insert_user)).await.unwrap();

    // Insert project owned by this user
    let insert_project = format!(
        "INSERT INTO projects (user_id, title, author, genre, status) VALUES ('{user_id_str}', 'Chapter Test Project', 'Author', 'fantasy', 'active')"
    );
    db.execute(Statement::from_string(DbBackend::Sqlite, insert_project)).await.unwrap();

    // Get the project ID
    let query = "SELECT last_insert_rowid()";
    let result = db.query_one(Statement::from_string(DbBackend::Sqlite, query.to_owned())).await.unwrap();
    let project_id: i32 = result.map(|r| r.try_get_by_index::<i32>(0).unwrap_or(1)).unwrap_or(1);

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
    let mut request = Request::builder()
        .method("POST").uri(path)
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
async fn test_create_chapter_success() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_post(&router,
        &format!("/api/v1/projects/{project_id}/chapters"),
        serde_json::json!({"title": "Chapter 1", "content": "It was a dark and stormy night..."}),
        &user).await;

    assert_eq!(status, StatusCode::OK, "Create chapter should return 200: {json:?}");
    assert!(json.get("id").is_some(), "Should have chapter id");
    assert_eq!(json["title"], "Chapter 1");
    assert_eq!(json["chapter_number"].as_i64().unwrap_or(0), 1);
}

#[tokio::test]
async fn test_list_chapters() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create chapters
    authed_post(&router, &format!("/api/v1/projects/{project_id}/chapters"),
        serde_json::json!({"title": "Ch 1"}), &user).await;
    authed_post(&router, &format!("/api/v1/projects/{project_id}/chapters"),
        serde_json::json!({"title": "Ch 2"}), &user).await;

    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/chapters"), &user).await;

    assert_eq!(status, StatusCode::OK, "List chapters should return 200: {json:?}");
    assert!(json.as_array().map_or(false, |a| a.len() >= 2), "Should have at least 2 chapters");
}

#[tokio::test]
async fn test_get_chapter_not_found() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/chapters/nonexistent-id"),
        &user).await;

    assert_eq!(status, StatusCode::NOT_FOUND, "Non-existent chapter should return 404: {json:?}");
}

#[tokio::test]
async fn test_create_chapter_without_auth() {
    let (router, _db, _user_id, project_id) = setup_app().await;

    let body_str = serde_json::json!({"title": "Unauth Chapter"}).to_string();
    let request = Request::builder()
        .method("POST")
        .uri(&format!("/api/v1/projects/{project_id}/chapters"))
        .header("content-type", "application/json")
        .body(Body::from(body_str))
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    assert!(response.status().is_client_error(),
        "Request without auth should fail, got {}", response.status());
}

#[tokio::test]
async fn test_get_chapter_success() {
    let (router, _db, user_id, project_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create a chapter
    let (_, create_json) = authed_post(&router,
        &format!("/api/v1/projects/{project_id}/chapters"),
        serde_json::json!({"title": "Specific Chapter"}),
        &user).await;

    let chapter_id = create_json["id"].as_str().unwrap();

    // Get the chapter
    let (status, json) = authed_get(&router,
        &format!("/api/v1/projects/{project_id}/chapters/{chapter_id}"),
        &user).await;

    assert_eq!(status, StatusCode::OK, "Get chapter should return 200: {json:?}");
    assert_eq!(json["title"], "Specific Chapter");
    assert_eq!(json["id"], chapter_id);
}
