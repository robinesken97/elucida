"""
elucida/si/excel.py - Excel-Report einer Verdünnungsreihe (neu aufgebaut 1.0, Nutzerwunsch „schön und übersichtlich“).

Blätter:
  Ergebnisse   eine Tabelle wie in der App (λ, ε ± SE, 95-%-KI, R², n, Hinweise), daneben ε aus den Excel-Formeln zur
               Kontrolle; zwei Diagramme im Stil der Abbildung (Spektren, A/d gegen c); die Angaben zur Messung
  Rechnung     alle Banden nebeneinander: Messpunkte mit „im Fit“ (1/0, änderbar), darunter die Regression als
               Excel-Formeln (Ergebnis oben, Zwischenwerte grau darunter)
  Spektren     A(λ) aller Proben, basislinienkorrigiert und roh (Daten des Spektrendiagramms)

Zahlen wie überall: ε/SE/KI über core.fmt_ve (`_coef_fmts`), R² mit core.R2_DIGITS, λ ganzzahlig. Die Zellen behalten
den vollen Wert, nur das Zahlenformat rundet.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.marker import Marker
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import CharacterProperties, Font as _DFont, Paragraph, ParagraphProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from elucida.core import uvvis as core
from elucida.app.i18n import get_lang


def _coef_fmts(r, cfg):
    """Zahlenformate für ε/a, SE und 95-%-KI wie in Tabelle, Bild und SI (core.fmt_ve) – überall dieselbe Zahl."""
    md = core.eps_max_decimals(cfg)

    def f(e):
        if not np.isfinite(r.get("eps", np.nan)):
            return "0"
        d = max(core.ve_decimals(r["eps"], e if e == e else None, max_decimals=md), 0)
        return "0" if d == 0 else "0." + "0" * d
    return f(r.get("eps_err")), f(r.get("eps_ci95"))


def _err_fmt(fmt):
    """Zahlenformat für SE/KI: ein Fehler, der auf 0 runden würde, zeigt wie `core.fmt_ve` die kleinste Einheit
    („± 1“, nie „± 0“); der Zellwert bleibt die Formel bzw. die Zahl."""
    d = len(fmt.split(".")[1]) if "." in fmt else 0
    return f'[<{0.5 * 10.0 ** -d:.{d + 1}f}]"{10.0 ** -d:.{d}f}";{fmt}'


# ---------------------------------------------------------------------------- Aussehen (nur hier)
FONT = "Arial"
INK, MUTED, ACCENT = "1A1A1A", "7A7A7A", "1F4E79"
F_BASE = Font(name=FONT, size=10, color=INK)
F_BOLD = Font(name=FONT, size=10, color=INK, bold=True)
F_MUTED = Font(name=FONT, size=10, color=MUTED)
F_TITLE = Font(name=FONT, size=16, color=INK, bold=True)
F_SECTION = Font(name=FONT, size=11, color=ACCENT, bold=True)
F_KEY = Font(name=FONT, size=11, color=INK, bold=True)
HEAD_FILL = PatternFill("solid", fgColor="EEF2F7")
KEY_FILL = PatternFill("solid", fgColor="EAF1FB")           # das Ergebnis (ε)
EDIT_FILL = PatternFill("solid", fgColor="FFF4CC")          # änderbare Zellen („im Fit“)
HAIR = Side(style="hair", color="BFC5CC")
RULE = Side(style="thin", color="5B6775")
ROW_LINE = Border(bottom=HAIR)
HEAD_LINE = Border(bottom=RULE)
CENTER = Alignment(horizontal="center", vertical="center")
LEFT = Alignment(horizontal="left", vertical="center")
WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)
ROW_H = 18

TXT = {
    "results": ("Ergebnisse", "Results"), "calc": ("Rechnung", "Calculation"), "spectra": ("Spektren", "Spectra"),
    "title": ("UV-Vis: Extinktionskoeffizienten", "UV-Vis: extinction coefficients"),
    "title_a": ("UV-Vis: spezifische Absorptionskoeffizienten", "UV-Vis: specific absorption coefficients"),
    "lam": ("λ [nm]", "λ [nm]"), "se": ("± SE", "± SE"), "ci": ("± 95-%-KI", "± 95 % CI"), "r2": ("R²", "R²"),
    "n": ("n", "n"), "check": ("{sym} (Excel)", "{sym} (Excel)"), "notes": ("Hinweise", "Notes"),
    "sh": ("Schulter", "shoulder"),
    "check_note": ("{sym} (Excel): unabhängig mit Excel-Formeln nachgerechnet (Blatt „{calc}“).",
                   "{sym} (Excel): recalculated independently with Excel formulas (sheet “{calc}”)."),
    "excl": ("nicht im Fit", "not in fit"),
    "info": ("Angaben", "Details"), "series": ("Serie", "Series"), "date": ("Erstellt", "Created"),
    "files": ("Messdateien", "Measurement files"), "unit": ("Konzentrationseinheit", "Concentration unit"),
    "mw": ("Molmasse M [g mol⁻¹]", "Molar mass M [g mol⁻¹]"), "d": ("Schichtdicke d [cm]", "Path length d [cm]"),
    "cut": ("Cutoff A (Fit)", "Cutoff A (fit)"), "minpts": ("min. Fitpunkte", "min. fit points"),
    "model": ("Modell", "Model"), "model_b": ("A/d = m·c + b", "A/d = m·c + b"),
    "model_0": ("A/d = m·c (durch den Ursprung)", "A/d = m·c (through the origin)"),
    "bl": ("Basislinie", "Baseline"), "bl_window": ("Fenster {a:.0f}–{b:.0f} nm", "window {a:.0f}–{b:.0f} nm"),
    "program": ("Programm", "Program"),
    "calc_title": ("Regression je Bande", "Regression per band"),
    "calc_hint": ("Gelbe Zellen („im Fit“: 1 oder 0) lassen sich ändern, Excel rechnet die Bande neu.",
                  "Yellow cells (“in fit”: 1 or 0) can be changed; Excel recalculates the band."),
    "fc": ("f_c", "f_c"), "fc_note": ("c [mol L⁻¹] = c · f_c", "c [mol L⁻¹] = c · f_c"),
    "fc_note_a": ("c [g L⁻¹] = c · f_c", "c [g L⁻¹] = c · f_c"),
    "points": ("Messpunkte", "Data points"), "sample": ("Probe", "Sample"), "A": ("A", "A"),
    "Ad": ("A/d [cm⁻¹]", "A/d [cm⁻¹]"), "w": ("im Fit", "in fit"),
    "reg": ("Regression", "Regression"), "slope": ("Steigung m", "Slope m"), "icpt": ("Achsenabschnitt b", "Intercept b"),
    "mid": ("Zwischenwerte", "Intermediate values"),
    "method": ("Methode", "Method"),
    "corr": ("basislinienkorrigiert", "baseline-corrected"), "raw": ("roh", "raw"),
    "offset": ("abgezogener Offset", "subtracted offset"), "wl": ("λ [nm]", "λ [nm]"),
}
METHOD = {
    "de": ["Lambert-Beer: A = ε · c · d. Je Bande wird A/d gegen c linear angepasst (kleinste Quadrate), nur mit den "
           "Punkten „im Fit“ = 1.",
           "ε = m / f_c,  SE(ε) = SE(m) / f_c,  95-%-KI = t(0,975; n − p) · SE(ε);  p = Zahl der Fitparameter.",
           "SE(m) = s / √Sxx mit s = √(RSS / (n − p));  R² = 1 − RSS / Σ(y − ȳ)²."],
    "en": ["Beer–Lambert: A = ε · c · d. For every band, A/d is fitted linearly against c (least squares), only with "
           "the points “in fit” = 1.",
           "ε = m / f_c,  SE(ε) = SE(m) / f_c,  95 % CI = t(0.975; n − p) · SE(ε);  p = number of fit parameters.",
           "SE(m) = s / √Sxx with s = √(RSS / (n − p));  R² = 1 − RSS / Σ(y − ȳ)²."],
}


def t(key, **kw):
    de, en = TXT[key]
    s = en if get_lang() == "en" else de
    return s.format(**kw) if kw else s


def _num(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _put(ws, row, col, value=None, font=F_BASE, fmt=None, align=CENTER, fill=None, border=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font, c.alignment = font, align
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if border:
        c.border = border
    return c


def _head(ws, row, col, labels, left=()):
    """Kopfzeile einer Tabelle: fett, zarter Grund, Linie darunter."""
    for j, lab in enumerate(labels):
        _put(ws, row, col + j, lab, F_BOLD, align=LEFT if j in left else CENTER, fill=HEAD_FILL, border=HEAD_LINE)
    ws.row_dimensions[row].height = ROW_H + 2


def _sheet(ws, widths, landscape=False):
    """Blatt ohne Gitter, feste Spaltenbreiten, Druck auf eine Seitenbreite."""
    ws.sheet_view.showGridLines = False
    for i, wd in enumerate(widths, 1):
        ws.column_dimensions[L(i)].width = wd
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def _rgb(color):
    """Farbe der Abbildung (Name oder #hex) -> RRGGBB für Excel."""
    from matplotlib.colors import to_hex
    try:
        return to_hex(color)[1:].upper()
    except ValueError:
        return "000000"


def _plain(text):
    """Achsentext der Abbildung ohne Mathtext-Zeichen (Excel-Titel sind reiner Text): cm$^{-1}$ -> cm⁻¹."""
    import re
    sup = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
    text = re.sub(r"\$\^\{?([-+0-9]+)\}?\$", lambda m: m.group(1).translate(sup), str(text))
    return text.replace("$", "")


def _chart_text(size):
    cp = CharacterProperties(latin=_DFont(typeface=FONT), sz=int(size * 100), b=False, solidFill="000000")
    par = Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)
    par.r = []                                             # openpyxl legt sonst einen leeren Textlauf an
    return cp, RichText(p=[par])


def _chart(cfg, x_title, y_title, width, height, ticks, size=10):
    """Diagramm im Stil der Abbildungen (Nutzerwunsch: „nahezu identisch zu den internen Graphen“): weißer Grund, schwarze
    Achsen, geschlossener Rahmen wie im Bild, Striche nach innen/außen wie dort, keine Gitterlinien, kein Titel, Arial."""
    ch = ScatterChart()
    ch.style = 2
    ch.width, ch.height = width, height
    cp, rich = _chart_text(size)
    line = LineProperties(solidFill="000000", w=9525)
    for ax, title in ((ch.x_axis, x_title), (ch.y_axis, y_title)):
        ax.title = _plain(title)
        ax.title.overlay = False                           # Titel neben der Zeichenfläche, nicht darauf
        ax.delete = False
        ax.majorGridlines = None
        ax.majorTickMark = ax.minorTickMark = ticks
        ax.spPr = GraphicalProperties(ln=line)
        ax.txPr = rich
        for par in ax.title.tx.rich.p:                       # Achsentitel: gleiche Schrift, etwas größer, nicht fett
            tp = CharacterProperties(latin=_DFont(typeface=FONT), sz=int(size * 120), b=False, solidFill="000000")
            par.pPr = ParagraphProperties(defRPr=tp)
            for run in par.r or []:
                run.rPr = tp
    frame = cfg.get("axes_frame", True)
    ch.plot_area.spPr = GraphicalProperties(noFill=True, ln=line if frame else LineProperties(noFill=True))
    ch.graphical_properties = GraphicalProperties(solidFill="FFFFFF", ln=LineProperties(noFill=True))
    ch.legend.position = "r"
    ch.legend.overlay = False
    ch.legend.txPr = _chart_text(size * 0.9)[1]
    return ch


def _line(series, color, width_pt=1.0):
    series.marker = Marker(symbol="none")
    series.smooth = False
    series.graphicalProperties.line.solidFill = color
    series.graphicalProperties.line.width = int(width_pt * 12700)


def _dots(series, color, hollow=False):
    series.marker = Marker(symbol="square", size=6)          # Quadrate wie im Inset der Abbildung
    series.marker.graphicalProperties.line.solidFill = color
    if hollow:
        series.marker.graphicalProperties.noFill = True
    else:
        series.marker.graphicalProperties.solidFill = color
    series.graphicalProperties.line.noFill = True


def _band_colors(cfg, n):
    cols = [_rgb(c) for c in (cfg.get("inset") or {}).get("colors") or ["#000000"]]
    return [cols[i % len(cols)] for i in range(n)]


def _spectrum_colors(cfg, spectra):
    """Kurvenfarben wie in der Abbildung: eigene Farbe der Messung, sonst der Verlauf nach Konzentration, sonst die
    Linienfarbe."""
    ramp = core.conc_ramp([s_["c"] for s_ in spectra]) if cfg.get("conc_colors") else {}
    return [_rgb(s_.get("color") or ramp.get(s_.get("c")) or cfg.get("line_color", "#000000")) for s_ in spectra]


def write_report(path, cfg, raw_spectra, spectra, results, series, files=(), version=""):
    """raw_spectra: Spektren vor der Basislinie; spectra/results/cfg aus core.prepare_series."""
    sym = "ε" if core.coeff_symbol_unit(cfg)[0] == "ε" else "a"
    coef_unit = "M⁻¹ cm⁻¹" if sym == "ε" else "L g⁻¹ cm⁻¹"
    unit = core.unit_text(cfg["conc_unit"])
    wb = Workbook()
    ws = wb.active
    ws.title = t("results")
    cs = wb.create_sheet(t("calc"))
    calc = _calc_sheet(cs, cfg, spectra, results, unit, sym, coef_unit)
    spec = _spectra_sheet(wb.create_sheet(t("spectra")), cfg, raw_spectra, spectra, unit)
    _results_sheet(ws, cs, calc, spec, cfg, results, series, files, version, unit, sym, coef_unit)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


# ---------------------------------------------------------------------------- Blatt „Rechnung“
REG_ROWS = ("n", "m", "b", "r2", "eps", "se_eps", "ci")                       # Ergebnis der Regression
MID_ROWS = ("xbar", "ybar", "sxx", "sxy", "rss", "s", "se_m", "se_b", "t")    # Zwischenwerte


def _calc_sheet(cs, cfg, spectra, results, unit, sym, coef_unit):
    """Alle Banden nebeneinander (je drei Spalten: A, A/d, im Fit), darunter die Regression als Formeln.
    -> dict(first, last, bands=[dict(col, rows)], x, helper) für Ergebnisblatt und Diagramm."""
    nb = len(results)
    _sheet(cs, [2, 26, 13] + [11, 12, 9] * nb + [2], landscape=True)
    _put(cs, 2, 2, t("calc_title"), F_TITLE, align=LEFT)
    _put(cs, 3, 2, t("calc_hint"), F_MUTED, align=LEFT)
    cs.row_dimensions[2].height = 26
    # Angaben, auf die die Formeln zugreifen
    _put(cs, 5, 2, t("info"), F_SECTION, align=LEFT)
    icpt = bool(cfg["fit_intercept"])
    mw = _num(cfg.get("molar_mass_g_mol"))
    R_D, R_FC, R_MW, R_MIN = 6, 7, 8, 9
    for row, lab, val, fmt in ((R_D, t("d"), float(cfg["path_length_cm"]), "General"),
                               (R_MW, t("mw"), mw if mw is not None else "–", "0.00"),
                               (R_MIN, t("minpts"), int(cfg["min_fit_points"]), "0")):
        _put(cs, row, 2, lab, align=LEFT, border=ROW_LINE)
        _put(cs, row, 3, val, fmt=fmt, border=ROW_LINE)
    _put(cs, R_FC, 2, t("fc"), align=LEFT, border=ROW_LINE)
    if cfg["conc_unit"] == "mg/mL":                         # über die Molmasse; ohne M: spezifischer Koeffizient
        fc = f'=IF(ISNUMBER(C{R_MW}),1/C{R_MW},1)'
    else:
        fc = {"mM": 1e-3, "uM": 1e-6, "M": 1.0}.get(cfg["conc_unit"], 1.0)
    _put(cs, R_FC, 3, fc, fmt="0.000E+00", border=ROW_LINE)
    _put(cs, R_FC, 4, t("fc_note" if sym == "ε" else "fc_note_a"), F_MUTED, align=LEFT)
    # Messpunkte
    R_SEC, R_BAND, R_HEAD = 11, 12, 13
    first = R_HEAD + 1
    pts = sorted(spectra, key=lambda s_: s_["c"])
    last = first + max(len(pts), 1) - 1
    _put(cs, R_SEC, 2, t("points"), F_SECTION, align=LEFT)
    _head(cs, R_HEAD, 2, [t("sample"), f"c [{unit}]"], left=(0,))
    for i, s_ in enumerate(pts):
        _put(cs, first + i, 2, s_.get("name", ""), align=LEFT, border=ROW_LINE)
        _put(cs, first + i, 3, float(s_["c"]), fmt="General", border=ROW_LINE)
        cs.row_dimensions[first + i].height = ROW_H
    X = f"$C${first}:$C${last}"
    R_REG = last + 2                                        # Abschnitt „Regression“
    rows = {k: R_REG + 1 + i for i, k in enumerate(REG_ROWS)}
    R_CUT = rows["ci"] + 1
    R_MID = R_CUT + 2
    rows.update({k: R_MID + 1 + i for i, k in enumerate(MID_ROWS)})
    labels = {"n": "n", "m": t("slope"), "b": t("icpt"), "r2": "R²", "eps": f"{sym} [{coef_unit}]",
              "se_eps": f"SE({sym})", "ci": t("ci"), "xbar": "x̄", "ybar": "ȳ", "sxx": "Sxx", "sxy": "Sxy",
              "rss": "RSS", "s": "s", "se_m": "SE(m)", "se_b": "SE(b)", "t": "t(0.975; n − p)"}
    _put(cs, R_REG, 2, t("reg"), F_SECTION, align=LEFT)
    _put(cs, R_MID, 2, t("mid"), F_SECTION, align=LEFT)
    for k in REG_ROWS:
        _put(cs, rows[k], 2, labels[k], F_KEY if k == "eps" else F_BASE, align=LEFT, border=ROW_LINE,
             fill=KEY_FILL if k == "eps" else None)
        _put(cs, rows[k], 3, None, border=ROW_LINE, fill=KEY_FILL if k == "eps" else None)
    _put(cs, R_CUT, 2, t("cut"), F_MUTED, align=LEFT)
    for k in MID_ROWS:
        _put(cs, rows[k], 2, labels[k], F_MUTED, align=LEFT)
    p = 2 if icpt else 1
    bands = []
    colors = _band_colors(cfg, nb)
    # Verborgene Spalten für das Diagramm: LX/LY alle Regressionsgeraden als eine Reihe (je Bande zwei Punkte, dann eine
    # leere Zeile = Lücke), EX/EY die Punkte außerhalb des Fits aller Banden, danach je Bande die Punkte im Fit.
    # Eine Reihe je Gerade ergäbe je einen Legendeneintrag; einzelne Einträge auszublenden ignoriert Excel (geprüft).
    helper0 = 4 + 3 * nb + 2
    LX, LY, EX, EY = helper0, helper0 + 1, helper0 + 2, helper0 + 3
    xmax = max((float(s_["c"]) for s_ in pts), default=1.0)
    any_excluded = False
    for k, r in enumerate(results):
        c0 = 4 + 3 * k
        cA, cY, cW = L(c0), L(c0 + 1), L(c0 + 2)
        used = {round(c, 12) for c, _ in r["used"]}
        cs.merge_cells(start_row=R_BAND, start_column=c0, end_row=R_BAND, end_column=c0 + 2)
        lam_txt = f"{core.fmt_lam(r['lam'])} nm" + (f" ({t('sh')})" if r.get("shoulder") else "")
        _put(cs, R_BAND, c0, lam_txt, Font(name=FONT, size=10, bold=True, color=colors[k]))
        _head(cs, R_HEAD, c0, [t("A"), t("Ad"), t("w")])
        for i, s_ in enumerate(pts):
            row = first + i
            A = _num(core.abs_at(s_["x"], s_["y"], r["lam"], cfg["avg_window_nm"]))
            _put(cs, row, c0, A, fmt="0.0000", border=ROW_LINE)
            _put(cs, row, c0 + 1, f"={cA}{row}/$C${R_D}", fmt="0.0000", border=ROW_LINE)
            _put(cs, row, c0 + 2, 1 if (A is not None and round(s_["c"], 12) in used) else 0, fmt="0",
                 fill=EDIT_FILL, border=ROW_LINE)
        Y, W = f"${cY}${first}:${cY}${last}", f"${cW}${first}:${cW}${last}"
        v = {k_: f"{cY}{rows[k_]}" for k_ in rows}          # Zelle je Größe dieser Bande
        f = {
            "n": f"=SUM({W})",
            "xbar": f'=IF({v["n"]}>0,SUMPRODUCT({W},{X})/{v["n"]},"")',
            "ybar": f'=IF({v["n"]}>0,SUMPRODUCT({W},{Y})/{v["n"]},"")',
            "sxx": f'=IFERROR(SUMPRODUCT({W},({X}-{v["xbar"]})^2),"")',
            "sxy": f'=IFERROR(SUMPRODUCT({W},({X}-{v["xbar"]}),({Y}-{v["ybar"]})),"")',
            "rss": f'=IFERROR(SUMPRODUCT({W},({Y}-({v["m"]}*{X}+{v["b"]}))^2),"")',
            "s": f'=IF({v["n"]}>{p},IFERROR(SQRT({v["rss"]}/({v["n"]}-{p})),""),"")',
            "r2": f'=IF({v["n"]}>1,IFERROR(1-{v["rss"]}/SUMPRODUCT({W},({Y}-{v["ybar"]})^2),""),"")',
            "eps": f'=IF({v["n"]}>=$C${R_MIN},IFERROR({v["m"]}/$C${R_FC},""),"")',
            "se_eps": f'=IFERROR({v["se_m"]}/$C${R_FC},"")',
            "t": f'=IF({v["n"]}>{p},TINV(0.05,{v["n"]}-{p}),"")',
            "ci": f'=IFERROR({v["t"]}*{v["se_eps"]},"")',
        }
        if icpt:
            f.update(m=f'=IFERROR({v["sxy"]}/{v["sxx"]},"")', b=f'=IFERROR({v["ybar"]}-{v["m"]}*{v["xbar"]},"")',
                     se_m=f'=IFERROR({v["s"]}/SQRT({v["sxx"]}),"")',
                     se_b=f'=IFERROR({v["s"]}*SQRT(1/{v["n"]}+{v["xbar"]}^2/{v["sxx"]}),"")')
        else:
            f.update(m=f'=IFERROR(SUMPRODUCT({W},{X},{Y})/SUMPRODUCT({W},{X},{X}),"")', b="=0",
                     se_m=f'=IFERROR({v["s"]}/SQRT(SUMPRODUCT({W},{X},{X})),"")', se_b='="–"')
        f_v, f_ci = _coef_fmts(r, cfg)
        sci_ = "0.000E+00"                                  # Steigung und Fehler: Größenordnung hängt von der Einheit ab
        fmts = {"n": "0", "m": sci_, "b": sci_, "r2": "0.0000", "eps": f_v, "se_eps": _err_fmt(f_v), "ci": _err_fmt(f_ci), "sxx": sci_,
                "sxy": sci_, "rss": sci_, "s": sci_, "se_m": sci_, "se_b": sci_, "t": "0.000"}
        for k_ in REG_ROWS:
            for cc in (c0, c0 + 2):
                _put(cs, rows[k_], cc, None, border=ROW_LINE, fill=KEY_FILL if k_ == "eps" else None)
            _put(cs, rows[k_], c0 + 1, f[k_], F_KEY if k_ == "eps" else F_BASE, fmt=fmts.get(k_, "0.0000"),
                 border=ROW_LINE, fill=KEY_FILL if k_ == "eps" else None)
        _put(cs, R_CUT, c0 + 1, float(r.get("cutoff", cfg["max_abs_fit"])), F_MUTED, fmt="0.00")
        for k_ in MID_ROWS:
            _put(cs, rows[k_], c0 + 1, f[k_], F_MUTED, fmt=fmts.get(k_, "0.0000"))
        # Diagrammdaten (verborgen): Punkte im Fit, Punkte außerhalb, Regressionsgerade
        hU = helper0 + 4 + k
        for i in range(len(pts)):
            row = first + i
            _put(cs, row, hU, f"=IF({cW}{row}=1,{cY}{row},NA())")
            erow = first + k * len(pts) + i
            _put(cs, erow, EX, f"=$C${row}")
            _put(cs, erow, EY, f"=IF(AND({cW}{row}<>1,ISNUMBER({cA}{row})),{cY}{row},NA())")
            any_excluded |= cs.cell(row=row, column=c0 + 2).value == 0 and cs.cell(row=row, column=c0).value is not None
        for j, xv in enumerate((0.0, xmax)):
            lrow = first + 3 * k + j
            _put(cs, lrow, LX, xv)
            _put(cs, lrow, LY, f'=IFERROR({v["m"]}*{L(LX)}{lrow}+{v["b"]},NA())')
        bands.append(dict(col=cY, rows=rows, hU=hU))
    for col in range(helper0, helper0 + 4 + nb):
        cs.column_dimensions[L(col)].hidden = True
    # Methode in drei Zeilen
    R_M = rows["t"] + 2
    _put(cs, R_M, 2, t("method"), F_SECTION, align=LEFT)
    for i, line in enumerate(METHOD["en" if get_lang() == "en" else "de"]):
        _put(cs, R_M + 1 + i, 2, line, F_MUTED, align=LEFT)
    return dict(first=first, last=last, n=len(pts), bands=bands, line=(LX, LY, first, first + max(3 * nb - 2, 1)),
                excluded=(EX, EY, first, first + max(nb * len(pts), 1) - 1) if any_excluded else None)


# ---------------------------------------------------------------------------- Blatt „Ergebnisse“
def _results_sheet(ws, cs, calc, spec, cfg, results, series, files, version, unit, sym, coef_unit):
    _sheet(ws, [2, 12, 16, 12, 12, 9, 7, 14, 46])
    _put(ws, 2, 2, t("title" if sym == "ε" else "title_a"), F_TITLE, align=LEFT)
    _put(ws, 3, 2, str(series), F_MUTED, align=LEFT)
    ws.row_dimensions[2].height = 26
    R_HEAD = 5
    _head(ws, R_HEAD, 2, [t("lam"), f"{sym} [{coef_unit}]", t("se"), t("ci"), t("r2"), t("n"), t("check", sym=sym),
                          t("notes")], left=(7,))
    r2_fmt = "0." + "0" * core.R2_DIGITS
    for i, (r, band) in enumerate(zip(results, calc["bands"])):
        row = R_HEAD + 1 + i
        ft = r["fit"]
        f_v, f_ci = _coef_fmts(r, cfg)
        notes = ([t("sh").capitalize()] if r.get("shoulder") else []) + list(r.get("warnings") or [])
        vals = [(_num(r["lam"]), "0", F_BOLD), (_num(r.get("eps")), f_v, F_KEY), (_num(r.get("eps_err")), _err_fmt(f_v), F_BASE),
                (_num(r.get("eps_ci95")), _err_fmt(f_ci), F_BASE), (_num(ft and ft["r2"]), r2_fmt, F_BASE),
                (ft["n"] if ft else len(r["used"]), "0", F_BASE)]
        for j, (v, fmt, font) in enumerate(vals):
            _put(ws, row, 2 + j, "–" if v is None else v, font, fmt=fmt, border=ROW_LINE,
                 fill=KEY_FILL if j == 1 else None)
        _put(ws, row, 8, f"=IFERROR('{cs.title}'!{band['col']}{band['rows']['eps']},\"–\")", F_MUTED, fmt=f_v,
             border=ROW_LINE)
        _put(ws, row, 9, "; ".join(notes), F_MUTED, align=WRAP, border=ROW_LINE)
        ws.row_dimensions[row].height = ROW_H * max(1, -(-len("; ".join(notes)) // 52))
    row = R_HEAD + len(results) + 2
    _put(ws, row, 2, t("check_note", sym=sym, calc=cs.title), F_MUTED, align=LEFT)
    # Diagramme wie die Abbildung: links die Spektren, rechts A/d gegen c (das Inset)
    R_CHART = row + 2
    w_in, h_in = cfg.get("figsize_in") or (6.3, 4.33)
    w_cm = 16.0
    h_cm = round(w_cm * h_in / w_in, 1)
    ticks = "in" if cfg.get("tick_direction", "in") == "in" else "out"
    ss = spec["sheet"]
    if spec["n"]:
        ch = _chart(cfg, cfg.get("xlabel") or "wavelength [nm]", cfg.get("ylabel") or "absorbance [a.u.]", w_cm, h_cm,
                    ticks)
        xlim, ylim = spec["xlim"], spec["ylim"]
        ch.x_axis.scaling.min, ch.x_axis.scaling.max = float(min(xlim)), float(max(xlim))
        ch.y_axis.scaling.min, ch.y_axis.scaling.max = float(min(ylim)), float(max(ylim))
        ch.x_axis.number_format, ch.y_axis.number_format = "0", "0.0"
        xref = Reference(ss, min_col=spec["x_col"], min_row=spec["first"], max_row=spec["last"])
        for j, color in enumerate(spec["colors"]):
            s = Series(Reference(ss, min_col=spec["col0"] + j, min_row=spec["first"] - 1, max_row=spec["last"]), xref,
                       title_from_data=True)
            _line(s, color, cfg.get("line_width", 1.0))
            ch.series.append(s)
        if len(set(spec["colors"])) < 2 and not cfg.get("conc_legend"):
            ch.legend = None                                # eine Farbe für alle Kurven: Legende sagt nichts
        ws.add_chart(ch, f"B{R_CHART}")
    ch = _chart(cfg, (cfg.get("inset") or {}).get("xlabel") or f"c [{unit}]", "A/d [cm⁻¹]", 8.6, h_cm, "out", size=9)
    ch.visible_cells_only = False                           # Diagrammdaten stehen in verborgenen Spalten
    ch.x_axis.scaling.min = 0
    ch.y_axis.scaling.min = 0
    first, last = calc["first"], calc["last"]
    xref = Reference(cs, min_col=3, min_row=first, max_row=last)
    colors = _band_colors(cfg, len(results))
    for k, (r, band) in enumerate(zip(results, calc["bands"])):
        s = Series(Reference(cs, min_col=band["hU"], min_row=first, max_row=last), xref,
                   title=f"{core.fmt_lam(r['lam'])} nm")
        _dots(s, colors[k])
        ch.series.append(s)
    if calc["excluded"]:
        ex, ey, r0, r1 = calc["excluded"]
        s = Series(Reference(cs, min_col=ey, min_row=r0, max_row=r1), Reference(cs, min_col=ex, min_row=r0, max_row=r1),
                   title=t("excl"))
        _dots(s, "7F7F7F", hollow=True)
        ch.series.append(s)
    if results:
        lx, ly, r0, r1 = calc["line"]
        s = Series(Reference(cs, min_col=ly, min_row=r0, max_row=r1), Reference(cs, min_col=lx, min_row=r0, max_row=r1),
                   title=t("reg"))
        _line(s, "000000", 0.9)
        ch.series.append(s)
    ch.legend.position = "b"
    ws.add_chart(ch, f"I{R_CHART}")
    # Angaben zur Messung
    R_INFO = R_CHART + int(h_cm / 0.53) + 2                 # unter den Diagrammen (Zeilenhöhe 15 pt = 0,53 cm)
    _put(ws, R_INFO, 2, t("info"), F_SECTION, align=LEFT)
    bl = cfg.get("_baseline_info") or {}
    mw = _num(cfg.get("molar_mass_g_mol"))
    info = [(t("unit"), unit, None),
            (t("d"), float(cfg["path_length_cm"]), "General"),
            (t("mw"), mw if mw is not None else "–", "0.00"),
            (t("model"), t("model_b" if cfg["fit_intercept"] else "model_0"), None),
            (t("cut"), float(cfg["max_abs_fit"]), "0.00"),
            (t("bl"), t("bl_window", a=bl["window"][0], b=bl["window"][1]) if bl.get("window") else "–", None),
            (t("files"), ", ".join(Path(f).name for f in files) or "–", None),
            (t("date"), _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), None),
            (t("program"), f"Elucida {version}".strip(), None)]
    for i, (lab, val, fmt) in enumerate(info):
        row = R_INFO + 1 + i
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=9)
        _put(ws, row, 2, lab, F_MUTED, align=LEFT, border=ROW_LINE)
        _put(ws, row, 3, None, border=ROW_LINE)
        _put(ws, row, 4, val, fmt=fmt, align=LEFT, border=ROW_LINE)
        for col in range(5, 10):
            _put(ws, row, col, None, border=ROW_LINE)
        ws.row_dimensions[row].height = ROW_H


# ---------------------------------------------------------------------------- Blatt „Spektren“
def _spectra_sheet(ss, cfg, raw_spectra, spectra, unit):
    """λ | korrigierte Spektren | Lücke | Rohspektren, höchste Konzentration zuerst; darüber der abgezogene Offset."""
    n = len(spectra)
    _sheet(ss, [2, 20] + [12] * n + [2] + [12] * n + [2], landscape=True)
    order = sorted(range(n), key=lambda i: -spectra[i]["c"])
    xs = spectra[order[0]]["x"] if spectra else np.array([])
    raw_by_name = {s_.get("name"): s_ for s_ in raw_spectra}
    c_corr, c_raw = 3, 3 + n + 1
    R_GROUP, R_OFF, R_HEAD = 2, 3, 4
    for c0, key in ((c_corr, "corr"), (c_raw, "raw")):
        if n:
            ss.merge_cells(start_row=R_GROUP, start_column=c0, end_row=R_GROUP, end_column=c0 + n - 1)
            _put(ss, R_GROUP, c0, t(key), F_SECTION)
    offs = (cfg.get("_baseline_info") or {}).get("offsets")
    if offs is not None and len(offs) == n:
        _put(ss, R_OFF, 2, t("offset"), F_MUTED, align=Alignment(horizontal="right", vertical="center"))
        for j, i in enumerate(order):
            _put(ss, R_OFF, c_corr + j, float(offs[i]), F_MUTED, fmt="0.0000")
    names = [f"{spectra[i]['c']:g} {unit}" for i in order]
    _head(ss, R_HEAD, 2, [t("wl")] + names)
    _head(ss, R_HEAD, c_raw, names)
    for k, x in enumerate(xs):
        row = R_HEAD + 1 + k
        _put(ss, row, 2, float(x), fmt="0.###")
        for j, i in enumerate(order):
            s_ = spectra[i]
            _put(ss, row, c_corr + j, round(float(np.interp(x, s_["x"], s_["y"])), 6), fmt="0.0000")
            rs = raw_by_name.get(s_.get("name"))
            if rs is not None:
                _put(ss, row, c_raw + j, round(float(np.interp(x, rs["x"], rs["y"])), 6), F_MUTED, fmt="0.0000")
    last = R_HEAD + len(xs)
    ss.freeze_panes = ss.cell(row=R_HEAD + 1, column=3)

    xlim = cfg.get("xlim") or ((float(xs.min()), float(xs.max())) if len(xs) else (0.0, 1.0))
    ylim = cfg.get("ylim") or (0.0, float(cfg["max_abs_fit"]))
    colors = _spectrum_colors(cfg, [spectra[i] for i in order])
    return dict(sheet=ss, n=n if len(xs) else 0, x_col=2, col0=c_corr, first=R_HEAD + 1, last=last, xlim=xlim,
                ylim=ylim, colors=colors)
