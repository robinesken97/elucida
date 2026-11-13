// The Linux clipboard for copy and paste (clipboard.rs; REL-3, CH-1), through GTK, which the window already uses
// (X11 and Wayland). GTK works only on its own thread, so each call runs there and the command waits for it.
use gtk::{gdk, Clipboard, TargetEntry, TargetFlags};
use tauri::AppHandle;

use super::MAX_TYPE;

// `f` on GTK's thread; its result back here.
async fn on_gtk<T: Send + 'static>(app: &AppHandle, f: impl FnOnce() -> T + Send + 'static) -> Result<T, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let _ = tx.send(f());
    })
    .map_err(|e| e.to_string())?;
    tauri::async_runtime::spawn_blocking(move || rx.recv()).await.map_err(|e| e.to_string())?.map_err(|e| e.to_string())
}

// Puts the types on the clipboard in their order, in place of what was there. GTK gives each app the type it asks
// for while Octet runs.
pub async fn write(app: &AppHandle, types: Vec<(&'static str, Vec<u8>)>) -> Result<(), String> {
    let done = on_gtk(app, move || {
        let targets: Vec<TargetEntry> = types.iter().enumerate().map(|(k, (n, _))| TargetEntry::new(n, TargetFlags::empty(), k as u32)).collect();
        Clipboard::get(&gdk::SELECTION_CLIPBOARD).set_with_data(&targets, move |_, data, info| {
            if let Some((_, bytes)) = types.get(info as usize) {
                data.set(&data.target(), 8, bytes);
            }
        })
    })
    .await?;
    if done { Ok(()) } else { Err("Octet cannot copy this.".into()) }
}

// The bytes of each named type on the clipboard (64 MB at most), read only if the clipboard has that type and paste
// uses it beside the other types there (clipboard.rs, asked): the owner makes each type when it is asked.
// Also whether the clipboard holds any type at all, apart from the X11 ones every owner offers.
pub async fn read(app: &AppHandle, names: Vec<&'static str>) -> Result<(Vec<(&'static str, Vec<u8>)>, bool), String> {
    on_gtk(app, move || {
        let clipboard = Clipboard::get(&gdk::SELECTION_CLIPBOARD);
        let present: Vec<String> = clipboard.wait_for_targets().unwrap_or_default().iter().map(|a| a.name().to_string()).collect();
        let any = present.iter().any(|p| !["TARGETS", "TIMESTAMP", "MULTIPLE", "SAVE_TARGETS"].contains(&p.as_str()));
        let found: Vec<(&'static str, Vec<u8>)> = names
            .into_iter()
            .filter(|n| super::asked(n, &present))
            .filter_map(|n| {
                let bytes = clipboard.wait_for_contents(&gdk::Atom::intern(n))?.data();
                (!bytes.is_empty() && bytes.len() <= MAX_TYPE).then_some((n, bytes))
            })
            .collect();
        (found, any)
    })
    .await
}
