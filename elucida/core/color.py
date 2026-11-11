"""elucida/core/color.py - Farbe einer Lösung aus dem Absorptionsspektrum (CIE-Farbmetrik).

Transmission T(λ) = 10^(−A), mal Weißlicht (Planck 6504 K ≈ Tageslicht D65), integriert mit den
CIE-1931-Normspektralwertkurven (2°) -> XYZ -> Bradford-Anpassung auf den D65-Weißpunkt (klare Lösung
= reines Weiß) -> sRGB. Die Kurven sind die analytische Näherung von Wyman, Sloan & Shirley,
J. Comput. Graph. Tech. 2 (2013) 1–11 (Abweichung von den CIE-Tabellen < 1 %).

Grenzen: Fluoreszenz und Streuung bleiben unberücksichtigt; Bildschirme sind nicht kalibriert.
"""
from __future__ import annotations

import numpy as np

LAM = np.arange(380.0, 781.0, 1.0)            # sichtbarer Bereich, 1 nm


def _g(lam, mu, s1, s2):
    s = np.where(lam < mu, s1, s2)
    return np.exp(-0.5 * ((lam - mu) / s) ** 2)


def cmf(lam=LAM):
    """CIE 1931 x̄, ȳ, z̄ (Mehrfach-Gauß-Näherung nach Wyman et al. 2013)."""
    x = 1.056 * _g(lam, 599.8, 37.9, 31.0) + 0.362 * _g(lam, 442.0, 16.0, 26.7) - 0.065 * _g(lam, 501.1, 20.4, 26.2)
    y = 0.821 * _g(lam, 568.8, 46.9, 40.5) + 0.286 * _g(lam, 530.9, 16.3, 31.1)
    z = 1.217 * _g(lam, 437.0, 11.8, 36.0) + 0.681 * _g(lam, 459.0, 26.0, 13.8)
    return x, y, z


def illuminant(lam=LAM, T=6504.0):
    """Planck-Strahler (relative spektrale Strahldichte) als Näherung für Tageslicht."""
    c2 = 1.4388e7                               # nm·K
    return lam ** -5 / (np.exp(c2 / (lam * T)) - 1.0)


_BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
_XYZ_TO_SRGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
_D65 = np.array([0.95047, 1.0, 1.08883])


def _gamma(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def absorbance_to_rgb(absorbance, lam=LAM):
    """A(λ) auf dem Raster lam -> (sRGB 0..1, außerhalb des sRGB-Farbraums?)."""
    S = illuminant(lam)
    xb, yb, zb = cmf(lam)
    T = 10.0 ** (-np.asarray(absorbance, float))
    white = np.array([np.sum(S * xb), np.sum(S * yb), np.sum(S * zb)])
    xyz = np.array([np.sum(S * T * xb), np.sum(S * T * yb), np.sum(S * T * zb)]) / white[1]
    white = white / white[1]
    # Bradford: Weißpunkt der Lichtquelle -> D65, damit A = 0 exakt Weiß ergibt
    src, dst = _BRADFORD @ white, _BRADFORD @ _D65
    adapt = np.linalg.inv(_BRADFORD) @ np.diag(dst / src) @ _BRADFORD
    lin = _XYZ_TO_SRGB @ (adapt @ xyz)
    # > 1: heller als Bildschirm-Weiß in einem Kanal (sRGB-Eigenheit bei gefiltertem Weiß) -> alle Kanäle
    # gemeinsam skalieren, Farbton bleibt. < 0: Farbe gesättigter als sRGB darstellen kann -> Hinweis.
    if lin.max() > 1.0:
        lin = lin / lin.max()
    return _gamma(lin), bool(np.any(lin < -0.02))


def to_hex(rgb):
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in rgb)


def solution_absorbance(spectra, c_target, d_target, d_meas, cutoff=1.0, lam=LAM):
    """A(λ) einer Lösung der Konzentration c_target in d_target cm, aus der Verdünnungsreihe
    (Lambert-Beer, linear skaliert). Je λ wird die höchste ungesättigte Konzentration genommen
    (A ≤ cutoff), sonst die niedrigste. -> (A, Anteil des Bereichs 380–780 nm, den die Daten abdecken)."""
    a_per_c = np.full(lam.shape, np.nan)
    for s in sorted(spectra, key=lambda s_: -s_["c"]):     # hoch -> niedrig
        x, y = np.asarray(s["x"], float), np.asarray(s["y"], float)
        o = np.argsort(x)
        inside = (lam >= x.min()) & (lam <= x.max())
        yi = np.interp(lam, x[o], y[o])
        take = inside & np.isnan(a_per_c) & (yi <= cutoff)
        a_per_c[take] = yi[take] / s["c"]
    low = min(spectra, key=lambda s_: s_["c"])               # gesättigt bei allen: niedrigste Konz.
    x, y = np.asarray(low["x"], float), np.asarray(low["y"], float)
    o = np.argsort(x)
    rest = np.isnan(a_per_c) & (lam >= x.min()) & (lam <= x.max())
    a_per_c[rest] = np.interp(lam[rest], x[o], y[o]) / low["c"]
    covered = float(np.mean(~np.isnan(a_per_c)))
    a = np.nan_to_num(a_per_c) * c_target * d_target / d_meas
    return np.clip(a, 0.0, None), covered
