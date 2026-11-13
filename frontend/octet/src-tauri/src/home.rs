// Home's projects and thumbnails (decision 0003). A project is a list in Octet that points at drawings, as an album in
// Photos points at photos: the files stay where they are. The page keeps the projects (src/projects.ts); this side
// keeps its file, home.json in the app's data folder, and the thumbnails the user chose, in thumbs/.
// A drawing in a project opens again without the file dialog, as a recent drawing does, so the page can only add a
// drawing Octet may open already: one on the recent list, in a project already, or one the user picked or dropped
// this session. The page never names any other path.
use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Manager, State};
use tauri_plugin_dialog::DialogExt;

use crate::{recent, write_atomic, Picked};

const FILE: &str = "home.json";
const DAMAGED: &str = "home-damaged.json"; // a file Octet could not read, kept beside the new one
const VERSION: u64 = 1; // the newest store this Octet writes (src/projects.ts, STORE_VERSION)
const MAX_STORE: u64 = 8 * 1024 * 1024; // bytes of home.json
const MAX_DRAWINGS: usize = 200_000; // drawings in all projects
const MAX_JPEG: usize = 512 * 1024; // bytes of one thumbnail picture
const MAX_SVG: usize = 400_000; // characters of one thumbnail drawn by Octet (as a recent drawing's)
const MAX_SIDE: u32 = 1024; // pixels: the page makes 512 by 384
const MAX_PICTURE: u64 = 32 * 1024 * 1024; // bytes of a picture file read to make a thumbnail
const PICTURES: [&str; 8] = ["png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "webp"];

// The drawings in projects, as home.json last held them (read once, then kept as it is written).
#[derive(Default)]
pub struct Home(Mutex<Option<HashSet<String>>>);

fn data_dir(app: &AppHandle) -> Option<PathBuf> {
    app.path().app_data_dir().ok()
}

// A store's version and the paths of its drawings (projects[].drawings[].path). None: it is not a store.
fn parse(text: &str) -> Option<(u64, HashSet<String>)> {
    let v: serde_json::Value = serde_json::from_str(text).ok()?;
    let version = v.get("version")?.as_u64()?;
    let mut paths = HashSet::new();
    for p in v.get("projects")?.as_array()? {
        for d in p.get("drawings").and_then(|d| d.as_array()).into_iter().flatten() {
            if let Some(path) = d.get("path").and_then(|p| p.as_str()) {
                paths.insert(path.to_string());
            }
        }
    }
    Some((version, paths))
}

// What home.json holds now: nothing (no file), its text, or Err for a file Octet cannot read (too large, not text).
fn load(app: &AppHandle) -> Result<Option<String>, ()> {
    let Some(path) = data_dir(app).map(|d| d.join(FILE)) else { return Ok(None) };
    match fs::metadata(&path) {
        Err(_) => Ok(None),
        Ok(m) if m.len() > MAX_STORE => Err(()),
        Ok(_) => fs::read_to_string(&path).map(Some).map_err(|_| ()),
    }
}

fn paths_now(app: &AppHandle) -> HashSet<String> {
    let state = app.state::<Home>();
    let mut held = state.0.lock().unwrap();
    held.get_or_insert_with(|| load(app).ok().flatten().and_then(|t| parse(&t)).map(|r| r.1).unwrap_or_default()).clone()
}

// A drawing in a project opens from Home as a recent drawing does (recent.rs, open_recent).
pub fn has(app: &AppHandle, path: &str) -> bool {
    paths_now(app).contains(path)
}

// Only drawings go in projects: Octet's and ChemDraw's files.
fn is_drawing(path: &str) -> bool {
    Path::new(path).extension().and_then(|e| e.to_str()).is_some_and(|e| ["oct", "cdxml", "cdx", "octet"].iter().any(|d| e.eq_ignore_ascii_case(d)))
}

// A project's colour, when it has one: "#" and six hex digits, nothing else (the page draws its folder with it).
fn colours_ok(text: &str) -> bool {
    let ok = |c: &str| c.len() == 7 && c.starts_with('#') && c[1..].bytes().all(|b| b.is_ascii_hexdigit());
    let Ok(v) = serde_json::from_str::<serde_json::Value>(text) else { return false };
    let projects = v.get("projects").and_then(|p| p.as_array()).map(Vec::as_slice).unwrap_or_default();
    projects.iter().all(|p| p.get("colour").is_none_or(|c| c.as_str().is_some_and(ok)))
}

// The project each drawing belongs to: a drawing is in one folder at most. In a store from before that rule, the one
// used last (its "used", else its "made"; the first of them on a tie). Index of the project, by path.
fn owners(projects: &[serde_json::Value]) -> HashMap<String, usize> {
    let last = |p: &serde_json::Value| ["made", "used"].iter().filter_map(|k| p.get(*k).and_then(|v| v.as_f64())).fold(0.0, f64::max);
    let mut owner: HashMap<String, usize> = HashMap::new();
    for (i, p) in projects.iter().enumerate() {
        for d in p.get("drawings").and_then(|d| d.as_array()).into_iter().flatten() {
            let Some(path) = d.get("path").and_then(|p| p.as_str()) else { continue };
            if owner.get(path).is_none_or(|&j| last(p) > last(&projects[j])) {
                owner.insert(path.to_string(), i);
            }
        }
    }
    owner
}

// A store with each drawing in one folder only (see owners), or None when it is so already or is not a store.
fn one_folder(text: &str) -> Option<String> {
    let mut v: serde_json::Value = serde_json::from_str(text).ok()?;
    let projects = v.get_mut("projects")?.as_array_mut()?;
    let owner = owners(projects);
    let mut changed = false;
    for (i, p) in projects.iter_mut().enumerate() {
        let Some(list) = p.get_mut("drawings").and_then(|d| d.as_array_mut()) else { continue };
        let before = list.len();
        list.retain(|d| d.get("path").and_then(|p| p.as_str()).is_none_or(|path| owner.get(path) == Some(&i)));
        changed |= list.len() != before;
    }
    changed.then(|| v.to_string())
}

#[derive(Serialize)]
pub struct HomeRead {
    text: Option<String>, // home.json, or None when there is none yet
    damaged: bool,        // there is a home.json, but Octet cannot read it
    missing: Vec<String>, // drawings in projects that are not where they were
    home: Option<String>, // the user's home folder, which Home shows as ~ in a drawing's place
}

#[tauri::command]
pub fn home_read(app: AppHandle) -> HomeRead {
    let (text, damaged) = match load(&app) {
        Ok(t) => (t.map(|t| one_folder(&t).unwrap_or(t)), false),
        Err(()) => (None, true),
    };
    let parsed = text.as_deref().and_then(parse);
    let paths = parsed.as_ref().map(|p| p.1.clone()).unwrap_or_default();
    let missing = paths.iter().filter(|p| !Path::new(p.as_str()).is_file()).cloned().collect();
    *app.state::<Home>().0.lock().unwrap() = Some(paths);
    let home = app.path().home_dir().ok().map(|h| h.to_string_lossy().into_owned());
    HomeRead { damaged: damaged || (text.is_some() && parsed.is_none()), text, missing, home }
}

// Why a store cannot be written over the one there now (`before`), or None. allowed: drawings Octet may open already.
fn refuse(text: &str, before: Option<&(u64, HashSet<String>)>, allowed: impl Fn(&str) -> bool) -> Option<String> {
    let Some((version, paths)) = parse(text) else { return Some("Octet cannot save your folders.".into()) };
    if before.is_some_and(|b| b.0 > version) || version > VERSION {
        return Some("A newer Octet saved your folders. Update Octet to change them.".into());
    }
    if paths.len() > MAX_DRAWINGS || paths.iter().any(|p| p.len() >= 4096 || !is_drawing(p)) || !colours_ok(text) || one_folder(text).is_some() {
        return Some("Octet cannot save your folders.".into());
    }
    paths.iter().filter(|p| !before.is_some_and(|b| b.1.contains(*p))).find(|p| !allowed(p)).map(|_| "Octet can only add a drawing that you opened, saved or dropped on Octet.".into())
}

// The page's projects, saved over home.json (atomically). A home.json Octet could not read is kept as
// home-damaged.json first, so nothing the user made is lost without a copy.
#[tauri::command]
pub fn home_write(app: AppHandle, picked: State<'_, Picked>, text: String) -> Result<(), String> {
    if text.len() as u64 > MAX_STORE {
        return Err("You have too many folders for Octet to save. Remove some drawings from them.".into());
    }
    let dir = data_dir(&app).ok_or("Octet cannot save your folders.")?;
    let now = load(&app);
    let before = now.as_ref().ok().and_then(|t| t.as_deref().map(parse));
    if now.is_err() || before.as_ref().is_some_and(|b| b.is_none()) {
        let _ = fs::rename(dir.join(FILE), dir.join(DAMAGED));
    }
    let before = before.flatten();
    let recents = recent::paths(&app);
    let allowed = |p: &str| recents.contains(p) || picked.0.lock().unwrap().contains(Path::new(p));
    if let Some(why) = refuse(&text, before.as_ref(), allowed) {
        return Err(why);
    }
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    write_atomic(&dir.join(FILE), text.as_bytes()).map_err(|e| e.to_string())?;
    *app.state::<Home>().0.lock().unwrap() = parse(&text).map(|p| p.1);
    Ok(())
}

// Drawings to add to a project (Add Drawings…), or a drawing's new place (Locate…): the Open dialog for drawings. Each
// file picked may then go in a project.
#[tauri::command]
pub async fn home_pick_drawings(app: AppHandle, picked: State<'_, Picked>, many: bool) -> Result<Vec<String>, String> {
    let dialog = app.dialog().file().add_filter(crate::OPEN.0, crate::OPEN.1);
    let files = if many { dialog.blocking_pick_files().unwrap_or_default() } else { dialog.blocking_pick_file().into_iter().collect() };
    let paths: Vec<PathBuf> = files.into_iter().filter_map(|f| f.into_path().ok()).filter(|p| is_drawing(&p.to_string_lossy())).collect();
    let mut held = picked.0.lock().unwrap();
    Ok(paths.into_iter().map(|p| {
        held.insert(p.clone());
        p.to_string_lossy().into_owned()
    }).collect())
}

// A picture for a thumbnail (Set Thumbnail…): its bytes in base64, read once and not remembered. The page decodes it
// in the webview and keeps only a small copy (src/thumbs.ts).
#[tauri::command]
pub async fn home_pick_picture(app: AppHandle) -> Result<Option<String>, String> {
    use base64::Engine;
    let Some(file) = app.dialog().file().add_filter("Pictures", &PICTURES).blocking_pick_file() else { return Ok(None) };
    let path = file.into_path().map_err(|e| e.to_string())?;
    if fs::metadata(&path).map_err(|e| e.to_string())?.len() > MAX_PICTURE {
        return Err("This picture is larger than 32 MB. Choose a smaller picture.".into());
    }
    fs::read(&path).map(|b| Some(base64::engine::general_purpose::STANDARD.encode(b))).map_err(|e| e.to_string())
}

fn thumbs_dir(app: &AppHandle) -> Option<PathBuf> {
    data_dir(app).map(|d| d.join("thumbs"))
}

// A thumbnail's name: 16 hex digits, from the time and a count, so two are never the same.
fn new_id() -> String {
    static COUNT: AtomicU64 = AtomicU64::new(0);
    let nanos = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0) as u64;
    format!("{:012x}{:04x}", nanos & 0xffff_ffff_ffff, COUNT.fetch_add(1, Ordering::Relaxed) & 0xffff)
}

fn id_ok(id: &str) -> bool {
    id.len() == 16 && id.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

// A thumbnail picture the page made: a JPEG no larger than Home needs. The Rust image decoder reads it all, within
// limits, so a file that is not one never goes in the data folder.
fn check_jpeg(bytes: &[u8]) -> Result<(), String> {
    let refused = || "Octet cannot use this picture as a thumbnail.".to_string();
    if bytes.len() > MAX_JPEG {
        return Err(refused());
    }
    let mut reader = image::ImageReader::with_format(Cursor::new(bytes), image::ImageFormat::Jpeg);
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(MAX_SIDE);
    limits.max_image_height = Some(MAX_SIDE);
    limits.max_alloc = Some(16 * 1024 * 1024);
    reader.limits(limits);
    reader.decode().map(|_| ()).map_err(|_| refused())
}

fn check_svg(svg: &str) -> Result<(), String> {
    if svg.len() > MAX_SVG || !svg.trim_start().starts_with("<svg") {
        return Err("Octet cannot use this picture as a thumbnail.".into());
    }
    Ok(())
}

// Keeps a thumbnail (a JPEG in base64, or an SVG Octet drew) in thumbs/ and gives its name.
#[tauri::command]
pub fn thumb_save(app: AppHandle, jpeg: Option<String>, svg: Option<String>) -> Result<String, String> {
    use base64::Engine;
    let (bytes, ext) = match (jpeg, svg) {
        (Some(b64), None) => {
            let bytes = base64::engine::general_purpose::STANDARD.decode(b64.as_bytes()).map_err(|_| "Octet cannot use this picture as a thumbnail.".to_string())?;
            check_jpeg(&bytes)?;
            (bytes, "jpg")
        }
        (None, Some(svg)) => {
            check_svg(&svg)?;
            (svg.into_bytes(), "svg")
        }
        _ => return Err("Octet cannot use this picture as a thumbnail.".into()),
    };
    let dir = thumbs_dir(&app).ok_or("Octet cannot keep this thumbnail.")?;
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let id = new_id();
    write_atomic(&dir.join(format!("{id}.{ext}")), &bytes).map_err(|e| e.to_string())?;
    Ok(id)
}

// Thumbnails by name, each as a data address an image can show (the page's content rules allow data: only).
#[tauri::command]
pub fn thumb_load(app: AppHandle, ids: Vec<String>) -> HashMap<String, String> {
    use base64::Engine;
    let Some(dir) = thumbs_dir(&app) else { return HashMap::new() };
    ids.into_iter().filter(|id| id_ok(id)).take(2000).filter_map(|id| {
        let read = |ext: &str, max: usize| fs::read(dir.join(format!("{id}.{ext}"))).ok().filter(|b| b.len() <= max);
        let url = if let Some(b) = read("jpg", MAX_JPEG) {
            format!("data:image/jpeg;base64,{}", base64::engine::general_purpose::STANDARD.encode(b))
        } else {
            format!("data:image/svg+xml;base64,{}", base64::engine::general_purpose::STANDARD.encode(read("svg", MAX_SVG)?))
        };
        Some((id, url))
    }).collect()
}

// A thumbnail no longer used: its file goes.
#[tauri::command]
pub fn thumb_drop(app: AppHandle, id: String) {
    if let (true, Some(dir)) = (id_ok(&id), thumbs_dir(&app)) {
        let _ = fs::remove_file(dir.join(format!("{id}.jpg")));
        let _ = fs::remove_file(dir.join(format!("{id}.svg")));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const STORE: &str = r#"{"version":1,"projects":[{"id":"a","name":"Thesis","made":1,"drawings":[{"path":"/d/a.oct","name":"a","added":1},{"path":"/d/b.cdxml","name":"b","added":1}]}],"pictures":{}}"#;

    #[test]
    fn a_store_names_its_drawings() {
        let (version, paths) = parse(STORE).unwrap();
        assert_eq!(version, 1);
        assert_eq!(paths, HashSet::from(["/d/a.oct".to_string(), "/d/b.cdxml".to_string()]));
        assert!(parse("{not json").is_none());
        assert!(parse(r#"{"projects":[]}"#).is_none(), "no version");
        assert!(parse(r#"{"version":1}"#).is_none(), "no projects");
    }

    #[test]
    fn only_drawings_octet_may_open_go_in() {
        let none = |_: &str| false;
        // A new store: each drawing must be one Octet may open already.
        assert!(refuse(STORE, None, |p| p.starts_with("/d/")).is_none());
        assert!(refuse(STORE, None, none).unwrap().contains("opened, saved or dropped"));
        // Drawings in the store already stay, and any can be removed.
        let before = parse(STORE).unwrap();
        assert!(refuse(STORE, Some(&before), none).is_none());
        assert!(refuse(r#"{"version":1,"projects":[],"pictures":{}}"#, Some(&before), none).is_none());
        // Only drawings: not a script, a picture or a folder.
        let script = STORE.replace("/d/b.cdxml", "/d/run.sh");
        assert!(refuse(&script, None, |_| true).is_some());
        assert!(refuse("{not json", None, |_| true).is_some());
    }

    #[test]
    fn a_project_colour_is_a_hex_colour_only() {
        let with = |c: &str| STORE.replace("\"made\":1,", &format!("\"made\":1,\"colour\":{c},"));
        assert!(refuse(STORE, None, |_| true).is_none(), "no colour: Octet Blue");
        for good in ["\"#213C99\"", "\"#3f6bff\"", "\"#000000\""] {
            assert!(colours_ok(&with(good)), "{good}");
            assert!(refuse(&with(good), None, |_| true).is_none(), "{good}");
        }
        for bad in ["\"red\"", "\"#FFF\"", "\"#21 C99\"", "\"#213C99;background:url(x)\"", "\"#GGGGGG\"", "\"213C990\"", "42", "null", "[\"#213C99\"]"] {
            assert!(!colours_ok(&with(bad)), "{bad}");
            assert!(refuse(&with(bad), None, |_| true).is_some(), "{bad} is refused");
        }
        // Each project is checked, not only the first.
        let two = r##"{"version":1,"projects":[{"id":"a","name":"A","colour":"#213C99","drawings":[]},{"id":"b","name":"B","colour":"url(x)","drawings":[]}],"pictures":{}}"##;
        assert!(!colours_ok(two));
    }

    #[test]
    fn a_drawing_is_in_one_folder() {
        // From before one folder at a time: a.oct in all three. It stays in the one used last (b, used 90).
        let old = r##"{"version":1,"projects":[
            {"id":"a","name":"A","made":5,"used":20,"drawings":[{"path":"/d/a.oct"},{"path":"/d/x.oct"}]},
            {"id":"b","name":"B","made":1,"used":90,"drawings":[{"path":"/d/a.oct"}]},
            {"id":"c","name":"C","made":30,"drawings":[{"path":"/d/a.oct"},{"path":"/d/y.oct"}]}],"pictures":{}}"##;
        let fixed: serde_json::Value = serde_json::from_str(&one_folder(old).unwrap()).unwrap();
        let paths = |i: usize| fixed["projects"][i]["drawings"].as_array().unwrap().iter().map(|d| d["path"].as_str().unwrap().to_string()).collect::<Vec<_>>();
        assert_eq!(paths(0), ["/d/x.oct"]);
        assert_eq!(paths(1), ["/d/a.oct"]);
        assert_eq!(paths(2), ["/d/y.oct"], "the other drawings stay where they are");
        assert_eq!(fixed["projects"][0]["name"], "A", "nothing else changes");
        // On a tie, the first project keeps it. A store that is right already is left as it is.
        let tie = r#"{"version":1,"projects":[{"id":"a","name":"A","made":1,"drawings":[{"path":"/d/a.oct"}]},{"id":"b","name":"B","made":1,"drawings":[{"path":"/d/a.oct"}]}]}"#;
        let tie: serde_json::Value = serde_json::from_str(&one_folder(tie).unwrap()).unwrap();
        assert_eq!(tie["projects"][0]["drawings"].as_array().unwrap().len(), 1);
        assert_eq!(tie["projects"][1]["drawings"].as_array().unwrap().len(), 0);
        assert!(one_folder(STORE).is_none());
        assert!(one_folder("{not json").is_none());
        // The page may not write a drawing into two folders.
        assert!(refuse(old, None, |_| true).is_some());
        assert!(refuse(STORE, None, |_| true).is_none());
    }

    #[test]
    fn a_newer_store_is_not_written_over() {
        let newer = STORE.replace("\"version\":1", "\"version\":2");
        assert!(refuse(&newer, None, |_| true).unwrap().contains("newer Octet"));
        let before = parse(&newer).unwrap();
        assert!(refuse(STORE, Some(&before), |_| true).unwrap().contains("newer Octet"));
    }

    #[test]
    fn thumbnails_are_checked() {
        assert!(id_ok(&new_id()));
        assert_ne!(new_id(), new_id());
        assert!(!id_ok("../../etc/passwd"));
        assert!(!id_ok("0123456789ABCDEF"));
        assert!(check_svg("<svg xmlns='http://www.w3.org/2000/svg'/>").is_ok());
        assert!(check_svg("<html><script>").is_err());
        assert!(check_svg(&format!("<svg>{}</svg>", "x".repeat(MAX_SVG))).is_err());
        assert!(check_jpeg(b"\xff\xd8\xff\xe0 not a real jpeg").is_err());
        // A real JPEG within the limits passes; one wider than Home ever needs does not.
        let jpeg = |w: u32, h: u32| {
            let mut out = Vec::new();
            image::codecs::jpeg::JpegEncoder::new(&mut out).encode(&vec![200u8; (w * h * 3) as usize], w, h, image::ExtendedColorType::Rgb8).unwrap();
            out
        };
        assert!(check_jpeg(&jpeg(512, 384)).is_ok());
        assert!(check_jpeg(&jpeg(2000, 10)).is_err());
    }
}
