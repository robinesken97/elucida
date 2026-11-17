"""Natürliche Übergangsorbitale (NTO) aus einer ORCA-Ausgabe (`%tddft DoNTO true end`).

ORCA 6 druckt je Zustand einen Block (geprüft an echten ORCA-6-TD-DFT-Ausgaben, auch Spin-Flip; Format wie im
Beispiel des ORCA-6.0-Handbuchs, Abschnitt „Natural Transition Orbitals“):

    NATURAL TRANSITION ORBITALS FOR STATE    1
    ...
    Natural Transition Orbitals were saved in name.s1.nto
    Threshold for printing occupation numbers 0.001000

     E=   0.143640 au      3.909 eV    31525.3 cm**-1
        61a ->  62a  : n=  0.96811794
        60a ->  63a  : n=  0.01661712

Je Zeile ein Paar Loch -> Teilchen (Orbitalnummern der .nto-Datei, ab 0 wie bei ORCA) mit dem Gewicht n. Die
.nto-Datei selbst (gbw-Format) liest Elucida nicht; der Nutzer wandelt sie mit orca_2mkl in Molden um oder schreibt
Cubes mit orca_plot. Ob die Besetzungen in einer so erzeugten Molden-Datei die Gewichte sind, ist nicht belegt: die
Gewichte kommen deshalb nur aus diesem Block (oder vom Nutzer)."""
import re

HARTREE_EV = 27.211386245988
_HEAD = re.compile(r"NATURAL TRANSITION ORBITALS FOR STATE\s+(\d+)")
_FILE = re.compile(r"Natural Transition Orbitals were saved in\s+(\S+)")
_E = re.compile(r"^\s*E=\s*(-?\d+\.\d+)\s+au")
_PAIR = re.compile(r"^\s*(\d+)([ab])\s*->\s*(\d+)([ab])\s*:\s*n=\s*(-?\d+\.\d+)")


def orca_nto_blocks(text):
    """-> [dict(state, E (eV, aus au), file (Name der .nto oder ""), pairs [(Loch-Nr., Spin, Teilchen-Nr., Spin, n)])]
    in der Reihenfolge der Ausgabe; Blöcke ohne Energie oder ohne Paare fallen weg."""
    out, cur = [], None
    for ln in text.splitlines():
        m = _HEAD.search(ln)
        if m:
            cur = dict(state=int(m.group(1)), E=None, file="", pairs=[])
            out.append(cur)
            continue
        if cur is None:
            continue
        m = _FILE.search(ln)
        if m:
            cur["file"] = m.group(1)
            continue
        m = _E.match(ln)
        if m and cur["E"] is None:
            cur["E"] = float(m.group(1)) * HARTREE_EV
            continue
        m = _PAIR.match(ln)
        if m and cur["E"] is not None:
            cur["pairs"].append((int(m.group(1)), m.group(2), int(m.group(3)), m.group(4), float(m.group(5))))
        elif cur["pairs"] and ln.strip():                    # erste andere Zeile nach den Paaren: Block zu Ende
            cur = None
    return [b for b in out if b["E"] is not None and b["pairs"]]


def block_for(blocks, E, tol=0.002):
    """Block zur Anregungsenergie E (eV) der Tabelle: genau einer innerhalb tol, sonst None (nie raten)."""
    hits = [b for b in blocks if abs(b["E"] - E) <= tol]
    return hits[0] if len(hits) == 1 else None
