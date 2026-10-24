"""
elucida/formats/epr.py - CW-EPR-Dateien: Bruker BES3T (.dsc/.DTA, 2D mit .YGF), ASCII (MS400, EasySpin), EasySpin-Parameter.
"""
from __future__ import annotations

import re
from pathlib import Path
import numpy as np


def _dsc(path):
    out = {}
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]{1,15})\s+(.*)$", ln.strip())
        if m and not ln.startswith(("*", "#", ".")):
            out[m.group(1)] = m.group(2).strip().strip("'")
    return out


def _f(h, key, default=None):
    try:
        return float(h[key])
    except (KeyError, ValueError, TypeError):
        return default


def read_bes3t(path) -> list:
    """Bruker BES3T (.DSC/.dsc + .DTA): -> [dict(B [mT], I, meta)], bei 2D je Zeile ein Spektrum.
    Unterstützt: reelle Daten, lineare x-Achse (IDX), D/F/I-Formate, Byte-Reihenfolge LIT/BIG."""
    p = Path(path)
    dsc = next((p.with_suffix(s) for s in (".dsc", ".DSC") if p.with_suffix(s).exists()), None)
    dta = next((p.with_suffix(s) for s in (".DTA", ".dta") if p.with_suffix(s).exists()), None)
    if dsc is None or dta is None:
        raise ValueError(f"{p.name}: .dsc und .DTA werden zusammen gebraucht")
    h = _dsc(dsc)
    if h.get("IKKF", "REAL") != "REAL":
        raise ValueError(f"{p.name}: komplexe Daten werden nicht unterstützt")
    nx, ny = int(_f(h, "XPTS", 0)), int(_f(h, "YPTS", 1) or 1)
    fmt = {"D": "f8", "F": "f4", "I": "i4", "S": "i2"}.get(h.get("IRFMT", "D"), "f8")
    order = "<" if h.get("BSEQ", "BIG") == "LIT" else ">"
    y = np.fromfile(dta, dtype=order + fmt).astype(float)
    if nx <= 1 or len(y) < nx * ny:
        raise ValueError(f"{p.name}: Datengröße passt nicht zur Beschreibung")
    if h.get("XTYP", "IDX") != "IDX":
        raise ValueError(f"{p.name}: nur lineare Feldachsen (XTYP IDX) werden unterstützt")
    B = _f(h, "XMIN", 0.0) + np.arange(nx) * _f(h, "XWID", 1.0) / (nx - 1)
    unit = h.get("XUNI", "G").strip().lower()
    B = B / 10.0 if unit == "g" else (B * 1000.0 if unit == "t" else B)
    yvals = None
    if ny > 1 and h.get("YTYP") == "IGD":
        ygf = next((p.with_suffix(s) for s in (".YGF", ".ygf") if p.with_suffix(s).exists()), None)
        if ygf is not None:
            yvals = np.fromfile(ygf, dtype=order + "f8")
    meta = {"mw_GHz": (_f(h, "MWFQ") or 0) / 1e9 or None, "T_K": _f(h, "STMP"),
            "mod_mT": (_f(h, "B0MA") or 0) * 1000 or None, "power_mW": (_f(h, "MWPW") or 0) * 1000 or None,
            "date": h.get("DATE", ""), "time": h.get("TIME", ""), "title": h.get("TITL", p.stem),
            "device": "Bruker BES3T"}
    out = []
    for k in range(ny):
        m = dict(meta)
        if yvals is not None and k < len(yvals):
            m["y"], m["y_name"], m["y_unit"] = float(yvals[k]), h.get("YNAM", ""), h.get("YUNI", "")
        out.append({"B": B, "I": y[k * nx:(k + 1) * nx], "meta": m})
    return out


def _ascii_xy(path):
    rows = []
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        parts = re.split(r"[\s,;]+", ln.strip().replace("−", "-"))
        try:
            vals = [float(v) for v in parts if v]
        except ValueError:
            continue                                   # Kopfzeile
        if len(vals) >= 2:
            rows.append(vals[:2])
    if len(rows) < 10:
        raise ValueError(f"{Path(path).name}: keine zweispaltigen Daten gefunden")
    a = np.array(rows)
    return a[:, 0], a[:, 1]


def read_ascii(path, unit=None) -> dict:
    """Zweispaltiger Text (MS400-Export, EasySpin-Simulation): B, I. Einheit aus der Kopfzeile ('[mT]', '[G]')
    oder geschätzt (Median > 1500 -> G). Mikrowellenfrequenz aus Dateinamen wie '…-9p404368-…' (GHz)."""
    p = Path(path)
    B, I = _ascii_xy(p)
    head = p.read_text(encoding="latin-1", errors="replace")[:300].lower()
    if unit is None:
        unit = "g" if ("[g]" in head or "(g)" in head) else ("mt" if "mt" in head else
                                                          ("g" if np.median(B) > 1500 else "mt"))
    B = B / 10.0 if unit == "g" else B
    o = np.argsort(B)
    mw = None
    for m in re.finditer(r"(?<![\d.])(\d{1,3})p(\d+)(?![\d])", p.stem):
        v = float(f"{m.group(1)}.{m.group(2)}")
        if 1 <= v <= 100:
            mw = v
            break
    return {"B": B[o], "I": I[o], "meta": {"mw_GHz": mw, "title": p.stem, "device": "ASCII"}}


def read_any(path) -> list:
    p = Path(path)
    if p.suffix.lower() in (".dsc", ".dta"):
        return read_bes3t(p)
    return [read_ascii(p)]


def parse_easyspin(text) -> dict:
    """MATLAB-Zeilen wie 'Sys.D = [1100 160];' -> {'Sys.D': [1100.0, 160.0], …} (nur Zahlen/Vektoren).
    Kommentare (%) werden entfernt; Zeichenketten und Funktionsaufrufe bleiben als Text."""
    out = {}
    for ln in str(text).splitlines():
        ln = ln.split("%")[0].strip().rstrip(";")
        m = re.match(r"^((?:Sys|Exp|Opt|Fit\w*|Vary)\w*\.\w+)\s*=\s*(.+)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val)
        if val.startswith("[") or re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val):
            out[key] = [float(x) for x in nums]
        else:
            out[key] = val
    return out
