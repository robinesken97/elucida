"""
elucida/formats/opus.py - Bruker OPUS: Spektrum aus der Binärdatei (Blockverzeichnis, T als Anteil -> %), Peakwerte aus dem OPUS-PDF.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path
import numpy as np


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
    return {"wn": wn, "y": y, "kind": kind, "name": Path(path).stem}


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
