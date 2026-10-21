"""
uvvis_gui.py - Grafische Oberfläche der UV-Vis-Auswertung (Windows / macOS / Linux).

Start:      python uvvis_gui.py
Selbsttest: python uvvis_gui.py --selftest AUSGABEORDNER [--selftest-isnet]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import traceback
from pathlib import Path

APP_NAME = "Spectravolt"
OLD_APP_NAMES = ("UVVisTool",)    # bis 1.15: Einstellungen beim ersten Start übernehmen
APP_VERSION = "1.17.0"
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
from PySide6.QtCore import QSettings, QSize, Qt, QThread, QTimer, Signal  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QIcon, QImage,  # noqa: E402
                           QGuiApplication, QKeySequence, QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox,  # noqa: E402
                               QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFontComboBox,
                               QFormLayout, QFrame, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea,
                               QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QTabWidget, QToolButton, QVBoxLayout, QWidget)

import uvvis_core as core  # noqa: E402
import uvvis_images as IMG  # noqa: E402
from uvvis_i18n import T, get_lang, set_lang  # noqa: E402
import uvvis_tabs  # noqa: E402
import uvvis_project as PRJ  # noqa: E402
import uvvis_report as REPORT  # noqa: E402
import uvvis_update as UPD  # noqa: E402
import uvvis_color as COLOR  # noqa: E402
import uvvis_cv as CVMOD  # noqa: E402
import uvvis_sec as SECMOD  # noqa: E402
import uvvis_epr as EPRMOD  # noqa: E402
import uvvis_style as STYLE  # noqa: E402
from uvvis_style import HINT_CSS, WARN_CSS, align_forms, compact, make_form  # noqa: E402

PREVIEW_DPI = 90
FIGSIZE = (8.0, 6.0)


def resource_path(rel):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
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
                "mark_sh": False, "min_r2": 0.98, "color_show": False, "color_d": 1.0}

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


class TextFormatDialog(QDialog):
    """Schriften, Labelstil und Rahmen – gilt für alle Tabs (Menü Format)."""

    def __init__(self, parent, tf):
        super().__init__(parent)
        self.setWindowTitle(T("tf_title"))
        tf = dict(core.TEXT_DEFAULTS, **(tf or {}))
        lay = QVBoxLayout(self)

        g = QGroupBox(T("tf_grp_fonts"))
        f = QFormLayout(g)
        self.cmb_font, self.cmb_sym = QFontComboBox(), QFontComboBox()
        self.cmb_font.setCurrentText(tf["font"])
        self.cmb_sym.setCurrentText(tf["symbol_font"])
        f.addRow(T("tf_font"), self.cmb_font)
        f.addRow(T("tf_symbol_font"), self.cmb_sym)
        self.cb_greek = QCheckBox(T("tf_greek"), checked=tf["greek"])
        self.cb_greek.toggled.connect(self.cmb_sym.setEnabled)
        self.cmb_sym.setEnabled(tf["greek"])
        f.addRow(self.cb_greek)
        lay.addWidget(g)

        g = QGroupBox(T("tf_grp_labels"))
        f = QFormLayout(g)
        self.sp_size = QDoubleSpinBox(decimals=1, minimum=0, maximum=40, singleStep=0.5, suffix=" pt")
        self.sp_size.setSpecialValueText(T("tf_auto"))
        self.sp_size.setValue(tf["label_pt"] or 0)
        f.addRow(T("tf_label_size"), self.sp_size)
        row = QHBoxLayout()
        self.cb_bold = QCheckBox(T("tf_bold"), checked=tf["bold"])
        self.cb_italic = QCheckBox(T("tf_italic"), checked=tf["italic"])
        row.addWidget(self.cb_bold)
        row.addWidget(self.cb_italic)
        row.addStretch(1)
        f.addRow("", row)
        self.color = tf["color"]
        self.btn_color = QPushButton()
        self.btn_color.clicked.connect(self.pick_color)
        self._show_color()
        f.addRow(T("tf_color"), self.btn_color)
        lay.addWidget(g)

        g = QGroupBox(T("tf_grp_frames"))
        v = QVBoxLayout(g)
        self.cb_axes = QCheckBox(T("tf_axes_frame"), checked=tf["axes_frame"])
        self.cb_struct = QCheckBox(T("tf_struct_frame"), checked=tf["struct_frame"])
        v.addWidget(self.cb_axes)
        v.addWidget(self.cb_struct)
        lay.addWidget(g)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        lay.addWidget(bb)

    def _show_color(self):
        self.btn_color.setText(self.color)
        self.btn_color.setStyleSheet(f"QPushButton {{ color: {self.color}; font-weight: bold; }}")

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, T("tf_color"))
        if c.isValid():
            self.color = c.name()
            self._show_color()

    def restore_defaults(self):
        d = core.TEXT_DEFAULTS
        self.cmb_font.setCurrentText(d["font"])
        self.cmb_sym.setCurrentText(d["symbol_font"])
        self.cb_greek.setChecked(d["greek"])
        self.sp_size.setValue(d["label_pt"])
        self.cb_bold.setChecked(d["bold"])
        self.cb_italic.setChecked(d["italic"])
        self.color = d["color"]
        self._show_color()
        self.cb_axes.setChecked(d["axes_frame"])
        self.cb_struct.setChecked(d["struct_frame"])

    def result_format(self):
        return {"font": self.cmb_font.currentFont().family(), "symbol_font": self.cmb_sym.currentFont().family(),
                "greek": self.cb_greek.isChecked(), "label_pt": self.sp_size.value(),
                "bold": self.cb_bold.isChecked(), "italic": self.cb_italic.isChecked(), "color": self.color,
                "axes_frame": self.cb_axes.isChecked(), "struct_frame": self.cb_struct.isChecked()}


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
        self.text_fmt = dict(core.TEXT_DEFAULTS)
        self._tab_index = 0
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
        m.addAction(QAction(T("act_show_folder"), self, triggered=self.show_project_folder))
        m.addSeparator()
        m.addAction(QAction(T("act_open"), self, shortcut=QKeySequence("Ctrl+Shift+O"), triggered=self.choose_csv))
        m.addAction(QAction(T("act_conc"), self, triggered=self.edit_concentrations))
        m.addAction(QAction(T("act_restart"), self, triggered=self.restart_file))
        act_export = QAction(STYLE.icon("export"), T("act_export"), self, shortcut="Ctrl+E",
                             triggered=self.export_current)
        m.addAction(act_export)
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
        for act in (act_new, act_open_prj, act_save, None, self.act_undo, self.act_redo):
            if act is None:
                self.toolbar.addSeparator()
                continue
            keys = act.shortcut().toString(QKeySequence.NativeText)
            act.setToolTip(f"{act.text().rstrip('…')} ({keys})" if keys else act.text())
            self.toolbar.addAction(act)
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
        self.sp_cut = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=5, singleStep=0.1)
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
        self.cb_inset = QCheckBox(T("inset_show"))
        self.cb_tab = QCheckBox(T("inset_table"))
        self.cb_excl = QCheckBox(T("show_excl"))
        for cb in (self.cb_err, self.cb_marksh, self.cb_inset, self.cb_tab, self.cb_excl):
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
        b = QPushButton(STYLE.icon("reset"), T("btn_reset_layout"))
        b.clicked.connect(self.reset_layout)
        row.addWidget(b)
        row.addStretch(1)
        self.btn_export = QPushButton(STYLE.icon("export", "#FFFFFF"), T("btn_export"))
        self.btn_export.setProperty("accent", True)
        self.btn_export.clicked.connect(self.export_dialog)
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
        self.canvas_host = uvvis_tabs.CanvasHost(self.canvas, self.fig)
        self.tabs = QTabWidget()
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([T("col_lam"), T("col_n"), T("col_coeff"),
                                              T("col_intercept"), T("col_r2"), T("col_cut"), T("col_warn")])
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
        self.tabs.addTab(self.table, T("tab_results"))
        self.tabs.addTab(self.log, T("tab_log"))
        # Leer-Zustand statt weißer Fläche, solange keine Messdaten geladen sind
        empty = QFrame(objectName="emptyDrop")
        empty.setStyleSheet("#emptyDrop { border: 1px dashed palette(mid); border-radius: 8px; }")
        ev = QVBoxLayout(empty)
        ev.addStretch(1)
        for text, css in ((T("empty_title"), "font-size: 15px; font-weight: bold;"),
                          (T("empty_formats"), HINT_CSS)):
            lb = QLabel(text, alignment=Qt.AlignCenter, wordWrap=True)
            lb.setStyleSheet(css)
            ev.addWidget(lb)
        b = QPushButton(STYLE.icon("open", "#FFFFFF"), T("act_open"))
        b.setProperty("accent", True)
        b.clicked.connect(self.choose_csv)
        ev.addWidget(b, 0, Qt.AlignCenter)
        ev.addStretch(1)
        empty_wrap = QWidget()
        QVBoxLayout(empty_wrap).addWidget(empty)
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(empty_wrap)
        self.preview_stack.addWidget(self.canvas_host)
        self.preview_stack.setCurrentIndex(1 if self.current and self.current in self.groups else 0)
        right = QSplitter(Qt.Vertical)
        right.addWidget(self.preview_stack)
        right.addWidget(self.tabs)
        right.setSizes([650, 220])
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left_col)
        split.addWidget(right)
        split.setSizes([left_col.minimumWidth(), 920])
        self.main_tabs = QTabWidget()
        self.main_tabs.addTab(split, T("tab_eps"))
        self.ov_tab = uvvis_tabs.OverlayTab(self, self.ov_state)
        self.fl_tab = uvvis_tabs.FluoTab(self, self.fl_state)
        self.main_tabs.addTab(self.ov_tab, T("tab_overlay"))
        self.main_tabs.addTab(self.fl_tab, T("tab_fluo"))
        self.cv_tab = CVMOD.CVTab(self, self.cv_state)
        self.main_tabs.addTab(self.cv_tab, T("tab_cv"))
        self.sec_tab = SECMOD.SECTab(self, self.sec_state)
        self.main_tabs.addTab(self.sec_tab, T("tab_sec"))
        self.epr_tab = EPRMOD.EPRTab(self, self.epr_state)
        self.main_tabs.addTab(self.epr_tab, T("tab_epr"))
        self.main_tabs.setCurrentIndex(self._tab_index)
        self.main_tabs.currentChanged.connect(lambda i: setattr(self, "_tab_index", i))
        self.setCentralWidget(self.main_tabs)

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
                  self.cb_marksh):
            w.toggled.connect(self.changed)
        for w in (self.sp_min, self.sp_r2):
            w.valueChanged.connect(self._update_sections)
        self.cmb_r2.currentIndexChanged.connect(self._update_sections)
        for w in (self.cb_shoulders, self.cb_err, self.cb_marksh, self.cb_inset, self.cb_tab, self.cb_excl,
                  self.cb_pdf, self.cb_svg, self.cb_png):
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
                (self.cb_err, "show_err"), (self.cb_marksh, "mark_sh"), (self.cb_inset, "inset"),
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
                         mark_sh=self.cb_marksh.isChecked(),
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
        self.lbl_chem.setStyleSheet(WARN_CSS if warn else "")
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
        self.build_ui()
        self.render()

    def _append_log(self, msg):
        self.log.appendPlainText(msg)

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
            paths = sorted(self.import_file(p, "data") for p in paths)   # Kopie ins Projekt
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
                "tab": self._tab_index,
                "text": dict(self.text_fmt)}

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
        self.text_fmt = dict(core.TEXT_DEFAULTS, **(state.get("text") or {}))
        self._tab_index = state.get("tab", 0) or 0
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

    def update_title(self):
        name = Path(self.project_dir).name if self.project_dir else T("no_project_title")
        self.setWindowTitle(f"{name} – {T('app_title')} {APP_VERSION}")

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
        return True

    def autosave(self):
        if not self.project_dir or self._restoring:
            return
        try:
            PRJ.write(self.project_dir, self.get_state())
            self._saved_snap = self._undo[-1] if self._undo else None
            self.statusBar().showMessage(T("autosaved"), 2000)
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
            path = self.import_file(path, "images")
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
                    import uvvis_chem
                    chem = uvvis_chem.load_cdxml(sib)
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
            path = self.import_file(path, "images")
        if path is None:
            st.update(photo=None, photo_asset=None)
            self.apply_series_widgets()
            return self.render()
        method = st["bg"]
        if method in ("auto", "isnet") and not self.ensure_model():
            method = "grabcut" if method == "isnet" else "auto"
        cache = Path(self.csv_path).parent / ".uvvis_cache" if self.csv_path else None

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
        core.apply_text_format(cfg, self.text_fmt)
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

    def edit_text_format(self):
        dlg = TextFormatDialog(self, self.text_fmt)
        if dlg.exec() != QDialog.Accepted:
            return
        self.text_fmt = dlg.result_format()
        for key in ("font", "symbol_font"):
            name = self.text_fmt[key]
            if core.first_font([name], None) is None:
                self.log_signal.emit("  " + T("tf_missing", name=name))
        self.render()
        self.ov_tab.render()
        self.fl_tab.render()
        self.cv_tab.render()
        self.sec_tab.render()
        self.epr_tab.render()
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
            self.hover = uvvis_tabs.HoverReadout(self.F, curves, self.show_hover, self.hover_text, self.pick_band)
            self.sync_image_sizes(self.F.current_layout())
            self.canvas.draw_idle()
            self.fill_table(results, cfg2)
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
        out = self.export_all()
        folders = sorted({str(p.parent) for p in out})
        self.info(T("exported_to", p="\n".join(folders)))

    def export_all(self, folder: Path = None):
        """Alle Serien exportieren: Abbildungen, Ergebnis-CSV und Excel-Report.
        Ohne Ordnerangabe nach <Projekt>/exports/epsilon/<Serie>/ (wird überschrieben)."""
        self.collect_globals()
        stem = Path(self.csv_path).stem
        written = []
        for g in self.groups:
            if folder is None:
                gdir = PRJ.export_dir(self.project_dir, "epsilon", core.safe_name(g))
                name = core.safe_name(g)
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
            try:
                rep = REPORT.write_report(folder_g / f"{name}_report.xlsx", cfg2, self.groups[g], spectra,
                                          results, g, files=self.csv_paths, version=APP_VERSION)
                written.append(Path(rep))
            except PermissionError:
                self.error(T("report_locked", p=folder_g / f"{name}_report.xlsx"))
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
        i = self.main_tabs.currentIndex()
        if i == 1:
            return self.ov_tab.export_dialog()
        if i == 2:
            return self.fl_tab.export_dialog()
        if i == 3:
            return self.cv_tab.export_dialog()
        if i == 4:
            return self.sec_tab.export_dialog()
        if i == 5:
            return self.epr_tab.export_dialog()
        return self.export_dialog()

    def info(self, msg):
        self.log_signal.emit(msg)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.information(self, T("app_title"), msg)

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

    def closeEvent(self, ev):
        if not self.maybe_save():
            ev.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(ev)


# ----------------------------------------------------------------------------
# Selbsttest (für CI und nach der Installation)
# ----------------------------------------------------------------------------
def make_selftest_inputs(d: Path):
    """Synthetische Cary-CSV (2 Serien), CDXML und Küvettenfoto (HEIC, falls möglich)."""
    from PIL import Image, ImageDraw
    d.mkdir(parents=True, exist_ok=True)
    wl = np.arange(1100.0, 199.0, -1.0)
    bands = {"TEST-A": [(262, 6.8, 20), (484, 1.6, 30), (732, 0.25, 40), (816, 0.24, 40)],
             "TEST-B": [(255, 7.3, 18), (351, 2.7, 20), (444, 3.5, 12), (719, 0.42, 35), (804, 0.41, 35)]}
    concs = [("1", 1.0), ("0p5", 0.5), ("0p25", 0.25), ("0p125", 0.125), ("0p0625", 0.0625)]
    rng = np.random.default_rng(0)
    cols, names = [], []
    for ser, bl in bands.items():
        a = sum(h * np.exp(-0.5 * ((wl - l) / w) ** 2) for l, h, w in bl)
        for tag, c in concs:
            names.append(f"{ser}-{tag}mgml_THF")
            y = np.minimum(a * c, 4.0) - 0.03 + rng.normal(0, 0.002, wl.size)
            cols.append(y)
    lines = ["".join(f"{n},," for n in names), "".join("Wavelength (nm),Abs," for _ in names)]
    for i, x in enumerate(wl):
        lines.append("".join(f"{x:.6f},{y[i]:.8f}," for y in cols))
    lines += ["", "TEST-A-1mgml_THF", "Instrument  Cary 60"]
    (d / "selftest.csv").write_text("\r\n".join(lines), encoding="utf-8", newline="")
    nodes = [(1, 100, 100, 6), (2, 112.5, 92.8, 6), (3, 125, 100, 6), (4, 125, 114.4, 6),
             (5, 112.5, 121.6, 6), (6, 100, 114.4, 7), (7, 112.5, 78.4, 8)]
    bonds = [(1, 2, 2), (2, 3, 1), (3, 4, 2), (4, 5, 1), (5, 6, 2), (6, 1, 1), (2, 7, 1)]
    xml = ['<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40"><page id="1"><fragment id="99">']
    xml += [f'<n id="{i}" p="{x} {y}"' + (f' Element="{e}"' if e != 6 else "") + "/>" for i, x, y, e in nodes]
    xml += [f'<b id="{20 + k}" B="{b}" E="{e}"' + (' Order="2"' if o == 2 else "") + "/>"
            for k, (b, e, o) in enumerate(bonds)]
    xml += ["</fragment></page></CDXML>"]
    (d / "pyridinol.cdxml").write_text("".join(xml), encoding="utf-8")
    im = Image.new("RGB", (600, 900), (190, 185, 175))
    dr = ImageDraw.Draw(im)
    dr.rectangle([240, 100, 360, 200], fill=(25, 25, 25))
    dr.rectangle([220, 200, 380, 820], fill=(215, 220, 228))
    dr.rectangle([235, 420, 365, 805], fill=(195, 90, 35))
    photo = d / "kuevette.png"
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        im.save(d / "kuevette.heic", quality=90)
        photo = d / "kuevette.heic"
    except Exception:
        im.save(photo)
    return d / "selftest.csv", d / "pyridinol.cdxml", photo


def selftest(outdir, with_isnet=False):
    global SETTINGS_FILE
    out = Path(outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE = out / "selftest_settings.ini"     # zuletzt geöffnet, Sprache usw. nicht beim Nutzer ändern
    SETTINGS_FILE.unlink(missing_ok=True)
    report = [f"{APP_NAME} {APP_VERSION} selftest", f"python {sys.version.split()[0]}, {sys.platform}"]
    ok = True
    app = QApplication.instance() or QApplication(sys.argv[:1])  # noqa: F841
    try:
        csv, cdxml, photo = make_selftest_inputs(out / "input")
        report.append(f"photo format: {photo.suffix}")
        w = MainWindow()
        w._allow_download = with_isnet
        proj = out / "projekt_test"
        assert not w.open_csv(csv), "ohne Projekt darf nichts geladen werden"
        assert w.create_project(proj)
        QApplication.processEvents()
        w.open_csv(csv)
        assert set(w.groups) == {"TEST-A", "TEST-B"}, w.groups
        assert Path(w.csv_path).parent == proj / "data", w.csv_path          # ins Projekt kopiert
        w.set_structure(str(cdxml), "TEST-A", render=False, sync=True)
        st = w.series["TEST-A"]
        report.append(f"CDXML: {st['chem_info']!r}")
        assert st["mw"] and abs(st["mw"] - 95.10) < 0.05, st["mw"]      # 3-Hydroxypyridin C5H5NO
        w.series["TEST-A"]["bg"] = "isnet" if with_isnet else "grabcut"
        w.set_photo(str(photo), "TEST-A", render=False, sync=True)
        bgm = st["photo_asset"]["bg_method"]
        report.append(f"background: {bgm}")
        if with_isnet:
            assert bgm == "isnet", bgm
        w.render()
        files = w.export_all(out)
        for f in files:
            assert f.exists() and f.stat().st_size > 200, f
        import pymupdf
        page = pymupdf.open(str(out / "selftest_TEST-A.pdf"))[0]
        report.append(f"pdf: {len(page.get_drawings())} vector paths, {len(page.get_images())} images")
        assert page.get_images(), "photo missing in PDF"
        svg = (out / "selftest_TEST-A.svg").read_text(encoding="utf-8")
        assert "structure_0" in svg and "<image" in svg, "SVG ohne Struktur/Foto"
        report.append(f"pdf size: {page.rect.width / 72 * 2.54:.2f} x {page.rect.height / 72 * 2.54:.2f} cm")
        # Probennamen ohne Konzentration (z. B. c0..c4) -> Overrides wie aus dem Dialog
        txt = csv.read_text(encoding="utf-8").splitlines()
        n_samples = len([n for n in txt[0].split(",") if n])
        txt[0] = "".join(f"c{i},," for i in range(n_samples))
        plain = out / "input" / "unnamed.csv"
        plain.write_text("\r\n".join(txt), encoding="utf-8", newline="")
        assert w.open_csv(plain, ask=False) is False                 # ohne Angaben: nichts
        w.conc = {f"c{i}": {"conc": 1.0 / 2 ** i, "unit": "mg/mL", "series": "unbenannt"}
                  for i in range(5)}
        assert w.rebuild_groups() and "unbenannt" in w.groups, w.groups
        assert len(w.groups["unbenannt"]) == 5
        w.render()
        report.append("unnamed samples: OK")
        # Einzelmessungen in getrennten Dateien + Cary-Binärdatei (.DSW)
        import struct
        singles = []
        for i, s_ in enumerate(core.read_samples([csv])[:5]):
            f = out / "input" / f"single_{i}.csv"
            f.write_text("\r\n".join([f"{s_['name']},,", "Wavelength (nm),Abs,"] +
                                      [f"{a:.4f},{b:.6f}," for a, b in zip(s_["x"], s_["y"])]),
                         encoding="utf-8", newline="")
            singles.append(f)
        assert w.open_files(singles, ask=False) and len(w.groups["TEST-A"]) == 5, w.groups
        magic = b"Varian UV-VIS Spectrophotometer"
        blob = bytearray([len(magic)]) + magic
        blob += bytes(0x400 - len(blob))
        for k in range(3):
            blk = bytearray(256)
            t = f"DSW-T-{0.5 / 2 ** k:g}".replace(".", "p").encode() + b"mgml"
            blk[:len(t)] = t
            blob += blk
            for x in np.arange(800.0, 249.0, -1.0):
                blob += struct.pack("<ff", x, 0.4 / 2 ** k * np.exp(-((x - 450) / 40) ** 2))
            blob += bytes(64)
        dsw = out / "input" / "test.DSW"
        dsw.write_bytes(bytes(blob))
        assert w.open_files([dsw], ask=False) and len(w.groups.get("DSW-T", [])) == 3, w.groups
        report.append("multiple files + DSW: OK")
        # Overlay (Messung + TD-DFT) und Fluoreszenz
        orca = out / "input" / "orca.out"
        orca.write_text("\n".join([
            "-" * 77, "         ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS", "-" * 77,
            "State   Energy    Wavelength  fosc         T2        TX        TY        TZ",
            "        (cm-1)      (nm)                 (au**2)    (au)      (au)      (au)", "-" * 77,
            "   1   20660.0    484.0   0.150000000   1.00000   1.00000   0.00000   0.00000",
            "   2   38168.0    262.0   0.600000000   3.00000   1.70000   0.00000   0.00000", ""]),
            encoding="utf-8")
        assert len(__import__("uvvis_extra").parse_tddft(orca)["E"]) == 2
        w.ov_state["entries"] = [
            {"kind": "exp", "file": str(csv), "sample": "TEST-A-0p25mgml_THF", "label": "exp", "color": "#000000",
             "visible": True, "own_norm": False, "nlo": 450, "nhi": 520, "conc": 0.25, "unit": "mg/mL",
             "mw": 95.1, "d": 1.0},
            {"kind": "calc", "file": str(orca), "label": "calc", "color": "#1764e8", "visible": True,
             "own_norm": False, "nlo": 450, "nhi": 520, "fwhm": 0.3, "shift": 0.0}]
        w.ov_state.update(nlo=450, nhi=520)
        for mode in ("norm", "eps"):
            w.ov_state["mode"] = mode
            files = w.ov_tab.export_to(out / f"overlay_{mode}")
            assert all(f.exists() for f in files), files
        em = out / "input" / "emission.csv"
        xs = np.arange(400.0, 701.0, 1.0)
        em.write_text("\r\n".join(["EM ex352,,", "Wavelength (nm),Intensity (a.u.),"] +
                                    [f"{x:.1f},{500 * np.exp(-((x - 520) / 30) ** 2):.3f}," for x in xs]),
                      encoding="utf-8", newline="")
        w.fl_state.update(abs_file=str(csv), abs_sample="TEST-A-0p25mgml_THF", em_file=str(em),
                          em_sample="EM ex352", ex=352.0, alo=450, ahi=520, eps="1234",
                          photo_day=str(photo), bg_day="grabcut", photo_uv=str(photo), bg_uv="none")
        files = w.fl_tab.export_to(out / "fluorescence")
        assert all(f.exists() for f in files), files
        # Cary-Eclipse-CSV (Name in Zeile 2, λex aus den Metadaten)
        ecl = out / "input" / "eclipse.csv"
        ecl.write_text("\r\n".join(["Wavelength (nm),Intensity (a.u.),Z Axis,", ",PROBE-1-45p3µM", ",1"] +
                                     [f"{x:g},{300 * np.exp(-((x - 480) / 25) ** 2):.4f}" for x in xs] +
                                     ["", "PROBE-1-45p3µM", "Ex. Wavelength (nm)               387.00"]),
                       encoding="utf-8", newline="")
        es = core.read_samples([ecl])
        assert len(es) == 1 and es[0]["name"] == "PROBE-1-45p3µM" and es[0]["ex"] == 387.0, es[0]["name"]
        report.append("overlay + fluorescence + Eclipse CSV: OK")

        # Fluoreszenz: Stokes-Verschiebung, A(λex), λabs-Label
        w.fl_state.update(stokes_label=True)
        files = w.fl_tab.export_to(out / "fluorescence_stokes")
        assert all(f.exists() for f in files), files
        inf = w.fl_tab.info
        exp_cm = 1e7 / inf["lam_abs"] - 1e7 / inf["lam_em"]
        assert inf["lam_em"] == 520 and abs(inf["stokes_cm"] - exp_cm) < 1e-6 and inf["stokes_cm"] > 0, inf
        assert inf["a_ex"] is not None and np.isfinite(inf["a_ex"]), inf
        assert uvvis_tabs.fmt_stokes(1473.4) == "1470"
        figf = MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI)
        FigureCanvasAgg(figf)
        ltxt = " ".join(a.get_text() for a in w.fl_tab.build(figf).ann_items.values())
        assert "abs" in ltxt and "\\tilde" in ltxt, ltxt
        w.fl_state.update(stokes_label=False)
        report.append("fluorescence Stokes shift + A(ex): OK")
        # Schultern, Zusatzbande, Cutoff und Ausblenden pro Bande
        w.open_csv(csv, ask=False)
        w.glob.update(shoulders=True, bands_add=True, bands="600")
        w.series["TEST-A"]["band_cutoff"] = {"484": 2.0}
        w.series["TEST-A"]["band_hidden"] = [600]
        cfg_t = w.make_cfg("TEST-A")
        _, _, res_t = core.prepare_series(cfg_t, w.groups["TEST-A"], "TEST-A")
        lams = {int(round(r["lam_requested"])): r for r in res_t}
        assert 600 in lams and lams[600].get("hidden") and lams[484]["cutoff"] == 2.0, sorted(lams)
        report.append("bands/shoulders/cutoff: OK")
        # einstellbare R²-Schwelle: 1.0 blendet alles aus, 0 zeigt alles mit Fit
        w.series["TEST-A"]["band_hidden"] = []
        for thr, expect_hidden in ((1.0, True), (0.0, False)):
            w.glob["min_r2"] = thr
            w.apply_globals()
            assert abs(w.sp_r2.value() - thr) < 1e-9
            w.collect_globals()
            _, _, res_r = core.prepare_series(w.make_cfg("TEST-A"), w.groups["TEST-A"], "TEST-A")
            fitted = [r for r in res_r if r["fit"]]
            assert fitted and all(bool(r.get("hidden")) == expect_hidden for r in fitted), (thr, res_r)
        w.glob["min_r2"] = 0.98
        w.apply_globals()
        report.append("min. R² threshold: OK")

        def pump(sec=0.4):
            import time
            t0 = time.time()
            while time.time() - t0 < sec:
                QApplication.processEvents()
                time.sleep(0.02)

        # TD-DFT mit Spin-Bahn-Kopplung (ORCA 6): Zustandsnamen wie "0-1.0A" dürfen nicht als Zahl gelten
        soc = out / "input" / "orca_soc.out"
        hdr = ["-" * 104, "      SOC CORRECTED ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS", "-" * 104,
               "      Transition         Energy     Energy  Wavelength fosc(D2)      D2       |DX|      |DY|      |DZ|",
               "                          (eV)      (cm-1)    (nm)                 (au**2)    (au)      (au)      (au)",
               "-" * 104,
               "  0-1.0A  ->  1-3.0A    2.898266   23376.1   427.8   0.000000000   0.00000   0.00001   0.00000   0.00000",
               "  0-1.0A  -> 10-1.0A    4.004892   32301.6   309.6   0.120701528   1.23017   0.69013   0.85513   0.15048",
               ""]
        soc.write_text("\n".join(orca.read_text(encoding="utf-8").splitlines() + hdr), encoding="utf-8")
        import uvvis_extra as XX
        r_soc = XX.parse_tddft(soc)
        assert r_soc["variant"] == "soc" and abs(r_soc["E"][1] - 4.004892) < 1e-6 and abs(r_soc["f"][1] - 0.1207) < 1e-3, r_soc
        assert XX.parse_tddft(soc, "nosoc")["variant"] == "nosoc"
        report.append("TD-DFT SOC: OK")

        # Zuschnitt von Strukturen: senkrechte/waagerechte Endbindungen dürfen nicht abgeschnitten werden
        import pymupdf
        tdoc = pymupdf.open()
        pg = tdoc.new_page(width=200, height=200)
        pg.draw_line((50, 50), (150, 50), width=1)        # waagerecht
        pg.draw_line((100, 50), (100, 160), width=1)      # senkrecht, reicht am weitesten nach unten
        cr = IMG._content_rect(pg)
        assert cr.y1 >= 160 and cr.x0 <= 50 and cr.x1 >= 150, cr
        report.append("structure trimming: OK")

        # Einfärben von Strukturen (Overlay: Struktur pro Spektrum in Kurvenfarbe)
        ca = IMG.load_structure(cdxml, color="#e8231b")
        opaque = ca["rgba"][..., 3] > 200
        assert ca["pdf"] and abs(int(np.median(ca["rgba"][opaque][:, 0])) - 232) < 3, "Einfärben"
        report.append("structure colour: OK")

        # Neu platzierte Labels dürfen nicht auf gespeicherten landen (zwei Banden, eine gespeichert)
        cfg_l = w.make_cfg("TEST-A")
        cfg_l2, sp_l, res_l = core.prepare_series(cfg_l, w.groups["TEST-A"], "TEST-A")
        figl = MplFigure(figsize=cfg_l2["figsize_in"], dpi=PREVIEW_DPI)
        FigureCanvasAgg(figl)
        auto = core.build_figure(plt, cfg_l2, sp_l, res_l, {}, fig=figl).current_layout()
        lk = [k for k in auto if k.startswith("label_")]
        assert len(lk) >= 2, lk
        Fl = core.build_figure(plt, cfg_l2, sp_l, res_l, {lk[-1]: auto[lk[0]]}, fig=figl)
        rl = Fl._renderer()
        b0, b1 = (Fl.ann_items[k].get_window_extent(rl) for k in (lk[0], lk[-1]))
        assert not b0.overlaps(b1), "Label-Kollision"
        report.append("label collision: OK")

        # Overlay-Optionen: Skalierung, Versatz, Linienart, Strich-Modi
        w.ov_state["entries"][1].update(scale=0.8, offset=0.2, ls="dotted", lw=2.0)
        for mode in ("max", "band", "faxis"):
            w.ov_state.update(mode="norm", stick_mode=mode, sticks=True)
            files = w.ov_tab.export_to(out / f"overlay_sticks_{mode}")
            assert all(f.exists() for f in files), files
        report.append("overlay options: OK")

        # Overlay gestapelt: Ebenen in Listenreihenfolge, TD-DFT auf der Ebene der Messung, y ohne Zahlen
        ents = w.ov_state["entries"]
        ents.append(dict(ents[0], uid="stack3", label="exp 2", color="#e8231b"))
        ents[1]["stack_with_prev"] = True

        def ov_fig():
            figo = MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI)
            FigureCanvasAgg(figo)
            Fo = w.ov_tab.build(figo)
            figo.canvas.draw()
            return Fo
        w.ov_state.update(mode="norm", stick_mode="faxis", stack=False, curve_labels=False, zero_lines=False)
        flat = ov_fig()
        w.ov_state.update(stack=True, stack_gap=1.2, y_axis="auto", curve_labels=True, zero_lines=True)
        stk = ov_fig()
        for i, dy in enumerate((1.2, 1.2, 0.0)):
            d = np.nanmedian(stk.curves[i]["y"] - flat.curves[i]["y"])
            assert abs(d - dy) < 1e-9, (i, d)
        assert stk.ax2 is None and not stk.ax.yaxis.get_major_ticks()[0].label1.get_visible()
        assert len(stk.curve_texts) == 2 and stk.legend is None, len(stk.curve_texts)
        files = w.ov_tab.export_to(out / "overlay_stacked")
        assert all(f.exists() for f in files), files
        ents.pop()
        ents[1].pop("stack_with_prev")
        w.ov_state.update(stack=False, curve_labels=False, zero_lines=False, y_axis="auto")
        report.append("overlay stacked: OK")

        # TD-DFT: Triplett-Zustände (ORCA 6 Bezeichnung, ORCA 4/5 eigener Block, Gaussian) und Kombinieren
        import uvvis_extra as XT
        sep = "-" * 100
        tab_head = [sep, "      ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS", sep,
                    "   Transition    Energy   Energy  Wavelength fosc(D2)   D2   DX   DY   DZ",
                    "                  (eV)    (cm-1)    (nm)", sep]
        o6 = out / "input" / "orca6_trip.out"
        o6.write_text("\n".join(tab_head + [
            "  0-1A  ->  1-3A    2.500000   20164.1   495.9   0.000000000   0.00000   0.00000   0.00000   0.00000",
            "  0-1A  ->  1-1A    3.000000   24196.9   413.3   0.200000000   1.00000   1.00000   0.00000   0.00000",
            ""]), encoding="utf-8")
        o5 = out / "input" / "orca5_trip.out"
        o5.write_text("\n".join([
            "TD-DFT/TDA EXCITED STATES (TRIPLETS)", "------------------------------------", "",
            "STATE  1:  E=   0.091874 au      2.600 eV    20970.5 cm**-1 <S**2> =   2.000000", "",
            "STATE  2:  E=   0.110000 au      2.993 eV    24142.0 cm**-1 <S**2> =   2.000000", ""]
            + tab_head + ["   1   26617.0    375.7   0.300000000   1.00000   1.00000   0.00000   0.00000", ""]),
            encoding="utf-8")
        gx = out / "input" / "gauss_trip.log"
        gx.write_text("\n".join([
            " Excited State   1:     Triplet-A      2.7000 eV  459.20 nm  f=0.0000  <S**2>=2.000",
            " Excited State   2:     Singlet-A      3.2000 eV  387.45 nm  f=0.1500  <S**2>=0.000", ""]),
            encoding="utf-8")
        for pth, n_t, e_t in ((o6, 1, 2.5), (o5, 2, 2.6), (gx, 1, 2.7)):
            rt = XT.parse_tddft(pth)
            trips = [E for E, m in zip(rt["E"], rt["mult"]) if m == 3]
            assert len(trips) == n_t and abs(min(trips) - e_t) < 1e-6, (pth.name, rt)
            assert all(fv == 0 for fv, m in zip(rt["f"], rt["mult"]) if m == 3), pth.name
        n_before = len(ents)
        ents += [{"kind": "calc", "file": str(p_), "label": p_.stem, "color": "#1f9e4a", "visible": True,
                  "own_norm": False, "nlo": 450, "nhi": 520, "fwhm": 0.3, "shift": 0.0} for p_ in (o6, gx)]
        w.ov_tab.fill_table()
        for r_ in range(n_before):                      # nur die beiden neuen markieren
            ents[r_]["visible"] = r_ == 0
        w.ov_tab.table.clearSelection()
        w.ov_tab.table.setSelectionMode(QAbstractItemView.MultiSelection)
        for r_ in (n_before, n_before + 1):
            w.ov_tab.table.selectRow(r_)
        w.ov_tab.combine_selected()
        comb = ents[-1]
        assert len(comb["sources"]) == 2 and not ents[n_before]["visible"], comb
        E_c, f_c, m_c = w.ov_tab.calc_data(comb)
        assert len(E_c) == 4 and m_c.count(3) == 2 and abs(f_c.sum() - 0.35) < 1e-9, (E_c, f_c, m_c)
        comb["sources"][1]["weight"] = 0.5
        assert abs(w.ov_tab.calc_data(comb)[1].sum() - 0.275) < 1e-9
        w.ov_state.update(mode="norm", triplets=True, sticks=True, stick_mode="band")
        _, _, _, stx = w.ov_tab.figure_spec()
        dashed = np.concatenate([s_["x"] for s_ in stx if s_.get("ls") == "dashed"])
        assert np.allclose(sorted(dashed), sorted(1e7 / (np.array([2.5, 2.7]) * XT.EV_TO_CM))), dashed
        files = w.ov_tab.export_to(out / "overlay_triplets")
        assert all(f.exists() for f in files), files
        assert any(c_ is comb["sources"][0] for c_, _, _ in PRJ._path_slots({"overlay": w.ov_state})), \
            "kombinierte Quellen fehlen im Projekt"
        del ents[n_before:]
        ents[1]["visible"] = True
        w.ov_state.update(triplets=False)
        w.ov_tab.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        w.ov_tab.fill_table()
        report.append("TD-DFT triplets + combine: OK")

        # Export ins Projekt inkl. Excel-Report
        w.open_csv(csv, ask=False)
        w.series["TEST-A"]["mw"] = 95.1
        w.set_structure(str(cdxml), "TEST-A", render=False, sync=True, autofill_mw=False)
        w.render()
        pump()
        files = w.export_all()
        rep = proj / "exports" / "epsilon" / "TEST-A" / "TEST-A_report.xlsx"
        assert rep in files and rep.exists(), files
        from openpyxl import load_workbook
        wbk = load_workbook(rep)
        assert len(wbk.sheetnames) >= 3 and any("nm" in n for n in wbk.sheetnames), wbk.sheetnames
        report.append("export into project + Excel report: OK")

        # Textformat: λ/ε in Symbolschrift, Labels fett/farbig, Rahmen um Plot und Struktur
        w.text_fmt = dict(core.TEXT_DEFAULTS, bold=True, color="#1764e8", label_pt=12.0,
                          axes_frame=True, struct_frame=True)
        w.render()
        assert w.F.ax.spines["top"].get_visible(), "Rahmen oben fehlt"
        ann = next(a for k, a in w.F.ann_items.items() if k.startswith("label_"))
        assert "\\mathsf{λ}" in ann.get_text() and ann.get_fontweight() == "bold" and ann.get_fontsize() == 12.0
        sa = w.F.axes_items["image_struktur"]
        assert sa._frame is not None
        rf = w.F._renderer()
        fb, ib = sa._frame.get_window_extent(rf), sa.get_window_extent(rf)
        assert fb.x0 < ib.x0 and fb.y1 > ib.y1, "Rahmen liegt nicht außen um die Struktur"
        for k, b in [(k, a.get_window_extent(rf)) for k, a in w.F.ann_items.items()]:
            assert not fb.overlaps(b), f"Strukturrahmen überdeckt {k}"
        files = w.export_all(out / "textformat")
        pdf = next(f for f in files if f.suffix == ".pdf")
        fonts = " ".join(f[3] for f in pymupdf.open(str(pdf))[0].get_fonts())
        sym_font = core.first_font(core.DEFAULTS["symbol_font"], "DejaVu Serif").replace(" ", "")
        assert sym_font.lower() in fonts.lower().replace("-", ""), fonts
        svg = next(f for f in files if f.suffix == ".svg").read_text(encoding="utf-8")
        assert "structure_0" in svg, "SVG ohne Struktur"
        w.fl_tab.export_to(out / "textformat_fluo")
        w.text_fmt = dict(core.TEXT_DEFAULTS)
        w.render()
        report.append("text format + frames: OK")

        # Hover: Maus über einem Messpunkt -> λ und A in der Statusleiste; Doppelklick -> Bande
        from matplotlib.backend_bases import MouseEvent
        w.glob["bands"] = ""
        w.apply_globals()
        w.render()
        w.canvas.draw()
        hv, ax = w.hover, w.F.ax
        def peak(c):                                   # Bande bei 484 nm, nur Kurven mit Peak im Bild
            xs = np.asarray(c["x"])
            i = int(np.nanargmax(np.where((xs > 400) & (xs < 560), c["y"], -np.inf)))
            return i, float(c["y"][i])
        top = ax.get_ylim()[1]
        sp0 = max((c for c in hv.curves if peak(c)[1] < 0.9 * top), key=lambda c: peak(c)[1])
        i0 = peak(sp0)[0]
        px, py = ax.transData.transform((sp0["x"][i0], sp0["y"][i0]))
        w.canvas.callbacks.process("motion_notify_event", MouseEvent("motion_notify_event", w.canvas, px, py))
        msg = w.statusBar().currentMessage()
        # Mausereignisse haben ganzzahlige Pixel, Messpunkte liegen in der Vorschau < 1 px auseinander:
        # Treffer darf der Nachbarpunkt sein. Geprüft wird, dass die Anzeige genau den markierten Punkt zeigt.
        assert hv.hit is not None, msg
        hc, hi = hv.hit
        # erlaubt: ein Messpunkt Abstand plus ein Pixel in Datenkoordinaten (Vorschaugröße je nach System/Schrift)
        step = float(np.median(np.abs(np.diff(np.asarray(sp0["x"], float)))))
        nm_per_px = abs(ax.transData.inverted().transform((px + 1, py))[0] - sp0["x"][i0])
        assert abs(hc["x"][hi] - sp0["x"][i0]) <= step + nm_per_px + 1e-9, (msg, hc["x"][hi], step, nm_per_px)
        assert f"λ = {hc['x'][hi]:.1f} nm" in msg and f"A = {hc['y'][hi]:.4f}" in msg, msg
        assert list(hv.marker.get_xdata()) == [hc["x"][hi]], hv.marker.get_xdata()
        assert hv.marker.get_animated(), "Marker darf nicht exportiert werden"
        w.canvas.callbacks.process("button_press_event",
                                   MouseEvent("button_press_event", w.canvas, px, py, button=1, dblclick=True))
        lam0 = round(float(hc["x"][hi]))
        assert w.glob["bands"] == f"{lam0:g}", w.glob["bands"]
        w.pick_band(lam0 + 1)                       # erneut (±2 nm) -> wieder entfernt
        assert w.glob["bands"] == "", w.glob["bands"]
        w.render()
        report.append("hover readout + band picking: OK")

        # Ziehen mit Blitting: Inset verschieben, beim Loslassen wieder normal gezeichnet und gespeichert
        w.render()
        w.canvas.draw()
        key_, a_ = next((k, a) for k, a in w.F.axes_items.items() if a.get_visible())
        p0 = a_.get_position().frozen()
        cx, cy = a_.get_window_extent().x0 + 5, a_.get_window_extent().y0 + 5
        proc = w.canvas.callbacks.process
        proc("button_press_event", MouseEvent("button_press_event", w.canvas, cx, cy, button=1))
        assert a_.get_animated() and w.dragger._bg is not None, "Blitting nicht aktiv"
        proc("motion_notify_event", MouseEvent("motion_notify_event", w.canvas, cx + 30, cy + 20, button=1))
        proc("button_release_event", MouseEvent("button_release_event", w.canvas, cx + 30, cy + 20, button=1))
        pump()
        p1 = a_.get_position()
        assert p1.x0 > p0.x0 and p1.y0 > p0.y0 and not a_.get_animated() and w.dragger._bg is None, (p0, p1)
        assert all(getattr(ann, "_draggable", None) is None or ann._draggable._use_blit
                   for ann in w.F.ann_items.values()), "Labels ohne Blitting"
        w.series[w.current]["layout"] = {}
        w.render()
        report.append("dragging with blitting: OK")

        # Cyclovoltammetrie: Gamry-Dateien (beide Varianten), Redoxpaare, interne Referenz, Export
        def cv_sweep(e0, ip, lo, hi, step=0.002, ref=None):
            """Modell-CV: Hinlauf lo->hi, Rücklauf hi->lo; Peaks bei E0 ± 30 mV (+ optional Referenzpaar)."""
            up = np.arange(lo, hi + step / 2, step)
            E_ = np.concatenate([up, up[::-1]])
            fw = np.r_[np.ones(len(up)), np.zeros(len(up))].astype(bool)

            def wave(e_c, i_p):
                pa = i_p * np.exp(-((E_ - (e_c + 0.03)) / 0.045) ** 2) + 0.3 * i_p / (1 + np.exp(-(E_ - e_c - 0.03) / 0.02))
                pc = -0.9 * i_p * np.exp(-((E_ - (e_c - 0.03)) / 0.045) ** 2)
                return np.where(fw, pa, pc + 0.3 * i_p * np.exp(-(hi - E_) / 0.1))
            I_ = wave(e0, ip) + (wave(ref, 0.8 * ip) if ref is not None else 0)
            return E_, I_

        def write_dta(path, cycles, rate, cycle_col=False, times=None):
            head = ["EXPLAIN", "TAG\tCV", "DATE\tLABEL\t1/1/2026\tDate", "TIME\tLABEL\t12:00:00\tTime",
                    f"SCANRATE\tQUANT\t{rate:.5E}\t&Scan Rate (mV/s)", "AREA\tQUANT\t7.10000E-002\tElectrode &Area (cm^2)",
                    "CONVENTION\tIQUANT\t1\tCurrent Convention"]
            cols = "\tPt\tT\tVf\tIm\tVu" + ("\tCycle" if cycle_col else "")
            units = "\t#\ts\tV vs. Ref.\tA\tV" + ("\t#" if cycle_col else "")
            body = []
            if cycle_col:
                body += [f"CURVE\tTABLE\t{sum(len(c[0]) for c in cycles)}", cols, units]
            pt = 0
            for n, (E_, I_) in enumerate(cycles):
                if not cycle_col:
                    body += [f"CURVE{n + 1}\tTABLE", cols, units]
                for e_, i_ in zip(E_, I_):
                    t_ = times[pt] if times is not None else pt * 0.02
                    body.append(f"\t{pt}\t{t_:.2f}\t{e_:.5E}\t{i_ * 1e-6:.5E}\t0" + (f"\t{n}" if cycle_col else ""))
                    pt += 1
            path.write_text("\r\n".join(head + body) + "\r\n", encoding="latin-1", newline="")
        cvdir = out / "input" / "cv"
        cvdir.mkdir(parents=True, exist_ok=True)
        cv_files = []
        for rate, ip in ((50, 40.0), (100, 56.0), (200, 80.0)):
            p_ = cvdir / f"cv_{rate}.DTA"
            write_dta(p_, [cv_sweep(-1.02, ip, -1.4, -0.5)], rate)
            cv_files.append(p_)
        ref_file = cvdir / "cv_ref.DTA"                  # zwei Zyklen, Variante mit Spalte 'Cycle'
        write_dta(ref_file, [cv_sweep(-1.02, 80.0, -1.4, 0.9, ref=0.55)] * 2, 200, cycle_col=True)
        d_ = CVMOD.read_gamry(ref_file)
        assert len(d_["cycles"]) == 2 and d_["meta"]["scanrate"] == 200 and d_["meta"]["area"] == 0.071, d_["meta"]
        c_ = CVMOD.read_gamry(cv_files[0])["cycles"][0]
        sug = CVMOD.suggest_couples(c_["E"], c_["I"])
        assert len(sug) == 1 and sug[0][0] < -1.02 < sug[0][1], sug
        r_ = CVMOD.analyze_couple(c_["E"], c_["I"], *sug[0])
        assert abs(r_["e12"] + 1.02) < 0.003 and abs(r_["dep"] - 0.06) < 0.006 and not r_["edge"], r_
        st_cv = w.cv_state
        st_cv["files"] = [{"file": str(p_), "uid": f"cv{i}", "visible": True, "color": "#000000",
                           "label": f"{r} mV/s"} for i, (p_, r) in enumerate(zip(cv_files, (50, 100, 200)))]
        st_cv["files"].append({"file": str(ref_file), "uid": "cvref", "visible": False, "color": "#000000",
                               "label": "ref"})
        st_cv.update(couples=[list(sug[0])], ref_mode="internal", ref_uid="cvref", ref_lo=0.3, ref_hi=0.8,
                     ref_compound="ac2fc", ref_value=0.49, cycle=2)
        w.cv_tab.fill_table()
        files = w.cv_tab.export_to(out / "cv_test")
        assert all(f.exists() for f in files), files
        res = w.cv_tab.results
        assert len(res) == 3 and all(abs(r["e12"] - (-1.02 - (0.55 - 0.49))) < 0.004 for r in res), res
        assert "Ac₂Fc" in w.cv_tab.note and "+0.49 V vs. Fc" in w.cv_tab.note, w.cv_tab.note
        rs = CVMOD.randles_sevcik([50, 100, 200], [r["ipa"] * 1e6 for r in res])
        assert rs and rs[2] > 0.99, rs
        csv_txt = files[-1].read_text(encoding="utf-8-sig")
        assert csv_txt.count("\n") == 4 and "E_half_V" in csv_txt, csv_txt
        assert any(c_ is st_cv["files"][0] for c_, _, _ in PRJ._path_slots({"cv": st_cv})), "CV-Dateien fehlen im Projekt"
        report.append("cyclic voltammetry: OK")

        # CV-Ausbau: Gruppe + eigene Referenz je Messung (zweites "Lösungsmittel"), Stapeln, E½ je Kurve,
        # Auftragungen gegen die Scanrate (ΔE_p, Randles-Ševčík, Trumpet)
        t_cv = w.cv_tab
        for e_ in st_cv["files"]:
            e_["group"] = "A"
        for r_ in (50, 100):                            # Gruppe B: E½ −0.92 V, eigenes Ac₂Fc bei +0.75 V (gemessen)
            p_ = cvdir / f"cvB_{r_}.DTA"
            write_dta(p_, [cv_sweep(-0.92, 60.0 * (r_ / 50) ** 0.5, -1.4, 1.1, ref=0.75)], r_)
            st_cv["files"].append({"file": str(p_), "uid": f"cvB{r_}", "visible": True, "color": "#000000",
                                   "label": f"B {r_} mV/s", "group": "B"})
        for e_ in st_cv["files"][-2:]:
            e_["ref"] = {"mode": "internal", "uid": e_["uid"], "lo": 0.5, "hi": 1.0, "compound": "ac2fc", "value": 0.49}
        st_cv.update(plot="cv", stack=True, e12_each=True, show_e12=True)
        t_cv.fill_table()
        spec_ = t_cv.figure_spec()
        resB = [r_ for r_ in t_cv.results if r_["group"] == "B"]
        assert len(resB) == 2 and all(abs(r_["e12"] - (-0.92 - (0.75 - 0.49))) < 0.004 for r_ in resB), resB
        resA = [r_ for r_ in t_cv.results if r_["group"] == "A"]
        assert len(resA) == 3 and all(abs(r_["e12"] - (-1.02 - (0.55 - 0.49))) < 0.004 for r_ in resA), resA
        cfg_, curves_, labels_, _ = spec_
        offs_ = [c_.get("off", 0) for c_ in curves_]
        assert offs_ == sorted(offs_, reverse=True) and offs_[0] > 0 == offs_[-1] and cfg_["y_axis"] == "no_numbers"
        assert len(labels_) == 5 and all(l_.get("y") is not None and "1/2" in l_["text"] for l_ in labels_), labels_
        t_cv.render()
        assert all(getattr(a_, "_anchor_y", None) is not None for a_ in t_cv.F.ann_items.values())
        # Peakpotentiale an einzelnen Peaks, y-Achse aus, Struktur je Messung (in Kurvenfarbe)
        st_cv.update(peak_labels="both", y_axis="off")
        st_cv["files"][0].update(structure=str(cdxml), struct_color=True)
        cfg_, curves_, labels_, _ = t_cv.figure_spec()
        assert len(labels_) == 10 and {l_["side"] for l_ in labels_} == {"above", "below"}, len(labels_)
        assert cfg_["y_axis"] == "off" and [i_["id"] for i_ in cfg_["images"]] == ["struktur_cv0"], cfg_["images"]
        t_cv.render()
        assert "image_struktur_cv0" in t_cv.F.axes_items
        assert any(c_ is st_cv["files"][0] and k_ == "structure" for c_, k_, _ in PRJ._path_slots({"cv": st_cv}))
        st_cv["files"][0].pop("structure")
        st_cv.update(peak_labels="e12", y_axis="auto")
        for plot_, n_series in (("dep", 2), ("rs", 4), ("trumpet", 4)):
            st_cv["plot"] = plot_
            cfg_, curves_, _, _ = t_cv.figure_spec()
            pts_ = [c_ for c_ in curves_ if c_.get("marker")]
            assert len(pts_) == n_series, (plot_, len(pts_))
            if plot_ == "dep":
                assert all(abs(y_ - 60) < 8 for c_ in pts_ for y_ in c_["y"]), [list(c_["y"]) for c_ in pts_]
                assert sorted(len(c_["x"]) for c_ in pts_) == [2, 3]
            if plot_ == "rs":
                assert len([c_ for c_ in curves_ if c_.get("ls") == "--"]) == 2      # Gerade nur ab 3 Scanraten (A)
            if plot_ == "trumpet":
                assert abs(min(c_["x"].min() for c_ in pts_) - np.log10(0.05)) < 1e-9
        files = t_cv.export_to(out / "cv_dep")
        assert all(f.exists() for f in files) and "group" in files[-1].read_text(encoding="utf-8-sig")
        st_cv["files"] = st_cv["files"][:1]
        assert t_cv.figure_spec() is None and "zwei Scanraten" in t_cv.note or "two scan rates" in t_cv.note
        st_cv.update(files=[], couples=[], ref_mode="none", plot="cv", stack=False, e12_each=False)
        w.cv_tab.fill_table()
        report.append("CV stacking, reference per file, rate plots: OK")

        # Spektroelektrochemie: BWSpec-Spektren + Gamry-Potential über die Uhrzeit, Nernst-Fit, Export
        import datetime as _dt
        secdir = out / "input" / "sec"
        secdir.mkdir(parents=True, exist_ok=True)
        t_start = _dt.datetime(2026, 1, 1, 12, 0, 0)
        T_ = np.arange(0.0, 1150.0, 2.0)
        E_run = -1.3 + 0.002 * T_                      # 2 mV/s
        write_dta(secdir / "sec.DTA", [(E_run, 1.0 + 0 * E_run)], 2.0, cycle_col=True, times=T_)  # Start 12:00:00
        pix = np.arange(0, 2048)
        lam_ = 200.0 + 0.35 * pix
        sec_files = []
        for j in range(0, 70):
            ts = j * 15.0 + 5.0
            e_ = -1.3 + 0.002 * ts
            ox = 1 / (1 + np.exp(-SECMOD.F_RT * (e_ + 0.80)))          # E½ = −0.80 V, n = 1
            A_ = (1 - ox) * 0.3 * np.exp(-((lam_ - 432) / 25) ** 2) + ox * 0.35 * np.exp(-((lam_ - 373) / 15) ** 2)
            hdr = ["File Version;BWSpec4.11_1", f"Date;{(t_start + _dt.timedelta(seconds=ts)):%Y-%m-%d %H:%M:%S}",
                   "coefs_a0;200", "coefs_a1;0.35", "coefs_a2;0", "coefs_a3;0", "sel_pixel_start;0",
                   "Pixel;Wavelength;Wavenumber;Raman Shift;Dark;Reference;Raw data #1;Dark Subtracted #1;%TR #1;"
                   "Absorbance #1;Irradiance (W/m^2/nm) #1"]
            rows_ = [f"{p_};   ;   ;   ;0;0;0;0;0;{a_:.5f};0;" for p_, a_ in zip(pix, A_)]
            f_ = secdir / f"s{j:03d}.txt"
            f_.write_text("\r\n".join(hdr + rows_), encoding="latin-1", newline="")
            sec_files.append(str(f_))
        (secdir / "LOG_s.txt").write_text("File Format;TXTR\r\nFile Description;Peak Monitor File\r\n",
                                         encoding="latin-1")
        assert not SECMOD.is_bwspec(secdir / "LOG_s.txt") and SECMOD.is_bwspec(sec_files[0])
        sp_ = [SECMOD.read_bwspec(f_) for f_ in sec_files]
        E_map = SECMOD.potentials(sp_, CVMOD.read_gamry(secdir / "sec.DTA"))
        assert np.allclose(E_map, -1.3 + 0.002 * (np.arange(70) * 15.0 + 5.0), atol=1e-3), E_map[:3]
        a432 = np.array([np.interp(432, s_["lam"], s_["A"]) for s_ in sp_])
        fit_ = SECMOD.nernst_fit(E_map, a432)
        assert abs(fit_["e12"] + 0.80) < 0.005 and abs(fit_["n"] - 1.0) < 0.1, fit_
        st_sec = w.sec_state
        st_sec.update(spec_files=sec_files, dta=str(secdir / "sec.DTA"), bands="373, 432", mode="spectra")
        files = w.sec_tab.export_to(out / "sec_spectra")
        assert all(f.exists() for f in files), files
        st_sec.update(mode="trace", trace_lams="432")
        files = w.sec_tab.export_to(out / "sec_trace")
        assert all(f.exists() for f in files) and abs(w.sec_tab.info[432.0]["e12"] + 0.80) < 0.005
        slots_ = PRJ._path_slots({"sec": st_sec})
        assert sum(1 for c_, k_, _ in slots_ if c_ is st_sec["spec_files"]) == 70 and \
            any(c_ is st_sec and k_ == "dta" for c_, k_, _ in slots_), "SEC-Dateien fehlen im Projekt"
        st_sec.update(mode="spectra")
        report.append("spectroelectrochemistry: OK")

        # SEC im Overlay: Spektren nach Potential übernehmen, nur normiert (kein ε aus der Dünnschichtzelle)
        ov_, st_ov = w.ov_tab, w.ov_state
        saved_ov = {k: json.loads(json.dumps(st_ov[k])) for k in ("entries", "mode", "nlo", "nhi", "baseline")}
        st_ov.update(entries=[], mode="norm", nlo=340.0, nhi=460.0)
        ov_.add_sec_entries([0, 69])
        e0, e1 = st_ov["entries"]
        assert e0["kind"] == "sec" and abs(e0["E"] - (-1.3 + 0.002 * 5.0)) < 1e-3, e0
        assert "V vs. Ag/AgNO" in e0["label"] and e1["E"] > e0["E"], (e0["label"], e1["E"])
        ov_.render()
        cs_ = [c_ for c_ in ov_.F.curves if c_.get("label") in (e0["label"], e1["label"]) or "SEC" in str(c_.get("label"))]
        assert len(cs_) == 2, [c_.get("label") for c_ in ov_.F.curves]
        for c_, peak_ in zip(cs_, (432, 373)):          # reduziert: Bande bei 432 nm, oxidiert: 373 nm
            win_ = (c_["x"] >= 340) & (c_["x"] <= 460)
            assert abs(float(np.max(c_["val"][win_])) - 1.0) < 1e-6, "SEC nicht normiert"
            assert abs(float(c_["x"][win_][np.argmax(c_["val"][win_])]) - peak_) < 2, (peak_, c_["label"])
        assert c_["x"].min() >= SECMOD.LAM_RANGE[0] and c_["x"].max() <= SECMOD.LAM_RANGE[1]
        assert any(c_ is e0 and k_ == "file" for c_, k_, _ in PRJ._path_slots({"overlay": st_ov}))
        # Serie: EIN Eintrag, gemeinsamer Faktor (auf das Startspektrum) -> Verhältnisse bleiben erhalten
        st_ov.update(entries=[], baseline=False)
        ov_.add_sec_series(0, 69)
        ov_.render()
        assert len(ov_.F.curves) == 70 and len(st_ov["entries"]) == 1, len(ov_.F.curves)
        named_ = [c_["label"] for c_ in ov_.F.curves if c_.get("label")]
        assert len(named_) == 2 and all("V vs. Ag/AgNO" in n_ for n_ in named_), named_
        raw0, raw1 = (SECMOD.read_bwspec(sec_files[i_]) for i_ in (0, 69))
        start_ = next(c_ for c_ in ov_.F.curves if c_["color"] == SECMOD.START_COLOR)
        end_ = next(c_ for c_ in ov_.F.curves if c_["color"] == SECMOD.END_COLOR)
        win_ = (start_["x"] >= 340) & (start_["x"] <= 460)
        assert abs(float(start_["val"][win_].max()) - 1.0) < 1e-6
        r_raw = np.interp(373, raw1["lam"], raw1["A"]) / np.interp(432, raw0["lam"], raw0["A"])
        r_plot = np.interp(373, end_["x"], end_["val"]) / np.interp(432, start_["x"], start_["val"])
        assert abs(r_plot / r_raw - 1) < 0.02, (r_plot, r_raw)      # nicht einzeln normiert
        assert sum(1 for c_, k_, _ in PRJ._path_slots({"overlay": st_ov}) if c_ is st_ov["entries"][0]["files"]) == 70
        st_ov["entries"][0]["ends_only"] = True
        ov_.render()
        assert len(ov_.F.curves) == 2
        st_ov["mode"] = "eps"                           # ε-Modus: SEC wird ausgelassen, nicht falsch skaliert
        assert ov_.figure_spec() is None or all("SEC" not in str(c_.get("label")) for c_ in ov_.figure_spec()[1])
        st_ov.update(saved_ov)
        st_sec.update(spec_files=[], dta=None, mode="spectra", trace_lams="", bands="")
        report.append("SEC spectra in overlay: OK")

        # EPR: BES3T lesen (G -> mT), Dunkelspektrum, Basislinie, Ausblenden, Simulation anpassen, EasySpin-Parameter
        eprdir = out / "input" / "epr"
        eprdir.mkdir(parents=True, exist_ok=True)
        Bg = np.linspace(4400.0, 5100.0, 7001)                       # G
        signal = -np.gradient(np.exp(-((Bg - 4700) / 30) ** 2)) * 1000  # Ableitungslinie bei 470 mT
        drift = 0.05 * (Bg - 4400)                                     # lineare Drift der Basislinie

        def write_bes3t(stem, y, time="11:30:15", temp=100.0):
            (eprdir / f"{stem}.dsc").write_text("\n".join([
                "#DESC\t1.2", "DSRC\tEXP", "BSEQ\tLIT", "IKKF\tREAL", "XTYP\tIDX", "YTYP\tNODATA", "IRFMT\tD",
                f"XPTS\t{len(Bg)}", f"XMIN\t{Bg[0]}", f"XWID\t{Bg[-1] - Bg[0]}", "XUNI\t'G'", "#SPL\t1.2",
                "MWFQ\t9338553208.5", f"STMP\t{temp}", "B0MA\t0.00095", "MWPW\t0.01", "DATE\t08/22/25",
                f"TIME\t{time}"]),
                encoding="latin-1")
            y.astype("<f8").tofile(eprdir / f"{stem}.DTA")
        dark_bg = 3.0 * np.sin((Bg - 4400) / 200)                      # Untergrund, der auch dunkel da ist
        write_bes3t("dark", drift + dark_bg)
        write_bes3t("light", drift + dark_bg + signal)
        sim_B = np.linspace(440.0, 510.0, 1401)                        # mT, wie EasySpin
        sim_I = 0.5 * np.interp(sim_B, Bg / 10, signal)
        np.savetxt(eprdir / "sim.txt", np.column_stack([sim_B, sim_I]), delimiter="\t")
        (eprdir / "sim_params.txt").write_text("Sys.S = 1;\nSys.g = 2.0023;\nSys.D = [11100 450]; % MHz\n"
                                               "Exp.mwFreq = 9.3386;\n", encoding="utf-8")
        sp_e = EPRMOD.read_any(eprdir / "light.DTA")[0]
        assert abs(sp_e["B"][0] - 440.0) < 1e-9 and abs(sp_e["meta"]["mw_GHz"] - 9.3385535) < 1e-6, sp_e["meta"]
        assert abs(sp_e["meta"]["mod_mT"] - 0.95) < 1e-9 and abs(sp_e["meta"]["power_mW"] - 10) < 1e-9
        pr_ = EPRMOD.parse_easyspin((eprdir / "sim_params.txt").read_text(encoding="utf-8"))
        assert pr_["Sys.D"] == [11100.0, 450.0] and "0.3703 cm" in EPRMOD.zfs_summary(pr_)
        assert abs(EPRMOD.g_value(9.3386, 333.2) - 2.0024) < 1e-3
        t_e = w.epr_tab
        ed = t_e._new("exp", str(eprdir / "dark.dsc"))
        el = t_e._new("exp", str(eprdir / "light.dsc"))
        es = t_e._new("sim", str(eprdir / "sim.txt"))
        ed["visible"] = False
        el["dark"] = ed["uid"]
        es.update(fit_to=el["uid"], params=str(eprdir / "sim_params.txt"))
        w.epr_state.update(entries=[ed, el, es], bl_order=1, exclude="499-501", smooth=0.0, normalize=False,
                           stack=False, labels="Z@452, X@490", show_params=True)
        cache_ = {}
        Bp, Ip = t_e.processed(el, cache_)
        cleaned = Ip[np.isfinite(Ip)]
        ref_ = (signal / 1.0)[np.isfinite(Ip)]
        assert np.max(np.abs(cleaned - ref_)) < 0.02 * np.ptp(signal), "Dunkelspektrum/Basislinie"
        assert np.isnan(Ip[(Bp > 499.2) & (Bp < 500.8)]).all(), "Bereich nicht ausgeblendet"
        data_, _ = t_e.components([el, es], {}, [])
        Is = data_[es["uid"]][1]
        assert abs(np.nanmax(Is) / np.nanmax(Ip) - 1) < 0.05, "Simulation nicht an Messung angepasst"
        t_e.fill_table()
        files = w.epr_tab.export_to(out / "epr_test")
        assert all(f.exists() for f in files), files
        F_e = w.epr_tab.build(MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI))
        assert any("cm" in a.get_text() for a in F_e.ann_items.values()), "D/E-Label fehlt"
        slots_ = PRJ._path_slots({"epr": w.epr_state})
        assert any(c_ is es and k_ == "params" for c_, k_, _ in slots_), "EPR-Parameter fehlen im Projekt"
        # Intensität gegen Zeit: Amplituden 25/50/75/100 % im Minutentakt nach dem Dunkelspektrum (11:30:15)
        series = [ed]
        for k_, amp in enumerate((0.25, 0.5, 0.75, 1.0), 1):
            write_bes3t(f"kin{k_}", drift + dark_bg + amp * signal, time=f"11:3{k_}:15")
            ek = t_e._new("exp", str(eprdir / f"kin{k_}.dsc"))
            ek["label"] = f"kin{k_}"
            series.append(ek)
        w.epr_state.update(entries=series, exclude="", labels="", show_params=False, mode="intensity",
                           int_window="455-485", int_method="double", int_x="time", normalize=True)
        t_e.fill_table()
        t_e.table.selectRow(1)
        series[1]["dark"] = ed["uid"]
        t_e.dark_for_all()
        files = w.epr_tab.export_to(out / "epr_kin")
        xs_ = [v[0] for v in t_e.series_values]
        ys_ = [v[1] for v in t_e.series_values]
        assert np.allclose(xs_, [1, 2, 3, 4]) and np.allclose(ys_, [0.25, 0.5, 0.75, 1.0], atol=0.02), (xs_, ys_)
        w.epr_state["int_method"] = "pp"
        w.epr_tab.export_to(out / "epr_kin_pp")
        assert np.allclose([v[1] for v in t_e.series_values], [0.25, 0.5, 0.75, 1.0], atol=0.02)
        txt_ = next(f for f in files if f.name.endswith("_kin4.txt"))
        arr_ = np.loadtxt(txt_, comments="%")
        assert arr_.shape[1] == 2 and abs(arr_[0, 0] - 440.0) < 1e-6 and "mwFreq" in txt_.read_text(encoding="utf-8")
        assert np.max(np.abs(arr_[:, 1] - signal)) < 0.02 * np.ptp(signal), "Export nicht verarbeitet"
        assert any(f.name.endswith("_intensity.csv") for f in files) and any(f.name.endswith("_data.csv") for f in files)
        w.epr_state.update(entries=[], labels="", exclude="", show_params=False, mode="spectra")
        report.append("EPR (BES3T, dark spectrum, simulation, intensity, export): OK")

        # EPR S = ½: TEMPO-artiges Spektrum mit Feldfehler +0.25 mT fitten -> Kalibrierung; zwei Spezies 70:30
        mw_ = 9.40
        Bt = np.linspace(330.0, 345.0, 6001)
        tempo_I = EPRMOD.iso_spectrum(Bt, mw_, 2.0055, [(1, 1.0, 1.55)], 0.15)
        noise = np.random.default_rng(0).standard_normal(len(Bt)) * 0.01 * np.ptp(tempo_I)
        np.savetxt(eprdir / "tempo-9p400000.txt", np.column_stack([Bt + 0.25, tempo_I + noise]),
                   header="B [mT]\tI [a.U.]", comments="", delimiter="\t")
        rad_I = EPRMOD.iso_spectrum(Bt, mw_, 2.0030, [(2, 0.5, 0.45)], 0.12)
        np.savetxt(eprdir / "radikal-9p400000.txt", np.column_stack([Bt + 0.25, rad_I]),
                   header="B [mT]\tI [a.U.]", comments="", delimiter="\t")
        et = t_e._new("exp", str(eprdir / "tempo-9p400000.txt"))
        er = t_e._new("exp", str(eprdir / "radikal-9p400000.txt"))
        assert abs(t_e.spectrum(et)["meta"]["mw_GHz"] - 9.4) < 1e-9
        w.epr_state.update(entries=[et, er], bl_order=-1, smooth=0.0, normalize=True, stack=False,
                           show_sum=True, show_residual=True, calib_uid=None, calib_g=2.0055)
        t_e.fill_table()
        t_e.table.selectRow(0)
        t_e.add_iso()
        ti = w.epr_state["entries"][-1]
        ti["nuclei"] = "1 14N 1.4"
        t_e.table.selectRow(2)
        t_e.fit_current()
        assert abs(ti["g"] - EPRMOD.g_value(mw_, EPRMOD.b_res(mw_, 2.0055) + 0.25)) < 2e-5, ti
        assert "1.55" in ti["nuclei"] and ti["fit"]["r2"] > 0.98, ti     # 1 % Rauschen
        w.epr_state["calib_uid"] = ti["uid"]
        t_e.fill_table()
        dB_, _ = t_e.calibration_shift()
        assert abs(dB_ - 0.25) < 0.003, dB_
        t_e.table.selectRow(1)
        t_e.add_iso()
        ri = w.epr_state["entries"][-1]
        ri["nuclei"] = "2 1H 0.4"
        t_e.table.selectRow(3)
        t_e.fit_current()
        assert abs(ri["g"] - 2.0030) < 5e-5 and abs(EPRMOD.parse_nuclei(ri["nuclei"])[0][2] - 0.45) < 0.005, ri
        # zwei Spezies: Messung = 0.7·A + 0.3·B, beide als EasySpin-ASCII importiert
        A_ = EPRMOD.iso_spectrum(Bt, mw_, 2.0030, [(1, 1.0, 1.4)], 0.2)
        B_ = EPRMOD.iso_spectrum(Bt, mw_, 2.0100, [], 0.5)
        np.savetxt(eprdir / "mix-9p400000.txt", np.column_stack([Bt, 0.7 * A_ + 0.3 * B_]), delimiter="\t")
        np.savetxt(eprdir / "simA.txt", np.column_stack([Bt, A_]), delimiter="\t")
        np.savetxt(eprdir / "simB.txt", np.column_stack([Bt, B_]), delimiter="\t")
        em = t_e._new("exp", str(eprdir / "mix-9p400000.txt"))
        sa, sb = t_e._new("sim", str(eprdir / "simA.txt")), t_e._new("sim", str(eprdir / "simB.txt"))
        sa["fit_to"] = sb["fit_to"] = em["uid"]
        w.epr_state.update(entries=[em, sa, sb], calib_uid=None, bl_order=-1)
        info_ = []
        data_, extra_ = t_e.components([em, sa, sb], {}, info_)
        wa = np.nanmax(data_[sa["uid"]][1]) / np.nanmax(A_)
        wb = np.nanmax(data_[sb["uid"]][1]) / np.nanmax(B_)
        assert abs(wa - 0.7) < 1e-3 and abs(wb - 0.3) < 1e-3, (wa, wb)
        assert np.nanmax(np.abs(extra_[em["uid"]]["res"][1])) < 1e-6 * np.ptp(A_) and "sum" in extra_[em["uid"]]
        assert info_ and "%" in info_[0], info_
        files = w.epr_tab.export_to(out / "epr_species")
        assert all(f.exists() for f in files), files
        w.epr_state.update(entries=[], calib_uid=None, show_residual=False, bl_order=1)
        report.append("EPR S=1/2 fit, TEMPO calibration, multiple species: OK")

        # EPR-Zerfall bei konstanter Heizrate: Gauß-Intensität eines Merkmals, Arrhenius-Fit (E_a = 50 kJ/mol, ln A = 45)
        Ea_true, lnA_true = 50e3, 45.0
        temps = np.arange(100.0, 135.01, 0.5)
        beta_ = 0.5 / 120.0                                         # 0,5 K alle 2 min
        I_true = EPRMOD.decay_model(temps, np.exp(lnA_true), Ea_true, beta_)
        Bk = Bg                                                       # G, 440–510 mT
        kin_entries = []
        for j, (Tk, Ik) in enumerate(zip(temps, I_true)):
            y = -2000.0 * Ik * np.exp(-((Bk / 10 - 487.0) ** 2) / 9.0) / Tk + 0.3 * (Bk - 4400) / 10
            stem = f"temp{j:03d}"
            hh, mm = divmod(2 * j, 60)
            write_bes3t(stem, y, time=f"{12 + hh:02d}:{mm:02d}:00", temp=Tk)
            ek = t_e._new("exp", str(eprdir / f"{stem}.dsc"))
            kin_entries.append(ek)
        w.epr_state.update(entries=kin_entries, mode="intensity", int_method="gauss", int_window="470-510",
                           int_center=487.0, int_x="T", int_curie=True, ref_freq=0.0, T_offset=0.0, kin_fit=True,
                           kin_norm="lsq", bl_order=-1, smooth=0.0, normalize=True, calib_uid=None)
        t_e.fill_table()
        files = w.epr_tab.export_to(out / "epr_decay")
        r_ = t_e.kin_result
        assert r_ and abs(r_["Ea"] - Ea_true) / Ea_true < 0.02 and abs(r_["lnA"] - lnA_true) < 1.0, r_
        assert r_["ci_Ea"][0] < Ea_true < r_["ci_Ea"][1] and abs(r_["beta"] - beta_) < 1e-9, r_
        w.epr_state["kin_norm"] = "script"
        w.epr_tab.export_to(out / "epr_decay_script")
        assert abs(t_e.kin_result["Ea"] - Ea_true) / Ea_true < 0.02, t_e.kin_result
        assert "Arrhenius" in next(f for f in files if f.name.endswith("_intensity.csv")).read_text(encoding="utf-8-sig")
        w.epr_state.update(entries=[], mode="spectra", kin_fit=False, int_method="double", int_window="", int_center=0.0)
        report.append("EPR decay at constant heating rate (Arrhenius): OK")

        # Farbe der Lösung: Farbmetrik (Weiß, Grau, Gelb bei Blauabsorption) und Anzeige im ε-Tab
        L_ = COLOR.LAM
        assert COLOR.to_hex(COLOR.absorbance_to_rgb(0 * L_)[0]) == "#FFFFFF"
        assert COLOR.to_hex(COLOR.absorbance_to_rgb(0 * L_ + 0.3)[0]) == "#BCBCBC"     # T = 50 % -> sRGB 188
        r_, g_, b_ = COLOR.absorbance_to_rgb(np.exp(-0.5 * ((L_ - 450) / 30) ** 2))[0]
        assert r_ > 0.9 and g_ > 0.9 and b_ < 0.5, (r_, g_, b_)                        # absorbiert Blau -> Gelb
        w.glob.update(color_show=True, color_d=1.0)
        w.series["TEST-A"].pop("color_c", None)
        w.apply_globals()
        w.render()
        assert w.lbl_color.isVisibleTo(w) and "#" in w.lbl_color_info.text(), w.lbl_color_info.text()
        hx1 = w.lbl_color_info.text().split()[0]
        c_max = max(s_["c"] for s_ in w.groups["TEST-A"])
        assert f"c = {c_max:g}" in w.lbl_color_info.text(), w.lbl_color_info.text()
        w.sp_color_c.setValue(4 * c_max)                    # konzentrierter -> dunkler
        hx2 = w.lbl_color_info.text().split()[0]
        lum = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5))
        assert lum(hx2) < lum(hx1) and w.series["TEST-A"]["color_c"] == 4 * c_max, (hx1, hx2)
        w.glob["color_show"] = False
        w.series["TEST-A"].pop("color_c", None)
        w.apply_globals()
        assert not w.lbl_color.isVisibleTo(w)
        report.append("solution colour: OK")

        # Layout ε-Tab: Vorschau statt Leer-Zustand, eingeklappte Bereiche melden Abweichungen vom Standard
        assert w.preview_stack.currentIndex() == 1
        w.sec_eval.btn.setChecked(False)
        assert not w.sec_eval.body.isVisibleTo(w)
        r2_old = w.sp_r2.value()
        w.sp_r2.setValue(DEFAULT_GLOB["min_r2"])
        w.sp_min.setValue(DEFAULT_GLOB["min_points"])
        w.cb_shoulders.setChecked(DEFAULT_GLOB["shoulders"])
        assert not w.sec_eval.changed
        w.sp_r2.setValue(0.95)
        assert w.sec_eval.changed and T("adv_changed") in w.sec_eval.btn.text()
        w.sp_r2.setValue(r2_old)
        w.sec_eval.btn.setChecked(True)
        assert w.sec_eval.body.isVisibleTo(w)
        labels = [lb for lb in w.main_tabs.widget(0).findChildren(QLabel)
                  if lb.text() in (T("molar_mass_short"), T("ymax"))]
        assert len({lb.minimumWidth() for lb in labels}) == 1 and labels[0].minimumWidth() > 0
        report.append("eps tab layout (sections, empty state): OK")

        # Erscheinungsbild: Fusion, Palette je Modus, Akzentbuttons, Symbole; Ergebnisse bleiben erhalten
        w.render()
        n_rows = w.table.rowCount()
        for mode in ("dark", "light"):
            w.switch_theme(mode)
            pal = QApplication.instance().palette()
            assert STYLE.base_style == "fusion"
            assert pal.color(pal.ColorRole.Window).name().upper() == STYLE.COLORS[mode]["window"], mode
            assert w.btn_export.property("accent") and w.btn_open.property("accent")
            assert not w.btn_export.icon().isNull(), "icon"
            assert w.table.rowCount() == n_rows, (w.table.rowCount(), n_rows)
        assert w.findChildren(QFrame, "card") and not w.main_tabs.widget(0).findChildren(QGroupBox)
        w.switch_theme("system")
        # Werkzeugleiste (nach Neuaufbau nur eine) und Listenknöpfe mit Symbol
        bars = w.findChildren(uvvis_tabs.QWidget, "mainToolbar")
        acts = [a for a in w.toolbar.actions() if not a.isSeparator()]
        assert len(bars) == 1 and len(acts) == 5 and all(not a.icon().isNull() for a in acts), (len(bars), len(acts))
        arrows = [b for b in w.epr_tab.findChildren(QPushButton) if b.toolTip() == T("move_up")]
        assert arrows and arrows[0].text() == "" and not arrows[0].icon().isNull()
        report.append("appearance (Fusion, light/dark, toolbar): OK")

        # Umbenennung UVVisTool -> Spectravolt: alte Einstellungen und Datenordner einmalig übernehmen
        old_s = QSettings(str(out / "old_settings.ini"), QSettings.IniFormat)
        old_s.setValue("lang", "en")
        old_s.setValue("recent", [str(out / "p1"), str(out / "p2")])
        new_s = QSettings(str(out / "new_settings.ini"), QSettings.IniFormat)
        new_s.clear()
        assert migrate_settings(old_s, new_s) and new_s.value("lang") == "en" and len(new_s.value("recent")) == 2
        new_s.setValue("lang", "de")
        assert not migrate_settings(old_s, new_s) and new_s.value("lang") == "de"   # nur einmal, nichts überschreiben
        base_ = out / "appdata"
        shutil.rmtree(base_, ignore_errors=True)
        (base_ / "UVVisTool" / "models").mkdir(parents=True)
        (base_ / "UVVisTool" / "models" / "m.onnx").write_bytes(b"x")
        d_ = IMG.app_data_dir(base_)
        assert d_.name == "Spectravolt" and (d_ / "models" / "m.onnx").exists() and not (base_ / "UVVisTool").exists()
        assert APP_NAME == "Spectravolt" and UPD.REPO.endswith("/spectravolt")
        report.append("rename (settings + data folder migration): OK")

        # Release Notes aus den Changelogs (nur im Quellcode; das Skript liegt nicht in der gebauten App)
        rn_path = Path(__file__).resolve().parent / "release_notes.py"
        if rn_path.exists() and not getattr(sys, "frozen", False):
            import importlib.util
            spec_ = importlib.util.spec_from_file_location("release_notes", rn_path)
            RN = importlib.util.module_from_spec(spec_)
            spec_.loader.exec_module(RN)
            en_ = (rn_path.parent / "CHANGELOG.md").read_text(encoding="utf-8")
            de_ = (rn_path.parent / "CHANGELOG.de.md").read_text(encoding="utf-8")
            txt_ = RN.notes(APP_VERSION, en_, de_)
            assert txt_.startswith("## English") and "## Deutsch" in txt_ and f"{APP_NAME}-windows-x64.zip" in txt_
            assert f"## {APP_VERSION}" not in txt_ and "\n## 1." not in txt_          # nur dieser Abschnitt
            try:
                RN.notes("0.0.1", en_, de_)
                raise AssertionError("fehlende Version nicht erkannt")
            except ValueError:
                pass
            report.append("release notes from changelogs: OK")

        # Update-Prüfung (ohne Netz: Versionsvergleich, API-Antwort, Meldungstext)
        assert UPD.parse_version("v1.10.0") > UPD.parse_version("1.9.9") and UPD.parse_version("x") == ()
        assert UPD.is_newer("1.4.1", "1.4.0") and not UPD.is_newer("1.4", "1.4.0") and not UPD.is_newer("", "1.0")
        lbl = UPD.platform_label()
        fake = {"tag_name": "v99.0.0", "html_url": "https://example.invalid/r",
                "assets": [{"name": f"Spectravolt-{x}.zip"} for x in ("windows-x64", "macos-arm64", "macos-x64")]
                + [{"name": "Spectravolt-linux-x64.tar.gz"}]}
        info = UPD.parse_release(fake)
        assert info["version"] == "99.0.0" and lbl in info["asset"], info
        assert "99.0.0" in w.update_text(info, manual=False)
        assert w.update_text(dict(info, version=APP_VERSION), manual=False) is None
        assert APP_VERSION in w.update_text(dict(info, version=APP_VERSION), manual=True)
        report.append("update check: OK")

        # Projekt automatisch gespeichert -> in neuem Fenster öffnen (Dateien als Kopie, Pfade relativ)
        w.ov_state["entries"][0]["file"] = w.import_file(w.ov_state["entries"][0]["file"], "data")
        w.push_undo()
        pump(1.5)                                      # automatisches Speichern abwarten
        w.maybe_save()
        txt = (proj / PRJ.PROJECT_FILE).read_text(encoding="utf-8")
        assert str(out / "input") not in txt.replace(str(proj), ""), "absolute Pfade im Projekt"
        assert (proj / "data" / csv.name).exists() and (proj / "images" / cdxml.name).exists()
        w2 = MainWindow()
        assert w2.open_project(proj, ask=False)
        pump()
        assert set(w2.groups) == {"TEST-A", "TEST-B"} and w2.series["TEST-A"]["mw"] == 95.1, w2.groups
        assert len(w2.ov_state.get("entries", [])) == 2 and w2.fl_state.get("em_file"), "Tabs nicht geladen"
        report.append("project save/load: OK")

        # Undo/Redo
        before = w2.glob["cutoff"]
        w2.sp_cut.setValue(before + 0.5)
        pump(0.8)
        assert w2.glob["cutoff"] == before + 0.5
        w2.undo()
        pump()
        assert abs(w2.glob["cutoff"] - before) < 1e-9, w2.glob["cutoff"]
        w2.redo()
        pump()
        assert abs(w2.glob["cutoff"] - (before + 0.5)) < 1e-9, w2.glob["cutoff"]
        report.append("undo/redo: OK")
        for lang in ("en", "de"):
            w.switch_lang(lang)
        report.append("OK")
    except Exception:
        ok = False
        report.append("FAILED\n" + traceback.format_exc())
    (out / "selftest_report.txt").write_text("\n".join(report), encoding="utf-8")
    try:                                   # Windows-Konsole (cp1252) kann z. B. kein λ: ersetzen statt abstürzen
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    print("\n".join(report))
    return 0 if ok else 1


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
        sys.exit(selftest(outdir, "--selftest-isnet" in sys.argv))
    install_crash_handler()
    QApplication.setApplicationName(APP_NAME)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args and Path(args[0]).exists():
        w.open_csv(args[0])          # Datei per Doppelklick / Drag auf das Programmsymbol
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
