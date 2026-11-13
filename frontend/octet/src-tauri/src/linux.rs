// Octet from an AppImage, the release's main Linux download (decision 0025), and the programs Octet starts on Linux.
//
// LibreOffice's Octet extension (tools/libreoffice) starts Octet with `--object`. An AppImage can be anywhere, so
// Octet writes its own path (the AppImage's, else its program's) to one small file that the extension reads first:
// $XDG_CONFIG_HOME/<Octet's id>/octet-path. Octet writes it when it starts and at Add to LibreOffice.
//
// An AppImage's runtime and launcher set variables for Octet's own libraries, and most name its mount ($APPDIR):
// LD_LIBRARY_PATH, PATH, PYTHONHOME, GTK_PATH, GIO_MODULE_DIR, XDG_DATA_DIRS and others. The programs Octet starts
// (unopkg, xdg-open) get the session's environment instead, as AppImage-aware apps give theirs.
use std::ffi::{OsStr, OsString};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use tauri::{AppHandle, Manager};

// The variables an AppImage sets that name no folder in its mount: the runtime's own, and its launcher's.
const OWN: [&str; 5] = ["APPIMAGE", "ARGV0", "OWD", "GTK_THEME", "PYTHONDONTWRITEBYTECODE"];

// The AppImage's file and its mount ($APPIMAGE and $APPDIR, which its runtime sets), when Octet runs from one: its
// program is in the mount. A program started from another AppImage has that one's variables. The mount by both its
// names: $APPDIR, and its real path, which Octet's program and AppRun's variables use when $TMPDIR is a link.
fn appimage() -> Option<(PathBuf, [PathBuf; 2])> {
    let file = PathBuf::from(std::env::var_os("APPIMAGE")?);
    let mount = PathBuf::from(std::env::var_os("APPDIR")?);
    let real = mount.canonicalize().ok()?;
    let exe = std::env::current_exe().ok()?;
    (file.is_absolute() && mount.is_absolute() && real.parent().is_some() && exe.starts_with(&real)).then_some((file, [mount, real]))
}

// Octet's path for the extension, written in one step (a temporary file renamed over it), mode 0600, on a thread of
// its own. Only the path: no line end.
pub fn note_path(app: &AppHandle) {
    let own = appimage().map(|(file, _)| file).or_else(|| std::env::current_exe().ok());
    let (Some(own), Ok(dir)) = (own, app.path().app_config_dir()) else { return };
    std::thread::spawn(move || write_private(&dir.join("octet-path"), own.as_os_str().as_bytes()));
}

fn write_private(path: &Path, data: &[u8]) -> std::io::Result<()> {
    use std::io::Write;
    use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt};
    let dir = path.parent().ok_or(std::io::ErrorKind::InvalidInput)?;
    std::fs::DirBuilder::new().recursive(true).mode(0o700).create(dir)?;
    let tmp = dir.join(format!(".octet-path-{}", std::process::id()));
    let result = (|| {
        std::fs::OpenOptions::new().write(true).create_new(true).mode(0o600).open(&tmp)?.write_all(data)?;
        std::fs::rename(&tmp, path)
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

// Starts a program on its own: its own process group, nothing on its input or output, and the session's environment
// when Octet runs from an AppImage. A thread waits for it, so no process is left behind.
pub fn spawn(c: &mut Command) -> std::io::Result<()> {
    use std::os::unix::process::CommandExt;
    if let Some((_, mount)) = appimage() {
        for (key, value) in session_env(std::env::vars_os(), &mount) {
            match value {
                Some(v) => c.env(key, v),
                None => c.env_remove(key),
            };
        }
        // The launcher starts Octet in its mount, which goes when Octet ends: the program starts where Octet was
        // started.
        let owd = std::env::var_os("OWD").map(PathBuf::from).filter(|d| d.is_absolute() && !mount.iter().any(|m| d.starts_with(m)) && d.is_dir());
        c.current_dir(owd.unwrap_or_else(|| "/".into()));
    }
    let mut child = c.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).process_group(0).spawn()?;
    std::thread::spawn(move || child.wait());
    Ok(())
}

// The changes that give the session's environment back, from Octet's in an AppImage mounted at `mount` (None removes
// the variable): each list of folders loses the ones in the mount, a variable left with none goes, and so do OWN.
fn session_env(vars: impl IntoIterator<Item = (OsString, OsString)>, mount: &[PathBuf]) -> Vec<(OsString, Option<OsString>)> {
    let inside = |p: &&[u8]| mount.iter().any(|m| Path::new(OsStr::from_bytes(p)).starts_with(m));
    vars.into_iter()
        .filter_map(|(key, value)| {
            if OWN.iter().any(|k| key == *k) {
                return Some((key, None));
            }
            let parts: Vec<&[u8]> = value.as_bytes().split(|b| *b == b':').collect();
            if !parts.iter().any(inside) {
                return None;
            }
            let kept: Vec<&[u8]> = parts.into_iter().filter(|p| !p.is_empty() && !inside(p)).collect();
            Some((key, (!kept.is_empty()).then(|| OsString::from_vec(kept.join(&b':')))))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    // An AppImage's variables (its runtime's, AppImageKit's AppRun and Tauri's GTK hook) against the session's. AppRun
    // names the mount by its real path (r), the runtime and the hook by $APPDIR (m).
    #[test]
    fn programs_get_the_sessions_environment() {
        let (m, r) = ("/tmp/.mount_OctetD1x2", "/data/tmp/.mount_OctetD1x2");
        let vars = [
            ("APPDIR", m.to_string()),
            ("APPIMAGE", "/home/u/Octet Draw.AppImage".into()),
            ("ARGV0", "./Octet Draw.AppImage".into()),
            ("OWD", "/home/u".into()),
            ("PATH", format!("{r}/usr/bin/:{r}/usr/sbin/:{r}/bin/:/usr/local/bin:/usr/bin")),
            ("LD_LIBRARY_PATH", format!("{r}/usr/lib/:{r}/lib/x86_64-linux-gnu/:")),
            ("PYTHONHOME", format!("{r}/usr/")),
            ("PYTHONDONTWRITEBYTECODE", "1".into()),
            ("XDG_DATA_DIRS", format!("{m}/usr/share:/usr/share:{m}/usr/share/:/usr/local/share")),
            ("GTK_PATH", format!("{m}//usr/lib/gtk-3.0")),
            ("GTK_THEME", "Adwaita:light".into()),
            ("HOME", "/home/u".into()),
            ("DISPLAY", ":0".into()),
            ("NOT_THE_MOUNT", "/tmp/.mount_OctetD1x2x/usr/lib".into()),
        ];
        let got = session_env(vars.iter().map(|(k, v)| (OsString::from(k), OsString::from(v))), &[m.into(), r.into()]);
        let want: Vec<(OsString, Option<OsString>)> = [
            ("APPDIR", None),
            ("APPIMAGE", None),
            ("ARGV0", None),
            ("OWD", None),
            ("PATH", Some("/usr/local/bin:/usr/bin")),
            ("LD_LIBRARY_PATH", None),
            ("PYTHONHOME", None),
            ("PYTHONDONTWRITEBYTECODE", None),
            ("XDG_DATA_DIRS", Some("/usr/share:/usr/local/share")),
            ("GTK_PATH", None),
            ("GTK_THEME", None),
        ]
        .iter()
        .map(|(k, v)| (OsString::from(k), v.map(OsString::from)))
        .collect();
        assert_eq!(got, want, "HOME, DISPLAY and a folder beside the mount stay as they are");
    }

    // The path file: only the path, mode 0600, in a folder of mode 0700 that it makes, and written again in one step.
    #[test]
    fn the_path_file_is_private() {
        use std::os::unix::fs::PermissionsExt;
        let dir = std::env::temp_dir().join(format!("octet-path-{}", std::process::id()));
        let path = dir.join("io.github.samchemman.octet-draw/octet-path");
        write_private(&path, b"/home/u/Octet Draw.AppImage").unwrap();
        write_private(&path, b"/usr/bin/octet").unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), b"/usr/bin/octet");
        assert_eq!(std::fs::metadata(&path).unwrap().permissions().mode() & 0o777, 0o600);
        assert_eq!(std::fs::metadata(path.parent().unwrap()).unwrap().permissions().mode() & 0o777, 0o700);
        assert_eq!(std::fs::read_dir(path.parent().unwrap()).unwrap().count(), 1, "no temporary file stays");
        std::fs::remove_dir_all(&dir).unwrap();
    }
}
