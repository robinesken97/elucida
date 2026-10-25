"""elucida/tabs/ir_ea.py - IR-Peakliste und HRMS-Zeile für die SI, Tab „IR + MS“.

IR:  Bruker OPUS (Binärdatei *.0, *.1 …: Spektrum + Parameterblock) oder OPUS-PDF-Ausdruck (Peakwerte als Text).
     Peaksuche in Rohdaten: Minima der Transmission (bzw. Maxima der Absorbanz) mit Mindest-Prominenz relativ zur
     stärksten Bande; Intensität optional w/m/s nach relativer Tiefe, br bei Halbwertsbreite > BROAD_CM.
MS:  Auftragsformular der Massenabteilung (Word, *.docx): Formel und Ionisierung aus dem Text, gemessene m/z aus den
     Beschriftungen der eingebetteten Spektren (EMF, EMR_EXTTEXTOUTW). calc. = monoisotopische Masse des Ions mit
     Elektronenmasse (z. B. [M+H]⁺ = M + m(H) − mₑ = M + 1.007276).
"""
from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

import numpy as np
from elucida.formats.opus import (read_opus, is_opus, read_ir_pdf)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.ms_report import (read_ms_docx, _emf_texts, cdx_structure)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.bruker_ms import (read_bruker_d, is_bruker_d, BAF_LINE_MAGIC, BAF_TRANSFORMATOR, _baf_mz)  # noqa: E402,F401  (Leser in elucida/formats)

# ---------------------------------------------------------------------------- Massen
ELECTRON = 0.000548579909
MONO = {  # häufigstes Isotop, IUPAC/AME
    "H": 1.00782503207, "D": 2.0141017778, "B": 11.0093054, "C": 12.0, "N": 14.0030740048, "O": 15.99491461956,
    "F": 18.99840322, "Na": 22.9897692809, "Mg": 23.985041700, "Al": 26.98153863, "Si": 27.9769265325,
    "P": 30.97376163, "S": 31.97207100, "Cl": 34.96885268, "K": 38.96370668, "Ca": 39.96259098,
    "Fe": 55.9349375, "Co": 58.9331950, "Ni": 57.9353429, "Cu": 62.9295975, "Zn": 63.9291422, "Se": 79.9165213,
    "Br": 78.9183371, "Ru": 101.9043493, "Rh": 102.905504, "Pd": 105.903486, "Ag": 106.905097, "Sn": 119.9021947,
    "I": 126.904473, "Pt": 194.9647911, "Au": 196.9665687, "Li": 7.01600455, "Cs": 132.905451933, "Ge": 73.9211778,
    "Te": 129.9062244, "Bi": 208.9803987, "Ti": 47.9479463, "Mn": 54.9380451, "Cr": 51.9405075,
}
# Addukt: (Anzeige, Änderung der Formel, Ladung)
ADDUCTS = {
    "M+H": ("[M+H]", {"H": 1}, 1), "M+Na": ("[M+Na]", {"Na": 1}, 1), "M+K": ("[M+K]", {"K": 1}, 1),
    "M+NH4": ("[M+NH$_4$]", {"N": 1, "H": 4}, 1), "M": ("[M]", {}, 1), "M-H": ("[M−H]", {"H": -1}, -1),
    "M+Cl": ("[M+Cl]", {"Cl": 1}, -1), "M-": ("[M]", {}, -1),
}


def parse_formula(text: str) -> dict:
    """'C31H21N3' / 'C18H20N2+' -> {'C': 31, …}; Ladung am Ende wird ignoriert (kommt vom Addukt)."""
    text = re.sub(r"[+\-−]+\d*$", "", str(text).replace(" ", ""))
    out = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", text):
        if el not in MONO:
            raise ValueError(f"Element {el} nicht bekannt")
        out[el] = out.get(el, 0) + (int(n) if n else 1)
    if not out:
        raise ValueError("keine Summenformel")
    return out


def formula_str(counts: dict) -> str:
    """Hill-Reihenfolge: C, H, dann alphabetisch."""
    keys = [k for k in ("C", "H", "D") if counts.get(k)] + sorted(k for k in counts if k not in ("C", "H", "D") and counts[k])
    return "".join(f"{k}{counts[k] if counts[k] != 1 else ''}" for k in keys)


def ion(formula: str, adduct: str = "M+H"):
    """-> (Ionenformel ohne Ladung, Ladung ±1, m/z calc, Addukt-Anzeige)."""
    counts = parse_formula(formula)
    label, delta, z = ADDUCTS[adduct]
    for el, n in delta.items():
        counts[el] = counts.get(el, 0) + n
    if any(v < 0 for v in counts.values()):
        raise ValueError("Addukt passt nicht zur Formel")
    m = sum(MONO[el] * n for el, n in counts.items()) - z * ELECTRON
    return formula_str(counts), z, m / abs(z), label


def ppm(found, calc):
    return (found - calc) / calc * 1e6


# ---------------------------------------------------------------------------- IR: OPUS


# ---------------------------------------------------------------------------- IR: PDF
AXIS_TICKS = {0, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 100}


# ---------------------------------------------------------------------------- IR: Peaksuche und Text
BROAD_CM = 120.0                                    # Halbwertsbreite, ab der eine Bande „br“ heißt (O–H, N–H)


def pick_peaks(wn, y, kind="T", lo=None, hi=None, prominence=0.05, min_dist=4.0):  # noqa: C901
    """Banden im Bereich [lo, hi] (cm⁻¹): Tiefe d = 100 − T (bzw. A), lokale Maxima von d mit Prominenz
    ≥ prominence · max(d). -> [dict(wn, depth, rel, width)] absteigend nach Wellenzahl."""
    wn, y = np.asarray(wn, float), np.asarray(y, float)
    d = (100.0 - y) if kind == "T" else y.copy()
    lo = float(np.nanmin(wn)) if lo is None else lo
    hi = float(np.nanmax(wn)) if hi is None else hi
    sel = (wn >= min(lo, hi)) & (wn <= max(lo, hi)) & np.isfinite(d)
    if sel.sum() < 5:
        return []
    o = np.argsort(wn[sel])
    x, dd = wn[sel][o], d[sel][o]
    base = float(np.percentile(dd, 5))
    dd = dd - base
    dmax = float(dd.max()) or 1.0
    step = float(np.median(np.diff(x))) or 1.0
    win = max(1, int(round(min_dist / step)))
    out = []
    for i in range(1, len(x) - 1):
        a, b = max(0, i - win), min(len(x), i + win + 1)
        if dd[i] < dd[a:b].max() or dd[i] <= 0:
            continue
        # Prominenz: Tiefe über dem höheren der beiden seitlichen Minima bis zur nächsten tieferen Bande
        left = dd[:i][::-1]
        right = dd[i + 1:]
        def side_min(arr):
            m = dd[i]
            for v in arr:
                if v > dd[i]:
                    break
                m = min(m, v)
            return m
        prom = dd[i] - max(side_min(left), side_min(right))
        if prom < prominence * dmax:
            continue
        half = dd[i] / 2                             # Halbwertsbreite für „br“
        l_, r_ = i, i
        while l_ > 0 and dd[l_] > half:
            l_ -= 1
        while r_ < len(x) - 1 and dd[r_] > half:
            r_ += 1
        xi = float(x[i])                             # Lage zwischen den Messpunkten per Parabel (wie OPUS)
        den = dd[i - 1] - 2 * dd[i] + dd[i + 1]
        if den < 0:
            xi += 0.5 * (dd[i - 1] - dd[i + 1]) / den * (x[i + 1] - x[i - 1]) / 2
        out.append({"wn": xi, "depth": float(dd[i]), "rel": float(dd[i] / dmax),
                    "width": float(x[r_] - x[l_])})
    # gleiche Wellenzahl nach Rundung nur einmal
    seen, uniq = set(), []
    for p in sorted(out, key=lambda p: -p["wn"]):
        k = round(p["wn"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def to_absorbance(t_pct):
    """A = −log10(T/100); T ≤ 0 (Rauschen bei Totalabsorption) -> NaN statt ±∞ (Lücke in der Kurve)."""
    t = np.asarray(t_pct, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        a = -np.log10(t / 100.0)
    a[~(t > 0)] = np.nan
    return a


def to_transmission(a):
    """T [%] = 100 · 10^(−A)."""
    return 100.0 * np.power(10.0, -np.asarray(a, float))


def display_y(sp, mode):
    """Spektrum in der gewählten Darstellung (T = Transmission in %, A = Absorbanz). Die Peaksuche läuft immer auf
    den Originaldaten (pick_peaks mit sp["kind"]), die Darstellung ändert nur das Bild."""
    y = np.asarray(sp["y"], float)
    if mode == sp["kind"]:
        return y
    return to_absorbance(y) if mode == "A" else to_transmission(y)


# Eingabe „y-Achse max“ je Darstellung: (Minimum, Maximum, Nachkommastellen, Schritt); 0 = automatisch
YMAX_SPIN = {"T": (0.0, 100.0, 0, 5.0), "A": (0.0, 10.0, 2, 0.1)}


def y_limits(y, mode, ymax=0.0):
    """y-Grenzen [unten, oben] für das IR-Bild und ob die Eingabe „y-Achse max“ verworfen wurde.
    %T: Obergrenze höchstens 100. Eine Obergrenze, die nicht über dem kleinsten Wert liegt, würde die ganze Kurve
    abschneiden (früher: Spinbox ab „auto“ = 0 mit Schritt 0.1 -> ylim [37, 0.1], Spektrum weg) -> automatisch."""
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    ymin, ymaxv = (float(y.min()), float(y.max())) if len(y) else (0.0, 100.0 if mode == "T" else 1.0)
    span = ymaxv - ymin or 1.0
    lo = ymin - 0.08 * span
    hi = ymaxv + 0.05 * span
    rejected = False
    if ymax and ymax > 0:
        top = min(float(ymax), 100.0) if mode == "T" else float(ymax)
        if top > ymin + 0.02 * span:
            hi = top
        else:
            rejected = True
    if hi <= lo:
        hi = lo + 1.0
    return [lo, hi], rejected


def intensity_tag(p, broad=BROAD_CM):
    """w/m/s nach relativer Tiefe (≥ 0.6 s, ≥ 0.3 m), „br“ bei breiten Banden."""
    t = "s" if p["rel"] >= 0.6 else ("m" if p["rel"] >= 0.3 else "w")
    return ("br " + t) if p.get("width", 0) > broad else t


def ir_line(peaks, with_intensity=False):
    """-> (Klartext, HTML) wie in der SI: IR [cm⁻¹]: ṽ = 2961, 2866, … (ganze Zahlen, absteigend)."""
    vals = sorted(peaks, key=lambda p: -p["wn"])
    items = [f"{round(p['wn']):d}" + (f" ({intensity_tag(p)})" if with_intensity and "rel" in p else "") for p in vals]
    body = ", ".join(items)
    plain = f"IR [cm-1]: ṽ = {body}"
    html = f"<b>IR</b> [cm<sup>-1</sup>]: ṽ = {body}"                    # wie in der SI: „-1“
    return plain, html


# ---------------------------------------------------------------------------- MS-Bericht


# ---------------------------------------------------------------------------- MS: Bruker-Rohdaten (.d, BAF)


def lc_found(spectra, calc, tol_ppm=10.0, rt=None, frac=0.5):
    """m/z des gesuchten Ions über den LC-Peak: je Spektrum die Linie am nächsten an calc (innerhalb tol_ppm),
    Peak = zusammenhängende Spektren um das Maximum mit Intensität ≥ frac·Maximum (oder fester Zeitbereich rt).
    -> dict(mz intensitätsgewichtet, n, std_mda, lo, hi, rt_lo, rt_hi, xic) oder None."""
    tol = calc * tol_ppm * 1e-6
    xic = []
    for t, mz, inten in spectra:
        j = int(np.searchsorted(mz, calc))
        cand = [k for k in (j - 1, j) if 0 <= k < len(mz) and abs(mz[k] - calc) <= tol]
        k = max(cand, key=lambda k: inten[k]) if cand else None
        xic.append((t, float(mz[k]) if k is not None else np.nan, float(inten[k]) if k is not None else 0.0))
    xic = np.array(xic)
    if not (xic[:, 2] > 0).any():
        return None
    if rt is not None:
        use = (xic[:, 0] >= min(rt)) & (xic[:, 0] <= max(rt)) & (xic[:, 2] > 0)
    else:
        top = int(np.argmax(xic[:, 2]))
        thr = frac * xic[top, 2]
        lo = hi = top
        while lo > 0 and xic[lo - 1, 2] >= thr:
            lo -= 1
        while hi < len(xic) - 1 and xic[hi + 1, 2] >= thr:
            hi += 1
        use = np.zeros(len(xic), bool)
        use[lo:hi + 1] = True
        use &= xic[:, 2] > 0
    if not use.any():
        return None
    m, w = xic[use, 1], xic[use, 2]
    mean = float(np.average(m, weights=w))
    return {"mz": mean, "n": int(use.sum()), "std_mda": float(np.sqrt(np.average((m - mean) ** 2, weights=w)) * 1000),
            "lo": float(m.min()), "hi": float(m.max()), "rt_lo": float(xic[use, 0].min()),
            "rt_hi": float(xic[use, 0].max()), "xic": xic}


def nearest(mz_list, calc, max_ppm=20.0):
    """Gemessenes m/z, das am nächsten an calc liegt (innerhalb max_ppm), sonst None."""
    best = min(mz_list, key=lambda v: abs(v - calc), default=None)
    return best if best is not None and abs(ppm(best, calc)) <= max_ppm else None


def ms_line(formula, adduct, found, ionisation="ESI"):
    """-> (Klartext, HTML): HR-MS-ESI(+) calc. C18H21N2+ [M+H]+ 265.1699; found 265.1703."""
    f_ion, z, calc, label = ion(formula, adduct)
    sign = "+" if z > 0 else "−"
    lab_plain = label.replace("$_4$", "4")
    lab_html = label.replace("$_4$", "<sub>4</sub>")
    f_html = re.sub(r"(\d+)", r"<sub>\1</sub>", f_ion)
    tail = f"; found {found:.4f}." if found is not None else "; found –."
    plain = f"HR-MS-{ionisation}({sign}) calc. {f_ion}{sign} {lab_plain}{sign} {calc:.4f}{tail}"
    html = (f"<b>HR-MS-{ionisation}({sign})</b> calc. {f_html}<sup>{sign}</sup> {lab_html}<sup>{sign}</sup> "
            f"{calc:.4f}{tail}")
    return plain, html, calc


# ----------------------------------------------------------------------------
# Tab „IR + MS“
# ----------------------------------------------------------------------------
from PySide6.QtCore import QMimeData, Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout,  # noqa: E402
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)
import os  # noqa: E402

from elucida.si import lines as SI  # noqa: E402
from elucida.tabs import base as TABS  # noqa: E402
from elucida.app.i18n import T  # noqa: E402
from elucida.app import project as PRJ  # noqa: E402
from elucida.app.style import HINT_CSS, WARN_CSS, make_form  # noqa: E402

IR_COLOR = "#7a1a12"


def spread_centers(targets, widths, lo=0.0, hi=1.0):
    """Mittelpunkte nebeneinanderliegender Labels (Achsenbruchteile) so nah wie möglich an targets, ohne dass sich
    Labels der Breite widths überlappen: überlappende Labels bilden einen Block, der um den Mittelwert seiner Ziele
    zentriert wird; Blöcke bleiben in [lo, hi]."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    blocks = []                                          # [indices, start]

    def start_of(idx):
        off, acc = [], 0.0
        for i in idx:
            off.append(acc + widths[i] / 2)
            acc += widths[i]
        s = float(np.mean([targets[i] - o for i, o in zip(idx, off)]))
        return min(max(s, lo), max(lo, hi - acc))

    for i in order:
        blocks.append([[i], start_of([i])])
        while len(blocks) > 1:
            (ia, sa), (ib, sb) = blocks[-2], blocks[-1]
            if sa + sum(widths[k] for k in ia) <= sb:
                break
            blocks[-2:] = [[ia + ib, start_of(ia + ib)]]
    out = [0.0] * len(targets)
    for idx, s in blocks:
        for i in idx:
            out[i] = s + widths[i] / 2
            s += widths[i]
    return out


class IRFigure(TABS.X.SimpleFigure):
    """IR-Abbildung: Wellenzahl-Labels senkrecht direkt unter dem Peakminimum (Transmission) bzw. über dem Maximum
    (Absorbanz), seitlich auseinandergeschoben statt überlappend; die y-Achse wächst, bis alle Labels hineinpassen.
    Gespeicherte (gezogene) Positionen haben Vorrang."""

    def __init__(self, *a, side="below", fixed_top=False, **kw):
        self._ir_side, self._ir_fixed_top = side, fixed_top
        super().__init__(*a, **kw)

    def _make_labels(self, labels):
        super()._make_labels(labels)
        for ann in self.ann_items.values():
            ann.set_rotation(90)

    def _ir_positions(self):
        """-> {key: (x, y)} lower-left in Achsenbruchteilen; erweitert dabei ggf. die y-Achse."""
        if not self.ann_items:
            return {}
        ax, below = self.ax, self._ir_side == "below"
        pts = [(np.asarray(c["x"], float), np.asarray(c["y"], float)) for c in self.spectra]
        X_ = np.concatenate([p[0] for p in pts])
        Y_ = np.concatenate([p[1] for p in pts])
        ok = np.isfinite(X_) & np.isfinite(Y_)
        X_, Y_ = X_[ok], Y_[ok]
        pad = 0.01 if self.cfg.get("size_cm") else 0.06
        pos = {}
        for _ in range(4):
            rend = self._renderer()
            ab = ax.get_window_extent(rend)
            gy, gx = 2.5 * self.fig.dpi / 72 / ab.height, 1.0 * self.fig.dpi / 72 / ab.width
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            fx, fy = (X_ - x0) / (x1 - x0), (Y_ - y0) / (y1 - y0)
            keys, tgt, ays, wid, hgt = [], [], [], [], []
            for key, ann in self.ann_items.items():
                _, _, bw, bh = self._measure_af(ann.get_window_extent(rend))
                keys.append(key)
                tgt.append((ann.xy[0] - x0) / (x1 - x0))
                ays.append((ann.xy[1] - y0) / (y1 - y0))
                wid.append(bw + gx)
                hgt.append(bh)
            cen = spread_centers(tgt, wid)
            pos, need = {}, []
            for key, c, ay, w, h in zip(keys, cen, ays, wid, hgt):
                m = (fx >= c - w / 2) & (fx <= c + w / 2)
                if below:                                # Oberkante unter der Kurve über die ganze Labelbreite
                    top = min(float(fy[m].min()) if m.any() else ay, ay) - gy
                    yb = top - h
                    need.append((top, h))
                else:
                    yb = max(float(fy[m].max()) if m.any() else ay, ay) + gy
                    need.append((yb, h))
                pos[key] = (c - (w - gx) / 2, yb)
            span = y1 - y0
            if below:                                    # unten Platz schaffen: (top − Y0)/(y1 − Y0) ≥ h + Rand
                new0 = min(y1 - (y1 - (y0 + t * span)) / (1 - (h + 0.01)) for t, h in need)
                if new0 >= y0 - 1e-9 * span:
                    break
                ax.set_ylim(new0, y1)
            else:
                if self._ir_fixed_top:
                    break
                new1 = max(y0 + (y0 + b * span - y0) / (1 - (h + 0.01)) for b, h in need)
                if new1 <= y1 + 1e-9 * span:
                    break
                ax.set_ylim(y0, new1)
            self._fit_axes(pad)
        return {k: (min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)) for k, (x, y) in pos.items()}

    def _place(self):
        auto = self._ir_positions()
        orig = self.layout
        self.layout = {**{k: list(v) for k, v in auto.items()}, **orig}
        try:
            super()._place()
        finally:
            self.layout = orig


def copy_rich(plain, html):
    """Zeile mit Formatierung (fett, hoch-/tiefgestellt) in die Zwischenablage – bleibt beim Einfügen in Word."""
    md = QMimeData()
    md.setText(SI.nbsp(plain))                  # geschützte Leerzeichen wie im Word-Export
    md.setHtml(SI.nbsp(html))
    QApplication.clipboard().setMimeData(md)


class IRMSTab(TABS.FigureTab):
    """Tab „IR + EA“ (der MS-Teil steht seit 1.21 im Tab HRMS, tabs/hrms.py)."""
    STATE_KEY = "irms"
    GUIDE, GUIDE_ACTION = "irms", ("guide_add", "choose_ir")
    SI_CAPTION = "IR spectrum of {name}."
    X_RANGE = (100.0, 8000.0, 0, 50.0)
    XRANGE_TEXT = "ir_xrange"
    RESET_KEEP = ("ir_file", "ir_pdf", "ir_off", "ea_solvate", "ea_found")   # Dateien, entfernte Peaks, EA
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=400.0, x_max=4000.0, ymax=0.0, ir_file=None, ir_pdf=None,
                         ir_lo=None, ir_hi=None, prominence=5.0, with_int=False, ir_off=[], ir_labels=False,
                         ea_solvate="", ea_found={}, ir_mode=None)    # ir_mode: None = wie die Datei, "T" | "A"

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("ir_group"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_ir = QLabel("–")
        self.lbl_ir.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_ir)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(self.clear_ir)
        row.addWidget(self.lbl_ir, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("ir_files"), row)
        row = QHBoxLayout()
        self.sp_lo = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.sp_hi = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.cb_full = QCheckBox(T("ir_full"))
        for w_ in (self.cb_full, self.sp_lo, QLabel("–"), self.sp_hi):
            row.addWidget(w_)
        f.addRow(T("ir_range"), row)
        self.sp_prom = QDoubleSpinBox(decimals=1, minimum=0.5, maximum=50, singleStep=0.5, suffix=" %",
                                      value=st["prominence"])
        self.sp_prom.setToolTip(T("ir_prom_tip"))
        f.addRow(T("ir_prom"), self.sp_prom)
        self.cb_int = QCheckBox(T("ir_with_int"))
        self.cb_int.setToolTip(T("ir_with_int_tip"))
        self.cb_int.setChecked(st["with_int"])
        f.addRow(self.cb_int)
        self.cb_irlab = QCheckBox(T("ir_labels"))
        self.cb_irlab.setChecked(st["ir_labels"])
        f.addRow(self.cb_irlab)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem(T("ir_mode_T"), "T")
        self.cmb_mode.addItem(T("ir_mode_A"), "A")
        self.cmb_mode.setToolTip(T("ir_mode_tip"))
        f.addRow(T("ir_mode"), self.cmb_mode)
        self.tbl_ir = QTableWidget(0, 3)
        self.tbl_ir.setHorizontalHeaderLabels(["", "ṽ [cm⁻¹]", T("ir_intensity")])
        self.tbl_ir.verticalHeader().setVisible(False)
        self.tbl_ir.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_ir.setMinimumHeight(160)
        self.tbl_ir.itemChanged.connect(self.ir_toggled)
        f.addRow(self.tbl_ir)
        self.txt_ir = QTextBrowser()
        self.txt_ir.setMaximumHeight(90)
        f.addRow(self.txt_ir)
        b = QPushButton(T("ir_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ir_line))
        f.addRow(b)
        self.lv.addWidget(g)

        g = QGroupBox(T("ea_group"))
        f = make_form(g)
        self.lbl_ea_formula = QLabel("–")
        self.lbl_ea_formula.setWordWrap(True)
        f.addRow(T("compound_formula"), self.lbl_ea_formula)
        self.ed_solv = QLineEdit(st.get("ea_solvate", ""))
        self.ed_solv.setPlaceholderText(T("ea_solvate_ph"))
        self.ed_solv.setToolTip(T("ea_solvate_tip"))
        f.addRow(T("ea_solvate"), self.ed_solv)
        grid = QGridLayout()
        grid.addWidget(QLabel(""), 0, 0)
        grid.addWidget(QLabel(T("ea_calc")), 1, 0)
        grid.addWidget(QLabel(T("ea_found")), 2, 0)
        self.ea_calc_lbl, self.ea_found_ed = {}, {}
        for j, el in enumerate(SI.EA_ELEMENTS, 1):
            grid.addWidget(QLabel(f"{el} [%]"), 0, j)
            lc = QLabel("–")
            grid.addWidget(lc, 1, j)
            ed = QLineEdit(str((st.get("ea_found") or {}).get(el, "")))
            ed.setMaximumWidth(80)
            grid.addWidget(ed, 2, j)
            ed.editingFinished.connect(self.changed)
            self.ea_calc_lbl[el], self.ea_found_ed[el] = lc, ed
        f.addRow(grid)
        self.lbl_ea_info = QLabel("")
        self.lbl_ea_info.setWordWrap(True)
        f.addRow(self.lbl_ea_info)
        self.txt_ea = QTextBrowser()
        self.txt_ea.setMaximumHeight(60)
        f.addRow(self.txt_ea)
        b = QPushButton(T("ea_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ea_line))
        f.addRow(b)
        self.lv.addWidget(g)
        self.ed_solv.editingFinished.connect(self.changed)

        self._ir_line = self._ea_line = ("", "")
        self.cb_full.toggled.connect(self.changed)
        for w_ in (self.sp_lo, self.sp_hi, self.sp_prom):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_int, self.cb_irlab):
            w_.toggled.connect(self.changed)
        self.cmb_mode.currentIndexChanged.connect(self.mode_changed)
        self.sync_widgets()

    def common_box(self):
        g = super().common_box()
        self.sync_ymax_spin()
        return g

    def mode(self):
        """Darstellung im Bild: gewählt, sonst wie die Datei (Transmission, falls keine Datei)."""
        m = self.st.get("ir_mode")
        if m in ("T", "A"):
            return m
        sp = self.spectrum()
        return sp["kind"] if sp else "T"

    def mode_changed(self, *_):
        if self._loading:
            return
        m = self.cmb_mode.currentData()
        if m != self.mode():
            self.st["ir_mode"] = m
            self.st["ymax"] = 0.0                      # Obergrenze gehört zur alten Einheit -> automatisch
            self.st["layout"][self.size_key()] = {}    # Labels wechseln die Seite
        self.sync_ymax_spin()
        self.timer.start()

    def sync_ymax_spin(self):
        """„y-Achse max“ passend zur Darstellung: %T 0–100 in ganzen Prozent, Absorbanz 0–10; 0 = automatisch."""
        sp_ = getattr(self, "sp_ymax", None)
        if sp_ is None:
            return
        lo, hi, dec, step = YMAX_SPIN[self.mode()]
        v = float(self.st.get("ymax") or 0.0)
        if not lo <= v <= hi:
            v = 0.0 if v < lo else hi
            self.st["ymax"] = v
        sp_.blockSignals(True)
        sp_.setDecimals(dec)
        sp_.setRange(lo, hi)
        sp_.setSingleStep(step)
        sp_.setSuffix(" %" if self.mode() == "T" else "")
        sp_.setValue(v)
        sp_.blockSignals(False)

    # -- Dateien --------------------------------------------------------------------
    def choose_ir(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ir_files"), self.main.settings.value("last_dir", ""),
                                             f"{T('flt_ir')};;{T('flt_all')}")
        for p in ps:
            self.load_ir(p)

    def load_ir(self, p):
        """PDF -> Peakliste aus OPUS, OPUS-Datei -> Spektrum (eigene Peaksuche); beides darf gleichzeitig da sein."""
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        try:
            if Path(p).suffix.lower() == ".pdf":
                if not read_ir_pdf(p):
                    raise ValueError(T("ir_pdf_empty"))
                self.st["ir_pdf"] = p
            else:
                read_opus(p)
                self.st["ir_file"] = p
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ir_lo=None, ir_hi=None, ir_off=[])
        self.sync_widgets()
        self.timer.start()

    def clear_ir(self):
        self.st.update(ir_file=None, ir_pdf=None, ir_lo=None, ir_hi=None, ir_off=[])
        self.sync_widgets()
        self.timer.start()

    def compound_changed(self):
        self.sync_widgets()
        self.timer.start()

    # -- Daten ------------------------------------------------------------------------
    def spectrum(self):
        p = self.st.get("ir_file")
        if not p or not Path(p).exists():
            return None
        return self.cache(("opus", p), lambda: read_opus(p))

    def ir_range(self):
        sp = self.spectrum()
        full = (float(sp["wn"].min()), float(sp["wn"].max())) if sp else (400.0, 4000.0)
        lo, hi = self.st.get("ir_lo"), self.st.get("ir_hi")
        return (full[0] if lo is None else lo, full[1] if hi is None else hi), full

    def peaks(self):
        """Peakliste im Bereich: aus dem OPUS-PDF (exakt die OPUS-Werte) oder eigene Suche im Spektrum.
        Intensitäten kommen immer aus dem Spektrum, falls vorhanden."""
        st = self.st
        (lo, hi), _ = self.ir_range()
        sp = self.spectrum()
        found = pick_peaks(sp["wn"], sp["y"], sp["kind"], lo, hi, st["prominence"] / 100) if sp else []
        if st.get("ir_pdf") and Path(st["ir_pdf"]).exists():
            vals = self.cache(("irpdf", st["ir_pdf"]), lambda: read_ir_pdf(st["ir_pdf"]))
            out = []
            for v in vals:
                if min(lo, hi) <= v <= max(lo, hi):
                    near = min(found, key=lambda q: abs(q["wn"] - v), default=None)
                    p = dict(near) if near is not None and abs(near["wn"] - v) < 3 else {}
                    p["wn"] = v
                    out.append(p)
            return out
        return found

    def formula(self):
        """Formel wie im HRMS-Tab: Verbindung des Projekts, sonst die Struktur im MS-Bericht, sonst dessen Formelfeld."""
        hr = getattr(self.main, "hrms_tab", None)
        if hr is not None:
            return hr.formula()
        c = self.main.compound
        return (c["formula"], "project") if c.get("formula") else (None, None)

    # -- Oberfläche -----------------------------------------------------------------
    def sync_widgets(self):
        st = self.st
        self._loading = True
        names = [Path(p).name for p in (st.get("ir_file"), st.get("ir_pdf")) if p]
        self.lbl_ir.setText(", ".join(names) or "–")
        (lo, hi), full = self.ir_range()
        auto = st.get("ir_lo") is None and st.get("ir_hi") is None
        self.cb_full.setChecked(auto)
        self.sp_lo.setValue(lo)
        self.sp_hi.setValue(hi)
        self.sp_lo.setEnabled(not auto)
        self.sp_hi.setEnabled(not auto)
        self.sp_prom.setEnabled(self.spectrum() is not None and not st.get("ir_pdf"))
        self.cb_int.setChecked(bool(st.get("with_int")))
        self.cb_irlab.setChecked(bool(st.get("ir_labels")))
        self.sp_prom.setValue(st.get("prominence", 5.0))
        self.cmb_mode.setCurrentIndex(self.cmb_mode.findData(self.mode()))
        self.sync_ymax_spin()
        self._loading = False

    def collect(self):
        st = self.st
        if self.cb_full.isChecked():
            st.update(ir_lo=None, ir_hi=None)
        else:
            st.update(ir_lo=self.sp_lo.value(), ir_hi=self.sp_hi.value())
        st.update(ea_solvate=self.ed_solv.text().strip(),
                  ea_found={el: ed.text().strip().replace(",", ".") for el, ed in self.ea_found_ed.items()
                            if ed.text().strip()})
        st.update(prominence=self.sp_prom.value(), with_int=self.cb_int.isChecked(), ir_labels=self.cb_irlab.isChecked())
        self.sync_widgets()

    def ir_toggled(self, item):
        if self._loading or item.column() != 0:
            return
        k = item.data(Qt.UserRole)
        off = set(self.st.get("ir_off") or [])
        off.discard(k) if item.checkState() == Qt.Checked else off.add(k)
        self.st["ir_off"] = sorted(off)
        self.timer.start()

    def fill_ir_table(self, peaks):
        self._loading = True
        off = set(self.st.get("ir_off") or [])
        self.tbl_ir.setRowCount(len(peaks))
        for i, p in enumerate(peaks):
            k = round(p["wn"])
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked if k in off else Qt.Checked)
            it.setData(Qt.UserRole, k)
            self.tbl_ir.setItem(i, 0, it)
            for j, v in ((1, f"{p['wn']:.1f}"), (2, intensity_tag(p) if "rel" in p else "–")):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                self.tbl_ir.setItem(i, j, it)
        self.tbl_ir.resizeColumnsToContents()
        self._loading = False

    def update_ea(self):
        """Elementaranalyse: berechnet aus der Formel (+ Solvat), gefunden wie eingegeben; Warnung ab 0.4 %."""
        st = self.st
        formula, _ = self.formula()
        self._ea_line = ("", "")
        for el in SI.EA_ELEMENTS:
            self.ea_calc_lbl[el].setText("–")
        if not formula:
            self.lbl_ea_formula.setText(T("ea_no_formula"))
            self.txt_ea.setHtml("")
            self.lbl_ea_info.setText("")
            return
        try:
            comp = SI.ea_composition(formula, st.get("ea_solvate", ""))
            label = SI.ea_formula_label(formula, st.get("ea_solvate", ""))
            plain, html, notes = SI.ea_line(formula, st.get("ea_solvate", ""), st.get("ea_found") or {})
        except (ValueError, KeyError) as e:
            self.lbl_ea_formula.setText(formula)
            self.lbl_ea_info.setText(str(e))
            self.lbl_ea_info.setStyleSheet(WARN_CSS)
            self.txt_ea.setHtml("")
            return
        self.lbl_ea_formula.setText(label)
        for el in SI.EA_ELEMENTS:
            if el in comp:
                self.ea_calc_lbl[el].setText(f"{comp[el]:.2f}")
        if not st.get("ea_found"):
            self.txt_ea.setHtml("")
            self.lbl_ea_info.setText(T("ea_enter"))
            self.lbl_ea_info.setStyleSheet(HINT_CSS)
            return
        self._ea_line = (plain, html)
        self.txt_ea.setHtml(html)
        if notes:
            self.lbl_ea_info.setText(T("ea_dev", els=", ".join(f"{el} {d:+.2f}" for el, d in notes)))
            self.lbl_ea_info.setStyleSheet(WARN_CSS)
        else:
            self.lbl_ea_info.setText(T("ea_ok"))
            self.lbl_ea_info.setStyleSheet(HINT_CSS)

    def si_parts(self):
        """Fertige Zeilen für den SI-Export: [(Klartext, HTML)] für IR und EA (leere fehlen)."""
        self.figure_spec()
        return [x for x in (self._ir_line, self._ea_line) if x and x[0]]

    # -- Abbildung ------------------------------------------------------------------
    def figure_spec(self):
        st = self.st
        peaks = self.peaks()
        self.fill_ir_table(peaks)
        off = set(st.get("ir_off") or [])
        use = [p for p in peaks if round(p["wn"]) not in off]
        self._ir_line = ir_line(use, st["with_int"]) if use else ("", "")
        self.txt_ir.setHtml(self._ir_line[1])
        self.update_ea()
        sp = self.spectrum()
        if sp is None:
            return None
        cfg = self.base_cfg()
        (lo, hi), _ = self.ir_range()
        x0, x1 = (st["x_min"], st["x_max"]) if not st["x_auto"] else (min(lo, hi), max(lo, hi))
        cfg["xlim"] = [x1, x0]                           # Wellenzahl fällt nach rechts (IR-Konvention)
        mode = self.mode()
        y = display_y(sp, mode)
        sel = (sp["wn"] >= x0) & (sp["wn"] <= x1)
        cfg["ylim"], rejected = y_limits(y[sel], mode, st["ymax"])
        if rejected:
            self.add_note(T("ir_ymax_low"))
        span = cfg["ylim"][1] - cfg["ylim"][0]
        cfg["xlabel"] = "wavenumber [cm$^{-1}$]"
        cfg["ylabel"] = "transmittance [%]" if mode == "T" else "absorbance"
        cfg["legend"] = False
        curves = [{"x": sp["wn"], "y": y, "color": IR_COLOR, "label": None, "ls": "-", "lw": 1.0}]
        labels = []
        if use:
            px = np.array([p["wn"] for p in use])
            o = np.argsort(sp["wn"])
            py = np.interp(px, sp["wn"][o], y[o])
            dy = -0.03 * span if mode == "T" else 0.03 * span
            curves.append({"x": px, "y": py + dy, "val": py, "color": "#14247a", "ls": "None",
                           "marker": "^" if mode == "T" else "v", "ms": 3, "label": None})
            if st.get("ir_labels"):                     # Labels am Peak: unter dem Minimum bzw. über dem Maximum
                for p, yv in zip(use, py):
                    if x0 <= p["wn"] <= x1 and np.isfinite(yv):
                        labels.append({"key": f"label_ir_{round(p['wn'])}", "lam": p["wn"], "y": float(yv),
                                       "side": "below" if mode == "T" else "above",
                                       "text": f"{round(p['wn'])}"})
        self._ir_fig = {"side": "below" if mode == "T" else "above",
                        "fixed_top": bool(st["ymax"]) and not rejected}
        return cfg, curves, labels, []

    def build(self, fig):
        quiet = TABS.core.LOG
        TABS.core.LOG = lambda *a: None
        try:
            spec = self.figure_spec()
        finally:
            TABS.core.LOG = quiet
        if spec is None:
            return None
        cfg, curves, labels, sticks = spec
        TABS.core.setup_fonts(TABS.plt, cfg)
        return IRFigure(TABS.plt, cfg, curves, labels, self.layout(), fig=fig, sticks=sticks, **self._ir_fig)

    def hover_text(self, x, val, name):
        fmt = ".1f" if self.mode() == "T" else ".3f"
        return f"ṽ = {x:.0f} cm⁻¹" + (f"    {val:{fmt}}" if val is not None else "")

    def export_to(self, base: Path):
        """Abbildung (falls Spektrum) und die SI-Zeilen als Text."""
        base = Path(base)
        files = []
        if self.spectrum() is not None:
            files = super().export_to(base)
        else:
            self.figure_spec()
        p = base.with_name(base.name + "_SI.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(x for x in (self._ir_line[0], self._ea_line[0]) if x) + "\n",
                     encoding="utf-8")
        return files + [p]
