"""Baut Elucida mit PyInstaller für das aktuelle Betriebssystem.

    pip install -r requirements.txt pyinstaller
    python build.py

Ergebnis: dist/Elucida/ (Windows/Linux) bzw. dist/Elucida.app (macOS).
"""
import plistlib
import re
import subprocess
import sys
from pathlib import Path

# Versionsnummer nur an einer Stelle pflegen: APP_VERSION in uvvis_gui.py
VERSION = re.search(r'^APP_VERSION = "([^"]+)"', Path("uvvis_gui.py").read_text(encoding="utf-8"), re.M).group(1)

args = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
    "--name", "Elucida",
    "--windowed",
    "--icon", "assets/icon.png",
    "--add-data", f"assets{';' if sys.platform.startswith('win') else ':'}assets",
    "--collect-all", "rdkit",
    "--collect-all", "pymupdf",
    "--collect-all", "pillow_heif",
    "--collect-all", "onnxruntime",
    "--hidden-import", "parseuv_lite",
    "--hidden-import", "olefile",
    "--hidden-import", "openpyxl",
    "--hidden-import", "uvvis_demo",               # Beispielprojekt (Hilfe-Menü), nur bei Bedarf importiert
    "--hidden-import", "uvvis_orbitals",           # Orbitale im DFT-Tab (Cube/Molden, Raycasting)
    "--hidden-import", "colorsys",                 # Orbitalfarben wie IboView (in uvvis_orbitals nur lokal importiert)
    "--hidden-import", "PySide6.QtSvg",          # Symbole/Theme (uvvis_style)
    "--hidden-import", "matplotlib.backends.backend_qtagg",
    "--hidden-import", "matplotlib.backends.backend_agg",
    "--hidden-import", "matplotlib.backends.backend_pdf",
    "--hidden-import", "matplotlib.backends.backend_svg",
    "--exclude-module", "tkinter",
    "--exclude-module", "PySide6.QtWebEngineCore",
    "--exclude-module", "PySide6.Qt3DCore",
    "--exclude-module", "PySide6.QtQuick",
    "--exclude-module", "PySide6.QtQml",
    "--exclude-module", "PySide6.QtMultimedia",
    "--exclude-module", "PySide6.QtCharts",
    "--exclude-module", "PySide6.QtDataVisualization",
    "uvvis_gui.py",
]
if sys.platform == "darwin":
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
