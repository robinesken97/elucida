"""HOMA (Harmonic Oscillator Model of Aromaticity) für Ringe einer Geometrie (Kristallstruktur oder Rechnung).

HOMA = 1 − (1/n) Σ α_j (R_opt,j − R_i)²  (j = Bindungstyp, n = Zahl der Ringbindungen)
Krygowski 1993 erweitert die Form von Kruszewski/Krygowski 1972 (nur CC) auf Heteroatome. Zerlegung für Ringe mit
einem einzigen Bindungstyp (Krygowski & Cyrański 1996): HOMA = 1 − EN − GEO, EN = α (R_opt − R_av)²,
GEO = (α/n) Σ (R_av − R_i)². Für gemischte Ringe ist die Zerlegung dort nicht definiert -> keine EN/GEO-Werte.

Parameter (nichts geschätzt; nicht parametrisierte Bindungen geben keinen Wert, sondern den fehlenden Typ):
- „homa“: T. M. Krygowski, J. Chem. Inf. Comput. Sci. 1993, 33, 70–78 (doi:10.1021/ci00011a011), Werte wie
  tabelliert in T. M. Krygowski, H. Szatyłowicz, ChemTexts 2015, 1 (3) (doi:10.1007/s40828-015-0012-2); CC/CN/NN/CO
  zusätzlich bestätigt durch Tabelle 1 in E. M. Arpa, S. Stafström, B. Durbeej, J. Org. Chem. 2025, 90, 1297–1308
  (Spalte „HOMA S0“, dort ref 22 = Krygowski 1993).
- „homac“: HOMAc, Arpa, Stafström, Durbeej, J. Org. Chem. 2025, 90, 1297–1308 (doi:10.1021/acs.joc.4c02475),
  Tabelle 1, Spalte „HOMAc S0“ (CASPT2-Referenzgeometrien); nur CC, CN, NN, CO.
"""
import numpy as np

from elucida.core.uvvis import fmt_num

# (R_opt [Å], α [Å⁻²]) je Bindungstyp; Schlüssel = Elementsymbole alphabetisch („CN“, nicht „NC“)
PARAMS = {
    "homa": dict(name="HOMA",
                 cite="T. M. Krygowski, J. Chem. Inf. Comput. Sci. 1993, 33, 70–78",
                 bonds={"CC": (1.388, 257.7), "CN": (1.334, 93.52), "CO": (1.265, 157.38), "CP": (1.698, 118.91),
                        "CS": (1.677, 94.09), "NN": (1.309, 130.33), "NO": (1.248, 57.21)}),
    "homac": dict(name="HOMAc",
                  cite="E. M. Arpa, S. Stafström, B. Durbeej, J. Org. Chem. 2025, 90, 1297–1308",
                  bonds={"CC": (1.392, 153.37), "CN": (1.333, 111.83), "NN": (1.318, 98.99), "CO": (1.315, 335.16)}),
}
EN_GEO_CITE = "T. M. Krygowski, M. Cyrański, Tetrahedron 1996, 52, 1713–1722"


def bond_type(a, b):
    """Bindungstyp aus zwei Elementsymbolen: „CN“ für C–N und N–C."""
    return "".join(sorted((a, b)))


def bond_name(t):
    """„CN“ -> „C–N“ (Elementsymbole mit zwei Buchstaben: „CSi“ -> „C–Si“)."""
    import re
    return "–".join(re.findall(r"[A-Z][a-z]?", t))


def homa(bonds, variant="homa"):
    """bonds = [(Element 1, Element 2, R [Å])] eines Rings -> dict(value, en, geo, n, mean, missing).
    missing: Bindungstypen ohne Parameter (dann value/en/geo None). en/geo nur bei einem einzigen Bindungstyp."""
    P = PARAMS[variant]["bonds"]
    types = [bond_type(a, b) for a, b, _ in bonds]
    R = np.array([float(r) for *_, r in bonds])
    out = dict(n=len(R), mean=float(R.mean()) if len(R) else None, value=None, en=None, geo=None,
               missing=sorted({t for t in types if t not in P}))
    if out["missing"] or not len(R):
        return out
    out["value"] = 1.0 - float(sum(P[t][1] * (P[t][0] - r) ** 2 for t, r in zip(types, R))) / len(R)
    if len(set(types)) == 1:
        ropt, a = P[types[0]]
        out["en"] = a * (ropt - out["mean"]) ** 2
        out["geo"] = a * float(np.mean((R - out["mean"]) ** 2))
    return out


def ring_bonds(els, xyz, ring):
    """Ring (Atomindizes in Ringfolge) -> [(Element i, Element i+1, Abstand)] reihum."""
    n = len(ring)
    return [(els[ring[i]], els[ring[(i + 1) % n]],
             float(np.linalg.norm(np.asarray(xyz[ring[i]], float) - np.asarray(xyz[ring[(i + 1) % n]], float))))
            for i in range(n)]


def ring_plane(xyz, ring):
    """Schwerpunkt und Normale der mittleren Ringebene."""
    P = np.array([xyz[k] for k in ring], float)
    c = P.mean(axis=0)
    return c, np.linalg.svd(P - c)[2][2]


def fmt(v):
    """Wert mit drei Nachkommastellen und echtem Minus (Tabelle, Bild, SI, CSV-Text gleich)."""
    if v is None:
        return "–"
    return fmt_num(v, 3)                                   # nie „−0.000“


def nics_for_ring(xyz, ring, pts, lateral=0.3):
    """NICS-Punkte (`dft_pages.nics_points`: xyz, nics, zz) über der Ringmitte: seitlich ≤ lateral Å von der Normalen
    durch den Schwerpunkt -> dict(„0“: NICS(0), „1“: NICS(1), „1zz“: NICS(1)zz), Mittel über beide Seiten; Höhe
    0 ± 0.1 Å bzw. 1 ± 0.1 Å. Leer, wenn kein Punkt passt."""
    c, nv = ring_plane(xyz, ring)
    got = {}
    for p, v, zz in zip(np.asarray(pts["xyz"], float), pts["nics"], pts["zz"]):
        h = float((p - c) @ nv)
        lat = float(np.linalg.norm((p - c) - h * nv))
        if lat > lateral:
            continue
        for key, h0 in (("0", 0.0), ("1", 1.0)):
            if abs(abs(h) - h0) <= 0.1:
                got.setdefault(key, []).append(float(v))
                if key == "1":
                    got.setdefault("1zz", []).append(float(zz))
    return {k: float(np.mean(v)) for k, v in got.items()}
