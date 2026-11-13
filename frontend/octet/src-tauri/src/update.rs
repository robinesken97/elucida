// Updates (decision 0010). Octet never checks by itself: the page asks for a check only when the user said yes to
// automatic checks (on first launch, or later in Settings), or chose Check for Updates. Every update is signed, and
// the updater installs it only when the signature matches the public key in tauri.conf.json.
use std::sync::Mutex;
use std::time::Duration;

use tauri::{AppHandle, State};
use tauri_plugin_updater::{Update, UpdaterExt};

// The update the last check found, kept for Install.
#[derive(Default)]
pub struct Found(Mutex<Option<Update>>);

// The newer version, or None when Octet is up to date. With no network the check fails, and the page says so only
// when the user asked. A check that gets no answer stops after 30 s.
#[tauri::command]
pub async fn update_check(app: AppHandle, found: State<'_, Found>) -> Result<Option<String>, String> {
    let updater = app.updater_builder().timeout(Duration::from_secs(30)).build().map_err(|e| e.to_string())?;
    let update = updater.check().await.map_err(|e| e.to_string())?;
    let version = update.as_ref().map(|u| u.version.clone());
    *found.0.lock().unwrap() = update;
    Ok(version)
}

// Downloads the update found, checks its signature, installs it and starts Octet again. The page asks to save the
// drawing first. The download has no time limit, as a slow network needs longer. On Windows the installer closes
// Octet itself. On the Mac the new Octet opens once this one has ended (open_when_ended), so it keeps its Dock icon.
#[tauri::command]
pub async fn update_install(app: AppHandle, found: State<'_, Found>) -> Result<(), String> {
    let mut update = found.0.lock().unwrap().take().ok_or("Octet found no update to install.")?;
    update.timeout = None;
    update.download_and_install(|_, _| {}, || {}).await.map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    if open_when_ended().is_ok() {
        app.exit(0);
        return Ok(());
    }
    app.restart()
}

// Opens Octet's app once this process has ended, as Sparkle does. Tauri's restart opens a second Octet while this one
// still runs: the Dock gives that one an icon of its own, and the icon kept in the Dock loses its dot.
#[cfg(target_os = "macos")]
fn open_when_ended() -> std::io::Result<()> {
    use std::os::unix::process::CommandExt;
    use std::process::{Command, Stdio};
    let exe = std::env::current_exe()?;
    let app = exe.ancestors().nth(3).filter(|p| p.extension().is_some_and(|e| e == "app")).ok_or(std::io::ErrorKind::NotFound)?;
    Command::new("/bin/sh")
        .args(["-c", "while kill -0 \"$0\" 2>/dev/null; do sleep 0.1; done; sleep 0.5; exec /usr/bin/open \"$1\""])
        .arg(std::process::id().to_string())
        .arg(app)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .process_group(0)
        .spawn()
        .map(|_| ())
}
