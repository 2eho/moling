use crate::state::AppState;
use serde::{Deserialize, Serialize};
use tauri::State;
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_updater::UpdaterExt;

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
pub struct AppInfo {
    pub name: String,
    pub version: String,
    pub backend_url: String,
    pub platform: String,
    pub arch: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendHealth {
    pub reachable: bool,
    pub status: Option<serde_json::Value>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateCheckResult {
    pub available: bool,
    pub version: Option<String>,
    pub body: Option<String>,
    pub date: Option<String>,
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

/// Returns application metadata including platform detection.
///
/// Used by the frontend shell to adapt UI for the current platform
/// (e.g. window controls placement on macOS vs Windows).
#[tauri::command]
pub fn get_app_info(state: State<'_, AppState>) -> Result<AppInfo, String> {
    Ok(AppInfo {
        name: env!("CARGO_PKG_NAME").to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        backend_url: state.backend_url().to_string(),
        platform: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    })
}

/// Checks whether the Axum backend is reachable.
///
/// Proxies a GET to `/api/health` on the backend. This is a thin pass-through —
/// the shell does not interpret the response body, only whether the backend
/// responded at all. All health semantics belong to the backend.
#[tauri::command]
pub async fn check_backend_health(
    state: State<'_, AppState>,
) -> Result<BackendHealth, String> {
    let url = format!("{}/api/health", state.backend_url());

    let client = reqwest::Client::builder()
        .connect_timeout(std::time::Duration::from_secs(3))
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| format!("Failed to build HTTP client: {e}"))?;

    match client.get(&url).send().await {
        Ok(resp) => {
            let status = resp.json::<serde_json::Value>().await.ok();
            Ok(BackendHealth {
                reachable: true,
                status,
                error: None,
            })
        }
        Err(e) => Ok(BackendHealth {
            reachable: false,
            status: None,
            error: Some(format!("{e}")),
        }),
    }
}

/// Sets the window theme for the title bar.
///
/// Maps frontend theme names to Tauri Theme variants.
/// This is intentionally a thin mapping — the theme *implementation*
/// lives entirely in the React frontend.
#[tauri::command]
pub fn set_titlebar_theme(window: tauri::Window, theme: String) -> Result<(), String> {
    let is_dark = !matches!(
        theme.as_str(),
        "solarized-light" | "paper" | "github-light"
    );
    window
        .set_theme(if is_dark {
            Some(tauri::Theme::Dark)
        } else {
            Some(tauri::Theme::Light)
        })
        .map_err(|e| e.to_string())
}

// ---------------------------------------------------------------------------
// Update commands
// ---------------------------------------------------------------------------

/// Checks for available updates via the configured updater endpoint.
///
/// Returns update availability and metadata. The frontend can then prompt
/// the user and call the updater's JS API to download and install.
///
/// Errors are returned as `Err(String)` only for configuration issues;
/// a failed network check still returns `Ok(UpdateCheckResult { available: false })`.
#[tauri::command]
pub async fn check_update(app: tauri::AppHandle) -> Result<UpdateCheckResult, String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Updater plugin not configured: {e}"))?;

    match updater.check().await {
        Ok(Some(update)) => Ok(UpdateCheckResult {
            available: true,
            version: Some(update.version.clone()),
            body: update.body.clone(),
            date: update.date.map(|d| d.to_string()),
        }),
        Ok(None) => Ok(UpdateCheckResult {
            available: false,
            version: None,
            body: None,
            date: None,
        }),
        Err(e) => {
            // Network or endpoint errors are not fatal — report as no update
            eprintln!("[moling] update check failed: {e}");
            Ok(UpdateCheckResult {
                available: false,
                version: None,
                body: None,
                date: None,
            })
        }
    }
}

// ---------------------------------------------------------------------------
// File import / export commands
// ---------------------------------------------------------------------------

/// Opens a native file dialog to select a `.moling` project file,
/// reads its contents, and returns the parsed JSON.
///
/// This is a thin shell operation:
/// 1. Native file picker (user explicitly chooses the file)
/// 2. Read bytes from disk
/// 3. Parse as JSON (basic structural validation only)
///
/// The returned JSON is forwarded to the frontend, which sends it to
/// the Axum backend for full project validation and import.
#[tauri::command]
pub async fn import_project(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let file_path = app
        .dialog()
        .file()
        .add_filter("墨灵项目包", &["moling"])
        .blocking_pick_file();

    let path = file_path.ok_or_else(|| "用户取消了文件选择".to_string())?;
    let path_str = path
        .as_path()
        .ok_or_else(|| "无法解析文件路径".to_string())?
        .to_string_lossy()
        .to_string();

    let bytes = std::fs::read(&path_str)
        .map_err(|e| format!("读取文件失败: {e}"))?;

    let value: serde_json::Value = serde_json::from_slice(&bytes)
        .map_err(|e| format!("项目文件格式无效 (非 JSON): {e}"))?;

    Ok(value)
}

/// Receives serialized project data, opens a native save dialog,
/// and writes the data to the chosen `.moling` file.
///
/// This is a thin shell operation:
/// 1. Validate that `data` is syntactically valid JSON
/// 2. Native save dialog (user explicitly chooses the destination)
/// 3. Write bytes to disk
///
/// All project serialisation logic belongs to the frontend/backend.
/// The shell only writes what it is given.
#[tauri::command]
pub async fn export_project(app: tauri::AppHandle, data: String) -> Result<(), String> {
    // Validate that data is syntactically valid JSON before writing
    let _: serde_json::Value = serde_json::from_str(&data)
        .map_err(|e| format!("项目数据无效 (非 JSON): {e}"))?;

    let file_path = app
        .dialog()
        .file()
        .add_filter("墨灵项目包", &["moling"])
        .blocking_save_file();

    let path = file_path.ok_or_else(|| "用户取消了文件保存".to_string())?;
    let path_str = path
        .as_path()
        .ok_or_else(|| "无法解析文件路径".to_string())?
        .to_string_lossy()
        .to_string();

    std::fs::write(&path_str, &data)
        .map_err(|e| format!("写入文件失败: {e}"))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Window chrome commands
// ---------------------------------------------------------------------------

/// Sets the webview window background color to match the active theme.
///
/// Receives a hex color string (e.g. `"#0f1117"`) from the frontend
/// and applies it to the current window's webview background. This
/// prevents a white/black flash during theme transitions and makes
/// the window chrome feel native to the active theme.
///
/// This is a thin shell operation: parse hex → call native API.
/// All theme logic lives in the React frontend.
#[tauri::command]
pub fn set_window_color(window: tauri::Window, color: String) -> Result<(), String> {
    let hex = color.trim_start_matches('#');
    if hex.len() != 6 {
        return Err(format!("Invalid hex color length: expected 6 hex chars, got {}", hex.len()));
    }

    let r = u8::from_str_radix(&hex[0..2], 16)
        .map_err(|e| format!("Invalid hex red component: {e}"))?;
    let g = u8::from_str_radix(&hex[2..4], 16)
        .map_err(|e| format!("Invalid hex green component: {e}"))?;
    let b = u8::from_str_radix(&hex[4..6], 16)
        .map_err(|e| format!("Invalid hex blue component: {e}"))?;

    window
        .set_background_color(Some(tauri::webview::Color(r, g, b, 255)))
        .map_err(|e| e.to_string())
}
