"""
elucida/formats/gamry.py - Gamry-Messdateien (.DTA): Kurven (CURVEn oder CURVE + Cycle), Kopfwerte (Vorschub, Fläche, DATE/TIME …).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from elucida.app.i18n import T


PULSE_TAGS = {"DPV": "DPV", "SQUARE_WAVE": "SWV"}      # TAG-Zeile -> Verfahren; andere Pulsdateien: „pulse“
PULSE_KEYS = {"STEPSIZE": "step_mV", "PULSESIZE": "pulse_mV", "PULSEON": "pulse_s", "FREQUENCY": "freq_Hz"}
PULSE_NAMES = {"DPV": "Differential pulse voltammograms", "SWV": "Square-wave voltammograms",
               "pulse": "Pulse voltammograms"}


def make_test_pulse(path, tag="DPV", n=120):
    """Künstliche Gamry-Pulsdatei (Kopf und Tabelle wie eine echte Square-Wave-Datei, Zahlen erfunden): ein Peak im
    Differenzstrom bei −0,25 V. Kein echter Datensatz."""
    E = np.linspace(0.0, -0.5, n)
    idif = 2e-6 * np.exp(-((E + 0.25) / 0.04) ** 2) + 1e-8
    L = ["EXPLAIN", f"TAG\t{tag}", "TITLE\tLABEL\ttest\tTest &Identifier", "DATE\tLABEL\t1/2/2026\tDate",
         "TIME\tLABEL\t12:00:00\tTime", "VINIT\tQUANT\t0.00000E+000\tInitial &E (V)",
         "VFINAL\tQUANT\t-5.00000E-001\tFinal &E (V)", "STEPSIZE\tQUANT\t2.00000E+000\tSt&ep Size (mV)",
         "PULSESIZE\tQUANT\t2.50000E+001\tPulse Size &Epeak (mV)", "PULSEON\tQUANT\t1.00000E-002\tPulse &Time (s)",
         "AREA\tQUANT\t1.00000E+000\tElectrode &Area (cm^2)", "IRCOMP\tSELECTOR\t0\tIRCom&p",
         f"CYCLES\tIQUANT\t{n}\tC&ycles (#)", f"CURVE\tTABLE\t{n}",
         "\tPt\tT\tVfwd\tVrev\tVstep\tIfwd\tIrev\tIdif\tSig\tAch\tIERange\tOver",
         "\t#\ts\tV\tV\tV\tA\tA\tA\tV\tV\t#\tbits"]
    L += [f"\t{k}\t{0.01 * (k + 1):g}\t{e - 0.0125:.5E}\t{e + 0.0125:.5E}\t{e:.5E}\t{i / 2:.5E}\t{-i / 2:.5E}\t{i:.5E}"
          f"\t{e:.5E}\t0.00000E+000\t7\t..........." for k, (e, i) in enumerate(zip(E, idif))]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\r\n".join(L) + "\r\n", encoding="latin-1", newline="")
    return Path(path)


def read_gamry(path) -> dict:
    """Gamry .DTA (Framework 6/7): -> dict(meta, cycles=[dict(E, I, T)]).
    Zwei Varianten: mehrere Tabellen CURVE1, CURVE2, … (je Zyklus) oder eine Tabelle 'CURVE' mit
    Spalte 'Cycle'. Sehr kurze Tabellen (Endpunkt) werden verworfen.
    Pulsverfahren (Nutzerauftrag 2026-11-13, DPV): eine Tabelle, die die Spalten „Vstep“ (Treppenpotential) und „Idif“
    (Differenzstrom) nennt, wird als eine Kurve E = Vstep, I = Idif gelesen; meta["pulse"] = Verfahren aus der
    TAG-Zeile, meta["pulse_par"] = Schrittweite, Pulshöhe, Pulszeit, Frequenz, soweit im Kopf. Geprüft mit einer echten
    Gamry-Square-Wave-Datei (TAG SQUARE_WAVE); eine echte DPV-Datei lag nicht vor – sie wird gelesen, wenn ihre Tabelle
    dieselben Spalten nennt, sonst abgelehnt (nie Spalten nach Position raten)."""
    try:
        return _read_gamry(path)
    except ValueError as e:                               # Dezimalkomma (deutsches Windows), Überlauf: nie roher Text
        if "could not convert" in str(e) or "invalid literal" in str(e):
            raise ValueError(T("r2l_gamry_number", name=Path(path).name)) from None
        raise


def table_rows(lines, i, rows, name):
    """Zeilenzahl aus „CURVE\\tTABLE\\t78“ gegen die gelesenen Zeilen (abgeschnittene Datei nie still kürzer)."""
    parts = lines[i].split("\t")
    if len(parts) > 2 and parts[2].strip().isdigit() and int(parts[2]) != len(rows):
        raise ValueError(T("r2l_gamry_rows", name=name, table=parts[0], n=len(rows), m=int(parts[2])))


def _read_gamry(path) -> dict:
    lines = Path(path).read_text(encoding="latin-1", errors="replace").splitlines()
    meta = {"scanrate": None, "area": None, "date": "", "time": "", "convention": None}
    tables = []
    i = 0
    while i < len(lines):
        parts = lines[i].split("\t")
        key = parts[0]
        if key == "TAG" and len(parts) > 1:
            meta["tag"] = parts[1].strip()
        elif key in PULSE_KEYS and len(parts) > 2:
            try:
                meta.setdefault("pulse_par", {})[PULSE_KEYS[key]] = float(parts[2])
            except ValueError:
                pass
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
            start = i
            i += 3
            rows = []
            while i < len(lines) and lines[i].startswith("\t"):
                rows.append(lines[i].split("\t")[1:])
                i += 1
            table_rows(lines, start, rows, Path(path).name)
            tables.append((hdr, rows))
            continue
        i += 1
    cycles = []
    for hdr, rows in tables:
        if len(rows) >= 10 and "Vstep" in hdr and "Idif" in hdr:      # Pulsverfahren: benannte Spalten
            col = {h: k for k, h in enumerate(hdr)}
            arr = np.array([[float(r[col["Vstep"]]), float(r[col["Idif"]]), float(r[col["T"]]) if "T" in col else np.nan]
                            for r in rows if len(r) > max(col["Vstep"], col["Idif"])])
            cycles.append({"E": arr[:, 0], "I": arr[:, 1], "T": arr[:, 2]})
            meta["pulse"] = PULSE_TAGS.get(meta.get("tag", ""), "pulse")
            meta.pop("n_cycles", None)                    # CYCLES zählt hier die Punkte, nicht die Zyklen
            continue
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
