"""ORCA 6 multireference results. Printed decimal values remain strings.

Result sets are scoped to a final CASSCF block and method; initial CI guesses,
iteration energies, perturbative corrections and state averages are never used
as individual state energies. No inferred natural occupations or CI coefficients.
"""
from __future__ import annotations

import re
from decimal import Decimal

NUMBER = r"[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?"
_CAS = re.compile(r"CAS-SCF STATES FOR BLOCK\s+(\d+)\s+MULT=\s*(\d+)(?:\s+IRREP=\s*(\S+))?\s+NROOTS=\s*(\d+)")
_ROOT = re.compile(r"ROOT\s+(\d+):\s+E=\s*(" + NUMBER + r")\s+Eh")
_CONFIG = re.compile(r"\s*(" + NUMBER + r")\s+\[\s*(\d+)\]:\s*([012]+)\s*$")


def parse_orca_mr(text):
    """Return final result sets in file order; no automatic choice of method/root.

    ORBITAL ENERGIES is retained as a printed occupation table, not advertised
    as state-specific natural orbitals. Explicit N[i] tables keep their title
    and context. Unassigned densities cannot generate a diradical indicator.
    """
    version = re.search(r"Program Version\s+(\d+)\.", text)
    if not version or version[1] != "6":
        return []
    lines = text.splitlines()
    out, group, current, state, block = [], None, None, None, None
    nel = norb = active_start = maxiter = None
    pt_method, converged = "NEVPT2", False
    active_type = "unconfirmed"
    occ = None

    def result(method, i):
        nonlocal current, state, occ
        current = dict(id=f"mr-{len(out)}", method=method, line=i + 1, states=[],
                       occupations=[], active_electrons=nel, active_orbitals=norb,
                       active_start=active_start, group=group,
                       active_type=active_type,
                       convergence="fixed-orbitals" if maxiter == 1 else "converged" if converged else "unconfirmed",
                       warnings=[], expected_roots={})
        out.append(current)
        state, occ = None, None
        return current

    for i, line in enumerate(lines):
        s = line.strip()
        if "$new_job" in s.lower() or s.startswith("Program Version"):
            current, state, occ, block = None, None, None, None   # nichts Späteres an das letzte Ergebnis hängen
        if s == "ORCA-CASSCF":
            nel = norb = active_start = maxiter = None
            pt_method, converged = "NEVPT2", False
            active_type = "unconfirmed"
            current, state, occ, block, group = None, None, None, None, None
        for label, key in (("Number of active electrons", "nel"), ("Number of active orbitals", "norb"),
                           ("Max. number of iterations", "maxiter")):
            m = re.match(re.escape(label) + r"\s*\.\.\.\s*(\d+)", s)
            if m:
                if key == "nel": nel = int(m[1])
                elif key == "norb": norb = int(m[1])
                else: maxiter = int(m[1])
        m = re.match(r"Active\s+(\d+)\s*-\s*\d+\s+\(", s)
        if m:
            active_start = int(m[1])
        m = re.match(r"Active\s+Orbitals\s*\.\.\.\s*(\S+)", s)
        if m:
            active_type = m[1].lower()
        m = re.search(r"\(PT2\s*=\s*([^ )]+)\)", s)
        if m:
            pt_method = m[1]
        if "THE CAS-SCF ENERGY" in s and "HAS CONVERGED" in s:
            converged = True
        if s == "CASSCF RESULTS":
            group = i + 1
            result("CASSCF", i)
            block = None
            continue
        if s in ("NEVPT2 Results", "QD-NEVPT2 Results") and group is not None:
            result("QD-" + pt_method if s.startswith("QD-") else pt_method, i)
            block = None
            continue
        if current is None:
            continue
        if s.startswith("WARNING") and ("QD-Matrix" in s or "imaginary component" in s):
            current["warnings"].append(s)
        m = _CAS.fullmatch(s)
        if m and current["method"] == "CASSCF":
            block = dict(block=int(m[1]), multiplicity=int(m[2]), irrep=m[3] or "", nroots=int(m[4]))
            current["expected_roots"][m[1]] = int(m[4])
            state, occ = None, None
            continue
        m = _ROOT.match(s)
        if m and block is not None and current["method"] == "CASSCF":
            state = dict(root=int(m[1]), energy=m[2], line=i + 1, configurations=[], **block)
            current["states"].append(state)
            continue
        if "NEVPT2" in current["method"]:
            m = re.fullmatch(r"MULT\s+(\d+),?\s*(?:IRREP\s+(\S+),?\s*)?(?:ROOT\s+(\d+))?", s)
            if m:
                block = dict(multiplicity=int(m[1]), irrep=(m[2] or "").rstrip(','))
                state = None
                if m[3] is not None:
                    state = dict(root=int(m[3]), energy=None, line=i + 1, configurations=[], **block)
                    current["states"].append(state)
                continue
            m = re.fullmatch(r"ROOT\s*=\s*(\d+)", s)
            if m and block:
                state = dict(root=int(m[1]), energy=None, line=i + 1, configurations=[], **block)
                current["states"].append(state)
                continue
            if state is not None:
                for label, key in ((r"Total Energy \(E0\+dE\)\s*:\s*E", "energy"),
                                   (r"(?:Reference\s+Energy|Zero Order Energy)\s*:\s*E0", "reference_energy"),
                                   (r"Total Energy Correction\s*:\s*dE", "correction")):
                    m = re.match(label + r"\s*=\s*(" + NUMBER + r")\s*$", s)
                    if m:
                        state[key] = m[1]
        if state is not None:
            m = _CONFIG.fullmatch(line)
            if m:
                state["configurations"].append(dict(weight=m[1], index=m[2], occupation=m[3], line=i + 1))
        if s == "ORBITAL ENERGIES" and current["method"] == "CASSCF" and block is None:
            occ = dict(kind="printed-orbital-occupations", scope="unassigned", line=i + 1, rows=[])
            current["occupations"].append(occ)
            continue
        if s == "Natural Orbital Occupation Numbers:":
            # A title alone does not identify the state/density. Keep provenance;
            # never inherit an unrelated previous MULT/ROOT from the output.
            occ = dict(kind="natural-orbital-occupations", scope="unassigned", line=i + 1, rows=[])
            current["occupations"].append(occ)
            continue
        if occ is not None:
            pat = (r"N\[\s*(\d+)\]\s*=\s*(" + NUMBER + r")\s*$" if occ["kind"].startswith("natural")
                   else r"(\d+)\s+(" + NUMBER + r")\s+" + NUMBER + r"\s+" + NUMBER + r"(?:\s+\S+)?\s*$")
            m = re.fullmatch(pat, s)
            if m:
                occ["rows"].append(dict(orbital=int(m[1]), occupation=m[2], line=i + 1))
            elif occ["rows"]:
                occ = None
        # Restrict CI weights to contiguous state sections (not later analysis).
        if s in ("DENSITY MATRIX", "TIMINGS NEVPT2") or "TOTAL ENERGIES" in s or "TRANSITION ENERGIES" in s:
            state = None
    for r in out:
        r["states"] = [s for s in r["states"] if s.get("energy") is not None]
        r["occupations"] = [o for o in r["occupations"] if o["rows"]]
        if r["method"] == "CASSCF":
            complete = sum(r["expected_roots"].values()) == len(r["states"])
            if not complete:
                r["warnings"].append("Incomplete CASSCF state table; occupations cannot be assigned to a single state.")
            for o in r["occupations"]:
                if o["kind"] == "printed-orbital-occupations":
                    o["scope"] = "single-state" if complete and len(r["states"]) == 1 else "state-averaged-or-unspecified"
    roots = {r["group"]: sum(r["expected_roots"].values()) for r in out if r["method"] == "CASSCF"}
    for r in out:
        if "NEVPT2" in r["method"] and roots.get(r["group"]) not in (None, len(r["states"])):
            r["warnings"].append(f"Incomplete {r['method']} results: {len(r['states'])} of {roots[r['group']]} states.")
        if "ORCA TERMINATED NORMALLY" not in text:
            r["warnings"].append("Output does not end with ORCA TERMINATED NORMALLY; results may be incomplete.")
    return [r for r in out if r["states"] or r["occupations"]]


def luno_indicator(r):
    """y0 = n(LUNO), ONLY explicit natural active orbitals of one singlet.

    No Yamaguchi/PUHF spin-projection formula on a spin-adapted CASSCF density.
    Source: Nature, doi:10.1038/s41586-025-08745-1 (see handoff).
    This is a labelled NOON diagnostic, not a universal percentage of radicals.
    """
    if r["method"] != "CASSCF" or r.get("active_type") != "natural" or len(r["states"]) != 1:
        return None
    if r.get("convergence") == "unconfirmed":      # nicht konvergierte Orbitale: kein belastbarer Indikator
        return None
    if r["states"][0]["multiplicity"] != 1:
        return None
    nel, norb, start = (r.get(k) for k in ("active_electrons", "active_orbitals", "active_start"))
    if nel is None or norb is None or start is None or nel % 2 or not 0 < nel // 2 < norb:
        return None
    for o in r["occupations"]:
        if o["kind"] != "printed-orbital-occupations" or o["scope"] != "single-state":
            continue
        rows = [x for x in o["rows"] if start <= x["orbital"] < start + norb]
        if len(rows) != norb or len({x['orbital'] for x in rows}) != norb:
            continue
        values = [Decimal(x["occupation"].replace("D", "E").replace("d", "e")) for x in rows]
        if any(not 0 <= x <= 2 for x in values) or abs(sum(values) - nel) > Decimal("0.0001") * norb:
            continue
        rows.sort(key=lambda x: Decimal(x["occupation"]), reverse=True)
        hono, luno = rows[nel // 2 - 1], rows[nel // 2]
        if Decimal(luno["occupation"]) > 1:
            continue
        return dict(value=luno["occupation"], hono=hono, luno=luno)
    return None


def spin_gap(r, singlet, triplet, convention="S-T"):
    """Selected spin-pure states of the SAME result block; no geometry matching."""
    if convention not in ("S-T", "T-S"):
        raise ValueError("Unknown spin-gap convention")
    s, t = r["states"][singlet], r["states"][triplet]
    if s["multiplicity"] != 1 or t["multiplicity"] != 3:
        raise ValueError("Select a singlet and a triplet state")
    gap = Decimal(s["energy"].replace('D', 'E')) - Decimal(t["energy"].replace('D', 'E'))
    return gap if convention == "S-T" else -gap


def result_label(result):
    n, m = result.get("active_electrons"), result.get("active_orbitals")
    space = f" · CAS({n},{m})" if n is not None and m is not None else ""
    return f"{result['method']}{space} · L{result['line']}"


def report_lines(result):
    """English, reproducible SI text; distinguish imported values from metrics."""
    r = result
    lines = [result_label(r), "Electronic state energies (Eh); root indices as printed by ORCA."]
    if r["convergence"] == "fixed-orbitals":
        lines.append("Fixed-orbital calculation (CASSCF MaxIter = 1).")
    elif r["convergence"] != "converged":
        lines.append("CASSCF convergence not confirmed in the output.")
    for s in r["states"]:
        label = f"M={s['multiplicity']}, root={s['root']}" + (f", irrep={s['irrep']}" if s.get("irrep") else "")
        lines.append(f"{label}: {s['energy']} Eh")
        if s["configurations"]:
            lines.append("Printed configuration weights (not renormalized): " + "; ".join(
                f"{c['occupation']}: {c['weight']}" for c in s["configurations"]))
    for o in r["occupations"]:
        lines.append(f"{o['kind']} ({o['scope']}; orbital indices as printed):")
        lines.append("; ".join(f"{x['orbital']}: {x['occupation']}" for x in o["rows"]
                               if r.get("active_start") is None or r.get("active_orbitals") is None
                               or r['active_start'] <= x['orbital'] < r['active_start'] + r['active_orbitals']))
    lines += r["warnings"]
    ind = luno_indicator(r)
    if ind:
        lines += [f"NOON diradical indicator y0 = n(LUNO) = {ind['value']} (single-state singlet, natural active orbitals).",
                  f"HONO: orbital {ind['hono']['orbital']}, occupation {ind['hono']['occupation']}; "
                  f"LUNO: orbital {ind['luno']['orbital']}, occupation {ind['luno']['occupation']}.",
                  "NOON indicator as in doi:10.1038/s41586-025-08745-1; not a PUHF spin-projected index."]
    return lines


def make_test_mr(path):
    """Synthetic numbers only. Compact fixture for packaged selftest and unit tests."""
    from pathlib import Path
    text = '''Program Version 6.1.1
ORCA-CASSCF
Number of active electrons          ... 2
Number of active orbitals           ... 2
Active 1 - 2 (2 orbitals)
Max. number of iterations           ... 100
Active Orbitals                     ... natural
A PT2 calculation will be performed (PT2 = SC-NEVPT2)
ROOT   0: E= -99.000000 Eh
0.99999 [0]: 20
---- THE CAS-SCF ENERGY   HAS CONVERGED ----
CASSCF RESULTS
Final CASSCF energy : -10.100000000 Eh
ORBITAL ENERGIES
NO OCC E(Eh) E(eV)
0 2.0000 -1.0 -27.2
1 1.8000 -0.4 -10.8
2 0.2000 0.1 2.7

CAS-SCF STATES FOR BLOCK 0 MULT= 1 IRREP= Ag NROOTS= 1
ROOT 0: E= -10.100000000123 Eh
0.90000 [0]: 20
0.10000 [1]: 02

NEVPT2 Results
MULT 1, ROOT 0
Reference Energy : E0 = -10.100000000123
Total Energy Correction : dE = -0.200000000000
Total Energy (E0+dE) : E = -10.300000000123
QD-NEVPT2 Results
MULT 1
ROOT = 0
0.88000 [0]: 20
Total Energy (E0+dE) : E = -10.310000000123
TIMINGS NEVPT2
****ORCA TERMINATED NORMALLY****
'''
    Path(path).write_text(text, encoding="utf-8")
    return Path(path)
