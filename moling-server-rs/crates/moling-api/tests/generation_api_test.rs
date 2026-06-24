//! Integration tests for Generation API routes.
//!
//! Tests: generate chapter (200), get job (200), job not found (404).

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

    let stmts = [
        "CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '', role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
        )",
        "CREATE TABLE IF NOT EXISTS generation_tasks (
            id TEXT PRIMARY KEY, project_id INTEGER NOT NULL DEFAULT 0,
            chapter_id TEXT, user_id TEXT NOT NULL DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'generate',
            status TEXT NOT NULL DEFAULT 'pending',
            input_params TEXT, output_data TEXT, progress_stage TEXT,
            progress_percent INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT
        )",
    ];

    for sql in stmts {
        let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
        db.execute(stmt).await.expect("Failed to create table");
    }

    let user_id = Uuid::new_v4();
    let uid = user_id.to_string();
    db.execute(Statement::from_string(DbBackend::Sqlite,
        format!("INSERT INTO users (id, email, username, password_hash, role, status) VALUES ('{uid}', 'test@test.com', 'genuser', 'hash', 'user', 'active')")
    )).await.unwrap();

    let settings = Arc::new(Settings::new().unwrap());
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
async fn test_generate_chapter_success() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_post(&router,
        "/api/v1/generation/chapters/test-chapter-id/generate",
        serde_json::json!({"mode": "generate_chapter", "temperature": 0.7}),
        &user).await;

    assert_eq!(status, StatusCode::OK, "Generate should return 200: {json:?}");
    assert!(json.get("id").is_some(), "Should have job id");
    assert_eq!(json["status"], "pending");
}

#[tokio::test]
async fn test_generate_without_auth() {
    let (router, _db, _user_id) = setup_app().await;

    let body_str = serde_json::json!({"mode": "test"}).to_string();
    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/generation/chapters/test-id/generate")
        .header("content-type", "application/json")
        .body(Body::from(body_str))
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    assert!(response.status().is_client_error(),
        "Request without auth should fail, got {}", response.status());
}

#[tokio::test]
async fn test_get_job_not_found() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    let (status, json) = authed_get(&router,
        "/api/v1/generation/jobs/00000000-0000-0000-0000-000000000000",
        &user).await;

    assert_eq!(status, StatusCode::NOT_FOUND, "Non-existent job should return 404: {json:?}");
}

#[tokio::test]
async fn test_get_job_success() {
    let (router, _db, user_id) = setup_app().await;
    let user = current_user(&user_id);

    // Create a job first
    let (_, create_json) = authed_post(&router,
        "/api/v1/generation/chapters/test-chapter/generate",
        serde_json::json!({"mode": "generate", "temperature": 0.5}),
        &user).await;

    let job_id = create_json["id"].as_str().unwrap();

    // Get the job
    let (status, json) = authed_get(&router,
        &format!("/api/v1/generation/jobs/{job_id}"),
        &user).await;

    assert_eq!(status, StatusCode::OK, "Get job should return 200: {json:?}");
    assert_eq!(json["id"], job_id);
    assert_eq!(json["status"], "pending");
}
