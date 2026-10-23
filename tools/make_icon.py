"""Rendert assets/icon.svg nach assets/icon.png (1024 × 1024, transparent außerhalb der Kachel).

    python tools/make_icon.py

PyInstaller macht daraus .ico/.icns (tools/build.py, --icon); gehört nicht in den Build.
"""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent


def main(size=1024):
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])  # noqa: F841
    r = QSvgRenderer(str(ROOT / "assets" / "icon.svg"))
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    r.render(p)
    p.end()
    out = ROOT / "assets" / "icon.png"
    img.save(str(out))
    print(out)


if __name__ == "__main__":
    main()
