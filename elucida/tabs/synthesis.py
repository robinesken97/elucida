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
        return float(t)
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
        for part in (p.strip() for p in re.split(r",(?!\d)", body)):     # „1,03 g“: Dezimalkomma bleibt
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


def cell_num(x):
    """Zahlenfeld der Tabelle -> float oder None (leer oder kein Zahlenwert, z. B. „150 mg“)."""
    try:
        return float(str(x or "").strip().replace(",", "."))
    except ValueError:
        return None


def row_amounts(row, ref_mmol=None):
    """Zeile der Tabelle (M, m_mg, V_mL, c_M, rho, role) -> dict(M, mmol, eq, yld) (Zahlen oder None)."""
    M = molar_mass(row.get("M"))
    m, V, c, rho = (cell_num(row.get(k)) for k in ("m_mg", "V_mL", "c_M", "rho"))
    n = None
    if m is not None and M:
        n = m / M
    elif V is not None and c is not None:
        n = V * c
    elif V is not None and rho is not None and M:
        n = V * rho * 1000 / M
    out = dict(M=M, mmol=n, eq=None, yld=None)
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
    m = str(row.get("m_mg") or "").strip()
    V = str(row.get("V_mL") or "").strip()
    m = m if cell_num(m) is not None else ""
    V = V if cell_num(V) is not None else ""
    if m:                                                   # Stellen wie eingegeben; ab 1000 mg in g
        mv = float(m.replace(",", "."))
        parts.append(f"{fmt_sig(mv / 1000, sig_digits(m))} g" if mv >= 1000 else f"{m.replace(',', '.')} mg")
    if V:
        vv = float(V.replace(",", "."))
        parts.append(f"{fmt_sig(vv * 1000, sig_digits(V))} µL" if vv < 0.1 else f"{V.replace(',', '.')} mL")
        if str(row.get("c_M") or "").strip():
            parts.append(f"{row['c_M']} M")
    if calc.get("mmol") is not None:
        parts.append(f"{fmt_sig(calc['mmol'])} mmol")
    if calc.get("yld") is not None:
        parts.append(f"{calc['yld']:.0f}%")
    elif calc.get("eq") is not None:
        parts.append(f"{calc['eq']:.1f} eq.")
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
    for m in mols or []:
        if m is not None:
            role = ("product" if m.HasProp("CDX_PRODUCT_ID") else
                    "reactant" if m.HasProp("CDX_REAGENT_ID") else "")
            out.append((rdMolDescriptors.CalcMolFormula(m, True, True), float(Descriptors.MolWt(m)), role))  # D, [13C]
    return out


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
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QScrollArea, QSplitter, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QTextBrowser, QTextEdit, QVBoxLayout, QWidget)

from elucida.app import project as PRJ  # noqa: E402
from elucida.app.style import HINT_CSS, WARN_CSS  # noqa: E402

ROLES = ("ref", "reagent", "product", "other")
COLS = ("name", "M", "m_mg", "V_mL", "c_M", "rho", "role")          # bearbeitbare Spalten, danach n und eq./%


class SynthTab(QWidget):
    STATE_KEY = "syn"
    DEFAULT_STATE = dict(name="", scheme=None, proc="", reagents=[])

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
        hint = QLabel(T("syn_scheme_hint"), wordWrap=True)
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
            n = f"{calc['mmol']:.3f}" if calc["mmol"] is not None else "–"
            e = f"{calc['yld']:.0f}%" if calc["yld"] is not None else f"{calc['eq']:.2f}" if calc["eq"] is not None \
                else ("1.00" if row.get("role") == "ref" and calc["mmol"] else "–")
            for c, val in ((len(COLS), n), (len(COLS) + 1, e)):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
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
                out[name] = dict(M=molar_mass(row.get("M")), density=cell_num(row.get("rho")), conc=cell_num(row.get("c_M")))
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
        """Moleküle des Schemas als Zeilen (Summenformel als M); Namen trägst du ein (z. B. S1)."""
        p = self.st.get("scheme")
        if not p or Path(p).suffix.lower() != ".cdxml":
            self.main.error(T("syn_need_cdxml"))
            return
        from elucida.formats import cdxml as CDX
        prod = lambda role: role == "product"                                   # noqa: E731
        have = {(x, prod(r.get("role"))) for r in self.st["reagents"] for x in (str(r.get("M") or ""), r.get("name"))
                if x}
        mols = scheme_molecules(p)
        # Reihenfolge wie die Vorschrift: Edukte (erstes = Bezug 1.0 eq.), Reagenzien über/unter dem Pfeil, Produkt
        # Mit Reaktionsschritt: Moleküle ohne Rolle (über/unter dem Pfeil) sind Reagenzien, nie der Bezug
        step = any(r for _f, _m, r in mols)
        rows = [("", f, "reactant" if r == "reactant" or not step else "reagent")
                for f, _m, r in sorted(mols, key=lambda x: x[2] != "reactant") if r != "product"]
        try:
            rows += [(n, f, r) for n, f, r in CDX.scheme_reagents(p)]
        except Exception as ex:
            self.main.log_signal.emit(f"{Path(p).name}: {ex}")
        rows += [("", f, "product") for f, _m, r in mols if r == "product"]
        for name, formula, kind in rows:
            if (formula, prod(kind)) in have or (name, prod(kind)) in have:  # Isomere: Produkt trotz gleicher Formel
                continue
            role = ("ref" if kind == "reactant" and not any(r["role"] == "ref" for r in self.st["reagents"])
                    else "reagent" if kind == "reactant" else kind)
            self.st["reagents"].append(dict(name=name, M=formula, m_mg="", V_mL="", c_M="", rho="", role=role))
            have |= {(x, prod(kind)) for x in (formula, name) if x}
        self.fill_table()
        self.main.push_undo()

    def cell_changed(self, item):
        r, c = item.row(), item.column()
        if self._loading or c >= len(COLS) or r >= len(self.st["reagents"]):
            return
        self.st["reagents"][r][COLS[c]] = item.text().strip()
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
            SI.write_docx(path, self.si_blocks(PRJ.work_dir(pdir, self.STATE_KEY)))
        except PermissionError:
            self.main.error(T("report_locked", p=path))
            return None
        self.main.log_signal.emit(T("saved", p=str(path)))
        return path


def doc_html(edit):
    return doc_to_html(edit.document())


def simple_to_qt(h):
    """Kleines SI-HTML (b, i, sub, sup, br) in den Editor laden."""
    return h.replace("<br>", "<br/>")
