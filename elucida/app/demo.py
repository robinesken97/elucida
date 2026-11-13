"""Beispielprojekt mit **künstlichen Daten** für alle Tabs (Hilfe → Beispielprojekt öffnen, README-Screenshots).

Keine Messdateien, keine gemessenen Werte: zwei erfundene Verbindungen (`COMPOUNDS`), deren Daten in allen Tabs zum
selben Molekül gehören und zueinander passen, aus eigenen Generatoren (feste Startwerte). Das Projekt liegt im
Datenordner des Programms und wird bei jedem Öffnen neu angelegt.
"""
from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path

import numpy as np

from elucida.tabs import nmr as NMR
from elucida.app import project as PRJ
from elucida.tabs import epr as EPR
from elucida.core import images as IMG
from elucida.tabs import sec as SEC
from elucida.tabs import xray as XRAY
from elucida.formats.bruker_ms import BAF_LINE_MAGIC


def write_dta(path, cycles, rate, cycle_col=False, times=None):
    """Gamry-.DTA wie im Selbsttest (Spalten Pt, T, Vf, Im, Vu; Strom in µA übergeben)."""
    head = ["EXPLAIN", "TAG\tCV", "DATE\tLABEL\t1/1/2026\tDate", "TIME\tLABEL\t12:00:00\tTime",
            f"SCANRATE\tQUANT\t{rate:.5E}\t&Scan Rate (mV/s)", "AREA\tQUANT\t7.10000E-002\tElectrode &Area (cm^2)",
            "CONVENTION\tIQUANT\t1\tCurrent Convention"]
    cols = "\tPt\tT\tVf\tIm\tVu" + ("\tCycle" if cycle_col else "")
    units = "\t#\ts\tV vs. Ref.\tA\tV" + ("\t#" if cycle_col else "")
    body = [f"CURVE\tTABLE\t{sum(len(c[0]) for c in cycles)}", cols, units] if cycle_col else []
    pt = 0
    for n, (E_, I_) in enumerate(cycles):
        if not cycle_col:
            body += [f"CURVE{n + 1}\tTABLE", cols, units]
        for e_, i_ in zip(E_, I_):
            t_ = times[pt] if times is not None else pt * 0.02
            body.append(f"\t{pt}\t{t_:.2f}\t{e_:.5E}\t{i_ * 1e-6:.5E}\t0" + (f"\t{n}" if cycle_col else ""))
            pt += 1
    Path(path).write_text("\r\n".join(head + body) + "\r\n", encoding="latin-1", newline="")


def write_cycling(d, name, q_theo_mAh, current_A, fractions, ce, e12=0.6, cuts=(1.0, 0.2), points=40, skip=()):
    """Künstliche Gamry-Lade/Entlade-Messung (Cyclic Charge Discharge) in Ordner d: Hauptdatei <name>.DTA mit
    Kapazitätstabelle + CHARGE_DISCHARGE/CHARGE_#n.DTA, DISCHARGE_#n.DTA (Nernst-Form, Sprung zum Abbruchpotential am
    Ende). fractions: geladener Anteil von Q_theo je Zyklus, ce: Entladen/Laden je Zyklus. skip: (Art, Zyklus)
    ohne Schrittdatei. -> Pfad der Hauptdatei."""
    d = Path(d)
    (d / "CHARGE_DISCHARGE").mkdir(parents=True, exist_ok=True)
    head = ["EXPLAIN", "TAG\t{tag}", "TITLE\tLABEL\t{title}\tTest &Identifier", "DATE\tLABEL\t1/1/2026\tDate",
            "TIME\tLABEL\t12:00:00\tTime", "PSTAT\tPSTAT\tDEMO-1\tPotentiostat",
            f"CAPACITY\tQUANT\t{q_theo_mAh / 1000:.5E}\tCapacity (A-hr)", f"CYCLES\tIQUANT\t{len(fractions)}\tNumber of Cycles",
            f"CHARGEMODE\tMULTIPARAM\t0\t{current_A:.5E}\tCharge Mode\tConstant Current\tAmp(s)",
            f"CHARGECURRENT\tQUANT\t{current_A}\tCharge Current (A)",
            f"CHARGESTOPAT1\tMULTIPARAM\t4\t{cuts[0]:.5E}\tCharge Stop At &1\tVoltage > Limit\tV",
            f"DISCHARGEMODE\tMULTIPARAM\t0\t{current_A:.5E}\t&Discharge Mode\tConstant Current\tAmp(s)",
            f"DISCHARGESTOPAT1\tMULTIPARAM\t3\t{cuts[1]:.5E}\tDischarge Stop At &1\tVoltage < Limit\tV"]
    t, pt, rows = 0.0, 1, []
    for n, (fr, c) in enumerate(zip(fractions, ce), 1):
        for kind, typ, q in (("CHARGE", 0, fr * q_theo_mAh * 3.6), ("DISCHARGE", 1, fr * c * q_theo_mAh * 3.6)):
            dur = q / current_A
            x = np.linspace(0.03, 0.97, points)
            sign = 1 if typ == 0 else -1
            E = e12 + sign * (0.0257 * np.log(x / (1 - x)) + 0.03)
            E[-1] = cuts[typ]
            ts = np.linspace(dur / points, dur, points)
            if (kind.lower(), n) not in skip:
                body = [f"CURVE\tTABLE\t{points}", "\tPt\tT\tVf\tIm\tVu\tPwr\tSig\tAch\tTemp\tIERange\tOver",
                        "\t#\ts\tV\tA\tV\tW\tV\tV\tdeg C\t#\tbits"]
                body += [f"\t{k}\t{tk:.3f}\t{ek:.5E}\t{sign * current_A:.5E}\t0\t0\t0\t0\t0\t9\t..........a"
                         for k, (tk, ek) in enumerate(zip(ts, E))]
                body.append(f"STARTTIMEOFFSET\tQUANT\t{t:.4f}\tStart Time Offset (s)")
                txt = "\r\n".join([h.format(tag=f"PWR800_{kind}", title=f"{name} - {kind.title()} Step")
                                   for h in head] + body) + "\r\n"
                (d / "CHARGE_DISCHARGE" / f"{kind}_#{n}.DTA").write_text(txt, encoding="latin-1", newline="")
            t += dur
            rows.append(f"\t{pt}\t{t:.0f}\t{typ}\t{n}\t{q:.6f}\t{dur:.3f}\t{E[0]:.5f}\t{E[-1]:.5f}\t0\t0\t0\t..........a")
            pt += 1
    main = [h.format(tag="PWR800_CYCLICCHARGEDISCHARGE", title=name) for h in head]
    main += ["CAPACITYCURVE\tTABLE", "\tPt\tTime\tType\tCycle\tCharge\tDuration\tVstart\tVend\tEnergy\tTstart\tTend\tOver",
             "\t#\ts\t#\t#\tC\ts\tV\tV\tJ\tdeg C\tdeg C\tbits"] + rows + ["STOPREASON\tLABEL\tCycle Limit\tStop Reason"]
    p = d / f"{name}.DTA"
    p.write_text("\r\n".join(main) + "\r\n", encoding="latin-1", newline="")
    return p


def band_sum(lam, bands):
    """Summe von Gaußbanden (λ_max in nm, Höhe, Breite σ in cm⁻¹): Gauß über der Wellenzahl, wie gemessene
    Banden über der Wellenlänge leicht unsymmetrisch."""
    nu = 1e7 / np.asarray(lam, float)
    return sum(h * np.exp(-0.5 * ((nu - 1e7 / l0) / s) ** 2) for l0, h, s in bands)


def cv_cycles(couples, rate, lo, hi, cycles=1, step=0.002, seed=0):
    """CV reversibler Ein-Elektronen-Paare [(E½ in V, nFAc√D in µA s^½)] von lo nach hi und zurück, Vorschub in mV/s:
    Strom = Halbableitung der Nernst-Oberflächenkonzentration (Grünwald–Letnikov), also i_p ∝ √v und ΔE_p ≈ 58 mV,
    dazu Doppelschichtstrom, schwache Steigung und Rauschen. -> ([(E, I in µA) je Zyklus], Zeiten in s)"""
    up = np.arange(lo, hi + step / 2, step)
    one = np.concatenate([up, up[-2:0:-1]])
    E = np.concatenate([one] * cycles + [up[:1]])
    n, dt_ = len(E), step / (rate / 1000.0)
    wgt = np.cumprod(np.r_[1.0, 1.0 - 1.5 / np.arange(1, n)])
    I = sum(a * np.convolve(1.0 / (1.0 + np.exp(-(E - e0) * SEC.F_RT)), wgt)[:n] for e0, a in couples) / np.sqrt(dt_)
    I += np.where(np.r_[True, np.diff(E) > 0], 1.0, -1.0) * 1.4e-3 * rate + 0.4 * (E - lo)
    I += np.random.default_rng(seed).normal(0, 0.02, n)
    cut = [k * len(one) for k in range(1, cycles)]
    return list(zip(np.split(E, cut), np.split(I, cut))), np.arange(n) * dt_


def make_sec(d, name, e_start, e12, neutral, oxidised, rate=0.0008, n=70):
    """BWSpec-Serie + Gamry-Potential einer Ein-Elektronen-Oxidation in der Dünnschichtzelle (Nernst-Gleichgewicht
    bei jedem Potential): Banden (λ, A, σ in cm⁻¹) der neutralen und der oxidierten Form, Potentiale wie gemessen."""
    d.mkdir(parents=True, exist_ok=True)
    t_start = dt.datetime(2026, 1, 1, 12, 0, 0)
    T_ = np.arange(0.0, n * 15.0 + 100.0, 2.0)
    write_dta(d / f"{name}_SEC.DTA", [(e_start + rate * T_, 1.0 + 0 * T_)], rate * 1000, cycle_col=True, times=T_)
    pix = np.arange(0, 2048)
    lam = 200.0 + 0.35 * pix
    rng = np.random.default_rng(3)
    files = []
    for j in range(n):
        ts = j * 15.0 + 5.0
        x = 1.0 / (1.0 + np.exp(-SEC.F_RT * (e_start + rate * ts - e12)))
        A = (1 - x) * band_sum(lam, neutral) + x * band_sum(lam, oxidised) + rng.normal(0, 0.0015, lam.size)
        hdr = ["File Version;BWSpec4.11_1", f"Date;{(t_start + dt.timedelta(seconds=ts)):%Y-%m-%d %H:%M:%S}",
               "coefs_a0;200", "coefs_a1;0.35", "coefs_a2;0", "coefs_a3;0", "sel_pixel_start;0",
               "Pixel;Wavelength;Wavenumber;Raman Shift;Dark;Reference;Raw data #1;Dark Subtracted #1;%TR #1;"
               "Absorbance #1;Irradiance (W/m^2/nm) #1"]
        rows = [f"{p};   ;   ;   ;0;0;0;0;0;{a:.5f};0;" for p, a in zip(pix, A)]
        f = d / f"{name}_SEC_{j:03d}.txt"
        f.write_text("\r\n".join(hdr + rows), encoding="latin-1", newline="")
        files.append(str(f))
    return files, d / f"{name}_SEC.DTA"


def uvvis_csv(path, name, bands, concs, solvent="THF", seed=0):
    """Cary-CSV einer Verdünnungsreihe (µM, 800–230 nm): Proben „<Name>-<c>uM_<Lösungsmittel>“, Banden (λ, ε, σ)."""
    wl = np.arange(800.0, 229.0, -1.0)
    eps = band_sum(wl, bands)
    rng = np.random.default_rng(seed)
    names = [f"{name}-{c:g}uM_{solvent}".replace(".", "p") for c in concs]
    cols = [eps * c * 1e-6 * rng.normal(1, 0.004) + rng.normal(0, 0.002) + rng.normal(0, 1e-5, wl.size)
            for c in concs]                             # Verdünnungsfehler, Basislinienversatz, Rauschen
    lines = ["".join(f"{n},," for n in names), "".join("Wavelength (nm),Abs," for _ in names)]
    lines += ["".join(f"{x:.6f},{y[i]:.8f}," for y in cols) for i, x in enumerate(wl)]
    lines += ["", names[0], "Instrument  Cary 60"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\r\n".join(lines), encoding="utf-8", newline="")
    return Path(path), names


def cary_csv(path, cols):
    """Cary-WinUV-Export mit Metadaten: cols = [(Name, λ, A, Aufnahmezeit als Text oder None)]; nach den Daten je Probe
    ein Block „<Name>,“ / „<Name>“ / „Collection Time: …“ in der Reihenfolge der Spalten (wie das Gerät)."""
    lines = ["".join(f"{n}," + "," for n, *_ in cols), "".join("Wavelength (nm),Abs," for _ in cols)]
    lines += ["".join(f"{c[1][i]:.6f},{c[2][i]:.8f}," for c in cols) for i in range(len(cols[0][1]))]
    for n, _, _, t in cols:
        lines += ["", f"{n},", n] + ([f"Collection Time: {t}"] if t else []) + ["Instrument  Cary 60", "Y Mode  Abs"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    return Path(path)


def cuvette_photo(path, liquid, uv=False):
    """Gezeichnetes Küvettenfoto: Lösung in der Farbe `liquid` (RGB), unter UV-Licht vor dunklem Hintergrund."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (600, 900), (22, 20, 34) if uv else (190, 185, 175))
    dr = ImageDraw.Draw(im)
    dr.rectangle([240, 100, 360, 200], fill=(25, 25, 25))
    dr.rectangle([220, 200, 380, 820], fill=(70, 72, 96) if uv else (215, 220, 228))
    dr.rectangle([235, 420, 365, 805], fill=tuple(int(v) for v in liquid))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return Path(path)


def tddft_out(path, states):
    """ORCA-Tabelle der Anregungen [(λ in nm, f_osc)]; T² passt zu Energie und Oszillatorstärke."""
    rows = []
    for k, (lam, f) in enumerate(states, 1):
        cm = 1e7 / lam
        t2 = 1.5 * f / (cm / 219474.63)
        rows.append(f"{k:4d}   {cm:7.1f}    {lam:5.1f}   {f:.9f}   {t2:.5f}   {t2 ** 0.5:.5f}   0.00000   0.00000")
    Path(path).write_text("\n".join([
        "-" * 77, "         ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS", "-" * 77,
        "State   Energy    Wavelength  fosc         T2        TX        TY        TZ",
        "        (cm-1)      (nm)                 (au**2)    (au)      (au)      (au)", "-" * 77] + rows + [""]),
        encoding="utf-8")
    return Path(path)


def demo_nmr_svg(path, nucleus, peaks, x_range, solvent=None):
    """Mnova-ähnliches SVG (Achse als Text wie bei Mnova) mit erfundenen Lorentz-Signalen."""
    w, h = 1088, 759
    hi, lo = x_range
    xs = np.linspace(hi, lo, 1600)
    y = np.zeros_like(xs)
    for pos, amp, width in peaks:
        y += amp / (1 + ((xs - pos) / width) ** 2)
    px = 50 + (hi - xs) / (hi - lo) * 990
    py = 690 - y / y.max() * 600
    num, el = "".join(c for c in nucleus if c.isdigit()), "".join(c for c in nucleus if c.isalpha())
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="287.867mm" height="200.819mm" viewBox="0 0 {w} {h}">',
             '<title>MestReNova SVG (demo)</title>',
             '<polyline fill="none" stroke="#000080" stroke-width="1.2" points="'
             + " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(px, py)) + '"/>',
             '<line x1="50" y1="700" x2="1040" y2="700" stroke="#000000"/>']
    step = 1 if hi - lo <= 12 else 20
    for v in np.arange(np.ceil(lo / step) * step, hi + 1e-9, step):
        x = 50 + (hi - v) / (hi - lo) * 990
        parts.append(f'<line x1="{x:.1f}" y1="700" x2="{x:.1f}" y2="706" stroke="#000000"/>')
        parts.append(f'<text x="{x - 6:.1f}" y="722" font-size="12">{v:g}</text>')
    for pos, _, _ in peaks if el == "C" else ():
        x = 50 + (hi - pos) / (hi - lo) * 990
        parts.append(f'<text x="{x:.1f}" y="70" font-size="9" transform="rotate(-90 {x:.1f} 70)">{pos:.2f}</text>')
    if solvent:
        x = 50 + (hi - solvent) / (hi - lo) * 990
        parts.append(f'<text x="{x:.1f}" y="70" font-size="9" transform="rotate(-90 {x:.1f} 70)">'
                     f'{solvent:.2f} CDCl3</text>')
    parts.append(f'<text x="500" y="745" font-size="14">δ <tspan dy="-4" font-size="9">{num}</tspan>'
                 f'<tspan dy="4">{el} (ppm)</tspan></text>')
    parts.append("</svg>")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return Path(path)


def mol_cdxml(m) -> str:
    """CDXML eines RDKit-Moleküls mit 2D-Koordinaten. RDKit 2025.9 (macOS Intel) hat kein MolToCDXMLBlock:
    dann eigene minimale CDXML (Kekulé-Bindungen, 14.4 pt Bindungslänge, y nach unten)."""
    from rdkit import Chem
    if hasattr(Chem, "MolToCDXMLBlock"):
        return Chem.MolToCDXMLBlock(m)
    m = Chem.Mol(m)
    Chem.Kekulize(m, clearAromaticFlags=True)
    pos = m.GetConformer().GetPositions()
    k = 14.4 / 1.5
    n = m.GetNumAtoms()
    xml = ['<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40"><page id="1"><fragment id="1">']
    for a in m.GetAtoms():
        x, y = pos[a.GetIdx()][:2]
        e = a.GetAtomicNum()
        xml.append(f'<n id="{a.GetIdx() + 2}" p="{100 + k * x:.3f} {100 - k * y:.3f}"'
                   + (f' Element="{e}"' if e != 6 else "") + "/>")
    for b in m.GetBonds():
        o = int(b.GetBondTypeAsDouble())
        xml.append(f'<b id="{b.GetIdx() + 2 + n}" B="{b.GetBeginAtomIdx() + 2}" E="{b.GetEndAtomIdx() + 2}"'
                   + (f' Order="{o}"' if o > 1 else "") + "/>")
    xml.append("</fragment></page></CDXML>")
    return "".join(xml)


def mol_3d(smiles, twist=None):
    """Erfundene 3D-Geometrie: RDKit ETKDG (fester Startwert) + MMFF, im Hauptachsensystem der Nicht-H-Atome (x zeigt
    zum ersten Atom, y zum ersten N). twist=(a, b): Den Rest hinter b um die Achse a→b drehen, bis die Ringe an a und
    b 8° einschließen (MMFF lässt Arylalkine beliebig verdreht, Kristall und DFT sind fast planar).
    -> (Molekül mit H, Koordinaten in Å)"""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    m = Chem.AddHs(Chem.MolFromSmiles(smiles))
    AllChem.EmbedMolecule(m, randomSeed=7)
    AllChem.MMFFOptimizeMolecule(m, maxIters=2000)
    P = m.GetConformer().GetPositions()
    if twist:
        a, b = twist
        ax = (P[b] - P[a]) / np.linalg.norm(P[b] - P[a])

        def normal(i):                                  # Ringebene am Atom i, senkrecht zur Achse
            n1, n2 = [x.GetIdx() for x in m.GetAtomWithIdx(i).GetNeighbors() if x.IsInRing()]
            v = np.cross(P[n1] - P[i], P[n2] - P[i])
            v -= (v @ ax) * ax
            return v / np.linalg.norm(v)
        na, nb = normal(a), normal(b)
        ang = np.radians(8.0) - np.arctan2(np.cross(na, nb) @ ax, na @ nb)
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K
        dist = Chem.GetDistanceMatrix(m)
        side = dist[b] < dist[a]
        P[side] = P[b] + (P[side] - P[b]) @ R.T
    heavy = [x.GetIdx() for x in m.GetAtoms() if x.GetAtomicNum() > 1]
    P = P - P[heavy].mean(0)
    v = np.linalg.eigh(P[heavy].T @ P[heavy])[1][:, ::-1]
    v[:, 0] *= np.sign(P[0] @ v[:, 0])
    v[:, 1] *= np.sign(P[next(x.GetIdx() for x in m.GetAtoms() if x.GetAtomicNum() == 7)] @ v[:, 1])
    v[:, 2] = np.cross(v[:, 0], v[:, 1])
    return m, P @ v


def _euler(a, b, c):
    ca, sa, cb, sb, cc, sc = np.cos(a), np.sin(a), np.cos(b), np.sin(b), np.cos(c), np.sin(c)
    return (np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
            @ np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]))


def atom_labels(m):
    """C1, C2 …, N1 … in der Reihenfolge des Moleküls; H nach seinem Atom (H3, bei mehreren H8A, H8B …)."""
    count, lab = {}, {}
    for a in m.GetAtoms():
        if a.GetAtomicNum() > 1:
            count[a.GetSymbol()] = count.get(a.GetSymbol(), 0) + 1
            lab[a.GetIdx()] = f"{a.GetSymbol()}{count[a.GetSymbol()]}"
    for a in m.GetAtoms():
        hs = [x.GetIdx() for x in a.GetNeighbors() if x.GetAtomicNum() == 1]
        for k, h in enumerate(hs):
            lab[h] = "H" + lab[a.GetIdx()][len(a.GetSymbol()):] + ("ABC"[k] if len(hs) > 1 else "")
    return [lab[i] for i in range(m.GetNumAtoms())]


P21C = ("x, y, z", "-x, y+1/2, -z+1/2", "-x, -y, -z", "x, -y-1/2, z-1/2")
_SIGMA_MO = {"H": 0.62, "C": 11.5, "N": 19.6}       # Absorptionsquerschnitte für Mo-Kα (barn), gerundet


def make_cif(path, name, m, P, cell, place):
    """Erfundene Kristallstruktur (P2₁/c, Z = 4, ganzes Molekül in der asymmetrischen Einheit) aus der Geometrie
    P: Lage `place` (drei Drehwinkel, Verschiebung in Zellbruchteilen; vorab ohne zu kurze Kontakte gesucht), H
    reitend (0.95/0.98 Å), anisotrope U der Nicht-H-Atome, Abstände und Winkel mit esd. Dichte, F(000), µ, Zahl der
    Reflexe und Parameter folgen aus Zelle und Formel; R-Werte erfunden. Kein echter Datensatz."""
    import math
    Z, lam, th = 4, 0.71073, 27.5
    M = XRAY.ortho_matrix(*cell)
    Mi = np.linalg.inv(M)
    V = float(np.linalg.det(M))
    X = P @ _euler(*place[:3]).T
    for a in m.GetAtoms():                              # reitende H-Atome wie nach der Verfeinerung
        if a.GetAtomicNum() == 1:
            par = a.GetNeighbors()[0]
            v = X[a.GetIdx()] - X[par.GetIdx()]
            X[a.GetIdx()] = X[par.GetIdx()] + v / np.linalg.norm(v) * (0.98 if par.GetTotalNumHs() == 3 else 0.95)
    F = X @ Mi.T + np.asarray(place[3:6])
    lab = atom_labels(m)
    el = [a.GetSymbol() for a in m.GetAtoms()]
    heavy = [i for i, e in enumerate(el) if e != "H"]
    rng = np.random.default_rng(5)
    N = np.diag(np.linalg.norm(Mi, axis=1))             # a*, b*, c* (Längen der Zeilen von M⁻¹)
    ueq, uani = {}, {}
    for i in heavy:
        u0 = 0.021 + 0.0026 * np.linalg.norm(P[i]) + (0.006 if m.GetAtomWithIdx(i).GetTotalNumHs() == 3 else 0.0)
        d = u0 * rng.permutation([0.82, 1.0, 1.18])
        o = rng.uniform(-0.004, 0.004, 3)
        U = np.array([[d[0], o[2], o[1]], [o[2], d[1], o[0]], [o[1], o[0], d[2]]])
        uani[i] = U
        ueq[i] = float(np.trace(M @ N @ U @ N @ M.T)) / 3
    comp = {e: el.count(e) for e in sorted(set(el))}
    mass = sum(a.GetMass() for a in m.GetAtoms())
    q = 2 * math.sin(math.radians(th)) / lam
    n_uniq = int(round(4 / 3 * math.pi * q ** 3 * V / 4 * 0.995))
    hkl = [int(q * x) for x in cell[:3]]
    L = [f"data_{name}", f"_chemical_formula_sum '{' '.join(f'{e}{n}' for e, n in comp.items())}'",
         f"_chemical_formula_weight {mass:.2f}",
         "_space_group_crystal_system monoclinic", "_space_group_name_H-M_alt 'P 21/c'",
         "loop_", "  _space_group_symop_operation_xyz"] + [f" '{o}'" for o in P21C]
    L += [f"_cell_length_a {cell[0]:.4f}(3)", f"_cell_length_b {cell[1]:.4f}(9)", f"_cell_length_c {cell[2]:.4f}(4)",
          "_cell_angle_alpha 90", f"_cell_angle_beta {cell[4]:.3f}(2)", "_cell_angle_gamma 90",
          f"_cell_volume {V:.2f}(9)", f"_cell_formula_units_Z {Z}",
          f"_exptl_crystal_density_diffrn {Z * mass / (0.602214 * V):.3f}",
          f"_exptl_absorpt_coefficient_mu {Z * sum(_SIGMA_MO[e] * n for e, n in comp.items()) / V / 10:.3f}",
          f"_exptl_crystal_F_000 {Z * sum(a.GetAtomicNum() for a in m.GetAtoms())}",
          "_exptl_crystal_size_max 0.28", "_exptl_crystal_size_mid 0.12", "_exptl_crystal_size_min 0.06",
          "_diffrn_ambient_temperature 100(2)", f"_diffrn_radiation_wavelength {lam}",
          "_diffrn_reflns_theta_min 2.410", f"_diffrn_reflns_theta_max {th:.3f}"]
    for ax, h in zip("hkl", hkl):
        L += [f"_diffrn_reflns_limit_{ax}_min {-h}", f"_diffrn_reflns_limit_{ax}_max {h}"]
    L += [f"_diffrn_reflns_number {int(round(n_uniq * 7.3))}", f"_reflns_number_total {n_uniq}",
          "_diffrn_reflns_av_R_equivalents 0.0358", "_diffrn_reflns_av_unetI/netI 0.0271",
          "_refine_ls_structure_factor_coef Fsqd", "_refine_ls_matrix_type full",
          f"_refine_ls_number_reflns {n_uniq}", "_refine_ls_number_restraints 0",
          f"_refine_ls_number_parameters {9 * len(heavy) + 1}", "_refine_ls_goodness_of_fit_ref 1.043",
          "_refine_ls_R_factor_gt 0.0412", "_refine_ls_wR_factor_gt 0.0987", "_refine_ls_R_factor_all 0.0536",
          "_refine_ls_wR_factor_ref 0.1058", "_refine_diff_density_max 0.24", "_refine_diff_density_min -0.21",
          "loop_", "  _atom_site_label", "  _atom_site_type_symbol", "  _atom_site_fract_x", "  _atom_site_fract_y",
          "  _atom_site_fract_z", "  _atom_site_U_iso_or_equiv", "  _atom_site_adp_type", "  _atom_site_occupancy",
          "  _atom_site_disorder_group"]
    for i in heavy + [i for i in range(len(el)) if i not in heavy]:
        f = F[i]
        if el[i] == "H":
            par = m.GetAtomWithIdx(i).GetNeighbors()[0]
            u = (1.5 if par.GetTotalNumHs() == 3 else 1.2) * ueq[par.GetIdx()]
            L.append(f" {lab[i]} H {f[0]:.5f} {f[1]:.5f} {f[2]:.5f} {u:.3f} Uiso 1 .")
        else:
            L.append(f" {lab[i]} {el[i]} {f[0]:.5f}(18) {f[1]:.5f}(5) {f[2]:.5f}(13) {ueq[i]:.4f}(3) Uani 1 .")
    L += ["loop_", "  _atom_site_aniso_label"] + [f"  _atom_site_aniso_U_{k}" for k in ("11", "22", "33", "23", "13", "12")]
    for i in heavy:
        U = uani[i]
        L.append(f" {lab[i]} " + " ".join(f"{v:.4f}({e})" for v, e in zip(
            (U[0, 0], U[1, 1], U[2, 2], U[1, 2], U[0, 2], U[0, 1]), (6, 6, 7, 5, 5, 5))))
    C = F @ M.T                                         # Abstände und Winkel aus den geschriebenen Lagen
    dist = lambda i, j: float(np.linalg.norm(C[i] - C[j]))                           # noqa: E731
    L += ["loop_", "  _geom_bond_atom_site_label_1", "  _geom_bond_atom_site_label_2", "  _geom_bond_distance",
          "  _geom_bond_site_symmetry_2", "  _geom_bond_publ_flag"]
    for b in m.GetBonds():
        i, j = sorted((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))
        L.append(f" {lab[i]} {lab[j]} " + (f"{dist(i, j):.4f}" if "H" in (el[i], el[j]) else f"{dist(i, j):.4f}(18)")
                 + " . ?")
    L += ["loop_", "  _geom_angle_atom_site_label_1", "  _geom_angle_atom_site_label_2",
          "  _geom_angle_atom_site_label_3", "  _geom_angle", "  _geom_angle_site_symmetry_1",
          "  _geom_angle_site_symmetry_3", "  _geom_angle_publ_flag"]
    for j in heavy:
        nb = sorted(x.GetIdx() for x in m.GetAtomWithIdx(j).GetNeighbors() if x.GetAtomicNum() > 1)
        for k, i in enumerate(nb):
            for l_ in nb[k + 1:]:
                u, v = C[i] - C[j], C[l_] - C[j]
                ang = math.degrees(math.acos(u @ v / np.linalg.norm(u) / np.linalg.norm(v)))
                L.append(f" {lab[i]} {lab[j]} {lab[l_]} {ang:.2f}(12) . . ?")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L + [""]), encoding="utf-8", newline="\n")
    return Path(path)


def make_orca(path, name, m, P, energy, method="B3LYP D4 def2-TZVP", solvent=("thf", "7.2500", "TETRAHYDROFURAN"),
              homo_lumo=(-5.12, -1.62), imag=None):
    """ORCA-6-Ausgabe (nur die gelesenen Abschnitte, Format wie `DFT.make_test_orca`; Zahlen erfunden) einer
    Optimierung + Frequenzrechnung mit der Geometrie P: Minimum (keine imaginäre Frequenz), Nullpunktsenergie aus
    den Frequenzen, Enthalpie und freie Enthalpie daraus fortgeschrieben, Orbitalenergien mit HOMO/LUMO in eV
    (`homo_lumo`). imag [cm⁻¹]: Übergangszustand, die tiefste Mode wird diese eine imaginäre Frequenz (zählt nicht
    zur Nullpunktsenergie). Kein echter Datensatz."""
    el = [a.GetSymbol() for a in m.GetAtoms()]
    n = len(el)
    geo = [f"  {e:<2s}  {x:12.6f} {y:12.6f} {z:12.6f}" for e, (x, y, z) in zip(el, P)]
    n_ch, n_cc = el.count("H"), sum(b.GetBondTypeAsDouble() == 3 for b in m.GetBonds())
    rng = np.random.default_rng(11)
    low = np.sort(28.0 + (1640.0 - 28.0) * np.linspace(0, 1, 3 * n - 6 - n_ch - n_cc) ** 1.15
                  + rng.uniform(-6, 6, 3 * n - 6 - n_ch - n_cc))
    fr = np.r_[np.zeros(6), np.abs(low), 2190.0 + 25.0 * np.arange(n_cc),
               np.sort(2935.0 + 265.0 * rng.uniform(0, 1, n_ch))]
    if imag:
        fr[6] = -abs(imag)
    zpe = fr[fr > 0].sum() / 2 / 219474.63
    u = energy + zpe + 0.00072 * n                       # thermische Korrektur grob je Atom
    h = u + 0.00094421
    ts = 0.0235 + 0.00093 * n
    L = ["", "                                 *****************", "                                 * O   R   C   A *",
         "                                 *****************", "", "                 Program Version 6.1.1 -  RELEASE  -",
         "", "=" * 80, "                                       INPUT FILE", "=" * 80, f"NAME = {name}.inp",
         "|  1> %pal nprocs 16 end", f"|  2> ! {method} TightOpt Freq CPCM({solvent[0]})", "|  3> * xyz 0 1"]
    L += [f"|{i + 4:3d}> {g.strip()}" for i, g in enumerate(geo)]
    L += [f"|{n + 4:3d}> *", f"|{n + 5:3d}> " + "                        ****END OF INPUT****",
          "", " Total Charge           Charge          ....    0", " Multiplicity           Mult            ....    1",
          "", "CPCM SOLVATION MODEL", "--------------------", "CPCM parameters:",
          f"  Epsilon                                         ...       {solvent[1]}",
          f"Solvent:                                          ... {solvent[2]}", "",
          "CPCM Dielectric    :         -0.00918273645501 Eh              -0.24988 eV", "",
          "          ----------------------|Geometry convergence|-------------------------",
          "          Item                value                   Tolerance       Converged",
          "          ---------------------------------------------------------------------",
          "          Energy change      -0.0000001400            0.0000010000      YES",
          "          RMS gradient        0.0000092000            0.0000300000      YES",
          "          MAX gradient        0.0000310000            0.0001000000      YES",
          "          RMS step            0.0001700000            0.0006000000      YES",
          "          MAX step            0.0006400000            0.0010000000      YES",
          "          ---------------------------------------------------------------------", "",
          "                    ***********************HURRAY********************",
          "                    ***        THE OPTIMIZATION HAS CONVERGED     ***", "",
          "---------------------------------", "CARTESIAN COORDINATES (ANGSTROEM)",
          "---------------------------------"] + geo
    # Orbitalenergien (ORCA, Nummern ab 0): Rümpfe, Valenzleiter bis zum HOMO, virtuelle ab dem LUMO; erfunden
    n_occ = sum(a.GetAtomicNum() for a in m.GetAtoms()) // 2
    core = sorted((-14.35 if e == "N" else -10.21) - 0.004 * k for k, e in enumerate(el) if e != "H")
    occ = core + list(np.linspace(-1.02, homo_lumo[0] / 27.211386, n_occ - len(core)))
    virt = homo_lumo[1] / 27.211386 + 0.031 * np.arange(12) ** 1.1
    L += ["", "----------------", "ORBITAL ENERGIES", "----------------", "",
          "  NO   OCC          E(Eh)            E(eV) "]
    L += [f"{k:4d}   {2.0 if k < n_occ else 0.0:.4f}   {e:14.6f}   {e * 27.211386:14.4f}"
          for k, e in enumerate(occ + list(virt))]
    L += ["", "-------------------------   --------------------", f"FINAL SINGLE POINT ENERGY     {energy:.12f}", "",
          "-----------------------", "VIBRATIONAL FREQUENCIES", "-----------------------", ""]
    L += [f"   {i:3d}:   {v:9.2f} cm**-1" + ("  ***imaginary mode***" if v < 0 else "") for i, v in enumerate(fr)]
    L += ["", "--------------------------", "THERMOCHEMISTRY AT 298.15K", "--------------------------", "",
          "Temperature         ...   298.15 K", "Pressure            ...     1.00 atm",
          "Quasi RRHO          ...     True",
          f"Electronic energy                ...   {energy:.8f} Eh",
          f"Zero point energy                ...      {zpe:.8f} Eh     {zpe * 627.5095:.2f} kcal/mol",
          f"Total thermal energy                   {u:.8f} Eh",
          f"Total Enthalpy                    ...   {h:.8f} Eh",
          "Point Group:  C1, Symmetry Number:   1  ",
          f"Final entropy term                ...      {ts:.8f} Eh     {ts * 627.5095:.2f} kcal/mol",
          f"Final Gibbs free energy         ...   {h - ts:.8f} Eh",
          f"G-E(el)                           ...      {h - ts - energy:.8f} Eh     "
          f"{(h - ts - energy) * 627.5095:.2f} kcal/mol", "",
          "                             ****ORCA TERMINATED NORMALLY****"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return Path(path)


# CASSCF(4,4)/SC-NEVPT2 von S3 (erfunden): je Multiplizität (Wurzel, E_CASSCF, E_NEVPT2 [Eh], Konfigurationen). S1
# liegt mit NEVPT2 3.40 eV über S0 (nahe der Bande bei 372 nm), T1 2.60 eV; CASSCF überschätzt die Abstände wie üblich.
MR_STATES = {1: [(0, -721.152340, -723.598120, ((0.88213, 0, "2200"), (0.05871, 5, "2020"))),
                 (1, -721.001640, -723.473170, ((0.84102, 1, "2110"), (0.07330, 3, "1210"))),
                 (2, -720.968640, -723.440120, ((0.79855, 3, "1210"), (0.10234, 1, "2110")))],
             3: [(0, -721.042140, -723.502620, ((0.95521, 0, "2110"),)),
                 (1, -721.005340, -723.469520, ((0.93017, 1, "1210"),))]}


def make_mr(path, name, m, P):
    """ORCA-6-Ausgabe einer CASSCF(4,4)-Rechnung (3 Singuletts, 2 Tripletts, natürliche Orbitale) mit SC-NEVPT2 auf der
    Geometrie P, nur die Abschnitte, die `formats.multireference.parse_orca_mr` und `formats.calc` lesen; alle Zahlen
    erfunden (`MR_STATES`), kein echter Datensatz."""
    el = [a.GetSymbol() for a in m.GetAtoms()]
    geo = [f"  {e:<2s}  {x:12.6f} {y:12.6f} {z:12.6f}" for e, (x, y, z) in zip(el, P)]
    n_occ = sum(a.GetAtomicNum() for a in m.GetAtoms()) // 2
    n = len(el)
    L = ["", "                 Program Version 6.1.1 -  RELEASE  -", "", "=" * 80, "                                       INPUT FILE",
         "=" * 80, f"NAME = {name}.inp", "|  1> %pal nprocs 16 end", "|  2> ! def2-TZVP def2-TZVP/C RIJCOSX",
         "|  3> %casscf nel 4 norb 4 mult 1,3 nroots 3,2 PTMethod SC_NEVPT2 ActOrbs NatOrbs end", "|  4> * xyz 0 1"]
    L += [f"|{i + 5:3d}> {g.strip()}" for i, g in enumerate(geo)]
    L += [f"|{n + 5:3d}> *", f"|{n + 6:3d}> " + "                        ****END OF INPUT****", "",
          " Total Charge           Charge          ....    0", " Multiplicity           Mult            ....    1", "",
          "---------------------------------", "CARTESIAN COORDINATES (ANGSTROEM)", "---------------------------------"]
    L += geo + ["", "ORCA-CASSCF", "", "Number of active electrons          ... 4",
                "Number of active orbitals           ... 4", f"Active {n_occ - 2} - {n_occ + 1} (4 orbitals)",
                "Max. number of iterations           ... 100", "Active Orbitals                     ... natural",
                "A PT2 calculation will be performed (PT2 = SC-NEVPT2)", "",
                "           ---- THE CAS-SCF ENERGY   HAS CONVERGED ----", "", "---------------", "CASSCF RESULTS",
                "---------------", "", f"Final CASSCF energy       : {MR_STATES[1][0][1]:.10f} Eh", ""]
    for blk, (mult, states) in enumerate(MR_STATES.items()):
        L += ["", "---------------------------------------------",
              f"CAS-SCF STATES FOR BLOCK  {blk + 1} MULT= {mult} NROOTS= {len(states)}",
              "---------------------------------------------", ""]
        for root, e_cas, _, conf in states:
            L += [f"ROOT   {root}:  E=    {e_cas:.10f} Eh"] + [f"      {w:.5f} [{k:5d}]: {o}" for w, k, o in conf] + [""]
    L += ["", "=" * 80, "                  NEVPT2 Results", "=" * 80, ""]
    for mult, states in MR_STATES.items():
        for root, e_cas, e_pt, _ in states:
            L += ["---------------", f"MULT {mult}, ROOT {root}", "---------------",
                  f"Reference Energy                 : E0 = {e_cas:.12f}",
                  f"Total Energy Correction          : dE = {e_pt - e_cas:.12f}",
                  f"Total Energy (E0+dE)             : E = {e_pt:.12f}", ""]
    L += ["TIMINGS NEVPT2", "", "-------------------------   --------------------",
          f"FINAL SINGLE POINT ENERGY     {MR_STATES[1][0][2]:.12f}", "",
          "                             ****ORCA TERMINATED NORMALLY****"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return Path(path)


# Reaktionspfad des Beispielprojekts (erfunden): Hydratisierung von S3 zum Keton über das Enol, ΔE_el [kcal/mol]
# relativ zum Komplex S3·H2O (ΔG folgt mit den erfundenen Frequenzen: 0.0, 34.8, −6.2, −21.6); Übergangszustand mit
# genau einer imaginären Frequenz. Name, SMILES, ΔE_el, imaginäre Frequenz [cm⁻¹].
PATH_SPECIES = (("S3·H2O", "Cc1ccc(C#Cc2ccc(N(C)C)cc2)nc1.O", 0.0, None),
                ("TS", None, 36.8, 1432.6),
                ("Enol", "Cc1ccc(/C=C(\\O)c2ccc(N(C)C)cc2)nc1", -4.2, None),
                ("Ketone", "Cc1ccc(CC(=O)c2ccc(N(C)C)cc2)nc1", -19.6, None))
PATH_E0 = -805.981234           # E_el des Komplexes [Eh], erfunden


def make_path(w, pdir, inp):
    """Reaktionspfad „Hydration of S3“ im Projekt: vier ORCA-Ausgaben (Opt/Freq, erfunden) als Plateaus in Schrittfolge,
    ΔG-Profil und Vorschau der Karte. Der Übergangszustand ist die Enol-Geometrie mit gestreckter C–O-Bindung."""
    from elucida.app import reaction_paths as RP
    item = RP.create(pdir, "Hydration of S3")
    host = RP.PathHost(w, pdir, item)
    try:
        geos = {}
        for label, smi, _, _ in PATH_SPECIES:
            if smi:
                geos[label] = mol_3d(smi)
        m, P = geos["Enol"]                                # TS: O–H des Enols 0.55 Å vom Kohlenstoff weg
        P = P.copy()
        o = next(a for a in m.GetAtoms() if a.GetSymbol() == "O")
        c = next(a.GetIdx() for a in o.GetNeighbors() if a.GetSymbol() == "C")
        v = (P[o.GetIdx()] - P[c]) / np.linalg.norm(P[o.GetIdx()] - P[c])
        P[[o.GetIdx()] + [a.GetIdx() for a in o.GetNeighbors() if a.GetSymbol() == "H"]] += 0.55 * v
        geos["TS"] = (m, P)
        from elucida.tabs.dft import new_entry
        for k, (label, _, dg, imag) in enumerate(PATH_SPECIES):         # wie „Rechnungen laden“, ohne je Datei zu zeichnen
            stem = f"S3_hydration_{k + 1}_{label.replace('·', '-')}"
            p = make_orca(inp / "path" / f"{stem}.out", stem, *geos[label], PATH_E0 + dg / 627.5095, imag=imag)
            host.tab.entries().append(new_entry(host.import_file(str(p), PRJ.data_sub("dft"))))
        host.tab.st["current"] = host.tab.entries()[0]["uid"]
        prof = host.tab.pages.prof
        prof["species"] ={e["uid"]: dict(label=s[0], step=k) for k, (e, s) in enumerate(zip(host.tab.entries(),
                                                                                             PATH_SPECIES))}
        prof.update(mode="levels", y="G")
        host.save()
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        fig = Figure()
        FigureCanvasAgg(fig)
        F, _ = host.tab.pages.build(fig)
        if F:                                              # Vorschau der Karte wie beim Schließen eines Pfads
            fig.savefig(host.project_dir / "preview.png", dpi=70, facecolor="white")
    finally:
        host.dispose()
    return item


PAGE_W, PAGE_H, PAGE_MARGIN = 540.0, 720.0, 36.0   # ChemDraw-Seite wie PRJ.EMPTY_CDXML (ACS 1996)
_XY_ATTRS = ("p", "Head3D", "Tail3D", "Center3D", "MajorAxisEnd3D", "MinorAxisEnd3D")


def cdxml_extent(root) -> tuple[float, float, float, float]:
    """Umriss (x0, y0, x1, y1) aller Objekte auf den Seiten; Texte grob über Schriftgröße und Zeichenzahl."""
    xs, ys = [], []
    for page in root.iter("page"):
        for el in page.iter():
            if el.tag == "page":
                continue
            for a in _XY_ATTRS[:3]:                 # Center3D/Achsen (Bogenpfeile) zählen nicht zum Umriss
                if el.get(a):
                    v = [float(t) for t in el.get(a).split()]
                    xs.append(v[0])
                    ys.append(v[1])
            if el.tag == "t" and el.get("p") and not el.get("BoundingBox"):
                x, y = map(float, el.get("p").split()[:2])
                size = max([float(s.get("size", 10)) for s in el.iter("s")] or [10.0])
                n = len("".join(s.text or "" for s in el.iter("s")))
                xs.append(x + 0.6 * size * n)
                ys.append(y - size)
            if el.get("BoundingBox") and el.tag != "page":
                v = [float(t) for t in el.get("BoundingBox").split()]
                xs += v[0::2]
                ys += v[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def fit_to_page(text: str) -> str:
    """CDXML so verschieben, dass alles auf der ersten ChemDraw-Seite liegt (RDKit schreibt Koordinaten um 0, ChemDraw
    zeigt dann nur den unteren Rand oben an der Seite). Nur Verschiebung: Zeichnung und Chemie bleiben gleich.
    Dazu Seitenangaben wie ChemDraw (Dokument-BoundingBox, PrintMargins, Seite 540 × 720 pt)."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(text)
    x0, y0, x1, y1 = cdxml_extent(root)
    dx = round((PAGE_W - (x1 - x0)) / 2 - x0, 2)                  # mittig, bei ACS-Größe innerhalb der Druckränder
    dy = round(PAGE_MARGIN * 1.5 - y0, 2)
    fmt = lambda v: f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    for page in root.iter("page"):
        for el in page.iter():
            if el.tag == "page":
                continue
            for a in _XY_ATTRS:
                if el.get(a):
                    v = [float(t) for t in el.get(a).split()]
                    v[0] += dx
                    v[1] += dy
                    el.set(a, " ".join(fmt(t) for t in v))
            if el.get("BoundingBox"):
                v = [float(t) for t in el.get("BoundingBox").split()]
                el.set("BoundingBox", " ".join(fmt(t + (dx if k % 2 == 0 else dy)) for k, t in enumerate(v)))
    root.set("BoundingBox", f"{fmt(x0 + dx)} {fmt(y0 + dy)} {fmt(x1 + dx)} {fmt(y1 + dy)}")
    root.set("PrintMargins", " ".join([fmt(PAGE_MARGIN)] * 4))
    for page in root.iter("page"):
        page.set("BoundingBox", f"0 0 {fmt(PAGE_W)} {fmt(PAGE_H)}")
        page.attrib.update(HeaderPosition="36", FooterPosition="36", HeightPages="1", WidthPages="1")
    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(root, encoding="unicode")


ACS_BOND = 14.4                                    # Bindungslänge ACS Document 1996 (pt)


def _scale_fragment(fr, bond=ACS_BOND):
    """Koordinaten eines Fragments auf die Bindungslänge `bond` skalieren (RDKit schreibt 28.8 pt)."""
    import statistics
    pos = {n.get("id"): tuple(map(float, n.get("p").split()[:2])) for n in fr.iter("n")}
    ls = [((pos[b.get("B")][0] - pos[b.get("E")][0]) ** 2 + (pos[b.get("B")][1] - pos[b.get("E")][1]) ** 2) ** 0.5
          for b in fr.iter("b")]
    k = bond / statistics.median(ls) if ls else 1.0
    for n in fr.iter("n"):
        x, y = pos[n.get("id")]
        n.set("p", f"{k * x:.2f} {k * y:.2f}")
    return fr


def acs_document(*children) -> str:
    """CDXML mit den Dokumenteinstellungen der leeren ACS-1996-Vorlage (PRJ.EMPTY_CDXML) um die Seitenobjekte."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(PRJ.EMPTY_CDXML.split("?>", 1)[1].split(">", 1)[1])   # ohne XML-Kopf und DOCTYPE
    root.set("CreationProgram", "Elucida")
    page = root.find("page")
    for c in children:
        page.append(c)
    return ET.tostring(root, encoding="unicode")


def acs_cdxml(text: str) -> str:
    """Einzelstruktur (RDKit-CDXML) in ACS-1996-Größe auf der ersten Seite."""
    import xml.etree.ElementTree as ET
    frags = [_scale_fragment(f) for f in ET.fromstring(text).iter("fragment")]
    return fit_to_page(acs_document(*frags))


def _formula_runs(t, text, size=10.0):
    """Text als <s>-Läufe wie ChemDraw-Formelstil: Ziffern nach Buchstaben/Klammern tiefgestellt (face 32)."""
    import re
    import xml.etree.ElementTree as ET
    for m in re.finditer(r"(?<=[A-Za-z)])\d+|(?:(?<![A-Za-z)])\d|[^\d])+", text):
        sub = m.group(0)[0].isdigit() and m.start() > 0 and re.match(r"[A-Za-z)]", text[m.start() - 1])
        ET.SubElement(t, "s", {"font": "3", "size": f"{size:g}", "color": "0",
                               "face": "32" if sub else "0"}).text = m.group(0)
    return t


def scheme_cdxml(path, reactants=("C[Si](C)(C)C#Cc1ccc(C)cn1",), product="Cc1ccc(C#C)nc1", above="K2CO3 (1.2 eq.)",
                 below="MeOH, rt, 1 h"):
    """Erfundenes Schema (Vorgabe: TMS-Entschützung eines Alkins): Edukte mit „+“ dazwischen, ein Pfeil mit Text
    darüber und darunter, Produkt (RDKit-CDXML, auf ACS 1996 skaliert) – Lage und Pfeil wie von ChemDraw geschrieben."""
    import xml.etree.ElementTree as ET
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from elucida.formats import cdxml as CDXD

    def frag(smiles, offset):
        m = Chem.MolFromSmiles(smiles)
        AllChem.Compute2DCoords(m)
        fr = _scale_fragment(ET.fromstring(mol_cdxml(m)).find(".//fragment"))
        ids = {o.get("id"): str(offset + k) for k, o in enumerate(fr.iter()) if o.get("id")}
        for o in fr.iter():
            if o.get("id"):
                o.set("id", ids[o.get("id")])
            if o.tag == "b":
                o.set("B", ids[o.get("B")])
                o.set("E", ids[o.get("E")])
        return fr

    def box(fr):
        xy = [tuple(map(float, n.get("p").split())) for n in fr.iter("n")]
        return (min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy))

    def move(fr, dx, dy):
        for n in fr.iter("n"):
            x, y = map(float, n.get("p").split())
            n.set("p", f"{x + dx:.2f} {y + dy:.2f}")

    size = 10.0
    width = lambda t: sum(CDXD._font(False).text_length(s.text, fontsize=size * (0.75 if s.get("face") == "32"
                                                                                  else 1.0)) for s in t.iter("s"))
    left = [frag(smi, 1000 * (k + 1)) for k, smi in enumerate(reactants)]
    f2 = frag(product, 1000 * (len(left) + 1))
    b1 = box(left[0])
    ay = (b1[1] + b1[3]) / 2                                     # Pfeil auf halber Höhe der Edukte
    plus, x = [], b1[2]
    for k, fr in enumerate(left[1:]):                            # weitere Edukte rechts daneben, „+“ dazwischen
        t = _formula_runs(ET.Element("t"), "+", size)
        w = width(t)
        t.attrib.update({"id": str(510 + k), "p": f"{x + 8.0 + w / 2:.2f} {ay + 0.36 * size:.2f}", "Z": str(510 + k),
                         "BoundingBox": f"{x + 8.0:.2f} {ay - 0.36 * size:.2f} {x + 8.0 + w:.2f} {ay + 0.36 * size:.2f}",
                         "CaptionJustification": "Center", "Justification": "Center", "InterpretChemically": "no"})
        plus.append(t)
        b = box(fr)
        move(fr, x + 16.0 + w - b[0], ay - (b[1] + b[3]) / 2)
        x = box(fr)[2]
    b2 = box(f2)
    move(f2, 0, ay - (b2[1] + b2[3]) / 2)
    t1 = _formula_runs(ET.Element("t"), above, size)
    t2 = _formula_runs(ET.Element("t"), below, size)
    w_txt = max(width(t1), width(t2))
    tail = x + 8.0
    head = tail + max(w_txt + 18.0, 43.2)                        # Text frei von der Pfeilspitze
    cx = (tail + head) / 2
    for t, i, base in ((t1, "501", ay - 5.0), (t2, "502", ay + 4.0 + 0.72 * size)):
        w = width(t)
        t.attrib.update({"id": i, "p": f"{cx:.2f} {base:.2f}", "Z": i,
                         "BoundingBox": f"{cx - w / 2:.2f} {base - 0.72 * size:.2f} {cx + w / 2:.2f} "
                                        f"{base + (0.25 if t is t1 else 0.21) * size:.2f}",
                         "CaptionJustification": "Center", "Justification": "Center", "InterpretChemically": "no"})
    b2 = box(f2)
    move(f2, head + 8.0 - b2[0], 0)
    L = head - tail
    arrow = ET.Element("arrow", {
        "id": "503", "BoundingBox": f"{tail:.2f} {ay - 1.88:.2f} {head:.2f} {ay + 1.88:.2f}", "Z": "503",
        "FillType": "None", "ArrowheadHead": "Full", "ArrowheadType": "Solid", "HeadSize": "1000",
        "ArrowheadCenterSize": "875", "ArrowheadWidth": "250",
        "Head3D": f"{head:.2f} {ay:.2f} 0", "Tail3D": f"{tail:.2f} {ay:.2f} 0",
        "Center3D": f"{cx:.2f} {ay:.2f} 0", "MajorAxisEnd3D": f"{cx + L / 2:.2f} {ay:.2f} 0",
        "MinorAxisEnd3D": f"{cx:.2f} {ay + L / 2:.2f} 0"})
    scheme = ET.fromstring(f'<scheme id="504"><step id="505" '
                           f'ReactionStepReactants="{" ".join(f.get("id") for f in left)}" '
                           f'ReactionStepProducts="{f2.get("id")}" ReactionStepArrows="503" '
                           'ReactionStepObjectsAboveArrow="501" ReactionStepObjectsBelowArrow="502"/></scheme>')
    Path(path).write_text(fit_to_page(acs_document(*left, f2, *plus, t1, t2, arrow, scheme)), encoding="utf-8")
    return Path(path)


# Zwei erfundene Verbindungen, deren Daten zueinander passen: S2 (Vorstufe, 2-Ethinyl-5-methylpyridin) und S3, ihr
# Sonogashira-Produkt mit 4-Iod-N,N-dimethylanilin (Donor-Akzeptor-Tolan: gelb, fluoresziert blau, reversibel oxidierbar).
# Banden: (λ in nm, ε bzw. A, σ in cm⁻¹); NMR-Signale: (δ, Höhe, Breite); Lage im Kristall: `make_cif`.
_J1, _J2, _J3 = 8.9 / 500 / 2, 8.0 / 500 / 2, 2.1 / 500 / 2          # halbe Aufspaltungen in ppm (500 MHz)
COMPOUNDS = {
    "S2": dict(
        smiles="Cc1ccc(C#C)nc1", formula="C8H7N", mw=117.15, mp="112–114 °C",
        uv=[(284, 6200, 1400), (246, 10400, 1700), (212, 15000, 2200)], concs=(80, 60, 40, 20, 10),
        h1=[(8.38, 1.0, 0.002), (7.50 + _J2, 0.5, 0.002), (7.50 - _J2, 0.5, 0.002), (7.41 + _J2, 0.5, 0.002),
            (7.41 - _J2, 0.5, 0.002), (3.08, 1.0, 0.002), (2.33, 3.0, 0.002), (7.26, 0.15, 0.002)],
        c13=(150.4, 139.9, 136.7, 133.4, 127.1, 82.9, 76.9, 18.4),
        nmr_text="1H NMR (500 MHz, CDCl3) δ 8.38 (s, 1H), 7.50 (d, J = 8.0 Hz, 1H), 7.41 (d, J = 8.0 Hz, 1H), "
                 "3.08 (s, 1H), 2.33 (s, 3H).\n13C NMR (126 MHz, CDCl3) δ 150.4, 139.9, 136.7, 133.4, 127.1, 82.9, "
                 "76.9, 18.4.",
        ir=((3290.0, 35, 10), (2104.0, 20, 6), (1598.0, 40, 8), (1482.0, 45, 6), (1029.0, 30, 8), (823.0, 55, 6)),
        ea={"C": "81.88", "H": "6.07", "N": "11.86"},
        scheme={},
        reagents=[dict(name="S1", M="C11H15NSi", m_mg="947", role="ref"),
                  dict(name="K2CO3", M="K2CO3", m_mg="829", role="reagent"),
                  dict(name="S2", M="C8H7N", m_mg="556", role="product")],
        proc="<b>S1</b> (947 mg, 5.00 mmol, 1.0 eq.) was dissolved in MeOH (10 mL) and K<sub>2</sub>CO<sub>3</sub> "
             "(829 mg, 6.00 mmol, 1.2 eq.) was added. The mixture was stirred at room temperature for 1 h, diluted "
             "with water and extracted with Et<sub>2</sub>O. Drying over MgSO<sub>4</sub> and removal of the solvent "
             "gave <b>S2</b> (556 mg, 4.75 mmol, 95%) as a colourless solid.",
        cell=(3.95, 14.60, 11.60, 90.0, 95.2, 90.0), place=(4.2, 4.141, 2.608, 0.847, 0.267, 0.108)),
    "S3": dict(
        smiles="Cc1ccc(C#Cc2ccc(N(C)C)cc2)nc1", formula="C16H16N2", mw=236.32, mp="141–143 °C", twist=(4, 7),
        uv=[(372, 28000, 2300), (268, 14500, 1900), (215, 22000, 2500)], concs=(30, 20, 10, 5, 2.5),
        h1=[(8.40 + _J3, 0.5, 0.002), (8.40 - _J3, 0.5, 0.002), (7.47 + _J1, 1.0, 0.002), (7.47 - _J1, 1.0, 0.002),
            (7.43 + _J2 + _J3, 0.25, 0.002), (7.43 + _J2 - _J3, 0.25, 0.002), (7.43 - _J2 + _J3, 0.25, 0.002),
            (7.43 - _J2 - _J3, 0.25, 0.002), (7.37 + _J2, 0.5, 0.002), (7.37 - _J2, 0.5, 0.002),
            (6.65 + _J1, 1.0, 0.002), (6.65 - _J1, 1.0, 0.002), (3.00, 6.0, 0.002), (2.34, 3.0, 0.002),
            (7.26, 0.15, 0.002)],
        c13=(150.5, 150.4, 141.2, 136.6, 133.2, 131.6, 126.3, 111.8, 109.2, 90.6, 87.2, 40.2, 18.5),
        nmr_text="1H NMR (500 MHz, CDCl3) δ 8.40 (d, J = 2.1 Hz, 1H), 7.47 (d, J = 8.9 Hz, 2H), 7.43 (dd, J = 8.0, "
                 "2.1 Hz, 1H), 7.37 (d, J = 8.0 Hz, 1H), 6.65 (d, J = 8.9 Hz, 2H), 3.00 (s, 6H), 2.34 (s, 3H).\n"
                 "13C NMR (126 MHz, CDCl3) δ 150.5, 150.4, 141.2, 136.6, 133.2, 131.6, 126.3, 111.8, 109.2, 90.6, "
                 "87.2, 40.2, 18.5.",
        ir=((3038.0, 6, 12), (2916.0, 12, 14), (2858.0, 9, 12), (2806.0, 8, 10), (2205.0, 32, 7), (1605.0, 55, 9),
            (1585.0, 28, 7), (1522.0, 60, 8), (1476.0, 24, 7), (1445.0, 18, 8), (1362.0, 45, 9), (1228.0, 20, 8),
            (1190.0, 30, 7), (1126.0, 16, 7), (1024.0, 14, 6), (945.0, 12, 6), (815.0, 50, 7), (728.0, 13, 6)),
        ea={"C": "81.12", "H": "6.90", "N": "11.74"},
        scheme=dict(reactants=("Cc1ccc(C#C)nc1", "Ic1ccc(N(C)C)cc1"), product="Cc1ccc(C#Cc2ccc(N(C)C)cc2)nc1",
                    above="PdCl2(PPh3)2, CuI", below="NEt3, THF, rt, 16 h"),
        reagents=[dict(name="S2", M="C8H7N", m_mg="586", role="ref"),
                  dict(name="4-iodo-N,N-dimethylaniline", M="C8H10IN", m_mg="1360", role="reagent"),
                  dict(name="PdCl2(PPh3)2", M="C36H30Cl2P2Pd", m_mg="70.2", role="reagent"),
                  dict(name="CuI", M="CuI", m_mg="38.1", role="reagent"),
                  dict(name="S3", M="C16H16N2", m_mg="1030", role="product")],
        proc="<b>S2</b> (586 mg, 5.00 mmol, 1.0 eq.), 4-iodo-<i>N</i>,<i>N</i>-dimethylaniline (1.36 g, 5.50 mmol, "
             "1.1 eq.), PdCl<sub>2</sub>(PPh<sub>3</sub>)<sub>2</sub> (70.2 mg, 2 mol%) and CuI (38.1 mg, 4 mol%) were "
             "dissolved in degassed THF (15 mL) and NEt<sub>3</sub> (5 mL) under argon. The mixture was stirred at "
             "room temperature for 16 h, filtered through Celite and concentrated. Column chromatography "
             "(SiO<sub>2</sub>, cyclohexane/EtOAc 4:1) gave <b>S3</b> (1.03 g, 4.35 mmol, 87%) as a yellow solid.",
        cell=(5.98, 25.10, 9.10, 90.0, 98.3, 90.0), place=(0.046, 2.454, 2.979, 0.569, 0.38, 0.446)),
}
STOCK_UM = 100.0                # Stammlösung der Verdünnungsreihen (µM), fotografiert in der Küvette
E_FC, E_OX = 0.09, 0.47         # CV/SEC von S3 wie gemessen (V gegen Ag/AgNO₃): Fc⁰/⁺ und S3⁰/•⁺ (+0.38 V vs. Fc⁰/⁺)


def load_data(w, inp, name="S3"):
    """Tabs mit den künstlichen Daten einer Verbindung füllen: Synthese, NMR, IR, EA, HRMS (Bericht + .d), UV-Vis und
    X-Ray für beide, Overlay, Kinetik, Fluoreszenz, CV, SEC, H-Zelle, EPR, DFT und Weitere nur für das Produkt S3
    (`load_product`)."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from elucida.core import color as COLOR
    c = COMPOUNDS[name]
    m2 = Chem.MolFromSmiles(c["smiles"])
    AllChem.Compute2DCoords(m2)
    cdxml = inp / f"{name}_structure.cdxml"         # „<Name>.cdxml“ ist die leere ChemDraw-Vorlage der Verbindung
    cdxml.write_text(acs_cdxml(mol_cdxml(m2)), encoding="utf-8")
    # Verbindung mit Zeichnung (Tab „Verbindung“), Formel, Molmasse und Schmelzpunkt (erfunden), damit die Checkliste
    # des Projekts vollständig ist
    w.set_compound({"name": name, "formula": c["formula"], "mw": c["mw"], "mp": c["mp"], "structure": str(cdxml)})
    # UV-Vis (ε): Verdünnungsreihe, Struktur, Küvettenfoto in der Farbe, die das Spektrum ergibt
    csv, samples = uvvis_csv(inp / f"{name}_UV-Vis.csv", name, c["uv"], c["concs"])
    rgb = COLOR.absorbance_to_rgb(band_sum(COLOR.LAM, c["uv"]) * STOCK_UM * 1e-6)[0]
    photo = cuvette_photo(inp / f"{name}_cuvette.png", 255 * np.asarray(rgb) * np.array([215, 220, 228]) / 228)
    w.open_csv(csv, ask=False)
    w.series[name]["color_c"] = STOCK_UM                 # „Farbe in Lösung“: die Stammlösung auf dem Foto
    w.glob["color_show"] = True
    w.apply_globals()
    w.set_structure(str(cdxml), name, render=False, sync=True)
    w.series[name]["bg"] = "grabcut"
    w.set_photo(str(photo), name, render=False, sync=True)
    w.current = name
    w.apply_series_widgets()
    # X-Ray: erfundene Struktur aus der 3D-Geometrie des Moleküls
    m3, P = mol_3d(c["smiles"], c.get("twist"))
    w.xray_tab.load_cif(str(make_cif(inp / "xray" / f"{name}.cif", name, m3, P, c["cell"], c["place"])))
    w.xray_state["current"] = w.xray_state["entries"][0]["uid"]
    # ausgewählte Parameter: C≡C und der Winkel davor (in S2 und S3 dieselben Labels: eine Spalte im Vergleich)
    w.xray_state["entries"][0]["params"] = [{"atoms": ["C6", "C7"]}, {"atoms": ["C5", "C6", "C7"]}]
    # NMR: erfundene Spektren (¹H, ¹³C), Mnova-Text, Struktur
    nd = inp / "nmr"
    h1 = demo_nmr_svg(nd / f"{name}-1H.svg", "1H", c["h1"], (9.5, 0.5))
    c13 = demo_nmr_svg(nd / f"{name}-13C.svg", "13C", [(d, 1.0 - 0.07 * (k % 5), 0.15) for k, d in enumerate(c["c13"])],
                       (170, 0), solvent=77.16)
    t_n = w.nmr_tab
    for p in (h1, c13):
        t_n.load_svg(str(p))
    w.nmr_state["structure"] = w.import_file(str(cdxml), PRJ.STRUCTURES)   # nicht im Temp-Ordner lassen
    # 2D: künstliches TopSpin-HSQC-Experiment (Rohdaten-Reiter, Checkliste „2D NMR“)
    t_n.import_topspin(str(NMR.make_test_acqus(nd / name / "3", nuc="1H", nuc2="13C", pulprog="hsqcedetgpsisp2.3")))
    # IR (künstliche OPUS-Datei), HRMS (künstlicher Bericht der Massenabteilung), Elementaranalyse (erfundene Werte)
    w.irms_tab.load_ir(str(make_opus(inp / "irms" / f"{name}_IR.0", c["ir"])))
    w.hrms_tab.load_ms(str(make_ms_report(inp / "irms" / f"{name}_HRMS.docx", name, c["formula"])))
    w.hrms_tab.load_raw(str(make_bruker_d(inp / "irms" / f"{name}_HRMS.d", name, c["formula"])))   # Spektrum + LC
    w.irms_state["ea_found"] = dict(c["ea"])
    w.nmr_state["text"] = c["nmr_text"]
    w.nmr_state["current"] = t_n.spectra()[0]["uid"]
    # Synthese: erfundenes Schema, Vorschrift, Reagenzien (Mengen passen zueinander)
    (inp / "syn").mkdir(parents=True, exist_ok=True)
    w.syn_tab.set_scheme(str(scheme_cdxml(inp / "syn" / f"{name}_reaction.cdxml", **c["scheme"])))
    w.syn_state["reagents"] = [dict(r) for r in c["reagents"]]
    w.syn_state["proc"] = c["proc"]
    if name == "S3":
        load_product(w, inp, name, csv, samples, photo, m3, P)


def load_product(w, inp, name, csv, samples, photo, m3, P):
    """Overlay, Fluoreszenz, CV, SEC, EPR und DFT des Produkts: derselbe Chromophor (372 nm), dieselbe Oxidation
    (+0.38 V vs. Fc⁰/⁺), deren Radikalkation in SEC und EPR, dieselbe Geometrie wie im Kristall."""
    from elucida.core import uvvis as core
    c = COMPOUNDS[name]
    lam0 = c["uv"][0][0]
    # Overlay: Messung + TD-DFT (erfundene ORCA-Tabelle, stärkster Übergang nahe der gemessenen Bande)
    orca = tddft_out(inp / f"{name}_TD-DFT.out", [(380.2, 0.952), (301.4, 0.061), (266.8, 0.284), (251.3, 0.022)])
    win = dict(nlo=lam0 - 42, nhi=lam0 + 48)
    w.ov_state.update(entries=[
        dict(win, kind="exp", file=str(csv), sample=samples[2], label="exp.", color="#000000", visible=True,
             own_norm=False, conc=c["concs"][2], unit="uM", mw=c["mw"], d=1.0),
        dict(win, kind="calc", file=str(orca), label="TD-DFT", color="#1764e8", visible=True, own_norm=False,
             fwhm=0.3, shift=0.0)], mode="norm", sticks=True, stick_mode="band", **win)
    # Fluoreszenz: verdünnteste Probe der Reihe (A < 0.1 bei λex), ε wie im ε-Tab; Foto unter UV-Licht
    em = inp / f"{name}_emission.csv"
    xs = np.arange(390.0, 701.0, 1.0)
    I_ = 480 * band_sum(xs, [(454, 1.0, 1250), (488, 0.28, 1400)])        # steile blaue Flanke, Maximum 458 nm
    I_ += np.random.default_rng(2).normal(0, 0.03, xs.size)
    em.write_text("\r\n".join([f"{name} EM ex{lam0},,", "Wavelength (nm),Intensity (a.u.),"]
                              + [f"{x:.1f},{y:.3f}," for x, y in zip(xs, I_)]), encoding="utf-8", newline="")
    res = core.prepare_series(w.make_cfg(name), w.groups[name], name)[2]
    eps = min(res, key=lambda r: abs(r["lam"] - lam0))["eps"]
    w.fl_state.update(abs_file=str(csv), abs_sample=samples[-1], em_file=str(em), em_sample=f"{name} EM ex{lam0}",
                      ex=float(lam0), alo=lam0 - 42, ahi=lam0 + 48, eps=f"{eps:.0f}", stokes_label=True,
                      photo_day=str(photo), bg_day="grabcut", bg_uv="none",
                      photo_uv=str(cuvette_photo(inp / f"{name}_cuvette_UV.png", (70, 150, 255), uv=True)))
    # UV-Vis-Kinetik: Stabilität der Lösung über eine Woche, je Tag eine Datei mit zwei Konzentrationen (Zerfall erster
    # Ordnung, k = 0.04 d⁻¹), Aufnahmezeiten im Cary-Format
    from elucida.tabs import uvkin as UVKIN
    wl = np.arange(800.0, 229.0, -1.0)
    eps_ = band_sum(wl, c["uv"])
    rng = np.random.default_rng(7)
    t0 = dt.datetime(2026, 3, 2, 10, 15, 0)
    entries = []
    for day in (0, 1, 2, 3, 5, 7):
        cols = []
        for k, conc in enumerate((20, 10)):
            t = t0 + dt.timedelta(days=day, minutes=3 * k + 7 * day)
            us = f"{t.month}/{t.day}/{t.year} {(t.hour - 1) % 12 + 1}:{t:%M:%S} {'PM' if t.hour >= 12 else 'AM'}"
            A = eps_ * conc * 1e-6 * np.exp(-0.04 * (t - t0).total_seconds() / 86400) * rng.normal(1, 0.003)
            cols.append((f"{name}-{conc}uM_THF", wl, A + rng.normal(0, 0.0015) + rng.normal(0, 1e-4, wl.size), us))
        p = w.import_file(str(cary_csv(inp / "uvkin" / f"{name}_stability_day{day}.csv", cols)), PRJ.data_sub("uvkin"))
        entries += [{"uid": f"kin{day}_{k}", "file": p, "idx": k, "label": f"{n_} day {day}",
                     "series": UVKIN.series_from_name(n_), "use": True} for k, (n_, *_) in enumerate(cols)]
    w.uvkin_state.update(entries=entries, fit=True, cap_solvent="THF")
    # CV: drei Vorschubgeschwindigkeiten + Messung mit Ferrocen als internem Standard (1 mM, D = 1·10⁻⁵ cm² s⁻¹)
    files = []
    for rate in (50, 100, 200):
        p = inp / "cv" / f"{name}_CV_{rate}mVs.DTA"
        p.parent.mkdir(parents=True, exist_ok=True)
        cyc, t = cv_cycles([(E_OX, 21.7)], rate, E_OX - 0.42, E_OX + 0.38, cycles=3, seed=rate)   # ausgewertet: 2.
        write_dta(p, cyc, rate, times=t)
        files.append((p, rate))
    ref = inp / "cv" / f"{name}_CV_Fc.DTA"
    cyc, t = cv_cycles([(E_OX, 21.7), (E_FC, 17.4)], 200, E_FC - 0.40, E_OX + 0.38, cycles=2, seed=1)
    write_dta(ref, cyc, 200, cycle_col=True, times=t)
    w.cv_state["files"] = [{"file": str(p), "uid": f"cv{i}", "visible": True, "color": "#000000",
                            "label": f"{r} mV s-1"} for i, (p, r) in enumerate(files)]
    w.cv_state["files"].append({"file": str(ref), "uid": "cvref", "visible": False, "color": "#000000",
                                "label": "Fc"})
    w.cv_state.update(couples=[[E_OX - 0.2, E_OX + 0.2]], ref_mode="internal", ref_uid="cvref", ref_lo=E_FC - 0.2,
                      ref_hi=E_FC + 0.2, ref_compound="fc", ref_value=0.0, cycle=2, cap_conc="1 mM",
                      cap_solvent="CH2Cl2", cap_el="0.1 M n-Bu4NPF6")
    # SEC: dieselbe Oxidation in der Dünnschichtzelle, Potentiale über die Referenz des CV-Tabs
    sec_files, dta = make_sec(inp / "sec", name, E_FC - 0.09, E_OX, neutral=[(lam0, 0.30, 1900), (268, 0.155, 1900)],
                              oxidised=[(505, 0.24, 1100), (760, 0.13, 1500), (334, 0.11, 1800), (262, 0.14, 2000)])
    w.sec_state.update(spec_files=sec_files, dta=str(dta), mode="spectra", bands=f"{lam0}, 505, 760", trace_lams=f"{lam0}, 505, 760", mid="",
                       ref_from_cv=True, cap_solvent="CH2Cl2", cap_start="neutral", cap_end="radical cation")
    # H-Zelle: symmetrisches Laden/Entladen derselben Oxidation (Konstantstrom, Plateau bei E½ wie im CV, Abbruch
    # ±0.3 V darum), 40 Zyklen mit langsamem Kapazitätsverlust
    rng = np.random.default_rng(7)
    k_ = np.arange(40)
    main_ = write_cycling(inp / "hcell" / f"{name}_cycling", f"{name}_cycling", 0.5, 0.002,
                          0.88 - 0.0018 * k_ + rng.normal(0, 0.002, 40), 0.996 + rng.normal(0, 0.0015, 40),
                          e12=E_OX, cuts=(E_OX + 0.3, E_OX - 0.3))
    w.hcell_state.update(cap_conc="5 mM", cap_solvent="CH2Cl2, 0.1 M n-Bu4NPF6", ref="Ag0/+")   # vor dem Bau des Tabs
    w.hcell_tab.load_files([str(main_)])
    # EPR: Radikalkation (isotrop, S = ½: 1 × 14N, 6 × 1H der NMe2-Gruppe) mit eigener Simulation und Fit
    Bt = np.linspace(328.0, 343.0, 6001)
    I_ = EPR.iso_spectrum(Bt, 9.40, 2.0031, [(1, 1.0, 0.86), (6, 0.5, 0.93)], 0.14)
    I_ += np.random.default_rng(1).standard_normal(len(Bt)) * 0.01 * np.ptp(I_)
    (inp / "epr").mkdir(parents=True, exist_ok=True)
    np.savetxt(inp / "epr" / f"{name}_EPR-9p400000.txt", np.column_stack([Bt, I_]), header="B [mT]\tI [a.U.]",
               comments="", delimiter="\t")
    t_e = w.epr_tab
    er = t_e._new("exp", str(inp / "epr" / f"{name}_EPR-9p400000.txt"))
    w.epr_state.update(entries=[er], bl_order=-1, smooth=0.0, normalize=True, stack=False, show_sum=False,
                       show_residual=False, x_min=328.0, x_max=343.0)
    t_e.fill_table()
    t_e.table.selectRow(0)
    t_e.add_iso()
    w.epr_state["entries"][-1]["nuclei"] = "1 14N 0.85; 6 1H 0.95"     # Startwerte aus dem Linienabstand
    t_e.fill_table()
    t_e.table.selectRow(1)
    t_e.fit_current()
    w.epr_state.update(cap_species=f"{name}^{{•+}}", cap_solvent="CH2Cl2", cap_conc="1 mM")
    # DFT: ORCA-Ausgabe (Optimierung + Frequenzen) mit der Geometrie des Kristalls, dazu HOMO und LUMO als Cube
    # (Namen wie orca_plot, Nummern ab 0; HOMO zuletzt, damit es gezeigt wird)
    w.dft_tab.load_xyz(str(make_orca(inp / "dft" / f"{name}_opt_freq.out", f"{name}_opt_freq", m3, P, -729.512846)))
    atoms, homo, lumo = huckel_frontier(m3, P)
    n_homo = sum(a.GetAtomicNum() for a in m3.GetAtoms()) // 2 - 1
    for no, coef in ((n_homo + 1, lumo), (n_homo, homo)):
        w.dft_tab.load_cube(str(orbital_cube(inp / "dft" / f"{name}_opt_freq.mo{no}a.cube", m3, P, atoms, coef)))
    # Reiter Multireferenz: CASSCF/SC-NEVPT2 auf derselben Geometrie als eigene Rechnung, Ergebnis SC-NEVPT2 gewählt;
    # gezeigt bleibt die Opt/Freq-Rechnung mit ihren Orbitalen (die Seite folgt der gewählten Rechnung)
    opt_uid = w.dft_state["current"]
    w.dft_tab.load_xyz(str(make_mr(inp / "dft" / f"{name}_CASSCF-NEVPT2.out", f"{name}_CASSCF-NEVPT2", m3, P)))
    e_mr = w.dft_tab.entry()
    e_mr["mr_result"] = next(r["id"] for r in w.dft_tab.calc_of(e_mr)["multireference"] if r["method"] == "SC-NEVPT2")
    e_mr.update(mr_singlet=0, mr_triplet=len(MR_STATES[1]))          # ΔE_ST zwischen S0 und T1 (Indizes im Block)
    w.dft_state["current"] = opt_uid
    w.dft_tab.pages.load_nics([str(make_nics(inp / "dft" / f"{name}_NICS-scan.log", m3, P))])     # Reiter NICS
    w.dft_tab.pages.nics["geom"] = "B3LYP-D4/def2-TZVP"
    w.dft_state["h_labels"] = False                   # Orbitalbild: nur Schweratome beschriftet (H bleiben anklickbar)
    # Weitere: Abbildung aus einem anderen Programm (Lippert-Mataga-Auftragung der Emission in fünf Lösungsmitteln)
    w.other_tab.load_files([str(lippert_png(inp / f"{name}_Lippert-Mataga.png"))])
    w.other_state["entries"][-1].update(
        chapter="uvvis", caption=f"Lippert–Mataga plot of {name} (Stokes shift against the orientation "
                                 "polarizability Δf of the solvent).")


DEMO_DIRS = ("Beispielverbindung", "Beispielprojekt", "Beispielpublikation")   # im Datenordner (alte Namen mit)


def make_opus(path, bands=((3290.0, 35, 10), (2104.0, 20, 6), (1598.0, 40, 8), (1482.0, 45, 6), (1029.0, 30, 8),
                            (823.0, 55, 6))) -> Path:
    """Künstliche Bruker-OPUS-Datei (Transmission, 4000–400 cm-1) im Format des Selbsttests: Banden (Wellenzahl,
    Tiefe in %, Breite) mit Lorentz-Anteil, Basislinie fällt wie bei ATR leicht zu kleinen Wellenzahlen, Rauschen."""
    import struct
    wn = np.linspace(3999.0, 400.0, 1800)
    A = sum(dp / 100 * (0.65 * np.exp(-((wn - c) / wd) ** 2) + 0.35 / (1 + ((wn - c) / wd) ** 2)) for c, dp, wd in bands)
    T = (0.995 - 0.02 * (3999.0 - wn) / 3599.0) * (1.0 - A) + np.random.default_rng(4).normal(0, 3e-4, wn.size)

    def par(pairs):
        out = b""
        for nm, typ, val in pairs:
            raw = struct.pack("<i", val) if typ == 0 else struct.pack("<d", val)
            out += nm.encode() + b"\0" + struct.pack("<hh", typ, len(raw) // 2) + raw
        return out + b"END\0" + struct.pack("<hh", 0, 0)
    p_ = par([("NPT", 0, len(wn)), ("FXV", 1, 3999.0), ("LXV", 1, 400.0), ("CSF", 1, 1.0)])
    off_par, off_dat = 24 + 12 * 2, 24 + 12 * 2 + len(p_)
    head = b"\x0a\x0a\xfe\xfe" + struct.pack("<d", 920622.0) + struct.pack("<iii", 24, 2, 2)
    dirs = struct.pack("<BBBBii", 31, 20, 0, 0, len(p_) // 4, off_par) + \
        struct.pack("<BBBBii", 15, 20, 0, 0, len(wn), off_dat)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(head + dirs + p_ + T.astype("<f4").tobytes())
    return Path(path)


def make_ms_report(path, name, formula, adduct="M+H", shift=0.0004) -> Path:
    """Künstlicher Word-Bericht der Massenabteilung (Text + EMF-Beschriftungen wie im echten Bericht): Probe, Formel,
    exakte Masse, ESI; gemessenes m/z = berechnet + shift."""
    import struct
    import zipfile
    from elucida.tabs import ir_ea as IRMS
    calc = IRMS.ion(formula, adduct)[2]
    exact = IRMS.ion(formula, "M+H")[2] - 1.007276467   # neutrale monoisotopische Masse (nur Text im Bericht)
    found = calc + shift

    def emf(texts):
        out = b""
        for t in texts:
            body = t.encode("utf-16-le")
            size = 76 + len(body) + (-(76 + len(body)) % 4)
            rec = bytearray(size)
            struct.pack_into("<II", rec, 0, 84, size)
            struct.pack_into("<II", rec, 44, len(t), 76)
            rec[76:76 + len(body)] = body
            out += bytes(rec)
        return out
    xml = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in
                  ("sample name:", name, "molecular formula:", formula, "exact mass:", f"{exact:.4f}",
                   "method of Ionisation:", "ESI ☒ APCI ☐ HESI ☐"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{xml}</w:body></w:document>")
        z.writestr("word/media/image1.emf", emf(["Chemical Formula:", formula, "Exact Mass:", f"{exact:.4f}"]))
        z.writestr("word/media/image2.emf", emf([f"{found:.4f}", f"{found + 1.0034:.4f}", "x.d: +MS, 0.1-0.4min",
                                                 "m/z"]))
    return Path(path)


BAF_CAL = (20000.0, 0.2, 302.5, 159870.0, 2.61e-4, 0.0, -0.0009)   # erfundene Kalibrierung: Delay, Takt, c0, c1, c2, –, c6


def make_bruker_d(d, name, formula, adduct="M+H", shift=0.0004, seed=0) -> Path:
    """Künstlicher Bruker-Messordner (.d: analysis.baf + analysis.sqlite im Baf2Sql-Schema, nur MS1-Linienspektren):
    LC-Lauf über 2 min, Ion der Formel mit dem berechneten Isotopenmuster im LC-Peak bei 0.9 min, gemessen um `shift`
    (Da, wie im Bericht) neben calc. mit Streuung je Scan, dazu zwei Untergrundionen. Flugzeit-Indizes über die
    Umkehrung der Kalibrierung (`BAF_CAL`, Variante int 10 wie `formats.bruker_ms`). Kein echter Datensatz."""
    import sqlite3
    import struct
    from elucida.tabs import hrms as HRMS
    from elucida.tabs import ir_ea as IRMS
    f_ion, z, calc, _ = IRMS.ion(formula, adduct)
    pat = HRMS.isotope_pattern(f_ion, z)
    delay, step, c0, c1, c2, _c5, c6 = BAF_CAL

    def to_idx(mz):
        m = np.asarray(mz, float) + c6
        return (c0 + np.sqrt(1e12 * m / c1) + c2 * m - delay) / step
    rng = np.random.default_rng(seed)
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    baf, rows = bytearray(64), []
    for k, rt in enumerate(np.arange(0.0, 120.1, 3.0)):
        amp = 2.4e5 * np.exp(-0.5 * ((rt - 54.0) / 6.0) ** 2)
        mz = [149.0233, 391.2843] + [m + shift + rng.normal(0, 3e-4) for m, r in pat if amp * r > 5000]
        it = [3.1e3 * rng.normal(1, 0.08), 6.5e3 * rng.normal(1, 0.08)] + [amp * r / 100 * rng.normal(1, 0.03)
                                                                         for m, r in pat if amp * r > 5000]
        n, o = len(mz), np.argsort(mz)                  # Linienspektren nach m/z sortiert wie vom Gerät
        mz, it = np.asarray(mz)[o], np.asarray(it)[o]
        body = (struct.pack("<4I", n, 16, 16 + 8 * n, 16 + 12 * n) + to_idx(mz).astype("<f8").tobytes()
                + np.asarray(it, "<f4").tobytes() + np.full(n, 0.012, "<f4").tobytes())
        head = bytearray(52)
        struct.pack_into("<III", head, 0, 52 + len(body), BAF_LINE_MAGIC, 52)
        rows.append((k + 1, float(rt), (0x10 << 56) | len(baf)))
        baf += head + body
    (d / "analysis.baf").write_bytes(bytes(baf))
    blob = struct.pack("<i7d", 10, *BAF_CAL)
    con = sqlite3.connect(d / "analysis.sqlite")
    con.executescript("create table Properties (Key text, Value text); create table AcquisitionKeys (Id integer, "
                      "Polarity integer); create table Spectra (Id integer, Rt real, TransformatorId integer, "
                      "LineIndexId integer, AcquisitionKey integer); create table Steps (TargetSpectrum integer); "
                      "create table Transformators (Id integer, Blob blob);")
    con.executemany("insert into Properties values (?, ?)", [("SchemaType", "Baf2Sql"), ("SampleName", name),
                                                            ("InstrumentName", "timsTOF (demo)")])
    con.execute("insert into AcquisitionKeys values (0, 0)")
    con.executemany("insert into Spectra values (?, ?, 1, ?, 0)", rows)
    con.execute("insert into Transformators values (1, ?)", (blob + bytes(112 - len(blob)),))
    con.commit()
    con.close()
    return d


def huckel_frontier(m, P):
    """HOMO und LUMO des π-Systems aus einer Hückel-Rechnung (Heteroatome nach Streitwieser: Pyridin-N h = 0.5,
    Amin-N h = 1.5, k(C–N) = 0.8), als p-Orbitale senkrecht zur Molekülebene (z der Hauptachsen von P) -> (Atome des
    π-Systems, Koeffizienten HOMO, LUMO). Nur für das Aussehen der Orbitale im Beispiel, keine Rechnung."""
    pi = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomicNum() in (6, 7) and (
        a.GetIsAromatic() or any(b.GetBondTypeAsDouble() == 3 for b in a.GetBonds())
        or (a.GetAtomicNum() == 7 and any(x.GetIsAromatic() for x in a.GetNeighbors())))]
    amine = {i for i in pi if m.GetAtomWithIdx(i).GetAtomicNum() == 7 and not m.GetAtomWithIdx(i).GetIsAromatic()}
    pos = {i: k for k, i in enumerate(pi)}
    H = np.zeros((len(pi), len(pi)))
    for i in pi:
        H[pos[i], pos[i]] = 1.5 if i in amine else (0.5 if m.GetAtomWithIdx(i).GetAtomicNum() == 7 else 0.0)
    for b in m.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in pos and j in pos:
            H[pos[i], pos[j]] = H[pos[j], pos[i]] = 0.8 if amine & {i, j} else 1.0
    x, C = np.linalg.eigh(H)                           # E = α + xβ (β < 0): großes x = tief
    n_occ = (len(pi) + len(amine)) // 2                 # ein π-Elektron je C/Pyridin-N, zwei am Amin-N
    order = np.argsort(-x)
    return pi, C[:, order[n_occ - 1]], C[:, order[n_occ]]


def orbital_cube(path, m, P, atoms, coef, step=0.2, pad=3.5, alpha=1.6):
    """Cube (Bohr, wie ORCA) eines π-Orbitals: Σ c·(z − z_i)·exp(−α r²) an den Atomen, normiert, auf einem Gitter um
    die Geometrie P (dieselben Atome und Koordinaten wie die ORCA-Ausgabe, damit der DFT-Tab den Cube anhängt)."""
    from elucida.core import orbitals as ORB
    lo, hi = P.min(0) - pad, P.max(0) + pad
    g = [np.arange(lo[k], hi[k] + step / 2, step) for k in range(3)]
    X, Y, Z = np.meshgrid(*g, indexing="ij")
    psi = np.zeros(X.shape)
    for i, c in zip(atoms, coef):
        x0, y0, z0 = P[i]
        psi += c * (Z - z0) * np.exp(-alpha * ((X - x0) ** 2 + (Y - y0) ** 2 + (Z - z0) ** 2))
    psi /= np.sqrt(np.sum(psi ** 2) * (step / ORB.BOHR) ** 3)
    ORB.write_cube(path, [a.GetSymbol() for a in m.GetAtoms()], P, lo, np.eye(3) * step, psi.astype(np.float32),
                   title="Elucida demo orbital", comment="pi orbital (Hueckel model)")
    return Path(path)


def make_nics(path, m, P, height=1.0, step=0.25, depth=(-27.0, -24.0)):
    """Gaussian-NMR-Ausgabe (nur die gelesenen Abschnitte wie `formats.calc.parse_nics`: Route, Eingabeorientierung mit
    Bq, Abschirmtensoren der Bq) eines NICS-Scans `height` Å über der Molekülebene (z der Hauptachsen von P) von 2 Å vor
    dem ersten bis 2 Å hinter dem letzten Sechsring. Werte erfunden: NICSzz je Ring als Gaußmulde (Tiefe `depth`,
    Pyridin etwas aromatischer als der Donorring), NICS = 0.36·NICSzz − 0.4. Kein echter Datensatz."""
    from elucida.formats.elements import ELEMENTS
    rings = [np.asarray(r) for r in m.GetRingInfo().AtomRings() if len(r) == 6]
    cen = [P[r].mean(0) for r in rings]
    a, b = cen[0], cen[-1]
    u = (b - a) / np.linalg.norm(b - a)
    s = np.arange(-2.0, np.linalg.norm(b - a) + 2.0 + step / 2, step)
    bq = a + np.outer(s, u)
    bq[:, 2] = np.mean([c[2] for c in cen]) + height
    zz = sum(dp * np.exp(-(np.linalg.norm((bq - c)[:, :2], axis=1) / 1.25) ** 2) for c, dp in zip(cen, depth)) - 1.5
    iso = 0.36 * zz - 0.4
    Z = {e: i + 1 for i, e in enumerate(ELEMENTS)}
    els = [x.GetSymbol() for x in m.GetAtoms()]
    dash = " " + "-" * 69
    L = [" Entering Gaussian System, Link 0=g16", dash, " #p nmr=giao b3lyp/6-311+g(2d,p) scrf=(smd,solvent=thf)", dash,
         "", "                          Input orientation:", dash,
         " Center     Atomic      Atomic             Coordinates (Angstroms)",
         " Number     Number       Type             X           Y           Z", dash]
    L += [f" {k + 1:6d} {Z[e]:10d} {0:11d} {x:15.6f} {y:11.6f} {z:11.6f}" for k, (e, (x, y, z)) in enumerate(zip(els, P))]
    L += [f" {len(els) + k + 1:6d} {0:10d} {0:11d} {x:15.6f} {y:11.6f} {z:11.6f}" for k, (x, y, z) in enumerate(bq)]
    L += [dash, "", " SCF GIAO Magnetic shielding tensor (ppm):"]
    for k, (si, sz) in enumerate(zip(-iso, -zz)):
        sx = (3 * si - sz) / 2                           # in der Ebene gleich, Spur = 3·σ_iso
        L += [f" {len(els) + k + 1:6d}  Bq   Isotropic = {si:12.4f}   Anisotropy = {sz - sx:12.4f}",
              f"   XX= {sx:12.4f}   YX= {0.0:12.4f}   ZX= {0.0:12.4f}",
              f"   XY= {0.0:12.4f}   YY= {sx:12.4f}   ZY= {0.0:12.4f}",
              f"   XZ= {0.0:12.4f}   YZ= {0.0:12.4f}   ZZ= {sz:12.4f}"]
    L += [" Normal termination of Gaussian 16."]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return Path(path)


# Emission in fünf Lösungsmitteln (Lippert-Mataga): Δf aus ε und n (Literaturkonstanten), λ_abs erfunden, λ_em aus einer
# erfundenen Geraden durch den THF-Punkt der Tabs ε/Fluoreszenz (372 → 458 nm)
SOLVENTS = (("cyclohexane", 2.02, 1.426, 366), ("toluene", 2.38, 1.497, 371), ("THF", 7.58, 1.407, 372),
            ("CH$_2$Cl$_2$", 8.93, 1.424, 375), ("MeCN", 35.9, 1.344, 370))


def lippert_png(path, em_thf=458.0, slope=9500.0):
    """Lippert-Mataga-Auftragung (Stokes-Verschiebung gegen Δf) als PNG für den Tab „Weitere“ (anderes Programm)."""
    from matplotlib.figure import Figure
    df = np.array([(e - 1) / (2 * e + 1) - (n * n - 1) / (2 * n * n + 1) for _, e, n, _ in SOLVENTS])
    lab = np.array([s[3] for s in SOLVENTS], float)
    s_thf = 1e7 / 372 - 1e7 / em_thf
    stokes = s_thf + slope * (df - df[2]) + np.array([60.0, -90.0, 0.0, 70.0, -40.0])
    fig = Figure(figsize=(16 / 2.54, 11 / 2.54), dpi=200)
    ax = fig.add_axes((0.14, 0.15, 0.82, 0.8))
    k, b = np.polyfit(df, stokes, 1)
    xs = np.array([df.min() - 0.02, df.max() + 0.02])
    ax.plot(xs, k * xs + b, color="0.5", lw=1)
    ax.plot(df, stokes, "o", color="#1764e8")
    offsets = ((-10, 8), (6, -12), (6, -14), (8, 2), (-34, -14))           # Beschriftungen frei von Punkten und Linie
    for (s, *_), x, y, o in zip(SOLVENTS, df, stokes, offsets):
        ax.annotate(s, (x, y), xytext=o, textcoords="offset points", fontsize=9)
    ax.set_xlabel(r"$\Delta f$")
    ax.set_ylabel(r"Stokes shift [cm$^{-1}$]")
    fig.savefig(path)
    return Path(path)


def demo_dir() -> Path:
    return IMG.app_data_dir() / "Beispielverbindung"


def is_demo(path) -> bool:
    """Liegt der Ordner in einem der Beispiele (Datenordner)? Die erscheinen nie in „Zuletzt geöffnet“."""
    try:
        p = Path(path).resolve()
        return any(p == (IMG.app_data_dir() / d).resolve() or (IMG.app_data_dir() / d).resolve() in p.parents
                   for d in DEMO_DIRS)
    except OSError:
        return False


def open_demo(w, folder=None, name="S3") -> Path:
    """Beispielverbindung neu anlegen (vorhandene wird ersetzt) und im Hauptfenster öffnen: S3 mit allen Tabs."""
    d = Path(folder) if folder else demo_dir()
    if d.exists():
        shutil.rmtree(d)
    inp = Path(tempfile.mkdtemp(prefix="elucida_demo_"))
    try:
        if not w.create_project(d):
            raise RuntimeError(f"Projekt {d} konnte nicht angelegt werden")
        load_data(w, inp, name)
        w.syn_tab.sync_widgets()
        w.render()
        tabs = ("nmr_tab", "irms_tab", "hrms_tab", "xray_tab")
        if name == "S3":                                   # die Vorstufe hat diese Tabs nicht
            tabs += ("ov_tab", "uvkin_tab", "fl_tab", "cv_tab", "sec_tab", "hcell_tab", "epr_tab", "dft_tab", "other_tab")
        for t in (getattr(w, a) for a in tabs):
            for fn in ("sync_widgets", "update_preview", "render"):
                f = getattr(type(t), fn, None)
                if f is not None and f.__qualname__.split(".")[0] != "QWidget":
                    getattr(t, fn)()
        w.save_project()
        # Speichern kopiert die Eingaben ins Projekt, der Zustand zeigte aber weiter in den Temp-Ordner (jedes
        # spätere Speichern schrieb dann tote Pfade): Pfade auf die Kopien übernehmen
        w._load_state_into_ui(PRJ.load(d))
    finally:
        shutil.rmtree(inp, ignore_errors=True)            # Eingaben sind ins Projekt kopiert
    return d


def demo_pub_dir() -> Path:
    return IMG.app_data_dir() / "Beispielprojekt"


def open_demo_publication(w, folder=None) -> Path:
    """Beispielpublikation (künstliche Daten): Vorstufe S2 (Synthese, NMR, IR, EA, HRMS, UV-Vis, X-Ray) und ihr
    Produkt S3 mit allen Tabs, Angaben und SI-Texte ausgefüllt; danach die Seite der Publikation zeigen."""
    from elucida.app import publication as PUB
    d = Path(folder) if folder else demo_pub_dir()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    PUB.create(d)
    for name in ("S2", "S3"):
        open_demo(w, d / name, name)
        PUB.add_compound(d, d / name)
    data = PUB.load(d)
    data.update(paper_title="Example project with artificial data",
                authors="A. Author, B. Author and C. Author*",
                affiliation="Example Department, Example University, Example Street 1, 12345 Example City.",
                contact="author@example.org", doi="10.0000/EXAMPLE",
                related="Author et al., Example Journal 2026, https://doi.org/10.0000/example",
                project_description="Artificial data generated by Elucida to show the publication workflow.",
                si_texts={"methods": "All reactions were carried out under argon using standard Schlenk techniques. "
                                     "NMR spectra were recorded at 298 K; chemical shifts are given in ppm.",
                          "cv": "Cyclic voltammograms were recorded with ferrocene as internal reference."})
    # Seite „Vergleich“: UV-Vis beider Verbindungen (ε wie im Overlay) und eine Eigenschaftstabelle (Werte aus den Tabs,
    # dazu eine freie Spalte mit der C≡C-Bande der erfundenen IR-Spektren)
    members = [dict(dir=n, on=True, key=f"m{n}", color=c) for n, c in (("S2", "#000000"), ("S3", "#e8231b"))]
    data["comparisons"] = [
        dict(uid="demo0spectra", name="UV-Vis S2 / S3", kind="spectra",
             st=dict(members=[dict(m) for m in members], content="eps")),
        dict(uid="demo00table", name="Properties", kind="table", st=dict(members=[dict(m) for m in members], table=dict(
            cols=[dict(id="c1", kind="auto", key="formula", group=""), dict(id="c2", kind="auto", key="mw", group=""),
                  dict(id="c3", kind="auto", key="uv_lam", group="UV-Vis"),
                  dict(id="c4", kind="auto", key="uv_eps", group="UV-Vis"),
                  dict(id="c5", kind="free", head="IR (C≡C)", unit="cm-1", group="")],
            rows=[], cells={f"m{n}|c5": f"{COMPOUNDS[n]['ir'][k][0]:.0f}" for n, k in (("S2", 1), ("S3", 4))},
            transpose=False)))]
    PUB.save(d, data)
    PUB.set_group(d, d / "S2", "Precursors")          # Gruppen im Projekt zeigen
    PUB.set_group(d, d / "S3", "Products")
    inp = Path(tempfile.mkdtemp(prefix="elucida_demo_path_"))
    try:                                                   # Computerchemie: ein Reaktionspfad mit Profil
        make_path(w, d, inp)
    finally:
        shutil.rmtree(inp, ignore_errors=True)            # Eingaben sind in den Pfad kopiert
    w.open_publication(d)
    return d
