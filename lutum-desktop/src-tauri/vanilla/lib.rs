// Lutum Veritas - Tauri Entry Point (Vanilla)
// =============================================
// Startet Backend via System-Python (python main.py)
// User muss Python + Dependencies selbst installieren.

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

/// Find system Python (python or python3)
fn find_python() -> Option<String> {
    // Windows: try "python" first (py launcher), then "python3"
    for candidate in &["python", "python3"] {
        let result = Command::new(candidate)
            .arg("--version")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .spawn();

        if let Ok(mut child) = result {
            if let Ok(status) = child.wait() {
                if status.success() {
                    log_to_file(&format!("Found Python: {}", candidate));
                    return Some(candidate.to_string());
                }
            }
        }
    }
    None
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Backend source finden (im resources Ordner)
            let resource_dir = app.path().resource_dir()
                .expect("Failed to get resource dir");

            let backend_main = resource_dir.join("lutum_backend").join("main.py");
            let backend_dir = resource_dir.join("lutum_backend");

            log_to_file(&format!("Resource dir: {:?}", resource_dir));
            log_to_file(&format!("Backend main.py: {:?}", backend_main));
            log_to_file(&format!("Backend exists: {}", backend_main.exists()));

            if backend_main.exists() {
                // Find system Python
                match find_python() {
                    Some(python) => {
                        log_to_file(&format!("Using Python: {}", python));

                        // Log file for backend stderr
                        let log_file = File::create(backend_dir.join("backend_stderr.log"))
                            .map(Stdio::from)
                            .unwrap_or(Stdio::null());

                        // Start backend hidden (CREATE_NO_WINDOW)
                        #[cfg(windows)]
                        let child = Command::new(&python)
                            .arg(&backend_main)
                            .current_dir(&backend_dir)
                            .stdout(Stdio::null())
                            .stderr(log_file)
                            .creation_flags(0x08000000)
                            .spawn();

                        #[cfg(not(windows))]
                        let child = Command::new(&python)
                            .arg(&backend_main)
                            .current_dir(&backend_dir)
                            .stdout(Stdio::null())
                            .stderr(Stdio::null())
                            .spawn();

                        match child {
                            Ok(process) => {
                                let state = app.state::<BackendProcess>();
                                *state.0.lock().unwrap() = Some(process);
                                println!("Backend started with system Python on port 8420");
                                log_to_file("Backend started with system Python on port 8420");
                            }
                            Err(e) => {
                                eprintln!("Failed to start backend: {}", e);
                                log_to_file(&format!("Failed to start backend: {}", e));
                            }
                        }
                    }
                    None => {
                        eprintln!("Python not found! Install Python 3.11+ from python.org");
                        log_to_file("ERROR: Python not found! Install Python 3.11+ from python.org");
                    }
                }
            } else {
                eprintln!("Backend main.py not found at {:?}", backend_main);
                log_to_file(&format!("Backend main.py NOT FOUND at {:?}", backend_main));
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
