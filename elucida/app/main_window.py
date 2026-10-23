"""
elucida/app/main_window.py - Grafische Oberfläche der UV-Vis-Auswertung (Windows / macOS / Linux).

Start:      python Elucida.py   (oder python -m elucida)
Selbsttest: python Elucida.py --selftest AUSGABEORDNER [--selftest-isnet]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import html
import re
import traceback
from pathlib import Path

from elucida import APP_NAME, APP_VERSION, ROOT  # noqa: F401  (Versionsnummer nur in elucida/__init__.py)
OLD_APP_NAMES = ("Spectravolt", "UVVisTool")   # 1.16–1.25 bzw. bis 1.15: Einstellungen beim ersten Start übernehmen
SI_PARTS = ("char", "nmr", "figs", "methods", "xray", "dft")   # Teile des SI-Exports (Auswahl im Dialog)
SETTINGS_FILE = None      # Selbsttest: eigene INI-Datei statt der echten Benutzereinstellungen

if "--selftest" in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
import yaml  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure as MplFigure  # noqa: E402
from PySide6.QtCore import QEvent, QSettings, QSize, Qt, QThread, QTimer, Signal  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QImage,  # noqa: E402
                           QGuiApplication, QKeySequence, QPixmap, QTextCursor)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox, QColorDialog, QComboBox,  # noqa: E402
                               QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
                               QFormLayout, QFrame, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                               QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea,
                               QSpinBox, QSplitter, QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem, QTextBrowser,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

from elucida.core import uvvis as core  # noqa: E402
from elucida.core import images as IMG  # noqa: E402
from elucida.app.i18n import T, get_lang, set_lang  # noqa: E402
from elucida.tabs import base as TABS  # noqa: E402
from elucida.app import project as PRJ  # noqa: E402
from elucida.si import excel as REPORT  # noqa: E402
from elucida.app import update as UPD  # noqa: E402
from elucida.core import color as COLOR  # noqa: E402
from elucida.tabs import cv as CVMOD  # noqa: E402
from elucida.tabs import sec as SECMOD  # noqa: E402
from elucida.tabs import epr as EPRMOD  # noqa: E402
from elucida.tabs import hrms as HRMS  # noqa: E402
from elucida.tabs import ir_ea as IRMS  # noqa: E402
from elucida.tabs import xray as XRAY  # noqa: E402
from elucida.tabs import dft as DFT  # noqa: E402
from elucida.tabs import nmr as NMR  # noqa: E402
from elucida.tabs import synthesis as SYN  # noqa: E402
from elucida.si import lines as SI  # noqa: E402
from elucida.app import style as STYLE  # noqa: E402
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

    def _report(self):
        # erst nach allen anderen Release-Handlern auslesen (Label-Drag von matplotlib)
        QTimer.singleShot(0, lambda: self.on_change(self.F.current_layout()))

    def release(self, ev):
        super().release(ev)
        self._report()

    def scroll(self, ev):
        if super().scroll(ev):
            self._report()

    def key(self, ev):
        pass


DEFAULT_GLOB = {"path_length": 1.0, "cutoff": 1.0, "min_points": 3, "bands": "",
                "baseline": "series", "bl_a": 1050.0, "bl_b": 1100.0, "ymax": 1.0,
                "r2": "legend", "show_err": False, "table": True,
                "size": "half_a4", "w_cm": 16.0, "h_cm": 11.0,
                "fmt_pdf": True, "fmt_svg": True, "fmt_png": True,
                "x_auto": True, "x_min": 200.0, "x_max": 1100.0,
                "bands_add": True, "shoulders": False, "show_excl": False, "inset": True,
                "mark_sh": False, "label_index": False, "min_r2": 0.98, "color_show": False, "color_d": 1.0}

UNITS = [("mM", "mM"), ("uM", "µM"), ("mg/mL", "mg/mL"), ("M", "M")]

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


class ConcDialog(QDialog):
    """Konzentrationen je Probe eintragen (wenn sie nicht im Probennamen stehen)."""

    def __init__(self, parent, samples, overrides, default_series):
        super().__init__(parent)
        self.setWindowTitle(T("conc_title"))
        self.samples = samples
        lay = QVBoxLayout(self)
        intro = QLabel(T("conc_intro"))
        intro.setWordWrap(True)
        lay.addWidget(intro)

        unit0 = None
        for s_ in samples:
            o = overrides.get(s_["key"]) or {}
            unit0 = unit0 or o.get("unit") or (s_["parsed"][2] if s_["parsed"] else None)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("unit")))
        self.cmb_unit = QComboBox()
        self.cmb_unit.addItem(T("unit_choose"), None)          # keine stille Vorbelegung
        for key, label in UNITS:
            self.cmb_unit.addItem(label, key)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(unit0)) if unit0 else 0)
        row.addWidget(self.cmb_unit)
        row.addStretch(1)
        lay.addLayout(row)

        self.table = QTableWidget(len(samples), 3)
        self.table.setHorizontalHeaderLabels([T("col_sample"), T("col_series"), T("col_conc")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i, s_ in enumerate(samples):
            o = overrides.get(s_["key"]) or {}
            it = QTableWidgetItem(s_["key"])
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, it)
            series = o.get("series") or (s_["parsed"][0] if s_["parsed"] else default_series)
            self.table.setItem(i, 1, QTableWidgetItem(series))
            c = o.get("conc") or (s_["parsed"][1] if s_["parsed"] and not o.get("skip") else None)
            self.table.setItem(i, 2, QTableWidgetItem(f"{c:g}" if c else ""))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.resizeColumnsToContents()
        lay.addWidget(self.table)

        row = QHBoxLayout()
        row.addWidget(QLabel(T("dil_start")))
        self.sp_start = QDoubleSpinBox(decimals=4, minimum=0.0, maximum=1e6, value=0.0)
        row.addWidget(self.sp_start)
        row.addWidget(QLabel(T("dil_factor")))
        self.sp_fac = QDoubleSpinBox(decimals=3, minimum=1.0, maximum=1000, value=2.0)
        row.addWidget(self.sp_fac)
        b = QPushButton(T("dil_fill"))
        b.clicked.connect(self.fill_dilution)
        row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        hint = QLabel(T("dil_hint"))
        hint.setStyleSheet(HINT_CSS)
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.table.setMinimumHeight(36 + 30 * min(len(samples), 12))
        self.resize(600, 300 + 30 * min(len(samples), 12))

    def fill_dilution(self):
        if self.sp_start.value() <= 0:
            QMessageBox.warning(self, T("conc_title"), T("start_missing"))
            return
        rows = sorted({i.row() for i in self.table.selectedIndexes()}) or list(range(self.table.rowCount()))
        c = self.sp_start.value()
        for r in rows:
            self.table.item(r, 2).setText(f"{c:.6g}")
            c /= self.sp_fac.value()

    def try_accept(self):
        any_conc = any((self.table.item(i, 2).text() or "").strip() for i in range(self.table.rowCount()))
        if any_conc and self.cmb_unit.currentData() is None:
            QMessageBox.warning(self, T("conc_title"), T("unit_missing"))
            return
        self.accept()

    def overrides(self):
        unit = self.cmb_unit.currentData()
        out = {}
        for i, s_ in enumerate(self.samples):
            series = (self.table.item(i, 1).text() or "").strip()
            try:
                c = parse_float(self.table.item(i, 2).text())
            except ValueError:
                c = None
            out[s_["key"]] = {"conc": c, "unit": unit, "series": series} if c else {"skip": True}
        return out


class CompoundDialog(QDialog):
    """Verbindung des Projekts: Name/Probennummer, ChemDraw (Formel und Molmasse daraus), beides änderbar."""

    def __init__(self, parent, comp):
        super().__init__(parent)
        self.setWindowTitle(T("compound_title"))
        self.main = parent
        self.path = comp.get("structure")
        f = make_form(self)
        self.ed_name = QLineEdit(comp.get("name", ""))
        self.ed_name.setPlaceholderText(T("compound_name_ph"))
        f.addRow(T("compound_name"), self.ed_name)
        row = QHBoxLayout()
        self.lbl_struct = QLabel(Path(self.path).name if self.path else "–")
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose)
        row.addWidget(self.lbl_struct, 1)
        row.addWidget(b)
        f.addRow(T("structure"), row)
        self.ed_formula = QLineEdit(comp.get("formula", ""))
        self.ed_formula.setPlaceholderText("C18H20N2")
        f.addRow(T("compound_formula"), self.ed_formula)
        self.ed_mw = QLineEdit(f"{comp['mw']:g}" if comp.get("mw") else "")
        f.addRow(T("molar_mass"), self.ed_mw)
        self.ed_mp = QLineEdit(comp.get("mp", ""))
        self.ed_mp.setPlaceholderText(T("compound_mp_ph"))
        f.addRow(T("compound_mp"), self.ed_mp)
        hint = QLabel(T("compound_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.resize(460, 0)

    def choose(self):
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.main.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.main.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_path(p)

    def set_path(self, p):
        self.path = p
        self.lbl_struct.setText(Path(p).name)
        chem = compound_from_structure(p)
        if chem.get("formula"):
            self.ed_formula.setText(chem["formula"])
        if chem.get("mw"):
            self.ed_mw.setText(f"{chem['mw']:.2f}")
        if not self.ed_name.text().strip():
            self.ed_name.setText(Path(p).stem)

    def result_compound(self):
        return {"name": self.ed_name.text().strip(), "structure": self.path,
                "formula": self.ed_formula.text().strip().replace(" ", ""), "mw": parse_float(self.ed_mw.text()),
                "mp": self.ed_mp.text().strip()}


def compound_from_structure(p):
    """Formel und Molmasse aus einer CDXML (oder der gleichnamigen CDXML neben SVG/PDF/PNG)."""
    p = Path(p)
    src = p if p.suffix.lower() == ".cdxml" else p.with_suffix(".cdxml")
    if not src.exists():
        return {}
    try:
        from elucida.core import chem as CHEM
        c = CHEM.load_cdxml(src)
        return {"formula": c.get("formula"), "mw": c.get("mw")}
    except Exception:
        return {}


class TextFormatDialog(QDialog):
    """Schriften, Labelstil und Rahmen (Menü Format). Gilt für alle Tabs oder – wahlweise – nur für den offenen Tab;
    gezeigt wird nur, was der Tab im Bild überhaupt hat (opts)."""

    ALL_OPTS = ("fonts", "greek", "labels", "label_size", "axes_frame", "struct_frame")

    def __init__(self, parent, tf, own=None, opts=ALL_OPTS, tab_key=None, tab_name=""):
        super().__init__(parent)
        from elucida.app.i18n import TEXTS
        self.setWindowTitle(T("tf_title"))
        self.glob = dict(core.TEXT_DEFAULTS, **(tf or {}))
        self.own = dict(self.glob, **own) if own else None
        lay = QVBoxLayout(self)
        self.cmb_scope = QComboBox()
        self.cmb_scope.addItem(T("tf_scope_global"), "global")
        if tab_key:
            self.cmb_scope.addItem(T("tf_scope_own", tab=tab_name), "own")
            row = QHBoxLayout()
            row.addWidget(QLabel(T("tf_scope")))
            row.addWidget(self.cmb_scope, 1)
            lay.addLayout(row)
        hint = QLabel(T("tf_scope_hint") if tab_key else T("tf_no_text", tab=tab_name))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        lay.addWidget(hint)

        g = QGroupBox(T("tf_grp_fonts"))
        f = QFormLayout(g)
        self.cmb_font, self.cmb_sym = QFontComboBox(), QFontComboBox()
        f.addRow(T("tf_font"), self.cmb_font)
        self.cb_greek = QCheckBox(T("tf_greek"))
        self.cb_greek.toggled.connect(self.cmb_sym.setEnabled)
        f.addRow(T("tf_symbol_font"), self.cmb_sym)
        f.addRow(self.cb_greek)
        if "greek" not in opts:
            for w_ in (self.cmb_sym, self.cb_greek, f.labelForField(self.cmb_sym)):
                w_.setVisible(False)
        g.setVisible("fonts" in opts)
        lay.addWidget(g)

        lk = f"tf_grp_labels_{tab_key}"
        g = QGroupBox(T(lk if lk in TEXTS else "tf_grp_labels"))
        f = QFormLayout(g)
        self.sp_size = QDoubleSpinBox(decimals=1, minimum=0, maximum=40, singleStep=0.5, suffix=" pt")
        self.sp_size.setSpecialValueText(T("tf_auto"))
        f.addRow(T("tf_label_size"), self.sp_size)
        if "label_size" not in opts:
            self.sp_size.setVisible(False)
            f.labelForField(self.sp_size).setVisible(False)
        row = QHBoxLayout()
        self.cb_bold = QCheckBox(T("tf_bold"))
        self.cb_italic = QCheckBox(T("tf_italic"))
        row.addWidget(self.cb_bold)
        row.addWidget(self.cb_italic)
        row.addStretch(1)
        f.addRow("", row)
        self.btn_color = QPushButton()
        self.btn_color.clicked.connect(self.pick_color)
        f.addRow(T("tf_color"), self.btn_color)
        g.setVisible("labels" in opts)
        lay.addWidget(g)

        g = QGroupBox(T("tf_grp_frames"))
        v = QVBoxLayout(g)
        self.cb_axes = QCheckBox(T("tf_axes_frame"))
        self.cb_struct = QCheckBox(T("tf_struct_frame"))
        v.addWidget(self.cb_axes)
        v.addWidget(self.cb_struct)
        self.cb_axes.setVisible("axes_frame" in opts)
        self.cb_struct.setVisible("struct_frame" in opts)
        g.setVisible("axes_frame" in opts or "struct_frame" in opts)
        lay.addWidget(g)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        lay.addWidget(bb)
        self.cmb_scope.setCurrentIndex(1 if (tab_key and own) else 0)
        self._scope = self.cmb_scope.currentData()
        self.load(self.own if self._scope == "own" else self.glob)
        self.cmb_scope.currentIndexChanged.connect(self.scope_changed)

    def scope_changed(self, *_):
        """Beim Umschalten die Werte der jeweiligen Ebene zeigen (eigenes Format startet als Kopie des Standards)."""
        cur = self.result_format()
        if self._scope == "own":
            self.own = cur
        else:
            self.glob = cur
        self._scope = self.cmb_scope.currentData()
        self.load((self.own or dict(self.glob)) if self._scope == "own" else self.glob)

    def load(self, tf):
        tf = dict(core.TEXT_DEFAULTS, **tf)
        self.cmb_font.setCurrentText(tf["font"])
        self.cmb_sym.setCurrentText(tf["symbol_font"])
        self.cb_greek.setChecked(tf["greek"])
        self.cmb_sym.setEnabled(tf["greek"])
        self.sp_size.setValue(tf["label_pt"] or 0)
        self.cb_bold.setChecked(tf["bold"])
        self.cb_italic.setChecked(tf["italic"])
        self.color = tf["color"]
        self._show_color()
        self.cb_axes.setChecked(tf["axes_frame"])
        self.cb_struct.setChecked(tf["struct_frame"])

    def _show_color(self):
        self.btn_color.setText(self.color)
        self.btn_color.setStyleSheet(f"QPushButton {{ color: {self.color}; font-weight: bold; }}")

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, T("tf_color"))
        if c.isValid():
            self.color = c.name()
            self._show_color()

    def restore_defaults(self):
        self.load(core.TEXT_DEFAULTS)

    def result_format(self):
        return {"font": self.cmb_font.currentFont().family(), "symbol_font": self.cmb_sym.currentFont().family(),
                "greek": self.cb_greek.isChecked(), "label_pt": self.sp_size.value(),
                "bold": self.cb_bold.isChecked(), "italic": self.cb_italic.isChecked(), "color": self.color,
                "axes_frame": self.cb_axes.isChecked(), "struct_frame": self.cb_struct.isChecked()}

    def results(self):
        """-> (Standard für alle Tabs, eigenes Format des Tabs oder None)."""
        cur = self.result_format()
        if self.cmb_scope.currentData() == "own":
            return self.glob, cur
        return cur, None


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
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
        self.series = {}               # je Serie: mw, structure, photo, bg, layout, assets
        self.current = None
        self.F = None
        self.dragger = None
        self.hover = None
        self._tasks = []
        self._loading = False
        self.glob = dict(DEFAULT_GLOB)
        self.extra_cache = {}
        self.ov_state, self.fl_state, self.cv_state, self.sec_state, self.epr_state = {}, {}, {}, {}, {}  # leer
        self.irms_state = {}
        self.hrms_state = {}
        self.xray_state = {}
        self.dft_state = {}
        self.nmr_state = {}
        self.syn_state = {}
        self.compound = {}                  # Verbindung des Projekts: name, structure, formula, mw
        self.text_fmt = dict(core.TEXT_DEFAULTS)
        self.tab_fmt = {}                                # eigenes Textformat je Tab (Schlüssel = STATE_KEY / epsilon)
        self._tab_key = "syn"                            # offener Tab (Name, nicht Position)
        self.project_dir = None
        self._undo, self._redo = [], []
        self._restoring = False
        self._saved_snap = None

        self.fig = MplFigure(figsize=FIGSIZE, dpi=PREVIEW_DPI)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFixedSize(int(FIGSIZE[0] * PREVIEW_DPI), int(FIGSIZE[1] * PREVIEW_DPI))
        self.timer = QTimer(self, singleShot=True, interval=400)
        self.timer.timeout.connect(self.render)
        self.autosave_timer = QTimer(self, singleShot=True, interval=800)
        self.autosave_timer.timeout.connect(self.autosave)
        # elucida.json (Characterization) seltener als das Autosave: baut die SI-Zeilen aller Tabs neu
        self.exchange_timer = QTimer(self, singleShot=True, interval=5000)
        self.exchange_timer.timeout.connect(self.write_exchange)

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
        icon = resource_path("assets/icon.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.apply_theme()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
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
        m.addSeparator()
        m.addAction(QAction(T("act_quit"), self, shortcut=QKeySequence.Quit, triggered=self.close))
        me = mb.addMenu(T("menu_edit"))
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
            self.removeToolBar(self.toolbar)
            self.toolbar.setParent(None)                # sofort lösen, gelöscht wird später
            self.toolbar.deleteLater()
        self.toolbar = self.addToolBar(T("toolbar"))
        self.toolbar.setObjectName("mainToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        for act in (act_new, act_open_prj, act_save, self.act_folder, None, self.act_undo, self.act_redo):
            if act is None:
                self.toolbar.addSeparator()
                continue
            keys = act.shortcut().toString(QKeySequence.NativeText)
            act.setToolTip(f"{act.text().rstrip('…')} ({keys})" if keys else act.text())
            self.toolbar.addAction(act)
        # Name des Dateimanagers je System (Finder, Explorer, sonst Standard-Dateimanager, z. B. Dolphin/Nautilus)
        fm = {"darwin": "fm_finder", "win32": "fm_explorer"}.get(sys.platform, "fm_linux")
        self.act_folder.setToolTip(T("act_show_folder_tip", fm=T(fm)))
        self.toolbar.addSeparator()
        self.act_compound = QAction(STYLE.icon("compound"), self.compound_label(), self,
                                    triggered=self.edit_compound)
        self.act_compound.setToolTip(T("compound_tip"))
        self.toolbar.addAction(self.act_compound)
        self.toolbar.widgetForAction(self.act_compound).setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.act_si = QAction(STYLE.icon("export"), T("act_si_short"), self, triggered=self.export_si_dialog)
        self.act_si.setToolTip(T("act_si_tip"))
        self.toolbar.addAction(self.act_si)
        tb_si = self.toolbar.widgetForAction(self.act_si)          # Ziel des Programms: als Hauptknopf hervorheben
        tb_si.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        tb_si.setProperty("accent", True)
        tb_si.style().unpolish(tb_si)
        tb_si.style().polish(tb_si)
        self.act_si.setIcon(STYLE.icon("export", "#FFFFFF"))
        mf = mb.addMenu(T("menu_format"))
        mf.addAction(QAction(T("act_text_format"), self, triggered=self.edit_text_format))
        mt = mf.addMenu(T("menu_theme"))
        grp_t = QActionGroup(self)
        for code in ("system", "light", "dark"):
            act = QAction(T(f"theme_{code}"), self, checkable=True, checked=self._theme_mode() == code)
            act.triggered.connect(lambda _=False, c=code: self.switch_theme(c))
            grp_t.addAction(act)
            mt.addAction(act)
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
        mh.addAction(QAction(T("act_demo"), self, triggered=self.open_demo))
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

        forms = []
        g, body = STYLE.card(T("grp_data"), "data")
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        row = QHBoxLayout()
        self.btn_open = QPushButton(STYLE.icon("open", "#FFFFFF"), T("act_open"))
        self.btn_open.setProperty("accent", True)
        self.btn_open.clicked.connect(self.choose_csv)
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
        row = QHBoxLayout()
        row.addWidget(self.cmb_series, 1)
        b = QPushButton(T("act_conc"))
        b.clicked.connect(self.edit_concentrations)
        row.addWidget(b)
        f.addRow(T("series"), row)
        lv.addWidget(g)

        g, body = STYLE.card(T("grp_compound"), "compound")
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        self.ed_mw = QLineEdit()
        self.ed_mw.setPlaceholderText(T("mw_hint_none"))
        self.ed_mw.editingFinished.connect(self.mw_edited)
        row = QHBoxLayout()
        row.addWidget(self.ed_mw, 1)
        row.addWidget(QLabel("g/mol"))
        f.addRow(T("molar_mass_short"), row)
        self.lbl_chem = QLabel("")
        self.lbl_chem.setWordWrap(True)
        f.addRow("", self.lbl_chem)
        row = QHBoxLayout()
        self.lbl_struct = QLabel("–")
        b1 = QPushButton(T("choose"))
        b1.clicked.connect(self.choose_structure)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(lambda: self.set_structure(None))
        row.addWidget(self.lbl_struct, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        f.addRow(T("structure"), row)
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
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        f.addRow("", self.lbl_thumb)
        # Farbe der Lösung aus dem Spektrum (nur Anzeige, nie in der Abbildung)
        self.cb_color = QCheckBox(T("color_show"))
        self.cb_color.setToolTip(T("color_tip"))
        self.cb_color.toggled.connect(self.color_settings_changed)
        f.addRow(self.cb_color)
        row = QHBoxLayout()
        self.sp_color_c = QDoubleSpinBox(decimals=4, minimum=0.0001, maximum=1e6, singleStep=0.1)
        self.sp_color_d = QDoubleSpinBox(decimals=2, minimum=0.01, maximum=100, singleStep=0.1, suffix=" cm")
        for w_ in (QLabel("c"), self.sp_color_c, QLabel("d"), self.sp_color_d):
            row.addWidget(w_)
        self.w_color_cd = QWidget()
        self.w_color_cd.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        f.addRow("", self.w_color_cd)
        for sp in (self.sp_color_c, self.sp_color_d):
            sp.valueChanged.connect(self.color_settings_changed)
        self.lbl_color = QLabel()
        self.lbl_color.setFixedHeight(36)
        self.lbl_color_info = QLabel()
        self.lbl_color_info.setWordWrap(True)
        self.lbl_color_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow("", self.lbl_color)
        f.addRow("", self.lbl_color_info)
        self._color_spectra = None
        lv.addWidget(g)

        g, body = STYLE.card(T("grp_eval"), "eval")
        f = make_form(body)
        f.setContentsMargins(0, 0, 0, 0)
        forms.append(f)
        self.sp_d = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=100, singleStep=0.1, suffix=" cm")
        f.addRow(T("path_length_short"), self.sp_d)
        self.ed_solvent = QLineEdit()                    # je Serie; für SI-Zeile und Bildunterschrift
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
        self.cb_shoulders = QCheckBox(T("find_shoulders"))
        fa.addRow(self.cb_shoulders)
        f.addRow(self.sec_eval)
        compact(self.sp_d, self.sp_cut, self.sp_min, self.sp_r2)
        lv.addWidget(g)

        g, body = STYLE.card(T("grp_plot"), "plot")
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
        for cb in (self.cb_err, self.cb_marksh, self.cb_lidx, self.cb_inset, self.cb_tab, self.cb_excl):
            fa.addRow(cb)
        row = QHBoxLayout()
        self.cb_pdf, self.cb_svg, self.cb_png = QCheckBox("PDF"), QCheckBox("SVG"), QCheckBox("PNG")
        for cb in (self.cb_pdf, self.cb_svg, self.cb_png):
            row.addWidget(cb)
        row.addStretch(1)
        fa.addRow(T("formats"), row)
        f.addRow(self.sec_plot)
        lv.addWidget(g)

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
        # Exportieren bleibt unten sichtbar, auch wenn die Spalte gescrollt wird
        row = QHBoxLayout()
        row.setContentsMargins(8, 6, 8, 6)
        row.addWidget(TABS.reset_button(self.reset_layout, self.reset_defaults))
        b = QPushButton(T("si_copy_methods"))
        b.setToolTip(T("si_copy_methods_tip"))
        b.clicked.connect(self.copy_eps_methods)
        row.addWidget(b)
        row.addStretch(1)
        self.btn_export = QPushButton(STYLE.icon("export", "#FFFFFF"), T("btn_export"))
        self.btn_export.setProperty("accent", True)
        self.btn_export.clicked.connect(self.export_dialog)
        self.btn_export.setToolTip(T("btn_export_tip"))
        self.btn_export.setDefault(True)
        row.addWidget(self.btn_export)
        left_col = QWidget()
        cv = QVBoxLayout(left_col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(lscroll, 1)
        bar = QFrame(objectName="bottomBar")
        bar.setLayout(row)
        cv.addWidget(bar)
        # so breit wie der Inhalt, sonst schneidet die Spalte rechts ab (macOS blendet die Leiste aus)
        lscroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_col.setMinimumWidth(max(380, left.minimumSizeHint().width()
                                     + lscroll.verticalScrollBar().sizeHint().width() + 4))

        # ---- rechte Seite
        self.canvas_host = TABS.CanvasHost(self.canvas, self.fig)
        self.tabs = QTabWidget()                      # wie die anderen Tabs: Abbildung | Ergebnisse | SI-Zeile
        self.tabs.setDocumentMode(True)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([T("col_lam"), T("col_n"), T("col_coeff"),
                                              T("col_intercept"), T("col_r2"), T("col_cut"), T("col_warn")])
        for c_ in range(6):                           # Spaltenköpfe nicht abschneiden („Achsenabschnitt“)
            self.table.horizontalHeader().setSectionResizeMode(c_, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
                                   | QTableWidget.SelectedClicked)
        self.table.setToolTip(T("cut_tip"))
        self.table.itemChanged.connect(self.cutoff_edited)
        self._row_keys = []
        old_log = self.log.toPlainText() if hasattr(self, "log") else ""
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setPlainText(old_log)
        g_res = QGroupBox()
        QVBoxLayout(g_res).addWidget(self.table)
        si_w = QGroupBox()
        si_l = QVBoxLayout(si_w)
        self.txt_si = QTextBrowser()
        si_l.addWidget(self.txt_si)
        hint = QLabel(T("si_uv_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        si_l.addWidget(hint)
        b = QPushButton(T("uv_copy"))
        b.clicked.connect(lambda: IRMS.copy_rich(*self._uv_line))
        si_l.addWidget(b)
        self._uv_line = ("", "")
        # Protokoll: Hilfe → Protokoll (eigenes Fenster), kein Reiter mehr
        # Leer-Zustand: Anleitung (was herauskommt, welche Dateien, Schritte) statt weißer Fläche
        empty = TABS.EmptyGuide("eps", (T("act_open"), self.choose_csv))
        empty_wrap = QWidget()
        QVBoxLayout(empty_wrap).addWidget(empty)
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(empty_wrap)
        self.preview_stack.addWidget(self.canvas_host)
        self.preview_stack.setCurrentIndex(1 if self.current and self.current in self.groups else 0)
        self.tabs.addTab(self.preview_stack, T("tab_figure"))
        self.tabs.addTab(TABS.result_page(g_res), T("tab_results"))
        self.tabs.addTab(TABS.result_page(si_w), T("tab_si_line"))
        right = self.tabs
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left_col)
        split.addWidget(right)
        split.setSizes([left_col.minimumWidth(), 920])
        self.column_fit = STYLE.fit_column(left, lscroll, bar, left_col, split, floor=380)   # nie abgeschnitten
        self.eps_page = split
        self.ov_tab = TABS.OverlayTab(self, self.ov_state)
        self.fl_tab = TABS.FluoTab(self, self.fl_state)
        self.cv_tab = CVMOD.CVTab(self, self.cv_state)
        self.sec_tab = SECMOD.SECTab(self, self.sec_state)
        self.epr_tab = EPRMOD.EPRTab(self, self.epr_state)
        self.hrms_tab = HRMS.HRMSTab(self, self.hrms_state)
        self.irms_tab = IRMS.IRMSTab(self, self.irms_state)
        self.xray_tab = XRAY.XrayTab(self, self.xray_state)
        self.syn_tab = SYN.SynthTab(self, self.syn_state)
        self.nmr_tab = NMR.NMRTab(self, self.nmr_state)
        self.dft_tab = DFT.DFTTab(self, self.dft_state)
        # Reihenfolge wie die SI: Synthese, Charakterisierung, Spektroskopie, Elektrochemie, Struktur, Rechnung
        self.main_tabs = QTabWidget()
        self._tab_keys = []
        for key, page, label in (("syn", self.syn_tab, "tab_syn"), ("nmr", self.nmr_tab, "tab_nmr"),
                                 ("irms", self.irms_tab, "tab_irms"), ("hrms", self.hrms_tab, "tab_hrms"),
                                 ("eps", split, "tab_eps"), ("overlay", self.ov_tab, "tab_overlay"),
                                 ("fluo", self.fl_tab, "tab_fluo"), ("cv", self.cv_tab, "tab_cv"),
                                 ("sec", self.sec_tab, "tab_sec"), ("epr", self.epr_tab, "tab_epr"),
                                 ("xray", self.xray_tab, "tab_xray"), ("dft", self.dft_tab, "tab_dft")):
            self.main_tabs.addTab(page, T(label))
            self._tab_keys.append(key)
        self.main_tabs.setCurrentIndex(self._tab_keys.index(self._tab_key) if self._tab_key in self._tab_keys else 0)
        self.main_tabs.currentChanged.connect(lambda i: setattr(self, "_tab_key", self._tab_keys[i]))
        self.main_tabs.currentChanged.connect(                    # Vorlagen (CIF aus X-Ray) aktuell halten
            lambda i: self.dft_tab.fill_refs() if self.main_tabs.widget(i) is self.dft_tab else None)
        for i in range(self.main_tabs.count()):
            STYLE.tidy(self.main_tabs.widget(i))
        self.center = QStackedWidget()
        self.center.addWidget(self.welcome_page())          # 0: ohne Projekt
        self.center.addWidget(self.nav_bar())               # 1: Tabs
        self.setCentralWidget(self.center)
        self.center.setCurrentIndex(1 if self.project_dir else 0)

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
        self.ed_bands.editingFinished.connect(self.changed)
        for w in (self.cmb_bl, self.cmb_r2):
            w.currentIndexChanged.connect(self.changed)
        for w in (self.cb_err, self.cb_tab, self.cb_bands_add, self.cb_shoulders, self.cb_excl, self.cb_inset,
                  self.cb_marksh, self.cb_lidx):
            w.toggled.connect(self.changed)
        for w in (self.sp_min, self.sp_r2):
            w.valueChanged.connect(self._update_sections)
        self.cmb_r2.currentIndexChanged.connect(self._update_sections)
        for w in (self.cb_shoulders, self.cb_err, self.cb_marksh, self.cb_lidx, self.cb_inset, self.cb_tab,
                  self.cb_excl, self.cb_pdf, self.cb_svg, self.cb_png):
            w.toggled.connect(self._update_sections)
        self._update_sections()

    def _update_sections(self, *_):
        """Eingeklappte Bereiche markieren, wenn dort etwas vom Standard abweicht."""
        d = DEFAULT_GLOB
        self.sec_images.set_changed(self.cmb_bg.currentData() not in (None, "auto"))
        self.sec_eval.set_changed(self.sp_min.value() != d["min_points"]
                                  or abs(self.sp_r2.value() - d["min_r2"]) > 1e-9
                                  or self.cb_shoulders.isChecked() != d["shoulders"])
        self.sec_plot.set_changed(self.cmb_r2.currentData() != d["r2"] or any(
            cb.isChecked() != d[k] for cb, k in (
                (self.cb_err, "show_err"), (self.cb_marksh, "mark_sh"), (self.cb_lidx, "label_index"),
                (self.cb_inset, "inset"),
                (self.cb_tab, "table"), (self.cb_excl, "show_excl"), (self.cb_pdf, "fmt_pdf"),
                (self.cb_svg, "fmt_svg"), (self.cb_png, "fmt_png"))))

    def apply_globals(self):
        self._loading = True
        gl = self.glob
        self.sp_d.setValue(gl["path_length"])
        self.sp_cut.setValue(gl["cutoff"])
        self.sp_min.setValue(gl["min_points"])
        self.sp_r2.setValue(gl.get("min_r2", 0.98))
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
        self.glob.update(path_length=self.sp_d.value(), cutoff=self.sp_cut.value(),
                         min_points=self.sp_min.value(), min_r2=self.sp_r2.value(), bands=self.ed_bands.text().strip(),
                         baseline=self.cmb_bl.currentData(), bl_a=self.sp_bla.value(),
                         bl_b=self.sp_blb.value(), ymax=self.sp_ymax.value(),
                         r2=self.cmb_r2.currentData(), show_err=self.cb_err.isChecked(),
                         table=self.cb_tab.isChecked(), size=self.cmb_size.currentData(),
                         w_cm=self.sp_w.value(), h_cm=self.sp_h.value(),
                         fmt_pdf=self.cb_pdf.isChecked(), fmt_svg=self.cb_svg.isChecked(),
                         fmt_png=self.cb_png.isChecked(), x_auto=self.cb_xauto.isChecked(),
                         bands_add=self.cb_bands_add.isChecked(), shoulders=self.cb_shoulders.isChecked(),
                         show_excl=self.cb_excl.isChecked(), inset=self.cb_inset.isChecked(),
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

    def apply_series_widgets(self):
        self._loading = True
        st = self.series.get(self.current)
        self.ed_mw.setText(f"{st['mw']:g}" if st and st["mw"] else "")
        self.lbl_struct.setText(Path(st["structure"]).name if st and st["structure"] else "–")
        self.lbl_photo.setText(Path(st["photo"]).name if st and st["photo"] else "–")
        self.cmb_bg.setCurrentIndex(self.cmb_bg.findData(st["bg"] if st else "auto"))
        info = st.get("chem_info", "") if st else ""
        unit = self.units.get(self.current) if st else None
        warn = bool(st and st.get("chem_warn"))
        if unit and unit != "mg/mL":
            info = (info + "\n" if info else "") + T("mw_unused", u="µM" if unit == "uM" else unit)
        mw_missing = unit == "mg/mL" and not (st and st["mw"])
        if mw_missing:
            info = (info + "\n" if info else "") + T("mw_needed")
            warn = True
        self.ed_mw.setStyleSheet("border: 2px solid #d9534f;" if mw_missing else "")
        self.lbl_chem.setText(info)
        self.lbl_chem.setVisible(bool(info))          # keine leere Zeile unter der Molmasse
        # fehlende Molmasse = Fehler (rot); Hinweise zur Zeichnung (aus CDXML statt ChemDraw-Bild) nur orange
        self.lbl_chem.setStyleSheet(WARN_CSS if mw_missing else STYLE.NOTE_CSS if warn else "")
        pa = st.get("photo_asset") if st else None
        self.lbl_thumb.setPixmap(rgba_to_pixmap(pa["rgba"]) if pa else QPixmap())
        self.lbl_thumb.setVisible(bool(pa))              # ohne Foto keine Leerzeile
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

    def _theme_mode(self):
        return self.settings.value("ui/theme", "system") or "system"

    def apply_theme(self):
        STYLE.apply(self._theme_mode(), IMG.app_data_dir() / "theme")

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

    NAV_GROUPS = (("nav_grp_syn", ("syn", "nmr", "irms", "hrms")), ("nav_grp_uv", ("eps", "overlay", "fluo")),
                  ("nav_grp_ec", ("cv", "sec", "epr")), ("nav_grp_struct", ("xray", "dft")))

    def nav_bar(self):
        """Tabs in vier Gruppen wie die SI (Leiste oben statt Reiter): kostet Höhe statt Breite – die Abbildung
        ist in der Breite begrenzt, eine Seitenleiste würde sie um ~20 % verkleinern."""
        from PySide6.QtWidgets import QButtonGroup
        bar = QFrame(objectName="navBar")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(10, 4, 10, 6)
        hb.setSpacing(4)
        grp = QButtonGroup(bar)
        self.nav_buttons = {}
        for gi, (head, keys) in enumerate(self.NAV_GROUPS):
            if gi:
                sep = QFrame(objectName="navSep")
                sep.setFixedWidth(1)
                hb.addSpacing(8)
                hb.addWidget(sep)
                hb.addSpacing(8)
            col = QVBoxLayout()
            col.setSpacing(1)
            col.addWidget(QLabel(T(head).upper(), objectName="navGroup"), 0, Qt.AlignHCenter)   # mittig über der Gruppe
            row = QHBoxLayout()
            row.setSpacing(2)
            for k in keys:
                i = self._tab_keys.index(k)
                b = QPushButton(self.main_tabs.tabText(i), objectName="navTab", checkable=True)
                b.clicked.connect(lambda _=False, i=i: self.main_tabs.setCurrentIndex(i))
                grp.addButton(b)
                row.addWidget(b)
                self.nav_buttons[i] = b
            col.addLayout(row)
            hb.addLayout(col)
        hb.addStretch(1)
        self.main_tabs.currentChanged.connect(lambda i: self.nav_buttons[i].setChecked(True))
        self.nav_buttons[self.main_tabs.currentIndex()].setChecked(True)
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
        self.settings.setValue("last_dir", str(Path(path).parent))
        self.groups, self.units, self.series, self.conc = {}, {}, {}, {}
        _, _, missing = core.group_samples(samples, self.conc, Path(path).stem)
        if missing and ask and not self.edit_concentrations(rebuild=False):
            pass
        if not self.rebuild_groups():
            self.lbl_file.setText(self.files_label())
            self.error(T("conc_none"))
            return False
        self.lbl_file.setText(self.files_label())
        self.apply_compound_defaults()
        self.apply_globals()
        self.apply_series_widgets()
        self.render()
        return True

    def edit_concentrations(self, rebuild=True):
        if not self.samples:
            self.error(T("load_first"))
            return False
        dlg = ConcDialog(self, self.samples, self.conc, Path(self.csv_path).stem)
        if dlg.exec() != QDialog.Accepted:
            return False
        self.conc = dlg.overrides()
        if rebuild:
            self.rebuild_groups()
            self.apply_series_widgets()
            self.render()
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
                "color_c")
        return {"eps": {"files": list(self.csv_paths), "glob": dict(self.glob), "conc": self.conc,
                        "series": {g: {k: st.get(k) for k in keys} for g, st in self.series.items()},
                        "current": self.current},
                "overlay": self.ov_state, "fluo": self.fl_state, "cv": self.cv_state, "sec": self.sec_state, "epr": self.epr_state,
                "irms": self.irms_state, "hrms": self.hrms_state, "xray": self.xray_state,
                "dft": self.dft_state, "nmr": self.nmr_state, "syn": self.syn_state,
                "compound": dict(self.compound),
                "tab": self._tab_key,
                "text": dict(self.text_fmt), "text_tabs": {k: dict(v) for k, v in self.tab_fmt.items()}}

    def set_state(self, state):
        """Zustand übernehmen (Projekt laden, Undo/Redo)."""
        state = json.loads(json.dumps(state))          # entkoppeln
        eps = state.get("eps") or {}
        old_series = self.series
        self.glob = dict(DEFAULT_GLOB, **(eps.get("glob") or {}))
        self.conc = eps.get("conc") or {}
        self.csv_paths = [p for p in eps.get("files") or [] if Path(p).exists()]
        self.csv_path = self.csv_paths[0] if self.csv_paths else None
        self.groups, self.units, self.series, self.samples = {}, {}, {}, []
        self.ov_state.clear()
        self.ov_state.update(state.get("overlay") or {})
        self.fl_state.clear()
        self.fl_state.update(state.get("fluo") or {})
        self.cv_state.clear()
        self.cv_state.update(state.get("cv") or {})
        self.sec_state.clear()
        self.sec_state.update(state.get("sec") or {})
        self.epr_state.clear()
        self.epr_state.update(state.get("epr") or {})
        self.irms_state.clear()
        self.irms_state.update(state.get("irms") or {})
        self.hrms_state.clear()
        hr = state.get("hrms")
        if hr is None:                                 # Projekte vor 1.21: MS-Teil stand im Tab IR + MS
            ir = state.get("irms") or {}
            hr = {k: ir[k] for k in ("ms_file", "ms_raw", "ms_rt", "adduct", "found") if k in ir}
        self.hrms_state.update(hr)
        self.xray_state.clear()
        self.xray_state.update(state.get("xray") or {})
        self.dft_state.clear()
        self.dft_state.update(state.get("dft") or {})
        self.nmr_state.clear()
        self.nmr_state.update(state.get("nmr") or {})
        self.syn_state.clear()
        self.syn_state.update(state.get("syn") or {})
        self.compound = dict(state.get("compound") or {})
        self.text_fmt = dict(core.TEXT_DEFAULTS, **(state.get("text") or {}))
        self.tab_fmt = {k: dict(v) for k, v in (state.get("text_tabs") or {}).items()}
        tab = state.get("tab", "syn")
        if isinstance(tab, int):                         # bis 1.23 gespeichert als Position (alte Reihenfolge)
            old = ("eps", "overlay", "fluo", "cv", "sec", "epr", "hrms", "irms", "xray", "dft")
            tab = old[tab] if 0 <= tab < len(old) else "syn"
        self._tab_key = tab
        self.current = eps.get("current")
        self.build_ui()
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
        self.apply_globals()
        self.apply_series_widgets()
        if self.csv_paths:
            self.render()
        else:
            self.fig.clear()
            self.canvas.draw_idle()

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
            self._undo.append(snap)
            del self._undo[:-200]
            self._redo.clear()
            self._update_undo_actions()
            self.update_title()
            if self.project_dir:
                self.autosave_timer.start()

    def _restore(self, snap):
        self._restoring = True
        self.set_state(json.loads(snap))
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
        self.set_state(state)
        QTimer.singleShot(200, self._after_load)

    def _after_load(self):
        self._restoring = False
        self._init_undo()

    def undo(self):
        if len(self._undo) > 1:
            self._redo.append(self._undo.pop())
            self._restore(self._undo[-1])

    def redo(self):
        if self._redo:
            self._undo.append(self._redo.pop())
            self._restore(self._undo[-1])

    def _update_undo_actions(self):
        if hasattr(self, "act_undo"):
            self.act_undo.setEnabled(len(self._undo) > 1)
            self.act_redo.setEnabled(bool(self._redo))

    def is_dirty(self):
        if self._restoring:
            return False
        return bool(self._undo) and self._undo[-1] != self._saved_snap

    def welcome_page(self):
        """Startbildschirm ohne Projekt: worum es geht, Neues Projekt / Öffnen / Beispielprojekt, zuletzt geöffnet."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.addStretch(1)
        card = QFrame(objectName="card")
        card.setMaximumWidth(620)
        v = QVBoxLayout(card)
        v.setContentsMargins(32, 28, 32, 28)
        v.setSpacing(12)
        head = QHBoxLayout()
        icon = resource_path("assets/icon.png")
        if icon.exists():
            lb = QLabel()
            lb.setPixmap(QIcon(str(icon)).pixmap(64, 64))
            head.addWidget(lb)
        t = QLabel(f"<span style='font-size:22px; font-weight:bold'>{APP_NAME}</span><br>{T('welcome_sub')}")
        t.setWordWrap(True)
        head.addWidget(t, 1)
        v.addLayout(head)
        row = QHBoxLayout()
        b_new = QPushButton(STYLE.icon("new", "#FFFFFF"), T("act_new_project"))
        b_new.setProperty("accent", True)
        b_new.clicked.connect(self.new_project)
        b_open = QPushButton(STYLE.icon("open"), T("act_open_project"))
        b_open.clicked.connect(self.open_project_dialog)
        b_demo = QPushButton(T("act_demo"))
        b_demo.setToolTip(T("act_demo_tip"))
        b_demo.clicked.connect(self.open_demo)
        for b in (b_new, b_open, b_demo):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lst_recent = QListWidget()
        self.lst_recent.setMaximumHeight(150)
        self.lst_recent.itemActivated.connect(lambda it: self.open_project(it.data(Qt.UserRole)))
        self.lst_recent.itemClicked.connect(lambda it: self.open_project(it.data(Qt.UserRole)))
        self.lbl_recent = QLabel(f"<b>{T('welcome_recent')}</b>")
        v.addWidget(self.lbl_recent)
        v.addWidget(self.lst_recent)
        hint = QLabel(T("welcome_hint", url=TABS.README_URL + ("README.de.md" if get_lang() == "de" else "README.md")
                        + "#" + TABS.gh_anchor(T("readme_quickstart"))))
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card, 4)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(2)
        self.fill_recent_list()
        return page

    def fill_recent_list(self):
        if getattr(self, "lst_recent", None) is None:
            return
        self.lst_recent.clear()
        rec = [r for r in self.recent() if PRJ.is_project(r)]
        for r in rec:
            it = QListWidgetItem(f"{Path(r).name}  –  {Path(r).parent}")
            it.setData(Qt.UserRole, r)
            self.lst_recent.addItem(it)
        self.lst_recent.setVisible(bool(rec))
        self.lbl_recent.setVisible(bool(rec))

    def open_demo(self, folder=None):
        """Beispielprojekt mit künstlichen Daten (alle Tabs) anlegen und öffnen."""
        from elucida.app import demo as DEMO
        self.maybe_save()
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

    def show_quickstart(self):
        url = (TABS.README_URL + ("README.de.md" if get_lang() == "de" else "README.md") + "#"
               + TABS.gh_anchor(T("readme_quickstart")))
        QDesktopServices.openUrl(QUrl(url))

    def update_title(self):
        if getattr(self, "center", None) is not None:
            self.center.setCurrentIndex(1 if self.project_dir else 0)
            self.fill_recent_list()
        if getattr(self, "act_folder", None) is not None:
            self.act_folder.setEnabled(bool(self.project_dir))
        name = Path(self.project_dir).name if self.project_dir else T("no_project_title")
        if self.compound.get("name"):
            name = f"{self.compound['name']} · {name}"
        self.setWindowTitle(f"{name} – {T('app_title')} {APP_VERSION}")

    # -- Verbindung des Projekts (Vorgabe für alle Tabs) ------------------------------------
    def compound_label(self):
        c = self.compound
        if not (c.get("name") or c.get("formula")):
            return T("compound_none")
        return T("compound_set", c=" · ".join(x for x in (c.get("name"), c.get("formula")) if x))

    def edit_compound(self):
        if not self.ensure_project():
            return
        dlg = CompoundDialog(self, self.compound)
        if dlg.exec() != QDialog.Accepted:
            return
        self.set_compound(dlg.result_compound())

    def set_compound(self, comp):
        """Verbindung übernehmen und als Vorgabe eintragen, wo noch nichts gewählt ist."""
        comp = dict(comp)
        if comp.get("structure") and self.project_dir:
            comp["structure"] = self.import_file(comp["structure"], PRJ.STRUCTURES)
        self.compound = comp
        self.apply_compound_defaults()
        if hasattr(self, "act_compound"):
            self.act_compound.setText(self.compound_label())
        self.update_title()
        if hasattr(self, "irms_tab"):
            self.irms_tab.compound_changed()
        if hasattr(self, "hrms_tab"):
            self.hrms_tab.compound_changed()
        self.render()
        self.push_undo()

    def apply_compound_defaults(self):
        """ε-Serien ohne Struktur/Molmasse und der Fluoreszenz-Tab bekommen die Verbindung des Projekts.
        Was schon gewählt ist, bleibt (Vergleichsprojekte, mehrere Verbindungen in einer Cary-Datei)."""
        c = self.compound
        p = c.get("structure")
        for g, st in self.series.items():
            if p and not st.get("structure") and Path(p).exists():
                self.set_structure(p, g, render=False)
            if not st.get("mw") and c.get("mw"):
                st["mw"] = c["mw"]
        if p and not self.fl_state.get("structure") and Path(p).exists():
            self.fl_state["structure"] = p
            if hasattr(self, "fl_tab"):
                self.fl_tab.timer.start()

    # -- Projektordner zuerst: Dateien werden beim Laden kopiert, Änderungen automatisch gespeichert
    def ensure_project(self):
        if self.project_dir:
            return True
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return False
        if QMessageBox.question(self, T("app_title"), T("need_project_q")) != QMessageBox.Yes:
            return False
        return self.choose_project_folder()

    def choose_project_folder(self):
        d = QFileDialog.getExistingDirectory(self, T("choose_project_dir"),
                                             self.settings.value("last_project_dir", str(Path.home())))
        if not d:
            return False
        if PRJ.is_project(d):
            return self.open_project(d, ask=False)
        return self.create_project(d)

    def create_project(self, d):
        try:
            pdir = PRJ.create(d)
        except OSError as e:
            self.error(str(e))
            return False
        self.project_dir = str(pdir)
        self.settings.setValue("last_project_dir", str(pdir.parent))
        self._load_state_into_ui({})
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

    def write_exchange(self):
        """elucida.json für Characterization neu schreiben (nach Speichern und Exporten); Fehler nur ins Protokoll.
        Nicht, während ein Menü/eine Liste offen ist oder die Maus gedrückt wird (Tabs aktualisieren dabei Felder)."""
        self.exchange_timer.stop()
        if not self.project_dir:
            return None
        if self._restoring or QApplication.activePopupWidget() is not None or \
                QApplication.mouseButtons() != Qt.NoButton:
            self.exchange_timer.start()                # später noch einmal versuchen
            return None
        from elucida.exchange import characterization as EXCH
        try:
            return EXCH.write(self.project_dir, EXCH.build(self))
        except Exception as e:
            self.log_signal.emit(f"{EXCH.FILE}: {type(e).__name__}: {e}")
            return None

    def import_file(self, path, sub):
        if not self.project_dir:
            return str(Path(path).resolve())
        new = PRJ.import_file(self.project_dir, path, sub)
        if Path(new) != Path(path).resolve():
            self.log_signal.emit("  " + T("file_imported", src=Path(path).name, dst=Path(new).relative_to(
                self.project_dir).as_posix()))
        return new

    def maybe_save(self):
        """Vor Neu/Öffnen/Schließen: ausstehendes automatisches Speichern sofort ausführen."""
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self.autosave()
        if self.exchange_timer.isActive():
            self.write_exchange()
        return True

    def autosave(self):
        if not self.project_dir or self._restoring:
            return
        try:
            PRJ.write(self.project_dir, self.get_state())
            self._saved_snap = self._undo[-1] if self._undo else None
            self.statusBar().showMessage(T("autosaved"), 2000)
            self.exchange_timer.start()
        except Exception as e:
            self.log_signal.emit(f"{T('err_title')}: {e}")

    def new_project(self):
        self.maybe_save()
        self.choose_project_folder()

    def open_project_dialog(self):
        self.maybe_save()
        d = QFileDialog.getExistingDirectory(self, T("act_open_project"),
                                             self.settings.value("last_project_dir", str(Path.home())))
        if not d:
            return
        if PRJ.is_project(d):
            self.open_project(d, ask=False)
        elif QMessageBox.question(self, T("app_title"), T("make_project_q", p=d)) == QMessageBox.Yes:
            self.create_project(d)

    def open_project(self, path, ask=True):
        pdir = PRJ.is_project(path)
        if pdir is None:
            self.error(T("no_project", p=path))
            return False
        self.maybe_save()
        try:
            PRJ.backup(pdir)                           # Sicherung: project.uvvis.bak
            state = PRJ.load(pdir)
        except Exception as e:
            self.error(f"{type(e).__name__}: {e}")
            return False
        for m in PRJ.missing_files(state):
            self.log_signal.emit("  " + T("missing_file", p=m))
        self.project_dir = str(pdir)
        self._load_state_into_ui(state)
        self.add_recent(pdir)
        self.settings.setValue("last_project_dir", str(pdir.parent))
        return True

    def save_project(self):
        if not self.project_dir:
            return self.ensure_project()
        self.autosave_timer.stop()
        self.autosave()
        self.write_exchange()
        return True

    def save_project_copy(self):
        """Projekt (inkl. aller Dateien) als Kopie in einen neuen Ordner schreiben, z. B. als Zwischenstand."""
        if not self.project_dir:
            return self.error(T("load_first"))
        d = QFileDialog.getExistingDirectory(self, T("act_save_copy"), str(Path(self.project_dir).parent))
        if d:
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
            self.exchange_timer.start()
        self.log_signal.emit(T("project_saved", p=pdir))
        return True

    def show_project_folder(self):
        if self.project_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_dir))

    def add_recent(self, pdir):
        rec = [str(pdir)] + [r for r in self.recent() if r != str(pdir)]
        self.settings.setValue("recent_projects", json.dumps(rec[:10]))
        self.fill_recent_menu()

    def recent(self):
        try:
            return [r for r in json.loads(self.settings.value("recent_projects", "[]") or "[]")]
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
        for w_ in (self.w_color_cd, self.lbl_color, self.lbl_color_info):
            w_.setVisible(on)
        if not on or not self._color_spectra or self.current not in self.series:
            return
        spectra, cfg = self._color_spectra
        if not spectra:
            return
        st = self.series[self.current]
        unit = cfg["conc_unit"].replace("uM", "µM")
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
            return "epsilon", name, TextFormatDialog.ALL_OPTS
        if isinstance(w_, TABS.FigureTab):
            return w_.STATE_KEY, name, w_.TEXT_OPTS
        return None, name, ()

    def edit_text_format(self):
        key, name, opts = self.text_tab()
        dlg = TextFormatDialog(self, self.text_fmt, self.tab_fmt.get(key), opts or TextFormatDialog.ALL_OPTS,
                               key, name)
        if dlg.exec() != QDialog.Accepted:
            return
        self.text_fmt, own = dlg.results()
        if key:
            if own is None:
                self.tab_fmt.pop(key, None)
            else:
                self.tab_fmt[key] = own
        for tf in [self.text_fmt] + list(self.tab_fmt.values()):
            for k_ in ("font", "symbol_font"):
                if core.first_font([tf[k_]], None) is None:
                    self.log_signal.emit("  " + T("tf_missing", name=tf[k_]))
        self.render()
        for t in (self.ov_tab, self.fl_tab, self.cv_tab, self.sec_tab, self.epr_tab, self.irms_tab, self.hrms_tab,
                  self.xray_tab, self.dft_tab):
            t.render()
        self.push_undo()

    def render(self):
        has_data = bool(self.current and self.current in self.groups)
        self.preview_stack.setCurrentIndex(1 if has_data else 0)
        if not has_data:
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
            unit = cfg2["conc_unit"].replace("uM", "µM")
            curves = [dict(x=s_["x"], y=s_["y"], val=s_["y"], name=f"c = {s_['c']:g} {unit}") for s_ in spectra]
            self.hover = TABS.HoverReadout(self.F, curves, self.show_hover, self.hover_text, self.pick_band)
            self.sync_image_sizes(self.F.current_layout())
            self.canvas.draw_idle()
            self.fill_table(results, cfg2)
            self.update_si_line(results, cfg2)
            self._color_spectra = (spectra, cfg2)
            self.update_color()
            self._last = (cfg2, results)
            self.push_undo()
        except Exception as e:
            self.log_signal.emit(traceback.format_exc())
            self.statusBar().showMessage(f"{T('err_title')}: {e}", 8000)

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
        stored = self.get_layout(self.current)
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
        self.txt_si.setHtml(self._uv_line[1] or T("si_uv_none"))

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
            except Exception:
                continue
            line = SI.uvvis_line(results, cfg2, (self.series.get(g) or {}).get("solvent", ""))
            if line[0]:
                out.append((g, line))
        return out

    def eps_methods_text(self, groups=None):
        """SI-Text zur ε-Bestimmung je Serie (englisch, si.lines.eps_methods)."""
        out = []
        for g in (groups or list(self.groups)):
            try:
                cfg2, spectra, results = core.prepare_series(self.make_cfg(g), self.groups[g], g)
            except Exception:
                continue
            txt = SI.eps_methods(cfg2, results, spectra, (self.series.get(g) or {}).get("solvent", ""))
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

    def export_si_dialog(self):
        """Auswahl der Teile (Charakterisierung, X-Ray, DFT), dann export_si. Die Auswahl wird gemerkt."""
        if not self.ensure_project():
            return
        avail = self.si_available()
        saved = self.settings.value("si_parts", "char,nmr,figs,methods,xray,dft")
        saved = set(str(saved).split(",")) if saved else set()
        if not self.settings.value("si_parts_figs"):         # neu in 1.24: Abbildungen einmalig mit auswählen
            saved |= {"nmr", "figs"}
            self.settings.setValue("si_parts_figs", 1)
        if not self.settings.value("si_parts_methods"):      # neu in 1.24.1: Methodentexte einmalig mit auswählen
            saved |= {"methods"}
            self.settings.setValue("si_parts_methods", 1)
        dlg = QDialog(self)
        dlg.setWindowTitle(T("act_export_si").rstrip(" …"))
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(T("si_parts_head")))
        cbs = {}
        for k in SI_PARTS:
            cb = QCheckBox(T("si_part_" + k))
            cb.setEnabled(avail[k])
            cb.setChecked(avail[k] and k in saved)
            if not avail[k]:
                cb.setToolTip(T("si_part_empty"))
            cbs[k] = cb
            v.addWidget(cb)
        row = QHBoxLayout()                                   # Schriftart aller Word-Exporte (Größe fest 11 pt)
        cmb_font = QFontComboBox()
        cmb_font.setCurrentFont(QFont(str(self.settings.value("si_font", "Arial") or "Arial")))
        cmb_font.setToolTip(T("si_font_tip"))
        row.addWidget(QLabel(T("si_font")))
        row.addWidget(cmb_font, 1)
        v.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        parts = [k for k, cb in cbs.items() if cb.isChecked()]
        self.settings.setValue("si_font", cmb_font.currentFont().family())
        SI.set_font(cmb_font.currentFont().family())
        self.settings.setValue("si_parts", ",".join(k for k, cb in cbs.items() if cb.isChecked() or not avail[k]
                                                   and k in saved))
        if parts:
            self.export_si(parts)

    def export_si(self, parts=SI_PARTS):
        """SI-Abschnitt der Verbindung als Word-Datei: Charakterisierungsabsatz (m.p.; IR; HR-MS; UV-Vis;
        Elementaranalyse), Kristalldaten, ausgewählte Parameter und Bildunterschriften aus dem X-Ray-Tab, DFT-Rechnungen
        (zweispaltig) – je nach Auswahl."""
        if not self.ensure_project():
            return
        try:
            blocks, missing = self.si_blocks(parts)
            pdir = Path(self.project_dir)
            name = core.safe_name(self.export_name())
            p = SI.write_docx(PRJ.export_dir(pdir, PRJ.SI_DIR) / f"{name}_SI.docx", blocks)
        except PermissionError as e:
            return self.error(T("report_locked", p=getattr(e, "filename", "")))
        except Exception as e:
            self.log_signal.emit(traceback.format_exc())
            return self.error(str(e))
        self.write_exchange()
        msg = T("si_written", p=str(p))
        if missing:
            msg += "\n" + T("si_missing", parts=", ".join(missing))
        self.info(msg)

    def si_blocks(self, parts=SI_PARTS):
        """-> (Blöcke für SI.write_docx, fehlende Teile)."""
        comp = self.compound or {}
        title = self.syn_tab.st.get("name") or comp.get("name") or Path(self.project_dir or ".").name
        blocks, missing, plain = [], [], ""
        if "char" in parts:
            blocks, missing, plain = self.si_char_blocks(comp, title)
        elif title:
            blocks = [("heading", title)]
        self._si_plain = plain
        if "nmr" in parts and self.nmr_tab.spectra() and self.project_dir:
            blocks += [("pagebreak",)] + self.nmr_tab.docx_blocks(PRJ.work_dir(self.project_dir, "si"))
        if "figs" in parts and self.project_dir:
            figs = self.si_figure_blocks(PRJ.work_dir(self.project_dir, "si"), title)
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

    def si_methods_blocks(self):
        """Abschnitt „Data processing and fitting“: dieselben Methodentexte wie „SI-Text kopieren“ (nur benutzte
        Schritte, aktuelle Parameter, dann Ergebnisse) für alle Tabs, die fitten; je Technik ein Absatz mit fettem
        Titel. Leer, wenn nirgends gefittet wurde."""
        self.collect_globals()
        items = [("UV-Vis absorption spectroscopy", self.eps_methods_text() if self.groups else "")]
        for title, t in (("Cyclic voltammetry", self.cv_tab), ("UV-Vis spectroelectrochemistry", self.sec_tab),
                         ("EPR spectroscopy", self.epr_tab)):
            try:
                txt = t.methods_text() if t.figure_spec() is not None else ""   # Ergebnisse/Fits aktuell
            except Exception:
                self.log_signal.emit(traceback.format_exc())
                txt = ""
            items.append((title, txt))
        blocks = []
        for title, txt in items:
            paras = [p.strip() for p in (txt or "").split("\n\n") if p.strip()]
            for k, p in enumerate(paras):
                blocks.append(("char", (f"<b>{title}.</b> " if k == 0 else "") + SI.methods_html(p)))
        return [("heading", "Data processing and fitting")] + blocks if blocks else []

    def figure_tabs(self):
        """Tabs mit Abbildung in der Reihenfolge der SI (Charakterisierung, dann Spektroskopie, Elektrochemie)."""
        return [self.irms_tab, self.hrms_tab, self.ov_tab, self.fl_tab, self.cv_tab, self.sec_tab, self.epr_tab]

    def si_figure_blocks(self, out_dir, name):
        """Abbildungen aller Tabs mit Daten (ε je Serie, IR, HR-MS, Overlay, Fluoreszenz, CV, SEC, EPR), immer zwei je
        Seite (SI.two_per_page verkleinert, wo nötig), jede mit „Figure Sn: …“."""
        figs = self.si_eps_figures(out_dir, name)
        for t in self.figure_tabs():
            try:
                fb = t.si_figure(out_dir, name)
                if fb and t.si_setup_text():                 # Aufbau-Absatz der Methode (lokal hinterlegt)
                    fb = [("char", SI.chem_html(t.si_setup_text()))] + fb
                figs += fb
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
            cap = (f"UV-Vis spectra of <b>{html.escape(name)}</b>"
                   + (f" in {SI.chem_html(solv)}" if solv else "")
                   + f", measured in {cfg2['path_length_cm']:g} cm quartz cuvettes.")
            if not solv:
                self.log_signal.emit(T("si_uv_no_solvent", g=g))
            out += [img, ("figcap", cap)]
        return out

    def si_char_parts(self, comp):
        """Zeilen des Charakterisierungsabsatzes in SI-Reihenfolge -> ([(Art, Klartext, HTML)], fehlende Teile).
        Art: mp, nmr_<Kern>, ir, hrms, uvvis, ea (auch für die Austauschdatei elucida.json)."""
        parts, missing = [], []
        if comp.get("mp"):
            mp = re.sub(r"(?i)^m\.?\s*p\.?\s*", "", comp["mp"]).strip()
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
        for key, lab in (("IR", "IR"), ("HR-MS-", "HR-MS"), ("Elemental", "EA")):
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
                for t_title, t_name, t_head, t_rows in xt.param_tables(e):
                    blocks += [("tabcap", t_title, t_name), ("params", t_head, t_rows)]
                    if any("^{a}" in r_[-1] for r_ in t_rows):
                        blocks.append(("note", "^{a} " + XRAY.CALC_NOTE))
                    blocks.append(("gap",))
            h_, r_ = xt.crystal_table()
            r_ = [[c_.replace(", ", "\n") if row_[0] == "Index ranges" else c_ for c_ in row_] for row_ in r_]
            names = [e.get("name") or e["block"] for e in es]
            blocks += [("tabcap", "Crystal data and structure refinement", ", ".join(names)), ("crystal", h_, r_)]
        return blocks

    def fill_table(self, results, cfg):
        sym = "ε [M⁻¹ cm⁻¹]" if core.conc_factor(cfg) else "a [L g⁻¹ cm⁻¹]"
        self.table.blockSignals(True)
        self.table.setHorizontalHeaderLabels([T("col_lam"), T("col_n"), sym, T("col_intercept"),
                                              T("col_r2"), T("col_cut"), T("col_warn")])
        self.table.setRowCount(len(results))
        self._row_keys = []
        for i, r in enumerate(results):
            ft = r["fit"]
            lam = f"{r['lam']:g}" + (" (sh)" if r.get("shoulder") else "")
            cut = r.get("cutoff", cfg["max_abs_fit"])
            if ft:
                v, e = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg))
                b, be = core.fmt_ve(ft["intercept"], ft["se_intercept"])
                cells = [lam, str(ft["n"]), f"{v} ± {e}" if e else v,
                         f"{b} ± {be}" if be else b, f"{ft['r2']:.5f}", f"{cut:g}", "; ".join(r["warnings"])]
            else:
                cells = [lam, str(len(r["used"])), "–", "–", "–", f"{cut:g}",
                         T("no_fit", n=len(r["used"]), cut=cut, min=cfg["min_fit_points"])]
            for j, c in enumerate(cells):
                it = QTableWidgetItem(c)
                if j < 6:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j == 0:                                   # Häkchen = im Bild anzeigen
                    it.setFlags((it.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
                    hidden = int(round(r["lam_requested"])) in set(cfg.get("band_hidden") or [])
                    it.setCheckState(Qt.Unchecked if hidden else Qt.Checked)
                elif j != 5:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    if j == 4 and ft and ft["r2"] < cfg["min_r2"]:   # unter R²-Schwelle -> nicht im Bild
                        it.setBackground(QColor("#f4cccc"))
                        it.setForeground(QColor("#000000"))
                        it.setToolTip(T("r2_below", min=cfg["min_r2"]))
                elif abs(cut - cfg["max_abs_fit"]) > 1e-9:
                    it.setBackground(QColor("#fff2cc"))
                    it.setForeground(QColor("#000000"))
                self.table.setItem(i, j, it)
            self._row_keys.append(int(round(r["lam_requested"])))
        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

    def cutoff_edited(self, item):
        """Cutoff pro Bande aus der Ergebnistabelle (leer = globaler Cutoff); Häkchen in Spalte λ
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
        self.write_exchange()

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
            written = PRJ.place_exports(self.project_dir, written)
        return written

    # ------------------------------------------------------------ Drag & Drop
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        files = [u.toLocalFile() for u in ev.mimeData().urls()]
        for p in files:
            if PRJ.is_project(p):
                self.open_project(p)
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
        # NMR: SVG-Exporte aus MestReNova; Bruker-Experimentordner gehören zum gewählten Spektrum
        svgs = [p for p in files if NMR.is_nmr_svg(p)
                or (Path(p).suffix.lower() == ".svg" and self.main_tabs.currentWidget() is self.nmr_tab)]
        exps = [p for p in files if self.main_tabs.currentWidget() is self.nmr_tab and NMR.bruker_dir(p) is not None]
        if (svgs or exps) and self.ensure_project():
            for p in svgs:
                self.nmr_tab.load_svg(p)
            for p in exps:
                if self.nmr_tab.current() is not None:
                    self.nmr_tab.set_bruker(self.nmr_tab.current(), p)
            self.main_tabs.setCurrentWidget(self.nmr_tab)
            files = [p for p in files if p not in svgs and p not in exps]
            if not files:
                return
        # DFT: xyz-Geometrien und Ausgaben von ORCA/Gaussian
        xyzs = [p for p in files if DFT.is_xyz(p) or DFT.is_calc(p)]
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
            for p in irms:
                self.irms_tab.load_ir(p)
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

    # ------------------------------------------------------------ Diverses
    def error(self, msg):
        self.log_signal.emit(f"{T('err_title')}: {msg}")
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.critical(self, T("err_title"), str(msg))

    def rebuild_tabs(self):
        self.build_ui()
        self.render()

    def export_current(self):
        cur = self.main_tabs.currentWidget()
        for tab in (self.ov_tab, self.fl_tab, self.cv_tab, self.sec_tab, self.epr_tab, self.hrms_tab, self.irms_tab,
                    self.xray_tab, self.dft_tab, self.nmr_tab, self.syn_tab):
            if cur is tab:
                return tab.export_dialog()
        return self.export_dialog()

    def info(self, msg):
        self.log_signal.emit(msg)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.information(self, T("app_title"), msg)

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
        t = Task(lambda: UPD.fetch_latest(APP_VERSION), self)
        self._tasks.append(t)

        def done(info):
            self.settings.setValue("update_last", time.time())
            self.show_update(info, manual)

        def failed(msg):
            if manual:
                QMessageBox.warning(self, T("upd_title"), T("upd_failed", err=msg))
        t.done.connect(done)
        t.failed.connect(failed)
        t.finished.connect(lambda: self._tasks.remove(t))
        t.start()

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
        t.setGeometry(self.width() - w - 24, self.height() - h - 24, w, h)
        t.show()
        t.raise_()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._place_toast()

    def closeEvent(self, ev):
        if not self.maybe_save():
            ev.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
