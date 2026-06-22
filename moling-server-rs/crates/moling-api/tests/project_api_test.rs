//! Integration tests for Project API routes.
//!
//! Tests: create project (200), list projects (200), get project (200),
//! get non-existent project (404), access denied (403).

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

async fn setup_app() -> (Router, DatabaseConnection, Uuid) {
    let db = Database::connect("sqlite::memory:").await.expect("Failed to create SQLite DB");

    // Create tables needed
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
    ];

    for sql in stmts {
        let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
        db.execute(stmt).await.expect("Failed to create table");
    }

    // Insert a test user
    let user_id = Uuid::new_v4();
    let insert_user = format!(
        "INSERT INTO users (id, email, username, password_hash, role, status) VALUES ('{}', 'test@test.com', 'testuser', '$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'user', 'active')",
        user_id
    );
    let stmt = Statement::from_string(DbBackend::Sqlite, insert_user);
    db.execute(stmt).await.expect("Failed to insert test user");

    let settings = Arc::new(Settings::new().unwrap_or_else(|_| {
        Settings { secret_key: "test-secret".into(), access_token_expire_minutes: 60, ..Settings::new().unwrap() }
    }));

    let redis_pool = RedisPool::new("redis://localhost:9999", None).await;
    let redis_client = Arc::new(RedisClient::new(redis_pool));

    let state = AppState::new(db.clone(), redis_client, settings);
    let router = build_router(state);

    (router, db, user_id)
}

fn current_user(user_id: &Uuid) -> CurrentUser {
    CurrentUser::new(*user_id, "test@test.com".into(), "user".into())
}

async fn authed_post(router: &Router, path: &str, body: serde_json::Value, user: &CurrentUser) -> (StatusCode, serde_json::Value) {
    let body_str = body.to_string();
    let mut request = Request::builder()
        .method("POST")
        .uri(path)
        .header("content-type", "application/json")
        .body(Body::from(body_str))
        .unwrap();
    request.extensions_mut().insert(user.clone());

    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = if body_bytes.is_empty() {
        serde_json::Value::Null
    } else {
        serde_json::from_slice(&body_bytes).unwrap_or(serde_json::Value::Null)
    };
    (status, json)
}

async fn authed_get(router: &Router, path: &str, user: &CurrentUser) -> (StatusCode, serde_json::Value) {
    let mut request = Request::builder()
        .method("GET")
        .uri(path)
        .body(Body::empty())
        .unwrap();
    request.extensions_mut().insert(user.clone());

    let response = router.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = if body_bytes.is_empty() {
        serde_json::Value::Null
    } else {
        serde_json::from_slice(&body_bytes).unwrap_or(serde_json::Value::Null)
    };
    (status, json)
}

#[tokio::test]
async fn test_create_project_success() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_post(&router, "/api/v1/projects", serde_json::json!({
        "title": "My Test Project",
        "author": "Test Author",
        "genre": "fantasy"
    }), &user).await;

    assert_eq!(status, StatusCode::OK, "Create project should return 200: {json:?}");
    assert!(json.get("id").is_some(), "Should have project id");
    assert_eq!(json["title"], "My Test Project");
    assert_eq!(json["author"], "Test Author");
}

#[tokio::test]
async fn test_list_projects() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create a project first
    authed_post(&router, "/api/v1/projects", serde_json::json!({
        "title": "List Test Project", "author": "Author", "genre": "scifi"
    }), &user).await;

    // List projects
    let (status, json) = authed_get(&router, "/api/v1/projects", &user).await;

    assert_eq!(status, StatusCode::OK, "List projects should return 200: {json:?}");
    assert!(json.get("items").is_some(), "Should have items array");
    assert!(json["total"].as_u64().unwrap_or(0) >= 1, "Should have at least 1 project");
}

#[tokio::test]
async fn test_get_project_not_found() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_get(&router, "/api/v1/projects/99999", &user).await;

    assert_eq!(status, StatusCode::NOT_FOUND, "Non-existent project should return 404: {json:?}");
}

#[tokio::test]
async fn test_get_project_success() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create a project first
    let (_, create_json) = authed_post(&router, "/api/v1/projects", serde_json::json!({
        "title": "Get Test Project", "author": "Getter", "genre": "mystery"
    }), &user).await;

    let project_id = create_json["id"].as_i64().unwrap();

    // Get the project
    let (status, json) = authed_get(&router, &format!("/api/v1/projects/{project_id}"), &user).await;

    assert_eq!(status, StatusCode::OK, "Get project should return 200: {json:?}");
    assert_eq!(json["title"], "Get Test Project");
    assert_eq!(json["id"].as_i64().unwrap(), project_id);
}

#[tokio::test]
async fn test_create_project_without_auth() {
    let (router, _db, _user_id) = setup_app().await;

    let body_str = serde_json::json!({"title": "No Auth Project"}).to_string();
    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/projects")
        .header("content-type", "application/json")
        .body(Body::from(body_str))
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    // Should return 401 since CurrentUser extractor requires auth
    assert!(response.status().is_client_error(),
        "Request without auth should fail with client error, got {}",
        response.status());
}
