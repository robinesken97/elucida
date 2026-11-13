// Recent drawings, for Home and File > Open Recent: each drawing opened or saved, newest first (24 at most), kept in
// the app's data folder with a small picture of it. A recent drawing opens again without the file dialog; only files
// the user picked before are on the list, and the page never names any other path.
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, State};

use crate::{write_atomic, Picked, MAX_BYTES};

const MOST: usize = 24;
const IN_MENU: usize = 10; // drawings in File > Open Recent
const MAX_THUMB: usize = 400_000; // characters of SVG for one picture
const MAX_LIST: u64 = 16 * 1024 * 1024; // bytes of the list file read back

#[derive(Serialize, Deserialize, Clone)]
pub struct Recent {
    pub path: String,
    pub name: String,
    pub at: u64, // seconds since 1970
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub thumb: Option<String>,
}

#[derive(Default)]
pub struct Recents(pub Mutex<Option<Vec<Recent>>>);

fn store_path(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_data_dir().ok().map(|d| d.join("recent.json"))
}

// The list, read once from the data folder. A damaged or oversized file gives an empty list.
fn with_list<T>(app: &AppHandle, f: impl FnOnce(&mut Vec<Recent>) -> T) -> T {
    let state = app.state::<Recents>();
    let mut guard = state.0.lock().unwrap();
    let list = guard.get_or_insert_with(|| {
        store_path(app)
            .filter(|p| fs::metadata(p).map(|m| m.len() <= MAX_LIST).unwrap_or(false))
            .and_then(|p| fs::read_to_string(p).ok())
            .and_then(|t| serde_json::from_str::<Vec<Recent>>(&t).ok())
            .map(|l| l.into_iter().filter(|r| r.path.len() < 4096 && r.name.len() < 512 && r.thumb.as_ref().is_none_or(|t| t.len() <= MAX_THUMB)).take(MOST).collect())
            .unwrap_or_default()
    });
    f(list)
}

// Called inside with_list, so each write goes out while the list is locked and an older list never replaces a newer
// one on disk (issue 2).
fn save_list(app: &AppHandle, list: &[Recent]) {
    let Some(path) = store_path(app) else { return };
    if let Some(dir) = path.parent() {
        let _ = fs::create_dir_all(dir);
    }
    if let Ok(text) = serde_json::to_string(list) {
        let _ = write_atomic(&path, text.as_bytes());
    }
}

// The drawings on the list, by path (a project can take any of them: home.rs).
pub fn paths(app: &AppHandle) -> HashSet<String> {
    with_list(app, |list| list.iter().map(|r| r.path.clone()).collect())
}

// The menu's names for the drawings in File > Open Recent: each file's name, in the list's order.
pub fn titles(app: &AppHandle) -> Vec<String> {
    with_list(app, |list| list.iter().take(IN_MENU).map(|r| Path::new(&r.path).file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| r.name.clone())).collect())
}

// File > Open Recent is built again when the drawings in it change (on the main thread, where menus are made).
fn menu_changed(app: &AppHandle, before: &[String]) {
    if titles(app) != before {
        let handle = app.clone();
        let _ = app.run_on_main_thread(move || {
            let _ = crate::rebuild(&handle);
        });
    }
}

// A drawing was opened or saved: it goes to the top of the list, keeping its picture.
pub fn note(app: &AppHandle, path: &Path) {
    let key = path.to_string_lossy().into_owned();
    let name = path.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_else(|| key.clone());
    let at = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let before = titles(app);
    with_list(app, |list| {
        let thumb = list.iter().find(|r| r.path == key).and_then(|r| r.thumb.clone());
        list.retain(|r| r.path != key);
        list.insert(0, Recent { path: key, name, at, thumb });
        list.truncate(MOST);
        save_list(app, list);
    });
    menu_changed(app, &before);
}

// File > Open Recent > Clear Menu: the list is emptied (Home shows the same list).
pub fn clear(app: &AppHandle) {
    let before = titles(app);
    with_list(app, |list| {
        list.clear();
        save_list(app, list);
    });
    menu_changed(app, &before);
}

#[derive(Serialize)]
pub struct RecentView {
    path: String,
    name: String,
    at: u64,
    thumb: Option<String>,
    found: bool, // the file is still where it was
}

// Async, so a stat of a drive that has stopped answering does not hold up the app.
#[tauri::command]
pub async fn recent_list(app: AppHandle) -> Vec<RecentView> {
    with_list(&app, |list| list.clone())
        .into_iter()
        .map(|r| RecentView { found: Path::new(&r.path).is_file(), path: r.path, name: r.name, at: r.at, thumb: r.thumb })
        .collect()
}

// The drawing's picture, from the page, for a drawing already on the list.
#[tauri::command]
pub fn recent_thumb(app: AppHandle, path: String, svg: String) -> Result<(), String> {
    if svg.len() > MAX_THUMB || !svg.trim_start().starts_with("<svg") {
        return Ok(()); // too large, or not a picture: the tile shows the drawing's name only
    }
    with_list(&app, |list| {
        if list.iter_mut().find(|r| r.path == path).map(|r| r.thumb = Some(svg)).is_some() {
            save_list(&app, list);
        }
    });
    Ok(())
}

#[tauri::command]
pub fn recent_remove(app: AppHandle, path: String) {
    let before = titles(&app);
    with_list(&app, |list| {
        list.retain(|r| r.path != path);
        save_list(&app, list);
    });
    menu_changed(&app, &before);
}

// Opens a drawing from the list, from a project or from the Experiments list on Home (only a path on one of them), as
// Open does after its dialog.
#[tauri::command]
pub async fn open_recent(app: AppHandle, picked: State<'_, Picked>, path: String) -> Result<(String, String), String> {
    if !with_list(&app, |list| list.iter().any(|r| r.path == path)) && !crate::home::has(&app, &path) && !with_experiments(&app, |list| list.iter().any(|e| e.path == path)) {
        return Err("Octet cannot open this drawing from Home. Open it with File > Open.".into());
    }
    let p = PathBuf::from(&path);
    let size = fs::metadata(&p).map_err(|_| "This drawing is not where it was. It was moved or deleted.".to_string())?.len();
    if size > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot open it.".into());
    }
    crate::stamp(&app, &p);
    let text = crate::read_text_or_cdx(&p).map_err(|e| e.to_string())?;
    picked.0.lock().unwrap().insert(p.clone());
    note(&app, &p);
    Ok((path, text))
}

// Home's Experiments list (discussion #15): each drawing with experiment details (src/experiment.ts), newest first, as
// it was last opened or saved. It is kept in experiments.json, longer than the recent list and with no picture (Home
// takes the recent list's). The page can only add a drawing on the recent list, and each record is checked when it
// comes from the page and when it is read back, as a file could carry anything.
const MOST_EXPERIMENTS: usize = 1000;
const DETAILS: [&str; 10] = ["title", "number", "date", "notebook", "project", "author", "temperature", "time", "pressure", "solvent"]; // experiment.ts FIELDS
const MAX_VALUE: usize = 200; // characters in a detail (experiment.ts MAX_VALUE)

#[derive(Serialize, Deserialize, Clone, PartialEq, Debug)]
pub struct Experiment {
    details: BTreeMap<String, String>,
    #[serde(default, rename = "yield", skip_serializing_if = "Option::is_none")]
    yld: Option<f64>, // the first product's yield, a fraction
}

impl Experiment {
    // Known details only, each one line of 1 to MAX_VALUE characters, and a yield from 0 to 10000%.
    fn ok(&self) -> bool {
        !self.details.is_empty()
            && self.details.iter().all(|(k, v)| DETAILS.contains(&k.as_str()) && !v.trim().is_empty() && v.chars().count() <= MAX_VALUE && !v.chars().any(|c| c.is_ascii_control()))
            && self.yld.is_none_or(|y| y.is_finite() && (0.0..=100.0).contains(&y))
    }
}

#[derive(Serialize, Deserialize, Clone)]
struct Entry {
    path: String,
    name: String,
    at: u64,
    experiment: Experiment,
}

#[derive(Default)]
pub struct Experiments(Mutex<Option<Vec<Entry>>>);

fn experiments_path(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_data_dir().ok().map(|d| d.join("experiments.json"))
}

// The records that pass the checks, MOST_EXPERIMENTS at most, from the file's text. A damaged file gives none.
fn read_experiments(text: &str) -> Vec<Entry> {
    serde_json::from_str::<Vec<Entry>>(text).map(|l| l.into_iter().filter(|e| e.path.len() < 4096 && e.name.len() < 512 && e.experiment.ok()).take(MOST_EXPERIMENTS).collect()).unwrap_or_default()
}

// As with_list, for the Experiments list. Each change is written while the list is locked.
fn with_experiments<T>(app: &AppHandle, f: impl FnOnce(&mut Vec<Entry>) -> T) -> T {
    let state = app.state::<Experiments>();
    let mut guard = state.0.lock().unwrap();
    let list = guard.get_or_insert_with(|| {
        experiments_path(app)
            .filter(|p| fs::metadata(p).map(|m| m.len() <= MAX_LIST).unwrap_or(false))
            .and_then(|p| fs::read_to_string(p).ok())
            .map(|t| read_experiments(&t))
            .unwrap_or_default()
    });
    f(list)
}

fn save_experiments(app: &AppHandle, list: &[Entry]) {
    let Some(path) = experiments_path(app) else { return };
    if let Some(dir) = path.parent() {
        let _ = fs::create_dir_all(dir);
    }
    if let Ok(text) = serde_json::to_string(list) {
        let _ = write_atomic(&path, text.as_bytes());
    }
}

// The list with a drawing's record put first (experiment) or taken out (None, or details that fail the checks).
fn put_experiment(list: &mut Vec<Entry>, path: &str, name: String, at: u64, experiment: Option<Experiment>) {
    list.retain(|e| e.path != path);
    if let Some(experiment) = experiment.filter(Experiment::ok) {
        list.insert(0, Entry { path: path.to_string(), name, at, experiment });
        list.truncate(MOST_EXPERIMENTS);
    }
}

// A drawing on the recent list was opened or saved: its experiment details and yield, or None when it has none.
#[tauri::command]
pub fn experiment_note(app: AppHandle, path: String, experiment: Option<Experiment>) {
    let Some(name) = with_list(&app, |list| list.iter().find(|r| r.path == path).map(|r| r.name.clone())) else { return };
    let at = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    with_experiments(&app, |list| {
        if experiment.is_none() && !list.iter().any(|e| e.path == path) {
            return; // nothing to take out
        }
        put_experiment(list, &path, name, at, experiment);
        save_experiments(&app, list);
    });
}

#[derive(Serialize)]
pub struct ExperimentView {
    path: String,
    name: String,
    at: u64,
    found: bool,
    details: BTreeMap<String, String>,
    #[serde(rename = "yield", skip_serializing_if = "Option::is_none")]
    yld: Option<f64>,
}

#[tauri::command]
pub async fn experiment_list(app: AppHandle) -> Vec<ExperimentView> {
    with_experiments(&app, |list| list.clone())
        .into_iter()
        .map(|e| ExperimentView { found: Path::new(&e.path).is_file(), path: e.path, name: e.name, at: e.at, details: e.experiment.details, yld: e.experiment.yld })
        .collect()
}

#[tauri::command]
pub fn experiment_remove(app: AppHandle, path: String) {
    with_experiments(&app, |list| {
        list.retain(|e| e.path != path);
        save_experiments(&app, list);
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn experiment(pairs: &[(&str, &str)], yld: Option<f64>) -> Experiment {
        Experiment { details: pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect(), yld }
    }

    #[test]
    fn experiment_details_are_checked() {
        assert!(experiment(&[("title", "Boc protection"), ("date", "2026-11-04")], Some(0.85)).ok());
        assert!(experiment(&[("title", "Wet product")], Some(1.2)).ok(), "a yield over 100% is kept");
        assert!(!experiment(&[], None).ok(), "no details");
        assert!(!experiment(&[("script", "x")], None).ok(), "an unknown detail");
        assert!(!experiment(&[("title", " ")], None).ok(), "an empty value");
        assert!(!experiment(&[("title", "two\nlines")], None).ok(), "a control character");
        assert!(!experiment(&[("title", &"x".repeat(MAX_VALUE + 1))], None).ok(), "too long");
        assert!(experiment(&[("title", &"é".repeat(MAX_VALUE))], None).ok(), "characters, not bytes");
        for bad in [f64::NAN, f64::INFINITY, -0.1, 101.0] {
            assert!(!experiment(&[("title", "x")], Some(bad)).ok(), "{bad}");
        }
    }

    #[test]
    fn a_damaged_or_hostile_file_gives_only_good_records() {
        assert!(read_experiments("{not json").is_empty());
        assert!(read_experiments(r#"{"path":"/a.oct"}"#).is_empty());
        let good = r#"{"path":"/a.oct","name":"a","at":1,"experiment":{"details":{"title":"A"},"yield":0.5}}"#;
        let bad = r#"{"path":"/b.oct","name":"b","at":1,"experiment":{"details":{"onload":"x"}}}"#;
        let list = read_experiments(&format!("[{good},{bad}]"));
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].experiment.yld, Some(0.5));
        let many = format!("[{}]", vec![good; MOST_EXPERIMENTS + 5].join(","));
        assert_eq!(read_experiments(&many).len(), MOST_EXPERIMENTS);
    }

    #[test]
    fn a_record_goes_first_once_and_goes_with_its_details() {
        let mut list = Vec::new();
        let e = |t: &str| Some(experiment(&[("title", t)], None));
        put_experiment(&mut list, "/a.oct", "a".into(), 1, e("A"));
        put_experiment(&mut list, "/b.oct", "b".into(), 2, e("B"));
        put_experiment(&mut list, "/a.oct", "a".into(), 3, e("A2"));
        assert_eq!(list.iter().map(|x| x.path.as_str()).collect::<Vec<_>>(), ["/a.oct", "/b.oct"]);
        assert_eq!(list[0].experiment.details["title"], "A2");
        put_experiment(&mut list, "/b.oct", "b".into(), 4, None);
        assert_eq!(list.len(), 1, "a drawing whose details went leaves the list");
        put_experiment(&mut list, "/a.oct", "a".into(), 5, Some(experiment(&[("x", "y")], None)));
        assert!(list.is_empty(), "details that fail the checks take it out");
        for k in 0..MOST_EXPERIMENTS + 3 {
            put_experiment(&mut list, &format!("/{k}.oct"), "k".into(), k as u64, e("T"));
        }
        assert_eq!(list.len(), MOST_EXPERIMENTS);
    }
}
