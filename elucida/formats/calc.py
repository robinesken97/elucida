"""
elucida/formats/calc.py - Geometrien und Rechnungen: xyz (auch Trajektorien, Ordnungszahlen), ORCA-6- und Gaussian-Ausgaben (Werte als Text wie in der Ausgabe), Kodierung (UTF-16 aus PowerShell).
"""
from __future__ import annotations

import re
from pathlib import Path
import numpy as np
from elucida.app.i18n import T
from elucida.formats.elements import ELEMENTS, element_of




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
            elif s.lower() in ("bq", "gh", "x", "xx", "du") or s.lower().startswith("bq-"):
                els.append("X")                              # Geisteratom (NICS): nie als Bor lesen („Bq“ -> „B“)
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
               ("G_E", "G-E(el)"), ("mTS", "Total entropy correction"))


def _calc():
    return dict(program="", version="", keywords=[], charge=None, mult=None, point_group="", solvation=None,
                opt_requested=False,
                opt_converged=None, conv=[], freq_requested=False, freqs=None, thermo={}, energy=None,
                normal=False, geometry=None, nuc_rep=None)


def is_orca(text):
    return "O   R   C   A" in text[:20000] or "Program Version 6" in text[:20000]


def is_gaussian(text):
    return "Entering Gaussian System" in text[:20000] or "Gaussian, Inc." in text[:20000]


def _num_rows(rows, k):
    """Koordinatenzeilen (Text, Token): drei Zahlen ab Token k (abgeschnittene Zeile -> False)."""
    try:
        return all(len(tok) >= k + 3 and [float(v) for v in tok[k:k + 3]] for _, tok in rows)
    except ValueError:
        return False


def _last_job(text, starts, parse, chained=lambda seg: False):
    """Mehrere Jobs in einer Ausgabe (ORCA $new_job/Compound, Gaussian Link1): alle Angaben aus DEMSELBEN Job, dem
    letzten vollständigen mit Geometrie (sonst dem letzten); `chained(seg)` hängt einen Folgeschritt desselben Jobs
    (Gaussian „opt freq“) an den vorigen. normal = Ende der ganzen Datei. starts: Zeilenindizes der Jobanfänge."""
    L = text.splitlines()
    bounds = [0] + [s for s in starts[1:]] + [len(L)]
    segs = []
    for a, b in zip(bounds, bounds[1:]):
        if segs and chained(L[a:b]):
            segs[-1] = (segs[-1][0], b)
        else:
            segs.append((a, b))
    jobs = [parse("\n".join(L[a:b])) for a, b in segs]
    done = [k for k, c in enumerate(jobs) if (k < len(jobs) - 1 or c["normal"]) and c["geometry"]]
    k = done[-1] if done else len(jobs) - 1
    c = jobs[k]
    c["normal"] = jobs[-1]["normal"]
    return c, "\n".join(L[:segs[k][1]])


def parse_orca(text) -> dict:
    """ORCA 6: Eingabezeile(n) „!“, Ladung/Multiplizität, CPCM/SMD, letzte Konvergenztabelle der Optimierung,
    letzte Koordinaten, Frequenzen, Thermochemie. Abgebrochene Dateien liefern, was vorhanden ist (normal = False);
    Koordinatenblöcke nur vollständig. Mehrere Jobs: alles aus dem letzten vollständigen (`_last_job`)."""
    L = text.splitlines()
    starts = [i for i, ln in enumerate(L) if ln.strip() == "INPUT FILE"]
    if len(starts) < 2:
        return _orca_job(text)
    c, upto = _last_job(text, starts, _orca_job)
    if not c["version"]:                                 # Kopf steht vor dem ersten Job
        vs = re.findall(r"Program Version\s+(\S+)", upto)
        c["version"] = vs[-1] if vs else ""
    return c


def _orca_job(text) -> dict:
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
                c["keywords"].append(m.group(1).split("#")[0].strip())          # „#“ = Kommentar
        elif s.startswith("Total Charge") and "...." in s and c["charge"] is None:
            c["charge"] = int(s.split()[-1])
        elif s.startswith("Multiplicity") and "...." in s and c["mult"] is None:
            c["mult"] = int(s.split()[-1])
        elif s.startswith("FINAL SINGLE POINT ENERGY"):
            m = re.search(_E, s)                 # danach evtl. „(Wavefunction not fully converged!)“
            c["energy"] = m.group(1) if m else c["energy"]
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
            # nur vollständige Blöcke (keine angeschnittene Zeile, Zahlen, Atomzahl wie „Number of atoms“ bzw. der vorige
            # Block): abgeschnittene Datei -> voriger Block
            if rows and (j >= n or not L[j].strip()) and _num_rows(rows, 1) and \
                    len(rows) == c.get("_natoms", len(rows)):
                c["geometry"], c["_natoms"] = rows, len(rows)
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
        elif s.startswith("Nuclear Repulsion"):          # „Nuclear Repulsion  :  819.92… Eh“ bzw. „… ENuc …. 819.92… Eh“
            m = re.search(_E + r"\s*Eh", s)
            if m:
                c["nuc_rep"] = m.group(1)
        elif "ORCA TERMINATED NORMALLY" in ln:
            c["normal"] = True
        elif re.fullmatch(r"Number of atoms\s+\.{3,}\s+\d+", s):
            c.setdefault("_natoms", int(s.split()[-1]))
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
    from elucida.formats.multireference import parse_orca_mr
    c["multireference"] = parse_orca_mr(text)
    c.pop("_natoms", None)
    return c


def _g_route(L):
    """Route eines Gaussian-Jobs (erste Zeile „#…“ nach einer Strichlinie) oder None."""
    for i in range(1, len(L)):
        if L[i].strip().startswith("#") and L[i - 1].strip().startswith("---"):
            j, parts = i, []
            while j < len(L) and not L[j].strip().startswith("---"):
                parts.append(L[j].strip())
                j += 1
            return "".join(parts)
    return None


def parse_gaussian(text) -> dict:
    """Gaussian (geprüft mit einer echten Opt+Freq/SMD-Ausgabe): Route, Ladung/Multiplizität, letzte Standard-/Input-
    Orientierung (nur vollständig), letzte Konvergenztabelle, Frequenzen, Thermochemie, SCF-Energie, SCRF aus der Route.
    Mehrere Jobs (Link1): von Gaussian erzeugte Folgeschritte („opt freq“: Route mit GenChk, Werte aus dem Checkpoint)
    gehören zum Job davor; ein eigener Job (andere Methode/Ladung möglich) ersetzt alles (`_last_job`)."""
    L = text.splitlines()
    starts = [i for i, ln in enumerate(L) if ln.strip().startswith(("Initial command:", "Link1:"))]
    if not starts or not L[starts[0]].strip().startswith("Initial command:"):
        starts = [0] + starts                            # Kopf ohne „Initial command“: Job 1 beginnt am Anfang
    if len(starts) < 2:
        return _gaussian_job(text)
    c, upto = _last_job(text, starts, _gaussian_job,
                        lambda seg: (lambda r: r is None or "genchk" in r.lower())(_g_route(seg)))
    if not c["version"]:                                 # eigener Job nach Link1: Kopf steht im ersten
        m = (re.search(r"Gaussian (\d\d), Revision ([A-Z]\.\d+)", upto)
             or re.search(r"Gaussian (\d\d):\s+\S*Rev([A-Z]\.\d+)", upto) or re.search(r"Gaussian (\d\d):", upto))
        c["version"] = m.group(1) + (f" Rev. {m.group(2)}" if m.lastindex and m.lastindex > 1 else "") if m else ""
    return c


def _gaussian_job(text) -> dict:
    c = _calc()
    c["program"] = "Gaussian"
    L = text.splitlines()
    n = len(L)
    i = 0
    while i < n:
        ln = L[i]
        s = ln.strip()
        if not c["version"]:
            m = (re.search(r"Gaussian (\d\d), Revision ([A-Z]\.\d+)", ln)
                 or re.search(r"Gaussian (\d\d):\s+\S*Rev([A-Z]\.\d+)", ln)    # „Gaussian 16:  ES64L-G16RevC.01“
                 or re.search(r"Gaussian (\d\d):", ln))
            if m:
                c["version"] = m.group(1) + (f" Rev. {m.group(2)}" if m.lastindex and m.lastindex > 1 else "")
        if s.startswith("#") and not c["keywords"] and i > 0 and L[i - 1].strip().startswith("---"):
            route, j = [], i
            while j < n and not L[j].strip().startswith("---"):
                route.append(L[j][1:] if L[j].startswith(" ") else L[j])  # Umbruch auch mitten im Wort
                j += 1
            c["keywords"] = ["".join(route).strip()]
            i = j
            continue
        if s.startswith("Charge =") and "Multiplicity =" in s and c["charge"] is None:
            m = re.match(r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)", s)
            if m:
                c["charge"], c["mult"] = int(m.group(1)), int(m.group(2))
        elif s in ("Standard orientation:", "Input orientation:"):
            rows, j, whole = [], i + 5, True
            while j < n and not L[j].strip().startswith("---"):
                tok = L[j].split()
                if len(tok) == 6 and tok[1].isdigit():
                    z = int(tok[1])
                    el = ELEMENTS[z - 1] if 1 <= z <= len(ELEMENTS) else "X"
                    rows.append((f"  {el:<2s} {tok[3]:>14s} {tok[4]:>14s} {tok[5]:>14s}", [el] + tok[3:6]))
                else:
                    whole = False                        # abgeschnittene Zeile
                j += 1
            # nur vollständige Blöcke (Strichlinie am Ende, gleiche Atomzahl): abgeschnittene Datei -> voriger Block
            whole = whole and j < n and _num_rows(rows, 1) and len(rows) == c.get("_natoms", len(rows))
            if rows and whole:
                c["_natoms"] = len(rows)
            if rows and whole and (s == "Standard orientation:" or c.get("_orient") != "std"):
                c["geometry"] = rows
                c["_orient"] = "std" if s == "Standard orientation:" else "inp"
            i = j
            continue
        elif s.startswith("SCF Done:"):
            m = re.search(r"=\s*" + _E, s)
            if m:
                c["energy"] = m.group(1)
        elif "EUMP2" in s or "E2(" in s or s.startswith("CCSD(T)="):
            # MP2, Doppelhybride, CCSD(T): „SCF Done“ ist nur der SCF-Anteil; die Gesamtenergie steht danach als
            # „EUMP2 = -0.76…D+02“, „E2(B2PLYP) = … E(B2PLYP) = -0.76…D+02“ bzw. „CCSD(T)= -0.76…D+02“ (Literaturprüfung
            # 2026-11: sonst fehlt Einzelpunkten die Korrelationsenergie). Die Ziffern bleiben, nur der Exponent entfällt.
            m = (re.search(r"EUMP2\s*=\s*(-?\d*\.\d+D[+-]\d+)", s)
                 or re.search(r"E2\([^)]*\)\s*=\s*\S+\s+E\([^)]*\)\s*=\s*(-?\d*\.\d+D[+-]\d+)", s)
                 or re.search(r"^CCSD\(T\)=\s*(-?\d*\.\d+D[+-]\d+)", s))
            if m:
                from decimal import Decimal
                c["energy"] = format(Decimal(m.group(1).replace("D", "E")), "f")
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
        elif s.startswith("Frequencies --") and not s.startswith("Frequencies ---"):    # „---“: hpmodes-Kopie
            if not c.get("_fjob"):               # erste Frequenzzeile dieses Jobs: Werte eines früheren Jobs verwerfen
                c["freqs"], c["thermo"], c["_fjob"] = [], {}, True
                c.pop("_e_th", None)
            c["freqs"] += s.split("--")[1].split()
        elif s.startswith("Temperature") and "Kelvin" in s:
            m = re.match(r"Temperature\s+(\S+)\s+Kelvin\.\s+Pressure\s+(\S+)\s+Atm", s)
            if m:
                c["thermo"].update(T=m.group(1), P=m.group(2))
        elif s.startswith("Zero-point correction="):
            c["thermo"]["ZPE"] = s.split("=")[1].split()[0]
        elif s.startswith("nuclear repulsion energy"):   # „nuclear repulsion energy  819.92… Hartrees.“
            m = re.search(_E + r"\s+Hartrees", s)
            if m:
                c["nuc_rep"] = m.group(1)
        elif s.startswith("Thermal correction to Enthalpy="):
            c["thermo"]["H_corr"] = s.split("=")[1].split()[0]
        elif s.startswith("Sum of electronic and thermal Enthalpies="):
            c["thermo"]["H"] = s.split("=")[1].split()[0]
        elif s.startswith("Sum of electronic and thermal Free Energies="):
            c["thermo"]["G"] = s.split("=")[1].split()[0]
            c["_e_th"] = c["energy"]             # E(el) desselben Jobs (spätere Single Points: andere Methode)
            c["_n_th"] = c["nuc_rep"]            # Kernabstoßung derselben Geometrie
        elif "Normal termination of Gaussian" in s:
            c["normal"] = True
        elif s.startswith(("Initial command:", "Link1:")) or "Error termination" in s:
            c["normal"] = False                  # neuer Job (opt freq = zwei Jobs) bzw. Abbruch: gilt erst am Ende
            if not s.startswith("Error"):        # neuer Job: eigene Orientierung/Frequenzen
                c.pop("_orient", None)
                c["_fjob"] = False
        i += 1
    route = " ".join(c["keywords"]).lower()
    c["opt_requested"] = c["opt_requested"] or bool(re.search(r"\bopt\b", route))
    c["freq_requested"] = bool(re.search(r"\bfreq\b", route)) or c["freqs"] is not None
    m = re.search(r"scrf\s*=?\s*\(?([^)\s]*)", route)
    if m:
        opts = m.group(1)
        sm = re.search(r"solvent\s*=\s*([\w,-]+)", opts)
        c["solvation"] = dict(model="SMD" if "smd" in opts else "PCM", solvent=sm.group(1) if sm else "", eps="",
                              e_diel=None, e_cds=None)
    if c["energy"] is not None:
        c["thermo"].setdefault("E_el", c.get("_e_th") or c["energy"])
    c["nuc_rep"] = c.get("_n_th") or c["nuc_rep"]
    for k in ("_orient", "_fjob", "_e_th", "_n_th", "_natoms"):
        c.pop(k, None)
    return c


_HFC_ROW = re.compile(r"^\s*(\d+)\s+([A-Za-z]+)\((\d+)\)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")
_DIP_ROW = re.compile(r"^\s*(?:(\d+)\s+[A-Za-z]+\(\d+\)\s+)?B(aa|bb|cc)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+"
                      r"(-?\d+\.\d+)")


def parse_gaussian_epr(text) -> dict:
    """Gaussian 16, offenschalig: Mulliken-Spinpopulationen je Atom, isotrope Fermi-Kontakt-Kopplungen und anisotrope
    Dipolkopplungen (Hauptwerte), je der letzte Block der Ausgabe. -> dict(calc (parse_gaussian), els, spin [float],
    fermi {Atomindex: (Isotop "14N", MHz, Gauss)}, dipole {Atomindex: [(MHz, Gauss) für Baa, Bbb, Bcc]}).
    Andere Programme und Ausgaben ohne Spinpopulationen werden abgelehnt (nicht raten). Geprüft mit G16 (Prop=EPR)."""
    if not is_gaussian(text):
        raise ValueError(T("epr_calc_not_gaussian"))
    c = parse_gaussian(text)
    L = text.splitlines()
    els, spin, fermi, dipole, blocks = [], [], {}, {}, set()
    i, n = 0, len(L)
    while i < n:
        s = L[i].strip()
        if s == "Mulliken charges and spin densities:":
            els, spin, j = [], [], i + 2
            while j < n:
                t = L[j].split()
                if len(t) != 4 or not t[0].isdigit():
                    break
                els.append(element_of(t[1], t[1]))
                try:
                    spin.append(float(t[3]))
                except ValueError:                             # Überlauf „****“
                    raise ValueError(T("fixr_epr_gauss_overflow", line=j + 1)) from None
                j += 1
            i = j
            continue
        if s == "Isotropic Fermi Contact Couplings":
            fermi, j = {}, i + 2
            blocks.add("fermi")
            while j < n:
                m = _HFC_ROW.match(L[j])
                if not m:
                    break
                fermi[int(m.group(1)) - 1] = (m.group(3) + m.group(2), float(m.group(5)), float(m.group(6)))
                j += 1
            i = j
            continue
        if s == "Anisotropic Spin Dipole Couplings in Principal Axis System":
            dipole, j, rows, at = {}, i + 1, [], None
            blocks.add("dipole")
            while j < n:
                m = _DIP_ROW.match(L[j])
                if m:
                    at = int(m.group(1)) - 1 if m.group(1) else at
                    rows.append((float(m.group(4)), float(m.group(5))))
                    if m.group(2) == "cc" and at is not None and len(rows) == 3:
                        dipole[at] = rows
                    if m.group(2) == "cc":
                        rows, at = [], None
                elif L[j].strip() and not set(L[j].strip()) <= {"-"} and "Atom" not in L[j]:
                    break
                j += 1
            i = j
            continue
        i += 1
    if not spin:
        raise ValueError(T("epr_calc_no_spin"))
    if not c["geometry"] or len(c["geometry"]) != len(spin):
        raise ValueError(T("dft_no_geometry"))
    for key, got in (("fermi", fermi), ("dipole", dipole)):    # Tabelle endet still beim ersten fremden Muster („****“)
        if key in blocks and len(got) != len(spin):
            raise ValueError(T("fixr_epr_gauss_count", n=len(got), m=len(spin)))
    return dict(calc=c, els=els, spin=spin, fermi=fermi, dipole=dipole)


# ORCA-Hyperfeinblock, geprüft an echten öffentlichen Ausgaben: 4.0/4.1/4.2/5.0 „Nucleus  10H : A:ISTP=    1 …“ +
# „Raw HFC matrix“, 6.0 „Nucleus   0H : A  : Isotope=    1 …“ + „Total HFC matrix“. 6.1 (Nutzerentscheid 2026-11-13)
# mit dem 6.0-Layout und strenger Prüfung, aber ohne echte Ausgabe (`ORCA_EPR_UNCHECKED`, Hinweis). Andere ablehnen.
ORCA_EPR_LAYOUT = {"4.0": "istp", "4.1": "istp", "4.2": "istp", "5.0": "istp", "6.0": "isotope", "6.1": "isotope"}
ORCA_EPR_UNCHECKED = {"6.1"}
_ORCA_HEAD = {"istp": "Raw HFC matrix (all values in MHz):", "isotope": "Total HFC matrix (all values in MHz):"}
_ORCA_NUC = {"istp": re.compile(r"^\s*Nucleus\s+(\d+)\s*([A-Z][a-z]?)\s*:\s*A:ISTP=\s*(\d+)\s"),
             "isotope": re.compile(r"^\s*Nucleus\s+(\d+)\s*([A-Z][a-z]?)\s*:\s*A\s+:\s*Isotope=\s*(\d+)\s")}
_ORCA_A = re.compile(r"^\s*A\((FC|SD|ORB)\)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*(?:$|A\(PC\))")
_ORCA_POP = re.compile(r"^\s*(\d+)\s+([A-Z][a-z]?)\s*:\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")
MHZ_PER_G = 2.00231930436 * 1.3996245                  # g_e · µ_B/h (MHz/G), wie die Gauss-Spalte von Gaussian


def parse_orca_epr(text) -> dict:
    """ORCA (4.0–4.2, 5.0, 6.0, 6.1 ungeprüft; offenschalig): Spinpopulationen (letzter Block „MULLIKEN ATOMIC CHARGES AND SPIN
    POPULATIONS“, Löwdin als `spin_loewdin`) und je Kern des letzten Hyperfeinblocks A(FC) (Fermi-Kontakt, MHz wie
    gedruckt, Gauss mit g_e) sowie A(SD) als Dipol-Hauptwerte, nur ohne A(ORB) (sonst Diagonale im Achsensystem
    des Gesamttensors). Gleiche Struktur wie `parse_gaussian_epr`; ohne `%eprnmr` bleibt fermi leer."""
    if not is_orca(text):
        raise ValueError(T("epr_calc_orca_not_supported"))
    m = re.search(r"Program Version\s+(\d+)\.(\d+)", text)
    ver = f"{m.group(1)}.{m.group(2)}" if m else "?"
    if ver not in ORCA_EPR_LAYOUT:
        raise ValueError(T("epr_calc_orca_version", v=ver))
    nuc_re, head = _ORCA_NUC[ORCA_EPR_LAYOUT[ver]], _ORCA_HEAD[ORCA_EPR_LAYOUT[ver]]
    c = parse_orca(text)
    L = text.splitlines()
    pops, fermi, dipole, inputs, hfc_input = {}, {}, {}, [], None
    i, n, in_hfc, cur, hfc_seen = 0, len(L), False, None, False

    def close(cur):
        if cur and "FC" in cur["A"] and not cur["head"]:          # Tabellenkopf fehlt/anders: Layout unbekannt
            raise ValueError(T("epr_calc_orca_layout", v=ver, line=cur["line"]))
        if cur and "FC" in cur["A"]:
            mhz = cur["A"]["FC"][0]
            fermi[cur["k"]] = (cur["iso"], mhz, mhz / MHZ_PER_G)
            if "SD" in cur["A"] and "ORB" not in cur["A"]:
                dipole[cur["k"]] = [(v, v / MHZ_PER_G) for v in sorted(cur["A"]["SD"])]

    while i < n:
        s = L[i].strip()
        for kind in ("MULLIKEN", "LOEWDIN"):
            if s == f"{kind} ATOMIC CHARGES AND SPIN POPULATIONS":
                rows, j = [], i + 2
                while j < n and (mm := _ORCA_POP.match(L[j])):
                    rows.append((element_of(mm.group(2), mm.group(2)), float(mm.group(4))))
                    j += 1
                if rows:                                       # Block ohne Spinspalte überschreibt keinen früheren
                    pops[kind] = rows
                i = j - 1
        if s == "INPUT FILE":
            inputs.append(i)
            close(cur)
            in_hfc, cur = False, None                          # neuer Job: Hyperfeinblock ist zu Ende
        if s.startswith("ELECTRIC AND MAGNETIC HYPERFINE STRUCTURE"):
            close(cur)
            fermi, dipole, in_hfc, cur = {}, {}, True, None     # nur der letzte Block gilt
            hfc_seen = True
            hfc_input = inputs[-1] if inputs else None
        elif in_hfc and s.startswith("Nucleus"):
            close(cur)
            mm = nuc_re.match(L[i])
            if not mm and re.fullmatch(r"Nucleus\s+\d+\s*[A-Z][a-z]?\s*:", s):   # NMR-Abschirmung: Block zu Ende
                in_hfc, cur = False, None
                i += 1
                continue
            if not mm:
                raise ValueError(T("epr_calc_orca_layout", v=ver, line=i + 1))
            cur = dict(k=int(mm.group(1)), iso=mm.group(3) + mm.group(2), A={}, head=False, line=i + 1)
        elif cur is not None and "HFC matrix" in s:
            if s != head:
                raise ValueError(T("epr_calc_orca_layout", v=ver, line=i + 1))
            cur["head"] = True
        elif cur is not None and (mm := _ORCA_A.match(L[i])):
            cur["A"].setdefault(mm.group(1), [float(mm.group(g)) for g in (2, 3, 4)])
        i += 1
    close(cur)
    if not c["normal"] and (hfc_seen or re.search(r"(?im)^\|\s*\d+>.*%eprnmr", text)):   # abgeschnitten: nie wie
        raise ValueError(T("r2l_epr_hfc_incomplete"))                               # ohne %eprnmr zeigen
    if "MULLIKEN" not in pops:
        raise ValueError(T("epr_calc_no_spin"))
    els = [e for e, _ in pops["MULLIKEN"]]
    spin = [v for _, v in pops["MULLIKEN"]]
    if not c["geometry"] or len(c["geometry"]) != len(spin):
        raise ValueError(T("dft_no_geometry"))
    if len(inputs) > 1 and hfc_input is not None:             # mehrere Jobs: Niveau des Jobs mit dem Hyperfeinblock
        kw, j = [], hfc_input + 1
        while j < n and "END OF INPUT" not in L[j]:
            mm = re.match(r"\|\s*\d+>\s?(.*)$", L[j])
            if mm and mm.group(1).lstrip().startswith("!"):
                kw.append(mm.group(1).split("#")[0].strip())
            j += 1
        c["keywords"] = kw or c["keywords"]
    lw = pops.get("LOEWDIN")
    if any(k >= len(els) or nucleus != els[k] for k, nucleus in
           ((k, re.sub(r"^\d+", "", f[0])) for k, f in fermi.items())):
        raise ValueError(T("epr_calc_orca_layout", v=ver, line="?"))
    return dict(calc=c, els=els, spin=spin, fermi=fermi, dipole=dipole, unchecked=ver in ORCA_EPR_UNCHECKED,
                spin_loewdin=[v for _, v in lw] if lw and len(lw) == len(spin) else None)


def parse_epr(text) -> dict:
    """Weiche für den EPR-Tab: Gaussian 16 oder ORCA, sonst ablehnen."""
    if is_gaussian(text):
        return parse_gaussian_epr(text)
    if is_orca(text):
        return parse_orca_epr(text)
    raise ValueError(T("epr_calc_orca_not_supported"))


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


def _orca_ir(text):
    """ORCA 5/6: letzter Block „IR SPECTRUM“ -> {Modennummer: Intensität [km/mol]}. Nur das Layout mit der Spalte
    „km/mol“ (Mode freq eps Int T**2 …); ältere Layouts ohne km/mol (ORCA 4: nur T**2) werden abgelehnt (None)."""
    i = text.rfind("\nIR SPECTRUM")
    if i < 0:
        return None
    lines = text[i:].splitlines()[1:40]
    head = "\n".join(lines[:8])
    if "km/mol" not in head or not re.search(r"Mode\s+freq\s+eps\s+Int", head):
        return None
    out, started, shape = {}, False, set()
    for ln in text[i:].splitlines()[1:]:
        m = re.match(r"^\s*(\d+):\s+" + _E + r"\s+" + _E + r"\s+" + _E, ln)
        if m:
            out[int(m.group(1))] = float(m.group(4))
            started = True
            shape.add(ln.rstrip()[-1:])                   # Zeilenende wie die übrigen (Klammer)
        elif started and ln.strip():
            if re.match(r"^\s*\d+:", ln) or len(shape) > 1:     # abgeschnittene Zeile
                raise ValueError(T("r2l_ir_incomplete"))
            return out
    if started:                                          # Tabelle reicht bis ans Dateiende: abgeschnitten
        raise ValueError(T("r2l_ir_incomplete"))
    return out


def _gaussian_ir(text):
    """Gaussian: Paare „Frequencies --“ / „IR Inten    --“ des letzten Frequenzjobs -> ([ṽ], [I km/mol]) oder None."""
    fr, it, in_job = [], [], False
    for k, ln in enumerate(text.splitlines()):
        s = ln.strip()
        try:
            if s.startswith("Frequencies --") and not s.startswith("Frequencies ---"):
                if not in_job:
                    fr, it, in_job = [], [], True
                fr += [float(v) for v in s.split("--")[1].split()]
            elif s.startswith("IR Inten    --"):
                it += [float(v) for v in s.split("--")[1].split()]
        except ValueError:                               # Überlauf „********“
            raise ValueError(T("r2l_ir_overflow", line=k + 1)) from None
        if s.startswith(("Initial command:", "Link1:")):
            in_job = False
    return (fr, it) if fr and len(fr) == len(it) else None


def _orca_raman(text):
    """ORCA 5/6: letzter Block „RAMAN SPECTRUM“ (Mode, freq (cm**-1), Activity, Depolarization; Layout wie im
    ORCA-6.1-Tutorial „Infrared and Raman“) -> {Modennummer: Aktivität [Å⁴/amu]} oder None."""
    i = text.rfind("\nRAMAN SPECTRUM")
    if i < 0:
        return None
    head = "\n".join(text[i:].splitlines()[1:8])
    if not re.search(r"Mode\s+freq \(cm\*\*-1\)\s+Activity\s+Depolarization", head):
        return None
    out, started = {}, False
    for ln in text[i:].splitlines()[1:]:
        m = re.match(r"^\s*(\d+):\s+" + _E + r"\s+" + _E + r"\s+" + _E, ln)
        if m:
            out[int(m.group(1))] = float(m.group(3))
            started = True
        elif started and ln.strip():
            break
    return out or None


def _gaussian_raman(text):
    """Gaussian (freq=raman): Zeilen „Raman Activ --“ des letzten Frequenzjobs (Lage wie cclib sie liest) ->
    ([ṽ], [Aktivität Å⁴/amu]) oder None; Sternchen (Überlauf) -> None."""
    fr, ra, in_job = [], [], False
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("Frequencies --") and not s.startswith("Frequencies ---"):
            if not in_job:
                fr, ra, in_job = [], [], True
            fr += [float(v) for v in s.split("--")[1].split()]
        elif s.startswith("Raman Activ --"):
            try:
                ra += [float(v) for v in s.split("--")[1].split()]
            except ValueError:
                return None
        elif s.startswith(("Initial command:", "Link1:")):
            in_job = False
    return (fr, ra) if fr and len(fr) == len(ra) else None


def raman_modes(text, program, freqs):
    """Raman-Aktivitäten passend zu den Frequenzen -> [(ṽ, S)] nur reelle Moden > 0, oder None (keine Aktivitäten oder
    passen nicht: dann gibt es kein berechnetes Raman-Spektrum, nie raten)."""
    if program == "ORCA":
        r = _orca_raman(text)
        if r is None or any(k >= len(freqs) for k in r):
            return None
        pairs = [(f, r.get(k, 0.0)) for k, f in enumerate(freqs)]
    else:
        g = _gaussian_raman(text)
        if g is None or len(g[0]) != len(freqs) or any(abs(a - b) > 0.01 for a, b in zip(g[0], freqs)):
            return None
        pairs = list(zip(*g))
    return [(f, s) for f, s in pairs if f > 0]


def read_ir_modes(path) -> dict:
    """Schwingungen einer Frequenzrechnung mit IR-Intensitäten (Paket B 1.2.0) -> dict(program, calc (wie read_calc),
    modes=[(ṽ [cm⁻¹], I [km/mol])] nur reelle Moden > 0, n_imag, raman=[(ṽ, Aktivität Å⁴/amu)] oder None).
    Frequenzen wie der DFT-Tab sie liest (`read_calc`), Intensitäten: ORCA „IR SPECTRUM“ (Int in km/mol), Gaussian
    „IR Inten“. Fehlen Intensitäten oder passen sie nicht zu den Frequenzen: ablehnen, nie raten. Raman-Aktivitäten
    (ORCA „RAMAN SPECTRUM“, Gaussian „Raman Activ“) nur, wenn vorhanden und passend."""
    text = read_text(path)
    c = read_calc(path)
    freqs = [float(f) for f in c.get("freqs") or []]
    if not freqs:
        raise ValueError(T("ir_calc_no_freq"))
    if c["program"] == "ORCA":
        ir = _orca_ir(text)
        if ir is None:
            raise ValueError(T("ir_calc_no_int"))
        if any(k >= len(freqs) or abs(freqs[k]) < 1e-6 and v > 0 for k, v in ir.items()):
            raise ValueError(T("ir_calc_mismatch"))
        if any(f > 0 and k not in ir for k, f in enumerate(freqs)):     # fehlende Intensität nie still 0
            raise ValueError(T("r2l_ir_incomplete"))
        pairs = [(f, ir.get(k, 0.0)) for k, f in enumerate(freqs)]
    else:
        g = _gaussian_ir(text)
        if g is None:
            raise ValueError(T("ir_calc_no_int"))
        if len(g[0]) != len(freqs) or any(abs(a - b) > 0.01 for a, b in zip(g[0], freqs)):
            raise ValueError(T("ir_calc_mismatch"))
        pairs = list(zip(*g))
    modes = [(f, i) for f, i in pairs if f > 0]
    return dict(program=c["program"], calc=c, modes=modes, n_imag=sum(1 for f, _ in pairs if f < 0),
                raman=raman_modes(text, c["program"], freqs))


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


def parse_irc(text) -> dict:
    """ORCA-IRC (Ausgabe): Tabelle „IRC PATH SUMMARY“ -> dict(steps, E (Eh, Text), cols {Name: [Werte]}, ts (Index)).
    Spalten nach max/RMS(G) sind Bindungslängen wie „B(C 26,H 23)“; die TS-Zeile trägt „<= TS“."""
    L = text.splitlines()
    k = max((i for i, ln in enumerate(L) if ln.strip() == "IRC PATH SUMMARY"), default=None)
    if k is None:
        raise ValueError(T("dft_irc_none"))
    head = next((i for i in range(k, min(k + 10, len(L))) if L[i].lstrip().startswith("Step")), None)
    if head is None:
        raise ValueError(T("dft_irc_none"))
    names = re.findall(r"[A-Za-z]+\([^)]*\)|\S+", L[head])[4:]       # Step, E(Eh), dE(kcal/mol), max(|G|), RMS(G)
    names = names[1:] if names and names[0].startswith("RMS") else names
    steps, E, cols, ts = [], [], {n: [] for n in names}, None
    for ln in L[head + 1:]:
        tok = ln.split()
        if not tok or not tok[0].isdigit():
            if steps:
                break
            continue
        steps.append(int(tok[0]))
        E.append(tok[1])
        for n, v in zip(names, tok[5:5 + len(names)]):
            cols[n].append(float(v))
        if "<= TS" in ln:
            ts = len(steps) - 1
    if not steps or ts is None:
        raise ValueError(T("dft_irc_none"))
    return dict(steps=steps, E=E, cols=cols, ts=ts)


def parse_nics(text) -> dict:
    """Gaussian-NMR mit Geisteratomen (Bq, z. B. aus py.Aroma) -> dict(route, els, xyz (echte Atome), bq_xyz,
    iso [ppm], tensor [3×3, ppm]). Mehrere Jobs (Link1): der letzte NMR-Block; Lagen aus der letzten Orientierung
    davor (Ordnungszahl 0 = Bq), Tensor in derselben Orientierung, Route des Jobs davor."""
    L = text.splitlines()
    k = max((i for i, ln in enumerate(L) if "Magnetic shielding tensor (ppm)" in ln), default=None)
    if k is None:
        raise ValueError(T("dft_nics_none"))
    route = ""
    for i in range(k):
        if L[i].strip().startswith("#") and i > 0 and L[i - 1].strip().startswith("---"):
            j, parts = i, []
            while j < len(L) and not L[j].strip().startswith("---"):
                parts.append(L[j].strip())
                j += 1
            route = "".join(parts)                       # letzte Route vor dem Block = Job des Blocks
    o = max((i for i in range(k) if L[i].strip() in ("Input orientation:", "Standard orientation:")), default=None)
    if o is None:
        raise ValueError(T("dft_nics_none"))
    atoms = []
    for ln in L[o + 5:]:
        tok = ln.split()
        if len(tok) != 6:
            break
        atoms.append((int(tok[1]), [float(v) for v in tok[3:6]]))
    bq = {}
    for i in range(k, len(L) - 3):
        m = re.match(r"^\s*(\d+)\s+Bq\s+Isotropic =\s*" + _E, L[i])
        if m:
            vals = [float(v) for ln in L[i + 1:i + 4] for v in re.findall(r"=\s*" + _E, ln)]
            if len(vals) == 9:
                bq[int(m.group(1)) - 1] = (float(m.group(2)), np.array(vals).reshape(3, 3))
    idx = [i for i, (z, _) in enumerate(atoms) if z == 0]
    if not idx or any(i not in bq for i in idx):
        raise ValueError(T("dft_nics_none"))
    real = [(z, p) for z, p in atoms if z > 0]
    return dict(route=route, els=[ELEMENTS[z - 1] if 0 < z <= len(ELEMENTS) else "X" for z, _ in real],
                xyz=np.array([p for _, p in real]), bq_xyz=np.array([atoms[i][1] for i in idx]),
                iso=np.array([bq[i][0] for i in idx]), tensor=np.array([bq[i][1] for i in idx]))


HC_EV_NM = 1239.84198                  # h·c in eV·nm
ESD_UNITS = ("nm", "cm-1", "eV")


def esd_unit(path, x) -> tuple[str, str]:
    """x-Einheit einer ESD-Spektrendatei -> (Einheit, Quelle "input"|"range"). Die Datei selbst nennt sie nicht (nur
    „Energy“); %ESD UNIT steht in der .inp bzw. im Eingabe-Echo der .out daneben, sonst über den Wertebereich:
    eV < 30, cm⁻¹ > 3000 (ab 3333 nm), dazwischen nm (ORCA-Beispiel in nm: 72–1153)."""
    p = Path(path)
    base = p.name.split(".spectrum")[0]
    for sib in (p.with_name(base + ".out"), p.with_name(base + ".inp")):
        try:
            m = re.search(r"^\s*(?:\|\s*\d+>\s*)?UNIT\s+(CM-1|NM|EV)\b", read_text(sib), re.I | re.M)
        except OSError:
            continue
        if m:
            return {"CM-1": "cm-1", "NM": "nm", "EV": "eV"}[m.group(1).upper()], "input"
    mx = float(np.nanmax(np.abs(x)))
    return ("eV" if mx < 30 else "cm-1" if mx > 3000 else "nm"), "range"


def read_esd_spectrum(path, unit=None) -> dict:
    """ORCA-ESD-Spektrum (BASENAME.spectrum, auch .spectrum.rootN): Kopf „Energy TotalSpectrum IntensityFC
    IntensityHT“, Tabulatoren -> dict(nm, total, fc, ht (aufsteigend nach nm), unit, unit_src). Intensität ohne
    Einheit (nur normiert vergleichen). unit: Vorgabe (ESD_UNITS), sonst esd_unit."""
    lines = read_text(path).splitlines()
    head = next((i for i, ln in enumerate(lines) if ln.split()[:2] == ["Energy", "TotalSpectrum"]), None)
    if head is None:
        raise ValueError(T("esd_bad", name=Path(path).name))
    rows, ncol = [], min(4, len(lines[head].split()))
    for k, ln in enumerate(lines[head + 1:], head + 2):
        tok = ln.split()
        if not tok:
            continue
        try:                                             # so viele Zahlen wie der Kopf Spalten nennt, sonst ablehnen
            if len(tok) < ncol:
                raise ValueError
            rows.append([float(v) for v in tok[:ncol]] + [0.0] * (4 - ncol))
        except ValueError:
            raise ValueError(T("r2l_esd_line", name=Path(path).name, line=k)) from None
    a = np.array(rows, float)
    if len(a) < 2:
        raise ValueError(T("esd_bad", name=Path(path).name))
    src = "user"
    if unit not in ESD_UNITS:
        unit, src = esd_unit(path, a[:, 0])
    x = a[:, 0]
    ok = x > 0
    a, x = a[ok], x[ok]
    nm = x if unit == "nm" else 1e7 / x if unit == "cm-1" else HC_EV_NM / x
    o = np.argsort(nm)
    return dict(nm=nm[o], total=a[o, 1], fc=a[o, 2], ht=a[o, 3], unit=unit, unit_src=src)


def esd_shift(nm, shift_ev):
    """Wellenlängen um shift_ev (eV) in der Energie verschieben (wie die TD-DFT-Verschiebung)."""
    return HC_EV_NM / (HC_EV_NM / np.asarray(nm, float) + shift_ev) if shift_ev else np.asarray(nm, float)


# -- Ladungen und Spinpopulationen (DFT-Tab, Reiter „Ladungen“) -------------------------------------------------
# Nur Layouts, die an echten Ausgaben geprüft sind: ORCA 5/6 „MULLIKEN ATOMIC CHARGES [AND SPIN POPULATIONS]“ und
# „LOEWDIN ATOMIC CHARGES [AND SPIN POPULATIONS]“, Gaussian 16 „Mulliken charges[ and spin densities]:“. Hirshfeld
# (ORCA „HIRSHFELD ANALYSIS“, Gaussian „Hirshfeld charges“) und NPA liegen nicht als echte Ausgabe vor: nicht gelesen
# (NBO/NPA: eigener Leser formats/nbo.py). Neue Schemata als weiterer Eintrag in POP_SCHEMES.
POP_SCHEMES = ("mulliken", "loewdin")
# nicht _ORCA_POP: so heißt weiter oben das Zeilenmuster des EPR-Lesers (Namenskollision beim Zusammenführen)
_ORCA_POP_HEADS = {"mulliken": re.compile(r"^MULLIKEN ATOMIC CHARGES(?: AND SPIN (?:POPULATIONS|DENSITIES))?\s*$", re.M),
                   "loewdin": re.compile(r"^LOEWDIN ATOMIC CHARGES(?: AND SPIN (?:POPULATIONS|DENSITIES))?\s*$", re.M)}
_ORCA_ROW = re.compile(r"^\s*(\d+)\s+([A-Z][a-z]?)\s*:\s*(-?\d+\.\d+)(?:\s+(-?\d+\.\d+))?\s*$")
_G_POP = re.compile(r"^ Mulliken charges(?: and spin densities)?:\s*$", re.M)
_G_ROW = re.compile(r"^\s*(\d+)\s+([A-Z][a-z]?)\s+(-?\d+\.\d+)(?:\s+(-?\d+\.\d+))?\s*$")


def _pop_block(lines, row_re, base):
    """Zeilen nach der Überschrift bis zur ersten Nicht-Atomzeile (Trennstriche/Kopf „1 2“ davor überspringen)."""
    els, q, s, started = [], [], [], False
    for ln in lines:
        m = row_re.match(ln)
        if m is None:
            if started:
                break
            if ln.strip() and not re.fullmatch(r"[-\s\d]+", ln):   # unerwarteter Text vor der ersten Zeile
                return None
            continue
        started = True
        if int(m.group(1)) - base != len(els):            # Lücke in der Nummerierung: Layout nicht wie erwartet
            return None
        els.append(m.group(2))
        q.append(float(m.group(3)))
        s.append(float(m.group(4)) if m.group(4) is not None else None)
    if not els:
        return None
    return dict(els=els, charge=q, spin=s if all(v is not None for v in s) else None)


def parse_populations(text) -> dict:
    """Ladungen (und Spinpopulationen, wo gedruckt) je Schema -> {Schema: {els, charge, spin|None}}, jeweils der
    letzte Block der Ausgabe (Endgeometrie). Fehlende Schemata fehlen im Ergebnis (keine leeren Spalten)."""
    out = {}
    if is_orca(text):
        for key, head in _ORCA_POP_HEADS.items():
            hits = list(head.finditer(text))
            if hits:
                b = _pop_block(text[hits[-1].end():].splitlines()[1:400000], _ORCA_ROW, 0)
                if b:
                    out[key] = b
    elif is_gaussian(text):
        hits = list(_G_POP.finditer(text))
        if hits:
            b = _pop_block(text[hits[-1].end():].splitlines()[1:400000], _G_ROW, 1)
            if b:
                out["mulliken"] = b
    n = {len(b["els"]) for b in out.values()}
    return out if len(n) <= 1 else {}               # verschiedene Atomzahlen: nichts zeigen statt falsch zuordnen
