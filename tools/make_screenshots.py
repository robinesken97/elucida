"""Screenshots für das README (docs/screenshots/<tab>_<light|dark>_<de|en>.png).

Startet das Hauptfenster (1600 × 1000; unter macOS als echtes Fenster, sonst QT_QPA_PLATFORM=offscreen) mit dem
**Beispielprojekt** (erfundene Daten, `app/demo.py`) und speichert über QWidget.grab je Tab ein Bild der Verbindung S3
mit geladenen Daten (Nutzerwunsch 2026-11-12, vorher leere Tabs mit Anleitung): Abbildung rechts, links der Schritt
mit den aussagekräftigsten Einstellungen (`SHOTS`). Coverbild: Startbildschirm (welcome_<theme>_<lang>.png) mit dem
Beispielprojekt (Pfade als ~/Documents/…), dazu Projektseite, Vergleich (Eigenschaftstabelle) und Reaktionspfad.
Das Werkzeug selbst gehört nicht in den PyInstaller-Build.

    python tools/make_screenshots.py [Zielordner]
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Ohne Bildschirm zeichnet der Zeicheneditor (WebEngine) nicht (weiße Fläche in Synthese und Reaktionspfad) und die
# Bilder haben nur einfache Auflösung: unter macOS deshalb mit echtem Fenster.
if sys.platform != "darwin":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from elucida.app import main_window as G  # noqa: E402

SIZE = (1600, 1000)
SHOW = "S3"                                       # Verbindung des Beispielprojekts mit Daten in allen Tabs
# (Dateiname, Tab-Schlüssel, Themes, Schritt der linken Spalte) in der Reihenfolge der Tabs
# Alle README-Bilder dunkel (Nutzerwunsch), auch das Coverbild
SHOTS = tuple((name, key, ("dark",), step) for name, key, step in (
    ("compound", "compound", 0), ("synthesis", "syn", 0), ("nmr", "nmr", 0), ("irms", "irms", 0), ("hrms", "hrms", 0),
    ("eps", "eps", 1), ("overlay", "overlay", 0), ("uvkin", "uvkin", 1), ("fluorescence", "fluo", 0), ("cv", "cv", 1),
    ("sec", "sec", 0), ("hcell", "hcell", 0), ("epr", "epr", 1), ("xray", "xray", 0), ("dft", "dft", 0),
    ("other", "other", 0)))


def pump(sec=0.6):
    t0 = time.time()
    while time.time() - t0 < sec:
        QApplication.processEvents()
        time.sleep(0.02)


def clear_toast(w):
    """Einblendungen nicht im Bild (auch die Meldung des beim Sprachwechsel verworfenen Zeicheneditors)."""
    w.statusBar().clearMessage()
    pump(0.1)


def shoot_welcome(w, outdir, lang, theme, work):
    """Coverbild: Startbildschirm mit dem Beispielprojekt (Projekte + zuletzt geöffnete Verbindungen), dazu die Seite
    des Beispielprojekts (Verbindungen mit Checkliste) für den Projekt-Abschnitt."""
    from elucida.app import welcome as WEL
    w.go_home()
    real = WEL.short_path
    base = str(Path(work).resolve())                   # macOS: /var -> /private/var
    WEL.short_path = lambda p: "~/Documents/" + Path(p).resolve().relative_to(base).as_posix() if str(
        Path(p).resolve()).startswith(base) else real(p)
    try:
        w.fill_recent_list()
        pump(2.5)                                         # Karten und Projektliste erscheinen mit echtem Fenster erst nach > 1 s
        p = Path(outdir) / f"welcome_{theme}_{lang}.png"
        clear_toast(w)
        w.grab().save(str(p))
        print(p.name)
        w.open_publication(work / "Beispielprojekt")
        pump(0.8)
        p = Path(outdir) / f"project_{theme}_{lang}.png"
        clear_toast(w)
        w.grab().save(str(p))
        print(p.name)
        shoot_comparison(w, outdir, lang, theme)
        from elucida.app import publication as PUB         # Reaktionspfad des Beispielprojekts: Rechnungen + Profil
        w.pub_page.open_path(PUB.load(work / "Beispielprojekt")["reaction_paths"][0])
        ws = w.pub_page.path_workspace
        ws.tabs.setCurrentWidget(ws.calc_page)
        pump(3.0)
        p = Path(outdir) / f"paths_{theme}_{lang}.png"
        clear_toast(w)
        w.grab().save(str(p))
        print(p.name)
        w.pub_page.close_path()
    finally:
        WEL.short_path = real
    w.open_project(work / "Beispielprojekt" / SHOW, recent=False)     # Tab-Bilder: Verbindung mit Daten
    pump(0.5)



def shoot_comparison(w, outdir, lang, theme):
    """Projektseite → Vergleich: Eigenschaftstabelle des Beispielprojekts (Schritt „Tabelle“ links)."""
    page = w.pub_page
    page.project_tabs.setCurrentWidget(page.compare_page)
    pump(0.5)
    page.compare_page.open("demo00table")
    page.compare_page.tab.steps.set_step(1, remember=False)
    pump(0.8)
    p = Path(outdir) / f"comparison_{theme}_{lang}.png"
    clear_toast(w)
    w.grab().save(str(p))
    print(p.name)
    page.project_tabs.setCurrentIndex(0)


def shoot(w, outdir, lang, theme):
    for name, key, themes, step in SHOTS:
        if theme not in themes:
            continue
        idx = w._tab_keys.index(key)
        w.main_tabs.setCurrentIndex(idx)                  # Tabs werden erst beim Anzeigen gebaut (Platzhalter)
        pump(0.3)
        page = w.main_tabs.widget(idx)
        steps = w.steps if key == "eps" else getattr(page, "steps", None)
        if steps is not None:
            steps.set_step(step, remember=False)
        w._update_nav_dots()                              # Tabs mit Daten (Abbildungs-Chips im Tab Verbindung)
        for fn in ("sync_si_export", "sync_widgets", "update_preview", "render"):
            if getattr(type(page), fn, None) not in (None, QWidget.render):    # nicht QWidget.render
                getattr(page, fn)()
        if key == "eps":
            w.render()
        pump(3.0 if key in ("compound", "syn", "dft") else 1.2)   # Zeichner (WebEngine), Orbitale
        ed = getattr(page, "drawing_editor", None)
        if ed is not None:                                # Zeichnung nach dem Auslegen der Seite neu mittig setzen
            ed._unplaced = True                           # (sonst je nach Ladezeit seitlich verschoben)
            ed.place()
            pump(1.0)
        clear_toast(w)                                    # Einblendung („Projekt gespeichert“) nicht im Bild
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
        import json
        w.open_demo_publication(work / "Beispielprojekt")      # Coverbild, Projektseite und alle Tabs (S3)
        w.go_home()
        w.settings.setValue("recent_projects", json.dumps(      # Übersicht: nur das Beispielprojekt
            [str((work / "Beispielprojekt" / n).resolve()) for n in ("S3", "S2")]))
        w.settings.setValue("recent_publications", json.dumps([str((work / "Beispielprojekt").resolve())]))
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
