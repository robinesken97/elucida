// The Windows clipboard for copy and paste (clipboard.rs; REL-3, CH-1). Each call opens the clipboard, works, and
// closes it again. The calls into Windows only move bytes; what is read is checked as hostile in clipboard.rs and
// the page, with no unsafe code there.
use std::ptr::{copy_nonoverlapping, null_mut};

use windows_sys::Win32::Foundation::GlobalFree;
use windows_sys::Win32::Graphics::Gdi::{DeleteEnhMetaFile, GetEnhMetaFileBits, SetEnhMetaFileBits};
use windows_sys::Win32::System::DataExchange::{CloseClipboard, CountClipboardFormats, EmptyClipboard, GetClipboardData, IsClipboardFormatAvailable, OpenClipboard, RegisterClipboardFormatW, SetClipboardData};
use windows_sys::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalSize, GlobalUnlock, GMEM_MOVEABLE};
use windows_sys::Win32::System::Ole::{CF_DIB, CF_ENHMETAFILE, CF_UNICODETEXT};

use super::{DIB, ENHMETAFILE, MAX_TYPE, UNICODE_TEXT};

// A format's number: CF_DIB for the bitmap and CF_UNICODETEXT for text, else the name registered (the same number in
// every app). 0 if Windows refuses the name.
pub fn format(name: &str) -> u32 {
    match name {
        DIB => return u32::from(CF_DIB),
        UNICODE_TEXT => return u32::from(CF_UNICODETEXT),
        ENHMETAFILE => return u32::from(CF_ENHMETAFILE),
        _ => {}
    }
    let wide: Vec<u16> = name.encode_utf16().chain([0]).collect();
    // SAFETY: `wide` is a NUL-terminated UTF-16 string that lives for the call.
    unsafe { RegisterClipboardFormatW(wide.as_ptr()) }
}

// The clipboard, open until this is dropped. Another app can hold it for a moment, so opening tries for half a second.
struct Open;

impl Open {
    fn new() -> Result<Open, String> {
        for _ in 0..10 {
            // SAFETY: no window is named; the clipboard is closed again on drop.
            if unsafe { OpenClipboard(null_mut()) } != 0 {
                return Ok(Open);
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        Err("Another app is using the clipboard. Try again.".into())
    }
}

impl Drop for Open {
    fn drop(&mut self) {
        // SAFETY: this thread opened the clipboard in Open::new.
        unsafe { CloseClipboard() };
    }
}

// Puts the types on the clipboard in their order, in place of what was there.
pub fn write(types: &[(&str, Vec<u8>)]) -> Result<(), String> {
    let fail = || "Octet cannot copy this.".to_string();
    let formats: Vec<u32> = types.iter().map(|(n, _)| format(n)).collect();
    if formats.contains(&0) {
        return Err(fail());
    }
    let _open = Open::new()?;
    // SAFETY: the clipboard is open on this thread.
    if unsafe { EmptyClipboard() } == 0 {
        return Err(fail());
    }
    for ((_, bytes), f) in types.iter().zip(formats) {
        // A metafile goes on as a metafile handle, made from its bytes; the clipboard owns it after SetClipboardData.
        if f == u32::from(CF_ENHMETAFILE) {
            // SAFETY: `bytes` lives for the call and GDI copies it; the handle is deleted here if the clipboard refuses it.
            unsafe {
                let h = SetEnhMetaFileBits(bytes.len() as u32, bytes.as_ptr());
                if h.is_null() {
                    return Err(fail());
                }
                if SetClipboardData(f, h).is_null() {
                    DeleteEnhMetaFile(h);
                    return Err(fail());
                }
            }
            continue;
        }
        // SAFETY: the memory is allocated with the size of `bytes`, written while locked, and given to the clipboard,
        // which owns it after SetClipboardData succeeds. If that fails, it is freed here.
        unsafe {
            let h = GlobalAlloc(GMEM_MOVEABLE, bytes.len().max(1));
            if h.is_null() {
                return Err(fail());
            }
            let p = GlobalLock(h).cast::<u8>();
            if p.is_null() {
                GlobalFree(h);
                return Err(fail());
            }
            copy_nonoverlapping(bytes.as_ptr(), p, bytes.len());
            GlobalUnlock(h);
            if SetClipboardData(f, h).is_null() {
                GlobalFree(h);
                return Err(fail());
            }
        }
    }
    Ok(())
}

// The bytes of each named format on the clipboard (64 MB at most), read only if the clipboard has that format.
// Also whether the clipboard holds any format at all.
pub fn read(names: &[&'static str]) -> Result<(Vec<(&'static str, Vec<u8>)>, bool), String> {
    let _open = Open::new()?;
    // SAFETY: the clipboard is open on this thread.
    let any = unsafe { CountClipboardFormats() } > 0;
    Ok((names.iter().filter_map(|n| one(format(n)).map(|b| (*n, b))).collect(), any))
}

fn one(f: u32) -> Option<Vec<u8>> {
    // SAFETY: the clipboard is open on this thread (read). The handle belongs to the clipboard; it is only locked,
    // copied from for at most its own size, and unlocked.
    unsafe {
        if f == 0 || IsClipboardFormatAvailable(f) == 0 {
            return None;
        }
        let h = GetClipboardData(f);
        if h.is_null() {
            return None;
        }
        // A metafile handle: its bytes come from GDI, at most 64 MB.
        if f == u32::from(CF_ENHMETAFILE) {
            let n = GetEnhMetaFileBits(h, 0, std::ptr::null_mut()) as usize;
            if n == 0 || n > MAX_TYPE {
                return None;
            }
            let mut out = vec![0u8; n];
            return (GetEnhMetaFileBits(h, n as u32, out.as_mut_ptr()) as usize == n).then_some(out);
        }
        let n = GlobalSize(h);
        if n == 0 || n > MAX_TYPE {
            return None;
        }
        let p = GlobalLock(h).cast::<u8>();
        if p.is_null() {
            return None;
        }
        let mut out = vec![0u8; n];
        copy_nonoverlapping(p, out.as_mut_ptr(), n);
        GlobalUnlock(h);
        Some(out)
    }
}
