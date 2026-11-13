// The crash log (REL-23): a short record of each Rust panic and each error the page reports, in the app's log folder
// on this computer. Octet sends it nowhere. After a crash, the next start offers the log to the user (to show, or to
// email), and only the user decides.
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use tauri::{AppHandle, Manager};

const LOG: &str = "crash.log";
const NEW: &str = "crash.new"; // made by a crash; the next start offers the log, then removes it
const MAX_LOG: u64 = 256 * 1024; // a longer log becomes crash.old.log, and a new one starts
const TAIL: usize = 16_000; // bytes of the log the page gets to offer

// Seconds since 1970 as a UTC time, 2026-10-17 14:02:09 UTC (days to a date: Howard Hinnant's civil_from_days).
fn date(s: i64) -> String {
    let z = s.div_euclid(86_400) + 719_468;
    let (era, doe) = (z.div_euclid(146_097), z.rem_euclid(146_097));
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let (d, m) = (doy - (153 * mp + 2) / 5 + 1, if mp < 10 { mp + 3 } else { mp - 9 });
    let t = s.rem_euclid(86_400);
    format!("{:04}-{m:02}-{d:02} {:02}:{:02}:{:02} UTC", yoe + era * 400 + i64::from(m <= 2), t / 3600, t / 60 % 60, t % 60)
}

fn append(dir: &Path, text: &str, crash: bool) {
    let _ = fs::create_dir_all(dir);
    let path = dir.join(LOG);
    if fs::metadata(&path).is_ok_and(|m| m.len() > MAX_LOG) {
        let _ = fs::rename(&path, dir.join("crash.old.log"));
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&path) {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0);
        let _ = writeln!(file, "{} {text}\n", date(now));
        let _ = file.sync_all();
    }
    if crash {
        let _ = fs::write(dir.join(NEW), b"");
    }
}

fn head(app: &AppHandle) -> String {
    format!("Octet Draw {} on {} ({})", app.package_info().version, std::env::consts::OS, std::env::consts::ARCH)
}

// A panic closes Octet (the release build aborts). The hook writes it to the log first.
pub fn install(app: &AppHandle) {
    let Ok(dir) = app.path().app_log_dir() else { return };
    hook(dir, head(app));
}

fn hook(dir: PathBuf, head: String) {
    let next = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        append(&dir, &format!("{head}. Octet stopped: {info}"), true);
        next(info);
    }));
}

// An error from the page (8000 characters at most). crash: the editor stopped, so the next start offers the log.
#[tauri::command]
pub fn log_error(app: AppHandle, text: String, crash: bool) -> Result<(), String> {
    let dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
    let text: String = text.chars().filter(|c| !c.is_control() || *c == '\n').take(8000).collect();
    append(&dir, &format!("{}. {text}", head(&app)), crash);
    Ok(())
}

// After a crash, once: the end of the log, for the page to offer.
#[tauri::command]
pub fn crash_report(app: AppHandle) -> Option<String> {
    let dir = app.path().app_log_dir().ok()?;
    fs::remove_file(dir.join(NEW)).ok()?;
    let log = fs::read(dir.join(LOG)).ok()?;
    let mut from = log.len().saturating_sub(TAIL);
    while from < log.len() && (log[from] & 0xC0) == 0x80 {
        from += 1; // start on a whole character
    }
    Some(String::from_utf8_lossy(&log[from..]).into_owned())
}

// Opens the log in the system's app for it (Console on the Mac).
#[tauri::command]
pub fn show_log(app: AppHandle) -> Result<(), String> {
    let path = app.path().app_log_dir().map_err(|e| e.to_string())?.join(LOG);
    crate::open_external(&path).map_err(|_| "Octet cannot open the log.".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    // A panic goes to the log and marks a crash; a log longer than 256 KB becomes crash.old.log.
    #[test]
    fn a_panic_is_logged() {
        let dir = std::env::temp_dir().join(format!("octet-crashlog-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        hook(dir.clone(), "Octet test".into());
        let _ = std::panic::catch_unwind(|| panic!("index out of bounds"));
        let _ = std::panic::take_hook(); // the default hook again
        let log = fs::read_to_string(dir.join(LOG)).unwrap();
        assert!(log.contains("UTC Octet test. Octet stopped: panicked at") && log.contains("index out of bounds"), "{log}");
        assert!(dir.join(NEW).exists());
        fs::write(dir.join(LOG), vec![b'x'; MAX_LOG as usize + 1]).unwrap();
        append(&dir, "next", false);
        assert!(dir.join("crash.old.log").exists() && fs::read_to_string(dir.join(LOG)).unwrap().ends_with("next\n\n"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn dates() {
        assert_eq!(super::date(0), "1970-01-01 00:00:00 UTC");
        assert_eq!(super::date(951_782_400), "2000-02-29 00:00:00 UTC");
        assert_eq!(super::date(1_792_252_929), "2026-10-17 16:02:09 UTC");
    }
}
