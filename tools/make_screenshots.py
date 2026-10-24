"""Screenshots für das README (docs/screenshots/<tab>_<light|dark>_<de|en>.png).

Startet das Hauptfenster (1600 × 1000, ohne Bildschirm: QT_QPA_PLATFORM=offscreen) mit einem **leeren Projekt** und
speichert je Tab ein Bild über QWidget.grab: die zentrierte Anleitung des leeren Tabs (was herauskommt, Dateien,
Schritte, Knopf für den ersten Schritt). Nutzerwunsch: keine Daten in den README-Bildern, auch keine Beispieldaten.
Ausnahme Coverbild (Nutzerwunsch): Startbildschirm (welcome_<theme>_<lang>.png) mit dem Beispielprojekt (zwei
erfundene Verbindungen, nur Namen, Strukturen und Analytik-Abzeichen; Pfade als ~/Documents/…).
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

from elucida.app import main_window as G  # noqa: E402

SIZE = (1600, 1000)
# (Dateiname, Tab-Schlüssel, Themes) in der Reihenfolge der Tabs
# Alle README-Bilder dunkel (Nutzerwunsch), auch das Coverbild
SHOTS = tuple((name, key, ("dark",)) for name, key in (
    ("synthesis", "syn"), ("nmr", "nmr"), ("irms", "irms"), ("hrms", "hrms"), ("eps", "eps"), ("overlay", "overlay"),
    ("fluorescence", "fluo"), ("cv", "cv"), ("sec", "sec"), ("epr", "epr"), ("xray", "xray"), ("dft", "dft")))


def pump(sec=0.6):
    t0 = time.time()
    while time.time() - t0 < sec:
        QApplication.processEvents()
        time.sleep(0.02)


def shoot_welcome(w, outdir, lang, theme, work):
    """Coverbild: Startbildschirm mit dem Beispielprojekt (Projekte + zuletzt geöffnete Verbindungen)."""
    from elucida.app import welcome as WEL
    keep = w.project_dir
    w.close_project()
    w.close_publication()
    real = WEL.short_path
    base = str(Path(work).resolve())                   # macOS: /var -> /private/var
    WEL.short_path = lambda p: "~/Documents/" + Path(p).resolve().relative_to(base).as_posix() if str(
        Path(p).resolve()).startswith(base) else real(p)
    try:
        w.fill_recent_list()
        pump(0.8)
        p = Path(outdir) / f"welcome_{theme}_{lang}.png"
        w.grab().save(str(p))
        print(p.name)
    finally:
        WEL.short_path = real
    w.open_project(keep, recent=False)
    pump(0.5)



def shoot(w, outdir, lang, theme):
    for name, key, themes in SHOTS:
        if theme not in themes:
            continue
        idx = w._tab_keys.index(key)
        w.main_tabs.setCurrentIndex(idx)                  # Tabs werden erst beim Anzeigen gebaut (Platzhalter)
        pump(0.3)
        page = w.main_tabs.widget(idx)
        for fn in ("sync_widgets", "update_preview", "render"):
            if getattr(type(page), fn, None) not in (None, QWidget.render):    # nicht QWidget.render
                getattr(page, fn)()
        if key == "eps":
            w.render()
        pump(1.2)
        w.statusBar().clearMessage()                      # Einblendung („Projekt gespeichert“) nicht im Bild
        pump(0.1)
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
        w.open_demo_publication(work / "Beispielprojekt")      # nur fürs Coverbild (Startbildschirm)
        w.close_publication()
        assert w.create_project(work / "Elucida")
        w.settings.setValue("recent_projects", __import__("json").dumps(      # Coverbild: nur das Beispielprojekt
            [str((work / "Beispielprojekt" / n).resolve()) for n in ("S3", "S2")]))
        for lang in ("de", "en"):
            w.switch_lang(lang)
            for theme in ("dark",):
                w.switch_theme(theme)
                w.resize(*SIZE)
                pump(0.5)
                shoot_welcome(w, outdir, lang, theme, work)
                shoot(w, outdir, lang, theme)
        w.switch_theme("system")
        w.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main(*sys.argv[1:2])
