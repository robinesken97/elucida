"""EPR-Tab: Spindichte und Hyperfeinkopplungen aus einer Rechnung (Gaussian 16 oder ORCA, `formats.calc.parse_epr`).

Zwei Reiter neben „Abbildung“: Spindichte/SOMO auf dem Molekül mit Mulliken-Spinpopulationen in Prozent und berechnete
isotrope Kopplungen an den Kernen neben den experimentellen der S = ½-Simulation. Rendering wie die Orbitale des
DFT-Tabs (`XrayFigure` + `core.orbitals`). Zustand: `tab.st["calc"]` (Dateien, Zuordnung, Ansicht), Darstellung in den
flachen Schlüsseln `spin_*`/`hfc_*` des Tabs.
"""
from __future__ import annotations

import csv
import html
import re
import unicodedata
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register as register_canvas
from elucida.app.i18n import T
from elucida.app.style import make_form
from elucida.core import orbitals as ORB
from elucida.core import uvvis as core
from elucida.formats.calc import parse_epr, read_text
from elucida.tabs import base as TABS
from elucida.tabs import dft as DFT
from elucida.tabs import xray as XRAY

UNITS = {"MHz": 2, "G": 2, "mT": 3}                    # Nachkommastellen wie im EPR-Tab (`hfc_texts`)
SURFACES = ("spin", "somo", "none")
ISO_DEFAULT = {"spin": 0.002, "somo": 0.03}            # a.u.; übliche Isowerte für Spindichte bzw. ein Orbital
CALC_DEFAULT = dict(file="", orb="", sim=None, assign={}, view=None, zoom=1.0, pan=[0.0, 0.0], layout={})
_PLUS, _MINUS, _ = ORB.orbital_colors(0)
DISPLAY_DEFAULTS = dict(spin_surface="spin", spin_iso=ISO_DEFAULT["spin"], somo_iso=ISO_DEFAULT["somo"],
                        spin_alpha=ORB.ORB_ALPHA, spin_plus="", spin_minus="", spin_thresh=5.0, hfc_unit="MHz",
                        hfc_min=10.0, hfc_nuclei="", hfc_signed=False, hfc_dipole=False)
HFC_ZOOM = 0.5                                         # Kopplungsbild: Start klein, dann wachsen, bis Molekül samt
HFC_FILL = 0.94                                        # Werten die Zeichenfläche bis auf einen Rand füllt
_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
ARROW = dict(arrowstyle="->", lw=0.8, color="black", shrinkA=2, shrinkB=6, mutation_scale=9)


def minus(t):
    return t.replace("-", "−")


def percents(spin):
    """Mulliken-Spinpopulationen -> Prozent der Summe aller Atome, mit Vorzeichen (Summe = 100)."""
    s = float(sum(spin))
    if abs(s) < 1e-6:
        raise ValueError(T("epr_calc_no_spin"))
    return [100.0 * v / s for v in spin]


def num(v, dec=2):
    """Zahl mit fester Stellenzahl und echtem Minus, kaufmännisch gerundet (`round_half_up`); nie „−0.00“."""
    r = core.round_half_up(v, dec)
    return minus(f"{0.0 if r == 0 else r:.{dec}f}")


def pct_label(p):
    """Ganzzahlig wie die Vorlage, in Bild, Tabelle (dort ohne „%“: die Einheit steht im Kopf) und Tooltip gleich;
    die CSV behält die Rohwerte."""
    return num(p, 0) + "%"


def calc_value(f, unit):
    """Berechnete Kopplung (Isotop, MHz, Gauss) in der Einheit; G und mT aus der Gauss-Spalte der Ausgabe."""
    return {"MHz": f[1], "G": f[2], "mT": f[2] / 10.0}[unit]


def nucleus_el(name):
    """'14N' -> 'N'; D und T sind Wasserstoff."""
    el = re.sub(r"^\d+", "", name)
    return "H" if el in ("D", "T") else el


def iso_text(name):
    """'14N' -> '¹⁴N'."""
    m = re.match(r"^(\d*)(.*)$", name)
    return m.group(1).translate(_SUP) + m.group(2)


def nuclei_filter(text):
    """'H, N' -> {'H', 'N'}; leer -> None (automatisch)."""
    els = {nucleus_el(t) for t in re.split(r"[,;\s]+", str(text).strip()) if t}
    return els or None


def bad_groups(d, groups, assign):
    """Gruppen (Index als Text), deren Zuordnung nicht mehr zur Simulation passt: Gruppe fehlt oder ein Kern hat ein
    anderes Element als die Gruppe (die Zuordnung hängt am Gruppenindex; nach Änderung der Kerne der Simulation stand
    sonst ein N-Wert unter „(exp. <H-Wert>)“). Solche Zuordnungen gelten nicht, sie werden nie umgedeutet."""
    bad = []
    for gi, ats in assign.items():
        i = int(gi)
        if ats and (i >= len(groups) or any(k >= len(d["els"]) or d["els"][k] != nucleus_el(groups[i][1])
                                            for k in ats)):
            bad.append(gi)
    return bad


def hfc_items(d, groups, assign, unit, nuclei, a_min, signed=True):
    """Beschriftungen der Kopplungs-Abbildung. groups: [(n, Kernname, experimenteller Wert als Text)] der Simulation,
    assign: {Gruppenindex als Text: [Atomindizes]}. Zugeordnete Kerne einer Gruppe = Mittel mit Vorzeichen („avg.“ ab
    zwei Kernen) über dem experimentellen Wert; übrige Kerne einzeln ab a_min (MHz), nur Elemente aus nuclei.
    signed False: Beträge im Text (das Experiment liefert kein Vorzeichen); gemittelt wird immer mit Vorzeichen.
    -> [dict(atoms, group, value, text)]"""
    dec, items, used, bad = UNITS[unit], [], set(), bad_groups(d, groups, assign)
    shown = (lambda v: v) if signed else abs
    for gi, (_n, _name, exp) in enumerate(groups):
        ats = [k for k in assign.get(str(gi), []) if k in d["fermi"]] if str(gi) not in bad else []
        if not ats:
            continue
        v = float(np.mean([calc_value(d["fermi"][k], unit) for k in ats]))
        items.append(dict(atoms=ats, group=gi, value=v, text=(
            f"{num(shown(v), dec)} {unit}" + (" avg." if len(ats) > 1 else "") + f"\n(exp. {exp} {unit})")))
        used |= set(ats)
    for k, f in sorted(d["fermi"].items()):
        if k in used or abs(f[1]) < a_min or (nuclei and d["els"][k] not in nuclei):
            continue
        v = calc_value(f, unit)
        items.append(dict(atoms=[k], group=None, value=v, text=f"{num(shown(v), dec)} {unit}"))
    return items


def easyspin_script(nuclei, g=None, g_from="", mw=None, rng=None, meas="", level="", source=""):
    """Startskript für EasySpin `garlic` (isotrope Lösung), reines ASCII, Zahlen mit Punkt.
    nuclei: [(Isotop '14N', n, A [MHz] mit Vorzeichen, [Atomnamen], n der Simulation oder None)]. g, mw (GHz), rng
    ((lo, hi) mT) None -> auskommentierter Platzhalter: garlic verlangt g ohne Standardwert, nie eine Zahl raten."""
    def mhz(v):
        r = core.round_half_up(v, 2)
        return f"{0.0 if r == 0 else r:.2f}"
    head = ["% EasySpin start script: isotropic cw EPR spectrum in solution (garlic)",
            "% Hyperfine couplings: Fermi contact terms from a DFT calculation"
            + (f" ({level} level of theory)" if level else ""),
            f"% Source: {source}" if source else None,
            "% Isotropic couplings only; anisotropic tensors not exported.",
            "% Units: A in MHz (signs as calculated; groups: mean over the assigned nuclei), mwFreq in GHz,",
            "%        Range and lwpp in mT.",
            "% Entries of Sys.Nucs / Sys.n / Sys.A:"]
    for i, (iso, n, _a, atoms, n_sim) in enumerate(nuclei, 1):
        head.append(f"%   {i}  {iso}  {' '.join(atoms)}"
                    + (f"  (simulation: {n_sim} nuclei)" if n_sim is not None and n_sim != n else ""))
    body = ["clear",
            f"Sys.g = {g:.4f};  % isotropic g, fit of the simulation '{g_from}'" if g is not None
            else "% Sys.g = ;  % set g (no fitted S = 1/2 simulation; garlic requires g)",
            "Sys.Nucs = '" + ",".join(x[0] for x in nuclei) + "';",
            "Sys.n = [" + " ".join(str(x[1]) for x in nuclei) + "];",
            "Sys.A = [" + " ".join(mhz(x[2]) for x in nuclei) + "];  % MHz",
            "% Sys.lwpp = [Gauss Lorentz];  % mT, peak-to-peak: set line width",
            f"Exp.mwFreq = {mw:.10g};  % GHz, measurement '{meas}'" if mw else "% Exp.mwFreq = ;  % GHz: set microwave frequency",
            f"Exp.Range = [{rng[0]:.3f} {rng[1]:.3f}];  % mT" if rng else "% Exp.Range = [ ];  % mT: set field range",
            "garlic(Sys,Exp);"]
    text = unicodedata.normalize("NFKD", "\n".join(x for x in head + body if x is not None).replace("½", "1/2"))
    return "".join(c for c in text if not unicodedata.combining(c)).encode("ascii", "replace").decode("ascii") + "\n"


def matlab_script_name(stem):
    """Dateiname des Skripts aus dem Exportnamen: MATLAB startet ein Skript nur über einen gültigen Bezeichner
    (Buchstabe am Anfang, nur [A-Za-z0-9_], höchstens 63 Zeichen), z. B. „S3.1_EPR“ -> „S3_1_EPR_easyspin.m“."""
    s = unicodedata.normalize("NFKD", str(stem)).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    if not s[:1].isalpha():
        s = "x" + s
    return s[:63 - len("_easyspin")] + "_easyspin.m"


def group_targets(atoms, bonds, taken):
    """Atome, auf die die Pfeile einer Gruppe zeigen: Kerne, die zu mehreren am selben Nachbarn sitzen (die drei H
    einer Methylgruppe), teilen sich einen Pfeil auf diesen Nachbarn, wenn er kein eigenes Label trägt; alle anderen
    bekommen ihren eigenen. Zwei Methylgruppen = zwei Pfeile."""
    parent = {}
    for k in atoms:
        nb = [b if a == k else a for a, b in bonds if k in (a, b)]
        parent[k] = nb[0] if len(nb) == 1 else None
    out = []
    for k in atoms:
        par = parent[k]
        t = par if par is not None and par not in taken and sum(parent[j] == par for j in atoms) > 1 else k
        if t not in out:
            out.append(t)
    return out


def place_outside(F, keys, kept, more=None):
    """Labels rings um das Molekül: vom Schwerpunkt aus nach außen, so nah wie möglich, nie auf einem Atom oder einem
    anderen Label; der Pfeil soll kein anderes Atom kreuzen (kostet, statt zu verbieten: Kerne in der Mitte). kept:
    vom Nutzer gezogene Labels, sie bleiben und werden nur reserviert. more: {Label: weitere Atome, zu denen von ihm
    ein Pfeil führt}. Kein Pfeil läuft durch ein Label, kein Label liegt auf einem Pfeil (Nutzerwunsch 2026-11-13);
    Labels halten Abstand zueinander und zum Molekül, sich kreuzende Pfeile kosten (verboten wäre zu streng, wenn keine
    Seite frei ist). -> (Rahmen um Atome und Labels in Pixeln, Zahl der Labels ohne Platz)"""
    from matplotlib.text import Text
    rend = F.fig.canvas.get_renderer()
    tr, ppt = F.ax.transData, F.fig.dpi / 72.0
    W, H = F.fig.get_size_inches() * F.fig.dpi
    ats = F.scene["atoms"]
    P = np.array([tr.transform((it["x"], it["y"])) for it in ats])
    rad = np.array([abs(tr.transform((it["x"] + max(it["w"], it["h"]) / 2, it["y"]))[0] - p[0]) for it, p in zip(ats, P)])
    row = {it["k"]: i for i, it in enumerate(ats)}
    c, m, boxes, segs, miss = P.mean(axis=0), 5.0 * ppt, [], [], 0

    def crossing(s1, s2):                                  # schneiden sich zwei Pfeile (Endpunkte der Linien)?
        a1, a2, b1, b2 = s1[0], s1[-1], s2[0], s2[-1]
        d1, d2 = a2 - a1, b2 - b1
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            return False
        t = ((b1[0] - a1[0]) * d2[1] - (b1[1] - a1[1]) * d2[0]) / den
        u = ((b1[0] - a1[0]) * d1[1] - (b1[1] - a1[1]) * d1[0]) / den
        return 0.02 < t < 0.98 and 0.02 < u < 0.98

    def on_box(pts, b):                                    # liegt ein Punkt der Linie im Kasten?
        return bool(((pts[:, 0] > b[0]) & (pts[:, 0] < b[2]) & (pts[:, 1] > b[1]) & (pts[:, 1] < b[3])).any())

    def line(a, b):
        return a + np.linspace(0.0, 1.0, max(2, int(np.hypot(*(b - a)) / 5)))[:, None] * (b - a)
    todo = sorted(keys, key=lambda key: -float(np.hypot(*(P[row[F.ann_items[key]._atom]] - c))))   # außen zuerst
    for key in todo:
        ann = F.ann_items[key]
        i = row[ann._atom]
        a = P[i]
        ann.arrow_patch.shrinkB = rad[i] / ppt + 2.0          # Spitze endet kurz vor dem Kern
        bb = Text.get_window_extent(ann, rend)
        w, h = bb.width, bb.height
        if key in kept:
            ctr = a + np.array(ann.xyann) * ppt
            boxes.append((ctr[0] - w / 2, ctr[1] - h / 2, ctr[0] + w / 2, ctr[1] + h / 2))
            segs += [line(a, ctr)] + [line(P[row[j]], ctr) for j in (more or {}).get(key, ()) if j in row]
            continue
        u0 = a - c
        u0 = u0 / np.hypot(*u0) if np.hypot(*u0) > 1 else np.array([0.0, 1.0])
        best = None
        for d in np.arange(26.0, 300.0, 8.0) * ppt:
            for rot in (0, 20, -20, 40, -40, 60, -60, 90, -90, 120, -120, 150, -150, 180):
                t = np.radians(rot)
                u = np.array([u0[0] * np.cos(t) - u0[1] * np.sin(t), u0[0] * np.sin(t) + u0[1] * np.cos(t)])
                ctr = a + u * (d + abs(u[0]) * w / 2 + abs(u[1]) * h / 2)
                box = (ctr[0] - w / 2 - m, ctr[1] - h / 2 - m, ctr[0] + w / 2 + m, ctr[1] + h / 2 + m)
                if box[0] < 0 or box[1] < 0 or box[2] > W or box[3] > H:
                    continue
                near = np.hypot(np.clip(P[:, 0], box[0], box[2]) - P[:, 0], np.clip(P[:, 1], box[1], box[3]) - P[:, 1])
                if (near < rad + 3.0 * ppt).any() or any(min(box[2], b[2]) > max(box[0], b[0]) and min(box[3], b[3]) > max(box[1], b[1])
                                             for b in boxes):
                    continue
                seg = [line(a, a + u * d)] + [line(P[row[j]], ctr) for j in (more or {}).get(key, ()) if j in row]
                if any(on_box(sg, b) for sg in seg for b in boxes) or any(on_box(sg, box) for sg in segs):
                    continue                               # Pfeil nie durch ein anderes Label, Label nie auf einem Pfeil
                along = np.clip((P - a) @ u, 0.0, d)
                off = np.hypot(*(P - a - along[:, None] * u).T)
                cross = int(((off < rad + 1.5 * ppt) & (np.arange(len(P)) != i)).sum())
                cross += 3 * sum(crossing(sg, old) for sg in seg for old in segs)
                cost = d / ppt + 0.4 * abs(rot) + 60.0 * cross
                if best is None or cost < best[0]:
                    best = (cost, ctr, box, seg)
            if best is not None and best[0] < d / ppt + 8:    # weiter außen wird es nur teurer
                break
        if best is not None:
            ann.xyann = tuple(round(float(v), 1) for v in (best[1] - a) / ppt)
            boxes.append(best[2])
            segs += best[3]
        else:
            miss += 1
    F.auto_pos = F.current_layout()
    lo = np.vstack([P - rad[:, None]] + [np.array(b[:2])[None] for b in boxes]).min(axis=0)
    hi = np.vstack([P + rad[:, None]] + [np.array(b[2:])[None] for b in boxes]).max(axis=0)
    return (lo[0], lo[1], hi[0], hi[1]), miss


def write_gaussian_epr(path, els, xyz, spin, mhz, route="#p Prop=EPR UB3LYP/def2SVP", charge=1, mult=2):
    """Künstliche Gaussian-16-Ausgabe einer offenschaligen Rechnung aus vorgegebenen (erfundenen) Werten:
    Mulliken-Spinpopulationen, Fermi-Kontakt-Kopplungen (MHz; Gauss mit g_e) und Dipolkopplungen in der Anordnung
    echter Ausgaben (zwei Mulliken-Blöcke, Dipolblock doppelt). Für Selbsttest und Beispielprojekt, kein Datensatz."""
    from elucida.formats.elements import ELEMENTS
    iso = {"H": 1, "C": 13, "N": 14, "O": 17, "F": 19, "P": 31, "S": 33, "Cl": 35, "B": 11}
    tag = [f"{e}({iso.get(e, 1)})" for e in els]
    line = " " + "-" * 69
    L = [" Entering Gaussian System, Link 0=g16", " Gaussian 16:  ES64L-G16RevC.01  3-Jul-2019", line,
         " " + route, line, f" Charge = {charge:2d} Multiplicity = {mult}",
         "                         Standard orientation:", line,
         " Center     Atomic      Atomic             Coordinates (Angstroms)",
         " Number     Number       Type             X           Y           Z", line]
    L += [f" {i + 1:6d} {ELEMENTS.index(e) + 1:10d} {0:11d} {x:13.6f} {y:11.6f} {z:11.6f}"
          for i, (e, (x, y, z)) in enumerate(zip(els, xyz))]
    L += [line, " SCF Done:  E(UB3LYP) =  -78.1234567890     A.U. after   12 cycles",
          " Mulliken charges and spin densities:", "               1          2"]
    L += [f" {i + 1:5d}  {e:<2s} {0.1:10.6f} {v:10.6f}" for i, (e, v) in enumerate(zip(els, spin))]
    L += [" Sum of Mulliken charges =   1.00000   1.00000",
          " Mulliken charges and spin densities with hydrogens summed into heavy atoms:", "               1          2",
          "     1  C    0.500000   0.520000", "     2  C    0.500000   0.480000",
          "                          Isotropic Fermi Contact Couplings",
          "        Atom                 a.u.       MegaHertz       Gauss      10(-4) cm-1"]
    L += [f" {i + 1:5d}  {t:<8s} {v / 1000:15.5f} {v:15.5f} {v / 2.8025:13.5f} {v / 2.998:13.5f}"
          for i, (t, v) in enumerate(zip(tag, mhz))]
    dip = [" " + "-" * 81, "              Anisotropic Spin Dipole Couplings in Principal Axis System", " " + "-" * 81, "",
           "       Atom             a.u.   MegaHertz   Gauss  10(-4) cm-1        Axes", ""]
    for i, (t, v) in enumerate(zip(tag, mhz)):
        for k, (nm, f) in enumerate((("Baa", -0.5), ("Bbb", -0.25), ("Bcc", 0.75))):
            head = f" {i + 1:5d} {t:<6s}" if k == 1 else " " * 13
            dip.append(f"{head} {nm} {f * v / 1000:10.4f} {f * v:9.3f} {f * v / 2.8025:9.3f} {f * v / 2.998:9.3f}"
                       "  0.0000  0.0000  1.0000")
        dip.append(" ")
    L += dip + [""] + dip + ["", " Normal termination of Gaussian 16 at Fri Nov 13 10:00:00 2026."]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return Path(path)


def make_test_gaussian_epr(path):
    """Ethen-Radikalkation mit der Geometrie von `ORB.make_test_cube`, alle Zahlen erfunden."""
    return write_gaussian_epr(
        path, ["C", "C", "H", "H", "H", "H"],
        [(-0.667, 0, 0), (0.667, 0, 0), (-1.232, 0.923, 0), (-1.232, -0.923, 0), (1.232, 0.923, 0), (1.232, -0.923, 0)],
        [0.58, 0.54, -0.03, -0.03, -0.03, -0.03], [30.5, 28.5, -40.0, -42.0, -38.0, -40.0])


def write_orca_epr(path, els, xyz, spin, mhz, version="6.0.0", hfc=True, aorb=(), charge=1, mult=2):
    """Künstliche ORCA-Ausgabe im Layout echter Ausgaben (6.0: „A  : Isotope=“ + „Total HFC matrix“; 4.x/5.0:
    „A:ISTP=“ + „Raw HFC matrix“): Mulliken- und Löwdin-Spinpopulationen, je Kern A(FC) und A(SD) (−½, −¼, ¾ der
    Kopplung), A(ORB) nur für Kerne in aorb. hfc False = Rechnung ohne %eprnmr. Alle Zahlen erfunden."""
    iso = {"H": 1, "C": 13, "N": 14, "O": 17, "F": 19, "P": 31, "S": 33, "Cl": 35, "B": 11}
    new = version.startswith("6")
    L = ["", "                                 *****************", "                                 * O   R   C   A *",
         "                                 *****************", "",
         f"                         Program Version {version}  -   RELEASE  -", "",
         "=" * 80, "                                       INPUT FILE", "=" * 80, "NAME = radical.inp",
         "|  1> ! UB3LYP def2-SVP TightSCF"]
    if hfc:
        L += ["|  2> %eprnmr", "|  3>   Nuclei = all H {aiso, adip}", "|  4>   Nuclei = all C {aiso, adip}", "|  5> end"]
    L += [f"|  6> * xyz {charge} {mult}", "|  7> *", "|  8>                          ****END OF INPUT****", "=" * 80,
          "", "---------------------------------", "CARTESIAN COORDINATES (ANGSTROEM)",
          "---------------------------------"]
    L += [f"  {e:<2s} {x:16.6f} {y:13.6f} {z:13.6f}" for e, (x, y, z) in zip(els, xyz)]
    L += ["", f" Total Charge           Charge          ....    {charge}",
          f" Multiplicity           Mult            ....    {mult}", "",
          "-----------------------------------------------", "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
          "--------------------------------------------"]
    L += [f"{i:4d} {e:<2s}:{0.1:12.6f}{v:12.6f}" for i, (e, v) in enumerate(zip(els, spin))]
    L += ["Sum of atomic charges         :    1.0000000", "Sum of atomic spin populations:    1.0000000", "",
          "-------------------------------------------", "LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS",
          "-------------------------------------------"]
    L += [f"{i:4d} {e:<2s}:{0.1:12.6f}{0.9 * v:12.6f}" for i, (e, v) in enumerate(zip(els, spin))]
    L += ["", "", "FINAL SINGLE POINT ENERGY       -78.123456789012", ""]
    if hfc:
        L += ["-----------------------------------------", "ELECTRIC AND MAGNETIC HYPERFINE STRUCTURE"
              + (f" ({len(els)} nuclei)" if new else ""), "-----------------------------------------", ""]
        for i, (e, v) in enumerate(zip(els, mhz)):
            rule = " " + "-" * 59
            head = (f" Nucleus {i:3d}{e} : A  : Isotope={iso.get(e, 1):5d} I=  0.5 P=100.0000 MHz/au**3 " if new else
                    f" Nucleus {i:3d}{e} : A:ISTP={iso.get(e, 1):5d} I=  0.5 P=100.0000 MHz/au**3")
            sd = (-0.5 * v, -0.25 * v, 0.75 * v)
            row = lambda nm, a: f" {nm:<13s}" + "".join(f"{x:10.4f}           " for x in a).rstrip()
            L += [rule, head, rule, "", f" {'Total' if new else 'Raw'} HFC matrix (all values in MHz): ",
                  " " + "-" * 64] + [" " * 14 + f"{v:10.4f}" * 3] * 3 + ["", row("A(FC)", (v,) * 3), row("A(SD)", sd)]
            if i in aorb:
                L += [row("A(ORB)", (0.01, 0.02, 0.03)) + "    A(PC) =    0.0200"]
            L += ["             ----------           ----------           ----------",
                  row("A(Tot)", [v + x for x in sd]) + f"    A(iso)={v:10.4f}", ""]
    L += ["", "                             ****ORCA TERMINATED NORMALLY****"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(L) + "\n")
    return Path(path)


def make_test_orca_epr(path, **kw):
    """Wie `make_test_gaussian_epr` (Geometrie von `ORB.make_test_cube`), alle Zahlen erfunden."""
    return write_orca_epr(
        path, ["C", "C", "H", "H", "H", "H"],
        [(-0.667, 0, 0), (0.667, 0, 0), (-1.232, 0.923, 0), (-1.232, -0.923, 0), (1.232, 0.923, 0), (1.232, -0.923, 0)],
        [0.58, 0.54, -0.03, -0.03, -0.03, -0.03], [30.5, 28.5, -40.0, -42.0, -38.0, -40.0], **kw)


class _Page(QWidget):
    """Seiteninhalt, der erst beim Anzeigen zeichnet (die Spindichte kostet einige Sekunden)."""

    def __init__(self, on_show):
        super().__init__()
        self.on_show = on_show

    def showEvent(self, ev):
        super().showEvent(ev)
        self.on_show()


class _Mouse:
    """Empfänger für `XrayMouse` je Reiter: Ansicht gilt für beide Abbildungen, Labels je Abbildung."""

    def __init__(self, pages, kind):
        self.p, self.kind = pages, kind

    def hover_atom(self, k):
        self.p.hover(self.kind, k)

    def atom_clicked(self, k):
        if self.kind == "hfc" and k is not None:
            self.p.toggle_atom(k)

    def atom_double_clicked(self, k):
        pass

    def atoms_boxed(self, ks):
        if self.kind == "hfc":
            for k in ks:
                self.p.toggle_atom(k, add_only=True)

    def view_changed(self, R):
        self.p.calc["view"] = [round(float(v), 6) for v in np.asarray(R).ravel()]
        self.p.changed()

    def pan_changed(self, pan):
        auto = getattr(self.p.F.get(self.kind), "_auto_pan", (0.0, 0.0))   # Kopplungsbild: ohne die automatische Lage
        self.p.calc["pan"] = [round(float(pan[0] - auto[0]), 4), round(float(pan[1] - auto[1]), 4)]
        self.p.changed()

    def zoom_changed(self, z):
        self.p.calc["zoom"] = round(float(z) / getattr(self.p.F.get(self.kind), "_auto_zoom", 1.0), 4)
        self.p.zoom_timer.start()

    def labels_moved(self, layout):
        lay = self.p.layout(self.kind)
        auto = self.p.F[self.kind].auto_pos if self.p.F.get(self.kind) else {}
        for key, pos in layout.items():
            if key.startswith("lbl_") and pos != auto.get(key):
                lay[key] = pos
        self.p.changed()


class SpinPages:
    """Karten und Reiter „Spindichte“/„Hyperfein“ eines EPR-Tabs."""

    KINDS = ("spin", "hfc")

    def __init__(self, tab):
        self.tab = tab
        self._loading = False
        self.F, self.mouse, self.dirty = {}, {}, {"spin": True, "hfc": True}
        self.figs, self.canvases, self.hosts, self.stacks, self.tables, self.hints, self.pages = {}, {}, {}, {}, {}, {}, {}
        self.zoom_timer = QTimer(tab)                      # Mausrad: viele Ereignisse, ein Rückgängig-Schritt
        self.zoom_timer.setSingleShot(True)
        self.zoom_timer.setInterval(400)
        self.zoom_timer.timeout.connect(self.changed)
        self.data_card = self._data_card()
        self.assign_card = self._assign_card()
        self.display_card = self._display_card()
        self.groups = {k: self._page(k) for k in self.KINDS}
        self.sync()

    # -- Zustand -------------------------------------------------------------------------------
    @property
    def calc(self):
        p = self.tab.st.get("calc")
        if not isinstance(p, dict):
            p = self.tab.st["calc"] = {}
        for k, v in CALC_DEFAULT.items():
            p.setdefault(k, type(v)(v) if isinstance(v, (dict, list)) else v)
        return p

    def layout(self, kind, create=True):
        if not create:                                     # nur lesen: Anzeigen allein ist kein Rückgängig-Schritt
            return (self.calc["layout"].get(kind) or {}).get(self.tab.size_key()) or {}
        return self.calc["layout"].setdefault(kind, {}).setdefault(self.tab.size_key(), {})

    def changed(self):
        if self._loading:
            return
        self.collect()
        self.tab.refresh_summary()                         # zieht Karten und beide Reiter nach
        self.tab.main.push_undo()

    def collect(self):
        st = self.tab.st
        surf = self.cmb_surface.currentData()
        st.update(spin_surface=surf, spin_alpha=self.sp_alpha.value(), spin_thresh=self.sp_thresh.value(),
                  hfc_unit=self.cmb_unit.currentData(), hfc_min=self.sp_min.value(),
                  hfc_nuclei=self.ed_nuclei.text().strip(), hfc_signed=self.cb_signed.isChecked(),
                  hfc_dipole=self.cb_dipole.isChecked())
        if surf in ISO_DEFAULT and self._iso_of == surf:
            st[surf + "_iso"] = self.sp_iso.value()
        self.calc["sim"] = self.cmb_sim.currentData()

    # -- Daten ---------------------------------------------------------------------------------
    def has_data(self):
        p = self.calc["file"]
        return bool(p) and Path(p).exists()

    def data(self):
        """Gelesene Rechnung oder None; Lesefehler als ValueError."""
        if not self.has_data():
            return None
        p = self.calc["file"]
        return self.tab.cache(("eprcalc", p), lambda: parse_epr(read_text(p)))

    def frame(self, d):
        return DFT.calc_frame(d["calc"])[0]

    def level(self, d):
        from elucida.tabs.dft_pages import level_of_theory
        return level_of_theory(d["calc"])

    def sims(self):
        """Eigene S = ½-Simulationen mit Kopplungen: [(uid, Eintrag)]."""
        from elucida.tabs import epr as EPR
        return [(e["uid"], e) for e in self.tab.st["entries"] if e.get("kind") == "iso"
                and EPR.parse_nuclei(e.get("nuclei", ""))]

    def sim(self):
        sims = dict(self.sims())
        return sims.get(self.calc["sim"]) or next(iter(sims.values()), None)

    def exp_groups(self):
        """[(n, Kernname, experimenteller Wert als Text in der gewählten Einheit)] der gewählten Simulation."""
        from elucida.tabs import epr as EPR
        e, unit = self.sim(), self.tab.st["hfc_unit"]
        if e is None:
            return []
        out = []
        for (n, _I, a), name in zip(EPR.parse_nuclei(e["nuclei"]), EPR.nuclei_names(e["nuclei"])):
            mt, mhz = EPR.hfc_texts(a, e["g"])
            out.append((n, name, {"MHz": mhz, "mT": mt, "G": f"{a * 10.0:.{UNITS['G']}f}"}[unit]))
        return out

    def assign(self):
        """Zuordnung der gewählten Simulation: {Gruppenindex als Text: [Atomindizes]}."""
        e = self.sim()
        return self.calc["assign"].setdefault(e["uid"], {}) if e is not None else {}

    def items(self, d, unit=None):
        st, groups = self.tab.st, self.exp_groups()
        # automatisch: Elemente der experimentellen Gruppen; ohne Simulation alles außer C und O (13C und 17O sind
        # selten, ihre Kopplungen sieht man im Spektrum normalerweise nicht – im Feld „Kerne“ wählbar)
        nuclei = (nuclei_filter(st["hfc_nuclei"]) or {nucleus_el(g[1]) for g in groups}
                  or set(d["els"]) - {"C", "O"})
        return hfc_items(d, groups, self.assign(), unit or st["hfc_unit"], nuclei, st["hfc_min"], st["hfc_signed"])

    def easyspin_text(self):
        """EasySpin-Startskript (garlic) oder None ohne Kopplungen. Nur die zugeordneten Gruppen; ohne Zuordnung die
        Kerne, die auch das Bild einzeln zeigt (ab „Ab Kopplung“, Elemente unter „Kerne“). A immer in MHz wie die
        Rechnung, n = Zahl der zugeordneten Kerne (über sie wird gemittelt). g und Exp nur aus der Simulation/ihrer
        Messung, g nur mit gültigem Fit (wie Unterschrift und Methodentext)."""
        d = self.data() if self.has_data() else None
        if d is None or not d["fermi"]:
            return None
        its = self.items(d, "MHz")
        its = [it for it in its if it["group"] is not None] or its
        if not its:
            return None
        groups, tab = self.exp_groups(), self.tab
        nuclei = [(d["fermi"][it["atoms"][0]][0], len(it["atoms"]), it["value"],
                   [self.atom_name(d, k) for k in it["atoms"]], groups[it["group"]][0] if it["group"] is not None else None)
                  for it in its]
        e, g, mw, rng, meas = self.sim(), None, None, None, ""
        if e is not None:
            dB, calib_t = tab.calibration_shift()
            if tab.fit_ok(e) and not (dB and e.get("fit_to") == calib_t):
                g = e["g"]
            target = next((x for x in tab.st["entries"] if x["uid"] == e.get("fit_to")), None)
            if target is not None:
                mw, meas = tab.axis_mw(target), target["label"]
                B = np.asarray(tab.processed(target, {}, hide=False)[0], float)
                B = B[np.isfinite(B)]
                rng = (float(B.min()), float(B.max())) if len(B) else None
        src = Path(self.calc["file"]).name + self.program(d)
        return easyspin_script(nuclei, g, e["label"] if e else "", mw, rng, meas, self.level(d), src)

    def save_easyspin(self, path=None):
        """EasySpin-Startskript speichern (Dateiauswahl wie die xyz-Sammlung des DFT-Tabs; der Export schreibt es mit)."""
        txt, t = self.easyspin_text(), self.tab
        if txt is None:
            return t.main.statusBar().showMessage(T("epr_calc_es_none"), 6000)
        if path is None:
            stem = matlab_script_name(PRJ.export_stem(t.main.export_name(), t.STATE_KEY))
            start = PRJ.export_dir(t.main.project_dir, PRJ.TABLES) / stem if t.main.project_dir else Path(stem)
            path, _ = QFileDialog.getSaveFileName(t, T("epr_calc_es"), str(start), "MATLAB (*.m)")
            if not path:
                return None
        Path(path).write_text(txt, encoding="ascii", newline="\n")
        t.main.log_signal.emit(T("saved", p=str(path)))
        t.main.statusBar().showMessage(T("saved", p=str(path)), 6000)
        return Path(path)

    # -- Fläche --------------------------------------------------------------------------------
    def basis(self, p):
        def make():
            b = ORB.Basis(self.tab.cache(("molden", p), lambda: ORB.parse_molden(read_text(p))))
            err = b.setup()
            if err > ORB.Basis.MAX_ORTH_ERR:
                raise ValueError(T("dft_orb_molden_conv", err=f"{err:.1e}"))
            return b
        return self.tab.cache(("basis", p), make)

    def orb_frame(self, p):
        """Geometrie der Orbitaldatei (Å) zum Abgleich mit der Rechnung."""
        if DFT.is_molden(p):
            return DFT.molden_frame(self.tab.cache(("molden", p), lambda: ORB.parse_molden(read_text(p))))
        return self.tab.cache(("cube", p), lambda: ORB.read_cube(p))

    def volume(self):
        """Gitter der gewählten Fläche oder None. Molden: Spindichte aus den besetzten MOs bzw. das höchste besetzte
        α-MO (SOMO); Cube: sein Inhalt (was er zeigt, sagt die Auswahl „Fläche“)."""
        surf, p = self.tab.st["spin_surface"], self.calc["orb"]
        if surf == "none" or not p or not Path(p).exists():
            return None
        if not DFT.is_molden(p):
            c = self.tab.cache(("cube", p), lambda: ORB.read_cube(p))
            return self.tab.cache(("orbvol", p, 0), lambda: ORB.Volume(c["data"][0], c["origin"], c["axes"]))
        b = self.basis(p)
        if surf == "spin":
            return self.tab.cache(("spinvol", p), lambda: ORB.Volume(*ORB.spin_density_grid(b)))
        mos = b.m["mos"]
        occ = [i for i, mo in enumerate(mos) if mo["spin"] == "a" and mo["occ"] > 0.5]
        if not occ:
            raise ValueError("Molden: no occupied orbital")
        i = max(occ, key=lambda i: mos[i]["energy"])
        return self.tab.cache(("orbvol", p, "mo", i),
                              lambda: ORB.Volume(*ORB.molden_grid(b, mos[i]["c"], ORB.MOLDEN_SPACING)))

    def surface(self):
        """Gezeigte Fläche: „spin“, „somo“ oder „none“ (auch ohne Orbitaldatei)."""
        return self.tab.st["spin_surface"] if self.volume() is not None else "none"

    def iso(self):
        st = self.tab.st
        return float(st[st["spin_surface"] + "_iso"])

    def colors(self):
        from matplotlib.colors import to_rgb
        st = self.tab.st
        return (to_rgb(st["spin_plus"]) if st["spin_plus"] else _PLUS,
                to_rgb(st["spin_minus"]) if st["spin_minus"] else _MINUS)

    # -- Abbildung -----------------------------------------------------------------------------
    def build(self, fig, kind, interactive=True):
        """XrayFigure der Spindichte („spin“) oder der Kopplungen („hfc“); None ohne Rechnung."""
        d = self.data()
        if d is None:
            return None
        st, fr = self.tab.st, self.frame(d)
        els, xyz, n = fr["els"], fr["xyz"], len(fr["els"])
        orb, items, sel = None, [], []
        bonds = self.tab.cache(("eprcalc_bonds", self.calc["file"]), lambda: DFT.bonds_of(els, xyz))
        vol = self.volume()                                 # Fläche in beiden Abbildungen (wie die Vorlage)
        if vol is not None:
            plus, minus_ = self.colors()
            orb = dict(vol=vol, iso=self.iso(), plus=plus, minus=minus_, alpha=min(1.0, float(st["spin_alpha"])))
        if kind == "spin":
            pct = percents(d["spin"])
            labels = [pct_label(p) for p in pct]
            on = {f"a{k}": abs(p) >= st["spin_thresh"] for k, p in enumerate(pct)}
        else:
            items = self.items(d)
            labels, on = [""] * n, {f"a{k}": False for k in range(n)}
            taken = {it["atoms"][0] for it in items if len(it["atoms"]) == 1}
            for it in items:                                # Gruppe: je Methylgruppe ein Pfeil auf ihr C
                it["targets"] = group_targets(it["atoms"], bonds, taken)
                it["at"] = it["targets"][0]
                taken.add(it["at"])
                labels[it["at"]] = it["text"]
                on[f"a{it['at']}"] = True
            if interactive and self.row() is not None:
                sel = [k for k in self.assign().get(str(self.row()), []) if k < n]
        mol = DFT.XyzMolecule(els, xyz, bonds, labels)
        cfg = self.tab.base_cfg()
        core.setup_fonts(TABS.plt, cfg)
        o = dict(prob=50, show_h=True, labels=True, h_labels=True, colors={}, bond_w=0.08, hidden_frags=[],
                 style="iboview", hidden_atoms=[], label_on=on, wire=set(), wire_h=False, label_mode="all",
                 hide_kinds=[], label_size=0.0, label_color="black", label_colors={}, cartoon_color=False,
                 h_radius=0.55 * 0.25, bg="white", ball_scale=1.0, rod_scale=1.0, orbital=orb, elem_labels=True,
                 label_arrows=ARROW if kind == "hfc" else None)
        v = self.calc["view"]
        R = np.array(v, float).reshape(3, 3) if v and len(v) == 9 else XRAY.default_view(mol, use=list(range(n)))
        lay = self.layout(kind, create=False)
        if kind == "spin":
            # Molekül, Fläche und Prozentwerte füllen die Fläche (Zoom/Verschiebung des Nutzers relativ dazu, wie im
            # Kopplungsbild: _Mouse rechnet _auto_zoom/_auto_pan heraus)
            F = XRAY.fitted_view(lambda z, shift: XRAY.XrayFigure(
                cfg, mol, R, o, lay, fig, selection=sel, zoom=self.calc["zoom"] * z,
                pan=tuple(np.array(self.calc["pan"], float) + shift)))
        else:
            # Molekül samt Werten soll die Fläche füllen: klein beginnen, Labels setzen, Rahmen messen, Maßstab und
            # Lage nachziehen (Labels haben feste Größe, deshalb in bis zu drei Schritten); der Zoom des Nutzers
            # multipliziert sich dazu. Passt ein Label nach dem Vergrößern nicht mehr, gilt der Schritt davor.
            more = {f"lbl_a{it['at']}": it["targets"][1:] for it in items if len(it["targets"]) > 1}
            def fitted(z, shift):
                F = XRAY.XrayFigure(cfg, mol, R, o, lay, fig, selection=sel, zoom=self.calc["zoom"] * z,
                                    pan=tuple(np.array(self.calc["pan"], float) + shift))
                F._auto_zoom, F._auto_pan = z, shift.copy()
                keys = [k for k in F.ann_items if k.startswith("lbl_")]
                for k in keys:
                    F.ann_items[k].set_multialignment("center")
                box, miss = place_outside(F, keys, {k for k in keys if lay.get(k)
                                                    and list(F.ann_items[k].xyann) == list(lay[k])}, more)
                return F, box, miss
            z, shift, good = HFC_ZOOM, np.zeros(2), None
            for step in range(3):
                F, box, miss = fitted(z, shift)
                if miss and good is not None:              # zu groß geworden: ein Label fand keinen Platz mehr
                    F, box, miss = fitted(*good)
                    break
                W, H = F.fig.get_size_inches() * F.fig.dpi
                f = min(HFC_FILL * W / max(1.0, box[2] - box[0]), HFC_FILL * H / max(1.0, box[3] - box[1]))
                dpp = F.data_per_px()
                move = np.array([(box[0] + box[2]) / 2 - W / 2, (box[1] + box[3]) / 2 - H / 2]) * dpp
                if step == 2 or (abs(f - 1.0) < 0.04 and np.abs(move / dpp).max() < 4):
                    break
                good = (z, shift.copy())
                z, shift = z * (1.0 + (f - 1.0) * 0.85), shift + move
        for it in items:                                    # weitere Ziele einer Gruppe: je ein Pfeil vom selben Label
            ann = F.ann_items.get(f"lbl_a{it['at']}")
            if ann is None:
                continue
            for j in it["targets"][1:]:
                r_pt = max(F.scene["by_k"][j]["w"], F.scene["by_k"][j]["h"]) / 2 * F.pt_per_A() if j in F.scene["by_k"] else 4
                a = F.ax.annotate("", xy=F._anchor(j), xycoords="data", xytext=(0.5, 0.5), textcoords=ann,
                                  arrowprops=dict(ARROW, shrinkB=r_pt + 2.0, patchA=None), annotation_clip=False,
                                  zorder=59)
                a._atom = j
                F.ann_items[f"arr_{it['at']}_{j}"] = a
                F.order.append(a)
            if len(it["targets"]) > 1:
                ann.set_bbox(dict(fc=F.bg_show, ec="none", pad=1.2))   # weitere Pfeile enden am Text, nicht darunter
        return F

    def caption(self, kind, name):
        """Bildunterschrift (HTML, englisch); nennt Isowert, Schwelle und Rechenniveau, nie das Programm."""
        d = self.data()
        if d is None:
            return ""
        st, lev = self.tab.st, self.level(d)
        at = f" ({html.escape(lev)} level of theory)" if lev else ""
        nm = f"<b>{html.escape(name)}</b>"
        if kind == "spin":
            surf = self.surface()
            pop = (f"Mulliken spin populations{at} in % of the sum over all atoms; values of at least "
                   f"{st['spin_thresh']:g}% are shown")
            if surf == "none":
                return f"{pop[0].upper()}{pop[1:]} for {nm}."
            what = "Spin density" if surf == "spin" else "SOMO"
            return f"{what} of {nm} (isovalue ±{self.iso():g} a.u.) with {pop}."
        unit, items, surf = st["hfc_unit"], self.items(d), self.surface()
        txt = f"Calculated isotropic hyperfine coupling constants (Fermi contact, in {unit}) of {nm}{at}"
        if surf != "none":
            txt += (f", shown on the {'spin density' if surf == 'spin' else 'SOMO'} "
                    f"(isovalue ±{self.iso():g} a.u.)")
        if not st["hfc_signed"]:
            txt += ", given as absolute values"
        if any(it["group"] is not None for it in items):
            txt += "; experimental values from the simulation of the EPR spectrum in parentheses"
        if any(len(it["atoms"]) > 1 for it in items):
            txt += "; avg.: mean over the nuclei assigned to one group of equivalent nuclei"
        return txt + "."

    def methods_text(self):
        d = self.data() if self.has_data() else None
        if d is None:
            return ""
        lev = self.level(d)
        m = ("Mulliken spin populations and isotropic hyperfine coupling constants (Fermi contact terms) were taken "
             "from a calculation" + (f" at the {lev} level of theory" if lev else "") + self.program(d)   # nie „a M06…“
             + "; spin populations are given as percentage of the "
             "sum over all atoms.")
        if any(len(it["atoms"]) > 1 for it in self.items(d)):
            m += (" Calculated coupling constants of nuclei assigned to one group of equivalent nuclei of the "
                  "simulation were averaged with their signs.")
        return m

    def program(self, d):
        """„ (ORCA 6.0.0)“ für den Methodentext; Rechenprogramm mit Version, nie Elucida."""
        c = d["calc"]
        return f" ({c['program']} {c['version']})".replace(" )", ")") if c.get("program") else ""

    # -- Tabellen ------------------------------------------------------------------------------
    def atom_name(self, d, k):
        return f"{d['els'][k]}{k + 1}"

    def rows(self, kind, d):
        """Tabellenzeilen (alle Atome, unabhängig von der Schwelle im Bild)."""
        if kind == "spin":
            pct = percents(d["spin"])
            rows = [[self.atom_name(d, k), num(v, 6), num(p, 0)] for k, (v, p) in enumerate(zip(d["spin"], pct))]
            return rows + [["Σ", num(sum(d["spin"]), 6), num(sum(pct), 0)]]
        # eine Spalte A_iso in der gewählten Einheit; Dipol-Hauptwerte nur auf Wunsch (acht Spalten rollten quer)
        st = self.tab.st
        unit, dip = st["hfc_unit"], st["hfc_dipole"]
        groups, rows = self.exp_groups(), []
        bad = bad_groups(d, groups, self.assign())
        group_of = {k: gi for gi, ats in self.assign().items() if gi not in bad for k in ats}
        for k, f in sorted(d["fermi"].items()):
            b = d["dipole"].get(k)
            gi = group_of.get(k)
            g = groups[int(gi)] if gi is not None and int(gi) < len(groups) else None
            rows.append([self.atom_name(d, k), iso_text(f[0]), num(calc_value(f, unit), UNITS[unit])]
                        + (([num(calc_value(("", x[0], x[1]), unit), UNITS[unit]) for x in b] if b else ["", "", ""])
                           if dip else [])
                        + [f"{g[0]} × {iso_text(g[1])}" if g else ""])
        return rows

    def headers(self, kind):
        if kind == "spin":
            return [T("epr_calc_atom"), T("epr_calc_pop"), T("epr_calc_pct")]
        st = self.tab.st
        unit = st["hfc_unit"]
        return ([T("epr_calc_atom"), T("epr_calc_nucleus"), f"A_iso [{unit}]"]
                + ([f"B_aa [{unit}]", f"B_bb [{unit}]", f"B_cc [{unit}]"] if st["hfc_dipole"] else [])
                + [T("epr_calc_group")])

    def write_csv(self, kind, path):
        """Rohwerte wie in der Ausgabe (CSV behält die Stellen der Rechnung)."""
        d = self.data()
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            if kind == "spin":
                w.writerow(["atom", "element", "Mulliken spin population", "percent of sum"])
                for k, (v, p) in enumerate(zip(d["spin"], percents(d["spin"]))):
                    w.writerow([k + 1, d["els"][k], f"{v:.6f}", f"{p:.4f}"])
            else:
                bad = bad_groups(d, self.exp_groups(), self.assign())
                group_of = {k: gi for gi, ats in self.assign().items() if gi not in bad for k in ats}
                w.writerow(["atom", "nucleus", "A_iso [MHz]", "A_iso [G]", "B_aa [MHz]", "B_bb [MHz]", "B_cc [MHz]",
                            "assigned group"])
                for k, (iso, mhz, gauss) in sorted(d["fermi"].items()):
                    b = d["dipole"].get(k) or [("", "")] * 3
                    w.writerow([k + 1, iso, f"{mhz:.5f}", f"{gauss:.5f}"] + [x[0] for x in b]
                               + [int(group_of[k]) + 1 if k in group_of else ""])
        return Path(path)

    # -- Oberfläche ----------------------------------------------------------------------------
    def _data_card(self):
        """Karte „Rechnung (DFT)“ im Schritt Daten: Gaussian-Ausgabe und Orbitaldatei."""
        g = QGroupBox(T("epr_calc_box"))
        f = make_form(g)
        self.ed_file, self.ed_orb = QLineEdit(), QLineEdit()
        rows = ((self.ed_file, "epr_calc_file", self.pick_file, "epr_calc_file_ph"),
                (self.ed_orb, "epr_calc_orb", self.pick_orb, "epr_calc_orb_ph"))
        for ed, key, fn, ph in rows:
            ed.setReadOnly(True)
            ed.setPlaceholderText(T(ph))
            b = QPushButton(T("choose"))
            b.clicked.connect(fn)
            file_w = 100                                   # Feld + Knopf zusammen genau die Wertespalte (wie X-Ray)
            ed.setFixedWidth(STYLE.VALUE_W - 8 - file_w)
            b.setFixedWidth(file_w)
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(ed)
            row.addWidget(b)
            f.addRow(T(key), row)
            ed.setToolTip(T(key + "_tip"))
        self.lbl_calc = STYLE.HintLabel("")
        self.lbl_calc.setWordWrap(True)
        self.lbl_calc.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(self.lbl_calc)
        self.btn_remove = QPushButton(STYLE.icon("trash"), T("epr_calc_remove"))
        self.btn_remove.clicked.connect(self.remove)
        f.addRow("", self.btn_remove)
        return g

    def _assign_card(self):
        """Karte „Hyperfein-Zuordnung“ (Schritt Auswertung): Gruppe wählen, dann ihre Kerne im Bild anklicken."""
        g = QGroupBox(T("epr_calc_assign"))
        f = make_form(g)
        self.cmb_sim = QComboBox()
        self.cmb_sim.setToolTip(T("epr_calc_sim_tip"))
        self.cmb_sim.activated.connect(self.changed)
        f.addRow(T("epr_calc_sim"), self.cmb_sim)
        self.tbl_groups = QTableWidget(0, 4)
        self.tbl_groups.setHorizontalHeaderLabels([T("epr_calc_group"), T("epr_calc_exp"), T("epr_calc_atoms"), T("epr_calc_mean")])
        self.tbl_groups.verticalHeader().setVisible(False)
        self.tbl_groups.verticalHeader().setDefaultSectionSize(STYLE.CHECK_ROW_H)
        self.tbl_groups.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_groups.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_groups.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_groups.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)   # Atome nehmen den Rest,
        self.tbl_groups.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)               # übrige: STYLE.fit_columns
        self.tbl_groups.itemSelectionChanged.connect(self.row_selected)
        STYLE.empty_note(self.tbl_groups, T("epr_calc_no_groups"))
        f.addRow(self.tbl_groups)
        self.lbl_assign = STYLE.HintLabel("")
        self.lbl_assign.setWordWrap(True)
        self.lbl_assign.setStyleSheet(STYLE.HINT_CSS)
        self.lbl_assign.linkActivated.connect(self.show_page)   # Klick auf „Hyperfein“ zeigt den Reiter (nichts von selbst)
        f.addRow(self.lbl_assign)
        self.btn_clear = QPushButton(T("epr_calc_clear"))
        self.btn_clear.setToolTip(T("epr_calc_clear_tip"))
        self.btn_clear.clicked.connect(self.clear_group)
        f.addRow("", self.btn_clear)
        self.btn_es = QPushButton(STYLE.icon("export"), T("epr_calc_es"))
        self.btn_es.setToolTip(T("epr_calc_es_tip"))
        self.btn_es.clicked.connect(lambda _=False: self.save_easyspin())
        f.addRow("", self.btn_es)
        for b in (self.btn_clear, self.btn_es):            # zwei Knöpfe untereinander: gleich breit
            b.ensurePolished()
        w = max(b.sizeHint().width() for b in (self.btn_clear, self.btn_es))
        for b in (self.btn_clear, self.btn_es):
            b.setMinimumWidth(w)
        return g

    def _display_card(self):
        """Karte „Spindichte und Hyperfein“ (Schritt Darstellung)."""
        st = self.tab.st
        g = QGroupBox(T("epr_calc_display"))
        f = make_form(g)
        self.cmb_surface = QComboBox()
        for s in SURFACES:
            self.cmb_surface.addItem(T("epr_calc_surf_" + s), s)
        self.cmb_surface.setToolTip(T("epr_calc_surface_tip"))
        self.cmb_surface.setCurrentIndex(max(0, self.cmb_surface.findData(st["spin_surface"])))
        f.addRow(T("epr_calc_surface"), self.cmb_surface)
        self.sp_iso = QDoubleSpinBox()
        self.sp_iso.setDecimals(4)
        self.sp_iso.setRange(0.0001, 10.0)
        self.sp_iso.setSingleStep(0.001)
        self.sp_iso.setSuffix(" a.u.")
        f.addRow(T("epr_calc_iso"), self.sp_iso)
        self.sp_alpha = QDoubleSpinBox()
        self.sp_alpha.setRange(0.1, 1.0)
        self.sp_alpha.setSingleStep(0.05)
        self.sp_alpha.setValue(st["spin_alpha"])
        f.addRow(T("epr_calc_alpha"), self.sp_alpha)
        from matplotlib.colors import to_hex
        plus, minus_ = self.colors()
        row = QHBoxLayout()
        row.setSpacing(8)
        for key, col in (("spin_plus", plus), ("spin_minus", minus_)):   # positiv, negativ (Tooltip)
            b = TABS.color_button(to_hex(col), lambda c, key=key: self.set_color(key, c))
            b.setToolTip(T("epr_calc_" + key))
            row.addWidget(b)
        row.addStretch(1)
        f.addRow(T("epr_calc_colors"), row)
        self.sp_thresh = QDoubleSpinBox()
        self.sp_thresh.setRange(0.0, 100.0)
        self.sp_thresh.setDecimals(1)
        self.sp_thresh.setSuffix(" %")
        self.sp_thresh.setValue(st["spin_thresh"])
        self.sp_thresh.setToolTip(T("epr_calc_thresh_tip"))
        f.addRow(T("epr_calc_thresh"), self.sp_thresh)
        self.cmb_unit = QComboBox()
        for u in UNITS:
            self.cmb_unit.addItem(u, u)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["hfc_unit"])))
        f.addRow(T("epr_calc_unit"), self.cmb_unit)
        self.ed_nuclei = QLineEdit(st["hfc_nuclei"])
        self.ed_nuclei.setPlaceholderText(T("epr_calc_nuclei_ph"))
        self.ed_nuclei.setToolTip(T("epr_calc_nuclei_tip"))
        f.addRow(T("epr_calc_nuclei"), self.ed_nuclei)
        self.sp_min = QDoubleSpinBox()
        self.sp_min.setRange(0.0, 10000.0)
        self.sp_min.setDecimals(1)
        self.sp_min.setSuffix(" MHz")
        self.sp_min.setValue(st["hfc_min"])
        self.sp_min.setToolTip(T("epr_calc_min_tip"))
        f.addRow(T("epr_calc_min"), self.sp_min)
        self.cb_signed = QCheckBox(T("epr_calc_signed"))
        self.cb_signed.setToolTip(T("epr_calc_signed_long"))
        self.cb_signed.setChecked(st["hfc_signed"])
        self.cb_signed.toggled.connect(self.changed)
        self.cb_dipole = QCheckBox(T("epr_calc_dipole"))
        self.cb_dipole.setToolTip(T("epr_calc_dipole_long"))
        self.cb_dipole.setChecked(st["hfc_dipole"])
        self.cb_dipole.toggled.connect(self.changed)
        row = QHBoxLayout()
        row.addWidget(self.cb_signed)
        row.addWidget(self.cb_dipole)
        row.addStretch(1)
        f.addRow(row)
        for w in (self.sp_iso, self.sp_alpha, self.sp_thresh, self.sp_min):
            w.valueChanged.connect(self.changed)
        self.cmb_surface.currentIndexChanged.connect(self.surface_changed)
        self.cmb_unit.currentIndexChanged.connect(self.changed)
        self.ed_nuclei.editingFinished.connect(self.changed)
        self._iso_of = None
        self._sync_iso()
        return g

    def _page(self, kind):
        """Reiter: Abbildung über der Tabelle aller Atome, „Kopieren“ oben rechts; ohne Rechnung ein Platzhalter."""
        g = QGroupBox(T("epr_calc_tab_" + kind))
        v = QVBoxLayout(g)
        content = _Page(lambda kind=kind: self.shown(kind))
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        fig = self.figs[kind] = MplFigure(figsize=(6.3, 4.3), dpi=TABS.PREVIEW_DPI)
        canvas = self.canvases[kind] = register_canvas(FigureCanvasQTAgg(fig))
        host = self.hosts[kind] = TABS.CanvasHost(canvas, fig, margin=0)
        host.setMinimumHeight(260)
        cv.addWidget(host, 4)                              # das Bild hat Vorrang, die Tabelle rollt
        hint = self.hints[kind] = STYLE.SciLabel("")
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)
        cv.addWidget(hint)
        heads = self.headers(kind)
        t = self.tables[kind] = STYLE.FitGrid(0, len(heads))
        t.setHorizontalHeaderLabels(heads)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cv.addWidget(t, 1)
        stack = self.stacks[kind] = QStackedWidget()
        none = STYLE.SciLabel("", T("epr_calc_start"))
        none.setWordWrap(True)
        stack.addWidget(none)
        stack.addWidget(content)
        v.addWidget(stack, 1)
        self.pages[kind] = content
        b = STYLE.copy_button(T("epr_calc_copy_tip"))
        b.clicked.connect(lambda _=False, kind=kind: self.copy_table(kind))
        STYLE.card_actions(g, b)
        return g

    def _sync_iso(self):
        surf = self.cmb_surface.currentData()
        self.sp_iso.blockSignals(True)
        self.sp_iso.setEnabled(surf in ISO_DEFAULT)
        if surf in ISO_DEFAULT:
            self.sp_iso.setValue(self.tab.st[surf + "_iso"])
        self.sp_iso.blockSignals(False)
        self._iso_of = surf

    def surface_changed(self, *_):
        self._iso_of = None                                # das Feld zeigt gleich den Isowert der neuen Fläche
        self.changed()
        self._sync_iso()

    def set_color(self, key, c):
        self.tab.st[key] = c
        self.changed()

    def sync(self):
        """Karten nach dem Zustand (Dateien, Simulationen, Zuordnung)."""
        self._loading = True
        c = self.calc
        self.ed_file.setText(Path(c["file"]).name if c["file"] else "")
        self.ed_orb.setText(Path(c["orb"]).name if c["orb"] else "")
        self.btn_remove.setEnabled(bool(c["file"] or c["orb"]))
        info = ""
        try:
            d = self.data()
            if d is not None:
                cc = d["calc"]
                info = (self.level(d) or "–") + "\n" + T("epr_calc_info", charge=cc["charge"], mult=cc["mult"],
                                                           n=len(d["spin"]))
            elif c["file"]:
                info = T("epr_calc_missing", f=Path(c["file"]).name)
        except Exception as ex:
            info = str(ex)
        self.lbl_calc.setText(info)
        sims = self.sims()
        self.cmb_sim.clear()
        for uid, e in sims:
            self.cmb_sim.addItem(e["label"], uid)
        cur = self.sim()
        self.cmb_sim.setCurrentIndex(max(0, self.cmb_sim.findData(cur["uid"])) if cur else -1)
        self.fill_groups()
        self._loading = False

    def fill_groups(self):
        row = self.row()
        groups, assign, unit = self.exp_groups(), self.assign(), self.tab.st["hfc_unit"]
        d = None
        try:
            d = self.data()
        except Exception:
            pass
        t = self.tbl_groups
        t.blockSignals(True)
        t.setHorizontalHeaderLabels([T("epr_calc_group"), f"{T('epr_calc_exp')} [{unit}]", T("epr_calc_atoms"),
                                     f"{T('epr_calc_mean')} [{unit}]"])      # Einheit im Kopf, nicht in den Zellen
        t.setRowCount(len(groups))
        notes, bad = [], (bad_groups(d, groups, assign) if d is not None else [])
        for i, (n, name, exp) in enumerate(groups):
            ats = [k for k in assign.get(str(i), []) if d is not None and k in d["fermi"]]
            if str(i) in bad:                              # Atome zeigen, Mittel nicht: Zuordnung gilt nicht
                notes.append(T("fixt_epr_assign_bad", group=f"{n} × {iso_text(name)}"))
            mean = (num(float(np.mean([calc_value(d['fermi'][k], unit) for k in ats])), UNITS[unit])
                    if ats and str(i) not in bad else "")
            cells = (f"{n} × {iso_text(name)}", exp, ", ".join(self.atom_name(d, k) for k in ats), mean)
            for j, v in enumerate(cells):
                t.setItem(i, j, QTableWidgetItem(v))
                t.item(i, j).setToolTip(v)                 # lange Atomlisten: ganz im Tooltip
            if ats and len(ats) != n and str(i) not in bad:
                notes.append(T("epr_calc_count", group=cells[0], n=n, m=len(ats)))
        if row is not None and row < len(groups):
            t.selectRow(row)
        t.blockSignals(False)
        STYLE.fit_columns(t)                               # Nebenspalten nach Inhalt mit Luft, wie alle Listen links
        t.setFixedHeight(t.horizontalHeader().sizeHint().height() + max(1, len(groups)) * STYLE.CHECK_ROW_H + 2)
        self.btn_clear.setEnabled(self.row() is not None)
        self.btn_es.setEnabled(bool(d is not None and d["fermi"]))
        self.lbl_assign.setText("\n".join("⚠ " + x for x in notes) if notes
                                else (T("epr_calc_assign_hint_link") if groups and d is not None else ""))

    def show_page(self, kind="hfc"):
        """Reiter `kind` rechts zeigen (Link im Hinweis der Zuordnung; Nutzer: Ansicht wechselt nur auf Klick)."""
        rt, g = self.tab.right_tabs, self.groups[kind]
        j = next((k for k in range(rt.count()) if rt.widget(k) is g or rt.widget(k).isAncestorOf(g)), -1)
        if j >= 0:
            rt.setCurrentIndex(j)

    def row(self):
        r = self.tbl_groups.currentRow()
        return r if r >= 0 and self.tbl_groups.selectionModel().hasSelection() else None

    def row_selected(self):
        if self._loading:
            return
        self.btn_clear.setEnabled(self.row() is not None)
        self.dirty["hfc"] = True
        self.shown("hfc")                                  # Auswahlringe der Gruppe im Bild

    def toggle_atom(self, k, add_only=False):
        """Atom k der gewählten Gruppe zuordnen bzw. wieder herausnehmen (nur Kerne des passenden Elements)."""
        gi, groups = self.row(), self.exp_groups()
        d = self.data()
        if gi is None or gi >= len(groups) or d is None:
            return self.hints["hfc"].setText(T("epr_calc_pick_group"), plain=True)
        if d["els"][k] != nucleus_el(groups[gi][1]):
            return self.hints["hfc"].setText(T("epr_calc_wrong_el", atom=self.atom_name(d, k),
                                               group=iso_text(groups[gi][1])), plain=True)
        assign = self.assign()
        if k in assign.get(str(gi), []):
            if add_only:
                return
            assign[str(gi)].remove(k)
        else:
            for ats in assign.values():                    # ein Kern gehört zu höchstens einer Gruppe
                if k in ats:
                    ats.remove(k)
            assign.setdefault(str(gi), []).append(k)
            assign[str(gi)].sort()
        self.fill_groups()
        self.changed()

    def clear_group(self):
        gi = self.row()
        if gi is not None and self.assign().pop(str(gi), None):
            self.fill_groups()
            self.changed()

    def hover(self, kind, k):
        d = self.data() if self.has_data() else None
        if d is None or k is None:
            return
        txt = f"{self.atom_name(d, k)}: {pct_label(percents(d['spin'])[k])}"
        f = d["fermi"].get(k)
        if f:
            txt += f", A_iso({iso_text(f[0])}) = {num(f[1], 2)} MHz"
        self.hints[kind].setText(txt, plain=True)

    def copy_table(self, kind):
        d = self.data() if self.has_data() else None
        if d is None:
            return
        QApplication.clipboard().setText("\n".join("\t".join(r) for r in [self.headers(kind)] + self.rows(kind, d)))

    # -- Dateien -------------------------------------------------------------------------------
    def _pick(self, title, flt):
        t = self.tab
        if not t.main.ensure_project():
            return None
        p, _ = QFileDialog.getOpenFileName(t, title, t.main.settings.value("last_dir", ""), flt)
        return p or None

    def pick_file(self):
        p = self._pick(T("epr_calc_file"), f"Gaussian, ORCA (*.log *.out);;{T('flt_all')}")
        if p:
            self.load_file(p)

    def pick_orb(self):
        p = self._pick(T("epr_calc_orb"), f"{T('dft_orb_flt')} (*.cube *.cub *.molden *.input);;{T('flt_all')}")
        if p:
            self.load_orb(p)

    def load_file(self, p):
        """Gaussian-/ORCA-Ausgabe prüfen und übernehmen; eine Orbitaldatei mit anderer Geometrie wird gelöst."""
        t = self.tab
        try:
            parse_epr(read_text(p))
        except Exception as ex:
            t.main.error(f"{Path(p).name}: {ex}")
            return False
        p = t.main.import_file(p, PRJ.data_sub(t.STATE_KEY))
        c = self.calc
        if c["file"] != p:
            c.update(file=p, assign={})
        if c["orb"] and not self.orb_fits(c["orb"]):
            c["orb"] = ""
            t.add_note(T("epr_calc_orb_mismatch"))
        self.sync()
        self.changed()
        return True

    def orb_fits(self, p):
        try:
            return DFT.cube_fits(self.frame(self.data()), self.orb_frame(p))
        except Exception:
            return False

    def load_orb(self, p):
        """Molden-/Cube-Datei: nur mit denselben Atomen und Koordinaten (± 0.02 Å) wie die Rechnung."""
        t = self.tab
        if not self.has_data():
            t.main.error(T("epr_calc_need_file"))
            return False
        try:
            if DFT.is_molden(p):
                self.basis(p)
            ok = DFT.cube_fits(self.frame(self.data()), self.orb_frame(p))
        except Exception as ex:
            t.main.error(f"{Path(p).name}: {ex}")
            return False
        if not ok:
            t.main.error(f"{Path(p).name}: {T('epr_calc_orb_mismatch')}")
            return False
        self.calc["orb"] = t.main.import_file(p, PRJ.data_sub(t.STATE_KEY))
        self.sync()
        self.changed()
        return True

    def remove(self):
        self.calc.update(file="", orb="", assign={}, layout={})
        self.sync()
        self.changed()

    # -- Zeichnen ------------------------------------------------------------------------------
    def refresh(self):
        """Nach jeder Änderung: sichtbare Seite neu zeichnen, die andere beim nächsten Anzeigen."""
        for k in self.KINDS:
            self.dirty[k] = True
            self.stacks[k].setCurrentIndex(1 if self.has_data() else 0)
            self.shown(k)

    def shown(self, kind):
        if self.dirty[kind] and self.pages[kind].isVisible():
            self.dirty[kind] = False
            QTimer.singleShot(0, self.pages[kind], lambda: self.draw(kind))

    def draw(self, kind):
        m = self.mouse.pop(kind, None)
        if m:
            m.disconnect()
        fig, notes, F = self.figs[kind], [], None
        QApplication.setOverrideCursor(Qt.WaitCursor)      # Spindichte aus der Molden-Datei: einige Sekunden
        try:
            F = self.build(fig, kind)
            d = self.data()
            rows = self.rows(kind, d) if d is not None else []
        except Exception as ex:
            notes, rows = [str(ex)], []
            fig.clear()
        finally:
            QApplication.restoreOverrideCursor()
        self.F[kind] = F
        if F is not None:
            self.mouse[kind] = XRAY.XrayMouse(F, _Mouse(self, kind))
        t = self.tables[kind]
        heads = self.headers(kind)                         # Einheit und Dipolspalten folgen den Einstellungen
        t.setColumnCount(len(heads))
        t.setHorizontalHeaderLabels(heads)
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                t.setItem(i, j, QTableWidgetItem(v))
        if kind == "hfc":                                  # ohne Zuordnung keine leere Spalte „Gruppe“
            t.setColumnHidden(t.columnCount() - 1, not any(r[-1] for r in rows))
        # nie höher als ihre Zeilen: bei wenigen Atomen bekommt das Bild den Platz
        head = t.horizontalHeader().sizeHint().height()
        t.setMaximumHeight(head + sum(t.rowHeight(i) for i in range(len(rows))) + 4)
        t.setMinimumHeight(head + sum(t.rowHeight(i) for i in range(min(4, len(rows)))) + 4)   # nie eine halbe Zeile
        t.fit()
        if kind == "spin" and F is not None and self.tab.st["spin_surface"] != "none" and not self.calc["orb"]:
            notes.append(T("epr_calc_no_orb"))
        d = self.data() if F is not None else None
        if d is not None and d.get("unchecked"):
            notes.append(T("epr_calc_orca_unchecked"))
        if kind == "hfc" and d is not None and d["calc"]["program"] == "ORCA":
            if not d["fermi"]:
                notes.append(T("epr_calc_orca_no_hfc"))
            elif self.tab.st["hfc_dipole"] and set(d["fermi"]) - set(d["dipole"]):
                notes.append(T("epr_calc_orca_no_dipole"))
        self.hints[kind].setText("\n".join("⚠ " + n for n in notes), plain=True)
        self.hosts[kind].set_figure_size(*fig.get_size_inches())
        self.canvases[kind].draw_idle()

    # -- Export / SI ---------------------------------------------------------------------------
    def figures(self):
        """Vorhandene Abbildungen: Spindichte immer, Kopplungen nur mit Beschriftungen."""
        try:
            d = self.data()
        except Exception as ex:                          # im Export melden (der Tab zeigt den Fehler in der Karte)
            self.tab.main.skip_part(ex, self.calc["file"])
            return []
        if d is None:
            return []
        return ["spin"] + (["hfc"] if d["fermi"] and self.items(d) else [])

    def _offscreen(self, kind):
        fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
        FigureCanvasAgg(fig)
        return self.build(fig, kind, interactive=False)

    def export_to(self, base: Path):
        """<base>_spin/_hfc in den Formaten des Tabs und je eine CSV mit allen Atomen."""
        files, kinds = [], self.figures()
        for kind in kinds:
            F = self._offscreen(kind)
            out = base.with_name(f"{base.name}_{kind}")
            F.cfg["output"] = str(PRJ.with_ext(out, "." + F.cfg["_main_fmt"]))
            files += F.export()
            files.append(self.write_csv(kind, PRJ.with_ext(out, ".csv")))
        script = base.with_name(matlab_script_name(base.name))
        try:
            txt = self.easyspin_text() if "hfc" in kinds else None
        except Exception as ex:                          # nur das Skript fehlt, die Exportmeldung nennt es mit Grund
            self.tab.main.skip_part(ex, part=script.name)
            txt = None
        if txt:
            files.append(script)
            script.write_text(txt, encoding="ascii", newline="\n")
        return files

    def si_figures(self, out_dir, name):
        """SI: [("image", …), ("figcap", …)] je Abbildung, eng um das Molekül beschnitten."""
        out = []
        for kind in self.figures():
            svg = Path(out_dir) / f"{core.safe_name(name)}_epr_{kind}.svg"
            out += [("image",) + XRAY.save_tight(self._offscreen(kind), svg), ("figcap", self.caption(kind, name))]
        return out
