// Quit from the Dock, the app switcher, a logout or a restart (REL-2). On the Mac these go to the app delegate's
// applicationShouldTerminate:, which tao 0.37 does not have, so Octet adds it to tao's delegate class at start. While
// a drawing has unsaved changes (each window tells set_edited), the quit waits (NSTerminateLater, as a document app's
// does) and each window with unsaved changes asks to save them, one at a time, as Octet > Quit does. Save or Don't
// Save closes the window and the next one asks; after the last, the quit goes on, so a logout or a restart goes on
// too. Cancel stops it (quit_answer). Octet's own Quit asks the same way, and then Octet ends.
use std::collections::BTreeSet;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering::Relaxed};
use std::sync::Mutex;

use tauri::{AppHandle, Emitter, Manager, Window};

// The windows whose drawings have unsaved changes.
static EDITED: Mutex<BTreeSet<String>> = Mutex::new(BTreeSet::new());
// A quit from outside Octet: 0 none, 1 waiting for the windows' answers, 2 answered yes (AppKit ends Octet).
static QUIT: AtomicU8 = AtomicU8::new(0);
// A quit going through the windows with unsaved changes.
static QUITTING: AtomicBool = AtomicBool::new(false);

#[tauri::command]
pub fn set_edited(window: Window, edited: bool) {
    let mut set = EDITED.lock().unwrap();
    if edited {
        set.insert(window.label().into());
    } else {
        set.remove(window.label());
    }
}

// The page kept the drawing (Cancel, or a save that did not happen): the quit stops.
#[tauri::command]
pub fn quit_answer(quit: bool) {
    if !quit {
        QUITTING.store(false, Relaxed);
    }
    answer(quit);
}

// Quit: each window with unsaved changes asks in turn, then Octet ends.
pub fn start(app: &AppHandle) {
    QUITTING.store(true, Relaxed);
    next(app);
}

// A window closed: if a quit goes on, the next window asks.
pub fn closed(app: &AppHandle, label: &str) {
    EDITED.lock().unwrap().remove(label);
    if QUITTING.load(Relaxed) {
        next(app);
    }
}

fn next(app: &AppHandle) {
    let edited = EDITED.lock().unwrap().iter().find(|l| app.get_webview_window(l).is_some()).cloned();
    match edited.and_then(|l| app.get_webview_window(&l)) {
        Some(window) => {
            let _ = window.unminimize();
            let _ = window.show();
            let _ = window.set_focus();
            let _ = window.emit_to(window.label(), "menu", "quit");
        }
        None => {
            QUITTING.store(false, Relaxed);
            if QUIT.load(Relaxed) == 1 {
                answer(true);
            } else {
                app.exit(0);
            }
        }
    }
}

// The answer to a quit that waits, if one does.
pub fn answer(quit: bool) {
    if QUIT.compare_exchange(1, if quit { 2 } else { 0 }, Relaxed, Relaxed).is_err() {
        return;
    }
    // AppKit takes the answer on the main thread. It goes on the main queue, so it runs after the event that
    // brought it, never inside tao's event handler: a yes ends Octet through applicationWillTerminate:, which calls
    // that handler.
    #[cfg(target_os = "macos")]
    dispatch2::DispatchQueue::main().exec_async(move || {
        if let Some(mtm) = objc2::MainThreadMarker::new() {
            objc2_app_kit::NSApplication::sharedApplication(mtm).replyToApplicationShouldTerminate(quit);
        }
    });
}

// Whether AppKit ends Octet after a yes: Tauri must not end it first (main.rs).
pub fn ending() -> bool {
    QUIT.load(Relaxed) == 2
}

#[cfg(target_os = "macos")]
pub fn install(app: &AppHandle) {
    use objc2::runtime::{AnyClass, AnyObject, Imp, Sel};
    use objc2_app_kit::NSApplicationTerminateReply;
    use std::sync::OnceLock;

    static APP: OnceLock<AppHandle> = OnceLock::new();
    // NSTerminateNow with no unsaved changes. Else NSTerminateLater, and the page gets Quit after AppKit's call.
    extern "C" fn should_terminate(_: &AnyObject, _: Sel, _: *mut AnyObject) -> NSApplicationTerminateReply {
        let Some(app) = APP.get().filter(|_| !EDITED.lock().unwrap().is_empty()).cloned() else { return NSApplicationTerminateReply::TerminateNow };
        QUIT.store(1, Relaxed);
        std::thread::spawn(move || start(&app));
        NSApplicationTerminateReply::TerminateLater
    }
    let _ = APP.set(app.clone());
    let Some(class) = AnyClass::get(c"TaoAppDelegateParent") else { return };
    type Method = extern "C" fn(&AnyObject, Sel, *mut AnyObject) -> NSApplicationTerminateReply;
    // SAFETY: the function takes the method's arguments (the delegate, the selector, the NSApplication) and returns
    // an NSUInteger (NSApplicationTerminateReply is one), as the type string "Q@:@" says. class_addMethod adds it
    // only if tao's class has no such method, and never replaces one.
    unsafe {
        let imp: Imp = std::mem::transmute(should_terminate as Method);
        objc2::ffi::class_addMethod(class as *const AnyClass as *mut AnyClass, objc2::sel!(applicationShouldTerminate:), imp, c"Q@:@".as_ptr());
    }
}

#[cfg(not(target_os = "macos"))]
pub fn install(_: &AppHandle) {}
