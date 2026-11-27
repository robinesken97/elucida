"""elucida/tabs/nmr.py - NMR für die SI: Spektren als Mnova-SVG, NMR-Zeile aus dem Mnova-Multiplettbericht, Parameter aus Bruker.

Auswertung bleibt in MestReNova. Hier: SVG-Exporte einsammeln (Kern aus der Achsenbeschriftung „δ ¹H (ppm)“, sonst von
Hand; 2D, wenn eine senkrechte δ-Achse vorkommt; Art aus dem Dateinamen), sortieren (¹H, ¹³C, übrige Kerne nach
Massenzahl, dann 2D), Bildunterschriften im Stil der SI („Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of Name.“),
Word-Seiten mit zwei Spektren. Mnova-Text („1H NMR (501 MHz, CDCl3) δ 7.52 – 7.45 (m, 2H), …“) wird in Signale
zerlegt, je Signal eine Zuordnung ergänzt und als „¹H NMR (500 MHz, CDCl₃): δ [ppm] = … (m, 2H, Zuordnung)“
ausgegeben. Werte bleiben Text wie im Bericht. Bruker acqus/acqu2s (JCAMP) liefern T, SFO1, O1P, SW, NS … zur Kontrolle.
"""
from __future__ import annotations

import html as _h
import re
import uuid
from pathlib import Path

import numpy as np

from elucida.app.canvas_theme import suspend as suspend_canvas
from elucida.tabs import xray as XRAY
from elucida.app.i18n import T
from elucida.formats.topspin import (read_jcamp_params, acq_params, bruker_dir, find_experiments, experiment_kind, experiment_name, parse_nucleus)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.mnova import (svg_info, svg_peaks, emf_info, is_emf, is_nmr_svg, spectrum_info, _NUC)  # noqa: E402,F401  (Leser in elucida/formats)

KINDS_2D = ("COSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "TOCSY", "HOESY", "INADEQUATE", "2D")
_KIND_ORDER = {k: i for i, k in enumerate(("COSY", "TOCSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "HOESY",
                                           "INADEQUATE", "2D"))}


# ---------------------------------------------------------------------------- Kerne


def nuc_mass(nuc):
    m = re.match(r"(\d+)", nuc or "")
    return int(m.group(1)) if m else 999


def nuc_markup(nuc):
    """„13C“ -> „^{13}C“ (Auszeichnung wie im X-Ray-Tab)."""
    m = re.match(r"(\d+)([A-Za-z]+)", nuc or "")
    return f"^{{{m.group(1)}}}{m.group(2)}" if m else str(nuc or "")


def nuc_rank(nuc):
    """¹H zuerst, dann ¹³C, dann die übrigen Kerne nach Massenzahl."""
    return 0 if nuc == "1H" else 1 if nuc == "13C" else 2 + nuc_mass(nuc)


def sort_key(spec):
    nuc = spec.get("nuclei") or []
    if spec.get("kind", "1D") == "1D":
        return (0, nuc_rank(nuc[0] if nuc else ""), 0)
    return (1, _KIND_ORDER.get(spec.get("kind"), 99), sum(nuc_rank(n) for n in nuc))


def kind_from_name(name):
    up = Path(name).stem.upper()
    for k in KINDS_2D[:-1]:
        if k in up:
            return k
    return None


# ---------------------------------------------------------------------------- SVG


# Larmorfrequenz relativ zu ¹H (für die Nennfrequenz anderer Kerne, wenn kein Bruker-Ordner da ist)
GAMMA_REL = {"2H": 0.15351, "7Li": 0.38864, "11B": 0.32084, "13C": 0.25145, "15N": 0.10137, "19F": 0.94094,
             "27Al": 0.26057, "29Si": 0.19867, "31P": 0.40481, "77Se": 0.19072, "103Rh": 0.03186, "117Sn": 0.35632,
             "119Sn": 0.37291, "125Te": 0.31549, "195Pt": 0.21496, "199Hg": 0.17911}


def svg_png(svg, png, dpi=200):
    """PNG-Ersatz für Word (das SVG selbst bleibt die eigentliche Grafik)."""
    import pymupdf
    pymupdf.open(str(svg))[0].get_pixmap(dpi=dpi).save(str(png))
    return Path(png)


# ---------------------------------------------------------------------------- Bruker-Parameter


def spectrum_kind(spec):
    """Art eines Mnova-Spektrums im Sinne von experiment_kind (1D: Kern, 2D: COSY/HSQC …)."""
    nuc = spec.get("nuclei") or []
    if spec.get("kind", "1D") == "1D":
        return nuc[0] if nuc else "1D"
    return spec.get("kind") or "2D"


def match_experiment(spec, raws, spectra=()):
    """Das eine TopSpin-Experiment, das zu einem Spektrum passt (gleiche Art), sonst None (keins oder mehrdeutig, auch
    wenn ein anderes Spektrum dieselbe Art hat, z. B. ¹³C + DEPT, oder das Experiment schon verknüpft ist)."""
    k = spectrum_kind(spec)
    others = [t for t in spectra if t is not spec]
    if any(spectrum_kind(t) == k for t in others):
        return None
    taken = {t.get("bruker") for t in others}
    hits = [r for r in raws if r.get("kind") == k and r.get("path") not in taken]
    return hits[0] if len(hits) == 1 else None


def params_rows(p):
    """Bruker-Parameter für die Tabelle im Tab: [(Beschriftung, Text, HTML)]; HTML setzt Massenzahlen hoch und Ziffern
    der Lösungsmittelformel tief (wie die Bildunterschrift), der Text bleibt zum Kopieren."""
    rows = []

    def add(lab, val, html=None):
        if val not in (None, ""):
            rows.append((lab, str(val), html or _h.escape(str(val))))
    nucs = [n for n in (p.get("nucleus"), p.get("nucleus2")) if n]
    add(T("nmr_p_nuc"), sup_nuclei(" / ".join(nucs)), XRAY.to_html(" / ".join(nuc_markup(n) for n in nucs)))
    add(T("nmr_p_pulprog"), p.get("pulprog"))
    add(T("nmr_p_solvent"), p.get("solvent"), XRAY.to_html(solvent_markup(p["solvent"])) if p.get("solvent") else None)
    add(T("nmr_temp"), f"{p['te']:.1f} K" if p.get("te") else "")
    add("SFO1", f"{p['sfo1']:.4f} MHz" if p.get("sfo1") else "")
    add("O1P", f"{p['o1p']:.3f} ppm" if p.get("o1p") is not None else "")
    add("SW", f"{p['sw']:.2f} ppm" if p.get("sw") else "")
    add("NS / DS", f"{p.get('ns')} / {p.get('ds')}" if p.get("ns") else "")
    add("TD", p.get("td"))
    add("D1", f"{p['d1']:g} s" if p.get("d1") is not None else "")
    add("AQ", f"{p['aq']:.2f} s" if p.get("aq") else "")
    add("RG", p.get("rg"))
    if p.get("sfo1_2"):
        add("F1: SFO1 / SW", f"{p['sfo1_2']:.4f} MHz / {p.get('sw2') or 0:.1f} ppm")
    add(T("nmr_p_probe"), p.get("probe"))
    return rows


# ---------------------------------------------------------------------------- Mnova-Text
_HEAD = re.compile(r"(?P<mass>\d{1,3})\s*(?P<el>[A-Z][a-z]?)\s*(?P<dec>\{[^}]*\})?\s*NMR\s*\(\s*(?P<freq>[\d.]+)\s*MHz\s*,"
                   r"\s*(?P<solv>[^)]+?)\s*\)\s*:?\s*δ\s*(?:\[\s*ppm\s*\]\s*=|\(\s*ppm\s*\)|=)?\s*", re.S)
_MULT = re.compile(r"^(?:br\.?\s*)?(?:app\.?\s*)?(?:[sdtqp]{1,4}|m|quint|sext|sept|hept|br|br s|brs|bs|m_c|AB|ABq|"
                   r"AA'BB'|AA′BB′)$", re.I)


def _split_top(s, sep=","):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def parse_signal(txt):
    """„6.91 (dd, J = 7.0, 1.5 Hz, 1H)“ -> dict(shift, mult, J, nH, assign)."""
    m = re.match(r"^\s*(?P<shift>[−-]?\d+(?:\.\d+)?(?:\s*[–—-]\s*[−-]?\d+(?:\.\d+)?)?)\s*(?:\((?P<par>.*)\))?\s*$",
                 txt, re.S)
    if not m:
        return dict(shift=txt.strip(), mult="", J="", nH="", assign="")
    shift = re.sub(r"\s*[–—]\s*", " – ", m.group("shift").strip())
    shift = re.sub(r"(\d)\s+-\s+([−-]?\d)", r"\1 – \2", shift)
    sig = dict(shift=shift, mult="", J="", nH="", assign="")
    toks = _split_top(m.group("par") or "")
    rest, i = [], 0
    while i < len(toks):
        t = toks[i]
        if re.match(r"^J\b|^\d?J\s*\(|^J\s*=", t):
            parts = [t]
            while not re.search(r"Hz\s*$", parts[-1]) and i + 1 < len(toks) and re.fullmatch(r"[\d.]+(\s*Hz)?",
                                                                                          toks[i + 1]):
                i += 1
                parts.append(toks[i])
            vals = re.sub(r"^.*?=\s*", "", ", ".join(parts))
            sig["J"] = (sig["J"] + "; " if sig["J"] else "") + re.sub(r"\s*Hz\s*$", "", vals).strip()
        elif not sig["mult"] and not sig["J"] and _MULT.match(t):
            sig["mult"] = t
        elif re.fullmatch(r"\d+(\.\d+)?\s*H", t):
            # mehrere H-Angaben in einer Klammer bleiben alle stehen (wie eingegeben); count_check meldet sie
            sig["nH"] = (sig["nH"] + ", " if sig["nH"] else "") + t.replace(" ", "")
        else:
            rest.append(t)
        i += 1
    sig["assign"] = ", ".join(rest)
    return sig


def parse_mnova(text):
    """Multiplettbericht(e) von Mnova (auch mehrere Kerne hintereinander) -> [dict(nucleus, dec, freq, solvent,
    signals)]."""
    blocks = []
    heads = list(_HEAD.finditer(text or ""))
    for k, m in enumerate(heads):
        body = text[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)].strip()
        body = re.split(r"\.\s*\n", body)[0]          # Satzende: danach z. B. „(13C Peak Report)“ von Mnova
        body = re.sub(r"[.;]\s*$", "", body.strip())
        sigs = [parse_signal(s) for s in _split_top(body)]
        blocks.append(dict(nucleus=f"{m.group('mass')}{m.group('el')}", dec=m.group("dec") or "",
                           freq=m.group("freq"), solvent=m.group("solv").strip(), signals=sigs))
    return blocks


HEAVY_H = {"2H": ("D", ("D", "[2H]")), "3H": ("T", ("T", "[3H]"))}


def count_check(blocks, formula):
    """Kernzahl der NMR-Zeilen gegen die Summenformel der Verbindung -> [(passt, [Kern, gefunden, Formel, Hinweis])]
    je Zeile, leer ohne lesbare Formel. ¹H: Summe der H-Zahlen der Signale gegen H der Formel (weniger ist möglich:
    austauschbare H). Andere Kerne: Zahl der Signale gegen die Atome des Elements (weniger ist möglich: Symmetrie,
    Überlagerung; mehr nicht). Nur Hinweise: nichts wird geändert oder abgelehnt."""
    from elucida.tabs.ir_ea import parse_formula
    try:
        counts = parse_formula(formula) if formula else {}
    except ValueError:
        counts = {}
    if not counts:
        return []
    out = []
    for b in blocks:
        if not b["signals"]:
            continue
        nuc, el = sup_nuclei(b["nucleus"]), re.sub(r"^\d+", "", b["nucleus"])
        n = len(b["signals"])
        if b["nucleus"] == "1H":
            m = counts.get("H", 0) + counts.get("[1H]", 0)
            vals = [float(s["nH"][:-1]) for s in b["signals"] if re.fullmatch(r"[\d.]+H", s["nH"])]
            if any("," in s["nH"] for s in b["signals"]):    # „2H, 3H“: mehrdeutig, nie still eine Zahl nehmen
                key, found = "fixt_nmr_count_multi_h", T("nmr_count_signals", n=n)
            elif len(vals) < n:
                key, found = "nmr_count_no_nh", T("nmr_count_signals", n=n)
            else:
                h = sum(vals)
                key = "nmr_count_ok" if abs(h - m) < 0.01 else "nmr_count_less_h" if h < m else "nmr_count_more_h"
                found = f"{h:g} H"
        else:
            if b["nucleus"] in HEAVY_H:                     # ²H/³H gegen D bzw. T der Formel, nie gegen H
                el, keys = HEAVY_H[b["nucleus"]]
                m = sum(counts.get(k, 0) for k in keys)
            else:
                m = sum(v for k, v in counts.items() if re.sub(r"^\[\d+|\]$", "", k) == el)
            key = "nmr_count_none" if not m else "nmr_count_more" if n > m else "nmr_count_ok" if n == m else "nmr_count_fewer"
            found = T("nmr_count_signals", n=n)
        if b.get("open") and key in ("nmr_count_less_h", "nmr_count_fewer"):   # fehlt, weil Vorschläge offen sind: das sagen
            key = "nmr_count_open"
        ok = key in ("nmr_count_ok", "nmr_count_fewer")
        out.append((ok, [nuc, found, f"{m} {el}", ("✓ " if ok else "⚠ ") + T(
            key, el=el, k=n - len(vals) if key == "nmr_count_no_nh" else 0, n=b.get("open") or 0)]))
    return out


def nominal_freq(nuc, freq):
    """¹H auf die Nennfrequenz (501 -> 500 MHz; nur bis ±5 MHz neben einem Vielfachen von 50, sonst ganzzahlig:
    270/360 MHz bleiben), andere Kerne ganzzahlig wie im Bericht."""
    try:
        f = float(freq)
    except (TypeError, ValueError):
        return str(freq or "")
    if nuc == "1H":
        n50 = round(f / 50) * 50
        return f"{n50:d}" if f >= 100 and abs(f - n50) <= 5 else f"{round(f):d}"
    return f"{round(f):d}"


def solvent_markup(s):
    """CDCl3 -> CDCl_{3}, DMSO-d6 -> DMSO-*d*_{6}, C6D6 -> C_{6}D_{6}."""
    s = (s or "").strip()
    s = re.sub(r"-d(\d+)\b", r"-*d*_{\1}", s)
    return re.sub(r"(?<=[A-Za-z)])(\d+)", r"_{\1}", s)


def signal_markup(sig, assign=None):
    a = sig["assign"] if assign is None else assign
    parts = [p for p in (sig["mult"], f"*J* = {sig['J']} Hz" if sig["J"] else "", sig["nH"], a) if p]
    sh = XRAY.minus(sig["shift"])
    return sh + (f" ({', '.join(parts)})" if parts else "")


def nmr_line(block, assigns=None):
    """-> (Klartext, HTML) im SI-Stil: „¹H NMR (500 MHz, CDCl₃): δ [ppm] = 7.39 – 7.36 (m, 2H, ImPy-H), …“."""
    assigns = assigns or {}
    nuc = block["nucleus"]
    dec = block.get("dec") or ""
    dec_m = re.sub(r"\{(\d+)([A-Z][a-z]?)\}", r"{^{\1}\2}", dec)
    head = nuc_markup(nuc) + dec_m + " NMR"
    cond = f"{nominal_freq(nuc, block['freq'])} MHz, {solvent_markup(block['solvent'])}"
    sigs = [signal_markup(s, assigns.get(sig_key(nuc, s))) for s in block["signals"]]
    body = "δ [ppm] = " + ", ".join(sigs)
    markup_plain = f"{head} ({cond}): {body}"
    html = f"<b>{XRAY.to_html(head)}</b> ({XRAY.to_html(cond)}): {XRAY.to_html(body)}"
    return XRAY.to_plain(markup_plain), html


def sig_key(nuc, sig):
    return f"{nuc}|{sig['shift']}"


# ---------------------------------------------------------------------------- Bildunterschriften
def spectrum_freqs(spec, blocks):
    """Frequenzen je Kern: Eingabe im Tab > Mnova-Text > Bruker (SFO1)."""
    out = {}
    by = {b["nucleus"]: b for b in blocks}
    pr = spec.get("params") or {}
    for i, nuc in enumerate(spec.get("nuclei") or []):
        man = (spec.get("freqs") or {}).get(nuc)
        if man:
            out[nuc] = str(man)
        elif nuc in by:
            out[nuc] = nominal_freq(nuc, by[nuc]["freq"])
        else:
            sf = pr.get("sfo1") if (pr.get("nucleus") == nuc) else pr.get("sfo1_2") if pr.get("nucleus2") == nuc else None
            if sf:
                out[nuc] = nominal_freq(nuc, sf)
    return out


def caption_html(spec, blocks, name):
    """„¹H NMR (500 MHz, CDCl₃, 298 K) of <b>Name</b>.“ bzw. „¹H/¹³C HSQC (500/126 MHz, …)“."""
    nuc = spec.get("nuclei") or []
    fr = spectrum_freqs(spec, blocks)
    solv = spec.get("solvent") or next((b["solvent"] for b in blocks if b["solvent"]), "") \
        or (spec.get("params") or {}).get("solvent", "")
    temp = spec.get("temp") or 298
    if spec.get("kind", "1D") == "1D":
        head = nuc_markup(nuc[0]) + " NMR" if nuc else "NMR"
        f = fr.get(nuc[0]) if nuc else None
    else:
        head = "/".join(nuc_markup(n) for n in nuc) + f" {spec.get('kind')}"
        f = "/".join(fr.get(n, "?") for n in nuc) if nuc and any(n in fr for n in nuc) else None
    cond = ", ".join(x for x in (f"{f} MHz" if f else "", solvent_markup(solv), f"{float(temp):.0f} K") if x)
    note = (spec.get("marks_note") or "").strip() if spec.get("source") == "bruker" else ""
    if note:                                           # Bedeutung der Marken im eigenen Spektrum („* = H2O“)
        from elucida.si import lines as SI
        note = " " + SI.chem_html(note.rstrip(".") + ".")
    return f"{XRAY.to_html(head)} ({XRAY.to_html(cond)}) of <b>{_h.escape(name)}</b>.{note}"


# Beschriftung unter der Struktur (ACS/Angew.: Strukturbild und Verbindungsnummer auf dem Spektrum, Lösungsmittel,
# Frequenz): Nummer fett, darunter „¹H NMR (500 MHz, CDCl₃)“. Als Pfade gezeichnet (wie Text in allen Abbildungen),
# damit Vorschau, SVG und Word gleich aussehen und keine Schrift auf dem Zielrechner nötig ist.
LABEL_F = 0.016                                        # Schrifthöhe als Anteil der Bildbreite
AXIS_MIN = {"1H": (0.0, 10.0), "13C": (0.0, 200.0)}    # diese Werte sollen beschriftet sein (Angew.: −1…10 und
                                                       # −10…200 ppm, ACS: 0…200 ppm); nur ein Hinweis


def label_lines(spec, blocks, name, number=True, info=True):
    """Zeilen der Beschriftung -> [(Mathtext, fett)]: Verbindungsnummer und Messangaben wie in der Unterschrift."""
    lines = []
    if number and name:
        lines.append((name.replace("$", r"\$"), True))
    if info:
        nuc = spec.get("nuclei") or []
        fr = spectrum_freqs(spec, blocks)
        solv = spec.get("solvent") or next((b["solvent"] for b in blocks if b["solvent"]), "") \
            or (spec.get("params") or {}).get("solvent", "")
        mt = lambda n: re.sub(r"^(\d+)", r"$^{\1}$", n)                      # noqa: E731
        if spec.get("kind", "1D") == "1D":
            head = (mt(nuc[0]) + " NMR") if nuc else "NMR"
            f = fr.get(nuc[0]) if nuc else None
        else:
            head = "/".join(mt(n) for n in nuc) + f" {spec.get('kind')}"
            f = "/".join(fr.get(n, "?") for n in nuc) if nuc and any(n in fr for n in nuc) else None
        sm = re.sub(r"-d(\d+)\b", r"-$d_{\1}$", (solv or "").strip())
        sm = re.sub(r"(?<=[A-Za-z)])(\d+)", r"$_{\1}$", sm)
        cond = ", ".join(x for x in (f"{f} MHz" if f else "", sm) if x)
        lines.append((head + (f" ({cond})" if cond else ""), False))
    return lines


def label_shapes(lines):
    """Zeilen als Umrisse in Einheiten der Schrifthöhe (y nach oben) -> [dict(segs, x0, w, bold)]."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    from elucida.core.uvvis import installed_fonts
    fams = installed_fonts(["Arial", "Liberation Sans", "DejaVu Sans"])     # ohne findfont-Meldung je fehlender Familie
    out = []
    for text, bold in lines:
        tp = TextPath((0, 0), text, size=100, prop=FontProperties(family=fams,
                                                                  weight="bold" if bold else "normal"))
        bb = tp.get_extents()
        out.append(dict(segs=[(int(code), (v / 100.0).tolist()) for v, code in tp.iter_segments(curves=True)],
                        x0=bb.x0 / 100.0, w=bb.width / 100.0, bold=bold))
    return out


def label_height(shapes):
    """Höhe des Blocks in Schrifthöhen (für die Suche nach einer freien Stelle)."""
    return sum(1.55 * (1.25 if sh["bold"] else 1.0) for sh in shapes) + (0.2 if shapes else 0.0)


def label_place(shapes, cx, top, F):
    """Zeilen mittig unter der Struktur: -> [(Umriss, Maßstab, x links, y Grundlinie)] (y nach unten wie im SVG)."""
    y, out = top + 0.2 * F, []
    for sh in shapes:
        k = F * (1.25 if sh["bold"] else 1.0)
        y += 1.25 * k
        out.append((sh, k, cx - (sh["x0"] + sh["w"] / 2) * k, y))
        y += 0.3 * k
    return out


def label_svg(placed):
    """Platzierte Zeilen als SVG-Gruppe mit absoluten Koordinaten (MuPDF: keine Transformationen nötig)."""
    cmd = {1: "M", 2: "L", 3: "Q", 4: "C"}
    paths = []
    for sh, k, x, y in placed:
        d = []
        for code, v in sh["segs"]:
            if code == 79:
                d.append("Z")
            elif code in cmd:
                d.append(cmd[code] + " ".join(f"{x + k * v[i]:.3f} {y - k * v[i + 1]:.3f}" for i in range(0, len(v), 2)))
        paths.append(f'<path fill="#000000" stroke="none" d="{" ".join(d)}"/>')
    return '<g id="elucida-label">' + "".join(paths) + "</g>"


def range_check(spec, rng):
    """Beschrifteter Bereich der Achse gegen die üblichen Mindestbereiche -> (passt | None, Text). None: nicht
    geprüft (2D, anderer Kern, keine Zahlenreihe gefunden)."""
    nuc = (spec.get("nuclei") or [""])[0]
    if spec.get("kind", "1D") != "1D" or nuc not in AXIS_MIN or rng is None:
        return None, "–"
    lo, hi = AXIS_MIN[nuc]
    return rng[0] <= lo and rng[1] >= hi, f"{rng[0] + 0.0:g} – {rng[1] + 0.0:g}".replace("-", "\u2212")   # nie „−0“


STRUCT_POS = ("auto", "tl", "tc", "tr", "manual")     # frei suchen / feste Ecken oben / gezogen
_FIXED = {"tl": (0.07, 0.12), "tc": (None, 0.12), "tr": (None, 0.12)}


def svg_viewbox(svg_text):
    m = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)', svg_text)
    if m:
        return tuple(map(float, m.groups()))
    w = re.search(r'<svg[^>]*\swidth="([\d.]+)', svg_text)
    h = re.search(r'<svg[^>]*\sheight="([\d.]+)', svg_text)
    return (0.0, 0.0, float(w.group(1)) if w else 1000.0, float(h.group(1)) if h else 700.0)


def _svg_box(txt, box, vw, vh):
    """Wurzel-<svg> mit neuem viewBox; width/height (mit Einheit) im selben Verhältnis, damit der Maßstab bleibt."""
    m = re.search(r"<svg\b[^>]*>", txt)
    head = re.sub(r'viewBox="[^"]*"', 'viewBox="{:.3f} {:.3f} {:.3f} {:.3f}"'.format(*box), m.group(0))
    for att, k in (("width", box[2] / vw), ("height", box[3] / vh)):
        head = re.sub(rf'(\s{att}=")([\d.]+)', lambda q, k=k: f"{q.group(1)}{float(q.group(2)) * k:.3f}", head)
    return txt[:m.start()] + head + txt[m.end():]


def svg_fit(txt, slack=0.012, cap=0.08):
    """MNova schneidet seine Seite genau an der Kante zu, die Endzahlen der ppm-Achse ragen halb hinaus (FR-2): Rahmen
    um den Überstand plus `slack` (Anteil der Breite; Word setzt eine etwas andere Schrift) vergrößern, je Seite höchstens
    `cap`. Gemessen am Bild (Text steht in transformierten Gruppen). Ohne Überstand, ohne viewBox oder nicht lesbar:
    unverändert."""
    if not re.search(r"<svg\b[^>]*\sviewBox=", txt):
        return txt
    try:
        import numpy as np
        import pymupdf
        vx, vy, vw, vh = svg_viewbox(txt)
        g = cap * max(vw, vh)
        probe = _svg_box(txt, (vx - g, vy - g, vw + 2 * g, vh + 2 * g), vw, vh)
        page = pymupdf.open(stream=probe.encode("utf-8"), filetype="svg")[0]
        pix = page.get_pixmap(dpi=max(10, int(1200 / max(page.rect.width, 1) * 72)), colorspace=pymupdf.csGRAY)
        a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 250
    except Exception:                                      # nur Darstellung: lieber MNovas Rahmen als kein Bild
        return txt
    ys, xs = np.nonzero(a.any(1))[0], np.nonzero(a.any(0))[0]
    if not xs.size:
        return txt
    ux, uy = (vw + 2 * g) / pix.width, (vh + 2 * g) / pix.height     # Benutzereinheiten je Pixel
    ink = (vx - g + xs[0] * ux, vy - g + ys[0] * uy, vx - g + (xs[-1] + 1) * ux, vy - g + (ys[-1] + 1) * uy)
    pad, tol = slack * vw, 0.5 * max(ux, uy)
    x0 = ink[0] - pad if ink[0] < vx - tol else vx
    y0 = ink[1] - pad if ink[1] < vy - tol else vy
    x1 = ink[2] + pad if ink[2] > vx + vw + tol else vx + vw
    y1 = ink[3] + pad if ink[3] > vy + vh + tol else vy + vh
    if (x0, y0, x1, y1) == (vx, vy, vx + vw, vy + vh):
        return txt
    return _svg_box(txt, (x0, y0, x1 - x0, y1 - y0), vw, vh)


def occupancy(spec_svg, px_w=400):
    """Belegte Fläche des Spektrums (alles, was nicht weiß ist: Signale, Labels, Integrale, Achsen, Insets) -> bool[H, W]."""
    import numpy as np
    import pymupdf
    page = pymupdf.open(str(spec_svg))[0]
    pix = page.get_pixmap(dpi=max(10, int(px_w / max(page.rect.width, 1) * 72)), colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return a < 235


def auto_place(mask, width, aspect, margin=0.015):
    """Freie Stelle für die Struktur (Breite = Anteil der Bildbreite, aspect = Höhe/Breite): am wenigsten Überdeckung
    mit Rand, bei Gleichstand möglichst weit oben links. -> (fx, fy) linke obere Ecke als Anteil von Breite/Höhe."""
    import numpy as np
    H, W = mask.shape
    w = max(2, int(round(width * W)))
    h = max(2, int(round(w * aspect)))
    m = max(1, int(round(margin * W)))
    if w + 2 * m >= W or h + 2 * m >= H:
        return 0.02, 0.02
    ii = np.zeros((H + 1, W + 1), np.int64)
    ii[1:, 1:] = mask.cumsum(0).cumsum(1)
    best, step = None, max(1, W // 120)
    for y in range(m, H - h - m + 1, step):
        y0, y1 = y - m, y + h + m
        for x in range(m, W - w - m + 1, step):
            x0, x1 = x - m, x + w + m
            occ = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
            key = (occ, y / H + x / W)
            if best is None or key < best[0]:
                best = (key, x, y)
    _, x, y = best
    return x / W, y / H


def struct_aspect(struct):
    cx0, cy0, cx1, cy1 = struct["clip"]
    return (cy1 - cy0) / max(cx1 - cx0, 1e-6)


def place_structure(spec_svg, struct, pos="auto", width=0.2, xy=None, extra=0.0):
    """Lage der Struktur als (fx, fy) – gezogen (manual), feste Ecke oder frei gesucht (auto). extra: Höhe der
    Beschriftung darunter als Anteil der Strukturbreite (die freie Stelle muss beides fassen)."""
    if pos == "manual" and xy:
        return float(xy[0]), float(xy[1])
    if pos in _FIXED:
        fx, fy = _FIXED[pos]
        if pos == "tc":
            fx = (1 - width) / 2
        elif pos == "tr":
            fx = 0.93 - width
        return fx, fy
    return auto_place(occupancy(spec_svg), width, struct_aspect(struct) + extra)   # Pixelmaske: x und y gleich skaliert


def compose_structure(spec_svg, struct, out_svg, xy=(0.07, 0.12), width=0.2, label=None):
    """Struktur (dict aus IMG.load_structure: pdf + clip) als Vektorgruppe in das Mnova-SVG setzen – ersetzt den
    Inkscape-Schritt. xy = linke obere Ecke als Anteil der Bildbreite/-höhe, width = Anteil der Bildbreite."""
    from elucida.core import images as IMG
    txt = Path(spec_svg).read_text(encoding="utf-8", errors="replace")
    vx, vy, vw, vh = svg_viewbox(txt)
    w = vw * width
    h = w * struct_aspect(struct)
    x0, y0 = vx + xy[0] * vw, vy + xy[1] * vh
    Path(out_svg).parent.mkdir(parents=True, exist_ok=True)
    Path(out_svg).write_text(txt, encoding="utf-8")
    IMG.overlay_vectors_svg(out_svg, [((x0, y0, x0 + w, y0 + h), struct["pdf"], struct["clip"])])
    if label:                                          # Nummer und Messangaben mittig unter der Struktur
        out = Path(out_svg).read_text(encoding="utf-8")
        k = out.rfind("</svg>")
        if k >= 0:
            g = label_svg(label_place(label, x0 + w / 2, y0 + h, vw * LABEL_F))
            Path(out_svg).write_text(out[:k] + g + out[k:], encoding="utf-8")
    return Path(out_svg)


def new_spectrum(path, info, kind=None):
    k = kind or ("1D" if not info["is2d"] else (kind_from_name(path) or "2D"))
    return dict(uid=uuid.uuid4().hex[:8], file=str(path), nuclei=list(info["nuclei"]), kind=k, temp=298.0,
                bruker=None, params=None, freqs={}, solvent="", size=list(info["size_cm"]), struct_on=True,
                struct_pos="auto", struct_xy=None, struct_w=20.0)


def make_test_svg(path, nuclei=("1H",), axis=True, peaks=()):
    """Künstliches Mnova-ähnliches SVG (Achsenbeschriftung als Text wie bei Mnova, eine Kurve). Kein echter Datensatz."""
    w, h = 1088, 759
    lab = lambda n, x, y, rot="": (f'<text x="{x}" y="{y}" font-size="14" {rot}>δ <tspan dy="-4" font-size="9">'  # noqa: E731
                                   f'{re.match(r"(\d+)", n).group(1)}</tspan><tspan dy="4">'
                                   f'{re.sub(r"^\d+", "", n)} (ppm)</tspan></text>')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="287.867mm" height="200.819mm" viewBox="0 0 {w} {h}">',
             '<title>MestReNova SVG (test)</title>',
             '<polyline fill="none" stroke="#800000" points="50,700 300,700 310,200 320,700 1040,700"/>']
    for k, txt in enumerate(peaks):                        # senkrechte Peaklabels wie bei Mnova
        x = 300 + 40 * k
        parts.append(f'<text x="{x}" y="60" font-size="9" transform="rotate(-90 {x} 60)">{txt}</text>')
    if axis:
        parts.append(lab(nuclei[0], 500, 745))
        if len(nuclei) > 1:
            parts.append(lab(nuclei[1], 1070, 380, 'transform="rotate(90 1070 380)"'))
    parts.append("</svg>")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return Path(path)


def make_test_acqus(d, nuc="1H", sfo1=500.503090587, te=298.1466, nuc2=None, pulprog="zg30"):
    """Künstlicher Bruker-Experimentordner mit acqus (und acqu2s). Kein echter Datensatz."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    txt = ["##TITLE= Parameter file", f"##$NUC1= <{nuc}>", f"##$PULPROG= <{pulprog}>", "##$SOLVENT= <CDCl3>",
           f"##$TE= {te}", f"##$SFO1= {sfo1}", "##$BF1= 500.5", f"##$O1= {6.175 * sfo1}", "##$SW= 19.9784",
           "##$NS= 16", "##$DS= 2", "##$TD= 65536", "##$RG= 101", "##$D= (0..63)", "0 1 0.03 0 0 0 0 0",
           "##$PROBHD= <test probe>", "##END="]
    (d / "acqus").write_text("\n".join(txt) + "\n", encoding="latin-1", newline="")      # wie TopSpin, auch unter Windows
    if nuc2:
        (d / "acqu2s").write_text(f"##$NUC1= <{nuc2}>\n##$SFO1= 125.8\n##$SW= 165\n##$TD= 256\n##END=\n",
                                  encoding="latin-1")
    return d


# ---------------------------------------------------------------------------- Bruker-Rohdaten (eigene Verarbeitung)
# Quelle je Spektrum: „mnova“ (SVG/EMF, Standard, unverändert) oder „bruker“ (Experimentordner im Schlüssel „bruker“,
# 1D aus dem FID nach core/nmr_proc). Belegt ist nur die Kette Leser -> FT -> Phase aus procs (Audit 1.3.0); Phase,
# Basislinie und Referenz sind Vorschläge, die der Nutzer bestätigt (Spezifikation NMR 1.3.0, Abnahme A2 offen).
SOURCES = ("mnova", "bruker")
SIGNED_KINDS = ("DEPT", "APT")                          # Vorzeichen zählt: Phase nur aus procs, keine Integrale


def raw_name(expdir):
    """Name eines Experiments in Meldungen: die letzten drei Pfadteile (eindeutig, Brief Spur C)."""
    return "/".join(Path(expdir).parts[-3:])


def raw_dataset(expdir, procno=1):
    """Bruker-1D-Experiment -> dict(spec = komplexes Spektrum ohne eigene Phase, own = selbst gerechnet, phase =
    (PHC0, PHC1) aus procs oder None, ax = unkalibrierte Achse (SF = BF1, nie SF/SR aus procs), sf, hzpt, nucleus,
    solvent, kind, notes). Eigene Verarbeitung abgelehnt (`blockers`): TopSpins 1r (+ 1i) mit Meldung, nie geraten;
    fehlt auch das: ValueError mit Meldung."""
    from elucida.core import nmr_analysis as NA, nmr_proc as NP
    from elucida.formats import bruker_nmr as BN
    d = Path(expdir)
    name = raw_name(d)
    a = BN.acqus(d)
    pdir = d / "pdata" / str(procno)
    p = BN.procs(pdir)
    for key in ("BF1", "SFO1"):
        BN.num(a, key, name)
    for key in ("SW_p", "SI"):
        BN.num(p, key, name)
    if (d / "acqu2s").is_file():
        raise ValueError(T("nmr_raw_is_2d", name=name))
    has_ph = all(isinstance(p.get(k), (int, float)) and not isinstance(p.get(k), bool) for k in ("PHC0", "PHC1"))
    p0 = dict(p, PHC0=0.0, PHC1=0.0)
    why = NP.blockers(a, p0, name=name)
    kind = experiment_kind(acq_params(d))
    notes = []
    if not why:
        fid, _ = BN.read_fid(d)
        spec, own = NP.process_1d(fid, a, p0, name), True
        phase = (float(p["PHC0"]), float(p["PHC1"])) if has_ph else None
    else:
        if p.get("REVERSE", "no") != "no" or p.get("STSR", 0) != 0 or p.get("STSI", p.get("SI")) != p.get("SI"):
            raise ValueError(T("nmr_raw_reverse", name=name, why=why[0]))   # 1r passt dann nicht zur Achse
        r, _ = BN.read_1d(pdir)                           # ValueError mit Meldung, wenn auch 1r fehlt
        try:
            im = BN.read_1d(pdir, "1i")[0]
        except ValueError:
            im = None
        spec = r - 1j * im if im is not None else r.astype(complex)   # TopSpin: 1i = −Im
        own, phase = False, None
        notes.append(why[0])
    ax = NA.axis_uncalibrated(a, p)
    if ax.size != spec.size:
        raise ValueError(T("b1nmr_size", name=name, n=spec.size, m=ax.size))
    return dict(spec=spec, own=own, phase=phase, ax=ax, sf=float(a["BF1"]), hzpt=float(p["SW_p"]) / float(p["SI"]),
                nucleus=parse_nucleus(a.get("NUC1")) or "1H", solvent=str(a.get("SOLVENT", "")), kind=kind,
                notes=notes)


def raw_2d(expdir, procno=1):
    """Bruker-2D-Experiment -> dict(data, ax2, ax1 = unkalibrierte Achsen (SF = BF1), own, notes, nuc2, nuc1, bf2,
    bf1). Eigene Verarbeitung aus ser (core/nmr2d), wo die Klasse belegt ist; sonst TopSpins 2rr mit der Meldung
    (Name = letzte drei Pfadteile); fehlt auch das: ValueError mit beiden Gründen. Unaufgeteiltes NOAH: Meldung
    „Phase ausstehend“, nichts geraten."""
    from elucida.core import nmr2d as N2
    from elucida.formats import bruker_nmr as BN
    d = Path(expdir)
    name = raw_name(d)
    a, a2 = BN.acqus(d), BN.acqus(d, "acqu2s")
    notes, own, module = [], True, None
    if isinstance(a.get("NBL"), int) and a["NBL"] > 1:     # unaufgeteiltes NOAH: je Block mit den Vorgaben des Moduls
        got = []
        for k in (1, 2):
            try:
                got.append(N2.process_noah(d, k, name=name))
            except ValueError as ex:                      # HSQC ohne Phase des Nutzers: „Phase ausstehend“
                notes.append(str(ex))
        if not got:
            raise ValueError(" ".join(notes))
        r = got[0]
        module = "HMBC" if r.p2.get("PH_mod") == 2 else "HSQC"          # NOAH_PARAMS: HMBC = Betrag in F2
        return dict(data=r.data, ax2=r.ax2, ax1=r.ax1, own=True, notes=notes + r.notes, module=module,
                    nuc2=parse_nucleus(a.get("NUC1")) or "", nuc1=parse_nucleus(a2.get("NUC1")) or "",
                    bf2=float(a["BF1"]), bf1=float(a2["BF1"]))
    try:
        r = N2.process(d, procno, name=name)
        data, ax2, ax1 = r.data, r.ax2, r.ax1
        notes += r.notes
    except ValueError as ex:
        own = False
        notes.append(str(ex))
        try:
            data, p2, p1 = BN.read_2d(d / "pdata" / str(procno))
        except ValueError as ex2:
            raise ValueError(f"{ex} {ex2}")
        for q in (p2, p1):                                 # gespiegelt/Streifen: 2rr passt nicht zur Achse aus acqus
            if q.get("REVERSE", "no") != "no" or q.get("STSR", 0) not in (0, None) \
                    or q.get("STSI", 0) not in (0, q.get("SI")):
                raise ValueError(T("nmr_raw_reverse", name=name, why=ex))
        ax2, ax1 = N2.axis(a, p2["SI"]), N2.axis(a2, p1["SI"])
    return dict(data=data, ax2=ax2, ax1=ax1, own=own, notes=notes, module=module, nuc2=parse_nucleus(a.get("NUC1")) or "",
                nuc1=parse_nucleus(a2.get("NUC1")) or "", bf2=float(a["BF1"]), bf1=float(a2["BF1"]))


def phased(spec, phc0, phc1):
    """Phase wie procs: exp(−i·(PHC0 + PHC1·i/SI)), Drehpunkt linker Rand (core/nmr_proc)."""
    n = spec.size
    return spec * np.exp(-1j * np.deg2rad(phc0 + phc1 * np.arange(n) / n))


def raw_proc_defaults(ds):
    """Anfangszustand der Verarbeitung: Phase aus procs (nicht bestätigt), ohne procs-Phase 0/0 bis zum Vorschlag;
    Basislinie automatisch; Referenz noch nicht gesucht (`suggest_ref`)."""
    ph = ds["phase"] or (0.0, 0.0)
    src = "procs" if ds["phase"] else ("topspin" if not ds["own"] else "none")
    return dict(phc0=ph[0], phc1=ph[1], phase=src, phase_ok=False, baseline=True, ref=None, ref_status="none",
                ref_src="", ref_target=None)


def mnova_key(spec):
    """Inhalt eines Spektrums aus einem MNova-Dokument (FID + acqus): gleich auch in neu gespeicherten Dokumenten."""
    import hashlib
    import json
    h = hashlib.sha256(np.ascontiguousarray(spec["fid"]).tobytes())
    h.update(json.dumps(spec["acqus"], sort_keys=True, default=str).encode())
    return h.hexdigest()


def baseline_key(pr):
    """Gewählte Basislinie eines Spektrums: „off“, „bernstein3“ oder „poly5“ (Standard)."""
    from elucida.core.nmr_analysis import BL_MODELS
    m = pr.get("bl_model", "poly5")
    return "off" if not pr.get("baseline", True) else m if m in BL_MODELS else "poly5"   # unbekannt: Standard


def suggest_ref(y, ds, solvent):
    """Referenzvorschlag (Fulmer-Restsignal, `nmr_analysis.suggest_reference`) -> (Verschiebung in ppm oder None,
    gefundene Lage auf der unkalibrierten Achse, Tabellenwert, Meldungen). Andere Kerne als ¹H/¹³C: keiner (Achse
    nominell, Abschnitt X-Kerne)."""
    from elucida.core import nmr_analysis as NA
    if ds["nucleus"] not in NA.REF_WIN:
        return None, None, None, [T("nmr_ref_nominal", nuc=ds["nucleus"])]
    r = NA.suggest_reference(y, ds["ax"], ds["nucleus"], solvent, ds["sf"])
    return r.get("shift"), r.get("found"), r.get("ref"), list(r.get("warnings") or [])


def shift_ranges(items, d):
    """Bereiche ({lo, hi, parts}) um d ppm verschieben (unkalibrierte Achse <-> Achse mit Referenz); Lage im Bild bleibt."""
    out = []
    for it in items:
        it = dict(it)
        for k in ("lo", "hi"):
            if it.get(k) is not None:
                it[k] = it[k] + d
        if it.get("parts"):
            it["parts"] = [dict(q, lo=q["lo"] + d, hi=q["hi"] + d) for q in it["parts"]]
        out.append(it)
    return out


def solvent_text(name):
    from elucida.core import nmr_report as NR
    return NR.solvent_text(name)


def demo_raw_1h(d, peaks, offset=0.04):
    """Erfundenes TopSpin-¹H-Experiment zu den Linien eines Beispielspektrums [(δ, Höhe, Breite)]: Achse 0.04 ppm
    unkalibriert (Referenzvorschlag hat zu tun), Empfängerphase 18° (procs hebt sie auf). Keine Messdaten."""
    from elucida.formats import bruker_nmr as BN
    return BN.make_test_1d(d, [(x + offset, a, 1.0) for x, a, _ in peaks], phc0=18.0, td=32768, si=65536)


# ---------------------------------------------------------------------------- Was gedruckt wird (EINE Definition)
# Entscheidungen 89/90: je Kern bleibt die Mnova-Zeile/-Abbildung, bis ein eigenes Spektrum ausdrücklich „für die SI“
# gewählt (höchstens eines je Kern) UND freigegeben ist (Phase und Referenz bestätigt, für jeden Kern); gedruckt werden nur
# bestätigte Signale (unberührte Vorschläge nie), bei Nicht-¹H ohne Signale die bestätigte Peakliste. SI-Zeile,
# Signaltabelle, Kernzahl, Kacheln, Word und Vergleichstabelle lesen nur `printed_blocks`.
def own_release(s):
    """Eigenes 1D-Spektrum für die SI freigegeben? -> None oder i18n-Schlüssel des Grundes."""
    if s.get("source") != "bruker" or not s.get("proc") or s.get("kind", "1D") != "1D":
        return "nmr_own_none"
    if not s.get("si_use"):
        return "nmr_own_not_chosen"
    if not s["proc"].get("phase_ok"):
        return "nmr_own_phase"
    if s["proc"].get("ref_status") != "confirmed":
        return "nmr_own_ref"
    return None


def own_signals(s, nh=None):
    """Gedruckte Signale eines eigenen Spektrums aus dem Zustand -> (Kern, [nmr_report.Signal], [Meldungen], offene
    Vorschläge, Stellen). Nur bestätigte Signale; ein bestätigtes, nicht schreibbares wird genannt (die Zeile bleibt).
    nh(g) -> Kerne eines Signals (Integral × Normierung), sonst die eingegebenen."""
    from elucida.core import nmr_report as NR
    a, pr = s.get("ana") or {}, s.get("proc") or {}
    ref = pr.get("ref") or 0.0
    nuc = (s.get("nuclei") or ["1H"])[0]
    d = 2 if nuc == "1H" else 1
    sigs, errs, open_ = [], [], 0
    for g in a.get("signals") or ():
        if not g.get("confirmed"):
            open_ += 1
            continue
        try:
            m = dict(lo=g["lo"] + ref, hi=g["hi"] + ref, mult=g.get("mult") or "m", J=g.get("J") or [],
                     shift=None if g.get("shift") is None else g["shift"] + ref,
                     unmeasured=[] if g.get("j_accepted") else g.get("unmeasured") or [])
            sig = NR.signal_of(m, nh(g) if nh else g.get("nH"), g.get("assign") or "", (m["lo"], m["hi"]), confirmed=True)
            NR.signal_markup(sig, d)                       # schreibbar? sonst nennen, nicht die Zeile abbrechen
        except (ValueError, KeyError, TypeError) as ex:
            c_ = next((v_ + ref for v_ in (g.get("shift"), g.get("lo"), g.get("hi")) if isinstance(v_, (int, float))), None)
            errs.append(T("nmr_sig_unprintable", d="–" if c_ is None else f"{c_:.2f}", e=ex))
            continue
        sig.uid = g.get("uid")
        sig.taken = bool(g.get("unmeasured") and g.get("j_accepted"))
        sigs.append(sig)
    if not a.get("signals") and nuc != "1H" and a.get("peaks_ok"):        # ¹³C u. a.: bestätigte Peakliste
        sigs = [NR.Signal(shift=p["x"] + ref, status=NR.CONFIRMED) for p in a.get("peaks") or ()]
    sigs.sort(key=lambda x: -x.centre)                    # hohe Verschiebung zuerst wie im Mnova-Bericht
    return nuc, sigs, errs, open_, d


def own_block(s, nh=None, bf=None):
    """Eigenes Spektrum als Block wie `parse_mnova` (Texte je Signal) + source „own“, Zeile und Meldungen."""
    from elucida.core import nmr_report as NR
    nuc, sigs, errs, open_, d = own_signals(s, nh)
    sf = (s.get("params") or {}).get("sfo1") or bf
    freq = spectrum_freqs(s, []).get(nuc) or (nominal_freq(nuc, sf) if sf else "")
    solv = NR.solvent_text(s.get("solvent") or "")
    rows = []
    for g in sigs:
        pos = NR._num(g.centre, d) if not g.is_range else f"{NR._num(g.hi, d)} – {NR._num(g.lo, d)}"
        rows.append(dict(shift=XRAY.minus(pos), mult=g.mult or "", J=", ".join(NR._num(c.hz, 1) for c in g.J),
                         nH=f"{g.nH:g}H" if g.nH is not None else "", assign=g.assign or "",
                         uid=getattr(g, "uid", None), taken=getattr(g, "taken", False)))
    line = None
    if sigs:
        spec = NR.Spectrum(nuc, float(freq or 0), solv, signals=sigs, digits=d)
        mk = NR.format_markup(spec)
        nm = NR.nucleus_markup(nuc) + " NMR"               # fett wie die Zeilen aus dem Mnova-Bericht
        line = (XRAY.to_plain(mk), f"<b>{XRAY.to_html(nm)}</b>{XRAY.to_html(mk[len(nm):])}")
    return dict(nucleus=nuc, dec="", freq=str(freq), solvent=solv, signals=rows, source="own", uid=s["uid"],
                line=line, errs=errs, open=open_)


def printed_blocks(st, nh=None):
    """Was die SI je Kern druckt -> (Blöcke wie `parse_mnova` mit source „mnova“/„own“, Hinweise). nh(s, g) -> Kerne
    eines Signals (Tab mit Rohdaten), sonst die eingegebenen."""
    spectra = sorted(st.get("spectra") or [], key=sort_key)
    chosen, notes = {}, []
    for s in spectra:
        why = own_release(s)
        if why == "nmr_own_none":
            continue
        nuc = (s.get("nuclei") or ["1H"])[0]
        name = Path(s.get("bruker") or s["file"]).name
        if why is None and nuc in chosen:                  # höchstens eines je Kern: das zweite fällt nicht still weg
            notes.append(T("nmr_own_second", nuc=sup_nuclei(nuc), f=name))
        elif why is None:
            chosen[nuc] = s
        elif why != "nmr_own_not_chosen" or (s.get("ana") or {}).get("signals") or (s.get("ana") or {}).get("peaks_ok"):
            notes.append(T("nmr_own_held", nuc=sup_nuclei(nuc), f=name, why=T(why)))
    out = []
    own = {}
    for nuc, s in chosen.items():
        b = own_block(s, (lambda g, s=s: nh(s, g)) if nh else None)
        if b["open"]:
            notes.append(T("nmr_own_open", nuc=sup_nuclei(nuc), n=b["open"]))
        notes += b["errs"]
        if b["signals"]:
            own[nuc] = b
        else:
            notes.append(T("nmr_own_empty", nuc=sup_nuclei(nuc)))
    for b in parse_mnova(st.get("text") or ""):
        if b["nucleus"] not in own:
            out.append(dict(b, source="mnova"))
    out += list(own.values())
    for nuc, b in own.items():
        notes.insert(0, T("nmr_own_line", nuc=sup_nuclei(nuc)))
    return sorted(out, key=lambda b: nuc_rank(b["nucleus"])), notes


def svg_peak_line(s, blocks):
    """Zeile „13C NMR (126 MHz, CDCl3) δ 141.20, …“ aus den Peaklabels eines 1D-Spektrums (SVG) -> (Zeile, Zahl der
    Signale). Frequenz aus SFO1 desselben Kerns, sonst ¹H-Zeile × γ; ValueError mit Meldung (¹H braucht den
    Multiplettbericht, EMF, keine Datei, keine Labels)."""
    if s is None or s.get("kind") != "1D" or not s.get("nuclei"):
        raise ValueError(T("nmr_peaks_need"))
    nuc = s["nuclei"][0]
    if nuc == "1H":
        raise ValueError(T("nmr_peaks_1h"))
    if is_emf(s["file"]):
        raise ValueError(T("nmr_emf_nopeaks"))
    if not Path(s["file"]).is_file():
        raise ValueError(T("nmr_peaks_svg_only"))
    vals, solv = svg_peaks(s["file"])
    if not vals:
        raise ValueError(T("nmr_peaks_none", f=Path(s["file"]).name))
    h1 = {b["nucleus"]: b for b in blocks}.get("1H") or {}
    freq = spectrum_freqs(s, []).get(nuc)                       # SFO1 nur vom selben Kern
    if not freq and h1.get("freq") and nuc in GAMMA_REL:
        freq = float(nominal_freq("1H", h1["freq"])) * GAMMA_REL[nuc]
    solv = s.get("solvent") or solv or h1.get("solvent") or ""
    head = f"{nuc} NMR" + (f" ({nominal_freq(nuc, freq)} MHz, {solv})" if freq else f" ({solv})" if solv else "")
    return f"{head} δ " + ", ".join(vals) + ".", len(vals)


def mx_lines(spectra):
    """NMR-Zeilen aus den Seiten exportierter MNova-Dokumente (Schlüssel „mx“ am Spektrum) -> (Text, je Kern eine
    Zeile; Hinweise). Nur 1D (2D-Berichte nie). ¹H nur aus dem Multiplettbericht (ohne: Vergleich/Serie, keine Zeile);
    andere Kerne Multipletts, wenn vorhanden und nicht „Peaks“ gewählt, sonst die Peaklabels der Seite (`svg_peak_line`,
    Zahl wie im Bild; MNovas Peakbericht rundet anders). Je Kern das erste Spektrum (`sort_key`), weitere werden genannt;
    eine Seite mit verschiedenen Spektren liefert keine Zeile (nicht raten)."""
    lines, notes, first, no_mult = {}, [], {}, {}
    for s in sorted(spectra, key=sort_key):
        mx = s.get("mx")
        if not mx or s.get("kind", "1D") != "1D":
            continue
        nuc, page = (s.get("nuclei") or ["?"])[0], T("nmr_mx_page", p=mx.get("page"), doc=mx.get("doc", ""))
        if mx.get("mult_bad"):
            notes.append(T("nmr_mx_mult_bad", page=page))
        if mx.get("mixed"):
            notes.append(T("nmr_mx_mixed", page=page, what=sup_nuclei(mx["mixed"])))
        elif nuc == "1H" and not mx.get("mult"):
            if not mx.get("mult_bad"):                     # Serie: eine Zeile je Dokument, nicht je Seite
                no_mult.setdefault(mx.get("doc", ""), []).append(str(mx.get("page")))
        elif nuc in first:
            notes.append(T("nmr_mx_second", nuc=sup_nuclei(nuc), page=page, first=first[nuc]))
        else:
            try:
                lines[nuc] = mx["mult"] if mx.get("mult") and (nuc == "1H" or mx.get("use") != "peaks") \
                    else svg_peak_line(s, parse_mnova(lines.get("1H", "")))[0]
                first[nuc] = page
            except ValueError as ex:
                notes.append(f"{page}: {ex}")
    notes += [T("nmr_mx_no_mult", page=T("nmr_mx_page" if len(ps) == 1 else "nmr_mx_pages", p=", ".join(ps), doc=d))
              for d, ps in no_mult.items()]
    return "\n".join(lines[n] for n in sorted(lines, key=nuc_rank)), notes


def mx_peak_report(s):
    """Peakbericht der Seite eines exportierten MNova-Spektrums (`manifest.json` neben der SVG, Seite `mx["page"]`) ->
    Peaklagen als Texte, sonst None (kein Manifest, Seite fehlt, verschiedene Spektren, leerer oder fremder Bericht)."""
    import json
    from elucida.formats import mnova_cli as MX
    try:
        m = json.loads((Path(s["file"]).parent / "manifest.json").read_text(encoding="utf-8"))
        pg = next(p for p in m.get("pages") or [] if p.get("page") == s["mx"].get("page"))
    except (OSError, ValueError, StopIteration, AttributeError):
        return None
    sps = MX.page_spectra(pg)
    if len(sps) != 1:
        return None
    blocks = parse_mnova(MX.report_text(sps[0].get("preport")))
    if len(blocks) != 1 or blocks[0]["nucleus"] != (s.get("nuclei") or [""])[0]:
        return None
    peaks = [g["shift"] for g in blocks[0]["signals"]]
    # Bericht mit Zusätzen (Intensität, Bereich …) ist nicht nur eine Peakliste: kein Abgleich statt raten
    return peaks if peaks and all(re.fullmatch(r"[-−]?\d+\.\d+", p) and not any(g[k] for k in ("mult", "J", "nH", "assign"))
                                  for p, g in zip(peaks, blocks[0]["signals"])) else None


def mx_merge(text, prop):
    """Vorschlag `prop` in den Text: Zeilen der Kerne im Vorschlag ersetzen (Folgezeilen gehören zur Zeile davor), Zeilen
    anderer Kerne (von Hand getippt) bleiben dahinter; wie `peaks_from_svg` für einen Kern."""
    head = re.compile(r"\s*(\d{1,3})\s*([A-Z][a-z]?)\s*(?:\{[^}]*\})?\s*NMR")
    nucs = {m.group(1) + m.group(2) for m in map(head.match, prop.splitlines()) if m}
    keep, drop = [], False
    for ln in (text or "").splitlines():
        m = head.match(ln)
        if m:
            drop = m.group(1) + m.group(2) in nucs
        if ln.strip() and not drop:
            keep.append(ln)
    return "\n".join([prop] + keep)


def plain_data(obj):
    """Werte aus der Ansicht (numpy-Zahlen aus matplotlib) als reine Python-Zahlen: YAML und Rückgängig (JSON)."""
    import json
    return json.loads(json.dumps(obj, default=float))


# ---------------------------------------------------------------------------- Tab
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,  # noqa: E402
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QScrollArea, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout,
                               QSizePolicy, QStackedWidget, QWidget, QApplication)

from elucida.app import project as PRJ, style as STYLE  # noqa: E402
from elucida.app.style import HINT_CSS, make_form  # noqa: E402

_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_UNSUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def sup_nuclei(text):
    """Massenzahl vor einem Elementsymbol hochstellen (1H/13C -> ¹H/¹³C; DEPT135 bleibt) – nur für die Anzeige."""
    return re.sub(r"(?<![A-Za-z0-9])\d+(?!D\b)(?=[A-Z])", lambda m: m.group().translate(_SUP), text or "")   # „2D“ bleibt


# ---------------------------------------------------------------------------- MNova-Export (eigener Prozess)
# Die Warteschlange gehört dem Hauptfenster (`_mnova_jobs`): der Tab wird bei Rückgängig, Sprache oder Design ersetzt,
# ein Export läuft weiter und wird vom dann aktuellen Tab übernommen.
def _mx_next(main):
    """Nächsten MNova-Export starten (höchstens ein MNova-Prozess von Elucida zugleich)."""
    import shutil
    import tempfile
    import time
    from elucida.formats import mnova_cli as MX
    jobs = main.__dict__.get("_mnova_jobs") or []
    if not jobs or jobs[0].get("t0"):
        return
    job = jobs[0]
    job["t0"] = time.monotonic()
    try:
        job["tmp"] = tempfile.mkdtemp(prefix="elucida-mnova-")
        job["proc"], job["out"], job["token"] = MX.start(job["exe"], job["dst"], job["tmp"])
    except ValueError:
        return _mx_done(main, job, why="nmr_mx_comma")
    except OSError as ex:
        return _mx_done(main, job, why="nmr_mx_failed", detail=str(ex))
    job["timer"] = t = QTimer(main, interval=500)
    t.timeout.connect(lambda: _mx_poll(main, job))
    t.start()
    main.notify(T("nmr_mx_started", name=Path(job["dst"]).name))     # Fortschritt danach in der Karte MNova
    app = QApplication.instance()
    if app is not None:                                    # Programm schließt: eigenen Prozess und Kopie nicht zurücklassen
        app.aboutToQuit.connect(lambda: (_mx_kill(job), shutil.rmtree(job["tmp"], ignore_errors=True)))


def _mx_poll(main, job):
    """Alle 0.5 s: Manifest da (Fertig-Marke) -> übernehmen; Prozess ohne Manifest beendet oder Zeitgrenze -> zurück."""
    import time
    from elucida.formats import mnova_cli as MX
    m = MX.read_manifest(job["out"], job["token"])
    if m is not None and (m.get("done") or m.get("refused") or m.get("error")):
        return _mx_done(main, job, m)
    if job["proc"].poll() is not None:                     # beendet: noch zweimal nachsehen (Datei eben geschrieben?)
        job["exited"] = job.get("exited", 0) + 1
        if job["exited"] > 2:
            return _mx_done(main, job, why="nmr_mx_exit")
    elif time.monotonic() - job["t0"] > MX.TIMEOUT_S:
        return _mx_done(main, job, why="nmr_mx_timeout")
    main.statusBar().showMessage(T("nmr_mx_running", name=Path(job["dst"]).name, s=int(time.monotonic() - job["t0"])),
                                 1500)
    if main._built("nmr"):
        main.nmr_tab.fill_mx_run()


def _mx_kill(job):
    """Nur den eigenen MNova-Prozess beenden (headless beendet sich MNova nicht immer; Batch-Beleg), nie einen anderen."""
    import subprocess
    p = job.get("proc")
    if p is None or p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.kill()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


_MX_REFUSED = {"gui": "nmr_mx_gui", "doc": "nmr_mx_doc", "open": "nmr_mx_open"}


def _mx_done(main, job, m=None, why=None, detail=""):
    """Export beendet: eigenen Prozess beenden, Ergebnis übernehmen oder auf den bisherigen Weg zurückfallen (immer mit
    Einblendung), eigenen Temp-Ordner löschen, nächsten Export starten."""
    import shutil
    t = job.pop("timer", None)
    if t is not None:
        t.stop()
        t.deleteLater()
    _mx_kill(job)
    jobs = main.__dict__.get("_mnova_jobs") or []
    if job in jobs:
        jobs.remove(job)
    dst = job["dst"]
    try:
        if main.project_dir != job["pdir"]:               # Verbindung inzwischen gewechselt: nie in die falsche
            main.notify(T("nmr_mx_dropped", name=Path(dst).name))
            return
        if m is not None and m.get("refused"):
            why = _MX_REFUSED.get(m["refused"], "nmr_mx_failed")
        elif m is not None and m.get("error"):
            why, detail = "nmr_mx_failed", str(m["error"])
        tab = main.nmr_tab
        if tab.text_timer.isActive():                       # gerade getippter Text zuerst in den Zustand (sonst überschrieben)
            tab.text_timer.stop()
            tab.text_changed()
        if why is None:
            try:
                n = tab.take_mnova_export(dst, job["out"], m)
            except Exception as ex:                        # zurückgerollt: bisheriger Weg mit Grund, nie halb übernommen
                n, why, detail = 0, "nmr_mx_failed", str(ex)
            if n:
                return main.notify(T("nmr_mx_done", n=n, name=Path(dst).name))
            why = why or "nmr_mx_empty"
        tab.mnova_rows(dst, why, detail)
    finally:
        if job.get("tmp"):
            shutil.rmtree(job["tmp"], ignore_errors=True)  # nur Elucidas eigener Temp-Ordner (Kopie + Ausgabe)
        if main._built("nmr"):
            main.nmr_tab.fill_mx_run()
        _mx_next(main)


FIG_W_CM = 16.0                    # Breite der Spektren in Word (zwei Abbildungen je Seite, wie in der SI)
OWN_SIZE_CM = (16.0, 11.0)         # eigene Spektren: Standardgröße der Abbildungen (project.md), Achse wie die Vorlage
PAGE_INSET_CAP = (14, 4, 14, 8)    # Unterschrift unter dem eigenen Spektrum (Seitenrand wie die Abbildung)



class _PreviewCard(QWidget):
    """Karte um die Vorschau (wie `CanvasHost(page=True)`): abgerundet, Rahmenlinie, Canvas-Farbe, Innenrand 10. Das
    übernommene MNova-Bild selbst bleibt unverändert."""

    def __init__(self, child):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.addWidget(child)

    def paintEvent(self, ev):
        from PySide6.QtGui import QColor, QPainter, QPen
        from elucida.app import canvas_theme as CANVAS
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(STYLE.colors()["border"]), 1))
        p.setBrush(QColor("#000000" if CANVAS._dark else "#ffffff"))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

class _ViewCards:
    """Halter für die Karten der NMR-Ansicht, solange es die Ansicht noch nicht gibt (`NMRTab.view`): dieselben Felder
    (`_boxes`) und dieselbe Anzeige (`opts`) gehen danach an die Ansicht."""

    def __init__(self, tab):
        from elucida.tabs import nmr_view as NV
        self.tab, self.opts, self._boxes = tab, dict(NV.SHOW_DEFAULT), {}

    def _set_show(self, k, v):
        if self.tab._view is not None:                    # ohne Ansicht sind die Karten verborgen (kein Spektrum)
            self.tab._view._set_show(k, v)


class NMRTab(QWidget):
    STATE_KEY = "nmr"
    STEP_LABELS = ("step_spectra", "step_nmr_line", "step_display")     # Schritte der linken Spalte
    DEFAULT_STATE = dict(spectra=[], current=None, text="", assign={}, raw=[], mnova=[])

    def __init__(self, main, state):
        super().__init__()
        self.main, self.st = main, state
        for k, v in self.DEFAULT_STATE.items():
            self.st.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)
        self._loading = False
        self.text_timer = QTimer(self, singleShot=True, interval=500)
        self.text_timer.timeout.connect(self.text_changed)
        self._view = None                                  # Ansicht der eigenen Spektren: erst bei Bedarf (`view`)
        self._cards = _ViewCards(self)                     # ihre Karten (Darstellung, Spektrum) gibt es immer
        self.phase_timer = QTimer(self, singleShot=True, interval=400)   # Phase nach dem Ziehen übernehmen
        self.phase_timer.timeout.connect(self.commit_phase)
        self._raw_s = None                                 # Spektrum, das die Ansicht gerade zeigt (uid, Referenz)
        self._ycache = {}                                  # uid -> letzter gerechneter Stand (raw_y)
        self._sel_uid = None                               # gewähltes Signal der Auswertung
        self._showing = False
        self._view2d = None                                # 2D-Ansicht, erst bei Bedarf
        left = QWidget()
        self.lv = QVBoxLayout(left)
        self.build_controls()
        self.lv.addStretch(1)
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ls.setMinimumWidth(max(460, left.minimumSizeHint().width() + 24))
        from elucida.tabs.base import EmptyGuide
        prev = QWidget()
        rv = QVBoxLayout(prev)
        rv.setContentsMargins(0, 0, 0, 0)
        self.lbl_prev = QLabel("", alignment=Qt.AlignCenter, wordWrap=True)
        from elucida.app.canvas_theme import register
        register(self.lbl_prev)
        # Größe kommt vom Layout, nie vom Pixmap (sonst Mindestgröße = altes Bild: wächst nicht nach, schrumpft nicht)
        self.lbl_prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lbl_prev.setMinimumSize(200, 200)
        self.lbl_prev.installEventFilter(self)             # Struktur in der Vorschau ziehen, Größenänderung
        self._drag_rect, self._drag, self._pm_size = None, None, (1, 1)
        rv.addWidget(_PreviewCard(self.lbl_prev), 1)           # Karte in Canvas-Farbe wie die Abbildungen der anderen Tabs
        self.lbl_rng = STYLE.HintLabel("", wordWrap=True)     # Signal der SI-Zeile außerhalb der Achse (leer = keine Zeile)
        self.lbl_rng.setStyleSheet(f"color: {STYLE.WARN_COLOR};")
        self.lbl_rng.setContentsMargins(*PAGE_INSET_CAP)
        rv.addWidget(self.lbl_rng)
        self.lbl_cap = QLabel("", wordWrap=True)
        self.lbl_cap.setTextFormat(Qt.RichText)
        self.lbl_cap.setAlignment(Qt.AlignCenter)             # mittig unter der Abbildung
        self.lbl_cap.setMinimumHeight(56)
        rv.addWidget(self.lbl_cap)
        right = QWidget()
        self.preview_stack = QStackedWidget()             # 0 = Anleitung (leerer Tab, wie die anderen Tabs), 1 = Vorschau
        from elucida.tabs.base import PAGE_TOP, page_wrap, result_tabs
        self.preview_stack.addWidget(page_wrap(EmptyGuide("nmr", (T("nmr_add"), self.add_svg), export=self)))
        self.preview_stack.addWidget(page_wrap(prev))
        raw = QWidget()                                    # 2 = eigenes Spektrum (Mnova-Bedienung) + Unterschrift
        rlv = self._raw_lay = QVBoxLayout(raw)
        rlv.setContentsMargins(0, 0, 0, 0)
        self.lbl_cap_raw = QLabel("", wordWrap=True)
        self.lbl_cap_raw.setTextFormat(Qt.RichText)
        self.lbl_cap_raw.setAlignment(Qt.AlignCenter)
        self.lbl_cap_raw.setContentsMargins(*PAGE_INSET_CAP)
        self.lbl_cmp_notes = QLabel("", wordWrap=True)      # Vergleich/Vorhersage: Referenz, Hinweis, Lizenz; Bereich
        self.lbl_cmp_notes.setTextFormat(Qt.RichText)
        self.lbl_cmp_notes.setContentsMargins(*PAGE_INSET_CAP)
        rlv.addWidget(self.lbl_cmp_notes)
        rlv.addWidget(self.lbl_cap_raw)
        self.preview_stack.addWidget(raw)
        p2d = QWidget()                                    # 3 = eigenes 2D-Spektrum (Höhenlinien) + Hinweise
        self._lay2d = QVBoxLayout(p2d)
        self._lay2d.setContentsMargins(0, 0, 0, 0)
        self.lbl_2d = STYLE.HintLabel("", wordWrap=True)
        self.lbl_2d.setStyleSheet(HINT_CSS)
        self._lay2d.addWidget(self.lbl_2d)
        self.lbl_cap_2d = QLabel("", wordWrap=True)
        self.lbl_cap_2d.setTextFormat(Qt.RichText)
        self.lbl_cap_2d.setAlignment(Qt.AlignCenter)
        self.lbl_cap_2d.setContentsMargins(*PAGE_INSET_CAP)
        self._lay2d.addWidget(self.lbl_cap_2d)
        self.preview_stack.addWidget(p2d)
        # Reiter neben der Abbildung wie die Ergebnisseiten der anderen Tabs: Rohdaten (TopSpin, Mnova)
        from elucida.tabs.base import result_page
        self.right_tabs = result_tabs()
        fig = QWidget()                                    # Abbildung: Leiste Einzeln · Überlagert · Gestapelt darüber
        fv = QVBoxLayout(fig)
        fv.setContentsMargins(0, 0, 0, 0)
        fv.setSpacing(6)
        fv.addWidget(self.build_cmp_bar())
        fv.addWidget(self.preview_stack, 1)
        self.right_tabs.addTab(fig, T("tab_figure"))
        self.right_tabs.addTab(result_page(self.grp_raw), T("nmr_raw"))
        si = QWidget()                                     # eigenes Spektrum, wie es in die SI geht (mit Struktur)
        sv = QVBoxLayout(si)
        sv.setContentsMargins(0, 0, 0, 0)
        self.lbl_si_prev = QLabel("", alignment=Qt.AlignCenter, wordWrap=True)
        self.lbl_si_prev.setStyleSheet("font-size: 15px; " + STYLE.HINT_CSS)     # Platzhalter groß und grau (ui.md)
        self.lbl_si_prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lbl_si_prev.setMinimumSize(200, 200)
        register(self.lbl_si_prev)
        self.lbl_si_state = STYLE.HintLabel("", wordWrap=True)   # nicht freigegeben: was stattdessen in die SI kommt
        self.lbl_si_state.setStyleSheet(f"color: {STYLE.WARN_COLOR};")
        sv.addWidget(self.lbl_si_state)
        sv.addWidget(_PreviewCard(self.lbl_si_prev), 1)
        self.si_page = page_wrap(si)
        self.right_tabs.addTab(self.si_page, T("nmr_si_fig"))
        self.right_tabs.set_empty(self.si_page, True)
        self.right_tabs.currentChanged.connect(lambda _i: self.update_si_preview())
        from elucida.tabs.base import kpi_corner
        self.kpi_box = kpi_corner(self.right_tabs)           # Kernzahl gegen die Summenformel (fill_count)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, PAGE_TOP, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(self.right_tabs)
        from elucida.tabs.base import footer, side_bar
        split = QSplitter(Qt.Horizontal)
        split.addWidget(footer(self, ls, clear=True))
        rl.addWidget(side_bar(self.btn_export, stretch_at=0))   # Hauptknopf rechts unter der Vorschau wie in allen Tabs
        split.addWidget(right)
        split.setSizes([500, 900])
        from elucida.tabs.base import fit_footer_column
        fit_footer_column(self, split)                   # Rand/Abstände der Spalte wie in den übrigen Tabs, Schritte
        # Reiter rechts und Bildlauf links überstehen einen Neuaufbau (Sprache, Design, Rückgängig) wie in den FigureTabs
        self._left_parts = (None, None, self._footer_parts[0], None)
        lay = QHBoxLayout(self)                          # kein QVBoxLayout: tidy(Tab) rückt sonst alles ein
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self.sync_widgets()

    def showEvent(self, ev):
        super().showEvent(ev)
        QTimer.singleShot(0, self, self.focus_view)              # Tab geöffnet: Tasten gehen gleich an das Spektrum (121)

    def focus_view(self):
        """Eigenes Spektrum sichtbar: Fokus an die Ansicht (nie die Ansicht dafür bauen, `_view`)."""
        try:
            if self._view is not None and self.isVisible() and self.preview_stack.currentIndex() == 2:
                return self._view.take_focus()
        except RuntimeError:                               # Tab inzwischen ersetzt
            pass
        return False

    # -- Bedienelemente -------------------------------------------------------------------
    def build_controls(self):
        # Mnova-Dokumente der Verbindung oben in der Spalte (Nutzerwunsch: nicht im Reiter Rohdaten verstecken)
        g = QGroupBox("MNova")
        v = QVBoxLayout(g)
        self.lbl_mnova = QLabel("", wordWrap=True)
        v.addWidget(self.lbl_mnova)
        self.lbl_mnova_refused = STYLE.HintLabel("", wordWrap=True)   # zuletzt nicht gelesene Spektren (2D, Ungeprüftes)
        self.lbl_mnova_refused.setStyleSheet(f"color: {STYLE.WARN_COLOR};")
        v.addWidget(self.lbl_mnova_refused)
        self.lbl_mx_run = STYLE.HintLabel("", wordWrap=True)    # Export in MNova läuft (Fortschritt), sonst leer
        self.lbl_mx_run.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_mx_run)
        row = QHBoxLayout()
        for txt, tip, fn in ((T("mnova_store"), T("nmr_mnova_tip"), self.add_mnova),
                             (T("mnova_open"), T("mnova_open_tip"), self.open_mnova)):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

        g = QGroupBox(T("nmr_spectra"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, tip, fn in ((T("nmr_add"), "", self.add_svg), (T("nmr_add_raw"), T("nmr_add_raw_tip"), self.add_raw),
                             (T("remove"), "", self.remove_spectrum)):
            b = QPushButton(txt)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels([T("nmr_file"), T("nmr_nuclei"), T("nmr_kind"), T("nmr_range"), ""])
        self.tbl.horizontalHeader().moveSection(4, 0)      # Häkchen (Vergleich) vorn, ohne Kopftext
        self.tbl.horizontalHeaderItem(4).setToolTip(T("nmr_cmp_check_tip"))
        self.tbl.itemChanged.connect(self.cmp_member_toggled)
        self.tbl.horizontalHeaderItem(3).setToolTip(T("nmr_range_tip"))
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setMinimumHeight(130)
        self.tbl.itemSelectionChanged.connect(self.spectrum_selected)
        v.addWidget(self.tbl)
        STYLE.hide_when_empty(self.tbl)
        hint = QLabel(T("nmr_order_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.lv.addWidget(g)

        # Rohdaten: TopSpin-Experimente (ganz, nach Art sortiert) und Mnova-Dokumente – nur ablegen, nicht auswerten;
        # als Reiter neben der Abbildung (siehe __init__), nicht in der linken Spalte
        g = QGroupBox(T("nmr_raw"))
        v = QVBoxLayout(g)
        hint = QLabel(T("nmr_raw_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.tbl_raw = QTableWidget(0, 4)
        STYLE.empty_note(self.tbl_raw, T("tbl_empty_raw"))
        self.tbl_raw.setHorizontalHeaderLabels([T("nmr_raw_kind"), T("nmr_raw_name"), T("nmr_raw_pulprog"),
                                                T("nmr_raw_spectrum")])
        self.tbl_raw.verticalHeader().setVisible(False)
        self.tbl_raw.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)     # vier gleich breite Spalten, mittig
        self.tbl_raw.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_raw.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_raw.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_raw.setToolTip(T("nmr_raw_open_tip"))
        self.tbl_raw.itemDoubleClicked.connect(lambda it: QDesktopServices.openUrl(
            QUrl.fromLocalFile(self.tbl_raw.item(it.row(), 0).data(Qt.UserRole))))
        v.addWidget(self.tbl_raw)
        row = QHBoxLayout()
        for txt, tip, fn, ic in ((T("nmr_topspin"), T("nmr_topspin_tip"), self.add_topspin, "open"),
                                 (T("nmr_raw_show"), T("nmr_raw_show_tip"), self.show_raw_row, None),
                                 (T("remove"), T("nmr_raw_remove_tip"), self.remove_raw, None)):
            b = QPushButton(txt)
            if ic:
                b.setIcon(STYLE.icon(ic))                   # kein Hauptknopf: Symbol in Textfarbe (weiß war hell unsichtbar)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        g.setProperty("hug", True)                         # Karte so hoch wie Tabelle und Knöpfe (result_page)
        self.grp_raw = g

        g = QGroupBox(T("nmr_selected"))
        f = make_form(g)
        self.cmb_source = QComboBox()                        # Quelle: Mnova-SVG (Standard) oder Bruker-Rohdaten
        for k in SOURCES:
            self.cmb_source.addItem(T("nmr_src_" + k), k)
        self.cmb_source.setToolTip(T("nmr_src_tip"))
        self.cmb_source.currentIndexChanged.connect(self.source_changed)
        f.addRow(T("nmr_src"), self.cmb_source)
        self.cb_si_use = QCheckBox(T("nmr_si_use"))       # eigenes Spektrum ausdrücklich für die SI (je Kern höchstens eines)
        self.cb_si_use.setProperty("chip_here", True)
        self.cb_si_use.setToolTip(T("nmr_si_use_long"))
        self.cb_si_use.toggled.connect(self.si_use_toggled)
        f.addRow(self.cb_si_use)
        self.cb_2d_nominal = QCheckBox(T("nmr_2d_nominal"))  # 2D ohne referenziertes 1D: nominelle Achsen ausdrücklich
        self.cb_2d_nominal.setProperty("chip_here", True)
        self.cb_2d_nominal.setToolTip(T("nmr_2d_nominal_long"))
        self.cb_2d_nominal.toggled.connect(self.nominal_2d_toggled)
        f.addRow(self.cb_2d_nominal)
        self._sel_form = f
        self.cmb_mx = QComboBox()                            # exportiertes MNova-Spektrum: Multipletts oder Peaks für die Zeile
        for k in ("mult", "peaks"):
            self.cmb_mx.addItem(T("nmr_mx_use_" + k), k)
        self.cmb_mx.setToolTip(T("nmr_mx_use_tip"))
        self.cmb_mx.currentIndexChanged.connect(self.mx_use_changed)
        f.addRow(T("nmr_mx_use"), self.cmb_mx)
        self.ed_nuc = QLineEdit()
        self.ed_nuc.setPlaceholderText("1H  ·  13C  ·  1H/13C")
        self.ed_nuc.setToolTip(T("nmr_nuclei_tip"))
        self.ed_nuc.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_nuclei"), self.ed_nuc)
        self.lbl_nuc = STYLE.HintLabel("", wordWrap=True)
        self.lbl_nuc.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_nuc)
        self.cmb_kind = QComboBox()
        for k in ("1D",) + KINDS_2D:
            self.cmb_kind.addItem(k, k)
        self.cmb_kind.currentIndexChanged.connect(self.spec_edited)
        f.addRow(T("nmr_kind"), self.cmb_kind)
        self.sp_temp = QDoubleSpinBox(decimals=0, minimum=100, maximum=500, singleStep=1, suffix=" K", value=298)
        self.sp_temp.valueChanged.connect(self.spec_edited)
        f.addRow(T("nmr_temp"), self.sp_temp)
        self.ed_freq = QLineEdit()
        self.ed_freq.setPlaceholderText(T("nmr_freq_ph"))
        self.ed_freq.setToolTip(T("nmr_freq_tip"))
        self.ed_freq.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_freq"), self.ed_freq)
        self.ed_solv = STYLE.ChemEdit()
        self.ed_solv.setPlaceholderText(T("nmr_solv_ph"))
        self.ed_solv.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_solvent"), self.ed_solv)
        row = QHBoxLayout()
        b = QPushButton(T("nmr_bruker"))
        b.setToolTip(T("nmr_bruker_tip"))
        b.clicked.connect(self.add_bruker)
        row.addWidget(b)
        b = QPushButton(T("nmr_bruker_temp"))
        b.setToolTip(T("nmr_bruker_temp_tip"))
        b.clicked.connect(self.temp_from_bruker)
        row.addWidget(b)
        row.addStretch(1)
        f.addRow(row)
        self.lbl_par = STYLE.HintLabel("", wordWrap=True)
        self.lbl_par.setTextFormat(Qt.RichText)
        f.addRow(self.lbl_par)
        # Bruker-Parameter als Tabelle wie alle Tabellen (Windows-Bericht 2026-11-20: vorher loses Textraster ohne
        # Hoch-/Tiefstellung); Werte über RichDelegate (¹H, CDCl₃), kopiert wird der Text
        self._par_html = {}
        self.tbl_par = STYLE.summary_grid([T("xr_par_head"), T("xr_par_value")])
        self.tbl_par.setItemDelegateForColumn(1, STYLE.RichDelegate(
            self.tbl_par, lambda s: self._par_html.get(s) or _h.escape(s)))
        self.tbl_par.elide_col = 1                         # langer Probenkopf: Wert gekürzt (Tooltip), statt quer zu rollen
        f.addRow(self.tbl_par)
        row = QHBoxLayout()
        self.cb_struct = QCheckBox(T("nmr_struct_on"))
        self.cb_struct.setProperty("chip_here", True)        # gehört zur Zeile „Struktur“ darüber
        self.cb_struct.setToolTip(T("nmr_struct_tip"))
        self.cb_struct.toggled.connect(self.spec_edited)
        row.addWidget(self.cb_struct)
        self.cmb_spos = QComboBox()
        for k in STRUCT_POS:
            self.cmb_spos.addItem(T("nmr_pos_" + k), k)
        self.cmb_spos.currentIndexChanged.connect(self.spec_edited)
        row.addWidget(self.cmb_spos)
        self.sp_sw = QDoubleSpinBox(decimals=0, minimum=5, maximum=60, singleStep=1, suffix=" %", value=20)
        self.sp_sw.valueChanged.connect(self.spec_edited)
        row.addWidget(self.sp_sw)
        row.addStretch(1)
        f.addRow(T("nmr_struct"), row)
        row = QHBoxLayout()                                  # unter der Struktur: Nummer der Verbindung, Messangaben
        self.cb_lab_no = QCheckBox(T("nmr_label_no"))
        self.cb_lab_info = QCheckBox(T("nmr_label_info"))
        for cb, key in ((self.cb_lab_no, "label_no"), (self.cb_lab_info, "label_info")):
            cb.setProperty("chip_here", True)
            cb.setToolTip(T("nmr_" + key + "_long"))
            cb.setChecked(self.st.get(key, True))
            cb.toggled.connect(self.label_toggled)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow("", row)
        row = QHBoxLayout()
        self.lbl_struct = QLabel("", wordWrap=True)
        self.lbl_struct.setStyleSheet(HINT_CSS)
        row.addWidget(self.lbl_struct, 1)
        b = QPushButton(T("nmr_struct_pick"))
        b.setToolTip(T("nmr_struct_pick_tip"))
        b.clicked.connect(self.pick_structure)
        row.addWidget(b)
        f.addRow(row)
        self.lv.addWidget(g)
        self.build_cmp_card()
        self.build_raw_cards()

        g = QGroupBox(T("nmr_text"))
        v = QVBoxLayout(g)
        hint = QLabel(T("nmr_text_short"), wordWrap=True)       # kurz; die ganze Erklärung im Tooltip
        hint.setToolTip(T("nmr_text_hint"))
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.lbl_mx = STYLE.HintLabel("", wordWrap=True)      # Zeilen aus exportierten MNova-Dokumenten: Hinweise, Vorschlag
        self.lbl_mx.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_mx)
        self.row_mx = QWidget()                              # Vorschlag nie still über vorhandenen Text: übernehmen/behalten
        row = QHBoxLayout(self.row_mx)
        row.setContentsMargins(0, 0, 0, 0)
        for key, fn in (("nmr_mx_adopt", self.mx_adopt), ("nmr_mx_keep", self.mx_keep)):
            b = QPushButton(T(key))
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addWidget(self.row_mx)
        self.ed_text = QPlainTextEdit()
        self.ed_text.setPlaceholderText("1H NMR (501 MHz, CDCl3) δ 7.52 – 7.45 (m, 2H), …\n"
                                        "13C NMR (126 MHz, CDCl3) δ 141.20, 128.35, …")
        self.ed_text.setMaximumHeight(120)
        self.ed_text.setToolTip(T("nmr_text_hint"))
        self.ed_text.textChanged.connect(lambda: None if self._loading else self.text_timer.start())
        v.addWidget(self.ed_text)
        self.tbl_sig = QTableWidget(0, 6)
        self.tbl_sig.setHorizontalHeaderLabels([T("nmr_nuc_short"), "δ [ppm]", T("nmr_mult"), "J [Hz]", "H",
                                                T("nmr_assign")])
        self.tbl_sig.verticalHeader().setVisible(False)
        for c_ in range(5):                                  # schmale Spalten nach Inhalt, Zuordnung nimmt den Rest:
            self.tbl_sig.horizontalHeader().setSectionResizeMode(c_, QHeaderView.ResizeToContents)   # kein Querrollen
        self.tbl_sig.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tbl_sig.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tbl_sig.setMinimumHeight(170)
        self.tbl_sig.setToolTip(T("nmr_assign_tip"))
        self.tbl_sig.itemChanged.connect(self.assign_edited)
        v.addWidget(self.tbl_sig)
        # Kernzahl gegen die Summenformel der Verbindung: je Kern eine Zeile, als Tabelle (nie als Text unter der Tabelle)
        self.tbl_count = STYLE.summary_grid([T("nmr_nuc_short"), T("nmr_count_found"), T("nmr_count_formula"),
                                             T("nmr_count_note")])
        self.tbl_count.setToolTip(T("nmr_count_tip"))
        v.addWidget(self.tbl_count)
        self.lbl_count = STYLE.HintLabel("", wordWrap=True)   # ohne Summenformel: sagen, was fehlt (keine leere Fläche)
        self.lbl_count.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_count)
        # ¹³C-Signale bei Restsignalen/Verunreinigungen dieses Lösungsmittels (Fulmer 2010): Chip + zweite Tabelle
        self.cb_imp = QCheckBox(T("nmr_imp_chip"))
        self.cb_imp.setToolTip(T("nmr_imp_chip_long"))
        self.cb_imp.setChecked(self.st.get("imp_hint", True))
        self.cb_imp.toggled.connect(self.imp_toggled)
        v.addWidget(self.cb_imp)
        self.tbl_imp = STYLE.summary_grid([T("nmr_nuc_short"), "δ [ppm]", T("nmr_imp_lit"), T("nmr_imp_match")])
        self.tbl_imp.setToolTip(T("nmr_imp_tip"))
        v.addWidget(self.tbl_imp)
        self.lbl_imp = STYLE.HintLabel("", wordWrap=True)     # Referenzversatz aus dem beschrifteten Lösungsmittelsignal
        self.lbl_imp.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_imp)
        b = STYLE.copy_button(T("nmr_copy"))
        b.clicked.connect(self.copy_lines)
        v.addWidget(STYLE.text_head(T("line_nmr"), b))     # „Kopieren“ direkt an der Zeile, die es kopiert
        self.txt_line = QTextBrowser()
        self.txt_line.setMaximumHeight(120)
        v.addWidget(self.txt_line)
        self.lbl_own = STYLE.HintLabel("", wordWrap=True)    # Zeilen aus eigenen Spektren: Herkunft und Vorbehalte
        self.lbl_own.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_own)
        row = QHBoxLayout()
        b = QPushButton(T("nmr_peaks"))
        b.setToolTip(T("nmr_peaks_tip"))
        b.clicked.connect(self.peaks_from_svg)
        row.addWidget(b)
        b = QPushButton(T("nmr_word"))
        b.setToolTip(T("nmr_word_tip"))
        b.clicked.connect(self.export_word)                # dieselbe Exportmeldung wie Strg+E
        if getattr(self.main, "EXPORT_TAB", False):        # R7: Export im Tab „Export“, Strg+E bleibt
            b.hide()
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)
        # Darstellung der eigenen Spektren: Karten der Ansicht (Schritt „Darstellung“ über den Kartentitel)
        from elucida.tabs.nmr_view import NMRView
        # ungebundene Methoden auf dem Halter: Karten ohne die Ansicht bauen (sie kostet ~0.1 s und setzt die Schriften
        # von matplotlib um, das verlangsamte den ersten Klick auf den Tab um ~0.4 s)
        for g, key in ((NMRView.display_card(self._cards), "nmr_raw_display"),
                       (NMRView.style_card(self._cards), "nmr_raw_style")):
            g.setTitle(T(key))
            if key == "nmr_raw_display":                   # gesperrt (MNova-SVG): der Grund als Satz oben im Schritt
                self.lbl_view_lock = QLabel(T("nmr_raw_only"), objectName="cardHint", wordWrap=True)
                self.lv.addWidget(self.lbl_view_lock)
            self.lv.addWidget(g)
            if key == "nmr_raw_display":                   # ein Satz je Schritt, die zweite Karte verschwindet nur
                self.ed_marks = STYLE.ChemEdit()           # Bedeutung der Marken (*, †) für die Unterschrift
                self.ed_marks.setPlaceholderText(T("nmr_marks_ph"))
                self.ed_marks.setToolTip(T("nmr_marks_tip"))
                self.ed_marks.editingFinished.connect(self.marks_note_changed)
                g.layout().addRow(T("nmr_marks_note"), self.ed_marks)
                # Bereich der SI-Abbildung: „auto“ = −1…11 bzw. −10…220 ppm, nie die letzte Zoomstufe der Ansicht
                row = QHBoxLayout()
                self.cb_rng = QCheckBox(T("auto"))
                self.cb_rng.setChecked(True)
                self.sp_rng = [QDoubleSpinBox(decimals=2, minimum=-1000.0, maximum=1000.0, singleStep=0.5, suffix=" ppm")
                               for _ in range(2)]
                for w_ in (self.cb_rng, self.sp_rng[0], QLabel("–"), self.sp_rng[1]):
                    row.addWidget(w_)
                for sp_ in self.sp_rng:
                    sp_.setToolTip(T("nmr_si_range_tip"))
                    sp_.editingFinished.connect(self.si_range_changed)
                self.cb_rng.toggled.connect(self.si_range_changed)
                g.layout().addRow(T("nmr_si_range"), row)
            self._view_cards.append(g)                     # bei MNova-SVG sichtbar, aber ausgegraut (R8), Grund im Tooltip
            self.raw_cards.append(g)
        # feste Texte der eigenen Spektren (Achsentitel, Titel; 1D und 2D): derselbe Mechanismus wie in allen Tabs
        from elucida.tabs import base as TABS
        self.texts = TABS.PageTexts(self, self._texts_view, self._texts_redraw)
        self.lv.addWidget(self.texts.box)
        self._view_cards.append(self.texts.box)
        self.raw_cards.append(self.texts.box)

    def _texts_view(self):
        """Ansicht der Karte „Beschriftungen im Bild“: eigenes 2D-Spektrum oder 1D."""
        ps = getattr(self, "preview_stack", None)          # die Karte fragt schon beim Bauen (vor der Vorschau)
        return "2d" if ps is not None and ps.currentIndex() == 3 else "1d"

    def _texts_redraw(self):
        v = self._view2d if self._texts_view() == "2d" else self._view
        if v is not None:
            v.redraw()

    def _texts_fill(self, v):
        """Nach dem Zeichnen der gezeigten Ansicht: Zeilen der Karte (nur wenn sich etwas geändert hat, Ziehen und
        Zoomen zeichnen oft)."""
        if v is not (self._view2d if self._texts_view() == "2d" else self._view):
            return
        sig = (self._texts_view(), repr(v.text_rows), repr(self.st.get("text_over")))
        if sig != getattr(self, "_texts_sig", None):
            self._texts_sig = sig
            self.texts.fill(v)

    def _text_tag(self):
        """Eigene Texte für den Namen zwischengespeicherter SVG (ohne eigene Texte: Name wie bisher)."""
        over = self.st.get("text_over")
        return [over] if over else []

    @property
    def view(self):
        """Ansicht der eigenen Spektren (tabs/nmr_view.py), beim ersten Zugriff gebaut; teilt Anzeige und Felder mit
        den Karten."""
        if self._view is None:
            from elucida.tabs.nmr_view import NMRView
            v = self._view = NMRView()
            h = self._cards
            v.opts, v._boxes, v.cmb_mult, v.cmb_mark = h.opts, h._boxes, h.cmb_mult, h.cmb_mark
            v.set_phase_callback(self.phase_preview)
            v.get_text_over, v.after_draw = (lambda: self.st.get("text_over")), (lambda: self._texts_fill(v))
            v.phase_changed.connect(lambda *_: self.phase_timer.start())
            v.reference_clicked.connect(self.reference_clicked)
            v.display_changed.connect(self.view_display_changed)
            v.insets_changed.connect(lambda _items: self.view_display_changed(v.display()))
            v.integrals_changed.connect(self.view_integrals_changed)
            v.multiplets_changed.connect(self.view_multiplets_changed)
            v.peaks_changed.connect(self.view_peaks_changed)
            v.marks_changed.connect(self.view_marks_changed)
            v.multiplet_requested.connect(self.multiplet_requested)
            v.peak_pick_requested.connect(self.peak_pick_requested)
            v.selection_changed.connect(self.view_selection_changed)
            v.view_changed.connect(self.view_zoomed)
            self._raw_lay.insertWidget(0, v, 1)
            # Modus (I, K, J …) übersteht den Neuaufbau (Sprache, Design, Rückgängig) wie Reiter, Bildlauf und Zoom; je
            # Spektrum, damit Phase/Schnitt nie in ein anderes Spektrum mitgehen
            modes = self.main.__dict__.setdefault("_nmr_view_mode", {})
            v.mode_changed.connect(lambda m: modes.__setitem__((self._raw_s or (None,))[0], m))
        return self._view

    def build_raw_cards(self):
        """Karten „Verarbeitung“ und „Referenzierung“ (Schritt Auswertung) für Spektren aus Bruker-Rohdaten; bei
        Mnova-Spektren steht stattdessen ein Satz, wofür sie gelten."""
        self.raw_cards = []
        g = QGroupBox(T("nmr_proc_card"))
        f = make_form(g)
        self.lbl_phase = STYLE.HintLabel("", wordWrap=True)
        f.addRow(T("nmr_phase"), self.lbl_phase)
        row = QHBoxLayout()
        self.btn_phase_ok, self.btn_acme, self.btn_phase_manual = (QPushButton(T(k)) for k in (
            "nmr_phase_ok", "nmr_phase_acme", "nmr_phase_manual"))
        for b, tip, fn in ((self.btn_phase_ok, "nmr_phase_ok_tip", self.confirm_phase),
                           (self.btn_acme, "nmr_phase_acme_tip", self.acme_phase),
                           (self.btn_phase_manual, "nmr_phase_manual_tip", lambda: (self.view.set_mode("phase"),
                                                                                    self.view.canvas.setFocus()))):
            b.setToolTip(T(tip))
            b.clicked.connect(fn)
            row.addWidget(b)
        f.addRow("", row)
        self.cmb_baseline = QComboBox()                    # Feld statt Kästchen: bleibt unter den Phasenknöpfen
        for k, data in (("auto", "poly5"), ("bernstein3", "bernstein3"), ("off", "off")):   # Standard Polynom 5 (110)
            self.cmb_baseline.addItem(T("nmr_baseline_" + k), data)
        self.cmb_baseline.setToolTip(T("nmr_baseline_long"))
        self.cmb_baseline.currentIndexChanged.connect(lambda _i: self.baseline_changed(self.cmb_baseline.currentData()))
        f.addRow(T("nmr_baseline"), self.cmb_baseline)
        self.lbl_proc = STYLE.HintLabel("", wordWrap=True)
        self.lbl_proc.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_proc)
        self.lv.addWidget(g)
        STYLE.hint_when_disabled(g, T("nmr_raw_only_cards"))   # nennt die Karten: darunter folgt die NMR-Zeile (jede Quelle)
        self.raw_cards.append(g)

        g = QGroupBox(T("nmr_ref_card"))
        f = make_form(g)
        self.lbl_ref = STYLE.HintLabel("", wordWrap=True)
        f.addRow(T("nmr_ref_state"), self.lbl_ref)
        self.sp_ref = QDoubleSpinBox(decimals=3, minimum=-1000.0, maximum=1000.0, singleStep=0.01, suffix=" ppm")
        self.sp_ref.setToolTip(T("nmr_ref_target_tip"))
        self.sp_ref.valueChanged.connect(self.ref_target_changed)
        f.addRow(T("nmr_ref_target"), self.sp_ref)
        row = QHBoxLayout()
        self.btn_ref_ok, self.btn_ref_click = QPushButton(T("nmr_ref_ok")), QPushButton(T("nmr_ref_click"))
        for b, tip, fn in ((self.btn_ref_ok, "nmr_ref_ok_tip", self.confirm_ref),
                           (self.btn_ref_click, "nmr_ref_click_tip", lambda: (self.view.set_mode("reference"),
                                                                              self.view.canvas.setFocus()))):
            b.setToolTip(T(tip))
            b.clicked.connect(fn)
            row.addWidget(b)
        f.addRow("", row)
        self.btn_unified = QPushButton(T("nmr_xi_btn"))   # X-Kerne: Unified Scale über das ¹H derselben Probe (eigene
        self.btn_unified.setToolTip(T("nmr_xi_tip"))      # Zeile, nur bei X-Kernen: zu dritt passte „Spitze wählen“ nicht)
        self.btn_unified.clicked.connect(self.unified_ref)
        row = self._xi_row = QHBoxLayout()
        row.addWidget(self.btn_unified)
        f.addRow("", row)
        self._ref_form = f
        self.cmb_xi15 = QComboBox()                        # ¹⁵N: Skala wählt der Nutzer (Zeile nur bei ¹⁵N)
        for k in ("MeNO2", "NH3"):
            self.cmb_xi15.addItem(T("nmr_xi15_" + k), k)
        self.cmb_xi15.setToolTip(T("nmr_xi15_tip"))
        f.addRow(T("nmr_xi15"), self.cmb_xi15)
        self._xi15_label = f.labelForField(self.cmb_xi15)
        self.lbl_ref_note = STYLE.HintLabel("", wordWrap=True)
        self.lbl_ref_note.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_ref_note)
        self.lv.addWidget(g)
        self.raw_cards.append(g)
        self._quiet_cards = [g]
        self._view_cards = []
        self.build_ana_card()

    # -- Zustand --------------------------------------------------------------------------
    def spectra(self):
        return sorted(self.st["spectra"], key=sort_key)

    def current(self):
        for s in self.st["spectra"]:
            if s["uid"] == self.st.get("current"):
                return s
        sp = self.spectra()
        return sp[0] if sp else None

    def blocks(self):
        """Was die SI je Kern druckt (Mnova-Bericht oder freigegebenes eigenes Spektrum): `printed_blocks`."""
        return self.printed()[0]

    def printed(self):
        return printed_blocks(self.st, self._nh)

    def _nh(self, s, g):
        """Kerne eines Signals aus den Rohdaten (Integral × Normierung); ohne lesbare Rohdaten die eingegebenen."""
        try:
            ds = self.raw_ds(s)
            c = self.raw_y(s, ds)
            return self.signal_nh(g, self.norm_factor(s, c, ds), c, ds)
        except (OSError, ValueError):
            return g.get("nH")

    def struct_w(self):
        """Größe der Struktur in % der Bildbreite – eine für alle Spektren (ältere Projekte: je Spektrum)."""
        if "struct_w" not in self.st:
            self.st["struct_w"] = float(next((s["struct_w"] for s in self.st["spectra"] if s.get("struct_w")), 20.0))
        return float(self.st["struct_w"])

    def peaks_from_svg(self):
        """Zeile „13C NMR (126 MHz, CDCl3) δ 141.20, …“ aus den Peaklabels des gewählten 1D-Spektrums (nicht ¹H:
        dort braucht es den Multiplettbericht); ersetzt eine vorhandene Zeile desselben Kerns."""
        s = self.current()
        try:
            line, n = svg_peak_line(s, self.blocks())
        except ValueError as ex:
            return self.main.error(str(ex))
        nuc = s["nuclei"][0]
        lines = [ln for ln in (self.st.get("text") or "").splitlines() if ln.strip()
                 and not re.match(rf"\s*{re.escape(nuc)}\s*(?:\{{[^}}]*\}})?\s*NMR", ln)]
        self.ed_text.setPlainText("\n".join(lines + [line]))
        self.text_changed()
        self.main.statusBar().showMessage(T("nmr_peaks_done", n=n, nuc=nuc), 8000)

    def compound_name(self):
        comp = getattr(self.main, "compound", None) or {}
        return comp.get("name") or (Path(self.main.project_dir).name if self.main.project_dir else "")

    def compound_changed(self):
        """Name in der Unterschrift, Struktur der Verbindung; nicht sync_widgets (verwürfe gerade getippten Text)."""
        sp_ = self.structure_path()
        self.lbl_struct.setText(T("nmr_struct_from", f=Path(sp_).name) if sp_ else T("nmr_struct_none"))
        self.fill_count()                                  # Summenformel geändert
        self.update_preview()

    def sync_widgets(self):
        self._loading = True
        sp = self.spectra()
        self.tbl.setRowCount(len(sp))
        bl = self.blocks()
        for r, s in enumerate(sp):
            nuc = sup_nuclei("/".join(s.get("nuclei") or []))
            ok, rtxt, out = self.range_state(s, bl)
            name = T("nmr_src_row_mnova" if s.get("mnova_doc") else "nmr_src_row", n=Path(s["file"]).name) \
                if s.get("source") == "bruker" else Path(s["file"]).name
            for c, val in enumerate((name, nuc or "?", s.get("kind"),
                                     rtxt if ok is None else ("✓ " if ok else "⚠ ") + rtxt)):
                it = QTableWidgetItem(val)
                if c == 0 and s.get("mnova_doc") and s.get("source") == "bruker":
                    it.setToolTip(T("nmr_src_mnova_doc") + ": " + Path(s["mnova_doc"]).name)
                if c == 1 and not s.get("nuclei"):
                    it.setToolTip(T("nmr_nuc_missing"))
                if c == 3:                                   # beschrifteter Bereich gegen −1…10 / 0…200 ppm (nur Hinweis)
                    it.setToolTip(T("nmr_range_tip") + ("\n" + self.range_warning(s, out) if out else ""))
                    if ok is False:
                        from PySide6.QtGui import QBrush, QColor as _QColor
                        it.setForeground(QBrush(_QColor(STYLE.WARN_COLOR)))
                self.tbl.setItem(r, c, it)
        self.fill_cmp_column(sp)
        STYLE.fit_columns(self.tbl)
        cur = self.current()
        if cur is not None:
            self.tbl.selectRow(sp.index(cur))
        if self.ed_text.toPlainText() != (self.st.get("text") or ""):
            self.ed_text.setPlainText(self.st.get("text") or "")
        self.fill_selected()
        self.fill_signals()
        self.fill_raw()
        self.fill_mx()
        self.fill_cmp()
        self._loading = False
        self.update_preview()

    def fill_selected(self):
        s = self.current()
        for w in (self.cmb_source, self.ed_nuc, self.cmb_kind, self.sp_temp, self.ed_freq, self.ed_solv, self.cb_struct,
                  self.cmb_spos, self.sp_sw):
            w.setEnabled(s is not None)
        self.fill_source(s)
        self.fill_mx_use(s)
        try:
            self.fill_raw_cards()
        except (OSError, ValueError):                      # Rohdaten verschwunden: Grund steht in der Vorschau
            for g in self.raw_cards:
                g.setEnabled(False)
        sp_ = self.structure_path()
        self.lbl_struct.setText(T("nmr_struct_from", f=Path(sp_).name) if sp_ else T("nmr_struct_none"))
        if s is None:
            self.lbl_par.setText("")
            STYLE.fill_summary(self.tbl_par, [])
            self.lbl_nuc.setText(T("nmr_select_first"))       # Grund für die gesperrten Felder
            self.lbl_nuc.setStyleSheet(HINT_CSS)
            return
        self.ed_nuc.setText(sup_nuclei("/".join(s.get("nuclei") or [])))   # Massenzahlen hochgestellt (¹H/¹³C)
        self.lbl_nuc.setText(T("nmr_nuc_manual") if not s.get("nuc_auto") else T("nmr_nuc_from_acqus")
                             if s.get("source") == "bruker" else T("nmr_nuc_from_axis"))
        self.lbl_nuc.setStyleSheet(HINT_CSS if s.get("nuclei") else "color: #d9534f;")
        if not s.get("nuclei"):
            self.lbl_nuc.setText(T("nmr_nuc_missing"))
        self.cmb_kind.setCurrentIndex(max(0, self.cmb_kind.findData(s.get("kind", "1D"))))
        self.sp_temp.setValue(float(s.get("temp") or 298))
        fr = "/".join(str((s.get("freqs") or {}).get(n, "")) for n in s.get("nuclei") or [])
        self.ed_freq.setText(fr.rstrip("/"))           # leere erste Frequenz bleibt als „/125“ (Zuordnung)
        self.ed_solv.setText(s.get("solvent") or "")
        self.cb_struct.setChecked(s.get("struct_on", True))
        self.cmb_spos.setCurrentIndex(max(0, self.cmb_spos.findData(s.get("struct_pos", "auto"))))
        self.sp_sw.setValue(self.struct_w())
        p = s.get("params")
        rows = params_rows(p) if p else []
        self._par_html = {txt: html for _, txt, html in rows}
        STYLE.fill_summary(self.tbl_par, [[lab, txt] for lab, txt, _ in rows])
        for r_ in range(self.tbl_par.rowCount()):
            self.tbl_par.item(r_, 1).setToolTip(self.tbl_par.item(r_, 1).text())
        self.lbl_par.setText("" if p else T("nmr_no_bruker"))
        self.lbl_par.setStyleSheet(HINT_CSS)

    def fill_source(self, s):
        """Auswahl „Quelle“: Mnova nur mit SVG/EMF-Datei, Bruker nur mit verknüpftem Experiment."""
        m = self.cmb_source.model()
        has = dict(mnova=s is not None and Path(s["file"]).is_file(), bruker=s is not None and bool(s.get("bruker")))
        for i, k in enumerate(SOURCES):
            m.item(i).setEnabled(has[k])
        # aus einem Mnova-Dokument nachgebaut: Quelle so nennen (nicht „Bruker-Rohdaten“), Schlüssel bleibt „bruker“
        m.item(1).setText(T("nmr_src_mnova_doc" if (s or {}).get("mnova_doc") else "nmr_src_bruker"))
        self.cmb_source.blockSignals(True)
        self.cmb_source.setCurrentIndex(SOURCES.index((s or {}).get("source") or "mnova"))
        self.cmb_source.blockSignals(False)
        self.cb_si_use.blockSignals(True)
        self.cb_si_use.setChecked(bool((s or {}).get("si_use")))
        self.cb_si_use.blockSignals(False)
        self.cb_si_use.setEnabled(s is not None and s.get("source") == "bruker")
        own2d = s is not None and s.get("source") == "bruker" and s.get("kind", "1D") != "1D"
        self.cb_2d_nominal.blockSignals(True)
        self.cb_2d_nominal.setChecked(bool(own2d and (s.get("view2d") or {}).get("nominal_ok")))
        self.cb_2d_nominal.blockSignals(False)
        self.cb_2d_nominal.setEnabled(own2d)
        self.cb_2d_nominal.setVisible(own2d)              # nur beim eigenen 2D: keine toten Felder in der Spalte

    def nominal_2d_toggled(self, on):
        s = self.current()
        if self._loading or s is None or s.get("kind", "1D") == "1D" or bool((s.get("view2d") or {}).get("nominal_ok")) == on:
            return
        s.setdefault("view2d", {})["nominal_ok"] = on
        self.changed()

    def si_use_toggled(self, on):
        """„Für die SI“: dieses eigene Spektrum ersetzt Mnova-Zeile/-Abbildung seines Kerns, sobald Phase und Referenz
        bestätigt sind; je Kern höchstens eines (ein anderes desselben Kerns wird abgewählt, der Hinweis nennt es)."""
        s = self.current()
        if self._loading or s is None or bool(s.get("si_use")) == on:
            return
        s["si_use"] = on
        if on:
            same = lambda x: (x.get("nuclei") or [""])[0] == (s.get("nuclei") or [""])[0] and x.get("kind", "1D") == s.get("kind", "1D")   # noqa: E731
            for x in self.st["spectra"]:
                if x is not s and x.get("si_use") and same(x):
                    x["si_use"] = False
        self.changed()

    def fill_signals(self):
        rows = [(b["nucleus"], sig) for b in self.blocks() for sig in b["signals"]]
        self.tbl_sig.setRowCount(len(rows))
        assign = self.st.get("assign") or {}
        for r, (nuc, sig) in enumerate(rows):
            own = sig.get("uid") is not None                     # eigenes Signal: Zuordnung im Zustand des Signals
            vals = (sup_nuclei(nuc), sig["shift"], sig["mult"], sig["J"], sig["nH"],        # ¹H/¹³C wie in der Liste oben
                    sig["assign"] if own else assign.get(sig_key(nuc, sig), sig["assign"]))
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c < 5:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                else:
                    it.setData(Qt.UserRole, f"own|{sig['uid']}" if own else sig_key(nuc, sig))
                self.tbl_sig.setItem(r, c, it)
        self.fill_count()
        lines = self.nmr_lines()
        self.txt_line.setHtml("<br>".join(h for _, h in lines) if lines else
                              f"<span style='color:gray'>{_h.escape(T('nmr_text_empty'))}</span>")
        self.lbl_own.setText(" ".join(self.printed()[1]))     # Herkunft, zurückgehaltene, offene Vorschläge

    def fill_count(self):
        comp = getattr(self.main, "compound", None) or {}
        res = count_check(sorted(self.blocks(), key=lambda b: nuc_rank(b["nucleus"])), comp.get("formula"))
        STYLE.fill_summary(self.tbl_count, [row for _, row in res])
        from PySide6.QtGui import QBrush, QColor
        for r, (ok, _) in enumerate(res):                    # Abweichung in der Warnfarbe, auf einen Blick
            if not ok:
                for c in range(self.tbl_count.columnCount()):
                    self.tbl_count.item(r, c).setForeground(QBrush(QColor(STYLE.WARN_COLOR)))
        has = any(b["signals"] for b in self.blocks())
        self.lbl_count.setText(T("nmr_count_noformula") if has and not res else "")
        box = getattr(self, "kpi_box", None)                 # Kacheln in der Reiterzeile: „¹H 16/16 H“, Abweichung rot
        if box is not None:
            box.show_items([(row[0], ("" if ok else "⚠ ") + row[1].split()[0] + "/" + row[2]) for ok, row in res[:2]])
            for lb, (ok, row) in zip(box.labels, res[:2]):
                lb.setToolTip(row[3].lstrip("✓⚠ "))         # Kachel ohne Platz für den Hinweis: im Tooltip
                if not ok:
                    lb.setText(lb.text().replace(f"color:{STYLE.colors()['text']}", f"color:{STYLE.WARN_COLOR}"))
        self.fill_impurities()

    def fill_impurities(self):
        """¹³C-Signale und freie ¹H-Peaks (in keinem Multiplett der Zeile, `h1_peaks`), die zu einem Restsignal des
        Lösungsmittels oder einer Verunreinigung in diesem Lösungsmittel passen (`core/nmr_impurities.py`, Fulmer 2010):
        nur ein Hinweis, je Treffer eine Zeile. ¹H: Stoffe mit einem Signal nur „möglich“ (grau); die Signale der Zeile
        selbst nie (an einer veröffentlichten SI traf fast jede ¹H-Zeile einen Tabellenwert)."""
        from PySide6.QtGui import QBrush, QColor
        from elucida.core import nmr_impurities as IMP
        rows, notes, sure = [], [], []
        for b in self.blocks() if self.st.get("imp_hint", True) else []:
            if b["nucleus"] == "13C":
                # Referenz wie im Spektrum beschriftet (z. B. CDCl3 auf 77.00 statt 77.16): Versatz nur für den Vergleich
                label = self.solvent_label()
                d, ref = IMP.ref_offset(b["solvent"], label)
                if ref is not None and d is None:                # Versatz unplausibel: kein Abgleich, nicht raten
                    notes.append(T("nmr_imp_offset_bad", v=label[0], r=f"{ref:.2f}", m=f"{IMP.MAX_OFFSET:g}"))
                    continue
                if d:
                    notes.append(T("nmr_imp_offset", d=f"{d:+.2f}", v=label[0], r=f"{ref:.2f}"))
                for i, r in IMP.hits(b["solvent"], [s["shift"] for s in b["signals"]], offset=d or 0.0):
                    name = T("nmr_imp_solvent") if r["compound"] == IMP.SOLVENT_ROW["2"] else T("fulmer_" + r["compound"])
                    rows.append([sup_nuclei("13C"), b["signals"][i]["shift"], r["shift"], name])
                    sure.append(True)
            elif b["nucleus"] == "1H":
                peaks = self.h1_peaks(b)
                if peaks is None:
                    if IMP.solvent_key(b["solvent"]) is not None:
                        notes.append(T("nmr_imp_1h_nopeaks"))
                    continue
                try:
                    freq = float(b["freq"])
                except (TypeError, ValueError):
                    freq = 0.0
                if freq <= 0:                                  # ohne Frequenz keine Multiplettbreite: nicht raten
                    notes.append(T("nmr_imp_1h_nofreq"))
                    continue
                for i, r, ok in IMP.hits_1h(b["solvent"], peaks, IMP.free_peaks(peaks, b["signals"], freq)):
                    name = T("nmr_imp_solvent") if r["compound"] == IMP.SOLVENT_ROW["1"] else T("fulmer_" + r["compound"])
                    rows.append([sup_nuclei("1H"), peaks[i], r["shift"], name if ok else T("nmr_imp_possible", name=name)])
                    sure.append(ok)
        STYLE.fill_summary(self.tbl_imp, rows)
        self.lbl_imp.setText(" ".join(notes))
        for r, ok in enumerate(sure):                        # Fremdstoff: Warnfarbe wie die Kernzahl-Prüfung; „möglich“ grau
            for c in range(self.tbl_imp.columnCount()):
                self.tbl_imp.item(r, c).setForeground(QBrush(QColor(STYLE.WARN_COLOR if ok else "gray")))

    def h1_peaks(self, b):
        """Peaks des ¹H-Spektrums zur gedruckten ¹H-Zeile (Texte, ppm) oder None. Nur aus MNova: Peakbericht im Manifest
        des ersten exportierten ¹H-Spektrums mit Multiplettbericht (`sort_key`, wie `mx_lines`). Eigene Verarbeitung ->
        None (Entscheidung 157: automatische Peaks trafen richtige und falsche Lösungsmittelspalte gleich oft). Nur lesen,
        nichts im Zustand."""
        if b.get("source") == "own":
            return None
        for s in self.spectra():
            mx = s.get("mx") or {}
            # dieselbe Seite wie die Zeile (`mx_lines`: erstes ¹H mit Multiplettbericht, nicht gemischt)
            if mx.get("mult") and not mx.get("mixed") and s.get("kind", "1D") == "1D" \
                    and (s.get("nuclei") or [""])[0] == "1H":
                try:                                         # neuer Export (Manifest geändert) -> neu lesen
                    st = (Path(s["file"]).parent / "manifest.json").stat()
                except OSError:
                    return None
                key = ("nmrh1peaks", s["file"], mx.get("page"), st.st_mtime_ns, st.st_size)
                if key not in self.main.extra_cache:
                    pk = mx_peak_report(s)
                    if pk is None:                           # fehlendes/unvollständiges Manifest nie festhalten
                        return None
                    self.main.extra_cache[key] = pk
                return self.main.extra_cache[key]
        return None

    def solvent_label(self):
        """Beschriftetes Lösungsmittelsignal (Wert als Text, Name) im ¹³C-Spektrum (Mnova-SVG), sonst None."""
        from elucida.formats.mnova import svg_peak_labels
        for s in self.spectra():
            if s.get("kind") == "1D" and (s.get("nuclei") or [""])[0] == "13C" and Path(s["file"]).is_file() \
                    and not is_emf(s["file"]):
                key = ("nmrsolvlabel", s["file"])
                if key not in self.main.extra_cache:
                    try:
                        self.main.extra_cache[key] = svg_peak_labels(s["file"])[1]
                    except Exception:                    # Datei fehlt oder unlesbar: kein Versatz
                        self.main.extra_cache[key] = None
                if self.main.extra_cache[key]:
                    return self.main.extra_cache[key]
        return None

    def imp_toggled(self, on):
        if self._loading or self.st.get("imp_hint", True) == on:    # Anfangszustand des Chips ist kein Rückgängig-Schritt
            return
        self.st["imp_hint"] = on
        self.fill_impurities()
        self.main.push_undo()

    def nmr_lines(self):
        """[(Klartext, HTML)] je Kern, sortiert wie die Spektren (¹H, ¹³C, übrige nach Massenzahl)."""
        return [line for _, line in self.nmr_lines_by_nucleus()]

    def nmr_lines_by_nucleus(self):
        """[(Kern, (Klartext, HTML))] in derselben Reihenfolge (Austauschdatei: Art der Zeile)."""
        assign = self.st.get("assign") or {}
        return [(b["nucleus"], b["line"] if b.get("source") == "own" else nmr_line(b, assign)) for b in self.blocks()
                if b["signals"]]

    def raw_line(self, s):
        """Zeile eines eigenen Spektrums wie sie gedruckt würde (ohne die Freigabe zu prüfen) -> (Kern, (Klartext,
        HTML), [Meldungen]) oder None ohne gedruckte Signale."""
        b = own_block(s, lambda g: self._nh(s, g))
        return (b["nucleus"], b["line"], b["errs"]) if b["line"] else None

    def si_parts(self):
        return self.nmr_lines()

    # -- Aktionen -------------------------------------------------------------------------
    def add_svg(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("nmr_add"), self.main.settings.value("last_dir", ""),
                                             f"{T('nmr_spec_flt')} (*.svg *.emf);;{T('flt_all')}")
        for p in ps:
            self.load_svg(p)

    def load_svg(self, p):
        try:
            info = spectrum_info(p)
        except Exception as ex:
            self.main.error(f"{Path(p).name}: {ex}")
            return None
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        s = new_spectrum(p, info)
        s["nuc_auto"] = bool(info["nuclei"])
        self.st["spectra"].append(s)
        self.st["current"] = s["uid"]
        self.link_raw()
        self.changed()
        return s

    # -- Rohdaten (TopSpin, Mnova) ----------------------------------------------------------
    def add_topspin(self):
        if not self.main.ensure_project():
            return
        d = QFileDialog.getExistingDirectory(self, T("nmr_topspin"), self.main.settings.value("last_dir", ""))
        if d:
            self.import_topspin(d)

    def import_topspin(self, path):
        """TopSpin-Experiment, -Datensatz oder Ordner mit Datensätzen: jedes Experiment ganz ins Projekt nach
        data/nmr/<Art>/<Datensatz>_<Nummer>, dann zu passenden Spektren zuordnen. -> Anzahl neuer Experimente."""
        exps = find_experiments(path)
        if not exps:
            self.main.error(T("nmr_no_acqus", p=Path(path).name))
            return 0
        raws = self.st.setdefault("raw", [])
        n0 = len(raws)
        for e in exps:
            try:
                self.import_experiment(e)
            except Exception as ex:
                self.main.log_signal.emit(f"  {e.name}: {ex}")
        n = len(raws) - n0
        self.main.log_signal.emit(T("nmr_raw_imported", n=n, kinds=", ".join(sorted({r["kind"] for r in raws}))))
        self.link_raw()
        # 1D ohne passendes Mnova-Spektrum: als eigenes Spektrum zeigen (sonst lag ein abgelegter Ordner nur unsichtbar
        # in „Rohdaten“); nicht „für die SI“ gewählt, die Mnova-Regel bleibt. Gewähltes Spektrum bleibt gewählt.
        cur = self.st.get("current")
        for p in [r["path"] for r in raws[n0:]]:
            if not (Path(p) / "acqu2s").is_file() and not any(
                    x.get("bruker") and Path(x["bruker"]) == Path(p) for x in self.st["spectra"]):
                try:
                    self.raw_spectrum_for(p)
                except Exception as ex:                      # nicht selbst verarbeitbar: bleibt Rohdaten, mit Grund
                    self.main.log_signal.emit(f"  {Path(p).name}: {ex}")
        if cur and any(x["uid"] == cur for x in self.st["spectra"]):
            self.st["current"] = cur
        self.changed()
        return n

    def link_raw(self):
        """Spektren ohne Bruker-Ordner mit dem einen passenden Experiment verknüpfen (Parameter, Temperatur)."""
        raws = [r for r in self.st.get("raw") or [] if Path(r["path"]).is_dir()]
        for s in self.spectra():
            if s.get("bruker"):
                continue
            r = match_experiment(s, raws, self.spectra())
            if r is not None:
                s["bruker"] = r["path"]
                s["params"] = acq_params(r["path"])
                if s["params"].get("te"):
                    s["temp"] = round(s["params"]["te"])

    def add_mnova(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("mnova_store"), self.main.settings.value("last_dir", ""),
                                             f"MNova (*.mnova);;{T('flt_all')}")
        for p in ps:
            self.add_mnova_file(p)

    def add_mnova_file(self, p, export=True):
        """MNova-Dokument in die Verbindung (data/nmr/mnova). export (Primärfall, Entscheidungen 147/149): MNova selbst
        exportiert eine Kopie headless (`start_export`); jede Seite mit Spektrum wird ein Spektrum, die FIDs hängen als
        Rohdaten daran (`take_mnova_export`). Ohne MNova, bei Abbruch oder Zeitgrenze der bisherige Weg (`mnova_rows`)
        mit Einblendung des Grundes. export=False (zusammen mit SVGs abgelegt): nur Rohdaten, FIDs an die passenden
        Spektren, keine neuen Zeilen. -> Pfad des Dokuments in der Verbindung (ein Export läuft danach weiter)."""
        dst = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY) + "/mnova")
        lst = self.st.setdefault("mnova", [])
        if dst not in lst:
            lst.append(dst)
        if not export:
            self.attach_mnova_fids(dst)
        elif any(x.get("mnova_doc") == dst and x.get("mx") for x in self.st["spectra"]):
            self.main.notify(T("nmr_mx_again", name=Path(dst).name))      # dasselbe Dokument: nichts doppelt
        elif any(j["dst"] == dst and j["pdir"] == self.main.project_dir
                 for j in self.main.__dict__.get("_mnova_jobs") or []):
            self.main.notify(T("nmr_mx_queued", name=Path(dst).name))     # Export wartet/läuft schon: kein zweiter
        else:
            why = self.start_export(dst)
            if why is not None:
                return self.mnova_rows(dst, why)
        self.changed()
        return dst

    def mnova_rows(self, dst, why=None, detail=""):
        """Bisheriger Weg (ohne MNova-Export): jedes lesbare 1D-Spektrum mit FID wie ein Bruker-Experiment zeigen
        (`formats/mnova_doc`): FID + acqus/procs als Experimentordner nach
        data/nmr/<Art>/<Dokument>_<k>, eigene Verarbeitung. Die Ordner kommen nicht in die Rohdaten-Liste (Datenpaket,
        FID-Paket): sie sind aus dem Dokument nachgebaut, das Dokument bleibt das Rohdatum. Mnovas Referenzierung nur
        als Vorschlag (`mnova_ref`). 2D/Ungeprüftes mit der Meldung des Lesers. Gewähltes Spektrum bleibt gewählt.
        why: Grund (i18n-Schlüssel), warum der MNova-Export nicht lief – steht vorn in der Einblendung."""
        import tempfile
        from elucida.formats import mnova_doc as MV
        lst = self.st.setdefault("mnova", [])
        if dst not in lst:
            lst.append(dst)
        cur, errs = self.st.get("current"), []
        try:
            doc = MV.read_document(dst)
        except Exception as ex:                           # wie import_topspin: Meldung statt Abbruch
            doc = dict(spectra=[], rejected=[str(ex)], skipped=[])
        for note in doc["skipped"]:
            self.main.log_signal.emit("  " + note)
        errs += doc["rejected"]
        self.main.__dict__.setdefault("_nmr_mnova_refused", {})[dst] = list(doc["rejected"])   # übersteht Neuaufbau
        stem = Path(dst).stem
        for k, spec in enumerate(doc["spectra"], 1):
            try:
                key = mnova_key(spec)                      # neu gespeichertes Dokument, gleicher FID: vorhandenes bleibt
                if any(x.get("mnova_key") == key for x in self.st["spectra"]):
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    e = MV.write_experiment(spec, Path(tmp) / f"{stem}_{k}")
                    kind = experiment_kind(acq_params(e))
                    path = self.main.import_file(str(e), PRJ.data_sub(self.STATE_KEY) + "/" + kind, name=e.name)
                new = not any(x.get("bruker") and Path(x["bruker"]) == Path(path) for x in self.st["spectra"])
                s = self.raw_spectrum_for(path)
                s["mnova_doc"], s["mnova_key"] = dst, key
                if new:                                         # Vorschlag; Meldungen in der Karte Referenzierung
                    s["proc"].update(mnova_ref=spec["ref_shift"], mnova_notes=list(spec["notes"]))
                    self.refresh_ref(s)
            except Exception as ex:                       # Teilerfolg bleibt, changed() unten läuft immer
                errs.append(str(ex))
        head = T("nmr_mx_fallback", name=Path(dst).name, why=T(why) + (f" ({detail})" if detail else "")) if why else ""
        if errs or head:                                   # Einblendung + Hinweis in der Karte MNova, kein Popup
            self.main.notify("\n".join(([head] if head else []) + errs),
                             brief=head or T("nmr_mnova_refused", n=len(errs), name=Path(dst).name))
        if cur and any(x["uid"] == cur for x in self.st["spectra"]):
            self.st["current"] = cur
        self.changed()
        return dst

    def start_export(self, dst):
        """MNova-Export eines Dokuments anstellen (Warteschlange am Hauptfenster: der Tab wird bei Rückgängig/Sprache
        ersetzt, höchstens ein MNova-Prozess von Elucida zugleich) -> None oder i18n-Schlüssel des Grundes, warum es
        nicht geht. Ohne Bildschirm (Selbsttest, CI) nur mit `_allow_mnova` (sonst startete jeder Lauf MNova)."""
        import os
        from elucida.formats import mnova_cli as MX
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and not self.main.__dict__.get("_allow_mnova"):
            return "nmr_mx_none"
        exe = MX.find_mnova()
        if exe is None:
            return "nmr_mx_none"
        if not MX.SCRIPT.is_file():
            return "nmr_mx_script"
        jobs = self.main.__dict__.setdefault("_mnova_jobs", [])
        jobs.append(dict(exe=exe, dst=dst, pdir=self.main.project_dir))
        _mx_next(self.main)
        self.fill_mx_run()
        return None

    def take_mnova_export(self, dst, out, m):
        """Export eines MNova-Dokuments (Ordner `out` mit page_<k>.svg + Manifest `m`) übernehmen -> Zahl der Spektren
        (Seiten in der Verbindung als <Dokument>_<k>.svg, `_mx_names`).
        Erfolg je Seite = Datei, `is_nmr_svg` und ein Kern aus `svg_info` (sonst „nicht übernommen“ in der Karte MNova).
        Ordner in die Verbindung (data/nmr/mnova/<Dokument> neben dem Dokument, nie überschrieben); jede Seite ein Spektrum wie
        `load_svg` (2D aus Achse oder dim), Berichte für `mx_lines`; FIDs des Dokuments als Rohdaten an das passende
        Spektrum (`attach_mnova_fids`); die NMR-Zeile nie still über vorhandenen Text (`apply_mx_text`)."""
        from elucida.formats import mnova_cli as MX
        name, pages, skipped = Path(dst).name, [], []
        for pg in m.get("pages") or []:
            sps = MX.page_spectra(pg)
            if not sps:
                continue                                   # Seite ohne Spektrum (Text, Struktur): nichts zu übernehmen
            f = Path(out) / Path(str(pg.get("svg") or "-")).name     # nur Dateien im Ausgabeordner
            try:
                info = svg_info(f) if is_nmr_svg(f) else None
            except Exception:
                info = None
            if not info or not info["nuclei"]:
                skipped.append(T("nmr_mx_skipped", page=T("nmr_mx_page", p=pg.get("page"), doc=name)))
            else:
                pages.append((pg, sps, f.name, info))
        self.main.__dict__.setdefault("_nmr_mnova_refused", {})[dst] = skipped
        if not pages:
            return 0
        import copy
        snap = copy.deepcopy(self.st)                      # Fehler unterwegs: Zustand zurück, Aufrufer fällt zurück
        try:
            return self._take_mnova_pages(dst, out, m, pages, skipped)
        except Exception:
            self.st.clear()
            self.st.update(snap)
            raise

    def _take_mnova_pages(self, dst, out, m, pages, skipped):
        from elucida.formats import mnova_cli as MX
        name = Path(dst).name
        folder = Path(self.main.import_file(str(out), PRJ.data_sub(self.STATE_KEY) + "/mnova",
                                            name=Path(dst).stem))
        ren = self._mx_names(folder, Path(dst).stem, m)
        cur, new = self.st.get("current"), []
        for pg, sps, fname, info in pages:
            fname = ren.get(fname, fname)
            is2d = info["is2d"] or any(int(sp.get("dim") or 1) > 1 for sp in sps)
            s = new_spectrum(folder / fname, dict(info, is2d=is2d))
            mx = dict(page=pg.get("page"), doc=name)
            if len(sps) > 1:                               # verschiedene Spektren auf einer Seite: nennen, nicht raten
                mx["mixed"] = ", ".join(str(sp.get("nucleus")) for sp in sps)
            elif not is2d and sps[0].get("multiplets"):
                txt = MX.report_text(sps[0].get("mreport"))
                if [b["nucleus"] for b in parse_mnova(txt)] == info["nuclei"][:1]:   # Bericht passt zur Achse
                    mx.update(mult=txt, use="mult")
                else:
                    mx["mult_bad"] = True
            s.update(nuc_auto=True, mnova_doc=dst, mx=mx)
            self.st["spectra"].append(s)
            new.append(s)
        if dst not in self.st.setdefault("mnova", []):
            self.st["mnova"].append(dst)
        self.attach_mnova_fids(dst, skipped)
        self.apply_mx_text()
        self.st["current"] = cur if cur and any(x["uid"] == cur for x in self.st["spectra"]) else new[0]["uid"]
        self.changed()
        return len(new)

    @staticmethod
    def _mx_names(folder, stem, m):
        """Seiten im importierten Export-Ordner sprechend benennen: page_<k>.svg -> <Dokument>_<k>.svg (in der Tabelle
        zuzuordnen); das Manifest bleibt vollständig und nennt die neuen Namen -> {alt: neu}."""
        import json
        ren, pages = {}, []
        for pg in m.get("pages") or []:
            old = Path(str(pg.get("svg") or "-")).name
            new = Path(f"{stem}_{pg.get('page')}.svg").name
            if old != new and (folder / old).is_file() and not (folder / new).exists():
                (folder / old).rename(folder / new)
                ren[old] = new
            pages.append(dict(pg, svg=ren[old]) if old in ren else pg)
        (folder / "manifest.json").write_text(json.dumps(dict(m, pages=pages), ensure_ascii=False), encoding="utf-8")
        return ren

    def attach_mnova_fids(self, dst, notes=()):
        """FIDs eines MNova-Dokuments (`formats/mnova_doc`) als Rohdaten an das je eine passende Spektrum mit MNova-
        Abbildung (gleiche Art, eindeutig wie `match_experiment`), keine neuen Zeilen; die Quelle bleibt MNova, bis der
        Nutzer die eigene Verarbeitung wählt (Entscheidung 90/111; MNovas Referenz dann als Vorschlag, `init_raw`).
        Nicht eindeutig zuzuordnende FIDs bleiben als Ordner liegen (von Hand: „Bruker-Ordner …“) und werden genannt."""
        import tempfile
        from elucida.formats import mnova_doc as MV
        notes = list(notes)
        try:
            doc = MV.read_document(dst)
        except Exception as ex:
            doc = dict(spectra=[], rejected=[str(ex)], skipped=[])
        for note in doc["skipped"] + doc["rejected"]:      # 2D/Ungeprüftes: die Abbildung kommt hier aus MNova selbst
            self.main.log_signal.emit("  " + note)
        raws, stem = [], Path(dst).stem
        for k, spec in enumerate(doc["spectra"], 1):
            try:
                key = mnova_key(spec)
                if any(x.get("mnova_key") == key for x in self.st["spectra"]):
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    e = MV.write_experiment(spec, Path(tmp) / f"{stem}_{k}")
                    kind = experiment_kind(acq_params(e))
                    path = self.main.import_file(str(e), PRJ.data_sub(self.STATE_KEY) + "/" + kind, name=e.name)
                raws.append(dict(kind=kind, path=path, key=key, spec=spec))
            except Exception as ex:
                notes.append(str(ex))
        cands = [x for x in self.st["spectra"] if not x.get("bruker") and x.get("source", "mnova") == "mnova"
                 and x.get("mnova_doc") in (None, dst) and x.get("kind", "1D") == "1D"]
        for s in cands:
            r = match_experiment(s, raws, cands)
            if r is None:
                continue
            r["taken"] = True
            s.update(bruker=r["path"], params=acq_params(r["path"]), mnova_doc=dst, mnova_key=r["key"],
                     mx_ref=dict(mnova_ref=r["spec"]["ref_shift"], mnova_notes=list(r["spec"]["notes"])))
            if s["params"].get("te"):
                s["temp"] = round(s["params"]["te"])
        open_ = [Path(r["path"]).name for r in raws if not r.get("taken")]
        if open_:                                          # eine Zeile für alle (Serien haben viele FIDs)
            notes.append(T("nmr_mx_fid_open", f=", ".join(open_)))
        self.main.__dict__.setdefault("_nmr_mnova_refused", {})[dst] = notes

    def fill_mx_run(self):
        """Laufende/wartende MNova-Exporte in der Karte MNova (Fortschritt, kein Dialog)."""
        import time
        jobs = self.main.__dict__.get("_mnova_jobs") or []
        self.lbl_mx_run.setText("\n".join(
            T("nmr_mx_running", name=Path(j["dst"]).name, s=int(time.monotonic() - j["t0"])) if j.get("t0")
            else T("nmr_mx_waiting", name=Path(j["dst"]).name) for j in jobs))

    def fill_mx(self):
        """Hinweise zu den Zeilen aus exportierten Dokumenten und ein noch offener Vorschlag (`apply_mx_text`)."""
        notes = mx_lines(self.st["spectra"])[1]
        if self.st.get("mx_pending"):
            notes.append(T("nmr_mx_pending"))
        self.lbl_mx.setText("\n".join(notes))
        self.row_mx.setVisible(bool(self.st.get("mx_pending")))

    def fill_mx_use(self, s):
        """Umschalter Multipletts/Peaks: nur bei einem exportierten 1D-Spektrum (nicht ¹H), das beides hat."""
        mx = (s or {}).get("mx") or {}
        show = bool(mx.get("mult")) and s.get("kind", "1D") == "1D" and (s.get("nuclei") or [""])[0] != "1H"
        try:
            show = show and bool(svg_peaks(s["file"])[0])
        except Exception:
            show = False
        self._sel_form.setRowVisible(self.cmb_mx, show)
        self.cmb_mx.blockSignals(True)
        self.cmb_mx.setCurrentIndex(max(0, self.cmb_mx.findData(mx.get("use") or "mult")))
        self.cmb_mx.blockSignals(False)

    def mx_use_changed(self, *_):
        s = self.current()
        if self._loading or s is None or not s.get("mx"):
            return
        s["mx"]["use"] = self.cmb_mx.currentData()
        self.flush_text()
        self.apply_mx_text()
        self.changed()

    def apply_mx_text(self):
        """Zeilen aus den exportierten Dokumenten (`mx_lines`) ins Feld: leer oder noch der letzte Vorschlag -> setzen;
        sonst nie still überschreiben, Vorschlag mit „Übernehmen“/„Behalten“ (Muster `sync_old_name`)."""
        prop = mx_lines(self.st["spectra"])[0]
        cur = (self.st.get("text") or "").strip()
        self.st.pop("mx_pending", None)
        if not prop or mx_merge(cur, prop) == cur:
            return
        if not cur or cur == (self.st.get("mx_auto") or "").strip():
            self.st["text"] = self.st["mx_auto"] = mx_merge(cur, prop)
        else:
            self.st["mx_pending"] = prop

    def flush_text(self):
        """Gerade getippten Text zuerst in den Zustand (wie `_mx_done`), sonst ersetzt ihn der nächste Neuaufbau still."""
        if self.text_timer.isActive():
            self.text_timer.stop()
            self.text_changed()

    def mx_adopt(self):
        self.flush_text()
        prop = self.st.pop("mx_pending", None)
        if prop:                                           # nur die Kerne des Vorschlags, andere Zeilen bleiben
            self.st["text"] = self.st["mx_auto"] = mx_merge(self.st.get("text"), prop)
        self.changed()

    def mx_keep(self):
        self.flush_text()
        self.st.pop("mx_pending", None)
        self.changed()

    def open_mnova(self):
        """Gewähltes Mnova-Dokument (sonst alle der Verbindung zur Auswahl) im Standardprogramm öffnen."""
        from elucida.app.publication_view import open_mnova
        r = self.tbl_raw.currentRow()
        sel = self.tbl_raw.item(r, 0).data(Qt.UserRole) if r >= 0 and self.tbl_raw.item(r, 0) else None
        mn = self.st.get("mnova") or []
        return open_mnova(self, [sel] if sel in mn else mn)

    def remove_raw(self):
        """Eintrag aus der Liste nehmen (die Dateien im Projektordner bleiben liegen)."""
        r = self.tbl_raw.currentRow()
        if r < 0:
            return
        p = self.tbl_raw.item(r, 0).data(Qt.UserRole)
        for s in self.spectra():                         # Verknüpfung lösen
            if s.get("bruker") == p:
                s["bruker"], s["params"], s["source"] = None, None, "mnova"
        # ein Spektrum nur aus diesen Rohdaten (ohne Mnova-Datei) hat danach nichts mehr zu zeigen
        self.st["spectra"] = [s for s in self.st["spectra"] if s.get("bruker") or Path(s["file"]).is_file()
                              or s["file"] != p]
        self.st["raw"] = [r for r in self.st.get("raw") or [] if r["path"] != p]
        self.st["mnova"] = [m for m in self.st.get("mnova") or [] if m != p]
        self.changed()

    def raw_rows(self):
        """Zeilen der Rohdaten-Tabelle: (Art, Name, Pulsprogramm, verknüpftes Spektrum, Pfad)."""
        linked = {s.get("bruker"): Path(s["file"]).name for s in self.spectra() if s.get("bruker")}
        rows = []
        for r in self.st.get("raw") or []:
            pp = ""
            try:
                pp = acq_params(r["path"]).get("pulprog", "")
            except Exception:
                pass
            rows.append((r["kind"], r["name"], pp, linked.get(r["path"], ""), r["path"]))
        rows += [("MNova", Path(m).name, "", "", m) for m in self.st.get("mnova") or []]
        return rows

    def fill_raw(self):
        rows = self.raw_rows()
        self.tbl_raw.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for c, val in enumerate(row[:4]):
                it = QTableWidgetItem(sup_nuclei(val) if c == 0 else val)
                if c == 0:
                    it.setData(Qt.UserRole, row[4])
                self.tbl_raw.setItem(i, c, it)
        self.tbl_raw.resizeColumnsToContents()
        STYLE.fit_check_table(self.tbl_raw, 12)            # so hoch wie die Zeilen (kein leerer Streifen), ab 12 rollen
        mn = self.st.get("mnova") or []
        self.lbl_mnova.setText(", ".join(Path(m).name for m in mn) or T("mnova_none"))
        self.lbl_mnova.setStyleSheet("" if mn else HINT_CSS)
        refused = self.main.__dict__.get("_nmr_mnova_refused") or {}
        self.lbl_mnova_refused.setText("\n".join(t for m in mn for t in refused.get(m, ())))
        self.fill_mx_run()

    def remove_spectrum(self):
        s = self.current()
        if s is not None:
            self.st["spectra"] = [x for x in self.st["spectra"] if x["uid"] != s["uid"]]
            self.st["current"] = None
            self.changed()

    def spectrum_selected(self):
        if self._loading:
            return
        rows = self.tbl.selectionModel().selectedRows()
        sp = self.spectra()
        if rows and rows[0].row() < len(sp):
            self.st["current"] = sp[rows[0].row()]["uid"]
            self._loading = True
            self.fill_selected()
            self._loading = False
            self.update_preview()

    def spec_edited(self, *_):
        if self._loading:
            return
        s = self.current()
        if s is None:
            return
        plain = self.ed_nuc.text().translate(_UNSUP).strip()     # Anzeige ¹H/¹³C, getippt 1H/13C
        nuc = [parse_nucleus(x) for x in re.split(r"[/,;\s]+", plain) if x]
        if all(nuc) and nuc != (s.get("nuclei") or []):
            s["nuclei"], s["nuc_auto"] = nuc, False
        s["kind"] = self.cmb_kind.currentData()
        if s["kind"] != "1D" and len(s.get("nuclei") or []) == 1:
            s["nuclei"] = s["nuclei"] * 2                          # homonuklear (COSY, NOESY …)
        s["temp"] = self.sp_temp.value()
        fr = [x.strip() for x in self.ed_freq.text().split("/")]
        s["freqs"] = {n: f for n, f in zip(s.get("nuclei") or [], fr) if f}
        s["solvent"] = self.ed_solv.text().strip()
        s.update(struct_on=self.cb_struct.isChecked(), struct_pos=self.cmb_spos.currentData())
        self.st["struct_w"] = self.sp_sw.value()                 # gleich groß in allen Spektren
        self.changed()

    # -- Bruker-Rohdaten: eigenes Spektrum ---------------------------------------------------
    def add_raw(self):
        if not self.main.ensure_project():
            return
        d = QFileDialog.getExistingDirectory(self, T("nmr_add_raw"), self.main.settings.value("last_dir", ""))
        if d:
            self.add_raw_path(d)

    def add_raw_path(self, path):
        """Experimentordner (oder Datensatz/Ordner mit Experimenten) als eigene Spektren: Ordner ganz ins Projekt
        (wie die Rohdaten), dann je 1D-Experiment ein Spektrum mit Quelle „bruker“. Abgelehnt mit Meldung, nie geraten.
        -> Liste der neuen Spektren."""
        exps = find_experiments(path)
        if not exps:
            self.main.error(T("nmr_no_acqus", p=Path(path).name))
            return []
        new, errs = [], []
        for e in exps:
            try:
                s = self.raw_spectrum_for(self.import_experiment(e))
            except (OSError, ValueError) as ex:
                errs.append(str(ex))
                continue
            if s is not None:
                new.append(s)
        if errs:
            self.main.error("\n".join(errs))
        self.link_raw()
        self.changed()
        return new

    def raw_spectrum_for(self, path):
        """Spektrum zu einem Experiment im Projekt (vorhandenes mit diesem Ordner wird auf „bruker“ umgestellt).
        ValueError mit Meldung, wenn das Experiment nicht gelesen werden kann."""
        path = str(path)
        s = next((x for x in self.st["spectra"] if x.get("bruker") and Path(x["bruker"]) == Path(path)), None)
        if s is None and (Path(path) / "acqu2s").is_file():   # 2D: Höhenlinien, Abbildung ohne Struktur
            from elucida.formats import bruker_nmr as BN
            p = acq_params(path)
            kind = BN.noah_module(path) or experiment_kind(p)
            s = dict(uid=uuid.uuid4().hex[:8], file=path, nuclei=[p.get("nucleus") or "1H", p.get("nucleus2") or "13C"],
                     nuc_auto=True, kind=kind if kind in KINDS_2D else "2D", source="bruker",
                     temp=float(round(p["te"])) if p.get("te") else 298.0, bruker=path, params=p, freqs={},
                     solvent=solvent_text(p.get("solvent")) if p.get("solvent") else "", size=list(OWN_SIZE_CM), struct_on=False, struct_pos="auto",
                     struct_xy=None, struct_w=20.0)
            s["kind"] = self.raw_2d_ds(s).get("module") or s["kind"]     # unlesbar: Meldung, nicht eingetragen
            self.st["spectra"].append(s)
            self.st["current"] = s["uid"]
            return s
        if s is None:
            p = acq_params(path)
            s = dict(uid=uuid.uuid4().hex[:8], file=path, nuclei=[p.get("nucleus") or "1H"], nuc_auto=True, kind="1D",
                     temp=float(round(p["te"])) if p.get("te") else 298.0, bruker=path, params=p, freqs={},
                     solvent=solvent_text(p.get("solvent")) if p.get("solvent") else "", size=[FIG_W_CM, 11.0], struct_on=True, struct_pos="auto",
                     struct_xy=None, struct_w=20.0)
            s["source"] = "bruker"
            self.init_raw(s)                               # vor dem Eintragen: ein unlesbares Experiment kommt nicht hinein
            self.st["spectra"].append(s)
        else:
            s["source"] = "bruker"
            self.init_raw(s)
        self.st["current"] = s["uid"]
        return s

    def show_raw_row(self):
        """Gewähltes Experiment der Rohdaten-Tabelle als eigenes Spektrum zeigen (auch nach Ablegen eines Ordners)."""
        r = self.tbl_raw.currentRow()
        it = self.tbl_raw.item(r, 0) if r >= 0 else None
        p = it.data(Qt.UserRole) if it is not None else None
        if not p or not (Path(p) / "acqus").is_file():
            return self.main.error(T("nmr_raw_show_need"))
        try:
            self.raw_spectrum_for(p)
        except (OSError, ValueError) as ex:
            return self.main.error(str(ex))
        self.right_tabs.setCurrentIndex(0)
        self.changed()

    def raw_2d_ds(self, s):
        d = Path(s.get("bruker") or "")
        try:
            stamp = (d / "acqus").stat().st_mtime
        except OSError:
            raise ValueError(T("nmr_raw_missing", name=raw_name(d)))
        key = ("nmrraw2d", str(d), int(s.get("procno") or 1), stamp)
        if key not in self.main.extra_cache:
            self.main.extra_cache[key] = raw_2d(d, int(s.get("procno") or 1))
        return self.main.extra_cache[key]

    def axes_2d(self, s, ds):
        """Achsen eines eigenen 2D-Spektrums: unkalibriert (SF = BF1), je Dimension um die bestätigte Referenz eines
        eigenen 1D desselben Kerns am selben Magneten verschoben (Spezifikation: F2 über ¹H, F1 über ¹³C). -> (ax2,
        ax1, Hinweise)."""
        out, notes = [], []
        for (ax, nuc, bf, dim), ref in zip(((ds["ax2"], ds["nuc2"], ds["bf2"], "F2"), (ds["ax1"], ds["nuc1"], ds["bf1"], "F1")),
                                           self.refs_2d(ds)):
            out.append(ax + (ref or 0.0))
            notes.append(T("nmr_2d_cal", dim=dim, nuc=sup_nuclei(nuc), d=f"{ref:+.3f}") if ref is not None
                         else T("nmr_2d_uncal", dim=dim, nuc=sup_nuclei(nuc)))
        return out[0], out[1], notes

    def refs_2d(self, ds):
        """Referenz je Dimension (F2, F1) aus einem eigenen 1D desselben Kerns am selben Magneten mit bestätigter
        Referenz, sonst None (Achse unkalibriert)."""
        refs = []
        for nuc, bf in ((ds["nuc2"], ds["bf2"]), (ds["nuc1"], ds["bf1"])):
            ref = None
            for x in self.spectra():
                if x.get("source") == "bruker" and x.get("proc") and x.get("kind", "1D") == "1D" \
                        and (x.get("nuclei") or [""])[0] == nuc and x["proc"].get("ref_status") == "confirmed":
                    try:
                        if abs(self.raw_ds(x)["sf"] - bf) <= 1e-6 * bf:
                            ref = x["proc"]["ref"]
                            break
                    except (OSError, ValueError):
                        continue
            refs.append(ref)
        return refs

    def own2d_release(self, s):
        """Eigene 2D-Abbildung freigegeben? „Für die SI“ gewählt und jede Achse referenziert (bestätigtes eigenes 1D
        desselben Magneten) oder die nominelle Achse ausdrücklich bestätigt (Chip). -> None oder Schlüssel des Grundes."""
        if not s.get("si_use"):
            return "nmr_own_not_chosen"
        try:
            refs = self.refs_2d(self.raw_2d_ds(s))
        except (OSError, ValueError):
            return "nmr_raw_unreadable"
        if any(r is None for r in refs) and not (s.get("view2d") or {}).get("nominal_ok"):
            return "nmr_2d_uncal_held"
        return None

    @property
    def view2d(self):
        if self._view2d is None:
            from elucida.tabs.nmr_view import NMR2DView
            self._view2d = NMR2DView()
            v2_ = self._view2d
            v2_.get_text_over, v2_.after_draw = (lambda: self.st.get("text_over")), (lambda: self._texts_fill(v2_))
            self._view2d.levels_changed.connect(self.level_2d_changed)
            self._view2d.view_changed.connect(self.zoom_2d_changed)
            self._lay2d.insertWidget(0, self._view2d, 1)
        return self._view2d

    def show_2d(self, s):
        try:
            ds = self.raw_2d_ds(s)
        except (OSError, ValueError) as ex:
            self.preview_stack.setCurrentIndex(1)
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_prev.setText(str(ex))
            suspend_canvas(self.lbl_prev, True)
            self.lbl_cap.setText("")
            return
        self.preview_stack.setCurrentIndex(3)
        ax2, ax1, cal = self.axes_2d(s, ds)
        v2 = s.get("view2d") or {}
        self.view2d.set_data(ds["data"], ax2, ax1, ds["nuc2"], ds["nuc1"], v2.get("level"))
        if v2.get("xlim") and v2.get("ylim"):
            self.view2d.xlim, self.view2d.ylim = tuple(v2["xlim"]), tuple(v2["ylim"])
            self.view2d.redraw()
        src = T("nmr_2d_own") if ds["own"] else T("nmr_2d_2rr")
        self.lbl_2d.setText(" ".join([src] + ds["notes"] + cal))
        n = self.spectra().index(s) + 1
        self.lbl_cap_2d.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))

    def zoom_2d_changed(self, xlim, ylim):
        """Zoom des 2D: Bereich der Abbildung, gespeichert (auf den gezeigten Achsen; ändert sich die Referenz, gilt
        der Bereich weiter in ppm)."""
        s = self.current()
        if s is not None and s.get("source") == "bruker" and s.get("kind", "1D") != "1D":
            s.setdefault("view2d", {}).update(xlim=[float(v) for v in xlim], ylim=[float(v) for v in ylim])
            self.main.push_undo()

    def level_2d_changed(self, v):
        s = self.current()
        if s is not None and s.get("source") == "bruker" and s.get("kind", "1D") != "1D":
            s.setdefault("view2d", {})["level"] = float(v)
            self.main.push_undo()

    def raw_svg2d(self, s):
        """Eigenes 2D-Spektrum als SVG (16 × 11 cm, Bereich und Schwelle wie die Ansicht)."""
        import json
        import zlib
        from elucida.tabs.nmr_view import NMR2DView
        ds = self.raw_2d_ds(s)
        ax2, ax1, _ = self.axes_2d(s, ds)
        v2 = s.get("view2d") or {}
        lim = (tuple(v2["xlim"]), tuple(v2["ylim"])) if v2.get("xlim") and v2.get("ylim") else None
        cdir = PRJ.work_dir(self.main.project_dir or Path(s["bruker"]).parent, self.STATE_KEY)
        tag = zlib.crc32(json.dumps([s, lim, float(ax2[0]), float(ax1[0])] + self._text_tag(), sort_keys=True,
                                    default=str).encode())
        out = cdir / f"{Path(s['bruker']).name}_own2d_{tag:08x}.svg"
        if not out.exists():
            e = NMR2DView()
            e.get_text_over = lambda: self.st.get("text_over")
            try:
                e.set_data(ds["data"], ax2, ax1, ds["nuc2"], ds["nuc1"], (s.get("view2d") or {}).get("level"))
                if lim:
                    e.xlim, e.ylim = lim
                e.export_svg(out, *OWN_SIZE_CM)
            finally:
                e.deleteLater()
        return str(out)

    def raw_ds(self, s):
        """Gelesene Rohdaten eines Spektrums (zwischengespeichert; FID-Verarbeitung ohne Phase)."""
        d = Path(s.get("bruker") or "")
        procno = int(s.get("procno") or 1)
        try:
            stamp = (d / "acqus").stat().st_mtime
        except OSError:
            raise ValueError(T("nmr_raw_missing", name=raw_name(d)))
        key = ("nmrrawds", str(d), procno, stamp)
        cache = self.main.extra_cache
        if key not in cache:
            cache[key] = raw_dataset(d, procno)
        return cache[key]

    def init_raw(self, s):
        """Verarbeitung anlegen (Phase aus procs, Basislinie) und den Referenzvorschlag suchen; Kern, Lösungsmittel aus
        acqus, wenn leer. 2D: nur lesen (Höhenlinien, keine Phase/Referenz hier)."""
        if (Path(s.get("bruker") or "") / "acqu2s").is_file():
            self.raw_2d_ds(s)
            return
        ds = self.raw_ds(s)
        s.setdefault("procno", 1)
        if not s.get("proc"):                              # FID aus einem MNova-Export: MNovas Referenz als Vorschlag
            s["proc"] = dict(raw_proc_defaults(ds), **s.pop("mx_ref", {}))
        if not s.get("nuclei"):
            s["nuclei"] = [ds["nucleus"]]
        s["solvent"] = s.get("solvent") or ds["solvent"]
        self.refresh_ref(s)

    def raw_y(self, s, ds=None):
        """Reelles Spektrum mit der Phase und Basislinie des Zustands -> dict(y, z, base, notes); je Spektrum nur der
        letzte Stand zwischengespeichert (Phase ändert sich beim Ziehen laufend)."""
        ds = ds or self.raw_ds(s)
        pr = s["proc"]
        key = (s.get("bruker"), id(ds), round(pr["phc0"], 6), round(pr["phc1"], 6), bool(pr.get("baseline", True)),
               pr.get("bl_model", "poly5"))
        c = self._ycache.get(s["uid"])
        if c is None or c["key"] != key:
            from elucida.core import nmr_analysis as NA
            z = phased(ds["spec"], pr["phc0"], pr["phc1"])
            y, notes = z.real.copy(), []
            if pr.get("baseline", True):
                y, sig, _m, notes = NA.baseline(z.real, ds["hzpt"], model=pr.get("bl_model", "poly5"))
            else:
                sig = NA.noise(y)
            c = self._ycache[s["uid"]] = dict(key=key, y=y, z=z, base=z.real - y, notes=list(notes), sigma=float(sig))
        return c

    def refresh_ref(self, s):
        """Referenzvorschlag neu suchen, solange der Nutzer nichts bestätigt hat (nach Phase/Basislinie)."""
        pr = s["proc"]
        if pr.get("ref_status") == "confirmed":
            return
        ds = self.raw_ds(s)
        shift, found, ref, notes = suggest_ref(self.raw_y(s, ds)["y"], ds, s.get("solvent") or ds["solvent"])
        if pr.get("ref_target") is None:
            pr["ref_target"] = float(ref) if ref is not None else 0.0
        pr["ref_found"] = None if found is None else float(found)
        pr["ref_notes"] = list(notes) + list(pr.get("mnova_notes") or [])
        if pr.get("mnova_ref") is not None and pr.get("ref_src") != "unified":   # Referenzierung aus dem Dokument
            pr.update(ref=float(pr["mnova_ref"]), ref_status="suggested", ref_src="mnova")
        elif found is not None:
            pr.update(ref=float(pr["ref_target"] - found), ref_status="suggested", ref_src="fulmer")
        elif pr.get("ref_src") != "click":
            pr.update(ref=None, ref_status="none", ref_src="")

    def raw_current(self):
        s = self.current()
        return s if s is not None and s.get("source") == "bruker" and s.get("proc") else None

    def source_changed(self, *_):
        if self._loading:
            return
        s = self.current()
        if s is None:
            return
        src = self.cmb_source.currentData()
        if src == "bruker":
            try:
                if not s.get("bruker"):
                    raise ValueError(T("nmr_src_need_raw"))
                s["source"] = "bruker"
                self.init_raw(s)
            except (OSError, ValueError) as ex:
                s["source"] = "mnova"
                self.main.error(str(ex))
        else:
            s["source"] = "mnova"
        self.changed()

    def show_raw(self, s):
        self._showing = True                               # Vollansicht beim Laden ist keine Wahl des Nutzers
        try:
            self._show_raw(s)
        finally:
            self._showing = False

    def _show_raw(self, s):
        """Eigenes Spektrum in der Ansicht: Achse unkalibriert + Referenz, Phase und Basislinie des Zustands; dieselbe
        Ansicht bleibt, wenn sich nur die Referenz verschiebt."""
        v = self.view
        try:
            ds = self.raw_ds(s)
            c = self.raw_y(s, ds)
        except (OSError, ValueError) as ex:                # Ordner fehlt/unlesbar: Grund statt Spektrum
            self.preview_stack.setCurrentIndex(1)
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_prev.setText(str(ex))
            suspend_canvas(self.lbl_prev, True)
            self.lbl_cap.setText("")
            self._raw_s = None
            return
        self.preview_stack.setCurrentIndex(2)
        pr = s["proc"]
        ref = pr.get("ref") or 0.0
        prev, keep = self._raw_s, None
        if prev and prev[0] == s["uid"] and v.xlim is not None:
            keep = (ref - prev[1], v.xlim, v.ylim)
        v.ph0 = v.ph1 = 0.0
        v.struct_left = bool(s.get("struct_on", True) and self.structure_path())   # Platz für die Struktur der SI
        v.set_display(self.view_opts(s, ref))
        f = pr.get("ref_found")
        v.set_solvents([dict(x=f + ref, name=solvent_text(s.get("solvent") or ds["solvent"]))] if f is not None else [])
        had = v._bands() if v.x is not None and v.xlim is not None else None
        self.push_analysis(s, ds, c, ref)                  # vor dem Spektrum: Vollansicht rechnet Labels/Werte mit
        v.set_spectrum(ds["ax"] + ref, c["y"], ds["sf"], nucleus=ds["nucleus"])
        traces, main_label, grp = self.cmp_traces(s)
        v.traces, v.main_label = traces, main_label
        v.stack, v.offset = self.cmp_mode() == "stack", int(self.cmp().get("offset") or 100) / 100
        if keep is not None:
            dx, xl, yl = keep
            v.set_view((xl[0] + dx, xl[1] + dx), yl, record=False)
            if had is not None and v._bands() != had:
                v.fit_highest(record=False)                # neue Labelreihe/Integralwerte: Platz oben/unten neu
        else:                                              # frisch gezeigt: zuletzt angesehene Stelle, sonst die SI-Abbildung
            xl = self.main.__dict__.get("_nmr_view_xlim", {}).get(s["uid"]) or (s.get("view") or {}).get("xlim")
            v.fit_highest(record=False, xlim=(xl[0] + ref, xl[1] + ref) if xl else self.si_xlim(s, ds, ref))
        self._raw_s = (s["uid"], ref)
        if prev is None or prev[0] != s["uid"]:            # anderes Spektrum oder Neuaufbau: dessen letzter Modus
            v.set_mode(self.main.__dict__.get("_nmr_view_mode", {}).get(s["uid"], "pointer"))
        n = self.spectra().index(s) + 1
        from elucida.tabs import nmr_compare as NC
        if len(grp) >= 2 and any(m["uid"] == s["uid"] for m in grp):     # Vergleich: dessen Unterschrift
            self.lbl_cap_raw.setText(NC.caption_html(grp, self.blocks(), self.compound_name(), self.cmp()))
        else:
            self.lbl_cap_raw.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))
        notes = self.cmp_notes(s, traces, grp)
        self.lbl_cmp_notes.setText(notes)
        self.lbl_cmp_notes.setVisible(bool(notes))

    def si_xlim(self, s, ds, ref):
        """Bereich der SI-Abbildung: vom Nutzer im Feld „Bereich“ festgelegt (gespeichert auf der unkalibrierten Achse),
        sonst „auto“ (`nmr_compare.auto_xlim`: ¹H 9…0, ¹³C 200…0 ppm, erweitert bis jedes Signal der SI-Zeile mit Rand
        innen liegt; Nutzerentscheid 2026-11-20), andere Kerne das ganze Spektrum. Nie die letzte Zoomstufe der Ansicht
        (Runde 2: die Abbildung sprang mit jedem Zoom mit)."""
        xl = (s.get("view") or {}).get("si_xlim")
        if xl:
            return (xl[0] + ref, xl[1] + ref)
        from elucida.tabs import nmr_compare as NC
        nuc = (s.get("nuclei") or [ds["nucleus"]])[0]
        return NC.auto_xlim(nuc, NC.signal_spans(self.blocks(), nuc),
                            (float(ds["ax"].min() + ref), float(ds["ax"].max() + ref)))

    def si_range_changed(self, *_):
        """Feld „Bereich“ (SI-Abbildung): eigener Bereich (gespeichert auf der unkalibrierten Achse) oder wieder „auto“."""
        s = self.raw_current()
        if self._loading or s is None:
            return
        v = s.setdefault("view", {})
        ref = s["proc"].get("ref") or 0.0
        a, b = (sp_.value() for sp_ in self.sp_rng)
        new = None if self.cb_rng.isChecked() or abs(a - b) < 1e-6 else [max(a, b) - ref, min(a, b) - ref]
        if new == v.get("si_xlim"):
            return
        if new is None:
            v.pop("si_xlim", None)
        else:
            v["si_xlim"] = new
        self.changed()

    def view_zoomed(self, xlim):
        """Neue Zoomstufe der Ansicht: nur die Ansicht merken (beim nächsten Zeigen dieselbe Stelle; kein eigener
        Rückgängig-Schritt). Die SI-Abbildung hängt nie davon ab, nur vom Feld „Bereich“ (`si_xlim`)."""
        s = self.raw_current()
        if s is None or self._loading or self._showing:
            return
        ref = s["proc"].get("ref") or 0.0
        s.setdefault("view", {})["xlim"] = [float(xlim[0] - ref), float(xlim[1] - ref)]
        # auch außerhalb des Zustands: Rückgängig setzt den Zustand zurück, die Ansicht soll aber bleiben, wo sie war
        self.main.__dict__.setdefault("_nmr_view_xlim", {})[s["uid"]] = s["view"]["xlim"]

    def view_opts(self, s, ref):
        """Anzeige des Spektrums für die Ansicht: Vorgabe + gespeicherte Werte; Bereiche in ppm der Ansicht (gespeichert
        auf der unkalibrierten Achse, damit eine neue Referenz sie mitnimmt)."""
        from elucida.tabs import nmr_view as NV
        d = dict(NV.SHOW_DEFAULT, insets=[])
        d.update(s.get("view") or {})
        d["insets"] = shift_ranges(d.get("insets") or [], ref)
        return d

    def view_display_changed(self, d):
        s = self.raw_current()
        if self._loading or s is None:
            return
        d = dict(d)
        d["insets"] = shift_ranges(d.get("insets") or [], -(s["proc"].get("ref") or 0.0))
        for k in ("xlim", "si_xlim"):                     # Zoom und Bereich der SI-Abbildung bleiben
            if (s.get("view") or {}).get(k):
                d[k] = s["view"][k]
        s["view"] = plain_data(d)
        self.main.push_undo()

    def phase_preview(self, ph0, ph1, pivot):
        """Phase beim Ziehen (Shift+P): zusätzlich zur gespeicherten, um den Drehpunkt; Basislinie vom letzten Stand."""
        s = self.raw_current()
        c = self._ycache.get(s["uid"]) if s is not None else None
        if c is None:
            return None
        z = c["z"]
        n = z.size
        ip = int(np.argmin(np.abs(self.view.x - pivot))) if pivot is not None else 0
        return (z * np.exp(-1j * np.deg2rad(ph0 + ph1 * (np.arange(n) - ip) / n))).real - c["base"]

    def commit_phase(self):
        """Gezogene Phase in procs-Form übernehmen (PHC0 + PHC1·i/SI, Drehpunkt links): ein Rückgängig-Schritt."""
        v, s = self.view, self.raw_current()
        if v.drag is not None:                             # noch am Ziehen
            self.phase_timer.start()
            return
        if s is None or not (v.ph0 or v.ph1):
            return
        n = v.x.size
        ip = int(np.argmin(np.abs(v.x - v.pivot))) if v.pivot is not None else 0
        pr = s["proc"]
        pr["phc0"] = float((pr["phc0"] + v.ph0 - v.ph1 * ip / n + 180.0) % 360.0 - 180.0)
        pr["phc1"] = float(pr["phc1"] + v.ph1)
        pr.update(phase="manual", phase_ok=True)           # von Hand gesetzt = Entscheidung des Nutzers
        v.ph0 = v.ph1 = 0.0
        self.refresh_ref(s)
        self.changed()

    def confirm_phase(self):
        s = self.raw_current()
        if s is not None and not s["proc"].get("phase_ok"):
            s["proc"]["phase_ok"] = True
            self.changed()

    def acme_phase(self):
        """ACME-Vorschlag (Chen 2002) im Hintergrund (~6 s bei 64k Punkten); Ergebnis als Phase „nicht bestätigt“."""
        import threading
        s = self.raw_current()
        if s is None or getattr(self, "_acme", None):
            return
        from elucida.core import nmr_analysis as NA
        spec, uid, box = self.raw_ds(s)["spec"], s["uid"], {}
        self._acme = box
        self.btn_acme.setEnabled(False)
        self.btn_acme.setText(T("nmr_phase_acme_busy"))

        def run():
            try:
                box["res"] = NA.autophase(spec)
            except Exception as ex:                      # Ergebnis oder Grund, nie ein stiller Abbruch
                box["err"] = str(ex)
        threading.Thread(target=run, daemon=True).start()

        def poll():
            if "res" not in box and "err" not in box:
                return QTimer.singleShot(150, self, poll)
            self._acme = None
            try:
                self.btn_acme.setText(T("nmr_phase_acme"))
            except RuntimeError:                           # Tab inzwischen ersetzt
                return
            s_ = next((x for x in self.st.get("spectra") or [] if x["uid"] == uid), None)
            if "err" in box or s_ is None:
                if "err" in box:
                    self.main.error(box["err"])
                return self.fill_raw_cards()
            s_["proc"].update(phc0=box["res"][0], phc1=box["res"][1], phase="acme", phase_ok=False)
            self.refresh_ref(s_)
            self.changed()
        QTimer.singleShot(150, self, poll)

    def baseline_changed(self, key):
        """Basislinie: „poly5“ (Standard), „bernstein3“ oder „off“. Zustand: `baseline` (an/aus wie bisher) und
        `bl_model` nur, wenn nicht Polynom 5 – alte Verbindungen bleiben unverändert."""
        s = self.raw_current()
        if self._loading or s is None or key == baseline_key(s["proc"]):
            return
        pr = s["proc"]
        pr["baseline"] = key != "off"
        if key == "bernstein3":
            pr["bl_model"] = key
        elif key == "poly5":
            pr.pop("bl_model", None)
        self.refresh_ref(s)
        self.changed()

    def reference_clicked(self, x):
        """R/L in der Ansicht: getroffene Spitze bekommt den Sollwert (Feld „Sollwert“) = bestätigte Referenz."""
        s = self.raw_current()
        if s is None:
            return
        pr = s["proc"]
        pr.update(ref=float((pr.get("ref") or 0.0) + self.sp_ref.value() - x), ref_status="confirmed", ref_src="click",
                  ref_target=float(self.sp_ref.value()), ref_found=None)
        self.changed()

    def unified_ref(self):
        """Unified Scale (IUPAC, Ξ doppelt abgeschrieben) über ein eigenes ¹H derselben Probe am selben Magneten mit
        bestätigter Referenz: Vorschlag, der wie jede Referenz bestätigt werden muss."""
        from elucida.core import nmr_analysis as NA
        s = self.raw_current()
        if s is None:
            return
        ds = self.raw_ds(s)
        nuc = ds["nucleus"]
        xi = NA.XI_15N_NH3 if nuc == "15N" and self.cmb_xi15.currentData() == "NH3" else None
        sample = Path(s["bruker"]).name.rsplit("_", 1)[0]
        why = T("nmr_xi_noh")
        for x in self.spectra():
            if x is s or x.get("source") != "bruker" or not x.get("proc") or (x.get("nuclei") or [""])[0] != "1H":
                continue
            if Path(x["bruker"]).name.rsplit("_", 1)[0] != sample or x["proc"].get("ref_status") != "confirmed":
                continue
            try:
                d = NA.unified_shift(nuc, ds["sf"], self.raw_ds(x)["sf"], x["proc"]["ref"], xi)
            except ValueError as ex:
                why = str(ex)
                continue
            s["proc"].update(ref=float(d), ref_status="suggested", ref_src="unified", ref_found=None,
                             ref_notes=[T("nmr_xi_done", h=Path(x["bruker"]).name,
                                          xi=f"{(xi or NA.XI[nuc]):.6f}")])
            return self.changed()
        self.main.error(why)

    def confirm_ref(self):
        s = self.raw_current()
        if s is None or s["proc"].get("ref_status") == "confirmed":
            return
        from elucida.core import nmr_analysis as NA
        if s["proc"].get("ref") is None:                   # X-Kern ohne Lösungsmittelsignal: nominelle Achse bestätigen
            if (s.get("nuclei") or ["1H"])[0] in NA.REF_WIN:
                return
            s["proc"].update(ref=0.0, ref_src="nominal")
        s["proc"]["ref_status"] = "confirmed"
        self.changed()

    def ref_target_changed(self, v):
        """Neuer Sollwert verschiebt die Referenz mit (gefundene oder angeklickte Spitze liegt danach auf dem Wert)."""
        s = self.raw_current()
        if self._loading or s is None:
            return
        pr = s["proc"]
        old = pr.get("ref_target") or 0.0
        if pr.get("ref") is not None and pr.get("ref_src") not in ("unified", "mnova"):
            pr["ref"] = float(pr["ref"] + v - old)
        pr["ref_target"] = float(v)
        self.changed()

    def fill_raw_cards(self):
        """Karten Verarbeitung/Referenzierung zum gewählten Spektrum; bei Mnova-Spektren nur der Satz, wofür sie sind."""
        s = self.raw_current()
        self.lbl_view_lock.setVisible(s is None)
        if s is None:                                       # MNova-SVG: keine eigenen Texte (Bild)
            self._texts_sig = None
            self.texts.fill(None)
        for g in self.raw_cards:
            g.setEnabled(s is not None)
            if g in self._quiet_cards:                    # Karten ohne eigenen Satz: mit verbergen
                g.setVisible(s is not None)
            if g in self._view_cards:
                g.setToolTip("" if s is not None else T("nmr_raw_only"))
        if s is None:
            return
        ds, pr = self.raw_ds(s), s["proc"]
        ph = f"PHC0 {pr['phc0']:.1f}°, PHC1 {pr['phc1']:.1f}°"
        self.lbl_phase.setText(T("nmr_phst_" + pr.get("phase", "procs"), ph=ph) + " · "
                               + T("nmr_ok" if pr.get("phase_ok") else "nmr_not_ok"))
        self.lbl_phase.setStyleSheet("" if pr.get("phase_ok") else f"color: {STYLE.WARN_COLOR};")
        signed = any(ds["kind"].startswith(k) for k in SIGNED_KINDS)
        self.btn_phase_ok.setEnabled(not pr.get("phase_ok"))
        imag = bool(ds["own"] or np.any(ds["spec"].imag))  # TopSpins 1r ohne 1i: Phase nicht änderbar
        self.btn_acme.setEnabled(imag and not signed and not getattr(self, "_acme", None))
        self.btn_phase_manual.setEnabled(imag)
        self.cmb_baseline.blockSignals(True)
        self.cmb_baseline.setCurrentIndex(self.cmb_baseline.findData(baseline_key(pr)))
        self.cmb_baseline.blockSignals(False)
        notes = list(ds["notes"]) + list(self._ycache.get(s["uid"], {}).get("notes") or [])
        if signed:
            notes.append(T("nmr_signed_note"))
        if not imag:
            notes.append(T("nmr_no_1i"))
        self.lbl_proc.setText(" ".join(notes))
        st = pr.get("ref_status", "none")
        f = pr.get("ref_found")
        if st == "none":
            txt = T("nmr_ref_none")
        else:
            txt = T("nmr_refst_" + (pr.get("ref_src") if pr.get("ref_src") in ("fulmer", "unified", "nominal", "mnova") else "click"),
                    f="–" if f is None else f"{f:.3f}", t=f"{pr.get('ref_target') or 0.0:.3f}",
                    d=f"{pr['ref']:+.3f}") + " · " + T("nmr_ok" if st == "confirmed" else "nmr_not_ok")
        # nie mitten im Wert umbrechen: Zahl und Einheit fest verbunden, Minus als Zeichen (kein Trennstrich)
        self.lbl_ref.setText(re.sub(r"(?<=\d) ppm", "\u00a0ppm", re.sub(r"(?<![\w.])-(?=\d)", "\u2212", txt)))
        self.lbl_ref.setStyleSheet("" if st == "confirmed" else f"color: {STYLE.WARN_COLOR};")
        self.sp_ref.blockSignals(True)
        self.sp_ref.setValue(float(pr.get("ref_target") or 0.0))
        self.sp_ref.blockSignals(False)
        from elucida.core import nmr_analysis as NA
        self.btn_ref_ok.setEnabled(st != "confirmed" and (pr.get("ref") is not None or ds["nucleus"] not in NA.REF_WIN))
        self._ref_form.setRowVisible(self._xi_row, ds["nucleus"] != "1H")   # ganze Zeile, kein leerer Abstand
        for w_ in (self.cmb_xi15, self._xi15_label):
            if w_ is not None:
                w_.setVisible(ds["nucleus"] == "15N")
        self.lbl_ref_note.setText(" ".join(pr.get("ref_notes") or []))
        self.ed_marks.setText(s.get("marks_note") or "")
        own = (s.get("view") or {}).get("si_xlim")
        xl = self.si_xlim(s, ds, pr.get("ref") or 0.0)
        for w_, v_ in ((self.cb_rng, None), (self.sp_rng[0], max(xl)), (self.sp_rng[1], min(xl))):
            w_.blockSignals(True)
            w_.setChecked(not own) if v_ is None else w_.setValue(v_)
            w_.blockSignals(False)
        self.fill_ana()

    # -- Bruker-Rohdaten: Auswertung (Integrale, Multipletts, Peaks) ------------------------------
    # Alles in ppm der unkalibrierten Achse gespeichert (eine neue Referenz nimmt es mit). Automatisches ist ein
    # Vorschlag, bis der Nutzer das einzelne Signal bestätigt (kein „alle bestätigen“: B2-Prüfung); ein eingegebenes,
    # nicht gemessenes J wird nur über „J übernehmen“ gedruckt.
    def build_ana_card(self):
        g = QGroupBox(T("nmr_ana_card"))
        f = make_form(g)
        row = QHBoxLayout()
        self.btn_mult_auto, self.btn_peaks_auto = QPushButton(T("nmr_mult_auto")), QPushButton(T("nmr_peaks_auto"))
        for b, tip, fn in ((self.btn_mult_auto, "nmr_mult_auto_tip", self.suggest_multiplets),
                           (self.btn_peaks_auto, "nmr_peaks_auto_tip", self.suggest_peaks)):
            b.setToolTip(T(tip))
            b.clicked.connect(fn)
            row.addWidget(b)
        f.addRow("", row)
        self.btn_peaks_ok = QPushButton(T("nmr_peaks_ok"))
        self.btn_peaks_ok.setToolTip(T("nmr_peaks_ok_tip"))
        self.btn_peaks_ok.clicked.connect(self.confirm_peaks)
        row = QHBoxLayout()                                # Knopf allein: ganze Wertespalte (tidy), nie halb
        row.addWidget(self.btn_peaks_ok)
        f.addRow("", row)
        self.tbl_raw_sig = QTableWidget(0, 5)
        self.tbl_raw_sig.setHorizontalHeaderLabels(["δ [ppm]", T("nmr_mult"), "J [Hz]", "H", T("nmr_sig_status")])
        self.tbl_raw_sig.verticalHeader().setVisible(False)
        self.tbl_raw_sig.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_raw_sig.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_raw_sig.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_raw_sig.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tbl_raw_sig.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tbl_raw_sig.itemSelectionChanged.connect(self.raw_sig_selected)
        STYLE.empty_note(self.tbl_raw_sig, T("nmr_sig_empty"))
        f.addRow(self.tbl_raw_sig)
        self.ed_cls, self.ed_j = QLineEdit(), QLineEdit()
        self.ed_cls.setPlaceholderText("dd")
        self.ed_cls.setToolTip(T("nmr_cls_tip"))
        self.ed_j.setPlaceholderText("8.0, 2.1")
        self.ed_j.setToolTip(T("nmr_j_tip"))
        row = QHBoxLayout()
        row.addWidget(self.ed_cls)
        row.addWidget(QLabel("J [Hz]"))
        row.addWidget(self.ed_j)
        f.addRow(T("nmr_mult"), row)
        self.sp_nh = QDoubleSpinBox(decimals=0, minimum=0, maximum=99, singleStep=1, suffix=" H")
        self.sp_nh.setSpecialValueText(T("auto"))
        self.sp_nh.setToolTip(T("nmr_nh_tip"))
        self.sp_nh.valueChanged.connect(self.raw_nh_changed)
        f.addRow(T("nmr_nh"), self.sp_nh)
        self.ed_assign = QLineEdit()
        self.ed_assign.setToolTip(T("nmr_raw_assign_tip"))
        self.ed_assign.editingFinished.connect(self.raw_assign_changed)
        f.addRow(T("nmr_assign"), self.ed_assign)
        row = QHBoxLayout()
        self.btn_fit, self.btn_sig_ok, self.btn_sig_del = (QPushButton(T(k)) for k in ("nmr_fit", "nmr_sig_ok", "remove"))
        for b, tip, fn in ((self.btn_fit, "nmr_fit_tip", self.fit_selected),
                           (self.btn_sig_ok, "nmr_sig_ok_tip", self.confirm_signal),
                           (self.btn_sig_del, "nmr_sig_del_tip", self.delete_signal)):
            b.setToolTip(T(tip))
            b.clicked.connect(fn)
            row.addWidget(b)
        f.addRow("", row)
        row = QHBoxLayout()                                # nicht gemessenes J: drucken ODER Muster ohne dieses J
        self.btn_j_take, self.btn_j_drop = QPushButton(T("nmr_j_take")), QPushButton(T("nmr_j_drop"))
        for b, tip, fn in ((self.btn_j_take, "nmr_j_take_tip", self.take_j), (self.btn_j_drop, "nmr_j_drop_tip", self.drop_j)):
            b.setToolTip(T(tip))
            b.clicked.connect(fn)
            row.addWidget(b)
        f.addRow("", row)
        self.sp_norm = QDoubleSpinBox(decimals=0, minimum=1, maximum=99, singleStep=1, suffix=" H", value=1)
        self.sp_norm.setToolTip(T("nmr_norm_tip"))
        self.btn_norm = QPushButton(T("nmr_norm_set"))
        self.btn_norm.setToolTip(T("nmr_norm_tip"))
        self.btn_norm.clicked.connect(self.set_norm)
        f.addRow(T("nmr_norm"), self.sp_norm)             # Feld über die Wertespalte, „Setzen“ darunter ebenso (tidy)
        row = QHBoxLayout()
        row.addWidget(self.btn_norm)
        f.addRow("", row)
        self.lbl_ana = STYLE.HintLabel("", wordWrap=True)
        self.lbl_ana.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_ana)
        self.lv.addWidget(g)
        self.raw_cards.append(g)
        self._quiet_cards.append(g)

    def ana(self, s):
        a = s.setdefault("ana", {})
        for k in ("integrals", "signals", "peaks"):
            a.setdefault(k, [])
        return a

    def norm_factor(self, s, c=None, ds=None):
        """Faktor Integral -> Kerne aus der Normierung des Nutzers (Bereich + n), sonst None."""
        from elucida.core import nmr_analysis as NA
        nm = self.ana(s).get("norm")
        if not nm:
            return None
        ds = ds or self.raw_ds(s)
        c = c or self.raw_y(s, ds)
        v = float(NA.integrate(c["y"], ds["ax"], [(nm["lo"], nm["hi"])])[0])
        return nm["n"] / v if v > 0 else None

    def signal_nh(self, sig, k, c, ds):
        """nH eines Signals: eingegeben, sonst Integral × Normierung gerundet; ohne Normierung None."""
        from elucida.core import nmr_analysis as NA
        if sig.get("nH") is not None:
            return sig["nH"]
        if k is None:
            return None
        return NA.round_h(float(NA.integrate(c["y"], ds["ax"], [(sig["lo"], sig["hi"])])[0]) * k)

    def sig_status(self, sig):
        """Status je Signal: Vorschlag, bestätigt, „J nicht gemessen“, bzw. „übernommen“ für ein angenommenes,
        nicht gemessenes J (nie „bestätigt“/„gemessen“, Entscheidung 59)."""
        if sig.get("unmeasured") and not sig.get("j_accepted"):
            return "unmeasured"
        if sig.get("unmeasured") and sig.get("j_accepted"):
            return "taken" if sig.get("confirmed") else "suggested"
        return "confirmed" if sig.get("confirmed") else "suggested"

    def push_analysis(self, s, ds, c, ref, v=None, export=False):
        """Integrale (mit Werten), Multipletts, Peaks, Marken und Fit-Linien in die Ansicht (ppm mit Referenz).
        export: Abbildung für die SI – Peaks nur bestätigt, Multipletts nur bestätigte Signale (Vorschläge nie)."""
        from elucida.core import nmr_analysis as NA
        a, v = self.ana(s), v or self.view
        k = self.norm_factor(s, c, ds)
        ints = a["integrals"]
        vals = NA.integrate(c["y"], ds["ax"], [(i["lo"], i["hi"]) for i in ints]) if ints else []
        if k is None and len(vals):                     # wie Mnova: ohne Normierung das erste Integral = 1
            k0 = 1.0 / vals[0] if vals[0] > 0 else None
        else:
            k0 = k
        v.peak_digits = 2 if ds["nucleus"] == "1H" else 1
        v.set_integrals([dict(lo=i["lo"] + ref, hi=i["hi"] + ref, value=None if k0 is None else float(x * k0))
                         for i, x in zip(ints, vals)])
        v.set_multiplets([dict(lo=g["lo"] + ref, hi=g["hi"] + ref, uid=g["uid"], cls=g.get("mult") or "m",
                               digits=2 if ds["nucleus"] == "1H" else 1,
                               delta=(g["shift"] if g.get("shift") is not None else (g["lo"] + g["hi"]) / 2) + ref,
                               nH=self.signal_nh(g, k, c, ds)) for g in a["signals"]
                          if not export or g.get("confirmed")])
        v.set_peaks([dict(x=p["x"] + ref) for p in a["peaks"]] if not export or a.get("peaks_ok") else [])
        v.set_marks([dict(m, x=m["x"] + ref) for m in a.get("marks") or ()])
        v.set_fit_lines([dict(x=x + ref, ok=self.sig_status(g) in ("confirmed", "taken")) for g in a["signals"]
                         for x in g.get("lines") or ()])

    def _raw_ctx(self):
        s = self.raw_current()
        if s is None:
            return None
        ds = self.raw_ds(s)
        return s, ds, self.raw_y(s, ds), s["proc"].get("ref") or 0.0

    def view_integrals_changed(self, items):
        ctx = self._raw_ctx()
        if ctx is None or self._loading:
            return
        s, ds, c, ref = ctx
        self.ana(s)["integrals"] = plain_data([dict(lo=i["lo"] - ref, hi=i["hi"] - ref) for i in items])
        self.changed()

    def view_peaks_changed(self, items):
        ctx = self._raw_ctx()
        if ctx is None or self._loading:
            return
        s, ds, c, ref = ctx
        self.ana(s)["peaks"] = plain_data(sorted((dict(x=p["x"] - ref) for p in items), key=lambda p: -p["x"]))
        self.ana(s)["peaks_ok"] = False
        self.ana(s).pop("peaks_note", None)               # Zahlen des Vorschlags gelten nicht mehr
        self.changed()

    def marks_note_changed(self):
        s = self.raw_current()
        if self._loading or s is None or (s.get("marks_note") or "") == self.ed_marks.text().strip():
            return
        s["marks_note"] = self.ed_marks.text().strip()
        self.changed()

    def view_marks_changed(self, items):
        ctx = self._raw_ctx()
        if ctx is None or self._loading:
            return
        s, ds, c, ref = ctx
        self.ana(s)["marks"] = plain_data([dict(m, x=m["x"] - ref) for m in items])
        self.changed()

    def view_multiplets_changed(self, items):
        """Bereich gezogen oder Multiplett gelöscht (Entf): geänderte Bereiche sind wieder Vorschläge ohne Fit-Linien."""
        ctx = self._raw_ctx()
        if ctx is None or self._loading:
            return
        s, ds, c, ref = ctx
        old = {g["uid"]: g for g in self.ana(s)["signals"]}
        new = []
        for m in items:
            g = old.get(m.get("uid"))
            if g is None:
                continue
            lo, hi = m["lo"] - ref, m["hi"] - ref
            if abs(lo - g["lo"]) > 1e-9 or abs(hi - g["hi"]) > 1e-9:
                g = dict(g, lo=float(lo), hi=float(hi), lines=[], confirmed=False, j_accepted=False)
                if g.get("mult") == "m":
                    g["shift"] = None
            new.append(g)
        self.ana(s)["signals"] = plain_data(new)
        self.changed()

    def _new_signal(self, m, src):
        return dict(uid=uuid.uuid4().hex[:8], lo=float(m["lo"]), hi=float(m["hi"]),
                    shift=None if m.get("mult") == "m" else float(m["shift"]), mult=m.get("mult") or "m",
                    J=[float(j) for j in m.get("J") or ()], lines=[float(x) for x in m.get("lines") or ()],
                    unmeasured=[float(j) for j in m.get("unmeasured") or ()], notes=list(m.get("notes") or ()),
                    nH=None, assign="", confirmed=False, j_accepted=False, src=src)

    def _solvent_free(self, s, x):
        f = s["proc"].get("ref_found")
        return f is None or abs(x - f) > 0.02

    def suggest_multiplets(self):
        """Automatische Multipletts (Hoye erster Ordnung, sonst „m“) als Vorschläge; bestätigte und von Hand gesetzte
        Signale bleiben, das Restsignal des Lösungsmittels fällt weg."""
        from elucida.core import nmr_analysis as NA
        ctx = self._raw_ctx()
        if ctx is None:
            return
        s, ds, c, ref = ctx
        a = self.ana(s)
        keep = [g for g in a["signals"] if g.get("confirmed") or g.get("src") != "auto"]
        found = [m for m in NA.multiplets(c["y"], ds["ax"], ds["sf"], c["sigma"])
                 if self._solvent_free(s, (m["lo"] + m["hi"]) / 2)
                 and not any(g["lo"] <= (m["lo"] + m["hi"]) / 2 <= g["hi"] for g in keep)]
        a["signals"] = sorted(keep + [self._new_signal(m, "auto") for m in found], key=lambda g: -g["hi"])
        self.lbl_ana.setText(T("nmr_mult_found", n=len(found)))
        self.changed()

    def suggest_peaks(self):
        """Peaks ab 5σ (¹³C-Liste) als Vorschlag ohne das Restsignal; der Nutzer entfernt Überzähliges (Entf, Modus K)."""
        from elucida.core import nmr_analysis as NA
        ctx = self._raw_ctx()
        if ctx is None:
            return
        s, ds, c, ref = ctx
        thr = NA.PEAK_NSIG * c["sigma"]
        # ¹³C mit bestätigter Phase (113): nur das höchste Maximum in ±1 Hz; die übrigen werden genannt (Modus K)
        nms = max(1, int(round(NA.PEAK_NMS_HZ / ds["hzpt"]))) if s["proc"].get("phase_ok") and \
            ds["nucleus"] == "13C" else 0
        pk = [dict(x=float(x)) for x, _h in NA.peaks(c["y"], ds["ax"], thr, nms=nms) if self._solvent_free(s, x)]
        rest = sum(1 for x, _h in NA.peaks(c["y"], ds["ax"], thr) if self._solvent_free(s, x)) - len(pk) if nms else 0
        self.ana(s)["peaks"] = sorted(pk, key=lambda p: -p["x"])
        self.ana(s)["peaks_ok"] = False
        self.ana(s)["peaks_note"] = dict(n=len(pk), rest=rest)   # bleibt stehen (fill_ana), bis die Peaks geändert werden
        self.changed()

    def multiplet_requested(self, lo, hi, thr):
        """J im Bild (Bereich + Schwelle, wie Mnova): Muster im Bereich erkennen (Vorschlag); nichts Eindeutiges ->
        „m“ über den Bereich (manueller Weg)."""
        from elucida.core import nmr_analysis as NA
        ctx = self._raw_ctx()
        if ctx is None:
            return
        s, ds, c, ref = ctx
        lo, hi = lo - ref, hi - ref
        ax, y = ds["ax"], c["y"]
        sel = np.nonzero((ax >= lo) & (ax <= hi))[0]
        out = []
        if sel.size > 2:
            NA._multiplet(np.where(y > max(thr, 0.0), y, 0.0), ax, int(sel[0]), int(sel[-1]), ds["sf"],
                          abs(ax[1] - ax[0]) * ds["sf"], out)
        m = dict(out[0], lo=lo, hi=hi) if len(out) == 1 else dict(lo=lo, hi=hi, mult="m", shift=None)
        a = self.ana(s)
        a["signals"] = sorted([g for g in a["signals"] if not (lo <= (g["lo"] + g["hi"]) / 2 <= hi)]
                              + [self._new_signal(m, "manual")], key=lambda g: -g["hi"])
        self._sel_uid = a["signals"][[g["lo"] for g in a["signals"]].index(lo)]["uid"]
        self.changed()

    def peak_pick_requested(self, lo, hi, thr):
        from elucida.core import nmr_analysis as NA
        ctx = self._raw_ctx()
        if ctx is None:
            return
        s, ds, c, ref = ctx
        ax = ds["ax"]
        m = (ax >= lo - ref) & (ax <= hi - ref)
        if m.sum() < 3:
            return
        new = [dict(x=float(x)) for x, _h in NA.peaks(c["y"][m], ax[m], thr)]
        a = self.ana(s)
        a["peaks"] = sorted([p for p in a["peaks"] if not (lo - ref <= p["x"] <= hi - ref)] + new, key=lambda p: -p["x"])
        a["peaks_ok"] = False
        self.changed()

    def confirm_peaks(self):
        s = self.raw_current()
        if s is not None and self.ana(s)["peaks"] and not self.ana(s).get("peaks_ok"):
            self.ana(s)["peaks_ok"] = True
            self.changed()

    def selected_signal(self):
        s = self.raw_current()
        uid = getattr(self, "_sel_uid", None)
        if s is None or uid is None:
            return None, None
        return s, next((g for g in self.ana(s)["signals"] if g["uid"] == uid), None)

    def view_selection_changed(self, sel):
        s = self.raw_current()
        if s is None or not sel or sel[0] != "multiplets":
            return
        sigs = self.ana(s)["signals"]
        if sel[1] < len(sigs) and getattr(self, "_sel_uid", None) != sigs[sel[1]]["uid"]:
            self._sel_uid = sigs[sel[1]]["uid"]
            self.fill_ana()

    def raw_sig_selected(self):
        if self._loading:
            return
        s = self.raw_current()
        rows = self.tbl_raw_sig.selectionModel().selectedRows()
        if s is None or not rows:
            return
        sigs = self.ana(s)["signals"]
        if rows[0].row() < len(sigs):
            self._sel_uid = sigs[rows[0].row()]["uid"]
            v = self.view
            v.selected = ("multiplets", rows[0].row())
            v.set_mode("multiplet") if v.mode != "multiplet" else v.redraw()
            self.fill_ana(select=False)

    def fit_selected(self):
        """Klasse + J des Nutzers im Bereich des Signals suchen (`fit_pattern`): Vorschlag mit eingezeichneten
        Linien; „m“ = Bereich + m (manueller Weg)."""
        from elucida.core import nmr_analysis as NA
        s, g = self.selected_signal()
        if g is None:
            return
        cls = self.ed_cls.text().strip()
        try:
            js = [float(x) for x in re.split(r"[,;\s]+", self.ed_j.text().strip().replace("Hz", "")) if x]
        except ValueError:
            return self.lbl_ana.setText(T("nmr_j_bad"))
        if cls == "m":
            g.update(mult="m", J=[], shift=None, lines=[], unmeasured=[], notes=[], confirmed=False, j_accepted=False,
                     src="manual")
            return self.changed()
        ds = self.raw_ds(s)
        c = self.raw_y(s, ds)
        res, why = NA.fit_pattern(c["y"], ds["ax"], g["lo"], g["hi"], ds["sf"], cls, js, NA.PEAK_NSIG * c["sigma"])
        if res is None:
            return self.lbl_ana.setText(why)
        g.update(plain_data(dict(shift=res["shift"], mult=cls, J=js, lines=res["lines"], unmeasured=res["unmeasured"],
                                 notes=res["notes"])), confirmed=False, j_accepted=False, src="fit")
        self.lbl_ana.setText(" ".join(res["notes"]))
        self.changed()

    def confirm_signal(self):
        s, g = self.selected_signal()
        if g is not None and not g.get("confirmed"):
            g["confirmed"] = True
            self.changed()

    def take_j(self):
        """Eigene Aktion (nie Teil von „Bestätigen“): ein eingegebenes, nicht gemessenes J wird gedruckt."""
        s, g = self.selected_signal()
        if g is not None and g.get("unmeasured") and not g.get("j_accepted"):
            g["j_accepted"] = True
            self.changed()

    def drop_j(self):
        """Muster ohne die nicht gemessenen J (dd -> d, ein Klick) und neu anpassen: wieder ein Vorschlag mit Linien,
        δ und die getrennten J bleiben erhalten statt Bereich + m."""
        from elucida.core import nmr_analysis as NA
        s, g = self.selected_signal()
        if g is None or not g.get("unmeasured"):
            return
        lets = NA.class_letters(g.get("mult") or "") or []
        un, keep_l, keep_j = list(g["unmeasured"]), [], []
        for let, j in zip(lets, g.get("J") or ()):
            if j in un:
                un.remove(j)
            else:
                keep_l.append(let)
                keep_j.append(j)
        cls = "".join(keep_l) if keep_l else "s"
        self.ed_cls.setText(cls)
        self.ed_j.setText(", ".join(f"{j:g}" for j in keep_j))
        self.fit_selected()

    def delete_signal(self):
        s, g = self.selected_signal()
        if g is not None:
            self.ana(s)["signals"] = [x for x in self.ana(s)["signals"] if x["uid"] != g["uid"]]
            self._sel_uid = None
            self.changed()

    def raw_assign_changed(self):
        s, g = self.selected_signal()
        if self._loading or g is None or g.get("assign", "") == self.ed_assign.text().strip():
            return
        g["assign"] = self.ed_assign.text().strip()
        self.changed()

    def raw_nh_changed(self, v):
        s, g = self.selected_signal()
        if self._loading or g is None:
            return
        g["nH"] = None if v == 0 else float(v)
        self.changed()

    def set_norm(self):
        """Normierung durch den Nutzer: gewähltes Integral (Modus I) oder gewähltes Signal hat n Kerne."""
        s = self.raw_current()
        if s is None:
            return
        v, a = self.view, self.ana(s)
        rng = None
        if v.selected and v.selected[0] == "integrals" and v.selected[1] < len(a["integrals"]):
            it = a["integrals"][v.selected[1]]
            rng = (it["lo"], it["hi"])
        else:
            _s, g = self.selected_signal()
            if g is not None:
                rng = (g["lo"], g["hi"])
        if rng is None:
            return self.lbl_ana.setText(T("nmr_norm_need"))
        a["norm"] = plain_data(dict(lo=rng[0], hi=rng[1], n=self.sp_norm.value()))
        self.changed()

    def fill_ana(self, select=True):
        s = self.raw_current()
        if s is None:
            return
        ds = self.raw_ds(s)
        c = self.raw_y(s, ds)
        a = self.ana(s)
        k = self.norm_factor(s, c, ds)
        ref = s["proc"].get("ref") or 0.0
        sigs = a["signals"]
        d = 2 if ds["nucleus"] == "1H" else 1
        self._loading, was = True, self._loading
        self.tbl_raw_sig.setRowCount(len(sigs))
        for r, g in enumerate(sigs):
            st = self.sig_status(g)
            pos = (f"{g['shift'] + ref:.{d}f}" if g.get("shift") is not None
                   else f"{g['hi'] + ref:.{d}f} – {g['lo'] + ref:.{d}f}")
            nh = self.signal_nh(g, k, c, ds)
            for col, val in enumerate((pos, g.get("mult") or "m", ", ".join(f"{j:.1f}" for j in g.get("J") or ()),
                                       "–" if nh is None else f"{nh:g}", T("nmr_sigst_" + st))):
                it = QTableWidgetItem(val)
                if col == 4 and st != "confirmed":
                    from PySide6.QtGui import QBrush
                    it.setForeground(QBrush(QColor(STYLE.WARN_COLOR)))
                self.tbl_raw_sig.setItem(r, col, it)
        STYLE.fit_columns(self.tbl_raw_sig)
        STYLE.fit_check_table(self.tbl_raw_sig, 8)          # so hoch wie die Zeilen, ab 8 scrollen
        if not sigs:                                       # leer: Platz für den Satz in der Mitte
            self.tbl_raw_sig.setFixedHeight(self.tbl_raw_sig.horizontalHeader().sizeHint().height() + 3 * STYLE.CHECK_ROW_H)
        uid = getattr(self, "_sel_uid", None)
        g = next((x for x in sigs if x["uid"] == uid), None)
        if select:
            self.tbl_raw_sig.clearSelection()
            if g is not None:
                self.tbl_raw_sig.selectRow(sigs.index(g))
        self.ed_assign.setText(g.get("assign", "") if g else "")
        for w_ in (self.ed_cls, self.ed_j, self.sp_nh, self.ed_assign, self.btn_fit, self.btn_sig_del):
            w_.setEnabled(g is not None)
        self.btn_sig_ok.setEnabled(g is not None and not g.get("confirmed"))
        self.btn_j_take.setEnabled(g is not None and bool(g.get("unmeasured")) and not g.get("j_accepted"))
        self.btn_j_drop.setEnabled(self.btn_j_take.isEnabled())
        self.ed_cls.setText(g.get("mult", "") if g else "")
        self.ed_j.setText(", ".join(f"{j:g}" for j in g.get("J") or ()) if g else "")
        self.sp_nh.setValue(float(g["nH"]) if g and g.get("nH") is not None else 0)
        nm = a.get("norm")
        self.lbl_ana.setText(T("nmr_norm_state", lo=f"{nm['hi'] + ref:.2f}", hi=f"{nm['lo'] + ref:.2f}", n=f"{nm['n']:g}")
                             if nm else T("nmr_norm_none"))
        pn = a.get("peaks_note")                          # Peakvorschlag: Anzahl neben dem Satz zur Normierung (sonst
        if pn:                                             # überschrieb ihn dieser sofort)
            self.lbl_ana.setText(self.lbl_ana.text() + " " + T("nmr_peaks_found", n=pn["n"])
                                 + (" " + T("nmr_peaks_rest", n=pn["rest"]) if pn.get("rest") else ""))
        if g is not None and g.get("notes"):
            self.lbl_ana.setText(self.lbl_ana.text() + " " + " ".join(g["notes"]))
        signed = any(ds["kind"].startswith(x) for x in SIGNED_KINDS)
        self.btn_mult_auto.setEnabled(ds["nucleus"] == "1H" and not signed)
        self.btn_norm.setEnabled(not signed)
        self.btn_peaks_ok.setEnabled(bool(a["peaks"]) and not a.get("peaks_ok"))
        self._loading = was

    # -- Vergleich (Einzeln · Überlagert · Gestapelt) und Vorhersage ---------------------------------------------------
    def build_cmp_bar(self):
        """Leiste über der Abbildung: Segment Einzeln · Überlagert · Gestapelt, Versatz (nur gestapelt), Chip Vorhersage;
        Spuren tragen ihre Beschriftung im Bild. Bei MNova-Bildern sichtbar, aber ausgegraut (Grund im Tooltip)."""
        from PySide6.QtWidgets import QButtonGroup, QSpinBox
        from elucida.tabs import nmr_compare as NC
        from elucida.tabs.base import PAGE_INSET
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(PAGE_INSET[0], 0, PAGE_INSET[2], 6)
        v.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        seg = self._cmp_seg = QFrame(objectName="seg")
        sh = QHBoxLayout(seg)
        sh.setContentsMargins(2, 2, 2, 2)
        sh.setSpacing(0)
        grp = QButtonGroup(seg)
        self.cmp_btns = {}
        for k in NC.MODES:
            b = QPushButton(T("nmr_cmp_" + k), objectName="segBtn", checkable=True)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _c=False, k=k: self.set_cmp_mode(k))
            grp.addButton(b)
            sh.addWidget(b)
            self.cmp_btns[k] = b
        row.addWidget(seg)
        row.addSpacing(6)
        self.lbl_cmp_off = QLabel(T("nmr_cmp_offset"))
        self.lbl_cmp_off.setStyleSheet(HINT_CSS)
        self.sp_cmp_off = QSpinBox(minimum=20, maximum=150, singleStep=10, suffix=" %", value=100)
        self.sp_cmp_off.setToolTip(T("nmr_cmp_offset_tip"))
        self.sp_cmp_off.setFixedSize(90, STYLE.CONTROL_H)
        self.sp_cmp_off.valueChanged.connect(self.cmp_offset_changed)
        row.addWidget(self.lbl_cmp_off)
        row.addWidget(self.sp_cmp_off)
        row.addStretch(1)
        self.cb_pred = QCheckBox(T("nmr_pred"))
        self.cb_pred.setProperty("chip", True)
        self.cb_pred.setProperty("nochip", True)           # eigener Chip der Leiste, nicht in „Optionen“ einsammeln
        self.cb_pred.toggled.connect(self.pred_toggled)
        row.addWidget(self.cb_pred)
        v.addLayout(row)
        return w

    def build_cmp_card(self):
        """Karte „NMR-Vergleich“ (Schritt Spektren): Beschriftung der gewählten Spur, Satz der Unterschrift, SI-Überschrift."""
        g = self.grp_cmp = QGroupBox(T("nmr_cmp_card"))
        f = make_form(g)
        self.ed_cmp_label = QLineEdit()
        self.ed_cmp_label.setToolTip(T("nmr_cmp_label_tip"))
        self.ed_cmp_label.editingFinished.connect(self.cmp_label_edited)
        f.addRow(T("nmr_cmp_label"), self.ed_cmp_label)
        self.ed_cmp_cap = STYLE.ChemEdit()
        self.ed_cmp_cap.setPlaceholderText(T("nmr_cmp_caption_ph"))
        self.ed_cmp_cap.setToolTip(T("nmr_cmp_caption_long"))
        self.ed_cmp_cap.editingFinished.connect(lambda: self.cmp_text_edited("caption", self.ed_cmp_cap))
        f.addRow(T("nmr_cmp_caption"), self.ed_cmp_cap)
        self.ed_cmp_head = QLineEdit()
        self.ed_cmp_head.setToolTip(T("nmr_cmp_heading_tip"))
        self.ed_cmp_head.editingFinished.connect(lambda: self.cmp_text_edited("heading", self.ed_cmp_head))
        f.addRow(T("nmr_cmp_heading"), self.ed_cmp_head)
        hint = STYLE.HintLabel(T("nmr_cmp_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        self.lv.addWidget(g)

    def cmp(self):
        """Zustand des Vergleichs zum Lesen (Vorgaben ergänzt, ohne ihn anzulegen: alte Verbindungen bleiben unberührt)."""
        from elucida.tabs import nmr_compare as NC
        return dict(NC.DEFAULT, **(self.st.get("cmp") or {}))

    def cmp_mode(self):
        return self.cmp().get("mode", "single")

    def fill_cmp_column(self, sp):
        """Häkchen der Spektrenliste: eigene 1D-Spektren wählbar, sonst leer; nur in Überlagert/Gestapelt sichtbar."""
        from elucida.tabs import nmr_compare as NC
        on = set(self.cmp().get("members") or ())
        for r, s in enumerate(sp):
            it = QTableWidgetItem()
            it.setData(Qt.UserRole, s["uid"])
            if NC.own_1d(s):
                it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                it.setCheckState(Qt.Checked if s["uid"] in on else Qt.Unchecked)
                it.setToolTip(T("nmr_cmp_check_tip"))
            else:
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                it.setToolTip(T("nmr_cmp_need_own"))
            self.tbl.setItem(r, 4, it)
        self.tbl.setColumnHidden(4, self.cmp_mode() == "single")

    def fill_cmp(self):
        """Leiste und Karte des Vergleichs nach dem Zustand (Segment, Versatz, Chip, Felder)."""
        from elucida.tabs import nmr_compare as NC
        c, s = self.cmp(), self.current()
        own = s is not None and NC.own_1d(s)
        tip = T("nmr_cmp_mode_tip") if own else T("nmr_cmp_need_own")
        for k, b in self.cmp_btns.items():
            b.setChecked(c["mode"] == k)
            b.setEnabled(own)                              # MNova-Bild: sichtbar, aber ausgegraut (R8), Grund im Tooltip
            b.setToolTip(tip)
        self._cmp_seg.setToolTip(tip)
        for w_ in (self.lbl_cmp_off, self.sp_cmp_off):
            w_.setVisible(c["mode"] == "stack")
            w_.setEnabled(own)
        self.sp_cmp_off.blockSignals(True)
        self.sp_cmp_off.setValue(int(c.get("offset") or 100))
        self.sp_cmp_off.blockSignals(False)
        why = self.pred_refusal(s)
        self.cb_pred.setEnabled(why is None)
        self.cb_pred.setToolTip(T("nmr_pred_tip") if why is None else why)
        self.cb_pred.blockSignals(True)
        self.cb_pred.setChecked(why is None and self.pred_on())
        self.cb_pred.blockSignals(False)
        self.ed_cmp_label.setEnabled(own)
        self.ed_cmp_label.setText((c.get("labels") or {}).get(s["uid"], "") if own else "")
        if own:
            grp = NC.groups(self.spectra(), c).get(NC.nucleus(s)) or []
            specs = grp if any(m["uid"] == s["uid"] for m in grp) else grp + [s]
            self.ed_cmp_label.setPlaceholderText(NC.label_of(s, specs, dict(c, labels={})))
        else:
            self.ed_cmp_label.setPlaceholderText("")
        self.ed_cmp_cap.setText(c.get("caption") or "")
        self.ed_cmp_head.setText(c.get("heading") or "")
        self.ed_cmp_head.setPlaceholderText(NC.DEFAULT["heading"])

    def set_cmp_mode(self, k):
        """Segment: ein Rückgängig-Schritt; die Auswahl der Spektren bleibt. Erstes Mal Überlagert/Gestapelt ohne Häkchen
        dieses Kerns: das gewählte Spektrum kommt dazu (sonst wäre der Vergleich leer)."""
        from elucida.tabs import nmr_compare as NC
        if self._loading or self.cmp_mode() == k:
            return self.fill_cmp()
        c = NC.state(self.st)
        c["mode"] = k
        s = self.current()
        if k != "single" and s is not None and NC.own_1d(s) and not NC.groups(self.spectra(), c).get(NC.nucleus(s)):
            c["members"].append(s["uid"])
        self._raw_s = None                                 # Spuren ändern die Höhe: neu einpassen
        self.changed()

    def cmp_member_toggled(self, item):
        from elucida.tabs import nmr_compare as NC
        if self._loading or item.column() != 4 or not (item.flags() & Qt.ItemIsUserCheckable):
            return
        uid, on = item.data(Qt.UserRole), item.checkState() == Qt.Checked
        if on == (uid in (self.cmp().get("members") or ())):
            return
        m = NC.state(self.st)["members"]
        if on:
            m.append(uid)
        else:
            m.remove(uid)
        self._raw_s = None
        QTimer.singleShot(0, self, self.changed)           # nicht im Signal der Tabelle neu füllen

    def cmp_offset_changed(self, v):
        from elucida.tabs import nmr_compare as NC
        if self._loading or int(self.cmp().get("offset") or 100) == int(v):
            return
        NC.state(self.st)["offset"] = int(v)
        self._raw_s = None
        self.changed()

    def cmp_label_edited(self):
        from elucida.tabs import nmr_compare as NC
        s = self.current()
        if self._loading or s is None or not NC.own_1d(s):
            return
        txt = self.ed_cmp_label.text().strip()
        if txt == (self.cmp().get("labels") or {}).get(s["uid"], ""):
            return
        lab = NC.state(self.st)["labels"]
        if txt:
            lab[s["uid"]] = txt
        else:
            lab.pop(s["uid"], None)
        self.changed()

    def cmp_text_edited(self, key, w):
        from elucida.tabs import nmr_compare as NC
        txt = w.text().strip() or (NC.DEFAULT[key] if key == "heading" else "")
        if self._loading or txt == (self.cmp().get(key) or ""):
            return
        NC.state(self.st)[key] = txt
        self.changed()

    def cmp_groups(self):
        """Vergleiche für Export und SI -> [(Kern, Spektren, Grund oder None)]; leer in „Einzeln“."""
        from elucida.tabs import nmr_compare as NC
        c = self.cmp()
        if c["mode"] == "single":
            return []
        return [(nuc, specs, NC.refusal(specs)) for nuc, specs in NC.groups(self.spectra(), c).items()]

    def cmp_traces(self, s):
        """Spuren der Ansicht für das gewählte Spektrum s -> (Spuren, Beschriftung von s, Gruppe). Die Vorhersage nur,
        wenn der Chip an ist und sie vorliegt (nie im Zustand)."""
        from elucida.tabs import nmr_compare as NC
        c = self.cmp()
        traces, grp, main_label = [], [], None
        if c["mode"] != "single":
            grp = NC.groups(self.spectra(), c).get(NC.nucleus(s)) or []
            specs = grp if any(m["uid"] == s["uid"] for m in grp) else grp + [s]
            for m in (m for m in grp if m["uid"] != s["uid"]):
                try:
                    ds = self.raw_ds(m)
                    y = self.raw_y(m, ds)["y"]
                except (OSError, ValueError):
                    continue
                traces.append(dict(x=ds["ax"] + (m["proc"].get("ref") or 0.0), y=y, kind="trace", h=1.0,
                                   color=NC.COLORS[(len(traces) + 1) % len(NC.COLORS)], label=NC.label_of(m, specs, c),
                                   uid=m["uid"]))
            if traces:
                main_label = NC.label_of(s, specs, c)
        p = self.pred_result(s)
        if p and p.get("curve") is not None:
            x, y = p["curve"]
            traces.append(dict(x=x, y=y, color=NC.PRED_COLOR, kind="pred", h=NC.PRED_H, label=T("nmr_pred_lane")))
        return traces, main_label, grp

    def cmp_notes(self, s, traces, grp):
        """Hinweise unter der Ansicht: Referenz unbestätigt, Spektrum nicht angehakt, Gruppe abgelehnt, Signale außerhalb
        des Bereichs der SI-Abbildung, Vorhersage samt Lizenzhinweis von nmrshiftdb2."""
        from elucida.tabs import nmr_compare as NC
        warn, gray = STYLE.WARN_COLOR, "gray"
        lines = []
        others = [t_ for t_ in traces if t_["kind"] == "trace"]
        pred = any(t_["kind"] == "pred" for t_ in traces)
        sp = {m["uid"]: m for m in self.st["spectra"]}
        shown = [s] + [sp[t_["uid"]] for t_ in others if t_["uid"] in sp]
        unconf = [NC.label_of(m, shown, self.cmp()) for m in shown if (m.get("proc") or {}).get("ref_status") != "confirmed"]
        if unconf and (pred or others):
            what = T("nmr_cmp_ref_both") if pred and others else T("nmr_cmp_ref_pred") if pred else T("nmr_cmp_ref_other")
            lines.append((warn, "⚠ " + T("nmr_cmp_ref", names=", ".join(unconf), what=what)))
        if self.cmp_mode() != "single" and grp and not any(m["uid"] == s["uid"] for m in grp):
            lines.append((gray, T("nmr_cmp_not_member")))
        why = NC.refusal(grp) if len(grp) >= 2 else None
        if why:
            lines.append((warn, "⚠ " + T("nmr_cmp_withheld", why=T(why, nuc=sup_nuclei(NC.nucleus(s))))))
        try:
            out = self.range_state(s)[2]
        except (OSError, ValueError):
            out = []
        if out:
            lines.append((warn, "⚠ " + self.range_warning(s, out)))
        if self.pred_on() and self.pred_refusal(s) is None:
            p = self.pred_result(s) or {}
            nuc = NC.nucleus(s)
            if p.get("error"):
                lines.append((warn, p["error"]))
            elif p.get("curve") is None:
                lines.append((gray, T("nmr_pred_running")))
            if nuc in ("19F", "31P"):
                lines.append((warn, "⚠ " + T("nmr_pred_xnuc", nuc=sup_nuclei(nuc))))
            if NC.octet_solvent(s.get("solvent")) is None:
                lines.append((gray, T("nmr_pred_solv_any", solv=s.get("solvent") or "–")))
            lines.append((gray, T("nmr_pred_frame") + " " + NC.NOTICE))
        return "<br>".join(f"<span style='color:{c_}'>{_h.escape(t_, quote=False)}</span>" for c_, t_ in lines)

    def range_state(self, s, bl=None):
        """Bereich der Achse -> (passt | None, Text, Signale der SI-Zeile außerhalb). Eigenes Spektrum: Bereich der
        SI-Abbildung, geprüft wird nur, ob jedes Signal innen liegt (die Vorgabe 9…0 ppm erreicht 10 nicht);
        MNova-Bild: Mindestbereich (`AXIS_MIN`) und Signale."""
        from elucida.tabs import nmr_compare as NC
        rng = self.axis_range(s)
        ok, rtxt = range_check(s, rng)
        if s.get("kind", "1D") != "1D" or rng is None:
            return ok, rtxt, []
        out = NC.outside(NC.signal_spans(self.blocks() if bl is None else bl, NC.nucleus(s)), rng)
        if NC.own_1d(s):
            return not out, f"{rng[0] + 0.0:g} – {rng[1] + 0.0:g}".replace("-", "−"), out
        return (False if out else ok), rtxt, out

    @staticmethod
    def range_warning(s, out):
        if not out:
            return ""
        return "; ".join(T("nmr_rng_out", sig=XRAY.minus(t_)) for t_ in out[:4]) + (" …" if len(out) > 4 else "")

    def cmp_svg(self, specs, fmt="svg", out=None):
        """Vergleichsabbildung (16 × 11 cm, Text als Pfade) -> Pfad. Erstes Spektrum der Liste oben bzw. vorn, ein
        Bereich für alle (Vereinigung der Bereiche ihrer SI-Abbildungen), ohne Auswertung und Struktur. Eigene Ansicht
        ohne Bildschirm (`screen` False): nie mit Vorhersage. SVG/PDF ohne Datum, feste IDs (bytegleich wiederholbar)."""
        import json
        import zlib
        import matplotlib
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from elucida.tabs import nmr_compare as NC
        from elucida.tabs import nmr_view as NV
        c = self.cmp()
        data = []
        for s in specs:
            ds = self.raw_ds(s)
            ref = s["proc"].get("ref") or 0.0
            data.append((ds, self.raw_y(s, ds)["y"], ref, self.si_xlim(s, ds, ref)))
        hi, lo = max(max(d[3]) for d in data), min(min(d[3]) for d in data)
        labels = [NC.label_of(s, specs, c) for s in specs]
        if out is None:
            cdir = PRJ.work_dir(self.main.project_dir or Path(specs[0]["bruker"]).parent, self.STATE_KEY)
            tag = zlib.crc32(json.dumps([c["mode"], c.get("offset"), labels, specs, hi, lo] + self._text_tag(),
                                        sort_keys=True, default=str).encode())
            out = cdir / f"cmp_{NC.nucleus(specs[0])}_{tag:08x}.{fmt}"
            if out.exists():
                return str(out)
        w_cm, h_cm = OWN_SIZE_CM
        v = NV.NMRView()
        v.get_text_over = lambda: self.st.get("text_over")
        try:
            v.canvas = FigureCanvasAgg(v.fig)
            v.screen = False
            v.fig.set_dpi(72)
            v.fig.set_size_inches(w_cm / 2.54, h_cm / 2.54, forward=False)
            v.set_display(dict(self.view_opts(specs[0], data[0][2]), insets=[]))   # ohne Auswertung: keine Labels
            ds0, y0, ref0, _xl = data[0]
            v.set_spectrum(ds0["ax"] + ref0, y0, ds0["sf"], nucleus=ds0["nucleus"])
            v.traces = [dict(x=ds["ax"] + ref, y=y, color=NC.COLORS[(i + 1) % len(NC.COLORS)], label=labels[i + 1],
                             kind="trace", h=1.0) for i, (ds, y, ref, _x) in enumerate(data[1:])]
            v.stack, v.offset, v.main_label = c["mode"] == "stack", int(c.get("offset") or 100) / 100, labels[0]
            v.fit_highest(record=False, xlim=(hi, lo))
            v.selected = None
            v.redraw()
            meta = {"svg": {"Date": None}, "pdf": {"CreationDate": None, "ModDate": None}}.get(fmt)
            with matplotlib.rc_context({"svg.fonttype": "path", "svg.hashsalt": "elucida-nmr"}):
                v.fig.savefig(out, format=fmt, dpi=300 if fmt == "png" else 72, facecolor="white", metadata=meta)
        finally:
            v.deleteLater()
        return str(out)

    def export_cmp_figures(self, base):
        """Vergleichsabbildungen beim Export als <Verbindung>_NMR_comparison_<Kern>.svg/.pdf/.png nach figures/ (Formate
        des Tabs „Export“); Zurückgehaltenes meldet die Word-Datei (`cmp_blocks`). -> geschriebene Pfade."""
        if self.main.is_quick() or not self.main.project_dir:
            return []                                      # shortcut: Schnellauswertung ohne Vergleichsabbildungen
        files, fmt = [], self.main.export_fmt()
        for nuc, specs, why in self.cmp_groups():
            if why:                                        # gemeldet hat es schon die Word-Datei (`cmp_blocks`)
                continue
            out = PRJ.export_dir(self.main.project_dir, PRJ.FIGURES)
            for ext in ("svg", "pdf", "png"):
                if fmt.get(ext):
                    try:
                        files.append(self.cmp_svg(specs, ext, out / f"{base}_comparison_{nuc}.{ext}"))
                    except Exception as ex:
                        self.main.skip_part(ex, specs[0].get("bruker") or "")
        return files

    def cmp_heading(self):
        return (self.cmp().get("heading") or "").strip() or "NMR Comparisons"

    def cmp_blocks(self, img_dir):
        """Vergleichsabbildungen für Word: Bild (SVG + PNG-Ersatz) + Unterschrift je freigegebener Gruppe; abgelehnte
        meldet `skip_part(withheld=True)`; Gruppen mit nur einem Spektrum sind kein Vergleich und still."""
        from elucida.tabs import nmr_compare as NC
        out, name, bl = [], self.compound_name(), self.blocks()
        for nuc, specs, why in self.cmp_groups():
            if why == "nmr_cmp_few":
                continue
            if why:
                self.main.skip_part(T("nmr_cmp_withheld", why=T(why, nuc=sup_nuclei(nuc))),
                                    specs[0].get("bruker") or "", withheld=True, who=name)
                continue
            try:
                f = self.cmp_svg(specs)
                png = svg_png(f, Path(img_dir) / (Path(f).stem + "_nmr.png"))
            except Exception as ex:                        # nur dieser Vergleich fehlt, mit Grund gemeldet
                self.main.skip_part(ex, specs[0].get("bruker") or "")
                continue
            w, h = OWN_SIZE_CM
            out += [("image", str(png), FIG_W_CM, FIG_W_CM * h / w, f),
                    ("figcap", NC.caption_html(specs, bl, name, self.cmp()))]
        return out

    # -- Vorhersage (Octet; nur Ansicht, nie in einer Ausgabe) -------------------------------------------------------
    def pred_on(self):
        return bool(self.main.__dict__.get("_nmr_pred_on"))

    def pred_refusal(self, s):
        """Warum für s keine Vorhersage geht -> Text oder None."""
        from elucida.tabs import nmr_compare as NC
        if s is None or not NC.own_1d(s):
            return T("nmr_cmp_need_own")
        if NC.nucleus(s) not in NC.PRED_NUCLEI:
            return T("nmr_pred_need_nuc")
        p = self.structure_path()
        if not p or Path(p).suffix.lower() != ".cdxml":
            return T("nmr_pred_need_struct")
        return None

    def pred_req(self, s):
        """Anfrage an Octet für s: Struktur, Kern, Lösungsmittel (Octets Name), ¹H-Frequenz des Magneten."""
        from elucida.tabs import nmr_compare as NC
        if self.pred_refusal(s) is not None:
            return None
        nuc = NC.nucleus(s)
        try:
            sf = float(self.raw_ds(s)["sf"])
            p = Path(self.structure_path())
            mtime = p.stat().st_mtime_ns
        except (OSError, ValueError, KeyError, TypeError):
            return None
        return dict(structure=str(p), mtime=mtime, nucleus=nuc, solvent=NC.octet_solvent(s.get("solvent")),
                    decouple=None, mhz=int(round(sf / GAMMA_REL.get(nuc, 1.0))))

    @staticmethod
    def _pred_key(req):
        return tuple(req.get(k) for k in ("structure", "mtime", "nucleus", "solvent", "mhz"))

    def pred_result(self, s):
        """Vorhersage für s, solange der Chip an ist: dict(curve) oder dict(error); {} = läuft (einmal angefragt)."""
        if not self.pred_on():
            return None
        req = self.pred_req(s)
        if req is None:
            return None
        res = self.main.__dict__.setdefault("_nmr_pred_res", {})
        key = self._pred_key(req)
        if key not in res:
            res[key] = {}
            self.predictor().request(req)
        return res[key]

    def predictor(self):
        if getattr(self, "_predictor", None) is None:
            from elucida.tabs import nmr_compare as NC
            self._predictor = NC.Predictor(self, store=self.main.__dict__.setdefault("_nmr_pred_store", {}))
            self._predictor.done.connect(self.pred_done)
        return self._predictor

    def pred_done(self, req, v):
        from elucida.tabs import nmr_compare as NC
        res = self.main.__dict__.setdefault("_nmr_pred_res", {})
        key = self._pred_key(req)
        p = (v.get("prediction") or {}) if isinstance(v, dict) else {}
        if isinstance(v, str):
            res[key] = dict(error=T("nmr_pred_failed", e=v))
        elif not p.get("lines"):
            res[key] = dict(error=T("nmr_pred_none", nuc=sup_nuclei(req["nucleus"])))
        else:
            span = {"1H": (-20.0, 20.0), "13C": (-50.0, 260.0)}.get(req["nucleus"], (-400.0, 300.0))
            ppm = [l_["ppm"] for l_ in p["lines"]]
            res[key] = dict(curve=NC.lorentz(p["lines"], min(span[0], min(ppm) - 5), max(span[1], max(ppm) + 5)),
                            acs=p.get("acs"))
        self._raw_s = None                                 # neue Spur: Höhe neu einpassen
        try:
            self.update_preview()
        except RuntimeError:                               # Tab inzwischen ersetzt
            pass

    def pred_toggled(self, on):
        if self._loading:
            return
        self.main.__dict__["_nmr_pred_on"] = bool(on)      # nie im Zustand: kein Rückgängig-Schritt, nie gespeichert
        self._raw_s = None
        self.update_preview()

    # -- Struktur im Spektrum ---------------------------------------------------------------
    def structure_path(self):
        """Eigene Struktur des Tabs, sonst die der Verbindung (CDXML; gleichnamige ChemDraw-SVG/PDF hat Vorrang)."""
        p = self.st.get("structure") or (getattr(self.main, "compound", None) or {}).get("structure")
        return p if PRJ.has_structure(p) else None

    def pick_structure(self):
        p, _ = QFileDialog.getOpenFileName(self, T("nmr_struct_pick"), self.main.settings.value("last_dir", ""),
                                           f"{T('nmr_struct_flt')} (*.cdxml *.svg *.pdf *.png);;{T('flt_all')}")
        if p:
            self.st["structure"] = self.main.import_file(p, PRJ.STRUCTURES)      # ChemDraw-Exporte daneben kommen mit
            self.changed()

    def structure_asset(self):
        from elucida.core import images as IMG
        p = self.structure_path()
        if p is None:
            return None
        key = ("nmrstruct", p)
        if key not in self.main.extra_cache:
            self.main.extra_cache[key] = IMG.load_structure(p)
        st = self.main.extra_cache[key]
        return st if st.get("pdf") else None

    def struct_xy(self, s, st):
        """Lage der Struktur (fx, fy); „auto“ sucht die freie Stelle für Struktur samt Beschriftung
        (Ergebnis zwischengespeichert)."""
        width = self.struct_w() / 100
        pos = s.get("struct_pos", "auto")
        if s.get("source") == "bruker" and s.get("proc"):  # eigenes Spektrum: vor den Ausschnitten gesetzt
            xy = self.raw_place(s)["xy"]
            if xy:
                return tuple(xy)
        src = self.svg_source(s)
        if pos != "auto":
            return place_structure(src, st, pos, width, s.get("struct_xy"))
        extra = round(label_height(self.label(s)) * LABEL_F / max(width, 1e-6), 3)
        key = ("nmrauto", src, self.structure_path(), round(width, 3), extra)
        if key not in self.main.extra_cache:
            self.main.extra_cache[key] = place_structure(src, st, "auto", width, extra=extra)
        return self.main.extra_cache[key]

    def label(self, s):
        """Beschriftung unter der Struktur als Umrisse (Nummer, Messangaben nach den Chips), zwischengespeichert."""
        lines = tuple(label_lines(s, self.blocks(), self.compound_name(), self.st.get("label_no", True),
                                  self.st.get("label_info", True)))
        return self.main.extra_cache.setdefault(("nmrlabel", lines), label_shapes(lines)) if lines else []

    def label_toggled(self, *_):
        new = dict(label_no=self.cb_lab_no.isChecked(), label_info=self.cb_lab_info.isChecked())
        # nur eine echte Änderung zählt: beim Aufbau des Tabs meldet der Chip-Ersatz den Anfangszustand (sonst entstand
        # bei jedem Neuaufbau ein Rückgängig-Schritt)
        if self._loading or all(self.st.get(k, True) == v for k, v in new.items()):
            return
        self.st.update(new)
        self.changed()

    def axis_range(self, s):
        """Beschrifteter Bereich der Achse des Spektrums (zwischengespeichert), None ohne Zahlenreihe."""
        from elucida.formats.mnova import svg_axis_range
        key = ("nmrrange", s["file"])
        if s.get("source") == "bruker" and s.get("proc") and s.get("kind", "1D") == "1D":
            try:                                           # eigenes Spektrum: Bereich seiner Abbildung
                xl = self.si_xlim(s, self.raw_ds(s), s["proc"].get("ref") or 0.0)
                return (round(min(xl), 2), round(max(xl), 2))
            except (OSError, ValueError):
                return None
        if not Path(s["file"]).is_file():                  # eigenes Spektrum (Ordner): keine Mnova-Beschriftung
            return None
        if key not in self.main.extra_cache:
            try:
                self.main.extra_cache[key] = None if is_emf(s["file"]) else svg_axis_range(s["file"])
            except Exception:
                self.main.extra_cache[key] = None
        return self.main.extra_cache[key]

    def figure_svg(self, s):
        """SVG für Word: Mnova-SVG, wahlweise mit eingesetzter Struktur (Datei unter .elucida/nmr)."""
        st = self.structure_asset() if s.get("struct_on", True) else None
        src = self.svg_source(s)
        if st is None:                                   # ohne Struktur: MNova-Kopie mit lesbaren Schriften (svg_fonts)
            return src
        fx, fy = self.struct_xy(s, st)
        width = self.struct_w() / 100
        cdir = PRJ.work_dir(self.main.project_dir or Path(s["file"]).parent, self.STATE_KEY)
        import zlib
        lab = self.label(s)
        tag = f"_{zlib.crc32(repr(label_lines(s, self.blocks(), self.compound_name(), self.st.get('label_no', True), self.st.get('label_info', True))).encode()):08x}" if lab else ""
        out = cdir / f"{Path(src).stem}{tag}_{int(fx * 1000)}_{int(fy * 1000)}_{int(width * 1000)}.svg"
        key = ("nmrcomp", src, self.structure_path(), out.name)
        if key not in self.main.extra_cache or not out.exists():
            self.main.extra_cache[key] = compose_structure(src, st, out, (fx, fy), width, label=lab)
        return str(out)

    def svg_source(self, s):
        """SVG des Spektrums ohne Struktur: Mnova-Datei oder das eigene Spektrum (`raw_svg`, 2D `raw_svg2d`)."""
        if s.get("source") == "bruker" and s.get("kind", "1D") != "1D":
            return self.raw_svg2d(s)
        return self.raw_svg(s) if s.get("source") == "bruker" and s.get("proc") else self.fonts_svg(s["file"])

    def fonts_svg(self, path):
        """MNova-SVG mit lesbaren Schriften (`svg_fonts`) und Rand um überstehende Achsenzahlen (`svg_fit`) als Kopie
        unter .elucida/nmr; die Datei selbst bleibt unverändert. Ohne Änderung der Pfad selbst."""
        import zlib
        from elucida.formats.mnova import svg_fonts
        p = Path(path)
        if p.suffix.lower() != ".svg" or not p.is_file():
            return path
        st = p.stat()
        key = ("nmrfonts", str(p), st.st_mtime_ns, st.st_size)
        if key not in self.main.extra_cache or not Path(self.main.extra_cache[key]).exists():
            txt = p.read_text(encoding="utf-8", errors="replace")
            fixed, out = svg_fit(svg_fonts(txt)), str(path)
            if fixed != txt:
                import tempfile                                  # ohne Verbindung nie neben die Datei des Nutzers
                o = PRJ.work_dir(self.main.project_dir or tempfile.gettempdir(), self.STATE_KEY) / \
                    f"{p.stem}_fonts_{zlib.crc32(fixed.encode()):08x}.svg"
                if not o.exists():
                    o.write_text(fixed, encoding="utf-8")
                out = str(o)
            self.main.extra_cache[key] = out
        return self.main.extra_cache[key]

    def raw_svg(self, s):
        """Eigenes Spektrum als SVG (16 × 11 cm, Text als Pfade) im Bereich der Abbildung, wie die Ansicht ohne
        Bedienhilfen (Auswahl, Fit-Linien, Drehpunkt); Datei unter .elucida/nmr, Name aus dem Zustand."""
        import json
        import zlib
        from elucida.tabs.nmr_view import NMRView
        ds = self.raw_ds(s)
        c = self.raw_y(s, ds)
        ref = s["proc"].get("ref") or 0.0
        cdir = PRJ.work_dir(self.main.project_dir or Path(s["bruker"]).parent, self.STATE_KEY)
        tag = zlib.crc32(json.dumps([s, self.si_xlim(s, ds, ref)] + self._text_tag(), sort_keys=True,
                                    default=str).encode())
        st = self.structure_asset() if s.get("struct_on", True) else None
        width = self.struct_w() / 100
        tag = zlib.crc32(f"{tag}|{self.structure_path()}|{width}|{self.label(s) and len(self.label(s))}".encode())
        out = cdir / f"{Path(s['bruker']).name}_own_{tag:08x}.svg"
        if out.exists() and out.with_suffix(".json").exists():
            return str(out)
        w_cm, h_cm = OWN_SIZE_CM                           # „size“ ist die Seite des Mnova-SVG, nicht dieses Bild
        v = NMRView()
        v.get_text_over = lambda: self.st.get("text_over")
        try:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            v.canvas = FigureCanvasAgg(v.fig)             # ohne Qt-Fläche: deren Gastgeber setzt sonst die Bildgröße
            v.screen = False
            v.fig.set_dpi(72)                              # Bildpunkte = pt: Abstände der Vorlage gelten im SVG
            v.fig.set_size_inches(w_cm / 2.54, h_cm / 2.54, forward=False)
            v.set_display(self.view_opts(s, ref))
            f = s["proc"].get("ref_found")
            v.set_solvents([dict(x=f + ref, name=solvent_text(s.get("solvent") or ds["solvent"]))]
                           if f is not None else [])
            self.push_analysis(s, ds, c, ref, v, export=True)
            v.set_spectrum(ds["ax"] + ref, c["y"], ds["sf"], nucleus=ds["nucleus"])
            v.fit_highest(record=False, xlim=self.si_xlim(s, ds, ref))
            v.selected = None
            xy = None
            if st is not None:                             # erst die Struktur (Bild ohne Ausschnitte), dann meiden die
                insets, v.insets, v.struct_left = v.insets, [], False      # Ausschnitte ihre echte Box
                v.redraw()
                v.fig.savefig(out, format="svg", dpi=72, facecolor="white")
                pos = s.get("struct_pos", "auto")
                extra = label_height(self.label(s)) * LABEL_F / max(width, 1e-6)
                xy = place_structure(str(out), st, pos, width, s.get("struct_xy"), extra=extra)
                h = width * (struct_aspect(st) + extra) * w_cm / h_cm
                v.struct_box = (xy[0], 1 - xy[1] - h, xy[0] + width, 1 - xy[1])
                v.insets = insets
            v.redraw()
            import matplotlib
            with matplotlib.rc_context({"svg.fonttype": "path"}):   # Text als Pfade (Word, ohne Schrift beim Leser)
                v.fig.savefig(out, format="svg", dpi=72, facecolor="white")
            out.with_suffix(".json").write_text(json.dumps(plain_data(dict(xy=xy, box=v.struct_box, notes=v.notes))),
                                                encoding="utf-8")
        finally:
            v.deleteLater()
        return str(out)

    def raw_place(self, s):
        """Lage der Struktur und Hinweise der SI-Abbildung des eigenen Spektrums (aus `raw_svg`): {xy, box, notes}."""
        import json
        return json.loads(Path(self.raw_svg(s)).with_suffix(".json").read_text(encoding="utf-8"))

    def add_bruker(self):
        s = self.current()
        if s is None:
            return
        d = QFileDialog.getExistingDirectory(self, T("nmr_bruker"), self.main.settings.value("last_dir", ""))
        if d:
            self.set_bruker(s, d)

    def set_bruker(self, s, path):
        d = bruker_dir(path)
        if d is None:
            self.main.error(T("nmr_no_acqus", p=Path(path).name))
            return False
        d = Path(self.import_experiment(d))
        s["bruker"] = str(d)
        s["params"] = acq_params(d)
        self.changed()
        return True

    def import_experiment(self, e):
        """Ein Experiment ganz nach data/nmr/<Art>/<Datensatz>_<Nummer>, in die Rohdaten-Liste -> Pfad im Projekt."""
        kind = experiment_kind(acq_params(e))
        dst = self.main.import_file(str(e), PRJ.data_sub(self.STATE_KEY) + "/" + kind, name=experiment_name(e))
        raws = self.st.setdefault("raw", [])
        if not any(Path(r["path"]) == Path(dst) for r in raws):
            raws.append(dict(path=dst, kind=kind, name=Path(dst).name))
        return dst

    def temp_from_bruker(self):
        s = self.current()
        if s is not None and (s.get("params") or {}).get("te"):
            s["temp"] = round(s["params"]["te"])
            self.changed()

    def text_changed(self):
        self.st["text"] = self.ed_text.toPlainText()
        self._loading = True
        self.fill_signals()
        self._loading = False
        self.update_preview()
        self.main.push_undo()

    def assign_edited(self, item):
        if self._loading or item.column() != 5:
            return
        key = item.data(Qt.UserRole)
        if str(key).startswith("own|"):                    # eigenes Signal: Zuordnung am Signal (wie in der Auswertung)
            uid = key.split("|", 1)[1]
            for s_ in self.st["spectra"]:
                for g in (s_.get("ana") or {}).get("signals") or ():
                    if g.get("uid") == uid:
                        g["assign"] = item.text().strip()
        else:
            self.st.setdefault("assign", {})[key] = item.text().strip()
        self._loading = True
        lines = self.nmr_lines()
        self.txt_line.setHtml("<br>".join(h for _, h in lines))
        self._loading = False
        self.main.push_undo()

    def copy_lines(self):
        from elucida.tabs.ir_ea import copy_rich
        lines = self.nmr_lines()
        if lines:
            copy_rich("; ".join(p for p, _ in lines), "; ".join(h for _, h in lines))

    def changed(self):
        self.sync_widgets()
        self.main.push_undo()

    def update_preview(self, xy=None):
        """Vorschau = Spektrum (Mnova-SVG) + Struktur als Bild an ihrer Lage; die Struktur lässt sich ziehen."""
        if "spectra" not in self.st:                   # alter Tab nach dem Schließen der Verbindung (Zustand geleert,
            return                                     # der neue Tab ist schon gebaut): verspätete Vorschau überspringen
        s = self.current()
        self._drag_rect = None
        if s is not None and s.get("source") == "bruker" and s.get("kind", "1D") != "1D":
            self.right_tabs.set_empty(self.si_page, False)     # Reiter „SI-Abbildung“ wie bei 1D
            self.show_2d(s)
            return self.update_si_preview()
        raw = s is not None and s.get("source") == "bruker" and bool(s.get("proc"))
        self.right_tabs.set_empty(self.si_page, not raw)
        if raw:
            self.show_raw(s)
            return self.update_si_preview()
        try:                                               # MNova-Bild: Signale der SI-Zeile außerhalb der Achse
            out = self.range_state(s)[2] if s is not None else []
        except Exception:
            out = []
        self.lbl_rng.setText("⚠ " + self.range_warning(s, out) if out else "")
        empty = s is None or not Path(s["file"]).is_file()
        self.preview_stack.setCurrentIndex(0 if empty else 1)
        if empty:
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_cap.setText("")
            return
        n = self.spectra().index(s) + 1
        if is_emf(s["file"]):                              # EMF: keine eigene Darstellung, geht unverändert nach Word
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_prev.setText(T("nmr_emf_preview", f=Path(s["file"]).name))
            suspend_canvas(self.lbl_prev, True)                # Text im Theme, nur Bilder werden umgefärbt
            self.lbl_cap.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))
            return
        self.lbl_prev.setText("")
        suspend_canvas(self.lbl_prev, False)
        import pymupdf
        # in Gerätepixeln rendern (HiDPI-Bildschirme), angezeigt in logischen Pixeln
        dpr = max(1.0, self.lbl_prev.devicePixelRatioF())
        cache = self.main.extra_cache
        akey = ("nmraspect", s["file"])
        if akey not in cache:
            try:
                r_ = pymupdf.open(self.fonts_svg(s["file"]))[0].rect      # Seite der Kopie (Rand, svg_fit)
            except Exception as ex:                        # gespeicherte Datei, die sich nicht öffnen lässt: Tab bleibt
                self.lbl_prev.setPixmap(QPixmap())         # bedienbar, Grund mit Dateinamen statt Vorschau
                self.lbl_prev.setText(T("skip_item", f=Path(s["file"]).name, e=ex))
                suspend_canvas(self.lbl_prev, True)
                self.lbl_cap.setText("")
                return
            cache[akey] = max(r_.width, 1) / max(r_.height, 1)
        # wie CanvasHost: ganzes Bild in die Fläche einpassen (Breite und Höhe), Seitenverhältnis der Mnova-Seite
        aw = max(100.0, self.lbl_prev.width() - 10.0)
        ah = max(80.0, self.lbl_prev.height() - 10.0)
        lw_ = float(int(min(aw, ah * cache[akey])))
        key = ("nmrprev", s["file"], int(lw_ * dpr) // 50)
        if key not in cache:
            page = pymupdf.open(self.fonts_svg(s["file"]))[0]        # Schriften wie in Word/SI (svg_fonts)
            dpi = int(round(max(60, min(600, lw_ * dpr / max(page.rect.width, 1) * 72))))   # pymupdf: nur ganze Zahl
            pix = page.get_pixmap(dpi=dpi)
            cache[key] = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        base = cache[key]
        pm = QPixmap.fromImage(base).scaledToWidth(int(lw_ * dpr), Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        lh_ = pm.height() / dpr
        st = self.structure_asset() if s.get("struct_on", True) else None
        if st is not None and st.get("rgba") is not None:
            from PySide6.QtGui import QPainter
            fx, fy = xy or self.struct_xy(s, st)
            sw = lw_ * self.struct_w() / 100
            sh = sw * struct_aspect(st)
            a = st["rgba"]
            simg = QImage(a.data, a.shape[1], a.shape[0], a.strides[0], QImage.Format_RGBA8888).scaled(
                max(1, int(sw * dpr)), max(1, int(sh * dpr)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            simg.setDevicePixelRatio(dpr)                  # vorher glatt verkleinern: 2400 px direkt gezeichnet ließ Bindungen ausfallen
            p = QPainter(pm)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawImage(QRectF(fx * lw_, fy * lh_, sw, sh), simg)
            p.setPen(QColor("#2a7ae2"))
            p.drawRect(QRectF(fx * lw_, fy * lh_, sw, sh))
            lab = self.label(s)
            if lab:                                        # Nummer und Messangaben wie im exportierten SVG (Umrisse)
                from PySide6.QtGui import QPainterPath
                p.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                for sh_, k_, x_, y_ in label_place(lab, fx * lw_ + sw / 2, fy * lh_ + sh, lw_ * LABEL_F):
                    for code, v in sh_["segs"]:
                        q = [(x_ + k_ * v[i], y_ - k_ * v[i + 1]) for i in range(0, len(v), 2)]
                        if code == 1:
                            path.moveTo(*q[0])
                        elif code == 2:
                            path.lineTo(*q[0])
                        elif code == 3:
                            path.quadTo(*q[0], *q[1])
                        elif code == 4:
                            path.cubicTo(*q[0], *q[1], *q[2])
                        elif code == 79:
                            path.closeSubpath()
                p.fillPath(path, QColor("#000000"))
            p.end()
            self._drag_rect = (fx, fy, sw / lw_, sh / lh_)
        self.lbl_prev.setPixmap(pm)
        self._pm_size = (lw_, lh_)
        n = self.spectra().index(s) + 1
        self.lbl_cap.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))

    def update_si_preview(self):
        """Reiter „SI-Abbildung“: das eigene Spektrum mit Struktur und Beschriftung wie im Word-Export (nur sichtbar
        gerechnet: SVG + Struktur kosten ~0.3 s)."""
        s = self.current()
        own2d = s is not None and s.get("source") == "bruker" and s.get("kind", "1D") != "1D"
        s = s if own2d else self.raw_current()
        if self.right_tabs.currentWidget() is not self.si_page:
            return
        if s is None:                                      # leerer Zustand: ein Satz, was fehlt (unslop #13)
            self.lbl_si_state.setText("")
            self.lbl_si_prev.setPixmap(QPixmap())
            return self.lbl_si_prev.setText(T("nmr_si_need_raw"))
        src, why = self.figure_source(s)
        self.lbl_si_state.setText(T("nmr_fig_mnova" if src else "nmr_fig_none", why=T(why)) if why else "")
        import pymupdf
        try:
            f = self.figure_svg(s)
            page = pymupdf.open(f)[0]
        except Exception as ex:                            # Grund statt Bild, der Tab bleibt bedienbar
            self.lbl_si_prev.setPixmap(QPixmap())
            return self.lbl_si_prev.setText(T("skip_item", f=Path(s["file"]).name, e=ex))
        dpr = max(1.0, self.lbl_si_prev.devicePixelRatioF())
        aw, ah = max(100.0, self.lbl_si_prev.width() - 10.0), max(80.0, self.lbl_si_prev.height() - 10.0)
        lw_ = min(aw, ah * page.rect.width / max(page.rect.height, 1))
        pix = page.get_pixmap(dpi=int(round(max(60, min(600, lw_ * dpr / max(page.rect.width, 1) * 72)))))
        pm = QPixmap.fromImage(QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy())
        pm.setDevicePixelRatio(dpr)
        self.lbl_si_prev.setText("")
        self.lbl_si_prev.setPixmap(pm)
        for n_ in ([] if own2d else self.raw_place(s).get("notes") or ()):   # kein Platz für einen Ausschnitt: sagen
            self.main.statusBar().showMessage(n_, 8000)

    def _frac(self, pos):
        """Mausposition in der Vorschau -> Anteil (x, y) des Spektrums (Bild ist im Label zentriert)."""
        pw, ph = self._pm_size
        ox = (self.lbl_prev.width() - pw) / 2
        oy = (self.lbl_prev.height() - ph) / 2
        return (pos.x() - ox) / max(pw, 1), (pos.y() - oy) / max(ph, 1)

    def eventFilter(self, obj, ev):
        if obj is self.lbl_prev and ev.type() == QEvent.Resize and getattr(self, "_drag", 1) is None:
            # sofort neu einpassen (auch bei Splitter/Reiter/verzögertem Layout, nicht nur beim Fenster): Bild passt
            # immer zur aktuellen Labelgröße; kein Rückkopplungsrisiko, die Labelgröße hängt nicht vom Pixmap ab
            self.update_preview()
        if obj is not self.lbl_prev or self._drag_rect is None:
            return super().eventFilter(obj, ev)
        t = ev.type()
        if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            if x <= fx <= x + w and y <= fy <= y + h:
                self._drag = (fx - x, fy - y)
                self.lbl_prev.setCursor(Qt.ClosedHandCursor)
                return True
        elif t == QEvent.Wheel and self._drag is None:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            if x <= fx <= x + w and y <= fy <= y + h:
                steps = ev.angleDelta().y() / 120
                if steps:
                    self.sp_sw.setValue(self.sp_sw.value() + (1 if steps > 0 else -1) * max(1, round(abs(steps))))
                return True
        elif t == QEvent.MouseMove and self._drag is not None:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            nx = min(max(fx - self._drag[0], 0.0), 1.0 - w)
            ny = min(max(fy - self._drag[1], 0.0), 1.0 - h)
            self.update_preview((nx, ny))
            return True
        elif t == QEvent.MouseButtonRelease and self._drag is not None:
            self._drag = None
            self.lbl_prev.unsetCursor()
            s = self.current()
            if s is not None and self._drag_rect is not None:
                s["struct_pos"] = "manual"
                s["struct_xy"] = [round(self._drag_rect[0], 4), round(self._drag_rect[1], 4)]
                self.changed()
            return True
        return super().eventFilter(obj, ev)

    # -- Export ---------------------------------------------------------------------------
    def docx_blocks(self, img_dir, cmp=True):
        """Zwei Spektren je Seite: Bild (SVG + PNG-Ersatz) 16 cm breit, darunter „Figure Sn: …“. Zurückgehaltene eigene
        Abbildungen (Freigabe fehlt) meldet `skip_part(withheld=True)` (eigene Zeile in der Exportmeldung). cmp: die
        Vergleiche (Überlagert/Gestapelt) unter ihrer Überschrift danach (Gesamt-SI holt sie über `cmp_blocks` selbst)."""
        blocks = []
        name = self.compound_name()
        bl = self.blocks()
        from elucida.si import lines as SI
        for s in self.spectra():
            src, why = self.figure_source(s)
            a_ = s.get("ana") or {}
            if why == "nmr_own_not_chosen" and src is None and not (a_.get("signals") or a_.get("peaks_ok")):
                why = None                                 # nie gewählt, nichts ausgewertet (z. B. abgelegter Ordner): wie
            if why:                                        # printed_blocks kein Hinweis; sonst sagen, was stattdessen kommt
                msg = T("nmr_fig_mnova" if src else "nmr_fig_none", why=T(why))
                self.main.skip_part(msg, s.get("bruker") or s["file"], withheld=True, who=name)   # eine Meldung für alle Wege
            if src is None:
                continue
            s = dict(s, source=src)
            if is_emf(s["file"]):                          # unverändert (Vektor in Word, ohne eingesetzte Struktur)
                w, h = s.get("size") or emf_info(s["file"])["size_cm"]
                blocks += [("image", s["file"], FIG_W_CM, FIG_W_CM * h / w), ("figcap", caption_html(s, bl, name))]
                continue
            try:
                f = self.figure_svg(s)
                png = svg_png(f, Path(img_dir) / (Path(f).stem + "_nmr.png"))
                if s.get("source") == "bruker":
                    w, h = OWN_SIZE_CM
                else:                                      # Seite der Kopie: svg_fit kann den Rand vergrößern
                    import pymupdf
                    r_ = pymupdf.open(f)[0].rect
                    w, h = r_.width, r_.height
            except Exception as ex:                        # nur dieses Spektrum fehlt, mit Datei und Grund gemeldet
                self.main.skip_part(ex, s["file"])
                continue
            blocks += [("image", str(png), FIG_W_CM, FIG_W_CM * h / w, f), ("figcap", caption_html(s, bl, name))]
        cb = self.cmp_blocks(img_dir) if cmp else []
        return SI.two_per_page(blocks + ([("heading", self.cmp_heading())] + cb if cb else []))

    def figure_source(self, s):
        """Welche Abbildung eines Spektrums in die SI kommt -> (Quelle „mnova“/„bruker“ oder None, Grund oder None).
        Eigene Abbildung nur „für die SI“ gewählt und (1D) mit bestätigter Phase und Referenz; sonst die Mnova-Datei des
        Spektrums, falls es eine gibt."""
        mn = "mnova" if Path(s["file"]).is_file() else None
        if s.get("source") != "bruker":
            return mn, None
        why = own_release(s) if s.get("kind", "1D") == "1D" else self.own2d_release(s)
        return ("bruker", None) if why is None else (mn, why)

    def copy_figure(self, tmp):
        """Abbildung kopieren (Entscheidung 128): das sichtbare Spektrum wie in Word, mit denselben Freigaben
        (zurückgehalten -> nichts, der Grund als Text); Bereich aus dem Feld, nicht aus dem Zoom -> (SVG, PNG)."""
        s = self.current()
        if s is None:
            return T("copy_fig_none")
        for nuc, specs, why in self.cmp_groups():          # Vergleich sichtbar: ihn kopieren, mit seiner Freigabe
            if any(m["uid"] == s["uid"] for m in specs) and len(specs) >= 2:
                if why:
                    return T("copy_fig_held", why=T(why, nuc=sup_nuclei(nuc)))
                f = self.cmp_svg(specs)
                return f, svg_png(f, Path(tmp) / (Path(f).stem + "_nmr.png"))
        src, why = self.figure_source(s)
        if why:
            return T("copy_fig_held", why=T(why))
        if src is None or is_emf(s["file"]):              # EMF geht nur unverändert nach Word
            return T("copy_fig_none")
        f = self.figure_svg(dict(s, source=src))
        return f, svg_png(f, Path(tmp) / (Path(f).stem + "_nmr.png"))

    def export_word(self):
        from elucida.tabs.base import _export_word
        _export_word(self)

    def export_dialog(self, path=None):
        """Word-Datei mit allen Spektren und Unterschriften, dazu die NMR-Zeile als Text (SI/<Name>_NMR.*)."""
        from elucida.si import lines as SI
        if not self.main.ensure_project():
            return None
        if not self.spectra() and not self.nmr_lines():
            self.main.error(T("nmr_empty"))
            return None
        out = PRJ.export_dir(self.main.project_dir, PRJ.SI_DIR)
        base = PRJ.export_stem(self.compound_name() or self.main.export_name(), self.STATE_KEY)
        path = Path(path) if path else out / f"{base}.docx"
        with self.main.collecting_skips():                 # zurückgehalten/unlesbar: in die eine Exportmeldung (exported)
            try:
                SI.write_docx(path, self.docx_blocks(PRJ.work_dir(self.main.project_dir, self.STATE_KEY)))
            except PermissionError:
                self.main.error(T("report_locked", p=path))
                return None
        lines = self.nmr_lines()
        if lines:
            (out / f"{base}.txt").write_text("; ".join(p for p, _ in lines) + "\n", encoding="utf-8")
        self._extra_files = self.export_cmp_figures(base)
        if self.main.is_quick() and path.parent == out:  # Schnellauswertung: in den gewählten Ordner
            path = (self.main.place_exports([path] + ([out / f"{base}.txt"] if lines else [])) or [path])[0]
        self.main.log_signal.emit(T("saved", p=str(path)))
        return path

