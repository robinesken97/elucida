"""Screenshots für das README (docs/screenshots/<tab>_<light|dark>_<de|en>.png).

Startet das Hauptfenster (1600 × 1000, ohne Bildschirm: QT_QPA_PLATFORM=offscreen), lädt **nur künstliche Daten**
(Generatoren des Selbsttests und erfundene Beispiele, keine Messdateien, keine echten Verbindungen) und speichert
je Tab ein Bild über QWidget.grab. Die Beispieldaten kommen aus uvvis_demo (auch Hilfe → Beispielprojekt).
Das Werkzeug selbst gehört nicht in den PyInstaller-Build.

    python tools/make_screenshots.py [Zielordner]
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

import uvvis_gui as G  # noqa: E402

SIZE = (1600, 1000)
# (Dateiname, Tab-Schlüssel, Themes) in der Reihenfolge der Tabs
SHOTS = (("synthesis", "syn", ("light",)), ("nmr", "nmr", ("light",)), ("eps", "eps", ("light", "dark")),
         ("overlay", "overlay", ("light",)), ("fluorescence", "fluo", ("light",)), ("cv", "cv", ("light",)),
         ("sec", "sec", ("light",)), ("epr", "epr", ("light",)), ("xray", "xray", ("light", "dark")),
         ("dft", "dft", ("light",)))


def pump(sec=0.6):
    t0 = time.time()
    while time.time() - t0 < sec:
        QApplication.processEvents()
        time.sleep(0.02)


from uvvis_demo import load_data  # noqa: E402,F401  (künstliche Daten: uvvis_demo)


def shoot(w, outdir, lang, theme):
    pages = {k: w.main_tabs.widget(i) for i, k in enumerate(w._tab_keys)}
    for name, key, themes in SHOTS:
        if theme not in themes:
            continue
        page = pages[key]
        w.main_tabs.setCurrentWidget(page)
        pump(0.3)
        for fn in ("sync_widgets", "update_preview", "render"):
            if getattr(type(page), fn, None) not in (None, QWidget.render):    # nicht QWidget.render
                getattr(page, fn)()
        if key == "eps":
            w.render()
        pump(1.2)
        p = Path(outdir) / f"{name}_{theme}_{lang}.png"
        w.grab().save(str(p))
        print(p.name)


def main(outdir=ROOT / "docs" / "screenshots"):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="elucida_shots_"))
    try:
        G.SETTINGS_FILE = work / "settings.ini"           # nicht die echten Benutzereinstellungen
        app = QApplication.instance() or QApplication(sys.argv[:1])  # noqa: F841
        QApplication.setApplicationVersion(G.APP_VERSION)
        w = G.MainWindow()
        w.settings.setValue("update_auto", False)
        w.resize(*SIZE)
        w.show()
        assert w.create_project(work / "Demo")
        load_data(w, work / "input")
        w.syn_tab.sync_widgets()
        for lang in ("de", "en"):
            w.switch_lang(lang)
            for theme in ("light", "dark"):
                w.switch_theme(theme)
                w.resize(*SIZE)
                pump(0.5)
                shoot(w, outdir, lang, theme)
        w.switch_theme("system")
        w.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main(*sys.argv[1:2])
