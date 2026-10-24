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

# Versionsnummer nur an einer Stelle pflegen: APP_VERSION in elucida/__init__.py
VERSION = re.search(r'^APP_VERSION = "([^"]+)"', Path("elucida/__init__.py").read_text(encoding="utf-8"), re.M).group(1)

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
    "--hidden-import", "elucida.formats.parseuv_lite",
    "--hidden-import", "olefile",
    "--hidden-import", "openpyxl",
    "--collect-submodules", "elucida",           # alle eigenen Module, auch nur bei Bedarf importierte (z. B. demo)
    "--hidden-import", "PySide6.QtSvg",          # Symbole/Theme (elucida/app/style.py)
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
    "Elucida.py",
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
