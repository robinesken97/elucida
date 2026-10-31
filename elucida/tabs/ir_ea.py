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
from elucida.formats.elements import ELEMENTS  # noqa: E402
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


_FTOK = re.compile(r"(?:\[(\d+)([A-Z][a-z]?)\]|([A-Z][a-z]?))(\d*)|(\()|\)(\d*)")
NO_NATURAL = {"Tc", "Pm", "Po", "At", "Rn"}          # ohne stabile Isotope: Masse nur mit Massenzahl
_ISO = re.compile(r"\[(\d+)([A-Z][a-z]?)\]")


def _formula_part(s: str) -> dict:
    stack = [{}]
    pos = 0
    while pos < len(s):
        m = _FTOK.match(s, pos)
        if not m:
            raise ValueError(f"Summenformel nicht lesbar: {s}")
        pos = m.end()
        if m.group(5):                               # „(“
            stack.append({})
        elif m.group(0).startswith(")"):
            if len(stack) == 1:
                raise ValueError(f"Summenformel nicht lesbar: {s}")
            grp, k = stack.pop(), int(m.group(6) or 1)
            for el, n in grp.items():
                stack[-1][el] = stack[-1].get(el, 0) + n * k
        else:
            sym = m.group(3) or m.group(2)
            if sym not in ELEMENTS and sym != "D":
                raise ValueError(f"Element {sym} nicht bekannt")
            if sym in NO_NATURAL and not m.group(2):
                raise ValueError(f"Element {sym} ohne natürliche Isotope: Massenzahl angeben, z. B. [99{sym}]")
            el = m.group(3) or f"[{m.group(1)}{m.group(2)}]"     # Isotop wie RDKit: [13C]
            stack[-1][el] = stack[-1].get(el, 0) + int(m.group(4) or 1)
    if len(stack) != 1:
        raise ValueError(f"Summenformel nicht lesbar: {s}")
    return stack[0]


def parse_formula(text: str) -> dict:
    """'C31H21N3' / 'C18H20N2+' / 'Ca(OH)2' / 'C18H20N2·2H2O' / '[13C]H4' (Isotope wie RDKit) -> {'C': 31, …,
    '[13C]': 1}; Ladung am Ende wird ignoriert (kommt vom Addukt). Nicht lesbare Teile -> ValueError."""
    text = re.sub(r"[+\-−]+\d*$", "", str(text).replace(" ", ""))
    out = {}
    for part in re.split(r"[·•*]", text):
        m = re.fullmatch(r"(\d+)?(.+)", part)
        if not m:
            raise ValueError(f"Summenformel nicht lesbar: {text}")
        k = int(m.group(1) or 1)
        for el, n in _formula_part(m.group(2)).items():
            out[el] = out.get(el, 0) + n * k
    if not out:
        raise ValueError("keine Summenformel")
    return out


def element_of_key(key: str) -> str:
    """'[13C]' -> 'C', 'C' -> 'C'."""
    m = _ISO.fullmatch(key)
    return m.group(2) if m else key


def mono_mass(key: str) -> float:
    """Monoisotopische Masse: Tabelle MONO, sonst häufigstes Isotop aus RDKit; '[13C]' = Masse des Isotops."""
    if key in MONO:
        return MONO[key]
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    m = _ISO.fullmatch(key)
    mass = (pt.GetMassForIsotope(pt.GetAtomicNumber(m.group(2)), int(m.group(1))) if m
            else pt.GetMostCommonIsotopeMass(pt.GetAtomicNumber(key)))
    if not mass > 0:
        raise ValueError(f"keine Masse für {key}")
    return float(mass)


def formula_str(counts: dict) -> str:
    """Hill-Reihenfolge: C, H, dann alphabetisch (Isotope beim Element)."""
    def order(k):
        el = element_of_key(k)
        r = {"C": 0, "H": 1, "D": 2}.get(el, 3)
        return (r, el if r == 3 else "", k)
    keys = sorted((k for k in counts if counts[k]), key=order)
    return "".join(f"{k}{counts[k] if counts[k] != 1 else ''}" for k in keys)


def formula_html(f: str) -> str:
    """'[13C]H5' -> <sup>13</sup>CH<sub>5</sub>."""
    return re.sub(r"\[(\d+)([A-Z][a-z]?)\]|(\d+)",
                  lambda m: f"<sup>{m.group(1)}</sup>{m.group(2)}" if m.group(1) else f"<sub>{m.group(3)}</sub>", f)


def ion(formula: str, adduct: str = "M+H"):
    """-> (Ionenformel ohne Ladung, Ladung ±1, m/z calc, Addukt-Anzeige)."""
    counts = parse_formula(formula)
    label, delta, z = ADDUCTS[adduct]
    for el, n in delta.items():
        counts[el] = counts.get(el, 0) + n
    if any(v < 0 for v in counts.values()):
        raise ValueError("Addukt passt nicht zur Formel")
    m = sum(mono_mass(el) * n for el, n in counts.items()) - z * ELECTRON
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
    ≥ prominence · max(d). rel (w/m/s) = Tiefe in T relativ zur stärksten Bande des ganzen Spektrums.
    -> [dict(wn, depth, rel, width)] absteigend nach Wellenzahl."""
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
        if dd[i] < dd[a:b].max() or dd[i] <= 0 or dd[i] == dd[i - 1]:     # Plateau: nur am Anfang
            continue
        j = i                                        # gesättigte Bande (flache Spitze): Mitte des Plateaus
        while j < len(x) - 1 and dd[j + 1] == dd[i]:
            j += 1
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
        xi = float(x[i] + x[j]) / 2                  # Lage zwischen den Messpunkten per Parabel (wie OPUS)
        den = dd[i - 1] - 2 * dd[i] + dd[i + 1]
        if den < 0 and j == i:
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
    # w/m/s wie üblich: Tiefe im Transmissionsspektrum (100 − T, auch bei Absorbanzdateien) relativ zur stärksten
    # Bande des ganzen gemessenen Spektrums – unabhängig vom gewählten Bereich
    dT = 100.0 - (y if kind == "T" else to_transmission(y))
    ok = np.isfinite(dT)
    if uniq and ok.sum() >= 5:
        o2 = np.argsort(wn[ok])
        xs, ds = wn[ok][o2], dT[ok][o2]
        ds = ds - float(np.percentile(ds, 5))
        dmx = float(ds.max()) or 1.0
        for p in uniq:
            p["rel"] = float(np.interp(p["wn"], xs, ds)) / dmx
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


# Felder „y-Bereich“ je Darstellung: (Minimum, Maximum, Nachkommastellen, Schritt) und Vorgabe beim Abschalten von
# „auto“ ohne Bild
Y_SPIN = {"T": (0.0, 100.0, 0, 5.0), "A": (-1.0, 10.0, 2, 0.1)}
Y_DEFAULT = {"T": (0.0, 100.0), "A": (0.0, 1.0)}


def y_limits(y, mode, manual=None):
    """y-Grenzen [unten, oben] für das IR-Bild und ob ein eingegebener Bereich verworfen wurde.
    auto: %T oben 100 (bzw. höchster Messwert) + 2 % Luft, damit die Basislinie bei 100 % nicht im Rahmen verschwindet
    (Nutzerwunsch P10), unten nach den Daten (Platz für Labels schafft
    IRFigure); Absorbanz unten 0 (bzw. tiefster Wert, falls negativ), oben nach den Daten.
    manual = (min, max): exakt übernommen, %T auf 0–100 begrenzt; min ≥ max -> verworfen (auto)."""
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    ymin, ymaxv = (float(y.min()), float(y.max())) if len(y) else (0.0, 100.0 if mode == "T" else 1.0)
    span = ymaxv - ymin or 1.0
    if manual is not None:
        lo, hi = float(manual[0]), float(manual[1])
        if mode == "T":
            lo, hi = min(max(lo, 0.0), 100.0), min(max(hi, 0.0), 100.0)
        if lo < hi:
            return [lo, hi], False
    if mode == "T":
        lo = ymin - 0.08 * span
        hi = max(100.0, ymaxv) + 0.02 * span
    else:
        lo = min(0.0, ymin)
        hi = ymaxv + 0.05 * span
    if hi <= lo:
        hi = lo + 1.0
    return [lo, hi], manual is not None


def wn_text(v):
    """Wellenzahl als ganze Zahl, x.5 aufgerundet (round() rundet x.5 zur geraden Zahl)."""
    return f"{int(np.floor(v + 0.5)):d}"


def intensity_tag(p, broad=BROAD_CM):
    """w/m/s nach relativer Tiefe (≥ 0.6 s, ≥ 0.3 m), „br“ bei breiten Banden."""
    t = "s" if p["rel"] >= 0.6 else ("m" if p["rel"] >= 0.3 else "w")
    return ("br " + t) if p.get("width", 0) > broad else t


def ir_line(peaks, with_intensity=False):
    """-> (Klartext, HTML) wie in der SI: IR [cm⁻¹]: ṽ = 2961, 2866, … (ganze Zahlen, absteigend)."""
    vals = sorted(peaks, key=lambda p: -p["wn"])
    items = [wn_text(p["wn"]) + (f" ({intensity_tag(p)})" if with_intensity and "rel" in p else "") for p in vals]
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
    if rt is not None:                                 # 1e-6 s: Grenzen kommen über min zurück (Rundung)
        use = (xic[:, 0] >= min(rt) - 1e-6) & (xic[:, 0] <= max(rt) + 1e-6) & (xic[:, 2] > 0)
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
    f_html = formula_html(f_ion)
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
    """IR-Abbildung wie der OPUS-Bericht (Nutzerwunsch P10, ohne Nachkommastellen): Wellenzahl-Labels senkrecht in
    einer Reihe am unteren Rand (Transmission) bzw. oberen Rand (Absorbanz), nebeneinander so nah wie möglich an ihrem
    Peak, dazwischen Hilfslinien zum Peak (senkrecht – schräg – senkrecht); die y-Achse wächst, bis das Spektrum
    jenseits der Hilfslinien bleibt. Gespeicherte (gezogene) Positionen haben Vorrang (dann ohne Hilfslinie)."""

    def __init__(self, *a, side="below", fixed=False, **kw):
        self._ir_side, self._ir_fixed = side, fixed       # fixed: y-Bereich vom Nutzer -> nie erweitern
        self.ir_clamped = []                               # Labels, die im festen Bereich nicht ganz passen
        self.ir_leaders, self._ir_lines = {}, []           # key -> (Peak-x, Label-x, y am Label, y am Spektrum)
        super().__init__(*a, **kw)

    def _make_labels(self, labels):
        super()._make_labels(labels)
        for ann in self.ann_items.values():
            ann.set_rotation(90)

    def _ir_positions(self):
        """-> {key: (x, y)} lower-left in Achsenbruchteilen; erweitert dabei ggf. die y-Achse, füllt ir_leaders."""
        self.ir_leaders = {}
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
            keys, tgt, wid, hgt = [], [], [], []
            for key, ann in self.ann_items.items():
                _, _, bw, bh = self._measure_af(ann.get_window_extent(rend))
                keys.append(key)
                tgt.append((ann.xy[0] - x0) / (x1 - x0))
                wid.append(bw + gx)
                hgt.append(bh)
            h = max(hgt)
            lead = 3 * max(wid) * ab.width / ab.height     # Hilfslinie drei Labelbreiten hoch (wie OPUS)
            cen = spread_centers(tgt, wid)
            row = gy if below else 1 - gy - h              # Unterkante der Labelreihe
            near = row + h + gy if below else row - gy     # Hilfslinie: Ende am Label …
            far = near + lead if below else near - lead    # … und am Spektrum
            pos = {k: (c - (w - gx) / 2, row) for k, c, w in zip(keys, cen, wid)}
            self.ir_leaders = {k: (t, c, near, far) for k, t, c in zip(keys, tgt, cen)}
            gm = gy + 2.0 * self.fig.dpi / 72 / ab.height  # Abstand + halbe Peakmarke (ms 3), Marken zählen mit
            q = far + gm if below else far - gm            # das Spektrum bleibt jenseits davon
            fy = (Y_ - y0) / (y1 - y0)
            if (fy.min() >= q - 1e-9) if below else (fy.max() <= q + 1e-9):
                break
            if self._ir_fixed or not (q < 0.9 if below else q > 0.1):   # fest bzw. Achse zu klein: Labels melden,
                fx = (X_ - x0) / (x1 - x0)                 # deren Spalte das Spektrum kreuzt
                for k, t, c, w in zip(keys, tgt, cen, wid):
                    m = (fx >= min(t, c) - w / 2) & (fx <= max(t, c) + w / 2)
                    if m.any() and ((fy[m].min() < q) if below else (fy[m].max() > q)):
                        self.ir_clamped.append(k)
                break
            if below:                                      # unten Platz schaffen: (Ymin − Y0)/(y1 − Y0) ≥ q
                ax.set_ylim((Y_.min() - q * y1) / (1 - q), y1)
            else:                                          # oben: (Ymax − y0)/(Y1 − y0) ≤ q
                ax.set_ylim(y0, y0 + (Y_.max() - y0) / q)
            self._fit_axes(pad)
        return {k: (min(max(x, 0.0), 1.0), y) for k, (x, y) in pos.items()}

    def _place(self):
        auto = self._ir_positions()
        orig = self.layout
        self.layout = {**{k: list(v) for k, v in auto.items()}, **orig}
        try:
            super()._place()
        finally:
            self.layout = orig
        for ln in self._ir_lines:
            ln.remove()
        self._ir_lines = []
        for k, (t, c, near, far) in self.ir_leaders.items():
            if k in orig or k not in self.ann_items:      # gezogenes Label: keine Hilfslinie
                continue
            d = (near - far) / 3                           # senkrecht – schräg – senkrecht
            ln = TABS.plt.Line2D([t, t, c, c], [far, far + d, far + 2 * d, near], transform=self.ax.transAxes,
                                 lw=0.6, color=self.ann_items[k].get_color(), clip_on=False)
            self.ax.add_line(ln)
            self._ir_lines.append(ln)


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
                         ea_solvate="", ea_found={}, ir_mode="T",     # "T" | "A"; None (alte Projekte) = wie die Datei
                         y_auto=True, y_min=0.0, y_max=100.0,        # y-Bereich (ymax: nur alte Projekte)
                         ir_color=IR_COLOR)                          # Farbe des Spektrums (FB-13)

    def build_controls(self):
        st = self.st
        self.migrate_ymax()
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

        def pick_color(c):
            self.st["ir_color"] = c
            self.changed()
        self.btn_ircolor = TABS.color_button(st.get("ir_color") or IR_COLOR, pick_color)
        f.addRow(T("ov_color"), self.btn_ircolor)
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
        """Statt „y-Achse max“ eine Zeile „y-Bereich“: auto | min – max (exakt)."""
        g = super().common_box()
        fl = g.layout()
        r, _ = fl.getWidgetPosition(self.sp_ymax)
        fl.setRowVisible(r, False)
        row = QHBoxLayout()
        self.cb_yauto = QCheckBox(T("auto"))
        self.cb_yauto.setToolTip(T("ir_yrange_tip"))
        self.sp_ymin = QDoubleSpinBox()
        self.sp_ymax2 = QDoubleSpinBox()
        for w_ in (self.cb_yauto, self.sp_ymin, QLabel("–"), self.sp_ymax2):
            row.addWidget(w_)
        fl.insertRow(r + 1, T("ir_yrange"), row)
        self.cb_yauto.toggled.connect(self.yauto_toggled)
        self.cb_yauto.toggled.connect(self.changed)
        for w_ in (self.sp_ymin, self.sp_ymax2):
            w_.valueChanged.connect(self.changed)
        self.sync_yrange()
        return g

    def migrate_ymax(self):
        """Alte Projekte (bis 2.3.6): „y-Achse max“ > 0 -> fester y-Bereich mit dieser Obergrenze und der damaligen
        automatischen Untergrenze; der alte Schlüssel wird danach 0 (bleibt lesbar)."""
        st = self.st
        old = float(st.get("ymax") or 0.0)
        if old <= 0:
            return
        st["ymax"] = 0.0
        mode = self.mode()
        sp = self.spectrum()
        auto, _ = y_limits(display_y(sp, mode) if sp else [], mode)
        top = min(old, 100.0) if mode == "T" else old
        lo = max(auto[0], 0.0) if mode == "T" else auto[0]
        if top > lo:
            st.update(y_auto=False, y_min=round(lo, 2), y_max=round(top, 2))

    def yauto_toggled(self, on):
        """„auto“ aus: Felder mit dem aktuell gezeigten Bereich vorbelegen (dann nur noch verschieben)."""
        if self._loading or on:
            return
        lo, hi = self.F.ax.get_ylim() if self.F is not None else Y_DEFAULT[self.mode()]
        mn, mx, dec, _ = Y_SPIN[self.mode()]
        for sp_, v in ((self.sp_ymin, lo), (self.sp_ymax2, hi)):
            sp_.blockSignals(True)
            sp_.setValue(round(min(max(v, mn), mx), dec))
            sp_.blockSignals(False)

    def sync_yrange(self):
        """Felder „y-Bereich“ passend zur Darstellung: %T 0–100 in ganzen Prozent, Absorbanz −1–10."""
        if getattr(self, "sp_ymin", None) is None:
            return
        mode, st = self.mode(), self.st
        mn, mx, dec, step = Y_SPIN[mode]
        auto = bool(st.get("y_auto", True))
        for sp_, k in ((self.sp_ymin, "y_min"), (self.sp_ymax2, "y_max")):
            sp_.blockSignals(True)
            sp_.setDecimals(dec)
            sp_.setRange(mn, mx)
            sp_.setSingleStep(step)
            sp_.setSuffix(" %" if mode == "T" else "")
            sp_.setValue(float(st.get(k, 0.0)))
            sp_.setEnabled(not auto)
            sp_.blockSignals(False)
        self.cb_yauto.blockSignals(True)
        self.cb_yauto.setChecked(auto)
        self.cb_yauto.blockSignals(False)

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
            lo, hi = Y_DEFAULT[m]                      # Bereich gehört zur alten Einheit -> auto
            self.st.update(y_auto=True, y_min=lo, y_max=hi)
            self.st["layout"][self.size_key()] = {}    # Labels wechseln die Seite
        self.sync_yrange()
        self.timer.start()

    # -- Dateien --------------------------------------------------------------------
    def choose_ir(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ir_files"), self.main.settings.value("last_dir", ""),
                                             f"{T('flt_ir')};;{T('flt_all')}")
        self.load_ir_files(ps)

    def load_ir_files(self, ps):
        """Mehrere Dateien auf einmal: das letzte Spektrum gilt; ein PDF nur, wenn es eindeutig zu ihm gehört (einziges
        Spektrum der Auswahl oder gleicher Dateiname), sonst Hinweis statt fremder Peaks."""
        spec = [p for p in ps if Path(p).suffix.lower() != ".pdf"]
        pdfs = [p for p in ps if Path(p).suffix.lower() == ".pdf"]
        for p in spec:
            self.load_ir(p)
        if spec and len(spec) > 1:
            same = [p for p in pdfs if Path(p).stem == Path(spec[-1]).stem]
            if pdfs and not same:
                self.main.error(T("ir_pdf_ambiguous"))
            pdfs = same
        for p in pdfs[-1:]:
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
                if self.st.get("ir_file") and self.st["ir_file"] != p:
                    self.st["ir_pdf"] = None             # PDF gehörte zum vorigen Spektrum
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
        pdf = self.st.get("ir_pdf")
        if sp is None and pdf and Path(pdf).exists():   # nur PDF: alle Peakwerte liegen im ganzen Bereich
            vals = self.cache(("irpdf", pdf), lambda: read_ir_pdf(pdf))
            full = (min([full[0], *vals]), max([full[1], *vals]))
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
        c_ = st.get("ir_color") or IR_COLOR
        self.btn_ircolor.setProperty("color", c_)
        self.btn_ircolor.setStyleSheet(f"background-color: {c_}; border: 1px solid #777;")
        self.sp_prom.setValue(st.get("prominence", 5.0))
        self.cmb_mode.setCurrentIndex(self.cmb_mode.findData(self.mode()))
        self.sync_yrange()
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
        if getattr(self, "sp_ymin", None) is not None:
            lo, hi = self.sp_ymin.value(), self.sp_ymax2.value()
            if lo >= hi:                                  # min < max: das gerade nicht geänderte Feld weicht aus
                step = Y_SPIN[self.mode()][3]
                if self.sender() is self.sp_ymax2:
                    lo = max(Y_SPIN[self.mode()][0], hi - step)
                    hi = max(hi, lo + step)
                else:
                    hi = min(Y_SPIN[self.mode()][1], lo + step)
                    lo = min(lo, hi - step)
            st.update(y_auto=self.cb_yauto.isChecked(), y_min=lo, y_max=hi)
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
        manual = None if st.get("y_auto", True) else (st["y_min"], st["y_max"])
        cfg["ylim"], rejected = y_limits(y[sel], mode, manual)
        if rejected:
            self.add_note(T("ir_yrange_bad"))
        span = cfg["ylim"][1] - cfg["ylim"][0]
        cfg["xlabel"] = "wavenumber [cm$^{-1}$]"
        cfg["ylabel"] = "transmittance [%]" if mode == "T" else "absorbance"
        cfg["legend"] = False
        curves = [{"x": sp["wn"], "y": y, "color": st.get("ir_color") or IR_COLOR, "label": None, "ls": "-", "lw": 1.0}]
        labels = []
        if use:
            px = np.array([p["wn"] for p in use])
            o = np.argsort(sp["wn"])
            py = np.interp(px, sp["wn"][o], y[o])
            dy = -0.03 * span if mode == "T" else 0.03 * span
            vis = (py >= cfg["ylim"][0]) & (py <= cfg["ylim"][1])   # fester y-Bereich: Peaks außerhalb ohne Marke/Label
            use = [p for p, v in zip(use, vis) if v]
            px, py = px[vis], py[vis]
            curves.append({"x": px, "y": py + dy, "val": py, "color": "#14247a", "ls": "None",
                           "marker": "^" if mode == "T" else "v", "ms": 3, "label": None})
            if st.get("ir_labels"):                     # Labels am Peak: unter dem Minimum bzw. über dem Maximum
                for p, yv in zip(use, py):
                    if x0 <= p["wn"] <= x1 and np.isfinite(yv):
                        labels.append({"key": f"label_ir_{round(p['wn'])}", "lam": p["wn"], "y": float(yv),
                                       "side": "below" if mode == "T" else "above",
                                       "text": wn_text(p["wn"])})
        self._ir_fig = {"side": "below" if mode == "T" else "above",
                        "fixed": manual is not None and not rejected}
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
        F = IRFigure(TABS.plt, cfg, curves, labels, self.layout(), fig=fig, sticks=sticks, **self._ir_fig)
        if F.ir_clamped:
            self.add_note(T("ir_labels_clamped", n=len(F.ir_clamped)))
        return F

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
