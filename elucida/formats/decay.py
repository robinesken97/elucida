"""
elucida/formats/decay.py - Abklingkurven (zeitaufgelöste Fluoreszenz) als allgemeine Textdatei: Kopfzeilen werden
übersprungen, Trenner Tab/Semikolon/Komma/Leerzeichen, Dezimalpunkt oder -komma (für die ganze Datei,
`xy.numeric_rows`). Erste Spalte Zeit, zweite Intensität (Zählrate); Zeiteinheit nur aus der Zeitspalte des
Spaltenkopfs (Zeilen mit leerem erstem Feld darunter übersprungen). Ein Herstellerformat (PicoQuant .phd, Edinburgh .fls, Horiba DAS) liest dieser Leser nicht: es lag keine
echte Beispieldatei vor (Regel: unbekannte Varianten ablehnen statt raten).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from elucida.app.i18n import T
from elucida.formats.xy import lead_sep, numeric_rows

MIN_POINTS = 10
TIME_UNITS = {"ps": 1e-3, "ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}   # Faktor nach ns
_UNIT_RE = re.compile(r"(?<![A-Za-z])(ps|ns|µs|μs|us|ms|s)(?![A-Za-z])")


def read_decay(path) -> dict:
    """-> dict(t, y, ncols, unit): t in der Einheit der Datei (unit aus dem Kopf, sonst None), y die zweite Spalte.
    Abgelehnt: keine Zahlenzeilen, weniger als MIN_POINTS Punkte, Zeit nicht streng aufsteigend, Zahlenzeilen mit
    anderem Format, anderer Spaltenzahl oder nicht endlichen Werten (mit Zeilennummer)."""
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16", errors="replace")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:                       # Windows-Export (cp1252): „µs“ ist dort das Byte 0xB5
            text = raw.decode("cp1252", errors="replace")
    found = numeric_rows(text)                           # Dezimalzeichen dateiweit (wie xy), sonst ValueError
    if not found:
        raise ValueError(T("fluo_tau_read_none"))
    n = len(found[0][1])
    for k, v in found:                                   # nie still Zeilen verwerfen: alle gleich breit und endlich
        if len(v) != n or not all(np.isfinite(v)):
            raise ValueError(T("fixr_decay_row", line=k, n=n))
    if len(found) < MIN_POINTS:
        raise ValueError(T("fluo_tau_read_short", n=len(found), m=MIN_POINTS))
    a = np.array([v for _, v in found], float)
    t, y = a[:, 0], a[:, 1]
    if not np.all(np.diff(t) > 0):
        raise ValueError(T("fluo_tau_read_order"))
    unit = None
    lines = text.splitlines()
    lead = lead_sep(lines[found[0][0] - 1])               # Datenzeilen beginnen selbst mit einem Trenner
    for ln in reversed([ln for ln in lines[:found[0][0] - 1] if ln.strip()]):
        # nur die Zeitspalte des Spaltenkopfs: Zeilen mit leerem erstem Feld darunter (Probennamen, Index der Z-Achse)
        # überspringen, danach Schluss – nie aus Metadaten darüber („Resolution [ns],0.1“ über „Time,Counts“)
        cols = [c for i, c in enumerate(re.split(r"\t|;|,|\s{2,}", ln.strip(" ")))
                if c.strip() or (i == 0 and not lead)]
        cols = cols if len(cols) >= 2 else ln.split()
        if not cols or not cols[0].strip():
            continue
        m = _UNIT_RE.search(cols[0])
        if m:
            unit = {"µs": "us", "μs": "us"}.get(m.group(1), m.group(1))
        break
    return {"t": t, "y": y, "ncols": n, "unit": unit}
