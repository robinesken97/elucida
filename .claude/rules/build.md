---
paths:
  - ".github/workflows/**"
  - "tools/build.py"
  - "tools/make_icon.py"
  - "tools/release_notes.py"
---

# Build, CI und Plattformen

- **AppImage (Linux):** in CI aus dem PyInstaller-Ordner gebaut; appimagetool und type2-Runtime mit fester
  Version und SHA-256 in `build.yml` – bei Updates beide Prüfsummen neu eintragen.
- **macOS-Version:** `tools/build.py` liest `APP_VERSION` und schreibt sie nach dem Build in die `Info.plist`,
  danach `codesign --force --deep --sign -` (Signatur schließt die Info.plist ein).
- macOS-Build ist unsigniert (Gatekeeper: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“).
  Trackpad-Zoom und HiDPI-Vorschau auf echter Mac-Hardware sind noch nicht verifiziert.
- **macOS arm64:** seit 2.4.0 auf `macos-15` (GitHub schaltet `macos-14` am 2026-11-02 ab, vorher Brownouts =
  Job sofort „cancelled“ ohne Runner; Ursache steht in den Annotations des Jobs).
- **macOS Intel** (`macos-15-intel`-Runner): rdkit nur bis 2025.9.3, onnxruntime nur bis 1.23.2 als
  x86_64-Wheel (pip wählt sie automatisch); numpy/PySide6/opencv verlangen macOS 14. Der Runner ist
  befristet – fällt er weg, Intel-Build aus der Matrix nehmen.
