"""
elucida/core/nmr_report.py - NMR-Ergebnis als Modell, SI-Zeile lesen und schreiben (ohne Qt).

Ein `Spectrum` = eine SI-Zeile wie
    1H NMR (400 MHz, CDCl3): δ [ppm] = 7.26 – 7.20 (m, 2H, Ar-H), 3.71 (q, J = 7.1 Hz, 2H, OCH2)
Das Modell hält nur die Bedeutung (δ oder Bereich, Klasse, Kopplungen, nH, Zuordnung) als Zahlen und rundet erst beim
Schreiben; das Aussehen kommt aus `Style` (Felder wie die Eigenschaften des Mnova-Multiplettberichts: deltaPrecision,
jPrecision, Bereichsvorlage, Trenner, Reihenfolge, Sortierung). `SI_STYLE` ist das Preset der Gruppen-SI.
Klassen: s, m, quint/sext/sept/hept/p und Folgen aus d/t/q/p (bis fünf Buchstaben); die Auswertung bildet „p“ und
„hept“ wie die Gruppen-SI. Lösungsmittel über `solvent_text` (Schreibweisen über `nmr_impurities.solvent_key`).

Markup wie in Elucida (`tabs/nmr.py`, `XRAY.runs`): ^{…} hoch, _{…} tief, *…* kursiv, \\x = Zeichen x selbst. Die
Zuordnung ist der einzige Freitext und wird maskiert (`esc`); `plain(markup)` = Text ohne Auszeichnung (wie die PDF).
Beispiele in diesem Modul sind erfunden.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from elucida.app.i18n import T
from elucida.core import nmr_impurities as IMP

# Status von δ und J: ein automatischer Wert ist ein Vorschlag, bis der Nutzer ihn bestätigt; „unmeasured“ = J
# eingegeben, aber nicht gemessen (Linien nicht getrennt), dann ist auch δ des Fits unsicher. Gedruckt wird nur
# Bestätigtes, sonst Bereich + „m“ ohne J (Ersatz bis zur Entscheidung, was die SI dafür zeigt).
CONFIRMED, SUGGESTED, UNMEASURED = "confirmed", "suggested", "unmeasured"

_CLASS_RE = re.compile(r"^(?:[dtqp]{1,5}|s|quint|sext|sept|hept|m)$")   # wie nmr_analysis.class_letters + s, m
_LETTER_N = {"d": 1, "t": 2, "q": 3, "p": 4, "quint": 4, "sext": 5, "sept": 6, "hept": 6}


@dataclass
class Coupling:
    hz: float
    bonds: int | None = None      # ¹J -> 1 (gedruckt nur mit Partner oder Bindungszahl)
    partner: str = ""             # „C,F“ für J(C,F)
    status: str = SUGGESTED       # ohne Angabe nie gedruckt (fail closed); der Leser setzt CONFIRMED

    def label(self):
        return (self.bonds, self.partner)


@dataclass
class Signal:
    shift: float | None = None    # δ eines aufgelösten Signals (None, wenn nur ein Bereich)
    lo: float | None = None       # Bereich, untere Grenze (ppm); bei δ aus der Auswertung der Bereich für den Ersatz
    hi: float | None = None
    mult: str = ""                # s, d, dd, …, m; "" = keine (¹³C)
    broad: bool = False
    J: list = field(default_factory=list)   # [Coupling] in Druckreihenfolge
    nH: float | None = None
    assign: str = ""              # Freitext
    status: str = SUGGESTED       # von δ (siehe CONFIRMED oben); ohne Angabe nie gedruckt

    @property
    def is_range(self):
        return self.shift is None

    @property
    def printable(self):
        """δ und alle J bestätigt (sonst druckt `signal_markup` Bereich + „m“ ohne J)."""
        return self.status == CONFIRMED and all(c.status == CONFIRMED for c in self.J)

    @property
    def centre(self):
        return (self.lo + self.hi) / 2 if self.is_range else self.shift


@dataclass
class Spectrum:
    nucleus: str                  # „1H“, „13C“, „19F“
    freq: float                   # MHz wie gedruckt
    solvent: str                  # „CDCl3“, „DMSO-d6“
    temp: float | None = None     # K
    dec: str = ""                 # „{1H}“ für 13C{1H}
    signals: list = field(default_factory=list)
    digits: int | None = None     # Stellen von δ (deltaPrecision); None -> Vorgabe des Stils je Kern


@dataclass(frozen=True)
class Style:
    """Eigenschaften des Mnova-Multiplettberichts: Kopf, deltaPrecision, jPrecision, Bereichsvorlage, Trenner,
    Reihenfolge in der Klammer, Sortierung; `minus` = Zeichen für negative δ (SI-Preset „-“ wie Mnova, der NMR-Tab druckt
    bisher U+2212)."""
    head: str = "{nuc} NMR ({cond}): δ [ppm] = "
    delta_digits: tuple = (("1H", 2), ("", 1))    # Kern -> Stellen; "" = alle übrigen
    j_digits: int = 1
    range_tpl: str = "{hi} – {lo}"                # hoher Wert zuerst
    m_sep: str = ", "
    j_sep: str = ", "
    j_tpl: str = "{label} = {list} Hz"
    order: tuple = ("mult", "J", "nH", "assign")  # in der Klammer
    broad_tpl: str = "br. {mult}"
    sort: str | None = None                       # None = wie gelistet, „desc“/„asc“ nach δ
    minus: str = "-"

    def digits_for(self, spec):
        if spec.digits is not None:
            return spec.digits
        d = dict(self.delta_digits)
        return d.get(spec.nucleus, d.get("", 2))


SI_STYLE = Style()   # Preset der Gruppen-SI („¹H NMR (500 MHz, CDCl₃): δ [ppm] = …“)


# ---------------------------------------------------------------------------- Markup
def esc(text):
    """Freitext unverändert ins Markup (wie `XRAY.esc_markup`: „Cp*“ würde sonst kursiv)."""
    return re.sub(r"([*_^~\\])", r"\\\1", str(text))


def plain(markup):
    """Markup -> Text ohne Auszeichnung (^{x}/_{x}/~{x} -> x, * fällt weg, \\x -> x)."""
    out, i, depth = [], 0, 0
    while i < len(markup):
        c = markup[i]
        if c == "\\" and i + 1 < len(markup):
            out.append(markup[i + 1])
            i += 2
        elif c in "_^~" and markup[i + 1:i + 2] == "{":
            depth += 1                                     # „{¹H}“ in 13C{1H}: Klammern ohne Marke bleiben Text
            i += 2
        elif (c == "}" and depth) or c == "*":
            depth -= c == "}"
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _num(x, d, minus="-"):
    s = f"{x:.{d}f}"
    if s.startswith("-") and float(s) == 0:              # nie „-0.00“
        s = s[1:]
    return s.replace("-", minus)


def _jlabel(c):
    if c.bonds is None and not c.partner:
        return "*J*"
    return (f"^{{{c.bonds}}}" if c.bonds is not None else "") + "*J*" + (f"_{{{c.partner}}}" if c.partner else "")


def nucleus_markup(nuc):
    m = re.match(r"(\d+)([A-Za-z]+)$", nuc)
    return f"^{{{m.group(1)}}}{m.group(2)}" if m else esc(nuc)


SOLVENT_SI = {"(CD3)2SO": "DMSO-d6"}   # Spalte der Fulmer-Tabelle -> Schreibweise der Gruppen-SI, wo sie abweicht


def solvent_text(name):
    """Lösungsmittel wie im Datensatz oder Feld („DMSO“, „dmso-d6“, „(CD3)2SO“, „Chloroform-d“) -> Schreibweise der SI
    („DMSO-d6“, „CDCl3“); unbekannt -> unverändert."""
    key = IMP.solvent_key(name)
    return SOLVENT_SI.get(key, key) if key else (name or "").strip()


def solvent_markup(s):
    """CDCl3 -> CDCl_{3}, DMSO-d6 -> DMSO-*d*_{6}, (CD3)2SO -> (CD_{3})_{2}SO (wie tabs/nmr.py); Zeichen des Markups
    im Namen werden maskiert."""
    s = re.sub(r"-d(\d+)\b", r"-*d*_{\1}", esc(s.strip()))
    return re.sub(r"(?<=[A-Za-z)])(\d+)", r"_{\1}", s)


def _couplings(J, st):
    out, k = [], 0
    while k < len(J):                                     # gleiche Bezeichnung hintereinander: „J = a, b Hz“
        e = k
        while e < len(J) and J[e].label() == J[k].label():
            e += 1
        out.append(st.j_tpl.format(label=_jlabel(J[k]), list=st.j_sep.join(_num(c.hz, st.j_digits) for c in J[k:e])))
        k = e
    return st.m_sep.join(out)


def signal_markup(sig, d, st=SI_STYLE):
    if not sig.printable:                                 # Vorschlag oder nicht gemessen: nie δ oder J drucken
        if sig.lo is None:
            raise ValueError(T("b2nmr_unconfirmed"))
        sig = Signal(lo=sig.lo, hi=sig.hi, mult="m", nH=sig.nH, assign=sig.assign)
    if sig.is_range:
        pos = st.range_tpl.format(hi=_num(sig.hi, d, st.minus), lo=_num(sig.lo, d, st.minus))
    else:
        pos = _num(sig.shift, d, st.minus)
    mult = st.broad_tpl.format(mult=sig.mult).strip() if sig.broad else sig.mult
    parts = {"mult": mult, "J": _couplings(sig.J, st) if sig.J else "",
             "nH": f"{sig.nH:g}H" if sig.nH is not None else "", "assign": esc(sig.assign)}
    inner = st.m_sep.join(parts[k] for k in st.order if parts[k])
    return pos + (f" ({inner})" if inner else "")


def head_markup(spec, st=SI_STYLE):
    cond = f"{spec.freq:g} MHz, {solvent_markup(spec.solvent)}" + (f", {spec.temp:g} K" if spec.temp is not None else "")
    nuc = nucleus_markup(spec.nucleus) + re.sub(r"\{(\d+)([A-Z][a-z]?)\}", r"{^{\1}\2}", esc(spec.dec))
    return st.head.format(nuc=nuc, cond=cond)


def sorted_signals(spec, st=SI_STYLE):
    if not st.sort:
        return list(spec.signals)
    return sorted(spec.signals, key=lambda s: s.centre, reverse=st.sort == "desc")


def format_markup(spec, st=SI_STYLE):
    d = st.digits_for(spec)
    return head_markup(spec, st) + st.m_sep.join(signal_markup(s, d, st) for s in sorted_signals(spec, st))


def format_plain(spec, st=SI_STYLE):
    return plain(format_markup(spec, st))


def signal_of(m, n_h=None, assign="", rng=None, confirmed=False):
    """Ergebnis aus `nmr_analysis` -> Signal: Multiplett (`multiplets`) oder Fit (`fit_pattern`, mit `unmeasured`), beide
    dict mit lo, hi, shift, mult, J; None = Fit mit Meldung -> Bereich `rng` = (lo, hi) des Nutzers als „m“.
    δ und J sind Vorschläge (SUGGESTED), mit `confirmed=True` (Nutzer hat bestätigt) CONFIRMED; J aus `unmeasured`
    bleiben UNMEASURED und machen auch δ UNMEASURED (Bestätigen hebt das nicht auf)."""
    if m is None:
        lo, hi = sorted(rng)
        return Signal(lo=lo, hi=hi, mult="m", nH=n_h, assign=assign, status=SUGGESTED)
    st = CONFIRMED if confirmed else SUGGESTED
    lo, hi = sorted((m["lo"], m["hi"]))
    if m["mult"] == "m":
        return Signal(lo=lo, hi=hi, mult="m", nH=n_h, assign=assign, status=st)
    un, J = list(m.get("unmeasured", ())), []
    for j in m["J"]:
        J.append(Coupling(j, status=UNMEASURED if j in un else st))
        if j in un:
            un.remove(j)
    return Signal(shift=m["shift"], lo=lo, hi=hi, mult=m["mult"], J=J, nH=n_h, assign=assign,
                  status=UNMEASURED if any(c.status == UNMEASURED for c in J) else st)


# ---------------------------------------------------------------------------- Lesen
_HEAD = re.compile(r"(?P<mass>\d{1,3})(?P<el>[A-Z][a-z]?)(?P<dec>\{[^}]*\})?\s*NMR\s*\((?P<cond>(?:[^()]|\([^()]*\))*)\)\s*:?\s*"
                   r"(?:δ\s*(?:\[\s*ppm\s*\]|\(\s*ppm\s*\))?\s*[=:]?\s*)?(?=[-−]?\d)")
_NUM = r"[-−]?\d+(?:\.\d+)?"
_ENTRY = re.compile(rf"(?P<a>{_NUM})(?:\s*[–—-]\s*(?P<b>{_NUM}))?(?![A-Za-z\d])")   # „13C NMR“ ist kein Eintrag
_JTOK = re.compile(r"^(?P<bonds>\d)?\s*J\s*(?:\(?(?P<partner>[A-Z][a-z]?\s*,\s*[A-Z][a-z]?)\)?)?\s*=\s*(?P<v>.*)$")
_HZ = re.compile(r"^(?P<v>\d+(?:\.\d+)?)\s*(?P<hz>Hz)?$")
_NH = re.compile(r"^(?P<n>\d+(?:\.\d+)?)\s*H$")


def _f(s):
    return float(s.replace("−", "-"))


def _decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def split_top(s, sep=","):
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch in "([{"
        depth -= ch in ")]}"
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out]


def _closing(s, i):
    """s[i] == '(' -> Index nach der passenden ')'; unbalanciert (vorher „;“ oder Textende) -> None."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == ";":
            return None
        depth += {"(": 1, ")": -1}.get(s[j], 0)
        if depth == 0:
            return j + 1
    return None


def parse_inner(text):
    """„dd, J = 8.1, 1.2 Hz, 1H, Ar-H“ -> dict(mult, broad, J, nH, assign)."""
    # das Komma im Partner („1JC,F = …“) trennt nicht
    text = re.sub(r"(\d?\s*J\s*\(?[A-Z][a-z]?)\s*,\s*([A-Z][a-z]?\)?\s*=)", "\\1\0\\2", text)
    toks = [t.replace("\0", ",") for t in split_top(text) if t]
    out = dict(mult="", broad=False, J=[], nH=None, assign="")
    rest, k = [], 0
    if toks:
        m = re.match(r"^(?:br\.?\s*)(?P<c>.*)$", toks[0])
        c = m.group("c").strip() if m else toks[0]
        if m and not c:                                   # nur „br“
            out.update(broad=True, mult="s")
            k = 1
        elif _CLASS_RE.match(c):
            out.update(broad=bool(m), mult=c)
            k = 1
    while k < len(toks):
        t = toks[k]
        mj = _JTOK.match(t)
        if mj:
            bonds = int(mj.group("bonds")) if mj.group("bonds") else None
            partner = re.sub(r"\s+", "", mj.group("partner") or "")
            vals, cur = [], mj.group("v")
            while True:
                mv = _HZ.match(cur.strip())
                if not mv:
                    break
                vals.append(float(mv.group("v")))
                if mv.group("hz") or k + 1 >= len(toks) or not _HZ.match(toks[k + 1]):
                    break
                k += 1
                cur = toks[k]
            if vals:
                out["J"] += [Coupling(v, bonds, partner, CONFIRMED) for v in vals]
                k += 1
                continue
        mh = _NH.match(t)
        if mh and out["nH"] is None:
            out["nH"] = float(mh.group("n"))
        else:
            rest.append(t)
        k += 1
    out["assign"] = ", ".join(rest)
    return out


def parse_spans(text):
    """Alle NMR-Zeilen in `text` -> [(Spectrum, Anfang, Ende)]; Ende = nach dem letzten Signal (ohne Satzzeichen).
    Nachsichtig (fehlendes Komma vor „x.x (…)“, „3 H“, „br.s“, offene Klammer bis „;“, Kopf ohne „δ [ppm] =“), Ausgabe
    immer in Normalform."""
    res = []
    for m in _HEAD.finditer(text):
        cond = [c.strip() for c in m.group("cond").split(",")]
        mf = re.match(r"([\d.]+)\s*MHz", cond[0])
        if not mf:
            continue
        temp = next((float(re.match(r"[\d.]+", c).group()) for c in cond[2:] if re.fullmatch(r"[\d.]+\s*K", c)), None)
        spec = Spectrum(f"{m.group('mass')}{m.group('el')}", float(mf.group(1)),
                        cond[1] if len(cond) > 1 else "", temp, m.group("dec") or "")
        i, end, decs = m.end(), m.end(), []
        while True:
            me = _ENTRY.match(text, i)
            if not me:
                break
            a, b = me.group("a"), me.group("b")
            decs += [_decimals(a)] + ([_decimals(b)] if b else [])
            j = me.end()
            js = re.match(r"\s*", text[j:]).end() + j
            inner = {}
            if js < len(text) and text[js] == "(":
                k = _closing(text, js)
                if k is None:                             # unbalanciert: Signal endet vor dem nächsten „;“
                    k = text.find(";", js)
                    k = len(text) if k < 0 else k
                    inner, j = parse_inner(text[js + 1:k]), js + 1 + len(text[js + 1:k].rstrip())
                else:
                    inner, j = parse_inner(text[js + 1:k - 1]), k
            sig = Signal(**inner, status=CONFIRMED)
            if b:
                sig.lo, sig.hi = sorted((_f(a), _f(b)))     # tief–hoch behält die Bedeutung; Ausgabe hoch – tief
            else:
                sig.shift = _f(a)
            spec.signals.append(sig)
            end = j
            mc = re.match(r"\s*,\s*|\s+(?=\S+\s*\()", text[j:])   # fehlendes Komma vor „x.x (…)“
            if not mc or not _ENTRY.match(text, j + mc.end()):
                break
            i = j + mc.end()
        if spec.signals:
            spec.digits = max(set(decs), key=lambda x: (decs.count(x), x))
            res.append((spec, m.start(), end))
    return res


def parse(text):
    return [s for s, _, _ in parse_spans(text)]


def class_j_count(sig):
    """Erwartete Zahl der J für eine Klasse erster Ordnung (dd -> 2, td -> 2, s -> 0); None für m/unbekannt."""
    c = sig.mult
    if c in ("s", ""):
        return 0
    if c == "m":
        return None
    if c in _LETTER_N:
        return 1
    return len(c) if re.fullmatch(r"[dtqp]+", c) else None
