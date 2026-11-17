"""
elucida/core/lifetime.py - Fluoreszenzlebensdauer aus einer Abklingkurve (TCSPC o. ä.).

Modell: y(t) = Σ A_i·exp(−t/τ_i) + B mit einer oder zwei Komponenten und konstantem Untergrund B.
- ohne IRF: Fit ab einem Startpunkt nach dem Maximum (Schwanz), t ab diesem Punkt gezählt;
- mit IRF: IRF (auf Fläche 1, um eine mitgefittete Verschiebung versetzt) diskret mit den Exponentialen gefaltet,
  über die ganze Kurve (gleichmäßiges Zeitraster nötig).
Gewichtung: sind alle Werte nichtnegative ganze Zahlen (Zählraten), Poisson-Gewichte 1/max(y, 1) und reduziertes
χ² = Σ w·r²/(n − p); sonst ungewichtet und kein χ² (ohne bekannte Messunsicherheit hätte es keine Bedeutung).
95-%-Intervalle aus der Kovarianz s²(JᵀWJ)⁻¹ (s² = Σ w·r²/(n − p)) mit t(0,975; n − p).
Amplituden und B linear (variable Projektion), τ (log) und Verschiebung über Levenberg-Marquardt. Mittlere
Lebensdauern nur bei positiven Amplituden: amplitudengewichtet Σ A τ / Σ A, intensitätsgewichtet Σ A τ² / Σ A τ.
"""
from __future__ import annotations

import numpy as np

from elucida.core.uvvis import t_quantile


def is_counts(y) -> bool:
    y = np.asarray(y, float)
    return bool(len(y)) and bool(np.all(y >= 0)) and bool(np.allclose(y, np.round(y)))


def _uniform(t):
    d = np.diff(t)
    return len(d) > 0 and np.allclose(d, d[0], rtol=1e-3, atol=0)


def _columns(tt, taus, irf=None, shift=0.0):
    """Spalten der Designmatrix: je τ ein (gefaltetes) Exponential, dann 1 für den Untergrund."""
    if irf is None:
        cols = [np.exp(-tt / tau) for tau in taus]
    else:
        g = np.clip(np.interp(tt - shift, tt, irf, left=0.0, right=0.0), 0.0, None)
        s = g.sum()
        g = g / s if s > 0 else g
        cols = [np.convolve(g, np.exp(-(tt - tt[0]) / tau))[:len(tt)] for tau in taus]
    return np.column_stack(cols + [np.ones_like(tt)])


def fit_decay(t, y, n_exp=1, irf=None, start=0.0):
    """Abklingkurve fitten. t [ns] aufsteigend; irf: (t_irf, y_irf) oder None; start [ns] nach dem Maximum (nur ohne
    IRF). -> dict(n_exp, A, tau, ci_tau, frac, B, shift, chi2_red, weighted, n, dof, t, fit, resid, t0, tau_amp,
    tau_int, at_bound) oder ValueError (zu wenig Punkte, IRF ohne gleichmäßiges Raster)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    n_exp = 2 if n_exp == 2 else 1
    if irf is None:
        t0 = float(t[int(np.argmax(y))]) + max(0.0, float(start))
        sel = t >= t0 - 1e-12
        tt, yy = t[sel] - t0, y[sel]
        g = None
    else:
        if not _uniform(t):
            raise ValueError("non-uniform time axis")
        t0, tt, yy = float(t[0]), t - float(t[0]), y
        g = np.interp(t, np.asarray(irf[0], float), np.asarray(irf[1], float), left=0.0, right=0.0)
    n_par = 2 * n_exp + 1 + (g is not None)
    if len(tt) < n_par + 3:
        raise ValueError("too few points")
    counts = is_counts(yy)
    w = 1.0 / np.maximum(yy, 1.0) if counts else np.ones_like(yy)
    sw = np.sqrt(w)
    dt = float(np.median(np.diff(tt)))
    span = float(tt[-1] - tt[0]) or dt
    lo, hi = np.log(dt / 10), np.log(span * 100)

    def solve(p):
        taus = np.exp(np.clip(p[:n_exp], lo, hi))
        X = _columns(tt, taus, g, p[n_exp] if g is not None else 0.0)
        c, *_ = np.linalg.lstsq(X * sw[:, None], yy * sw, rcond=None)
        return sw * (yy - X @ c), c, X

    grid = np.linspace(np.log(dt), np.log(span * 2), 24)
    if n_exp == 1:
        starts = [[a] for a in grid]
    else:
        starts = [[a, b] for i, a in enumerate(grid[::2]) for b in grid[::2][i + 1:]]
    starts = [np.array(s_ + ([0.0] if g is not None else []), float) for s_ in starts]
    p = min(starts, key=lambda s_: float(np.sum(solve(s_)[0] ** 2)))
    steps = np.array([1e-4] * n_exp + ([dt * 1e-2] if g is not None else []))
    r, c, X = solve(p)
    cost, lam = float(r @ r), 1e-3
    for _ in range(100):                                # Levenberg-Marquardt auf log τ (und Verschiebung)
        J = np.empty((len(r), len(p)))
        for k in range(len(p)):
            dp = np.zeros_like(p)
            dp[k] = steps[k]
            J[:, k] = (solve(p + dp)[0] - r) / steps[k]
        A_, grad = J.T @ J, J.T @ r
        improved = False
        for _ in range(10):
            try:
                delta = np.linalg.solve(A_ + lam * np.diag(np.diag(A_) + 1e-12), -grad)
            except np.linalg.LinAlgError:
                break
            r2, c2, X2 = solve(p + delta)
            if float(r2 @ r2) < cost:
                p, r, c, X, cost, lam, improved = p + delta, r2, c2, X2, float(r2 @ r2), lam / 3, True
                break
            lam *= 5
        if not improved or np.all(np.abs(delta) < steps * 1e-2):
            break
    at_bound = bool(np.any((p[:n_exp] <= lo + 1e-6) | (p[:n_exp] >= hi - 1e-6)))
    taus = np.exp(np.clip(p[:n_exp], lo, hi))
    shift = float(p[n_exp]) if g is not None else 0.0
    # Kovarianz aller Parameter (A_i, τ_i, B, Verschiebung) über die volle Jacobi-Matrix des Modells
    full = np.concatenate([c[:n_exp], taus, [c[-1]], [shift] if g is not None else []])

    def model(q):
        X_ = _columns(tt, q[n_exp:2 * n_exp], g, q[-1] if g is not None else 0.0)
        return X_ @ np.concatenate([q[:n_exp], [q[2 * n_exp]]])
    f0 = model(full)
    Jf = np.empty((len(tt), len(full)))
    for k in range(len(full)):
        h = 1e-6 * max(abs(full[k]), 1e-3 if k < n_exp or k == 2 * n_exp else dt)
        q1, q2 = full.copy(), full.copy()
        q1[k] += h
        q2[k] -= h
        Jf[:, k] = sw * (model(q1) - model(q2)) / (2 * h)
    dof = len(tt) - len(full)
    s2 = float(np.sum(w * (yy - f0) ** 2)) / dof
    try:
        cov = np.linalg.inv(Jf.T @ Jf) * s2
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        se = np.full(len(full), np.nan)
    tq = t_quantile(0.975, dof)
    A = c[:n_exp]
    order = np.argsort(taus)
    A, taus, se_tau = A[order], taus[order], se[n_exp:2 * n_exp][order]
    ci = [(float(tau - tq * s_), float(tau + tq * s_)) if np.isfinite(s_) else None for tau, s_ in zip(taus, se_tau)]
    pos = bool(np.all(A > 0))
    at = A * taus
    return {"n_exp": n_exp, "A": [float(a) for a in A], "tau": [float(x) for x in taus], "ci_tau": ci,
            "frac": [float(v) for v in at / at.sum()] if pos else None, "B": float(c[-1]), "shift": shift,
            "chi2_red": s2 if counts else None, "weighted": counts, "n": int(len(tt)), "dof": int(dof),
            "t": tt + t0, "fit": f0, "resid": sw * (yy - f0) if counts else yy - f0, "t0": t0,
            "tau_amp": float(at.sum() / A.sum()) if pos else None,
            "tau_int": float((at * taus).sum() / at.sum()) if pos else None, "at_bound": at_bound,
            "irf": g is not None, "start": float(start) if g is None else None}


def rates(phi, tau_ns):
    """k_r = Φ/τ, k_nr = (1 − Φ)/τ in s⁻¹; None, wenn Φ oder τ fehlt oder Φ nicht in (0, 1]."""
    if phi is None or tau_ns is None or not (0 < phi <= 1) or not tau_ns > 0:
        return None, None
    return phi / (tau_ns * 1e-9), (1 - phi) / (tau_ns * 1e-9)


def make_test_decay(taus=(1.5, 6.0), amps=(3000.0, 1500.0), bg=8.0, dt=0.02, n=1024, irf_fwhm=0.12, t_peak=2.0,
                    seed=0):
    """Erfundene TCSPC-Kurve (Poisson-Rauschen) und ihre IRF (Gauß): -> (t, counts, irf_counts) in ns."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * dt
    sig = irf_fwhm / 2.3548
    irf = np.exp(-0.5 * ((t - t_peak) / sig) ** 2)
    ideal = _columns(t, taus, irf) @ np.concatenate([amps, [bg]])
    return t, rng.poisson(ideal).astype(float), rng.poisson(irf / irf.max() * 5000).astype(float)
