// Feedback (Sam, 17 October 2026), for testers: in every build except the public release, which the release workflow
// makes with OCTET_FEEDBACK=0 (build.rs, REL-8). A picture of the window and the tester's note, as an email draft to
// Sam with the picture attached. Octet sends nothing itself: the mail app opens the draft, and the tester sends it.
use base64::Engine;
use tauri::{AppHandle, Manager, WebviewWindow};

const TO: &str = "samellis2004@gmail.com";
const MAX_NOTE: usize = 20_000;
const MAX_PICTURE: usize = 40 << 20; // base64 characters

// The window as it looks now, as base64 PNG. The web view takes it itself, so no screen-recording permission is asked.
#[tauri::command]
pub async fn snapshot(window: WebviewWindow) -> Result<String, String> {
    #[cfg(target_os = "macos")]
    {
        let (tx, rx) = std::sync::mpsc::channel::<Option<Vec<u8>>>();
        window.with_webview(move |view| mac::snapshot(view.inner(), tx)).map_err(|e| e.to_string())?;
        let png = tauri::async_runtime::spawn_blocking(move || rx.recv_timeout(std::time::Duration::from_secs(5)).ok().flatten())
            .await
            .map_err(|e| e.to_string())?
            .ok_or("Octet cannot take a picture of the window.")?;
        Ok(base64::engine::general_purpose::STANDARD.encode(png))
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = window;
        Err("Octet can take a picture of the window only on the Mac.".into())
    }
}

#[cfg(target_os = "macos")]
mod mac {
    use block2::RcBlock;
    use objc2_app_kit::{NSBitmapImageFileType, NSBitmapImageRep, NSImage};
    use objc2_foundation::{NSDictionary, NSError};
    use objc2_web_kit::WKWebView;
    use std::sync::{mpsc::Sender, Mutex};

    pub fn snapshot(view: *mut std::ffi::c_void, tx: Sender<Option<Vec<u8>>>) {
        // SAFETY: Tauri hands over its own WKWebView, alive for this call, on the main thread.
        let view = unsafe { &*(view as *const WKWebView) };
        let tx = Mutex::new(Some(tx));
        let done = RcBlock::new(move |image: *mut NSImage, _error: *mut NSError| {
            // SAFETY: WebKit passes the picture, or null when it could not take one.
            let png = unsafe { image.as_ref() }.and_then(|image| {
                let tiff = image.TIFFRepresentation()?;
                let rep = NSBitmapImageRep::imageRepWithData(&tiff)?;
                // SAFETY: an empty dictionary is a valid set of properties.
                unsafe { rep.representationUsingType_properties(NSBitmapImageFileType::PNG, &NSDictionary::new()) }.map(|d| d.to_vec())
            });
            if let Some(tx) = tx.lock().ok().and_then(|mut t| t.take()) {
                let _ = tx.send(png);
            }
        });
        // SAFETY: no configuration takes the whole visible page; the block lives as long as WebKit needs it.
        unsafe { view.takeSnapshotWithConfiguration_completionHandler(None, &done) };
    }
}

// Base64 in lines of 76, as email wants.
fn lines(b64: &str) -> String {
    b64.as_bytes().chunks(76).map(|c| std::str::from_utf8(c).unwrap_or("")).collect::<Vec<_>>().join("\r\n")
}

// The feedback as an email draft to Sam, opened in the mail app ready to send: the note, the app's version and
// system, and the picture attached. X-Unsent makes Mail (and Outlook) open it as a new message to send.
// Async, off the main thread: the open crate waits for the Mac's open command to hand the file over.
#[tauri::command]
pub async fn send_feedback(app: AppHandle, note: String, picture: Option<String>) -> Result<(), String> {
    if note.len() > MAX_NOTE || picture.as_ref().is_some_and(|p| p.len() > MAX_PICTURE) {
        return Err("This feedback is too large.".into());
    }
    let b64 = base64::engine::general_purpose::STANDARD;
    let png = match &picture {
        Some(p) => Some(b64.decode(p).map_err(|_| "The picture is damaged.".to_string())?),
        None => None,
    };
    if png.as_ref().is_some_and(|p| !p.starts_with(b"\x89PNG\r\n\x1a\n")) {
        return Err("The picture is damaged.".into());
    }
    let body = format!("{}\n\n— Octet Draw {} on {}", note.trim(), app.package_info().version, std::env::consts::OS);
    let boundary = "octet-feedback-part";
    let mut eml = format!(
        "To: {TO}\r\nSubject: Octet Draw feedback\r\nX-Unsent: 1\r\nMIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=\"{boundary}\"\r\n\r\n\
         --{boundary}\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: base64\r\n\r\n{}\r\n",
        lines(&b64.encode(body))
    );
    if let Some(png) = png {
        eml += &format!(
            "--{boundary}\r\nContent-Type: image/png; name=\"Octet.png\"\r\nContent-Disposition: attachment; filename=\"Octet.png\"\r\nContent-Transfer-Encoding: base64\r\n\r\n{}\r\n",
            lines(&b64.encode(png))
        );
    }
    eml += &format!("--{boundary}--\r\n");
    let dir = app.path().app_cache_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = dir.join("Octet feedback.eml");
    std::fs::write(&path, eml).map_err(|e| e.to_string())?;
    crate::open_external(&path).map_err(|_| "Octet cannot open your mail app.".into())
}
