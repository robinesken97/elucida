"""
elucida/tabs/base.py - Zusätzliche Tabs der GUI: Overlay (Messung + TD-DFT) und Fluoreszenz.
"""
from __future__ import annotations

import copy
import csv
import html
import math
import re
import traceback
import uuid
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.backends.backend_agg import FigureCanvasAgg
from elucida.app.canvas_theme import register as register_canvas
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox,
                               QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QFrame, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget, QDialog, QDialogButtonBox, QListWidget, QMenu, QMessageBox, QPlainTextEdit, QTabWidget)

from elucida.core import color as COLOR
from elucida.core import uvvis as core
from elucida.core import tddft as X
from elucida.formats import calc as CALC
from elucida.core import images as IMG
from elucida.app import project as PRJ
from elucida.app.i18n import T, get_lang
from elucida.app import style as STYLE
from elucida.app.style import HINT_CSS, WARN_CSS, align_forms, make_form

PREVIEW_DPI = 90
PALETTE = ["#000000", "#e8231b", "#1764e8", "#1f9e4a", "#a35ce0", "#e08a00", "#00a0b0", "#8c564b"]
UNITS = [("mM", "mM"), ("uM", "µM"), ("mg/mL", "mg mL⁻¹"), ("M", "M")]     # (Schlüssel, Anzeige)


def parse_num(txt):
    txt = (txt or "").strip().replace(",", ".")
    if not txt:
        return None
    try:
        v = float(txt)
        return v if v > 0 else None
    except ValueError:
        return None


def _plain(label):
    """Achsenbeschriftung ohne Mathtext für CSV-Köpfe: 'cm$^{-1}$' -> 'cm^-1'."""
    s = re.sub(r"\$\^\{?([^}$]*)\}?\$", r"^\1", str(label))
    s = re.sub(r"\$_\{?([^}$]*)\}?\$", r"_\1", s)
    return s.replace("$", "").replace("\\mathrm", "").replace("{", "").replace("}", "")


def write_curves_csv(path, curves, xlabel, ylabel):
    """Gezeichnete Kurven als CSV (UTF-8, Komma): je Kurve ein x/y-Spaltenpaar, Werte ohne Stapelversatz
    ('val'). Lässt sich in Origin, Excel und MATLAB (readmatrix) öffnen."""
    curves = [c for c in curves if len(c["x"]) and not c.get("aux")]    # aux: Hilfslinien (z. B. Basislinien)
    cols, head = [], []
    for k, c in enumerate(curves):
        name = str(c.get("label") or c.get("tag") or f"curve {k + 1}").replace("\u200b", "")
        cols += [np.asarray(c["x"], float), np.asarray(c.get("val", c["y"]), float)]
        head += [f"{name}: {_plain(xlabel)}", f"{name}: {_plain(ylabel)}"]
    n = max((len(c) for c in cols), default=0)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for i in range(n):
            w.writerow([(f"{c[i]:.10g}" if i < len(c) and np.isfinite(c[i]) else "") for c in cols])
    return path


def reset_button(reset_layout, reset_defaults):
    """Knopf „Zurücksetzen“ mit Menü: nur Layout (Lage von Labels/Inset/Bildern) oder alles auf Standard."""
    b = QPushButton(STYLE.icon("reset"), T("btn_reset"))
    m = QMenu(b)
    m.addAction(T("btn_reset_layout"), reset_layout)
    a = m.addAction(T("btn_reset_defaults"), reset_defaults)
    a.setToolTip(T("btn_reset_defaults_tip"))
    m.setToolTipsVisible(True)
    b.setMenu(m)
    b.setToolTip(T("btn_reset_defaults_tip"))
    return b


def color_button(color, on_pick, cell=False, small=False):
    """Farbfeld; cell: in einer Tabellenzelle mit gleichem Rand ringsum (mittig wie die übrigen Zellen); small: flaches
    Feld neben einem Buchstaben (ohne die Mindesthöhe der Knöpfe, bleibt in seiner Zeile)."""
    b = QPushButton()
    css = "margin: 6px 12px; min-height: 0px; padding: 0px; " if cell else ""   # passt in die Zeilenhöhe
    if small:
        css = "min-height: 0px; max-height: 16px; padding: 0px; border-radius: 4px; "
        b.setFixedSize(36, 18)
    elif not cell:
        b.setFixedSize(44, 22)
    b.setProperty("cellcss", css)
    b.setStyleSheet(f"{css}background-color: {color}; border: 1px solid #777;")

    def pick():
        c = QColorDialog.getColor(QColor(b.property("color") or color))
        if c.isValid():
            b.setProperty("color", c.name())
            b.setStyleSheet(f"{css}background-color: {c.name()}; border: 1px solid #777;")
            on_pick(c.name())
    b.setProperty("color", color)
    b.clicked.connect(pick)
    return b


ALL_TEXT_OPTS = ("fonts", "greek", "labels", "label_size", "axes_frame", "struct_frame")


class TextFormatCard(QWidget):
    """Inhalt der Karte „Schrift und Rahmen“ (Menü Format) am Ende des Schritts Darstellung; früher ein Dialog
    (Nutzerwunsch 2026-11-11: keine Popups). Zeigt nur, was der Tab im Bild hat (`opts` = TEXT_OPTS). Chip „Nur dieser
    Tab“ = eigenes Format (`main.tab_fmt[key]`), sonst der Standard aller Tabs (`main.text_fmt`). Jede Änderung gilt
    sofort (`main.update_text_format`: alle Tabs neu, ein Rückgängig-Schritt); Zahlenfelder gesammelt nach kurzer Pause.
    Die Karte selbst (`box`) baut der Tab: Klappkarte (QGroupBox + Fold) bzw. im ε-Tab eine Karte wie dort üblich."""

    def __init__(self, main, key, opts):
        super().__init__()
        self.main, self.key, self.fold, self.box = main, key, None, None
        self._loading, self._pending = False, {}
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.flush)
        lk = f"tf_grp_labels_{key}"
        from elucida.app.i18n import TEXTS
        label_tip = T(lk if lk in TEXTS else "tf_grp_labels")
        f = make_form(self)
        f.setContentsMargins(0, 0, 0, 0)
        self.cb_own = QCheckBox(T("tf_own"))
        self.cb_own.toggled.connect(self._own_toggled)
        row = QHBoxLayout()
        row.addWidget(self.cb_own)
        row.addStretch(1)
        f.addRow(T("tf_scope"), row)
        hint = STYLE.HintLabel(T("tf_own_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)                # Hinweise grau wie überall
        f.addRow(hint)
        self.cmb_font = self.cmb_sym = self.cb_greek = self.sp_size = self.cb_bold = self.cb_italic = None
        self.btn_color = self.cb_axes = self.cb_struct = None
        if "fonts" in opts:
            self.cmb_font = QFontComboBox()
            self.cmb_font.currentFontChanged.connect(lambda fn: self._set("font", fn.family()))
            f.addRow(T("tf_font"), self.cmb_font)
            if "greek" in opts:
                self.cmb_sym = QFontComboBox()
                self.cmb_sym.currentFontChanged.connect(lambda fn: self._set("symbol_font", fn.family()))
                f.addRow(T("tf_symbol_font"), self.cmb_sym)
                self.cb_greek = QCheckBox(T("tf_greek_c"))
                self.cb_greek.setProperty("chip_here", True)      # gehört zur Symbolschrift darüber
                self.cb_greek.toggled.connect(lambda on: self._set("greek", on))
                f.addRow(self.cb_greek)
        if "labels" in opts:
            if "label_size" in opts:
                self.sp_size = QDoubleSpinBox(decimals=1, minimum=0, maximum=40, singleStep=0.5, suffix=" pt")
                self.sp_size.setSpecialValueText(T("tf_auto"))
                self.sp_size.setToolTip(label_tip)
                self.sp_size.valueChanged.connect(lambda v: self._set("label_pt", v))
                f.addRow(T("tf_label_size_row"), self.sp_size)
            self.cb_bold, self.cb_italic = QCheckBox(T("tf_bold")), QCheckBox(T("tf_italic"))
            row = QHBoxLayout()
            for k_, cb in (("bold", self.cb_bold), ("italic", self.cb_italic)):
                cb.setToolTip(label_tip)
                cb.toggled.connect(lambda on, k_=k_: self._set(k_, on))
                row.addWidget(cb)
            row.addStretch(1)
            f.addRow(T("tf_label_style"), row)
            self.btn_color = color_button(core.TEXT_DEFAULTS["color"], lambda c: self._set("color", c))
            self.btn_color.setToolTip(label_tip)
            row = QHBoxLayout()                               # Farbfeld in normaler Größe, nicht über die ganze Spalte
            row.addWidget(self.btn_color)
            row.addStretch(1)
            f.addRow(T("tf_label_color"), row)
        frames = [(k_, QCheckBox(T(t_))) for k_, t_ in (("axes_frame", "tf_axes_frame_c"),
                                                        ("struct_frame", "tf_struct_frame_c")) if k_ in opts]
        if frames:
            row = QHBoxLayout()
            for k_, cb in frames:
                cb.toggled.connect(lambda on, k_=k_: self._set(k_, on))
                row.addWidget(cb)
            row.addStretch(1)
            f.addRow(T("tf_grp_frames"), row)
            fr = dict(frames)
            self.cb_axes, self.cb_struct = fr.get("axes_frame"), fr.get("struct_frame")
        b = QPushButton(T("tf_defaults"))
        b.clicked.connect(self.restore_defaults)
        b.setFixedWidth(STYLE.VALUE_W)                    # einzelner Knopf: ganze Wertespalte
        f.addRow("", b)
        self.load()

    def own(self):
        return self.key in self.main.tab_fmt

    def current(self):
        """Werte der bearbeiteten Ebene: eigenes Format des Tabs oder der Standard aller Tabs."""
        return self.main.text_format(self.key) if self.own() else {**core.TEXT_DEFAULTS, **self.main.text_fmt}

    def differs(self):
        """„(geändert)“ am Titel: eigenes Format oder Abweichung vom Standard."""
        return self.own() or self.main.text_format(self.key) != core.TEXT_DEFAULTS

    def load(self):
        """Zustand -> Felder (ohne Signale: Laden ist keine Änderung)."""
        if self._pending:
            return
        tf = self.current()
        self._loading = True
        try:
            self.cb_own.setChecked(self.own())
            for cmb, k_ in ((self.cmb_font, "font"), (self.cmb_sym, "symbol_font")):
                if cmb is not None:
                    cmb.setCurrentFont(QFont(tf[k_]))
            if self.cmb_sym is not None:
                self.cb_greek.setChecked(bool(tf["greek"]))
                self.cmb_sym.setEnabled(bool(tf["greek"]))
            if self.sp_size is not None:
                self.sp_size.setValue(tf["label_pt"] or 0)
            for cb, k_ in ((self.cb_bold, "bold"), (self.cb_italic, "italic"), (self.cb_axes, "axes_frame"),
                           (self.cb_struct, "struct_frame")):
                if cb is not None:
                    cb.setChecked(bool(tf[k_]))
            if self.btn_color is not None:
                b = self.btn_color
                b.setProperty("color", tf["color"])
                b.setStyleSheet(f"{b.property('cellcss') or ''}background-color: {tf['color']}; border: 1px solid #777;")
        finally:
            self._loading = False
        if self.fold is not None:
            self.fold.refresh()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.load()                                       # ein anderer Tab kann den Standard inzwischen geändert haben

    def _set(self, key, value):
        if self._loading:
            return
        if key == "greek" and self.cmb_sym is not None:
            self.cmb_sym.setEnabled(bool(value))
        self._pending[key] = value
        self.timer.start()

    def flush(self):
        """Gesammelte Änderungen übernehmen (Selbsttest ruft das direkt)."""
        self.timer.stop()
        changes, self._pending = self._pending, {}
        if changes:
            self.main.update_text_format(self.key if self.own() else None, changes)

    def _own_toggled(self, on):
        if self._loading:
            return
        self.flush()
        self.main.set_own_text_format(self.key, on)

    def restore_defaults(self):
        self._pending = {}
        self.timer.stop()
        self.main.update_text_format(self.key if self.own() else None, dict(core.TEXT_DEFAULTS))


# ---------------------------------------------------------------------------- Anleitung im leeren Tab
README_URL = "https://github.com/robinesken97/elucida/blob/main/"
MANUAL = {"de": "docs/manual.de.md", "en": "docs/manual.en.md"}
# Handbuch-Abschnitt je Tab (Deutsch, Englisch) – Überschriften wie in docs/manual.*.md (Selbsttest prüft das)
GUIDE_HEAD = {"compound": ("Verbindung", "Compound"), "syn": ("Synthese-Tab", "Synthesis tab"), "nmr": ("NMR-Tab", "NMR tab"),
              "irms": ("IR + EA-Tab", "IR + EA tab"), "hrms": ("HRMS-Tab", "HRMS tab"), "eps": ("UV-Vis-(ε)-Tab", "UV-Vis (ε) tab"),
              "overlay": ("UV-Vis-Overlay-Tab", "UV-Vis overlay tab"), "fluo": ("Fluoreszenz-Tab", "Fluorescence tab"),
              "uvkin": ("UV-Vis-Kinetik-Tab", "UV-Vis kinetics tab"),
              "cv": ("CV-Tab (Cyclovoltammetrie)", "CV tab (cyclic voltammetry)"),
              "sec": ("SEC-Tab (Spektroelektrochemie)", "SEC tab (spectroelectrochemistry)"),
              "hcell": ("H-Cell-Tab (Laden und Entladen)", "H-Cell tab (charge–discharge cycling)"),
              "epr": ("EPR-Tab (CW-EPR)", "EPR tab (CW EPR)"), "xray": ("X-Ray-Tab", "X-Ray tab"),
              "dft": ("DFT-Tab", "DFT tab"), "other": ("Weitere-Tab", "Other tab")}


def gh_anchor(heading):
    """Anker einer Markdown-Überschrift wie bei GitHub: klein, Satzzeichen weg, Leerzeichen -> „-“."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def guide_url(key):
    de = get_lang() == "de"
    return README_URL + MANUAL["de" if de else "en"] + "#" + gh_anchor(GUIDE_HEAD[key][0 if de else 1])


def guide_html(key):
    """Anleitung für einen leeren Tab: was herauskommt, welche Dateien, Schritte, Link zur README."""
    # Schritte als Tabelle: Nummer bündig mit Titel und Link, umbrochener Text bündig mit seiner ersten Zeile
    steps = "".join(f"<tr><td style='padding:0 6px 4px 0'>{i}.</td><td style='padding:0 0 4px 0'>{STYLE.sci(s)}</td></tr>"
                    for i, s in enumerate(T(f"guide_{key}_steps").split("\n"), 1))
    body = (f"<p style='font-size:15px'><b>{STYLE.sci(T(f'guide_{key}_title'))}</b></p>"
            f"<p style='color:gray'>{STYLE.sci(T(f'guide_{key}_files'))}</p>"
            f"<table cellspacing='0' cellpadding='0' style='margin-top:8px'>{steps}</table>"
            f"<p><a href='{guide_url(key)}'>{html.escape(T('guide_more'))}</a></p>")
    return body


_BIG = ()          # Felder, die auf Ergebnisseiten mit der Höhe wachsen (gesetzt beim ersten Aufruf)


def _buttons_of(w):
    """Knopf -> [Knopf]; Container, der nur Knöpfe enthält -> diese Knöpfe; sonst None."""
    if isinstance(w, QPushButton):
        return [w]
    lay = w.layout() if w is not None else None
    if lay is None:
        return None
    ws = [STYLE.item_at(lay, j).widget() for j in range(lay.count()) if STYLE.item_at(lay, j).widget() is not None]
    return ws if ws and all(isinstance(x, QPushButton) for x in ws) else None


PAGE_INSET = (14, 0, 14, 14)        # rechte Seite: Rand um Abbildung, Anleitung und Ergebniskarten (Entwurf; oben 12 an der Seite)
PAGE_TOP = 12


def page_wrap(widget):
    """Seite der rechten Spalte mit den Rändern des Entwurfs (Anleitung, eigene Vorschau)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*PAGE_INSET)
    lay.addWidget(widget)
    return w


def result_tabs():
    """Reiter neben der Abbildung, in allen Tabs gleich (Abbildung | Ergebnisse | ...). Stil: QTabWidget#resultTabs."""
    tabs = QTabWidget(objectName="resultTabs")
    tabs.setDocumentMode(True)
    tabs.tabBar().setDrawBase(False)                         # sonst Linie über der Reiterzeile, sobald Kacheln daneben stehen
    return tabs


def kpi_corner(tabs):
    """Ergebnis auf einen Blick (Entwurf 2026-11): bis zu zwei Kacheln rechts in der Reiterzeile. Gibt das Widget
    zurück; `box.show_items([(Bezeichnung, Wert), …])` setzt den Inhalt, `box.labels` sind die Kacheln."""
    class _Box(QWidget):
        def minimumSizeHint(self):                           # Kacheln machen das Fenster nie breiter
            return QSize(0, super().minimumSizeHint().height())

    box = _Box()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 3, PAGE_INSET[2], 15)          # auf Höhe der Reiter (Reiter: 3 oben, 26 hoch, 13 unten + Rand)
    lay.setSpacing(8)
    box.labels = []

    def show_items(items):
        items = list(items)[:2]
        while len(box.labels) < len(items):
            lb = QLabel(objectName="kpi")
            lb.setTextFormat(Qt.RichText)
            lay.addWidget(lb)
            box.labels.append(lb)
        col = STYLE.colors()["text"]
        for i, lb in enumerate(box.labels):
            if i < len(items):
                a, b = items[i]
                lb.setText(f"{STYLE.sci(a)} <span style='color:{col}; font-weight:600'>{STYLE.sci(b)}</span>"
                           if b not in ("", None) else STYLE.sci(a))
            lb.setVisible(i < len(items))
    class _Fit(QObject):                                     # schmales Fenster: Reiter gehen vor, Kacheln entfallen
        def eventFilter(self, obj, ev):
            if ev.type() in (QEvent.Resize, QEvent.Show):
                fit()
            return False

    def fit():
        need = tabs.tabBar().sizeHint().width() + sum(lb.sizeHint().width() + 8 for lb in box.labels
                                                       if not lb.isHidden()) + 2 * PAGE_INSET[2]
        box.setMaximumWidth(16777215 if tabs.width() >= need else 0)

    def show_fit(items):
        show_items(items)
        fit()
    box.show_items = show_fit
    box._fit = _Fit(box)
    tabs.installEventFilter(box._fit)
    tabs.setCornerWidget(box, Qt.TopRightCorner)
    return box


def _natural(button):
    """Knopf der Ergebnisseite: natürliche Breite, rechts (tidy hatte ihn in der linken Spalte gedehnt)."""
    from PySide6.QtWidgets import QSizePolicy
    button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    button.setMinimumWidth(0)
    button.setMaximumWidth(16777215)


# ---------------------------------------------------------------------------- Rahmen eines Tabs (Entwurf 2026-11)
# Links, was man einstellt, in Schritten statt als Kartenstapel; rechts, was herauskommt. Fußleisten beider Seiten gleich
# hoch: links Zurücksetzen/Vorlagen/Weiter, rechts Bildunterschrift und der Hauptknopf.
STEP_LABELS = ("step_data", "step_eval", "step_display")
# Karten nach ihrem deutschen Titel; alles Übrige (Dateilisten, gewählter Eintrag, Verbindung) gehört zu Schritt 1
STEP_TITLES = {
    1: ("Rechenweg", "Auswertung", "Verarbeitung", "Referenzierung", "Diffusionskoeffizient", "Simulationen",
        "Intensität und Kinetik", "Normierung",
        "Elementaranalyse", "Ausgewählte Parameter", "Messen (Abstand, Winkel, Diederwinkel)",
        "NMR-Zeile (MNova-Multiplettbericht)", "Reagenzien (Mengen berechnen)", "Verbinder"),
    2: ("Darstellung", "Weitere Darstellung", "Bildunterschrift (SI-Export)", "Achsen, Größe und Formate",
        "Größe und Formate", "Stapeln und Achsen", "Hervorheben und Labels", "Bilder", "Atome und Fragmente",
        "Ausrichten", "Atomfarben", "Spektrum", "Stil des Diagramms", "Größe", "Schrift und Rahmen"),
}
BAR_MIN_H = STYLE.BAR_H + 21          # Fußleiste: Knopf + 2 × 10 Rand + Linie, auch wenn links kein Knopf steht


def _card_title(w):
    """Titel einer Karte der linken Spalte ohne Klapp-Zeichen und „(geändert)“."""
    if isinstance(w, QGroupBox):
        f = next((c for c in w.children() if isinstance(c, STYLE.Fold)), None)
        return f.base if f is not None else w.title()
    t = w.findChild(QLabel, "cardTitle")
    return t.text() if t is not None else ""


class StepButton(QPushButton):
    """Schritt der linken Spalte: Nummer im Kreis, Name, Punkt = dort weicht etwas vom Standard ab."""

    def __init__(self, no, label):
        super().__init__(objectName="segBtn", checkable=True)
        self.no, self.label, self.changed = no, label, False
        self.setAccessibleName(label)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        s = super().sizeHint()
        s.setWidth(self.fontMetrics().horizontalAdvance(self.label) + 18 + 7 + 13 + 20)
        return s

    def paintEvent(self, ev):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QFont, QPainter, QPen
        from PySide6.QtWidgets import QStyle, QStyleOptionButton, QStylePainter
        p = QStylePainter(self)
        o = QStyleOptionButton()
        self.initStyleOption(o)
        o.text = ""
        p.drawControl(QStyle.CE_PushButton, o)               # Fläche wie die anderen Segmentknöpfe
        c, on = STYLE.colors(), self.isChecked()
        f = QFont(self.font())
        f.setWeight(QFont.DemiBold if on else QFont.Medium)
        p.setFont(f)
        tw = p.fontMetrics().horizontalAdvance(self.label)
        x, cy = (self.width() - (18 + 7 + tw)) / 2, self.height() / 2      # Punkt zählt nicht mit: Text bleibt mittig
        p.setRenderHint(QPainter.Antialiasing)
        circle = QRectF(x, cy - 9, 18, 18)
        if on:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(c["accent"]))
        else:
            p.setPen(QPen(QColor(c["border_strong"]), 1))
            p.setBrush(Qt.NoBrush)
        p.drawEllipse(circle.adjusted(0.5, 0.5, -0.5, -0.5))
        nf = QFont(f)
        nf.setPixelSize(11)
        nf.setWeight(QFont.DemiBold)
        p.setFont(nf)
        p.setPen(QColor(c["on_accent"] if on else c["text2"]))
        p.drawText(circle, Qt.AlignCenter, str(self.no))
        p.setFont(f)
        p.setPen(QColor(c["text"] if on or self.underMouse() else c["text2"]))
        p.drawText(QRectF(x + 25, 0, tw + 2, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.label)
        if self.changed:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#E5AC62" if STYLE._mode == "dark" else "#9A5C0B"))
            p.drawEllipse(QRectF(x + 25 + tw + 7, cy - 3, 6, 6))


class StepColumn(QObject):
    """Linke Spalte in Schritten: verteilt die Karten von `content` (QVBoxLayout) nach STEP_TITLES auf bis zu drei
    Seiten und setzt die Schrittleiste fest über die Spalte (`column` = Layout aus Spalte und Fußleiste). Die Karten
    bleiben dieselben Objekte; ein Schritt ohne Karten entfällt. Die Leiste steht auch bei nur einem Schritt: Karten
    links und die Seite rechts beginnen in jedem Tab auf derselben Höhe."""

    def __init__(self, content, column, labels=STEP_LABELS, changed=None, settings=None, name="", next_button=None):
        super().__init__(content)
        from PySide6.QtWidgets import QButtonGroup
        from elucida.app.i18n import TEXTS
        i = 1 if get_lang() == "en" else 0
        titles = {n: {pair[i] for pair in TEXTS.values() if pair[0] in names} for n, names in STEP_TITLES.items()}
        lay = content.layout()
        widgets = [x for x in (STYLE.item_at(lay, i).widget() for i in range(lay.count())) if x is not None]
        for w in widgets:
            # removeWidget löscht das alte Layout-Element; nach takeAt lebte es weiter, die Karte meldete Größenänderungen
            # dorthin statt an das neue Element und die Seite rechnete mit veralteten Höhen (Karten zusammengedrückt)
            lay.removeWidget(w)
        while lay.count():
            lay.takeAt(0)
        groups, pending, tail = [[], [], []], [], []
        for w in widgets:
            if isinstance(w, QLabel) and w.objectName() == "cardHint":
                pending.append(w)                            # „erst einen Eintrag wählen“: gehört zur Karte danach
            elif isinstance(w, QLabel):
                tail.append(w)                               # allgemeiner Hinweis: ans Ende des letzten Schritts
            else:
                t = _card_title(w)
                n = 2 if t in titles[2] else 1 if t in titles[1] else 0
                groups[n] += pending + [w]
                pending = []
        used = [n for n in range(3) if groups[n]] or [0]
        groups[used[-1]] += pending + tail
        self.content, self.changed, self.settings, self.name, self.next_button = content, changed, settings, name, next_button
        self.pages, self.buttons, self.bar, self.step = [], [], None, 0
        for n in used:
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 0, 0, 0)
            pl.setSpacing(10)
            for w in groups[n]:
                pl.addWidget(w)
            lay.addWidget(page)
            self.pages.append(page)
            if n == 2:
                self.display_page = page
        lay.addStretch(1)
        if used:
            seg = QFrame(objectName="seg")
            h = QHBoxLayout(seg)
            h.setContentsMargins(2, 2, 2, 2)
            h.setSpacing(0)
            grp = QButtonGroup(seg)
            for k, n in enumerate(used):
                b = StepButton(k + 1, T(labels[n]))
                grp.addButton(b, k)
                h.addWidget(b, 1)
                self.buttons.append(b)
            grp.idClicked.connect(self.set_step)
            self.bar = QWidget()
            r = QHBoxLayout(self.bar)
            r.setContentsMargins(STYLE.COL_PAD, PAGE_TOP, STYLE.COL_PAD, 0)
            r.addWidget(seg)
            column.insertWidget(0, self.bar)
            m = lay.contentsMargins()
            lay.setContentsMargins(m.left(), 10, m.right(), m.bottom())     # Abstand Leiste – erste Karte wie zwischen Karten
        if next_button is not None:
            next_button.clicked.connect(lambda: self.set_step(self.step + 1))
        start = 0
        if settings is not None and name:
            try:
                start = int(settings.value(f"step/{name}", 0))
            except (TypeError, ValueError):
                start = 0
        self.set_step(start, remember=False)

    def set_step(self, k, remember=True):
        k = max(0, min(int(k), len(self.pages) - 1))
        self.step = k
        page = getattr(self, "display_page", None)           # Schritt Darstellung: die Chips schalten Dinge im Bild
        for chips in page.findChildren(STYLE.ChipRow) if page is not None else ():
            form = next((fl for fl in page.findChildren(QFormLayout) if fl.indexOf(chips) >= 0), None)
            lab = form.labelForField(chips) if form is not None else None
            if isinstance(lab, QLabel) and lab.text() == T("chips_options"):
                lab.setText(T("chips_figure"))
        for i, page in enumerate(self.pages):
            page.setVisible(i == k)
        for i, b in enumerate(self.buttons):
            b.setChecked(i == k)
        if self.next_button is not None:
            more = k < len(self.pages) - 1
            self.next_button.setVisible(more)
            if more:
                self.next_button.setText(T("step_next", s=self.buttons[k + 1].label))
        if remember and self.settings is not None and self.name:
            self.settings.setValue(f"step/{self.name}", k)
        area = self.content.parentWidget().parentWidget() if self.content.parentWidget() is not None else None
        if remember and isinstance(area, QScrollArea):
            area.verticalScrollBar().setValue(0)

    def reveal(self, widget):
        """Den Schritt zeigen, in dem `widget` liegt (z. B. vor dem Fokussieren eines Felds)."""
        for i, page in enumerate(self.pages):
            if page.isAncestorOf(widget):
                self.set_step(i)
                return

    def refresh(self):
        """Punkt an den Schritten, in denen etwas vom Standard abweicht."""
        for page, b in zip(self.pages, self.buttons):
            on = bool(self.changed is not None and self.changed(page))
            if on != b.changed:
                b.changed = on
                b.setToolTip(T("step_changed_tip") if on else "")
                b.update()


class RowDrag(QObject):
    """Zeilen einer Liste mit der Maus umsortieren (Nutzerwunsch): Loslassen ruft `move_row(von, nach)` des Tabs.
    Qt verschiebt selbst nichts (Zellen mit Knöpfen und Auswahllisten gingen dabei verloren); die Liste baut der Tab
    wie bei den Pfeilknöpfen neu auf. Dateien aus dem Dateimanager gehen weiter an das Fenster."""
    MIME = "application/x-qabstractitemmodeldatalist"

    def __init__(self, view, move_row):
        super().__init__(view)
        self.view, self.move_row = view, move_row
        view.setDragDropMode(QAbstractItemView.InternalMove)
        view.setDragDropOverwriteMode(False)
        view.setDropIndicatorShown(True)
        view.viewport().installEventFilter(self)

    def target(self, pos):
        """Zeile, vor der losgelassen wurde (untere Hälfte einer Zeile = dahinter, unter der Liste = ans Ende)."""
        idx = self.view.indexAt(pos)
        if not idx.isValid():
            return self.view.model().rowCount()
        return idx.row() + (pos.y() > self.view.visualRect(idx).center().y())

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Drop and ev.source() in (None, self.view) and ev.mimeData().hasFormat(self.MIME):
            src, dst = self.view.currentIndex().row(), self.target(ev.position().toPoint())
            ev.setDropAction(Qt.IgnoreAction)              # sonst löscht Qt die gezogene Zeile
            ev.accept()
            dst -= dst > src                               # Ziel zählt ohne die gezogene Zeile
            if src >= 0 and dst != src:
                QTimer.singleShot(0, lambda: self.move_row(src, dst))   # erst nach dem Ende des Ziehens neu aufbauen
            return True
        return False


def move_item(items, src, dst):
    """Eintrag einer Liste von `src` nach `dst` setzen; False, wenn nichts zu tun ist."""
    if not (0 <= src < len(items) and 0 <= dst < len(items)) or src == dst:
        return False
    items.insert(dst, items.pop(src))
    return True


class CaptionLabel(QLabel):
    """Bildunterschrift in der Fußleiste: eine Zeile, am Ende gekürzt, ganz im Tooltip."""

    def __init__(self):
        super().__init__(objectName="recentSub")
        self._full = ""
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)

    def set_full(self, text):
        from elucida.si import lines as SI
        text = SI.chem_plain(text)                           # CH₂Cl₂ auch in der Fußleiste (reiner Text)
        self._full = text
        self.setToolTip(text)
        self.setText(self.fontMetrics().elidedText(text, Qt.ElideRight, max(10, self.width())))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.setText(self.fontMetrics().elidedText(self._full, Qt.ElideRight, max(10, self.width())))


def side_bar(*widgets, stretch_at=None):
    """Fußleiste einer Seite (links oder rechts), beide gleich hoch. stretch_at: Index, vor dem der Freiraum liegt."""
    row = QHBoxLayout()
    row.setContentsMargins(14, 10, 14, 10)
    row.setSpacing(8)
    for i, w in enumerate(widgets):
        if i == stretch_at:
            row.addStretch(1)
        row.addWidget(w, 1 if isinstance(w, CaptionLabel) else 0)
    if stretch_at is not None and stretch_at >= len(widgets):
        row.addStretch(1)
    bar = QFrame(objectName="bottomBar")
    bar.setLayout(row)
    bar.setMinimumHeight(BAR_MIN_H)
    return bar


def next_step_button():
    b = QPushButton(objectName="ghost")
    b.hide()
    return b


def result_page(group):
    """Ergebnisse als Reiter neben „Abbildung“, in allen Tabs gleich: Karte füllt die Seite, Tabellen/Texte wachsen
    mit der Höhe (statt fester kleiner Kästen), reine Knopfreihen stehen rechts unten, der erste Knopf der letzten
    Reihe ist der Hauptknopf (blau wie „Exportieren“). -> QScrollArea für addTab."""
    from PySide6.QtWidgets import QSizePolicy, QTextBrowser, QTextEdit
    big = (QTextBrowser, QTextEdit, QPlainTextEdit, QTableWidget, QListWidget)
    group.setParent(None)
    group.setTitle("")
    group.setObjectName("resultCard")
    v = group.layout()
    v.setContentsMargins(12, 12, 12, 12)                     # mit Padding 4 + Rahmen: ringsum 17
    v.setSpacing(10)
    actions = []
    for idx in range(v.count()):
        it = STYLE.item_at(v, idx)
        w, lay = it.widget(), it.layout()
        if isinstance(w, big):
            w.setMaximumHeight(16777215)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            v.setStretch(idx, 1)
            if isinstance(w, QTableWidget):                  # Tabelle füllt die Karte: Spalten gleich verteilt, wenn
                hh = w.horizontalHeader()                    # der Tab keine dehnbare Spalte festgelegt hat
                if not hh.stretchLastSection() and not any(hh.sectionResizeMode(c) == hh.ResizeMode.Stretch
                                                           for c in range(w.columnCount())):
                    hh.setSectionResizeMode(hh.ResizeMode.Stretch)
        elif isinstance(w, QPushButton):                     # einzelner Knopf über die volle Breite -> rechts
            v.removeWidget(w)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(w)
            _natural(w)
            v.insertLayout(idx, row)
            actions.append(row)
        elif isinstance(lay, QHBoxLayout):
            items = [STYLE.item_at(lay, j) for j in range(lay.count())]
            parts = [_buttons_of(i.widget()) for i in items if i.widget() is not None]
            if parts and all(p is not None for p in parts):  # nur Knöpfe (auch in Containern wie methods_button)
                while lay.count():
                    STYLE.drop_taken(lay.takeAt(0))
                lay.addStretch(1)
                for x in (b for p in parts for b in p):
                    lay.addWidget(x)
                    _natural(x)
                actions.append(lay)
    if actions:
        last = actions[-1]
        b = next(STYLE.item_at(last, j).widget() for j in range(last.count()) if STYLE.item_at(last, j).widget() is not None)
        if b.icon().isNull():                       # blau bleibt „Exportieren“ (ein Hauptknopf je Ansicht)
            b.setIcon(STYLE.icon("copy"))
    page = QWidget()
    pv = QVBoxLayout(page)
    pv.setContentsMargins(*PAGE_INSET)
    if group.property("hug"):                                # kurzer Text (Bildunterschrift): Karte so hoch wie ihr Inhalt
        pv.addWidget(group)
        pv.addStretch(1)
    else:
        pv.addWidget(group, 1)
    sa = QScrollArea()
    sa.setWidget(page)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    group.show()
    return sa


def footer(tab, left_scroll):
    """Linke Spalte mit Fußleiste wie in den anderen Tabs (Synthese, NMR). Der Hauptknopf „Exportieren“ (hier:
    Word-Datei ins Projekt) entsteht hier als tab.btn_export und gehört in die Fußleiste rechts: `side_bar(tab.btn_export,
    stretch_at=0)` unter die Vorschau."""
    from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
    b = QPushButton(STYLE.icon("export", "#FFFFFF"), T("btn_export"))
    b.setProperty("accent", True)
    b.setToolTip(T("btn_export_word_tip"))
    b.clicked.connect(lambda: _export_word(tab))
    tab.btn_next = next_step_button()
    bar = side_bar(tab.btn_next, stretch_at=0)
    col = QWidget()
    v = QVBoxLayout(col)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    v.addWidget(left_scroll, 1)
    v.addWidget(bar)
    tab.btn_export = b
    tab._footer_parts = (left_scroll, bar, col)
    return col


def fit_footer_column(tab, split):
    """Spaltenbreite für Synthese/NMR wie in den anderen Tabs automatisch (STYLE.ColumnFit)."""
    ls, bar, col = tab._footer_parts
    ls.setMinimumWidth(0)
    STYLE.tidy(ls.widget())                               # Ränder der Spalte zuerst: die Schrittleiste setzt den oberen neu
    tab.steps = StepColumn(ls.widget(), col.layout(), getattr(tab, "STEP_LABELS", STEP_LABELS),
                           settings=tab.main.settings, name=type(tab).__name__, next_button=tab.btn_next)
    tab.column_fit = STYLE.fit_column(ls.widget(), ls, bar, col, split)


def _export_word(tab):
    path = tab.export_dialog()
    if path:
        tab.main.exported([Path(path).parent])


class EmptyGuide(QFrame):
    """Leerer Vorschaubereich mit Anleitung (guide_html) und optional einem Knopf für den ersten Schritt."""

    def __init__(self, key, action=None, extra=None, export=None):
        super().__init__(objectName="emptyDrop")
        self.btn = None
        self.export = export                                # ohne Daten ist der Knopf der Anleitung der Hauptknopf
        self.setStyleSheet("#emptyDrop { border: 1px solid palette(midlight); border-radius: 12px; }")
        QTimer.singleShot(0, self, self._attach)
        v = QVBoxLayout(self)
        v.addStretch(1)
        self.label = QLabel(guide_html(key), wordWrap=True)
        self.label.setTextFormat(Qt.RichText)
        self.label.setOpenExternalLinks(True)
        self.label.setMinimumWidth(280)
        self.label.setMaximumWidth(560)
        # ohne Ausrichtungs-Flag einfügen (sonst rechnet Qt die Höhe des umbrochenen Texts falsch und schneidet ab),
        # zentriert über gleiche Dehnfelder links und rechts; Breite = längste Zeile (fit_width), sonst sitzt der
        # linksbündige Text links in einem zu breiten Feld
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.label, 100)
        row.addStretch(1)
        v.addLayout(row)
        if action is not None:
            b = QPushButton(STYLE.icon("open", "#FFFFFF"), action[0])
            b.setProperty("accent", True)
            b.clicked.connect(action[1])
            v.addSpacing(6)
            v.addWidget(b, 0, Qt.AlignHCenter)
            self.btn = b
        if extra is not None:
            v.addWidget(extra, 0, Qt.AlignHCenter)
        v.addStretch(1)                                     # Block genau in der Mitte der Fläche

    def fit_width(self):
        """Feld so breit wie die längste Zeile (höchstens 560 px) – mit der Schrift nach dem Stylesheet."""
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self.label.font())
        doc.setDocumentMargin(0)
        doc.setHtml(self.label.text())
        doc.setTextWidth(560)
        self.label.setMaximumWidth(max(280, min(560, int(doc.idealWidth()) + 6)))

    def showEvent(self, ev):
        self.fit_width()
        super().showEvent(ev)

    def _attach(self):
        """Blau folgt der sichtbaren Seite, auch wenn sie wechselt, während der Tab verborgen ist."""
        w = self
        while w is not None and not isinstance(w.parentWidget(), QStackedWidget):
            w = w.parentWidget()
        if w is None or self.export is None:
            return
        self._page, self._stack = w, w.parentWidget()
        self._stack.currentChanged.connect(self._sync_export)
        self._sync_export()

    def _sync_export(self, *_):
        b = getattr(self.export, "btn_export", self.export)      # Knopf oder Tab, dessen Fußleiste erst später entsteht
        if b is not None:
            STYLE.set_accent(b, self._stack.currentWidget() is not self._page, "export")


class CanvasHost(QWidget):
    """Fläche für die Vorschau: skaliert die Abbildung auf den verfügbaren Platz.
    Nur die Anzeige-dpi ändert sich – Positionen (Anteile) und Schriftgrößen (pt) bleiben, die
    Vorschau ist also weiterhin maßstabsgetreu zum Export."""

    def __init__(self, canvas, fig, margin=12, page=False):
        super().__init__()
        self.canvas, self.fig, self.margin = canvas, fig, margin
        # page: Abbildung eines Tabs – Karte mit den Rändern der rechten Seite, Innenrand 10 (Entwurf); sonst wie bisher
        self.card = PAGE_INSET if page else (4, 2, 8, 8)
        pad = 10 if page else 0
        self.inset = tuple(x + pad for x in self.card) if page else (margin,) * 4
        self.fit_timer = QTimer(self, singleShot=True, interval=0)
        self.fit_timer.timeout.connect(self.fit)
        self.fig_in = (8.0, 6.0)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(*(self.inset if page else (0, 0, 0, 0)))
        lay.addWidget(canvas, 0, Qt.AlignCenter)
        self.setMinimumSize(200, 150)
        # Abbildungen setzen beim Neuaufbau ihre Nenngröße (fig.set_size_inches); der Puffer wird dann eine Pixelzeile
        # kürzer als die Fläche, sobald deren Höhe aufgerundet wurde. Die unbedeckte Zeile zeigte die Hintergrundfarbe
        # des Designs – im dunklen Canvas eine helle Linie am unteren Rand, die beim Drehen flackerte. Deshalb vor
        # jedem Zeichnen angleichen.
        draw = canvas.draw

        def matched(*a, **k):
            self.match_buffer()
            return draw(*a, **k)
        canvas.draw = matched

    def set_figure_size(self, w_in, h_in):
        self.fig_in = (float(w_in), float(h_in))
        self.fit()

    def fit(self):
        w_in, h_in = self.fig_in
        aw = max(100, self.width() - self.inset[0] - self.inset[2])
        ah = max(80, self.height() - self.inset[1] - self.inset[3])
        dpi = max(30.0, min(aw / w_in, ah / h_in))
        ratio = getattr(self.canvas, "device_pixel_ratio", 1) or 1
        self.fig._original_dpi = dpi                       # Basis für HiDPI-Skalierung durch matplotlib
        self.fig._set_dpi(dpi * ratio, forward=False)
        width, height = int(round(w_in * dpi)), int(round(h_in * dpi))
        self.canvas.setFixedSize(width, height)
        self.match_buffer()
        self.canvas.draw_idle()

    def match_buffer(self):
        """Qt paints integer widget pixels; Agg truncates its floating dimensions. Match that buffer exactly, otherwise
        copy_from_bbox reads beyond its last column/row (strip of uninitialised pixels) or leaves one uncovered."""
        ratio = getattr(self.canvas, "device_pixel_ratio", 1) or 1
        dpi = self.fig.dpi
        self.fig.set_size_inches((math.ceil(self.canvas.width() * ratio) + 1e-7) / dpi,   # ceil: 125/150 % Skalierung
                                 (math.ceil(self.canvas.height() * ratio) + 1e-7) / dpi, forward=False)

    def paintEvent(self, ev):
        """Karte in Canvas-Farbe um die Vorschau: die Abbildung füllt sie optisch (nur Anzeige, nie im Export)."""
        if not self.margin:
            return
        from PySide6.QtGui import QColor, QPainter, QPen
        from elucida.app import canvas_theme as CANVAS
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(STYLE.colors()["border"]), 1))
        p.setBrush(QColor("#000000" if CANVAS._dark else "#ffffff"))
        l_, t_, r_, b_ = self.card
        p.drawRoundedRect(self.rect().adjusted(l_, t_, -r_, -b_), 12, 12)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.fit_timer.start()

    def showEvent(self, ev):
        """Wieder sichtbar (Reiter „Abbildung“, Anleitung -> Abbildung): Größe kann sich verborgen geändert haben."""
        super().showEvent(ev)
        self.fit_timer.start()


class TabDragger(core.Dragger):
    def __init__(self, F, cb):
        self.cb = cb
        super().__init__(F, None)

    def _report(self, lay0):
        QTimer.singleShot(0, lambda: self.cb(self.moved(lay0)))

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


class HoverReadout:
    """Maus über den Spektren: nächsten Messpunkt markieren und λ/Wert melden (on_text).
    curves: [dict(x, y, val, name)] – x/y wie gezeichnet (Datenkoordinaten von F.ax), val = angezeigter
    Wert (z. B. ohne Stapelversatz). Doppelklick auf einen Punkt -> on_pick(λ).
    Der Marker ist 'animated' (nur per Blitting gezeichnet) und erscheint daher nie im Export."""

    TOL_PX = 12

    def __init__(self, F, curves, on_text, fmt, on_pick=None):
        self.F, self.curves, self.on_text, self.fmt, self.on_pick = F, curves, on_text, fmt, on_pick
        self.bg, self.hit, self.shown = None, None, False
        self.marker, = F.ax.plot([], [], "o", ms=7, mfc="none", mec="#d9534f", mew=1.5,
                                 animated=True, zorder=10, clip_on=False)
        c = F.fig.canvas
        self.cids = [c.mpl_connect("draw_event", self._on_draw),
                     c.mpl_connect("motion_notify_event", self.move),
                     c.mpl_connect("figure_leave_event", self.leave),
                     c.mpl_connect("button_press_event", self.press)]

    def disconnect(self):
        for cid in self.cids:
            self.F.fig.canvas.mpl_disconnect(cid)
        self.on_text("")

    def _on_draw(self, _ev):
        self.bg = self.F.fig.canvas.copy_from_bbox(self.F.fig.bbox)

    def _blocked(self, ev):
        """Über Inset/Bild/Label/Legende oder beim Ziehen: kein Hover (die gehören dem Dragger)."""
        if ev.button is not None:
            return True
        if any(a.get_window_extent().contains(ev.x, ev.y) for a in self.F.axes_items.values()):
            return True
        leg = getattr(self.F, "legend", None)
        if leg is not None and leg.contains(ev)[0]:
            return True
        return any(a.contains(ev)[0] for a in self.F.ann_items.values())

    def nearest(self, px, py):
        """Nächster Messpunkt zum Pixel (px, py) -> (Kurve, Index) oder None."""
        ax = self.F.ax
        xd = ax.transData.inverted().transform((px, py))[0]
        best, bd = None, self.TOL_PX * self.F.fig.dpi / 72
        for c in self.curves:
            x = np.asarray(c["x"], float)
            if not len(x):
                continue
            i = int(np.nanargmin(np.abs(x - xd)))
            if not np.isfinite(c["y"][i]):
                continue
            qx, qy = ax.transData.transform((x[i], c["y"][i]))
            d = np.hypot(qx - px, qy - py)
            if d < bd:
                best, bd = (c, i), d
        return best

    def move(self, ev):
        if ev.x is None or not self.F.ax.bbox.contains(ev.x, ev.y) or self._blocked(ev):
            return self.leave(ev)
        self.hit = self.nearest(ev.x, ev.y)
        if self.hit:
            c, i = self.hit
            self.marker.set_data([c["x"][i]], [c["y"][i]])
            self.on_text(self.fmt(float(c["x"][i]), float(c["val"][i]), c["name"]))
        else:
            self.on_text(self.fmt(float(self.F.ax.transData.inverted().transform((ev.x, ev.y))[0]), None, None))
        self.shown = True
        self._blit()

    def leave(self, _ev=None):
        if not self.shown:
            return
        self.hit, self.shown = None, False
        self.on_text("")
        self._blit()

    def _blit(self):
        canvas = self.F.fig.canvas
        if self.bg is None:
            return
        canvas.restore_region(self.bg)
        if self.hit:
            self.F.ax.draw_artist(self.marker)
        canvas.blit(self.F.fig.bbox)

    def press(self, ev):
        # Ziehen von Inset/Bild/Label beginnt: der gemerkte Hintergrund ist ohne das gezogene Element entstanden ->
        # erst nach dem nächsten vollständigen Zeichnen (draw_event, nach dem Loslassen) wieder blitten
        if ev.button == 1 and ev.x is not None and self._blocked_click(ev):
            self.bg = None
        if ev.dblclick and ev.button == 1 and self.on_pick and self.hit and not self._blocked_click(ev):
            c, i = self.hit
            self.on_pick(float(c["x"][i]))

    def _blocked_click(self, ev):
        return any(a.get_window_extent().contains(ev.x, ev.y) for a in self.F.axes_items.values()) \
            or any(a.contains(ev)[0] for a in self.F.ann_items.values())


# ----------------------------------------------------------------------------
SI_MAX_W_CM = 16.0                       # Abbildungen im SI-Export höchstens so breit wie der Satzspiegel


def si_image(F, svg):
    """Abbildung für den SI-Export: SVG (Vektor, Text als Pfade) + PNG-Ersatz -> ("image", PNG, b, h, SVG)."""
    from PIL import Image
    svg = Path(svg).resolve()
    F.cfg.update(output=str(svg), extra_formats=["png"], _base_dir=svg.parent, png_fast=True)
    F.export()
    png = svg.with_suffix(".png")
    with Image.open(png) as im:
        w_cm, h_cm = (v / F.cfg["dpi"] * 2.54 for v in im.size)
    if w_cm > SI_MAX_W_CM:
        w_cm, h_cm = SI_MAX_W_CM, h_cm * SI_MAX_W_CM / w_cm
    return ("image", str(png), w_cm, h_cm, str(svg))


class FigureTab(QWidget):
    """Gemeinsame Basis: Vorschau, Größe/Formate, Ziehen, Export, Speichern/Laden."""

    DEFAULT_STATE: dict = {}
    STATE_KEY = ""
    # was der Tab im Bild hat (Menü Format zeigt nur das): Schriften, Symbolschrift für λ/ε, Labels, Labelgröße, Rahmen
    TEXT_OPTS = ("fonts", "labels", "label_size", "axes_frame")
    X_RANGE = (100, 3500, 0, 10)         # x-Achse: min, max, Nachkommastellen, Schritt (Spektren: nm)
    GUIDE = ""                           # Schlüssel der Anleitung im leeren Tab (guide_<GUIDE>_…), "" = nur Text
    GUIDE_ACTION = None                  # (Textschlüssel, Methode) für den Knopf in der Anleitung
    GUIDE_EXTRA = None                   # Methode -> weiteres Widget in der Anleitung (Overlay: „Aus Tabs ▾“)
    MAIN_SI = False                      # True: Hauptknopf (blau) ist „SI (Word)“ in der Leiste, nicht „Exportieren“
    STEP_LABELS = STEP_LABELS            # Namen der Schritte der linken Spalte (i18n-Schlüssel), je Tab änderbar
    XRANGE_TEXT = "xrange"

    def __init__(self, main, state):
        super().__init__()
        self.main = main
        self.st = state
        for k, v in self.DEFAULT_STATE.items():
            self.st.setdefault(k, copy.deepcopy(v))
        self.F = None
        self.dragger = None
        self.hover = None
        self._loading = False
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.render)
        self.fig = MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        left = QWidget()
        self.lv = QVBoxLayout(left)
        self.build_controls()
        self.grp_common = self.common_box()
        self.lv.addWidget(self.grp_common)
        hint = QLabel(T(self.DRAG_HINT), alignment=Qt.AlignHCenter)      # Fußnote unter den Karten: mittig
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        hint.setContentsMargins(STYLE.CARD_PAD, 0, STYLE.CARD_PAD, 0)    # nicht breiter als der Karteninhalt
        self.lv.addWidget(hint)
        self.lv.addStretch(1)
        align_forms(left.findChildren(QFormLayout))
        self.folds, self._to_right = [], []
        self.arrange()                                   # einklappen / Zeilen gruppieren / Ergebnisse nach rechts
        self.tf_card = None
        # Schrift und Rahmen: letzte Karte im Schritt Darstellung (nicht im Reaktionspfad: dort gilt das Format des Projekts)
        if self.TEXT_OPTS and hasattr(main, "update_text_format"):
            c_ = self.tf_card = TextFormatCard(main, self.STATE_KEY, self.TEXT_OPTS)
            c_.box = QGroupBox(T("tf_title"))
            QVBoxLayout(c_.box).addWidget(c_)
            self.lv.insertWidget(self.lv.indexOf(self.grp_common) + 1, c_.box)
            c_.fold = STYLE.Fold(c_.box, f"{self.STATE_KEY}/text_format", main.settings, c_.differs)
            self.folds.append(c_.fold)
        self.chain_row = None
        if type(self).chain is not FigureTab.chain:      # Rechenweg: erste Karte im Schritt Auswertung
            g = QGroupBox(T("chain_title"))
            g.setToolTip(T("chain_tip"))
            self.chain_row = STYLE.ChainRow()
            QVBoxLayout(g).addWidget(self.chain_row)
            self.lv.insertWidget(0, g)
        cap = getattr(self, "grp_caption", None)         # Bildunterschrift steht rechts im Reiter „SI-Text“
        if cap is not None:
            self.lv.removeWidget(cap)
            cap.setParent(None)
        STYLE.tidy(left)
        det = getattr(self, "det", None)                 # Einstellungen des gewählten Eintrags: erst nach Auswahl
        if isinstance(det, QGroupBox):
            STYLE.hint_when_disabled(det, T("card_select_first", t=det.title()))
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Fußleisten bleiben sichtbar, auch wenn die Spalte gescrollt wird. Links: Zurücksetzen ▾ · Vorlagen ▾ … Weiter;
        # rechts unter der Abbildung: Bildunterschrift … Exportieren (Entwurf 2026-11)
        b_reset = reset_button(self.reset_layout, self.reset_defaults)
        b = QPushButton(T("tab_presets"))
        b.setToolTip(T("tab_presets_tip"))
        m = QMenu(b)
        for txt, fn, tip in ((T("tab_save"), self.save_setup, T("tab_save_tip")),
                             (T("tab_load"), self.load_setup, T("tab_load_tip"))):
            a = m.addAction(txt, fn)
            a.setToolTip(tip)
        m.setToolTipsVisible(True)
        b.setMenu(m)
        self.btn_presets = b
        self.btn_next = next_step_button()
        self.btn_export = QPushButton(STYLE.icon("export", "#FFFFFF"), T("btn_export"))
        self.btn_export.setProperty("accent", True)
        self.btn_export.setToolTip(T("btn_export_tip"))
        self.btn_export.setDefault(True)
        self.btn_export.clicked.connect(self.export_dialog)
        bar = side_bar(b_reset, self.btn_presets, self.btn_next, stretch_at=2)
        left_col = QWidget()
        cv = QVBoxLayout(left_col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(ls, 1)
        cv.addWidget(bar)
        self.steps = StepColumn(left, cv, self.STEP_LABELS, settings=self.main.settings, name=self.STATE_KEY,
                                next_button=self.btn_next,
                                changed=lambda page: any(f.changed is not None and f.changed() for f in self.folds
                                                         if page.isAncestorOf(f.group)))
        # so breit wie der Inhalt, sonst schneidet die Spalte rechts ab (macOS blendet die Leiste aus); nach dem ersten
        # Anzeigen neu bestimmt (fit_left), weil Qt vor dem Stylesheet andere (unter Windows größere) Breiten meldet
        self._left_parts = (left, bar, ls, left_col)
        left_col.setMinimumWidth(self._left_width())
        self.host = CanvasHost(self.canvas, self.fig, page=True)
        # Leer-Zustand: Anleitung (was herauskommt, welche Dateien, Schritte) statt einer weißen Abbildung
        act = getattr(self, self.GUIDE_ACTION[1], None) if self.GUIDE_ACTION else None
        extra = getattr(self, self.GUIDE_EXTRA)() if self.GUIDE_EXTRA else None
        if self.MAIN_SI:                                  # Hauptknopf dieses Tabs ist „SI (Word)“ in der Leiste
            STYLE.set_accent(self.btn_export, False, "export")
        empty = EmptyGuide(self.GUIDE, (T(self.GUIDE_ACTION[0]), act) if act else None, extra,
                           None if self.MAIN_SI else self.btn_export) if self.GUIDE else None
        if empty is None:
            empty = QLabel(T("tab_empty"), alignment=Qt.AlignCenter, wordWrap=True)
            empty.setStyleSheet(HINT_CSS + " font-size: 14px;")
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(page_wrap(empty))
        self.preview_stack.addWidget(self.host)
        self.empty_guide = empty if isinstance(empty, EmptyGuide) else None
        if self.MAIN_SI:
            self.preview_stack.currentChanged.connect(lambda *_: self.main.sync_main_button())
        # Hinweise beim Zeichnen (z. B. Kurve ausgelassen) hier im Tab, nicht nur im Protokoll
        self.lbl_note = QLabel(wordWrap=True)
        self.lbl_note.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_note.setContentsMargins(PAGE_INSET[0], 0, PAGE_INSET[2], 10)
        self.lbl_note.hide()
        self._notes = []
        right_col = QWidget()
        rv = QVBoxLayout(right_col)
        rv.setContentsMargins(0, PAGE_TOP, 0, 0)
        rv.setSpacing(0)
        # Reiterzeile in jedem Tab, auch nur mit „Abbildung“: Abbildung und Karten links beginnen auf derselben Höhe
        self.right_tabs = result_tabs()
        self.right_tabs.addTab(self.preview_stack, T("tab_figure"))
        rv.addWidget(self.right_tabs, 1)
        rv.addWidget(self.lbl_note)
        self.lbl_cap_bar = CaptionLabel()
        rv.addWidget(side_bar(self.lbl_cap_bar, self.btn_export))
        for g, title in self._to_right:                   # Ergebnisse als Reiter neben der Abbildung
            self.move_right(g, title)
        self._build_si_page()
        self.kpi_box = kpi_corner(self.right_tabs)        # Ergebnis auf einen Blick, rechts in der Reiterzeile
        self.right_tabs.currentChanged.connect(lambda *_: self.refresh_summary())
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left_col)
        split.addWidget(right_col)
        split.setSizes([left_col.minimumWidth(), 900])
        self._split = split
        self.column_fit = STYLE.fit_column(left, ls, bar, left_col, split)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self._render_pending = False
        self.sync_caption_bar()
        self.steps.refresh()
        QTimer.singleShot(0, self._first_render)

    def sync_caption_bar(self):
        """Bildunterschrift der SI in der Fußleiste unter der Abbildung (eine Zeile, ganz im Tooltip)."""
        name = (getattr(self.main, "compound", None) or {}).get("name") or "X"
        try:                                              # ohne Abbildung keine Unterschrift (HRMS zeigte eine zur Anleitung)
            text = re.sub(r"<[^>]+>", "", self.si_caption(name)) if getattr(self, "F", None) is not None else ""
        except Exception:
            text = ""
        self.lbl_cap_bar.set_full(f"{T('caption_bar')} · Figure Sn: {html.unescape(text)}" if text else "")

    def _first_render(self):
        """Erstes Zeichnen nach dem Aufbau: sofort, wenn der Tab zu sehen ist, sonst beim ersten Anzeigen (beim
        Öffnen eines Projekts sind elf von zwölf Tabs verborgen – das Zeichnen aller Abbildungen kostete ~1 s)."""
        if self.isVisible():
            self.render()
        else:
            self._render_pending = True

    def showEvent(self, ev):
        super().showEvent(ev)
        if getattr(self, "_render_pending", False):
            self._render_pending = False
            QTimer.singleShot(0, self.render)

    def ensure_rendered(self):
        """Abbildung jetzt zeichnen, falls sie wegen eines verborgenen Tabs noch aussteht (z. B. vor Zugriff auf F)."""
        if getattr(self, "_render_pending", False):
            self._render_pending = False
            self.render()

    def compound_changed(self):
        """Verbindung des Projekts geändert (MainWindow.set_compound ruft das in jedem gebauten Tab): Abbildung und
        Unterschrift neu, verborgen erst beim Anzeigen. Tabs mit Feldern aus der Verbindung ergänzen das."""
        if self.isVisible():
            self.timer.start()
        else:
            self._render_pending = True

    # -- Bausteine ------------------------------------------------------------
    def build_controls(self):
        raise NotImplementedError

    def common_box(self):
        g = QGroupBox(T("grp_export"))
        f = make_form(g)
        st = self.st
        row = QHBoxLayout()
        self.cb_xauto = QCheckBox(T("xrange_auto"))
        self.cb_xauto.setChecked(st["x_auto"])
        lo, hi, dec, step = self.X_RANGE
        self.sp_xmin = QDoubleSpinBox(decimals=dec, minimum=lo, maximum=hi, singleStep=step, value=st["x_min"])
        self.sp_xmax = QDoubleSpinBox(decimals=dec, minimum=lo, maximum=hi, singleStep=step, value=st["x_max"])
        for w in (self.cb_xauto, self.sp_xmin, QLabel("–"), self.sp_xmax):
            row.addWidget(w)
        f.addRow(T(self.XRANGE_TEXT), row)
        self.sp_ymax = QDoubleSpinBox(decimals=2, minimum=0, maximum=1e6, singleStep=0.1, value=st["ymax"])
        self.sp_ymax.setSpecialValueText(T("auto"))
        f.addRow(T("ymax"), self.sp_ymax)
        self.cmb_size = QComboBox()
        for key in ("half_a4", "custom", "std"):
            self.cmb_size.addItem(T({"half_a4": "size_half_a4", "custom": "size_custom", "std": "size_std"}[key]), key)
        self.cmb_size.setCurrentIndex(self.cmb_size.findData(st["size"]))
        f.addRow(T("size"), self.cmb_size)
        row = QHBoxLayout()
        self.sp_w = QDoubleSpinBox(decimals=1, minimum=4, maximum=40, singleStep=0.5, suffix=" cm", value=st["w_cm"])
        self.sp_h = QDoubleSpinBox(decimals=1, minimum=3, maximum=40, singleStep=0.5, suffix=" cm", value=st["h_cm"])
        row.addWidget(self.sp_w)
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_h)
        f.addRow(T("size_wh"), row)
        row = QHBoxLayout()
        self.cb_fmt = {}
        for e in ("pdf", "svg", "png"):
            cb = QCheckBox(e.upper())
            cb.setChecked(st["fmt"].get(e, True))
            self.cb_fmt[e] = cb
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("formats"), row)
        for w in (self.sp_xmin, self.sp_xmax, self.sp_ymax, self.sp_w, self.sp_h):
            w.valueChanged.connect(self.changed)
        self.cb_xauto.toggled.connect(self.changed)
        self.cmb_size.currentIndexChanged.connect(self.changed)
        for cb in self.cb_fmt.values():
            cb.toggled.connect(self.changed)
        self._sync_common()
        return g

    def size_spin(self, form, key, layout_key, lo=3.0, hi=90.0):
        """Größenfeld (% der Plotbreite) für ein Bild; Mausrad im Plot hält es aktuell."""
        sp = QDoubleSpinBox(decimals=1, minimum=lo, maximum=hi, singleStep=1, suffix=" %",
                            value=self.st.get(key, 20.0))
        self._size_spins = getattr(self, "_size_spins", {})
        self._size_spins[layout_key] = (sp, key)

        def changed(v):
            if self._loading:
                return
            self.st[key] = v
            lay = self.layout()
            if layout_key in lay and len(lay[layout_key]) == 4:
                x, y, w, h = lay[layout_key]
                nw = v / 100
                nh = h * nw / w
                lay[layout_key] = [min(max(x + (w - nw) / 2, 0), max(0, 1 - nw)),
                                   min(max(y + (h - nh) / 2, 0), max(0, 1 - nh)), nw, nh]
            self.timer.start()
        sp.valueChanged.connect(changed)
        form.addRow(T("img_size"), sp)
        return sp

    def sync_sizes(self, layout):
        for lk, (sp, key) in getattr(self, "_size_spins", {}).items():
            if lk in layout and len(layout[lk]) == 4:
                self.st[key] = round(layout[lk][2] * 100, 1)
                sp.blockSignals(True)
                sp.setValue(self.st[key])
                sp.blockSignals(False)

    def _sync_common(self):
        auto = self.cb_xauto.isChecked()
        self.sp_xmin.setEnabled(not auto)
        self.sp_xmax.setEnabled(not auto)
        if self.cmb_size.currentData() == "half_a4":
            for sp, v in ((self.sp_w, 16.0), (self.sp_h, 11.0)):
                sp.blockSignals(True)
                sp.setValue(v)
                sp.blockSignals(False)
        custom = self.cmb_size.currentData() == "custom"
        self.sp_w.setEnabled(custom)
        self.sp_h.setEnabled(custom)

    def collect_common(self):
        st = self.st
        st.update(x_auto=self.cb_xauto.isChecked(), x_min=self.sp_xmin.value(), x_max=self.sp_xmax.value(),
                  ymax=self.sp_ymax.value(), size=self.cmb_size.currentData(), w_cm=self.sp_w.value(),
                  h_cm=self.sp_h.value(), fmt={e: cb.isChecked() for e, cb in self.cb_fmt.items()})

    def changed(self, *_):
        if self._loading:
            return
        self.collect_common()
        self._sync_common()
        self.collect()
        self.timer.start()

    def collect(self):
        pass

    # -- Daten-Cache (im Hauptfenster, übersteht Sprachwechsel) ------------------
    def cache(self, key, fn):
        c = self.main.extra_cache
        if key not in c:
            c[key] = fn()
        return c[key]

    def samples(self, path):
        return self.cache(("samples", path), lambda: core.read_samples([path]))

    def sample(self, path, key):
        for s_ in self.samples(path):
            if s_["key"] == key:
                return s_
        return None

    def structure_asset(self, path, color=None):
        return self.cache(("struct", path, color), lambda: IMG.load_structure(path, color=color))

    def photo_asset(self, path, method):
        if method in ("auto", "isnet") and not self.main.ensure_model():
            method = "grabcut" if method == "isnet" else "auto"
        cdir = self.main.cache_dir(path)
        return self.cache(("photo", path, method), lambda: IMG.load_photo(path, method, cdir))

    # -- Abbildung ----------------------------------------------------------------
    def base_cfg(self):
        st = self.st
        cfg = core.deep_merge(core.DEFAULTS, {})
        cfg["_base_dir"] = Path.home()
        if st["size"] != "std":
            core.apply_export_size(cfg, st["w_cm"], st["h_cm"])
        core.apply_text_format(cfg, self.main.text_format(self.STATE_KEY))
        fmts = [e for e in ("pdf", "svg", "png") if st["fmt"].get(e)] or ["pdf"]
        cfg["_main_fmt"], cfg["extra_formats"] = fmts[0], fmts[1:]
        return cfg

    def size_key(self):
        return "std" if self.st["size"] == "std" else f"{self.st['w_cm']:g}x{self.st['h_cm']:g}"

    def layout(self):
        return self.st["layout"].setdefault(self.size_key(), {})

    def figure_spec(self):
        """-> (cfg, curves, labels, sticks) oder None."""
        raise NotImplementedError

    def build(self, fig):
        quiet = core.LOG
        core.LOG = IMG.LOG = lambda *a: None      # Basislinien-Meldungen nicht bei jedem Neuzeichnen
        try:
            spec = self.figure_spec()
        finally:
            core.LOG = IMG.LOG = quiet
        if spec is None:
            return None
        cfg, curves, labels, sticks = spec
        core.setup_fonts(plt, cfg)
        return X.SimpleFigure(plt, cfg, curves, labels, self.layout(), fig=fig, sticks=sticks)

    # -- linke Spalte ordnen ------------------------------------------------------
    def _left_width(self):
        left, bar, ls, _ = self._left_parts
        return (max(420, left.minimumSizeHint().width(), bar.minimumSizeHint().width())
                + ls.verticalScrollBar().sizeHint().width() + 4)

    def fit_left(self):
        """Linke Spalte auf ihre tatsächliche Mindestbreite (STYLE.ColumnFit, läuft auch von selbst bei Änderungen)."""
        self.column_fit.fit()

    # -- linke Spalte ordnen (Karten) -------------------------------------------
    def group_titled(self, key):
        root = self.lv.parentWidget()                    # linke Spalte (hängt beim Ordnen noch nicht am Tab)
        return next(g for g in root.findChildren(QGroupBox) + self.findChildren(QGroupBox) if g.title() == T(key))

    def fold(self, group, name, keys=None, opened=False):
        """Karte einklappbar machen; keys: Zustandsschlüssel für „(geändert)“ (Vergleich mit DEFAULT_STATE)."""
        changed = (lambda: any(self.st.get(k) != self.DEFAULT_STATE.get(k) for k in keys)) if keys else None
        f = STYLE.Fold(group, f"{self.STATE_KEY}/{name}", self.main.settings, changed, opened)
        self.folds.append(f)
        return f

    def to_right(self, group, title):
        self._to_right.append((group, title))

    def arrange(self):
        """Standard: „Achsen, Größe und Formate“ eingeklappt; die Bildunterschrift steht rechts im Reiter „SI-Text“
        (`_build_si_page`). Tabs ergänzen (super())."""
        self.fold(self.grp_common, "common", ("x_auto", "ymax", "size", "w_cm", "h_cm", "fmt"))

    # -- Rechenweg, Ergebnis-Kacheln, SI-Text (Entwurf 2026-11) --------------------------
    SI_PAGE = True                     # Reiter „SI-Text“ (Bildunterschrift, Methodentext) neben der Abbildung
    DRAG_HINT = "drag_hint_tab"        # Fußnote unter den Karten; Tabs ohne Kurven: "drag_hint_plain"

    def chain(self):
        """Rechenweg dieses Tabs: [(Schritt, benutzt)] aus dem aktuellen Zustand; Tabs mit Auswertung überschreiben."""
        return []

    def kpis(self):
        """Ergebnis auf einen Blick: höchstens zwei (Bezeichnung, Wert) aus den aktuellen Ergebnissen."""
        return []

    def _build_si_page(self):
        """Reiter „SI-Text“: Bildunterschrift mit ihren Feldern und der Methodentext der Fits, je mit „Kopieren“."""
        self.si_page = self.lbl_methods = None
        if not self.SI_PAGE:                              # X-Ray, DFT: eigener Reiter für Bildunterschrift/SI
            return
        cap = getattr(self, "grp_caption", None)
        if cap is None:                                   # Tab ohne eigene Felder: nur die fertige Unterschrift
            cap = QGroupBox(T("cap_box"))
            f = make_form(cap)
            self.lbl_cap = STYLE.SiText()
            f.addRow(self.lbl_cap)
        if isinstance(self.lbl_cap, STYLE.SiText):        # ohne Abbildung: grauer Platzhalter statt einer leeren Karte
            self.lbl_cap.empty = T("si_caption_empty")
            self.lbl_cap.setText(self.lbl_cap.text())
        cap.setTitle(T("si_caption_title"))
        self.lbl_cap.setStyleSheet("")
        self.lbl_cap.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_cap.setProperty("plaintext", True)          # tidy: nicht mittig setzen
        b = STYLE.copy_button()
        b.clicked.connect(self.copy_caption)
        page = QWidget()
        v = QVBoxLayout(page)
        v.addWidget(cap)
        if type(self).methods_text is not FigureTab.methods_text:
            g = QGroupBox(T("si_methods_title"))
            gv = QVBoxLayout(g)
            self.lbl_methods = STYLE.SiText(empty=T("si_methods_none"))
            gv.addWidget(self.lbl_methods)
            mb = self.methods_button()                       # Knöpfe auf die Titelzeile: Aufbau-Text, ganz rechts Kopieren
            copy_, setup_ = mb.findChildren(QPushButton)
            copy_.setIcon(STYLE.icon("copy"))
            copy_.setText(T("si_copy"))
            self._methods_actions = (g, setup_, copy_)
            mb.deleteLater()
            v.addWidget(g)
        v.addStretch(1)
        align_forms(page.findChildren(QFormLayout))
        STYLE.tidy(page)
        v.setContentsMargins(*PAGE_INSET)
        # Eingabefelder der Unterschrift (ed_cap ist bei den meisten Tabs ein dict Schlüssel -> Feld; „Weitere“ hat ein
        # einzelnes Feld in der linken Spalte, das nicht hierher gehört)
        fields = [e for e in self.ed_cap.values() if cap.isAncestorOf(e)] if isinstance(getattr(self, "ed_cap", None), dict) else []
        fl = cap.layout()                                 # fertige Unterschrift: linksbündig über die ganze Karte, in
        r, _role = fl.getWidgetPosition(self.lbl_cap)     # einem eigenen Rahmen (tidy setzt Hinweise sonst wieder mittig
        if r >= 0:                                        # unter die Wertespalte)
            lab, _w = STYLE.take_row(fl, r)
            if lab is not None:
                lab.hide()
                lab.deleteLater()
            holder = QWidget()
            hl = QVBoxLayout(holder)
            hl.setContentsMargins(0, 4, 0, 4)
            if fields:                                     # Karte mit Eingabefeldern: „Kopieren“ direkt über dem Text
                hl.addWidget(STYLE.text_head(T("si_caption_text"), b))
            hl.addWidget(self.lbl_cap)
            fl.insertRow(r, holder)
        if not fields:
            STYLE.card_actions(cap, b)                    # Karte ist nur der Text: „Kopieren“ auf der Titelzeile
        if fields:                                        # Felder bis zum Kartenrand wie Text und Knopf
            cap.setProperty("widefields", True)
            STYLE._wide_fields(cap)
        if getattr(self, "_methods_actions", None):
            STYLE.card_actions(*self._methods_actions)
        self.lbl_cap.setProperty("fieldw", None)
        self.lbl_cap.setProperty("centered", False)
        self.lbl_cap.setMinimumWidth(0)
        self.lbl_cap.setMaximumWidth(16777215)
        self.lbl_cap.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        sa = QScrollArea()
        sa.setWidget(page)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        self.si_page = sa
        self.right_tabs.addTab(sa, T("tab_si_text"))

    def copy_caption(self):
        name = (getattr(self.main, "compound", None) or {}).get("name") or "X"
        try:
            text = html.unescape(re.sub(r"<[^>]+>", "", self.si_caption(name))) if self.F is not None else ""
        except Exception:
            text = ""
        if text:
            QApplication.clipboard().setText(text)
        self.main.statusBar().showMessage(T("si_caption_copied") if text else T("si_caption_none"), 6000)

    def refresh_summary(self):
        """Rechenweg, Kacheln und SI-Text nach dem Zeichnen auf den aktuellen Stand bringen."""
        if getattr(self, "kpi_box", None) is None:
            return
        try:
            if self.chain_row is not None:
                self.chain_row.set_items(self.chain())
            ks = list(self.kpis())[:2] if getattr(self, "F", None) is not None else []
        except Exception:                                 # Kennwerte sind Zugabe: nie das Zeichnen stören
            ks = []
        self.kpi_box.show_items(ks)
        if self.lbl_methods is not None and self.right_tabs.currentWidget() is self.si_page:
            try:                                           # ohne Abbildung kein Text (CV schrieb sonst den Absatz zu
                txt = self.methods_text() if getattr(self, "F", None) is not None else ""   # Messungen, die es nicht gibt)
            except Exception:
                txt = ""
            self.lbl_methods.setText(txt)

    def move_right(self, group, title):
        """Karte als Reiter neben „Abbildung“ (kostet nur die Reiterzeile, die Abbildung bleibt gleich groß –
        unter der Abbildung würde sie in der Höhe begrenzt und schrumpfen)."""
        # eigene Seite mit Spalte und Bild (Energiediagramm): ohne Ergebniskarte darum
        self.right_tabs.addTab(group if group.property("rawpage") else result_page(group), title)

    # -- Hinweise im Tab ----------------------------------------------------------
    def add_note(self, msg):
        """Hinweis beim Zeichnen: im Tab unter der Vorschau anzeigen und ins Protokoll schreiben."""
        msg = msg.strip()
        if msg not in self._notes:
            self._notes.append(msg)
        self.main.log_signal.emit("  " + msg)

    def notes_begin(self):
        self._notes = []

    def notes_show(self, error=None):
        """Gesammelte Hinweise (orange) bzw. einen Fehler (rot) unter der Vorschau zeigen; „(geändert)“ an
        eingeklappten Karten aktualisieren."""
        for f in getattr(self, "folds", ()):
            f.refresh()
        if getattr(self, "steps", None) is not None:
            self.steps.refresh()
            self.sync_caption_bar()
            self.refresh_summary()
        if error is not None:
            self.lbl_note.setText(T("note_error", e=error))
            self.lbl_note.setStyleSheet(WARN_CSS)
        else:
            self.lbl_note.setText("\n".join("⚠ " + n for n in self._notes))
            self.lbl_note.setStyleSheet(STYLE.NOTE_CSS)
        self.lbl_note.setVisible(error is not None or bool(self._notes))

    def render(self):
        self.notes_begin()
        try:
            if self.dragger:
                self.dragger.disconnect()
                self.dragger = None
            if self.hover:
                self.hover.disconnect()
                self.hover = None
            spec_cfg = self.base_cfg()
            self.host.set_figure_size(*spec_cfg["figsize_in"])
            self.F = self.build(self.fig)
            self.show_caption()
            self.preview_stack.setCurrentIndex(0 if self.F is None else 1)
            if self.F is None:
                self.fig.clear()
                self.fig.text(0.5, 0.5, T("tab_empty"), ha="center", va="center", color="gray")
            else:
                self.dragger = TabDragger(self.F, self.layout_changed)
                curves = [dict(x=c["x"], y=c["y"], val=c.get("val", c["y"]), name=c.get("label") or "")
                          for c in self.F.curves if not c.get("aux")]
                self.hover = HoverReadout(self.F, curves, self.main.show_hover, self.hover_text)
                self.sync_sizes(self.F.current_layout())
            self.canvas.draw_idle()
            self.notes_show()
        except Exception as e:
            self.main.log_signal.emit(traceback.format_exc())
            self.main.statusBar().showMessage(f"{T('err_title')}: {e}", 8000)
            self.notes_show(error=e)
        self.main.push_undo()                          # auch wenn das Bild scheitert: Änderung speichern/rückgängig

    def hover_text(self, lam, val, name):
        if val is None:
            return T("hover_lam", lam=lam)
        return T("hover_y", lam=lam, y=val, name=name)

    def layout_changed(self, layout):
        if not layout:                                 # nichts bewegt
            return
        layout = self.st["layout"][self.size_key()] = dict(self.st["layout"].get(self.size_key()) or {}, **layout)
        self.sync_sizes(layout)
        self.main.push_undo()

    def reset_layout(self):
        self.st["layout"][self.size_key()] = {}
        self.render()

    # was „Alles auf Standard“ behält: Daten und Angaben zur Messung (Dateien, Referenz, Kalibrierung, eingegebene
    # Werte); Exportgröße/-formate und Bildunterschriften (cap_*) bleiben immer
    RESET_KEEP: tuple = ()

    def reset_defaults(self):
        """Alle übrigen Einstellungen des Tabs (Darstellung und Auswertung) auf DEFAULT_STATE, Layout neu.
        Rückgängig (Strg+Z) holt alles zurück."""
        keep = set(self.RESET_KEEP) | {"size", "w_cm", "h_cm", "fmt"}
        for k, v in self.DEFAULT_STATE.items():
            if k not in keep and not k.startswith("cap_"):
                self.st[k] = copy.deepcopy(v)
        key = self.main.tab_key_of(self)              # nur diesen Tab aus dem Zustand neu aufbauen
        self.main.replace_tab(key) if key else self.main.rebuild_tabs()
        self.main.push_undo()
        self.main.statusBar().showMessage(T("xr_reset_display_done"), 6000)

    def export_dialog(self):
        """Direkt ins Projekt: <Verbindung>_<Tab>.* nach figures/, tables/ und SI/ (wird überschrieben)."""
        if not self.main.ensure_project():
            return
        pdir = Path(self.main.project_dir)
        base = PRJ.staging(pdir, self.STATE_KEY) / PRJ.export_stem(self.main.export_name(), self.STATE_KEY)
        try:
            out = self.main.place_exports(self.export_to(base))
        except PermissionError as e:
            return self.main.error(T("report_locked", p=getattr(e, "filename", "") or ""))
        except Exception as e:
            return self.main.error(str(e))
        self.main.exported(p.parent for p in out)
        return out

    def export_to(self, base: Path):
        base = Path(base).resolve()
        fig = MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI)
        FigureCanvasAgg(fig)
        F = self.build(fig)
        if F is None:
            raise RuntimeError(T("tab_empty"))
        F.cfg["output"] = str(base.with_suffix("." + F.cfg["_main_fmt"]))
        F.cfg["_base_dir"] = base.parent
        F.export()
        data = base.with_name(base.name + "_data.csv")
        write_curves_csv(data, F.curves, F.cfg.get("xlabel", "x"), F.cfg.get("ylabel", "y"))
        out = [base.with_suffix("." + e) for e in [F.cfg["_main_fmt"]] + F.cfg["extra_formats"]] + [data]
        txt = self.methods_text()
        if txt:
            out.append(base.with_name(base.name + "_methods.txt"))
            out[-1].write_text(txt + "\n", encoding="utf-8")
        return out

    # -- SI-Export (Word) ------------------------------------------------------------------
    SI_CAPTION = ""                      # englische Bildunterschrift, {name} = Name der Verbindung (fett)

    def si_figure(self, out_dir, name):
        """Abbildung des Tabs für den SI-Export -> [("image", …), ("figcap", …)], leer ohne Daten."""
        fig = MplFigure(figsize=(8, 6), dpi=PREVIEW_DPI)
        FigureCanvasAgg(fig)
        F = self.build(fig)
        if F is None:
            return []
        svg = Path(out_dir) / f"{core.safe_name(name)}_{self.STATE_KEY}.svg"
        return [si_image(F, svg), ("figcap", self.si_caption(name))]

    def si_caption(self, name):
        """Bildunterschrift (HTML) für den SI-Export; Tabs mit mehr Wissen (CV, SEC, EPR) überschreiben das."""
        return self.SI_CAPTION.format(name="<b>" + html.escape(name) + "</b>")

    CAP_FIELDS: tuple = ()               # Felder der Bildunterschrift -> st["cap_<Feld>"] (Konzentration, Lösungsmittel …)
    CAP_REMEMBER: tuple = ()             # Felder, die für neue Projekte gemerkt werden (Leitsalz)

    def caption_box(self):
        """Gruppe „Bildunterschrift (SI-Export)“: Freitextfelder + Vorschau der fertigen Unterschrift."""
        from elucida.app.i18n import TEXTS
        st = self.st
        g = QGroupBox(T("cap_box"))
        self.grp_caption = g
        g.setToolTip(T(f"{self.STATE_KEY}_cap_tip"))
        f = make_form(g)
        self.ed_cap = {}
        for key in self.CAP_FIELDS:
            if key in self.CAP_REMEMBER and not st.get("cap_" + key):
                st["cap_" + key] = str(self.main.settings.value(f"cap_{key}", "") or "")
            ed = STYLE.ChemEdit(st.get("cap_" + key, ""))    # CH₂Cl₂ schon im Feld mit tiefgestellten Ziffern
            ph = f"{self.STATE_KEY}_cap_{key}_ph"
            ed.setPlaceholderText(T(ph if ph in TEXTS else f"cap_{key}_ph"))
            ed.editingFinished.connect(self.cap_edited)
            self.ed_cap[key] = ed
            lab = f"{self.STATE_KEY}_cap_{key}"
            f.addRow(T(lab if lab in TEXTS else f"cap_{key}"), ed)
        self.lbl_cap = STYLE.SiText()
        self.lbl_cap.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_cap)
        return g

    def cap_edited(self):
        for key, ed in self.ed_cap.items():
            self.st["cap_" + key] = ed.text().strip()
            if key in self.CAP_REMEMBER and self.st["cap_" + key]:
                self.main.settings.setValue(f"cap_{key}", self.st["cap_" + key])
        self.show_caption()
        self.main.push_undo()

    def show_caption(self):
        if getattr(self, "lbl_cap", None) is not None:
            name = (getattr(self.main, "compound", None) or {}).get("name") or "X"
            try:
                self.lbl_cap.setText("<b>Figure Sn:</b> " + self.si_caption(name))
            except Exception:
                self.lbl_cap.setText("")

    def si_setup_text(self):
        """Allgemeiner Aufbau-Absatz der Methode (Geräte, Elektroden …), vom Nutzer hinterlegt; steht nur in den
        lokalen Einstellungen, nicht im Projekt und nicht im Code."""
        return str(self.main.settings.value(f"si_setup/{self.STATE_KEY}", "") or "").strip()

    def edit_setup_text(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(T("si_setup_title"))
        dlg.resize(640, 420)
        v = QVBoxLayout(dlg)
        lb = QLabel(T("si_setup_hint"))
        lb.setWordWrap(True)
        lb.setStyleSheet(HINT_CSS)
        v.addWidget(lb)
        ed = QPlainTextEdit(self.si_setup_text())
        v.addWidget(ed, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if dlg.exec() == QDialog.Accepted:
            self.main.settings.setValue(f"si_setup/{self.STATE_KEY}", " ".join(ed.toPlainText().split()))

    # -- SI-Text zu den Fits (englisch) -------------------------------------------------
    def methods_text(self) -> str:
        """Methodenabsatz für die SI zu allem, was dieser Tab fittet, dazu die Ergebnisse; leer = kein Fit."""
        return ""

    def methods_button(self):
        """Knopf „SI-Text kopieren“ (Zwischenablage); derselbe Text wird beim Export als _methods.txt geschrieben."""
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        b = QPushButton(T("si_copy_methods"))
        b.setToolTip(T("si_copy_methods_tip"))
        b.clicked.connect(self.copy_methods)
        b2 = QPushButton(T("si_setup_btn"))
        b2.setToolTip(T("si_setup_tip"))
        b2.clicked.connect(self.edit_setup_text)
        row.addWidget(b)
        row.addWidget(b2)
        row.addStretch(1)
        return w

    def copy_methods(self):
        txt = self.methods_text()
        if txt:
            QApplication.clipboard().setText(txt)
        self.main.statusBar().showMessage(T("si_methods_copied") if txt else T("si_methods_none"), 6000)

    def _is_data_key(self, k):
        """Daten, Angaben zur Messung, Bildunterschrift: nicht in Vorlagen (X-Ray/DFT: entries, current)."""
        return k in self.RESET_KEEP or k in ("entries", "current") or k.startswith("cap_")

    def save_setup(self):
        p, _ = QFileDialog.getSaveFileName(self, T("tab_save"), self.STATE_KEY + ".yaml", "YAML (*.yaml)")
        if p:
            data = {k: v for k, v in self.st.items() if not self._is_data_key(k)}
            Path(p).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def load_setup(self):
        p, _ = QFileDialog.getOpenFileName(self, T("tab_load"), "", "YAML (*.yaml)")
        if p:
            data = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                return self.main.error(f"YAML: {p}")
            keep = {k: v for k, v in self.st.items() if self._is_data_key(k)}
            self.st.clear()
            self.st.update(copy.deepcopy(self.DEFAULT_STATE))
            self.st.update({k: v for k, v in data.items() if not self._is_data_key(k)})
            self.st.update(keep)
            key = self.main.tab_key_of(self)
            self.main.replace_tab(key) if key else self.main.rebuild_tabs()


COMMON_DEFAULTS = {"x_auto": True, "x_min": 200.0, "x_max": 800.0, "size": "half_a4", "w_cm": 16.0,
                   "h_cm": 11.0, "fmt": {"pdf": True, "svg": True, "png": True}, "layout": {}}


# ----------------------------------------------------------------------------
class OverlayTab(FigureTab):
    STATE_KEY = "overlay"
    GUIDE, GUIDE_ACTION, GUIDE_EXTRA = "overlay", ("guide_add", "add_exp"), "tabs_button"
    TEXT_OPTS = ("fonts", "greek", "labels", "label_size", "axes_frame", "struct_frame")
    SI_CAPTION = "Comparison of UV-Vis spectra of {name}."
    RESET_KEEP = ("entries", "structure")
    DEFAULT_STATE = dict(COMMON_DEFAULTS, entries=[], mode="norm", nlo=300.0, nhi=500.0, ymax=0.0,
                         baseline=True, sticks=True, stick_mode="band", structure=None, struct_w=20.0,
                         stack=False, stack_gap=1.0, y_axis="auto", curve_labels=False, zero_lines=False,
                         triplets=False)


    def arrange(self):
        super().arrange()
        self.fold(self.group_titled("ov_stack_grp"), "stack", ("stack", "stack_gap", "y_axis", "curve_labels", "zero_lines"))
    def build_controls(self):
        st = self.st
        g = QGroupBox(T("ov_curves"))
        v = QVBoxLayout(g)
        btns = []
        for txt, fn in ((T("ov_add_exp"), self.add_exp), (T("ov_add_sec"), self.add_sec),
                        (T("ov_add_calc"), self.add_calc), (T("ov_add_esd"), self.add_esd),
                        (T("ov_combine"), self.combine_selected),
                        ("↑", lambda: self.move_selected(-1)), ("↓", lambda: self.move_selected(1)),
                        (T("remove"), self.remove_selected)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            if fn == self.combine_selected:
                b.setToolTip(T("ov_combine_tip"))
                self.btn_combine = b
            elif fn == self.add_esd:
                b.setToolTip(T("ov_add_esd_tip"))
            btns.append(b)
        # Hinzufügen / Auswahl: zwei Reihen im selben Raster, beide bis zur Kante (Symmetrie)
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(8)
        for c_ in range(8):
            grid.setColumnStretch(c_, 1)
        arrows = QHBoxLayout()
        arrows.setSpacing(8)
        arrows.addStretch(1)
        arrows.addWidget(btns[5])
        arrows.addWidget(btns[6])
        arrows.addStretch(1)
        for k_ in range(4):
            grid.addWidget(btns[k_], 0, 2 * k_, 1, 2)
        grid.addWidget(btns[4], 1, 0, 1, 2)
        grid.addLayout(arrows, 1, 2, 1, 2)
        grid.addWidget(btns[7], 1, 4, 1, 2)
        grid.addWidget(self.tabs_button(list_style=True), 1, 6, 1, 2)
        v.addLayout(grid)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), T("ov_type")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)    # Strg/Shift: mehrere fürs Kombinieren
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self.table_edited)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.table.itemSelectionChanged.connect(self.update_combine)
        QTimer.singleShot(0, self.update_combine)             # Anfangszustand (nichts markiert)
        v.addWidget(self.table)
        RowDrag(self.table, self.move_row)
        STYLE.hide_when_empty(self.table)
        lay = self.lv
        lay.addWidget(g)

        # Details der gewählten Kurve
        self.det = QGroupBox(T("ov_details"))
        f = make_form(self.det)
        self.cb_own = QCheckBox(T("ov_own_norm"))
        row = QHBoxLayout()
        self.sp_elo = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=300)
        self.sp_ehi = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=500)
        for w in (self.cb_own, self.sp_elo, QLabel("–"), self.sp_ehi):
            row.addWidget(w)
        f.addRow(T("ov_norm_window"), row)
        self.ed_conc = QLineEdit()
        self.cmb_unit = QComboBox()
        for key, label in UNITS:
            self.cmb_unit.addItem(label, key)
        row = QHBoxLayout()
        row.addWidget(self.ed_conc, 1)
        row.addWidget(self.cmb_unit)
        self.lbl_conc = QLabel(T("col_conc"))
        f.addRow(self.lbl_conc, row)
        self.ed_mw = QLineEdit()
        self.lbl_mw = QLabel(T("molar_mass"))
        f.addRow(self.lbl_mw, self.ed_mw)
        self.sp_d = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=100, value=1.0, singleStep=0.1)
        self.lbl_d = QLabel(T("path_length"))
        f.addRow(self.lbl_d, self.sp_d)
        self.cmb_eps = QComboBox()                       # verknüpfte ε-Serie: welche Messung (Standard automatisch)
        self.cmb_eps.setToolTip(T("ov_eps_pick_tip"))
        self.lbl_eps = QLabel(T("ov_eps_pick"))
        f.addRow(self.lbl_eps, self.cmb_eps)
        self.cmb_eps.currentIndexChanged.connect(self.detail_changed)
        self.sp_fwhm = QDoubleSpinBox(decimals=2, minimum=0.02, maximum=3, singleStep=0.05, value=0.3, suffix=" eV")
        self.lbl_fwhm = QLabel(T("ov_fwhm"))
        f.addRow(self.lbl_fwhm, self.sp_fwhm)
        self.sp_shift = QDoubleSpinBox(decimals=2, minimum=-3, maximum=3, singleStep=0.05, value=0.0, suffix=" eV")
        self.lbl_shift = QLabel(T("ov_shift"))
        f.addRow(self.lbl_shift, self.sp_shift)
        self.cmb_esd_unit = QComboBox()                  # ESD: Einheit der Datei (steht nicht darin)
        for u in CALC.ESD_UNITS:
            self.cmb_esd_unit.addItem("cm⁻¹" if u == "cm-1" else u, u)
        self.cmb_esd_unit.setToolTip(T("ov_esd_unit_tip"))
        self.lbl_esd_unit = QLabel(T("ov_esd_unit"))
        f.addRow(self.lbl_esd_unit, self.cmb_esd_unit)
        self.cmb_esd_unit.currentIndexChanged.connect(self.detail_changed)
        self.cmb_soc = QComboBox()
        self.lbl_soc = QLabel(T("ov_soc"))
        f.addRow(self.lbl_soc, self.cmb_soc)
        self.ed_weights = QLineEdit()
        self.ed_weights.setToolTip(T("ov_weights_tip"))
        self.lbl_weights = QLabel(T("ov_weights"))
        f.addRow(self.lbl_weights, self.ed_weights)
        self.ed_weights.editingFinished.connect(self.detail_changed)
        # Farbe der Lösung aus dem gerechneten Spektrum (nur Anzeige, wie im ε-Tab): A = ε(λ)·c·d
        row = QHBoxLayout()
        self.sp_ccol_c = QDoubleSpinBox(decimals=4, minimum=0.0001, maximum=1e4, singleStep=0.1, value=1.0, suffix=" mM")
        self.sp_ccol_d = QDoubleSpinBox(decimals=2, minimum=0.01, maximum=100, singleStep=0.1, value=1.0, suffix=" cm")
        for w_ in (QLabel("c"), self.sp_ccol_c, QLabel("d"), self.sp_ccol_d):
            row.addWidget(w_)
        self.w_ccol = QWidget()
        self.w_ccol.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        self.lbl_ccol = QLabel(T("ov_calc_color"))
        self.lbl_ccol.setToolTip(T("ov_calc_color_tip"))
        f.addRow(self.lbl_ccol, self.w_ccol)
        self.sw_ccol = QLabel()
        self.sw_ccol.setFixedHeight(28)
        self.lbl_ccol_info = STYLE.HintLabel()
        self.lbl_ccol_info.setWordWrap(True)
        self.lbl_ccol_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow("", self.sw_ccol)
        f.addRow("", self.lbl_ccol_info)
        self.calc_color_widgets = (self.lbl_ccol, self.w_ccol, self.sw_ccol, self.lbl_ccol_info)
        row = QHBoxLayout()
        self.sp_scale = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=1000, singleStep=0.05, value=1.0)
        self.sp_offset = QDoubleSpinBox(decimals=3, minimum=-1000, maximum=1000, singleStep=0.05, value=0.0)
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_scale)
        row.addWidget(QLabel("+"))
        row.addWidget(self.sp_offset)
        f.addRow(T("ov_scale_offset"), row)
        row = QHBoxLayout()
        self.cmb_ls = QComboBox()
        for key in ("solid", "dashed", "dotted", "dashdot"):
            self.cmb_ls.addItem(T("ls_" + key), key)
        self.sp_lw = QDoubleSpinBox(decimals=1, minimum=0.0, maximum=6, singleStep=0.25, value=0.0, suffix=" pt")
        self.sp_lw.setSpecialValueText(T("auto"))
        row.addWidget(self.cmb_ls, 1)
        row.addWidget(self.sp_lw)
        f.addRow(T("ov_line"), row)
        row = QHBoxLayout()
        self.lbl_estruct = QLabel("–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        b1.clicked.connect(self.choose_entry_structure)
        b2.clicked.connect(lambda: self.set_entry_structure(None))
        row.addWidget(self.lbl_estruct, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        f.addRow(T("structure"), row)
        self.cb_ecolor = QCheckBox(T("ov_struct_color"))
        self.cb_ecolor.toggled.connect(self.detail_changed)
        f.addRow(self.cb_ecolor)
        self.cb_samelevel = QCheckBox(T("ov_same_level"))
        self.cb_samelevel.setToolTip(T("ov_same_level_tip"))
        self.cb_samelevel.toggled.connect(self.detail_changed)
        f.addRow(self.cb_samelevel)
        for w in (self.sp_elo, self.sp_ehi, self.sp_d, self.sp_fwhm, self.sp_shift, self.sp_scale,
                  self.sp_offset, self.sp_lw, self.sp_ccol_c, self.sp_ccol_d):
            w.valueChanged.connect(self.detail_changed)
        self.cmb_ls.currentIndexChanged.connect(self.detail_changed)
        self.cmb_soc.currentIndexChanged.connect(self.detail_changed)
        self.cb_own.toggled.connect(self.detail_changed)
        self.cmb_unit.currentIndexChanged.connect(self.detail_changed)
        self.ed_conc.editingFinished.connect(self.detail_changed)
        self.ed_mw.editingFinished.connect(self.detail_changed)
        lay.addWidget(self.det)

        g = QGroupBox(T("ov_display"))
        f = make_form(g)
        self.cmb_ymode = QComboBox()                     # y-Größe passend zu den Daten (früher nur normiert/ε)
        for key in ("norm", "eps", "abs"):
            self.cmb_ymode.addItem(T("ov_y_" + key), key)
        self.cmb_ymode.setCurrentIndex(max(0, self.cmb_ymode.findData(st["mode"])))
        self.cmb_ymode.setToolTip(T("ov_ymode_tip"))
        f.addRow(T("ov_ymode"), self.cmb_ymode)
        row = QHBoxLayout()
        self.sp_nlo = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=st["nlo"])
        self.sp_nhi = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=st["nhi"])
        for w in (self.sp_nlo, QLabel("–"), self.sp_nhi):
            row.addWidget(w)
        f.addRow(T("ov_norm_window"), row)
        self.cb_base = QCheckBox(T("ov_baseline"))
        self.cb_base.setProperty("chip_here", True)      # gehört zum Feld darüber
        self.cb_base.setChecked(st["baseline"])
        self.cb_sticks = QCheckBox(T("ov_sticks"))
        self.cb_sticks.setChecked(st["sticks"])
        f.addRow(self.cb_base)
        f.addRow(self.cb_sticks)
        self.cb_trip = QCheckBox(T("ov_triplets"))
        self.cb_trip.setToolTip(T("ov_triplets_tip"))
        self.cb_trip.setChecked(st.get("triplets", False))
        self.cb_trip.toggled.connect(self.changed)
        f.addRow(self.cb_trip)
        self.cmb_stick = QComboBox()
        for key in ("band", "max", "faxis"):
            self.cmb_stick.addItem(T("stick_" + key), key)
        self.cmb_stick.setCurrentIndex(max(0, self.cmb_stick.findData(st.get("stick_mode", "band"))))
        self.cmb_stick.setToolTip(T("stick_mode_tip"))
        f.addRow(T("stick_mode"), self.cmb_stick)
        self.cmb_stick.currentIndexChanged.connect(self.changed)
        row = QHBoxLayout()
        self.lbl_struct = QLabel(Path(st["structure"]).name if st["structure"] else "–")
        b1 = QPushButton(T("choose"))
        b1.clicked.connect(self.choose_structure)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(lambda: self.set_structure(None))
        row.addWidget(self.lbl_struct, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        f.addRow(T("structure"), row)
        self.sp_struct_w = self.size_spin(f, "struct_w", "image_struktur")
        self.cmb_ymode.currentIndexChanged.connect(self.changed)
        self.cmb_ymode.currentIndexChanged.connect(self.mode_changed)
        for w in (self.sp_nlo, self.sp_nhi):
            w.valueChanged.connect(self.changed)
        for w in (self.cb_base, self.cb_sticks):
            w.toggled.connect(self.changed)
        lay.addWidget(g)

        g = QGroupBox(T("ov_stack_grp"))
        f = make_form(g)
        row = QHBoxLayout()
        self.cb_stack = QCheckBox(T("ov_stack"))
        self.cb_stack.setChecked(st["stack"])
        self.cb_stack.setToolTip(T("ov_stack_tip"))
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=1000, singleStep=0.1, value=st["stack_gap"])
        self.sp_gap.setToolTip(T("ov_gap_tip"))
        row.addWidget(self.cb_stack)
        row.addWidget(QLabel(T("ov_gap")))
        row.addWidget(self.sp_gap)
        row.addStretch(1)
        f.addRow(row)
        self.cmb_yaxis = QComboBox()
        for key in ("auto", "numbers", "no_numbers", "off"):
            self.cmb_yaxis.addItem(T("yaxis_" + key), key)
        self.cmb_yaxis.setCurrentIndex(max(0, self.cmb_yaxis.findData(st["y_axis"])))
        f.addRow(T("ov_yaxis"), self.cmb_yaxis)
        self.cb_clabels = QCheckBox(T("ov_curve_labels"))
        self.cb_clabels.setChecked(st["curve_labels"])
        self.cb_zero = QCheckBox(T("ov_zero_lines"))
        self.cb_zero.setChecked(st["zero_lines"])
        f.addRow(self.cb_clabels)
        f.addRow(self.cb_zero)
        for w in (self.cb_stack, self.cb_clabels, self.cb_zero):
            w.toggled.connect(self.changed)
        self.sp_gap.valueChanged.connect(self.changed)
        self.cmb_yaxis.currentIndexChanged.connect(self.changed)
        lay.addWidget(g)
        self.fill_table()
        self.show_details()

    def mode_changed(self, *_):
        """ymax gilt für die jeweilige Skala (normiert ~1, ε in 10³, A): beim Umschalten auf Automatik."""
        self.sp_ymax.setValue(0.0)
        for w in (self.cb_own, self.sp_elo, self.sp_ehi):
            w.setEnabled(self.cmb_ymode.currentData() == "norm")   # Normierungsbereich wirkt nur beim Normieren

    # -- Kurvenliste ------------------------------------------------------------
    def next_color(self):
        used = {e["color"] for e in self.st["entries"]}
        for c in PALETTE:
            if c not in used:
                return c
        return PALETTE[len(self.st["entries"]) % len(PALETTE)]

    def add_exp(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ov_add_exp"), self.main.settings.value("last_dir", ""),
                                             f"{T('flt_csv')};;{T('flt_all')}")
        for p in ps:
            try:
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                for s_ in self.samples(p):
                    self.st["entries"].append({
                        "kind": "exp", "file": p, "sample": s_["key"], "label": s_["name"],
                        "color": self.next_color(), "visible": True, "own_norm": False,
                        "nlo": self.st["nlo"], "nhi": self.st["nhi"], "conc": None, "unit": "mM",
                        "mw": None, "d": 1.0})
            except Exception as e:
                self.main.error(f"{Path(p).name}: {e}")
        self.fill_table()
        self.timer.start()

    def tabs_button(self, list_style=False):
        """„Aus Tabs ▾“: ε-Serien und TD-DFT-Rechnungen des DFT-Tabs übernehmen (abgehakt = schon im Overlay)."""
        b = STYLE.list_button(T("ov_from_tabs")) if list_style else QPushButton(T("ov_from_tabs"))
        b.setToolTip(T("ov_from_tabs_tip"))
        b.setMenu(QMenu(b))
        b.menu().aboutToShow.connect(lambda m=b.menu(): self.fill_tabs_menu(m))
        return b

    def tab_sources(self):
        """-> [(Art, Schlüssel, Anzeigename)]: Serien des ε-Tabs, Rechnungen des DFT-Tabs mit TD-DFT-Zuständen."""
        out = [("eps", g, g) for g in (getattr(self.main, "groups", None) or {})]
        for d in (getattr(self.main, "dft_state", None) or {}).get("entries") or []:
            p = d.get("file")
            if not p or Path(p).suffix.lower() not in (".out", ".log") or not Path(p).exists():
                continue
            try:
                self.cache(("tddft", p), lambda p=p: X.parse_tddft(p))
            except Exception:
                continue                                   # Optimierung/Frequenzen ohne Anregungen
            out.append(("calc", p, Path(p).stem))
        return out

    def linked_entry(self, kind, key):
        for e in self.st["entries"]:
            if (kind == "eps" and e.get("link") == "eps" and e.get("series") == key) or \
                    (kind == "calc" and e["kind"] == "calc" and not e.get("sources") and
                     Path(e["file"]).resolve() == Path(key).resolve()):
                return e
        return None

    def fill_tabs_menu(self, m):
        m.clear()
        src = self.tab_sources()
        for kind, key, name in src:
            a = m.addAction(f"{name} ({T('ov_eps_linked') if kind == 'eps' else 'TD-DFT'})")
            a.setCheckable(True)
            a.setChecked(self.linked_entry(kind, key) is not None)
            a.triggered.connect(lambda on, kind=kind, key=key, name=name: self.toggle_linked(kind, key, name, on))
        if not src:
            m.addAction(T("ov_from_tabs_none")).setEnabled(False)

    def toggle_linked(self, kind, key, name, on):
        """Eintrag hinzufügen bzw. (Haken weg) entfernen. ε: verknüpft (Messung, c, Einheit, d, M immer aus dem
        ε-Tab); TD-DFT: dieselbe Datei wie im DFT-Tab."""
        e = self.linked_entry(kind, key)
        if not on:
            if e is not None:
                self.st["entries"].remove(e)
        elif e is None:
            base = {"color": self.next_color(), "visible": True, "own_norm": False, "nlo": self.st["nlo"],
                    "nhi": self.st["nhi"]}
            if kind == "eps":
                self.st["entries"].append(dict(base, kind="exp", link="eps", series=key, sample=None, label=name,
                                               conc=None, unit="mM", mw=None, d=1.0))
            else:
                self.st["entries"].append(dict(base, kind="calc", file=key, label=f"{name} (TD-DFT)", fwhm=0.3,
                                               shift=0.0))
        self.fill_table()
        self.show_details()                        # sonst schreibt die nächste Änderung alte Werte in den Nachbarn
        self.timer.start()

    def eps_series(self, e):
        return (getattr(self.main, "groups", None) or {}).get(e.get("series")) or []

    def eps_linked(self, e):
        """Verknüpfte ε-Serie -> (Spektrum {x, y} oder None, Eintrag mit c/Einheit/d/M aus dem ε-Tab). Messung:
        gewählte (e["sample"]) oder automatisch die höchste Konzentration, deren Maximum ab dem Beginn der Peaksuche
        (230 nm) den Cutoff des ε-Tabs nicht überschreitet (sonst die niedrigste)."""
        sp = self.eps_series(e)
        pick = next((s_ for s_ in sp if s_["name"] == e.get("sample")), None)
        if pick is None and sp:
            cut = (getattr(self.main, "glob", None) or {}).get("cutoff", 1.0)
            lo = core.DEFAULTS["peak_range_nm"][0]
            ok = [s_ for s_ in sp if np.nanmax(np.where(s_["x"] >= lo, s_["y"], -np.inf)) <= cut]
            pick = max(ok, key=lambda s_: s_["c"]) if ok else min(sp, key=lambda s_: s_["c"])
        if pick is None:
            return None, e
        mw = ((getattr(self.main, "series", None) or {}).get(e["series"]) or {}).get("mw")
        d = (getattr(self.main, "glob", None) or {}).get("path_length", 1.0)
        return {"x": pick["x"], "y": pick["y"]}, dict(e, conc=pick["c"], unit=pick["unit"], d=d, mw=mw)

    def add_sec(self):
        """Spektren aus dem SEC-Tab übernehmen, ausgewählt nach Potential. SEC-Kurven werden nur normiert
        gezeigt: Schichtdicke und umgesetzte Konzentration der Dünnschichtzelle sind nicht genau bekannt."""
        from elucida.tabs import cv as CV
        sec = self.main.sec_tab
        sec.collect()
        if sec.st["quantity"] == "raw":                  # Rohsignal ist keine Absorbanz
            self.main.error(T("ov_sec_raw"))
            return
        sp, E = sec.series()
        if not sp:
            self.main.error(T("ov_sec_none"))
            return
        off, ref = sec.e_offset()
        ref = "Fc⁺/Fc" if ref.startswith("Fc$") else ref
        dlg = QDialog(self)
        dlg.setWindowTitle(T("ov_add_sec"))
        v = QVBoxLayout(dlg)
        lb = QLabel(T("ov_sec_pick"), wordWrap=True)
        v.addWidget(lb)
        cmb = QComboBox()
        for key in ("all", "ends", "single"):
            cmb.addItem(T("ov_sec_mode_" + key), key)
        v.addWidget(cmb)
        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for i, s_ in enumerate(sp):
            e_txt = f"   {CV._fmt_e(E[i] - off)} V vs. {ref}" if E is not None else ""
            lst.addItem(f"{i + 1:>3}{e_txt}   ({s_['name']})")
        v.addWidget(lst)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.resize(460, 420)
        if dlg.exec() != QDialog.Accepted:
            return
        rows = sorted(ix.row() for ix in lst.selectedIndexes())
        if cmb.currentData() == "single":
            self.add_sec_entries(rows or [len(sp) - 1])
        else:                                   # Bereich: erstes bis letztes markiertes, sonst ganze Serie
            i0, i1 = (rows[0], rows[-1]) if len(rows) >= 2 else (0, len(sp) - 1)
            self.add_sec_series(i0, i1, ends_only=cmb.currentData() == "ends")

    def add_sec_series(self, i0, i1, ends_only=False):
        """SEC-Spektren i0…i1 als EINEN Eintrag: gemeinsamer Normierungsfaktor, damit Intensitätsverhältnisse
        und isosbestische Punkte erhalten bleiben (Einzelnormierung würde sie zerstören)."""
        from elucida.tabs import cv as CV
        from elucida.tabs import sec as SEC
        sec = self.main.sec_tab
        sp, E = sec.series()
        off, ref = sec.e_offset()
        ref = "Fc⁺/Fc" if ref.startswith("Fc$") else ref
        idx = list(range(i0, i1 + 1))
        Es = None if E is None else [float(E[i] - off) for i in idx]
        rng = f"{CV._fmt_e(Es[0], 2)} … {CV._fmt_e(Es[-1], 2)} V vs. {ref}" if Es else f"{len(idx)}"
        self.st["entries"].append({
            "kind": "secser", "files": [self._sec_file(sec, sp[i]) for i in idx], "E": Es, "ref": ref,
            "ends_only": ends_only, "label": T("ov_sec_series_label", rng=rng, n=len(idx)),
            "color": SEC.END_COLOR, "visible": True, "own_norm": False,
            "nlo": self.st["nlo"], "nhi": self.st["nhi"]})
        self.fill_table()
        self.timer.start()

    def sec_series_curves(self, e, lo, hi, bcfg=None, norm=True):
        """Kurven einer SEC-Serie, alle mit demselben Faktor normiert: auf das Startspektrum (Ausgangsverbindung,
        direkt vergleichbar mit dem isolierten UV-Vis-Spektrum); ohne Signal dort auf das Maximum der Serie.
        norm=False: Absorbanz wie gemessen."""
        from elucida.tabs import cv as CV
        from elucida.tabs import sec as SEC
        data = [self.sec_spectrum({"file": f}) for f in e["files"]]
        if not data or any(d is None for d in data):
            return None
        x0 = data[0]["x"]
        ys = []
        for d in data:
            y = np.interp(x0, d["x"], d["y"])
            if bcfg is not None:
                tmp = [{"x": x0, "y": y, "c": 1.0}]
                core.apply_baseline(tmp, bcfg)
                y = tmp[0]["y"]
            ys.append(y)
        win = (x0 >= min(lo, hi)) & (x0 <= max(lo, hi))
        if norm and not win.any():
            return None
        m = float(np.nanmax(ys[0][win])) if norm else 1.0
        if not m > 0:
            m = float(max(np.nanmax(y[win]) for y in ys))
        if not m > 0:
            return None
        n = len(ys)
        idx = [0, n - 1] if (e.get("ends_only") and n > 1) else list(range(n))
        out = []
        for i in idx:
            end = i in (0, n - 1)
            col = (SEC.START_COLOR if i == 0 else e["color"]) if end else "#b0b0b0"
            lab = None
            if end:
                lab = (f"SEC {CV._fmt_e(e['E'][i], 2)} V vs. {CV.axis_ref(e['ref'])}" if e.get("E")
                       else f"SEC {Path(e['files'][i]).stem}")
            out.append({"x": x0, "val": ys[i] / m, "color": col, "label": lab, "main": end,
                        "lw": None if end else 0.5})
        out.sort(key=lambda c: (c["main"], c["color"] != SEC.START_COLOR))   # grau unten, Ende oben
        return out

    def add_sec_entries(self, indices):
        """SEC-Spektren Nr. `indices` (0-basiert, Reihenfolge wie im SEC-Tab) als Einträge anlegen."""
        from elucida.tabs import cv as CV
        sec = self.main.sec_tab
        sp, E = sec.series()
        off, ref = sec.e_offset()
        ref = "Fc⁺/Fc" if ref.startswith("Fc$") else ref
        for i in indices:
            e_ax = None if E is None else float(E[i] - off)
            label = f"SEC {CV._fmt_e(e_ax, 2)} V vs. {ref}" if e_ax is not None else f"SEC {sp[i]['name']}"
            self.st["entries"].append({
                "kind": "sec", "file": self._sec_file(sec, sp[i]), "E": e_ax, "ref": ref, "label": label,
                "color": self.next_color(), "visible": True, "own_norm": False,
                "nlo": self.st["nlo"], "nhi": self.st["nhi"]})
        self.fill_table()
        self.timer.start()

    @staticmethod
    def _sec_file(sec, s_):
        """Datei eines SEC-Spektrums (eine BWSpec-Datei je Spektrum, schon im Projektordner)."""
        return next(p for p in sec.st["spec_files"] if Path(p).stem == s_["name"])

    def sec_spectrum(self, e):
        from elucida.tabs import sec as SEC
        if not Path(e["file"]).exists():
            return None
        s_ = self.cache(("bws", e["file"]), lambda: SEC.read_spectrum(e["file"]))
        if s_.get("merged"):
            return {"x": s_["lam"], "y": s_["A"]}
        win = (s_["lam"] >= SEC.LAM_RANGE[0]) & (s_["lam"] <= SEC.LAM_RANGE[1])   # verrauschte Ränder weg
        return {"x": s_["lam"][win], "y": s_["A"][win]}

    def add_calc(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ov_add_calc"), self.main.settings.value("last_dir", ""),
                                             "ORCA / Gaussian (*.out *.log *.txt);;" + T("flt_all"))
        for p in ps:
            try:
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                r = self.cache(("tddft", p), lambda p=p: X.parse_tddft(p))
                self.main.log_signal.emit(f"  {Path(p).name}: {r['program']}, {len(r['E'])} {T('ov_states')}")
                self.st["entries"].append({
                    "kind": "calc", "file": p, "label": f"{Path(p).stem} (TD-DFT)", "color": self.next_color(),
                    "visible": True, "own_norm": False, "nlo": self.st["nlo"], "nhi": self.st["nhi"],
                    "fwhm": 0.3, "shift": 0.0})
            except Exception as e:
                self.main.error(str(e))
        self.fill_table()
        self.timer.start()

    def add_esd(self):
        """ORCA-ESD-Spektrum (ESD(ABS), BASENAME.spectrum[.rootN]): fertig verbreitert, nur normiert vergleichbar.
        Einheit beim Hinzufügen bestimmen – die .inp/.out daneben wird nicht ins Projekt kopiert."""
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ov_add_esd"), self.main.settings.value("last_dir", ""),
                                             "ORCA ESD (*.spectrum *.spectrum.root*);;" + T("flt_all"))
        for p in ps:
            try:
                r = CALC.read_esd_spectrum(p)
                self.main.log_signal.emit("  " + T("ov_esd_read", name=Path(p).name, unit=r["unit"],
                                                   src=T("ov_esd_src_" + r["unit_src"])))
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                self.st["entries"].append({
                    "kind": "esd", "file": p, "label": f"{Path(p).name.split('.spectrum')[0]} (ESD)",
                    "color": self.next_color(), "visible": True, "own_norm": False, "nlo": self.st["nlo"],
                    "nhi": self.st["nhi"], "shift": 0.0, "unit": r["unit"]})
            except Exception as e:
                self.main.error(str(e))
        self.fill_table()
        self.timer.start()

    def esd_data(self, e):
        return self.cache(("esd", e["file"], e.get("unit")), lambda: CALC.read_esd_spectrum(e["file"], e.get("unit")))

    @staticmethod
    def sources(e):
        """Rechnungen eines TD-DFT-Eintrags: [dict(file, variant, weight)] (kombiniert: mehrere)."""
        return e.get("sources") or [{"file": e["file"], "variant": e.get("variant"), "weight": 1.0}]

    def calc_data(self, e):
        """Übergänge aller Rechnungen des Eintrags zusammengeführt -> (E [eV], f·Gewicht, Multiplizität).
        Verbreitert wird erst danach (gemeinsame FWHM/Verschiebung)."""
        Es, fs, mult = [], [], []
        for s_ in self.sources(e):
            r = self.cache(("tddft", s_["file"], s_.get("variant")),
                           lambda s_=s_: X.parse_tddft(s_["file"], s_.get("variant")))
            Es.append(np.asarray(r["E"], float))
            fs.append(np.asarray(r["f"], float) * float(s_.get("weight", 1.0)))
            mult += list(r.get("mult") or [None] * len(r["E"]))
        return np.concatenate(Es), np.concatenate(fs), mult

    @staticmethod
    def shared_states(a, b, tol_ev=0.002):
        """Anzahl erlaubter Zustände (f > 0), die in beiden Rechnungen mit gleicher Energie und Stärke
        vorkommen – Hinweis auf doppelt gerechnete Zustände."""
        (Ea, fa, _), (Eb, fb, _) = a, b
        return sum(1 for e, f in zip(Ea, fa)
                   if f > 0 and np.any((np.abs(Eb - e) < tol_ev) & (np.abs(fb - f) < 0.01 * f + 1e-4)))

    def update_combine(self):
        """„Kombinieren“ nur aktiv, wenn mindestens zwei TD-DFT-Einträge markiert sind."""
        rows = {i.row() for i in self.table.selectedIndexes()}
        ents = self.st["entries"]
        n = sum(1 for r in rows if 0 <= r < len(ents) and ents[r]["kind"] == "calc")
        self.btn_combine.setEnabled(n >= 2)

    def combine_selected(self):
        """Markierte TD-DFT-Einträge zu einem neuen Eintrag zusammenführen (Originale ausgeblendet)."""
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        ents = [self.st["entries"][r] for r in rows if self.st["entries"][r]["kind"] == "calc"]
        if len(ents) < 2:
            return self.main.error(T("ov_combine_need2"))
        srcs = [dict(s_) for e in ents for s_ in self.sources(e)]
        for s_ in srcs:
            s_["variant"] = s_.get("variant") or self.cache(
                ("tddft", s_["file"], None), lambda s_=s_: X.parse_tddft(s_["file"]))["variant"]
        # gleiche Zustände in zwei Rechnungen würden doppelt zählen -> warnen
        data = [self.calc_data({"sources": [s_]}) for s_ in srcs]
        for i in range(len(data)):
            for j in range(i + 1, len(data)):
                same = self.shared_states(data[i], data[j])
                if same:
                    msg = T("ov_combine_dup", a=Path(srcs[i]["file"]).name, b=Path(srcs[j]["file"]).name, n=same)
                    self.main.log_signal.emit("  " + msg)
                    QMessageBox.warning(self, T("ov_combine"), msg)     # nicht beim Zeichnen: sofort zeigen
        first = ents[0]
        for e in ents:
            e["visible"] = False
        self.st["entries"].append({
            "kind": "calc", "sources": srcs, "label": " + ".join(e["label"].replace(" (TD-DFT)", "") for e in ents)
            + " (TD-DFT)", "color": self.next_color(), "visible": True, "own_norm": first["own_norm"],
            "nlo": first["nlo"], "nhi": first["nhi"], "fwhm": first.get("fwhm", 0.3),
            "shift": first.get("shift", 0.0)})
        self.fill_table()
        self.table.selectRow(len(self.st["entries"]) - 1)
        self.timer.start()

    def chain(self):
        st = self.st
        ents = [e for e in st["entries"] if e.get("visible", True)]
        calc = [e for e in ents if e.get("kind") in ("calc", "esd")]
        return [(T("chain_baseline"), bool(st["baseline"])), (T("chain_norm"), st["mode"] == "norm"),
                (T("chain_broad"), any(e.get("kind") == "calc" for e in ents)),
                (T("chain_shift"), any(e.get("shift") for e in calc))]

    def move_selected(self, d):
        self.move_row(self.table.currentRow(), self.table.currentRow() + d)

    def move_row(self, src, dst):
        """Kurve an eine andere Stelle der Liste (Pfeilknöpfe, Ziehen mit der Maus)."""
        if move_item(self.st["entries"], src, dst):
            self.fill_table()
            self.table.selectRow(dst)
            self.timer.start()

    def remove_selected(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["entries"]):
            del self.st["entries"][r]
            self.fill_table()
            self.show_details()                    # sonst schreibt die nächste Änderung alte Werte in den Nachbarn
            self.timer.start()

    def fill_table(self):
        for e in self.st["entries"]:
            e.setdefault("uid", uuid.uuid4().hex[:8])     # stabiler Schlüssel fürs Layout (Reihenfolge änderbar)
        self._loading = True
        self.table.setRowCount(len(self.st["entries"]))
        for i, e in enumerate(self.st["entries"]):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, color_button(e["color"], lambda c, e=e: self._set_color(e, c), cell=True))
            it = QTableWidgetItem(T("ov_eps_linked") if e.get("link") == "eps" else
                                  {"exp": T("ov_exp"), "sec": "SEC", "secser": T("ov_sec_series"),
                                   "esd": "ESD"}.get(e["kind"], "TD-DFT"))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, it)
        self.table.resizeColumnToContents(0)
        self._loading = False
        self.update_combine()                             # Liste neu aufgebaut: Knopfzustand nachziehen

    def _set_color(self, e, c):
        e["color"] = c
        self.timer.start()

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["entries"][item.row()]
        if item.column() == 0:
            e["visible"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text()
        self.timer.start()

    def current_entry(self):
        r = self.table.currentRow()
        return self.st["entries"][r] if 0 <= r < len(self.st["entries"]) else None

    def show_details(self):
        e = self.current_entry()
        self.det.setEnabled(e is not None)
        self._loading = True
        for w in (self.cb_own, self.sp_elo, self.sp_ehi):
            w.setEnabled(self.cmb_ymode.currentData() == "norm")
        exp = e is not None and e["kind"] == "exp"
        calc = e is not None and e["kind"] == "calc"
        esd = e is not None and e["kind"] == "esd"
        linked = exp and e.get("link") == "eps"
        for w in (self.lbl_conc, self.ed_conc, self.cmb_unit, self.lbl_mw, self.ed_mw, self.lbl_d, self.sp_d):
            w.setVisible(exp or e is None)              # SEC: kein ε (Dünnschichtzelle)
            w.setEnabled(not linked)                    # verknüpft: Werte aus dem ε-Tab (dort ändern)
        for w in (self.lbl_eps, self.cmb_eps):
            w.setVisible(linked)
        combined = e is not None and bool(e.get("sources"))
        for w in (self.lbl_fwhm, self.sp_fwhm) + self.calc_color_widgets:
            w.setVisible(calc)
        for w in (self.lbl_shift, self.sp_shift):
            w.setVisible(calc or esd)
        for w in (self.lbl_esd_unit, self.cmb_esd_unit):
            w.setVisible(esd)
        for w in (self.lbl_soc, self.cmb_soc):
            w.setVisible(calc and not combined)
        for w in (self.lbl_weights, self.ed_weights):
            w.setVisible(combined)
        if e:
            self.lbl_estruct.setText(Path(e["structure"]).name if e.get("structure") else "–")
            self.cb_ecolor.setChecked(e.get("struct_color", True))
            self.cb_samelevel.setChecked(e.get("stack_with_prev", False))
            self.sp_scale.setValue(e.get("scale", 1.0))
            self.sp_offset.setValue(e.get("offset", 0.0))
            self.cmb_ls.setCurrentIndex(max(0, self.cmb_ls.findData(
                e.get("ls", "dashed" if e["kind"] in ("calc", "esd") else "solid"))))
            self.sp_lw.setValue(e.get("lw") or 0.0)
            self.cb_own.setChecked(e["own_norm"])
            self.show_norm_window(e if e["own_norm"] else None)  # ohne eigene: das geltende (globale) Fenster
            if linked:
                self.cmb_eps.clear()
                self.cmb_eps.addItem(T("ov_eps_auto"), None)
                for s_ in sorted(self.eps_series(e), key=lambda s_: s_["c"]):
                    self.cmb_eps.addItem(f"{s_['name']} ({s_['c']:g} {s_['unit']})", s_["name"])
                self.cmb_eps.setCurrentIndex(max(0, self.cmb_eps.findData(e.get("sample"))))
                e = self.eps_linked(e)[1]
            if exp:
                self.ed_conc.setText(f"{e['conc']:g}" if e.get("conc") else "")
                self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(e.get("unit", "mM"))))
                self.ed_mw.setText(f"{e['mw']:.2f}" if e.get("mw") else "")
                self.sp_d.setValue(e.get("d", 1.0))
            elif esd:
                self.sp_shift.setValue(e.get("shift", 0.0))
                self.cmb_esd_unit.setCurrentIndex(max(0, self.cmb_esd_unit.findData(e.get("unit"))))
            elif calc:
                self.sp_fwhm.setValue(e.get("fwhm", 0.3))
                self.sp_shift.setValue(e.get("shift", 0.0))
                self.sp_ccol_c.setValue(e.get("color_c", 1.0))
                self.sp_ccol_d.setValue(e.get("color_d", 1.0))
                self.update_calc_color(e)
                self.cmb_soc.clear()
                if combined:
                    self.ed_weights.setText(", ".join(f"{s_.get('weight', 1.0):g}" for s_ in e["sources"]))
                    self._loading = False
                    return
                try:
                    variants = self.cache(("tdv", e["file"]), lambda: X.tddft_variants(e["file"]))
                except Exception:
                    variants = []
                for v in variants or ["nosoc"]:
                    self.cmb_soc.addItem(X.variant_label(v), v)
                cur = e.get("variant") or (variants[0] if variants else "nosoc")
                if any(v.startswith("mr:") for v in variants) and e.get("variant") not in variants:
                    cur = X.parse_tddft(e["file"], e.get("variant"))["variant"]
                self.cmb_soc.setCurrentIndex(max(0, self.cmb_soc.findData(cur)))
                self.cmb_soc.setEnabled(len(variants) > 1)
        self._loading = False

    def detail_changed(self, *_):
        e = self.current_entry()
        if self._loading or e is None:
            return
        e.update(struct_color=self.cb_ecolor.isChecked(), stack_with_prev=self.cb_samelevel.isChecked())
        if self.sender() in (self.sp_elo, self.sp_ehi) and not self.cb_own.isChecked():
            self._loading = True                   # eigenen Bereich eingestellt = eigene Normierung
            self.cb_own.setChecked(True)
            self._loading = False
        elif self.sender() is self.cb_own:         # Felder zeigen das geltende Fenster: eigenes bzw. globales
            self.show_norm_window(e if self.cb_own.isChecked() else None)
        own = self.cb_own.isChecked()
        if own:                                    # ohne eigene bleiben die eigenen Grenzen gespeichert
            e.update(nlo=self.sp_elo.value(), nhi=self.sp_ehi.value())
        e.update(own_norm=own, scale=self.sp_scale.value(), offset=self.sp_offset.value(),
                 ls=self.cmb_ls.currentData(), lw=self.sp_lw.value() or None)
        if e.get("link") == "eps":
            e["sample"] = self.cmb_eps.currentData()
            self.show_details()                    # c/Einheit/d der gewählten Messung anzeigen
        elif e["kind"] == "exp":
            e.update(conc=parse_num(self.ed_conc.text()), unit=self.cmb_unit.currentData(),
                     mw=parse_num(self.ed_mw.text()), d=self.sp_d.value())
        elif e["kind"] == "esd":
            e.update(shift=self.sp_shift.value(), unit=self.cmb_esd_unit.currentData())
        elif e["kind"] == "calc":
            e.update(fwhm=self.sp_fwhm.value(), shift=self.sp_shift.value())
            if e.get("sources"):
                try:
                    # „0.7, 0.3“ (Anzeige) wie „0,7; 0,3“ oder „0,7 0,3“
                    ws = [float(x.replace(",", ".")) for x in re.split(r";\s*|,\s+|\s+", self.ed_weights.text().strip())
                          if x]
                except ValueError:
                    ws = []
                if len(ws) == len(e["sources"]) and all(w >= 0 for w in ws):
                    for s_, w in zip(e["sources"], ws):
                        s_["weight"] = w
                else:
                    self.ed_weights.setText(", ".join(f"{s_.get('weight', 1.0):g}" for s_ in e["sources"]))
            elif self.cmb_soc.currentData():
                e["variant"] = self.cmb_soc.currentData()
            e.update(color_c=self.sp_ccol_c.value(), color_d=self.sp_ccol_d.value())
            self.update_calc_color(e)
        self.timer.start()

    def calc_color(self, e):
        """Farbe einer Lösung aus dem TD-DFT-Spektrum: ε(λ) mit FWHM/Verschiebung des Eintrags verbreitert,
        A = ε·c·d (c in mM, Standard 1 mM in 1 cm) -> (Hex, außerhalb sRGB?)."""
        E, f, _ = self.calc_data(e)
        _, eps, _, _ = X.broaden(E, f, e.get("fwhm", 0.3), e.get("shift", 0.0), lam=COLOR.LAM)
        rgb, out_of_gamut = COLOR.absorbance_to_rgb(eps * e.get("color_c", 1.0) * 1e-3 * e.get("color_d", 1.0))
        return COLOR.to_hex(rgb), out_of_gamut

    def update_calc_color(self, e):
        try:
            hx, oog = self.calc_color(e)
        except Exception as ex:
            self.sw_ccol.setStyleSheet("")
            self.lbl_ccol_info.setText(f"{T('err_title')}: {ex}")
            return
        self.sw_ccol.setStyleSheet(f"background: {hx}; border: 1px solid #888; border-radius: 4px;")
        info = T("color_info", hex=hx, c=f"{e.get('color_c', 1.0):g}", unit="mM", d=f"{e.get('color_d', 1.0):g}")
        info += "\n" + T("ov_calc_color_hint")
        if oog:
            info += "\n" + T("color_gamut")
        self.lbl_ccol_info.setText(info)
        self.lbl_ccol_info.setStyleSheet(HINT_CSS)

    def collect(self):
        self.st.update(mode=self.cmb_ymode.currentData(), nlo=self.sp_nlo.value(), nhi=self.sp_nhi.value(),
                       baseline=self.cb_base.isChecked(), sticks=self.cb_sticks.isChecked(),
                       stick_mode=self.cmb_stick.currentData(), triplets=self.cb_trip.isChecked(), stack=self.cb_stack.isChecked(),
                       stack_gap=self.sp_gap.value(), y_axis=self.cmb_yaxis.currentData(),
                       curve_labels=self.cb_clabels.isChecked(), zero_lines=self.cb_zero.isChecked())
        e = self.current_entry()
        if e is not None and not e["own_norm"]:    # geerbtes Fenster in den Detailfeldern nachziehen
            self.show_norm_window(None)

    def show_norm_window(self, e):
        """Detailfelder Normierungsfenster: eigenes des Eintrags e bzw. (None) das globale, ohne Änderungssignal."""
        src = e if e is not None else self.st
        old, self._loading = self._loading, True
        self.sp_elo.setValue(src["nlo"])
        self.sp_ehi.setValue(src["nhi"])
        self._loading = old

    def choose_entry_structure(self):
        e = self.current_entry()
        if e is None or not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.main.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.main.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_entry_structure(self.main.import_file(p, PRJ.STRUCTURES))

    def set_entry_structure(self, p):
        e = self.current_entry()
        if e is None:
            return
        e["structure"] = p
        self.lbl_estruct.setText(Path(p).name if p else "–")
        self.timer.start()

    def choose_structure(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.main.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.set_structure(self.main.import_file(p, PRJ.STRUCTURES))

    def set_structure(self, p):
        self.st["structure"] = p
        self.lbl_struct.setText(Path(p).name if p else "–")
        self.timer.start()

    def hover_text(self, lam, val, name):
        if val is not None and self.st["mode"] == "eps":
            return T("hover_eps", lam=lam, eps=val, name=name)
        return super().hover_text(lam, val, name)

    # -- Abbildung --------------------------------------------------------------
    @staticmethod
    def stack_levels(vis):
        """uid -> Stapelebene (0 = oben). „Gleiche Ebene wie darüber“ teilt die Ebene der Vorgängerkurve,
        z. B. Messung und TD-DFT derselben Verbindung."""
        out, lev = {}, -1
        for i, e in enumerate(vis):
            if i == 0 or not e.get("stack_with_prev"):
                lev += 1
            out[e["uid"]] = lev
        return out

    LS = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["entries"] if e["visible"]]
        if not vis:
            return None
        for e in vis:
            e.setdefault("uid", uuid.uuid4().hex[:8])
        cfg = self.base_cfg()
        eps_mode, abs_mode = st["mode"] == "eps", st["mode"] == "abs"
        mode = st.get("stick_mode", "max")
        stack = st.get("stack", False)
        if mode == "faxis" and (stack or any(e.get("offset") for e in vis)):   # f-Achse beginnt bei y = 0
            mode = "band"
            self.add_note(T("ov_faxis_stack"))
        levels = self.stack_levels(vis) if stack else {}
        n_lev = max(levels.values(), default=0) + 1
        gap = st.get("stack_gap", 1.0)

        def total_off(e):                        # oberster Eintrag der Liste = oberste Kurve
            return e.get("offset", 0.0) + ((n_lev - 1 - levels[e["uid"]]) * gap if stack else 0.0)
        curves, sticks, exp_x, calc_x, f_scales = [], [], [], [], []
        tagged = set()
        for e in vis:
            lo, hi = (e["nlo"], e["nhi"]) if e["own_norm"] else (st["nlo"], st["nhi"])
            sc, off = e.get("scale", 1.0), total_off(e)
            ls = self.LS.get(e.get("ls") or ("dashed" if e["kind"] in ("calc", "esd") else "solid"), "-")
            if e["kind"] == "esd":
                if eps_mode or abs_mode:             # ESD-Intensität ohne Einheit: nur normiert
                    self.add_note(T("ov_esd_norm_only", name=e["label"]))
                    continue
                r = self.esd_data(e)
                x = CALC.esd_shift(r["nm"], e.get("shift", 0.0))
                win = (x >= min(lo, hi)) & (x <= max(lo, hi))
                # wie TD-DFT: nur Ausläufer im Fenster (< 1 % des Maximums) nicht hochskalieren
                ok = win.any() and r["total"][win].max() >= 0.01 * r["total"].max()
                y = X.normalize(x, r["total"], lo, hi) if ok else None
                if y is None:
                    self.add_note(T("ov_no_signal", name=e["label"], lo=lo, hi=hi))
                    continue
                band = x[y > 0.01 * np.nanmax(y)]          # Datei reicht weit ins UV (72 nm): x-Bereich nach Signal
                calc_x.append(np.array([band.min(), band.max()]) if band.size else x)
                c = {"x": x, "y": y * sc + off, "val": y * sc, "color": e["color"], "label": e["label"], "ls": ls}
                if e.get("lw"):
                    c["lw"] = e["lw"]
                lev = levels.get(e["uid"], len(curves))
                if lev not in tagged:
                    c["tag"] = e["label"]
                    tagged.add(lev)
                curves.append(c)
                continue
            if e["kind"] == "secser":
                if eps_mode:                         # Dünnschichtzelle: Schichtdicke/Konzentration unbekannt
                    self.add_note(T("ov_sec_no_eps", name=e["label"]))
                    continue
                bcfg = dict(cfg, baseline_nm="auto", baseline_mode="simple", conc_unit="mM") if st["baseline"] else None
                ser = self.sec_series_curves(e, lo, hi, bcfg, norm=not abs_mode)
                if not ser:
                    self.add_note(T("ov_no_signal", name=e["label"], lo=lo, hi=hi))
                    continue
                for sc_c in ser:
                    c = {"x": sc_c["x"], "y": sc_c["val"] * sc + off, "val": sc_c["val"] * sc,
                         "color": sc_c["color"], "label": sc_c["label"], "ls": ls}
                    if sc_c["main"] and e.get("lw"):
                        c["lw"] = e["lw"]
                    elif sc_c["lw"]:
                        c["lw"] = sc_c["lw"]
                    curves.append(c)
                exp_x.append(ser[0]["x"])
                lev = levels.get(e["uid"], len(curves))
                if lev not in tagged:
                    curves[-1]["tag"] = e["label"]
                    tagged.add(lev)
                continue
            if e["kind"] in ("exp", "sec"):
                if e["kind"] == "sec":
                    if eps_mode:                     # Dünnschichtzelle: Schichtdicke/Konzentration unbekannt
                        self.add_note(T("ov_sec_no_eps", name=e["label"]))
                        continue
                    s_ = self.sec_spectrum(e)
                elif e.get("link") == "eps":
                    s_, e = self.eps_linked(e)
                    if s_ is None:
                        self.add_note(T("ov_eps_gone", name=e["label"]))
                        continue
                else:
                    s_ = self.sample(e["file"], e["sample"])
                if s_ is None:
                    continue
                x, y = s_["x"].copy(), s_["y"].copy()
                if st["baseline"]:
                    tmp = [{"x": x, "y": y, "c": 1.0}]
                    bcfg = dict(cfg, baseline_nm="auto", baseline_mode="simple", conc_unit="mM")
                    core.apply_baseline(tmp, bcfg)
                    y = tmp[0]["y"]
                if eps_mode:
                    fac = (1 / e["mw"] if e.get("mw") else None) if e.get("unit") == "mg/mL" \
                        else core.CONC_TO_M.get(e.get("unit", "mM"))
                    if not (e.get("conc") and fac):
                        self.add_note(T("ov_need_conc", name=e["label"]))
                        continue
                    y = y / (e["conc"] * fac * e.get("d", 1.0)) / 1000.0
                elif not abs_mode:
                    y = X.normalize(x, y, lo, hi)
                    if y is None:
                        self.add_note(T("ov_no_signal", name=e["label"], lo=lo, hi=hi))
                        continue
                exp_x.append(x)
                lab = e["label"]
                if e["kind"] == "sec":                   # AgNO₃ -> Mathtext-Index (Glyphen fehlen oft)
                    from elucida.tabs import cv as CV
                    lab = CV.axis_ref(lab)
                c = {"x": x, "y": y * sc + off, "val": y * sc, "color": e["color"], "label": lab, "ls": ls}
            else:
                if abs_mode:                             # Rechnung: Absorbanz nur mit c und d -> ε/normiert
                    self.add_note(T("ov_calc_no_abs", name=e["label"]))
                    continue
                E, f, mult = self.calc_data(e)
                lam, eps, sl, sh = X.broaden(E, f, e.get("fwhm", 0.3), e.get("shift", 0.0))
                trip = np.array([m == 3 for m in mult], bool)
                only_trip = st.get("triplets") and trip.any() and not (np.asarray(f) > 0).any()
                # Kurve und Striche immer mit DEMSELBEN Faktor: jeder Strich = Höhe seiner eigenen
                # Gaußbande, die Kurve ist deren Summe. Gewählt wird nur die Bezugsgröße.
                if eps_mode or only_trip:                # nur Tripletts (alle f = 0): Marken ohne Kurve
                    k = 1 / 1000.0                       # ε in 10³ M⁻¹ cm⁻¹
                else:
                    sel = (lam >= min(lo, hi)) & (lam <= max(lo, hi))
                    if not sel.any() or not eps[sel].max() > 0 or not eps[sel].max() >= 0.01 * eps.max():
                        # nur Gauß-Ausläufer im Fenster (oder alle f = 0)
                        self.add_note(T("ov_no_signal", name=e["label"], lo=lo, hi=hi))
                        continue
                    band_max = eps[sel].max()
                    ssel = (sl >= min(lo, hi)) & (sl <= max(lo, hi))
                    stick_max = sh[ssel].max() if ssel.any() and sh[ssel].max() > 0 else sh.max()
                    k = 1 / (stick_max if mode == "max" else band_max)
                y, h = eps * k, sh * k
                c = {"x": lam, "y": y * sc + off, "val": y * sc, "color": e["color"], "label": e["label"], "ls": ls}
                calc_x.append(sl if st.get("triplets") or trip.all() else sl[~trip])   # ohne ausgeblendete Tripletts
                if st["sticks"]:
                    sticks.append({"x": sl[~trip], "h": (h * sc)[~trip], "color": e["color"], "base": off})
                    fa, hs = np.asarray(f, float), h * sc
                    ok = ~trip & (fa > 0) & (hs > 0)
                    if mode == "faxis" and ok.any():
                        # f rechts nur als zweite Skala: Strich = Höhe seiner Bande (derselbe Faktor wie die
                        # Kurve), f/Höhe ist je Eintrag konstant (σ/C/k)
                        f_scales.append(float(np.median(fa[ok] / hs[ok])))
                if st.get("triplets") and trip.any():
                    # formal spinverboten (f = 0): gestrichelte Marken fester Höhe, kein Beitrag zur Kurve
                    ht = 0.15 * sc * (float(np.nanmax(y)) if eps_mode and np.nanmax(y) > 0 else 1.0)
                    sticks.append({"x": sl[trip], "h": np.full(int(trip.sum()), ht), "color": e["color"],
                                   "base": off, "ls": "dashed"})
            if e.get("lw"):
                c["lw"] = e["lw"]
            lev = levels.get(e["uid"], len(curves))
            if lev not in tagged:                # Name an der Kurve: nur die erste Kurve je Ebene
                c["tag"] = e["label"]
                tagged.add(lev)
            curves.append(c)
        if not curves:
            return None
        if f_scales:                             # eine f-Achse passt nur bei gleichem Maßstab aller Rechnungen
            if max(f_scales) <= min(f_scales) * (1 + 1e-3):           # 0,1 %: unter der Strichstärke
                cfg["f_axis"] = f_scales[0]
            else:
                self.add_note(T("ov_faxis_mixed"))
        y_axis = st.get("y_axis", "auto")
        cfg["y_axis"] = ("no_numbers" if stack else "numbers") if y_axis == "auto" else y_axis
        cfg["curve_labels"] = bool(st.get("curve_labels"))
        cfg["legend"] = not cfg["curve_labels"]
        if stack and st.get("zero_lines"):
            cfg["zero_lines"] = [lev * gap for lev in range(n_lev)]
        if st["x_auto"]:
            if exp_x:
                xs = np.concatenate(exp_x)
                cfg["xlim"] = [float(xs.min()), float(xs.max())]
            else:
                sx = np.concatenate(calc_x) if calc_x else np.array([300.0, 600.0])
                cfg["xlim"] = [max(150.0, sx.min() - 80), sx.max() + 120]
        else:
            cfg["xlim"] = [st["x_min"], st["x_max"]]
        lo_x, hi_x = cfg["xlim"]
        ymin = min(0.0, min(float(np.nanmin(c["y"][(c["x"] >= lo_x) & (c["x"] <= hi_x)], initial=0))
                            for c in curves))
        if st["ymax"] > 0:
            cfg["ylim"] = [ymin, st["ymax"]]
        elif eps_mode or abs_mode:
            mx = max(np.nanmax(c["y"][(c["x"] >= lo_x) & (c["x"] <= hi_x)], initial=0) for c in curves)
            cfg["ylim"] = [ymin, 1.1 * mx if mx > 0 else 1]
        else:                                    # normiert: Platz für skalierte/versetzte Kurven
            mx = max(np.nanmax(c["y"][(c["x"] >= lo_x) & (c["x"] <= hi_x)], initial=0) for c in curves)
            mx = max([mx] + [float(np.max(sk["h"][(sk["x"] >= lo_x) & (sk["x"] <= hi_x)] + sk.get("base", 0.0),
                                          initial=0)) for sk in sticks if not sk.get("axis2")])
            cfg["ylim"] = [ymin, max(1.1, 1.05 * mx,      # stärkere Banden ausserhalb des Normierungsbereichs
                                     max(1.1 * e.get("scale", 1.0) + total_off(e) for e in vis))]
        cfg["ylabel"] = (r"$\varepsilon$ [10$^3$ M$^{-1}$ cm$^{-1}$]" if eps_mode else
                         "absorbance [a.u.]" if abs_mode else "normalized absorbance [a.u.]")
        imgs = []
        if st.get("structure") and Path(st["structure"]).exists():
            imgs.append({"file": st["structure"], "id": "struktur", "width": st.get("struct_w", 20) / 100,
                         "prefer": "top", "_asset": self.structure_asset(st["structure"])})
        for e in vis:                                   # Struktur pro Spektrum, optional in Kurvenfarbe
            p = e.get("structure")
            if p and Path(p).exists():
                color = e["color"] if e.get("struct_color", True) else None
                try:
                    asset = self.structure_asset(p, color)
                except Exception as ex:
                    self.add_note(f"{Path(p).name}: {ex}")
                    continue
                imgs.append({"file": p, "id": "struktur_" + e.get("uid", "x"),
                             "width": st.get("struct_w", 20) / 100, "prefer": "top", "_asset": asset})
        cfg["images"] = imgs
        return cfg, curves, [], sticks


# ----------------------------------------------------------------------------
INNER_FILTER_A = 0.1          # darüber verzerrt der Innenfiltereffekt Emissionsspektren und Quantenausbeuten


def stokes_cm(lam_abs, lam_em):
    """Stokes-Verschiebung Δν̃ = 1/λabs − 1/λem in cm⁻¹ (λ in nm)."""
    if not (lam_abs and lam_em):
        return None
    return 1e7 / lam_abs - 1e7 / lam_em


def fmt_stokes(v):
    """Auf 10 cm⁻¹ runden: Peaklagen aus Spektren mit ~1 nm Raster sind nicht genauer."""
    return f"{round(v, -1):.0f}".replace("-", "\u2212")


def color_name(c) -> str:
    """Grober englischer Farbname für Bildunterschriften („blue“, „red“ …) aus einer Matplotlib-Farbe."""
    import colorsys
    from matplotlib.colors import to_rgb
    try:
        r, g, b = to_rgb(c)
    except ValueError:
        return str(c)
    h, l, s_ = colorsys.rgb_to_hls(r, g, b)
    if s_ < 0.2 or l < 0.12 or l > 0.92:
        return "black" if l < 0.3 else "grey" if l < 0.85 else "white"
    hue = h * 360
    for lim, name in ((15, "red"), (45, "orange"), (70, "yellow"), (160, "green"), (195, "cyan"), (255, "blue"),
                      (290, "purple"), (335, "magenta"), (360, "red")):
        if hue < lim:
            return name
    return "red"


class FluoTab(FigureTab):
    STATE_KEY = "fluorescence"
    GUIDE, GUIDE_ACTION = "fluo", None
    TEXT_OPTS = ("fonts", "greek", "labels", "label_size", "axes_frame", "struct_frame")
    SI_CAPTION = "Fluorescence spectra of {name}."
    CAP_FIELDS = ("solvent", "conc", "cuvette")
    RESET_KEEP = ("abs_file", "abs_sample", "em_file", "em_sample", "ex", "eps", "structure", "photo_day", "photo_uv",
                  "esd_file", "esd_unit", "esd_shift")
    DEFAULT_STATE = dict(COMMON_DEFAULTS, abs_file=None, abs_sample=None, em_file=None, em_sample=None,
                         ex=350.0, alo=300.0, ahi=500.0, eps="", mask=False, c_abs="#1f9bff",
                         c_em="#e8231b", structure=None, photo_day=None, bg_day="auto", photo_uv=None,
                         bg_uv="none", ymax=1.2, struct_w=20.0, photo_w=30.0, stokes_label=False,
                         esd_file=None, esd_unit=None, esd_shift=0.0)    # berechnete Emission (ORCA ESD(FLUOR))


    def arrange(self):
        super().arrange()
        self.fold(self.group_titled("fl_images"), "images")
    def build_controls(self):
        st = self.st
        g = QGroupBox(T("fl_data"))
        f = make_form(g)
        self.w_abs = self._file_row(f, T("fl_abs"), "abs")
        self.w_em = self._file_row(f, T("fl_em"), "em")
        self.lbl_esd = self._esd_row(f)
        self.sp_ex = QDoubleSpinBox(decimals=0, minimum=150, maximum=1500, value=st["ex"], suffix=" nm")
        self.sp_ex.setToolTip(T("fl_ex_tip"))
        f.addRow(T("fl_ex"), self.sp_ex)
        self.cb_mask = QCheckBox(T("fl_mask"))
        self.cb_mask.setProperty("chip_here", True)      # gehört zum Feld darüber
        self.cb_mask.setChecked(st["mask"])
        f.addRow(self.cb_mask)
        row = QHBoxLayout()
        self.sp_alo = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=st["alo"])
        self.sp_ahi = QDoubleSpinBox(decimals=0, minimum=100, maximum=3500, value=st["ahi"])
        for w in (self.sp_alo, QLabel("–"), self.sp_ahi):
            row.addWidget(w)
            w.setToolTip(T("fl_abs_window_tip"))
        f.addRow(T("fl_abs_window"), row)
        self.ed_eps = QLineEdit(st["eps"])
        self.ed_eps.setPlaceholderText(T("fl_eps_ph"))
        self.ed_eps.setToolTip(T("fl_eps_tip"))
        f.addRow("ε [M⁻¹ cm⁻¹]", self.ed_eps)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("fl_abs")))
        row.addWidget(color_button(st["c_abs"], lambda c: self._set("c_abs", c), small=True))
        row.addWidget(QLabel(T("fl_em")))
        row.addWidget(color_button(st["c_em"], lambda c: self._set("c_em", c), small=True))
        row.addStretch(1)
        f.addRow(T("ov_color"), row)
        self.cb_stokes = QCheckBox(T("fl_stokes_label"))
        self.cb_stokes.setChecked(st.get("stokes_label", False))
        self.cb_stokes.toggled.connect(self.changed)
        f.addRow(self.cb_stokes)
        self.lbl_info = STYLE.HintLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.lbl_info)                              # mittig über die ganze Karte
        self.info = {}
        self.lv.addWidget(g)

        g = QGroupBox(T("fl_images"))
        f = make_form(g)
        self.lbl_struct = self._img_row(f, T("structure"), "structure", T("flt_struct"))
        self.size_spin(f, "struct_w", "image_struktur")
        self.lbl_day = self._img_row(f, T("fl_photo_day"), "photo_day", T("flt_photo"))
        self.cmb_bg_day = self._bg_combo(f, "bg_day")
        self.lbl_uv = self._img_row(f, T("fl_photo_uv"), "photo_uv", T("flt_photo"))
        self.cmb_bg_uv = self._bg_combo(f, "bg_uv")
        self.size_spin(f, "photo_w", "image_fotos")
        self.lv.addWidget(g)
        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export
        for w in (self.sp_ex, self.sp_alo, self.sp_ahi):
            w.valueChanged.connect(self.changed)
        self.cb_mask.toggled.connect(self.changed)
        self.ed_eps.editingFinished.connect(self.changed)

    def _set(self, k, v):
        self.st[k] = v
        self.timer.start()

    def _file_row(self, form, label, which):
        row = QHBoxLayout()
        lbl = QLabel(Path(self.st[f"{which}_file"]).name if self.st[f"{which}_file"] else "–")
        b = QPushButton(T("choose"))
        cmb = QComboBox()
        row.addWidget(lbl, 1)
        row.addWidget(b)
        form.addRow(label, row)
        form.addRow("", cmb)

        def fill():
            cmb.blockSignals(True)
            cmb.clear()
            p = self.st[f"{which}_file"]
            if p and Path(p).exists():
                for s_ in self.samples(p):
                    cmb.addItem(s_["name"], s_["key"])
                i = cmb.findData(self.st[f"{which}_sample"])
                cmb.setCurrentIndex(max(0, i))
                self.st[f"{which}_sample"] = cmb.currentData()
            cmb.blockSignals(False)

        def choose():
            if not self.main.ensure_project():
                return
            p, _ = QFileDialog.getOpenFileName(self, label, self.main.settings.value("last_dir", ""),
                                               f"{T('flt_csv')};;{T('flt_all')}")
            if p:
                try:
                    p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                    self.samples(p)
                except Exception as e:
                    return self.main.error(f"{Path(p).name}: {e}")
                self.st[f"{which}_file"], self.st[f"{which}_sample"] = p, None
                lbl.setText(Path(p).name)
                fill()
                self._auto_ex(which)
                self.timer.start()

        def picked(_):
            self.st[f"{which}_sample"] = cmb.currentData()
            self._auto_ex(which)
            self.timer.start()
        b.clicked.connect(choose)
        cmb.currentIndexChanged.connect(picked)
        fill()
        return lbl, cmb

    def _esd_row(self, form):
        """Berechnete Emission (ORCA ESD(FLUOR), .spectrum): Datei, Verschiebung in eV, Einheit der Datei."""
        row = QHBoxLayout()
        lbl = QLabel(Path(self.st["esd_file"]).name if self.st.get("esd_file") else "–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        row.addWidget(lbl, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        form.addRow(T("fl_esd"), row)
        row2 = QHBoxLayout()
        sp = QDoubleSpinBox(decimals=2, minimum=-3, maximum=3, singleStep=0.05, value=self.st.get("esd_shift", 0.0),
                            suffix=" eV")
        sp.setToolTip(T("fl_esd_shift_tip"))
        cmb = QComboBox()
        for u in CALC.ESD_UNITS:
            cmb.addItem("cm⁻¹" if u == "cm-1" else u, u)
        cmb.setToolTip(T("ov_esd_unit_tip"))
        cmb.setCurrentIndex(max(0, cmb.findData(self.st.get("esd_unit"))))
        row2.addWidget(sp, 1)
        row2.addWidget(cmb)
        form.addRow(T("ov_shift"), row2)
        self.esd_widgets = (sp, cmb)

        def enable():
            for w_ in (sp, cmb):
                w_.setEnabled(bool(self.st.get("esd_file")))

        def choose():
            if not self.main.ensure_project():
                return
            p, _ = QFileDialog.getOpenFileName(self, T("fl_esd"), self.main.settings.value("last_dir", ""),
                                               "ORCA ESD (*.spectrum *.spectrum.root*);;" + T("flt_all"))
            if not p:
                return
            try:
                r = CALC.read_esd_spectrum(p)            # Einheit hier: die .inp/.out daneben wird nicht kopiert
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
            except Exception as e:
                return self.main.error(f"{Path(p).name}: {e}")
            self.main.log_signal.emit("  " + T("ov_esd_read", name=Path(p).name, unit=r["unit"],
                                               src=T("ov_esd_src_" + r["unit_src"])))
            self.st.update(esd_file=p, esd_unit=r["unit"])
            lbl.setText(Path(p).name)
            cmb.blockSignals(True)
            cmb.setCurrentIndex(max(0, cmb.findData(r["unit"])))
            cmb.blockSignals(False)
            enable()
            self.timer.start()

        def remove():
            self.st["esd_file"] = None
            lbl.setText("–")
            enable()
            self.timer.start()
        b1.clicked.connect(choose)
        b2.clicked.connect(remove)
        sp.valueChanged.connect(lambda v: self._set("esd_shift", v))
        cmb.currentIndexChanged.connect(lambda _: self._set("esd_unit", cmb.currentData()))
        enable()
        return lbl

    def esd_curve(self):
        """Berechnete Emission -> (nm, auf 1 normiert) oder None."""
        p = self.st.get("esd_file")
        if not p or not Path(p).exists():
            return None
        r = self.cache(("esd", p, self.st.get("esd_unit")), lambda: CALC.read_esd_spectrum(p, self.st.get("esd_unit")))
        m = np.nanmax(r["total"])
        return (CALC.esd_shift(r["nm"], self.st.get("esd_shift", 0.0)), r["total"] / m) if m > 0 else None

    def _auto_ex(self, which):
        """λex aus den Gerätemetadaten der Emissionsmessung übernehmen (Eclipse CSV/FBSW)."""
        if which != "em" or not self.st.get("em_file"):
            return
        s_ = self.sample(self.st["em_file"], self.st["em_sample"])
        if s_ and s_.get("ex") and hasattr(self, "sp_ex"):
            self.st["ex"] = float(s_["ex"])
            self.sp_ex.blockSignals(True)
            self.sp_ex.setValue(self.st["ex"])
            self.sp_ex.blockSignals(False)

    def _img_row(self, form, label, key, flt):
        row = QHBoxLayout()
        lbl = QLabel(Path(self.st[key]).name if self.st[key] else "–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))

        def choose():
            if not self.main.ensure_project():
                return
            p, _ = QFileDialog.getOpenFileName(self, label, self.main.settings.value("last_img_dir", ""),
                                               f"{flt};;{T('flt_all')}")
            if p:
                self.main.settings.setValue("last_img_dir", str(Path(p).parent))
                p = self.main.import_file(p, PRJ.STRUCTURES)
                self.st[key] = p
                lbl.setText(Path(p).name)
                self.timer.start()

        def remove():
            self.st[key] = None
            lbl.setText("–")
            self.timer.start()
        b1.clicked.connect(choose)
        b2.clicked.connect(remove)
        row.addWidget(lbl, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        form.addRow(label, row)
        return lbl

    def _bg_combo(self, form, key):
        cmb = QComboBox()
        for k in ("auto", "isnet", "grabcut", "border", "none"):
            cmb.addItem(T({"auto": "bg_auto", "isnet": "bg_isnet", "grabcut": "bg_grabcut",
                           "border": "bg_border", "none": "bg_off"}[k]), k)
        cmb.setCurrentIndex(cmb.findData(self.st[key]))
        cmb.currentIndexChanged.connect(lambda _: self._set(key, cmb.currentData()))
        form.addRow(T("bg_method"), cmb)
        return cmb

    def collect(self):
        self.st.update(ex=self.sp_ex.value(), mask=self.cb_mask.isChecked(), alo=self.sp_alo.value(),
                       ahi=self.sp_ahi.value(), eps=self.ed_eps.text().strip(),
                       stokes_label=self.cb_stokes.isChecked())

    def si_caption(self, name):
        """Vergleich Absorption/Emission wie in der SI üblich: „Normalized UV-Vis absorption (blue) and fluorescence
        emission spectra (red; λex = 350 nm) of X in THF, measured in 1 cm quartz cuvettes.“ Farben aus dem Bild,
        Küvette aus dem Feld (leer = 1 cm, übliche Fluoreszenzküvette)."""
        from elucida.si.lines import chem_html
        st = self.st
        n = "<b>" + html.escape(name) + "</b>"
        ab, em = bool(st.get("abs_file")), bool(st.get("em_file"))
        ex = f"λ<sub>ex</sub> = {st['ex']:g} nm"
        if ab and em:
            h = (f"Normalized UV-Vis absorption ({color_name(st['c_abs'])}) and fluorescence emission spectra "
                 f"({color_name(st['c_em'])}; {ex}) of {n}")
        elif em:
            h = f"Normalized fluorescence emission spectrum ({ex}) of {n}"
        else:
            h = f"Normalized UV-Vis absorption spectrum of {n}"
        if st.get("cap_solvent"):
            h += " in " + chem_html(st["cap_solvent"])
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        cuv = (st.get("cap_cuvette") or "1 cm").strip()
        h += ", measured in " + chem_html(cuv) + " quartz cuvettes."
        if st.get("esd_file"):
            sh = st.get("esd_shift", 0.0)
            h += (" Dashed: calculated vibronic emission spectrum"
                  + (f", shifted by {sh:+.2f} eV".replace("-", "−") if sh else "") + ".")
        return h

    def kpis(self):
        i = getattr(self, "info", None) or {}
        out = [("λem", f"{i['lam_em']:.0f} nm")] if i.get("lam_em") else []
        if i.get("stokes_cm") is not None:
            out.append(("Stokes", f"{fmt_stokes(i['stokes_cm'])} cm⁻¹"))
        return out

    def show_info(self, pa, pe, a_ex):
        """Kennwerte unter den Daten: λabs, λem, Stokes-Verschiebung, A(λex) mit Innenfilter-Hinweis."""
        self.info = {"lam_abs": pa, "lam_em": pe, "a_ex": a_ex,
                     "stokes_cm": stokes_cm(pa, pe), "stokes_nm": (pe - pa) if pa and pe else None}
        lines, warn = [], False
        if self.info["stokes_cm"] is not None:
            lines.append(T("fl_stokes", cm=fmt_stokes(self.info["stokes_cm"]), nm=self.info["stokes_nm"]))
        if a_ex is not None:
            lines.append(T("fl_a_ex", ex=self.st["ex"], a=a_ex))
            if a_ex > INNER_FILTER_A:
                lines.append(T("fl_inner_filter", lim=INNER_FILTER_A))
                warn = True
        if hasattr(self, "lbl_info"):
            self.lbl_info.setText("  ·  ".join(lines))
            self.lbl_info.setStyleSheet(WARN_CSS if warn else HINT_CSS)

    def figure_spec(self):
        st = self.st
        a = self.sample(st["abs_file"], st["abs_sample"]) if st["abs_file"] else None
        em = self.sample(st["em_file"], st["em_sample"]) if st["em_file"] else None
        esd = self.esd_curve()
        if a is None and em is None and esd is None:
            return None
        cfg = self.base_cfg()
        curves, labels = [], []
        pa = pe = a_ex = None
        if a is not None:
            ya = X.normalize(a["x"], a["y"], st["alo"], st["ahi"])
            if ya is None:
                self.add_note(T("ov_no_signal", name=a["name"], lo=st["alo"], hi=st["ahi"]))
                a = None
        if a is not None:
            curves.append({"x": a["x"], "y": ya, "color": st["c_abs"], "label": None})
            pa = X.peak_in(a["x"], ya, st["alo"], st["ahi"])
            xa = np.asarray(a["x"], float)
            if xa.min() <= st["ex"] <= xa.max():         # Rohabsorbanz bei λex (vor dem Normieren)
                o = np.argsort(xa)
                a_ex = float(np.interp(st["ex"], xa[o], np.asarray(a["y"], float)[o]))
            if pa:
                txt = f"λ$_{{\\mathrm{{abs}}}}$ =  {pa:.0f} nm"
                eps = parse_num(st["eps"])
                if eps:
                    txt += f"\nε =  {eps:.0f} cm$^{{-1}}$ M$^{{-1}}$"
                labels.append({"key": "label_abs", "text": txt, "lam": pa})
        if em is not None:
            y = em["y"].astype(float).copy()
            if st["mask"]:
                for c in (st["ex"], 2 * st["ex"]):
                    y[np.abs(em["x"] - c) <= 12] = np.nan
            ye = X.normalize(em["x"], y, float(np.nanmin(em["x"])), float(np.nanmax(em["x"])))
            if ye is None:
                ye = y
            curves.append({"x": em["x"], "y": ye, "color": st["c_em"], "label": None})
            pe = X.peak_in(em["x"], ye, float(np.nanmin(em["x"])), float(np.nanmax(em["x"])))
            if pe:
                txt = f"λ$_{{\\mathrm{{em}}}}$ =  {pe:.0f} nm"
                if st.get("stokes_label") and pa:
                    txt += f"\nΔ$\\tilde{{\\nu}}$ =  {fmt_stokes(stokes_cm(pa, pe))} cm$^{{-1}}$"
                labels.append({"key": "label_em", "text": txt, "lam": pe})
        self.show_info(pa, pe, a_ex)
        if esd is not None:                              # gestrichelt in der Emissionsfarbe; x-Bereich nach Messung
            band = esd[0][esd[1] > 0.01]
            curves.append({"x": esd[0], "y": esd[1], "color": st["c_em"], "label": None, "ls": "--",
                           "_xr": np.array([band.min(), band.max()]) if band.size else esd[0]})
        xs = np.concatenate([c["x"] for c in curves if "_xr" not in c] or [c["_xr"] for c in curves])
        cfg["xlim"] = [float(xs.min()), float(xs.max())] if st["x_auto"] else [st["x_min"], st["x_max"]]
        cfg["ylim"] = [0, st["ymax"] if st["ymax"] > 0 else 1.2]
        cfg["ylabel"] = "normalized intensity [a.u.]"
        imgs = []
        if st.get("structure") and Path(st["structure"]).exists():
            imgs.append({"file": st["structure"], "id": "struktur", "width": st.get("struct_w", 20) / 100,
                         "prefer": "top", "_asset": self.structure_asset(st["structure"])})
        day = self.photo_asset(st["photo_day"], st["bg_day"]) if st.get("photo_day") else None
        uv = self.photo_asset(st["photo_uv"], st["bg_uv"]) if st.get("photo_uv") else None
        if day and uv:
            pair = X.compose_photo_pair(day["rgba"], uv["rgba"], f"{st['ex']:g} nm")
            imgs.append({"file": "pair", "id": "fotos", "width": st.get("photo_w", 30) / 100, "prefer": "bottom-right",
                         "_asset": {"rgba": pair, "pdf": None, "clip": None}})
        elif day or uv:
            one = day or uv
            imgs.append({"file": "photo", "id": "fotos", "width": st.get("photo_w", 30) / 300, "prefer": "bottom-right",
                         "_asset": {"rgba": one["rgba"], "pdf": None, "clip": None}})
        cfg["images"] = imgs
        return cfg, curves, labels, []
