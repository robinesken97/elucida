// Crash recovery (REL-1, CH-4): while the drawing has unsaved changes, the page keeps a copy of it in the app's data
// folder ("recovery"). Save, Don't Save and a clean close remove the copy, so a copy found later is a drawing that a
// crash, a force quit or a power cut took. Home offers it. Each Octet process locks a file of its own there while it
// runs (the system lets the lock go when the process ends, even in a crash), so a second copy of Octet never offers
// a drawing that is still open. Each drawing window keeps its own copy, named for the session and the window ("z" and
// the window's label without its hyphen). Files: <copy>.oct (the drawing), <copy>.json (its name and when it was
// kept) and <session>.lock. Copies Octet kept before it had more than one window are named for the session only.
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, State, Window};

use crate::{write_atomic, MAX_BYTES};

// Home lists every kept drawing up to this many (a bound on a folder that a fault fills).
const MAX_KEPT: usize = 1000;

pub struct Session {
    id: String,
    dir: Option<PathBuf>, // None when the app has no data folder: nothing is kept
    _lock: Option<File>,
}

#[derive(Serialize, Deserialize)]
struct Meta {
    name: String,
    at: u64, // seconds since 1970
}

#[derive(Serialize)]
pub struct Recovered {
    id: String,
    name: String,
    at: u64,
}

fn now() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

// A session id: letters and digits only, so it is safe in a file name.
fn valid(id: &str) -> bool {
    !id.is_empty() && id.len() <= 40 && id.bytes().all(|b| b.is_ascii_alphanumeric())
}

// The session that kept a copy.
fn session_of(id: &str) -> &str {
    id.split('z').next().unwrap_or(id)
}

// A window's copy: "draw-2" keeps <session>zdraw2.
fn copy_id(session: &str, label: &str) -> String {
    format!("{session}z{}", label.replace('-', ""))
}

// Another Octet still runs the session when it holds the session's lock.
fn live(dir: &Path, id: &str) -> bool {
    OpenOptions::new().write(true).open(dir.join(format!("{}.lock", session_of(id)))).is_ok_and(|f| f.try_lock().is_err())
}

// A copy that is not there is removed already. Any other failure is said: the page logs it (issue 2).
fn remove(dir: &Path, id: &str) -> Result<(), String> {
    let gone = |ext: &str| match fs::remove_file(dir.join(format!("{id}.{ext}"))) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(e.to_string()),
        _ => Ok(()),
    };
    gone("json").and(gone("oct"))
}

// The name and time kept with a drawing; without them (a crash between the two writes), "Untitled" and the file's time.
fn meta(dir: &Path, id: &str) -> Meta {
    let json = dir.join(format!("{id}.json"));
    let read = fs::metadata(&json).ok().filter(|m| m.len() <= 4096).and_then(|_| fs::read(&json).ok());
    read.and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_else(|| Meta {
        name: "Untitled".into(),
        at: fs::metadata(dir.join(format!("{id}.oct"))).and_then(|m| m.modified()).ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok()).map(|d| d.as_secs()).unwrap_or(0),
    })
}

impl Session {
    // This process's session in `dir`, locked. Lock files of ended sessions are removed (their copies stay).
    fn start_in(dir: Option<PathBuf>) -> Session {
        let nanos = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        let id = format!("{nanos:x}{:x}", std::process::id());
        let lock = dir.as_ref().and_then(|dir| {
            fs::create_dir_all(dir).ok()?;
            for entry in fs::read_dir(dir).ok()?.flatten() {
                let path = entry.path();
                let Some(other) = path.file_stem().and_then(|s| s.to_str()).filter(|_| path.extension().is_some_and(|e| e == "lock")) else { continue };
                if !live(dir, other) {
                    let _ = fs::remove_file(&path);
                }
            }
            let file = OpenOptions::new().create(true).truncate(false).write(true).open(dir.join(format!("{id}.lock"))).ok()?;
            file.try_lock().ok()?;
            Some(file)
        });
        Session { id, dir, _lock: lock }
    }

    fn dir(&self) -> Result<&Path, String> {
        self.dir.as_deref().ok_or_else(|| "Octet has no folder to keep drawings in.".into())
    }

    // The drawing of another session that ended (never this one's, never one still open).
    fn other(&self, id: &str) -> Result<&Path, String> {
        let dir = self.dir()?;
        if !valid(id) || session_of(id) == self.id || live(dir, id) {
            return Err("Octet cannot use this drawing now.".into());
        }
        Ok(dir)
    }

    fn write(&self, label: &str, name: &str, contents: &str) -> Result<(), String> {
        if contents.len() as u64 > MAX_BYTES {
            return Err("This drawing is too large to keep.".into());
        }
        let dir = self.dir()?;
        fs::create_dir_all(dir).map_err(|e| e.to_string())?;
        let kept = Meta { name: name.chars().filter(|c| !c.is_control()).take(200).collect(), at: now() };
        let id = copy_id(&self.id, label);
        write_atomic(&dir.join(format!("{id}.oct")), contents.as_bytes()).map_err(|e| e.to_string())?;
        write_atomic(&dir.join(format!("{id}.json")), &serde_json::to_vec(&kept).map_err(|e| e.to_string())?).map_err(|e| e.to_string())
    }

    fn list(&self) -> Vec<Recovered> {
        let Some(dir) = self.dir.as_deref() else { return Vec::new() };
        let Ok(entries) = fs::read_dir(dir) else { return Vec::new() };
        let mut list: Vec<Recovered> = entries
            .flatten()
            .filter_map(|entry| {
                let path = entry.path();
                let id = path.file_stem()?.to_str()?.to_string();
                if path.extension()? != "oct" || self.other(&id).is_err() {
                    return None;
                }
                let Meta { name, at } = meta(dir, &id);
                Some(Recovered { id, name, at })
            })
            .collect();
        list.sort_by(|a, b| b.at.cmp(&a.at));
        list.truncate(MAX_KEPT);
        list
    }

    fn discard(&self, ids: &[String]) -> Result<(), String> {
        let failed = ids.iter().take(MAX_KEPT).filter(|id| self.other(id).and_then(|dir| remove(dir, id)).is_err()).count();
        match failed {
            0 => Ok(()),
            1 => Err("Octet cannot discard 1 drawing. It may be open in another window.".into()),
            n => Err(format!("Octet cannot discard {n} drawings. They may be open in another window.")),
        }
    }

    // Its copy becomes the window's, so it stays safe until the user saves it or chooses Don't Save.
    fn open(&self, label: &str, id: &str) -> Result<(String, String), String> {
        let dir = self.other(id)?;
        let oct = dir.join(format!("{id}.oct"));
        if fs::metadata(&oct).map_err(|_| "This drawing is no longer kept.".to_string())?.len() > MAX_BYTES {
            return Err("This drawing is larger than 64 MB. Octet cannot open it.".into());
        }
        let text = fs::read_to_string(&oct).map_err(|e| e.to_string())?;
        let kept = meta(dir, id);
        let mine = copy_id(&self.id, label);
        fs::rename(&oct, dir.join(format!("{mine}.oct"))).map_err(|e| e.to_string())?;
        let _ = serde_json::to_vec(&kept).map(|b| write_atomic(&dir.join(format!("{mine}.json")), &b));
        let _ = fs::remove_file(dir.join(format!("{id}.json")));
        Ok((kept.name, text))
    }
}

pub fn start(app: &AppHandle) -> Session {
    Session::start_in(app.path().app_data_dir().ok().map(|d| d.join("recovery")))
}

// The page's drawing, kept (64 MB at most; the name cut to 200 characters).
#[tauri::command]
pub async fn recovery_write(window: Window, session: State<'_, Session>, name: String, contents: String) -> Result<(), String> {
    session.write(window.label(), &name, &contents)
}

#[tauri::command]
pub async fn recovery_clear(window: Window, session: State<'_, Session>) -> Result<(), String> {
    remove(session.dir()?, &copy_id(&session.id, window.label()))
}

// Drawings kept by Octet sessions that ended without closing them, newest first (MAX_KEPT at most). A folder Octet cannot
// read is an error, not an empty list, so the page can say so (issue 2).
#[tauri::command]
pub async fn recovery_list(session: State<'_, Session>) -> Result<Vec<Recovered>, String> {
    if let Some(Err(e)) = session.dir.as_deref().map(fs::read_dir) {
        if e.kind() != std::io::ErrorKind::NotFound {
            return Err(e.to_string());
        }
    }
    Ok(session.list())
}

// A kept drawing, to edit again: its name and contents.
#[tauri::command]
pub async fn recovery_open(window: Window, session: State<'_, Session>, id: String) -> Result<(String, String), String> {
    session.open(window.label(), &id)
}

// The user discarded kept drawings on Home. Each one Octet can remove goes; the error says how many stay.
#[tauri::command]
pub async fn recovery_discard(session: State<'_, Session>, ids: Vec<String>) -> Result<(), String> {
    session.discard(&ids)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_are_plain() {
        assert!(valid("18f3a2b9c0d1e2f3a4b5"));
        assert!(!valid("../x") && !valid("") && !valid("a.b") && !valid(&"a".repeat(41)));
    }

    // Two Octets side by side, then one crashes (its lock goes): the other offers its drawing, takes it over, and a
    // third never sees it while the second has it.
    #[test]
    fn a_crashed_drawing_comes_back_once() {
        let dir = std::env::temp_dir().join(format!("octet-recovery-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        let first = Session::start_in(Some(dir.clone()));
        let second = Session::start_in(Some(dir.clone()));
        first.write("draw-1", "Suzuki cycle", "<CDXML/>").unwrap();
        first.write("draw-2", "Heck cycle", "<CDXML/>").unwrap();
        assert!(second.list().is_empty(), "a drawing still open is not offered");
        assert!(first.list().is_empty(), "nor is a session's own");
        let id = copy_id(&first.id, "draw-1");
        assert!(second.open("draw-1", &id).is_err());
        drop(first); // the crash: the system lets its lock go
        let list = second.list();
        assert_eq!(list.len(), 2, "each window's drawing comes back");
        assert!(list.iter().any(|r| r.id == id && r.name == "Suzuki cycle"));
        assert_eq!(second.open("draw-5", &id).unwrap(), ("Suzuki cycle".into(), "<CDXML/>".into()));
        let heck = second.list().iter().find(|r| r.name == "Heck cycle").map(|r| r.id.clone()).unwrap();
        remove(&dir, &heck).unwrap();
        let third = Session::start_in(Some(dir.clone()));
        assert!(third.list().is_empty(), "the second session has it now");
        drop(second);
        assert_eq!(third.list()[0].name, "Suzuki cycle");
        // A copy with no name file still comes back, as Untitled.
        fs::remove_file(dir.join(format!("{}.json", third.list()[0].id))).unwrap();
        assert_eq!(third.list()[0].name, "Untitled");
        remove(&dir, &third.list()[0].id).unwrap();
        assert!(remove(&dir, "gone").is_ok(), "a copy that is not there is removed already");
        assert!(third.list().is_empty());
        assert!(third.open("draw-1", "../etc").is_err());
        // Discard takes a list: the ones it can remove go, and the error counts the rest.
        let fourth = Session::start_in(Some(dir.clone()));
        fourth.write("draw-1", "Open still", "<CDXML/>").unwrap();
        for k in 1..=2 {
            let ended = Session::start_in(Some(dir.clone()));
            ended.write("draw-1", &format!("Ended {k}"), "<CDXML/>").unwrap();
        }
        let mut ids: Vec<String> = third.list().into_iter().map(|r| r.id).collect();
        assert_eq!(ids.len(), 2);
        ids.push(copy_id(&fourth.id, "draw-1"));
        assert_eq!(third.discard(&ids).unwrap_err(), "Octet cannot discard 1 drawing. It may be open in another window.");
        assert!(third.list().is_empty());
        drop(fourth);
        assert_eq!(third.list().len(), 1, "the drawing that was open is still kept");
        let _ = fs::remove_dir_all(&dir);
    }
}
