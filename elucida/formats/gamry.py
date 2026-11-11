"""
elucida/formats/gamry.py - Gamry-Messdateien (.DTA): Kurven (CURVEn oder CURVE + Cycle), Kopfwerte (Vorschub, Fläche, DATE/TIME …).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np


def read_gamry(path) -> dict:
    """Gamry .DTA (Framework 6/7): -> dict(meta, cycles=[dict(E, I, T)]).
    Zwei Varianten: mehrere Tabellen CURVE1, CURVE2, … (je Zyklus) oder eine Tabelle 'CURVE' mit
    Spalte 'Cycle'. Sehr kurze Tabellen (Endpunkt) werden verworfen."""
    lines = Path(path).read_text(encoding="latin-1", errors="replace").splitlines()
    meta = {"scanrate": None, "area": None, "date": "", "time": "", "convention": None}
    tables = []
    i = 0
    while i < len(lines):
        parts = lines[i].split("\t")
        key = parts[0]
        if key == "SCANRATE" and len(parts) > 2:
            meta["scanrate"] = float(parts[2])                 # mV/s
        elif key == "AREA" and len(parts) > 2:
            meta["area"] = float(parts[2])                     # cm²
        elif key == "DATE" and len(parts) > 2:
            meta["date"] = parts[2]
        elif key == "TIME" and len(parts) > 2:
            meta["time"] = parts[2]
        elif key == "CYCLES" and len(parts) > 2:
            meta["n_cycles"] = int(float(parts[2]))
        elif key == "CONVENTION" and len(parts) > 2:
            meta["convention"] = int(float(parts[2]))
        elif key == "IRCOMP" and len(parts) > 2:
            meta["ircomp_on"] = parts[2].strip() not in ("0", "F", "")
        elif key == "PFCOR" and len(parts) > 2:
            meta["pfcor"] = float(parts[2])                    # Positive-Feedback-Widerstand [Ohm]
        elif key == "POSFEEDENABLE" and len(parts) > 2:
            meta["posfeed"] = parts[2].strip() == "T"
        if re.match(r"CURVE\d*$", key) and len(parts) > 1 and parts[1] == "TABLE":
            hdr = lines[i + 1].strip().split("\t")
            i += 3
            rows = []
            while i < len(lines) and lines[i].startswith("\t"):
                rows.append(lines[i].split("\t")[1:])
                i += 1
            tables.append((hdr, rows))
            continue
        i += 1
    cycles = []
    for hdr, rows in tables:
        if len(rows) < 10 or "Vf" not in hdr or "Im" not in hdr:
            continue
        col = {h: k for k, h in enumerate(hdr)}
        arr = np.array([[float(r[col["Vf"]]), float(r[col["Im"]]), float(r[col["T"]]) if "T" in col else np.nan,
                         float(r[col["Cycle"]]) if "Cycle" in col else 0.0] for r in rows if len(r) >= len(hdr) - 1])
        if "Cycle" in col:
            for c in np.unique(arr[:, 3]):
                sel = arr[:, 3] == c
                if sel.sum() >= 10:
                    cycles.append({"E": arr[sel, 0], "I": arr[sel, 1], "T": arr[sel, 2]})
        else:
            cycles.append({"E": arr[:, 0], "I": arr[:, 1], "T": arr[:, 2]})
    if not cycles:
        raise ValueError(f"{Path(path).name}: keine CV-Daten (Gamry .DTA) gefunden")
    # Start innerhalb des Fensters (VINIT zwischen den Grenzen): Gamry schreibt den Rückweg zu VFINAL als eigenes
    # Stück (CURVE{n+1} bzw. Cycle n) – gehört zum letzten Zyklus, sonst fehlt das Ende der Kurve
    n = meta.get("n_cycles")
    if n and len(cycles) == n + 1 and abs(cycles[-1]["E"][0] - cycles[-2]["E"][-1]) < 0.05:
        tail = cycles.pop()
        cycles[-1] = {k: np.concatenate([cycles[-1][k], tail[k]]) for k in ("E", "I", "T")}
    if meta.get("ircomp_on"):                                 # nur zur Dokumentation (Abbildung/CSV)
        meta["ircomp"] = (f"PF {meta['pfcor']:g} Ω" if meta.get("posfeed") and meta.get("pfcor") else "on")
    elif "ircomp_on" in meta:
        meta["ircomp"] = "off"
    return {"meta": meta, "cycles": cycles}
