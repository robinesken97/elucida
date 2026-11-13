// Alt and a letter on Windows: the menu with that access key opens, as in every Windows app. WebView2 has the keyboard
// focus and keeps Alt and a letter from the window (Alt alone and F10 reach it), so no menu opened that way, and screen
// readers could not open the menus: MSAA's default action and UI Automation's Expand on a menu bar item press Alt and
// the item's access key. WebView2 asks the window about such keys first (AcceleratorKeyPressed). An access key of the
// menu bar opens its menu there, before the page sees the key; other letters go on to the page.
use tauri::WebviewWindow;
use webview2_com::AcceleratorKeyPressedEventHandler;
use webview2_com::Microsoft::Web::WebView2::Win32::{COREWEBVIEW2_KEY_EVENT_KIND, COREWEBVIEW2_KEY_EVENT_KIND_SYSTEM_KEY_DOWN};
use windows_sys::Win32::UI::WindowsAndMessaging::{GetMenu, GetMenuItemCount, GetMenuStringW, PostMessageW, MF_BYPOSITION, SC_KEYMENU, WM_SYSCOMMAND};

// The letter after a single & in a menu's name ("&&" is an ampersand), in capitals.
fn mnemonic(name: &str) -> Option<char> {
    let mut chars = name.chars();
    while let Some(c) = chars.next() {
        if c == '&' {
            match chars.next() {
                Some('&') => continue,
                k => return k.map(|k| k.to_ascii_uppercase()),
            }
        }
    }
    None
}

// Whether a virtual key (A to Z) is the access key of a menu in the window's menu bar.
fn access_key(hwnd: isize, key: u32) -> bool {
    if !(u32::from(b'A')..=u32::from(b'Z')).contains(&key) {
        return false;
    }
    // SAFETY: these calls only read the window's own menu bar, and GetMenuStringW writes at most name.len() characters
    // into name.
    unsafe {
        let bar = GetMenu(hwnd as _);
        if bar.is_null() {
            return false;
        }
        (0..GetMenuItemCount(bar).max(0)).any(|i| {
            let mut name = [0u16; 128];
            let n = GetMenuStringW(bar, i as u32, name.as_mut_ptr(), name.len() as i32, MF_BYPOSITION);
            mnemonic(&String::from_utf16_lossy(&name[..n.clamp(0, 128) as usize])) == char::from_u32(key)
        })
    }
}

pub fn install(window: &WebviewWindow) {
    let Ok(hwnd) = window.hwnd() else { return };
    let hwnd = hwnd.0 as isize;
    let _ = window.with_webview(move |webview| {
        let handler = AcceleratorKeyPressedEventHandler::create(Box::new(move |_, args| {
            let Some(args) = args else { return Ok(()) };
            let (mut kind, mut key) = (COREWEBVIEW2_KEY_EVENT_KIND::default(), 0u32);
            // SAFETY: each call writes one value into a local that outlives it.
            unsafe {
                args.KeyEventKind(&mut kind)?;
                args.VirtualKey(&mut key)?;
            }
            // A system key is one pressed with Alt (and not AltGr, which types text).
            if kind == COREWEBVIEW2_KEY_EVENT_KIND_SYSTEM_KEY_DOWN && access_key(hwnd, key) {
                // SAFETY: the window's own handle and a message of two plain numbers, which the window runs as Windows
                // runs Alt and the letter.
                unsafe {
                    args.SetHandled(true)?;
                    PostMessageW(hwnd as _, WM_SYSCOMMAND, SC_KEYMENU as usize, (key + 32) as isize);
                }
            }
            Ok(())
        }));
        let mut token = 0i64;
        // SAFETY: the controller is this window's web view, and the call writes the token into a local.
        let _ = unsafe { webview.controller().add_AcceleratorKeyPressed(&handler, &mut token) };
    });
}
