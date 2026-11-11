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
_CI_STATE = re.compile(r"STATE\s+(\d+):\s+Energy=\s*(" + NUMBER + r")\s+Eh\s+RefWeight=\s*(" + NUMBER + r")\b.*")
_CI_ROOT = re.compile(r"Root=\s*(\d+)\s+W=\s*" + NUMBER + r"\s+E0=\s*(" + NUMBER + r")\s+ECI=\s*(" + NUMBER + r")\s+DE=\s*(" + NUMBER + r")")
_CI_UNSEL = re.compile(r"Root=\s*(\d+)\s+E\(unsel\)=\s*(" + NUMBER + r")")
_CI_CONFIG = re.compile(r"\s*(" + NUMBER + r")\s*:\s*(\S*\[[012]+\]\S*)\s*")
_CI_ROW = re.compile(r"(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")")
_SCHMIDT = re.compile(r"found\s+(" + NUMBER + r")\s+between\s+\d+\s+and\s+\d+\s+-\s+redoing schmidt")
MAX_SCHMIDT = 0.5                # darüber waren die eingelesenen Orbitale nicht mehr orthogonal (zerstörter Start, echte H2-Ausgabe)


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
    out = [r for r in out if r["states"] or r["occupations"]] + _sorci_results(lines)
    if "ORCA TERMINATED NORMALLY" not in text:
        for r in out:
            if r["method"] == "SORCI":
                r["warnings"].append("Output does not end with ORCA TERMINATED NORMALLY; results may be incomplete.")
    return sorted(out, key=lambda r: r["line"])


def _sorci_results(lines):
    """Final (DDCI3) step of each SORCI run. The DDCI2 step only builds the natural orbitals and is never a result.

    Each block prints its states twice, reference CI first, so the last print wins. Energy = the printed STATE value,
    which the printed transition table uses too; it already holds ORCA's Davidson-type and unselected-CSF corrections.
    """
    out, blocks, r, schmidt = [], {}, None, None
    block = number = state = None
    extra, states = {}, {}
    for i, line in enumerate(lines):
        s = line.strip()
        if "JOB NUMBER" in s:
            schmidt = None
        m = _SCHMIDT.fullmatch(s)
        if m:
            schmidt = max(schmidt or 0, abs(float(m[1])))
        if s == "CI-BLOCK STRUCTURE":
            blocks, number = {}, None
        m = re.fullmatch(r"CI BLOCK\s+(\d+)", s)
        if m:
            number = int(m[1])
            blocks[number] = dict(multiplicity=None, irrep="", refs=[])
        if number is not None and r is None:
            m = re.fullmatch(r"(Multiplicity|Irrep)\s*\.\.\.\s*(-?\d+)", s)
            if m and m[1] == "Multiplicity":
                blocks[number]["multiplicity"] = int(m[2])
            elif m and m[2] != "-1":                   # -1: ohne Symmetrie
                blocks[number]["irrep"] = m[2]
            m = re.fullmatch(r"Reference\s+\d+:\s*(\S+)", s)
            if m:
                blocks[number]["refs"].append(m[1])
        if "S O R C I (DDCI3-STEP)" in s:
            refs = {x for b in blocks.values() for x in b["refs"]}
            cas = re.fullmatch(r"CAS\((\d+),(\d+)\)", next(iter(refs))) if len(refs) == 1 else None
            r = dict(id=f"mr-sorci-{len(out)}", method="SORCI", line=i + 1, states=[], occupations=[],
                     active_electrons=int(cas[1]) if cas else None, active_orbitals=int(cas[2]) if cas else None,
                     active_start=None, group=None, active_type="unconfirmed", convergence="ci", warnings=[], expected_roots={})
            if schmidt is not None and schmidt > MAX_SCHMIDT:
                r["warnings"].append(f"Input orbitals were not orthogonal on reading (overlap {schmidt:.3f}); results are unreliable.")
            out.append(r)
            block = state = None
            extra, states = {}, {}
            continue
        if r is None:
            continue
        m = re.fullmatch(r"\*\s*CI-BLOCK\s+(\d+)\s*\*", s)
        if m:
            block, state = int(m[1]), None
            continue
        m = _CI_ROOT.match(s)
        if m and block is not None:
            extra.setdefault((block, int(m[1])), {}).update(reference_energy=m[2], ci_energy=m[3], correction=m[4])
            continue
        m = _CI_UNSEL.match(s)
        if m and block is not None:
            extra.setdefault((block, int(m[1])), {})["unselected"] = m[2]
            continue
        m = _CI_STATE.fullmatch(s)
        if m and block in blocks:
            state = dict(root=int(m[1]), energy=m[2], reference_weight=m[3], line=i + 1, configurations=[], block=block,
                         multiplicity=blocks[block]["multiplicity"], irrep=blocks[block]["irrep"],
                         **extra.get((block, int(m[1])), {}))
            states[block, int(m[1])] = state
            continue
        m = _CI_CONFIG.fullmatch(line)
        if m and state is not None:
            state["configurations"].append(dict(weight=m[1], index=None, occupation=m[2], line=i + 1))
            continue
        if s == "TRANSITION ENERGIES":
            state, rows = None, []
            for ln in lines[i + 1:]:
                m = _CI_ROW.fullmatch(ln.strip())
                if m:
                    rows.append(m)
                elif rows:
                    break
            for m in rows:                             # Spalte Block zählt ab 0, CI-BLOCK ab 1
                if (int(m[5]) + 1, int(m[4])) in states:
                    states[int(m[5]) + 1, int(m[4])]["excitation_ev"] = m[7]
            r["states"] = list(states.values())
            if len(rows) != len(states):
                r["warnings"].append(f"Incomplete SORCI results: {len(states)} states, {len(rows)} in the transition table.")
            r = None
    if r is not None:                                  # abgebrochen: nichts als fertig ausgeben, aber Gefundenes zeigen
        r["states"] = list(states.values())
        r["warnings"].append("SORCI transition table missing; the run did not finish.")
    return [x for x in out if x["states"]]


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
    elif r["convergence"] == "unconfirmed":
        lines.append("CASSCF convergence not confirmed in the output.")
    if r["method"] == "SORCI":
        lines.append("Final DDCI3 step; energies as printed by ORCA, including its Davidson-type and unselected-CSF corrections.")
    for s in r["states"]:
        label = f"M={s['multiplicity']}, root={s['root']}" + (f", irrep={s['irrep']}" if s.get("irrep") else "")
        details = "".join(f"; {name} {s[key]}{unit}" for name, key, unit in (
            ("CI energy", "ci_energy", " Eh"), ("correction", "correction", " Eh"), ("unselected", "unselected", " Eh"),
            ("excitation energy", "excitation_ev", " eV")) if s.get(key) is not None)
        lines.append(f"{label}: {s['energy']} Eh{details}")
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


def make_test_sorci(path):
    """Synthetic numbers, layout of a real ORCA 6.0.1 SORCI output: DDCI2 step, then DDCI3 with two prints per block."""
    from pathlib import Path

    def block(n, mult_rows):
        return f"""***************************************
*              CI-BLOCK  {n}            *
***************************************
""" + "".join(f"STATE   {k}:  Energy=     -9.000000000 Eh RefWeight=  1.0000  0.00 eV      0.0 cm**-1\n" for k, _ in mult_rows) + "".join(
            f"Root= {k} W=   0.900 E0=    -9.000000000 ECI=    {e} DE=-0.000100\n" for k, e in mult_rows) + "".join(
            f" Root=  {k}  E(unsel)=      0.000000000\n" for k, _ in mult_rows) + "".join(
            f"STATE   {k}:  Energy=     {e}9 Eh RefWeight=  0.9000  0.00 eV      0.0 cm**-1\n      0.9000  : h---h---[20]\n"
            for k, e in mult_rows)
    table = """-------------------
TRANSITION ENERGIES
-------------------

The lowest energy is     -2.000000009 Eh

State Mult Irrep Root Block    mEh          eV      1/cm
  0    1    -1    0    0      0.000      0.000       0.0
  1    3    -1    0    1    500.000     13.606  109737.3
  2    1    -1    1    0    900.000     24.490  197527.2
#
"""
    head = """Program Version 6.0.1  -  RELEASE   -
JOB NUMBER  1
CI-BLOCK STRUCTURE
CI BLOCK 1
Multiplicity             ...   1
Irrep                    ...  -1
  Reference   1: CAS(2,2)
CI BLOCK 2
Multiplicity             ...   3
Irrep                    ...  -1
  Reference   1: CAS(2,2)
"""
    body = block(1, [(0, "-2.00000000"), (1, "-1.10000000")]) + block(2, [(0, "-1.50000000")]) + table
    text = (head + "# S O R C I (DDCI2-STEP) #\n" + body.replace("-2.00000000", "-7.00000000") + "# S O R C I (DDCI3-STEP) #\n" + body
            + "FINAL SINGLE POINT ENERGY -2.000000009\n****ORCA TERMINATED NORMALLY****\n")
    Path(path).write_text(text, encoding="utf-8")
    return Path(path)


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
