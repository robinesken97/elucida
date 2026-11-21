"""
elucida/formats/ms_report.py - Bericht der Massenabteilung (.docx): Text, Beschriftungen der EMF-Spektren, ChemDraw-Objekt (CDX).
"""
from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

from elucida.app.i18n import T


def _emf_texts(data: bytes) -> list[str]:
    """Alle EMR_EXTTEXTOUTW-Texte eines EMF (Beschriftungen der Spektren aus der Massenabteilung)."""
    out, p = [], 0
    while p + 8 <= len(data):
        typ, size = struct.unpack_from("<II", data, p)
        if size < 8 or p + size > len(data):
            break
        if typ == 84 and size >= 76:
            n, off = struct.unpack_from("<II", data, p + 44)
            if 0 < n < 4096 and p + off + 2 * n <= len(data):
                out.append(data[p + off:p + off + 2 * n].decode("utf-16-le", "replace"))
        p += size
    return out


def cdx_structure(blob: bytes) -> dict | None:
    """ChemDraw-Objekt (CDX-Binärdaten) -> dict(formula, mw, cdxml) über RDKit; None, wenn nicht lesbar.
    cdxml ist eine RDKit-Umwandlung (Ersatzzeichnung), nicht ChemDraws eigene Darstellung."""
    import tempfile
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
        from elucida.core.chem import mol_weight
        if not Chem.HasChemDrawCDXSupport():
            return None
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "obj.cdx"
            f.write_bytes(blob)
            prm = Chem.CDXMLParserParams()
            prm.format = Chem.CDXMLFormat.CDX
            mols = [m for m in Chem.MolsFromCDXMLFile(str(f), prm) if m is not None]
    except Exception:
        return None
    if not mols:
        return None
    mol = mols[0]
    for m in mols[1:]:
        mol = Chem.CombineMols(mol, m)
    return {"formula": rdMolDescriptors.CalcMolFormula(mol, True, True), "mw": mol_weight(mol),
            "cdxml": Chem.MolToCDXMLBlock(mol) if hasattr(Chem, "MolToCDXMLBlock") else None,   # ältere RDKit
            "n_fragments": len(mols)}


def _docx_cdx(z: zipfile.ZipFile) -> bytes | None:
    """Erstes eingebettetes ChemDraw-Objekt (OLE-Container mit Stream CONTENTS = CDX) eines docx."""
    import io
    try:
        import olefile
    except ImportError:
        return None
    for n in z.namelist():
        if n.startswith("word/embeddings/") and n.lower().endswith(".bin"):
            try:
                ole = olefile.OleFileIO(io.BytesIO(z.read(n)))
                if ole.exists("CONTENTS"):
                    data = ole.openstream("CONTENTS").read()
                    if data[:8] == b"VjCD0100":
                        return data
            except Exception:
                continue
    return None


CHECKED = "☒☑✓✔✗✘"                                   # angekreuzte Kästchen im Formular


def read_ms_docx(path) -> dict:
    """Auftragsformular (docx) -> dict(sample, formula, exact_mass, ionisation, polarity, mz [found], remark,
    structure = Formel/Molmasse aus dem eingebetteten ChemDraw-Objekt oder None)."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
            emf = [z.read(n) for n in z.namelist() if n.startswith("word/media/") and n.lower().endswith(".emf")]
            cdx = _docx_cdx(z)
    except (zipfile.BadZipFile, KeyError):                   # kein/kaputtes Word-Dokument: nie roher Text
        raise ValueError(T("r2l_docx_bad", name=Path(path).name)) from None
    xml = re.sub(r"<w:del(?:\s[^>]*)?(?<!/)>.*?</w:del>", "", xml, flags=re.S)   # Löschungen (nicht <w:del/>)
    paras = [re.sub(r"<[^>]+>", "", p) for p in xml.split("</w:p>")]
    paras = [re.sub(r"\s+", " ", p.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")).strip()
             for p in paras]
    paras = [p for p in paras if p]

    def field(key):
        for i, p in enumerate(paras):
            if p.lower().startswith(key):
                rest = p[len(key):].strip(" :")
                return rest or (paras[i + 1] if i + 1 < len(paras) else "")
        return ""
    ionisation = ""
    for p in paras:
        if p.lower().startswith("method of ionisation") or "ESI" in p and re.search(f"[{CHECKED}]", p):
            m = re.search(rf"(ESI|APCI|HESI|EI|MALDI)\s*[{CHECKED}]", p)
            if m:
                ionisation = m.group(1)
                break
    texts, mz, polarity = [], [], ""
    for blob in emf:
        tt = _emf_texts(blob)
        texts.append(tt)
        if "m/z" not in tt:                          # nur Spektren, nicht das Formelbild (exakte Masse, Molmasse)
            continue
        for t in tt:
            if re.search(r"\+MS", t):
                polarity = "+"
            elif re.search(r"(?<![A-Za-z])-MS", t):          # nicht „HR-MS“
                polarity = polarity or "-"
            s = t.strip().replace(",", ".")
            if re.fullmatch(r"\d{2,5}\.\d{3,5}", s):
                mz.append(float(s))
        # Formelbild (ChemDraw im Formular): „C | 31 | H | 21 | N | 3“ -> Formel
    formula = re.sub(r"\s", "", field("molecular formula"))
    if not formula:
        for tt in texts:
            j = " ".join(tt)
            m = re.search(r"Formula:\s*((?:[A-Z][a-z]?\s*\d*\s*)+)", j)
            if m:
                formula = re.sub(r"\s", "", m.group(1))
                break
    exact = field("exact mass").replace(",", ".")
    struct_ = cdx_structure(cdx) if cdx else None
    return {"sample": field("sample name"), "formula": formula, "structure": struct_,
            "exact_mass": float(exact) if re.fullmatch(r"\d+(\.\d+)?", exact) else None,
            "ionisation": ionisation or "ESI", "polarity": polarity or "+",
            "mz": sorted(set(mz)), "remark": field("magnification") or field("remarks")}


# ---------------------------------------------------------------------------- PDF (Entscheidungen 171/172)
# Bekanntes Layout: Bruker Compass DataAnalysis „Compound Spectrum SmartFormula Report“ (Textebene, Spektren als
# Rasterbilder). Gelesen werden nur die Tabelle (Meas. m/z, Ion Formula, m/z, err [ppm]) und zwei Messangaben
# (Ion Polarity, Source Type) als Werte aus einer festen Liste; Kopfdaten (Pfad, Probe, Bearbeiter) nie.
SF_TITLE = "Compound Spectrum SmartFormula Report"
SF_MEAS, SF_FORMULA, SF_CALC, SF_ERR = "Meas. m/z", "Ion Formula", "m/z", "err [ppm]"
IONISATIONS = ("ESI", "APCI", "HESI", "APPI", "MALDI", "EI")
POLARITIES = {"Positive": "+", "Negative": "-"}
# Zeilen mit diesen Wörtern (oder einem Pfad) stellen in unbekannten PDFs nie Kandidaten: Kopfdaten (Probe, Name,
# Bearbeiter, Pfad, Datum) dürfen nicht angezeigt werden
HEADER_WORDS = re.compile(r"sample|name|operator|user|printed|analy[sz]|comment|method|file|path|date|time|by:|"
                          r"instrument|acquisition|position|vial|tray|submit|customer|group|account|mail|page", re.I)
MZ_NUM = re.compile(r"(?<![\d.])(\d{2,4}\.\d{3,6})(?![\d.])")     # m/z mit mindestens drei Nachkommastellen
_SF_ION = re.compile(r"(?:[A-Z][a-z]?\d*)+[+-]?")
PDF_IMG_MIN_PX = 100                    # kleinere Bilder (Logos) werden nicht angeboten
PDF_IMG_MAX_PAGE = 0.5                  # Bilder über die halbe Seite (Scans ganzer Seiten mit Kopf) nie


def _pdf_lines(doc):
    """Textzeilen aller Seiten -> [(Seite, y-Mitte, [(x0, x1, Text) nach x])]; Spans mit gleicher Mitte (± 2.5 pt)."""
    out = []
    for pno, page in enumerate(doc):
        spans = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", ()):
                for s in ln["spans"]:
                    t = s["text"].strip()
                    if t:
                        x0, y0, x1, y1 = s["bbox"]
                        spans.append(((y0 + y1) / 2, x0, x1, t))
        rows = []
        for yc, x0, x1, t in sorted(spans):
            if rows and yc - rows[-1][0] <= 2.5:
                rows[-1][1].append((x0, x1, t))
            else:
                rows.append([yc, [(x0, x1, t)]])
        out += [(pno, yc, sorted(sp)) for yc, sp in rows]
    return out


def _right_of(lines, label, allowed):
    """Wert rechts neben einer Beschriftung derselben Zeile, nur aus `allowed` (sonst None)."""
    for _, _, sp in lines:
        for x0, x1, t in sp:
            if t == label:
                right = [s for s in sp if s[0] > x1]
                v = min(right)[2] if right else ""
                return v if v in allowed else None
    return None


def _smartformula_rows(lines):
    """Zeilen aller SmartFormula-Tabellen -> [dict(meas, formula, calc, err)]; None, wenn kein Tabellenkopf da ist.
    Jede Zeile wird geprüft (Zahl, Ionenformel, Zahl); die erste, die nicht passt, beendet die Tabelle."""
    rows, head = [], False
    for i, (pno, _, sp) in enumerate(lines):
        texts = [t for _, _, t in sp]
        if SF_MEAS not in texts or SF_FORMULA not in texts:
            continue
        head = True
        cols = {t: (x0 + x1) / 2 for x0, x1, t in sp}
        for pno2, _, sp2 in lines[i + 1:]:
            if pno2 != pno:
                break
            cells = {}
            for x0, x1, t in sp2:
                c = min(cols, key=lambda k: abs(cols[k] - (x0 + x1) / 2))
                cells[c] = (cells.get(c, "") + " " + t).strip()
            meas, ion_f = cells.get(SF_MEAS, ""), cells.get(SF_FORMULA, "")
            calc, err = cells.get(SF_CALC, ""), cells.get(SF_ERR, "")
            if not (re.fullmatch(r"\d+\.\d+", meas) and _SF_ION.fullmatch(ion_f)
                    and (not calc or re.fullmatch(r"\d+\.\d+", calc))
                    and (not err or re.fullmatch(r"[-−+]?\d+(\.\d+)?", err))):
                break
            rows.append({"meas": float(meas), "formula": ion_f, "calc": float(calc) if calc else None,
                         "err": float(err.replace("−", "-")) if err else None})
    return rows if head else None


def _pdf_candidates(lines):
    """Unbekanntes Layout: [(m/z, Textzeile)] aller Zahlen mit ≥ 3 Nachkommastellen zwischen 50 und 5000, ohne
    Zeilen, die nach Kopfdaten aussehen (HEADER_WORDS, Pfade); jede Zahl einmal (erste Zeile)."""
    out, seen = [], set()
    for _, _, sp in lines:
        line = " ".join(t for _, _, t in sp)
        if HEADER_WORDS.search(line) or "\\" in line or ":/" in line:
            continue
        for m in MZ_NUM.finditer(line):
            v = float(m.group(1))
            if 50 <= v <= 5000 and v not in seen:
                seen.add(v)
                out.append((v, line[:120]))
    return out


def _pdf_images(doc):
    """Eingebettete Bilder zur Auswahl -> [dict(page, xref, w, h, w_cm, h_cm)]: keine Logos (< PDF_IMG_MIN_PX), nie ganze
    Seiten (> PDF_IMG_MAX_PAGE der Seitenfläche: gescannte Seiten tragen den Kopf mit Namen)."""
    out, seen = [], set()
    for pno, page in enumerate(doc):
        area = page.rect.width * page.rect.height
        for img in page.get_images(full=True):
            xref, w, h = img[0], img[2], img[3]
            if xref in seen or w < PDF_IMG_MIN_PX or h < 40:
                continue
            rects = page.get_image_rects(xref)
            if not rects or any(r.width * r.height > PDF_IMG_MAX_PAGE * area for r in rects):
                continue
            seen.add(xref)
            out.append({"page": pno + 1, "xref": xref, "w": w, "h": h,
                        "w_cm": rects[0].width / 72 * 2.54, "h_cm": rects[0].height / 72 * 2.54})
    return out


def read_ms_pdf(path) -> dict:
    """MS-Bericht als PDF -> dict wie `read_ms_docx` (ohne Probe/Formel/Struktur) + kind ("smartformula": Tabelle des
    bekannten Layouts in `rows`, found-Werte in `mz`; "text": unbekanntes Layout, Zahlen nur als `candidates`, nichts
    vorgewählt), `images` (eingebettete Bilder zur Auswahl). Ohne Textebene: ValueError (OCR folgt als zweite Stufe)."""
    import pymupdf
    try:
        doc = pymupdf.open(str(path))
    except Exception:
        raise ValueError(T("ms_pdf_bad", name=Path(path).name)) from None
    with doc:
        if not doc.is_pdf:
            raise ValueError(T("ms_pdf_bad", name=Path(path).name))
        lines = _pdf_lines(doc)
        images = _pdf_images(doc)
    if not lines:
        raise ValueError(T("ms_pdf_no_text", name=Path(path).name))
    out = {"sample": "", "formula": "", "structure": None, "exact_mass": None, "remark": "", "images": images,
           "rows": [], "candidates": [], "mz": []}
    rows = _smartformula_rows(lines) if any(t == SF_TITLE for _, _, sp in lines for _, _, t in sp) else None
    if rows:
        out.update(kind="smartformula", rows=rows, mz=sorted({r["meas"] for r in rows}),
                   ionisation=_right_of(lines, "Source Type", IONISATIONS),
                   polarity=POLARITIES.get(_right_of(lines, "Ion Polarity", tuple(POLARITIES)) or ""))
        return out
    body = " ".join(" ".join(t for _, _, t in sp) for _, _, sp in lines
                    if not HEADER_WORDS.search(" ".join(t for _, _, t in sp)))
    ion = {m for m in IONISATIONS if re.search(rf"(?<![A-Za-z]){m}(?![A-Za-z])", body)}
    out.update(kind="text", candidates=_pdf_candidates(lines), polarity=None,
               ionisation=ion.pop() if len(ion) == 1 else None)
    return out


def _pdf_pixmap(doc, xref):
    import pymupdf
    pix = pymupdf.Pixmap(doc, int(xref))
    cs = pix.colorspace
    return pymupdf.Pixmap(pymupdf.csRGB, pix) if cs is not None and cs.n != 3 else pix    # CMYK/Grau -> RGB


def pdf_image_png(path, xref, dst) -> Path:
    """Eingebettetes Bild (xref) unverändert als PNG speichern."""
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        _pdf_pixmap(doc, xref).save(str(dst))
    return Path(dst)


def pdf_image_array(path, xref):
    """Eingebettetes Bild (xref) als Pixelfeld (Höhe, Breite, Kanäle) für die Vorschau."""
    import numpy as np
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        pix = _pdf_pixmap(doc, xref)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n).copy()
    return arr


def read_ms_report(path) -> dict:
    """Bericht der Massenabteilung: .pdf über `read_ms_pdf`, sonst Word (`read_ms_docx`)."""
    return read_ms_pdf(path) if Path(path).suffix.lower() == ".pdf" else read_ms_docx(path)
