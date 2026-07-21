#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use std::net::TcpStream;
use std::io::{Read, Write};
use std::thread;
use std::time::Duration;
use tauri::Manager;

#[derive(serde::Serialize)]
struct AppVersion {
    version: String,
    tauri_version: String,
}

#[derive(serde::Serialize)]
struct SystemInfo {
    platform: String,
    os_version: String,
    arch: String,
    locale: String,
}

#[tauri::command]
fn get_app_version(app: tauri::AppHandle) -> AppVersion {
    AppVersion {
        version: app.package_info().version.to_string(),
        tauri_version: tauri::VERSION.to_string(),
    }
}

#[tauri::command]
fn get_system_info() -> SystemInfo {
    SystemInfo {
        platform: std::env::consts::OS.to_string(),
        os_version: os_info_version(),
        arch: std::env::consts::ARCH.to_string(),
        locale: sys_locale::get_locale().unwrap_or_else(|| "zh-CN".to_string()),
    }
}

fn os_info_version() -> String {
    if cfg!(target_os = "windows") {
        Command::new("cmd")
            .args(["/c", "ver"])
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| "Windows".to_string())
    } else if cfg!(target_os = "macos") {
        Command::new("sw_vers")
            .args(["-productVersion"])
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| "macOS".to_string())
    } else if cfg!(target_os = "linux") {
        Command::new("uname")
            .args(["-r"])
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| "Linux".to_string())
    } else {
        "Unknown".to_string()
    }
}

fn check_backend_ready(port: u16) -> bool {
    if let Ok(mut stream) = TcpStream::connect(format!("127.0.0.1:{}", port)) {
        let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
        let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));

        let request = format!(
            "GET /api/system/health HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n\r\n",
            port
        );

        if let Ok(_) = stream.write_all(request.as_bytes()) {
            let mut response = String::new();
            if let Ok(_) = stream.read_to_string(&mut response) {
                return response.contains("200 OK");
            }
        }
    }
    false
}

fn find_available_port(start: u16) -> u16 {
    let mut port = start;
    while port < 65535 {
        if TcpStream::connect(format!("127.0.0.1:{}", port)).is_err() {
            return port;
        }
        port += 1;
    }
    start
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .invoke_handler(tauri::generate_handler![
            get_app_version,
            get_system_info
        ])
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();

            {
                let window = window.clone();
                thread::spawn(move || {
                    let port = find_available_port(8000);

                    let resource_dir = std::env::current_exe()
                        .ok()
                        .and_then(|p| p.parent().map(|p| p.to_path_buf()));

                    let backend_started = if let Some(dir) = resource_dir {
                        let backend_paths = [
                            dir.join("../Resources/backend/main.py"),
                            dir.join("backend/main.py"),
                            dir.join("../../backend/main.py"),
                        ];

                        let mut started = false;
                        for backend_path in &backend_paths {
                            if backend_path.exists() {
                                if let Some(parent) = backend_path.parent() {
                                    let _ = Command::new("python")
                                        .arg(backend_path)
                                        .env("PORT", port.to_string())
                                        .current_dir(parent)
                                        .spawn();
                                    started = true;
                                    break;
                                }
                            }
                        }
                        started
                    } else {
                        false
                    };

                    if backend_started {
                        for _ in 0..30 {
                            thread::sleep(Duration::from_secs(1));
                            if check_backend_ready(port) {
                                let _ = window.eval(&format!(
                                    "window.__TAURI_BACKEND_PORT__={};window.__TAURI_BACKEND_READY__=true;",
                                    port
                                ));
                                break;
                            }
                        }
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() {
    run();
}
