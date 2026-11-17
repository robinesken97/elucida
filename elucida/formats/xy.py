"""elucida/formats/xy.py - allgemeiner Textleser für zwei Spalten (x, y) ohne Gerätewissen.

Für Raman-Spektren (Raman-Verschiebung, Intensität) und Pulverdiffraktogramme (2θ, Intensität; .xy/.xye, die dritte
Spalte = Fehler wird ignoriert). Kopfzeilen, Kommentare (#, ;, !, ') und Zeilen ohne zwei Zahlen werden übersprungen;
Trenner Leerraum, Tab, Semikolon oder Komma. Dezimalpunkt oder -komma wird für die ganze Datei entschieden
(`numeric_rows`, auch für Abklingkurven): „400,5<Tab>1000“ und „401<Tab>990“ sind dann beide Dezimalkomma; passt kein
Format zu allen Zahlenzeilen, wird abgelehnt (nie je Zeile raten). Ein Gerät-eigenes Binärformat wird nicht geraten:
weniger als MIN_ROWS Zahlenzeilen -> ablehnen.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from elucida.app.i18n import T
from elucida.formats.calc import decode

MIN_ROWS = 10
_SEP_DOT = re.compile(r"[\s;,]+")                         # Dezimalpunkt: Komma darf trennen
_SEP_COMMA = re.compile(r"[\s;]+")                        # Dezimalkomma: Komma trennt nie
_COMMA_NUM = re.compile(r"[+-]?(?:\d+(?:,\d+)?|,\d+)(?:[eE][+-]?\d+)?")
_OVERFLOW = re.compile(r"\*{2,}")                       # Fortran-Überlauf „******“ statt einer Zahl


def _dot(s):
    """Zahlen mit Dezimalpunkt oder None. Trenner einer Zeile alle mit oder alle ohne Komma („1, 100“ ja; „400,5<Tab>1000“
    nein: dort ist das Komma dezimal)."""
    if len({"," in sep for sep in _SEP_DOT.findall(s)}) > 1:
        return None
    try:
        v = [float(t) for t in _SEP_DOT.split(s) if t]
    except ValueError:
        return None
    return v if len(v) >= 2 else None


def _comma(s):
    """Zahlen mit Dezimalkomma oder None (kein Punkt, Komma nur zwischen Ziffern: „1,“ ist kein Dezimalkomma)."""
    tok = [t for t in _SEP_COMMA.split(s) if t]
    if len(tok) < 2 or not all(_COMMA_NUM.fullmatch(t) for t in tok):
        return None
    return [float(t.replace(",", ".")) for t in tok]


def lead_sep(line) -> bool:
    """Erstes Feld leer: Zeile beginnt (nach Leerzeichen) mit Komma, Semikolon oder Tab."""
    return line.lstrip(" ")[:1] in (",", ";", "\t")


def numeric_rows(text) -> list[tuple[int, list[float]]]:
    """[(Zeilennummer ab 1, Zahlen)] aller Zeilen mit mindestens zwei Zahlen; Dezimalzeichen für die ganze Datei. Passt
    weder Punkt noch Komma zu allen diesen Zeilen oder steht in einer Zahlenzeile ein Überlauf „****“: ValueError mit der
    Zeilennummer."""
    cand = []
    for k, line in enumerate(text.splitlines(), 1):
        s = line.strip().rstrip(";,").strip()
        if not s or s[0] in "#;!'\"" or "\0" in s:
            continue
        d, c = _dot(s), _comma(s)
        if not (d or c) and _OVERFLOW.search(s):         # Datenzeile mit Überlauf: nie still weglassen
            z = _OVERFLOW.sub("0", s)
            if _dot(z) or _comma(z):
                raise ValueError(T("fixr_overflow", line=k))
        if d or c:
            cand.append((k, d, c, lead_sep(line)))
    # Zeilen vor dem Datenblock mit leerem erstem Feld, wo die Datenzeilen dort eine Zahl haben (Cary Eclipse: Index der
    # Z-Achse „,1,2“ unter den Probennamen) sind keine Daten. Beginnt jede Zeile mit einem Trenner, bleibt alles.
    if 2 * sum(r[3] for r in cand) < len(cand):
        while cand and cand[0][3]:
            cand.pop(0)
    for i in (1, 2):                                       # passen beide, sind die Werte gleich (keine Kommas)
        if all(r[i] for r in cand):
            return [(r[0], r[i]) for r in cand]
    i = 1 if sum(bool(r[1]) for r in cand) >= sum(bool(r[2]) for r in cand) else 2
    raise ValueError(T("fixr_mixed_decimal", line=next(r[0] for r in cand if not r[i])))


def read_xy(path) -> dict:
    """-> dict(x, y) als Arrays in Dateireihenfolge (erste zwei Zahlenspalten). Unlesbar/zu kurz: ValueError."""
    raw = Path(path).read_bytes()
    if b"\0" in raw[:4096] and raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):   # UTF-16 nur mit BOM
        raise ValueError(T("raman_xy_binary"))
    rows = [v for _, v in numeric_rows(decode(raw))]
    if len(rows) < MIN_ROWS:
        raise ValueError(T("raman_xy_short", n=MIN_ROWS))
    x = np.array([r[0] for r in rows], float)
    y = np.array([r[1] for r in rows], float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < MIN_ROWS:
        raise ValueError(T("raman_xy_short", n=MIN_ROWS))
    return {"x": x[ok], "y": y[ok]}
