// Prevents an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use tauri::menu::{CheckMenuItem, IsMenuItem, Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, DragDropEvent, Emitter, Manager, State, WindowEvent, Wry};
use tauri_plugin_dialog::DialogExt;

// Alt and a menu's access key on Windows, from the web view to the menu bar.
#[cfg(windows)]
mod access_keys;
mod clipboard;
mod crashlog;
mod export;
mod eyedropper;
// Feedback, for testers: not in the public release (build.rs, REL-8).
#[cfg(feedback)]
mod feedback;
mod home;
// Octet from an AppImage, and the programs Octet starts on Linux (linux.rs).
#[cfg(target_os = "linux")]
mod linux;
// Octet Drawing objects in Office for Windows (decision 0023). The COM server builds on Windows only (ole_windows.rs).
mod ole;
// Object windows on every system: Windows' OLE objects and objects in files (decision 0023).
mod objects;
// Edit Picture from Word on the Mac: Apple Events to Word, and the Service "Edit in Octet Draw" (word.rs).
#[cfg(target_os = "macos")]
mod word;
mod open;
mod pubchem;
mod quit;
mod recent;
mod recovery;
mod search;
#[cfg(feature = "smoke")]
mod smoke;
mod spectrum;
mod update;
mod vector;
mod windows;

// Opens a web address or a file in the user's own program for it (the browser, the mail app). On Windows the open
// crate asks the shell (ShellExecuteExW) directly: cmd.exe would read each & in an address as a new command. ::open is
// the crate, not src/open.rs. On Linux each opener in turn (xdg-open, then gio and others), with the session's
// environment when Octet runs from an AppImage (linux::spawn).
#[cfg(not(target_os = "linux"))]
pub fn open_external(target: impl AsRef<std::ffi::OsStr>) -> std::io::Result<()> {
    ::open::that_detached(target)
}

#[cfg(target_os = "linux")]
pub fn open_external(target: impl AsRef<std::ffi::OsStr>) -> std::io::Result<()> {
    let mut result = Err(std::io::ErrorKind::NotFound.into());
    for mut opener in ::open::commands(target) {
        result = linux::spawn(&mut opener);
        if result.is_ok() {
            break;
        }
    }
    result
}

// The computer user's full name (the Mac's, or the GECOS field of /etc/passwd on Linux), else the login name: a new
// drawing's author (Settings > Document > Properties). Windows gives the login name.
#[tauri::command]
fn user_name() -> String {
    let login = std::env::var("USER").or_else(|_| std::env::var("USERNAME")).unwrap_or_default();
    #[cfg(target_os = "macos")]
    let full = objc2_foundation::NSFullUserName().to_string();
    #[cfg(target_os = "linux")]
    let full = std::fs::read_to_string("/etc/passwd").unwrap_or_default().lines().find_map(|l| Some(l.strip_prefix(&format!("{login}:"))?.split(':').nth(3)?.split(',').next()?.to_string())).unwrap_or_default();
    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    let full = String::new();
    let name = if full.trim().is_empty() { login } else { full };
    name.chars().filter(|c| !c.is_control()).take(200).collect::<String>().trim().to_string()
}

// File > Print: the system's print dialog for the window, which prints only the page the editor laid out for it.
#[tauri::command]
fn print_page(window: tauri::WebviewWindow) -> Result<(), String> {
    window.print().map_err(|e| e.to_string())
}

// Files the user picked in an Open or Save dialog this session. The webview can only save to these,
// so a compromised page can't write anywhere else.
#[derive(Default)]
pub struct Picked(pub Mutex<HashSet<PathBuf>>);

// Each drawing file's size and time when Octet last read or wrote it. Save and the window coming to the front compare
// them with the file on disk, so a change another app made is never written over without a question (issue 2).
#[derive(Default)]
pub struct Stamps(Mutex<HashMap<PathBuf, Stamp>>);
type Stamp = (u64, Option<std::time::SystemTime>);
fn stamp_of(path: &Path) -> Option<Stamp> {
    fs::metadata(path).ok().map(|m| (m.len(), m.modified().ok()))
}
// Called before Octet reads a drawing and after it writes one.
pub fn stamp(app: &AppHandle, path: &Path) {
    note_stamp(&app.state::<Stamps>(), path);
}
fn note_stamp(stamps: &Stamps, path: &Path) {
    let mut held = stamps.0.lock().unwrap();
    match stamp_of(path) {
        Some(s) => held.insert(path.to_path_buf(), s),
        None => held.remove(path),
    };
}
// True when the file is there and is not as Octet last read or wrote it. A file that is gone is not changed: Save
// writes it again.
fn changed(stamps: &Stamps, path: &Path) -> bool {
    let held = stamps.0.lock().unwrap().get(path).copied();
    held.is_some_and(|s| stamp_of(path).is_some_and(|now| now != s))
}
#[tauri::command]
fn file_changed(stamps: State<'_, Stamps>, path: String) -> bool {
    changed(&stamps, Path::new(&path))
}

// Tickable menu items, so the page can set their ticks from the user's saved settings.
struct Checks(Mutex<Vec<CheckMenuItem<Wry>>>);

// Shortcuts for menu commands. MenuKeys: the user's own (Settings > Keyboard shortcuts), an accelerator for each
// command they changed, "" for none. MenuList: every command as the menu was last built (its id, its name, the menu
// it is in and its default shortcut), for Settings to list. Palette: the user's colour names, for building again.
#[derive(Default)]
struct MenuKeys(Mutex<HashMap<String, String>>);
#[derive(Default)]
struct MenuList(Mutex<Vec<(String, String, String, String)>>);
#[derive(Default)]
struct Palette(Mutex<Vec<String>>);
// The Text menu's fonts and sizes: the same lists as the Actions panel's, sent by the page.
#[derive(Default)]
struct TextLists(Mutex<(Vec<String>, Vec<f64>)>);
type Built = (Menu<Wry>, Vec<CheckMenuItem<Wry>>, Vec<(String, String, String, String)>);

// The menu bar goes on the app. On the Mac, Help becomes the system's Help menu, which only works once it is on the app.
pub fn set_bar(app: &AppHandle, bar: Menu<Wry>) -> tauri::Result<()> {
    app.set_menu(bar.clone())?;
    #[cfg(target_os = "macos")]
    if let Some(help) = bar.get("help").and_then(|h| h.as_submenu().cloned()) {
        help.set_as_help_menu_for_nsapp()?;
    }
    // The system lists the open windows in the Window menu.
    #[cfg(target_os = "macos")]
    if let Some(window) = bar.get("window").and_then(|w| w.as_submenu().cloned()) {
        window.set_as_windows_menu_for_nsapp()?;
    }
    Ok(())
}

// The menu bar built again with the user's colours and shortcuts, and the recent drawings. A shortcut the menu cannot
// take leaves every command on its default, so the menu is never lost. The ticks stay as they were.
fn rebuild(app: &AppHandle) -> Result<(), String> {
    let names = app.state::<Palette>().0.lock().unwrap().clone();
    let keys = app.state::<MenuKeys>().0.lock().unwrap().clone();
    let online = *app.state::<search::Online>().0.lock().unwrap();
    let text = app.state::<TextLists>().0.lock().unwrap().clone();
    let (bar, mut checks, list) = menu(app, &names, &text, &keys, online, None).or_else(|_| menu(app, &names, &text, &HashMap::new(), online, None)).map_err(|e| e.to_string())?;
    // An object window (decision 0023) has a menu bar of its own, with its own File menu: it is built again too.
    let mut objects = Vec::new();
    for (label, host) in windows::object_hosts(app) {
        if let Ok((m, c, _)) = menu(app, &names, &text, &keys, online, Some(&host)).or_else(|_| menu(app, &names, &text, &HashMap::new(), online, Some(&host))) {
            checks.extend(c);
            objects.push((label, m));
        }
    }
    keep_ticks(app, &checks);
    windows::set_menu(app, None, bar).map_err(|e| e.to_string())?;
    for (label, m) in objects {
        let _ = windows::set_menu(app, Some(&label), m);
    }
    *app.state::<Checks>().0.lock().unwrap() = checks;
    *app.state::<MenuList>().0.lock().unwrap() = list;
    Ok(())
}

// New tick items take the ticks the old ones had.
fn keep_ticks(app: &AppHandle, checks: &[CheckMenuItem<Wry>]) {
    if let Some(old) = app.try_state::<Checks>() {
        let old = old.0.lock().unwrap();
        for (c, was, on) in checks.iter().filter_map(|c| old.iter().find(|o| o.id() == c.id()).map(|o| (c, o.is_checked(), o.is_enabled()))) {
            let _ = c.set_checked(was.unwrap_or(true));
            let _ = c.set_enabled(on.unwrap_or(true));
        }
    }
}

// The menu bar of an object window (decision 0023): the same menus, with File's Save, Save As and Close for the
// object in the document `host`. Its ticks join the others, so the page sets them as it sets the rest.
pub fn object_menu(app: &AppHandle, host: &str) -> tauri::Result<Menu<Wry>> {
    let names = app.state::<Palette>().0.lock().unwrap().clone();
    let keys = app.state::<MenuKeys>().0.lock().unwrap().clone();
    let online = *app.state::<search::Online>().0.lock().unwrap();
    let text = app.state::<TextLists>().0.lock().unwrap().clone();
    let (bar, checks, _) = menu(app, &names, &text, &keys, online, Some(host)).or_else(|_| menu(app, &names, &text, &HashMap::new(), online, Some(host)))?;
    keep_ticks(app, &checks);
    if let Some(all) = app.try_state::<Checks>() {
        all.0.lock().unwrap().extend(checks);
    }
    Ok(bar)
}

#[tauri::command]
fn menu_items(list: State<'_, MenuList>) -> Vec<(String, String, String, String)> {
    list.0.lock().unwrap().clone()
}

// Each window sends its lists when they change and when it comes to the front (the drawings' own colours and fonts
// differ): the menu bar is built again only when a list is new. True when `next` was new and is kept.
fn keep_new<T: PartialEq>(held: &Mutex<T>, next: T) -> bool {
    let mut held = held.lock().unwrap();
    if *held == next {
        return false;
    }
    *held = next;
    true
}

// The user's menu shortcuts (at most 500, ids and accelerators of bounded length); the menu bar is built again
// with them. The frontend sets its check marks again afterwards.
#[tauri::command]
fn set_menu_keys(app: AppHandle, keys: HashMap<String, String>) -> Result<(), String> {
    let keys: HashMap<String, String> = keys.into_iter().filter(|(id, k)| id.len() <= 60 && k.len() <= 40 && !k.chars().any(char::is_control)).take(500).collect();
    if !keep_new(&app.state::<MenuKeys>().0, keys) {
        return Ok(());
    }
    rebuild(&app)
}

// Settings > Online search: the Search menu is there only while it is on.
#[tauri::command]
fn set_online_search(app: AppHandle, on: bool) -> Result<(), String> {
    if !keep_new(&app.state::<search::Online>().0, on) {
        return Ok(());
    }
    rebuild(&app)
}

// A tick, and (enabled) whether the item can be chosen: Curves > Solid, Hollow and Angled Arrowhead follow the selection.
#[tauri::command]
fn set_check(checks: State<'_, Checks>, id: String, checked: bool, enabled: Option<bool>) -> Result<(), String> {
    let checks = checks.0.lock().unwrap();
    let items: Vec<_> = checks.iter().filter(|c| c.id().0 == id).collect();
    if items.is_empty() {
        return Err("no such menu item".into());
    }
    // An object window's items can outlive its window until the menus are built again: those fail, and do not count.
    let mut answer = Err(String::new());
    for c in items {
        match c.set_checked(checked).and_then(|_| enabled.map_or(Ok(()), |on| c.set_enabled(on))) {
            Ok(()) => answer = Ok(()),
            Err(e) if answer.is_err() => answer = Err(e.to_string()),
            Err(_) => {}
        }
    }
    answer
}

// The user's own colours (100 at most, OWN_MOST in src/colours.ts), then the drawing's own (24 at most), by name, in
// the Colour menu: the menu bar is built again with them (names cut to 40 characters). The frontend sets its check
// marks again afterwards.
#[tauri::command]
fn set_palette(app: AppHandle, names: Vec<String>) -> Result<(), String> {
    let names: Vec<String> = names.into_iter().take(124).map(|n| n.chars().filter(|c| !c.is_control()).take(40).collect()).collect();
    if !keep_new(&app.state::<Palette>().0, names) {
        return Ok(());
    }
    rebuild(&app)
}

// The Text menu's fonts (Octet's and the drawing's, 60 at most, names cut to 64 characters) and sizes (40 at most,
// 0.1 to 999 pt), as the Actions panel lists them: ChemDraw's sizes times the document scale (decision 0007). The menu
// bar is built again with them.
#[tauri::command]
fn set_text_lists(app: AppHandle, fonts: Vec<String>, sizes: Vec<f64>) -> Result<(), String> {
    let fonts: Vec<String> = fonts.into_iter().take(60).map(|n| n.chars().filter(|c| !c.is_control()).take(64).collect()).collect();
    let sizes: Vec<f64> = sizes.into_iter().filter(|s| s.is_finite() && (0.1..=999.0).contains(s)).take(40).collect();
    if !keep_new(&app.state::<TextLists>().0, (fonts, sizes)) {
        return Ok(());
    }
    rebuild(&app)
}

// What new drawings are for (IDEA-SIZE-1): the user's own purposes by name (12 at most, names cut to 40 characters)
// after Paper, Thesis, Slides, Poster and Experiment in File > New For, and the name of the one File > New starts,
// which New shows as ChemDraw's New shows its stationery. The menu bar is built again with them.
#[derive(Default)]
struct Purposes(Mutex<(Vec<String>, String)>);

#[tauri::command]
fn set_purposes(app: AppHandle, held: State<'_, Purposes>, names: Vec<String>, current: String) -> Result<(), String> {
    let clean = |n: String| n.chars().filter(|c| !c.is_control()).take(40).collect::<String>();
    let next = (names.into_iter().take(12).map(clean).collect::<Vec<_>>(), clean(current));
    {
        let mut held = held.0.lock().unwrap();
        if *held == next {
            return Ok(());
        }
        *held = next;
    }
    rebuild(&app)
}

// View > Templates (ChemDraw's View > Templates): the template sets a floating palette opens for, the user's own
// (My templates first), then Octet's structures and Octet's clip art, as the library has them apart, each as an item
// "templates_<k>" in that order. The page sends the three lists (at most 80 sets each, names cut to 40 characters) and
// opens the palette for the item chosen.
#[derive(Default)]
struct TemplateSets(Mutex<[Vec<String>; 3]>);

#[tauri::command]
fn set_template_sets(app: AppHandle, held: State<'_, TemplateSets>, own: Vec<String>, octet: Vec<String>, art: Vec<String>) -> Result<(), String> {
    let clean = |list: Vec<String>| list.into_iter().take(80).map(|n| n.chars().filter(|c| !c.is_control()).take(40).collect::<String>()).collect::<Vec<_>>();
    let next = [clean(own), clean(octet), clean(art)];
    {
        let mut held = held.0.lock().unwrap();
        if *held == next {
            return Ok(());
        }
        *held = next;
    }
    rebuild(&app)
}

// A menu's items for the template sets, group by group (the user's, Octet's structures, Octet's clip art), with a
// separator between two groups that have sets.
fn in_groups<'a, M: IsMenuItem<Wry>>(items: &'a [M], groups: &[Vec<String>; 3], seps: &'a [PredefinedMenuItem<Wry>; 2]) -> Vec<&'a dyn IsMenuItem<Wry>> {
    let mut list: Vec<&'a dyn IsMenuItem<Wry>> = Vec::new();
    let mut at = 0;
    for (k, n) in groups.iter().map(Vec::len).filter(|&n| n > 0).enumerate() {
        if k > 0 {
            list.push(&seps[k - 1]);
        }
        list.extend(items[at..at + n].iter().map(|m| m as &dyn IsMenuItem<Wry>));
        at += n;
    }
    list
}

// File > More Formats (Settings > Pro > More formats): the rare formats the page lists (40 at most), each an id ("more_"
// and the format) and its name (cut to 60 characters). None while the switch is off: File has no More Formats.
#[derive(Default)]
struct MoreFormats(Mutex<Option<Vec<(String, String)>>>);

#[tauri::command]
fn set_more_formats(app: AppHandle, formats: Option<Vec<(String, String)>>) -> Result<(), String> {
    let next = formats.map(|list| list.into_iter()
        .filter(|(id, _)| id.len() <= 60 && id.starts_with("more_") && id.chars().all(|c| c.is_ascii_alphanumeric() || c == '_'))
        .take(40).map(|(id, name)| (id, name.chars().filter(|c| !c.is_control()).take(60).collect())).collect());
    if !keep_new(&app.state::<MoreFormats>().0, next) {
        return Ok(());
    }
    rebuild(&app)
}

pub const MAX_BYTES: u64 = 64 * 1024 * 1024;
// Octet saves .oct, a CDXML file with Octet's drawing inside (decision 0004), or .cdxml, which is the same file, or
// .cdx, ChemDraw's binary file with Octet's drawing inside (decision 0009). It opens all three, and the older .octet
// files.
const OPEN: (&str, &[&str]) = ("Drawings", &["oct", "cdxml", "cdx", "octet"]);
// File > Open also opens measured spectra (JCAMP-DX and SPC), which go into the drawing that is open (src/jcamp.ts),
// and ChemDraw template files (.ctp, and .cts stationery), whose panes become a set of templates (src/ctp.ts).
const OPEN_ALL: (&str, &[&str]) = ("Drawings, spectra and templates", &["oct", "cdxml", "cdx", "octet", "jdx", "dx", "jcamp", "spc", "ctp", "cts"]);
// File > Apply Settings From File… also takes a ChemDraw style sheet (.cds: a CDX file with the settings and no
// drawing), as Settings > Document > Save to file… writes one.
const STYLES: (&str, &[&str]) = ("Drawings and style sheets", &["oct", "cdxml", "cdx", "cds", "octet"]);
// A ChemDraw template file: read, but never a drawing Octet saves over or lists on Home.
pub fn is_template_file(path: &Path) -> bool {
    path.extension().and_then(|e| e.to_str()).is_some_and(|e| e.eq_ignore_ascii_case("ctp") || e.eq_ignore_ascii_case("cts"))
}
const SAVE: [(&str, &[&str]); 3] = [("Octet drawing", &["oct"]), ("ChemDraw drawing (CDXML)", &["cdxml"]), ("ChemDraw drawing (CDX)", &["cdx"])];
const SAVES: [&str; 3] = ["oct", "cdxml", "cdx"];

// A file's contents for the page: its text, or a CDX file's bytes in base64 (which starts "VmpDRDAxMDA", the
// magic). Anything else that is not UTF-8 text is an InvalidData error.
pub fn read_text_or_cdx(path: &Path) -> std::io::Result<String> {
    use base64::Engine;
    let bytes = fs::read(path)?;
    if bytes.starts_with(b"VjCD0100") {
        return Ok(base64::engine::general_purpose::STANDARD.encode(bytes));
    }
    String::from_utf8(bytes).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
}

// Write to a temporary file next to the target, flush it to disk, then rename it over the target.
// A crash mid-save leaves the old file intact. Each write has a temporary file of its own, so two saves of one file
// at the same time (two windows, or Save pressed twice) never write into the same one (issue 2).
pub fn write_atomic(path: &Path, data: &[u8]) -> std::io::Result<()> {
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let dir = path.parent().unwrap_or(Path::new("."));
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let tmp = dir.join(format!(".{name}.saving-{}-{}", std::process::id(), NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)));
    let result = (|| {
        let mut file = fs::File::create_new(&tmp)?;
        file.write_all(data)?;
        file.sync_all()?;
        fs::rename(&tmp, path)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result
}

#[tauri::command]
async fn open_drawing(app: AppHandle, picked: State<'_, Picked>) -> Result<Option<(String, String)>, String> {
    let Some(file) = app.dialog().file().add_filter(OPEN_ALL.0, OPEN_ALL.1).blocking_pick_file() else {
        return Ok(None);
    };
    let path = file.into_path().map_err(|e| e.to_string())?;
    // A spectrum is not a drawing: Octet does not save over it or list it on Home.
    if spectrum::is_jcamp(&path) {
        let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
        return spectrum::read_jcamp(&path, &name).map(|t| Some((path.to_string_lossy().into_owned(), t)));
    }
    let size = fs::metadata(&path).map_err(|e| e.to_string())?.len();
    if size > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot open it.".into());
    }
    stamp(&app, &path);
    let text = read_text_or_cdx(&path).map_err(|e| e.to_string())?;
    // A template file's panes become templates: it is not a drawing to save over or to list on Home.
    if !is_template_file(&path) {
        picked.0.lock().unwrap().insert(path.clone());
        recent::note(&app, &path);
    }
    Ok(Some((path.to_string_lossy().into_owned(), text)))
}

// File > Revert to Saved: the drawing's file as it is on disk, for a file the user picked before.
#[tauri::command]
async fn revert_drawing(app: AppHandle, picked: State<'_, Picked>, path: String) -> Result<String, String> {
    let p = PathBuf::from(&path);
    if !picked.0.lock().unwrap().contains(&p) {
        return Err("Octet cannot read this drawing again. Open it with File > Open.".into());
    }
    let size = fs::metadata(&p).map_err(|_| "This drawing is not where it was. It was moved or deleted.".to_string())?.len();
    if size > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot open it.".into());
    }
    stamp(&app, &p);
    read_text_or_cdx(&p).map_err(|e| e.to_string())
}

// File > Apply Settings From File… (ChemDraw's Apply Document Settings from > Other…): a drawing or a style sheet to
// take the style from. Only read: it is not remembered for Save and does not go in the recent drawings.
#[tauri::command]
async fn pick_style_file(app: AppHandle) -> Result<Option<String>, String> {
    let Some(file) = app.dialog().file().add_filter(STYLES.0, STYLES.1).blocking_pick_file() else {
        return Ok(None);
    };
    let path = file.into_path().map_err(|e| e.to_string())?;
    if fs::metadata(&path).map_err(|e| e.to_string())?.len() > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot open it.".into());
    }
    read_text_or_cdx(&path).map(Some).map_err(|_| "Octet can only take settings from a drawing or a style sheet (Octet, CDXML, CDX or CDS).".to_string())
}

// Opens one of Octet's own links in the browser (or, for feedback, the mail app). The page names it; only these fixed
// addresses can be opened.
#[tauri::command]
async fn open_link(app: tauri::AppHandle, name: String) -> Result<(), String> {
    let url = match name.as_str() {
        "author" => "https://www.linkedin.com/in/sam-ellis-132781206/".to_string(),
        // Help > Report a Problem.
        "issues" => "https://github.com/SamChemMan/Octet-Draw/issues/new".to_string(),
        // What's new > All versions: every version's notes.
        "releases" => "https://github.com/SamChemMan/Octet-Draw/releases".to_string(),
        // What's new > Donate: Sam's Buy Me a Coffee page, the link at the foot of octet.software.
        "donate" => "https://buymeacoffee.com/chemmansam".to_string(),
        // The Feedback button: a new mail to Sam, with the version and system filled in.
        "feedback" => format!(
            "mailto:{FEEDBACK_TO}?subject=Octet%20Draw%20feedback&body=%0A%0A--%0AOctet%20Draw%20{}%20on%20{}",
            app.package_info().version,
            std::env::consts::OS
        ),
        // The Properties panel's PubChem CID: the compound's Safety and Hazards section.
        n if n.starts_with("pubchem:") => pubchem::safety_page(&n["pubchem:".len()..]).ok_or("Octet has no such link.")?,
        _ => return Err("Octet has no such link.".into()),
    };
    open_external(url).map_err(|e| e.to_string())
}

// Where the Feedback button's mail goes (Sam, 19 October 2026).
const FEEDBACK_TO: &str = "samellis1892@gmail.com";

// Shows a file the user opened, saved or exported this session in the system's file manager: Finder on the Mac,
// File Explorer on Windows, its folder on Linux. The page can name no other file.
#[tauri::command]
fn reveal_file(picked: State<'_, Picked>, exported: State<'_, export::Exported>, path: String) -> Result<(), String> {
    let path = PathBuf::from(path);
    if !picked.0.lock().unwrap().contains(&path) && !exported.0.lock().unwrap().contains(&path) {
        return Err("Octet can only show a file it opened or saved.".into());
    }
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut c = std::process::Command::new("open");
        c.arg("-R").arg(&path);
        c
    };
    #[cfg(target_os = "windows")]
    let mut command = {
        use std::os::windows::process::CommandExt;
        let mut c = std::process::Command::new("explorer");
        c.raw_arg(format!("/select,\"{}\"", path.display()));
        c
    };
    #[cfg(target_os = "linux")]
    let shown = linux::spawn(std::process::Command::new("xdg-open").arg(path.parent().unwrap_or(Path::new("/"))));
    #[cfg(not(target_os = "linux"))]
    let shown = command.spawn().map(|_| ());
    shown.map_err(|e| e.to_string())
}

// About > Licences: the licence notices Octet ships (scripts/licences.mjs), in the system's text app.
#[tauri::command]
async fn open_licences(app: AppHandle) -> Result<(), String> {
    let path = app.path().resolve("licences/third-party.txt", tauri::path::BaseDirectory::Resource).map_err(|e| e.to_string())?;
    open_external(&path).map_err(|e| e.to_string())
}

// Settings > General > Add to LibreOffice (Linux): Octet's extension for LibreOffice (tools/libreoffice) in
// LibreOffice's Extension Manager, which asks the user to confirm. `unopkg gui` shows the manager on its own when
// LibreOffice is closed, so no restart is needed, and in LibreOffice when it is open. The .oxt opened as a file
// starts a closed LibreOffice with the file as its argument, and the restart after the install opens it again: a
// second install prompt. A Flatpak Octet has no unopkg and opens the file through the system's portal. Octet writes
// its path again for the extension (linux::note_path).
#[cfg(target_os = "linux")]
#[tauri::command]
async fn add_to_libreoffice(app: AppHandle) -> Result<(), String> {
    let path = app.path().resolve("libreoffice/octet-draw.oxt", tauri::path::BaseDirectory::Resource).map_err(|e| e.to_string())?;
    linux::note_path(&app);
    linux::spawn(std::process::Command::new("unopkg").arg("gui").arg(&path)).or_else(|_| open_external(&path)).map_err(|e| e.to_string())
}

// Import a structure or reaction from another program's file (MOL, SDF, RXN, RDF, CML, SMILES, InChI, CDXML, CDX).
// Returns its name and text (a CDX file's bytes in base64). ct: only a connection table (.ct), for File > More Formats >
// Import a Connection Table….
#[tauri::command]
async fn import_structure(app: AppHandle, ct: Option<bool>) -> Result<Option<(String, String)>, String> {
    let (kind, list): (&str, &[&str]) = if ct == Some(true) { ("Connection Table (CT)", &["ct"]) } else { ("Structures", &["mol", "sdf", "sd", "rxn", "rdf", "rd", "cml", "smi", "smiles", "inchi", "cdxml", "cdx", "ket", "txt"]) };
    let Some(file) = app.dialog().file().add_filter(kind, list).blocking_pick_file() else {
        return Ok(None);
    };
    let path = file.into_path().map_err(|e| e.to_string())?;
    if fs::metadata(&path).map_err(|e| e.to_string())?.len() > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot import it.".into());
    }
    let text = read_text_or_cdx(&path).map_err(|_| "Octet can only import structure files (MOL, SDF, RXN, RDF, CML, SMILES, InChI, CDXML, CDX).".to_string())?;
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    Ok(Some((name, text)))
}

// File > More Formats > Open CIF or mmCIF…: a crystal structure's file. Returns its name and text, with any bytes that
// are not UTF-8 replaced (older CIF files can have Latin-1 names in them). It is not a drawing to save over.
#[tauri::command]
async fn open_cif(app: AppHandle) -> Result<Option<(String, String)>, String> {
    let Some(file) = app.dialog().file().add_filter("CIF and mmCIF", &["cif", "mmcif"]).blocking_pick_file() else {
        return Ok(None);
    };
    let path = file.into_path().map_err(|e| e.to_string())?;
    if fs::metadata(&path).map_err(|e| e.to_string())?.len() > MAX_BYTES {
        return Err("This file is larger than 64 MB. Octet cannot open it.".into());
    }
    let text = String::from_utf8_lossy(&fs::read(&path).map_err(|e| e.to_string())?).into_owned();
    Ok(Some((path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default(), text)))
}

// Saves to `path` if the user picked it earlier, otherwise asks where to save. Returns the path, or None if cancelled.
// name: the name the Save dialog suggests when there is no path (a recovered drawing keeps its name). contents: the
// .oct (and .cdxml) file; cdx: the .cdx file in base64, which the page sends when the file may be a .cdx.
// format: what the Save dialog offers first, "oct" or "cdxml" (Settings > Import and export > Save new drawings as).
#[tauri::command]
async fn save_drawing(app: AppHandle, picked: State<'_, Picked>, path: Option<String>, name: Option<String>, contents: String, cdx: Option<String>, format: Option<String>) -> Result<Option<String>, String> {
    if contents.len() as u64 > MAX_BYTES || cdx.as_ref().is_some_and(|c| c.len() as u64 > MAX_BYTES / 3 * 4 + 4) {
        return Err("This drawing is larger than 64 MB. Octet cannot save it.".into());
    }
    // An old .octet file is saved as a new .oct beside it, so Save asks where, as Save As does.
    let given = path.map(PathBuf::from);
    let stem = given.as_ref().and_then(|p| p.file_stem()).map(|s| s.to_string_lossy().into_owned())
        .or_else(|| name.map(|n| n.chars().filter(|c| !c.is_control() && !"/\\:".contains(*c)).take(200).collect::<String>()).filter(|n| !n.trim().is_empty()))
        .unwrap_or_else(|| "Untitled".into());
    let known = given.filter(|p| picked.0.lock().unwrap().contains(p) && p.extension().is_some_and(|e| SAVES.iter().any(|s| e == *s)));
    let target = match known {
        Some(p) => p,
        None => {
            let ext = SAVES.iter().copied().find(|s| format.as_deref() == Some(*s)).unwrap_or("oct");
            let mut filters: Vec<_> = SAVE.iter().collect();
            filters.sort_by_key(|(_, e)| e[0] != ext);
            let dialog = filters.iter().fold(app.dialog().file(), |d, (name, e)| d.add_filter(*name, e));
            let Some(file) = dialog.set_file_name(format!("{stem}.{ext}")).blocking_save_file() else {
                return Ok(None);
            };
            let mut p = file.into_path().map_err(|e| e.to_string())?;
            if p.extension().is_none_or(|e| !SAVES.iter().any(|s| e == *s)) {
                p.set_extension(ext);
            }
            p
        }
    };
    let bytes = if target.extension().is_some_and(|e| e == "cdx") {
        use base64::Engine;
        let b64 = cdx.ok_or("Octet cannot save this drawing as CDX.")?;
        base64::engine::general_purpose::STANDARD.decode(b64).map_err(|_| "Octet cannot save this drawing as CDX.".to_string())?
    } else {
        contents.into_bytes()
    };
    write_atomic(&target, &bytes).map_err(|e| e.to_string())?;
    stamp(&app, &target);
    picked.0.lock().unwrap().insert(target.clone());
    recent::note(&app, &target);
    Ok(Some(target.to_string_lossy().into_owned()))
}

// An object window's File > Update <document> and Close and Return to <document>. In menu text & marks the next
// letter as an access key, so an & in the document's name is written &&.
fn object_texts(host: &str) -> (String, String) {
    let h = host.replace('&', "&&");
    (format!("Update {h}"), format!("Close and Return to {h}"))
}

// File and Edit menus. Custom items send their id to the page as a "menu" event; Cut, Copy and Paste
// stay native on the Mac and Windows so the page gets ordinary clipboard events. Select All selects the drawing, not
// the page. Each menu in the bar has its own access key (the letter after &): Alt and the letter open it on Windows
// (access_keys.rs, in the main window and the Reaxys window) and Linux, and a screen reader on Windows opens it the same way (MSAA and UI Automation press the
// access key). The Mac shows no &.
// object: the document's name, for an object window's menu bar (decision 0023): File's Save becomes "Update <document>"
// (Ctrl+S), Save As "Save Copy As…", Close "Close and Return to <document>", and Revert to Saved goes, as Windows'
// guidelines for objects opened in a window give them.
fn menu(app: &AppHandle, palette: &[String], text: &(Vec<String>, Vec<f64>), overrides: &HashMap<String, String>, online: bool, object: Option<&str>) -> tauri::Result<Built> {
    // Every command goes through here: it is listed (with the menu it is in) and takes the user's shortcut if they
    // set one, else its default ("" for none).
    let (list, section) = (RefCell::new(Vec::new()), RefCell::new(String::new()));
    let item = |id: &str, text: &str, keys: &str| {
        list.borrow_mut().push((id.to_string(), text.to_string(), section.borrow().clone(), keys.to_string()));
        let k = overrides.get(id).cloned().unwrap_or_else(|| keys.to_string());
        MenuItem::with_id(app, id, text, true, if k.is_empty() { None } else { Some(k) })
    };
    // A tickable command, listed and given the user's shortcut as `item` does. The page sets its tick.
    let check = |id: &str, text: &str, keys: &str| {
        list.borrow_mut().push((id.to_string(), text.to_string(), section.borrow().clone(), keys.to_string()));
        let k = overrides.get(id).cloned().unwrap_or_else(|| keys.to_string());
        CheckMenuItem::with_id(app, id, text, true, false, if k.is_empty() { None } else { Some(k) })
    };
    let sep = || PredefinedMenuItem::separator(app);
    // Open Recent, as ChemDraw's and every Mac app's: the recent drawings (Home's list), newest first, then Clear Menu.
    // The items are not commands with shortcuts, so Settings does not list them.
    let recents = recent::titles(app)
        .into_iter()
        .enumerate()
        .map(|(k, title)| MenuItem::with_id(app, format!("recent_{k}"), title, true, None::<&str>))
        .collect::<tauri::Result<Vec<_>>>()?;
    let (recent_sep, clear) = (sep()?, MenuItem::with_id(app, "recent_clear", "Clear Menu", !recents.is_empty(), None::<&str>)?);
    let mut recent_items: Vec<&dyn IsMenuItem<Wry>> = recents.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect();
    if !recents.is_empty() {
        recent_items.push(&recent_sep);
    }
    recent_items.push(&clear);
    let open_recent = Submenu::with_items(app, "Open Recent", true, &recent_items)?;
    // File > New For: Quick start (as on Home), then Paper, Thesis, Slides, Poster and Experiment, then the user's own
    // purposes.
    let (own, current) = app.state::<Purposes>().0.lock().unwrap().clone();
    section.replace("File › New For".into());
    let quick = item("new_quick", "Quick start", "")?;
    let quick_sep = sep()?;
    let purposes = [("paper", "Paper"), ("thesis", "Thesis"), ("slides", "Slides"), ("poster", "Poster"), ("experiment", "Experiment")].iter()
        .map(|(id, name)| item(&format!("new_{id}"), name, ""))
        .collect::<tauri::Result<Vec<_>>>()?;
    let own_items = own.iter().enumerate().map(|(k, name)| item(&format!("new_own_{k}"), name, "")).collect::<tauri::Result<Vec<_>>>()?;
    let own_sep = sep()?;
    let mut new_for_items: Vec<&dyn IsMenuItem<Wry>> = vec![&quick, &quick_sep];
    new_for_items.extend(purposes.iter().map(|m| m as &dyn IsMenuItem<Wry>));
    if !own_items.is_empty() {
        new_for_items.push(&own_sep);
        new_for_items.extend(own_items.iter().map(|m| m as &dyn IsMenuItem<Wry>));
    }
    let new_for = Submenu::with_items(app, "New For", true, &new_for_items)?;
    // File > Save Templates for ChemDraw: each template set (as View > Templates lists them, "ctp_<k>") saved as a
    // ChemDraw template file. The items change with the sets, so they are not commands with shortcuts.
    let template_sets = app.state::<TemplateSets>().0.lock().unwrap().clone();
    let ctp_items = template_sets.iter().flatten().enumerate()
        .map(|(k, name)| MenuItem::with_id(app, format!("ctp_{k}"), name, true, None::<&str>))
        .collect::<tauri::Result<Vec<_>>>()?;
    let ctp_seps = [sep()?, sep()?];
    let ctp_list = in_groups(&ctp_items, &template_sets, &ctp_seps);
    let save_ctp = Submenu::with_items(app, "Save Templates for ChemDraw", !ctp_items.is_empty(), &ctp_list)?;
    // File > More Formats, while Settings > Pro > More formats is on: the rare formats, as the page lists them. Each is a
    // command with a shortcut, as File's others are. Off, File has no More Formats.
    let more_list = app.state::<MoreFormats>().0.lock().unwrap().clone();
    section.replace("File › More Formats".into());
    let more_items = more_list.iter().flatten().map(|(id, name)| item(id, name, "")).collect::<tauri::Result<Vec<_>>>()?;
    let more = Submenu::with_items(app, "More Formats", !more_items.is_empty(), &more_items.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect::<Vec<_>>())?;
    section.replace("File".into());
    let new_name = if current.is_empty() { "New".to_string() } else { format!("New {current}") };
    let revert = item("revert", "Revert to Saved", "")?;
    let file = Submenu::with_items(app, "&File", true, &[
        &item("home", "Home", "")?,
        &item("new", &new_name, "CmdOrCtrl+N")?,
        &new_for,
        &item("open", "Open…", "CmdOrCtrl+O")?,
        &open_recent,
        &item("import", "Import a Structure…", "")?,
        &item("insert_file", "Insert…", "")?,
        &sep()?,
        &item("save", &object.map_or("Save".into(), |h| object_texts(h).0), "CmdOrCtrl+S")?,
        &item("save_as", if object.is_some() { "Save Copy As…" } else { "Save As…" }, "CmdOrCtrl+Shift+S")?,
        &revert,
        // ChemDraw's key: ⌃⌘E.
        // ⌃⌘E on the Mac; Ctrl+Shift+E elsewhere, where Control and Command are both Ctrl.
        &item("export", "Export…", if cfg!(target_os = "macos") { "Ctrl+CmdOrCtrl+E" } else { "CmdOrCtrl+Shift+E" })?,
        &save_ctp,
        &more,
        &sep()?,
        &item("page_setup", "Page Setup…", "CmdOrCtrl+Shift+P")?,
        &item("print", "Print…", "CmdOrCtrl+P")?,
        // ChemDraw's Print dialog: Selection.
        &item("print_selection", "Print Selection…", "")?,
        &sep()?,
        &item("document", "Document Settings…", "")?,
        &item("apply_style_file", "Apply Settings From File…", "")?,
        &sep()?,
    ])?;
    // Close Window: the system's item on the Mac and Windows, Octet's own on Linux, where GTK has none. Windows and
    // Linux end Octet from File > Exit, as their apps do (REL-18); on the Mac it is Octet Draw > Quit Octet Draw. Not the
    // system's quit, which closes Octet at once: the page asks to save unsaved changes first.
    if object.is_some() {
        file.remove(&revert)?;
    }
    // The picture selected in Word, or a new drawing at Word's cursor, in an object window (word.rs). After Insert…
    #[cfg(target_os = "macos")]
    file.insert(&item("edit_word", "Edit Picture from Word", "")?, 7)?;
    if more_list.is_none() {
        file.remove(&more)?;
    }
    let close_text = object.map(|h| object_texts(h).1);
    #[cfg(not(target_os = "linux"))]
    file.append(&match close_text.as_deref() {
        None => PredefinedMenuItem::close_window(app, None)?,
        Some(t) => PredefinedMenuItem::close_window(app, Some(t))?,
    })?;
    #[cfg(target_os = "linux")]
    file.append(&item("close", close_text.as_deref().unwrap_or("Close Window"), "CmdOrCtrl+W")?)?;
    #[cfg(not(target_os = "macos"))]
    {
        file.append(&sep()?)?;
        file.append(&item("quit", "Exit", "CmdOrCtrl+Q")?)?;
    }
    // Copy As, as ChemDraw's: each puts the selected structures (or all of them) on the clipboard as text. ChemDraw's
    // keys: ⌥⌘C SMILES, ⌘D CDXML Text, ⌥⌘O MOL Text (V3000 since ChemDraw 26.1), ⇧⌥⌘O MOL V2000 Text, ⌥⌘E HELM (on
    // the Mac only: Ctrl+Alt+E is AltGr+E, which types € on many keyboards).
    section.replace("Edit › Copy As".into());
    let copy_as = Submenu::with_items(app, "Copy As", true, &[
        &item("copy_smiles", "SMILES", "Alt+CmdOrCtrl+C")?,
        &item("copy_inchi", "InChI", "")?,
        &item("copy_inchikey", "InChIKey", "")?,
        &item("copy_cdxml", "CDXML Text", "CmdOrCtrl+D")?,
        &item("copy_mol", "MOL Text", "Alt+CmdOrCtrl+O")?,
        &item("copy_mol_v2000", "MOL V2000 Text", "Alt+Shift+CmdOrCtrl+O")?,
        &item("copy_helm", "HELM", if cfg!(target_os = "macos") { "Alt+CmdOrCtrl+E" } else { "" })?,
        &item("copy_fasta", "FASTA", "")?,
    ])?;
    section.replace("Edit".into());
    // Cut, Copy and Paste: the system's items on the Mac, and on Windows, where they press the keys in the window.
    // GTK's items press the keys only with libxdo, which Octet does not use, so on Linux they are Octet's own, as Close
    // Window is: the page runs them on the drawing or on the text field that has the focus (Editor.tsx).
    #[cfg(not(target_os = "linux"))]
    let (cut, copy, paste) = (PredefinedMenuItem::cut(app, None)?, PredefinedMenuItem::copy(app, None)?, PredefinedMenuItem::paste(app, None)?);
    #[cfg(target_os = "linux")]
    let (cut, copy, paste) = (item("cut", "Cut", "CmdOrCtrl+X")?, item("copy", "Copy", "CmdOrCtrl+C")?, item("paste", "Paste", "CmdOrCtrl+V")?);
    let edit = Submenu::with_items(app, "&Edit", true, &[
        &item("undo", "Undo", "CmdOrCtrl+Z")?,
        &item("redo", "Redo", "CmdOrCtrl+Y")?,
        // ChemDraw's Repeat: the last turn, flip, scale or style again. Redo's ⌘Y repeats when there is nothing to redo.
        &item("repeat", "Repeat", "")?,
        &sep()?,
        &cut,
        &copy,
        &paste,
        &item("select_all", "Select All", "CmdOrCtrl+A")?,
        &item("invert_selection", "Invert Selection", "CmdOrCtrl+Shift+I")?,
        &sep()?,
        &copy_as,
    ])?;
    // Windows and Linux: Settings at the end of Edit, as their apps have it; on the Mac it is in the Octet menu.
    #[cfg(not(target_os = "macos"))]
    {
        edit.append(&sep()?)?;
        edit.append(&item("settings", "Settings…", "CmdOrCtrl+,")?)?;
    }
    section.replace("View".into());
    // ChemDraw's Show Crosshair (⌥⌘X) and Show Rulers (⌘;), in its order. ChemDraw has no grid: Show Grid (⌘') and
    // Snap to Grid (⇧⌘') take Affinity Designer's and Illustrator's keys.
    let grid = check("grid", "Show Grid", "CmdOrCtrl+'")?;
    let crosshair = check("crosshair", "Show Crosshair", "Alt+CmdOrCtrl+X")?;
    let rulers = check("rulers", "Show Rulers", "CmdOrCtrl+;")?;
    let snap = check("snap", "Snap to Objects", "")?;
    let snap_grid = check("snap_grid", "Snap to Grid", "Shift+CmdOrCtrl+'")?;
    // ChemDraw's View > Show Chemical Warnings.
    let warnings = check("warnings", "Show Chemical Warnings", "")?;
    // ChemDraw's View > Show Reaction Interpretation.
    let interpretation = check("interpretation", "Show Reaction Interpretation", "")?;
    // View > Templates: each set shows or hides its floating palette, ticked while it is open (ChemDraw's View > Templates
    // toggles a palette's window). The user's sets come first, then Octet's structures, then its clip art. The items
    // change with the sets, so they are not commands with shortcuts, and Settings does not list them.
    let set_items = template_sets.iter().flatten().enumerate()
        .map(|(k, name)| CheckMenuItem::with_id(app, format!("templates_{k}"), name, true, false, None::<&str>))
        .collect::<tauri::Result<Vec<_>>>()?;
    let sets_seps = [sep()?, sep()?];
    let sets_list = in_groups(&set_items, &template_sets, &sets_seps);
    let templates = Submenu::with_items(app, "Templates", !set_items.is_empty(), &sets_list)?;
    let view = Submenu::with_items(app, "&View", true, &[
        // ChemDraw's keys: Actual Size and Fit to Window.
        &item("zoom_actual", "Actual Size", "CmdOrCtrl+\\")?,
        &item("zoom_fit", "Fit to Window", "CmdOrCtrl+/")?,
        // The selection (or the whole drawing) in the middle of the window, at the same zoom. ChemDraw has no such item; its
        // Magnify keeps the selection in view.
        &item("centre_view", "Centre in Window", "Alt+CmdOrCtrl+/")?,
        // ChemDraw's Show Document: the whole page.
        &item("show_page", "Show Page", "")?,
        // Sam's keys (31 October 2026), not ChemDraw's ⇧⌘> and ⇧⌘<: ⇧⌘+ and ⇧⌘-.
        &item("zoom_in", "Magnify", "CmdOrCtrl+Shift+=")?,
        &item("zoom_out", "Reduce", "CmdOrCtrl+Shift+-")?,
        &sep()?,
        &grid,
        &crosshair,
        &rulers,
        &sep()?,
        &snap,
        &snap_grid,
        &warnings,
        &interpretation,
        &item("actions", "Show or Hide Actions", "")?,
        &item("properties", "Show or Hide Properties", "")?,
        // The spectrum or Mass spec panel shown goes to its pill beside its structure, or the last one comes back.
        &item("toggle_spectrum", "Show or Hide Spectrum", "")?,
        &templates,
        // Not ⌘K, which is ChemDraw's Scale.
        &item("command_palette", "Command Palette…", "CmdOrCtrl+Shift+A")?,
    ])?;
    // Structure > Enhanced Stereochemistry, as ChemDraw's.
    section.replace("Structure › Enhanced Stereochemistry".into());
    let enhanced = Submenu::with_items(app, "Enhanced Stereochemistry", true, &[
        &item("stereo_clear", "Clear All", "")?,
        &item("stereo_abs", "Mark as Absolute", "")?,
        &item("stereo_or", "Create Or Group", "")?,
        &item("stereo_and", "Create And Group", "")?,
    ])?;
    // Structure commands keep ChemDraw's shortcuts.
    section.replace("Structure".into());
    let structure = Submenu::with_items(app, "&Structure", true, &[
        &item("check_structure", "Check Structure", "")?,
        &item("clean_up", "Clean Up Structure", "CmdOrCtrl+Shift+K")?,
        &item("clean_reaction", "Clean Up Reaction", "CmdOrCtrl+Shift+X")?,
        // ChemDraw's 3D Clean Up (⇧⌘D): a 3D shape for the selected structures.
        &item("clean_3d", "3D Clean Up", "CmdOrCtrl+Shift+D")?,
        &item("atom_properties", "Atom Properties…", "")?,
        &item("bond_properties", "Bond Properties…", "")?,
        &item("bracket_properties", "Bracket Properties…", "")?,
        &sep()?,
        &item("expand_label", "Expand Label", "")?,
        &item("contract_label", "Contract Label", "")?,
        &item("expand_generic", "Expand Generic Structure", "")?,
        &item("expand_generic_sdf", "Expand Generic Structure to SDF…", "")?,
        &item("aromatic_display", "Toggle Aromatic Display", "Alt+CmdOrCtrl+K")?,
        &item("hydrogen_display", "Toggle Hydrogen Display", "")?,
        &item("structure_perspective", "Structure Perspective", "Alt+CmdOrCtrl+S")?,
        // Query and Markush structures, as ChemDraw's Structure menu has them.
        &item("add_multicentre", "Add Multi-Centre Attachment", "")?,
        &item("add_variable", "Add Variable Attachment", "")?,
        &item("rlogic", "R-Logic Query…", "")?,
        &enhanced,
        &sep()?,
        &item("map_reaction", "Map Reaction Atoms", "")?,
        &item("clear_reaction_map", "Clear Reaction Map", "")?,
        &item("stoichiometry", "Analyse Stoichiometry", "")?,
        &sep()?,
        &item("predict_1h", "Predict ¹H-NMR Shifts", "")?,
        &item("predict_13c", "Predict ¹³C-NMR Shifts", "")?,
        &item("predict_19f", "Predict ¹⁹F-NMR Shifts", "")?,
        &item("predict_31p", "Predict ³¹P-NMR Shifts", "")?,
        // With the two NMR items, as the Actions panel has them; the Mass spec analysis tool stays in the toolbar.
        &item("mass_spec", "Show Mass Spec Analysis", "")?,
        &sep()?,
        // ChemDraw's Add Structure to Dictionary…: a name of the user's own for the selected structure.
        &item("dictionary_add", "Add Structure to Dictionary…", "")?,
        &item("name_to_structure", "Convert Name to Structure", "CmdOrCtrl+Shift+N")?,
        // One-letter peptide, RNA and DNA codes, drawn through Name to Structure (issue 27).
        &item("insert_peptide", "Insert Peptide…", "")?,
        &item("insert_rna", "Insert RNA…", "")?,
        &item("insert_dna", "Insert DNA…", "")?,
        &item("structure_to_name", "Convert Structure to Name", "Alt+CmdOrCtrl+N")?,
    ])?;
    // Align and Distribute, as ChemDraw's (lined up on the highest thing; spaced out between the two at the ends).
    section.replace("Object › Align".into());
    let align = Submenu::with_items(app, "Align", true, &[
        &item("arrange_left", "Left Edges", "Alt+Shift+CmdOrCtrl+L")?,
        &item("arrange_centre", "Left-Right Centres", "Alt+Shift+CmdOrCtrl+C")?,
        &item("arrange_right", "Right Edges", "Alt+Shift+CmdOrCtrl+R")?,
        &item("arrange_top", "Top Edges", "Alt+Shift+CmdOrCtrl+T")?,
        &item("arrange_middle", "Top-Bottom Centres", "Alt+Shift+CmdOrCtrl+M")?,
        &item("arrange_bottom", "Bottom Edges", "Alt+Shift+CmdOrCtrl+B")?,
    ])?;
    section.replace("Object › Distribute".into());
    let distribute = Submenu::with_items(app, "Distribute", true, &[
        &item("arrange_across", "Horizontally", "Alt+Shift+CmdOrCtrl+H")?,
        &item("arrange_down", "Vertically", "Alt+Shift+CmdOrCtrl+V")?,
    ])?;
    // Add Frame, as ChemDraw's: a frame round everything selected.
    section.replace("Object › Add Frame".into());
    let frame = Submenu::with_items(app, "Add Frame", true, &[
        &item("frame_brackets", "Brackets", "")?,
        &item("frame_parens", "Parentheses", "")?,
        &item("frame_braces", "Braces", "")?,
        &item("frame_box", "Rectangle", "")?,
        &item("frame_rounded", "Rounded Rectangle", "")?,
        &item("frame_box_shadow", "Rectangle with Shadow", "")?,
        &item("frame_rounded_shadow", "Rounded Rectangle with Shadow", "")?,
    ])?;
    section.replace("Object".into());
    // ChemDraw's Fixed Lengths (⌘L) and Fixed Angles (⌘E): ticked, a dragged bond is one bond length long and at a
    // 15° step.
    let fixed_lengths = check("fixed_lengths", "Fixed Lengths", "CmdOrCtrl+L")?;
    let fixed_angles = check("fixed_angles", "Fixed Angles", "CmdOrCtrl+E")?;
    let object = Submenu::with_items(app, "&Object", true, &[
        &align,
        &distribute,
        &item("centre_page", "Centre on Page", "")?,
        &sep()?,
        &fixed_lengths,
        &fixed_angles,
        &sep()?,
        &item("show_stereo", "Show Stereochemistry", "")?,
        &item("atom_numbers", "Show Atom Numbers", "")?,
        &sep()?,
        &item("group", "Group", "CmdOrCtrl+G")?,
        &item("ungroup", "Ungroup", "CmdOrCtrl+Shift+G")?,
        // ChemDraw's Group > Integral: a click on any part picks the whole group.
        &item("group_integral", "Pick as One", "")?,
        // ChemDraw's Join (⌘J): atoms or bonds from different structures become one.
        &item("join", "Join", "CmdOrCtrl+J")?,
        &sep()?,
        &item("bring_front", "Bring to Front", "CmdOrCtrl+[")?,
        &item("send_back", "Send to Back", "CmdOrCtrl+]")?,
        &sep()?,
        &frame,
        &sep()?,
        // ChemDraw's Flip (a mirror image, no key) and Rotate 180° (stereo kept, ⇧⌘H and ⇧⌘V).
        &item("flatten", "Flatten", "")?,
        &item("mirror_h", "Flip Horizontal", "")?,
        &item("mirror_v", "Flip Vertical", "")?,
        &item("flip_h", "Rotate 180° Horizontal", "CmdOrCtrl+Shift+H")?,
        &item("flip_v", "Rotate 180° Vertical", "CmdOrCtrl+Shift+V")?,
        &item("rotate_dialog", "Rotate…", "CmdOrCtrl+R")?,
        &item("scale_dialog", "Scale…", "CmdOrCtrl+K")?,
    ])?;
    // Text commands style the caption being typed, the picked captions, or the selected atom labels. The fonts and
    // sizes are the Actions panel's (the page sends them); Other Size… types any size, and Last Typed Size uses it
    // again (ChemDraw's Other… and Set Font Size To Last One).
    section.replace("Text › Size".into());
    let sizes = text.1.iter()
        .map(|pt| item(&format!("size_{pt}"), &format!("{pt} pt"), ""))
        .collect::<tauri::Result<Vec<_>>>()?;
    let (size_other, size_last, size_sep) = (item("size_other", "Other Size…", "")?, item("size_last", "Last Typed Size", "")?, sep()?);
    let mut size_items: Vec<&dyn IsMenuItem<Wry>> = sizes.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect();
    size_items.extend([&size_sep as &dyn IsMenuItem<Wry>, &size_other, &size_last]);
    let size = Submenu::with_items(app, "Size", true, &size_items)?;
    // ChemDraw's text keys: Plain ⌘T, Bold ⌘B, Italic ⌘I, Underline ⌘U, Subscript ⌘-, Superscript ⌘+, Formula ⌘F.
    // Fonts: Octet's and the drawing's, then Other Font…, which finds any font on the computer.
    section.replace("Text › Font".into());
    let fonts = text.0.iter()
        .map(|f| item(&format!("font:{f}"), f, ""))
        .collect::<tauri::Result<Vec<_>>>()?;
    let (font_other, font_sep) = (item("font_other", "Other Font…", "")?, sep()?);
    let mut font_items: Vec<&dyn IsMenuItem<Wry>> = fonts.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect();
    font_items.extend([&font_sep as &dyn IsMenuItem<Wry>, &font_other]);
    let font = Submenu::with_items(app, "Font", true, &font_items)?;
    section.replace("Text".into());
    let text = Submenu::with_items(app, "&Text", true, &[
        &font,
        &sep()?,
        &item("text_plain", "Plain", "CmdOrCtrl+T")?,
        &item("text_bold", "Bold", "CmdOrCtrl+B")?,
        &item("text_italic", "Italic", "CmdOrCtrl+I")?,
        &item("text_underline", "Underline", "CmdOrCtrl+U")?,
        &item("text_sub", "Subscript", "CmdOrCtrl+-")?,
        &item("text_super", "Superscript", "CmdOrCtrl+=")?,
        &item("text_formula", "Formula", "CmdOrCtrl+F")?,
        // Octet's own: *italic*, **bold**, LaTeX's \textit{…} and $^{13}$C in the text become rich text (experiment.ts).
        &item("text_markup", "Apply Markup", "")?,
        // As ChemDraw's Character Map window: Greek, arrows and signs typed where the caret is (CharMap.tsx).
        // ⇧⌘Space (Ctrl+Shift+Space): from any text box. The Mac's ⌃⌘Space stays the system's Emoji & Symbols.
        &item("char_map", "Character Map", "CmdOrCtrl+Shift+Space")?,
        &sep()?,
        &item("align_left", "Flush Left", "CmdOrCtrl+Shift+L")?,
        &item("align_centre", "Centre", "CmdOrCtrl+Shift+C")?,
        &item("align_right", "Flush Right", "CmdOrCtrl+Shift+R")?,
        &item("align_justify", "Justified", "CmdOrCtrl+Shift+J")?,
        // Atom labels only, as ChemDraw's: the rest of the label stacked over the atom's own unit, or back to automatic.
        &item("align_above", "Stacked Above", "")?,
        &item("align_auto", "Automatic", "CmdOrCtrl+Shift+M")?,
        &sep()?,
        &size,
        &item("line_spacing", "Line Spacing…", "")?,
    ])?;
    // Curves, as ChemDraw's Curves menu: the line, a head at either end (again takes it off), and a closed curve's fill.
    // Then the heads' shape, as ChemDraw's arrow context menu has it (Solid, Hollow and Angled Arrowhead): ticked for
    // the selection, and only on for arrows and catalytic cycles whose heads take a shape (the page sets both).
    section.replace("Curves".into());
    let heads = [("solid", "Solid Arrowhead"), ("hollow", "Hollow Arrowhead"), ("angled", "Angled Arrowhead")].iter()
        .map(|(id, name)| check(&format!("curves_head_{id}"), name, "").and_then(|c| c.set_enabled(false).map(|_| c)))
        .collect::<tauri::Result<Vec<_>>>()?;
    let curves = Submenu::with_items(app, "&Curves", true, &[
        &item("curves_plain", "Plain", "")?,
        &item("curves_dashed", "Dashed", "")?,
        &item("curves_bold", "Bold", "")?,
        &item("curves_doubled", "Double", "")?,
        &sep()?,
        &item("curves_start_full", "Arrowhead at Start", "")?,
        &item("curves_end_full", "Arrowhead at End", "")?,
        &item("curves_start_left", "Half Arrowhead at Start, Left", "")?,
        &item("curves_start_right", "Half Arrowhead at Start, Right", "")?,
        &item("curves_end_left", "Half Arrowhead at End, Left", "")?,
        &item("curves_end_right", "Half Arrowhead at End, Right", "")?,
        &sep()?,
        &heads[0],
        &heads[1],
        &heads[2],
        &sep()?,
        &item("curves_closed", "Closed", "")?,
        &item("curves_solid", "Filled", "")?,
        &item("curves_shaded", "Shaded", "")?,
        &item("curves_faded", "Faded", "")?,
    ])?;
    // Colour, as ChemDraw's Color menu: it colours whatever is selected. The colours are docstyle.ts's COLOURS.
    // Then the user's own colours by name, Pick from Screen (the eyedropper) and Edit Colours…, which opens them in
    // Settings.
    section.replace("Colour".into());
    let builtin = ["Black", "Ink", "Octet Blue", "Bright Blue", "Green", "Amber", "Red"].iter().enumerate()
        .map(|(k, name)| item(&format!("colour_{k}"), name, ""))
        .collect::<tauri::Result<Vec<_>>>()?;
    let mine = palette.iter().enumerate()
        .map(|(k, name)| item(&format!("colour_user_{k}"), name, ""))
        .collect::<tauri::Result<Vec<_>>>()?;
    let (sep1, sep2, sep3) = (sep()?, sep()?, sep()?);
    let pick_colour = item("colour_pick", "Pick from Screen", "")?;
    let edit_colours = item("colour_other", "Edit Colours…", "")?;
    // ChemDraw's By Element, and its highlight and ring fill colours (the Actions panel's Highlight and Ring fill lists).
    let by_element = item("colour_by_element", "By Element", "")?;
    // The names of docstyle.ts's HIGHLIGHT_COLOURS and RING_FILLS, in the same order.
    let fills = ["None", "Blue", "Sky", "Cyan", "Teal", "Green", "Lime", "Yellow", "Gold", "Orange", "Coral", "Red", "Crimson", "Pink", "Magenta", "Purple", "Violet", "Indigo", "Brown", "Grey", "Slate", "Mint", "Peach", "Lavender", "Sand", "Olive"];
    section.replace("Colour › Highlight".into());
    let highlights = fills[..21].iter().enumerate().map(|(k, name)| item(&format!("highlight_{k}"), name, "")).collect::<tauri::Result<Vec<_>>>()?;
    let highlight = Submenu::with_items(app, "Highlight", true, &highlights.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect::<Vec<_>>())?;
    section.replace("Colour › Ring Fill".into());
    let ringfills = fills.iter().enumerate().map(|(k, name)| item(&format!("ringfill_{k}"), name, "")).collect::<tauri::Result<Vec<_>>>()?;
    let ringfill = Submenu::with_items(app, "Ring Fill", true, &ringfills.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect::<Vec<_>>())?;
    section.replace("Colour".into());
    let mut colour_items: Vec<&dyn IsMenuItem<Wry>> = builtin.iter().map(|m| m as &dyn IsMenuItem<Wry>).collect();
    if !mine.is_empty() {
        colour_items.push(&sep1);
        colour_items.extend(mine.iter().map(|m| m as &dyn IsMenuItem<Wry>));
    }
    colour_items.push(&sep2);
    colour_items.push(&by_element);
    colour_items.push(&highlight);
    colour_items.push(&ringfill);
    colour_items.push(&sep3);
    colour_items.push(&pick_colour);
    colour_items.push(&edit_colours);
    let colour = Submenu::with_items(app, "Co&lour", true, &colour_items)?;
    // Search, after Colour, as ChemDraw's Search menu (Search Reaxys…). Each search is one press, with no dialog.
    // Not ⌥⌘R or ⌥⌘P, which are ChemDraw's (Re-run Script, Paste SMILES).
    section.replace("Search".into());
    let search = Submenu::with_items(app, "Se&arch", true, &[
        &item("search_reaxys", "Search Reaxys", "Alt+CmdOrCtrl+F")?,
        &item("search_reaxys_exact", "Search Reaxys for Exact Structure", "Alt+Shift+CmdOrCtrl+F")?,
        &sep()?,
        &item("search_pubchem", "Search PubChem", "Alt+CmdOrCtrl+U")?,
        &item("search_pubchem_sub", "Search PubChem for Substructures", "Alt+Shift+CmdOrCtrl+U")?,
        &sep()?,
        &item("search_scifinder", "Search SciFinder", "")?,
        &sep()?,
        &item("search_scholar", "Search Google Scholar", "")?,
        &item("search_patents", "Search Google Patents", "")?,
    ])?;
    // Window: Minimize and Full Screen where the system has them (GTK on Linux has neither, Windows has no full screen
    // item), then the open drawings. The Mac lists the windows itself (set_bar); Windows and Linux list them here.
    section.replace("Window".into());
    let window = Submenu::with_id(app, "window", "&Window", true)?;
    #[cfg(not(target_os = "linux"))]
    window.append(&PredefinedMenuItem::minimize(app, None)?)?;
    #[cfg(target_os = "macos")]
    window.append(&PredefinedMenuItem::fullscreen(app, None)?)?;
    if !cfg!(target_os = "macos") {
        windows::list(app, &window)?;
    }
    // Help on every platform, as ChemDraw's (REL-18). On the Mac, set_bar makes it the system's Help menu, with its
    // search field.
    section.replace("Help".into());
    let help = Submenu::with_id_and_items(app, "help", "&Help", true, &[
        &item("tutorial", "Tutorial", "")?,
        &item("shortcuts", "Keyboard Shortcuts", "")?,
        &sep()?,
        &item("report_problem", "Report a Problem…", "")?,
    ])?;
    // Windows and Linux: Check for Updates and About at the end of Help; on the Mac they are in the Octet menu.
    #[cfg(not(target_os = "macos"))]
    {
        help.append(&item("check_updates", "Check for Updates…", "")?)?;
        help.append(&sep()?)?;
        help.append(&item("about", "About Octet Draw", "")?)?;
    }
    section.replace("Octet Draw".into());
    #[cfg(target_os = "macos")]
    let octet = Submenu::with_items(app, "Octet Draw", true, &[
        // Octet's own About window (src/About.tsx): the mark, who made it, and the credits the licences ask for.
        &item("about", "About Octet Draw", "")?,
        // As ChemDraw 26.1's ChemDraw > Check for Updates… (decision 0010).
        &item("check_updates", "Check for Updates…", "")?,
        &sep()?,
        &item("settings", "Settings…", "CmdOrCtrl+,")?,
        &sep()?,
        &PredefinedMenuItem::services(app, None)?,
        &sep()?,
        &PredefinedMenuItem::hide(app, None)?,
        &PredefinedMenuItem::hide_others(app, None)?,
        &PredefinedMenuItem::show_all(app, None)?,
        &sep()?,
        // Not the system's Quit, which closes Octet at once: the page asks to save unsaved changes first.
        &item("quit", "Quit Octet Draw", "CmdOrCtrl+Q")?,
    ])?;
    let mut items: Vec<&dyn IsMenuItem<Wry>> = Vec::new();
    #[cfg(target_os = "macos")]
    items.push(&octet);
    items.extend([&file as &dyn IsMenuItem<Wry>, &edit, &view, &object, &structure, &text, &curves, &colour]);
    if online {
        items.push(&search);
    }
    items.push(&window);
    items.push(&help);
    // Commands of a menu that is not there are not listed (Settings shows no shortcuts for them).
    let listed = list.borrow().iter().filter(|c| online || c.2 != "Search").cloned().collect();
    let mut checks = vec![grid, rulers, crosshair, snap, snap_grid, warnings, interpretation, fixed_lengths, fixed_angles];
    checks.extend(set_items.iter().cloned());
    checks.extend(heads.iter().cloned());
    Ok((Menu::with_items(app, &items)?, checks, listed))
}

fn main() {
    // octet.exe --register-ole and --unregister-ole write and remove this user's keys for Octet Drawing objects, for
    // this program, and end (the CI harness, and a copy with no installer). The installer writes the same keys.
    #[cfg(windows)]
    for a in std::env::args_os().skip(1) {
        match a.to_str() {
            Some("--register-ole") => std::process::exit(match std::env::current_exe() { Ok(me) if ole::win::register(&me) => 0, _ => 1 }),
            Some("--unregister-ole") => {
                ole::win::unregister();
                std::process::exit(0)
            }
            _ => {}
        }
    }
    // Started by Windows for Word (-Embedding, decision 0023): Octet serves an Octet Drawing object and opens no Home.
    let embedding = cfg!(windows) && ole::embedding(std::env::args_os());
    // Started for Word, Home's window is made hidden. Every other start (and the Mac and Linux) is as in 1.1.1: Home
    // is made visible by tauri.conf.json, so no start can leave Octet with no window.
    let mut context = tauri::generate_context!();
    if embedding {
        for w in context.config_mut().app.windows.iter_mut().filter(|w| w.label == "main") {
            w.visible = false;
        }
    }
    let builder = tauri::Builder::default();
    // Windows and Linux start a second Octet for each file opened from Explorer or a file manager. It gives its files
    // to the Octet that runs, and ends. (On the Mac the system sends them to the running Octet itself.) An Octet that
    // Windows started for Word never hands over and ends: Word waits for that process.
    #[cfg(any(windows, target_os = "linux"))]
    let builder = if embedding {
        builder
    } else {
        builder.plugin(tauri_plugin_single_instance::init(|app, args, cwd| {
            let args: Vec<std::ffi::OsString> = args.into_iter().map(std::ffi::OsString::from).collect();
            match objects::object_arg(args.clone(), Path::new(&cwd)) {
                Some((file, host, program)) => objects::open_file(app, file, host, program),
                None => open::offer(app, open::from_args(args, Path::new(&cwd)), None),
            }
        }))
    };
    builder
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(Picked::default())
        .manage(Stamps::default())
        .manage(export::Exported::default())
        .manage(update::Found::default())
        .manage(open::Waiting::default())
        .manage(recent::Recents::default())
        .manage(recent::Experiments::default())
        .manage(home::Home::default())
        .manage(windows::Windows::default())
        .manage(objects::Files::default())
        .manage(MenuKeys::default())
        .manage(MenuList::default())
        .manage(Palette::default())
        .manage(search::Online(Mutex::new(true)))
        .manage(TextLists::default())
        .manage(Purposes::default())
        .manage(TemplateSets::default())
        .manage(MoreFormats::default())
        .invoke_handler(tauri::generate_handler![user_name, recent::recent_list, recent::recent_thumb, recent::recent_remove, recent::open_recent, file_changed, recent::experiment_note, recent::experiment_list, recent::experiment_remove, home::home_read, home::home_write, home::home_pick_drawings, home::home_pick_picture, home::thumb_save, home::thumb_load, home::thumb_drop, revert_drawing, menu_items, set_menu_keys, set_online_search, search::search_online, pubchem::pubchem_structure, pubchem::pubchem_cas, pubchem::pubchem_hazards, open_link, open_licences, reveal_file, open_drawing, pick_style_file, save_drawing, set_check, set_palette, set_text_lists, set_purposes, set_template_sets, set_more_formats, import_structure, open_cif, print_page, clipboard::copy_to_clipboard, clipboard::read_clipboard, objects::ole_update, objects::ole_close, #[cfg(target_os = "macos")] word::word_edit, #[cfg(target_os = "macos")] word::set_word_click, #[cfg(target_os = "linux")] add_to_libreoffice, export::export_file, export::system_fonts, eyedropper::pick_colour, #[cfg(feedback)] feedback::snapshot, #[cfg(feedback)] feedback::send_feedback, update::update_check, update::update_install, recovery::recovery_write, recovery::recovery_clear, recovery::recovery_list, recovery::recovery_open, recovery::recovery_discard, crashlog::log_error, crashlog::crash_report, crashlog::show_log, quit::set_edited, quit::quit_answer, open::take_opened, open::insert_file, windows::open_window, windows::close_window, windows::window_start, windows::window_info, windows::window_empty, windows::window_list, windows::window_show, windows::show_home])
        .setup(move |app| {
            let handle = app.handle();
            // Octet Drawing objects: the class object goes up first, before any window shows, so Word's wait for an
            // Octet it started is short (decision 0023).
            #[cfg(windows)]
            ole::win::start(handle, embedding);
            // Files named when Octet starts (Explorer and file managers pass them as arguments).
            let cwd = std::env::current_dir().unwrap_or_default();
            let object = objects::object_arg(std::env::args_os(), &cwd);
            if !embedding && object.is_none() {
                open::offer(handle, open::from_args(std::env::args_os(), &cwd), None);
            }
            crashlog::install(handle);
            #[cfg(feature = "smoke")]
            smoke::start(handle.clone());
            quit::install(handle);
            #[cfg(target_os = "macos")]
            word::install(handle);
            #[cfg(target_os = "linux")]
            linux::note_path(handle);
            app.manage(recovery::start(handle));
            let (bar, checks, list) = menu(handle, &[], &Default::default(), &HashMap::new(), true, None)?;
            windows::set_menu(handle, None, bar)?;
            #[cfg(windows)]
            if let Some(main) = app.get_webview_window("main") {
                access_keys::install(&main);
            }
            app.manage(Checks(Mutex::new(checks)));
            *app.state::<MenuList>().0.lock().unwrap() = list;
            // An object in a file (--object, objects.rs), once its window can have a menu bar.
            if let Some((file, host, program)) = object.filter(|_| !embedding) {
                objects::open_file(handle, file, host, program);
            }
            // With the Reaxys window in front, Undo, Redo and Select All act on its page. Every other command goes
            // to the window in front (Home or a drawing), and only that window hears it. Quit goes through every
            // window with unsaved changes (quit.rs).
            app.on_menu_event(|app, event| {
                let id = event.id().0.as_str();
                if id == "quit" {
                    quit::start(app);
                    return;
                }
                if id == "recent_clear" {
                    recent::clear(app);
                }
                // Works with any window in front, or none.
                #[cfg(target_os = "macos")]
                if id == "edit_word" {
                    word::edit(app);
                    return;
                }
                // Window > a drawing (Windows and Linux): its window comes to the front, and the menu ticks it again.
                if let Some(label) = id.strip_prefix("window_") {
                    tauri::async_runtime::spawn(windows::window_show(app.clone(), label.to_string()));
                    return;
                }
                if let Some(w) = app.get_webview_window("reaxys").filter(|w| w.is_focused().unwrap_or(false)) {
                    let js = match id {
                        "undo" => Some("document.execCommand('undo')"),
                        "redo" => Some("document.execCommand('redo')"),
                        "select_all" => Some("document.execCommand('selectAll')"),
                        _ => None,
                    };
                    if let Some(js) = js {
                        let _ = w.eval(js);
                        return;
                    }
                }
                if let Some(label) = windows::front(app) {
                    let _ = app.emit_to(label, "menu", id);
                }
            });
            Ok(())
        })
        // Files dropped on the window, with where they were dropped in CSS pixels from the top left. wry 0.57 gives
        // WebView2's point in device pixels, and WebKit's (Mac, Linux) in CSS pixels already.
        .on_window_event(|window, event| {
            if let WindowEvent::Focused(true) = event {
                windows::focused(window.app_handle(), window.label());
            }
            // Only Home and the drawing windows take files (not the Reaxys window).
            if !windows::ours(window.label()) {
                return;
            }
            if let WindowEvent::DragDrop(DragDropEvent::Drop { paths, position }) = event {
                #[cfg(windows)]
                let position = position.to_logical::<f64>(window.scale_factor().unwrap_or(1.0));
                open::offer(window.app_handle(), paths.clone(), Some((window.label().to_string(), position.x, position.y)));
            }
        })
        .build(context)
        .expect("error while running Octet")
        .run(|_app, event| match event {
            // Files opened from Finder or the Dock (a double-click, Open With, a drop on the Dock icon).
            #[cfg(target_os = "macos")]
            tauri::RunEvent::Opened { urls } => open::offer(_app, urls.into_iter().filter_map(|u| u.to_file_path().ok()), None),
            // A window closed: it leaves Home's list, and a quit that waits goes on to the next window (quit.rs).
            // After a quit from the Dock or a logout, AppKit ends Octet, so Tauri does not end it first.
            tauri::RunEvent::WindowEvent { label, event: WindowEvent::Destroyed, .. } => {
                windows::closed(_app, &label);
                quit::closed(_app, &label);
            }
            tauri::RunEvent::ExitRequested { api, .. } if quit::ending() => api.prevent_exit(),
            // Each open object tells Word it closed, and the class object goes (decision 0023). Each object in a file
            // left open closes too (objects.rs): Quit destroys no window.
            tauri::RunEvent::Exit => {
                #[cfg(windows)]
                ole::win::shutdown();
                objects::shutdown(&_app.state::<objects::Files>());
            }
            _ => {}
        });
}

#[cfg(test)]
mod tests {
    use super::*;

    // An & in the document's name shows in an object window's File menu: && in menu text is an &.
    #[test]
    fn a_documents_name_in_the_file_menu_keeps_its_ampersand() {
        assert_eq!(object_texts("R&D report.odt"), ("Update R&&D report.odt".into(), "Close and Return to R&&D report.odt".into()));
        assert_eq!(object_texts("Report.docx"), ("Update Report.docx".into(), "Close and Return to Report.docx".into()));
    }

    // Another app writes the drawing after Octet read it: changed, until Octet reads or writes it again. A file that
    // is gone, or one Octet never read, is not changed.
    #[test]
    fn a_file_changed_elsewhere_is_seen() {
        let path = std::env::temp_dir().join(format!("octet-stamp-test-{}.oct", std::process::id()));
        let stamps = Stamps::default();
        fs::write(&path, "<CDXML/>").unwrap();
        assert!(!changed(&stamps, &path), "a file Octet never read");
        note_stamp(&stamps, &path);
        assert!(!changed(&stamps, &path));
        fs::write(&path, "<CDXML><page/></CDXML>").unwrap();
        assert!(changed(&stamps, &path));
        write_atomic(&path, b"<CDXML/>").unwrap();
        note_stamp(&stamps, &path);
        assert!(!changed(&stamps, &path), "Octet's own save");
        fs::remove_file(&path).unwrap();
        assert!(!changed(&stamps, &path), "a file that is gone");
    }
}
