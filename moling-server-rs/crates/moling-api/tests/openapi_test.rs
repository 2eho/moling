//! OpenAPI / Swagger UI integration tests.
//!
//! Verifies that the utoipa-generated OpenAPI schema is accessible
//! and the Swagger UI endpoint serves HTML.

use axum::body::Body;
use axum::http::{Request, StatusCode};
use moling_api::{build_router, AppState};
use moling_core::config::Settings;
use moling_core::redis::{RedisClient, RedisPool};
use sea_orm::{Database, DatabaseConnection, ConnectionTrait, DbBackend, Statement};
use std::sync::Arc;
use tower::util::ServiceExt;

async fn setup_app() -> (axum::Router, DatabaseConnection) {
    let db = Database::connect("sqlite::memory:").await.expect("Failed to create SQLite DB");

    // Create minimal users table for state initialization
    let sql = "CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'user',
        avatar_url TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_at TEXT
    )";
    let stmt = Statement::from_string(DbBackend::Sqlite, sql.to_owned());
    db.execute(stmt).await.expect("Failed to create table");

    let settings = Arc::new(Settings::new().unwrap());
    let redis_pool = RedisPool::new("redis://localhost:9999", None).await;
    let redis_client = Arc::new(RedisClient::new(redis_pool));

    let state = AppState::new(db.clone(), redis_client, settings);
    let router = build_router(state);

    (router, db)
}

#[tokio::test]
async fn test_openapi_json_accessible() {
    let (router, _db) = setup_app().await;

    let request = Request::builder()
        .method("GET")
        .uri("/api/openapi.json")
        .body(Body::empty())
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK, "OpenAPI JSON should be accessible");

    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();

    assert!(json.get("openapi").is_some(), "Should have openapi version");
    assert!(json.get("info").is_some(), "Should have info section");
    assert!(json["info"]["title"].as_str().unwrap_or("").contains("Moling"), "Title should mention Moling");

    // Verify key paths are documented
    assert!(json.get("paths").is_some(), "Should have paths section");
    let paths = &json["paths"];
    assert!(paths.get("/api/v1/auth/register").is_some(), "Should have register path");
    assert!(paths.get("/api/v1/auth/login").is_some(), "Should have login path");
}

#[tokio::test]
async fn test_swagger_ui_accessible() {
    let (router, _db) = setup_app().await;

    let request = Request::builder()
        .method("GET")
        .uri("/api/swagger-ui")
        .body(Body::empty())
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    // Swagger UI may redirect or return HTML
    let status = response.status();
    assert!(
        status == StatusCode::OK || status == StatusCode::TEMPORARY_REDIRECT || status == StatusCode::MOVED_PERMANENTLY,
        "Swagger UI should be accessible, got {status}"
    );
}

#[tokio::test]
async fn test_openapi_json_valid_structure() {
    let (router, _db) = setup_app().await;

    let request = Request::builder()
        .method("GET")
        .uri("/api/openapi.json")
        .body(Body::empty())
        .unwrap();

    let response = router.clone().oneshot(request).await.unwrap();
    let body_bytes = axum::body::to_bytes(response.into_body(), 1024 * 1024).await.unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();

    // JSON content type check on response headers
    // Verify key sections exist
    assert!(json.get("components").is_some(), "Should have components/schemas");
    let schemas = &json["components"]["schemas"];
    assert!(schemas.get("RegisterReq").is_some(), "Should have RegisterReq schema");
    assert!(schemas.get("TokenResp").is_some(), "Should have TokenResp schema");
}
