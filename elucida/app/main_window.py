"""
elucida/app/main_window.py - Grafische Oberfläche der UV-Vis-Auswertung (Windows / macOS / Linux).

Start:      python Elucida.py   (oder python -m elucida)
Selbsttest: python Elucida.py --selftest AUSGABEORDNER [--selftest-isnet]
"""
from __future__ import annotations
import elucida

import json
import os
import shutil
import sys
import html
import re
import traceback
import tempfile
import logging
import locale
from pathlib import Path

from elucida import APP_NAME, APP_VERSION, ROOT  # noqa: F401  (Versionsnummer nur in elucida/__init__.py)
OLD_APP_NAMES = ("Spectravolt", "UVVisTool")   # 1.16–1.25 bzw. bis 1.15: Einstellungen beim ersten Start übernehmen
SI_PARTS = ("char", "nmr", "figs", "methods", "xray", "dft")   # Teile des SI-Exports (Auswahl im Dialog)
WELCOME_FILTERS = ("all", "recent", "incomplete", "sample")   # Verbindungsliste des Startbildschirms (FB-2)
SETTINGS_FILE = None      # Selbsttest: eigene INI-Datei statt der echten Benutzereinstellungen

if "--selftest" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
import yaml  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from elucida.app.canvas_theme import register as register_canvas
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure as MplFigure  # noqa: E402
from PySide6.QtCore import QEvent, QFileSystemWatcher, QSettings, QSize, Qt, QThread, QTimer, Signal  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QIcon, QImage,  # noqa: E402
                           QGuiApplication, QKeySequence, QPixmap, QTextCursor)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox, QComboBox,  # noqa: E402
                               QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFrame, QGroupBox, QHBoxLayout, QInputDialog,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                               QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea, QSizePolicy,
                               QSpinBox, QSplitter, QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem, QTextBrowser,
                               QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget)

from elucida.core import uvvis as core  # noqa: E402
from elucida.core import images as IMG  # noqa: E402
from elucida.app.i18n import T, get_lang, set_lang  # noqa: E402
from elucida.tabs import base as TABS  # noqa: E402
from elucida.app import project as PRJ  # noqa: E402
from elucida.si import excel as REPORT  # noqa: E402
from elucida.app import update as UPD  # noqa: E402
from elucida.core import color as COLOR  # noqa: E402
from elucida.tabs import compound as COMP  # noqa: E402
from elucida.tabs import cv as CVMOD  # noqa: E402
from elucida.tabs import sec as SECMOD  # noqa: E402
from elucida.tabs import hcell as HCELL  # noqa: E402
from elucida.tabs import epr as EPRMOD  # noqa: E402
from elucida.tabs import hrms as HRMS  # noqa: E402
from elucida.tabs import ir_ea as IRMS  # noqa: E402
from elucida.tabs import xray as XRAY  # noqa: E402
from elucida.tabs import dft as DFT  # noqa: E402
from elucida.tabs import other as OTHER  # noqa: E402
from elucida.tabs import nmr as NMR  # noqa: E402
from elucida.tabs import synthesis as SYN  # noqa: E402
from elucida.tabs import uvkin as UVKIN  # noqa: E402
from elucida.si import lines as SI  # noqa: E402
from elucida.app import style as STYLE  # noqa: E402
from elucida.app import macos as MAC  # noqa: E402
from elucida.app.style import HINT_CSS, WARN_CSS, align_forms, compact, make_form  # noqa: E402

PREVIEW_DPI = 90
FIGSIZE = (8.0, 6.0)


def resource_path(rel):
    base = Path(getattr(sys, "_MEIPASS", ROOT))
    return base / rel


def rgba_to_pixmap(arr, max_h=110):
    arr = np.ascontiguousarray(arr)
    h, w = arr.shape[:2]
    img = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(img).scaledToHeight(max_h, Qt.SmoothTransformation)


def parse_float(txt):
    txt = (txt or "").strip().replace(",", ".")
    if not txt:
        return None
    v = float(txt)
    if v <= 0:
        raise ValueError
    return v


class Task(QThread):
    """Funktion im Hintergrund ausführen (Freistellung, CDXML), GUI bleibt bedienbar."""
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class GuiDragger(core.Dragger):
    """Wie core.Dragger, meldet aber jede Änderung (Ziehen von Inset/Bild/Label, Mausrad)
    an die GUI, damit Vorschau, Serienwechsel und Export dasselbe Layout verwenden."""

    def __init__(self, F, on_change):
        self.on_change = on_change
        super().__init__(F, None)

    def _report(self, lay0):
        # erst nach allen anderen Release-Handlern auslesen (Label-Drag von matplotlib)
        QTimer.singleShot(0, lambda: self.on_change(self.moved(lay0)))

    def release(self, ev):
        lay0, self._lay0 = self._lay0, None
        super().release(ev)
        if lay0 is not None:
            self._report(lay0)

    def scroll(self, ev):
        lay0 = self.F.current_layout()
        if super().scroll(ev):
            self._report(lay0)

    def key(self, ev):
        pass


class TrimSpin(QDoubleSpinBox):
    """Zahlenfeld, das nur die nötigen Nachkommastellen zeigt (Nutzerwunsch: „c braucht nicht so viele“); die
    Genauigkeit der Eingabe bleibt (decimals)."""

    def textFromValue(self, value):
        return f"{value:.{self.decimals()}f}".rstrip("0").rstrip(".")


DEFAULT_GLOB = {"path_length": 1.0, "cutoff": 1.0, "min_points": 3, "bands": "",
                "baseline": "series", "bl_a": 1050.0, "bl_b": 1100.0, "ymax": 1.0,
                "r2": "legend", "show_err": False, "table": True,
                "size": "half_a4", "w_cm": 16.0, "h_cm": 11.0,
                "fmt_pdf": True, "fmt_svg": True, "fmt_png": True,
                "x_auto": True, "x_min": 200.0, "x_max": 1100.0,
                "bands_add": True, "shoulders": False, "show_excl": False, "inset": True,
                "mark_sh": False, "label_index": False, "conc_colors": False, "conc_legend": False, "min_r2": 0.98, "r2_digits": 2,
                "color_show": False, "color_d": 1.0}

UNITS = [("mM", "mM"), ("uM", "µM"), ("mg/mL", "mg mL⁻¹"), ("M", "M")]     # (Schlüssel, Anzeige)

def migrate_settings(old, new):
    """Einstellungen des alten Programmnamens (zuletzt geöffnet, Sprache, Theme …) einmalig übernehmen,
    solange unter dem neuen Namen noch nichts gespeichert ist. Das Alte bleibt (Rückkehr zur alten Version)."""
    if new.allKeys() or not old.allKeys():
        return False
    for k in old.allKeys():
        new.setValue(k, old.value(k))
    new.sync()
    return True


class Section(QWidget):
    """Aufklappbarer Bereich für seltener gebrauchte Optionen. Weicht ein Wert vom Standard ab, steht
    „(geändert)“ im Titel – eingeklappte Einstellungen wirken sich sonst unbemerkt aus."""

    def __init__(self, title, key, settings):
        super().__init__()
        self.title, self.key, self.settings = title, key, settings
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.btn = QToolButton(checkable=True, autoRaise=True)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn.setStyleSheet("QToolButton { border: none; padding: 2px 0; }")
        self.btn.setFont(QApplication.font())         # macOS: Werkzeugknöpfe sonst mit kleinerer Schrift
        self.body = QWidget()
        self.form = make_form(self.body)
        self.form.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.btn)
        lay.addWidget(self.body)
        self.btn.toggled.connect(self._toggled)
        self.btn.setChecked(settings.value(f"ui/section_{key}", False, type=bool))
        self._toggled(self.btn.isChecked())
        self.set_changed(False)

    def _toggled(self, on):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)
        self.settings.setValue(f"ui/section_{self.key}", on)

    def set_changed(self, changed):
        self.changed = changed
        self.btn.setText(f"{self.title} ({T('adv_changed')})" if changed else self.title)
        f = self.btn.font()
        f.setBold(changed)
        self.btn.setFont(f)


def compound_from_structure(p):
    """Formel und Molmasse aus einer CDXML (oder der gleichnamigen CDXML neben SVG/PDF/PNG)."""
    p = Path(p)
    src = p if p.suffix.lower() == ".cdxml" else p.with_suffix(".cdxml")
    if not src.exists() or not PRJ.cdxml_has_content(src):
        return {}
    try:
        from elucida.core import chem as CHEM
        c = CHEM.load_cdxml(src, render=False)
        # Molmasse überall mit 2 Nachkommastellen (Nutzerwunsch; nur die exakte Masse der HRMS hat mehr): gerundet
        # speichern, damit Rechnung, Feld, Methodentext und Excel dieselbe Zahl benutzen
        return {"formula": c.get("formula"), "mw": round(c["mw"], 2) if c.get("mw") else None}
    except Exception:
        logging.getLogger('elucida.drawing').exception('Could not calculate compound properties from CDXML')
        return {}


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        # QApplication adopts the system's numeric locale. Native CDXML readers
        # expect decimal points; a German comma locale collapses RDKit coordinates
        # and makes its preview fail. Set this once before loading data/workers;
        # localized Qt widgets and Elucida's comma-aware input remain unchanged.
        # https://doc.qt.io/qt-6/qcoreapplication.html#locale-settings
        locale.setlocale(locale.LC_NUMERIC, 'C')
        super().__init__()
        self.settings = (QSettings(str(SETTINGS_FILE), QSettings.IniFormat) if SETTINGS_FILE
                         else QSettings(APP_NAME, APP_NAME))
        if not SETTINGS_FILE:
            for old in OLD_APP_NAMES:
                if migrate_settings(QSettings(old, old), self.settings):
                    break
        set_lang(self.settings.value("lang", "de"))
        SI.set_font(self.settings.value("si_font", "Arial"))
        self.csv_path = None
        self.groups, self.units = {}, {}
        self.samples, self.conc, self.csv_paths = [], {}, []          # Rohproben und Konzentrations-Overrides
        self._eps_held = {}            # beim Öffnen fehlende Dateien/Serien: unverändert weiter speichern
        self.series = {}               # je Serie: mw, structure, photo, bg, layout, assets
        self.current = None
        self.F = None
        self.dragger = None
        self.hover = None
        self._tasks = []
        self._loading = False
        self.glob = dict(DEFAULT_GLOB)
        self.extra_cache = {}
        self.ov_state, self.fl_state, self.cv_state, self.sec_state, self.epr_state = {}, {}, {}, {}, {}
        self.hcell_state = {}  # leer
        self.irms_state = {}
        self.uvkin_state = {}
        self.hrms_state = {}
        self.xray_state = {}
        self.dft_state = {}
        self.other_state = {}
        self.nmr_state = {}
        self.syn_state = {}
        self.compound = {}                  # Verbindung des Projekts: name, structure, formula, mw
        self.text_fmt = dict(core.TEXT_DEFAULTS)
        self.tab_fmt = {}                                # eigenes Textformat je Tab (Schlüssel = STATE_KEY / epsilon)
        self._tab_key = "syn"                            # offener Tab (Name, nicht Position)
        self.project_dir = None
        self.publication_dir = None                      # Publikation (übergeordneter Ordner), falls bekannt
        self._undo, self._redo = [], []
        self._restoring = False
        self._saved_snap = None

        self.fig = MplFigure(figsize=FIGSIZE, dpi=PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.canvas.setFixedSize(int(FIGSIZE[0] * PREVIEW_DPI), int(FIGSIZE[1] * PREVIEW_DPI))
        self.timer = QTimer(self, singleShot=True, interval=400)
        self.timer.timeout.connect(self.render)
        self.autosave_timer = QTimer(self, singleShot=True, interval=800)
        self.autosave_timer.timeout.connect(self.autosave)
        # ChemDraw: Struktur/Schema der Verbindung überwachen; gespeichert -> automatisch übernehmen
        self.cd_watch = QFileSystemWatcher(self)
        self.cd_watch.fileChanged.connect(self._cd_changed)
        self._cd_kinds = {}                              # Pfad -> "structure" | "scheme"
        self._cd_pending = set()
        self._drawn, self._taken = {}, None              # je Strukturdatei: Formel/Molmasse der Zeichnung; zuletzt übernommen
        self.cd_timer = QTimer(self, singleShot=True, interval=800)   # ChemDraw schreibt in mehreren Schritten
        self.cd_timer.timeout.connect(self._cd_apply_pending)

        # Meldungen als Einblendung unten über dem Fenster statt Statusleiste: die Leiste bliebe nach der ersten
        # Meldung als leerer Streifen unter den Fußleisten stehen (Knöpfe nicht mittig), Ein-/Ausblenden ließe die
        # Abbildung bei jedem Autosave springen
        self._status = QStatusBar()                      # nur Nachrichtenträger (showMessage mit Zeitlimit), unsichtbar
        self._toast = QLabel(self, objectName="toast", alignment=Qt.AlignCenter)
        self._toast.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._toast.hide()
        self._status.messageChanged.connect(self._place_toast)
        self.log_signal.connect(self._append_log)
        core.LOG = IMG.LOG = lambda m="": self.log_signal.emit(str(m))
        self.apply_theme()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
        self._mac_title = MAC.enabled()
        MAC.prepare(self)                                # macOS: keine Titelleiste, Ampelknöpfe auf der Werkzeugleiste
        self._title_h = None                             # Höhe der Titelleiste (px) nach dem ersten Anzeigen
        self.windowTitleChanged.connect(lambda _: QTimer.singleShot(0, self._hide_native_title))
        self.build_ui()
        self.setAcceptDrops(True)
        QTimer.singleShot(0, self._init_undo)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QTimer.singleShot(3000, lambda: self.check_updates(manual=False))
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1320, 900)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        if not self.save_drawings():
            return
        old_pub = self.__dict__.get('pub_page')
        old_path = old_pub.path_workspace.item.copy() if old_pub and old_pub.path_workspace else None
        old_pub_tab = old_pub.project_tabs.currentIndex() if old_pub else 0
        old_pdir = old_pub.pdir if old_pub else None
        if old_pub and not old_pub.close_path(): return
        self.update_title()
        mb = self.menuBar()
        mb.clear()
        m = mb.addMenu(T("menu_file"))
        act_new = QAction(STYLE.icon("new"), T("act_new_project"), self, shortcut=QKeySequence.New,
                          triggered=self.new_project)
        act_open_prj = QAction(STYLE.icon("open"), T("act_open_project"), self, shortcut=QKeySequence.Open,
                               triggered=self.open_project_dialog)
        act_save = QAction(STYLE.icon("save"), T("act_save_project"), self, shortcut=QKeySequence.Save,
                           triggered=self.save_project)
        m.addAction(act_new)
        m.addAction(act_open_prj)
        m.addAction(QAction(T("act_new_publication"), self, triggered=self.new_publication))
        self.act_to_pub = QAction(T("act_to_publication"), self, shortcut=QKeySequence("Ctrl+Shift+P"),
                                  triggered=self.go_publication)
        self.act_home = QAction(T("act_to_overview"), self, shortcut=QKeySequence("Ctrl+Shift+H"),
                                triggered=self.go_home)
        self.act_home.setEnabled(bool(self.project_dir or self.publication_dir))
        m.addAction(self.act_home)
        self.act_to_pub.setEnabled(bool(self.publication_dir and self.project_dir))
        m.addAction(self.act_to_pub)
        self.recent_menu = m.addMenu(T("act_recent"))
        self.fill_recent_menu()
        m.addAction(act_save)
        m.addAction(QAction(T("act_save_copy"), self, shortcut=QKeySequence("Ctrl+Shift+S"),
                            triggered=self.save_project_copy))
        self.act_folder = QAction(STYLE.icon("reveal"), T("act_show_folder"), self, triggered=self.show_project_folder)
        self.act_folder.setEnabled(bool(self.project_dir))
        m.addAction(self.act_folder)
        m.addSeparator()
        # nur für den Tab UV-Vis (ε): eigenes Untermenü, damit klar ist, wofür die Befehle gelten
        m_eps = m.addMenu(T("menu_eps"))
        m_eps.addAction(QAction(T("act_open"), self, shortcut=QKeySequence("Ctrl+Shift+O"), triggered=self.choose_csv))
        m_eps.addAction(QAction(T("act_conc"), self, triggered=self.edit_concentrations))
        m_eps.addAction(QAction(T("act_restart"), self, triggered=self.restart_file))
        m.addSeparator()
        act_export = QAction(STYLE.icon("export"), T("act_export"), self, shortcut="Ctrl+E",
                             triggered=self.export_current)
        m.addAction(act_export)
        m.addAction(QAction(T("act_export_si"), self, triggered=self.export_si_dialog))
        m.addAction(QAction(T("act_datapack"), self, triggered=self.export_datapack))
        m.addSeparator()
        m.addAction(QAction(T("act_quit"), self, shortcut=QKeySequence.Quit, triggered=self.close))
        me = mb.addMenu(T("menu_edit"))
        me.addAction(QAction(T("act_search"), self, shortcut=QKeySequence.Find, triggered=self.focus_search))
        self.act_undo = QAction(STYLE.icon("undo"), T("act_undo"), self, triggered=self.undo)
        self.act_undo.setShortcuts([QKeySequence.Undo])
        self.act_redo = QAction(STYLE.icon("redo"), T("act_redo"), self, triggered=self.redo)
        self.act_redo.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Shift+Z")])
        me.addAction(self.act_undo)
        me.addAction(self.act_redo)
        self._update_undo_actions()
        # Werkzeugleiste: Projekt, Rückgängig/Wiederholen (dieselben Aktionen wie im Menü; Exportieren steht
        # in jedem Tab unten fest sichtbar)
        if getattr(self, "toolbar", None):
            self.toolbar.setParent(None)                # sofort lösen, gelöscht wird später
            self.toolbar.deleteLater()
        self.toolbar = QToolBar(T("toolbar"))           # im Layout neben der Seitenleiste (die reicht bis zum Fensterrand)
        self.toolbar.setObjectName("mainToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        if self._mac_title:                              # Platz für die Ampelknöpfe, freie Stellen ziehen das Fenster
            inset = QWidget(objectName="titleInset")
            inset.setFixedWidth(MAC.INSET)
            self._title_inset = self.toolbar.addWidget(inset)      # QAction: sie steuert die Sichtbarkeit
            self.toolbar.installEventFilter(MAC.TitleDrag(self))
            self._fit_title_bar()
        # Eine Leiste für alles: Übersicht/Projekt = Suche, Ansicht, Öffnen, Neu (welcome_page); Verbindung/Pfad = Pfadleiste
        # (nav_bar) links, Bearbeiten rechts. Sichtbarkeit: _update_crumbs
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._tb_left = self.toolbar.addWidget(spacer)
        self._tb_edit = []
        for act in (self.act_undo, self.act_redo, self.act_folder):
            keys = act.shortcut().toString(QKeySequence.NativeText)
            act.setToolTip(f"{act.text().rstrip('…')} ({keys})" if keys else act.text())
            tb = QToolButton(iconSize=QSize(18, 18))        # eigene Knöpfe: ausgeblendet bleibt das Tastenkürzel im Menü aktiv
            tb.setDefaultAction(act)
            self._tb_edit.append(self.toolbar.addWidget(tb))
        # Erscheinungsbild umschalten (Nutzerwunsch): Symbol = aktueller Zustand (Mond dunkel, Sonne hell)
        dark = STYLE._mode == "dark"
        self.act_theme = QAction(STYLE.icon("moon" if dark else "sun"), T("theme_now_dark" if dark else "theme_now_light"),
                                 self, triggered=lambda: self.switch_theme("light" if STYLE._mode == "dark" else "dark"))
        tb = QToolButton(iconSize=QSize(18, 18))
        tb.setDefaultAction(self.act_theme)
        self._tb_theme = self.toolbar.addWidget(tb)     # auch bei offenem Reaktionspfad sichtbar (_update_crumbs)
        # Name des Dateimanagers je System (Finder, Explorer, sonst Standard-Dateimanager, z. B. Dolphin/Nautilus)
        fm = {"darwin": "fm_finder", "win32": "fm_explorer"}.get(sys.platform, "fm_linux")
        self.act_folder.setToolTip(T("act_show_folder_tip", fm=T(fm)))
        self._sep_compound = self.toolbar.addSeparator()   # Name und Summenformel stehen am Tab „Verbindung“ (NameTab)
        self.act_si = QAction(STYLE.icon("export"), T("act_si_short"), self, triggered=self.export_si_dialog)
        self.act_si.setToolTip(T("act_si_tip"))
        self.toolbar.addAction(self.act_si)
        self.toolbar.widgetForAction(self.act_si).setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.widgetForAction(self.act_si).setObjectName("barTool")
        mf = mb.addMenu(T("menu_format"))
        mf.addAction(QAction(T("act_text_format"), self, triggered=self.edit_text_format))
        mt = mf.addMenu(T("menu_theme"))
        grp_t = QActionGroup(self)
        for code in ("system", "light", "dark"):
            act = QAction(T(f"theme_{code}"), self, checkable=True, checked=self._theme_mode() == code)
            act.triggered.connect(lambda _=False, c=code: self.switch_theme(c))
            grp_t.addAction(act)
            mt.addAction(act)
        if elucida.octet_enabled():
            canvas = mf.addMenu(T("draw_canvas"))
            group = QActionGroup(self)
            self.canvas_mode_actions = {}
            for code in ("system", "light", "dark"):
                a = QAction(T("draw_follow_theme") if code == "system" else T("theme_" + code), self,
                            checkable=True, checked=self.settings.value("ui/canvas", "system") == code)
                a.triggered.connect(lambda checked=False, c=code: self.set_canvas_mode(c))
                group.addAction(a)
                canvas.addAction(a)
                self.canvas_mode_actions[code] = a
            self.canvas_toggle = QAction(self, triggered=lambda: self.set_canvas_mode(
                "light" if self.canvas_is_dark() else "dark"))
            self.toolbar.insertAction(self.act_si, self.canvas_toggle)
            self.toolbar.widgetForAction(self.canvas_toggle).setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            self._sync_canvas_toggle()
        ml = mb.addMenu(T("menu_lang"))
        grp = QActionGroup(self)
        for code, name in (("de", "Deutsch"), ("en", "English")):
            act = QAction(name, self, checkable=True, checked=get_lang() == code)
            act.triggered.connect(lambda _=False, c=code: self.switch_lang(c))
            grp.addAction(act)
            ml.addAction(act)
        mh = mb.addMenu(T("menu_help"))
        mh.addAction(QAction(T("act_guide_tab"), self, shortcut=QKeySequence.HelpContents, triggered=self.show_tab_guide))
        mh.addAction(QAction(T("act_quickstart"), self, triggered=self.show_quickstart))
        mh.addAction(QAction(T("act_shortcuts"), self, triggered=self.show_shortcuts))
        mh.addAction(QAction(T("act_demo"), self, triggered=self.open_demo))
        mh.addAction(QAction(T("act_demo_pub"), self, triggered=self.open_demo_publication))
        mh.addSeparator()
        mh.addAction(QAction(T("act_log"), self, triggered=self.show_log))
        mh.addSeparator()
        mh.addAction(QAction(T("act_check_updates"), self, triggered=lambda: self.check_updates(manual=True)))
        act = QAction(T("act_auto_updates"), self, checkable=True, checked=self._auto_updates())
        act.toggled.connect(lambda on: self.settings.setValue("update_auto", on))
        mh.addAction(act)
        mh.addSeparator()
        mh.addAction(QAction(T("act_about"), self, triggered=lambda: QMessageBox.about(
            self, T("act_about"), T("about", v=APP_VERSION))))

        # ---- linke Spalte
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(STYLE.COL_PAD, STYLE.COL_PAD, 0, STYLE.COL_PAD)   # wie STYLE.tidy in den übrigen Tabs
        lv.setSpacing(10)

        forms = []
        g, body = STYLE.card(T("grp_data"))
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        row = QHBoxLayout()
        self.btn_open = QPushButton(STYLE.icon("open"), T("act_open"))
        self.btn_open.clicked.connect(self.choose_csv)
        self.btn_open.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)      # natürliche Breite
        row.addWidget(self.btn_open)
        self.lbl_file = QLabel(self.files_label() if self.csv_path else T("no_file"))
        self.lbl_file.setWordWrap(True)
        row.addWidget(self.lbl_file, 1)
        f.addRow(row)
        self.cmb_series = QComboBox()
        self.cmb_series.addItems(list(self.groups))
        if self.current:
            self.cmb_series.setCurrentText(self.current)
        self.cmb_series.currentTextChanged.connect(self.series_changed)
        f.addRow(T("series"), self.cmb_series)
        self.lst_conc = STYLE.check_table((T("conc_col"), T("conc_col_unit"), T("conc_col_color")))
        self.lst_conc.setToolTip(T("conc_list_tip"))
        self.lst_conc.itemChanged.connect(self.conc_toggled)
        f.addRow(T("conc_list"), self.lst_conc)
        self.btn_conc_colors = QPushButton(T("conc_colors_reset"), objectName="ghost")   # nur mit eigenen Farben
        self.btn_conc_colors.clicked.connect(self.conc_colors_reset)
        f.addRow("", self.btn_conc_colors)
        # Konzentrationen eintragen (bis 2.7.1 ein Dialog; Nutzerwunsch: keine Popups): gilt sofort, sobald eine
        # Einheit gewählt ist. Klappt von selbst auf, wenn die Probennamen keine Konzentration nennen.
        self.sec_conc = Section(T("conc_title"), "conc", self.settings)
        fc = self.sec_conc.form
        forms.append(fc)
        self.lbl_conc_intro = STYLE.HintLabel("")
        self.lbl_conc_intro.setWordWrap(True)
        fc.addRow(self.lbl_conc_intro)
        self.cmb_unit = QComboBox()
        self.cmb_unit.addItem(T("unit_choose"), None)       # keine stille Vorbelegung (führte früher zu falschem ε)
        for key, label in UNITS:
            self.cmb_unit.addItem(label, key)
        self.cmb_unit.currentIndexChanged.connect(self.conc_apply)
        fc.addRow(T("unit"), self.cmb_unit)
        self.tbl_conc = QTableWidget(0, 3)
        self.tbl_conc.setHorizontalHeaderLabels([T("col_sample"), T("col_series"), T("col_conc")])
        self.tbl_conc.verticalHeader().setVisible(False)
        self.tbl_conc.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_conc.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_conc.itemChanged.connect(self.conc_apply)
        fc.addRow(self.tbl_conc)
        self.sp_dil_start = QDoubleSpinBox(decimals=4, minimum=0.0, maximum=1e6, value=0.0)
        fc.addRow(T("dil_start"), self.sp_dil_start)
        self.sp_dil_fac = QDoubleSpinBox(decimals=3, minimum=1.0, maximum=1000, value=2.0)
        fc.addRow(T("dil_factor"), self.sp_dil_fac)
        b = QPushButton(T("dil_fill"))
        b.setToolTip(T("dil_hint"))
        b.clicked.connect(self.conc_fill_dilution)
        fc.addRow(b)
        self.lbl_conc_warn = STYLE.HintLabel("")
        self.lbl_conc_warn.setStyleSheet(WARN_CSS)
        fc.addRow(self.lbl_conc_warn)
        f.addRow(self.sec_conc)
        lv.addWidget(g)

        g, body = STYLE.card(T("grp_compound"))
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        # Summenformel und Molmasse stehen hier nur noch als Angabe: sie kommen aus der Verbindung (Nutzerwunsch
        # 2026-11-10: im Tab nichts mehr eingeben). ed_mw/lbl_struct bleiben verborgen als Träger der Werte der Serie.
        self.ed_mw = QLineEdit(body)
        self.ed_mw.editingFinished.connect(self.mw_edited)
        self.ed_mw.hide()
        self.lbl_struct = QLabel("–", body)
        self.lbl_struct.hide()
        self.lbl_formula = QLabel("–", objectName="valueStrong")
        f.addRow(T("compound_formula"), self.lbl_formula)
        row = QHBoxLayout()
        self.lbl_mw = QLabel("–", objectName="valueStrong")
        b1 = QPushButton(T("compound_edit"))
        b1.setProperty("chooselike", True)                  # Breite und Kante wie „Wählen …“ + Papierkorb darunter
        b1.setToolTip(T("compound_tip"))
        b1.clicked.connect(self.edit_compound)
        row.addWidget(self.lbl_mw, 1)
        row.addWidget(b1)
        f.addRow(T("molar_mass_short"), row)
        self.lbl_chem = STYLE.HintLabel("")
        self.lbl_chem.setWordWrap(True)
        f.addRow(self.lbl_chem)
        self.cb_structure = QCheckBox(T("ir_struct"))       # Struktur der Verbindung im Bild (je Serie abwählbar)
        self.cb_structure.toggled.connect(self.structure_toggled)
        f.addRow("", self.cb_structure)
        row = QHBoxLayout()
        self.lbl_photo = QLabel("–")
        b1 = QPushButton(T("choose"))
        b1.clicked.connect(self.choose_photo)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(lambda: self.set_photo(None))
        row.addWidget(self.lbl_photo, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        f.addRow(T("photo"), row)
        self.sec_images = Section(T("adv_images"), "images", self.settings)
        fa = self.sec_images.form
        forms.append(fa)
        self.sp_struct_w = QDoubleSpinBox(decimals=1, minimum=3, maximum=90, singleStep=1, suffix=" %")
        self.sp_struct_w.valueChanged.connect(lambda v: self.image_size_changed("struktur", v))
        fa.addRow(T("img_size_struct"), self.sp_struct_w)
        self.sp_photo_w = QDoubleSpinBox(decimals=1, minimum=2, maximum=60, singleStep=0.5, suffix=" %")
        self.sp_photo_w.valueChanged.connect(lambda v: self.image_size_changed("kuevette", v))
        fa.addRow(T("img_size_photo"), self.sp_photo_w)
        compact(self.sp_struct_w, self.sp_photo_w)
        self.cmb_bg = QComboBox()
        for key in ("auto", "isnet", "grabcut", "border", "none"):
            self.cmb_bg.addItem(T({"auto": "bg_auto", "isnet": "bg_isnet", "grabcut": "bg_grabcut",
                                   "border": "bg_border", "none": "bg_off"}[key]), key)
        self.cmb_bg.currentIndexChanged.connect(self.bg_changed)
        self.cmb_bg.currentIndexChanged.connect(self._update_sections)
        fa.addRow(T("bg_method"), self.cmb_bg)
        f.addRow(self.sec_images)
        # Farbe der Lösung aus dem Spektrum (nur Anzeige, nie in der Abbildung)
        self.cb_color = QCheckBox(T("color_show"))
        self.cb_color.setToolTip(T("color_tip"))
        self.cb_color.toggled.connect(self.color_settings_changed)
        f.addRow(self.cb_color)                             # Chip in der Zeile „Optionen“ (STYLE._chips)
        self.sp_color_c = TrimSpin(decimals=4, minimum=0.0001, maximum=1e6, singleStep=0.1)   # „100 µM“, nicht „100.0000“
        self.sp_color_d = QDoubleSpinBox(decimals=2, minimum=0.01, maximum=100, singleStep=0.1, suffix=" cm")
        self._color_form = f                               # c und d als Felder im Raster (grafische Sichtung 2026-11-11)
        for sp in (self.sp_color_c, self.sp_color_d):       # gehören zum Chip „Farbe in Lösung“: unter der Zeile „Optionen“
            sp.setProperty("below_chips", True)
        f.addRow("c", self.sp_color_c)
        f.addRow("d", self.sp_color_d)
        for sp in (self.sp_color_c, self.sp_color_d):
            sp.valueChanged.connect(self.color_settings_changed)
        self.lbl_color = QLabel()
        self.lbl_color.setFixedHeight(36)
        self.lbl_color_info = STYLE.SciLabel()               # „c = …, d = …“: Größen kursiv bei jedem Text
        self.lbl_color_info.setWordWrap(True)
        self.lbl_color_info.setAlignment(Qt.AlignHCenter)            # mittig unter dem Farbfeld
        self.lbl_color_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.lbl_color)
        f.addRow(self.lbl_color_info)                       # mittig über die ganze Karte
        self._color_spectra = None
        lv.addWidget(g)

        g, body = STYLE.card(T("chain_title"))             # Rechenweg: erste Karte im Schritt Auswertung
        g.setToolTip(T("chain_tip"))
        self.chain_row = STYLE.ChainRow()
        cl_ = QVBoxLayout(body)
        cl_.setContentsMargins(0, 0, 0, 0)
        cl_.addWidget(self.chain_row)
        lv.addWidget(g)
        g, body = STYLE.card(T("grp_eval"))
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        self.sp_d = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=100, singleStep=0.1, suffix=" cm")
        f.addRow(T("path_length_short"), self.sp_d)
        self.ed_solvent = STYLE.ChemEdit()                    # je Serie; für SI-Zeile und Bildunterschrift
        self.ed_solvent.setPlaceholderText(T("si_solvent_ph"))
        self.ed_solvent.editingFinished.connect(self.solvent_changed)
        f.addRow(T("si_solvent"), self.ed_solvent)
        self.sp_cut = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=5, singleStep=0.1)
        self.sp_cut.setToolTip(T("cutoff_tip"))
        f.addRow(T("cutoff"), self.sp_cut)
        self.ed_bands = QLineEdit()
        self.ed_bands.setPlaceholderText(T("wavelengths_ph"))
        f.addRow(T("wavelengths"), self.ed_bands)
        self.cb_bands_add = QCheckBox(T("bands_add"))
        self.cb_bands_add.setProperty("chip_here", True)     # gehört zum Feld „Banden“ darüber
        f.addRow(self.cb_bands_add)
        self.cmb_bl = QComboBox()
        for key in ("series", "simple", "manual", "off"):
            self.cmb_bl.addItem(T({"series": "bl_series", "simple": "bl_simple", "manual": "bl_manual",
                                   "off": "bl_off"}[key]), key)
        self.cmb_bl.setToolTip(T("baseline_tip"))
        f.addRow(T("baseline"), self.cmb_bl)
        row = QHBoxLayout()
        self.sp_bla = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, suffix=" nm")
        self.sp_blb = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, suffix=" nm")
        row.addWidget(self.sp_bla)
        row.addWidget(QLabel("–"))
        row.addWidget(self.sp_blb)
        row.addStretch(1)
        f.addRow("", row)
        self.sec_eval = Section(T("adv_eval"), "eval", self.settings)
        fa = self.sec_eval.form
        forms.append(fa)
        self.sp_min = QSpinBox(minimum=2, maximum=20)
        fa.addRow(T("min_points"), self.sp_min)
        self.sp_r2 = QDoubleSpinBox(decimals=3, minimum=0.0, maximum=1.0, singleStep=0.005)
        self.sp_r2.setToolTip(T("min_r2_tip"))
        fa.addRow(T("min_r2"), self.sp_r2)
        self.sp_r2d = QSpinBox(minimum=1, maximum=6)       # Nutzerwunsch 2026-11-11: wählbar, Standard 2
        self.sp_r2d.setToolTip(T("r2_digits_tip"))
        fa.addRow(T("r2_digits"), self.sp_r2d)
        self.cb_shoulders = QCheckBox(T("find_shoulders"))
        fa.addRow(self.cb_shoulders)
        f.addRow(self.sec_eval)
        compact(self.sp_d, self.sp_cut, self.sp_min, self.sp_r2, self.sp_r2d)
        lv.addWidget(g)

        g, body = STYLE.card(T("grp_plot"))
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        self.sp_ymax = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=10, singleStep=0.1)
        compact(self.sp_ymax)
        f.addRow(T("ymax"), self.sp_ymax)
        row = QHBoxLayout()
        self.cb_xauto = QCheckBox(T("xrange_auto"))
        self.sp_xmin = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, singleStep=10)
        self.sp_xmax = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, singleStep=10)
        row.addWidget(self.cb_xauto)
        row.addWidget(self.sp_xmin)
        row.addWidget(QLabel("–"))
        row.addWidget(self.sp_xmax)
        f.addRow(T("xrange"), row)
        self.cmb_size = QComboBox()
        for key in ("half_a4", "custom", "std"):
            self.cmb_size.addItem(T({"half_a4": "size_half_a4", "custom": "size_custom",
                                     "std": "size_std"}[key]), key)
        f.addRow(T("size"), self.cmb_size)
        row = QHBoxLayout()
        self.sp_w = QDoubleSpinBox(decimals=1, minimum=4, maximum=40, singleStep=0.5, suffix=" cm")
        self.sp_h = QDoubleSpinBox(decimals=1, minimum=3, maximum=40, singleStep=0.5, suffix=" cm")
        row.addWidget(self.sp_w)
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_h)
        row.addStretch(1)
        f.addRow(T("size_wh"), row)
        self.sec_plot = Section(T("adv_plot"), "plot", self.settings)
        fa = self.sec_plot.form
        forms.append(fa)
        self.cmb_r2 = QComboBox()
        for key in ("legend", "label", "off"):
            self.cmb_r2.addItem(T({"legend": "r2_legend", "label": "r2_label", "off": "r2_off"}[key]), key)
        fa.addRow(T("r2_mode"), self.cmb_r2)
        self.cb_err = QCheckBox(T("show_err"))
        self.cb_marksh = QCheckBox(T("mark_sh"))
        self.cb_lidx = QCheckBox(T("label_index"))
        self.cb_lidx.setToolTip(T("label_index_tip"))
        self.cb_inset = QCheckBox(T("inset_show"))
        self.cb_tab = QCheckBox(T("inset_table"))
        self.cb_excl = QCheckBox(T("show_excl"))
        self.cb_conc_colors = QCheckBox(T("conc_colors"))
        self.cb_conc_legend = QCheckBox(T("conc_legend"))   # Legende der Konzentrationen: Standard aus (Nutzerwunsch)
        self.cb_conc_legend.setToolTip(T("conc_legend_tip"))
        self.cb_conc_colors.toggled.connect(lambda *_: self.fill_conc_list())   # Farbfelder der Liste folgen dem Verlauf
        for cb in (self.cb_err, self.cb_marksh, self.cb_lidx, self.cb_inset, self.cb_tab, self.cb_excl, self.cb_conc_colors,
                   self.cb_conc_legend):
            fa.addRow(cb)
        row = QHBoxLayout()
        self.cb_pdf, self.cb_svg, self.cb_png = QCheckBox("PDF"), QCheckBox("SVG"), QCheckBox("PNG")
        for cb in (self.cb_pdf, self.cb_svg, self.cb_png):
            row.addWidget(cb)
        row.addStretch(1)
        fa.addRow(T("formats"), row)
        f.addRow(self.sec_plot)
        lv.addWidget(g)
        self.tf_card = TABS.TextFormatCard(self, "epsilon", TABS.ALL_TEXT_OPTS)   # Schrift und Rahmen (früher Dialog)
        self.tf_card.box, body = STYLE.card(T("tf_title"))   # Karte wie die übrigen des ε-Tabs (QFrame#card)
        bl_ = QVBoxLayout(body)
        bl_.setContentsMargins(0, 0, 0, 0)
        bl_.addWidget(self.tf_card)
        lv.addWidget(self.tf_card.box)

        hint = QLabel(T("drag_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        lv.addWidget(hint)
        lv.addStretch(1)
        align_forms(forms)

        lscroll = QScrollArea()
        lscroll.setWidget(left)
        lscroll.setWidgetResizable(True)
        lscroll.setFrameShape(QFrame.NoFrame)
        # Fußleisten wie in allen Tabs (Entwurf 2026-11): links Zurücksetzen … Weiter, rechts SI-Text und Exportieren
        self.btn_export = QPushButton(STYLE.icon("export", "#FFFFFF"), T("btn_export"))
        self.btn_export.setProperty("accent", True)
        self.btn_export.clicked.connect(self.export_dialog)
        self.btn_export.setToolTip(T("btn_export_tip"))
        self.btn_export.setDefault(True)
        self.btn_next = TABS.next_step_button()
        left_col = QWidget()
        cv = QVBoxLayout(left_col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(lscroll, 1)
        bar = TABS.side_bar(TABS.reset_button(self.reset_layout, self.reset_defaults), self.btn_next, stretch_at=1)
        cv.addWidget(bar)
        self.steps = TABS.StepColumn(left, cv, settings=self.settings, name="eps", next_button=self.btn_next,
                                     changed=lambda page: any(s_.changed for s_ in page.findChildren(Section)))
        # so breit wie der Inhalt, sonst schneidet die Spalte rechts ab (macOS blendet die Leiste aus)
        lscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_col.setMinimumWidth(max(380, left.minimumSizeHint().width()
                                     + lscroll.verticalScrollBar().sizeHint().width() + 4))

        # ---- rechte Seite
        self.canvas_host = TABS.CanvasHost(self.canvas, self.fig, page=True)
        self.tabs = TABS.result_tabs()                # wie die anderen Tabs: Abbildung | Ergebnisse | SI-Zeile
        # Kästchen (Bande im Bild) in eigener Spalte 0 ohne Text; λ steht in Spalte 7, die gleich dahinter angezeigt wird
        # (n, ε, b, R², Cutoff, Hinweise behalten ihre Nummern 1–6)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["", T("col_n"), T("col_coeff"), T("col_intercept"), T("col_r2"),
                                              T("col_cut"), T("col_warn"), T("col_lam")])
        hh_ = self.table.horizontalHeader()
        hh_.moveSection(7, 1)
        for c_ in (1, 2, 3, 4, 5, 7):                 # Spaltenköpfe nicht abschneiden („Achsenabschnitt“)
            hh_.setSectionResizeMode(c_, QHeaderView.ResizeToContents)
        STYLE.check_columns(self.table)
        hh_.setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.setShowGrid(False)                     # ruhige Zeilen wie die Auswahllisten links
        self.table.verticalHeader().setDefaultSectionSize(STYLE.CHECK_ROW_H + 4)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
                                   | QTableWidget.SelectedClicked)
        self.table.setToolTip(T("cut_tip"))
        STYLE.empty_note(self.table, T("tbl_empty_results"))
        self.table.itemChanged.connect(self.cutoff_edited)
        self._row_keys = []
        old_log = self.log.toPlainText() if hasattr(self, "log") else ""
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setPlainText(old_log)
        g_res = QGroupBox()
        QVBoxLayout(g_res).addWidget(self.table)
        # Reiter „SI-Text“ wie in den anderen Tabs: je Text eine Karte mit „Kopieren“ (SI-Zeile, Bildunterschrift,
        # Methodentext) statt eines großen leeren Textfelds
        si_w = QWidget()
        si_l = QVBoxLayout(si_w)

        def si_card(title, copy, tip=""):
            g_, body_ = STYLE.card(title)                    # Karten des ε-Tabs sind QFrame#card (keine QGroupBox)
            gv_ = QVBoxLayout(body_)
            gv_.setContentsMargins(0, 0, 0, 0)
            lb_ = STYLE.SiText()                          # Blocksatz, Formelzeichen wie im Satz
            b_ = STYLE.copy_button(tip)
            b_.clicked.connect(copy)
            gv_.addWidget(lb_)
            STYLE.card_actions(g_, b_)                    # „Kopieren“ oben rechts auf der Titelzeile, wie in jeder Karte
            si_l.addWidget(g_)
            return lb_
        self.txt_si = si_card(T("si_uv_title"), lambda: IRMS.copy_rich(*self._uv_line), T("si_uv_hint"))
        self.lbl_eps_cap = si_card(T("si_caption_title"), self.copy_eps_caption)
        self.lbl_eps_methods = si_card(T("si_methods_title"), self.copy_eps_methods, T("si_copy_methods_tip"))
        si_l.addStretch(1)
        self._uv_line = ("", "")
        self.lbl_cap_bar = TABS.CaptionLabel()            # Fußleiste rechts wie in den anderen Tabs
        # Protokoll: Hilfe → Protokoll (eigenes Fenster), kein Reiter mehr
        # Leer-Zustand: Anleitung (was herauskommt, welche Dateien, Schritte) statt weißer Fläche
        empty = TABS.EmptyGuide("eps", (T("act_open"), self.choose_csv), export=self.btn_export)
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(TABS.page_wrap(empty))
        self.preview_stack.addWidget(self.canvas_host)
        self.preview_stack.setCurrentIndex(1 if self.current and self.current in self.groups else 0)
        self.tabs.addTab(self.preview_stack, T("tab_figure"))
        self.tabs.addTab(TABS.result_page(g_res), T("tab_results"))
        STYLE.tidy(si_w)
        si_l.setContentsMargins(*TABS.PAGE_INSET)
        si_sa = QScrollArea()
        si_sa.setWidget(si_w)
        si_sa.setWidgetResizable(True)
        si_sa.setFrameShape(QFrame.NoFrame)
        self.tabs.addTab(si_sa, T("tab_si_text"))
        self.kpi_box = TABS.kpi_corner(self.tabs)     # Ergebnis auf einen Blick: die ersten beiden Banden mit Fit
        right = QWidget()                             # Rand oben wie in den anderen Tabs
        rl_ = QVBoxLayout(right)
        rl_.setContentsMargins(0, TABS.PAGE_TOP, 0, 0)
        rl_.setSpacing(0)
        rl_.addWidget(self.tabs)
        rl_.addWidget(TABS.side_bar(self.lbl_cap_bar, self.btn_export))
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left_col)
        split.addWidget(right)
        split.setSizes([left_col.minimumWidth(), 920])
        self.column_fit = STYLE.fit_column(left, lscroll, bar, left_col, split)   # nie abgeschnitten
        self.eps_page = split
        # Tabs erst bei Bedarf bauen (sichtbar oder Zugriff auf self.<x>_tab, siehe __getattr__): beim Öffnen nur
        # der angezeigte; die übrigen sind Platzhalter
        self._lazy = set()
        for key in self._TAB_BUILD_ORDER:
            self.__dict__.pop(self._tab_spec(key)[0], None)
        # Reihenfolge wie die SI: Synthese, Charakterisierung, Spektroskopie, Elektrochemie, Struktur, Rechnung
        self.main_tabs = QTabWidget()
        self._tab_keys = []
        for key in self._TAB_ORDER:
            if key == "eps":
                page, label = split, "tab_eps"
            else:
                page, label = QWidget(), self._tab_spec(key)[3]
                self._lazy.add(key)
            self.main_tabs.addTab(page, T(label))
            self._tab_keys.append(key)
        if self._tab_key in self._lazy:
            self._build_tab(self._tab_key)
        self.main_tabs.setCurrentIndex(self._tab_keys.index(self._tab_key) if self._tab_key in self._tab_keys else 0)
        self.main_tabs.currentChanged.connect(self._tab_shown)
        self.main_tabs.currentChanged.connect(lambda i: setattr(self, "_tab_key", self._tab_keys[i]))
        self.main_tabs.currentChanged.connect(                    # Vorlagen (CIF aus X-Ray) aktuell halten
            lambda i: self.dft_tab.fill_refs() if self._tab_keys[i] == "dft" else None)
        for i in range(self.main_tabs.count()):
            STYLE.tidy(self.main_tabs.widget(i))
        self.center = QStackedWidget()
        self.side = self.sidebar()                          # nur Übersicht und Projektseite; Tabs behalten die volle Breite
        self.center.addWidget(self.welcome_page())          # 0: ohne Projekt
        self.center.addWidget(self.nav_bar())               # 1: Tabs
        from elucida.app.publication_view import PublicationPage
        self.pub_page = PublicationPage(self)               # 2: Publikation (Verbindungen, Exporte)
        self.pub_page.set_publication(self.publication_dir)
        self.center.addWidget(self.pub_page)
        shell = QWidget()
        sh = QHBoxLayout(shell)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.setSpacing(0)
        sh.addWidget(self.side)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self.toolbar)
        right.addWidget(self.center, 1)
        sh.addLayout(right, 1)
        self.setCentralWidget(shell)
        self.center.setCurrentIndex(self._center_index())
        if old_pdir and str(old_pdir) == self.publication_dir:
            self.pub_page.project_tabs.setCurrentIndex(old_pub_tab)
            if old_path: self.pub_page.open_path(old_path)

        self.apply_globals()
        self.apply_series_widgets()
        for w in (self.sp_d, self.sp_cut, self.sp_ymax, self.sp_bla, self.sp_blb, self.sp_w, self.sp_h,
                  self.sp_xmin, self.sp_xmax):
            w.valueChanged.connect(self.changed)
        self.cb_xauto.toggled.connect(self._xauto_toggled)
        self.cmb_size.currentIndexChanged.connect(self._size_changed)
        for cb in (self.cb_pdf, self.cb_svg, self.cb_png):
            cb.toggled.connect(lambda *_: self.collect_globals())
        self.sp_min.valueChanged.connect(self.changed)
        self.sp_r2.valueChanged.connect(self.changed)
        self.sp_r2d.valueChanged.connect(self._r2_digits_changed)
        self.ed_bands.editingFinished.connect(self.changed)
        for w in (self.cmb_bl, self.cmb_r2):
            w.currentIndexChanged.connect(self.changed)
        for w in (self.cb_err, self.cb_tab, self.cb_bands_add, self.cb_shoulders, self.cb_excl, self.cb_inset,
                  self.cb_marksh, self.cb_lidx, self.cb_conc_colors, self.cb_conc_legend):
            w.toggled.connect(self.changed)
        for w in (self.sp_min, self.sp_r2, self.sp_r2d):
            w.valueChanged.connect(self._update_sections)
        self.cmb_r2.currentIndexChanged.connect(self._update_sections)
        for w in (self.cb_shoulders, self.cb_err, self.cb_marksh, self.cb_lidx, self.cb_inset, self.cb_tab,
                  self.cb_excl, self.cb_conc_colors, self.cb_conc_legend, self.cb_pdf, self.cb_svg, self.cb_png):
            w.toggled.connect(self._update_sections)
        self._update_sections()

    # Tabs: Schlüssel im Zustand -> (Attribut, Klasse, Attribut des Zustands, Textschlüssel); ε ist Teil des Fensters
    _TAB_ORDER = ("compound", "syn", "nmr", "irms", "hrms", "eps", "overlay", "uvkin", "fluo", "cv", "sec", "hcell", "epr", "xray", "dft", "other")
    _TAB_BUILD_ORDER = ("compound", "overlay", "uvkin", "fluo", "cv", "sec", "hcell", "epr", "hrms", "irms", "xray", "syn", "nmr", "dft", "other")

    def _tab_spec(self, key):
        return {"compound": ("comp_tab", COMP.CompoundTab, "compound", "tab_compound"),   # Zustand = self.compound
                "overlay": ("ov_tab", TABS.OverlayTab, "ov_state", "tab_overlay"),
                "fluo": ("fl_tab", TABS.FluoTab, "fl_state", "tab_fluo"),
                "uvkin": ("uvkin_tab", UVKIN.UVKinTab, "uvkin_state", "tab_uvkin"),
                "cv": ("cv_tab", CVMOD.CVTab, "cv_state", "tab_cv"),
                "sec": ("sec_tab", SECMOD.SECTab, "sec_state", "tab_sec"),
                "hcell": ("hcell_tab", HCELL.HCellTab, "hcell_state", "tab_hcell"),
                "epr": ("epr_tab", EPRMOD.EPRTab, "epr_state", "tab_epr"),
                "hrms": ("hrms_tab", HRMS.HRMSTab, "hrms_state", "tab_hrms"),
                "irms": ("irms_tab", IRMS.IRMSTab, "irms_state", "tab_irms"),
                "xray": ("xray_tab", XRAY.XrayTab, "xray_state", "tab_xray"),
                "syn": ("syn_tab", SYN.SynthTab, "syn_state", "tab_syn"),
                "nmr": ("nmr_tab", NMR.NMRTab, "nmr_state", "tab_nmr"),
                "dft": ("dft_tab", DFT.DFTTab, "dft_state", "tab_dft"),
                "other": ("other_tab", OTHER.OtherTab, "other_state", "tab_other")}[key]

    def tab_key_of(self, tab):
        """Schlüssel (cv, xray …) eines Tab-Objekts, None für Unbekanntes (baut keine Tabs)."""
        return next((k for k in self._TAB_BUILD_ORDER if self.__dict__.get(self._tab_spec(k)[0]) is tab), None)

    def _built(self, key):
        """Ist der Tab schon gebaut? (hasattr würde ihn über __getattr__ bauen)"""
        return self._tab_spec(key)[0] in self.__dict__

    def __getattr__(self, name):
        """Noch nicht gebauter Tab (self.cv_tab …): jetzt bauen und an seinen Platz setzen."""
        lazy = self.__dict__.get("_lazy") or ()
        for key in lazy:
            if self._tab_spec(key)[0] == name:
                return self._build_tab(key)
        raise AttributeError(name)

    def _tab_shown(self, i):
        if 0 <= i < len(self._tab_keys) and self._tab_keys[i] in self._lazy:
            self._build_tab(self._tab_keys[i])
        elif 0 <= i < len(self._tab_keys) and self._tab_keys[i] == "overlay" and \
                any(e.get("link") for e in self.ov_state.get("entries") or []):
            self.ov_tab.show_details()                # verknüpfte ε-Serien: Änderungen im ε-Tab übernehmen
            self.ov_tab.timer.start()
        self.sync_main_button()

    def sync_main_button(self, *_):
        """Ein Hauptknopf (blau) je Ansicht: in Tabs, deren Ergebnis nur in die SI geht (`MAIN_SI`: HRMS, Weitere), ist es
        „SI (Word)“ in der Leiste statt „Exportieren“ (Nutzerwunsch)."""
        b = self.toolbar.widgetForAction(self.act_si) if getattr(self, "act_si", None) is not None else None
        if b is None:
            return
        i = self.main_tabs.currentIndex()
        built = 0 <= i < len(self._tab_keys) and self._tab_keys[i] not in self._lazy
        tab = self.main_tabs.widget(i) if built else None
        nav = getattr(self, "nav_buttons", {}).get(i)
        on = bool(getattr(tab, "MAIN_SI", False)                  # Abbildung zu sehen oder Daten gespeichert (HR-MS-Zeile)
                  and (tab.preview_stack.currentIndex() == 1 or getattr(nav, "has_data", False)))
        if bool(b.property("accent")) != on:
            self.act_si.setIcon(STYLE.icon("export", "#FFFFFF" if on else None))
            STYLE.set_accent(b, on)
        guide = getattr(getattr(tab, "empty_guide", None), "btn", None)
        if getattr(tab, "MAIN_SI", False) and guide is not None and bool(guide.property("accent")) == on:
            STYLE.set_accent(guide, not on, "open")           # mit Daten ist „Dateien hinzufügen“ nicht mehr der Hauptknopf

    def _build_tab(self, key):
        """Tab aus seinem Zustand bauen und den Platzhalter ersetzen."""
        self._lazy.discard(key)
        attr, cls, st_attr, label = self._tab_spec(key)
        tab = cls(self, getattr(self, st_attr))
        self.__dict__[attr] = tab
        i = self._tab_keys.index(key)
        old = self.main_tabs.widget(i)
        cur = self.main_tabs.currentIndex()
        self.main_tabs.blockSignals(True)
        self.main_tabs.removeTab(i)
        self.main_tabs.insertTab(i, tab, T(label))
        self.main_tabs.setCurrentIndex(cur)
        self.main_tabs.blockSignals(False)
        STYLE.tidy(tab)
        if old is not None:
            old.setParent(None)
            old.deleteLater()
        return tab

    def replace_tab(self, key):
        """Einen Tab aus seinem Zustand neu aufbauen und an derselben Stelle einsetzen (Rückgängig: nur was sich
        geändert hat statt der ganzen Oberfläche, ~0,05 s statt ~1,2 s)."""
        if key in self._lazy:                          # noch nicht gebaut: entsteht später aus dem neuen Zustand
            return None
        attr, cls, st_attr, label = self._tab_spec(key)
        old = getattr(self, attr)
        fw = QApplication.focusWidget()                # Feld mit Fokus meldet beim Entfernen editingFinished: still
        if fw is not None and old.isAncestorOf(fw):
            fw.blockSignals(True)
        new = cls(self, getattr(self, st_attr))
        setattr(self, attr, new)
        i = self._tab_keys.index(key)
        cur = self.main_tabs.currentIndex()
        self.main_tabs.blockSignals(True)
        self.main_tabs.removeTab(i)
        self.main_tabs.insertTab(i, new, T(label))
        self.main_tabs.setCurrentIndex(cur)
        self.main_tabs.blockSignals(False)
        STYLE.tidy(new)
        # Eltern behalten: ohne sie gehört das Objekt Python, und die Speicherbereinigung könnte den Tab samt WebEngine
        # mitten in anderem Code zerstören. deleteLater räumt in der Ereignisschleife auf.
        old.hide()
        old.deleteLater()
        return new

    def _update_sections(self, *_):
        """Eingeklappte Bereiche markieren, wenn dort etwas vom Standard abweicht."""
        d = DEFAULT_GLOB
        self.sec_images.set_changed(self.cmb_bg.currentData() not in (None, "auto"))
        self.sec_eval.set_changed(self.sp_min.value() != d["min_points"]
                                  or abs(self.sp_r2.value() - d["min_r2"]) > 1e-9
                                  or self.sp_r2d.value() != d["r2_digits"]
                                  or self.cb_shoulders.isChecked() != d["shoulders"])
        self.sec_plot.set_changed(self.cmb_r2.currentData() != d["r2"] or any(
            cb.isChecked() != d[k] for cb, k in (
                (self.cb_err, "show_err"), (self.cb_marksh, "mark_sh"), (self.cb_lidx, "label_index"),
                (self.cb_inset, "inset"),
                (self.cb_tab, "table"), (self.cb_excl, "show_excl"), (self.cb_conc_colors, "conc_colors"),
                (self.cb_conc_legend, "conc_legend"), (self.cb_pdf, "fmt_pdf"),
                (self.cb_svg, "fmt_svg"), (self.cb_png, "fmt_png"))))
        if getattr(self, "steps", None) is not None:
            self.steps.refresh()                           # Punkt am Schritt, in dem etwas vom Standard abweicht

    def apply_globals(self):
        self._loading = True
        gl = self.glob
        self.sp_d.setValue(gl["path_length"])
        self.sp_cut.setValue(gl["cutoff"])
        self.sp_min.setValue(gl["min_points"])
        self.sp_r2.setValue(gl.get("min_r2", 0.98))
        self.sp_r2d.setValue(int(gl.get("r2_digits", 2)))
        core.R2_DIGITS = self.sp_r2d.value()
        self.ed_bands.setText(gl["bands"])
        self.cmb_bl.setCurrentIndex(self.cmb_bl.findData(gl["baseline"]))
        self.sp_bla.setValue(gl["bl_a"])
        self.sp_blb.setValue(gl["bl_b"])
        self.sp_ymax.setValue(gl["ymax"])
        self.cmb_r2.setCurrentIndex(self.cmb_r2.findData(gl["r2"]))
        self.cb_err.setChecked(gl["show_err"])
        self.cb_tab.setChecked(gl["table"])
        self.cmb_size.setCurrentIndex(max(0, self.cmb_size.findData(gl["size"])))
        self.sp_w.setValue(gl["w_cm"])
        self.sp_h.setValue(gl["h_cm"])
        self.cb_pdf.setChecked(gl["fmt_pdf"])
        self.cb_svg.setChecked(gl["fmt_svg"])
        self.cb_png.setChecked(gl["fmt_png"])
        self.cb_xauto.setChecked(gl["x_auto"])
        self.cb_bands_add.setChecked(gl.get("bands_add", True))
        self.cb_shoulders.setChecked(gl.get("shoulders", False))
        self.cb_excl.setChecked(gl.get("show_excl", False))
        self.cb_conc_colors.setChecked(gl.get("conc_colors", False))
        self.cb_conc_legend.setChecked(gl.get("conc_legend", False))
        self.cb_inset.setChecked(gl.get("inset", True))
        self.cb_marksh.setChecked(gl.get("mark_sh", False))
        self.cb_lidx.setChecked(gl.get("label_index", False))
        self.cb_tab.setEnabled(gl.get("inset", True))
        self.sp_xmin.setValue(gl["x_min"])
        self.sp_xmax.setValue(gl["x_max"])
        self.sp_xmin.setEnabled(not gl["x_auto"])
        self.sp_xmax.setEnabled(not gl["x_auto"])
        self._update_size_widgets()
        manual = gl["baseline"] == "manual"
        self.sp_bla.setEnabled(manual)
        self.sp_blb.setEnabled(manual)
        self.cb_color.setChecked(gl.get("color_show", False))
        self.sp_color_d.setValue(gl.get("color_d", 1.0))
        self._loading = False
        self.update_color()

    def collect_globals(self):
        core.R2_DIGITS = self.sp_r2d.value()
        self.glob.update(path_length=self.sp_d.value(), cutoff=self.sp_cut.value(), r2_digits=self.sp_r2d.value(),
                         min_points=self.sp_min.value(), min_r2=self.sp_r2.value(), bands=self.ed_bands.text().strip(),
                         baseline=self.cmb_bl.currentData(), bl_a=self.sp_bla.value(),
                         bl_b=self.sp_blb.value(), ymax=self.sp_ymax.value(),
                         r2=self.cmb_r2.currentData(), show_err=self.cb_err.isChecked(),
                         table=self.cb_tab.isChecked(), size=self.cmb_size.currentData(),
                         w_cm=self.sp_w.value(), h_cm=self.sp_h.value(),
                         fmt_pdf=self.cb_pdf.isChecked(), fmt_svg=self.cb_svg.isChecked(),
                         fmt_png=self.cb_png.isChecked(), x_auto=self.cb_xauto.isChecked(),
                         bands_add=self.cb_bands_add.isChecked(), shoulders=self.cb_shoulders.isChecked(),
                         show_excl=self.cb_excl.isChecked(), conc_colors=self.cb_conc_colors.isChecked(),
                         conc_legend=self.cb_conc_legend.isChecked(), inset=self.cb_inset.isChecked(),
                         mark_sh=self.cb_marksh.isChecked(), label_index=self.cb_lidx.isChecked(),
                         x_min=self.sp_xmin.value(), x_max=self.sp_xmax.value())

    def _update_size_widgets(self):
        key = self.cmb_size.currentData()
        if key == "half_a4":
            self.sp_w.blockSignals(True)
            self.sp_h.blockSignals(True)
            self.sp_w.setValue(16.0)
            self.sp_h.setValue(11.0)
            self.sp_w.blockSignals(False)
            self.sp_h.blockSignals(False)
        custom = key == "custom"
        self.sp_w.setEnabled(custom)
        self.sp_h.setEnabled(custom)

    def fill_conc_list(self):
        """Messungen der Serie zum Ab- und Anwählen, auch die abgewählten (die fehlen in self.groups)."""
        self.lst_conc.blockSignals(True)
        self.lst_conc.setRowCount(0)
        if self.samples:
            on = {k: {a: v for a, v in o.items() if a != "off"} for k, o in self.conc.items()}
            every = core.group_samples(self.samples, on, Path(self.csv_path).stem)[0].get(self.current, [])
            ramp = core.conc_ramp([s_["c"] for s_ in self.groups.get(self.current, [])]) \
                if self.cb_conc_colors.isChecked() else {}
            for s_ in sorted(every, key=lambda s_: -s_["c"]):
                o_ = self.conc.get(s_["name"]) or {}
                STYLE.check_row(self.lst_conc, s_["name"], (f"{s_['c']:g}", core.unit_text(s_["unit"]), ""),
                                not o_.get("off"))
                # eigene Farbe, sonst die des Bildes (Farbverlauf bzw. Linienfarbe)
                shown = o_.get("color") or ramp.get(s_["c"]) or core.DEFAULTS["line_color"]
                self.lst_conc.setCellWidget(self.lst_conc.rowCount() - 1, 3, TABS.color_button(
                    shown, lambda c, k=s_["name"]: self.conc_color_picked(k, c), cell=True))
        STYLE.fit_check_table(self.lst_conc)
        self.lst_conc.setVisible(self.lst_conc.rowCount() > 0)
        self.btn_conc_colors.setVisible(any(o.get("color") for o in self.conc.values()))
        self.lst_conc.blockSignals(False)
        self.fill_conc_table()

    def conc_color_picked(self, key, color):
        """Eigene Farbe einer Messung (ersetzt für sie den Farbverlauf bzw. die Linienfarbe)."""
        self.conc.setdefault(key, {})["color"] = color
        self.rebuild_groups()
        self.btn_conc_colors.setVisible(True)
        self.render()
        self.push_undo()
        QTimer.singleShot(0, self.fill_conc_list)        # nicht sofort: der Farbknopf, der gerade meldet, würde gelöscht

    def conc_colors_reset(self):
        for k in [k for k, o in self.conc.items() if o.pop("color", None) and not o]:
            del self.conc[k]
        self.rebuild_groups()
        self.fill_conc_list()
        self.render()
        self.push_undo()

    # -- Konzentrationen eintragen (Klappbereich der Karte Daten, früher ein Dialog) ----------------------
    def fill_conc_table(self):
        """Proben aller Serien mit Serie und Konzentration (aus dem Namen oder eingetragen)."""
        self._conc_loading = True
        t = self.tbl_conc
        t.setRowCount(len(self.samples or []))
        unit0, missing = None, False
        default = Path(self.csv_path).stem if self.csv_path else ""
        for i, s_ in enumerate(self.samples or []):
            o = self.conc.get(s_["key"]) or {}
            unit0 = unit0 or o.get("unit") or (s_["parsed"][2] if s_["parsed"] else None)
            it = QTableWidgetItem(s_["key"])
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setToolTip(s_["key"])
            t.setItem(i, 0, it)
            t.setItem(i, 1, QTableWidgetItem(o.get("series") or (s_["parsed"][0] if s_["parsed"] else default)))
            c = o.get("conc") or (s_["parsed"][1] if s_["parsed"] and not o.get("skip") else None)
            missing = missing or not (c or o.get("skip"))
            t.setItem(i, 2, QTableWidgetItem(f"{c:g}" if c else ""))
        t.setFixedHeight(t.horizontalHeader().sizeHint().height() + min(max(t.rowCount(), 1), 8) * STYLE.CHECK_ROW_H + 2)
        for r in range(t.rowCount()):
            t.setRowHeight(r, STYLE.CHECK_ROW_H)
        files = tuple(self.csv_paths or ())
        if unit0 or files != getattr(self, "_conc_files", None):   # Einheit aus den Daten zeigen, nie eine erfinden:
            self._conc_files = files                         # andere Messdateien beginnen wieder ohne Einheit
            self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(unit0)) if unit0 else 0)
        self.lbl_conc_intro.setText(T("conc_intro") if missing else "")
        self.sec_conc.setVisible(bool(self.samples))
        if missing:                                          # ohne Konzentrationen gibt es nichts auszuwerten: aufklappen
            self.sec_conc.btn.setChecked(True)
        self._conc_loading = False

    def conc_fill_dilution(self):
        if self.sp_dil_start.value() <= 0:
            self.lbl_conc_warn.setText(T("start_missing"))
            return
        t = self.tbl_conc
        rows = sorted({i.row() for i in t.selectedIndexes()}) or list(range(t.rowCount()))
        c = self.sp_dil_start.value()
        self._conc_loading = True
        for r in rows:
            t.item(r, 2).setText(f"{c:.6g}")
            c /= self.sp_dil_fac.value()
        self._conc_loading = False
        self.conc_apply()

    def conc_apply(self, *_):
        """Tabelle -> Konzentrationen (wie früher OK im Dialog): gilt sofort, mit Werten aber erst mit einer Einheit."""
        if getattr(self, "_conc_loading", False) or not self.samples:
            return
        t, unit, new = self.tbl_conc, self.cmb_unit.currentData(), {}
        for i, s_ in enumerate(self.samples):
            try:
                c = parse_float(t.item(i, 2).text())
            except ValueError:
                c = None
            o = {"conc": c, "unit": unit, "series": (t.item(i, 1).text() or "").strip()} if c else {"skip": True}
            old = self.conc.get(s_["key"]) or {}
            o.update({k: old[k] for k in ("off", "color") if old.get(k)})
            new[s_["key"]] = o
        if unit is None and any(o.get("conc") for o in new.values()):
            self.lbl_conc_warn.setText(T("unit_missing"))
            return
        self.lbl_conc_warn.setText("")
        if new == self.conc:
            return
        self.conc = new
        if self.rebuild_groups():
            self.apply_compound_defaults(only_empty=True)
            self.lbl_conc_intro.setText("")
        self.apply_series_widgets()
        self.render()
        self.push_undo()

    def conc_toggled(self, it):
        key, on = it.data(Qt.UserRole), it.checkState() == Qt.Checked
        if not on and len(self.groups.get(self.current, [])) < 2:
            self.lst_conc.blockSignals(True)           # ganz ohne Messung gäbe es die Serie nicht mehr
            it.setCheckState(Qt.Checked)
            self.lst_conc.blockSignals(False)
            self.statusBar().showMessage(T("conc_last"), 5000)
            return
        o = self.conc.setdefault(key, {})
        if on:
            o.pop("off", None)
            if not o:
                del self.conc[key]
        else:
            o["off"] = True
        self.rebuild_groups()
        self.render()

    def apply_series_widgets(self):
        self.fill_conc_list()
        self._loading = True
        st = self.series.get(self.current)
        self.ed_mw.setText(f"{st['mw']:.2f}" if st and st["mw"] else "")
        self.lbl_struct.setText(Path(st["structure"]).name if st and st["structure"] else "–")
        from elucida.app.welcome import formula_text
        c = self.compound
        used = st["mw"] if st else c.get("mw")              # gezeigt wird die Zahl, mit der die Serie rechnet
        self.lbl_formula.setText(formula_text(c["formula"]) if c.get("formula") else "–")
        self.lbl_mw.setText(f"{used:.2f} g mol⁻¹" if used else "–")
        self.cb_structure.setChecked(bool(st and st["structure"]))
        self.cb_structure.setEnabled(bool(st and (st["structure"] or c.get("structure"))))
        self.lbl_photo.setText(Path(st["photo"]).name if st and st["photo"] else "–")
        self.cmb_bg.setCurrentIndex(self.cmb_bg.findData(st["bg"] if st else "auto"))
        info = ""                                     # Hinweise zur Struktur zeigt die Karte nicht mehr (Nutzerwunsch)
        unit = self.units.get(self.current) if st else None
        if unit and unit != "mg/mL":
            info = (info + "\n" if info else "") + T("mw_unused", u="µM" if unit == "uM" else unit)
        mw_missing = unit == "mg/mL" and not (st and st["mw"])
        if mw_missing:
            info = (info + "\n" if info else "") + T("mw_needed")
        differs = bool(st and st["mw"] and c.get("mw") and abs(st["mw"] - c["mw"]) >= 0.005)
        if differs:                                   # gespeicherte Serie mit eigenem Wert: folgt erst nach dem Ändern
            info = (info + "\n" if info else "") + T("mw_differs", m=f"{c['mw']:.2f}")
        self.lbl_chem.setText(info)                   # HintLabel: ohne Text keine Zeile, mittig
        self.lbl_chem.setStyleSheet(WARN_CSS if mw_missing else STYLE.NOTE_CSS if differs else "")   # fehlende Molmasse = Fehler (rot)
        self.sp_struct_w.setValue(st.get("struct_w", 17.0) if st else 17.0)
        self.sp_photo_w.setValue(st.get("photo_w", 9.0) if st else 9.0)
        self.sp_struct_w.setEnabled(bool(st and st["structure"]))
        self.sp_photo_w.setEnabled(bool(st and st["photo"]))
        self._loading = False

    def _xauto_toggled(self, on):
        if self._loading:
            return
        self.sp_xmin.setEnabled(not on)
        self.sp_xmax.setEnabled(not on)
        if not on and self.current in self.groups:       # mit dem Datenbereich vorbelegen
            xs = np.concatenate([s_["x"] for s_ in self.groups[self.current]])
            self._loading = True
            if self.sp_xmin.value() <= xs.min() or self.sp_xmin.value() >= xs.max():
                self.sp_xmin.setValue(float(np.floor(xs.min())))
            if self.sp_xmax.value() >= xs.max() or self.sp_xmax.value() <= self.sp_xmin.value():
                self.sp_xmax.setValue(float(np.ceil(xs.max())))
            self._loading = False
        self.changed()

    def _size_changed(self, *_):
        if self._loading:
            return
        self._update_size_widgets()
        self.changed()

    def canvas_is_dark(self):
        mode = self.settings.value("ui/canvas", "system")
        return (STYLE._mode if mode == "system" else mode) == "dark"

    def _sync_canvas_toggle(self):
        """Knopf der Leiste: Symbol und Text nennen den aktuellen Zustand der Zeichenfläche (Mond dunkel, Sonne hell)."""
        if getattr(self, "canvas_toggle", None) is None:
            return
        dark = self.canvas_is_dark()
        self.canvas_toggle.setIcon(STYLE.icon("moon" if dark else "sun", STYLE.colors()["text2"]))
        self.canvas_toggle.setText(T("canvas_now_dark" if dark else "canvas_now_light"))
        self.canvas_toggle.setToolTip(T("canvas_toggle_tip"))

    def set_canvas_mode(self, mode):
        self.settings.setValue("ui/canvas", mode)
        from elucida.app.canvas_theme import configure
        configure(self.canvas_is_dark())
        from elucida.app.drawing_editor import DrawingEditor
        for editor in self.findChildren(DrawingEditor):
            editor.set_canvas_dark(self.canvas_is_dark())
        self._sync_canvas_toggle()
        for host in self.findChildren(TABS.CanvasHost):
            host.update()
        self.fill_recent_list()                        # Strukturbilder: Hintergrund folgt dem Canvas
        if self.__dict__.get("pub_page") is not None and self.publication_dir and not self.project_dir:
            self.pub_page.refresh()
        for code, action in getattr(self, 'canvas_mode_actions', {}).items():
            action.setChecked(code == mode)

    def _theme_mode(self):
        return self.settings.value("ui/theme", "system") or "system"

    def apply_theme(self):
        STYLE.apply(self._theme_mode(), IMG.app_data_dir() / "theme")
        from elucida.app.canvas_theme import configure
        configure(self.canvas_is_dark())
        icon = self.app_icon()                           # Fenster-/Dock-Symbol folgt dem Theme
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

    @staticmethod
    def app_icon():
        """Helles oder dunkles App-Symbol passend zum aktuellen Theme (Paket-Icons: .ico hell, .icns dunkel)."""
        return resource_path("assets/icon-dark.png" if STYLE._mode == "dark" else "assets/icon.png")

    def switch_theme(self, mode):
        self.collect_globals()
        self.settings.setValue("ui/theme", mode)
        self.apply_theme()
        self.build_ui()                                # Symbole in der neuen Textfarbe
        self.render()

    def _system_scheme_changed(self, *_):
        if self._theme_mode() == "system" and STYLE.resolve("system") != STYLE._mode:
            self.switch_theme("system")

    def switch_lang(self, code):
        self.collect_globals()
        set_lang(code)
        self.settings.setValue("lang", code)
        # Hinweise zur Struktur werden beim Laden übersetzt und gespeichert -> in der neuen Sprache neu laden
        for g, st in self.series.items():
            if st.get("structure") and Path(st["structure"]).exists():
                self.set_structure(st["structure"], g, render=False, sync=True, autofill_mw=False)
        self.build_ui()
        self.render()

    NAV_GROUPS = (("nav_grp_compound", ("compound",)), ("nav_grp_syn", ("syn", "nmr", "irms", "hrms")), ("nav_grp_uv", ("eps", "overlay", "uvkin", "fluo")),
                  ("nav_grp_ec", ("cv", "sec", "hcell", "epr")), ("nav_grp_struct", ("xray", "dft", "other")))

    def nav_bar(self):
        """Tabs in vier Gruppen wie die SI (Leiste oben statt Reiter): kostet Höhe statt Breite – die Abbildung
        ist in der Breite begrenzt, eine Seitenleiste würde sie um ~20 % verkleinern."""
        from PySide6.QtWidgets import QButtonGroup
        from elucida.app.welcome import NameTab, NavTab
        bar = QFrame(objectName="navBar")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(10, 8, 10, 8)
        hb.setSpacing(4)
        # Pfadleiste: ⌂ Übersicht › Projekt › Verbindung ▾ (jede Stufe anklickbar, Verbindungen des Projekts im Menü);
        # sitzt in der Werkzeugleiste, damit die Tab-Leiste schmaler wird (Mindestbreite des Fensters)
        # Haus als Symbol: das Zeichen ⌂ kommt aus einer Ersatzschrift und hob die Grundlinie um 1 px
        self.btn_home = QPushButton(STYLE.icon("home", STYLE.colors()["text2"]), T("nav_home"), objectName="crumb")
        self.btn_home.setIconSize(self.toolbar.iconSize())      # wie Sonne/Mond und die übrigen Leistensymbole
        self.btn_home.setToolTip(T("act_to_overview"))
        self.btn_home.clicked.connect(self.go_home)
        self.btn_pub = QPushButton(objectName="crumb")      # Projekt (nur bei Verbindungen darin)
        self.btn_pub.setToolTip(T("act_to_publication"))
        self.btn_pub.clicked.connect(self._crumb_pub)
        self.btn_comp = QPushButton(objectName="crumbNow")     # andere Verbindungen des Projekts
        self.btn_comp.setToolTip(T("nav_switch_tip"))
        self.comp_menu = QMenu(self.btn_comp)
        self.comp_menu.aboutToShow.connect(self._fill_comp_menu)
        self.btn_comp.setMenu(self.comp_menu)
        self.crumb_seps = [QLabel("›", objectName="crumbSep", alignment=Qt.AlignCenter),
                           QLabel("›", objectName="crumbSep", alignment=Qt.AlignCenter)]
        cw = QWidget()
        crumbs = QHBoxLayout(cw)
        crumbs.setContentsMargins(0, 0, 0, 0)
        crumbs.setSpacing(2)
        for w_ in (self.btn_home, self.crumb_seps[0], self.btn_pub, self.crumb_seps[1], self.btn_comp):
            crumbs.addWidget(w_, 0, Qt.AlignVCenter)
        self.act_crumbs = self.toolbar.insertWidget(self._tb_left, cw)
        grp = QButtonGroup(bar)
        self.nav_buttons, self._dots_dir = {}, None
        for gi, (head, keys) in enumerate(self.NAV_GROUPS):
            if gi:
                sep = QFrame(objectName="navSep")
                sep.setFixedWidth(1)
                hb.addSpacing(8)
                hb.addWidget(sep)
                hb.addSpacing(8)
            col = QVBoxLayout()
            col.setSpacing(5)                                   # Abstand Gruppenüberschrift – Tabs
            col.addWidget(QLabel(T(head).upper(), objectName="navGroup"), 0, Qt.AlignHCenter)   # mittig über der Gruppe
            row = QHBoxLayout()
            row.setSpacing(2)
            for k in keys:
                i = self._tab_keys.index(k)
                b = NameTab() if k == "compound" else NavTab(self.main_tabs.tabText(i))
                b.clicked.connect(lambda _=False, i=i: self.main_tabs.setCurrentIndex(i))
                grp.addButton(b)
                row.addWidget(b)
                self.nav_buttons[i] = b
            col.addLayout(row)
            hb.addLayout(col)
        hb.addStretch(1)
        self.main_tabs.currentChanged.connect(lambda i: self.nav_buttons[i].setChecked(True))
        self.nav_buttons[self.main_tabs.currentIndex()].setChecked(True)
        self._update_crumbs()
        self.main_tabs.tabBar().hide()
        self.main_tabs.setDocumentMode(True)
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(bar)
        v.addWidget(self.main_tabs, 1)
        return holder

    def _append_log(self, msg):
        self.log.appendPlainText(msg)

    def show_log(self):
        """Protokoll aller Tabs (Meldungen, Warnungen, Fehlerdetails) in einem eigenen Fenster."""
        dlg = QDialog(self)
        dlg.setWindowTitle(T("log_title"))
        dlg.resize(820, 520)
        v = QVBoxLayout(dlg)
        txt = QPlainTextEdit(readOnly=True)
        txt.setPlainText(self.log.toPlainText())
        txt.moveCursor(QTextCursor.End)
        v.addWidget(txt)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.exec()

    # ------------------------------------------------------------ Daten
    def choose_csv(self):
        if not self.ensure_project():
            return
        start = self.settings.value("last_dir", str(Path.home()))
        ps, _ = QFileDialog.getOpenFileNames(self, T("dlg_open_csv"), start,
                                             f"{T('flt_csv')};;{T('flt_all')}")
        if ps:
            self.open_files(ps)

    def open_csv(self, path, ask=True):
        return self.open_files([path], ask)

    def files_label(self):
        names = [Path(p).name for p in self.csv_paths]
        if len(names) == 1:
            return names[0]
        short = ", ".join(names[:3]) + (", …" if len(names) > 3 else "")
        return T("files_loaded", n=len(names), names=short)

    def open_files(self, paths, ask=True):
        """Eine oder mehrere Messdateien (CSV/TXT/DSW/BSW) gemeinsam öffnen,
        z. B. wenn jede Konzentration einzeln gemessen wurde."""
        if not self.ensure_project():
            return False
        try:
            paths = sorted(self.import_file(p, PRJ.data_sub("eps")) for p in paths)   # Kopie ins Projekt
        except OSError as e:
            self.error(str(e))
            return False
        path = paths[0]
        try:
            samples = core.read_samples(paths)
        except Exception as e:
            self.error(f"{type(e).__name__}: {e}")
            return False
        if not samples:
            self.error(T("conc_none"))
            return False
        self.csv_path, self.csv_paths, self.samples = path, paths, samples
        self._eps_held = {}
        self.settings.setValue("last_dir", str(Path(path).parent))
        self.groups, self.units, self.series, self.conc = {}, {}, {}, {}
        _, _, missing = core.group_samples(samples, self.conc, Path(path).stem)
        if not self.rebuild_groups():
            self.lbl_file.setText(self.files_label())
            self.fill_conc_list()
            if missing:                                      # Konzentrationen fehlen: im Tab eintragen statt Fehlermeldung
                self.edit_concentrations()
                self.statusBar().showMessage(T("conc_enter"), 10000)
            else:
                self.error(T("conc_none"))
            return False
        self.lbl_file.setText(self.files_label())
        self.apply_compound_defaults(only_empty=True)   # Messdaten geladen (auch beim Öffnen): nur leere Serien füllen
        self.apply_globals()
        self.apply_series_widgets()
        self.render()
        return True

    def edit_concentrations(self):
        """Klappbereich „Konzentrationen eingeben“ in der Karte Daten zeigen (bis 2.7.1 ein Dialog)."""
        if not self.samples:
            self.error(T("load_first"))
            return False
        self.main_tabs.setCurrentIndex(self._tab_keys.index("eps"))
        self.steps.reveal(self.sec_conc)
        self.sec_conc.btn.setChecked(True)
        return True

    def rebuild_groups(self):
        """Serien aus Proben + Konzentrationen neu bilden; Einstellungen je Serie bleiben."""
        try:
            groups, units, missing = core.group_samples(self.samples, self.conc, Path(self.csv_path).stem)
        except ValueError as e:
            self.error(str(e))
            return False
        for k in missing:
            self.log_signal.emit("  " + T("no_conc_in_name", name=k))
        self.groups, self.units = groups, units
        for g in groups:
            self.series.setdefault(g, {"mw": None, "structure": None, "photo": None, "bg": "auto",
                                       "layout": {}, "structure_asset": None, "photo_asset": None,
                                       "chem_info": "", "chem_warn": False,
                                       "struct_w": 17.0, "photo_w": 9.0, "band_cutoff": {},
                                       "band_hidden": []})
        if self.current not in groups:
            self.current = next(iter(groups), None)
        self.cmb_series.blockSignals(True)
        self.cmb_series.clear()
        self.cmb_series.addItems(list(groups))
        if self.current:
            self.cmb_series.setCurrentText(self.current)
        self.cmb_series.blockSignals(False)
        log_names = ", ".join(groups) or "–"
        self.log_signal.emit(T("cary_series", name=Path(self.csv_path).name, s=log_names))
        return bool(groups)

    def restart_file(self):
        """Eingaben zu den aktuellen Messdateien verwerfen (Konzentrationen, Serien-Einstellungen)."""
        if not self.csv_path:
            return self.error(T("load_first"))
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            ans = QMessageBox.question(self, T("act_restart").rstrip("…"),
                                       T("restart_q", name=self.files_label()))
            if ans != QMessageBox.Yes:
                return False
        paths = list(self.csv_paths)
        self.glob = dict(DEFAULT_GLOB)
        self.series, self.conc, self.current = {}, {}, None
        return self.open_files(paths)

    # ------------------------------------------------------------ Projekt
    def get_state(self):
        """Gesamter Zustand aller Tabs (serialisierbar) – für Projektdatei und Undo."""
        if hasattr(self, "sp_d"):
            self.collect_globals()
        keys = ("mw", "structure", "photo", "bg", "layout", "struct_w", "photo_w", "band_cutoff", "band_hidden",
                "color_c", "solvent", "no_structure")
        held = self._eps_held
        return {"eps": {"files": list(self.csv_paths) + [p for p in held.get("files", []) if p not in self.csv_paths],
                        "glob": dict(self.glob), "conc": self.conc,
                        "series": dict(held.get("series", {}),
                                       **{g: {k: st.get(k) for k in keys} for g, st in self.series.items()}),
                        "current": self.current},
                "overlay": self.ov_state, "uvkin": self.uvkin_state, "fluo": self.fl_state, "cv": self.cv_state, "sec": self.sec_state, "hcell": self.hcell_state, "epr": self.epr_state,
                "irms": self.irms_state, "hrms": self.hrms_state, "xray": self.xray_state,
                "dft": self.dft_state, "other": self.other_state, "nmr": self.nmr_state, "syn": self.syn_state,
                "compound": dict(self.compound),
                "tab": self._tab_key,
                "text": dict(self.text_fmt), "text_tabs": {k: dict(v) for k, v in self.tab_fmt.items()}}

    def _changed_parts(self, state):
        """Teile des Zustands (eps, cv, xray, tab …), die sich gegenüber der Oberfläche unterscheiden. Verbindung oder
        Textformat wirken auf alle Tabs und ε: dann gelten alle als geändert (ohne das Fenster neu zu bauen)."""
        prev = json.loads(self._snap())
        dump = lambda v: json.dumps(v, sort_keys=True, default=str)       # noqa: E731
        changed = {k for k in set(prev) | set(state) if dump(prev.get(k)) != dump(state.get(k))}
        if changed & {"compound", "text", "text_tabs"}:
            changed |= set(self._TAB_BUILD_ORDER) | {"eps"}
        return changed

    def set_state(self, state, partial=False):
        """Zustand übernehmen (Projekt laden, Undo/Redo). partial (Rückgängig/Wiederholen): nur geänderte Tabs neu
        aufbauen, ε nur nachziehen, statt der ganzen Oberfläche (build_ui, ~1,2 s im Beispielprojekt)."""
        if not self.save_drawings():
            return
        state = json.loads(json.dumps(state))          # entkoppeln
        if state.get("hrms") is None:                  # Projekte vor 1.21: MS-Teil stand im Tab IR + MS
            ir = state.get("irms") or {}
            state["hrms"] = {k: ir[k] for k in ("ms_file", "ms_raw", "ms_rt", "adduct", "found") if k in ir}
        changed = self._changed_parts(state) if partial and getattr(self, "main_tabs", None) is not None else None
        eps_changed = changed is None or "eps" in changed
        eps = state.get("eps") or {}
        old_series = self.series
        if eps_changed:
            self.glob = dict(DEFAULT_GLOB, **(eps.get("glob") or {}))
            self.conc = eps.get("conc") or {}
            files = list(eps.get("files") or [])
            # alle oder keine: bei mehreren Dateien tragen die Probenschlüssel (Konzentrationen) den Dateinamen
            self.csv_paths = files if all(Path(p).exists() for p in files) else []
            self.csv_path = self.csv_paths[0] if self.csv_paths else None
            self._eps_held = {"files": [p for p in files if p not in self.csv_paths]}
            self.groups, self.units, self.series, self.samples = {}, {}, {}, []
        for key in self._TAB_BUILD_ORDER:
            # unveränderte Tabs behalten ihre Objekte (nicht neu gebaute Tabs halten Verweise)
            if changed is None or key in changed:
                st_ = getattr(self, self._tab_spec(key)[2])
                st_.clear()
                st_.update(state.get(key) or {})
        self.compound = dict(state.get("compound") or {})
        self.text_fmt = dict(core.TEXT_DEFAULTS, **(state.get("text") or {}))
        self.tab_fmt = {k: dict(v) for k, v in (state.get("text_tabs") or {}).items()}
        if changed is not None:
            self.sync_text_cards()                     # ε-Karte bleibt beim Rückgängig stehen, die anderen werden neu gebaut
        tab = state.get("tab", "syn")
        if isinstance(tab, int):                         # bis 1.23 gespeichert als Position (alte Reihenfolge)
            old = ("eps", "overlay", "fluo", "cv", "sec", "epr", "hrms", "irms", "xray", "dft")
            tab = old[tab] if 0 <= tab < len(old) else "syn"
        self._tab_key = tab
        if changed is None:
            self.current = eps.get("current")
            self.build_ui()
        else:
            for key in self._TAB_BUILD_ORDER:          # feste Reihenfolge wie beim Aufbau (DFT liest X-Ray)
                if key in changed:
                    self.replace_tab(key)
            if "tab" in changed and tab in self._tab_keys:
                self.main_tabs.setCurrentIndex(self._tab_keys.index(tab))
            if not eps_changed:
                return
            self.current = eps.get("current")
            self.cmb_series.blockSignals(True)
            self.cmb_series.clear()
            self.cmb_series.blockSignals(False)
            self.lbl_file.setText(self.files_label())
        if self.csv_paths:
            key = ("samples_multi", tuple(self.csv_paths))
            if key not in self.extra_cache:
                self.extra_cache[key] = core.read_samples(self.csv_paths)
            self.samples = self.extra_cache[key]
            self.rebuild_groups()
            for g, sd in (eps.get("series") or {}).items():
                if g not in self.series:
                    continue
                st = self.series[g]
                for k, v in sd.items():
                    if v is not None and k not in ("structure", "photo"):
                        st[k] = v
                st["layout"] = st.get("layout") or {}
                if st.get("no_structure"):                  # „Struktur im Bild“ abgewählt: Vorgabe der Verbindung zurücknehmen
                    st.update(structure=None, structure_asset=None)
                old = old_series.get(g) or {}
                for kind, setter in (("structure", self.set_structure), ("photo", self.set_photo)):
                    p = sd.get(kind)
                    if p and Path(p).exists():
                        if old.get(kind) == p and old.get(kind + "_asset") is not None:
                            st[kind], st[kind + "_asset"] = p, old[kind + "_asset"]   # wiederverwenden
                            if kind == "structure":
                                st["chem_info"], st["chem_warn"] = old.get("chem_info", ""), old.get("chem_warn")
                        elif kind == "structure":
                            setter(p, g, render=False, sync=True, autofill_mw=False)
                        else:
                            setter(p, g, render=False, sync=True)
            if self.current not in self.groups:
                self.current = next(iter(self.groups), None)
            self.cmb_series.blockSignals(True)
            self.cmb_series.setCurrentText(self.current or "")
            self.cmb_series.blockSignals(False)
            self.lbl_file.setText(self.files_label())
        self._eps_held["series"] = {g: sd for g, sd in (eps.get("series") or {}).items() if g not in self.series}
        self.apply_globals()
        self.apply_series_widgets()
        if changed is not None:                        # ohne Neuaufbau: Anleitung/Abbildung selbst umschalten
            self.preview_stack.setCurrentIndex(1 if self.current and self.current in self.groups else 0)
            self._update_sections()
        if self.csv_paths:
            self.render()
        else:
            self.fig.clear()
            self.canvas.draw_idle()
            self.clear_results()                           # nichts von der zuvor geöffneten Verbindung stehen lassen

    def _snap(self):
        return json.dumps(self.get_state(), sort_keys=True, default=str)

    def _init_undo(self):
        self._undo, self._redo = [self._snap()], []
        self._saved_snap = self._undo[0]
        self._update_undo_actions()
        self.update_title()

    def push_undo(self):
        if self._restoring or not self._undo:
            return
        snap = self._snap()
        if snap != self._undo[-1]:
            no_tab = lambda s: dict(json.loads(s), tab=None)       # noqa: E731
            if no_tab(snap) == no_tab(self._undo[-1]):         # nur der offene Tab anders: kein eigener Schritt
                self._undo[-1] = snap
            else:
                self._undo.append(snap)
                del self._undo[:-200]
                self._redo.clear()
            self._update_undo_actions()
            self.update_title()
            if self.project_dir:
                self.autosave_timer.start()

    def _restore(self, snap):
        self._restoring = True
        state = json.loads(snap)
        # im offenen Tab bleiben; betrifft die Änderung nur andere Tabs, deren ersten zeigen (Nutzerwunsch P9 R1)
        ch = self._changed_parts(state)
        state["tab"] = next((k for k in self._TAB_ORDER if k in ch), self._tab_key) \
            if self._tab_key not in ch else self._tab_key
        self.set_state(state, partial=True)
        QTimer.singleShot(200, self._end_restore)       # erst nach dem Neuzeichnen aller Tabs

    def _end_restore(self):
        self._restoring = False
        if self._undo:
            self._undo[-1] = self._snap()              # tatsächlichen Zustand übernehmen
        self._update_undo_actions()
        self.update_title()
        if self.project_dir:
            self.autosave_timer.start()                # Undo/Redo-Stand ebenfalls speichern

    def _load_state_into_ui(self, state):
        """Projekt/neues Projekt: Zustand setzen, Undo-Verlauf nach dem Neuzeichnen neu beginnen."""
        self._restoring = True
        self.set_state(state, partial=True)            # Fenster bleibt, nur Tabs und ε (statt build_ui)
        QTimer.singleShot(200, self._after_load)

    def _after_load(self):
        self._restoring = False
        self._init_undo()

    def undo(self):
        path = self.active_reaction_path()
        if path: return path.undo(-1)
        tabs = (self.__dict__.get(self._tab_spec(k)[0]) for k in self._TAB_BUILD_ORDER)
        if any(hasattr(t, "timer") and t.timer.isActive() for t in tabs):
            self.push_undo()                           # Änderung, deren Vorschau noch aussteht: sonst ein Schritt zu weit
        if len(self._undo) > 1:
            self._redo.append(self._undo.pop())
            self._restore(self._undo[-1])

    def redo(self):
        path = self.active_reaction_path()
        if path: return path.undo(1)
        if self._redo:
            self._undo.append(self._redo.pop())
            self._restore(self._undo[-1])

    def active_reaction_path(self):
        page = self.__dict__.get('pub_page')
        center = self.__dict__.get('center')
        if page and center and center.currentWidget() is page and page.project_tabs.currentWidget() is page.paths_page:
            return page.path_workspace
        return None

    def _update_undo_actions(self):
        if hasattr(self, "act_undo"):
            path = bool(self.active_reaction_path())
            self.act_undo.setEnabled(path or len(self._undo) > 1)
            self.act_redo.setEnabled(path or bool(self._redo))

    def is_dirty(self):
        if self._restoring:
            return False
        return bool(self._undo) and self._undo[-1] != self._saved_snap

    _recent_filter, _recent_limit, _search_pub = "all", 20, None

    def _set_filter(self, b):
        self._recent_filter, self._recent_limit = b.property("filter"), 20
        if self.publication_dir:                        # Seitenleiste auf der Projektseite: zurück zur Übersicht
            self.go_home()
        else:
            self.fill_recent_list()

    def _more_recent(self):
        self._recent_limit += 20
        self.fill_recent_list()

    def _set_view(self, view):
        self.settings.setValue("welcome/view", view)
        self._sync_view_buttons(view)
        self.fill_recent_list()

    def _sync_view_buttons(self, view):
        for k, b in self.view_buttons.items():
            b.setChecked(k == view)

    def compound_infos(self, flt, index=None):
        """Verbindungen für die Liste des Startbildschirms, neueste zuerst: all = alle bekannten Projekte + zuletzt
        geöffnete, recent = zuletzt geöffnete, incomplete = Checkliste offen, sample = Substanz übrig."""
        from elucida.app import welcome as WEL
        from elucida.app import publication as PUB
        if flt == "recent":
            infos = [i for i in (WEL.project_info(p) for p in self.recent()) if i is not None]
            for info in infos:
                pub = PUB.publication_of(info["path"])
                if pub is not None:
                    info["publication"] = re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(pub))) or pub.name
            return infos
        infos = sorted(self.search_index() if index is None else index, key=lambda i: i["modified"], reverse=True)
        if flt == "incomplete":
            infos = [i for i in infos if i["check"]["missing"]]
        elif flt == "sample":
            infos = [i for i in infos if i.get("sample")]
        return infos

    def sidebar(self):
        """Linke Spalte von Übersicht und Projektseite: Filter der Verbindungen, Projekte, Hilfe, Erscheinungsbild."""
        from PySide6.QtWidgets import QButtonGroup
        from elucida.app import welcome as WEL
        side = QFrame(objectName="sideBar")
        side.setFixedWidth(WEL.SIDE_W)
        v = QVBoxLayout(side)
        # macOS: Ampelknöpfe liegen darüber. Windows/Linux: Marke ganz oben links auf der Höhe der Werkzeugleiste
        # (dort, wo unter macOS die Ampelknöpfe sitzen; Nutzerwunsch)
        v.setContentsMargins(10, 44 if self._mac_title else (STYLE.TOOLBAR_H - 26) // 2, 10, 12)
        v.setSpacing(2)
        if self._mac_title:
            side.installEventFilter(MAC.TitleDrag(self))
        brand = QHBoxLayout()
        brand.setContentsMargins(8, 0, 0, 0)
        brand.setSpacing(10)
        icon = self.app_icon()
        if icon.exists():
            lb = QLabel()
            lb.setPixmap(QIcon(str(icon)).pixmap(26, 26))
            brand.addWidget(lb)
        brand.addWidget(QLabel(APP_NAME, objectName="sideBrand"), 1)
        v.addLayout(brand)
        v.addSpacing(14)
        v.addWidget(QLabel(T("side_library"), objectName="sideCap"))
        self.grp_filter = QButtonGroup(self)
        self.grp_filter.setExclusive(False)               # keine Auswahl, wenn ein Projekt offen ist (_sync_side)
        for k, ic in zip(WELCOME_FILTERS, ("grid", "clock", "open_check", "flask")):
            b = WEL.SideRow(T("welcome_f_" + k), icon=ic)
            b.setProperty("filter", k)
            self.grp_filter.addButton(b)
            v.addWidget(b)
        self.grp_filter.buttonClicked.connect(self._set_filter)
        v.addSpacing(14)
        self.lbl_side_pubs = QLabel(T("welcome_publications"), objectName="sideCap")
        v.addWidget(self.lbl_side_pubs)
        inner = QWidget()
        self.side_pubs = QVBoxLayout(inner)
        self.side_pubs.setContentsMargins(0, 0, 0, 0)
        self.side_pubs.setSpacing(2)
        self.side_pubs.setAlignment(Qt.AlignTop)
        sa = QScrollArea()
        sa.setWidget(inner)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(sa, 1)
        dark = STYLE._mode == "dark"
        for text, ic, slot in ((T("side_quickstart"), "help", self.show_quickstart),
                               (T("side_demo"), "flask", self.open_demo_publication),
                               (T("welcome_theme_light" if dark else "welcome_theme_dark"), "theme",
                                lambda: self.switch_theme("light" if dark else "dark"))):
            b = WEL.SideRow(text, icon=ic, checkable=False)
            b.clicked.connect(lambda _=False, f=slot: f())
            v.addWidget(b)
        return side

    def welcome_page(self):
        """Übersicht: Verbindungen als Galerie oder Matrix (zuletzt geänderte zuerst, Rechtsklick-Menü). Suche, Ansicht,
        Öffnen und Neu sitzen in der Werkzeugleiste, Filter und Projekte in der Seitenleiste."""
        from PySide6.QtWidgets import QButtonGroup
        from elucida.app import welcome as WEL
        from elucida.app.publication_view import add_card
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(28, 24, 28, 12)
        v.setSpacing(2)
        self.lbl_recent = QLabel(objectName="pageTitle")
        v.addWidget(self.lbl_recent)
        self.lbl_recent_sub = QLabel(objectName="pageSub")
        v.addWidget(self.lbl_recent_sub)
        v.addSpacing(14)
        self.recent_box = WEL.Gallery()
        self.list_head = WEL.MatrixHeader()
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.addWidget(self.recent_box)
        self.btn_more = QPushButton(T("welcome_more"))
        self.btn_more.clicked.connect(self._more_recent)
        iv.addWidget(self.btn_more, 0, Qt.AlignHCenter)
        iv.addStretch(1)
        sa = QScrollArea()
        sa.setWidget(inner)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(sa, 1)
        self.lbl_recent_empty = QLabel(T("recent_none"), wordWrap=True, alignment=Qt.AlignCenter)
        self.lbl_recent_empty.setStyleSheet(HINT_CSS + " padding: 24px;")
        v.addWidget(self.lbl_recent_empty)
        self.add_compound = add_card(T("pub_new_compound"), T("welcome_add_hint"), WEL.CARD_H)
        self.add_compound.clicked.connect(lambda: self.new_project())
        self.add_compound.hide()
        # Werkzeugleiste
        self.ed_recent = QLineEdit(objectName="searchField")   # Suche über alle Verbindungen aller bekannten Projekte
        self.ed_recent.setPlaceholderText(T("welcome_search_ph"))
        self.ed_recent.setToolTip(T("recent_search_ph"))
        self.ed_recent.setClearButtonEnabled(True)
        self.ed_recent.setMinimumWidth(200)
        self.ed_recent.setFixedHeight(30)
        self.ed_recent.setMaximumWidth(420)
        self.ed_recent.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lupe = QLabel(self.ed_recent)                       # eigenes Symbol: genau mittig in der Höhe
        lupe.setPixmap(STYLE.pixmap("search", 16, STYLE.colors()["text2"]))
        lupe.setFixedSize(16, 16)
        lupe.move(10, 7)
        lupe.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.ed_recent.setTextMargins(22, 0, 0, 0)
        self.ed_recent.textChanged.connect(self._filter_recent)
        self._act_search = self.toolbar.insertWidget(self._tb_left, self.ed_recent)
        seg = QFrame(objectName="seg")
        seg.setFixedHeight(30)
        sg = QHBoxLayout(seg)
        sg.setContentsMargins(2, 2, 2, 2)
        sg.setSpacing(0)
        view = self.settings.value("welcome/view", "gallery")
        self.view_buttons = {}
        grp = QButtonGroup(seg)
        for k, key in (("gallery", "welcome_gallery"), ("list", "welcome_list")):
            b = QPushButton(T(key), objectName="segBtn", checkable=True)
            b.setFixedHeight(24)
            b.clicked.connect(lambda _=False, k=k: self._set_view(k))
            grp.addButton(b)
            sg.addWidget(b)
            self.view_buttons[k] = b
        self._sync_view_buttons(view)
        anchor = self._tb_edit[0]
        self._act_view = self.toolbar.insertWidget(anchor, seg)
        b_open = QPushButton(T("act_open_project"), objectName="barBtn")
        b_open.setFixedHeight(30)
        b_open.clicked.connect(self.open_project_dialog)
        self._act_open = self.toolbar.insertWidget(anchor, b_open)
        self.btn_new = QPushButton(T("welcome_new"), objectName="newBtn")
        self.btn_new.setFixedHeight(30)
        self.btn_new.setProperty("accent", True)
        m = QMenu(self.btn_new)
        m.setToolTipsVisible(True)
        for key, tip, fn in (("act_new_publication", "act_new_publication_tip", self.new_publication),
                             ("act_new_project", None, self.new_project), ("act_quick", "act_quick_tip", self.quick_evaluation)):
            a = m.addAction(T(key), lambda f=fn: f())
            if tip:
                a.setToolTip(T(tip))
        self.btn_new.setMenu(m)
        self._act_new = self.toolbar.insertWidget(anchor, self.btn_new)
        self.recent_rows = []
        self.pub_rows = []
        self.fill_recent_list()
        return page

    def _sync_side(self):
        """Markierung der Seitenleiste: der Filter oder das offene Projekt."""
        cur = Path(self.publication_dir).resolve() if self.publication_dir else None
        for b in self.grp_filter.buttons():
            b.setChecked(cur is None and b.property("filter") == self._recent_filter)
        for r in self.pub_rows:
            r.setChecked(cur is not None and Path(r.info["path"]).resolve() == cur)

    def _show_recent(self, infos, add=True):
        """Karten bzw. Zeilen der Verbindungen zeigen; add: dahinter die Karte „Neue Verbindung“."""
        from elucida.app import welcome as WEL
        for r in self.recent_rows:
            r.setParent(None)
            r.deleteLater()
        gallery = self.settings.value("welcome/view", "gallery") == "gallery"
        self.recent_rows = []
        for info in infos:
            row = (WEL.CompoundCard if gallery else WEL.RecentRow)(info)
            row.opened.connect(lambda p: self.open_project(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._recent_menu(r, pos))
            self.recent_rows.append(row)
        add = add and gallery
        table = not gallery and bool(infos)
        self.recent_box.set_single(table)
        self.list_head.setVisible(table)
        self.add_compound.setVisible(add)
        self.recent_box.set_items(([self.list_head] if table else []) + self.recent_rows + ([self.add_compound] if add else []))

    def fill_recent_list(self):
        """Übersicht neu füllen: Projekte und Zähler der Seitenleiste, Verbindungen des gewählten Filters."""
        if getattr(self, "recent_box", None) is None:
            return
        self._search_cache = None                       # Suche neu aufbauen (Liste hat sich geändert)
        self.lbl_recent_empty.setText(T("recent_none"))
        from elucida.app import welcome as WEL
        from elucida.app.publication_view import PublicationTile, publication_info
        for r in self.pub_rows:
            r.setParent(None)
            r.deleteLater()
        self.pub_rows = []
        pubs, seen = [], set()
        self._side_known = self.recent_publications()
        for p in self._side_known:                    # jeder Ordner einmal
            try:
                info = publication_info(p)
                key = Path(p).resolve()                # macOS: /var und /private/var sind derselbe Ordner
            except Exception:
                info = None
            if info is not None and key not in seen:
                seen.add(key)
                pubs.append(info)
        for info in pubs:
            row = PublicationTile(info)
            row.opened.connect(lambda p: self.open_publication(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._pub_menu(r, pos))
            self.side_pubs.addWidget(row)
            self.pub_rows.append(row)
        self.lbl_side_pubs.setVisible(bool(pubs))
        index = self.search_index()
        counts = dict(all=len(index), incomplete=sum(1 for i in index if i["check"]["missing"]),
                      sample=sum(1 for i in index if i.get("sample")),
                      recent=sum(1 for p in self.recent() if WEL.PRJ.is_project(p) is not None))
        for b in self.grp_filter.buttons():
            b.count.setText(str(counts[b.property("filter")]))
        self._sync_side()
        infos = self.compound_infos(self._recent_filter, index)
        self._show_recent(infos[:self._recent_limit])
        self.btn_more.setVisible(len(infos) > self._recent_limit)
        self.lbl_recent.setText(T("welcome_f_" + self._recent_filter))
        self.lbl_recent_sub.setText(T("welcome_count", n=len(infos)) if infos else "")
        self.lbl_recent_empty.setVisible(not infos)
        self._filter_recent(self.ed_recent.text())

    def focus_search(self):
        """Strg+F: in einem Projekt dessen Filter, sonst die Suche der Übersicht (offene Verbindung wird geschlossen
        – gespeichert ist sie ohnehin)."""
        if self.project_dir:
            self.go_home()
        self.ed_recent.setFocus()
        self.ed_recent.selectAll()

    def search_index(self):
        """Alle Verbindungen der bekannten Projekte und die zuletzt geöffneten (ohne doppelte) für die Suche."""
        from elucida.app import welcome as WEL
        from elucida.app import publication as PUB
        out, seen = [], set()

        def add(path, pub_title=""):
            try:
                key = Path(path).resolve()
            except OSError:
                return
            if key in seen:
                return
            info = WEL.project_info(path)
            if info is None:
                return
            seen.add(key)
            if not pub_title:
                pp = PUB.publication_of(path)
                pub_title = (re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(pp))) or pp.name) if pp else ""
            if pub_title:
                info["publication"] = pub_title
            out.append(info)
        for pub in self.recent_publications():
            if PUB.is_publication(pub) is None:
                continue
            title = re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(pub))) or Path(pub).name
            data_ = PUB.load(pub)
            for d in PUB.sync(pub)[0]:
                add(d, title)
                g_ = PUB.group_name(pub, d, data_)
                if g_ and out and Path(out[-1]["path"]).resolve() == d.resolve():
                    out[-1]["group"] = g_
        for r in self.recent():
            add(r)
        return out

    def _filter_recent(self, text):
        """Leer: Übersicht wie immer. Sonst Treffer aus allen Verbindungen aller bekannten Projekte (+ Projekte, deren
        Titel passt) statt der Listen."""
        from elucida.app import welcome as WEL
        if self.publication_dir and not self.project_dir and getattr(self, "pub_page", None) is not None:
            self.pub_page.ed_filter.setText(text)       # Projektseite: dieselbe Suche filtert die Verbindungen
            return
        t = text.strip()
        if not t:
            if getattr(self, "_searching", False):
                self._searching = False
                self._search_cache = None
                self.fill_recent_list()
            return
        if not getattr(self, "_searching", False) or getattr(self, "_search_cache", None) is None:
            self._search_cache = self.search_index()
        self._searching = True
        for r in self.pub_rows:
            r.setVisible(r.matches(t))
        self.lbl_side_pubs.setVisible(any(r.matches(t) for r in self.pub_rows))
        hits = [i for i in self._search_cache if WEL.info_matches(i, t)][:60]
        self._show_recent(hits, add=False)
        self.btn_more.setVisible(False)
        self.lbl_recent.setText(T("search_hits"))
        self.lbl_recent_sub.setText(str(len(hits)))
        self.lbl_recent_empty.setText(T("search_none"))
        self.lbl_recent_empty.setVisible(not hits)

    def _recent_menu(self, row, pos):
        p = row.info["path"]
        m = QMenu(self)
        m.addAction(T("act_open_project"), lambda: self.open_project(p))
        m.addAction(T("recent_reveal"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        m.addSeparator()
        if row.info.get("publication"):
            m.addAction(T("move_title"), lambda: self.move_compound(p))
            m.addAction(T("move_copy_title"), lambda: self.move_compound(p, copy=True))
        else:
            m.addAction(T("assign_title"), lambda: self.move_compound(p))
        m.addSeparator()
        m.addAction(T("recent_remove"), lambda: self.remove_recent(p))
        m.addAction(STYLE.icon("trash"), T("recent_trash"), lambda: self.trash_folder(p, publication=False))
        m.exec(row.mapToGlobal(pos))

    def _pub_menu(self, row, pos):
        p = row.info["path"]
        m = QMenu(self)
        m.addAction(T("act_open_project"), lambda: self.open_publication(p))
        m.addAction(T("recent_reveal"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        m.addSeparator()
        m.addAction(T("recent_remove"), lambda: self.remove_recent_publication(p))
        m.addAction(STYLE.icon("trash"), T("recent_trash"), lambda: self.trash_folder(p, publication=True))
        m.exec(row.mapToGlobal(pos))

    def remove_recent_publication(self, pdir):
        """Projekt aus der Liste nehmen (der Ordner bleibt unberührt)."""
        self.settings.setValue("recent_publications",
                               json.dumps([r for r in self.recent_publications() if r != str(pdir)]))
        self.fill_recent_list()

    @staticmethod
    def folder_stats(path):
        """-> (Dateien, Bytes) eines Ordners (für die Nachfrage vor dem Löschen)."""
        n = size = 0
        for f in Path(path).rglob("*"):
            if f.is_file():
                n += 1
                try:
                    size += f.stat().st_size
                except OSError:
                    pass
        return n, size

    def trash_folder(self, path, publication=False, confirm=True):
        """Verbindungs- oder Projektordner in den Papierkorb (nie endgültig löschen: Rohdaten). Vorher nachfragen
        (Ordner, Dateien, Größe; beim Projekt die Verbindungen darin – Verbindungen außerhalb bleiben). Offene
        Verbindung/offenes Projekt vorher schließen. -> True, wenn verschoben."""
        from PySide6.QtCore import QFile
        from elucida.app import publication as PUB
        p = Path(path)
        if not p.is_dir():
            self.remove_recent_publication(p) if publication else self.remove_recent(p)
            return False
        n, size = self.folder_stats(p)
        mb = f"{size / 1e6:.1f} MB"
        if publication:
            inside = [d for d in PUB.sync(p)[0] if p.resolve() in d.resolve().parents]
            names = ", ".join(PUB.compound_name(d) for d in inside) or "–"
            msg = T("trash_pub_q", p=str(p), n=n, size=mb, k=len(inside), names=names)
        else:
            msg = T("trash_q", p=str(p), n=n, size=mb)
        if confirm and QMessageBox.question(self, T("recent_trash"), msg, QMessageBox.Yes | QMessageBox.No,
                                            QMessageBox.No) != QMessageBox.Yes:
            return False
        cur = Path(self.project_dir).resolve() if self.project_dir else None
        if cur is not None and (cur == p.resolve() or p.resolve() in cur.parents):
            if self.close_project() is False:
                return False
        if self.publication_dir and Path(self.publication_dir).resolve() == p.resolve():
            self.close_publication()
        if not QFile.moveToTrash(str(p)):
            self.error(T("trash_failed", p=str(p)))
            return False
        if publication:
            self.remove_recent_publication(p)
        self.settings.setValue("recent_projects", json.dumps(
            [r for r in self.recent() if Path(r).resolve() != p.resolve() and p.resolve() not in Path(r).resolve().parents]))
        self.fill_recent_menu()
        self.fill_recent_list()
        self.log_signal.emit(T("trashed", p=str(p)))
        return True

    def thumb_structure(self):
        """Struktur fürs Vorschaubild: Verbindung des Projekts, sonst eine ε-Serie, sonst die des NMR-Tabs."""
        cands = [(self.compound or {}).get("structure")]
        cands += [st.get("structure") for st in self.series.values()]
        cands += [self.nmr_state.get("structure")]
        return next((p for p in cands if p and Path(p).exists()), None)

    def remove_recent(self, pdir):
        """Projekt aus der Liste nehmen (der Ordner bleibt unberührt)."""
        self.settings.setValue("recent_projects", json.dumps([r for r in self.recent() if r != str(pdir)]))
        self.fill_recent_menu()
        self.fill_recent_list()

    def open_demo_publication(self, folder=None):
        """Beispielpublikation mit zwei Verbindungen (künstliche Daten) anlegen und ihre Seite zeigen."""
        from elucida.app import demo as DEMO
        if not self.maybe_save():
            return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            d = DEMO.open_demo_publication(self, folder)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.log_signal.emit(traceback.format_exc())
            return self.error(str(e))
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(T("demo_pub_done", p=str(d)), 10000)
        return d

    def open_demo(self, folder=None):
        """Beispielprojekt mit künstlichen Daten (alle Tabs) anlegen und öffnen."""
        from elucida.app import demo as DEMO
        if not self.maybe_save():
            return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            d = DEMO.open_demo(self, folder)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.log_signal.emit(traceback.format_exc())
            return self.error(str(e))
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(T("demo_done", p=str(d)), 10000)
        return d

    def show_tab_guide(self):
        key = self._tab_keys[self.main_tabs.currentIndex()]
        QDesktopServices.openUrl(QUrl(TABS.guide_url(key)))

    # Maus im offenen Tab (dieselben Texte wie unter den Tabs); Synthese/NMR ohne Mausaktionen im Bild
    _MOUSE_HINTS = {"eps": ("drag_hint",), "hrms": ("ms_pick_hint", "drag_hint_tab"), "syn": (), "nmr": (),
                    "xray": ("xr_mouse_hint", "drag_hint_plain"), "dft": ("dft_mouse_hint", "drag_hint_plain"),
                    "other": ("drag_hint_plain",)}

    def shortcuts_html(self):
        """Hilfe → Maus und Tastenkürzel: Maus im offenen Tab + alle Kürzel aus den Menüaktionen (nie doppelt gepflegt)."""
        import html
        key = self._tab_keys[self.main_tabs.currentIndex()] if self.project_dir and self._tab_keys else None
        mouse = [T(k) for k in self._MOUSE_HINTS.get(key, ("drag_hint_tab",))] if key else []
        rows = []
        for m in self.menuBar().actions():
            for a in (m.menu().actions() if m.menu() else []):
                if not a.shortcut().isEmpty():
                    rows.append(f"<tr><td><b>{html.escape(a.shortcut().toString(QKeySequence.NativeText))}</b>"
                                f"&nbsp;&nbsp;</td><td>{html.escape(a.text().replace('&', ''))}</td></tr>")
        out = ""
        if mouse:
            out += f"<h4>{T('shortcuts_mouse')}</h4>" + "".join(f"<p>{html.escape(x)}</p>" for x in mouse)
        return out + f"<h4>{T('shortcuts_keys')}</h4><table>{''.join(rows)}</table>"

    def show_shortcuts(self):
        box = QMessageBox(QMessageBox.Information, T("act_shortcuts").rstrip("…"), self.shortcuts_html(), parent=self)
        box.setTextFormat(Qt.RichText)
        box.exec()

    def show_quickstart(self):
        url = (TABS.README_URL + TABS.MANUAL[get_lang()] + "#"
               + TABS.gh_anchor(T("readme_quickstart")))
        QDesktopServices.openUrl(QUrl(url))

    def _center_index(self):
        return 1 if self.project_dir else 2 if self.publication_dir else 0

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._mac_title and self._title_h is None:
            self._title_h = MAC.finish(self)
            self._fit_title_bar()

    def changeEvent(self, ev):
        super().changeEvent(ev)
        if ev.type() == QEvent.WindowStateChange and getattr(self, "_mac_title", False):
            self._fit_title_bar()

    def event(self, ev):
        # Der erste Zeicheneditor lässt Qt das native Fenster neu anlegen: Titelleiste neu einrichten, sonst fehlt sie.
        if ev.type() == QEvent.WinIdChange and getattr(self, "_mac_title", False) and self._title_h is not None:
            QTimer.singleShot(0, self._restore_title_bar)
        return super().event(ev)

    def _restore_title_bar(self):
        self._title_h = MAC.finish(self)
        self._fit_title_bar()

    def _fit_toolbar(self):
        """Eine Höhe auf allen Ebenen (macOS: Titelleiste, dort liegen die Ampelknöpfe). Qt nimmt den Innenrand für alle
        Seiten: so gewählt, dass die 30 px hohen Elemente genau mittig zwischen Fensterrand und Linie sitzen."""
        full = bool(self.windowState() & Qt.WindowFullScreen)
        h = self._title_h if self._mac_title and self._title_h and not full else STYLE.TOOLBAR_H
        # Knöpfe BAR_H hoch wie im Entwurf; die kompakte macOS-Titelleiste ist niedriger als dessen Leiste (die hohe
        # wäre 66 px): dort so hoch, dass oben und unten 4 px bleiben
        ch = min(STYLE.BAR_H, h - 8)
        ch -= (h - ch) % 2                                 # gerade Differenz: oben und unten gleich
        self.toolbar.setFixedHeight(h)
        self.toolbar.setStyleSheet(
            f"QToolBar {{ padding: {(h - ch) // 2 - 1}px; }} QToolButton#barTool, QPushButton#barBtn, QPushButton#newBtn, "
            f"QLineEdit#searchField {{ min-height: {ch - 2}px; max-height: {ch - 2}px; }} "
            f"QPushButton#segBtn {{ min-height: {ch - 6}px; max-height: {ch - 6}px; }}")

    def _fit_title_bar(self):
        """macOS: Werkzeugleiste so hoch wie die Titelleiste. Einzug auch im Vollbild: Fährt dort die Menüleiste ein,
        erscheinen die Ampelknöpfe über der Werkzeugleiste."""
        inset = getattr(self, "_title_inset", None)
        if inset is None or self._title_h is None:
            return
        full = bool(self.windowState() & Qt.WindowFullScreen)
        on = bool(self._title_h) and not full
        if self._title_h:
            MAC.set_toolbar_visible(self, not full)
        side = self.__dict__.get("side")                 # Seitenleiste sichtbar: Ampelknöpfe liegen auf ihr
        inset.setVisible(bool(self._title_h) and (side is None or side.isHidden()))
        # Genau die Titelleistenhöhe: macOS zentriert die Ampelknöpfe darin, sonst sitzen sie zu hoch.
        self._fit_toolbar()
        self._hide_native_title()

    def _hide_native_title(self):
        if self._mac_title and self._title_h:
            MAC.hide_title(self)

    def update_title(self):
        if getattr(self, "center", None) is not None:
            self.center.setCurrentIndex(self._center_index())
            if self._center_index() == 0:                # Liste nur lesen, wenn sie zu sehen ist
                self.fill_recent_list()
            elif self._center_index() == 2:              # Projektseite: Seitenleiste nur bei neuen Projekten neu aufbauen
                if self.recent_publications() != getattr(self, "_side_known", None):
                    self.fill_recent_list()
                self._sync_side()
        if getattr(self, "act_folder", None) is not None:
            self.act_folder.setEnabled(bool(self.project_dir))
        if getattr(self, "act_to_pub", None) is not None:
            self.act_to_pub.setEnabled(bool(self.publication_dir and self.project_dir))
        if getattr(self, "act_home", None) is not None:
            self.act_home.setEnabled(bool(self.project_dir or self.publication_dir))
        self._update_crumbs()
        if self.publication_dir and not self.project_dir:
            self.setWindowTitle(f"{self.publication_title()} – {T('app_title')} {APP_VERSION}")
            return
        name = Path(self.project_dir).name if self.project_dir else T("no_project_title")
        if self.compound.get("name"):
            name = f"{self.compound['name']} · {name}"
        if self.compound.get("note"):                  # Notiz zur Verbindung (z. B. „Radikalkation“)
            name = f"{name} ({self.compound['note']})"
        if self.publication_dir:                         # Teil einer Publikation
            name = f"{name} – {self.publication_title()}"
        self.setWindowTitle(f"{name} – {T('app_title')} {APP_VERSION}")

    # -- Verbindung des Projekts (Vorgabe für alle Tabs) ------------------------------------
    def edit_compound(self):
        """Tab „Verbindung“ zeigen (bis 2.7.1 ein Dialog; Nutzerwunsch: keine Popups)."""
        if not self.ensure_project():
            return
        self.main_tabs.setCurrentIndex(self._tab_keys.index("compound"))

    # -- ChemDraw: leere Vorlagen, bearbeiten, beim Speichern übernehmen ---------------------------------------
    def watch_chemdraw(self):
        """Vorlagen anlegen und Struktur/Schema der offenen Verbindung überwachen (auch außerhalb von Elucida
        bearbeitete CDXML werden übernommen)."""
        if self.cd_watch.files():
            self.cd_watch.removePaths(self.cd_watch.files())
        self._cd_kinds = {}
        if not self.project_dir:
            return
        try:
            s_t, sch_t = PRJ.ensure_templates(self.project_dir)
        except OSError as e:
            self.log_signal.emit(f"ChemDraw: {e}")
            return
        cur_s = self.compound.get("structure")
        cur_sch = self.syn_state.get("scheme")
        for p, kind in ((s_t, "structure"), (sch_t, "scheme"), (cur_s, "structure"), (cur_sch, "scheme")):
            if p and Path(p).suffix.lower() == ".cdxml" and Path(p).exists():
                self._cd_kinds[str(Path(p).resolve())] = kind
                self.cd_watch.addPath(str(Path(p).resolve()))

    def chemdraw_file(self, kind):
        """CDXML zum Bearbeiten: die der Verbindung bzw. des Schemas, sonst die leere Vorlage."""
        s_t, sch_t = PRJ.ensure_templates(self.project_dir)
        cur = self.compound.get("structure") if kind == "structure" else self.syn_state.get("scheme")
        if cur and Path(cur).suffix.lower() == ".cdxml" and Path(cur).exists():
            return Path(cur)
        return s_t if kind == "structure" else sch_t

    def edit_in_elucida(self, kind):
        if not self.ensure_project():
            return
        from elucida.app.drawing_editor import DrawingEditor, DrawingDialog
        dlg = DrawingDialog(self)
        dlg.setWindowTitle(T("draw_title"))
        dlg.resize(1250, 850)
        layout = QVBoxLayout(dlg)
        editor = DrawingEditor(dlg, scheme_actions=False)
        editor.set_canvas_dark(self.canvas_is_dark())
        editor.external_requested.connect(lambda: self.edit_in_chemdraw(kind))
        layout.addWidget(editor)
        dlg.editor = editor
        path = self.chemdraw_file(kind)
        editor.open_path(path)
        dlg.exec()
        self.chemdraw_saved(str(path))
        dlg.deleteLater()

    def save_drawings(self):
        for attr in ("comp_tab", "syn_tab"):
            editor = getattr(self.__dict__.get(attr), "drawing_editor", None)
            if editor is not None and editor.dirty and not editor.save_sync(): return False
        page = self.__dict__.get('pub_page')
        return page is None or page.save_paths()

    def edit_in_chemdraw(self, kind):
        """CDXML in ChemDraw (Standardprogramm für .cdxml) öffnen; beim Speichern übernimmt Elucida sie selbst."""
        if not self.ensure_project():
            return None
        p = self.chemdraw_file(kind)
        key = str(p.resolve())
        self._cd_kinds[key] = kind
        if key not in self.cd_watch.files():
            self.cd_watch.addPath(key)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(key)):
                self.error(T("chemdraw_open_failed", p=key))
                return None
        self.statusBar().showMessage(T("chemdraw_opened", name=p.name), 8000)
        return p

    def _cd_changed(self, path):
        self._cd_pending.add(path)
        self.cd_timer.start()

    def _cd_apply_pending(self):
        for p in list(self._cd_pending):
            self._cd_pending.discard(p)
            self.chemdraw_saved(p)

    def chemdraw_saved(self, path, quiet=False):
        """In ChemDraw oder im Zeichner gespeichert: Struktur (Formel, Molmasse, Bilder) bzw. Schema neu übernehmen. Leere
        Vorlagen zählen nicht. ChemDraw ersetzt die Datei beim Speichern – dann wieder überwachen. Summenformel und
        Molmasse folgen der Zeichnung, außer sie wurden von Hand geändert (weichen von dem ab, was die Zeichnung zuletzt
        ergab, `_drawn`; unbekannt = übernehmen). quiet: ohne Einblendung (der Zeichner meldet das Speichern selbst)."""
        key = str(Path(path).resolve())
        if Path(key).exists() and key not in self.cd_watch.files():
            self.cd_watch.addPath(key)
        if not self.project_dir or not PRJ.cdxml_has_content(key):
            return False
        kind = self._cd_kinds.get(key, "structure")
        if kind == "scheme":
            self.syn_tab.set_scheme(key)
        else:
            stamp = Path(key).stat().st_mtime_ns          # Zeichner und Dateiüberwachung melden dasselbe Speichern
            if self._taken == (key, stamp):
                return True
            self._taken = (key, stamp)
            comp = dict(self.compound)
            comp["structure"] = key
            new, was = compound_from_structure(key), self._drawn.get(key)
            for k, v in new.items():
                if v and (was is None or not comp.get(k) or comp.get(k) == was.get(k)):
                    comp[k] = v
            self._drawn[key] = new
            self.set_compound(comp)
        if not quiet:
            self.statusBar().showMessage(T("chemdraw_taken", name=Path(key).name), 6000)
            self.log_signal.emit(T("chemdraw_taken", name=Path(key).name))
        return True

    def set_compound(self, comp):
        """Verbindung übernehmen und als Vorgabe eintragen, wo noch nichts gewählt ist."""
        comp = dict(comp)
        if comp.get("structure") and self.project_dir:
            comp["structure"] = self.import_file(comp["structure"], PRJ.STRUCTURES)
        old, self.compound = self.compound, comp
        paths = {old.get("structure"), comp.get("structure")} - {None}
        for k in [k for k in self.extra_cache if isinstance(k, tuple) and paths.intersection(k)]:
            del self.extra_cache[k]                    # Zeichnung am selben Pfad geändert: Tabs laden sie neu
        replaced = self.apply_compound_defaults(old)
        self.apply_series_widgets()
        if replaced:                                    # nichts still überschreiben: ε der Serie ändert sich damit
            g, was, now = replaced[0]
            self.statusBar().showMessage(T("compound_mw_replaced", s=g, old=f"{was:.2f}", new=f"{now:.2f}",
                                           more=T("compound_mw_more", n=len(replaced) - 1) if len(replaced) > 1 else ""), 10000)
        self.update_title()
        for key in self._TAB_BUILD_ORDER:              # ungebaute Tabs lesen die Verbindung beim Bauen
            if self._built(key):
                getattr(self, self._tab_spec(key)[0]).compound_changed()
        self.render()
        self.push_undo()

    def apply_compound_defaults(self, old=None, only_empty=False):
        """ε-Serien und der Fluoreszenz-Tab folgen **immer** der Verbindung (Nutzerwunsch 2026-11-10): Molmasse und
        Struktur der Verbindung ersetzen, was dort steht, auch eigene oder von Hand eingetragene Werte. Nennt die
        Verbindung keinen Wert, bleibt der des Tabs. only_empty (Messdaten laden, damit auch das Öffnen einer
        gespeicherten Verbindung): nur leere Werte füllen – gespeicherte Auswertungen ändern sich erst, wenn die
        Verbindung geändert wird. -> ersetzte abweichende Molmassen [(Serie, alt, neu)]."""
        c = self.compound
        p = c.get("structure")
        replaced = []
        for g, st in self.series.items():
            if c.get("mw") and not (only_empty and st.get("mw")):
                if st.get("mw") and abs(st["mw"] - c["mw"]) >= 0.005:
                    replaced.append((g, st["mw"], c["mw"]))
                st["mw"] = c["mw"]
            if p and Path(p).exists() and not (only_empty and st.get("structure")) and not st.get("no_structure"):   # Molmasse der Verbindung gilt vor der Zeichnung
                self.set_structure(p, g, render=g == self.current, autofill_mw=not st.get("mw"))
        if p and Path(p).exists() and not (only_empty and self.fl_state.get("structure")):
            self.fl_state["structure"] = p
            if self._built("fluo"):
                self.fl_tab.lbl_struct.setText(Path(p).name)
                self.fl_tab.timer.start()
        return replaced

    # -- Projektordner zuerst: Dateien werden beim Laden kopiert, Änderungen automatisch gespeichert
    def ensure_project(self):
        if self.project_dir:
            return True
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return False
        if QMessageBox.question(self, T("app_title"), T("need_project_q")) != QMessageBox.Yes:
            return False
        return self.new_project()                      # jede Verbindung gehört zu einem Projekt

    def create_project(self, d):
        try:
            pdir = PRJ.create(d)
        except OSError as e:
            self.error(str(e))
            return False
        self.project_dir = str(pdir)
        from elucida.app import publication as PUB
        pub = PUB.publication_of(pdir)
        self.publication_dir = str(pub) if pub else None
        self.settings.setValue("last_project_dir", str(pdir.parent))
        self._load_state_into_ui({"tab": "compound"})  # neue Verbindung: zuerst benennen und zeichnen
        self.watch_chemdraw()                          # leere ChemDraw-Dateien für Struktur und Schema
        self.update_title()
        self.add_recent(pdir)
        self.log_signal.emit(T("project_created", p=pdir))
        return True

    def export_name(self):
        """Name in Exportdateien: Verbindung des Projekts, sonst der Projektordner."""
        return self.compound.get("name") or Path(self.project_dir or ".").resolve().name

    def cache_dir(self, path):
        """Cache für freigestellte Fotos: im Projekt .elucida/cache, sonst neben der Datei (wie bis 2.0)."""
        if self.project_dir:
            return PRJ.work_dir(self.project_dir, "cache")
        return Path(path).parent / ".uvvis_cache"

    def import_file(self, path, sub, name=None):
        if not self.project_dir:
            return str(Path(path).resolve())
        new = PRJ.import_file(self.project_dir, path, sub, name)
        if Path(new) != Path(path).resolve():
            self.log_signal.emit("  " + T("file_imported", src=Path(path).name, dst=Path(new).relative_to(
                self.project_dir).as_posix()))
        return new

    def _flush_edits(self):
        """Laufende Eingabe übernehmen (Strg+S/Schließen verschieben den Fokus nicht): verzögerte Texte (Vorschrift,
        NMR-Text) zuerst – Feld-Handler ziehen Bedienelemente aus dem Zustand nach –, dann das Feld mit Fokus (Fokus
        weg: editingFinished, Tabelleneditor übernimmt), dann ausstehendes Neuzeichnen (legt den Undo-Schritt an)."""
        tabs = {k: self.__dict__.get(self._tab_spec(k)[0]) for k in self._TAB_BUILD_ORDER}
        for key, timer, slot in (("syn", "timer", "proc_changed"), ("nmr", "text_timer", "text_changed")):
            if tabs[key] is not None and getattr(tabs[key], timer).isActive():
                getattr(tabs[key], timer).stop()
                getattr(tabs[key], slot)()
        w = QApplication.focusWidget()
        if isinstance(w, QLineEdit) and w.window() is self:
            w.clearFocus()
            if w.isVisible():                          # Cursor bleibt im Feld (Tabelleneditor ist danach zu)
                w.setFocus()
        for tab in [self] + [t for k, t in tabs.items() if t is not None and k != "syn"]:
            t = getattr(tab, "timer", None)
            if isinstance(t, QTimer) and t.isActive():
                t.stop()
                tab.render()

    def maybe_save(self):
        """Vor Neu/Öffnen/Schließen: ausstehendes automatisches Speichern sofort ausführen."""
        if not self.save_drawings():
            return False
        self._flush_edits()
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self.autosave()
        return True

    def autosave(self, force=False):
        """Projekt speichern. Automatisch nicht während eines Ladevorgangs (_restoring: halb gesetzter Zustand);
        force (ausdrückliches Speichern, Beispielprojekt): Zustand ist vollständig gesetzt, immer speichern."""
        if not self.project_dir or (self._restoring and not force):
            return
        try:
            PRJ.write(self.project_dir, self.get_state())
            from elucida.app import welcome as WEL       # Strukturbild für den Startbildschirm (nur wenn neuer)
            WEL.write_thumb(self.project_dir, self.thumb_structure(), self.log_signal.emit)
            self._update_nav_dots()
            self._saved_snap = self._undo[-1] if self._undo else None
            self.statusBar().showMessage(T("autosaved"), 2000)
        except Exception as e:
            self.log_signal.emit(f"{T('err_title')}: {e}")

    def new_project(self):
        """Neue Verbindung – immer in einem Projekt (Nutzerwunsch): im offenen Projekt, sonst Projekt wählen/anlegen."""
        if not self.maybe_save():
            return False
        if not self.publication_dir:
            pub = self.choose_publication(T("choose_pub_new"))
            if pub is None:
                return False
            self.open_publication(pub)
        return self.new_compound_in_publication()

    def choose_publication(self, title, exclude=None):
        """Projekt wählen: zuletzt geöffnete, „Anderes Projekt öffnen …“ oder „Neues Projekt …“. -> Ordner oder None."""
        from elucida.app import publication as PUB
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(560, 380)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(T("choose_pub_hint"), wordWrap=True))
        lst = QListWidget()
        ex = Path(exclude).resolve() if exclude else None
        for p in self.recent_publications():
            if PUB.is_publication(p) is None or (ex is not None and Path(p).resolve() == ex):
                continue
            title_ = re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(p))) or Path(p).name
            it = QListWidgetItem(f"{title_}\n{p}")
            it.setData(Qt.UserRole, p)
            lst.addItem(it)
        lst.itemDoubleClicked.connect(lambda *_: dlg.accept())
        if lst.count():
            lst.setCurrentRow(0)
        v.addWidget(lst, 1)
        chosen = {}

        def other(new):
            d = QFileDialog.getExistingDirectory(dlg, T("act_new_publication") if new else T("act_open_project"),
                                                 self.settings.value("last_project_dir", str(Path.home())))
            if not d:
                return
            if new:
                if PRJ.is_project(d):
                    return self.error(T("pub_is_project"))
                PUB.create(d)
            elif PUB.is_publication(d) is None:
                return self.error(T("no_project", p=d))
            chosen["p"] = d
            dlg.accept()
        row = QHBoxLayout()
        b_open = QPushButton(STYLE.icon("open"), T("choose_pub_other"))
        b_open.clicked.connect(lambda: other(False))
        b_new = QPushButton(STYLE.icon("new"), T("act_new_publication"))
        b_new.clicked.connect(lambda: other(True))
        row.addWidget(b_open)
        row.addWidget(b_new)
        row.addStretch(1)
        v.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return None
        if "p" in chosen:
            return Path(chosen["p"])
        it = lst.currentItem()
        return Path(it.data(Qt.UserRole)) if it is not None else None

    def move_compound(self, cdir=None, copy=False, target=None):
        """Verbindung in ein anderes Projekt verschieben oder dorthin kopieren (dieselbe Verbindung in zwei Papern; die
        Kopie ist danach unabhängig). Ohne Projekt: einem Projekt zuordnen. -> neuer Ordner oder None."""
        from elucida.app import publication as PUB
        cdir = Path(cdir or self.project_dir or "")
        if PRJ.is_project(cdir) is None:
            return None
        src = PUB.publication_of(cdir)
        if target is None:
            title = T("move_copy_title" if copy else ("move_title" if src else "assign_title"))
            target = self.choose_publication(title, exclude=None if copy else src)
            if target is None:
                return None
        was_open = bool(self.project_dir) and Path(self.project_dir).resolve() == cdir.resolve()
        if was_open and not copy:
            if self.close_project() is False:
                return False
        else:
            if not self.maybe_save():
                return False
        try:
            new = PUB.copy_compound_to(cdir, target) if copy else PUB.move_compound_to(cdir, target)
        except OSError as e:
            self.error(f"{type(e).__name__}: {e}")
            if was_open and not copy:
                self.open_project(cdir, ask=False)
            return None
        if not copy:                                   # Listen auf den neuen Ort umstellen
            self.settings.setValue("recent_projects", json.dumps(
                [str(new) if Path(r).resolve() == cdir.resolve() else r for r in self.recent()]))
        self.add_recent_publication(target)
        self.log_signal.emit(T("compound_copied" if copy else "compound_moved", src=str(cdir), dst=str(new)))
        if was_open and not copy:
            self.open_project(new, ask=False)
        if self.publication_dir and not self.project_dir:
            self.pub_page.refresh()
        self.fill_recent_menu()
        self.fill_recent_list()
        self.update_title()
        return new

    def open_project_dialog(self):
        if not self.maybe_save():
            return False
        d = QFileDialog.getExistingDirectory(self, T("act_open_project"),
                                             self.settings.value("last_project_dir", str(Path.home())))
        if not d:
            return
        from elucida.app import publication as PUB
        if PRJ.is_project(d):
            self.open_project(d, ask=False)
        elif PUB.is_publication(d):
            self.open_publication(d)
        elif QMessageBox.question(self, T("app_title"), T("make_project_q", p=d)) == QMessageBox.Yes:
            self.create_project(d)

    def open_project(self, path, ask=True, recent=True):
        pdir = PRJ.is_project(path)
        if pdir is None:
            self.error(T("no_project", p=path))
            return False
        if not self.maybe_save():
            return False
        try:
            PRJ.backup(pdir)                           # Sicherung: .elucida/project.elucida.bak
            state = PRJ.load(pdir)
        except Exception as e:
            self.error(f"{type(e).__name__}: {e}")
            return False
        for m in PRJ.missing_files(state):
            self.log_signal.emit("  " + T("missing_file", p=m))
        self.project_dir = str(pdir)
        from elucida.app import publication as PUB
        pub = PUB.publication_of(pdir)
        self.publication_dir = str(pub) if pub else None
        self._load_state_into_ui(state)
        self.watch_chemdraw()
        if recent:
            self.add_recent(pdir)
            self.settings.setValue("last_project_dir", str(pdir.parent))
        self.update_title()
        from elucida.app import demo as DEMO
        if pub is None and ask and recent and not DEMO.is_demo(pdir) and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QTimer.singleShot(0, self._ask_assign)     # jede Verbindung gehört zu einem Projekt (Nutzerwunsch)
        return True

    def _ask_assign(self):
        if self.project_dir and not self.publication_dir and \
                QMessageBox.question(self, T("app_title"), T("orphan_q")) == QMessageBox.Yes:
            self.move_compound()

    def save_project(self):
        if not self.project_dir and self.publication_dir:
            return self.save_drawings()
        if not self.project_dir:
            return self.ensure_project()
        if not self.save_drawings():
            return False
        self._flush_edits()
        self.autosave_timer.stop()
        self.autosave(force=True)                      # auch direkt nach dem Laden (Beispielprojekt), sonst leer
        return True

    def save_project_copy(self):
        """Projekt (inkl. aller Dateien) als Kopie in einen neuen Ordner schreiben, z. B. als Zwischenstand."""
        if not self.project_dir:
            return self.error(T("load_first"))
        d = QFileDialog.getExistingDirectory(self, T("act_save_copy"), str(Path(self.project_dir).parent))
        if d:
            from elucida.app import publication as PUB
            if PRJ.is_project(d) or PUB.is_publication(d):    # nie über Verbindung/Projekt
                return self.error(T("copy_target_used", p=d))
            return self._write_project(Path(d), switch=False)
        return False

    def _write_project(self, pdir: Path, switch=True):
        try:
            abs_state = PRJ.save(pdir, self.get_state())
        except Exception as e:
            self.error(f"{type(e).__name__}: {e}")
            return False
        if switch:
            self.project_dir = str(pdir)
            self._load_state_into_ui(abs_state)
            self.add_recent(pdir)
        self.log_signal.emit(T("project_saved", p=pdir))
        return True

    def show_project_folder(self):
        if self.project_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_dir))

    def add_recent(self, pdir):
        from elucida.app import demo as DEMO
        if DEMO.is_demo(pdir):                         # Beispiele nach dem Ansehen nicht in der Übersicht
            return
        rec = [str(pdir)] + [r for r in self.recent() if r != str(pdir)]
        self.settings.setValue("recent_projects", json.dumps(rec[:20]))
        self.fill_recent_menu()

    # -- Publikation (elucida/app/publication.py) ------------------------------------------
    def publication_title(self):
        from elucida.app import publication as PUB
        if not self.publication_dir:
            return ""
        return re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(self.publication_dir))) or \
            Path(self.publication_dir).name

    def recent_publications(self):
        from elucida.app import demo as DEMO
        try:
            rec = list(json.loads(self.settings.value("recent_publications", "[]") or "[]"))
        except Exception:
            return []
        return [r for r in rec if not DEMO.is_demo(r)]

    def add_recent_publication(self, pdir):
        from elucida.app import demo as DEMO
        if DEMO.is_demo(pdir):
            return
        rec = [str(pdir)] + [r for r in self.recent_publications() if r != str(pdir)]
        self.settings.setValue("recent_publications", json.dumps(rec[:10]))

    def new_publication(self):
        """Ordner wählen (leer oder mit vorhandenen Verbindungsprojekten) und zur Publikation machen."""
        from elucida.app import publication as PUB
        d = QFileDialog.getExistingDirectory(self, T("act_new_publication"),
                                             self.settings.value("last_project_dir", str(Path.home())))
        if not d:
            return False
        if PRJ.is_project(d):
            self.error(T("pub_is_project"))
            return False
        try:
            PUB.create(d)
        except (OSError, ValueError) as e:
            self.error(str(e))
            return False
        self.open_publication(d)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.pub_page.edit_info()
        return True

    def open_publication(self, path):
        from elucida.app import publication as PUB
        pdir = PUB.is_publication(path)
        if pdir is None:
            self.error(T("no_project", p=path))
            return False
        if not self.maybe_save(): return False
        if self.project_dir:
            if self.close_project() is False:
                return False
        if not self.pub_page.set_publication(pdir): return False
        self.publication_dir = str(pdir)
        self.add_recent_publication(pdir)
        self.update_title()
        return True

    def close_project(self):
        """Verbindung schließen (gespeichert wird automatisch) – zurück zur Publikation bzw. zum Startbildschirm."""
        if not self.maybe_save():
            return False
        self.project_dir = None
        self._load_state_into_ui({})
        self.watch_chemdraw()                          # nichts mehr überwachen
        self.update_title()

    def close_publication(self):
        if not self.pub_page.close_path(): return False
        self.publication_dir = None
        self.pub_page.set_publication(None)
        self.update_title()

    def _crumb_pub(self):
        if self.pub_page.path_workspace:
            self.pub_page.close_path()
        elif self.publication_dir:
            self.go_publication()
        else:
            self.move_compound()                       # „⚠ ohne Projekt“: einem Projekt zuordnen

    def _update_crumbs(self):
        """Werkzeugleiste und Seitenleiste je Ebene: Übersicht/Projekt oder Arbeit (Verbindung, offener Pfad)."""
        if getattr(self, "btn_home", None) is None:
            return
        page = self.__dict__.get("pub_page")
        path = page.path_workspace if page is not None else None
        work = bool(self.project_dir or path)
        self.act_crumbs.setVisible(work)
        for a_ in self._tb_edit + [self._sep_compound]:
            a_.setVisible(bool(self.project_dir))
        self.act_si.setVisible(bool(self.project_dir))
        if getattr(self, "canvas_toggle", None) is not None:
            self.canvas_toggle.setVisible(work)
        self._tb_theme.setVisible(work)
        for a_ in (self._act_search, self._act_open, self._act_new):
            a_.setVisible(not work)
        self._act_view.setVisible(not work and not self.publication_dir)
        self.side.setVisible(not work)
        self._fit_title_bar()
        self._fit_toolbar()
        if self.publication_dir != self._search_pub:              # neue Seite: Suche beginnt leer
            self._search_pub = self.publication_dir
            if self.ed_recent.text():
                self.ed_recent.setText("")
            if page is not None:
                page.ed_filter.setText("")
        if self.project_dir != self._dots_dir and self.project_dir:
            self._update_nav_dots()
        from elucida.app import demo as DEMO
        on = bool(self.publication_dir and self.project_dir)
        orphan = bool(self.project_dir and not self.publication_dir and not DEMO.is_demo(self.project_dir))
        self.crumb_seps[0].setVisible(on or orphan or bool(path))
        self.btn_pub.setVisible(on or orphan or bool(path))
        for w_ in (self.crumb_seps[1], self.btn_comp):
            w_.setVisible(on or bool(path))
        if orphan:
            self.btn_pub.setText("⚠ " + T("nav_no_project"))
            self.btn_pub.setToolTip(T("assign_title"))
        if on or path:
            t_ = self.publication_title()
            self.btn_pub.setText(t_ if len(t_) <= 44 else t_[:42] + " …")      # erst kürzen, wenn es wirklich lang ist
            self.btn_pub.setToolTip(T("act_to_publication") + ": " + t_)
            self.btn_comp.setText(path.item["name"] if path and not on else self.export_name())
        if self.project_dir:                                # Tab „Verbindung“: Nummer (SI, sonst Laborbuch) · Summenformel
            c_ = self.compound
            self.nav_buttons[self._tab_keys.index("compound")].set_compound(
                c_.get("name") or c_.get("labbook") or self.export_name(), c_.get("formula"))

    def _update_nav_dots(self):
        """Punkt am Tab, wenn dort Daten liegen (aus der gespeicherten Projektdatei)."""
        from elucida.app import welcome as WEL
        self._dots_dir = self.project_dir
        info = WEL.project_info(self.project_dir) if self.project_dir else None
        have = {WEL.TAB_OF[k] for k in info["badges"]} if info else set()
        for i, b in self.nav_buttons.items():
            if self._tab_keys[i] != "compound":           # NameTab: hell, sobald es eine Summenformel gibt
                b.set_data(self._tab_keys[i] in have)
        self.sync_main_button()

    def _fill_comp_menu(self):
        """Verbindungen des Projekts zum direkten Wechseln (die offene abgehakt); offener Pfad: die Pfade."""
        from elucida.app import publication as PUB
        self.comp_menu.clear()
        if not self.publication_dir:
            return
        if self.pub_page.path_workspace:
            cur_ = self.pub_page.path_workspace.item["uid"]
            for it in PUB.load(self.publication_dir).get("reaction_paths", []):
                act = self.comp_menu.addAction(it["name"])
                act.setCheckable(True)
                act.setChecked(it["uid"] == cur_)
                act.triggered.connect(lambda _=False, it=it: self.pub_page.open_path(it))
            return
        cur = Path(self.project_dir).resolve() if self.project_dir else None
        for d in PUB.sync(self.publication_dir)[0]:
            act = self.comp_menu.addAction(PUB.compound_name(d))
            act.setCheckable(True)
            act.setChecked(d.resolve() == cur)
            act.triggered.connect(lambda _=False, d=d: d.resolve() != cur and self.open_project(d))
        self.comp_menu.addSeparator()
        self.comp_menu.addAction(T("pub_new_compound") + " …", self.new_compound_in_publication)
        self.comp_menu.addAction(T("move_title"), lambda: self.move_compound())
        self.comp_menu.addAction(T("move_copy_title"), lambda: self.move_compound(copy=True))

    def go_home(self):
        """Zur Übersicht (Startbildschirm): offene Verbindung und Projekt schließen (gespeichert wird automatisch)."""
        if self.project_dir:
            if self.close_project() is False:
                return False
        if self.publication_dir:
            if self.close_publication() is False: return False
        self.update_title()

    def go_publication(self):
        if self.publication_dir:
            self.open_publication(self.publication_dir)

    def new_compound_in_publication(self, name=None):
        """Neue Verbindung als Unterordner der Publikation; Name = Ordner und Verbindung des Projekts."""
        from elucida.app import publication as PUB
        if not self.publication_dir:
            return False
        if not isinstance(name, str):   # Qt-Signale übergeben sonst checked (bool) als Namen
            name, ok = QInputDialog.getText(self, T("pub_new_compound"), T("pub_new_compound_q"))
            if not ok:
                return False
        name = name.strip()
        if not name:
            return False
        d = Path(self.publication_dir) / core.safe_name(name)
        if PRJ.is_project(d):
            return self.open_project(d)
        if not self.create_project(d):
            return False
        PUB.add_compound(self.publication_dir, d)
        self.set_compound({**self.compound, "name": name})
        self.save_project()
        return True

    def export_publication_si(self, pdir, compounds, sections, toc=True, methods=True, path=None, template="group"):
        """Gesamt-SI (elucida/si/publication_si.py): jede Verbindung kurz öffnen, ihre Blöcke je Kapitel sammeln,
        danach die vorher offene Verbindung wiederherstellen. -> Pfad der Word-Datei."""
        from elucida.app import publication as PUB
        from elucida.si import publication_si as PSI
        if not self.maybe_save():
            return False
        prev = self.project_dir
        comps = []
        dlg = QProgressDialog(T("pub_si_writing"), T("cancel"), 0, len(compounds), self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(300)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for i, d in enumerate(compounds):
                dlg.setValue(i)
                dlg.setLabelText(T("pub_si_compound", name=PUB.compound_name(d)))
                QApplication.processEvents()
                if dlg.wasCanceled():
                    return None
                if not self.open_project(d, recent=False):
                    continue
                try:
                    name_, parts_ = self.si_compound_parts(sections, methods)
                    parts_["_group"] = PUB.group_name(pdir, d)     # Unterkapitel je Gruppe
                    parts_["_gp"] = self.syn_tab.st.get("gp") or None  # allgemeine Vorschrift (einmal vor der ersten)
                    comps.append((name_, parts_))
                except Exception:
                    self.log_signal.emit(traceback.format_exc())
        finally:
            if prev:
                self.open_project(prev, recent=False)
            else:
                self.close_project()
                self.open_publication(pdir)
            QApplication.restoreOverrideCursor()
            dlg.close()
        meta = PUB.load(pdir)
        setup = [str(self.settings.value(f"si_setup/{k}", "") or "").strip() for k in PSI.SETUP_KEYS]
        paths = []
        if "dft" in sections and meta.get("reaction_paths") and (meta.get("reaction_paths_si") or {}).get("include") is not False:
            from elucida.app.reaction_paths import si_blocks
            try:
                paths = si_blocks(self, pdir)
            except Exception as ex:
                self.error(str(ex))
                return None
        blocks = PSI.assemble(meta, comps, sections, setup, toc=toc, methods=methods, reaction_paths=paths)
        name = core.safe_name(Path(pdir).name)
        path = Path(path) if path else Path(pdir) / PUB.SI_DIR / f"{name}_SI.docx"
        SI.set_template(template, page_numbers=True)    # nur für diese Datei (Einzel-SI bleibt wie die Gruppe)
        try:
            SI.write_docx(path, blocks)
        except PermissionError:
            self.error(T("report_locked", p=str(path)))
            return None
        finally:
            SI.set_template("group")
        self.exported([path.parent])
        return path

    def recent(self):
        from elucida.app import demo as DEMO
        try:
            return [r for r in json.loads(self.settings.value("recent_projects", "[]") or "[]") if not DEMO.is_demo(r)]
        except Exception:
            return []

    def fill_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        rec = [r for r in self.recent() if PRJ.is_project(r)]
        for r in rec:
            act = QAction(f"{Path(r).name}  –  {Path(r).parent}", self)
            act.triggered.connect(lambda _=False, r=r: self.open_project(r))
            self.recent_menu.addAction(act)
        self.recent_menu.setEnabled(bool(rec))

    def series_changed(self, g):
        if not g or g not in self.series:
            return
        self.current = g
        self.apply_series_widgets()
        self.render()

    def changed(self, *_):
        if self._loading:
            return
        self.collect_globals()
        manual = self.glob["baseline"] == "manual"
        self.sp_bla.setEnabled(manual)
        self.sp_blb.setEnabled(manual)
        self.cb_tab.setEnabled(self.glob.get("inset", True))
        self.timer.start()

    def mw_edited(self):
        if self._loading or not self.current:
            return
        try:
            self.series[self.current]["mw"] = parse_float(self.ed_mw.text())
        except ValueError:
            self.ed_mw.setText("")
            self.series[self.current]["mw"] = None
        self.apply_series_widgets()                 # Warnung zur Molmasse sofort aktualisieren
        self.timer.start()

    # ------------------------------------------------------- Struktur/Foto
    def structure_toggled(self, on):
        """„Struktur im Bild“: Struktur der Verbindung in dieser Serie zeigen oder weglassen (bleibt abgewählt, auch wenn
        die Verbindung später geändert wird)."""
        if self._loading or not self.current:
            return
        st = self.series[self.current]
        st["no_structure"] = not on
        p = self.compound.get("structure") or st.get("structure")
        self.set_structure(p if on and p and Path(p).exists() else None)

    def choose_structure(self):
        if not self.current:
            return self.error(T("load_first"))
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_structure(p)

    def set_structure(self, path, g=None, render=True, sync=False, autofill_mw=True):
        g = g or self.current
        st = self.series[g]
        if path is not None and self.project_dir:
            path = self.import_file(path, PRJ.STRUCTURES)
        if path is None:
            st.update(structure=None, structure_asset=None, chem_info="", chem_warn=False)
            self.apply_series_widgets()
            return self.render()

        def work():
            asset = IMG.load_structure(path)
            p = Path(path)
            if asset["mw"] is None and p.suffix.lower() != ".cdxml":
                sib = p.with_suffix(".cdxml")            # gleichnamige CDXML neben SVG/PDF
                if sib.exists():
                    from elucida.core import chem as CHEM
                    chem = CHEM.load_cdxml(sib)
                    asset.update(mw=chem["mw"], formula=chem["formula"], warnings=chem["warnings"])
            return asset

        def done(asset):
            if st.get("no_structure"):                    # inzwischen abgewählt (z. B. gespeicherter Zustand geladen)
                return
            st["structure"], st["structure_asset"] = str(path), asset
            info = []
            if asset.get("formula") and asset.get("mw"):
                info.append(T("mw_formula", f=asset["formula"], mw=asset["mw"]))
                if autofill_mw:
                    st["mw"] = round(asset["mw"], 2)
            if asset.get("drawing_from"):
                info.append(T("drawing_from", name=asset["drawing_from"]))
            info += asset.get("warnings") or []
            st["chem_info"] = "\n".join(info)
            st["chem_warn"] = bool(asset.get("warnings"))
            if g == self.current:
                self.apply_series_widgets()
            if render:
                self.render()

        self.run(work, done, sync)

    def choose_photo(self):
        if not self.current:
            return self.error(T("load_first"))
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_photo"), self.settings.value("last_img_dir", ""),
                                           f"{T('flt_photo')};;{T('flt_all')}")
        if p:
            self.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_photo(p)

    def bg_changed(self):
        if self._loading or not self.current:
            return
        st = self.series[self.current]
        st["bg"] = self.cmb_bg.currentData()
        if st["photo"]:
            self.set_photo(st["photo"])

    def ensure_model(self):
        """Fragt nach dem Modell-Download. True = ISNet nutzbar."""
        if IMG.model_path(existing_only=True):
            return True
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            return False
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and not getattr(self, "_allow_download", False):
            return False
        if not getattr(self, "_allow_download", False):
            ans = QMessageBox.question(self, T("model_q_title"), T("model_q", mb=IMG.MODEL_SIZE_MB))
            if ans != QMessageBox.Yes:
                return False
        dlg = QProgressDialog(T("downloading"), T("cancel"), 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.show()

        def prog(done, total):
            dlg.setValue(int(100 * done / max(total, 1)))
            QApplication.processEvents()
            return not dlg.wasCanceled()
        try:
            IMG.download_model(prog)
            return True
        except Exception as e:
            self.log_signal.emit(str(e))
            print(f"ISNet download failed: {type(e).__name__}: {e}", flush=True)
            return False
        finally:
            dlg.close()

    def set_photo(self, path, g=None, render=True, sync=False):
        g = g or self.current
        st = self.series[g]
        if path is not None and self.project_dir:
            path = self.import_file(path, PRJ.STRUCTURES)
        if path is None:
            st.update(photo=None, photo_asset=None)
            self.apply_series_widgets()
            return self.render()
        method = st["bg"]
        if method in ("auto", "isnet") and not self.ensure_model():
            method = "grabcut" if method == "isnet" else "auto"
        cache = self.cache_dir(self.csv_path) if self.csv_path else None

        def done(asset):
            st["photo"], st["photo_asset"] = str(path), asset
            self.log_signal.emit(f"  {Path(path).name}: {asset.get('bg_method')}")
            if g == self.current:
                self.apply_series_widgets()
            if render:
                self.render()

        self.run(lambda: IMG.load_photo(path, method, cache), done, sync)

    def run(self, fn, done, sync=False):
        if sync:
            try:
                done(fn())
            except Exception as e:
                self.error(str(e))
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage(T("working"))
        t = Task(fn, self)
        self._tasks.append(t)

        def fin():
            QApplication.restoreOverrideCursor()
            self.statusBar().clearMessage()
            self._tasks.remove(t)
        t.done.connect(done)
        t.failed.connect(self.error)
        t.finished.connect(fin)
        t.start()

    # ------------------------------------------------------------ Plot
    def make_cfg(self, g):
        gl = self.glob
        st = self.series[g]
        cfg = core.deep_merge(core.DEFAULTS, {})
        cfg["_base_dir"] = Path(self.csv_path).parent
        cfg["conc_unit"] = self.units[g]
        cfg["molar_mass_g_mol"] = st["mw"]
        cfg["path_length_cm"] = gl["path_length"]
        cfg["max_abs_fit"] = gl["cutoff"]
        cfg["min_fit_points"] = gl["min_points"]
        cfg["min_r2"] = gl.get("min_r2", 0.98)
        try:
            bands = [float(x) for x in gl["bands"].replace(";", ",").split(",") if x.strip()]
        except ValueError:
            bands = []
        cfg["wavelengths_nm"] = bands or "auto"
        cfg["bands_add_auto"] = gl.get("bands_add", True)
        cfg["find_shoulders"] = gl.get("shoulders", False)
        cfg["inset"]["show_excluded"] = gl.get("show_excl", False)
        cfg["conc_colors"] = gl.get("conc_colors", False)
        cfg["conc_legend"] = gl.get("conc_legend", False)
        cfg["inset"]["show"] = gl.get("inset", True)
        cfg["labels"]["mark_shoulders"] = gl.get("mark_sh", False)
        cfg["labels"]["index"] = gl.get("label_index", False)
        cfg["band_cutoff"] = {int(k): float(v) for k, v in (st.get("band_cutoff") or {}).items()}
        cfg["band_hidden"] = [int(k) for k in (st.get("band_hidden") or [])]
        if gl["baseline"] == "off":
            cfg["baseline_nm"] = None
        elif gl["baseline"] == "manual":
            cfg["baseline_nm"] = [gl["bl_a"], gl["bl_b"]]
        else:
            cfg["baseline_nm"] = "auto"
            cfg["baseline_mode"] = gl["baseline"]
        cfg["ylim"] = [0, gl["ymax"]]
        if not gl["x_auto"] and gl["x_max"] > gl["x_min"]:
            cfg["xlim"] = [gl["x_min"], gl["x_max"]]
        cfg["r2_mode"] = gl["r2"]
        cfg["labels"]["show_error"] = gl["show_err"]
        cfg["inset"]["table"] = gl["table"]
        cfg["figsize_in"] = list(FIGSIZE)
        if gl["size"] != "std":
            core.apply_export_size(cfg, gl["w_cm"], gl["h_cm"])
        fmts = [e for e, on in (("pdf", gl["fmt_pdf"]), ("svg", gl["fmt_svg"]), ("png", gl["fmt_png"])) if on]
        cfg["extra_formats"] = fmts[1:]
        cfg["_main_fmt"] = fmts[0] if fmts else "pdf"
        imgs = []
        if st["structure_asset"]:
            imgs.append({"file": st["structure"], "id": "struktur", "width": st.get("struct_w", 17) / 100,
                         "prefer": "top",
                         "_asset": st["structure_asset"]})
        if st["photo_asset"]:
            imgs.append({"file": st["photo"], "id": "kuevette", "width": st.get("photo_w", 9) / 100,
                         "prefer": "right",
                         "_asset": st["photo_asset"]})
        cfg["images"] = imgs
        core.apply_text_format(cfg, self.text_format("epsilon"))
        return cfg

    # ------------------------------------------------------------ Farbe der Lösung
    def color_settings_changed(self, *_):
        if self._loading:
            return
        self.glob.update(color_show=self.cb_color.isChecked(), color_d=self.sp_color_d.value())
        st = self.series.get(self.current)
        if st is not None and self.sender() is self.sp_color_c:    # nur echte Eingabe merken
            st["color_c"] = self.sp_color_c.value()
        self.update_color()
        self.push_undo()

    def update_color(self):
        """Farbfeld aktualisieren: c (Serieneinheit) und d frei wählbar, Standard = höchste gemessene
        Konzentration in 1 cm."""
        on = bool(self.glob.get("color_show"))
        for w_ in (self.lbl_color, self.lbl_color_info):
            w_.setVisible(on)
        for sp in (self.sp_color_c, self.sp_color_d):       # Feld samt Beschriftung
            self._color_form.setRowVisible(sp, on)
        if not on or not self._color_spectra or self.current not in self.series:
            return
        spectra, cfg = self._color_spectra
        if not spectra:
            return
        st = self.series[self.current]
        unit = core.unit_text(cfg["conc_unit"])
        c = st.get("color_c") or max(s_["c"] for s_ in spectra)
        d = self.glob.get("color_d", 1.0)
        loading, self._loading = self._loading, True
        self.sp_color_c.setSuffix(f" {unit}")
        self.sp_color_c.setValue(c)
        self.sp_color_d.setValue(d)
        self._loading = loading
        a, covered = COLOR.solution_absorbance(spectra, c, d, cfg["path_length_cm"], cfg["max_abs_fit"])
        rgb, out_of_gamut = COLOR.absorbance_to_rgb(a)
        hx = COLOR.to_hex(rgb)
        self.lbl_color.setStyleSheet(f"background: {hx}; border: 1px solid #888; border-radius: 4px;")
        info = T("color_info", hex=hx, c=f"{c:g}", unit=unit, d=f"{d:g}")
        if covered < 0.95:
            info += "\n" + T("color_partial", p=round(100 * covered))
        if out_of_gamut:
            info += "\n" + T("color_gamut")
        self.lbl_color_info.setText(info)
        self.lbl_color_info.setStyleSheet(WARN_CSS if covered < 0.95 else HINT_CSS)

    def show_hover(self, txt):
        if txt:
            self.statusBar().showMessage(txt)
        else:
            self.statusBar().clearMessage()

    @staticmethod
    def hover_text(lam, val, name):
        return T("hover_abs", lam=lam, a=val, name=name) if val is not None else T("hover_lam", lam=lam)

    def pick_band(self, lam):
        """Doppelklick aufs Spektrum: λ als Bande hinzufügen bzw. (±2 nm) wieder entfernen."""
        try:
            bands = [float(x) for x in self.glob["bands"].replace(";", ",").split(",") if x.strip()]
        except ValueError:
            bands = []
        lam = round(lam)
        near = [b for b in bands if abs(b - lam) <= 2]
        if near:
            bands = [b for b in bands if b not in near]
            msg = T("band_removed", lam=f"{near[0]:g}")
        else:
            bands.append(lam)
            msg = T("band_added", lam=f"{lam:g}")
        self.ed_bands.setText(", ".join(f"{b:g}" for b in sorted(bands)))
        self.changed()
        QTimer.singleShot(0, lambda: self.statusBar().showMessage(msg, 6000))

    def text_format(self, key):
        """Textformat eines Tabs: eigenes Format (Menü Format, „nur dieser Tab“), sonst das für alle Tabs."""
        return {**core.TEXT_DEFAULTS, **self.text_fmt, **(self.tab_fmt.get(key) or {})}

    def text_tab(self):
        """Offener Tab -> (Schlüssel für das Textformat oder None, Name, Optionen, die der Tab im Bild hat)."""
        w_ = self.main_tabs.currentWidget()
        name = self.main_tabs.tabText(self.main_tabs.currentIndex())
        if w_ is self.eps_page:
            return "epsilon", name, TABS.ALL_TEXT_OPTS
        if isinstance(w_, TABS.FigureTab) and w_.TEXT_OPTS:
            return w_.STATE_KEY, name, w_.TEXT_OPTS
        return None, name, ()

    def edit_text_format(self):
        """Menü Format → Schrift und Rahmen: zeigt die Karte im offenen Tab (früher ein Dialog, Nutzerwunsch: keine
        Popups). Tabs ohne Textformat (Synthese, NMR, Verbindung, Weitere) melden das nur."""
        key, name, _ = self.text_tab()
        tab = self.main_tabs.currentWidget()
        card = self.tf_card if key == "epsilon" else getattr(tab, "tf_card", None) if key else None
        if card is None:
            self.statusBar().showMessage(T("tf_no_text", tab=name), 8000)
            return
        (self.steps if key == "epsilon" else tab.steps).reveal(card)
        if card.fold is not None:
            card.fold.set_open(True)
        area = card.parentWidget()
        while area is not None and not isinstance(area, QScrollArea):
            area = area.parentWidget()
        if area is not None:
            QTimer.singleShot(0, lambda: area.ensureWidgetVisible(card.box))
        if card.cmb_font is not None:
            card.cmb_font.setFocus()

    def update_text_format(self, key, changes):
        """Textformat ändern: key None = Standard aller Tabs, sonst das eigene Format dieses Tabs."""
        if key is None:
            self.text_fmt = {**self.text_fmt, **changes}
        else:
            self.tab_fmt[key] = {**self.text_format(key), **changes}
        self.text_format_changed()

    def set_own_text_format(self, key, on):
        """„Nur dieser Tab“: eigenes Format beginnt als Kopie des Standards; abgewählt gilt wieder der Standard."""
        if on:
            self.tab_fmt[key] = {**core.TEXT_DEFAULTS, **self.text_fmt}
        else:
            self.tab_fmt.pop(key, None)
        self.text_format_changed()

    def text_format_changed(self):
        """Nach jeder Änderung des Textformats: fehlende Schriften melden, alle gebauten Tabs neu zeichnen, Karten
        nachziehen, ein Rückgängig-Schritt."""
        for tf in [self.text_fmt] + list(self.tab_fmt.values()):
            for k_ in ("font", "symbol_font"):
                if tf.get(k_) and core.first_font([tf[k_]], None) is None:
                    self.log_signal.emit("  " + T("tf_missing", name=tf[k_]))
        self.render()
        for key in ("overlay", "uvkin", "fluo", "cv", "sec", "hcell", "epr", "irms", "hrms", "xray", "dft"):
            if self._built(key):                       # ungebaute zeichnen beim Bauen mit dem neuen Format
                getattr(self, self._tab_spec(key)[0]).render()
        self.sync_text_cards()
        self.push_undo()

    def sync_text_cards(self):
        """Karten „Schrift und Rahmen“ aller gebauten Tabs zeigen den aktuellen Stand (auch nach Rückgängig)."""
        for card in self.findChildren(TABS.TextFormatCard):
            card.load()

    def _r2_digits_changed(self, *_):
        """Stellenzahl von R² gilt für alle Tabs der Verbindung: die anderen mit Fit neu zeichnen."""
        if self._loading:
            return
        self.changed()
        for key in ("cv", "sec", "epr"):
            if self._built(key):
                getattr(self, self._tab_spec(key)[0]).render()

    def clear_results(self):
        """Ohne Messdaten: Ergebnistabelle, Kacheln, SI-Zeile, Bildunterschrift und Methodentext leeren. Sonst blieben in
        einer neuen oder leeren Verbindung die Zahlen der zuvor geöffneten stehen (grafische Sichtung 2026-11-11)."""
        if self.dragger:
            self.dragger.disconnect()
            self.dragger = None
        if self.hover:
            self.hover.disconnect()
            self.hover = None
        self.F = None
        self._last = None
        self._color_spectra = None
        self._row_keys = []
        self._uv_line = ("", "")
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.kpi_box.show_items([])
        self.txt_si.setText("")
        self.lbl_eps_cap.setText("")
        self.lbl_eps_methods.setText("")
        self.lbl_cap_bar.set_full("")
        try:
            self.update_color()
        except Exception:                                # die Farbe der Lösung ist Zugabe
            pass

    def render(self):
        has_data = bool(self.current and self.current in self.groups)
        self.preview_stack.setCurrentIndex(1 if has_data else 0)
        if not has_data:
            self.clear_results()
            return
        g = self.current
        try:
            cfg = self.make_cfg(g)
            core.setup_fonts(plt, cfg)
            cfg2, spectra, results = core.prepare_series(cfg, self.groups[g], g)
            if self.dragger:
                self.dragger.disconnect()
                self.dragger = None
            if self.hover:
                self.hover.disconnect()
                self.hover = None
            self.canvas_host.set_figure_size(*cfg2["figsize_in"])
            self.F = core.build_figure(plt, cfg2, spectra, results, self.get_layout(g), fig=self.fig)
            self.dragger = GuiDragger(self.F, self.layout_changed)
            unit = core.unit_text(cfg2["conc_unit"])
            curves = [dict(x=s_["x"], y=s_["y"], val=s_["y"], name=f"c = {s_['c']:g} {unit}") for s_ in spectra]
            self.hover = TABS.HoverReadout(self.F, curves, self.show_hover, self.hover_text, self.pick_band)
            self.sync_image_sizes(self.F.current_layout())
            self.canvas.draw_idle()
            self.fill_table(results, cfg2)
            self.update_si_line(results, cfg2)
            self._color_spectra = (spectra, cfg2)
            self.update_color()
            self._last = (cfg2, results)
        except Exception as e:
            self.log_signal.emit(traceback.format_exc())
            self.statusBar().showMessage(f"{T('err_title')}: {e}", 8000)
        self.push_undo()                               # auch wenn das Bild scheitert: Änderung speichern/rückgängig

    def size_key(self):
        gl = self.glob
        return "std" if gl["size"] == "std" else f"{gl['w_cm']:g}x{gl['h_cm']:g}"

    def get_layout(self, g):
        lay = self.series[g]["layout"] or {}
        if lay and not all(isinstance(v, dict) for v in lay.values()):
            lay = {"std": lay}                       # altes Format (eine Größe)
            self.series[g]["layout"] = lay
        return lay.setdefault(self.size_key(), {})

    def layout_changed(self, layout):
        if not self.current or self.F is None:
            return
        if not layout:                                 # nichts bewegt
            return
        stored = self.get_layout(self.current)
        layout = dict(stored, **layout)
        if layout != stored:
            self.series[self.current]["layout"][self.size_key()] = layout
        self.sync_image_sizes(layout)
        self.push_undo()

    def sync_image_sizes(self, layout):
        """Größenfelder an die tatsächliche Bildgröße anpassen (Mausrad, automatisches Verkleinern)."""
        st = self.series.get(self.current)
        if not st:
            return
        self._loading = True
        for key, field, spin in (("image_struktur", "struct_w", self.sp_struct_w),
                                 ("image_kuevette", "photo_w", self.sp_photo_w)):
            if key in layout and len(layout[key]) == 4:
                st[field] = round(layout[key][2] * 100, 1)
                spin.setValue(st[field])
        self._loading = False

    def image_size_changed(self, iid, value):
        """Größe aus dem Zahlenfeld: Breite setzen, Mittelpunkt und Seitenverhältnis behalten."""
        if self._loading or not self.current:
            return
        st = self.series[self.current]
        st["struct_w" if iid == "struktur" else "photo_w"] = value
        lay = self.get_layout(self.current)
        key = f"image_{iid}"
        if key in lay and len(lay[key]) == 4:
            x, y, w, h = lay[key]
            nw = value / 100
            nh = h * nw / w
            nx = min(max(x + (w - nw) / 2, 0.0), max(0.0, 1 - nw))     # in der Achse halten
            ny = min(max(y + (h - nh) / 2, 0.0), max(0.0, 1 - nh))
            lay[key] = [nx, ny, nw, nh]
        self.timer.start()

    def reset_layout(self):
        if self.current:
            self.get_layout(self.current)
            self.series[self.current]["layout"][self.size_key()] = {}
            self.render()

    def reset_defaults(self):
        """ε-Tab: Einstellungen (Cutoff, Banden, Basislinie, Darstellung …) auf DEFAULT_GLOB, für die gewählte Serie
        Cutoff/Ausblenden je Bande und Layout. Schichtdicke, Exportgröße/-formate, Molmasse, Struktur, Foto,
        Lösungsmittel und Konzentrationen bleiben. Rückgängig holt alles zurück."""
        keep = ("path_length", "size", "w_cm", "h_cm", "fmt_pdf", "fmt_svg", "fmt_png")
        self.glob.update({k: v for k, v in DEFAULT_GLOB.items() if k not in keep})
        st = self.series.get(self.current)
        if st is not None:
            st.update(band_cutoff={}, band_hidden=[], layout={})
        self.apply_globals()
        self.apply_series_widgets()
        self.render()
        self.push_undo()
        self.statusBar().showMessage(T("xr_reset_display_done"), 6000)

    def update_si_line(self, results, cfg):
        st = self.series.get(self.current) or {}
        self.ed_solvent.setText(st.get("solvent", ""))
        self._uv_line = SI.uvvis_line(results, cfg, st.get("solvent", ""))
        self.txt_si.setText(self._uv_line[1] or T("si_uv_none"))
        cap = "<b>Figure Sn:</b> " + self.eps_caption(self.current, cfg["path_length_cm"], self.export_name())
        self.lbl_eps_cap.setText(cap)
        self.lbl_cap_bar.set_full(T("caption_bar") + " · " + html.unescape(re.sub(r"<[^>]+>", "", cap)))
        try:
            txt = self.eps_methods_text()
        except Exception:                                    # der Text ist Zugabe: nie das Zeichnen stören
            txt = ""
        self.lbl_eps_methods.setText(html.escape(txt) or T("si_methods_none"))

    def eps_caption(self, g, path_cm, name):
        """Bildunterschrift der Serie für die SI (HTML): Lösungsmittel aus der Serie, Schichtdicke aus dem Bild."""
        solv = (self.series.get(g) or {}).get("solvent", "").strip()
        return (f"UV-Vis spectra of <b>{html.escape(name)}</b>" + (f" in {SI.chem_html(solv)}" if solv else "")
                + f", measured in {path_cm:g} cm quartz cuvettes.")

    def copy_eps_caption(self):
        cap = self.lbl_eps_cap.text()
        IRMS.copy_rich(html.unescape(re.sub(r"<[^>]+>", "", cap)), cap)
        self.statusBar().showMessage(T("si_caption_copied") if cap else T("si_caption_none"), 6000)

    def solvent_changed(self):
        st = self.series.get(self.current)
        if st is not None and self.ed_solvent.text().strip() != st.get("solvent", ""):
            st["solvent"] = self.ed_solvent.text().strip()
            self.render()

    def uvvis_si_parts(self):
        """UV-Vis-Zeile je Serie mit Ergebnissen (für den SI-Export)."""
        return [line for _, line in self.uvvis_si_parts_by_series()]

    def uvvis_si_parts_by_series(self):
        """[(Serie, (Klartext, HTML))] in derselben Reihenfolge (Austauschdatei: Zeile ↔ Serie)."""
        out = []
        for g in self.groups:
            try:
                cfg2, _, results = core.prepare_series(self.make_cfg(g), self.groups[g], g)
            except Exception as ex:                    # fehlt sonst unbemerkt in der SI
                self.log_signal.emit(T("si_series_failed", name=g, error=ex))
                self.statusBar().showMessage(T("si_series_failed", name=g, error=ex), 12000)
                continue
            line = SI.uvvis_line(results, cfg2, (self.series.get(g) or {}).get("solvent", ""))
            if line[0]:
                out.append((g, line))
        return out

    def eps_methods_text(self, groups=None, with_results=True):
        """SI-Text zur ε-Bestimmung je Serie (englisch, si.lines.eps_methods)."""
        out = []
        for g in (groups or list(self.groups)):
            try:
                cfg2, spectra, results = core.prepare_series(self.make_cfg(g), self.groups[g], g)
            except Exception as ex:
                self.log_signal.emit(T("si_series_failed", name=g, error=ex))
                self.statusBar().showMessage(T("si_series_failed", name=g, error=ex), 12000)
                continue
            txt = SI.eps_methods(cfg2, results, spectra, (self.series.get(g) or {}).get("solvent", ""),
                                 with_results)
            if txt:
                out.append((f"Series {g}: " if len(self.groups) > 1 and g else "") + txt)
        return "\n\n".join(out)

    def copy_eps_methods(self):
        self.collect_globals()
        txt = self.eps_methods_text()
        if txt:
            QApplication.clipboard().setText(txt)
        self.statusBar().showMessage(T("si_methods_copied") if txt else T("si_methods_none"), 6000)

    def si_available(self):
        """Teile der SI, für die Daten da sind."""
        xt, dt = self.xray_tab, self.dft_tab
        return dict(char=True, nmr=bool(self.nmr_tab.spectra()),
                    figs=bool(self.groups) or any(t.F is not None for t in self.figure_tabs()),
                    methods=bool(self.si_methods_blocks()),
                    xray=any(xt.structure(e) is not None for e in xt.entries()),
                    dft=any(dt.calc_of(e) is not None for e in dt.entries()))

    def si_figure_choices(self):
        """[(Schlüssel, Titel)] der Tabs mit Abbildung für die Auswahl im SI-Dialog (Reihenfolge wie die SI)."""
        out = [("eps", T("tab_eps"))] if self.groups else []
        for t in self.figure_tabs():
            t.ensure_rendered()
            if t.F is not None:
                k = self.tab_key_of(t)
                out.append((k, T(self._tab_spec(k)[3])))
        ds = self.dft_state
        if ds.get("entries") or (ds.get("profile") or {}).get("irc") or (ds.get("nics") or {}).get("files"):
            out.append(("dft", T("tab_dft")))
        return out

    def si_parts_saved(self):
        """Gewählte Teile des SI-Exports (QSettings `si_parts`, Karte „SI-Export“ im Tab Verbindung). Abbildungen und
        Methodentexte, neu in 1.24/1.24.1, einmalig mit ausgewählt."""
        saved = self.settings.value("si_parts", "char,nmr,figs,methods,xray,dft")
        saved = set(str(saved).split(",")) if saved else set()
        if not self.settings.value("si_parts_figs"):
            saved |= {"nmr", "figs"}
            self.settings.setValue("si_parts_figs", 1)
        if not self.settings.value("si_parts_methods"):
            saved |= {"methods"}
            self.settings.setValue("si_parts_methods", 1)
        return saved & set(SI_PARTS)

    def set_si_parts(self, parts):
        self.settings.setValue("si_parts", ",".join(k for k in SI_PARTS if k in parts))

    def si_figs_off(self):
        """Tabs, deren Abbildung nicht in die SI soll (QSettings `si_figs_off`)."""
        return set(str(self.settings.value("si_figs_off", "") or "").split(",")) - {""}

    def export_si_dialog(self):
        """„SI (Word)“: exportiert direkt mit der Auswahl der Karte „SI-Export“ im Tab Verbindung (früher ein Dialog,
        Nutzerwunsch: keine Popups). Gewählte Teile ohne Daten fallen weg und werden gemeldet; die Auswahl bleibt."""
        if not self.ensure_project():
            return
        avail = self.si_available()
        saved = self.si_parts_saved()
        parts = [k for k in SI_PARTS if k in saved and avail[k]]
        empty = [T("si_chip_" + k) for k in SI_PARTS if k in saved and not avail[k]]
        if not parts:
            self.statusBar().showMessage(T("si_nothing_selected"), 8000)
            return
        if empty:
            self.statusBar().showMessage(T("si_parts_without_data", parts=", ".join(empty)), 8000)
        self.export_si(parts, self.si_figs_off())

    def export_si(self, parts=SI_PARTS, skip_figs=()):
        """SI-Abschnitt der Verbindung als Word-Datei: Charakterisierungsabsatz (m.p.; IR; HR-MS; UV-Vis;
        Elementaranalyse), Kristalldaten, ausgewählte Parameter und Bildunterschriften aus dem X-Ray-Tab, DFT-Rechnungen
        (zweispaltig) – je nach Auswahl."""
        if not self.ensure_project():
            return
        try:
            blocks, missing = self.si_blocks(parts, skip_figs)
            pdir = Path(self.project_dir)
            name = core.safe_name(self.export_name())
            p = SI.write_docx(PRJ.export_dir(pdir, PRJ.SI_DIR) / f"{name}_SI.docx", blocks)
            p = (self.place_exports([p]) or [p])[0] if self.is_quick() else p     # Schnellauswertung: Zielordner
        except PermissionError as e:
            return self.error(T("report_locked", p=getattr(e, "filename", "")))
        except Exception as e:
            self.log_signal.emit(traceback.format_exc())
            return self.error(str(e))
        msg = T("si_written", p=str(p))
        if missing:
            msg += "\n" + T("si_missing", parts=", ".join(missing))
        self.info(msg)

    def si_blocks(self, parts=SI_PARTS, skip_figs=()):
        """-> (Blöcke für SI.write_docx, fehlende Teile). skip_figs: Tabs (Schlüssel wie si_figure_choices) ohne
        Abbildung; ihre Zeilen im Charakterisierungsabsatz bleiben."""
        comp = self.compound or {}
        title = self.syn_tab.st.get("name") or comp.get("name") or Path(self.project_dir or ".").name
        blocks, missing, plain = [], [], ""
        if "char" in parts:
            blocks, missing, plain = self.si_char_blocks(comp, title)
            blocks = self.syn_tab.gp_blocks() + blocks            # Einzel-SI: allgemeine Vorschrift davor
        elif title:
            blocks = [("heading", title)]
        self._si_plain = plain
        if "nmr" in parts and self.nmr_tab.spectra() and self.project_dir:
            blocks += [("pagebreak",)] + self.nmr_tab.docx_blocks(PRJ.work_dir(self.project_dir, "si"))
        if "figs" in parts and self.project_dir:
            figs = self.si_figure_blocks(PRJ.work_dir(self.project_dir, "si"), title, skip_figs)
            if figs:
                blocks += [("pagebreak",)] + figs
        if "methods" in parts:
            mb = self.si_methods_blocks()
            if mb:
                blocks += [("gap",)] + mb
        xt = self.xray_tab
        es = [e for e in xt.entries() if xt.structure(e) is not None] if "xray" in parts else []
        if es:
            blocks += self.si_xray_blocks(es)
        dt = self.dft_tab
        if "dft" in parts and any(dt.calc_of(e) is not None for e in dt.entries()) and self.project_dir:
            blocks += [("gap",), ("columns", 2)] + dt.docx_blocks(PRJ.work_dir(self.project_dir, "si"))
        return blocks, missing

    def si_methods_items(self):
        """Methodentexte der Tabs, die fitten -> [(Kapitel der Gesamt-SI, Titel, Text)] (Text leer ohne Fit)."""
        self.collect_globals()
        items = [("uvvis", "UV-Vis absorption spectroscopy",          # Word: ohne Bandenliste (steht in Zeile/Bild)
                  self.eps_methods_text(with_results=False) if self.groups else "")]
        for key, title, t in (("uvvis", "UV-Vis kinetics", self.uvkin_tab), ("cv", "Cyclic voltammetry", self.cv_tab),
                              ("sec", "UV-Vis spectroelectrochemistry", self.sec_tab),
                              ("hcell", "H-cell charge–discharge cycling", self.hcell_tab),
                              ("epr", "EPR spectroscopy", self.epr_tab)):
            try:
                txt = t.methods_text() if t.figure_spec() is not None else ""   # Ergebnisse/Fits aktuell
            except Exception:
                self.log_signal.emit(traceback.format_exc())
                txt = ""
            items.append((key, title, txt))
        return items

    @staticmethod
    def _methods_paras(title, txt):
        paras = [p.strip() for p in (txt or "").split("\n\n") if p.strip()]
        return [("char", (f"<b>{title}.</b> " if k == 0 else "") + SI.methods_html(p)) for k, p in enumerate(paras)]

    def si_methods_blocks(self):
        """Abschnitt „Data processing and fitting“: dieselben Methodentexte wie „SI-Text kopieren“ (nur benutzte
        Schritte, aktuelle Parameter, dann Ergebnisse) für alle Tabs, die fitten; je Technik ein Absatz mit fettem
        Titel. Leer, wenn nirgends gefittet wurde."""
        blocks = []
        for _, title, txt in self.si_methods_items():
            blocks += self._methods_paras(title, txt)
        return [("heading", "Data processing and fitting")] + blocks if blocks else []

    def si_compound_parts(self, sections, methods=True):
        """Gesamt-SI (elucida/si/publication_si.py): Blöcke der geöffneten Verbindung je Kapitel. Abbildungen ohne
        Seitenaufteilung (macht die Gesamt-SI), Aufbau-Texte stehen dort in „Materials and Methods“."""
        comp = self.compound or {}
        title = self.syn_tab.st.get("name") or comp.get("name") or Path(self.project_dir or ".").name
        out_dir = PRJ.work_dir(self.project_dir, "si")
        parts = {}

        def figs(tabs):
            res = []
            for t in tabs:
                try:
                    res += t.si_figure(out_dir, title)
                except Exception:
                    self.log_signal.emit(traceback.format_exc())
            return res
        if "char" in sections:
            parts["char"] = self.si_char_blocks(comp, title)[0]
        if "nmr" in sections and self.nmr_tab.spectra():
            parts["nmr"] = self.nmr_tab.docx_blocks(out_dir)
        if "irms" in sections:
            parts["irms"] = figs([self.irms_tab, self.hrms_tab])
        if "uvvis" in sections:
            parts["uvvis"] = self.si_eps_figures(out_dir, title) + figs([self.ov_tab, self.uvkin_tab, self.fl_tab])
        for key, tab in (("epr", self.epr_tab), ("cv", self.cv_tab), ("sec", self.sec_tab), ("hcell", self.hcell_tab)):
            if key in sections:
                parts[key] = figs([tab])
        if methods:
            for key, mtitle, txt in self.si_methods_items():
                if key in sections and txt:
                    parts["methods_" + key] = (parts.get("methods_" + key) or []) + \
                        self._methods_paras(f"{mtitle} ({title})", txt)   # UV-Vis: ε und Kinetik
        xt = self.xray_tab
        es = [e for e in xt.entries() if xt.structure(e) is not None] if "xray" in sections else []
        if es:
            blocks = self.si_xray_blocks(es)
            k = next((i for i, b in enumerate(blocks) if b[0] == "tabcap" and b[1].startswith("Crystal data")), None)
            parts["xray"] = blocks[:k] if k is not None else blocks       # Kristalldaten: gemeinsame Tabellen
            h_, r_ = xt.crystal_table()
            parts["crystal"] = (h_, [[c_.replace(", ", "\n") if row_[0] == "Index ranges" else c_ for c_ in row_]
                                     for row_ in r_])
        dt = self.dft_tab
        if "dft" in sections and any(dt.calc_of(e) is not None for e in dt.entries()):
            parts["dft"] = dt.docx_blocks(out_dir)
        if "dft" in sections:
            try:
                parts["dft_figs"] = dt.pages.si_figures(out_dir, title)    # Energieprofil, IRC, NICS (F4)
            except Exception:
                self.log_signal.emit(traceback.format_exc())
        try:                                    # Tab „Weitere“: ins gewählte Kapitel oder eigenes Kapitel am Ende
            for key, bl in self.other_tab.chapter_blocks(out_dir, title):
                key = "dft_figs" if key == "dft" else key
                if key.startswith("new:") or key in sections or (key == "dft_figs" and "dft" in sections):
                    parts[key] = (parts.get(key) or []) + bl
        except Exception:
            self.log_signal.emit(traceback.format_exc())
        return title, parts

    def figure_tabs(self):
        """Tabs mit Abbildung in der Reihenfolge der SI (Charakterisierung, dann Spektroskopie, Elektrochemie)."""
        return [self.irms_tab, self.hrms_tab, self.ov_tab, self.uvkin_tab, self.fl_tab, self.cv_tab, self.sec_tab, self.hcell_tab,
                self.epr_tab, self.other_tab]

    def si_figure_blocks(self, out_dir, name, skip=()):
        """Abbildungen aller Tabs mit Daten (ε je Serie, IR, HR-MS, Overlay, Fluoreszenz, CV, SEC, EPR), immer zwei je
        Seite (SI.two_per_page verkleinert, wo nötig), jede mit „Figure Sn: …“."""
        figs = self.si_eps_figures(out_dir, name) if "eps" not in skip else []
        for t in self.figure_tabs():
            if self.tab_key_of(t) in skip:
                continue
            try:
                fb = t.si_figure(out_dir, name)
                if fb and t.si_setup_text():                 # Aufbau-Absatz der Methode (lokal hinterlegt)
                    fb = [("char", SI.chem_html(t.si_setup_text()))] + fb
                figs += fb
            except Exception:
                self.log_signal.emit(traceback.format_exc())
        ds = self.dft_state
        if "dft" not in skip and (ds.get("entries") or (ds.get("profile") or {}).get("irc")
                                  or (ds.get("nics") or {}).get("files")):   # F4
            try:
                figs += self.dft_tab.pages.si_figures(out_dir, name)
            except Exception:
                self.log_signal.emit(traceback.format_exc())
        return SI.two_per_page(figs)

    def si_eps_figures(self, out_dir, name):
        """ε-Abbildung je Serie wie beim Export (Größe aus dem Tab) + Unterschrift."""
        if not self.groups:
            return []
        self.collect_globals()
        out = []
        for g in self.groups:
            cfg = self.make_cfg(g)
            core.setup_fonts(plt, cfg)
            cfg2, spectra, results = core.prepare_series(cfg, self.groups[g], g)
            fig = MplFigure(figsize=cfg2["figsize_in"], dpi=PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = core.build_figure(plt, cfg2, spectra, results, self.get_layout(g), fig=fig)
            sfx = f"_{core.safe_name(g)}" if len(self.groups) > 1 else ""
            img = TABS.si_image(F, Path(out_dir) / f"{core.safe_name(name)}_epsilon{sfx}.svg")
            solv = (self.series.get(g) or {}).get("solvent", "").strip()
            cap = self.eps_caption(g, cfg2["path_length_cm"], name)
            if not solv:
                self.log_signal.emit(T("si_uv_no_solvent", g=g))
            out += [img, ("figcap", cap)]
        return out

    def si_char_parts(self, comp):
        """Zeilen des Charakterisierungsabsatzes in SI-Reihenfolge -> ([(Art, Klartext, HTML)], fehlende Teile).
        Art: mp, nmr_<Kern>, ir, hrms, uvvis, ea."""
        parts, missing = [], []
        if comp.get("oil"):                                # Öl: Schmelzpunkt unter Raumtemperatur
            parts.append(("mp", "m.p. <25 °C", "<b>m.p.</b> &lt;25 °C"))
        elif comp.get("mp"):
            mp = SI.mp_text(comp["mp"])                    # nur Zahl/Bereich: „°C“ ergänzen
            parts.append(("mp", "m.p. " + mp, "<b>m.p.</b> " + html.escape(mp)))   # wie in der SI: „m.p.“ fett
        else:
            missing.append("m.p.")
        nmr = self.nmr_tab.nmr_lines_by_nucleus()        # wie in der SI: m.p.; ¹H NMR …; ¹³C NMR …; IR …
        if not nmr:
            missing.append("NMR")
        parts += [("nmr_" + nuc, *line) for nuc, line in nmr]
        ir_ms_ea = self.irms_tab.si_parts() + self.hrms_tab.si_parts()
        kinds = [p_[0].split(" ")[0] for p_ in ir_ms_ea]
        uv = self.uvvis_si_parts()
        for key, lab in (("IR", "IR"), ("HR-MS-", "HR-MS")):   # Elementaranalyse immer optional (Nutzerwunsch)
            if not any(k_.startswith(key) for k_ in kinds):
                missing.append(lab)
        if not uv:
            missing.append("UV-Vis")
        parts += [("ir", *p_) for p_ in ir_ms_ea if p_[0].startswith("IR")] + \
            [("hrms", *p_) for p_ in ir_ms_ea if p_[0].startswith("HR-MS")] + [("uvvis", *p_) for p_ in uv] + \
            [("ea", *p_) for p_ in ir_ms_ea if p_[0].startswith("Elemental")]
        return parts, missing

    def si_char_blocks(self, comp, title):
        """„Synthesis of Name“ + Charakterisierungsabsatz -> (Blöcke, fehlende Teile, Klartext)."""
        parts, missing = self.si_char_parts(comp)
        plain, para = SI.join_lines([(p_, h_) for _, p_, h_ in parts])
        blocks = [("synthesis", title)]
        if self.syn_tab.has_content() and self.project_dir:      # Überschrift, Schema, Vorschrift aus dem Tab
            blocks = self.syn_tab.si_blocks(PRJ.work_dir(self.project_dir, "si"))
        if para:
            blocks.append(("char", para))
        return blocks, missing, plain

    def si_xray_blocks(self, es):
        """Abbildungen, Unterschriften, ausgewählte Parameter und Kristalldaten aus dem X-Ray-Tab."""
        xt, blocks = self.xray_tab, []
        if es:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure as MplFigure
            out_dir = PRJ.work_dir(self.project_dir, "si") if self.project_dir else None
            blocks.append(("gap",))
            for e in es:
                fname = e.get("name") or e["block"]
                if out_dir is not None:                   # Abbildung wie im X-Ray-Tab, 300 dpi
                    fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                    FigureCanvasAgg(fig)
                    F = xt.build(fig, e, interactive=False)
                    if F is not None:                     # wie in der SI eng um das Molekül beschnitten
                        svg = out_dir / f"{core.safe_name(fname)}_xray.svg"
                        blocks.append(("image",) + XRAY.save_tight(F, svg))
                blocks.append(("figcap", xt.caption(e)[1]))
                p_tabs = xt.param_tables(e)
                for t_title, t_name, t_head, t_rows in p_tabs:
                    blocks += [("tabcap", t_title, t_name), ("params", t_head, t_rows)]
                    if any("^{a}" in r_[-1] for r_ in t_rows):
                        blocks.append(("note", "^{a} " + XRAY.CALC_NOTE))
                    blocks.append(("gap",))
                if p_tabs and xt.sym_note(e):              # Symmetriecodes nur in den Parametertabellen (Regel)
                    blocks[-1:-1] = [("note", xt.sym_note(e))]
            h_, r_ = xt.crystal_table()
            r_ = [[c_.replace(", ", "\n") if row_[0] == "Index ranges" else c_ for c_ in row_] for row_ in r_]
            names = [e.get("name") or e["block"] for e in es]
            blocks += [("tabcap", "Crystal data and structure refinement", ", ".join(names)), ("crystal", h_, r_)]
        return blocks

    def fill_table(self, results, cfg):
        sym = "ε [M⁻¹ cm⁻¹]" if core.conc_factor(cfg) else "a [L g⁻¹ cm⁻¹]"
        self.table.blockSignals(True)
        self.table.setHorizontalHeaderLabels(["", T("col_n"), sym, T("col_intercept"),
                                              T("col_r2"), T("col_cut"), T("col_warn"), T("col_lam")])
        self.table.setRowCount(len(results))
        self._row_keys = []
        sym_ = "ε" if core.conc_factor(cfg) else "a"         # Kacheln neben den Reitern und Rechenweg
        fits_ = [r for r in results if r["fit"]][:2]
        self.kpi_box.show_items(
            [(core.fmt_lam(r["lam"]) + " nm", f"{sym_} = " + " ± ".join(x for x in core.fmt_ve(
                r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg)) if x)) for r in fits_])
        self.chain_row.set_items([(T("chain_baseline"), self.cmb_bl.currentData() != "off"), (T("chain_bands"), True),
                                  ("A/d = " + sym_ + "·c + b", True), (T("chain_ci"), True)])
        for i, r in enumerate(results):
            ft = r["fit"]
            lam = core.fmt_lam(r["lam"]) + (" (sh)" if r.get("shoulder") else "")
            cut = r.get("cutoff", cfg["max_abs_fit"])
            if ft:
                v, e = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg))
                b, be = core.fmt_ve(ft["intercept"], ft["se_intercept"])
                cells = [lam, str(ft["n"]), f"{v} ± {e}" if e else v,
                         f"{b} ± {be}" if be else b, core.r2_text(ft['r2']), f"{cut:g}", "; ".join(r["warnings"])]
            else:
                cells = [lam, str(len(r["used"])), "–", "–", "–", f"{cut:g}",
                         r.get("no_fit") or T("no_fit", n=len(r["used"]), cut=cut, min=cfg["min_fit_points"])]
            it = QTableWidgetItem()                          # Häkchen = im Bild anzeigen
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Unchecked if int(round(r["lam_requested"])) in set(cfg.get("band_hidden") or [])
                             else Qt.Checked)
            self.table.setItem(i, 0, it)
            for j, c in enumerate(cells):
                it = QTableWidgetItem(c)
                if j < 6:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j != 5:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    if j == 4 and ft and ft["r2"] < cfg["min_r2"]:   # unter R²-Schwelle -> nicht im Bild
                        it.setBackground(QColor("#f4cccc"))
                        it.setForeground(QColor("#000000"))
                        it.setToolTip(T("r2_below", min=cfg["min_r2"]))
                elif abs(cut - cfg["max_abs_fit"]) > 1e-9:
                    it.setBackground(QColor("#fff2cc"))
                    it.setForeground(QColor("#000000"))
                self.table.setItem(i, j or 7, it)            # λ (j = 0) steht in Spalte 7
            self._row_keys.append(int(round(r["lam_requested"])))
        self.table.blockSignals(False)

    def cutoff_edited(self, item):
        """Cutoff pro Bande aus der Ergebnistabelle (leer = globaler Cutoff); Häkchen in Spalte 0
        = Bande im Bild anzeigen."""
        if not self.current or item.row() >= len(self._row_keys):
            return
        if item.column() == 0:
            st = self.series[self.current]
            hid = set(st.get("band_hidden") or [])
            k = self._row_keys[item.row()]
            hid.discard(k) if item.checkState() == Qt.Checked else hid.add(k)
            st["band_hidden"] = sorted(hid)
            QTimer.singleShot(0, self.render)
            return
        if item.column() != 5:
            return
        key = str(self._row_keys[item.row()])
        st = self.series[self.current]
        bc = st.setdefault("band_cutoff", {})
        try:
            v = parse_float(item.text())
        except ValueError:
            v = None
        if v is None or abs(v - self.glob["cutoff"]) < 1e-9:
            bc.pop(key, None)
        else:
            bc[key] = v
        QTimer.singleShot(0, self.render)

    # ------------------------------------------------------------ Export
    def export_dialog(self):
        if not self.csv_path:
            return self.error(T("load_first"))
        if not self.ensure_project():
            return
        try:
            out = self.export_all()
        except PermissionError as e:
            return self.error(T("report_locked", p=getattr(e, "filename", "") or ""))
        self.exported(p.parent for p in out)

    def export_all(self, folder: Path = None):
        """Alle Serien exportieren: Abbildungen, Ergebnis-CSV und Excel-Report.
        Ohne Ordnerangabe ins Projekt: <Serie>_UV-Vis.* nach figures/, tables/, SI/ (wird überschrieben)."""
        self.collect_globals()
        stem = Path(self.csv_path).stem
        written = []
        for g in self.groups:
            if folder is None:
                gdir = PRJ.staging(self.project_dir, f"eps_{core.safe_name(g)}")
                name = PRJ.export_stem(g, "eps")
            else:
                gdir = Path(folder)
                name = f"{stem}_{g}" if len(self.groups) > 1 else stem
            cfg = self.make_cfg(g)
            core.setup_fonts(plt, cfg)
            cfg2, spectra, results = core.prepare_series(cfg, self.groups[g], g)
            folder_g = gdir
            cfg2["output"] = str(folder_g / f"{name}.{cfg2['_main_fmt']}")
            fig = MplFigure(figsize=cfg2["figsize_in"], dpi=PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = core.build_figure(plt, cfg2, spectra, results, self.get_layout(g), fig=fig)
            F.export()
            core.write_results(results, folder_g / f"{name}_results.csv", cfg2)
            written += [folder_g / f"{name}.{e}" for e in [cfg2["_main_fmt"]] + cfg2["extra_formats"]]
            written.append(folder_g / f"{name}_results.csv")
            meth = SI.eps_methods(cfg2, results, spectra, (self.series.get(g) or {}).get("solvent", ""))
            if meth:
                written.append(folder_g / f"{name}_methods.txt")
                written[-1].write_text(meth + "\n", encoding="utf-8")
            try:
                rep = REPORT.write_report(folder_g / f"{name}_report.xlsx", cfg2, self.groups[g], spectra,
                                          results, g, files=self.csv_paths, version=APP_VERSION)
                written.append(Path(rep))
            except PermissionError:
                self.error(T("report_locked", p=folder_g / f"{name}_report.xlsx"))
        if folder is None:
            written = self.place_exports(written)
        return written

    # ------------------------------------------------------------ Schnellauswertung (FB-3)
    def quick_dir(self) -> Path:
        """Internes Projekt für Einzelauswertungen (normales Projekt im Datenordner, erscheint im Startbildschirm)."""
        return IMG.app_data_dir() / "Einzelauswertungen"

    def is_quick(self) -> bool:
        try:
            return bool(self.project_dir) and Path(self.project_dir).parent.resolve() == self.quick_dir().resolve()
        except OSError:
            return False

    def quick_evaluation(self):
        """Startbildschirm „Schnellauswertung“: neue Verbindung „Auswertung JJJJ-MM-TT“ im internen Projekt."""
        from elucida.app import publication as PUB
        import datetime as _dt
        q = self.quick_dir()
        if PUB.is_publication(q) is None:
            q.mkdir(parents=True, exist_ok=True)
            PUB.create(q, T("quick_title"))
        name = PUB.unique_dest(q, core.safe_name(T("quick_name", date=_dt.date.today().isoformat()))).name
        if not self.open_publication(q):
            return False
        self.add_recent_publication(q)
        return self.new_compound_in_publication(name)

    def place_exports(self, files):
        """Exporte ablegen: im Projekt nach figures/, tables/, SI/ – in einer Schnellauswertung in einen gewählten
        Ordner (zuletzt gewählter in QSettings „quick_export_dir“); abgebrochen -> wie sonst ins Projekt."""
        if not self.is_quick():
            return PRJ.place_exports(self.project_dir, files)
        d = QFileDialog.getExistingDirectory(self, T("quick_export"), str(self.settings.value("quick_export_dir", "")
                                                                            or Path.home()))
        if not d:
            return PRJ.place_exports(self.project_dir, files)
        self.settings.setValue("quick_export_dir", d)
        out = []
        for f in map(Path, files):
            if f.exists():
                dst = Path(d) / f.name
                if f.resolve() == dst.resolve():
                    out.append(dst)
                    continue
                if dst.exists():                                # überschreiben wie im Projekt
                    dst.unlink()
                shutil.move(str(f), str(dst))                   # auch über Laufwerke hinweg
                from elucida.formats.ole import copy_editable_companions
                copy_editable_companions(f, dst)                # erst nach der Word-Datei (gesperrt = keine halbe Ablage)
                out.append(dst)
        return out

    # ------------------------------------------------------------ Drag & Drop
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        files = [u.toLocalFile() for u in ev.mimeData().urls()]
        from elucida.app import publication as PUB
        for p in files:
            if PRJ.is_project(p):
                self.open_project(p)
                return
            if PUB.is_publication(p):
                self.open_publication(p)
                return
        # SEC: Spektren haben kein eigenes Dateiformat-Kennzeichen außer der ersten Zeile
        secs = [p for p in files if Path(p).is_file() and (SECMOD.is_bwspec(p) or SECMOD.is_merged(p))]
        if secs and self.ensure_project():
            self.sec_tab.load_spectra(secs)
            self.main_tabs.setCurrentWidget(self.sec_tab)
            files = [p for p in files if p not in secs]
            if not files:
                return
        # X-Ray: CIF-Dateien (jeder data_-Block mit Atomen wird ein Eintrag)
        cifs = [p for p in files if XRAY.is_cif(p)]
        if cifs and self.ensure_project():
            for p in cifs:
                self.xray_tab.load_cif(p)
            self.main_tabs.setCurrentWidget(self.xray_tab)
            files = [p for p in files if p not in cifs]
            if not files:
                return
        # NMR: SVG-Exporte aus MestReNova, Mnova-Dokumente; TopSpin-Ordner (Experiment, Datensatz, mehrere Datensätze)
        # kommen als Rohdaten ins Projekt und werden passenden Spektren zugeordnet
        svgs = [p for p in files if NMR.is_nmr_svg(p)
                or (Path(p).suffix.lower() in (".svg", ".emf") and self.main_tabs.currentWidget() is self.nmr_tab)]
        mnovas = [p for p in files if Path(p).suffix.lower() == ".mnova"]
        exps = [p for p in files if Path(p).is_dir() and NMR.find_experiments(p)]
        if (svgs or exps or mnovas) and self.ensure_project():
            for p in svgs:
                self.nmr_tab.load_svg(p)
            for p in mnovas:
                self.nmr_tab.add_mnova_file(p)
            for p in exps:
                self.nmr_tab.import_topspin(p)
            self.main_tabs.setCurrentWidget(self.nmr_tab)
            files = [p for p in files if p not in svgs and p not in exps and p not in mnovas]
            if not files:
                return
        # DFT: xyz-Geometrien und Ausgaben von ORCA/Gaussian
        xyzs = [p for p in files if DFT.is_xyz(p) or DFT.is_calc(p) or DFT.is_cube(p) or DFT.is_molden(p)]
        if xyzs and self.ensure_project():
            for p in xyzs:
                self.dft_tab.load_xyz(p)
            self.main_tabs.setCurrentWidget(self.dft_tab)
            files = [p for p in files if p not in xyzs]
            if not files:
                return
        # HRMS: MS-Berichte (docx) und Bruker-.d-Ordner; IR + EA: OPUS-Dateien, PDF nur auf dem Tab IR + EA
        ms = [p for p in files if IRMS.is_bruker_d(p) or Path(p).suffix.lower() == ".docx"]
        irms = [p for p in files if IRMS.is_opus(p)
                or (Path(p).suffix.lower() == ".pdf" and self.main_tabs.currentWidget() is self.irms_tab)]
        if (ms or irms) and self.ensure_project():
            for p in ms:
                (self.hrms_tab.load_raw if IRMS.is_bruker_d(p) else self.hrms_tab.load_ms)(p)
            if irms:
                self.irms_tab.load_ir_files(irms)
            self.main_tabs.setCurrentWidget(self.hrms_tab if ms else self.irms_tab)
            files = [p for p in files if p not in ms and p not in irms]
            if not files:
                return
        data = [p for p in files if Path(p).suffix.lower() in {".csv", ".txt"} | core.BINARY_EXT]
        if data:
            self.open_files(data)                     # mehrere Messdateien = ein Datensatz
        for p in files:
            ext = Path(p).suffix.lower()
            if p in data:
                continue
            if not self.current:
                self.error(T("load_first"))
            elif ext in IMG.CHEM_EXT | IMG.VECTOR_EXT:
                self.set_structure(p)
            elif ext in IMG.RASTER_EXT:
                self.set_photo(p)
            else:                                     # nie still fallen lassen
                self.error(T("drop_unknown", name=Path(p).name))

    # ------------------------------------------------------------ Diverses
    def error(self, msg):
        self.log_signal.emit(f"{T('err_title')}: {msg}")
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.critical(self, T("err_title"), str(msg))

    def rebuild_tabs(self):
        self.build_ui()
        self.render()

    def export_current(self):
        key = self._tab_keys[self.main_tabs.currentIndex()]
        if key == "eps":
            return self.export_dialog()
        return getattr(self, self._tab_spec(key)[0]).export_dialog()

    def info(self, msg):
        self.log_signal.emit(msg)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.information(self, T("app_title"), msg)

    def export_datapack(self):
        """Datenpaket (Zip) dieser Verbindung für ein Datenrepositorium (elucida/exchange/datapack.py)."""
        if not self.ensure_project():
            return None
        if not self.maybe_save():
            return False
        from elucida.app.datapack_dialog import DatapackDialog
        dlg = DatapackDialog(self)
        dlg.exec()
        return dlg.report

    def exported(self, folders):
        """Meldung nach einem Export mit Knopf „Ordner öffnen“ (erster Zielordner im Finder/Explorer)."""
        folders = sorted({str(f) for f in folders})
        msg = T("exported_to", p="\n".join(folders))
        self.log_signal.emit(msg)
        self.last_export = folders
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or not folders:
            return
        box = QMessageBox(QMessageBox.Information, T("app_title"), msg, QMessageBox.Ok, self)
        b_open = box.addButton(T("open_folder"), QMessageBox.ActionRole)
        box.exec()
        if box.clickedButton() is b_open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folders[0]))

    # ------------------------------------------------------------ Updates
    def _auto_updates(self):
        return str(self.settings.value("update_auto", True)).lower() not in ("false", "0")

    def check_updates(self, manual=False):
        """Neuestes Release auf GitHub abfragen. Automatisch höchstens einmal pro Tag und still bei
        Fehlern (z. B. offline); über das Hilfe-Menü mit Rückmeldung."""
        import time
        if not manual:
            if not self._auto_updates() or time.time() - float(self.settings.value("update_last", 0) or 0) < 86400:
                return
        # Daemon-Thread statt QThread: beim Beenden während der Abfrage (Netz langsam, DNS ohne Timeout) zerstörte
        # Qt sonst den laufenden QThread -> qFatal/abort -> macOS meldete einen Absturz. Ergebnis per Polling holen.
        import threading
        box = {}

        def work():
            try:
                box["info"] = UPD.fetch_latest(APP_VERSION)
            except Exception as e:
                box["err"] = f"{type(e).__name__}: {e}"

        def poll():
            if not box:
                return
            timer.stop()
            timer.deleteLater()
            if "info" in box:
                self.settings.setValue("update_last", time.time())
                self.show_update(box["info"], manual)
            elif manual:
                QMessageBox.warning(self, T("upd_title"), T("upd_failed", err=box["err"]))
        timer = QTimer(self)
        timer.setInterval(200)
        timer.timeout.connect(poll)
        threading.Thread(target=work, daemon=True).start()
        timer.start()

    def update_text(self, info, manual):
        """Meldungstext oder None (nichts anzeigen). Übersprungene Versionen nur bei manueller Prüfung."""
        if not UPD.is_newer(info["version"], APP_VERSION):
            return T("upd_current", cur=APP_VERSION) if manual else None
        if not manual and self.settings.value("update_skip", "") == info["version"]:
            return None
        return T("upd_available", new=info["version"], cur=APP_VERSION,
                 file=info["asset"] or T("upd_no_asset"))

    def show_update(self, info, manual):
        txt = self.update_text(info, manual)
        if txt is None:
            return
        if not UPD.is_newer(info["version"], APP_VERSION):
            QMessageBox.information(self, T("upd_title"), txt)
            return
        box = QMessageBox(QMessageBox.Information, T("upd_title"), txt, parent=self)
        b_open = box.addButton(T("upd_open"), QMessageBox.AcceptRole)
        b_skip = box.addButton(T("upd_skip"), QMessageBox.DestructiveRole)
        box.addButton(T("upd_later"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is b_open:
            QDesktopServices.openUrl(QUrl(info["url"]))
        elif box.clickedButton() is b_skip:
            self.settings.setValue("update_skip", info["version"])

    def statusBar(self):
        return self._status

    def _place_toast(self, msg=None):
        """Meldung unten rechts über der Abbildung (nimmt keinen Platz im Layout ein)."""
        t = self._toast
        msg = self._status.currentMessage() if msg is None else msg
        if not msg:
            t.hide()
            return
        t.setText(msg)
        t.ensurePolished()
        w = min(t.fontMetrics().horizontalAdvance(msg) + 32, self.width() - 40)
        h = t.fontMetrics().height() + 14
        # in einer Verbindung über der Fußleiste, in der Ecke der Abbildung: der Hauptknopf bleibt frei
        lift = TABS.BAR_MIN_H if self.project_dir else 0
        t.setGeometry(self.width() - w - 24, self.height() - h - 24 - lift, w, h)
        t.show()
        t.raise_()

    def resizeEvent(self, ev):
        side = self.__dict__.get("side")                 # schmale Fenster: Seitenleiste schmaler, Inhalt behält Platz
        if side is not None:
            side.setFixedWidth(240 if self.width() >= 1180 else 204)
        super().resizeEvent(ev)
        self._place_toast()

    def closeEvent(self, ev):
        if not self.maybe_save():
            ev.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        for t in list(self._tasks):                      # laufende Hintergrundarbeit (Freistellung, CDXML) abwarten:
            t.wait()                                     # zerstörter laufender QThread = abort beim Beenden
        super().closeEvent(ev)


# ----------------------------------------------------------------------------
def install_crash_handler():
    def hook(t, v, tb):
        msg = "".join(traceback.format_exception(t, v, tb))
        try:
            (IMG.app_data_dir() / "crash.log").write_text(msg, encoding="utf-8")
        except Exception:
            pass
        if QApplication.instance() and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.critical(None, "Error", msg[-2000:])
        sys.__excepthook__(t, v, tb)
    sys.excepthook = hook


def release_widgets(app):
    """Alle Fenster löschen, solange die QApplication lebt (Qt löscht Kinder mit). Sonst baut PySide beim
    Interpreter-Ende (atexit, destroyQCoreApplication) die übrigen Widgets in beliebiger Reihenfolge ab –
    macOS-Absturz 2.3.7: pure virtual in ~QObject einer QCheckBox. Liste jedes Mal neu von Qt holen."""
    import shiboken6
    if "elucida.app.drawing_editor" in sys.modules:
        sys.modules["elucida.app.drawing_editor"].release_pages(app)
    for _ in range(10000):
        top = [x for x in app.topLevelWidgets() if x.parentWidget() is None]
        if not top:
            break
        shiboken6.delete(top[0])


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        outdir = sys.argv[i + 1] if len(sys.argv) > i + 1 and not sys.argv[i + 1].startswith("--") \
            else "selftest_out"
        from elucida.selftest import selftest
        sys.exit(selftest(outdir, "--selftest-isnet" in sys.argv))
    install_crash_handler()
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args and Path(args[0]).exists():
        w.open_csv(args[0])          # Datei per Doppelklick / Drag auf das Programmsymbol
    rc = app.exec()
    release_widgets(app)
    sys.exit(rc)


if __name__ == "__main__":
    main()
