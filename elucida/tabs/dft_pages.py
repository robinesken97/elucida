"""elucida/tabs/dft_pages.py - Reiter des DFT-Tabs neben „Abbildung“: Energieprofil (Stufen aus Opt/Freq, optional
Einzelpunkt; IRC) und NICS (Gaussian-NMR mit Geisteratomen). Zustand im DFT-Zustand: `profile`, `nics`.

Energieprofil: G = E(SP) + (G − E_el)(Opt/Freq), H analog, ΔE = E(SP); Einzelpunkt über gleiche Atome/Koordinaten
(± 0.02 Å, nie über Dateinamen). Haben einige Spezies einen Einzelpunkt, fallen die übrigen weg (nie mischen).
IRC (ORCA): nur ΔE_el; x = Reaktionskoordinate [Å] = aufsummierte kartesische Abstände aufeinanderfolgender Bilder
der Trajektorie (TS = 0, rückwärts negativ) oder eine Bindungslänge aus „IRC PATH SUMMARY“.
NICS = −σ_iso, NICSzz = −n·σ·n mit n = Normale der Ebene durch die Schweratome in der Nähe des Bq.
"""
from __future__ import annotations

import csv
import html
import re
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from elucida.app import project as PRJ
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS
from elucida.formats.calc import parse_irc, parse_nics, read_text, read_xyz
from elucida.tabs import base as TABS

HARTREE_KCAL = 627.5094740631            # kcal/mol je Hartree (CODATA 2018)
LEVEL_W = 0.35                           # halbe Stufenbreite (Schritte)
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
        g = QGroupBox(T("dft_profile"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        self.cmb_mode = QComboBox()
        for k in ("levels", "irc"):
            self.cmb_mode.addItem(T("dft_prof_mode_" + k), k)
        self.cmb_y = QComboBox()
        for k in KINDS:
            self.cmb_y.addItem(KINDS[k][0], k)
        self.cmb_y.setToolTip(T("dft_prof_y_tip"))
        for w in (QLabel(T("dft_prof_mode")), self.cmb_mode, QLabel(T("dft_prof_y")), self.cmb_y):
            row.addWidget(w)
        row.addStretch(1)
        v.addLayout(row)
        self.tbl_sp = QTableWidget(0, 5)
        self.tbl_sp.setHorizontalHeaderLabels([T("dft_prof_species"), T("dft_prof_label"), T("dft_prof_step"),
                                               T("dft_prof_paths"), T("dft_prof_sp")])
        self.tbl_sp.verticalHeader().setVisible(False)
        self.tbl_sp.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tbl_sp.setToolTip(T("dft_prof_tbl_tip"))
        self.tbl_sp.itemChanged.connect(self.species_edited)
        v.addWidget(self.tbl_sp)
        self.irc_list = QListWidget()
        self.irc_list.setToolTip(T("dft_irc_tip"))
        v.addWidget(self.irc_list)
        row = QHBoxLayout()
        self.cmb_irc_x = QComboBox()
        self.cmb_irc_ref = QComboBox()
        self.lbl_irc_x, self.lbl_irc_ref = QLabel(T("dft_irc_x")), QLabel(T("dft_irc_ref"))
        for w in (self.lbl_irc_x, self.cmb_irc_x, self.lbl_irc_ref, self.cmb_irc_ref):
            row.addWidget(w)
        row.addStretch(1)
        v.addLayout(row)
        self.color_row = QHBoxLayout()
        v.addLayout(self.color_row)
        self.canvas_fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.canvas = FigureCanvasQTAgg(self.canvas_fig)
        self.canvas.setMinimumHeight(320)
        v.addWidget(self.canvas, 2)
        self.lbl_prof = QLabel("")
        self.lbl_prof.setWordWrap(True)
        self.lbl_prof.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_prof)
        row = QHBoxLayout()
        self.btn_sp_add = QPushButton(T("dft_prof_sp_add"))
        self.btn_sp_add.clicked.connect(self.add_sp)
        self.btn_sp_rm = QPushButton(T("dft_prof_sp_rm"))
        self.btn_sp_rm.clicked.connect(self.clear_sp)
        self.btn_irc_add = QPushButton(T("dft_irc_add"))
        self.btn_irc_add.clicked.connect(self.add_irc)
        self.btn_irc_up = QPushButton(T("dft_irc_up"))
        self.btn_irc_up.clicked.connect(self.irc_up)
        self.btn_irc_rm = QPushButton(T("remove"))
        self.btn_irc_rm.clicked.connect(self.remove_irc)
        for b in (self.btn_sp_add, self.btn_sp_rm, self.btn_irc_add, self.btn_irc_up, self.btn_irc_rm):
            row.addWidget(b)
        v.addLayout(row)
        self.cmb_mode.currentIndexChanged.connect(self.combo_changed)
        self.cmb_y.currentIndexChanged.connect(self.combo_changed)
        self.cmb_irc_x.currentIndexChanged.connect(self.combo_changed)
        self.cmb_irc_ref.currentIndexChanged.connect(self.combo_changed)
        return g

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

    def sp_calcs(self):
        """[(Pfad, Rechnung, Geometrie)] der geladenen Einzelpunkte (unlesbare fehlen)."""
        out = []
        for p in self.prof["sp"]:
            if Path(p).exists():
                try:
                    c = self.tab.calc_file(p)
                    if c.get("energy") is not None:              # abgebrochener Einzelpunkt zählt nicht
                        out.append((p, c, self.tab.calc_geom(p)[0]))
                except Exception:
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
        for i, e in enumerate(self.calc_entries()):
            d = self.spec(e, i)
            if not d["on"]:
                continue
            hit = self.sp_for(e, sps)
            out.append(dict(uid=e["uid"], label=d["label"], step=int(d["step"]),
                            paths=[s.strip() for s in str(d["paths"]).split(",") if s.strip()] or ["A"],
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
        rows, notes = profile_rows(items, self.prof["y"]) if items else ([], [])
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
            out.append(dict(c, label=d.get("label") or Path(d["file"]).stem))
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
        TABS.core.setup_fonts(TABS.plt, cfg)
        cfg["legend"] = False
        cfg["xlabel"] = "reaction coordinate" + (" [Å]" if kind == "irc_rc" else "")
        return cfg

    def build_levels(self, fig):
        rows, paths, notes = self.levels_spec()
        if not rows:
            return None, notes
        y = self.prof["y"]
        cfg = self.cfg("levels")
        cfg["ylabel"] = KINDS[y][0] + " [kcal mol$^{-1}$]"
        vals = [r["value"] for r in rows]
        span = (max(vals) - min(vals)) or 10.0
        steps = [r["step"] for r in rows]
        cfg["xlim"] = [min(steps) - 0.8, max(steps) + 0.8]
        cfg["ylim"] = [min(vals) - 0.18 * span, max(vals) + 0.15 * span]
        curves = []
        for k, p in enumerate(paths):
            col = self.path_color(p, k)
            rs = [r for r in rows if p in r["paths"]]
            for a, b in zip(rs, rs[1:]):
                curves.append(dict(x=np.array([a["step"] + LEVEL_W, b["step"] - LEVEL_W]),
                                   y=np.array([a["value"], b["value"]]), color=col, ls="--", lw=0.8, label=None))
        for r in rows:
            col = self.path_color(r["paths"][0], paths.index(r["paths"][0])) if len(r["paths"]) == 1 else "black"
            curves.append(dict(x=np.array([r["step"] - LEVEL_W, r["step"] + LEVEL_W]),
                               y=np.array([r["value"]] * 2), color=col, ls="-", lw=2.2, label=None))
        F = TABS.X.SimpleFigure(TABS.plt, cfg, curves, [], {}, fig=fig, legend=False)
        F.ax.set_xticks([])
        fs = cfg["labels"]["font_size"]
        off = 0.025 * (cfg["ylim"][1] - cfg["ylim"][0])
        for r in rows:
            F.ax.text(r["step"], r["value"] + off, kcal(r["value"]), ha="center", va="bottom", fontsize=fs)
            F.ax.text(r["step"], r["value"] - off, r["label"], ha="center", va="top", fontsize=fs)
        return F, notes

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
        curves, marks, x_end = [], [], None
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
            curves.append(dict(x=x, y=y, color="black", ls="-", lw=1.2, label=None))
            ts = c["ts"]
            marks.append((x[ts], y[ts], (c["E"][ts] - c["E"][0]) * HARTREE_KCAL, (c["E"][ts] - c["E"][-1]) * HARTREE_KCAL))
        if not curves:
            return None, notes
        xs = np.concatenate([c["x"] for c in curves])
        ys = np.concatenate([c["y"] for c in curves])
        span = float(ys.max() - ys.min()) or 10.0
        cfg["xlim"] = [float(xs.min()), float(xs.max())]
        cfg["ylim"] = [float(ys.min()) - 0.08 * span, float(ys.max()) + 0.2 * span]
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
        sps = self.sp_calcs()
        es = self.calc_entries()
        self.tbl_sp.setRowCount(len(es))
        for i, e in enumerate(es):
            d = self.spec(e, i)
            hit = self.sp_for(e, sps)
            it = QTableWidgetItem(e.get("name") or Path(e["file"]).stem)
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Checked if d["on"] else Qt.Unchecked)
            it.setData(Qt.UserRole, e["uid"])
            self.tbl_sp.setItem(i, 0, it)
            for j, v in ((1, d["label"]), (2, str(d["step"])), (3, d["paths"])):
                self.tbl_sp.setItem(i, j, QTableWidgetItem(v))
            it = QTableWidgetItem(Path(hit[0]).name if hit else "–")
            it.setFlags(Qt.ItemIsEnabled)
            self.tbl_sp.setItem(i, 4, it)
        self.tbl_sp.resizeColumnsToContents()
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
        for w in (self.tbl_sp, self.cmb_y, self.btn_sp_add, self.btn_sp_rm):
            w.setVisible(lv)
        for w in (self.irc_list, self.cmb_irc_x, self.cmb_irc_ref, self.lbl_irc_x, self.lbl_irc_ref,
                  self.btn_irc_up, self.btn_irc_rm):
            w.setVisible(not lv)
        self.btn_sp_rm.setEnabled(bool(p["sp"]))
        while self.color_row.count():
            w = self.color_row.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        rows, paths, _ = self.levels_spec() if lv else ([], [], [])
        if len(paths) > 1:
            self.color_row.addWidget(QLabel(T("dft_prof_colors")))
            for k, path in enumerate(paths):
                def pick(c, path=path):
                    self.prof["colors"][path] = c
                    self.changed()
                self.color_row.addWidget(QLabel(path))
                self.color_row.addWidget(TABS.color_button(self.path_color(path, k), pick))
            self.color_row.addStretch(1)
        self._loading = False

    def refresh(self):
        """Vorschau des gewählten Modus neu zeichnen (Exportgröße des Tabs, maßstabsgetreu verkleinert)."""
        try:
            F, notes = self.build(self.canvas_fig)
        except Exception as ex:
            F, notes = None, [str(ex)]
        if F is None:
            self.canvas_fig.clear()
            self.canvas_fig.text(0.5, 0.5, T("dft_prof_empty"), ha="center", va="center", color="gray")
        self.lbl_prof.setText("\n".join("⚠ " + n for n in notes))
        self.canvas.draw_idle()

    # -- NICS ----------------------------------------------------------------------------------------
    def _nics_group(self):
        g = QGroupBox(T("dft_nics"))
        v = QVBoxLayout(g)
        self.nics_list = QListWidget()
        self.nics_list.setMaximumHeight(90)
        v.addWidget(self.nics_list)
        row = QHBoxLayout()
        self.ed_nics_geom = QLineEdit()
        self.ed_nics_geom.setPlaceholderText(T("dft_nics_geom_ph"))
        self.ed_nics_geom.setToolTip(T("dft_nics_geom_tip"))
        self.ed_nics_geom.editingFinished.connect(self.nics_geom_changed)
        row.addWidget(QLabel(T("dft_nics_geom")))
        row.addWidget(self.ed_nics_geom, 1)
        v.addLayout(row)
        self.tbl_nics = QTableWidget(0, 6)
        self.tbl_nics.setHorizontalHeaderLabels([T("dft_nics_file"), "Bq", "h [Å]", "NICS [ppm]", "NICSzz [ppm]",
                                                 T("dft_nics_pair")])
        self.tbl_nics.verticalHeader().setVisible(False)
        self.tbl_nics.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        v.addWidget(self.tbl_nics)
        self.nics_fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.nics_canvas = FigureCanvasQTAgg(self.nics_fig)
        self.nics_canvas.setMinimumHeight(280)
        v.addWidget(self.nics_canvas, 2)
        self.lbl_nics = QLabel("")
        self.lbl_nics.setWordWrap(True)
        self.lbl_nics.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_nics)
        row = QHBoxLayout()
        b = QPushButton(T("dft_nics_add"))
        b.clicked.connect(self.add_nics)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(self.remove_nics)
        row.addWidget(b)
        row.addWidget(b2)
        v.addLayout(row)
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
        self.tbl_nics.resizeColumnsToContents()
        self._loading = False
        try:
            F, notes = self.build_nics(self.nics_fig)
        except Exception as ex:
            F, notes = None, [str(ex)]
        if F is None:
            self.nics_fig.clear()
            self.nics_fig.text(0.5, 0.5, T("dft_nics_empty"), ha="center", va="center", color="gray")
        self.lbl_nics.setText("\n".join("⚠ " + n for n in notes))
        self.nics_canvas.draw_idle()

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
            fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = build(fig)
            if F is not None:
                svg = Path(out_dir) / f"{TABS.core.safe_name(name)}_dft_{key}.svg"
                out += [TABS.si_image(F, svg), ("figcap", cap(name))]
        return out
