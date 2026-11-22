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
import io
import re
import uuid
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from elucida import ROOT
from elucida.core import images as IMG
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
# Struktur des internen Standards an seiner Welle (Entscheidung 176/179): einmal mit Octet „Name to Structure“
# gezeichnet (Sandwich), Octets SVG unverändert, im Bild in Druckgröße (wie ChemDraw ACS 1996)
REF_STRUCTS = {"fc": "ferrocene.svg", "ac2fc": "diacetylferrocene.svg"}
REF_BOND_PT = 14.4                     # Bindungslänge dieser SVGs (ACS 1996, nachgemessen ~14.5 pt)

# Basislinie endet so weit vor dem Hinpeak. 0,20 V = E½ − 0,17 V: dort trägt eine ideal reversible Welle (n = 1, 25 °C)
# etwa 0,3 % von i_p, der Fehler von i_p bleibt unter 1 % (simuliert: 0,2–0,8 % je nach Fensterbeginn). Mit den
# früheren 0,15 V (E½ − 0,12 V, noch 2 % von i_p) lag die Gerade auf dem Fuß: i_p 1–3 % zu klein, Nicholson +0,015
# (Literaturprüfung 2026-11, Nutzerentscheidung „das wissenschaftlich Korrekte“). Gespeicherte Verbindungen behalten
# ihren Wert.
BL_GAP = 0.20
# Reicht der Vorlauf im Fenster dafür nicht, endet die Gerade wie früher 0,15 V vor dem Peak (gekennzeichnet, `bl_short`:
# i_p dort bis etwa 6 % zu klein, simuliert) – sonst bekäme eine Messung mit kurzem Vorlauf gar keine Basislinie mehr.
BL_GAP_MIN = 0.15
# … und spätestens am Anstieg der Welle: Strom (geglättet) 2 % der Peakhöhe über dem Anfangsstrom des Fensters.
# Nötig für breite Wellen (iR-Abfall, quasi-reversibel): dort beginnt der Anstieg
# weit mehr als 0,15 V vor dem Peak, und eine Gerade durch den Fuß überkorrigiert i_p massiv.
BL_ONSET = 0.02
# Nicholson gilt nur, wenn zwischen Hinpeak und Umkehrpotential kein weiterer Prozess liegt (sonst ist i_sp und der
# abklingende Strom ein anderer). Erkennung: Strom steigt im Hinlauf nach dem Peak wieder um > 10 % der Peakhöhe an.
NICHOLSON_RISE = 0.10
X_PAD = 0.03                # Rand links/rechts der Kurven (Anteil der Spanne): sie liefen sonst bis an den Rahmen
PEAK_REL = 0.03             # Peak = Prominenz > 3 % des größten |I| der Kurve (Vorschlag der Paare und Zwei-Wellen-Prüfung)
F_CONST, R_CONST = 96485.33212, 8.314462618
# D aus Randles–Ševčík gilt nur für ein reversibles Paar: ΔE_p höchstens so groß wie das der internen Referenz derselben
# Messung (sie trägt denselben iR-Abfall) bzw. ohne sie wie das einer reversiblen Welle, 2,22·RT/(nF), plus diese Toleranz
D_DEP_TOL = 0.010
# k⁰ aus ΔE_p (n·ΔE_p in mV, auf 25 °C umgerechnet): unter K0_X_MIN zu nah am reversiblen Grenzwert (ψ → ∞), bis K0_X_MAX
# Lavagnini (Näherung an Nicholsons ψ-Tabelle), darüber Klingler–Kochi (nur mit eingegebenem α). Simuliert (Butler–Volmer,
# α = 0,5, Umkehr 0,6 V hinter E°, wahres D): 66–160 mV −14 … +17 %, darüber Klingler–Kochi −7 … +7 %; bei 62–64 mV
# +21 … +27 % (ψ ändert sich dort steil mit ΔE_p), deshalb erst ab 66 mV
K0_X_MIN, K0_X_MAX = 66.0, 160.0
# „k⁰ fällt mit v“ (iR-Abfall): k⁰ bei der größten Scanrate unter 75 % des Werts bei der kleinsten. Simuliert ohne Ru:
# Lavagnini driftet selbst um bis zu −17 % (ψ-Näherung ±15 %); mit Ru = 1 kΩ fällt k⁰ um 34 % bzw. 57 %
K0_FALL = 0.75
# Referenz per Klick (Entscheidung 171): ein Klick sucht den Peak in ±REF_SNAP V um die Klickstelle (Parabel wie die
# Paare); das gespeicherte Fenster reicht REF_PADS V über beide Peaks (das erste, das genau diese Peaks wiederfindet)
REF_SNAP = 0.08
REF_PADS = (0.15, 0.10, 0.07, 0.05, 0.03)
# Nur bei gleicher Scanrate ist ΔE_p einer Referenz in eigener Messung ein fairer Vergleich für die D-Schwelle
REF_RATE_TOL = 0.5          # mV s⁻¹


def _smooth(I):
    return np.convolve(I, np.ones(5) / 5, mode="same")


def find_peaks(E, I, mask, sign, min_rel=PEAK_REL, half_width=0.15):
    """Peaks von sign·I im Lauf `mask` (Messpunkte in Messreihenfolge) -> Indizes. Lokales Maximum des geglätteten Stroms
    (5 Punkte) mit Prominenz gegen die Minima in ±half_width V über min_rel·max|I| (breite Peaks). Zwei Maxima zählen nur
    getrennt, wenn der Strom zwischen ihnen um mehr als dieselbe Schwelle unter das kleinere fällt: Rauschen auf einer
    Peakspitze ergibt sonst zwei „Peaks“ mit der Prominenz der ganzen Welle."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    thr = min_rel * (np.nanmax(np.abs(I)) or 1.0)
    idx = np.flatnonzero(mask)
    y = sign * _smooth(I)
    out = []
    for j in range(3, len(idx) - 3):
        k = idx[j]
        if y[k] < y[idx[j - 3:j + 4]].max():
            continue
        left = idx[(E[idx] >= E[k] - half_width) & (E[idx] <= E[k])]
        right = idx[(E[idx] <= E[k] + half_width) & (E[idx] >= E[k])]
        if len(left) < 3 or len(right) < 3:
            continue
        if y[k] - max(y[left].min(), y[right].min()) <= thr:
            continue
        if out:
            p = out[-1]
            between = idx[(idx > p) & (idx < k)]
            low = min(y[p], y[k])
            if not len(between) or low - y[between].min() <= thr:      # keine echte Senke dazwischen: derselbe Peak
                if y[k] > y[p]:
                    out[-1] = k
                continue
        out.append(k)
    return out


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
    # Der Messpunkt am Umkehrpunkt zählt zu keiner Seite: ob er noch den Ladestrom des Hinlaufs trägt oder schon den des
    # Rücklaufs, steht in keiner Datei – mitgefittet halbierte er im zweiten Fall den Sprung (Literaturprüfung 2026-11)
    before = np.arange(max(0, k_turn - 6), k_turn)
    after = np.arange(k_turn + 1, min(n, k_turn + 8))
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
    bl, fail, short = None, False, False
    ia, ic, i_sp = ipa, ipc, float(I[turn])
    if use_baseline:
        # Vorlauf nur aus dem Abschnitt des Hinpeaks (gleiche Richtung ab dem vorigen Umkehrpunkt)
        other = np.flatnonzero(np.sign(dE[:k_f]) != s)
        seg = np.zeros(len(E), bool)
        seg[(other[-1] + 1 if len(other) else 0):turn + 1] = True
        bl = baseline(E, I, k_f, turn, (fw if anodic_first else bw) & seg, s, gap)
        if bl is None and gap > BL_GAP_MIN:
            bl = baseline(E, I, k_f, turn, (fw if anodic_first else bw) & seg, s, BL_GAP_MIN)
            short = bl is not None
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
    # zwei Wellen im Fenster (Paare ≤ ~0,25 V auseinander): E_pa und E_pc kämen sonst von verschiedenen Paaren – ein
    # plausibles, falsches E½/ΔE_p. Peaks auf dem ganzen Lauf suchen (im Fenster wären die Flanken abgeschnitten)
    n_a = sum(lo <= E[k] <= hi for k in find_peaks(E, I, dE > 0, 1))
    n_c = sum(lo <= E[k] <= hi for k in find_peaks(E, I, dE < 0, -1))
    two = n_a > 1 or n_c > 1
    # Halbpeakpotential des Hinpeaks (|E_p − E_p/2|, CSV): Strom (gegen die Basislinie) = halber Peakstrom, vor dem Peak
    ep2 = None
    run = np.flatnonzero((fw if anodic_first else bw)[:k_f + 1])
    if len(run) > 2:
        base_ = (lambda e: bl["a"] * e + bl["b"]) if bl is not None else (lambda e: 0.0 * e)
        y = s * (I[run] - base_(E[run]))
        half = (abs(ia) if anodic_first else abs(ic)) / 2
        below = np.flatnonzero(y < half)
        if len(below) and below[-1] + 1 < len(run):
            j0, j1 = run[below[-1]], run[below[-1] + 1]
            y0, y1 = y[below[-1]], y[below[-1] + 1]
            ep2 = float(E[j0] + (half - y0) / (y1 - y0) * (E[j1] - E[j0])) if y1 != y0 else float(E[j0])
    return {"epa": epa, "epc": epc, "e12": (epa + epc) / 2, "dep": epa - epc, "ipa": ia, "ipc": ic,
            "ipa_raw": ipa, "ipc_raw": ipc, "ratio": ratio, "ratio_ok": bool(ratio_ok), "edge": bool(edge),
            "two_waves": bool(two), "invalid": bool(edge or two),
            "bl": bl, "bl_fail": fail, "bl_short": bool(short),
            "anodic_first": bool(anodic_first), "ep2": ep2}


def suggest_couples(E, I, min_rel=PEAK_REL, max_sep=0.25, half=0.25):
    """Vorschläge für Redoxpaare: anodische Peaks im Hinlauf mit passendem kathodischen Peak im Rücklauf.
    -> [(lo, hi)]: Fenster je Seite bis `half` V um E½, höchstens bis zur halben Strecke zum E½ des Nachbarpaars (zwei
    Paare in einem Fenster ergäben ein E½ aus beiden). Die freie Seite bleibt weit (Vorlauf für die Basislinie)."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    dE = np.gradient(E)
    an = [float(E[k]) for k in find_peaks(E, I, dE > 0, 1, min_rel)]
    ca = [float(E[k]) for k in find_peaks(E, I, dE < 0, -1, min_rel)]
    mids, used = [], set()
    for a in an:
        cs = [c for c in ca if 0 <= a - c <= max_sep and c not in used]
        if cs:
            c = max(cs)
            used.add(c)
            mids.append((a + c) / 2)
    out = []
    for m in mids:                                        # Reihenfolge wie bisher (Nummern der Paare)
        below = [x for x in mids if x < m]
        above = [x for x in mids if x > m]
        left = min(half, (m - max(below)) / 2) if below else half
        right = min(half, (min(above) - m) / 2) if above else half
        out.append((round(m - left, 2), round(m + right, 2)))
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


def diffusion_coefficient(slope_A, n, area_cm2, conc_mM, temp_C=25.0):
    """Randles–Ševčík für ein reversibles, frei diffundierendes Paar: i_p = 0.4463·n·F·A·c·√(n·F·v·D/(R·T)), also
    D = (m/(0.4463·n·F·A·c))²·R·T/(n·F) mit der Steigung m = di_p/d√v [A (V s⁻¹)^-½], A [cm²], c [mM] → D [cm² s⁻¹].
    Ohne Fläche oder Konzentration: None (nie die Fläche aus der Messdatei annehmen: dort steht oft die Vorgabe 1 cm²)."""
    if not (area_cm2 > 0 and conc_mM > 0 and n > 0):
        return None
    F, R = 96485.33212, 8.314462618
    return (slope_A / (0.4463 * n * F * area_cm2 * conc_mM * 1e-6)) ** 2 * R * (temp_C + 273.15) / (n * F)


def dep_reversible(n=1, temp_C=25.0):
    """ΔE_p einer reversiblen Welle [V]: 2,22·RT/(nF) (Bard & Faulkner §6.2; 57 mV für n = 1 bei 25 °C)."""
    return 2.22 * R_CONST * (temp_C + 273.15) / (n * F_CONST)


def psi_lavagnini(x_mV):
    """Nicholsons ψ aus n·ΔE_p [mV, 25 °C] nach Lavagnini, Antiochia, Magno, Electroanalysis 2004, 16, 505:
    ψ = (−0.6288 + 0.0021·X)/(1 − 0.017·X). Gegen Nicholsons Tabelle (Anal. Chem. 1965, 37, 1351; α = 0,5) geprüft:
    63–141 mV innerhalb ±7 %, bei 61 und 212 mV −30 % (daher nur K0_X_MIN … K0_X_MAX)."""
    return (-0.6288 + 0.0021 * x_mV) / (1 - 0.017 * x_mV)


def k0_value(dep_V, rate_mVs, D, n=1, temp_C=25.0, alpha=0.0):
    """Heterogene Standardgeschwindigkeitskonstante k⁰ [cm s⁻¹] aus ΔE_p einer Scanrate, D_O = D_R = D [cm² s⁻¹].
    X = n·ΔE_p in mV, auf 25 °C umgerechnet (ΔE_p skaliert mit RT/F). X < K0_X_MIN: kein Wert („rev“, zu nah am
    reversiblen Grenzwert); bis K0_X_MAX: ψ nach Lavagnini, k⁰ = ψ·(π·D·n·F·v/(R·T))^½ (Nicholson 1965); darüber
    Klingler & Kochi, J. Phys. Chem. 1981, 85, 1731: k⁰ = 2,18·(D·α·n·F·v/(R·T))^½·exp(−α²·n·F·ΔE_p/(R·T)), nur mit α
    (sonst „alpha“). -> (k⁰ oder None, "lav"|"kk"|"rev"|"alpha")."""
    T_ = temp_C + 273.15
    f = n * F_CONST / (R_CONST * T_)
    v = rate_mVs / 1000.0
    x = n * dep_V * 1000.0 * 298.15 / T_
    if x < K0_X_MIN:
        return None, "rev"
    if x <= K0_X_MAX:
        return psi_lavagnini(x) * np.sqrt(np.pi * D * f * v), "lav"
    if not alpha or alpha <= 0:
        return None, "alpha"
    return 2.18 * np.sqrt(D * alpha * f * v) * np.exp(-alpha ** 2 * f * dep_V), "kk"


def loglog_fit(rates_mVs, ip):
    """log|i_p| gegen log v: Steigung 0,5 = diffusionskontrolliert, 1 = an der Oberfläche gebunden."""
    v, ip = np.asarray(rates_mVs, float), np.abs(np.asarray(ip, float))
    ok = (v > 0) & (ip > 0)
    return rate_fit(np.log10(v[ok] / 1000.0), np.log10(ip[ok]))


def _flag_note(r):
    """Warnung eines ungültigen Paars (Peak am Fensterrand, zwei Wellen im Fenster) für Hinweise und Tooltips."""
    return "".join("  " + T(k) for k, on in (("cv_edge", r.get("edge")), ("cv_two_waves", r.get("two_waves"))) if on)


def sci_range(lo, hi, digits=2):
    """„1.0–1.4 × 10^-2“ (gleicher Exponent, `digits` gültige Stellen), bei gleichen Werten nur einer."""
    ex = int(f"{hi:.{digits - 1}e}".split("e")[1])
    a, b = f"{lo / 10 ** ex:.{digits - 1}f}", f"{hi / 10 ** ex:.{digits - 1}f}"
    return (a if a == b else f"{a}–{b}") + f" × 10^{ex}"


def fmt_ci(v, ci, unit="", ref=None):
    """Wert ± 95-%-KI, gerundet auf die Genauigkeit des Intervalls (core.fmt_ve), höchstens 4 gültige Stellen von `ref`
    (Größenordnung der Spalte, Vorgabe der Wert): ein winziges Intervall (rauschfreie Daten) steht als „± < 0.01“
    statt mit 8 Nachkommastellen (die Regressionstabelle rollte sonst bei 1200 px quer). Nie ein erfundenes Intervall."""
    ref = abs(v if ref is None else ref)
    if ci is not None and np.isfinite(ci) and ref > 0:
        cap = max(0, 3 - int(np.floor(np.log10(ref))))
        if core.ve_decimals(v, ci) > cap:
            a = f"{core.round_half_up(v, cap) or 0.0:.{cap}f}".replace("-", "\u2212")
            return f"{a} ± < {10.0 ** -cap:.{cap}f}{unit}"
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


E_DEC = 2      # E½, Epa, Epc: Stellen wie Bild, Methodentext und Word (seit jeher); Tabelle, Kachel, Vergleich folgen


def _fmt_e(v, nd=3):
    """Potential mit Vorzeichen und echtem Minus, nie „−0.000“."""
    return core.fmt_num(v, nd, sign=True)


ACS_FIELDS = ("acs_we", "acs_ce", "acs_ref", "acs_gas", "acs_device", "acs_polish")   # Karte „Messbedingungen“
# Messaufbau einmal je Projekt (publication.elucida: cv_setup), Nutzerentscheidung 2026-11-13: „CV-Messbedingungen
# gehören gesammelt in den Anfangstext“ – erster Absatz des Kapitels „Cyclic Voltammetry“ der Gesamt-SI
SETUP_KEYS = ("device", "we", "area", "polish", "ce", "ref", "gas", "ir", "conv", "more")
CONVENTIONS = {"iupac": "IUPAC convention (anodic currents positive)",
               "polar": "polarographic convention (cathodic currents positive)"}


def setup_text(v, what="Cyclic voltammograms"):
    """Messaufbau als Fließtext (englisch) wie der Kapitelanfang in der SI des Nutzers: Gerät und iR-Kompensation,
    Atmosphäre, Dreielektrodenanordnung, Konvention, freie weitere Angaben. Nur aus eingetragenen Feldern; ein leeres
    Feld lässt seinen Satzteil weg (keine hängenden Kommas), ohne Angaben leer."""
    def area_txt(a):
        a = str(a).strip()
        if not re.search(r"[A-Za-zµ²]", a):                  # nur eine Zahl: cm² wie im Feld der Fläche
            a += " cm2"
        return re.sub(r"\b(cm|mm)2\b", r"\1²", a)
    out = []
    dev, ir = v.get("device"), v.get("ir")
    if dev:
        out.append(f"{what} were recorded on {dev}" + (f" with iR compensation ({ir})" if ir else "") + ".")
    elif ir:
        out.append(f"The voltammograms were recorded with iR compensation ({ir}).")
    if v.get("gas"):
        out.append(f"The samples were measured under {v['gas']}.")
    items = []
    extra = [x for x in (f"A = {area_txt(v['area'])}" if v.get("area") else "",
                         f"polished with {v['polish']}" if v.get("polish") else "") if x]
    if v.get("we") or extra:
        items.append((f"{v['we']} as working electrode" if v.get("we") else "a working electrode")
                     + (f" ({', '.join(extra)})" if extra else ""))
    if v.get("ce"):
        items.append(f"{v['ce']} as counter electrode")
    if v.get("ref"):
        items.append(f"{v['ref']} as reference electrode")
    if items:
        lst = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
        out.append(("A three-electrode setup was used, consisting of " if len(items) == 3 else "The setup contained ")
                   + lst + ".")
    if v.get("conv") in CONVENTIONS:
        out.append(f"Voltammograms are plotted in the {CONVENTIONS[v['conv']]}.")
    more = str(v.get("more") or "").strip()
    if more:                                              # was sich nicht aus Feldern bilden lässt (Präparation …)
        out.append(more if more.endswith((".", "!", "?")) else more + ".")
    return " ".join(out)


def pulse_params(metas):
    """Pulsparameter aus den Dateien als Text („step 5 mV, pulse amplitude 25 mV …“), nur wenn für alle Pulsmessungen
    gleich; sonst ''."""
    pp = {tuple(sorted((m.get("pulse_par") or {}).items())) for m in metas if m.get("pulse")}
    if len(pp) != 1 or pp == {()}:
        return ""
    par = dict(next(iter(pp)))
    bits = [f"step {par['step_mV']:g} mV" if "step_mV" in par else "",
            f"pulse amplitude {par['pulse_mV']:g} mV" if "pulse_mV" in par else "",
            f"pulse time {par['pulse_s'] * 1000:g} ms" if "pulse_s" in par else "",
            f"frequency {par['freq_Hz']:g} Hz" if "freq_Hz" in par else ""]
    return ", ".join(b for b in bits if b)


def scan_start(E, n=6):
    """Erster Messpunkt und Richtung des Scans (+1 positiv, −1 negativ) aus den aufgezeichneten Potentialen;
    None bei weniger als zwei Punkten."""
    if len(E) < 2:
        return None
    d = np.diff(np.asarray(E[:n], float))
    return float(E[0]), (1 if d.mean() >= 0 else -1)


class CVTab(TABS.FigureTab):
    LABEL_CARD = True                    # Karte „Beschriftungen im Bild“

    def label_view(self):
        return self.st.get("plot", "cv")
    STATE_KEY = "cv"
    GUIDE, GUIDE_ACTION = "cv", ("guide_add", "add_files")
    TEXT_OPTS = ("fonts", "labels", "label_size", "axes_frame", "struct_frame")
    CAP_FIELDS = ("conc", "solvent", "el", "temp")
    CAP_REMEMBER = ("el",)
    SI_CAPTION = "Cyclic voltammograms of {name}."
    X_RANGE = (-10.0, 10.0, 2, 0.1)
    XRANGE_TEXT = "cv_xrange"
    RESET_KEEP = ("files", "couples", "ref_mode", "ref_uid", "ref_lo", "ref_hi", "ref_compound", "ref_value",
                  "ref_offset", "ref_electrode", "cycle",  # Messungen, Zyklus, Redoxpaare und Referenzierung bleiben
                  "rs_n", "rs_area", "rs_conc", "rs_temp",   # Angaben zur Messung für den Diffusionskoeffizienten
                  "k0_D", "k0_alpha",                        # Angaben für k⁰ (eingegebenes D, α für Klingler–Kochi)
                  "acs_we", "acs_ce", "acs_ref", "acs_gas", "acs_device", "acs_polish",   # Messaufbau (ACS-Angaben)
                  "baseline", "bl_gap", "density",            # Peakströme und Stromdichte: Auswertung
                  "plot", "peak_labels")                     # andere SI-Abbildung, andere Größe im Bild
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=-1.5, x_max=-0.5, ymax=0.0, files=[], couples=[], cycle=1,
                         ref_mode="none", ref_uid=None, ref_lo=0.3, ref_hi=0.8, ref_compound="ac2fc",
                         ref_value=REFERENCES["ac2fc"][1], ref_offset=0.0, ref_electrode="Ag/AgNO₃",
                         gradient=True, density=False, show_e12=True, arrow=True, invert=False, ref_marker=True, ref_color=False,
                         plot="cv", stack=False, stack_gap=1.0, e12_each=False, y_axis="auto", peak_labels="e12",
                         struct_w=18.0, baseline=True, bl_gap=BL_GAP, show_bl=False,
                         rs_n=1, rs_area=0.0, rs_conc=0.0, rs_temp=25.0, k0_D=0.0, k0_alpha=0.0,
                         acs_we="", acs_ce="", acs_ref="", acs_gas="", acs_device="", acs_polish="",
                         cap_conc="", cap_solvent="", cap_el="", cap_temp="rt", cap_start=False)

    # CV | ΔE_p gegen v | Randles-Ševčík | log i_p gegen log v | i_r/i_f gegen v | Trumpet-Plot
    PLOTS = ("cv", "dep", "rs", "rs_v", "loglog", "ratio", "trumpet")
    WARN_KINDS = ("bl_fail", "bl_short", "two_waves", "D", "k0", "k0_falls")      # Reihenfolge der Warnzeilen
    MARKERS = ("s", "o", "^", "v", "D", "p")

    # -- Bedienelemente ------------------------------------------------------------

    def arrange(self):
        super().arrange()
        g = STYLE.split_group(self.group_titled("cv_analysis"), self.cmb_ref, self.ed_electrode, T("grp_refs"))
        self.fold(g, "refs", ("ref_mode", "ref_uid", "ref_lo", "ref_hi", "ref_compound", "ref_value", "ref_offset",
                              "ref_electrode"))
        g = STYLE.split_group(self.group_titled("cv_analysis"), self.sp_rs_n, self.lbl_rs_hint, T("grp_diffusion"))
        self.fold(g, "diffusion", ("rs_n", "rs_area", "rs_conc", "rs_temp", "k0_D", "k0_alpha"))
        g = STYLE.split_group(self.group_titled("cv_display"), self.cb_gradient, self.cb_invert, T("grp_more_display"))
        self.fold(g, "more", ("gradient", "density", "show_e12", "arrow", "ref_marker", "ref_color", "invert"))
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
        self.table = QTableWidget(0, 6)                   # Spalte 5: Messung mit dem internen Standard (je Reihe eine)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), "ν [mV s⁻¹]", T("cv_group"), "Fc"])
        self.table.horizontalHeaderItem(5).setToolTip(T("cv_ref_col_tip"))
        self.table.setItemDelegateForColumn(1, STYLE.RichDelegate(self.table, core.unit_html))   # „50 mV s⁻¹“
        self.table.horizontalHeaderItem(4).setToolTip(T("cv_group_tip"))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(140)
        self.table.itemChanged.connect(self.table_edited)
        self.table.currentCellChanged.connect(lambda *_: self.show_file_ref())
        v.addWidget(self.table)
        TABS.RowDrag(self.table, self.move_row)
        STYLE.hide_when_empty(self.table)
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
        self.lbl_fref_info = STYLE.HintLabel("")
        self.lbl_fref_info.setWordWrap(True)
        self.lbl_fref_info.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_fref_info)
        self.lv.addWidget(self.det)
        for w_ in (self.sp_fref_lo, self.sp_fref_hi, self.sp_fref_value, self.sp_foffset):
            w_.valueChanged.connect(self.file_ref_changed)
        for w_ in (self.cmb_fref, self.cmb_fref_file):
            w_.currentIndexChanged.connect(self.file_ref_changed)
        self.cmb_fcompound.currentIndexChanged.connect(self.fcompound_changed)

        # Angaben zur Messung, die ACS/Angew. zum Voltammogramm verlangen und die nicht in der Gamry-Datei stehen
        # (Start, Richtung, Vorschub und iR-Kompensation liest der Tab aus der Datei); einmal eingegeben, gemerkt für neue
        # Verbindungen (nur solange der Tab noch keine Messung hat: alte Projekte bekommen nie still fremde Angaben)
        g = QGroupBox(T("cv_acs_group"))
        f = make_form(g)
        self.ed_acs = {}
        for key in ACS_FIELDS:
            if not st.get(key) and not st["files"]:
                st[key] = str(self.main.settings.value(f"cv_acs/{key}", "") or "")
            ed = STYLE.ChemEdit(st.get(key, ""))
            lk = ("fixt_cv_" if key == "acs_ref" else "cv_") + key          # Referenzelektrode im Aufbau (1.2.0)
            ed.setPlaceholderText(T(lk + "_ph"))
            ed.editingFinished.connect(self.acs_edited)
            f.addRow(T(lk), ed)
            self.ed_acs[key] = ed
        # In einem Projekt steht der Messaufbau einmal in den Projektangaben (Anfangstext des Kapitels der Gesamt-SI):
        # hier nur der Verweis und der Text, wie er dort gebildet wird; die Felder gelten nur ohne Projekt
        self.lbl_acs_pub = STYLE.HintLabel("")
        self.lbl_acs_pub.setStyleSheet(HINT_CSS)
        self.lbl_acs_pub.setWordWrap(True)
        f.addRow(self.lbl_acs_pub)
        self.lbl_acs_text = STYLE.SiText("")              # der Text selbst: linksbündig, normale Farbe, Formeln gesetzt
        holder = QWidget()                                 # eigener Rahmen: tidy setzt Hinweise sonst mittig unter die
        hl = QVBoxLayout(holder)                           # Wertespalte (wie die Bildunterschrift im Reiter SI-Text)
        hl.setContentsMargins(0, 2, 0, 2)
        hl.addWidget(self.lbl_acs_text)
        f.addRow(holder)
        if self.project_setup() is not None:
            for ed in self.ed_acs.values():
                f.setRowVisible(ed, False)
        self.lbl_acs_file = STYLE.HintLabel("")
        self.lbl_acs_file.setStyleSheet(HINT_CSS)
        self.lbl_acs_file.setWordWrap(True)
        f.addRow(self.lbl_acs_file)
        self.lbl_acs_missing = STYLE.HintLabel("")
        self.lbl_acs_missing.setStyleSheet(STYLE.WARN_CSS)
        self.lbl_acs_missing.setWordWrap(True)
        f.addRow(self.lbl_acs_missing)
        self.lv.addWidget(g)

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
        row = QHBoxLayout()                                  # Knopfreihe über der Liste wie in allen Tabs (Sichtung)
        for txt, fn, tip in ((T("cv_couple_add"), self.add_couple, ""), (T("remove"), self.remove_couple, ""),
                             (T("cv_suggest"), self.suggest, T("cv_suggest_tip"))):
            b = STYLE.list_button(txt)
            if fn == self.add_couple:
                b.setIcon(STYLE.icon("add"))
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        f.addRow(QLabel(T("cv_couples")))
        f.addRow(row)
        f.addRow(self.tbl_couples)
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
        self.lbl_ref_dash = QLabel("–")                    # eigener Name: verschwindet mit der Zeile (stand sonst allein da)
        for w_ in (self.sp_ref_lo, self.lbl_ref_dash, self.sp_ref_hi):
            row.addWidget(w_)
        self.lbl_ref_win = QLabel(T("cv_ref_window"))
        f.addRow(self.lbl_ref_win, row)
        # Referenz per Klick: Oxidations- und Reduktionspeak des Standards in der Vorschau anklicken (Esc bricht ab)
        self.btn_ref_pick = QPushButton(T("cv_ref_pick"))
        self.btn_ref_pick.setCheckable(True)
        self.btn_ref_pick.setToolTip(T("cv_ref_pick_tip"))
        self.btn_ref_pick.toggled.connect(self.toggle_ref_pick)
        row = QHBoxLayout()                                 # Knopfreihe in der Wertespalte (lag sonst lose am linken Rand)
        row.addWidget(self.btn_ref_pick)
        f.addRow("", row)
        self._pick, self._pick_cid = None, None
        self._esc = QShortcut(QKeySequence(Qt.Key_Escape), self, context=Qt.WindowShortcut)
        self._esc.setEnabled(False)                        # nur im Klickmodus (kein Konflikt mit anderen Tabs)
        self._esc.activated.connect(self.cancel_ref_pick)
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
        # ab hier eigene Klappkarte „Diffusion und k⁰“ (arrange): Angaben für D aus der Randles–Ševčík-Steigung
        self.sp_rs_n = QSpinBox(minimum=1, maximum=6, value=st["rs_n"])
        self.sp_rs_area = QDoubleSpinBox(decimals=4, minimum=0, maximum=100, singleStep=0.01, value=st["rs_area"],
                                         suffix=" cm²")
        self.sp_rs_conc = QDoubleSpinBox(decimals=3, minimum=0, maximum=1000, singleStep=0.1, value=st["rs_conc"],
                                         suffix=" mM")
        for sp_ in (self.sp_rs_area, self.sp_rs_conc):     # nichts vorbelegen: ohne Angabe kein D
            sp_.setSpecialValueText(T("off"))
        self.sp_rs_area.setToolTip(T("cv_rs_area_tip"))
        self.sp_rs_temp = QDoubleSpinBox(decimals=1, minimum=-100, maximum=200, singleStep=1, value=st["rs_temp"],
                                         suffix=" °C")
        f.addRow(T("cv_rs_n"), self.sp_rs_n)
        f.addRow(T("cv_rs_area"), self.sp_rs_area)
        f.addRow(T("cv_rs_conc"), self.sp_rs_conc)
        f.addRow(T("cv_rs_temp"), self.sp_rs_temp)
        # k⁰ aus ΔE_p: D eingegeben (sonst aus Randles–Ševčík des Paars) und α nur für Klingler–Kochi – nie vorbelegt
        from elucida.app.main_window import TrimSpin       # hier: main_window importiert die Tabs
        self.sp_k0_D = TrimSpin(decimals=3, minimum=0, maximum=1000, singleStep=0.1,      # „10 × 10⁻⁶“, nicht „10.000“
                                value=st.get("k0_D", 0.0) * 1e6, suffix=" × 10⁻⁶ cm² s⁻¹")
        self.sp_k0_D.setSpecialValueText(T("cv_k0_D_rs"))
        self.sp_k0_D.setToolTip(T("cv_k0_D_tip"))
        self.sp_k0_alpha = QDoubleSpinBox(decimals=2, minimum=0, maximum=0.95, singleStep=0.05,
                                          value=st.get("k0_alpha", 0.0))
        self.sp_k0_alpha.setSpecialValueText(T("off"))
        self.sp_k0_alpha.setToolTip(T("cv_k0_alpha_tip"))
        f.addRow(T("cv_k0_D"), self.sp_k0_D)
        f.addRow(T("cv_k0_alpha"), self.sp_k0_alpha)
        self.lbl_rs_hint = STYLE.HintLabel(T("cv_rs_hint"))
        self.lbl_rs_hint.setStyleSheet(STYLE.HINT_CSS)
        self.lbl_rs_hint.setWordWrap(True)
        f.addRow(self.lbl_rs_hint)
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
        for sp_ in (self.sp_rs_n, self.sp_rs_area, self.sp_rs_conc, self.sp_rs_temp, self.sp_k0_D, self.sp_k0_alpha):
            sp_.valueChanged.connect(self.changed)
        self.sp_gap.valueChanged.connect(self.changed)
        for cb in (self.cb_stack, self.cb_e12_each):
            cb.toggled.connect(self.changed)
        self.cb_gradient = QCheckBox(T("cv_gradient"))
        self.cb_density = QCheckBox(T("cv_density"))
        self.cb_e12 = QCheckBox(T("cv_show_e12"))
        self.cb_arrow = QCheckBox(T("cv_arrow"))
        self.cb_ref_marker = QCheckBox(T("cv_ref_marker"))
        self.cb_ref_marker.setToolTip(T("cv_ref_marker_long"))
        self.cb_ref_color = QCheckBox(T("cv_ref_color"))       # schwarz (Vorgabe) oder Farbe der Referenzmessung
        self.cb_ref_color.setToolTip(T("cv_ref_color_tip"))
        self.cb_invert = QCheckBox(T("cv_invert"))
        self.cb_invert.setToolTip(T("cv_invert_tip"))
        for cb, key in ((self.cb_gradient, "gradient"), (self.cb_density, "density"), (self.cb_e12, "show_e12"),
                        (self.cb_arrow, "arrow"), (self.cb_ref_marker, "ref_marker"), (self.cb_ref_color, "ref_color"),
                        (self.cb_invert, "invert")):
            cb.setChecked(st[key])
            f.addRow(cb)
            cb.toggled.connect(self.changed)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_results"))
        v = QVBoxLayout(g)
        self.tbl_res = STYLE.FitGrid(0, 9)                # über die ganze Seite wie die Tabelle darunter
        STYLE.empty_note(self.tbl_res, T("results_none"))
        self.tbl_res.setHorizontalHeaderLabels(
            [T("ov_name"), "#", "E_pa [V]", "E_pc [V]", "E½ [V]", "ΔE_p [mV]", "i_pa [µA]", "i_pc [µA]", "i_r/i_f"])
        self.tbl_res.horizontalHeaderItem(8).setToolTip(T("cv_ratio_tip"))
        self.tbl_res.setItemDelegateForColumn(0, STYLE.RichDelegate(self.tbl_res, core.unit_html))
        self.tbl_res.elide_col = 0                       # Name gibt nach, bevor die Tabelle quer rollt (1200 px)
        self.tbl_res.verticalHeader().setVisible(False)
        self.tbl_res.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_res.setMinimumHeight(140)
        v.addWidget(self.tbl_res)
        # Scanraten-Analyse als zweite Tabelle, Referenz und Warnungen als eigene Zeilen (vorher eine Textwand unter der
        # Tabelle, Nutzerhinweis 2026-11-13)
        self.lbl_fit = QLabel(T("cv_fit_title"))
        self.lbl_fit.setProperty("formlabel", True)
        self.lbl_fit.setWordWrap(True)
        v.addWidget(self.lbl_fit)
        self.tbl_fit = STYLE.summary_grid([T("cv_fit_couple"), T("cv_fit_peak"), "N", T("cv_fit_slope"),
                                           T("cv_fit_icpt"), "R²", T("cv_fit_ll")], rich=(1,))
        self.tbl_fit.horizontalHeaderItem(2).setToolTip(T("cv_fit_n"))
        self.tbl_fit.horizontalHeaderItem(4).setToolTip(T("cv_fit_icpt_tip"))
        v.addWidget(self.tbl_fit)
        # D und k⁰ je Paar als eigene kleine Tabelle (vorher zwei Spalten der Regressionstabelle: sie rollte schon bei
        # 1500 px quer); Bewertung kurz, Gründe vollständig im Tooltip der Zelle
        self.lbl_dk = QLabel(T("cv_dk_title"))
        self.lbl_dk.setProperty("formlabel", True)
        v.addWidget(self.lbl_dk)
        self.tbl_dk = STYLE.summary_grid([T("cv_fit_couple"), "D [cm² s⁻¹]", "k⁰ [cm s⁻¹]", T("cv_dk_status")],
                                         rich=(1, 2))
        self.tbl_dk.elide_col = 3
        self.tbl_dk.horizontalHeaderItem(1).setToolTip(T("cv_fit_D_tip"))
        self.tbl_dk.horizontalHeaderItem(2).setToolTip(T("cv_fit_k0_tip"))
        v.addWidget(self.tbl_dk)
        self.lbl_res = STYLE.SciLabel("")                 # Referenz
        self.lbl_res.setWordWrap(True)
        self.lbl_res.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_res)                        # „SI-Text kopieren“ steht im Reiter SI-Text
        # Warnungen: eine kurze Zeile je Art mit Anzahl, Einzelheiten im Tooltip (vorher eine rote Textwand)
        self.warn_lbls = {}
        for key in self.WARN_KINDS:
            lb_ = STYLE.SciLabel("")
            lb_.setStyleSheet(STYLE.WARN_CSS)
            lb_.setWordWrap(True)
            lb_.hide()
            v.addWidget(lb_)
            self.warn_lbls[key] = lb_
        self.lv.addWidget(g)

        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export

        self.sp_cycle.valueChanged.connect(self.changed)
        for w_ in (self.sp_ref_lo, self.sp_ref_hi, self.sp_ref_value, self.sp_offset):
            w_.valueChanged.connect(self.changed)
        self.cmb_ref.currentIndexChanged.connect(self.changed)
        self.cmb_ref_file.currentIndexChanged.connect(self.changed)
        self.cmb_compound.currentIndexChanged.connect(self.ref_compound_changed)
        self.ed_electrode.editingFinished.connect(self.changed)
        self.fill_table()
        self.fill_couples()
        self._sync_ref_widgets()

    CAP_TITLES = {"cv": "Cyclic voltammograms", "dep": "Reversibility plot", "rs": "Randles–Ševčík plot",
                  "rs_v": "Peak current vs. scan rate",
                  "loglog": "Double-logarithmic plot of peak current vs. scan rate",
                  "ratio": "Peak current ratio vs. scan rate", "trumpet": "Trumpet plot"}
    CAP_REFS = {"ac2fc": "diacetylferrocene", "fc": "ferrocene"}

    def pulse_kinds(self, entries):
        """Verfahren der Messungen: {None} = nur CV, sonst „DPV“/„SWV“/„pulse“ (auch gemischt)."""
        out = set()
        for e in entries:
            try:
                out.add(self.data(e["file"])["meta"].get("pulse"))
            except Exception:
                pass
        return out

    def caption_box(self):
        """Bildunterschrift: zusätzlich der Schalter „Start und Richtung“ (Vorgabe aus: der Pfeil im Bild zeigt sie)."""
        g = super().caption_box()
        f = g.layout()
        r, _ = f.getWidgetPosition(self.lbl_cap)
        self.cb_cap_start = QCheckBox(T("cv_cap_start"))
        self.cb_cap_start.setToolTip(T("cv_cap_start_long"))
        self.cb_cap_start.setChecked(bool(self.st.get("cap_start")))
        f.insertRow(r, self.cb_cap_start)

        def set_(*_):
            self.st["cap_start"] = self.cb_cap_start.isChecked()
            self.show_caption()
            self.timer.start()
        self.cb_cap_start.toggled.connect(set_)
        return g

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
        title = self.CAP_TITLES.get(plot, "Cyclic voltammograms")
        kinds = self.pulse_kinds(vis)                    # Pulsverfahren (DPV, Square-Wave): eigener Titel
        if plot == "cv" and kinds - {None}:
            from elucida.formats.gamry import PULSE_NAMES
            title = PULSE_NAMES[next(iter(kinds))] if len(kinds) == 1 else "Voltammograms"
        h = f"{title} of <b>{html.escape(name)}</b>"
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        groups = sorted({e.get("group", "").strip() for e in vis} - {""})
        solv = st.get("cap_solvent") or (groups[0] if len(groups) == 1 else "different solvents" if groups else "")
        if solv:
            h += " in " + chem_html(solv)
        if st.get("cap_el"):
            h += f" ({chem_html(st['cap_el'])})"
        h += " at " + chem_html(st.get("cap_temp") or "rt")
        # Elektroden, Gerät, Atmosphäre und Politur stehen nicht in jeder Unterschrift (Nutzerentscheidung 2026-11-13):
        # sie gehören gesammelt in den Anfangstext (Projekt: Kapiteltext der Gesamt-SI, sonst Methodentext)
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
            pp = pulse_params(metas)
            if pp:
                h += "; " + pp
            ir = {m.get("pfcor") if m.get("ircomp_on") and m.get("posfeed") else None for m in metas}
            states = {m.get("ircomp_on") for m in metas}
            # Steht etwas schon im Kapitelabsatz des Projekts (iR-Kompensation, Konvention), nennt die Unterschrift es
            # nur, wenn diese Messung davon abweicht (Nutzerentscheidung 2026-11-13: kurze Unterschriften)
            pub = self.project_setup() or {}
            if pub.get("ir"):
                if False in states:
                    h += " (without iR compensation)"
            elif len(ir) == 1 and None not in ir:
                h += f" (iR compensation = {next(iter(ir)):g} Ohm)"
            elif states == {True}:
                h += " (with iR compensation)"
            elif states == {False}:
                h += " (without iR compensation)"
            sf = self.scan_facts()
            if st.get("cap_start") and sf["start"] and sf["direction"]:   # die Abbildung zeigt die Richtung als Pfeil
                lab = str(sf["start"][1]).replace("Fc$^{0/+}$", "Fc<sup>0/+</sup>")
                h += (f"; scans started at {_fmt_e(sf['start'][0], 2)} V vs. {chem_html(lab) if '<' not in lab else lab}"
                      f" in the {'positive' if sf['direction'] > 0 else 'negative'} direction")
            # Konvention nur, wenn das Projekt eine nennt und die Darstellung abweicht, oder die Darstellung von der
            # Aufnahme abweicht (umgekehrt); alte Verbindungen ohne Angabe bleiben wie in 1.1.0
            conv = self.shown_convention(metas)
            if conv and ((pub.get("conv") and pub["conv"] != conv) or (not pub.get("conv") and st.get("invert"))):
                h += "; " + CONVENTIONS[conv]
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
                        e12 = (f" (E<sub>1/2</sub> = {_fmt_e(vals[0], 2)}" + f" V vs. {fc})" if len(vals) == 1 else "")
                        parts.append(self.CAP_REFS[k] + e12)
                h += f"; potentials referenced against {fc} using " + " or ".join(parts) + " as internal standard"
            if st.get("arrow"):
                h += " (arrows indicate scanning direction)"
        return h + "."

    def shown_convention(self, metas):
        """Konvention der Darstellung: Gamry zeichnet anodisch positiv auf (CONVENTION 1 in allen geprüften Dateien,
        ohne Angabe ebenso angenommen), `invert` kehrt um. Anderer Wert in einer Datei -> None (nicht belegt)."""
        if {m.get("convention") for m in metas} - {None, 1}:
            return None
        return "polar" if self.st.get("invert") else "iupac"

    def _sync_ref_widgets(self):
        mode = self.st["ref_mode"]
        for w_ in (self.lbl_ref_file, self.cmb_ref_file, self.lbl_ref_win, self.sp_ref_lo, self.lbl_ref_dash,
                   self.sp_ref_hi, self.lbl_compound, self.cmb_compound, self.sp_ref_value):
            w_.setVisible(mode == "internal")
        for w_ in (self.lbl_offset, self.sp_offset):
            w_.setVisible(mode == "manual")
        self.btn_ref_pick.setVisible(mode != "manual")

    def ref_compound_changed(self, *_):
        key = self.cmb_compound.currentData()
        if key in REFERENCES and not self._loading:
            self.sp_ref_value.blockSignals(True)
            self.sp_ref_value.setValue(REFERENCES[key][1])
            self.sp_ref_value.blockSignals(False)
        self.changed()

    def acs_edited(self):
        for key, ed in self.ed_acs.items():
            v = ed.text().strip()
            if v:                                         # für neue Verbindungen merken
                self.main.settings.setValue(f"cv_acs/{key}", v)
        self.changed()

    def scan_facts(self):
        """Aus den sichtbaren Gamry-Dateien: Startpotential (Achsenskala, auf 0.01 V), Richtung, iR-Kompensation.
        -> dict(start=(E, Referenz) oder None, direction=±1 oder None, ir=Menge der Zustände True/False/None)."""
        starts, dirs, ir, conv = set(), set(), set(), set()
        for e in [e for e in self.st["files"] if e["visible"]]:
            try:
                d = self.data(e["file"])
            except Exception:
                continue
            conv.add(d["meta"].get("convention"))
            ir.add(d["meta"].get("ircomp_on"))
            ss = scan_start(d["cycles"][0]["E"]) if d["cycles"] else None
            if ss is None:                                # leere Kurve: keine Angabe, Hinweise bleiben
                continue
            e0, s = ss
            off, lab, _ = self.file_offset(e)
            starts.add((round(e0 - off, 2) + 0.0, lab))
            dirs.add(s)
        return dict(start=next(iter(starts)) if len(starts) == 1 else None,
                    direction=next(iter(dirs)) if len(dirs) == 1 else None, ir=ir, n=len(dirs), conv=conv)

    def acs_missing(self):
        """Angaben, die die Richtlinien (ACS, Angew.) zum Voltammogramm oder in der SI verlangen und die noch fehlen."""
        st = self.st
        groups = {e.get("group", "").strip() for e in st["files"] if e["visible"]} - {""}
        v = self.setup_effective()
        have = dict(solvent=st.get("cap_solvent") or len(groups) == 1, el=st.get("cap_el"), conc=st.get("cap_conc"),
                    we=v.get("we"), ce=v.get("ce"), ref=v.get("ref"), gas=v.get("gas"), device=v.get("device"),
                    area=v.get("area"), polish=v.get("polish"))
        return [k for k, v in have.items() if not v]

    def update_acs_hint(self):
        f = self.scan_facts()
        parts = []
        if f["start"]:
            parts.append(T("cv_acs_start", E=_fmt_e(f["start"][0], 2), ref=self.ref_text(f["start"][1])))
        if f["direction"]:
            parts.append(T("cv_acs_dir_pos" if f["direction"] > 0 else "cv_acs_dir_neg"))
        if f["n"] and f["ir"] <= {True, False}:
            parts.append(T("cv_acs_ir_on" if f["ir"] == {True} else "cv_acs_ir_off" if f["ir"] == {False}
                           else "cv_acs_ir_mixed"))
        self.lbl_acs_file.setText(T("cv_acs_from_file", items=", ".join(parts)) if parts else "")
        miss = self.acs_missing() if self.st["files"] else []
        lines = [T("cv_acs_missing", items=", ".join(T("cv_acs_n_" + k) for k in miss))] if miss else []
        pub = self.project_setup()
        if pub is not None:
            from elucida.si.lines import chem_plain
            txt = setup_text(self.setup_effective())
            self.lbl_acs_pub.setText(T("cv_acs_in_project") if txt else T("cv_acs_in_project_none"))
            self.lbl_acs_text.setText(chem_plain(txt) if txt else "")
            self.lbl_acs_text.setVisible(bool(txt))
            if pub.get("ir") and False in f["ir"]:        # Sammeltext nennt iR-Kompensation, diese Messung hat keine
                lines.append(T("cv_acs_ir_differs"))
        else:
            self.lbl_acs_pub.setText("")
            self.lbl_acs_text.setText("")
            self.lbl_acs_text.setVisible(False)
        if f["conv"] - {None, 1}:                         # Stromkonvention der Datei nicht anodisch positiv: prüfen
            lines.append(T("fixt_cv_conv_file", v=", ".join(str(c) for c in sorted(f["conv"] - {None, 1}))))
        self.lbl_acs_missing.setText("\n".join(lines))

    @staticmethod
    def ref_text(lab):
        return str(lab).replace("Fc$^{0/+}$", "Fc⁰/⁺")

    def collect(self):
        st = self.st
        st.update({k: ed.text().strip() for k, ed in self.ed_acs.items()})
        st.update(cycle=self.sp_cycle.value(), ref_mode=self.cmb_ref.currentData(),
                  ref_uid=self.cmb_ref_file.currentData(), ref_lo=self.sp_ref_lo.value(),
                  ref_hi=self.sp_ref_hi.value(), ref_compound=self.cmb_compound.currentData(),
                  ref_value=self.sp_ref_value.value(), ref_offset=self.sp_offset.value(),
                  ref_electrode=self.ed_electrode.text().strip() or "Ag/AgNO₃",
                  gradient=self.cb_gradient.isChecked(), density=self.cb_density.isChecked(),
                  show_e12=self.cb_e12.isChecked(), arrow=self.cb_arrow.isChecked(),
                  ref_marker=self.cb_ref_marker.isChecked(), ref_color=self.cb_ref_color.isChecked(),
                  invert=self.cb_invert.isChecked(), plot=self.cmb_plot.currentData(),
                  stack=self.cb_stack.isChecked(), stack_gap=self.sp_gap.value(),
                  e12_each=self.cb_e12_each.isChecked(), y_axis=self.cmb_yaxis.currentData(),
                  peak_labels=self.cmb_peaklab.currentData(), baseline=self.cb_baseline.isChecked(),
                  bl_gap=self.sp_bl_gap.value(), show_bl=self.cb_show_bl.isChecked(),
                  rs_n=self.sp_rs_n.value(), rs_area=self.sp_rs_area.value(), rs_conc=self.sp_rs_conc.value(),
                  rs_temp=self.sp_rs_temp.value(), k0_D=self.sp_k0_D.value() * 1e-6, k0_alpha=self.sp_k0_alpha.value())
        self._sync_ref_widgets()

    # -- Dateien -------------------------------------------------------------------
    def data(self, path):
        return self.cache(("cv", path), lambda: read_gamry(path))

    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("cv_add"), self.main.settings.value("last_dir", ""),
                                             "Gamry (*.DTA *.dta);;" + T("flt_all"))
        self.load_files(ps)

    def load_files(self, ps):
        """Gamry-Dateien übernehmen (auch beim Ablegen); Unlesbares wird gemeldet."""
        for p in ps:
            try:
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                d = self.data(p)
            except Exception as e:
                self.main.error(str(e))
                continue
            rate = d["meta"]["scanrate"]
            self.st["files"].append({"file": p, "uid": uuid.uuid4().hex[:8], "visible": True, "color": "#000000",
                                     "label": f"{round(rate, 1):g} mV s-1" if rate else Path(p).stem})
        if ps and not self.st["couples"]:
            self.suggest()
        self.fill_table()
        self.timer.start()

    def move(self, d):
        self.move_row(self.table.currentRow(), self.table.currentRow() + d)

    def move_row(self, src, dst):
        if TABS.move_item(self.st["files"], src, dst):
            self.fill_table()
            self.table.selectRow(dst)
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
        refs = self.ref_uids()
        self.table.setRowCount(len(fs))
        for i, e in enumerate(fs):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(e["color"], lambda c, e=e: self._set_color(e, c),
                                                              cell=True))
            try:
                rate = self.data(e["file"])["meta"]["scanrate"]
            except Exception:
                rate = None
            it = QTableWidgetItem(f"{round(rate, 1):g}" if rate else "–")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, it)
            self.table.setItem(i, 4, QTableWidgetItem(e.get("group", "")))
            it = QTableWidgetItem()                          # enthält den internen Standard (Referenz der Reihe)
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["uid"] in refs else Qt.Unchecked)
            self.table.setItem(i, 5, it)
        # Kopf = Kurzname des Standards (Fc, Ac₂Fc); verschiedene oder eigener Standard: „Ref.“
        comp = {(x.get("ref") or {}).get("compound") for x in fs if (x.get("ref") or {}).get("mode") == "internal"}
        comp |= {self.st.get("ref_compound")} if self.st.get("ref_mode") == "internal" or not comp else set()
        key = next(iter(comp)) if len(comp) == 1 else None
        self.table.horizontalHeaderItem(5).setText(REFERENCES[key][0] if key in REFERENCES else T("cv_ref_col"))
        STYLE.fit_columns(self.table)
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
            b.setStyleSheet(f"{b.property('cellcss') or ''}background-color: {col}; border: 1px solid {STYLE.swatch_border()};")

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
        elif item.column() == 5:
            return self.set_ref_run(e, item.checkState() == Qt.Checked)
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

    # -- Referenzmessung (Häkchen in der Liste) und Referenz per Klick (Entscheidung 171) -------------------------
    def ref_uids(self):
        """Messungen, die als interner Standard dienen (global oder je Messung/Reihe)."""
        st = self.st
        out = {st.get("ref_uid")} if st.get("ref_mode") == "internal" else set()
        out |= {(e.get("ref") or {}).get("uid") for e in st["files"] if (e.get("ref") or {}).get("mode") == "internal"}
        return out - {None}

    def ref_only_uids(self):
        """Messungen, die **anderen** Messungen als interner Standard dienen (reiner Fc-Lauf oder Fc am Ende zugegeben,
        Entscheidung 177): nur Referenz, nicht in der Scanraten-Analyse. Eine Messung, die nur sich selbst referenziert
        (Standard in jeder Lösung, z. B. „mit Ac₂Fc“), bleibt eine Messung der Reihe."""
        st, users = self.st, {}
        for e in st["files"]:
            ref = e.get("ref") or {}
            uid = ref.get("uid") if ref.get("mode") == "internal" else \
                st.get("ref_uid") if not ref.get("mode") and st["ref_mode"] == "internal" else None
            if uid:
                users.setdefault(uid, set()).add(e["uid"])
        return {u for u, us in users.items() if us - {u}}

    def sync_ref_controls(self):
        """Felder der Karte Referenz aus dem Zustand (ohne Signale): `collect` liest sie sonst zurück."""
        st = self.st
        for w_, val in ((self.cmb_ref, st["ref_mode"]), (self.cmb_ref_file, st.get("ref_uid")),
                        (self.cmb_compound, st["ref_compound"])):
            w_.blockSignals(True)
            w_.setCurrentIndex(max(0, w_.findData(val)))
            w_.blockSignals(False)
        for w_, val in ((self.sp_ref_lo, st["ref_lo"]), (self.sp_ref_hi, st["ref_hi"]),
                        (self.sp_ref_value, st["ref_value"])):
            w_.blockSignals(True)
            w_.setValue(val)
            w_.blockSignals(False)
        self._sync_ref_widgets()

    def set_ref_run(self, x, on):
        """Häkchen „enthält den Standard“: eine Messung je Reihe (Gruppe). Ohne verschiedene Gruppen die globale
        Referenz, sonst die Referenz je Messung aller Messungen dieser Gruppe; Standard und E° bleiben."""
        st, fs = self.st, self.st["files"]
        internal = lambda f: (f.get("ref") or {}).get("mode") == "internal"          # noqa: E731
        if on and len({f.get("group", "") for f in fs}) <= 1:
            for f in fs:
                if internal(f):
                    f["ref"] = None
            st.update(ref_mode="internal", ref_uid=x["uid"])
        elif on:
            for f in (f for f in fs if f.get("group", "") == x.get("group", "")):
                old = f["ref"] if internal(f) else {}
                same = old.get("uid") == x["uid"]
                f["ref"] = {"mode": "internal", "uid": x["uid"], "lo": old["lo"] if same else st["ref_lo"],
                            "hi": old["hi"] if same else st["ref_hi"], "compound": old.get("compound", st["ref_compound"]),
                            "value": old.get("value", st["ref_value"])}
        else:
            if st["ref_mode"] == "internal" and st.get("ref_uid") == x["uid"]:
                st["ref_mode"] = "none"
            for f in fs:
                if internal(f) and f["ref"].get("uid") == x["uid"]:
                    f["ref"] = None
        self.fill_table()
        self.sync_ref_controls()
        self.timer.start()

    def ref_target(self):
        """Referenzmessung für „Referenz setzen“: die der gewählten Zeile (eigene Referenz oder global), sonst die
        globale, sonst die erste angehakte -> uid oder None."""
        e, st = self.current_file(), self.st
        ref = (e or {}).get("ref") or {}
        if ref.get("mode") == "internal":
            return ref.get("uid")
        if st["ref_mode"] == "internal" and st.get("ref_uid"):
            return st["ref_uid"]
        return next(iter(sorted(self.ref_uids())), None)

    def toggle_ref_pick(self, on):
        if not on:
            return self.cancel_ref_pick()
        uid = self.ref_target()
        e = next((x for x in self.st["files"] if x["uid"] == uid), None)
        why = ("cv_ref_pick_none" if e is None else "cv_ref_pick_hidden" if not e["visible"] else
               "cv_ref_pick_plot" if self.st["plot"] != "cv" or self.F is None else None)
        if why:
            self.btn_ref_pick.blockSignals(True)
            self.btn_ref_pick.setChecked(False)
            self.btn_ref_pick.blockSignals(False)
            return self.main.notify(T(why), ms=8000)
        self._pick = {"uid": uid}
        self._pick_cid = self.canvas.mpl_connect("button_press_event", self.ref_clicked)
        self._esc.setEnabled(True)
        self.main.notify(T("cv_ref_pick_hint", name=e["label"]), links=[(T("cancel"), self.cancel_ref_pick)], ms=0)

    def cancel_ref_pick(self):
        if self._pick_cid is not None:
            self.canvas.mpl_disconnect(self._pick_cid)
        self._pick, self._pick_cid = None, None
        self._esc.setEnabled(False)
        self.btn_ref_pick.blockSignals(True)
        self.btn_ref_pick.setChecked(False)
        self.btn_ref_pick.blockSignals(False)

    def snap_ref_peak(self, uid, x_axis, y_axis=None):
        """Klick (Achsenkoordinaten der Vorschau) -> ("a"|"c", E_p gemessen) oder None: höchster Strom im Hinlauf bzw.
        tiefster im Rücklauf in ±REF_SNAP V um die Klickstelle (dieselben Läufe wie `analyze_couple`), Lage per Parabel
        (`_refine`). Liegt das Extremum am Rand des Suchbereichs, ist dort kein Peak. Von beiden gilt der in der Vorschau
        nähere (Pixelabstand zum Klick)."""
        curve = next((c for c in (self.F.curves if self.F else []) if c.get("uid") == uid and not c.get("aux")), None)
        e = next((x for x in self.st["files"] if x["uid"] == uid), None)
        if curve is None or e is None:
            return None
        c = self.cycle_of(e)
        E, I = np.asarray(c["E"], float), np.asarray(c["I"], float)
        em = x_axis + curve["_off_e"]                     # Achse = gemessen − Offset dieser Messung
        dE = np.gradient(E)
        near = np.abs(E - em) <= REF_SNAP
        hits = []
        for kind, mask, pick in (("a", near & (dE > 0), np.argmax), ("c", near & (dE < 0), np.argmin)):
            idx = np.flatnonzero(mask)
            if len(idx) < 5:
                continue
            k = int(idx[pick(I[idx])])
            # Extremum am Rand des Suchbereichs oder am Ende des Laufs (Umkehrpunkt): Flanke, kein Peak
            if abs(E[k] - em) >= REF_SNAP - 0.004 or k in (idx[0], idx[-1]) or not (mask[k - 1] and mask[k + 1]):
                continue
            d = 0.0
            if y_axis is not None:
                px = self.F.ax.transData.transform([(curve["x"][k], curve["y"][k]), (x_axis, y_axis)])
                d = float(np.hypot(*(px[0] - px[1])))
            hits.append((d, kind, _refine(E, I, k)[0]))
        return min(hits)[1:] if hits else None

    def ref_window(self, uid, epa, epc):
        """Fenster (gemessene Potentiale, 2 Stellen wie die Felder), in dem `analyze_couple` genau diese Peaks findet
        -> (lo, hi) oder None."""
        e = next((x for x in self.st["files"] if x["uid"] == uid), None)
        c = self.cycle_of(e)
        for pad in REF_PADS:
            lo, hi = np.floor((epc - pad) * 100) / 100, np.ceil((epa + pad) * 100) / 100
            r = analyze_couple(c["E"], c["I"], lo, hi)
            if r is not None and not r["invalid"] and abs(r["epa"] - epa) < 0.002 and abs(r["epc"] - epc) < 0.002:
                return float(lo), float(hi)
        return None

    def ref_clicked(self, ev):
        if self._pick is None or self.F is None or ev.inaxes is not self.F.ax or ev.button != 1 or ev.xdata is None:
            return
        hit = self.snap_ref_peak(self._pick["uid"], float(ev.xdata), float(ev.ydata))
        if hit is None:
            return self.main.notify(T("cv_ref_pick_nopeak"), ms=8000)
        self._pick[hit[0]] = hit[1]
        if not ("a" in self._pick and "c" in self._pick):
            return self.main.notify(T("cv_ref_pick_next", e=_fmt_e(hit[1]), which=T("cv_ref_pick_" + hit[0])),
                                    links=[(T("cancel"), self.cancel_ref_pick)], ms=0)
        self.apply_ref_pick(self._pick["uid"], self._pick["a"], self._pick["c"])

    def apply_ref_pick(self, uid, epa, epc):
        """Beide Peaks gewählt: Fenster speichern wie ein eingegebenes (Referenz je Messung oder global); E½ rechnet
        danach `analyze_couple` wie immer. Ein Rückgängig-Schritt (ein Zeichnen)."""
        self.cancel_ref_pick()
        win = self.ref_window(uid, epa, epc) if epa > epc else None
        if win is None:
            return self.main.notify(T("cv_ref_pick_fail"), ms=8000)
        st, hit = self.st, False
        for f in st["files"]:
            ref = f.get("ref") or {}
            if ref.get("mode") == "internal" and ref.get("uid") == uid:
                ref["lo"], ref["hi"] = win
                hit = True
        if not hit or (st["ref_mode"] == "internal" and st.get("ref_uid") == uid):
            st.update(ref_mode="internal", ref_uid=uid, ref_lo=win[0], ref_hi=win[1])
        self.sync_ref_controls()
        self.fill_table()
        self.main.notify(T("cv_ref_pick_done", e12=_fmt_e((epa + epc) / 2), dep=f"{(epa - epc) * 1000:.0f}"), ms=8000)
        self.timer.start()

    def ref_marks(self, always=False):
        """Interner Standard im Bild (Chip „Struktur des Standards“, Schlüssel `ref_marker` wie früher der Stern):
        [(uid, Ergebnis von analyze_couple, Standard)] der
        sichtbaren Referenzmessungen, deren Fenster ein gültiges Paar ergibt; nur in der CV-Ansicht."""
        st = self.st
        if not always and (st.get("plot", "cv") != "cv" or not st.get("ref_marker", True)):   # always: Vergleich
            return []
        wins = {}
        if st["ref_mode"] == "internal":
            wins[st.get("ref_uid")] = (st["ref_lo"], st["ref_hi"], st["ref_compound"])
        for e in st["files"]:
            ref = e.get("ref") or {}
            if ref.get("mode") == "internal" and e["visible"]:
                wins.setdefault(ref.get("uid"), (ref.get("lo", 0.3), ref.get("hi", 0.8), ref.get("compound")))
        out = []
        for e in st["files"]:
            if e["uid"] in wins and e["visible"]:
                lo, hi, comp = wins[e["uid"]]
                try:
                    c = self.cycle_of(e)
                except Exception:
                    continue
                r = analyze_couple(c["E"], c["I"], lo, hi)
                if r is not None and not r["invalid"]:
                    out.append((e["uid"], r, comp))
        return out

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
                    note += _flag_note(r)
                    return r["e12"] - st["ref_value"], "Fc$^{0/+}$", note
            return 0.0, st["ref_electrode"], T("cv_ref_missing")
        return 0.0, st["ref_electrode"], ""

    def file_offset(self, e):
        """Offset dieser Messung (eigene Referenz oder global) -> (Offset, Achsenbeschriftung, Hinweis)."""
        ref = e.get("ref") or {}
        if ref.get("mode") == "manual":
            return ref.get("offset", 0.0), "Fc$^{0/+}$", T("cv_ref_own", off=_fmt_e(ref.get("offset", 0.0)))
        if ref.get("mode") == "internal":
            src = next((x for x in self.st["files"] if x["uid"] == ref.get("uid")), None)
            if src is not None:
                c = self.cycle_of(src)
                r = analyze_couple(c["E"], c["I"], ref.get("lo", 0.3), ref.get("hi", 0.8))
                if r is not None:
                    name = REFERENCES.get(ref.get("compound"), (T("cv_ref_custom"), 0))[0]
                    note = T("cv_ref_note", name=name, e12=_fmt_e(r["e12"]), el=self.st["ref_electrode"],
                             dep=f"{r['dep'] * 1000:.0f}", val=_fmt_e(ref.get("value", 0.0), 2))
                    note += _flag_note(r)
                    return r["e12"] - ref.get("value", 0.0), "Fc$^{0/+}$", note
            return 0.0, self.st["ref_electrode"], T("cv_ref_missing")
        return self.reference_offset()

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["files"] if e["visible"]]
        try:
            self.update_acs_hint()                       # Angaben aus der Datei und was für die Richtlinie fehlt
        except Exception as ex:                          # Hinweis darf das Zeichnen nie stören
            core.LOG(f"CV: {ex}")
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
        area_in = st.get("rs_area", 0.0)                # eingetragene Fläche gilt für Stromdichte und D
        no_area = [] if area_in > 0 else [e["label"] for e in vis if not self.data(e["file"])["meta"]["area"]]
        density = self._density = st["density"] and not no_area
        if st["density"] and no_area:
            notes.append(T("cv_area_missing", files=", ".join(no_area)))
        elif st["density"] and not area_in > 0:           # Fläche der Messdatei: oft die Vorgabe der Messsoftware
            areas = sorted({self.data(e["file"])["meta"]["area"] for e in vis})
            notes.append(T("cv_area_from_file", A=", ".join(f"{a:g}" for a in areas)))
        short = [e["label"] for e in vis if len(self.data(e["file"])["cycles"]) < st["cycle"]]
        if short:
            notes.append(T("cv_cycle_missing", files=", ".join(short), n=st["cycle"]))
        refs = self.ref_only_uids()
        for k, e in enumerate(vis):
            d = self.data(e["file"])
            c = self.cycle_of(e)
            off, lab_ref, n_ = self.file_offset(e)
            dep_ref, dep_kind = self.ref_dep(e)
            labels_ref.add(lab_ref)
            if n_ and e.get("ref"):
                notes.append(f"{e['label']}: {n_}")
            E = c["E"] - off
            if density:
                fac, unit = sign * 1e3 / (area_in if area_in > 0 else d["meta"]["area"]), "mA"   # mA cm⁻²
            else:
                fac, unit = sign * 1e6, "µA"
            y = fac * c["I"]
            color = (RATE_CMAP(order[k] / max(1, len(vis) - 1)) if st["gradient"] and len(vis) > 1 else e["color"])
            color = color if isinstance(color, str) else "#%02x%02x%02x" % tuple(int(255 * v) for v in color[:3])
            grad_colors[e["uid"]] = color
            curves.append({"x": E, "y": y, "val": y, "color": color, "label": core.math_units(e["label"]), "ls": "-", "lw": 1.3,
                           "uid": e["uid"], "_scale": fac,
                           "_off_e": off})
            # Fenster gespeichert in gemessenen Potentialen der globalen Referenz -> auf diese Messung umrechnen
            shift = off - off_g
            for n, (lo, hi) in enumerate(st["couples"], 1):
                r = analyze_couple(c["E"], c["I"], lo + shift, hi + shift, st["baseline"], st["bl_gap"])
                # reine Fc-Messung: das Fenster der Verbindung trifft dort nur den Rand (rote Zeile ohne Nutzen)
                if r is not None and not (r["invalid"] and not r["two_waves"] and e["uid"] in refs):
                    self.results.append(dict(r, label=e["label"], group=e.get("group", ""), n=n, uid=e["uid"],
                                             rate=d["meta"]["scanrate"], epa=r["epa"] - off, epc=r["epc"] - off,
                                             e12=r["e12"] - off, ircomp=d["meta"].get("ircomp", ""), offset=off,
                                             ref=lab_ref, file=e["file"], dep_ref=dep_ref, dep_ref_kind=dep_kind,
                                             ir_on=d["meta"].get("ircomp_on"),
                                             cycle=min(st["cycle"], len(d["cycles"]))))
        self.grad_colors = grad_colors if st["gradient"] and len(vis) > 1 else {}
        self.update_color_buttons()
        if len(labels_ref) > 1:
            notes.append(T("cv_ref_mixed"))
        ref_label = "Fc$^{0/+}$" if labels_ref == {"Fc$^{0/+}$"} else ref_label
        miss = self.ref_rates_missing()
        if miss:
            notes.append(T("cv_ref_rate_out", rates=", ".join(f"{v:g}" for v in miss)))
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
        xpad = X_PAD * (float(np.ptp(allx)) or 1.0)
        cfg["xlim"] = [float(allx.min()) - xpad, float(allx.max()) + xpad] if st["x_auto"] else [st["x_min"], st["x_max"]]
        ally = np.concatenate([c_["y"] for c_ in curves])
        span = float(ally.max() - ally.min()) or 1.0
        top = 0.22 if (st["show_e12"] and (st["e12_each"] or st["stack"])) else 0.12
        cfg["ylim"] = [float(ally.min()) - 0.08 * span, st["ymax"] if st["ymax"] > 0 else float(ally.max()) + top * span]
        cfg["xlabel"] = f"E [V vs. {axis_ref(ref_label)}]"
        cfg["ylabel"] = "j [mA cm$^{-2}$]" if (st["density"] and unit == "mA") else "I [µA]"
        if None not in self.pulse_kinds(vis) and vis:     # nur Pulsverfahren: aufgetragen ist der Differenzstrom
            cfg["ylabel"] = "Δ" + cfg["ylabel"]
        if st["show_e12"]:
            multi = len(st["couples"]) > 1
            mode = st.get("peak_labels", "e12")
            dens = st["density"] and unit == "mA"
            if mode != "e12":
                # Peakpotentiale als Zahl an den einzelnen Peaks (z. B. Probe und Ac₂Fc in einer Messung)
                for c_ in curves:
                    for r in self.results:
                        if r["uid"] != c_["uid"] or r["invalid"]:
                            continue
                        for kind, ex, ip, side in (("epa", r["epa"], r["ipa_raw"], "above"),
                                                         ("epc", r["epc"], r["ipc_raw"], "below")):
                            if mode in (kind, "both"):
                                labels.append({"key": f"label_{kind}_{c_['uid']}_{r['n']}", "lam": ex, "side": side,
                                               "y": None if dens else float(ip * 1e6 * sign) + c_.get("off", 0.0),
                                               "text": core.fmt_num(ex, E_DEC)})
            elif st["e12_each"] or stacked:
                # je Kurve und Redoxpaar, am anodischen Peak dieser Kurve (wie in Vergleichsabbildungen üblich)
                for c_ in curves:
                    for r in self.results:
                        if r["uid"] != c_["uid"] or r["invalid"]:
                            continue
                        sup = f"$^{{{r['n']}}}$" if multi else ""
                        side = "right" if (multi and r["n"] == len(st["couples"])) else "left"
                        labels.append({"key": f"label_e12_{c_['uid']}_{r['n']}", "lam": r["epa"], "side": side,
                                       "y": float(r["ipa_raw"] * 1e6 * sign) + c_.get("off", 0.0)
                                       if not (st["density"] and unit == "mA") else None,
                                       "text": f"E{sup}$_{{1/2}}$ = " + _fmt_e(r["e12"], E_DEC)})
            else:
                # Mittel je Gruppe: verschiedene Lösungsmittel nie zu einem E½ mitteln
                groups = sorted({r.get("group", "") for r in self.results})
                ser = self.e12_series()
                for n in range(1, len(st["couples"]) + 1):
                    for grp in groups:
                        e12 = ser.get((grp, n))
                        if e12 is not None:                                 # nie über Referenzskalen mitteln
                            tag = f" ({grp})" if len(groups) > 1 and grp else ""
                            key = f"label_e12_{n}" + (f"_{grp}" if len(groups) > 1 else "")
                            labels.append({"key": key, "lam": e12,
                                           "text": "E$_{1/2}$" + tag + " = " + _fmt_e(e12, E_DEC) + " V"})
        if st["arrow"]:
            c0 = curves[0]
            xr = cfg["xlim"][1] - cfg["xlim"][0]
            direction = 1.0 if np.gradient(c0["x"])[:5].mean() >= 0 else -1.0
            x0, y0 = float(c0["x"][0]), float(c0["y"][0])
            cfg["scan_arrow"] = (x0, y0, x0 + direction * 0.08 * xr)
            cfg["scan_arrow_prefer"] = "top-left"        # Vorgabe oben links über den Kurven (Entscheidung 179)
        imgs = self.ref_images(curves, cfg)              # interner Standard: seine Struktur an seiner Welle
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

    def ref_images(self, curves, cfg):
        """Struktur des internen Standards (Fc/Ac₂Fc, `REF_STRUCTS`) über dem Oxidationspeak seiner Messung (Chip „Struktur
        des Standards“ = `ref_marker`), schwarz (Vorgabe; auf dunkler Zeichenfläche weiß) oder in der Kurvenfarbe der
        Referenzmessung (`ref_color`); im Maßstab der Struktur der Verbindung im Bild (gleiche Bindungslänge), ohne diese
        in Druckgröße. Anderer Standard: nichts. Automatisches y-Maximum wächst, bis sie über den Peak passt.
        -> Bildeinträge."""
        found = []
        ax_w_in, ax_h_in = (cfg["figsize_in"][k] * cfg["axes_rect"][k + 2] for k in (0, 1))
        k_sc = self.ref_scale(ax_w_in)
        for uid, r, comp in self.ref_marks():
            c_ = next((x for x in curves if x["uid"] == uid), None)
            if c_ is None or comp not in REF_STRUCTS:
                continue
            path = Path(ROOT) / "assets" / "standards" / REF_STRUCTS[comp]
            try:
                asset = self.structure_asset(str(path), c_["color"] if self.st.get("ref_color") else None)
                head = path.read_text(encoding="utf-8")[:2000]
                w_pt, h_pt = (float(re.search(rf'{k}="([\d.]+)pt"', head).group(1)) for k in ("width", "height"))
            except Exception as ex:
                self.main.log_signal.emit(f"  {path.name}: {ex}")
                continue
            found.append((uid, path, asset, w_pt * k_sc, h_pt * k_sc, r["epa"] - c_["_off_e"],
                          float(r["ipa_raw"] * c_["_scale"]) + c_.get("off", 0.0)))
        y0, y1 = cfg["ylim"]
        if self.st["ymax"] <= 0:                         # Platz über dem Peak: Bildhöhe + 4 % der Achse
            for *_, h_pt, _x, ypk in found:
                f = h_pt / 72 / ax_h_in + 0.04
                if f < 0.8:
                    y1 = max(y1, (ypk - f * y0) / (1 - f))
            cfg["ylim"] = [y0, y1]
        out = []
        (x0, x1) = cfg["xlim"]
        for uid, path, asset, w_pt, h_pt, xpk, ypk in found:
            out.append({"file": str(path), "id": f"ref_{uid}", "_asset": asset, "width": w_pt / 72 / ax_w_in,
                        "prefer": core.anchor_score((xpk - x0) / (x1 - x0), (ypk - y0) / (y1 - y0))})
        return out

    def ref_scale(self, ax_w_in):
        """Faktor auf die Druckgröße der Standard-SVG: Bindungslänge wie die Struktur der ersten sichtbaren Messung mit
        Struktur (Breite `struct_w` % der Achse, Breite in Bindungslängen aus ihrer CDXML); ohne sie 1."""
        for e in self.st["files"]:
            p = e.get("structure")
            if e.get("visible", True) and p and Path(p).exists():
                u = IMG.structure_units(p)
                if u:
                    return self.st.get("struct_w", 18.0) / 100 * ax_w_in * 72 / u / REF_BOND_PT
        return 1.0

    def baseline_curves(self, curves):
        """Basislinien zur Kontrolle: Hin- und Rückbasislinie (gestrichelt) und Lote vom Peak (gepunktet)."""
        out = []
        for c_ in curves:
            sc, off_e, yoff = c_["_scale"], c_["_off_e"], c_.get("off", 0.0)
            for r in self.results:
                bl = r.get("bl")
                if r["uid"] != c_["uid"] or bl is None or r["invalid"]:
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
        ser, refs = {}, self.ref_only_uids()
        for r in self.results:                           # Messungen mit Standard (Häkchen Fc): nur Referenz (Entscheidung 177)
            if r["rate"] and not r["invalid"] and not (currents and r.get("bl_fail")) and r["uid"] not in refs:
                ser.setdefault((r["group"], r["n"]), []).append(r)
        return {k: sorted(v, key=lambda r: r["rate"]) for k, v in ser.items()}

    def ref_rates_missing(self):
        """Scanraten [mV s⁻¹], die nur eine Messung mit Standard hat: sie fehlen deshalb in der Scanraten-Analyse."""
        refs, ser = self.ref_only_uids(), self.rate_series()
        return sorted({round(r["rate"], 1) for r in self.results if r["uid"] in refs and r["rate"] and not r["invalid"]
                       and round(r["rate"], 1) not in {round(x["rate"], 1) for x in ser.get((r["group"], r["n"]), [])}})

    def e12_series(self):
        """E½ je (Gruppe, Paar): Mittel über alle gültigen Zeilen (auch ohne Scanrate in der Datei), nur bei einer
        Referenzskala – dieselbe Zahl im Bild und im Methodentext. -> {(Gruppe, n): E½ oder None}."""
        out = {}
        for r in self.results:
            if not r["invalid"]:
                out.setdefault((r.get("group", ""), r["n"]), []).append(r)
        return {k: float(np.mean([r["e12"] for r in rr])) if len({r["ref"] for r in rr}) == 1 else None
                for k, rr in out.items()}

    def ref_dep(self, e):
        """ΔE_p [V] der internen Referenz für die D-Schwelle, nur aus einem gültigen Paar -> (ΔE_p oder None, Art):
        „same“ = Referenz in derselben Messung (trägt denselben iR-Abfall), „separate“ = eigene Messung mit derselben
        Scanrate (Entscheidung 171: nur dann ein fairer Vergleich), „nomatch“ = eigene Messung mit anderer Scanrate
        (dann gilt wie ohne Referenz der reversible Grenzwert), None = keine interne Referenz."""
        st = self.st
        ref = e.get("ref") or {}
        if ref.get("mode") == "internal":
            uid, lo, hi = ref.get("uid"), ref.get("lo", 0.3), ref.get("hi", 0.8)
        elif not ref.get("mode") and st["ref_mode"] == "internal":
            uid, lo, hi = st.get("ref_uid"), st["ref_lo"], st["ref_hi"]
        else:
            return None, None
        kind = "same"
        if uid != e["uid"]:
            src = next((x for x in st["files"] if x["uid"] == uid), None)
            if src is None:
                return None, None
            try:
                v_ref, v_e = self.data(src["file"])["meta"]["scanrate"], self.data(e["file"])["meta"]["scanrate"]
            except Exception:
                return None, None
            if not (v_ref and v_e and abs(v_ref - v_e) <= REF_RATE_TOL):
                return None, "nomatch"
            e, kind = src, "separate"
        c = self.cycle_of(e)
        r = analyze_couple(c["E"], c["I"], lo, hi)
        return (None, None) if r is None or r["invalid"] else (float(r["dep"]), kind)

    def d_check(self, rr):
        """Scanraten [mV s⁻¹], bei denen das Paar nicht als reversibel gilt: ΔE_p > ΔE_p(Referenz derselben Messung)
        + D_DEP_TOL, ohne Referenz > 2,22·RT/(nF) + D_DEP_TOL. Leer = D ist ein Ergebnis, sonst nur „scheinbar“
        (langsamer Elektronentransfer oder unkompensierter Widerstand machen i_p und damit D zu klein)."""
        st = self.st
        rev = dep_reversible(st["rs_n"], st["rs_temp"])
        return sorted({round(r["rate"], 1) for r in rr
                       if r["dep"] > (r["dep_ref"] if r.get("dep_ref") is not None else rev) + D_DEP_TOL})

    def k0_info(self, key, fits=None):
        """k⁰ eines Paars über die Scanraten (`k0_value`), D_O = D_R = eingegebenes D, sonst D aus Randles–Ševčík des
        Hinpeaks. -> dict(vals=[(v, k⁰, Verfahren)], skip={v: Grund}, lo, hi, D, D_src "entered"|"rs", apparent=[Gründe:
        "ir" ohne iR-Kompensation (Datei, sonst Projektangabe), "ref" ΔE_p der Referenz über der D-Schwelle, "D" D aus
        einem nicht reversiblen Paar], falls=k⁰ fällt mit v) oder None (kein D)."""
        st = self.st
        rr = self.rate_series().get(key) or []
        if not rr:
            return None
        D, src = st.get("k0_D", 0.0), "entered"
        if not D > 0:
            Dt = self.diffusion(fits) if fits else None
            if not Dt:
                return None
            D, src = Dt[0], "rs"
        vals, skip = [], {}
        for r in rr:
            k, how = k0_value(r["dep"], r["rate"], D, st["rs_n"], st["rs_temp"], st.get("k0_alpha", 0.0))
            if k is None:
                skip[round(r["rate"], 1)] = how
            else:
                vals.append((r["rate"], float(k), how))
        apparent = []
        pub_ir = bool((self.project_setup() or {}).get("ir"))
        if any(r.get("ir_on") is False or (r.get("ir_on") is None and not pub_ir) for r in rr):
            apparent.append("ir")
        if any(r.get("dep_ref") is not None and r["dep_ref"] > dep_reversible(1, st["rs_temp"]) + D_DEP_TOL for r in rr):
            apparent.append("ref")
        if src == "rs" and self.d_check(self.rate_series(currents=True).get(key) or []):
            apparent.append("D")
        ks = [k for _, k, _ in vals]
        return dict(vals=vals, skip=skip, lo=min(ks) if ks else None, hi=max(ks) if ks else None, D=D, D_src=src,
                    apparent=apparent, falls=len(vals) >= 2 and vals[-1][1] < K0_FALL * vals[0][1])

    def rate_fits(self):
        """Regressionen je (Gruppe, Redoxpaar) ab 3 Scanraten -> {(Gruppe, n): dict(rs_a, rs_c, ll_a, ll_c, rates)}."""
        out = {}
        for key, rr in self.rate_series(currents=True).items():
            v = [r["rate"] for r in rr]
            if len(set(v)) < 3:
                continue
            ia, ic = [r["ipa"] * 1e6 for r in rr], [r["ipc"] * 1e6 for r in rr]
            first = {bool(r["anodic_first"]) for r in rr}     # Hinpeak: nur er folgt Randles–Ševčík (für D)
            out[key] = dict(rs_a=rate_fit(np.sqrt(np.array(v) / 1000.0), ia),
                            rs_c=rate_fit(np.sqrt(np.array(v) / 1000.0), ic),
                            ll_a=loglog_fit(v, ia), ll_c=loglog_fit(v, ic), rates=sorted(set(v)),
                            fwd=("a" if first == {True} else "c" if first == {False} else None))
        return out

    def diffusion(self, fits):
        """D [cm² s⁻¹] mit 95-%-Grenzen aus der Randles–Ševčík-Regression des **Hinpeaks** eines Paars (`rate_fits`-
        Eintrag; Steigung in µA (V s⁻¹)^-½). Nie aus dem Rückpeak: er wird gegen die verschobene Hin-Basislinie
        gemessen (Nicholsons (i_p)0) und ergäbe ein um etwa 40 % zu kleines D (Literaturprüfung 2026-11, Bard &
        Faulkner §6.2/6.5). Die Grenzen tragen nur die Unsicherheit der Steigung.
        -> (D, lo, hi, "a"|"c") oder None (Angaben fehlen, keine Regression, Richtung der Messungen gemischt)."""
        st = self.st
        tag = fits.get("fwd") if fits else None
        fit = fits.get("rs_" + tag) if tag else None
        if not fit:
            return None
        d = lambda m: diffusion_coefficient(m * 1e-6, st["rs_n"], st["rs_area"], st["rs_conc"], st["rs_temp"])  # noqa: E731
        D = d(fit["slope"])
        if D is None:
            return None
        lo, hi = abs(fit["slope"]) - fit["ci"], abs(fit["slope"]) + fit["ci"]
        return D, (d(lo) if lo > 0 else None), d(hi), tag

    def rate_plot(self, cfg, ref_label):
        """ΔE_p gegen v, Randles-Ševčík (i_p gegen √v) oder Trumpet-Plot (E_p gegen log v)."""
        st = self.st
        ser = self.rate_series(currents=st["plot"] in ("rs", "rs_v", "loglog", "ratio"))
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
            elif st["plot"] in ("rs", "rs_v"):
                xv = np.sqrt(v / 1000.0) if st["plot"] == "rs" else v / 1000.0     # √v oder v, beides in V/s
                for key, tag, m_ in (("ipa", "a", "^"), ("ipc", "c", "v")):
                    ip = np.array([r[key] * 1e6 for r in rr])
                    lab = f"i$_{{p{tag}}}$" + (f" {name}" if name else "")
                    curves.append(dict(base, x=xv, y=ip, label=lab, marker=m_))
                    fit = rate_fit(xv, ip)
                    if fit:
                        xf = np.array([0.0, float(xv.max()) * 1.05])
                        curves.append(dict(color=col, ls="--", lw=1.0, x=xf, y=fit["slope"] * xf + fit["intercept"],
                                           label=None))
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
        min_span = {"dep": 40.0, "rs": 1.0, "rs_v": 1.0, "loglog": 0.3, "ratio": 0.3, "trumpet": 0.05}[st["plot"]]
        ypad = 0.1 * max(float(np.ptp(ys)), min_span) + max(0.0, min_span - float(np.ptp(ys))) / 2
        if st["plot"] == "dep":
            cfg["xlim"] = [0.0, float(xs.max()) * 1.08]
            cfg["ylim"] = [max(0.0, float(ys.min()) - ypad), float(ys.max()) + ypad]
            cfg["xlabel"], cfg["ylabel"] = "scan rate [mV s$^{-1}$]", "peak to peak separation ΔE$_p$ [mV]"
        elif st["plot"] in ("rs", "rs_v"):
            cfg["xlim"] = [0.0, float(xs.max()) * 1.08]
            cfg["ylim"] = [min(0.0, float(ys.min()) - ypad), max(0.0, float(ys.max()) + ypad)]
            cfg["xlabel"] = "v$^{1/2}$ [V s$^{-1}$]$^{1/2}$" if st["plot"] == "rs" else "v [V s$^{-1}$]"
            cfg["ylabel"] = "i$_p$ [µA]"
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
            cfg["xlabel"], cfg["ylabel"] = "scan rate [mV s$^{-1}$]", "i$_{p,r}$/i$_{p,f}$ (Nicholson)"
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
        # ν steht im Namen (Vorgabe „50 mV s-1“); nennt ein Name die Scanrate nicht, wird sie angehängt – eine eigene
        # Spalte ließ die Tabelle bei 1200 px quer rollen
        self.tbl_res.setRowCount(len(res))
        for i, r in enumerate(res):
            rate = f"{round(r['rate'], 1):g} mV s-1" if r["rate"] else ""
            name = r["label"] if not rate or rate in r["label"] else f"{r['label']} · {rate}"
            name = f"{name} ({r['group']})" if r.get("group") else name
            vals = [name, str(r["n"]), _fmt_e(r["epa"], E_DEC), _fmt_e(r["epc"], E_DEC), _fmt_e(r["e12"], E_DEC),
                    f"{r['dep'] * 1000:.0f}", f"{r['ipa'] * 1e6:.1f}", f"{r['ipc'] * 1e6:.1f}",
                    f"{r['ratio']:.2f}" if np.isfinite(r["ratio"]) else "–"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v.replace("-", "−") if j >= 2 else v)      # echtes Minus wie im Text darunter
                if r["invalid"]:                                 # Rand oder zwei Wellen: nirgends ausgewertet
                    it.setForeground(Qt.red)
                    it.setToolTip(_flag_note(r).strip())
                elif r.get("bl_fail") and j >= 6:
                    it.setForeground(Qt.darkYellow)
                    it.setToolTip(T("cv_bl_fail"))
                elif j == 8 and not r.get("ratio_ok", True):
                    it.setToolTip(T("cv_ratio_invalid"))
                elif j == 0:
                    it.setToolTip(name)                          # Name wird bei wenig Platz gekürzt
                self.tbl_res.setItem(i, j, it)
        # so hoch wie die Zeilen (wie die Tabellen darunter): die Seite rollt, nie eine halb sichtbare Zeile
        self.tbl_res._rows_h = self.tbl_res.horizontalHeader().sizeHint().height() + len(res) * STYLE.CHECK_ROW_H + 2
        self.tbl_res.setFixedHeight(self.tbl_res._rows_h)
        self.tbl_res.fit()
        # Warnungen gesammelt je Art: (Anzahl, Einzelheiten)
        warn = {k: [0, []] for k in self.WARN_KINDS}
        n_fail = sum(1 for r in res if r.get("bl_fail"))
        if n_fail:
            warn["bl_fail"] = [n_fail, [T("cv_bl_fail")]]
        n_short = sum(1 for r in res if r.get("bl_short"))
        if n_short:
            warn["bl_short"] = [n_short, [T("cv_bl_short", n=n_short, gap=f"{BL_GAP_MIN:.2f}")]]
        n_two = sum(1 for r in res if r.get("two_waves"))
        if n_two:
            warn["two_waves"] = [n_two, [T("cv_two_waves_warn", n=n_two)]]
        rows, dk_rows, dk_tips, dk_warn = [], [], [], []
        mn = lambda t: t.replace("-", "−")                    # noqa: E731  (echtes Minus wie in der Tabelle darüber)
        rates = lambda v: ", ".join(f"{x:g}" for x in v)      # noqa: E731
        for (grp, n), f in sorted(self.rate_fits().items(), key=lambda kv: (kv[0][1], kv[0][0])):
            name = f"{n}" + (f" ({grp})" if grp else "")
            for tag, rs, ll in (("a", f["rs_a"], f["ll_a"]), ("c", f["rs_c"], f["ll_c"])):
                if rs and ll:
                    rows.append([name, f"i_p{tag}", str(rs["n"]), mn(fmt_ci(rs["slope"], rs["ci"])),
                                 mn(fmt_ci(rs["intercept"], rs["ci_b"], ref=rs["slope"])), core.r2_text(rs["r2"]),
                                 mn(fmt_ci(ll["slope"], ll["ci"]))])
            D = self.diffusion(f)
            k0 = self.k0_info((grp, n), f)
            if not D and not k0:
                continue
            short, long_ = [], []
            d_txt = k_txt = "–"
            bad = self.d_check(self.rate_series(currents=True).get((grp, n)) or []) if D else []
            if D:                                             # Grenzen mit demselben Exponenten
                ex = int(f"{D[0]:.2e}".split("e")[1])
                d_txt = f"{D[0] / 10 ** ex:.2f} ({(D[1] or 0) / 10 ** ex:.2f}–{D[2] / 10 ** ex:.2f}) × 10^{ex}"
                short.append(T("cv_dk_D_app" if bad else "cv_dk_D_ok"))
                if bad:
                    long_.append(T("cv_D_apparent_warn", couple=name, rates=rates(bad)))
                    warn["D"][0] += 1
                    warn["D"][1].append(long_[-1])
                miss = sorted({round(r["rate"], 1) for r in self.rate_series().get((grp, n)) or []
                               if r.get("dep_ref_kind") == "nomatch"})
                if miss:                                      # Referenz nur bei anderer Scanrate gemessen
                    long_.append(T("cv_dk_ref_rate", rates=rates(miss)))
            k_app = False
            if k0:
                if k0["vals"]:
                    k_txt = sci_range(k0["lo"], k0["hi"])
                    k_app = bool(k0["apparent"])
                    short.append(T("cv_dk_k0_app" if k_app else "cv_dk_k0_ok"))
                    if k_app:
                        long_.append(T("cv_k0_apparent_warn", couple=name,
                                       why="; ".join(T("cv_k0_why_" + w) for w in k0["apparent"])))
                        warn["k0"][0] += 1
                        warn["k0"][1].append(long_[-1])
                for why in ("rev", "alpha"):
                    rr = [v for v, w in k0["skip"].items() if w == why]
                    if rr:
                        short.append(T("cv_dk_skip_" + why, n=len(rr)))
                        long_.append(T("cv_k0_skip_" + why, couple=name, rates=rates(rr)))
                if k0["falls"]:
                    short.append(T("cv_dk_falls"))
                    long_.append(T("cv_k0_falls", couple=name, pct=f"{(1 - K0_FALL) * 100:.0f}"))
                    warn["k0_falls"][0] += 1
                    warn["k0_falls"][1].append(long_[-1])
            dk_rows.append([name, mn(d_txt), mn(k_txt), "; ".join(short)])
            dk_tips.append("\n".join(x.lstrip("⚠ ") for x in long_))
            dk_warn.append((bool(bad), k_app, bool(bad or k_app or (k0 and k0["falls"]))))
        STYLE.fill_summary(self.tbl_fit, rows)
        STYLE.fill_summary(self.tbl_dk, dk_rows)
        for i, (d_bad, k_bad, any_bad) in enumerate(dk_warn):    # scheinbare Werte in der Warnfarbe
            for j, on in ((1, d_bad), (2, k_bad), (3, any_bad)):
                if on:
                    self.tbl_dk.item(i, j).setForeground(Qt.darkYellow)
            self.tbl_dk.item(i, 3).setToolTip(dk_tips[i] or dk_rows[i][3])
        for x, on in ((self.lbl_fit, rows), (self.lbl_dk, dk_rows), (self.lbl_res, getattr(self, "note", ""))):
            x.setVisible(bool(on))
        self.lbl_res.setText(getattr(self, "note", "") or "")
        for k, (cnt, tips) in warn.items():
            lb_ = self.warn_lbls[k]
            lb_.setText("⚠ " + T("cv_w_" + k, n=cnt) if cnt else "")
            lb_.setToolTip("\n".join(x.lstrip("⚠ ") for x in tips))
            lb_.setVisible(bool(cnt))

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

    def chain(self):
        st = self.st
        return [(T("chain_cycle", n=st["cycle"]), True), (T("chain_baseline"), bool(st["baseline"])),
                ("E½", bool(st["couples"])), (T("chain_ref"), st["ref_mode"] != "none")]

    def kpis(self):
        r = next((r for r in getattr(self, "results", None) or [] if not r["invalid"]), None)   # erste gültige Zeile
        if r is None:
            return []
        return [("E½", _fmt_e(r["e12"], E_DEC) + " V"), ("ΔEp", f"{r['dep'] * 1000:.0f} mV")]

    def setup_values(self):
        """Messaufbau aus den Feldern dieser Verbindung (Karte „Messbedingungen“, Fläche aus Randles-Ševčík); die
        Referenzelektrode aus dem eigenen Feld des Aufbaus (`acs_ref`); die Referenz der Achse (`ref_electrode`) gilt nur,
        wenn der Nutzer sie geändert hat (ihre Vorgabe ist keine Angabe über den Aufbau) und Elektroden eingetragen sind
        (alte Verbindungen mit eigener Angabe behalten ihren Satz)."""
        st = self.st
        axis_ref = st.get("ref_electrode") or ""
        old_ref = (axis_ref if axis_ref != self.DEFAULT_STATE["ref_electrode"] and (st.get("acs_we") or st.get("acs_ce"))
                   else "")
        v = dict(device=st.get("acs_device"), we=st.get("acs_we"),
                 area=f"{st['rs_area']:g}" if st.get("rs_area", 0.0) > 0 else "", polish=st.get("acs_polish"),
                 ce=st.get("acs_ce"), gas=st.get("acs_gas"), ref=st.get("acs_ref") or old_ref)
        return {k: x for k, x in v.items() if x}

    def project_setup(self):
        """Messaufbau des Projekts (cv_setup) oder None, wenn die Verbindung zu keinem Projekt gehört."""
        from elucida.app import publication as PUB
        pdir = PUB.publication_of(self.main.project_dir)
        if pdir is None:
            return None
        f = Path(pdir) / PUB.PUB_FILE
        key = ("cvsetup", str(f), f.stat().st_mtime_ns if f.exists() else 0)
        return self.cache(key, lambda: dict(PUB.load(pdir).get("cv_setup") or {}))

    def setup_effective(self):
        """Was gilt: Angaben des Projekts, wo sie fehlen die der Verbindung (alte Verbindungen werden nicht umgeräumt)."""
        return dict(self.setup_values(), **{k: v for k, v in (self.project_setup() or {}).items() if v})

    def setup_sentence(self):
        """Messaufbau im Methodentext der Verbindung, nur ohne Projekt: im Projekt steht er einmal als Anfangstext des
        Kapitels der Gesamt-SI (sonst stünde er dort je Verbindung noch einmal)."""
        if self.project_setup() is not None:
            return ""
        kinds = self.pulse_kinds([e for e in self.st["files"] if e["visible"]])
        return setup_text(self.setup_values(), "Cyclic voltammograms" if kinds <= {None} else "Voltammograms")

    def methods_text(self):
        """SI-Text zur Auswertung (englisch, Stil des Abschnitts „Cyclic Voltammetry“ der Gruppen-SI): Gerät,
        Elektroden und Leitsalz stehen im Aufbau-Absatz der SI und fehlen hier bewusst. Danach ein Absatz mit
        den Ergebnissen je Redoxpaar (zum Übernehmen in Text oder Bildunterschrift)."""
        st = self.st
        rates = sorted({round(r["rate"], 1) for r in self.results if r["rate"]})
        ref_txt, ref_lab = self._ref_sentence()
        vis = [e for e in st["files"] if e["visible"]]
        kinds = self.pulse_kinds(vis)
        if kinds and None not in kinds:                # nur Pulsmessungen: keine CV-Sätze (E½, Nicholson, Zyklen)
            from elucida.formats.gamry import PULSE_NAMES
            title = PULSE_NAMES[next(iter(kinds))] if len(kinds) == 1 else "Pulse voltammograms"
            metas = []
            for e in vis:
                try:
                    metas.append(self.data(e["file"])["meta"])
                except Exception:
                    pass
            pp = pulse_params(metas)
            m = [self.setup_sentence(), ref_txt,
                 f"{title} are shown as the difference current against the step potential"
                 + (f" ({pp})" if pp else "") + "."]
            return " ".join(x for x in m if x)
        m = [self.setup_sentence(), ref_txt,           # nur die Mathematik, kein Programmname (Nutzerwunsch)
             "Peak potentials (Epa, Epc) were obtained by a parabolic fit to the current extremum (±3 data points) "
             f"of cycle {st['cycle']}; E1/2 = (Epa + Epc)/2 and ΔEp = Epa − Epc."]
        vis = [e for e in st["files"] if e["visible"]]
        short = [core.si_units(e["label"]) for e in vis if len(self.data(e["file"])["cycles"]) < st["cycle"]]
        if short:
            m.append(f"For {', '.join(short)} (fewer cycles), the last cycle was used.")
        if st["baseline"]:
            m.append("Peak currents were measured against a linear baseline fitted to the current of the forward "
                     f"scan before the onset of the wave (ending at least {st['bl_gap'] * 1000:.0f} mV before the "
                     f"peak potential and before the current exceeded {BL_ONSET * 100:.0f}% of the peak height) and "
                     "extrapolated beneath the peak. For the reverse peak, this baseline was shifted "
                     "by the change of the capacitive current at the switching potential (current step of 2C·v).")
            n_short = sum(1 for r in self.results if r.get("bl_short"))
            if n_short:
                m.append(f"For {n_short} of {len(self.results)} peak pairs the scan before the wave was too short for "
                         f"this distance; their baseline ended {BL_GAP_MIN * 1000:.0f} mV before the peak potential.")
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
            Ds = {k_: self.diffusion(f_) for k_, f_ in fits.items()}
            if any(Ds.values()):
                m.append("Diffusion coefficients were calculated from the Randles–Ševčík slope of the forward peak for "
                         "a reversible, freely diffusing couple, ip = 0.4463·n·F·A·c·(n·F·v·D/RT)1/2, with n = "
                         f"{st['rs_n']}, A = {st['rs_area']:g} cm2, c = {st['rs_conc']:g} mM and T = "
                         f"{st['rs_temp']:g} °C; their intervals reflect the uncertainty of the slope only.")
                m.append("D is reported as a result only if ΔEp at every scan rate was at most 10 mV above ΔEp of the "
                         "internal standard in the same measurement or in a separate measurement at the same scan rate "
                         "(without one, above 2.22·RT/(nF)); otherwise it is given as an apparent value, because slow "
                         "electron transfer or uncompensated resistance lowers the peak current.")
                # Standard in eigener Messung: ΔE_p nur bei gleicher Scanrate vergleichbar (Entscheidung 171)
                rr_ = [r for r in self.results if not r["invalid"] and r.get("rate")]
                sep_ = ", ".join(f"{x:g}" for x in sorted({round(r["rate"], 1) for r in rr_
                                                             if r.get("dep_ref_kind") == "separate"}))
                miss_ = ", ".join(f"{x:g}" for x in sorted({round(r["rate"], 1) for r in rr_
                                                              if r.get("dep_ref_kind") == "nomatch"}))
                if miss_:
                    m.append("The internal standard was measured in a separate run"
                             + (f" at {sep_} mV s-1 only" if sep_ else " at a different scan rate")
                             + f"; at {miss_} mV s-1 the reversible limit 2.22·RT/(nF) + 10 mV was used instead, "
                             "because ΔEp of a separate measurement is comparable only at the same scan rate.")
            k0s = {k_: self.k0_info(k_, f_) for k_, f_ in fits.items()}
            used = {how for k_ in k0s.values() if k_ for _, _, how in k_["vals"]}
            if used:
                srcs = {k_["D_src"] for k_ in k0s.values() if k_ and k_["vals"]}
                d_src = " and ".join(("the Randles–Ševčík value of the couple" if x == "rs" else
                                      f"D = {core.sci_text(st['k0_D'])} cm2 s-1") for x in sorted(srcs, reverse=True))
                parts = []
                if "lav" in used:
                    parts.append(f"for n·ΔEp of {K0_X_MIN:.0f}–{K0_X_MAX:.0f} mV from Nicholson's kinetic parameter "
                                 "ψ = k0 (π·D·n·F·v/RT)-1/2, approximated by ψ = (−0.6288 + 0.0021·n·ΔEp)/"
                                 "(1 − 0.017·n·ΔEp) [R. S. Nicholson, Anal. Chem. 1965, 37, 1351; I. Lavagnini, "
                                 "R. Antiochia, F. Magno, Electroanalysis 2004, 16, 505]")
                if "kk" in used:
                    parts.append(f"for n·ΔEp above {K0_X_MAX:.0f} mV according to k0 = 2.18 (D·α·n·F·v/RT)1/2 "
                                 f"exp(−α2·n·F·ΔEp/RT) with α = {st['k0_alpha']:g} [R. J. Klingler, J. K. Kochi, "
                                 "J. Phys. Chem. 1981, 85, 1731]")
                m.append("Standard heterogeneous electron-transfer rate constants k0 were estimated from ΔEp at each "
                         f"scan rate with DO = DR = D ({d_src}) and n = {st['rs_n']} (n·ΔEp scaled to 25 °C), "
                         + " and ".join(parts) + ". k0 is given as the range over the scan rates; scan rates with "
                         f"n·ΔEp below {K0_X_MIN:.0f} mV were too close to reversible behaviour to give a value.")
        res = []
        valid = {}
        for r in self.results:
            if not r["invalid"]:
                valid.setdefault((r.get("group", ""), r["n"]), []).append(r)
        e12s = self.e12_series()                         # dieselben Mittel wie im Bild (auch ohne Scanrate)
        rates_txt = lambda v: ", ".join(f"{x:g}" for x in v)      # noqa: E731
        for (grp, n), rr in sorted(valid.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            refs = {r["ref"] for r in rr}
            e12 = e12s.get((grp, n))
            lab = str(next(iter(refs))).replace("Fc$^{0/+}$", "Fc0/+") if len(refs) == 1 else ref_lab
            dep = [r["dep"] * 1000 for r in rr]
            rat = [r["ratio"] for r in rr if np.isfinite(r["ratio"]) and not r.get("bl_fail")]
            rv = sorted(round(r["rate"], 1) for r in rr if r["rate"])
            rng = lambda v, f: f"{min(v):{f}}" + (f"–{max(v):{f}}" if f"{min(v):{f}}" != f"{max(v):{f}}" else "")  # noqa: E731
            e_txt = (f"E1/2 = {_fmt_e(e12, E_DEC)} V vs. {lab}" if e12 is not None
                     else "E1/2 not averaged (different reference scales)")
            txt = (f"Couple {n}" + (f" ({grp})" if grp else "") + f": {e_txt}"
                   + f" (ΔEp = {rng(dep, '.0f')} mV" + (f", ip,r/ip,f = {rng(rat, '.2f')}" if rat else "")
                   + (f"; {rng(rv, 'g')} mV s-1" if len(rv) > 1 else "") + ")")
            f = fits.get((grp, n))
            if f and f["ll_a"] and f["ll_c"]:
                txt += (f"; log–log slopes {fmt_ci(f['ll_a']['slope'], f['ll_a']['ci'])} (ipa) and "
                        f"{fmt_ci(f['ll_c']['slope'], f['ll_c']['ci'])} (ipc)")
            D = self.diffusion(f)
            if D:
                bad = self.d_check(self.rate_series(currents=True).get((grp, n)) or [])
                txt += (f"; {'apparent ' if bad else ''}D = {core.sci_text(D[0])} cm2 s-1 from ip{D[3]} (95% interval "
                        f"{core.sci_text(D[1]) if D[1] else '0'} to {core.sci_text(D[2])} cm2 s-1"
                        + (f"; couple not reversible at {rates_txt(bad)} mV s-1" if bad else "") + ")")
            k0 = self.k0_info((grp, n), f) if f else None
            if k0 and k0["vals"]:
                why = {"ir": "recorded without iR compensation",
                       "ref": "ΔEp of the internal standard indicates uncompensated resistance",
                       "D": "D from a couple that is not reversible"}
                txt += (f"; {'apparent ' if k0['apparent'] else ''}k0 = {sci_range(k0['lo'], k0['hi'])} cm s-1 "
                        f"({len(k0['vals'])} of {len(k0['vals']) + len(k0['skip'])} scan rates"
                        + ("; " + ", ".join(why[w] for w in k0["apparent"]) if k0["apparent"] else "")
                        + ("; k0 decreases with increasing scan rate, indicating uncompensated resistance"
                           if k0["falls"] else "") + ")")
            res.append(txt + ".")
        out = " ".join(x for x in m if x)
        return out + ("\n\n" + " ".join(res) if res else "")

    def hover_text(self, x, val, name):
        plot = self.st.get("plot", "cv")
        if plot != "cv":
            xs = {"dep": f"ν = {x:.0f} mV s⁻¹", "rs": f"√ν = {x:.3f} V½ s⁻½", "rs_v": f"ν = {x:.3f} V s⁻¹",
                  "trumpet": f"log ν = {x:.2f}", "loglog": f"log ν = {x:.2f}", "ratio": f"ν = {x:.0f} mV s⁻¹"}[plot]
            ys = {"dep": "ΔE_p = {:.0f} mV", "rs": "i_p = {:.2f} µA", "rs_v": "i_p = {:.2f} µA", "trumpet": "E_p = {:.3f} V",
                  "loglog": "log i_p = {:.3f}", "ratio": "i_r/i_f = {:.2f}"}[plot]
            return f"{xs}    {ys.format(val)}    {name}" if val is not None else xs
        if val is None:
            return f"E = {x:.3f} V"
        dens = getattr(self, "_density", self.st["density"])
        unit = "mA cm⁻²" if dens else "µA"
        return f"E = {x:.3f} V    {'j' if dens else 'I'} = {val:.2f} {unit}    {name}"

    def export_to(self, base: Path):
        """Abbildung wie die anderen Tabs, dazu die Ergebnisse als CSV (Entscheidung 170: Komma, Dezimalpunkt, UTF-8 mit
        BOM, englische ASCII-Köpfe „Name [Einheit]“, volle Rohwerte – die Stellen der Anzeige gehören nicht hierher): je
        Messung und Paar (`_results.csv`) und je Regression gegen die Scanrate mit D und k⁰ (`_rate_fits.csv`).
        Statuswerte englisch und fest (sprachfrei); leere Zelle = kein Wert."""
        files = super().export_to(base)
        st = self.st
        data = next((f for f in files if f.name.endswith("_data.csv")), None)
        if data is not None:          # Kurvennamen der Abbildung tragen Mathtext („s$^{-1}$“): Kopf als ASCII (Entsch. 170)
            with open(data, encoding="utf-8-sig", newline="") as fh:
                head, rest = fh.read().split("\r\n", 1)
            fold = str.maketrans({"µ": "u", "−": "-", "⁰": "0", "⁺": "+", **{chr(0x2080 + k): str(k) for k in range(10)}})
            buf = io.StringIO()
            csv.writer(buf).writerow([TABS._plain(h).translate(fold) for h in next(csv.reader([head]))])
            with open(data, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write(buf.getvalue() + rest)
        p = Path(base).with_name(Path(base).name + "_results.csv")
        num = lambda v: repr(float(v)) if v is not None and np.isfinite(v) else ""     # noqa: E731
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["file", "label", "group", "couple", "cycle", "v [mV s^-1]", "E_pa [V]", "E_pc [V]", "E_1/2 [V]",
                        "dE_p [mV]", "dE_p reference [mV]", "|E_p - E_p/2| [mV]", "i_pa [uA]", "i_pc [uA]",
                        "i_r/i_f Nicholson", "ratio_ok", "peak_at_window_edge", "two_waves_in_window",
                        "reference offset [V]", "ir_compensation_in_file", "reference", "baseline", "baseline_short",
                        "i_pa raw [uA]", "i_pc raw [uA]", "charging step [uA]", "T [degC]"])
            for r in self.results:
                epf = r["epa"] if r.get("anodic_first", True) else r["epc"]
                ep2 = r["ep2"] - r.get("offset", 0) if r.get("ep2") is not None else None
                w.writerow([Path(r.get("file", "")).name, r["label"], r.get("group", ""), r["n"], r.get("cycle", ""),
                            num(r["rate"]), num(r["epa"]), num(r["epc"]), num(r["e12"]), num(r["dep"] * 1000),
                            num(r["dep_ref"] * 1000 if r.get("dep_ref") is not None else None),
                            num(abs(epf - ep2) * 1000 if ep2 is not None else None),
                            num(r["ipa"] * 1e6), num(r["ipc"] * 1e6), num(r["ratio"]),
                            int(r.get("ratio_ok", True)), int(r["edge"]), int(r.get("two_waves", False)),
                            num(r.get("offset", 0)),
                            r.get("ircomp", ""),                       # Skala, nie Hinweistext (sprachfrei), ASCII: „Ag/AgNO3“
                            str(r["ref"]).replace("Fc$^{0/+}$", "Fc0/+").translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")),
                            "failed" if r.get("bl_fail") else ("linear" if r.get("bl") else "none"),
                            int(r.get("bl_short", False)), num(r["ipa_raw"] * 1e6), num(r["ipc_raw"] * 1e6),
                            num(r["bl"]["step"] * 1e6) if r.get("bl") else "", num(st["rs_temp"])])
        p2 = Path(base).with_name(Path(base).name + "_rate_fits.csv")
        with open(p2, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["couple", "group", "peak", "n scan rates", "slope [uA (V s^-1)^-1/2]",
                        "slope CI95 [uA (V s^-1)^-1/2]", "intercept [uA]", "intercept CI95 [uA]", "R2", "log-log slope",
                        "log-log slope CI95", "D [cm^2 s^-1]", "D low [cm^2 s^-1]", "D high [cm^2 s^-1]", "D_status",
                        "D not reversible at [mV s^-1]", "k0 low [cm s^-1]", "k0 high [cm s^-1]", "k0_status",
                        "k0_apparent_because", "k0_methods", "k0 scan rates used [mV s^-1]",
                        "k0 no value at [mV s^-1]", "k0_D_source", "k0_falls_with_scan_rate", "alpha"])
            for (grp, n), f in sorted(self.rate_fits().items(), key=lambda kv: (kv[0][1], kv[0][0])):
                D = self.diffusion(f)
                bad = self.d_check(self.rate_series(currents=True).get((grp, n)) or []) if D else []
                k0 = self.k0_info((grp, n), f)
                for tag in ("a", "c"):
                    rs, ll = f["rs_" + tag], f["ll_" + tag]
                    if not rs:
                        continue
                    row = [n, grp, "i_p" + tag, rs["n"], num(rs["slope"]), num(rs["ci"]), num(rs["intercept"]),
                           num(rs["ci_b"]), num(rs["r2"]), num(ll["slope"]) if ll else "", num(ll["ci"]) if ll else ""]
                    if D and D[3] == tag:
                        row += [num(D[0]), num(D[1]), num(D[2]), "apparent" if bad else "result",
                                " ".join(f"{x:g}" for x in bad)]
                    else:
                        row += [""] * 5
                    if k0 and tag == (D[3] if D else f.get("fwd")) and k0["vals"]:
                        row += [num(k0["lo"]), num(k0["hi"]), "apparent" if k0["apparent"] else "result",
                                " ".join(k0["apparent"]), " ".join(sorted({h for _, _, h in k0["vals"]})),
                                " ".join(f"{v:g}" for v, _, _ in k0["vals"]),
                                " ".join(f"{v:g}:{why}" for v, why in k0["skip"].items()),
                                k0["D_src"], int(k0["falls"]), num(st["k0_alpha"]) if st.get("k0_alpha") else ""]
                    else:
                        row += [""] * 10
                    w.writerow(row)
        return files + [p, p2]
