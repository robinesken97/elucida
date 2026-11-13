// Octet drawings as objects in Office for Windows (decision 0023, issue 24). Octet is a local OLE server: Word keeps
// an "Octet Drawing" object in the document, with Octet's EMF as its picture and the drawing as a .oct file in its
// storage, and double-click opens the drawing in an Octet window.
//
// This file holds the parts that are only data: the class's names, the registry keys, the Object Descriptor's bytes,
// the clipboard's formats and order, the size of the picture, and the limits on what an object's storage gives. They
// build and are tested on every system. The COM server, the registry and the OLE clipboard are in ole_windows.rs,
// which builds on Windows only. Nothing here changes what Octet does on the Mac or Linux.
#![cfg_attr(not(windows), allow(dead_code))]

use std::path::{Path, PathBuf};

// The COM server, the registry and the OLE clipboard.
#[cfg(windows)]
#[path = "ole_windows.rs"]
pub mod win;

// The class. Made once on 5 November 2026 and never changed: every document with an Octet object keeps it.
pub const CLSID: &str = "{211EF98F-E45E-42C8-9D49-A10D2D394DB2}";
pub const CLSID_FIELDS: (u32, u16, u16, [u8; 8]) = (0x211E_F98F, 0xE45E, 0x42C8, [0x9D, 0x49, 0xA1, 0x0D, 0x2D, 0x39, 0x4D, 0xB2]);
pub const PROGID: &str = "OctetDraw.Drawing";
pub const PROGID_1: &str = "OctetDraw.Drawing.1";
// What Office calls the object (Insert > Object, the context menu), and the program's short name (AuxUserType\3).
pub const NAME: &str = "Octet Drawing";
pub const APP: &str = "Octet Draw";
// The .oct file type's ProgID, as Tauri's installer writes it (the file association's name in tauri.conf.json). A
// CLSID under it lets Insert > Object > Create from File make an Octet Drawing from a .oct file (GetClassFile).
pub const OCT_TYPE: &str = "Octet Drawing";
// The streams Octet writes in an object's storage, and the only ones it reads: the drawing as a .oct file in UTF-8,
// and the picture's size in HIMETRIC (two little-endian i32s, width then height, 8 bytes), so GetExtent has the size
// from Load on, before the window sends a picture.
pub const STREAM: &str = "Octet";
pub const SIZE_STREAM: &str = "OctetSize";
// The largest width or height Octet takes from a storage or a container: 10 m, in hundredths of a millimetre.
pub const MAX_EXTENT: i32 = 1_000_000;
// OLEMISC_CANTLINKINSIDE (0x10) and OLEMISC_RENDERINGISDEVICEINDEPENDENT (0x200): no links into the object, and one
// picture for every device. No in-place editing, so no OLEMISC_INSIDEOUT or ACTIVATEWHENVISIBLE.
// https://learn.microsoft.com/windows/win32/api/oleidl/ne-oleidl-olemisc
pub const MISC_STATUS: u32 = 0x10 | 0x200;
// The OLE clipboard formats Octet puts first: the object's storage and its description.
// https://learn.microsoft.com/windows/win32/com/clipboard-formats (CF_EMBEDSOURCE, CF_OBJECTDESCRIPTOR)
pub const EMBED_SOURCE: &str = "Embed Source";
pub const OBJECT_DESCRIPTOR: &str = "Object Descriptor";
// What a container (Word) puts on the clipboard when it copies an object it holds: the object's storage, as "Embed
// Source" is. Paste reads either. https://learn.microsoft.com/windows/win32/com/clipboard-formats (CF_EMBEDDEDOBJECT)
pub const EMBEDDED_OBJECT: &str = "Embedded Object";
// The largest drawing an object holds, as for a file Octet opens.
pub const MAX_STREAM: u64 = crate::MAX_BYTES;
// A new object's size before it has a picture (1 in by 1 in, in hundredths of a millimetre).
pub const BLANK_EXTENT: (i32, i32) = (2540, 2540);
// The longest container or document name Octet keeps (SetHostNames), in characters.
const MAX_HOST: usize = 260;

// One registry value under HKEY_CURRENT_USER\Software\Classes: the key, the value's name ("" for the key's default
// value) and its text. A value of None makes the key with no value (Insertable).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub key: String,
    pub name: &'static str,
    pub value: Option<String>,
}

fn entry(key: impl Into<String>, name: &'static str, value: Option<&str>) -> Entry {
    Entry { key: key.into(), name, value: value.map(str::to_string) }
}

// Every key and value for the class, for Octet at `exe`, in the order they are written. The NSIS installer
// (src-tauri/windows/hooks.nsh) writes the same list; `keys_match_the_installer` checks that they agree.
// https://learn.microsoft.com/windows/win32/com/localserver32, https://learn.microsoft.com/windows/win32/com/inprochandler32,
// https://learn.microsoft.com/windows/win32/com/insertable, https://learn.microsoft.com/windows/win32/com/verb,
// https://learn.microsoft.com/windows/win32/com/auxusertype, https://learn.microsoft.com/windows/win32/com/miscstatus
pub fn keys(exe: &Path) -> Vec<Entry> {
    let exe = exe.to_string_lossy();
    let clsid = format!("CLSID\\{CLSID}");
    let server = format!("\"{exe}\"");
    // DefaultIcon has no quotes: OLE splits it at the last comma and passes the path to ExtractIcon as it is.
    // https://learn.microsoft.com/windows/win32/com/defaulticon
    let icon = format!("{exe},0");
    let misc = MISC_STATUS.to_string();
    vec![
        entry(PROGID, "", Some(NAME)),
        entry(format!("{PROGID}\\CLSID"), "", Some(CLSID)),
        entry(format!("{PROGID}\\CurVer"), "", Some(PROGID_1)),
        entry(format!("{PROGID}\\Insertable"), "", None),
        entry(PROGID_1, "", Some(NAME)),
        entry(format!("{PROGID_1}\\CLSID"), "", Some(CLSID)),
        entry(format!("{PROGID_1}\\Insertable"), "", None),
        entry(clsid.clone(), "", Some(NAME)),
        entry(format!("{clsid}\\LocalServer32"), "", Some(&server)),
        entry(format!("{clsid}\\InprocHandler32"), "", Some("ole32.dll")),
        entry(format!("{clsid}\\ProgID"), "", Some(PROGID_1)),
        entry(format!("{clsid}\\VersionIndependentProgID"), "", Some(PROGID)),
        entry(format!("{clsid}\\Insertable"), "", None),
        entry(format!("{clsid}\\DefaultIcon"), "", Some(&icon)),
        entry(format!("{clsid}\\AuxUserType\\2"), "", Some(NAME)),
        entry(format!("{clsid}\\AuxUserType\\3"), "", Some(APP)),
        entry(format!("{clsid}\\MiscStatus"), "", Some(&misc)),
        // Verb n: its menu text, then MF_ flags (0) and OLEVERBATTRIB_ONCONTAINERMENU (2).
        entry(format!("{clsid}\\Verb\\0"), "", Some("&Edit,0,2")),
        entry(format!("{clsid}\\Verb\\1"), "", Some("&Open,0,2")),
        entry(format!("{OCT_TYPE}\\CLSID"), "", Some(CLSID)),
    ]
}

// The keys Octet removes (the uninstaller, and Octet's own tests), each with everything under it. The .oct type's
// CLSID goes too; the installer removes the .oct type itself.
pub fn roots() -> Vec<String> {
    vec![PROGID.into(), PROGID_1.into(), format!("CLSID\\{CLSID}"), format!("{OCT_TYPE}\\CLSID")]
}

// The program a LocalServer32 value names: the path in quotes, or up to the first space after ".exe".
pub fn server_path(value: &str) -> Option<PathBuf> {
    let v = value.trim();
    let path = if let Some(rest) = v.strip_prefix('"') {
        &rest[..rest.find('"')?]
    } else {
        let lower = v.to_ascii_lowercase();
        lower.find(".exe").map_or(v, |k| &v[..k + 4])
    };
    (!path.is_empty()).then(|| PathBuf::from(path))
}

// What a release build does with the keys when it starts.
#[derive(Debug, PartialEq, Eq)]
pub enum Repair {
    Write, // missing, or this Octet's (written again, so a key that went is back), or naming a program that is gone
    Leave, // another Octet that exists (a second install, a portable copy): never taken over
}

// `registered`: what LocalServer32 says now, if anything. `me`: this program. Windows paths compare without case.
pub fn repair(registered: Option<&str>, me: &Path, exists: impl Fn(&Path) -> bool) -> Repair {
    let Some(other) = registered.and_then(server_path) else { return Repair::Write };
    let same = other.to_string_lossy().eq_ignore_ascii_case(&me.to_string_lossy());
    if same || !exists(&other) { Repair::Write } else { Repair::Leave }
}

// Windows starts a local server with -Embedding (or /Embedding) when Word needs one. Octet then opens no Home window
// and gives none of its arguments to open::from_args.
// https://learn.microsoft.com/windows/win32/com/localserver32 ("-Embedding")
pub fn is_embedding_arg(arg: &str) -> bool {
    arg.eq_ignore_ascii_case("-embedding") || arg.eq_ignore_ascii_case("/embedding")
}

pub fn embedding<I: IntoIterator<Item = std::ffi::OsString>>(args: I) -> bool {
    args.into_iter().skip(1).any(|a| is_embedding_arg(&a.to_string_lossy()))
}

// The picture's size in hundredths of a millimetre (HIMETRIC), from the EMF header's frame (rclFrame, already in
// 0.01 mm). This is the size GetExtent and the Object Descriptor give. None if the bytes are not an EMF.
// https://learn.microsoft.com/openspecs/windows_protocols/ms-emf/de081ec1-3a0f-4c24-a389-4e6a5fd3e5ff (EMR_HEADER)
pub fn extent(emf: &[u8]) -> Option<(i32, i32)> {
    let i32_at = |k: usize| emf.get(k..k + 4).map(|b| i32::from_le_bytes([b[0], b[1], b[2], b[3]]));
    if emf.get(40..44)? != b" EMF" || i32_at(0)? != 1 {
        return None;
    }
    let (l, t, r, b) = (i32_at(24)?, i32_at(28)?, i32_at(32)?, i32_at(36)?);
    let (w, h) = (r.checked_sub(l)?, b.checked_sub(t)?);
    (w > 0 && h > 0).then_some((w, h))
}

pub fn valid_extent((w, h): (i32, i32)) -> bool {
    (1..=MAX_EXTENT).contains(&w) && (1..=MAX_EXTENT).contains(&h)
}

// The size stream's bytes, and back. Anything but exactly 8 bytes with a valid size is refused.
pub fn size_bytes((w, h): (i32, i32)) -> [u8; 8] {
    let mut out = [0u8; 8];
    out[..4].copy_from_slice(&w.to_le_bytes());
    out[4..].copy_from_slice(&h.to_le_bytes());
    out
}

pub fn read_size(bytes: &[u8]) -> Option<(i32, i32)> {
    let b: &[u8; 8] = bytes.try_into().ok()?;
    let size = (i32::from_le_bytes([b[0], b[1], b[2], b[3]]), i32::from_le_bytes([b[4], b[5], b[6], b[7]]));
    valid_extent(size).then_some(size)
}

// The drawing's size from the .oct file, for a storage with no size stream (or a bad one): the BoundingBox of the
// root CDXML element, in points, as HIMETRIC. Only the root element's start tag is read, at most 64 KB into the text.
pub fn extent_from_oct(oct: &str) -> Option<(i32, i32)> {
    let head = &oct.as_bytes()[..oct.len().min(64 << 10)];
    let at = head.windows(7).position(|w| w.starts_with(b"<CDXML") && (w[6].is_ascii_whitespace() || w[6] == b'>'))?;
    let tag = &head[at..];
    let tag = &tag[..tag.iter().position(|&c| c == b'>')?];
    let key = tag.windows(14).position(|w| w[0].is_ascii_whitespace() && &w[1..] == b"BoundingBox=\"")?;
    let rest = &tag[key + 14..];
    let value = std::str::from_utf8(&rest[..rest.iter().position(|&c| c == b'"')?]).ok()?;
    let n: Vec<f64> = value.split_ascii_whitespace().map(str::parse).collect::<Result<_, _>>().ok()?;
    let [l, t, r, b] = n[..] else { return None };
    let himetric = |pt: f64| (pt * 2540.0 / 72.0).round();
    let (w, h) = (himetric(r - l), himetric(b - t));
    if !(w.is_finite() && h.is_finite()) || w < 1.0 || h < 1.0 || w > MAX_EXTENT as f64 || h > MAX_EXTENT as f64 {
        return None;
    }
    Some((w as i32, h as i32))
}

// A loaded object's size: the size stream, else the drawing's own size, else 1 in by 1 in. Never blank.
pub fn loaded_extent(stream: Option<&[u8]>, oct: &str) -> (i32, i32) {
    stream.and_then(read_size).or_else(|| extent_from_oct(oct)).unwrap_or(BLANK_EXTENT)
}

fn utf16z(s: &str) -> Vec<u8> {
    s.encode_utf16().chain([0]).flat_map(u16::to_le_bytes).collect()
}

pub fn clsid_bytes() -> [u8; 16] {
    let (a, b, c, d) = CLSID_FIELDS;
    let mut out = [0u8; 16];
    out[..4].copy_from_slice(&a.to_le_bytes());
    out[4..6].copy_from_slice(&b.to_le_bytes());
    out[6..8].copy_from_slice(&c.to_le_bytes());
    out[8..].copy_from_slice(&d);
    out
}

// The "Object Descriptor" clipboard format: an OBJECTDESCRIPTOR (52 bytes) and then its two strings in UTF-16, the
// full name "Octet Drawing" and the source "Octet Draw", each at its offset from the start. Size in HIMETRIC; the
// aspect is the content (DVASPECT_CONTENT, 1); no offset to the drag point.
// https://learn.microsoft.com/windows/win32/api/oleidl/ns-oleidl-objectdescriptor
pub fn object_descriptor(size: (i32, i32)) -> Vec<u8> {
    let (name, source) = (utf16z(NAME), utf16z(APP));
    let head = 52u32;
    let total = head + name.len() as u32 + source.len() as u32;
    let mut out = Vec::with_capacity(total as usize);
    out.extend_from_slice(&total.to_le_bytes());
    out.extend_from_slice(&clsid_bytes());
    out.extend_from_slice(&1u32.to_le_bytes());
    out.extend_from_slice(&size.0.to_le_bytes());
    out.extend_from_slice(&size.1.to_le_bytes());
    out.extend_from_slice(&[0; 8]);
    out.extend_from_slice(&MISC_STATUS.to_le_bytes());
    out.extend_from_slice(&head.to_le_bytes());
    out.extend_from_slice(&(head + name.len() as u32).to_le_bytes());
    out.extend_from_slice(&name);
    out.extend_from_slice(&source);
    out
}

// The clipboard's formats in order: the object first, so Word's paste makes the object (as ChemDraw's copy does),
// then exactly the formats decision 0011 lists, in its order. Without the object, the list is 0011's.
pub fn clipboard_order<'a>(object: bool, rest: &[&'a str]) -> Vec<&'a str> {
    let mut out: Vec<&'a str> = if object { vec![EMBED_SOURCE, OBJECT_DESCRIPTOR] } else { Vec::new() };
    out.extend_from_slice(rest);
    out
}

// Why an object cannot be read. Each gives the same message to the user.
#[derive(Debug, PartialEq, Eq)]
pub enum Refused {
    WrongClass,
    NoStream,
    TooLarge,
    SizeDiffers,
    NotText,
    Failed,
}
pub const CANNOT_OPEN: &str = "Octet cannot open this object.";

// The drawing from an object's stream, with Open's limits. `stated`: the size the stream gives (IStream::Stat).
// `read` fills the buffer it is given and says how many bytes it gave (0 at the end). Reading stops at 64 MB and one
// byte whatever the stream said, and the bytes must be the size stated and UTF-8. An empty stream is a new empty
// drawing (an object saved before anything was drawn).
pub fn read_stream(stated: u64, mut read: impl FnMut(&mut [u8]) -> Result<usize, ()>) -> Result<String, Refused> {
    if stated > MAX_STREAM {
        return Err(Refused::TooLarge);
    }
    let mut out = Vec::with_capacity(stated as usize);
    let mut buf = vec![0u8; 64 << 10];
    loop {
        let n = read(&mut buf).map_err(|_| Refused::Failed)?;
        if n == 0 {
            break;
        }
        let n = n.min(buf.len());
        out.extend_from_slice(&buf[..n]);
        if out.len() as u64 > MAX_STREAM {
            return Err(Refused::TooLarge);
        }
        if out.len() as u64 > stated {
            return Err(Refused::SizeDiffers);
        }
    }
    if out.len() as u64 != stated {
        return Err(Refused::SizeDiffers);
    }
    String::from_utf8(out).map_err(|_| Refused::NotText)
}

// The container's and the document's names from SetHostNames, as the window's title takes them: no control
// characters, 260 characters at most, and "Document" when the container gives none.
pub fn host_name(name: &str) -> String {
    let clean = program_name(name);
    if clean.is_empty() { "Document".into() } else { clean }
}

// The program's name for the Update button (Update in Word), cleaned as host_name cleans a document's name. Empty when
// there is none: the button then names the document.
pub fn program_name(name: &str) -> String {
    name.chars().filter(|c| !c.is_control()).take(MAX_HOST).collect::<String>().trim().into()
}

// The object window's title, as Windows' guidelines for objects opened in a window give it.
pub fn title(document: &str, closed: bool) -> String {
    if closed { format!("{NAME} ({document} is closed)") } else { format!("{NAME} in {document}") }
}

// IOleObject::DoVerb: what a verb does. Edit (0, the primary verb), Open (1), OLEIVERB_SHOW (-1) and OLEIVERB_OPEN
// (-2) open the window; OLEIVERB_HIDE (-3) hides it. Octet has no in-place editing, so OLEIVERB_UIACTIVATE (-4) and
// OLEIVERB_INPLACEACTIVATE (-5) are not supported. A positive verb Octet does not have does the primary verb, as the
// documentation asks. https://learn.microsoft.com/windows/win32/api/oleidl/nf-oleidl-ioleobject-doverb
#[derive(Debug, PartialEq, Eq)]
pub enum Verb {
    Open,
    Hide,
    Nothing,     // OLEIVERB_DISCARDUNDOSTATE (-6): no undo state to discard
    Unknown,     // a positive verb Octet does not have: the primary verb, and OLEOBJ_S_INVALIDVERB
    NotSupported, // in-place verbs and other negative verbs: E_NOTIMPL
}

pub fn verb(v: i32) -> Verb {
    match v {
        0 | 1 | -1 | -2 => Verb::Open,
        -3 => Verb::Hide,
        -6 => Verb::Nothing,
        v if v > 1 => Verb::Unknown,
        _ => Verb::NotSupported,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_class_id_is_fixed() {
        // The text and the bytes are the same GUID: Data1, Data2 and Data3 little-endian, then Data4 as it is.
        let hex: String = CLSID.chars().filter(char::is_ascii_hexdigit).collect();
        let (a, b, c, d) = CLSID_FIELDS;
        assert_eq!(hex, format!("{a:08X}{b:04X}{c:04X}{}", d.iter().map(|x| format!("{x:02X}")).collect::<String>()));
        assert_eq!(&clsid_bytes()[..4], &[0x8F, 0xF9, 0x1E, 0x21]);
        assert_eq!(CLSID, "{211EF98F-E45E-42C8-9D49-A10D2D394DB2}", "documents keep this class for ever");
    }

    #[test]
    fn registry_keys_for_the_class() {
        let k = keys(Path::new(r"C:\Users\sam\AppData\Local\Octet Draw\octet.exe"));
        let get = |key: &str| k.iter().find(|e| e.key == key).map(|e| e.value.clone());
        assert_eq!(get("OctetDraw.Drawing"), Some(Some("Octet Drawing".into())));
        assert_eq!(get("OctetDraw.Drawing\\CurVer"), Some(Some("OctetDraw.Drawing.1".into())));
        assert_eq!(get("OctetDraw.Drawing.1\\Insertable"), Some(None));
        let c = format!("CLSID\\{CLSID}");
        assert_eq!(get(&format!("{c}\\LocalServer32")), Some(Some(r#""C:\Users\sam\AppData\Local\Octet Draw\octet.exe""#.into())), "the program in quotes, with no arguments");
        assert_eq!(get(&format!("{c}\\InprocHandler32")), Some(Some("ole32.dll".into())));
        assert_eq!(get(&format!("{c}\\MiscStatus")), Some(Some("528".into())));
        assert_eq!(get(&format!("{c}\\Verb\\0")), Some(Some("&Edit,0,2".into())));
        assert_eq!(get(&format!("{c}\\Verb\\1")), Some(Some("&Open,0,2".into())));
        assert_eq!(get(&format!("{c}\\AuxUserType\\2")), Some(Some("Octet Drawing".into())));
        assert_eq!(get("Octet Drawing\\CLSID"), Some(Some(CLSID.into())));
        // Every key is under one of the roots the uninstaller removes, and nothing names HKLM, an AppID or DCOM.
        let roots = roots();
        assert!(k.iter().all(|e| roots.iter().any(|r| e.key == *r || e.key.starts_with(&format!("{r}\\")))));
        assert!(k.iter().all(|e| !e.key.contains("AppID") && !e.key.contains("HKEY")));
    }

    // The installer's hooks write the same keys as Octet's own repair, and remove the same roots.
    #[test]
    fn keys_match_the_installer() {
        // Git on Windows checks the file out with CRLF line ends.
        let nsh = &include_str!("../windows/hooks.nsh").replace("\r\n", "\n");
        for e in keys(Path::new(r"$INSTDIR\${MAINBINARYNAME}.exe")) {
            let key = e.key.replace(CLSID, "${OCTET_CLSID}");
            let line = match &e.value {
                Some(v) => format!("WriteRegStr HKCU \"Software\\Classes\\{key}\" \"{}\" '{}'", e.name, v.replace(CLSID, "${OCTET_CLSID}")),
                None => format!("WriteRegStr HKCU \"Software\\Classes\\{key}\" \"\" \"\""),
            };
            assert!(nsh.contains(&line), "the installer lacks: {line}");
        }
        for r in roots() {
            let line = format!("DeleteRegKey HKCU \"Software\\Classes\\{}\"", r.replace(CLSID, "${OCTET_CLSID}"));
            assert!(nsh.contains(&line), "the uninstaller lacks: {line}");
        }
        assert!(nsh.contains(&format!("!define OCTET_CLSID \"{CLSID}\"")));
        // The installer is 32-bit: both hooks set the 64-bit view, then the 32-bit one, then put the view back.
        let views = "    SetRegView 64\n    !insertmacro OCTET_OLE_REMOVE\n    SetRegView 32\n    !insertmacro OCTET_OLE_REMOVE\n    SetRegView default\n";
        assert!(nsh.contains("  SetRegView 64\n  !insertmacro OCTET_OLE_KEYS\n  SetRegView 32\n  !insertmacro OCTET_OLE_KEYS\n  SetRegView default\n"), "install writes both views");
        assert!(nsh.contains(views), "uninstall removes both views");
        assert_eq!(nsh.matches("WriteRegStr").count(), keys(Path::new("x")).len(), "every key is written once per view, through the macro");
    }

    #[test]
    fn repair_never_takes_another_octets_keys() {
        let me = Path::new(r"C:\Users\sam\AppData\Local\Octet Draw\octet.exe");
        let there = |_: &Path| true;
        let gone = |_: &Path| false;
        assert_eq!(repair(None, me, there), Repair::Write);
        assert_eq!(repair(Some(r#""C:\USERS\SAM\APPDATA\LOCAL\OCTET DRAW\OCTET.EXE""#), me, there), Repair::Write, "this Octet, in another case");
        assert_eq!(repair(Some(r#""D:\Portable\octet.exe""#), me, there), Repair::Leave);
        assert_eq!(repair(Some(r#""D:\Portable\octet.exe""#), me, gone), Repair::Write);
        assert_eq!(repair(Some(""), me, there), Repair::Write);
        assert_eq!(server_path(r"C:\Program Files\Octet Draw\octet.exe -Embedding"), Some(PathBuf::from(r"C:\Program Files\Octet Draw\octet.exe")));
        assert_eq!(server_path(r#""C:\a b\octet.exe" /Automation"#), Some(PathBuf::from(r"C:\a b\octet.exe")));
        assert_eq!(server_path(r#""unclosed"#), None);
    }

    #[test]
    fn embedding_launches() {
        let args = |a: &[&str]| a.iter().map(std::ffi::OsString::from).collect::<Vec<_>>();
        assert!(embedding(args(&["octet.exe", "-Embedding"])));
        assert!(embedding(args(&["octet.exe", "/Embedding"])));
        assert!(embedding(args(&["octet.exe", "-embedding"])));
        assert!(!embedding(args(&["octet.exe", "aspirin.oct"])));
        assert!(!embedding(args(&["-Embedding"])), "the program's own path is not an argument");
    }

    #[test]
    fn object_descriptor_bytes() {
        let d = object_descriptor((1983, 1289));
        let u32_at = |k: usize| u32::from_le_bytes(d[k..k + 4].try_into().unwrap());
        assert_eq!(u32_at(0) as usize, d.len(), "cbSize is the whole block");
        assert_eq!(&d[4..20], &clsid_bytes());
        assert_eq!(u32_at(20), 1, "DVASPECT_CONTENT");
        assert_eq!((u32_at(24), u32_at(28)), (1983, 1289), "the size in HIMETRIC");
        assert_eq!((u32_at(32), u32_at(36)), (0, 0));
        assert_eq!(u32_at(40), MISC_STATUS);
        let text = |k: usize| {
            let units: Vec<u16> = d[k..].chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).take_while(|&u| u != 0).collect();
            String::from_utf16(&units).unwrap()
        };
        assert_eq!(text(u32_at(44) as usize), "Octet Drawing");
        assert_eq!(text(u32_at(48) as usize), "Octet Draw");
        assert_eq!(d.len(), 52 + 2 * 14 + 2 * 11);
    }

    #[test]
    fn extent_is_the_emf_frame() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="72pt" height="36pt" viewBox="0 0 72 36"><path d="M1 1H71V2H1Z"/></svg>"#;
        let emf = crate::vector::make_emf(&crate::export::tree(svg).unwrap(), Some("<CDXML/>"), None);
        assert_eq!(extent(&emf), Some((2540, 1270)), "1 in by 0.5 in");
        assert_eq!(extent(b"not a metafile"), None);
        let mut bad = emf.clone();
        bad[32..36].copy_from_slice(&(-5i32).to_le_bytes());
        assert_eq!(extent(&bad), None, "a frame with no width");
    }

    #[test]
    fn clipboard_puts_the_object_first() {
        let rest = ["CF_ENHMETAFILE", "CF_DIB", "ChemDraw Interchange Format", "CDXML", "MDLCT", "SMILES", "application/x-octet+json"];
        assert_eq!(clipboard_order(true, &rest), [&["Embed Source", "Object Descriptor"][..], &rest[..]].concat());
        assert_eq!(clipboard_order(false, &rest), rest, "switched off: 1.1.1's list");
    }

    // R13: what an object's storage gives is hostile. A reader over bytes, in pieces of `step`.
    fn reader(bytes: Vec<u8>, step: usize) -> impl FnMut(&mut [u8]) -> Result<usize, ()> {
        let mut at = 0;
        move |buf: &mut [u8]| {
            let n = step.min(buf.len()).min(bytes.len() - at);
            buf[..n].copy_from_slice(&bytes[at..at + n]);
            at += n;
            Ok(n)
        }
    }

    #[test]
    fn hostile_streams_are_refused() {
        let oct = "<?xml version=\"1.0\"?><CDXML/>";
        assert_eq!(read_stream(oct.len() as u64, reader(oct.into(), 7)).as_deref(), Ok(oct));
        assert_eq!(read_stream(0, reader(Vec::new(), 7)).as_deref(), Ok(""), "an empty object is a new drawing");
        assert_eq!(read_stream(MAX_STREAM + 1, reader(Vec::new(), 7)), Err(Refused::TooLarge), "65 MB stated");
        assert_eq!(read_stream(4, reader(b"<CDXML/>".to_vec(), 3)), Err(Refused::SizeDiffers), "more than it said");
        assert_eq!(read_stream(40, reader(b"<CDXML/>".to_vec(), 3)), Err(Refused::SizeDiffers), "less than it said");
        assert_eq!(read_stream(3, reader(vec![0xff, 0xfe, 0x00], 3)), Err(Refused::NotText));
        assert_eq!(read_stream(3, |_| Err(())), Err(Refused::Failed));
        // A stream that says it is small and never ends stops at the limit.
        let mut endless = |buf: &mut [u8]| Ok(buf.len());
        assert!(matches!(read_stream(MAX_STREAM, &mut endless), Err(Refused::TooLarge)));
        // A reader that claims more than the buffer it was given cannot overrun it.
        assert_eq!(read_stream(2, |buf: &mut [u8]| { buf[0] = b'a'; Ok(usize::MAX) }), Err(Refused::SizeDiffers));
    }

    #[test]
    fn the_size_stream_and_its_fallbacks() {
        assert_eq!(read_size(&size_bytes((1983, 1289))), Some((1983, 1289)));
        assert_eq!(read_size(&[1, 2, 3]), None, "not 8 bytes");
        assert_eq!(read_size(&[0; 9]), None);
        assert_eq!(read_size(&size_bytes((0, 100))), None, "no width");
        assert_eq!(read_size(&size_bytes((-5, 100))), None);
        assert_eq!(read_size(&size_bytes((MAX_EXTENT + 1, 100))), None, "larger than 10 m");
        let oct = "<?xml version=\"1.0\"?>\n<!DOCTYPE CDXML SYSTEM \"x\">\n<CDXML\n CreationProgram=\"Octet\" BoundingBox=\"10 20 82 56\" Name=\"a\"><page BoundingBox=\"0 0 540 720\"/></CDXML>";
        assert_eq!(extent_from_oct(oct), Some((2540, 1270)), "72 pt by 36 pt");
        assert_eq!(extent_from_oct("<CDXML><page BoundingBox=\"0 0 540 720\"/></CDXML>"), None, "only the root's box");
        assert_eq!(extent_from_oct("<CDXML BoundingBox=\"0 0 0 0\"/>"), None, "an empty drawing");
        assert_eq!(extent_from_oct("<CDXML BoundingBox=\"0 0 1e30 5\"/>"), None);
        assert_eq!(extent_from_oct("<CDXML BoundingBox=\"0 0 NaN 5\"/>"), None);
        assert_eq!(extent_from_oct("<CDXMLX BoundingBox=\"0 0 72 72\"/>"), None);
        assert_eq!(extent_from_oct(""), None);
        assert_eq!(loaded_extent(Some(&size_bytes((300, 400))), oct), (300, 400));
        assert_eq!(loaded_extent(Some(b"bad"), oct), (2540, 1270), "a bad stream: the drawing's size");
        assert_eq!(loaded_extent(None, ""), BLANK_EXTENT, "never blank");
    }

    #[test]
    fn titles_and_host_names() {
        assert_eq!(title("Document1", false), "Octet Drawing in Document1");
        assert_eq!(title("Document1", true), "Octet Drawing (Document1 is closed)");
        assert_eq!(host_name("Paper\u{7}.docx"), "Paper.docx");
        assert_eq!(host_name("  "), "Document");
        assert_eq!(host_name(&"x".repeat(1000)).len(), 260);
        assert_eq!(program_name(" Writer\u{7}"), "Writer");
        assert_eq!(program_name("\u{7} "), "", "no name: the button names the document");
    }

    #[test]
    fn verbs() {
        assert_eq!([0, 1, -1, -2].map(verb), [Verb::Open, Verb::Open, Verb::Open, Verb::Open]);
        assert_eq!(verb(-3), Verb::Hide);
        assert_eq!(verb(-4), Verb::NotSupported);
        assert_eq!(verb(-5), Verb::NotSupported);
        assert_eq!(verb(-6), Verb::Nothing);
        assert_eq!(verb(7), Verb::Unknown);
    }
}
