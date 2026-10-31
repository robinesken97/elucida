"""elucida/tabs/synthesis.py - Synthese für die SI: „Synthesis of Name“, Reaktionsschema (ChemDraw), Vorschrift, Mengenprüfung.

Schema: CDXML im Projekt; gezeigt wird die gleichnamige ChemDraw-Exportdatei (SVG/PDF/PNG, unverändert), sonst die
eigene Zeichnung aus den CDXML-Koordinaten (formats/cdxml.py). Exporte, die älter als die CDXML sind, gelten als
veraltet (IMG.is_fresh). Liegt eine gleichnamige .cdx daneben, wird das Schema in Word als **bearbeitbares
ChemDraw-Objekt** eingebettet (formats/ole.py); Vorschau dann die gleichnamige .emf aus ChemDraw (Vektor), sonst ein
PNG des Bildes. ChemDraw liest im Objekt nur CDX, keine CDXML (in Word geprüft).
Mengen: Klammern im SI-Format „S1 (1.03 g, 5.00 mmol, 1.0 eq.)“, „n-BuLi (0.44 mL, 2.5 M, 1.10 mmol, 1.1 eq.)“,
„S2 (525 mg, 4.95 mmol, 99%)“. Geprüft wird mit der Rundung der Angaben (1.03 g = 1.025–1.035 g), sonst gäbe es
Falschalarme: m/M ↔ n, V·c ↔ n, V·ρ/M ↔ n, n/n_ref ↔ eq., n_Produkt/n_ref ↔ Ausbeute.
"""
from __future__ import annotations

import html as _h
import math
import re
from pathlib import Path

from elucida.app.i18n import T

# Massen (g), Volumen (mL), Stoffmengen (mmol): Umrechnungsfaktoren
MASS = {"kg": 1000.0, "g": 1.0, "mg": 1e-3, "µg": 1e-6, "μg": 1e-6, "ug": 1e-6}
VOL = {"L": 1000.0, "mL": 1.0, "µL": 1e-3, "μL": 1e-3, "uL": 1e-3}
AMOUNT = {"mol": 1000.0, "mmol": 1.0, "µmol": 1e-3, "μmol": 1e-3, "umol": 1e-3}
CONC = {"M": 1.0, "mM": 1e-3, "mol/L": 1.0, "mol L-1": 1.0}
_BOLD = 700
TOL = 0.005            # zusätzlicher Spielraum (relativ) über die Rundung hinaus: Atommassen, gerundete Molmassen


def formula_mw(formula):
    """Molmasse aus einer Summenformel (mittlere Atommassen wie in der Elementaranalyse, Isotope wie [13C] mit ihrer
    Masse)."""
    from elucida.si import lines as SI
    from elucida.tabs.ir_ea import mono_mass, parse_formula
    counts = parse_formula(formula)
    missing = [el for el in counts if el not in SI.AVG and not el.startswith("[")]
    if missing:
        raise ValueError(T("syn_no_mass", el=", ".join(missing)))
    return sum((SI.AVG[el] if el in SI.AVG else mono_mass(el)) * k for el, k in counts.items())


def molar_mass(text):
    """Feld „M“ der Tabelle: Zahl (g/mol) oder Summenformel -> float oder None."""
    t = str(text or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        v = float(t)
        return v if math.isfinite(v) and v > 0 else None
    except ValueError:
        try:
            return formula_mw(re.sub(r"[·•]+(?=[+\-−]*\d*$)", "", t))   # Radikalpunkt am Ende; Hydrat-Punkt bleibt
        except ValueError:
            return None


# ---------------------------------------------------------------------------- Zahlen mit Rundung
def interval(num_text, factor=1.0):
    """„1.05“ -> (1.045, 1.055)·factor: die Angabe steht für alles, was so gerundet wird."""
    s = num_text.replace(",", ".").strip()
    v = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    h = 0.5 * 10 ** (-dec)
    return ((v - h) * factor, (v + h) * factor)


def div(a, b):
    lo, hi = a
    blo, bhi = b
    return (lo / bhi, hi / blo)


def mul(a, b):
    return (a[0] * b[0], a[1] * b[1])


def overlaps(a, b, rel=TOL):
    return a[0] <= b[1] * (1 + rel) and b[0] <= a[1] * (1 + rel)


def mid(a):
    return (a[0] + a[1]) / 2


# ---------------------------------------------------------------------------- Klammern in der Vorschrift
_NUM = r"(\d+(?:[.,]\d+)?)"
_PAREN = re.compile(r"(?P<name>[^\s()]+(?:\s*\{[^}]*\})?)\s*\((?P<body>[^()]*(?:mmol|mol|eq|equiv|%)[^()]*)\)")


def parse_amounts(text):
    """Mengenangaben „Name (1.03 g, 5.00 mmol, 1.0 eq.)“ aus der Vorschrift -> [dict(name, raw, mass, vol, conc,
    mmol, eq, yield, density)] (Intervalle in g, mL, mol/L, mmol, –, %)."""
    out = []
    plain = re.sub(r"<[^>]+>", "", text or "")
    for m in _PAREN.finditer(plain):
        body = m.group("body")
        it = dict(name=m.group("name").strip(".,;:"), raw=m.group(0), pos=m.start(), mass=None, vol=None, conc=None,
                  mmol=None, eq=None, yld=None, density=None)
        for part in (p.strip() for p in re.split(r"(?<!\d),|,(?!\d)", body)):   # „1,03 g“: Dezimalkomma bleibt
            if mm := re.fullmatch(_NUM + r"\s*(kg|mg|µg|μg|ug|g)", part):
                it["mass"] = interval(mm.group(1), MASS[mm.group(2)])
            elif mm := re.fullmatch(_NUM + r"\s*(mL|µL|μL|uL|L)", part):
                it["vol"] = interval(mm.group(1), VOL[mm.group(2)])
            elif mm := re.fullmatch(_NUM + r"\s*(mmol|µmol|μmol|umol|mol)", part):
                it["mmol"] = interval(mm.group(1), AMOUNT[mm.group(2)])
            elif mm := re.fullmatch(_NUM + r"\s*(M|mM)(?:\s+in\s+.+)?", part):
                it["conc"] = interval(mm.group(1), CONC[mm.group(2)])
            elif mm := re.fullmatch(_NUM + r"\s*(?:eq\.?|equiv\.?|equivalents?)", part):
                it["eq"] = interval(mm.group(1))
            elif mm := re.fullmatch(_NUM + r"\s*%(?:\s*yield)?", part):
                it["yld"] = interval(mm.group(1))
            elif mm := re.fullmatch(r"(?:d|ρ)\s*=\s*" + _NUM + r"\s*(?:g\s*/\s*mL|g\s*mL-1|g\s*cm-3)?", part):
                it["density"] = interval(mm.group(1))
        out.append(it)
    return out


def check_amounts(items, table=None):
    """Prüfung -> [(Stufe 'ok'|'warn'|'info', Text)]. table = {Name: dict(M, density, conc)} (Zahlen oder None).
    Bezug für eq. und Ausbeute: der erste Eintrag mit 1.0 eq. (sonst der erste mit mmol)."""
    table = table or {}
    res = []
    ref = next((it for it in items if it["eq"] and abs(mid(it["eq"]) - 1.0) < 1e-9 and it["mmol"]), None) or \
        next((it for it in items if it["mmol"]), None)
    for it in items:
        name = it["name"]
        info = table.get(name) or table.get(name.strip("*")) or {}
        M = info.get("M")
        n = it["mmol"]
        dens = it["density"] or (interval(f"{info['density']}") if info.get("density") else None)
        conc = it["conc"] or (interval(f"{info['conc']}") if info.get("conc") else None)
        if it["mass"] and n:
            implied = div(it["mass"], n)                          # g/mmol = kg/mol -> ×1000 = g/mol
            implied = (implied[0] * 1000, implied[1] * 1000)
            if M:
                ok = overlaps(implied, (M, M))
                res.append(("ok" if ok else "warn", T("syn_chk_mass_ok" if ok else "syn_chk_mass_bad", name=name,
                                                       M=f"{M:.2f}", n=f"{it['mass'][0] * 1000 / M:.3f}–"
                                                       f"{it['mass'][1] * 1000 / M:.3f}")))
            else:
                res.append(("info", T("syn_chk_mass_implied", name=name, lo=f"{implied[0]:.1f}",
                                      hi=f"{implied[1]:.1f}")))
        if it["vol"] and n:
            if conc:
                calc = mul(it["vol"], conc)                         # mL · mol/L = mmol
                ok = overlaps(calc, n)
                res.append(("ok" if ok else "warn", T("syn_chk_conc_ok" if ok else "syn_chk_conc_bad", name=name,
                                                       n=f"{mid(calc):.3f}")))
            elif dens and M:
                calc = (it["vol"][0] * dens[0] / M * 1000, it["vol"][1] * dens[1] / M * 1000)
                ok = overlaps(calc, n)
                res.append(("ok" if ok else "warn", T("syn_chk_dens_ok" if ok else "syn_chk_dens_bad", name=name,
                                                       n=f"{mid(calc):.3f}")))
            else:
                res.append(("info", T("syn_chk_vol_unknown", name=name)))
        if ref is not None and it is not ref and n and it["eq"]:
            r = div(n, ref["mmol"])
            ok = overlaps(r, it["eq"], rel=0.01)
            res.append(("ok" if ok else "warn", T("syn_chk_eq_ok" if ok else "syn_chk_eq_bad", name=name,
                                                   eq=f"{mid(r):.2f}", ref=ref["name"])))
        if ref is not None and it is not ref and n and it["yld"]:
            y = (n[0] / ref["mmol"][1] * 100, n[1] / ref["mmol"][0] * 100)
            ok = overlaps(y, it["yld"], rel=0.01)
            res.append(("ok" if ok else "warn", T("syn_chk_yield_ok" if ok else "syn_chk_yield_bad", name=name,
                                                   y=f"{mid(y):.1f}", ref=ref["name"])))
        if not n and (it["eq"] or it["yld"]):
            res.append(("info", T("syn_chk_no_mmol", name=name)))
    return res


# ---------------------------------------------------------------------------- Reagenzientabelle
def fmt_sig(v, sig=3):
    """Zahl mit sig gültigen Stellen, ohne wissenschaftliche Schreibweise (1.05, 760, 0.440)."""
    if v == 0:
        return "0"
    import math
    d = max(0, sig - 1 - int(math.floor(math.log10(abs(v)))))
    return f"{v:.{d}f}"


def sig_digits(text):
    """Gültige Stellen einer Eingabe („1050“ -> 3, „0.440“ -> 3, „1.05“ -> 3), mindestens 2."""
    t = str(text).replace(",", ".").lstrip("0.").replace(".", "")
    t = t.rstrip("0") if "." not in str(text).replace(",", ".") else t
    return max(2, min(5, len(t)))


# Einheiten je Spalte (Faktor zur Spalteneinheit mg, mL, M, g/mL, mmol): „1.03 g“ in der Spalte m [mg] = 1030
UNITS = {"m_mg": {u: f * 1000 for u, f in MASS.items()}, "V_mL": VOL, "c_M": CONC,
         "rho": {"g/mL": 1.0, "g/cm3": 1.0, "g/cm³": 1.0, "kg/L": 1.0}, "n_mmol": AMOUNT}
_NUM_UNIT = re.compile(r"^\s*([-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")


def split_unit(x):
    """„1,03 g“ -> („1.03“, „g“), „150“ -> („150“, „“), kein Zahlenwert -> None (µ einheitlich, „uL“ = „µL“)."""
    m = _NUM_UNIT.match(str(x or ""))
    if not m:
        return None
    u = m.group(2).replace("μ", "µ")
    return m.group(1).replace(",", "."), ("µ" + u[1:] if u in ("ug", "uL", "umol") else u)


def cell_num(x, units=None):
    """Zahlenfeld der Tabelle -> float in der Spalteneinheit oder None (leer, kein Zahlenwert, unbekannte Einheit).
    units: Einheit -> Faktor (UNITS[Spalte]); ohne units nur reine Zahlen."""
    su = split_unit(x)
    if su is None or (su[1] and su[1] not in (units or {})):
        return None
    v = float(su[0]) * (units[su[1]] if su[1] else 1.0)
    return v if math.isfinite(v) else None


def row_amounts(row, ref_mmol=None):
    """Zeile der Tabelle (M, m_mg, V_mL, c_M, rho, n_mmol, role) -> dict(M, mmol, eq, yld, given) (Zahlen oder None);
    Zellen dürfen eine Einheit tragen („1.03 g“). Eingetragenes n zählt, wenn sich n nicht aus m bzw. V berechnen lässt (given = True; z. B. Harz/Polymer ohne M)."""
    M = molar_mass(row.get("M"))
    m, V, c, rho, n_in = (cell_num(row.get(k), UNITS[k]) for k in ("m_mg", "V_mL", "c_M", "rho", "n_mmol"))
    n = None
    if m is not None and M:
        n = m / M
    elif V is not None and c is not None:
        n = V * c
    elif V is not None and rho is not None and M:
        n = V * rho * 1000 / M
    given = n is None and n_in is not None
    out = dict(M=M, mmol=n_in if given else n, eq=None, yld=None, given=given)
    n = out["mmol"]
    if n is not None and ref_mmol:
        if row.get("role") == "product":
            out["yld"] = n / ref_mmol * 100
        else:
            out["eq"] = n / ref_mmol
    return out


def amount_text(row, calc):
    """Klammer im SI-Format: „(1.03 g, 5.00 mmol, 1.0 eq.)“, Lösung „(0.44 mL, 2.5 M, 1.10 mmol, 1.1 eq.)“,
    Produkt „(707 mg, 4.53 mmol, 99%)“."""
    parts = []
    ok = lambda k: split_unit(row.get(k)) if cell_num(row.get(k), UNITS[k]) is not None else None  # noqa: E731
    m, V, c = ok("m_mg"), ok("V_mL"), ok("c_M")
    if m:                                       # Stellen und Einheit wie eingegeben; ohne Einheit ab 1000 mg in g
        mv = float(m[0])
        parts.append(f"{m[0]} {m[1]}" if m[1] else f"{fmt_sig(mv / 1000, sig_digits(m[0]))} g" if mv >= 1000
                     else f"{m[0]} mg")
    if V:
        vv = float(V[0])
        parts.append(f"{V[0]} {V[1]}" if V[1] else f"{fmt_sig(vv * 1000, sig_digits(V[0]))} µL" if vv < 0.1
                     else f"{V[0]} mL")
        if c:
            parts.append(f"{c[0]} {c[1] or 'M'}")
    n_in = ok("n_mmol") if calc.get("given") else None
    if n_in:                                    # eingetragenes n wie eingegeben („1.23450 µmol“)
        parts.append(f"{n_in[0]} {n_in[1] or 'mmol'}")
    elif calc.get("mmol") is not None:
        parts.append(f"{fmt_sig(calc['mmol'])} mmol")
    if calc.get("yld") is not None:
        parts.append(f"{calc['yld']:.0f}%")
    elif calc.get("eq") is not None:
        e = f"{calc['eq']:.2f}"                             # 1.05 eq., aber 1.1/1.0 eq. (Nutzerwunsch P7 R1)
        parts.append(f"{e[:-1] if e.endswith('0') else e} eq.")
    return f"({', '.join(parts)})" if parts else ""


# ---------------------------------------------------------------------------- Schema
def scheme_files(cdxml):
    """Zur CDXML gehörende ChemDraw-Dateien: Bild (SVG/PDF/PNG), CDX (bearbeitbar), EMF (Vektor-Vorschau)."""
    from elucida.core import images as IMG
    p = Path(cdxml)
    sib = {c.suffix.lower(): c for c in p.parent.glob(p.stem + ".*") if c.stem == p.stem}
    cdxml_ = p.suffix.lower() == ".cdxml"
    fresh = lambda f: f if f is not None and (not cdxml_ or IMG.is_fresh(f, p)) else None   # noqa: E731
    return dict(picture=IMG.find_sibling_drawing(p) if cdxml_ else p,       # veraltete Exporte nicht verwenden
                cdx=fresh(sib.get(".cdx")), emf=fresh(sib.get(".emf")))


def scheme_molecules(cdxml):
    """Moleküle des Schemas (RDKit) -> [(Formel, Molmasse, Rolle)] für die Tabelle; Rolle aus dem Reaktionsschritt
    der CDXML (Edukt -> "reactant", Produkt -> "product", sonst "")."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    out = []
    try:
        mols = Chem.MolsFromCDXMLFile(str(cdxml), sanitize=True, removeHs=False)
    except Exception:
        return out
    from elucida.core.chem import drop_label_dummies
    for m in mols or []:
        if m is not None:
            m = drop_label_dummies(m)                     # „*Br2“: Beschriftung mit hinterlegter Struktur
            role = ("product" if m.HasProp("CDX_PRODUCT_ID") else
                    "reactant" if m.HasProp("CDX_REAGENT_ID") else "")
            out.append((rdMolDescriptors.CalcMolFormula(m, True, True), float(Descriptors.MolWt(m)), role))  # D, [13C]
    return out


def grid_row(comp):
    """Verbindung der ChemDraw-Reagenzientabelle (CDX.stoich_grid) -> (Zeile, Hinweis oder ""); Rolle "ref"
    (limitierend), "reactant" (übrige Edukte/Reagenzien) oder "product". Eingegebene Masse -> m, sonst mit Molarität/
    Dichte/eingegebenem Volumen -> V (+ c bzw. ρ), sonst m; Produkt: m nur aus der Produktmasse (erwartete fällt weg).
    Eingegebene Werte wie in ChemDraw, berechnete mit 3 gültigen Stellen; Einheit in der Zelle („2.15 g“, „341 mg“, „1.60 mL“)."""
    from elucida.formats import cdxml as CDX
    v = comp["values"]
    val = lambda t: v.get(t, (0.0, False))                                      # noqa: E731

    def num(x, edited):
        return f"{x:.10g}" if edited else fmt_sig(x)

    def mass(t):
        g, ed = val(t)
        return (f"{num(g, ed)} g" if g >= 1 else f"{num(g * 1000, ed)} mg") if g > 0 else ""

    mw = val(CDX.GRID_MW)[0]
    M = comp["formula"] if molar_mass(comp["formula"]) else (num(mw, True) if mw else "")
    row = dict(name="", M=M, m_mg="", V_mL="", c_M="", rho="", role="reactant")
    (c, c_ed), (rho, rho_ed) = val(CDX.GRID_MOLARITY), val(CDX.GRID_DENSITY)
    if not comp["reactant"]:
        row.update(role="product", m_mg=mass(CDX.GRID_PRODUCT_MASS))
    else:
        if val(CDX.GRID_LIMITING)[0] == 1:
            row["role"] = "ref"
        row.update(c_M=num(c, c_ed) if c > 0 else "", rho=num(rho, rho_ed) if rho > 0 else "")
        V, v_ed = val(CDX.GRID_VOLUME)
        if not val(CDX.GRID_SAMPLE_MASS)[1] and V > 0 and (c > 0 or rho > 0 or v_ed):
            row["V_mL"] = f"{num(V, v_ed)} mL" if V >= 0.1 else f"{num(V * 1000, v_ed)} µL"
        else:
            row["m_mg"] = mass(CDX.GRID_SAMPLE_MASS) or mass(CDX.GRID_REACTANT_MASS)
    impure = [k for k, t in (("%Weight", CDX.GRID_WEIGHT), ("Purity", CDX.GRID_PURITY))
              if t in v and abs(val(t)[0] - 1) > 1e-6]
    return row, (T("syn_grid_purity", f=comp["formula"], what=" / ".join(impure)) if impure else "")


def scheme_drawing(cdxml):
    """Schema ohne ChemDraw-Export: eigene Zeichnung aus den CDXML-Koordinaten (formats/cdxml.py), Asset wie
    IMG.load_structure (PDF-Vektor + Vorschau); Hinweise auf nicht gezeichnete Objekte als Warnung."""
    from elucida.formats import cdxml as CDX
    from elucida.core import images as IMG
    svg, notes = CDX.render_svg(cdxml)
    info = {"mw": None, "formula": None, "warnings": [T("syn_scheme_notdrawn", what=", ".join(notes))] if notes else []}
    res = IMG._render_doc(IMG._vector_doc(cdxml, svg), 2400, info)
    res["drawing_from"] = "cdxml"
    return res


def emf_size_cm(path):
    """Größe einer EMF aus dem Header (rclFrame, 0.01 mm) -> (Breite, Höhe) in cm."""
    import struct
    b = Path(path).read_bytes()[:40]
    left, top, right, bottom = struct.unpack("<iiii", b[24:40])
    return (right - left) / 1000.0, (bottom - top) / 1000.0


# ---------------------------------------------------------------------------- Rich Text (QTextDocument) -> SI-HTML
def _weight(w):
    return int(getattr(w, "value", w))


def doc_to_html(doc):
    """QTextDocument -> kleines HTML (b, i, sub, sup; Absätze als <br>) wie die übrigen SI-Zeilen."""
    from PySide6.QtGui import QFont, QTextCharFormat
    global _BOLD
    _BOLD = _weight(QFont.Weight.Bold)
    paras = []
    block = doc.begin()
    while block.isValid():
        parts = []
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid():
                f = frag.charFormat()
                t = _h.escape(frag.text())
                if f.verticalAlignment() == QTextCharFormat.AlignSubScript:
                    t = f"<sub>{t}</sub>"
                elif f.verticalAlignment() == QTextCharFormat.AlignSuperScript:
                    t = f"<sup>{t}</sup>"
                if f.fontItalic():
                    t = f"<i>{t}</i>"
                if f.fontWeight() >= _BOLD:
                    t = f"<b>{t}</b>"
                parts.append(t)
            it += 1
        paras.append("".join(parts))
        block = block.next()
    while paras and not paras[-1].strip():
        paras.pop()
    return "<br>".join(paras)


# ---------------------------------------------------------------------------- Tab
from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QFont, QImage, QPixmap, QTextCharFormat  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFrame, QGroupBox,  # noqa: E402
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QSplitter, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QTextEdit, QVBoxLayout, QWidget)

from elucida.app import project as PRJ  # noqa: E402
from elucida.app.style import HINT_CSS, WARN_CSS  # noqa: E402

ROLES = ("ref", "reagent", "product", "other")
COLS = ("name", "M", "m_mg", "V_mL", "c_M", "rho", "role")          # bearbeitbare Spalten, danach n und eq./%


class SynthTab(QWidget):
    STATE_KEY = "syn"
    DEFAULT_STATE = dict(name="", scheme=None, proc="", reagents=[], gp="")

    def __init__(self, main, state):
        super().__init__()
        self.main, self.st = main, state
        for k, v in self.DEFAULT_STATE.items():
            self.st.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)
        self._loading = False
        self.timer = QTimer(self, singleShot=True, interval=500)
        self.timer.timeout.connect(self.proc_changed)
        left = QWidget()
        self.lv = QVBoxLayout(left)
        self.build_controls()
        self.lv.addStretch(1)
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ls.setMinimumWidth(max(520, left.minimumSizeHint().width() + 24))
        from elucida.tabs.base import EmptyGuide
        prev = QWidget()
        rv = QVBoxLayout(prev)
        rv.setContentsMargins(0, 0, 0, 0)
        # Schema auf weißem Grund wie in Word (im dunklen Modus sonst kaum lesbar), nur wenn eines geladen ist;
        # der Text darunter folgt dem Erscheinungsbild
        self.lbl_prev = QLabel("", alignment=Qt.AlignCenter)
        self.lbl_prev.setStyleSheet("background: #ffffff; padding: 12px;")
        self.lbl_prev.hide()
        rv.addWidget(self.lbl_prev)
        self.txt_prev = QTextBrowser()
        rv.addWidget(self.txt_prev, 1)
        right = QWidget()
        self.preview_stack = QStackedWidget()             # 0 = Anleitung (leerer Tab, wie die anderen Tabs), 1 = Vorschau
        self.preview_stack.addWidget(EmptyGuide("syn", (T("syn_scheme_pick"), self.pick_scheme)))
        self.preview_stack.addWidget(prev)
        QVBoxLayout(right).addWidget(self.preview_stack)
        from elucida.tabs.base import footer
        split = QSplitter(Qt.Horizontal)
        split.addWidget(footer(self, ls))
        split.addWidget(right)
        split.setSizes([620, 800])
        from elucida.tabs.base import fit_footer_column
        fit_footer_column(self, split, 520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self.sync_widgets()

    # -- Bedienelemente -------------------------------------------------------------------
    def build_controls(self):
        g = QGroupBox(T("syn_title_grp"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel("Synthesis of"))
        self.ed_name = QLineEdit()
        self.ed_name.setToolTip(T("syn_name_tip"))
        self.ed_name.editingFinished.connect(self.name_changed)
        row.addWidget(self.ed_name, 1)
        v.addLayout(row)
        hint = QLabel(T("syn_output_hint"))                  # wohin der Text geht (Tab ohne eigenen Export-Knopf)
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.lv.addWidget(g)

        g = QGroupBox(T("syn_scheme"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        b = QPushButton(T("syn_scheme_pick"))
        b.clicked.connect(self.pick_scheme)
        row.addWidget(b)
        b = QPushButton(T("chemdraw_edit"))                # leere Vorlage liegt schon bereit
        b.setToolTip(T("chemdraw_edit_scheme_tip"))
        b.clicked.connect(lambda: self.main.edit_in_chemdraw("scheme"))
        row.addWidget(b)
        b = QPushButton(T("remove"))
        b.clicked.connect(self.remove_scheme)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lbl_scheme = QLabel("", wordWrap=True)
        v.addWidget(self.lbl_scheme)
        hint = QLabel(T("syn_scheme_hint_short"), wordWrap=True)
        hint.setToolTip(T("syn_scheme_hint"))
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.lv.addWidget(g)

        g = QGroupBox(T("syn_proc"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn, tip in (("B", self.fmt_bold, T("syn_bold")), ("I", self.fmt_italic, T("syn_italic")),
                             ("X₂", lambda: self.fmt_valign(QTextCharFormat.AlignSubScript), T("syn_sub")),
                             ("X²", lambda: self.fmt_valign(QTextCharFormat.AlignSuperScript), T("syn_sup"))):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.setFixedWidth(40)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        self.btn_gp = QPushButton("GP")                     # allgemeine Vorschrift des Projekts wählen + Verweis
        self.btn_gp.setToolTip(T("syn_gp_tip"))
        self.btn_gp.setMenu(QMenu(self.btn_gp))
        self.btn_gp.menu().aboutToShow.connect(self.fill_gp_menu)
        row.addWidget(self.btn_gp)
        v.addLayout(row)
        self.ed_proc = QTextEdit()
        self.ed_proc.setAcceptRichText(True)
        self.ed_proc.setMinimumHeight(170)
        self.ed_proc.setPlaceholderText(T("syn_proc_ph"))
        self.ed_proc.textChanged.connect(lambda: None if self._loading else self.timer.start())
        v.addWidget(self.ed_proc)
        self.lbl_check = QLabel("", wordWrap=True)
        self.lbl_check.setTextFormat(Qt.RichText)
        v.addWidget(self.lbl_check)
        self.lv.addWidget(g)

        g = QGroupBox(T("syn_reagents"))
        v = QVBoxLayout(g)
        self.tbl = QTableWidget(0, len(COLS) + 2)
        self.tbl.setHorizontalHeaderLabels([T("syn_col_name"), T("syn_col_M"), "m [mg]", "V [mL]", "c [M]",
                                            "ρ [g/mL]", T("syn_col_role"), "n [mmol]", T("syn_col_eq")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setMinimumHeight(170)
        self.tbl.setToolTip(T("syn_table_tip"))
        self.tbl.itemChanged.connect(self.cell_changed)
        v.addWidget(self.tbl)
        row = QHBoxLayout()
        for txt, fn, tip in ((T("syn_row_add"), self.add_row, ""), (T("remove"), self.remove_row, ""),
                             (T("syn_from_scheme"), self.rows_from_scheme, T("syn_from_scheme_tip")),
                             (T("syn_insert"), self.insert_amounts, T("syn_insert_tip"))):
            b = QPushButton(txt)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(fn)
            if fn == self.rows_from_scheme:
                self.btn_from_scheme = b                  # nur mit Schema aktiv (update_scheme_info)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

    # -- Zustand --------------------------------------------------------------------------
    def compound_name(self):
        comp = getattr(self.main, "compound", None) or {}
        pdir = getattr(self.main, "project_dir", None)
        return self.st.get("name") or comp.get("name") or (Path(pdir).name if pdir else "")

    def has_content(self):
        return bool(self.st.get("scheme") or (self.st.get("proc") or "").strip())

    def sync_widgets(self):
        self._loading = True
        self.ed_name.setText(self.st.get("name") or "")
        self.ed_name.setPlaceholderText((getattr(self.main, "compound", None) or {}).get("name") or T("syn_name_ph"))
        if doc_html(self.ed_proc) != (self.st.get("proc") or ""):
            self.ed_proc.setHtml(simple_to_qt(self.st.get("proc") or ""))
        self.fill_table()
        self._loading = False
        self.btn_gp.setText(f"GP {self.st['gp']}" if self.st.get("gp") else "GP")
        self.update_scheme_info()
        self.update_check()
        self.update_preview()

    def fill_table(self):
        rows = self.st["reagents"]
        self.tbl.blockSignals(True)
        self.tbl.setRowCount(0)                       # alte Auswahlfelder (Rolle) sonst an falscher Stelle
        self.tbl.setRowCount(len(rows))
        ref = self.ref_mmol()
        for r, row in enumerate(rows):
            for c, k in enumerate(COLS):
                if k == "role":
                    cmb = QComboBox()
                    for ro in ROLES:
                        cmb.addItem(T("syn_role_" + ro), ro)
                    cmb.setCurrentIndex(max(0, cmb.findData(row.get("role") or "reagent")))
                    cmb.currentIndexChanged.connect(lambda _=0, r_=r, w=cmb: self.role_changed(r_, w.currentData()))
                    self.tbl.setCellWidget(r, c, cmb)
                    continue
                self.tbl.setItem(r, c, QTableWidgetItem(str(row.get(k) or "")))
            calc = row_amounts(row, ref)
            # n eintragbar (zählt nur ohne m/V); berechnetes n grau
            n = (str(row.get("n_mmol")) if calc["given"] else f"{calc['mmol']:.3f}" if calc["mmol"] is not None
                 else str(row.get("n_mmol") or "–"))
            e = f"{calc['yld']:.0f}%" if calc["yld"] is not None else f"{calc['eq']:.2f}" if calc["eq"] is not None \
                else ("1.00" if row.get("role") == "ref" and calc["mmol"] else "–")
            for c, val in ((len(COLS), n), (len(COLS) + 1, e)):
                it = QTableWidgetItem(val)
                if c > len(COLS):
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                elif calc["mmol"] is not None and not calc["given"]:
                    it.setForeground(Qt.gray)
                self.tbl.setItem(r, c, it)
            M = calc["M"]
            if row.get("M") and M is None:
                self.tbl.item(r, 1).setToolTip(T("syn_M_bad"))
                self.tbl.item(r, 1).setForeground(Qt.red)
            elif M:
                self.tbl.item(r, 1).setToolTip(f"M = {M:.2f} g/mol")
        self.tbl.blockSignals(False)

    def ref_mmol(self):
        for row in self.st["reagents"]:
            if row.get("role") == "ref":
                return row_amounts(row)["mmol"]
        return None

    def table_info(self):
        """Name -> dict(M, density, conc) für die Prüfung der Vorschrift."""
        out = {}
        for row in self.st["reagents"]:
            name = str(row.get("name") or "").strip()
            if name:
                out[name] = dict(M=molar_mass(row.get("M")), density=cell_num(row.get("rho"), UNITS["rho"]),
                                 conc=cell_num(row.get("c_M"), UNITS["c_M"]))
                out[re.sub(r"\s+", "", name)] = out[name]
        return out

    # -- Aktionen -------------------------------------------------------------------------
    def name_changed(self):
        if not self._loading:
            self.st["name"] = self.ed_name.text().strip()
            self.update_preview()
            self.main.push_undo()

    def pick_scheme(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("syn_scheme_pick"), self.main.settings.value("last_dir", ""),
                                           f"ChemDraw (*.cdxml *.svg *.pdf *.png);;{T('flt_all')}")
        if p:
            self.set_scheme(p)

    def set_scheme(self, p):
        """CDXML (oder Bild) ins Projekt; gleichnamige ChemDraw-Dateien (SVG/PDF/PNG/CDX/EMF) kommen mit."""
        src = Path(p)
        newp = Path(self.main.import_file(str(src), PRJ.STRUCTURES))
        for sib in src.parent.glob(src.stem + ".*"):                # CDX und EMF zusätzlich zu den Bildern
            if sib.stem == src.stem and sib.suffix.lower() in (".cdx", ".emf"):
                tgt = newp.with_suffix(sib.suffix.lower())
                if not tgt.exists():
                    import shutil
                    shutil.copy2(sib, tgt)
        self.st["scheme"] = str(newp)
        self.main.extra_cache.pop(("synscheme", str(newp)), None)
        self.sync_widgets()
        self.main.push_undo()

    def remove_scheme(self):
        self.st["scheme"] = None
        self.sync_widgets()
        self.main.push_undo()

    def scheme_parts(self):
        p = self.st.get("scheme")
        if not p or not Path(p).exists():
            return None
        return scheme_files(p)

    def update_scheme_info(self):
        sp = self.scheme_parts()
        if getattr(self, "btn_from_scheme", None) is not None:
            self.btn_from_scheme.setEnabled(sp is not None)
            self.btn_from_scheme.setToolTip(T("syn_from_scheme_tip") if sp is not None else T("syn_need_scheme"))
        if sp is None:
            self.lbl_scheme.setText(T("syn_scheme_none"))
            self.lbl_scheme.setStyleSheet(HINT_CSS)
            return
        bits = [T("syn_scheme_pic", f=sp["picture"].name) if sp["picture"] else T("syn_scheme_nopic")]
        if sp["cdx"]:
            bits.append(T("syn_scheme_cdx") + (" " + T("syn_scheme_emf") if sp["emf"] else " " + T("syn_scheme_png")))
        else:
            bits.append(T("syn_scheme_nocdx"))
        warn = list((self.scheme_asset() or {}).get("warnings") or [])
        self.lbl_scheme.setText("\n".join(bits + warn))
        self.lbl_scheme.setStyleSheet(WARN_CSS if warn else "")

    def scheme_asset(self):
        """Schema als Struktur-Asset (PDF-Vektor + Vorschau) aus der ChemDraw-Exportdatei (sonst RDKit)."""
        from elucida.core import images as IMG
        p = self.st.get("scheme")
        if not p or not Path(p).exists():
            return None
        key = ("synscheme", p)
        if key not in self.main.extra_cache:
            try:
                if Path(p).suffix.lower() == ".cdxml" and IMG.find_sibling_drawing(p) is None:
                    self.main.extra_cache[key] = scheme_drawing(p)           # Pfeil und Text wie in ChemDraw
                else:
                    self.main.extra_cache[key] = IMG.load_structure(p)
            except Exception as ex:
                self.main.log_signal.emit(f"{Path(p).name}: {ex}")
                self.main.extra_cache[key] = None
        return self.main.extra_cache[key]

    def fmt_bold(self):
        f = QTextCharFormat()
        bold = _weight(self.ed_proc.fontWeight()) >= _weight(QFont.Weight.Bold)
        f.setFontWeight(QFont.Weight.Normal if bold else QFont.Weight.Bold)
        self.ed_proc.mergeCurrentCharFormat(f)

    def fmt_italic(self):
        f = QTextCharFormat()
        f.setFontItalic(not self.ed_proc.fontItalic())
        self.ed_proc.mergeCurrentCharFormat(f)

    def fmt_valign(self, al):
        f = QTextCharFormat()
        cur = self.ed_proc.currentCharFormat().verticalAlignment()
        f.setVerticalAlignment(QTextCharFormat.AlignNormal if cur == al else al)
        self.ed_proc.mergeCurrentCharFormat(f)

    def proc_changed(self):
        self.st["proc"] = doc_html(self.ed_proc)
        self.update_check()
        self.update_preview()
        self.main.push_undo()

    def update_check(self):
        items = parse_amounts(self.st.get("proc") or "")
        if not items:
            self.lbl_check.setText(f"<span style='color:gray'>{_h.escape(T('syn_check_none'))}</span>")
            return
        icon = {"ok": "✓", "warn": "⚠", "info": "ℹ"}
        col = {"ok": "#2e7d32", "warn": "#d9534f", "info": "gray"}
        res = check_amounts(items, self.table_info())
        self.lbl_check.setText("<br>".join(f"<span style='color:{col[lv]}'>{icon[lv]} {_h.escape(t)}</span>"
                                           for lv, t in res) or T("syn_check_none"))

    def add_row(self):
        role = "ref" if not self.st["reagents"] else "reagent"
        self.st["reagents"].append(dict(name="", M="", m_mg="", V_mL="", c_M="", rho="", role=role))
        self.fill_table()
        self.main.push_undo()

    def remove_row(self):
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()}, reverse=True)
        for r in rows:
            if r < len(self.st["reagents"]):
                del self.st["reagents"][r]
        self.fill_table()
        self.update_check()
        self.main.push_undo()

    def rows_from_scheme(self):
        """Moleküle des Schemas als Zeilen (Summenformel als M); Namen trägst du ein (z. B. S1). Mit ChemDraw-
        Reagenzientabelle in derselben CDXML: Moleküle, Formeln und Mengen von dort (grid_row)."""
        p = self.st.get("scheme")
        if not p or Path(p).suffix.lower() != ".cdxml":
            self.main.error(T("syn_need_cdxml"))
            return
        from elucida.formats import cdxml as CDX
        notes = []
        try:
            grid = CDX.stoich_grid(p)
        except Exception as ex:
            self.main.log_signal.emit(f"{Path(p).name}: {ex}")
            grid = []
        if len({c["grid"] for c in grid}) > 1:
            notes.append(T("syn_grid_many"))
        try:
            texts = CDX.scheme_reagents(p)
        except Exception as ex:
            self.main.log_signal.emit(f"{Path(p).name}: {ex}")
            texts = []
        empty = dict(m_mg="", V_mL="", c_M="", rho="")
        if grid:      # RDKit liest Formeln über dem Pfeil teils mit Platzhalteratom („*Br2“), die Tabelle nicht
            gr = []
            for comp in grid:
                g, note = grid_row(comp)
                gr.append(g)
                notes += [note] if note else []
            gm = [molar_mass(r["M"]) for r in gr]
            txt = [dict(name=n, M=f, role=r, **empty) for n, f, r in texts       # Lösungsmittel u. a. aus Pfeiltexten
                   if not (molar_mass(f) and any(m and abs(m - molar_mass(f)) < 0.01 for m in gm))]
            rows = (sorted((r for r in gr if r["role"] != "product"), key=lambda r: r["role"] != "ref") + txt +
                    [r for r in gr if r["role"] == "product"])
        else:
            mols = scheme_molecules(p)
            # Reihenfolge wie die Vorschrift: Edukte (erstes = Bezug 1.0 eq.), Reagenzien über/unter dem Pfeil, Produkt
            # Mit Reaktionsschritt: Moleküle ohne Rolle (über/unter dem Pfeil) sind Reagenzien, nie der Bezug
            step = any(r for _f, _m, r in mols)
            rows = [dict(name="", M=f, role="reactant" if r == "reactant" or not step else "reagent", **empty)
                    for f, _m, r in sorted(mols, key=lambda x: x[2] != "reactant") if r != "product"]
            rows += [dict(name=n, M=f, role=r, **empty) for n, f, r in texts]
            rows += [dict(name="", M=f, role="product", **empty) for f, _m, r in mols if r == "product"]
        tab = self.st["reagents"]
        prod = lambda role: role == "product"                                   # noqa: E731

        def same(a, b):                    # gleiche Formel oder gleicher Name; Isomere: Produkt trotzdem getrennt
            return prod(a.get("role")) == prod(b.get("role")) and any(
                a.get(k) and str(a.get(k)) == str(b.get(k)) for k in ("M", "name"))
        taken = []                     # je ChemDraw-Komponente eine Zeile (Isomere gleicher Formel getrennt)
        for new in rows:
            old = next((r for r in tab if same(r, new) and not any(r is t for t in taken)), None)
            has_ref = any(r.get("role") == "ref" for r in tab)
            if old is not None:
                # vorhanden: Mengen nur, wenn die Zeile noch keine hat (sonst widersprüchliche Dosierung m vs. V·c)
                if not any(str(old.get(k) or "").strip() for k in ("m_mg", "V_mL", "n_mmol")):
                    for k in empty:
                        if new[k] and not str(old.get(k) or "").strip():
                            old[k] = new[k]
                if new["role"] == "ref" and not has_ref:       # limitierend in ChemDraw, noch kein Bezug
                    old["role"] = "ref"
            else:
                new["role"] = ("ref" if new["role"] in ("ref", "reactant") and not has_ref
                               else "reagent" if new["role"] in ("ref", "reactant") else new["role"])
                tab.append(new)
                old = new
            if grid:
                taken.append(old)
        if notes:
            self.main.log_signal.emit("\n".join(notes))
            self.main.statusBar().showMessage("\n".join(notes), 8000)
        self.fill_table()
        self.main.push_undo()

    def cell_changed(self, item):
        r, c = item.row(), item.column()
        if self._loading or c > len(COLS) or r >= len(self.st["reagents"]):
            return
        self.st["reagents"][r][COLS[c] if c < len(COLS) else "n_mmol"] = item.text().strip()
        self.fill_table()
        self.update_check()
        self.main.push_undo()

    def role_changed(self, r, role):
        if r < len(self.st["reagents"]):
            if role == "ref":                                       # nur ein Bezug
                for row in self.st["reagents"]:
                    if row.get("role") == "ref":
                        row["role"] = "reagent"
            self.st["reagents"][r]["role"] = role
            QTimer.singleShot(0, self.fill_table)       # nicht während des Signals des Auswahlfelds neu aufbauen
            self.update_check()
            self.main.push_undo()

    def insert_amounts(self):
        """Klammer der gewählten Zeile an der Schreibmarke einfügen, z. B. „(1.03 g, 5.00 mmol, 1.0 eq.)“."""
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()})
        if not rows or rows[0] >= len(self.st["reagents"]):
            return
        row = self.st["reagents"][rows[0]]
        calc = row_amounts(row, self.ref_mmol())
        if row.get("role") == "ref" and calc["mmol"] is not None:
            calc["eq"] = 1.0
        txt = amount_text(row, calc)
        if txt:
            cur = self.ed_proc.textCursor()
            cur.setCharFormat(QTextCharFormat())
            cur.insertText(" " + txt if cur.position() and not self.ed_proc.toPlainText()[cur.position() - 1:
                                                                                       cur.position()].isspace()
                           else txt)
            self.ed_proc.setFocus()

    def procedures(self):
        """Allgemeine Vorschriften des Projekts (publication.elucida) -> [dict(key, title, text)]."""
        from elucida.app import publication as PUB
        pub = PUB.publication_of(getattr(self.main, "project_dir", None))
        return PUB.load(pub)["procedures"] if pub else []

    def fill_gp_menu(self):
        m = self.btn_gp.menu()
        m.clear()
        procs = self.procedures()
        for p in procs:
            a = m.addAction(f"GP {p['key']}" + (f" – {p['title']}" if p["title"] else ""))
            a.setCheckable(True)
            a.setChecked(p["key"] == self.st.get("gp"))
            a.triggered.connect(lambda _=False, k=p["key"]: self.set_gp(k))
        if not procs:
            m.addAction(T("syn_gp_none_defined")).setEnabled(False)
        m.addSeparator()
        m.addAction(T("syn_gp_off"), lambda: self.set_gp(""))
        from elucida.app import publication as PUB
        pub = PUB.publication_of(getattr(self.main, "project_dir", None))
        a = m.addAction(T("pub_procs") + " …", self.edit_procedures)
        a.setEnabled(pub is not None)

    def edit_procedures(self):
        from elucida.app import publication as PUB
        from elucida.app.publication_view import edit_procedures
        edit_procedures(self, PUB.publication_of(self.main.project_dir))

    def set_gp(self, key):
        """GP der Verbindung merken und den Verweis im Text pflegen: neu „according to GP A“ an der Schreibmarke,
        Wechsel A -> B ersetzt „GP A“, „Keine GP“ entfernt „according to GP A“ (bzw. „GP A“). Ein Undo-Schritt."""
        old = self.st.get("gp") or ""
        self.st["gp"] = key
        self.btn_gp.setText(f"GP {key}" if key else "GP")
        doc = self.ed_proc.document()
        from PySide6.QtGui import QTextDocument
        flags = QTextDocument.FindCaseSensitively | QTextDocument.FindWholeWords
        bold = QTextCharFormat()
        bold.setFontWeight(_BOLD)
        found = False
        if old and old != key:
            pat = f"GP {old}" if key else f"according to GP {old}"
            cur = doc.find(pat, 0, flags)
            while not cur.isNull():
                found = True
                cur.insertText(f"GP {key}" if key else "", bold if key else QTextCharFormat())
                cur = doc.find(pat, cur, flags)
            if not key and found:                        # Leerzeichen vor dem entfernten Verweis
                h = doc_html(self.ed_proc)
                self.ed_proc.setHtml(simple_to_qt(re.sub(r"\s+(?=[.,;]|$)", "", h)))
            if not key and f"GP {old}" in self.ed_proc.toPlainText():   # anders formulierter Verweis bleibt
                self.main.statusBar().showMessage(T("syn_gp_left", key=old), 8000)
        if key and not found and f"GP {key}" not in self.ed_proc.toPlainText():
            cur = self.ed_proc.textCursor()
            pre = "" if not cur.position() or self.ed_proc.toPlainText()[cur.position() - 1].isspace() else " "
            cur.insertText(pre + "according to ", QTextCharFormat())
            cur.insertText(f"GP {key}", bold)
            cur.setCharFormat(QTextCharFormat())
            self.ed_proc.setTextCursor(cur)
            self.ed_proc.setFocus()
        self.timer.stop()                                # Text und Zuordnung zusammen als ein Schritt
        self.proc_changed()

    def gp_blocks(self):
        """Einzel-SI: gewählte allgemeine Vorschrift vor „Synthesis of …“ (Gesamt-SI: einmal, publication_si)."""
        from elucida.si.publication_si import procedure_blocks
        p = next((p for p in self.procedures() if p["key"] == self.st.get("gp")), None)
        return procedure_blocks(p) if p else []

    # -- Vorschau / SI --------------------------------------------------------------------
    def update_preview(self):
        st = self.scheme_asset()
        if st is not None and st.get("rgba") is not None:
            a = st["rgba"]
            img = QImage(a.data, a.shape[1], a.shape[0], a.strides[0], QImage.Format_RGBA8888).copy()
            dpr = max(1.0, self.lbl_prev.devicePixelRatioF())              # scharf auf HiDPI-Bildschirmen
            pm = QPixmap.fromImage(img).scaledToWidth(int(min(700 * dpr, img.width())), Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            self.lbl_prev.setPixmap(pm)
            self.lbl_prev.show()
        else:
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_prev.hide()
        name = self.compound_name()
        empty = st is None and not (self.st.get("proc") or "").strip()   # noch nichts da: Anleitung statt leerer Seite
        self.preview_stack.setCurrentIndex(0 if empty else 1)
        if empty:
            return
        self.txt_prev.setHtml(f"<p>Synthesis of <b>{_h.escape(name)}</b></p><p style='text-align:justify'>"
                              f"{self.st.get('proc') or ''}</p>")

    def si_blocks(self, img_dir):
        """„Synthesis of Name“, Schema (ChemDraw-Objekt mit CDX, sonst Vektorbild), Vorschrift."""
        blocks = [("synthesis", self.compound_name())]
        sp = self.scheme_parts()
        st = self.scheme_asset()
        if sp is not None:
            img_dir = Path(img_dir)
            img_dir.mkdir(parents=True, exist_ok=True)
            w_cm = h_cm = None
            if st is not None and st.get("clip"):
                x0, y0, x1, y1 = st["clip"]
                w_cm, h_cm = (x1 - x0) / 72 * 2.54, (y1 - y0) / 72 * 2.54
            png = None
            if st is not None and st.get("rgba") is not None:
                from PIL import Image
                png = img_dir / (Path(self.st["scheme"]).stem + "_scheme.png")
                Image.fromarray(st["rgba"]).save(png)
            if sp["cdx"] and (sp["emf"] or png):
                prev = sp["emf"] or png
                if sp["emf"]:
                    w_cm, h_cm = emf_size_cm(sp["emf"])
                blocks.append(("ole", str(sp["cdx"]), str(prev), w_cm or 12.0, h_cm or 4.0))
            elif png is not None:
                svg = None
                if st.get("pdf"):                                   # Vektor für Word: Seite der Exportdatei als SVG
                    import pymupdf
                    doc = pymupdf.open("pdf", st["pdf"])
                    doc[0].set_cropbox(pymupdf.Rect(*st["clip"]))
                    svg = img_dir / (Path(self.st["scheme"]).stem + "_scheme.svg")
                    svg.write_text(doc[0].get_svg_image(text_as_path=True), encoding="utf-8")
                blocks.append(("image", str(png), w_cm or 12.0, h_cm or 4.0, str(svg) if svg else None))
        if (self.st.get("proc") or "").strip():
            blocks.append(("char", self.st["proc"]))
        return blocks

    def export_dialog(self):
        from elucida.si import lines as SI
        if not self.main.ensure_project():
            return None
        pdir = self.main.project_dir
        path = PRJ.export_dir(pdir, PRJ.SI_DIR) / (PRJ.export_stem(self.compound_name() or self.main.export_name(),
                                                                   self.STATE_KEY) + ".docx")
        try:
            SI.write_docx(path, self.gp_blocks() + self.si_blocks(PRJ.work_dir(pdir, self.STATE_KEY)))
        except PermissionError:
            self.main.error(T("report_locked", p=path))
            return None
        if self.main.is_quick():                        # Schnellauswertung: in den gewählten Ordner
            path = (self.main.place_exports([path]) or [path])[0]
        self.main.log_signal.emit(T("saved", p=str(path)))
        return path


def doc_html(edit):
    return doc_to_html(edit.document())


def simple_to_qt(h):
    """Kleines SI-HTML (b, i, sub, sup, br) in den Editor laden."""
    return h.replace("<br>", "<br/>")
