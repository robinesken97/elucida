"""
elucida/formats/gamry_cycling.py - Gamry-Lade/Entlade-Zyklen (PWR800 Cyclic Charge Discharge, H-Zelle).

Hauptdatei (TAG PWR800_CYCLICCHARGEDISCHARGE): Kopf (CAPACITY, CYCLES, Lade-/Entlademodus, Abbruchpotentiale) und
Tabelle CAPACITYCURVE (je Halbzyklus Zeit am Ende, Art 0 = Laden / 1 = Entladen, Zyklus, Ladung in C).
Schrittdateien im Ordner CHARGE_DISCHARGE daneben: CHARGE_#n.DTA / DISCHARGE_#n.DTA (TAG PWR800_CHARGE/_DISCHARGE,
Tabelle CURVE mit T, Vf, Im; STARTTIMEOFFSET = Beginn des Schritts seit Messbeginn). Kopfwerte und Spalten nach Namen;
andere TAGs oder fehlende Tabellen werden abgelehnt (keine Varianten raten).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from elucida.app.i18n import T

MAIN_TAG = "PWR800_CYCLICCHARGEDISCHARGE"
STEP_TAGS = {"PWR800_CHARGE": "charge", "PWR800_DISCHARGE": "discharge"}
STEP_DIR = "CHARGE_DISCHARGE"
STEP_RE = re.compile(r"^(CHARGE|DISCHARGE)_#(\d+)\.DTA$", re.I)
KINDS = {0: "charge", 1: "discharge"}               # Spalte Type der Kapazitätstabelle


def _lines(path):
    return Path(path).read_text(encoding="latin-1", errors="replace").splitlines()


def _tag(lines):
    return next((ln.split("\t")[1].strip() for ln in lines[:10] if ln.startswith("TAG\t")), "")


def _header(lines):
    """Kopfzeilen KEY\\tTYP\\t… -> {KEY: Teile} (erstes Vorkommen gilt)."""
    out = {}
    for ln in lines:
        parts = ln.split("\t")
        if len(parts) > 2 and re.fullmatch(r"[A-Z][A-Z0-9_]*", parts[0]):
            out.setdefault(parts[0], parts)
    return out


def _table(lines, name):
    """Tabelle `name` (Zeile NAME\\tTABLE, Kopf, Einheiten, Datenzeilen mit Tab am Anfang) -> {Spalte: Werte};
    Spalten mit Text (Over) fallen weg. None, wenn es die Tabelle nicht gibt."""
    for i, ln in enumerate(lines):
        parts = ln.split("\t")
        if parts[0] == name and len(parts) > 1 and parts[1] == "TABLE" and i + 2 < len(lines):
            head = lines[i + 1].split("\t")[1:]
            rows = []
            for row in lines[i + 3:]:
                if not row.startswith("\t"):
                    break
                rows.append(row.split("\t")[1:])
            cols = {}
            for k, h in enumerate(head):
                try:
                    cols[h.strip()] = np.array([float(r[k]) for r in rows])
                except (ValueError, IndexError):
                    continue
            return cols
    return None


def _num(h, key, k=2):
    try:
        return float(h[key][k])
    except (KeyError, IndexError, ValueError):
        return None


def _cutoff(h, prefix, sign):
    """Abbruchpotential aus CHARGESTOPATn/DISCHARGESTOPATn mit Bedingung „Voltage > Limit“ bzw. „< Limit“."""
    for n in (1, 2, 3):
        p = h.get(f"{prefix}{n}") or []
        if len(p) > 5 and p[5].strip().startswith(f"Voltage {sign}"):
            return _num(h, f"{prefix}{n}", 3)
    return None


def _current(h, key):
    """Strom [A] eines Schritts, nur bei Konstantstrom („Constant Current“), sonst None."""
    p = h.get(key) or []
    return _num(h, key, 3) if len(p) > 5 and p[5].strip() == "Constant Current" else None


def is_cycling(path) -> bool:
    try:
        return _tag(_lines(path)[:10]) == MAIN_TAG
    except OSError:
        return False


def read_cycling(path) -> dict:
    """Hauptdatei -> dict(meta, halves=[dict(cycle, kind, end_s, charge_C, duration_s)]). ValueError mit
    übersetzter Meldung bei anderem TAG oder ohne Kapazitätstabelle."""
    lines = _lines(path)
    name = Path(path).name
    tag = _tag(lines)
    if tag != MAIN_TAG:
        raise ValueError(T("hcell_bad_tag", f=name, tag=tag or "–"))
    cols = _table(lines, "CAPACITYCURVE")
    need = ("Time", "Type", "Cycle", "Charge")
    if cols is None or any(c not in cols for c in need) or not len(cols["Time"]):
        raise ValueError(T("hcell_no_table", f=name, t="CAPACITYCURVE"))
    if not set(np.unique(cols["Type"]).astype(int)) <= set(KINDS):
        raise ValueError(T("hcell_bad_type", f=name))
    h = _header(lines)
    cap = _num(h, "CAPACITY")
    meta = {"capacity_mAh": cap * 1000.0 if cap else None, "cycles": _num(h, "CYCLES"),
            "charge_A": _current(h, "CHARGEMODE"), "discharge_A": _current(h, "DISCHARGEMODE"),
            "charge_cut_V": _cutoff(h, "CHARGESTOPAT", ">"), "discharge_cut_V": _cutoff(h, "DISCHARGESTOPAT", "<"),
            "date": (h.get("DATE") or ["", "", ""])[2], "time": (h.get("TIME") or ["", "", ""])[2]}
    dur = cols.get("Duration")
    halves = [{"cycle": int(cols["Cycle"][i]), "kind": KINDS[int(cols["Type"][i])], "end_s": float(cols["Time"][i]),
               # Betrag: die Datei führt Ladung in beiden Richtungen positiv; Kapazität ist eine Menge
               "charge_C": abs(float(cols["Charge"][i])),
               "duration_s": float(dur[i]) if dur is not None else None} for i in range(len(cols["Time"]))]
    if len({(h_["cycle"], h_["kind"]) for h_ in halves}) != len(halves):      # Halbzyklus doppelt: unbekannte Variante
        raise ValueError(T("hcell_bad_type", f=name))
    return {"meta": meta, "halves": halves}


def step_files(main_path) -> list:
    """Schrittdateien CHARGE_#n/DISCHARGE_#n.DTA im Ordner CHARGE_DISCHARGE neben der Hauptdatei (andere Dateien dort
    gehören zu anderen Experimenten und bleiben weg), natürlich sortiert."""
    d = Path(main_path).parent / STEP_DIR
    if not d.is_dir():
        return []
    fs = [p for p in d.iterdir() if p.is_file() and STEP_RE.match(p.name)]
    return sorted(fs, key=lambda p: (int(STEP_RE.match(p.name)[2]), p.name.upper().startswith("DIS")))


def step_key(path):
    """Dateiname -> („charge“|„discharge“, Zyklus) oder None."""
    m = STEP_RE.match(Path(path).name)
    return (m[1].lower(), int(m[2])) if m else None


def read_step(path) -> dict:
    """Schrittdatei -> dict(kind, t_s (seit Messbeginn), E (V), I (A)). ValueError bei anderem TAG, ohne Tabelle CURVE
    (Spalten T, Vf) oder ohne STARTTIMEOFFSET (ohne Beginn keine echte Zeitachse)."""
    lines = _lines(path)
    name = Path(path).name
    kind = STEP_TAGS.get(_tag(lines))
    if kind is None:
        raise ValueError(T("hcell_bad_tag", f=name, tag=_tag(lines) or "–"))
    cols = _table(lines, "CURVE")
    if cols is None or "T" not in cols or "Vf" not in cols or not len(cols["T"]):
        raise ValueError(T("hcell_no_table", f=name, t="CURVE"))
    off = _num(_header(lines), "STARTTIMEOFFSET")
    if off is None:
        raise ValueError(T("hcell_no_offset", f=name))
    return {"kind": kind, "t_s": cols["T"] + off, "E": cols["Vf"], "I": cols.get("Im")}
