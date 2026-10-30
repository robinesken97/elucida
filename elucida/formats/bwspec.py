"""
elucida/formats/bwspec.py - Spektren aus BWSpec (B&W Tek, SEC): Wellenlänge aus coefs_a0…a3, Zeitstempel je Spektrum.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import numpy as np


def read_bwspec(path) -> dict:
    """BWSpec-Textexport (B&W Tek, z. B. BRC115P) -> dict(time, lam, A, name).
    Die Wellenlängenspalte ist oft leer: λ aus Pixel über coefs_a0…a3 (Kalibrierpolynom)."""
    hdr, cols, rows = {}, None, []
    with open(path, encoding="latin-1", errors="replace") as fh:
        for ln in fh:
            ln = ln.rstrip("\r\n")
            if cols is None:
                if ln.startswith("Pixel;"):
                    cols = [c.strip() for c in ln.split(";")]
                    continue
                k, _, v = ln.partition(";")
                hdr[k.strip()] = v.strip()
            elif ln:
                rows.append(ln.split(";"))
    if cols is None or "Absorbance #1" not in cols:
        raise ValueError(f"{Path(path).name}: kein BWSpec-Spektrum mit Absorbanz")
    ia, iw = cols.index("Absorbance #1"), cols.index("Wavelength") if "Wavelength" in cols else None
    pix = np.array([float(r[0]) for r in rows if len(r) > ia])
    A = np.array([float(r[ia]) for r in rows if len(r) > ia])
    lam = None
    if iw is not None:
        try:
            lam = np.array([float(r[iw]) for r in rows if len(r) > ia])
        except ValueError:
            lam = None
    if lam is None:
        a = [float(hdr.get(f"coefs_a{i}", 0) or 0) for i in range(4)]
        lam = a[0] + a[1] * pix + a[2] * pix ** 2 + a[3] * pix ** 3
    if not np.all(np.isfinite(lam)) or np.ptp(lam) <= 0:   # ohne (vollständige) Kalibrierung keine λ-Achse
        raise ValueError(f"{Path(path).name}: keine Wellenlängen und keine Kalibrierung (coefs_a0…a3)")
    lo = int(float(hdr.get("sel_pixel_start", 0) or 0))         # vom Gerät gewählter gültiger Bereich
    keep = pix >= lo
    o = np.argsort(lam[keep])
    try:
        t = dt.datetime.strptime(hdr.get("Date", ""), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        t = None
    return {"time": t, "lam": lam[keep][o], "A": A[keep][o], "name": Path(path).stem}


def is_bwspec(path) -> bool:
    try:
        with open(path, encoding="latin-1", errors="replace") as fh:
            head = fh.read(400)
    except OSError:
        return False
    return head.startswith("File Version;BWSpec") and "Peak Monitor" not in head
