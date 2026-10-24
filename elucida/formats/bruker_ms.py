"""
elucida/formats/bruker_ms.py - Bruker-MS-Rohdaten (.d, timsTOF): Linienspektren aus analysis.baf/analysis.sqlite, eigene m/z-Kalibrierung (Transformator-Blob, Variante int 10, 112 B; unbekannte Varianten ablehnen).
"""
from __future__ import annotations

import struct
from pathlib import Path
import numpy as np


# Eigener Leser ohne Bruker-Bibliothek, geprüft gegen CompassXport (alle Peaks einer timsTOF-Messung auf 4
# Nachkommastellen identisch). Gelesen werden nur die Linienspektren (Peaklisten des Geräts):
#   analysis.sqlite (Baf2Sql-Schema): Spectra.LineIndexId = Typbyte (oberstes Byte) + Position in analysis.baf
#   Linienblock: Kopf 52 B (Länge, Kennung 0xBFA01002 …), dann n und drei Offsets: f8 Flugzeit-Index, f4 Intensität,
#   f4 Breite. Kalibrierung (Transformators.Blob, ab Byte 4: Delay, Takt, c0, c1, c2, –, c6):
#   t = Delay + Takt·Index;  t = c0 + √(1e12·m'/c1) + c2·m';  m/z = m' − c6.
# Unbekannte Block- oder Kalibrier-Varianten werden abgelehnt statt geraten.
BAF_LINE_MAGIC = 0xBFA01002


BAF_TRANSFORMATOR = (10, 112)                       # (Kennung, Länge) der geprüften Variante


def is_bruker_d(path) -> bool:
    p = Path(path)
    return p.is_dir() and (p / "analysis.baf").exists() and (p / "analysis.sqlite").exists()


def _baf_line(buf, ident):
    off = ident & 0xFFFFFFFFFFFFFF
    size, magic, hlen = struct.unpack_from("<III", buf, off)
    if magic != BAF_LINE_MAGIC or hlen != 52 or off + size > len(buf):
        raise ValueError("unbekanntes Format des Linienspektrums")
    blk = buf[off:off + size]
    n, o1, o2, o3 = struct.unpack_from("<4I", blk, 52)
    if not (52 + o1 + 8 * n <= size and 52 + o2 + 4 * n <= size and 52 + o3 + 4 * n <= size):
        raise ValueError("Linienspektrum unvollständig")
    idx = np.frombuffer(blk, "<f8", count=n, offset=52 + o1)
    inten = np.frombuffer(blk, "<f4", count=n, offset=52 + o2).astype(float)
    return idx, inten


def _baf_mz(idx, blob):
    if (struct.unpack_from("<i", blob, 0)[0], len(blob)) != BAF_TRANSFORMATOR:
        raise ValueError("unbekannte Kalibrier-Variante (Transformator)")
    delay, step, c0, c1, c2, _c5, c6 = struct.unpack_from("<7d", blob, 4)
    if not (step > 0 and c1 > 0):
        raise ValueError("ungültige Kalibrierung")
    t = delay + step * np.asarray(idx, float)
    m = np.maximum((t - c0), 1e-9) ** 2 * c1 / 1e12           # Startwert ohne quadratisches Glied
    for _ in range(30):                                       # Newton für c0 + √(1e12 m/c1) + c2 m = t
        f = c0 + np.sqrt(1e12 * m / c1) + c2 * m - t
        m = m - f / (0.5 * np.sqrt(1e12 / c1 / m) + c2)
    return m - c6


def read_bruker_d(path) -> dict:
    """Bruker-Messordner (.d mit analysis.baf/.sqlite) -> dict(sample, polarity, spectra=[(rt_s, mz, int)])."""
    import sqlite3
    p = Path(path)
    con = sqlite3.connect(f"file:{(p / 'analysis.sqlite').as_posix()}?mode=ro", uri=True)
    try:
        props = dict(con.execute("select Key, Value from Properties").fetchall())
        if props.get("SchemaType") != "Baf2Sql":
            raise ValueError("kein Baf2Sql-Index")
        pol = {r[0]: r[1] for r in con.execute("select Id, Polarity from AcquisitionKeys")}
        rows = con.execute("select Rt, TransformatorId, LineIndexId, AcquisitionKey, "
                           "(select count(*) from Steps where TargetSpectrum = Spectra.Id) from Spectra "
                           "order by Rt").fetchall()
        blobs = dict(con.execute("select Id, Blob from Transformators").fetchall())
    finally:
        con.close()
    buf = (p / "analysis.baf").read_bytes()
    spectra, pols = [], set()
    for rt, tid, lid, key, nsteps in rows:
        if nsteps or not lid:                                 # nur MS1 mit Linienspektrum
            continue
        idx, inten = _baf_line(buf, lid)
        spectra.append((float(rt), _baf_mz(idx, blobs[tid]), inten))
        pols.add(pol.get(key, 0))
    if not spectra:
        raise ValueError("keine MS1-Linienspektren gefunden")
    return {"sample": props.get("SampleName", p.stem), "instrument": (props.get("InstrumentName") or "").strip(),
            "polarity": "-" if pols == {1} else "+", "ionisation": "ESI", "spectra": spectra, "kind": "raw"}
