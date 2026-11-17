"""
elucida/formats/bruker_nmr.py - Bruker-NMR-Rohdaten lesen (ohne Qt): acqus/acqu2s/procs/proc2s, fid/ser, 1r/1i/2rr
(Untermatrizen nach XDIM), ppm-Achse aus OFFSET, NOAH-Modul aus dem Audit-Trail. Unbekannte Varianten werden mit
Meldung abgelehnt.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from elucida.app.i18n import T

# Belegt an 201 1D-, 182 TUDO- und 815 öffentlichen 2D-Datensätzen (Audit 1.3.0, Prototyp brk.py):
#   Daten: DTYP 0 = int32, 2 = float64; fid/ser auch big endian (BYTORDA 1, 144 alte 1D), 1r/2rr nur little endian (BYTORDP 1
#   nie gesehen -> abgelehnt); Wert × 2^NC_proc (procs, auch negativ)
#   Achse: ppm(i) = OFFSET − i·SW_p/(SF·SI); 2rr: Untermatrizen XDIM(F2)×XDIM(F1), F1-Block außen, F2-Block innen
#   NOAH-Modul nur aus audita.txt („created by splitx n k. dataset“) + k-tem Buchstaben nach noahN_ (nie EXPNO/Titel)
NOAH_LETTERS = {"S": "HSQC", "B": "HMBC"}             # nur diese beiden an echten Daten geprüft


def read_params(path):
    """Bruker-Parameterdatei (JCAMP) -> dict der Einzelwerte (int/float/str, Schlüssel wie in der Datei); Felder fehlen."""
    out = {}
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = re.match(r"##\$(\w+)=\s*(.*)", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("("):                   # Feld oder Text mit Länge in den Folgezeilen: hier nicht gebraucht
                continue
            if val.startswith("<"):
                out[key] = val.strip("<>")
                continue
            try:
                out[key] = int(val)
            except ValueError:
                try:
                    out[key] = float(val)
                except ValueError:
                    out[key] = val
    return out


def _short(path, n=3):
    return "/".join(Path(path).parts[-n:])


def num(par, key, where):
    """Zahl aus einem Parameter-dict; fehlt sie oder ist sie Text: ValueError mit Meldung (Datei + Parameter)."""
    v = par.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(T("b1nmr_param", key=key, name=where))
    return v


def _dtype(par, dkey, bkey, where, big=False):
    dt, bo = num(par, dkey, where), num(par, bkey, where)
    if dt not in (0, 2):
        raise ValueError(T("b1nmr_dtype", name=where, key=dkey, v=dt))
    if bo not in ((0, 1) if big else (0,)):
        raise ValueError(T("b1nmr_unchecked", name=where, key=bkey, v=bo))
    return np.dtype((">" if bo else "<") + ("i4" if dt == 0 else "f8"))


def acqus(expdir, name="acqus"):
    """acqus/acqu2s eines Experiments; nur acqus.bak (abgebrochene/umkopierte Messung) wird abgelehnt, nie ausgewichen."""
    d = Path(expdir)
    if not (d / name).is_file():
        key = "b1nmr_only_bak" if (d / (name + ".bak")).is_file() else "b1nmr_missing"
        raise ValueError(T(key, name=_short(d, 2), file=name))
    return read_params(d / name)


def procs(pdir, name="procs"):
    d = Path(pdir)
    if not (d / name).is_file():
        raise ValueError(T("b1nmr_missing", name=_short(d, 4), file=name))
    return read_params(d / name)


def _data(path, dtype, where):
    if not Path(path).is_file():
        raise ValueError(T("b1nmr_missing", name=_short(Path(path).parent, 4), file=Path(path).name))
    return np.fromfile(path, dtype=dtype)


def _td(par, where, even=True):
    """TD als positive ganze Zahl (gerade, wenn Re/Im-Paare), sonst Meldung."""
    td = num(par, "TD", where)
    if not isinstance(td, int) or td <= 0 or (even and td % 2):
        raise ValueError(T("b1nmr_td", name=where, v=td))
    return td


def read_fid(expdir):
    """1D-FID -> (komplexe Punkte Re/Im, acqus-dict). Länge TD (Werte) / 2."""
    a = acqus(expdir)
    where = _short(Path(expdir) / "fid")
    td = _td(a, where)
    raw = _data(Path(expdir) / "fid", _dtype(a, "DTYPA", "BYTORDA", where, big=True), where)
    if raw.size < td:
        raise ValueError(T("b1nmr_size", name=where, n=raw.size, m=td))
    raw = raw[:td].astype(float)
    return raw[0::2] + 1j * raw[1::2], a


def read_ser(expdir):
    """2D-ser -> (komplexe Matrix TD(F1) × TD(F2)/2, acqus, acqu2s). Jeder FID in der Datei auf 1024 Byte aufgefüllt.
    NUS (FnTYPE 2) und unaufgeteiltes NOAH (NBL > 1) werden abgelehnt."""
    d = Path(expdir)
    a, a2 = acqus(d), acqus(d, "acqu2s")
    where = _short(d / "ser")
    fnt, nbl = a.get("FnTYPE", 0), a.get("NBL", 1)
    if fnt == 2:
        raise ValueError(T("b1nmr_nus", name=where, file="2rr"))
    if fnt != 0:
        raise ValueError(T("b1nmr_unchecked", name=where, key="FnTYPE", v=fnt))
    if nbl != 1:
        raise ValueError(T("b1nmr_nbl", name=where, n=nbl) if isinstance(nbl, int) and nbl > 1
                         else T("b1nmr_unchecked", name=where, key="NBL", v=nbl))
    dt = _dtype(a, "DTYPA", "BYTORDA", where, big=True)
    td2, td1 = _td(a, where), _td(a2, where, even=False)
    row = -(-td2 * dt.itemsize // 1024) * 1024 // dt.itemsize
    raw = _data(d / "ser", dt, where)
    if raw.size % row or raw.size // row < td1:
        raise ValueError(T("b1nmr_size", name=where, n=raw.size, m=td1 * row))
    raw = raw[: td1 * row].reshape(td1, row)[:, :td2].astype(float)
    return raw[:, 0::2] + 1j * raw[:, 1::2], a, a2


def read_1d(pdir, name="1r"):
    """1r/1i -> (Werte × 2^NC_proc, procs-dict)."""
    p = procs(pdir)
    where = _short(Path(pdir) / name, 5)
    d = _data(Path(pdir) / name, _dtype(p, "DTYPP", "BYTORDP", where), where).astype(float)
    si = num(p, "SI", where)
    if p.get("STSI", si) != si:                       # Strip-FT: kein Satz vorhanden, Länge und Achse ungeprüft
        raise ValueError(T("b1nmr_strip", name=where, v=p.get("STSI"), si=si))
    if d.size != si:
        raise ValueError(T("b1nmr_size", name=where, n=d.size, m=si))
    return d * 2.0 ** num(p, "NC_proc", where), p


def read_2d(pdir, name="2rr"):
    """2rr (auch 2ii …) -> (Matrix SI(F1) × SI(F2) × 2^NC_proc, procs = F2, proc2s = F1); Untermatrizen nach XDIM
    umgeordnet (an 16 echten 2rr mit XDIM < SI belegt)."""
    p2, p1 = procs(pdir), procs(pdir, "proc2s")
    where = _short(Path(pdir) / name, 5)
    si2, si1 = num(p2, "SI", where), num(p1, "SI", where)
    x2, x1 = num(p2, "XDIM", where), num(p1, "XDIM", where)
    d = _data(Path(pdir) / name, _dtype(p2, "DTYPP", "BYTORDP", where), where).astype(float)
    if d.size != si1 * si2:
        raise ValueError(T("b1nmr_size", name=where, n=d.size, m=si1 * si2))
    d *= 2.0 ** num(p2, "NC_proc", where)
    if x2 <= 0 or x1 <= 0 or si2 % x2 or si1 % x1:
        raise ValueError(T("b1nmr_xdim", name=where, si=f"{si2}×{si1}", x=f"{x2}×{x1}"))
    n2, n1 = si2 // x2, si1 // x1
    d = d.reshape(n1, n2, x1, x2).transpose(0, 2, 1, 3).reshape(si1, si2)
    return d, p2, p1


def ppm_axis(p, n=None, name=""):
    """ppm je Punkt aus procs bzw. proc2s (Bruker procref: OFFSET = ppm des ersten Punkts)."""
    for key in ("OFFSET", "SW_p", "SF", "SI"):
        num(p, key, name)
    n = p["SI"] if n is None else n
    return p["OFFSET"] - np.arange(n) * p["SW_p"] / p["SF"] / p["SI"]


def noah_module(expdir):
    """„HSQC“/„HMBC“ für einen aufgeteilten NOAH-Teildatensatz, sonst None (dann allgemeines „2D“, Nutzer
    wählt).
    Nur aus audita.txt (k) und PULPROG (k-ter Buchstabe nach noahN_): EXPNO und Titel sind in echten Daten vertauscht."""
    d = Path(expdir)
    try:
        pp = acqus(d).get("PULPROG", "")
        text = (d / "audita.txt").read_text(encoding="latin-1")
    except (OSError, ValueError):
        return None
    m = re.fullmatch(r"noah(\d+)_([A-Z]+)", str(pp))      # nur Großbuchstaben: Zusätze würden die Zählung verschieben
    k = re.search(r"created by splitx (\d+) (\d+)\. dataset from", text)
    if not m or not k or int(m.group(1)) != len(m.group(2)) or int(k.group(1)) != len(m.group(2)) \
            or not 1 <= int(k.group(2)) <= len(m.group(2)):
        return None
    return NOAH_LETTERS.get(m.group(2)[int(k.group(2)) - 1])


def _write_par(path, par):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    txt = "##TITLE= Parameter file\n" + "".join(f"##${k}= {v}\n" for k, v in par.items()) + "##END=\n"
    Path(path).write_text(txt, encoding="latin-1", newline="")        # wie TopSpin, auch unter Windows


def make_test_1d(d, lines, nucleus="1H", bf1=500.13, o1p=6.0, sw_ppm=20.0, td=65536, si=65536, solvent="CDCl3",
                 phc0=0.0, lb=0.3, grpdly=76.0, seed=7, noise=2e-4, pulprog="zg30", te=298.2, procs_phase=True,
                 extra_acq=None, extra_proc=None):
    """Erfundenes TopSpin-1D-Experiment (acqus, fid, pdata/1/procs + 1r) aus Lorentz-Linien [(δ, Fläche, FWHM Hz)] auf
    der unkalibrierten Achse (SF = BF1). Digitalfilter wie echte Daten (Signal ab GRPDLY, Phase π·GRPDLY), Empfängerphase
    `phc0` (procs PHC0 hebt sie auf; procs_phase=False lässt PHC0/PHC1 weg). Keine Messdaten. -> Experimentordner."""
    from elucida.core import nmr_proc as NP                 # hier, nicht oben: core importiert formats
    d = Path(d)
    sfo1 = bf1 * (1 + o1p * 1e-6)
    sw_h = sw_ppm * bf1
    n = td // 2
    k = np.arange(n) - grpdly
    t = k / sw_h
    rng = np.random.default_rng(seed)
    fid = np.zeros(n, complex)
    for ppm, area, fwhm in lines:
        nu = (ppm - o1p) * bf1                             # Hz relativ zum Träger (höher = größeres δ)
        fid += area * np.exp(2j * np.pi * nu * t - np.pi * fwhm * np.clip(t, 0, None))
    fid[k < 0] = 0
    fid *= np.exp(1j * (np.pi * grpdly + np.deg2rad(phc0)))
    fid += noise * (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * max(a for _, a, _ in lines)
    fid *= 1e6 / max(np.abs(fid).max(), 1e-30)
    acq = dict(TD=td, DTYPA=2, BYTORDA=0, SW_h=sw_h, SW=sw_ppm, SFO1=sfo1, BF1=bf1, O1=o1p * bf1,
               GRPDLY=grpdly, AQ_mod=3, DIGMOD=1, NBL=1, FnTYPE=0, NUC1=f"<{nucleus}>", PULPROG=f"<{pulprog}>",
               SOLVENT=f"<{solvent}>", TE=te, NS=16, DS=2, RG=101)
    acq.update(extra_acq or {})
    # TopSpins eigene Kalibrierung (SF/OFFSET) absichtlich 0.02 ppm daneben: die App nimmt sie nie (SF = BF1)
    sf = bf1 * (1 + 0.02e-6)
    prc = dict(SI=si, TDeff=0, DTYPP=0, BYTORDP=0, NC_proc=0, SF=sf, SW_p=sw_h,
               OFFSET=(sfo1 / sf - 1) * 1e6 + 0.5 * sw_h / sf, WDW=1, LB=lb, PH_mod=1, FT_mod=6, BC_mod=0,
               ME_mod=0, REVERSE="<no>", STSI=si, STSR=0, TDoff=0, ABSG=5)
    _write_par(d / "acqus", acq)
    raw = np.empty(td)
    raw[0::2], raw[1::2] = fid.real, fid.imag
    raw.astype("<f8").tofile(d / "fid")
    pdir = d / "pdata" / "1"
    _write_par(pdir / "procs", dict(prc, PHC0=phc0, PHC1=0.0))       # 1r wie TopSpin mit der richtigen Phase
    s = NP.process_1d(fid, read_params(d / "acqus"), read_params(pdir / "procs"))
    if procs_phase:
        prc.update(PHC0=phc0, PHC1=0.0)
    prc.update(extra_proc or {})
    _write_par(pdir / "procs", prc)
    r = s.real * (2 ** 20 / max(np.abs(s.real).max(), 1e-30))
    r.astype("<i4").tofile(pdir / "1r")
    (-s.imag * (2 ** 20 / max(np.abs(s.real).max(), 1e-30))).astype("<i4").tofile(pdir / "1i")
    return d


def make_test_2d(d, peaks, nuc2="1H", nuc1="13C", bf2=500.13, bf1=125.77, o1p2=5.0, o1p1=80.0, sw2_ppm=10.0,
                 sw1_ppm=160.0, td2=512, td1=64, si2=1024, si1=256, pulprog="hsqcedetgpsisp2.3", grpdly=68.0,
                 solvent="CDCl3", two_rr=False):
    """Erfundenes TopSpin-2D-Experiment (States-TPPI, SINE/QSINE, Phase 0) mit Kreuzsignalen [(δ F2, δ F1, Vorzeichen)]
    auf den unkalibrierten Achsen (SF = BF1); two_rr: dazu pdata/1/2rr aus der eigenen Verarbeitung. Keine Messdaten."""
    from elucida.core import nmr2d as N2                   # hier, nicht oben: core importiert formats
    d = Path(d)
    sfo2, sfo1 = bf2 * (1 + o1p2 * 1e-6), bf1 * (1 + o1p1 * 1e-6)
    sw2, sw1 = sw2_ppm * sfo2, sw1_ppm * sfo1
    n2 = td2 // 2
    k = np.arange(n2) - grpdly
    rows = []
    for j in range(td1 // 2):
        cs = [np.zeros(n2, complex), np.zeros(n2, complex)]
        for d2, d1, sgn in peaks:
            f2 = np.exp(2j * np.pi * (d2 - o1p2) * bf2 / sw2 * k - np.maximum(k, 0) / 30 + 1j * np.pi * grpdly)
            w1 = 2 * np.pi * (d1 - o1p1) * bf1 / sw1 * j
            for c, fn in zip(cs, (np.cos, np.sin)):
                c += sgn * (-1) ** j * fn(w1) * np.exp(-j / 8) * f2
        rows += cs
    rows = np.array(rows) * 1e5
    acq = dict(TD=td2, DTYPA=2, BYTORDA=0, SW_h=sw2, SW=sw2_ppm, SFO1=sfo2, BF1=bf2, GRPDLY=grpdly, NBL=1, FnTYPE=0,
               AQ_mod=3, DIGMOD=1, PULPROG=f"<{pulprog}>", NUC1=f"<{nuc2}>", SOLVENT=f"<{solvent}>", TE=298.2)
    acq2 = dict(TD=td1, FnMODE=5, SW=sw1_ppm, SFO1=sfo1, BF1=bf1, NUC1=f"<{nuc1}>")
    base = dict(WDW=4, SSB=2, LB=0.0, GB=0.0, PH_mod=1, PHC0=0.0, PHC1=0.0, BC_mod=0, ME_mod=0, TDeff=0, TDoff=0, STSR=0,
                REVERSE="<no>", DTYPP=0, BYTORDP=0, NC_proc=0)
    prc = dict(base, SI=si2, XDIM=si2, STSI=si2, FTSIZE=si2, SF=bf2, OFFSET=0.0, SW_p=sw2)
    prc2 = dict(base, SI=si1, XDIM=si1, STSI=si1, FTSIZE=si1, SF=bf1, FCOR=0.5, MC2=4, OFFSET=0.0, SW_p=sw1)
    _write_par(d / "acqus", acq)
    _write_par(d / "acqu2s", acq2)
    pdir = d / "pdata" / "1"
    _write_par(pdir / "procs", prc)
    _write_par(pdir / "proc2s", prc2)
    raw = np.empty((len(rows), td2))
    raw[:, 0::2], raw[:, 1::2] = rows.real, rows.imag
    raw.astype("<f8").tofile(d / "ser")
    if two_rr:
        r = N2.process(d).data
        (r * (2 ** 24 / np.abs(r).max())).astype("<i4").tofile(pdir / "2rr")
    return d
