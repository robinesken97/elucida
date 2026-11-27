"""elucida/tabs/dft_acid.py - Reiter „ACID“ des DFT-Tabs: Isofläche der Anisotropie der induzierten Stromdichte
(ACID, Herges/Geuenich) auf dem Kugel-Stab-Modell, entweder aus den POV-Ray-Dateien des AICD-Programms (`Isoober.inc`
mit Dreiecksnetz und Stromdichtepfeilen + `Molekuel.inc`, Leser `formats.aicd`) oder aus einem Gaussian-Cube des
Skalarfelds. Aufbau wie 3D-NICS (`dft_pages`): links Karten „ACID-Rechnung“ (Daten) und „ACID-Abbildung“
(Darstellung), rechts nur das Bild. Zustand in tab.st["acid"].

Nichts wird berechnet: Fläche, Pfeile und Magnetfeldrichtung stehen so in den AICD-Dateien (Pfeile nur ausgedünnt oder
skaliert), das Skalarfeld kommt fertig aus dem Cube; die Gaussian-Ausgabe (NMR=CSGT, IOp(10/93)) liefert nur
Methode/Basis für die Unterschrift.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import numpy as np
from elucida.app.canvas_theme import register as register_canvas
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS
from elucida.formats import aicd as AICD
from elucida.formats.calc import parse_gaussian, read_text
from elucida.formats.orbital_files import read_cube
from elucida.tabs import base as TABS

# Vorgabe wie die SI des Nutzers (ACID-Abbildungen mit allen Orbitalen: Isowert 0.045, gelbe Fläche)
# Pfeile wie AICD/POV-Ray (Zylinder Green, Kegel Red), Magnetfeldpfeil dunkelgrün wie in der Vorlage
ACID_DEFAULT = dict(cube="", log="", inc="", mol="", geom="", iso=0.045, color="#e6d81e", alpha=0.9, view=None,
                    zoom=1.0, pan=[0.0, 0.0], arrows=True, arrow_scale=2.5, arrow_density=100.0,
                    color_shaft="#00ff00", color_head="#ff0000", field=True, color_field="#008000")
# arrow_scale 2.5: AICD schreibt Pfeile von ~0.25 Å Länge (öffentliche Ausgabe AICD 3.0.4); in 1.00 × waren sie im Bild
# nur Punkte. 2.5 macht sie im Beispiel und in der öffentlichen Datei erkennbar (gespeicherte Werte bleiben)
LIGHT = np.array([0.45, 0.55, 1.0]) / np.linalg.norm([0.45, 0.55, 1.0])   # Licht oben rechts vorn (wie die Orbitale)
MIN_ARROW_PX = 0.6                                       # Pfeile nie dünner als so viele Pixel (sonst unsichtbar)
CITATION = ("R. Herges, D. Geuenich, <i>J. Phys. Chem. A</i> <b>2001</b>, <i>105</i>, 3214–3220; D. Geuenich, K. Hess, "
            "F. Köhler, R. Herges, <i>Chem. Rev.</i> <b>2005</b>, <i>105</i>, 3758–3772")


def read_acid_cube(path) -> dict:
    """Cube mit dem ACID-Skalarfeld -> dict wie `read_cube` (ein Datensatz). ACID ist nie negativ: ein Feld mit
    deutlich negativen Werten (Orbital, Spindichte) oder ohne Atome wird abgelehnt."""
    c = read_cube(path)
    if len(c["data"]) != 1 or not len(c["els"]):
        raise ValueError(T("acid_bad_cube"))
    v = c["data"][0]
    hi = float(np.nanmax(v))
    if not np.isfinite(hi) or hi <= 0 or float(np.nanmin(v)) < -1e-3 * hi:
        raise ValueError(T("acid_bad_cube"))
    return c


def read_acid_log(text) -> dict:
    """Gaussian-Ausgabe der CSGT-Rechnung für ACID -> parse_gaussian-Ergebnis; ohne NMR=CSGT und IOp(10/93) abgelehnt."""
    c = parse_gaussian(text)
    route = " ".join(c.get("keywords") or []).lower()
    if not re.search(r"nmr\s*=\s*\(?[^)\s]*csgt", route) or not re.search(r"iop\([^)]*10/93=", route):
        raise ValueError(T("acid_bad_log"))
    return c


def orbital_selection(c) -> bool:
    """IOp(10/93=2): nur ausgewählte Orbitale (z. B. π) tragen bei."""
    return bool(re.search(r"10/93=2", " ".join(c.get("keywords") or []).lower()))


def _raster(V, A, W, H, chunk=3_000_000):
    """Dreiecke V [N,3,3] (x, y in Pixeln, z = Tiefe, größer = näher) mit Ecken-Attributen A [N,3,C] -> Tiefe [H,W]
    (−inf = leer) und Attribute [H,W,C] des vordersten Dreiecks (baryzentrisch interpoliert). Zwei Durchgänge
    (Tiefe, dann Gewinner), Dreiecke nach Größe gebündelt, alles in numpy."""
    C = A.shape[2]
    zb = np.full(H * W, -np.inf, np.float32)
    out = np.zeros((H * W, C), np.float32)
    if not len(V):
        return zb.reshape(H, W), out.reshape(H, W, C)
    x, y, z = V[..., 0], V[..., 1], V[..., 2]
    x0, x1 = np.floor(x.min(1)).astype(int), np.floor(x.max(1)).astype(int)
    y0, y1 = np.floor(y.min(1)).astype(int), np.floor(y.max(1)).astype(int)
    area = (x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) - (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0])
    keep = (x1 >= 0) & (x0 < W) & (y1 >= 0) & (y0 < H) & (np.abs(area) > 1e-9)
    x0, y0 = np.maximum(x0, 0), np.maximum(y0, 0)
    span = np.maximum(np.minimum(x1, W - 1) - x0, np.minimum(y1, H - 1) - y0) + 1
    groups, k = [], 1
    while keep.any():
        sel = keep & (span <= k)
        if sel.any():
            groups.append((k, np.nonzero(sel)[0]))
        keep &= ~sel
        k *= 2

    def pieces():
        for k, idx in groups:
            o = np.arange(k * k)
            ox, oy = o % k, o // k
            n = max(1, chunk // (k * k))
            for i in range(0, len(idx), n):
                t = idx[i:i + n]
                PX = x0[t, None] + ox + 0.5
                PY = y0[t, None] + oy + 0.5
                xa, ya, xb, yb, xc, yc = (v[t, None] for v in (x[:, 0], y[:, 0], x[:, 1], y[:, 1], x[:, 2], y[:, 2]))
                ar = area[t, None]
                la = ((xb - PX) * (yc - PY) - (xc - PX) * (yb - PY)) / ar
                lb = ((xc - PX) * (ya - PY) - (xa - PX) * (yc - PY)) / ar
                lc = 1.0 - la - lb
                ok = (la >= -1e-6) & (lb >= -1e-6) & (lc >= -1e-6) & (PX < W) & (PY < H)
                r, c = np.nonzero(ok)
                tt = t[r]
                L = np.stack([la[r, c], lb[r, c], lc[r, c]], 1)
                pix = (PY[r, c].astype(np.int64)) * W + PX[r, c].astype(np.int64)
                yield tt, L, pix, (L * z[tt]).sum(1).astype(np.float32)

    for _, _, pix, d in pieces():
        np.maximum.at(zb, pix, d)
    for tt, L, pix, d in pieces():
        win = d >= zb[pix]
        out[pix[win]] = np.einsum("nk,nkc->nc", L[win], A[tt[win]])
    return zb.reshape(H, W), out.reshape(H, W, C)


def _arrow_tris(S, r_shaft, r_head, cs, ch):
    """Pfeile im Bildraum (S [M,3,3]: Anfang, Zylinderende, Spitze in Pixeln + Tiefe) -> Dreiecke [3M,3,3] und Farben:
    Schaft als Band (zwei Dreiecke), Kopf als Dreieck, zur Kamera gedreht wie bei orthographischer Ansicht."""
    d = S[:, 2, :2] - S[:, 0, :2]
    n = np.linalg.norm(d, axis=1)
    ok = n > 1e-6
    S, d, n, r_shaft, r_head = S[ok], d[ok], n[ok], r_shaft[ok], r_head[ok]
    q = np.stack([-d[:, 1], d[:, 0], np.zeros(len(d))], 1) / n[:, None]
    a, b, c = S[:, 0], S[:, 1], S[:, 2]
    rs, rh = q * r_shaft[:, None], q * r_head[:, None]
    tris = np.concatenate([np.stack([a - rs, a + rs, b + rs], 1), np.stack([a - rs, b + rs, b - rs], 1),
                           np.stack([b - rh, b + rh, c], 1)])
    m = len(S)
    cols = np.concatenate([np.repeat([cs], 2 * m, 0), np.repeat([ch], m, 0)]).reshape(-1, 1, 3).repeat(3, 1)
    return tris, cols


def mesh_render(mesh, R, center, xl, yl, W, H, occ, color, alpha, arrows=None, field=None):
    """Isofläche (Dreiecksnetz mit Normalen) + Pfeile als RGBA-Bild (H×W×4, Zeile 0 unten, gerade Deckkraft) in der
    Ansicht R; occ = Tiefe des vordersten Atoms je Pixel (nur Davorliegendes zählt). arrows: (S [M,3,3] Welt,
    r_shaft, r_head, Farbe Schaft, Farbe Kopf); field: (Richtung, Farbe) – Symbol unten links im Bild."""
    px, py = (xl[1] - xl[0]) / W, (yl[1] - yl[0]) / H
    R = np.asarray(R, float)

    def screen(P):
        S = (np.asarray(P, float) - center) @ R.T
        return np.stack([(S[..., 0] - xl[0]) / px, (S[..., 1] - yl[0]) / py, S[..., 2]], -1)

    V = screen(mesh["tri"])
    N = np.asarray(mesh["nrm"], float) @ R.T
    A = np.concatenate([N, np.ones(N.shape[:2] + (1,)), np.zeros(N.shape[:2] + (3,))], -1)   # Normale, Fläche, Farbe
    if arrows is not None and len(arrows[0]):
        S = screen(arrows[0])
        S[..., 2] += 0.03                                 # liegen auf der Fläche: knapp davor (kein Flimmern)
        rs = np.maximum(arrows[1] / px, MIN_ARROW_PX)
        rh = np.maximum(arrows[2] / px, 2 * MIN_ARROW_PX)
        T_, Cc = _arrow_tris(S, rs, rh, arrows[3], arrows[4])
        Aa = np.concatenate([np.zeros(T_.shape[:2] + (3,)), np.zeros(T_.shape[:2] + (1,)), Cc], -1)
        V, A = np.concatenate([V, T_]), np.concatenate([A, Aa])
    zb, at = _raster(V.astype(np.float64), A.astype(np.float32), W, H)
    img = np.zeros((H, W, 4), np.float32)
    hit = np.isfinite(zb) & (zb > occ)
    surf = hit & (at[..., 3] > 0.5)
    n = at[surf, :3]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    n *= np.where(n[:, 2:3] < 0, -1.0, 1.0)              # beidseitig beleuchtet
    h = (LIGHT + [0, 0, 1]) / np.linalg.norm(LIGHT + [0, 0, 1])
    dif = np.clip(n @ LIGHT, 0, 1)[:, None]
    spec = (np.clip(n @ h, 0, 1) ** 40)[:, None]
    img[surf, :3] = np.clip(np.asarray(color[:3]) * (0.35 + 0.65 * dif) + 0.35 * spec, 0, 1)
    img[surf, 3] = alpha
    arr = hit & ~surf
    img[arr, :3] = at[arr, 4:7]
    img[arr, 3] = 1.0
    if field is not None:                                 # Richtung von B: Pfeil (projiziert) oder ⊙/⊗ unten links
        b = R @ np.asarray(field[0], float)
        r = 0.055 * H
        cx, cy = 0.03 * W + r, 0.04 * H + r
        if np.hypot(b[0], b[1]) > 0.25:
            u = b[:2]                                     # Länge = Projektion (schräg zum Betrachter kürzer)
            p0 = np.array([cx, cy, 1e9]) - np.r_[u * r, 0]
            p2 = np.array([cx, cy, 1e9]) + np.r_[u * r, 0]
            p1 = p0 + (p2 - p0) * 0.62
            tris, cols = _arrow_tris(np.array([[p0, p1, p2]]), np.array([0.07 * r]), np.array([0.2 * r]),
                                     field[1], field[1])
        else:                                             # zum Betrachter (Punkt) oder von ihm weg (Kreuz) im Kreis
            ang = np.linspace(0, 2 * np.pi, 33)
            ring = [(np.cos(a_) * r * f_, np.sin(a_) * r * f_) for a_ in ang for f_ in (1.0, 0.86)]
            tris = []
            for i in range(32):
                (ax_, ay_), (bx_, by_) = ring[2 * i], ring[2 * i + 1]
                (cx_, cy_), (dx_, dy_) = ring[2 * i + 2], ring[2 * i + 3]
                tris += [[(ax_, ay_), (bx_, by_), (cx_, cy_)], [(bx_, by_), (dx_, dy_), (cx_, cy_)]]
            if b[2] > 0:
                tris += [[(np.cos(a_) * .2 * r, np.sin(a_) * .2 * r), (np.cos(a2) * .2 * r, np.sin(a2) * .2 * r), (0, 0)]
                         for a_, a2 in zip(ang[:-1], ang[1:])]
            else:
                w_, e_ = 0.07 * r, 0.6 * r
                for s_ in (1, -1):
                    tris += [[(-e_, -e_ * s_ + w_), (-e_ + w_, -e_ * s_), (e_, e_ * s_ - w_)],
                             [(-e_ + w_, -e_ * s_), (e_, e_ * s_ - w_), (e_ - w_, e_ * s_)]]
            tris = np.array([[(cx + p_[0], cy + p_[1], 1e9) for p_ in t_] for t_ in tris], float)
            cols = np.repeat([field[1]], len(tris) * 3, 0).reshape(-1, 3, 3)
        zg, ag = _raster(tris, np.asarray(cols, np.float32), W, H)
        g = np.isfinite(zg)
        img[g, :3] = ag[g]
        img[g, 3] = 1.0
    return img


class MeshImage:
    """Bild der AICD-Fläche über den Atomen einer XrayFigure (wie `OrbitalImage`: gerechnet beim Zeichnen in
    Zielauflösung, beim Drehen gröber, 2×2-Unterabtastung für glatte Kanten)."""

    @staticmethod
    def attach(F, spec):
        from elucida.core import orbitals as ORB

        class _Img(ORB.OrbitalImage):
            def make_image(self, renderer, magnification=1.0, unsampled=False):
                ax = self.axes
                bb = ax.bbox
                w_in = ax.get_position().width * ax.figure.get_figwidth()
                dpi = bb.width * magnification / max(w_in, 1e-9)
                f = min(1.0, ORB.ORB_MAX_DPI / max(dpi, 1e-9))
                if self.drag:
                    f /= max(ORB.DRAG_SCALE, np.sqrt(bb.width * bb.height * (magnification * f) ** 2 / ORB.DRAG_PX))
                W = max(2, int(round(bb.width * magnification * f)))
                H = max(2, int(round(bb.height * magnification * f)))
                xl, yl = tuple(ax.get_xlim()), tuple(ax.get_ylim())
                key = (W, H, self.F.R.tobytes(), xl, yl)
                self.set_interpolation(ORB.DRAG_INTERP if self.drag else "bilinear")
                if key != self._key:
                    self._key = key
                    s = 1 if self.drag or W * H > 4_000_000 else 2
                    occ, zoff = self.F.occluder(xl, yl, s * W, s * H)
                    o = self.orb
                    img = mesh_render(o["mesh"], self.F.R, self.F.center, xl, yl, s * W, s * H, occ - zoff,
                                      o["color"], o["alpha"], o["arrows"], o["field"])
                    if s == 2:                            # gerade Deckkraft: Farbe gewichtet mitteln
                        a = img[..., 3:4]
                        pre = np.concatenate([img[..., :3] * a, a], -1).reshape(H, 2, W, 2, 4).mean((1, 3))
                        img = np.zeros_like(pre)
                        ok = pre[..., 3] > 0
                        img[ok, :3] = pre[ok, :3] / pre[ok, 3:4]
                        img[ok, 3] = pre[ok, 3]
                    self.set_data(img)
                    self.set_extent((xl[0], xl[1], yl[0], yl[1]))
                return super(ORB.OrbitalImage, self).make_image(renderer, magnification, unsampled)

        art = _Img(F.ax, F, spec)
        art.set_zorder(45)
        F.ax.add_image(art)
        F.orb, F.orb_art = spec, art                       # Drehen (gröber beim Ziehen) und Reihenfolge wie Orbitale
        F.order.append(art)
        return art


class _AcidMouse:
    """Empfänger für `XrayMouse` der ACID-Abbildung: nur die Ansicht."""

    def __init__(self, page):
        self.p = page

    def hover_atom(self, k):
        pass

    atom_clicked = atom_double_clicked = atoms_boxed = labels_moved = hover_atom

    def _store(self, **kw):
        self.p.acid.update(kw)
        self.p.sync()
        self.p.changed()

    def view_changed(self, R):
        self._store(view=[round(float(v), 6) for v in np.asarray(R).ravel()])

    def pan_changed(self, pan):
        self._store(pan=[round(float(pan[0]), 4), round(float(pan[1]), 4)])

    def zoom_changed(self, z):
        self.p.acid["zoom"] = round(float(z), 4)


class AcidPage:
    """Karten und Reiter „ACID“ eines DFT-Tabs."""

    def __init__(self, tab):
        self.tab = tab
        self._loading = False
        self.mouse = None
        self._cards()
        self.group = self._page()
        self._pending = False
        TABS.ShowHook(self.group, lambda: self._pending and self._draw())

    @property
    def acid(self):
        p = self.tab.st.setdefault("acid", {})
        for k, v in ACID_DEFAULT.items():
            p.setdefault(k, list(v) if isinstance(v, list) else v)
        return p

    def changed(self):
        if self._loading:
            return
        self.sync()
        self.tab.main.push_undo()

    # -- Oberfläche --------------------------------------------------------------------------------------
    def _cards(self):
        from elucida.app import style as STYLE
        g = QGroupBox(T("acid_card"))
        f = STYLE.make_form(g)
        row = QHBoxLayout()
        b = STYLE.list_button(T("dft_nics_add_short"))
        b.setToolTip(T("acid_add"))
        b.clicked.connect(self.add)
        self.btn_rm = STYLE.list_button(T("remove"))
        self.btn_rm.clicked.connect(self.remove)
        row.addWidget(b)
        row.addWidget(self.btn_rm)
        f.addRow(row)
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels([T("dft_nics_file"), T("dft_nics_kind")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(STYLE.CHECK_ROW_H)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        STYLE.empty_note(self.tbl, T("acid_start"))
        f.addRow(self.tbl)
        self.ed_geom = QLineEdit()
        self.ed_geom.setPlaceholderText(T("dft_nics_geom_ph"))
        self.ed_geom.setToolTip(T("acid_geom_tip"))
        self.ed_geom.editingFinished.connect(self.geom_changed)
        f.addRow(T("dft_nics_geom"), self.ed_geom)
        self.card = g

        g = QGroupBox(T("acid_display"))
        f = STYLE.make_form(g)
        self.sp_iso = QDoubleSpinBox()
        self.sp_iso.setRange(0.0001, 10.0)
        self.sp_iso.setDecimals(4)
        self.sp_iso.setSingleStep(0.005)
        self.sp_iso.setToolTip(T("acid_iso_tip"))
        self.sp_iso.valueChanged.connect(self.display_changed)
        f.addRow(T("acid_iso"), self.sp_iso)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_color = TABS.color_button(self.acid["color"], lambda c: self.color_changed(c, "color"))
        row.addWidget(self.btn_color)
        row.addStretch(1)
        f.addRow(T("acid_color"), row)
        self.sp_alpha = QDoubleSpinBox()
        self.sp_alpha.setRange(0.05, 1.0)
        self.sp_alpha.setSingleStep(0.05)
        self.sp_alpha.valueChanged.connect(self.display_changed)
        f.addRow(T("dft_nics3d_alpha"), self.sp_alpha)
        from elucida.tabs import xray as XRAY
        f.addRow(T("view_row"), XRAY.view_reset_button(lambda: self.acid, self.changed))
        self.lbl_iso_file = STYLE.HintLabel("")                # AICD: Isowert steht in der Datei
        self.lbl_iso_file.setWordWrap(True)
        f.addRow(self.lbl_iso_file)
        self._display_form = f
        self.display = g

        g = QGroupBox(T("acid_arrows_card"))                  # nur mit AICD-Dateien (Pfeile, Magnetfeld)
        f = STYLE.make_form(g)
        row = QHBoxLayout()                                   # Pfeile: an/aus + Größe (ein Feld mit „aus“)
        self.cb_arrows = QCheckBox(T("acid_arrows"))
        self.cb_arrows.toggled.connect(self.display_changed)
        self.sp_arrow = QDoubleSpinBox()
        self.sp_arrow.setRange(0.2, 5.0)
        self.sp_arrow.setSingleStep(0.1)
        self.sp_arrow.setSuffix(" ×")
        self.sp_arrow.setToolTip(T("acid_arrow_size_tip"))
        self.sp_arrow.valueChanged.connect(self.display_changed)
        row.addWidget(self.cb_arrows)
        row.addWidget(self.sp_arrow)
        f.addRow(row)                                         # Beschriftung = Text des Kästchens („Pfeile“)
        self.sp_density = QDoubleSpinBox()
        self.sp_density.setRange(5.0, 100.0)
        self.sp_density.setDecimals(0)
        self.sp_density.setSingleStep(5.0)
        self.sp_density.setSuffix(" %")
        self.sp_density.setToolTip(T("acid_density_tip"))
        self.sp_density.valueChanged.connect(self.display_changed)
        f.addRow(T("acid_density"), self.sp_density)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_shaft = TABS.color_button(self.acid["color_shaft"], lambda c: self.color_changed(c, "color_shaft"))
        self.btn_head = TABS.color_button(self.acid["color_head"], lambda c: self.color_changed(c, "color_head"))
        self.btn_field = TABS.color_button(self.acid["color_field"], lambda c: self.color_changed(c, "color_field"))
        for b_, tip in ((self.btn_shaft, "acid_shaft_tip"), (self.btn_head, "acid_head_tip"),
                        (self.btn_field, "acid_field_tip")):
            b_.setToolTip(T(tip))
            row.addWidget(b_)
        row.addStretch(1)
        f.addRow(T("acid_arrow_colors"), row)
        self.cb_field = QCheckBox(T("acid_field"))
        self.cb_field.setToolTip(T("acid_field_tip"))
        self.cb_field.toggled.connect(self.display_changed)
        f.addRow(self.cb_field)
        self.arrow_card = g
        self.enabled = True                               # im Reaktionspfad aus: ACID gehört zur einzelnen Verbindung

    def _page(self):
        """Seite „ACID“: nur die Abbildung (füllt die Seite) und Hinweise; ohne Cube ein Platzhalter."""
        from PySide6.QtWidgets import QStackedWidget
        from elucida.app import style as STYLE
        g = QGroupBox(T("acid"))
        v = QVBoxLayout(g)
        self.lbl_none = STYLE.SciLabel("", T("acid_start"))
        self.lbl_none.setWordWrap(True)
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        self.fig = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.host = TABS.CanvasHost(self.canvas, self.fig, margin=0)
        self.host.setMinimumHeight(280)
        cv.addWidget(self.host, 1)
        self.lbl_notes = QLabel("")
        self.lbl_notes.setWordWrap(True)
        self.lbl_notes.setStyleSheet(HINT_CSS)
        cv.addWidget(self.lbl_notes)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.lbl_none)
        self.stack.addWidget(content)
        v.addWidget(self.stack, 1)
        return g

    # -- Daten ---------------------------------------------------------------------------------------------
    def cube(self):
        p = self.acid["cube"]
        return self.tab.cache(("acid_cube", p), lambda: read_acid_cube(p)) if p else None

    def calc(self):
        p = self.acid["log"]
        return self.tab.cache(("acid_log", p), lambda: read_acid_log(read_text(p))) if p else None

    def mesh(self):
        p = self.acid["inc"]
        return self.tab.cache(("acid_inc", p), lambda: AICD.read_isoober(read_text(p))) if p else None

    def molecule(self):
        p = self.acid["mol"]
        return self.tab.cache(("acid_mol", p), lambda: AICD.read_molekuel(read_text(p))) if p else None

    def data(self):
        """-> (Fläche oder None, Rechnung oder None, Hinweise). Fläche: dict(kind "mesh" (AICD) | "cube", els, xyz, …);
        die AICD-Dateien gehen dem Cube vor."""
        notes, got = [], {}
        for key, fn in (("inc", self.mesh), ("mol", self.molecule), ("cube", self.cube), ("log", self.calc)):
            try:
                got[key] = fn()
            except Exception as ex:
                notes.append(f"{Path(self.acid[key]).name}: {ex}")
                got[key] = None
        src, calc = None, got["log"]
        if got["inc"] is not None:
            if got["mol"] is None:
                notes.append(T("acid_no_mol"))
            else:
                src = dict(kind="mesh", mesh=got["inc"], **got["mol"])
            if self.acid["cube"]:
                notes.append(T("acid_cube_unused"))
        elif got["cube"] is not None:
            src = dict(kind="cube", cube=got["cube"], els=got["cube"]["els"], xyz=got["cube"]["xyz"])
        if src is not None and calc is None and not self.acid["log"]:
            notes.append(T("acid_no_log"))
        if src is not None and calc is not None:
            n = len(calc.get("geometry") or [])
            if n and n != len(src["els"]):
                notes.append(T("acid_atoms_differ", n=len(src["els"]), m=n))
        if src is not None and src["kind"] == "mesh" and src["mesh"]["iso"] is None:
            notes.append(T("acid_iso_unknown"))
        return src, calc, notes

    def shown_arrows(self, mesh):
        """Indizes der gezeigten Pfeile: fester Zufall (immer dieselben), Anteil = Dichte; nie neu berechnet."""
        m = len(mesh["arrows"])
        k = int(np.ceil(m * float(self.acid["arrow_density"]) / 100.0))
        return np.sort(np.random.default_rng(0).permutation(m)[:k])

    def level(self, calc):
        from elucida.tabs import dft_pages as PAGES
        lev, geom = PAGES.level_of_theory(calc) if calc else "", self.acid["geom"].strip()
        return f"{lev}//{geom}" if lev and geom else lev

    # -- Abbildung -----------------------------------------------------------------------------------------
    def build(self, fig, interactive=True):
        """Kugel-Stab-Modell („depth“ wie 3D-NICS) mit der Isofläche ACID = iso über das Orbital-Rendering
        (Feld/Isowert, Fläche bei +1; ACID ist nie negativ, die zweite Fläche entfällt)."""
        from matplotlib.colors import to_rgb
        from elucida.core import orbitals as ORB
        from elucida.tabs import dft as DFT
        from elucida.tabs import xray as XRAY
        src, _, notes = self.data()
        if src is None:
            return None, notes
        st, t = self.acid, self.tab
        els, xyz, n = src["els"], src["xyz"], len(src["els"])
        key = st["inc"] or st["cube"]
        mol = DFT.XyzMolecule(els, xyz, t.cache(("acid_bonds", key), lambda: DFT.bonds_of(els, xyz)), [""] * n)
        cfg = t.base_cfg()
        TABS.core.setup_fonts(TABS.plt, cfg)
        a, c = min(1.0, float(st["alpha"])), to_rgb(st["color"])
        if src["kind"] == "cube":
            iso = float(st["iso"])
            cube = src["cube"]
            vol = t.cache(("acid_vol", st["cube"], iso), lambda: ORB.Volume(
                (cube["data"][0] / iso).astype(np.float32), cube["origin"], cube["axes"]))
            orb = dict(vol=vol, iso=1.0, plus=c, minus=c, alpha=(a, a))
        else:
            orb = None
        o = dict(prob=50, show_h=True, labels=False, h_labels=False, colors={}, bond_w=0.08, hidden_frags=[],
                 style="depth", hidden_atoms=[], label_on={}, wire=set(), wire_h=False, label_mode="all", hide_kinds=[],
                 label_size=0.0, label_color="black", label_colors={}, cartoon_color=False, h_radius=0.55 * 0.25,
                 bg="white", ball_scale=1.0, rod_scale=1.0, elem_labels=False,
                 orbital=orb)
        R = (np.array(st["view"], float).reshape(3, 3) if st["view"] and len(st["view"]) == 9
             else XRAY.default_view(mol, use=list(range(n))))
        F = XRAY.XrayFigure(cfg, mol, R, o, {}, fig, zoom=st["zoom"], pan=st["pan"])
        if src["kind"] == "mesh":
            m = src["mesh"]
            arrows = None
            if st["arrows"] and len(m["arrows"]):
                ix = self.shown_arrows(m)
                A = m["arrows"][ix]
                s_ = float(st["arrow_scale"])
                A = A[:, :1] + (A - A[:, :1]) * s_            # um den Anfang skaliert (Lage bleibt auf der Fläche)
                arrows = (A, m["r_shaft"][ix] * s_, m["r_head"][ix] * s_, to_rgb(st["color_shaft"]),
                          to_rgb(st["color_head"]))
            field = (m["field"], to_rgb(st["color_field"])) if st["field"] and m["field"] is not None else None
            MeshImage.attach(F, dict(mesh=m, color=c, alpha=a, arrows=arrows, field=field))
            if field is not None:                         # Beschriftung neben dem Symbol unten links
                bb = F.ax.bbox
                F.ax.text(0.03 + 2.25 * 0.055 * bb.height / max(bb.width, 1), 0.04 + 0.055, "B", style="italic",
                          transform=F.ax.transAxes, ha="left", va="center", color=st["color_field"], zorder=46,
                          fontsize=max(8.0, cfg.get("font_size", 10)))
        return F, notes

    def caption(self, name):
        src, calc, _ = self.data()
        if src is None:
            return ""
        st = self.acid
        lev = self.level(calc)
        sel = ", considering only the selected orbitals" if calc and orbital_selection(calc) else ""
        iso = float(st["iso"]) if src["kind"] == "cube" else src["mesh"]["iso"]
        out = (f"ACID plot of <b>{html.escape(name)}</b>{sel}" + (f" (isovalue: {iso:g})" if iso is not None else "")
               + (f", based on a CSGT calculation at the {html.escape(lev)} level of theory" if lev else ""))
        if src["kind"] == "mesh":
            m = src["mesh"]
            if st["arrows"] and len(m["arrows"]):
                out += "; current density vectors are plotted onto the isosurface"
            if st["field"] and m["field"] is not None:
                out += (f"; the {TABS.color_name(st['color_field'])} arrow indicates the direction of the magnetic "
                        "field")
        return out + f". ACID method: {CITATION}."

    # -- Bedienung -----------------------------------------------------------------------------------------
    def add(self):
        t = self.tab
        if not t.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(t, T("acid_add"), t.main.settings.value("last_dir", ""),
                                             f"{T('acid_filter')} (*.inc *.cube *.cub *.log *.out);;{T('flt_all')}")
        self.load(ps)

    def load(self, ps):
        """Cube (ACID-Feld) oder Gaussian-Ausgabe (CSGT); eine neue Datei ersetzt die vorhandene derselben Art."""
        t = self.tab
        ps = list(ps)
        for p in list(ps):                                  # Isoober.inc: Molekuel.inc aus demselben Ordner dazu
            sib = Path(p).with_name("Molekuel.inc")
            if Path(p).name.lower() == "isoober.inc" and sib.exists() and str(sib) not in ps:
                ps.append(str(sib))
        for p in ps:
            try:
                ext = Path(p).suffix.lower()
                if ext in (".cube", ".cub"):
                    key = "cube"
                    read_acid_cube(p)
                elif ext == ".inc":
                    txt = read_text(p)
                    key = "inc" if "#declare Isooberflaeche" in txt else "mol"
                    AICD.read_isoober(txt) if key == "inc" else AICD.read_molekuel(txt)
                else:
                    key = "log"
                    read_acid_log(read_text(p))
            except Exception as ex:
                t.main.error(f"{Path(p).name}: {ex}")
                continue
            # AICD nennt beide Dateien immer gleich: im Projekt nach dem Ordner der Rechnung benennen
            dst = PRJ.data_sub(t.STATE_KEY)
            if key in ("inc", "mol"):
                dst = f"{dst}/{Path(p).parent.name or 'AICD'}"
            self.acid[key] = t.main.import_file(p, dst)
            if key in ("cube", "inc"):
                self.acid.update(view=None, zoom=1.0, pan=[0.0, 0.0])
        self.changed()

    def remove(self):
        i = self.tbl.currentRow()
        keys = [k for k in KINDS if self.acid[k]]
        if 0 <= i < len(keys):
            self.acid[keys[i]] = ""
            self.changed()

    def geom_changed(self):
        if self.acid["geom"] != self.ed_geom.text().strip():
            self.acid["geom"] = self.ed_geom.text().strip()
            self.changed()

    def display_changed(self, *_):
        if self._loading:
            return
        self.acid.update(iso=self.sp_iso.value(), alpha=self.sp_alpha.value(), arrows=self.cb_arrows.isChecked(),
                         arrow_scale=self.sp_arrow.value(), arrow_density=self.sp_density.value(),
                         field=self.cb_field.isChecked())
        self.changed()

    def color_changed(self, c, key):
        self.acid[key] = c
        self.changed()

    def sync(self):
        from elucida.app import style as STYLE
        self._loading = True
        st = self.acid
        rows = [(Path(st[k]).name, T(kind)) for k, kind in KINDS.items() if st[k]]
        r0 = self.tbl.currentRow()
        self.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, txt in enumerate(r):
                self.tbl.setItem(i, j, QTableWidgetItem(txt))
                self.tbl.item(i, j).setToolTip(r[0])
        if 0 <= r0 < self.tbl.rowCount():
            self.tbl.selectRow(r0)
        self.tbl.setFixedHeight(self.tbl.horizontalHeader().sizeHint().height()
                                + max(2, len(rows)) * STYLE.CHECK_ROW_H + 2)
        STYLE.fit_columns(self.tbl)
        self.ed_geom.setText(st["geom"])
        self.sp_iso.setValue(float(st["iso"]))
        self.sp_alpha.setValue(float(st["alpha"]))
        self.cb_arrows.setChecked(bool(st["arrows"]))
        self.sp_arrow.setValue(float(st["arrow_scale"]))
        self.sp_density.setValue(float(st["arrow_density"]))
        self.cb_field.setChecked(bool(st["field"]))
        for b, key in ((self.btn_color, "color"), (self.btn_shaft, "color_shaft"), (self.btn_head, "color_head"),
                       (self.btn_field, "color_field")):      # Farbfelder nach Rückgängig/Öffnen nachziehen
            b.setProperty("color", st[key])
            b.setStyleSheet(STYLE.swatch_css(st[key], b.property('cellcss') or ''))
        self._loading = False
        if self.mouse:
            self.mouse.disconnect()
            self.mouse = None
        self.card.setVisible(self.enabled)
        src = None
        try:
            src = self.data()[0]
        except Exception:
            pass
        mesh = src is not None and src["kind"] == "mesh"
        has_arrows = mesh and len(src["mesh"]["arrows"]) > 0
        f = self._display_form
        f.setRowVisible(self.sp_iso, not mesh)              # AICD: Isowert liegt in der Fläche fest
        self.lbl_iso_file.setText(T("acid_iso_file", v=f"{src['mesh']['iso']:g}") if mesh and src["mesh"]["iso"]
                                  is not None else "")
        has_field = mesh and src["mesh"]["field"] is not None
        self.btn_field.setVisible(has_field)
        self.cb_field.setVisible(has_field)
        self.display.setVisible(self.enabled and src is not None)
        self.arrow_card.setVisible(self.enabled and (has_arrows or has_field))
        self.btn_rm.setEnabled(bool(rows))
        self.stack.setCurrentIndex(1 if any(st[k] for k in KINDS) else 0)
        self._pending = not self.group.isVisible()        # Bild (Netz rastern, Pfeile) erst beim Anzeigen der Seite
        if not self._pending:
            self._draw()

    def _draw(self):
        self._pending = False
        if self.mouse:
            self.mouse.disconnect()
            self.mouse = None
        try:
            F, notes = self.build(self.fig)
            if F is not None:
                from elucida.tabs import xray as XRAY
                self.mouse = XRAY.XrayMouse(F, _AcidMouse(self))
        except Exception as ex:
            F, notes = None, [str(ex)]
        if F is None:
            self.fig.clear()
            self.fig.text(0.5, 0.5, T("acid_empty"), ha="center", va="center", color="gray")
        self.lbl_notes.setText("\n".join("⚠ " + n for n in notes))
        self.host.set_figure_size(*self.fig.get_size_inches())

    # -- Export / SI ---------------------------------------------------------------------------------------
    def figures(self):
        """[(Kürzel, Bauer, Unterschrift)] wie `DftPages.figures`."""
        return [("ACID", lambda fig: self.build(fig, False)[0], self.caption)] if self.data()[0] is not None else []


KINDS = {"inc": "acid_kind_inc", "mol": "acid_kind_mol", "cube": "acid_kind_cube", "log": "acid_kind_log"}
