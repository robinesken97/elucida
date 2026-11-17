"""
elucida/formats/nbo.py - NBO-Ausgaben lesen (nichts rechnen): Natural Population Analysis, NBO-Liste mit Besetzung und
Hybriden, E(2)-Tabelle (zweite Ordnung), NRT (Resonanzstrukturen mit Gewicht, natürliche Bindungsordnungen,
Valenzen) und die NRT-Strukturen der CML-Datei (Schlüsselwort NRTCML).

Geprüft (Layout) nur an echten Ausgaben von NBO 7.0.10 über ORCA 6.0.0 (geschlossenschalig, eine NBO-Analyse je
Datei, UTF-8 und UTF-16 aus PowerShell). Andere NBO-Versionen, Gaussian/GENNBO-Ausgaben und offenschalige Rechnungen
werden mit Meldung abgelehnt. Wiberg-Matrix (BNDIDX, „Wiberg bond index matrix in the NAO basis“ + „Totals by atom“):
Layout wie im NBO-7.0-Handbuch (B.6.5), geprüft an öffentlichen echten Ausgaben (ORCA 6.1.1 + NBO 7.0, ORCA 5.0.4 +
NBO 7.0.5, GENNBO 7.0.10), streng gelesen (Spaltenblöcke vollständig, symmetrisch, Diagonale 0), sonst nicht gelesen
und gemeldet. Alle Werte bleiben Text wie in der Ausgabe.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from elucida.app.i18n import T
from elucida.formats.calc import is_orca, parse_orca

NBO_VERSIONS = ("7.0",)                 # geprüfte Hauptversionen (7.0.10)
ORCA_MAJOR = ("6",)

_TYPE = r"(?:BD\*|BD|3C\*|3Cn|3C|LP\*|LP|CR|RY\*|RY|LV\*|LV)"
_ATOM = r"[A-Z][a-z]?\s*\d+"
LABEL = rf"({_TYPE})\s*\(\s*(\d+)\)\s*({_ATOM}(?:\s*-\s*{_ATOM}){{0,2}})"
_NUM = r"(-?\d+\.\d+|\*+)"
_E2_ROW = re.compile(rf"^\s*(\d+)\.\s*{LABEL}\s+(\d+)\.\s*{LABEL}\s+{_NUM}\s+{_NUM}\s+{_NUM}\s*$")
_SUM_ROW = re.compile(rf"^\s*(\d+)\.\s*{LABEL}\s+(\d+\.\d+)\s+(-?\d+\.\d+)")
_LIST_HEAD = re.compile(rf"^\s*(\d+)\.\s*\(\s*(\d+\.\d+)\)\s*{LABEL}(.*)$")
_POL = re.compile(r"^\s*\(\s*(\d+\.\d+)%\)\s+(-?\d+\.\d+)\*\s*([A-Z][a-z]?)\s*(\d+)\s+(s\(.*)$")
_HYB = re.compile(r"([spdfg])\s*(\d+\.\d+|\*+)?\(\s*(\d+\.\d+)%\)")
_NPA_ROW = re.compile(r"^\s*([A-Z][a-z]?)\s*(\d+)\s+(-?\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)"
                      r"(?:\s+(-?\d+\.\d+))?\s*$")         # offenschalig: natürliche Spindichte als 8. Spalte
_VAL_ROW = re.compile(r"^\s*(\d+)\.\s+([A-Z][a-z]?)\s+" + r"\s+".join([r"(-?\d+\.\d+)"] * 5) + r"\s*$")
_LEWIS = re.compile(r"^\s*(Total Lewis|Valence non-Lewis|Rydberg non-Lewis)\s+(\d+\.\d+)\s+\(\s*(\d+\.\d+)%\)")


def atoms_of(text):
    """„N  4- C  7“ -> [(„N“, 4), („C“, 7)]."""
    return [(m.group(1), int(m.group(2))) for m in re.finditer(r"([A-Z][a-z]?)\s*(\d+)", text)]


def nbo_label(typ, n, atoms):
    """Lesbare Bezeichnung wie in Veröffentlichungen: „LP(1) N8“, „BD*(2) N4–C7“."""
    return f"{typ}({n}) " + "–".join(f"{el}{k}" for el, k in atoms)


def hybrid(comp):
    """Zusammensetzung [(l, Verhältnis, %)] wie gedruckt -> Mini-Auszeichnung „sp^{1.70}“ (Verhältnisse wie
    gedruckt). Reines s/p ohne Hochzahl. Ist ein Verhältnis übergelaufen („99.99“, „*“), ist sp^λ nicht eindeutig:
    dann die Anteile wie gedruckt („s 0.06%, p 99.88%“)."""
    d = {l: (r, p) for l, r, p in comp}
    if "s" not in d:
        return ""
    s_pct = float(d["s"][1])
    if s_pct >= 99.995:
        return "s"
    if s_pct == 0.0:                                     # Verhältnisse beziehen sich dann auf p: reines p
        return "p"
    out = "sp"
    if "p" in d:
        lam = d["p"][0] or ""
        if lam.startswith("*") or lam == "99.99":
            return ", ".join(f"{l} {p}%" for l, (_, p) in d.items() if float(p) >= 0.005)
        if lam == "0.00":                                # H: s(99.9x%)p 0.00 – als sp^0 gedruckt, gemeint ist s
            return "s"
        out += "^{" + lam + "}"
    for l in "dfg":
        if l in d and float(d[l][1]) >= 1.0:
            r = d[l][0] or ""
            if r.startswith("*") or r == "99.99":
                return ", ".join(f"{x} {p}%" for x, (_, p) in d.items() if float(p) >= 0.005)
            out += l + "^{" + r + "}"
    return out


def plain(markup):
    """„sp^{1.70}“ -> „sp1.70“ (CSV)."""
    return re.sub(r"[\^_]\{([^}]*)\}", r"\1", markup)


def _block(text):
    """Text der NBO-Analyse (vom Kopf „NBO 7.0“ bis „NBO analysis completed“) und Kopfzeilen."""
    heads = [m.start() for m in re.finditer(r"\*{5,} NBO \d+\.\d+ \*{5,}", text)]
    if not heads:
        raise ValueError(T("nbo_none"))
    if len(heads) > 1:
        raise ValueError(T("nbo_several", n=len(heads)))
    end = text.find("NBO analysis completed", heads[0])
    return text[heads[0]:end if end > 0 else len(text)]


def _citation(lines, i):
    """Zitierzeilen nach „Cite this program … as:“ bis zur Leerzeile, zusammengefügt."""
    out, j = [], i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    while j < len(lines) and lines[j].strip():
        out.append(lines[j].strip())
        j += 1
    return re.sub(r"\s+", " ", " ".join(out))


def orca_citation(text):
    """Erste „essential“ Zitierung aus „SUGGESTED CITATIONS FOR THIS RUN“ (wie gedruckt) oder ''."""
    k = text.find("List of essential papers")
    if k < 0:
        return ""
    L = text[k:k + 3000].splitlines()[1:]
    out = []
    for ln in L:
        s = ln.strip()
        if not s:
            if out:
                break
            continue
        if re.match(r"^\d+\.\s", s):
            if out:
                break
            s = s.split(".", 1)[1].strip()
        out.append(s)
    return "; ".join(out)


def nbo_keys(text):
    """NBOKEYLIST der ORCA-Eingabe ohne $NBO/$END und ohne FILE=… (Pfad des Nutzers) -> (Schlüssel, FILE-Stamm)."""
    m = re.search(r'NBOKEYLIST\s*=\s*"([^"]*)"', text[:200000])
    if not m:
        return "", ""
    toks = [t for t in m.group(1).split() if t.upper() not in ("$NBO", "$END")]
    stem = next((re.split(r"[\\/]", t.split("=", 1)[1])[-1] for t in toks if t.upper().startswith("FILE=")), "")
    keys = list(dict.fromkeys(t for t in toks if not t.upper().startswith("FILE=")))
    return " ".join(keys), stem


def parse_nbo(text) -> dict:
    """ORCA-6-Ausgabe mit NBO 7.0 -> dict (Werte als Text wie gedruckt). Fehlende Abschnitte fehlen (None/leer)."""
    if not is_orca(text):
        raise ValueError(T("nbo_program"))
    c = parse_orca(text)
    if not c["version"].split(".")[0] in ORCA_MAJOR:
        raise ValueError(T("nbo_orca_version", v=c["version"] or "?"))
    if c["mult"] not in (None, 1, 2):                    # geprüft: Dublett (Radikal, Radikalkation)
        raise ValueError(T("nbo_open_shell", m=c["mult"]))
    blk = _block(text)
    L = blk.splitlines()
    ver, cite = "", ""
    for i, ln in enumerate(L[:40]):
        m = re.search(r"Cite this program \[NBO (\S+)\s*\(([^)]*)\)\]", ln)
        if m:
            ver, cite = m.group(1), _citation(L, i)
            break
    if not ver:                                          # gekürzte Ausgaben ohne Zitierblock: Version des Kopfs
        m = re.search(r"\*{5,} NBO (\d+\.\d+) \*{5,}", L[0] if L else "")
        ver = m.group(1) if m else ""
    if not ver or not any(ver == v or ver.startswith(v + ".") for v in NBO_VERSIONS):
        raise ValueError(T("nbo_version", v=ver or "?"))
    keys, stem = nbo_keys(text)
    out = dict(program="ORCA", version=c["version"], nbo_version=ver, nbo_cite=cite, orca_cite=orca_citation(text),
               keywords=c["keywords"], nbo_keys=keys, file_stem=stem, charge=c["charge"], mult=c["mult"],
               geometry=c["geometry"], normal=c["normal"], npa=[], nbos={}, lewis=[], e2=[], e2_thr="", nrt=None,
               wiberg=None, notes=[])
    parts = re.split(r"(?m)^\s*\*{7}\s+(Alpha|Beta)\s+spin orbitals\s+\*{7}\s*$", blk)
    open_shell = c["mult"] not in (None, 1)
    if open_shell != (len(parts) > 1) or (open_shell and [x.strip() for x in parts[1::2]] != ["Alpha", "Beta"]):
        raise ValueError(T("nbo_open_shell", m=c["mult"] or "?"))
    _parse_section(parts[0].splitlines(), out)
    out["spin"] = None
    if open_shell:                                       # offenschalig: Gesamtteil + je Spin eigener Abschnitt
        out["spin"] = {}
        for lab, txt in zip(("alpha", "beta"), parts[2::2]):
            sec = dict(npa=[], nbos={}, lewis=[], e2=[], e2_thr="", nrt=None, wiberg=None, notes=[])
            _parse_section(txt.splitlines(), sec)
            out["notes"] += [x for x in sec["notes"] if x not in out["notes"]]
            sec["wiberg"] = _check_wiberg(sec["wiberg"], out["npa"], out["notes"])
            out["spin"][lab] = sec
        if out["nrt"] or any(sec["nrt"] for sec in out["spin"].values()):
            out["notes"].append(T("nbo_nrt_open"))       # offenschalige NRT an keiner echten Ausgabe gesehen
            out["nrt"] = None
        if out["nbos"] or out["e2"]:                     # Gesamtteil hat bei ORCA keine NBO-Liste: unerwartet
            raise ValueError(T("nbo_open_shell", m=c["mult"]))
        if any(sec["nbos"] or sec["e2"] for sec in out["spin"].values()):
            out["notes"].append(T("nbo_open_lists"))
        if not out["npa"] or "spin" not in out["npa"][0]:
            raise ValueError(T("nbo_open_shell", m=c["mult"]))
    if not out["npa"]:
        raise ValueError(T("nbo_no_npa"))
    out["wiberg"] = _check_wiberg(out["wiberg"], out["npa"], out["notes"])
    if c["geometry"] and len(c["geometry"]) != len(out["npa"]):
        raise ValueError(T("nbo_atom_count", n=len(out["npa"]), m=len(c["geometry"])))
    return out


def _check_wiberg(w, npa, notes):
    """Wiberg nur mit denselben Atomen wie die NPA; nicht lesbar (False) oder fremd -> None mit Hinweis."""
    w = w or None
    if w and [(a["el"], a["num"]) for a in npa] != [(w["els"][k], k) for k in sorted(w["els"])]:
        w = None
        if T("nbo_wiberg_bad") not in notes:
            notes.append(T("nbo_wiberg_bad"))
    return w


def _parse_section(L, out):
    """Abschnitt einer NBO-Analyse (ganz bzw. gesamt/Alpha/Beta) in `out` (npa, nbos, lewis, e2, e2_thr, nrt, wiberg)."""
    n = len(L)
    i = 0
    while i < n:
        s = L[i].strip()
        if s.startswith("Summary of Natural Population Analysis"):
            j = i + 1
            while j < n and not L[j].lstrip().startswith("===="):
                m = _NPA_ROW.match(L[j])
                if m:
                    out["npa"].append(dict(el=m.group(1), num=int(m.group(2)), charge=m.group(3), core=m.group(4),
                                           valence=m.group(5), rydberg=m.group(6), total=m.group(7),
                                           **({"spin": m.group(8)} if m.group(8) else {})))
                j += 1
            i = j
        elif s.startswith("(Occupancy)") and "Bond orbital" in s:
            i = _parse_list(L, i + 1, out["nbos"])
            continue
        elif s.startswith("Wiberg bond index matrix in the NAO basis") and out["wiberg"] is None:
            out["wiberg"], i = _parse_wiberg(L, i + 1)
            if out["wiberg"] is None:
                out["notes"].append(T("nbo_wiberg_bad"))
                out["wiberg"] = False                    # gesehen, nicht lesbar: kein zweiter Versuch
            continue
        elif s.startswith("SECOND ORDER PERTURBATION THEORY ANALYSIS"):
            j = i + 1
            while j < n and not L[j].strip().startswith("NATURAL BOND ORBITALS"):
                m = re.search(r"Threshold for printing:\s*(\d+\.\d+)", L[j])
                if m:
                    out["e2_thr"] = m.group(1)
                m = _E2_ROW.match(L[j])
                if m:
                    g = m.groups()
                    if any(v.startswith("*") for v in g[8:11]):
                        out["notes"].append(T("nbo_e2_overflow", row=L[j].strip()))
                    else:
                        out["e2"].append(dict(donor=int(g[0]), d_type=g[1], d_n=int(g[2]), d_atoms=atoms_of(g[3]),
                                              acceptor=int(g[4]), a_type=g[5], a_n=int(g[6]), a_atoms=atoms_of(g[7]),
                                              e2=g[8], de=g[9], f=g[10]))
                j += 1
            i = j
            continue
        elif s.startswith("NATURAL BOND ORBITALS (Summary)"):
            j = i + 1
            while j < n and not L[j].strip().startswith("$CHOOSE") and not L[j].strip().startswith("Charge unit"):
                m = _SUM_ROW.match(L[j])
                if m:
                    k = int(m.group(1))
                    e = out["nbos"].setdefault(k, dict(idx=k, type=m.group(2), n=int(m.group(3)),
                                                      atoms=atoms_of(m.group(4)), occ=m.group(5), centers=[], hyb=""))
                    e["energy"] = m.group(6)
                m = _LEWIS.match(L[j])
                if m:
                    out["lewis"].append(m.groups())
                j += 1
            i = j
            continue
        elif s.startswith("NATURAL RESONANCE THEORY ANALYSIS"):
            if out["nrt"] is not None:
                out["nrt"] = None
                out["notes"].append(T("nbo_nrt_several"))
                break
            out["nrt"], i = _parse_nrt(L, i + 1)
            continue
        i += 1
    return out


def _parse_list(L, i, nbos):
    """Hauptliste „(Occupancy) Bond orbital / Coefficients / Hybrids“: je NBO Typ, Atome, Besetzung und die Hybride
    (einzentrig auf der Kopfzeile, zweizentrig je Zentrum mit Polarisation). Endet vor „NHO DIRECTIONALITY“."""
    n, cur = len(L), None
    while i < n:
        ln = L[i]
        s = ln.strip()
        if s.startswith("NHO DIRECTIONALITY") or s.startswith("SECOND ORDER PERTURBATION") \
                or s.startswith("NATURAL BOND ORBITALS"):
            break
        m = _LIST_HEAD.match(ln)
        if m:
            k = int(m.group(1))
            cur = nbos.setdefault(k, dict(idx=k, type=m.group(3), n=int(m.group(4)), atoms=atoms_of(m.group(5)),
                                          occ=m.group(2), centers=[], hyb=""))
            rest = m.group(6)
            cur["comp"] = _HYB.findall(rest) if len(cur["atoms"]) == 1 else []
        elif cur is not None:
            p = _POL.match(ln)
            if p:
                cur["centers"].append(dict(pct=p.group(1), el=p.group(3), num=int(p.group(4)),
                                           comp=_HYB.findall(p.group(5))))
            elif re.match(r"^\s+[dfg]\s*(\d+\.\d+|\*+)\(", ln):      # Fortsetzung der Zusammensetzung (f, g …)
                tgt = cur["centers"][-1]["comp"] if cur["centers"] else cur.setdefault("comp", [])
                tgt += _HYB.findall(ln)
        i += 1
    for e in nbos.values():
        if e["centers"]:
            e["hyb"] = "; ".join(f"{c['el']}{c['num']} ({c['pct']}%) {hybrid(c['comp'])}".rstrip()
                                 for c in e["centers"])
        elif e.get("comp"):
            e["hyb"] = hybrid(e["comp"])
    return i


def _parse_nrt(L, i):
    """NRT-Abschnitt: Einstellungen, Gewichte der Resonanzstrukturen (mit „Added(Removed)“ gegenüber RS 1),
    natürliche Bindungsordnungen gesamt/kovalent/ionisch (Paare i < j), Valenzen. -> (dict, Index danach)."""
    n = len(L)
    nrt = dict(settings=[], rs=[], others="", bo={}, val=[])
    j = i
    while j < n and not L[j].strip().startswith("TOPO matrix"):
        m = re.match(r"^\s*(Parent structure threshold|Delocalization list threshold|Maximum search cycles):\s*(.+)$",
                     L[j])
        if m:
            nrt["settings"].append((m.group(1), m.group(2).strip()))
        j += 1
    while j < n and "Weight(%)" not in L[j]:
        j += 1
    j += 2                                               # Kopf + Strichlinie
    while j < n and not L[j].strip().startswith("---"):
        m = re.match(r"^\s*(\d+)\s+(\d+\.\d+)\s*(.*)$", L[j])
        o = re.match(r"^\s*others\s+(\d+\.\d+)", L[j])
        if m:
            nrt["rs"].append(dict(rs=int(m.group(1)), weight=m.group(2), change=m.group(3).strip()))
        elif o:
            nrt["others"] = o.group(1)
        elif L[j].strip() and nrt["rs"]:
            nrt["rs"][-1]["change"] = (nrt["rs"][-1]["change"] + " " + L[j].strip()).strip()
        j += 1
    while j < n and not L[j].strip().startswith("Natural Bond Order"):
        j += 1
    cols, row, el = [], None, {}
    while j < n and not L[j].strip().startswith("Natural Atomic Valencies"):
        ln = L[j]
        h = re.match(r"^\s*Atom\s+([\d\s]+)$", ln)
        t = re.match(r"^\s*(\d+)\.\s+([A-Z][a-z]?)\s+t\s+(.*)$", ln)
        ci = re.match(r"^\s+([ci])\s+(.*)$", ln)
        if h:
            cols = [int(x) for x in h.group(1).split()]
        elif t:
            row = int(t.group(1))
            el[row] = t.group(2)
            _bo_row(nrt["bo"], row, cols, t.group(3).split(), 0)
        elif ci and row is not None:
            _bo_row(nrt["bo"], row, cols, ci.group(2).split(), 1 if ci.group(1) == "c" else 2)
        j += 1
    while j < n and not L[j].strip().startswith("$NRTSTR") and not L[j].strip().startswith("RESONANCE NATURAL"):
        m = _VAL_ROW.match(L[j])
        if m:
            g = m.groups()
            nrt["val"].append(dict(num=int(g[0]), el=g[1], valency=g[2], covalency=g[3], electrovalency=g[4],
                                   count=g[5], formal=g[6]))
        j += 1
    nrt["els"] = el
    return nrt, j


def _bo_row(bo, row, cols, vals, k):
    if len(vals) != len(cols):
        return
    for col, v in zip(cols, vals):
        if col > row and v != "---":
            bo.setdefault((row, col), ["", "", ""])[k] = v


_WB_HEAD = re.compile(r"^\s*Atom((?:\s+\d+)+)\s*$")
_WB_VAL = re.compile(r"^\d+\.\d{4}$")


def _wiberg_block(L, i, stop):
    """Matrix in Spaltenblöcken (Kopf „Atom  1 2 …“, Strichzeile, Zeilen „  n. El  w …“) bis zur Zeile `stop`.
    -> ({(i, j): Text}, {n: El}, Index der Zeile `stop`) oder None, wenn etwas nicht dem Muster folgt."""
    n_, M, els, cols, rows_in_block = len(L), {}, {}, None, 0
    while i < n_ and not L[i].strip().startswith(stop):
        ln = L[i]
        h = _WB_HEAD.match(ln)
        r = re.match(r"^\s*(\d+)\.\s+([A-Z][a-z]?)\s+(.*)$", ln)
        if h:
            if cols is not None and rows_in_block != len(els):
                return None
            cols, rows_in_block = [int(x) for x in h.group(1).split()], 0
        elif r and cols is not None:
            vals = r.group(3).split()
            if len(vals) != len(cols) or not all(_WB_VAL.match(v) for v in vals):
                return None
            k = int(r.group(1))
            if els.setdefault(k, r.group(2)) != r.group(2):
                return None
            for c, v in zip(cols, vals):
                M[(k, c)] = v
            rows_in_block += 1
        elif ln.strip() and not set(ln.strip()) <= set("- "):
            return None
        i += 1
    if i >= n_ or cols is None:
        return None
    return M, els, i


def _parse_wiberg(L, i):
    """BNDIDX: „Wiberg bond index matrix in the NAO basis“ + „Wiberg bond index, Totals by atom“ (NBO-7-Handbuch B.6.5).
    Streng: alle Spalten 1…N je Zeile, symmetrisch, Diagonale 0.0000, Summen für dieselben Atome. -> (dict | None, i)."""
    got = _wiberg_block(L, i, "Wiberg bond index, Totals by atom")
    if got is None:
        return None, i
    M, els, i = got
    N = len(els)
    if sorted(els) != list(range(1, N + 1)) or len(M) != N * N \
            or any(M[(k, k)] != "0.0000" or M[(k, c)] != M[(c, k)] for k in els for c in els):
        return None, i
    tot, j = {}, i + 1
    while j < len(L):
        m = re.match(r"^\s*(\d+)\.\s+([A-Z][a-z]?)\s+(\d+\.\d{4})\s*$", L[j])
        if m:
            tot[int(m.group(1))] = m.group(3)
        elif tot and not L[j].strip():
            break
        j += 1
    if sorted(tot) != sorted(els):
        return None, j
    return dict(matrix=M, els=els, totals=tot), j


def wiberg_bonds(w, thr=0.0):
    """[(i, j, Index)] (Atomnummern ab 1, i < j) mit Index ≥ thr und > 0, nach i, j."""
    return [(a, b, v) for (a, b), v in sorted((w or {}).get("matrix", {}).items())
            if a < b and float(v) >= thr and float(v) > 0]


def nrt_bonds(nrt, thr=0.0):
    """[(i, j, total, covalent, ionic)] (Atomnummern ab 1) mit Gesamtordnung ≥ thr, nach i, j."""
    out = []
    for (a, b), (t, c, i) in sorted((nrt or {}).get("bo", {}).items()):
        if t and float(t) >= thr and float(t) > 0:
            out.append((a, b, t, c, i))
    return out


# ---------------------------------------------------------------------------- NRT-Strukturen (CML)
def cml_name(stem):
    """CML-Datei der Ausgabe: <FILE>-nrt.cml (NBO 7, Schlüsselwort NRTCML)."""
    return f"{stem}-nrt.cml" if stem else ""


def parse_cml(path) -> list[dict]:
    """CML von NBO 7 (NRTCML) -> [dict(weight, rhonl, els, xyz, lp, bonds [(i, j, Ordnung)])] (Indizes ab 0; lp None,
    wo das Atom kein `lonePair` hat – NBO 7 schreibt es sonst immer, auch 0).
    Gewicht und rhoNL als Text wie im Titel „Wgt=56.67%  rhoNL=2.50244“."""
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError:                                    # leer/abgeschnitten/kein XML: nie roher Parsertext
        raise ValueError(T("r2l_cml_bad", name=Path(path).name)) from None
    out = []
    for mol in root.iter("molecule"):
        m = re.match(r"\s*Wgt=\s*(\d+\.\d+)%\s+rhoNL=\s*(\S+)", mol.get("title") or "")
        if not m:
            raise ValueError(T("nbo_cml_bad"))
        ids, els, xyz, lp = {}, [], [], []
        for k, a in enumerate(mol.iter("atom")):
            ids[a.get("id")] = k
            els.append(a.get("elementType"))
            xyz.append([float(a.get("x3")), float(a.get("y3")), float(a.get("z3"))])
            lp.append(int(a.get("lonePair")) if a.get("lonePair") is not None else None)   # fehlt: unbekannt
        bonds = []
        for b in mol.iter("bond"):
            a1, a2 = (b.get("atomRefs2") or "").split()
            bonds.append((ids[a1], ids[a2], int(b.get("order"))))
        out.append(dict(weight=m.group(1), rhonl=m.group(2), els=els, xyz=xyz, lp=lp, bonds=bonds))
    if not out:
        raise ValueError(T("nbo_cml_bad"))
    return out


VALENCE_E = {"H": 1, "B": 3, "C": 4, "N": 5, "O": 6, "F": 7, "Si": 4, "P": 5, "S": 6, "Cl": 7, "Br": 7, "I": 7}


def formal_charges(st):
    """Formalladungen einer Lewis-Struktur aus der CML: Valenzelektronen − 2·freie Paare − Σ Bindungsordnungen
    (nur Elemente aus VALENCE_E, sonst None). Fehlt `lonePair` bei einem Atom, ist die Struktur unvollständig: alle None
    (keine Ladung erfinden)."""
    if None in st["lp"]:
        return [None] * len(st["els"])
    order = [0] * len(st["els"])
    for a, b, o in st["bonds"]:
        order[a] += o
        order[b] += o
    return [VALENCE_E[e] - 2 * lp - s if e in VALENCE_E else None for e, lp, s in zip(st["els"], st["lp"], order)]


def check_cml(structs, nbo):
    """CML passt zur Ausgabe: gleiche Elemente in gleicher Reihenfolge, Koordinaten ± 0.01 Å (CML hat zwei
    Nachkommastellen) und die erste Struktur hat das Gewicht von RS 1. Sonst ValueError (nie zuordnen raten)."""
    geo = nbo["geometry"] or []
    els = [g[1][0] for g in geo]
    xyz = [[float(v) for v in g[1][1:4]] for g in geo]
    for s in structs:
        if s["els"] != els:
            raise ValueError(T("nbo_cml_atoms"))
        if max(abs(p - q) for a, b in zip(s["xyz"], xyz) for p, q in zip(a, b)) > 0.01:
            raise ValueError(T("nbo_cml_atoms"))
    rs = (nbo.get("nrt") or {}).get("rs") or []
    if rs and structs[0]["weight"] != rs[0]["weight"]:
        raise ValueError(T("nbo_cml_weight", a=structs[0]["weight"], b=rs[0]["weight"]))


def find_cml(out_path, nbo):
    """Pfad der CML-Datei neben der Ausgabe (Name aus FILE=) oder None."""
    if not nbo.get("file_stem"):                             # ohne FILE= kein Name (with_name("") wirft ValueError)
        return None
    p = Path(out_path).with_name(cml_name(nbo["file_stem"]))
    return p if p.is_file() else None
