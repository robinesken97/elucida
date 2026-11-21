"""
elucida/core/chem.py - CDXML lesen: Zeichnung (Orientierung wie in ChemDraw), Molmasse, Summenformel.

RDKit übernimmt die 2D-Koordinaten aus der CDXML, die Struktur wird also nicht neu
ausgerichtet, sondern nur im ACS-1996-Stil neu gezeichnet.
"""
from __future__ import annotations

import re
from pathlib import Path

from elucida.app.i18n import T


def mol_weight(mol):
    """Molmasse eines RDKit-Moleküls mit denselben mittleren Atommassen wie Elementaranalyse und eingetippte Formeln
    (`SI.AVG`, IUPAC 2021); markierte Atome (D, 13C) mit ihrer Isotopenmasse. RDKits `MolWt` trägt ältere Werte
    (S 32.067, Cl 35.453 …): dieselbe Verbindung hatte so zwei Molmassen, die sich in der 2. Nachkommastelle
    unterschieden (Literaturprüfung 2026-11). Element nicht in der Tabelle: RDKits Wert."""
    from elucida.si.lines import AVG
    total = 0.0
    for a in mol.GetAtoms():
        total += a.GetMass() if a.GetIsotope() else AVG.get(a.GetSymbol(), a.GetMass())
        total += a.GetTotalNumHs() * AVG["H"]
    return float(total)


def _rdkit():
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import Descriptors, Draw, rdMolDescriptors
        from rdkit.Chem.Draw import rdMolDraw2D
        RDLogger.DisableLog("rdApp.*")
        return Chem, Descriptors, Draw, rdMolDescriptors, rdMolDraw2D
    except ImportError as e:
        raise RuntimeError(T("need_rdkit")) from e


_CACHE = {}                            # (Pfad, Änderungszeit, Größe) -> Ergebnis (RDKit liest dieselbe CDXML sonst oft)


def load_cdxml(path, *, render=True) -> dict:
    """Wie _load_cdxml, zwischengespeichert je Datei und Stand; Rückgabe ist eine Kopie."""
    p = Path(path)
    try:
        st = p.stat()
        from elucida.app.i18n import get_lang
        key = (str(p.resolve()), st.st_mtime_ns, st.st_size, get_lang(), render)      # Warnungen sind übersetzt
    except OSError:
        return _load_cdxml(path, render=render)
    if key not in _CACHE:
        if len(_CACHE) >= 32:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = _load_cdxml(path, render=render)
    return {k: (list(v) if isinstance(v, list) else v) for k, v in _CACHE[key].items()}


def _xml_fragments(root) -> int:
    """Strukturen in der CDXML (Fragmente mit Atomen, ohne die in Abkürzungen verschachtelten)."""
    if root is None:
        return 0
    parent = {c: p for p in root.iter() for c in p}
    return sum(1 for f in root.iter("fragment") if parent.get(f) is not None and parent[f].tag != "n"
               and f.find("n") is not None)


# Gegenionen als Beschriftung ohne Atome (ChemDraw „PF6“, Octet „Unspecified“) oder mit falsch gelesenen Atomen (Octet
# liest „BArF“ als B–Ph–F): SMILES des Ions, Zusammensetzung nach dem IUPAC-Namen. Schlüssel ohne Klammern und Ladung,
# Groß-/Kleinschreibung egal. BArF/BArF4/BArF24 = Tetrakis[3,5-bis(trifluormethyl)phenyl]borat (Brookhart 1992,
# Organometallics 11, 3920); BArF20 = Tetrakis(pentafluorphenyl)borat.
_ARF = "c1cc(C(F)(F)F)cc(C(F)(F)F)c1"
_C6F5 = "c1c(F)c(F)c(F)c(F)c1F"
_IONS = {
    "F[P-](F)(F)(F)(F)F": ("PF6",),                                   # Hexafluoridophosphat
    "F[Sb-](F)(F)(F)(F)F": ("SbF6",),                                 # Hexafluoridoantimonat
    "F[As-](F)(F)(F)(F)F": ("AsF6",),                                 # Hexafluoridoarsenat
    "F[B-](F)(F)F": ("BF4",),                                         # Tetrafluoridoborat
    "[O-]Cl(=O)(=O)=O": ("ClO4",),                                    # Perchlorat
    "[O-]S(=O)(=O)C(F)(F)F": ("OTf", "TfO", "CF3SO3", "SO3CF3"),      # Trifluormethansulfonat
    "FC(F)(F)S(=O)(=O)[N-]S(=O)(=O)C(F)(F)F": ("NTf2", "Tf2N", "N(SO2CF3)2", "TFSI"),   # Bis(trifluormethansulfonyl)imid
    f"[B-]({_ARF})({_ARF})({_ARF}){_ARF}": ("BArF", "BArF4", "BArF24"),
    f"[B-]({_C6F5})({_C6F5})({_C6F5}){_C6F5}": ("BArF20",),
    "[B-](c1ccccc1)(c1ccccc1)(c1ccccc1)c1ccccc1": ("BPh4",),          # Tetraphenylborat
    "CC(=O)[O-]": ("OAc", "AcO"),                                     # Acetat
    "Cc1ccc(S(=O)(=O)[O-])cc1": ("OTs", "TsO"),                       # Tosylat
    "[O-][N+](=O)[O-]": ("NO3",),                                     # Nitrat
    "OS(=O)(=O)[O-]": ("HSO4",),                                      # Hydrogensulfat
    "[O-]S(=O)(=O)[O-]": ("SO4",),                                    # Sulfat („SO4 2-“)
    "I[I-]I": ("I3",),                                                # Triiodid
    "[N-]=[N+]=[N-]": ("N3",),                                        # Azid („N3-“ ist Index, kein Nitrid)
}
COUNTER_IONS = {name.lower(): smi for smi, names in _IONS.items() for name in names}
LABEL_TYPES = ("Nickname", "Fragment", "Unspecified", "GenericNickname")      # Knoten mit Text statt Element
_SIGNS = {"+": 1, "⊕": 1, "⁺": 1, "-": -1, "−": -1, "⊖": -1, "⁻": -1}
_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉", "01234567890123456789")


# Nichtmetalle: „X2+“ ist dort ein Molekülion (O2+, H2+), kein X²⁺ (auch für den eigenen CDXML-Zeichner)
_NONMETALS = set("H He B C N O F Ne Si P S Cl Ar Se Br Kr I Xe At Rn".split())


def monatomic(sym, sign):
    """Elementsymbol + Zahl + ein Zeichen ist ein einatomiges Ion (Zahl = Ladung, Entscheidung 191): Metallkation
    („Fe2+“, „Al3+“) oder Chalkogenid („O2-“, „S2-“); „I3-“, „N3-“, „O2+“, „H2+“ bleiben Molekülionen mit Index."""
    from ..formats.elements import ELEMENTS
    if sym not in ELEMENTS:
        return False
    return sym not in _NONMETALS if _SIGNS.get(sign) == 1 else sym in ("O", "S", "Se", "Te")


def ambiguous_count(body, digits):
    """Mehrstellige Zahl vor dem Ladungszeichen, die auch Index + Ladung sein kann („SO42-“, „CO32-“, „Hg22+“): ohne
    Kohlenstoff, mit O oder „)“ direkt davor („Fe(CN)64-“). Hill-Formeln organischer Ionen („C32H12BF24-“, „C19H15+“) bleiben Index.
    shortcut: Heuristik, Liste bei Bedarf erweitern."""
    els = re.findall(r"[A-Z][a-z]?", body)
    return len(digits) > 1 and bool(els) and ("C" not in els or els[-1] == "O" or body.endswith(")"))


def _label_charge(text):
    """-> (Text ohne Ladung, Ladung oder None, mehrdeutig). Regel (Entscheidung 191): hochgestellt, nach „]“ oder nach
    Leerzeichen ist die Zahl Ladung („X²⁻“, „[X]2+“, „SO4 2-“); direkt am Text nur beim einatomigen Ion (`monatomic`:
    „Fe2+“ +2, „O2-“ -2), sonst Index und Ladung = Zahl der Zeichen („NH4+“, „BF4-“, „I3-“, „N3-“, „O2+“). Mehrdeutige
    mehrstellige Zahl (`ambiguous_count`: „SO42-“, „Hg22+“): keine Ladung, Hinweis statt Raten."""
    s = str(text or "").strip()
    m = re.search(r"(\]?)(\s*)([⁰¹²³⁴⁵⁶⁷⁸⁹]*)(\d*)\s*([+\-−⊕⊖⁺⁻]+)$", s)
    if not m or len({_SIGNS[c] for c in m.group(5)}) != 1:
        return "".join(s.split()), None, False
    sign, digits = _SIGNS[m.group(5)[0]], m.group(4)
    body = "".join(s[:m.start(2)].split())
    if m.group(3):
        return body, sign * int(m.group(3).translate(_SUP)), False
    if not digits:
        return body, sign * len(m.group(5)), False
    if m.group(1) or m.group(2):
        return body, sign * int(digits), False
    if ambiguous_count(body, digits):
        return body + digits, None, True
    if len(m.group(5)) == 1 and monatomic(body, m.group(5)):
        return body, sign * int(digits), False
    return body + digits, sign * len(m.group(5)), False


def label_charge(text):
    """Ladung am Ende einer Beschriftung -> (Text ohne Ladung, Ladung oder None); Regel in `_label_charge`."""
    return _label_charge(text)[:2]


def counter_ion(text):
    """Beschriftung -> SMILES eines bekannten Gegenions („PF6“, „[BArF4]−“, „TfO⁻“) oder None."""
    name = label_charge(text)[0].translate(_SUP)
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    return COUNTER_IONS.get(name.lower())


_TO_SUP = str.maketrans("0123456789+-−", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻")


def _label_text(n):
    t = n.find("t")      # hochgestellter Lauf (face 0x40 ohne 0x20, nicht Formel 0x60) -> Unicode-Hochzahl
    sup = lambda r: (int(r.get("face") or 0) & 0x60) == 0x40 if (r.get("face") or "").isdigit() else False
    return n.get("GenericNickname") or ("".join((s.text or "").translate(_TO_SUP) if sup(s) else (s.text or "")
                                                for s in t.iter("s")) if t is not None else "")


def _prepare(path):
    """CDXML für RDKit vorbereiten -> (XML-Wurzel oder None, Text zum Zeichnen, Text zum Rechnen (je None = Datei
    unverändert), [SMILES der Gegenionen], [nicht aufgelöste Beschriftungen], [Ladung mehrdeutig]). Ladung, die nur im
    Text einer Beschriftung ohne eigene Atome steht („Br−“ ohne Charge), wird als Charge eingetragen (beide Texte). Zum
    Rechnen werden Fragmente, die nur aus der Beschriftung eines bekannten Gegenions bestehen, herausgenommen (die
    Tabelle zählt, nie die Atome darin). Text-Knoten ohne Element und ohne Atome darin zählte RDKit still als CH3 oder als „*“: sie werden genannt
    (Formel und Masse bleiben dann leer)."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return None, None, None, [], [], []
    parent = {c: p for p in root.iter() for c in p}
    ions, unknown, drop, charged, amb = [], [], [], False, []
    for frag in [f for f in root.iter("fragment") if parent.get(f) is not None and parent[f].tag != "n"]:
        nodes = [n for n in frag.findall("n") if n.get("NodeType") != "ExternalConnectionPoint"]
        bonded = {b.get(k) for b in frag.findall("b") for k in ("B", "E")}
        for n in nodes:
            text = _label_text(n)
            inner = n.find("fragment")
            atoms = inner is not None and inner.find("n") is not None
            q = _label_charge(text) if not atoms and n.get("Charge") is None and text else (None, None, False)
            if n.get("NodeType") in LABEL_TYPES and n.get("Element") is None:
                smi = counter_ion(text) if len(nodes) == 1 and n.get("id") not in bonded else None
                if smi:
                    ions.append(smi)
                    drop.append(frag)
                    continue
                if (n.get("NodeType") in ("Unspecified", "GenericNickname") or not atoms) and not q[2]:
                    unknown.append(text.strip() or "?")         # mehrdeutig: nur dieser Hinweis
            elif n.get("NodeType", "Element") != "Element":
                continue
            if q[2]:
                amb.append(text.strip())                         # „SO42-“: nicht raten (Entscheidung 191)
            elif q[1]:
                n.set("Charge", str(q[1]))                       # Abkürzung mit Atomen („NMe3+“): RDKit liest sie
                charged = True
    draw = ET.tostring(root, encoding="unicode") if charged else None
    for frag in drop:
        parent[frag].remove(frag)
    return root, draw, (ET.tostring(root, encoding="unicode") if charged or drop else None), ions, unknown, amb


def drop_label_dummies(mol):
    """ChemDraw-Beschriftung als Fragment („Br2“ mit hinterlegter Struktur): RDKit liest die Atome darin und zusätzlich
    ein ungebundenes Platzhalteratom „*“ (Formel „*Br2“). Nur ungebundene „*“ neben weiteren Atomen entfernen –
    gebundene sind echte Platzhalter (R, Polymer)."""
    from rdkit import Chem
    idx = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 0 and a.GetDegree() == 0]
    if not idx or len(idx) == mol.GetNumAtoms():
        return mol
    rw = Chem.RWMol(mol)
    for i in reversed(idx):
        rw.RemoveAtom(i)
    out = rw.GetMol()
    out.UpdatePropertyCache(strict=False)
    return out


def _load_cdxml(path, *, render=True) -> dict:
    """-> dict(svg, mw, formula, n_fragments, warnings, charges, parts, labels). parts = [(Formel ohne Ladung, Ladung)]
    je Molekül (gleiche einmal; leer, wenn die Formel fehlt), labels = nicht aufgelöste Beschriftungen."""
    Chem, Descriptors, Draw, rdMolDescriptors, rdMolDraw2D = _rdkit()
    path = Path(path)
    warnings = []
    root, draw_text, text, ions, unknown, amb = _prepare(path)

    def read(sanitize):
        got = Chem.MolsFromCDXML(text, sanitize=sanitize, removeHs=False) if text is not None else \
            Chem.MolsFromCDXMLFile(str(path), sanitize=sanitize, removeHs=False)
        return [drop_label_dummies(m) for m in got if m]
    mols, raw = read(True), read(False)
    sanitized = True
    # RDKit lässt nicht interpretierbare Fragmente weg (auch ungültige Bindungen) -> Masse sonst still zu klein
    if len(mols) < max(len(raw), _xml_fragments(root)):
        mols = raw
        sanitized = False
        if mols:
            warnings.append(T("cdxml_unsanitized"))
    mols += [Chem.MolFromSmiles(s) for s in ions]                # Gegenionen aus der Beschriftung (Tabelle)
    if not mols:
        raise RuntimeError(T("cdxml_empty", name=path.name))

    mol = mols[0]
    for m in mols[1:]:
        mol = Chem.CombineMols(mol, m)
    if len(mols) > 1:
        warnings.append(T("cdxml_fragments", n=len(mols)))

    dummies = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
    if unknown:
        warnings.append(T("cdxml_label_unknown", names=", ".join(dict.fromkeys(unknown))))
    elif dummies:
        warnings.append(T("cdxml_dummies", n=len(dummies)))
    if amb:
        warnings.append(T("cdxml_charge_ambiguous", names=", ".join(dict.fromkeys(amb))))

    mw = formula = None
    parts = []
    try:
        if sanitized and not dummies and not unknown and not amb:      # Masse/Formel wären zu klein oder falsch -> lieber keine
            mw = mol_weight(mol)
            formula = rdMolDescriptors.CalcMolFormula(mol, True, True)   # Isotope: D statt [2H]
            parts = list(dict.fromkeys((re.sub(r"[+-]\d*$", "", rdMolDescriptors.CalcMolFormula(m, True, True)),
                                        Chem.GetFormalCharge(m)) for m in mols))
    except Exception as e:  # pragma: no cover
        warnings.append(str(e))

    properties = {"mw": mw, "formula": formula, "n_fragments": len(mols), "warnings": warnings,
                  "charges": [Chem.GetFormalCharge(m) for m in mols],        # je Molekül (Salz: geladen, Summe 0)
                  "parts": parts, "labels": list(dict.fromkeys(unknown)),
                  "ambiguous": list(dict.fromkeys(amb)),
                  "dummies": len(dummies)}
    # Properties depend on the molecular graph, not on drawable 2D coordinates.
    # RDKit can calculate a valid molecule yet reject its preview (e.g. coincident
    # coordinates: "Cannot normalize a zero length vector"). The embedded editor
    # already supplies the preview, so such a failure must not discard its fields.
    if not render:
        return properties

    # Zeichnen: Koordinaten aus der CDXML behalten (auch gezeichnete H), ACS-1996-Stil; aus der Datei wie gezeichnet
    # (Gegenionen als Beschriftung bleiben Beschriftung)
    dm = mol
    if text is not None:
        got = Chem.MolsFromCDXML(draw_text, sanitize=sanitized, removeHs=False) if draw_text is not None else \
            Chem.MolsFromCDXMLFile(str(path), sanitize=sanitized, removeHs=False)
        drawn = [drop_label_dummies(m) for m in got if m]
        dm = drawn[0] if drawn else mol
        for m in drawn[1:]:
            dm = Chem.CombineMols(dm, m)
    # Feste, großzügige Zeichenfläche (statt "flexicanvas"); Maßstab wie im ACS-1996-Stil
    # (Bindungslänge 14,4 pt), damit Linienstärke und Schrift zur Bindungslänge passen.
    # Der Rand wird beim Einlesen auf den tatsächlichen Inhalt zugeschnitten.
    bl = Draw.MeanBondLength(dm) or 1.0
    pos = dm.GetConformer().GetPositions() if dm.GetNumConformers() else None
    px_bl = 14.4
    if pos is not None and len(pos):
        w = int((pos[:, 0].max() - pos[:, 0].min()) / bl * px_bl + 10 * px_bl)
        h = int((pos[:, 1].max() - pos[:, 1].min()) / bl * px_bl + 10 * px_bl)
    else:
        w = h = int(14 * px_bl)
    d = rdMolDraw2D.MolDraw2DSVG(max(w, 100), max(h, 100))
    opts = d.drawOptions()
    Draw.SetACS1996Mode(opts, bl)
    opts.clearBackground = False
    opts.prepareMolsBeforeDrawing = sanitized
    d.DrawMolecule(dm)
    d.FinishDrawing()
    return {"svg": d.GetDrawingText(), **properties}
