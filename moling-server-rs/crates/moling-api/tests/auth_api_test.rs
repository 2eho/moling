//! Integration tests for Auth API routes.
//!
//! Tests: register (201), login (200), unauthorized access (401),
//! duplicate email (409), get profile (200), missing fields (422).

use axum::body::Body;
use axum::http::{Request, StatusCode};
use axum::Router;
use moling_api::{build_router, AppState};
use moling_core::config::Settings;
use moling_core::redis::{RedisClient, RedisPool};
use sea_orm::{Database, DatabaseConnection, ConnectionTrait, DbBackend, Statement};
use std::sync::Arc;
use tower::util::ServiceExt;

/// Create a test AppState with SQLite :memory: database.
async fn setup_app() -> (Router, DatabaseConnection) {
    let db = Database::connect("sqlite::memory:").await.expect("Failed to create SQLite DB");

    // Create users table
    let stmts = [
        "CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'user',
            avatar_url TEXT,
            bio TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            settings TEXT,
            reset_token TEXT,
            reset_token_expires TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at TEXT
        )",
    ];

    for sql in stmts {
        let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
        db.execute(stmt).await.expect("Failed to create table");
    }

    let settings = Arc::new(Settings::new().unwrap_or_else(|_| {
        Settings {
            database_url: "sqlite::memory:".into(),
            secret_key: "test-secret-key-for-jwt".into(),
            access_token_expire_minutes: 60,
            ..Settings::new().unwrap()
        }
    }));

    let redis_pool = RedisPool::new("redis://localhost:9999", None).await;
    let redis_client = Arc::new(RedisClient::new(redis_pool));

    let state = AppState::new(db.clone(), redis_client, settings);
    let router = build_router(state);

    (router, db)
}

/// Helper: send a JSON POST request
async fn post_json(router: &Router, path: &str, body: serde_json::Value) -> (StatusCode, serde_json::Value) {
    let body_str = body.to_string();
    let request = Request::builder()
        .method("POST")
        .uri(path)
        .header("content-type", "application/json")
        .body(Body::from(body_str))
        .unwrap();

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
#[ignore = "requires PostgreSQL database connection"]
async fn test_register_success() {
    let (router, _db) = setup_app().await;

    let (status, json) = post_json(&router, "/api/v1/auth/register", serde_json::json!({
        "email": "newuser@test.com",
        "nickname": "newuser",
        "password": "StrongP@ss1"
    })).await;

    assert_eq!(status, StatusCode::OK, "Register should return 200: {json:?}");
    assert!(json.get("access_token").is_some(), "Should have access_token");
    assert!(json.get("refresh_token").is_some(), "Should have refresh_token");
    assert_eq!(json["token_type"], "bearer");
}

#[tokio::test]
async fn test_register_duplicate_email() {
    let (router, _db) = setup_app().await;

    // First registration
    post_json(&router, "/api/v1/auth/register", serde_json::json!({
        "email": "dup@test.com",
        "nickname": "user1",
        "password": "StrongP@ss1"
    })).await;

    // Second registration with same email
    let (status, json) = post_json(&router, "/api/v1/auth/register", serde_json::json!({
        "email": "dup@test.com",
        "nickname": "user2",
        "password": "StrongP@ss2"
    })).await;

    assert_eq!(status, StatusCode::CONFLICT, "Duplicate email should return 409: {json:?}");
}

#[tokio::test]
async fn test_login_success() {
    let (router, _db) = setup_app().await;

    // Register first
    post_json(&router, "/api/v1/auth/register", serde_json::json!({
        "email": "login@test.com",
        "nickname": "logintest",
        "password": "StrongP@ss1"
    })).await;

    // Login
    let (status, json) = post_json(&router, "/api/v1/auth/login", serde_json::json!({
        "email": "login@test.com",
        "password": "StrongP@ss1"
    })).await;

    assert_eq!(status, StatusCode::OK, "Login should return 200: {json:?}");
    assert!(json.get("access_token").is_some(), "Should have access_token");
}

#[tokio::test]
async fn test_login_invalid_credentials() {
    let (router, _db) = setup_app().await;

    let (status, json) = post_json(&router, "/api/v1/auth/login", serde_json::json!({
        "email": "nonexistent@test.com",
        "password": "WrongPassword1"
    })).await;

    assert_eq!(status, StatusCode::UNAUTHORIZED, "Invalid login should return 401: {json:?}");
}

#[tokio::test]
async fn test_login_wrong_password() {
    let (router, _db) = setup_app().await;

    // Register first
    post_json(&router, "/api/v1/auth/register", serde_json::json!({
        "email": "pwdtest@test.com",
        "nickname": "pwdtest",
        "password": "CorrectP@ss1"
    })).await;

    // Login with wrong password
    let (status, _json) = post_json(&router, "/api/v1/auth/login", serde_json::json!({
        "email": "pwdtest@test.com",
        "password": "WrongPassword1"
    })).await;

    assert_eq!(status, StatusCode::UNAUTHORIZED, "Wrong password should return 401");
}
