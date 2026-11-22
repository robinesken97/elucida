"""elucida/core/ocr.py - Texterkennung (RapidOCR, ONNX-Modelle im Paket, Apache-2.0) für PDFs ohne Textebene und Bilder:
Zahlen als Kandidaten zum Anklicken (HRMS: m/z, IR: ṽ). Nichts wird übernommen oder korrigiert; jede Zahl kommt mit
ihrem Bildausschnitt, damit man sie mit dem Original vergleicht. Langsam (~1 s je Seite): nur im Hintergrund aufrufen
(`main.run`), Ergebnis über den Cache des Fensters. rapidocr wird erst hier geladen."""
from __future__ import annotations

import importlib.util
import logging
import re
from pathlib import Path

import numpy as np

DPI = 200                                   # PDF-Seiten für die Erkennung (ganzzahlig: pymupdf unter Windows)
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
CROP_PAD = 4                                # Pixel um das Wort im Ausschnitt
_ENGINE = None


def available() -> bool:
    return importlib.util.find_spec("rapidocr") is not None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from rapidocr import RapidOCR
        _ENGINE = RapidOCR(params={"Global.log_level": "warning"})   # Info-Meldungen (Modellpfade) nicht ausgeben
        logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    return _ENGINE


def page_images(path) -> list[np.ndarray]:
    """Seiten eines PDF (DPI) oder ein Bild -> [RGB-Feld (Höhe, Breite, 3)]."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        import pymupdf
        out = []
        with pymupdf.open(str(p)) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=DPI, alpha=False)
                out.append(np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3].copy())
        return out
    from PIL import Image
    with Image.open(p) as im:
        return [np.asarray(im.convert("RGB")).copy()]


def recognise(path) -> list[dict]:
    """Alle erkannten Wörter -> [dict(text = ganze Zeile, word, number (float oder None), bbox (x0, y0, x1, y1) in
    Pixeln der Seite, page (0-basiert), crop (Bildausschnitt des Worts, nur bei Zahlen))]."""
    eng = _engine()
    out = []
    for pno, img in enumerate(page_images(path)):
        res = eng(img, return_word_box=True)
        for line, words in zip(res.txts or (), res.word_results or ()):
            for word, _score, box in words:
                xs, ys = [q[0] for q in box], [q[1] for q in box]
                bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
                num = float(word) if re.fullmatch(r"\d+(\.\d+)?", word) else None     # nie „reparieren“
                crop = None
                if num is not None:
                    x0, y0 = max(0, bbox[0] - CROP_PAD), max(0, bbox[1] - CROP_PAD)
                    crop = img[y0:bbox[3] + CROP_PAD, x0:bbox[2] + CROP_PAD].copy()
                out.append({"text": line, "word": word, "number": num, "bbox": bbox, "page": pno, "crop": crop})
    return out


def text_items(path) -> list[dict]:
    """Wörter der Textebene eines PDF im Format von `recognise` (Zeile = Textzeile von pymupdf, Ausschnitt gerendert);
    ohne Textebene oder für Bilder -> []."""
    if Path(path).suffix.lower() != ".pdf":
        return []
    import pymupdf
    out = []
    with pymupdf.open(str(path)) as doc:
        for pno, page in enumerate(doc):
            words = page.get_text("words")
            lines = {}
            for w in words:
                lines.setdefault((w[5], w[6]), []).append(w[4])
            for x0, y0, x1, y1, word, blk, ln, _ in words:      # Textebene: Dezimalkomma ist Schreibweise, kein OCR-Fehler
                num = float(word.replace(",", ".")) if re.fullmatch(r"\d+([.,]\d+)?", word) else None
                crop = None
                if num is not None:
                    r = pymupdf.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
                    pix = page.get_pixmap(dpi=DPI, clip=r, alpha=False)
                    crop = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3].copy()
                out.append({"text": " ".join(lines[(blk, ln)]), "word": word, "number": num,
                            "bbox": (x0, y0, x1, y1), "page": pno, "crop": crop})
    return out


def run(path) -> dict:
    """Für den Hintergrund: {"items": recognise(path)} oder {"error": Grund} (rapidocr fehlt, Datei unlesbar)."""
    if not available():
        return {"error": "missing"}
    try:
        return {"items": recognise(path)}
    except Exception as ex:                            # Ergebnis oder Grund, nie ein stiller Abbruch
        return {"error": f"{type(ex).__name__}: {ex}"}


def start(main, path):
    """OCR-Ergebnis einer Datei aus dem Cache des Fensters ({"items"} oder {"error"}); fehlt es, startet die Erkennung
    im Hintergrund (einmal je Datei) und zeichnet danach die Tabs neu, die die Datei zeigen. -> Ergebnis oder None."""
    key = ("ocr", str(path), Path(path).stat().st_mtime)
    c = main.extra_cache
    if key in c:
        return c[key]
    busy = main.__dict__.setdefault("_ocr_busy", set())
    if key not in busy:
        busy.add(key)

        def done(res, key=key):
            busy.discard(key)
            c[key] = res
            for k, attr in (("hrms", "ms_file"), ("irms", "ir_doc")):      # nur gebaute Tabs, die die Datei zeigen
                if main._built(k):
                    tab = getattr(main, main._tab_spec(k)[0])
                    if tab.st.get(attr) == str(path):
                        tab.sync_widgets()
                        tab.render()
        main.run(lambda: run(path), done)
    return None


def candidates(items, pattern, lo, hi, skip_line=None) -> list[tuple]:
    """Zahlen, deren Wort ganz `pattern` entspricht, im Bereich [lo, hi] -> [(Wert, Zeile, Bildausschnitt)], jede einmal
    (erstes Vorkommen); Zeilen, für die skip_line(Zeile) wahr ist (Kopfdaten), fallen weg."""
    out, seen = [], set()
    for it in items:
        if it["number"] is None or not re.fullmatch(pattern, it["word"]):
            continue
        if skip_line is not None and skip_line(it["text"]):
            continue
        v = it["number"]
        if lo <= v <= hi and v not in seen:
            seen.add(v)
            out.append((v, it["text"][:120], it["crop"]))
    return out


def tip_html(crop, line, extra=()) -> str:
    """Tooltip einer Kandidatenzeile: Bildausschnitt der Zahl (zum Vergleich mit dem Original), ganze Zeile der Quelle,
    weitere Hinweise; Rich Text mit eingebettetem PNG."""
    import base64
    import html
    import io
    parts = []
    if crop is not None:
        from PIL import Image
        buf = io.BytesIO()
        Image.fromarray(np.ascontiguousarray(crop[..., :3])).save(buf, "PNG")
        parts.append(f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">')
    parts += [html.escape(x) for x in (line, *extra) if x]
    return "<br>".join(parts)
