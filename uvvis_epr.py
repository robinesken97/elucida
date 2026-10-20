"""uvvis_epr.py - CW-EPR: Bruker BES3T (ESR5000/ESRStudio, Elexsys), Magnettech-MS400-Text, EasySpin-Simulationen.

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
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

import uvvis_tabs as TABS
from uvvis_i18n import T

MHZ_PER_CM = 29979.2458                       # 1 cm⁻¹ in MHz
MU_B_H = 13.996245                             # µ_B/h in GHz/T  -> g = ν / (µ_B/h · B)


# ----------------------------------------------------------------------------
# Lesen
# ----------------------------------------------------------------------------
def _dsc(path):
    out = {}
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]{1,15})\s+(.*)$", ln.strip())
        if m and not ln.startswith(("*", "#", ".")):
            out[m.group(1)] = m.group(2).strip().strip("'")
    return out


def _f(h, key, default=None):
    try:
        return float(h[key])
    except (KeyError, ValueError, TypeError):
        return default


def read_bes3t(path) -> list:
    """Bruker BES3T (.DSC/.dsc + .DTA): -> [dict(B [mT], I, meta)], bei 2D je Zeile ein Spektrum.
    Unterstützt: reelle Daten, lineare x-Achse (IDX), D/F/I-Formate, Byte-Reihenfolge LIT/BIG."""
    p = Path(path)
    dsc = next((p.with_suffix(s) for s in (".dsc", ".DSC") if p.with_suffix(s).exists()), None)
    dta = next((p.with_suffix(s) for s in (".DTA", ".dta") if p.with_suffix(s).exists()), None)
    if dsc is None or dta is None:
        raise ValueError(f"{p.name}: .dsc und .DTA werden zusammen gebraucht")
    h = _dsc(dsc)
    if h.get("IKKF", "REAL") != "REAL":
        raise ValueError(f"{p.name}: komplexe Daten werden nicht unterstützt")
    nx, ny = int(_f(h, "XPTS", 0)), int(_f(h, "YPTS", 1) or 1)
    fmt = {"D": "f8", "F": "f4", "I": "i4", "S": "i2"}.get(h.get("IRFMT", "D"), "f8")
    order = "<" if h.get("BSEQ", "BIG") == "LIT" else ">"
    y = np.fromfile(dta, dtype=order + fmt).astype(float)
    if nx <= 1 or len(y) < nx * ny:
        raise ValueError(f"{p.name}: Datengröße passt nicht zur Beschreibung")
    if h.get("XTYP", "IDX") != "IDX":
        raise ValueError(f"{p.name}: nur lineare Feldachsen (XTYP IDX) werden unterstützt")
    B = _f(h, "XMIN", 0.0) + np.arange(nx) * _f(h, "XWID", 1.0) / (nx - 1)
    unit = h.get("XUNI", "G").strip().lower()
    B = B / 10.0 if unit == "g" else (B * 1000.0 if unit == "t" else B)
    yvals = None
    if ny > 1 and h.get("YTYP") == "IGD":
        ygf = next((p.with_suffix(s) for s in (".YGF", ".ygf") if p.with_suffix(s).exists()), None)
        if ygf is not None:
            yvals = np.fromfile(ygf, dtype=order + "f8")
    meta = {"mw_GHz": (_f(h, "MWFQ") or 0) / 1e9 or None, "T_K": _f(h, "STMP"),
            "mod_mT": (_f(h, "B0MA") or 0) * 1000 or None, "power_mW": (_f(h, "MWPW") or 0) * 1000 or None,
            "date": h.get("DATE", ""), "time": h.get("TIME", ""), "title": h.get("TITL", p.stem),
            "device": "Bruker BES3T"}
    out = []
    for k in range(ny):
        m = dict(meta)
        if yvals is not None and k < len(yvals):
            m["y"], m["y_name"], m["y_unit"] = float(yvals[k]), h.get("YNAM", ""), h.get("YUNI", "")
        out.append({"B": B, "I": y[k * nx:(k + 1) * nx], "meta": m})
    return out


def _ascii_xy(path):
    rows = []
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        parts = re.split(r"[\s,;]+", ln.strip().replace("−", "-"))
        try:
            vals = [float(v) for v in parts if v]
        except ValueError:
            continue                                   # Kopfzeile
        if len(vals) >= 2:
            rows.append(vals[:2])
    if len(rows) < 10:
        raise ValueError(f"{Path(path).name}: keine zweispaltigen Daten gefunden")
    a = np.array(rows)
    return a[:, 0], a[:, 1]


def read_ascii(path, unit=None) -> dict:
    """Zweispaltiger Text (MS400-Export, EasySpin-Simulation): B, I. Einheit aus der Kopfzeile ('[mT]', '[G]')
    oder geschätzt (Median > 1500 -> G). Mikrowellenfrequenz aus Dateinamen wie '…-9p404368-…' (GHz)."""
    p = Path(path)
    B, I = _ascii_xy(p)
    head = p.read_text(encoding="latin-1", errors="replace")[:300].lower()
    if unit is None:
        unit = "g" if ("[g]" in head or "(g)" in head) else ("mt" if "mt" in head else
                                                          ("g" if np.median(B) > 1500 else "mt"))
    B = B / 10.0 if unit == "g" else B
    o = np.argsort(B)
    mw = None
    for m in re.finditer(r"(?<![\d.])(\d{1,3})p(\d+)(?![\d])", p.stem):
        v = float(f"{m.group(1)}.{m.group(2)}")
        if 1 <= v <= 100:
            mw = v
            break
    return {"B": B[o], "I": I[o], "meta": {"mw_GHz": mw, "title": p.stem, "device": "ASCII"}}


def read_any(path) -> list:
    p = Path(path)
    if p.suffix.lower() in (".dsc", ".dta"):
        return read_bes3t(p)
    return [read_ascii(p)]


# ----------------------------------------------------------------------------
# EasySpin-Parameter
# ----------------------------------------------------------------------------
def parse_easyspin(text) -> dict:
    """MATLAB-Zeilen wie 'Sys.D = [1100 160];' -> {'Sys.D': [1100.0, 160.0], …} (nur Zahlen/Vektoren).
    Kommentare (%) werden entfernt; Zeichenketten und Funktionsaufrufe bleiben als Text."""
    out = {}
    for ln in str(text).splitlines():
        ln = ln.split("%")[0].strip().rstrip(";")
        m = re.match(r"^((?:Sys|Exp|Opt|Fit\w*|Vary)\w*\.\w+)\s*=\s*(.+)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val)
        if val.startswith("[") or re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val):
            out[key] = [float(x) for x in nums]
        else:
            out[key] = val
    return out


def zfs_summary(params) -> str | None:
    """D und E (EasySpin: MHz) in cm⁻¹ und MHz; None ohne Sys.D."""
    d = params.get("Sys.D")
    if not isinstance(d, list) or not d:
        return None
    D, E = d[0], (d[1] if len(d) > 1 else 0.0)
    return (f"D = {D / MHZ_PER_CM:.4f} cm⁻¹ ({D:.0f} MHz), |E| = {abs(E) / MHZ_PER_CM:.4f} cm⁻¹ "
            f"({abs(E):.0f} MHz), E/D = {abs(E / D) if D else 0:.3f}")


# ----------------------------------------------------------------------------
# Verarbeitung
# ----------------------------------------------------------------------------
def ranges(text):
    """'330-340, 480–485' -> [(330, 340), (480, 485)] (mT)."""
    out = []
    for part in str(text).replace(";", ",").split(","):
        m = re.match(r"^\s*([-+]?\d*\.?\d+)\s*[-–—]\s*([-+]?\d*\.?\d+)\s*$", part.replace("−", "-"))
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            out.append((min(a, b), max(a, b)))
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


def smooth(B, I, width_mT):
    """Gleitender Mittelwert über width_mT (ungerade Punktzahl), NaN-sicher."""
    if not width_mT or len(B) < 3:
        return I
    step = float(np.median(np.diff(B))) or 1.0
    n = int(round(width_mT / step)) | 1
    if n < 3:
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


def parse_nuclei(text):
    """'2 14N 0.65; 4 1H 0.32' -> [(2, 1.0, 0.65), (4, 0.5, 0.32)] (Anzahl äquivalenter Kerne, Kernspin, a in mT).
    Auch 'I=1' statt Isotop möglich: '2 I=1 0.65'."""
    out = []
    for part in re.split(r"[;\n]+", str(text)):
        tok = part.replace(",", ".").replace("×", " ").replace("x", " ", 1 if re.match(r"^\s*\d+x", part) else 0).split()
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


def nuclei_with_a(text, new_a):
    """Kopplungen im Text ersetzen, Isotopnamen und Reihenfolge behalten: ('2 14N 0.6', [0.65]) -> '2 14N 0.6500'."""
    out, k = [], 0
    for part in re.split(r"[;\n]+", str(text)):
        tok = part.split()
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
    X_RANGE = (0.0, 20000.0, 1, 1.0)
    XRANGE_TEXT = "epr_xrange"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=300.0, x_max=360.0, ymax=0.0, entries=[], unit="mT",
                         bl_order=1, bl_edge=5.0, bl_regions="", exclude="", smooth=0.0, normalize=True,
                         stack=False, gap=1.2, labels="", show_params=False, y_axis="no_numbers",
                         mode="spectra", int_window="", int_method="double", int_x="time", int_curie=False,
                         show_sum=True, show_residual=False, calib_uid=None, calib_g=2.0055)

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("epr_entries"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("epr_add_exp"), self.add_exp), (T("epr_add_sim"), self.add_sim),
                        (T("epr_add_iso"), self.add_iso),
                        ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)), (T("remove"), self.remove)):
            b = QPushButton(txt)
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
        f = QFormLayout(self.det)
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
        fi = QFormLayout(self.w_iso)
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
        self.lbl_meta.setStyleSheet("color: gray;")
        f.addRow(self.lbl_meta)
        for w_ in (self.sp_dark_k, self.sp_scale, self.sp_shift):
            w_.valueChanged.connect(self.detail_changed)
        for w_ in (self.cmb_dark, self.cmb_fit):
            w_.currentIndexChanged.connect(self.detail_changed)
        self.lv.addWidget(self.det)

        g = QGroupBox(T("epr_processing"))
        f = QFormLayout(g)
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
        self.cmb_calib = QComboBox()
        self.cmb_calib.setToolTip(T("epr_calib_tip"))
        self.sp_calib_g = QDoubleSpinBox(decimals=5, minimum=1.0, maximum=10.0, singleStep=0.0001, value=st["calib_g"])
        row.addWidget(self.cmb_calib, 1)
        row.addWidget(QLabel("g_lit"))
        row.addWidget(self.sp_calib_g)
        f.addRow(T("epr_calib"), row)
        self.lv.addWidget(g)

        g = QGroupBox(T("epr_display"))
        f = QFormLayout(g)
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
        for key in ("double", "pp"):
            self.cmb_int_method.addItem(T("epr_int_" + key), key)
        self.cmb_int_method.setCurrentIndex(max(0, self.cmb_int_method.findData(st["int_method"])))
        self.cmb_int_x = QComboBox()
        for key in ("time", "T", "index"):
            self.cmb_int_x.addItem(T("epr_x_" + key), key)
        self.cmb_int_x.setCurrentIndex(max(0, self.cmb_int_x.findData(st["int_x"])))
        row.addWidget(self.cmb_int_method, 1)
        row.addWidget(QLabel(T("epr_against")))
        row.addWidget(self.cmb_int_x, 1)
        f.addRow(T("epr_int_method"), row)
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
        self.lv.addWidget(g)
        for w_ in (self.sp_bl_order, self.sp_bl_edge, self.sp_smooth, self.sp_gap):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_norm, self.cb_stack, self.cb_params, self.cb_curie, self.cb_sum, self.cb_res):
            w_.toggled.connect(self.changed)
        self.cmb_calib.currentIndexChanged.connect(self.changed)
        self.sp_calib_g.valueChanged.connect(self.changed)
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
                       calib_uid=self.cmb_calib.currentData(), calib_g=self.sp_calib_g.value())

    # -- Einträge ------------------------------------------------------------------
    def data(self, path):
        return self.cache(("epr", path), lambda: read_any(path))

    def spectrum(self, e):
        d = self.data(e["file"])
        return d[min(e.get("slice", 0), len(d) - 1)]

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
                if Path(p).suffix.lower() in (".dsc", ".dta"):
                    for ext in (".dsc", ".DSC", ".DTA", ".dta", ".YGF", ".ygf", ".xml"):
                        if Path(stem + ext).exists() and ext.lower() != Path(p).suffix.lower():
                            self.main.import_file(stem + ext, "data")
                p = self.main.import_file(p, "data")
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
                p = self.main.import_file(p, "data")
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
        mw = self.spectrum(target)["meta"].get("mw_GHz")
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
        mw = self.spectrum(target)["meta"].get("mw_GHz") if target else None
        if target is None or not mw:
            return self.main.error(T("epr_iso_need_mw"))
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

    def calibration_shift(self):
        """Feldkorrektur ΔB [mT] aus einer gefitteten Referenz (z. B. TEMPO, g_lit): B_korr = B − ΔB.
        -> (ΔB, uid der Referenzmessung) oder (0, None)."""
        st = self.st
        ref = next((x for x in st["entries"] if x["uid"] == st.get("calib_uid") and x["kind"] == "iso"), None)
        if ref is None or not ref.get("fit"):
            return 0.0, None
        mw = ref["fit"]["mw"]
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
            e.update(fit_to=self.cmb_fit.currentData(), g=self.sp_g.value(), lw=self.sp_lw.value(),
                     lorentz=self.sp_lor.value(), fit_lorentz=self.cb_fit_lor.isChecked(),
                     nuclei=self.ed_nuclei.text().strip())
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
            self.set_params(self.main.import_file(p, "data"))

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
            mw = self.spectrum(target)["meta"].get("mw_GHz") if target else None
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
            dB, calib_target = self.calibration_shift()
            if dB and e["uid"] != calib_target:
                B = B - dB                                 # Feldkorrektur aus der Referenz (z. B. TEMPO)
            dark = next((x for x in st["entries"] if x["uid"] == e.get("dark")), None)
            if dark is not None:
                ds = self.spectrum(dark)
                I = I - e.get("dark_k", 1.0) * np.interp(B, ds["B"], ds["I"], left=np.nan, right=np.nan)
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
            ref = e if e["kind"] == "exp" else next((x for x in vis if x["uid"] == e.get("fit_to")), e)
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
                        txt = f"D = {d[0] / MHZ_PER_CM:.3f} cm$^{{-1}}$"
                        if len(d) > 1:
                            txt += f"\n|E| = {abs(d[1]) / MHZ_PER_CM:.4f} cm$^{{-1}}$"
                        labels.append({"key": f"label_zfs_{e['uid']}", "lam": float(np.mean(cfg["xlim"])), "text": txt,
                                       "color": e["color"]})
        self.lbl_info.setText("\n".join(dict.fromkeys(info)))
        self._mw = next((self.spectrum(e)["meta"].get("mw_GHz") for e in vis if e["kind"] == "exp"
                         and self.spectrum(e)["meta"].get("mw_GHz")), None)
        return cfg, curves, labels, []

    def components(self, vis, cache, info):
        """Simulationen (EasySpin und S = ½), die einer Messung zugeordnet sind, gemeinsam per linearen kleinsten
        Quadraten skalieren. -> (uid -> (B, I) für alle sichtbaren Einträge, uid der Messung -> {sum/res: (B, I)})."""
        st = self.st
        data = {e["uid"]: self.processed(e, cache) for e in vis}
        extra = {}
        for t in [e for e in vis if e["kind"] == "exp"]:
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
            if len(comps) > 1:
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
        # t = 0: frühestes Spektrum im Tab (auch ausgeblendet, z. B. das Dunkelspektrum vor dem Bestrahlen)
        times = [measured_at(self.spectrum(x)["meta"]) for x in st["entries"] if x["kind"] == "exp"]
        t0 = min((t for t in times if t), default=None)
        for k, e in enumerate(entries):
            B, I = self.processed(e, cache, hide=False)
            v = (double_integral(B, I, win) if st["int_method"] == "double" else peak_to_peak(B, I, win))
            meta = self.spectrum(e)["meta"]
            if st["int_curie"] and meta.get("T_K"):
                v *= meta["T_K"]
            if st["int_x"] == "T":
                x = meta.get("T_K")
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
        if st["normalize"] and np.nanmax(np.abs(y)) > 0:
            y = y / y[np.nanargmax(np.abs(y))]           # mit Vorzeichen: unabhängig von der Signalphase positiv
        cfg = self.base_cfg()
        o = np.argsort(x) if st["int_x"] != "index" else np.arange(len(x))
        curves = [{"x": x[o], "y": y[o], "color": "#000000", "label": None, "ls": "-", "lw": 0.8, "marker": "o"}]
        pad = 0.05 * (np.ptp(x) or 1.0)
        cfg["xlim"] = [float(x.min() - pad), float(x.max() + pad)] if st["x_auto"] else [st["x_min"], st["x_max"]]
        top = float(np.nanmax(y)) if len(y) else 1.0
        cfg["ylim"] = [min(0.0, float(np.nanmin(y))) - 0.05 * abs(top), st["ymax"] if st["ymax"] > 0 else 1.1 * top]
        cfg["xlabel"] = xlabel
        name = ("normalized " if st["normalize"] else "") + "EPR intensity" + (" (I × T)" if st["int_curie"] else "")
        cfg["ylabel"] = name + ("" if st["normalize"] else " [arb. u.]")
        cfg["y_axis"] = "numbers"
        cfg["legend"] = False
        self.series_values = list(zip(x[o], y[o], [used[i]["label"] for i in o]))
        self.lbl_info.setText(T("epr_int_info", n=len(x), method=T("epr_int_" + st["int_method"])))
        return cfg, curves, [], []

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
            head = [f"% {e['label']} – exported by UVVisTool (processed spectrum for EasySpin: load(...))",
                    f"% source: {Path(e['file']).name}" + (f" [{e.get('slice', 0) + 1}]" if e.get("slice") else ""),
                    f"% mwFreq [GHz]: {m.get('mw_GHz')}; T [K]: {m.get('T_K')}; ModAmp [mT]: {m.get('mod_mT')}; "
                    f"Power [mW]: {m.get('power_mW')}",
                    f"% dark spectrum: {dark['label'] + ' x ' + format(e.get('dark_k', 1.0), 'g') if dark else 'none'}; "
                    f"baseline: order {st['bl_order']}, " + (f"ranges {st['bl_regions']}" if st['bl_regions']
                                                           else f"edges {st['bl_edge']:g} %") +
                    f"; smoothing: {st['smooth']:g} mT",
                    "% B [mT]\tI [arb. u.]"]
            safe = re.sub(r"[^\w.+-]+", "_", e["label"]).strip("_") or e["uid"]
            p = base.with_name(f"{base.name}_{safe}.txt")
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
