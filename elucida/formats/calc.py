"""
elucida/formats/calc.py - Geometrien und Rechnungen: xyz (auch Trajektorien, Ordnungszahlen), ORCA-6- und Gaussian-Ausgaben (Werte als Text wie in der Ausgabe), Kodierung (UTF-16 aus PowerShell).
"""
from __future__ import annotations

import re
from pathlib import Path
import numpy as np
from elucida.app.i18n import T
from elucida.formats.elements import element_of


ELEMENTS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
            "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
            "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn").split()


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
                els.append(element_of(s, s))
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
