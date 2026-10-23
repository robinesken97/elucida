"""uvvis_orbitals.py - Molekülorbitale als Isoflächen im DFT-Tab, Aussehen wie IboView (G. Knizia).

Daten:   Gaussian-Cube (ORCA `orca_plot`, Gaussian `cubegen`): Gitter liegt vor. Werte ψ in a.u. (Bohr^-3/2).
Isowert: wie IboView als Anteil der Orbitaldichte (Standard 80 %): Gitterpunkte nach ψ² absteigend, aufsummieren
         bis zum Anteil; Schwelle = geometrisches Mittel der beiden Nachbarwerte. Wahlweise absolut (a.u.).
Bild:    Raycasting auf dem Gitter (trilinear), je Pixel bis zu 4 Vorderseiten vor dem vordersten Atom, von hinten
         nach vorn überlagert (IboView: Depth Peeling, 4 Schichten, Rückseiten weggelassen). Licht wie IboView: drei
         Lichter (Mayavi), diffus 0.7·c^0.8, Glanz 0.7·(−0.5·c^16 + 1.2·c^64) mit c = n·L (ohne Blickrichtung);
         Deckkraft = 0.6 · diffuser Anteil / |n_z| (Ränder deckender); Aufhellung nach hinten wie IboView.
         Die Orbitale sind ein Rasterbild über den (vektoriellen) Atomen; wo ein Atom davor liegt, bleibt es frei.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

BOHR = 0.529177210903                           # Å

ELEMENTS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
            "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
            "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn").split()

# ---------------------------------------------------------------------------- Aussehen wie IboView
# Zeichenradien (Bohr) und Farben (RasMol „CPKnew“, C = #999999) wie IboView; Kugelradius = 0.4 × Tabelle
IBO_RADII = dict(zip(ELEMENTS, map(float, (
    "0.87 1.6 2.52 2.03 1.58 1.43 1.32 1.29 1.26 1.74 2.91 2.69 2.35 2.11 2.08 2.04 1.97 1.95 3.69 3.33 2.86 2.67 "
    "2.65 2.54 2.61 2.52 2.35 2.2 2.46 2.25 2.38 2.26 2.29 2.25 2.25 2.17 4.27 3.88 3.21 2.96 2.78 2.8 2.5 2.79 2.52 "
    "2.53 2.62 2.65 2.76 2.64 2.66 2.62 2.61 2.39 4.86 4.3 3.67 3.48 3.44 3.43 3.4 3.36 3.35 3.28 3.27 3.23 3.2 3.16 "
    "3.14 3.09 3.16 3.04 2.86 2.88 2.59 2.59 2.59 2.58 2.38 2.53 2.87 2.76 2.86 2.83 2.92 2.68").split())))
IBO_COLORS = {"H": "#FFFFFF", "He": "#FFC0CB", "Li": "#B22121", "B": "#00FF00", "C": "#999999", "N": "#87CEE6",
              "O": "#FF0000", "F": "#DAA520", "Na": "#0000FF", "Mg": "#228B22", "Al": "#696969", "Si": "#DAA520",
              "P": "#FFAA00", "S": "#FFFF00", "Cl": "#00FF00", "Ca": "#696969", "Ti": "#696969", "Cr": "#696969",
              "Mn": "#696969", "Fe": "#FFAA00", "Ni": "#802828", "Cu": "#802828", "Zn": "#802828", "Br": "#802828",
              "Ag": "#696969", "I": "#A020F0", "Ba": "#FFAA00", "Au": "#DAA520"}
IBO_OTHER = "#FF1493"
IBO_BALL = 0.4                                  # Kugelradius = 0.4 × Zeichenradius
IBO_ROD_R = 0.35 * 0.4 / 0.5                    # Stabradius am Atom (Bohr)
IBO_TAPER = 0.72                                # Stab zur Bindungsmitte auf 72 % verjüngt
# drei Lichter (Ansicht: x rechts, y oben, z zum Betrachter) mit Gewicht
IBO_LIGHTS = ((np.array([0.5, 0.5, 0.70710678]), 1.0), (np.array([-0.4330127, -0.25, 0.8660254]), 0.6),
              (np.array([0.4330127, -0.25, 0.8660254]), 0.5))
IBO_REG = {"atom": (0.8, 0.7, 0.4, -0.5), "orbital": (0.8, 0.7, 0.7, -0.5)}   # Exponent, diffus, Glanz, Glanz-Vorfaktor
IBO_FADE = (1.0 * BOHR, 22.0 * BOHR)            # Aufhellung ab 1 Bohr hinter der Mitte, voll weiß nach weiteren 22 Bohr
ISO_FRACTION = 80.0                             # % der Orbitaldichte innerhalb der Fläche
ORB_ALPHA = 0.6
MOLDEN_SPACING = 0.1                            # Å, Gitter für MOs aus Molden (IboView: 12 Punkte/Å)
MAX_LAYERS = 4


def ibo_radius(el):
    """Kugelradius (Å) wie IboView."""
    return IBO_BALL * IBO_RADII.get(el, 1.5) * BOHR


def ibo_color(el):
    return IBO_COLORS.get(el, IBO_OTHER)


def ibo_light(n, kind="atom"):
    """Helligkeit je Normale (…×3, Ansicht) -> (diffus D, Glanz S): Farbe = Grundfarbe·D + S (weiß), wie IboView."""
    e, kd, ks, k3 = IBO_REG[kind]
    D = np.zeros(n.shape[:-1])
    S = np.zeros(n.shape[:-1])
    for L, w in IBO_LIGHTS:
        c = np.clip(n @ L, 0.0, 1.0)
        D += w * kd * c ** e
        S += w * ks * (k3 * c ** 16 + 1.2 * c ** 64)
    return D, S


def ibo_fog(z):
    """Anteil Weiß nach Tiefe z (Å, + zum Betrachter, 0 = Mitte)."""
    return np.clip((-np.asarray(z, float) - IBO_FADE[0]) / IBO_FADE[1], 0.0, 1.0)


def _hsv(h, s, v):
    import colorsys
    return colorsys.hsv_to_rgb((h % 360.0) / 360.0, s, v)


SCHEMES = ("hue", "sat", "opposite")


def orbital_colors(k, scheme="hue"):
    """Farben (+, −) und Deckkraft des k-ten Orbitals wie IboView: je Orbital ein neuer Farbton."""
    if scheme == "sat":
        h = k * 60.0
        return _hsv(h, 0.6, 1.0), _hsv(h, 0.35, 1.0), ORB_ALPHA
    if scheme == "opposite":
        h = -(k + 1) * 60.0
        return _hsv(h + 90.0, 0.5, 1.0), _hsv(h - 90.0, 0.5, 1.0), 0.5
    h = -(k + 1) * 120.0
    return _hsv(h + 25.0, 0.6, 1.0), _hsv(h - 25.0, 0.6, 1.0), ORB_ALPHA


# ---------------------------------------------------------------------------- Cube lesen
def read_cube(path) -> dict:
    """Gaussian-Cube -> dict(title, comment, els, xyz (Å), origin (Å), axes (3×3 Å, Zeile = Schritt), data [Gitter],
    mos [Nummern oder None]). Mehrere Orbitale (Atomzahl negativ, MO-Liste) werden alle gelesen."""
    with open(path, "r", errors="replace") as f:
        title = f.readline().rstrip("\n")
        comment = f.readline().rstrip("\n")
        t = f.readline().split()
        nat = int(t[0])
        origin = np.array([float(x) for x in t[1:4]])
        nval = int(t[4]) if len(t) > 4 else 1
        n, axes = [], []
        for _ in range(3):
            t = f.readline().split()
            n.append(int(t[0]))
            axes.append([float(x) for x in t[1:4]])
        unit = BOHR if n[0] > 0 else 1.0                      # negative Punktzahl: Ångström
        n = [abs(x) for x in n]
        axes = np.array(axes) * unit
        origin = origin * unit
        els, xyz = [], []
        for _ in range(abs(nat)):
            t = f.readline().split()
            z = int(float(t[0]))
            els.append(ELEMENTS[z - 1] if 0 < z <= len(ELEMENTS) else "X")
            xyz.append([float(x) * unit for x in t[2:5]])
        mos = [None]
        rest = f.read().split()
    vals = rest
    if nat < 0:                                              # MO-Liste: Anzahl, dann Nummern
        nm = int(rest[0])
        mos = [int(x) for x in rest[1:1 + nm]]
        vals = rest[1 + nm:]
    elif nval > 1:
        mos = [None] * nval
    m = len(mos)
    need = n[0] * n[1] * n[2] * m
    if len(vals) < need:
        raise ValueError(f"cube: {len(vals)} values, expected {need}")
    a = np.array(vals[:need], dtype=np.float32).reshape(n[0], n[1], n[2], m)
    data = [np.ascontiguousarray(a[..., j]) for j in range(m)]
    return dict(title=title, comment=comment, els=els, xyz=np.array(xyz, float).reshape(-1, 3), origin=origin,
                axes=axes, data=data, mos=mos)


def cube_mo(path, cube=None):
    """MO-Nummer und Spin aus der MO-Liste oder dem Dateinamen (ORCA: „name.mo21a.cube“) -> (Nummer, „a“/„b“/"")."""
    if cube and cube["mos"][0] is not None:
        return cube["mos"][0], ""
    m = re.search(r"mo(\d+)([ab]?)", Path(path).name, re.I)
    return (int(m.group(1)), m.group(2).lower()) if m else (None, "")


def write_cube(path, els, xyz, origin, axes, data, title="Elucida test cube", comment="orbital"):
    """Cube schreiben (Bohr, wie Gaussian/ORCA) – für Testdaten."""
    Z = {e: i + 1 for i, e in enumerate(ELEMENTS)}
    n = data.shape
    with open(path, "w", newline="\n") as f:
        f.write(f"{title}\n{comment}\n")
        f.write(f"{len(els):5d}" + "".join(f"{v / BOHR:12.6f}" for v in origin) + "\n")
        for i in range(3):
            f.write(f"{n[i]:5d}" + "".join(f"{v / BOHR:12.6f}" for v in axes[i]) + "\n")
        for e, p in zip(els, xyz):
            f.write(f"{Z[e]:5d}{float(Z[e]):12.6f}" + "".join(f"{v / BOHR:12.6f}" for v in p) + "\n")
        flat = data.reshape(-1, n[2])
        for row in flat:
            for i in range(0, len(row), 6):
                f.write("".join(f"{v:13.5E}" for v in row[i:i + 6]) + "\n")


# ---------------------------------------------------------------------------- Orbitalenergien
HARTREE_EV = 27.211386245988


def orbital_energies(text) -> dict:
    """Letzte Orbitalenergien einer Ausgabe -> {Spin: [(Nummer, Besetzung, E in eV)]}; Spin "" (geschlossen),
    "a"/"b" (offen). ORCA: Block „ORBITAL ENERGIES“ (Nummern ab 0 wie orca_plot); Gaussian: „Alpha/Beta occ./virt.
    eigenvalues“ (Nummern ab 1 wie cubegen)."""
    out = {}
    i = text.rfind("ORBITAL ENERGIES")
    if i >= 0:
        spin = ""
        for ln in text[i:].splitlines()[1:]:
            t = ln.split()
            if "SPIN UP" in ln:
                spin = "a"
            elif "SPIN DOWN" in ln:
                spin = "b"
            elif len(t) == 4 and t[0].isdigit():
                out.setdefault(spin, []).append((int(t[0]), float(t[1]), float(t[3])))
            elif not t or t[0] in ("NO", "*") or t[0].startswith("*") or set(ln.strip()) == {"-"} and not out:
                continue
            elif out:
                break
        return out
    j = text.rfind("Population analysis using the SCF")
    part = text[j:] if j >= 0 else text
    for spin, key in (("a", "Alpha"), ("b", "Beta")):
        rows = []
        for m in re.finditer(key + r"\s+(occ|virt)\. eigenvalues --(.*)", part):
            for v in re.findall(r"-?\d+\.\d+", m.group(2)):
                rows.append((len(rows) + 1, 1.0 if m.group(1) == "occ" else 0.0, float(v) * HARTREE_EV))
        if rows:
            out[spin] = rows
    if "a" in out and "b" not in out:                           # geschlossenschalig: doppelt besetzt, ohne Spin
        out = {"": [(n, 2.0 * o, e) for n, o, e in out["a"]]}
    return out


def frontier_name(no, spin, table):
    """„HOMO“, „HOMO−2“, „LUMO+1“ … aus den Besetzungen (Spin des Orbitals), sonst None."""
    rows = table.get(spin or "") or table.get("") or table.get("a")       # geschlossenschalig: „mo7a“ = Spin ""
    if not rows or no is None:
        return None
    homo = max((n for n, o, _ in rows if o > 0.5), default=None)
    if homo is None:
        return None
    d = no - homo
    if d <= 0:
        return "HOMO" + (f"\u2212{-d}" if d else "")
    return "LUMO" + (f"+{d - 1}" if d > 1 else "")


def orbital_energy(no, spin, table):
    for n, _, e in table.get(spin) or table.get("") or []:
        if n == no:
            return e
    return None


# ---------------------------------------------------------------------------- Isowert
def iso_for_fraction(data, frac=ISO_FRACTION):
    """Isowert, dessen Fläche frac % von Σψ² (auf dem Gitter) umschließt – wie IboView (iso_threshold)."""
    w = np.sort((np.asarray(data, np.float64).ravel()) ** 2)[::-1]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return 0.0
    i = int(np.searchsorted(c, c[-1] * frac / 100.0, side="right"))
    i = min(max(i, 1), len(w) - 1)
    return float(math.sqrt(math.sqrt(w[i - 1] * w[i])))


def grid_norm(data, axes):
    """Σψ²·dV (Bohr³): ≈ 1, wenn das Gitter das ganze Orbital enthält (sonst ist der Anteil zu groß geschätzt)."""
    dv = abs(np.linalg.det(np.asarray(axes) / BOHR))
    return float(np.sum(np.asarray(data, np.float64) ** 2) * dv)


# ---------------------------------------------------------------------------- Volumen und Raycasting
class Volume:
    """Gitter eines Orbitals: Werte, Gradient (Indexraum), Abbildung Ort (Å) <-> Index."""

    def __init__(self, data, origin, axes):
        self.data = np.ascontiguousarray(data, dtype=np.float32)
        self.n = np.array(self.data.shape)
        self.origin = np.asarray(origin, float)
        self.axes = np.asarray(axes, float)                    # Zeile i = Schritt entlang Index i (Å)
        self.inv = np.linalg.inv(self.axes.T)                  # Ort - origin -> Index
        self.step = float(min(np.linalg.norm(self.axes, axis=1)))
        self._grad = None
        self._flat = self.data.ravel()
        n0, n1, n2 = self.n
        self.strides = np.array([n1 * n2, n2, 1], np.int64)
        self._corner = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)], np.int64) @ self.strides

    def grad(self):
        if self._grad is None:
            self._grad = [np.ascontiguousarray(g, dtype=np.float32).ravel() for g in np.gradient(self.data)]
        return self._grad

    def index_of(self, P):
        return (np.asarray(P, float) - self.origin) @ self.inv.T

    def sample(self, I, fields=None):
        """Trilinear an Indexpositionen I (N×3); außerhalb 0. fields: flache Arrays (Standard: Werte)."""
        fields = [self._flat] if fields is None else fields
        n = self.n
        ok = np.all((I >= 0) & (I <= n - 1.0001), axis=1)
        Ic = np.where(ok[:, None], I, 0.0)
        i0 = np.floor(Ic).astype(np.int64)
        f = (Ic - i0).astype(np.float32)
        base = i0 @ self.strides
        fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
        wts = []
        for cx in (1 - fx, fx):
            for cy in (1 - fy, fy):
                wts.append(cx * cy)
        out = []
        for F in fields:
            acc = np.zeros(len(I), np.float32)
            for c in range(8):
                w = wts[c >> 1] * (fz if c & 1 else 1 - fz)
                acc += w * F[base + self._corner[c]]
            out.append(np.where(ok, acc, 0.0))
        return out if len(out) > 1 else out[0]


TILE = 8                                                        # Pixel je Kachel für die Tiefenbereiche


def render(vol: Volume, iso, R, center, zoff, xlim, ylim, W, H, cplus, cminus, alpha=ORB_ALPHA, occ=None,
           max_layers=MAX_LAYERS, step_frac=0.5, budget=3_000_000):
    """Orbital als RGBA-Bild (H×W×4, Zeile 0 unten, gerade Deckkraft).
    Bildschirm s = R·(p − center) (Å, z zum Betrachter); zoff: Tiefe der Szenenmitte relativ dazu (Aufhellung).
    occ: Tiefe des vordersten Atoms je Pixel (H×W, −inf = frei); nur Flächen davor zählen."""
    img = np.zeros((H, W, 4), np.float32)
    if iso <= 0 or W < 1 or H < 1:
        return img
    R = np.asarray(R, float)
    center = np.asarray(center, float)
    px = (xlim[1] - xlim[0]) / W
    py = (ylim[1] - ylim[0]) / H
    # Bereich mit |ψ| > iso: Gitterpunkte -> Bildschirm, je Kachel kleinste/größte Tiefe (mit Rand)
    sup = np.argwhere(np.abs(vol.data) > iso * 0.9)
    if not len(sup):
        return img
    S = (vol.origin + sup @ vol.axes - center) @ R.T
    m = float(np.linalg.norm(vol.axes.sum(axis=0)))             # Raumdiagonale einer Zelle
    TW, TH = (W + TILE - 1) // TILE, (H + TILE - 1) // TILE
    zmin = np.full((TH, TW), np.inf)
    zmax = np.full((TH, TW), -np.inf)
    tx = np.floor((S[:, 0] - xlim[0]) / (px * TILE)).astype(int)
    ty = np.floor((S[:, 1] - ylim[0]) / (py * TILE)).astype(int)
    k = int(math.ceil(m / min(px, py) / TILE)) + 1
    ok = (tx >= -k) & (tx < TW + k) & (ty >= -k) & (ty < TH + k)
    tx, ty, sz = tx[ok], ty[ok], S[ok, 2]
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            a, b = tx + dx, ty + dy
            o = (a >= 0) & (a < TW) & (b >= 0) & (b < TH)
            np.minimum.at(zmin, (b[o], a[o]), sz[o])
            np.maximum.at(zmax, (b[o], a[o]), sz[o])
    tiles = np.argwhere(np.isfinite(zmin))
    if not len(tiles):
        return img
    step = vol.step * step_frac
    lo = zmin[tiles[:, 0], tiles[:, 1]] - m
    hi = zmax[tiles[:, 0], tiles[:, 1]] + m
    nst = np.ceil((hi - lo) / step).astype(int) + 2
    order = np.argsort(nst)
    dirI = R[2] @ vol.inv.T                                     # Indexschritt je Å Tiefe
    gx = (np.arange(W) + 0.5) * px + xlim[0]
    gy = (np.arange(H) + 0.5) * py + ylim[0]
    cp, cm = np.array(cplus[:3], np.float32), np.array(cminus[:3], np.float32)
    lin = np.arange(TILE)
    pos = 0
    while pos < len(order):
        # Kacheln mit ähnlicher Schrittzahl zusammen (aufsteigend sortiert; Speicher etwa ≤ budget Stützstellen),
        # Schrittzahl = größte der Gruppe, damit keine Kachel zu früh endet
        cnt = max(1, budget // (TILE * TILE * int(nst[order[pos]])))
        while cnt > 1 and cnt * TILE * TILE * int(nst[order[min(pos + cnt, len(order)) - 1]]) > budget:
            cnt //= 2
        sel = order[pos:pos + cnt]
        ns = int(nst[sel].max())
        pos += len(sel)
        ty_, tx_ = tiles[sel, 0], tiles[sel, 1]
        iy = (ty_[:, None, None] * TILE + lin[None, :, None]).repeat(TILE, 2).reshape(len(sel), -1)
        ix = (tx_[:, None, None] * TILE + lin[None, None, :]).repeat(TILE, 1).reshape(len(sel), -1)
        top = np.repeat(hi[sel], TILE * TILE)
        iy, ix = iy.ravel(), ix.ravel()
        inb = (iy < H) & (ix < W)
        iy, ix, top = iy[inb], ix[inb], top[inb]
        if not len(iy):
            continue
        floor_ = occ[iy, ix] if occ is not None else np.full(len(iy), -np.inf)
        floor_ = np.maximum(floor_, np.repeat(lo[sel], TILE * TILE)[inb])
        # Stützstellen von vorn nach hinten: z_j = top − j·step
        base = vol.index_of(np.column_stack([gx[ix], gy[iy], np.zeros(len(ix))]) @ R + center)
        zs = top[:, None] - step * np.arange(ns)[None, :]
        live = zs >= floor_[:, None] - step
        I = base[:, None, :] + zs[..., None] * dirI[None, None, :]
        v = np.zeros(zs.shape, np.float32)
        v[live] = vol.sample(I[live])
        ins = np.abs(v) > iso
        # Eintritt in eine Fläche (außen -> innen, nur Vorderseiten wie IboView)
        ent = ~ins[:, :-1] & ins[:, 1:]
        r_, j_ = np.nonzero(ent)
        if not len(r_):
            continue
        a0, a1 = np.abs(v[r_, j_]), np.abs(v[r_, j_ + 1])
        t = np.clip((iso - a0) / np.maximum(a1 - a0, 1e-12), 0, 1)
        zc = zs[r_, j_] - t * step
        keep = zc > floor_[r_]
        r_, j_, t, zc = r_[keep], j_[keep], t[keep], zc[keep]
        if not len(r_):
            continue
        # je Strahl die hintersten max_layers (IboView schält von hinten), dann von hinten nach vorn überlagern
        o = np.lexsort((zc, r_))                                 # je Strahl aufsteigend in z = von hinten
        r_, j_, t, zc = r_[o], j_[o], t[o], zc[o]
        first = np.r_[True, r_[1:] != r_[:-1]]
        rank = np.arange(len(r_)) - np.maximum.accumulate(np.where(first, np.arange(len(r_)), 0))
        keep = rank < max_layers
        r_, j_, t, zc = r_[keep], j_[keep], t[keep], zc[keep]
        Ic = I[r_, j_] + t[:, None] * (I[r_, j_ + 1] - I[r_, j_])
        g = np.column_stack(vol.sample(Ic, vol.grad()))
        sign = np.sign(v[r_, j_ + 1])
        nw = -(sign[:, None] * g) @ vol.inv                     # Index-Gradient -> Ort; nach außen (kleineres |ψ|)
        nv = nw @ R.T
        nv /= np.maximum(np.linalg.norm(nv, axis=1), 1e-12)[:, None]
        D, Sp = ibo_light(nv, "orbital")
        base_c = np.where((sign > 0)[:, None], cp, cm)
        col = np.clip(base_c * D[:, None] + Sp[:, None], 0, 1)
        fog = ibo_fog(zc + zoff)[:, None]
        col = col + (1 - col) * fog
        a = np.clip(alpha * D / np.clip(np.abs(nv[:, 2]), 0.1, 1.0), 0, 1)
        # Überlagern je Strahl (Schicht für Schicht, hinterste zuerst)
        C = np.zeros((len(iy), 3), np.float32)
        A = np.zeros(len(iy), np.float32)
        rank = rank[keep]
        for lay in range(max_layers):
            s = rank == lay
            if not s.any():
                break
            rr, aa = r_[s], a[s]
            C[rr] = col[s] * aa[:, None] + C[rr] * (1 - aa[:, None])
            A[rr] = aa + A[rr] * (1 - aa)
        hit = A > 0
        img[iy[hit], ix[hit], :3] = C[hit] / A[hit, None]
        img[iy[hit], ix[hit], 3] = A[hit]
    return img


# ---------------------------------------------------------------------------- Tiefe der Atome (Verdeckung)
def occluder_depth(spheres, rods, xlim, ylim, W, H):
    """Tiefe der vordersten Atomoberfläche je Pixel (−inf = frei). spheres: (x, y, z, r); rods: (x0, y0, z0, x1, y1,
    z1, r0, r1) – Kegelstumpf, Tiefe über die Achse + Halbkreisprofil (Achse nahe der Bildebene genügt hier)."""
    D = np.full((H, W), -np.inf, np.float32)
    px = (xlim[1] - xlim[0]) / W
    py = (ylim[1] - ylim[0]) / H

    def window(x0, x1, y0, y1):
        i0 = max(0, int((x0 - xlim[0]) / px))
        i1 = min(W, int((x1 - xlim[0]) / px) + 2)
        j0 = max(0, int((y0 - ylim[0]) / py))
        j1 = min(H, int((y1 - ylim[0]) / py) + 2)
        if i0 >= i1 or j0 >= j1:
            return None
        X = (np.arange(i0, i1) + 0.5) * px + xlim[0]
        Y = (np.arange(j0, j1) + 0.5) * py + ylim[0]
        return (slice(j0, j1), slice(i0, i1)), X[None, :], Y[:, None]

    for x, y, z, r in spheres:
        w = window(x - r, x + r, y - r, y + r)
        if w is None:
            continue
        sl, X, Y = w
        d2 = r * r - (X - x) ** 2 - (Y - y) ** 2
        zz = np.where(d2 > 0, z + np.sqrt(np.maximum(d2, 0)), -np.inf)
        D[sl] = np.maximum(D[sl], zz)
    for x0, y0, z0, x1, y1, z1, r0, r1 in rods:
        rr = max(r0, r1)
        w = window(min(x0, x1) - rr, max(x0, x1) + rr, min(y0, y1) - rr, max(y0, y1) + rr)
        if w is None:
            continue
        sl, X, Y = w
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            continue
        t = ((X - x0) * dx + (Y - y0) * dy) / L2
        dist2 = (X - x0 - t * dx) ** 2 + (Y - y0 - t * dy) ** 2
        rt = r0 + (r1 - r0) * np.clip(t, 0, 1)
        d2 = rt * rt - dist2
        zz = np.where((t >= 0) & (t <= 1) & (d2 > 0), z0 + t * (z1 - z0) + np.sqrt(np.maximum(d2, 0)), -np.inf)
        D[sl] = np.maximum(D[sl], zz)
    return D


# ---------------------------------------------------------------------------- Molden (Gauß-Basis)
# Kartesische Reihenfolge im Molden-Format; kugelförmige Funktionen m = 0, +1, −1, +2, −2 …
_MOLDEN_CART = {0: ["", ], 1: ["x", "y", "z"], 2: ["xx", "yy", "zz", "xy", "xz", "yz"],
                3: ["xxx", "yyy", "zzz", "xyy", "xxy", "xxz", "xzz", "yzz", "yyz", "xyz"],
                4: ["xxxx", "yyyy", "zzzz", "xxxy", "xxxz", "xyyy", "yyyz", "xzzz", "yzzz", "xxyy", "xxzz", "yyzz",
                    "xxyz", "xyyz", "xyzz"]}
_L = {"s": 0, "p": 1, "d": 2, "f": 3, "g": 4, "sp": -1}


def _mono(word):
    return (word.count("x"), word.count("y"), word.count("z"))


def _cart(l):
    """Alle Monome x^a y^b z^c mit a+b+c = l (feste interne Reihenfolge)."""
    return [(a, b, l - a - b) for a in range(l, -1, -1) for b in range(l - a, -1, -1)]


def _poly_mul(p, q):
    out = {}
    for k1, c1 in p.items():
        for k2, c2 in q.items():
            k = (k1[0] + k2[0], k1[1] + k2[1], k1[2] + k2[2])
            out[k] = out.get(k, 0.0) + c1 * c2
    return out


def solid_harmonic(l, m):
    """Reelle Kugelflächenfunktion r^l·Y_lm als Polynom {(a, b, c): Koeffizient}, ohne Condon-Shortley-Phase,
    unnormiert (m > 0: cos-Typ, m < 0: sin-Typ). Normiert wird später numerisch über die Überlappung."""
    am = abs(m)
    xy = {}
    for k in range(am + 1):                                       # (x + i y)^|m|: Real- bzw. Imaginärteil
        if (k % 2 == 0) == (m >= 0):
            sign = (-1) ** (k // 2)
            xy[(am - k, k, 0)] = xy.get((am - k, k, 0), 0.0) + sign * math.comb(am, k)
    zr = {}
    for k in range((l - am) // 2 + 1):
        c = (-1) ** k * math.comb(l, k) * math.comb(2 * l - 2 * k, l) * math.factorial(l - 2 * k) / \
            math.factorial(l - 2 * k - am)
        r2 = {(0, 0, 0): 1.0}
        for _ in range(k):
            r2 = _poly_mul(r2, {(2, 0, 0): 1.0, (0, 2, 0): 1.0, (0, 0, 2): 1.0})
        term = _poly_mul(r2, {(0, 0, l - 2 * k - am): c})
        for key, v in term.items():
            zr[key] = zr.get(key, 0.0) + v
    return {k: v for k, v in _poly_mul(zr, xy).items() if abs(v) > 1e-12}


def _sph_order(l):
    return [0] + [s * m for m in range(1, l + 1) for s in (1, -1)]


def parse_molden(text) -> dict:
    """Molden-Datei -> dict(title, els, xyz (Bohr), shells [(Atom, l, Exponenten, Koeffizienten)], pure {l: bool},
    mos [dict(sym, energy (Eh), spin "a"/"b", occ, c (Array))], orca)."""
    sec, out = None, dict(title="", els=[], xyz=[], shells=[], pure={2: False, 3: False, 4: False}, mos=[])
    lines = text.splitlines()
    unit = 1.0
    i = 0
    atom_ix = {}
    while i < len(lines):
        ln = lines[i].strip()
        low = ln.lower()
        if ln.startswith("["):
            tag = low.split("]")[0] + "]"
            sec = tag
            if tag == "[atoms]":
                unit = 1.0 if "au" in low.split("]")[1] else 1.0 / BOHR
            for flag, ls in (("[5d]", {2: True, 3: True}), ("[5d7f]", {2: True, 3: True}),
                             ("[5d10f]", {2: True, 3: False}), ("[7f]", {3: True}), ("[9g]", {4: True})):
                if tag == flag:
                    out["pure"].update(ls)
            i += 1
            continue
        if sec == "[title]" and ln:
            out["title"] += ln + " "
        elif sec == "[atoms]" and ln:
            t = ln.split()
            atom_ix[int(t[1])] = len(out["els"])
            z = int(t[2])
            out["els"].append(ELEMENTS[z - 1] if 0 < z <= len(ELEMENTS) else t[0])
            out["xyz"].append([float(v) * unit for v in t[3:6]])
        elif sec == "[gto]" and ln:
            t = ln.split()
            at = atom_ix.get(int(t[0]), int(t[0]) - 1)
            i += 1
            while i < len(lines) and lines[i].strip():
                t = lines[i].split()
                if not t[0].isalpha():
                    break
                l, n = _L[t[0].lower()], int(t[1])
                ex, co = [], []
                for j in range(n):
                    v = lines[i + 1 + j].replace("D", "E").replace("d", "e").split()
                    ex.append(float(v[0]))
                    co.append([float(x) for x in v[1:]])
                if l == -1:                                       # sp-Schale: s und p mit eigenen Koeffizienten
                    out["shells"].append((at, 0, np.array(ex), np.array([c[0] for c in co])))
                    out["shells"].append((at, 1, np.array(ex), np.array([c[1] for c in co])))
                else:
                    out["shells"].append((at, l, np.array(ex), np.array([c[0] for c in co])))
                i += 1 + n
            continue
        elif sec == "[mo]" and "=" in ln:
            mo = dict(sym="", energy=0.0, spin="a", occ=0.0)
            while i < len(lines) and "=" in lines[i]:
                k, v = lines[i].split("=", 1)
                k, v = k.strip().lower(), v.strip()
                if k == "sym":
                    mo["sym"] = v
                elif k == "ene":
                    mo["energy"] = float(v.replace("D", "E"))
                elif k == "spin":
                    mo["spin"] = "b" if v.lower().startswith("beta") else "a"
                elif k == "occup":
                    mo["occ"] = float(v.replace("D", "E"))
                i += 1
            c = {}
            while i < len(lines) and lines[i].strip() and "=" not in lines[i] and not lines[i].lstrip().startswith("["):
                t = lines[i].split()
                c[int(t[0])] = float(t[1].replace("D", "E"))
                i += 1
            n = max(c) if c else 0
            mo["c"] = np.array([c.get(j + 1, 0.0) for j in range(n)])
            out["mos"].append(mo)
            continue
        i += 1
    out["xyz"] = np.array(out["xyz"], float).reshape(-1, 3)
    out["orca"] = "orca" in out["title"].lower()
    if not out["els"] or not out["shells"] or not out["mos"]:
        raise ValueError("Molden: [Atoms], [GTO] or [MO] missing")
    return out


def _prim_norm(a, l):
    """Norm von x^l·exp(−a r²) (axiale Funktion): (2a/π)^{3/4} (4a)^{l/2} / √(2l−1)!!"""
    df = 1.0
    for k in range(2 * l - 1, 0, -2):
        df *= k
    return (2 * a / math.pi) ** 0.75 * (4 * a) ** (l / 2) / math.sqrt(df)


def _overlap_1d(la, lb, PA, PB, p):
    """1D-Überlappungen (Obara–Saika) für Paare: S[i][j] (Arrays), i ≤ la, j ≤ lb, ohne Vorfaktor."""
    S = [[None] * (lb + 1) for _ in range(la + 1)]
    S[0][0] = np.sqrt(np.pi / p)
    h = 0.5 / p
    for i in range(la + 1):
        for j in range(lb + 1):
            if i == 0 and j == 0:
                continue
            if i > 0:
                v = PA * S[i - 1][j]
                if i > 1:
                    v = v + (i - 1) * h * S[i - 2][j]
                if j > 0:
                    v = v + j * h * S[i - 1][j - 1]
            else:
                v = PB * S[i][j - 1]
                if j > 1:
                    v = v + (j - 1) * h * S[i][j - 2]
            S[i][j] = v
    return S


class Basis:
    """Gauß-Basis einer Molden-Datei: AO-Transformationen, Überlappung, Auswertung von MOs auf Gittern.
    Jede AO wird numerisch auf 1 normiert (Molden-Standard). Die Konvention (Koeffizienten bezogen auf normierte oder
    rohe Primitive, Vorzeichen der f/g-Funktionen ±3/±4 wie ORCA) wird an CᵀSC = 1 geprüft: die Variante mit der
    kleinsten Abweichung gilt; über MAX_ORTH_ERR wird die Datei abgelehnt (nicht raten)."""

    MAX_ORTH_ERR = 1e-3

    def __init__(self, m):
        self.m = m
        self.centers = np.asarray(m["xyz"], float)
        self.shells = []
        for at, l, ex, co in m["shells"]:
            pure = l >= 2 and m["pure"].get(l, False)
            out = _sph_order(l) if pure else [_mono(w) for w in _MOLDEN_CART[l]]
            self.shells.append(dict(at=at, l=l, ex=np.asarray(ex, float), co=np.asarray(co, float), pure=pure,
                                    out=out, cart=_cart(l)))
        self.nao = sum(len(s["out"]) for s in self.shells)
        self.variant, self.err = None, None

    def _T(self, sh, sign):
        """Matrix AO (Dateireihenfolge) × Monome der Schale, unnormiert."""
        idx = {c: k for k, c in enumerate(sh["cart"])}
        T = np.zeros((len(sh["out"]), len(sh["cart"])))
        for r, o in enumerate(sh["out"]):
            if sh["pure"]:
                for mono, v in solid_harmonic(sh["l"], o).items():
                    T[r, idx[mono]] = v
                if sign == "orca" and ((sh["l"] == 3 and abs(o) == 3) or (sh["l"] == 4 and abs(o) >= 3)):
                    T[r] *= -1
            else:
                T[r, idx[o]] = 1.0
        return T

    def _weights(self, sh, prim):
        return sh["co"] * np.array([_prim_norm(a, sh["l"]) for a in sh["ex"]]) if prim == "norm" else sh["co"]

    def _cart_overlap(self, prim):
        """Überlappung der kartesischen Schalenfunktionen (Σ Gewicht · Primitive) aller Schalenpaare -> {(i, j): Block}.
        Vektorisiert je Drehimpulspaar über alle Schalenpaare (Primitive auf gleiche Zahl aufgefüllt); weit entfernte
        Paare (Überlappung < e^−40) entfallen."""
        sh = self.shells
        n = len(sh)
        npr = max(len(s["ex"]) for s in sh)
        EX = np.ones((n, npr))
        W = np.zeros((n, npr))
        for i, s in enumerate(sh):
            k = len(s["ex"])
            EX[i, :k] = s["ex"]
            W[i, :k] = self._weights(s, prim)
        C = self.centers[[s["at"] for s in sh]]
        L = np.array([s["l"] for s in sh])
        amin = np.array([s["ex"].min() for s in sh])
        blocks = {}
        I, J = np.triu_indices(n)
        AB2 = np.sum((C[I] - C[J]) ** 2, axis=1)
        keep = amin[I] * amin[J] / (amin[I] + amin[J]) * AB2 < 40.0
        I, J, AB2 = I[keep], J[keep], AB2[keep]
        for la in range(L.max() + 1):
            for lb in range(L.max() + 1):
                sel = np.nonzero((L[I] == la) & (L[J] == lb))[0]
                ca, cb = _cart(la), _cart(lb)
                ax, ay, az = (np.array([c[d] for c in ca]) for d in range(3))
                bx, by, bz = (np.array([c[d] for c in cb]) for d in range(3))
                for k0 in range(0, len(sel), 4000):
                    ss = sel[k0:k0 + 4000]
                    i_, j_ = I[ss], J[ss]
                    a = EX[i_][:, :, None]
                    b = EX[j_][:, None, :]
                    p = a + b
                    K = np.exp(-a * b / p * AB2[ss][:, None, None]) * W[i_][:, :, None] * W[j_][:, None, :]
                    A, B = C[i_], C[j_]
                    S1 = []
                    for d in range(3):
                        Pd = (a * A[:, d, None, None] + b * B[:, d, None, None]) / p
                        S1.append(_overlap_1d(la, lb, Pd - A[:, d, None, None], Pd - B[:, d, None, None], p))
                    Sx = np.array([[S1[0][u][v] for v in range(lb + 1)] for u in range(la + 1)])
                    Sy = np.array([[S1[1][u][v] for v in range(lb + 1)] for u in range(la + 1)])
                    Sz = np.array([[S1[2][u][v] for v in range(lb + 1)] for u in range(la + 1)])
                    # (la+1, lb+1, P, ni, nj) -> Block (P, nu, nv)
                    prod = Sx[ax[:, None], bx[None, :]] * Sy[ay[:, None], by[None, :]] * Sz[az[:, None], bz[None, :]]
                    blk = np.einsum("uvpij,pij->puv", prod, K)
                    for q, (i, j) in enumerate(zip(i_, j_)):
                        blocks[(int(i), int(j))] = blk[q]
        return blocks

    def setup(self, mos=None):
        """Konvention bestimmen, Normierung je AO setzen. -> größte Abweichung von CᵀSC = 1."""
        C = np.array([mo["c"] for mo in (mos or self.m["mos"])]).T
        if C.shape[0] != self.nao:
            raise ValueError(f"Molden: {C.shape[0]} MO coefficients, basis has {self.nao} functions")
        self.errors = {}
        need_sign = any(s["pure"] and s["l"] >= 3 for s in self.shells)
        best = None
        for prim in ("norm", "raw"):
            blocks = self._cart_overlap(prim)
            for sign in ("std", "orca") if need_sign else ("std",):
                Ts = [self._T(s, sign) for s in self.shells]
                off = np.cumsum([0] + [len(s["out"]) for s in self.shells])
                S = np.zeros((self.nao, self.nao))
                for (i, j), blk in blocks.items():
                    v = Ts[i] @ blk @ Ts[j].T
                    S[off[i]:off[i + 1], off[j]:off[j + 1]] = v
                    S[off[j]:off[j + 1], off[i]:off[i + 1]] = v.T
                nrm = 1 / np.sqrt(np.diag(S))
                Sn = S * nrm[:, None] * nrm[None, :]
                err = float(np.abs(C.T @ Sn @ C - np.eye(C.shape[1])).max())
                self.errors[(prim, sign)] = err
                if best is None or err < best[0]:
                    best = (err, (prim, sign), Ts, nrm)
        self.err, self.variant, self._Ts, self._nrm = best
        return self.err

    def evaluate(self, c, P, eps=1e-9):
        """MO mit Koeffizienten c an Punkten P (N×3, Bohr) -> Werte (a.u.)."""
        if self.variant is None:
            self.setup()
        prim = self.variant[0]
        val = np.zeros(len(P))
        off = 0
        for sh, T in zip(self.shells, self._Ts):
            k = len(sh["out"])
            w = (c[off:off + k] * self._nrm[off:off + k]) @ T          # Gewichte je Monom
            off += k
            if not np.any(np.abs(w) > 1e-14):
                continue
            wt = self._weights(sh, prim)
            A = self.centers[sh["at"]]
            amin = float(sh["ex"].min())
            amp = float(np.abs(wt).sum() * np.abs(w).sum())
            rc2 = max(0.0, math.log(max(amp, eps) / eps) / amin) + 1.0
            d = P - A
            r2 = np.einsum("ij,ij->i", d, d)
            sel = np.nonzero(r2 < rc2 * (1 + 0.1 * sh["l"]) + 4.0 * sh["l"])[0]
            if not len(sel):
                continue
            ds, rs = d[sel], r2[sel]
            R = np.exp(-np.outer(rs, sh["ex"])) @ wt
            ang = np.zeros(len(sel))
            for (a, b, cc), wk in zip(sh["cart"], w):
                if wk:
                    ang += wk * ds[:, 0] ** a * ds[:, 1] ** b * ds[:, 2] ** cc
            val[sel] += ang * R
        return val


def molden_grid(basis: Basis, c, spacing=0.12, margin=4.0, thresh=1e-3):
    """MO auf einem Gitter (Å): grob über Atome ± margin, dann fein (spacing Å) über den Bereich mit |ψ| > thresh
    (+1 Å). -> (Werte float32, origin Å, axes Å) wie ein Cube."""
    X = basis.centers * BOHR
    lo, hi = X.min(axis=0) - margin, X.max(axis=0) + margin
    hc = 0.35
    gc = [np.arange(lo[d], hi[d] + hc, hc) for d in range(3)]
    G = np.stack(np.meshgrid(*gc, indexing="ij"), -1).reshape(-1, 3)
    v = basis.evaluate(c, G / BOHR)
    big = np.abs(v) > thresh
    if big.any():
        lo, hi = G[big].min(axis=0) - 1.0, G[big].max(axis=0) + 1.0
    n = np.ceil((hi - lo) / spacing).astype(int) + 1
    g = [lo[d] + spacing * np.arange(n[d]) for d in range(3)]
    out = np.empty(int(np.prod(n)), np.float32)
    G = np.stack(np.meshgrid(*g, indexing="ij"), -1).reshape(-1, 3)
    for k in range(0, len(G), 400_000):
        out[k:k + 400_000] = basis.evaluate(c, G[k:k + 400_000] / BOHR)
    return out.reshape(tuple(n)), lo, np.eye(3) * spacing


def molden_table(m):
    """Orbitalenergien aus der Molden-Datei wie orbital_energies: {Spin: [(Nummer, Besetzung, eV)]}.
    Nummern je Spin ab 0 (ORCA) bzw. ab 1 (andere); ohne β-Orbitale Spin ""."""
    base = 0 if m.get("orca") else 1
    out = {}
    for mo in m["mos"]:
        rows = out.setdefault(mo["spin"], [])
        rows.append((len(rows) + base, mo["occ"], mo["energy"] * HARTREE_EV))
    if set(out) == {"a"}:
        out = {"": out["a"]}
    return out


def molden_index(m, no, spin):
    """Index in m["mos"] für Nummer/Spin (wie molden_table)."""
    base = 0 if m.get("orca") else 1
    k = 0
    for i, mo in enumerate(m["mos"]):
        if mo["spin"] == (spin or "a"):
            if k + base == no:
                return i
            k += 1
    return None


# ---------------------------------------------------------------------------- Testdaten
def make_test_cube(path, n=48):
    """Ethen mit einem π-artigen Orbital (p_z an beiden C, gleiche Phase; zwei Lappen ober-/unterhalb der Ebene)."""
    els = ["C", "C", "H", "H", "H", "H"]
    xyz = np.array([[-0.667, 0, 0], [0.667, 0, 0], [-1.232, 0.923, 0], [-1.232, -0.923, 0],
                    [1.232, 0.923, 0], [1.232, -0.923, 0]])
    lo, hi = -5.0, 5.0
    g = np.linspace(lo, hi, n)
    h = g[1] - g[0]
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    a = 0.9 * BOHR ** 2                                          # Exponent (Å^-2)
    psi = sum(Z * np.exp(-a / BOHR ** 2 * 0.8 * ((X - c[0]) ** 2 + (Y - c[1]) ** 2 + Z ** 2)) for c in xyz[:2])
    dv = (h / BOHR) ** 3
    psi = psi / math.sqrt(float(np.sum(psi ** 2)) * dv)
    write_cube(path, els, xyz, np.array([lo, lo, lo]), np.eye(3) * h, psi.astype(np.float32),
               comment="pi orbital (test)")
    return path


# ---------------------------------------------------------------------------- Bild in der Abbildung
ORB_MAX_DPI = 300                               # Export: Orbitalbild höchstens so fein (PDF/SVG eingebettet)
DRAG_SCALE = 3                                  # beim Drehen: Bild mit 1/3 der Auflösung (flüssig), danach voll

from matplotlib.image import AxesImage  # noqa: E402


class OrbitalImage(AxesImage):
    """Orbital als Bild über den Atomen. Gerechnet wird erst beim Zeichnen, in der Auflösung des Ziels (Vorschau:
    Bildschirmpixel, Export: dpi, höchstens ORB_MAX_DPI) und neu nur, wenn Ansicht oder Größe sich ändern."""

    def __init__(self, ax, fig_obj, orb):
        super().__init__(ax, origin="lower", interpolation="bilinear")
        self.F, self.orb = fig_obj, orb
        self.drag = False
        self._key = None
        self.set_data(np.zeros((2, 2, 4), np.float32))
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        self.set_extent((x0, x1, y0, y1))

    def make_image(self, renderer, magnification=1.0, unsampled=False):
        ax = self.axes
        bb = ax.bbox
        # Zielpixel (Agg: Bildschirm/PNG; PDF/SVG: Punkte × Vergrößerung = dpi des Exports) -> wirksame dpi begrenzen
        w_in = ax.get_position().width * ax.figure.get_figwidth()
        dpi = bb.width * magnification / max(w_in, 1e-9)
        f = min(1.0, ORB_MAX_DPI / max(dpi, 1e-9)) / (DRAG_SCALE if self.drag else 1)
        W = max(2, int(round(bb.width * magnification * f)))
        H = max(2, int(round(bb.height * magnification * f)))
        xl, yl = tuple(ax.get_xlim()), tuple(ax.get_ylim())
        key = (W, H, self.F.R.tobytes(), xl, yl)
        if key != self._key:
            self._key = key
            o = self.orb
            occ, zoff = self.F.occluder(xl, yl, W, H)
            img = render(o["vol"], o["iso"], self.F.R, self.F.center, zoff, xl, yl, W, H, o["plus"], o["minus"],
                         o.get("alpha", ORB_ALPHA), occ - zoff)
            self.set_data(img)
            self.set_extent((xl[0], xl[1], yl[0], yl[1]))
        return super().make_image(renderer, magnification, unsampled)


def support_points(vol: Volume, iso):
    """Orte (Å) der Gitterpunkte mit |ψ| > iso (für Bildausschnitt und Zuschnitt)."""
    key = ("sup", float(iso))
    cache = vol.__dict__.setdefault("_cache", {})
    if key not in cache:
        idx = np.argwhere(np.abs(vol.data) > iso)
        cache[key] = vol.origin + idx @ vol.axes
    return cache[key]


def make_test_molden(path, orca=False):
    """Testdatei: H2 (STO-3G, R = 1.4 Bohr, σg/σu analytisch normiert) und weit entfernt ein Atom mit je einer
    s-, p-, d-, f-, g-Schale (kugelförmig, eine Primitive), MOs = einzelne AOs. Orthonormal nur, wenn Überlappung,
    Kugelflächenfunktionen und Normierung stimmen. orca: Koeffizienten bezogen auf rohe Primitive, Titel wie orca_2mkl."""
    ex = [3.42525091, 0.62391373, 0.16885540]
    co = [0.15432897, 0.53532814, 0.44463454]
    # Überlappung der beiden 1s (STO-3G) bei R = 1.4 Bohr
    S = 0.0
    for a, ca in zip(ex, co):
        for b, cb in zip(ex, co):
            p = a + b
            S += ca * cb * _prim_norm(a, 0) * _prim_norm(b, 0) * (math.pi / p) ** 1.5 * math.exp(-a * b / p * 1.96)
    g, u = 1 / math.sqrt(2 * (1 + S)), 1 / math.sqrt(2 * (1 - S))
    lines = ["[Molden Format]", "[Title]", " created by orca_2mkl (test)" if orca else " Elucida test", "[Atoms] AU",
             "H     1    1   0.0000000000   0.0000000000   0.0000000000",
             "H     2    1   0.0000000000   0.0000000000   1.4000000000",
             "Ne    3   10  30.0000000000   0.0000000000   0.0000000000", "[GTO]"]

    def shell(t, exps, coefs, l):
        out = [f" {t}   {len(exps)} 1.00"]
        for a, c in zip(exps, coefs):
            out.append(f"  {a:18.10E} {c * (_prim_norm(a, l) if orca else 1.0):18.10E}")
        return out
    for at in (1, 2):
        lines += [f"  {at} 0"] + shell("s", ex, co, 0) + [""]
    lines += ["  3 0"]
    for t, l in (("s", 0), ("p", 1), ("d", 2), ("f", 3), ("g", 4)):
        lines += shell(t, [1.1], [1.0], l)
    lines += ["", "[5D7F]", "[9G]", "[MO]"]
    nao = 2 + 1 + 3 + 5 + 7 + 9
    mos = [({1: g, 2: g}, -0.578, 2.0), ({1: u, 2: -u}, 0.671, 0.0)]
    mos += [({k: 1.0}, 1.0 + 0.1 * k, 0.0) for k in range(3, nao + 1)]
    for c, e, o in mos:
        lines += [" Sym= A", f" Ene= {e:.6f}", " Spin= Alpha", f" Occup= {o:.6f}"]
        lines += [f"{k:5d} {c.get(k, 0.0):14.8f}" for k in range(1, nao + 1)]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
