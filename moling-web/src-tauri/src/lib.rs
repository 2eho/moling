//! 墨灵 (Moling) Desktop Shell
//!
//! This crate is the Tauri v2 desktop shell for the Moling AI novel writing
//! platform. It follows a strict "shell is a shell" architecture:
//!
//! - Window management, system tray, native dialogs, and IPC bridging live here.
//! - All business logic, encryption, persistence, and heavy computation live in
//!   the Axum backend (port 8000).
//! - The frontend (React 19 + Vite 7) is embedded via Tauri's webview.
//!
//! ## Architecture constraints
//!
//! - Zero local database / file index / encryption.
//! - Zero multi-threaded synchronisation primitives (`Mutex`, `Arc<Mutex<>>`, channels).
//! - IPC commands are thin: validate parameters, forward to backend HTTP API.
//! - Window-close → hide to tray (quit only via tray menu).

mod commands;
mod state;
mod tray;

use state::AppState;
use tauri::{Emitter, Manager};

/// Sets up window lifecycle handlers.
///
/// - `CloseRequested`: prevent close, hide to tray instead.
///   The application only exits via the tray "退出" menu item or
///   platform quit gesture (Cmd+Q on macOS).
fn setup_window_events(window: &tauri::WebviewWindow) {
    let window_handle = window.clone();

    window.on_window_event(move |event| {
        if let tauri::WindowEvent::CloseRequested { api, .. } = event {
            api.prevent_close();
            let _ = window_handle.hide();
        }
    });
}

/// Application entry point for all platforms.
///
/// On Windows, `#![windows_subsystem = "windows"]` (set in `main.rs`) prevents
/// a console window from appearing in release builds.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app_state = AppState::new();

    tauri::Builder::default()
        .manage(app_state)
        // --- Official Tauri plugins ---
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_fs::init())
        // --- Global shortcut: Ctrl+Shift+T / Cmd+Shift+T → toggle theme ---
        .plugin({
            let builder = tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                        let _ = app.emit("toggle-theme", ());
                    }
                });
            // Shortcut strings are hardcoded and statically valid — the Result
            // only fails for malformed shortcut strings, which can't happen here.
            let builder = builder
                .with_shortcut("Ctrl+Shift+T")
                .expect("hardcoded shortcut 'Ctrl+Shift+T' must be valid");
            let builder = builder
                .with_shortcut("Cmd+Shift+T")
                .expect("hardcoded shortcut 'Cmd+Shift+T' must be valid");
            builder.build()
        })
        // --- IPC command handlers ---
        .invoke_handler(tauri::generate_handler![
            commands::get_app_info,
            commands::check_backend_health,
            commands::set_titlebar_theme,
            commands::set_window_color,
            commands::check_update,
            commands::import_project,
            commands::export_project,
        ])
        // --- Application setup ---
        .setup(|app| {
            // System tray (show/hide/quit)
            tray::create_tray(app.handle())
                .inspect_err(|e| eprintln!("[moling] tray creation failed: {e}"))
                .ok();

            // Main window lifecycle
            let window = app
                .get_webview_window("main")
                .expect("main window must exist (check tauri.conf.json → app.windows)");

            // Close → hide to tray
            setup_window_events(&window);

            // Default to dark title bar (the app only supports dark themes)
            let _ = window.set_theme(Some(tauri::Theme::Dark));

            // Devtools in debug builds
            #[cfg(debug_assertions)]
            {
                window.open_devtools();
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to start Tauri application");
}
