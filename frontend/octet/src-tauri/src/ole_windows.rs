// The COM server for Octet Drawing objects (decision 0023), on Windows only. ole.rs has the data it uses (the class,
// the keys, the limits) and its tests.
//
// What runs where:
// - Every COM object lives on the main thread, the thread of tao's window loop. That thread is a single-threaded
//   apartment: tao calls OleInitialize when it makes a window, and start() calls it too before it registers (it gives
//   S_FALSE when OLE is already on). tao's GetMessage/DispatchMessage loop dispatches COM's calls into Octet.
//   https://learn.microsoft.com/windows/win32/com/single-threaded-apartments
// - Tauri's commands run on the async runtime's threads. They reach the main thread through run_on_main_thread
//   (on_main) and wait there for the answer. No COM pointer is used on any other thread.
// - No incoming call makes a window or waits for the page: making a window on the main thread in a call that waits
//   hangs Octet on Windows (windows.rs). DoVerb records what to open and starts the window from the async runtime.
// - No RefCell borrow is held across a call out to Word: Word calls back into Octet during SaveObject and
//   SendOnDataChange (Save, GetData), on this same thread.
//
// Every `unsafe` block is a call across the COM or Win32 boundary, with a SAFETY line. No unsafe code reads an
// object's contents: the bytes go to ole::read_stream, which is safe Rust.
#![allow(non_snake_case)] // the COM interfaces' method names

use std::cell::{Cell, RefCell};
use std::collections::HashMap;
use std::mem::ManuallyDrop;
use std::path::Path;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};
use std::sync::OnceLock;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Emitter, Manager};
use windows::Win32::Foundation::{
    CLASS_E_NOAGGREGATION, CO_E_OBJNOTCONNECTED, DATA_S_SAMEFORMATETC, DV_E_DVASPECT, DV_E_FORMATETC, DV_E_LINDEX, DV_E_TYMED, E_FAIL, E_INVALIDARG, E_NOTIMPL, E_POINTER, ERROR_SUCCESS,
    CloseHandle, GlobalFree, HANDLE, HGLOBAL, HWND, WAIT_OBJECT_0, OLEOBJ_S_INVALIDVERB, OLE_E_ADVISENOTSUPPORTED, OLE_E_BLANK, RECT, RPC_E_DISCONNECTED, RPC_E_SERVER_DIED,
    RPC_E_SERVER_DIED_DNE, SIZE, S_FALSE, S_OK, STG_E_DOCFILECORRUPT,
};
use windows::Win32::Graphics::Gdi::{DeleteEnhMetaFile, GetDC, GetWinMetaFileBits, ReleaseDC, SetEnhMetaFileBits, SetMetaFileBitsEx, HENHMETAFILE, LOGPALETTE, MM_ANISOTROPIC};
use windows::Win32::Media::Audio::{CoRegisterMessageFilter, IMessageFilter, IMessageFilter_Impl};
use windows::Win32::Media::HTASK;
use windows::Win32::System::Com::StructuredStorage::{
    CreateILockBytesOnHGlobal, IPersistStorage, IPersistStorage_Impl, IStorage, ReadClassStg, StgCreateDocfileOnILockBytes, StgOpenStorageOnILockBytes, WriteClassStg,
    WriteFmtUserTypeStg,
};
use windows::Win32::System::Com::{
    CoCreateInstance, CoDisconnectObject, CoInitializeEx, IGlobalInterfaceTable, CLSCTX_INPROC_SERVER, CoLockObjectExternal, CoRegisterClassObject, CoRevokeClassObject, CoUninitialize, CreateDataAdviseHolder, IAdviseSink,
    IClassFactory, IClassFactory_Impl, IDataAdviseHolder, IDataObject, IDataObject_Impl, IEnumFORMATETC, IEnumFORMATETC_Impl, IEnumSTATDATA, IMoniker, IPersistFile, IPersistFile_Impl,
    IPersist_Impl, CLSCTX_LOCAL_SERVER, COINIT_MULTITHREADED, DATADIR_GET, DVASPECT, DVASPECT_CONTENT, FORMATETC, INTERFACEINFO, PENDINGMSG_WAITDEFPROCESS, REGCLS_MULTIPLEUSE,
    SERVERCALL_ISHANDLED, SERVERCALL_RETRYLATER, STATFLAG_NONAME, STATSTG, STGC_DEFAULT, STGM, STGM_CREATE, STGM_READ, STGM_READWRITE, STGM_SHARE_EXCLUSIVE, STGM_WRITE, STGMEDIUM,
    STGMEDIUM_0, TYMED_ENHMF, TYMED_HGLOBAL, TYMED_ISTORAGE, TYMED_MFPICT,
};
use windows::Win32::System::DataExchange::{RegisterClipboardFormatW, METAFILEPICT};
use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GMEM_MOVEABLE};
use windows::Win32::System::Rpc::I_RpcBindingInqLocalClientPID;
use windows::Win32::System::Threading::{OpenProcess, WaitForSingleObject, PROCESS_SYNCHRONIZE};
use windows::Win32::System::Ole::{
    CreateOleAdviseHolder, IEnumOLEVERB, IOleWindow, IOleAdviseHolder, IOleClientSite, IOleObject, IOleObject_Impl, OleFlushClipboard, OleInitialize, OleRegEnumVerbs,
    OleRegGetMiscStatus, OleRegGetUserType, OleSetClipboard, CF_ENHMETAFILE, CF_METAFILEPICT, OLECLOSE, OLECLOSE_NOSAVE, OLEGETMONIKER, OLEMISC, OLEWHICHMK,
    USERCLASSTYPE,
};
use windows::Win32::System::Registry::{
    RegCloseKey, RegCreateKeyExW, RegDeleteTreeW, RegGetValueW, RegSetValueExW, HKEY, HKEY_CURRENT_USER, KEY_SET_VALUE, KEY_WOW64_32KEY, KEY_WOW64_64KEY, REG_OPTION_NON_VOLATILE,
    REG_SAM_FLAGS, REG_SZ, RRF_RT_REG_SZ, RRF_SUBKEY_WOW6432KEY, RRF_SUBKEY_WOW6464KEY,
};
use windows::Win32::UI::WindowsAndMessaging::MSG;
use windows_core::{implement, Error, IUnknown, IUnknownImpl, Interface, Ref, Result, BOOL, GUID, HRESULT, PCWSTR, PWSTR};

use super::{Refused, CANNOT_OPEN};
use crate::objects::{label, Session, Taken};

pub const CLASS: GUID = GUID::from_values(super::CLSID_FIELDS.0, super::CLSID_FIELDS.1, super::CLSID_FIELDS.2, super::CLSID_FIELDS.3);

static APP: OnceLock<AppHandle> = OnceLock::new();
// Started by COM (-Embedding): Octet ends when Word lets go of its last object and no window of Octet's is open.
static EMBEDDING: AtomicBool = AtomicBool::new(false);
// Started by COM, and Word's first object has not come yet: only the check after a minute (start) ends Octet then.
static WAITING: AtomicBool = AtomicBool::new(false);
// The objects alive, and IClassFactory::LockServer's locks: while either is above 0, an embedding Octet stays.
// Octet keeps its own counts and does not use CoAddRefServerProcess: at 0, that suspends the class object, and an
// Octet the user also works in would then make Word start a second Octet.
// https://learn.microsoft.com/windows/win32/api/combaseapi/nf-combaseapi-coreleaseserverprocess
static LIVE: AtomicUsize = AtomicUsize::new(0);
static LOCKS: AtomicUsize = AtomicUsize::new(0);
// The objects whose Word watch_site asks from a thread of its own.
static WATCHED: std::sync::Mutex<std::collections::BTreeSet<u64>> = std::sync::Mutex::new(std::collections::BTreeSet::new());
// CLSID_StdGlobalInterfaceTable, which the windows crate does not name.
const STD_GIT: GUID = GUID::from_u128(0x00000323_0000_0000_C000_000000000046);

thread_local! {
    // The main thread's state. The objects with a window open are held here (a strong reference), with
    // CoLockObjectExternal, so the user's window keeps its object until the window closes.
    // https://learn.microsoft.com/windows/win32/api/combaseapi/nf-combaseapi-colockobjectexternal
    static OPEN: RefCell<HashMap<u64, windows_core::ComObject<Drawing>>> = RefCell::new(HashMap::new());
    static COOKIE: Cell<Option<u32>> = const { Cell::new(None) };
    // While the user waits for Word (Update, Close), a call Word turns down because it shows a dialog is tried again
    // for 10 seconds. Other calls are not.
    static RETRY: Cell<bool> = const { Cell::new(false) };
    static LAST_CLIP: RefCell<Option<IDataObject>> = const { RefCell::new(None) };
    // Objects to cut off from Word once the call in progress has returned (Drawing::disconnect).
    static LATER: RefCell<Vec<(IUnknown, bool)>> = const { RefCell::new(Vec::new()) };
}

fn app() -> Option<&'static AppHandle> {
    APP.get()
}

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain([0]).collect()
}

fn fail(h: HRESULT) -> Error {
    Error::from_hresult(h)
}

// The calls that fail because Word (or the process that held the object) is gone.
fn container_gone(e: &Error) -> bool {
    const RPC_S_SERVER_UNAVAILABLE: HRESULT = HRESULT(0x8007_06BA_u32 as i32);
    const RPC_S_CALL_FAILED: HRESULT = HRESULT(0x8007_06BE_u32 as i32);
    [RPC_E_DISCONNECTED, RPC_E_SERVER_DIED, RPC_E_SERVER_DIED_DNE, CO_E_OBJNOTCONNECTED, RPC_S_SERVER_UNAVAILABLE, RPC_S_CALL_FAILED].contains(&e.code())
}

// The format number Windows gives a name (the same in every program).
fn registered(name: &str) -> u16 {
    let w = wide(name);
    // SAFETY: `w` is a NUL-terminated UTF-16 string that lives for the call.
    unsafe { RegisterClipboardFormatW(PCWSTR(w.as_ptr())) as u16 }
}

// ---------------------------------------------------------------------------------------------------------------
// Start and end

// At start, on the main thread, before any window is shown. Release builds write the keys again when they are
// missing or name a program that is gone (ole::repair). The class object goes up in release builds, and in a debug
// build only when COM started it: a debug build the user starts never takes over Word's objects.
pub fn start(app: &AppHandle, embedding: bool) {
    let _ = APP.set(app.clone());
    EMBEDDING.store(embedding, SeqCst);
    // SAFETY: called on the main thread once; OLE stays on for the life of the process.
    if let Err(e) = unsafe { OleInitialize(None) } {
        log(&format!("OLE did not start ({e}). Octet Drawing objects are off."));
        return;
    }
    if !cfg!(debug_assertions) {
        repair();
    }
    if cfg!(debug_assertions) && !embedding {
        return;
    }
    let factory: IClassFactory = Factory.into();
    // SAFETY: CLASS lives for the call; the factory is AddRef'd by COM and kept until CoRevokeClassObject. REGCLS_MULTIPLEUSE:
    // one Octet serves every object, and Word's activations go to it while it runs.
    // https://learn.microsoft.com/windows/win32/api/combaseapi/nf-combaseapi-coregisterclassobject
    match unsafe { CoRegisterClassObject(&CLASS, &factory, CLSCTX_LOCAL_SERVER, REGCLS_MULTIPLEUSE) } {
        Ok(cookie) => COOKIE.with(|c| c.set(Some(cookie))),
        Err(e) => {
            log(&format!("Octet cannot offer Octet Drawing objects ({e})."));
            return;
        }
    }
    WAITING.store(embedding, SeqCst);
    let filter: IMessageFilter = Filter.into();
    // SAFETY: on the main thread, which is an STA; COM keeps the filter until it is replaced or OLE ends.
    // https://learn.microsoft.com/windows/win32/api/objidl/nn-objidl-imessagefilter
    let _ = unsafe { CoRegisterMessageFilter(&filter, None) };
    // Word gone: a check every 2 seconds while an object window is open. A started Octet that no object ever came
    // to ends after a minute.
    let app = app.clone();
    std::thread::spawn(move || {
        let started = Instant::now();
        loop {
            std::thread::sleep(Duration::from_secs(2));
            let first = started.elapsed() > Duration::from_secs(60);
            let a = app.clone();
            let checked = app.run_on_main_thread(move || {
                ping();
                if first {
                    WAITING.store(false, SeqCst);
                    maybe_exit(&a);
                }
            });
            if checked.is_err() {
                break;
            }
        }
    });
}

// When Octet ends (RunEvent::Exit, on the main thread): each open object sends Word its newest drawing and tells Word
// it closed, the class object goes, and a copy Octet still holds on the clipboard is rendered so it stays after Octet.
pub fn shutdown() {
    let open: Vec<_> = OPEN.with(|m| m.borrow_mut().drain().map(|(_, o)| o).collect());
    for o in open {
        Drawing::flush(&o);
        o.closed_notices();
        Drawing::disconnect(&o);
    }
    // The loop is ending, so what disconnect posted may never run: now, as no call from Word is in progress.
    disconnect_later();
    revoke();
    // Copy flushes at once, so this only matters if a flush failed: OleFlushClipboard does nothing when Octet does
    // not own the clipboard.
    if LAST_CLIP.with(|c| c.borrow_mut().take()).is_some() {
        // SAFETY: an OLE call on the main thread, where OLE is on.
        let _ = unsafe { OleFlushClipboard() };
    }
}

fn revoke() {
    if let Some(cookie) = COOKIE.with(|c| c.take()) {
        // SAFETY: the cookie is the one CoRegisterClassObject gave.
        let _ = unsafe { CoRevokeClassObject(cookie) };
    }
}

// An Octet that COM started ends when no object is alive and no window of Octet's shows: Home hidden, no drawing or
// object window. The class object goes first, so a new activation starts a new Octet. One thread (the STA), so no
// activation can come in between. Not before Word's first object (WAITING): Home's hidden page says it is empty as
// soon as it loads, which can be before Word's first call, and Octet then ended while Word waited for it (issue 24).
pub fn maybe_exit(app: &AppHandle) {
    if !EMBEDDING.load(SeqCst) || WAITING.load(SeqCst) || LIVE.load(SeqCst) > 0 || LOCKS.load(SeqCst) > 0 || OPEN.with(|m| !m.borrow().is_empty()) {
        return;
    }
    let shown = app.webview_windows().iter().any(|(l, w)| (l.starts_with("draw-") || l.starts_with("object-")) || (l == "main" && w.is_visible().unwrap_or(false)));
    if shown {
        return;
    }
    revoke();
    app.exit(0);
}

// Runs `f` on the main thread after the call in progress has returned. run_on_main_thread runs `f` at once when it is
// called on the main thread (tauri-runtime-wry's send_user_message), so it is posted from another thread instead.
fn later(f: impl FnOnce(&AppHandle) + Send + 'static) {
    if let Some(a) = app().cloned() {
        std::thread::spawn(move || {
            let b = a.clone();
            let _ = a.run_on_main_thread(move || f(&b));
        });
    }
}

fn log(text: &str) {
    if let Some(app) = app() {
        let _ = crate::crashlog::log_error(app.clone(), format!("Office objects: {text}"), false);
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The registry: HKEY_CURRENT_USER\Software\Classes only, in both views. Windows keeps a 32-bit copy of
// Software\Classes\CLSID (Wow6432Node) for 32-bit programs, so 32-bit Office (still common, and every older Office)
// reads the class there, and 64-bit Office reads the 64-bit one. Octet writes and removes both.
// https://learn.microsoft.com/windows/win32/winprog64/shared-registry-keys
// https://learn.microsoft.com/windows/win32/winprog64/accessing-an-alternate-registry-view
const VIEWS: [REG_SAM_FLAGS; 2] = [KEY_WOW64_64KEY, KEY_WOW64_32KEY];

fn reg_set(view: REG_SAM_FLAGS, key: &str, name: &str, value: Option<&str>) -> bool {
    let path = wide(&format!("Software\\Classes\\{key}"));
    let mut hk = HKEY::default();
    // SAFETY: `path` lives for the call; `hk` is closed below.
    let made = unsafe { RegCreateKeyExW(HKEY_CURRENT_USER, PCWSTR(path.as_ptr()), None, PCWSTR::null(), REG_OPTION_NON_VOLATILE, KEY_SET_VALUE | view, None, &mut hk, None) };
    if made != ERROR_SUCCESS {
        return false;
    }
    let ok = match value {
        None => true,
        Some(v) => {
            let n = wide(name);
            let data: Vec<u8> = wide(v).iter().flat_map(|u| u.to_le_bytes()).collect();
            let name = if name.is_empty() { PCWSTR::null() } else { PCWSTR(n.as_ptr()) };
            // SAFETY: `hk` is open; the name and data live for the call; REG_SZ data ends with a NUL.
            unsafe { RegSetValueExW(hk, name, None, REG_SZ, Some(&data)) == ERROR_SUCCESS }
        }
    };
    // SAFETY: `hk` was opened above.
    let _ = unsafe { RegCloseKey(hk) };
    ok
}

fn reg_get(view: REG_SAM_FLAGS, key: &str) -> Option<String> {
    let path = wide(&format!("Software\\Classes\\{key}"));
    let mut buf = vec![0u16; 1024];
    let mut size = (buf.len() * 2) as u32;
    let flags = RRF_RT_REG_SZ | if view == KEY_WOW64_32KEY { RRF_SUBKEY_WOW6432KEY } else { RRF_SUBKEY_WOW6464KEY };
    // SAFETY: `buf` holds `size` bytes; RegGetValueW writes at most that and NUL-terminates REG_SZ.
    let got = unsafe { RegGetValueW(HKEY_CURRENT_USER, PCWSTR(path.as_ptr()), PCWSTR::null(), flags, None, Some(buf.as_mut_ptr().cast()), Some(&mut size)) };
    if got != ERROR_SUCCESS {
        return None;
    }
    let n = (size as usize / 2).min(buf.len());
    Some(String::from_utf16_lossy(&buf[..n]).trim_end_matches('\0').to_string())
}

// What LocalServer32 names now, for this user, in the 64-bit view (the one Octet's own checks use).
pub fn registered_server() -> Option<String> {
    reg_get(KEY_WOW64_64KEY, &format!("CLSID\\{}\\LocalServer32", super::CLSID))
}

// Writes every key for the program at `exe`, in both views. True if each one was written.
pub fn register(exe: &Path) -> bool {
    let keys = super::keys(exe);
    VIEWS.iter().flat_map(|v| keys.iter().map(move |e| reg_set(*v, &e.key, e.name, e.value.as_deref()))).fold(true, |a, b| a && b)
}

// Removes every key the class has, in both views (for tests; the uninstaller does the same). Each key is opened with
// its view, as RegDeleteTreeW takes no view of its own.
pub fn unregister() {
    use windows::Win32::System::Registry::{RegDeleteKeyExW, RegOpenKeyExW, KEY_ALL_ACCESS};
    for view in VIEWS {
        for r in super::roots() {
            let path = wide(&format!("Software\\Classes\\{r}"));
            let mut hk = HKEY::default();
            // SAFETY: `path` lives for the calls; the key is closed again.
            unsafe {
                if RegOpenKeyExW(HKEY_CURRENT_USER, PCWSTR(path.as_ptr()), None, KEY_ALL_ACCESS | view, &mut hk) == ERROR_SUCCESS {
                    let _ = RegDeleteTreeW(hk, PCWSTR::null());
                    let _ = RegCloseKey(hk);
                }
                let _ = RegDeleteKeyExW(HKEY_CURRENT_USER, PCWSTR(path.as_ptr()), view.0, None);
            }
        }
    }
}

// On a thread of its own, so start-up does not wait for the registry. Both views are written when the 64-bit view's
// server is missing, is this Octet, or names a program that is gone: an Octet updated from 1.1 or an installer that
// wrote one view gets the other at its first start.
fn repair() {
    std::thread::spawn(|| {
        let Ok(me) = std::env::current_exe() else { return };
        if super::repair(registered_server().as_deref(), &me, |p| p.is_file()) == super::Repair::Write && !register(&me) {
            log("Octet cannot write the keys for Octet Drawing objects.");
        }
    });
}

// Copy offers the object only when Word can open it: the class is registered for this user and names a program that
// is there. Otherwise Word would get an object nothing opens (decision 0023).
pub fn offered() -> bool {
    registered_server().and_then(|v| super::server_path(&v)).is_some_and(|p| p.is_file())
}

// ---------------------------------------------------------------------------------------------------------------
// Data: STGMEDIUMs and storages

fn hglobal(bytes: &[u8]) -> Result<HGLOBAL> {
    // SAFETY: the block is allocated with the bytes' size (at least 1), written while locked, and freed if locking
    // fails. The caller owns it after this.
    unsafe {
        let h = GlobalAlloc(GMEM_MOVEABLE, bytes.len().max(1))?;
        let p = GlobalLock(h).cast::<u8>();
        if p.is_null() {
            let _ = GlobalFree(Some(h));
            return Err(fail(E_FAIL));
        }
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), p, bytes.len());
        let _ = GlobalUnlock(h);
        Ok(h)
    }
}

fn medium(tymed: i32, u: STGMEDIUM_0) -> STGMEDIUM {
    STGMEDIUM { tymed: tymed as u32, u, pUnkForRelease: ManuallyDrop::new(None) }
}

fn medium_bytes(bytes: &[u8]) -> Result<STGMEDIUM> {
    Ok(medium(TYMED_HGLOBAL.0, STGMEDIUM_0 { hGlobal: hglobal(bytes)? }))
}

fn medium_emf(emf: &[u8]) -> Result<STGMEDIUM> {
    // SAFETY: GDI copies the bytes; the handle belongs to the caller (ReleaseStgMedium deletes it).
    let h = unsafe { SetEnhMetaFileBits(emf) };
    if h.is_invalid() {
        return Err(fail(DV_E_FORMATETC));
    }
    Ok(medium(TYMED_ENHMF.0, STGMEDIUM_0 { hEnhMetaFile: h }))
}

// CF_METAFILEPICT for a container that asks for a Windows metafile: the EMF converted by Windows (it keeps the whole
// EMF in the WMF's comment records, so the CDXML goes with it), with the size in HIMETRIC (MM_ANISOTROPIC).
// https://learn.microsoft.com/windows/win32/api/wingdi/nf-wingdi-getwinmetafilebits
// https://learn.microsoft.com/windows/win32/api/wingdi/ns-wingdi-metafilepict
fn medium_wmf(emf: &[u8]) -> Result<STGMEDIUM> {
    let (w, h) = super::extent(emf).ok_or_else(|| fail(DV_E_FORMATETC))?;
    // SAFETY: each GDI handle made here is deleted or given to the caller; the screen DC is released; the WMF bytes
    // are read into a buffer of the size GDI gave.
    unsafe {
        let hemf: HENHMETAFILE = SetEnhMetaFileBits(emf);
        if hemf.is_invalid() {
            return Err(fail(DV_E_FORMATETC));
        }
        let dc = GetDC(None);
        let n = GetWinMetaFileBits(hemf, None, MM_ANISOTROPIC.0, dc);
        let mut wmf = vec![0u8; n as usize];
        let got = if n > 0 { GetWinMetaFileBits(hemf, Some(&mut wmf), MM_ANISOTROPIC.0, dc) } else { 0 };
        ReleaseDC(None, dc);
        let _ = DeleteEnhMetaFile(Some(hemf));
        if got == 0 {
            return Err(fail(DV_E_FORMATETC));
        }
        let hmf = SetMetaFileBitsEx(&wmf);
        if hmf.is_invalid() {
            return Err(fail(DV_E_FORMATETC));
        }
        let pict = METAFILEPICT { mm: MM_ANISOTROPIC.0, xExt: w, yExt: h, hMF: hmf };
        let bytes = std::slice::from_raw_parts((&pict as *const METAFILEPICT).cast::<u8>(), std::mem::size_of::<METAFILEPICT>());
        let g = hglobal(bytes)?;
        Ok(medium(TYMED_MFPICT.0, STGMEDIUM_0 { hMetaFilePict: g.0 }))
    }
}

// The object's storage as Octet writes it: the class, the name ("Octet Drawing"), the stream Octet with the drawing,
// and the stream OctetSize with the picture's size. Nothing else: the picture streams are the default handler's.
// https://learn.microsoft.com/windows/win32/api/coml2api/nf-coml2api-writeclassstg
// https://learn.microsoft.com/windows/win32/api/ole2/nf-ole2-writefmtusertypestg
fn write_storage(stg: &IStorage, oct: &str, size: (i32, i32)) -> Result<()> {
    let name = wide(super::NAME);
    let stream = wide(super::STREAM);
    let size_stream = wide(super::SIZE_STREAM);
    let size = super::size_bytes(if super::valid_extent(size) { size } else { super::BLANK_EXTENT });
    // SAFETY: COM calls on a live storage; the strings and the bytes live for each call.
    unsafe {
        WriteClassStg(stg, &CLASS)?;
        WriteFmtUserTypeStg(stg, registered(super::NAME), PCWSTR(name.as_ptr()))?;
        let s = stg.CreateStream(PCWSTR(stream.as_ptr()), STGM_CREATE | STGM_WRITE | STGM_SHARE_EXCLUSIVE, 0, 0)?;
        let bytes = oct.as_bytes();
        let len = u32::try_from(bytes.len()).map_err(|_| fail(E_INVALIDARG))?;
        let mut written = 0u32;
        s.Write(bytes.as_ptr().cast(), len, Some(&mut written)).ok()?;
        if written != len {
            return Err(fail(E_FAIL));
        }
        let s = stg.CreateStream(PCWSTR(size_stream.as_ptr()), STGM_CREATE | STGM_WRITE | STGM_SHARE_EXCLUSIVE, 0, 0)?;
        let mut written = 0u32;
        s.Write(size.as_ptr().cast(), size.len() as u32, Some(&mut written)).ok()?;
        if written as usize != size.len() {
            return Err(fail(E_FAIL));
        }
    }
    Ok(())
}

// The size stream's bytes, if the storage has it and it is exactly 8 bytes long (ole::read_size checks the values).
// Opened by name only, like the drawing's stream.
fn read_size_stream(stg: &IStorage) -> Option<[u8; 8]> {
    let name = wide(super::SIZE_STREAM);
    // SAFETY: COM calls on a live storage and stream; Read writes at most 8 bytes into an 8-byte buffer.
    unsafe {
        let s = stg.OpenStream(PCWSTR(name.as_ptr()), None, STGM_READ | STGM_SHARE_EXCLUSIVE, 0).ok()?;
        let mut stat = STATSTG::default();
        s.Stat(&mut stat, STATFLAG_NONAME).ok()?;
        if stat.cbSize != 8 {
            return None;
        }
        let mut buf = [0u8; 8];
        let mut n = 0u32;
        s.Read(buf.as_mut_ptr().cast(), 8, Some(&mut n)).ok().ok()?;
        (n == 8).then_some(buf)
    }
}

// The drawing from an object's storage, with ole::read_stream's limits. Only the stream Octet is opened, by name; the
// storage is never listed and no storage inside it is opened.
fn read_storage(stg: &IStorage) -> std::result::Result<String, Refused> {
    let stream = wide(super::STREAM);
    // SAFETY: COM calls on a live storage and stream. Read writes at most `buf.len()` bytes into `buf` and says how
    // many in `n`; read_stream never trusts `n` past the buffer.
    unsafe {
        if ReadClassStg(stg).map_err(|_| Refused::WrongClass)? != CLASS {
            return Err(Refused::WrongClass);
        }
        let s = stg.OpenStream(PCWSTR(stream.as_ptr()), None, STGM_READ | STGM_SHARE_EXCLUSIVE, 0).map_err(|_| Refused::NoStream)?;
        let mut stat = STATSTG::default();
        s.Stat(&mut stat, STATFLAG_NONAME).map_err(|_| Refused::Failed)?;
        super::read_stream(stat.cbSize, |buf| {
            let mut n = 0u32;
            let len = u32::try_from(buf.len()).unwrap_or(u32::MAX);
            if s.Read(buf.as_mut_ptr().cast(), len, Some(&mut n)).is_err() {
                return Err(());
            }
            Ok(n as usize)
        })
    }
}

// A storage in memory with the drawing in it, for "Embed Source" asked for as TYMED_ISTORAGE.
fn storage_in_memory(oct: &str, size: (i32, i32)) -> Result<IStorage> {
    // SAFETY: the lock bytes free their memory when released (fDeleteOnRelease); the storage holds them.
    unsafe {
        let bytes = CreateILockBytesOnHGlobal(None, true)?;
        let stg = StgCreateDocfileOnILockBytes(&bytes, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0)?;
        write_storage(&stg, oct, size)?;
        stg.Commit(STGC_DEFAULT.0 as u32)?;
        Ok(stg)
    }
}

// Paste: Octet's own drawing from an "Embed Source" copied out of Word (a compound file flattened into memory, as the
// Windows clipboard gives it). Windows (ole32) reads the compound file; Octet opens only its stream, with the limits.
// None for another program's object, or anything that is not sound. Runs on a thread of its own with COM on.
pub fn oct_from_embed_source(flat: &[u8]) -> Option<String> {
    if flat.is_empty() || flat.len() as u64 > super::MAX_STREAM {
        return None;
    }
    let flat = flat.to_vec();
    std::thread::spawn(move || {
        // SAFETY: COM is started and ended on this thread. The memory block is a copy of the bytes, given to the lock
        // bytes, which free it on release. The storage is opened read-only.
        unsafe {
            if CoInitializeEx(None, COINIT_MULTITHREADED).is_err() {
                return None;
            }
            let out = (|| {
                let h = hglobal(&flat).ok()?;
                let bytes = CreateILockBytesOnHGlobal(Some(h), true).ok()?;
                let stg = StgOpenStorageOnILockBytes(&bytes, None, STGM_READ | STGM_SHARE_EXCLUSIVE, None, None).ok()?;
                read_storage(&stg).ok().filter(|t| !t.is_empty())
            })();
            CoUninitialize();
            out
        }
    })
    .join()
    .ok()
    .flatten()
}

// What each data object can give, and checks on a FORMATETC.
fn formatetc(cf: u16, tymed: i32) -> FORMATETC {
    FORMATETC { cfFormat: cf, ptd: std::ptr::null_mut(), dwAspect: DVASPECT_CONTENT.0, lindex: -1, tymed: tymed as u32 }
}

fn check(asked: *const FORMATETC, offered: &[FORMATETC]) -> Result<FORMATETC> {
    if asked.is_null() {
        return Err(fail(E_INVALIDARG));
    }
    // SAFETY: the caller's FORMATETC, checked non-null, read once.
    let a = unsafe { *asked };
    let same: Vec<&FORMATETC> = offered.iter().filter(|f| f.cfFormat == a.cfFormat).collect();
    if same.is_empty() {
        return Err(fail(DV_E_FORMATETC));
    }
    if a.dwAspect != DVASPECT_CONTENT.0 {
        return Err(fail(DV_E_DVASPECT));
    }
    if a.lindex != -1 {
        return Err(fail(DV_E_LINDEX));
    }
    same.into_iter().find(|f| f.tymed & a.tymed != 0).copied().ok_or_else(|| fail(DV_E_TYMED))
}

// The list of formats, for EnumFormatEtc.
#[implement(IEnumFORMATETC, Agile = false)]
struct Formats {
    list: Vec<FORMATETC>,
    at: Cell<usize>,
}

impl IEnumFORMATETC_Impl for Formats_Impl {
    fn Next(&self, celt: u32, rgelt: *mut FORMATETC, fetched: *mut u32) -> HRESULT {
        if rgelt.is_null() {
            return E_POINTER;
        }
        let at = self.at.get();
        let n = (celt as usize).min(self.list.len().saturating_sub(at));
        // SAFETY: the caller gives room for `celt` FORMATETCs at `rgelt`; at most `n` <= celt are written. `fetched`
        // may be null (allowed when celt is 1).
        unsafe {
            for (k, f) in self.list[at..at + n].iter().enumerate() {
                rgelt.add(k).write(*f);
            }
            if !fetched.is_null() {
                *fetched = n as u32;
            }
        }
        self.at.set(at + n);
        if n == celt as usize { S_OK } else { S_FALSE }
    }
    fn Skip(&self, celt: u32) -> Result<()> {
        let to = self.at.get() + celt as usize;
        self.at.set(to.min(self.list.len()));
        if to <= self.list.len() { Ok(()) } else { Err(fail(S_FALSE)) }
    }
    fn Reset(&self) -> Result<()> {
        self.at.set(0);
        Ok(())
    }
    fn Clone(&self) -> Result<IEnumFORMATETC> {
        Ok(Formats { list: self.list.clone(), at: Cell::new(self.at.get()) }.into())
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The class factory

// Agile = false on every object Word calls: the windows crate makes an object agile by default (free-threaded), and
// COM then runs Word's calls on its own worker threads. Not agile, they come to the main thread, an STA, where OPEN,
// LATER and the windows are.
#[implement(IClassFactory, Agile = false)]
struct Factory;

impl IClassFactory_Impl for Factory_Impl {
    // https://learn.microsoft.com/windows/win32/api/unknwn/nf-unknwn-iclassfactory-createinstance
    fn CreateInstance(&self, outer: Ref<IUnknown>, riid: *const GUID, ppv: *mut *mut core::ffi::c_void) -> Result<()> {
        if ppv.is_null() {
            return Err(fail(E_POINTER));
        }
        // SAFETY: `ppv` is the caller's out pointer, checked non-null.
        unsafe { *ppv = std::ptr::null_mut() };
        if !outer.is_null() {
            return Err(fail(CLASS_E_NOAGGREGATION));
        }
        let unknown: IUnknown = Drawing::new().into();
        // SAFETY: QueryInterface on a live object with the caller's IID and out pointer.
        unsafe { unknown.query(riid, ppv).ok() }
    }
    fn LockServer(&self, lock: BOOL) -> Result<()> {
        if lock.as_bool() {
            LOCKS.fetch_add(1, SeqCst);
        } else if LOCKS.try_update(SeqCst, SeqCst, |n| n.checked_sub(1)) == Ok(1) {
            later(maybe_exit);
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The message filter: Word turns a call down while it shows a dialog (SERVERCALL_RETRYLATER). Update and Close try
// again every quarter second for 10 seconds; other calls give up at once.
// https://learn.microsoft.com/windows/win32/api/objidl/nf-objidl-imessagefilter-retryrejectedcall

#[implement(IMessageFilter)]
struct Filter;

impl IMessageFilter_Impl for Filter_Impl {
    fn HandleInComingCall(&self, _calltype: u32, _caller: HTASK, _tick: u32, _info: *const INTERFACEINFO) -> u32 {
        SERVERCALL_ISHANDLED.0 as u32
    }
    fn RetryRejectedCall(&self, _callee: HTASK, tick: u32, reject: u32) -> u32 {
        if reject == SERVERCALL_RETRYLATER.0 as u32 && RETRY.with(Cell::get) && tick < 10_000 { 250 } else { u32::MAX }
    }
    fn MessagePending(&self, _callee: HTASK, _tick: u32, _kind: u32) -> u32 {
        PENDINGMSG_WAITDEFPROCESS.0 as u32
    }
}

// Calls out to Word made while the user waits.
fn waiting<T>(f: impl FnOnce() -> T) -> T {
    let was = RETRY.with(|r| r.replace(true));
    let out = f();
    RETRY.with(|r| r.set(was));
    out
}

// ---------------------------------------------------------------------------------------------------------------
// The object

// One Octet Drawing object. Word's default handler holds it while it runs; OPEN holds it while its window is open.
// Methods run on the main thread only (an STA, as the object is not agile), so plain Cells and RefCells are enough.
#[implement(IOleObject, IDataObject, IPersistStorage, IPersistFile, Agile = false)]
struct Drawing {
    // The object window's session (objects.rs): its number, the document's name, the drawing Word has (empty for a
    // new object nothing was drawn in), the window's newest drawing and picture not sent to Word yet, the number of
    // the page's newest message, whether Word's Close is in progress, and whether Word went away while the window was
    // open. Read as the object's own fields (Deref).
    session: Session,
    site: RefCell<Option<IOleClientSite>>,
    advise: RefCell<Option<IOleAdviseHolder>>,
    data_advise: RefCell<Option<IDataAdviseHolder>>,
    // Held between Load or InitNew and HandsOffStorage, as IPersistStorage asks.
    storage: RefCell<Option<IStorage>>,
    emf: RefCell<Option<Vec<u8>>>, // the picture from the last update; None until there is one
    dirty: Cell<bool>,            // changed since Word last saved the storage
    // The picture's size in HIMETRIC: from the storage at Load (or the drawing's own size), 1 in square for a new
    // object, and the EMF's frame from each picture the window sends. GetExtent gives it from Load on.
    extent: Cell<(i32, i32)>,
    // The size Word asked for (SetExtent), until the drawing changes. Word scales the picture to it.
    asked: Cell<Option<(i32, i32)>>,
    shown: Cell<bool>,            // its window is open
    locked: Cell<bool>,           // CoLockObjectExternal held for the window
    // Word's process (from the call that opened the window), to see that it ended without asking Word anything.
    container: Cell<Option<HANDLE>>,
}

impl std::ops::Deref for Drawing {
    type Target = Session;
    fn deref(&self) -> &Session {
        &self.session
    }
}

impl Drawing {
    fn new() -> Self {
        LIVE.fetch_add(1, SeqCst);
        WAITING.store(false, SeqCst);
        Drawing {
            session: Session::new("Document", String::new()),
            site: RefCell::new(None),
            advise: RefCell::new(None),
            data_advise: RefCell::new(None),
            storage: RefCell::new(None),
            emf: RefCell::new(None),
            dirty: Cell::new(false),
            extent: Cell::new(super::BLANK_EXTENT),
            asked: Cell::new(None),
            shown: Cell::new(false),
            locked: Cell::new(false),
            container: Cell::new(None),
        }
    }

    // Word's process, kept with SYNCHRONIZE only, so ping can see that Word ended without asking Word anything. In
    // order: the owner of the window DoVerb names (the document's window), the window of Word's site (IOleWindow,
    // which Word's sites have), the caller of the call in progress. If none gives it, watch_site asks Word from a
    // thread of its own.
    // https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-iolewindow-getwindow
    // https://learn.microsoft.com/windows/win32/api/rpcdcep/nf-rpcdcep-i_rpcbindinginqlocalclientpid
    fn note_caller(&self, parent: HWND) {
        if self.container.get().is_some() || WATCHED.lock().unwrap().contains(&self.id) {
            return;
        }
        let owner = |w: HWND| {
            let mut pid = 0u32;
            if !w.is_invalid() {
                // SAFETY: reads the owner of a window handle; an invalid one gives 0.
                unsafe { windows::Win32::UI::WindowsAndMessaging::GetWindowThreadProcessId(w, Some(&mut pid)) };
            }
            pid
        };
        let mut pid = owner(parent);
        if pid == 0 {
            let site = self.site.borrow().clone();
            if let Some(w) = site.and_then(|s| s.cast::<IOleWindow>().ok()) {
                // SAFETY: a call to Word's live site, made while Word calls Octet (DoVerb), so Word is there to answer.
                pid = unsafe { w.GetWindow() }.map_or(0, owner);
            }
        }
        // SAFETY: asks RPC for the caller of the call in progress on this thread.
        if pid == 0 && unsafe { I_RpcBindingInqLocalClientPID(std::ptr::null_mut(), &mut pid) }.0 != 0 {
            pid = 0;
        }
        if pid != 0 && pid != std::process::id() {
            // SAFETY: opens a handle that only waits on the process; it is closed on drop.
            if let Ok(h) = unsafe { OpenProcess(PROCESS_SYNCHRONIZE, false, pid) } {
                self.container.set(Some(h));
                return;
            }
        }
        self.watch_site();
    }

    // When Octet cannot learn Word's process: a thread of its own asks Word's site every 2 seconds whether Word is
    // there. The site goes to that thread through the global interface table. A hung Word stops only that thread,
    // never Octet's windows. The thread ends when the window closes or Word is gone.
    // https://learn.microsoft.com/windows/win32/api/objidl/nn-objidl-iglobalinterfacetable
    fn watch_site(&self) {
        let Some(site) = self.site.borrow().clone() else { return };
        // SAFETY: COM calls on the main thread, where COM is on; the cookie is revoked by the thread below.
        let cookie = unsafe {
            let Ok(git) = CoCreateInstance::<_, IGlobalInterfaceTable>(&STD_GIT, None, CLSCTX_INPROC_SERVER) else { return };
            match git.RegisterInterfaceInGlobal(&site, &IOleClientSite::IID) {
                Ok(c) => c,
                Err(_) => return,
            }
        };
        let id = self.id;
        WATCHED.lock().unwrap().insert(id);
        std::thread::spawn(move || {
            // SAFETY: this thread's own COM, in the multithreaded apartment, ended below; the interface comes from the
            // table and is released before the cookie goes.
            unsafe {
                if CoInitializeEx(None, COINIT_MULTITHREADED).is_err() {
                    return;
                }
                if let Ok(git) = CoCreateInstance::<_, IGlobalInterfaceTable>(&STD_GIT, None, CLSCTX_INPROC_SERVER) {
                    while WATCHED.lock().unwrap().contains(&id) {
                        std::thread::sleep(Duration::from_secs(2));
                        if !WATCHED.lock().unwrap().contains(&id) {
                            break;
                        }
                        let mut out: Option<IOleClientSite> = None;
                        let asked = git.GetInterfaceFromGlobal(cookie, &IOleClientSite::IID, &mut out as *mut _ as *mut _).and_then(|_| match &out {
                            Some(s) => s.GetContainer().map(|_| ()),
                            None => Ok(()),
                        });
                        drop(out);
                        if matches!(&asked, Err(e) if container_gone(e)) {
                            WATCHED.lock().unwrap().remove(&id);
                            if let Some(a) = app() {
                                let _ = a.run_on_main_thread(move || {
                                    if let Some(o) = OPEN.with(|m| m.borrow().get(&id).cloned()) {
                                        o.gone_now();
                                    }
                                });
                            }
                        }
                    }
                    let _ = git.RevokeInterfaceFromGlobal(cookie);
                }
                CoUninitialize();
            }
        });
    }

    fn formats(&self) -> Vec<FORMATETC> {
        vec![formatetc(registered(super::EMBED_SOURCE), TYMED_ISTORAGE.0), formatetc(CF_ENHMETAFILE.0, TYMED_ENHMF.0), formatetc(CF_METAFILEPICT.0, TYMED_MFPICT.0)]
    }

    // A picture from the window. Its frame is the size from now on. A changed drawing (Update) drops the size Word
    // asked for, so Word takes the new drawing's size; the same drawing (sent when the window opens) keeps it.
    fn picture(&self, emf: Vec<u8>, changed: bool) {
        if let Some(size) = super::extent(&emf).filter(|s| super::valid_extent(*s)) {
            self.extent.set(size);
        }
        if changed {
            self.asked.set(None);
        }
        *self.emf.borrow_mut() = Some(emf);
    }

    // Edit or Open: the window opens (from the async runtime, never in this call), or comes to the front.
    fn show(this: &windows_core::ComObject<Drawing>) {
        OPEN.with(|m| m.borrow_mut().insert(this.id, this.clone()));
        if !this.locked.get() {
            let unknown: IUnknown = this.to_interface();
            // SAFETY: a live object on its own apartment's thread.
            if unsafe { CoLockObjectExternal(&unknown, true, true) }.is_ok() {
                this.locked.set(true);
            }
        }
        let Some(app) = app().cloned() else { return };
        let label = label(this.id);
        if this.shown.replace(true) {
            tauri::async_runtime::spawn(async move { let _ = crate::windows::window_show(app, label).await; });
            return;
        }
        let start = serde_json::json!({ "object": this.id, "oct": this.oct.borrow().as_str(), "host": this.host.borrow().as_str(), "title": this.title(), "app": this.app.borrow().as_str() });
        let host = this.host.borrow().clone();
        tauri::async_runtime::spawn(async move {
            if let Err(e) = crate::windows::open_object(app.clone(), label, start, host).await {
                log(&format!("the object window did not open ({e})"));
            }
        });
    }

    // OnShowWindow(FALSE) and OnClose to Word, so it takes the shading off and lets the server go.
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleclientsite-onshowwindow
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleadviseholder-sendonclose
    fn closed_notices(&self) {
        WATCHED.lock().unwrap().remove(&self.id);
        if self.gone.get() {
            return;
        }
        let (site, advise) = (self.site.borrow().clone(), self.advise.borrow().clone());
        if self.shown.replace(false) {
            if let Some(s) = site {
                // SAFETY: a call to the container's live site; a failure means Word is gone, which changes nothing here.
                let _ = unsafe { s.OnShowWindow(false) };
            }
        }
        if let Some(a) = advise {
            // SAFETY: as above, to Word's advise sinks through the holder.
            let _ = unsafe { a.SendOnClose() };
        }
    }

    // After the window closes: the lock goes, and Word's links to the object are cut, so Word lets it go and an
    // embedding Octet can end. On the main thread run_on_main_thread runs this at once, so it can run inside a call
    // from Word (Close). That is allowed: CoDisconnectObject waits for calls in progress to return.
    // https://learn.microsoft.com/windows/win32/api/combaseapi/nf-combaseapi-codisconnectobject
    fn disconnect(this: &windows_core::ComObject<Drawing>) {
        LATER.with(|l| l.borrow_mut().push((this.to_interface(), this.locked.replace(false))));
        match app() {
            Some(a) => {
                let _ = a.run_on_main_thread(disconnect_later);
            }
            None => disconnect_later(),
        }
    }

    fn gone_now(&self) {
        WATCHED.lock().unwrap().remove(&self.id);
        if self.gone.replace(true) {
            return;
        }
        self.site.borrow_mut().take();
        self.advise.borrow_mut().take();
        self.data_advise.borrow_mut().take();
        if let Some(a) = app() {
            let _ = a.emit_to(label(self.id), "ole-gone", self.title());
        }
    }

    // Update: the new drawing and picture go into Word now. OnDataChange makes the default handler take the new
    // picture (GetData); SaveObject makes Word save the storage (Save, then SaveCompleted, which sends OnSave).
    // https://learn.microsoft.com/windows/win32/api/objidl/nf-objidl-idataadviseholder-sendondatachange
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleclientsite-saveobject
    fn update(this: &windows_core::ComObject<Drawing>, oct: String, emf: Vec<u8>) -> std::result::Result<(), String> {
        let doc = this.host.borrow().clone();
        if this.gone.get() {
            return Err(format!("{doc} is closed. Save a copy to keep this drawing."));
        }
        this.latest.borrow_mut().take();
        *this.oct.borrow_mut() = oct;
        this.picture(emf, true);
        this.dirty.set(true);
        let data: IDataObject = this.to_interface();
        let (holder, site) = (this.data_advise.borrow().clone(), this.site.borrow().clone());
        let sent = waiting(|| {
            // SAFETY: calls to Word's live holder and site; no borrow is held, as Word calls back into GetData and Save.
            unsafe {
                if let Some(h) = holder {
                    h.SendOnDataChange(&data, None, 0)?;
                }
                match site {
                    Some(s) => s.SaveObject(),
                    None => Ok(()),
                }
            }
        });
        match sent {
            Ok(()) => Ok(()),
            Err(e) if container_gone(&e) => {
                this.gone_now();
                Err(format!("{doc} is closed. Save a copy to keep this drawing."))
            }
            Err(e) => {
                log(&format!("update failed ({e})"));
                Err(format!("Octet cannot update {doc}. Try again."))
            }
        }
    }
}

impl Drawing {
    // Close and Quit: the window's newest drawing goes to Word, then Word saves the object. No question, and no
    // wait for the page.
    fn flush(this: &windows_core::ComObject<Drawing>) {
        if this.gone.get() {
            this.latest.borrow_mut().take();
            return;
        }
        let latest = this.latest.borrow_mut().take();
        if let Some((oct, emf)) = latest {
            *this.oct.borrow_mut() = oct;
            this.picture(emf, true);
            this.dirty.set(true);
            let (holder, data): (_, IDataObject) = (this.data_advise.borrow().clone(), this.to_interface());
            if let Some(h) = holder {
                // SAFETY: a call to Word's live holder; no borrow is held, as Word calls back into GetData.
                let _ = waiting(|| unsafe { h.SendOnDataChange(&data, None, 0) });
            }
        }
        if this.dirty.get() {
            let site = this.site.borrow().clone();
            if let Some(s) = site {
                // SAFETY: a call to Word's live site; Word calls Save on this thread meanwhile.
                let _ = waiting(|| unsafe { s.SaveObject() });
            }
        }
    }
}

fn disconnect_later() {
    let list = LATER.with(|l| std::mem::take(&mut *l.borrow_mut()));
    for (unknown, locked) in list {
        // SAFETY: live objects on the main thread, their own apartment.
        unsafe {
            if locked {
                let _ = CoLockObjectExternal(&unknown, false, true);
            }
            let _ = CoDisconnectObject(&unknown, None);
        }
    }
}

impl Drop for Drawing {
    fn drop(&mut self) {
        WATCHED.lock().unwrap().remove(&self.id);
        if let Some(h) = self.container.take() {
            // SAFETY: the handle note_caller opened.
            let _ = unsafe { CloseHandle(h) };
        }
        // Never at once: this can be the last Release of a call from Word, or inside a borrow of OPEN.
        if LIVE.fetch_sub(1, SeqCst) == 1 {
            later(maybe_exit);
        }
    }
}

impl IOleObject_Impl for Drawing_Impl {
    fn SetClientSite(&self, site: Ref<IOleClientSite>) -> Result<()> {
        *self.site.borrow_mut() = site.cloned();
        Ok(())
    }
    fn GetClientSite(&self) -> Result<IOleClientSite> {
        self.site.borrow().clone().ok_or_else(|| fail(E_FAIL))
    }
    // The container's name and the document's: the window's title says the document, and its Update button the
    // container ("Microsoft Word" gives Update in Word).
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleobject-sethostnames
    fn SetHostNames(&self, program: &PCWSTR, doc: &PCWSTR) -> Result<()> {
        // SAFETY: the container's NUL-terminated strings, read during the call (null is allowed).
        let read = |s: &PCWSTR| if s.is_null() { String::new() } else { unsafe { s.to_string() }.unwrap_or_default() };
        let program = super::program_name(&read(program));
        let doc = super::host_name(&read(doc));
        if *self.host.borrow() != doc || *self.app.borrow() != program {
            *self.host.borrow_mut() = doc.clone();
            *self.app.borrow_mut() = program.clone();
            if self.shown.get() {
                if let Some(a) = app().cloned() {
                    let l = label(self.id);
                    let _ = a.emit_to(l.clone(), "ole-host", (doc.clone(), self.title(), program));
                    tauri::async_runtime::spawn(async move { crate::windows::object_host(&a, &l, &doc) });
                }
            }
        }
        Ok(())
    }
    // Word closes the document or ends. Unless Word says NOSAVE, the window's newest drawing goes to Word, with no
    // question (PROMPTSAVE too: decision 0023, Q2), then Word saves the object. Nothing here waits for the page or
    // shows a dialog: the page already gave its newest drawing (latest). The window then closes itself.
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleobject-close
    fn Close(&self, option: &OLECLOSE) -> Result<()> {
        let id = self.id;
        if self.closing.replace(true) {
            return Ok(());
        }
        // Whether Word got the window's newest drawing. If not (NOSAVE with changes not sent), the window stays open
        // and keeps the drawing, as when Word goes away.
        let sent = *option != OLECLOSE_NOSAVE || self.latest.borrow().is_none();
        if *option == OLECLOSE_NOSAVE {
            self.latest.borrow_mut().take();
        } else {
            Drawing::flush(&self.to_object());
        }
        let shown = OPEN.with(|m| m.borrow_mut().remove(&id)).is_some();
        self.closed_notices();
        Drawing::disconnect(&self.to_object());
        if shown {
            if let Some(a) = app() {
                // sent: Word has the drawing, and the page closes its window with no question unless it has a change
                // newer than the one it last gave. Otherwise the window stays, says the document is closed, and keeps
                // the drawing for Save Copy As.
                let _ = a.emit_to(label(id), "ole-closed", (sent, super::title(&self.host.borrow(), true)));
            }
        }
        Ok(())
    }
    fn SetMoniker(&self, _which: &OLEWHICHMK, _mk: Ref<IMoniker>) -> Result<()> {
        Ok(()) // no links into an Octet Drawing (OLEMISC_CANTLINKINSIDE)
    }
    fn GetMoniker(&self, _assign: &OLEGETMONIKER, _which: &OLEWHICHMK) -> Result<IMoniker> {
        Err(fail(E_NOTIMPL))
    }
    fn InitFromData(&self, _data: Ref<IDataObject>, _creation: BOOL, _reserved: u32) -> Result<()> {
        Err(fail(E_NOTIMPL))
    }
    fn GetClipboardData(&self, _reserved: u32) -> Result<IDataObject> {
        Err(fail(E_NOTIMPL))
    }
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleobject-doverb
    fn DoVerb(&self, verb: i32, _msg: *const MSG, active: Ref<IOleClientSite>, _lindex: i32, parent: HWND, _rect: *const RECT) -> Result<()> {
        use super::Verb;
        match super::verb(verb) {
            Verb::Open | Verb::Unknown => {
                if self.gone.get() {
                    return Err(fail(E_FAIL));
                }
                if self.site.borrow().is_none() {
                    *self.site.borrow_mut() = active.cloned();
                }
                self.note_caller(parent);
                let site = self.site.borrow().clone();
                if let Some(s) = &site {
                    // SAFETY: calls to the container's live site; failures change nothing.
                    let _ = unsafe { s.ShowObject() };
                }
                Drawing::show(&self.to_object());
                if let Some(s) = &site {
                    // SAFETY: as above. Word shades the object while its window is open.
                    let _ = unsafe { s.OnShowWindow(true) };
                }
                if super::verb(verb) == Verb::Unknown { Err(fail(OLEOBJ_S_INVALIDVERB)) } else { Ok(()) }
            }
            Verb::Hide => {
                if let Some(a) = app() {
                    if let Some(w) = a.get_webview_window(&label(self.id)) {
                        let _ = w.hide();
                    }
                }
                Ok(())
            }
            Verb::Nothing => Ok(()),
            Verb::NotSupported => Err(fail(E_NOTIMPL)),
        }
    }
    fn EnumVerbs(&self) -> Result<IEnumOLEVERB> {
        // SAFETY: reads the registry's Verb keys for the class.
        unsafe { OleRegEnumVerbs(&CLASS) }
    }
    fn Update(&self) -> Result<()> {
        Ok(())
    }
    fn IsUpToDate(&self) -> Result<()> {
        Ok(()) // embedded, with no links
    }
    fn GetUserClassID(&self) -> Result<GUID> {
        Ok(CLASS)
    }
    fn GetUserType(&self, form: &USERCLASSTYPE) -> Result<PWSTR> {
        // SAFETY: reads the registry's AuxUserType keys; the string is the caller's to free.
        unsafe { OleRegGetUserType(&CLASS, *form) }
    }
    // Word gives the space it shows the object in (the user resized it, or Word fits it to the page). Octet takes it
    // and gives it back from GetExtent, so Word and Octet agree on the size. The picture is not redrawn: it keeps the
    // drawing's own aspect, and Word scales it into the space. E_FAIL is only for an object whose size cannot be set
    // (a link); an embedded picture can be scaled. A changed drawing (Update) gives its own size again.
    // https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleobject-setextent
    fn SetExtent(&self, aspect: DVASPECT, size: *const SIZE) -> Result<()> {
        if aspect != DVASPECT_CONTENT {
            return Err(fail(E_FAIL));
        }
        if size.is_null() {
            return Err(fail(E_INVALIDARG));
        }
        // SAFETY: the caller's SIZEL, checked non-null, read once.
        let s = unsafe { *size };
        if !super::valid_extent((s.cx, s.cy)) {
            return Err(fail(E_INVALIDARG));
        }
        self.asked.set(Some((s.cx, s.cy)));
        Ok(())
    }
    fn GetExtent(&self, aspect: DVASPECT) -> Result<SIZE> {
        if aspect != DVASPECT_CONTENT {
            return Err(fail(DV_E_DVASPECT));
        }
        // The size Word asked for, else the picture's: from the storage's size stream at Load, before the window sends
        // a picture. Never OLE_E_BLANK: the default handler gives Word the running object's answer as it is.
        let (cx, cy) = self.asked.get().unwrap_or(self.extent.get());
        Ok(SIZE { cx, cy })
    }
    fn Advise(&self, sink: Ref<IAdviseSink>) -> Result<u32> {
        if self.advise.borrow().is_none() {
            // SAFETY: makes OLE's own advise holder.
            *self.advise.borrow_mut() = Some(unsafe { CreateOleAdviseHolder()? });
        }
        let holder = self.advise.borrow().clone().ok_or_else(|| fail(E_FAIL))?;
        // SAFETY: the holder AddRefs the sink.
        unsafe { holder.Advise(sink.ok()?) }
    }
    fn Unadvise(&self, connection: u32) -> Result<()> {
        let holder = self.advise.borrow().clone().ok_or_else(|| fail(E_FAIL))?;
        // SAFETY: as Advise.
        unsafe { holder.Unadvise(connection) }
    }
    fn EnumAdvise(&self) -> Result<IEnumSTATDATA> {
        let holder = self.advise.borrow().clone().ok_or_else(|| fail(E_FAIL))?;
        // SAFETY: as Advise.
        unsafe { holder.EnumAdvise() }
    }
    fn GetMiscStatus(&self, aspect: DVASPECT) -> Result<OLEMISC> {
        // SAFETY: reads the registry's MiscStatus key for the class.
        unsafe { OleRegGetMiscStatus(&CLASS, aspect.0).map(|m| OLEMISC(m as i32)) }
    }
    fn SetColorScheme(&self, _palette: *const LOGPALETTE) -> Result<()> {
        Err(fail(E_NOTIMPL))
    }
}

impl IDataObject_Impl for Drawing_Impl {
    // The picture (EMF, or WMF for a container that asks for one) and the object's own storage.
    // https://learn.microsoft.com/windows/win32/api/objidl/nf-objidl-idataobject-getdata
    fn GetData(&self, asked: *const FORMATETC) -> Result<STGMEDIUM> {
        let f = check(asked, &self.formats())?;
        match f.tymed as i32 {
            t if t == TYMED_ENHMF.0 || t == TYMED_MFPICT.0 => {
                let emf = self.emf.borrow().clone().ok_or_else(|| fail(OLE_E_BLANK))?;
                if t == TYMED_ENHMF.0 { medium_emf(&emf) } else { medium_wmf(&emf) }
            }
            _ => {
                let stg = storage_in_memory(&self.oct.borrow(), self.extent.get())?;
                Ok(medium(TYMED_ISTORAGE.0, STGMEDIUM_0 { pstg: ManuallyDrop::new(Some(stg)) }))
            }
        }
    }
    fn GetDataHere(&self, asked: *const FORMATETC, out: *mut STGMEDIUM) -> Result<()> {
        let f = check(asked, &self.formats())?;
        if f.tymed as i32 != TYMED_ISTORAGE.0 || out.is_null() {
            return Err(fail(DV_E_FORMATETC));
        }
        // SAFETY: the caller's medium, checked non-null; its storage is borrowed, not released.
        let stg = unsafe { (*out).u.pstg.as_ref().cloned() }.ok_or_else(|| fail(E_INVALIDARG))?;
        write_storage(&stg, &self.oct.borrow(), self.extent.get())
    }
    fn QueryGetData(&self, asked: *const FORMATETC) -> HRESULT {
        match check(asked, &self.formats()) {
            Ok(f) if f.tymed as i32 != TYMED_ISTORAGE.0 && self.emf.borrow().is_none() => OLE_E_BLANK,
            Ok(_) => S_OK,
            Err(e) => e.code(),
        }
    }
    fn GetCanonicalFormatEtc(&self, asked: *const FORMATETC, out: *mut FORMATETC) -> HRESULT {
        canonical(asked, out)
    }
    fn SetData(&self, _f: *const FORMATETC, _m: *const STGMEDIUM, _release: BOOL) -> Result<()> {
        Err(fail(E_NOTIMPL))
    }
    fn EnumFormatEtc(&self, direction: u32) -> Result<IEnumFORMATETC> {
        if direction != DATADIR_GET.0 as u32 {
            return Err(fail(E_NOTIMPL));
        }
        Ok(Formats { list: self.formats(), at: Cell::new(0) }.into())
    }
    // The default handler asks for the picture through these, and refreshes its cache when Octet sends OnDataChange.
    fn DAdvise(&self, f: *const FORMATETC, advf: u32, sink: Ref<IAdviseSink>) -> Result<u32> {
        if self.data_advise.borrow().is_none() {
            // SAFETY: makes OLE's own data advise holder.
            *self.data_advise.borrow_mut() = Some(unsafe { CreateDataAdviseHolder()? });
        }
        let holder = self.data_advise.borrow().clone().ok_or_else(|| fail(E_FAIL))?;
        let data: IDataObject = self.to_object().to_interface();
        // SAFETY: the holder AddRefs the sink and may call GetData now (ADVF_PRIMEFIRST); no borrow is held.
        unsafe { holder.Advise(&data, f, advf, sink.ok()?) }
    }
    fn DUnadvise(&self, connection: u32) -> Result<()> {
        let holder = self.data_advise.borrow().clone().ok_or_else(|| fail(OLE_E_ADVISENOTSUPPORTED))?;
        // SAFETY: as DAdvise.
        unsafe { holder.Unadvise(connection) }
    }
    fn EnumDAdvise(&self) -> Result<IEnumSTATDATA> {
        let holder = self.data_advise.borrow().clone().ok_or_else(|| fail(OLE_E_ADVISENOTSUPPORTED))?;
        // SAFETY: as DAdvise.
        unsafe { holder.EnumAdvise() }
    }
}

fn canonical(asked: *const FORMATETC, out: *mut FORMATETC) -> HRESULT {
    if asked.is_null() || out.is_null() {
        return E_INVALIDARG;
    }
    // SAFETY: both pointers are the caller's, checked non-null.
    unsafe {
        *out = *asked;
        (*out).ptd = std::ptr::null_mut();
    }
    DATA_S_SAMEFORMATETC
}

impl IPersist_Impl for Drawing_Impl {
    fn GetClassID(&self) -> Result<GUID> {
        Ok(CLASS)
    }
}

// https://learn.microsoft.com/windows/win32/api/objidl/nn-objidl-ipersiststorage
impl IPersistStorage_Impl for Drawing_Impl {
    fn IsDirty(&self) -> HRESULT {
        if self.dirty.get() { S_OK } else { S_FALSE }
    }
    // Insert > Object > Create New: an empty drawing, which Word saves once.
    fn InitNew(&self, stg: Ref<IStorage>) -> Result<()> {
        *self.storage.borrow_mut() = Some(stg.ok()?.clone());
        self.oct.borrow_mut().clear();
        self.dirty.set(true);
        self.extent.set(super::BLANK_EXTENT);
        Ok(())
    }
    // An object from a document: the stream Octet, read as hostile (ole::read_stream). A storage Octet cannot read
    // is refused, and the user hears why.
    fn Load(&self, stg: Ref<IStorage>) -> Result<()> {
        let stg = stg.ok()?.clone();
        match read_storage(&stg) {
            Ok(oct) => {
                self.extent.set(super::loaded_extent(read_size_stream(&stg).as_ref().map(|b| &b[..]), &oct));
                *self.oct.borrow_mut() = oct;
                *self.storage.borrow_mut() = Some(stg);
                self.dirty.set(false);
                Ok(())
            }
            Err(why) => {
                log(&format!("an object was refused ({why:?})"));
                tell(CANNOT_OPEN);
                Err(fail(STG_E_DOCFILECORRUPT))
            }
        }
    }
    fn Save(&self, stg: Ref<IStorage>, _same_as_load: BOOL) -> Result<()> {
        write_storage(stg.ok()?, &self.oct.borrow(), self.extent.get())
    }
    fn SaveCompleted(&self, stg: Ref<IStorage>) -> Result<()> {
        if let Some(s) = stg.cloned() {
            *self.storage.borrow_mut() = Some(s);
        }
        self.dirty.set(false);
        if let Some(a) = self.advise.borrow().clone() {
            // SAFETY: to Word's sinks through the holder; no borrow of `advise` is held over the call.
            let _ = unsafe { a.SendOnSave() };
        }
        Ok(())
    }
    fn HandsOffStorage(&self) -> Result<()> {
        self.storage.borrow_mut().take();
        Ok(())
    }
}

// Insert > Object > Create from File with a .oct file (GetClassFile gives Octet Drawing through the .oct type's CLSID
// key). The file is read with Open's limits. Octet has no picture of it until the window updates Word once.
// https://learn.microsoft.com/windows/win32/api/objidl/nf-objidl-ipersistfile-load
impl IPersistFile_Impl for Drawing_Impl {
    fn IsDirty(&self) -> HRESULT {
        S_FALSE
    }
    fn Load(&self, name: &PCWSTR, _mode: STGM) -> Result<()> {
        if name.is_null() {
            return Err(fail(E_POINTER));
        }
        // SAFETY: the caller's NUL-terminated file name, read during the call.
        let path = std::path::PathBuf::from(unsafe { name.to_string() }.map_err(|_| fail(E_INVALIDARG))?);
        let read = std::fs::metadata(&path).ok().filter(|m| m.is_file() && m.len() <= super::MAX_STREAM).and_then(|_| std::fs::read(&path).ok()).and_then(|b| String::from_utf8(b).ok());
        match read {
            Some(oct) => {
                self.extent.set(super::loaded_extent(None, &oct));
                *self.oct.borrow_mut() = oct;
                self.dirty.set(true);
                Ok(())
            }
            None => {
                tell(CANNOT_OPEN);
                Err(fail(STG_E_DOCFILECORRUPT))
            }
        }
    }
    fn Save(&self, _name: &PCWSTR, _remember: BOOL) -> Result<()> {
        Err(fail(E_NOTIMPL))
    }
    fn SaveCompleted(&self, _name: &PCWSTR) -> Result<()> {
        Ok(())
    }
    fn GetCurFile(&self) -> Result<PWSTR> {
        Err(fail(E_NOTIMPL))
    }
}

// A message for the user when no window is there to say it. It does not wait for the user: Octet goes on serving
// Word (and a test harness is never stuck on it).
fn tell(text: &'static str) {
    use tauri_plugin_dialog::{DialogExt, MessageDialogKind};
    if let Some(a) = app() {
        a.dialog().message(text).title(super::APP).kind(MessageDialogKind::Warning).show(|_| {});
    }
}

// The check that Word is still there, every 2 seconds while an object window is open (R14): Word's process has
// ended. Octet's main thread never calls Word for this, so a busy or hung Word cannot stop Octet. When Octet could
// not learn Word's process, watch_site asks Word from a thread of its own.
fn ping() {
    let open: Vec<_> = OPEN.with(|m| m.borrow().values().filter(|o| !o.gone.get()).cloned().collect());
    for o in open {
        if let Some(h) = o.container.get() {
            // SAFETY: a process handle Octet holds; a wait of 0 ms only looks.
            if unsafe { WaitForSingleObject(h, 0) } == WAIT_OBJECT_0 {
                o.gone_now();
            }
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// The page's commands (decision 0023): Update and Close from the object window.

// Runs `f` on the main thread and gives back its answer.
pub async fn on_main<T: Send + 'static>(app: &AppHandle, f: impl FnOnce() -> T + Send + 'static) -> std::result::Result<T, String> {
    let (tx, rx) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let _ = tx.send(f());
    })
    .map_err(|e| e.to_string())?;
    tauri::async_runtime::spawn_blocking(move || rx.recv()).await.map_err(|e| e.to_string())?.map_err(|e| e.to_string())
}

// File > Update Document1 (Ctrl+S), from objects::ole_update, which checked the sizes: the picture becomes the EMF
// here, as Copy makes it. The window sends its picture once the drawing is open, so GetData and GetExtent have it,
// and then its newest drawing after each change, for Close and Quit (Session::message).
pub async fn update(app: AppHandle, id: u64, oct: String, svg: String, cdxml: String, send: Option<bool>, seq: Option<u64>) -> std::result::Result<(), String> {
    let emf = crate::vector::make_emf(&crate::export::tree(&svg)?, Some(&cdxml), None);
    on_main(&app, move || {
        let o = OPEN.with(|m| m.borrow().get(&id).cloned()).filter(|o| !o.closing.get()).ok_or("The document is closed. Save a copy to keep this drawing.")?;
        match o.message(seq, send != Some(false), oct, emf) {
            Taken::Same(emf) => o.picture(emf, false),
            Taken::Send(oct, emf) => return Drawing::update(&o, oct, emf),
            Taken::Old | Taken::Kept => {}
        }
        Ok(())
    })
    .await?
}

// The object's window is gone (closed by the page, or destroyed): Word hears so, once.
pub fn closed(id: u64) {
    let o = OPEN.with(|m| m.borrow().get(&id).cloned());
    if let Some(o) = o.filter(|o| !o.closing.replace(true)) {
        OPEN.with(|m| m.borrow_mut().remove(&id));
        Drawing::flush(&o);
        o.closed_notices();
        Drawing::disconnect(&o);
    }
}

// ---------------------------------------------------------------------------------------------------------------
// Copy through the OLE clipboard: "Embed Source" and "Object Descriptor", then every format decision 0011 lists, in
// its order. OleFlushClipboard renders each one at once, so the copy stays after Octet ends and Octet holds nothing.
// https://learn.microsoft.com/windows/win32/api/ole2/nf-ole2-olesetclipboard
// https://learn.microsoft.com/windows/win32/api/ole2/nf-ole2-oleflushclipboard

enum Payload {
    Bytes(Vec<u8>),
    Emf(Vec<u8>),
    Storage(String, (i32, i32)),
}

#[implement(IDataObject, Agile = false)]
struct Clip {
    items: Vec<(FORMATETC, Payload)>,
}

impl Clip {
    fn list(&self) -> Vec<FORMATETC> {
        self.items.iter().map(|(f, _)| *f).collect()
    }
    fn find(&self, f: &FORMATETC) -> Option<&Payload> {
        self.items.iter().find(|(g, _)| g.cfFormat == f.cfFormat && g.tymed == f.tymed).map(|(_, p)| p)
    }
}

impl IDataObject_Impl for Clip_Impl {
    fn GetData(&self, asked: *const FORMATETC) -> Result<STGMEDIUM> {
        let f = check(asked, &self.list())?;
        match self.find(&f).ok_or_else(|| fail(DV_E_FORMATETC))? {
            Payload::Bytes(b) => medium_bytes(b),
            Payload::Emf(b) => medium_emf(b),
            Payload::Storage(oct, size) => Ok(medium(TYMED_ISTORAGE.0, STGMEDIUM_0 { pstg: ManuallyDrop::new(Some(storage_in_memory(oct, *size)?)) })),
        }
    }
    fn GetDataHere(&self, asked: *const FORMATETC, out: *mut STGMEDIUM) -> Result<()> {
        let f = check(asked, &self.list())?;
        let Some(Payload::Storage(oct, size)) = self.find(&f) else { return Err(fail(DV_E_FORMATETC)) };
        if out.is_null() {
            return Err(fail(E_INVALIDARG));
        }
        // SAFETY: the caller's medium, checked non-null; its storage is borrowed, not released.
        let stg = unsafe { (*out).u.pstg.as_ref().cloned() }.ok_or_else(|| fail(E_INVALIDARG))?;
        write_storage(&stg, oct, *size)
    }
    fn QueryGetData(&self, asked: *const FORMATETC) -> HRESULT {
        check(asked, &self.list()).map_or_else(|e| e.code(), |_| S_OK)
    }
    fn GetCanonicalFormatEtc(&self, asked: *const FORMATETC, out: *mut FORMATETC) -> HRESULT {
        canonical(asked, out)
    }
    fn SetData(&self, _f: *const FORMATETC, _m: *const STGMEDIUM, _release: BOOL) -> Result<()> {
        Err(fail(E_NOTIMPL))
    }
    fn EnumFormatEtc(&self, direction: u32) -> Result<IEnumFORMATETC> {
        if direction != DATADIR_GET.0 as u32 {
            return Err(fail(E_NOTIMPL));
        }
        Ok(Formats { list: self.list(), at: Cell::new(0) }.into())
    }
    fn DAdvise(&self, _f: *const FORMATETC, _advf: u32, _sink: Ref<IAdviseSink>) -> Result<u32> {
        Err(fail(OLE_E_ADVISENOTSUPPORTED))
    }
    fn DUnadvise(&self, _c: u32) -> Result<()> {
        Err(fail(OLE_E_ADVISENOTSUPPORTED))
    }
    fn EnumDAdvise(&self) -> Result<IEnumSTATDATA> {
        Err(fail(OLE_E_ADVISENOTSUPPORTED))
    }
}

// The data object for one copy. `types`: decision 0011's formats in order, each with its number (from
// clipboard_windows's format()); `oct`: the selection as a .oct file.
fn clip_object(types: &[(u16, &str, Vec<u8>)], oct: String) -> IDataObject {
    let emf = types.iter().find(|(cf, ..)| *cf == CF_ENHMETAFILE.0).map(|(.., b)| b.as_slice());
    let size = emf.and_then(super::extent).unwrap_or(super::BLANK_EXTENT);
    let names: Vec<&str> = types.iter().map(|(_, n, _)| *n).collect();
    let mut items = Vec::new();
    for name in super::clipboard_order(true, &names) {
        if name == super::EMBED_SOURCE {
            items.push((formatetc(registered(name), TYMED_ISTORAGE.0), Payload::Storage(oct.clone(), size)));
        } else if name == super::OBJECT_DESCRIPTOR {
            items.push((formatetc(registered(name), TYMED_HGLOBAL.0), Payload::Bytes(super::object_descriptor(size))));
        } else if let Some((cf, _, b)) = types.iter().find(|(_, n, _)| *n == name) {
            if *cf == CF_ENHMETAFILE.0 {
                items.push((formatetc(*cf, TYMED_ENHMF.0), Payload::Emf(b.clone())));
            } else {
                items.push((formatetc(*cf, TYMED_HGLOBAL.0), Payload::Bytes(b.clone())));
            }
        }
    }
    Clip { items }.into()
}

// Copy with the object, on the main thread. Another program can hold the clipboard for a moment, so it tries for half
// a second, as the plain copy does.
pub async fn copy(app: &AppHandle, types: Vec<(u16, &'static str, Vec<u8>)>, oct: String) -> std::result::Result<(), String> {
    on_main(app, move || {
        let data = clip_object(&types, oct);
        for _ in 0..10 {
            // SAFETY: OLE calls on the main thread (OLE is on); OLE AddRefs the data object and, after the flush,
            // has rendered every format and released it.
            let set = unsafe { OleSetClipboard(&data).and_then(|_| OleFlushClipboard()) };
            if set.is_ok() {
                LAST_CLIP.with(|c| *c.borrow_mut() = Some(data.clone()));
                return Ok(());
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        Err("Another app is using the clipboard. Try again.".to_string())
    })
    .await?
}

// ---------------------------------------------------------------------------------------------------------------
// Tests that need Windows: the object in this process, through its COM interfaces, with storages in memory. They run
// in the Windows CI job (cargo test on windows-latest). The container harness in tests/ole_container.rs drives the
// real server from another process.

#[cfg(test)]
mod tests {
    use super::*;
    use windows::Win32::System::Ole::OleUninitialize;

    fn ole<T>(f: impl FnOnce() -> T) -> T {
        // SAFETY: each test thread starts and ends OLE once.
        unsafe { OleInitialize(None).unwrap() };
        let out = f();
        // SAFETY: as above.
        unsafe { OleUninitialize() };
        out
    }

    fn storage() -> IStorage {
        // SAFETY: an in-memory compound file, freed on release.
        unsafe {
            let b = CreateILockBytesOnHGlobal(None, true).unwrap();
            StgCreateDocfileOnILockBytes(&b, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0).unwrap()
        }
    }

    fn put_stream(stg: &IStorage, name: &str, bytes: &[u8]) {
        let n = wide(name);
        // SAFETY: COM calls on a live storage with live buffers.
        unsafe {
            let s = stg.CreateStream(PCWSTR(n.as_ptr()), STGM_CREATE | STGM_WRITE | STGM_SHARE_EXCLUSIVE, 0, 0).unwrap();
            if !bytes.is_empty() {
                s.Write(bytes.as_ptr().cast(), bytes.len() as u32, None).ok().unwrap();
            }
        }
    }

    const OCT: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><CDXML><page/></CDXML><!--Octet 1 0 e30=-->";

    #[test]
    fn storage_round_trip() {
        ole(|| {
            let stg = storage();
            write_storage(&stg, OCT, (1983, 1289)).unwrap();
            assert_eq!(read_storage(&stg).as_deref(), Ok(OCT));
            assert_eq!(read_size_stream(&stg).and_then(|b| super::super::read_size(&b)), Some((1983, 1289)));
            // The object through IPersistStorage: Load, then Save into a new storage, then Load that.
            let obj: IPersistStorage = Drawing::new().into();
            // SAFETY: COM calls on live objects.
            unsafe {
                assert_eq!(obj.GetClassID().unwrap(), CLASS);
                obj.Load(&stg).unwrap();
                assert_eq!(obj.IsDirty(), S_FALSE);
                let ole: IOleObject = obj.cast().unwrap();
                assert_eq!(ole.GetExtent(DVASPECT_CONTENT).unwrap(), SIZE { cx: 1983, cy: 1289 }, "the size from Load on");
                let out = storage();
                obj.Save(&out, false).unwrap();
                obj.SaveCompleted(&out).unwrap();
                assert_eq!(read_storage(&out).as_deref(), Ok(OCT));
                assert_eq!(read_size_stream(&out).and_then(|b| super::super::read_size(&b)), Some((1983, 1289)));
                assert_eq!(ReadClassStg(&out).unwrap(), CLASS);
                // A storage with no size stream, or a bad one: the drawing's own size, never OLE_E_BLANK.
                let old = storage();
                WriteClassStg(&old, &CLASS).unwrap();
                put_stream(&old, "Octet", b"<CDXML BoundingBox=\"0 0 72 36\"><page/></CDXML>");
                put_stream(&old, "OctetSize", &[1, 2, 3]);
                let o2: IPersistStorage = Drawing::new().into();
                o2.Load(&old).unwrap();
                assert_eq!(o2.cast::<IOleObject>().unwrap().GetExtent(DVASPECT_CONTENT).unwrap(), SIZE { cx: 2540, cy: 1270 });
            }
        });
    }

    // R13: hostile storages are refused, and nothing panics.
    #[test]
    fn hostile_storages_are_refused() {
        ole(|| {
            // No stream.
            let stg = storage();
            // SAFETY: COM calls on a live storage.
            unsafe { WriteClassStg(&stg, &CLASS).unwrap() };
            assert_eq!(read_storage(&stg), Err(Refused::NoStream));
            // Another program's class.
            let other = storage();
            // SAFETY: as above.
            unsafe { WriteClassStg(&other, &GUID::from_u128(0x1234)).unwrap() };
            put_stream(&other, "Octet", b"<CDXML/>");
            assert_eq!(read_storage(&other), Err(Refused::WrongClass));
            // Not UTF-8.
            let bad = storage();
            // SAFETY: as above.
            unsafe { WriteClassStg(&bad, &CLASS).unwrap() };
            put_stream(&bad, "Octet", &[0xff, 0xfe, 0x00, 0x80]);
            assert_eq!(read_storage(&bad), Err(Refused::NotText));
            // Larger than 64 MB.
            let big = storage();
            // SAFETY: as above.
            unsafe { WriteClassStg(&big, &CLASS).unwrap() };
            put_stream(&big, "Octet", &vec![b'a'; (super::super::MAX_STREAM + 1024 * 1024) as usize]);
            assert_eq!(read_storage(&big), Err(Refused::TooLarge));
            // Deeply nested CDXML is text: Rust passes it on and the page's reader refuses it as it refuses such a file.
            let deep = storage();
            // SAFETY: as above.
            unsafe { WriteClassStg(&deep, &CLASS).unwrap() };
            let nested = format!("{}{}", "<a>".repeat(100_000), "</a>".repeat(100_000));
            put_stream(&deep, "Octet", nested.as_bytes());
            assert_eq!(read_storage(&deep).map(|t| t.len()), Ok(nested.len()));
            // Load gives an error for each; it does not panic.
            let obj: IPersistStorage = Drawing::new().into();
            for s in [&stg, &other, &bad, &big] {
                // SAFETY: COM calls on live objects.
                assert!(unsafe { obj.Load(s) }.is_err());
            }
        });
    }

    #[test]
    fn the_object_gives_its_picture_and_storage() {
        ole(|| {
            let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="72pt" height="36pt" viewBox="0 0 72 36"><path d="M1 1H71V2H1Z"/></svg>"#;
            let emf = crate::vector::make_emf(&crate::export::tree(svg).unwrap(), Some("<CDXML/>"), None);
            let d = windows_core::ComObject::new(Drawing::new());
            d.picture(emf.clone(), true);
            *d.oct.borrow_mut() = OCT.into();
            let data: IDataObject = d.to_interface();
            let ole: IOleObject = d.to_interface();
            // SAFETY: COM calls on live objects; each medium is released.
            unsafe {
                assert_eq!(ole.GetExtent(DVASPECT_CONTENT).unwrap(), SIZE { cx: 2540, cy: 1270 });
                // Word's size is taken and given back; the picture is not changed. A bad size is refused.
                ole.SetExtent(DVASPECT_CONTENT, &SIZE { cx: 5080, cy: 2540 }).unwrap();
                assert_eq!(ole.GetExtent(DVASPECT_CONTENT).unwrap(), SIZE { cx: 5080, cy: 2540 });
                assert!(ole.SetExtent(DVASPECT_CONTENT, &SIZE { cx: 0, cy: 1 }).is_err());
                assert!(ole.SetExtent(DVASPECT_CONTENT, &SIZE { cx: super::super::MAX_EXTENT + 1, cy: 1 }).is_err());
                let mut m = data.GetData(&formatetc(CF_ENHMETAFILE.0, TYMED_ENHMF.0)).unwrap();
                let n = windows::Win32::Graphics::Gdi::GetEnhMetaFileBits(m.u.hEnhMetaFile, None) as usize;
                assert_eq!(n, emf.len(), "the EMF as Copy makes it, CDXML comment and all");
                windows::Win32::System::Ole::ReleaseStgMedium(&mut m);
                let mut m = data.GetData(&formatetc(CF_METAFILEPICT.0, TYMED_MFPICT.0)).unwrap();
                windows::Win32::System::Ole::ReleaseStgMedium(&mut m);
                let mut m = data.GetData(&formatetc(registered(super::super::EMBED_SOURCE), TYMED_ISTORAGE.0)).unwrap();
                let stg = m.u.pstg.as_ref().cloned().unwrap();
                assert_eq!(read_storage(&stg).as_deref(), Ok(OCT));
                windows::Win32::System::Ole::ReleaseStgMedium(&mut m);
                assert_eq!(data.QueryGetData(&formatetc(CF_ENHMETAFILE.0, TYMED_HGLOBAL.0)), DV_E_TYMED);
                assert_eq!(data.QueryGetData(&formatetc(2, TYMED_HGLOBAL.0)), DV_E_FORMATETC);
                let e = data.EnumFormatEtc(DATADIR_GET.0 as u32).unwrap();
                let mut got = [FORMATETC::default(); 4];
                let mut n = 0;
                let _ = e.Next(&mut got, Some(&mut n));
                assert_eq!(n, 3);
            }
            // A new object has no picture yet.
            let fresh: IDataObject = Drawing::new().into();
            // SAFETY: as above.
            assert_eq!(unsafe { fresh.QueryGetData(&formatetc(CF_ENHMETAFILE.0, TYMED_ENHMF.0)) }, OLE_E_BLANK);
        });
    }

    // The clipboard's data object: the object first, then 0011's formats in order, and "Embed Source" holds the drawing.
    #[test]
    fn the_copy_puts_the_object_first() {
        ole(|| {
            let types = vec![(CF_ENHMETAFILE.0, crate::clipboard::ENHMETAFILE, b"x".to_vec()), (registered("SMILES"), "SMILES", b"CO\0".to_vec())];
            let data = clip_object(&types, OCT.into());
            // SAFETY: COM calls on live objects.
            unsafe {
                let e = data.EnumFormatEtc(DATADIR_GET.0 as u32).unwrap();
                let mut got = [FORMATETC::default(); 8];
                let mut n = 0;
                let _ = e.Next(&mut got, Some(&mut n));
                let cfs: Vec<u16> = got[..n as usize].iter().map(|f| f.cfFormat).collect();
                assert_eq!(cfs, [registered("Embed Source"), registered("Object Descriptor"), CF_ENHMETAFILE.0, registered("SMILES")]);
                let mut m = data.GetData(&formatetc(registered("Embed Source"), TYMED_ISTORAGE.0)).unwrap();
                assert_eq!(read_storage(m.u.pstg.as_ref().unwrap()).as_deref(), Ok(OCT));
                windows::Win32::System::Ole::ReleaseStgMedium(&mut m);
            }
        });
    }

    // Paste reads Octet's own object back from the flattened compound file the Windows clipboard holds.
    #[test]
    fn paste_reads_octets_object() {
        let flat = ole(|| {
            // SAFETY: an in-memory compound file; its bytes are copied out of the HGLOBAL while locked.
            unsafe {
                let b = CreateILockBytesOnHGlobal(None, false).unwrap();
                let stg = StgCreateDocfileOnILockBytes(&b, STGM_CREATE | STGM_READWRITE | STGM_SHARE_EXCLUSIVE, 0).unwrap();
                write_storage(&stg, OCT, (100, 100)).unwrap();
                stg.Commit(0).unwrap();
                drop(stg);
                let h = windows::Win32::System::Com::StructuredStorage::GetHGlobalFromILockBytes(&b).unwrap();
                let n = windows::Win32::System::Memory::GlobalSize(h);
                let p = GlobalLock(h).cast::<u8>();
                let out = std::slice::from_raw_parts(p, n).to_vec();
                let _ = GlobalUnlock(h);
                drop(b);
                let _ = GlobalFree(Some(h));
                out
            }
        });
        assert_eq!(oct_from_embed_source(&flat).as_deref(), Some(OCT));
        assert_eq!(oct_from_embed_source(b"not a compound file"), None);
        assert_eq!(oct_from_embed_source(&[]), None);
    }
}
