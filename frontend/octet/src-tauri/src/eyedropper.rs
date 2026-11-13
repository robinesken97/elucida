// The eyedropper's colour from the screen (pickColour in src/ColourPicker.tsx), as #RRGGBB, or None when the user
// cancels or Octet cannot read the screen. On macOS the system's colour sampler shows its loupe: a click picks, Escape
// cancels. On Windows and Linux it is the screen's pixel under the pointer now: the page asks when a press in Octet is
// let go outside the window. Wayland lets no app read the screen, so there it is None and the page picks inside the
// window only. Each platform's work runs on the main thread, as AppKit and GTK need.
use std::sync::mpsc::{channel, Sender};
use tauri::AppHandle;

#[tauri::command]
pub async fn pick_colour(app: AppHandle) -> Option<String> {
    let (tx, rx) = channel();
    app.run_on_main_thread(move || sample(tx)).ok()?;
    tauri::async_runtime::spawn_blocking(move || rx.recv().ok().flatten()).await.ok().flatten()
}

fn hex([r, g, b]: [u8; 3]) -> String {
    format!("#{r:02X}{g:02X}{b:02X}")
}

#[cfg(target_os = "macos")]
fn sample(tx: Sender<Option<String>>) {
    use objc2_app_kit::{NSColor, NSColorSampler, NSColorSpace};
    let byte = |v: f64| (v.clamp(0.0, 1.0) * 255.0).round() as u8;
    // The sampler keeps itself until the user picks or cancels (nil), then calls this once.
    let handler = block2::RcBlock::new(move |colour: *mut NSColor| {
        let rgb = unsafe { colour.as_ref() }.and_then(|c| c.colorUsingColorSpace(&NSColorSpace::sRGBColorSpace()));
        let _ = tx.send(rgb.map(|c| hex([byte(c.redComponent()), byte(c.greenComponent()), byte(c.blueComponent())])));
    });
    unsafe { NSColorSampler::new().showSamplerWithSelectionHandler(&handler) };
}

#[cfg(windows)]
fn sample(tx: Sender<Option<String>>) {
    use windows_sys::Win32::{Foundation::POINT, Graphics::Gdi::{GetDC, GetPixel, ReleaseDC, CLR_INVALID}, UI::WindowsAndMessaging::GetCursorPos};
    let mut at = POINT { x: 0, y: 0 };
    // SAFETY: plain Win32 calls; the screen's device context is released before it returns.
    let c = unsafe {
        let screen = if GetCursorPos(&mut at) != 0 { GetDC(std::ptr::null_mut()) } else { std::ptr::null_mut() };
        if screen.is_null() {
            CLR_INVALID
        } else {
            let c = GetPixel(screen, at.x, at.y);
            ReleaseDC(std::ptr::null_mut(), screen);
            c
        }
    };
    // COLORREF is 0x00BBGGRR.
    let _ = tx.send((c != CLR_INVALID).then(|| hex([c as u8, (c >> 8) as u8, (c >> 16) as u8])));
}

#[cfg(target_os = "linux")]
fn sample(tx: Sender<Option<String>>) {
    use gtk::gdk::{self, prelude::*};
    let pixel = || {
        let display = gdk::Display::default()?;
        // Only X11 lets an app read the screen: under Wayland the root window is not the screen.
        if display.type_().name() != "GdkX11Display" {
            return None;
        }
        let (screen, x, y) = display.default_seat()?.pointer()?.position();
        let bytes = screen.root_window()?.pixbuf(x, y, 1, 1)?.read_pixel_bytes();
        (bytes.len() >= 3).then(|| hex([bytes[0], bytes[1], bytes[2]]))
    };
    let _ = tx.send(pixel());
}

#[cfg(test)]
mod tests {
    #[test]
    fn a_colour_is_six_hex_digits() {
        assert_eq!(super::hex([255, 0, 16]), "#FF0010");
        assert_eq!(super::hex([0, 0, 0]), "#000000");
    }
}
