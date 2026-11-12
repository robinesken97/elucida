"""elucida/tabs/dft_pages.py - Reiter des DFT-Tabs neben „Abbildung“: Energieprofil (Stufen aus Opt/Freq, optional
Einzelpunkt; IRC) und NICS (Gaussian-NMR mit Geisteratomen). Zustand im DFT-Zustand: `profile`, `nics`.

Energieprofil: G = E(SP) + (G − E_el)(Opt/Freq), H analog, ΔE = E(SP); Einzelpunkt über gleiche Atome/Koordinaten
(± 0.02 Å, nie über Dateinamen). Haben einige Spezies einen Einzelpunkt, fallen die übrigen weg (nie mischen).
IRC (ORCA): nur ΔE_el; x = Reaktionskoordinate [Å] = aufsummierte kartesische Abstände aufeinanderfolgender Bilder
der Trajektorie (TS = 0, rückwärts negativ) oder eine Bindungslänge aus „IRC PATH SUMMARY“.
NICS = −σ_iso, NICSzz = −n·σ·n mit n = Normale der Ebene durch die Schweratome in der Nähe des Bq.
"""
from __future__ import annotations
import elucida

import csv
import html
import os
import re
import uuid
from pathlib import Path

import numpy as np
from elucida.app.canvas_theme import register as register_canvas
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QListWidget, QMenu, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS
from elucida.formats.calc import parse_irc, parse_nics, read_text, read_xyz
from elucida.tabs import base as TABS

HARTREE_KCAL = 627.5094740631            # kcal/mol je Hartree (CODATA 2018)
LEVEL_W = 0.35                           # halbe Stufenbreite (Schritte)
# Stilvorlagen des Stufenbilds (Schritt Darstellung): setzen nur Stil, nie Lage oder Werte
PRESETS = {"classic": dict(connector_style="--", line_width=2.2, connector_width=.8, frame=True, path_colors=False, color="black"),
           "curves": dict(connector_style="curve", line_width=2.2, connector_width=1.0, frame=True, path_colors=False, color="black"),
           "colour": dict(connector_style="--", line_width=2.6, connector_width=1.0, frame=True, path_colors=True),
           "minimal": dict(connector_style=":", line_width=1.6, connector_width=.7, frame=False, path_colors=False, color="black")}
LINE_KEYS = {"--": "dashed", "-": "solid", ":": "dotted", "curve": "curve", "wavy": "wavy", "none": "none"}
PATH_COLORS = ("#1f3a93", "#c0392b", "#1e8449", "#7d3c98", "#b9770e")
KINDS = {"G": ("ΔG", "Gibbs free energy"), "H": ("ΔH", "enthalpy"), "E": ("ΔE", "electronic energy")}
NICS_SCAN_MIN = 10                       # ab so vielen Bq: Scan (Kurve über die Weglänge), sonst Einzelpunkte
NICS_NEAR = 2.5                          # Å: Schweratome für die lokale Ebene um ein Bq
PROFILE_DEFAULT = dict(species={}, sp=[], y="G", mode="levels", colors={}, irc=[], irc_x="rc", irc_ref="first")
NICS_DEFAULT = dict(files=[], geom="")

# Schlüsselwörter der Eingabezeile, die keine Methode sind (Job, Konvergenz, Gitter, Ausgabe, Hilfsbasen)
_JOB_KW = re.compile(r"(?i)^(\w*opt\w*|\w*freq|\w*scf|\w*pno|\w*conv|irc|sp|nmr|engrad|moread|\w*print\w*|"
                     r"(def|final)?grid\d*|pal\d+|ri|rijcosx|rijk|nori|autoaux|keepdens|noautostart|\S+/(c|j|jk))$")
_SOLV_KW = re.compile(r"(?i)^(smd|cpcm|cpcmc|alpb|ddcosmo)\(([^)]*)\)$")
_DISP_KW = re.compile(r"(?i)^d3(bj|zero)?$|^d4$")


def kcal(v) -> str:
    """Wert in kcal/mol mit einer Nachkommastelle und echtem Minus („−0.0“ -> „0.0“)."""
    s = f"{v:.1f}"
    return "0.0" if s == "-0.0" else s.replace("-", "−")


def level_of_theory(c) -> str:
    """Rechnung -> Methode wie in Veröffentlichungen: ORCA „! CAM-B3LYP D4 def2-TZVPP … SMD(Toluene)“ ->
    „CAM-B3LYP-D4/def2-TZVPP(SMD:Toluene)“; Gaussian: Token mit „/“ der Route. Schreibweise wie in der Eingabe."""
    if c is None:
        return ""
    words = " ".join(c.get("keywords") or []).replace("!", " ").split()
    solv = ""
    if c.get("program") == "Gaussian":
        meth = [w for w in words if "/" in w and not w.startswith("#")][:1]
        s = c.get("solvation") or {}
        solv = f"({s['model']}:{s['solvent']})" if s.get("solvent") else ""
        return (meth[0] + solv) if meth else ""
    parts = []
    for w in words:
        m = _SOLV_KW.match(w)
        if m:
            solv = f"({m.group(1).upper()}:{m.group(2)})" if m.group(2) else f"({m.group(1).upper()})"
        elif _DISP_KW.match(w) and parts:
            parts[-1] += "-" + w
        elif not _JOB_KW.match(w) and not w.startswith("%"):
            parts.append(w)
    return "/".join(parts) + solv if parts else ""


def same_geometry(f1, f2, tol=0.02):
    """Gleiche Elemente in gleicher Reihenfolge und Koordinaten ± tol Å (Einzelpunkt auf der Opt-Geometrie)."""
    return (list(f1["els"]) == list(f2["els"])
            and np.abs(np.asarray(f1["xyz"], float) - np.asarray(f2["xyz"], float)).max() < tol)


def species_energies(opt, sp=None) -> dict:
    """Absolute Energien [Eh] einer Spezies: E, H, G (fehlende Thermochemie -> Schlüssel fehlt). Mit Einzelpunkt
    E = E(SP), H/G = E(SP) + Korrektur der Opt/Freq-Rechnung."""
    th = opt.get("thermo") or {}
    e = th.get("E_el") or opt.get("energy")
    if e is None or (sp is not None and sp.get("energy") is None):   # abgebrochen: keine Energie -> keine Größe
        return {}
    e_el = float(e)
    base = float(sp["energy"]) if sp is not None else e_el
    out = {"E": base}
    for k in ("H", "G"):
        if th.get(k):
            out[k] = base + float(th[k]) - e_el
    return out


def profile_rows(items, kind):
    """items = [dict(label, step, paths, opt, sp)] -> (Zeilen mit „value“ [kcal/mol relativ zur ersten], Hinweise).
    Mit Einzelpunkten fallen Spezies ohne weg; ohne Größe (z. B. G ohne Frequenzen) ebenso."""
    notes = []
    if any(it["sp"] is not None for it in items):
        miss = [it["label"] for it in items if it["sp"] is None]
        if miss:
            notes.append(T("dft_prof_no_sp", names=", ".join(miss)))
        items = [it for it in items if it["sp"] is not None]
    rows = []
    for it in items:
        en = species_energies(it["opt"], it["sp"])
        if kind not in en:
            notes.append(T("dft_prof_no_kind", name=it["label"], kind=KINDS[kind][0]))
            continue
        rows.append(dict(it, abs=en[kind]))
    for r in rows:
        r["value"] = (r["abs"] - rows[0]["abs"]) * HARTREE_KCAL
    return rows, notes


def irc_curve(out_path, trj_path):
    """ORCA-IRC -> dict(s [Å], E [Eh], ts, cols, method). s = Reaktionskoordinate aus der Trajektorie."""
    from elucida.formats.calc import read_calc
    summ = parse_irc(read_text(out_path))
    frames = read_xyz(trj_path)
    if len(frames) != len(summ["steps"]):
        raise ValueError(T("dft_irc_trj_bad", n=len(frames), m=len(summ["steps"])))
    E = []
    for f, e in zip(frames, summ["E"]):
        m = re.search(r"\bE\s+(-?\d+\.\d+)", f.get("comment") or "")
        E.append(float(m.group(1)) if m else float(e))
    X = np.array([np.asarray(f["xyz"], float).ravel() for f in frames])
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))])
    return dict(s=s - s[summ["ts"]], E=np.array(E), ts=summ["ts"], cols=summ["cols"],
                method=level_of_theory(read_calc(out_path)))


def nics_points(n):
    """parse_nics-Ergebnis -> dict(h [Å, Abstand zur lokalen Ebene], nics, zz [ppm]) je Bq."""
    xyz, els = np.asarray(n["xyz"], float), n["els"]
    heavy = xyz[[e not in ("H", "D") for e in els]]
    if len(heavy) < 3:
        heavy = xyz

    def plane(pts):
        c = pts.mean(axis=0)
        return c, np.linalg.svd(pts - c)[2][2]
    g = plane(heavy)
    h, nics, zz = [], [], []
    for p, iso, t in zip(n["bq_xyz"], n["iso"], n["tensor"]):
        near = heavy[np.linalg.norm(heavy - p, axis=1) < NICS_NEAR]
        c, nv = plane(near) if len(near) >= 3 else g
        ts = (t + t.T) / 2
        h.append(float(np.dot(p - c, nv)))
        nics.append(-float(iso))
        zz.append(-float(nv @ ts @ nv))
    return dict(h=np.array(h), nics=np.array(nics), zz=np.array(zz), xyz=np.asarray(n["bq_xyz"], float))


def nics_pairs(pts):
    """Einzelpunkte ober- und unterhalb derselben Stelle -> [(i, j)] (gleiche Achse ± 0.3 Å, Seiten verschieden)."""
    out, used = [], set()
    for i in range(len(pts["h"])):
        if i in used:
            continue
        for j in range(i + 1, len(pts["h"])):
            d = pts["xyz"][i] - pts["xyz"][j]
            lateral = np.sqrt(max(0.0, float(d @ d) - (abs(pts["h"][i]) + abs(pts["h"][j])) ** 2))
            if j not in used and pts["h"][i] * pts["h"][j] < 0 and lateral < 0.3 \
                    and abs(abs(pts["h"][i]) - abs(pts["h"][j])) < 0.1:
                out.append((i, j))
                used |= {i, j}
                break
    return out


def nics_method(route):
    """„#p nmr=giao cam-b3lyp/6-311+g(2d,p)“ -> „GIAO-cam-b3lyp/6-311+g(2d,p)“ (Schreibweise wie in der Route)."""
    m = next((w for w in route.split() if "/" in w), "")
    g = re.search(r"(?i)nmr=\(?(giao|csgt|igaim)", route)
    return (g.group(1).upper() + "-" + m) if g and m else m


class DftPages:
    """Reiter „Energieprofil“ und „NICS“ eines DFT-Tabs (Zustand in tab.st["profile"/"nics"])."""

    def __init__(self, tab):
        self.tab = tab
        self._loading = False
        self.prof_group = self._profile_group()
        self.nics_group = self._nics_group()

    # -- Zustand -----------------------------------------------------------------------
    @property
    def prof(self):
        p = self.tab.st.setdefault("profile", {})
        for k, v in PROFILE_DEFAULT.items():
            p.setdefault(k, type(v)(v) if isinstance(v, (dict, list)) else v)
        for curve in p["irc"]:
            curve.setdefault("uid", uuid.uuid4().hex)
        return p

    @property
    def nics(self):
        p = self.tab.st.setdefault("nics", {})
        for k, v in NICS_DEFAULT.items():
            p.setdefault(k, type(v)(v) if isinstance(v, (dict, list)) else v)
        return p

    def changed(self):
        if self._loading:
            return
        self.refresh()
        self.tab.main.push_undo()

    # -- Energieprofil: Oberfläche ---------------------------------------------------------
    def _profile_group(self):
        """Seite „Energiediagramm“ wie die Tabs (Nutzerwunsch 2026-11-11): links die Spalte in Schritten
        Daten · Pfad · Darstellung, rechts das Diagramm, das jeder Änderung sofort folgt."""
        from PySide6.QtWidgets import QCheckBox, QFrame, QScrollArea, QSplitter
        from elucida.app import style as STYLE
        g = QWidget()
        g.setProperty("rawpage", True)                    # eigene Seite neben „Abbildung“, keine Ergebniskarte darum
        outer = QVBoxLayout(g)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        left = QWidget()
        lv = QVBoxLayout(left)

        # ---- Schritt Daten: Rechnungen als Plateaus, Einzelpunkte, IRC
        card = QGroupBox(T("dft_prof_card_levels"))
        f = STYLE.make_form(card)
        self.cmb_mode = QComboBox()
        for k in ("levels", "irc"):
            self.cmb_mode.addItem(T("dft_prof_mode_" + k), k)
        f.addRow(T("dft_prof_kind"), self.cmb_mode)
        self.cmb_y = QComboBox()
        for k in KINDS:
            self.cmb_y.addItem(KINDS[k][0], k)
        self.cmb_y.setToolTip(T("dft_prof_y_tip"))
        self.lbl_y = QLabel(T("dft_prof_energy"))
        f.addRow(self.lbl_y, self.cmb_y)
        self.form_levels = f
        # Kästchen in eigener Spalte 0 (ohne Text); der Name der Rechnung steht in Spalte 6, die gleich dahinter angezeigt
        # wird – so behalten Beschriftung, Schritt, Pfade, SP und Struktur ihre Nummern 1–5
        self.tbl_sp = QTableWidget(0, 7)
        self.tbl_sp.setHorizontalHeaderLabels(["", T("dft_prof_label"), T("dft_prof_step"), T("dft_prof_paths"),
                                               "SP", T("structure"), T("dft_prof_species")])
        self.tbl_sp.verticalHeader().setVisible(False)
        hh = self.tbl_sp.horizontalHeader()
        hh.moveSection(6, 1)
        for c_ in range(1, 7):                            # alle Spalten nach Inhalt (nichts abgeschnitten), die letzte füllt
            hh.setSectionResizeMode(c_, QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        self.tbl_sp.horizontalHeaderItem(4).setToolTip(T("dft_prof_sp"))
        STYLE.check_columns(self.tbl_sp)
        self.tbl_sp.setToolTip(T("dft_prof_tbl_tip"))
        STYLE.empty_note(self.tbl_sp, T("tbl_empty_calcs"))
        self.tbl_sp.itemChanged.connect(self.species_edited)
        self.tbl_sp.setMaximumHeight(170)
        f.addRow(self.tbl_sp)
        row = QHBoxLayout()
        self.btn_sp_add = QPushButton(T("dft_prof_sp_add_short"))      # kurz: die Spalte ist schmal, lang im Tooltip
        self.btn_sp_add.setToolTip(T("dft_prof_sp_add"))
        self.btn_sp_add.clicked.connect(self.add_sp)
        self.btn_sp_rm = QPushButton(T("dft_prof_sp_rm_short"))
        self.btn_sp_rm.setToolTip(T("dft_prof_sp_rm"))
        self.btn_sp_rm.clicked.connect(self.clear_sp)
        row.addWidget(self.btn_sp_add)
        row.addWidget(self.btn_sp_rm)
        f.addRow(row)
        self.row_sp = row
        row = QHBoxLayout()
        self.btn_level_remove = QPushButton(T('dft_prof_level_remove'))
        self.btn_level_remove.setToolTip(T('rp_remove_level_from_profile'))
        self.btn_level_remove.clicked.connect(self.remove_level)
        self.btn_level_restore = QPushButton(T('dft_prof_level_restore'))
        self.btn_level_restore.setToolTip(T('rp_restore_removed_level'))
        self.btn_level_restore.clicked.connect(self.restore_level)
        row.addWidget(self.btn_level_remove)
        row.addWidget(self.btn_level_restore)
        f.addRow(row)
        self.row_level = row
        self.cmb_level_restore = QComboBox()
        f.addRow(self.cmb_level_restore)
        # Lage, Breite und Farbe des in der Tabelle gewählten Plateaus (nur Darstellung: prof["layout"]["nodes"][uid];
        # fehlender Schlüssel = automatisch, wie im Zeichenwerk `DL.arranged`)
        from PySide6.QtWidgets import QAbstractItemView
        self.tbl_sp.setSelectionBehavior(QAbstractItemView.SelectRows)      # ganze Zeile wie in den anderen Tabellen
        self.tbl_sp.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_sp.itemSelectionChanged.connect(self.level_selected)
        self.lbl_level = STYLE.HintLabel("")               # sagt, wozu die Felder darunter gehören
        self.lbl_level.setWordWrap(True)
        self.lbl_level.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(self.lbl_level)
        self.level_spins = {}
        for key, text, low, high in (("x", "rp_layout_x", -1000, 1000), ("width", "rp_plateau_width", .05, 20),
                                     ("y", "rp_layout_height", -10000, 10000)):
            sp = QDoubleSpinBox(decimals=2, minimum=low, maximum=high, singleStep=.1)
            sp.setToolTip(T(text + "_tip"))
            sp.editingFinished.connect(self.level_field)
            f.addRow(T(text), sp)
            self.level_spins[key] = sp
        self.cb_level_break = QCheckBox(T("rp_break_after"))
        self.cb_level_break.setProperty("chip_here", True)  # gehört zur schematischen Höhe darüber
        self.cb_level_break.toggled.connect(self.level_field)
        f.addRow(self.cb_level_break)
        self.btn_level_color = TABS.color_button("black", lambda c: self._level_set("color", c))
        self.row_level_color = QHBoxLayout()               # Farbfeld in normaler Größe, nicht über die ganze Spalte
        self.row_level_color.addWidget(self.btn_level_color)
        self.row_level_color.addStretch(1)
        f.addRow(T("rp_plateau_color"), self.row_level_color)
        self.btn_level_auto = QPushButton(T("rp_auto_level"))
        self.btn_level_auto.setToolTip(T("rp_auto_level_tip"))
        self.btn_level_auto.clicked.connect(self.level_auto)
        self.btn_level_auto.setFixedWidth(STYLE.VALUE_W)   # einzelner Knopf: ganze Wertespalte
        f.addRow("", self.btn_level_auto)
        self.irc_list = QListWidget()
        self.irc_list.setToolTip(T("dft_irc_tip"))
        self.irc_list.setMaximumHeight(110)
        f.addRow(self.irc_list)
        row = QHBoxLayout()
        self.btn_irc_add = QPushButton(T("dft_irc_add"))
        self.btn_irc_add.clicked.connect(self.add_irc)
        self.btn_irc_up = QPushButton(T("dft_irc_up"))
        self.btn_irc_up.clicked.connect(self.irc_up)
        self.btn_irc_rm = QPushButton(T('rp_remove_irc_curve'))
        self.btn_irc_rm.clicked.connect(self.remove_irc)
        for b_ in (self.btn_irc_add, self.btn_irc_up, self.btn_irc_rm):
            row.addWidget(b_)
        f.addRow(row)
        self.row_irc = row
        self.cmb_irc_x, self.cmb_irc_ref = QComboBox(), QComboBox()
        self.lbl_irc_x, self.lbl_irc_ref = QLabel(T("dft_irc_x")), QLabel(T("dft_irc_ref"))
        f.addRow(self.lbl_irc_x, self.cmb_irc_x)
        f.addRow(self.lbl_irc_ref, self.cmb_irc_ref)
        lv.addWidget(card)

        # ---- Schritt Pfad: Plateaus als Knoten verknüpfen (im Bild ziehen oder hier), Stil je Verbinder
        from elucida.tabs import diagram_layout as DL
        from PySide6.QtWidgets import QAbstractItemView, QLineEdit
        card = self.card_edges = QGroupBox(T("dft_prof_card_edges"))
        f = self.form_edges = STYLE.make_form(card)
        hint = QLabel(T("dft_prof_edges_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        row = QHBoxLayout()                               # neuer Verbinder: von -> nach
        self.cmb_edge_a, self.cmb_edge_b = QComboBox(), QComboBox()
        b_ = QPushButton(STYLE.icon("add"), T("dft_prof_edge_add"))
        b_.clicked.connect(lambda: self.add_edge(self.cmb_edge_a.currentData(), self.cmb_edge_b.currentData()))
        row.addWidget(self.cmb_edge_a, 1)
        row.addWidget(QLabel("→"))
        row.addWidget(self.cmb_edge_b, 1)
        row.addWidget(b_)
        f.addRow(row)
        # Tabelle wie in den übrigen Tabs: lesen und wählen; geändert wird der gewählte Verbinder in den Feldern darunter
        self.tbl_edges = QTableWidget(0, 5)
        self.tbl_edges.setHorizontalHeaderLabels([T("dft_prof_edge_from"), T("dft_prof_edge_to"), T("dft_prof_edge_line"),
                                                  T("dft_prof_edge_text"), T("ov_color")])
        self.tbl_edges.verticalHeader().setVisible(False)
        self.tbl_edges.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_edges.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_edges.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hh = self.tbl_edges.horizontalHeader()
        for c_ in (0, 1, 4):
            hh.setSectionResizeMode(c_, QHeaderView.ResizeToContents)
        for c_ in (2, 3):
            hh.setSectionResizeMode(c_, QHeaderView.Stretch)
        self.tbl_edges.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tbl_edges.itemSelectionChanged.connect(self.edge_selected)
        f.addRow(self.tbl_edges)
        row = QHBoxLayout()
        self.btn_edge_rm = QPushButton(STYLE.icon("trash"), T("remove"))
        self.btn_edge_rm.clicked.connect(self.remove_edge)
        self.btn_edge_reset = QPushButton(T("dft_prof_edge_reset"))
        self.btn_edge_reset.setToolTip(T("dft_prof_edge_reset_tip"))
        self.btn_edge_reset.clicked.connect(self.reset_edges)
        row.addWidget(self.btn_edge_rm)
        row.addWidget(self.btn_edge_reset)
        f.addRow(row)
        self.cmb_edge_line = QComboBox()
        self.cmb_edge_line.addItem(T("dft_prof_line_default"), None)
        for key in DL.EDGE_LINES:
            self.cmb_edge_line.addItem(T("dft_prof_line_" + LINE_KEYS[key]), key)
        self.cmb_edge_line.currentIndexChanged.connect(self.edge_field)
        f.addRow(T("dft_prof_edge_line"), self.cmb_edge_line)
        self.ed_edge_text = QLineEdit()
        self.ed_edge_text.setPlaceholderText("ISC, IC, hν")
        self.ed_edge_text.editingFinished.connect(self.edge_field)
        f.addRow(T("dft_prof_edge_text"), self.ed_edge_text)
        self.cb_edge_arrow = QCheckBox(T("dft_prof_edge_arrow"))
        self.cb_edge_arrow.toggled.connect(self.edge_field)
        f.addRow(self.cb_edge_arrow)
        lv.addWidget(card)

        # ---- Schritt Darstellung: Stilvorlagen, Feinheiten, Größe
        card = self.card_style = QGroupBox(T("dft_prof_card_style"))
        f = STYLE.make_form(card)
        row = QHBoxLayout()
        self.preset_buttons = {}
        for key in PRESETS:
            b_ = QPushButton(T("dft_prof_preset_" + key))
            b_.setCheckable(True)
            b_.clicked.connect(lambda _=False, k=key: self.apply_preset(k))
            row.addWidget(b_, 1)
            self.preset_buttons[key] = b_
        f.addRow(T("dft_prof_preset"), row)
        self.row_presets = row
        self.cmb_connector = QComboBox()
        for key in ("--", "-", ":", "curve", "wavy", "none"):
            self.cmb_connector.addItem(T("dft_prof_line_" + LINE_KEYS[key]), key)
        self.cmb_connector.currentIndexChanged.connect(self.style_changed)
        f.addRow(T("rp_connector_style"), self.cmb_connector)
        self.style_spins = {}
        for key, text, low, high, step in (("line_width", "dft_prof_w_level", .2, 10, .2), ("connector_width", "dft_prof_w_connector", .2, 10, .1),
                                           ("font_size", "rp_layout_font", 4, 40, 1)):
            sp = QDoubleSpinBox(decimals=1, minimum=low, maximum=high, singleStep=step)
            sp.editingFinished.connect(self.style_changed)
            f.addRow(T(text), sp)
            self.style_spins[key] = sp
        self.cb_frame = QCheckBox(T("rp_show_diagram_frame"))
        self.cb_scaled = QCheckBox(T("dft_prof_scaled"))
        self.cb_scaled.setToolTip(T("dft_prof_scaled_tip"))
        self.cb_path_colors = QCheckBox(T("dft_prof_path_colors"))
        for cb in (self.cb_frame, self.cb_scaled, self.cb_path_colors):
            cb.toggled.connect(self.style_changed)
            f.addRow(cb)
        self.form_style = f
        self.color_row = QHBoxLayout()                    # Farbe je Pfad (nur bei mehreren Pfaden)
        self.color_row.setSpacing(6)
        f.addRow(T("dft_prof_colors"), self.color_row)
        self.btn_labels_reset = QPushButton(T("dft_prof_labels_reset"))
        self.btn_labels_reset.setToolTip(T("dft_prof_labels_reset_tip"))
        self.btn_labels_reset.clicked.connect(self.reset_labels)
        f.addRow("", self.btn_labels_reset)                # an der Feldkante wie die übrigen Knopfreihen
        lv.addWidget(card)
        card = QGroupBox(T("dft_prof_card_size"))
        f = STYLE.make_form(card)
        row = QHBoxLayout()
        self.profile_width, self.profile_height = QDoubleSpinBox(), QDoubleSpinBox()
        size = self.prof.get("size_cm") or [16., 11.]
        for w, value in zip((self.profile_width, self.profile_height), size):
            w.setRange(5., 80.); w.setValue(value); w.setDecimals(1); w.setSuffix(" cm")
            w.editingFinished.connect(self.profile_size_changed)
        row.addWidget(self.profile_width)
        row.addWidget(QLabel("×"))
        row.addWidget(self.profile_height)
        f.addRow(T("size_wh"), row)
        self.btn_images = QPushButton(T('rp_profile_images'))
        self.btn_images.clicked.connect(self.edit_annotations)
        f.addRow(self.btn_images)
        self.btn_workspace = QPushButton(g)                # früher „Große Arbeitsfläche“ (Dialog): die Seite ist jetzt groß
        self.btn_workspace.hide()
        lv.addWidget(card)
        lv.addStretch(1)

        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.btn_next = TABS.next_step_button()
        bar = TABS.side_bar(self.btn_next, stretch_at=0)
        col = QWidget()
        cv = QVBoxLayout(col)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(ls, 1)
        cv.addWidget(bar)

        self.canvas_fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.canvas_fig))
        self.canvas_host = TABS.CanvasHost(self.canvas, self.canvas_fig)        # mit Karte wie die Vorschau der Tabs
        self.canvas_host.setMinimumHeight(280)
        from elucida.tabs.profile_workspace import ProfileWorkspace
        self.workspace = ProfileWorkspace(self.canvas_host)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(TABS.PAGE_INSET[0], 0, TABS.PAGE_INSET[2], TABS.PAGE_INSET[3])
        rv.addWidget(self.workspace, 1)
        self.lbl_prof = QLabel("")
        self.lbl_prof.setWordWrap(True)
        self.lbl_prof.setStyleSheet(HINT_CSS)
        rv.addWidget(self.lbl_prof)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(col)
        split.addWidget(right)
        split.setSizes([STYLE.COLUMN_W, 900])
        outer.addWidget(split)
        STYLE.tidy(left)                                   # Ränder der Spalte zuerst: die Schrittleiste setzt den oberen neu
        self.row_presets.setSpacing(6)                     # vier gleich breite Vorlagen über die ganze Wertespalte
        for b_ in self.preset_buttons.values():
            b_.setFixedWidth((STYLE.VALUE_W - 18) // 4)
            b_.setStyleSheet("padding-left: 2px; padding-right: 2px;")     # „Klassisch“ passt sonst nicht in ein Viertel
        self.steps = TABS.StepColumn(left, cv, ("step_data", "step_path", "step_display"),
                                     settings=getattr(self.tab.main, "settings", None), name="profile", next_button=self.btn_next)
        self.column_fit = STYLE.fit_column(left, ls, bar, col, split)
        self.cmb_mode.currentIndexChanged.connect(self.combo_changed)
        self.cmb_y.currentIndexChanged.connect(self.combo_changed)
        self.cmb_irc_x.currentIndexChanged.connect(self.combo_changed)
        self.cmb_irc_ref.currentIndexChanged.connect(self.combo_changed)
        return g

    # -- Pfad: Verbinder (Plateaus als Knoten) ------------------------------------------------------
    def edges(self):
        """Verbinder, wie sie gezeichnet werden (ausdrücklich gesetzt oder aus Schritt und Pfad abgeleitet)."""
        from elucida.tabs import diagram_layout as DL
        return DL.edges_of(self.prof, self.levels_spec()[0])

    def _own_edges(self):
        """Verbinder zum Ändern: beim ersten Eingriff werden die abgeleiteten fest übernommen."""
        if self.prof.get("edges") is None:
            self.prof["edges"] = [dict(a=e["a"], b=e["b"]) for e in self.edges()]
        return self.prof["edges"]

    def add_edge(self, a, b):
        if not a or not b or a == b:
            return
        own = self._own_edges()
        if not any(e["a"] == a and e["b"] == b for e in own):
            own.append(dict(a=a, b=b))
        self.sync()
        self.tbl_edges.selectRow(next(i for i, e in enumerate(own) if e["a"] == a and e["b"] == b))   # gleich einstellbar
        self.changed()

    def remove_edge(self):
        r = self.tbl_edges.currentRow()
        own = self._own_edges()
        if 0 <= r < len(own):
            del own[r]
            self.sync()
            self.changed()

    def reset_edges(self):
        self.prof["edges"] = None
        self.sync()
        self.changed()

    def edge_selected(self):
        """Felder unter der Tabelle zeigen den gewählten Verbinder (ohne Auswahl aus)."""
        r = self.tbl_edges.currentRow()
        edges = self.edges() if self.prof["mode"] == "levels" else []
        on = 0 <= r < len(edges)
        e = edges[r] if on else {}
        was, self._loading = self._loading, True
        self.cmb_edge_line.setCurrentIndex(max(0, self.cmb_edge_line.findData(e.get("line"))))
        self.ed_edge_text.setText(e.get("label") or "")
        self.cb_edge_arrow.setChecked(bool(e.get("arrow")))
        self._loading = was
        for w in (self.cmb_edge_line, self.ed_edge_text, self.cb_edge_arrow, self.btn_edge_rm):
            w.setEnabled(on)

    def edge_field(self, *_):
        """Linie, Text oder Pfeilspitze des gewählten Verbinders geändert."""
        if self._loading:
            return
        r = self.tbl_edges.currentRow()
        own = self._own_edges()
        if not 0 <= r < len(own):
            return
        new = dict(line=self.cmb_edge_line.currentData(), label=self.ed_edge_text.text().strip(),
                   arrow=self.cb_edge_arrow.isChecked())
        if all((own[r].get(k) or None) == (v or None) for k, v in new.items()):
            return
        for k, v in new.items():
            own[r][k] = v
            if not v:
                del own[r][k]
        self._edge_row(r, own[r])
        self.btn_edge_reset.setEnabled(True)
        self.changed()

    def _edge_set(self, r, key, value):
        own = self._own_edges()
        if 0 <= r < len(own):
            own[r][key] = value
            self._edge_row(r, own[r])
            if r == self.tbl_edges.currentRow():
                self.edge_selected()
            self.btn_edge_reset.setEnabled(True)
            self.changed()

    @staticmethod
    def _edge_line(e):
        return T("dft_prof_line_" + LINE_KEYS[e["line"]] if e.get("line") else "dft_prof_line_default") + \
            (" →" if e.get("arrow") else "")

    def _edge_row(self, r, e):
        for c, text in ((2, self._edge_line(e)), (3, e.get("label") or "")):
            it = self.tbl_edges.item(r, c)
            if it is not None:
                it.setText(text)

    def fill_edges(self):
        from elucida.tabs import diagram_layout as DL
        rows = self.levels_spec()[0] if self.prof["mode"] == "levels" else []
        names = {r["uid"]: r["label"] for r in rows}
        edges = DL.edges_of(self.prof, rows) if rows else []
        t = self.tbl_edges
        keep = t.currentRow()
        t.setRowCount(len(edges))
        for i, e in enumerate(edges):
            for c, text in ((0, names.get(e["a"], "?")), (1, names.get(e["b"], "?")), (2, self._edge_line(e)),
                            (3, e.get("label") or "")):
                it = QTableWidgetItem(text)
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                t.setItem(i, c, it)
            if t.cellWidget(i, 4) is not None:
                t.cellWidget(i, 4).hide()                    # sofort weg, gelöscht wird erst in der Ereignisschleife
            t.setCellWidget(i, 4, TABS.color_button(e.get("color") or "black",
                                                    lambda c, i=i: self._edge_set(i, "color", c), cell=True))
        # Höhe nach den Zeilen (3 bis 8, darüber scrollen): kein halb sichtbarer Verbinder
        t.setFixedHeight(t.horizontalHeader().sizeHint().height() + max(3, min(len(edges), 8)) * TABS.STYLE.CHECK_ROW_H + 2)
        if edges:
            t.selectRow(min(max(keep, 0), len(edges) - 1))
        for cmb in (self.cmb_edge_a, self.cmb_edge_b):
            keep = cmb.currentData()
            cmb.clear()
            for r in rows:
                cmb.addItem(r["label"], r["uid"])
            cmb.setCurrentIndex(max(0, cmb.findData(keep)))
        if rows and self.cmb_edge_a.currentIndex() == self.cmb_edge_b.currentIndex() and len(rows) > 1:
            self.cmb_edge_b.setCurrentIndex(1)
        self.edge_selected()
        self.btn_edge_reset.setEnabled(self.prof.get("edges") is not None)
        self.card_edges.setEnabled(self.prof["mode"] == "levels")

    # -- Darstellung: Stil des Diagramms --------------------------------------------------------------
    def layout_key(self):
        return "layout" if self.prof["mode"] == "levels" else "layout_irc"

    def style_changed(self, *_):
        if self._loading:
            return
        lay = self.prof.setdefault(self.layout_key(), {})
        lay["connector_style"] = self.cmb_connector.currentData()
        for key, sp in self.style_spins.items():
            lay[key] = sp.value()
        lay["frame"] = self.cb_frame.isChecked()
        lay["mode"] = "scaled" if self.cb_scaled.isChecked() or self.prof["mode"] != "levels" else "schematic"
        lay["path_colors"] = self.cb_path_colors.isChecked()
        lay.pop("preset", None)
        self.sync_style()
        self.changed()

    def apply_preset(self, key):
        """Stilvorlage: setzt die Feinheiten in einem Zug; Lage der Plateaus und Labels bleibt."""
        lay = self.prof.setdefault(self.layout_key(), {})
        lay.update(PRESETS[key], preset=key)
        self.sync_style()
        self.changed()

    def reset_labels(self):
        """Verschobene Beschriftungen wieder an ihren Platz (über und unter dem Plateau, an der Mitte des Verbinders)."""
        for node in (self.prof.get("layout") or {}).get("nodes", {}).values():
            for k in ("energy_dx", "energy_dy", "label_dx", "label_dy"):
                node.pop(k, None)
        for e in self.prof.get("edges") or []:
            e.pop("label_dx", None)
            e.pop("label_dy", None)
        self.changed()

    def sync_style(self):
        from elucida.tabs import diagram_layout as DL
        lay = self.style_of(self.prof["mode"])[1]
        levels = self.prof["mode"] == "levels"
        self._loading = True
        self.cmb_connector.setCurrentIndex(max(0, self.cmb_connector.findData(lay.get("connector_style", "--" if levels else "-"))))
        defaults = dict(line_width=2.2 if levels else 1.2, connector_width=.8, font_size=self.cfg(self.prof["mode"])["labels"]["font_size"])
        for key, sp in self.style_spins.items():
            sp.setValue(lay.get(key, defaults[key]))
        self.cb_frame.setChecked(bool((self.prof.get(self.layout_key()) or {}).get("frame", True)))
        self.cb_scaled.setChecked(lay.get("mode", "scaled") == "scaled")
        self.cb_path_colors.setChecked(bool(lay.get("path_colors", True)))
        for key, b in self.preset_buttons.items():
            b.setChecked((self.prof.get(self.layout_key()) or {}).get("preset") == key)
        for w in (self.cb_scaled, self.cb_path_colors, self.btn_labels_reset, self.style_spins["connector_width"]):
            w.setEnabled(levels)
        self._loading = False
        self.level_selected()                              # Höhe je Plateau nur im schematischen Bild

    def link(self, a, b):
        """Im Bild von einem Plateau auf ein anderes gezogen: verknüpfen."""
        self.add_edge(a, b)

    def profile_size_changed(self):
        self.prof["size_cm"] = [self.profile_width.value(), self.profile_height.value()]
        self.changed()

    def edit_annotations(self):
        from elucida.tabs.profile_annotations import AnnotationDialog
        if not self.tab.main.ensure_project(): return
        d = AnnotationDialog(self)
        if d.exec() == QDialog.Accepted:
            self.prof["annotations"] = d.items
            self.changed()
        d.deleteLater()

    def combo_changed(self, *_):
        if self._loading:
            return
        p = self.prof
        p.update(mode=self.cmb_mode.currentData(), y=self.cmb_y.currentData())
        if self.cmb_irc_x.currentData():
            p["irc_x"] = self.cmb_irc_x.currentData()
        if self.cmb_irc_ref.currentData():
            p["irc_ref"] = self.cmb_irc_ref.currentData()
        self.changed()

    # -- Energieprofil: Daten --------------------------------------------------------------
    def calc_entries(self):
        """Einträge des Tabs mit ausgewerteter Rechnung (Opt/Freq; Reihenfolge wie im Tab)."""
        t = self.tab
        return [e for e in t.entries() if t.calc_of(e) is not None]

    def spec(self, e, i):
        d = dict(on=True, label=e.get("name") or Path(e["file"]).stem, step=i, paths="A")
        d.update(self.prof["species"].get(e["uid"]) or {})
        return d

    def profile_entries(self):
        removed = set(self.prof.get("removed_species", []))
        return [e for e in self.calc_entries() if e["uid"] not in removed]

    def remove_level(self):
        row = self.tbl_sp.currentRow()
        if row < 0: return
        uid = self.tbl_sp.item(row, 0).data(Qt.UserRole)
        removed = self.prof.setdefault("removed_species", [])
        if uid not in removed: removed.append(uid)
        # Beiseite legen, nicht wegwerfen: „Wiederherstellen“ bringt Label, Schritt, Pfade und Bilder zurück.
        anchored = [a for a in self.prof.get("annotations", []) if a["anchor"].get("species") == uid]
        self.prof.setdefault("removed_specs", {})[uid] = dict(spec=self.prof["species"].pop(uid, None), annotations=anchored)
        self.prof["annotations"] = [a for a in self.prof.get("annotations", []) if a["anchor"].get("species") != uid]
        self.sync(); self.changed()

    def restore_level(self):
        uid = self.cmb_level_restore.currentData()
        if uid in self.prof.get('removed_species', []):
            self.prof["removed_species"].remove(uid)
            kept = self.prof.get("removed_specs", {}).pop(uid, None) or {}
            if kept.get("spec") is not None:
                self.prof["species"][uid] = kept["spec"]
            self.prof.setdefault("annotations", []).extend(kept.get("annotations", []))
            self.sync(); self.changed()

    # -- Daten: Darstellung je Plateau (Lage, Breite, Farbe) --------------------------------------------
    LEVEL_KEYS = ("x", "width", "y", "break_after", "color")

    def _level_row(self):
        """(uid, Zeile des Stufenbilds) des in der Tabelle gewählten Plateaus; ohne Plateau (aus, ohne SP) (uid, None)."""
        r = self.tbl_sp.currentRow()
        it = self.tbl_sp.item(r, 0) if r >= 0 else None
        uid = it.data(Qt.UserRole) if it is not None else None
        rows, paths, _ = self.levels_spec() if uid and self.prof["mode"] == "levels" else ([], [], [])
        return uid, next((x for x in rows if x["uid"] == uid), None), paths

    def _level_auto_color(self, row, paths):
        """Farbe ohne eigene Angabe, wie `DL.build_levels` sie im Stufenbild der Seite wählt."""
        lay = self.style_of("levels")[1]
        default = lay.get("color", "black")
        if len(row["paths"]) != 1:
            return default
        p = row["paths"][0]
        return self.prof["colors"].get(p) or (self.path_color(p, paths.index(p)) if lay.get("path_colors", True) else default)

    def level_selected(self):
        """Felder unter der Tabelle zeigen Lage, Breite und Farbe des gewählten Plateaus (ohne Plateau aus)."""
        uid, row, paths = self._level_row()
        node = ((self.prof.get("layout") or {}).get("nodes") or {}).get(uid, {}) if row else {}
        schematic = self.style_of("levels")[1].get("mode", "scaled") == "schematic"
        was, self._loading = self._loading, True
        if row:
            for key, default in (("x", row["step"]), ("width", .7), ("y", row["value"])):
                self.level_spins[key].setValue(node.get(key, default))
            self.cb_level_break.setChecked(bool(node.get("break_after")))
            color = node.get("color") or self._level_auto_color(row, paths)
            b = self.btn_level_color
            b.setProperty("color", color)
            b.setStyleSheet(f"{b.property('cellcss')}background-color: {color}; border: 1px solid #777;")
        self._loading = was
        for w in (*self.level_spins.values(), self.cb_level_break, self.btn_level_color):
            w.setEnabled(row is not None)
        self.btn_level_auto.setEnabled(any(k in node for k in self.LEVEL_KEYS))
        lv = self.prof["mode"] == "levels"
        self.lbl_level.setText(T("rp_level_of", name=row["label"]) if row else T("rp_level_pick"))
        for w in (self.lbl_level, self.level_spins["x"], self.level_spins["width"], self.row_level_color,
                  self.btn_level_auto):
            self.form_levels.setRowVisible(w, lv)
        self.form_levels.setRowVisible(self.level_spins["y"], lv and schematic)   # Höhe frei nur im schematischen Bild
        self.cb_level_break.setVisible(lv and schematic)    # Chip: seine Zeile folgt ihm (`ChipRow.sync`)

    def _level_node(self):
        uid, row, _ = self._level_row()
        if row is None:
            return None
        return self.prof.setdefault("layout", {}).setdefault("nodes", {}).setdefault(uid, {})

    def _level_set(self, key, value):
        node = self._level_node()
        if node is None or node.get(key) == value:
            return
        node[key] = value
        self.level_selected()
        self.changed()

    def level_field(self, *_):
        """Lage, Breite, Höhe oder Unterbrechung des gewählten Plateaus geändert; der automatische Wert bleibt ungesetzt."""
        if self._loading:
            return
        _, row, _ = self._level_row()
        node = self._level_node()
        if node is None:
            return
        new = dict(x=(self.level_spins["x"].value(), row["step"]), width=(self.level_spins["width"].value(), .7))
        if self.style_of("levels")[1].get("mode", "scaled") == "schematic":    # Höhe nur im schematischen Bild frei
            new["y"] = (self.level_spins["y"].value(), round(row["value"], 2))
            new["break_after"] = (self.cb_level_break.isChecked(), False)
        before = dict(node)
        for key, (value, auto) in new.items():
            if value == auto if isinstance(value, bool) else abs(value - auto) < 1e-9:
                node.pop(key, None)
            else:
                node[key] = value
        if node != before:
            self.btn_level_auto.setEnabled(True)
            self.changed()

    def level_auto(self):
        """Gewähltes Plateau wieder automatisch: Lage am Schritt, Standardbreite, Farbe des Pfads."""
        node = self._level_node()
        if node is None or not any(k in node for k in self.LEVEL_KEYS):
            return
        for k in self.LEVEL_KEYS:
            node.pop(k, None)
        self.level_selected()
        self.changed()

    def sp_calcs(self):
        """[(Pfad, Rechnung, Geometrie)] der geladenen Einzelpunkte (unlesbare fehlen)."""
        out = []
        for p in self.prof["sp"]:
            if Path(p).exists():
                try:
                    c = self.tab.calc_file(p)
                    if c.get("energy") is not None:              # abgebrochener Einzelpunkt zählt nicht
                        out.append((p, c, self.tab.calc_geom(p)[0]))
                except Exception as ex:                          # sonst fehlt die Spezies ohne Erklärung
                    self.tab.add_note(f"{Path(p).name}: {ex}")
                    continue
        return out

    def sp_for(self, e, sps):
        g = self.tab.geometry(e)
        if g is None:
            return None
        frame = g[0][-1]
        return next(((p, c) for p, c, f in sps if same_geometry(frame, f)), None)

    def items(self):
        """Eingeschaltete Spezies -> [dict(label, step, paths, opt, sp, sp_file, uid)] in Schrittfolge."""
        sps = self.sp_calcs()
        out = []
        for i, e in enumerate(self.profile_entries()):
            d = self.spec(e, i)
            if not d["on"]:
                continue
            hit = self.sp_for(e, sps)
            out.append(dict(uid=e["uid"], label=d["label"], step=int(d["step"]),
                            paths=[s.strip() for s in str(d["paths"]).split(",") if s.strip()] or ["A"],
                            structure=d.get("structure"),
                            structure_offset=d.get("structure_offset"), structure_width=d.get("structure_width"),
                            opt=self.tab.calc_of(e), sp=hit[1] if hit else None, sp_file=hit[0] if hit else None))
        return sorted(out, key=lambda it: it["step"])

    def path_color(self, path, k):
        return self.prof["colors"].get(path) or PATH_COLORS[k % len(PATH_COLORS)]

    def level_text(self, items):
        """„<SP>//<Opt>“ (übliche Reihenfolge Einzelpunkt//Geometrie) bzw. nur die Opt-Methode; verschiedene -> erste."""
        opt = {level_of_theory(it["opt"]) for it in items} - {""}
        sp = {level_of_theory(it["sp"]) for it in items if it["sp"] is not None} - {""}
        lev = sorted(opt)[0] if opt else ""
        if sp:
            lev = sorted(sp)[0] + "//" + lev
        return lev, len(opt) > 1 or len(sp) > 1

    def levels_spec(self):
        """-> (Zeilen, Pfade, Hinweise) für das Stufenbild."""
        items = self.items()
        mr_items = [it for it in items if any((it.get(k) or {}).get("multireference") for k in ("opt", "sp"))]
        items = [it for it in items if not any((it.get(k) or {}).get("multireference") for k in ("opt", "sp"))]
        rows, notes = profile_rows(items, self.prof["y"]) if items else ([], [])
        notes += [it["label"] + ": " + T('rp_multireference_profile_requires_an_explicit_state_energy_omitted_for_n')
                  for it in mr_items]
        paths = sorted({p for r in rows for p in r["paths"]})
        lev, mixed = self.level_text(rows)
        if mixed:
            notes.append(T("dft_prof_mixed"))
        if any(r["sp"] is not None and not (r["sp"].get("solvation")) and r["opt"].get("solvation") for r in rows):
            notes.append(T("dft_prof_sp_solv"))
        return rows, paths, notes

    def irc_data(self):
        """Geladene IRCs -> ([dict(label, s, E, ts, cols, method)], Hinweise)."""
        out, notes = [], []
        for d in self.prof["irc"]:
            try:
                c = self.tab.cache(("irc", d["file"], d.get("trj")), lambda d=d: irc_curve(d["file"], d["trj"]))
            except Exception as ex:
                notes.append(f"{Path(d['file']).name}: {ex}")
                continue
            out.append(dict(c, uid=d["uid"], label=d.get("label") or Path(d["file"]).stem))
        return out, notes

    def irc_ref(self, curves):
        ref = self.prof["irc_ref"]
        if ref == "ts":
            return float(curves[0]["E"][curves[0]["ts"]])
        if ref.startswith("e:"):
            e = next((x for x in self.calc_entries() if x["uid"] == ref[2:]), None)
            if e is not None and species_energies(self.tab.calc_of(e)):
                return species_energies(self.tab.calc_of(e))["E"]
        return float(curves[0]["E"][0])

    # -- Abbildungen ------------------------------------------------------------------------
    def cfg(self, kind):
        cfg = TABS.FigureTab.base_cfg(self.tab)            # Größe/Formate/Textformat des DFT-Tabs
        if kind != "nics" and self.prof.get("size_cm"):
            cfg["figsize_in"] = [x / 2.54 for x in self.prof["size_cm"]]
            cfg["size_cm"] = list(self.prof["size_cm"])
        TABS.core.setup_fonts(TABS.plt, cfg)
        cfg["legend"] = False
        cfg["xlabel"] = "reaction coordinate" + (" [Å]" if kind == "irc_rc" else "")
        return cfg

    def style_of(self, mode, rec=None):
        """(Rahmen, Layout) einer Abbildung. Der Stil gehört zum Profil (`prof["layout"]` für das Stufenbild,
        `prof["layout_irc"]` für die IRC-Kurve); eine früher eingefügte Abbildung ohne Profilstil behält ihren eigenen."""
        lay = self.prof.get("layout" if mode == "levels" else "layout_irc")
        rec = rec or {}
        if lay:
            return bool(lay.get("frame", rec.get("frame", False))), {k: v for k, v in lay.items() if k != "frame"}
        return bool(rec.get("frame", False)), dict(rec.get("layout") or {})

    def build_levels(self, fig):
        """Stufenbild mit Strukturen/Bildern an den Plateaus; gezeichnet vom selben Zeichenwerk wie die Abbildungen
        des Reaktionspfads (`diagram_layout.build_levels`), Stil aus `prof["layout"]`."""
        from elucida.tabs import diagram_layout as DL
        frame = bool((self.prof.get("layout") or {}).get("frame", True))      # auf der Seite: Rahmen, solange nicht abgewählt
        return DL.build_levels(self, fig, dict(self.style_of("levels")[1], frame=frame), images=True)

    def build_irc(self, fig):
        curves_, notes = self.irc_data()
        if not curves_:
            return None, notes
        meth = {c["method"] for c in curves_}
        if len(meth) > 1:
            return None, notes + [T("dft_irc_method")]
        xk = self.prof["irc_x"]
        e0 = self.irc_ref(curves_)
        cfg = self.cfg("irc_rc" if xk == "rc" else "irc_bond")
        if xk != "rc":
            cfg["xlabel"] = f"{xk} [Å]"
        cfg["ylabel"] = "ΔE [kcal mol$^{-1}$]"
        curves, marks, x_end, anchors = [], [], None, {}
        for c in curves_:
            if xk == "rc":
                x = c["s"] + (0.0 if x_end is None else x_end - c["s"][0])
                x_end = x[-1]
            elif xk in c["cols"]:
                x = np.array(c["cols"][xk])
            else:
                notes.append(T("dft_irc_no_col", name=c["label"], col=xk))
                continue
            y = (c["E"] - e0) * HARTREE_KCAL
            anchors.update({("irc", c["uid"], i): (xx, yy) for i, (xx, yy) in enumerate(zip(x, y))})
            curves.append(dict(x=x, y=y, color="black", ls="-", lw=1.2, label=None))
            ts = c["ts"]
            marks.append((x[ts], y[ts], (c["E"][ts] - c["E"][0]) * HARTREE_KCAL, (c["E"][ts] - c["E"][-1]) * HARTREE_KCAL))
        if not curves:
            return None, notes
        xs = np.concatenate([c["x"] for c in curves])
        ys = np.concatenate([c["y"] for c in curves])
        span = float(ys.max() - ys.min()) or 10.0
        cfg["xlim"] = [float(xs.min()), float(xs.max())]
        if cfg["xlim"][0] == cfg["xlim"][1]:
            cfg["xlim"] = [cfg["xlim"][0]-.5, cfg["xlim"][1]+.5]
        cfg["ylim"] = [float(ys.min()) - 0.08 * span, float(ys.max()) + 0.2 * span]
        if any(a["mode"] == "irc" for a in self.prof.get("annotations", [])):
            cfg["ylim"][1] += .5 * span
        from elucida.tabs.profile_annotations import append_images
        notes += append_images(self, cfg, anchors, mode="irc")
        curves.append(dict(x=np.array([m[0] for m in marks]), y=np.array([m[1] for m in marks]), color="#c0392b",
                           ls="None", marker="o", ms=4, label=None, aux=True))
        F = TABS.X.SimpleFigure(TABS.plt, cfg, curves, [], {}, fig=fig, legend=False)
        fs = cfg["labels"]["font_size"]
        for x, y, fwd, rev in marks:
            F.ax.text(x, y + 0.04 * span, f"ΔE‡ = {kcal(fwd)} / {kcal(rev)}", ha="center", va="bottom", fontsize=fs)
        return F, notes

    def build(self, fig, mode=None):
        mode = mode or self.prof["mode"]
        return self.build_levels(fig) if mode == "levels" else self.build_irc(fig)

    # -- Bildunterschriften (HTML, englisch) ---------------------------------------------------
    def levels_caption(self, name):
        rows, _, _ = self.levels_spec()
        if not rows:
            return ""
        y = self.prof["y"]
        lev, _ = self.level_text(rows)
        th = rows[0]["opt"].get("thermo") or {}
        cond = f"; T = {th['T']} K, p = {th['P']} atm" if y != "E" and th.get("T") and th.get("P") else ""
        txt = (f"Calculated {KINDS[y][1]} profile of <b>{html.escape(name)}</b> ({KINDS[y][0]} in kcal mol-1, relative "
               f"to {html.escape(rows[0]['label'])}{cond})")
        return txt + (f" calculated at the {html.escape(lev)} level of theory." if lev else ".")

    def irc_caption(self, name):
        curves, _ = self.irc_data()
        if not curves:
            return ""
        meth = curves[0]["method"]
        xk = self.prof["irc_x"]
        xs = "the reaction coordinate" if xk == "rc" else html.escape(xk)
        return (f"Intrinsic reaction coordinate (IRC) of <b>{html.escape(name)}</b> (ΔE in kcal mol-1 along {xs}; "
                f"ΔE‡ forward/reverse at the transition state)"
                + (f" calculated at the {html.escape(meth)} level of theory." if meth else "."))

    # -- Aktionen ------------------------------------------------------------------------------
    def assign_structure(self, uid, path):
        """Copy a plateau's editable drawing into the project and persist its association."""
        path = self.tab.main.import_file(str(path), PRJ.STRUCTURES)
        self.prof["species"].setdefault(uid, {})["structure"] = path
        self.sync()
        self.changed()

    def choose_structure(self, uid):
        main = self.tab.main
        if not main.ensure_project():
            return
        path, _ = QFileDialog.getOpenFileName(self.tab, T("dlg_structure"),
                                             main.settings.value("last_img_dir", ""),
                                             f"{T('flt_struct')};;{T('flt_all')}")
        if path:
            self.assign_structure(uid, path)

    def draw_structure(self, uid):
        from elucida.app.drawing_editor import DrawingDialog, DrawingEditor
        main = self.tab.main
        if not main.ensure_project():
            return
        existing = self.prof["species"].get(uid, {}).get("structure")
        if existing and Path(existing).suffix.lower() == '.cdxml' and Path(existing).is_file():
            path = Path(existing)
        else:
            path = Path(main.project_dir) / PRJ.STRUCTURES / ('profile_' + uuid.uuid4().hex[:12] + '.cdxml')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PRJ.EMPTY_CDXML, encoding='utf-8')
        dialog = DrawingDialog(self.tab)
        dialog.setWindowTitle(T('dft_prof_draw_structure'))
        dialog.resize(820, 580)
        dialog.setSizeGripEnabled(True)
        layout = QVBoxLayout(dialog)
        editor = DrawingEditor(dialog, scheme_actions=False)
        dialog.editor = editor
        editor.set_canvas_dark(main.canvas_is_dark())
        editor.open_path(path)
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
        if PRJ.cdxml_has_content(path):
            self.assign_structure(uid, path)
        else:
            self.changed()
        dialog.deleteLater()

    def remove_structure(self, uid):
        self.prof["species"].setdefault(uid, {}).pop("structure", None)
        self.sync()
        self.changed()

    def add_sp(self):
        t = self.tab
        if not t.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(t, T("dft_prof_sp_add"), t.main.settings.value("last_dir", ""),
                                             f"{T('dft_flt')} (*.out *.log);;{T('flt_all')}")
        self.load_sp(ps)

    def load_sp(self, ps):
        t = self.tab
        for p in ps:
            p = t.main.import_file(p, PRJ.data_sub(t.STATE_KEY))
            try:
                t.calc_geom(p)
            except Exception as ex:
                t.main.error(f"{Path(p).name}: {ex}")
                continue
            if p not in self.prof["sp"]:
                self.prof["sp"].append(p)
        self.sync()
        self.changed()

    def clear_sp(self):
        self.prof["sp"] = []
        self.sync()
        self.changed()

    def add_irc(self):
        t = self.tab
        if not t.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(t, T("dft_irc_add"), t.main.settings.value("last_dir", ""),
                                             f"ORCA IRC (*.out);;{T('flt_all')}")
        for p in ps:
            self.load_irc(p)

    def load_irc(self, p):
        """IRC-Ausgabe + Trajektorie „<Name>_IRC_Full_trj.xyz“ daneben (beide ins Projekt); andere Methode als die
        schon geladenen -> ablehnen."""
        t = self.tab
        trj = Path(p).with_name(Path(p).stem + "_IRC_Full_trj.xyz")
        try:
            if not trj.exists():
                raise ValueError(T("dft_irc_trj", name=trj.name))
            c = irc_curve(p, trj)
            have, _ = self.irc_data()
            if have and have[0]["method"] != c["method"]:
                raise ValueError(T("dft_irc_method"))
        except Exception as ex:
            t.main.error(f"{Path(p).name}: {ex}")
            return
        sub = PRJ.data_sub(t.STATE_KEY)
        self.prof["irc"].append(dict(file=t.main.import_file(p, sub), trj=t.main.import_file(str(trj), sub),
                                     label=Path(p).stem))
        self.prof["mode"] = "irc"
        self.sync()
        self.changed()

    def irc_up(self):
        i = self.irc_list.currentRow()
        if i > 0:
            L = self.prof["irc"]
            L[i - 1], L[i] = L[i], L[i - 1]
            self.sync()
            self.irc_list.setCurrentRow(i - 1)
            self.changed()

    def remove_irc(self):
        i = self.irc_list.currentRow()
        if 0 <= i < len(self.prof["irc"]):
            uid = self.prof["irc"][i]["uid"]
            self.prof["annotations"] = [a for a in self.prof.get("annotations", []) if a["anchor"].get("irc") != uid]
            del self.prof["irc"][i]
            self.sync()
            self.changed()

    def species_edited(self, item):
        if self._loading:
            return
        uid = self.tbl_sp.item(item.row(), 0).data(Qt.UserRole)
        d = self.prof["species"].setdefault(uid, {})
        c, txt = item.column(), item.text().strip()
        if c == 0:
            d["on"] = item.checkState() == Qt.Checked
        elif c == 1:
            d["label"] = txt
        elif c == 2:
            try:
                d["step"] = int(float(txt.replace(",", ".")))
            except ValueError:
                self.sync()
                return
        elif c == 3:
            d["paths"] = ",".join(s.strip().upper() for s in txt.replace(";", ",").split(",") if s.strip()) or "A"
        self.sync()
        self.changed()

    # -- Anzeige -----------------------------------------------------------------------------------
    def sync(self):
        """Bedienelemente nach dem Zustand (Tabelle der Spezies, IRC-Liste, Auswahlfelder, Farben)."""
        p = self.prof
        self._loading = True
        for w, value in zip((self.profile_width, self.profile_height), p.get("size_cm") or [16., 11.]):
            w.setValue(value)
        sps = self.sp_calcs()
        es = self.profile_entries()
        self.tbl_sp.setRowCount(len(es))
        for i, e in enumerate(es):
            d = self.spec(e, i)
            hit = self.sp_for(e, sps)
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)   # ganze Zeile markiert
            it.setCheckState(Qt.Checked if d["on"] else Qt.Unchecked)
            it.setData(Qt.UserRole, e["uid"])
            self.tbl_sp.setItem(i, 0, it)
            it = QTableWidgetItem(e.get("name") or Path(e["file"]).stem)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tbl_sp.setItem(i, 6, it)
            for j, v in ((1, d["label"]), (2, str(d["step"])), (3, d["paths"])):
                self.tbl_sp.setItem(i, j, QTableWidgetItem(v))
            it = QTableWidgetItem(Path(hit[0]).name if hit else "–")
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tbl_sp.setItem(i, 4, it)
            button = QPushButton(T('dft_prof_structure_set') if d.get('structure') else T('dft_prof_structure_add'))
            button.setToolTip(d.get('structure') or T('dft_prof_structure_tip'))
            menu = QMenu(button)
            if elucida.octet_enabled():
                menu.addAction(T('dft_prof_draw_structure'), lambda checked=False, uid=e['uid']: self.draw_structure(uid))
            menu.addAction(T('choose'), lambda checked=False, uid=e['uid']: self.choose_structure(uid))
            if d.get('structure'):
                menu.addAction(T('remove'), lambda checked=False, uid=e['uid']: self.remove_structure(uid))
            button.setMenu(menu)
            self.tbl_sp.setCellWidget(i, 5, button)
        self.tbl_sp.resizeColumnsToContents()
        TABS.STYLE.check_columns(self.tbl_sp)
        # nicht unter die Höhe ihrer Zeilen (bis 170) drücken lassen: sonst schrumpft sie mit den Plateau-Feldern darunter
        self.tbl_sp.setMinimumHeight(min(170, self.tbl_sp.horizontalHeader().sizeHint().height()
                                         + max(1, len(es)) * TABS.STYLE.CHECK_ROW_H + 2))
        self.irc_list.clear()
        self.irc_list.addItems([d.get("label") or Path(d["file"]).stem for d in p["irc"]])
        self.cmb_mode.setCurrentIndex(max(0, self.cmb_mode.findData(p["mode"])))
        self.cmb_y.setCurrentIndex(max(0, self.cmb_y.findData(p["y"])))
        curves, _ = self.irc_data() if p["irc"] else ([], [])
        self.cmb_irc_x.clear()
        self.cmb_irc_x.addItem(T("dft_irc_rc"), "rc")
        for k in (curves[0]["cols"] if curves else {}):
            self.cmb_irc_x.addItem(k, k)
        self.cmb_irc_x.setCurrentIndex(max(0, self.cmb_irc_x.findData(p["irc_x"])))
        self.cmb_irc_ref.clear()
        self.cmb_irc_ref.addItem(T("dft_irc_ref_first"), "first")
        self.cmb_irc_ref.addItem(T("dft_irc_ref_ts"), "ts")
        if curves:
            for e in es:
                if level_of_theory(self.tab.calc_of(e)) == curves[0]["method"]:
                    self.cmb_irc_ref.addItem(e.get("name") or Path(e["file"]).stem, "e:" + e["uid"])
        self.cmb_irc_ref.setCurrentIndex(max(0, self.cmb_irc_ref.findData(p["irc_ref"])))
        lv = p["mode"] == "levels"
        self.cmb_level_restore.clear()
        for e in self.calc_entries():
            if e['uid'] in p.get('removed_species', []):
                self.cmb_level_restore.addItem(e.get('name') or Path(e['file']).stem, e['uid'])
        self.btn_level_restore.setEnabled(bool(p.get("removed_species")))
        fl = self.form_levels                               # ganze Zeilen ein-/ausblenden (keine Lücken im Formular)
        for w in (self.cmb_y, self.tbl_sp, self.row_sp, self.row_level):
            fl.setRowVisible(w, lv)
        fl.setRowVisible(self.cmb_level_restore, lv and bool(self.cmb_level_restore.count()))
        for w in (self.irc_list, self.row_irc, self.cmb_irc_x, self.cmb_irc_ref):
            fl.setRowVisible(w, not lv)
        self.btn_sp_rm.setEnabled(bool(p["sp"]))
        while self.color_row.count():
            w = self.color_row.takeAt(0).widget()
            if w is not None:
                w.hide()                                    # sofort weg, gelöscht wird erst in der Ereignisschleife
                w.deleteLater()
        rows, paths, _ = self.levels_spec() if lv else ([], [], [])
        self.form_style.setRowVisible(self.color_row, len(paths) > 1)
        if len(paths) > 1:
            for k, path in enumerate(paths):
                def pick(c, path=path):
                    self.prof["colors"][path] = c
                    self.changed()
                if k:
                    self.color_row.addSpacing(10)
                self.color_row.addWidget(QLabel(path), 0, Qt.AlignVCenter)
                self.color_row.addWidget(TABS.color_button(self.path_color(path, k), pick, small=True), 0, Qt.AlignVCenter)
            self.color_row.addStretch(1)
        self.fill_edges()
        self._loading = False
        self.sync_style()
        if hasattr(self.tab, "show_profile_tab"):
            self.tab.show_profile_tab()

    def has_profile(self):
        """Hat diese Verbindung ein Energieprofil gespeichert (Stufen bearbeitet, Einzelpunkte, IRC, Bilder)?"""
        p = self.prof
        return bool(p.get("species") or p.get("sp") or p.get("irc") or p.get("annotations") or p.get("edges")
                    or p.get("composition_assets"))

    def refresh(self):
        """Vorschau des gewählten Modus neu zeichnen (Exportgröße des Tabs, maßstabsgetreu verkleinert)."""
        self.tbl_sp.setMaximumHeight(170)
        self.irc_list.setMaximumHeight(110)
        dragger = getattr(self, "profile_dragger", None)
        if dragger:
            dragger.disconnect()
            self.profile_dragger = None
        linker = getattr(self, "profile_linker", None)
        if linker:
            linker.disconnect()
            self.profile_linker = None
        try:
            F, notes = self.build(self.canvas_fig)
        except Exception as ex:
            F, notes = None, [str(ex)]
        if F is None:
            self.canvas_fig.clear()
            self.canvas_fig.text(0.5, 0.5, T("dft_prof_empty"), ha="center", va="center", color="gray")
        else:
            self.profile_dragger = TABS.TabDragger(F, lambda moved, F=F: self.images_moved(F, moved))
            if self.prof["mode"] == "levels" and getattr(F, "profile_rows", None):
                from elucida.tabs import diagram_layout as DL
                self.profile_linker = DL.LinkMouse(F, F.profile_rows, self.link)   # Plateaus im Bild verknüpfen
        self.lbl_prof.setText("\n".join("⚠ " + n for n in notes))
        # SimpleFigure resets inches while Qt keeps the widget's pixel dimensions.
        # Fit both together after every rebuild (also on Retina screens).
        self.canvas_host.set_figure_size(*self.canvas_fig.get_size_inches())

    def images_moved(self, figure, moved):
        changed = False
        for key, pos in moved.items():                       # Energie-/Namenslabel verschoben: Abstand zum Plateau merken
            kind, _, uid = key.partition("_")
            ann = figure.ann_items.get(key)
            if kind in ("energy", "label") and ann is not None and hasattr(ann, "_anchor_af"):
                node = self.prof.setdefault("layout", {}).setdefault("nodes", {}).setdefault(uid, {})
                node[kind + "_dx"] = round(max(-1.0, min(1.0, pos[0] - ann._anchor_af[0])), 4)
                node[kind + "_dy"] = round(max(-1.0, min(1.0, pos[1] - ann._anchor_af[1])), 4)
                changed = True
            elif kind == "edge" and ann is not None:         # Beschriftung eines Verbinders verschoben
                a_, _, b_ = uid.partition("_")
                for e in self._own_edges():                  # abgeleitete Verbinder werden dabei fest übernommen
                    if e.get("a") == a_ and e.get("b") == b_:
                        e["label_dx"] = round(max(-1.0, min(1.0, pos[0] - ann._anchor_af[0])), 4)
                        e["label_dy"] = round(max(-1.0, min(1.0, pos[1] - ann._anchor_af[1])), 4)
                        changed = True
        for a in self.prof.get("annotations", []):
            key = "image_annotation_" + a["uid"]
            image = next((im for im in figure.cfg["images"] if im.get("_id") == key), None)
            if key in moved and image and image.get("_anchor_af"):
                x, y, width, _ = moved[key]
                ax, ay = image["_anchor_af"]
                a.update(offset=[x-ax, y-ay], width=width)
                changed = True
        for uid, species in self.prof["species"].items():
            key = "image_profile_" + uid
            image = next((im for im in figure.cfg["images"] if im.get("_id") == key), None)
            if key in moved and image and image.get("_anchor_af"):
                x, y, width, _ = moved[key]
                ax, ay = image["_anchor_af"]
                species.update(structure_offset=[x-ax, y-ay], structure_width=width)
                changed = True
        if changed:
            self.changed()

    # -- NICS ----------------------------------------------------------------------------------------
    def _nics_group(self):
        """Seite „NICS“ wie die übrigen Ergebnisseiten (Nutzerwunsch 2026-11-11): Aktionen oben rechts auf der Titelzeile,
        ohne Dateien ein Platzhalter in der Mitte, sonst Angaben als Formular, Tabelle mit gleich breiten Spalten und
        darunter der Scan (nur wenn es einen gibt)."""
        from PySide6.QtWidgets import QStackedWidget
        from elucida.app import style as STYLE
        g = QGroupBox(T("dft_nics"))
        v = QVBoxLayout(g)
        self.lbl_nics_none = STYLE.SciLabel("", T("dft_nics_start"))
        self.lbl_nics_none.setWordWrap(True)
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        f = STYLE.make_form()
        self.nics_list = QListWidget()
        self.nics_list.setMaximumHeight(90)
        f.addRow(T("dft_nics_files"), self.nics_list)
        self.ed_nics_geom = QLineEdit()
        self.ed_nics_geom.setPlaceholderText(T("dft_nics_geom_ph"))
        self.ed_nics_geom.setToolTip(T("dft_nics_geom_tip"))
        self.ed_nics_geom.editingFinished.connect(self.nics_geom_changed)
        f.addRow(T("dft_nics_geom"), self.ed_nics_geom)
        cv.addLayout(f)
        self.tbl_nics = QTableWidget(0, 6)
        self.tbl_nics.setHorizontalHeaderLabels([T("dft_nics_file"), "Bq", "h [Å]", "NICS [ppm]", "NICSzz [ppm]",
                                                 T("dft_nics_pair")])
        self.tbl_nics.verticalHeader().setVisible(False)
        self.tbl_nics.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)      # gleich breite Spalten, mittig
        cv.addWidget(self.tbl_nics, 1)
        self.nics_fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.nics_canvas = register_canvas(FigureCanvasQTAgg(self.nics_fig))
        self.nics_host = TABS.CanvasHost(self.nics_canvas, self.nics_fig, margin=0)
        self.nics_host.setMinimumHeight(280)
        cv.addWidget(self.nics_host, 2)
        self.lbl_nics = QLabel("")
        self.lbl_nics.setWordWrap(True)
        self.lbl_nics.setStyleSheet(HINT_CSS)
        cv.addWidget(self.lbl_nics)
        self.nics_stack = QStackedWidget()
        self.nics_stack.addWidget(self.lbl_nics_none)
        self.nics_stack.addWidget(content)
        v.addWidget(self.nics_stack, 1)
        b = QPushButton(STYLE.icon("add"), T("dft_nics_add"))
        b.clicked.connect(self.add_nics)
        self.btn_nics_rm = QPushButton(STYLE.icon("trash"), T("remove"))
        self.btn_nics_rm.clicked.connect(self.remove_nics)
        STYLE.card_actions(g, self.btn_nics_rm, b)
        return g

    def nics_data(self):
        """-> [dict(file, route, pts, scan)] der lesbaren NICS-Dateien, Hinweise."""
        out, notes = [], []
        for p in self.nics["files"]:
            try:
                n = self.tab.cache(("nics", p), lambda p=p: parse_nics(read_text(p)))
            except Exception as ex:
                notes.append(f"{Path(p).name}: {ex}")
                continue
            pts = nics_points(n)
            out.append(dict(file=p, route=n["route"], pts=pts, scan=len(pts["h"]) >= NICS_SCAN_MIN))
        return out, notes

    def nics_rows(self):
        """Tabelle: Einzelpunkte je Bq + Mittel ober-/unterhalb („NICS(1.0)“), -> [(Datei, Bq, h, NICS, zz, Paar)]."""
        rows = []
        data, _ = self.nics_data()
        for d in data:
            if d["scan"]:
                continue
            pts = d["pts"]
            pair_of = {}
            for i, j in nics_pairs(pts):
                pair_of[i] = pair_of[j] = (i, j)
            for i in range(len(pts["h"])):
                pr = ""
                if i in pair_of and pair_of[i][0] == i:
                    a, b = pair_of[i]
                    h = (abs(pts["h"][a]) + abs(pts["h"][b])) / 2
                    pr = (f"NICS({h:.1f}) = {(pts['nics'][a] + pts['nics'][b]) / 2:.1f}, "
                          f"NICSzz({h:.1f}) = {(pts['zz'][a] + pts['zz'][b]) / 2:.1f}").replace("-", "−")
                rows.append((Path(d["file"]).name, i + 1, pts["h"][i], pts["nics"][i], pts["zz"][i], pr))
        return rows

    def build_nics(self, fig):
        data, notes = self.nics_data()
        scans = [d for d in data if d["scan"]]
        if not scans:
            return None, notes
        cfg = self.cfg("nics")
        cfg["xlabel"] = "path length [Å]"
        cfg["ylabel"] = "NICS [ppm]"
        curves, ys, xs = [], [], []
        for k, d in enumerate(scans):
            pts = d["pts"]
            s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts["xyz"], axis=0), axis=1))])
            h = float(np.median(np.abs(pts["h"])))
            ls = ("-", "--", ":", "-.")[k % 4]
            curves += [dict(x=s, y=pts["nics"], color="black", ls=ls, lw=1.2, label=f"NICS({h:.1f})"),
                       dict(x=s, y=pts["zz"], color="#c0392b", ls=ls, lw=1.2, label=f"NICSzz({h:.1f})")]
            ys += [pts["nics"], pts["zz"]]
            xs.append(s)
        y = np.concatenate(ys)
        span = float(y.max() - y.min()) or 10.0
        cfg["xlim"] = [0.0, float(max(x[-1] for x in xs))]
        cfg["ylim"] = [float(y.min()) - 0.08 * span, float(y.max()) + 0.08 * span]
        cfg["legend"] = len(scans) > 1
        F = TABS.X.SimpleFigure(TABS.plt, cfg, curves, [], {}, fig=fig, legend=len(scans) > 1)
        F.ax.axhline(0.0, color="gray", lw=0.6)
        return F, notes

    def nics_caption(self, name):
        data, _ = self.nics_data()
        scans = [d for d in data if d["scan"]]
        if not scans:
            return ""
        hs = " and ".join(f"{float(np.median(np.abs(d['pts']['h']))):.1f}" for d in scans)
        lev = nics_method(scans[0]["route"])
        geom = self.nics["geom"].strip()
        lev = f"{lev}//{geom}" if lev and geom else lev
        return (f"NICS (black) and NICSzz (red) scan of <b>{html.escape(name)}</b> at {hs} Å above the molecular plane"
                + (f" calculated at the {html.escape(lev)} level of theory." if lev else "."))

    def add_nics(self):
        t = self.tab
        if not t.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(t, T("dft_nics_add"), t.main.settings.value("last_dir", ""),
                                             f"Gaussian (*.log *.out);;{T('flt_all')}")
        self.load_nics(ps)

    def load_nics(self, ps):
        t = self.tab
        for p in ps:
            try:
                parse_nics(read_text(p))
            except Exception as ex:
                t.main.error(f"{Path(p).name}: {ex}")
                continue
            p = t.main.import_file(p, PRJ.data_sub(t.STATE_KEY))
            if p not in self.nics["files"]:
                self.nics["files"].append(p)
        self.sync_nics()
        self.changed()

    def remove_nics(self):
        i = self.nics_list.currentRow()
        if 0 <= i < len(self.nics["files"]):
            del self.nics["files"][i]
            self.sync_nics()
            self.changed()

    def nics_geom_changed(self):
        if self.nics["geom"] != self.ed_nics_geom.text().strip():
            self.nics["geom"] = self.ed_nics_geom.text().strip()
            self.changed()

    def sync_nics(self):
        self._loading = True
        self.nics_list.clear()
        self.nics_list.addItems([Path(p).name for p in self.nics["files"]])
        self.ed_nics_geom.setText(self.nics["geom"])
        rows = self.nics_rows()
        self.tbl_nics.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate((r[0], str(r[1]), f"{r[2]:.2f}", f"{r[3]:.1f}", f"{r[4]:.1f}", r[5])):
                it = QTableWidgetItem(v.replace("-", "−") if j in (2, 3, 4) else v)
                it.setFlags(Qt.ItemIsEnabled)
                self.tbl_nics.setItem(i, j, it)
        self._loading = False
        try:
            F, notes = self.build_nics(self.nics_fig)
        except Exception as ex:
            F, notes = None, [str(ex)]
        if F is None:
            self.nics_fig.clear()
            self.nics_fig.text(0.5, 0.5, T("dft_nics_empty"), ha="center", va="center", color="gray")
        self.nics_host.setVisible(F is not None)              # Scan nur, wenn es einen gibt (sonst gehört der Platz der Tabelle)
        self.nics_stack.setCurrentIndex(1 if self.nics["files"] else 0)
        self.btn_nics_rm.setEnabled(bool(self.nics["files"]))
        self.lbl_nics.setText("\n".join("⚠ " + n for n in notes))
        self.nics_host.set_figure_size(*self.nics_fig.get_size_inches())

    # -- Export / SI ----------------------------------------------------------------------------------
    def figures(self):
        """[(Kürzel, Bauer, Unterschrift)] der vorhandenen Abbildungen: profile, IRC, NICS."""
        out = []
        if self.levels_spec()[0]:
            out.append(("profile", lambda fig: self.build(fig, "levels")[0], self.levels_caption))
        if self.prof["irc"]:
            out.append(("IRC", lambda fig: self.build(fig, "irc")[0], self.irc_caption))
        if any(d["scan"] for d in self.nics_data()[0]):
            out.append(("NICS", lambda fig: self.build_nics(fig)[0], self.nics_caption))
        return out

    def export_to(self, base: Path):
        """<base>_profile/_IRC/_NICS in den Formaten des Tabs; NICS-Einzelpunkte als CSV."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        files = []
        for key, build, _ in self.figures():
            fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = build(fig)
            if F is not None:
                out = base.with_name(f"{base.name}_{key}")
                F.cfg["output"] = str(out.with_suffix("." + F.cfg["_main_fmt"]))
                F.export()                               # core.Figure.export liefert keine Liste
                files += [out.with_suffix("." + e) for e in [F.cfg["_main_fmt"]] + F.cfg["extra_formats"]]
        rows = self.nics_rows()
        if rows:
            p = base.with_name(base.name + "_NICS.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["file", "Bq", "h [A]", "NICS [ppm]", "NICSzz [ppm]", "average above/below"])
                for r in rows:
                    w.writerow([r[0], r[1], f"{r[2]:.3f}", f"{r[3]:.2f}", f"{r[4]:.2f}", r[5].replace("−", "-")])
            files.append(p)
        return files

    def si_figures(self, out_dir, name):
        """SI: [("image", …), ("figcap", …)] je Abbildung (Energieprofil, IRC, NICS-Scan)."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        out = []
        for key, build, cap in self.figures():
            if key == "profile" and len(self.levels_spec()[0]) < 2:
                continue                                  # eine einzige Stufe ist kein Profil (ein Strich bei 0): nicht in die SI
            fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = build(fig)
            if F is not None:
                svg = Path(out_dir) / f"{TABS.core.safe_name(name)}_dft_{key}.svg"
                out += [TABS.si_image(F, svg), ("figcap", cap(name))]
        return out
