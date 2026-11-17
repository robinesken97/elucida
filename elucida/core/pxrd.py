"""elucida/core/pxrd.py - Pulverdiffraktogramm aus einer Einkristallstruktur (X-Ray-Tab, 1.2.0).

Rechnung aus der Struktur, kein Rietveld-Fit: Reflexlagen aus der Zelle (Bragg, d aus dem reziproken metrischen
Tensor), Intensitäten I = |F|² · Lp je einzelnem hkl (Friedel-Paare und symmetrieäquivalente Reflexe zählen einzeln, die
Multiplizität ergibt sich daraus), F = Σ occ · f0(s) · T(hkl) · exp(2πi h·x) über alle Atome der Elementarzelle
(Symmetrieoperationen der CIF, gleiche Lage einmal), f0 nach Cromer–Mann (International Tables Vol. C, siehe
`formats/xray_f0.py`), ohne anomale Dispersion. Auslenkung isotrop exp(−8π²U s²) oder anisotrop exp(−2π² qᵀUq)
(q = kartesischer reziproker Vektor, U mit der Operation gedreht); Atome ohne Auslenkungsparameter in der CIF ohne
Temperaturfaktor (`no_u`, mit Hinweis; U = 0 aus der CIF gilt wie angegeben). Lorentz-Polarisation für Bragg–Brentano ohne
Monochromator: (1 + cos²2θ) / (sin²θ cos θ). Profil Pseudo-Voigt (gemeinsame Halbwertsbreite in 2θ, Lorentz-Anteil η),
Kα2 mit halber Intensität (Kα2/Kα1 = 0.5) an seiner eigenen Bragg-Lage. Angepasst wird nichts außer der Skalierung auf
das stärkste Maximum; eine Nullpunktverschiebung gibt der Nutzer ein.
"""
from __future__ import annotations

import math

import numpy as np

from elucida.formats.xray_f0 import F0, f0

# Kα1/Kα2 [Å] nach International Tables for Crystallography Vol. C, Table 4.2.2.1 (Werte wie in pymatgen
# `WAVELENGTHS`, dort ebenso aus den International Tables); Reihenfolge = Auswahlliste
ANODES = {"Cu": (1.54056, 1.54439), "Mo": (0.70930, 0.71359), "Co": (1.78896, 1.79285), "Fe": (1.93604, 1.93998),
          "Cr": (2.28970, 2.29361), "Ag": (0.559421, 0.563813)}
KA2_RATIO = 0.5
SAME_SITE = 1e-3          # fraktional: gleiche Lage (spezielle Lagen) nur einmal
SAME_D = 1e-7             # relativ in 1/d²: zusammenfallende Reflexe (gleiche Lage im Diagramm)
MIN_REL = 1e-5            # Reflexe unter diesem Anteil des stärksten gelten als ausgelöscht


def cell_atoms(S):
    """Alle Atome der Elementarzelle -> (Elemente, frac N×3, occ, U_iso, U_kart N×3×3 oder None je Atom).
    Fehlgeordnete Teile zählen alle mit ihrer Besetzung (für die Streuung richtig). Element ohne f0: ValueError."""
    Minv = np.linalg.inv(S.M)
    els, xs, occ, uiso, ucart = [], [], [], [], []
    for a in S.atoms:
        el = "H" if a["el"] == "D" else a["el"]
        if el not in F0:
            raise ValueError(el)
        seen = []
        for R, t in S.ops:
            x = (R @ a["frac"] + t) % 1.0
            if any(np.all(np.abs(((x - y) + 0.5) % 1.0 - 0.5) < SAME_SITE) for y in seen):
                continue
            seen.append(x)
            els.append(el)
            xs.append(x)
            occ.append(float(a["occ"]))
            u = a.get("u_iso_cif", a["uiso"])
            uiso.append(0.0 if u is None else float(u))     # ohne Angabe: kein Temperaturfaktor (no_u), nie geschätzt
            if a["U"] is not None:
                Rc = S.M @ R @ Minv
                ucart.append(Rc @ a["U"] @ Rc.T)
            else:
                ucart.append(None)
    return els, np.array(xs), np.array(occ), np.array(uiso), ucart


def no_u(S):
    """Labels der Atome ohne Auslenkungsparameter in der CIF (weder U_ij noch U_iso/B_iso): sie gehen ohne
    Temperaturfaktor (U = 0) in die Rechnung ein – kein angenommener Wert; Karte und Methodensatz nennen sie."""
    return [a["label"] for a in S.atoms if a["U"] is None and a.get("u_iso_cif", a["uiso"]) is None]


def hkl_list(S, d_min):
    """Alle hkl ≠ 000 mit d ≥ d_min -> (H N×3 int, 1/d² N)."""
    a, b, c = S.cell[:3]
    lim = [int(math.floor(v / d_min)) + 1 for v in (a, b, c)]
    g = np.mgrid[-lim[0]:lim[0] + 1, -lim[1]:lim[1] + 1, -lim[2]:lim[2] + 1].reshape(3, -1).T
    g = g[np.any(g != 0, axis=1)]
    Gs = np.linalg.inv(S.M.T @ S.M)                      # reziproker metrischer Tensor
    q2 = np.einsum("ni,ij,nj->n", g, Gs, g)
    keep = q2 <= 1.0 / d_min ** 2 + 1e-12
    return g[keep], q2[keep]


def structure_factors(S, H, q2, chunk=1500):
    """|F|² je hkl (ohne anomale Dispersion)."""
    els, X, occ, uiso, ucart = cell_atoms(S)
    s2 = q2 / 4.0                                        # (sin θ/λ)² = 1/(4d²)
    Minv = np.linalg.inv(S.M)
    Q = H @ Minv                                         # kartesischer reziproker Vektor (Zeilen), |Q| = 1/d
    aniso = [i for i, U in enumerate(ucart) if U is not None]
    Uc = np.array([ucart[i] for i in aniso]) if aniso else np.zeros((0, 3, 3))
    fel = {el: f0(el, s2) for el in set(els)}
    F = np.zeros(len(H), complex)
    for k0 in range(0, len(H), chunk):
        sl = slice(k0, k0 + chunk)
        T = np.exp(-8 * math.pi ** 2 * np.outer(s2[sl], uiso))          # isotrop, für Atome ohne U_ij
        if aniso:
            Tan = np.exp(-2 * math.pi ** 2 * np.einsum("ni,aij,nj->na", Q[sl], Uc, Q[sl]))
            T[:, aniso] = Tan
        f = np.stack([fel[el][sl] for el in els], axis=1)
        F[sl] = (occ * f * T * np.exp(2j * math.pi * (H[sl] @ X.T))).sum(1)
    return np.abs(F) ** 2


def lp(tth_deg):
    th = np.radians(np.asarray(tth_deg, float) / 2)
    return (1 + np.cos(2 * th) ** 2) / (np.sin(th) ** 2 * np.cos(th))


def reflections(S, lam, tth_max):
    """Reflexliste bis 2θ_max (Kα1) -> [dict(hkl, d, tth, m, F2, I)] nach 2θ, I = Σ|F|²·Lp über zusammenfallende hkl
    (m = deren Zahl), ausgelöschte (I < MIN_REL·max) fehlen."""
    d_min = lam / (2 * math.sin(math.radians(min(tth_max, 179.0)) / 2))
    H, q2 = hkl_list(S, d_min)
    if not len(H):
        return []
    F2 = structure_factors(S, H, q2)
    o = np.argsort(q2)
    H, F2, q2 = H[o], F2[o], q2[o]
    key = np.r_[0, np.cumsum(np.diff(q2) > SAME_D * q2.max())]      # Gruppen fortlaufend gleicher 1/d²
    out = {}
    for h, k_, f2, qq in zip(H, key, F2, q2):
        r = out.setdefault(int(k_), {"hkl": tuple(int(v) for v in h), "q2": float(qq), "m": 0, "F2": 0.0})
        r["m"] += 1
        r["F2"] += float(f2)
        if tuple(h) > r["hkl"]:                          # Vertreter: größtes (h, k, l), also positive Indizes
            r["hkl"] = tuple(int(v) for v in h)
    refl = []
    for r in out.values():
        d = 1 / math.sqrt(r["q2"])
        tth = 2 * math.degrees(math.asin(min(1.0, lam / (2 * d))))
        refl.append(dict(hkl=r["hkl"], d=d, tth=tth, m=r["m"], F2=r["F2"] / r["m"], I=r["F2"] * float(lp(tth))))
    imax = max((r["I"] for r in refl), default=0.0)
    return sorted((r for r in refl if r["I"] >= MIN_REL * imax), key=lambda r: r["tth"])


def pseudo_voigt(x, x0, fwhm, eta):
    """Flächennormiertes Pseudo-Voigt-Profil (gemeinsame Halbwertsbreite), x und x0 in ° 2θ."""
    dx2 = (x - x0) ** 2
    lor = (2 / (math.pi * fwhm)) / (1 + 4 * dx2 / fwhm ** 2)
    gau = math.sqrt(4 * math.log(2) / math.pi) / fwhm * np.exp(-4 * math.log(2) * dx2 / fwhm ** 2)
    return eta * lor + (1 - eta) * gau


def pattern(refl, x, lam1, lam2=None, fwhm=0.1, eta=0.5, zero=0.0, ratio=KA2_RATIO):
    """Berechnetes Diffraktogramm auf dem Raster x [° 2θ], auf das stärkste Maximum = 1 normiert; zero verschiebt die
    Rechnung (2θ + zero). Kα2: Lage aus d und lam2, Intensität ratio · |F|² · Lp(2θ₂). -> (y, Liste der Linien
    [(2θ, I, Kα1?)])."""
    lines = []
    for r in refl:
        lines.append((r["tth"] + zero, r["I"], True))
        if lam2:
            s = lam2 / (2 * r["d"])
            if s < 1:
                t2 = 2 * math.degrees(math.asin(s))
                lines.append((t2 + zero, ratio * r["m"] * r["F2"] * float(lp(t2)), False))
    y = np.zeros_like(np.asarray(x, float))
    if not lines:
        return y, lines
    pos = np.array([p for p, _, _ in lines])
    inten = np.array([i for _, i, _ in lines])
    w = 25 * fwhm
    for k in range(0, len(pos), 400):
        p_, i_ = pos[k:k + 400], inten[k:k + 400]
        near = (x[None, :] > p_[:, None] - w) & (x[None, :] < p_[:, None] + w)
        y += (i_[:, None] * pseudo_voigt(x[None, :], p_[:, None], fwhm, eta) * near).sum(0)
    m = y.max()
    return (y / m if m > 0 else y), lines


def temperature(block):
    """Temperatur der Strukturbestimmung [K] aus der CIF (Messung, sonst Zellbestimmung) oder None."""
    for tag in ("_diffrn_ambient_temperature", "_cell_measurement_temperature"):
        v = block.num(tag)
        if v is not None:
            return v
    return None
