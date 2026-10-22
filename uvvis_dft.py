"""uvvis_dft.py - DFT-Geometrien (xyz): Ansicht wie im X-Ray-Tab, Atome per Klick umnummerieren, xyz speichern.

xyz:   Atomzahl, Kommentarzeile, je Atom „El x y z“ (Symbol, Label wie „C12“ oder Ordnungszahl); mehrere Bilder
       hintereinander (ORCA-Trajektorie) werden alle gelesen, gezeigt wird das letzte. Beim Speichern bleiben die
       Atomzeilen Zeichen für Zeichen erhalten (nur umsortiert, keine Rundung); die Reihenfolge gilt für alle Bilder.
Bindungen: kovalente Radien wie im X-Ray-Tab (d < r1 + r2 + 0.45 Å, keine H–H).
Nummerierung: `order` = Atomindizes der Datei in der aktuellen Reihenfolge (None = wie in der Datei). Angeklickte
       Atome kommen der Reihe nach nach vorn, der Rest behält seine Reihenfolge (wahlweise H direkt hinter ihrem Atom).
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import numpy as np

import uvvis_xray as XRAY
from uvvis_i18n import T

ELEMENTS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
            "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
            "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn").split()
H_ELS = ("H", "D")


# ---------------------------------------------------------------------------- xyz lesen/schreiben
def parse_xyz(text) -> list[dict]:
    """-> [dict(comment, lines, els, xyz)] je Bild; lines = Atomzeilen unverändert (ohne Zeilenende)."""
    lines = text.splitlines()
    frames, i = [], 0
    while i < len(lines):
        head = lines[i].strip()
        if not head:
            i += 1
            continue
        try:
            n = int(head.split()[0])
        except ValueError:
            raise ValueError(T("dft_bad_xyz", line=i + 1)) from None
        if n <= 0 or i + 2 + n > len(lines):
            raise ValueError(T("dft_short_xyz", n=n, line=i + 1))
        comment = lines[i + 1]
        raw = lines[i + 2:i + 2 + n]
        els, xyz = [], []
        for j, ln in enumerate(raw):
            tok = ln.split()
            try:
                if len(tok) < 4:
                    raise ValueError
                xyz.append([float(t.replace("D", "E").replace("d", "e")) for t in tok[1:4]])
            except ValueError:
                raise ValueError(T("dft_bad_atom", line=i + 3 + j)) from None
            s = tok[0]
            if s.isdigit():
                z = int(s)
                if not 1 <= z <= len(ELEMENTS):
                    raise ValueError(T("dft_bad_atom", line=i + 3 + j))
                els.append(ELEMENTS[z - 1])
            else:
                els.append(XRAY.element_of(s, s))
        frames.append(dict(comment=comment, lines=[ln.rstrip("\r\n") for ln in raw], els=els,
                           xyz=np.array(xyz, float)))
        i += 2 + n
    if not frames:
        raise ValueError(T("dft_no_atoms"))
    if any(f["els"] != frames[0]["els"] for f in frames):
        raise ValueError(T("dft_frames_differ"))
    return frames


def read_text(path) -> str:
    """Text mit Kodierungserkennung: ORCA unter Windows-PowerShell („orca x.inp > x.out“) schreibt UTF-16."""
    return decode(Path(path).read_bytes())


def decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="replace")
    head = raw[:4000]
    if head and head.count(b"\x00") > len(head) // 4:            # UTF-16 ohne BOM
        return raw.decode("utf-16-le" if head[1:2] == b"\x00" else "utf-16-be", errors="replace")
    return raw.decode("utf-8", errors="replace")


def read_xyz(path) -> list[dict]:
    return parse_xyz(read_text(path))


# ---------------------------------------------------------------------------- Rechnungen (ORCA 6, Gaussian)
# Werte bleiben Text wie in der Ausgabe (keine Rundung), Zahlen zusätzlich als float, wo gerechnet wird.
_E = r"(-?\d+\.\d+)"
ORCA_THERMO = (("E_el", "Electronic energy"), ("ZPE", "Zero point energy"), ("U", "Total thermal energy"),
               ("H", "Total Enthalpy"), ("TS", "Final entropy term"), ("G", "Final Gibbs free energy"),
               ("G_E", "G-E(el)"))


def _calc():
    return dict(program="", version="", keywords=[], charge=None, mult=None, point_group="", solvation=None,
                opt_requested=False,
                opt_converged=None, conv=[], freq_requested=False, freqs=None, thermo={}, energy=None,
                normal=False, geometry=None)


def is_orca(text):
    return "O   R   C   A" in text[:20000] or "Program Version 6" in text[:20000]


def is_gaussian(text):
    return "Entering Gaussian System" in text[:20000] or "Gaussian, Inc." in text[:20000]


def parse_orca(text) -> dict:
    """ORCA 6: Eingabezeile(n) „!“, Ladung/Multiplizität, CPCM/SMD, letzte Konvergenztabelle der Optimierung,
    letzte Koordinaten, Frequenzen, Thermochemie. Abgebrochene Dateien liefern, was vorhanden ist (normal = False)."""
    c = _calc()
    c["program"] = "ORCA"
    L = text.splitlines()
    n = len(L)
    in_input, input_done, solv = False, False, None
    i = 0
    while i < n:
        ln = L[i]
        s = ln.strip()
        if not c["version"] and "Program Version" in ln:
            m = re.search(r"Program Version\s+(\S+)", ln)
            c["version"] = m.group(1) if m else ""
        elif s == "INPUT FILE" and not input_done:
            in_input = True
        elif in_input:
            if "END OF INPUT" in ln:
                in_input, input_done = False, True
            m = re.match(r"\|\s*\d+>\s?(.*)$", ln)
            if m and m.group(1).lstrip().startswith("!"):
                c["keywords"].append(m.group(1).strip())
        elif s.startswith("Total Charge") and "...." in s and c["charge"] is None:
            c["charge"] = int(s.split()[-1])
        elif s.startswith("Multiplicity") and "...." in s and c["mult"] is None:
            c["mult"] = int(s.split()[-1])
        elif s.startswith("FINAL SINGLE POINT ENERGY"):
            c["energy"] = s.split()[-1]
        elif "|Geometry convergence|" in ln:
            rows, j = [], i + 1
            while j < n and j < i + 15:
                m = re.match(r"^\s*([A-Za-z][A-Za-z ]*?)\s+(-?\d\S*)\s+(\d\S*)\s+(YES|NO)\s*$", L[j])
                if m:
                    rows.append(m.groups())
                elif rows and L[j].strip().startswith("---"):
                    break
                j += 1
            c["conv"] = rows
            c["opt_requested"] = True
        elif "THE OPTIMIZATION HAS CONVERGED" in ln:
            c["opt_converged"] = True
        elif "OPTIMIZATION DID NOT CONVERGE" in ln.upper() or "maximum number of optimization cycles" in ln:
            c["opt_converged"] = False
        elif s == "CARTESIAN COORDINATES (ANGSTROEM)":
            rows, j = [], i + 1
            while j < n:
                tok = L[j].split()
                if len(tok) != 4:
                    if rows or not (not tok or set(L[j].strip()) == {"-"}):     # Kopf: Strichlinie/Leerzeile
                        break
                    j += 1
                    continue
                rows.append((L[j].rstrip(), tok))
                j += 1
            if rows:
                c["geometry"] = rows
            i = j
            continue
        elif s == "VIBRATIONAL FREQUENCIES":
            fr, j = [], i + 1
            while j < n and j < i + 6 + 3 * 2000:
                m = re.match(r"^\s*\d+:\s+" + _E + r"\s+cm\*\*-1", L[j])
                if m:
                    fr.append(m.group(1))
                elif fr and L[j].strip():
                    break
                j += 1
            c["freqs"] = fr
            i = j
            continue
        elif s == "CPCM SOLVATION MODEL" or s.startswith("SMD"):
            solv = c["solvation"] = c["solvation"] or dict(model="CPCM", solvent="", eps="", e_diel=None,
                                                           e_cds=None)
            if "SMD" in s:
                solv["model"] = "SMD"
        elif solv is not None and s.startswith("Solvent:") and not solv["solvent"]:
            solv["solvent"] = s.split("...")[-1].strip()
        elif solv is not None and s.startswith("Epsilon ") and "..." in s and not solv["eps"]:
            solv["eps"] = s.split()[-1]
        elif solv is not None and re.match(r"SMD.*(true|TRUE|\bON\b)", s):
            solv["model"] = "SMD"
        elif s.startswith("CPCM Dielectric"):
            m = re.search(_E + r"\s*Eh", s)
            if m and solv is not None:
                solv["e_diel"] = m.group(1)
        elif s.startswith("Free-energy (cav+disp)"):
            m = re.search(_E + r"\s*Eh", s)
            if m and solv is not None:
                solv["e_cds"] = m.group(1)
        elif s.startswith("THERMOCHEMISTRY AT"):
            c["thermo"] = {}
        elif s.startswith("Temperature") and "..." in s and "K" in s:
            c["thermo"]["T"] = s.split("...")[-1].replace("K", "").strip()
        elif s.startswith("Pressure") and "..." in s:
            c["thermo"]["P"] = s.split("...")[-1].replace("atm", "").strip()
        elif s.startswith("Point Group:"):
            c["point_group"] = s.split(":", 1)[1].split(",")[0].strip()
        elif s.startswith("Quasi RRHO"):
            c["thermo"]["qrrho"] = s.split("...")[-1].strip().lower() == "true"
        elif "ORCA TERMINATED NORMALLY" in ln:
            c["normal"] = True
        else:
            for key, lab in ORCA_THERMO:
                if s.startswith(lab):
                    m = re.match(re.escape(lab) + r"\s+(?:\.\.\.)?\s*" + _E + r"\s*Eh", s)
                    if m:
                        c["thermo"][key] = m.group(1)
                    break
        i += 1
    kw = " ".join(c["keywords"]).upper()
    c["opt_requested"] = c["opt_requested"] or bool(re.search(r"\b\w*OPT\b", kw))
    c["freq_requested"] = bool(re.search(r"\b(NUM|AN)?FREQ\b", kw)) or c["freqs"] is not None
    return c


def parse_gaussian(text) -> dict:
    """Gaussian (nicht mit echten Ausgaben geprüft): Route, Ladung/Multiplizität, letzte Standard-/Input-Orientierung,
    letzte Konvergenztabelle, Frequenzen, Thermochemie, SCF-Energie, SCRF aus der Route."""
    c = _calc()
    c["program"] = "Gaussian"
    L = text.splitlines()
    n = len(L)
    i = 0
    while i < n:
        ln = L[i]
        s = ln.strip()
        if not c["version"]:
            m = re.search(r"Gaussian (\d\d), Revision ([A-Z]\.\d+)", ln) or re.search(r"Gaussian (\d\d):", ln)
            if m:
                c["version"] = m.group(1) + (f" Rev. {m.group(2)}" if m.lastindex and m.lastindex > 1 else "")
        if s.startswith("#") and not c["keywords"] and i > 0 and L[i - 1].strip().startswith("---"):
            route, j = [], i
            while j < n and not L[j].strip().startswith("---"):
                route.append(L[j].strip())
                j += 1
            c["keywords"] = ["".join(route)]
            i = j
            continue
        if s.startswith("Charge =") and "Multiplicity =" in s and c["charge"] is None:
            m = re.match(r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)", s)
            if m:
                c["charge"], c["mult"] = int(m.group(1)), int(m.group(2))
        elif s in ("Standard orientation:", "Input orientation:"):
            rows, j = [], i + 5
            while j < n and not L[j].strip().startswith("---"):
                tok = L[j].split()
                if len(tok) == 6 and tok[1].isdigit():
                    z = int(tok[1])
                    el = ELEMENTS[z - 1] if 1 <= z <= len(ELEMENTS) else "X"
                    rows.append((f"  {el:<2s} {tok[3]:>14s} {tok[4]:>14s} {tok[5]:>14s}", [el] + tok[3:6]))
                j += 1
            if rows and (s == "Standard orientation:" or c.get("_orient") != "std"):
                c["geometry"] = rows
                c["_orient"] = "std" if s == "Standard orientation:" else "inp"
            i = j
            continue
        elif s.startswith("SCF Done:"):
            m = re.search(r"=\s*" + _E, s)
            if m:
                c["energy"] = m.group(1)
        elif s.startswith("Item") and "Value" in s and "Threshold" in s:
            rows = []
            for j in range(i + 1, min(n, i + 6)):
                m = re.match(r"^\s*(Maximum Force|RMS\s+Force|Maximum Displacement|RMS\s+Displacement)\s+(\S+)\s+"
                             r"(\S+)\s+(YES|NO)", L[j])
                if m:
                    rows.append((re.sub(r"\s+", " ", m.group(1)),) + m.groups()[1:])
            c["conv"] = rows
            c["opt_requested"] = True
        elif s.startswith("Full point group"):
            tok = s.split()
            c["point_group"] = tok[3] if len(tok) > 3 else ""
        elif "Optimization completed." in s:
            c["opt_converged"] = True
        elif "Optimization stopped." in s:
            c["opt_converged"] = False
        elif s.startswith("Frequencies --"):
            c["freqs"] = (c["freqs"] or []) + s.split("--")[1].split()
        elif s.startswith("Temperature") and "Kelvin" in s:
            m = re.match(r"Temperature\s+(\S+)\s+Kelvin\.\s+Pressure\s+(\S+)\s+Atm", s)
            if m:
                c["thermo"].update(T=m.group(1), P=m.group(2))
        elif s.startswith("Zero-point correction="):
            c["thermo"]["ZPE"] = s.split("=")[1].split()[0]
        elif s.startswith("Sum of electronic and thermal Enthalpies="):
            c["thermo"]["H"] = s.split("=")[1].split()[0]
        elif s.startswith("Sum of electronic and thermal Free Energies="):
            c["thermo"]["G"] = s.split("=")[1].split()[0]
        elif "Normal termination of Gaussian" in s:
            c["normal"] = True
        elif s.startswith(("Initial command:", "Link1:")) or "Error termination" in s:
            c["normal"] = False                  # neuer Job (opt freq = zwei Jobs) bzw. Abbruch: gilt erst am Ende
        i += 1
    route = " ".join(c["keywords"]).lower()
    c["opt_requested"] = c["opt_requested"] or bool(re.search(r"\bopt\b", route))
    c["freq_requested"] = bool(re.search(r"\bfreq\b", route)) or c["freqs"] is not None
    if c["freqs"] and c["geometry"]:                 # mit freq=hpmodes steht die Liste zweimal da
        c["freqs"] = c["freqs"][:max(1, 3 * len(c["geometry"]) - 5)]
    m = re.search(r"scrf\s*=?\s*\(?([^)\s]*)", route)
    if m:
        opts = m.group(1)
        sm = re.search(r"solvent\s*=\s*([\w,-]+)", opts)
        c["solvation"] = dict(model="SMD" if "smd" in opts else "PCM", solvent=sm.group(1) if sm else "", eps="",
                              e_diel=None, e_cds=None)
    if c["energy"] is not None:
        c["thermo"].setdefault("E_el", c["energy"])
    c.pop("_orient", None)
    return c


def read_calc(path) -> dict:
    text = read_text(path)
    if is_orca(text):
        c = parse_orca(text)
    elif is_gaussian(text):
        c = parse_gaussian(text)
    else:
        raise ValueError(T("dft_not_calc"))
    if not c["geometry"]:
        raise ValueError(T("dft_no_geometry"))
    return c


def calc_frame(c, comment="", partner=None):
    """Geometrie einer Rechnung als xyz-Bild (Zeilen wie in der Ausgabe). partner = gleichnamige xyz neben der Ausgabe
    (ORCA schreibt sie mit 14 statt 6 Nachkommastellen): ihre Zeilen gelten, wenn Elemente und Koordinaten
    (± 1e-4 Å) zur letzten Geometrie der Ausgabe passen – sonst (z. B. Startgeometrie) wird sie ignoriert.
    -> (Bild, Partner benutzt)"""
    rows = c["geometry"]
    fr = dict(comment=comment, lines=[r[0] for r in rows], els=[XRAY.element_of(r[1][0], r[1][0]) for r in rows],
              xyz=np.array([[float(v) for v in r[1][1:4]] for r in rows], float))
    if partner is not None and Path(partner).is_file():
        try:
            px = read_xyz(partner)[-1]
        except ValueError:
            return fr, False
        if px["els"] == fr["els"] and np.abs(px["xyz"] - fr["xyz"]).max() < 1e-4:
            return dict(fr, lines=px["lines"], xyz=px["xyz"]), True
    return fr, False


def imaginary(c):
    return [f for f in (c.get("freqs") or []) if float(f) < 0]


def calc_warnings(c):
    """Hinweise für die Anzeige (nicht für den SI-Text)."""
    w = []
    if not c["normal"]:
        w.append(T("dft_w_abnormal"))
    if c["opt_requested"] and not c["opt_converged"]:
        w.append(T("dft_w_not_converged"))
    elif c["opt_converged"] and any(r[3] == "NO" for r in c["conv"]):
        w.append(T("dft_w_partly"))
    if not c["opt_requested"]:
        w.append(T("dft_w_no_opt"))
    if c["freq_requested"] and not c["freqs"]:
        w.append(T("dft_w_no_freq"))
    im = imaginary(c)
    if im:
        w.append(T("dft_w_imag", n=len(im), v=", ".join(XRAY.minus(f) for f in im)))
    if c["freqs"] and not c["thermo"].get("G"):
        w.append(T("dft_w_no_thermo"))
    s = c.get("solvation")
    if s:
        w.append(T("dft_w_solv_smd" if s["model"] == "SMD" else "dft_w_solv_cpcm"))
    return w


CONV_NAMES = {"Energy change": "Energy change", "RMS gradient": "RMS gradient", "MAX gradient": "Max. gradient",
              "RMS step": "RMS step", "MAX step": "Max. step", "Maximum Force": "Max. force", "RMS Force": "RMS force",
              "Maximum Displacement": "Max. displacement", "RMS Displacement": "RMS displacement"}


SI_DEFAULTS = dict(method="each", conv=True, freq=True, zpe=False)
METHOD_MODES = ("each", "top", "off")            # Methode je Struktur / einmal oben („Computational details“) / gar nicht


def method_mode(v):
    """Gespeicherter Wert -> Modus (frühere Fassung: True/False)."""
    return "each" if v is True else "off" if v is False else v if v in METHOD_MODES else "each"


def method_line(c):
    prog = c["program"] + (f" {c['version']}" if c["version"] else "")
    return prog, " ".join(c["keywords"])


def computational_details(items):
    """items = [(Name, Rechnung)] -> [(Klartext, HTML)]: je verschiedener Eingabezeile ein Absatz; bei mehreren
    Methoden mit den Strukturen dahinter (wie „Sample Input Files“ in der SI, aber ohne Platzhalter)."""
    import html as _h
    groups = {}
    for name, c in items:
        if c["keywords"]:
            groups.setdefault(method_line(c), []).append(name)
    out = []
    for (prog, kw), names in groups.items():
        t = f"{prog}: {kw}"
        h = f"{_h.escape(prog)}: {_h.escape(kw)}"
        if len(groups) > 1:
            t += f" ({', '.join(names)})"
            h += f" ({_h.escape(', '.join(names))})"
        elif len(names) > 1:
            t, h = "All calculations: " + t, "All calculations: " + h
        out.append((t, h))
    return out


def pg_html(pg):
    """Punktgruppe mit tiefgestelltem Rest: C2h -> C<sub>2h</sub> (Gaussian schreibt C2H)."""
    pg = (pg or "").strip()
    return f"{pg[0].upper()}<sub>{pg[1:].lower()}</sub>" if len(pg) > 1 else pg


def mono_lines(lines):
    """Koordinatenzeilen für Festbreitenschrift: gemeinsamen Einzug entfernen, sonst unverändert."""
    lines = [ln.rstrip() for ln in lines]
    ind = min((len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()), default=0)
    return [ln[ind:] for ln in lines]


def si_parts(c, name, coord_lines, opts=None):
    """SI-Block (englisch, Aufbau wie die SI der Gruppe): Name, Abbildung, „Charge/Multiplicity/Point group“,
    wahlweise Methode/Konvergenz/Frequenzen, Koordinaten (Festbreite, Zeilen unverändert), Energietabelle.
    -> dict(name, fields, extra=[(Klartext, HTML)], conv, conv_at, coords=[Zeilen], energies=(Köpfe, Werte))"""
    import html as _h
    o = dict(SI_DEFAULTS, **(opts or {}))
    o["method"] = method_mode(o["method"])
    mi = XRAY.minus
    f_pl, f_ht = [], []
    if c["charge"] is not None:
        f_pl.append(f"Charge: {mi(str(c['charge']))}")
    if c["mult"] is not None:
        f_pl.append(f"Multiplicity: {c['mult']}")
    f_ht = [_h.escape(x) for x in f_pl]
    if c.get("point_group"):
        f_pl.append(f"Point group: {c['point_group']}")
        f_ht.append(f"Point group: <i>{pg_html(c['point_group'])}</i>")
    extra, conv_at = [], 0
    s = c.get("solvation")
    if o["method"] == "each":
        prog, kw = method_line(c)
        if kw:
            extra.append((f"{prog}: {kw}", f"{_h.escape(prog)}: {_h.escape(kw)}"))
        if s:
            bits = [x for x in (s["solvent"].lower() if s["solvent"] else "",
                                f"ε = {s['eps']}" if s["eps"] else "") if x]
            t = f"Solvation: {s['model']}" + (f" ({', '.join(bits)})" if bits else "") + "."
            extra.append((t, _h.escape(t)))
    if o["conv"] and c["opt_requested"]:
        t = ("Geometry optimisation converged" if c["opt_converged"] else "Geometry optimisation NOT converged") + \
            (" (final cycle):" if c["conv"] else ".")
        extra.append((t, _h.escape(t)))
    conv_at = len(extra)                                   # Konvergenztabelle direkt unter dieser Zeile
    th = c["thermo"]
    if o["freq"] and c["freqs"] is not None:
        im = imaginary(c)
        if not im:
            t = "Frequency calculation: no imaginary frequencies."
        else:
            t = (f"Frequency calculation: {len(im)} imaginary frequenc{'y' if len(im) == 1 else 'ies'} "
                 f"({', '.join(mi(f) for f in im)} cm-1).")
        if th.get("G") and th.get("T"):
            t = t[:-1] + f"; thermochemistry at {th['T']} K" + (f" and {th['P']} atm" if th.get("P") else "") + \
                (" (quasi-RRHO)" if th.get("qrrho") else "") + "."
        extra.append((t, _h.escape(t).replace("cm-1", "cm<sup>-1</sup>")))
    if o["method"] != "off" and s and s.get("e_diel"):
        t = f"{s['model'] if s['model'] == 'CPCM' else 'CPCM/SMD'} dielectric energy (included in E(el)): " \
            f"{mi(s['e_diel'])} Eh"
        if s.get("e_cds"):
            t += f"; SMD cavity/dispersion term: {mi(s['e_cds'])} Eh"
        extra.append((t + ".", _h.escape(t).replace("Eh", "E<sub>h</sub>") + "."))
    conv = (["Item", "Value", "Threshold", "Conv."],
            [[CONV_NAMES.get(r[0], r[0]), mi(r[1]), r[2], r[3].lower()] for r in c["conv"]]) \
        if o["conv"] and c["conv"] else None
    e_el = th.get("E_el") or c["energy"]
    cols = [(k, v) for k, v in (("E_el", e_el), ("ZPE", th.get("ZPE") if o["zpe"] else None), ("H", th.get("H")),
                                ("G", th.get("G"))) if v]
    energies = None
    if cols:
        head = {"E_el": ("*E*_{el} [E_{h}]", "E_el [Eh]"), "ZPE": ("ZPE [E_{h}]", "ZPE [Eh]"),
                "H": ("*H* [E_{h}]", "H [Eh]"), "G": ("*G* [E_{h}]", "G [Eh]")}
        energies = ([head[k][0] for k, _ in cols], [head[k][1] for k, _ in cols], [mi(v) for _, v in cols])
    return dict(name=name, fields=(f_pl, f_ht), extra=extra, conv=conv, conv_at=conv_at,
                coords=[mi(ln) for ln in mono_lines(coord_lines)], energies=energies)


def si_plain(p):
    """SI-Block als Text (Tabellen mit Tabulatoren, lassen sich in Word in eine Tabelle umwandeln)."""
    k = p["conv_at"]
    out = [p["name"], "\t".join(p["fields"][0])] + [pl for pl, _ in p["extra"][:k]]
    if p["conv"]:
        out += ["\t".join(p["conv"][0])] + ["\t".join(r) for r in p["conv"][1]]
    out += [pl for pl, _ in p["extra"][k:]] + [""] + p["coords"]
    if p["energies"]:
        out += ["", "\t".join(p["energies"][1]), "\t".join(p["energies"][2])]
    return "\n".join(out)


def si_html(p):
    import html as _h

    def table(head, rows, raw_head=False):
        return ("<table cellspacing='0' cellpadding='2'><tr>" +
                "".join(f"<th>{h if raw_head else _h.escape(h)}</th>" for h in head) + "</tr>" +
                "".join("<tr>" + "".join(f"<td align='right'>{_h.escape(v)}</td>" for v in r) + "</tr>"
                        for r in rows) + "</table>")
    k = p["conv_at"]
    out = [f"<p><b>{_h.escape(p['name'])}</b></p>", "<p>" + "&nbsp;&nbsp;&nbsp;&nbsp;".join(p["fields"][1]) + "</p>"]
    out += [f"<p>{h}</p>" for _, h in p["extra"][:k]]
    if p["conv"]:
        out.append(table(*p["conv"]))
    out += [f"<p>{h}</p>" for _, h in p["extra"][k:]]
    out.append("<pre style='font-size:8pt'>" + _h.escape("\n".join(p["coords"])) + "</pre>")
    if p["energies"]:
        heads = [XRAY.to_html(h) for h in p["energies"][0]]
        out.append(table(heads, [p["energies"][2]], raw_head=True))
    return "".join(out)


def write_xyz(path, frames, order=None):
    """Alle Bilder in der Reihenfolge order (Atomindizes der Datei) schreiben; Zeilen unverändert."""
    n = len(frames[0]["lines"])
    order = list(range(n)) if order is None else list(order)
    if sorted(order) != list(range(n)):
        raise ValueError("order is not a permutation of the atoms")
    out = []
    for f in frames:
        out += [str(n), f["comment"]] + [f["lines"][k] for k in order]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    return path


# ---------------------------------------------------------------------------- Modell
def bonds_of(els, xyz, chunk=400):
    """Bindungen aus kovalenten Radien (wie X-Ray): [(i, j)] mit i < j."""
    xyz = np.asarray(xyz, float)
    rad = np.array([XRAY.COV.get(e, 1.5) for e in els])
    isH = np.array([e in H_ELS for e in els])
    out = []
    for s in range(0, len(els), chunk):                  # zeilenweise in Blöcken: Speicher bleibt klein
        d = np.linalg.norm(xyz[s:s + chunk, None, :] - xyz[None, :, :], axis=2)
        cut = rad[s:s + chunk, None] + rad[None, :] + XRAY.BOND_TOL
        hit = (d > 0.4) & (d < cut) & ~(isH[s:s + chunk, None] & isH[None, :])
        for a, b in np.argwhere(hit):
            if s + a < b:
                out.append((int(s + a), int(b)))
    return out


class XyzMolecule(XRAY.Molecule):
    """Molekül aus einer xyz-Geometrie mit der Schnittstelle von X-Ray (XrayFigure, default_view, Fragmente).
    Atomindex = Index in der Datei, Schlüssel „a<Index>“ bleibt beim Umnummerieren gleich."""

    def __init__(self, els, xyz, bonds, labels, uiso=0.0264):
        self.S, self.truncated, self.ops = None, False, {}
        self.atoms = [dict(asu=i, label=labels[i], el=e, xyz=np.asarray(xyz[i], float), U=None, uiso=uiso, part=0,
                           generated=False, sym="", opkey="", key=f"a{i}") for i, e in enumerate(els)]
        self.bonds = sorted(bonds)
        self._fragments()


def renumber(order, picked, els=None, nbrs=None):
    """Neue Reihenfolge: angeklickte Atome (Dateiindizes) zuerst, Rest in der bisherigen Reihenfolge. Mit nbrs
    (Nachbarn je Atom) folgen die nicht angeklickten H direkt ihrem Atom."""
    order = list(order)
    inside = set(order)
    picked = [k for k in dict.fromkeys(picked) if k in inside]
    chosen = set(picked)
    rest = [k for k in order if k not in chosen]
    if nbrs is None or els is None:
        return picked + rest
    pos = {k: i for i, k in enumerate(order)}
    seq, placed = [], set()
    for k in picked + [r for r in rest if els[r] not in H_ELS]:
        if k in placed:
            continue
        seq.append(k)
        placed.add(k)
        for h in sorted(nbrs.get(k, ()), key=pos.get):
            if els[h] in H_ELS and h not in placed and h not in chosen:
                seq.append(h)
                placed.add(h)
    return seq + [k for k in rest if k not in placed]


# ---------------------------------------------------------------------------- Vergleichsmodus (Nummerierung übernehmen)
def _graph(els, idx, bonds):
    """RDKit-Molekül nur aus Elementen und Verknüpfung (Einfachbindungen, keine impliziten H)."""
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    pos = {k: i for i, k in enumerate(idx)}
    rw = Chem.RWMol()
    for k in idx:
        a = Chem.Atom(pt.GetAtomicNumber(els[k]))
        a.SetNoImplicit(True)
        rw.AddAtom(a)
    for a, b in bonds:
        if a in pos and b in pos and rw.GetBondBetweenAtoms(pos[a], pos[b]) is None:
            rw.AddBond(pos[a], pos[b], Chem.BondType.SINGLE)
    m = rw.GetMol()
    m.UpdatePropertyCache(strict=False)
    Chem.FastFindRings(m)
    return m


def kabsch(P, Q):
    """Beste Überlagerung von P auf Q (n×3); Spiegelung erlaubt (Enantiomer im Kristall) -> (RMSD, R, cP, cQ)."""
    cP, cQ = P.mean(axis=0), Q.mean(axis=0)
    U, _, Vt = np.linalg.svd((P - cP).T @ (Q - cQ))
    d0 = np.sign(np.linalg.det(Vt.T @ U.T)) or 1.0

    def fit(d):
        R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
        return float(np.sqrt(np.mean(np.sum(((R @ (P - cP).T).T - (Q - cQ)) ** 2, axis=1)))), R
    # echte Drehung (det = +1); Spiegelung nur, wenn sie deutlich besser passt – bei ebenen Schweratomen passen
    # beide gleich gut, dann zählt die Drehung (sonst werden H-Atome ober- und unterhalb der Ebene vertauscht)
    rp, Rp = fit(d0)
    rm, Rm = fit(-d0)
    return (rm, Rm, cP, cQ) if rm < rp - 1e-3 else (rp, Rp, cP, cQ)


MATCH_MAX = 20000            # Obergrenze für Zuordnungen (symmetrische Gruppen: tBu, Phenyl … vervielfachen sie)
AMBIG_TOL = 0.05             # Å: zweite Zuordnung praktisch so gut wie die beste -> als mehrdeutig warnen


def match_reference(ref, tgt):
    """Nummerierung einer Vorlage auf eine Geometrie übertragen. ref/tgt = dict(els, xyz, bonds, order, labels?).
    Schweratome über die Verknüpfung (Substruktur, sonst gemeinsamer Teil ≥ 80 %), bei mehreren Zuordnungen die mit
    der kleinsten Abweichung nach Überlagerung; H über ihr Schweratom und den Abstand nach Überlagerung.
    -> dict(order, labels, n_heavy, n_ref_heavy, n_tgt_heavy, n_h, rmsd, rmsd_alt (nächstbeste andere Zuordnung bei
    symmetrischem Bindungsnetz), ambiguous=[Vorlagen-Labels, wenn rmsd_alt ≤ rmsd + AMBIG_TOL], partial, truncated);
    ValueError, wenn nichts passt."""
    from rdkit import Chem
    from rdkit.Chem import rdFMCS
    rH = [k for k, e in enumerate(ref["els"]) if e not in H_ELS]
    tH = [k for k, e in enumerate(tgt["els"]) if e not in H_ELS]
    rg, tg = _graph(ref["els"], rH, ref["bonds"]), _graph(tgt["els"], tH, tgt["bonds"])
    small_ref = len(rH) <= len(tH)
    q, m = (rg, tg) if small_ref else (tg, rg)
    hits = m.GetSubstructMatches(q, uniquify=False, maxMatches=MATCH_MAX, useChirality=False)
    partial = False
    if hits:
        pairs = [list(zip(range(len(h)), h)) for h in hits]           # (Index in q, Index in m)
    else:
        res = rdFMCS.FindMCS([q, m], timeout=10, atomCompare=rdFMCS.AtomCompare.CompareElements,
                             bondCompare=rdFMCS.BondCompare.CompareAny, ringMatchesRingOnly=False)
        if not res.numAtoms or res.numAtoms < max(3, 0.8 * q.GetNumAtoms()):
            raise ValueError(T("dft_match_none"))
        sm = Chem.MolFromSmarts(res.smartsString)
        qm = q.GetSubstructMatch(sm)
        mm = m.GetSubstructMatches(sm, uniquify=False, maxMatches=MATCH_MAX)
        pairs = [list(zip(qm, h)) for h in mm]
        partial = True
    truncated = len(pairs) >= MATCH_MAX
    rxyz, txyz = np.asarray(ref["xyz"], float), np.asarray(tgt["xyz"], float)
    scored = []
    for pr in pairs:
        mp = {(rH[a] if small_ref else rH[b]): (tH[b] if small_ref else tH[a]) for a, b in pr}   # ref -> tgt
        rk = list(mp)
        r, R, cP, cQ = kabsch(txyz[[mp[k] for k in rk]], rxyz[rk])
        scored.append((r, mp, R, cP, cQ))
    scored.sort(key=lambda s: s[0])
    rmsd, best, R, cP, cQ = scored[0]
    # symmetrisches Bindungsnetz: nächstbeste andere Zuordnung immer melden (gewählt wird nach Geometrie)
    alt = next(((r2, mp2) for r2, mp2, *_ in scored[1:] if mp2 != best), None)
    amb = {k for k in best if alt and alt[1].get(k) != best[k]} if alt and alt[0] - rmsd <= AMBIG_TOL else set()
    # H: je zugeordnetem Schweratom die H-Nachbarn nach Abstand (Ziel auf die Vorlage überlagert)
    def h_nbrs(g, k):
        return [j for a, b in g["bonds"] for j in ((b,) if a == k else (a,) if b == k else ())
                if g["els"][j] in H_ELS]
    t_al = (R @ (txyz - cP).T).T + cQ
    full = dict(best)
    used = set(best.values())
    for rk, tk in best.items():
        rh, th = h_nbrs(ref, rk), [j for j in h_nbrs(tgt, tk) if j not in used]
        cand = sorted((float(np.linalg.norm(t_al[j] - rxyz[i])), i, j) for i in rh for j in th)
        for _, i, j in cand:                           # gierig nach Abstand (je Atom höchstens 3–4 H)
            if i not in full and j not in used:
                full[i] = j
                used.add(j)
    ref_order = list(ref.get("order") or range(len(ref["els"])))
    new = [full[k] for k in ref_order if k in full]
    new += [k for k in (tgt.get("order") or range(len(tgt["els"]))) if k not in used]
    labels = {full[k]: ref["labels"][k] for k in full} if ref.get("labels") else {}
    rl = ref.get("labels") or {}
    return dict(order=new, labels=labels, n_heavy=len(best), n_ref_heavy=len(rH), n_tgt_heavy=len(tH),
                n_h=len(full) - len(best), rmsd=rmsd, rmsd_alt=alt[0] if alt else None, partial=partial,
                truncated=truncated,
                ambiguous=sorted((rl.get(k) or f"{ref['els'][k]}{ref_order.index(k) + 1}" for k in amb),
                                 key=lambda s: (re.sub(r"\d.*", "", s), len(s), s)))


def number_of(order, base=1):
    """Dateiindex -> angezeigte Nummer."""
    return {k: i + base for i, k in enumerate(order)}


def is_xyz(path):
    return Path(path).suffix.lower() == ".xyz" and Path(path).is_file()


def is_calc(path):
    """ORCA-/Gaussian-Ausgabe (.out/.log, am Kopf erkannt)."""
    p = Path(path)
    if p.suffix.lower() not in (".out", ".log") or not p.is_file():
        return False
    try:
        with open(p, "rb") as fh:
            head = decode(fh.read(60000))
    except OSError:
        return False
    return is_orca(head) or is_gaussian(head)


def make_test_xyz(path):
    """Künstliches Molekül für den Selbsttest (Chlorethan, Bindungslängen gerundet, zwei Bilder wie eine kurze
    Trajektorie, Windows-Zeilenenden). Kein echter Datensatz."""
    atoms = [("H", 1.48, 0.0, -1.60), ("C", 0.0, 0.0, 0.0), ("Cl", 0.0, 0.0, 1.79), ("C", 1.43, 0.0, -0.51),
             ("H", -0.51, 0.89, -0.36), ("H", -0.51, -0.89, -0.36), ("H", 1.96, 0.89, -0.15),
             ("H", 1.96, -0.89, -0.15)]           # erstes Atom = H am zweiten C: Reihenfolge absichtlich „unordentlich“
    lines = []
    for title, dz in (("start geometry", 0.05), ("E -539.123456789 (test)", 0.0)):
        lines += [str(len(atoms)), title]
        lines += [f"  {el:<2s} {x:12.6f} {y:12.6f} {z + (dz if el == 'Cl' else 0.0):12.6f}" for el, x, y, z in atoms]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\r\n".join(lines) + "\r\n")                 # Windows-Zeilenenden wie aus ORCA unter Windows
    return Path(path)


_TEST_GEOM = [("C", "0.000000", "0.000000", "0.000000"), ("Cl", "0.000000", "0.000000", "1.790000"),
              ("C", "1.430000", "0.000000", "-0.510000"), ("H", "-0.510000", "0.890000", "-0.360000"),
              ("H", "-0.510000", "-0.890000", "-0.360000"), ("H", "1.960000", "0.890000", "-0.150000"),
              ("H", "1.960000", "-0.890000", "-0.150000"), ("H", "1.480000", "0.000000", "-1.600000")]


def make_test_orca(path):
    """Künstliche ORCA-6-Ausgabe (nur die gelesenen Abschnitte, Format wie ORCA 6.1; Zahlen erfunden) als UTF-16 mit
    CRLF wie aus der Windows-PowerShell: Opt + Freq mit CPCM, eine imaginäre Frequenz. Kein echter Datensatz."""
    geo = [f"  {el:<2s}  {x:>12s} {y:>12s} {z:>12s}" for el, x, y, z in _TEST_GEOM]
    L = ["", "                                 *****************", "                                 * O   R   C   A *",
         "                                 *****************", "", "                 Program Version 6.1.1 -  RELEASE  -",
         "", "================================================================================",
         "                                       INPUT FILE",
         "================================================================================", "NAME = test.inp",
         "|  1> %pal nprocs 4 end", "|  2> ! B3LYP D4 def2-SVP TightOpt Freq CPCM(thf)", "|  3> * xyz 0 1"]
    L += [f"|{i + 4:3d}> {g.strip()}" for i, g in enumerate(geo)]
    L += [f"|{len(geo) + 4:3d}> *", "|{0:3d}> ".format(len(geo) + 5) + "                        ****END OF INPUT****",
          "", " Total Charge           Charge          ....    0", " Multiplicity           Mult            ....    1",
          "", "CPCM SOLVATION MODEL", "--------------------", "CPCM parameters:",
          "  Epsilon                                         ...       7.5650",
          "Solvent:                                          ... TETRAHYDROFURAN", "",
          "CPCM Dielectric    :         -0.00412345678901 Eh              -0.11221 eV", "",
          "          ----------------------|Geometry convergence|-------------------------",
          "          Item                value                   Tolerance       Converged",
          "          ---------------------------------------------------------------------",
          "          Energy change      -0.0000002000            0.0000010000      YES",
          "          RMS gradient        0.0000150000            0.0000300000      YES",
          "          MAX gradient        0.0000500000            0.0001000000      YES",
          "          RMS step            0.0002000000            0.0006000000      YES",
          "          MAX step            0.0008000000            0.0010000000      YES",
          "          ---------------------------------------------------------------------", "",
          "                    ***********************HURRAY********************",
          "                    ***        THE OPTIMIZATION HAS CONVERGED     ***", "",
          "---------------------------------", "CARTESIAN COORDINATES (ANGSTROEM)",
          "---------------------------------"] + geo + ["", "-------------------------   --------------------",
                                                         "FINAL SINGLE POINT ENERGY      -539.987654321098",
                                                         "", "-----------------------", "VIBRATIONAL FREQUENCIES",
                                                         "-----------------------", ""]
    fr = ["0.00"] * 6 + ["-31.20", "245.10", "330.40", "655.70", "790.00", "980.30", "1010.50", "1080.20", "1260.30",
                         "1290.80", "1450.10", "1460.40", "1470.20", "1480.90", "3010.20", "3050.70", "3080.10",
                         "3110.60"]
    L += [f"   {i:2d}:   {v:>9s} cm**-1" + ("  ***imaginary mode***" if v.startswith("-") else "")
          for i, v in enumerate(fr)]
    L += ["", "--------------------------", "THERMOCHEMISTRY AT 298.15K", "--------------------------", "",
          "Temperature         ...   298.15 K", "Pressure            ...     1.00 atm",
          "Quasi RRHO          ...     True",
          "Electronic energy                ...   -539.98765432 Eh",
          "Zero point energy                ...      0.06543210 Eh      41.06 kcal/mol",
          "Total thermal energy                   -539.91765432 Eh",
          "Total Enthalpy                    ...   -539.91670987 Eh",
          "Point Group:  C1, Symmetry Number:   1  ",
          "Final entropy term                ...      0.03012345 Eh     18.90 kcal/mol",
          "Final Gibbs free energy         ...   -539.94683332 Eh",
          "G-E(el)                           ...      0.04082100 Eh     25.62 kcal/mol", "",
          "                             ****ORCA TERMINATED NORMALLY****"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"\xff\xfe" + ("\r\n".join(L) + "\r\n").encode("utf-16-le"))
    return Path(path)


def make_test_gaussian(path):
    """Künstliche Gaussian-Ausgabe (Format nach Gaussian 16 aus dem Gedächtnis, Zahlen erfunden): Opt + Freq mit
    SCRF/SMD. Kein echter Datensatz."""
    Z = {"H": 1, "C": 6, "Cl": 17}
    L = [" Entering Gaussian System, Link 0=g16", " Gaussian 16:  ES64L-G16RevC.01  3-Jul-2019",
         " ----------------------------------------------------------------------",
         " #p B3LYP/def2SVP opt freq scrf=(smd,solvent=thf)",
         " ----------------------------------------------------------------------",
         " Charge =  0 Multiplicity = 1"]
    orient = [" " + "-" * 69, " Center     Atomic      Atomic             Coordinates (Angstroms)",
              " Number     Number       Type             X           Y           Z", " " + "-" * 69]
    orient += [f" {i + 1:6d} {Z[el]:10d} {0:11d} {x:>13s} {y:>11s} {z:>11s}" for i, (el, x, y, z) in
               enumerate(_TEST_GEOM)] + [" " + "-" * 69]
    L += ["                         Standard orientation:"] + orient
    L += [" SCF Done:  E(RB3LYP) =  -539.987000000     A.U. after   10 cycles",
          "         Item               Value     Threshold  Converged?",
          " Maximum Force            0.000012     0.000450     YES",
          " RMS     Force            0.000004     0.000300     YES",
          " Maximum Displacement     0.000210     0.001800     YES",
          " RMS     Displacement     0.000070     0.001200     YES", "    -- Stationary point found.",
          " Optimization completed.", " Full point group                 CS      NOp   2"]
    L += ["                         Standard orientation:"] + orient
    L += [" SCF Done:  E(RB3LYP) =  -539.987654321     A.U. after    1 cycles",
          " Frequencies --    245.1023               330.4012               655.7034",
          " Frequencies --    790.0011               980.3022              1010.5013",
          " Temperature   298.150 Kelvin.  Pressure   1.00000 Atm.",
          " Zero-point correction=                           0.065432 (Hartree/Particle)",
          " Sum of electronic and thermal Enthalpies=           -539.916710",
          " Sum of electronic and thermal Free Energies=        -539.946833",
          " Normal termination of Gaussian 16 at Thu Oct 22 10:00:00 2026."]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return Path(path)


# ---------------------------------------------------------------------------- Tab
import matplotlib.patheffects as PE  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure as MplFigure  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,  # noqa: E402
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout)

import uvvis_core as core  # noqa: E402
import uvvis_project as PRJ  # noqa: E402
import uvvis_tabs as TABS  # noqa: E402
from uvvis_style import HINT_CSS, WARN_CSS, make_form  # noqa: E402

PICK_COLOR = XRAY.SEL_COLOR
OLD_COLOR = "#9a9a9a"


class DFTTab(TABS.FigureTab):
    STATE_KEY = "dft"
    TEXT_OPTS = ("fonts", "labels")               # Labelgröße hat der Tab selbst
    DEFAULT_STATE = dict(size="half_a4", w_cm=16.0, h_cm=11.0, fmt={"pdf": True, "svg": True, "png": True},
                         layout={}, entries=[], current=None, show_h=True, labels=True, h_labels=True, export_labels=False,
                         label_style="el_num", zero_based=False, radius=0.25, bond_w=0.08, style="mercury",
                         h_follow=False, x_auto=True, x_min=0.0, x_max=1.0, ymax=0.0)

    # Größe/Formate wie im X-Ray-Tab (keine Achsen)
    common_box = XRAY.XrayTab.common_box
    _sync_common = XRAY.XrayTab._sync_common
    collect_common = XRAY.XrayTab.collect_common

    def __init__(self, main, state):
        self.numbering = False            # Klick-Modus „Nummerieren“ (nicht im Undo)
        self.picks = []                   # angeklickte Dateiindizes in Klickreihenfolge
        super().__init__(main, state)

    # -- Bedienelemente -------------------------------------------------------------------
    def build_controls(self):
        st = self.st
        g = QGroupBox(T("dft_structures"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("dft_add"), self.add_xyz), (T("remove"), self.remove_entry)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.tbl = QTableWidget(0, 2)
        self.tbl.setHorizontalHeaderLabels([T("dft_name"), T("dft_file")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setMinimumHeight(100)
        self.tbl.itemChanged.connect(self.entry_edited)
        self.tbl.itemSelectionChanged.connect(self.entry_selected)
        v.addWidget(self.tbl)
        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_info)
        self.lv.addWidget(g)

        g = QGroupBox(T("dft_si"))
        v = QVBoxLayout(g)
        self.lbl_warn = QLabel("")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setStyleSheet(WARN_CSS)
        v.addWidget(self.lbl_warn)
        self.txt_si = QTextBrowser()
        self.txt_si.setMinimumHeight(180)
        v.addWidget(self.txt_si)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("dft_si_with")))
        self.cmb_method = QComboBox()
        for k in METHOD_MODES:
            self.cmb_method.addItem(T("dft_method_" + k), k)
        self.cmb_method.setToolTip(T("dft_method_tip"))
        self.cmb_method.currentIndexChanged.connect(self.si_opts_changed)
        row.addWidget(self.cmb_method)
        self.cb_si = {}
        for k in ("conv", "freq", "zpe"):
            cb = QCheckBox(T("dft_si_" + k))
            cb.setChecked(self.st.get("si_" + k, SI_DEFAULTS[k]))
            cb.toggled.connect(self.si_opts_changed)
            self.cb_si[k] = cb
            row.addWidget(cb)
        row.addStretch(1)
        v.addLayout(row)
        row = QHBoxLayout()
        self.btn_si_copy = QPushButton(T("dft_si_copy"))
        self.btn_si_copy.setToolTip(T("dft_si_copy_tip"))
        self.btn_si_copy.clicked.connect(self.copy_si)
        self.btn_si_word = QPushButton(T("dft_si_word"))
        self.btn_si_word.setToolTip(T("dft_si_word_tip"))
        self.btn_si_word.clicked.connect(lambda: self.save_docx())
        row.addWidget(self.btn_si_copy)
        row.addWidget(self.btn_si_word)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

        g = QGroupBox(T("dft_numbering"))
        v = QVBoxLayout(g)
        self.btn_num = QPushButton(T("dft_num_start"))
        self.btn_num.setCheckable(True)
        self.btn_num.setToolTip(T("dft_num_tip"))
        self.btn_num.toggled.connect(self.set_numbering)
        v.addWidget(self.btn_num)
        self.lbl_num = QLabel("")
        self.lbl_num.setWordWrap(True)
        v.addWidget(self.lbl_num)
        row = QHBoxLayout()
        self.btn_undo_pick = QPushButton(T("dft_num_back"))
        self.btn_undo_pick.clicked.connect(self.undo_pick)
        self.btn_apply = QPushButton(T("dft_num_apply"))
        self.btn_apply.clicked.connect(self.apply_numbering)
        row.addWidget(self.btn_undo_pick)
        row.addWidget(self.btn_apply)
        row.addStretch(1)
        v.addLayout(row)
        self.cb_hfollow = QCheckBox(T("dft_h_follow"))
        self.cb_hfollow.setToolTip(T("dft_h_follow_tip"))
        self.cb_hfollow.setChecked(st.get("h_follow", False))
        v.addWidget(self.cb_hfollow)
        row = QHBoxLayout()
        row.addWidget(QLabel(T("dft_ref")))
        self.cmb_ref = QComboBox()
        self.cmb_ref.setToolTip(T("dft_ref_tip"))
        row.addWidget(self.cmb_ref, 1)
        self.btn_ref = QPushButton(T("dft_ref_apply"))
        self.btn_ref.clicked.connect(self.apply_reference)
        row.addWidget(self.btn_ref)
        v.addLayout(row)
        self.lbl_ref = QLabel("")
        self.lbl_ref.setWordWrap(True)
        self.lbl_ref.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_ref)
        row = QHBoxLayout()
        b = QPushButton(T("dft_order_reset"))
        b.setToolTip(T("dft_order_reset_tip"))
        b.clicked.connect(self.reset_order)
        row.addWidget(b)
        b = QPushButton(T("dft_save_xyz"))
        b.setToolTip(T("dft_save_xyz_tip"))
        b.clicked.connect(lambda: self.save_xyz())
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

        g = QGroupBox(T("xr_display"))
        f = make_form(g)
        self.cmb_style = QComboBox()
        for key in ("mercury", "flat"):
            self.cmb_style.addItem(T("xr_style_" + key), key)
        f.addRow(T("xr_style"), self.cmb_style)
        self.cb_h = QCheckBox(T("xr_show_h"))
        self.cb_lab = QCheckBox(T("xr_labels"))
        self.cb_hlab = QCheckBox(T("xr_h_labels"))
        row = QHBoxLayout()
        for w_ in (self.cb_h, self.cb_lab, self.cb_hlab):
            row.addWidget(w_)
        row.addStretch(1)
        f.addRow(row)
        self.cb_explab = QCheckBox(T("dft_export_labels"))
        self.cb_explab.setToolTip(T("dft_export_labels_tip"))
        f.addRow(self.cb_explab)
        self.cmb_lstyle = QComboBox()
        for key in ("el_num", "num", "ref"):
            self.cmb_lstyle.addItem(T("dft_lab_" + key), key)
        self.cmb_lstyle.setToolTip(T("dft_lab_ref_tip"))
        f.addRow(T("dft_label_style"), self.cmb_lstyle)
        self.cb_zero = QCheckBox(T("dft_zero_based"))
        self.cb_zero.setToolTip(T("dft_zero_based_tip"))
        f.addRow(self.cb_zero)
        self.sp_rad = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=0.8, singleStep=0.01, suffix=" Å")
        f.addRow(T("dft_radius"), self.sp_rad)
        self.sp_bond = QDoubleSpinBox(decimals=2, minimum=0.02, maximum=0.4, singleStep=0.01, suffix=" Å")
        f.addRow(T("xr_bond_lw"), self.sp_bond)
        self.sp_lab = XRAY.label_size_spin(self.st)
        f.addRow(T("xr_label_size"), self.sp_lab)
        b = QPushButton(T("xr_reset_view"))
        b.clicked.connect(self.reset_view)
        f.addRow(b)
        hint = QLabel(T("dft_mouse_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        self.lv.addWidget(g)

        for w_ in (self.sp_rad, self.sp_bond, self.sp_lab):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cmb_style, self.cmb_lstyle):
            w_.currentIndexChanged.connect(self.changed)
        for w_ in (self.cb_h, self.cb_lab, self.cb_hlab, self.cb_zero, self.cb_hfollow, self.cb_explab):
            w_.toggled.connect(self.changed)
        self.sync_widgets()

    def collect(self):
        self.st.update(show_h=self.cb_h.isChecked(), labels=self.cb_lab.isChecked(), h_labels=self.cb_hlab.isChecked(),
                       label_style=self.cmb_lstyle.currentData(), zero_based=self.cb_zero.isChecked(),
                       radius=self.sp_rad.value(), bond_w=self.sp_bond.value(), label_pt=self.sp_lab.value(), style=self.cmb_style.currentData(),
                       h_follow=self.cb_hfollow.isChecked(), export_labels=self.cb_explab.isChecked())
        self.update_num_status()

    def sync_widgets(self):
        self._loading = True
        st = self.st
        es = self.entries()
        self.tbl.setRowCount(len(es))
        for r, e in enumerate(es):
            self.tbl.setItem(r, 0, QTableWidgetItem(e.get("name") or ""))
            it = QTableWidgetItem(Path(e["file"]).name)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(r, 1, it)
        cur = self.entry()
        if cur is not None:
            self.tbl.selectRow(es.index(cur))
        self.cmb_style.setCurrentIndex(max(0, self.cmb_style.findData(st.get("style", "mercury"))))
        self.cmb_lstyle.setCurrentIndex(max(0, self.cmb_lstyle.findData(st.get("label_style", "el_num"))))
        self.cb_h.setChecked(st["show_h"])
        self.cb_lab.setChecked(st["labels"])
        self.cb_hlab.setChecked(st["h_labels"])
        self.cb_zero.setChecked(st.get("zero_based", False))
        self.cb_hfollow.setChecked(st.get("h_follow", False))
        self.cb_explab.setChecked(st.get("export_labels", False))
        for k, cb in self.cb_si.items():
            cb.setChecked(st.get("si_" + k, SI_DEFAULTS[k]))
        self.cmb_method.setCurrentIndex(max(0, self.cmb_method.findData(method_mode(st.get("si_method", "each")))))
        self.sp_rad.setValue(st.get("radius", 0.25))
        self.sp_bond.setValue(st.get("bond_w", 0.08))
        self.sp_lab.setValue(st.get("label_pt", 0.0))
        self.fill_refs()
        self._loading = False
        self.update_num_status()

    # -- Einträge -------------------------------------------------------------------------
    def entries(self):
        return self.st["entries"]

    def entry(self):
        es = self.entries()
        cur = self.st.get("current")
        for e in es:
            if e["uid"] == cur:
                return e
        return es[0] if es else None

    def add_xyz(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("dft_add"), self.main.settings.value("last_dir", ""),
                                             f"{T('dft_flt')} (*.xyz *.out *.log);;{T('flt_all')}")
        for p in ps:
            self.load_xyz(p)

    def load_xyz(self, p):
        """xyz oder Ausgabe einer Rechnung (ORCA 6, Gaussian); Name = Dateiname ohne Endung."""
        p = self.main.import_file(p, "data")
        try:
            self.frames_of(p)
        except Exception as ex:
            self.main.error(f"{Path(p).name}: {ex}")
            return None
        e = dict(uid=uuid.uuid4().hex[:8], file=p, name=Path(p).stem, order=None, view=None, zoom=1.0,
                 pan=[0.0, 0.0], layout={}, label_on={})
        self.entries().append(e)
        self.st["current"] = e["uid"]
        self.stop_numbering()
        self.sync_widgets()
        self.render()
        return e

    def remove_entry(self):
        e = self.entry()
        if e is None:
            return
        self.st["entries"] = [x for x in self.entries() if x["uid"] != e["uid"]]
        self.st["current"] = self.entries()[0]["uid"] if self.entries() else None
        self.stop_numbering()
        self.sync_widgets()
        self.render()

    def entry_edited(self, item):
        if self._loading or item.column() != 0:
            return
        es = self.entries()
        if item.row() < len(es):
            es[item.row()]["name"] = item.text().strip()
            self.main.push_undo()

    def entry_selected(self):
        if self._loading:
            return
        rows = self.tbl.selectionModel().selectedRows()
        es = self.entries()
        if rows and rows[0].row() < len(es) and es[rows[0].row()]["uid"] != self.st.get("current"):
            self.st["current"] = es[rows[0].row()]["uid"]
            self.stop_numbering()
            self.sync_widgets()
            self.render()

    # -- Modell ---------------------------------------------------------------------------
    def frames_of(self, p):
        if Path(p).suffix.lower() == ".xyz":
            return self.cache(("xyz", p), lambda: read_xyz(p))
        return [self.calc_geom(p)[0]]

    def calc_geom(self, p):
        """-> (Bild, Partner-xyz benutzt) einer Rechnung."""
        c = self.calc_file(p)
        return self.cache(("calcxyz", p), lambda: calc_frame(c, Path(p).stem, Path(p).with_suffix(".xyz")))

    def calc_file(self, p):
        return self.cache(("calc", p), lambda: read_calc(p))

    def calc_of(self, e):
        """Ausgewertete Rechnung eines Eintrags oder None (reine xyz)."""
        p = e["file"] if e else None
        if not p or Path(p).suffix.lower() == ".xyz" or not Path(p).exists():
            return None
        return self.calc_file(p)

    def si_of(self, e):
        c = self.calc_of(e)
        if c is None:
            return None
        g = self.geometry(e)
        order = self.order(e, len(g[1]))
        lines = g[0][-1]["lines"]
        opts = {k: self.st.get("si_" + k, v) for k, v in SI_DEFAULTS.items()}
        return si_parts(c, e.get("name") or Path(e["file"]).stem, [lines[k] for k in order], opts)

    def geometry(self, e):
        """-> (Bilder, Elemente, Koordinaten des letzten Bildes, Bindungen) oder None."""
        p = e["file"]
        if not p or not Path(p).exists():
            return None
        frames = self.frames_of(p)
        last = frames[-1]
        bonds = self.cache(("xyzbonds", p), lambda: bonds_of(last["els"], last["xyz"]))
        return frames, last["els"], last["xyz"], bonds

    def order(self, e, n):
        o = e.get("order")
        return list(o) if o and sorted(o) == list(range(n)) else list(range(n))

    def base(self):
        return 0 if self.st.get("zero_based") else 1

    def label_text(self, el, num, k=None, e=None):
        """Label eines Atoms: Element + Nummer, nur Nummer oder (Stil „ref“) das Label der Vorlage, z. B. aus der CIF."""
        style = self.st.get("label_style")
        if style == "ref" and k is not None:
            lab = ((e or self.entry() or {}).get("ref_labels") or {}).get(str(k))
            if lab:
                return lab
        return str(num) if style == "num" else f"{el}{num}"

    def molecule(self, e, interactive=True):
        g = self.geometry(e)
        if g is None:
            return None
        _, els, xyz, bonds = g
        num = number_of(self.order(e, len(els)), self.base())
        picked = set()
        if interactive and self.numbering:                         # angeklickte Atome: neue Nummer
            for i, k in enumerate(self.picks):
                num[k] = i + self.base()
            picked = set(self.picks)
        labels = [f"{el}{num[k]}" if k in picked else self.label_text(el, num[k], k, e) for k, el in enumerate(els)]
        r = self.st.get("radius", 0.25)
        return XyzMolecule(els, xyz, bonds, labels, uiso=(r / XRAY.chi2_scale(0.5)) ** 2)

    def view_of(self, e, mol):
        v = e.get("view")
        if v and len(v) == 9:
            return np.array(v, float).reshape(3, 3)
        # anders als bei X-Ray mit H: beim Nummerieren muss jedes Atom anklickbar sein (nichts verdeckt)
        return XRAY.default_view(mol, use=list(range(len(mol.atoms))))

    def layout(self):
        e = self.entry()
        if e is None:
            return {}
        return e.setdefault("layout", {}).setdefault(self.size_key(), {})

    # -- Abbildung ------------------------------------------------------------------------
    def opts(self, e, interactive=True):
        st = self.st
        label_on = dict(e.get("label_on") or {})
        numbering = interactive and self.numbering
        if numbering:
            label_on.update({f"a{k}": True for k in self.picks})
        r = st.get("radius", 0.25)
        # Labels: Vorschau wie eingestellt (zum Nummerieren), Export/Word nur mit „Labels im Export“
        labels = st["labels"] if interactive else st.get("export_labels", False)
        return dict(prob=50, show_h=st["show_h"], labels=labels or numbering, h_labels=st["h_labels"],
                    colors={}, bond_w=st.get("bond_w", 0.08), hidden_frags=[], style=st.get("style", "mercury"),
                    hidden_atoms=[], label_on=label_on, wire=set(), wire_h=False, label_mode="all", hide_kinds=[],
                    label_size=st.get("label_pt", 0.0),
                    h_radius=0.55 * r)

    def build(self, fig, e=None, interactive=True):
        e = e or self.entry()
        if e is None:
            return None
        mol = self.molecule(e, interactive)
        if mol is None or not mol.atoms:
            return None
        cfg = self.base_cfg()
        core.setup_fonts(TABS.plt, cfg)
        lay = e.setdefault("layout", {}).setdefault(self.size_key(), {})
        sel = list(self.picks) if interactive and self.numbering else []
        F = XRAY.XrayFigure(cfg, mol, self.view_of(e, mol), self.opts(e, interactive), lay, fig, selection=sel,
                            zoom=e.get("zoom", 1.0), pan=e.get("pan") or (0.0, 0.0))
        if interactive and self.numbering:
            # neu vergeben: Nummer mittig auf dem Atom (der Auswahlring belegt den Platz daneben), nicht anklickbar,
            # damit ein erneuter Klick das Atom trifft; noch nicht vergebene Labels grau
            picked = {f"lbl_a{k}" for k in self.picks}
            for key, ann in F.ann_items.items():
                if key in picked:
                    ann.xyann = (0.0, 0.0)
                    ann.set_color("white")
                    ann.set_fontweight("bold")
                    ann.set_path_effects([PE.withStroke(linewidth=3.5, foreground=PICK_COLOR)])
                    ann.contains = lambda ev: (False, {})
                else:
                    ann.set_color(OLD_COLOR)
        return F

    def render(self, push=True):
        try:
            if self.dragger:
                self.dragger.disconnect()
                self.dragger = None
            cfg = self.base_cfg()
            self.host.set_figure_size(*cfg["figsize_in"])
            self.F = self.build(self.fig)
            self.preview_stack.setCurrentIndex(0 if self.F is None else 1)
            if self.F is None:
                self.fig.clear()
            else:
                self.dragger = XRAY.XrayMouse(self.F, self)
            self.update_info()
            self.canvas.draw_idle()
            if push:
                self.main.push_undo()
        except Exception as ex:
            import traceback
            self.main.log_signal.emit(traceback.format_exc())
            self.main.statusBar().showMessage(f"{T('err_title')}: {ex}", 8000)

    def update_info(self):
        e = self.entry()
        g = self.geometry(e) if e else None
        if g is None:
            self.lbl_info.setText("")
            self.update_si()
            return
        frames, els, _, _ = g
        bits = [T("dft_info", n=len(els), formula=XRAY.hill(els))]
        if len(frames) > 1:
            bits.append(T("dft_frames", n=len(frames)))
        if self.calc_of(e) is not None:
            bits.append(T("dft_partner_used") if self.calc_geom(e["file"])[1] else T("dft_partner_none"))
        if frames[-1]["comment"].strip():
            bits.append(T("dft_comment", c=frames[-1]["comment"].strip()[:120]))
        mol = self.F.mol if self.F is not None else None
        if mol is not None and len(mol.fragments) > 1:
            bits.append(T("dft_fragments", n=len(mol.fragments)))
        bits.append(T("dft_renumbered") if e.get("order") else T("dft_file_order"))
        self.lbl_info.setText("\n".join(bits))
        self.update_si()

    def update_si(self):
        e = self.entry()
        c = self.calc_of(e) if e else None
        self.btn_si_copy.setEnabled(c is not None)
        self.btn_si_word.setEnabled(any(self.calc_of(x) is not None for x in self.entries()))
        self.lbl_warn.setVisible(c is not None and bool(calc_warnings(c)))
        if c is None:
            self.lbl_warn.setText("")
            self.txt_si.setHtml(f"<p style='color:gray'>{T('dft_si_hint')}</p>")
            return
        self.lbl_warn.setText("\n".join(calc_warnings(c)))
        self.txt_si.setHtml(si_html(self.si_of(e)))

    def si_opts_changed(self, *_):
        if self._loading:
            return
        for k, cb in self.cb_si.items():
            self.st["si_" + k] = cb.isChecked()
        self.st["si_method"] = self.cmb_method.currentData()
        self.update_si()
        self.main.push_undo()

    def copy_si(self):
        e = self.entry()
        p = self.si_of(e)
        if p is not None:
            from uvvis_irms import copy_rich
            pl, ht = si_plain(p), si_html(p)
            if method_mode(self.st.get("si_method")) == "top":
                det = computational_details([(p["name"], self.calc_of(e))])
                pl = "\n".join(t for t, _ in det) + "\n\n" + pl
                ht = "".join(f"<p>{h}</p>" for _, h in det) + ht
            copy_rich(pl, ht)
            self.main.statusBar().showMessage(T("dft_si_copied"), 4000)

    # -- Maus (Schnittstelle von XrayMouse) -----------------------------------------------
    def hover_atom(self, k):
        if self.F is None or k is None:
            self.main.show_hover("")
            return
        e = self.entry()
        a = self.F.mol.atoms[k]
        cur = number_of(self.order(e, len(self.F.mol.atoms)), self.base())[k]
        txt = self.label_text(a["el"], cur, k, e)
        if e.get("order"):
            txt += "   " + T("dft_hover_file", lab=f"{a['el']}{k + self.base()}")
        self.main.show_hover(txt)

    def atom_clicked(self, k):
        """Im Modus „Nummerieren“: Atom erhält die nächste Nummer; erneuter Klick nimmt es wieder heraus."""
        if not self.numbering or self.F is None or k is None:
            return
        if k in self.picks:
            self.picks.remove(k)
        else:
            self.picks.append(k)
        self.update_num_status()
        self.render(push=False)

    def atom_double_clicked(self, k):
        """Doppelklick: Label an/aus (beim Nummerieren nicht – dort zählt jeder Klick einzeln)."""
        if self.numbering or self.F is None:
            return
        e = self.entry()
        a = self.F.mol.atoms[k]
        e.setdefault("label_on", {})[a["key"]] = not XRAY.label_shown(a, self.opts(e))
        self.render()

    def view_changed(self, R):
        e = self.entry()
        if e is not None:
            e["view"] = [round(float(v), 6) for v in np.asarray(R).ravel()]
            self.render()

    def pan_changed(self, pan):
        e = self.entry()
        if e is not None:
            e["pan"] = [round(float(pan[0]), 3), round(float(pan[1]), 3)]
            self.render()

    def zoom_changed(self, z):
        e = self.entry()
        if e is not None:
            e["zoom"] = round(float(z), 4)
            self.timer.start()

    def labels_moved(self, layout):
        e = self.entry()
        if e is None or self.F is None or self.numbering:          # beim Nummerieren stehen Nummern auf den Atomen
            return
        lay = self.layout()
        for key, pos in layout.items():
            if key in lay or pos != self.F.auto_pos.get(key):
                lay[key] = pos
        self.main.push_undo()

    def reset_view(self):
        e = self.entry()
        if e is not None:
            e.update(view=None, zoom=1.0, pan=[0.0, 0.0], layout={})
            self.render()

    def reset_layout(self):
        e = self.entry()
        if e is not None:
            e["layout"] = {}
        self.render()

    # -- Nummerieren ----------------------------------------------------------------------
    def set_numbering(self, on):
        self.numbering = bool(on) and self.entry() is not None
        self.picks = []
        if self.btn_num.isChecked() != self.numbering:
            self.btn_num.blockSignals(True)
            self.btn_num.setChecked(self.numbering)
            self.btn_num.blockSignals(False)
        self.btn_num.setText(T("dft_num_cancel" if self.numbering else "dft_num_start"))
        self.update_num_status()
        self.render(push=False)

    def stop_numbering(self):
        if self.numbering or self.picks:
            self.numbering, self.picks = False, []
            self.btn_num.blockSignals(True)
            self.btn_num.setChecked(False)
            self.btn_num.blockSignals(False)
            self.btn_num.setText(T("dft_num_start"))
        self.update_num_status()

    def undo_pick(self):
        if self.picks:
            self.picks.pop()
            self.update_num_status()
            self.render(push=False)

    def update_num_status(self):
        if not hasattr(self, "lbl_num"):
            return
        e = self.entry()
        g = self.geometry(e) if e else None
        n = len(g[1]) if g else 0
        self.btn_undo_pick.setEnabled(self.numbering and bool(self.picks))
        self.btn_apply.setEnabled(self.numbering and bool(self.picks))
        if not self.numbering:
            self.lbl_num.setText(T("dft_num_hint"))
            self.lbl_num.setStyleSheet(HINT_CSS)
            return
        b = self.base()
        txt = T("dft_num_next", next=len(self.picks) + b, k=len(self.picks), n=n)
        if self.picks and len(self.picks) < n:
            txt += "\n" + T("dft_num_rest_h" if self.st.get("h_follow") else "dft_num_rest",
                            a=len(self.picks) + b, b=n - 1 + b)
        self.lbl_num.setText(txt)
        self.lbl_num.setStyleSheet("")

    def apply_numbering(self):
        e = self.entry()
        g = self.geometry(e) if e else None
        if g is None or not self.picks:
            return
        _, els, _, bonds = g
        nbrs = None
        if self.st.get("h_follow"):
            nbrs = {k: [] for k in range(len(els))}
            for a, b in bonds:
                nbrs[a].append(b)
                nbrs[b].append(a)
        new = renumber(self.order(e, len(els)), self.picks, els, nbrs)
        e["order"] = None if new == list(range(len(els))) else new
        self.stop_numbering()
        self.main.statusBar().showMessage(T("dft_num_done"), 6000)
        self.render()

    def reset_order(self):
        e = self.entry()
        if e is not None and (e.get("order") or e.get("ref_labels")):
            e.update(order=None, ref_labels={}, ref_name="")
            self.lbl_ref.setText("")
            self.stop_numbering()
            self.render()

    # -- Vergleichsmodus: Nummerierung einer Vorlage übernehmen -------------------------------
    def fill_refs(self):
        """Vorlagen: die anderen Geometrien dieses Tabs und die Strukturen des X-Ray-Tabs (CIF)."""
        cur = self.entry()
        keep = self.cmb_ref.currentData()
        self.cmb_ref.blockSignals(True)
        self.cmb_ref.clear()
        for x in self.entries():
            if cur is not None and x["uid"] != cur["uid"]:
                self.cmb_ref.addItem(f"DFT: {x.get('name') or Path(x['file']).stem}", f"dft:{x['uid']}")
        xt = getattr(self.main, "xray_tab", None)
        for x in (xt.entries() if xt is not None else []):
            self.cmb_ref.addItem(f"X-Ray: {x.get('name') or x['block']}", f"xray:{x['uid']}")
        if keep is not None and self.cmb_ref.findData(keep) >= 0:
            self.cmb_ref.setCurrentIndex(self.cmb_ref.findData(keep))
        self.cmb_ref.blockSignals(False)
        self.btn_ref.setEnabled(cur is not None and self.cmb_ref.count() > 0)

    def reference(self, data):
        """-> (dict(els, xyz, bonds, order, labels), Name) einer Vorlage. CIF: Hauptmolekül (Fragment 0), Labels wie
        in der CIF (erzeugte Atome mit Symmetriezusatz)."""
        kind, uid = data.split(":", 1)                   # „dft:<uid>“ bzw. „xray:<uid>“
        if kind == "dft":
            x = next(x for x in self.entries() if x["uid"] == uid)
            g = self.geometry(x)
            if g is None:
                raise ValueError(T("dft_ref_missing"))
            return dict(els=g[1], xyz=g[2], bonds=g[3], order=self.order(x, len(g[1])), labels=None), \
                x.get("name") or Path(x["file"]).stem
        xt = self.main.xray_tab
        x = next(x for x in xt.entries() if x["uid"] == uid)
        mol = xt.molecule(x)
        if mol is None:
            raise ValueError(T("dft_ref_missing"))
        idx = [k for k, a in enumerate(mol.atoms) if a.get("frag") == 0]
        pos = {k: i for i, k in enumerate(idx)}
        return dict(els=[mol.atoms[k]["el"] for k in idx], xyz=np.array([mol.atoms[k]["xyz"] for k in idx]),
                    bonds=[(pos[a], pos[b]) for a, b in mol.bonds if a in pos and b in pos], order=None,
                    labels={i: XRAY.atom_name(mol.atoms[k]) for i, k in enumerate(idx)}), x.get("name") or x["block"]

    def apply_reference(self):
        """Nummerierung der gewählten Vorlage auf die aktuelle Geometrie übertragen (Undo möglich)."""
        e = self.entry()
        g = self.geometry(e) if e else None
        data = self.cmb_ref.currentData()
        if g is None or data is None:
            return
        try:
            ref, name = self.reference(data)
            r = match_reference(ref, dict(els=g[1], xyz=g[2], bonds=g[3], order=self.order(e, len(g[1]))))
        except (ValueError, StopIteration) as ex:
            self.lbl_ref.setText(T("dft_ref_fail", err=str(ex)))
            self.lbl_ref.setStyleSheet(WARN_CSS)
            return
        self.stop_numbering()
        e["order"] = None if r["order"] == list(range(len(g[1]))) else r["order"]
        e["ref_labels"] = {str(k): v for k, v in r["labels"].items()}
        e["ref_name"] = name
        bits = [T("dft_ref_done", ref=name, n=r["n_heavy"], nr=r["n_ref_heavy"], nt=r["n_tgt_heavy"], nh=r["n_h"],
                  rmsd=f"{r['rmsd']:.2f}")]
        warn = r["partial"] or bool(r["ambiguous"]) or r["truncated"]
        if r["rmsd_alt"] is not None:
            bits.append(T("dft_ref_sym", alt=f"{r['rmsd_alt']:.2f}"))
        if r["ambiguous"]:
            bits.append(T("dft_ref_amb", atoms=", ".join(r["ambiguous"][:12]) + (" …" if len(r["ambiguous"]) > 12 else "")))
        if r["partial"]:
            bits.append(T("dft_ref_partial"))
        if r["truncated"]:
            bits.append(T("dft_ref_truncated", n=MATCH_MAX))
        rest = len(g[1]) - r["n_heavy"] - r["n_h"]
        if rest:
            bits.append(T("dft_ref_rest", n=rest))
        if r["labels"]:
            self.st["label_style"] = "ref"                    # CIF-Vorlage: Labels der Kristallstruktur zeigen
            self.cmb_lstyle.blockSignals(True)
            self.cmb_lstyle.setCurrentIndex(self.cmb_lstyle.findData("ref"))
            self.cmb_lstyle.blockSignals(False)
        self.lbl_ref.setText("\n".join(bits))
        self.lbl_ref.setStyleSheet(WARN_CSS if warn else HINT_CSS)
        self.render()

    # -- Speichern / Export ---------------------------------------------------------------
    def default_xyz_path(self, e):
        name = core.safe_name(e.get("name") or Path(e["file"]).stem)
        if self.main.project_dir:
            return PRJ.export_dir(self.main.project_dir, self.STATE_KEY) / f"{name}.xyz"
        return Path(e["file"]).with_name(f"{name}_renumbered.xyz")

    def save_xyz(self, path=None):
        """Aktuelle Reihenfolge als xyz; die Datei im Projekt (data/) wird nie überschrieben."""
        e = self.entry()
        g = self.geometry(e) if e else None
        if g is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, T("dft_save_xyz"), str(self.default_xyz_path(e)),
                                                  "xyz (*.xyz)")
            if not path:
                return None
        path = Path(path)
        if path.suffix.lower() != ".xyz":
            path = path.with_suffix(".xyz")
        if path.resolve() == Path(e["file"]).resolve():
            self.main.error(T("dft_no_overwrite"))
            return None
        write_xyz(path, g[0], self.order(e, len(g[1])))
        self.main.log_signal.emit(T("saved", p=str(path)))
        self.main.statusBar().showMessage(T("saved", p=str(path)), 6000)
        return path

    def export_to(self, base: Path):
        """Je Geometrie eine Abbildung (eigene Ansicht) und die xyz-Datei in der aktuellen Reihenfolge."""
        base = Path(base).resolve()
        base.parent.mkdir(parents=True, exist_ok=True)
        files = []
        es = [e for e in self.entries() if self.geometry(e) is not None]
        if not es:
            raise RuntimeError(T("tab_empty"))
        for e in es:
            name = base.name + ("_" + core.safe_name(e.get("name") or Path(e["file"]).stem) if len(es) > 1 else "")
            stem = base.with_name(name)
            fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = self.build(fig, e, interactive=False)
            if F is not None:
                F.cfg["output"] = str(stem.with_suffix("." + F.cfg["_main_fmt"]))
                files += F.export()
            g = self.geometry(e)
            files.append(write_xyz(stem.with_suffix(".xyz"), g[0], self.order(e, len(g[1]))))
        if any(self.calc_of(e) is not None for e in es):
            files.append(self.save_docx(base.with_name(base.name + "_SI.docx")))
            si = [si_plain(self.si_of(e)) for e in es if self.calc_of(e) is not None]
            txt = base.with_name(base.name + "_SI.txt")
            txt.write_text("\n\n\n".join(si) + "\n", encoding="utf-8")
            files.append(txt)
        return files

    def docx_blocks(self, img_dir):
        """Blöcke für SI.write_docx: je Rechnung Name, Abbildung (eng beschnitten), Text, Konvergenz, Koordinaten."""
        blocks = []
        if method_mode(self.st.get("si_method")) == "top":
            items = [(e.get("name") or Path(e["file"]).stem, self.calc_of(e)) for e in self.entries()
                     if self.calc_of(e) is not None]
            det = computational_details(items)
            if det:
                blocks.append(("heading", "Computational details"))
                blocks += [("text", h) for _, h in det]
        for e in self.entries():
            p = self.si_of(e) if self.geometry(e) is not None else None
            if p is None:
                continue
            if blocks:
                blocks.append(("gap",))
            blocks.append(("heading", p["name"]))
            fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
            FigureCanvasAgg(fig)
            F = self.build(fig, e, interactive=False)
            if F is not None:
                svg = Path(img_dir) / f"{core.safe_name(p['name'])}_dft.svg"
                blocks.append(("image",) + XRAY.save_tight(F, svg))
            blocks.append(("fields", p["fields"][1]))
            k = p["conv_at"]
            blocks += [("text", h) for _, h in p["extra"][:k]]
            if p["conv"]:
                blocks.append(("coords",) + tuple(p["conv"]))
            blocks += [("text", h) for _, h in p["extra"][k:]]
            blocks.append(("mono", p["coords"]))
            if p["energies"]:
                blocks.append(("energies", p["energies"][0], [p["energies"][2]]))
        return blocks

    def save_docx(self, path=None):
        """SI-Abschnitt aller Rechnungen als Word-Datei (Stil wie die SI der Gruppe)."""
        import uvvis_si as SI
        if path is None:
            if not self.main.ensure_project():
                return None
            path, _ = QFileDialog.getSaveFileName(
                self, T("dft_si_word"), str(PRJ.export_dir(self.main.project_dir, self.STATE_KEY) / "DFT_SI.docx"),
                "Word (*.docx)")
            if not path:
                return None
        path = Path(path)
        img_dir = path.parent / "si_images"
        img_dir.mkdir(parents=True, exist_ok=True)
        try:
            out = SI.write_docx(path, self.docx_blocks(img_dir), columns=2)     # zweispaltig wie die SI der Gruppe
        except PermissionError:
            self.main.error(T("report_locked", p=path))
            return None
        self.main.log_signal.emit(T("saved", p=str(out)))
        return out
