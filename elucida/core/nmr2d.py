"""
elucida/core/nmr2d.py - 2D-NMR aus dem Bruker-ser rechnen (ohne Qt): F2 wie 1D (core.nmr_proc), F1 je FnMODE (QF, TPPI,
States-TPPI, Echo-Antiecho), Fenster SINE/QSINE, Nullauffüllung auf SI, Phase/Betrag, Achsen aus den
Akquisitionsparametern; unaufgeteilte NOAH-Sätze (noah2_SB/BS) aufteilen. Nur an echten Daten belegte Klassen
(`nmr_proc.blockers`), sonst Meldung: dann darf nur TopSpins 2rr gezeigt werden.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import numpy as np

from elucida.app.i18n import T
from elucida.core import nmr_proc as NP
from elucida.formats import bruker_nmr as BN

# Belegt (Audit 1.3.0, nmr13/2d/BERICHT.md, Prototyp proc2d.py + conv.json; 314 Sätze eigene FT aus ser gegen 2rr):
#   F2 = 1D-Konvention (bitgleich zu brk.process_1d). F1: Fenster über die gemessenen t1-Punkte, FCOR auf den ersten,
#   Nullauffüllung auf SI, FFT, gespiegelt mit Roll 1, Phase exp(−i·(PHC0 + PHC1·i/SI)) wie 1D. Je FnMODE empirisch an
#   2rr bestimmt (keine Bruker-Quelle): QF NICHT gespiegelt; States-TPPI jedes 2. komplexe t1-Paar negiert; TPPI reelle
#   FT über 2·SI, zweite Hälfte, gespiegelt mit Roll 1; Echo-Antiecho cos = i·(E + A), sin = i·i·(E − A)
#   (F2-Vierteldrehung, 22 punktweise + 105 LP-Sätze). Betrag (PH_mod 2): F2 = hypot(RR, IR), F1 = hypot(RR, RI),
#   beide = Wurzel aller vier Quadranten. apk*/apkm im auditp: gespeicherte Phase gilt auch bei PH_mod 0 (1 Satz).
#   F1-Breite = SW·SFO1 aus acqu2s (SW_h dort ist nicht die F1-Breite; OFFSET so an 314 Sätzen ≤ 0.0014 Punkte).
F1_FLIP = {"QF": False, "TPPI": True, "States-TPPI": True, "Echo-Antiecho": True}
EA_TURN = 1j                     # Echo-Antiecho: C = EA_TURN·(E + A), D = EA_TURN·i·(E − A)
# NOAH unaufgeteilt (91/91 Eltern bytegleich): Block k = Zeile 2·j + k − 1, Modul = k-ter Buchstabe; nur noah2_SB/BS.
NOAH_PULPROG = re.compile(r"noah2_(SB|BS)")
# Verarbeitung je Modul = TopSpins Teilsätze (91 HSQC, 91 HMBC, alle gleich bis auf HMBC SSB(F2): 2 in 50, 4 in 41 ->
# 2), ohne LP (nicht nachgebaut). Die HSQC-Phase steht in keinem Elternsatz (apkm je Teilsatz): nur mit Nutzerphase.
_NOAH_F2 = dict(SI=4096, WDW=4, SSB=2, LB=0.0, GB=0.0, BC_mod=0, ME_mod=0, TDeff=0, TDoff=0, FTSIZE=0, STSI=0, STSR=0,
                REVERSE="no", PHC0=0.0, PHC1=0.0)
_NOAH_F1 = dict(_NOAH_F2, SI=1024, FCOR=0.5, MC2=5)
NOAH_PARAMS = {"HSQC": (dict(_NOAH_F2, PH_mod=1), dict(_NOAH_F1, PH_mod=1)),
               "HMBC": (dict(_NOAH_F2, PH_mod=2), dict(_NOAH_F1, PH_mod=0))}
O1_TOL_MHZ = 1e-6                # homonuklear: SFO1 in acqu2s ≠ acqus (1 Satz, 650 Hz) -> F1-Achse mit SFO1 aus acqus


class Result(NamedTuple):
    data: np.ndarray             # SI(F1) × SI(F2), Index wie TopSpins 2rr
    ax2: np.ndarray              # ppm je Spalte (F2)
    ax1: np.ndarray              # ppm je Zeile (F1)
    mode: str                    # F1-Quadraturmodus
    p2: dict                     # verwendete procs (F2)
    p1: dict                     # verwendete proc2s (F1)
    notes: list                  # Hinweise (Texte), auch jeder Nutzerwert
    sf: tuple                    # SF (F2, F1) der Achsen = BF1 (unkalibriert)
    sf_stored: tuple             # SF (F2, F1) aus procs/proc2s (TopSpins Kalibrierung), None ohne pdata (NOAH-Eltern)


def mode_of(a2, p1):
    fn = a2.get("FnMODE", 0)
    return NP.F1_MODES.get(fn) if fn else NP.MC2_MODES.get(p1.get("MC2"))


def load(expdir, procno=1, f2=None, f1=None):
    """acqus, acqu2s, procs, proc2s, auditp-Text eines Experiments; apk*-Regel, dann Nutzerwerte f2/f1 (dicts, z. B.
    {"ME_mod": 0} = ohne Linear Prediction, eigene Phase) über die gespeicherten Werte."""
    d = Path(expdir)
    pd = d / "pdata" / str(procno)
    a, a2 = BN.acqus(d), BN.acqus(d, "acqu2s")
    p2, p1 = BN.procs(pd), BN.procs(pd, "proc2s")
    audit = (pd / "auditp.txt").read_text(encoding="latin-1") if (pd / "auditp.txt").is_file() else ""
    if re.search(r"\bapk", audit):                     # apk/apkm phast 2rr mit PHC0/PHC1, auch bei PH_mod 0
        p2, p1 = (dict(q, PH_mod=1) if q.get("PH_mod") == 0 else q for q in (p2, p1))
    return a, a2, dict(p2, **(f2 or {})), dict(p1, **(f1 or {})), audit


def reasons(expdir, procno=1, f2=None, f1=None, name=""):
    """Meldungen, warum das Experiment nicht selbst verarbeitet wird (leer = erlaubt; der Vorzeichenvergleich mit
    2rr folgt erst in process)."""
    name = name or _name(expdir)
    a, a2, p2, p1, audit = load(expdir, procno, f2, f1)
    return _lp_f2(expdir, procno, p2, name) + NP.blockers(a, p2, a2, p1, name=name, auditp=audit)


def _lp_f2(expdir, procno, p2, name):
    """LP in F2 abschalten ist nicht belegt (ohne LP nur F1 an echten Sätzen geprüft): Meldung, wenn ein Nutzerwert
    das gespeicherte ME_mod (F2) ≠ 0 aufhebt."""
    stored = load(expdir, procno)[2].get("ME_mod", 0)
    return [T("c2d_lp_f2", name=name, v=stored)] if stored != 0 and p2.get("ME_mod") == 0 else []


def _name(expdir):
    return BN._short(Path(expdir), 3)


def _override_notes(name, base2, base1, f2, f1):
    """jeder Nutzerwert, der vom gespeicherten Wert (bzw. der Vorgabe) abweicht, als Hinweis."""
    return [T("c2d_override", name=name, dim=dim, key=k, v=v, old=base.get(k, "–"))
            for dim, base, o in (("F2", base2, f2), ("F1", base1, f1)) for k, v in (o or {}).items()
            if base.get(k) != v]


def _window(n, p, sw, grp=0.0):
    """procref: EM exp(−π·LB·t), SINE sin((π−φ)·t/AQ + φ), QSINE Quadrat davon, φ = π/SSB (SSB < 2: 0)."""
    k = np.arange(n, dtype=float)
    if p["WDW"] == 1:
        return np.exp(-np.pi * p["LB"] * (k - grp) / sw)
    t, aq = (k - grp) / sw, n / sw
    phi = np.pi / p["SSB"] if p["SSB"] >= 2 else 0.0
    s = np.sin((np.pi - phi) * t / aq + phi)
    return s * s if p["WDW"] == 4 else s


def _f2(fid, a, p):
    """F2 aller Zeilen wie nmr_proc.process_1d (Gruppenlaufzeit Pivot links, Spiegeln mit Roll 1, Phase −)."""
    si = p["SI"]
    x = fid
    n = x.shape[-1]
    if p.get("TDeff", 0) and p["TDeff"] // 2 < n:
        n = p["TDeff"] // 2
        x = x[..., :n]
    g = NP.group_delay(a)
    x = x * _window(n, p, a["SW_h"], g if p["WDW"] == 1 else 0.0)
    X = np.zeros(x.shape[:-1] + (si,), complex)
    X[..., :min(n, si)] = x[..., :si]
    s = np.fft.fftshift(np.fft.fft(X, axis=-1), axes=-1)
    k = np.arange(si) - si // 2
    s *= np.exp(2j * np.pi * g * (k - si / 2) / si)
    s = np.roll(s[..., ::-1], 1, axis=-1)
    if p["PH_mod"] == 1:
        s *= np.exp(-1j * np.deg2rad(p["PHC0"] + p["PHC1"] * (np.arange(si) / si)))
    return s


def _phase1(s, p1):
    if p1["PH_mod"] == 1:
        s *= np.exp(-1j * np.deg2rad(p1["PHC0"] + p1["PHC1"] * (np.arange(p1["SI"]) / p1["SI"])))[:, None]
    return s


def _f1(x, p1, sw1, flip):
    """Fenster + FCOR + Nullauffüllung + FFT entlang t1 (Achse 0), Spiegelung je Modus, Phase."""
    si, n1 = p1["SI"], x.shape[0]
    x = x * _window(n1, p1, sw1)[:, None]
    x[0] *= p1["FCOR"]
    X = np.zeros((si,) + x.shape[1:], complex)
    X[:min(n1, si)] = x[:si]
    s = np.fft.fftshift(np.fft.fft(X, axis=0), axes=0)
    if flip:
        s = np.roll(s[::-1], 1, axis=0)
    return _phase1(s, p1)


def _tppi(x, p1, sw1):
    """reelle t1-Daten (DW1 = 1/(2·SW1)): FT über 2·SI, zweite Hälfte, gespiegelt mit Roll 1."""
    si, n1 = p1["SI"], x.shape[0]
    x = x * _window(n1, p1, sw1)[:, None]
    x[0] *= p1["FCOR"]
    X = np.zeros((2 * si,) + x.shape[1:])
    X[:min(n1, 2 * si)] = x[:2 * si]
    f = np.fft.fft(X, axis=0)[si:]
    if F1_FLIP["TPPI"]:
        f = np.roll(f[::-1], 1, axis=0)
    return _phase1(f, p1)


def compute(ser, a, a2, p2, p1):
    """ser (komplex, Zeilen = t1) + Parameter -> reelle Matrix SI(F1) × SI(F2). Prüft nichts: vorher blockers."""
    mode = mode_of(a2, p1)
    S = _f2(ser, a, p2)
    sw1 = a2["SW"] * a2["SFO1"]
    if mode == "QF":
        Z = _f1(S, p1, sw1, F1_FLIP["QF"])
        rr, ri, ir, ii = Z.real, Z.imag, None, None
    elif mode == "TPPI":
        XR, XI = _tppi(S.real, p1, sw1), _tppi(S.imag, p1, sw1)
        rr, ri, ir, ii = XR.real, XR.imag, XI.real, XI.imag
    elif mode in ("States-TPPI", "Echo-Antiecho"):
        n1 = S.shape[0] // 2
        C, D = S[0:2 * n1:2], S[1:2 * n1:2]
        if mode == "Echo-Antiecho":
            C, D = EA_TURN * (C + D), EA_TURN * 1j * (C - D)
        else:
            sgn = ((-1.0) ** np.arange(n1))[:, None]
            C, D = C * sgn, D * sgn
        XR = _f1(C.real + 1j * D.real, p1, sw1, F1_FLIP[mode])
        XI = _f1(C.imag + 1j * D.imag, p1, sw1, F1_FLIP[mode])
        rr, ri, ir, ii = XR.real, XR.imag, XI.real, XI.imag
    else:
        raise ValueError(mode)
    ph2, ph1 = p2["PH_mod"], p1["PH_mod"]
    if ph2 == 2 and ph1 == 2:
        return np.sqrt(sum(q ** 2 for q in (rr, ri, ir, ii) if q is not None)), mode
    if ph2 == 2:
        return (np.hypot(rr, ir) if ir is not None else np.abs(rr)), mode
    if ph1 == 2:
        return np.hypot(rr, ri), mode
    return rr, mode


def axis(a, n, sf=None):
    """ppm je Punkt aus den Akquisitionsparametern: OFFSET = (SFO1/SF − 1)·1e6 + SW·SFO1/(2·SF), Abstand SW·SFO1/(SF·n).
    SF = BF1 (unkalibriert wie TopSpins Teilsätze; die 1D-Kalibrierung rechnet der Aufrufer um), sonst sf."""
    sf = a["BF1"] if sf is None else sf
    sw = a["SW"] * a["SFO1"]
    return (a["SFO1"] / sf - 1) * 1e6 + 0.5 * sw / sf - np.arange(n) * sw / sf / n


def _axes(a, a2, p2, p1, name):
    notes = []
    if a.get("NUC1") == a2.get("NUC1") and abs(a2["SFO1"] - a["SFO1"]) > O1_TOL_MHZ:
        notes.append(T("c2d_o1", name=name, d=f"{(a2['SFO1'] - a['SFO1']) * 1e6:.0f}"))
        a2 = dict(a2, SFO1=a["SFO1"])
    return axis(a, p2["SI"]), axis(a2, p1["SI"]), notes


def _sign_check(data, pdir, name):
    """Globales Vorzeichen gegen TopSpins 2rr (3/91 TUDO-HSQC kamen mit gespeicherter Phase invertiert heraus):
    Pearson r ≤ 0 -> ValueError. Anderes SI: 2rr-Raster aus dem eigenen Ergebnis (gleiche Achsenspanne) abgetastet."""
    ref = BN.read_2d(pdir)[0]
    i1 = np.arange(ref.shape[0]) * data.shape[0] // ref.shape[0]
    i2 = np.arange(ref.shape[1]) * data.shape[1] // ref.shape[1]
    own = data[np.ix_(i1, i2)]
    own, ref = own - own.mean(), ref - ref.mean()
    r = float((own * ref).sum() / np.sqrt((own * own).sum() * (ref * ref).sum()))
    if not r > 0:
        raise ValueError(T("c2d_sign", name=name, r=f"{r:.2f}"))


def process(expdir, procno=1, f2=None, f1=None, name=""):
    """Experiment (ser + pdata/procno) selbst verarbeiten -> Result. Abgelehnt (blockers, Vorzeichen gegen ein
    vorhandenes 2rr) -> ValueError mit der ersten Meldung; f2/f1 = Nutzerwerte über procs/proc2s (z. B.
    {"ME_mod": 0}: ohne Linear Prediction), jeder davon steht in notes."""
    name = name or _name(expdir)
    a, a2, p2, p1, audit = load(expdir, procno, f2, f1)
    why = _lp_f2(expdir, procno, p2, name) + NP.blockers(a, p2, a2, p1, name=name, auditp=audit)
    if why:
        raise ValueError(why[0])
    ser, _, _ = BN.read_ser(expdir)
    data, mode = compute(ser, a, a2, p2, p1)
    pdir = Path(expdir) / "pdata" / str(procno)
    if (pdir / "2rr").is_file():
        _sign_check(data, pdir, name)
    ax2, ax1, notes = _axes(a, a2, p2, p1, name)
    base2, base1 = load(expdir, procno)[2:4]
    notes += _override_notes(name, base2, base1, f2, f1)
    return Result(data, ax2, ax1, mode, p2, p1, notes, (a["BF1"], a2["BF1"]), (base2.get("SF"), base1.get("SF")))


def noah_blocks(expdir):
    """Unaufgeteiltes NOAH (noah2_SB/BS, NBL 2) -> (acqus, acqu2s je Block, [(Modul, Rohzeilen im Dateityp inkl.
    Auffüllung)] für k = 1, 2). Andere NOAH-Varianten -> ValueError (nur diese an echten Daten geprüft)."""
    d = Path(expdir)
    a, a2 = BN.acqus(d), BN.acqus(d, "acqu2s")
    where = BN._short(d / "ser")
    m = NOAH_PULPROG.fullmatch(str(a.get("PULPROG", "")))
    if not m or a.get("NBL") != 2 or a.get("FnTYPE", 0) != 0:
        raise ValueError(T("c2d_noah_unchecked", name=where, pp=a.get("PULPROG", "–"), n=a.get("NBL", "–")))
    dt = BN._dtype(a, "DTYPA", "BYTORDA", where, big=True)
    td2, td1 = BN._td(a, where), BN._td(a2, where)         # td1 gerade: zwei Blöcke gleicher Länge
    row = -(-td2 * dt.itemsize // 1024) * 1024 // dt.itemsize
    raw = BN._data(d / "ser", dt, where)
    if raw.size % row or raw.size // row < td1:            # Datei kann mehr Zeilen haben (abgebrochene Messung)
        raise ValueError(T("b1nmr_size", name=where, n=raw.size, m=td1 * row))
    raw = raw[: td1 * row].reshape(td1, row)
    letters = BN.NOAH_LETTERS
    return dict(a, NBL=1), dict(a2, TD=td1 // 2), [(letters[m.group(1)[k]], raw[k::2]) for k in range(2)]


def process_noah(expdir, k, f2=None, f1=None, name=""):
    """Block k (1, 2) eines unaufgeteilten NOAH-Satzes mit den Vorgaben des Moduls (NOAH_PARAMS) verarbeiten; f2/f1 =
    Nutzerwerte. Phasenempfindliche Module (HSQC): ohne Phase des Nutzers in jeder phasierten Dimension (PHC0 in f2
    und f1) ValueError „Phase ausstehend“ – der Elternsatz enthält keine Phase, F1 ist um 180° mehrdeutig (8/12 TUDO-
    Eltern kamen mit F2-Phase allein invertiert heraus). Achsen unkalibriert (SF = BF1) wie TopSpins Teilsätze."""
    name = name or _name(expdir)
    a, a2, blocks = noah_blocks(expdir)
    if not isinstance(k, int) or not 1 <= k <= len(blocks):
        raise ValueError(T("c2d_noah_k", name=name, k=k, n=len(blocks)))
    module, raw = blocks[k - 1]
    base2, base1 = NOAH_PARAMS[module]
    p2, p1 = dict(base2, **(f2 or {})), dict(base1, **(f1 or {}))
    why = NP.blockers(a, p2, a2, p1, name=name)
    if why:
        raise ValueError(why[0])
    missing = [dim for dim, p, o in (("F2", p2, f2), ("F1", p1, f1)) if p["PH_mod"] == 1 and "PHC0" not in (o or {})]
    if missing:
        raise ValueError(T("c2d_noah_phase", name=name, module=module, dims=" + ".join(missing)))
    td2 = a["TD"]
    rows = raw[:, :td2].astype(float)
    data, mode = compute(rows[:, 0::2] + 1j * rows[:, 1::2], a, a2, p2, p1)
    ax2, ax1, notes = _axes(a, a2, p2, p1, name)
    notes += _override_notes(name, base2, base1, f2, f1)
    return Result(data, ax2, ax1, mode, p2, p1, notes, (a["BF1"], a2["BF1"]), (None, None))
