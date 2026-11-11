"""Rendert die App-Icons aus assets/icon-light.svg und assets/icon-dark.svg (1024 × 1024, transparent außerhalb der
Kachel):

    python tools/make_icon.py

- hell: assets/icon.png (Fenster unter Windows/Linux, README, AppImage), assets/icon.ico (Windows, 16–256 px),
  assets/png/icon-<n>.png (Standardgrößen für Windows/Web)
- dunkel: assets/icon-dark.png (Fenster/Dock unter macOS), assets/icon.icns (macOS, über ein .iconset mit allen
  Retina-Größen; braucht iconutil, also macOS)

tools/build.py nimmt je System .ico/.icns/.png (--icon); die Dateien sind eingecheckt, CI rendert nichts.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZES = (16, 32, 48, 64, 128, 180, 192, 256, 512)
ICONSET = (16, 32, 128, 256, 512)                   # je @1x und @2x


def render(svg, size):
    """SVG direkt in der Zielgröße rendern (schärfer als Verkleinern des 1024er-Bildes)."""
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(svg)).render(p)
    p.end()
    return img


def save(svg, size, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    render(svg, size).save(str(out))
    return out


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    light, dark = ASSETS / "icon-light.svg", ASSETS / "icon-dark.svg"
    out = [save(light, 1024, ASSETS / "icon.png"), save(dark, 1024, ASSETS / "icon-dark.png")]
    out += [save(light, n, ASSETS / "png" / f"icon-{n}.png") for n in PNG_SIZES]
    with tempfile.TemporaryDirectory() as tmp:
        frames = [Image.open(save(light, n, Path(tmp) / f"{n}.png")) for n in ICO_SIZES]
        frames[-1].save(ASSETS / "icon.ico", sizes=[(n, n) for n in ICO_SIZES], append_images=frames[:-1])
        out.append(ASSETS / "icon.ico")
        if shutil.which("iconutil"):
            iconset = Path(tmp) / "icon.iconset"
            for n in ICONSET:
                save(dark, n, iconset / f"icon_{n}x{n}.png")
                save(dark, 2 * n, iconset / f"icon_{n}x{n}@2x.png")
            subprocess.check_call(["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "icon.icns")])
            out.append(ASSETS / "icon.icns")
        else:
            print("iconutil fehlt (nur macOS): assets/icon.icns nicht erneuert")
    for p in out:
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
