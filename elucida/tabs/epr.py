"""elucida/tabs/epr.py - CW-EPR: Bruker BES3T (ESR5000/ESRStudio, Elexsys), Magnettech-MS400-Text, EasySpin-Simulationen.

Verarbeitung einer Messung (Reihenfolge): Dunkelspektrum abziehen (hell − k·dunkel, auf das Feldraster der
Messung interpoliert) -> Basislinie (Polynom an den Rändern des Sweeps oder in gewählten Bereichen) ->
Bereiche ausblenden (z. B. scharfes Radikalsignal) -> Glätten (gleitender Mittelwert über ein Feldintervall)
-> optional normieren. Simulationen: Feldverschiebung, Skalierung von Hand oder per kleinsten Quadraten an
eine Messung angepasst. Felder intern in mT.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from elucida.core import uvvis as core
from elucida.tabs import base as TABS
from elucida.app.i18n import T
from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.style import HINT_CSS, make_form
from elucida.formats.epr import (read_bes3t, read_ascii, read_any, parse_easyspin)  # noqa: E402,F401  (Leser in elucida/formats)

MHZ_PER_CM = 29979.2458                       # 1 cm⁻¹ in MHz
MU_B_H = 13.996245                             # µ_B/h in GHz/T  -> g = ν / (µ_B/h · B)


# ----------------------------------------------------------------------------
# Lesen
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# EasySpin-Parameter
# ----------------------------------------------------------------------------


def zfs_summary(params) -> str | None:
    """D und E (EasySpin: MHz) in cm⁻¹ und MHz; None ohne Sys.D."""
    d = params.get("Sys.D")
    if not isinstance(d, list) or not d:
        return None
    D, E = zfs_DE(d)
    return (f"D = {D / MHZ_PER_CM:.4f} cm⁻¹ ({D:.0f} MHz), |E| = {abs(E) / MHZ_PER_CM:.4f} cm⁻¹ "
            f"({abs(E):.0f} MHz), E/D = {abs(E / D) if D else 0:.3f}")


def zfs_DE(d):
    """EasySpin Sys.D: [D], [D E] oder Hauptwerte [Dx Dy Dz] -> (D, E) (D = Dz − (Dx + Dy)/2, E = (Dx − Dy)/2)."""
    if len(d) >= 3:
        return d[2] - (d[0] + d[1]) / 2.0, (d[0] - d[1]) / 2.0
    return d[0], (d[1] if len(d) > 1 else 0.0)


# ----------------------------------------------------------------------------
# Verarbeitung
# ----------------------------------------------------------------------------
def ranges(text):
    """'330-340, 480–485' -> [(330, 340), (480, 485)] (mT). Dezimalkomma ('330,5-340,5'), wenn sich der Text nur
    so vollständig in Bereiche zerlegen lässt."""
    def parse(t):
        out, ok = [], True
        for part in t.replace(";", ",").split(","):
            m = re.match(r"^\s*([-+]?\d*\.?\d+)\s*[-–—]\s*([-+]?\d*\.?\d+)\s*$", part.replace("−", "-"))
            if m:
                a, b = float(m.group(1)), float(m.group(2))
                out.append((min(a, b), max(a, b)))
            elif part.strip():
                ok = False
        return out, ok
    text = str(text)
    out, ok = parse(text)
    if not ok and re.search(r"\d,\d", text):
        alt, ok2 = parse(re.sub(r"(\d),(\d)", r"\1.\2", text))
        if ok2:
            return alt
    return out


def baseline(B, I, order=1, edge=0.05, regions=None):
    """Polynom der Ordnung order an signalfreie Punkte: gewählte Bereiche oder die äußeren edge-Anteile."""
    if order < 0:
        return np.zeros_like(I)
    if regions:
        m = np.zeros(len(B), bool)
        for a, b in regions:
            m |= (B >= a) & (B <= b)
    else:
        n = max(3, int(edge * len(B)))
        m = np.zeros(len(B), bool)
        m[:n] = m[-n:] = True
    m &= np.isfinite(I)
    if m.sum() <= order + 1:
        return np.zeros_like(I)
    x0, s = B.mean(), (np.ptp(B) or 1.0)
    c = np.polyfit((B[m] - x0) / s, I[m], order)
    return np.polyval(c, (B - x0) / s)


def smooth_points(B, width_mT):
    """Punktzahl des gleitenden Mittels (ungerade, höchstens der Sweep); < 3 = keine Glättung."""
    if not width_mT or len(B) < 3:
        return 0
    step = float(np.median(np.diff(B))) or 1.0
    n = min(int(round(width_mT / step)) | 1, len(B) - 1 + len(B) % 2)
    return n if n >= 3 else 0


def smooth(B, I, width_mT):
    """Gleitender Mittelwert über width_mT (ungerade Punktzahl), NaN-sicher."""
    n = smooth_points(B, width_mT)
    if not n:
        return I
    ok = np.isfinite(I).astype(float)
    k = np.ones(n)
    num = np.convolve(np.nan_to_num(I), k, "same")
    den = np.convolve(ok, k, "same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[~np.isfinite(I)] = np.nan
    return out


def decimate(B, I, max_points=6000):
    """Für die Abbildung auf höchstens max_points mitteln (60 000 Punkte pro Spektrum sind üblich)."""
    if len(B) <= max_points:
        return B, I
    f = int(np.ceil(len(B) / max_points))
    n = len(B) // f * f
    with np.errstate(invalid="ignore"):
        return B[:n].reshape(-1, f).mean(1), np.nanmean(I[:n].reshape(-1, f), 1)


def double_integral(B, I, window=None):
    """Doppelintegral eines Ableitungsspektrums: erst integrieren (Absorption), deren Basislinie linear zwischen
    den Fenster-Rändern (je 5 %) abziehen, dann erneut integrieren. NaN-Werte zählen als 0."""
    B, I = np.asarray(B, float), np.nan_to_num(np.asarray(I, float))
    if window:
        m = (B >= window[0]) & (B <= window[1])
        B, I = B[m], I[m]
    if len(B) < 10:
        return float("nan")
    a = np.concatenate([[0.0], np.cumsum(0.5 * (I[1:] + I[:-1]) * np.diff(B))])
    n = max(2, len(B) // 20)
    x0, x1 = B[:n].mean(), B[-n:].mean()
    y0, y1 = a[:n].mean(), a[-n:].mean()
    a = a - (y0 + (y1 - y0) * (B - x0) / (x1 - x0))
    return float(np.sum(0.5 * (a[1:] + a[:-1]) * np.diff(B)))


def peak_to_peak(B, I, window=None):
    B, I = np.asarray(B, float), np.asarray(I, float)
    if window:
        m = (B >= window[0]) & (B <= window[1])
        B, I = B[m], I[m]
    return float(np.nanmax(I) - np.nanmin(I)) if np.isfinite(I).any() else float("nan")


def gauss_lin_fit(B, I, center, c_lo, c_hi, width=8.5, w_lo=3.0, w_hi=50.0, max_iter=200):
    """Gauß + lineare Basislinie an ein Merkmal (wie im MATLAB-Skript der Arbeitsgruppe):
    y = p1·exp(−(x − p2)²/p3) + p4·x + p5, Grenzen c_lo ≤ p2 ≤ c_hi, w_lo ≤ p3 ≤ w_hi (mT²).
    Startwerte: Gerade durch je 10 Randpunkte, Amplitude = Minimum − Randmittel. -> (p, Modellwerte).
    Das Zentrum bleibt innerhalb der Messpunkte (3 % Abstand zum Rand): Ein Gauß außerhalb der Daten hätte eine
    beliebige Amplitude (bei Spektren ohne Signal sonst Ausreißer)."""
    ok = np.isfinite(I)
    B, I = np.asarray(B, float)[ok], np.asarray(I, float)[ok]
    margin = 0.03 * float(np.ptp(B))
    c_lo, c_hi = max(c_lo, float(B.min()) + margin), min(c_hi, float(B.max()) - margin)
    center = min(max(center, c_lo), c_hi)
    if len(B) > 4000:
        f = int(np.ceil(len(B) / 4000))
        B, I = B[::f], I[::f]
    xe = np.r_[B[:10], B[-10:]]
    ye = np.r_[I[:10], I[-10:]]
    m, b0 = np.polyfit(xe, ye, 1)
    amp = float(I.min() - np.mean([I[:10].mean(), I[-10:].mean()]))
    p = np.array([amp, center, width, m, b0], float)
    lo = np.array([-np.inf, c_lo, w_lo, -np.inf, -np.inf])
    hi = np.array([np.inf, c_hi, w_hi, np.inf, np.inf])

    def model(q, x=B):
        return q[0] * np.exp(-((x - q[1]) ** 2) / q[2]) + q[3] * x + q[4]
    r = I - model(p)
    cost, lam = float(r @ r), 1e-3
    scale = np.maximum(np.abs(p), 1e-6)
    for _ in range(max_iter):
        J = np.empty((len(B), 5))
        for k in range(5):
            dp = np.zeros(5)
            dp[k] = 1e-6 * scale[k]
            J[:, k] = (model(np.clip(p + dp, lo, hi)) - model(np.clip(p - dp, lo, hi))) / (2 * dp[k])
        A_ = J.T @ J
        g_ = J.T @ r
        improved = False
        for _ in range(10):
            try:
                step = np.linalg.solve(A_ + lam * np.diag(np.diag(A_) + 1e-12), g_)
            except np.linalg.LinAlgError:
                break
            q = np.clip(p + step, lo, hi)
            r2 = I - model(q)
            c2 = float(r2 @ r2)
            if c2 < cost:
                p, r, cost, lam, improved = q, r2, c2, lam / 3, True
                break
            lam *= 5
        if not improved or np.all(np.abs(step) < 1e-9 * scale):
            break
    return p, model(p)


R_GAS = 8.314462618                    # J mol⁻¹ K⁻¹ (wie EasySpin molgas)


def decay_model(T, A, Ea, beta, time=None):
    """Zerfall erster Ordnung: I = exp(−A·∫ exp(−Ea/RT) dt), I(erster Punkt) = 1. Integral per Trapezregel über die
    Messpunkte: mit time (s) über die gemessene Zeit (beliebiges Temperaturprogramm, auch Haltephasen/Abkühlen),
    sonst wie cumtrapz im MATLAB-Skript über T bei konstanter Heizrate β (K/s), dt = dT/β."""
    T = np.asarray(T, float)
    f = np.exp(-Ea / (R_GAS * T))
    x = np.asarray(time, float) if time is not None else T / beta
    integral = np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * np.diff(x))])
    return np.exp(-A * integral)


def fit_decay(T, I, beta, start=(40e3, np.log(1e15)), max_iter=400, norm="script", time=None):
    """E_a und ln A. norm='script': wie das MATLAB-Skript (min-max-normierte Intensitäten, konstante Heizrate,
    lsqnonlin auf sqrt(|Modell − Messung|), also L1-Norm; Intervalle formal aus inv(JᵀJ)·resnorm/n – unterschätzt die
    Unsicherheit). norm='lsq' (Standard, Audit P6 R1): gemessene Intensitäten ohne Min-Max, Startintensität I0 linear
    mitbestimmt (Min-Max verschob E_a bei unvollständigem Zerfall und Rauschen an den Extremen), Integral über die
    Messzeit time, wenn gegeben; kleinste Quadrate, Kovarianz s²·inv(JᵀJ) der projizierten Residuen,
    s² = SSR/(n − 3), t-Quantil. -> dict(Ea, lnA, A, I0, ci_Ea, ci_lnA, cov, t, resnorm, corr)."""
    T, I = np.asarray(T, float), np.asarray(I, float)
    lsq = norm != "script"
    tm = time if lsq else None

    def model(q):
        return decay_model(T, np.exp(q[1]), q[0], beta, tm)

    def amp(m):
        den = float(m @ m)
        return float(m @ I) / den if den > 0 else 0.0

    def res(q):
        m = model(q)
        if lsq:
            return amp(m) * m - I
        return np.sqrt(np.abs(m - I))
    # Startwert per Raster: für jedes E_a wird ln A so gewählt, dass das Modell bei der gemessenen Halbwertstemperatur
    # 0.5 ergibt (eindeutig). Umgeht die fast vollständige Korrelation E_a/ln A, an der ein direkter Start scheitert.
    p = np.array(start, float)
    if lsq:                                          # relativ zum Anfang; ohne Halbwert: Stand am Ende der Serie
        rel = I / (np.max(I[:3]) or 1.0)
        L = 0.5 if (rel <= 0.5).any() else float(rel[-1])
        below = np.flatnonzero(rel <= L)
        x = np.asarray(tm, float) if tm is not None else T / beta
        if 0 < L < 0.98 and len(below) and below[0] > 0:
            k = below[0]
            frac = (rel[k - 1] - L) / (rel[k - 1] - rel[k]) if rel[k - 1] != rel[k] else 1.0
            best = None
            for Ea in np.arange(5e3, 300e3, 500.0):
                f = np.exp(-Ea / (R_GAS * T))
                cum = np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * np.diff(x))])
                integ = float(cum[k - 1] + frac * (cum[k] - cum[k - 1]))
                if integ <= 0 or not np.isfinite(integ):
                    continue
                q = np.array([Ea, np.log(-np.log(L) / integ)])
                with np.errstate(over="ignore", invalid="ignore"):
                    c = float(np.nansum(res(q) ** 2))
                if best is None or c < best[0]:
                    best = (c, q)
            if best is not None:
                p = best[1]
    else:
        below = np.flatnonzero(I <= 0.5)
        if len(below) and below[0] > 0:
            k = below[0]
            T50 = float(np.interp(0.5, [I[k], I[k - 1]], [T[k], T[k - 1]]))
            best = None
            for Ea in np.arange(5e3, 300e3, 500.0):
                Tg = np.linspace(T[0], T50, 200)
                fg = np.exp(-Ea / (R_GAS * Tg)) / beta
                integ = float(np.sum(0.5 * (fg[1:] + fg[:-1]) * np.diff(Tg)))
                if integ <= 0 or not np.isfinite(integ):
                    continue
                q = np.array([Ea, np.log(np.log(2.0) / integ)])
                with np.errstate(over="ignore", invalid="ignore"):
                    c = float(np.nansum(res(q) ** 2))
                if best is None or c < best[0]:
                    best = (c, q)
            if best is not None:
                p = best[1]
    with np.errstate(over="ignore", invalid="ignore"):
        r = res(p)
    cost, lam = float(r @ r), 1e-3
    h = np.array([10.0, 1e-3])
    for _ in range(max_iter):
        J = np.column_stack([(res(p + dv) - res(p - dv)) / (2 * dv[k])
                             for k, dv in enumerate((np.array([h[0], 0]), np.array([0, h[1]])))])
        A_ = J.T @ J
        g_ = J.T @ r
        improved = False
        for _ in range(12):
            try:
                step = np.linalg.solve(A_ + lam * np.diag(np.diag(A_) + 1e-12), -g_)
            except np.linalg.LinAlgError:
                break
            r2 = res(p + step)
            c2 = float(r2 @ r2)
            if c2 < cost:
                p, r, cost, lam, improved = p + step, r2, c2, lam / 3, True
                break
            lam *= 5
        if not improved or (abs(step[0]) < 1e-3 and abs(step[1]) < 1e-8):
            break
    J = np.column_stack([(res(p + dv) - res(p - dv)) / (2 * dv[k])
                         for k, dv in enumerate((np.array([h[0], 0]), np.array([0, h[1]])))])
    try:
        if not lsq:
            cov = np.linalg.inv(J.T @ J) * cost / len(I)
            z = 1.96
        else:
            from elucida.core import uvvis as core                    # eigenes t-Quantil wie im ε-Fit
            dof = max(1, len(I) - 3)                                  # E_a, ln A und I0
            cov = np.linalg.inv(J.T @ J) * cost / dof
            z = core.t_quantile(0.975, dof)
        se = np.sqrt(np.abs(np.diag(cov)))
        corr = float(cov[0, 1] / (se[0] * se[1])) if se.all() else float("nan")
    except np.linalg.LinAlgError:
        cov, se, z, corr = np.full((2, 2), np.nan), np.array([np.nan, np.nan]), 1.96, float("nan")
    return {"Ea": float(p[0]), "lnA": float(p[1]), "A": float(np.exp(p[1])), "cov": cov, "t": z,
            "I0": amp(model(p)) if lsq else 1.0,
            "ci_Ea": (float(p[0] - z * se[0]), float(p[0] + z * se[0])),
            "ci_lnA": (float(p[1] - z * se[1]), float(p[1] + z * se[1])), "resnorm": cost, "corr": corr}


def decay_band(T, r, beta, time=None):
    """Band (Faktor r["t"] wie die Intervalle) um das Modell aus der Kovarianz von (E_a, ln A), linear fortgepflanzt:
    sd = √(J·cov·Jᵀ). Die Randwerte der Einzelintervalle taugen dafür nicht (Korrelation ≈ 1). -> (unten, oben)."""
    T = np.asarray(T, float)
    m = decay_model(T, r["A"], r["Ea"], beta, time)
    J = np.column_stack([(decay_model(T, np.exp(r["lnA"] + d[1]), r["Ea"] + d[0], beta, time)
                          - decay_model(T, np.exp(r["lnA"] - d[1]), r["Ea"] - d[0], beta, time)) / (2 * max(d))
                         for d in ((10.0, 0.0), (0.0, 1e-3))])
    sd = np.sqrt(np.abs(np.einsum("ij,jk,ik->i", J, np.asarray(r["cov"], float), J)))
    return m - r["t"] * sd, m + r["t"] * sd


def measured_at(meta):
    """Aufnahmezeit aus DATE/TIME (BES3T: MM/DD/YY) -> datetime oder None."""
    import datetime as dt
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(f"{meta.get('date', '')} {meta.get('time', '')}".strip(), fmt)
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------------------
# Isotrope S = ½-Simulation (erste Ordnung) und Fit
# ----------------------------------------------------------------------------
NUCLEAR_SPIN = {"1H": 0.5, "2H": 1.0, "D": 1.0, "13C": 0.5, "14N": 1.0, "15N": 0.5, "17O": 2.5, "19F": 0.5,
                "29Si": 0.5, "31P": 0.5, "33S": 1.5, "35Cl": 1.5, "37Cl": 1.5, "79Br": 1.5, "81Br": 1.5,
                "51V": 3.5, "55Mn": 2.5, "57Fe": 0.5, "59Co": 3.5, "61Ni": 1.5, "63Cu": 1.5, "65Cu": 1.5,
                "107Ag": 0.5, "109Ag": 0.5, "117Sn": 0.5, "119Sn": 0.5, "195Pt": 0.5, "199Hg": 0.5}
MHZ_PER_MT_FREE = 28.02495             # g_e·µ_B/h in MHz/mT (Umrechnung a [mT] <-> A [MHz] für g ≈ 2.0023)


def _nuc_tokens(part):
    """'2x14N 0,65' / '2 × 14N 0.65' -> ['2', '14N', '0.65']."""
    return part.replace(",", ".").replace("×", " ").replace("x", " ", 1 if re.match(r"^\s*\d+x", part) else 0).split()


def parse_nuclei(text):
    """'2 14N 0.65; 4 1H 0.32' -> [(2, 1.0, 0.65), (4, 0.5, 0.32)] (Anzahl äquivalenter Kerne, Kernspin, a in mT).
    Auch 'I=1' statt Isotop möglich: '2 I=1 0.65'."""
    out = []
    for part in re.split(r"[;\n]+", str(text)):
        tok = _nuc_tokens(part)
        if len(tok) < 3:
            continue
        try:
            n = int(tok[0])
            a = float(tok[2])
        except ValueError:
            continue
        nuc = tok[1]
        if nuc.lower().startswith("i="):
            I = float(nuc[2:])
        elif nuc in NUCLEAR_SPIN:
            I = NUCLEAR_SPIN[nuc]
        else:
            continue
        out.append((n, I, a))
    return out


def nuclei_names(text):
    """Kernbezeichnungen in der Reihenfolge von parse_nuclei: '2 14N 0.65; 4 1H 0.32' -> ['14N', '1H']."""
    return [_nuc_tokens(part)[1] for part in re.split(r"[;\n]+", str(text)) if parse_nuclei(part)]


def unknown_nuclei(text):
    """Nicht lesbare Einträge (z. B. '2 14n 0.65') – der Fit würde sie sonst still weglassen."""
    return [part.strip() for part in re.split(r"[;\n]+", str(text)) if part.strip() and not parse_nuclei(part)]


def band_name(mw_GHz):
    """Mikrowellenband aus der Frequenz (X ≈ 9–10 GHz, Q ≈ 34 GHz …); None, wenn unbekannt."""
    for lo, hi, name in ((1, 2, "L"), (2, 4, "S"), (8, 12, "X"), (12, 18, "K"), (26, 40, "Q"), (75, 110, "W")):
        if mw_GHz and lo <= mw_GHz < hi:
            return name
    return None


def nucleus_html(nuc):
    m = re.fullmatch(r"(\d+)([A-Z][a-z]?)", nuc)
    return f"<sup>{m.group(1)}</sup>{m.group(2)}" if m else nuc.replace("I=", "I = ")


def nuclei_with_a(text, new_a):
    """Kopplungen im Text ersetzen, Isotopnamen und Reihenfolge behalten: ('2 14N 0.6', [0.65]) -> '2 14N 0.6500'."""
    out, k = [], 0
    for part in re.split(r"[;\n]+", str(text)):
        tok = _nuc_tokens(part)
        if len(tok) >= 3 and k < len(new_a) and parse_nuclei(part):
            tok[2] = f"{new_a[k]:.4f}"
            k += 1
            out.append(" ".join(tok[:3]))
    return "; ".join(out)


def stick_spectrum(groups):
    """Linienlagen (Verschiebung in mT relativ zur Mitte) und Gewichte für Gruppen äquivalenter Kerne
    (erste Ordnung: Gesamt-M jeder Gruppe binomial/multinomial verteilt)."""
    pos, w = np.array([0.0]), np.array([1.0])
    for n, I, a in groups:
        m = np.arange(-I, I + 0.5, 1.0)                      # Einzelkern: 2I+1 Werte, gleich gewichtet
        dist = np.array([1.0])
        for _ in range(int(n)):
            dist = np.convolve(dist, np.ones(len(m)))
        M = np.arange(len(dist)) - (len(dist) - 1) / 2.0     # Gesamt-M in Einheiten von 1
        p2 = (pos[:, None] + a * M[None, :]).ravel()
        w2 = (w[:, None] * dist[None, :]).ravel()
        keep = w2 > 1e-12 * w2.max()
        pos, w = p2[keep], w2[keep]
    return pos, w / w.sum()


def derivative_line(x, lw_pp, lorentz):
    """Erste Ableitung einer Pseudo-Voigt-Linie mit Peak-zu-Peak-Breite lw_pp (mT), Lorentz-Anteil 0…1."""
    lw = max(float(lw_pp), 1e-6)
    sg = lw / 2.0                                            # Gauß: Abstand der Extrema = 2σ
    g = -x / sg ** 2 * np.exp(-0.5 * (x / sg) ** 2) / (sg * np.sqrt(2 * np.pi))
    gam = lw * np.sqrt(3) / 2.0                              # Lorentz: Abstand der Extrema = 2Γ/√3
    lo = -2 * x * gam / np.pi / (x ** 2 + gam ** 2) ** 2
    return (1 - lorentz) * g + lorentz * lo


def iso_spectrum(B, mw_GHz, g, groups, lw_pp, lorentz=0.0):
    """CW-Ableitungsspektrum (erste Harmonische) eines isotropen S = ½-Systems in erster Ordnung."""
    B0 = mw_GHz / (MU_B_H * g) * 1000.0                      # mT
    pos, w = stick_spectrum(groups)
    y = np.zeros_like(B, dtype=float)
    for p0, w0 in zip(B0 + pos, w):                         # Schleife statt Matrix: spart Speicher
        y += w0 * derivative_line(B - p0, lw_pp, lorentz)
    return y


def fit_iso(B, I, mw_GHz, g, groups, lw_pp, lorentz=0.0, vary_lorentz=False, max_iter=60):
    """Levenberg-Marquardt für g, Kopplungen a_k, Linienbreite (und Lorentz-Anteil); Amplitude linear.
    -> dict(g, groups, lw, lorentz, amp, r2, rms)."""
    ok = np.isfinite(I)
    B, I = np.asarray(B, float)[ok], np.asarray(I, float)[ok]
    if len(B) > 4000:                                        # schneller fitten, Linienform bleibt erhalten
        f = int(np.ceil(len(B) / 4000))
        B, I = B[::f], I[::f]
    n_a = len(groups)
    g, groups = _coarse_start(B, I, mw_GHz, g, groups, lw_pp, lorentz)

    def model(p):
        gg = [(n, Ii, p[2 + k]) for k, (n, Ii, _) in enumerate(groups)]
        lor = min(max(p[2 + n_a], 0.0), 1.0) if vary_lorentz else lorentz
        return iso_spectrum(B, mw_GHz, p[0], gg, abs(p[1]), lor)

    def residual(p):
        y = model(p)
        den = float(y @ y)
        amp = float(y @ I) / den if den > 0 else 0.0
        return I - amp * y, amp
    p = np.array([g, lw_pp] + [a for (_, _, a) in groups] + ([lorentz] if vary_lorentz else []), float)
    steps = np.array([1e-5, 1e-3] + [1e-3] * n_a + ([1e-2] if vary_lorentz else []))
    r, amp = residual(p)
    cost, lam = float(r @ r), 1e-3
    for _ in range(max_iter):
        J = np.empty((len(r), len(p)))
        for k in range(len(p)):
            dp = np.zeros_like(p)
            dp[k] = steps[k]
            J[:, k] = (residual(p + dp)[0] - r) / steps[k]
        A = J.T @ J
        grad = J.T @ r
        improved = False
        for _ in range(8):
            try:
                delta = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), -grad)
            except np.linalg.LinAlgError:
                break
            r2, amp2 = residual(p + delta)
            c2 = float(r2 @ r2)
            if c2 < cost:
                p, r, amp, cost, lam, improved = p + delta, r2, amp2, c2, lam / 3, True
                break
            lam *= 5
        if not improved or np.all(np.abs(delta) < steps * 1e-3):
            break
    ss = float(np.sum((I - I.mean()) ** 2))
    return {"g": float(p[0]), "lw": float(abs(p[1])),
            "groups": [(n, Ii, float(p[2 + k])) for k, (n, Ii, _) in enumerate(groups)],
            "lorentz": float(min(max(p[2 + n_a], 0), 1)) if vary_lorentz else float(lorentz), "amp": amp,
            "r2": 1 - cost / ss if ss > 0 else float("nan"), "rms": float(np.sqrt(cost / len(I)))}


def _coarse_start(B, I, mw_GHz, g, groups, lw_pp, lorentz):
    """Grobsuche vor dem LM-Fit: Feldlage (g) und gemeinsamer Faktor der Kopplungen auf einem Raster, mit
    absichtlich breiten Linien (glatte Zielfunktion). Verhindert lokale Minima bei ungenauen Startwerten."""
    span = float(B.max() - B.min()) or 1.0
    lw_s = max(lw_pp, span / 150.0)
    best = (-np.inf, g, groups)
    centers = np.arange(B.min() + 0.05 * span, B.max() - 0.05 * span, lw_s / 3.0)
    for fa in ((0.8, 0.9, 1.0, 1.1, 1.25) if groups else (1.0,)):
        gg = [(n, Ii, a * fa) for (n, Ii, a) in groups]
        for Bc in centers:
            y = iso_spectrum(B, mw_GHz, g_value(mw_GHz, Bc), gg, lw_s, lorentz)
            ny = float(np.sqrt(y @ y))
            score = float(y @ I) / ny if ny > 0 else -np.inf
            if score > best[0]:
                best = (score, g_value(mw_GHz, Bc), gg)
    return best[1], best[2]


def center_g(B, I, mw_GHz):
    """Startwert für g: Schwerpunkt der Absorption (integriertes Ableitungsspektrum)."""
    ok = np.isfinite(I)
    B, I = np.asarray(B, float)[ok], np.asarray(I, float)[ok]
    a = np.concatenate([[0.0], np.cumsum(0.5 * (I[1:] + I[:-1]) * np.diff(B))])
    a = a - np.linspace(a[0], a[-1], len(a))
    a = np.abs(a)
    Bc = float(np.sum(B * a) / np.sum(a)) if a.sum() > 0 else float(np.mean(B))
    return g_value(mw_GHz, Bc)


def combine_components(B_t, I_t, comps):
    """Gemeinsame lineare Anpassung mehrerer Komponenten (je (B, I)) an die Messung (B_t, I_t).
    -> Gewichte (Liste). NaN-Bereiche der Messung zählen nicht."""
    cols = [np.interp(B_t, b, i, left=0.0, right=0.0) for b, i in comps]
    ok = np.isfinite(I_t)
    if not cols or ok.sum() < len(cols) + 2:
        return [1.0] * len(cols)
    M = np.column_stack([c[ok] for c in cols])
    w, *_ = np.linalg.lstsq(M, I_t[ok], rcond=None)
    return [float(v) for v in w]


def b_res(mw_GHz, g):
    return mw_GHz / (MU_B_H * g) * 1000.0


def g_value(mw_GHz, B_mT):
    return mw_GHz / (MU_B_H * B_mT / 1000.0)


# ----------------------------------------------------------------------------
# EPR-Tab
# ----------------------------------------------------------------------------
def _labels(text):
    """'Z⁻@122, Y⁺@400' -> [('Z⁻', 122.0), ('Y⁺', 400.0)] (Feld in der Achseneinheit)."""
    out = []
    for part in str(text).split(","):
        if "@" in part:
            name, _, pos = part.rpartition("@")
            try:
                out.append((name.strip(), float(pos.strip().replace("\u2212", "-"))))
            except ValueError:
                pass
    return out


class EPRTab(TABS.FigureTab):
    STATE_KEY = "epr"
    GUIDE, GUIDE_ACTION = "epr", ("guide_add", "add_exp")
    CAP_FIELDS = ("species", "solvent", "conc")
    SI_CAPTION = "EPR spectra of {name}."
    X_RANGE = (0.0, 20000.0, 1, 1.0)
    XRANGE_TEXT = "epr_xrange"
    RESET_KEEP = ("entries", "calib_uid", "calib_g", "T_offset", "ref_freq")   # Spektren/Simulationen, Kalibrierung
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=300.0, x_max=360.0, ymax=0.0, entries=[], unit="mT",
                         bl_order=1, bl_edge=5.0, bl_regions="", exclude="", smooth=0.0, normalize=True,
                         stack=False, gap=1.2, labels="", show_params=False, y_axis="no_numbers",
                         mode="spectra", int_window="", int_method="double", int_x="time", int_curie=False,
                         show_sum=True, show_residual=False, calib_uid=None, calib_g=2.0055,
                         ref_freq=0.0, T_offset=0.0, int_center=0.0, kin_fit=False, kin_norm="lsq",
                         cap_species="", cap_solvent="", cap_conc="")


    def arrange(self):
        super().arrange()
        # Fit-Ergebnis + „SI-Text kopieren“ als Reiter neben der Abbildung wie in CV (nicht mitten in „Darstellung“)
        self.to_right(STYLE.split_group(self.group_titled("epr_display"), self.lbl_info, None, T("tab_results"), n=2),
                      T("tab_results"))
        g = STYLE.split_group(self.group_titled("epr_display"), self.ed_int_window, self.cb_curie, T("grp_intensity"))
        self.fold(g, "intensity", ("int_window", "int_method", "int_x", "int_center", "kin_fit", "kin_norm",
                                   "int_curie"))
    def build_controls(self):
        st = self.st
        g = QGroupBox(T("epr_entries"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        tips = {T("epr_add_sim"): T("epr_add_sim_tip"), T("epr_add_iso"): T("epr_add_iso_tip")}
        for txt, fn in ((T("epr_add_exp"), self.add_exp), (T("epr_add_sim"), self.add_sim),
                        (T("epr_add_iso"), self.add_iso),
                        ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)), (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            if txt in tips:
                b.setToolTip(tips[txt])
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), T("ov_type"), "T [K]"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self.table_edited)
        self.table.itemSelectionChanged.connect(self.show_details)
        v.addWidget(self.table)
        self.lv.addWidget(g)

        self.det = QGroupBox(T("ov_details"))
        f = make_form(self.det)
        row = QHBoxLayout()
        self.cmb_dark = QComboBox()
        self.cmb_dark.setToolTip(T("epr_dark_tip"))
        self.sp_dark_k = QDoubleSpinBox(decimals=3, minimum=0, maximum=100, singleStep=0.05, value=1.0)
        row.addWidget(self.cmb_dark, 1)
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_dark_k)
        self.lbl_dark = QLabel(T("epr_dark"))
        f.addRow(self.lbl_dark, row)
        self.btn_dark_all = QPushButton(T("epr_dark_all"))
        self.btn_dark_all.setToolTip(T("epr_dark_all_tip"))
        self.btn_dark_all.clicked.connect(self.dark_for_all)
        f.addRow("", self.btn_dark_all)
        self.cmb_fit = QComboBox()
        self.cmb_fit.setToolTip(T("epr_fit_tip"))
        self.lbl_fit = QLabel(T("epr_fit_to"))
        f.addRow(self.lbl_fit, self.cmb_fit)
        row = QHBoxLayout()
        self.sp_scale = QDoubleSpinBox(decimals=4, minimum=-1e9, maximum=1e9, singleStep=0.1, value=1.0)
        self.sp_shift = QDoubleSpinBox(decimals=3, minimum=-100, maximum=100, singleStep=0.05, value=0.0,
                                       suffix=" mT")
        self.sp_scale.setToolTip(T("epr_scale_tip"))
        self.sp_shift.setToolTip(T("epr_shift_tip"))
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_scale)
        row.addWidget(QLabel(T("epr_shift")))
        row.addWidget(self.sp_shift)
        self.lbl_scale = QLabel(T("epr_scale"))
        f.addRow(self.lbl_scale, row)
        row = QHBoxLayout()
        self.lbl_params = QLabel("–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        b1.clicked.connect(self.choose_params)
        b2.clicked.connect(lambda: self.set_params(None))
        for w_ in (self.lbl_params, b1, b2):
            row.addWidget(w_, 1 if w_ is self.lbl_params else 0)
        self.lbl_params_row = QLabel(T("epr_params"))
        f.addRow(self.lbl_params_row, row)
        self.w_iso = QGroupBox(T("epr_iso"))
        fi = make_form(self.w_iso)
        row = QHBoxLayout()
        self.sp_g = QDoubleSpinBox(decimals=5, minimum=1.0, maximum=10.0, singleStep=0.0005, value=2.0023)
        self.sp_lw = QDoubleSpinBox(decimals=3, minimum=0.001, maximum=50, singleStep=0.01, value=0.1, suffix=" mT")
        for w_ in (QLabel("g"), self.sp_g, QLabel(T("epr_lw")), self.sp_lw):
            row.addWidget(w_)
        fi.addRow(row)
        row = QHBoxLayout()
        self.sp_lor = QDoubleSpinBox(decimals=2, minimum=0, maximum=1, singleStep=0.1, value=0.0)
        self.cb_fit_lor = QCheckBox(T("epr_fit_lor"))
        for w_ in (QLabel(T("epr_lorentz")), self.sp_lor, self.cb_fit_lor):
            row.addWidget(w_)
        row.addStretch(1)
        fi.addRow(row)
        self.ed_nuclei = QLineEdit()
        self.ed_nuclei.setPlaceholderText(T("epr_nuclei_ph"))
        self.ed_nuclei.setToolTip(T("epr_nuclei_tip"))
        fi.addRow(T("epr_nuclei"), self.ed_nuclei)
        self.btn_fit = QPushButton(T("epr_fit_btn"))
        self.btn_fit.clicked.connect(self.fit_current)
        fi.addRow(self.btn_fit)
        self.lbl_fit = QLabel("")
        self.lbl_fit.setWordWrap(True)
        self.lbl_fit.setTextInteractionFlags(Qt.TextSelectableByMouse)
        fi.addRow(self.lbl_fit)
        f.addRow(self.w_iso)
        for w_ in (self.sp_g, self.sp_lw, self.sp_lor):
            w_.valueChanged.connect(self.detail_changed)
        self.cb_fit_lor.toggled.connect(self.detail_changed)
        self.ed_nuclei.editingFinished.connect(self.detail_changed)
        self.lbl_meta = QLabel("")
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_meta.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_meta)
        for w_ in (self.sp_dark_k, self.sp_scale, self.sp_shift):
            w_.valueChanged.connect(self.detail_changed)
        for w_ in (self.cmb_dark, self.cmb_fit):
            w_.currentIndexChanged.connect(self.detail_changed)
        self.lv.addWidget(self.det)

        g = QGroupBox(T("epr_processing"))
        f = make_form(g)
        row = QHBoxLayout()
        self.sp_bl_order = QSpinBox(minimum=-1, maximum=5, value=st["bl_order"])
        self.sp_bl_order.setSpecialValueText(T("off"))
        self.sp_bl_edge = QDoubleSpinBox(decimals=1, minimum=1, maximum=45, singleStep=1, value=st["bl_edge"],
                                         suffix=" %")
        row.addWidget(self.sp_bl_order)
        row.addWidget(QLabel(T("epr_bl_edge")))
        row.addWidget(self.sp_bl_edge)
        f.addRow(T("epr_bl_order"), row)
        self.ed_bl_regions = QLineEdit(st["bl_regions"])
        self.ed_bl_regions.setPlaceholderText(T("epr_regions_ph"))
        self.ed_bl_regions.setToolTip(T("epr_bl_regions_tip"))
        f.addRow(T("epr_bl_regions"), self.ed_bl_regions)
        self.ed_exclude = QLineEdit(st["exclude"])
        self.ed_exclude.setPlaceholderText(T("epr_regions_ph"))
        self.ed_exclude.setToolTip(T("epr_exclude_tip"))
        f.addRow(T("epr_exclude"), self.ed_exclude)
        self.sp_smooth = QDoubleSpinBox(decimals=2, minimum=0, maximum=50, singleStep=0.05, value=st["smooth"],
                                        suffix=" mT")
        self.sp_smooth.setSpecialValueText(T("off"))
        f.addRow(T("epr_smooth"), self.sp_smooth)
        row = QHBoxLayout()
        self.sp_ref_freq = QDoubleSpinBox(decimals=4, minimum=0, maximum=500, singleStep=0.1, value=st["ref_freq"],
                                          suffix=" GHz")
        self.sp_ref_freq.setSpecialValueText(T("off"))
        self.sp_ref_freq.setToolTip(T("epr_ref_freq_tip"))
        self.sp_T_offset = QDoubleSpinBox(decimals=2, minimum=-50, maximum=50, singleStep=0.5, value=st["T_offset"],
                                          suffix=" K")
        self.sp_T_offset.setToolTip(T("epr_T_offset_tip"))
        row.addWidget(self.sp_ref_freq)
        row.addWidget(QLabel(T("epr_T_offset")))
        row.addWidget(self.sp_T_offset)
        f.addRow(T("epr_ref_freq"), row)
        row = QHBoxLayout()
        self.cmb_calib = QComboBox()
        self.cmb_calib.setToolTip(T("epr_calib_tip"))
        self.sp_calib_g = QDoubleSpinBox(decimals=5, minimum=1.0, maximum=10.0, singleStep=0.0001, value=st["calib_g"])
        self.sp_calib_g.setToolTip(T("epr_calib_tip"))
        row.addWidget(self.cmb_calib, 1)
        row.addWidget(QLabel("g_lit"))
        row.addWidget(self.sp_calib_g)
        f.addRow(T("epr_calib"), row)
        self.lv.addWidget(g)

        g = QGroupBox(T("epr_display"))
        f = make_form(g)
        self.cmb_unit = QComboBox()
        for u in ("mT", "G"):
            self.cmb_unit.addItem(u, u)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["unit"])))
        f.addRow(T("epr_unit"), self.cmb_unit)
        self.cb_norm = QCheckBox(T("epr_normalize"))
        self.cb_norm.setChecked(st["normalize"])
        f.addRow(self.cb_norm)
        row = QHBoxLayout()
        self.cb_stack = QCheckBox(T("ov_stack"))
        self.cb_stack.setChecked(st["stack"])
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0, maximum=1e6, singleStep=0.1, value=st["gap"])
        row.addWidget(self.cb_stack)
        row.addWidget(QLabel(T("ov_gap")))
        row.addWidget(self.sp_gap)
        row.addStretch(1)
        f.addRow(row)
        self.cmb_yaxis = QComboBox()
        for key in ("numbers", "no_numbers", "off"):
            self.cmb_yaxis.addItem(T("yaxis_" + key), key)
        self.cmb_yaxis.setCurrentIndex(max(0, self.cmb_yaxis.findData(st["y_axis"])))
        f.addRow(T("ov_yaxis"), self.cmb_yaxis)
        self.ed_labels = QLineEdit(st["labels"])
        self.ed_labels.setPlaceholderText(T("epr_labels_ph"))
        self.ed_labels.setToolTip(T("epr_labels_tip"))
        f.addRow(T("epr_labels"), self.ed_labels)
        self.cmb_mode = QComboBox()
        for key in ("spectra", "intensity"):
            self.cmb_mode.addItem(T("epr_mode_" + key), key)
        self.cmb_mode.setCurrentIndex(max(0, self.cmb_mode.findData(st["mode"])))
        f.addRow(T("sec_mode"), self.cmb_mode)
        self.ed_int_window = QLineEdit(st["int_window"])
        self.ed_int_window.setPlaceholderText(T("epr_int_window_ph"))
        self.ed_int_window.setToolTip(T("epr_int_window_tip"))
        f.addRow(T("epr_int_window"), self.ed_int_window)
        row = QHBoxLayout()
        self.cmb_int_method = QComboBox()
        for key in ("double", "pp", "gauss"):
            self.cmb_int_method.addItem(T("epr_int_" + key), key)
        self.cmb_int_method.setToolTip(T("epr_int_method_tip"))
        self.cmb_int_method.setCurrentIndex(max(0, self.cmb_int_method.findData(st["int_method"])))
        self.cmb_int_x = QComboBox()
        for key in ("time", "T", "index"):
            self.cmb_int_x.addItem(T("epr_x_" + key), key)
        self.cmb_int_x.setCurrentIndex(max(0, self.cmb_int_x.findData(st["int_x"])))
        row.addWidget(self.cmb_int_method, 1)
        row.addWidget(QLabel(T("epr_against")))
        row.addWidget(self.cmb_int_x, 1)
        f.addRow(T("epr_int_method"), row)
        self.sp_int_center = QDoubleSpinBox(decimals=1, minimum=0, maximum=20000, singleStep=0.5,
                                            value=st["int_center"], suffix=" mT")
        self.sp_int_center.setSpecialValueText(T("auto"))
        f.addRow(T("epr_int_center"), self.sp_int_center)
        row = QHBoxLayout()
        self.cb_kin = QCheckBox(T("epr_kin_fit"))
        self.cb_kin.setToolTip(T("epr_kin_tip"))
        self.cb_kin.setChecked(st["kin_fit"])
        self.cmb_kin_norm = QComboBox()
        for key in ("lsq", "script"):                     # Standard: kleinste Quadrate (belastbares Intervall)
            self.cmb_kin_norm.addItem(T("epr_kin_" + key), key)
        self.cmb_kin_norm.setCurrentIndex(max(0, self.cmb_kin_norm.findData(st["kin_norm"])))
        self.cmb_kin_norm.setToolTip(T("epr_kin_norm_tip"))
        row.addWidget(self.cb_kin)
        row.addWidget(self.cmb_kin_norm, 1)
        f.addRow(row)
        self.cb_curie = QCheckBox(T("epr_curie"))
        self.cb_curie.setToolTip(T("epr_curie_tip"))
        self.cb_curie.setChecked(st["int_curie"])
        f.addRow(self.cb_curie)
        row = QHBoxLayout()
        self.cb_sum = QCheckBox(T("epr_show_sum"))
        self.cb_sum.setChecked(st["show_sum"])
        self.cb_res = QCheckBox(T("epr_show_residual"))
        self.cb_res.setChecked(st["show_residual"])
        row.addWidget(self.cb_sum)
        row.addWidget(self.cb_res)
        row.addStretch(1)
        f.addRow(row)
        self.cb_params = QCheckBox(T("epr_show_params"))
        self.cb_params.setChecked(st["show_params"])
        f.addRow(self.cb_params)
        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.lbl_info)
        f.addRow(self.methods_button())
        self.lv.addWidget(g)
        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export
        for w_ in (self.sp_bl_order, self.sp_bl_edge, self.sp_smooth, self.sp_gap):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_norm, self.cb_stack, self.cb_params, self.cb_curie, self.cb_sum, self.cb_res):
            w_.toggled.connect(self.changed)
        self.cmb_calib.currentIndexChanged.connect(self.changed)
        self.sp_calib_g.valueChanged.connect(self.changed)
        for w_ in (self.sp_ref_freq, self.sp_T_offset, self.sp_int_center):
            w_.valueChanged.connect(self.changed)
        self.cb_kin.toggled.connect(self.changed)
        self.cmb_kin_norm.currentIndexChanged.connect(self.changed)
        for w_ in (self.cmb_unit, self.cmb_yaxis, self.cmb_mode, self.cmb_int_method, self.cmb_int_x):
            w_.currentIndexChanged.connect(self.changed)
        for ed in (self.ed_bl_regions, self.ed_exclude, self.ed_labels, self.ed_int_window):
            ed.editingFinished.connect(self.changed)
        self.fill_table()
        self.show_details()

    def collect(self):
        self.st.update(unit=self.cmb_unit.currentData(), bl_order=self.sp_bl_order.value(),
                       bl_edge=self.sp_bl_edge.value(), bl_regions=self.ed_bl_regions.text().strip(),
                       exclude=self.ed_exclude.text().strip(), smooth=self.sp_smooth.value(),
                       normalize=self.cb_norm.isChecked(), stack=self.cb_stack.isChecked(), gap=self.sp_gap.value(),
                       y_axis=self.cmb_yaxis.currentData(), labels=self.ed_labels.text().strip(),
                       show_params=self.cb_params.isChecked(), mode=self.cmb_mode.currentData(),
                       int_window=self.ed_int_window.text().strip(), int_method=self.cmb_int_method.currentData(),
                       int_x=self.cmb_int_x.currentData(), int_curie=self.cb_curie.isChecked(),
                       show_sum=self.cb_sum.isChecked(), show_residual=self.cb_res.isChecked(),
                       calib_uid=self.cmb_calib.currentData(), calib_g=self.sp_calib_g.value(),
                       ref_freq=self.sp_ref_freq.value(), T_offset=self.sp_T_offset.value(),
                       int_center=self.sp_int_center.value(), kin_fit=self.cb_kin.isChecked(),
                       kin_norm=self.cmb_kin_norm.currentData())

    # -- Einträge ------------------------------------------------------------------
    def data(self, path):
        return self.cache(("epr", path), lambda: read_any(path))

    def spectrum(self, e):
        d = self.data(e["file"])
        return d[min(e.get("slice", 0), len(d) - 1)]

    def axis_mw(self, e):
        """Frequenz der Feldachse einer Messung nach processed(): ν_ref, wenn skaliert wird, sonst ν der Datei."""
        mw = self.spectrum(e)["meta"].get("mw_GHz") if e else None
        return (self.st.get("ref_freq") or mw) if mw else None

    def _new(self, kind, path, k=0, n=1):
        d = self.data(path)[k]
        name = Path(path).stem if n == 1 else f"{Path(path).stem} [{k + 1}]"
        return {"uid": uuid.uuid4().hex[:8], "kind": kind, "file": path, "slice": k, "label": name,
                "color": "#000000" if kind == "exp" else "#e8238a", "visible": True, "dark": None, "dark_k": 1.0,
                "fit_to": None, "scale": 1.0, "shift": 0.0, "params": None, "T": d["meta"].get("T_K")}

    def _pick(self, title, flt):
        if not self.main.ensure_project():
            return []
        ps, _ = QFileDialog.getOpenFileNames(self, title, self.main.settings.value("last_dir", ""), flt)
        return ps

    def add_exp(self):
        ps = self._pick(T("epr_add_exp"), "EPR (*.dsc *.DSC *.DTA *.txt *.asc *.csv);;" + T("flt_all"))
        seen = set()
        for p in ps:
            stem = str(Path(p).with_suffix(""))
            if stem in seen:                               # .dsc und .DTA derselben Messung nur einmal
                continue
            seen.add(stem)
            try:
                if Path(p).suffix.lower() in (".dsc", ".dta"):       # Partner unter einem gemeinsamen Namen
                    parts, have = [Path(p)], {Path(p).suffix.lower()}
                    for x in (".dsc", ".DSC", ".DTA", ".dta", ".YGF", ".ygf", ".xml"):
                        if Path(stem + x).exists() and x.lower() not in have:
                            parts.append(Path(stem + x))
                            have.add(x.lower())
                    p = PRJ.import_group(self.main.project_dir, parts, PRJ.data_sub(self.STATE_KEY))[0]
                else:
                    p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                d = self.data(p)
            except Exception as ex:
                self.main.error(str(ex))
                continue
            for k in range(len(d)):
                self.st["entries"].append(self._new("exp", p, k, len(d)))
        self.fill_table()
        self.timer.start()

    def add_sim(self):
        for p in self._pick(T("epr_add_sim"), "ASCII (*.txt *.asc *.dat *.csv);;" + T("flt_all")):
            try:
                p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                self.data(p)
            except Exception as ex:
                self.main.error(str(ex))
                continue
            e = self._new("sim", p)
            exp = [x for x in self.st["entries"] if x["kind"] == "exp"]
            e["fit_to"] = exp[-1]["uid"] if exp else None
            self.st["entries"].append(e)
        self.fill_table()
        self.timer.start()

    def add_iso(self):
        """Eigene isotrope S = ½-Simulation; Startwert g aus dem Schwerpunkt der zugeordneten Messung."""
        exp = [x for x in self.st["entries"] if x["kind"] == "exp" and x["visible"]]
        cur = self.current()
        target = cur if (cur and cur["kind"] == "exp") else (exp[-1] if exp else None)
        if target is None:
            return self.main.error(T("epr_iso_need_exp"))
        e = {"uid": uuid.uuid4().hex[:8], "kind": "iso", "file": None, "label": f"S = ½ ({target['label']})",
             "color": "#e8238a", "visible": True, "fit_to": target["uid"], "g": 2.0023, "lw": 0.1, "lorentz": 0.0,
             "fit_lorentz": False, "nuclei": "", "fit": None, "T": None}
        mw = self.axis_mw(target)
        if mw:
            B, I = self.processed(target, {})
            e["g"] = round(center_g(B, I, mw), 5)
        self.st["entries"].append(e)
        self.fill_table()
        self.table.selectRow(len(self.st["entries"]) - 1)
        self.timer.start()

    def iso_groups(self, e):
        return parse_nuclei(e.get("nuclei", ""))

    def fit_current(self):
        e = self.current()
        if e is None or e["kind"] != "iso":
            return
        target = next((x for x in self.st["entries"] if x["uid"] == e.get("fit_to")), None)
        mw = self.axis_mw(target)
        if target is None or not mw:
            return self.main.error(T("epr_iso_need_mw"))
        bad = unknown_nuclei(e.get("nuclei", ""))
        if bad:
            return self.main.error(T("epr_nuclei_unknown", parts="; ".join(bad)))
        B, I = self.processed(target, {})
        r = fit_iso(B, I, mw, e["g"], self.iso_groups(e), e["lw"], e.get("lorentz", 0.0),
                    vary_lorentz=e.get("fit_lorentz", False))
        e.update(g=round(r["g"], 6), lw=round(r["lw"], 5), lorentz=round(r["lorentz"], 3),
                 nuclei=nuclei_with_a(e.get("nuclei", ""), [a for (_, _, a) in r["groups"]]),
                 fit={"r2": r["r2"], "rms": r["rms"], "mw": mw})
        self.show_details()
        self.timer.start()

    def fit_text(self, e):
        r = e.get("fit")
        groups = self.iso_groups(e)
        parts = [f"g = {e['g']:.5f}", f"ΔB_pp = {e['lw']:.3f} mT"]
        for n, I_, a in groups:
            parts.append(f"{n}× (I = {I_:g}): a = {a:.4f} mT ≙ {a * MHZ_PER_MT_FREE * e['g'] / 2.0023:.2f} MHz")
        if r:
            parts.append(f"R² = {r['r2']:.4f}")
        return "\n".join(parts)

    def si_caption(self, name):
        """Wie in der SI: „X-Band EPR spectrum of <b>6m•+</b> in THF (1 mM). Fitting parameters: g = 2.0026;
        ΔBpp = 0.284 mT; hyperfine coupling: 1×14N: 2.39 MHz; …“. Band aus der Mikrowellenfrequenz, Parameter nur aus
        eigenen S = ½-Fits (ohne Fehler, siehe methods_text), Spezies/Lösungsmittel/Konzentration aus den Feldern."""
        import html
        from elucida.si.lines import chem_html
        st = self.st
        if st["mode"] != "spectra":
            return super().si_caption(name)
        sp = st.get("cap_species") or name
        sp = re.sub(r"\^\{([^}]*)\}", r"<sup>\1</sup>", html.escape(sp, quote=False))
        vis = [e for e in st["entries"] if e["visible"]]
        exps = [e for e in vis if e["kind"] == "exp"]
        mw = next((self.spectrum(e)["meta"].get("mw_GHz") for e in exps if self.spectrum(e)["meta"].get("mw_GHz")),
                  None)
        band = band_name(st.get("ref_freq") or mw)
        h = (f"{band}-Band " if band else "") + ("EPR spectra" if len(exps) > 1 else "EPR spectrum") + f" of <b>{sp}</b>"
        if st.get("cap_solvent"):
            h += " in " + chem_html(st["cap_solvent"])
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        h += "."
        dB, calib_t = self.calibration_shift()
        isos = [e for e in vis if e["kind"] == "iso" and e.get("fit") and not (dB and e.get("fit_to") == calib_t)]
        for e in isos:
            parts = [f"g = {e['g']:.4f}", f"ΔB<sub>pp</sub> = {e['lw']:.3f} mT"]
            hfc = [f"{n}×{nucleus_html(nm)}: {a * MHZ_PER_MT_FREE * e['g'] / 2.0023:.2f} MHz"
                   for (n, _, a), nm in zip(self.iso_groups(e), nuclei_names(e.get("nuclei", "")))]
            if hfc:
                parts.append("hyperfine coupling: " + "; ".join(hfc))
            h += " Fitting parameters" + (f" ({html.escape(e['label'])})" if len(isos) > 1 else "") + ": " + \
                "; ".join(parts) + "."
        if dB:
            h += f" The magnetic field was referenced to a standard (g = {st['calib_g']:.4f})."
        return h

    def calibration_shift(self):
        """Feldkorrektur ΔB [mT] aus einer gefitteten Referenz (z. B. TEMPO, g_lit): B_korr = B − ΔB.
        -> (ΔB, uid der Referenzmessung) oder (0, None)."""
        st = self.st
        ref = next((x for x in st["entries"] if x["uid"] == st.get("calib_uid") and x["kind"] == "iso"), None)
        if ref is None or not ref.get("fit"):
            return 0.0, None
        # bei der aktuellen Achsenfrequenz (ν_ref später geändert: ΔB skaliert mit); g_fit hängt nicht davon ab
        target = next((x for x in st["entries"] if x["uid"] == ref.get("fit_to")), None)
        mw = self.axis_mw(target) or ref["fit"]["mw"]
        return b_res(mw, ref["g"]) - b_res(mw, st["calib_g"]), ref.get("fit_to")

    def move(self, d):
        r, es = self.table.currentRow(), self.st["entries"]
        if 0 <= r < len(es) and 0 <= r + d < len(es):
            es[r], es[r + d] = es[r + d], es[r]
            self.fill_table()
            self.table.selectRow(r + d)
            self.timer.start()

    def remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["entries"]):
            uid = self.st["entries"][r]["uid"]
            del self.st["entries"][r]
            for e in self.st["entries"]:                  # Verweise aufheben
                e["dark"] = None if e.get("dark") == uid else e.get("dark")
                e["fit_to"] = None if e.get("fit_to") == uid else e.get("fit_to")
            self.fill_table()
            self.timer.start()

    def fill_table(self):
        self._loading = True
        es = self.st["entries"]
        self.table.setRowCount(len(es))
        for i, e in enumerate(es):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(e["color"], lambda c, e=e: self._set_color(e, c)))
            for j, txt in ((3, T("epr_kind_" + e["kind"])), (4, f"{e['T']:.0f}" if e.get("T") else "–")):
                it = QTableWidgetItem(txt)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, it)
        self.table.resizeColumnToContents(0)
        cur = self.st.get("calib_uid")
        self.cmb_calib.blockSignals(True)
        self.cmb_calib.clear()
        self.cmb_calib.addItem(T("epr_none"), None)
        for e in es:
            if e["kind"] == "iso":
                self.cmb_calib.addItem(e["label"], e["uid"])
        self.cmb_calib.setCurrentIndex(max(0, self.cmb_calib.findData(cur)))
        self.cmb_calib.blockSignals(False)
        self._loading = False

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

    def current(self):
        r = self.table.currentRow()
        return self.st["entries"][r] if 0 <= r < len(self.st["entries"]) else None

    def show_details(self):
        e = self.current()
        self.det.setEnabled(e is not None)
        self._loading = True
        exp = e is not None and e["kind"] == "exp"
        for w_ in (self.lbl_dark, self.cmb_dark, self.sp_dark_k, self.btn_dark_all):
            w_.setVisible(exp or e is None)
        iso = e is not None and e["kind"] == "iso"
        for w_ in (self.lbl_fit, self.cmb_fit):
            w_.setVisible(e is not None and not exp)
        for w_ in (self.lbl_scale, self.sp_scale, self.sp_shift, self.lbl_params_row, self.lbl_params):
            w_.setVisible(e is not None and e["kind"] == "sim")
        self.w_iso.setVisible(iso)
        others = [x for x in self.st["entries"] if e is None or x["uid"] != e["uid"]]
        for cmb, key in ((self.cmb_dark, "dark"), (self.cmb_fit, "fit_to")):
            cmb.clear()
            cmb.addItem(T("epr_none"), None)
            for x in others:
                if x["kind"] == "exp":
                    cmb.addItem(x["label"], x["uid"])
            cmb.setCurrentIndex(max(0, cmb.findData(e.get(key) if e else None)))
        if e:
            self.sp_dark_k.setValue(e.get("dark_k", 1.0))
            self.sp_scale.setValue(e.get("scale", 1.0))
            self.sp_scale.setEnabled(not e.get("fit_to"))
            self.sp_shift.setValue(e.get("shift", 0.0))
            self.lbl_params.setText(Path(e["params"]).name if e.get("params") else "–")
            if iso:
                self.sp_g.setValue(e["g"])
                self.sp_lw.setValue(e["lw"])
                self.sp_lor.setValue(e.get("lorentz", 0.0))
                self.cb_fit_lor.setChecked(e.get("fit_lorentz", False))
                self.ed_nuclei.setText(e.get("nuclei", ""))
                self.lbl_fit.setText(self.fit_text(e))
            self.lbl_meta.setText(self.meta_text(e) if e["kind"] != "iso" else "")
        self._loading = False

    def meta_text(self, e):
        m = self.spectrum(e)["meta"]
        parts = []
        for key, fmt in (("mw_GHz", "ν = {:.5f} GHz"), ("T_K", "T = {:.1f} K"), ("mod_mT", "B_mod = {:.3f} mT"),
                         ("power_mW", "P = {:.3g} mW")):
            if m.get(key):
                parts.append(fmt.format(m[key]))
        if m.get("date") or m.get("time"):
            parts.append(f"{m.get('date', '')} {m.get('time', '')}".strip())
        txt = ", ".join(parts)
        if e.get("params"):
            try:
                pr = parse_easyspin(Path(e["params"]).read_text(encoding="utf-8", errors="replace"))
                z = zfs_summary(pr)
                txt += ("\n" + z) if z else ""
                g = pr.get("Sys.g")
                if isinstance(g, list) and g:
                    txt += "\n" + "g = " + ", ".join(f"{v:.4f}" for v in g)
            except OSError:
                pass
        return txt

    def detail_changed(self, *_):
        e = self.current()
        if self._loading or e is None:
            return
        if e["kind"] == "exp":
            e.update(dark=self.cmb_dark.currentData(), dark_k=self.sp_dark_k.value())
        elif e["kind"] == "iso":
            new = dict(fit_to=self.cmb_fit.currentData(), g=self.sp_g.value(), lw=self.sp_lw.value(),
                       lorentz=self.sp_lor.value(), fit_lorentz=self.cb_fit_lor.isChecked(),
                       nuclei=self.ed_nuclei.text().strip())
            # von Hand geändert -> keine Fit-Ergebnisse mehr (Unterschrift/SI nennen nur Fits); Vergleich in der
            # Genauigkeit der Felder, sonst verwirft schon das Häkchen den Fit
            dec = {"g": 5, "lw": 3, "lorentz": 2}                       # Nachkommastellen der Felder
            if (any(new[k] != e.get(k) for k in ("fit_to", "nuclei"))
                    or any(abs(new[k] - round(e.get(k, 0.0), d)) > 0.4 * 10 ** -d for k, d in dec.items())):
                new["fit"] = None
            e.update(new)
        else:
            e.update(fit_to=self.cmb_fit.currentData(), scale=self.sp_scale.value(), shift=self.sp_shift.value())
            self.sp_scale.setEnabled(not e["fit_to"])
        self.timer.start()

    def dark_for_all(self):
        """Dunkelspektrum und Faktor des gewählten Eintrags für alle übrigen Messungen übernehmen."""
        e = self.current()
        if e is None or e["kind"] != "exp":
            return
        for x in self.st["entries"]:
            if x["kind"] == "exp" and x["uid"] != e.get("dark") and x is not e:
                x.update(dark=e.get("dark"), dark_k=e.get("dark_k", 1.0))
        self.timer.start()

    def choose_params(self):
        e = self.current()
        if e is None or not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("epr_params"), self.main.settings.value("last_dir", ""),
                                           "EasySpin (*.txt *.m);;" + T("flt_all"))
        if p:
            self.set_params(self.main.import_file(p, PRJ.data_sub(self.STATE_KEY)))

    def set_params(self, p):
        e = self.current()
        if e is None:
            return
        e["params"] = p
        self.show_details()
        self.timer.start()

    # -- Verarbeitung und Abbildung -----------------------------------------------------
    def processed(self, e, cache, hide=True):
        """Messung oder Simulation nach allen Schritten -> (B [mT], I) auf dem Raster der Datei.
        hide=False: ausgeblendete Bereiche bleiben erhalten (Export für EasySpin, Integration)."""
        key = (e["uid"], hide)
        if key in cache:
            return cache[key]
        st = self.st
        if e["kind"] == "iso":                           # eigene Simulation auf dem Raster ihrer Messung
            target = next((x for x in st["entries"] if x["uid"] == e.get("fit_to")), None)
            mw = self.axis_mw(target)
            if target is None or not mw:
                cache[key] = (np.array([]), np.array([]))
                return cache[key]
            tb, _ = self.processed(target, cache, hide)
            B = tb if len(tb) <= 8000 else np.linspace(tb.min(), tb.max(), 8000)
            I = iso_spectrum(B, mw, e["g"], self.iso_groups(e), e["lw"], e.get("lorentz", 0.0))
            cache[key] = (B, I)
            return B, I
        s = self.spectrum(e)
        B, I = s["B"].astype(float), s["I"].astype(float).copy()
        if e["kind"] == "exp":
            dark = next((x for x in st["entries"] if x["uid"] == e.get("dark")), None)
            if dark is not None:                           # auf den Rohachsen, vor Skalierung/Kalibrierung
                ds = self.spectrum(dark)
                I = I - e.get("dark_k", 1.0) * np.interp(B, ds["B"], ds["I"], left=np.nan, right=np.nan)
            mw = s["meta"].get("mw_GHz")
            if st.get("ref_freq") and mw:                  # Feld auf Referenzfrequenz skalieren (B·ν_ref/ν)
                B = B * st["ref_freq"] / mw
            dB, calib_target = self.calibration_shift()
            if dB and e["uid"] != calib_target:
                B = B - dB                                 # Feldkorrektur aus der Referenz (z. B. TEMPO)
            I = I - baseline(B, I, st["bl_order"], st["bl_edge"] / 100.0, ranges(st["bl_regions"]) or None)
            if hide:
                for a, b in ranges(st["exclude"]):
                    I[(B >= a) & (B <= b)] = np.nan
            I = smooth(B, I, st["smooth"])
        else:                                              # EasySpin-Simulation: Form; Skalierung in components()
            B = B + e.get("shift", 0.0)
            if not e.get("fit_to"):
                I = I * e.get("scale", 1.0)
        cache[key] = (B, I)
        return B, I

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["entries"] if e["visible"]]
        if not vis:
            self.lbl_info.setText("")
            return None
        if st["mode"] == "intensity":
            return self.intensity_spec([e for e in vis if e["kind"] == "exp"])
        cfg = self.base_cfg()
        fac = 10.0 if st["unit"] == "G" else 1.0
        cache, curves, info = {}, [], []
        data, extra = self.components(vis, cache, info)   # skalierte Kurven, Summen und Reste je Messung
        # Normierung: Messung auf max |I| = 1; Simulationen, Summe, Rest mit dem Faktor ihrer Messung
        norm = {}
        for e in vis:
            ref = e if e["kind"] == "exp" else next((x for x in st["entries"] if x["uid"] == e.get("fit_to")
                                                     and x["uid"] in data), e)   # auch ausgeblendete Messung
            ri = data[ref["uid"]][1]
            mx = np.nanmax(np.abs(ri)) if len(ri) and np.isfinite(ri).any() else 0
            norm[e["uid"]] = (1.0 / mx) if (st["normalize"] and mx > 0) else 1.0
        levels, lev = {}, -1
        for e in vis:                                     # Simulation auf der Ebene ihrer Messung
            if e["kind"] in ("sim", "iso") and e.get("fit_to") in levels:
                levels[e["uid"]] = levels[e["fit_to"]]
            else:
                lev += 1
                levels[e["uid"]] = lev
        n_lev = lev + 1
        span = st["gap"] if st["normalize"] else st["gap"] * max(
            (np.nanmax(np.abs(data[e["uid"]][1])) for e in vis if len(data[e["uid"]][1])), default=1.0)
        for e in vis:
            B, I = data[e["uid"]]
            if not len(B):
                continue
            Bd, Id = decimate(B * fac, I * norm[e["uid"]])
            off = (n_lev - 1 - levels[e["uid"]]) * span if st["stack"] else 0.0
            curves.append({"x": Bd, "y": Id + off, "val": Id, "color": e["color"], "label": e["label"],
                           "ls": "-" if e["kind"] == "exp" else "--", "lw": 1.0 if e["kind"] == "exp" else 1.2})
            for kind, (Bx, Ix) in extra.get(e["uid"], {}).items():  # Summe/Rest der Komponenten dieser Messung
                Bd, Id = decimate(Bx * fac, Ix * norm[e["uid"]])
                curves.append({"x": Bd, "y": Id + off, "val": Id, "color": "#7f7f7f" if kind == "res" else "#e08a00",
                               "label": T("epr_sum") if kind == "sum" else T("epr_residual"),
                               "ls": ":" if kind == "res" else "-.", "lw": 1.0})
            if e["kind"] == "exp" and e.get("dark"):
                m1, m2 = self.spectrum(e)["meta"], self.spectrum(
                    next(x for x in st["entries"] if x["uid"] == e["dark"]))["meta"]
                for key, tol, name in (("mw_GHz", 2e-4, "ν"), ("mod_mT", 1e-6, "B_mod"), ("power_mW", 1e-6, "P")):
                    if m1.get(key) and m2.get(key) and abs(m1[key] - m2[key]) > tol * max(1, abs(m1[key])):
                        info.append(T("epr_dark_mismatch", name=e["label"], what=name))
        allx = np.concatenate([c["x"] for c in curves])
        cfg["xlim"] = [float(np.nanmin(allx)), float(np.nanmax(allx))] if st["x_auto"] else [st["x_min"], st["x_max"]]
        ally = np.concatenate([c["y"] for c in curves])
        lo_, hi_ = float(np.nanmin(ally)), float(np.nanmax(ally))
        pad = 0.08 * ((hi_ - lo_) or 1.0)
        cfg["ylim"] = [lo_ - pad, st["ymax"] if st["ymax"] > 0 else hi_ + 2 * pad]
        cfg["xlabel"] = f"magnetic field [{st['unit']}]"
        cfg["ylabel"] = ("normalized " if st["normalize"] else "") + "EPR intensity [arb. u.]"
        cfg["y_axis"] = st["y_axis"]
        labels = [{"key": f"label_epr_{k}", "lam": pos, "text": name} for k, (name, pos) in enumerate(_labels(st["labels"]))]
        if st["show_params"]:
            for e in vis:
                if e["kind"] == "sim" and e.get("params") and Path(e["params"]).exists():
                    pr = parse_easyspin(Path(e["params"]).read_text(encoding="utf-8", errors="replace"))
                    d = pr.get("Sys.D")
                    if isinstance(d, list) and d:
                        D_, E_ = zfs_DE(d)
                        txt = f"D = {D_ / MHZ_PER_CM:.3f} cm$^{{-1}}$"
                        if len(d) > 1:
                            txt += f"\n|E| = {abs(E_) / MHZ_PER_CM:.4f} cm$^{{-1}}$"
                        labels.append({"key": f"label_zfs_{e['uid']}", "lam": float(np.mean(cfg["xlim"])), "text": txt,
                                       "color": e["color"]})
        self.lbl_info.setText("\n".join(dict.fromkeys(info)))
        self._mw = next((self.axis_mw(e) for e in vis if e["kind"] == "exp" and self.axis_mw(e)), None)
        return cfg, curves, labels, []

    def components(self, vis, cache, info):
        """Simulationen (EasySpin und S = ½), die einer Messung zugeordnet sind, gemeinsam per linearen kleinsten
        Quadraten skalieren. -> (uid -> (B, I) für alle sichtbaren Einträge, uid der Messung -> {sum/res: (B, I)})."""
        st = self.st
        data = {e["uid"]: self.processed(e, cache) for e in vis}
        # ausgeblendete Messung mit sichtbarer Simulation: Faktor und Normierung kommen weiter von ihr
        wanted = {e.get("fit_to") for e in vis if e["kind"] in ("sim", "iso")}
        hidden = [e for e in st["entries"] if e["kind"] == "exp" and e["uid"] in wanted and e["uid"] not in data]
        for e in hidden:
            data[e["uid"]] = self.processed(e, cache)
        extra = {}
        for t in [e for e in vis if e["kind"] == "exp"] + hidden:
            comps = [e for e in vis if e["kind"] in ("sim", "iso") and e.get("fit_to") == t["uid"] and len(data[e["uid"]][0])]
            if not comps:
                continue
            tb, ti = data[t["uid"]]
            w = combine_components(tb, ti, [data[c["uid"]] for c in comps])
            total = np.zeros_like(tb)
            parts = []
            for c, wk in zip(comps, w):
                b, i = data[c["uid"]]
                data[c["uid"]] = (b, wk * i)
                total += np.interp(tb, b, wk * i, left=0.0, right=0.0)
                parts.append((c["label"], abs(double_integral(b, wk * i))))
            if min(w) < 0:                                # Anteile in % wären irreführend
                info.append(T("epr_negative_weight", name=t["label"]))
            elif len(comps) > 1:
                tot = sum(v for _, v in parts) or 1.0
                info.append(T("epr_fractions", name=t["label"],
                              parts=", ".join(f"{n} {100 * v / tot:.0f} %" for n, v in parts)))
            ex = {}
            if st["show_sum"] and len(comps) > 1:
                ex["sum"] = (tb, total)
            if st["show_residual"]:
                ex["res"] = (tb, ti - total)
            extra[t["uid"]] = ex
        dB, calib_t = self.calibration_shift()
        if dB:
            ref = next(x for x in st["entries"] if x["uid"] == st["calib_uid"])
            info.append(T("epr_calib_info", dB=f"{dB:+.4f}", g=f"{ref['g']:.5f}", glit=f"{st['calib_g']:.5f}"))
        return data, extra

    def intensity_series(self, entries):
        """-> (x-Werte, Intensitäten, x-Beschriftung, Einträge mit Wert) für die Intensitätsansicht."""
        st, cache = self.st, {}
        win = (ranges(st["int_window"]) or [None])[0]
        xs, ys, used = [], [], []
        self._edge_hits = 0
        # t = 0: frühestes Spektrum im Tab (auch ausgeblendet, z. B. das Dunkelspektrum vor dem Bestrahlen)
        times = [measured_at(self.spectrum(x)["meta"]) for x in st["entries"] if x["kind"] == "exp"]
        t0 = min((t for t in times if t), default=None)
        for k, e in enumerate(entries):
            B, I = self.processed(e, cache, hide=False)
            meta = self.spectrum(e)["meta"]
            T_K = meta["T_K"] + st.get("T_offset", 0.0) if meta.get("T_K") else None
            if st["int_curie"] and not T_K:               # I und I·T nicht mischen
                continue
            if st["int_method"] == "gauss":
                Bw, Iw = (B, I) if not win else (B[(B >= win[0]) & (B <= win[1])], I[(B >= win[0]) & (B <= win[1])])
                if len(Bw) < 30:
                    continue
                if st["int_curie"] and T_K:               # wie im Skript: erst ×T, dann fitten
                    Iw = Iw * T_K
                lo_, hi_ = (win if win else (float(Bw.min()), float(Bw.max())))
                c0 = st.get("int_center") or float(Bw[np.nanargmax(np.abs(Iw - np.polyval(np.polyfit(
                    np.r_[Bw[:10], Bw[-10:]], np.r_[Iw[:10], Iw[-10:]], 1), Bw)))])
                pfit, _ = gauss_lin_fit(Bw, Iw, min(max(c0, lo_), hi_), lo_, hi_)
                v = abs(float(pfit[0]))
                span_ = float(np.ptp(Bw))
                if min(pfit[1] - Bw.min(), Bw.max() - pfit[1]) < 0.035 * span_:
                    self._edge_hits = getattr(self, "_edge_hits", 0) + 1
            else:
                v = (double_integral(B, I, win) if st["int_method"] == "double" else peak_to_peak(B, I, win))
                if st["int_curie"] and T_K:
                    v *= T_K
            if st["int_x"] == "T":
                x = T_K
            elif st["int_x"] == "time":
                t = measured_at(meta)
                x = (t - t0).total_seconds() / 60.0 if (t and t0) else None
            else:
                x = float(k + 1)
            if x is None or not np.isfinite(v):
                continue
            xs.append(float(x))
            ys.append(float(v))
            used.append(e)
            self._times = getattr(self, "_times", {})
            self._times[e["uid"]] = measured_at(meta)
        xlabel = {"T": "T [K]", "time": "t [min]", "index": T("sec_index")}[st["int_x"]]
        return np.array(xs), np.array(ys), xlabel, used

    def intensity_spec(self, entries):
        st = self.st
        if not entries:
            return None
        x, y, xlabel, used = self.intensity_series(entries)
        if len(x) == 0:
            self.lbl_info.setText(T("epr_int_none"))
            return None
        kin = st.get("kin_fit") and st["int_x"] == "T" and len(x) >= 5
        lsq = st.get("kin_norm", "lsq") == "lsq"
        if kin and not lsq and np.ptp(y) > 0:
            y = (y - y.min()) / np.ptp(y)                  # Min-Max wie im Skript (Modell: I(T₀) = 1 → 0)
        elif st["normalize"] and np.nanmax(np.abs(y)) > 0:
            y = y / y[np.nanargmax(np.abs(y))]           # mit Vorzeichen: unabhängig von der Signalphase positiv
        cfg = self.base_cfg()
        o = np.argsort(x) if st["int_x"] != "index" else np.arange(len(x))
        self.kin_result = None
        fits = []
        if kin:
            ts_ = [self._times.get(e["uid"]) for e in used]
            if all(ts_):
                sec = np.array([(t_ - min(ts_)).total_seconds() for t_ in ts_])
                o = np.argsort(sec, kind="stable")          # Integral in Zeitfolge
                xs_, ss_ = x[o], sec[o]
                beta = float((xs_[-1] - xs_[0]) / (ss_[-1] - ss_[0])) if ss_[-1] > ss_[0] else 0.0  # mittlere Rate
                if lsq or beta > 0:
                    tm = ss_ if lsq else None
                    r = fit_decay(xs_, y[o], beta, norm=st.get("kin_norm", "lsq"), time=tm)
                    if lsq and r["I0"]:
                        y = y / r["I0"]                    # Anzeige relativ zur gefitteten Startintensität
                    # an den Messpunkten: das Integral des Modells läuft über genau diese Punkte (wie im Fit)
                    fits.append({"x": xs_, "y": decay_model(xs_, r["A"], r["Ea"], beta, tm), "color": "#1764e8",
                                 "label": T("epr_kin_fitcurve"), "ls": "-", "lw": 1.6})
                    if np.isfinite(r["cov"]).all():
                        for yb, lab in zip(decay_band(xs_, r, beta, tm), (T("epr_kin_band"), None)):
                            fits.append({"x": xs_, "y": yb, "color": "#1764e8", "label": lab, "ls": ":",
                                         "lw": 0.9})
                    self.kin_result = dict(r, beta=beta)
        curves = [{"x": x[o], "y": y[o], "color": "#000000", "label": T("epr_kin_data") if kin else None,
                   "ls": "-" if not kin else "none", "lw": 0.8, "marker": "o"}] + fits
        if kin:
            cfg["legend"] = True
        pad = 0.05 * (np.ptp(x) or 1.0)
        cfg["xlim"] = [float(x.min() - pad), float(x.max() + pad)] if st["x_auto"] else [st["x_min"], st["x_max"]]
        top = float(np.nanmax(y)) if len(y) else 1.0
        cfg["ylim"] = [min(0.0, float(np.nanmin(y))) - 0.05 * abs(top), st["ymax"] if st["ymax"] > 0 else 1.1 * top]
        cfg["xlabel"] = xlabel
        name = ("normalized " if st["normalize"] else "") + "EPR intensity" + (" (I × T)" if st["int_curie"] else "")
        cfg["ylabel"] = name + ("" if st["normalize"] else " [arb. u.]")
        cfg["y_axis"] = "numbers"
        cfg.setdefault("legend", False)
        self.series_values = list(zip(x[o], y[o], [used[i]["label"] for i in o]))
        info = T("epr_int_info", n=len(x), method=T("epr_int_" + st["int_method"]))
        r = self.kin_result
        if r:
            info += "\n" + T("epr_kin_result", Ea=f"{r['Ea'] / 1000:.1f}", kcal=f"{r['Ea'] / 4184:.2f}",
                             lo=f"{r['ci_Ea'][0] / 4184:.2f}", hi=f"{r['ci_Ea'][1] / 4184:.2f}", A=f"{r['A']:.2e}",
                             beta=f"{r['beta'] * 60:.3f}", corr=f"{r['corr']:.4f}",
                             how=T("epr_kin_" + st.get("kin_norm", "lsq")))
        elif st.get("kin_fit") and st["int_x"] != "T":
            info += "\n" + T("epr_kin_need_T")
        if getattr(self, "_edge_hits", 0):
            info += "\n" + T("epr_gauss_edge", n=self._edge_hits)
        self.lbl_info.setText(info)
        return cfg, curves, [], []

    def methods_text(self):
        """SI-Text (englisch) zu Verarbeitung und Fits der sichtbaren Einträge, nur die benutzten Schritte, in der
        Reihenfolge der Verarbeitung; danach die Ergebnisse (S = ½-Fits, Kalibrierung, Kinetik)."""
        st = self.st
        vis = [e for e in st["entries"] if e["visible"]]
        exps = [e for e in vis if e["kind"] == "exp"]
        if not exps:
            return ""
        fmt_r = lambda rs: ", ".join(f"{a:g}–{b:g}" for a, b in rs)          # noqa: E731
        m, res = [], []
        if st.get("ref_freq"):
            m.append(f"Field axes were scaled to a common microwave frequency of {st['ref_freq']:g} GHz "
                     "(B·ν_ref/ν).")
        dB, calib_t = self.calibration_shift()
        if dB:
            ref = next(x for x in st["entries"] if x["uid"] == st["calib_uid"])
            m.append(f"The magnetic field was calibrated with a reference spectrum (g_lit = {st['calib_g']:.4f}): its "
                     "simulation was fitted (see below), and the field offset ΔB = B_res(g_fit) − B_res(g_lit) at the "
                     "microwave frequency of the reference was subtracted from the field axes of all other spectra.")
            res.append(f"Field calibration: g_fit = {ref['g']:.5f}, ΔB = {dB:+.3f} mT".replace("-", "−"))
        steps = []
        darks = sorted({round(e.get("dark_k", 1.0), 3) for e in exps if e.get("dark")})
        if darks:
            steps.append("a dark spectrum was subtracted (I_light − k·I_dark, k = " + ", ".join(f"{k:g}" for k in darks)
                         + "; interpolated onto the field axis of the measurement)")
        if st["bl_order"] >= 0:
            regs = ranges(st["bl_regions"])
            where = (f"the signal-free field ranges {fmt_r(regs)} mT" if regs
                     else f"the outer {st['bl_edge']:g}% of the field sweep on each side")
            steps.append(f"a polynomial baseline of order {st['bl_order']} was fitted by least squares to {where} "
                         "and subtracted")
        if ranges(st["exclude"]):
            steps.append(f"the field range(s) {fmt_r(ranges(st['exclude']))} mT were excluded")
        win = sorted({round(n * float(np.median(np.diff(B))), 4) for B in (self.spectrum(e)["B"] for e in exps)
                      for n in [smooth_points(B, st["smooth"])] if n})   # wirksames Fenster, nicht die Eingabe
        if win:
            steps.append("the spectra were smoothed by a moving average over " + ", ".join(f"{v:g}" for v in win)
                         + " mT")
        if st["normalize"] and st["mode"] == "spectra":
            steps.append("the spectra were normalized to their maximum absolute intensity (assigned simulations "
                         "with the factor of their measurement)")
        if steps:
            txt = "; ".join(steps)
            m.append("Processing of the measured spectra: " + txt + ".")
        sims = [e for e in vis if e["kind"] in ("sim", "iso") and e.get("fit_to")]
        if any(e["kind"] == "sim" for e in sims):
            m.append("Spectra were simulated with EasySpin.[S. Stoll, A. Schweiger, J. Magn. Reson. 2006, 178, 42–55.]")
        if sims:
            m.append("Simulations assigned to a measured spectrum were scaled to it by linear least squares, all "
                     "components of a spectrum simultaneously (one factor each); relative contributions were "
                     "obtained from the double integrals of the scaled components.")
        isos = [e for e in vis if e["kind"] == "iso" and e.get("fit")]
        if isos:
            lor = any(e.get("fit_lorentz") for e in isos)
            m.append("Isotropic S = 1/2 spectra were simulated to first order (lines of groups of equivalent nuclei "
                     "with binomial/multinomial intensities, first-derivative pseudo-Voigt line shape with "
                     "peak-to-peak width ΔBpp). g, the hyperfine coupling constants a and ΔBpp"
                     + (" and the Lorentzian fraction" if lor else "") + " were optimized by Levenberg–Marquardt "
                     "least squares after a coarse grid search over the field position and a common scaling factor "
                     "of the coupling constants; the amplitude was determined linearly. Parameter uncertainties "
                     "were not derived from the fit (residuals of a digitized spectrum are correlated).")
            for e in isos:
                parts = [f"g = {e['g']:.5f}"]
                for n, I_, a in self.iso_groups(e):
                    parts.append(f"a({n} × I = {I_:g}) = {a:.3f} mT ({a * MHZ_PER_MT_FREE * e['g'] / 2.0023:.1f} MHz)")
                parts.append(f"ΔBpp = {e['lw']:.3f} mT")
                if e.get("fit_lorentz"):
                    parts.append(f"Lorentzian fraction {e.get('lorentz', 0.0):.2f}")
                parts.append(f"R² = {e['fit']['r2']:.4f}")
                res.append(f"{e['label']}: " + ", ".join(parts))
        if st["mode"] == "intensity":
            win = (ranges(st["int_window"]) or [None])[0]
            wtxt = f" within {win[0]:g}–{win[1]:g} mT" if win else ""
            meth = st["int_method"]
            if meth == "double":
                m.append(f"EPR intensities were obtained by double integration of the first-derivative spectra{wtxt}; "
                         "after the first integration, a straight line through the mean values of the outer 5% "
                         "on each side was subtracted.")
            elif meth == "pp":
                m.append(f"EPR intensities were taken as peak-to-peak amplitudes{wtxt}.")
            else:
                m.append(f"EPR intensities were obtained by fitting a Gaussian on a linear baseline{wtxt}, "
                         "y = p1·exp[−(B − p2)²/p3] + p4·B + p5, by Levenberg–Marquardt least squares (centre p2 "
                         "constrained to the window and at least 3% of its width from the edges, p3 = 3–50 mT²); "
                         "|p1| was used as intensity.")
            if st["int_curie"]:
                m.append("Intensities were multiplied by the temperature (I·T)"
                         + (" before fitting." if meth == "gauss" else "."))
            if st.get("T_offset"):
                m.append(f"Temperatures were corrected by {st['T_offset']:+g} K.".replace("-", "−"))
            r = getattr(self, "kin_result", None)
            if r:
                lsq = st.get("kin_norm", "lsq") == "lsq"
                if lsq:
                    m.append("The decay was analysed as a first-order process, I(t) = I0·exp[−A∫exp(−Ea/RT(t′))dt′] "
                             "from the first spectrum, with the integral evaluated by the trapezoidal rule over the "
                             "recorded times and temperatures (no constant heating rate assumed). Ea and ln A were "
                             "fitted to the measured intensities by Levenberg–Marquardt least squares, with I0 determined "
                             "linearly, starting from a grid over Ea with ln A chosen to reproduce the measured "
                             "half-decay point; 95% confidence intervals were obtained from s²(JᵀJ)⁻¹ with "
                             "s² = SSR/(n − 3) and t(0.975; n − 3). β is the mean heating rate.")
                else:
                    m.append("The decay was analysed as a first-order process at a constant heating rate β (from the "
                             "first and last temperature and time), I(T) = exp[−(A/β)∫exp(−Ea/RT′)dT′] from the first "
                             "temperature (trapezoidal integration over the measured temperatures), using min–max "
                             "normalized intensities. Ea and ln A were fitted by Levenberg–Marquardt, starting from a "
                             "grid over Ea with ln A chosen to reproduce the measured half-decay temperature. The square "
                             "roots of the absolute residuals were minimized (L1 norm); the intervals (1.96·SE from "
                             "(JᵀJ)⁻¹·SSR/n) underestimate the uncertainty.")
                half = (r["ci_Ea"][1] - r["ci_Ea"][0]) / 2
                a_, e_ = core.fmt_ve(r["Ea"] / 1000, half / 1000, max_decimals=2)      # Auflösung 0,01 kJ/mol
                mant, ex = f"{r['A']:.2e}".split("e")
                res.append(f"Ea = {a_}" + (f" ± {e_}" if e_ is not None else "") +
                           f" kJ mol-1 ({r['Ea'] / 4184:.1f} kcal mol-1), "
                           f"A = {mant} × 10^{int(ex)} s-1, "
                           f"β = {r['beta'] * 60:.3f} K min-1, n = {len(self.series_values)}, "
                           f"correlation Ea/ln A = {r['corr']:.4f}")
        if not m and not res:
            return ""
        out = " ".join(m)
        return out + ("\n\n" + "; ".join(res) + "." if res else "")

    def export_to(self, base: Path):
        """Abbildung + Daten wie überall; zusätzlich je Messung eine EasySpin-fertige Textdatei (B in mT, I) in
        voller Auflösung nach Dunkelspektrum/Basislinie/Glättung, ohne Normierung und Ausblenden."""
        files = super().export_to(base)
        st, cache = self.st, {}
        base = Path(base).resolve()
        for e in st["entries"]:
            if not (e["visible"] and e["kind"] == "exp"):
                continue
            B, I = self.processed(e, cache, hide=False)
            m = self.spectrum(e)["meta"]
            dark = next((x for x in st["entries"] if x["uid"] == e.get("dark")), None)
            head = [f"% {e['label']} – exported by Elucida (processed spectrum for EasySpin: load(...))",
                    f"% source: {Path(e['file']).name}" + (f" [{e.get('slice', 0) + 1}]" if e.get("slice") else ""),
                    f"% mwFreq [GHz]: {self.axis_mw(e)}; T [K]: {m.get('T_K')}; ModAmp [mT]: {m.get('mod_mT')}; "
                    f"Power [mW]: {m.get('power_mW')}",
                    f"% dark spectrum: {dark['label'] + ' x ' + format(e.get('dark_k', 1.0), 'g') if dark else 'none'}; "
                    f"baseline: order {st['bl_order']}, " + (f"ranges {st['bl_regions']}" if st['bl_regions']
                                                           else f"edges {st['bl_edge']:g} %") +
                    f"; smoothing: {st['smooth']:g} mT",
                    "% B [mT]\tI [arb. u.]"]
            safe = re.sub(r"[^\w.+-]+", "_", e["label"]).strip("_") or e["uid"]
            p, n = base.with_name(f"{base.name}_{safe}.txt"), 1
            while p in files:                              # „sample A“ und „sample/A“: nicht überschreiben
                p, n = base.with_name(f"{base.name}_{safe}_{e['uid']}" + (f"_{n}" if n > 1 else "") + ".txt"), n + 1
            ok = np.isfinite(I)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("\n".join(head) + "\n")
                for b, i in zip(B[ok], I[ok]):
                    fh.write(f"{b:.6f}\t{i:.8g}\n")
            files.append(p)
        if st["mode"] == "intensity" and getattr(self, "series_values", None):
            p = base.with_name(base.name + "_intensity.csv")
            with open(p, "w", encoding="utf-8-sig") as fh:
                fh.write("x;intensity;spectrum\n")
                for x, y, lab in self.series_values:
                    fh.write(f"{x:.6g};{y:.6g};{lab}\n")
                r = getattr(self, "kin_result", None)
                if r:
                    fh.write(f"# Arrhenius first-order decay ({st.get('kin_norm', 'lsq')}): "
                             f"Ea = {r['Ea']:.6g} J/mol [{r['ci_Ea'][0]:.6g}, {r['ci_Ea'][1]:.6g}], "
                             f"lnA = {r['lnA']:.6g} [{r['ci_lnA'][0]:.6g}, {r['ci_lnA'][1]:.6g}], "
                             f"beta = {r['beta']:.6g} K/s, corr(Ea, lnA) = {r['corr']:.4f}\n")
            files.append(p)
        return files

    def hover_text(self, x, val, name):
        if self.st["mode"] == "intensity":
            return f"x = {x:.4g}    I = {val:.4g}" if val is not None else f"x = {x:.4g}"
        unit = self.st["unit"]
        B_mT = x / (10.0 if unit == "G" else 1.0)
        g = f"    g = {g_value(self._mw, B_mT):.4f}" if getattr(self, "_mw", None) and B_mT > 0 else ""
        if val is None:
            return f"B = {x:.2f} {unit}{g}"
        return f"B = {x:.2f} {unit}{g}    I = {val:.3g}    {name}"
