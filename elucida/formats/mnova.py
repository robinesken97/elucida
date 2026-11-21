"""
elucida/formats/mnova.py - Spektren-Exporte aus MestReNova: SVG (Kern aus der Achse „δ ¹H (ppm)“, Peaklabels) und EMF (Kern aus den Texten, Größe aus dem Header).
"""
from __future__ import annotations

import re
from pathlib import Path
from elucida.app.i18n import T


_NUC = re.compile(r"δ\s*(\d{1,3})\s*([A-Z][a-z]?)\s*\(ppm\)")


def is_emf(path):
    return Path(path).suffix.lower() == ".emf"


def emf_info(path):
    """Mnova-EMF -> wie svg_info. Kern aus den Texten (EMR_EXTTEXTOUTW, „δ 1H (ppm)“), Größe aus dem Header.
    Die Richtung der Beschriftung ist nicht bekannt: zwei verschiedene Kerne = 2D (erster = x). Elucida zeichnet EMF
    nicht selbst (keine Vorschau), sie geht unverändert nach Word."""
    import struct
    from elucida.formats.ms_report import _emf_texts
    data = Path(path).read_bytes()
    if len(data) < 40 or struct.unpack_from("<I", data, 0)[0] != 1:
        raise ValueError(T("nmr_emf_bad"))
    left, top, right, bottom = struct.unpack_from("<iiii", data, 24)          # rclFrame in 0.01 mm
    texts = _emf_texts(data)
    joined = " ".join(texts)
    nuclei = []
    for m in _NUC.finditer(joined):
        n = f"{m.group(1)}{m.group(2)}"
        if n not in nuclei:
            nuclei.append(n)
    return dict(nuclei=nuclei[:2], is2d=len(nuclei) > 1, size_cm=((right - left) / 1000.0, (bottom - top) / 1000.0))


def spectrum_info(path):
    return emf_info(path) if is_emf(path) else svg_info(path)


def svg_info(path):
    """Mnova-SVG -> dict(nuclei=[x, (y)], is2d, size_cm). Kern aus „δ ¹H (ppm)“ (waagerecht = x, senkrecht = y)."""
    import pymupdf
    doc = pymupdf.open(str(path))
    page = doc[0]
    w, h = page.rect.width / 72 * 2.54, page.rect.height / 72 * 2.54
    horiz, vert = [], []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            txt = "".join(s["text"] for s in ln["spans"])
            m = _NUC.search(txt)
            if not m:
                continue
            nuc = f"{m.group(1)}{m.group(2)}"
            dx, dy = ln.get("dir", (1, 0))
            (horiz if abs(dx) >= abs(dy) else vert).append(nuc)
    nuclei = []
    if horiz:
        nuclei.append(max(set(horiz), key=horiz.count))
    if vert:
        nuclei.append(max(set(vert), key=vert.count))
    return dict(nuclei=nuclei, is2d=bool(vert), size_cm=(w, h))


def svg_axis_range(path):
    """Kleinste und größte Zahl der waagerechten Achsenbeschriftung eines 1D-Mnova-SVG -> (lo, hi) oder None (keine
    Zahlenreihe gefunden). Das ist der beschriftete Bereich; die Achse selbst kann etwas weiter reichen.
    Achse = längste Textzeile mit ≥ 3 verschiedenen Zahlen in gleichen Schritten; Integrale unter dem Spektrum sind
    nicht gleichmäßig gestuft und zählen nicht, auch wenn sie mehr Zahlen haben.
    shortcut: eine Achse mit fehlender Beschriftung (Lücke im Raster) gilt als nicht gefunden (None, „nicht geprüft“);
    erst mit einem echten Beispiel lockern."""
    import pymupdf
    page = pymupdf.open(str(path))[0]
    rows = {}
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            dx, dy = ln.get("dir", (1, 0))
            if abs(dx) < abs(dy):
                continue
            toks = "".join(s["text"] for s in ln["spans"]).replace("\u2212", "-").split()
            if toks and all(re.fullmatch(r"-?\d+(\.\d+)?", t) for t in toks):
                rows.setdefault(round(ln["bbox"][3] / 4), []).extend(float(t) for t in toks)   # eine Textzeile ± 4 pt
    def axis_like(vals):
        v = sorted(set(vals))
        steps = [round(b - a, 6) for a, b in zip(v, v[1:])]
        return len(v) == len(vals) >= 3 and len(set(steps)) == 1
    vals = max((v for v in rows.values() if axis_like(v)), key=len, default=[])
    return (min(vals), max(vals)) if vals else None


def svg_peaks(path):
    """Peaklabels eines Mnova-SVG (senkrechte Zahlen über dem Spektrum) -> (Verschiebungen als Text wie gedruckt,
    absteigend; Lösungsmittel, falls ein Label einen Namen trägt, z. B. „77.16 CDCl3“). Das Lösungsmittelsignal
    selbst fällt weg."""
    vals, label = svg_peak_labels(path)
    return vals, label[1] if label else None


def svg_peak_labels(path):
    """Wie `svg_peaks`, aber mit dem beschrifteten Lösungsmittelsignal als (Wert als Text, Name), sonst None."""
    import pymupdf
    page = pymupdf.open(str(path))[0]
    vals, solvent = [], None
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            dx, dy = ln.get("dir", (1, 0))
            if abs(dy) <= abs(dx):
                continue
            txt = "".join(sp["text"] for sp in ln["spans"]).strip()
            m = re.fullmatch(r"([-−]?\d+\.\d+)\s*(\S.*)?", txt)
            if not m:
                continue
            if m.group(2):
                if m.group(2).strip().upper() != "TMS":                 # Referenz, kein Lösungsmittel
                    solvent = (m.group(1).replace("−", "-"), m.group(2).strip())
                continue
            vals.append(m.group(1).replace("−", "-"))
    vals = sorted(set(vals), key=float, reverse=True)
    return vals, solvent


SANS = "Arial, Helvetica, sans-serif"
_SHELL = {"ms shell dlg 2", "ms shell dlg"}          # Windows-Aliasse der Qt-Standardschrift, die MNova 14.2 schreibt
_TAG = re.compile(r"""<(/?)([A-Za-z][\w.:-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(/?)>""")
_FAMILY = re.compile(r"""(\sfont-family\s*=\s*)(["'])(.*?)\2""")


def svg_fonts(txt):
    """Schriften eines MNova-SVG für Renderer ohne Windows-Aliasse (MuPDF, Word unter macOS): „MS Shell Dlg 2“/„MS Shell
    Dlg“ → Arial, Helvetica, sans-serif; jedes <text> bekommt die Familie selbst, weil MuPDF sie nicht von <g>/<svg>
    erbt (ohne Angabe: Times). Ohne Familie in der Kette → Arial. Text unverändert, wenn nichts zu tun ist."""
    out, pos, stack = [], 0, [None]
    for m in _TAG.finditer(txt):
        close, name, attrs, empty = m.groups()
        if close:
            if len(stack) > 1:
                stack.pop()
            continue
        f = _FAMILY.search(attrs)
        own = f.group(3) if f else None
        new = attrs
        if own is not None and own.strip().lower() in _SHELL:
            new, own = attrs[:f.start(3)] + SANS + attrs[f.end(3):], SANS
        fam = own or stack[-1]
        if name == "text" and own is None:
            q = "'" if '"' in (fam or "") else '"'
            new += f" font-family={q}{fam or SANS}{q}"
        if new != attrs:
            out += [txt[pos:m.start(3)], new]
            pos = m.end(3)
        if not empty:
            stack.append(fam)
    return "".join(out + [txt[pos:]]) if out else txt


def is_nmr_svg(path):
    """Mnova-SVG (Titel „MestReNova …“ oder δ-Achse)."""
    p = Path(path)
    if p.suffix.lower() != ".svg" or not p.is_file():
        return False
    head = p.read_bytes()[:4000].decode("utf-8", errors="ignore")
    return "MestReNova" in head or "Mnova" in head
