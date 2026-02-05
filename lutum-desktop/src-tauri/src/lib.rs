// Lutum Veritas - Tauri Entry Point
// ==================================
// Startet Backend (Python) hidden beim App-Start

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::fs::{File, OpenOptions};
use std::io::Write;
use tauri::Manager;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

// Backend process handle
struct BackendProcess(Mutex<Option<Child>>);

// Helper: Log to file for debugging
fn log_to_file(msg: &str) {
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open("lutum_backend.log")
    {
        let _ = writeln!(file, "{}", msg);
    }
}

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

            let backend_main = resource_dir.join("lutum_backend").join("main.py");
            let backend_dir = resource_dir.join("lutum_backend");
            let python_exe = resource_dir.join("python").join("python.exe");

            log_to_file(&format!("Resource dir: {:?}", resource_dir));
            log_to_file(&format!("Backend main: {:?}", backend_main));
            log_to_file(&format!("Backend exists: {}", backend_main.exists()));
            log_to_file(&format!("Python exe: {:?}", python_exe));
            log_to_file(&format!("Python exists: {}", python_exe.exists()));

            if backend_main.exists() {
                println!("Starting backend from: {:?}", backend_main);
                log_to_file(&format!("Starting backend from: {:?}", backend_main));

                // Log file für Backend stderr
                let log_file = File::create(backend_dir.join("backend_stderr.log"))
                    .map(Stdio::from)
                    .unwrap_or(Stdio::null());

                // Embedded Python hidden starten (CREATE_NO_WINDOW)
                #[cfg(windows)]
                let child = Command::new(&python_exe)
                    .arg(&backend_main)
                    .current_dir(&backend_dir)
                    .stdout(Stdio::null())
                    .stderr(log_file)
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .spawn();

                #[cfg(not(windows))]
                let child = Command::new("python3")
                    .arg(&backend_main)
                    .current_dir(&backend_dir)
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn();

                match child {
                    Ok(process) => {
                        let state = app.state::<BackendProcess>();
                        *state.0.lock().unwrap() = Some(process);
                        println!("Backend started successfully on port 8420");
                        log_to_file("Backend started successfully on port 8420");
                    }
                    Err(e) => {
                        eprintln!("Failed to start backend with embedded Python: {}", e);
                        log_to_file(&format!("Failed to start backend with embedded Python: {}", e));
                        // Embedded Python sollte immer da sein - kein Fallback mehr nötig
                    }
                }
            } else {
                eprintln!("Backend not found at {:?}", backend_main);
                log_to_file(&format!("Backend NOT FOUND at {:?}", backend_main));
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
