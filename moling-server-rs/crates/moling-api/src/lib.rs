//! 墨灵 (Moling) — API routing layer.
//!
//! Assembles the Axum [`Router`] from 16 route modules with full middleware
//! stack and shared [`AppState`].
//!
//! # Usage
//!
//! ```ignore
//! use moling_api::{build_router, AppState};
//! let app = build_router(state);
//! axum::serve(listener, app).await?;
//! ```

pub mod error_handler;
pub mod middleware;
pub mod routes;
pub mod state;
pub mod types;

use axum::Router;
use utoipa_swagger_ui::SwaggerUi;

pub use state::AppState;

use utoipa::OpenApi;

/// Moling API OpenAPI documentation.
#[derive(OpenApi)]
#[openapi(
    info(
        title = "Moling API",
        version = "0.1.0",
        description = "墨灵网文续写辅助工具 API"
    ),
    paths(
        // auth
        crate::routes::auth::register,
        crate::routes::auth::login,
        crate::routes::auth::refresh,
        crate::routes::auth::logout,
        crate::routes::auth::get_me,
        crate::routes::auth::update_me,
        crate::routes::auth::password_reset_request,
        crate::routes::auth::password_reset,
        // project
        crate::routes::project::create_project,
        crate::routes::project::get_project,
        crate::routes::project::list_projects,
        crate::routes::project::update_project,
        crate::routes::project::delete_project,
        // chapter
        crate::routes::chapter::create_chapter,
        crate::routes::chapter::list_chapters,
        crate::routes::chapter::get_chapter,
        crate::routes::chapter::update_chapter,
        crate::routes::chapter::delete_chapter,
        // generation
        crate::routes::generation::generate,
        crate::routes::generation::get_job,
    ),
    components(schemas(
        crate::types::RegisterReq,
        crate::types::LoginReq,
        crate::types::RefreshReq,
        crate::types::LogoutReq,
        crate::types::PasswordResetRequestReq,
        crate::types::PasswordResetReq,
        crate::types::UpdateProfileReq,
        crate::types::UserResp,
        crate::types::TokenResp,
        crate::types::MessageResponse,
        crate::types::CreateProjectReq,
        crate::types::UpdateProjectReq,
        crate::types::ProjectResp,
        crate::types::CreateChapterReq,
        crate::types::UpdateChapterReq,
        crate::types::ReorderChaptersReq,
        crate::types::ChapterResp,
        crate::types::GenerateReq,
        crate::types::GenerationJobResp,
    ))
)]
pub struct ApiDoc;

/// Build the complete Axum router with all routes and middleware.
///
/// Routes are organized by domain under `/api/v1`:
///
/// | Prefix | Module | Tags |
/// |--------|--------|------|
/// | `/api/v1/auth` | `routes::auth` | auth |
/// | `/api/v1/projects` | `routes::project` | projects |
/// | `/api/v1/projects/{project_id}/chapters` | `routes::chapter` | chapters |
/// | `/api/v1/projects/{project_id}/cards` | `routes::card` | cards |
/// | `/api/v1/projects/{project_id}/vault` | `routes::vault` | vault |
/// | `/api/v1/projects/{project_id}/secrets` | `routes::secret` | secrets |
/// | `/api/v1/generation` | `routes::generation` | generation |
/// | `/api/v1/health` | `routes::health` | health |
/// | `/api/v1/admin` | `routes::admin` | admin |
/// | `/api/v1/notifications` | `routes::notification` | notifications |
/// | `/api/v1/settings` | `routes::setting` | settings |
/// | `/api/v1/templates` | `routes::template` | templates |
/// | `/api/v1/phase4` | `routes::phase4` | phase4 |
/// | `/api/v1/weave` | `routes::weave` | weave |
/// | `/api/v1/subscriptions` | `routes::subscription` | subscriptions |
/// | `/api/v1/projects/{project_id}/import` | `routes::import_route` | import |
/// | `/api/v1/genre` | `routes::genre` | genre |
pub fn build_router(state: AppState) -> Router {
    // Record server start time for uptime metrics
    middleware::metrics::record_start_time();

    // API router — all `/api/v1` routes
    let api_router = Router::new()
        .nest("/auth", routes::auth::router())
        .nest("/projects", routes::project::router())
        .nest("/projects/{project_id}", nested_project_routes())
        .nest("/projects/{project_id}/vault", routes::vault::router())
        .nest("/projects/{project_id}/secrets", routes::secret::router())
        .nest("/generation", routes::generation::router())
        .nest("/health", routes::health::router())
        .nest("/admin", routes::admin::router())
        .nest("/notifications", routes::notification::router())
        .nest("/settings", routes::setting::router())
        .nest("/templates", routes::template::router())
        .nest("/phase4", routes::phase4::router())
        .nest("/weave", routes::weave::router())
        .nest("/subscriptions", routes::subscription::router())
        .nest("/projects/{project_id}/import", routes::import_route::router())
        .nest("/genre", routes::genre::router())
        .nest("/metrics", routes::metrics::router())
        .with_state(state.clone());

    // Root router with `/api/v1` prefix and full middleware stack
    Router::new()
        .merge(SwaggerUi::new("/api/swagger-ui").url("/api/openapi.json", ApiDoc::openapi()))
        .nest("/api/v1", api_router)
        .layer(
            tower::ServiceBuilder::new()
                .layer(axum::middleware::from_fn(
                    middleware::request_id::request_id_middleware,
                ))
                .layer(axum::middleware::from_fn(
                    middleware::metrics::metrics_middleware,
                ))
                .layer(axum::middleware::from_fn(
                    middleware::sentry::sentry_middleware,
                ))
                .layer(axum::middleware::from_fn(
                    middleware::audit_log::audit_log_middleware,
                ))
                .layer(axum::middleware::from_fn(
                    middleware::response_format::response_format_middleware,
                ))
                .layer(axum::middleware::from_fn(
                    middleware::content_length::content_length_middleware,
                ))
                .layer(axum::middleware::from_fn_with_state(
                    state.redis.clone(),
                    middleware::rate_limit::rate_limit_middleware,
                ))
                .layer(tower_http::trace::TraceLayer::new_for_http())
                .into_inner(),
        )
        .layer(middleware::cors::cors_middleware("*"))
}

/// Nested routes under `/projects/{project_id}`:
/// chapters, cards, and project_health share the project_id prefix.
fn nested_project_routes() -> Router<AppState> {
    Router::new()
        .merge(routes::chapter::router())
        .merge(routes::card::router())
        .merge(routes::project_health::router())
}
