"""Beispielprojekt mit **künstlichen Daten** für alle Tabs (Hilfe → Beispielprojekt öffnen, README-Screenshots).

Keine Messdateien, keine echten Verbindungen: Generatoren des Selbsttests und erfundene Beispiele. Das Projekt liegt im
Datenordner des Programms und wird bei jedem Öffnen neu angelegt.
"""
from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path

import numpy as np

from elucida.tabs import dft as DFT
from elucida.tabs import nmr as NMR
from elucida.app import project as PRJ
from elucida.tabs import epr as EPR
from elucida.core import images as IMG
from elucida.tabs import sec as SEC
from elucida.tabs import xray as XRAY


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


def cv_sweep(e0, ip, lo, hi, step=0.002, ref=None):
    """Modell-CV wie im Selbsttest: Peaks bei E0 ± 30 mV, optional Referenzpaar."""
    up = np.arange(lo, hi + step / 2, step)
    E_ = np.concatenate([up, up[::-1]])
    fw = np.r_[np.ones(len(up)), np.zeros(len(up))].astype(bool)

    def wave(e_c, i_p):
        pa = i_p * np.exp(-((E_ - (e_c + 0.03)) / 0.045) ** 2) + 0.3 * i_p / (1 + np.exp(-(E_ - e_c - 0.03) / 0.02))
        pc = -0.9 * i_p * np.exp(-((E_ - (e_c - 0.03)) / 0.045) ** 2)
        return np.where(fw, pa, pc + 0.3 * i_p * np.exp(-(hi - E_) / 0.1))
    return E_, wave(e0, ip) + (wave(ref, 0.8 * ip) if ref is not None else 0)


def make_sec(d):
    """BWSpec-Serie + Gamry-Potential: zwei Oxidationen (neutral 432 nm → Radikalkation 610 nm → Dikation 373 nm)."""
    d.mkdir(parents=True, exist_ok=True)
    t_start = dt.datetime(2026, 1, 1, 12, 0, 0)
    T_ = np.arange(0.0, 1150.0, 2.0)
    write_dta(d / "sec.DTA", [(-1.3 + 0.002 * T_, 1.0 + 0 * T_)], 2.0, cycle_col=True, times=T_)
    pix = np.arange(0, 2048)
    lam = 200.0 + 0.35 * pix
    bands = (0.30 * np.exp(-((lam - 432) / 25) ** 2),
             0.22 * np.exp(-((lam - 610) / 45) ** 2) + 0.12 * np.exp(-((lam - 395) / 20) ** 2),
             0.35 * np.exp(-((lam - 373) / 15) ** 2))
    files = []
    for j in range(70):
        ts = j * 15.0 + 5.0
        e = -1.3 + 0.002 * ts
        k1 = np.exp(SEC.F_RT * (e + 0.80))
        k2 = np.exp(SEC.F_RT * (e + 0.25))
        w_ = np.array([1.0, k1, k1 * k2])
        A = sum(f * b for f, b in zip(w_ / w_.sum(), bands))
        hdr = ["File Version;BWSpec4.11_1", f"Date;{(t_start + dt.timedelta(seconds=ts)):%Y-%m-%d %H:%M:%S}",
               "coefs_a0;200", "coefs_a1;0.35", "coefs_a2;0", "coefs_a3;0", "sel_pixel_start;0",
               "Pixel;Wavelength;Wavenumber;Raman Shift;Dark;Reference;Raw data #1;Dark Subtracted #1;%TR #1;"
               "Absorbance #1;Irradiance (W/m^2/nm) #1"]
        rows = [f"{p};   ;   ;   ;0;0;0;0;0;{a:.5f};0;" for p, a in zip(pix, A)]
        f = d / f"s{j:03d}.txt"
        f.write_text("\r\n".join(hdr + rows), encoding="latin-1", newline="")
        files.append(str(f))
    return files, d / "sec.DTA"


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


def scheme_cdxml(path):
    """Erfundenes Schema: TMS-Entschützung eines Alkins (RDKit-CDXML), Pfeil mit K2CO3 / MeOH, rt, 1 h."""
    import xml.etree.ElementTree as ET
    from rdkit import Chem
    from rdkit.Chem import AllChem

    def frag(smiles, offset, dx):
        m = Chem.MolFromSmiles(smiles)
        AllChem.Compute2DCoords(m)
        fr = ET.fromstring(mol_cdxml(m)).find(".//fragment")
        ids = {o.get("id"): str(offset + k) for k, o in enumerate(fr.iter()) if o.get("id")}
        for o in fr.iter():
            if o.get("id"):
                o.set("id", ids[o.get("id")])
            if o.tag == "n":
                x, y = map(float, o.get("p").split())
                o.set("p", f"{x + dx} {y}")
            if o.tag == "b":
                o.set("B", ids[o.get("B")])
                o.set("E", ids[o.get("E")])
        return fr
    f1 = frag("C[Si](C)(C)C#Cc1ccc(C)cn1", 1000, 0)
    xs = [float(n.get("p").split()[0]) for n in f1.iter("n")]
    ys = [float(n.get("p").split()[1]) for n in f1.iter("n")]
    xr, ym = max(xs), sum(ys) / len(ys)
    f2 = frag("Cc1ccc(C#C)nc1", 2000, 0)
    p2 = [float(n.get("p").split()[0]) for n in f2.iter("n")]
    f2_shift = (xr + 150) - min(p2)
    for n in f2.iter("n"):
        x, y = map(float, n.get("p").split())
        n.set("p", f"{x + f2_shift} {y}")
    txt = (f'<?xml version="1.0"?><CDXML LineWidth="0.6" BondSpacing="18" LabelSize="10"><page>'
           + ET.tostring(f1, encoding="unicode") + ET.tostring(f2, encoding="unicode")
           + f'<t id="501" p="{xr + 30} {ym - 6}"><s face="96" size="10">K2CO3 (1.2 eq.)</s></t>'
           + f'<t id="502" p="{xr + 30} {ym + 12}"><s size="9.7">MeOH, rt, 1 h</s></t>'
           + f'<arrow id="503" Head3D="{xr + 125} {ym} 0" Tail3D="{xr + 20} {ym} 0"/>'
           + f'<scheme><step ReactionStepReactants="{f1.get("id")}" ReactionStepProducts="{f2.get("id")}" '
           + 'ReactionStepObjectsAboveArrow="501" ReactionStepObjectsBelowArrow="502"/></scheme></page></CDXML>')
    Path(path).write_text(txt, encoding="utf-8")
    return Path(path)


def load_data(w, inp):
    """Alle Tabs mit künstlichen Daten füllen."""
    from elucida.selftest import make_selftest_inputs
    csv, cdxml, photo = make_selftest_inputs(inp)
    # Verbindung mit Formel, Molmasse und Schmelzpunkt (erfunden), damit die Checkliste des Projekts vollständig ist
    w.set_compound({"name": "S2", "formula": "C8H7N", "mw": 117.15, "mp": "112–114 °C"})
    # UV-Vis (ε): Verdünnungsreihe, Struktur, Küvettenfoto
    w.open_csv(csv, ask=False)
    w.set_structure(str(cdxml), "TEST-A", render=False, sync=True)
    w.series["TEST-A"]["bg"] = "grabcut"
    w.set_photo(str(photo), "TEST-A", render=False, sync=True)
    w.current = "TEST-A"
    w.apply_series_widgets()
    # Overlay: Messung + TD-DFT (erfundene ORCA-Tabelle)
    orca = inp / "tddft.out"
    orca.write_text("\n".join([
        "-" * 77, "         ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS", "-" * 77,
        "State   Energy    Wavelength  fosc         T2        TX        TY        TZ",
        "        (cm-1)      (nm)                 (au**2)    (au)      (au)      (au)", "-" * 77,
        "   1   20660.0    484.0   0.150000000   1.00000   1.00000   0.00000   0.00000",
        "   2   27400.0    365.0   0.080000000   0.60000   0.70000   0.00000   0.00000",
        "   3   38168.0    262.0   0.600000000   3.00000   1.70000   0.00000   0.00000", ""]), encoding="utf-8")
    w.ov_state.update(entries=[
        {"kind": "exp", "file": str(csv), "sample": "TEST-A-0p25mgml_THF", "label": "exp.", "color": "#000000",
         "visible": True, "own_norm": False, "nlo": 450, "nhi": 520, "conc": 0.25, "unit": "mg/mL", "mw": 95.1,
         "d": 1.0},
        {"kind": "calc", "file": str(orca), "label": "TD-DFT", "color": "#1764e8", "visible": True,
         "own_norm": False, "nlo": 450, "nhi": 520, "fwhm": 0.3, "shift": 0.0}],
        nlo=450, nhi=520, mode="norm", sticks=True, stick_mode="band")
    # Fluoreszenz
    em = inp / "emission.csv"
    xs = np.arange(400.0, 701.0, 1.0)
    em.write_text("\r\n".join(["EM ex352,,", "Wavelength (nm),Intensity (a.u.),"] +
                              [f"{x:.1f},{500 * np.exp(-((x - 540) / 32) ** 2):.3f}," for x in xs]),
                  encoding="utf-8", newline="")
    w.fl_state.update(abs_file=str(csv), abs_sample="TEST-A-0p25mgml_THF", em_file=str(em), em_sample="EM ex352",
                      ex=352.0, alo=450, ahi=520, eps="1234", stokes_label=True,
                      photo_day=str(photo), bg_day="grabcut", photo_uv=str(photo), bg_uv="none")
    # CV: drei Vorschubgeschwindigkeiten + Messung mit interner Referenz
    cvd = inp / "cv"
    cvd.mkdir(parents=True, exist_ok=True)
    files = []
    for rate, ip in ((50, 40.0), (100, 56.0), (200, 80.0)):
        p = cvd / f"cv_{rate}.DTA"
        write_dta(p, [cv_sweep(-1.02, ip, -1.4, -0.5)], rate)
        files.append((p, rate))
    ref = cvd / "cv_ref.DTA"
    write_dta(ref, [cv_sweep(-1.02, 80.0, -1.4, 0.9, ref=0.55)] * 2, 200, cycle_col=True)
    w.cv_state["files"] = [{"file": str(p), "uid": f"cv{i}", "visible": True, "color": "#000000",
                            "label": f"{r} mV/s"} for i, (p, r) in enumerate(files)]
    w.cv_state["files"].append({"file": str(ref), "uid": "cvref", "visible": False, "color": "#000000",
                                "label": "ref"})
    w.cv_state.update(couples=[[-1.2, -0.8]], ref_mode="internal", ref_uid="cvref", ref_lo=0.3, ref_hi=0.8,
                      ref_compound="ac2fc", ref_value=0.49, cycle=2)
    # SEC mit Zwischenspezies
    sec_files, dta = make_sec(inp / "sec")
    w.sec_state.update(spec_files=sec_files, dta=str(dta), mode="spectra", bands="373, 432, 610", mid="-0.53",
                       cap_solvent="THF", cap_start="neutral", cap_mid="radical cation", cap_end="dication")
    # EPR: isotropes S = ½-Spektrum (1 × 14N, 2 × 1H) mit eigener Simulation
    ed = inp / "epr"
    ed.mkdir(parents=True, exist_ok=True)
    Bt = np.linspace(330.0, 345.0, 6001)
    I_ = EPR.iso_spectrum(Bt, 9.40, 2.0058, [(1, 1.0, 1.52), (2, 0.5, 0.21)], 0.10)
    I_ += np.random.default_rng(1).standard_normal(len(Bt)) * 0.01 * np.ptp(I_)
    np.savetxt(ed / "radical-9p400000.txt", np.column_stack([Bt, I_]), header="B [mT]\tI [a.U.]", comments="",
               delimiter="\t")
    t_e = w.epr_tab
    er = t_e._new("exp", str(ed / "radical-9p400000.txt"))
    w.epr_state.update(entries=[er], bl_order=-1, smooth=0.0, normalize=True, stack=False, show_sum=False,
                       show_residual=False)
    t_e.fill_table()
    t_e.table.selectRow(0)
    t_e.add_iso()
    si = w.epr_state["entries"][-1]
    si["nuclei"] = "1 14N 1.5; 2 1H 0.2"
    t_e.fill_table()
    t_e.table.selectRow(1)
    t_e.fit_current()
    w.epr_state.update(cap_species="S2^{•+}", cap_solvent="THF", cap_conc="1 mM")
    # X-Ray: künstliche CIF des Selbsttests
    (inp / "xray").mkdir(parents=True, exist_ok=True)
    cif, _ = XRAY.make_test_cif(inp / "xray" / "xtest.cif")
    w.xray_tab.load_cif(str(cif))
    w.xray_state["current"] = w.xray_state["entries"][0]["uid"]
    # DFT: künstliche ORCA-6-Ausgabe des Selbsttests
    (inp / "dft").mkdir(parents=True, exist_ok=True)
    w.dft_tab.load_xyz(str(DFT.make_test_orca(inp / "dft" / "otest.out")))
    # NMR: erfundene Spektren (¹H, ¹³C), Mnova-Text, Struktur
    nd = inp / "nmr"
    j = 7.9 / 400 / 2                                   # halbe Dublett-Aufspaltung in ppm (400 MHz)
    h1 = demo_nmr_svg(nd / "S2-1H.svg", "1H", [(8.38, 1.0, 0.004), (7.50 + j, 0.5, 0.004), (7.50 - j, 0.5, 0.004),
                                              (7.41 + j, 0.5, 0.004), (7.41 - j, 0.5, 0.004), (3.08, 1.0, 0.004),
                                              (2.33, 3.0, 0.004), (7.26, 0.15, 0.003)],
                      (9.5, 0.5))
    c13 = demo_nmr_svg(nd / "S2-13C.svg", "13C", [(150.4, 0.8, 0.15), (139.9, 0.5, 0.15), (136.7, 0.9, 0.15),
                                                 (133.4, 0.5, 0.15), (127.1, 0.9, 0.15), (82.9, 0.6, 0.15),
                                                 (76.9, 0.7, 0.15), (18.4, 1.0, 0.15)],
                       (170, 0), solvent=77.16)
    t_n = w.nmr_tab
    for p in (h1, c13):
        t_n.load_svg(str(p))
    from rdkit import Chem
    from rdkit.Chem import AllChem
    m = Chem.MolFromSmiles("Cc1ccc(C#C)nc1")
    AllChem.Compute2DCoords(m)
    (nd / "S2.cdxml").write_text(mol_cdxml(m), encoding="utf-8")
    w.nmr_state["structure"] = w.import_file(str(nd / "S2.cdxml"), PRJ.STRUCTURES)   # nicht im Temp-Ordner lassen
    # 2D: künstliches TopSpin-HSQC-Experiment (Rohdaten-Reiter, Checkliste „2D NMR“)
    t_n.import_topspin(str(NMR.make_test_acqus(nd / "S2" / "3", nuc="1H", nuc2="13C", pulprog="hsqcedetgpsisp2.3")))
    # IR (künstliche OPUS-Datei), HRMS (künstlicher Bericht der Massenabteilung), Elementaranalyse (erfundene Werte)
    ird = inp / "irms"
    ird.mkdir(parents=True, exist_ok=True)
    w.irms_tab.load_ir(str(make_opus(ird / "S2.0")))
    w.hrms_tab.load_ms(str(make_ms_report(ird / "S2_MS.docx", "S2", "C8H7N")))
    w.irms_state["ea_found"] = {"C": "81.88", "H": "6.07", "N": "11.86"}
    w.nmr_state["text"] = ("1H NMR (400 MHz, CDCl3) δ 8.38 (s, 1H), 7.50 (d, J = 7.9 Hz, 1H), 7.41 (d, J = 7.9 Hz, 1H), "
                           "3.08 (s, 1H), 2.33 (s, 3H).\n13C NMR (101 MHz, CDCl3) δ 150.4, 139.9, 136.7, 133.4, "
                           "127.1, 82.9, 76.9, 18.4.")
    w.nmr_state["current"] = t_n.spectra()[0]["uid"]
    # Synthese: erfundenes Schema, Vorschrift, Reagenzien (Mengen passen zueinander)
    sd = inp / "syn"
    sd.mkdir(parents=True, exist_ok=True)
    w.syn_tab.set_scheme(str(scheme_cdxml(sd / "rxn.cdxml")))
    w.syn_state["reagents"] = [dict(name="S1", M="C11H15NSi", m_mg="947", role="ref"),
                               dict(name="K2CO3", M="K2CO3", m_mg="829", role="reagent"),
                               dict(name="S2", M="C8H7N", m_mg="556", role="product")]
    w.syn_state["proc"] = ("<b>S1</b> (947 mg, 5.00 mmol, 1.0 eq.) was dissolved in MeOH (10 mL) and "
                           "K<sub>2</sub>CO<sub>3</sub> (829 mg, 6.00 mmol, 1.2 eq.) was added. The mixture was stirred "
                           "at room temperature for 1 h, diluted with water and extracted with Et<sub>2</sub>O. "
                           "Drying over MgSO<sub>4</sub> and removal of the solvent gave <b>S2</b> "
                           "(556 mg, 4.75 mmol, 95%) as a colourless solid.")


DEMO_DIRS = ("Beispielverbindung", "Beispielprojekt", "Beispielpublikation")   # im Datenordner (alte Namen mit)


def make_opus(path, bands=((3290.0, 35, 10), (2104.0, 20, 6), (1598.0, 40, 8), (1482.0, 45, 6), (1029.0, 30, 8),
                            (823.0, 55, 6))) -> Path:
    """Künstliche Bruker-OPUS-Datei (Transmission, 4000–400 cm-1) wie im Selbsttest."""
    import struct
    wn = np.linspace(3999.0, 400.0, 1800)
    T = 1.0 - sum(dp / 100 * np.exp(-((wn - c) / wd) ** 2) for c, dp, wd in bands)

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


def open_demo(w, folder=None) -> Path:
    """Beispielprojekt neu anlegen (vorhandenes wird ersetzt) und im Hauptfenster öffnen."""
    d = Path(folder) if folder else demo_dir()
    if d.exists():
        shutil.rmtree(d)
    inp = Path(tempfile.mkdtemp(prefix="elucida_demo_"))
    try:
        if not w.create_project(d):
            raise RuntimeError(f"Projekt {d} konnte nicht angelegt werden")
        load_data(w, inp)
        w.syn_tab.sync_widgets()
        w.render()
        for t in (w.nmr_tab, w.irms_tab, w.hrms_tab, w.ov_tab, w.fl_tab, w.cv_tab, w.sec_tab, w.epr_tab, w.xray_tab,
                  w.dft_tab):
            for fn in ("sync_widgets", "update_preview", "render"):
                f = getattr(type(t), fn, None)
                if f is not None and f.__qualname__.split(".")[0] != "QWidget":
                    getattr(t, fn)()
        w.save_project()
    finally:
        shutil.rmtree(inp, ignore_errors=True)            # Eingaben sind ins Projekt kopiert
    return d


def demo_pub_dir() -> Path:
    return IMG.app_data_dir() / "Beispielprojekt"


def open_demo_publication(w, folder=None) -> Path:
    """Beispielpublikation (künstliche Daten): zwei Verbindungen (S2 mit allen Tabs, S3 als umbenannte Kopie),
    Angaben und SI-Texte ausgefüllt; danach die Seite der Publikation zeigen."""
    from elucida.app import publication as PUB
    d = Path(folder) if folder else demo_pub_dir()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    PUB.create(d)
    open_demo(w, d / "S2")
    PUB.add_compound(d, d / "S2")
    shutil.copytree(d / "S2", d / "S3")
    w.open_project(d / "S3", recent=False)
    w.set_compound({**w.compound, "name": "S3"})
    w.syn_state["name"] = "S3"
    w.save_project()
    PUB.add_compound(d, d / "S3")
    data = PUB.load(d)
    data.update(paper_title="Example project with artificial data for all tabs",
                authors="A. Author, B. Author and C. Author*",
                affiliation="Example Department, Example University, Example Street 1, 12345 Example City.",
                contact="author@example.org", doi="10.0000/EXAMPLE",
                related="Author et al., Example Journal 2026, https://doi.org/10.0000/example",
                project_description="Artificial data generated by Elucida to show the publication workflow.",
                si_texts={"methods": "All reactions were carried out under argon using standard Schlenk techniques. "
                                     "NMR spectra were recorded at 298 K; chemical shifts are given in ppm.",
                          "cv": "Cyclic voltammograms were recorded with ferrocene as internal reference."})
    PUB.save(d, data)
    PUB.set_group(d, d / "S2", "Precursors")          # Gruppen im Projekt zeigen
    PUB.set_group(d, d / "S3", "Products")
    w.open_publication(d)
    return d
