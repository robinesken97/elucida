"""
elucida/core/nmr_proc.py - 1D-NMR aus dem Bruker-FID rechnen (ohne Qt): EM-Fenster, Nullauffüllung, FFT, Gruppenlaufzeit,
Spiegeln, Phase PHC0/PHC1 aus procs. Nur die an echten Daten belegten Konventionen; alles andere wird mit Meldung abgelehnt
(`blockers`), dann darf nur TopSpins eigenes Spektrum (1r/2rr) gezeigt werden.
"""
from __future__ import annotations

import math
import re

import numpy as np

from elucida.app.i18n import T

# Belegt (Audit 1.3.0, brk.py; 201 1D davon 196 unabhängig, eigenes Spektrum = TopSpins 1r bis auf die Basislinie):
#   Gruppenlaufzeit GRPDLY als lineare Phase mit Pivot am LINKEN Rand (Mitte scheitert an 78 gebrochenen GRPDLY);
#   Spiegeln mit Verschiebung um einen Punkt (Träger bei i = SI/2); Phase exp(−i·(PHC0 + PHC1·i/SI)); FCOR ohne
#   Einfluss.
#   TopSpins 1i = −Im(Ergebnis). Nur gerades GRPDLY (gebrochen ≤ 0.08 daneben) kam vor: mehr als GRPDLY_EVEN_TOL
#   neben einer geraden Zahl wird abgelehnt (bei ungeradem GRPDLY unterscheiden sich die Pivots um 180°).
#   Ohne GRPDLY (alte Geräte, DSPFVS 12): Gruppenlaufzeit aus der Tabelle in nmrglue fileio/bruker.py `bruker_dsp_table`
#   (dort Westler/Abildgaard zugeschrieben), zweimal abgeschrieben; nur die an 78 Sätzen geprüften Paare.
#   DSPFVS 10 (nur mit Vorbehalt belegt), DIGMOD 0 und alle übrigen Paare werden abgelehnt.
DSP_TABLE = {12: {8: 53.25, 12: 69.5, 16: 71.625, 24: 70.166666666666667, 32: 72.125, 64: 72.375}}
# Geprüfte Werte (fehlt der Schlüssel: abgelehnt). PH_mod 0 nur mit apbk-Basislinie gesehen: nicht vergleichbar, abgelehnt.
CHECKED_ACQ = {"AQ_mod": (1, 3)}                                       # 1/3 = qsim/DQD
CHECKED_PROC = {"WDW": (1,), "PH_mod": (1,), "FT_mod": (6,), "BC_mod": (0,), "TDoff": (0,), "STSR": (0,),
                "REVERSE": ("no",)}                                    # WDW 1 = EM
GRPDLY_EVEN_TOL = 0.1          # belegt: gebrochenes GRPDLY höchstens 0.08 neben einer geraden Zahl (505 Sätze)
# 2D (Spezifikation „2D-Prüfung“): ohne echten Satz bzw. nicht nachgebaut -> nur 2rr. Für die eigene 2D-Verarbeitung.
F1_MODES = {1: "QF", 2: "QSEQ", 3: "TPPI", 4: "States", 5: "States-TPPI", 6: "Echo-Antiecho"}      # FnMODE (acqu2s)
MC2_MODES = {0: "QF", 1: "QSEQ", 2: "TPPI", 3: "States", 4: "States-TPPI", 5: "Echo-Antiecho"}     # MC2, wenn FnMODE 0
F1_MODES_UNCHECKED = ("QSEQ", "States")
PSEUDO_2D = ("jres", "t1ir", "t1rho", "ledbp", "stebp")               # J-res, T1/T1rho, DOSY (Pulsprogramm, klein)
AUDIT_2D_UNCHECKED = r"\b(sym\w*|tilt|ptilt\w*)\b"                    # auditp: symmetrisiert/gekippt
# Eigene 2D-Verarbeitung (core/nmr2d.py): nur Klassen mit bestandenem B2-Satz (eigene FT aus ser = 2rr, BERICHT 2D).
# PH_mod 0 = ohne Phase, 1 = Phase, 2 = Betrag; Paare (F2, F1) je Modus. WDW 3/4 = SINE/QSINE.
PH_2D = {"QF": ((0, 2), (1, 2)), "TPPI": ((1, 1),), "States-TPPI": ((1, 1),),
         "Echo-Antiecho": ((1, 1), (1, 0), (2, 0), (2, 1))}
WDW_2D = (3, 4)
SSB_2D = (0, 2, 4, 8)
FCOR_2D = (0.5, 1)
# Speicher: gemessen 6.3 × Ergebnisgröße (4096², float64) als Spitze -> Faktor 7; Grenze für 8-GB-Rechner
SI_MAX_2D = 8192
MEM_FACTOR_2D, MEM_MAX_2D = 7, 1.5e9


def group_delay(a):
    """Gruppenlaufzeit des Digitalfilters in Punkten: GRPDLY, sonst Tabelle (DSPFVS, DECIM); None = nicht belegt.
    Tabelle: nmrglue nmrglue/fileio/bruker.py `bruker_dsp_table`, Commit 3505954195d5380ab5cdba6663c7dcc892a57e2d."""
    g = a.get("GRPDLY")
    if isinstance(g, (int, float)) and not isinstance(g, bool) and g > 0:
        return g if math.isfinite(g) else None
    if a.get("DIGMOD") == 0:                              # analoger Filter: kein geprüfter Satz
        return None
    d = a.get("DECIM")
    if not _is_num(d) or not math.isfinite(d) or d != int(d):   # 16.5 nie zu 16 kürzen: nicht belegt
        return None
    try:
        return DSP_TABLE[a.get("DSPFVS")][int(d)]
    except (KeyError, TypeError):
        return None


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _value(key, v, ok):
    return T("b1nmr_why_value", key=key, v="–" if v is None else v, ok=", ".join(map(str, ok)))


def blockers(a, p, a2=None, p2=None, name="", auditp=""):
    """Gründe (Meldungen), warum ein Experiment nicht selbst verarbeitet werden darf; leer = erlaubt.
    2D (p = procs F2, a2/p2 = acqu2s/proc2s F1, auditp = Text von auditp.txt): die verwendeten Parameter (nach
    apk-Regel und Nutzerwerten, core/nmr2d.load); erlaubt nur belegte Klassen (PH_2D, WDW_2D, SSB_2D, FCOR_2D)."""
    two = a2 is not None
    if two:
        p2 = p2 or {}
    why = []
    fnt = a.get("FnTYPE", 0)                               # fehlt in alten 1D-Sätzen
    if fnt == 2:
        why.append(T("b1nmr_why_nus"))
    elif fnt != 0:
        why.append(_value("FnTYPE", fnt, (0,)))
    nbl = a.get("NBL")
    if isinstance(nbl, int) and not isinstance(nbl, bool) and nbl > 1:
        why.append(T("b1nmr_why_nbl", n=nbl))
    elif nbl != 1:
        why.append(_value("NBL", nbl, (1,)))
    for dim, q in (("F2", p), ("F1", p2)):
        if q is None:
            continue
        me = q.get("ME_mod")
        if me is None or not _is_num(me):
            why.append(_value(f"ME_mod ({dim})", me, (0,)))
        elif me != 0:
            why.append(T("b1nmr_why_lp", dim=dim, v=me))
    g = a.get("GRPDLY")
    if _is_num(g) and g > 0 and not math.isfinite(g):   # round(inf) bräche ab: Meldung statt Absturz
        why.append(_value("GRPDLY", g, ("> 0",)))
    elif _is_num(g) and g > 0:
        if abs(g - 2 * round(g / 2)) > GRPDLY_EVEN_TOL:    # Tabellenwerte (unten) sind einzeln geprüft
            why.append(T("b1nmr_why_grpdly_odd", v=g, tol=GRPDLY_EVEN_TOL))
    elif two:
        why.append(T("b1nmr_why_grpdly_2d"))
    elif a.get("DIGMOD") == 0:
        why.append(T("b1nmr_why_digmod"))
    elif group_delay(a) is None:
        why.append(T("b1nmr_why_grpdly", v=a.get("DSPFVS", "–"), d=a.get("DECIM", "–")))
    if not two:
        for par, checked in ((a, CHECKED_ACQ), (p, CHECKED_PROC)):
            for key, ok in checked.items():
                if par.get(key) not in ok:
                    why.append(_value(key, par.get(key), ok))
        si = p.get("SI")
        if _is_num(si) and p.get("STSI") != si:
            why.append(T("b1nmr_why_strip", v=p.get("STSI", "–"), si=si))
        for key, par in (("SW_h", a), ("SI", p), ("LB", p), ("PHC0", p), ("PHC1", p), ("TDeff", p)):
            if not _is_num(par.get(key, 0 if key == "TDeff" else None)):
                why.append(T("b1nmr_why_missing", key=key))
        if _is_num(si) and (si < 2 or int(si) & (int(si) - 1)):
            why.append(T("b1nmr_why_si", si=si))
        return [T("b1nmr_own", name=name, why=w, file="1r") for w in why]
    if a.get("AQ_mod") != 3:                               # nur DQD an 2D-Sätzen belegt
        why.append(_value("AQ_mod", a.get("AQ_mod"), (3,)))
    for key, par in (("SW_h", a), ("SW", a), ("SFO1", a), ("BF1", a), ("SW", a2), ("SFO1", a2), ("BF1", a2),
                     ("TD", a2)):
        if not _is_num(par.get(key)):
            why.append(T("b1nmr_why_missing", key=key))
    for dim, q in (("F2", p), ("F1", p2)):
        for key in ("SI", "WDW", "SSB", "PH_mod", "PHC0", "PHC1") + (("FCOR",) if dim == "F1" else ()):
            if not _is_num(q.get(key)):
                why.append(T("b1nmr_why_missing", key=f"{key} ({dim})"))
        if q.get("REVERSE", "no") != "no":
            why.append(_value(f"REVERSE ({dim})", q.get("REVERSE"), ("no",)))
        if q.get("WDW") not in WDW_2D:                     # EM/GM/ohne Fenster: kein 2D-Satz verglichen
            why.append(_value(f"WDW ({dim})", q.get("WDW"), ("SINE", "QSINE")))
        elif q.get("SSB") not in SSB_2D:
            why.append(_value(f"SSB ({dim})", q.get("SSB"), SSB_2D))
        si = q.get("SI")
        if _is_num(si) and (si < 2 or int(si) & (int(si) - 1)):
            why.append(T("b1nmr_why_si", si=si))
        if _is_num(si) and si > SI_MAX_2D:
            why.append(_value(f"SI ({dim})", si, (f"≤ {SI_MAX_2D}",)))
        te = q.get("TDeff", 0)
        if not _is_num(te) or te < 0:
            why.append(_value(f"TDeff ({dim})", te, ("≥ 0",)))
        for key, ok in (("FTSIZE", (0, si)), ("STSI", (0, si)), ("STSR", (0,)), ("BC_mod", (0,)), ("TDoff", (0,))):
            if q.get(key, 0) not in ok:                  # Strip-FT, qpol/quad: ohne bestandenen 2D-Satz
                why.append(_value(f"{key} ({dim})", q.get(key), ok))
    si2, si1 = p.get("SI"), p2.get("SI")
    if _is_num(si2) and _is_num(si1) and si2 * si1 * 8 * MEM_FACTOR_2D > MEM_MAX_2D:
        why.append(T("c2d_why_mem", si=f"{si1} × {si2}", gb=f"{si2 * si1 * 8 * MEM_FACTOR_2D / 1e9:.1f}",
                     max=f"{MEM_MAX_2D / 1e9:.1f}"))
    if p2.get("FCOR") not in FCOR_2D and _is_num(p2.get("FCOR")):
        why.append(_value("FCOR (F1)", p2.get("FCOR"), FCOR_2D))
    te, td1 = p2.get("TDeff", 0), a2.get("TD")
    if _is_num(te) and _is_num(td1) and 0 < te < td1:   # TopSpin kürzt t1, nicht nachgebaut (Sätze scheiterten)
        why.append(_value("TDeff (F1)", te, (0, f"≥ {td1}")))
    fn = a2.get("FnMODE", 0)
    mode = F1_MODES.get(fn) if fn else MC2_MODES.get(p2.get("MC2"))
    if mode is None or mode in F1_MODES_UNCHECKED:
        why.append(T("b1nmr_why_f1mode", v=mode or f"FnMODE {fn}, MC2 {p2.get('MC2', '–')}"))
    elif (p.get("PH_mod"), p2.get("PH_mod")) not in PH_2D[mode]:
        why.append(_value("PH_mod (F2/F1)", f"{p.get('PH_mod')}/{p2.get('PH_mod')}",
                          [f"{x}/{y}" for x, y in PH_2D[mode]]))
    pp = str(a.get("PULPROG", "")).lower()
    if any(k in pp for k in PSEUDO_2D):
        why.append(T("b1nmr_why_pseudo", pp=a.get("PULPROG")))
    m = re.search(AUDIT_2D_UNCHECKED, auditp or "")
    if m:
        why.append(T("b1nmr_why_symtilt", cmd=m.group(1)))
    return [T("b1nmr_own", name=name, why=w, file="2rr") for w in why]


def process_1d(fid, a, p, name=""):
    """FID (read_fid) + acqus + procs -> komplexes Spektrum, Index wie TopSpins 1r (Realteil = 1r ohne Basislinie).
    Abgelehnte Experimente (blockers) -> ValueError mit der ersten Meldung."""
    why = blockers(a, p, name=name)
    if why:
        raise ValueError(why[0])
    si = p["SI"]
    n = fid.size
    if p.get("TDeff", 0) and p["TDeff"] < 2 * n:
        n = p["TDeff"] // 2
    x = fid[:n].copy()
    g = group_delay(a)
    t = (np.arange(n) - g) / a["SW_h"]
    x *= np.exp(-np.pi * p["LB"] * t)                    # EM
    x = np.concatenate([x, np.zeros(max(si - n, 0), complex)])[:si]
    s = np.fft.fftshift(np.fft.fft(x))
    k = np.arange(si) - si // 2
    s *= np.exp(2j * np.pi * g * (k - si / 2) / si)      # Gruppenlaufzeit, Pivot linker Rand
    s = np.roll(s[::-1], 1)                              # Index i <-> Frequenz SI/2 − i
    ph = np.deg2rad(p["PHC0"] + p["PHC1"] * (np.arange(si) / si))
    return s * np.exp(1j * -1.0 * ph)
