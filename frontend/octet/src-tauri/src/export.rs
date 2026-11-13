// File > Export… and the picture on the clipboard. The page sends a standalone SVG of the drawing at true size
// (src/export.ts); this makes a vector PDF, EPS or EMF (vector.rs), or a PNG, TIFF, JPEG, GIF or BMP of it. The PDF carries the drawing's CDXML in its catalog
// /Metadata stream, as ChemDraw's does, so a picture pasted into Word and copied out again pastes back into
// Octet and ChemDraw as a structure. cdxml_from_pdf reads it back from any PDF, treated as hostile.

use std::cell::Cell;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};

use base64::Engine;
use pdf_writer::{Content, Filter, Finish, Name, Pdf, Rect, Ref, TextStr};
use svg2pdf::usvg::{self, fontdb};
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

const MAX_SVG: usize = 64 << 20;
const MAX_PDF: usize = 64 << 20;
const MAX_XML: usize = 32 << 20;

// The system's fonts, loaded once. Labels are embedded from them as subsets (Arial on the Mac and Windows).
// Linux has no Arial unless the user adds it, so labels fall back to a font with Arial's widths (Liberation Sans,
// Arimo), or else a common sans; with no fallback the labels would be left out of the PDF.
const NO_ARIAL: [&str; 5] = ["Liberation Sans", "Arimo", "Helvetica", "DejaVu Sans", "Noto Sans"];
fn fonts() -> Arc<fontdb::Database> {
    static FONTS: OnceLock<Arc<fontdb::Database>> = OnceLock::new();
    FONTS.get_or_init(|| {
        let mut db = fontdb::Database::new();
        db.load_system_fonts();
        let has = |db: &fontdb::Database, name: &str| db.faces().any(|f| f.families.iter().any(|(n, _)| n == name));
        if !has(&db, "Arial") {
            if let Some(name) = NO_ARIAL.into_iter().find(|n| has(&db, n)) {
                db.set_sans_serif_family(name);
            }
        }
        Arc::new(db)
    }).clone()
}

// Every font family on the computer, for the font lists, as ChemDraw's Font menu lists every installed font. Hidden
// system fonts (their names start with a dot) are left out.
#[tauri::command]
pub async fn system_fonts() -> Vec<String> {
    let mut names: Vec<String> = fonts()
        .faces()
        .filter_map(|f| f.families.first().map(|(n, _)| n.trim().to_string()))
        .filter(|n| !n.is_empty() && !n.starts_with('.') && n.len() <= 64)
        .collect();
    names.sort_by_cached_key(|n| n.to_lowercase());
    names.dedup();
    names
}

pub fn tree(svg: &str) -> Result<usvg::Tree, String> {
    if svg.len() > MAX_SVG {
        return Err("This drawing is too large to export.".into());
    }
    let mut opt = usvg::Options::default();
    opt.fontdb = fonts();
    // usvg reads <image> files from disk by default. The picture holds only what the page drew.
    opt.image_href_resolver.resolve_string = Box::new(|_, _| None);
    usvg::Tree::from_str(svg, &opt).map_err(|e| {
        eprintln!("usvg: {e}");
        "Octet cannot draw this picture.".to_string()
    })
}

// The CDXML as ChemDraw hides it: the XML declaration at byte 0 and the CDXML DOCTYPE on line 2.
pub fn cdxml_document(cdxml: &str) -> String {
    let mut s = cdxml.trim_start_matches('\u{feff}').trim_start();
    if s.starts_with("<?xml") {
        s = s.find("?>").map_or(s, |k| &s[k + 2..]).trim_start();
    }
    if s.starts_with("<!DOCTYPE") {
        s = s.find('>').map_or(s, |k| &s[k + 1..]).trim_start();
    }
    format!("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<!DOCTYPE CDXML SYSTEM \"http://www.cambridgesoft.com/xml/cdxml.dtd\" >\n{s}")
}

// The drawing's title, author and keywords (Settings > Document > Properties), for a PDF's document information.
#[derive(serde::Deserialize)]
pub struct Info {
    title: Option<String>,
    author: Option<String>,
    keywords: Option<String>,
}

// A vector PDF of the SVG at true size: the page is the SVG's box (1 pt per pt, CSS units honoured), text stays
// text in embedded font subsets, and nothing paints the background. With CDXML, the catalog gets a /Metadata
// stream holding it (/Type /Metadata /Subtype /XML, Flate, /Vendor /org.octet). With `info`, the document
// information gets the title, author and keywords that are set.
pub fn make_pdf(svg: &str, cdxml: Option<&str>, info: Option<&Info>) -> Result<Vec<u8>, String> {
    pdf_of(&tree(svg)?, cdxml, info)
}

// make_pdf for an SVG that is read already, so Copy on the Mac reads it once for the PDF and for Office's copy.
pub fn pdf_of(tree: &usvg::Tree, cdxml: Option<&str>, info: Option<&Info>) -> Result<Vec<u8>, String> {
    pdf_pages(&[tree], cdxml, info)
}

// The pages Octet sends for a PDF of several pages (an experiment page and its risk assessment), at most MAX_PAGES.
pub const MAX_PAGES: usize = 64;
pub fn make_pdf_pages(svgs: &[String], cdxml: Option<&str>, info: Option<&Info>) -> Result<Vec<u8>, String> {
    if svgs.is_empty() || svgs.len() > MAX_PAGES {
        return Err("Octet cannot export this many pages.".into());
    }
    let trees = svgs.iter().map(|s| tree(s)).collect::<Result<Vec<_>, _>>()?;
    pdf_pages(&trees.iter().collect::<Vec<_>>(), cdxml, info)
}

// A PDF with a page for each SVG, each page the SVG's box.
fn pdf_pages(trees: &[&usvg::Tree], cdxml: Option<&str>, info: Option<&Info>) -> Result<Vec<u8>, String> {
    let mut alloc = Ref::new(1);
    let [catalog, pages, meta] = [(); 3].map(|_| alloc.bump());
    // usvg measures in CSS px (96 to the inch); PDF in points (72). Rounded, so 86 pt stays 86, not 85.99999.
    let pt = |px: f32| (px * 750.0).round() / 1000.0;
    let mut pdf = Pdf::new();
    let mut cat = pdf.catalog(catalog);
    cat.pages(pages);
    if cdxml.is_some() {
        cat.metadata(meta);
    }
    cat.finish();
    let kids: Vec<Ref> = trees.iter().map(|_| alloc.bump()).collect();
    pdf.pages(pages).kids(kids.iter().copied()).count(kids.len() as i32);
    for (tree, &page) in trees.iter().zip(&kids) {
        let (chunk, picture) = svg2pdf::to_chunk(tree, svg2pdf::ConversionOptions::default()).map_err(|e| e.to_string())?;
        let content = alloc.bump();
        let mut map = HashMap::new();
        let chunk = chunk.renumber(|old| *map.entry(old).or_insert_with(|| alloc.bump()));
        let (w, h) = (pt(tree.size().width()), pt(tree.size().height()));
        let mut p = pdf.page(page);
        p.media_box(Rect::new(0.0, 0.0, w, h)).parent(pages).contents(content);
        p.resources().x_objects().pair(Name(b"S"), map[&picture]);
        p.finish();
        let mut c = Content::new();
        c.save_state().transform([w, 0.0, 0.0, h, 0.0, 0.0]).x_object(Name(b"S")).restore_state();
        pdf.stream(content, &c.finish());
        pdf.extend(&chunk);
    }
    if let Some(x) = cdxml {
        let data = miniz_oxide::deflate::compress_to_vec_zlib(cdxml_document(x).as_bytes(), 6);
        pdf.metadata(meta, &data).filter(Filter::FlateDecode).pair(Name(b"Vendor"), Name(b"org.octet"));
    }
    if let Some(i) = info.filter(|i| i.title.is_some() || i.author.is_some() || i.keywords.is_some()) {
        let mut d = pdf.document_info(alloc.bump());
        if let Some(v) = &i.title {
            d.title(TextStr(v));
        }
        if let Some(v) = &i.author {
            d.author(TextStr(v));
        }
        if let Some(v) = &i.keywords {
            d.keywords(TextStr(v));
        }
    }
    Ok(pdf.finish())
}

// The clipboard's SVG on Linux: the same width and height in pt, with 1 user unit = 1 px (96 to the inch), the unit
// Inkscape gives pasted content. Inkscape pastes an SVG's content in its own user units and drops the root's width,
// height and viewBox, so the picture as export writes it (1 user unit = 1 pt) pasted at 72/96, 75% of true size
// (issue 47). The view box is scaled by 4/3 and the content drawn in a group scaled by 4/3, so every reader that
// honours width and height sees the same picture. An SVG without a root view box is unchanged.
pub fn px_units(svg: &str) -> String {
    let scaled = || -> Option<String> {
        let start = svg.find("<svg")?;
        let open = start + svg[start..].find('>')?;
        let close = svg.rfind("</svg>").filter(|&k| k > open)?;
        let head = &svg[start..open];
        let at = start + head.find(" viewBox=\"")? + 10;
        let len = svg[at..open].find('"')?;
        let v: Vec<f64> = svg[at..at + len].split([' ', ',']).filter(|s| !s.is_empty()).map(str::parse).collect::<Result<_, _>>().ok()?;
        if v.len() != 4 || v.iter().any(|n| !n.is_finite()) || v[2] <= 0.0 || v[3] <= 0.0 {
            return None;
        }
        let box_ = v.iter().map(|n| format!("{}", n * 4.0 / 3.0)).collect::<Vec<_>>().join(" ");
        Some(format!("{}{box_}{}><g transform=\"scale(1.3333333333333333)\">{}</g>{}", &svg[..at], &svg[at + len..open], &svg[open + 1..close], &svg[close..]))
    };
    scaled().unwrap_or_else(|| svg.to_string())
}

// The SVG drawn at `dpi` of its true size, white or transparent behind. A part pixel at the edge counts; a rounding
// error does not (pixelsAt in src/export.ts counts the same, so Export… shows the size written).
fn draw(tree: &usvg::Tree, dpi: f32, transparent: bool) -> Result<resvg::tiny_skia::Pixmap, String> {
    use resvg::tiny_skia::{Color, Pixmap, Transform};
    let scale = dpi / 96.0;
    let (w, h) = ((tree.size().width() * scale - 0.01).ceil().max(1.0) as u32, (tree.size().height() * scale - 0.01).ceil().max(1.0) as u32);
    let too_big = "This picture is too large at this resolution. Choose a lower resolution.";
    if w > 20_000 || h > 20_000 || u64::from(w) * u64::from(h) > 100_000_000 {
        return Err(too_big.into());
    }
    let mut pixmap = Pixmap::new(w.max(1), h.max(1)).ok_or(too_big)?;
    if !transparent {
        pixmap.fill(Color::WHITE);
    }
    resvg::render(tree, Transform::from_scale(scale, scale), &mut pixmap.as_mut());
    Ok(pixmap)
}

// A drawn picture as width, height and RGBA rows (not premultiplied).
fn rgba_of(pixmap: &resvg::tiny_skia::Pixmap) -> (u32, u32, Vec<u8>) {
    let rgba = pixmap.pixels().iter().flat_map(|p| {
        let c = p.demultiply();
        [c.red(), c.green(), c.blue(), c.alpha()]
    }).collect();
    (pixmap.width(), pixmap.height(), rgba)
}

// The SVG as pixels at `dpi` (of its true size), white or transparent behind.
fn pixels(svg: &str, dpi: f32, transparent: bool) -> Result<(u32, u32, Vec<u8>), String> {
    Ok(rgba_of(&draw(&tree(svg)?, dpi, transparent)?))
}

fn dpi_of(dpi: f32) -> f32 {
    if dpi.is_finite() { dpi.clamp(36.0, 2400.0) } else { 300.0 }
}

// A PNG of the SVG at `dpi` (of its true size), white or transparent behind. It records its resolution, so
// Word, PowerPoint and Keynote place it at true size. With `cdxml`, the drawing goes in it too (png_of).
pub fn make_png(svg: &str, dpi: f32, transparent: bool, cdxml: Option<&str>) -> Result<Vec<u8>, String> {
    let dpi = dpi_of(dpi);
    png_of(&draw(&tree(svg)?, dpi, transparent)?, dpi, cdxml)
}

// The PNG's keyword for the drawing's CDXML, in a compressed iTXt chunk before the pixels, so the picture opens,
// drops and pastes back into Octet as the drawing (cdxml_from_png). Viewers and Office skip the chunk.
const PNG_KEYWORD: &str = "CDXML";

fn png_of(pixmap: &resvg::tiny_skia::Pixmap, dpi: f32, cdxml: Option<&str>) -> Result<Vec<u8>, String> {
    let (w, h, rgba) = rgba_of(pixmap);
    let mut out = Vec::new();
    let mut enc = png::Encoder::new(&mut out, w, h);
    enc.set_color(png::ColorType::Rgba);
    enc.set_depth(png::BitDepth::Eight);
    let ppm = (dpi / 0.0254).round() as u32;
    enc.set_pixel_dims(Some(png::PixelDimensions { xppu: ppm, yppu: ppm, unit: png::Unit::Meter }));
    let mut writer = enc.write_header().map_err(|e| e.to_string())?;
    if let Some(x) = cdxml {
        let mut chunk = png::text_metadata::ITXtChunk::new(PNG_KEYWORD, cdxml_document(x));
        chunk.compressed = true;
        writer.write_text_chunk(&chunk).map_err(|e| e.to_string())?;
    }
    writer.write_image_data(&rgba).map_err(|e| e.to_string())?;
    writer.finish().map_err(|e| e.to_string())?;
    Ok(out)
}

// The picture on the clipboard on Windows and Linux, where Office pastes no PDF: a transparent PNG at `dpi` of true
// size, the export resolution (lower for a large drawing, so it has at most 16 million pixels and 8,192 on a side),
// with `cdxml` in it, and with `bitmap` the same on white as a Windows bitmap (a DIB), for programs that read no PNG.
pub fn clipboard_pictures(svg: &str, bitmap: bool, dpi: f32, cdxml: Option<&str>) -> Result<(Vec<u8>, Option<Vec<u8>>), String> {
    clipboard_pixels(&tree(svg)?, bitmap, dpi, cdxml)
}

pub fn clipboard_pixels(tree: &usvg::Tree, bitmap: bool, dpi: f32, cdxml: Option<&str>) -> Result<(Vec<u8>, Option<Vec<u8>>), String> {
    let (w, h) = (tree.size().width().max(1.0), tree.size().height().max(1.0));
    let dpi = dpi_of(dpi).min(96.0 * (16e6 / (w * h)).sqrt()).min(96.0 * 8192.0 / w.max(h));
    let pixmap = draw(tree, dpi, true)?;
    Ok((png_of(&pixmap, dpi, cdxml)?, bitmap.then(|| dib(&pixmap, dpi))))
}

// A device-independent bitmap as the Windows clipboard holds it (CF_DIB): a BITMAPINFOHEADER, then rows of blue,
// green and red from the bottom up, each padded to 4 bytes. The picture is put on white.
fn dib(pixmap: &resvg::tiny_skia::Pixmap, dpi: f32) -> Vec<u8> {
    let (w, h) = (pixmap.width() as usize, pixmap.height() as usize);
    let row = (w * 3 + 3) & !3;
    let ppm = ((dpi / 0.0254).round() as i32).to_le_bytes();
    let mut out = Vec::with_capacity(40 + row * h);
    out.extend(40u32.to_le_bytes());
    out.extend((w as i32).to_le_bytes());
    out.extend((h as i32).to_le_bytes());
    out.extend(1u16.to_le_bytes()); // planes
    out.extend(24u16.to_le_bytes()); // bits per pixel
    out.extend(0u32.to_le_bytes()); // BI_RGB
    out.extend(((row * h) as u32).to_le_bytes());
    out.extend(ppm);
    out.extend(ppm);
    out.extend([0u8; 8]); // colours used, colours important
    let px = pixmap.pixels();
    for y in (0..h).rev() {
        let start = out.len();
        // Premultiplied colour on white: each channel plus what the alpha leaves.
        for c in &px[y * w..(y + 1) * w] {
            let white = 255 - c.alpha();
            out.extend([c.blue().saturating_add(white), c.green().saturating_add(white), c.red().saturating_add(white)]);
        }
        out.resize(start + row, 0);
    }
    out
}

// A Windows bitmap (BMP) of the SVG at `dpi`, on white: a file header, then the bitmap as the clipboard holds it (dib).
pub fn make_bmp(svg: &str, dpi: f32) -> Result<Vec<u8>, String> {
    let dpi = dpi_of(dpi);
    let dib = dib(&draw(&tree(svg)?, dpi, false)?, dpi);
    let mut out = Vec::with_capacity(14 + dib.len());
    out.extend(b"BM");
    out.extend(((14 + dib.len()) as u32).to_le_bytes());
    out.extend([0u8; 4]); // reserved
    out.extend(54u32.to_le_bytes()); // where the pixels start: after this header and the dib's
    out.extend(dib);
    Ok(out)
}

// A 3MF file (3D Manufacturing Format): a zip of the 3D model the page made (src/model3mf.ts), with the two parts every
// 3MF package has: its content types, and the relationship that points to the model. Each part is deflated.
pub fn make_3mf(model: &str) -> Result<Vec<u8>, String> {
    if model.len() > MAX_SVG {
        return Err("This drawing is too large to export.".into());
    }
    let parts: [(&str, &[u8]); 3] = [
        ("[Content_Types].xml", br#"<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>
"#),
        ("_rels/.rels", br#"<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>
"#),
        ("3D/3dmodel.model", model.as_bytes()),
    ];
    Ok(zip(&parts, 6, usize::MAX))
}

// A zip file of `parts` (each a name and its bytes), each deflated at `level` (1 fastest, 9 smallest), with its CRC-32
// and sizes, then the central directory and the end record. A part larger than `stored_over` bytes goes in as it is
// (stored, method 0), with nothing to wait for. For a 3MF file, which stores no part, and for Office's copy of a
// picture (clipboard.rs). A part is under 4 GB and there are under 65,536 of them: the callers' limits are far below
// both.
pub(crate) fn zip(parts: &[(&str, &[u8])], level: u8, stored_over: usize) -> Vec<u8> {
    let (mut out, mut dir) = (Vec::new(), Vec::new());
    for (name, data) in parts {
        let deflated = (data.len() <= stored_over).then(|| miniz_oxide::deflate::compress_to_vec(data, level));
        let (method, packed): (u16, &[u8]) = match &deflated {
            Some(d) => (8, d),
            None => (0, data),
        };
        // The fields the local header and the central directory share: version 2.0, no flags, the method, 1 January
        // 1980, the CRC-32, both sizes, the name's length and no extra field.
        let mut common = Vec::new();
        for v in [20u16, 0, method, 0, 0x21] {
            common.extend(v.to_le_bytes());
        }
        for v in [crc32(data), packed.len() as u32, data.len() as u32] {
            common.extend(v.to_le_bytes());
        }
        common.extend((name.len() as u16).to_le_bytes());
        common.extend([0u8; 2]);
        dir.extend(0x0201_4b50u32.to_le_bytes());
        dir.extend(20u16.to_le_bytes());
        dir.extend(&common);
        dir.extend([0u8; 10]); // no comment, disk 0, no attributes
        dir.extend((out.len() as u32).to_le_bytes());
        dir.extend(name.as_bytes());
        out.extend(0x0403_4b50u32.to_le_bytes());
        out.extend(&common);
        out.extend(name.as_bytes());
        out.extend(packed);
    }
    let (at, size, count) = (out.len() as u32, dir.len() as u32, parts.len() as u16);
    out.extend(dir);
    out.extend(0x0605_4b50u32.to_le_bytes());
    for v in [0u16, 0, count, count] {
        out.extend(v.to_le_bytes());
    }
    out.extend(size.to_le_bytes());
    out.extend(at.to_le_bytes());
    out.extend([0u8; 2]);
    out
}

// The CRC-32 a zip file keeps for each part (the reflected polynomial 0xEDB88320), from tables, eight bytes a step.
// CRC[0][b] is the CRC of the byte b; CRC[k][b] is that byte's with k zero bytes after it.
static CRC: [[u32; 256]; 8] = {
    let mut t = [[0u32; 256]; 8];
    let mut b = 0;
    while b < 256 {
        let (mut c, mut bit) = (b as u32, 0);
        while bit < 8 {
            c = if c & 1 == 1 { (c >> 1) ^ 0xEDB8_8320 } else { c >> 1 };
            bit += 1;
        }
        t[0][b] = c;
        b += 1;
    }
    let mut k = 1;
    while k < 8 {
        let mut b = 0;
        while b < 256 {
            t[k][b] = (t[k - 1][b] >> 8) ^ t[0][(t[k - 1][b] & 0xff) as usize];
            b += 1;
        }
        k += 1;
    }
    t
};
pub(crate) fn crc32(data: &[u8]) -> u32 {
    let mut c = !0u32;
    let mut eights = data.chunks_exact(8);
    for b in &mut eights {
        let lo = (c ^ u32::from_le_bytes([b[0], b[1], b[2], b[3]])).to_le_bytes();
        c = CRC[7][lo[0] as usize] ^ CRC[6][lo[1] as usize] ^ CRC[5][lo[2] as usize] ^ CRC[4][lo[3] as usize]
            ^ CRC[3][b[4] as usize] ^ CRC[2][b[5] as usize] ^ CRC[1][b[6] as usize] ^ CRC[0][b[7] as usize];
    }
    for &b in eights.remainder() {
        c = (c >> 8) ^ CRC[0][((c ^ u32::from(b)) & 0xff) as usize];
    }
    !c
}

// A JPEG of the SVG at `dpi`, on white (JPEG has no transparency), at `quality` (1 to 100), with its resolution.
pub fn make_jpeg(svg: &str, dpi: f32, quality: u8) -> Result<Vec<u8>, String> {
    use image::codecs::jpeg::{JpegEncoder, PixelDensity};
    let dpi = dpi_of(dpi);
    let (w, h, rgba) = pixels(svg, dpi, false)?;
    let rgb: Vec<u8> = rgba.chunks_exact(4).flat_map(|p| [p[0], p[1], p[2]]).collect();
    let mut out = Vec::new();
    let mut enc = JpegEncoder::new_with_quality(&mut out, quality.clamp(1, 100));
    enc.set_pixel_density(PixelDensity::dpi(dpi.round() as u16));
    enc.encode(&rgb, w, h, image::ExtendedColorType::Rgb8).map_err(|e| e.to_string())?;
    Ok(out)
}

// A GIF of the SVG at `dpi`, white or transparent behind: 256 colours at most, chosen for the picture. GIF records no
// resolution.
pub fn make_gif(svg: &str, dpi: f32, transparent: bool) -> Result<Vec<u8>, String> {
    let (w, h, mut rgba) = pixels(svg, dpi_of(dpi), transparent)?;
    if w > u32::from(u16::MAX) || h > u32::from(u16::MAX) {
        return Err("This picture is too large for a GIF. Choose a lower resolution.".into());
    }
    // GIF transparency is on or off: a pixel under half covered is clear, the rest are solid.
    for p in rgba.chunks_exact_mut(4) {
        p[3] = if p[3] < 128 { 0 } else { 255 };
    }
    let mut out = Vec::new();
    let mut enc = image::codecs::gif::GifEncoder::new_with_speed(&mut out, 10);
    enc.encode(&rgba, w, h, image::ExtendedColorType::Rgba8).map_err(|e| e.to_string())?;
    drop(enc);
    Ok(out)
}

// A TIFF of the SVG at `dpi`, white or transparent behind: baseline RGB (RGBA with transparency), 8 bits a sample,
// PackBits compression, its resolution in pixels per inch. Little-endian, a strip every 16 rows.
pub fn make_tiff(svg: &str, dpi: f32, transparent: bool) -> Result<Vec<u8>, String> {
    let dpi = dpi_of(dpi);
    let (w, h, rgba) = pixels(svg, dpi, transparent)?;
    let spp: u32 = if transparent { 4 } else { 3 };
    let rows = 16u32;
    let mut out = vec![b'I', b'I', 42, 0, 0, 0, 0, 0];
    let (mut offsets, mut counts) = (Vec::new(), Vec::new());
    for strip in rgba.chunks((w * 4 * rows) as usize) {
        offsets.push(out.len() as u32);
        let start = out.len();
        for row in strip.chunks_exact((w * 4) as usize) {
            let line: Vec<u8> = row.chunks_exact(4).flat_map(|p| p[..spp as usize].to_vec()).collect();
            packbits(&line, &mut out);
        }
        counts.push((out.len() - start) as u32);
        if out.len() % 2 == 1 {
            out.push(0);
        }
    }
    // The arrays the directory points to: bits per sample, strip offsets and byte counts, the two resolutions.
    let at = |data: &[u8], out: &mut Vec<u8>| -> u32 {
        let o = out.len() as u32;
        out.extend_from_slice(data);
        if out.len() % 2 == 1 {
            out.push(0);
        }
        o
    };
    let le = |v: &[u32]| v.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>();
    let bits = at(&vec![8u8, 0].repeat(spp as usize), &mut out);
    let offs = at(&le(&offsets), &mut out);
    let lens = at(&le(&counts), &mut out);
    let res = at(&le(&[(dpi * 100.0).round() as u32, 100]), &mut out);
    let n = offsets.len() as u32;
    // Tags in order: (tag, type, count, value or offset). Types: 3 SHORT, 4 LONG, 5 RATIONAL.
    let mut tags: Vec<(u16, u16, u32, u32)> = vec![
        (256, 4, 1, w), (257, 4, 1, h), (258, 3, spp, bits), (259, 3, 1, 32773), (262, 3, 1, 2),
        (273, 4, n, if n == 1 { offsets[0] } else { offs }), (277, 3, 1, spp), (278, 4, 1, rows),
        (279, 4, n, if n == 1 { counts[0] } else { lens }), (282, 5, 1, res), (283, 5, 1, res), (284, 3, 1, 1), (296, 3, 1, 2),
    ];
    if transparent {
        tags.push((338, 3, 1, 2)); // ExtraSamples: unassociated alpha
    }
    let dir = out.len() as u32;
    out[4..8].copy_from_slice(&dir.to_le_bytes());
    out.extend_from_slice(&(tags.len() as u16).to_le_bytes());
    for (tag, kind, count, value) in tags {
        out.extend_from_slice(&tag.to_le_bytes());
        out.extend_from_slice(&kind.to_le_bytes());
        out.extend_from_slice(&count.to_le_bytes());
        // A single SHORT sits in the first two bytes of the value.
        out.extend_from_slice(&value.to_le_bytes());
    }
    out.extend_from_slice(&0u32.to_le_bytes());
    Ok(out)
}
// PackBits (TIFF compression 32773): runs of 2 to 128 equal bytes as (1 - n, byte), the rest as (n - 1, n bytes).
fn packbits(line: &[u8], out: &mut Vec<u8>) {
    let mut i = 0;
    while i < line.len() {
        let mut run = 1;
        while i + run < line.len() && run < 128 && line[i + run] == line[i] {
            run += 1;
        }
        if run >= 2 {
            out.push((1 - run as i32) as i8 as u8);
            out.push(line[i]);
            i += run;
            continue;
        }
        let start = i;
        while i < line.len() && i - start < 128 && !(i + 1 < line.len() && line[i + 1] == line[i]) {
            i += 1;
        }
        if i == start {
            i += 1;
        }
        out.push((i - start - 1) as u8);
        out.extend_from_slice(&line[start..i]);
    }
}

// What File > Export… can write: id, name in the Save dialog, extensions (the first is the default). The MDL formats
// are V3000, and V2000 apart, with ChemDraw's names. The pictures are ChemDraw's Save As pictures. A template set saved
// as a ChemDraw template file (src/ctp.ts) is a template document (CTP) or stationery (CTS), with ChemDraw's names: the
// same CDX file. CML and ChemDraw's connection table (CT) are for File > More Formats (Settings > Pro), with ChemDraw's names.
const FORMATS: [(&str, &str, &[&str]); 30] = [
    ("oct", "Octet drawing", &["oct"]),
    ("pdf", "PDF", &["pdf"]),
    ("svg", "SVG", &["svg"]),
    ("png", "PNG", &["png"]),
    ("emf", "Windows Enhanced Metafile (EMF)", &["emf"]),
    ("eps", "Encapsulated PostScript (EPS)", &["eps"]),
    ("tif", "TIFF", &["tif", "tiff"]),
    ("jpg", "JPEG", &["jpg", "jpeg"]),
    ("gif", "GIF", &["gif"]),
    ("cdxml", "ChemDraw XML (CDXML)", &["cdxml"]),
    ("cdx", "ChemDraw (CDX)", &["cdx"]),
    ("mol", "MDL Molfile", &["mol"]),
    ("mol2000", "MDL Molfile V2000", &["mol"]),
    ("sdf", "MDL SDfile", &["sdf", "sd"]),
    ("sdf2000", "MDL SDfile V2000", &["sdf", "sd"]),
    ("rxn", "Reaction Molfile (RXN)", &["rxn"]),
    ("rxn2000", "Reaction Molfile V2000 (RXN)", &["rxn"]),
    ("rdf", "MDL RDfile", &["rdf", "rd"]),
    ("rdf2000", "MDL RDfile V2000", &["rdf", "rd"]),
    ("smi", "SMILES", &["smi", "smiles"]),
    ("inchi", "InChI", &["inchi", "txt"]),
    ("tex", "LaTeX (chemfig)", &["tex"]),
    ("ctp", "ChemDraw Template (CTP)", &["ctp"]),
    ("cts", "ChemDraw Template Style Sheet (CTS)", &["cts"]),
    ("cds", "ChemDraw Style Sheet (CDS)", &["cds"]),
    ("csv", "CSV", &["csv"]),
    ("bmp", "Windows Bitmap (BMP)", &["bmp"]),
    ("3mf", "3D Manufacturing Format for Printing (3MF)", &["3mf"]),
    ("cml", "Chemical Markup Language (CML)", &["cml"]),
    ("ct", "Connection Table (CT)", &["ct"]),
];

#[derive(serde::Deserialize)]
pub struct Export {
    name: String,
    format: Option<String>,
    oct: Option<String>,
    svg: Option<String>,
    cdxml: Option<String>,
    cdx: Option<String>, // base64
    ctp: Option<String>, // a template set's ChemDraw template file, base64
    cds: Option<String>, // the document's settings as a ChemDraw style sheet (a CDX file with no drawing), base64
    mdl: Option<String>, // the text of the MDL format asked for, or of CML or CT
    smiles: Option<String>,
    inchi: Option<String>,
    tex: Option<String>, // chemfig code (File > More Formats)
    csv: Option<String>, // Home's Experiments list
    model: Option<String>, // a 3MF file's 3D model (src/model3mf.ts)
    dpi: Option<f32>,
    transparent: Option<bool>,
    quality: Option<u8>, // JPEG
    info: Option<Info>, // the PDF's
    pages: Option<Vec<String>>, // a PDF's pages, each an SVG, in place of svg (an experiment page and its risk assessment)
}

// Files exported this session. The page can ask to show one of them in the file manager (reveal_file), never
// another file.
#[derive(Default)]
pub struct Exported(pub Mutex<HashSet<PathBuf>>);

// File > Export…: asks where to save, then writes the format the file name's extension asks for. The page sends
// the drawing in every form it has; the Save dialog offers those (or only `format`, if given). The page never
// names a path, so Octet writes only where the user chose. Returns the path, or None if cancelled.
#[tauri::command]
pub async fn export_file(app: AppHandle, exported: State<'_, Exported>, export: Export) -> Result<Option<String>, String> {
    let e = export;
    let has = |id: &str| match id {
        "oct" => e.oct.is_some(),
        "pdf" => e.svg.is_some() || e.pages.is_some(),
        "svg" | "png" | "emf" | "eps" | "tif" | "jpg" | "gif" | "bmp" => e.svg.is_some(),
        "cdxml" => e.cdxml.is_some(),
        "cdx" => e.cdx.is_some(),
        "inchi" => e.inchi.is_some(),
        "smi" => e.smiles.is_some(),
        "tex" => e.tex.is_some(),
        "ctp" | "cts" => e.ctp.is_some(),
        "cds" => e.cds.is_some(),
        "csv" => e.csv.is_some(),
        "3mf" => e.model.is_some(),
        _ => e.mdl.is_some(),
    };
    let offered: Vec<_> = FORMATS.iter().filter(|f| has(f.0) && e.format.as_deref().is_none_or(|x| x == f.0)).collect();
    let Some(first) = offered.first() else {
        return Err("There is nothing to export in this format.".into());
    };
    let stem: String = e.name.trim_end_matches(".octet").chars().filter(|c| !c.is_control() && !matches!(c, '/' | '\\' | ':')).take(100).collect();
    let stem = if stem.trim().is_empty() { "Untitled".into() } else { stem };
    let mut dialog = app.dialog().file().set_file_name(format!("{stem}.{}", first.2[0]));
    for f in &offered {
        dialog = dialog.add_filter(f.1, f.2);
    }
    let Some(file) = dialog.blocking_save_file() else {
        return Ok(None);
    };
    let mut path: PathBuf = file.into_path().map_err(|e| e.to_string())?;
    let ext = path.extension().and_then(|x| x.to_str()).map(str::to_ascii_lowercase);
    let format = match offered.iter().find(|f| ext.as_deref().is_some_and(|x| f.2.contains(&x))) {
        Some(f) => f.0,
        None => {
            path.as_mut_os_string().push(format!(".{}", first.2[0]));
            first.0
        }
    };
    let text = |s: &Option<String>| s.clone().unwrap_or_default().into_bytes();
    let bytes = match format {
        "pdf" => match &e.pages {
            Some(pages) => make_pdf_pages(pages, e.cdxml.as_deref(), e.info.as_ref())?,
            None => make_pdf(e.svg.as_deref().unwrap_or_default(), e.cdxml.as_deref(), e.info.as_ref())?,
        },
        "svg" => format!("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{}\n", e.svg.as_deref().unwrap_or_default()).into_bytes(),
        "png" => make_png(e.svg.as_deref().unwrap_or_default(), e.dpi.unwrap_or(300.0), e.transparent.unwrap_or(false), e.cdxml.as_deref())?,
        "tif" => make_tiff(e.svg.as_deref().unwrap_or_default(), e.dpi.unwrap_or(300.0), e.transparent.unwrap_or(false))?,
        "jpg" => make_jpeg(e.svg.as_deref().unwrap_or_default(), e.dpi.unwrap_or(300.0), e.quality.unwrap_or(95))?,
        "gif" => make_gif(e.svg.as_deref().unwrap_or_default(), e.dpi.unwrap_or(300.0), e.transparent.unwrap_or(false))?,
        "bmp" => make_bmp(e.svg.as_deref().unwrap_or_default(), e.dpi.unwrap_or(300.0))?,
        "3mf" => make_3mf(e.model.as_deref().unwrap_or_default())?,
        "emf" => crate::vector::make_emf(&tree(e.svg.as_deref().unwrap_or_default())?, e.cdxml.as_deref(), None),
        "eps" => crate::vector::make_eps(&tree(e.svg.as_deref().unwrap_or_default())?),
        "oct" => text(&e.oct),
        "cdxml" => text(&e.cdxml),
        "cdx" => base64::engine::general_purpose::STANDARD.decode(e.cdx.as_deref().unwrap_or_default()).map_err(|_| "Octet cannot write this drawing as CDX.".to_string())?,
        "ctp" | "cts" => base64::engine::general_purpose::STANDARD.decode(e.ctp.as_deref().unwrap_or_default()).map_err(|_| "Octet cannot write this template file.".to_string())?,
        "cds" => base64::engine::general_purpose::STANDARD.decode(e.cds.as_deref().unwrap_or_default()).map_err(|_| "Octet cannot write this style sheet.".to_string())?,
        "inchi" => format!("{}\n", e.inchi.as_deref().unwrap_or_default().trim()).into_bytes(),
        "smi" => format!("{}\n", e.smiles.as_deref().unwrap_or_default().trim()).into_bytes(),
        "tex" => format!("{}\n", e.tex.as_deref().unwrap_or_default().trim()).into_bytes(),
        "csv" => text(&e.csv),
        _ => text(&e.mdl),
    };
    crate::write_atomic(&path, &bytes).map_err(|e| e.to_string())?;
    // Export over the open drawing's own file is Octet's write: Save does not ask about another app (issue 2).
    crate::stamp(&app, &path);
    exported.0.lock().unwrap().insert(path.clone());
    Ok(Some(path.to_string_lossy().into_owned()))
}

// ---- Reading CDXML back out of a PDF: Octet's, ChemDraw's, or either after Word ----
// The PDF is hostile: every index is checked, nothing recurses, a dictionary is read from at most 16 KB,
// at most 10,000 objects are looked at, and inflating stops at 32 MB. The searches for a stream's end and for an
// indirect /Length read at most four times the PDF's size in all, and the check for "endstream" where /Length says
// reads 256 bytes (REL-25): before, a crafted 63 MB PDF with thousands of streams kept a core busy for minutes.

// The drawing's CDXML in a PDF: the catalog's /Metadata, then any /Type /Metadata /Subtype /XML stream, then
// Octet's first test form (base64 CDXML in the document info /Keywords). Clipboard spec 4.3 and 4.4.
pub fn cdxml_from_pdf(pdf: &[u8]) -> Option<String> {
    if pdf.len() > MAX_PDF || !pdf.starts_with(b"%PDF") {
        return None;
    }
    let catalog = rfind(pdf, b"/Root").and_then(|i| reference(pdf, i + 5)).and_then(|(n, _)| object(pdf, n));
    let meta = catalog.and_then(|at| dict(pdf, at)).and_then(|(d, _)| match get(&d, b"Metadata") {
        Some(Val::Ref(n)) => object(pdf, *n),
        _ => None,
    });
    let budget = Cell::new(pdf.len().saturating_mul(4));
    if let Some(s) = meta.and_then(|at| xml_stream(pdf, at, false, &budget)) {
        return Some(s);
    }
    let headers = (0..pdf.len().saturating_sub(2)).filter(|&i| &pdf[i..i + 3] == b"obj" && obj_header(pdf, i));
    if let Some(s) = headers.take(10_000).find_map(|i| xml_stream(pdf, i + 3, true, &budget)) {
        return Some(s);
    }
    let i = find(pdf, b"octet-cdxml-base64:")? + 19;
    let end = pdf[i..].iter().position(|c| !(c.is_ascii_alphanumeric() || b"+/=".contains(c))).map_or(pdf.len(), |k| i + k);
    let raw = base64::engine::general_purpose::STANDARD.decode(&pdf[i..end]).ok()?;
    is_cdxml(&raw).then(|| String::from_utf8_lossy(&raw).into_owned())
}

// CDXML starts with the XML declaration (after an optional byte order mark) and names CDXML near the top.
// Laxer than ChemDraw (which wants the DOCTYPE in the first 256 bytes); the CDXML is read as hostile anyway.
fn is_cdxml(head: &[u8]) -> bool {
    let head = &head[..head.len().min(1024)];
    let s = head.strip_prefix(b"\xEF\xBB\xBF").unwrap_or(head);
    let s = &s[s.iter().position(|c| !c.is_ascii_whitespace()).unwrap_or(s.len())..];
    s.starts_with(b"<?xml") && (find(s, b"<!DOCTYPE CDXML").is_some() || find(s, b"<CDXML").is_some())
}

// The stream of the object whose dictionary starts at `at`, decoded, if it is CDXML. With `marked`, only a
// stream whose dictionary says /Type /Metadata (or /MetaData) and /Subtype /XML. `budget`: the bytes that the
// searches here may still read; each search takes what it reads from it.
fn xml_stream(pdf: &[u8], at: usize, marked: bool, budget: &Cell<usize>) -> Option<String> {
    let (d, end) = dict(pdf, at)?;
    let name = |k: &[u8]| match get(&d, k) {
        Some(Val::Name(n)) => Some(*n),
        _ => None,
    };
    if marked && !(matches!(name(b"Type"), Some(b"Metadata" | b"MetaData")) && name(b"Subtype") == Some(b"XML")) {
        return None;
    }
    let flate = match get(&d, b"Filter") {
        None => false,
        Some(Val::Name(b"FlateDecode")) => true,
        Some(Val::Array(a)) if names(a) == [b"FlateDecode".as_slice()] => true,
        Some(Val::Array(a)) if names(a).is_empty() => false,
        _ => return None,
    };
    // The data starts after "stream" and its line end. /Length says where it ends, if it agrees with the
    // "endstream" there; otherwise the first "endstream" does. The keywords are looked for in the 256 bytes after
    // where they should be, as every /Length can point at one long run.
    let near = |e: usize| &pdf[..pdf.len().min(e.saturating_add(256))];
    let mut i = skip_white(near(end), end);
    if word(near(i), i) != b"stream" {
        return None;
    }
    i += 6;
    i += usize::from(pdf.get(i) == Some(&b'\r'));
    i += usize::from(pdf.get(i) == Some(&b'\n'));
    let spend = |n: usize| budget.get().checked_sub(n).map(|left| budget.set(left)).is_some();
    let length = match get(&d, b"Length") {
        Some(Val::Int(n)) => Some(*n),
        // object() reads the whole PDF.
        Some(Val::Ref(r)) if spend(pdf.len()) => object(pdf, *r).and_then(|j| int(pdf, skip_white(pdf, j))).map(|(n, _)| n),
        _ => None,
    };
    let stated = length.and_then(|n| i.checked_add(usize::try_from(n).ok()?)).filter(|&e| e <= pdf.len() && word(near(e), skip_white(near(e), e)) == b"endstream");
    let end = stated.or_else(|| {
        let rest = pdf.get(i..)?;
        let window = &rest[..rest.len().min(budget.get())];
        let found = find(window, b"endstream");
        spend(found.map_or(window.len(), |k| k + 9));
        let mut e = i + found?;
        e -= usize::from(e > i && pdf[e - 1] == b'\n');
        e -= usize::from(e > i && pdf[e - 1] == b'\r');
        Some(e)
    })?;
    cdxml_of(&pdf[i..end], flate)
}

// `data` as CDXML, inflated (zlib) first when `flate`: None if it is not CDXML or comes to more than 32 MB. Zlib data
// with no filter is inflated too: LibreOffice keeps a PDF newer than 1.6 (Octet's, ChemDraw's) as pdfium saves it at
// 1.6, which takes the /Filter off the /Metadata stream and leaves the stream deflated.
fn cdxml_of(data: &[u8], flate: bool) -> Option<String> {
    let zlib = data.len() > 2 && data[0] == 0x78 && (u16::from(data[0]) << 8 | u16::from(data[1])) % 31 == 0;
    if !flate && !zlib {
        return (data.len() <= MAX_XML && is_cdxml(data)).then(|| String::from_utf8_lossy(data).into_owned());
    }
    use miniz_oxide::inflate::{decompress_to_vec_zlib_with_limit as inflate, TINFLStatus};
    // Look at the start first, so a large stream that is not CDXML is never inflated in full.
    let head = match inflate(data, 1024) {
        Ok(v) => v,
        Err(e) if e.status == TINFLStatus::HasMoreOutput => e.output,
        Err(_) => return None,
    };
    if !is_cdxml(&head) {
        return None;
    }
    inflate(data, MAX_XML).ok().map(|v| String::from_utf8_lossy(&v).into_owned())
}

// The CDXML in a PNG's iTXt chunk named CDXML (png_of), if it has one. The chunks are walked with bounds checks.
pub fn cdxml_from_png(png: &[u8]) -> Option<String> {
    if png.len() > MAX_PDF || !png.starts_with(b"\x89PNG\r\n\x1a\n") {
        return None;
    }
    let mut at = 8;
    while let Some(head) = png.get(at..at + 8) {
        let n = u32::from_be_bytes([head[0], head[1], head[2], head[3]]) as usize;
        let data = png.get(at + 8..(at + 8).checked_add(n)?)?;
        match &head[4..] {
            b"IEND" => return None,
            // Keyword, NUL, compression flag and method, language tag, NUL, translated keyword, NUL, text.
            b"iTXt" if data.starts_with(PNG_KEYWORD.as_bytes()) && data.get(PNG_KEYWORD.len()) == Some(&0) => {
                let rest = &data[PNG_KEYWORD.len() + 1..];
                let (flag, method) = (*rest.first()?, *rest.get(1)?);
                let mut text = rest.get(2..)?;
                for _ in 0..2 {
                    text = &text[text.iter().position(|&c| c == 0)? + 1..];
                }
                return if flag > 1 || method != 0 { None } else { cdxml_of(text, flag == 1) };
            }
            _ => {}
        }
        at += n + 12; // length, type, data and CRC
    }
    None
}

// The drawing in a picture file or a picture from the clipboard: the CDXML in a PDF (Octet's or ChemDraw's), in an
// EMF's comment or in a PNG's chunk (Octet's). None for any other picture.
pub fn cdxml_from_picture(b: &[u8]) -> Option<String> {
    if b.starts_with(b"%PDF") {
        cdxml_from_pdf(b)
    } else if b.starts_with(b"\x89PNG") {
        cdxml_from_png(b)
    } else if b.get(40..44) == Some(b" EMF") {
        crate::vector::cdxml_from_emf(b)
    } else {
        None
    }
}

fn find(h: &[u8], n: &[u8]) -> Option<usize> {
    h.windows(n.len()).position(|w| w == n)
}

fn rfind(h: &[u8], n: &[u8]) -> Option<usize> {
    h.windows(n.len()).rposition(|w| w == n)
}

fn is_white(c: u8) -> bool {
    matches!(c, b' ' | b'\t' | b'\r' | b'\n' | b'\x0c' | 0)
}

fn is_delim(c: u8) -> bool {
    matches!(c, b'(' | b')' | b'<' | b'>' | b'[' | b']' | b'{' | b'}' | b'/' | b'%')
}

// Past whitespace and comments.
fn skip_white(b: &[u8], mut i: usize) -> usize {
    while let Some(&c) = b.get(i) {
        if is_white(c) {
            i += 1;
        } else if c == b'%' {
            while b.get(i).is_some_and(|&c| c != b'\n' && c != b'\r') {
                i += 1;
            }
        } else {
            break;
        }
    }
    i
}

// The regular characters from `i` up to whitespace or a delimiter.
fn word(b: &[u8], i: usize) -> &[u8] {
    let Some(rest) = b.get(i..) else { return &[] };
    &rest[..rest.iter().position(|&c| is_white(c) || is_delim(c)).unwrap_or(rest.len())]
}

fn int(b: &[u8], i: usize) -> Option<(u64, usize)> {
    let w = word(b, i);
    if w.is_empty() || w.len() > 12 || !w.iter().all(u8::is_ascii_digit) {
        return None;
    }
    Some((std::str::from_utf8(w).ok()?.parse().ok()?, i + w.len()))
}

// "N G R" at `i`: the object number, and where the reference ends.
fn reference(b: &[u8], i: usize) -> Option<(u32, usize)> {
    let (n, j) = int(b, skip_white(b, i))?;
    let (_, j) = int(b, skip_white(b, j))?;
    let j = skip_white(b, j);
    if word(b, j) != b"R" {
        return None;
    }
    Some((u32::try_from(n).ok()?, j + 1))
}

// Whether the "obj" at `i` follows "N G " (and so is not "endobj").
fn obj_header(b: &[u8], i: usize) -> bool {
    let back_white = |mut j: usize| {
        while j > 0 && is_white(b[j - 1]) {
            j -= 1;
        }
        j
    };
    let back_digits = |mut j: usize| {
        while j > 0 && b[j - 1].is_ascii_digit() {
            j -= 1;
        }
        j
    };
    let after = b.get(i + 3).is_none_or(|&c| is_white(c) || is_delim(c));
    let j = back_white(i);
    let k = back_digits(j);
    let l = back_white(k);
    let m = back_digits(l);
    after && j < i && k < j && l < k && m < l && (m == 0 || is_white(b[m - 1]))
}

// Where object `n`'s body starts (after "n g obj"). The last definition wins, as in an updated PDF.
fn object(b: &[u8], n: u32) -> Option<usize> {
    let pat = format!("{n} ");
    let pat = pat.as_bytes();
    let mut found = None;
    let mut from = 0;
    while let Some(k) = b.get(from..).and_then(|rest| find(rest, pat)) {
        let i = from + k;
        from = i + 1;
        if i == 0 || !is_white(b[i - 1]) {
            continue;
        }
        if let Some((_, j)) = int(b, skip_white(b, i + pat.len())) {
            let j = skip_white(b, j);
            if word(b, j) == b"obj" {
                found = Some(j + 3);
            }
        }
    }
    found
}

enum Val<'a> {
    Name(&'a [u8]),
    Int(u64),
    Ref(u32),
    Array(&'a [u8]),
    Other,
}

fn get<'a, 'b>(d: &'b [(&'a [u8], Val<'a>)], key: &[u8]) -> Option<&'b Val<'a>> {
    d.iter().find(|(k, _)| *k == key).map(|(_, v)| v)
}

// The names in an array's bytes, such as [/FlateDecode].
fn names(a: &[u8]) -> Vec<&[u8]> {
    a.split(|&c| c == b'/').skip(1).map(|s| word(s, 0)).collect()
}

// The dictionary starting at `at` (after whitespace): its entries, and where it ends.
fn dict(b: &[u8], at: usize) -> Option<(Vec<(&[u8], Val<'_>)>, usize)> {
    let b = &b[..b.len().min(at.saturating_add(16 << 10))];
    let mut i = skip_white(b, at);
    if b.get(i..i + 2)? != b"<<" {
        return None;
    }
    i += 2;
    let mut out = Vec::new();
    loop {
        i = skip_white(b, i);
        if b.get(i..i + 2)? == b">>" {
            return Some((out, i + 2));
        }
        if *b.get(i)? != b'/' {
            return None;
        }
        let key = word(b, i + 1);
        i = skip_white(b, i + 1 + key.len());
        let (val, next) = value(b, i)?;
        out.push((key, val));
        i = next;
    }
}

fn value(b: &[u8], i: usize) -> Option<(Val<'_>, usize)> {
    match *b.get(i)? {
        b'/' => {
            let w = word(b, i + 1);
            Some((Val::Name(w), i + 1 + w.len()))
        }
        b'<' if b.get(i + 1) == Some(&b'<') => Some((Val::Other, skip_nested(b, i)?)),
        b'[' => {
            let end = skip_nested(b, i)?;
            Some((Val::Array(&b[i + 1..end - 1]), end))
        }
        b'<' => Some((Val::Other, i + 1 + b.get(i + 1..)?.iter().position(|&c| c == b'>')? + 1)),
        b'(' => Some((Val::Other, skip_string(b, i)?)),
        c if c.is_ascii_digit() => {
            if let Some((r, end)) = reference(b, i) {
                return Some((Val::Ref(r), end));
            }
            if let Some((n, end)) = int(b, i) {
                return Some((Val::Int(n), end));
            }
            Some((Val::Other, i + word(b, i).len().max(1)))
        }
        _ => {
            let w = word(b, i);
            (!w.is_empty()).then_some((Val::Other, i + w.len()))
        }
    }
}

// Past a literal string "( ... )", with nested brackets and backslash escapes.
fn skip_string(b: &[u8], mut i: usize) -> Option<usize> {
    let mut depth = 0usize;
    loop {
        match *b.get(i)? {
            b'\\' => i += 1,
            b'(' => depth += 1,
            b')' => {
                depth -= 1;
                if depth == 0 {
                    return Some(i + 1);
                }
            }
            _ => {}
        }
        i += 1;
    }
}

// Past a nested dictionary "<< ... >>" or array "[ ... ]", counting depth instead of recursing.
fn skip_nested(b: &[u8], mut i: usize) -> Option<usize> {
    let mut depth = 0usize;
    loop {
        match *b.get(i)? {
            b'(' => i = skip_string(b, i)?,
            b'<' if b.get(i + 1) == Some(&b'<') => {
                depth += 1;
                i += 2;
            }
            b'<' => i += 1 + b.get(i + 1..)?.iter().position(|&c| c == b'>')? + 1,
            b'>' if b.get(i + 1) == Some(&b'>') => {
                depth = depth.checked_sub(1)?;
                i += 2;
                if depth == 0 {
                    return Some(i);
                }
            }
            b'[' => {
                depth += 1;
                i += 1;
            }
            b']' => {
                depth = depth.checked_sub(1)?;
                i += 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            b'%' => i = skip_white(b, i),
            _ => i += 1,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SVG: &str = r##"<svg xmlns="http://www.w3.org/2000/svg" width="86pt" height="65pt" viewBox="0 0 86 65">
        <path d="M10 10L60 10L60 12L10 12Z" fill="rgb(15, 23, 42)"/>
        <text x="20" y="40" font-family="Arial, Helvetica, sans-serif" font-size="10" fill="rgb(15, 23, 42)">NH<tspan baseline-shift="sub" font-size="7.5">2</tspan></text>
    </svg>"##;
    const CDXML: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<!DOCTYPE CDXML SYSTEM \"http://www.cambridgesoft.com/xml/cdxml.dtd\" >\n<CDXML><page><fragment/></page></CDXML>\n";

    #[test]
    fn pdf_carries_cdxml_and_reads_back() {
        let pdf = make_pdf(SVG, Some(CDXML), None).unwrap();
        assert_eq!(cdxml_from_pdf(&pdf).as_deref(), Some(CDXML));
        // As LibreOffice keeps it: pdfium's copy at PDF 1.6 has the /Metadata stream deflated with no /Filter.
        let meta = find(&pdf, b"/Type /Metadata").unwrap();
        let at = meta + find(&pdf[meta..], b"/Filter /FlateDecode").unwrap();
        let unfiltered = [&pdf[..at], &[b' '; 20][..], &pdf[at + 20..]].concat();
        assert_eq!(cdxml_from_pdf(&unfiltered).as_deref(), Some(CDXML));
        // The catalog points at the stream, which is marked as ChemDraw marks its own.
        let text = String::from_utf8_lossy(&pdf);
        assert!(text.contains("/Type /Catalog"));
        assert!(find(&pdf, b"/Metadata").is_some() && find(&pdf, b"/Subtype /XML").is_some() && find(&pdf, b"/Vendor /org.octet").is_some());
        // True size: 86 x 65 pt.
        assert!(text.contains("/MediaBox [0 0 86 65]"), "{}", &text[..text.len().min(2000)]);
        // Labels are text in an embedded font subset.
        assert!(text.contains("/FontFile2"));
        #[cfg(target_os = "macos")]
        assert!(text.contains("+ArialMT"));
    }

    // PackBits read back (TIFF 6.0, section 9).
    fn unpack(data: &[u8]) -> Vec<u8> {
        let (mut out, mut i) = (Vec::new(), 0);
        while i < data.len() {
            let n = data[i] as i8;
            i += 1;
            if n >= 0 {
                out.extend_from_slice(&data[i..i + n as usize + 1]);
                i += n as usize + 1;
            } else if n != -128 {
                out.extend(std::iter::repeat_n(data[i], (1 - n as i32) as usize));
                i += 1;
            }
        }
        out
    }

    #[test]
    fn packbits_reads_back() {
        for line in [vec![], vec![7], vec![1, 2, 3], vec![9; 300], [vec![1, 2], vec![5; 3], vec![6, 7, 8], vec![0; 129]].concat(), (0..=255).collect::<Vec<u8>>()] {
            let mut out = Vec::new();
            packbits(&line, &mut out);
            assert_eq!(unpack(&out), line);
        }
    }

    #[test]
    fn rasters_have_their_size_and_resolution() {
        // 86 x 65 pt at 144 dpi: 172 x 130 px.
        let jpeg = make_jpeg(SVG, 144.0, 95).unwrap();
        let img = image::load_from_memory(&jpeg).unwrap();
        assert_eq!((img.width(), img.height()), (172, 130));
        let gif = make_gif(SVG, 144.0, true).unwrap();
        assert!(gif.starts_with(b"GIF89a"));
        assert_eq!(image::load_from_memory(&gif).unwrap().width(), 172);
        let tiff = make_tiff(SVG, 144.0, true).unwrap();
        assert!(tiff.starts_with(b"II*\0"));
        let u16_at = |at: usize| u16::from_le_bytes([tiff[at], tiff[at + 1]]);
        let u32_at = |at: usize| u32::from_le_bytes(tiff[at..at + 4].try_into().unwrap());
        let dir = u32_at(4) as usize;
        let tags: Vec<(u16, u32, u32)> = (0..u16_at(dir) as usize).map(|k| (u16_at(dir + 2 + 12 * k), u32_at(dir + 6 + 12 * k), u32_at(dir + 10 + 12 * k))).collect();
        let tag = |t: u16| tags.iter().find(|x| x.0 == t).copied().unwrap();
        assert_eq!((tag(256).2, tag(257).2), (172, 130));
        assert_eq!(tag(259).2, 32773);
        assert_eq!(tag(338).2, 2);
        let res = tag(282).2 as usize;
        assert_eq!((u32_at(res), u32_at(res + 4)), (14400, 100));
        // The strips unpack to 4 bytes a pixel, 16 rows each but the last.
        let (offs, lens) = (tag(273), tag(279));
        let strips = offs.1 as usize;
        let mut pixels = 0;
        for k in 0..strips {
            let (o, n) = (u32_at(offs.2 as usize + 4 * k) as usize, u32_at(lens.2 as usize + 4 * k) as usize);
            pixels += unpack(&tiff[o..o + n]).len() / 4;
        }
        assert_eq!(pixels, 172 * 130);
        if let Ok(dir) = std::env::var("OCTET_EXPORT_SAMPLES") {
            for (name, bytes) in [("sample.tif", tiff), ("sample.jpg", jpeg), ("sample.gif", gif), ("sample-white.tif", make_tiff(SVG, 144.0, false).unwrap()),
                ("sample.eps", crate::vector::make_eps(&tree(SVG).unwrap())), ("sample.emf", crate::vector::make_emf(&tree(SVG).unwrap(), None, None))] {
                std::fs::write(std::path::Path::new(&dir).join(name), bytes).unwrap();
            }
        }
    }

    #[test]
    fn cdxml_takes_chemdraws_header() {
        let doc = cdxml_document("\u{feff}<?xml version=\"1.0\"?>\n<!DOCTYPE CDXML SYSTEM \"x\">\n<CDXML/>");
        assert!(doc.starts_with("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<!DOCTYPE CDXML SYSTEM \"http://www.cambridgesoft.com/xml/cdxml.dtd\" >\n<CDXML/>"));
        assert_eq!(cdxml_document("<CDXML/>"), doc);
    }

    // An experiment page with its risk assessment exports as a PDF of two pages, each the size of its SVG, and the
    // CDXML still reads back. No pages, or more than MAX_PAGES, are refused.
    #[test]
    fn pdf_of_pages() {
        let pages = [SVG.to_string(), SVG.to_string()];
        let pdf = make_pdf_pages(&pages, Some(CDXML), None).unwrap();
        assert!(find(&pdf, b"/Count 2").is_some());
        assert_eq!(pdf.windows(9).filter(|w| w == b"/MediaBox").count(), 2);
        assert!(cdxml_from_pdf(&pdf).is_some());
        assert!(make_pdf_pages(&[], None, None).is_err());
        assert!(make_pdf_pages(&vec![SVG.to_string(); MAX_PAGES + 1], None, None).is_err());
    }

    #[test]
    fn pdf_without_cdxml_has_no_metadata() {
        let pdf = make_pdf(SVG, None, None).unwrap();
        assert!(find(&pdf, b"/Metadata").is_none());
        assert_eq!(cdxml_from_pdf(&pdf), None);
    }

    // Settings > Document > Properties: the title, author and keywords that are set go in the document information
    // (text past ASCII as UTF-16), and the CDXML still reads back. None set writes no document information.
    #[test]
    fn pdf_has_the_drawings_properties() {
        let info = Info { title: Some("Aspirin (route 2)".into()), author: Some("Zoë Ångström".into()), keywords: None };
        let pdf = make_pdf(SVG, Some(CDXML), Some(&info)).unwrap();
        assert!(find(&pdf, b"/Info").is_some() && find(&pdf, b"/Title (Aspirin (route 2))").is_some());
        let utf16: String = [0xFEFF].into_iter().chain("Zoë Ångström".encode_utf16()).map(|u| format!("{u:04X}")).collect();
        assert!(find(&pdf, format!("/Author <{utf16}>").as_bytes()).is_some());
        assert!(find(&pdf, b"/Keywords").is_none());
        assert_eq!(cdxml_from_pdf(&pdf).as_deref(), Some(CDXML));
        let none = Info { title: None, author: None, keywords: None };
        assert_eq!(make_pdf(SVG, Some(CDXML), Some(&none)).unwrap(), make_pdf(SVG, Some(CDXML), None).unwrap());
        assert!(find(&make_pdf(SVG, None, None).unwrap(), b"/Info").is_none());
    }

    #[test]
    fn finds_marked_stream_without_catalog_entry() {
        // An uncompressed metadata stream that the catalog does not name, with an indirect /Length.
        let body = CDXML.as_bytes();
        let pdf = [
            b"%PDF-1.3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n".as_slice(),
            b"5 0 obj\n<< /Length 6 0 R /Type /Metadata /Subtype /XML >>\nstream\n",
            body,
            format!("\nendstream\nendobj\n6 0 obj\n{}\nendobj\ntrailer\n<< /Size 7 /Root 1 0 R >>\n%%EOF\n", body.len()).as_bytes(),
        ].concat();
        assert_eq!(cdxml_from_pdf(&pdf).as_deref(), Some(CDXML));
    }

    #[test]
    fn hostile_pdfs_are_refused_quietly() {
        for pdf in [
            b"%PDF-1.4\n1 0 obj << /Metadata 1 0 R".as_slice(),
            b"%PDF trailer << /Root 99999999999 0 R >>",
            b"%PDF\n1 0 obj << /Type /Metadata /Subtype /XML /Length 999999 /Filter /FlateDecode >>\nstream\nxx",
            b"%PDF\n1 0 obj << /A << /B << [ ( ) ) ] >> >> /Type",
            b"%PDF\n1 0 obj << /Type /Metadata /Subtype /XML /Filter [/LZWDecode] /Length 3 >>\nstream\nabc\nendstream",
            b"%PDF octet-cdxml-base64:!!!",
        ] {
            assert_eq!(cdxml_from_pdf(pdf), None);
        }
        // A zip bomb that starts like CDXML stops at the 32 MB cap.
        let mut big = CDXML.as_bytes().to_vec();
        big.resize(40 << 20, b' ');
        let bomb = miniz_oxide::deflate::compress_to_vec_zlib(&big, 1);
        let pdf = [b"%PDF\n1 0 obj << /Type /Metadata /Subtype /XML /Filter /FlateDecode >>\nstream\n".as_slice(), &bomb, b"\nendstream"].concat();
        assert_eq!(cdxml_from_pdf(&pdf), None);
    }

    // REL-25: thousands of marked streams that never end, or whose /Length points at an object, then a long tail.
    // Each search used to read to the end of the file, so 10,000 of them took minutes on 63 MB.
    #[test]
    fn crafted_pdfs_end_quickly() {
        for length in ["", "/Length 7 0 R "] {
            let mut pdf = b"%PDF-1.4\n".to_vec();
            for k in 0..10_000 {
                pdf.extend_from_slice(format!("{} 0 obj << /Type /Metadata /Subtype /XML {length}>>\nstream\n", k + 1).as_bytes());
            }
            pdf.resize(8 << 20, b'x');
            let t = std::time::Instant::now();
            assert_eq!(cdxml_from_pdf(&pdf), None);
            assert!(t.elapsed() < std::time::Duration::from_secs(5), "{length:?} took {:?}", t.elapsed());
        }
        // A sound stream after many that are not CDXML is still found.
        let mut pdf = b"%PDF-1.4\n".to_vec();
        for k in 0..100 {
            pdf.extend_from_slice(format!("{} 0 obj << /Type /Metadata /Subtype /XML >>\nstream\n<x/>\nendstream\nendobj\n", k + 1).as_bytes());
        }
        pdf.extend_from_slice(format!("500 0 obj << /Type /Metadata /Subtype /XML /Length 999 >>\nstream\n{CDXML}\nendstream\nendobj\n").as_bytes());
        assert_eq!(cdxml_from_pdf(&pdf).as_deref(), Some(CDXML));
        // Every /Length points at the start of one long run of spaces, of a comment, or of letters, so each check for
        // "endstream" there used to read all of the run.
        for fill in [b" ".as_slice(), b"%x", b"x"] {
            let mut pdf = b"%PDF-1.4\n".to_vec();
            let mut starts = Vec::new();
            for k in 0..10_000 {
                pdf.extend_from_slice(format!("{} 0 obj << /Type /Metadata /Subtype /XML /Length 0000000000 >>\nstream\n", k + 1).as_bytes());
                starts.push(pdf.len());
            }
            let run = pdf.len();
            for &s in &starts {
                let at = s - "0000000000 >>\nstream\n".len();
                pdf[at..at + 10].copy_from_slice(format!("{:010}", run - s).as_bytes());
            }
            pdf.extend_from_slice(fill);
            pdf.resize(8 << 20, *fill.last().unwrap());
            let t = std::time::Instant::now();
            assert_eq!(cdxml_from_pdf(&pdf), None);
            assert!(t.elapsed() < std::time::Duration::from_secs(5), "{fill:?} took {:?}", t.elapsed());
        }
    }

    // A picture in the drawing (dropped, pasted, or from a ChemDraw file) shows in every export: the page writes it as
    // an <image> with its PNG, JPEG or GIF bytes in a data: address.
    #[test]
    fn pictures_show_in_exports() {
        use base64::Engine;
        let mut png_bytes = Vec::new();
        {
            let mut enc = png::Encoder::new(&mut png_bytes, 8, 4);
            enc.set_color(png::ColorType::Rgba);
            enc.set_depth(png::BitDepth::Eight);
            enc.write_header().unwrap().write_image_data(&[255, 0, 0, 255].repeat(32)).unwrap();
        }
        let red = image::DynamicImage::ImageRgb8(image::RgbImage::from_pixel(8, 4, image::Rgb([255, 0, 0])));
        let made = |f: image::ImageFormat| {
            let mut out = std::io::Cursor::new(Vec::new());
            red.write_to(&mut out, f).unwrap();
            out.into_inner()
        };
        for (mime, bytes) in [("png", png_bytes), ("jpeg", made(image::ImageFormat::Jpeg)), ("gif", made(image::ImageFormat::Gif))] {
            let b64 = base64::engine::general_purpose::STANDARD.encode(bytes);
            let svg = format!(r#"<svg xmlns="http://www.w3.org/2000/svg" width="40pt" height="20pt" viewBox="0 0 40 20"><image href="data:image/{mime};base64,{b64}" x="0" y="0" width="40" height="20" preserveAspectRatio="none"/></svg>"#);
            let (w, h, rgba) = pixels(&svg, 72.0, true).unwrap();
            let k = ((h / 2) * w + w / 2) as usize * 4;
            assert!(rgba[k] > 200 && rgba[k + 1] < 60 && rgba[k + 3] > 200, "{mime}: {:?}", &rgba[k..k + 4]);
            assert!(find(&make_pdf(&svg, None, None).unwrap(), b"/Subtype /Image").is_some(), "{mime}");
            // The clipboard's PNG on Windows and Linux, and EMF and EPS (vector.rs, which checks where they go).
            let mut reader = png::Decoder::new(std::io::Cursor::new(clipboard_pictures(&svg, false, 600.0, None).unwrap().0)).read_info().unwrap();
            let mut buf = vec![0; reader.output_buffer_size()];
            let info = reader.next_frame(&mut buf).unwrap();
            let k = ((info.height / 2) * info.width + info.width / 2) as usize * 4;
            assert!(buf[k] > 200 && buf[k + 1] < 60 && buf[k + 3] > 200, "{mime}: {:?}", &buf[k..k + 4]);
            assert!(String::from_utf8(crate::vector::make_eps(&tree(&svg).unwrap())).unwrap().contains(" image\n"), "{mime}");
            assert!(find(&crate::vector::make_emf(&tree(&svg).unwrap(), None, None), &[81, 0, 0, 0]).is_some(), "{mime}");
        }
    }

    #[test]
    fn png_is_true_size_at_the_resolution() {
        let png = make_png(SVG, 300.0, true, None).unwrap();
        let header = png::Decoder::new(std::io::Cursor::new(png)).read_info().unwrap().info().clone();
        // 86 pt at 300 dpi.
        assert_eq!((header.width, header.height), (359, 271));
        assert_eq!(header.pixel_dims.unwrap().xppu, 11811);
    }

    // A width typed in pixels sets the dpi behind it (dpiFor in src/export.ts): the PNG comes out that wide, with no
    // extra pixel from rounding. JPEG takes its quality, the clipboard's PNG the export dpi, and a picture over 100
    // million pixels is refused with a plain message.
    #[test]
    fn typed_size_quality_clipboard_dpi_and_cap() {
        let size = |png: Vec<u8>| {
            let i = png::Decoder::new(std::io::Cursor::new(png)).read_info().unwrap().info().clone();
            (i.width, i.height)
        };
        assert_eq!(size(make_png(SVG, 1000.0 * 72.0 / 86.0, true, None).unwrap()).0, 1000);
        assert_eq!(size(make_png(SVG, 72.0, true, None).unwrap()), (86, 65));
        assert!(make_jpeg(SVG, 300.0, 20).unwrap().len() < make_jpeg(SVG, 300.0, 100).unwrap().len());
        assert_eq!(size(clipboard_pictures(SVG, false, 150.0, None).unwrap().0), (180, 136));
        let big = r#"<svg xmlns="http://www.w3.org/2000/svg" width="400pt" height="400pt" viewBox="0 0 400 400"/>"#;
        assert!(make_png(big, 2400.0, true, None).unwrap_err().contains("too large"));
    }

    // Issue 47: the clipboard's SVG on Linux keeps export's width and height in pt and draws the same picture, but in px
    // user units. Inkscape drops the root's size on paste and reads user units as px, so its content measures the true
    // size in px there (before: 75% of it).
    #[test]
    fn clipboard_svg_is_true_size_in_px_units() {
        let px = px_units(SVG);
        assert!(px.starts_with(r#"<svg xmlns="http://www.w3.org/2000/svg" width="86pt" height="65pt" viewBox="0 0 114.66666666666667 86.66666666666667">"#), "{px}");
        let (a, b) = (tree(SVG).unwrap(), tree(&px).unwrap());
        assert_eq!(a.size(), b.size(), "the same true size");
        let (ia, ib) = (a.root().abs_bounding_box(), b.root().abs_bounding_box());
        for (x, y) in [(ia.left(), ib.left()), (ia.top(), ib.top()), (ia.width(), ib.width()), (ia.height(), ib.height())] {
            assert!((x - y).abs() < 1e-3, "the same picture: {ia:?} {ib:?}");
        }
        // As Inkscape pastes: the root's size and view box gone, the content's user units as px.
        let pasted = |s: &str| {
            let open = s.find('>').unwrap();
            let s = format!("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1000\" height=\"1000\">{}", &s[open + 1..]);
            tree(&s).unwrap().root().abs_bounding_box().width()
        };
        let true_px = 50.0 * 4.0 / 3.0; // the 50 pt bar
        assert!((pasted(&px) - true_px).abs() < 1e-3, "{}", pasted(&px));
        assert!((pasted(SVG) / true_px - 0.75).abs() < 1e-3, "export's own units paste at 75%");
        // The PNG from it has the same pixels across.
        let size = |png: Vec<u8>| png::Decoder::new(std::io::Cursor::new(png)).read_info().unwrap().info().size();
        assert_eq!(size(make_png(&px, 300.0, true, None).unwrap()), size(make_png(SVG, 300.0, true, None).unwrap()));
        // No root view box, or a broken one: unchanged. Cut short anywhere: no panic.
        for s in [r#"<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt"/>"#, r#"<svg viewBox="0 0 0 5"></svg>"#, r#"<svg viewBox="a b c d"></svg>"#, "", "<svg"] {
            assert_eq!(px_units(s), s);
        }
        for k in 0..SVG.len() {
            if SVG.is_char_boundary(k) {
                px_units(&SVG[..k]);
            }
        }
    }

    // A BMP is a file header, then the bitmap on white at the resolution, 24 bits a pixel from the bottom row up.
    #[test]
    fn bmp_is_true_size_on_white() {
        let bmp = make_bmp(SVG, 300.0).unwrap();
        let u32_at = |k: usize| u32::from_le_bytes(bmp[k..k + 4].try_into().unwrap());
        assert_eq!(&bmp[..2], b"BM");
        assert_eq!(u32_at(2) as usize, bmp.len());
        assert_eq!((u32_at(10), u32_at(14), u32_at(18), u32_at(22), u32_at(38)), (54, 40, 359, 271, 11811));
        assert_eq!(&bmp[26..30], &[1, 0, 24, 0]);
        // Row 0 of the file is the bottom row of the picture, which is white.
        assert!(bmp[54..54 + 359 * 3].iter().all(|&c| c == 255));
        assert_eq!(bmp.len(), 54 + 1080 * 271, "each row padded to 4 bytes");
    }

    // The CRC-32 as Octet worked it out before the tables: a bit at a time.
    fn bitwise_crc32(data: &[u8]) -> u32 {
        !data.iter().fold(!0u32, |c, &b| (0..8).fold(c ^ u32::from(b), |c, _| if c & 1 == 1 { (c >> 1) ^ 0xEDB8_8320 } else { c >> 1 }))
    }

    // The tables give the CRC-32 the bits gave: the standard check value, every length from 0 to 40 bytes (the eights
    // and what is left over), and 100,000 bytes that follow no pattern.
    #[test]
    fn crc32_from_tables_is_the_same() {
        assert_eq!((crc32(b"123456789"), crc32(b"")), (0xCBF4_3926, 0));
        let mut x = 0x2545_F491u32;
        let noise: Vec<u8> = (0..100_000).map(|_| { x ^= x << 13; x ^= x >> 17; x ^= x << 5; (x >> 24) as u8 }).collect();
        for n in (0..=40).chain([255, 256, 257, 4_095, 65_537, 100_000]) {
            assert_eq!(crc32(&noise[..n]), bitwise_crc32(&noise[..n]), "{n} bytes");
            assert_eq!(crc32(&noise[noise.len() - n..]), bitwise_crc32(&noise[noise.len() - n..]), "the last {n} bytes");
        }
        assert_eq!(crc32(&[0xff; 1000]), bitwise_crc32(&[0xff; 1000]));
    }

    // A part over the limit is stored, and a part at or under it deflated. The stored part's bytes are in the file as
    // they are, and both sizes are its own.
    #[test]
    fn zip_stores_large_parts() {
        let (small, large) = (vec![7u8; 100], (0..=255u8).cycle().take(101).collect::<Vec<u8>>());
        let file = zip(&[("small", &small), ("large", &large)], 1, 100);
        let (u16_at, u32_at) = (|k: usize| u16::from_le_bytes([file[k], file[k + 1]]) as usize, |k: usize| u32::from_le_bytes(file[k..k + 4].try_into().unwrap()) as usize);
        assert_eq!((u16_at(8), u32_at(22)), (8, 100), "the small part is deflated");
        assert!(u32_at(18) < 100);
        let second = 30 + 5 + u32_at(18);
        assert_eq!((u32_at(second), u16_at(second + 8), u32_at(second + 14), u32_at(second + 18), u32_at(second + 22)), (0x0403_4b50, 0, crc32(&large) as usize, 101, 101), "the large part is stored");
        assert_eq!(&file[second + 35..second + 35 + 101], &large[..]);
        assert_eq!(u16::from_le_bytes(zip(&[("large", &large)], 1, 101)[8..10].try_into().unwrap()), 8, "at the limit: deflated");
    }

    // A 3MF file is a zip of three parts, each deflated with its CRC-32, and the model reads back as it went in.
    #[test]
    fn three_mf_is_a_zip_with_the_model() {
        assert_eq!(crc32(b"123456789"), 0xCBF4_3926);
        // The file's bytes are what they were when zip stored no part and the CRC-32 went a bit at a time (the same
        // miniz_oxide deflates them).
        let tetrahedron = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<model unit=\"millimeter\"><resources><object id=\"1\" type=\"model\"><mesh><vertices><vertex x=\"0\" y=\"0\" z=\"0\"/><vertex x=\"1\" y=\"0\" z=\"0\"/><vertex x=\"0\" y=\"1\" z=\"0\"/><vertex x=\"0\" y=\"0\" z=\"1\"/></vertices><triangles><triangle v1=\"0\" v2=\"2\" v3=\"1\"/><triangle v1=\"0\" v2=\"1\" v3=\"3\"/><triangle v1=\"0\" v2=\"3\" v3=\"2\"/><triangle v1=\"1\" v2=\"2\" v3=\"3\"/></triangles></mesh></object></resources><build><item objectid=\"1\"/></build></model>\n";
        let file = make_3mf(tetrahedron).unwrap();
        assert_eq!((file.len(), bitwise_crc32(&file)), (926, 0x2F1C_8E8F), "the 3MF file has changed");
        let model = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<model unit=\"millimeter\"/>\n";
        let zip = make_3mf(model).unwrap();
        let (u16_at, u32_at) = (|k: usize| u16::from_le_bytes([zip[k], zip[k + 1]]) as usize, |k: usize| u32::from_le_bytes(zip[k..k + 4].try_into().unwrap()) as usize);
        let end = zip.len() - 22;
        assert_eq!(u32_at(end), 0x0605_4b50);
        assert_eq!((u16_at(end + 8), u16_at(end + 10)), (3, 3));
        let (mut at, mut names) = (u32_at(end + 16), Vec::new());
        for _ in 0..3 {
            assert_eq!(u32_at(at), 0x0201_4b50);
            let (crc, packed, size, name_len, local) = (u32_at(at + 16), u32_at(at + 20), u32_at(at + 24), u16_at(at + 28), u32_at(at + 42));
            let name = std::str::from_utf8(&zip[at + 46..at + 46 + name_len]).unwrap().to_string();
            assert_eq!(u32_at(local), 0x0403_4b50);
            assert_eq!(zip[local + 4..local + 30], zip[at + 6..at + 32], "the local header agrees with the directory");
            let start = local + 30 + name_len;
            let data = miniz_oxide::inflate::decompress_to_vec(&zip[start..start + packed]).unwrap();
            assert_eq!((data.len(), crc32(&data) as usize), (size, crc));
            if name == "3D/3dmodel.model" {
                assert_eq!(data, model.as_bytes());
            }
            names.push(name);
            at += 46 + name_len;
        }
        assert_eq!(names, ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"]);
        assert_eq!(at, end, "the directory ends where the end record starts");
        assert!(make_3mf(&" ".repeat(MAX_SVG + 1)).unwrap_err().contains("too large"));
    }

    // A PNG Octet writes carries the drawing in an iTXt chunk before the pixels, and reads back as it went in; the
    // picture still decodes. A PNG from elsewhere, or a hostile one, gives nothing.
    #[test]
    fn png_carries_cdxml_and_reads_back() {
        let png = make_png(SVG, 72.0, true, Some(CDXML)).unwrap();
        assert_eq!(cdxml_from_png(&png).as_deref(), Some(CDXML));
        assert_eq!(cdxml_from_picture(&png).as_deref(), Some(CDXML));
        assert!(png::Decoder::new(std::io::Cursor::new(&png)).read_info().is_ok());
        assert_eq!(cdxml_from_png(&make_png(SVG, 72.0, true, None).unwrap()), None);
        // Cut short anywhere, it gives nothing or the drawing (the chunk comes before the pixels), and never panics.
        for k in (0..png.len()).step_by(7) {
            let x = cdxml_from_png(&png[..k]);
            assert!(x.is_none() || x.as_deref() == Some(CDXML));
        }
        let chunk = |kind: &[u8], data: &[u8]| [&(data.len() as u32).to_be_bytes()[..], kind, data, &[0; 4]].concat();
        let sig = b"\x89PNG\r\n\x1a\n".as_slice();
        let itxt = |flag: u8, text: &[u8]| chunk(b"iTXt", &[b"CDXML\0".as_slice(), &[flag, 0], b"\0\0", text].concat());
        // Uncompressed, as another writer might put it: read.
        assert_eq!(cdxml_from_png(&[sig, &itxt(0, CDXML.as_bytes())].concat()).as_deref(), Some(CDXML));
        // A zip bomb that starts like CDXML stops at the 32 MB cap.
        let mut big = CDXML.as_bytes().to_vec();
        big.resize(40 << 20, b' ');
        let bomb = miniz_oxide::deflate::compress_to_vec_zlib(&big, 1);
        assert_eq!(cdxml_from_png(&[sig, &itxt(1, &bomb)].concat()), None);
        for bad in [
            [sig, &itxt(1, b"not zlib")].concat(),                           // a broken stream
            [sig, &itxt(2, CDXML.as_bytes())].concat(),                      // an unknown compression flag
            [sig, &itxt(0, b"<?xml version=\"1.0\"?><svg/>")].concat(),      // XML that is not CDXML
            [sig, &chunk(b"tEXt", CDXML.as_bytes())].concat(),               // another chunk
            [sig, &u32::MAX.to_be_bytes()[..], b"iTXt"].concat(),            // a length past the end
            [sig, &chunk(b"iTXt", b"CDXML\0\x01")].concat(),                 // cut short in the chunk
            [sig, &chunk(b"IEND", b""), &itxt(0, CDXML.as_bytes())].concat(), // after the end
        ] {
            assert_eq!(cdxml_from_png(&bad), None);
        }
    }

    // Sam's clipboard dumps (ChemDraw's copy, and it copied back out of Word). Set OCTET_CLIPBOARD_DUMPS to the
    // folder holding chemdraw-copy/ and word-copy/ to run this; the files stay out of the repository.
    #[test]
    fn reads_chemdraws_pdf() {
        let Ok(dir) = std::env::var("OCTET_CLIPBOARD_DUMPS") else { return };
        for sub in ["chemdraw-copy", "word-copy"] {
            let pdf = std::fs::read(format!("{dir}/{sub}/0_com.adobe.pdf")).unwrap();
            let x = cdxml_from_pdf(&pdf).unwrap();
            assert!(x.contains("<CDXML"), "{sub}");
        }
        // Octet's PDF copied back out of Word for Mac is the same file, so it reads back as it went in.
        let ours = std::fs::read(format!("{dir}/octet-aspirin/0_com.adobe.pdf")).unwrap();
        assert_eq!(std::fs::read(format!("{dir}/word-octet-aspirin/0_com.adobe.pdf")).unwrap(), ours);
        assert!(cdxml_from_pdf(&ours).unwrap().contains("<CDXML"));
        let old = std::fs::read(format!("{dir}/word-octet-pdf/0_com.adobe.pdf")).unwrap();
        assert!(cdxml_from_pdf(&old).unwrap().contains("<CDXML"));
    }
}
