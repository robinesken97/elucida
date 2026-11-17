"""
elucida/core/nmr_analysis.py - 1D-NMR auswerten (ohne Qt): Rauschen, Basislinie, Phasenvorschlag, Referenzvorschlag über
das Lösungsmittel-Restsignal, Peaks, Integrale, Multipletts erster Ordnung. Alles sind Vorschläge für den Nutzer; die
Zahlen der SI entstehen aus seinen Entscheidungen (Bereich, Klasse, J, Referenz, Normierung).

Prüfung außerhalb des Repos (Audit 1.3.0): Basislinie, Integrale und ¹³C-Peaks belastbar; automatische Phase,
Restsignal-Referenz und Multiplettklasse nicht, deshalb nur Vorschlag. Nie procs SF/SR als Referenz (TopSpins Kalibrierung
ist nicht die der gedruckten Werte): Achse unkalibriert, `axis_uncalibrated`.
Achsen: ppm fallend mit dem Index (wie TopSpins 1r), sf = Spektrometerfrequenz in MHz (ppm · MHz = Hz).
"""
from __future__ import annotations

import itertools
import math
import re

import numpy as np

from elucida.app.i18n import T
from elucida.core import nmr_impurities as IMP

# Parameter des Prototyps (vor der Prüfung eingefroren); ¹H-Restsignalfenster ±0.25 ppm (Spezifikation 1.3.0);
# BL_ITER … QUIET_MIN neu in 1.3.0 (Abnahmetests der Prüfung, nicht eingefroren)
GW_WIN_HZ = 12.0        # Golotvin–Williams: Fensterbreite
GW_NSIG = 8.0           # Basislinie, wenn max − min im Fenster ≤ GW_NSIG · σ
GW_DILATE_HZ = 3.0      # Signalbereiche verbreitern
BL_DEG = 5              # Polynomgrad (wie TopSpin ABSG 5)
BL_MODELS = {"poly5": None, "bernstein3": 3}   # Basislinie wählbar (Entscheidung 110): Bernstein 3 = Mnova „Advised“
BL_ITER = 20            # Neuanpassungen ohne Punkte weit neben dem Polynom (Flanken breiter Linien)
BL_RES_NSIG = 3.0
BL_KEEP = 0.1           # in jedem Viertel des Spektrums bleiben ≥ 10 % Basispunkte
BL_WIDEN = 1.0          # danach jeden Signalbereich um seine eigene Breite je Seite verlängern
QUIET_FACTOR = 3.0      # Abschnitt signalfrei, wenn seine Std ≤ 3 × die kleinste
QUIET_MIN = 0.3         # Anteil signalfreier Abschnitte, darunter keine Basislinienkorrektur (σ nicht bestimmbar)
RUN_NSIG = 10.0         # Multiplettbereiche: y > max(RUN_NSIG · σ, RUN_FRAC · Maximum)
RUN_FRAC = 0.001
RUN_GAP_HZ = 1.5        # Bereiche mit kleinerer Lücke zusammenlegen
LINE_FRAC = 0.03        # Linien eines Bereichs: lokale Maxima ≥ LINE_FRAC · Bereichsmaximum
EDGE_FRAC = 0.15        # schwache Randlinien (Verunreinigung, Nachbar), die vor „m“ weggelassen werden dürfen
SPLIT_FRAC = 0.02       # kein Muster: an einem Tal unter SPLIT_FRAC · kleinerer Nachbarlinie teilen
HOYE_WTOL = 0.35        # |Höhe/Einheit − Gewicht|
HOYE_PTOL_HZ = 0.25     # Linienlage (dazu 1.5 Punkte)
J_EQ_HZ = 0.25          # gleiche Kopplungen -> t/q/…
INT_MARGIN_HZ = 5.0     # Integrationsrand außerhalb eines Bereichs
PEAK_NSIG = 5.0         # Peaks (¹³C-Liste) ab 5σ
PEAK_NMS_HZ = 1.0       # ¹³C-Vorschlag bei bestätigter Phase (Entscheidung 113): nur das höchste Maximum in ±1 Hz.
                        # Abnahme 94 echte ¹³C-Sätze: kein SI-Wert verloren (1225 von 1225), Vorschläge −41 %; ohne Spielraum
                        # (±1.25 Hz verlor einen Wert), Prominenz-Filter verloren 3–43 Werte
ACME_GAMMA = 1000.0     # Strafgewicht negativer Punkte (Chen 2002), auf max|S| normiert
REF_WIN = {"1H": 0.25, "13C": 3.0}   # Suchfenster um den Tabellenwert auf der unkalibrierten Achse (ppm)
REF_MIN = 0.02          # Muster-Lösungsmittel: stärkste Musterlinie ≥ 2 % der stärksten Linie im Fenster
BROAD_HZ = 100.0        # Integral einer Linie mit größerer Halbwertsbreite: ±2 % nicht belegt (Hinweis)
FIT_PTOL_HZ = 0.5       # vorgegebenes Muster: jede Linie ein Maximum in ±max(FIT_PTOL_HZ, 2 Punkte)
FIT_HMIN = 0.25         # … jede Linie ≥ 25 % ihrer erwarteten Höhe (bezogen auf die stärkste Linie des Musters)
FIT_TOP = 0.15          # … stärkste Linie des Musters ≥ 15 % des stärksten Maximums im Bereich (Rippel, Wellen)
FIT_AMBIG = 0.5         # mehrdeutig: Lösung mit mehr weggelassenen J > 2 Hz daneben, stärkste Linie ≥ 50 %

LETTER_N = {"d": 1, "t": 2, "q": 3, "quint": 4, "p": 4, "sext": 5, "sept": 6, "hept": 6}
_NAME = {1: "d", 2: "t", 3: "q", 4: "p", 5: "sext", 6: "hept"}   # wie die Gruppen-SI („hept“, „dp“)

# Restsignal: Muster (Gewichte, J in Hz) und Halbbreite (Hz) für den Schwerpunkt, nur für die am Prototyp geprüften
# Lösungsmittel (Schlüssel wie nmr_impurities). J_HD/J_CD sind Lehrbuchwerte, nicht aus Fulmer (nicht doppelt
# abgeschrieben); andere Lösungsmittel: kein Vorschlag, der Nutzer setzt die Referenz.
SOLVENT_PATTERN = {("1H", "CD3CN"): ((1, 2, 3, 2, 1), 2.5), ("1H", "(CD3)2SO"): ((1, 2, 3, 2, 1), 1.9),
                   ("13C", "CDCl3"): ((1, 1, 1), 32.0), ("13C", "C6D6"): ((1, 1, 1), 24.3),
                   ("13C", "CD2Cl2"): ((1, 2, 3, 2, 1), 27.2), ("13C", "CD3CN"): ((1, 3, 6, 7, 6, 3, 1), 20.8),
                   ("13C", "(CD3)2SO"): ((1, 3, 6, 7, 6, 3, 1), 21.0)}
SOLVENT_HW = {("1H", "CDCl3"): 0.0, ("1H", "C6D6"): 1.0, ("1H", "CD2Cl2"): 1.0, ("1H", "CD3CN"): 5.0,
              ("1H", "(CD3)2SO"): 3.8, ("13C", "CDCl3"): 32.0, ("13C", "C6D6"): 24.0, ("13C", "CD2Cl2"): 54.0,
              ("13C", "CD3CN"): 63.0, ("13C", "(CD3)2SO"): 63.0}


# ---------------------------------------------------------------------------- Rauschen, Basislinie
def _segment_std(y):
    out = []
    for s in np.array_split(np.asarray(y, float), 64):
        x = np.arange(s.size)
        out.append(np.std(s - np.polyval(np.polyfit(x, s, 1), x)))
    return np.array(out)


def noise(y):
    """σ: 25. Perzentil der Standardabweichung von 64 linear entzerrten Abschnitten (Nullauffüllung und LB koppeln
    benachbarte Punkte, deshalb keine Differenzen)."""
    return float(np.percentile(_segment_std(y), 25))


def baseline_mask(y, hz_per_pt, sigma=None):
    """Golotvin & Williams, J. Magn. Reson. 2000, 146, 122: Punkt gehört zur Basislinie, wenn max − min im 12-Hz-Fenster
    ≤ 8σ; Signalbereiche um 3 Hz verbreitert. -> bool je Punkt (True = Basislinie)."""
    s = noise(y) if sigma is None else sigma
    w = max(3, int(round(GW_WIN_HZ / hz_per_pt)) | 1)
    v = np.lib.stride_tricks.sliding_window_view(np.pad(y, w // 2, mode="edge"), w)
    return ~_dilate((v.max(1) - v.min(1)) > GW_NSIG * s, int(round(GW_DILATE_HZ / hz_per_pt)))


def _dilate(m, d):
    return np.convolve(m.astype(float), np.ones(2 * d + 1), "same") > 0 if d else m


def bernstein_basis(x, n):
    """Bernstein-Basis vom Grad n auf x ∈ [−1, 1] -> Matrix (Punkte × n + 1): C(n, k) t^k (1 − t)^(n − k), t = (x + 1)/2."""
    t = (np.asarray(x, float) + 1) / 2
    return np.stack([math.comb(n, k) * t ** k * (1 - t) ** (n - k) for k in range(n + 1)], axis=1)


def baseline(y, hz_per_pt, ax=None, exclude=(), model="poly5"):
    """Basislinie = Polynom Grad 5 über die signalfreien Punkte (abweichend von Golotvin–Williams kein stückweises
    Modell, wie TopSpin ABSG 5). Punkte in `exclude` (Bereiche lo–hi in ppm auf `ax`, z. B. Integralbereiche) sind nie
    Basislinie. Danach bis zu BL_ITER-mal: Punkte, die mehr als BL_RES_NSIG · σ neben dem Polynom liegen (Flanken breiter
    Linien), samt 3 Hz Rand herausnehmen und neu anpassen; zuletzt jeden Signalbereich um seine eigene Breite verlängern.
    Beides nur, solange jedes Viertel des Spektrums ≥ BL_KEEP Basispunkte behält (sonst schwingt das Polynom).
    Grenze: sehr breite, flache Linien (200 Hz bei 25σ) verlieren einige Prozent Fläche, weil zerfaserte Flanken unter
    3σ Basislinie bleiben.
    model „bernstein3“: dieselben Punkte, Bernstein-Polynom 3. Grades (Mnovas Vorgabe „Advised“; als Kleinste-Quadrate-
    Anpassung dieselbe Kurve wie ein Polynom 3. Grades, Mnovas Punktwahl ist nicht nachgebaut).
    -> (korrigiertes y, σ, Maske, Meldungen). Ohne Korrektur (y unverändert, Meldung): weniger als QUIET_MIN der
    Abschnitte signalfrei (σ wäre sonst ein Signalwert und das Polynom zöge die Signale ab) oder < 50 Basispunkte."""
    y = np.asarray(y, float)
    known = [] if model in BL_MODELS else [T("b2nmr_bl_unknown", m=model)]   # unbekannte Variante: Standard + Meldung
    sd = _segment_std(y)
    quiet = sd <= QUIET_FACTOR * sd.min()
    if quiet.mean() < QUIET_MIN:
        return y.copy(), float(np.median(sd[quiet])), np.zeros(y.size, bool), [T("b2nmr_bl_dense",
                                                                                   pct=round(100 * quiet.mean()))] + known
    s = float(np.percentile(sd, 25))
    m = baseline_mask(y, hz_per_pt, s)
    if ax is not None:
        ax = np.asarray(ax)
        for lo, hi in exclude:
            m &= ~((ax >= min(lo, hi)) & (ax <= max(lo, hi)))
    x = np.linspace(-1, 1, y.size)
    d = int(round(GW_DILATE_HZ / hz_per_pt))
    bern = bernstein_basis(x, BL_MODELS[model]) if BL_MODELS.get(model) else None

    def fit(mask):
        idx = np.nonzero(mask)[0][::4]
        if idx.size < 50:
            return None
        if bern is not None:
            return y - bern @ np.linalg.lstsq(bern[idx], y[idx], rcond=None)[0]
        return y - np.polynomial.polynomial.polyval(x, np.polynomial.polynomial.polyfit(x[idx], y[idx], BL_DEG))

    def spread(mask):                                     # Polynom braucht Stützpunkte in jedem Viertel
        return min(q.mean() for q in np.array_split(mask, 4)) >= BL_KEEP
    r = fit(m)
    if r is None:
        return y.copy(), noise(y), m, [T("b2nmr_bl_few")] + known
    for _ in range(BL_ITER):
        out = m & (np.abs(r) > BL_RES_NSIG * s)
        new = m & ~_dilate(out, d)
        if not out.any() or not spread(new):
            break
        m, r = new, fit(new)
    # Flanken unter 3σ: jeden Signalbereich um BL_WIDEN seiner Breite verlängern, wenn genug Stützpunkte bleiben
    e = np.diff(np.concatenate([[1], m.astype(int), [1]]))
    wide = m.copy()
    for a, b in zip(np.nonzero(e == -1)[0], np.nonzero(e == 1)[0]):
        k = int(BL_WIDEN * (b - a))
        wide[max(0, a - k):min(y.size, b + k)] = False
    if spread(wide):
        m, r = wide, fit(wide)
    return r, noise(r), m, known


# ---------------------------------------------------------------------------- Phase (nur Vorschlag)
def _acme(r, gamma):
    """Chen, Weng, Goh, Garland, J. Magn. Reson. 2002, 158, 164: Entropie der |1. Ableitung| + γ · Σ R² (R < 0)."""
    d = np.abs(r[2:] - r[:-2])
    h = d / d.sum()
    h = h[h > 0]
    neg = r[r < 0]
    return -np.sum(h * np.log(h)) + gamma * np.sum(neg * neg)


def _simplex(f, x0, step, it=150):
    """Nelder–Mead (Reflexion, Expansion, Kontraktion, Schrumpfen)."""
    pts = [np.array(x0, float)] + [np.array(x0, float) + s for s in step]
    val = [f(p) for p in pts]
    for _ in range(it):
        o = np.argsort(val)
        pts, val = [pts[k] for k in o], [val[k] for k in o]
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < val[0]:
            xe = c + 2 * (c - pts[-1])
            fe = f(xe)
            pts[-1], val[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < val[-2]:
            pts[-1], val[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < val[-1]:
                pts[-1], val[-1] = xc, fc
            else:
                pts = [pts[0] + 0.5 * (p - pts[0]) for p in pts]
                val = [f(p) for p in pts]
        if max(abs(v - val[0]) for v in val) < 1e-9:
            break
    k = int(np.argmin(val))
    return pts[k], val[k]


def autophase(spec):
    """ACME auf dem komplexen Spektrum ohne Phase (`process_1d` mit PHC0 = PHC1 = 0) -> (PHC0, PHC1) in Grad wie procs
    (Phase PHC0 + PHC1 · i/SI). Gitter 15°/30° (Drehpunkt Mitte), Simplex von den vier besten Punkten."""
    sn = np.asarray(spec) / np.abs(spec).max()
    x = np.arange(sn.size) / sn.size - 0.5
    grid = []
    for b in np.arange(-360, 361, 30.0):
        t = sn * np.exp(-1j * np.deg2rad(b) * x)
        for a in np.arange(0, 360, 15.0):
            grid.append((_acme(t.real * np.cos(np.deg2rad(a)) + t.imag * np.sin(np.deg2rad(a)), ACME_GAMMA), a, b))
    grid.sort()
    f = lambda v: _acme((sn * np.exp(-1j * np.deg2rad(v[0] + v[1] * x))).real, ACME_GAMMA)  # noqa: E731
    (a, b), _ = min((_simplex(f, (a, b), [(10, 0), (0, 20)]) for _, a, b in grid[:4]), key=lambda r: r[1])
    return float((a - b / 2) % 360), float(b)


def suggest_phase(spec, procs=None):
    """Phasenvorschlag nur, wenn procs keine Phase hat (PHC0/PHC1 fehlen); sonst None (TopSpins Phase gilt, der Leser
    reproduziert 1r). ACME ist nicht belastbar: immer bestätigen lassen."""
    if procs is not None and all(isinstance(procs.get(k), (int, float)) for k in ("PHC0", "PHC1")):
        return None
    return autophase(spec)


# ---------------------------------------------------------------------------- Achse, Referenz
def axis_uncalibrated(acqus, procs):
    """ppm ohne TopSpin-Kalibrierung (SR = 0, SF = BF1): Trägerfrequenz SFO1 aus acqus, Breite SW_p und SI aus procs."""
    bf, sw, si = acqus["BF1"], procs["SW_p"], procs["SI"]
    off = (acqus["SFO1"] / bf - 1) * 1e6 + 0.5 * sw / bf
    return off - np.arange(si) * sw / (bf * si)


def residual(nucleus, solvent):
    """Tabellenwert des Restsignals (Fulmer 2010, erster gedruckter Wert der Lösungsmittelzeile) -> ppm, sonst None."""
    key = IMP.solvent_key(solvent)
    table, row = {"1H": (IMP.H1, IMP.SOLVENT_ROW["1"]), "13C": (IMP.C13, IMP.SOLVENT_ROW["2"])}.get(nucleus, ((), ""))
    return next((float(r["shift"]) for r in table if r["compound"] == row and r["solvent"] == key), None)


def _maxima(y, i0, i1):
    i0, i1 = max(i0, 1), min(i1, y.size - 2)
    k = np.arange(i0, i1 + 1)
    return k[(y[k] >= y[k - 1]) & (y[k] >= y[k + 1])]


def suggest_reference(y, ax, nucleus, solvent, sf):
    """Restsignal im Fenster ±0.25 ppm (¹H) / ±3 ppm (¹³C) um den Tabellenwert suchen (`ax` unkalibriert).
    -> dict(found = ppm auf `ax`, ref = Tabellenwert, shift = ref − found, warnings) oder dict(found=None,
    warnings=[Grund]). Muster-Lösungsmittel über die Linien des Musters, Singulett-Lösungsmittel: singulettartige
    Linie nächst dem Tabellenwert; Lage = Schwerpunkt. Liegt das Restsignal in einem Signal der Verbindung, ist der
    Vorschlag verschoben; das erkennt nur der Nutzer (eine Warnung aus dem Spektrum allein traf zu selten)."""
    key = IMP.solvent_key(solvent)
    ref = residual(nucleus, solvent)
    if ref is None or (nucleus, key) not in SOLVENT_HW:
        return dict(found=None, ref=ref, warnings=[T("b2nmr_ref_unchecked", solvent=solvent or "–", nuc=nucleus)])
    y, ax = np.asarray(y, float), np.asarray(ax, float)
    step = abs(ax[1] - ax[0])
    sel = np.nonzero(np.abs(ax - ref) <= REF_WIN[nucleus])[0]
    if sel.size < 5:
        return dict(found=None, ref=ref, warnings=[T("b2nmr_ref_outside", ref=ref)])
    pat = SOLVENT_PATTERN.get((nucleus, key))
    if pat is None:
        # singulettartig: ≤ 3 Maxima ≥ 20 % in ±1.5 Hz, nichts ≥ 20 % bei 1.5–4 Hz; ≥ 2 % des Fenstermaximums
        mx = [k for k in _maxima(y, sel[0], sel[-1]) if y[k] >= 0.02 * y[sel].max()]
        allmx = _maxima(y, sel[0] - 200, sel[-1] + 200)
        good = []
        for k in mx:
            dhz = np.abs(allmx - k) * step * sf
            ring = allmx[(dhz > 1.5) & (dhz <= 4.0)]
            if np.sum((dhz <= 1.5) & (y[allmx] >= 0.2 * y[k])) <= 3 and not np.any(y[ring] >= 0.2 * y[k]):
                good.append(k)
        k0 = min(good, key=lambda k: abs(ax[k] - ref)) if good else sel[np.argmax(y[sel])]
    else:
        w, jhz = pat
        tol = max(2, int(0.15 * jhz / sf / step))
        best, cut = (-np.inf, sel[np.argmax(y[sel])]), np.inf
        for k in sorted(_maxima(y, sel[0], sel[-1]), key=lambda k: -y[k])[:200]:
            sc = np.inf
            for n, wk in enumerate(w):
                j = k + int(round((n - (len(w) - 1) / 2) * jhz / sf / step))
                if j - tol < 0 or j + tol >= y.size:          # Musterlinie hinter dem Spektrumrand
                    sc = -np.inf
                    cut = min(cut, abs(ax[k] - ref))
                    break
                sc = min(sc, y[j - tol:j + tol + 1].max() / wk)
            if sc > best[0]:
                best = (sc, k)
        # abgeschnittenes Muster näher am Tabellenwert als der Gewinner: das Restsignal liegt am Rand, der Gewinner ist
        # etwas anderes (z. B. Wasser) -> kein Vorschlag. (Täler zwischen den Linien zu verlangen geht nicht: echte
        # DMSO-d5-Quintetts sind oft unaufgelöst.)
        if best[0] == -np.inf or cut < abs(ax[best[1]] - ref):
            return dict(found=None, ref=ref, warnings=[T("b2nmr_ref_outside", ref=ref)])
        if best[0] * max(w) < REF_MIN * y[sel].max():                # nur Rauschen/Flanken passen zum Muster
            return dict(found=None, ref=ref, warnings=[T("b2nmr_ref_weak", ref=ref)])
        k0 = best[1]
    c = float(ax[k0])
    hw = (SOLVENT_HW[(nucleus, key)] + (1.5 if nucleus == "1H" else 5.0)) / sf
    for _ in range(3):
        m = np.abs(ax - c) <= hw
        wt = np.clip(y[m], 0, None)
        if wt.sum() <= 0:
            break
        c = float(np.sum(ax[m] * wt) / wt.sum())
    return dict(found=c, ref=ref, shift=ref - c, warnings=[])


# ---------------------------------------------------------------------------- Peaks, Integrale
def _vertex(y, i):
    a, b, c = y[i - 1], y[i], y[i + 1]
    den = a - 2 * b + c
    d = 0.5 * (a - c) / den if den else 0.0
    return i + d, b - 0.25 * (a - c) * d


def _ppm(ax, q):
    return float(np.interp(q, np.arange(len(ax)), ax))


def peaks(y, ax, thr, exclude=(), nms=0):
    """Lokale Maxima über `thr` (z. B. PEAK_NSIG · σ), Lage als Parabelscheitel -> [(ppm, Höhe)] in Achsenreihenfolge;
    `exclude` = [(lo, hi)] ppm (z. B. Lösungsmittel). nms > 0: nur Maxima, die in ±nms Punkten die höchsten sind."""
    y = np.asarray(y, float)
    i = np.nonzero((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:]) & (y[1:-1] > thr))[0] + 1
    if nms > 0 and len(i):
        i = i[[y[k] >= y[max(0, k - nms):k + nms + 1].max() for k in i]]
    out = []
    for k in i:
        q, h = _vertex(y, k)
        x = _ppm(ax, q)
        if not any(lo <= x <= hi for lo, hi in exclude):
            out.append((x, float(h)))
    return out


def integral_ranges(ranges, sf, margin_hz=INT_MARGIN_HZ):
    """Bereiche (lo, hi) ppm um `margin_hz` erweitern; überlappende Ränder an der Mitte der Lücke teilen.
    -> [(lo, hi)] in derselben Reihenfolge."""
    mg = margin_hz / sf
    ranges = [sorted(r) for r in ranges]
    rr = [[lo - mg, hi + mg, lo, hi] for lo, hi in ranges]
    o = sorted(range(len(rr)), key=lambda k: rr[k][2])
    for a, b in zip(o[:-1], o[1:]):
        if rr[a][1] > rr[b][0]:
            mid = 0.5 * (rr[a][3] + rr[b][2])
            rr[a][1], rr[b][0] = mid, mid
    if any(r[0] >= r[1] for r in rr):                         # verschachtelt oder überlappend
        raise ValueError(T("b2nmr_int_overlap"))
    return [(r[0], r[1]) for r in rr]


def integrate(y, ax, ranges):
    """Summe der Punkte je Bereich (lo, hi) ppm × Punktabstand -> numpy-Feld (Einheit: Intensität · ppm)."""
    ax = np.asarray(ax)
    step = abs(ax[1] - ax[0])
    return np.array([float(np.asarray(y)[(ax >= min(lo, hi)) & (ax <= max(lo, hi))].sum() * step) for lo, hi in ranges])


def integral_notes(y, ax, ranges, sf):
    """Hinweise je Integralbereich: stärkste Linie breiter als BROAD_HZ (Halbwertsbreite) -> Genauigkeit ±2 % nicht
    belegt (Basislinie nimmt flache Flanken mit). -> [Text oder ""] in der Reihenfolge der Bereiche."""
    y, ax = np.asarray(y, float), np.asarray(ax, float)
    hzpt = abs(ax[1] - ax[0]) * sf
    out = []
    for lo, hi in ranges:
        i0, i1 = sorted(int(np.argmin(np.abs(ax - v))) for v in (lo, hi))
        k = i0 + int(np.argmax(y[i0:i1 + 1]))
        wide = i1 > i0 and _fwhm_hz(y, k, 0, y.size - 1, hzpt) > BROAD_HZ
        out.append(T("b2nmr_int_broad", hz=f"{BROAD_HZ:g}") if wide else "")
    return out


def normalise(integrals, k, n_h):
    """Integrale so skalieren, dass Bereich k n_h Kerne hat (Normierung durch den Nutzer)."""
    integrals = np.asarray(integrals, float)
    if not np.isfinite(integrals[k]) or integrals[k] <= 0:
        raise ValueError(T("b2nmr_norm_zero"))
    return integrals * (n_h / integrals[k])


# ---------------------------------------------------------------------------- Multipletts
def _runs(y, thr, gap_pts):
    m = np.asarray(y) > thr
    e = np.diff(np.concatenate([[0], m.astype(int), [0]]))
    out = []
    for s, t in zip(np.nonzero(e == 1)[0], np.nonzero(e == -1)[0] - 1):
        if out and s - out[-1][1] <= gap_pts:
            out[-1][1] = t
        else:
            out.append([s, t])
    return out


def hoye(pos_hz, h, ptol):
    """Erste Ordnung nach Hoye, Hanson, Vyvyan, J. Org. Chem. 1994, 59, 4096: ganzzahlige Liniengewichte mit Summe 2ⁿ,
    J-Baum von der ersten Linie. -> (Klasse, J absteigend, Linien in Hz) oder None."""
    pos_hz, h = np.asarray(pos_hz, float), np.asarray(h, float)
    o = np.argsort(pos_hz)
    pos_hz, h = pos_hz[o], h[o]
    if pos_hz.size == 1:
        return "s", [], pos_hz
    for n in range(1, 9):
        u = h.sum() / 2 ** n
        w = np.round(h / u).astype(int)
        if w.min() < 1 or w.sum() != 2 ** n or np.max(np.abs(h / u - w)) > HOYE_WTOL:
            continue
        comp = np.repeat(pos_hz, w)
        expl, js = comp[:1].copy(), []
        while expl.size < comp.size:
            rem = list(comp)
            for e in expl:                                    # Multimengen-Differenz comp − expl
                k = int(np.argmin(np.abs(np.array(rem) - e)))
                if abs(rem[k] - e) > ptol:
                    break
                rem.pop(k)
            else:
                jj = min(rem) - comp[0]
                if jj <= ptol:
                    break
                js.append(jj)
                expl = np.sort(np.concatenate([expl, expl + jj]))
                continue
            break
        if expl.size != comp.size or np.max(np.abs(np.sort(expl) - comp)) > ptol:
            continue
        groups = []
        for jj in sorted(js, reverse=True):
            if groups and abs(groups[-1][0] - jj) <= J_EQ_HZ:
                groups[-1][1].append(jj)
            else:
                groups.append([jj, [jj]])
        if any(len(g[1]) > 6 for g in groups):
            return None
        name = "".join(_NAME[len(g[1])] for g in groups)
        if class_letters(name) is None:                   # „dsext“, „thept“ …: im Bericht nicht druckbar -> „m“
            return None
        return name, [float(np.mean(g[1])) for g in groups], pos_hz
    return None


def _multiplet(y, ax, a, b, sf, hzpt, out, depth=0):
    p = np.concatenate([[y[a]], y[a:b + 1], [y[b]]])         # Randpunkte doppelt: Maxima am Bereichsrand zählen
    k = np.nonzero((p[1:-1] > p[:-2]) & (p[1:-1] >= p[2:]) & (p[1:-1] > 0))[0] + 1
    ln = [(a + q - 1, v) for q, v in (_vertex(p, i) for i in k)]
    if not ln:
        return
    vmax = max(v for _, v in ln)
    ln = [(q, v) for q, v in ln if v >= LINE_FRAC * vmax]
    pos = [_ppm(ax, q) * sf for q, _ in ln]
    hh = [v for _, v in ln]
    ptol = HOYE_PTOL_HZ + 1.5 * hzpt
    res = hoye(pos, hh, ptol)
    for drop in ((0,), (-1,), (0, -1), (0, 1), (-1, -2)):      # schwache Randlinien weglassen, bevor „m“
        if res or len(ln) - len(drop) < 1:
            break
        if all(hh[d] < EDGE_FRAC * vmax for d in drop):
            keep = [k for k in range(len(ln)) if k not in {d % len(ln) for d in drop}]
            res = hoye([pos[k] for k in keep], [hh[k] for k in keep], ptol)
    if res is None and len(ln) > 1 and depth < 8:
        best = (np.inf, None)                                 # kein Muster: am tiefsten Tal teilen, wenn tief genug
        for (q1, v1), (q2, v2) in zip(ln[:-1], ln[1:]):
            i1, i2 = int(round(q1)), int(round(q2))
            if i2 - i1 < 2:
                continue
            k = i1 + int(np.argmin(y[i1:i2 + 1]))
            if y[k] / min(v1, v2) < best[0]:
                best = (y[k] / min(v1, v2), k)
        if best[0] < SPLIT_FRAC:
            _multiplet(y, ax, a, best[1], sf, hzpt, out, depth + 1)
            _multiplet(y, ax, best[1] + 1, b, sf, hzpt, out, depth + 1)
            return
    lo, hi = float(ax[b]), float(ax[a])
    if res:
        name, js, lines = res
        shift = float((lines.min() + lines.max()) / 2 / sf)  # Mitte des Musters (äußere Linien)
    else:
        name, js, lines, shift = "m", [], np.array(pos), (lo + hi) / 2
    out.append(dict(lo=lo, hi=hi, shift=shift, mult=name, J=js, lines=sorted(float(p / sf) for p in lines),
                    height=float(vmax)))


def multiplets(y, ax, sf, sigma=None):
    """Automatische Multipletts (Vorschlag): Bereiche über max(10σ, 0.1 % Maximum), Linien ≥ 3 %, Hoye erster Ordnung,
    sonst am tiefen Tal teilen, sonst „m“. -> [dict(lo, hi, shift, mult, J, lines, height)], shift = Mitte des Musters
    bzw. Bereichsmitte bei „m“; J in Hz absteigend."""
    y, ax = np.asarray(y, float), np.asarray(ax, float)
    s = noise(y) if sigma is None else sigma
    hzpt = abs(ax[1] - ax[0]) * sf
    out = []
    for a, b in _runs(y, max(RUN_NSIG * s, RUN_FRAC * y.max()), int(RUN_GAP_HZ / hzpt)):
        if b - a >= 2:
            _multiplet(y, ax, a, b, sf, hzpt, out)
    return out


def class_letters(mult):
    """„dt“ -> [d, t]; „p“/„hept“ -> [p]/[hept]; s/m/unbekannt -> None. Gemischte Klassen nur aus d/t/q/p, höchstens fünf
    Buchstaben (Vokabular des Berichts, `nmr_report`)."""
    if mult in LETTER_N:
        return [mult]
    return list(mult) if re.fullmatch(r"[dtqp]{1,5}", mult or "") else None


def _pattern_sets(lets, js):
    """Linien erster Ordnung (Hz relativ zur Mitte, Gewichte) je Zuordnung J ↔ Buchstabe; Linien < 0.5 Hz auseinander
    zusammengelegt (Gewichte addiert). -> [(Lagen, Gewichte)]."""
    out = []
    for perm in set(itertools.permutations(range(len(lets)))):
        pos, w = np.zeros(1), np.ones(1)
        for let, k in zip(lets, perm):
            n = LETTER_N[let]
            pos = (pos[:, None] + ((np.arange(n + 1) - n / 2) * js[k])[None, :]).ravel()
            w = (w[:, None] * np.array([math.comb(n, i) for i in range(n + 1)], float)[None, :]).ravel()
        o = np.argsort(pos)
        pos, w = pos[o], w[o]
        cut = np.nonzero(np.diff(pos) > 0.5)[0] + 1
        mp = np.array([g.mean() for g in np.split(pos, cut)])
        mw = np.array([g.sum() for g in np.split(w, cut)])
        if not any(len(mp) == len(q) and np.allclose(mp, q) for q, _ in out):
            out.append((mp, mw))
    return out


def pattern_lines(mult, js):
    """Linienlagen erster Ordnung (Hz relativ zur Mitte) für jede Zuordnung J ↔ Buchstabe (dt/td … ist im Text nicht
    festgelegt); zusammenfallende Linien (< 0.5 Hz) zusammengelegt. -> [numpy-Feld]."""
    lets = class_letters(mult)
    if not lets or len(lets) != len(js):
        return []
    return [p for p, _ in _pattern_sets(lets, list(js))]


def _fwhm_hz(y, k, i0, i1, hzpt, rise=np.inf):
    """Halbwertsbreite (Hz) des Maximums k, nur innerhalb i0…i1 gesucht. Steigt y auf dem Weg nach außen vor der halben
    Höhe wieder um mehr als `rise` an (Tal zu einer Nachbarlinie, Welle), ist die Breite nicht bestimmbar: 0."""
    half = y[k] / 2
    width = 0
    for step in (-1, 1):
        i, low = k, y[k]
        while i0 < i < i1 and y[i] > half:
            i += step
            low = min(low, y[i])
            if y[i] > low + rise:
                return 0.0
        width += abs(i - k)
    return width * hzpt


def _match(obs, hgt, sets, lo_hz, hi_hz, tol, top):
    """Alle Lagen eines Musters im Bereich: jede Linie ein Maximum in ±tol, Höhen passen zu den Gewichten (jede
    ≥ FIT_HMIN × erwartet, gemessen an der stärksten Linie des Musters), stärkste Linie ≥ FIT_TOP × stärkstes Maximum im
    Bereich (sonst Rippel/Basislinienwellen). -> [(Höhe der stärksten Linie, Abweichung², Indizes der Linien)]."""
    sols = []
    for pos, w in sets:
        if len(pos) > len(obs):
            continue
        for c in np.arange(lo_hz - pos.min(), hi_hz - pos.max() + 1e-9, 0.1):
            d = np.abs((c + pos)[:, None] - obs[None, :])
            j = d.argmin(1)
            dm = d[np.arange(len(pos)), j]
            if not (dm <= tol).all() or len(set(j)) != len(pos):
                continue
            h = hgt[j]
            r = int(np.argmax(h))
            if h[r] < FIT_TOP * top or np.any(h / h[r] < FIT_HMIN * w / w[r]):
                continue
            sols.append((float(h[r]), float((dm ** 2).sum()), tuple(sorted(j))))
    return sols


def fit_pattern(y, ax, lo, hi, sf, mult, js, thr):
    """Vorgegebenes Muster (Klasse + J in Hz, Nutzerentscheidung) im Bereich lo–hi ppm suchen: Mitte im Raster 0.1 Hz,
    jede Linie braucht ein Maximum > thr in ±max(0.5 Hz, 2 Punkte), Höhen wie erster Ordnung (`_match`), alle Linien im
    Bereich. Zusätzlich Durchläufe, in denen die kleinsten J (Linien nicht trennbar) weggelassen sind; δ dann aus den äußeren aufgelösten Linien, diese J stehen in `unmeasured`
    („eingegeben, nicht gemessen“). Ein J darf nur weg, wenn es nicht größer als die Halbwertsbreite jeder Musterlinie
    ist. Es gewinnt die Lösung mit den wenigsten weggelassenen J, darunter die mit der stärksten Linie. Mehrdeutig: eine
    andere Lösung > 2 Hz daneben mit gleich vielen weggelassenen J (unabhängig von der Höhe) oder mit mehr weggelassenen J
    und ≥ FIT_AMBIG der Höhe. -> (dict(shift = Mitte des Musters, lines, unmeasured, notes, dazu die Eingabe lo, hi,
    mult, J für `nmr_report.signal_of`), None) oder (None, Grund). Das Ergebnis ist ein Vorschlag (Status im Signal)."""
    js = [float(j) for j in js]
    lets = class_letters(mult)
    if not lets or len(lets) != len(js):
        return None, T("b2nmr_fit_class", mult=mult or "–", n=len(js))
    y, ax = np.asarray(y, float), np.asarray(ax, float)
    lo, hi = sorted((lo, hi))
    i0, i1 = sorted(int(np.argmin(np.abs(ax - v))) for v in (lo, hi))
    mx = _maxima(y, i0, i1)
    mx = mx[y[mx] > thr]
    if not mx.size:
        return None, T("b2nmr_fit_lines")
    obs = np.array([_ppm(ax, _vertex(y, k)[0]) for k in mx]) * sf
    hgt = y[mx]
    hzpt = abs(ax[1] - ax[0]) * sf
    tol0 = max(FIT_PTOL_HZ, 2 * hzpt)
    fw = np.array([_fwhm_hz(y, int(k), i0, i1, hzpt, thr) for k in mx])   # Halbwertsbreite je Maximum
    order = sorted(range(len(js)), key=lambda i: js[i])
    sols = []                                             # alle Durchläufe sammeln, dann vergleichen
    for nd in range(len(js) + 1):
        drop = order[:nd]
        keep = [i for i in range(len(js)) if i not in drop]
        sets = _pattern_sets([lets[i] for i in keep], [js[i] for i in keep]) if keep else [(np.zeros(1), np.ones(1))]
        tol = tol0 + 0.5 * sum(LETTER_N[lets[i]] * js[i] for i in drop)
        for h, q, idx in _match(obs, hgt, sets, lo * sf, hi * sf, tol, hgt.max()):
            if nd and js[drop[-1]] > fw[list(idx)].min():   # weggelassenes J muss in jeder Musterlinie verschwinden
                continue
            sols.append((h, nd, q, idx))
    if sols:
        mid = lambda o: (obs[list(o[3])].min() + obs[list(o[3])].max()) / 2   # noqa: E731
        nd0 = min(o[1] for o in sols)                     # weniger weggelassene J werden nie überstimmt
        best = min((o for o in sols if o[1] == nd0), key=lambda o: (-o[0], o[2]))
        if any(abs(mid(o) - mid(best)) > 2 and (o[1] == nd0 or o[0] >= FIT_AMBIG * best[0]) for o in sols):
            return None, T("b2nmr_fit_ambiguous", mult=mult)
        lines = obs[list(best[3])]
        keep = order[best[1]:]
        # gemessen ist ein J nur, wenn seine Linien im Muster getrennt geblieben sind: legt `_pattern_sets` sie zusammen
        # (< 0.5 Hz), hat das Muster ohne dieses J nicht weniger Linien -> nicht gemessen (unabhängig von der Breite)
        merged = [i for i in keep if min(len(p) for p, _ in _pattern_sets([lets[j] for j in keep],
                                                                           [js[j] for j in keep]))
                  <= max((len(p) for p, _ in _pattern_sets([lets[j] for j in keep if j != i],
                                                           [js[j] for j in keep if j != i]))
                         if len(keep) > 1 else [1])]
        un = sorted((js[i] for i in order[:best[1]] + merged), reverse=True)
        notes = [T("b2nmr_fit_unresolved", j=", ".join(f"{j:g}" for j in un))] if un else []
        return dict(shift=float(mid(best) / sf), lines=sorted(float(v / sf) for v in lines), unmeasured=un,
                    notes=notes, lo=lo, hi=hi, mult=mult, J=js), None
    return None, T("b2nmr_fit_none", mult=mult)


def first_order_width(mult, js):
    """Breite eines Musters erster Ordnung in Hz (Σ nₖ·Jₖ); unbekannte Klasse: Σ J."""
    lets = class_letters(mult)
    if lets and len(lets) == len(js):
        return float(sum(LETTER_N[k] * j for k, j in zip(lets, js)))
    return float(sum(js))


def round_h(x):
    """nH auf ganze Kerne (Integral × Normierung)."""
    if not np.isfinite(x):
        raise ValueError(T("b2nmr_norm_zero"))
    return int(math.floor(x + 0.5))


# ---------------------------------------------------------------------------- Unified Scale (X-Kerne)
# Ξ in % (Harris et al., Pure Appl. Chem. 2001, 73, 1795, Tab. 1/2/4; Nachdruck auremn.org): zweifach unabhängig
# abgeschrieben und zeichengleich (Audit 2026-11-15, ref19f + xi2). Nur diese Werte; alle übrigen Kerne nur einfach
# gelesen -> nicht hier. 19F/13C zusätzlich über das BF1-Verhältnis echter acqus bestätigt (1e-8).
XI = {"1H": 100.000000, "13C": 25.145020, "19F": 94.094011, "31P": 40.480742, "29Si": 19.867187,
      "15N": 10.136767, "11B": 32.083974}
XI_15N_NH3 = 10.132912           # ¹⁵N auf der NH3-Skala (flüssig, extern; Tab. 4), Wahl des Nutzers
XI_RATIO_TOL = 2e-5              # BF1_X/BF1_H muss Ξ/100 auf 2e-5 treffen (gleicher Magnet; 4/9 echte Paare scheiterten)


def unified_shift(nucleus, bf_x, bf_h, ref_h, xi=None):
    """Verschiebung der unkalibrierten X-Achse (SF = BF1_X) auf die Unified Scale über ein referenziertes ¹H desselben
    Magneten: ν(TMS) = BF1_H·(1 − ref_H·1e-6) (ref_H = bestätigte Verschiebung der ¹H-Achse), ν_ref(X) = Ξ/100·ν(TMS),
    Verschiebung = (BF1_X/ν_ref − 1)·1e6 ppm (Skalenfehler BF1_X/ν_ref − 1 ≈ 1e-6 relativ: vernachlässigt).
    ValueError mit Meldung, wenn Ξ nicht doppelt belegt ist oder BF1_X/BF1_H nicht zu Ξ passt (anderer Magnet)."""
    xi = XI.get(nucleus) if xi is None else xi
    if xi is None:
        raise ValueError(T("nmr_xi_none", nuc=nucleus))
    if abs(bf_x / bf_h - xi / 100) > XI_RATIO_TOL:
        raise ValueError(T("nmr_xi_ratio", r=f"{bf_x / bf_h:.7f}", xi=f"{xi / 100:.7f}"))
    nu_ref = xi / 100 * bf_h * (1 - ref_h * 1e-6)
    return (bf_x / nu_ref - 1) * 1e6
