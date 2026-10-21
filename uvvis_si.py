"""SI-Zeilen und SI-Export: UV-Vis-Zeile (ε-Tab), Elementaranalyse, Word-Datei (docx ohne Zusatzpaket).

Stil wie in den SI der Arbeitsgruppe: „m.p. …; IR [cm-1]: ṽ = …; HR-MS-ESI(+) calc. …; found …;
UV-Vis: λmax: 331 nm (ε = 8443 cm-1 M-1), …“. Die Elementaranalyse folgt dem üblichen Wiley-Format
„Elemental analysis calcd (%) for C18H20N2: C 81.78, H 7.63, N 10.60; found: C 81.52, H 7.70, N 10.41“.
"""
from __future__ import annotations

import html as _html
import re
import zipfile
from pathlib import Path

import uvvis_core as core
from uvvis_irms import formula_str, parse_formula

# Mittlere Atommassen (IUPAC 2021, konventionelle Werte) für die Elementaranalyse
AVG = {"H": 1.008, "D": 2.014, "Li": 6.94, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998,
       "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "K": 39.098,
       "Ca": 40.078, "Ti": 47.867, "V": 50.942, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933,
       "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723, "Ge": 72.630, "As": 74.922, "Se": 78.971,
       "Br": 79.904, "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Mo": 95.95, "Ru": 101.07,
       "Rh": 102.906, "Pd": 106.42, "Ag": 107.868, "Cd": 112.414, "In": 114.818, "Sn": 118.710, "Sb": 121.760,
       "Te": 127.60, "I": 126.904, "Cs": 132.905, "Ba": 137.327, "La": 138.905, "Hf": 178.49, "W": 183.84,
       "Re": 186.207, "Os": 190.23, "Ir": 192.217, "Pt": 195.084, "Au": 196.967, "Hg": 200.592, "Tl": 204.38,
       "Pb": 207.2, "Bi": 208.980}
EA_ELEMENTS = ("C", "H", "N", "S")          # was CHNS-Analysatoren messen
EA_TOL = 0.4                                # übliche Grenze der Journals (absolut, in %)


# ---------------------------------------------------------------------------- Elementaranalyse
def parse_solvate(text: str) -> list[tuple[float, str]]:
    """'0.5 CH2Cl2, H2O' / '0.5CH2Cl2·H2O' -> [(0.5, 'CH2Cl2'), (1.0, 'H2O')]."""
    out = []
    for part in re.split(r"[,;·•+]|\s{2,}", text or ""):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)?\s*([A-Z].*)", part)
        if not m:
            raise ValueError(f"Solvat nicht lesbar: {part}")
        n = float(m.group(1).replace(",", ".")) if m.group(1) else 1.0
        parse_formula(m.group(2))                  # prüft die Formel
        out.append((n, m.group(2).replace(" ", "")))
    return out


def ea_composition(formula: str, solvate: str = "") -> dict:
    """Massenanteile in % (Formel + Solvat, mittlere Atommassen)."""
    counts = dict(parse_formula(formula))
    for n, f in parse_solvate(solvate):
        for el, k in parse_formula(f).items():
            counts[el] = counts.get(el, 0) + n * k
    missing = [el for el in counts if el not in AVG]
    if missing:
        raise ValueError("keine Atommasse für " + ", ".join(missing))
    mw = sum(AVG[el] * k for el, k in counts.items())
    return {el: 100 * AVG[el] * k / mw for el, k in counts.items()}


def _num(n):
    return f"{n:g}"


def ea_formula_label(formula: str, solvate: str = "") -> str:
    """'C18H20N2·0.5CH2Cl2' (Klartext)."""
    f = formula_str(parse_formula(formula))
    for n, s in parse_solvate(solvate):
        f += "·" + ("" if n == 1 else _num(n)) + s
    return f


def _sub_html(f):
    return re.sub(r"(?<=[A-Za-z\)])(\d+(?:\.\d+)?)", r"<sub>\1</sub>", _html.escape(f))


def ea_line(formula: str, solvate: str, found: dict):
    """-> (Klartext, HTML, Hinweise). found: {'C': '81.52', …}; nur gemessene Elemente stehen bei found."""
    comp = ea_composition(formula, solvate)
    els = [el for el in EA_ELEMENTS if el in comp or (found or {}).get(el)]
    calc = ", ".join(f"{el} {comp.get(el, 0.0):.2f}" for el in els if el in comp)
    fv = {}
    for el in els:
        v = str((found or {}).get(el) or "").strip().replace(",", ".")
        if v:
            fv[el] = float(v)
    notes = []
    for el, v in fv.items():
        d = v - comp.get(el, 0.0)
        if abs(d) > EA_TOL:
            notes.append((el, d))
    label = ea_formula_label(formula, solvate)
    fnd = ", ".join(f"{el} {v:.2f}" for el, v in fv.items()) if fv else "–"
    plain = f"Elemental analysis calcd (%) for {label}: {calc}; found: {fnd}"
    html = f"<b>Elemental analysis</b> calcd (%) for {_sub_html(label)}: {calc}; found: {fnd}"
    return plain, html, notes


# ---------------------------------------------------------------------------- UV-Vis
def uvvis_line(results, cfg, solvent: str = ""):
    """ε-Ergebnisse -> (Klartext, HTML): UV-Vis: λmax: 331 nm (ε = 8443 cm-1 M-1), … Nur Banden, die auch im Bild
    stehen (nicht abgewählt, R² ≥ Schwelle); ε gerundet auf die Genauigkeit des Standardfehlers (wie in der Tabelle,
    ohne ±). Ohne Molmasse: a in L g-1 cm-1."""
    molar = bool(core.conc_factor(cfg))
    items_p, items_h = [], []
    for r in sorted(results, key=lambda r: r["lam"]):
        if not r.get("fit") or r.get("hidden"):
            continue
        v, _ = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg))
        sh = ", sh" if r.get("shoulder") and (cfg.get("labels") or {}).get("mark_shoulders") else ""
        lam = f"{r['lam']:.0f}"
        if molar:
            items_p.append(f"{lam} nm (ε = {v} cm⁻¹ M⁻¹{sh})")
            items_h.append(f"{lam} nm (<i>ε</i> = {v} cm<sup>−1</sup> M<sup>−1</sup>{sh})")
        else:
            items_p.append(f"{lam} nm (a = {v} L g⁻¹ cm⁻¹{sh})")
            items_h.append(f"{lam} nm (<i>a</i> = {v} L g<sup>−1</sup> cm<sup>−1</sup>{sh})")
    if not items_p:
        return "", ""
    head = "UV-Vis" + (f" ({solvent})" if solvent else "")
    plain = f"{head}: λmax: " + ", ".join(items_p)
    html = f"<b>{_html.escape(head)}</b>: <i>λ</i><sub>max</sub>: " + ", ".join(items_h)
    return plain, html


# ---------------------------------------------------------------------------- Absatz und Word-Datei
def join_lines(parts):
    """Teilzeilen (Klartext, HTML) zu einem Absatz im SI-Stil: durch „; “ getrennt, Punkt am Ende."""
    parts = [(p.rstrip(" .;"), h.rstrip(" .;")) for p, h in parts if p]
    if not parts:
        return "", ""
    return "; ".join(p for p, _ in parts) + ".", "; ".join(h for _, h in parts) + "."


def html_runs(h):
    """Kleines HTML (b, i, sub, sup) -> [(Text, {b, i, sub, sup})]."""
    out, st = [], {"b": 0, "i": 0, "sub": 0, "sup": 0}
    for tok in re.split(r"(<[^>]+>)", h or ""):
        m = re.fullmatch(r"<(/?)(b|i|sub|sup)\s*>", tok)
        if m:
            st[m.group(2)] += -1 if m.group(1) else 1
        elif tok.startswith("<"):
            continue
        elif tok:
            out.append((_html.unescape(tok), {k for k, v in st.items() if v > 0}))
    return out


def markup_runs(markup):
    """Tabellen-Markup des X-Ray-Tabs (*kursiv*, _{tief}, ^{hoch}) -> Läufe wie html_runs."""
    import uvvis_xray as XRAY
    out = []
    for t, s in XRAY.runs(markup):
        if "o" in s:
            t = "".join(ch + "̅" for ch in t)
        out.append((t, {k for k, c in (("i", "i"), ("sub", "s"), ("sup", "p")) if c in s}))
    return out


# Zwischenüberschriften der Parametertabelle (X-Ray-Tab) fett
SECTION_ROWS = {"Bond lengths [Å]", "Angles [°]", "Torsion angles [°]"}
_FONT = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'


def _run_xml(text, st, size=22, bold=False):
    props = _FONT + ("<w:b/>" if bold or "b" in st else "") + ("<w:i/>" if "i" in st else "")
    if "sub" in st:
        props += '<w:vertAlign w:val="subscript"/>'
    elif "sup" in st:
        props += '<w:vertAlign w:val="superscript"/>'
    props += f'<w:sz w:val="{size}"/>'
    t = _html.escape(text, quote=False)
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'


def _para_xml(runs, size=22, bold=False, align=None, space_after=120, keep_next=False):
    ppr = f'<w:spacing w:after="{space_after}" w:line="276" w:lineRule="auto"/>'
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    if keep_next:
        ppr += "<w:keepNext/>"
    body = "".join(_run_xml(t, s, size, bold) for t, s in runs)
    return f"<w:p><w:pPr>{ppr}</w:pPr>{body}</w:p>"


def _table_xml(header, rows, size=20):
    """Dreilinien-Tabelle wie in den SI (Linie oben, unter dem Kopf, unten), Spalten zentriert, erste links."""
    def cell(markup, bold=False, first=False, top=False, bottom=False, head=False):
        b = []
        if top:
            b.append('<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>')
        if bottom or head:
            b.append('<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>')
        borders = f"<w:tcBorders>{''.join(b)}</w:tcBorders>" if b else ""
        p = _para_xml(markup_runs(markup), size=size, bold=bold, align="left" if first else "center", space_after=0)
        return f"<w:tc><w:tcPr>{borders}</w:tcPr>{p}</w:tc>"
    n = len(rows)
    xml = ('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/>'
           '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>')
    xml += "<w:tr>" + "".join(cell(h, bold=True, first=(j == 0), top=True, head=True)
                              for j, h in enumerate(header)) + "</w:tr>"
    for i, r in enumerate(rows):
        xml += "<w:tr>" + "".join(cell(c or "", bold=(j == 0 and r[0] in SECTION_ROWS), first=(j == 0),
                                       bottom=(i == n - 1)) for j, c in enumerate(r)) + "</w:tr>"
    return xml + "</w:tbl>"


def write_docx(path, blocks):
    """blocks: [("h", Text) | ("p", HTML) | ("caption", HTML) | ("table", Titel, Kopf, Zeilen, Fußnoten)]."""
    body = []
    for b in blocks:
        if b[0] == "h":
            body.append(_para_xml([(b[1], set())], size=24, bold=True, space_after=120, keep_next=True))
        elif b[0] == "p":
            body.append(_para_xml(html_runs(b[1]), align="both"))
        elif b[0] == "caption":
            body.append(_para_xml(html_runs(b[1]), size=20, align="both", space_after=240))
        elif b[0] == "table":
            _, title, header, rows, notes = b
            if title:
                body.append(_para_xml([(title, {"b"})], size=22, keep_next=True))
            body.append(_table_xml(header, rows))
            for n_ in notes or ():
                body.append(_para_xml(markup_runs(n_), size=18, space_after=0))
            body.append(_para_xml([("", set())]))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + "".join(body) +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1134" '
           'w:left="1417" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
              'wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return path
