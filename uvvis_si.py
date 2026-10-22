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


# ---------------------------------------------------------------------------- Geschützte Leerzeichen
NBSP = "\u00a0"
_UNITS = ("°C|K|°|Å|nm|pm|mm|cm|µm|μm|m|mg|µg|μg|g|kg|mmol|µmol|μmol|mol|mL|µL|μL|L|mM|µM|μM|M|N|equiv|eq|h|min|ms|s|"
          "ppm|kHz|MHz|GHz|Hz|mT|mV|V|eV|Eh|E<sub>h</sub>|kcal|kJ|atm|mbar|bar|Torr|Da|wt%|%")
_NB_RULES = [
    (re.compile(r"(?<=\d)[ ]+(?=(?:" + _UNITS + r")(?![A-Za-z0-9]))"), NBSP),          # Zahl ↔ Einheit: 67 °C, 0.82 mmol
    (re.compile(r"[ ]+([=±≈])[ ]+"), NBSP + r"\1" + NBSP),                            # ε = 8443, 7.39 ± 0.01
    (re.compile(r"(?<=</sup>)[ ]+(?=[A-Za-zµμ]+<sup>)"), NBSP),                        # cm<sup>-1</sup> M<sup>-1</sup>
    (re.compile(r"(?<=-1)[ ]+(?=[A-Za-zµμ]+-1\b)"), NBSP),                             # cm-1 M-1 (Klartext)
    (re.compile(r"(?<=⁻¹)[ ]+(?=[A-Za-zµμ]+⁻¹)"), NBSP),                               # cm⁻¹ M⁻¹
    (re.compile(r"(?<![\w.])([A-Z][a-z]?)[ ]+(?=\d{1,3}\.\d{2}\b)"), r"\1" + NBSP),     # Elementaranalyse: C 81.78
    (re.compile(r"\bm\.p\.[ ]+"), "m.p." + NBSP),
]


def nbsp(text):
    """Geschützte Leerzeichen (U+00A0) zwischen Zahl und Einheit, um =/±, in zusammengesetzten Einheiten und in der
    Elementaranalyse – Word bricht dort nicht mehr um. Funktioniert für Klartext und das kleine HTML der SI-Zeilen."""
    for rx, rep in _NB_RULES:
        text = rx.sub(rep, text)
    return text


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
            items_p.append(f"{lam} nm (ε = {v} cm-1 M-1{sh})")
            items_h.append(f"{lam} nm (ε = {v} cm<sup>-1</sup> M<sup>-1</sup>{sh})")
        else:
            items_p.append(f"{lam} nm (a = {v} L g-1 cm-1{sh})")
            items_h.append(f"{lam} nm (<i>a</i> = {v} L g<sup>-1</sup> cm<sup>-1</sup>{sh})")
    if not items_p:
        return "", ""
    head = "UV-Vis" + (f" ({solvent})" if solvent else "")
    plain = f"{head}: λmax: " + ", ".join(items_p)
    html = f"<b>{_html.escape(head)}</b>: <b>λ<sub>max</sub></b>: " + ", ".join(items_h)
    return plain, html


def eps_methods(cfg, results, spectra, solvent: str = ""):
    """SI-Text (englisch) zur ε-Bestimmung einer Verdünnungsreihe nach prepare_series: Basislinie, Fit A/d = m·c + b
    (OLS), Cutoff, Unsicherheiten; danach die Ergebnisse je Bande (ε ± SE wie in der Tabelle gerundet, 95-%-KI, n,
    R²). Exponenten wie in der SI als „-1“."""
    fitted = [r for r in results if r.get("fit")]
    if not fitted:
        return ""
    molar = bool(core.conc_factor(cfg))
    unit = {"uM": "µM", "mg/mL": "mg mL-1"}.get(cfg["conc_unit"], cfg["conc_unit"])
    cs = sorted({s_["c"] for s_ in spectra})
    coef, cunit = ("ε", "cm-1 M-1") if molar else ("a", "L g-1 cm-1")
    m = ["Molar absorption coefficients were determined from a dilution series" if molar else
         "Specific absorption coefficients a (no molar mass given) were determined from a dilution series",
         ""]
    m[0] += (f"{' in ' + solvent if solvent else ''} ({len(cs)} concentrations, {cs[0]:g}–{cs[-1]:g} {unit}, "
             f"path length {cfg['path_length_cm']:g} cm" + (f"; mass concentrations converted with M = "
                                                            f"{float(cfg['molar_mass_g_mol']):.2f} g mol-1"
                                                            if molar and cfg["conc_unit"] == "mg/mL" else "") + ").")
    bl = cfg.get("_baseline_info")
    if bl:
        a, b = bl["window"]
        txt = (f"Each spectrum was baseline-corrected by its median absorbance between {a:.0f} and {b:.0f} nm "
               "(the range of lowest absorbance of the most concentrated solution)")
        if cfg.get("baseline_mode") == "series" and len(spectra) >= 3:
            txt += ("; a contribution proportional to the concentration in this range (linear regression of the "
                    "window absorbance against c, kept if the slope exceeded twice its standard error) was retained")
        m[1] = txt + "."
    sampling = "interpolated at the band wavelength"
    if cfg.get("avg_window_nm"):
        sampling = f"averaged over ±{cfg['avg_window_nm']:g} nm around the band wavelength"
    snap = (f", which was set to the local maximum within ±{cfg['snap_window_nm']:g} nm of the most concentrated "
            "unsaturated spectrum" if cfg.get("snap_window_nm") else "")
    cuts = sorted({float(r["cutoff"]) for r in fitted})
    cut_txt = (f"A ≤ {cuts[0]:g}" if len(cuts) == 1 else
               f"A ≤ {cfg['max_abs_fit']:g} (band-specific limits: " + ", ".join(
                   f"{r['lam']:.0f} nm: {r['cutoff']:g}" for r in fitted if r["cutoff"] != cfg["max_abs_fit"]) + ")")
    model = "A/d = " + coef + "·c + b" if cfg["fit_intercept"] else "A/d = " + coef + "·c"
    dof = "n − 2" if cfg["fit_intercept"] else "n − 1"
    m.append(f"At each band, the absorbance ({sampling}{snap}) divided by the path length was fitted against the "
             f"concentration by ordinary least squares ({model}), using only points with {cut_txt} to stay in "
             f"the linear range; {coef} is the slope. Uncertainties are given as standard error (SE) and 95% "
             f"confidence interval (t(0.975; {dof})·SE); {coef} was rounded to the precision of the SE"
             + (" and is given without decimals" if molar else "") + ".")
    if any(r.get("hidden") for r in fitted):
        m.append(f"Bands with R² < {cfg['min_r2']:g} or deselected bands are listed but not labelled in the figure.")
    res = []
    for r in sorted(fitted, key=lambda r: r["lam"]):
        v, e = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg))
        ci = r.get("eps_ci95")
        _, ci_s = core.fmt_ve(r["eps"], ci, max_decimals=core.eps_max_decimals(cfg)) if ci == ci else (None, None)
        sh = " (sh)" if r.get("shoulder") and (cfg.get("labels") or {}).get("mark_shoulders") else ""
        txt = f"{r['lam']:.0f} nm{sh}: {coef} = {v}" + (f" ± {e}" if e else "") + f" {cunit}"
        txt += f" (SE; 95% CI ± {ci_s}" if ci_s else " ("
        txt += f"{'; ' if ci_s else ''}n = {r['fit']['n']}, R² = {r['fit']['r2']:.4f})"
        if r.get("hidden"):
            txt += " [not in figure]"
        res.append(txt)
    return " ".join(x for x in m if x) + "\n\n" + "; ".join(res) + "."


# ---------------------------------------------------------------------------- Absatz und Word-Datei
def join_lines(parts):
    """Teilzeilen (Klartext, HTML) zu einem Absatz im SI-Stil: durch „; “ getrennt, Punkt am Ende."""
    parts = [(p.rstrip(" .;"), h.rstrip(" .;")) for p, h in parts if p]
    if not parts:
        return "", ""
    return "; ".join(p for p, _ in parts) + ".", "; ".join(h for _, h in parts) + "."


def html_runs(h):
    """Kleines HTML (b, i, sub, sup, br) -> [(Text, {b, i, sub, sup, br})]."""
    out, st = [], {"b": 0, "i": 0, "sub": 0, "sup": 0}
    for tok in re.split(r"(<[^>]+>)", h or ""):
        m = re.fullmatch(r"<(/?)(b|i|sub|sup)\s*>", tok)
        if m:
            st[m.group(2)] += -1 if m.group(1) else 1
        elif re.fullmatch(r"<br\s*/?>", tok):
            out.append(("", {"br"}))
        elif tok.startswith("<"):
            continue
        elif tok:
            out.append((_html.unescape(tok), {k for k, v in st.items() if v > 0}))
    return out


def markup_runs(markup, bold=False):
    """Tabellen-Markup des X-Ray-Tabs (*kursiv*, _{tief}, ^{hoch}, ~{Überstrich}, Zeilenumbruch \n) -> Läufe."""
    import uvvis_xray as XRAY
    out = []
    for li, line in enumerate(str(markup).split("\n")):
        if li:
            out.append(("", {"br"}))
        for t, s_ in XRAY.runs(line):
            st = {k for k, c in (("i", "i"), ("sub", "s"), ("sup", "p"), ("ov", "o")) if c in s_}
            out.append((t, st | ({"b"} if bold else set())))
    return out


# ---------------------------------------------------------------------------- docx (Stil der SI)
# Gemessen an einer SI der Arbeitsgruppe (Word): A4, Ränder 2.5 cm, Arial 11 pt, Blocksatz, 1.5-zeilig, Hoch-/Tiefstellung
# 7 pt (Word: vertAlign), Dreilinien-Tabellen, Unterschriften „Figure Sn: …“ / „Table Sn: …“ (fett bis zum Doppelpunkt).
_FONT = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Arial"/>'
TEXT_W = 11906 - 2 * 1417                  # Textbreite in twips (A4, 2.5 cm Rand)
COL_GAP = 425                              # Abstand zweier Spalten (0.75 cm)
_MONO = '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New" w:eastAsia="Courier New"/>'


def _run_xml(text, st, size=22):
    if "br" in st:
        return "<w:r><w:br/></w:r>"
    if "ov" in st:                          # Überstrich: Formelobjekt „Balken oben“, Text als Arial (m:nor)
        wr = _FONT + ("<w:b/>" if "b" in st else "") + ("<w:i/>" if "i" in st else "") + \
            f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        t = _html.escape(text, quote=False)
        return ('<m:oMath><m:bar><m:barPr><m:pos m:val="top"/><m:ctrlPr><w:rPr>' + wr + '</w:rPr></m:ctrlPr>'
                '</m:barPr><m:e><m:r><m:rPr><m:nor/></m:rPr><w:rPr>' + wr + f'</w:rPr><m:t>{t}</m:t></m:r></m:e>'
                '</m:bar></m:oMath>')
    if "\t" in text and text.strip("\t") == "":
        return "<w:r>" + "<w:tab/>" * len(text) + "</w:r>"
    props = (_MONO if "mono" in st else _FONT) + ("<w:b/><w:bCs/>" if "b" in st else "") + \
        ("<w:i/><w:iCs/>" if "i" in st else "")
    if "sub" in st:
        props += '<w:vertAlign w:val="subscript"/>'
    elif "sup" in st:
        props += '<w:vertAlign w:val="superscript"/>'
    props += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    t = _html.escape(text, quote=False)
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'


def _seq_xml(kind, num, size=22):
    """Word-Feld SEQ (Abbildungs-/Tabellennummer), fett, mit fortlaufendem Vorgabewert; in einer SI mit eigenen
    SEQ-Feldern zählt Word beim Aktualisieren (F9) einfach weiter."""
    props = _FONT + f'<w:b/><w:bCs/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return (f'<w:fldSimple w:instr=" SEQ {kind} \\* ARABIC "><w:r><w:rPr>{props}</w:rPr><w:t>{num}</w:t></w:r>'
            '</w:fldSimple>')


def _ppr(align="both", line=360, before=0, after=0, keep_next=False, tabs=""):
    x = f'<w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>'
    if keep_next:
        x += "<w:keepNext/>"
    if tabs:
        x = f"<w:tabs>{tabs}</w:tabs>" + x
    return f"<w:pPr>{x}<w:jc w:val=\"{align}\"/></w:pPr>"


def _para(runs, size=22, **kw):
    return "<w:p>" + _ppr(**kw) + "".join(_run_xml(t, s, size) for t, s in runs) + "</w:p>"


def _label_para(kind, num, runs, **kw):
    """„Figure S1: …“ / „Table S1: …“ – Kürzel und Nummer fett, Doppelpunkt bei Tabellen fett, bei Abbildungen nicht
    (wie in der SI)."""
    lab = _run_xml(f"{kind} S", {"b"})
    colon = _run_xml(":", {"b"} if kind == "Table" else set())
    return "<w:p>" + _ppr(**kw) + lab + _seq_xml(kind, num) + colon + _run_xml(" ", set()) + \
        "".join(_run_xml(t, s) for t, s in runs) + "</w:p>"


def _border(sides):
    b = "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="000000"/>' for s in sides)
    return f"<w:tcBorders>{b}</w:tcBorders>" if b else ""


def _head_runs(text):
    """Tabellenkopf: ganz fett (wie in der SI)."""
    return markup_runs(text, bold=True)


# Spaltenbreiten der SI-Tabellen (gemessen: 4.76 / 3.49 / 3.99 / 3.49 cm, weitere abwechselnd), twips
COL_PATTERN = (2700, 1980, 2265, 1980)


def col_widths(n):
    w = list(COL_PATTERN[:n]) + [COL_PATTERN[2 + (i % 2)] for i in range(max(0, n - len(COL_PATTERN)))]
    tot = sum(w)
    return [int(x * TEXT_W / tot) for x in w] if tot > TEXT_W else w


def _table(header, rows, widths, row_after=0, line=240, bold_rows=(), span_equal=(), width=None, size=20):
    """Dreilinien-Tabelle, alles zentriert. widths: Spaltenbreiten (twips). span_equal: Zeilenindizes, deren gleiche
    Werte über alle Spalten zusammengefasst werden (z. B. Refinement method). bold_rows: Zeilen mit fetten Werten."""
    tw = width or sum(widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    x = (f'<w:tbl><w:tblPr><w:tblW w:w="{tw}" w:type="dxa"/><w:jc w:val="center"/>'
         '<w:tblLayout w:type="fixed"/>'
         '<w:tblCellMar><w:left w:w="60" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>'
         f'<w:tblGrid>{grid}</w:tblGrid>')

    def cell(runs, w, sides, span=1, head=False):
        tcpr = f'<w:tcW w:w="{w}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{span}"/>' if span > 1 else "") + \
            _border(sides) + '<w:vAlign w:val="center"/>'
        sp = dict(line=240, after=0) if head else dict(line=line, before=row_after // 2, after=row_after // 2)
        return f"<w:tc><w:tcPr>{tcpr}</w:tcPr>" + _para(runs, size=size, align="center", **sp) + "</w:tc>"
    x += '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(
        cell(_head_runs(h), widths[j], ("top", "bottom"), head=True) for j, h in enumerate(header)) + "</w:tr>"
    n = len(rows)
    for i, r in enumerate(rows):
        sides = ("bottom",) if i == n - 1 else ()
        x += "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
        vals = r[1:]
        if i in span_equal and len(vals) > 1 and len(set(vals)) == 1:
            x += cell(markup_runs(r[0]), widths[0], sides) + cell(markup_runs(vals[0]), sum(widths[1:]), sides,
                                                                    span=len(vals))
        else:
            x += "".join(cell(markup_runs(c or "", bold=(j > 0 and i in bold_rows)), widths[j], sides)
                         for j, c in enumerate(r))
        x += "</w:tr>"
    return x + "</w:tbl>"


def _image_xml(rid, n, w_cm, h_cm, svg_rid=None):
    cx, cy = int(w_cm * 360000), int(h_cm * 360000)
    return ('<w:p>' + _ppr(align="center", line=240, after=120, keep_next=True) +
            '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Picture {n}"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{n}" name="image{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}">' +
            ('<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}"><asvg:svgBlip '
             'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" '
             f'r:embed="{svg_rid}"/></a:ext></a:extLst>' if svg_rid else "") +
            '</a:blip><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r></w:p>')


def _sect(columns):
    """Abschnittseigenschaften (A4, Ränder wie in der SI), fortlaufend, mit Spaltenzahl."""
    return ('<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" '
            'w:right="1417" w:bottom="1134" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/>' +
            (f'<w:cols w:num="{columns}" w:space="{COL_GAP}"/>' if columns > 1 else "") + '</w:sectPr>')


def write_docx(path, blocks, columns=1):
    """Blöcke:
    ("synthesis", Name)                   „Synthesis of <b>Name</b>“
    ("char", HTML)                        Charakterisierungsabsatz (Abstand davor wie in der SI)
    ("image", PNG, Breite cm, Höhe cm[, SVG])  Abbildung zentriert (SVG = Vektor, PNG als Ersatz)
    ("figcap", HTML)                      „Figure Sn: …“
    ("tabcap", Markup, Name)              „Table Sn: <Markup> <b>Name</b>.“
    ("crystal", Kopf, Zeilen)             Kristalldaten (erste Spalte breiter, Referenz fett, Methode zusammengefasst)
    ("params", Kopf, Zeilen)              Ausgewählte Bindungen/Winkel
    ("note", Markup)                      Fußnote unter einer Tabelle
    ("heading", Text)                     fette Überschrift (DFT: Name der Rechnung)
    ("text", HTML)                        linksbündiger Absatz, einzeilig (DFT-Angaben)
    ("coords", Kopf, Zeilen)              kompakte Tabelle (Konvergenz)
    ("fields", [HTML, …])                 eine Zeile, Felder auf Tabstopps verteilt (Charge / Multiplicity / Point group)
    ("mono", [Zeilen])                    Festbreitenschrift, Größe so, dass die längste Zeile in die Spalte passt
    ("energies", Köpfe, Zeilen)           Energietabelle über die Spaltenbreite
    ("columns", n)                        ab hier n Spalten (fortlaufender Abschnittswechsel, z. B. DFT zweispaltig)
    ("gap",)                              Leerzeile
    columns = Spalten am Anfang (2: ganzes Dokument zweispaltig wie die DFT-SI der Gruppe)"""
    body, media, svgs = [], [], []
    n_fig = n_tab = 0
    def col_width(n):
        return TEXT_W if n == 1 else (TEXT_W - COL_GAP * (n - 1)) // n
    col_w = col_width(columns)
    for b in blocks:
        k = b[0]
        if k == "columns":
            if b[1] != columns:                  # Abschnitt mit der bisherigen Spaltenzahl beenden
                body.append(f"<w:p><w:pPr>{_sect(columns)}</w:pPr></w:p>")
                columns = b[1]
                col_w = col_width(columns)
        elif k == "synthesis":
            body.append(_para([("Synthesis of ", set()), (b[1], {"b"})], keep_next=True))
        elif k == "char":
            body.append(_para(html_runs(nbsp(b[1])), before=200))
        elif k == "image":
            media.append(Path(b[1]))
            svg_rid = None
            if len(b) > 4 and b[4] and Path(b[4]).exists():
                svgs.append((len(media), Path(b[4])))
                svg_rid = f"rIdSvg{len(media)}"
            w_cm = min(b[2], col_w / 567.0)
            body.append(_image_xml(f"rIdImg{len(media)}", len(media), w_cm, b[3] * w_cm / b[2], svg_rid))
        elif k == "figcap":
            n_fig += 1
            body.append(_label_para("Figure", n_fig, html_runs(nbsp(b[1])), after=240))
        elif k == "tabcap":
            n_tab += 1
            body.append(_label_para("Table", n_tab, markup_runs(b[1]) + [(" ", set()), (b[2] + ".", {"b"})],
                                    before=120, after=120, keep_next=True))
        elif k == "crystal":
            header, rows = b[1], b[2]
            widths = col_widths(len(header))
            ref_row = [i for i, r in enumerate(rows) if r[0] == "Internal reference"]
            meth = [i for i, r in enumerate(rows) if r[0] == "Refinement method"]
            body.append(_table(header, rows, widths, row_after=64, bold_rows=ref_row, span_equal=meth))
        elif k == "params":
            header, rows = b[1], b[2]
            body.append(_table(header, rows, col_widths(len(header)), row_after=260))
        elif k == "note":
            body.append(_para(markup_runs(b[1]), size=18, line=240, after=0))
        elif k == "heading":
            body.append(_para([(b[1], {"b"})], align="left", before=240, after=120, keep_next=True))
        elif k == "text":
            body.append(_para(html_runs(nbsp(b[1])), align="left", line=240 if columns > 1 else 276, after=60,
                              size=18 if columns > 1 else 22))
        elif k == "coords":
            header, rows = b[1], b[2]
            n = len(header)
            w = [int(col_w * 0.27)] + [int(col_w * 0.6 / (n - 2))] * (n - 2) + [int(col_w * 0.13)] if n > 2 else \
                [col_w // n] * n
            body.append(_table(header, rows, w, line=240, size=14 if columns > 1 else 18))
            body.append(_para([("", set())], line=240))
        elif k == "fields":
            n = max(1, len(b[1]))
            tabs = "".join(f'<w:tab w:val="left" w:pos="{int(col_w * i / n)}"/>' for i in range(1, n))
            runs = []
            for i, h in enumerate(b[1]):
                if i:
                    runs.append(("\t", set()))
                runs += html_runs(h)
            body.append(_para(runs, align="left", line=240, before=60, after=60, tabs=tabs, size=18))
        elif k == "mono":
            lines = b[1] or [""]
            longest = max(len(ln) for ln in lines)
            # Courier: Zeichenbreite 0.6 × Schriftgröße; halbe Punkte, höchstens 8 pt
            size = max(10, min(16, int(2 * col_w / 20 / (0.6 * max(1, longest)))))
            for ln in lines:
                body.append(_para([(ln, {"mono"})], size=size, align="left", line=240))
        elif k == "energies":
            header, rows = b[1], b[2]
            n = len(header)
            body.append(_table(header, rows, [col_w // n] * n, line=240, size=16 if columns > 1 else 18))
            body.append(_para([("", set())], line=240))
        elif k == "gap":
            body.append(_para([("", set())]))
    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {ns}><w:body>' + "".join(body) + _sect(columns) + '</w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults>'
              f'<w:rPrDefault><w:rPr>{_FONT}<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-GB"/></w:rPr>'
              '</w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="360" w:lineRule="auto"/></w:pPr>'
              '</w:pPrDefault></w:docDefaults></w:styles>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
              '<Default Extension="svg" ContentType="image/svg+xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
              'wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/'
              'vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
             'styles" Target="styles.xml"/>' +
             "".join(f'<Relationship Id="rIdImg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                     f'relationships/image" Target="media/image{i}.png"/>' for i in range(1, len(media) + 1)) +
             "".join(f'<Relationship Id="rIdSvg{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                     f'relationships/image" Target="media/image{i}.svg"/>' for i, _ in svgs) +
             '</Relationships>')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)
        for i, m in enumerate(media, 1):
            z.writestr(f"word/media/image{i}.png", m.read_bytes())
        for i, sv in svgs:
            z.writestr(f"word/media/image{i}.svg", sv.read_bytes())
    return path
