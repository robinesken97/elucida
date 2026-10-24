"""
elucida/formats/topspin.py - Bruker TopSpin: JCAMP-Parameter (acqus/acqu2s), Experimentordner finden, Art des Experiments (1D-Kern, DEPT/APT, 2D aus dem Pulsprogramm).
"""
from __future__ import annotations

import re
from pathlib import Path


def parse_nucleus(s):
    """„1H“, „13C“, „¹⁹F“, „H1“ -> „1H“ usw.; None, wenn nicht erkennbar."""
    s = str(s or "").translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")).strip()
    m = re.fullmatch(r"(\d{1,3})\s*([A-Z][a-z]?)", s) or re.fullmatch(r"([A-Z][a-z]?)\s*(\d{1,3})", s)
    if not m:
        return None
    a, b = m.groups()
    return f"{a}{b}" if a.isdigit() else f"{b}{a}"


def read_jcamp_params(path):
    """Bruker acqus/procs (JCAMP-DX): ##$KEY= Wert; Felder „(0..n)“ über die Folgezeilen."""
    out, key, arr = {}, None, None
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        m = re.match(r"##\$?([\w-]+)=\s*(.*)$", ln)
        if m:
            key, val = m.group(1).upper(), m.group(2).strip()
            if re.fullmatch(r"\(\d+\.\.\d+\)", val):
                arr = out[key] = []
            else:
                arr = None
                out[key] = val.strip("<>")
        elif arr is not None and ln.strip() and not ln.startswith("$$"):
            arr += ln.split()
    return out


def bruker_dir(p):
    """Experimentordner (mit acqus) zu einer Auswahl: Ordner, acqus-Datei oder pdata-Unterordner."""
    p = Path(p)
    for c in (p, p.parent, p.parent.parent, p.parent.parent.parent):
        if (c / "acqus").is_file():
            return c
    return None


def acq_params(d):
    """Übersicht aus acqus (und acqu2s bei 2D): Kern, Pulsprogramm, Lösungsmittel, T, SFO1, O1P, SW, NS, TD, D1 …"""
    d = Path(d)
    a = read_jcamp_params(d / "acqus")

    def f(x, default=None):
        try:
            return float(x)
        except (TypeError, ValueError):
            return default
    sfo1 = f(a.get("SFO1"))
    o1 = f(a.get("O1"))
    dvals = a.get("D") if isinstance(a.get("D"), list) else []
    p = dict(nucleus=parse_nucleus(a.get("NUC1")), pulprog=a.get("PULPROG", ""), solvent=a.get("SOLVENT", ""),
             te=f(a.get("TE")), sfo1=sfo1, bf1=f(a.get("BF1")), o1p=o1 / sfo1 if o1 is not None and sfo1 else None,
             sw=f(a.get("SW")), ns=a.get("NS", ""), ds=a.get("DS", ""), td=a.get("TD", ""), rg=a.get("RG", ""),
             d1=f(dvals[1]) if len(dvals) > 1 else None, aq=None, instrument=a.get("INSTRUM", ""),
             probe=a.get("PROBHD", ""), date=a.get("DATE", ""))
    if sfo1 and p["sw"] and f(a.get("TD")):
        p["aq"] = f(a.get("TD")) / 2 / (p["sw"] * sfo1)               # s, komplexe Punkte
    if (d / "acqu2s").is_file():
        b = read_jcamp_params(d / "acqu2s")
        p.update(nucleus2=parse_nucleus(b.get("NUC1")), sfo1_2=f(b.get("SFO1")), sw2=f(b.get("SW")),
                 td2=b.get("TD", ""))
        if p.get("nucleus2") and p["nucleus2"] != p["nucleus"]:
            p["nucleus_f2"], p["nucleus_f1"] = p["nucleus"], p["nucleus2"]
    return p


# Experimentart aus dem Pulsprogramm (Bruker-Namen, klein geschrieben); Reihenfolge: spezifischere zuerst
_PULPROG_2D = (("hsqc", "HSQC"), ("hmqc", "HMQC"), ("hmbc", "HMBC"), ("noesy", "NOESY"), ("roesy", "ROESY"),
               ("hoesy", "HOESY"), ("tocsy", "TOCSY"), ("mlev", "TOCSY"), ("dipsi", "TOCSY"), ("cosy", "COSY"),
               ("inad", "INADEQUATE"))


def experiment_kind(p):
    """Art eines Bruker-Experiments (acq_params): 1D nach Kern („1H“, „13C“, „19F“), DEPT/APT nach Pulsprogramm
    („DEPT135“, „APT“), 2D nach Pulsprogramm („HSQC“, „COSY“ …), unbekanntes 2D = „2D“. Ordnername in data/nmr/."""
    pp = (p.get("pulprog") or "").lower()
    if p.get("nucleus2") is not None or "td2" in p:
        return next((k for key, k in _PULPROG_2D if key in pp), "2D")
    if pp.startswith("dept"):
        m = re.match(r"dept(\d+)", pp)
        return "DEPT" + (m.group(1) if m else "")
    if pp.startswith("jmod") or pp.startswith("apt"):
        return "APT"
    return p.get("nucleus") or "1D"


def experiment_name(d):
    """Zielname eines Experiments im Projekt: <Datensatz>_<Nummer> (TopSpin: Datensatz/10, /11 …), sonst Ordnername."""
    d = Path(d)
    return f"{d.parent.name}_{d.name}" if d.name.isdigit() and d.parent.name else d.name


def find_experiments(root, depth=3):
    """Alle Bruker-Experimentordner (mit acqus) unter einer Auswahl: ein Experiment, ein Datensatz (10, 11, …) oder
    ein Ordner mit mehreren Datensätzen. pdata wird nicht durchsucht. Sortiert nach Datensatz und Nummer."""
    root = Path(root)
    if (root / "acqus").is_file():
        return [root]
    out = []

    def walk(d, k):
        for c in sorted(d.iterdir()) if k > 0 else ():
            if c.is_dir() and c.name != "pdata" and not c.name.startswith("."):
                if (c / "acqus").is_file():
                    out.append(c)
                else:
                    walk(c, k - 1)
    walk(root, depth)
    return sorted(out, key=lambda c: (str(c.parent), int(c.name) if c.name.isdigit() else 10 ** 9, c.name))
