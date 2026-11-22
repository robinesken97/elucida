"""elucida/tabs/dft_nbo.py - Reiter „NBO“ des DFT-Tabs: zeigt, was eine NBO-Ausgabe enthält (Leser
`formats/nbo.py`), rechnet nichts. Zustand im DFT-Zustand `nbo`.

Links (Nutzerregel „links stellen, rechts sehen“): Karte „NBO-Rechnungen“ (Schritt Daten) und „NBO-Darstellung“
(Schritt Darstellung). Rechts eine Seite mit Unterreitern: Abbildung (Molekül mit natürlichen Ladungen an den Atomen
und NRT-Bindungsordnungen an den Bindungen, Labels ziehbar), Resonanzstrukturen (aus der CML von NRTCML, nur wenn sie
eindeutig zur Ausgabe passt), NPA, NBO, E(2), NRT, SI-Text. Ein Abschnitt, den die Ausgabe nicht enthält, hat keinen
Reiter. Die Bindungsordnungen sind die aus der NRT-Analyse; die IAO-Wiberg-Ordnungen des Orbitalbilds (Molden,
`core/orbitals`) sind eine eigene Rechnung von Elucida und haben hiermit nichts zu tun.
"""
from __future__ import annotations

import html
import math
import re
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout,
                               QHeaderView, QLineEdit, QCheckBox, QSpinBox, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register as register_canvas
from elucida.app.i18n import T
from elucida.core import tables as TBL
from elucida.formats import nbo as NBO
from elucida.formats.calc import read_text
from elucida.tabs import base as TABS
from elucida.tabs import xray as XRAY

NBO_DEFAULT = dict(files=[], current=None, atoms="charge", bonds="nrt", thr=0.10, dec=2, els="", show_h=True,
                   h_labels=False, e2_min=5.0, rs_max=12, color_q="#000000", color_bo="#1f3a93", view=None, zoom=1.0,
                   pan=[0.0, 0.0], layout={}, spin="total")
# bleibt bei „Darstellung zurücksetzen“: Dateien, Auswahl und was Tabellen ändert (Schwelle der Bindungsordnungen,
# E(2)-Schwelle, Spin der Wiberg-Tabelle)
RESET_KEEP = ("files", "current", "thr", "e2_min", "spin")
ATOM_MODES = ("charge", "spin", "name", "none")
SPINS = ("total", "alpha", "beta")
SPIN_SIGN = {"alpha": "α", "beta": "β"}
SKIP_TYPES = ("CR", "RY", "RY*")         # NBO-Liste: ohne Rumpf- und Rydberg-Orbitale (stehen in der CSV)


def minus(s):
    return str(s).replace("-", "−")


def fmt(v, dec):
    """Zahl mit `dec` Nachkommastellen, echtes Minus, nie „−0.00“."""
    s = f"{float(v):.{dec}f}"
    return s.lstrip("-") if float(s) == 0 else minus(s)


def compact(text):
    """„( C  1- C  2), N  4“ (Spalten der Ausgabe) -> „(C1–C2), N4“ (gleicher Inhalt, ohne Füllzeichen)."""
    t = re.sub(r"([A-Z][a-z]?)\s+(\d+)", r"\1\2", text)
    t = re.sub(r"(?<=\d)-\s*(?=[A-Z])", "–", t)
    return re.sub(r"\(\s+", "(", re.sub(r"\s+", " ", t)).strip()


def label_of(typ, n, atoms):
    return NBO.nbo_label(typ, n, atoms)


def e2_rows(d, e_min):
    """E(2)-Wechselwirkungen ab e_min kcal/mol, größte zuerst -> [(Donor, Akzeptor, E2, dE, F)] (Texte wie gedruckt)."""
    rows = [r for r in d["e2"] if float(r["e2"]) >= e_min - 1e-9]
    rows.sort(key=lambda r: -float(r["e2"]))
    return [(label_of(r["d_type"], r["d_n"], r["d_atoms"]), label_of(r["a_type"], r["a_n"], r["a_atoms"]),
             r["e2"], r["de"], r["f"]) for r in rows]


def nbo_rows(d):
    """NBO-Liste ohne CR/RY: [(NBO, Besetzung, Energie, Hybride als Mini-Auszeichnung)]."""
    return [(label_of(e["type"], e["n"], e["atoms"]), e["occ"], minus(e.get("energy", "")), e["hyb"])
            for k, e in sorted(d["nbos"].items()) if e["type"] not in SKIP_TYPES]


def views(d, spin):
    """Abschnitte für NBO-Liste/E(2): geschlossenschalig [("", d)]; offenschalig je Spin (α, β), bei „gesamt“ beide
    (die Liste bekommt dann die Spalte Spin) – NBO-Liste und E(2) gibt es offenschalig nur je Spin."""
    if not d.get("spin"):
        return [("", d)]
    keys = ("alpha", "beta") if spin == "total" else (spin,)
    return [(SPIN_SIGN[k], d["spin"][k]) for k in keys]


def wiberg_of(d, spin):
    """Wiberg der Auswahl: gesamt = d["wiberg"], α/β = die des Spin-Abschnitts (falls lesbar)."""
    if spin in ("alpha", "beta") and d.get("spin"):
        return d["spin"][spin]["wiberg"]
    return d["wiberg"]


def bond_source(st, d):
    """Gewählte Quelle der Bindungsbeschriftung, falls die Ausgabe sie enthält, sonst die andere vorhandene; „none“."""
    have = [k for k in ("nrt", "wiberg") if (wiberg_of(d, st.get("spin", "total")) if k == "wiberg" else d.get(k))]
    if st["bonds"] == "none" or not have:
        return "none"
    return st["bonds"] if st["bonds"] in have else have[0]


def bond_pairs(st, d):
    """{(i, j): Text} (Atomnummern ab 1) der gewählten Quelle ab der Schwelle."""
    src = bond_source(st, d)
    if src == "nrt":
        return {(a, b): t for a, b, t, _c, _i in NBO.nrt_bonds(d["nrt"], st["thr"])}
    if src == "wiberg":
        return {(a, b): v for a, b, v in NBO.wiberg_bonds(wiberg_of(d, st.get("spin", "total")), st["thr"])}
    return {}


class NboFigure(XRAY.XrayFigure):
    """Molekül wie im DFT-Tab, Atomlabels = Werte je Atom (über die Labels des Moleküls), dazu Labels an den
    Bindungen (`bond_labels` [(i, j, Text)], Indizes ab 0), ziehbar wie die Atomlabels (Schlüssel bo_i_j)."""

    def __init__(self, cfg, mol, R, opts, layout, fig, bond_labels=(), bond_color="#1f3a93", **kw):
        self.bond_labels, self.bond_color = list(bond_labels), bond_color
        super().__init__(cfg, mol, R, opts, layout, fig, **kw)

    def _anchor(self, k):
        if isinstance(k, tuple):
            a, b = self.scene["by_k"][k[0]], self.scene["by_k"][k[1]]
            return (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
        return super()._anchor(k)

    def _labels(self):
        """Atom- und Bindungslabels gemeinsam platzieren (eigene Platzierung statt der des X-Ray-Bilds, damit beide
        Sorten einander ausweichen): gespeicherte Versätze zuerst, dann die Bindungslabels (nur quer zur Bindung,
        etwas entlang verschiebbar), dann die Atomlabels (16 Richtungen). Kosten: Überlappung mit Atomen, Bindungen,
        anderen Labels und dem Bildrand."""
        o = self.opts
        atoms = [it for it in self.scene["atoms"] if o.get("labels", True)
                 and XRAY.label_shown(self.mol.atoms[it["k"]], o) and self.mol.atoms[it["k"]]["label"]]
        bonds = [(i, j, t) for i, j, t in self.bond_labels if i in self.scene["by_k"] and j in self.scene["by_k"]]
        if not atoms and not bonds:
            return
        from matplotlib.backends.backend_agg import RendererAgg
        W, H = self.fig.get_size_inches() * self.fig.dpi
        rend = RendererAgg(int(W), int(H), self.fig.dpi)
        tr, ppt = self.ax.transData, self.fig.dpi / 72.0
        fs = o.get("label_size") or self.cfg["labels"]["font_size"]
        halo = [XRAY.PE.withStroke(linewidth=2.2 * self.cfg.get("scale", 1.0), foreground=self.bg_show)]
        qcol = XRAY.label_color("C", {}, o.get("label_color"), self.style) or "black"
        circ = np.array([(*tr.transform((it["x"], it["y"])),
                          abs(tr.transform((it["x"] + max(it["w"], it["h"]) / 2, it["y"]))[0]
                              - tr.transform((it["x"], it["y"]))[0])) for it in self.scene["atoms"]])
        segs = [(tr.transform(self._anchor(a)), tr.transform(self._anchor(b))) for a, b in self.mol.bonds
                if a in self.scene["by_k"] and b in self.scene["by_k"]]
        f = np.linspace(0, 1, 24)[:, None]
        spts = np.vstack([p + f * (q - p) for p, q in segs]) if segs else np.zeros((0, 2))
        hw = max(1.5, self.bond_w * self.pt_per_A() * ppt / 2 if self.ball else 1.5 * ppt)
        boxes = []

        def cost(bx):
            x0, y0, x1, y1 = bx
            c = 0.0
            if len(circ):
                d = np.hypot(np.clip(circ[:, 0], x0, x1) - circ[:, 0], np.clip(circ[:, 1], y0, y1) - circ[:, 1])
                c += float(np.sum(np.clip(circ[:, 2] + 2 - d, 0, None))) * 4
            if len(spts):
                c += 30.0 * float(np.count_nonzero((spts[:, 0] > x0 - hw) & (spts[:, 0] < x1 + hw)
                                                   & (spts[:, 1] > y0 - hw) & (spts[:, 1] < y1 + hw)))
            for b in boxes:                                   # 5 px Luft zwischen Labels (2 px lagen im Pyridinring dicht)
                ox, oy = min(x1, b[2]) + 5 - max(x0, b[0]), min(y1, b[3]) + 5 - max(y0, b[1])
                if ox > 0 and oy > 0:
                    c += 5.0 * ox * oy + 200
            if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
                c += 1e4
            return c

        def make(key, text, anchor, color):
            ann = self.ax.annotate(text, xy=self._anchor(anchor), xycoords="data", xytext=(0, 0),
                                   textcoords="offset points", ha="center", va="center", fontsize=fs, zorder=60,
                                   color=color, annotation_clip=False, path_effects=halo)
            ann._atom = anchor
            self.ann_items[key] = ann
            bb = ann.get_window_extent(rend)
            return ann, bb.width, bb.height

        todo = []
        for i, j, text in bonds:
            todo.append(("b", f"bo_{i}_{j}", text, (i, j), self.bond_color))
        for it in atoms:
            a = self.mol.atoms[it["k"]]
            todo.append(("a", "lbl_" + a["key"], a["label"], it["k"], qcol))
        made = [(kind, key, anchor) + make(key, text, anchor, col) for kind, key, text, anchor, col in todo]
        free = []
        for kind, key, anchor, ann, w, h in made:                 # 1) gespeicherte Versätze
            pos = self.layout.get(key)
            if pos and len(pos) == 2:
                mx, my = tr.transform(self._anchor(anchor))
                ann.xyann = (float(pos[0]), float(pos[1]))
                boxes.append((mx + pos[0] * ppt - w / 2, my + pos[1] * ppt - h / 2,
                              mx + pos[0] * ppt + w / 2, my + pos[1] * ppt + h / 2))
            else:
                free.append((kind, key, anchor, ann, w, h))
        for kind, key, anchor, ann, w, h in free:                 # 2) Bindungen, 3) Atome (Reihenfolge von todo)
            mx, my = tr.transform(self._anchor(anchor))
            cands = []
            if kind == "b":
                pa, pb = tr.transform(self._anchor(anchor[0])), tr.transform(self._anchor(anchor[1]))
                u = (pb - pa) / (np.hypot(*(pb - pa)) or 1.0)
                nrm = np.array([-u[1], u[0]])
                L_ = np.hypot(*(pb - pa))
                for t in (0.0, 0.12, -0.12, 0.24, -0.24):
                    for side in (1, -1):
                        for dist in (1.0, 1.35, 1.8):
                            off = side * nrm * (abs(nrm[0]) * w / 2 + abs(nrm[1]) * h / 2 + 2.0 * ppt) * dist + u * t * L_
                            cands.append((off, (dist - 1) * 25 + abs(t) * 40))
            else:
                it = self.scene["by_k"][anchor]
                for rr in (1.0, 1.3, 1.7, 2.2):
                    for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                        ux, uy = math.cos(ang), math.sin(ang)
                        rpx = abs(tr.transform((it["x"] + XRAY._radius_along(it, ux, uy), it["y"]))[0] - mx)
                        dist = (rpx + abs(ux) * w / 2 + abs(uy) * h / 2 + 2.0 * ppt) * rr
                        cands.append((np.array([ux, uy]) * dist, (rr - 1) * 40 + 0.01 * ang))
            best = None
            for off, extra in cands:
                cx, cy = mx + off[0], my + off[1]
                bx = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                c = cost(bx) + extra
                if best is None or c < best[0]:
                    best = (c, bx, off)
            _, bx, off = best
            ann.xyann = (round(float(off[0] / ppt), 1), round(float(off[1] / ppt), 1))
            boxes.append(bx)
        self.order += [a for a in self.ann_items.values() if a not in self.order]
        self.auto_pos = self.current_layout()


class _Mouse:
    """Empfänger für `XrayMouse` der NBO-Abbildung: Ansicht und gezogene Labels."""

    def __init__(self, page):
        self.p = page

    def hover_atom(self, k):
        pass

    atom_clicked = atom_double_clicked = atoms_boxed = hover_atom

    def _store(self, **kw):
        self.p.st.update(kw)
        self.p.changed()

    def view_changed(self, R):
        self._store(view=[round(float(v), 6) for v in np.asarray(R).ravel()])

    def pan_changed(self, pan):
        self._store(pan=[round(float(pan[0]), 4), round(float(pan[1]), 4)])

    def zoom_changed(self, z):
        self.p.st["zoom"] = round(float(z), 4)

    def labels_moved(self, layout):
        F = self.p.F
        auto = F.auto_pos if F is not None else {}
        self._store(layout={k: v for k, v in layout.items() if auto.get(k) != v})


class NboPage:
    """Karten (links) und Ergebnisseite (rechts) des Reiters NBO; `page` kommt über `to_right` in den Tab."""

    def __init__(self, tab):
        self.tab, self._loading, self.F, self.mouse = tab, False, None, None
        self.enabled = True                     # im Reaktionspfad aus: NBO gehört zur einzelnen Verbindung
        self._cards()
        self._page()

    # -- Zustand -------------------------------------------------------------------------------
    @property
    def st(self):
        p = self.tab.st.setdefault("nbo", {})
        for k, v in NBO_DEFAULT.items():
            p.setdefault(k, type(v)(v) if isinstance(v, (dict, list)) else v)
        return p

    def changed(self):
        if self._loading:
            return
        self.sync()
        self.tab.main.push_undo()

    def entry(self):
        fs = self.st["files"]
        return next((f for f in fs if f["file"] == self.st["current"]), fs[0] if fs else None)

    def data(self, f):
        """Gelesene Ausgabe (gecacht) -> (dict, Fehlertext)."""
        try:
            return self.tab.cache(("nbo", f["file"]), lambda: NBO.parse_nbo(read_text(f["file"]))), ""
        except Exception as ex:
            return None, f"{Path(f['file']).name}: {ex}"

    def structures(self, f, d):
        """NRT-Strukturen der CML -> (Liste, Hinweis). Nur wenn die CML zur Ausgabe passt (`check_cml`)."""
        if not f.get("cml") or d is None:
            return [], (T("nbo_cml_none", name=NBO.cml_name(d["file_stem"])) if d and d["nrt"] and d["file_stem"]
                        and "NRTCML" in d["nbo_keys"].upper() else "")
        try:
            def load():
                s = NBO.parse_cml(f["cml"])
                NBO.check_cml(s, d)
                return s
            return self.tab.cache(("nbocml", f["cml"], f["file"]), load), ""
        except Exception as ex:
            return [], f"{Path(f['cml']).name}: {ex}"

    def has_data(self):
        return any(self.data(f)[0] is not None for f in self.st["files"])

    # -- Karten links --------------------------------------------------------------------------
    def _cards(self):
        g = QGroupBox(T("nbo_card"))
        f = STYLE.make_form(g)
        row = QHBoxLayout()
        b = STYLE.list_button(T("dft_nics_add_short"))          # wie NICS und ACID: „Hinzufügen …“ mit Plus
        b.setToolTip(T("nbo_add"))
        b.clicked.connect(self.add)
        self.btn_rm = STYLE.list_button(T("remove"))
        self.btn_rm.clicked.connect(self.remove)
        row.addWidget(b)
        row.addWidget(self.btn_rm)
        f.addRow(row)
        self.tbl_files = QTableWidget(0, 3)
        self.tbl_files.setHorizontalHeaderLabels([T("nbo_file"), "NBO", T("nbo_sections")])
        self.tbl_files.verticalHeader().setVisible(False)
        self.tbl_files.verticalHeader().setDefaultSectionSize(STYLE.CHECK_ROW_H)
        self.tbl_files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_files.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_files.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tbl_files.itemSelectionChanged.connect(self.selected)
        STYLE.empty_note(self.tbl_files, T("nbo_start"))
        f.addRow(self.tbl_files)
        self.lbl_files = STYLE.HintLabel("")
        self.lbl_files.setWordWrap(True)
        self.lbl_files.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(self.lbl_files)
        self.card = g

        g = QGroupBox(T("nbo_display"))
        f = STYLE.make_form(g)
        self.cmb_atoms = QComboBox()
        for k in ATOM_MODES:
            self.cmb_atoms.addItem(T("nbo_atoms_" + k), k)
        self.cmb_atoms.setToolTip(T("nbo_atoms_tip"))
        f.addRow(T("nbo_atoms"), self.cmb_atoms)
        self.cmb_bonds = QComboBox()
        self.cmb_bonds.addItem(T("nbo_bonds_nrt"), "nrt")
        self.cmb_bonds.addItem(T("nbo_bonds_wiberg"), "wiberg")
        self.cmb_bonds.addItem(T("nbo_bonds_none"), "none")
        self.cmb_bonds.setToolTip(T("nbo_bonds_tip"))
        f.addRow(T("nbo_bonds"), self.cmb_bonds)
        self.sp_thr = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=3.0, singleStep=0.05)
        self.sp_thr.setToolTip(T("nbo_thr_tip"))
        f.addRow(T("nbo_thr"), self.sp_thr)
        self.sp_dec = QSpinBox(minimum=1, maximum=4)
        f.addRow(T("nbo_dec"), self.sp_dec)
        self.ed_els = QLineEdit()
        self.ed_els.setPlaceholderText(T("nbo_els_ph"))
        self.ed_els.setToolTip(T("nbo_els_tip"))
        f.addRow(T("nbo_els"), self.ed_els)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_q = TABS.color_button(self.st["color_q"], lambda c: self.set_color("color_q", c))
        self.btn_q.setToolTip(T("nbo_color_q"))
        self.btn_bo = TABS.color_button(self.st["color_bo"], lambda c: self.set_color("color_bo", c))
        self.btn_bo.setToolTip(T("nbo_color_bo"))
        row.addWidget(self.btn_q)
        row.addWidget(self.btn_bo)
        row.addStretch(1)
        f.addRow(T("nbo_colors"), row)
        self.sp_e2 = QDoubleSpinBox(decimals=1, minimum=0.0, maximum=500.0, singleStep=1.0)
        self.sp_e2.setToolTip(T("nbo_e2_min_tip"))
        f.addRow(T("nbo_e2_min"), self.sp_e2)
        self.cmb_spin = QComboBox()
        for k in SPINS:
            self.cmb_spin.addItem(T("nbo_spin_" + k), k)
        self.cmb_spin.setToolTip(T("nbo_spin_tip"))
        f.addRow(T("nbo_spin"), self.cmb_spin)
        self._form_display = f
        self.sp_rs = QSpinBox(minimum=1, maximum=60)
        self.sp_rs.setToolTip(T("nbo_rs_max_tip"))
        f.addRow(T("nbo_rs_max"), self.sp_rs)
        self.cb_h = QCheckBox(T("nbo_show_h"))
        self.cb_hlab = QCheckBox(T("nbo_h_labels"))
        f.addRow(self.cb_h)
        f.addRow(self.cb_hlab)
        self.display = g
        for w in (self.cmb_atoms, self.cmb_spin):
            w.currentIndexChanged.connect(self.collect)
        self.cmb_bonds.currentIndexChanged.connect(self.bonds_changed)   # nur eigene Wahl speichern (s. sync)
        for w in (self.sp_thr, self.sp_dec, self.sp_e2, self.sp_rs):
            w.valueChanged.connect(self.collect)
        for w in (self.cb_h, self.cb_hlab):
            w.toggled.connect(self.collect)
        self.ed_els.editingFinished.connect(self.collect)

    def reset_display(self):
        """„Darstellung zurücksetzen“: Darstellung auf NBO_DEFAULT, RESET_KEEP bleibt (ohne eigenes Undo: der Tab
        speichert danach einen Schritt)."""
        import copy
        for k, v in NBO_DEFAULT.items():
            if k not in RESET_KEEP:
                self.st[k] = copy.deepcopy(v)

    def bonds_changed(self, *_):
        if not self._loading:
            self.st["bonds"] = self.cmb_bonds.currentData()
            self.changed()

    def set_color(self, key, c):
        self.st[key] = c
        self.changed()

    def collect(self, *_):
        if self._loading:
            return
        els = ", ".join(x for x in re.split(r"[,;\s]+", self.ed_els.text()) if x)
        self.st.update(atoms=self.cmb_atoms.currentData(), spin=self.cmb_spin.currentData(),
                       thr=round(self.sp_thr.value(), 2), dec=self.sp_dec.value(), els=els,
                       e2_min=round(self.sp_e2.value(), 1), rs_max=self.sp_rs.value(), show_h=self.cb_h.isChecked(),
                       h_labels=self.cb_hlab.isChecked())
        self.changed()

    # -- Seite rechts --------------------------------------------------------------------------
    def _card(self, title=""):
        g = QGroupBox(title)
        QVBoxLayout(g)
        return g

    def _grid(self, heads, rich=()):
        t = STYLE.FitGrid(0, len(heads))
        t.setHorizontalHeaderLabels(heads)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for c in rich:
            t.setItemDelegateForColumn(c, STYLE.RichDelegate(t, XRAY.to_html))
        return t

    def _page(self):
        """Seite „NBO“: Unterreiter im Stil der Ergebnisreiter, jeder eine Ergebniskarte."""
        self.page = QWidget()
        self.page.setProperty("rawpage", True)
        v = QVBoxLayout(self.page)
        v.setContentsMargins(0, 0, 0, 0)
        self.lbl_none = STYLE.SciLabel("", T("nbo_empty"))
        self.lbl_none.setWordWrap(True)
        none = self._card()
        none.layout().addWidget(self.lbl_none)
        self.sub = TABS.result_tabs()
        self.stack = QStackedWidget()
        self.stack.addWidget(TABS.result_page(none))
        self.stack.addWidget(self.sub)
        v.addWidget(self.stack)
        # Abbildung
        g = self._card()
        self.fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.host = TABS.CanvasHost(self.canvas, self.fig, margin=0)
        self.host.setMinimumHeight(280)
        g.layout().addWidget(self.host, 1)
        self.lbl_fig = STYLE.HintLabel("")
        self.lbl_fig.setWordWrap(True)
        self.lbl_fig.setStyleSheet(STYLE.HINT_CSS)
        g.layout().addWidget(self.lbl_fig)
        self.pg_fig = TABS.result_page(g)
        # Resonanzstrukturen (CML)
        g = self._card()
        self.rs_fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.rs_canvas = register_canvas(FigureCanvasQTAgg(self.rs_fig))
        self.rs_host = TABS.CanvasHost(self.rs_canvas, self.rs_fig, margin=0)
        self.rs_host.setMinimumHeight(280)
        g.layout().addWidget(self.rs_host, 1)
        self.pg_rs = TABS.result_page(g)
        # NPA
        g = self._card()
        self.tbl_npa = self._grid([T("nbo_col_atom"), "q" + STYLE.QTY + " [e]", T("nbo_col_core"),
                                   T("nbo_col_valence"), "Rydberg", T("nbo_col_total"), T("nbo_col_spin")])
        STYLE.name_table(self.tbl_npa, "NBO_NPA", "NBO natural charges")
        g.layout().addWidget(self.tbl_npa, 1)
        self.lbl_npa = STYLE.SciLabel("")
        self.lbl_npa.setWordWrap(True)
        g.layout().addWidget(self.lbl_npa)
        self.pg_npa = TABS.result_page(g)
        # NBO-Liste
        g = self._card()
        self.tbl_lewis = STYLE.summary_grid(["Spin", T("nbo_col_lewis"), T("nbo_col_occ") + " [e]", "%"])
        STYLE.name_table(self.tbl_lewis, "NBO_Lewis", "NBO Lewis structure")
        g.layout().addWidget(self.tbl_lewis)
        self.tbl_nbo = self._grid(["Spin", "NBO", T("nbo_col_occ") + " [e]", T("nbo_col_energy") + " [Eₕ]",
                                   T("nbo_col_hyb")], rich=(4,))
        STYLE.name_table(self.tbl_nbo, "NBO_list", "NBO list")
        self.tbl_nbo.elide_col = 4
        g.layout().addWidget(self.tbl_nbo, 1)
        self.lbl_nbo = STYLE.SciLabel("")
        self.lbl_nbo.setWordWrap(True)
        g.layout().addWidget(self.lbl_nbo)
        self.pg_nbo = TABS.result_page(g)
        # E(2)
        g = self._card()
        self.tbl_e2 = self._grid(["Spin", "Donor", T("nbo_col_acceptor"), "E(2) [kcal mol⁻¹]", "E(j)−E(i) [a.u.]",
                                  "F" + STYLE.QTY + "(i,j) [a.u.]"])
        STYLE.name_table(self.tbl_e2, "NBO_E2", "NBO E(2)")
        self.tbl_e2.elide_col = 2                            # Akzeptor gibt nach, statt quer zu rollen
        g.layout().addWidget(self.tbl_e2, 1)
        self.lbl_e2 = STYLE.SciLabel("")
        self.lbl_e2.setWordWrap(True)
        g.layout().addWidget(self.lbl_e2)
        self.pg_e2 = TABS.result_page(g)
        # NRT
        g = self._card()
        self.tbl_rs = self._grid(["RS", T("nbo_col_weight") + " [%]", T("nbo_col_change")])
        STYLE.name_table(self.tbl_rs, "NBO_NRT_weights", "NRT weights")
        self.tbl_rs.elide_col = 2
        g.layout().addWidget(self.tbl_rs, 1)
        self.tbl_bo = self._grid([T("nbo_col_bond"), T("nbo_col_bo_t"), T("nbo_col_bo_c"), T("nbo_col_bo_i")])
        STYLE.name_table(self.tbl_bo, "NBO_NRT_bond_orders", "NRT bond orders")
        g.layout().addWidget(self.tbl_bo, 1)
        self.lbl_nrt = STYLE.SciLabel("")
        self.lbl_nrt.setWordWrap(True)
        g.layout().addWidget(self.lbl_nrt)
        self.pg_nrt = TABS.result_page(g)
        # Wiberg (BNDIDX): Bindungen ab Schwelle, darunter die Summen je Atom
        g = self._card()
        self.tbl_wb = self._grid([T("nbo_col_bond"), T("nbo_col_wiberg")])
        STYLE.name_table(self.tbl_wb, "NBO_Wiberg", "Wiberg bond indices")
        g.layout().addWidget(self.tbl_wb, 1)
        self.tbl_wbt = self._grid([T("nbo_col_atom"), T("nbo_col_wiberg_sum")])
        STYLE.name_table(self.tbl_wbt, "NBO_Wiberg_totals", "Wiberg totals")
        g.layout().addWidget(self.tbl_wbt, 1)
        self.lbl_wb = STYLE.SciLabel("")
        self.lbl_wb.setWordWrap(True)
        g.layout().addWidget(self.lbl_wb)
        self.pg_wb = TABS.result_page(g)
        # SI-Text
        g = self._card()
        self.txt_si = STYLE.SiText("", T("nbo_empty"))
        g.layout().addWidget(self.txt_si, 1)
        self.btn_copy = STYLE.copy_button(T("nbo_copy_tip"))
        self.btn_copy.clicked.connect(self.copy_si)
        STYLE.card_actions(g, self.btn_copy)
        self.pg_si = TABS.result_page(g)
        self.pages = [(self.pg_fig, "nbo_sub_fig"), (self.pg_rs, "nbo_sub_rs"), (self.pg_npa, "NPA"),
                      (self.pg_nbo, "NBO"), (self.pg_e2, "E(2)"), (self.pg_nrt, "NRT"), (self.pg_wb, "Wiberg"),
                      (self.pg_si, "nbo_sub_si")]
        self.sub.currentChanged.connect(lambda *_: self.host.set_figure_size(*self.fig.get_size_inches()))

    def _show_pages(self, keep):
        """Unterreiter mit Inhalt in fester Reihenfolge; die übrigen herausgenommen (nicht nur verborgen)."""
        cur = self.sub.currentWidget()
        want = [(w, t) for w, t in self.pages if w in keep]
        have = [self.sub.widget(i) for i in range(self.sub.count())]
        if have != [w for w, _ in want]:
            self.sub.blockSignals(True)
            while self.sub.count():
                self.sub.removeTab(0)
            for w, t in want:
                self.sub.addTab(w, T(t) if t.startswith("nbo_") else t)
            self.sub.blockSignals(False)
            if cur in keep:
                self.sub.setCurrentWidget(cur)

    # -- Abbildung -----------------------------------------------------------------------------
    def molecule(self, d):
        from elucida.tabs import dft as DFT
        els = [g[1][0] for g in d["geometry"]]
        xyz = np.array([[float(v) for v in g[1][1:4]] for g in d["geometry"]])
        st = self.st
        mode = st["atoms"] if st["atoms"] != "spin" or "spin" in (d["npa"] or [{}])[0] else "charge"
        q = {(a["el"], a["num"]): a["spin" if mode == "spin" else "charge"] for a in d["npa"]}
        labels = []
        for k, el in enumerate(els):
            if mode in ("charge", "spin"):
                v = fmt(q[(el, k + 1)], st["dec"]) if (el, k + 1) in q else ""
                labels.append("+" + v if mode == "spin" and v and not v.startswith("−") and float(v) != 0 else v)
            else:
                labels.append(f"{el}{k + 1}")
        bonds = self.tab.cache(("nbobonds", tuple(els), xyz.tobytes()), lambda: DFT.bonds_of(els, xyz))
        r = self.tab.st.get("radius", 0.25)
        return DFT.XyzMolecule(els, xyz, bonds, labels, uiso=(r / XRAY.chi2_scale(0.5)) ** 2)

    def element_filter(self):
        return {x.strip().capitalize() for x in self.st["els"].split(",") if x.strip()}

    def bond_labels(self, d, mol):
        st = self.st
        bo = bond_pairs(st, d)
        out = []
        for i, j in mol.bonds:
            a, b = sorted((i + 1, j + 1))
            if (a, b) in bo:
                out.append((i, j, fmt(bo[(a, b)], st["dec"])))
        return out

    def build(self, fig, d, interactive=True):
        if not d.get("geometry"):                        # Ausgabe ohne Geometrieblock: Tabellen ja, Abbildung nicht
            raise ValueError(T("fixd_nbo_no_geom"))
        st, t = self.st, self.tab
        mol = self.molecule(d)
        cfg = t.base_cfg()
        TABS.core.setup_fonts(TABS.plt, cfg)
        r = t.st.get("radius", 0.25)
        only = self.element_filter()
        label_on = {}
        for a in mol.atoms:
            if st["atoms"] == "none" or (only and a["el"] not in only):
                label_on[a["key"]] = False
        o = dict(prob=50, show_h=st["show_h"], labels=st["atoms"] != "none", h_labels=st["h_labels"], colors={},
                 bond_w=t.st.get("bond_w", 0.08), hidden_frags=[],
                 style=XRAY.allowed_style(t.st.get("style", "mercury"), XRAY.DFT_STYLES, "depth"),
                 hidden_atoms=[], label_on=label_on, wire=set(), wire_h=False, label_mode="all", hide_kinds=[],
                 label_size=t.st.get("label_pt", 0.0), label_color=st["color_q"], label_colors={},
                 cartoon_color=t.st.get("cartoon_color", False), h_radius=0.55 * r, bg=t.st.get("bg", "white"),
                 ball_scale=r / t.DEFAULT_STATE["radius"], rod_scale=t.st.get("bond_w", 0.08) / t.DEFAULT_STATE["bond_w"],
                 orbital=None, elem_labels=False)
        if o["style"] == "iboview":                      # IboView-Stil ohne Orbital: wie Kugel-Stab „depth“
            o["style"] = "depth"
        # X–H nur mit „H beschriften“; mit Elementauswahl nur Bindungen, an denen ein gewähltes Element hängt
        bl = [x for x in self.bond_labels(d, mol)
              if (st["h_labels"] or "H" not in (mol.atoms[x[0]]["el"], mol.atoms[x[1]]["el"]))
              and (not only or {mol.atoms[x[0]]["el"], mol.atoms[x[1]]["el"]} & only)]
        R = (np.array(st["view"], float).reshape(3, 3) if st["view"] and len(st["view"]) == 9
             else XRAY.default_view(mol, use=list(range(len(mol.atoms)))))
        return NboFigure(cfg, mol, R, o, st["layout"], fig, bond_labels=bl, bond_color=st["color_bo"],
                         zoom=st["zoom"] if interactive else 1.0, pan=st["pan"] if interactive else (0.0, 0.0))

    def rs_view(self, d):
        mol = self.molecule(d)
        st = self.st
        return (np.array(st["view"], float).reshape(3, 3) if st["view"] and len(st["view"]) == 9
                else XRAY.default_view(mol, use=list(range(len(mol.atoms)))))

    def build_rs(self, fig, d, structs):
        """Resonanzstrukturen als Strichformeln in der Ansicht der Abbildung: Bindungen mit ihrer Ordnung (Doppel-/
        Dreifachstrich), Heteroatome mit Symbol, Formalladungen ⊕/⊖ (aus der Lewis-Struktur), darunter das Gewicht."""
        st = self.st
        n = min(len(structs), st["rs_max"])
        structs = structs[:n]
        cfg = self.tab.base_cfg()
        TABS.core.setup_fonts(TABS.plt, cfg)
        W = cfg["figsize_in"][0]
        fig.clear()
        R = self.rs_view(d)
        P = np.asarray(structs[0]["xyz"], float) @ R.T if structs else np.zeros((1, 3))
        show = [k for k, e in enumerate(structs[0]["els"]) if st["show_h"] or e != "H"] if structs else []
        xy = P[:, :2] - P[show, :2].mean(axis=0)
        span = np.ptp(xy[show], axis=0) + 1.5         # Rand: Elementsymbole am Rand nicht angeschnitten
        aspect = span[1] / span[0]
        # Spalten nach Form: kompakte Moleküle vier je Zeile wie in der Vorlage, gestreckte weniger (sonst winzig)
        cols = max(1, min(n, 4 if aspect >= 0.75 else 3 if aspect >= 0.5 else 2))
        rows = max(1, math.ceil(n / cols))
        cell_w = W / cols
        cell_h = cell_w * aspect + 0.28
        fig.set_size_inches(W, max(1.0, rows * cell_h), forward=False)
        fig.set_facecolor("white")
        fs = cfg["labels"]["font_size"]
        for k, s in enumerate(structs):
            ax = fig.add_axes([(k % cols) / cols, 1 - (k // cols + 1) / rows, 1 / cols, 1 / rows])
            ax.set_axis_off()
            ax.set_aspect("equal")
            ax.set_xlim(-span[0] / 2, span[0] / 2)
            ax.set_ylim(-span[1] / 2 - 0.28 * span[0] / cell_w, span[1] / 2)
            ch = NBO.formal_charges(s)
            for a, b, o in s["bonds"]:
                if a not in show or b not in show:
                    continue
                p, q = xy[a], xy[b]
                u = (q - p) / (np.hypot(*(q - p)) or 1.0)
                nv = np.array([-u[1], u[0]]) * 0.11
                offs = {1: (0,), 2: (-0.5, 0.5), 3: (-1, 0, 1)}.get(o, (0,))
                for f_ in offs:
                    ax.plot([p[0] + f_ * nv[0], q[0] + f_ * nv[0]], [p[1] + f_ * nv[1], q[1] + f_ * nv[1]],
                            color="black", lw=1.0, solid_capstyle="round", zorder=2)
            for a in show:
                el = s["els"][a]
                if el != "C":
                    ax.text(xy[a][0], xy[a][1], el, ha="center", va="center", fontsize=fs * (0.7 if el == "H" else 0.9),
                            color="#777777" if el == "H" else XRAY.label_color(el, {}, "atom") or "black", zorder=4,
                            bbox=dict(boxstyle="circle,pad=0.08", fc="white", ec="none"))
                if ch[a]:                                   # Ladung im Kreis (⊕/⊖ fehlen in Arial)
                    col = "#c0392b" if ch[a] > 0 else "#1f3a93"
                    ax.text(xy[a][0] + 0.34, xy[a][1] + 0.34, ("+" if ch[a] > 0 else "−") * abs(ch[a]), ha="center",
                            va="center", fontsize=fs * 0.6, color=col, zorder=5,
                            bbox=dict(boxstyle="circle,pad=0.12", fc="white", ec=col, lw=0.6))
            ax.text(0, -span[1] / 2 - 0.1, f"{s['weight']}%", ha="center", va="top", fontsize=fs)
        return n

    # -- Laden ---------------------------------------------------------------------------------
    def add(self):
        t = self.tab
        if not t.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(t, T("nbo_add"), t.main.settings.value("last_dir", ""),
                                             f"ORCA (*.out *.log);;{T('flt_all')}")
        self.load(ps)

    def load(self, ps):
        """ORCA-Ausgaben mit NBO übernehmen (Kopie ins Projekt); die CML der NRT-Strukturen (FILE=…-nrt.cml) daneben
        kopiert mit, wenn es sie gibt. Nicht lesbare Dateien: Meldung, nichts übernommen."""
        t = self.tab
        for p in ps:
            try:
                d = NBO.parse_nbo(read_text(p))
            except Exception as ex:
                t.main.error(f"{Path(p).name}: {ex}")
                continue
            cml = NBO.find_cml(p, d)
            sub = PRJ.data_sub(t.STATE_KEY)
            q = t.main.import_file(p, sub)
            entry = dict(file=q, cml=t.main.import_file(str(cml), sub) if cml else None)
            self.st["files"] = [f for f in self.st["files"] if f["file"] != q] + [entry]
            self.st["current"] = q
            if not d.get("spin"):
                self.st["spin"] = "total"          # geschlossenschalig: keine α/β-Wahl stehen lassen
        self.changed()

    def remove(self):
        i = self.tbl_files.currentRow()
        fs = self.st["files"]
        if 0 <= i < len(fs):
            del fs[i]
            self.st["current"] = fs[0]["file"] if fs else None
            self.changed()

    def selected(self):
        if self._loading:
            return
        i = self.tbl_files.currentRow()
        fs = self.st["files"]
        if 0 <= i < len(fs) and fs[i]["file"] != self.st["current"]:
            self.st.update(current=fs[i]["file"], view=None, zoom=1.0, pan=[0.0, 0.0], layout={})
            self.changed()

    # -- Anzeige -------------------------------------------------------------------------------
    def sections(self, d, structs):
        out = ["NPA"] if d["npa"] else []
        vs = views(d, "total")
        if any(v["nbos"] for _, v in vs):
            out.append("NBO" + (" α/β" if d.get("spin") else ""))
        if any(v["e2"] for _, v in vs):
            out.append("E(2)")
        if d["nrt"]:
            out.append("NRT")
        if d["wiberg"]:
            out.append("Wiberg")
        if structs:
            out.append("CML")
        return ", ".join(out)

    def notes(self, f, d, structs, cml_note):
        out = list(d["notes"])
        if not d["wiberg"] and T("nbo_wiberg_bad") not in out:
            out.append(T("nbo_wiberg_none"))
        if cml_note:
            out.append(cml_note)
        if not d["normal"]:
            out.append(T("nbo_not_normal"))
        if any(None in s_["lp"] for s_ in structs or []):    # D8: ohne lonePair keine Formalladungen (nie geraten)
            out.append(T("r2a_nbo_no_lp"))
        return out

    def sync(self):
        self._loading = True
        st = self.st
        try:
            fs = st["files"]
            tf = self.tbl_files
            tf.setRowCount(len(fs))
            cur = self.entry()
            for i, f in enumerate(fs):
                d, err = self.data(f)
                structs = self.structures(f, d)[0] if d else []
                vals = (Path(f["file"]).name, d["nbo_version"] if d else "–", self.sections(d, structs) if d else err)
                for j, v in enumerate(vals):
                    it = QTableWidgetItem(v)
                    it.setToolTip(v)
                    tf.setItem(i, j, it)
            if cur is not None:
                tf.selectRow(fs.index(cur))
            tf.setFixedHeight(tf.horizontalHeader().sizeHint().height() + max(2, min(6, tf.rowCount())) * STYLE.CHECK_ROW_H + 2)
            STYLE.fit_columns(tf)
            self.btn_rm.setEnabled(bool(fs))
            d0 = self.data(cur)[0] if cur else None
            open_ = bool(d0 and d0.get("spin"))
            modes = [k for k in ATOM_MODES if k != "spin" or open_]   # Spindichte nur, wenn die Ausgabe sie hat
            if [self.cmb_atoms.itemData(i) for i in range(self.cmb_atoms.count())] != modes:
                self.cmb_atoms.clear()
                for k in modes:
                    self.cmb_atoms.addItem(T("nbo_atoms_" + k), k)
            self.cmb_atoms.setCurrentIndex(max(0, self.cmb_atoms.findData(st["atoms"])))
            self.cmb_spin.setCurrentIndex(max(0, self.cmb_spin.findData(st["spin"])))
            self._form_display.setRowVisible(self.cmb_spin, open_)
            # Anzeige = tatsächlich gezeigte Quelle (fehlt NRT, zeigt das Bild Wiberg und das Feld sagt es)
            self.cmb_bonds.setCurrentIndex(max(0, self.cmb_bonds.findData(bond_source(st, d0) if d0 else st["bonds"])))
            self.sp_thr.setValue(st["thr"])
            self.sp_dec.setValue(st["dec"])
            self.ed_els.setText(st["els"])
            self.sp_e2.setValue(st["e2_min"])
            self.sp_rs.setValue(st["rs_max"])
            self.cb_h.setChecked(st["show_h"])
            self.cb_hlab.setChecked(st["h_labels"])
            for b, k in ((self.btn_q, "color_q"), (self.btn_bo, "color_bo")):
                b.setProperty("color", st[k])
                b.setStyleSheet(STYLE.swatch_css(st[k], b.property('cellcss') or ''))
            self.card.setVisible(self.enabled)
            d = self.data(cur)[0] if cur else None
            structs, cml_note = self.structures(cur, d) if d else ([], "")
            self.display.setVisible(self.enabled and d is not None)
            self.lbl_files.setText("\n".join(self.notes(cur, d, structs, cml_note)) if d else
                                   (self.data(cur)[1] if cur else ""))
            self._fill(d, structs)
        finally:
            self._loading = False

    def _fill(self, d, structs):
        if self.mouse is not None:
            self.mouse.disconnect()
            self.mouse = None
        self.F = None
        self.stack.setCurrentIndex(1 if d is not None else 0)
        if d is None:
            self.txt_si.setText("")
            return
        st = self.st
        keep = {self.pg_fig, self.pg_npa, self.pg_si}
        try:
            self.F = self.build(self.fig, d)
            self.mouse = XRAY.XrayMouse(self.F, _Mouse(self))
            self.lbl_fig.setText(T("nbo_fig_hint"))
        except Exception as ex:
            self.fig.clear()
            self.lbl_fig.setText("⚠ " + str(ex))
        self.host.set_figure_size(*self.fig.get_size_inches())
        self.canvas.draw_idle()
        if structs:
            keep.add(self.pg_rs)
            self.build_rs(self.rs_fig, d, structs)
            self.rs_host.set_figure_size(*self.rs_fig.get_size_inches())
            self.rs_canvas.draw_idle()
        rows = [(f"{a['el']}{a['num']}", fmt(a["charge"], 5), a["core"], a["valence"], a["rydberg"], a["total"],
                 minus(a.get("spin", ""))) for a in d["npa"]]
        self._set(self.tbl_npa, rows, hide=() if d.get("spin") else (6,))
        self.lbl_npa.setText(T("nbo_npa_note"), plain=True)
        vs = views(d, st["spin"])
        sp_hide = () if d.get("spin") else (0,)          # Spalte Spin nur offenschalig
        if any(v["nbos"] for _, v in vs):
            keep.add(self.pg_nbo)
            STYLE.fill_summary(self.tbl_lewis, [(lab, T("nbo_lewis_" + k.split()[0].lower()), v, p_)
                                                for lab, sec in vs for k, v, p_ in sec["lewis"]], hidden=sp_hide)
            self._set(self.tbl_nbo, [(lab,) + r_ for lab, sec in vs for r_ in nbo_rows(sec)], hide=sp_hide)
            self.lbl_nbo.setText(T("nbo_list_note"), plain=True)
        if any(v["e2"] for _, v in vs):
            keep.add(self.pg_e2)
            rows = [(lab,) + r_ for lab, sec in vs for r_ in e2_rows(sec, st["e2_min"])]
            self._set(self.tbl_e2, [(lab, a, b, e, minus(de), minus(f_)) for lab, a, b, e, de, f_ in rows],
                      hide=sp_hide)
            self.lbl_e2.setText(T("nbo_e2_note", n=len(rows), m=sum(len(v["e2"]) for _, v in vs),
                                  thr=f"{st['e2_min']:.1f}", out=vs[0][1]["e2_thr"] or "?"), plain=True)
        if d["nrt"]:
            keep.add(self.pg_nrt)
            nrt = d["nrt"]
            rs = [(str(r["rs"]), r["weight"], compact(r["change"]) or "–") for r in nrt["rs"]]
            if nrt["others"]:
                rs.append((T("nbo_others"), nrt["others"], ""))
            self._set(self.tbl_rs, rs)
            self._set(self.tbl_bo, [(f"{d['nrt']['els'].get(a, '')}{a}–{d['nrt']['els'].get(b, '')}{b}", t, c, i)
                                    for a, b, t, c, i in NBO.nrt_bonds(nrt, st["thr"])])
            self.lbl_nrt.setText(T("nbo_nrt_note", thr=f"{st['thr']:.2f}",
                                   par="; ".join(f"{k}: {v}" for k, v in nrt["settings"])), plain=True)
        w = wiberg_of(d, st["spin"]) or d["wiberg"]
        if w:
            keep.add(self.pg_wb)
            self._set(self.tbl_wb, [(f"{w['els'][a]}{a}–{w['els'][b]}{b}", v) for a, b, v in NBO.wiberg_bonds(w, st["thr"])])
            self._set(self.tbl_wbt, [(f"{w['els'][k]}{k}", w["totals"][k]) for k in sorted(w["els"])])
            self.lbl_wb.setText(T("nbo_wb_note", thr=f"{st['thr']:.2f}")
                                + (" " + T("nbo_wb_spin_" + st["spin"]) if d.get("spin") else "")
                                + (" " + T("nbo_wb_spin_missing") if w is not wiberg_of(d, st["spin"]) else ""),
                                plain=True)
        self._show_pages(keep)
        name = self.compound_name()
        self.txt_si.setText(re.sub(r"<[^>]+>", "", "\n\n".join(x for x in self.si_texts(d, structs, name) if x)))

    @staticmethod
    def _set(t, rows, hide=()):
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                if t.elide_col == j or j == 0:
                    it.setToolTip(XRAY.to_html(v) if "^{" in v else v)
                t.setItem(i, j, it)
        for c in range(t.columnCount()):
            t.setColumnHidden(c, c in hide)
        t.fit()

    # -- Texte ---------------------------------------------------------------------------------
    def compound_name(self):
        return (getattr(self.tab.main, "compound", None) or {}).get("name") or "X"

    def level(self, d):
        from elucida.tabs.dft_pages import level_of_theory
        kw = [" ".join(w for w in k.split() if w.upper().lstrip("!") not in ("NBO", "NPA")) for k in d["keywords"]]
        return level_of_theory(dict(program="ORCA", keywords=kw))

    def caption(self, d, name):
        st, parts = self.st, []
        if st["atoms"] == "charge" or (st["atoms"] == "spin" and not d.get("spin")):
            parts.append(f"natural charges (NPA, {TABS.color_name(st['color_q'])})")
        elif st["atoms"] == "spin":
            parts.append(f"natural spin densities (NPA, {TABS.color_name(st['color_q'])})")
        src = bond_source(st, d)
        if src == "nrt":
            parts.append(f"total natural bond orders from NRT ({TABS.color_name(st['color_bo'])}, "
                         f"≥ {st['thr']:.2f})")
        elif src == "wiberg":
            spin = {"alpha": "α-spin ", "beta": "β-spin "}.get(st["spin"], "") \
                if d.get("spin") and wiberg_of(d, st["spin"]) else ""        # α/β nur offenschalig
            parts.append(f"{spin}Wiberg bond indices in the NAO basis ({TABS.color_name(st['color_bo'])}, "
                         f"≥ {st['thr']:.2f})")
        lev = self.level(d)
        what = " and ".join(parts) if parts else "NBO analysis"
        return (f"{what[0].upper() + what[1:]} of <b>{html.escape(name)}</b>"
                + (f" at the {html.escape(lev)} level of theory." if lev else "."))

    def rs_caption(self, d, structs, name):
        n = min(len(structs), self.st["rs_max"])
        return (f"{'Leading' if n < len(structs) else 'All'} {n} resonance structures of <b>{html.escape(name)}</b> "
                f"from the CML file of the NRT analysis with their weights; formal charges (circled +/−) follow from the "
                f"bonds and lone pairs of each structure.")

    def methods(self, d):
        """Methodentext: Programm, NBO-Version, Zitate wie in der Ausgabe gedruckt, Niveau, Schlüsselwörter."""
        lev = self.level(d)
        cite = f" ({d['nbo_cite']})" if d["nbo_cite"] else ""
        ocite = f" ({d['orca_cite']})" if d["orca_cite"] else ""
        txt = (f"Natural bond orbital (NBO) analysis was performed with NBO {d['nbo_version']}{cite} as interfaced with "
               f"ORCA {d['version']}{ocite}" + (f" at the {lev} level of theory" if lev else "") + ".")
        if d.get("spin"):
            txt += (f" Open-shell wavefunction (multiplicity {d['mult']}); the natural population analysis gives "
                    "natural spin densities, NBOs and E(2) are listed separately for α and β spin.")
        if d["nbo_keys"]:
            txt += f" NBO keywords: {d['nbo_keys']}."
        if d["nrt"] and d["nrt"]["settings"]:
            txt += " NRT: " + "; ".join(f"{k.lower()} {v}" for k, v in d["nrt"]["settings"]) + "."
        if d["e2"]:
            txt += (f" Second-order perturbation energies E(2) are listed from {self.st['e2_min']:.1f} kcal mol-1 "
                    f"(printing threshold of the output: {d['e2_thr']} kcal mol-1).")
        return txt

    def si_texts(self, d, structs, name):
        return [self.methods(d), "Figure: " + self.caption(d, name),
                ("Figure: " + self.rs_caption(d, structs, name)) if structs else ""]

    def copy_si(self):
        cur = self.entry()
        d = self.data(cur)[0] if cur else None
        if d is None:
            return
        from elucida.tabs.ir_ea import copy_rich
        structs = self.structures(cur, d)[0]
        parts = [x for x in self.si_texts(d, structs, self.compound_name()) if x]
        copy_rich("\n\n".join(re.sub(r"<[^>]+>", "", p) for p in parts), "".join(f"<p>{p}</p>" for p in parts))
        self.tab.main.statusBar().showMessage(T("nbo_copied"), 4000)

    # -- Export / SI ---------------------------------------------------------------------------
    def items(self):
        """[(Eintrag, Daten, Strukturen, Namensteil)] aller lesbaren Dateien."""
        out = []
        good = []
        for f in self.st["files"]:
            d, err = self.data(f)
            if d is None:                      # unlesbare Ausgabe: im Export mit Datei und Grund melden
                self.tab.main.skip_part(err, f["file"])
            else:
                good.append((f, d))
        stems = [Path(f["file"]).stem for f, _ in good] if len(good) > 1 else [""] * len(good)
        parts = [self._short(s_) for s_ in stems]
        if len(set(parts)) < len(parts):                # gekürzt nicht mehr eindeutig: ganzer Dateiname
            parts = stems
        for (f, d), part in zip(good, parts):
            out.append((f, d, self.structures(f, d)[0], part))
        return out

    def _short(self, stem):
        """Dateiname ohne doppelte Namensteile (Verbindung, „NBO“): S3_NBO -> "", S3_cation_NBO -> "cation"."""
        cmp = TABS.core.safe_name(self.compound_name())
        if cmp and stem.startswith(cmp + "_"):
            stem = stem[len(cmp) + 1:]
        return "_".join(t for t in stem.split("_") if t.upper() != "NBO")

    def _with(self, f, fn):
        """fn() mit `f` als gewählter Datei (Ansicht, Labels gehören zur gewählten); danach zurück."""
        old = self.st["current"]
        self.st["current"] = f["file"]
        try:
            return fn()
        finally:
            self.st["current"] = old

    def export_to(self, base: Path):
        """<base>_NBO(.pdf …), _NBO_resonance, CSV aller Tabellen (Werte wie in der Ausgabe)."""
        files = []
        for f, d, structs, part in self.items():
            stem = base.with_name(base.name + "_NBO" + (f"_{TABS.core.safe_name(part)}" if part else ""))
            if d.get("geometry"):                        # ohne Geometrie nur die CSV-Tabellen
                fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                FigureCanvasAgg(fig)
                F = self._with(f, lambda: self.build(fig, d, interactive=False))
                F.cfg["output"] = str(PRJ.with_ext(stem, "." + F.cfg["_main_fmt"]))
                files += F.export()
            if structs:
                fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                FigureCanvasAgg(fig)
                self._with(f, lambda: self.build_rs(fig, d, structs))
                cfg = self.tab.base_cfg()
                for e in [cfg["_main_fmt"]] + cfg["extra_formats"]:
                    p = stem.with_name(stem.name + "_resonance." + e)
                    fig.savefig(p, dpi=cfg["dpi"], facecolor="white")
                    files.append(p)
            files += self.write_csv(stem, d)
        return files

    def write_csv(self, stem, d):
        def w(suffix, head, rows):
            return TBL.write_csv(stem.with_name(stem.name + suffix), head, rows)
        op = bool(d.get("spin"))
        out = [w("_NPA.csv", ["atom", "natural charge [e]", "core", "valence", "Rydberg", "total"]
                 + (["natural spin density"] if op else []),
                 [(f"{a['el']}{a['num']}", a["charge"], a["core"], a["valence"], a["rydberg"], a["total"])
                  + ((a.get("spin", ""),) if op else ()) for a in d["npa"]])]
        sp = [("alpha" if lab == "α" else "beta" if lab == "β" else "", sec) for lab, sec in views(d, "total")]
        if any(sec["nbos"] for _, sec in sp):
            out.append(w("_list.csv", (["spin"] if op else []) + ["NBO", "type", "occupancy [e]", "energy [Eh]",
                                                                   "hybrids"],
                         [([lab] if op else []) + [k, NBO.nbo_label(e["type"], e["n"], e["atoms"]), e["occ"],
                                                   e.get("energy", ""), NBO.plain(e["hyb"])]
                          for lab, sec in sp for k, e in sorted(sec["nbos"].items())]))
        if any(sec["e2"] for _, sec in sp):
            out.append(w("_E2.csv", (["spin"] if op else []) + ["donor NBO", "donor", "acceptor NBO", "acceptor",
                                                                 "E(2) [kcal mol^-1]", "E(j)-E(i) [a.u.]", "F(i,j) [a.u.]"],
                         [([lab] if op else []) + [r["donor"], NBO.nbo_label(r["d_type"], r["d_n"], r["d_atoms"]),
                                                   r["acceptor"], NBO.nbo_label(r["a_type"], r["a_n"], r["a_atoms"]),
                                                   r["e2"], r["de"], r["f"]]
                          for lab, sec in sp for r in sec["e2"]]))
        nrt = d["nrt"]
        if nrt:
            out.append(w("_NRT_weights.csv", ["RS", "weight [%]", "added (removed) vs. RS 1"],
                         [(r["rs"], r["weight"], compact(r["change"])) for r in nrt["rs"]]
                         + ([("others", nrt["others"], "")] if nrt["others"] else [])))
            out.append(w("_NRT_bond_orders.csv", ["atom i", "atom j", "total", "covalent", "ionic"],
                         [(f"{nrt['els'].get(a, '')}{a}", f"{nrt['els'].get(b, '')}{b}", t, c, i)
                          for (a, b), (t, c, i) in sorted(nrt["bo"].items())]))
            if nrt["val"]:
                out.append(w("_NRT_valencies.csv", ["atom", "valency", "covalency", "electrovalency",
                                                    "electron count", "formal charge"],
                             [(f"{v['el']}{v['num']}", v["valency"], v["covalency"], v["electrovalency"], v["count"],
                               v["formal"]) for v in nrt["val"]]))
        for tag, wb in (("", d["wiberg"]), ("_alpha", wiberg_of(d, "alpha") if op else None),
                        ("_beta", wiberg_of(d, "beta") if op else None)):
            if wb:                                       # volle Matrix wie gedruckt, dazu die Summen je Atom
                ks = sorted(wb["els"])
                out.append(w(f"_Wiberg{tag}_matrix.csv", ["atom"] + [f"{wb['els'][k]}{k}" for k in ks],
                             [[f"{wb['els'][i]}{i}"] + [wb["matrix"][(i, j)] for j in ks] for i in ks]))
                out.append(w(f"_Wiberg{tag}_totals.csv", ["atom", "Wiberg bond index total"],
                             [(f"{wb['els'][k]}{k}", wb["totals"][k]) for k in ks]))
        return out

    def docx_blocks(self, img_dir):
        """Word (einspaltig): je Datei Methodentext, Abbildung(en) mit Unterschrift, Tabellen NPA, E(2) ab der
        Schwelle, NRT-Gewichte und -Bindungsordnungen (ab der Schwelle der Abbildung)."""
        items = self.items()
        if not items:
            return []
        name = self.compound_name()
        blocks = [("columns", 1)]
        for f, d, structs, part in items:
            nm = f"{name} ({part.replace('_', ' ')})" if part else name     # zwei Rechnungen: Unterschriften unterscheidbar
            blocks += [("heading", "NBO analysis" + (f" ({part})" if part else "")),
                       ("text", html.escape(self.methods(d)).replace("E(2)", "<i>E</i>(2)"))]
            svg = Path(img_dir) / f"{TABS.core.safe_name(name)}_nbo{('_' + TABS.core.safe_name(part)) if part else ''}.svg"
            if d.get("geometry"):                        # ohne Geometrieblock keine Abbildung, Tabellen bleiben
                fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                FigureCanvasAgg(fig)
                F = self._with(f, lambda: self.build(fig, d, interactive=False))
                blocks += [("image",) + XRAY.save_tight(F, svg), ("figcap", self.caption(d, nm))]
            if structs:
                fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                FigureCanvasAgg(fig)
                self._with(f, lambda: self.build_rs(fig, d, structs))
                svg2 = svg.with_name(svg.stem + "_resonance.svg")
                fig.savefig(svg2, facecolor="white")
                png = svg2.with_suffix(".png")
                fig.savefig(png, dpi=300, facecolor="white")
                w_cm, h_cm = (v * 2.54 for v in fig.get_size_inches())
                blocks += [("image", str(png), w_cm, h_cm, str(svg2)), ("figcap", self.rs_caption(d, structs, nm))]
            op = bool(d.get("spin"))
            blocks += [("tabcap", "Natural charges" + (" and spin densities" if op else "") + " (NPA) of",
                        nm),
                       ("params", ["Atom", "*q* [e]", "Core", "Valence", "Rydberg", "Total"] + (["Spin density"] if op else []),
                        [[f"{a['el']}{a['num']}", minus(a["charge"]), a["core"], a["valence"], a["rydberg"], a["total"]]
                         + ([minus(a.get("spin", ""))] if op else []) for a in d["npa"]], {"fit": True})]
            rows = [(lab,) + r_ for lab, sec in views(d, "total") for r_ in e2_rows(sec, self.st["e2_min"])]
            if rows:
                blocks += [("tabcap", f"Second-order perturbation energies *E*(2) ≥ {self.st['e2_min']:.1f} "
                                      "kcal mol^{−1} of", nm),
                           ("params", (["Spin"] if op else []) + ["Donor", "Acceptor", "*E*(2) [kcal mol^{−1}]",
                                                                  "*E*(j)−*E*(i) [a.u.]", "*F*(i,j) [a.u.]"],
                            [([lab] if op else []) + [XRAY.esc_markup(a), XRAY.esc_markup(b), e, minus(de), minus(f_)]
                             for lab, a, b, e, de, f_ in rows], {"fit": True})]
            nrt = d["nrt"]
            if nrt:
                blocks += [("tabcap", "NRT resonance weights of", nm),
                           ("params", ["RS", "Weight [%]", "Added (removed) vs. RS 1"],
                            [[str(r["rs"]), r["weight"], XRAY.esc_markup(compact(r["change"]))] for r in nrt["rs"]]
                            + ([["others", nrt["others"], ""]] if nrt["others"] else []), {"fit": True})]
                bo = NBO.nrt_bonds(nrt, self.st["thr"])
                if bo:
                    blocks += [("tabcap", f"Natural bond orders (NRT, total ≥ {self.st['thr']:.2f}) of",
                                nm),
                               ("params", ["Bond", "Total", "Covalent", "Ionic"],
                                [[f"{nrt['els'].get(a, '')}{a}–{nrt['els'].get(b, '')}{b}", t, c, i]
                                 for a, b, t, c, i in bo], {"fit": True})]
            wb = d["wiberg"]
            rows = NBO.wiberg_bonds(wb, self.st["thr"]) if wb else []
            if rows:
                blocks += [("tabcap", f"Wiberg bond indices in the NAO basis (NBO, ≥ {self.st['thr']:.2f}) of",
                            nm),
                           ("params", ["Bond", "Wiberg bond index"],
                            [[f"{wb['els'][a]}{a}–{wb['els'][b]}{b}", v] for a, b, v in rows], {"fit": True})]
        return blocks
