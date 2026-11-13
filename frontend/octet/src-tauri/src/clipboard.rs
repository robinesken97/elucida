// Copy and paste with Word, PowerPoint, Keynote and ChemDraw, as ChemDraw's own clipboard works.
// Copy puts one item holding, in this order: a picture of the selection, ChemDraw's CDX (ChemDraw reads it first, so
// the whole drawing pastes into ChemDraw), CDXML, a molfile, SMILES, and Octet's own JSON for a lossless paste into
// Octet. Settings > Import and export > Copy switches the picture, CDX, CDXML, MOL and SMILES off (REL-19, CH-8);
// Octet's JSON always goes on. No plain text: ChemDraw reads text before pictures and would paste it as a caption,
// and Word pastes text before a picture.
// - macOS: the picture is a vector PDF with the CDXML in its catalog /Metadata (Office keeps it; ChemDraw and Octet
//   read the structure back out of it). The types are ChemDraw's. Before the PDF goes Office's own copy of a picture
//   (a zip, office_package), which Word takes first: its picture file is an EMF with the PDF in a comment and the
//   drawing as vector records, so the picture is sharp in Word for Mac and in Word for Windows. Update in Word
//   (word.rs) gives Word the same two (mac_picture).
// - Windows (REL-3, CH-1): Office for Windows pastes no PDF, so the picture is an EMF (vector, as ChemDraw for Windows
//   puts a metafile), with the CDXML in a comment, and a bitmap for programs that read no metafile. No PNG: Office
//   would take it before the EMF and paste pixels. ChemDraw for Windows puts CDX, the molfile and SMILES on under
//   these names: "ChemDraw Interchange Format", "MDLCT" (a molfile as length-prefixed lines) and "SMILES". It puts no
//   CDXML (issue 23). "CDXML" is ChemDraw JS's name in ChemOffice+, which reads it first. Octet writes and reads it for
//   that.
//   An Octet Drawing object goes first ("Embed Source", "Object Descriptor"), through the OLE clipboard, for Word,
//   PowerPoint and Excel (decision 0023, ole_windows.rs); Settings switches it off.
// - Linux: the picture is a PNG (with the CDXML in a chunk), the Mac's PDF (with the CDXML in it, which LibreOffice
//   keeps, so its Octet extension can open the drawing again) and an SVG. The chemistry has its MIME types
//   (chemical/x-cdx and so on).
//
// The webview keeps a page's own clipboard types in a form of its own and shows a page only text, HTML and URLs from
// other apps, so the page cannot read these types itself: paste calls read_clipboard. Paste also reads a picture (a
// screenshot, a picture copied from a browser): PNG, else the system's bitmap (TIFF on the Mac, the bitmap on Windows).

pub const PDF: &str = "com.adobe.pdf";
// ChemDraw 26.1 declares the Revvity names too (its Info.plist), and the CambridgeSoft names for the same CDX and CDXML
// codes. ChemDraw asks macOS for the name of each code, so the name it reads can be any of them: copy writes and paste
// reads all three.
pub const CDX: [&str; 3] = ["com.perkinelmer.chemdraw.cdx-clipboard", "com.revvity.chemdraw.cdx-clipboard", "com.cambridgesoft.cdx"];
pub const CDXML: [&str; 3] = ["com.perkinelmer.cdxml", "com.revvity.cdxml", "com.cambridgesoft.cdxml"];
pub const MOLFILE: &str = "com.mdli.molfile";
pub const SMILES: &str = "org.opensmiles.smiles";
// Plain text, for Name to Structure (the name field opens with a name copied from elsewhere).
pub const TEXT: &str = "public.utf8-plain-text";
// Octet's own type. A UTI under the app's identifier: macOS refuses MIME-style names such as
// application/x-octet+json on the pasteboard. Windows and Linux use that name.
pub const OCTET: &str = "io.github.samchemman.octet.json";
// A copied file, on the Mac.
pub const FILE_URL: &str = "public.file-url";
// The Windows bitmap and text are standard formats (CF_DIB, CF_UNICODETEXT), not registered names.
pub const DIB: &str = "CF_DIB";
pub const UNICODE_TEXT: &str = "CF_UNICODETEXT";
pub const ENHMETAFILE: &str = "CF_ENHMETAFILE";
// LibreOffice's own copy of a picture on Linux, under its full name.
pub const SVXB: &str = "application/x-openoffice-svxb;windows_formatname=\"SVXB (StarView Bitmap/Animation)\"";

const MAX_TYPE: usize = 64 << 20;
const MAX_TEXT: usize = 64 << 10;
// Office's copy of a picture on the Mac is left out, and the PDF goes alone, when its EMF is larger than this: paste's
// limit for one type, less 64 KB for the zip's other parts, so Octet reads back every copy it makes. For a picture in
// the drawing (a photo, a pasted screenshot) the EMF holds its pixels raw (300 dpi at most, 3 bytes each), the CDXML
// with the picture's file as hex (2 bytes a byte), and the PDF, which holds the file and that CDXML deflated. So it
// is the pixels and about 4 times the file. A 12 MB photo drawn 6 by 4.5 in is about 55 MB.
const MAX_OFFICE: usize = MAX_TYPE - (64 << 10);
// In Office's copy, a part larger than 1 MB is stored, not deflated. That is an EMF with a picture's pixels in it, or
// a very large drawing's: deflating it would take longer than the rest of Copy.
const STORED_OVER: usize = 1 << 20;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum System {
    Mac,
    Windows,
    Linux,
}
pub const HERE: System = if cfg!(target_os = "macos") { System::Mac } else if cfg!(windows) { System::Windows } else { System::Linux };

// What one copy can hold.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Kind {
    Pdf,
    Emf,
    Png,
    Bitmap,
    Svg,
    Cdx,
    Cdxml,
    Molfile,
    Smiles,
    Octet,
    Text,
    FileUrl, // read only: a copied file, for a spectrum (spectrum.rs) or a picture with a drawing in it
    Office,  // Office's own copy of a picture, a zip with the picture's file in it: read (cdxml_from_office), and written on the Mac (office_package)
    Keynote, // read only: Keynote's copy keeps the picture's file under a numbered type (com.apple.iWork.TSPData.364)
    Object,  // read only: an Octet Drawing object copied out of Word ("Embed Source", Windows only, decision 0023)
    Svxb,    // read only: LibreOffice's own copy of a picture, which holds the picture's file (svxb_picture)
}

// Each system's names for a kind, in the order copy writes them; paste reads the first one there. Empty: that system's
// clipboard does not have the kind.
fn names(s: System, k: Kind) -> &'static [&'static str] {
    use Kind::*;
    match s {
        System::Mac => match k {
            Pdf => &[PDF],
            Cdx => &CDX,
            Cdxml => &CDXML,
            Molfile => &[MOLFILE],
            Smiles => &[SMILES],
            Octet => &[OCTET],
            Text => &[TEXT],
            // Read only: copy's picture on the Mac is Office's copy and a PDF.
            Png => &["public.png"],
            Bitmap => &["public.tiff"],
            FileUrl => &[FILE_URL],
            Office => &["com.microsoft.Art--GVML-ClipFormat"],
            Object | Svxb => &[],
            // A prefix: mac::read gives the first such type that holds a PDF.
            Keynote => &["com.apple.iWork.TSPData."],
            Svg | Emf => &[],
        },
        System::Windows => match k {
            Emf => &[ENHMETAFILE],
            Png => &["PNG"],
            Bitmap => &[DIB],
            Cdx => &["ChemDraw Interchange Format"],
            Cdxml => &["CDXML"],
            Molfile => &["MDLCT"],
            Smiles => &["SMILES"],
            Octet => &["application/x-octet+json"],
            Text => &[UNICODE_TEXT],
            Office => &["Art::GVML ClipFormat"],
            Object => &[crate::ole::EMBED_SOURCE, crate::ole::EMBEDDED_OBJECT],
            Pdf | Svg | FileUrl | Keynote | Svxb => &[],
        },
        System::Linux => match k {
            Png => &["image/png"],
            Pdf => &["application/pdf"],
            Svg => &["image/svg+xml"],
            Cdx => &["chemical/x-cdx"],
            Cdxml => &["chemical/x-cdxml"],
            Molfile => &["chemical/x-mdl-molfile"],
            Smiles => &["chemical/x-daylight-smiles"],
            Octet => &["application/x-octet+json"],
            Text => &["text/plain;charset=utf-8", "UTF8_STRING", "text/plain"],
            FileUrl => &["text/uri-list"],
            Svxb => &[SVXB],
            Bitmap | Emf | Office | Keynote | Object => &[],
        },
    }
}

// What paste found on the clipboard. Each is None when absent or unreadable.
#[derive(serde::Serialize, Default, Debug, PartialEq)]
pub struct Clip {
    octet: Option<String>,   // Octet's own JSON
    oct: Option<String>,     // the .oct file in an Octet Drawing object copied out of Word (Windows, decision 0023)
    // CDXML: the CDXML type, or hidden in a picture: Octet's on every system, ChemDraw's PDF on the Mac, or either
    // after Word. ChemDraw's EMF on Windows has none.
    cdxml: Option<String>,
    cdx: Option<String>,     // ChemDraw's CDX, base64
    molfile: Option<String>, // a molfile or RXN file, with LF line ends
    smiles: Option<String>,
    text: Option<String>,    // plain text of 64 KB or less
    picture: Option<String>, // a picture's file bytes (PNG, TIFF or BMP), base64; the page checks and decodes them
    spectrum: Option<(String, String)>, // a spectrum file copied, or its path pasted: its name and text (spectrum.rs)
    filled: bool, // the clipboard holds something, usable or not; paste says it cannot read it only then (issue 23)
}

// ChemDraw's form of a molfile on the clipboard (MDL's MDLCT): each line as one length byte, then the line, with no
// line ends. None if a line is longer than 255 bytes (V2000 lines never are).
pub fn prefixed_lines(text: &str) -> Option<Vec<u8>> {
    let text = text.replace("\r\n", "\n").replace('\r', "\n");
    let text = text.strip_suffix('\n').unwrap_or(&text);
    let mut out = Vec::with_capacity(text.len() + 1);
    for line in text.split('\n') {
        out.push(u8::try_from(line.len()).ok()?);
        out.extend_from_slice(line.as_bytes());
    }
    Some(out)
}

// A molfile from the clipboard: ChemDraw's length-prefixed lines, or ordinary text with CR, LF or CRLF.
pub fn molfile_text(b: &[u8]) -> Option<String> {
    let b = &b[..b.iter().rposition(|&c| c != 0).map_or(0, |k| k + 1)];
    if b.is_empty() {
        return None;
    }
    let mut lines = Vec::new();
    let mut i = 0;
    while i < b.len() {
        let n = usize::from(b[i]);
        match b.get(i + 1..i + 1 + n) {
            Some(line) if !line.contains(&b'\r') && !line.contains(&b'\n') => lines.push(line),
            _ => {
                lines.clear();
                break;
            }
        }
        i += 1 + n;
    }
    let text = if lines.is_empty() {
        String::from_utf8_lossy(b).replace("\r\n", "\n").replace('\r', "\n")
    } else {
        String::from_utf8_lossy(&lines.join(&b'\n')).into_owned()
    };
    Some(if text.ends_with('\n') { text } else { text + "\n" })
}

// SMILES from the clipboard: ASCII, with or without ChemDraw's trailing NUL.
pub fn smiles_text(b: &[u8]) -> Option<String> {
    let s = std::str::from_utf8(b).ok()?.trim_matches(|c: char| c == '\0' || c.is_whitespace());
    (!s.is_empty() && s.is_ascii() && !s.contains('\0')).then(|| s.to_string())
}

// Text from the clipboard as UTF-8, without the NULs a Windows clipboard can add at the end.
fn text_of(b: Vec<u8>) -> Option<String> {
    let end = b.iter().rposition(|&c| c != 0).map_or(0, |k| k + 1);
    String::from_utf8(b[..end].to_vec()).ok()
}

// Plain text from the clipboard: UTF-16 on Windows, UTF-8 elsewhere, without NULs at the end.
fn plain_text(s: System, b: Vec<u8>) -> Option<String> {
    if s != System::Windows {
        return text_of(b);
    }
    let units: Vec<u16> = b.chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).collect();
    let end = units.iter().rposition(|&c| c != 0).map_or(0, |k| k + 1);
    String::from_utf16(&units[..end]).ok()
}

// The types for one copy on system `s`, in ChemDraw's order, as (name, bytes). svg: the picture (None: no picture).
// cdxml: hidden in the picture (on macOS in the PDF and in the EMF in Office's copy), and also put on as its own type
// when `cdxml_type` is set. cdx: ChemDraw's binary drawing.
#[allow(clippy::too_many_arguments)]
fn types(s: System, svg: Option<&str>, dpi: f32, cdxml: Option<&str>, cdxml_type: bool, cdx: Option<Vec<u8>>, molfile: Option<&str>, smiles: Option<&str>, octet_json: Option<String>) -> Result<Vec<(&'static str, Vec<u8>)>, String> {
    // The Mac's picture is the one Update in Word puts on.
    let mut out: Vec<(&'static str, Vec<u8>)> = match svg {
        Some(svg) if s == System::Mac => mac_picture(svg, cdxml)?,
        _ => Vec::new(),
    };
    let mut put = |k: Kind, b: Vec<u8>| out.extend(names(s, k).iter().map(|n| (*n, b.clone())));
    if let Some(svg) = svg.filter(|_| s != System::Mac) {
        if s == System::Windows {
            let tree = crate::export::tree(svg)?;
            put(Kind::Emf, crate::vector::make_emf(&tree, cdxml, None));
            if let (_, Some(b)) = crate::export::clipboard_pixels(&tree, true, dpi, None)? {
                put(Kind::Bitmap, b);
            }
        } else {
            // The PDF is made on a thread of its own while the PNG is drawn, so Copy takes no longer than in 1.1.1. A PDF
            // Octet cannot make (a font it cannot embed) leaves the PNG and the SVG, as in 1.1.1.
            let (png, pdf) = std::thread::scope(|t| {
                let pdf = t.spawn(|| crate::export::make_pdf(svg, cdxml, None));
                (crate::export::clipboard_pictures(svg, false, dpi, cdxml), pdf.join().ok().and_then(Result::ok))
            });
            put(Kind::Png, png?.0);
            if let Some(pdf) = pdf {
                put(Kind::Pdf, pdf);
            }
            // The SVG in px user units, so Inkscape pastes it at true size (issue 47).
            put(Kind::Svg, crate::export::px_units(svg).into_bytes());
        }
    }
    if let Some(b) = cdx.filter(|b| b.starts_with(b"VjCD0100")) {
        put(Kind::Cdx, b);
    }
    if let Some(x) = cdxml.filter(|_| cdxml_type) {
        put(Kind::Cdxml, crate::export::cdxml_document(x).into_bytes());
    }
    // A molfile as length-prefixed lines where ChemDraw writes it so (macOS, Windows); as text on Linux.
    if let Some(m) = molfile.filter(|m| !m.trim().is_empty()) {
        if s == System::Linux {
            put(Kind::Molfile, m.replace("\r\n", "\n").into_bytes());
        } else if let Some(b) = prefixed_lines(m) {
            put(Kind::Molfile, b);
        }
    }
    // SMILES with a NUL, as ChemDraw writes it (macOS, Windows); as text on Linux.
    if let Some(m) = smiles.map(str::trim).filter(|m| !m.is_empty() && m.is_ascii()) {
        put(Kind::Smiles, if s == System::Linux { m.as_bytes().to_vec() } else { [m.as_bytes(), b"\0"].concat() });
    }
    if let Some(j) = octet_json {
        put(Kind::Octet, j.into_bytes());
    }
    Ok(out)
}

// Text alone on the clipboard (Edit > Copy As, a value from a panel), as ChemDraw's Copy As puts it: UTF-8, or on
// Windows UTF-16 with a NUL. Under each of the system's names for text.
fn text_types(s: System, text: &str) -> Vec<(&'static str, Vec<u8>)> {
    let bytes = if s == System::Windows { text.encode_utf16().chain([0]).flat_map(u16::to_le_bytes).collect() } else { text.as_bytes().to_vec() };
    names(s, Kind::Text).iter().map(|n| (*n, bytes.clone())).collect()
}

// The first of a kind's names on the clipboard: its bytes (`read` gives a type's bytes if it is on the clipboard).
fn first(s: System, k: Kind, read: &impl Fn(&str) -> Option<Vec<u8>>) -> Option<Vec<u8>> {
    names(s, k).iter().find_map(|n| read(n))
}

// What paste can use on system `s`, from each type's bytes.
fn clip(s: System, read: impl Fn(&str) -> Option<Vec<u8>>) -> Clip {
    use base64::Engine;
    let filled = std::cell::Cell::new(false);
    let read = |n: &str| read(n).inspect(|_| filled.set(true));
    let mut c = Clip {
        octet: first(s, Kind::Octet, &read).and_then(text_of),
        oct: None,
        cdxml: first(s, Kind::Cdxml, &read).and_then(text_of),
        cdx: first(s, Kind::Cdx, &read).map(|b| base64::engine::general_purpose::STANDARD.encode(b)),
        molfile: first(s, Kind::Molfile, &read).and_then(|b| molfile_text(&b)),
        smiles: first(s, Kind::Smiles, &read).and_then(|b| smiles_text(&b)),
        text: first(s, Kind::Text, &read).filter(|b| b.len() <= MAX_TEXT).and_then(|b| plain_text(s, b)),
        picture: first(s, Kind::Png, &read)
            .or_else(|| first(s, Kind::Bitmap, &read).and_then(|b| if s == System::Windows { bmp_file(&b) } else { Some(b) }))
            .map(|b| base64::engine::general_purpose::STANDARD.encode(b)),
        spectrum: None,
        filled: false,
    };
    // An Octet Drawing copied out of Word: the drawing in its storage, when there is no JSON (from another Octet).
    // Word copies an object it holds as "Embedded Object"; Octet's own copy is "Embed Source". Both are the storage.
    if c.octet.is_none() {
        c.oct = names(s, Kind::Object).iter().find_map(|n| read(n).and_then(|b| object_oct(&b)));
    }
    c.spectrum = crate::spectrum::from_clipboard(first(s, Kind::FileUrl, &read).and_then(text_of).as_deref(), c.text.as_deref());
    // The picture's CDXML when there is no Octet JSON or CDXML type: it holds the whole drawing, arrows, text and
    // shapes too (REL-4, CH-2). A picture copied back out of Word, PowerPoint or Keynote: the PDF Word keeps, the PDF in
    // Keynote's copy (its own PDF has no CDXML), the EMF, Office's zip, then a PNG; or a picture file copied in Finder or
    // the file manager. ChemDraw's CDX is the page's next choice: for a copy with no picture, and for every copy from
    // ChemDraw for Windows, whose EMF holds no CDXML.
    if c.octet.is_none() && c.cdxml.is_none() {
        let picture = |k: Kind| first(s, k, &read).and_then(|b| crate::export::cdxml_from_picture(&b));
        c.cdxml = picture(Kind::Pdf)
            .or_else(|| first(s, Kind::Svxb, &read).and_then(|b| svxb_picture(&b).and_then(crate::export::cdxml_from_picture)))
            .or_else(|| picture(Kind::Keynote))
            .or_else(|| picture(Kind::Emf))
            .or_else(|| first(s, Kind::Office, &read).and_then(|b| cdxml_from_office(&b)))
            .or_else(|| picture(Kind::Png))
            .or_else(|| first(s, Kind::FileUrl, &read).and_then(text_of).and_then(|u| copied_drawing(&u)));
    }
    c.filled = filled.get();
    c
}

// The drawing in an Octet Drawing object's storage, as the Windows clipboard holds it (a compound file in memory).
// Windows reads the compound file; Octet opens only its own stream, with Open's limits. None for other programs'
// objects and on other systems.
fn object_oct(b: &[u8]) -> Option<String> {
    #[cfg(windows)]
    return crate::ole::win::oct_from_embed_source(b);
    #[cfg(not(windows))]
    {
        let _ = b;
        None
    }
}

// The drawing in Office's own copy of a picture (Word, PowerPoint and Excel put it on as Art::GVML ClipFormat): a
// zip whose clipboard/media/ holds the picture's file as it was pasted in, so an EMF Word has redrawn for the
// clipboard does not matter. The zip is hostile: its central directory is read with bounds checks, at most 64 entries
// and 4 pictures are looked at, and each is inflated to 64 MB at most.
fn cdxml_from_office(zip: &[u8]) -> Option<String> {
    let u16_at = |k: usize| zip.get(k..k + 2).map(|b| usize::from(u16::from_le_bytes([b[0], b[1]])));
    let u32_at = |k: usize| zip.get(k..k + 4).map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]) as usize);
    // The end record: the last 22 bytes, or before a comment of at most 64 KB.
    let last = zip.len().checked_sub(22)?;
    let end = (last.saturating_sub(0xffff)..=last).rev().find(|&k| zip[k..k + 4] == *b"PK\x05\x06")?;
    let (count, mut at, mut pictures) = (u16_at(end + 10)?, u32_at(end + 16)?, 0);
    for _ in 0..count.min(64) {
        if zip.get(at..at + 4)? != b"PK\x01\x02" {
            return None;
        }
        let (method, size, local) = (u16_at(at + 10)?, u32_at(at + 20)?, u32_at(at + 42)?);
        let name = zip.get(at + 46..at + 46 + u16_at(at + 28)?)?.to_ascii_lowercase();
        at += 46 + name.len() + u16_at(at + 30)? + u16_at(at + 32)?;
        if !name.starts_with(b"clipboard/media/") || ![&b".pdf"[..], b".emf", b".png"].iter().any(|e| name.ends_with(e)) || zip.get(local..local + 4)? != b"PK\x03\x04" {
            continue;
        }
        pictures += 1;
        if pictures > 4 {
            return None;
        }
        let start = local + 30 + u16_at(local + 26)? + u16_at(local + 28)?;
        let data = zip.get(start..start.checked_add(size)?)?;
        let file = match method {
            0 => data.to_vec(),
            8 => miniz_oxide::inflate::decompress_to_vec_with_limit(data, MAX_TYPE).ok()?,
            _ => continue,
        };
        if let Some(x) = crate::export::cdxml_from_picture(&file) {
            return Some(x);
        }
    }
    None
}

// The Mac's picture of a drawing, as (name, bytes) in the order the clipboard gets them: Office's own copy of the
// picture (office_package) when Octet can make it, then the PDF. Copy and Update in Word (word.rs) both put on what
// this gives. The SVG is read once for both: reading it is most of the time a PDF takes.
pub(crate) fn mac_picture(svg: &str, cdxml: Option<&str>) -> Result<Vec<(&'static str, Vec<u8>)>, String> {
    mac_picture_within(svg, cdxml, MAX_OFFICE)
}

// mac_picture with Office's copy left out when its EMF is larger than `most` bytes. The EMF's records are made on a
// thread of their own while the PDF is made here, so the two take about as long as the longer one, and the PDF goes
// into the EMF after (vector::with_pdf). The thread starts only if the pixels and the CDXML, which the EMF holds as
// they are, fit the limit; without it Copy takes what the PDF takes. If the system gives no thread, the PDF goes alone.
fn mac_picture_within(svg: &str, cdxml: Option<&str>, most: usize) -> Result<Vec<(&'static str, Vec<u8>)>, String> {
    let tree = crate::export::tree(svg)?;
    let fits = crate::vector::pixel_bytes(&tree).saturating_add(cdxml.map_or(0, str::len)) <= most;
    let (emf, pdf) = std::thread::scope(|t| {
        let emf = fits.then(|| std::thread::Builder::new().spawn_scoped(t, || crate::vector::make_emf(&tree, cdxml, None)).ok()).flatten();
        let pdf = crate::export::pdf_of(&tree, cdxml, None);
        (emf.and_then(|e| e.join().ok()), pdf)
    });
    let pdf = pdf?;
    let name = |k: Kind| names(System::Mac, k)[0];
    let mut out = Vec::with_capacity(2);
    // Office's own copy goes first: Word takes it before the PDF. The size is checked before the PDF is put in.
    if let Some(emf) = emf.filter(|e| e.len() + crate::vector::pdf_comment(pdf.len()) <= most) {
        out.push((name(Kind::Office), office_package(crate::vector::size(&tree), &crate::vector::with_pdf(&emf, &pdf))));
    }
    out.push((name(Kind::Pdf), pdf));
    Ok(out)
}

// Office's own copy of a picture as Octet writes it on the Mac: a zip with the parts Office's has. The drawing part
// places one picture at the drawing's size (`w` by `h` pt), given for the group and for the picture, in EMU (12,700 a
// pt). The picture's file is `emf`: an EMF with the PDF in a comment and the drawing as vector records (vector.rs).
// Word for Mac draws the PDF and keeps the EMF in the document as it is, so Word for Windows draws the vector
// records. From a PDF alone Word for Mac makes an EMF whose only drawing is a bitmap of one pixel a point, and that is
// what Word for Windows then shows. The theme part is Octet's own: the format has one in every copy, and a picture
// uses nothing from it.
fn office_package((w, h): (f32, f32), emf: &[u8]) -> Vec<u8> {
    const HEAD: &str = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>"#;
    const RELS: &str = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    const MAIN: &str = "http://schemas.openxmlformats.org/drawingml/2006/main";
    const CANVAS: &str = "http://schemas.openxmlformats.org/drawingml/2006/lockedCanvas";
    let emu = |pt: f32| ((f64::from(pt) * 12_700.0).round() as i64).max(1);
    let ext = format!(r#"cx="{}" cy="{}""#, emu(w), emu(h));
    let types = format!(
        r#"{HEAD}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="emf" ContentType="image/x-emf"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/clipboard/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/clipboard/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/></Types>"#
    );
    let rels = |list: &str| format!(r#"{HEAD}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{list}</Relationships>"#);
    let package = rels(&format!(r#"<Relationship Id="rId1" Type="{RELS}/drawing" Target="clipboard/drawings/drawing1.xml"/>"#));
    let drawing_rels = rels(&format!(r#"<Relationship Id="rId1" Type="{RELS}/image" Target="../media/image1.emf"/><Relationship Id="rId2" Type="{RELS}/theme" Target="../theme/theme1.xml"/>"#));
    // A locked canvas (a group Office pastes as one object) with one picture that fills it.
    let drawing = format!(
        r#"{HEAD}<a:graphic xmlns:a="{MAIN}"><a:graphicData uri="{CANVAS}"><lc:lockedCanvas xmlns:lc="{CANVAS}"><a:nvGrpSpPr><a:cNvPr id="0" name=""/><a:cNvGrpSpPr/></a:nvGrpSpPr><a:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext {ext}/><a:chOff x="0" y="0"/><a:chExt {ext}/></a:xfrm></a:grpSpPr><a:pic><a:nvPicPr><a:cNvPr id="1" name="Picture 1"/><a:cNvPicPr><a:picLocks noChangeAspect="1"/></a:cNvPicPr></a:nvPicPr><a:blipFill><a:blip xmlns:r="{RELS}" r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></a:blipFill><a:spPr><a:xfrm><a:off x="0" y="0"/><a:ext {ext}/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></a:spPr></a:pic></lc:lockedCanvas></a:graphicData></a:graphic>"#
    );
    // The smallest theme the format allows: 12 colours (black, white and Octet Blue), Arial, and three each of the
    // fills, lines, effects and background fills, then the colour map.
    let colours: String = [("dk1", "000000"), ("lt1", "FFFFFF"), ("dk2", "000000"), ("lt2", "FFFFFF"), ("accent1", "213C99"), ("accent2", "213C99"), ("accent3", "213C99"), ("accent4", "213C99"), ("accent5", "213C99"), ("accent6", "213C99"), ("hlink", "213C99"), ("folHlink", "213C99")]
        .iter()
        .map(|(tag, rgb)| format!(r#"<a:{tag}><a:srgbClr val="{rgb}"/></a:{tag}>"#))
        .collect();
    let font = r#"<a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/>"#;
    let fills = r#"<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>"#.repeat(3);
    let lines = r#"<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>"#.repeat(3);
    let effects = "<a:effectStyle><a:effectLst/></a:effectStyle>".repeat(3);
    let theme = format!(
        r#"{HEAD}<a:clipboardTheme xmlns:a="{MAIN}"><a:themeElements><a:clrScheme name="Octet">{colours}</a:clrScheme><a:fontScheme name="Octet"><a:majorFont>{font}</a:majorFont><a:minorFont>{font}</a:minorFont></a:fontScheme><a:fmtScheme name="Octet"><a:fillStyleLst>{fills}</a:fillStyleLst><a:lnStyleLst>{lines}</a:lnStyleLst><a:effectStyleLst>{effects}</a:effectStyleLst><a:bgFillStyleLst>{fills}</a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></a:clipboardTheme>"#
    );
    // Deflated at the fastest level: the PDF in the EMF is deflated already, and Copy should not wait for more. An EMF
    // over 1 MB is stored.
    let parts: [(&str, &[u8]); 6] = [
        ("[Content_Types].xml", types.as_bytes()),
        ("_rels/.rels", package.as_bytes()),
        ("clipboard/drawings/drawing1.xml", drawing.as_bytes()),
        ("clipboard/drawings/_rels/drawing1.xml.rels", drawing_rels.as_bytes()),
        ("clipboard/theme/theme1.xml", theme.as_bytes()),
        ("clipboard/media/image1.emf", emf),
    ];
    crate::export::zip(&parts, 1, STORED_OVER)
}

// The picture's file in LibreOffice's own copy of a picture (SVXB): "NAT5" and a 6-byte header, then the picture's
// link, a 6-byte header with the length of the link's fields, which start with its type (2 bytes) and the file's size
// (4 bytes). The file comes after the fields: for a PDF, the PDF as it was pasted in. Read with bounds checks.
fn svxb_picture(b: &[u8]) -> Option<&[u8]> {
    let u32_at = |k: usize| b.get(k..k + 4).map(|x| u32::from_le_bytes([x[0], x[1], x[2], x[3]]) as usize);
    if b.get(..4)? != b"NAT5" {
        return None;
    }
    let start = 16usize.checked_add(u32_at(12)?)?;
    b.get(start..start.checked_add(u32_at(18)?)?)
}

// The drawing in a PDF, EMF or PNG file copied in Finder or the file manager (its path, or a file:// list), read
// with Open's 64 MB limit.
fn copied_drawing(url: &str) -> Option<String> {
    let line = url.lines().map(str::trim).find(|l| !l.is_empty() && !l.starts_with('#'))?;
    let path = if line.starts_with("file:") { tauri::Url::parse(line).ok()?.to_file_path().ok()? } else { std::path::PathBuf::from(line) };
    let ext = path.extension()?.to_str()?.to_ascii_lowercase();
    if !path.is_absolute() || !["pdf", "emf", "png"].contains(&ext.as_str()) {
        return None;
    }
    let meta = std::fs::metadata(&path).ok()?;
    if !meta.is_file() || meta.len() > crate::MAX_BYTES {
        return None;
    }
    crate::export::cdxml_from_picture(&std::fs::read(&path).ok()?)
}

// Every name paste may read on system `s`.
#[cfg_attr(target_os = "macos", allow(dead_code))]
fn readable(s: System) -> Vec<&'static str> {
    use Kind::*;
    [Octet, Object, Cdxml, Cdx, Molfile, Smiles, Pdf, Svxb, Emf, Office, Text, Png, Bitmap, FileUrl].iter().flat_map(|k| names(s, *k).iter().copied()).collect()
}

// Whether paste on Linux asks the clipboard's owner for the type `name`, from the names the owner offers. The owner
// makes a type when it is asked, and that can take long (Inkscape runs its PDF export). The PDF and LibreOffice's own
// copy are read only for the drawing in them: not when Octet's JSON or CDXML is there, and Inkscape's PDF holds none.
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
fn asked(name: &str, present: &[String]) -> bool {
    let has = |n: &str| present.iter().any(|p| p == n);
    let drawing = has("application/x-octet+json") || has("chemical/x-cdxml");
    has(name) && !(drawing && (name == "application/pdf" || name == SVXB)) && !(name == "application/pdf" && has("image/x-inkscape-svg"))
}

// What paste can use from the types the system found. any: the clipboard holds something, even if paste reads none
// of it (Word's OLE formats alone, say).
#[cfg_attr(target_os = "macos", allow(dead_code))]
fn found_clip((found, any): (Vec<(&'static str, Vec<u8>)>, bool)) -> Clip {
    let mut c = clip(HERE, |t| found.iter().find(|(n, _)| *n == t).map(|(_, b)| b.clone()));
    c.filled |= any;
    c
}

// A Windows bitmap (CF_DIB: its header, colours and pixels) as a .bmp file, which the page's decoder reads: the
// 14-byte file header goes first, with where the pixels start. None if the header is not sound.
fn bmp_file(dib: &[u8]) -> Option<Vec<u8>> {
    let u32_at = |k: usize| dib.get(k..k + 4).map(|b| u32::from_le_bytes([b[0], b[1], b[2], b[3]]) as usize);
    let (head, bits, compression, used) = (u32_at(0)?, u16::from_le_bytes([*dib.get(14)?, *dib.get(15)?]), u32_at(16)?, u32_at(32)?);
    let colours = if used > 0 { used } else if bits <= 8 { 1 << bits } else { 0 };
    // A 40-byte header with BI_BITFIELDS (3) has its three colour masks after it.
    let masks = if head == 40 && compression == 3 { 12 } else { 0 };
    let start = head.checked_add(masks)?.checked_add(colours.checked_mul(4)?)?.checked_add(14)?;
    if head < 40 || start > dib.len() + 14 {
        return None;
    }
    let mut out = Vec::with_capacity(dib.len() + 14);
    out.extend_from_slice(b"BM");
    out.extend_from_slice(&u32::try_from(dib.len() + 14).ok()?.to_le_bytes());
    out.extend_from_slice(&[0; 4]);
    out.extend_from_slice(&u32::try_from(start).ok()?.to_le_bytes());
    out.extend_from_slice(dib);
    Some(out)
}

#[cfg(target_os = "macos")]
pub(crate) mod mac {
    use objc2::rc::{autoreleasepool, Retained};
    use objc2::runtime::ProtocolObject;
    use objc2_app_kit::{NSPasteboard, NSPasteboardItem};
    use objc2_foundation::{NSArray, NSData, NSString, NSURL};

    pub fn write<B: AsRef<[u8]>>(pb: &NSPasteboard, types: &[(&str, B)]) -> Result<(), String> {
        autoreleasepool(|_| {
            let item = NSPasteboardItem::new();
            for (t, bytes) in types {
                if !item.setData_forType(&NSData::with_bytes(bytes.as_ref()), &NSString::from_str(t)) {
                    return Err("The clipboard did not accept the data.".to_string());
                }
            }
            pb.clearContents();
            let items: Retained<NSArray<ProtocolObject<dyn objc2_app_kit::NSPasteboardWriting>>> = NSArray::from_retained_slice(&[ProtocolObject::from_retained(item)]);
            if pb.writeObjects(&items) { Ok(()) } else { Err("The clipboard did not accept the data.".to_string()) }
        })
    }

    // The bytes of each type on the clipboard (64 MB at most), read only if the clipboard has that type.
    pub fn read(pb: &NSPasteboard) -> super::Clip {
        autoreleasepool(|_| {
            let present: Vec<String> = pb.types().map(|a| a.iter().map(|t| t.to_string()).collect()).unwrap_or_default();
            let mut c = super::clip(super::System::Mac, |t| {
                // A name that ends in a full stop is a prefix (Keynote's numbered types): the first such type with a PDF.
                if t.ends_with('.') {
                    let pdf = |p: &String| pb.dataForType(&NSString::from_str(p)).filter(|d| d.len() <= super::MAX_TYPE).map(|d| d.to_vec()).filter(|b| b.starts_with(b"%PDF"));
                    return present.iter().filter(|p| p.starts_with(t)).take(16).find_map(pdf);
                }
                if !present.iter().any(|p| p == t) {
                    return None;
                }
                let data = pb.dataForType(&NSString::from_str(t))?;
                // A file Finder copied comes as a file reference (file:///.file/id=…): its path instead.
                if t == super::FILE_URL {
                    let u = NSURL::URLWithString(&NSString::from_str(std::str::from_utf8(&data.to_vec()).ok()?))?;
                    return Some(u.filePathURL()?.path()?.to_string().into_bytes());
                }
                (data.len() <= super::MAX_TYPE).then(|| data.to_vec())
            });
            c.filled |= !present.is_empty();
            c
        })
    }

    pub fn general() -> Retained<NSPasteboard> {
        NSPasteboard::generalPasteboard()
    }

    // The drawing on the clipboard as paste reads it, as CDXML: a picture Word copied for Edit Picture from Word
    // (word.rs).
    pub fn drawing(pb: &NSPasteboard) -> Option<String> {
        read(pb).cdxml
    }

    // The clipboard as it is, to put back after Octet borrows it (word.rs): each item's types and bytes, 64 MB a type
    // at most. A type that gives no data (a promise its program no longer keeps) is left out.
    pub type Saved = Vec<Vec<(String, Vec<u8>)>>;

    pub fn save(pb: &NSPasteboard) -> Saved {
        autoreleasepool(|_| {
            let items = pb.pasteboardItems().map(|a| a.to_vec()).unwrap_or_default();
            items
                .iter()
                .map(|item| {
                    let types = item.types().to_vec();
                    types.iter().filter_map(|t| item.dataForType(t).filter(|d| d.len() <= super::MAX_TYPE).map(|d| (t.to_string(), d.to_vec()))).collect()
                })
                .collect()
        })
    }

    pub fn restore(pb: &NSPasteboard, saved: &Saved) {
        autoreleasepool(|_| {
            pb.clearContents();
            let items: Vec<Retained<ProtocolObject<dyn objc2_app_kit::NSPasteboardWriting>>> = saved
                .iter()
                .map(|types| {
                    let item = NSPasteboardItem::new();
                    for (t, bytes) in types {
                        item.setData_forType(&NSData::with_bytes(bytes), &NSString::from_str(t));
                    }
                    ProtocolObject::from_retained(item)
                })
                .collect();
            if !items.is_empty() {
                pb.writeObjects(&NSArray::from_retained_slice(&items));
            }
        })
    }
}

#[cfg(windows)]
#[path = "clipboard_windows.rs"]
pub(crate) mod win;

#[cfg(target_os = "linux")]
#[path = "clipboard_linux.rs"]
mod linux;

// Copy: the selection as a picture, CDX (base64 from the page), CDXML, a molfile, SMILES and Octet's JSON. With
// `text`, only that text (CH-7): the app puts it there, as the webview allows a page to copy only during a click.
// oct: the selection as a .oct file, sent on Windows while Settings > Import and export > Copy > Office object is on.
// It goes on as an Octet Drawing object first, through the OLE clipboard, when Octet's class is registered (decision
// 0023). Otherwise the copy is as decision 0011 says.
#[allow(clippy::too_many_arguments)]
#[tauri::command]
pub async fn copy_to_clipboard(app: tauri::AppHandle, svg: Option<String>, dpi: Option<f32>, cdxml: Option<String>, cdxml_type: Option<bool>, cdx: Option<String>, molfile: Option<String>, smiles: Option<String>, octet_json: Option<String>, text: Option<String>, oct: Option<String>) -> Result<(), String> {
    use base64::Engine;
    let cdx = match cdx {
        Some(c) if c.len() <= MAX_TYPE / 3 * 4 + 4 => Some(base64::engine::general_purpose::STANDARD.decode(c).map_err(|_| "Octet cannot copy this.".to_string())?),
        _ => None,
    };
    let object = oct.filter(|o| text.is_none() && o.len() <= MAX_TYPE);
    #[cfg(not(windows))]
    let _ = object;
    let types = match text {
        Some(t) if t.len() <= MAX_TYPE => text_types(HERE, &t),
        Some(_) => return Err("This text is too long to copy.".into()),
        None => types(HERE, svg.as_deref(), dpi.unwrap_or(600.0), cdxml.as_deref(), cdxml_type.unwrap_or(false), cdx, molfile.as_deref(), smiles.as_deref(), octet_json)?,
    };
    let _ = &app;
    #[cfg(target_os = "macos")]
    return mac::write(&mac::general(), &types);
    #[cfg(windows)]
    {
        if let Some(oct) = object.filter(|_| crate::ole::win::offered()) {
            let numbered = types.into_iter().map(|(n, b)| (win::format(n) as u16, n, b)).collect::<Vec<_>>();
            if numbered.iter().any(|(f, ..)| *f == 0) {
                return Err("Octet cannot copy this.".into());
            }
            return crate::ole::win::copy(&app, numbered, oct).await;
        }
        return win::write(&types);
    }
    #[cfg(target_os = "linux")]
    return linux::write(&app, types).await;
    #[allow(unreachable_code)]
    Err("Octet cannot copy on this system.".into())
}

// Paste: everything Octet can use from the clipboard.
#[tauri::command]
pub async fn read_clipboard(app: tauri::AppHandle) -> Result<Clip, String> {
    let _ = &app;
    #[cfg(target_os = "macos")]
    return Ok(mac::read(&mac::general()));
    #[cfg(windows)]
    return win::read(&readable(HERE)).map(found_clip);
    #[cfg(target_os = "linux")]
    return linux::read(&app, readable(HERE)).await.map(found_clip);
    #[allow(unreachable_code)]
    Err("Octet cannot paste on this system.".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    const OFFICE: &str = "com.microsoft.Art--GVML-ClipFormat";
    const MOL: &str = "\n  Octet\n\n  2  1  0  0  0  0  0  0  0  0999 V2000\n    0.0000    0.0000    0.0000 C   0  0\n    1.0000    0.0000    0.0000 O   0  0\n  1  2  1  0\nM  END\n";

    #[test]
    fn molfile_as_chemdraw_writes_it() {
        let b = prefixed_lines(MOL).unwrap();
        // One length byte per line instead of each line end, so the same length as the text.
        assert_eq!(b.len(), MOL.len());
        assert_eq!(b[0], 0);
        assert_eq!(&b[1..9], b"\x07  Octet");
        assert!(b.ends_with(b"\x06M  END"));
        assert_eq!(molfile_text(&b).as_deref(), Some(MOL));
        // Ordinary text with CR line ends reads too.
        assert_eq!(molfile_text(MOL.replace('\n', "\r").as_bytes()).as_deref(), Some(MOL));
        assert_eq!(prefixed_lines(&"x".repeat(300)), None);
    }

    #[test]
    fn smiles_with_nul() {
        assert_eq!(smiles_text(b"N[C@@H](CC1=CC=CC=C1)C(O)=O\0").as_deref(), Some("N[C@@H](CC1=CC=CC=C1)C(O)=O"));
        assert_eq!(smiles_text(b"CCO").as_deref(), Some("CCO"));
        assert_eq!(smiles_text(b"\0"), None);
        // ChemDraw's reaction SMILES for a drawing with an arrow (issue 23): the arrow stays.
        assert_eq!(smiles_text(b"O=C(O)[C@H]1NCCC1>>\0").as_deref(), Some("O=C(O)[C@H]1NCCC1>>"));
    }

    // Issue 23: ChemDraw 25.5 for Windows puts these 14 formats on the clipboard and no CDXML. Its EMF holds no CDXML,
    // so paste takes the CDX, with the molfile and SMILES there if the CDX fails. Paste reads nothing else here.
    #[test]
    fn chemdraw_for_windows_pastes_its_cdx() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let emf = crate::vector::make_emf(&crate::export::tree(svg).unwrap(), None, None);
        let cdx = [&b"VjCD0100\x04\x03\x02\x01"[..], &[0; 14], &[0x80, 0x01, 0, 0, 0, 0, 0, 0]].concat();
        let junk = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1junk".to_vec();
        let chemdraw: Vec<(&str, Vec<u8>)> = vec![
            ("ChemDraw Interchange Format", cdx.clone()),
            ("ChemDraw Structure Data", junk.clone()),
            ("MDLSK", junk.clone()),
            ("MDLCT", prefixed_lines(MOL).unwrap()),
            ("SMILES", b"O=C(O)[C@H]1NCCC1>>\0".to_vec()),
            ("SLNSTRING", b"OC(=O)CH[1]NHCH2CH2CH2@1\0".to_vec()),
            (ENHMETAFILE, emf),
            ("CF_METAFILEPICT", vec![0; 24]),
            ("Embed Source", junk.clone()),
            ("Native", junk.clone()),
            ("OwnerLink", junk.clone()),
            ("Object Descriptor", junk.clone()),
            ("Ole Private Data", junk.clone()),
            ("DataObject", vec![0; 8]),
        ];
        let c = clip(System::Windows, |n| chemdraw.iter().find(|(x, _)| *x == n).map(|(_, b)| b.clone()));
        use base64::Engine;
        assert_eq!((c.octet.as_deref(), c.cdxml.as_deref(), c.picture.as_deref(), c.text.as_deref()), (None, None, None, None));
        assert_eq!(c.cdx.map(|b| base64::engine::general_purpose::STANDARD.decode(b).unwrap()), Some(cdx));
        assert_eq!((c.molfile.as_deref(), c.smiles.as_deref(), c.filled), (Some(MOL), Some("O=C(O)[C@H]1NCCC1>>"), true));
        // Word's copy of ChemDraw's picture, as expected: an EMF with no CDXML and OLE formats. Nothing to paste, but
        // the clipboard is not empty, so paste says so. An empty clipboard says nothing.
        let word = |n: &str| chemdraw.iter().filter(|(x, _)| [ENHMETAFILE, "Object Descriptor"].contains(x)).find(|(x, _)| *x == n).map(|(_, b)| b.clone());
        let c = clip(System::Windows, word);
        assert_eq!(c, Clip { filled: true, ..Clip::default() });
        assert!(!clip(System::Windows, |_| None).filled);
        assert!(found_clip((Vec::new(), true)).filled && !found_clip((Vec::new(), false)).filled);
    }

    #[test]
    fn copy_types_in_chemdraws_order() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let t = types(System::Mac, Some(svg), 600.0, Some("<CDXML/>"), true, Some(b"VjCD0100\x04\x03\x02\x01".to_vec()), Some(MOL), Some("CO"), Some("{}".into())).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF, CDX[0], CDX[1], CDX[2], CDXML[0], CDXML[1], CDXML[2], MOLFILE, SMILES, OCTET]);
        assert!(t[2].1.starts_with(b"VjCD0100") && t[2].1 == t[3].1 && t[2].1 == t[4].1);
        let t = types(System::Mac, Some(svg), 600.0, Some("<CDXML/>"), true, None, Some(MOL), Some("CO"), Some("{}".into())).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF, CDXML[0], CDXML[1], CDXML[2], MOLFILE, SMILES, OCTET]);
        assert!(t[2].1.starts_with(b"<?xml") && t[2].1.ends_with(b"<CDXML/>") && t[2].1 == t[3].1 && t[2].1 == t[4].1);
        assert_eq!(t[6].1, b"CO\0");
        // ChemDraw 26.1's Revvity CDXML type pastes too.
        assert!(clip(System::Mac, |n| (n == CDXML[1]).then(|| b"<CDXML/>".to_vec())).cdxml.is_some());
        // Paste reads them all back; the PDF is not needed when Octet's JSON is there.
        let read = |name: &str| t.iter().find(|(n, _)| *n == name).map(|(_, b)| b.clone());
        let c = clip(System::Mac, read);
        assert_eq!((c.octet.as_deref(), c.molfile.as_deref(), c.smiles.as_deref()), (Some("{}"), Some(MOL), Some("CO")));
        // Plain text (a name copied from a paper) comes through for the name field, unless it is too long.
        assert_eq!(clip(System::Mac, |name| (name == TEXT).then(|| b"aspirin".to_vec())).text.as_deref(), Some("aspirin"));
        assert_eq!(clip(System::Mac, |name| (name == TEXT).then(|| vec![b'a'; MAX_TEXT + 1])).text, None);
        let utf16: Vec<u8> = "aspirin".encode_utf16().chain([0]).flat_map(u16::to_le_bytes).collect();
        assert_eq!(clip(System::Windows, |name| (name == UNICODE_TEXT).then(|| utf16.clone())).text.as_deref(), Some("aspirin"));
        // A picture: PNG first, else the system's bitmap (on Windows made a .bmp file).
        assert_eq!(clip(System::Mac, |n| (n == "public.tiff").then(|| b"MM\0*".to_vec())).picture.as_deref(), Some("TU0AKg=="));
        assert_eq!(clip(System::Mac, |n| [Some("public.tiff"), Some("public.png")].contains(&Some(n)).then(|| n.as_bytes().to_vec())).picture.as_deref(), Some("cHVibGljLnBuZw=="));
        let mut dib = vec![0u8; 40 + 4 * 2 + 8];
        dib[0] = 40;
        dib[14] = 1; // 1 bit a pixel: two colours, then the pixels
        let bmp = bmp_file(&dib).unwrap();
        assert_eq!((&bmp[..2], u32::from_le_bytes(bmp[2..6].try_into().unwrap()), u32::from_le_bytes(bmp[10..14].try_into().unwrap())), (&b"BM"[..], 70, 62));
        assert_eq!(&bmp[14..], &dib[..]);
        assert!(clip(System::Windows, |n| (n == DIB).then(|| dib.clone())).picture.is_some());
        assert_eq!(bmp_file(&dib[..20]), None);
        assert_eq!(bmp_file(&[&[40, 0, 0, 0][..], &[0; 28], &[255, 255, 255, 255], &[0; 8]].concat()), None);
        // Without it (a picture copied back out of Word), the CDXML comes out of the PDF.
        let c = clip(System::Mac, |name| (name == PDF).then(|| t[1].1.clone()));
        assert!(c.cdxml.unwrap().contains("<CDXML/>"));
        // The Copy switches in Settings: with all four off, only Octet's JSON goes on; CDXML off keeps it in the PDF.
        let t = types(System::Mac, None, 600.0, Some("<CDXML/>"), false, None, None, None, Some("{}".into())).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OCTET]);
        let t = types(System::Mac, Some(svg), 600.0, Some("<CDXML/>"), false, None, None, Some("CO"), None).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF, SMILES]);
        assert!(crate::export::cdxml_from_pdf(&t[1].1).unwrap().contains("<CDXML/>"));
    }

    // REL-4, CH-2: ChemDraw's copy has a CDX as well as its PDF. Paste still takes the whole drawing from the PDF.
    #[test]
    fn chemdraws_copy_pastes_from_its_pdf() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let pdf = crate::export::make_pdf(svg, Some("<CDXML><page><arrow/></page></CDXML>"), None).unwrap();
        for cdx in CDX {
            let c = clip(System::Mac, |name| match name {
                PDF => Some(pdf.clone()),
                n if n == cdx => Some(b"VjCD0100".to_vec()),
                MOLFILE => Some(prefixed_lines(MOL).unwrap()),
                _ => None,
            });
            assert!(c.cdxml.as_deref().is_some_and(|x| x.contains("<arrow/>")), "{cdx}");
            assert!(c.cdx.is_some() && c.molfile.is_some());
        }
        // Sam's dump of ChemDraw 22.2's copy (see export.rs reads_chemdraws_pdf).
        let Ok(dir) = std::env::var("OCTET_CLIPBOARD_DUMPS") else { return };
        let c = clip(System::Mac, |name| std::fs::read(format!("{dir}/chemdraw-copy/0_{name}")).ok());
        assert!(c.cdxml.unwrap().contains("<CDXML") && c.cdx.is_some() && c.molfile.is_some() && c.smiles.is_some());
        // Octet's and ChemDraw's pictures copied back out of Word for Mac, and Octet's out of Keynote, paste as drawings.
        let file = |sub: &str, name: &str| std::fs::read(format!("{dir}/{sub}/0_{name}")).ok();
        for sub in ["word-octet-aspirin", "word-cd22-aspirin", "word-copy", "keynote-octet-aspirin"] {
            let names: Vec<String> = std::fs::read_dir(format!("{dir}/{sub}")).unwrap().map(|e| e.unwrap().file_name().to_string_lossy()[2..].to_string()).collect();
            let c = clip(System::Mac, |n| match n.strip_suffix('.') {
                Some(_) => names.iter().filter(|p| p.starts_with(n)).filter_map(|p| file(sub, p)).find(|b| b.starts_with(b"%PDF")),
                None => file(sub, n),
            });
            assert!(c.cdxml.is_some_and(|x| x.contains("<CDXML")), "{sub}");
        }
    }

    // REL-3, CH-1: Windows and Linux copy the same things as the Mac, under their own names: on Windows a vector EMF and
    // a bitmap for the picture, on Linux a PNG and an SVG. Paste reads them back.
    #[test]
    fn windows_and_linux_copy_the_same() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let cdx = b"VjCD0100\x04\x03\x02\x01".to_vec();
        let all = |s| types(s, Some(svg), 600.0, Some("<CDXML/>"), true, Some(cdx.clone()), Some(MOL), Some("CO"), Some("{}".into())).unwrap();
        let t = all(System::Windows);
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [ENHMETAFILE, DIB, "ChemDraw Interchange Format", "CDXML", "MDLCT", "SMILES", "application/x-octet+json"]);
        assert_eq!(&t[0].1[40..44], b" EMF");
        // A picture copied back out of Word keeps its EMF: with nothing else, paste reads the drawing from it.
        let c = clip(System::Windows, |n| (n == ENHMETAFILE).then(|| t[0].1.clone()));
        assert_eq!(c.cdxml.as_deref(), Some("<CDXML/>"));
        // 20 pt by 10 pt at 600 dpi: 167 by 84 pixels, as a bottom-up 24-bit bitmap on white with rows of 504 bytes.
        let dib = &t[1].1;
        let int = |k: usize| i32::from_le_bytes(dib[k..k + 4].try_into().unwrap());
        assert_eq!((int(0), int(4), int(8), dib[14]), (40, 167, 84, 24));
        assert_eq!(dib.len(), 40 + 504 * 84);
        assert_eq!(&dib[40..43], [255, 255, 255], "the bottom row is white");
        assert!(dib[40..].chunks(3).any(|c| c == [0, 0, 0]), "the bar is black");
        assert_eq!((t[4].1.clone(), t[5].1.clone()), (prefixed_lines(MOL).unwrap(), b"CO\0".to_vec()));
        let read = |t: &Vec<(&str, Vec<u8>)>, n: &str| t.iter().find(|(x, _)| *x == n).map(|(_, b)| b.clone());
        let c = clip(System::Windows, |n| read(&t, n));
        assert_eq!((c.octet.as_deref(), c.molfile.as_deref(), c.smiles.as_deref()), (Some("{}"), Some(MOL), Some("CO")));
        assert!(c.cdxml.unwrap().ends_with("<CDXML/>") && c.cdx.is_some());
        // A block of Windows memory can be larger than what was put in it: text reads without the NULs after it.
        let c = clip(System::Windows, |n| (n == "application/x-octet+json").then(|| b"{}\0\0\0".to_vec()));
        assert_eq!(c.octet.as_deref(), Some("{}"));
        let t = all(System::Linux);
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), ["image/png", "application/pdf", "image/svg+xml", "chemical/x-cdx", "chemical/x-cdxml", "chemical/x-mdl-molfile", "chemical/x-daylight-smiles", "application/x-octet+json"]);
        assert_eq!((t[2].1.as_slice(), t[5].1.as_slice(), t[6].1.as_slice()), (crate::export::px_units(svg).as_bytes(), MOL.as_bytes(), b"CO".as_slice()));
        // The PDF is the Mac's, with the CDXML in it.
        assert_eq!(t[1].1, types(System::Mac, Some(svg), 600.0, Some("<CDXML/>"), false, None, None, None, None).unwrap()[1].1);
        let c = clip(System::Linux, |n| read(&t, n));
        assert_eq!((c.octet.as_deref(), c.molfile.as_deref(), c.smiles.as_deref()), (Some("{}"), Some(MOL), Some("CO")));
        assert!(c.cdxml.unwrap().ends_with("<CDXML/>") && c.cdx.is_some());
        // The Copy switches: with all five off, only Octet's JSON goes on.
        for s in [System::Windows, System::Linux] {
            let t = types(s, None, 600.0, None, false, None, None, None, Some("{}".into())).unwrap();
            assert_eq!(t.len(), 1);
        }
        // Paste reads only names its system has.
        assert!(readable(System::Windows).contains(&"MDLCT") && !readable(System::Linux).contains(&PDF) && readable(System::Linux).contains(&"application/pdf"));
    }

    // A zip as Office writes its own copy of a picture (Art::GVML ClipFormat): `files` deflated, with the central
    // directory and end record after them.
    fn office_zip(files: &[(&str, &[u8])]) -> Vec<u8> {
        let (mut out, mut dir) = (Vec::new(), Vec::new());
        for (name, data) in files {
            let packed = miniz_oxide::deflate::compress_to_vec(data, 6);
            let sizes = [&[0u8; 4][..], &(packed.len() as u32).to_le_bytes(), &(data.len() as u32).to_le_bytes(), &(name.len() as u16).to_le_bytes(), &[0, 0]].concat();
            dir.extend([b"PK\x01\x02".as_slice(), &[20, 0, 20, 0, 0, 0, 8, 0, 0, 0, 0, 0], &sizes, &[0; 10], &(out.len() as u32).to_le_bytes(), name.as_bytes()].concat());
            out.extend([b"PK\x03\x04".as_slice(), &[20, 0, 0, 0, 8, 0, 0, 0, 0, 0], &sizes, name.as_bytes(), &packed].concat());
        }
        let n = (files.len() as u16).to_le_bytes();
        let end = [b"PK\x05\x06".as_slice(), &[0; 4], &n, &n, &(dir.len() as u32).to_le_bytes(), &(out.len() as u32).to_le_bytes(), &[0, 0]].concat();
        [out, dir, end].concat()
    }

    // A picture pasted into Word (PowerPoint, Keynote) and copied back out pastes back as the drawing. Word hands back
    // only its own types: on the Mac Octet's PDF unchanged, with Office's zip (an EMF it drew), TIFF, PNG and JPEG; on
    // Windows an EMF, maybe redrawn, and the zip with the EMF Octet put on. Keynote's own PDF loses the CDXML, but its
    // copy keeps Octet's PDF under a numbered type. On Linux the PNG carries it. A picture file copied in Finder too.
    #[test]
    fn pictures_copied_back_out_paste_as_the_drawing() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        let doc = crate::export::cdxml_document(x);
        let tree = crate::export::tree(svg).unwrap();
        let on = |s| types(s, Some(svg), 600.0, Some(x), false, None, Some(MOL), Some("CO"), Some("{}".into())).unwrap();
        let picture = |s, n: &str| on(s).into_iter().find(|(t, _)| *t == n).unwrap().1;
        let (pdf, emf, png) = (picture(System::Mac, PDF), picture(System::Windows, ENHMETAFILE), picture(System::Linux, "image/png"));
        let redrawn = crate::vector::make_emf(&tree, None, None); // an EMF Word drew, with no comment
        let mac_word = |n: &str| match n {
            PDF => Some(pdf.clone()),
            OFFICE => Some(office_zip(&[("clipboard/media/image1.emf", &redrawn)])),
            "public.tiff" => Some(b"MM\0*".to_vec()),
            "public.png" => Some(crate::export::clipboard_pictures(svg, false, 600.0, None).unwrap().0),
            _ => None,
        };
        let c = clip(System::Mac, mac_word);
        assert_eq!((c.cdxml.as_deref(), c.octet.as_deref(), c.molfile.as_deref()), (Some(doc.as_str()), None, None));
        // Keynote: its own PDF, with no CDXML, then Octet's under a numbered type (mac::read finds it by the prefix).
        let keynote = |n: &str| match n {
            PDF => Some(crate::export::make_pdf(svg, None, None).unwrap()),
            "com.apple.iWork.TSPData." => Some(pdf.clone()),
            _ => None,
        };
        assert_eq!(clip(System::Mac, keynote).cdxml.as_deref(), Some(doc.as_str()));
        // Windows: the EMF as it went on, or Word's redrawn EMF with the zip holding Octet's, deflated or not.
        assert_eq!(clip(System::Windows, |n| (n == ENHMETAFILE).then(|| emf.clone())).cdxml.as_deref(), Some(x));
        let zip = office_zip(&[("[Content_Types].xml", b"<Types/>"), ("clipboard/drawings/drawing1.xml", b"<a:graphic/>"), ("clipboard/media/image1.emf", &emf)]);
        let windows_word = |n: &str| match n {
            ENHMETAFILE => Some(redrawn.clone()),
            "Art::GVML ClipFormat" => Some(zip.clone()),
            _ => None,
        };
        assert_eq!(clip(System::Windows, windows_word).cdxml.as_deref(), Some(x));
        assert_eq!(cdxml_from_office(&office_zip(&[("clipboard/media/image1.png", &crate::export::clipboard_pictures(svg, false, 600.0, Some(x)).unwrap().0)])).as_deref(), Some(doc.as_str()));
        // Linux: Octet's PNG, or the PDF that LibreOffice keeps (Octet's or ChemDraw's), which goes first.
        assert_eq!(clip(System::Linux, |n| (n == "image/png").then(|| png.clone())).cdxml.as_deref(), Some(doc.as_str()));
        let libreoffice = |n: &str| match n {
            "application/pdf" => Some(pdf.clone()),
            "image/png" => Some(crate::export::clipboard_pictures(svg, false, 600.0, None).unwrap().0),
            _ => None,
        };
        assert_eq!(clip(System::Linux, libreoffice).cdxml.as_deref(), Some(doc.as_str()));
        // Copied out of LibreOffice: its own copy (SVXB) holds the PDF as it was pasted in. Its PNG is LibreOffice's.
        let svxb = [&b"NAT5\x01\x00\0\0\0\0\x02\x00\x33\0\0\0\x0c\x00"[..], &(pdf.len() as u32).to_le_bytes(), &[0; 45], &pdf, &[0; 9]].concat();
        let libreoffice = |n: &str| match n {
            SVXB => Some(svxb.clone()),
            "image/png" => Some(crate::export::clipboard_pictures(svg, false, 600.0, None).unwrap().0),
            _ => None,
        };
        assert_eq!(clip(System::Linux, libreoffice).cdxml.as_deref(), Some(doc.as_str()));
        assert_eq!(svxb_picture(&svxb), Some(pdf.as_slice()));
        for k in 0..70 {
            assert_eq!(svxb_picture(&svxb[..k]), None, "cut at {k}");
        }
        assert_eq!(svxb_picture(&[&svxb[..12], &[0xff; 4][..], &svxb[16..]].concat()), None, "fields past the end");
        // A PDF or PNG file copied in Finder (its path) or the file manager (a file:// list).
        let dir = std::env::temp_dir().join(format!("octet-copied-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join("aspirin.pdf");
        std::fs::write(&file, &pdf).unwrap();
        assert_eq!(clip(System::Mac, |n| (n == FILE_URL).then(|| file.to_string_lossy().as_bytes().to_vec())).cdxml.as_deref(), Some(doc.as_str()));
        let url = tauri::Url::from_file_path(&file).unwrap();
        assert_eq!(clip(System::Linux, |n| (n == "text/uri-list").then(|| format!("# copied\r\n{url}\r\n").into_bytes())).cdxml.as_deref(), Some(doc.as_str()));
        std::fs::write(dir.join("aspirin.txt"), &pdf).unwrap();
        assert_eq!(copied_drawing(&dir.join("aspirin.txt").to_string_lossy()), None, "only pictures are read");
        // Only a file: a folder (or a pipe, which would never end) named like a picture is not read.
        std::fs::create_dir(dir.join("folder.pdf")).unwrap();
        assert_eq!(copied_drawing(&dir.join("folder.pdf").to_string_lossy()), None);
        std::fs::remove_dir_all(&dir).unwrap();
        // Octet's own JSON, when there, wins over the picture.
        assert_eq!(clip(System::Mac, |n| [PDF, OCTET].contains(&n).then(|| if n == PDF { pdf.clone() } else { b"{}".to_vec() })).cdxml, None);
    }

    // Office's zip is hostile: a broken or cut-short zip, a bomb, or a zip with no pictures gives nothing, quickly.
    #[test]
    fn hostile_office_zips_give_nothing() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="0 0 20 10"><path d="M1 1H19V2H1Z"/></svg>"#;
        let pdf = crate::export::make_pdf(svg, Some("<CDXML/>"), None).unwrap();
        let good = office_zip(&[("clipboard/media/image1.pdf", &pdf)]);
        assert!(cdxml_from_office(&good).is_some());
        for k in 0..good.len() {
            assert_eq!(cdxml_from_office(&good[..k]), None, "cut at {k}");
        }
        let mut wrong = good.clone();
        let at = good.len() - 6;
        wrong[at..at + 4].copy_from_slice(&u32::MAX.to_le_bytes()); // the directory's offset past the end
        assert_eq!(cdxml_from_office(&wrong), None);
        assert_eq!(cdxml_from_office(&office_zip(&[("clipboard/media/image1.pdf", b"%PDF-1.4 not a pdf"), ("word/media/image2.pdf", &pdf)])), None);
        // 100 MB of zeros in one picture: inflating stops at 64 MB.
        let t = std::time::Instant::now();
        assert_eq!(cdxml_from_office(&office_zip(&[("clipboard/media/image1.emf", &vec![0; 100 << 20])])), None);
        // Many pictures without a drawing: only the first four are inflated.
        let many: Vec<(String, Vec<u8>)> = (0..60).map(|k| (format!("clipboard/media/image{k}.png"), vec![0; 1 << 20])).collect();
        let many: Vec<(&str, &[u8])> = many.iter().map(|(n, b)| (n.as_str(), b.as_slice())).collect();
        assert_eq!(cdxml_from_office(&office_zip(&many)), None);
        assert!(t.elapsed() < std::time::Duration::from_secs(10), "{:?}", t.elapsed());
        assert_eq!(cdxml_from_office(&[0; 21]), None);
        assert_eq!(cdxml_from_office(b"PK\x05\x06\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\0\0"), None);
    }

    // Every part of a zip, read from its central directory: each inflated (or taken as it is, if it is stored) and
    // checked against its size and CRC-32, with a local header that agrees with the directory.
    fn unzip(zip: &[u8]) -> Vec<(String, Vec<u8>)> {
        let u16_at = |k: usize| u16::from_le_bytes([zip[k], zip[k + 1]]) as usize;
        let u32_at = |k: usize| u32::from_le_bytes(zip[k..k + 4].try_into().unwrap()) as usize;
        let end = zip.len() - 22;
        assert_eq!(&zip[end..end + 4], b"PK\x05\x06");
        let (mut at, mut out) = (u32_at(end + 16), Vec::new());
        for _ in 0..u16_at(end + 10) {
            assert_eq!(&zip[at..at + 4], b"PK\x01\x02");
            let (method, crc, packed, size, name_len, local) = (u16_at(at + 10), u32_at(at + 16), u32_at(at + 20), u32_at(at + 24), u16_at(at + 28), u32_at(at + 42));
            assert_eq!(&zip[local..local + 4], b"PK\x03\x04");
            assert_eq!(zip[local + 4..local + 30], zip[at + 6..at + 32], "the local header agrees with the directory");
            let start = local + 30 + name_len;
            let data = match method {
                0 => zip[start..start + packed].to_vec(),
                8 => miniz_oxide::inflate::decompress_to_vec(&zip[start..start + packed]).unwrap(),
                m => panic!("method {m}"),
            };
            assert_eq!((data.len(), crate::export::crc32(&data) as usize), (size, crc));
            out.push((String::from_utf8(zip[at + 46..at + 46 + name_len].to_vec()).unwrap(), data));
            at += 46 + name_len;
        }
        assert_eq!(at, end, "the directory ends where the end record starts");
        out
    }

    // Each part's method, from the central directory: 8 deflated, 0 stored.
    fn methods(zip: &[u8]) -> Vec<u16> {
        let u16_at = |k: usize| u16::from_le_bytes([zip[k], zip[k + 1]]);
        let (end, mut out) = (zip.len() - 22, Vec::new());
        let mut at = u32::from_le_bytes(zip[end + 16..end + 20].try_into().unwrap()) as usize;
        for _ in 0..u16_at(end + 10) {
            out.push(u16_at(at + 10));
            at += 46 + usize::from(u16_at(at + 28));
        }
        out
    }

    // The system's own unzip finds nothing wrong with a zip, where there is one.
    fn system_unzip_passes(zip: &[u8], name: &str) {
        if !std::path::Path::new("/usr/bin/unzip").exists() {
            return;
        }
        let file = std::env::temp_dir().join(format!("octet-{name}-{}.zip", std::process::id()));
        std::fs::write(&file, zip).unwrap();
        let out = std::process::Command::new("/usr/bin/unzip").arg("-t").arg(&file).output().unwrap();
        std::fs::remove_file(&file).unwrap();
        assert!(out.status.success(), "{}{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
    }

    // The Mac's copy for Word: Office's own copy of the picture first, then the PDF. The copy is a sound zip with the
    // parts Office's has, and its picture is Octet's EMF with that same PDF in its first comment and the CDXML in the
    // next. Paste reads the drawing back from Octet's copy and from Word's copy of the picture. Windows and Linux put
    // on what they did.
    #[test]
    fn mac_copy_puts_offices_copy_first() {
        let svg = crate::vector::tests::PROLINE;
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        let t = types(System::Mac, Some(svg), 600.0, Some(x), false, None, Some(MOL), Some("CO"), Some("{}".into())).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF, MOLFILE, SMILES, OCTET]);
        let (zip, pdf) = (&t[0].1, &t[1].1);
        assert_eq!(pdf, &crate::export::make_pdf(svg, Some(x), None).unwrap(), "the PDF is the one Copy put on before");
        assert_eq!(mac_picture(svg, Some(x)).unwrap(), t[..2], "Copy's two pictures are the ones Update in Word gives");
        let parts = unzip(zip);
        assert_eq!(methods(zip), [8; 6], "every part deflated, the form Word has taken");
        let names: Vec<&str> = parts.iter().map(|(n, _)| n.as_str()).collect();
        assert_eq!(names, ["[Content_Types].xml", "_rels/.rels", "clipboard/drawings/drawing1.xml", "clipboard/drawings/_rels/drawing1.xml.rels", "clipboard/theme/theme1.xml", "clipboard/media/image1.emf"]);
        let part = |n: &str| &parts.iter().find(|(p, _)| p == n).unwrap().1;
        let text = |n: &str| String::from_utf8(part(n).clone()).unwrap();
        // The picture's file: the header (108 bytes), then the comment (its kind and size, the data's size, "GDIC" and
        // 56 more bytes of fields), with the PDF's bytes 60 into the data.
        let tree = crate::export::tree(svg).unwrap();
        let emf = part("clipboard/media/image1.emf");
        assert_eq!(emf, &crate::vector::make_emf(&tree, Some(x), Some(pdf)));
        assert_eq!((&emf[108..112], &emf[120..124], &emf[180..180 + pdf.len()]), (&[70, 0, 0, 0][..], &b"GDIC"[..], &pdf[..]));
        assert_eq!(crate::vector::cdxml_from_emf(emf).as_deref(), Some(x));
        assert_eq!(cdxml_from_office(zip).as_deref(), Some(x));
        // The XML parts are well formed. The drawing gives the picture's size three times (the group, its children's
        // space, the picture) in EMU: 56.21 by 36.55 pt is 713,867 by 464,185.
        for (name, data) in parts.iter().filter(|(n, _)| !n.ends_with(".emf")) {
            let xml = std::str::from_utf8(data).unwrap();
            assert!(svg2pdf::usvg::roxmltree::Document::parse(xml).is_ok(), "{name}: {xml}");
        }
        let drawing = text("clipboard/drawings/drawing1.xml");
        let (w, h) = crate::vector::size(&tree);
        let (cx, cy) = ((f64::from(w) * 12_700.0).round() as i64, (f64::from(h) * 12_700.0).round() as i64);
        assert!((cx - 713_867).abs() <= 13 && (cy - 464_185).abs() <= 13, "{cx} by {cy}");
        assert_eq!(drawing.matches(&format!(r#" cx="{cx}" cy="{cy}"/>"#)).count(), 3, "{drawing}");
        // Each relationship points to a part that is there, and the content types name the drawing and the theme.
        assert!(text("_rels/.rels").contains(r#"Target="clipboard/drawings/drawing1.xml""#));
        let rels = text("clipboard/drawings/_rels/drawing1.xml.rels");
        assert!(rels.contains(r#"Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.emf""#) && rels.contains(r#"Target="../theme/theme1.xml""#), "{rels}");
        assert!(drawing.contains(r#"r:embed="rId1""#));
        let content = text("[Content_Types].xml");
        assert!(content.contains(r#"Extension="emf""#) && content.contains(r#"PartName="/clipboard/drawings/drawing1.xml""#) && content.contains(r#"PartName="/clipboard/theme/theme1.xml""#));
        system_unzip_passes(zip, "office");
        // The two pictures as files, to put on a clipboard by hand and paste into Word.
        if let Ok(dir) = std::env::var("OCTET_CLIPBOARD_SAMPLES") {
            for (name, bytes) in [("office-copy.zip", zip), ("copy.pdf", pdf), ("image1.emf", emf)] {
                std::fs::write(std::path::Path::new(&dir).join(name), bytes).unwrap();
            }
        }
        // Paste in Octet from Octet's copy: its own JSON, as before.
        let c = clip(System::Mac, |name| t.iter().find(|(n, _)| *n == name).map(|(_, b)| b.clone()));
        assert_eq!((c.octet.as_deref(), c.cdxml.as_deref(), c.molfile.as_deref()), (Some("{}"), None, Some(MOL)));
        // Paste from Word's copy of the picture: Office's copy with Octet's EMF as it went in, and the PDF from the
        // EMF's comment (with a TIFF). The drawing comes from the PDF; from the EMF if Office's copy is there alone.
        let word = |n: &str| match n {
            OFFICE => Some(office_zip(&[("[Content_Types].xml", b"<Types/>"), ("clipboard/media/image1.emf", emf)])),
            PDF => Some(emf[180..180 + pdf.len()].to_vec()),
            "public.tiff" => Some(b"MM\0*".to_vec()),
            _ => None,
        };
        assert_eq!(clip(System::Mac, word).cdxml.as_deref(), Some(crate::export::cdxml_document(x).as_str()));
        assert_eq!(clip(System::Mac, |n| (n == OFFICE).then(|| zip.clone())).cdxml.as_deref(), Some(x));
        // A copy with no CDXML still has Office's copy. Windows and Linux have none (their lists are in
        // windows_and_linux_copy_the_same).
        let t = types(System::Mac, Some(svg), 600.0, None, false, None, None, None, None).unwrap();
        assert_eq!((t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), cdxml_from_office(&t[0].1)), (vec![OFFICE, PDF], None));
        for s in [System::Windows, System::Linux] {
            let t = types(s, Some(svg), 600.0, Some(x), true, None, Some(MOL), Some("CO"), Some("{}".into())).unwrap();
            assert!(!t.iter().any(|(n, _)| n.contains("GVML")), "{s:?}");
        }
    }

    // A drawing that holds a picture (a photo, a pasted screenshot) gets Office's copy too: its EMF has the picture as
    // pixels after the same PDF and CDXML comments. Over the size limit the PDF goes alone, as it did for every such
    // drawing before.
    #[test]
    fn a_drawing_with_a_picture_gets_offices_copy() {
        let svg = crate::vector::tests::picture_svg();
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        let t = types(System::Mac, Some(&svg), 600.0, Some(x), false, None, None, Some("CO"), Some("{}".into())).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF, SMILES, OCTET]);
        let (zip, pdf) = (&t[0].1, &t[1].1);
        assert_eq!(pdf, &crate::export::make_pdf(&svg, Some(x), None).unwrap());
        let tree = crate::export::tree(&svg).unwrap();
        let parts = unzip(zip);
        let emf = &parts[5].1;
        assert_eq!((parts[5].0.as_str(), emf), ("clipboard/media/image1.emf", &crate::vector::make_emf(&tree, Some(x), Some(pdf))));
        // The picture's record (EMR_STRETCHDIBITS) is there: 4 by 2 pixels in rows of 12 bytes, after a 40-byte header.
        let record = [&[81u8, 0, 0, 0][..], &(80u32 + 40 + 24).to_le_bytes()].concat();
        assert!(emf.windows(8).any(|w| w == record));
        assert_eq!(crate::vector::pixel_bytes(&tree), 24);
        assert_eq!(crate::vector::pixel_bytes(&crate::export::tree(crate::vector::tests::PROLINE).unwrap()), 0);
        assert_eq!((cdxml_from_office(zip).as_deref(), methods(zip)), (Some(x), vec![8; 6]));
        system_unzip_passes(zip, "office-picture");
        // The limit: the pixels and the CDXML over it (no EMF is made), the EMF with the PDF over it by a byte, and
        // the EMF at it. The size is known before the PDF goes in.
        let kinds = |most: usize| mac_picture_within(&svg, Some(x), most).unwrap().iter().map(|(t, _)| *t).collect::<Vec<_>>();
        assert_eq!((kinds(23 + x.len()), kinds(24 + x.len()), kinds(emf.len() - 1), kinds(emf.len())), (vec![PDF], vec![PDF], vec![PDF], vec![OFFICE, PDF]));
        assert_eq!(crate::vector::make_emf(&tree, Some(x), None).len() + crate::vector::pdf_comment(pdf.len()), emf.len());
        assert_eq!(mac_picture_within(&svg, Some(x), 23).unwrap()[0].1, *pdf, "the PDF alone is the same PDF");
        assert_eq!(mac_picture(&svg, Some(x)).unwrap(), t[..2]);
        // A PDF Octet cannot make is Copy's error, as before; Office's copy changes none.
        assert!(mac_picture("<svg", None).is_err());
    }

    // In Office's copy, an EMF over 1 MB is stored, and one of 1 MB or less is deflated like the other parts. Both are
    // sound zips, and paste reads the drawing from both.
    #[test]
    fn offices_copy_stores_a_large_emf() {
        let x = "<CDXML><page/></CDXML>";
        let small = crate::vector::make_emf(&crate::export::tree(crate::vector::tests::PROLINE).unwrap(), Some(x), None);
        // An EMF with a record of zeros at its end is still one for paste's reader, which stops at the CDXML comment.
        let padded = |len: usize| [&small[..], &vec![0; len - small.len()]].concat();
        for (len, emf_method) in [(STORED_OVER + 1, 0), (STORED_OVER, 8)] {
            let emf = padded(len);
            let zip = office_package((56.21, 36.55), &emf);
            assert_eq!(methods(&zip), [8, 8, 8, 8, 8, emf_method], "{len} bytes");
            let parts = unzip(&zip);
            assert!(parts[5].1 == emf && parts.len() == 6);
            assert_eq!(cdxml_from_office(&zip).as_deref(), Some(x));
            system_unzip_passes(&zip, "office-stored");
            // Stored: the EMF's bytes are in the zip as they are, and the zip is little larger than the EMF.
            assert_eq!(zip.windows(small.len()).any(|w| w == &small[..]), emf_method == 0);
            assert!(emf_method == 8 || zip.len() < emf.len() + 4_096);
        }
        assert!(MAX_OFFICE > STORED_OVER && MAX_OFFICE <= MAX_TYPE, "paste's limit takes every copy Octet makes");
    }

    // A drawing that holds one picture of `w` by `h` px, drawn `inches` wide, with a bond and a label over it, and its
    // CDXML, which holds the picture's file as hex as the page writes it (cdxml.ts). The picture follows no pattern a
    // deflater likes, as a photo does. A JPEG at `quality` (a photo), or with None a PNG (a pasted screenshot).
    fn photo(w: u32, h: u32, quality: Option<u8>, inches: f32) -> (String, String) {
        use base64::Engine;
        let mut x = 0x2545_F491u32;
        let mut rgb = Vec::with_capacity((w * h * 3) as usize);
        for row in 0..h {
            for col in 0..w {
                x ^= x << 13;
                x ^= x >> 17;
                x ^= x << 5;
                let noise = x >> 28;
                rgb.extend([(col * 220 / w + noise) as u8, (row * 220 / h + noise) as u8, ((col + row) * 110 / w + noise) as u8]);
            }
        }
        let mut file = Vec::new();
        let (mime, key) = if let Some(q) = quality {
            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut file, q).encode(&rgb, w, h, image::ExtendedColorType::Rgb8).unwrap();
            ("image/jpeg", "JPEG")
        } else {
            let mut enc = png::Encoder::new(&mut file, w, h);
            enc.set_color(png::ColorType::Rgb);
            enc.set_depth(png::BitDepth::Eight);
            enc.write_header().unwrap().write_image_data(&rgb).unwrap();
            ("image/png", "PNG")
        };
        let data = base64::engine::general_purpose::STANDARD.encode(&file);
        let hex: String = file.iter().map(|b| format!("{b:02X}")).collect();
        let (pw, ph) = (inches * 72.0, inches * 72.0 * h as f32 / w as f32);
        let svg = format!(
            r#"<svg xmlns="http://www.w3.org/2000/svg" width="{}pt" height="{}pt" viewBox="0 0 {} {}"><image href="data:{mime};base64,{data}" x="9" y="9" width="{pw}" height="{ph}" preserveAspectRatio="none"/><path d="M40 60L64 74L88 60" fill="none" stroke="rgb(255, 255, 255)" stroke-width="1.2"/><text x="90" y="64" fill="rgb(255, 255, 255)" font-family="Arial, Helvetica, sans-serif" font-size="10">OH</text></svg>"#,
            pw + 18.0, ph + 18.0, pw + 18.0, ph + 18.0
        );
        let cdxml = format!(r#"<CDXML><page><fragment><n id="1"/></fragment><embeddedobject id="2" BoundingBox="9 9 {} {}" {key}="{hex}"/></page></CDXML>"#, pw + 9.0, ph + 9.0);
        (svg, cdxml)
    }

    // The limit counts everything the EMF holds. A small photo (300 by 200 px, drawn 1 in wide, so every pixel is
    // kept) with its file as hex in the CDXML: the EMF is the pixels, the CDXML and the PDF, and Office's copy is
    // there at that size and not a byte under it. With the pixels and the CDXML alone over the limit, the same PDF.
    #[test]
    fn a_photos_file_counts_towards_the_limit() {
        let (svg, x) = photo(300, 200, Some(85), 1.0);
        let tree = crate::export::tree(&svg).unwrap();
        let t = mac_picture(&svg, Some(&x)).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF]);
        let (pixels, pdf) = (crate::vector::pixel_bytes(&tree), &t[1].1);
        assert_eq!(pixels, 300 * 200 * 3);
        let emf = &unzip(&t[0].1)[5].1;
        assert!(emf.len() > pixels + x.len() + pdf.len() && pdf.len() > x.len() / 4, "the EMF holds all three");
        assert_eq!(cdxml_from_office(&t[0].1).as_deref(), Some(x.as_str()));
        let kinds = |most: usize| mac_picture_within(&svg, Some(&x), most).unwrap().iter().map(|(t, _)| *t).collect::<Vec<_>>();
        assert_eq!((kinds(pixels + x.len() - 1), kinds(emf.len() - 1), kinds(emf.len())), (vec![PDF], vec![PDF], vec![OFFICE, PDF]));
        assert_eq!(mac_picture_within(&svg, Some(&x), pixels).unwrap()[0].1, *pdf);
    }

    // The two pictures of a drawing with a photo in it, as files, to put on a clipboard by hand and paste into Word:
    // Office's copy with its EMF stored, and the PDF. Only when asked, with the folder to write them to:
    // OCTET_PHOTO_SAMPLES=<folder> cargo test --release --bin octet photo_samples -- --ignored
    #[test]
    #[ignore]
    fn photo_samples() {
        let dir = std::env::var("OCTET_PHOTO_SAMPLES").expect("OCTET_PHOTO_SAMPLES names the folder");
        let (svg, x) = photo(1800, 1200, Some(85), 6.0);
        let t = mac_picture(&svg, Some(&x)).unwrap();
        assert_eq!(t.iter().map(|(t, _)| *t).collect::<Vec<_>>(), [OFFICE, PDF]);
        let (zip, pdf) = (&t[0].1, &t[1].1);
        assert_eq!(methods(zip), [8, 8, 8, 8, 8, 0], "the EMF is stored");
        let emf = &unzip(zip)[5].1;
        assert!(emf.len() > 1_800 * 1_200 * 3 && emf[180..180 + pdf.len()] == pdf[..]);
        system_unzip_passes(zip, "office-photo");
        for (name, bytes) in [("office-copy.zip", zip), ("copy.pdf", pdf), ("image1.emf", emf)] {
            std::fs::write(std::path::Path::new(&dir).join(name), bytes).unwrap();
        }
    }

    // No step back (decision 0024): Copy on the Mac makes Office's copy as well as the PDF, from one reading of the SVG,
    // so it takes little longer than the PDF alone, which is what Copy made before: a tenth more and 2 ms at most.
    // This prints both times and what Office's copy takes. A drawing of 60 bonds and 12 labels; the middle of 9 runs of
    // each, taken in turn, so other work on the computer slows both alike.
    // Then the same for drawings that hold one picture (photo), with the picture's file in the CDXML as the page
    // sends it. Their Copy made the PDF alone before, and now waits for the picture's pixels to be drawn for the EMF
    // (on a thread beside the PDF), so it takes longer when the EMF takes longer than the PDF. These times are printed
    // and not judged.
    // A clock on a busy computer can fail it, so it runs only when asked, and it judges only a release build (a debug
    // build deflates many times slower): cargo test --release --bin octet mac_copy_time -- --ignored --nocapture
    #[test]
    #[ignore]
    fn mac_copy_time() {
        let mut svg = String::from(r#"<svg xmlns="http://www.w3.org/2000/svg" width="320pt" height="200pt" viewBox="0 0 320 200">"#);
        for k in 0..60 {
            let (x, y) = (10.0 + 24.0 * (k % 12) as f32, 20.0 + 36.0 * (k / 12) as f32 + 6.0 * (k % 3) as f32);
            svg += &format!(r#"<path d="M{x} {y}L{} {}" stroke="rgb(0, 0, 0)" stroke-width="0.6"/>"#, x + 12.0, y + 7.0);
        }
        for (k, label) in ["O", "OH", "N", "NH", "O", "S", "Cl", "OH", "O", "N", "F", "O"].iter().enumerate() {
            svg += &format!(r#"<text x="{}" y="{}" font-family="Arial, Helvetica, sans-serif" font-size="10">{label}</text>"#, 20 + 24 * k, 50 + 36 * (k % 4));
        }
        svg += "</svg>";
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        let time = |f: &dyn Fn()| {
            let t = std::time::Instant::now();
            f();
            t.elapsed()
        };
        let middle = |mut v: Vec<std::time::Duration>| {
            v.sort();
            v[v.len() / 2]
        };
        // The middle time of each step for one drawing: the PDF alone (all of Copy's picture before Office's copy, and
        // before this change for a drawing with a picture), Copy now, reading the SVG, the EMF's records, the PDF put
        // into them, the EMF's CRC-32, and the zip (with that CRC-32).
        let times = |svg: &str, x: &str| {
            let pdf = crate::export::make_pdf(svg, Some(x), None).unwrap();
            let tree = crate::export::tree(svg).unwrap();
            let records = crate::vector::make_emf(&tree, Some(x), None);
            let emf = crate::vector::with_pdf(&records, &pdf);
            let mut all: [Vec<std::time::Duration>; 7] = Default::default();
            for _ in 0..9 {
                let steps: [&dyn Fn(); 7] = [
                    &|| drop(crate::export::make_pdf(svg, Some(x), None).unwrap()),
                    &|| drop(types(System::Mac, Some(svg), 600.0, Some(x), false, None, None, None, None).unwrap()),
                    &|| drop(crate::export::tree(svg).unwrap()),
                    &|| drop(crate::vector::make_emf(&tree, Some(x), None)),
                    &|| drop(crate::vector::with_pdf(&records, &pdf)),
                    &|| drop(std::hint::black_box(vec![crate::export::crc32(std::hint::black_box(&emf))])),
                    &|| drop(office_package(crate::vector::size(&tree), &emf)),
                ];
                for (list, step) in all.iter_mut().zip(steps) {
                    list.push(time(step));
                }
            }
            let package = office_package(crate::vector::size(&tree), &emf);
            (all.map(middle), pdf.len(), emf.len(), package.len(), methods(&package)[5])
        };
        let ([before, now, read, records, with_pdf, crc, zip], pdf, emf, package, _) = times(&svg, x);
        eprintln!("Copy on the Mac: {now:?}; the PDF alone, as before: {before:?}. Reading the SVG, once for both: {read:?}. Office's copy: the EMF's records {records:?} (beside the PDF), the PDF put in {with_pdf:?}, the zip {zip:?} (its CRC-32 {crc:?}). The PDF is {pdf} bytes, the EMF {emf}, Office's copy {package}.");
        assert!(cfg!(debug_assertions) || now <= before + before / 10 + std::time::Duration::from_millis(2), "Copy takes {now:?}, the PDF alone {before:?}");
        let photos = [
            ("1,800 by 1,200 px, a JPEG, drawn 6 in wide", 1800, 1200, Some(85), 6.0),
            ("1,800 by 1,200 px, a PNG (a screenshot), drawn 6 in wide", 1800, 1200, None, 6.0),
            ("4,032 by 3,024 px (a phone's photo), a JPEG, drawn 6 in wide", 4032, 3024, Some(85), 6.0),
            ("4,032 by 3,024 px, a JPEG with a small file, drawn 8 in wide", 4032, 3024, Some(40), 8.0),
        ];
        for (name, w, h, quality, inches) in photos {
            let (svg, x) = photo(w, h, quality, inches);
            let ([before, now, read, records, with_pdf, crc, zip], pdf, emf, package, method) = times(&svg, &x);
            eprintln!("Copy of a drawing with one picture of {name}: {now:?}; the PDF alone, which was Copy before: {before:?}. Reading the SVG: {read:?}. Office's copy: the EMF's records {records:?} (beside the PDF), the PDF put in {with_pdf:?}, the zip {zip:?} (its CRC-32 {crc:?}). The CDXML is {} bytes, the PDF {pdf}, the EMF {emf}, Office's copy {package} (the EMF's method {method}).", x.len());
            assert!(emf <= MAX_OFFICE && method == 0, "this picture is under the limit, and its EMF is stored");
        }
    }

    // No step back (decision 0024): Copy on Linux makes the PDF while it draws the PNG, so it takes no longer than 1.1.1's
    // PNG and SVG. A drawing the size of aspirin with its labels; the middle of 9 runs of each, taken in turn, so
    // other tests running at the same time slow both alike.
    // A clock on a busy computer can fail it, so it runs only when asked: cargo test linux_copy_takes_no_longer -- --ignored
    #[test]
    #[ignore]
    fn linux_copy_takes_no_longer() {
        let mut svg = String::from(r#"<svg xmlns="http://www.w3.org/2000/svg" width="160pt" height="120pt" viewBox="0 0 160 120">"#);
        for k in 0..13 {
            let (x, y) = (10.0 + 10.0 * k as f32, 20.0 + 6.0 * (k % 3) as f32);
            svg += &format!(r#"<path d="M{x} {y}L{} {}" stroke="rgb(0, 0, 0)" stroke-width="0.6"/>"#, x + 12.0, y + 7.0);
        }
        for (k, label) in ["O", "OH", "O", "O"].iter().enumerate() {
            svg += &format!(r#"<text x="{}" y="80" font-family="Arial, Helvetica, sans-serif" font-size="10">{label}</text>"#, 20 + 30 * k);
        }
        svg += "</svg>";
        let x = "<CDXML><page><fragment><n id=\"1\"/></fragment></page></CDXML>";
        let time = |f: &dyn Fn()| {
            let t = std::time::Instant::now();
            f();
            t.elapsed()
        };
        let (mut before, mut now) = (Vec::new(), Vec::new());
        for _ in 0..9 {
            before.push(time(&|| {
                crate::export::clipboard_pictures(&svg, false, 600.0, Some(x)).unwrap();
                crate::export::px_units(&svg);
            }));
            now.push(time(&|| {
                types(System::Linux, Some(&svg), 600.0, Some(x), false, None, None, None, None).unwrap();
            }));
        }
        before.sort();
        now.sort();
        let (before, now) = (before[4], now[4]);
        eprintln!("Copy on Linux: {now:?}, 1.1.1's pictures: {before:?}");
        assert!(now <= before + before / 10 + std::time::Duration::from_millis(2), "Copy takes {now:?}, 1.1.1 took {before:?}");
    }

    // Paste on Linux asks the clipboard's owner only for what it uses: no PDF from Inkscape, and no PDF or LibreOffice
    // copy beside Octet's own JSON or CDXML. A picture copied in LibreOffice still gives both.
    #[test]
    fn linux_paste_asks_for_what_it_uses() {
        let asks = |offered: &[&str]| {
            let present: Vec<String> = offered.iter().map(|n| n.to_string()).collect();
            readable(System::Linux).into_iter().filter(|n| asked(n, &present)).collect::<Vec<_>>()
        };
        assert_eq!(asks(&["TARGETS", "image/x-inkscape-svg", "image/svg+xml", "application/pdf", "image/png"]), ["image/png"]);
        assert_eq!(asks(&["image/png", "application/pdf", "image/svg+xml", "chemical/x-cdxml", "application/x-octet+json"]), ["application/x-octet+json", "chemical/x-cdxml", "image/png"]);
        assert_eq!(asks(&["chemical/x-cdxml", "application/pdf", SVXB]), ["chemical/x-cdxml"]);
        assert_eq!(asks(&[SVXB, "application/pdf", "image/png", "text/plain"]), ["application/pdf", SVXB, "text/plain", "image/png"]);
    }

    // CH-7: Copy As puts the text alone, under each system's names for text (on Windows UTF-16 with a NUL).
    #[test]
    fn copy_as_puts_text() {
        assert_eq!(text_types(System::Mac, "CCO"), [("public.utf8-plain-text", b"CCO".to_vec())]);
        assert_eq!(text_types(System::Windows, "Cé"), [(UNICODE_TEXT, vec![b'C', 0, 0xe9, 0, 0, 0])]);
        assert_eq!(text_types(System::Linux, "CCO").iter().map(|(n, _)| *n).collect::<Vec<_>>(), ["text/plain;charset=utf-8", "UTF8_STRING", "text/plain"]);
    }

    // A long drawing goes on the clipboard at a lower resolution, so the picture has at most 8,192 pixels on a side.
    #[test]
    fn large_pictures_fit() {
        let svg = r#"<svg xmlns="http://www.w3.org/2000/svg" width="3000pt" height="100pt" viewBox="0 0 3000 100"><path d="M1 1H2999V99H1Z"/></svg>"#;
        let (png, dib) = crate::export::clipboard_pictures(svg, true, 600.0, None).unwrap();
        let width = u32::from_be_bytes(png[16..20].try_into().unwrap());
        assert_eq!(width, 8192);
        assert_eq!(i32::from_le_bytes(dib.unwrap()[4..8].try_into().unwrap()), 8192);
    }

    // On a private pasteboard, so the user's clipboard is untouched.
    #[cfg(target_os = "macos")]
    #[test]
    fn pasteboard_keeps_type_order() {
        use objc2_app_kit::NSPasteboard;
        let pb = NSPasteboard::pasteboardWithUniqueName();
        let t = vec![(OFFICE, b"PK\x05\x06".to_vec()), (PDF, b"%PDF-1.7".to_vec()), (MOLFILE, prefixed_lines(MOL).unwrap()), (SMILES, b"CO\0".to_vec()), (OCTET, b"{}".to_vec())];
        mac::write(&pb, &t).unwrap();
        let names: Vec<String> = pb.types().unwrap().iter().map(|s| s.to_string()).collect();
        let ours: Vec<&str> = names.iter().map(String::as_str).filter(|n| t.iter().any(|(x, _)| x == n)).collect();
        assert_eq!(ours, [OFFICE, PDF, MOLFILE, SMILES, OCTET], "{names:?}");
        let c = mac::read(&pb);
        assert_eq!((c.octet.as_deref(), c.smiles.as_deref(), c.molfile.as_deref(), c.text.as_deref()), (Some("{}"), Some("CO"), Some(MOL), None));
        pb.clearContents();
    }
}
