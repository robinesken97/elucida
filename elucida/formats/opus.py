"""
elucida/formats/opus.py - Bruker OPUS: Spektrum aus der Binärdatei (Blockverzeichnis, T als Anteil -> %), Peakwerte aus dem OPUS-PDF.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path
import numpy as np

from elucida.app.i18n import T


def _opus_params(b, off, ln):
    out, p = {}, off
    while p < off + 4 * ln and p + 8 <= len(b):
        name = b[p:p + 3].decode("latin-1")
        typ, size = struct.unpack_from("<hh", b, p + 4)
        if name == "END":
            break
        raw = b[p + 8:p + 8 + 2 * size]
        try:
            if typ == 0:
                out[name] = struct.unpack_from("<i", raw)[0]
            elif typ == 1:
                out[name] = struct.unpack_from("<d", raw)[0]
            else:
                out[name] = raw.split(b"\0")[0].decode("latin-1")
        except struct.error:
            pass
        p += 8 + 2 * size
    return out


def read_opus(path) -> dict:
    """Bruker OPUS -> dict(wn, y, kind 'T'|'A', name). Nimmt das prozessierte Spektrum (Transmission oder Absorbanz
    mit eigenem Parameterblock, x in cm⁻¹); Einkanal-/Interferogramm-Dateien werden abgelehnt."""
    b = Path(path).read_bytes()
    if b[:4] != b"\x0a\x0a\xfe\xfe":
        raise ValueError(f"{Path(path).name}: keine OPUS-Datei")
    n = struct.unpack_from("<i", b, 20)[0]
    blocks = [struct.unpack_from("<BBBBii", b, 24 + 12 * i) for i in range(n)]
    blocks = [((t0, t1, t2, t3), ln, off) for t0, t1, t2, t3, ln, off in blocks]
    params = {}
    for t, ln, off in blocks:                       # Parameterblöcke der Daten: Typ mit 2. Byte = 20 (Datenpar.)
        pr = _opus_params(b, off, ln) if t[0] in (31, 23, 27) or t[0] == 15 and t[1] == 0 else {}
        if "NPT" in pr and "FXV" in pr:
            params[t] = pr
    # bevorzugt: Transmission (Typ 15/20) bzw. Absorbanz, mit gleicher Kennung im Parameterblock (31,20,…)
    cands = []
    for t, ln, off in blocks:
        if t[0] in (15, 7, 11) and t[1] in (20, 16) and ln > 100:     # nur TR/AB (4 = Einkanal)
            key = (31, t[1], t[2], t[3])
            pr = params.get(key) or params.get((23, t[1], t[2], t[3])) or params.get((27, t[1], t[2], t[3]))
            if pr and pr.get("DXU", "WN") == "WN":       # x-Achse in cm⁻¹ (nicht µm/nm)
                cands.append((t, ln, off, pr))
    if not cands:
        raise ValueError(f"{Path(path).name}: kein Transmissions- oder Absorbanzspektrum (cm⁻¹) gefunden")
    cands.sort(key=lambda c: (c[0][1] not in (20, 16), c[0][1] != 20, c[0][2] != 0))   # erst T, dann A
    t, ln, off, pr = cands[0]
    npt = int(pr["NPT"])
    y = np.frombuffer(b, dtype="<f4", count=npt, offset=off).astype(float) * float(pr.get("CSF", 1.0))
    wn = np.linspace(pr["FXV"], pr["LXV"], npt)
    # 2. Kennbyte 20 = Transmission (OPUS speichert sie als Anteil 0–1), 16 = Absorbanz
    kind = "A" if t[1] == 16 else "T"
    if kind == "T":                                  # Anteil (0–1) oder %: fast alle Werte ≤ 1.5 bzw. fast alle darüber
        hi_ = float(np.nanmean(y > 1.5))
        if hi_ <= 0.05:
            y = y * 100.0                            # in % wie im OPUS-Ausdruck
        elif hi_ < 0.95:
            raise ValueError(f"{Path(path).name}: Einheit der Transmission unklar (Anteil oder %)")
    out = {"wn": wn, "y": y, "kind": kind, "name": Path(path).stem}
    # Verlauf: letzte Basislinienkorrektur in OPUS (z. B. „Baseline (["::this::":TR], {BME=3, BCO=0, BPO=128, BIO=50})“)
    hist = re.findall(rb"Baseline \(\[[^\]]*\], \{([^}]*)\}\)", b)
    if hist:
        out["baseline"] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", hist[-1].decode("latin-1"))}
    return out


def is_opus(path) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x0a\x0a\xfe\xfe"
    except OSError:
        return False


def read_ir_pdf(path) -> list[float]:
    """OPUS-PDF-Ausdruck -> Peaklagen [cm⁻¹] aus den Textbeschriftungen. Achsenwerte (runde Hunderter/Prozente)
    werden verworfen; Peakwerte tragen in OPUS Nachkommastellen."""
    import pymupdf
    vals = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            for w in page.get_text("words"):
                s = w[4].replace(",", ".")
                if re.fullmatch(r"\d{3,4}\.\d{1,3}", s):
                    v = float(s)
                    if 350 <= v <= 8000:
                        vals.append(v)
    return sorted(set(vals), reverse=True)


def _ticks(words, axis):
    """Achsenbeschriftung: größte Gruppe von Zahlen (x ganzzahlig, y auch mit Dezimalstellen) auf einer Linie (x-Achse: gleiche Höhe, y: gleiche
    Spalte) -> [(Wert, Pixel)] nach Pixel."""
    groups = {}
    num = r"\d{1,4}" if axis == "x" else r"-?\d{1,4}(\.\d{1,3})?"   # y auch 0.0, 0.2 … (Absorbanz)
    for w in words:
        if re.fullmatch(num, w[4]):
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
            line, pos = (cy, cx) if axis == "x" else (w[2], cy)       # y-Achse: rechtsbündige Spalte
            groups.setdefault(round(line), []).append((float(w[4]), pos))
    best = max(groups.values(), key=len, default=[])
    return sorted(best, key=lambda t: t[1])


def _piecewise(px, tp, tv):
    """Pixel -> Wert stückweise linear zwischen den Ticks, außerhalb mit dem Randabschnitt verlängert."""
    v = np.interp(px, tp, tv)
    lo, hi = px < tp[0], px > tp[-1]
    v[lo] = tv[0] + (px[lo] - tp[0]) * (tv[1] - tv[0]) / (tp[1] - tp[0])
    v[hi] = tv[-1] + (px[hi] - tp[-1]) * (tv[-1] - tv[-2]) / (tp[-1] - tp[-2])
    return v


def read_ir_pdf_curve(path) -> dict:
    """OPUS-PDF ohne Messdatei -> Spektrum wie read_opus (wn, y, kind, name). Kurve = Linienzüge mit ≥ 50 Segmenten,
    x über die Wellenzahl-Ticks stückweise linear (OPUS staucht die Achse über 2000 cm⁻¹), y linear über die
    %T- bzw. Absorbanz-Ticks. Unbekanntes Layout -> ValueError (nicht raten)."""
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        pages = [(pg.get_text("words"), pg.get_drawings()) for pg in doc]
    pages = [(w, d) for w, d in pages if any(len(d_["items"]) >= 50 for d_ in d)]
    if len(pages) != 1:
        raise ValueError(T("ir_pdf_layout"))
    words, drawings = pages[0]
    text = " ".join(w[4] for w in words)
    kind = "T" if "Transmittance" in text else "A" if "Absorbance" in text else None
    xt, yt = _ticks(words, "x"), _ticks(words, "y")
    if kind is None or "Wavenumber" not in text or len(xt) < 3 or len(yt) < 3:
        raise ValueError(T("ir_pdf_layout"))
    xp, xv = np.array([t[1] for t in xt]), np.array([t[0] for t in xt])
    yp, yv = np.array([t[1] for t in yt]), np.array([t[0] for t in yt])
    fit = np.polyfit(yp, yv, 1)
    if (np.any(np.diff(xp) <= 0) or np.any(np.diff(xv) >= 0) or fit[0] >= 0
            or np.abs(np.polyval(fit, yp) - yv).max() > 0.01 * np.ptp(yv)):   # Wellenzahl fällt nach rechts, y linear
        raise ValueError(T("ir_pdf_layout"))
    pts = np.array([(p.x, p.y) for d in drawings if len(d["items"]) >= 50 and all(it[0] == "l" for it in d["items"])
                    for it in d["items"] for p in it[1:3]])
    if len(pts) < 100:
        raise ValueError(T("ir_pdf_layout"))
    wn, y = _piecewise(pts[:, 0], xp, xv), np.polyval(fit, pts[:, 1])
    wn, i = np.unique(wn, return_index=True)
    return {"wn": wn[::-1], "y": y[i][::-1], "kind": kind, "name": Path(path).stem, "from_pdf": True}
