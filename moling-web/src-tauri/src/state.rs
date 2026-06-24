/// Application state managed by Tauri.
///
/// Contains runtime configuration that is shared across commands.
/// This is intentionally minimal — heavy state lives in the Axum backend.
pub struct AppState {
    backend_url: String,
}

impl AppState {
    /// Creates the application state with default backend URL.
    ///
    /// The backend URL can be overridden via the `MOLING_BACKEND_URL`
    /// environment variable, useful for development and testing.
    pub fn new() -> Self {
        let backend_url = std::env::var("MOLING_BACKEND_URL")
            .unwrap_or_else(|_| "http://localhost:8000".to_string());
        Self { backend_url }
    }

    /// Returns the backend base URL.
    pub fn backend_url(&self) -> &str {
        &self.backend_url
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}
