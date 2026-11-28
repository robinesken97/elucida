"""elucida/selftest_smoke.py - Rauchtest (Selbsttest-Gruppe „smoke“): was nur eine GEBAUTE App kaputt machen kann.

Läuft in der gebauten App und im AppImage allein (`--selftest-group smoke`), im vollen Selbsttest als erste Gruppe.
Eigenes Fenster, eigene Einstellungsdatei und eigener Unterordner `smoke/`: die übrigen Abschnitte sehen davon nichts.
Prüft: jedes `--hidden-import`/`--collect-all` aus `tools/build.py` (Liste wird dort gelesen, die gebaute App trägt die
Datei mit), Repo-Dateien über `elucida.ROOT` (Symbole, Lizenzen, Octet, Mnova-Skript, Handbuch-Verweise), Bibliotheken
(rdkit, pymupdf, onnxruntime/ISNet, pillow-heif, openpyxl, OpenCV, RapidOCR-Modelle), Start, Beispielprojekt mit jedem Tab gebaut und
gezeichnet, Octet-Zeichner (WebEngine), ein Export, eine Word-SI und eine PPTX-Datei.
"""
from __future__ import annotations

import importlib
import re
import sys
import time
import zipfile
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from elucida import ROOT


def build_imports(text: str, platform: str = sys.platform) -> list[str]:
    """Module aus tools/build.py: --hidden-import und --collect-all (macOS-Zusätze nur unter darwin)."""
    mods, only = [], None                                 # only: Plattform eines `if sys.platform == …:`-Blocks
    for line in text.splitlines():
        ind = len(line) - len(line.lstrip())
        m = re.match(r'\s*if sys\.platform == "(\w+)":', line)
        if m:
            only = (m.group(1), ind)
            continue
        if only and line.strip() and ind <= only[1]:
            only = None
        if only and only[0] != platform:
            continue
        mods += re.findall(r'"--(?:hidden-import|collect-all)",\s*"([^"]+)"', line)
    return list(dict.fromkeys(mods))


def _pump(sec=0.3):
    t0 = time.time()
    while time.time() - t0 < sec:
        QApplication.processEvents()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        time.sleep(0.01)


def run(section, report, out: Path, with_isnet: bool):
    """Abschnitte des Rauchtests (je `with section:`, Titel „smoke: …: OK“)."""
    from elucida.app import main_window as MW
    from elucida.app.i18n import get_lang
    from elucida.selftest import make_selftest_inputs
    sm = out / "smoke"
    keep = (MW.SETTINGS_FILE, get_lang())
    MW.SETTINGS_FILE = sm / "smoke_settings.ini"         # eigene Einstellungen: die übrigen Abschnitte sehen nichts davon
    sm.mkdir(parents=True, exist_ok=True)
    MW.SETTINGS_FILE.unlink(missing_ok=True)
    ws = None
    try:
        with section:   # smoke: hidden imports and own modules
            src = ROOT / "tools" / "build.py"
            assert src.is_file(), f"tools/build.py fehlt unter ROOT ({ROOT})"
            mods = build_imports(src.read_text(encoding="utf-8"))
            assert len(mods) >= 15 and "PySide6.QtWebEngineWidgets" in mods and "rdkit" in mods, mods
            bad = []
            for m in mods:
                try:
                    importlib.import_module(m)
                except Exception as e:                       # ImportError, aber auch Fehler beim Laden nativer Teile
                    bad.append(f"{m}: {type(e).__name__}: {e}")
            subs = []                                        # --collect-submodules: jedes eigene Modul
            for pkg in re.findall(r'"--collect-submodules",\s*"([^"]+)"', src.read_text(encoding="utf-8")):
                import pkgutil
                base = importlib.import_module(pkg)
                subs += [m.name for m in pkgutil.walk_packages(base.__path__, pkg + ".")
                         if not m.name.endswith(".__main__")]          # startet die App
            assert len(subs) > 50, f"nur {len(subs)} eigene Module gefunden"
            for m in subs:
                try:
                    importlib.import_module(m)
                except Exception as e:
                    bad.append(f"{m}: {type(e).__name__}: {e}")
            assert not bad, bad
            report.append(f"smoke: {len(mods)} hidden imports / collected packages and {len(subs)} own modules from "
                          f"tools/build.py import: OK")
        with section:   # smoke: repo files via elucida.ROOT
            from elucida.app.main_window import resource_path
            from elucida.tabs import base as TABS
            assert resource_path("assets") == ROOT / "assets", (resource_path("assets"), ROOT)
            need = ["assets/icon-light.svg", "assets/icon-dark.svg", "assets/icon.png", "assets/icon.ico",
                    "assets/octet/embedded.html", "assets/octet/bridge.js", "assets/octet/LICENSE",
                    "assets/octet/THIRD_PARTY.md", "assets/mnova/elucida_export.qs", "assets/shaders/orb.vert.qsb",
                    "assets/shaders/orb1.frag.qsb", "assets/shaders/orb2.frag.qsb"]
            missing = [n for n in need if not (ROOT / n).is_file() or (ROOT / n).stat().st_size == 0]
            assert not missing, missing
            pngs = list((ROOT / "assets" / "png").glob("*.png"))
            lic = list((ROOT / "assets" / "licenses").glob("*.txt"))
            octl = [p for p in (ROOT / "assets" / "octet" / "licenses").rglob("*") if p.is_file()]
            assert pngs and lic and octl, (len(pngs), len(lic), len(octl))
            assert all(p.stat().st_size > 0 for p in pngs + lic), "leere Datei in assets"
            assert list((ROOT / "assets" / "octet" / "assets").glob("*.js")), "Octet-Skripte fehlen"
            from PySide6.QtGui import QShader                # 3D-Shader der GPU-Vorschau (gpu3d) lesbar
            for n in ("orb.vert.qsb", "orb1.frag.qsb", "orb2.frag.qsb"):
                assert QShader.fromSerialized((ROOT / "assets" / "shaders" / n).read_bytes()).isValid(), n
            for lang in ("de", "en"):                        # Handbuch: Verweise auf die Online-Fassung
                assert TABS.MANUAL[lang].startswith("docs/manual.") and TABS.README_URL.startswith("https://")
            report.append(f"smoke: repo files via elucida.ROOT ({len(pngs)} icons, {len(lic)} licence texts, Octet, "
                          f"Mnova script, 3D shaders, manual links): OK")
        with section:   # smoke: text recognition (RapidOCR models in the package)
            from elucida.core import ocr as OCR
            frozen = bool(getattr(sys, "frozen", False))
            if not OCR.available() and not frozen:           # aus dem Quelltext ohne rapidocr: nur dann überspringen
                report.append("smoke: text recognition SKIPPED: package rapidocr not installed (source run)")
            else:
                assert OCR.available(), "rapidocr fehlt in der gebauten App (tools/build.py)"
                import matplotlib
                from PIL import Image, ImageDraw, ImageFont
                font = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"), 28)
                img = Image.new("RGB", (420, 70), "white")
                ImageDraw.Draw(img).text((16, 16), "found 176.0710", fill="black", font=font)
                img.save(sm / "ocr_smoke.png")
                t0 = time.time()
                res = OCR.run(sm / "ocr_smoke.png")            # Modelle fehlen -> {"error": ...}
                assert "items" in res, res
                nums = [it["number"] for it in res["items"] if it["number"] is not None]
                assert 176.071 in nums, [it["word"] for it in res["items"]]
                report.append(f"smoke: text recognition (RapidOCR models found, 176.0710 read in "
                              f"{time.time() - t0:.1f} s): OK")
        with section:   # smoke: start, UV-Vis project
            csv, cdxml, photo = make_selftest_inputs(sm / "input")
            ws = MW.MainWindow()
            ws._allow_download = with_isnet
            assert ws.center.currentIndex() == 0, "Start: Startbildschirm"
            assert ws.create_project(sm / "projekt")
            ws.open_csv(csv)
            assert set(ws.groups) == {"TEST-A", "TEST-B"}, ws.groups
            ws.set_structure(str(cdxml), "TEST-A", render=False, sync=True)          # rdkit
            st = ws.series["TEST-A"]
            assert st["mw"] and abs(st["mw"] - 95.10) < 0.05, st["mw"]
            st["bg"] = "isnet" if with_isnet else "grabcut"
            try:                                                # Fehlerbild: OpenCV-Stand der gebauten App
                import cv2
                cv = f"cv2 {cv2.__version__}"
            except Exception as ex:                             # noqa: BLE001 – nur für die Meldung
                cv = f"import cv2 failed: {type(ex).__name__}: {ex}"
            from elucida.core import images as IMG
            bg_log, log0 = [], IMG.LOG                          # Grund einer gescheiterten Freistellung (sonst nur im
            IMG.LOG = lambda m="": (bg_log.append(str(m)), log0(m))   # Protokoll der Sitzung, nicht im Bericht)
            try:
                ws.set_photo(str(photo), "TEST-A", render=False, sync=True)            # pillow-heif, onnxruntime/OpenCV
            finally:
                IMG.LOG = log0
            bgm = st["photo_asset"]["bg_method"]
            assert bgm == ("isnet" if with_isnet else "grabcut"), (bgm, cv, [m.strip() for m in bg_log if m.strip()])
            ws.render()
            files = ws.export_all(sm)
            assert files and all(f.exists() and f.stat().st_size > 200 for f in files), files
            import pymupdf
            pdf = next(f for f in files if f.suffix == ".pdf")
            page = pymupdf.open(str(pdf))[0]
            assert page.get_drawings() and page.get_images(), "PDF ohne Pfade/Foto"
            assert page.get_pixmap(dpi=50).width > 50                                  # MuPDF rendert
            xlsx = [f for f in files if f.suffix == ".xlsx"]
            if xlsx:
                import openpyxl
                assert openpyxl.load_workbook(xlsx[0]).sheetnames
            report.append(f"smoke: start, UV-Vis project (rdkit, HEIC photo, background {bgm} with {cv}, PDF/SVG/PNG "
                          f"export, MuPDF): OK")
        with section:   # smoke: example project, all tabs
            assert ws is not None, "kein Fenster (voriger Abschnitt)"
            demo_log = []                                       # Grund im Bericht (Fehler, Rückfrage zum Speichern)

            def demo_line(m):
                demo_log.append(str(m))
            ws.log_signal.connect(demo_line)
            try:
                d = ws.open_demo_publication(sm / "demo")
                assert d, ("open_demo_publication", ws.statusBar().currentMessage(), demo_log[-6:])
                assert ws.open_project(Path(d) / "S3", ask=False, recent=False), ("open_project S3", demo_log[-6:])
            finally:
                ws.log_signal.disconnect(demo_line)
            _pump(0.5)
            drawn = []
            for key in ws._TAB_ORDER:
                ws.show_tab(key)
                _pump(0.2)
                if key == "eps":
                    ws.render()
                    drawn.append(key)
                    continue
                tab = getattr(ws, ws._tab_spec(key)[0])
                if hasattr(tab, "ensure_rendered"):
                    tab.ensure_rendered()
                    if getattr(tab, "F", None) is not None:
                        drawn.append(key)
            tabs = [k for k in ws._TAB_ORDER if k != "eps"]         # ε ist das Hauptfenster selbst
            assert tabs and all(ws._built(k) for k in tabs), [k for k in tabs if not ws._built(k)]
            assert len(drawn) >= 10, drawn
            report.append(f"smoke: example project, all {len(ws._TAB_ORDER)} tabs built, {len(drawn)} figures drawn: OK")
        with section:   # smoke: Octet drawing editor (WebEngine)
            ws.show_tab("compound")
            ed = getattr(ws.comp_tab, "drawing_editor", None)
            assert ed is not None, "kein Zeichner im Tab Verbindung"
            ed.wait_ready(90)
            assert ed.ready, "Octet (WebEngine) nicht bereit"
            report.append("smoke: Octet drawing editor (WebEngine) loads: OK")
        with section:   # smoke: one export, Word SI, PPTX
            ws.show_tab("cv")
            _pump(0.3)
            before = set((Path(ws.project_dir) / "figures").glob("*")) if (Path(ws.project_dir) / "figures").exists() else set()
            ws.export_key("cv")
            _pump(0.3)
            new = set((Path(ws.project_dir) / "figures").glob("*")) - before
            assert any(p.suffix == ".pdf" for p in new) and any(p.suffix == ".svg" for p in new), sorted(new)
            ws.export_si()
            si = list((Path(ws.project_dir) / "SI").glob("*_SI.docx"))
            assert si, "keine Word-SI"
            with zipfile.ZipFile(si[0]) as z:
                assert "word/document.xml" in z.namelist() and len(z.read("word/document.xml")) > 1000
            from elucida.si import pptx as PPTX
            png = next(p for p in new if p.suffix == ".png")
            svg = next(p for p in new if p.suffix == ".svg")
            pp = PPTX.write_pptx(sm / "smoke.pptx", [(str(png), 16.0, 11.0, str(svg), "Smoke <b>1</b>.")])
            with zipfile.ZipFile(pp) as z:
                assert any(n.startswith("ppt/slides/slide") for n in z.namelist()), z.namelist()
            report.append("smoke: one export (CV: PDF/SVG/PNG), one Word SI, one PPTX: OK")
    finally:
        if ws is not None:
            try:
                ws.close()
                import shiboken6
                if "elucida.app.drawing_editor" in sys.modules:
                    sys.modules["elucida.app.drawing_editor"].release_pages(QApplication.instance())
                shiboken6.delete(ws)
            except Exception:
                pass
            _pump(0.3)
        MW.SETTINGS_FILE = keep[0]
        from elucida.app import i18n as I18N
        if I18N.get_lang() != keep[1]:
            I18N.set_lang(keep[1])
