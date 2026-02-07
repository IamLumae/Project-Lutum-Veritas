// Lutum Veritas - Tauri Entry Point
// ==================================
// Startet Backend (Frozen PyInstaller EXE) hidden beim App-Start

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
            // Backend EXE finden (im resources Ordner)
            let resource_dir = app.path().resource_dir()
                .expect("Failed to get resource dir");

            let backend_exe = resource_dir.join("backend").join("lutum-backend.exe");
            let backend_dir = resource_dir.join("backend");

            log_to_file(&format!("Resource dir: {:?}", resource_dir));
            log_to_file(&format!("Backend exe: {:?}", backend_exe));
            log_to_file(&format!("Backend exists: {}", backend_exe.exists()));

            if backend_exe.exists() {
                println!("Starting frozen backend from: {:?}", backend_exe);
                log_to_file(&format!("Starting frozen backend from: {:?}", backend_exe));

                // Log file für Backend stderr - wichtig für Debugging beim Kunden!
                let log_file = File::create(backend_dir.join("backend_stderr.log"))
                    .map(Stdio::from)
                    .unwrap_or(Stdio::null());

                // Frozen Backend hidden starten (CREATE_NO_WINDOW)
                #[cfg(windows)]
                let child = Command::new(&backend_exe)
                    .current_dir(&backend_dir)
                    .stdout(Stdio::null())
                    .stderr(log_file)
                    .creation_flags(0x08000000) // CREATE_NO_WINDOW
                    .spawn();

                #[cfg(not(windows))]
                let child = Command::new(&backend_exe)
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
                        eprintln!("Failed to start frozen backend: {}", e);
                        log_to_file(&format!("Failed to start frozen backend: {}", e));
                    }
                }
            } else {
                eprintln!("Backend EXE not found at {:?}", backend_exe);
                log_to_file(&format!("Backend EXE NOT FOUND at {:?}", backend_exe));
            }

            // Show window after WebView had time to render the splash screen
            let main_window = app.get_webview_window("main").unwrap();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_millis(1500));
                let _ = main_window.show();
            });

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
