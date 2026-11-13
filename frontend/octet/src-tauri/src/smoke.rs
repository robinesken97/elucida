// Smoke test of the real app (CI, `--features smoke`): Octet starts and is asked to open two drawings, as from Finder.
// The first opens in Home's window, the second in a new drawing window, whose page starts and tells Octet its name.
// Edit > Paste in Home's window pastes into its drawing.
// File > New For there makes one more window, and File > Home brings Home back. Each step must answer on the main
// thread, so a hang (as on Windows when a synchronous command made a window) fails it. Ends with 0, or 1 and the step.
use std::sync::mpsc;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, Manager};

fn wait(what: &str, secs: u64, mut done: impl FnMut() -> bool) {
    let start = Instant::now();
    while !done() {
        if start.elapsed() > Duration::from_secs(secs) {
            eprintln!("smoke: failed: {what}");
            std::process::exit(1);
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    eprintln!("smoke: ok: {what}");
}

// The main thread answers within 10 seconds.
fn alive(app: &AppHandle, what: &str) {
    let (tx, rx) = mpsc::channel();
    let _ = app.run_on_main_thread(move || {
        let _ = tx.send(());
    });
    if rx.recv_timeout(Duration::from_secs(10)).is_err() {
        eprintln!("smoke: failed: the app hangs after {what}");
        std::process::exit(1);
    }
}

pub fn start(app: AppHandle) {
    std::thread::spawn(move || {
        wait("Home is open", 60, || app.get_webview_window("main").is_some());
        std::thread::sleep(Duration::from_secs(15)); // Home's page loads
        alive(&app, "starting");
        let dir = std::env::temp_dir().join("octet-smoke");
        let _ = std::fs::create_dir_all(&dir);
        let files: Vec<_> = ["one", "two"].iter().map(|n| dir.join(format!("{n}.cdxml"))).collect();
        for f in &files {
            let _ = std::fs::write(f, r#"<?xml version="1.0" encoding="UTF-8" ?><CDXML><page id="1"><fragment id="2"><n id="3" p="100 100"/></fragment></page></CDXML>"#);
        }
        crate::open::offer(&app, files, None);
        let named = |app: &AppHandle, label: &str| crate::windows::window_list(app.state()).iter().find(|i| i.label().starts_with(label)).map(|i| i.name().to_string());
        wait("the second drawing opens in a new window, and its page starts", 90, || named(&app, "draw-").is_some());
        alive(&app, "opening two drawings");
        wait("the first drawing is in Home's window, the second in the new one", 30, || {
            named(&app, "main").as_deref() == Some("one") && named(&app, "draw-").as_deref() == Some("two")
        });
        // Edit > Paste in Home's window, which holds the first drawing, pastes into that drawing.
        let edited = |app: &AppHandle| crate::windows::window_list(app.state()).iter().any(|i| i.label() == "main" && i.edited());
        let _ = tauri::async_runtime::block_on(crate::clipboard::copy_to_clipboard(app.clone(), None, None, None, None, None, None, None, None, Some("CCO".into()), None));
        let _ = app.emit_to("main", "menu", "paste");
        wait("Edit > Paste pastes into the drawing in Home's window", 30, || edited(&app));
        alive(&app, "Edit > Paste");
        let label = crate::windows::window_list(app.state()).iter().find(|i| i.label().starts_with("draw-")).unwrap().label().to_string();
        // A menu command runs in the window it is sent to, and only there: File > New For > Paper makes one window.
        let count = |app: &AppHandle| crate::windows::window_list(app.state()).len();
        let before = count(&app);
        let _ = app.emit_to(label.as_str(), "menu", "new_paper");
        wait("File > New For > Paper opens a drawing window", 60, || count(&app) > before);
        std::thread::sleep(Duration::from_secs(5));
        if count(&app) != before + 1 {
            eprintln!("smoke: failed: File > New For > Paper opened {} windows", count(&app) - before);
            std::process::exit(1);
        }
        alive(&app, "File > New For");
        let _ = app.emit_to(label, "menu", "home");
        std::thread::sleep(Duration::from_secs(3));
        alive(&app, "File > Home");
        eprintln!("smoke: passed");
        std::process::exit(0);
    });
}
