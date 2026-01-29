// Lutum Veritas - Tauri Entry Point
// ==================================
// Backend wird als Resource gestartet (simpler als Sidecar)

use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

// Backend process handle
struct BackendProcess(Mutex<Option<Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Backend exe finden (neben der App oder als Resource)
            let app_dir = app.path().resource_dir()
                .expect("Failed to get resource dir");

            let backend_path = app_dir.join("lutum-backend.exe");

            if backend_path.exists() {
                println!("Starting backend from: {:?}", backend_path);

                // Backend starten (ohne Console-Fenster)
                #[cfg(windows)]
                let child = Command::new(&backend_path)
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .spawn();

                #[cfg(not(windows))]
                let child = Command::new(&backend_path).spawn();

                match child {
                    Ok(process) => {
                        let state = app.state::<BackendProcess>();
                        *state.0.lock().unwrap() = Some(process);
                        println!("Backend started successfully on port 8420");
                    }
                    Err(e) => {
                        eprintln!("Failed to start backend: {}", e);
                    }
                }
            } else {
                eprintln!("Backend not found at {:?}", backend_path);
                // Versuche es im selben Ordner wie die exe
                if let Ok(exe_dir) = std::env::current_exe() {
                    let alt_path = exe_dir.parent().unwrap().join("lutum-backend.exe");
                    if alt_path.exists() {
                        println!("Found backend at: {:?}", alt_path);
                        #[cfg(windows)]
                        let child = Command::new(&alt_path)
                            .creation_flags(0x08000000)
                            .spawn();

                        #[cfg(not(windows))]
                        let child = Command::new(&alt_path).spawn();

                        if let Ok(process) = child {
                            let state = app.state::<BackendProcess>();
                            *state.0.lock().unwrap() = Some(process);
                            println!("Backend started from exe dir");
                        }
                    }
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendProcess>();
                let mut guard = state.0.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                    println!("Backend process terminated");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
