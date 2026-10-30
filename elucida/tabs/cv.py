"""elucida/tabs/cv.py - Cyclovoltammetrie: Gamry-Dateien lesen, Redoxpaare auswerten, CV-Tab.

Auswertung je Redoxpaar in einem Potentialfenster [lo, hi]:
  E_pa = Maximum des Stroms im Hinlauf (dE/dt > 0), E_pc = Minimum im Rücklauf (dE/dt < 0),
  Peaklage per Parabel über ±3 Punkte verfeinert; E½ = (E_pa + E_pc)/2, ΔE_p = E_pa − E_pc.
  i_pa, i_pc = Ströme am Peak, ohne Basislinie gemessen von null. Mit Basislinie (Standard):
  Hinpeak gegen eine Gerade durch den Strom vor dem Peak (Hinlauf, bis BL_GAP vor E_p; Ladestrom und
  Untergrund), extrapoliert unter den Peak. Der Ladestrom wechselt am Umkehrpunkt das Vorzeichen (+C·v ->
  −C·v), der Faradaystrom ist dort stetig: Sprung des Stroms am Umkehrpunkt = 2·C·v. Rückbasislinie =
  Hinbasislinie minus dieser Sprung. Der Rückpeak sitzt zusätzlich auf dem abklingenden Faradaystrom des
  Hinlaufs, den korrigiert Nicholson (Anal. Chem. 38 (1966) 1406), angewandt auf die korrigierten Ströme:
  i_r/i_f = (i_r)₀/i_f + 0.485·(i_sp)₀/i_f + 0.086 (i_sp = Strom am Umkehrpotential).
  Keine zweite (extrapolierte) Rückbasislinie zusätzlich zu Nicholson – das wäre doppelt korrigiert.
  Peakpotentiale immer aus dem gemessenen Strom (wie bisher).
Referenzierung: E vs. Fc⁺/Fc = E_gemessen − (E½(Referenz, gemessen) − E°(Referenz vs. Fc⁺/Fc)).
Ströme: IUPAC-Konvention wie aufgezeichnet (Gamry: anodisch positiv); optional invertierbar.
"""
from __future__ import annotations

import csv
import re
import uuid
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

from elucida.core import uvvis as core
from elucida.tabs import base as TABS
from elucida.app.i18n import T
from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.style import HINT_CSS, make_form
from elucida.formats.gamry import (read_gamry)  # noqa: E402,F401  (Leser in elucida/formats)

# Referenzverbindungen: E½ gegen Fc⁺/Fc [V]. Ac₂Fc = 1,1'-Diacetylferrocen; Wert im Programm änderbar
# (lösungsmittelabhängig, gegen Literatur prüfen).
REFERENCES = {"fc": ("Fc", 0.0), "ac2fc": ("Ac₂Fc", 0.49)}
REF_NAMES_EN = {"fc": ("ferrocene", "Fc"), "ac2fc": ("1,1'-diacetylferrocene", "Ac₂Fc")}

# Basislinie endet so weit vor dem Hinpeak: Fuß einer reversiblen Welle bei E½ − 0,12 V < 1 % des Peakstroms
BL_GAP = 0.15
# … und spätestens am Anstieg der Welle: Strom (geglättet) 2 % der Peakhöhe über dem Anfangsstrom des Fensters.
# Nötig für breite Wellen (iR-Abfall, quasi-reversibel; echte THF-Daten mit ΔE_p ≈ 240 mV): dort beginnt der Anstieg
# weit mehr als 0,15 V vor dem Peak, und eine Gerade durch den Fuß überkorrigiert i_p massiv.
BL_ONSET = 0.02
# Nicholson gilt nur, wenn zwischen Hinpeak und Umkehrpotential kein weiterer Prozess liegt (sonst ist i_sp und der
# abklingende Strom ein anderer). Erkennung: Strom steigt im Hinlauf nach dem Peak wieder um > 10 % der Peakhöhe an.
NICHOLSON_RISE = 0.10


def _refine(E, I, k):
    """Peaklage per Parabel durch ±3 Punkte (Raster der Messung ist meist 2–4 mV)."""
    lo, hi = max(0, k - 3), min(len(E), k + 4)
    if hi - lo < 5:
        return float(E[k]), float(I[k])
    try:
        a, b, c = np.polyfit(E[lo:hi], I[lo:hi], 2)
    except (np.linalg.LinAlgError, ValueError):
        return float(E[k]), float(I[k])
    if a == 0:
        return float(E[k]), float(I[k])
    e = -b / (2 * a)
    if not (min(E[lo:hi]) <= e <= max(E[lo:hi])):
        return float(E[k]), float(I[k])
    return float(e), float(np.polyval([a, b, c], e))


def _line_at(E, I, idx, e_at):
    """Gerade durch die Punkte idx, ausgewertet bei e_at (oder None bei zu wenigen Punkten)."""
    if len(idx) < 3 or np.ptp(E[idx]) <= 0:
        return None
    a, b = np.polyfit(E[idx], I[idx], 1)
    return float(a * e_at + b)


def baseline(E, I, k_f, k_turn, fmask, s, gap=BL_GAP):
    """Basislinie für ein Redoxpaar -> dict(a, b, step, e0, ok) oder None.
    Hinbasislinie i_b(E) = a·E + b aus den Punkten des Hinlaufs (fmask) mindestens gap vor dem Hinpeak k_f
    (s = +1: anodisch zuerst). step = Sprung des Ladestroms am Umkehrpunkt k_turn (≥ 0, in Richtung s):
    Rückbasislinie = i_b(E) − s·step."""
    e_pf = E[k_f]
    e_end = e_pf - s * gap
    # Anstieg der Welle: Punkte des Hinlaufs vor dem Peak in Scanrichtung, gleitend gemittelt (5 Punkte)
    run = np.flatnonzero(fmask & (s * (E - e_pf) < 0))
    run = run[np.argsort(s * E[run], kind="stable")]
    if len(run) >= 10:
        y = np.convolve(I[run], np.ones(5) / 5, mode="same")[2:-2]
        i0 = float(np.median(I[run[:5]]))
        h = s * (float(I[k_f]) - i0)
        if h > 0:
            up = np.flatnonzero(s * (y - i0) > BL_ONSET * h)
            if len(up):
                e_on = float(E[run[2 + up[0]]])
                if s * e_on < s * e_end:
                    e_end = e_on
    pre = np.flatnonzero(fmask & (s * (E - e_end) <= 0))
    if len(pre) < 5 or np.ptp(E[pre]) < 0.03:
        return None
    a, b = np.polyfit(E[pre], I[pre], 1)
    # Umkehrpunkt: Gerade durch je 6 Punkte davor/danach, beide bei E_umkehr ausgewertet
    n = len(E)
    before = np.arange(max(0, k_turn - 6), k_turn + 1)
    after = np.arange(k_turn + 1, min(n, k_turn + 8))       # Umkehrpunkt selbst gehört zum Hinlauf
    i_b = _line_at(E, I, before, E[k_turn])
    i_a = _line_at(E, I, after, E[k_turn])
    step = max(0.0, s * (i_b - i_a)) if i_b is not None and i_a is not None else 0.0
    return {"a": float(a), "b": float(b), "step": float(step), "s": s,
            "e0": float(E[pre].min() if s > 0 else E[pre].max()), "e1": float(e_end),
            "i_sp": i_b if i_b is not None else float(I[k_turn])}


def analyze_couple(E, I, lo, hi, use_baseline=False, gap=BL_GAP):
    """Redoxpaar im Fenster [lo, hi] -> dict(epa, epc, e12, dep, ipa, ipc, ratio, edge, …) oder None.
    ratio = Rückpeak/Hinpeak nach Nicholson (1 = chemisch reversibel); Hinlauf = erste Scanrichtung.
    edge = True, wenn ein Peak am Fensterrand liegt (Fenster zu eng oder kein echter Peak).
    ratio_ok = False (ratio = NaN): weiterer Prozess zwischen Hinpeak und Umkehrpotential, Nicholson ungültig.
    use_baseline: i_pa/i_pc/i_sp gegen die Basislinie (siehe Modulkopf); ipa_raw/ipc_raw = Strom am Peak.
    bl = Basislinie (für die Abbildung) oder None; bl_fail = Basislinie verlangt, aber zu wenig Vorlauf."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    dE = np.gradient(E)
    lo, hi = min(lo, hi), max(lo, hi)
    win = (E >= lo) & (E <= hi)
    fw, bw = win & (dE > 0), win & (dE < 0)
    if fw.sum() < 5 or bw.sum() < 5:
        return None
    ka = int(np.flatnonzero(fw)[np.argmax(I[fw])])
    kc = int(np.flatnonzero(bw)[np.argmin(I[bw])])
    epa, ipa = _refine(E, I, ka)
    epc, ipc = _refine(E, I, kc)
    edge_tol = 0.01 * (hi - lo) + 0.004
    edge = any(abs(e - b) < edge_tol for e in (E[ka], E[kc]) for b in (lo, hi))
    edge = edge or epa <= epc                              # E_pa < E_pc: kein Redoxpaar, Fenster falsch
    # Nicholson: Hinlauf = der zuerst durchlaufene Peak dieses Paars (Start innerhalb des Bereichs: nicht unbedingt
    # die erste Scanrichtung), i_sp = Strom am Umkehrpunkt zwischen Hin- und Rückpeak
    anodic_first = ka < kc
    k_f, k_r = (ka, kc) if anodic_first else (kc, ka)
    turn = k_f + int(np.argmax(E[k_f:k_r + 1]) if anodic_first else np.argmin(E[k_f:k_r + 1]))
    s = 1 if anodic_first else -1
    bl, fail = None, False
    ia, ic, i_sp = ipa, ipc, float(I[turn])
    if use_baseline:
        # Vorlauf nur aus dem Abschnitt des Hinpeaks (gleiche Richtung ab dem vorigen Umkehrpunkt)
        other = np.flatnonzero(np.sign(dE[:k_f]) != s)
        seg = np.zeros(len(E), bool)
        seg[(other[-1] + 1 if len(other) else 0):turn + 1] = True
        bl = baseline(E, I, k_f, turn, (fw if anodic_first else bw) & seg, s, gap)
        if bl is None:
            fail = True
        else:
            fwd = lambda e: bl["a"] * e + bl["b"]               # noqa: E731
            rev = lambda e: fwd(e) - s * bl["step"]             # noqa: E731
            ia = ipa - (fwd(epa) if anodic_first else rev(epa))
            ic = ipc - (rev(epc) if anodic_first else fwd(epc))
            i_sp = bl["i_sp"] - fwd(E[turn])
            bl.update(epf=epa if anodic_first else epc, epr=epc if anodic_first else epa)
    i_f, i_r = (abs(ia), abs(ic)) if anodic_first else (abs(ic), abs(ia))
    ratio = (i_r / i_f + 0.485 * abs(i_sp) / i_f + 0.086) if i_f > 0 else float("nan")
    # weiterer Prozess zwischen Hinpeak und Umkehrpunkt (z. B. Referenz oder zweite Welle) -> Verhältnis ungültig
    ratio_ok = True
    if turn - k_f > 10:
        y = s * np.convolve(I[k_f:turn + 1], np.ones(5) / 5, mode="valid")
        h = i_f if i_f > 0 else abs(float(I[k_f]))
        ratio_ok = not np.any(y - np.minimum.accumulate(y) > NICHOLSON_RISE * h)
    if not ratio_ok:
        ratio = float("nan")
    return {"epa": epa, "epc": epc, "e12": (epa + epc) / 2, "dep": epa - epc, "ipa": ia, "ipc": ic,
            "ipa_raw": ipa, "ipc_raw": ipc, "ratio": ratio, "ratio_ok": bool(ratio_ok), "edge": bool(edge),
            "bl": bl, "bl_fail": fail,
            "anodic_first": bool(anodic_first)}


def suggest_couples(E, I, min_rel=0.03, max_sep=0.25):
    """Vorschläge für Redoxpaare: anodische Peaks im Hinlauf mit passendem kathodischen Peak im Rücklauf.
    -> [(lo, hi)] (Fenster ±0.25 V um E½)."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    dE = np.gradient(E)
    scale = np.nanmax(np.abs(I)) or 1.0

    def peaks(mask, sign, half_width=0.15):
        """Lokale Maxima von sign·I im Lauf; Prominenz gegen die Minima in ±half_width V (breite Peaks)."""
        idx = np.flatnonzero(mask)
        y = sign * np.convolve(I, np.ones(5) / 5, mode="same")
        out = []
        for j in range(3, len(idx) - 3):
            k = idx[j]
            if y[k] < y[idx[j - 3:j + 4]].max():
                continue
            left = idx[(E[idx] >= E[k] - half_width) & (E[idx] <= E[k])]
            right = idx[(E[idx] <= E[k] + half_width) & (E[idx] >= E[k])]
            if len(left) < 3 or len(right) < 3:
                continue
            prom = y[k] - max(y[left].min(), y[right].min())
            if prom > min_rel * scale:
                out.append(float(E[k]))
        return out
    an, ca = peaks(dE > 0, 1), peaks(dE < 0, -1)
    out = []
    for a in an:
        cs = [c for c in ca if 0 <= a - c <= max_sep]
        if cs:
            c = max(cs)
            mid = (a + c) / 2
            if not any(lo <= mid <= hi for lo, hi in out):
                out.append((round(mid - 0.25, 2), round(mid + 0.25, 2)))
    return out


def rate_fit(x, y):
    """Lineare Regression (OLS) mit 95-%-KI = t(0,975; n−2)·SE -> dict(slope, ci, intercept, ci_b, r2, n) oder None."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return None
    f = core.linfit(x[ok], y[ok])
    if f is None:                                         # z. B. nur eine Scanrate: keine Steigung
        return None
    t = core.t_quantile(0.975, f["n"] - 2)
    return dict(slope=f["slope"], ci=t * f["se_slope"], intercept=f["intercept"], ci_b=t * f["se_intercept"],
                r2=f["r2"], n=f["n"])


def randles_sevcik(rates_mVs, ipa):
    """i_pa gegen √v (v in V/s): lineare Regression -> (Steigung, Achsenabschnitt, R²) oder None."""
    f = rate_fit(np.sqrt(np.asarray(rates_mVs, float) / 1000.0), ipa)
    return (f["slope"], f["intercept"], f["r2"]) if f else None


def loglog_fit(rates_mVs, ip):
    """log|i_p| gegen log v: Steigung 0,5 = diffusionskontrolliert, 1 = an der Oberfläche gebunden."""
    v, ip = np.asarray(rates_mVs, float), np.abs(np.asarray(ip, float))
    ok = (v > 0) & (ip > 0)
    return rate_fit(np.log10(v[ok] / 1000.0), np.log10(ip[ok]))


def fmt_ci(v, ci, unit=""):
    """Wert ± 95-%-KI, gerundet auf die Genauigkeit des Intervalls (core.fmt_ve)."""
    a, b = core.fmt_ve(v, ci)
    return f"{a} ± {b}{unit}" if b is not None else f"{a}{unit}"


# ----------------------------------------------------------------------------
# CV-Tab
# ----------------------------------------------------------------------------
# hellblau -> blau -> violett -> dunkelrot -> rot (wie übliche Scanraten-Serien)
RATE_CMAP = LinearSegmentedColormap.from_list("rates", ["#56c1f0", "#1a4fd6", "#8a2be2", "#b0102a", "#e8231b"])


_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def axis_ref(text):
    """Referenzelektrode für die Achsenbeschriftung: tiefgestellte Unicode-Ziffern (AgNO₃) fehlen in vielen
    Schriften -> als Mathtext-Index setzen (AgNO$_3$)."""
    return re.sub("[₀-₉]+", lambda m: "$_{" + m.group().translate(_SUB) + "}$", str(text))


def _fmt_e(v, nd=3):
    return f"{v:+.{nd}f}".replace("-", "−")


class CVTab(TABS.FigureTab):
    STATE_KEY = "cv"
    GUIDE, GUIDE_ACTION = "cv", ("guide_add", "add_files")
    TEXT_OPTS = ("fonts", "labels", "label_size", "axes_frame", "struct_frame")
    CAP_FIELDS = ("conc", "solvent", "el", "temp")
    CAP_REMEMBER = ("el",)
    SI_CAPTION = "Cyclic voltammograms of {name}."
    X_RANGE = (-10.0, 10.0, 2, 0.1)
    XRANGE_TEXT = "cv_xrange"
    RESET_KEEP = ("files", "couples", "ref_mode", "ref_uid", "ref_lo", "ref_hi", "ref_compound", "ref_value",
                  "ref_offset", "ref_electrode")           # Messungen, Redoxpaare und Referenzierung bleiben
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=-1.5, x_max=-0.5, ymax=0.0, files=[], couples=[], cycle=1,
                         ref_mode="none", ref_uid=None, ref_lo=0.3, ref_hi=0.8, ref_compound="ac2fc",
                         ref_value=REFERENCES["ac2fc"][1], ref_offset=0.0, ref_electrode="Ag/AgNO₃",
                         gradient=True, density=False, show_e12=True, arrow=True, invert=False,
                         plot="cv", stack=False, stack_gap=1.0, e12_each=False, y_axis="auto", peak_labels="e12",
                         struct_w=18.0, baseline=True, bl_gap=BL_GAP, show_bl=False,
                         cap_conc="", cap_solvent="", cap_el="", cap_temp="rt")

    # CV | ΔE_p gegen v | Randles-Ševčík | log i_p gegen log v | i_r/i_f gegen v | Trumpet-Plot
    PLOTS = ("cv", "dep", "rs", "loglog", "ratio", "trumpet")
    MARKERS = ("s", "o", "^", "v", "D", "p")

    # -- Bedienelemente ------------------------------------------------------------

    def arrange(self):
        super().arrange()
        g = STYLE.split_group(self.group_titled("cv_analysis"), self.cmb_ref, self.ed_electrode, T("grp_refs"))
        self.fold(g, "refs", ("ref_mode", "ref_uid", "ref_lo", "ref_hi", "ref_compound", "ref_value", "ref_offset",
                              "ref_electrode"))
        g = STYLE.split_group(self.group_titled("cv_display"), self.cb_gradient, self.cb_invert, T("grp_more_display"))
        self.fold(g, "more", ("gradient", "density", "show_e12", "arrow", "invert"))
        self.to_right(self.group_titled("cv_results"), T("cv_results"))
    def build_controls(self):
        st = self.st
        self._offset = 0.0
        self.results = []
        g = QGroupBox(T("cv_files"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("cv_add"), self.add_files), ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                        (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), "v [mV/s]", T("cv_group")])
        self.table.horizontalHeaderItem(4).setToolTip(T("cv_group_tip"))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(140)
        self.table.itemChanged.connect(self.table_edited)
        self.table.currentCellChanged.connect(lambda *_: self.show_file_ref())
        v.addWidget(self.table)
        self.lv.addWidget(g)

        # Referenz je Messung (z. B. jedes Lösungsmittel gegen sein eigenes Ac₂Fc/Fc)
        self.det = QGroupBox(T("cv_file_ref"))
        f = make_form(self.det)
        self.cmb_fref = QComboBox()
        for key in ("global", "internal", "manual"):
            self.cmb_fref.addItem(T("cv_fref_" + key), key)
        f.addRow(T("cv_ref"), self.cmb_fref)
        self.cmb_fref_file = QComboBox()
        self.lbl_fref_file = QLabel(T("cv_ref_file"))
        f.addRow(self.lbl_fref_file, self.cmb_fref_file)
        row = QHBoxLayout()
        self.sp_fref_lo = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=0.3)
        self.sp_fref_hi = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=0.8)
        for w_ in (self.sp_fref_lo, QLabel("–"), self.sp_fref_hi):
            row.addWidget(w_)
        self.lbl_fref_win = QLabel(T("cv_ref_window"))
        f.addRow(self.lbl_fref_win, row)
        row = QHBoxLayout()
        self.cmb_fcompound = QComboBox()
        for key, (name, _) in REFERENCES.items():
            self.cmb_fcompound.addItem(name, key)
        self.cmb_fcompound.addItem(T("cv_ref_custom"), "custom")
        self.sp_fref_value = QDoubleSpinBox(decimals=3, minimum=-3, maximum=3, singleStep=0.01, suffix=" V",
                                            value=REFERENCES["ac2fc"][1])
        self.sp_fref_value.setToolTip(T("cv_ref_value_tip"))
        row.addWidget(self.cmb_fcompound, 1)
        row.addWidget(self.sp_fref_value)
        self.lbl_fcompound = QLabel(T("cv_ref_compound"))
        f.addRow(self.lbl_fcompound, row)
        self.sp_foffset = QDoubleSpinBox(decimals=3, minimum=-5, maximum=5, singleStep=0.01, suffix=" V")
        self.sp_foffset.setToolTip(T("cv_offset_tip"))
        self.lbl_foffset = QLabel(T("cv_offset"))
        f.addRow(self.lbl_foffset, self.sp_foffset)
        row = QHBoxLayout()
        self.lbl_fstruct = QLabel("–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        b1.clicked.connect(self.choose_file_structure)
        b2.clicked.connect(lambda: self.set_file_structure(None))
        row.addWidget(self.lbl_fstruct, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        f.addRow(T("structure"), row)
        self.cb_fstruct_color = QCheckBox(T("ov_struct_color"))
        self.cb_fstruct_color.toggled.connect(self.file_ref_changed)
        f.addRow(self.cb_fstruct_color)
        self.lbl_fref_info = QLabel("")
        self.lbl_fref_info.setWordWrap(True)
        self.lbl_fref_info.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_fref_info)
        self.lv.addWidget(self.det)
        for w_ in (self.sp_fref_lo, self.sp_fref_hi, self.sp_fref_value, self.sp_foffset):
            w_.valueChanged.connect(self.file_ref_changed)
        for w_ in (self.cmb_fref, self.cmb_fref_file):
            w_.currentIndexChanged.connect(self.file_ref_changed)
        self.cmb_fcompound.currentIndexChanged.connect(self.fcompound_changed)

        g = QGroupBox(T("cv_analysis"))
        f = make_form(g)
        self.sp_cycle = QSpinBox(minimum=1, maximum=100, value=st["cycle"])
        self.sp_cycle.setToolTip(T("cv_cycle_tip"))
        f.addRow(T("cv_cycle"), self.sp_cycle)
        row = QHBoxLayout()
        self.cb_baseline = QCheckBox(T("cv_baseline"))
        self.cb_baseline.setChecked(st["baseline"])
        self.cb_baseline.setToolTip(T("cv_baseline_tip"))
        self.sp_bl_gap = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=0.5, singleStep=0.01, value=st["bl_gap"],
                                        suffix=" V")
        self.sp_bl_gap.setToolTip(T("cv_bl_gap_tip"))
        self.cb_show_bl = QCheckBox(T("cv_show_bl"))
        self.cb_show_bl.setChecked(st["show_bl"])
        for w_ in (self.cb_baseline, self.sp_bl_gap, self.cb_show_bl):
            row.addWidget(w_)
        row.addStretch(1)
        f.addRow(row)
        for cb in (self.cb_baseline, self.cb_show_bl):
            cb.toggled.connect(self.changed)
        self.sp_bl_gap.valueChanged.connect(self.changed)
        self.tbl_couples = QTableWidget(0, 2)
        self.tbl_couples.setHorizontalHeaderLabels([T("cv_from"), T("cv_to")])
        self.tbl_couples.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_couples.verticalHeader().setVisible(True)
        self.tbl_couples.setMaximumHeight(110)
        self.tbl_couples.setToolTip(T("cv_couples_tip"))
        self.tbl_couples.itemChanged.connect(self.couples_edited)
        f.addRow(T("cv_couples"), self.tbl_couples)
        row = QHBoxLayout()
        for txt, fn, tip in (("+", self.add_couple, ""), ("−", self.remove_couple, ""),
                             (T("cv_suggest"), self.suggest, T("cv_suggest_tip"))):
            b = STYLE.list_button(txt)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        f.addRow("", row)
        self.cmb_ref = QComboBox()
        for key in ("none", "internal", "manual"):
            self.cmb_ref.addItem(T("cv_ref_" + key), key)
        self.cmb_ref.setCurrentIndex(max(0, self.cmb_ref.findData(st["ref_mode"])))
        f.addRow(T("cv_ref"), self.cmb_ref)
        self.cmb_ref_file = QComboBox()
        self.lbl_ref_file = QLabel(T("cv_ref_file"))
        f.addRow(self.lbl_ref_file, self.cmb_ref_file)
        row = QHBoxLayout()
        self.sp_ref_lo = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=st["ref_lo"])
        self.sp_ref_hi = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=st["ref_hi"])
        for w_ in (self.sp_ref_lo, QLabel("–"), self.sp_ref_hi):
            row.addWidget(w_)
        self.lbl_ref_win = QLabel(T("cv_ref_window"))
        f.addRow(self.lbl_ref_win, row)
        row = QHBoxLayout()
        self.cmb_compound = QComboBox()
        for key, (name, _) in REFERENCES.items():
            self.cmb_compound.addItem(name, key)
        self.cmb_compound.addItem(T("cv_ref_custom"), "custom")
        self.cmb_compound.setCurrentIndex(max(0, self.cmb_compound.findData(st["ref_compound"])))
        self.sp_ref_value = QDoubleSpinBox(decimals=3, minimum=-3, maximum=3, singleStep=0.01, value=st["ref_value"],
                                           suffix=" V")
        self.sp_ref_value.setToolTip(T("cv_ref_value_tip"))
        row.addWidget(self.cmb_compound, 1)
        row.addWidget(self.sp_ref_value)
        self.lbl_compound = QLabel(T("cv_ref_compound"))
        f.addRow(self.lbl_compound, row)
        self.sp_offset = QDoubleSpinBox(decimals=3, minimum=-5, maximum=5, singleStep=0.01, value=st["ref_offset"],
                                        suffix=" V")
        self.sp_offset.setToolTip(T("cv_offset_tip"))
        self.lbl_offset = QLabel(T("cv_offset"))
        f.addRow(self.lbl_offset, self.sp_offset)
        self.ed_electrode = QLineEdit(st["ref_electrode"])
        f.addRow(T("cv_electrode"), self.ed_electrode)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_display"))
        f = make_form(g)
        self.cmb_plot = QComboBox()
        for key in self.PLOTS:
            self.cmb_plot.addItem(T("cv_plot_" + key), key)
        self.cmb_plot.setCurrentIndex(max(0, self.cmb_plot.findData(st["plot"])))
        self.cmb_plot.setToolTip(T("cv_plot_tip"))
        f.addRow(T("cv_plot"), self.cmb_plot)
        row = QHBoxLayout()
        self.cb_stack = QCheckBox(T("cv_stack"))
        self.cb_stack.setChecked(st["stack"])
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0.2, maximum=5, singleStep=0.1, value=st["stack_gap"])
        self.sp_gap.setToolTip(T("cv_stack_gap_tip"))
        row.addWidget(self.cb_stack)
        row.addWidget(self.sp_gap)
        row.addStretch(1)
        f.addRow(row)
        self.cb_e12_each = QCheckBox(T("cv_e12_each"))
        self.cb_e12_each.setChecked(st["e12_each"])
        f.addRow(self.cb_e12_each)
        self.cmb_peaklab = QComboBox()
        for key in ("e12", "epa", "epc", "both"):
            self.cmb_peaklab.addItem(T("cv_peaklab_" + key), key)
        self.cmb_peaklab.setCurrentIndex(max(0, self.cmb_peaklab.findData(st["peak_labels"])))
        self.cmb_peaklab.setToolTip(T("cv_peaklab_tip"))
        f.addRow(T("cv_peaklab"), self.cmb_peaklab)
        self.cmb_yaxis = QComboBox()
        for key in ("auto", "numbers", "no_numbers", "off"):
            self.cmb_yaxis.addItem(T("yaxis_" + key), key)
        self.cmb_yaxis.setCurrentIndex(max(0, self.cmb_yaxis.findData(st["y_axis"])))
        f.addRow(T("ov_yaxis"), self.cmb_yaxis)
        self.sp_struct_w = self.size_spin(f, "struct_w", "image_struktur")
        for w_ in (self.cmb_peaklab, self.cmb_yaxis):
            w_.currentIndexChanged.connect(self.changed)
        self.cmb_plot.currentIndexChanged.connect(self.changed)
        self.sp_gap.valueChanged.connect(self.changed)
        for cb in (self.cb_stack, self.cb_e12_each):
            cb.toggled.connect(self.changed)
        self.cb_gradient = QCheckBox(T("cv_gradient"))
        self.cb_density = QCheckBox(T("cv_density"))
        self.cb_e12 = QCheckBox(T("cv_show_e12"))
        self.cb_arrow = QCheckBox(T("cv_arrow"))
        self.cb_invert = QCheckBox(T("cv_invert"))
        self.cb_invert.setToolTip(T("cv_invert_tip"))
        for cb, key in ((self.cb_gradient, "gradient"), (self.cb_density, "density"), (self.cb_e12, "show_e12"),
                        (self.cb_arrow, "arrow"), (self.cb_invert, "invert")):
            cb.setChecked(st[key])
            f.addRow(cb)
            cb.toggled.connect(self.changed)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_results"))
        v = QVBoxLayout(g)
        self.tbl_res = QTableWidget(0, 9)
        self.tbl_res.setHorizontalHeaderLabels(
            [T("ov_name"), "#", "E_pa [V]", "E_pc [V]", "E½ [V]", "ΔE_p [mV]", "i_pa [µA]", "i_pc [µA]",
             "i_r/i_f"])
        self.tbl_res.horizontalHeaderItem(8).setToolTip(T("cv_ratio_tip"))
        self.tbl_res.verticalHeader().setVisible(False)
        self.tbl_res.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_res.setMinimumHeight(140)
        v.addWidget(self.tbl_res)
        self.lbl_res = QLabel("")
        self.lbl_res.setWordWrap(True)
        self.lbl_res.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_res)
        row = QHBoxLayout()
        row.addWidget(self.methods_button())
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export

        self.sp_cycle.valueChanged.connect(self.changed)
        for w_ in (self.sp_ref_lo, self.sp_ref_hi, self.sp_ref_value, self.sp_offset):
            w_.valueChanged.connect(self.changed)
        self.cmb_ref.currentIndexChanged.connect(self.changed)
        self.cmb_ref_file.currentIndexChanged.connect(self.changed)
        self.cmb_compound.currentIndexChanged.connect(self.compound_changed)
        self.ed_electrode.editingFinished.connect(self.changed)
        self.fill_table()
        self.fill_couples()
        self._sync_ref_widgets()

    CAP_TITLES = {"cv": "Cyclic voltammograms", "dep": "Reversibility plot", "rs": "Randles–Ševčík plot",
                  "loglog": "Double-logarithmic plot of peak current vs. scan rate",
                  "ratio": "Peak current ratio vs. scan rate", "trumpet": "Trumpet plot"}
    CAP_REFS = {"ac2fc": "diacetylferrocene", "fc": "ferrocene"}

    def si_caption(self, name):
        """Wie in der SI: „Cyclic voltammograms of <b>6b</b> (1.7±0.1 mg mL-1) in THF (0.1 M n-Bu4NPF6) at rt;
        scan rate 200 mV s-1 (iR compensation = 2200 Ohm); potentials referenced against Fc0/+ using ferrocene as
        internal standard (arrows indicate scanning direction).“ (Achse vs. Fc0/+, Nutzerhinweis: der Standard ist nur das
        Hilfsmittel; bei Ac2Fc mit seinem E½.) Rate, iR-Kompensation (Gamry-Datei) und Referenz aus den sichtbaren Messungen;
        Konzentration, Lösungsmittel (leer = Gruppen) und Leitsalz aus den Feldern."""
        import html
        from elucida.si.lines import chem_html
        st = self.st
        vis = [e for e in st["files"] if e["visible"]]
        plot = st.get("plot", "cv")
        h = f"{self.CAP_TITLES.get(plot, 'Cyclic voltammograms')} of <b>{html.escape(name)}</b>"
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        groups = sorted({e.get("group", "").strip() for e in vis} - {""})
        solv = st.get("cap_solvent") or (groups[0] if len(groups) == 1 else "different solvents" if groups else "")
        if solv:
            h += " in " + chem_html(solv)
        if st.get("cap_el"):
            h += f" ({chem_html(st['cap_el'])})"
        h += " at " + chem_html(st.get("cap_temp") or "rt")
        if plot == "cv" and vis:
            metas = []
            for e in vis:
                try:
                    metas.append(self.data(e["file"])["meta"])
                except Exception:
                    metas.append({})
            rates = sorted({round(m.get("scanrate") or 0.0, 1) for m in metas} - {0.0})
            if len(rates) == 1:
                h += "; scan rate " + chem_html(f"{rates[0]:g} mV s-1")
            elif rates:
                h += "; different scan rates"
            ir = {m.get("pfcor") if m.get("ircomp_on") and m.get("posfeed") else None for m in metas}
            if len(ir) == 1 and None not in ir:
                h += f" (iR compensation = {next(iter(ir)):g} Ohm)"
            refs = {}                                  # interner Standard -> E½ vs. Fc0/+ (Vorgabe)
            for e in vis:
                ref = e.get("ref") or {}
                if self.file_offset(e)[1] != "Fc$^{0/+}$":           # nicht gefunden: Achse wie gemessen
                    continue
                if ref.get("mode") == "internal":
                    refs.setdefault(ref.get("compound"), set()).add(ref.get("value"))
                elif not ref.get("mode") and st["ref_mode"] == "internal":
                    refs.setdefault(st["ref_compound"], set()).add(st["ref_value"])
            if refs:                                   # Achse = vs. Fc0/+; der Standard ist nur das Hilfsmittel
                fc = "Fc<sup>0/+</sup>"
                parts = []
                for k in self.CAP_REFS:
                    if k not in refs:
                        continue
                    vals = sorted(v for v in refs[k] if v is not None)
                    if k == "fc":
                        parts.append("ferrocene")
                    else:
                        e12 = (f" (E<sub>1/2</sub> = {vals[0]:+.2f}".replace("-", "\u2212") + f" V vs. {fc})" if len(vals) == 1 else "")
                        parts.append(self.CAP_REFS[k] + e12)
                h += f"; potentials referenced against {fc} using " + " or ".join(parts) + " as internal standard"
            if st.get("arrow"):
                h += " (arrows indicate scanning direction)"
        return h + "."

    def _sync_ref_widgets(self):
        mode = self.st["ref_mode"]
        for w_ in (self.lbl_ref_file, self.cmb_ref_file, self.lbl_ref_win, self.sp_ref_lo, self.sp_ref_hi,
                   self.lbl_compound, self.cmb_compound, self.sp_ref_value):
            w_.setVisible(mode == "internal")
        for w_ in (self.lbl_offset, self.sp_offset):
            w_.setVisible(mode == "manual")

    def compound_changed(self, *_):
        key = self.cmb_compound.currentData()
        if key in REFERENCES and not self._loading:
            self.sp_ref_value.blockSignals(True)
            self.sp_ref_value.setValue(REFERENCES[key][1])
            self.sp_ref_value.blockSignals(False)
        self.changed()

    def collect(self):
        st = self.st
        st.update(cycle=self.sp_cycle.value(), ref_mode=self.cmb_ref.currentData(),
                  ref_uid=self.cmb_ref_file.currentData(), ref_lo=self.sp_ref_lo.value(),
                  ref_hi=self.sp_ref_hi.value(), ref_compound=self.cmb_compound.currentData(),
                  ref_value=self.sp_ref_value.value(), ref_offset=self.sp_offset.value(),
                  ref_electrode=self.ed_electrode.text().strip() or "Ag/AgNO₃",
                  gradient=self.cb_gradient.isChecked(), density=self.cb_density.isChecked(),
                  show_e12=self.cb_e12.isChecked(), arrow=self.cb_arrow.isChecked(),
                  invert=self.cb_invert.isChecked(), plot=self.cmb_plot.currentData(),
                  stack=self.cb_stack.isChecked(), stack_gap=self.sp_gap.value(),
                  e12_each=self.cb_e12_each.isChecked(), y_axis=self.cmb_yaxis.currentData(),
                  peak_labels=self.cmb_peaklab.currentData(), baseline=self.cb_baseline.isChecked(),
                  bl_gap=self.sp_bl_gap.value(), show_bl=self.cb_show_bl.isChecked())
        self._sync_ref_widgets()

    # -- Dateien -------------------------------------------------------------------
    def data(self, path):
        return self.cache(("cv", path), lambda: read_gamry(path))

    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("cv_add"), self.main.settings.value("last_dir", ""),
                                             "Gamry (*.DTA *.dta);;" + T("flt_all"))
        for p in ps:
            try:
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                d = self.data(p)
            except Exception as e:
                self.main.error(str(e))
                continue
            rate = d["meta"]["scanrate"]
            self.st["files"].append({"file": p, "uid": uuid.uuid4().hex[:8], "visible": True, "color": "#000000",
                                     "label": f"{round(rate, 1):g} mV/s" if rate else Path(p).stem})
        if ps and not self.st["couples"]:
            self.suggest()
        self.fill_table()
        self.timer.start()

    def move(self, d):
        r = self.table.currentRow()
        fs = self.st["files"]
        if 0 <= r < len(fs) and 0 <= r + d < len(fs):
            fs[r], fs[r + d] = fs[r + d], fs[r]
            self.fill_table()
            self.table.selectRow(r + d)
            self.timer.start()

    def remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["files"]):
            del self.st["files"][r]
            self.fill_table()
            self.timer.start()

    def fill_table(self):
        self._loading = True
        fs = self.st["files"]
        self.table.setRowCount(len(fs))
        for i, e in enumerate(fs):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(e["color"], lambda c, e=e: self._set_color(e, c)))
            try:
                rate = self.data(e["file"])["meta"]["scanrate"]
            except Exception:
                rate = None
            it = QTableWidgetItem(f"{round(rate, 1):g}" if rate else "–")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, it)
            self.table.setItem(i, 4, QTableWidgetItem(e.get("group", "")))
        self.table.resizeColumnToContents(0)
        self.update_color_buttons()
        cur = self.st.get("ref_uid")
        self.cmb_ref_file.blockSignals(True)
        self.cmb_ref_file.clear()
        for e in fs:
            self.cmb_ref_file.addItem(e["label"], e["uid"])
        self.cmb_ref_file.setCurrentIndex(max(0, self.cmb_ref_file.findData(cur)))
        self.cmb_ref_file.blockSignals(False)
        self._loading = False
        self.show_file_ref()

    def update_color_buttons(self):
        """Mit Farbverlauf nach Scanrate gelten die eigenen Farben nicht: Felder zeigen die Farbe im Bild und
        sind gesperrt."""
        grad = getattr(self, "grad_colors", {})
        for i, e in enumerate(self.st["files"]):
            b = self.table.cellWidget(i, 2)
            if b is None:
                continue
            col = grad.get(e["uid"], e["color"])
            b.setEnabled(not grad)
            b.setToolTip(T("cv_color_gradient_tip") if grad else "")
            b.setStyleSheet(f"background-color: {col}; border: 1px solid #777;")

    def _set_color(self, e, c):
        e["color"] = c
        self.timer.start()

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["files"][item.row()]
        if item.column() == 0:
            e["visible"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text()
            self.fill_table()
        elif item.column() == 4:
            e["group"] = item.text().strip()
        self.timer.start()

    # -- Referenz je Messung ---------------------------------------------------------
    def current_file(self):
        r = self.table.currentRow()
        return self.st["files"][r] if 0 <= r < len(self.st["files"]) else None

    def show_file_ref(self):
        if not hasattr(self, "det"):
            return
        e = self.current_file()
        self.det.setEnabled(e is not None)
        ref = (e or {}).get("ref") or {}
        self._loading = True
        self.cmb_fref.setCurrentIndex(max(0, self.cmb_fref.findData(ref.get("mode", "global"))))
        self.cmb_fref_file.clear()
        for x in self.st["files"]:
            self.cmb_fref_file.addItem(x["label"], x["uid"])
        self.cmb_fref_file.setCurrentIndex(max(0, self.cmb_fref_file.findData(ref.get("uid", (e or {}).get("uid")))))
        self.sp_fref_lo.setValue(ref.get("lo", self.st["ref_lo"]))
        self.sp_fref_hi.setValue(ref.get("hi", self.st["ref_hi"]))
        self.cmb_fcompound.setCurrentIndex(max(0, self.cmb_fcompound.findData(ref.get("compound", "ac2fc"))))
        self.sp_fref_value.setValue(ref.get("value", REFERENCES["ac2fc"][1]))
        self.sp_foffset.setValue(ref.get("offset", 0.0))
        self.lbl_fstruct.setText(Path(e["structure"]).name if e and e.get("structure") else "–")
        self.cb_fstruct_color.setChecked(bool(e and e.get("struct_color", False)))
        self._loading = False
        mode = ref.get("mode", "global")
        for w_ in (self.lbl_fref_file, self.cmb_fref_file, self.lbl_fref_win, self.sp_fref_lo, self.sp_fref_hi,
                   self.lbl_fcompound, self.cmb_fcompound, self.sp_fref_value):
            w_.setVisible(mode == "internal")
        for w_ in (self.lbl_foffset, self.sp_foffset):
            w_.setVisible(mode == "manual")
        self.lbl_fref_info.setText(self.file_offset(e)[2] if e is not None and mode != "global" else "")

    def choose_file_structure(self):
        e = self.current_file()
        if e is None or not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.main.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.main.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_file_structure(self.main.import_file(p, PRJ.STRUCTURES))

    def set_file_structure(self, p):
        e = self.current_file()
        if e is None:
            return
        e["structure"] = p
        self.show_file_ref()
        self.timer.start()

    def fcompound_changed(self, *_):
        key = self.cmb_fcompound.currentData()
        if key in REFERENCES and not self._loading:
            self.sp_fref_value.blockSignals(True)
            self.sp_fref_value.setValue(REFERENCES[key][1])
            self.sp_fref_value.blockSignals(False)
        self.file_ref_changed()

    def file_ref_changed(self, *_):
        e = self.current_file()
        if self._loading or e is None:
            return
        mode = self.cmb_fref.currentData()
        e["struct_color"] = self.cb_fstruct_color.isChecked()
        e["ref"] = None if mode == "global" else {
            "mode": mode, "uid": self.cmb_fref_file.currentData(), "lo": self.sp_fref_lo.value(),
            "hi": self.sp_fref_hi.value(), "compound": self.cmb_fcompound.currentData(),
            "value": self.sp_fref_value.value(), "offset": self.sp_foffset.value()}
        self.show_file_ref()
        self.timer.start()

    # -- Redoxpaare (gespeichert in gemessenen Potentialen, angezeigt in der Achsenskala) -----------------
    def fill_couples(self):
        self._loading = True
        cs = self.st["couples"]
        self.tbl_couples.setRowCount(len(cs))
        for i, (lo, hi) in enumerate(cs):
            for j, v in enumerate((lo, hi)):
                self.tbl_couples.setItem(i, j, QTableWidgetItem(f"{v - self._offset:.3f}"))
        self._loading = False

    def couples_edited(self, item):
        if self._loading:
            return
        try:
            v = float(item.text().replace(",", ".").replace("−", "-")) + self._offset
        except ValueError:
            return self.fill_couples()
        self.st["couples"][item.row()][item.column()] = v
        self.timer.start()

    def add_couple(self):
        x0, x1 = (self.st["x_min"], self.st["x_max"]) if not self.st["x_auto"] else (-0.25, 0.25)
        mid = (x0 + x1) / 2 + self._offset
        self.st["couples"].append([round(mid - 0.25, 3), round(mid + 0.25, 3)])
        self.fill_couples()
        self.timer.start()

    def remove_couple(self):
        r = self.tbl_couples.currentRow()
        if 0 <= r < len(self.st["couples"]):
            del self.st["couples"][r]
        elif self.st["couples"]:
            self.st["couples"].pop()
        self.fill_couples()
        self.timer.start()

    def suggest(self):
        """Redoxpaare aus der ersten sichtbaren Messung vorschlagen (ersetzt die Liste)."""
        vis = [e for e in self.st["files"] if e["visible"]]
        if not vis:
            return
        c = self.cycle_of(vis[0])
        # Fenster gespeichert in gemessenen Potentialen der globalen Referenz (figure_spec verschiebt je Messung)
        shift = self.file_offset(vis[0])[0] - self.reference_offset()[0]
        self.st["couples"] = [[lo - shift, hi - shift] for lo, hi in suggest_couples(c["E"], c["I"])]
        self.fill_couples()
        self.timer.start()

    # -- Auswertung und Abbildung -------------------------------------------------------
    def cycle_of(self, e):
        cyc = self.data(e["file"])["cycles"]
        return cyc[min(self.st["cycle"], len(cyc)) - 1]

    def reference_offset(self):
        """-> (Offset in V: E_Achse = E_gemessen − Offset, Achsenbeschriftung der Referenz, Hinweis)."""
        st = self.st
        if st["ref_mode"] == "manual":
            return st["ref_offset"], "Fc$^{0/+}$", ""
        if st["ref_mode"] == "internal":
            e = next((x for x in st["files"] if x["uid"] == st.get("ref_uid")), None)
            if e is not None:
                c = self.cycle_of(e)
                r = analyze_couple(c["E"], c["I"], st["ref_lo"], st["ref_hi"])
                if r is not None:
                    name = REFERENCES.get(st["ref_compound"], (T("cv_ref_custom"), 0))[0]
                    note = T("cv_ref_note", name=name, e12=_fmt_e(r["e12"]), el=st["ref_electrode"],
                             dep=f"{r['dep'] * 1000:.0f}", val=_fmt_e(st["ref_value"], 2))
                    if r["edge"]:
                        note += "  " + T("cv_edge")
                    return r["e12"] - st["ref_value"], "Fc$^{0/+}$", note
            return 0.0, st["ref_electrode"], T("cv_ref_missing")
        return 0.0, st["ref_electrode"], ""

    def file_offset(self, e):
        """Offset dieser Messung (eigene Referenz oder global) -> (Offset, Achsenbeschriftung, Hinweis)."""
        ref = e.get("ref") or {}
        if ref.get("mode") == "manual":
            return ref.get("offset", 0.0), "Fc$^{0/+}$", ""
        if ref.get("mode") == "internal":
            src = next((x for x in self.st["files"] if x["uid"] == ref.get("uid")), None)
            if src is not None:
                c = self.cycle_of(src)
                r = analyze_couple(c["E"], c["I"], ref.get("lo", 0.3), ref.get("hi", 0.8))
                if r is not None:
                    name = REFERENCES.get(ref.get("compound"), (T("cv_ref_custom"), 0))[0]
                    note = T("cv_ref_note", name=name, e12=_fmt_e(r["e12"]), el=self.st["ref_electrode"],
                             dep=f"{r['dep'] * 1000:.0f}", val=_fmt_e(ref.get("value", 0.0), 2))
                    if r["edge"]:
                        note += "  " + T("cv_edge")
                    return r["e12"] - ref.get("value", 0.0), "Fc$^{0/+}$", note
            return 0.0, self.st["ref_electrode"], T("cv_ref_missing")
        return self.reference_offset()

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["files"] if e["visible"]]
        if not vis:
            self.results = []
            self.show_results()
            self.grad_colors = {}
            self.update_color_buttons()
            return None
        cfg = self.base_cfg()
        off_g, ref_label, note = self.reference_offset()
        if abs(off_g - self._offset) > 1e-12:
            self._offset = off_g
            self.fill_couples()
        sign = -1.0 if st["invert"] else 1.0
        rates = [self.data(e["file"])["meta"]["scanrate"] or 0.0 for e in vis]
        order = np.argsort(np.argsort(rates))
        curves, self.results, notes, labels_ref = [], [], [note] if note else [], set()
        grad_colors = {}
        # Stromdichte nur, wenn alle Messungen eine Fläche haben (sonst Strom und Dichte unter einer Achse)
        no_area = [e["label"] for e in vis if not self.data(e["file"])["meta"]["area"]]
        density = self._density = st["density"] and not no_area
        if st["density"] and no_area:
            notes.append(T("cv_area_missing", files=", ".join(no_area)))
        short = [e["label"] for e in vis if len(self.data(e["file"])["cycles"]) < st["cycle"]]
        if short:
            notes.append(T("cv_cycle_missing", files=", ".join(short), n=st["cycle"]))
        for k, e in enumerate(vis):
            d = self.data(e["file"])
            c = self.cycle_of(e)
            off, lab_ref, n_ = self.file_offset(e)
            labels_ref.add(lab_ref)
            if n_ and e.get("ref"):
                notes.append(f"{e['label']}: {n_}")
            E = c["E"] - off
            if density:
                fac, unit = sign * 1e3 / d["meta"]["area"], "mA"              # mA cm⁻²
            else:
                fac, unit = sign * 1e6, "µA"
            y = fac * c["I"]
            color = (RATE_CMAP(order[k] / max(1, len(vis) - 1)) if st["gradient"] and len(vis) > 1 else e["color"])
            color = color if isinstance(color, str) else "#%02x%02x%02x" % tuple(int(255 * v) for v in color[:3])
            grad_colors[e["uid"]] = color
            curves.append({"x": E, "y": y, "val": y, "color": color, "label": e["label"], "ls": "-", "lw": 1.3,
                           "uid": e["uid"], "_scale": fac,
                           "_off_e": off})
            # Fenster gespeichert in gemessenen Potentialen der globalen Referenz -> auf diese Messung umrechnen
            shift = off - off_g
            for n, (lo, hi) in enumerate(st["couples"], 1):
                r = analyze_couple(c["E"], c["I"], lo + shift, hi + shift, st["baseline"], st["bl_gap"])
                if r is not None:
                    self.results.append(dict(r, label=e["label"], group=e.get("group", ""), n=n, uid=e["uid"],
                                             rate=d["meta"]["scanrate"], epa=r["epa"] - off, epc=r["epc"] - off,
                                             e12=r["e12"] - off, ircomp=d["meta"].get("ircomp", ""), offset=off,
                                             ref=lab_ref))
        self.grad_colors = grad_colors if st["gradient"] and len(vis) > 1 else {}
        self.update_color_buttons()
        if len(labels_ref) > 1:
            notes.append(T("cv_ref_mixed"))
        ref_label = "Fc$^{0/+}$" if labels_ref == {"Fc$^{0/+}$"} else ref_label
        self.note = "\n".join(notes)
        if st["plot"] != "cv":
            out = self.rate_plot(cfg, ref_label)
            self.show_results()
            return out
        labels = []
        stacked = st["stack"] and len(curves) > 1
        if stacked:                                      # oberster Eintrag der Liste = oberste Kurve
            span = max(float(np.ptp(c_["y"])) for c_ in curves) or 1.0
            for k, c_ in enumerate(curves):
                c_["off"] = (len(curves) - 1 - k) * st["stack_gap"] * span
                c_["y"] = c_["y"] + c_["off"]
        y_axis = st.get("y_axis", "auto")
        cfg["y_axis"] = ("no_numbers" if stacked else "numbers") if y_axis == "auto" else y_axis
        allx = np.concatenate([c_["x"] for c_ in curves])
        cfg["xlim"] = [float(allx.min()), float(allx.max())] if st["x_auto"] else [st["x_min"], st["x_max"]]
        ally = np.concatenate([c_["y"] for c_ in curves])
        span = float(ally.max() - ally.min()) or 1.0
        top = 0.22 if (st["show_e12"] and (st["e12_each"] or st["stack"])) else 0.12
        cfg["ylim"] = [float(ally.min()) - 0.08 * span, st["ymax"] if st["ymax"] > 0 else float(ally.max()) + top * span]
        cfg["xlabel"] = f"E [V vs. {axis_ref(ref_label)}]"
        cfg["ylabel"] = "j [mA cm$^{-2}$]" if (st["density"] and unit == "mA") else "I [µA]"
        if st["show_e12"]:
            multi = len(st["couples"]) > 1
            mode = st.get("peak_labels", "e12")
            dens = st["density"] and unit == "mA"
            if mode != "e12":
                # Peakpotentiale als Zahl an den einzelnen Peaks (z. B. Probe und Ac₂Fc in einer Messung)
                for c_ in curves:
                    for r in self.results:
                        if r["uid"] != c_["uid"] or r["edge"]:
                            continue
                        for kind, ex, ip, side in (("epa", r["epa"], r["ipa_raw"], "above"),
                                                         ("epc", r["epc"], r["ipc_raw"], "below")):
                            if mode in (kind, "both"):
                                labels.append({"key": f"label_{kind}_{c_['uid']}_{r['n']}", "lam": ex, "side": side,
                                               "y": None if dens else float(ip * 1e6 * sign) + c_.get("off", 0.0),
                                               "text": f"{ex:.2f}".replace("-", "−")})
            elif st["e12_each"] or stacked:
                # je Kurve und Redoxpaar, am anodischen Peak dieser Kurve (wie in Vergleichsabbildungen üblich)
                for c_ in curves:
                    for r in self.results:
                        if r["uid"] != c_["uid"] or r["edge"]:
                            continue
                        sup = f"$^{{{r['n']}}}$" if multi else ""
                        side = "right" if (multi and r["n"] == len(st["couples"])) else "left"
                        labels.append({"key": f"label_e12_{c_['uid']}_{r['n']}", "lam": r["epa"], "side": side,
                                       "y": float(r["ipa_raw"] * 1e6 * sign) + c_.get("off", 0.0)
                                       if not (st["density"] and unit == "mA") else None,
                                       "text": f"E{sup}$_{{1/2}}$ = " + _fmt_e(r["e12"], 2)})
            else:
                # Mittel je Gruppe: verschiedene Lösungsmittel nie zu einem E½ mitteln
                groups = sorted({r.get("group", "") for r in self.results})
                for n in range(1, len(st["couples"]) + 1):
                    for grp in groups:
                        rr = [r for r in self.results if r["n"] == n and not r["edge"] and r.get("group", "") == grp]
                        vals = [r["e12"] for r in rr]
                        if vals and len({r["ref"] for r in rr}) == 1:      # nie über Referenzskalen mitteln
                            e12 = float(np.mean(vals))
                            tag = f" ({grp})" if len(groups) > 1 and grp else ""
                            key = f"label_e12_{n}" + (f"_{grp}" if len(groups) > 1 else "")
                            labels.append({"key": key, "lam": e12,
                                           "text": "E$_{1/2}$" + tag + " =\n" + _fmt_e(e12, 2) + " V"})
        if st["arrow"]:
            c0 = curves[0]
            xr = cfg["xlim"][1] - cfg["xlim"][0]
            direction = 1.0 if np.gradient(c0["x"])[:5].mean() >= 0 else -1.0
            x0, y0 = float(c0["x"][0]), float(c0["y"][0])
            cfg["arrows"] = [(x0, y0, x0 + direction * 0.08 * xr, y0)]
        imgs = []
        for e, c_ in zip(vis, curves):                  # Struktur je Messung, optional in Kurvenfarbe
            p = e.get("structure")
            if p and Path(p).exists():
                try:
                    asset = self.structure_asset(p, c_["color"] if e.get("struct_color") else None)
                except Exception as ex:
                    self.main.log_signal.emit(f"  {Path(p).name}: {ex}")
                    continue
                imgs.append({"file": p, "id": "struktur_" + e["uid"], "width": st.get("struct_w", 18.0) / 100,
                             "prefer": "top", "_asset": asset})
        cfg["images"] = imgs
        if st["baseline"] and st["show_bl"]:
            curves += self.baseline_curves(curves)
        self.show_results()
        return cfg, curves, labels, []

    def baseline_curves(self, curves):
        """Basislinien zur Kontrolle: Hin- und Rückbasislinie (gestrichelt) und Lote vom Peak (gepunktet)."""
        out = []
        for c_ in curves:
            sc, off_e, yoff = c_["_scale"], c_["_off_e"], c_.get("off", 0.0)
            for r in self.results:
                bl = r.get("bl")
                if r["uid"] != c_["uid"] or bl is None or r["edge"]:
                    continue
                s, a, b, step = bl["s"], bl["a"], bl["b"], bl["step"]
                epf, epr = bl["epf"], bl["epr"]               # gemessene Potentiale; Achse = gemessen − off_e
                ends = [bl["e0"], epf + s * 0.03, epr - s * 0.03]
                x = np.linspace(min(ends), max(ends), 50)
                fwd = a * x + b
                kw = dict(color=c_["color"], lw=0.8, label=None, aux=True)
                out.append(dict(kw, x=x - off_e, y=fwd * sc + yoff, ls="--"))
                if step > 0:
                    out.append(dict(kw, x=x - off_e, y=(fwd - s * step) * sc + yoff, ls="--"))
                i_f, i_r = (r["ipa_raw"], r["ipc_raw"]) if r["anodic_first"] else (r["ipc_raw"], r["ipa_raw"])
                for ep, i_pk, rev in ((epf, i_f, False), (epr, i_r, True)):
                    i_bl = a * ep + b - (s * step if rev else 0.0)
                    out.append(dict(kw, x=np.array([ep, ep]) - off_e, y=np.array([i_bl, i_pk]) * sc + yoff, ls=":"))
        return out

    def rate_series(self, currents=False):
        """Ergebnisse nach (Gruppe, Redoxpaar) für Auftragungen gegen die Scanrate (ohne Randpeaks).
        currents=True: auch ohne Messungen, deren Basislinie fehlt (sonst korrigierte und unkorrigierte
        Ströme in einer Regression)."""
        ser = {}
        for r in self.results:
            if r["rate"] and not r["edge"] and not (currents and r.get("bl_fail")):
                ser.setdefault((r["group"], r["n"]), []).append(r)
        return {k: sorted(v, key=lambda r: r["rate"]) for k, v in ser.items()}

    def rate_fits(self):
        """Regressionen je (Gruppe, Redoxpaar) ab 3 Scanraten -> {(Gruppe, n): dict(rs_a, rs_c, ll_a, ll_c, rates)}."""
        out = {}
        for key, rr in self.rate_series(currents=True).items():
            v = [r["rate"] for r in rr]
            if len(set(v)) < 3:
                continue
            ia, ic = [r["ipa"] * 1e6 for r in rr], [r["ipc"] * 1e6 for r in rr]
            out[key] = dict(rs_a=rate_fit(np.sqrt(np.array(v) / 1000.0), ia),
                            rs_c=rate_fit(np.sqrt(np.array(v) / 1000.0), ic),
                            ll_a=loglog_fit(v, ia), ll_c=loglog_fit(v, ic), rates=sorted(set(v)))
        return out

    def rate_plot(self, cfg, ref_label):
        """ΔE_p gegen v, Randles-Ševčík (i_p gegen √v) oder Trumpet-Plot (E_p gegen log v)."""
        st = self.st
        ser = self.rate_series(currents=st["plot"] in ("rs", "loglog", "ratio"))
        multi_n = len(st["couples"]) > 1
        curves = []
        for j, ((grp, n), rr) in enumerate(sorted(ser.items(), key=lambda kv: (kv[0][1], kv[0][0]))):
            name = " ".join(x for x in (grp, f"#{n}" if multi_n else "") if x) or (f"#{n}" if multi_n else None)
            col = TABS.PALETTE[j % len(TABS.PALETTE)]
            mk = self.MARKERS[j % len(self.MARKERS)]
            v = np.array([r["rate"] for r in rr], float)
            base = dict(color=col, ls="None", marker=mk, ms=6, lw=1.0)
            if st["plot"] == "dep":
                curves.append(dict(base, x=v, y=np.array([r["dep"] * 1000 for r in rr]), label=name))
            elif st["plot"] == "rs":
                sq = np.sqrt(v / 1000.0)
                for key, tag, m_ in (("ipa", "a", "^"), ("ipc", "c", "v")):
                    ip = np.array([r[key] * 1e6 for r in rr])
                    lab = f"i$_{{p{tag}}}$" + (f" {name}" if name else "")
                    curves.append(dict(base, x=sq, y=ip, label=lab, marker=m_))
                    fit = randles_sevcik(v, ip)
                    if fit:
                        xf = np.array([0.0, float(sq.max()) * 1.05])
                        curves.append(dict(color=col, ls="--", lw=1.0, x=xf, y=fit[0] * xf + fit[1], label=None))
            elif st["plot"] == "loglog":
                lv = np.log10(v / 1000.0)
                for key, tag, m_ in (("ipa", "a", "^"), ("ipc", "c", "v")):
                    ip = np.abs(np.array([r[key] * 1e6 for r in rr]))
                    ok = ip > 0
                    lab = f"i$_{{p{tag}}}$" + (f" {name}" if name else "")
                    curves.append(dict(base, x=lv[ok], y=np.log10(ip[ok]), label=lab, marker=m_))
                    fit = loglog_fit(v, ip)
                    if fit:
                        xf = np.array([lv.min() - 0.1, lv.max() + 0.1])
                        curves.append(dict(color=col, ls="--", lw=1.0, x=xf, y=fit["slope"] * xf + fit["intercept"],
                                           label=None))
            elif st["plot"] == "ratio":
                ok = np.array([bool(np.isfinite(r["ratio"])) for r in rr])
                if ok.any():
                    curves.append(dict(base, x=v[ok], y=np.array([r["ratio"] for r in rr])[ok], label=name))
            else:                                        # Trumpet: E_pa und E_pc gegen log v
                lv = np.log10(v / 1000.0)
                curves.append(dict(base, x=lv, y=np.array([r["epa"] for r in rr]), marker="^",
                                   label=f"E$_{{pa}}$" + (f" {name}" if name else "")))
                curves.append(dict(base, x=lv, y=np.array([r["epc"] for r in rr]), marker="v",
                                   label=f"E$_{{pc}}$" + (f" {name}" if name else "")))
        pts = [c_ for c_ in curves if c_.get("marker")]
        if not pts or all(len(c_["x"]) < 2 for c_ in pts):
            self.note = "\n".join(x for x in (self.note, T("cv_rates_needed")) if x)
            return None
        xs = np.concatenate([c_["x"] for c_ in curves])
        ys = np.concatenate([c_["y"] for c_ in pts])
        # Mindestspanne, sonst zoomt die Achse bei fast gleichen Werten auf Rauschen (z. B. 63,82–63,84 mV)
        min_span = {"dep": 40.0, "rs": 1.0, "loglog": 0.3, "ratio": 0.3, "trumpet": 0.05}[st["plot"]]
        ypad = 0.1 * max(float(np.ptp(ys)), min_span) + max(0.0, min_span - float(np.ptp(ys))) / 2
        if st["plot"] == "dep":
            cfg["xlim"] = [0.0, float(xs.max()) * 1.08]
            cfg["ylim"] = [max(0.0, float(ys.min()) - ypad), float(ys.max()) + ypad]
            cfg["xlabel"], cfg["ylabel"] = "scan rate [mV/s]", "peak to peak separation ΔE$_p$ [mV]"
        elif st["plot"] == "rs":
            cfg["xlim"] = [0.0, float(xs.max()) * 1.08]
            cfg["ylim"] = [min(0.0, float(ys.min()) - ypad), max(0.0, float(ys.max()) + ypad)]
            cfg["xlabel"], cfg["ylabel"] = "v$^{1/2}$ [V$^{1/2}$ s$^{-1/2}$]", "i$_p$ [µA]"
        elif st["plot"] == "loglog":
            xpad = 0.1 * (float(np.ptp(xs)) or 1.0)
            cfg["xlim"] = [float(xs.min()) - xpad, float(xs.max()) + xpad]
            cfg["ylim"] = [float(ys.min()) - ypad, float(ys.max()) + ypad]
            cfg["xlabel"], cfg["ylabel"] = "log(v / V s$^{-1}$)", "log(|i$_p$| / µA)"
        elif st["plot"] == "ratio":
            x1 = float(xs.max()) * 1.08
            cfg["xlim"] = [0.0, x1]
            lo_, hi_ = min(float(ys.min()), 1.0), max(float(ys.max()), 1.0)
            cfg["ylim"] = [max(0.0, lo_ - ypad), hi_ + ypad]
            cfg["xlabel"], cfg["ylabel"] = "scan rate [mV/s]", "i$_{p,r}$/i$_{p,f}$ (Nicholson)"
            curves.append(dict(color="#888888", ls=":", lw=0.8, x=np.array([0.0, x1]), y=np.array([1.0, 1.0]),
                               label=None, aux=True))
        else:
            xpad = 0.1 * (float(np.ptp(xs)) or 1.0)
            cfg["xlim"] = [float(xs.min()) - xpad, float(xs.max()) + xpad]
            cfg["ylim"] = [float(ys.min()) - ypad, float(ys.max()) + ypad]
            cfg["xlabel"], cfg["ylabel"] = "log(v / V s$^{-1}$)", f"E$_p$ [V vs. {axis_ref(ref_label)}]"
        cfg["legend"] = any(c_.get("label") for c_ in curves)
        return cfg, curves, [], []

    def show_results(self):
        if not hasattr(self, "tbl_res"):
            return
        self.show_caption()
        res = self.results
        self.tbl_res.setRowCount(len(res))
        for i, r in enumerate(res):
            name = f"{r['label']} ({r['group']})" if r.get("group") else r["label"]
            vals = [name, str(r["n"]), _fmt_e(r["epa"]), _fmt_e(r["epc"]), _fmt_e(r["e12"]),
                    f"{r['dep'] * 1000:.0f}", f"{r['ipa'] * 1e6:.1f}", f"{r['ipc'] * 1e6:.1f}",
                    f"{r['ratio']:.2f}" if np.isfinite(r["ratio"]) else "–"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if r["edge"]:
                    it.setForeground(Qt.red)
                    it.setToolTip(T("cv_edge"))
                elif r.get("bl_fail") and j >= 6:
                    it.setForeground(Qt.darkYellow)
                    it.setToolTip(T("cv_bl_fail"))
                elif j == 8 and not r.get("ratio_ok", True):
                    it.setToolTip(T("cv_ratio_invalid"))
                self.tbl_res.setItem(i, j, it)
        self.tbl_res.resizeColumnsToContents()
        lines = [self.note] if getattr(self, "note", "") else []
        if any(r.get("bl_fail") for r in res):
            lines.append(T("cv_bl_fail"))
        for (grp, n), f in sorted(self.rate_fits().items(), key=lambda kv: (kv[0][1], kv[0][0])):
            name = f"{n}" + (f" ({grp})" if grp else "")
            for tag, rs, ll in (("a", f["rs_a"], f["ll_a"]), ("c", f["rs_c"], f["ll_c"])):
                if rs and ll:
                    lines.append(T("cv_fit_line", n=name, p=tag, m=fmt_ci(rs["slope"], rs["ci"]),
                                   b=fmt_ci(rs["intercept"], rs["ci_b"]), r2=f"{rs['r2']:.4f}",
                                   ll=fmt_ci(ll["slope"], ll["ci"]), k=rs["n"]))
        self.lbl_res.setText("\n".join(lines))

    def _ref_sentence(self):
        """Referenzierung der sichtbaren Messungen -> (Satz englisch, Referenz für die Ergebnisse)."""
        st = self.st
        kinds = set()
        for e in (x for x in st["files"] if x["visible"]):
            ref = e.get("ref") or {}
            if self.file_offset(e)[1] != "Fc$^{0/+}$":            # interne Referenz nicht gefunden: wie gemessen
                kinds.add(("none", None, 0.0))
            elif ref.get("mode") in ("internal", "manual"):
                kinds.add((ref["mode"], ref.get("compound"), round(ref.get("value", 0.0), 3)))
            else:
                kinds.add((st["ref_mode"], st["ref_compound"], round(st["ref_value"], 3)))
        out = []
        internal = sorted(k for k in kinds if k[0] == "internal")
        if internal:
            stds = []
            for _, comp, val in internal:
                name, short = REF_NAMES_EN.get(comp, ("an internal standard", ""))
                stds.append(name if comp == "fc" else
                            f"{name} ({short + ', ' if short else ''}E1/2 = {_fmt_e(val, 2)} V vs. Fc0/+)")
            out.append("Potentials are given vs. the ferrocene/ferrocenium couple (Fc0/+) and were referenced to "
                       "the half-wave potential of " + " or ".join(stds) + " as internal standard.")
        if any(k[0] == "manual" for k in kinds):
            out.append("Potentials were converted to the Fc0/+ scale using the half-wave potential of Fc0/+ "
                       f"measured vs. {st['ref_electrode']}.")
        if any(k[0] == "none" for k in kinds):
            out.append(f"Potentials of measurements without internal standard are given vs. {st['ref_electrode']}."
                       if len({k[0] == "none" for k in kinds}) > 1 else
                       f"Potentials are given vs. {st['ref_electrode']}.")
        return " ".join(out), ("Fc0/+" if kinds and all(k[0] != "none" for k in kinds) else st["ref_electrode"])

    def methods_text(self):
        """SI-Text zur Auswertung (englisch, Stil des Abschnitts „Cyclic Voltammetry“ der Gruppen-SI): Gerät,
        Elektroden und Leitsalz stehen im Aufbau-Absatz der SI und fehlen hier bewusst. Danach ein Absatz mit
        den Ergebnissen je Redoxpaar (zum Übernehmen in Text oder Bildunterschrift)."""
        st = self.st
        rates = sorted({round(r["rate"], 1) for r in self.results if r["rate"]})
        ref_txt, ref_lab = self._ref_sentence()
        m = [ref_txt,                                  # nur die Mathematik, kein Programmname (Nutzerwunsch)
             "Peak potentials (Epa, Epc) were obtained by a parabolic fit to the current extremum (±3 data points) "
             f"of cycle {st['cycle']}; E1/2 = (Epa + Epc)/2 and ΔEp = Epa − Epc."]
        vis = [e for e in st["files"] if e["visible"]]
        short = [e["label"] for e in vis if len(self.data(e["file"])["cycles"]) < st["cycle"]]
        if short:
            m.append(f"For {', '.join(short)} (fewer cycles), the last cycle was used.")
        if st["baseline"]:
            m.append("Peak currents were measured against a linear baseline fitted to the current of the forward "
                     f"scan before the onset of the wave (ending at least {st['bl_gap'] * 1000:.0f} mV before the "
                     f"peak potential and before the current exceeded {BL_ONSET * 100:.0f}% of the peak height) and "
                     "extrapolated beneath the peak. For the reverse peak, this baseline was shifted "
                     "by the change of the capacitive current at the switching potential (current step of 2C·v).")
            n_fail = sum(1 for r in self.results if r.get("bl_fail"))
            if n_fail:
                m.append(f"For {n_fail} of {len(self.results)} peak pairs the scan before the wave was too short for "
                         "a baseline; their peak currents were measured from zero current and excluded from the "
                         "regressions and from the ratios given below.")
        else:
            m.append("Peak currents were measured from zero current.")
        m.append("The ratio of reverse to forward peak current was calculated according to Nicholson, "
                 "ip,r/ip,f = (ip,r)0/ip,f + 0.485 (isp)0/ip,f + 0.086, where (isp)0 is the current at the switching "
                 "potential, to account for the decaying current of the forward scan.[R. S. Nicholson, Anal. Chem. "
                 "1966, 38, 1406.]")
        if any(not r.get("ratio_ok", True) for r in self.results):
            m.append("No ratio was determined from scans in which a further process occurred between the forward "
                     "peak and the switching potential.")
        if rates:
            m.append("Scan rates: " + ", ".join(f"{v:g}" for v in rates) + " mV s-1.")
        fits = self.rate_fits()
        if fits:
            m.append("The scan-rate dependence was analysed by linear least-squares regression of ip vs. v1/2 "
                     "(Randles–Ševčík) and of log|ip| vs. log v (slope 0.5: diffusion-controlled, 1: surface-"
                     "confined species); uncertainties are given as 95% confidence intervals (t-distribution, "
                     "n − 2 degrees of freedom).")
        res = []
        for (grp, n), rr in sorted(self.rate_series().items(), key=lambda kv: (kv[0][1], kv[0][0])):
            refs = {r["ref"] for r in rr}
            e12 = np.mean([r["e12"] for r in rr]) if len(refs) == 1 else None
            lab = str(next(iter(refs))).replace("Fc$^{0/+}$", "Fc0/+") if len(refs) == 1 else ref_lab
            dep = [r["dep"] * 1000 for r in rr]
            rat = [r["ratio"] for r in rr if np.isfinite(r["ratio"]) and not r.get("bl_fail")]
            rng = lambda v, f: f"{min(v):{f}}" + (f"–{max(v):{f}}" if f"{min(v):{f}}" != f"{max(v):{f}}" else "")  # noqa: E731
            e_txt = (f"E1/2 = {_fmt_e(e12, 2)} V vs. {lab}" if e12 is not None
                     else "E1/2 not averaged (different reference scales)")
            txt = (f"Couple {n}" + (f" ({grp})" if grp else "") + f": {e_txt}"
                   + f" (ΔEp = {rng(dep, '.0f')} mV" + (f", ip,r/ip,f = {rng(rat, '.2f')}" if rat else "")
                   + (f"; {rng([round(r['rate'], 1) for r in rr], 'g')} mV s-1" if len(rr) > 1 else "") + ")")
            f = fits.get((grp, n))
            if f and f["ll_a"] and f["ll_c"]:
                txt += (f"; log–log slopes {fmt_ci(f['ll_a']['slope'], f['ll_a']['ci'])} (ipa) and "
                        f"{fmt_ci(f['ll_c']['slope'], f['ll_c']['ci'])} (ipc)")
            res.append(txt + ".")
        out = " ".join(x for x in m if x)
        return out + ("\n\n" + " ".join(res) if res else "")

    def hover_text(self, x, val, name):
        plot = self.st.get("plot", "cv")
        if plot != "cv":
            xs = {"dep": f"v = {x:.0f} mV/s", "rs": f"√v = {x:.3f} V½ s⁻½", "trumpet": f"log v = {x:.2f}",
                  "loglog": f"log v = {x:.2f}", "ratio": f"v = {x:.0f} mV/s"}[plot]
            ys = {"dep": "ΔE_p = {:.0f} mV", "rs": "i_p = {:.2f} µA", "trumpet": "E_p = {:.3f} V",
                  "loglog": "log i_p = {:.3f}", "ratio": "i_r/i_f = {:.2f}"}[plot]
            return f"{xs}    {ys.format(val)}    {name}" if val is not None else xs
        if val is None:
            return f"E = {x:.3f} V"
        dens = getattr(self, "_density", self.st["density"])
        unit = "mA cm⁻²" if dens else "µA"
        return f"E = {x:.3f} V    {'j' if dens else 'I'} = {val:.2f} {unit}    {name}"

    def export_to(self, base: Path):
        """Abbildung wie die anderen Tabs, dazu die Ergebnisse als CSV (UTF-8, Semikolon)."""
        files = super().export_to(base)
        p = Path(base).with_name(Path(base).name + "_results.csv")
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["file", "group", "couple", "scan_rate_mV_s", "E_pa_V", "E_pc_V", "E_half_V", "dE_p_mV",
                        "i_pa_uA", "i_pc_uA", "ratio_Nicholson", "peak_at_window_edge", "reference_offset_V",
                        "ir_compensation_in_file", "reference", "baseline", "i_pa_raw_uA", "i_pc_raw_uA",
                        "charging_step_uA"])
            for r in self.results:
                w.writerow([r["label"], r.get("group", ""), r["n"], r["rate"], f"{r['epa']:.4f}", f"{r['epc']:.4f}",
                            f"{r['e12']:.4f}", f"{r['dep'] * 1000:.1f}", f"{r['ipa'] * 1e6:.3f}",
                            f"{r['ipc'] * 1e6:.3f}", f"{r['ratio']:.3f}", int(r["edge"]), f"{r.get('offset', 0):.4f}",
                            r.get("ircomp", ""), getattr(self, "note", "").replace("\n", " | "),
                            "failed" if r.get("bl_fail") else ("linear" if r.get("bl") else "none"),
                            f"{r['ipa_raw'] * 1e6:.3f}", f"{r['ipc_raw'] * 1e6:.3f}",
                            f"{r['bl']['step'] * 1e6:.3f}" if r.get("bl") else ""])
        return files + [p]
