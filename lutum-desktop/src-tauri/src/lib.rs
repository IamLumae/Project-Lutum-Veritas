// Lutum Veritas - Tauri Entry Point
// ==================================
// Startet Backend (Python) hidden beim App-Start

use std::process::{Child, Command, Stdio};
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
            // Backend main.py finden (im resources Ordner)
            let resource_dir = app.path().resource_dir()
                .expect("Failed to get resource dir");

            let backend_main = resource_dir.join("backend").join("main.py");

            if backend_main.exists() {
                println!("Starting backend from: {:?}", backend_main);

                // Python hidden starten (CREATE_NO_WINDOW)
                // Normales Python (nicht frozen) hat stdout auch wenn hidden!
                #[cfg(windows)]
                let child = Command::new("python")
                    .arg(&backend_main)
                    .current_dir(resource_dir.join("backend"))
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .spawn();

                #[cfg(not(windows))]
                let child = Command::new("python3")
                    .arg(&backend_main)
                    .current_dir(resource_dir.join("backend"))
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn();

                match child {
                    Ok(process) => {
                        let state = app.state::<BackendProcess>();
                        *state.0.lock().unwrap() = Some(process);
                        println!("Backend started successfully on port 8420");
                    }
                    Err(e) => {
                        eprintln!("Failed to start backend: {}", e);
                        // Fallback: Versuche py launcher (Windows)
                        #[cfg(windows)]
                        {
                            let fallback = Command::new("py")
                                .args(["-3", backend_main.to_str().unwrap()])
                                .current_dir(resource_dir.join("backend"))
                                .stdout(Stdio::null())
                                .stderr(Stdio::null())
                                .creation_flags(0x08000000)
                                .spawn();

                            if let Ok(process) = fallback {
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(process);
                                println!("Backend started via py launcher");
                            }
                        }
                    }
                }
            } else {
                eprintln!("Backend not found at {:?}", backend_main);
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            // Bei App-Close: Backend killen
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
