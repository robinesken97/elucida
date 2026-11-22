"""
elucida/tabs/nmr_view.py - Interaktive 1D-NMR-Ansicht, Bedienung wie Mnova (Tasten Z, F, H, P, I, K, J, R/L, C, X, E,
Shift+P, Esc; jeder Modus auch als Knopf mit seiner Taste). Das Widget rechnet nichts: Integrale, Peaks, Multipletts,
Lösungsmittelmarken und Phase kommen als Daten herein, Auswahl und Bearbeitung gehen als Signale hinaus.

Daten: x in ppm (absteigend), y reell; Bereiche als Listen von dicts mit "lo"/"hi" (ppm, lo < hi; weitere Schlüssel
bleiben erhalten), Integrale zusätzlich "value" (angezeigt, nie gerechnet), Peaks {"x"}, Multipletts {"lo", "hi",
"delta", "cls", "nH"}, Lösungsmittel {"x", "name"}.
"""
from __future__ import annotations

import math
import re

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure as MplFigure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import IdentityTransform
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QPushButton,
                               QVBoxLayout, QWidget)

from elucida.app import canvas_theme as CANVAS
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register as register_canvas
from elucida.app.i18n import T
from elucida.core import uvvis as core
from elucida.tabs import base as TABS


# Modus -> (Taste auf dem Knopf, Symbol). Esc/Z/P/I/K/J/R/C/X/E/Shift+P aus der Mnova-Recherche (SPEZ mnova-ui)
MODES = {"pointer": ("Esc", "nmrv_pointer"), "zoom": ("Z", "nmrv_zoom_h"), "pan": ("P", "nmrv_pan_free"),
         "integral": ("I", "nmrv_integral"), "peaks": ("K", "nmrv_peaks"), "multiplet": ("J", "nmrv_multiplet"),
         "reference": ("R", "nmrv_reference"), "cursor": ("C", "nmrv_cursor"), "cut": ("X", "nmrv_cut"),
         "inset": ("E", "nmrv_inset"), "phase": ("⇧P", "nmrv_phase"), "mark": ("T", "nmrv_mark")}
# Sofortaktionen -> (Taste, Symbol). „<“/„>“ für vorige/nächste Zoomstufe sind eigene Wahl (Mnova: nur Toolbar)
ACTIONS = {"zoom_out": ("⇧Z", "nmrv_zoom_out"), "full": ("F", "nmrv_full"), "highest": ("H", "nmrv_highest"),
           "prev": ("<", "nmrv_prev"), "next": (">", "nmrv_next")}
ZOOM_KINDS = ("h", "v", "box")            # Z mehrfach: waagerecht -> senkrecht -> Rechteck (Mnova)
PAN_KINDS = ("free", "h", "v")            # P mehrfach: frei -> waagerecht -> senkrecht (Mnova)
RANGE_LAYER = {"integral": "integrals", "cut": "cuts", "inset": "insets", "multiplet": "multiplets"}
MARK_SYMBOLS = ("*", "†", "‡", "§")       # Marken für Verunreinigungen (Bedeutung schreibt der Tab in die Unterschrift)
SHOW_KEYS = ("int_curves", "int_values", "peak_labels", "y_axis", "grid", "title", "solvents")
# Vorgabe = Mnova-Vorgabe (aus den Vektoren von Mnova-PDF-Abbildungen gelesen; Achse 426.7 pt = 150.5 mm breit): Spektrum #800000, Peak-Labels und Integralwerte #000080, Integralklammer #008000, Lösungsmittel
# #808080, alle Striche 0.665 pt; Schrift Peak-Labels/Werte 4.0 pt, Achsenzahlen 5.13 pt (Mnova: MS Shell Dlg 2, hier
# die Programmschrift). Die Vorlage zeigt weder Integralkurven noch Multiplett-Labels noch Titel. Schlüssel sprechend
# benannt (wandern später in die gemeinsame Karte „Schrift, Linien und Farben“).
STYLE_DEFAULT = dict(spectrum_color="#800000", spectrum_width=0.665, peak_label_color="#000080", peak_label_size=4.0,
                     integral_bracket_color="#008000", integral_bracket_width=0.665, integral_value_color="#000080",
                     integral_value_size=4.0, solvent_label_color="#808080", solvent_label_size=4.0,
                     axis_color="#000000", axis_font_size=5.13, mark_color="#000000", mark_size=6.5)
SHOW_DEFAULT = dict(int_curves=False, int_values=True, peak_labels=True, mult_labels=False, y_axis=False, grid=False,
                    title=False, solvents=True, mult_label="delta_full", mark_symbol="*", **STYLE_DEFAULT)
# Abstände der Vorlage in pt bei Abbildungsbreite NOMINAL_W_PT (Vorschau skaliert wie jede Abbildung mit der Breite):
# Leitlinie 1.26 senkrecht, 2.51 schräg, 1.26 senkrecht; Labels unten bündig (lange Texte reichen höher); Integralklammer
# 9.55 unter der Grundlinie, Enden 2.26 hoch, Strich zum Wert 1.13; Grundlinie 25.3 über der Achse; Teilstrich 2.26,
# Zwischenstrich 1.13 (halbe Teilung); Teilung so, dass Hauptstriche >= 14 pt auseinander liegen (Vorlagen: 0.5 ppm in
# 23.7 pt, Ausschnitte 0.1 ppm in 17.9 pt und 0.01 ppm in 16 pt, 13C 10 ppm in 21.3 pt; die nächstfeinere Teilung läge
# jeweils unter 12 pt); Ausschnitt: Klammer 2.8 über seiner Grundlinie
G = dict(lead=(1.26, 2.51, 1.26), int_off=9.55, int_end=2.26, val_lead=1.13, val_gap=0.86, base=25.3, tick=2.26,
         minor=1.13, tick_step=14.0, inset_int=2.8, stroke=0.665, arrow=2.26, pitch=1.225, join=3.2)
# Labels und Werte stehen im Abstand 1.225 × Schriftgröße (Vorlage: 4.89 pt bei 3.99 pt); Nachbarn mit weniger als
# 3.2 pt Luft rücken als Gruppe zusammen (Vorlage: 2.9 pt Luft verbunden, 3.5 pt getrennt)
# Integralwert wie die Vorlage: Leitlinie 3 × 1.13 pt (senkrecht, schräg zum Label, senkrecht), Zahl 0.86 pt darunter;
# reicht ein Integral über den sichtbaren Bereich (Ausschnitt), endet die Klammer dort mit einer Pfeilspitze
NOMINAL_W_PT = 16.0 / 2.54 * 72            # SI-Abbildung 16 cm breit (TABS.SI_MAX_W_CM), Achse ~426.7 pt wie die Vorlage
SIDE_PT = (NOMINAL_W_PT - 426.66) / 2
MULT_LABELS = ("delta", "cls", "delta_cls", "delta_full", "range", "range_full")     # Inhalt wie Mnova „Multiplet Label“

C_LINE, C_SEL, C_MARK = "#000000", "#2E6BD6", "#c77c0e"
STRUCT_FRAC = 0.3                           # automatische Ausschnitte meiden das linke Drittel (Struktur)
ML_SCREEN_PX = 12                         # Multiplett-Labels in der Ansicht: Schrift mindestens so hoch (Bildschirmpunkte)
CLICK_PX = 4                              # weniger Bewegung = Klick
EDGE_PX = 5                               # Rand eines Bereichs greifen
HIT_PX = 6                                # Peak/Schnitt treffen
WHEEL = 1.25                              # Mausrad und +/-: Intensität je Schritt
PH0_DEG_PX, PH1_DEG_PX, FINE = 0.5, 2.0, 0.1


def spread(centers, widths, lo, hi, join=0.0):
    """Kästen (Mitte, Breite) auf einer Linie ohne Überlappung: Reihenfolge bleibt, zusammenstoßende rücken als Gruppe
    um ihre gemeinsame Mitte auseinander und bleiben in [lo, hi], solange sie hineinpassen; join: Nachbarn mit weniger
    Luft dazwischen gehören ebenfalls zur Gruppe (Mnova). -> Mitten (gleiche Folge)."""
    n = len(centers)
    if not n:
        return []
    total = sum(widths)
    if total > hi - lo:                                    # passen nicht: gleichmäßig gestaucht (überlappen dann)
        widths = [w * (hi - lo) / total for w in widths]
    order = sorted(range(n), key=lambda i: centers[i])
    # Gruppen wie Mnova: Nachbarn, deren Kästen sich an der eigenen Lage berühren oder weniger als join Luft lassen;
    # jede Gruppe mittig zwischen ihrem ersten und letzten Mitglied (Mnova-Vorgabe: Integralwerte auf 0.01 pt genau)
    clusters = []
    for i in order:
        if clusters and centers[i] - widths[i] / 2 < centers[clusters[-1][-1]] + widths[clusters[-1][-1]] / 2 + join:
            clusters[-1].append(i)
        else:
            clusters.append([i])
    mid = lambda mem: (centers[mem[0]] + centers[mem[-1]]) / 2
    groups = []                                            # [Mitglieder, Breite, linke Kante]
    for mem in clusters:
        w = sum(widths[k] for k in mem)
        g = [mem, w, mid(mem) - w / 2]
        while groups and groups[-1][2] + groups[-1][1] > g[2]:      # Gruppen, die sich dann überlappen: eine Gruppe
            p = groups.pop()
            mem2, w2 = p[0] + g[0], p[1] + g[1]
            g = [mem2, w2, mid(mem2) - w2 / 2]
        groups.append(g)
    for g in groups:
        g[2] = min(max(g[2], lo), hi - g[1]) if g[1] <= hi - lo + 1e-9 else lo
    for a, b in zip(groups, groups[1:]):                   # nach dem Einpassen erneut ohne Überlappung
        b[2] = max(b[2], a[2] + a[1])
    for a, b in zip(groups[-2::-1], groups[::-1]):
        a[2] = max(lo, min(a[2], b[2] - a[1]))
    out = [0.0] * n
    for mem, _, left in groups:
        for k in mem:
            out[k] = left + widths[k] / 2
            left += widths[k]
    return out


def label_row(centers, groups, pitch, lo, hi):
    """Labelreihe wie Mnova: jede Gruppe (Multiplett) liegt mittig über ihren Peaks, Labels im Abstand pitch. Stößt eine
    Gruppe an ihre rechte Nachbarin, rückt sie nach links (von rechts nach links); am linken Rand (lo) rückt alles
    zurück nach rechts. Mnova lässt Nachbargruppen dabei um ein halbes Label überlappen – hier nie (ui.md: Beschriftungen
    berühren sich nicht); reicht der Platz nicht, wird der Abstand gestaucht, die Reihe bleibt in [lo, hi].
    centers: Peaklagen in px (aufsteigend je Gruppe), groups: Listen von Indizes. -> Mitten der Labels."""
    pitch = min(pitch, (hi - lo) / max(1, len(centers)))
    gs = sorted(groups, key=lambda g: (centers[g[0]] + centers[g[-1]]) / 2)
    w = [pitch * len(g) for g in gs]
    left = [(centers[g[0]] + centers[g[-1]]) / 2 - wi / 2 for g, wi in zip(gs, w)]
    if gs:
        left[-1] = min(left[-1], hi - w[-1])
    for i in range(len(gs) - 2, -1, -1):
        left[i] = min(left[i], left[i + 1] - w[i])
    if gs:
        left[0] = max(left[0], lo)
    for i in range(1, len(gs)):
        left[i] = max(left[i], left[i - 1] + w[i - 1])
    if gs and left[-1] + w[-1] > hi:                  # rechts übergelaufen: von rechts wieder nach links schieben
        left[-1] = hi - w[-1]
        for i in range(len(gs) - 2, -1, -1):
            left[i] = min(left[i], left[i + 1] - w[i])
    out = [0.0] * len(centers)
    for g, l0 in zip(gs, left):
        for k, i in enumerate(g):
            out[i] = l0 + pitch * (k + 0.5)
    return out


def merge_ranges(items):
    """Überlappende Bereiche zusammenfassen (Schnitte) -> neue Liste, aufsteigend."""
    out = []
    for r in sorted(({"lo": float(r["lo"]), "hi": float(r["hi"])} for r in items), key=lambda r: r["lo"]):
        if out and r["lo"] <= out[-1]["hi"]:
            out[-1]["hi"] = max(out[-1]["hi"], r["hi"])
        else:
            out.append(r)
    return out


def cut_functions(cuts, lo, hi, gap=None):
    """Skala ohne die ausgeblendeten Bereiche (Mnova „Cut“): jeder Schnitt schrumpft auf eine schmale Lücke (gap in
    ppm). -> (vor, zurück) für matplotlibs FunctionScale, streng monoton (auch weit außerhalb der Daten linear)."""
    span = max(hi - lo, 1e-9)
    gap, far = (0.004 * span if gap is None else gap), 1e3 * span
    xs, us, shift = [lo - far], [lo - far], 0.0
    for c in merge_ranges(cuts):
        a, b = max(c["lo"], lo), min(c["hi"], hi)
        if b <= a:
            continue
        xs += [a, b]
        us += [a - shift, a - shift + gap]
        shift += (b - a) - gap
    xs.append(hi + far)
    us.append(hi + far - shift)
    xs, us = np.array(xs), np.array(us)
    return (lambda v: np.interp(v, xs, us)), (lambda u: np.interp(u, us, xs))


def nucleus_axis_label(nucleus):
    """„δ ¹H (ppm)“, δ steil wie in Mnova (Nutzerwunsch, Ausnahme im NMR). Arial hat nur ¹²³ als hochgestellte Zeichen:
    andere Massenzahlen (¹⁹F, ³¹P, ¹⁵N …) als Mathtext-Exponent, sonst stünde ein leeres Kästchen da."""
    m = re.match(r"(\d+)([A-Z][a-z]?)$", nucleus or "")
    if not m:
        return "δ (ppm)"
    if set(m.group(1)) <= set("123"):
        return f"δ {m.group(1).translate(str.maketrans('123', '¹²³'))}{m.group(2)} (ppm)"
    return f"δ $^{{{m.group(1)}}}$" + f"{m.group(2)} (ppm)"


class _CutLocator(MaxNLocator):
    """Teilstriche wie in der Vorlage (Dichte über nbins), aber keine in einem Schnitt oder direkt an seinen Rändern
    (Beschriftungen stießen dort zusammen). minor: Zwischenstriche auf halber Teilung. char_px: Breite einer Ziffer –
    passen die Zahlen nicht zwischen ihre Striche (z. B. „7.525“ bei feiner Teilung), wird die Teilung gröber; Haupt- und
    Zwischenstriche rechnen gleich und bleiben deckungsgleich. sep_px: Mindestabstand zweier Zahlen über einen Bruch."""

    def __init__(self, cuts, near_px, nbins, minor=False, sep_px=0.0, char_px=0.0):
        super().__init__(nbins=max(2, math.ceil(nbins)), steps=[1, 2, 2.5, 5, 10])
        self.cuts, self.near, self.minor, self.base_nb = cuts, near_px, minor, max(2.0, nbins)
        self.sep, self.char = sep_px, char_px              # sep: Luft zwischen zwei Zahlen über einen Bruch

    def _w(self, txt):
        """Breite einer Zahl in px (Arial: Ziffer 0.556 em, Punkt 0.278, Minus 0.584; char = Ziffernbreite)."""
        return sum(0.278 if c == "." else 0.584 if c in "-−" else 0.556 for c in txt) * self.char / 0.556

    def _px(self):
        ax = self.axis.axes
        return lambda v: ax.transData.transform((v, 0))[0]

    def _fits(self, t):
        """Zahlen zwischen benachbarten Strichen ohne Bruch dazwischen nicht breiter als ihr Abstand."""
        st = abs(t[1] - t[0])
        dec = next((d for d in range(7) if abs(round(st, d) - st) <= 1e-9 * max(1.0, st)), 6)
        vmin, vmax = sorted(self.axis.get_view_interval())
        vis = [v for v in t if vmin <= v <= vmax and not any(c["lo"] < v < c["hi"] for c in self.cuts)]
        if len(vis) < 2:
            return True
        need = max(self._w(f"{v:.{dec}f}") for v in vis) + 0.5 * self.char   # halbe Ziffer Luft
        px = self._px()
        return all(abs(px(b) - px(a)) >= need for a, b in zip(vis, vis[1:])
                   if not any(min(a, b) < c["lo"] < max(a, b) for c in self.cuts))

    def __call__(self):
        nb = self.base_nb
        if self.cuts:                                      # Dichte nach der sichtbaren Breite, nicht über die Lücken
            vmin, vmax = sorted(self.axis.get_view_interval())
            cut = sum(max(0.0, min(c["hi"], vmax) - max(c["lo"], vmin)) for c in self.cuts)
            nb = self.base_nb * (vmax - vmin) / max(vmax - vmin - cut, 1e-9)
        for _ in range(12):
            self.set_params(nbins=max(2, math.ceil(nb)))
            t = list(super().__call__())
            if not self.char or len(t) < 2 or nb <= 2 or self._fits(t):
                break
            nb /= 1.25
        if self.minor and len(t) > 1:
            st = t[1] - t[0]
            t = [v + st / 2 for v in [t[0] - st] + t]
        if not self.cuts:
            return t
        px = self._px()
        gaps = [px((c["lo"] + c["hi"]) / 2) for c in self.cuts]
        t = [v for v in t if not any(c["lo"] < v < c["hi"] for c in self.cuts)
             and not any(abs(px(v) - g) < self.near for g in gaps)]
        if self.sep and len(t) > 1:                        # Zahlen links und rechts eines Bruchs liefen ineinander
            bb = self.axis.axes.bbox                       # („7.487.40“): die am Bruch auf der schmaleren Seite fällt weg
            st = abs(t[1] - t[0])
            dec = next((d for d in range(7) if abs(round(st, d) - st) <= 1e-9 * max(1.0, st)), 6)
            wid = lambda v: self._w(f"{v:.{dec}f}")              # noqa: E731
            edges = [bb.x0] + sorted(gaps) + [bb.x1]
            for k, g in enumerate(edges[1:-1], 1):
                left = [v for v in t if edges[k - 1] <= px(v) < g]
                right = [v for v in t if g < px(v) <= edges[k + 1]]
                if left and right:
                    a, b = max(left, key=px), min(right, key=px)
                    if px(b) - px(a) < (wid(a) + wid(b)) / 2 + self.sep:
                        t.remove(a if g - edges[k - 1] < edges[k + 1] - g else b)
        return t


class _Host(TABS.CanvasHost):
    """Zeichenfläche in der Karte der rechten Seite wie jede Abbildung: Nennbreite = SI-Abbildung (Schrift und Striche
    in pt dazu, die Vorschau skaliert über die dpi), Höhe füllt den Platz (Spektrum füllt die Seite)."""

    def fit(self):
        aw = max(100, self.width() - self.inset[0] - self.inset[2])
        ah = max(80, self.height() - self.inset[1] - self.inset[3])
        w_in = NOMINAL_W_PT / 72
        self.fig_in = (w_in, w_in * ah / aw)
        super().fit()


class _FlowBar(QWidget):
    """Gruppen der Modusleiste nebeneinander, Umbruch erst, wenn die Breite nicht reicht (960-px-Fenster); die
    Mindestbreite ist die der breitesten Gruppe."""

    def __init__(self, items):
        super().__init__()
        self.items = items
        for w in items:
            w.setParent(self)
        self.setMinimumWidth(max(w.sizeHint().width() for w in items))
        self.setFixedHeight(STYLE.BAR_H)

    def rows(self):
        return round((STYLE._flow(self.items, self.width(), False) + 6) / (STYLE.BAR_H + 6))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        h = STYLE._flow(self.items, self.width(), True)
        if h != self.height():
            self.setFixedHeight(h)


class ModeButton(QPushButton):
    """Knopf der Modusleiste im Segmentstil: nur Symbol, die Taste als kleines Zeichen unten rechts; angewählt in der
    Akzentfarbe (Fläche wie die Reiter, `segBtn:checked`). Breite = Höhe der Leistenknöpfe."""

    def __init__(self, icon_name, key):
        super().__init__("", objectName="segBtn")
        self.icon_name, self.key = icon_name, key
        self.setFixedWidth(STYLE.CONTROL_H)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        from PySide6.QtGui import QColor, QFont, QPainter
        c = STYLE.colors()
        col = c["accent"] if self.isChecked() else (c["text"] if self.isEnabled() else c["disabled"])
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pm = STYLE.pixmap(self.icon_name, STYLE.ICON_PX, col)
        sh = STYLE.MODE_BADGE_INSET
        p.drawPixmap((self.width() - STYLE.ICON_PX) // 2 - sh, (self.height() - STYLE.ICON_PX) // 2 - sh, pm)
        f = QFont(self.font())
        f.setPixelSize(STYLE.MODE_BADGE_PX)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(c["accent"] if self.isChecked() else c["text2"]))
        p.drawText(self.rect().adjusted(0, 0, -sh, -sh), Qt.AlignRight | Qt.AlignBottom, self.key)
        p.end()

    def set_icon(self, name):
        self.icon_name = name
        self.update()


class NMRView(QWidget):
    """Spektrum mit Modusleiste und Statuszeile. Ansichtsaktionen ändern nur die Grenzen; alles andere (Daten,
    Anzeige, Phase) zeichnet mit denselben Grenzen neu: nichts springt von selbst."""

    mode_changed = Signal(str)
    integrals_changed = Signal(list)
    peaks_changed = Signal(list)
    multiplets_changed = Signal(list)
    cuts_changed = Signal(list)
    insets_changed = Signal(list)
    peak_pick_requested = Signal(float, float, float)      # lo, hi, Schwelle (y)
    multiplet_requested = Signal(float, float, float)      # lo, hi, Schwelle (y)
    marks_changed = Signal(list)                            # [{x, text}] Marken über Signalen
    reference_clicked = Signal(float)                       # δ der getroffenen Peakspitze
    distance_measured = Signal(float, float, object)        # δ1, δ2, Abstand in Hz (None ohne SF)
    phase_changed = Signal(float, float, float)             # PHC0, PHC1 [°], Drehpunkt [ppm]
    display_changed = Signal(dict)
    view_changed = Signal(tuple)                            # neue Zoomstufe (xlim) im Verlauf
    selection_changed = Signal(object)                      # (Ebene, Index) oder None, nach jedem Zeichnen geprüft

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x = self.y = self._yplot = None
        self.sf = None
        self.title, self.nucleus = "", "1H"
        self.peak_digits = 2
        self.integrals, self.peaks, self.multiplets, self.cuts, self.insets, self.solvents = [], [], [], [], [], []
        self.marks = []
        self.fit_lines = []                                  # [{x, ok}] Linien eines Musterfits (nur Bildschirm)
        self._last_sel = None
        self.screen = True                                   # False: Abbildung für die SI (ohne Bedienhilfen)
        self.struct_box = None                               # Struktur im Bild (Bildanteile x0, y0, x1, y1): Ausschnitte meiden sie
        self.struct_left = True                              # ohne bekannte Box: linkes Drittel freihalten (Struktur folgt)
        self.notes = []                                      # Hinweise der letzten Zeichnung (kein Platz für einen Ausschnitt)
        # Vergleich (Überlagert/Gestapelt): weitere Spuren {x, y, color, label, kind "trace"/"pred", h}; das Hauptspektrum
        # trägt main_label. Vorhersage („pred“) nur am Bildschirm (`screen`), nie in einer Abbildung für die SI
        self.traces, self.stack, self.offset, self.main_label = [], False, 1.0, None
        self.opts = dict(SHOW_DEFAULT)
        self.mode, self.zoom_kind, self.pan_kind = "pointer", "h", "free"
        self.xlim = self.ylim = None
        self.history, self.hist_i = [], -1
        self.selected = None                                 # (Ebene, Index)
        self.drag = None
        self.measure = []                                    # Klicks des Fadenkreuzes
        self.ph0 = self.ph1 = 0.0
        self.pivot = None
        self.phase_cb = None                                 # (ph0, ph1, pivot) -> neues y
        self._ov, self._insets_ax, self._bg, self._rubber, self._cross = [], [], None, [], []
        self._fast, self._fast_bg = None, None
        self._mark_texts = []                               # Marken („*“) der letzten Zeichnung
        self._inset_boxes = []                              # (Index, Achse) der gezeichneten Ausschnitte              # schnelles Zeichnen beim Ziehen („pan“/„phase“)
        self._boxes = {}
        self.cfg = core.deep_merge(core.DEFAULTS, {})
        self.cfg["font_size"] = 11.0                         # Bildschirmansicht, nicht die SI-Abbildung
        core.setup_fonts(plt, self.cfg)                       # vor den Achsen: ihre Texte merken sich den Mathtext-Satz
        self.fig = MplFigure(figsize=(8, 5), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.installEventFilter(self)
        self.ax = self.fig.add_axes([0.05, 0.1, 0.9, 0.85])
        self.line, = self.ax.plot([], [], color=C_LINE, lw=0.9, zorder=3)
        self.host = _Host(self.canvas, self.fig, page=True)
        self._build()
        c = self.canvas
        for name, fn in (("button_press_event", self._press), ("motion_notify_event", self._move),
                         ("button_release_event", self._release), ("scroll_event", self._scroll),
                         ("draw_event", self._on_draw), ("resize_event", lambda _e: self.redraw()),
                         ("figure_leave_event", self._leave)):
            c.mpl_connect(name, fn)
        self.set_mode("pointer")

    # -- Aufbau ------------------------------------------------------------------------------------------------------
    def _seg(self, names):
        """Knopfgruppe im Segmentstil: Modi schaltbar (der aktive hervorgehoben), Aktionen einfache Knöpfe."""
        frame = QFrame(objectName="seg")
        h = QHBoxLayout(frame)
        m = STYLE.BAR_H - STYLE.CONTROL_H                    # Segmentrahmen: Knöpfe 28 hoch in BAR_H
        h.setContentsMargins(m, m, m, m)
        h.setSpacing(m)
        for name in names:
            mode = name in MODES
            key, icon = (MODES if mode else ACTIONS)[name]
            b = ModeButton(icon, key)
            b.setCheckable(mode)
            b.setToolTip(T(f"nmrv_{name}_tip"))                # Name, Taste und Bedienung
            fn = (lambda n: self.set_mode(n, cycle=True)) if mode else self.action
            b.clicked.connect(lambda _c=False, n=name, fn=fn: (fn(n), self.canvas.setFocus()))
            h.addWidget(b)
            (self.mode_buttons if mode else self.action_buttons)[name] = b
        return frame

    def _build(self):
        # vier Gruppen (Ansichtsmodi, Ansichtsaktionen, zwei mal Auswerten), die wie Text umbrechen: die rechte Seite ist
        # bei 960 px Fenster nur ~420 px breit, die Leiste darf die Mindestbreite nicht hochtreiben (ui.md)
        self.mode_buttons, self.action_buttons = {}, {}
        self.segs = [self._seg(("pointer", "zoom", "pan")), self._seg(("zoom_out", "full", "highest", "prev", "next")),
                     self._seg(("integral", "peaks", "multiplet", "reference")),
                     self._seg(("cursor", "cut", "inset", "mark", "phase"))]
        bar = self.bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(TABS.PAGE_INSET[0], 0, TABS.PAGE_INSET[2], 0)
        self.flow = _FlowBar(self.segs)
        h.addWidget(self.flow)
        self.lbl_hint = STYLE.SciLabel()
        self.lbl_hint.setStyleSheet(STYLE.HINT_CSS)
        self.lbl_hint.setWordWrap(True)                      # schmale Seite: umbrechen statt Mindestbreite
        self.lbl_read = STYLE.SciLabel()
        self.btn_delete = QPushButton(STYLE.icon("trash", lone=True), "")
        self.btn_delete.setToolTip(T("nmrv_delete"))
        self.btn_delete.setFocusPolicy(Qt.NoFocus)
        self.btn_delete.clicked.connect(self.delete_selected)
        status = QHBoxLayout()
        side = TABS.PAGE_INSET[0] + STYLE.COL_PAD           # bündig mit dem Karteninhalt der rechten Seite
        status.setContentsMargins(side, 0, side, 0)
        status.addWidget(self.lbl_hint, 1)
        status.addWidget(self.lbl_read)
        status.addWidget(self.btn_delete)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.addWidget(bar)
        v.addWidget(self.host, 1)
        v.addLayout(status)
        self.lbl_note = STYLE.HintLabel("", wordWrap=True)    # leer = keine Zeile
        self.lbl_note.setStyleSheet(f"color: {STYLE.WARN_COLOR};")
        self.lbl_note.setContentsMargins(side, 0, side, 0)
        v.addWidget(self.lbl_note)

    def display_card(self):
        """Karte „Anzeige“ für die linke Spalte (Kästchen + Auswahlliste; `STYLE.tidy` macht daraus Chips und das Feld
        „Multiplett-Labels“ mit „aus“)."""
        g = QGroupBox(T("nmrv_display"))
        f = STYLE.make_form(g)
        self._boxes = {}
        for k in SHOW_KEYS:
            b = self._boxes[k] = QCheckBox(T(f"nmrv_show_{k}"))
            b.setChecked(self.opts[k])
            b.toggled.connect(lambda on, k=k: self._set_show(k, on))
            f.addRow(b)
        b = self._boxes["mult_labels"] = QCheckBox(T("nmrv_show_mult_labels"))
        b.setChecked(self.opts["mult_labels"])
        b.toggled.connect(lambda on: self._set_show("mult_labels", on))
        cmb = self.cmb_mult = QComboBox()
        for k in MULT_LABELS:
            cmb.addItem(T(f"nmrv_ml_{k}"), k)
        cmb.setCurrentIndex(MULT_LABELS.index(self.opts["mult_label"]))
        cmb.setToolTip(T("nmrv_ml_tip"))
        cmb.currentIndexChanged.connect(lambda i: self._set_show("mult_label", MULT_LABELS[i]))
        row = QHBoxLayout()
        row.addWidget(b)
        row.addWidget(cmb)
        f.addRow(row)
        cm = self.cmb_mark = QComboBox()                   # Zeichen neuer Marken (Modus T)
        for sym in MARK_SYMBOLS:
            cm.addItem(sym, sym)
        cm.setCurrentIndex(MARK_SYMBOLS.index(self.opts["mark_symbol"]))
        cm.setToolTip(T("nmrv_mark_symbol_tip"))
        cm.currentIndexChanged.connect(lambda i: self._set_show("mark_symbol", MARK_SYMBOLS[i]))
        self._boxes["mark_symbol"] = cm
        f.addRow(T("nmrv_mark_symbol"), cm)
        return g

    # -- Daten ---------------------------------------------------------------------------------------------------------
    def set_spectrum(self, x, y, sf=None, title="", nucleus="1H"):
        """Neues Spektrum. Vollansicht nur beim ersten oder bei anderer Achse; gleiche Achse (z. B. neu phasiert) behält
        die Ansicht."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        same = self.x is not None and len(self.x) == len(x) and np.allclose(self.x[[0, -1]], x[[0, -1]])
        self.x, self.y, self.sf, self.title, self.nucleus = x, y, sf, title or "", nucleus
        self._mask()
        if not same or self.xlim is None:
            self.history, self.hist_i = [], -1
            self.ph0 = self.ph1 = 0.0                        # anderes Spektrum: Phase und Drehpunkt gelten nicht mehr
            self.pivot = None
            self.full_view()
        else:
            self.redraw()

    def set_integrals(self, items):
        self.integrals = [dict(r) for r in items]
        self._drop_selection("integrals")

    def set_peaks(self, items):
        self.peaks = [dict(p) for p in items]
        self._drop_selection("peaks")

    def set_multiplets(self, items):
        self.multiplets = [dict(m) for m in items]
        self._drop_selection("multiplets")

    def set_cuts(self, items):
        self.cuts = merge_ranges(items)
        self._mask()
        self._drop_selection("cuts")

    def set_insets(self, items):
        self.insets = [dict(r) for r in items]
        self._drop_selection("insets")

    def set_marks(self, items):
        """Marken über Signalen ({x, text}, z. B. „*“ für H2O)."""
        self.marks = [dict(m) for m in items]
        self._drop_selection("marks")

    def set_fit_lines(self, items):
        """Linienlagen eines Multiplett-Vorschlags ({x, ok}): kurze Striche über dem Spektrum, damit ein falscher
        Vorschlag sichtbar ist (orange = Vorschlag, grün = bestätigt). Nur am Bildschirm."""
        self.fit_lines = [dict(f) for f in items]
        self.redraw()

    def set_solvents(self, items):
        self.solvents = [dict(s) for s in items]
        self.redraw()

    def set_phase_callback(self, fn):
        """fn(ph0, ph1, pivot) -> y (gleiche Länge) oder None; rechnet außerhalb (Spur B2)."""
        self.phase_cb = fn

    def display(self):
        """Anzeige, Aussehen und die Ausschnitte (mit Lage, Größe und Intensität) zum Speichern im Tab."""
        return dict(self.opts, insets=[dict(i) for i in self.insets])

    def set_display(self, d):
        """Anzeige und Aussehen setzen (gespeicherter Zustand des Tabs); Felder der Karten folgen ohne eigene Signale."""
        for k, v in d.items():
            if k not in self.opts:
                continue
            self.opts[k] = v
            w = self._boxes.get(k)
            if isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QDoubleSpinBox):
                w.blockSignals(True)
                w.setValue(float(v))
                w.blockSignals(False)
            elif isinstance(w, QComboBox):
                w.blockSignals(True)
                w.setCurrentIndex(max(0, w.findData(v)))
                w.blockSignals(False)
            elif isinstance(w, QPushButton):                 # Farbfeld (TABS.color_button)
                w.setProperty("color", v)
                w.setStyleSheet(STYLE.swatch_css(v, w.property('cellcss') or ''))
        if "insets" in d:
            self.insets = [dict(i) for i in d["insets"]]
        if "mult_label" in d and hasattr(self, "cmb_mult"):
            self.cmb_mult.setCurrentIndex(MULT_LABELS.index(self.opts["mult_label"]))
        self.redraw()

    def reset_display(self):
        """„Darstellung zurücksetzen“: Anzeige und Aussehen wie die Vorlage."""
        self.set_display(SHOW_DEFAULT)
        self.display_changed.emit(self.display())

    def style_card(self):
        """Karte „Aussehen“ (Schritt Darstellung): je Zeile Farbe und Dicke bzw. Größe als Paar im Raster der Spalte
        (Beschriftung + Farbfeld | Beschriftung + Zahlenfeld, `tidy`); Vorgabe = Vektorwerte der Mnova-Vorlage."""
        from PySide6.QtWidgets import QLabel
        g = QGroupBox(T("nmrv_style"))
        f = STYLE.make_form(g)

        def color(k):
            b = self._boxes[k] = TABS.color_button(self.opts[k], lambda c, k=k: self._set_show(k, c))
            b.setToolTip(T(f"nmrv_st_{k}"))
            return b

        def spin(k, lo, hi, step):
            sp = self._boxes[k] = QDoubleSpinBox(decimals=3 if step < 0.1 else 2, minimum=lo, maximum=hi, singleStep=step,
                                                 suffix=" pt")
            sp.setValue(self.opts[k])
            sp.setToolTip(T(f"nmrv_st_{k}"))
            sp.valueChanged.connect(lambda v, k=k: self._set_show(k, v))
            return sp
        for label, ck, nk, word, lo, hi, step in (
                ("nmrv_st_spectrum", "spectrum_color", "spectrum_width", "nmrv_st_width", 0.1, 5.0, 0.05),
                # Peak-Labels: Vorgabe = Vorlage, nur größer stellbar (Entscheidung 78)
                ("nmrv_st_labels", "peak_label_color", "peak_label_size", "nmrv_st_size",
                 STYLE_DEFAULT["peak_label_size"], 24.0, 0.5),
                ("nmrv_st_bracket", "integral_bracket_color", "integral_bracket_width", "nmrv_st_width", 0.1, 5.0, 0.05),
                ("nmrv_st_values", "integral_value_color", "integral_value_size", "nmrv_st_size", 2.0, 24.0, 0.5),
                ("nmrv_st_solvent", "solvent_label_color", "solvent_label_size", "nmrv_st_size", 2.0, 24.0, 0.5),
                ("nmrv_st_axis", "axis_color", "axis_font_size", "nmrv_st_size", 2.0, 24.0, 0.5),
                ("nmrv_st_marks", "mark_color", "mark_size", "nmrv_st_size", 2.0, 24.0, 0.5)):
            row = QHBoxLayout()
            for w in (QLabel(T("nmrv_st_color")), color(ck), QLabel(T(word)), spin(nk, lo, hi, step)):
                row.addWidget(w)
            f.addRow(T(label), row)
        return g

    def _set_show(self, k, v):
        if self.opts.get(k) == v:
            return
        self.opts[k] = v
        self.redraw()
        self.display_changed.emit(self.display())

    def _drop_selection(self, layer):
        if self.selected and self.selected[0] == layer:
            self.selected = None
        self.redraw()

    def _mask(self):
        if self.y is None:
            return
        yp = self.y.copy()
        for c in self.cuts:
            yp[(self.x > c["lo"]) & (self.x < c["hi"])] = np.nan
        self._yplot = yp

    # -- Modi und Aktionen ---------------------------------------------------------------------------------------------
    def set_mode(self, mode, cycle=False):
        """Modus setzen; derselbe Modus noch einmal (Taste oder Knopf) wechselt bei Zoom und Verschieben die Art."""
        if cycle and mode == self.mode == "zoom":
            self.zoom_kind = ZOOM_KINDS[(ZOOM_KINDS.index(self.zoom_kind) + 1) % 3]
        elif cycle and mode == self.mode == "pan":
            self.pan_kind = PAN_KINDS[(PAN_KINDS.index(self.pan_kind) + 1) % 3]
        if mode != self.mode:
            self._cancel_drag()
            if mode not in ("cursor",):
                self.measure = []
            if self.selected and RANGE_LAYER.get(mode, mode) != self.selected[0]:
                self.selected = None
            if mode == "phase" and self.pivot is None and self.y is not None:
                self.pivot = float(self.x[int(np.nanargmax(self._yplot))])        # Mnova: größter Peak
        self.mode = mode
        for n, b in self.mode_buttons.items():
            b.setChecked(n == mode)
        self.mode_buttons["zoom"].set_icon(f"nmrv_zoom_{self.zoom_kind}")
        self.mode_buttons["pan"].set_icon(f"nmrv_pan_{self.pan_kind}")
        self.lbl_hint.setText(self.hint())
        self.redraw()
        self.mode_changed.emit(mode)

    def hint(self):
        sub = {"zoom": "_" + self.zoom_kind, "pan": "_" + self.pan_kind}.get(self.mode, "")
        return T(f"nmrv_hint_{self.mode}{sub}")

    def action(self, name):
        {"zoom_out": self.zoom_out, "full": self.full_view, "highest": self.fit_highest, "prev": self.prev_zoom,
         "next": self.next_zoom}[name]()

    def _visible(self, xlim=None):
        """Indizes im sichtbaren ppm-Bereich ohne Schnitte."""
        a, b = sorted(xlim or self.xlim)
        return np.flatnonzero((self.x >= a) & (self.x <= b) & np.isfinite(self._yplot))

    def _pt(self, v):
        return v * self.fig.dpi / 72

    def _ratio(self):
        """Gerätepixel je Bildschirmpunkt: Greifweiten bleiben am Bildschirm gleich, egal wie groß die Abbildung ist."""
        return getattr(self.canvas, "device_pixel_ratio", 1) or 1

    def _label_len(self, n, size):
        """Länge eines senkrechten Labels mit n Zeichen in px (Ziffernbreite 0.556 em, Arial)."""
        return self._pt(0.556 * size * n + 1)

    def _bands(self):
        """Platz oben (Labelreihe: längstes Label + Leitlinie + Luft; Multiplett-Labels) und unten (Grundlinie 25.3 pt
        über der Achse wie die Vorlage, ohne Integralwerte 4 pt) als Anteil der Achsenhöhe."""
        o = self.opts
        hgt = max(self.ax.bbox.height, 1.0)
        top = 0.0
        lens = ([(self.peak_digits + 3, o["peak_label_size"])] if o["peak_labels"] and self.peaks else []) + (
            [(len(s_.get("name", "")) + 5, o["solvent_label_size"]) for s_ in self.solvents] if o["solvents"] else [])
        if lens:
            top += max(self._label_len(n, sz) for n, sz in lens) + self._pt(sum(G["lead"]) + 4)
        if o["mult_labels"] and self.multiplets:
            from matplotlib.font_manager import FontProperties
            sz, r = self._ml_size(), self.canvas.get_renderer()   # zu breit für eine Zeile: senkrecht (_multiplets_ov),
            lens = [r.get_text_width_height_descent(self._ml_text(m), FontProperties(size=sz), ismath=False)[0]
                    for m in self.multiplets]                  # dann so hoch wie das längste Label
            rot = sum(n + 6 for n in lens) > self.ax.bbox.width
            top += (max(lens) + 4 if rot else self._pt(1.3 * sz)) + self._pt(8) + 10   # + Streifen der Verbindungen
        bot = self._pt(G["base"] if (o["int_values"] and any(r.get("value") is not None for r in self.integrals)) else 4)
        return min(top / hgt, 0.5), min(bot / hgt, 0.4)

    def lanes(self):
        """Spuren unter dem Hauptspektrum: gestapelte Spektren, darunter die Vorhersage (nur am Bildschirm)."""
        return [t_ for t_ in self.traces if t_["kind"] == "trace" and self.stack] + \
            [t_ for t_ in self.traces if t_["kind"] == "pred" and self.screen]

    def _lane_fracs(self, ls):
        """Lage der Spuren als Anteil der Achsenhöhe: (Höhe des Hauptspektrums, Grundlinien relativ zu seiner, unterer
        Rand). Erste Spur unter dem Band der Integralwerte, weitere im Abstand `offset` × Spurhöhe."""
        top_f, bot_f = self._bands()
        t, m0, gap = 1 - top_f - 0.03, 0.03, 0.02
        rest = sum(l_["h"] for l_ in ls[1:])
        ha = max(t - m0 - bot_f - (len(ls) - 1) * gap, 0.05) / (1 + ls[0]["h"] + self.offset * rest)
        bases, b = [], 0.0
        for k, l_ in enumerate(ls):
            b = (-bot_f - l_["h"] * ha) if k == 0 else b - self.offset * l_["h"] * ha - gap
            bases.append(b)
        return ha, bases, -bases[-1] + m0

    def fit_highest(self, record=True, xlim=None):
        """H: höchster sichtbarer Punkt auf Fensterhöhe (unter den Labels), Grundlinie über den Integralwerten."""
        if self.x is None:
            return
        xlim = xlim or self.xlim
        idx = self._visible(xlim)
        ymax = float(np.nanmax(self.y[idx])) if len(idx) else 1.0
        ymax = ymax if ymax > 0 else 1.0
        ls = self.lanes()
        if ls:                                             # Spuren darunter: Hauptspektrum oben, Spuren in den Rest
            ha, _bases, B = self._lane_fracs(ls)
            rng = ymax / ha
            return self.set_view(xlim, (-B * rng, -B * rng + rng), record)
        top_f, bot_f = self._bands()
        t, b = 1 - top_f - 0.03, bot_f
        rng = ymax / max(t - b, 0.1)
        self.set_view(xlim, (-b * rng, -b * rng + rng), record)

    def full_view(self):
        """F (und Doppelklick): ganzes Spektrum, Höhe wie H."""
        if self.x is None:
            return
        self.fit_highest(xlim=(float(self.x.max()), float(self.x.min())))

    def zoom_out(self):
        """Shift+Z: Ausschnitt waagerecht verdoppeln (um die Mitte, nicht über das Spektrum hinaus)."""
        if self.x is None:
            return
        l, r = self.xlim
        mid, half = (l + r) / 2, (l - r)
        hi, lo = float(self.x.max()), float(self.x.min())
        half = min(half, (hi - lo) / 2)
        mid = min(max(mid, lo + half), hi - half)
        self.set_view((mid + half, mid - half), self.ylim)

    def intensity(self, steps):
        """Mausrad/+/-: Intensität um WHEEL je Schritt, die Grundlinie bleibt an ihrer Höhe (nicht als Zoomstufe)."""
        if self.ylim is None:                            # noch kein Spektrum
            return
        f = WHEEL ** steps
        self.set_view(self.xlim, (self.ylim[0] / f, self.ylim[1] / f), record=False)

    def set_view(self, xlim, ylim, record=True):
        self.xlim, self.ylim = (float(xlim[0]), float(xlim[1])), (float(ylim[0]), float(ylim[1]))
        if record:
            del self.history[self.hist_i + 1:]
            self.history.append((self.xlim, self.ylim))
            self.hist_i = len(self.history) - 1
            self.view_changed.emit(self.xlim)
        self._sync_history()
        self.redraw()

    def _sync_history(self):
        self.action_buttons["prev"].setEnabled(self.hist_i > 0)
        self.action_buttons["next"].setEnabled(0 <= self.hist_i < len(self.history) - 1)

    def prev_zoom(self):
        if self.hist_i > 0:
            self.hist_i -= 1
            self.set_view(*self.history[self.hist_i], record=False)

    def next_zoom(self):
        if self.hist_i < len(self.history) - 1:
            self.hist_i += 1
            self.set_view(*self.history[self.hist_i], record=False)

    def delete_selected(self):
        if not self.selected:
            return
        layer, i = self.selected
        items = getattr(self, layer)
        del items[i]
        self.selected = None
        if layer == "cuts":
            self._mask()
        self.redraw()
        self._emit(layer)

    def _emit(self, layer):
        sig = {"integrals": self.integrals_changed, "peaks": self.peaks_changed, "cuts": self.cuts_changed,
               "insets": self.insets_changed, "multiplets": self.multiplets_changed, "marks": self.marks_changed}[layer]
        sig.emit([dict(r) for r in getattr(self, layer)])

    # -- Tasten (nur mit Fokus im Bild: Buchstaben in Feldern bleiben Text) --------------------------------------------
    def take_focus(self):
        """Tasten wie in Mnova ohne vorherigen Klick (Entscheidung 121): das Spektrum nimmt den Fokus, außer ein
        Textfeld, in dem getippt wird, hat ihn. Nur im aktiven Fenster (Maus über einem Fenster im Hintergrund)."""
        from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QLineEdit, QPlainTextEdit, QTextEdit
        if not self.canvas.window().isActiveWindow():
            return False
        f = QApplication.focusWidget()
        if isinstance(f, (QLineEdit, QAbstractSpinBox, QTextEdit, QPlainTextEdit)) or \
                isinstance(f, QComboBox) and f.isEditable():
            return False
        if self.canvas.isVisible():
            self.canvas.setFocus(Qt.MouseFocusReason)
        return self.canvas.hasFocus()

    def eventFilter(self, obj, ev):
        t = ev.type()
        if obj is self.canvas and t == QEvent.Enter:
            self.take_focus()
        if obj is self.canvas and t in (QEvent.KeyPress, QEvent.ShortcutOverride):
            fn = self._key_action(ev.key(), ev.modifiers())
            if fn is None:
                return False
            if t == QEvent.ShortcutOverride:                  # vor Menükürzeln des Fensters
                ev.accept()
                return True
            fn()
            return True
        return super().eventFilter(obj, ev)

    def _key_action(self, key, mods):
        shift = bool(mods & Qt.ShiftModifier)
        if mods & Qt.AltModifier and not mods & (Qt.ControlModifier | Qt.MetaModifier) and key in (Qt.Key_Left,
                                                                                                    Qt.Key_Right):
            return self.prev_zoom if key == Qt.Key_Left else self.next_zoom   # Alt+←/→: jede Tastaturbelegung
        if mods & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return None
        letters = {Qt.Key_I: "integral", Qt.Key_K: "peaks", Qt.Key_J: "multiplet", Qt.Key_R: "reference",
                   Qt.Key_L: "reference", Qt.Key_C: "cursor", Qt.Key_X: "cut", Qt.Key_E: "inset",
                   Qt.Key_T: "mark"}
        if key == Qt.Key_Escape:
            return self.escape
        if key == Qt.Key_Z:
            return self.zoom_out if shift else (lambda: self.set_mode("zoom", cycle=True))
        if key == Qt.Key_P:
            return (lambda: self.set_mode("phase")) if shift else (lambda: self.set_mode("pan", cycle=True))
        if shift and key not in (Qt.Key_Greater, Qt.Key_Less, Qt.Key_Plus):     # US: < und > liegen auf Umschalt
            return None
        if key in letters:
            return lambda m=letters[key]: self.set_mode(m)
        return {Qt.Key_F: self.full_view, Qt.Key_H: self.fit_highest, Qt.Key_Less: self.prev_zoom,
                Qt.Key_Greater: self.next_zoom, Qt.Key_Plus: lambda: self.intensity(1),
                Qt.Key_Minus: lambda: self.intensity(-1), Qt.Key_Delete: self.delete_selected,
                Qt.Key_Backspace: self.delete_selected}.get(key)

    def escape(self):
        """Esc: laufendes Ziehen abbrechen, sonst Auswahl aufheben und zurück zum Zeiger (Mnova)."""
        if self.drag is not None:
            self._cancel_drag(revert=True)
            self.redraw()
            return
        self.selected = None
        self.measure = []
        self.set_mode("pointer")

    # -- Zeichnen ------------------------------------------------------------------------------------------------------
    def _layout(self):
        """Achse in pt der Nennbreite: Achse fast über die ganze Breite (Vorlage), unten Striche, Zahlen und
        „δ ¹H (ppm)“ (15.1 pt in der Vorlage), oben der Titel, links die Intensitätsachse."""
        W, H = self.fig.bbox.width, self.fig.bbox.height
        if W < 10 or H < 10:
            return
        fs = self.opts["axis_font_size"]
        left = self._pt(SIDE_PT + (4 * fs if self.opts["y_axis"] else 0))
        right = self._pt(SIDE_PT)
        top = self._pt(2 * self.cfg["font_size"] * 0.5 if self.opts["title"] and self.title else 2)
        bottom = self._pt(G["tick"] + 1 + 2 * 1.2 * fs + 1)
        self.ax.set_position([left / W, bottom / H, max(0.1, 1 - (left + right) / W), max(0.1, 1 - (top + bottom) / H)])

    def axis_label(self):
        return nucleus_axis_label(self.nucleus)

    def _style_axis(self, ax, cuts):
        """Achse wie die Vorlage: nur unten, Striche nach außen, Hauptstriche >= 14 pt auseinander, Zwischenstriche."""
        o = self.opts
        fs, col = o["axis_font_size"], o["axis_color"]
        nb = ax.bbox.width / self._pt(G["tick_step"])
        dig = self._pt(0.556 * fs)                        # Ziffernbreite: Zahlen passen zwischen ihre Striche
        ax.xaxis.set_major_locator(_CutLocator(cuts, self._pt(1.6), nb,       # nur Striche in der 3-pt-Lücke; Zahlen
                                               sep_px=dig / 2, char_px=dig))  # über den Bruch: ½ Ziffer Luft
        ax.xaxis.set_minor_locator(_CutLocator(cuts, 0.0, nb, minor=True, char_px=dig))
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_linewidth(G["stroke"])
        ax.spines["bottom"].set_color(col)
        ax.tick_params(axis="x", which="major", direction="out", length=G["tick"], width=G["stroke"], pad=1.0,
                       labelsize=fs, colors=col)
        ax.tick_params(axis="x", which="minor", direction="out", length=G["minor"], width=G["stroke"], colors=col)
        ax.tick_params(axis="y", left=False, labelleft=False)
        ax.set_xlabel(self.axis_label(), fontsize=fs, labelpad=0.5, color=col)

    def redraw(self):
        """Alles neu zeichnen mit den aktuellen Grenzen (die Ansicht selbst ändert sich hier nie)."""
        if self.x is None or self.xlim is None:
            self.canvas.draw_idle()
            return
        cfg, o = self.cfg, self.opts
        core.setup_fonts(plt, cfg)
        ax = self.ax
        for a in self._ov:
            a.remove()
        for a in self._insets_ax:
            a.remove()
        self._ov, self._insets_ax = [], []
        self.notes = []
        self._layout()
        fwd, inv = cut_functions(self.cuts, float(self.x.min()), float(self.x.max()),
                                 self._gap(self.cuts, self.xlim, self.ax.bbox.width))
        ax.set_xscale("function", functions=(fwd, inv))
        self.line.set_data(self.x, self._yplot)
        self.line.set_color(o["spectrum_color"])
        self.line.set_linewidth(o["spectrum_width"])
        ax.set_xlim(*self.xlim)
        ax.set_ylim(*self.ylim)
        self._style_axis(ax, self.cuts)
        ax.spines["left"].set_visible(o["y_axis"])
        ax.tick_params(axis="y", left=o["y_axis"], labelleft=o["y_axis"], labelsize=o["axis_font_size"])
        ax.grid(False)
        if o["grid"]:                                        # grid(False, color=…) schaltete es wieder ein
            ax.grid(True, color=STYLE.FIG_GRID_COLOR, lw=0.5, zorder=0)
        self._title()
        try:
            r = self.canvas.get_renderer()
            self._integrals_ov(r)
            self._label_row(self.ax, r, self._multiplets_ov(r), self._row_items())
            self._marks_text()
            self._ranges_ov()
            self._cuts_ov()
            self._insets_ov()
            self._marks_ov()
            self._traces_ov()
        finally:
            self._sync_delete()
            if self.screen:                                  # Hinweise der Zeichnung (Labels zu dicht, kein Platz)
                self.lbl_note.setText(" ".join(dict.fromkeys(self.notes)))
            self.canvas.draw_idle()
            if self.selected != self._last_sel:
                self._last_sel = self.selected
                self.selection_changed.emit(self.selected)

    def _add(self, a):
        self._ov.append(a)
        return a

    def _vmax(self, x, y):
        a, b = sorted(self.xlim)
        m = (x >= a) & (x <= b) & np.isfinite(y)
        v = float(np.nanmax(y[m])) if m.any() else 0.0
        return v if v > 0 else 1.0

    def _traces_ov(self):
        """Vergleich: überlagerte Spuren auf derselben Grundlinie und Höhe wie das Hauptspektrum (Legende im Bild) oder
        gestapelte Spuren darunter (Beschriftung links über der Grundlinie); die Vorhersage nur am Bildschirm."""
        ax, o = self.ax, self.opts
        fs, lw = o["axis_font_size"], o["spectrum_width"]
        traces = [t_ for t_ in self.traces if t_["kind"] != "pred" or self.screen]
        if not traces:
            return
        from matplotlib.transforms import blended_transform_factory
        lab = blended_transform_factory(ax.transAxes, ax.transData)
        ymax = self._vmax(self.x, self._yplot)
        if not self.stack:                                 # überlagert: hinter dem Hauptspektrum, gleiche Höhe
            lines = [self.line]
            for t_ in traces:
                if t_["kind"] == "trace":
                    lines.append(self._add(ax.plot(t_["x"], t_["y"] * ymax / self._vmax(t_["x"], t_["y"]),
                                                   color=t_["color"], lw=lw, zorder=2)[0]))
            if self.main_label and len(lines) > 1:
                self._add(ax.legend(lines, [self.main_label] + [t_["label"] for t_ in traces if t_["kind"] == "trace"],
                                    loc="best", frameon=False, fontsize=fs, handlelength=1.6, borderaxespad=0.6))
        labels = []                                        # (Text, x, y, Grundlinie, Höhe, Farbe, kursiv)
        if self.stack and self.main_label:
            labels.append((self.main_label, self.x, self._yplot, 0.0, ymax, o["spectrum_color"], False))
        ls = self.lanes()
        ha, bases, _B = self._lane_fracs(ls) if ls else (0.0, [], 0.0)
        rng = self.ylim[1] - self.ylim[0]
        lo, hi = sorted(self.xlim)
        for t_, b in zip(ls, bases):
            base, hgt = b * rng, t_["h"] * ha * rng * 0.95
            y = base + t_["y"] * hgt / self._vmax(t_["x"], t_["y"])
            if t_["kind"] == "pred":                       # eigener Farbton, gefüllt, gestrichelte Grundlinie, kursiv
                self._add(ax.fill_between(t_["x"], base, y, color=t_["color"], alpha=0.18, lw=0, zorder=2))
                self._add(ax.plot([hi, lo], [base, base], color=t_["color"], lw=0.6, ls=(0, (4, 3)), zorder=2)[0])
            self._add(ax.plot(t_["x"], y, color=t_["color"], lw=0.8 if t_["kind"] == "pred" else lw, zorder=3)[0])
            labels.append((t_["label"], t_["x"], y, base, hgt, t_["color"], t_["kind"] == "pred"))
        self._lane_labels(labels, lab)

    def _lane_labels(self, labels, tr):
        """Beschriftungen der gestapelten Spuren über ihrer Grundlinie, alle am selben Rand (links, außer rechts liegen
        die Spuren unter den Beschriftungen niedriger), je über dem höchsten Punkt der Spur dort: nie auf einem Signal."""
        if not labels:
            return
        lo, hi = sorted(self.xlim)
        texts = [self._add(self.ax.text(0.004, base, text, transform=tr, fontsize=self.opts["axis_font_size"], color=col,
                                        style="italic" if it else "normal", ha="left", va="bottom", zorder=5))
                 for text, _x, _y, base, _h, col, it in labels]
        try:                                               # breiteste Beschriftung als Anteil der Achse
            r = self.fig.canvas.get_renderer()
            frac = max(t_.get_window_extent(r).width for t_ in texts) / max(self.ax.bbox.width, 1.0)
        except Exception:
            frac = 0.012 * max(len(lb[0]) for lb in labels)
        w = (min(frac, 0.45) + 0.02) * (hi - lo)

        def edge(x, y, base, a, b):
            x = np.asarray(x)
            m = (x >= a) & (x <= b)
            return float(np.nanmax(y[m]) - base) if m.any() else 0.0
        lift = {side: [max(0.18 * h, edge(x, y, base, *rng_) + 0.06 * h) / max(h, 1e-12)
                       for _t, x, y, base, h, _c, _i in labels]
                for side, rng_ in (("left", (hi - w, hi)), ("right", (lo, lo + w)))}   # links = hohe ppm
        side = "right" if max(lift["right"]) < max(lift["left"]) - 1e-9 else "left"
        for t_, lb, k in zip(texts, labels, lift[side]):
            t_.set_y(lb[3] + k * lb[4])
            if side == "right":
                t_.set_x(0.996)
                t_.set_ha("right")

    def _px(self, x, y=0.0):
        return self.ax.transData.transform((x, y))

    def _ytop(self, x):
        """Höhe des Spektrums an x (größter Punkt im Pixel um x, damit Leitlinien nicht in Linien enden)."""
        i = int(np.argmin(np.abs(self.x - x)))
        lo, hi = max(0, i - 3), min(len(self.x), i + 4)
        v = self._yplot[lo:hi]
        return float(np.nanmax(v)) if np.isfinite(v).any() else 0.0

    def _in_view(self, x):
        a, b = sorted(self.xlim)
        return a <= x <= b and not any(c["lo"] < x < c["hi"] for c in self.cuts)

    def _text(self, px, py, s, r=None, ax=None, **kw):
        """Text in Pixeln auf ax (Vorgabe: Hauptachse); Texte eines Ausschnitts gehören auf dessen Achse, sonst deckt
        seine weiße Fläche sie ab."""
        kw.setdefault("fontsize", self.cfg["font_size"] * 0.8)
        t = self._add((ax or self.ax).text(px, py, s, transform=IdentityTransform(), clip_on=False, zorder=6, **kw))
        return t, (t.get_window_extent(r) if r is not None else None)

    def _title(self):
        if self.opts["title"] and self.title:
            bb = self.ax.bbox
            self._add(self.fig.text(bb.x0 / self.fig.bbox.width, 1 - 6 * self.fig.dpi / 72 / self.fig.bbox.height,
                                    self.title, va="top", ha="left", fontsize=self.cfg["font_size"]))

    def _row_items(self, parts=None):
        """Peaks und Lösungsmittel der Labelreihe (in parts oder im sichtbaren Bereich) -> [(x, Text, Farbe, Größe)]."""
        o = self.opts
        inside = (lambda x: any(q["lo"] <= x <= q["hi"] for q in parts)) if parts else self._in_view
        items = []
        if o["peak_labels"]:
            items += [(p["x"], f"{p['x']:.{self.peak_digits}f}", C_SEL if self.selected == ("peaks", i)
                       else o["peak_label_color"], o["peak_label_size"]) for i, p in enumerate(self.peaks) if inside(p["x"])]
        if o["solvents"]:
            items += [(s_["x"], (f"{s_['x']:.2f} " + re.sub(r"(?<=[A-Za-z)])(\d+)", r"$_{\1}$", s_.get("name", ""))).strip(),
                       o["solvent_label_color"], o["solvent_label_size"]) for s_ in self.solvents if inside(s_["x"])]
        return sorted(items, key=lambda it: -it[0])

    def _label_row(self, ax, r, top_px, items, spans=None):
        """Labelreihe wie Mnova: senkrecht, unten bündig (lange Texte reichen höher), auseinandergerückt; Leitlinie
        1.26 pt senkrecht, 2.51 pt schräg zur Peaklage, 1.26 pt senkrecht – nie bis zum Peak. spans: Teilbereiche eines
        Ausschnitts [(lo, hi) ppm]; je Teil eine eigene Gruppe über dem Teil (Mnova), Schrift und Unterkante gemeinsam."""
        if not items:
            return
        bb = ax.bbox
        longest = max(self._label_len(len(re.sub(r"\$_\{(\d+)\}\$", r"\1", t)), sz) for _, t, _, sz in items)
        ybot = bb.y1 - top_px - longest
        texts = [(x, *self._text(0, ybot, t, r, ax, rotation=90, ha="center", va="bottom", color=c, fontsize=sz))
                 for x, t, c, sz in items]
        px = lambda v: ax.transData.transform((v, 0))[0]          # noqa: E731
        rows = [(list(range(len(texts))), bb.x0, bb.x1)]   # Ränder nach der Schriftgröße (unten)
        if spans:                                       # Teile: (Indizes, Kanten in px bis zur Mitte der Lücke zum Nachbarn)
            iv = sorted((sorted((px(lo), px(hi))), (lo, hi)) for lo, hi in spans)
            rows = []
            for k, ((a_, b_), (lo, hi)) in enumerate(iv):
                a_ = bb.x0 if k == 0 else (iv[k - 1][0][1] + a_) / 2
                b_ = bb.x1 if k == len(iv) - 1 else (b_ + iv[k + 1][0][0]) / 2
                rows.append(([i for i, (x, _, _) in enumerate(texts) if lo <= x <= hi], a_, b_))
            rows = [q for q in rows if q[0]]
        need = sum(self._pt(G["pitch"] * t.get_fontsize()) for _, t, _ in texts)
        if need > bb.width:                             # viele Peaks (13C): Schrift bis auf 60 % verkleinern (alle gleich)
            for _, t, _ in texts:
                t.set_fontsize(t.get_fontsize() * max(0.6, bb.width / need))
            texts = [(x, t, t.get_window_extent(r)) for x, t, _ in texts]
        pitch = self._pt(G["pitch"] * texts[0][1].get_fontsize())
        if any(len(idx) * pitch > b_ - a_ - (0.0 if spans else 1.5 * pitch) + 0.5 for idx, a_, b_ in rows) \
                and T("nmrv_labels_crowded") not in self.notes:
            self.notes.append(T("nmrv_labels_crowded"))   # passt auch so nicht: nur sagen, nichts ändern (Entscheidung 79)
        pxs = [px(x) for x, _, _ in texts]
        # Gruppen je Multiplett: aus den Multiplett-Bereichen, sonst Nachbarpeaks näher als 25 Hz (bzw. 0.05 ppm)
        gap = 25.0 / self.sf if self.sf else 0.05
        xs = list(pxs)
        for idx, a_, b_ in rows:
            idx = sorted(idx, key=lambda i: pxs[i])         # lokale Nummern 0..n-1 dieses Teils
            groups = []
            for k, i in enumerate(idx):
                prev = idx[groups[-1][-1]] if groups else None
                same = prev is not None and (abs(texts[prev][0] - texts[i][0]) < gap or any(
                    m["lo"] <= texts[prev][0] <= m["hi"] and m["lo"] <= texts[i][0] <= m["hi"] for m in self.multiplets))
                groups[-1].append(k) if same else groups.append([k])
            lo_, hi_ = (a_, b_) if spans else (a_ + pitch, b_ - pitch / 2)
            res = label_row([pxs[i] for i in idx], groups, pitch, lo_, hi_)
            for k, i in enumerate(idx):
                xs[i] = res[k]
        a, b, c = (self._pt(v) for v in G["lead"])
        y0 = ybot - self._pt(0.7)
        for (x, t, _), lx in zip(texts, xs):
            t.set_x(lx)
            px = ax.transData.transform((x, 0))[0]
            pts = [(lx, y0), (lx, y0 - a), (px, y0 - a - b), (px, y0 - a - b - c)]
            self._add(ax.add_line(Line2D(*zip(*pts), transform=IdentityTransform(), lw=G["stroke"],
                                         color=t.get_color(), clip_on=False, zorder=5)))

    def _ml_text(self, m):
        k = self.opts["mult_label"]
        n = m.get("digits", 2)
        rng = f"{m['hi']:.{n}f} – {m['lo']:.{n}f}"
        cls = m.get("cls") or ""
        # „m“ steht in der SI-Zeile als Bereich: dieselbe Zahl im Bild (nie eine Mitte, die nirgends gedruckt wird)
        d = rng if cls == "m" else (f"{m['delta']:.{n}f}" if m.get("delta") is not None else "")
        nh = f"{m['nH']:g}H" if m.get("nH") is not None else ""
        inner = ", ".join(s for s in (cls, nh) if s)
        return {"delta": d, "cls": cls, "delta_cls": f"{d} ({cls})" if cls else d,
                "delta_full": f"{d} ({inner})" if inner else d, "range": rng,
                "range_full": f"{rng} ({inner})" if inner else rng}[k]

    def _ml_size(self):
        """Schrift der Multiplett-Labels: in der SI-Abbildung wie die Peak-Labels; in der Ansicht mindestens ML_SCREEN_PX
        Bildschirmpunkte (sonst ~6 px, unlesbar), die Ansicht darf dafür größer beschriften als die Abbildung."""
        sz = self.opts["peak_label_size"]
        if not self.screen:
            return sz
        return max(sz, ML_SCREEN_PX * self._ratio() * 72 / max(self.fig.dpi, 1e-6))

    def _multiplets_ov(self, r):
        """Multiplett-Labels ganz oben (über den Peak-Labels: deren Leitlinien kreuzen sie so nie), Klammer über den
        Bereich. -> belegte Höhe in Pixeln."""
        if not (self.opts["mult_labels"] and self.multiplets):
            return 0.0
        bb = self.ax.bbox
        ytop = bb.y1 - 2
        vis = [(i, m) for i, m in enumerate(self.multiplets) if self._in_view((m["lo"] + m["hi"]) / 2)]
        items = []
        for i, m in vis:
            sel = self.selected == ("multiplets", i)
            t, e = self._text(0, ytop, self._ml_text(m), r, ha="center", va="top", color=C_SEL if sel else C_LINE,
                              fontsize=self._ml_size())
            items.append((m, t, e))
        if not items:
            return 0.0
        width = sum(e.width + 6 for *_, e in items)
        rot = width > bb.width                       # zu eng: senkrecht wie die Peak-Labels
        if rot:
            for _, t, _ in items:
                t.set_rotation(90)
            items = [(m, t, t.get_window_extent(r)) for m, t, _ in items]
        xs = spread([(self._px(m["lo"])[0] + self._px(m["hi"])[0]) / 2 for m, *_ in items],
                    [e.width + (2 if rot else 6) for *_, e in items], bb.x0, bb.x1)
        hgt = max(e.height for *_, e in items)
        band = 10                                    # Streifen unter ALLEN Labels: nur dort laufen Verbindungen schräg
        yb = ytop - hgt - 2 - band                   # (vorher 3 px direkt an der Schrift: Linien lagen unter Nachbarn)
        for (m, t, e), lx in zip(items, xs):
            t.set_x(lx)
            a, b = sorted((self._px(m["lo"])[0], self._px(m["hi"])[0]))
            c = t.get_color()
            lines = [[(a, yb - 4), (a, yb), (b, yb), (b, yb - 4)]]
            if abs(lx - (a + b) / 2) > 2:                    # verschobenes Label: senkrecht aus dem Label, schräg zur Klammer
                lines.append([(lx, ytop - e.height - 1), (lx, yb + 0.6 * band), ((a + b) / 2, yb)])
            for pts in lines:
                self._add(self.ax.add_line(Line2D(*zip(*pts), transform=IdentityTransform(), lw=0.7, color=c,
                                                  clip_on=False, zorder=5)))
        return hgt + band + 12

    def _integrals_ov(self, r):
        """Integralkurven über den Bereichen; Klammer wie Mnova 9.55 pt unter der Grundlinie (Enden 2.26 pt hoch),
        Strich 1.13 pt zur Zahl, Zahl senkrecht darunter, auseinandergerückt."""
        o = self.opts
        if not self.integrals or not (o["int_curves"] or o["int_values"]):
            return
        ax, bb = self.ax, self.ax.bbox
        tr = ax.get_xaxis_transform()
        base = self._base()
        totals = []
        for it in self.integrals:
            m = (self.x >= it["lo"]) & (self.x <= it["hi"])
            totals.append(float(np.nansum(self.y[m])))
        big = max((abs(v) for v in totals), default=0) or 1.0
        yb = bb.y0 + base * bb.height - self._pt(G["int_off"])
        vals = []
        for i, it in enumerate(self.integrals):
            if not self._in_view((it["lo"] + it["hi"]) / 2):
                continue
            sel = self.selected == ("integrals", i)
            col = C_SEL if sel else o["integral_bracket_color"]
            m = (self.x >= it["lo"]) & (self.x <= it["hi"])
            if o["int_curves"] and m.sum() > 1:
                cum = np.cumsum(np.nan_to_num(self.y[m]))
                self._add(ax.plot(self.x[m], base + 0.02 + 0.25 * cum / big, color=col, lw=1.6 if sel else 1.0,
                                  transform=tr, zorder=4)[0])
            if o["int_values"] and it.get("value") is not None:
                a_, b_ = sorted((self._px(it["lo"])[0], self._px(it["hi"])[0]))
                self._bracket(ax, a_, b_, yb, col)
                vals.append(((max(a_, bb.x0) + min(b_, bb.x1)) / 2, f"{it['value']:.2f}",
                             C_SEL if sel else o["integral_value_color"]))
        self._values(ax, r, yb, vals)

    def _bracket(self, ax, a_, b_, yb, col, lo_px=None, hi_px=None):
        """Klammer von a_ bis b_ (px); Enden senkrecht 2.26 pt, am Rand des sichtbaren Bereichs (lo_px/hi_px)
        abgeschnitten mit Pfeilspitze wie Mnova."""
        e = self._pt(G["int_end"]) / 2
        w = self.opts["integral_bracket_width"]
        lo_px = ax.bbox.x0 if lo_px is None else lo_px
        hi_px = ax.bbox.x1 if hi_px is None else hi_px
        cut_a, cut_b = a_ < lo_px - 0.5, b_ > hi_px + 0.5
        a_, b_ = max(a_, lo_px), min(b_, hi_px)
        self._add(ax.add_line(Line2D([a_, b_], [yb, yb], transform=IdentityTransform(), color=col, lw=w, clip_on=False,
                                     zorder=4)))
        h = self._pt(G["arrow"])
        for x, cut, d in ((a_, cut_a, 1), (b_, cut_b, -1)):
            pts = [(x + d * h, yb + h / 2), (x, yb), (x + d * h, yb - h / 2)] if cut else [(x, yb - e), (x, yb + e)]
            self._add(ax.add_line(Line2D(*zip(*pts), transform=IdentityTransform(), color=col, lw=w, clip_on=False,
                                         zorder=4)))

    def _values(self, ax, r, yb, vals):
        """Integralwerte senkrecht unter der Klammer, auseinandergerückt; Strich von der Klammer zur Zahl."""
        if not vals:
            return
        bb = ax.bbox
        st = self._pt(G["val_lead"])
        texts = [self._text(0, yb - 3 * st - self._pt(G["val_gap"]), s_, r, ax, rotation=90, ha="center", va="top",
                            color=c, fontsize=self.opts["integral_value_size"]) for _, s_, c in vals]
        xs = spread([p for p, _, _ in vals], [self._pt(G["pitch"] * t.get_fontsize()) for t, _ in texts], bb.x0, bb.x1,
                    self._pt(G["join"]))
        for (t, _), lx, (px, _, c) in zip(texts, xs, vals):
            t.set_x(lx)
            self._add(ax.add_line(Line2D([px, px, lx, lx], [yb, yb - st, yb - 2 * st, yb - 3 * st],
                                         transform=IdentityTransform(), color=c, lw=G["stroke"], clip_on=False,
                                         zorder=4)))

    def _base(self):
        """Grundlinie (y = 0) als Anteil der Achsenhöhe, begrenzt auf die Achse."""
        bb = self.ax.bbox
        return min(max((self._px(0, 0)[1] - bb.y0) / bb.height, 0.0), 0.7)

    def _ranges_ov(self):
        """Im Modus Integration/Inset/Multiplett: die Bereiche als Flächen (gewählter kräftiger) zum Greifen."""
        layer = RANGE_LAYER.get(self.mode)
        if layer in (None, "cuts"):
            return
        col = {"integrals": self.opts["integral_bracket_color"], "insets": C_SEL, "multiplets": C_MARK}[layer]
        for i, it in enumerate(getattr(self, layer)):
            sel = self.selected == (layer, i)
            self._add(self.ax.axvspan(it["lo"], it["hi"], color=col, alpha=0.22 if sel else 0.08, lw=0, zorder=1))

    def _gap(self, cuts, lim, width_px):
        """Lücke eines Schnitts in ppm, so dass sie 3 pt breit ist wie in der Vorlage."""
        lo, hi = sorted(lim)
        inside = [c for c in cuts if c["hi"] > lo and c["lo"] < hi]
        vis = (hi - lo) - sum(min(c["hi"], hi) - max(c["lo"], lo) for c in inside)
        g = self._pt(3.0)
        return max(vis, 1e-9) * g / max(width_px - len(inside) * g, 1.0)

    def _spine(self, ax, gaps_px):
        """Achsenlinie mit Lücken (3 pt) an den Brüchen wie Mnova; ohne Bruch die normale Linie."""
        if not gaps_px:
            ax.spines["bottom"].set_visible(True)
            return
        ax.spines["bottom"].set_visible(False)
        bb, h = ax.bbox, self._pt(1.5)
        xs = [bb.x0] + [v for g in sorted(gaps_px) for v in (g - h, g + h)] + [bb.x1]
        for a, b in zip(xs[::2], xs[1::2]):
            self._add(ax.add_line(Line2D([a, b], [bb.y0, bb.y0], transform=IdentityTransform(), lw=G["stroke"],
                                         color=self.opts["axis_color"], clip_on=False, zorder=6)))

    def _break(self, ax, mx, y0, col):
        """Achsenbruch wie Mnova: zwei Schrägstriche je 3 × 3 pt nebeneinander, mittig auf der Lücke der Achse."""
        d = self._pt(3.0)
        for x0 in (mx - d, mx):
            self._add(ax.add_line(Line2D([x0, x0 + d], [y0 - d / 2, y0 + d / 2], transform=IdentityTransform(),
                                         lw=G["stroke"], color=col, clip_on=False, zorder=7)))

    def _cuts_ov(self):
        """Achsenbruch an jedem Schnitt; im Modus X auch die Lücke markiert."""
        tr = self.ax.get_xaxis_transform()
        gaps = []
        for i, c in enumerate(self.cuts):
            if not (min(self.xlim) < c["lo"] < max(self.xlim) or min(self.xlim) < c["hi"] < max(self.xlim)):
                continue
            mx = (self._px(c["lo"])[0] + self._px(c["hi"])[0]) / 2
            gaps.append(mx)
            sel = self.selected == ("cuts", i)
            self._break(self.ax, mx, self.ax.bbox.y0, C_SEL if sel else self.opts["axis_color"])
            if self.mode == "cut":
                self._add(self.ax.axvspan(c["lo"], c["hi"], ymin=0, ymax=1, color="#d9534f",
                                          alpha=0.35 if sel else 0.15, lw=0, zorder=1, transform=tr))
        self._spine(self.ax, gaps)

    def _insets_ov(self):
        """Ausschnitte (E) wie die Vorlage: eigene Labelreihe, Spektrum, Integralklammern 2.8 pt
        über der Grundlinie und Wert, eigene Achse ohne Rahmen; mehrere Teile mit Achsenbruch (Umschalt + Ziehen fügt
        einen Teil an). Größe wie die Vorlage (1/3 der Achse breit, 82.5 pt hoch, Grundlinie 9 pt und höchster Punkt
        52.7 pt über seiner Achse); Platz über dem niedrigsten Teil des Spektrums, unter der Labelreihe."""
        if not self.insets:
            return
        o = self.opts
        bb = self.ax.bbox
        top_f, _ = self._bands()
        r = self.canvas.get_renderer()
        h_f, w_f = min(self._pt(82.5) / bb.height, 0.6), 1 / 3
        y_top = 1 - top_f
        idx = self._visible()
        if not len(idx):
            return
        pts = self.ax.transData.transform(np.column_stack([self.x[idx], self._yplot[idx]]))
        # Hülle der Hindernisse je Pixelspalte (Höhe in px über der Achse): Spektrum mit halber Strichbreite, auch
        # zwischen weit auseinanderliegenden Punkten, und die Marken über den Signalen („*“)
        ncol = int(bb.width) + 1
        env_px = np.zeros(ncol)
        cx = pts[:, 0] - bb.x0
        np.maximum.at(env_px, np.clip(cx.astype(int), 0, ncol - 1), pts[:, 1] - bb.y0)
        o_ = np.argsort(cx)
        env_px = np.fmax(env_px, np.interp(np.arange(ncol) + 0.5, cx[o_], pts[o_, 1] - bb.y0, left=0, right=0))
        env_px += self._pt(o["spectrum_width"]) / 2
        if o["int_curves"] and self.integrals:            # eingeblendete Integralkurven sind Hindernisse
            base = self._base()
            tot = [float(np.nansum(self.y[(self.x >= it["lo"]) & (self.x <= it["hi"])])) for it in self.integrals]
            big = max((abs(v) for v in tot), default=0) or 1.0
            for it, v in zip(self.integrals, tot):
                a_, b_ = sorted(self._px(q)[0] - bb.x0 for q in (it["lo"], it["hi"]))
                a_, b_ = int(max(a_, 0)), int(min(np.ceil(b_), ncol - 1))
                if a_ <= b_:
                    env_px[a_:b_ + 1] = np.maximum(env_px[a_:b_ + 1], (base + 0.02 + 0.25 * abs(v) / big) * bb.height)
        for e in (t.get_window_extent(r) for t in self._mark_texts):
            a_, b_ = int(max(e.x0 - bb.x0, 0)), int(min(np.ceil(e.x1 - bb.x0), ncol - 1))
            if a_ <= b_:
                env_px[a_:b_ + 1] = np.maximum(env_px[a_:b_ + 1], e.y1 - bb.y0)
        # der ganze Ausschnitt hält Abstand: Zahlen der Achse ragen seitlich über die Enden, Striche, Zahlen und
        # Achsentitel hängen unter der Achse (wie in _layout); dazu 2 pt Luft
        fs, air = o["axis_font_size"], self._pt(2.0)
        side = self._pt(0.556 * fs * 2) + air
        below = (self._pt(G["tick"] + 1 + 2 * 1.2 * fs + 1) + air) / bb.height
        taken = [(q["pos"][0], q["pos"][0] + q["pos"][2]) for q in self.insets if q.get("pos")]
        self._inset_boxes = []
        span = float(self.x.max() - self.x.min())
        for k, it in enumerate(self.insets):
            if it.get("pos"):                             # vom Nutzer gezogen: Lage und Größe gespeichert
                x0, y0, w_i, h_i = it["pos"]
            else:
                best = None
                # bis an das rechte Ende der Achse (Zahlen ragen in den Rand): neben einem Signal am rechten Rand
                # reicht der Platz sonst um wenige Pixel nicht
                sb = self._struct_axes()
                own = (self._px((it["lo"] + it["hi"]) / 2)[0] - bb.x0) / bb.width
                for x0 in np.append(np.arange(0.01, 1 - w_f, 0.01), 1 - w_f):
                    if any(x0 < b_ and x0 + w_f > a_ for a_, b_ in taken):
                        continue
                    a_ = max(int(np.floor(x0 * bb.width - side)), 0)
                    env = float(env_px[a_:int(np.ceil((x0 + w_f) * bb.width + side)) + 1].max()) / bb.height
                    # Rangfolge: frei vom Spektrum vor allem (die Strukturstrafe dreht das nie um), dann frei von der
                    # Struktur (echte Box, sonst das linke Drittel), dann möglichst niedriges Spektrum darunter
                    hits = env + below + h_f > y_top + 1e-9
                    left = False
                    if sb is not None:                    # echte Struktur: Überdeckung ist eine Kollision
                        y_lo = min(max(env + 0.57 * (y_top - env) - h_f / 2, env + below), y_top - h_f)
                        hits = hits or (x0 < sb[2] and x0 + w_f > sb[0] and y_lo < sb[3] and y_lo + h_f > sb[1])
                    else:                                 # Struktur folgt erst: linkes Drittel nur nachrangig meiden
                        left = self.struct_left and x0 < STRUCT_FRAC
                    # unter freien Plätzen der nächste zum eigenen Bereich (Mnova zeigt Ausschnitte bei ihrem Signal)
                    score = (hits, left, round(abs(x0 + w_f / 2 - own), 2), env)
                    if best is None or score < best[0]:
                        best = (score, x0, env)
                if best is None:
                    break
                (hits, *_), x0, env = best
                taken.append((x0, x0 + w_f))
                h_i = h_f
                if hits:                                  # kein freier Platz: kleiner (bis halb so hoch), sonst oben
                    h_i = max(0.5 * h_f, y_top - env - below)   # an der Labelreihe und als Hinweis gemeldet
                    if env + below + h_i > y_top + 1e-9:
                        self.notes.append(T("nmrv_inset_nofree"))
                # senkrecht im freien Band zwischen Spektrum (in seiner Breite) und Labelreihe, Mitte bei 57 % (Mnova-
                # Vorgabe, dort von Hand gesetzt), nie auf dem Spektrum (auch nicht mit Zahlen und Achsentitel)
                y0 = min(max(env + 0.57 * (y_top - env) - h_i / 2, env + below), y_top - h_i)
                w_i = w_f
            parts = sorted(it.get("parts") or [{"lo": it["lo"], "hi": it["hi"]}], key=lambda q: -q["hi"])
            lo, hi = min(q["lo"] for q in parts), max(q["hi"] for q in parts)
            gaps = [{"lo": b_["hi"], "hi": a_["lo"]} for a_, b_ in zip(parts, parts[1:]) if b_["hi"] < a_["lo"]]
            W, H = self.fig.bbox.width, self.fig.bbox.height
            ia = self.fig.add_axes([(bb.x0 + x0 * bb.width) / W, (bb.y0 + y0 * bb.height) / H, w_i * bb.width / W,
                                    h_i * bb.height / H], zorder=3)
            ia.set_facecolor("white")                     # deckt Linien des Hauptspektrums ab
            self._insets_ax.append(ia)
            self._inset_boxes.append((k, ia))
            xs_, ys_ = [], []                             # nur die Teile zeichnen, getrennt durch NaN
            for q in parts:
                m = (self.x >= q["lo"]) & (self.x <= q["hi"])
                xs_ += [self.x[m], [np.nan]]
                ys_ += [self._yplot[m], [np.nan]]
            xv, yv = np.concatenate(xs_), np.concatenate(ys_)
            ia.plot(xv, yv, color=o["spectrum_color"], lw=o["spectrum_width"])
            fwd, inv = cut_functions(gaps, float(self.x.min()), float(self.x.max()),
                                     self._gap(gaps, (hi, lo), w_i * bb.width))
            ia.set_xscale("function", functions=(fwd, inv))
            ia.set_xlim(hi, lo)
            ih = max(h_i * bb.height, 1.0)
            # eigene Intensität: gespeichert (Mausrad über dem Ausschnitt) oder höchstes Signal ohne Lösungsmittel
            sv = np.ones(len(xv), bool)
            for s_ in self.solvents:
                sv &= ~(np.abs(xv - s_["x"]) < 0.003 * span)
            ok = np.isfinite(yv) & sv
            top = it.get("ymax") or (float(np.nanmax(yv[ok])) if ok.any() else
                                     (float(np.nanmax(yv)) if np.isfinite(yv).any() else 1.0))
            b0, b1 = self._pt(9.0) / ih, self._pt(52.7) / ih             # Grundlinie, höchster Punkt (Anteil)
            rng = top / max(b1 - b0, 0.05)
            ia.set_ylim(-b0 * rng, -b0 * rng + rng)
            ia._top = top
            self._style_axis(ia, gaps)
            ibb = ia.bbox
            gx_ = [ia.transData.transform((inv((fwd(np.array([g_["lo"]])) + fwd(np.array([g_["hi"]]))) / 2)[0], 0))[0]
                   for g_ in gaps]
            for gx in gx_:
                self._break(ia, gx, ibb.y0, o["axis_color"])
            self._spine(ia, gx_)
            if it.get("labels", True):                    # Labelreihe im Ausschnitt (Mnova: je Ausschnitt schaltbar)
                self._label_row(ia, r, 0.0, self._row_items(parts), spans=[(q["lo"], q["hi"]) for q in parts])
            yb = ibb.y0 + self._pt(9.0 + G["inset_int"])
            vals = []
            for jt in self.integrals:
                part = next((q for q in parts if q["lo"] <= (jt["lo"] + jt["hi"]) / 2 <= q["hi"]), None)
                if not o["int_values"] or jt.get("value") is None or part is None:
                    continue
                a_, b_ = sorted(ia.transData.transform([(jt["lo"], 0), (jt["hi"], 0)])[:, 0])
                pa, pb = sorted(ia.transData.transform([(part["lo"], 0), (part["hi"], 0)])[:, 0])
                self._bracket(ia, a_, b_, yb, o["integral_bracket_color"], pa, pb)
                vals.append(((max(a_, pa) + min(b_, pb)) / 2, f"{jt['value']:.2f}", o["integral_value_color"]))
            self._values(ia, r, yb, vals)

    def _struct_axes(self):
        """Strukturbox (Bildanteile x0, y0, x1, y1, y nach oben) als Anteile der Achse, sonst None."""
        if self.struct_box is None:
            return None
        F, bb = self.fig.bbox, self.ax.bbox
        x0, y0, x1, y1 = self.struct_box
        return ((x0 * F.width - bb.x0) / bb.width, (y0 * F.height - bb.y0) / bb.height,
                (x1 * F.width - bb.x0) / bb.width, (y1 * F.height - bb.y0) / bb.height)

    def _marks_ov(self):
        """Drehpunkt der Phase, die Klicks des Fadenkreuzes und die Linien eines Musterfits (nur am Bildschirm)."""
        tr = self.ax.get_xaxis_transform()
        if not self.screen:
            return
        for f in self.fit_lines:
            if self._in_view(f["x"]):
                px, py = self._px(f["x"], self._ytop(f["x"]))
                lo = py + self._pt(1.5)
                self._add(self.ax.add_line(Line2D([px, px], [lo, lo + self._pt(6)], transform=IdentityTransform(),
                                                  color="#2e9e4f" if f.get("ok") else C_MARK, lw=1.4, clip_on=False,
                                                  zorder=7)))
        if self.mode == "phase" and self.pivot is not None:
            self._add(self.ax.plot([self.pivot] * 2, [0, 1], transform=tr, color=C_MARK, lw=1.0, ls="--", zorder=6)[0])
        if self.mode == "cursor":
            for x in self.measure:
                self._add(self.ax.plot([x] * 2, [0, 1], transform=tr, color=C_SEL, lw=0.8, ls=":", zorder=6)[0])

    def _marks_text(self):
        """Marken wie die Vorlage („*“ über H2O): Text 6.5 pt schwarz, unten auf der Spitze des Signals."""
        o = self.opts
        self._mark_texts = []                                # Hindernisse für die Lage der Ausschnitte
        for i, m in enumerate(self.marks):
            if self._in_view(m["x"]):
                px, py = self._px(m["x"], self._ytop(m["x"]))
                py = min(py, self.ax.bbox.y1 - self._pt(1.2 * o["mark_size"]))      # abgeschnittenes Signal: im Bild
                self._mark_texts.append(self._text(px, py, m.get("text") or o["mark_symbol"], ha="center", va="bottom",
                                        color=C_SEL if self.selected == ("marks", i) else o["mark_color"],
                                        fontsize=o["mark_size"])[0])

    def _hit_mark(self, px):
        tol = HIT_PX * self._ratio()
        best = None
        for i, m in enumerate(self.marks):
            d = abs(self._px(m["x"])[0] - px)
            if d <= tol and (best is None or d < best[1]):
                best = (i, d)
        return best and best[0]

    def _sync_delete(self):
        self.btn_delete.setEnabled(self.selected is not None)

    # -- Maus ----------------------------------------------------------------------------------------------------------
    def _on_draw(self, _ev):
        self._bg = self.canvas.copy_from_bbox(self.fig.bbox)

    def _blit(self, artists):
        if self._bg is None:
            self.canvas.draw_idle()
            return
        self.canvas.restore_region(self._bg)
        for a in artists:
            self.ax.draw_artist(a)
        self.canvas.blit(self.fig.bbox)

    def _inside(self, ev):
        return ev.x is not None and self.ax.bbox.contains(ev.x, ev.y)

    def _data(self, px, py):
        bb = self.ax.bbox
        px, py = min(max(px, bb.x0), bb.x1), min(max(py, bb.y0), bb.y1)
        return self.ax.transData.inverted().transform((px, py))

    def _hit_range(self, layer, px):
        """-> (Index, „lo“|„hi“|„in“) des Bereichs unter px; zuerst der gewählte."""
        items = getattr(self, layer)
        order = list(range(len(items)))
        if self.selected and self.selected[0] == layer:
            order.insert(0, order.pop(self.selected[1]))
        tol = (HIT_PX if layer == "cuts" else EDGE_PX) * self._ratio()
        for i in order:
            a, b = self._px(items[i]["hi"])[0], self._px(items[i]["lo"])[0]      # hi links (ppm absteigend)
            if layer != "cuts":
                if abs(px - a) <= tol:
                    return i, "hi"
                if abs(px - b) <= tol:
                    return i, "lo"
            if a - (tol if layer == "cuts" else 0) <= px <= b + (tol if layer == "cuts" else 0):
                return i, "in"
        return None

    def _hit_peak(self, px):
        tol = HIT_PX * self._ratio()
        best = None
        for i, p in enumerate(self.peaks):
            d = abs(self._px(p["x"])[0] - px)
            if d <= tol and (best is None or d < best[1]):
                best = (i, d)
        return best and best[0]

    def _press(self, ev):
        if not self._inside(ev) or self.x is None:
            return
        self.canvas.setFocus()
        if ev.dblclick:
            self._cancel_drag()
            if ev.button == 1 and self.mode in ("pointer", "zoom", "pan"):
                self.full_view()
            return                                       # zweiter Klick eines Doppelklicks: kein zweiter Treffer
        d = self.drag = dict(x0=ev.x, y0=ev.y, button=ev.button, moved=False, kind=None)
        m = self.mode
        if m == "zoom" and ev.button == 1:
            d["kind"] = "zoom"
        elif m == "pan":
            d.update(kind="pan", inv=self.ax.transData.inverted().frozen(), lim=(self.xlim, self.ylim))
        elif m == "inset" and ev.button == 1 and self._hit_inset(ev) is not None:
            k, ia, corner = self._hit_inset(ev)          # Ausschnitt ziehen (Lage) oder an der Ecke unten rechts (Größe)
            self.selected = ("insets", k)
            d.update(kind="inset_size" if corner else "inset_pos", i=k, pos0=self._inset_pos(ia))
            CANVAS.moving(self.canvas, True)
        elif m == "cut" and ev.button == 1 and self._hit_inset(ev) is not None:
            k, ia, _ = self._hit_inset(ev)               # X im Ausschnitt: Bereich aus dem Ausschnitt schneiden (Mnova),
            # ohne ihn zu wählen (Entf danach löschte sonst den ganzen Ausschnitt)
            d.update(kind="inset_cut", i=k, ia=ia)
        elif m in RANGE_LAYER and ev.button == 1:
            layer = RANGE_LAYER[m]
            hit = self._hit_range(layer, ev.x)
            if hit is not None:
                i, part = hit
                self.selected = (layer, i)
                fixed = layer == "cuts" or len(getattr(self, layer)[i].get("parts") or ()) > 1
                d.update(kind="select" if fixed else ("move" if part == "in" else "resize"), layer=layer, i=i,
                         part=part, orig=dict(getattr(self, layer)[i]), x0d=self._data(ev.x, ev.y)[0])
                self.redraw()
            else:
                d["kind"] = "new"
        elif m == "peaks" and ev.button == 1:
            i = self._hit_peak(ev.x)
            d.update(kind="new") if i is None else d.update(kind="pick", i=i)
        elif m == "mark" and ev.button == 1:
            i = self._hit_mark(ev.x)
            if i is None:
                d["kind"] = "markadd"
            else:
                self.selected = ("marks", i)
                d.update(kind="markmove", i=i)
                self.redraw()
        elif m in ("reference", "cursor") and ev.button == 1:
            d["kind"] = "click"
        elif m == "phase" and ev.button in (1, 3):
            d.update(kind="phase", ph=(self.ph0, self.ph1),
                     fine=bool({"ctrl", "control", "cmd"} & set(getattr(ev, "modifiers", None) or ())) or
                     "control" in (ev.key or "") or "ctrl" in (ev.key or ""))
        if d["kind"] is None:
            self.drag = None
        elif d["kind"] in ("zoom", "new", "move", "resize", "pan", "phase", "inset_cut"):
            CANVAS.moving(self.canvas, True)

    def _rubber_artists(self, ev):
        """Rahmen beim Aufziehen (nur geblittet, nie Teil des Bildes) und bei K/J die Schwelle an der Mausposition."""
        d = self.drag
        bb = (d.get("ia") or self.ax).bbox                # Schnitt im Ausschnitt: Rahmen in dessen Achse
        x0, x1 = sorted((d["x0"], min(max(ev.x, bb.x0), bb.x1)))
        y0, y1 = sorted((d["y0"], min(max(ev.y, bb.y0), bb.y1)))
        if self.mode == "zoom":
            if self.zoom_kind == "h":
                y0, y1 = bb.y0, bb.y1
            elif self.zoom_kind == "v":
                x0, x1 = bb.x0, bb.x1
        else:
            y0, y1 = bb.y0, bb.y1
        col = self.opts["integral_bracket_color"] if self.mode == "integral" else C_SEL
        out = [Rectangle((x0, y0), x1 - x0, y1 - y0, transform=IdentityTransform(), fc=col, alpha=0.12, ec=col,
                         lw=0.8, ls="--", animated=True, zorder=10)]
        if self.mode in ("peaks", "multiplet"):
            yt = min(max(ev.y, bb.y0), bb.y1)
            out.append(Line2D([x0, x1], [yt, yt], transform=IdentityTransform(), color=C_MARK, lw=1.0, ls="--",
                              animated=True, zorder=10))
        for a in out:
            a.set_figure(self.fig)
            a.axes = self.ax
        return out

    def _move(self, ev):
        if self.x is None:
            return
        if self._inside(ev):
            xd, yd = self._data(ev.x, ev.y)
            self.lbl_read.setText(self.readout(xd))
            if self.mode == "cursor" and self.drag is None:
                self._crosshair(ev)
        d = self.drag
        if d is None or ev.x is None:
            return
        if not d["moved"] and math.hypot(ev.x - d["x0"], ev.y - d["y0"]) < CLICK_PX:
            return
        d["moved"] = True
        if d["kind"] == "pick":                          # K: Ziehen ab einem Peak ist ein neuer Bereich, kein Klick
            d["kind"] = "new"
            CANVAS.moving(self.canvas, True)
        k = d["kind"]
        if k in ("zoom", "new", "inset_cut"):
            self._rubber = self._rubber_artists(ev)
            self._blit(self._rubber)
        elif k == "pan":
            inv, (xl, yl) = d["inv"], d["lim"]
            dx = 0 if self.pan_kind == "v" else ev.x - d["x0"]
            dy = 0 if self.pan_kind == "h" else ev.y - d["y0"]
            bb = self.ax.bbox
            l_, b_ = inv.transform((bb.x0 - dx, bb.y0 - dy))
            r_, t_ = inv.transform((bb.x1 - dx, bb.y1 - dy))
            # die gesperrte Richtung behält ihre Grenzen exakt (keine Rundung über die Rücktransformation)
            self.xlim = xl if self.pan_kind == "v" else (float(l_), float(r_))
            self.ylim = yl if self.pan_kind == "h" else (float(b_), float(t_))
            self._fast_view()
        elif k in ("inset_pos", "inset_size"):
            bb = self.ax.bbox
            x0, y0, w, h = d["pos0"]
            fx, fy = (ev.x - d["x0"]) / bb.width, (ev.y - d["y0"]) / bb.height
            if k == "inset_pos":
                x0, y0 = min(max(x0 + fx, 0.0), 1 - w), min(max(y0 + fy, 0.0), 1 - h)
            else:                                        # Ecke unten rechts: Breite nach rechts, Höhe nach unten
                w, nh = max(0.1, min(w + fx, 1 - x0)), max(0.08, min(h - fy, y0 + h))
                y0, h = y0 + h - nh, nh
            self.insets[d["i"]]["pos"] = [x0, y0, w, h]
            self.redraw()
        elif k in ("move", "resize"):
            it, o = getattr(self, d["layer"])[d["i"]], d["orig"]
            xd = self._data(ev.x, ev.y)[0]
            if k == "move":
                it["lo"], it["hi"] = o["lo"] + xd - d["x0d"], o["hi"] + xd - d["x0d"]
            else:
                it[d["part"]] = xd
                if it["lo"] > it["hi"]:
                    it["lo"], it["hi"] = it["hi"], it["lo"]
                    d["part"] = "lo" if d["part"] == "hi" else "hi"
            self.redraw()
        elif k == "phase":
            f = FINE if d["fine"] else 1.0
            dy = ev.y - d["y0"]
            ph0, ph1 = d["ph"]
            if d["button"] == 1:
                self.ph0 = ph0 + dy * PH0_DEG_PX * f
            else:
                self.ph1 = ph1 + dy * PH1_DEG_PX * f
            self._phase_apply(fast=True)

    def _crosshair(self, ev):
        bb = self.ax.bbox
        self._cross = [Line2D([ev.x, ev.x], [bb.y0, bb.y1], transform=IdentityTransform(), color=C_SEL, lw=0.6,
                              animated=True), Line2D([bb.x0, bb.x1], [ev.y, ev.y], transform=IdentityTransform(),
                                                     color=C_SEL, lw=0.6, animated=True)]
        for a in self._cross:
            a.set_figure(self.fig)
            a.axes = self.ax
        self._blit(self._cross)

    def _leave(self, _ev):
        self.lbl_read.setText(self.readout(None))
        if self._cross:
            self._cross = []
            self._blit([])

    def readout(self, xd):
        """Statuszeile rechts: δ unter der Maus; Fadenkreuz: die beiden Klicks und ihr Abstand (Hz nur mit SF)."""
        parts = [] if xd is None else [f"δ: {xd:.3f} ppm"]           # δ steil (keine Formelregel „δ [“)
        if self.mode == "cursor" and self.measure:
            parts = ["δ: " + " – ".join(f"{v:.3f}" for v in self.measure) + " ppm"]
            if len(self.measure) == 2:
                d = abs(self.measure[0] - self.measure[1])
                parts.append(f"J = {d * self.sf:.1f} Hz" if self.sf else T("nmrv_dist_ppm", d=f"{d:.4f}"))
        if self.mode == "phase":
            parts.append(T("nmrv_phase_read", ph0=f"{self.ph0:.1f}", ph1=f"{self.ph1:.1f}"))
        return " · ".join(parts)

    def _phase_apply(self, fast=False):
        """Phase melden und (über den Rückruf) neu rechnen. fast: während des Ziehens nur die Linie blitten (Hintergrund
        beim ersten Schritt gemerkt), alles andere zeichnet das Loslassen neu."""
        self.phase_changed.emit(float(self.ph0), float(self.ph1), float(self.pivot if self.pivot is not None else 0.0))
        if self.phase_cb is not None:
            y = self.phase_cb(self.ph0, self.ph1, self.pivot)
            if y is not None:
                self.y = np.asarray(y, float)
                self._mask()
        self.lbl_read.setText(self.readout(None))
        if not fast:
            self._end_fast()
            self.redraw()
            return
        c = self.canvas
        if self._fast != "phase":
            self._fast = "phase"
            self.line.set_animated(True)
            c.draw()
            self._fast_bg = c.copy_from_bbox(self.fig.bbox)
        self.line.set_ydata(self._yplot)
        c.restore_region(self._fast_bg)
        self.ax.draw_artist(self.line)
        c.blit(self.fig.bbox)

    def _fast_view(self):
        """Verschieben: nur Grenzen setzen und Spektrum + Achse zeichnen; Labels, Klammern und Ausschnitte sind bis zum
        Loslassen verborgen (das volle Neuzeichnen kostete bei 262k Punkten ~120 ms je Mausbewegung)."""
        if self._fast != "pan":
            self._fast = "pan"
            for a in self._ov + self._insets_ax:
                a.set_visible(False)
            CANVAS.moving(self.canvas, True)
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)
        self.canvas.draw_idle()

    def _end_fast(self):
        if self._fast == "phase":
            self.line.set_animated(False)
        self._fast = None

    def snap_peak(self, xd, px_tol=8):
        """Peakspitze nahe xd: größter Punkt innerhalb ±px_tol Pixel (Mnova rastet ebenso auf die Spitze)."""
        cx = self._px(xd)[0]
        a = self.ax.transData.inverted().transform((cx - px_tol * self._ratio(), 0))[0]
        b = self.ax.transData.inverted().transform((cx + px_tol * self._ratio(), 0))[0]
        m = np.flatnonzero((self.x >= min(a, b)) & (self.x <= max(a, b)) & np.isfinite(self._yplot))
        if not len(m):
            return float(xd)
        return float(self.x[m[int(np.argmax(self._yplot[m]))]])

    def _release(self, ev):
        d = self.drag
        if d is None:
            return
        self.drag = None
        CANVAS.moving(self.canvas, False)
        if self._fast:                                   # Verschieben/Phase: jetzt alles neu zeichnen
            self._end_fast()
            if d["kind"] == "phase":
                self.redraw()
        had_rubber, self._rubber = bool(self._rubber), []
        k = d["kind"]
        px = d["x0"] if ev.x is None else ev.x
        py = d["y0"] if ev.y is None else ev.y
        if not d["moved"]:
            shift = "shift" in set(getattr(ev, "modifiers", None) or ()) or "shift" in (ev.key or "")
            if k == "new" and self.mode == "peaks":
                # einzelner Peak (Schulter): Klick ins Leere, rastet auf ±3 px; mit Umschalt genau an der Mausposition
                xd = float(self._data(d["x0"], d["y0"])[0])
                self.peaks.append({"x": xd if shift else self.snap_peak(xd, 3)})
                self.peaks.sort(key=lambda q: -q["x"])
                self._emit("peaks")
            elif k == "new":
                self.selected = None
            elif k == "markadd":
                x = self.snap_peak(float(self._data(d["x0"], d["y0"])[0]))
                self.marks.append({"x": x, "text": self.opts["mark_symbol"]})
                self.selected = ("marks", len(self.marks) - 1)
                self._emit("marks")
            elif k == "pick":
                self.selected = None if self.selected == ("peaks", d["i"]) else ("peaks", d["i"])
            elif k == "click":
                xd = self._data(d["x0"], d["y0"])[0]
                if self.mode == "reference":
                    x = self.snap_peak(xd)
                    self.lbl_hint.setText(T("nmrv_ref_done", x=f"{x:.3f}"))
                    self.reference_clicked.emit(x)
                else:
                    self.measure = [xd] if len(self.measure) != 1 else self.measure + [xd]
                    self.lbl_read.setText(self.readout(None))
                    if len(self.measure) == 2:
                        a, b = self.measure
                        self.distance_measured.emit(float(a), float(b), abs(a - b) * self.sf if self.sf else None)
            elif k == "phase" and d["button"] == 1:
                self.pivot = float(self._data(d["x0"], d["y0"])[0])
                self.phase_changed.emit(float(self.ph0), float(self.ph1), self.pivot)
            self.redraw()
            return
        if k == "inset_cut":                             # Teile des Ausschnitts in ppm seiner eigenen Skala
            ia = d["ia"]
            b = ia.bbox
            inv = ia.transData.inverted()
            lo, hi = sorted(float(inv.transform((min(max(v, b.x0), b.x1), b.y0))[0]) for v in (d["x0"], px))
            w2 = abs(float(inv.transform((b.x0 + CLICK_PX, 0))[0] - inv.transform((b.x0, 0))[0]))   # Reste < 4 px: weg
            if abs(min(max(px, b.x0), b.x1) - d["x0"]) >= CLICK_PX and self.cut_inset(d["i"], lo, hi, w2):
                self._emit("insets")
            self.redraw()
            return
        (x0d, y0d), (x1d, y1d) = self._data(d["x0"], d["y0"]), self._data(px, py)
        lo, hi = sorted((float(x0d), float(x1d)))
        bb = self.ax.bbox
        wide = abs(min(max(px, bb.x0), bb.x1) - d["x0"]) >= CLICK_PX
        tall = abs(min(max(py, bb.y0), bb.y1) - d["y0"]) >= CLICK_PX
        if (k == "zoom" and not {"h": wide, "v": tall, "box": wide and tall}[self.zoom_kind]) or (k == "new" and not wide):
            self.redraw()                                # ohne Ausdehnung in der Richtung des Modus: nichts (Grenzen
            return                                       # gleich = leere Ansicht, Bereich ohne Breite)
        if k == "zoom":
            xl = (hi, lo) if self.zoom_kind != "v" else self.xlim
            yl = tuple(sorted((float(y0d), float(y1d)))) if self.zoom_kind != "h" else self.ylim
            self.set_view(xl, yl)
        elif k == "pan":
            self.set_view(self.xlim, self.ylim)
        elif k == "new":
            m = self.mode
            if m == "integral":
                self.integrals.append({"lo": lo, "hi": hi})
                self.selected = ("integrals", len(self.integrals) - 1)
                self._emit("integrals")
            elif m == "cut":
                self.cuts = merge_ranges(self.cuts + [{"lo": lo, "hi": hi}])
                self.selected = None                         # Indizes haben sich verschoben (Verschmelzen)
                self._mask()
                self._emit("cuts")
            elif m == "inset":
                if self.insets and ("shift" in set(getattr(ev, "modifiers", None) or ()) or "shift" in (ev.key or "")):
                    last = self.insets[-1]                   # Umschalt: weiterer Teil desselben Ausschnitts („//“)
                    parts = last.get("parts") or [{"lo": last["lo"], "hi": last["hi"]}]
                    parts.append({"lo": lo, "hi": hi})
                    last.update(parts=parts, lo=min(q["lo"] for q in parts), hi=max(q["hi"] for q in parts))
                else:
                    self.insets.append({"lo": lo, "hi": hi})
                self._emit("insets")
            elif m == "peaks":
                self.peak_pick_requested.emit(lo, hi, float(y1d))
            elif m == "multiplet":
                self.multiplet_requested.emit(lo, hi, float(y1d))
            self.redraw()
        elif k in ("move", "resize"):
            self._emit(d["layer"])
            self.redraw()
        elif k in ("inset_pos", "inset_size"):
            self._emit("insets")
            self.redraw()
        elif k == "markmove":                            # Marke gezogen: auf die Spitze am neuen Ort
            self.marks[d["i"]]["x"] = self.snap_peak(float(x1d))
            self._emit("marks")
            self.redraw()
        elif had_rubber:
            self.redraw()

    def cut_inset(self, k, lo, hi, min_w=1e-9):
        """Bereich lo–hi (ppm) aus Ausschnitt k herausschneiden: getroffene Teile werden gekürzt oder geteilt, die Lücken
        zeichnet der Ausschnitt mit „//“ (Mnova: E, dann X im Ausschnitt); Reste schmaler als min_w (ppm) fallen weg. Bliebe
        nichts übrig: nichts ändern (Entf löscht den Ausschnitt). -> geändert?"""
        it = self.insets[k]
        parts = it.get("parts") or [{"lo": it["lo"], "hi": it["hi"]}]
        out = []
        for q in parts:
            if hi <= q["lo"] or lo >= q["hi"]:
                out.append(dict(q))
                continue
            out += [dict(q, hi=lo)] if lo - q["lo"] > min_w else []
            out += [dict(q, lo=hi)] if q["hi"] - hi > min_w else []
        if not out or out == parts:
            return False
        out.sort(key=lambda q: -q["hi"])
        it.update(parts=out, lo=min(q["lo"] for q in out), hi=max(q["hi"] for q in out))
        return True

    def _cancel_drag(self, revert=False):
        d, self.drag = self.drag, None
        CANVAS.moving(self.canvas, False)
        self._end_fast()
        self._rubber = []
        if d is None or not revert:
            return
        if d["kind"] == "pan":
            self.xlim, self.ylim = d["lim"]
        elif d["kind"] in ("move", "resize"):
            getattr(self, d["layer"])[d["i"]].update(d["orig"])
        elif d["kind"] == "phase":
            self.ph0, self.ph1 = d["ph"]
            self._phase_apply()

    def _scroll(self, ev):
        hit = self._hit_inset(ev) if ev.x is not None else None
        if hit is not None:                              # Mausrad über einem Ausschnitt: seine eigene Intensität
            k, ia, _ = hit
            self.insets[k]["ymax"] = ia._top / WHEEL ** ev.step
            self.redraw()
            self._emit("insets")
        elif self._inside(ev) and self.ylim is not None:
            self.intensity(ev.step)

    def _hit_inset(self, ev):
        """-> (Index, Achse, an der Ecke unten rechts) des Ausschnitts unter der Maus oder None."""
        for k, ia in reversed(self._inset_boxes):
            b = ia.bbox
            if b.x0 <= ev.x <= b.x1 and b.y0 - self._pt(15) <= ev.y <= b.y1:   # mit Achse und Zahlen darunter
                tol = 8 * self._ratio()
                return k, ia, abs(ev.x - b.x1) <= tol and abs(ev.y - b.y0) <= tol
        return None

    def _inset_pos(self, ia):
        bb, b = self.ax.bbox, ia.bbox
        return [(b.x0 - bb.x0) / bb.width, (b.y0 - bb.y0) / bb.height, b.width / bb.width, b.height / bb.height]


class NMR2DView(QWidget):
    """2D-Spektrum: Höhenlinien mit Vorzeichen (positiv/negativ getrennte Farben), Projektionen oben (F2) und links (F1),
    Zoom per Rechteck (ziehen), Doppelklick = ganzes Spektrum, Mausrad = Schwelle der untersten Linie. Rechnet nichts:
    Matrix und Achsen (ppm, absteigend wie 2rr) kommen herein. `export_svg` zeichnet dieselbe Ansicht für die SI."""

    levels_changed = Signal(float)
    view_changed = Signal(tuple, tuple)                     # Zoom (xlim, ylim), auch Doppelklick

    POS, NEG = "#1f4fbf", "#c0392b"                         # positiv blau, negativ rot (Vorzeichen editierter HSQC)
    N_LEVELS, STEP = 10, 1.4                                # Linien geometrisch ab der Schwelle (wie TopSpin/Mnova)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = self.ax2 = self.ax1 = None
        self.nuc2 = self.nuc1 = ""
        self.level = None                                   # unterste Linie (Absolutwert); None = 6σ des Rauschens
        self.xlim = self.ylim = None
        self.cfg = core.deep_merge(core.DEFAULTS, {})
        self.cfg["font_size"] = 11.0
        self.fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.host = _Host(self.canvas, self.fig, page=True)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.host, 1)
        self._press_xy = None
        for name, fn in (("button_press_event", self._press), ("button_release_event", self._release),
                         ("scroll_event", self._scroll), ("resize_event", lambda _e: self.redraw())):
            self.canvas.mpl_connect(name, fn)

    def set_data(self, data, ax2, ax1, nuc2="", nuc1="", level=None):
        same = self.data is not None and self.data.shape == np.shape(data)
        self.data, self.ax2, self.ax1 = np.asarray(data, float), np.asarray(ax2, float), np.asarray(ax1, float)
        self.nuc2, self.nuc1, self.level = nuc2, nuc1, level
        if not same or self.xlim is None:
            self.xlim = (float(self.ax2.max()), float(self.ax2.min()))
            self.ylim = (float(self.ax1.max()), float(self.ax1.min()))
        self.redraw()

    def noise(self):
        """Rauschen als Median der Beträge (robust gegen die Signale)."""
        return float(np.median(np.abs(self.data))) * 1.4826 or 1.0

    def base_level(self):
        """Unterste Linie: gewählt (Mausrad) oder 6σ, mindestens 3 % des Maximums (sonst füllen Abschneide-Wellen
        rauscharmer Sätze das Bild)."""
        return self.level if self.level else max(6.0 * self.noise(), 0.03 * float(np.abs(self.data).max()))

    def levels(self):
        b = self.base_level()
        top = float(np.abs(self.data).max())
        lv = [b * self.STEP ** k for k in range(self.N_LEVELS) if b * self.STEP ** k < top] or [b]
        return lv

    def _label(self, nuc):
        return nucleus_axis_label(nuc)

    def _view(self):
        """Ausschnitt der Matrix im sichtbaren Bereich, höchstens ~800 × 800 Punkte (Betragsmaximum je Block, damit
        keine Spitze verschwindet)."""
        (x0, x1), (y0, y1) = sorted(self.xlim), sorted(self.ylim)
        c = np.flatnonzero((self.ax2 >= x0) & (self.ax2 <= x1))
        r = np.flatnonzero((self.ax1 >= y0) & (self.ax1 <= y1))
        if c.size < 2 or r.size < 2:
            return None
        d = self.data[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
        f1, f2 = max(1, d.shape[0] // 800), max(1, d.shape[1] // 800)
        if f1 > 1 or f2 > 1:
            n1, n2 = d.shape[0] // f1 * f1, d.shape[1] // f2 * f2
            b = d[:n1, :n2].reshape(n1 // f1, f1, n2 // f2, f2).transpose(0, 2, 1, 3).reshape(n1 // f1, n2 // f2, -1)
            d = np.take_along_axis(b, np.abs(b).argmax(2)[..., None], 2)[..., 0]
        return d, self.ax2[c[0]:c[-1] + 1:f2][:d.shape[1]], self.ax1[r[0]:r[-1] + 1:f1][:d.shape[0]]

    def redraw(self, fig=None):
        fig = fig or self.fig
        fig.clear()
        if self.data is None:
            self.canvas.draw_idle()
            return
        core.setup_fonts(plt, self.cfg)
        fs = 7.0
        gs = fig.add_gridspec(2, 2, width_ratios=(1, 7), height_ratios=(1, 6), left=0.04, right=0.9, bottom=0.12,
                              top=0.97, wspace=0.0, hspace=0.0)
        ax = fig.add_subplot(gs[1, 1])
        top = fig.add_subplot(gs[0, 1], sharex=ax)
        left = fig.add_subplot(gs[1, 0], sharey=ax)
        v = self._view()
        if v is not None:
            d, x, y = v
            lv = self.levels()
            ax.contour(x, y, d, levels=lv, colors=self.POS, linewidths=0.5)
            ax.contour(x, y, d, levels=[-q for q in reversed(lv)], colors=self.NEG, linewidths=0.5)
            top.plot(x, d.max(0), color="#000000", lw=0.5)         # Projektion = Maximum je Spalte (positiv)
            left.plot(d.max(1), y, color="#000000", lw=0.5)
        ax.set_xlim(*self.xlim)
        ax.set_ylim(*self.ylim)
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.set_xlabel(self._label(self.nuc2), fontsize=fs)
        ax.set_ylabel(self._label(self.nuc1), fontsize=fs)
        ax.tick_params(labelsize=fs, width=0.5, length=2.5)
        for a in (top, left):
            a.axis("off")
        for sp in ax.spines.values():
            sp.set_linewidth(0.5)
        self.ax = ax
        if fig is self.fig:
            self.canvas.draw_idle()

    def export_svg(self, path, w_cm=16.0, h_cm=11.0):
        """Dieselbe Ansicht als SVG für die SI (eigene Figure, weißer Grund)."""
        f = MplFigure(figsize=(w_cm / 2.54, h_cm / 2.54), dpi=72)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(f)
        self.redraw(f)
        import matplotlib
        with matplotlib.rc_context({"svg.fonttype": "path"}):       # Text als Pfade wie alle SVG-Exporte
            f.savefig(path, format="svg", dpi=72, facecolor="white")
        return path

    def full_view(self):
        if self.data is not None:
            self.xlim = (float(self.ax2.max()), float(self.ax2.min()))
            self.ylim = (float(self.ax1.max()), float(self.ax1.min()))
            self.redraw()
            self.view_changed.emit(self.xlim, self.ylim)

    def _press(self, ev):
        if self.data is None or ev.inaxes is not getattr(self, "ax", None):
            return
        if ev.dblclick:
            return self.full_view()
        self._press_xy = (ev.xdata, ev.ydata)

    def _release(self, ev):
        p, self._press_xy = self._press_xy, None
        if p is None or ev.xdata is None or ev.inaxes is not getattr(self, "ax", None):
            return
        if abs(ev.xdata - p[0]) > 1e-6 and abs(ev.ydata - p[1]) > 1e-6:      # Rechteck aufgezogen: Zoom
            self.xlim = (max(p[0], ev.xdata), min(p[0], ev.xdata))
            self.ylim = (max(p[1], ev.ydata), min(p[1], ev.ydata))
            self.redraw()
            self.view_changed.emit(self.xlim, self.ylim)

    def _scroll(self, ev):
        """Mausrad: unterste Höhenlinie höher/tiefer (wie die Intensität in Mnova)."""
        if self.data is None:
            return
        self.level = self.base_level() * (1.25 ** -ev.step)
        self.redraw()
        self.levels_changed.emit(float(self.level))


def make_test_spectrum(n=65536, sf=500.13):
    """Erfundenes ¹H-Spektrum (keine Messdaten): Dublett, Triplett, Quartett, Singuletts, Restsignal CHCl3 und Wasser,
    Lorentz-Linien mit 1 Hz, leichtes Rauschen. -> dict(x, y, sf, integrals, peaks, multiplets, solvents)."""
    x = np.linspace(11.0, -0.5, n)
    rng = np.random.default_rng(7)
    lw = 1.0 / sf                                           # 1 Hz in ppm
    y = rng.normal(0, 0.002, n)
    mults = [(7.81, "d", [8.4], 2), (7.43, "t", [7.6], 2), (7.31, "t", [7.4], 1), (4.13, "q", [7.1], 2),
             (3.86, "s", [], 3), (2.38, "s", [], 3), (1.27, "t", [7.1], 3)]
    pascal = {"s": [1], "d": [1, 1], "t": [1, 2, 1], "q": [1, 3, 3, 1]}
    peaks, multiplets, integrals = [], [], []
    for delta, cls, js, nh in mults:
        w = pascal[cls]
        jp = (js[0] / sf) if js else 0.0
        pos = [delta + (k - (len(w) - 1) / 2) * jp for k in range(len(w))]
        amp = nh / sum(w)
        for p, a in zip(pos, w):
            y += amp * a * (lw / 2) ** 2 / ((x - p) ** 2 + (lw / 2) ** 2)
            peaks.append({"x": round(p, 4)})
        lo, hi = min(pos) - 6 * lw, max(pos) + 6 * lw
        multiplets.append({"lo": lo, "hi": hi, "delta": delta, "cls": cls, "nH": nh, "J": js})
        integrals.append({"lo": lo, "hi": hi, "value": float(nh)})
    solvents = []
    for p, a, name in ((7.26, 0.25, "CHCl3"), (1.56, 0.6, "H2O")):
        y += a * (lw / 2) ** 2 / ((x - p) ** 2 + (lw / 2) ** 2)
        solvents.append({"x": p, "name": name})
    return dict(x=x, y=y, sf=sf, integrals=integrals, peaks=peaks, multiplets=multiplets, solvents=solvents)
