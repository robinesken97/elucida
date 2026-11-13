// Measured spectra the page opens (audit item CH-29): JCAMP-DX files (.jdx, .dx, .jcamp) as text, Galactic SPC files
// (.spc, binary) and Bruker's processed data (a pdata folder with procs and 1r, or the experiment folder above it) each
// as an envelope the page reads (src/jcamp.ts, readSpcText and readBrukerText). The page checks what they hold; here
// they are only found and read, with limits. They are not drawings: Octet does not save over them or list them on Home.
use std::fs;
use std::path::{Path, PathBuf};

use crate::MAX_BYTES;

pub const EXTENSIONS: [&str; 4] = ["jdx", "dx", "jcamp", "spc"];
const MAX_PARAMS: u64 = 4 << 20; // procs and acqus: text files of a few kilobytes

// A spectrum file by its extension: JCAMP-DX or SPC.
pub fn is_jcamp(path: &Path) -> bool {
    path.extension().and_then(|e| e.to_str()).is_some_and(|e| EXTENSIONS.contains(&e.to_ascii_lowercase().as_str()))
}

// A JCAMP-DX file's text. Many instruments write Latin-1, not UTF-8: bytes that are not UTF-8 are read as Latin-1.
// An SPC file is binary: "OCTET-SPC 1", then JSON with its name and its bytes in base64.
pub fn read_jcamp(path: &Path, name: &str) -> Result<String, String> {
    match fs::metadata(path) {
        Err(_) => Err("This file is not where it was. It was moved or deleted.".into()),
        Ok(m) if m.len() > MAX_BYTES => Err(format!("Octet cannot open {name}. It is larger than 64 MB.")),
        Ok(_) => {
            let bytes = fs::read(path).map_err(|_| format!("Octet cannot read {name}."))?;
            if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("spc")) {
                use base64::Engine;
                let json = serde_json::json!({ "name": name, "data": base64::engine::general_purpose::STANDARD.encode(bytes) });
                return Ok(format!("OCTET-SPC 1\n{json}"));
            }
            Ok(String::from_utf8(bytes).unwrap_or_else(|e| e.into_bytes().iter().map(|&b| b as char).collect()))
        }
    }
}

// The pdata folder of Bruker processed data at `path`: the folder itself (it has procs and 1r), its 1r or procs file,
// or an experiment folder (its pdata/1).
pub fn bruker_folder(path: &Path) -> Option<PathBuf> {
    let has = |d: &Path| d.join("procs").is_file() && d.join("1r").is_file();
    let name = path.file_name().and_then(|n| n.to_str()).unwrap_or_default();
    let dir = if path.is_file() && (name == "1r" || name == "procs") { path.parent()?.to_path_buf() } else { path.to_path_buf() };
    if dir.is_dir() && has(&dir) {
        return Some(dir);
    }
    let first = dir.join("pdata").join("1");
    (dir.is_dir() && has(&first)).then_some(first)
}

// Bruker's processed data as the page reads it: "OCTET-BRUKER 1", then JSON with a name (the data set and experiment
// number), procs, acqus (if it is there) and 1r in base64.
pub fn read_bruker(pdata: &Path) -> Result<String, String> {
    use base64::Engine;
    let text = |p: PathBuf, most: u64| -> Result<Option<String>, String> {
        match fs::metadata(&p) {
            Err(_) => Ok(None),
            Ok(m) if m.len() > most => Err("Octet cannot open this Bruker folder. A parameter file is too large.".into()),
            Ok(_) => fs::read(&p).map(|b| Some(String::from_utf8_lossy(&b).into_owned())).map_err(|_| "Octet cannot read this Bruker folder.".into()),
        }
    };
    let procs = text(pdata.join("procs"), MAX_PARAMS)?.ok_or("This Bruker folder has no procs file.")?;
    let expno = pdata.parent().and_then(Path::parent);
    let acqus = match expno { Some(e) => text(e.join("acqus"), MAX_PARAMS)?, None => None };
    let size = fs::metadata(pdata.join("1r")).map_err(|_| "This Bruker folder has no 1r file.".to_string())?.len();
    if size > MAX_BYTES {
        return Err("Octet cannot open this Bruker folder. Its 1r file is larger than 64 MB.".into());
    }
    let data = fs::read(pdata.join("1r")).map_err(|_| "Octet cannot read this Bruker folder.".to_string())?;
    let part = |p: Option<&Path>| p.and_then(Path::file_name).map(|n| n.to_string_lossy().into_owned());
    let name = match (part(expno.and_then(Path::parent)), part(expno)) {
        (Some(set), Some(e)) => format!("{set} {e}"),
        (_, Some(e)) => e,
        _ => "Bruker spectrum".into(),
    };
    let json = serde_json::json!({ "name": name, "procs": procs, "acqus": acqus, "data": base64::engine::general_purpose::STANDARD.encode(data) });
    Ok(format!("OCTET-BRUKER 1\n{json}"))
}

// A spectrum named on the clipboard: a copied file (its file URL) or a pasted path, to a JCAMP-DX file or a Bruker
// folder. Returns its name and text; None for anything else, so the paste goes on as usual.
pub fn from_clipboard(file_url: Option<&str>, text: Option<&str>) -> Option<(String, String)> {
    // A file URL, or a path as it is (macOS hands over a file reference already turned into its path).
    let to_path = |s: &str| if s.starts_with("file:") { tauri::Url::parse(s).ok()?.to_file_path().ok() } else { Some(PathBuf::from(s)) };
    let from_url = file_url.and_then(|u| u.lines().map(str::trim).find(|l| !l.is_empty() && !l.starts_with('#'))).and_then(to_path);
    let from_text = text.map(str::trim).filter(|t| !t.contains('\n') && t.len() < 4096).and_then(|t| to_path(t.trim_matches(|c| c == '"' || c == '\'')));
    let path = from_url.or(from_text).filter(|p| p.is_absolute())?;
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    if is_jcamp(&path) && path.is_file() {
        return Some((name.clone(), read_jcamp(&path, &name).ok()?));
    }
    bruker_folder(&path).and_then(|d| read_bruker(&d).ok()).map(|t| (name, t))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spectra_are_found_and_read_with_limits() {
        let dir = std::env::temp_dir().join(format!("octet-spectrum-{}", std::process::id()));
        let pdata = dir.join("ethyl").join("1").join("pdata").join("1");
        fs::create_dir_all(&pdata).unwrap();
        // A JCAMP-DX file in Latin-1 (a degree sign), read as text all the same.
        let jdx = dir.join("a.JDX");
        fs::write(&jdx, b"##TITLE= 25 \xb0C\n##END=\n").unwrap();
        assert!(is_jcamp(&jdx) && !is_jcamp(&dir.join("a.mol")));
        assert_eq!(read_jcamp(&jdx, "a.JDX").unwrap(), "##TITLE= 25 °C\n##END=\n");
        // An SPC file: its bytes in base64, with its name.
        let spc = dir.join("b.SPC");
        fs::write(&spc, [0u8, 0x4b, 0xff]).unwrap();
        assert!(is_jcamp(&spc));
        let text = read_jcamp(&spc, "b.SPC").unwrap();
        let json: serde_json::Value = serde_json::from_str(text.strip_prefix("OCTET-SPC 1\n").unwrap()).unwrap();
        assert_eq!((json["name"].as_str(), json["data"].as_str()), (Some("b.SPC"), Some("AEv/")));
        let big = dir.join("big.dx");
        fs::File::create(&big).unwrap().set_len(MAX_BYTES + 1).unwrap();
        assert!(read_jcamp(&big, "big.dx").unwrap_err().contains("64 MB"));
        // Bruker: found from the pdata folder, its 1r, or the experiment folder; read with its acqus.
        fs::write(pdata.join("procs"), "##$SI= 2\n").unwrap();
        fs::write(pdata.join("1r"), [1u8, 0, 0, 0, 2, 0, 0, 0]).unwrap();
        fs::write(dir.join("ethyl").join("1").join("acqus"), "##$NUC1= <1H>\n").unwrap();
        assert_eq!(bruker_folder(&pdata), Some(pdata.clone()));
        assert_eq!(bruker_folder(&pdata.join("1r")), Some(pdata.clone()));
        assert_eq!(bruker_folder(&dir.join("ethyl").join("1")), Some(pdata.clone()));
        assert_eq!(bruker_folder(&dir), None);
        let text = read_bruker(&pdata).unwrap();
        assert!(text.starts_with("OCTET-BRUKER 1\n"));
        let json: serde_json::Value = serde_json::from_str(&text["OCTET-BRUKER 1\n".len()..]).unwrap();
        assert_eq!(json["name"], "ethyl 1");
        assert_eq!(json["data"], "AQAAAAIAAAA=");
        assert_eq!(json["acqus"], "##$NUC1= <1H>\n");
        // The clipboard: a pasted path or a file URL to a spectrum; anything else is left alone.
        let url = tauri::Url::from_file_path(&jdx).unwrap().to_string();
        assert_eq!(from_clipboard(Some(&url), None).map(|s| s.0), Some("a.JDX".into()));
        assert_eq!(from_clipboard(None, Some(&format!("  \"{}\"\n", jdx.display()))).map(|s| s.0), Some("a.JDX".into()));
        assert!(from_clipboard(None, Some(&pdata.display().to_string())).is_some_and(|s| s.1.starts_with("OCTET-BRUKER")));
        assert_eq!(from_clipboard(None, Some("CCO")), None);
        assert_eq!(from_clipboard(None, Some(&dir.join("a.mol").display().to_string())), None);
        fs::remove_dir_all(&dir).unwrap();
    }
}
