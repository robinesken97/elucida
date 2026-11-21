"""Baut Elucida mit PyInstaller für das aktuelle Betriebssystem.

    pip install -r requirements.txt pyinstaller
    python tools/build.py

Ergebnis: dist/Elucida/ (Windows/Linux) bzw. dist/Elucida.app (macOS).
"""
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)     # Pfade relativ zur Repo-Wurzel (dist/ liegt dort)

# The embedded editor assets must be built before packaging.
subprocess.run([sys.executable, "tools/build_octet.py"], check=True)

# Versionsnummer nur an einer Stelle pflegen: APP_VERSION in elucida/__init__.py
VERSION = re.search(r'^APP_VERSION = "([^"]+)"', Path("elucida/__init__.py").read_text(encoding="utf-8"), re.M).group(1)

args = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
    "--name", "Elucida",
    "--windowed",
    "--icon", {"darwin": "assets/icon.icns", "win32": "assets/icon.ico"}.get(sys.platform, "assets/icon.png"),
    "--add-data", f"assets{';' if sys.platform.startswith('win') else ':'}assets",
    # Rauchtest der gebauten App (elucida/selftest_smoke.py) liest die Liste der Module unten aus dieser Datei
    "--add-data", f"tools/build.py{';' if sys.platform.startswith('win') else ':'}tools",
    "--collect-all", "rdkit",
    "--collect-all", "pymupdf",
    "--collect-all", "pillow_heif",
    "--collect-all", "onnxruntime",
    "--hidden-import", "elucida.formats.parseuv_lite",
    "--hidden-import", "olefile",
    "--hidden-import", "openpyxl",
    "--hidden-import", "rapidocr",               # Texterkennung (elucida/core/ocr.py, erst bei Bedarf geladen)
    "--collect-data", "rapidocr",                # ONNX-Modelle und config.yaml im Paket
    "--collect-submodules", "elucida",           # alle eigenen Module, auch nur bei Bedarf importierte (z. B. demo)
    "--hidden-import", "PySide6.QtSvg",          # Symbole/Theme (elucida/app/style.py)
    "--hidden-import", "colorsys",                 # Orbitalfarben wie IboView (in elucida/core/orbitals nur lokal importiert)
    "--hidden-import", "matplotlib.backends.backend_qtagg",
    "--hidden-import", "matplotlib.backends.backend_agg",
    "--hidden-import", "matplotlib.backends.backend_pdf",
    "--hidden-import", "matplotlib.backends.backend_svg",
    "--exclude-module", "tkinter",
    "--hidden-import", "PySide6.QtWebEngineCore",
    "--hidden-import", "PySide6.QtWebEngineWidgets",
    "--hidden-import", "PySide6.QtWebChannel",
    "--exclude-module", "PySide6.Qt3DCore",
    "--exclude-module", "PySide6.QtMultimedia",
    "--exclude-module", "PySide6.QtCharts",
    "--exclude-module", "PySide6.QtDataVisualization",
    "Elucida.py",
]
if sys.platform == "win32":
    # Versionsressource der .exe (Eigenschaften → Details, sonst leer); Text im Format von PyInstallers versioninfo
    nums = tuple((list(map(int, re.findall(r"\d+", VERSION)[:3])) + [0, 0, 0, 0])[:4])
    vfile = Path("build/version_info.txt")
    vfile.parent.mkdir(exist_ok=True)
    vfile.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Elucida'),
      StringStruct('FileDescription', 'Elucida'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'Elucida'),
      StringStruct('OriginalFilename', 'Elucida.exe'),
      StringStruct('ProductName', 'Elucida'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")
    args[4:4] = ["--version-file", str(vfile)]
if sys.platform == "darwin":
    args[4:4] = ["--hidden-import", "AppKit", "--hidden-import", "Foundation"]
    args[4:4] = ["--osx-bundle-identifier", "de.elucida.app"]
print(" ".join(args))
rc = subprocess.call(args)
if rc == 0 and sys.platform == "darwin":
    # Version in die Info.plist (sonst zeigt der Finder 0.0.0), danach neu ad-hoc signieren,
    # weil die Signatur die Info.plist einschließt
    app = Path("dist/Elucida.app")
    plist = app / "Contents" / "Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info.update(CFBundleShortVersionString=VERSION, CFBundleVersion=VERSION)
    plist.write_bytes(plistlib.dumps(info))
    rc = subprocess.call(["codesign", "--force", "--deep", "--sign", "-", str(app)])
    print(f"Info.plist: Version {VERSION}")
sys.exit(rc)
