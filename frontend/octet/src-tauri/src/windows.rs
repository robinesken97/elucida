// Drawing windows. Home is the window "main"; each drawing has a window of its own ("draw-1", "draw-2" and on), as
// ChemDraw has a window for each document. Home (or a drawing window, for New and Open) asks for a new window with
// what it should open, and the new page takes that once it starts (window_start). Each drawing window tells this side
// its name, file and whether it has unsaved changes, for Home's list of open windows.
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use tauri::menu::{CheckMenuItem, Menu, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Emitter, Manager, State, WebviewUrl, WebviewWindowBuilder, Window, Wry};

use crate::MAX_BYTES;

static NEXT: AtomicU64 = AtomicU64::new(1);
// The last of Octet's windows in front, for menu commands while another window (Reaxys) is in front.
static LAST: Mutex<String> = Mutex::new(String::new());

#[derive(Clone, Serialize, Deserialize)]
pub struct Info {
    label: String,
    name: String,
    path: Option<String>,
    edited: bool,
    picture: Option<String>, // the drawing as an SVG, as a recent drawing's (400,000 characters at most)
}

#[cfg(feature = "smoke")]
impl Info {
    pub fn edited(&self) -> bool {
        self.edited
    }
    pub fn label(&self) -> &str {
        &self.label
    }
    pub fn name(&self) -> &str {
        &self.name
    }
}

// What each new window is to open, until its page takes it, and what each drawing window shows.
#[derive(Default)]
pub struct Windows {
    starts: Mutex<HashMap<String, serde_json::Value>>,
    open: Mutex<Vec<Info>>,
    hosts: Mutex<HashMap<String, String>>, // each object window's document (decision 0023)
    // The Mac's menu bars: the app's, and each object window's. Tauri has no menu bar per window on the Mac, so the bar
    // of the window in front goes on the app (bar).
    #[cfg(target_os = "macos")]
    bars: Mutex<(Option<Menu<Wry>>, HashMap<String, Menu<Wry>>)>,
}

// Octet's own windows: Home, the drawing windows and the windows of objects in Office documents (decision 0023),
// not the Reaxys window.
pub fn ours(label: &str) -> bool {
    label == "main" || label.starts_with("draw-") || label.starts_with("object-")
}

// A window came to the front: the Window menu ticks it. On the Mac, its menu bar goes on the app.
pub fn focused(app: &AppHandle, label: &str) {
    if ours(label) {
        *LAST.lock().unwrap() = label.into();
        menus(app);
        #[cfg(target_os = "macos")]
        let _ = bar(app);
    }
}

// A menu bar: the app's (label None), or an object window's (decision 0023: File's Update, Save Copy As and Close and
// Return). On Windows and Linux an object window has a menu bar of its own. On the Mac the app has one, and it shows
// the bar of the window in front.
pub fn set_menu(app: &AppHandle, label: Option<&str>, menu: Menu<Wry>) -> tauri::Result<()> {
    #[cfg(target_os = "macos")]
    {
        {
            let windows = app.state::<Windows>();
            let mut bars = windows.bars.lock().unwrap();
            match label {
                None => bars.0 = Some(menu),
                Some(l) => {
                    bars.1.insert(l.to_string(), menu);
                }
            }
        }
        bar(app)
    }
    #[cfg(not(target_os = "macos"))]
    match (label, label.and_then(|l| app.get_webview_window(l))) {
        (None, _) => crate::set_bar(app, menu),
        (Some(_), Some(w)) => w.set_menu(menu).map(|_| ()),
        (Some(_), None) => Ok(()),
    }
}

// The Mac: the menu bar of the window in front (an object window's, else the app's) goes on the app, if it is not
// there already.
#[cfg(target_os = "macos")]
fn bar(app: &AppHandle) -> tauri::Result<()> {
    let front = front(app);
    let windows = app.state::<Windows>();
    let menu = {
        let bars = windows.bars.lock().unwrap();
        front.and_then(|l| bars.1.get(&l).cloned()).or_else(|| bars.0.clone())
    };
    match menu {
        Some(m) if app.menu().is_none_or(|now| now.id() != m.id()) => crate::set_bar(app, m),
        _ => Ok(()),
    }
}

// The window that gets menu commands: the one in front, else the last of Octet's in front, else Home, else the
// oldest drawing window.
pub fn front(app: &AppHandle) -> Option<String> {
    let windows = app.webview_windows();
    let mut labels: Vec<&String> = windows.keys().filter(|l| ours(l)).collect();
    labels.sort_by_key(|l| (l.as_str() != "main", l.trim_start_matches("draw-").parse::<u64>().unwrap_or(0)));
    let last = LAST.lock().unwrap().clone();
    labels
        .iter()
        .find(|l| windows[l.as_str()].is_focused().unwrap_or(false))
        .or(labels.iter().find(|l| l.as_str() == last))
        .or(labels.first())
        .map(|l| l.to_string())
}

fn changed(app: &AppHandle) {
    let list = app.state::<Windows>().open.lock().unwrap().clone();
    let _ = app.emit("windows", list);
    menus(app);
}

// Windows and Linux: the Window menu lists the open drawings (Home's list), the one in front ticked, after Minimize on
// Windows (GTK has no Minimize). On the Mac the system lists the windows (set_bar in main.rs).
pub fn list(app: &AppHandle, menu: &Submenu<Wry>) -> tauri::Result<()> {
    let fixed = usize::from(cfg!(windows));
    for _ in fixed..menu.items()?.len() {
        menu.remove_at(fixed)?;
    }
    let front = front(app);
    let items = entries(&app.state::<Windows>().open.lock().unwrap(), front.as_deref());
    if fixed > 0 && !items.is_empty() {
        menu.append(&PredefinedMenuItem::separator(app)?)?;
    }
    // On Linux, with no drawing open, the menu is dimmed.
    menu.set_enabled(fixed > 0 || !items.is_empty())?;
    for (id, title, ticked) in items {
        menu.append(&CheckMenuItem::with_id(app, id, title, true, ticked, None::<&str>)?)?;
    }
    Ok(())
}

// Each drawing's item: its id, its window's title (as the page sets it) and whether its window is in front. An & in a
// name is doubled, because a single & makes the next letter an access key.
fn entries(open: &[Info], front: Option<&str>) -> Vec<(String, String, bool)> {
    open.iter()
        .map(|i| {
            let title = if i.edited { format!("{} (edited)", i.name) } else { i.name.clone() };
            (format!("window_{}", i.label), title.replace('&', "&&"), front == Some(i.label.as_str()))
        })
        .collect()
}

// The Window menus listed again, in the menu bar and in each object window's (decision 0023). The lists are made on
// the main thread, one at a time, as a window that comes to the front and one chosen from the menu can ask together.
pub fn menus(app: &AppHandle) {
    if cfg!(target_os = "macos") {
        return;
    }
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || {
        let bars = handle.menu().into_iter().chain(object_hosts(&handle).into_iter().filter_map(|(l, _)| handle.get_webview_window(&l)?.menu()));
        for menu in bars.filter_map(|b| b.get("window")?.as_submenu().cloned()) {
            let _ = list(&handle, &menu);
        }
    });
}

// A new drawing window, a little below and right of the window in front, with what it opens (64 MB at most).
// The commands that make or show windows are async: on Windows, making a window in a synchronous command (which runs
// on the main thread) deadlocks, and the app hangs with a white window.
#[tauri::command]
pub async fn open_window(app: AppHandle, windows: State<'_, Windows>, start: serde_json::Value) -> Result<(), String> {
    if start.to_string().len() as u64 > MAX_BYTES + 4096 {
        return Err("This drawing is larger than 64 MB. Octet cannot open it.".into());
    }
    let label = format!("draw-{}", NEXT.fetch_add(1, Ordering::Relaxed));
    windows.starts.lock().unwrap().insert(label.clone(), start);
    let mut builder = WebviewWindowBuilder::new(&app, &label, WebviewUrl::App("index.html?window".into()))
        .title("Octet Draw")
        .inner_size(1200.0, 800.0)
        .min_inner_size(800.0, 620.0);
    let from = front(&app).and_then(|l| app.get_webview_window(&l));
    if let Some((pos, scale)) = from.and_then(|w| Some((w.outer_position().ok()?, w.scale_factor().ok()?))) {
        let pos = pos.to_logical::<f64>(scale);
        builder = builder.position(pos.x + 28.0, pos.y + 28.0);
    } else {
        builder = builder.center();
    }
    let window = builder.build().map_err(|e| {
        windows.starts.lock().unwrap().remove(&label);
        e.to_string()
    })?;
    #[cfg(windows)]
    crate::access_keys::install(&window);
    let _ = window.set_focus();
    Ok(())
}

// The window of an Octet Drawing object in another program's document (decision 0023, objects.rs): a drawing window
// with the label object-N, a title from the document ("Octet Drawing in Document1") and a File menu of its own
// (Update Document1, Save Copy As…, Close and Return to Document1). Made from the async runtime, never in a call
// from Word.
pub async fn open_object(app: AppHandle, label: String, start: serde_json::Value, host: String) -> Result<(), String> {
    let title = start.get("title").and_then(|t| t.as_str()).unwrap_or("Octet Drawing").to_string();
    app.state::<Windows>().starts.lock().unwrap().insert(label.clone(), start);
    app.state::<Windows>().hosts.lock().unwrap().insert(label.clone(), host.clone());
    let menu = crate::object_menu(&app, &host).map_err(|e| e.to_string())?;
    let builder = WebviewWindowBuilder::new(&app, &label, WebviewUrl::App("index.html?window".into()))
        .title(title)
        .inner_size(1200.0, 800.0)
        .min_inner_size(800.0, 620.0)
        .center();
    #[cfg(not(target_os = "macos"))]
    let builder = builder.menu(menu);
    let window = builder.build().map_err(|e| {
        app.state::<Windows>().starts.lock().unwrap().remove(&label);
        e.to_string()
    })?;
    #[cfg(target_os = "macos")]
    let _ = set_menu(&app, Some(&label), menu);
    #[cfg(windows)]
    crate::access_keys::install(&window);
    let _ = window.set_focus();
    Ok(())
}

// The document has a new name (Save As in Word): the window's File menu says it.
pub fn object_host(app: &AppHandle, label: &str, host: &str) {
    app.state::<Windows>().hosts.lock().unwrap().insert(label.to_string(), host.to_string());
    if let (Some(_), Ok(menu)) = (app.get_webview_window(label), crate::object_menu(app, host)) {
        let _ = set_menu(app, Some(label), menu);
    }
}

// The object windows and their documents' names, for building their menus again.
pub fn object_hosts(app: &AppHandle) -> Vec<(String, String)> {
    let hosts = app.state::<Windows>().hosts.lock().unwrap().clone();
    hosts.into_iter().filter(|(l, _)| app.get_webview_window(l).is_some()).collect()
}

// Close closes the window. On Windows and Linux the menu bar comes off first. On Linux, muda keeps each GTK window's
// menu bar under the window's address and never lets it go, so a new window made at the same address got no menu bar
// (issue 4). On Windows, every window shows the same menu, and DestroyWindow destroys the menu of the window it
// closes, so the other windows lost their menu bar. (On the Mac the menu belongs to the app.)
// home: Windows and Linux, where closing the last drawing window opens Home, so Octet is not left running with no
// window (issue 38).
#[tauri::command]
pub async fn close_window(app: AppHandle, window: Window, home: Option<bool>) -> Result<(), String> {
    if home == Some(true) && last(app.webview_windows().keys().map(String::as_str), window.label()) {
        self::home(&app).map_err(|e| e.to_string())?;
    }
    #[cfg(not(target_os = "macos"))]
    let _ = window.remove_menu();
    window.destroy().map_err(|e| e.to_string())
}

// What this window opens: once, then nothing.
#[tauri::command]
pub fn window_start(window: Window, windows: State<'_, Windows>) -> Option<serde_json::Value> {
    windows.starts.lock().unwrap().remove(window.label())
}

// A drawing window's name, file and unsaved changes, for Home, and its picture when it sends one (else the last).
// Home's window sends them too while it holds a drawing.
#[tauri::command]
pub fn window_info(app: AppHandle, window: Window, windows: State<'_, Windows>, name: String, path: Option<String>, edited: bool, picture: Option<String>) {
    if !ours(window.label()) {
        return;
    }
    let picture = picture.filter(|p| p.len() <= 400_000);
    let name = name.chars().filter(|c| !c.is_control()).take(200).collect();
    {
        let mut open = windows.open.lock().unwrap();
        match open.iter_mut().find(|i| i.label == window.label()) {
            Some(i) => {
                let picture = picture.or(i.picture.take());
                *i = Info { label: window.label().into(), name, path, edited, picture };
            }
            None => open.push(Info { label: window.label().into(), name, path, edited, picture }),
        }
    }
    changed(&app);
}

// Home's window holds no drawing: it leaves the list.
#[tauri::command]
pub fn window_empty(app: AppHandle, window: Window) {
    if window.label() == "main" {
        closed(&app, "main");
    }
}

#[tauri::command]
pub fn window_list(windows: State<'_, Windows>) -> Vec<Info> {
    windows.open.lock().unwrap().clone()
}

// A window from Home's list or the Window menu, in front. Home's window shows its drawing.
#[tauri::command]
pub async fn window_show(app: AppHandle, label: String) -> Result<(), String> {
    let window = app.get_webview_window(&label).filter(|_| ours(&label)).ok_or("This window is closed.")?;
    let _ = window.unminimize();
    let _ = window.show();
    window.set_focus().map_err(|e| e.to_string())?;
    focused(&app, &label);
    if label == "main" {
        let _ = app.emit_to("main", "show-drawing", ());
    }
    Ok(())
}

// File > Home from a drawing window: Home in front, opened again if it was closed. When Home's window holds the first
// drawing, Home shows over it.
#[tauri::command]
pub async fn show_home(app: AppHandle) -> Result<(), String> {
    home(&app).map_err(|e| e.to_string())?;
    app.emit_to("main", "show-home", ()).map_err(|e| e.to_string())
}

pub fn home(app: &AppHandle) -> tauri::Result<()> {
    let window = match app.get_webview_window("main") {
        Some(w) => w,
        None => {
            let w = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("Octet Draw")
                .inner_size(1200.0, 800.0)
                .min_inner_size(800.0, 620.0)
                .center()
                .build()?;
            #[cfg(windows)]
            crate::access_keys::install(&w);
            w
        }
    };
    let _ = window.unminimize();
    window.show()?;
    window.set_focus()
}

// Whether a window is the last of Octet's windows open.
fn last<'a>(labels: impl Iterator<Item = &'a str>, label: &str) -> bool {
    !labels.into_iter().any(|l| ours(l) && l != label)
}

// A closed window leaves Home's list.
pub fn closed(app: &AppHandle, label: &str) {
    let windows = app.state::<Windows>();
    windows.starts.lock().unwrap().remove(label);
    windows.hosts.lock().unwrap().remove(label);
    if let Some(id) = crate::objects::id_of(label) {
        crate::objects::closed(app, id, false);
        #[cfg(windows)]
        crate::ole::win::closed(id);
    }
    // An Octet that Windows started for Word ends when its last window closes and Word holds no object.
    #[cfg(windows)]
    crate::ole::win::maybe_exit(app);
    // The Mac: the next window's menu bar, or the app's.
    #[cfg(target_os = "macos")]
    {
        windows.bars.lock().unwrap().1.remove(label);
        let _ = bar(app);
    }
    let before = {
        let mut open = windows.open.lock().unwrap();
        let n = open.len();
        open.retain(|i| i.label != label);
        n != open.len()
    };
    if before {
        changed(app);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn octets_windows_only() {
        assert!(ours("main") && ours("draw-3") && ours("object-2"));
        assert!(!ours("reaxys") && !ours("drawing"));
    }

    // The Window menu names each drawing as its window's title does, ticks the one in front, and shows an & in a name.
    #[test]
    fn the_window_menu_lists_the_drawings() {
        let info = |label: &str, name: &str, edited| Info { label: label.into(), name: name.into(), path: None, edited, picture: None };
        let open = [info("main", "Aspirin", false), info("draw-2", "R&D route", true)];
        let item = |id: &str, title: &str, ticked| (id.to_string(), title.to_string(), ticked);
        assert_eq!(entries(&open, Some("draw-2")), [item("window_main", "Aspirin", false), item("window_draw-2", "R&&D route (edited)", true)]);
        assert!(entries(&open, Some("draw-5")).iter().all(|e| !e.2), "a window not on the list is not ticked");
        assert!(entries(&[], Some("main")).is_empty());
    }

    // Closing the last drawing window opens Home; with Home or another drawing window open, nothing opens.
    #[test]
    fn the_last_window_closed_opens_home() {
        assert!(last(["draw-2"].into_iter(), "draw-2"));
        assert!(last(["draw-2", "reaxys"].into_iter(), "draw-2"));
        assert!(!last(["draw-2", "main"].into_iter(), "draw-2"));
        assert!(!last(["draw-2", "draw-5"].into_iter(), "draw-2"));
    }
}
