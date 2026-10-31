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
from PySide6.QtCore import QEvent, QFileSystemWatcher, QSettings, QSize, Qt, QThread, QTimer, Signal  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QIcon, QImage,  # noqa: E402
                           QGuiApplication, QKeySequence, QPixmap, QTextCursor)
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox, QColorDialog, QComboBox,  # noqa: E402
                               QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
                               QFormLayout, QFrame, QGroupBox, QHBoxLayout, QInputDialog,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
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
        self.ed_note = QLineEdit(comp.get("note", ""))                 # nur intern: Startbildschirm, Titel, elucida.json
        self.ed_note.setPlaceholderText(T("compound_note_ph"))
        self.ed_note.setToolTip(T("compound_note_tip"))
        f.addRow(T("compound_note"), self.ed_note)
        row = QHBoxLayout()
        self.lbl_struct = QLabel(Path(self.path).name if self.path else "–")
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose)
        row.addWidget(self.lbl_struct, 1)
        row.addWidget(b)
        self.chemdraw = False                            # „In ChemDraw bearbeiten“ gedrückt (nach dem Schließen öffnen)
        b_cd = QPushButton(T("chemdraw_edit"))
        b_cd.setToolTip(T("chemdraw_edit_tip"))
        b_cd.clicked.connect(self._chemdraw)
        row.addWidget(b_cd)
        f.addRow(T("structure"), row)
        self.ed_formula = QLineEdit(comp.get("formula", ""))
        self.ed_formula.setPlaceholderText("C18H20N2")
        f.addRow(T("compound_formula"), self.ed_formula)
        self.ed_mw = QLineEdit(f"{comp['mw']:g}" if comp.get("mw") else "")
        f.addRow(T("molar_mass"), self.ed_mw)
        self.ed_mp = QLineEdit(comp.get("mp", ""))
        self.ed_mp.setPlaceholderText(T("compound_mp_ph"))
        self.cb_oil = QCheckBox(T("compound_oil"))                    # Öl: m.p. <25 °C
        self.cb_oil.setToolTip(T("compound_oil_tip"))
        self.cb_oil.setChecked(bool(comp.get("oil")))
        self.ed_mp.setEnabled(not self.cb_oil.isChecked())
        self.cb_oil.toggled.connect(lambda on: self.ed_mp.setEnabled(not on))
        mp_row = QHBoxLayout()
        mp_row.addWidget(self.ed_mp, 1)
        mp_row.addWidget(self.cb_oil)
        f.addRow(T("compound_mp"), mp_row)
        self.cb_known = QCheckBox(T("compound_known"))                # Publikation: Checkliste nur ¹H/¹³C
        self.cb_known.setChecked(bool(comp.get("known")))
        self.cb_known.setToolTip(T("compound_known_tip"))
        self.ed_lit = QLineEdit(comp.get("lit", ""))
        self.ed_lit.setPlaceholderText(T("compound_lit_ph"))
        self.ed_lit.setEnabled(self.cb_known.isChecked())
        self.cb_known.toggled.connect(self.ed_lit.setEnabled)
        f.addRow("", self.cb_known)
        f.addRow(T("compound_lit"), self.ed_lit)
        hint = QLabel(T("compound_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        # Höhe über heightForWidth: resize(460, 0) nahm nur die Mindesthöhe des Formulars, die den umbrechenden
        # Hinweis mit einer Zeile rechnet – die letzte Zeile unter „Literatur“ war abgeschnitten (macOS)
        self.resize(460, max(self.sizeHint().height(), f.totalHeightForWidth(460)))

    def _chemdraw(self):
        self.chemdraw = True
        self.accept()

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
                "mp": self.ed_mp.text().strip(), "oil": self.cb_oil.isChecked(), "note": self.ed_note.text().strip(),
                "known": self.cb_known.isChecked(), "lit": self.ed_lit.text().strip() if self.cb_known.isChecked() else ""}


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
        self.publication_dir = None                      # Publikation (übergeordneter Ordner), falls bekannt
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
        # ChemDraw: Struktur/Schema der Verbindung überwachen; gespeichert -> automatisch übernehmen
        self.cd_watch = QFileSystemWatcher(self)
        self.cd_watch.fileChanged.connect(self._cd_changed)
        self._cd_kinds = {}                              # Pfad -> "structure" | "scheme"
        self._cd_pending = set()
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
            self.removeToolBar(self.toolbar)
            self.toolbar.setParent(None)                # sofort lösen, gelöscht wird später
            self.toolbar.deleteLater()
        self.toolbar = self.addToolBar(T("toolbar"))
        self.toolbar.setObjectName("mainToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(18, 18))
        if self._mac_title:                              # Platz für die Ampelknöpfe, freie Stellen ziehen das Fenster
            inset = QWidget(objectName="titleInset")
            inset.setFixedWidth(MAC.INSET)
            self._title_inset = self.toolbar.addWidget(inset)      # QAction: sie steuert die Sichtbarkeit
            self.toolbar.installEventFilter(MAC.TitleDrag(self))
            self._fit_title_bar()
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
        self.center.addWidget(self.welcome_page())          # 0: ohne Projekt
        self.center.addWidget(self.nav_bar())               # 1: Tabs
        from elucida.app.publication_view import PublicationPage
        self.pub_page = PublicationPage(self)               # 2: Publikation (Verbindungen, Exporte)
        self.pub_page.set_publication(self.publication_dir)
        self.center.addWidget(self.pub_page)
        self.setCentralWidget(self.center)
        self.center.setCurrentIndex(self._center_index())

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

    # Tabs: Schlüssel im Zustand -> (Attribut, Klasse, Attribut des Zustands, Textschlüssel); ε ist Teil des Fensters
    _TAB_ORDER = ("syn", "nmr", "irms", "hrms", "eps", "overlay", "fluo", "cv", "sec", "epr", "xray", "dft")
    _TAB_BUILD_ORDER = ("overlay", "fluo", "cv", "sec", "epr", "hrms", "irms", "xray", "syn", "nmr", "dft")

    def _tab_spec(self, key):
        return {"overlay": ("ov_tab", TABS.OverlayTab, "ov_state", "tab_overlay"),
                "fluo": ("fl_tab", TABS.FluoTab, "fl_state", "tab_fluo"),
                "cv": ("cv_tab", CVMOD.CVTab, "cv_state", "tab_cv"),
                "sec": ("sec_tab", SECMOD.SECTab, "sec_state", "tab_sec"),
                "epr": ("epr_tab", EPRMOD.EPRTab, "epr_state", "tab_epr"),
                "hrms": ("hrms_tab", HRMS.HRMSTab, "hrms_state", "tab_hrms"),
                "irms": ("irms_tab", IRMS.IRMSTab, "irms_state", "tab_irms"),
                "xray": ("xray_tab", XRAY.XrayTab, "xray_state", "tab_xray"),
                "syn": ("syn_tab", SYN.SynthTab, "syn_state", "tab_syn"),
                "nmr": ("nmr_tab", NMR.NMRTab, "nmr_state", "tab_nmr"),
                "dft": ("dft_tab", DFT.DFTTab, "dft_state", "tab_dft")}[key]

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
        old.setParent(None)
        old.deleteLater()
        return new

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
        # Pfadleiste: ⌂ Übersicht › Projekt › Verbindung ▾ (jede Stufe anklickbar, Verbindungen des Projekts im Menü)
        self.btn_home = QPushButton("⌂ " + T("nav_home"), objectName="navTab")
        self.btn_home.setToolTip(T("act_to_overview"))
        self.btn_home.clicked.connect(self.go_home)
        self.btn_pub = QPushButton(objectName="navTab")      # Projekt (nur bei Verbindungen darin)
        self.btn_pub.setToolTip(T("act_to_publication"))
        self.btn_pub.clicked.connect(self._crumb_pub)
        self.btn_comp = QPushButton(objectName="navTab")     # andere Verbindungen des Projekts
        self.btn_comp.setToolTip(T("nav_switch_tip"))
        self.comp_menu = QMenu(self.btn_comp)
        self.comp_menu.aboutToShow.connect(self._fill_comp_menu)
        self.btn_comp.setMenu(self.comp_menu)
        self.crumb_seps = [QLabel("›", objectName="navGroup"), QLabel("›", objectName="navGroup")]
        crumbs = QHBoxLayout()
        crumbs.setSpacing(2)
        for w_ in (self.btn_home, self.crumb_seps[0], self.btn_pub, self.crumb_seps[1], self.btn_comp):
            crumbs.addWidget(w_, 0, Qt.AlignVCenter)
        hb.addLayout(crumbs)
        self._update_crumbs()
        self.btn_pub_sep = QFrame(objectName="navSep")
        self.btn_pub_sep.setFixedWidth(1)
        hb.addSpacing(6)
        hb.addWidget(self.btn_pub_sep)
        hb.addSpacing(6)
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
        self._eps_held = {}
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
                "color_c", "solvent")
        held = self._eps_held
        return {"eps": {"files": list(self.csv_paths) + [p for p in held.get("files", []) if p not in self.csv_paths],
                        "glob": dict(self.glob), "conc": self.conc,
                        "series": dict(held.get("series", {}),
                                       **{g: {k: st.get(k) for k in keys} for g, st in self.series.items()}),
                        "current": self.current},
                "overlay": self.ov_state, "fluo": self.fl_state, "cv": self.cv_state, "sec": self.sec_state, "epr": self.epr_state,
                "irms": self.irms_state, "hrms": self.hrms_state, "xray": self.xray_state,
                "dft": self.dft_state, "nmr": self.nmr_state, "syn": self.syn_state,
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
        tab = state.get("tab", "syn")
        if isinstance(tab, int):                         # bis 1.23 gespeichert als Position (alte Reihenfolge)
            old = ("eps", "overlay", "fluo", "cv", "sec", "epr", "hrms", "irms", "xray", "dft")
            tab = old[tab] if 0 <= tab < len(old) else "syn"
        self._tab_key = tab
        if changed is None:
            self.current = eps.get("current")
            self.build_ui()
        else:
            if hasattr(self, "act_compound"):              # Werkzeugleiste: Verbindung des Projekts
                self.act_compound.setText(self.compound_label())
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
        """Startbildschirm ohne Projekt: worum es geht, Neues Projekt / Öffnen / Beispielprojekt und eine Übersicht der
        zuletzt geöffneten Projekte (Verbindung, Analytik, Stand; Suche, Rechtsklick-Menü)."""
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(24, 28, 24, 20)
        col = QWidget()
        col.setMaximumWidth(1500)                   # wächst mit dem Fenster (FB-1), bleibt auf großen Schirmen lesbar
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        head = QHBoxLayout()
        head.setSpacing(16)
        icon = self.app_icon()
        if icon.exists():
            lb = QLabel()
            lb.setPixmap(QIcon(str(icon)).pixmap(72, 72))
            head.addWidget(lb, 0, Qt.AlignTop)
        t = QLabel(f"<span style='font-size:26px; font-weight:bold'>{APP_NAME}</span><br>{T('welcome_sub')}")
        t.setWordWrap(True)
        head.addWidget(t, 1)
        v.addLayout(head)
        row = QHBoxLayout()
        b_new = QPushButton(STYLE.icon("new"), T("act_new_project"))           # einzelne Verbindung
        b_new.clicked.connect(self.new_project)
        b_open = QPushButton(STYLE.icon("open"), T("act_open_project"))
        b_open.clicked.connect(self.open_project_dialog)
        b_pub = QPushButton(STYLE.icon("new", "#FFFFFF"), T("act_new_publication"))   # Projekt (mehrere Verbindungen)
        b_pub.setProperty("accent", True)
        b_pub.setToolTip(T("act_new_publication_tip"))
        b_pub.clicked.connect(self.new_publication)
        b_demo = QPushButton(T("act_demo"))
        b_demo.setToolTip(T("act_demo_tip"))
        b_demo.clicked.connect(self.open_demo)
        b_demo_pub = QPushButton(T("act_demo_pub"))
        b_demo_pub.setToolTip(T("act_demo_pub_tip"))
        b_demo_pub.clicked.connect(self.open_demo_publication)
        for b in (b_pub, b_new, b_open, b_demo_pub, b_demo):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.ed_recent = QLineEdit()                    # Suche über alle Verbindungen aller bekannten Projekte
        self.ed_recent.setPlaceholderText(T("recent_search_ph"))
        self.ed_recent.setClearButtonEnabled(True)
        self.ed_recent.textChanged.connect(self._filter_recent)
        v.addWidget(self.ed_recent)
        v.addSpacing(6)
        self.lbl_pubs = QLabel(objectName="recentHead")
        v.addWidget(self.lbl_pubs)
        self.pub_box = QVBoxLayout()
        self.pub_box.setSpacing(8)
        v.addLayout(self.pub_box)
        row = QHBoxLayout()
        self.lbl_recent = QLabel(objectName="recentHead")
        row.addWidget(self.lbl_recent)
        row.addStretch(1)
        v.addLayout(row)
        self.recent_box = QVBoxLayout()
        self.recent_box.setContentsMargins(0, 0, 4, 0)
        self.recent_box.setSpacing(8)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.addLayout(self.recent_box)
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
        hint = QLabel(T("welcome_hint", url=TABS.README_URL + ("README.de.md" if get_lang() == "de" else "README.md")
                        + "#" + TABS.gh_anchor(T("readme_quickstart"))))
        hint.setWordWrap(True)
        hint.setOpenExternalLinks(True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        outer.addStretch(1)
        outer.addWidget(col, 12)
        outer.addStretch(1)
        self.recent_rows = []
        self.pub_rows = []
        self.fill_recent_list()
        return page

    def fill_recent_list(self):
        """Projektliste des Startbildschirms neu füllen (nur vorhandene Projekte, neueste zuerst)."""
        if getattr(self, "recent_box", None) is None:
            return
        self._search_cache = None                       # Suche neu aufbauen (Liste hat sich geändert)
        self.lbl_recent_empty.setText(T("recent_none"))
        from elucida.app import welcome as WEL
        from elucida.app import publication as PUB
        from elucida.app.publication_view import PublicationRow, publication_info
        for r in self.recent_rows + self.pub_rows:
            r.setParent(None)
            r.deleteLater()
        self.recent_rows, self.pub_rows = [], []
        pubs = []
        for p in self.recent_publications():          # Publikationen oben, je höchstens drei sichtbar
            try:
                info = publication_info(p)
            except Exception:
                info = None
            if info is not None:
                pubs.append(info)
        for info in pubs[:3]:
            row = PublicationRow(info)
            row.opened.connect(lambda p: self.open_publication(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._pub_menu(r, pos))
            self.pub_box.addWidget(row)
            self.pub_rows.append(row)
        self.lbl_pubs.setText(f"<b>{T('welcome_publications')}</b>")
        self.lbl_pubs.setVisible(bool(pubs))
        infos = [i for i in (WEL.project_info(p) for p in self.recent()) if i is not None]
        for info in infos:
            pub = PUB.publication_of(info["path"])
            if pub is not None:
                info["publication"] = re.sub(r"<[^>]+>", "", PUB.paper_title(PUB.load(pub))) or pub.name
            row = WEL.RecentRow(info)
            row.opened.connect(lambda p: self.open_project(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._recent_menu(r, pos))
            self.recent_box.addWidget(row)
            self.recent_rows.append(row)
        self.lbl_recent.setText(f"<b>{T('welcome_recent')}</b>" + (f"  <span style='color:gray'>{len(infos)}</span>"
                                                                   if infos else ""))
        self.lbl_recent_empty.setVisible(not infos)
        self._filter_recent(self.ed_recent.text())

    def focus_search(self):
        """Strg+F: in einem Projekt dessen Filter, sonst die Suche der Übersicht (offene Verbindung wird geschlossen
        – gespeichert ist sie ohnehin)."""
        if self.publication_dir and not self.project_dir:
            self.pub_page.ed_filter.setFocus()
            self.pub_page.ed_filter.selectAll()
            return
        if self.project_dir or self.publication_dir:
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
        for r in self.recent_rows:
            r.setParent(None)
            r.deleteLater()
        self.recent_rows = []
        for r in self.pub_rows:
            r.setVisible(r.matches(t))
        self.lbl_pubs.setVisible(any(r.matches(t) for r in self.pub_rows))
        hits = [i for i in self._search_cache if WEL.info_matches(i, t)][:60]
        for info in hits:
            row = WEL.RecentRow(info)
            row.opened.connect(lambda p: self.open_project(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._recent_menu(r, pos))
            self.recent_box.addWidget(row)
            self.recent_rows.append(row)
        self.lbl_recent.setText(f"<b>{T('search_hits')}</b>  <span style='color:gray'>{len(hits)}</span>")
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
            self.close_project()
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
        self.maybe_save()
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

    # Maus im offenen Tab (dieselben Texte wie unter den Tabs); Synthese/NMR ohne Mausaktionen im Bild
    _MOUSE_HINTS = {"eps": ("drag_hint",), "hrms": ("ms_pick_hint", "drag_hint_tab"), "syn": (), "nmr": (),
                    "xray": ("xr_mouse_hint", "drag_hint_tab"), "dft": ("dft_mouse_hint", "drag_hint_tab")}

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
        url = (TABS.README_URL + ("README.de.md" if get_lang() == "de" else "README.md") + "#"
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

    def _fit_title_bar(self):
        """macOS: Werkzeugleiste so hoch wie die Titelleiste; im Vollbild (ohne Ampelknöpfe) kein Einzug."""
        inset = getattr(self, "_title_inset", None)
        if inset is None or self._title_h is None:
            return
        full = bool(self.windowState() & Qt.WindowFullScreen)
        on = bool(self._title_h) and not full
        if self._title_h:
            MAC.set_toolbar_visible(self, not full)
        inset.setVisible(on)
        self.toolbar.setMinimumHeight(self._title_h if on else 0)

    def update_title(self):
        if getattr(self, "center", None) is not None:
            self.center.setCurrentIndex(self._center_index())
            if self._center_index() == 0:                # Liste nur lesen, wenn sie zu sehen ist
                self.fill_recent_list()
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
        if self.compound.get("note"):                  # Notiz zur Verbindung (z. B. „Radikalkation von 6m“)
            name = f"{name} ({self.compound['note']})"
        if self.publication_dir:                         # Teil einer Publikation
            name = f"{name} – {self.publication_title()}"
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
        if dlg.chemdraw:                                 # „In ChemDraw bearbeiten“: Dialog zu, ChemDraw auf
            self.edit_in_chemdraw("structure")

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

    def chemdraw_saved(self, path):
        """In ChemDraw gespeichert: Struktur (Formel, Molmasse, Bilder) bzw. Schema neu übernehmen. Leere Vorlagen
        zählen nicht. ChemDraw ersetzt die Datei beim Speichern – dann wieder überwachen."""
        key = str(Path(path).resolve())
        if Path(key).exists() and key not in self.cd_watch.files():
            self.cd_watch.addPath(key)
        if not self.project_dir or not PRJ.cdxml_has_content(key):
            return False
        kind = self._cd_kinds.get(key, "structure")
        if kind == "scheme":
            self.syn_tab.set_scheme(key)
        else:
            comp = dict(self.compound)
            comp["structure"] = key
            comp.update({k: v for k, v in compound_from_structure(key).items() if v})
            self.set_compound(comp)
        self.statusBar().showMessage(T("chemdraw_taken", name=Path(key).name), 6000)
        self.log_signal.emit(T("chemdraw_taken", name=Path(key).name))
        return True

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
        for key in ("irms", "hrms"):                   # ungebaute Tabs lesen die Verbindung beim Bauen
            if self._built(key):
                getattr(self, self._tab_spec(key)[0]).compound_changed()
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
            if self._built("fluo"):
                self.fl_tab.timer.start()

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
        self._load_state_into_ui({})
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
        self._flush_edits()
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self.autosave()
        if self.exchange_timer.isActive():
            self.write_exchange()
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
            self._saved_snap = self._undo[-1] if self._undo else None
            self.statusBar().showMessage(T("autosaved"), 2000)
            self.exchange_timer.start()
        except Exception as e:
            self.log_signal.emit(f"{T('err_title')}: {e}")

    def new_project(self):
        """Neue Verbindung – immer in einem Projekt (Nutzerwunsch): im offenen Projekt, sonst Projekt wählen/anlegen."""
        self.maybe_save()
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
            self.close_project()                       # gespeichert, Ordner frei zum Verschieben
        else:
            self.maybe_save()
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
        self.maybe_save()
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
        self.maybe_save()
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
        if not self.project_dir:
            return self.ensure_project()
        self._flush_edits()
        self.autosave_timer.stop()
        self.autosave(force=True)                      # auch direkt nach dem Laden (Beispielprojekt), sonst leer
        self.write_exchange()
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
            self.exchange_timer.start()
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
        if self.project_dir:
            self.close_project()
        self.publication_dir = str(pdir)
        self.add_recent_publication(pdir)
        self.pub_page.set_publication(pdir)
        self.update_title()
        return True

    def close_project(self):
        """Verbindung schließen (gespeichert wird automatisch) – zurück zur Publikation bzw. zum Startbildschirm."""
        self.maybe_save()
        self.project_dir = None
        self._load_state_into_ui({})
        self.watch_chemdraw()                          # nichts mehr überwachen
        self.update_title()

    def close_publication(self):
        self.publication_dir = None
        self.pub_page.set_publication(None)
        self.update_title()

    def _crumb_pub(self):
        if self.publication_dir:
            self.go_publication()
        else:
            self.move_compound()                       # „⚠ ohne Projekt“: einem Projekt zuordnen

    def _update_crumbs(self):
        if getattr(self, "btn_home", None) is None:
            return
        from elucida.app import demo as DEMO
        on = bool(self.publication_dir and self.project_dir)
        orphan = bool(self.project_dir and not self.publication_dir and not DEMO.is_demo(self.project_dir))
        self.crumb_seps[0].setVisible(on or orphan)
        self.btn_pub.setVisible(on or orphan)
        for w_ in (self.crumb_seps[1], self.btn_comp):
            w_.setVisible(on)
        if orphan:
            self.btn_pub.setText("⚠ " + T("nav_no_project"))
            self.btn_pub.setToolTip(T("assign_title"))
        if on:
            t_ = self.publication_title()
            self.btn_pub.setText(t_ if len(t_) <= 28 else t_[:26] + "…")
            self.btn_pub.setToolTip(T("act_to_publication") + ": " + t_)
            self.btn_comp.setText(self.export_name())

    def _fill_comp_menu(self):
        """Verbindungen des Projekts zum direkten Wechseln (die offene abgehakt)."""
        from elucida.app import publication as PUB
        self.comp_menu.clear()
        if not self.publication_dir:
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
            self.close_project()
        if self.publication_dir:
            self.close_publication()
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
        self.maybe_save()
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
        blocks = PSI.assemble(meta, comps, sections, setup, toc=toc, methods=methods)
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
        for key in ("overlay", "fluo", "cv", "sec", "epr", "irms", "hrms", "xray", "dft"):
            if self._built(key):                       # ungebaute zeichnen beim Bauen mit dem neuen Format
                getattr(self, self._tab_spec(key)[0]).render()
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

    def si_methods_items(self):
        """Methodentexte der Tabs, die fitten -> [(Kapitel der Gesamt-SI, Titel, Text)] (Text leer ohne Fit)."""
        self.collect_globals()
        items = [("uvvis", "UV-Vis absorption spectroscopy", self.eps_methods_text() if self.groups else "")]
        for key, title, t in (("cv", "Cyclic voltammetry", self.cv_tab),
                              ("sec", "UV-Vis spectroelectrochemistry", self.sec_tab),
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
            parts["uvvis"] = self.si_eps_figures(out_dir, title) + figs([self.ov_tab, self.fl_tab])
        for key, tab in (("epr", self.epr_tab), ("cv", self.cv_tab), ("sec", self.sec_tab)):
            if key in sections:
                parts[key] = figs([tab])
        if methods:
            for key, mtitle, txt in self.si_methods_items():
                if key in sections and txt:
                    parts["methods_" + key] = self._methods_paras(f"{mtitle} ({title})", txt)
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
        return title, parts

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
        self.table.setHorizontalHeaderLabels([T("col_lam"), T("col_n"), sym, T("col_intercept"),
                                              T("col_r2"), T("col_cut"), T("col_warn")])
        self.table.setRowCount(len(results))
        self._row_keys = []
        for i, r in enumerate(results):
            ft = r["fit"]
            lam = core.fmt_lam(r["lam"]) + (" (sh)" if r.get("shoulder") else "")
            cut = r.get("cutoff", cfg["max_abs_fit"])
            if ft:
                v, e = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg))
                b, be = core.fmt_ve(ft["intercept"], ft["se_intercept"])
                cells = [lam, str(ft["n"]), f"{v} ± {e}" if e else v,
                         f"{b} ± {be}" if be else b, f"{ft['r2']:.5f}", f"{cut:g}", "; ".join(r["warnings"])]
            else:
                cells = [lam, str(len(r["used"])), "–", "–", "–", f"{cut:g}",
                         r.get("no_fit") or T("no_fit", n=len(r["used"]), cut=cut, min=cfg["min_fit_points"])]
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
        from elucida.app import publication as PUB
        for p in files:
            if PRJ.is_project(p):
                self.open_project(p)
                return
            if PUB.is_publication(p):
                self.open_publication(p)
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
        self.maybe_save()
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
