use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, Runtime,
};

/// Creates the system tray icon and its context menu.
///
/// Tray behaviour by platform (per platform difference matrix):
/// - Windows: left-click shows context menu, right-click shows context menu
/// - macOS:   right-click shows context menu
/// - Linux:   depends on DE, left-click typically shows menu
///
/// Menu items:
/// - 显示窗口 (Show Window) — restores and focuses the main window
/// - 隐藏窗口 (Hide Window) — hides the main window to tray
/// - ──────────
/// - 退出 (Quit) — fully exits the application
pub fn create_tray<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let show_item =
        MenuItemBuilder::with_id("show", "显示窗口").build(app)?;
    let hide_item =
        MenuItemBuilder::with_id("hide", "隐藏窗口").build(app)?;
    let quit_item =
        MenuItemBuilder::with_id("quit", "退出").build(app)?;

    let menu = MenuBuilder::new(app)
        .item(&show_item)
        .item(&hide_item)
        .separator()
        .item(&quit_item)
        .build()?;

    let icon = app
        .default_window_icon()
        .cloned()
        .ok_or_else(|| tauri::Error::from(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            "default window icon not found — ensure icons are configured in tauri.conf.json",
        )))?;

    let _tray = TrayIconBuilder::new()
        .icon(icon)
        .tooltip("墨灵 — Vibe Writing")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(move |app_handle, event| {
            handle_tray_menu_event(app_handle, event.id().as_ref());
        })
        .on_tray_icon_event(|tray_handle, event| {
            // On left-click, toggle window visibility
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                toggle_main_window(tray_handle.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

/// Handles tray menu item clicks.
fn handle_tray_menu_event(app: &AppHandle<impl Runtime>, item_id: &str) {
    match item_id {
        "show" => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        "hide" => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.hide();
            }
        }
        "quit" => {
            app.exit(0);
        }
        _ => {}
    }
}

/// Toggles the main window between shown and hidden.
fn toggle_main_window(app: &AppHandle<impl Runtime>) {
    if let Some(window) = app.get_webview_window("main") {
        match window.is_visible() {
            Ok(true) => {
                let _ = window.hide();
            }
            Ok(false) => {
                let _ = window.show();
                let _ = window.set_focus();
            }
            Err(_) => {}
        }
    }
}
