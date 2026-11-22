"""elucida/tabs/ir_ea.py - IR-Peakliste und HRMS-Zeile für die SI, Tab „IR + MS“.

IR:  Bruker OPUS (Binärdatei *.0, *.1 …: Spektrum + Parameterblock) oder OPUS-PDF-Ausdruck (Peakwerte als Text).
     Peaksuche in Rohdaten: Minima der Transmission (bzw. Maxima der Absorbanz) mit Mindest-Prominenz relativ zur
     stärksten Bande; Intensität optional w/m/s nach relativer Tiefe, br bei Halbwertsbreite > BROAD_CM.
MS:  Auftragsformular der Massenabteilung (Word, *.docx): Formel und Ionisierung aus dem Text, gemessene m/z aus den
     Beschriftungen der eingebetteten Spektren (EMF, EMR_EXTTEXTOUTW). calc. = monoisotopische Masse des Ions mit
     Elektronenmasse (z. B. [M+H]⁺ = M + m(H) − mₑ = M + 1.007276).
"""
from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

import numpy as np
from elucida.formats.opus import (read_opus, is_opus, is_opus_pdf, read_ir_pdf, read_ir_pdf_curve)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.ms_report import (read_ms_docx, _emf_texts, cdx_structure)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.elements import ELEMENTS  # noqa: E402
from elucida.formats.bruker_ms import (read_bruker_d, is_bruker_d, BAF_LINE_MAGIC, BAF_TRANSFORMATOR, _baf_mz)  # noqa: E402,F401  (Leser in elucida/formats)

# ---------------------------------------------------------------------------- Massen
ELECTRON = 0.000548579909
MONO = {  # häufigstes Isotop, IUPAC/AME
    "H": 1.00782503207, "D": 2.0141017778, "B": 11.0093054, "C": 12.0, "N": 14.0030740048, "O": 15.99491461956,
    "F": 18.99840322, "Na": 22.9897692809, "Mg": 23.985041700, "Al": 26.98153863, "Si": 27.9769265325,
    "P": 30.97376163, "S": 31.97207100, "Cl": 34.96885268, "K": 38.96370668, "Ca": 39.96259098,
    "Fe": 55.9349375, "Co": 58.9331950, "Ni": 57.9353429, "Cu": 62.9295975, "Zn": 63.9291422, "Se": 79.9165213,
    "Br": 78.9183371, "Ru": 101.9043493, "Rh": 102.905504, "Pd": 105.903486, "Ag": 106.905097, "Sn": 119.9021947,
    "I": 126.904473, "Pt": 194.9647911, "Au": 196.9665687, "Li": 7.01600455, "Cs": 132.905451933, "Ge": 73.9211778,
    "Te": 129.9062244, "Bi": 208.9803987, "Ti": 47.9479463, "Mn": 54.9380451, "Cr": 51.9405075,
}
_FTOK = re.compile(r"(?:\[(\d+)([A-Z][a-z]?)\]|([A-Z][a-z]?))(\d*)|(\()|\)(\d*)")
NO_NATURAL = {"Tc", "Pm", "Po", "At", "Rn"}          # ohne stabile Isotope: Masse nur mit Massenzahl
_ISO = re.compile(r"\[(\d+)([A-Z][a-z]?)\]")


def _formula_part(s: str) -> dict:
    stack = [{}]
    pos = 0
    while pos < len(s):
        m = _FTOK.match(s, pos)
        if not m:
            raise ValueError(f"Summenformel nicht lesbar: {s}")
        pos = m.end()
        if m.group(5):                               # „(“
            stack.append({})
        elif m.group(0).startswith(")"):
            if len(stack) == 1:
                raise ValueError(f"Summenformel nicht lesbar: {s}")
            grp, k = stack.pop(), int(m.group(6) or 1)
            for el, n in grp.items():
                stack[-1][el] = stack[-1].get(el, 0) + n * k
        else:
            sym = m.group(3) or m.group(2)
            if sym not in ELEMENTS and sym != "D":
                raise ValueError(f"Element {sym} nicht bekannt")
            if sym in NO_NATURAL and not m.group(2):
                raise ValueError(f"Element {sym} ohne natürliche Isotope: Massenzahl angeben, z. B. [99{sym}]")
            el = m.group(3) or f"[{m.group(1)}{m.group(2)}]"     # Isotop wie RDKit: [13C]
            stack[-1][el] = stack[-1].get(el, 0) + int(m.group(4) or 1)
    if len(stack) != 1:
        raise ValueError(f"Summenformel nicht lesbar: {s}")
    return stack[0]


_FTOKS = r"(?:\[\d+[A-Z][a-z]?\]|[A-Z][a-z]?\d*|\(|\)\d*)+"             # Formel aus Elementen/Isotopen/Klammern
# Teil eines Salzes: [Anzahl] Formel Ladung | [Anzahl] [Formel]Ladung („2[PF6]-“, „[C8H22N2]2+“); ohne eckige Klammer
# ist eine Ziffer vor dem Zeichen Index („PF6-“, Ladung = Zahl der Zeichen), außer am einatomigen Ion („Fe2+“, „O2-“; Entsch. 191)
_SALT_PART = re.compile(rf"[·•]?(\d*)(?:\[({_FTOKS})\](\d*)|({_FTOKS}))(\++|[\-−]+)")


def salt_parts(text: str) -> list:
    """Salzschreibweise 'C10H16N+ Br-', '[C10H16N]+[PF6]-', 'C10H16N+·PF6-', '[C8H22N2]2+ 2[PF6]-', 'Fe2+ 2Cl-',
    'Na+ SO4 2-' -> [(Formel, Ladung, Anzahl)]; keine Salzschreibweise (höchstens eine Ladung am Ende) -> []. Lässt sie
    sich nicht ganz oder nicht eindeutig lesen („SO42-“) -> ValueError (nie still einen Teil weglassen oder raten)."""
    from elucida.app.i18n import T
    from elucida.core.chem import ambiguous_count, monatomic
    s = str(text).strip()
    s = re.sub(rf"(^|[\s·•])(\d*)({_FTOKS})\s+(\d+)(?=[+\-−])", r"\1\2[\3]\4", s)    # „SO4 2-“ = [SO4]2-
    s = s.replace(" ", "")
    if not re.search(r"[+\-−]\d*[^\d+\-−]", s):
        return []
    out, pos = [], 0
    while pos < len(s):
        m = _SALT_PART.match(s, pos)
        if not m or (m.group(3) and len(m.group(5)) > 1):
            raise ValueError(T("formula_salt_bad", f=text))
        f, z = m.group(2) or m.group(4), int(m.group(3)) if m.group(3) else len(m.group(5))
        tail = re.fullmatch(r"(.*?)(\d+)", f) if m.group(4) else None
        if tail and ambiguous_count(tail.group(1), tail.group(2)):
            raise ValueError(T("formula_salt_bad", f=text))
        if tail and len(m.group(5)) == 1 and monatomic(tail.group(1), m.group(5)):
            f, z = tail.group(1), int(tail.group(2))
        out.append((f, z if m.group(5)[0] == "+" else -z, int(m.group(1) or 1)))
        pos = m.end()
    return out


def parse_formula(text: str) -> dict:
    """'C20H15N3' / 'C18H18N2O+' / 'Ca(OH)2' / 'C18H18N2O·2H2O' / '[13C]H4' (Isotope wie RDKit) -> {'C': 20, …,
    '[13C]': 1}; Ladung am Ende wird ignoriert (kommt vom Addukt). Salz ('[C10H16N]+[PF6]-', `salt_parts`): alle Teile
    zusammen. Hydrat-Trenner wie bisher „·“, „•“, „*“. Nicht lesbare Teile -> ValueError."""
    parts = salt_parts(text)
    if parts:
        out = {}
        for f, _, k in parts:
            for el, n in _formula_part(f).items():
                out[el] = out.get(el, 0) + n * k
        return out
    text = re.sub(r"[+\-−]+\d*$", "", str(text).replace(" ", ""))
    out = {}
    for part in re.split(r"[·•*]", text):
        m = re.fullmatch(r"(\d+)?(.+)", part)
        if not m:
            raise ValueError(f"Summenformel nicht lesbar: {text}")
        k = int(m.group(1) or 1)
        for el, n in _formula_part(m.group(2)).items():
            out[el] = out.get(el, 0) + n * k
    if not out:
        raise ValueError("keine Summenformel")
    return out


# Benannte Gruppen in Ionenausdrücken (eigenes Ion, Fremdpeak-Liste): Lösungsmittel/Anionen als Summenformel
ION_GROUPS = {"MeOH": "CH4O", "MeCN": "C2H3N", "ACN": "C2H3N", "H2O": "H2O", "HCOO": "CHO2", "DMSO": "C2H6OS",
              "FA": "CH2O2", "CH3COO": "C2H3O2", "AcO": "C2H3O2", "NH4": "NH4"}
# Ladung, die eine Gruppe mitbringt (+X: z += q, −X: z −= q); alles andere gilt als neutral
ION_CHARGES = {"H": 1, "Li": 1, "Na": 1, "K": 1, "NH4": 1, "Ag": 1, "Cs": 1, "Cl": -1, "Br": -1, "I": -1,
               "HCOO": -1, "CH3COO": -1, "AcO": -1}
_ION_RE = re.compile(r"\[?\s*(\d*)\s*M((?:\s*[+\-−]\s*\d*\s*[A-Za-z][A-Za-z0-9()]*)*)\s*\]?")
_ION_TERM = re.compile(r"([+\-−])(\d*)([A-Za-z][A-Za-z0-9()]*)")


def parse_ion(spec: str):
    """Ionenausdruck „M+Na+MeOH“, „2M+H“, „M-H2O+H“, „[M+2H]“, „nM+HCOO“ (n = Reihe, zählt 1) -> (k, Änderung der
    Formel, Ladung aus den Gruppen, Anzeige mit $_n$ für tiefe Ziffern). Gruppen: ION_GROUPS oder Summenformel.
    Nicht lesbar -> ValueError."""
    s = str(spec).strip().replace(" ", "")
    s = re.sub(r"^n(?=M)", "", s)
    m = _ION_RE.fullmatch(s)
    if not m:
        raise ValueError(f"Ion nicht lesbar: {spec}")
    k = int(m.group(1) or 1)
    delta, z = {}, 0
    for sign, mult, grp in _ION_TERM.findall(m.group(2)):
        f = (-1 if sign != "+" else 1) * int(mult or 1)
        counts = _formula_part(ION_GROUPS.get(grp, grp))
        for el, n in counts.items():
            delta[el] = delta.get(el, 0) + f * n
        z += f * ION_CHARGES.get(grp, 0)
    body = "".join(f"{'+' if sign == '+' else '−'}{mult}{re.sub(r'(?<=[A-Za-z)])(\d+)', r'$_\1$', grp)}"
                   for sign, mult, grp in _ION_TERM.findall(m.group(2)))
    return k, {el: n for el, n in delta.items() if n}, z, f"[{k if k > 1 else ''}M{body}]"


def _adduct(spec, z):
    k, delta, _, label = parse_ion(spec)
    return label, delta, z, k


# Addukt: (Anzeige, Änderung der Formel, Ladung, Anzahl M); Ladung > 1 und 2M rechnet `ion`
ADDUCTS = {key: _adduct("M" if key == "M-" else key, z) for key, z in (
    ("M+H", 1), ("M+Na", 1), ("M+K", 1), ("M+NH4", 1), ("M", 1), ("M+H+MeOH", 1), ("M+Na+MeOH", 1),
    ("M+H+H2O", 1), ("M+H-H2O", 1), ("M+H+MeCN", 1), ("M+2H", 2), ("2M+H", 1), ("2M+Na", 1),
    ("M-H", -1), ("M+Cl", -1), ("M+HCOO", -1), ("M-", -1))}


def adduct_def(adduct):
    """Schlüssel aus ADDUCTS oder eigenes Ion (Ausdruck, Ladung) -> (Anzeige, Änderung, Ladung, Anzahl M)."""
    if isinstance(adduct, str) and adduct in ADDUCTS:
        return ADDUCTS[adduct]
    spec, z = (adduct, None) if isinstance(adduct, str) else adduct
    k, delta, zg, label = parse_ion(spec)
    z = int(zg if z is None else z)
    if not z:
        raise ValueError(f"Ion ohne Ladung: {spec}")
    return label, delta, z, k


def part_adduct(key, q):
    """Addukt aus ADDUCTS auf einem geladenen Teil eines Salzes (Ladung q) -> eigenes Ion (Ausdruck, Ladung): [M] trägt
    die Ladung des Teils, Gruppen ändern sie ([M+H]2+ eines Kations). None, wenn es keinen Sinn ergibt (Ladung 0,
    Vorzeichen gewechselt, mehrere M)."""
    spec = "M" if key == "M-" else key
    k, _, zg, _ = parse_ion(spec)
    z = q + zg
    return (spec, z) if k == 1 and z and (z > 0) == (q > 0) else None


def charge_text(z: int) -> str:
    """Ladung als Hochzahl-Text: +, −, 2+, 3−."""
    return (f"{abs(z)}" if abs(z) > 1 else "") + ("+" if z > 0 else "−")


def label_text(label: str, mode="plain") -> str:
    """Anzeige eines Addukts ($_n$ = tiefe Ziffern) als Klartext, HTML oder mit Unicode-Indizes (Oberfläche)."""
    if mode == "html":
        return re.sub(r"\$_(\d+)\$", r"<sub>\1</sub>", label)
    if mode == "ui":
        return re.sub(r"\$_(\d+)\$", lambda m: m.group(1).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")), label)
    return re.sub(r"\$_(\d+)\$", r"\1", label)


def adduct_ui(adduct) -> str:
    """„[M+NH₄]⁺“, „[M+2H]²⁺“ für Auswahllisten und Tabellen."""
    label, _, z, _ = adduct_def(adduct)
    sup = charge_text(z).translate(str.maketrans("0123456789+−", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻"))
    return label_text(label, "ui") + sup


def element_of_key(key: str) -> str:
    """'[13C]' -> 'C', 'C' -> 'C'."""
    m = _ISO.fullmatch(key)
    return m.group(2) if m else key


def mono_mass(key: str) -> float:
    """Monoisotopische Masse: Tabelle MONO, sonst häufigstes Isotop aus RDKit; '[13C]' = Masse des Isotops."""
    if key in MONO:
        return MONO[key]
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    m = _ISO.fullmatch(key)
    mass = (pt.GetMassForIsotope(pt.GetAtomicNumber(m.group(2)), int(m.group(1))) if m
            else pt.GetMostCommonIsotopeMass(pt.GetAtomicNumber(key)))
    if not mass > 0:
        raise ValueError(f"keine Masse für {key}")
    return float(mass)


def formula_str(counts: dict) -> str:
    """Hill-Reihenfolge: C, H, dann alphabetisch (Isotope beim Element)."""
    def order(k):
        el = element_of_key(k)
        r = {"C": 0, "H": 1, "D": 2}.get(el, 3)
        return (r, el if r == 3 else "", k)
    keys = sorted((k for k in counts if counts[k]), key=order)
    return "".join(f"{k}{counts[k] if counts[k] != 1 else ''}" for k in keys)


def formula_html(f: str) -> str:
    """'[13C]H5' -> <sup>13</sup>CH<sub>5</sub>."""
    return re.sub(r"\[(\d+)([A-Z][a-z]?)\]|(\d+)",
                  lambda m: f"<sup>{m.group(1)}</sup>{m.group(2)}" if m.group(1) else f"<sub>{m.group(3)}</sub>", f)


def ion(formula: str, adduct="M+H"):
    """-> (Ionenformel ohne Ladung, Ladung z, m/z calc, Addukt-Anzeige); m/z = (k·M + Δ − z·mₑ)/|z|. adduct: Schlüssel
    aus ADDUCTS oder eigenes Ion (Ausdruck, Ladung)."""
    label, delta, z, k = adduct_def(adduct)
    counts = {el: n * k for el, n in parse_formula(formula).items()}
    for el, n in delta.items():
        counts[el] = counts.get(el, 0) + n
    if any(v < 0 for v in counts.values()) or not any(counts.values()):
        raise ValueError("Addukt passt nicht zur Formel")
    m = sum(mono_mass(el) * n for el, n in counts.items()) - z * ELECTRON
    return formula_str(counts), z, m / abs(z), label


def ppm(found, calc):
    return (found - calc) / calc * 1e6


# ---------------------------------------------------------------------------- IR: OPUS


# ---------------------------------------------------------------------------- IR: PDF
AXIS_TICKS = {0, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 100}


# ---------------------------------------------------------------------------- IR: Peaksuche und Text
BROAD_CM = 120.0                                    # Halbwertsbreite, ab der eine Bande „br“ heißt (O–H, N–H)


def pick_peaks(wn, y, kind="T", lo=None, hi=None, prominence=0.05, min_dist=4.0):  # noqa: C901
    """Banden im Bereich [lo, hi] (cm⁻¹): Tiefe d = 100 − T (bzw. A), lokale Maxima von d mit Prominenz
    ≥ prominence · max(d). rel (w/m/s) = Tiefe in T relativ zur stärksten Bande des ganzen Spektrums.
    -> [dict(wn, depth, rel, width)] absteigend nach Wellenzahl."""
    wn, y = np.asarray(wn, float), np.asarray(y, float)
    d = (100.0 - y) if kind == "T" else y.copy()
    lo = float(np.nanmin(wn)) if lo is None else lo
    hi = float(np.nanmax(wn)) if hi is None else hi
    sel = (wn >= min(lo, hi)) & (wn <= max(lo, hi)) & np.isfinite(d)
    if sel.sum() < 5:
        return []
    o = np.argsort(wn[sel])
    x, dd = wn[sel][o], d[sel][o]
    base = float(np.percentile(dd, 5))
    dd = dd - base
    dmax = float(dd.max()) or 1.0
    step = float(np.median(np.diff(x))) or 1.0
    win = max(1, int(round(min_dist / step)))
    out = []
    for i in range(1, len(x) - 1):
        a, b = max(0, i - win), min(len(x), i + win + 1)
        if dd[i] < dd[a:b].max() or dd[i] <= 0 or dd[i] == dd[i - 1]:     # Plateau: nur am Anfang
            continue
        j = i                                        # gesättigte Bande (flache Spitze): Mitte des Plateaus
        while j < len(x) - 1 and dd[j + 1] == dd[i]:
            j += 1
        # Prominenz: Tiefe über dem höheren der beiden seitlichen Minima bis zur nächsten tieferen Bande
        left = dd[:i][::-1]
        right = dd[i + 1:]
        def side_min(arr):
            m = dd[i]
            for v in arr:
                if v > dd[i]:
                    break
                m = min(m, v)
            return m
        prom = dd[i] - max(side_min(left), side_min(right))
        if prom < prominence * dmax:
            continue
        half = dd[i] / 2                             # Halbwertsbreite für „br“
        l_, r_ = i, i
        while l_ > 0 and dd[l_] > half:
            l_ -= 1
        while r_ < len(x) - 1 and dd[r_] > half:
            r_ += 1
        xi = float(x[i] + x[j]) / 2                  # Lage zwischen den Messpunkten per Parabel (wie OPUS)
        den = dd[i - 1] - 2 * dd[i] + dd[i + 1]
        if den < 0 and j == i:
            xi += 0.5 * (dd[i - 1] - dd[i + 1]) / den * (x[i + 1] - x[i - 1]) / 2
        out.append({"wn": xi, "depth": float(dd[i]), "rel": float(dd[i] / dmax),
                    "width": float(x[r_] - x[l_])})
    # gleiche Wellenzahl nach Rundung nur einmal
    seen, uniq = set(), []
    for p in sorted(out, key=lambda p: -p["wn"]):
        k = round(p["wn"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    # w/m/s wie üblich: Tiefe im Transmissionsspektrum (100 − T, auch bei Absorbanzdateien) relativ zur stärksten
    # Bande des ganzen gemessenen Spektrums – unabhängig vom gewählten Bereich
    dT = 100.0 - (y if kind == "T" else to_transmission(y))
    ok = np.isfinite(dT)
    if uniq and ok.sum() >= 5:
        o2 = np.argsort(wn[ok])
        xs, ds = wn[ok][o2], dT[ok][o2]
        ds = ds - float(np.percentile(ds, 5))
        dmx = float(ds.max()) or 1.0
        for p in uniq:
            p["rel"] = float(np.interp(p["wn"], xs, ds)) / dmx
    return uniq


OPUS_BASE = (128, 50)        # Stützpunkte und Iterationen (OPUS BPO/BIO), falls der Verlauf keine nennt


def _lower_hull(x, y):
    h = []
    for p in zip(x, y):
        while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
            h.pop()
        h.append(p)
    return np.array(h)


def concave_rubberband(wn, a, points=OPUS_BASE[0], iters=OPUS_BASE[1]):
    """Basislinie wie OPUS „Baseline Method 3“ (konkaves Gummiband, Bruker-Patent US 7359815): je Iteration eine
    Parabel F·((x − Mitte)/(Rand − Mitte))² addieren, F = Spannweite/2.2, dann das Gummiband (untere Hülle der Minima
    von `points` Abschnitten) abziehen. a = Absorbanz -> Basislinie (Rohspektrum − Ergebnis), NaN bleibt NaN.
    Faktor 1/2.2 statt 1/10 aus dem Patent: an einem OPUS-8.5-Bericht angepasst (RMS 0.05 %T, max. 0.4 %T)."""
    wn, a = np.asarray(wn, float), np.asarray(a, float)
    ok = np.isfinite(a) & np.isfinite(wn)
    out = np.full_like(a, np.nan)
    if ok.sum() < 3:
        return out
    o = np.argsort(wn[ok])
    x, y = wn[ok][o], a[ok][o]
    par = ((x - (x[0] + x[-1]) / 2) / ((x[-1] - x[0]) / 2)) ** 2
    parts = np.array_split(np.arange(len(x)), max(1, min(int(points), len(x))))
    z = y.copy()
    for _ in range(max(1, int(iters))):
        z = z + (z.max() - z.min()) / 2.2 * par
        mi = sorted({0, len(x) - 1, *(int(i[np.argmin(z[i])]) for i in parts)})
        h = _lower_hull(x[mi], z[mi])
        z = z - np.interp(x, h[:, 0], h[:, 1])
    base = np.empty_like(y)
    base[o] = y - z
    out[ok] = base
    return out


def baseline_corrected(sp):
    """Spektrum mit abgezogener OPUS-Basislinie (Stützpunkte/Iterationen aus dem OPUS-Verlauf, sonst OPUS_BASE);
    gerechnet in Absorbanz, zurück in der Einheit der Datei. Ändert nur die Anzeige/Peaksuche, nie die Datei."""
    h = sp.get("baseline") or {}
    pts, its = (h.get("BPO", OPUS_BASE[0]), h.get("BIO", OPUS_BASE[1])) if h.get("BME") == 3 else OPUS_BASE
    y = np.asarray(sp["y"], float)
    a = y if sp["kind"] == "A" else to_absorbance(y)
    a2 = a - concave_rubberband(sp["wn"], a, pts, its)
    y2 = a2 if sp["kind"] == "A" else to_transmission(a2)
    return dict(sp, y=np.where(np.isfinite(a2), y2, y))


def threshold_peaks(sp, line, lo=None, hi=None):
    """Peaks jenseits der Schwellenlinie (FB-15): line = [[ṽ, A], …] stückweise linear (außerhalb waagrecht), Peak =
    lokales Maximum der Absorbanz bzw. Minimum der Transmission oberhalb bzw. unterhalb der Linie. Kleine Prominenz
    (THR_PROM) nur gegen Rauschspitzen."""
    pk = pick_peaks(sp["wn"], sp["y"], sp["kind"], lo, hi, THR_PROM)
    if not pk or not line:
        return pk
    lx, ly = np.array(sorted(line)).T
    o = np.argsort(sp["wn"])
    y = np.asarray(sp["y"], float)[o]
    a = y if sp["kind"] == "A" else to_absorbance(y)
    return [p for p in pk if np.interp(p["wn"], sp["wn"][o], a) > np.interp(p["wn"], lx, ly)]


THR_PROM = 0.005


def to_absorbance(t_pct):
    """A = −log10(T/100); T ≤ 0 (Rauschen bei Totalabsorption) -> NaN statt ±∞ (Lücke in der Kurve)."""
    t = np.asarray(t_pct, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        a = -np.log10(t / 100.0)
    a[~(t > 0)] = np.nan
    return a


def to_transmission(a):
    """T [%] = 100 · 10^(−A)."""
    return 100.0 * np.power(10.0, -np.asarray(a, float))


def display_y(sp, mode):
    """Spektrum in der gewählten Darstellung (T = Transmission in %, A = Absorbanz). Die Peaksuche läuft immer auf
    den Originaldaten (pick_peaks mit sp["kind"]), die Darstellung ändert nur das Bild."""
    y = np.asarray(sp["y"], float)
    if mode == sp["kind"]:
        return y
    return to_absorbance(y) if mode == "A" else to_transmission(y)


# Felder „y-Bereich“ je Darstellung: (Minimum, Maximum, Nachkommastellen, Schritt) und Vorgabe beim Abschalten von
# „auto“ ohne Bild
Y_SPIN = {"T": (0.0, 100.0, 0, 5.0), "A": (-1.0, 10.0, 2, 0.1)}
Y_DEFAULT = {"T": (0.0, 100.0), "A": (0.0, 1.0)}


def y_limits(y, mode, manual=None):
    """y-Grenzen [unten, oben] für das IR-Bild und ob ein eingegebener Bereich verworfen wurde.
    auto: %T oben 100 (bzw. höchster Messwert) + 2 % Luft, damit die Basislinie bei 100 % nicht im Rahmen verschwindet
    (Nutzerwunsch P10), unten nach den Daten (Platz für Labels schafft
    IRFigure); Absorbanz unten 0 (bzw. tiefster Wert, falls negativ), oben nach den Daten.
    manual = (min, max): exakt übernommen, %T auf 0–100 begrenzt; min ≥ max -> verworfen (auto)."""
    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    ymin, ymaxv = (float(y.min()), float(y.max())) if len(y) else (0.0, 100.0 if mode == "T" else 1.0)
    span = ymaxv - ymin or 1.0
    if manual is not None:
        lo, hi = float(manual[0]), float(manual[1])
        if mode == "T":
            lo, hi = min(max(lo, 0.0), 100.0), min(max(hi, 0.0), 100.0)
        if lo < hi:
            return [lo, hi], False
    if mode == "T":
        lo = ymin - 0.08 * span
        hi = max(100.0, ymaxv) + 0.02 * span
    else:
        lo = min(0.0, ymin)
        hi = ymaxv + 0.05 * span
    if hi <= lo:
        hi = lo + 1.0
    return [lo, hi], manual is not None


def wn_text(v):
    """Wellenzahl als ganze Zahl, x.5 aufgerundet (round() rundet x.5 zur geraden Zahl)."""
    return f"{int(np.floor(v + 0.5)):d}"


def intensity_tag(p, broad=BROAD_CM):
    """w/m/s nach relativer Tiefe (≥ 0.6 s, ≥ 0.3 m), „br“ bei breiten Banden."""
    t = "s" if p["rel"] >= 0.6 else ("m" if p["rel"] >= 0.3 else "w")
    return ("br " + t) if p.get("width", 0) > broad else t


def ir_line(peaks, with_intensity=False):
    """-> (Klartext, HTML) wie in der SI: IR [cm⁻¹]: ṽ = 2961, 2866, … (ganze Zahlen, absteigend)."""
    vals = sorted(peaks, key=lambda p: -p["wn"])
    items = [wn_text(p["wn"]) + (f" ({intensity_tag(p)})" if with_intensity and "rel" in p else "") for p in vals]
    body = ", ".join(items)
    plain = f"IR [cm-1]: ṽ = {body}"
    html = f"<b>IR</b> [cm<sup>-1</sup>]: ṽ = {body}"                    # wie in der SI: „-1“
    return plain, html


# ---------------------------------------------------------------------------- MS-Bericht


# ---------------------------------------------------------------------------- MS: Bruker-Rohdaten (.d, BAF)


def lc_found(spectra, calc, tol_ppm=10.0, rt=None, frac=0.5):
    """m/z des gesuchten Ions über den LC-Peak: je Spektrum die Linie am nächsten an calc (innerhalb tol_ppm),
    Peak = zusammenhängende Spektren um das Maximum mit Intensität ≥ frac·Maximum (oder fester Zeitbereich rt).
    -> dict(mz intensitätsgewichtet, n, std_mda, lo, hi, rt_lo, rt_hi, xic) oder None."""
    tol = calc * tol_ppm * 1e-6
    xic = []
    for t, mz, inten in spectra:
        j = int(np.searchsorted(mz, calc))
        cand = [k for k in (j - 1, j) if 0 <= k < len(mz) and abs(mz[k] - calc) <= tol]
        k = max(cand, key=lambda k: inten[k]) if cand else None
        xic.append((t, float(mz[k]) if k is not None else np.nan, float(inten[k]) if k is not None else 0.0))
    xic = np.array(xic)
    if not (xic[:, 2] > 0).any():
        return None
    if rt is not None:                                 # 1e-6 s: Grenzen kommen über min zurück (Rundung)
        use = (xic[:, 0] >= min(rt) - 1e-6) & (xic[:, 0] <= max(rt) + 1e-6) & (xic[:, 2] > 0)
    else:
        top = int(np.argmax(xic[:, 2]))
        thr = frac * xic[top, 2]
        lo = hi = top
        while lo > 0 and xic[lo - 1, 2] >= thr:
            lo -= 1
        while hi < len(xic) - 1 and xic[hi + 1, 2] >= thr:
            hi += 1
        use = np.zeros(len(xic), bool)
        use[lo:hi + 1] = True
        use &= xic[:, 2] > 0
    if not use.any():
        return None
    m, w = xic[use, 1], xic[use, 2]
    mean = float(np.average(m, weights=w))
    return {"mz": mean, "n": int(use.sum()), "std_mda": float(np.sqrt(np.average((m - mean) ** 2, weights=w)) * 1000),
            "lo": float(m.min()), "hi": float(m.max()), "rt_lo": float(xic[use, 0].min()),
            "rt_hi": float(xic[use, 0].max()), "xic": xic}


def nearest(mz_list, calc, max_ppm=20.0):
    """Gemessenes m/z, das am nächsten an calc liegt (innerhalb max_ppm), sonst None."""
    best = min(mz_list, key=lambda v: abs(v - calc), default=None)
    return best if best is not None and abs(ppm(best, calc)) <= max_ppm else None


def ms_line(formula, adduct, found, ionisation="ESI"):
    """-> (Klartext, HTML): HR-MS-ESI(+) calc. C18H19N2O+ [M+H]+ 279.1492; found 279.1496. Ladung 2: „[C…]2+ [M+2H]2+“
    im Klartext (sonst liefe die Ladung in die letzte Ziffer der Formel), hochgestellt im HTML."""
    f_ion, z, calc, label = ion(formula, adduct)
    sign = charge_text(z)
    pol = "+" if z > 0 else "−"
    lab_plain = label_text(label)
    lab_html = label_text(label, "html")
    f_html = formula_html(f_ion)
    f_plain = f"[{f_ion}]" if abs(z) > 1 else f_ion
    tail = f"; found {found:.4f}." if found is not None else "; found –."
    plain = f"HR-MS-{ionisation}({pol}) calc. {f_plain}{sign} {lab_plain}{sign} {calc:.4f}{tail}"
    html = (f"<b>HR-MS-{ionisation}({pol})</b> calc. {f_html}<sup>{sign}</sup> {lab_html}<sup>{sign}</sup> "
            f"{calc:.4f}{tail}")
    return plain, html, calc


# ---------------------------------------------------------------------------- IR berechnet gegen gemessen (Paket B 1.2.0)
IRC_MIN_REL = 0.05          # berechnete Moden ab 5 % der stärksten im Bereich zählen für die automatische Zuordnung
IRC_COLOR = "#1764e8"


def calc_ir_profile(modes, scale, fwhm, x0, x1):
    """Berechnetes Spektrum im Bereich [x0, x1] -> (ṽ, Hüllkurve 0–1) oder None. modes [(ṽ, I)] werden mit `scale`
    multipliziert; fwhm [cm⁻¹] > 0: Lorentz-Profile (Höhe ∝ I, gemeinsame Halbwertsbreite), sonst Linienspektrum als
    Polylinie (Strich je Mode, Höhe I/I_max). Normiert auf das Maximum im Bereich."""
    lo, hi = min(x0, x1), max(x0, x1)
    m = [(w * scale, i) for w, i in modes if lo <= w * scale <= hi and i > 0]
    if not m:
        return None
    w = np.array([a for a, _ in m])
    inten = np.array([b for _, b in m])
    if fwhm and fwhm > 0:
        x = np.linspace(lo, hi, int(min(20000, max(2000, (hi - lo) / 0.5))))
        g = (fwhm / 2) ** 2
        env = (inten[:, None] * g / ((x[None, :] - w[:, None]) ** 2 + g)).sum(0)
        return x, env / env.max()
    o = np.argsort(w)
    x = np.repeat(w[o], 3)
    y = np.zeros_like(x)
    y[1::3] = inten[o] / inten.max()
    return np.r_[lo, x, hi], np.r_[0.0, y, 0.0]


def calc_ir_display(env, y_meas, mode):
    """Hüllkurve in die Darstellung der Messung: die stärkste berechnete Bande so tief/hoch wie die Spannweite der
    gemessenen Absorbanz, Grundlinie auf der gemessenen. Transmission: T = 100·10^(−A) (berechnetes Spektrum wird
    umgerechnet, nie die Messung)."""
    a = to_absorbance(y_meas) if mode == "T" else np.asarray(y_meas, float)
    lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
    calc_a = lo + np.asarray(env, float) * (hi - lo)
    return to_transmission(calc_a) if mode == "T" else calc_a


def assign_bands(meas, modes, scale, tol=None, manual=(), min_rel=IRC_MIN_REL):
    """Zuordnung gemessener Banden (ṽ) zu berechneten Moden -> [dict(meas, calc, diff, I, mode, how)], absteigend.
    manual: [[ṽ_gemessen gerundet, Modenindex]] gilt immer; automatisch (tol in cm⁻¹, None = aus) nur eindeutig: genau
    eine Mode ab min_rel der stärksten innerhalb ±tol, und diese Mode hat innerhalb ±tol nur diese eine Bande.
    diff = gemessen − berechnet (skaliert)."""
    meas = sorted({round(float(v)) for v in meas}, reverse=True)
    scaled = [(k, w * scale, i) for k, (w, i) in enumerate(modes)]
    imax = max((i for _, _, i in scaled), default=0.0)
    strong = [(k, w, i) for k, w, i in scaled if imax > 0 and i >= min_rel * imax]
    out, used_m, used_c = [], set(), set()
    for v, k in manual or ():
        if v in meas and 0 <= k < len(scaled) and v not in used_m and k not in used_c:
            out.append(dict(meas=v, calc=scaled[k][1], I=scaled[k][2], mode=k, how="manual"))
            used_m.add(v)
            used_c.add(k)
    if tol:
        free_m = [v for v in meas if v not in used_m]
        free_c = [(k, w, i) for k, w, i in strong if k not in used_c]
        for v in free_m:
            cand = [(k, w, i) for k, w, i in free_c if abs(w - v) <= tol]
            if len(cand) != 1:
                continue
            k, w, i = cand[0]
            if sum(1 for u in free_m if abs(w - u) <= tol) != 1:
                continue
            out.append(dict(meas=v, calc=w, I=i, mode=k, how="auto"))
    for r in out:
        r["diff"] = r["meas"] - round(r["calc"])
    return sorted(out, key=lambda r: -r["meas"])


# ---------------------------------------------------------------------------- Raman (1.2.0)
RAMAN_COLOR = "#1f7a3a"
RAMAN_VIEWS = ("ir", "raman", "stack")         # Abbildung des Tabs: IR, Raman oder beide übereinander
STACK_GAP = 0.12                               # Abstand der gestapelten Spektren (Anteil der normierten Höhe)


def exc_text(nm):
    """Anregungswellenlänge ohne überflüssige Stellen: 785, 632.8."""
    return f"{nm:.1f}".rstrip("0").rstrip(".")


def raman_line(peaks, exc=None):
    """-> (Klartext, HTML) wie in der SI: Raman (λexc = 785 nm): ṽ = 1601, 1175, … cm-1 (ganze Zahlen, absteigend)."""
    body = ", ".join(wn_text(p["wn"]) for p in sorted(peaks, key=lambda p: -p["wn"]))
    ex = f" (λexc = {exc_text(exc)} nm)" if exc else ""
    ex_h = f" (<i>λ</i><sub>exc</sub> = {exc_text(exc)} nm)" if exc else ""
    return f"Raman{ex}: ṽ = {body} cm-1", f"<b>Raman</b>{ex_h}: ṽ = {body} cm<sup>-1</sup>"


def norm01(y):
    """Auf 0–1 (Minimum–Maximum) für Peaksuche und gestapelte Darstellung; NaN bleibt NaN."""
    y = np.asarray(y, float)
    lo, hi = np.nanmin(y), np.nanmax(y)
    return (y - lo) / ((hi - lo) or 1.0)


# ----------------------------------------------------------------------------
# Tab „IR + MS“
# ----------------------------------------------------------------------------
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout,  # noqa: E402
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget)
import os  # noqa: E402

from elucida.si import lines as SI  # noqa: E402
from elucida.tabs import base as TABS  # noqa: E402
from elucida.app.i18n import T, T_en  # noqa: E402
from elucida.app import project as PRJ  # noqa: E402
from elucida.app.style import HINT_CSS, WARN_CSS, HintLabel, make_form, off_spin  # noqa: E402
from elucida.core import ocr as OCR  # noqa: E402
from elucida.formats.ms_report import header_line  # noqa: E402
IR_DOC_NUM = r"\d{3,4}([.,]\d{1,3})?"                  # ṽ in einem fremden Dokument (ganze Zahl oder 1–3 Nachkommastellen)
IR_DOC_RANGE = (350, 4500)

IR_COLOR = "#7a1a12"


def spread_centers(targets, widths, lo=0.0, hi=1.0):
    """Mittelpunkte nebeneinanderliegender Labels (Achsenbruchteile) so nah wie möglich an targets, ohne dass sich
    Labels der Breite widths überlappen: überlappende Labels bilden einen Block, der um den Mittelwert seiner Ziele
    zentriert wird; Blöcke bleiben in [lo, hi]."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    blocks = []                                          # [indices, start]

    def start_of(idx):
        off, acc = [], 0.0
        for i in idx:
            off.append(acc + widths[i] / 2)
            acc += widths[i]
        s = float(np.mean([targets[i] - o for i, o in zip(idx, off)]))
        return min(max(s, lo), max(lo, hi - acc))

    for i in order:
        blocks.append([[i], start_of([i])])
        while len(blocks) > 1:
            (ia, sa), (ib, sb) = blocks[-2], blocks[-1]
            if sa + sum(widths[k] for k in ia) <= sb:
                break
            blocks[-2:] = [[ia + ib, start_of(ia + ib)]]
    out = [0.0] * len(targets)
    for idx, s in blocks:
        for i in idx:
            out[i] = s + widths[i] / 2
            s += widths[i]
    return out


IR_LABEL_MIN_PT = 4.0                                    # kleinste Schrift der Wellenzahl-Labels
IR_LABEL_FILL = 0.8                                      # Labelreihe höchstens so breit (Anteil der Achse), sonst kleiner


class IRFigure(TABS.X.SimpleFigure):
    """IR-Abbildung wie der OPUS-Bericht (Nutzerwunsch P10, ohne Nachkommastellen): Wellenzahl-Labels senkrecht in
    einer Reihe am unteren Rand (Transmission) bzw. oberen Rand (Absorbanz), nebeneinander so nah wie möglich an ihrem
    Peak, dazwischen Hilfslinien zum Peak (senkrecht – schräg – senkrecht); die y-Achse wächst, bis das Spektrum
    jenseits der Hilfslinien bleibt. Gespeicherte (gezogene) Positionen haben Vorrang (dann ohne Hilfslinie)."""

    def __init__(self, *a, side="below", fixed=False, **kw):
        self._ir_side, self._ir_fixed = side, fixed       # fixed: y-Bereich vom Nutzer -> nie erweitern
        self.ir_clamped = []                               # Labels, die im festen Bereich nicht ganz passen
        self.ir_leaders, self._ir_lines = {}, []           # key -> (Peak-x, Label-x, y am Label, y am Spektrum)
        super().__init__(*a, **kw)

    def _make_labels(self, labels):
        super()._make_labels(labels)
        for ann in self.ann_items.values():
            ann.set_rotation(90)

    def _ir_positions(self):
        """-> {key: (x, y)} lower-left in Achsenbruchteilen; erweitert dabei ggf. die y-Achse, füllt ir_leaders."""
        self.ir_leaders = {}
        if not any(not getattr(a, "_extra", False) for a in self.ann_items.values()):
            return {}
        ax, below = self.ax, self._ir_side == "below"
        pts = [(np.asarray(c["x"], float), np.asarray(c["y"], float)) for c in self.spectra]
        X_ = np.concatenate([p[0] for p in pts])
        Y_ = np.concatenate([p[1] for p in pts])
        ok = np.isfinite(X_) & np.isfinite(Y_)
        X_, Y_ = X_[ok], Y_[ok]
        pad = 0.01 if self.cfg.get("size_cm") else 0.06
        pos, shrunk = {}, False
        for _ in range(5):
            rend = self._renderer()
            ab = ax.get_window_extent(rend)
            gy, gx = 2.5 * self.fig.dpi / 72 / ab.height, 1.0 * self.fig.dpi / 72 / ab.width
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            keys, tgt, wid, hgt = [], [], [], []
            for key, ann in self.ann_items.items():
                if getattr(ann, "_extra", False):          # eigenes Label: feste Stelle, nicht in der Reihe
                    continue
                _, _, bw, bh = self._measure_af(ann.get_window_extent(rend))
                keys.append(key)
                tgt.append((ann.xy[0] - x0) / (x1 - x0))
                wid.append(bw + gx)
                hgt.append(bh)
            if sum(wid) > IR_LABEL_FILL and not shrunk:    # viele Peaks (Rohdatei): wie OPUS kleiner setzen, statt
                shrunk = True                              # über den Rand zu schieben oder die Breite zu füllen
                for ann in (a for a in self.ann_items.values() if not getattr(a, "_extra", False)):
                    ann.set_fontsize(max(IR_LABEL_MIN_PT, ann.get_fontsize() * IR_LABEL_FILL / sum(wid)))
                continue
            h = max(hgt)
            lead = 3 * max(wid) * ab.width / ab.height     # Hilfslinie drei Labelbreiten hoch (wie OPUS)
            cen = spread_centers(tgt, wid)
            row = gy if below else 1 - gy - h              # Unterkante der Labelreihe
            near = row + h + gy if below else row - gy     # Hilfslinie: Ende am Label …
            far = near + lead if below else near - lead    # … und am Spektrum
            pos = {k: (c - (w - gx) / 2, row) for k, c, w in zip(keys, cen, wid)}
            self.ir_leaders = {k: (t, c, near, far) for k, t, c in zip(keys, tgt, cen)}
            gm = gy + 2.0 * self.fig.dpi / 72 / ab.height  # Abstand + kleiner Rand zum Spektrum
            q = far + gm if below else far - gm            # das Spektrum bleibt jenseits davon
            fy = (Y_ - y0) / (y1 - y0)
            if (fy.min() >= q - 1e-9) if below else (fy.max() <= q + 1e-9):
                break
            if self._ir_fixed or not (q < 0.9 if below else q > 0.1):   # fest bzw. Achse zu klein: Labels melden,
                fx = (X_ - x0) / (x1 - x0)                 # deren Spalte das Spektrum kreuzt
                for k, t, c, w in zip(keys, tgt, cen, wid):
                    m = (fx >= min(t, c) - w / 2) & (fx <= max(t, c) + w / 2)
                    if m.any() and ((fy[m].min() < q) if below else (fy[m].max() > q)):
                        self.ir_clamped.append(k)
                break
            if below:                                      # unten Platz schaffen: (Ymin − Y0)/(y1 − Y0) ≥ q
                ax.set_ylim((Y_.min() - q * y1) / (1 - q), y1)
            else:                                          # oben: (Ymax − y0)/(Y1 − y0) ≤ q
                ax.set_ylim(y0, y0 + (Y_.max() - y0) / q)
            self._fit_axes(pad)
        return {k: (min(max(x, 0.0), 1.0), y) for k, (x, y) in pos.items()}

    def _place(self):
        auto = self._ir_positions()
        orig = self.layout
        self.layout = {**{k: list(v) for k, v in auto.items()}, **orig}
        try:
            super()._place()
        finally:
            self.layout = orig
        for ln in self._ir_lines:
            ln.remove()
        self._ir_lines = []
        for k, (t, c, near, far) in self.ir_leaders.items():
            if k in orig or k not in self.ann_items:      # gezogenes Label: keine Hilfslinie
                continue
            d = (near - far) / 3                           # senkrecht – schräg – senkrecht
            ln = TABS.plt.Line2D([t, t, c, c], [far, far + d, far + 2 * d, near], transform=self.ax.transAxes,
                                 lw=0.6, color=self.ann_items[k].get_color(), clip_on=False)
            self.ax.add_line(ln)
            self._ir_lines.append(ln)


def copy_rich(plain, html):
    """Zeile mit Formatierung (fett, hoch-/tiefgestellt) in die Zwischenablage – bleibt beim Einfügen in Word."""
    md = TABS.STYLE.clip_mime()
    md.setText(SI.nbsp(plain))                  # geschützte Leerzeichen wie im Word-Export
    md.setHtml(SI.nbsp(html))
    QApplication.clipboard().setMimeData(md)


def read_ir_checked(p):
    """CALC.read_ir_modes, aber eine nicht normal beendete (abgeschnittene) Ausgabe wird abgelehnt: ihre Moden und
    Intensitäten können unvollständig sein."""
    from elucida.formats import calc as CALC
    r = CALC.read_ir_modes(p)
    if not r["calc"].get("normal", True):
        raise ValueError(T("r2a_calc_abnormal"))
    return r


class IRMSTab(TABS.FigureTab):
    """Tab „IR + EA“ (der MS-Teil steht seit 1.21 im Tab HRMS, tabs/hrms.py)."""
    LABEL_CARD = True                    # Karte „Beschriftungen im Bild“

    def label_view(self):
        return self.st.get("ram_view", "ir")

    def own_labels_allowed(self):
        return not self.btn_thr.isChecked()      # Schwellenmodus: Rechtsklick entfernt einen Stützpunkt
    STATE_KEY = "irms"
    STEP_LABELS = ("step_ir", "step_ea", "step_display")                # Schritte der linken Spalte
    GUIDE, GUIDE_ACTION = "irms", ("guide_add", "choose_ir")
    SI_CAPTION = "IR spectrum of {name}."
    X_RANGE = (100.0, 8000.0, 0, 50.0)
    XRANGE_TEXT = "ir_xrange"
    RESET_KEEP = ("ir_file", "ir_pdf", "ir_doc", "ir_doc_sel", "ir_off", "ir_thr", "ea_solvate", "ea_found", "ea_found2",
                  "ea_reason", "irc_file", "irc_scale", "irc_pairs",   # Dateien, Peakwahl, EA, Rechnung
                  "ram_file", "ram_exc", "ram_off",                  # Raman: Datei, Anregung, Peakwahl
                  "prominence", "with_int", "ir_lo", "ir_hi", "ir_base", "ram_prom",   # Peaksuche (IR-/Raman-Zeile)
                  "x_auto", "x_min", "x_max",                        # Raman-Peaks nur im gezeigten Bereich
                  "irc_tol_on", "irc_tol", "irc_si",                 # Zuordnung zur Rechnung (SI-Tabelle)
                  "ram_view")                                        # andere SI-Abbildung (IR/Raman)
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=400.0, x_max=4000.0, ymax=0.0, ir_file=None, ir_pdf=None,
                         ir_lo=None, ir_hi=None, prominence=5.0, with_int=False, ir_off=[], ir_labels=False,
                         ea_solvate="", ea_found={}, ea_found2={}, ea_reason="",   # EA (2. Satz, Begründung)
                         ir_mode="T",                                # "T" | "A"; None (alte Projekte) = wie die Datei
                         y_auto=True, y_min=0.0, y_max=100.0,        # y-Bereich (ymax: nur alte Projekte)
                         ir_color=IR_COLOR,                          # Farbe des Spektrums (FB-13)
                         ir_lw=1.0,                                 # gleiche Linienbreite in Ansicht und Export
                         ir_base=False,                              # OPUS-Basislinie abziehen (FB-11)
                         ir_thr=[],                                  # Schwellenlinie [[ṽ, A], …] (FB-15)
                         ir_struct=False, struct_w=20.0,             # Struktur der Verbindung im Bild
                         # berechnetes IR (Paket B 1.2.0): Datei, Skalierung (Vorgabe 1, vom Nutzer), Lorentz-FWHM
                         # („aus“ = Linien), Toleranz der automatischen Zuordnung („aus“ = nur von Hand), Paare von Hand
                         irc_file=None, irc_scale=1.0, irc_fwhm_on=True, irc_fwhm=15.0, irc_tol_on=True, irc_tol=20.0,
                         irc_color=IRC_COLOR, irc_pairs=[], irc_si=True,
                         # Raman (1.2.0): Datei (Textspalten), Anregung [nm], Mindesttiefe, abgewählte Peaks, Abbildung
                         # (IR | Raman | übereinander), Farbe, berechnetes Raman aus der Frequenzrechnung
                         ram_file=None, ram_exc=None, ram_prom=5.0, ram_off=[], ram_view="ir", ram_color=RAMAN_COLOR,
                         ram_calc=True)

    def arrange(self):
        super().arrange()
        self.to_right(self.grp_irc_res, T("ir_calc_page"))

    def result_empty(self):
        return [(self.grp_irc_res, not self.st.get("irc_file"))]     # ohne Frequenzrechnung keine Seite

    def build_controls(self):
        st = self.st
        self.migrate_ymax()
        g = QGroupBox(T("ir_group"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_ir = QLabel("–")
        self.lbl_ir.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_ir)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(self.clear_ir)
        row.addWidget(self.lbl_ir, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("ir_files"), row)
        # anderes PDF oder Bild (Tabelle anderer Gruppen): Zahlen als Kandidaten, Häkchen übernimmt sie in die IR-Zeile
        self.doc_head = TABS.STYLE.text_head(T("ir_doc_head_pdf"))
        f.addRow(self.doc_head)
        self.tbl_doc = TABS.STYLE.check_table([T("ir_doc_wn")])     # Zeile und Ausschnitt im Tooltip der Zeile
        self.tbl_doc.setToolTip(T("ir_doc_tip"))
        self.tbl_doc.itemChanged.connect(self.doc_toggled)
        f.addRow(self.tbl_doc)
        self.lbl_doc = HintLabel("")
        self.lbl_doc.setWordWrap(True)
        self.lbl_doc.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_doc)
        self._doc_form = f
        row = QHBoxLayout()
        self.sp_lo = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.sp_hi = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.cb_full = QCheckBox(T("ir_full"))
        for w_ in (self.cb_full, self.sp_lo, QLabel("–"), self.sp_hi):
            row.addWidget(w_)
        f.addRow(T("ir_range"), row)
        self.sp_prom = QDoubleSpinBox(decimals=1, minimum=0.5, maximum=50, singleStep=0.5, suffix=" %",
                                      value=st["prominence"])
        self.sp_prom.setToolTip(T("ir_prom_tip"))
        f.addRow(T("ir_prom"), self.sp_prom)
        self.cb_base = QCheckBox(T("ir_base"))
        self.cb_base.setToolTip(T("ir_base_tip"))
        f.addRow(self.cb_base)
        row = QHBoxLayout()
        self.btn_thr = QPushButton(T("ir_thr"))
        self.btn_thr.setCheckable(True)
        self.btn_thr.setToolTip(T("ir_thr_tip"))
        self.btn_thr.toggled.connect(lambda _on: self.render())
        self.btn_thr_clear = QPushButton(T("ir_thr_clear"))
        self.btn_thr_clear.clicked.connect(self.clear_threshold)
        row.addWidget(self.btn_thr)
        row.addWidget(self.btn_thr_clear)
        row.addStretch(1)
        f.addRow(row)
        self.cb_int = QCheckBox(T("ir_with_int"))
        self.cb_int.setToolTip(T("ir_with_int_tip"))
        self.cb_int.setChecked(st["with_int"])
        f.addRow(self.cb_int)
        self.cb_irlab = QCheckBox(T("ir_labels"))
        self.cb_irlab.setChecked(st["ir_labels"])
        f.addRow(self.cb_irlab)
        self.cb_irstruct = QCheckBox(T("ir_struct"))
        self.cb_irstruct.setToolTip(T("ir_struct_tip"))
        self.cb_irstruct.setChecked(st["ir_struct"])
        f.addRow(self.cb_irstruct)
        self.sp_struct_w = self.size_spin(f, "struct_w", "image_struktur")
        off_spin(self.cb_irstruct, self.sp_struct_w)     # ein Feld „Struktur im Bild: aus / 20 %“
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem(T("ir_mode_T"), "T")
        self.cmb_mode.addItem(T("ir_mode_A"), "A")
        self.cmb_mode.setToolTip(T("ir_mode_tip"))
        f.addRow(T("ir_mode"), self.cmb_mode)

        def pick_color(c):
            self.st["ir_color"] = c
            self.changed()
        self.btn_ircolor = TABS.color_button(st.get("ir_color") or IR_COLOR, pick_color)
        f.addRow(T("ov_color"), self.btn_ircolor)
        self.sp_ir_lw = QDoubleSpinBox(decimals=2, minimum=0.05, maximum=20.0,
                                      singleStep=0.1, suffix=" pt", value=st.get("ir_lw", 1.0))
        f.addRow(T("ir_linewidth"), self.sp_ir_lw)
        self.tbl_ir = QTableWidget(0, 3)
        self.tbl_ir.setHorizontalHeaderLabels(["", "ṽ [cm⁻¹]", T("ir_intensity")])
        self.tbl_ir.verticalHeader().setVisible(False)
        hh = self.tbl_ir.horizontalHeader()                 # feste Spalten: springen beim Scrollen nicht
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_ir.setMinimumHeight(160)
        self.tbl_ir.itemChanged.connect(self.ir_toggled)
        f.addRow(self.tbl_ir)
        b = TABS.STYLE.copy_button(T("ir_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ir_line))
        f.addRow(TABS.STYLE.text_head(T("line_ir"), b))    # „Kopieren“ direkt an der Zeile, die es kopiert
        self.txt_ir = QTextBrowser()
        self.txt_ir.setMaximumHeight(90)
        f.addRow(self.txt_ir)
        self.lv.addWidget(g)
        self.build_calc_card()
        self.build_raman_card()

        g = QGroupBox(T("ea_group"))
        f = make_form(g)
        self.lbl_ea_formula = QLabel("–")
        self.lbl_ea_formula.setWordWrap(True)
        f.addRow(T("compound_formula"), self.lbl_ea_formula)
        self.ed_solv = TABS.STYLE.ChemEdit(st.get("ea_solvate", ""))
        self.ed_solv.setPlaceholderText(T("ea_solvate_ph"))
        self.ed_solv.setToolTip(T("ea_solvate_tip"))
        f.addRow(T("ea_solvate"), self.ed_solv)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(QLabel(""), 0, 0)
        for r_, key_ in ((1, "ea_calc"), (2, "ea_found"), (3, "ea_chk_found2")):   # Raster: Beschriftungen, dann Werte
            lab_ = QLabel(T(key_))
            lab_.setProperty("formlabel", True)
            lab_.setFixedWidth(TABS.STYLE.LABEL_W)
            grid.addWidget(lab_, r_, 0)
        self.ea_calc_lbl, self.ea_found_ed, self.ea_found2_ed = {}, {}, {}
        for j, el in enumerate(SI.EA_ELEMENTS, 1):
            grid.addWidget(QLabel(f"{el} [%]", alignment=Qt.AlignCenter), 0, j)    # mittig über den Feldern
            lc = QLabel("–", alignment=Qt.AlignCenter)
            grid.addWidget(lc, 1, j)
            ed = QLineEdit(str((st.get("ea_found") or {}).get(el, "")))
            ed.setAlignment(Qt.AlignCenter)                  # Wert mittig unter „calc.“
            grid.setColumnStretch(j, 1)
            grid.addWidget(ed, 2, j)
            ed.editingFinished.connect(self.changed)
            self.ea_calc_lbl[el], self.ea_found_ed[el] = lc, ed
            ed2 = QLineEdit(str((st.get("ea_found2") or {}).get(el, "")))   # Doppelbestimmung (Angew.), optional
            ed2.setAlignment(Qt.AlignCenter)
            ed2.setToolTip(T("ea_chk_found2_tip"))
            grid.addWidget(ed2, 3, j)
            ed2.editingFinished.connect(self.changed)
            self.ea_found2_ed[el] = ed2
        f.addRow(grid)
        # Prüfung gegen 0.4 % je Element als Tabelle (Mittel bei Doppelbestimmung), Abweichung in der Warnfarbe
        self.tbl_ea = TABS.STYLE.summary_grid([T("ea_chk_el"), T("ea_chk_f1"), T("ea_chk_mean"), "Δ [%]",
                                               T("ea_chk_status")])   # Einzelwerte stehen im Raster darüber
        self.tbl_ea.setToolTip(T("ea_chk_tip"))
        TABS.STYLE.name_table(self.tbl_ea, "EA", "Elemental analysis check", csv=True)
        f.addRow(TABS.STYLE.table_head(T("tbl_head_check"), self.tbl_ea))
        f.addRow(self.tbl_ea)
        self.lbl_ea_info = HintLabel("")
        self.lbl_ea_info.setWordWrap(True)
        f.addRow(self.lbl_ea_info)
        b = TABS.STYLE.copy_button(T("ea_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ea_line))
        f.addRow(TABS.STYLE.text_head(T("line_ea"), b))
        self.txt_ea = QTextBrowser()
        self.txt_ea.setMaximumHeight(60)
        f.addRow(self.txt_ea)
        self.ed_reason = QLineEdit(st.get("ea_reason", ""))   # SI-Text, wenn es keine EA gibt (Angew., ACS)
        self.ed_reason.setPlaceholderText(T("ea_chk_reason_ph"))
        self.ed_reason.setToolTip(T("ea_chk_reason_tip"))
        f.addRow(T("ea_chk_reason"), self.ed_reason)
        self.lv.addWidget(g)
        self.ed_solv.editingFinished.connect(self.changed)
        self.ed_reason.editingFinished.connect(self.changed)

        self._ir_line = self._ea_line = ("", "")
        self.cb_full.toggled.connect(self.changed)
        for w_ in (self.sp_lo, self.sp_hi, self.sp_prom, self.sp_ir_lw):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_int, self.cb_irlab, self.cb_base, self.cb_irstruct):
            w_.toggled.connect(self.changed)
        self.cmb_mode.currentIndexChanged.connect(self.mode_changed)
        self.sync_widgets()

    # -- berechnetes IR (Paket B 1.2.0) ----------------------------------------------------
    def build_calc_card(self):
        """Karte „IR-Rechnung“ (Schritt IR): Frequenzrechnung, Skalierung, Verbreiterung, Toleranz, Zuordnung von Hand;
        Ergebnisseite „Rechnung“ rechts (arrange)."""
        st = self.st
        g = QGroupBox(T("ir_calc_card"))
        g.setToolTip(T("ir_calc_card_tip"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_irc = QLabel("–")
        self.lbl_irc.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_calc)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(lambda: self.set_calc(None))
        row.addWidget(self.lbl_irc, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("ir_calc_file"), row)
        self.sp_irc_scale = QDoubleSpinBox(decimals=3, minimum=0.5, maximum=1.5, singleStep=0.001, value=st["irc_scale"])
        self.sp_irc_scale.setToolTip(T("ir_calc_scale_tip"))
        f.addRow(T("ir_calc_scale"), self.sp_irc_scale)
        row = QHBoxLayout()
        self.cb_irc_fwhm = QCheckBox(T("ir_calc_fwhm"))
        self.cb_irc_fwhm.setChecked(st["irc_fwhm_on"])
        self.sp_irc_fwhm = QDoubleSpinBox(decimals=0, minimum=1, maximum=200, singleStep=1, value=st["irc_fwhm"],
                                          suffix=" cm⁻¹")
        self.sp_irc_fwhm.setToolTip(T("ir_calc_fwhm_tip"))
        row.addWidget(self.cb_irc_fwhm)
        row.addWidget(self.sp_irc_fwhm)
        f.addRow(row)
        row = QHBoxLayout()
        self.cb_irc_tol = QCheckBox(T("ir_calc_tol"))
        self.cb_irc_tol.setChecked(st["irc_tol_on"])
        self.sp_irc_tol = QDoubleSpinBox(decimals=0, minimum=1, maximum=200, singleStep=1, value=st["irc_tol"],
                                         suffix=" cm⁻¹")
        self.sp_irc_tol.setToolTip(T("ir_calc_tol_tip"))
        row.addWidget(self.cb_irc_tol)
        row.addWidget(self.sp_irc_tol)
        f.addRow(row)

        def pick_color(c):
            self.st["irc_color"] = c
            self.changed()
        self.btn_irc_color = TABS.color_button(st.get("irc_color") or IRC_COLOR, pick_color)
        f.addRow(T("ov_color"), self.btn_irc_color)
        self.cb_irc_si = QCheckBox(T("ir_calc_si"))
        self.cb_irc_si.setToolTip(T("ir_calc_si_tip"))
        self.cb_irc_si.setChecked(st["irc_si"])
        self.cb_irc_si.setProperty("chip_here", True)     # vor der Zuordnung von Hand, nicht unter ihren Knöpfen
        f.addRow(self.cb_irc_si)
        TABS.si_elsewhere(f, self.cb_irc_si, self, "irms", T("export_part_irc"))
        # Zuordnung von Hand: Bande und Mode wählen (Felder, keine Auswahl in Zellen), dann zuordnen/lösen
        self.cmb_irc_band = QComboBox()
        self.cmb_irc_band.setToolTip(T("ir_calc_band_tip"))
        self.cmb_irc_band.currentIndexChanged.connect(self.fill_mode_combo)
        f.addRow(T("ir_calc_band"), self.cmb_irc_band)
        self.cmb_irc_mode = QComboBox()
        self.cmb_irc_mode.setToolTip(T("ir_calc_mode_tip"))
        f.addRow(T("ir_calc_mode"), self.cmb_irc_mode)
        row = QHBoxLayout()
        self.btn_irc_pair = QPushButton(T("ir_calc_pair"))
        self.btn_irc_pair.clicked.connect(self.pair_selected)
        self.btn_irc_unpair = QPushButton(T("ir_calc_unpair"))
        self.btn_irc_unpair.clicked.connect(self.unpair_selected)
        row.addWidget(self.btn_irc_pair)
        row.addWidget(self.btn_irc_unpair)
        f.addRow("", row)
        self.grp_irc = g
        self.lv.addWidget(g)
        for w_ in (self.sp_irc_scale, self.sp_irc_fwhm, self.sp_irc_tol):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_irc_fwhm, self.cb_irc_tol, self.cb_irc_si):
            w_.toggled.connect(self.changed)
        # Ergebnisseite: Tabelle der zugeordneten Banden, darunter Skalierung und Regel
        self.grp_irc_res = QGroupBox(T("ir_calc_page"))
        self.grp_irc_res.setProperty("hug", True)
        v = QVBoxLayout(self.grp_irc_res)
        self.tbl_irc = TABS.STYLE.summary_grid([T("ir_calc_col_meas"), T("ir_calc_col_calc"), "Δṽ [cm⁻¹]",
                                                "I_calc [km mol⁻¹]", T("ir_calc_col_how")])
        TABS.STYLE.name_table(self.tbl_irc, "calc_modes", "Calculated IR assignment", csv=True)
        TABS.STYLE.rich_header(self.tbl_irc)
        v.addWidget(self.tbl_irc)
        self.lbl_irc_res = TABS.STYLE.SciLabel(empty=T("ir_calc_none"))
        self.lbl_irc_res.setWordWrap(True)
        v.addWidget(self.lbl_irc_res)
        self.lv.addWidget(self.grp_irc_res)
        self._irc_rows = []

    def choose_calc(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("ir_calc_file"), self.main.settings.value("last_dir", ""),
                                           "ORCA / Gaussian (*.out *.log);;" + T("flt_all"))
        if p:
            self.set_calc(p)

    def set_calc(self, p):
        """Frequenzrechnung laden (Kopie ins Projekt) oder entfernen; unlesbar: Meldung, nichts ändern."""
        if p:
            try:
                read_ir_checked(p)
            except Exception as e:
                return self.main.error(f"{Path(p).name}: {e}")
            p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        self.st.update(irc_file=p, irc_pairs=[])
        self.sync_widgets()
        self.timer.start()

    def calc_modes(self):
        """-> Ergebnis von CALC.read_ir_modes (zwischengespeichert) oder None."""
        p = self.st.get("irc_file")
        if not p or not Path(p).exists():
            return None
        def read():
            try:
                return read_ir_checked(p)
            except Exception as e:
                return str(e)
        r = self.cache(("irmodes", p), read)
        if isinstance(r, str):                 # Tab zeigt den Grund (show_calc); im Export mit Datei melden
            self.main.skip_part(r, p)
        return r if isinstance(r, dict) else None

    def used_peaks(self):
        off = set(self.st.get("ir_off") or [])
        return [p for p in self.peaks() if round(p["wn"]) not in off]

    def fill_band_combo(self):
        """Gemessene Banden (gezeigte Peaks) in die Auswahl; Auswahl bleibt, wenn es die Bande noch gibt."""
        old = self.cmb_irc_band.currentData()
        self.cmb_irc_band.blockSignals(True)
        self.cmb_irc_band.clear()
        for p in sorted(self.used_peaks(), key=lambda q: -q["wn"]):
            self.cmb_irc_band.addItem(f"{round(p['wn'])} cm⁻¹", round(p["wn"]))
        i = self.cmb_irc_band.findData(old)
        self.cmb_irc_band.setCurrentIndex(max(0, i))
        self.cmb_irc_band.blockSignals(False)
        self.fill_mode_combo()

    def fill_mode_combo(self, *_):
        """Berechnete Moden zur gewählten Bande, die nächsten (skaliert) zuerst."""
        self.cmb_irc_mode.clear()
        r, v = self.calc_modes(), self.cmb_irc_band.currentData()
        ok = r is not None and v is not None
        for w_ in (self.cmb_irc_mode, self.btn_irc_pair, self.btn_irc_unpair, self.cmb_irc_band):
            w_.setEnabled(ok)
        if not ok:
            return
        sc = self.st.get("irc_scale", 1.0)
        near = sorted(range(len(r["modes"])), key=lambda k: abs(r["modes"][k][0] * sc - v))[:12]
        for k in near:
            w, i = r["modes"][k]
            self.cmb_irc_mode.addItem(T("ir_calc_mode_item", w=f"{w * sc:.0f}", i=f"{i:.0f}"), k)

    def pair_selected(self):
        v, k = self.cmb_irc_band.currentData(), self.cmb_irc_mode.currentData()
        if v is None or k is None:
            return
        pairs = [q for q in self.st.get("irc_pairs") or [] if q[0] != v and q[1] != k] + [[v, k]]
        self.st["irc_pairs"] = pairs
        self.timer.start()

    def unpair_selected(self):
        v = self.cmb_irc_band.currentData()
        self.st["irc_pairs"] = [q for q in self.st.get("irc_pairs") or [] if q[0] != v]
        self.timer.start()

    def calc_rows(self):
        """Zugeordnete Banden (Tabelle, SI, Kachel) aus Messung, Rechnung und Einstellungen."""
        r = self.calc_modes()
        if r is None or self.spectrum() is None and not self.st.get("ir_pdf") and not self.doc_values():
            return []
        st = self.st
        return assign_bands([p["wn"] for p in self.used_peaks()], r["modes"], st.get("irc_scale", 1.0),
                            st.get("irc_tol") if st.get("irc_tol_on") else None, st.get("irc_pairs") or [])

    def show_calc(self):
        """Ergebnisseite „IR-Rechnung“ nach jedem Zeichnen."""
        if getattr(self, "tbl_irc", None) is None:
            return
        rows = self._irc_rows = self.calc_rows()
        N = TABS.STYLE.num
        TABS.STYLE.fill_summary(self.tbl_irc, [[N(str(q["meas"]), q["meas"]), N(f"{q['calc']:.0f}", q["calc"]),
                                                N(f"{q['diff']:+d}".replace("-", "−"), q["diff"]), N(f"{q['I']:.0f}", q["I"]),
                                                N(T("ir_calc_how_" + q["how"]), T_en("ir_calc_how_" + q["how"]))]
                                               for q in rows])
        r, st = self.calc_modes(), self.st
        notes = []
        if st.get("irc_file") and r is None:
            e = self.main.extra_cache.get(("irmodes", st["irc_file"]))
            notes.append(T("ir_calc_bad", e=e if isinstance(e, str) else ""))
        elif r is not None:
            notes.append(T("ir_calc_info", n=len(r["modes"]), s=f"{st.get('irc_scale', 1.0):.3f}",
                           pct=f"{IRC_MIN_REL * 100:.0f}"))
            if rows:
                mad = sum(abs(q["diff"]) for q in rows) / len(rows)
                notes.append(T("ir_calc_mad", n=len(rows), d=f"{mad:.0f}"))
            if r["n_imag"]:
                notes.append(T("ir_calc_imag", n=r["n_imag"]))
            if abs(st.get("irc_scale", 1.0) - 1.0) < 1e-9:
                notes.append(T("ir_calc_scale_hint"))
        self.lbl_irc_res.setText("\n".join(notes), plain=bool(rows))

    # -- Raman (1.2.0) ---------------------------------------------------------------------
    def build_raman_card(self):
        """Karte „Raman“ (Schritt IR): Spektrum als Textspalten, Anregung, Mindesttiefe, Abbildung (IR, Raman oder beide
        übereinander), Farbe, berechnetes Raman, Peaktabelle und SI-Zeile."""
        st = self.st
        g = QGroupBox(T("raman_card"))
        g.setToolTip(T("raman_card_tip"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_ram = QLabel("–")
        self.lbl_ram.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_raman)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(lambda: self.set_raman(None))
        row.addWidget(self.lbl_ram, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("raman_file"), row)
        # 0 = nicht angegeben: ohne Eingabe steht keine Anregung in SI und Unterschrift (nie eine Vorgabe)
        self.sp_ram_exc = QDoubleSpinBox(decimals=1, minimum=0.0, maximum=1600.0, singleStep=1.0, suffix=" nm",
                                         value=st["ram_exc"] or 0.0)
        self.sp_ram_exc.setSpecialValueText(T("fixt_raman_exc_none"))
        self.sp_ram_exc.setToolTip(T("raman_exc_tip"))
        f.addRow(T("raman_exc"), self.sp_ram_exc)
        self.sp_ram_prom = QDoubleSpinBox(decimals=1, minimum=0.5, maximum=50, singleStep=0.5, suffix=" %",
                                          value=st["ram_prom"])
        self.sp_ram_prom.setToolTip(T("raman_prom_tip"))
        f.addRow(T("ir_prom"), self.sp_ram_prom)
        self.cmb_ram_view = QComboBox()
        for k_ in RAMAN_VIEWS:
            self.cmb_ram_view.addItem(T("raman_view_" + k_), k_)
        self.cmb_ram_view.setToolTip(T("raman_view_tip"))
        f.addRow(T("raman_view"), self.cmb_ram_view)

        def pick_color(c):
            self.st["ram_color"] = c
            self.changed()
        self.btn_ram_color = TABS.color_button(st.get("ram_color") or RAMAN_COLOR, pick_color)
        f.addRow(T("ov_color"), self.btn_ram_color)
        self.cb_ram_calc = QCheckBox(T("raman_calc"))
        self.cb_ram_calc.setToolTip(T("raman_calc_tip"))
        self.cb_ram_calc.setChecked(bool(st["ram_calc"]))
        self.cb_ram_calc.setProperty("chip_here", True)     # vor der Tabelle, nicht darunter
        f.addRow(self.cb_ram_calc)
        self.tbl_ram = QTableWidget(0, 2)
        self.tbl_ram.setHorizontalHeaderLabels(["", "ṽ [cm⁻¹]"])
        self.tbl_ram.verticalHeader().setVisible(False)
        hh = self.tbl_ram.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_ram.setMinimumHeight(130)
        STYLE_ = TABS.STYLE
        STYLE_.empty_note(self.tbl_ram, T("raman_none"))
        self.tbl_ram.itemChanged.connect(self.raman_toggled)
        f.addRow(self.tbl_ram)
        b = STYLE_.copy_button(T("raman_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ram_line))
        f.addRow(STYLE_.text_head(T("raman_line"), b))
        self.txt_ram = QTextBrowser()
        self.txt_ram.setMaximumHeight(70)
        f.addRow(self.txt_ram)
        self.grp_raman = g
        self.lv.addWidget(g)
        self._ram_line = ("", "")
        for w_ in (self.sp_ram_exc, self.sp_ram_prom):
            w_.valueChanged.connect(self.changed)
        self.cb_ram_calc.toggled.connect(self.changed)
        self.cmb_ram_view.currentIndexChanged.connect(self.raman_view_changed)

    def choose_raman(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("raman_file"), self.main.settings.value("last_dir", ""),
                                           f"{T('raman_flt')};;{T('flt_all')}")
        if p:
            self.set_raman(p)

    def set_raman(self, p):
        """Raman-Spektrum laden (Kopie ins Projekt) oder entfernen; unlesbar: Meldung, nichts ändern."""
        if p:
            from elucida.formats.xy import read_xy
            try:
                read_xy(p)
            except Exception as e:
                return self.main.error(f"{Path(p).name}: {e}")
            p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        self.st.update(ram_file=p, ram_off=[])
        if p and self.st.get("ram_view", "ir") == "ir" and self.spectrum() is None:
            self.st["ram_view"] = "raman"                  # nur Raman geladen: gleich zeigen
        self.sync_widgets()
        self.timer.start()

    def raman_view_changed(self, *_):
        if self._loading:
            return
        self.st["ram_view"] = self.cmb_ram_view.currentData()
        self.st["layout"][self.size_key()] = {}            # Labels gehören zur anderen Abbildung
        self.timer.start()

    def raman_spectrum(self):
        """-> dict(wn, y) aufsteigend nach der Raman-Verschiebung oder None."""
        p = self.st.get("ram_file")
        if not p or not Path(p).exists():
            return None
        from elucida.formats.xy import read_xy

        def read():
            try:
                d = read_xy(p)
            except Exception as e:
                return str(e)
            o = np.argsort(d["x"])
            return {"wn": d["x"][o], "y": d["y"][o]}
        r = self.cache(("raman", p), read)
        return r if isinstance(r, dict) else None

    def raman_peaks(self):
        """Maxima des Raman-Spektrums (auf 0–1 normiert, Mindesttiefe relativ zur stärksten Bande) im gezeigten Bereich."""
        sp = self.raman_spectrum()
        if sp is None:
            return []
        lo, hi = self.raman_xlim(sp)
        return pick_peaks(sp["wn"], norm01(sp["y"]), "A", lo, hi, self.st.get("ram_prom", 5.0) / 100)

    def raman_xlim(self, sp):
        st = self.st
        if not st.get("x_auto", True):
            return min(st["x_min"], st["x_max"]), max(st["x_min"], st["x_max"])
        return float(sp["wn"].min()), float(sp["wn"].max())

    def raman_used(self):
        off = set(self.st.get("ram_off") or [])
        return [p for p in self.raman_peaks() if round(p["wn"]) not in off]

    def raman_toggled(self, item):
        if self._loading or item.column() != 0:
            return
        k = item.data(Qt.UserRole)
        off = set(self.st.get("ram_off") or [])
        off.discard(k) if item.checkState() == Qt.Checked else off.add(k)
        self.st["ram_off"] = sorted(off)
        self.timer.start()

    def fill_raman(self):
        """Peaktabelle und SI-Zeile des Raman-Spektrums."""
        peaks = self.raman_peaks()
        self._loading = True
        off = set(self.st.get("ram_off") or [])
        self.tbl_ram.setRowCount(len(peaks))
        for i, p in enumerate(sorted(peaks, key=lambda q: -q["wn"])):
            k = round(p["wn"])
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked if k in off else Qt.Checked)
            it.setData(Qt.UserRole, k)
            self.tbl_ram.setItem(i, 0, it)
            it = QTableWidgetItem(f"{p['wn']:.1f}")
            it.setFlags(Qt.ItemIsEnabled)
            self.tbl_ram.setItem(i, 1, it)
        self._loading = False
        use = [p for p in peaks if round(p["wn"]) not in off]
        self._ram_line = raman_line(use, self.st.get("ram_exc")) if use else ("", "")
        self.txt_ram.setHtml(self._ram_line[1])

    def calc_raman(self):
        """Berechnete Raman-Aktivitäten [(ṽ, S)] der geladenen Frequenzrechnung oder None (fehlen sie: kein Spektrum)."""
        r = self.calc_modes()
        return r.get("raman") if r is not None and self.st.get("ram_calc", True) else None

    def raman_figure_spec(self, view):
        """Abbildung „Raman“ (Maxima nach oben, Achse Raman shift, Intensität ohne Zahlen) oder „übereinander“ (IR oben,
        Raman unten auf gemeinsamer Wellenzahlachse, beide auf ihre Spannweite normiert) -> wie figure_spec."""
        st = self.st
        rs = self.raman_spectrum()
        cfg = self.base_cfg()
        cfg["y_axis"] = "no_numbers"
        cfg["legend"] = False
        lw = min(20.0, max(0.05, float(st.get("ir_lw", 1.0))))
        col = st.get("ram_color") or RAMAN_COLOR
        labels = []
        if view == "stack":
            sp = self.spectrum()
            (lo, hi), _ = self.ir_range()
            if st["x_auto"]:
                x0, x1 = min(lo, hi, rs["wn"].min()), max(lo, hi, rs["wn"].max())
            else:
                x0, x1 = min(st["x_min"], st["x_max"]), max(st["x_min"], st["x_max"])
            mode = self.mode()
            sel = (sp["wn"] >= x0) & (sp["wn"] <= x1)
            yi = display_y(sp, mode)
            ys = yi[sel] if sel.any() else yi
            yi = (yi - np.nanmin(ys)) / ((np.nanmax(ys) - np.nanmin(ys)) or 1.0)
            rsel = (rs["wn"] >= x0) & (rs["wn"] <= x1)
            yr = rs["y"] - np.nanmin(rs["y"][rsel] if rsel.any() else rs["y"])
            yr = yr / ((np.nanmax(yr[rsel] if rsel.any() else yr)) or 1.0)
            off = 1.0 + STACK_GAP
            curves = [{"x": sp["wn"], "y": yi + off, "color": st.get("ir_color") or IR_COLOR, "label": "IR", "ls": "-",
                       "lw": lw},
                      {"x": rs["wn"], "y": yr, "color": col, "label": "Raman", "ls": "-", "lw": lw}]
            cfg.update(xlim=[x1, x0], ylim=[-0.04, 2 + STACK_GAP + 0.04], legend=True, legend_beside=True,
                       xlabel="wavenumber [cm$^{-1}$]", ylabel="intensity [arb. u.]")
            self._ir_fig = {"side": "above", "fixed": True}
            self._fig_kind = "stack"
            return cfg, curves, labels, []
        x0, x1 = self.raman_xlim(rs)
        sel = (rs["wn"] >= x0) & (rs["wn"] <= x1)
        y = rs["y"]
        ys = y[sel] if sel.any() else y
        ymin, ymax = float(np.nanmin(ys)), float(np.nanmax(ys))
        span = (ymax - ymin) or 1.0
        curves = [{"x": rs["wn"], "y": y, "color": col, "label": None, "ls": "-", "lw": lw}]
        self._ram_calc_drawn = None
        modes = self.calc_raman()
        if modes:
            fw = st.get("irc_fwhm") if st.get("irc_fwhm_on", True) else 0.0
            prof = calc_ir_profile(modes, st.get("irc_scale", 1.0), fw, x0, x1)
            if prof is None:
                self.add_note(T("ir_calc_out_of_range"))
            else:
                curves[0]["label"] = "exp."
                curves.append({"x": prof[0], "y": ymin + prof[1] * span, "color": st.get("irc_color") or IRC_COLOR,
                               "ls": "-", "label": "calc.", "lw": lw})
                cfg.update(legend=True, legend_beside=True)
                self._ram_calc_drawn = fw
        elif self.calc_modes() is not None and st.get("ram_calc", True):
            self.add_note(T("raman_calc_none"))
        if st.get("ir_labels"):
            o = np.argsort(rs["wn"])
            for p in self.raman_used():
                yv = float(np.interp(p["wn"], rs["wn"][o], y[o]))
                labels.append({"key": f"label_ram_{round(p['wn'])}", "lam": p["wn"], "y": yv, "side": "above",
                               "text": wn_text(p["wn"])})
        cfg.update(xlim=[x0, x1], ylim=[ymin - 0.04 * span, ymax + 0.06 * span],
                   xlabel="Raman shift [cm$^{-1}$]", ylabel="intensity [arb. u.]")
        self._ir_fig = {"side": "above", "fixed": False}
        self._fig_kind = "raman"
        return cfg, curves, labels, []

    def raman_caption(self, name):
        """Bildunterschrift der Raman-Abbildungen (HTML); Anregung aus dem Feld, Rechnung wie beim IR."""
        import html as _h
        nm = "<b>" + _h.escape(name) + "</b>"
        exc = self.st.get("ram_exc")
        ex = f"<i>λ</i><sub>exc</sub> = {exc_text(exc)} nm" if exc else ""
        if getattr(self, "_fig_kind", "ir") == "stack":
            return f"IR (top) and Raman (bottom{', ' + ex if ex else ''}) spectra of {nm}."
        cap = f"Raman spectrum of {nm}" + (f" ({ex})" if ex else "")
        fw = getattr(self, "_ram_calc_drawn", None)
        r = self.calc_modes()
        if fw is None or r is None:
            return cap + "."
        from elucida.tabs import dft_pages as DP
        lvl = DP.level_of_theory(r["calc"])
        how = f"Lorentzian broadening, FWHM {fw:.0f} cm-1" if fw else "line spectrum"
        return (cap + f" (measured) with the calculated Raman activities{' (' + _h.escape(lvl) + ')' if lvl else ''}, "
                f"frequencies scaled by {self.st.get('irc_scale', 1.0):.3f}, {how}.")

    def refresh_summary(self):
        try:                                              # Zugabe zum Zeichnen: Fehler nie nach außen; vor den Kacheln
            if getattr(self, "tbl_irc", None) is not None:
                self.fill_band_combo()
                self.show_calc()
        except Exception:
            import traceback
            self.main.log_signal.emit(traceback.format_exc())
        super().refresh_summary()

    def si_caption(self, name):
        if getattr(self, "_fig_kind", "ir") != "ir":
            return self.raman_caption(name)
        cap = super().si_caption(name)
        r = self.calc_modes()
        if r is None or getattr(self, "_irc_drawn", None) is None:
            return cap
        from elucida.tabs import dft_pages as DP
        lvl = DP.level_of_theory(r["calc"])
        fw = self._irc_drawn
        how = f"Lorentzian broadening, FWHM {fw:.0f} cm-1" if fw else "line spectrum"
        return (cap[:-1] + f" (measured) with the calculated spectrum{' (' + __import__('html').escape(lvl) + ')' if lvl else ''}, "
                f"frequencies scaled by {self.st.get('irc_scale', 1.0):.3f}, {how}.")

    def si_table_blocks(self, name):
        """Tabelle der zugeordneten Banden für die SI (Word), leer ohne Zuordnung oder ohne Haken."""
        if not self.st.get("irc_si", True):
            return []
        self.ensure_rendered()
        rows = self.calc_rows()
        if not rows:
            return []
        from elucida.tabs import xray as XRAY
        st = self.st
        head = ["*ṽ*_{exp} / cm^{−1}", "*ṽ*_{calc} / cm^{−1}", "Δ*ṽ* / cm^{−1}", "*I*_{calc} / km mol^{−1}"]
        body = [[str(q["meas"]), f"{q['calc']:.0f}", f"{q['diff']:+d}".replace("-", "−"), f"{q['I']:.0f}"] for q in rows]
        note = (f"Calculated frequencies scaled by {st.get('irc_scale', 1.0):.3f}; Δ*ṽ* = *ṽ*_{{exp}} − *ṽ*_{{calc}}. "
                + ("Bands assigned manually" if all(q["how"] == "manual" for q in rows) else
                   f"Bands assigned manually or as the only calculated mode (≥ {IRC_MIN_REL * 100:.0f}% of the strongest "
                   f"intensity) within ±{st.get('irc_tol', 20.0):.0f} cm^{{−1}}") + ".")
        return [("tabcap", "Measured and calculated IR bands of", name),
                ("params", head, body, {"fit": True}), ("note", note), ("gap",)]

    def common_box(self):
        """Statt „y-Achse max“ eine Zeile „y-Bereich“: auto | min – max (exakt)."""
        g = super().common_box()
        fl = g.layout()
        r, _ = fl.getWidgetPosition(self.sp_ymax)
        fl.setRowVisible(r, False)
        row = QHBoxLayout()
        self.cb_yauto = QCheckBox(T("auto"))
        self.cb_yauto.setToolTip(T("ir_yrange_tip"))
        self.sp_ymin = QDoubleSpinBox()
        self.sp_ymax2 = QDoubleSpinBox()
        for w_ in (self.cb_yauto, self.sp_ymin, QLabel("–"), self.sp_ymax2):
            row.addWidget(w_)
        fl.insertRow(r + 1, T("ir_yrange"), row)
        self.cb_yauto.toggled.connect(self.yauto_toggled)
        self.cb_yauto.toggled.connect(self.changed)
        for w_ in (self.sp_ymin, self.sp_ymax2):
            w_.valueChanged.connect(self.changed)
        self.sync_yrange()
        return g

    def migrate_ymax(self):
        """Alte Projekte (bis 2.3.6): „y-Achse max“ > 0 -> fester y-Bereich mit dieser Obergrenze und der damaligen
        automatischen Untergrenze; der alte Schlüssel wird danach 0 (bleibt lesbar)."""
        st = self.st
        old = float(st.get("ymax") or 0.0)
        if old <= 0:
            return
        st["ymax"] = 0.0
        mode = self.mode()
        sp = self.spectrum()
        auto, _ = y_limits(display_y(sp, mode) if sp else [], mode)
        top = min(old, 100.0) if mode == "T" else old
        lo = max(auto[0], 0.0) if mode == "T" else auto[0]
        if top > lo:
            st.update(y_auto=False, y_min=round(lo, 2), y_max=round(top, 2))

    def yauto_toggled(self, on):
        """„auto“ aus: Felder mit dem aktuell gezeigten Bereich vorbelegen (dann nur noch verschieben)."""
        if self._loading or on:
            return
        lo, hi = self.F.ax.get_ylim() if self.F is not None else Y_DEFAULT[self.mode()]
        mn, mx, dec, _ = Y_SPIN[self.mode()]
        for sp_, v in ((self.sp_ymin, lo), (self.sp_ymax2, hi)):
            sp_.blockSignals(True)
            sp_.setValue(round(min(max(v, mn), mx), dec))
            sp_.blockSignals(False)

    def sync_yrange(self):
        """Felder „y-Bereich“ passend zur Darstellung: %T 0–100 in ganzen Prozent, Absorbanz −1–10."""
        if getattr(self, "sp_ymin", None) is None:
            return
        mode, st = self.mode(), self.st
        mn, mx, dec, step = Y_SPIN[mode]
        auto = bool(st.get("y_auto", True))
        for sp_, k in ((self.sp_ymin, "y_min"), (self.sp_ymax2, "y_max")):
            sp_.blockSignals(True)
            sp_.setDecimals(dec)
            sp_.setRange(mn, mx)
            sp_.setSingleStep(step)
            sp_.setSuffix(" %" if mode == "T" else "")
            sp_.setValue(float(st.get(k, 0.0)))
            sp_.setEnabled(not auto)
            sp_.blockSignals(False)
        self.cb_yauto.blockSignals(True)
        self.cb_yauto.setChecked(auto)
        self.cb_yauto.blockSignals(False)

    def mode(self):
        """Darstellung im Bild: gewählt, sonst wie die Datei (Transmission, falls keine Datei)."""
        m = self.st.get("ir_mode")
        if m in ("T", "A"):
            return m
        sp = self.spectrum()
        return sp["kind"] if sp else "T"

    def mode_changed(self, *_):
        if self._loading:
            return
        m = self.cmb_mode.currentData()
        if m != self.mode():
            self.st["ir_mode"] = m
            lo, hi = Y_DEFAULT[m]                      # Bereich gehört zur alten Einheit -> auto
            self.st.update(y_auto=True, y_min=lo, y_max=hi)
            self.st["layout"][self.size_key()] = {}    # Labels wechseln die Seite
        self.sync_yrange()
        self.timer.start()

    # -- Dateien --------------------------------------------------------------------
    def choose_ir(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ir_files"), self.main.settings.value("last_dir", ""),
                                             f"{T('flt_ir')};;{T('flt_ocr_img')} "
                                             f"({' '.join('*' + e for e in OCR.IMAGE_EXT)});;{T('flt_all')}")
        self.load_ir_files(ps)

    def load_ir_files(self, ps):
        """Mehrere Dateien auf einmal: das letzte Spektrum gilt; ein PDF nur, wenn es eindeutig zu ihm gehört (einziges
        Spektrum der Auswahl oder gleicher Dateiname), sonst Hinweis statt fremder Peaks."""
        spec = [p for p in ps if Path(p).suffix.lower() != ".pdf" and Path(p).suffix.lower() not in OCR.IMAGE_EXT]
        for p in [p for p in ps if Path(p).suffix.lower() in OCR.IMAGE_EXT][-1:]:   # Bild: Zahlen per OCR
            self.load_ir(p)
        pdfs = [p for p in ps if Path(p).suffix.lower() == ".pdf"]
        for p in spec:
            self.load_ir(p)
        if spec and len(spec) > 1:
            same = [p for p in pdfs if Path(p).stem == Path(spec[-1]).stem]
            if pdfs and not same:
                self.main.error(T("ir_pdf_ambiguous"))
            pdfs = same
        for p in pdfs[-1:]:
            self.load_ir(p)

    def load_ir(self, p):
        """OPUS-PDF (am Layout erkannt) -> Peakliste, anderes PDF/Bild -> Kandidaten zum Anhaken (nichts vorgewählt),
        OPUS-Datei -> Spektrum (eigene Peaksuche); Spektrum und PDF dürfen gleichzeitig da sein."""
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        try:
            if Path(p).suffix.lower() in OCR.IMAGE_EXT or (Path(p).suffix.lower() == ".pdf"
                                                               and not (is_opus_pdf(p) and read_ir_pdf(p))):
                if Path(p).suffix.lower() == ".pdf":
                    import pymupdf
                    with pymupdf.open(p) as doc_:                 # unlesbar: Grund statt leerer Liste
                        doc_.page_count
                else:
                    from PIL import Image
                    with Image.open(p) as im_:
                        im_.verify()
                self.st.update(ir_doc=p, ir_doc_sel=[], ir_pdf=None)   # kein OPUS-PDF: Werte per Klick
                self.sync_widgets()
                self.timer.start()
                return
            if Path(p).suffix.lower() == ".pdf":
                self.st.update(ir_pdf=p, ir_doc=None, ir_doc_sel=[])
            else:
                read_opus(p)
                if self.st.get("ir_file") and self.st["ir_file"] != p:
                    self.st["ir_pdf"] = None             # PDF gehörte zum vorigen Spektrum
                self.st["ir_file"] = p
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ir_lo=None, ir_hi=None, ir_off=[], ir_thr=[])
        self.sync_widgets()
        self.timer.start()

    def clear_ir(self):
        self.st.update(ir_file=None, ir_pdf=None, ir_lo=None, ir_hi=None, ir_off=[], ir_thr=[], ir_doc=None, ir_doc_sel=[])
        self.sync_widgets()
        self.timer.start()

    def compound_changed(self):
        self.sync_widgets()
        self.timer.start()

    # -- Daten ------------------------------------------------------------------------
    def raw_spectrum(self):
        """Spektrum der OPUS-Datei, sonst die Kurve aus dem OPUS-PDF (FB-14; unlesbar -> None, Grund in pdf_error)."""
        p, pdf = self.st.get("ir_file"), self.st.get("ir_pdf")
        if p and Path(p).exists():
            return self.cache(("opus", p), lambda: read_opus(p))
        if pdf and Path(pdf).exists():
            def curve():
                try:
                    return read_ir_pdf_curve(pdf)
                except Exception as e:                   # unbekanntes Layout: Peakwerte gelten weiter, kein Bild
                    return str(e)
            sp = self.cache(("irpdfcurve", pdf), curve)
            return sp if isinstance(sp, dict) else None
        return None

    def pdf_error(self):
        pdf = self.st.get("ir_pdf")
        e = self.main.extra_cache.get(("irpdfcurve", pdf)) if pdf and not self.st.get("ir_file") else None
        return e if isinstance(e, str) else None

    def spectrum(self):
        """Spektrum für Bild und Peaksuche: mit Haken „Basislinie“ korrigiert (nie die Datei)."""
        sp = self.raw_spectrum()
        if sp is None or not self.st.get("ir_base"):
            return sp
        key = ("irbase", self.st.get("ir_file") or self.st.get("ir_pdf"))
        return self.cache(key, lambda: baseline_corrected(sp))

    def raw_uncorrected(self):
        """OPUS-Verlauf nennt eine Basislinienkorrektur, die Datei hat aber noch die Basislinie (> 0.02 A)."""
        sp = self.raw_spectrum()
        if not sp or not sp.get("baseline") or self.st.get("ir_base"):
            return False
        b = self.cache(("irbase", self.st.get("ir_file")), lambda: baseline_corrected(sp))
        d = to_absorbance(sp["y"]) - to_absorbance(b["y"]) if sp["kind"] == "T" else sp["y"] - b["y"]
        return bool(np.nanmax(np.abs(d)) > 0.02)

    def ir_range(self):
        sp = self.spectrum()
        full = (float(sp["wn"].min()), float(sp["wn"].max())) if sp else (400.0, 4000.0)
        pdf = self.st.get("ir_pdf")
        if sp is None and pdf and Path(pdf).exists():   # nur PDF: alle Peakwerte liegen im ganzen Bereich
            vals = self.cache(("irpdf", pdf), lambda: read_ir_pdf(pdf))
            full = (min([full[0], *vals]), max([full[1], *vals]))
        elif sp is None and self.doc_values():           # nur Werte aus einem Dokument: ebenso
            vals = self.doc_values()
            full = (min([full[0], *vals]), max([full[1], *vals]))
        lo, hi = self.st.get("ir_lo"), self.st.get("ir_hi")
        return (full[0] if lo is None else lo, full[1] if hi is None else hi), full

    def peaks(self):
        """Peakliste im Bereich: aus dem OPUS-PDF (exakt die OPUS-Werte) oder eigene Suche im Spektrum.
        Intensitäten kommen immer aus dem Spektrum, falls vorhanden."""
        st = self.st
        (lo, hi), _ = self.ir_range()
        sp = self.spectrum()
        if sp and st.get("ir_thr") and not st.get("ir_pdf"):
            found = threshold_peaks(sp, st["ir_thr"], lo, hi)
        else:
            found = pick_peaks(sp["wn"], sp["y"], sp["kind"], lo, hi, st["prominence"] / 100) if sp else []
        vals = None
        if st.get("ir_pdf") and Path(st["ir_pdf"]).exists():
            vals = self.cache(("irpdf", st["ir_pdf"]), lambda: read_ir_pdf(st["ir_pdf"]))
        elif self.doc_values():                          # aus einem Dokument angehakt (Textebene oder OCR)
            vals = self.doc_values()
        if vals is not None:
            out = []
            for v in vals:
                if min(lo, hi) <= v <= max(lo, hi):
                    near = min(found, key=lambda q: abs(q["wn"] - v), default=None)
                    p = dict(near) if near is not None and abs(near["wn"] - v) < 3 else {}
                    p["wn"] = v
                    out.append(p)
            return out
        return found

    def doc_values(self):
        """Angehakte ṽ aus dem Dokument (ganze Zahlen, absteigend); gelten ohne erneute Erkennung."""
        return sorted({float(v) for v in self.st.get("ir_doc_sel") or []}, reverse=True) if self.st.get("ir_doc") else []

    def doc_candidates(self):
        """Zahlen des Dokuments -> ([(ṽ ganzzahlig, Zeile, Ausschnitt)], Herkunft "pdf"/"ocr", Zustand der Erkennung):
        erst die Textebene, ohne Zahlen dort die Texterkennung im Hintergrund."""
        p = self.st.get("ir_doc")
        if not p or not Path(p).exists():
            return [], "", ""
        items = self.cache(("irdoctext", p), lambda: OCR.text_items(p))
        cands = OCR.candidates(items, IR_DOC_NUM, IR_DOC_RANGE[0], IR_DOC_RANGE[1], header_line)
        if cands:
            return self._ir_ints(cands), "pdf", ""
        res = OCR.start(self.main, p)
        if res is None:
            return [], "ocr", "running"
        if "error" in res:
            return [], "ocr", res["error"]
        return self._ir_ints(OCR.candidates(res["items"], IR_DOC_NUM, IR_DOC_RANGE[0], IR_DOC_RANGE[1], header_line)), "ocr", ""

    @staticmethod
    def _ir_ints(cands):
        out, seen = [], set()
        for v, line, crop in cands:
            k = int(wn_text(v))                     # x.5 aufgerundet wie in der IR-Zeile
            if k not in seen:
                seen.add(k)
                out.append((k, line, crop))
        return out

    def fill_doc(self):
        """Kandidatentabelle des Dokuments: nichts angehakt, bis man klickt; Herkunft in der Kopfzeile."""
        on = bool(self.st.get("ir_doc"))
        for w_ in (self.doc_head, self.tbl_doc):
            self._doc_form.setRowVisible(w_, on)
        if not on:
            self.lbl_doc.setText("")
            return
        cands, src, state = self.doc_candidates()
        self.doc_head.findChild(QLabel).setText(T("ir_doc_head_" + (src or "pdf")))
        sel = {int(v) for v in self.st.get("ir_doc_sel") or []}
        t = self.tbl_doc
        t.blockSignals(True)
        t.setRowCount(0)
        for k, line, crop in cands:
            TABS.STYLE.check_row(t, k, [str(k)], checked=k in sel)
            tip = OCR.tip_html(crop, line)
            for c in range(t.columnCount()):
                t.item(t.rowCount() - 1, c).setToolTip(tip)
        t.blockSignals(False)
        TABS.STYLE.fit_columns(t)
        TABS.STYLE.fit_check_table(t, 6)
        self._doc_form.setRowVisible(t, bool(cands))
        self.lbl_doc.setStyleSheet(WARN_CSS if state not in ("", "running") else HINT_CSS)
        self.lbl_doc.setText(T("ms_ocr_running") if state == "running" else T("ocr_missing") if state == "missing"
                             else T("ocr_failed", e=state) if state else T("ir_doc_none") if not cands else "")

    def doc_toggled(self, item):
        if item.column() != 0:
            return
        k = item.data(Qt.UserRole)
        sel = {int(v) for v in self.st.get("ir_doc_sel") or []}
        sel.add(k) if item.checkState() == Qt.Checked else sel.discard(k)
        self.st["ir_doc_sel"] = sorted(sel, reverse=True)
        self.fill_doc()
        self.timer.start()

    def formula(self):
        """Formel wie im HRMS-Tab: Verbindung des Projekts, sonst die Struktur im MS-Bericht, sonst dessen Formelfeld."""
        hr = getattr(self.main, "hrms_tab", None)
        if hr is not None:
            return hr.formula()
        c = self.main.compound
        return (c["formula"], "project") if c.get("formula") else (None, None)

    # -- Oberfläche -----------------------------------------------------------------
    def sync_widgets(self):
        st = self.st
        self._loading = True
        names = [Path(p).name for p in (st.get("ir_file"), st.get("ir_pdf"), st.get("ir_doc")) if p]
        self.lbl_ir.setText(", ".join(names) or "–")
        (lo, hi), full = self.ir_range()
        auto = st.get("ir_lo") is None and st.get("ir_hi") is None
        self.cb_full.setChecked(auto)
        self.sp_lo.setValue(lo)
        self.sp_hi.setValue(hi)
        self.sp_lo.setEnabled(not auto)
        self.sp_hi.setEnabled(not auto)
        self.sp_prom.setEnabled(self.spectrum() is not None and not st.get("ir_pdf") and not st.get("ir_thr"))
        self.cb_base.setChecked(bool(st.get("ir_base")))
        self.cb_base.setEnabled(self.raw_spectrum() is not None)
        thr_ok = self.spectrum() is not None and not st.get("ir_pdf")
        self.btn_thr.setEnabled(thr_ok)
        if not thr_ok and self.btn_thr.isChecked():
            self.btn_thr.blockSignals(True)
            self.btn_thr.setChecked(False)
            self.btn_thr.blockSignals(False)
        self.btn_thr_clear.setEnabled(bool(st.get("ir_thr")))
        for key_, eds_ in (("ea_found", self.ea_found_ed), ("ea_found2", self.ea_found2_ed)):
            for el, ed in eds_.items():
                ed.setText(str((st.get(key_) or {}).get(el, "")))
        self.cb_int.setChecked(bool(st.get("with_int")))
        self.cb_irlab.setChecked(bool(st.get("ir_labels")))
        self.cb_irstruct.setChecked(bool(st.get("ir_struct")))
        self.sp_struct_w.setValue(st.get("struct_w", 20.0))
        c_ = st.get("ir_color") or IR_COLOR
        self.btn_ircolor.setProperty("color", c_)
        self.btn_ircolor.setStyleSheet(f"background-color: {c_}; border: 1px solid {TABS.STYLE.swatch_border()};")
        self.sp_prom.setValue(st.get("prominence", 5.0))
        self.sp_ir_lw.setValue(st.get("ir_lw", 1.0))
        if getattr(self, "lbl_irc", None) is not None:      # berechnetes IR
            self.lbl_irc.setText(Path(st["irc_file"]).name if st.get("irc_file") else "–")
            self.sp_irc_scale.setValue(st.get("irc_scale", 1.0))
            self.cb_irc_fwhm.setChecked(bool(st.get("irc_fwhm_on", True)))
            self.sp_irc_fwhm.setValue(st.get("irc_fwhm", 15.0))
            self.cb_irc_tol.setChecked(bool(st.get("irc_tol_on", True)))
            self.sp_irc_tol.setValue(st.get("irc_tol", 20.0))
            self.cb_irc_si.setChecked(bool(st.get("irc_si", True)))
            c2_ = st.get("irc_color") or IRC_COLOR
            self.btn_irc_color.setProperty("color", c2_)
            self.btn_irc_color.setStyleSheet(f"background-color: {c2_}; border: 1px solid {TABS.STYLE.swatch_border()};")
        if getattr(self, "lbl_ram", None) is not None:      # Raman
            self.lbl_ram.setText(Path(st["ram_file"]).name if st.get("ram_file") else "–")
            self.sp_ram_exc.setValue(st.get("ram_exc") or 0.0)
            self.sp_ram_prom.setValue(st.get("ram_prom", 5.0))
            self.cb_ram_calc.setChecked(bool(st.get("ram_calc", True)))
            self.cmb_ram_view.setCurrentIndex(max(0, self.cmb_ram_view.findData(st.get("ram_view", "ir"))))
            c3_ = st.get("ram_color") or RAMAN_COLOR
            self.btn_ram_color.setProperty("color", c3_)
            self.btn_ram_color.setStyleSheet(f"background-color: {c3_}; border: 1px solid {TABS.STYLE.swatch_border()};")
        self.cmb_mode.setCurrentIndex(self.cmb_mode.findData(self.mode()))
        self.sync_yrange()
        self.fill_doc()
        self._loading = False

    def collect(self):
        st = self.st
        if self.cb_full.isChecked():
            st.update(ir_lo=None, ir_hi=None)
        else:
            st.update(ir_lo=self.sp_lo.value(), ir_hi=self.sp_hi.value())
        st.update(ea_solvate=self.ed_solv.text().strip(),
                  ea_found={el: ed.text().strip().replace(",", ".") for el, ed in self.ea_found_ed.items()
                            if ed.text().strip()},
                  ea_found2={el: ed.text().strip().replace(",", ".") for el, ed in self.ea_found2_ed.items()
                             if ed.text().strip()},
                  ea_reason=self.ed_reason.text().strip())
        st.update(prominence=self.sp_prom.value(), with_int=self.cb_int.isChecked(), ir_labels=self.cb_irlab.isChecked(),
                  ir_base=self.cb_base.isChecked(), ir_struct=self.cb_irstruct.isChecked(), ir_lw=self.sp_ir_lw.value(),
                  irc_scale=self.sp_irc_scale.value(), irc_fwhm_on=self.cb_irc_fwhm.isChecked(),
                  irc_fwhm=self.sp_irc_fwhm.value(), irc_tol_on=self.cb_irc_tol.isChecked(),
                  irc_tol=self.sp_irc_tol.value(), irc_si=self.cb_irc_si.isChecked(),
                  ram_exc=self.sp_ram_exc.value() or None, ram_prom=self.sp_ram_prom.value(),
                  ram_calc=self.cb_ram_calc.isChecked())
        if getattr(self, "sp_ymin", None) is not None:
            lo, hi = self.sp_ymin.value(), self.sp_ymax2.value()
            if lo >= hi:                                  # min < max: das gerade nicht geänderte Feld weicht aus
                step = Y_SPIN[self.mode()][3]
                if self.sender() is self.sp_ymax2:
                    lo = max(Y_SPIN[self.mode()][0], hi - step)
                    hi = max(hi, lo + step)
                else:
                    hi = min(Y_SPIN[self.mode()][1], lo + step)
                    lo = min(lo, hi - step)
            st.update(y_auto=self.cb_yauto.isChecked(), y_min=lo, y_max=hi)
        self.sync_widgets()

    def ir_toggled(self, item):
        if self._loading or item.column() != 0:
            return
        k = item.data(Qt.UserRole)
        off = set(self.st.get("ir_off") or [])
        off.discard(k) if item.checkState() == Qt.Checked else off.add(k)
        self.st["ir_off"] = sorted(off)
        self.timer.start()

    def fill_ir_table(self, peaks):
        self._loading = True
        off = set(self.st.get("ir_off") or [])
        self.tbl_ir.setRowCount(len(peaks))
        for i, p in enumerate(peaks):
            k = round(p["wn"])
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked if k in off else Qt.Checked)
            it.setData(Qt.UserRole, k)
            self.tbl_ir.setItem(i, 0, it)
            for j, v in ((1, f"{p['wn']:.1f}"), (2, intensity_tag(p) if "rel" in p else "–")):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                self.tbl_ir.setItem(i, j, it)
        self._loading = False

    def update_ea(self):
        """Elementaranalyse: berechnet aus der Formel (+ Solvat), gefunden wie eingegeben; Warnung ab 0.4 %."""
        st = self.st
        formula, _ = self.formula()
        self._ea_line = ("", "")
        self._ea_rows = []
        TABS.STYLE.fill_summary(self.tbl_ea, [])
        for el in SI.EA_ELEMENTS:
            self.ea_calc_lbl[el].setText("–")
        if not formula:
            self.lbl_ea_formula.setText(T("ea_no_formula"))
            self.txt_ea.setHtml("")
            self.lbl_ea_info.setText("")
            return
        try:
            comp = SI.ea_composition(formula, st.get("ea_solvate", ""))
            label = SI.ea_formula_label(formula, st.get("ea_solvate", ""))
            plain, html, notes = SI.ea_line(formula, st.get("ea_solvate", ""), st.get("ea_found") or {},
                                            st.get("ea_found2") or {})
            rows = SI.ea_check(formula, st.get("ea_solvate", ""), st.get("ea_found") or {}, st.get("ea_found2") or {})
        except (ValueError, KeyError) as e:
            self.lbl_ea_formula.setText(SI.chem_plain(formula))
            self.lbl_ea_info.setText(str(e))
            self.lbl_ea_info.setStyleSheet(WARN_CSS)
            self.txt_ea.setHtml("")
            return
        self.lbl_ea_formula.setText(SI.chem_plain(label))
        for el in SI.EA_ELEMENTS:
            if el in comp:
                self.ea_calc_lbl[el].setText(f"{comp[el]:.2f}")
        if not st.get("ea_found"):
            self._ea_line = SI.ea_reason_line(st.get("ea_reason", ""))   # ohne Werte: Begründung, falls eingetragen
            self.txt_ea.setHtml(self._ea_line[1])
            self.lbl_ea_info.setText(T("ea_enter"))
            self.lbl_ea_info.setStyleSheet(HINT_CSS)
            return
        self._ea_rows = rows
        self.fill_ea_table(rows)
        self._ea_line = (plain, html)
        self.txt_ea.setHtml(html)
        if notes:
            self.lbl_ea_info.setText(T("ea_dev", els=", ".join(f"{el} {d:+.2f}".replace("-", "−") for el, d in notes)))
            self.lbl_ea_info.setStyleSheet(WARN_CSS)
        else:
            self.lbl_ea_info.setText(T("ea_ok"))
            self.lbl_ea_info.setStyleSheet(HINT_CSS)

    def fill_ea_table(self, rows):
        """Tabelle der EA-Prüfung: je Element der geprüfte Wert (gefunden, mit zweitem Satz das Mittel), Δ, Status."""
        from PySide6.QtGui import QBrush, QColor
        two = any(r[3] is not None for r in rows)
        single = two and any(r[4] is None for r in rows)  # Element nur einmal bestimmt: dieser Wert wird geprüft
        self.tbl_ea.setHorizontalHeaderLabels([T("ea_chk_el"), T("ea_chk_f1"),
                                               T("r2a_ea_mean_single" if single else "ea_chk_mean"), "Δ [%]",
                                               T("ea_chk_status")])
        N = TABS.STYLE.num                               # CSV: Rohwerte, Status englisch
        TABS.STYLE.fill_summary(self.tbl_ea, [
            [el, N(f"{v1:.2f}", v1), N(f"{m if m is not None else v1:.2f}", m if m is not None else v1),
             N(TABS.core.fmt_num(d, 2, sign=True), d),
             N(("✓ " if ok else "⚠ ") + T("ea_chk_ok" if ok else "ea_chk_bad"), T_en("ea_chk_ok" if ok else "ea_chk_bad"))]
            for el, calc, v1, v2, m, d, ok in rows], hidden=(1,) if two else (2,))
        for r, row in enumerate(rows):
            if not row[-1]:
                for c in range(self.tbl_ea.columnCount()):
                    self.tbl_ea.item(r, c).setForeground(QBrush(QColor(TABS.STYLE.WARN_COLOR)))

    KPI_WITHOUT_FIGURE = True                             # EA-Kachel auch ohne IR-Spektrum

    def kpis(self):
        """Kachel EA: alle Elemente innerhalb 0.4 % oder die größte Abweichung in der Warnfarbe; dazu die Zahl der
        zugeordneten Banden der IR-Rechnung (dieselbe Zahl wie die Tabelle der Seite IR-Rechnung)."""
        out = []
        irc = getattr(self, "_irc_rows", None) or []
        if irc:
            out.append((T("ir_calc_kpi"), str(len(irc))))
        rows = getattr(self, "_ea_rows", None) or []
        if not rows:
            return out
        bad = [r for r in rows if not r[-1]]
        if not bad:
            return [(T("ea_chk_kpi"), "≤ 0.4 %")] + out
        el, *_, d, _ = max(bad, key=lambda r: abs(r[5]))
        return [(T("ea_chk_kpi"), f"{el} {d:+.2f} %".replace("-", "−"), True)] + out

    def si_parts(self):
        """Fertige Zeilen für den SI-Export: [(Klartext, HTML)] für IR und EA (leere fehlen)."""
        self.figure_spec()
        return [x for x in (self._ir_line, getattr(self, "_ram_line", None), self._ea_line) if x and x[0]]

    # -- Abbildung ------------------------------------------------------------------
    def figure_spec(self):
        st = self.st
        peaks = self.peaks()
        self.fill_ir_table(peaks)
        off = set(st.get("ir_off") or [])
        use = [p for p in peaks if round(p["wn"]) not in off]
        self._ir_line = ir_line(use, st["with_int"]) if use else ("", "")
        self.txt_ir.setHtml(self._ir_line[1])
        self.update_ea()
        sp = self.spectrum()
        self._fig_kind = "ir"
        if getattr(self, "tbl_ram", None) is not None:
            self.fill_raman()
            view = st.get("ram_view", "ir")
            if st.get("ram_file") and self.raman_spectrum() is None:
                self.add_note(T("raman_unreadable"))
            elif view != "ir" and self.raman_spectrum() is not None:
                if view == "stack" and sp is None:
                    self.add_note(T("raman_stack_no_ir"))
                    view = "raman"
                return self.raman_figure_spec(view)
            elif view != "ir":
                self.add_note(T("raman_view_no_data"))
        if self.pdf_error():
            self.add_note(T("ir_pdf_curve_none", e=self.pdf_error()))
        if sp is None:
            return None
        if self.raw_uncorrected():
            self.add_note(T("ir_base_hint"))
        if st.get("ir_thr") and st.get("ir_pdf"):
            self.add_note(T("ir_thr_pdf"))
        cfg = self.base_cfg()
        (lo, hi), _ = self.ir_range()
        x0, x1 = (st["x_min"], st["x_max"]) if not st["x_auto"] else (min(lo, hi), max(lo, hi))
        cfg["xlim"] = [x1, x0]                           # Wellenzahl fällt nach rechts (IR-Konvention)
        mode = self.mode()
        y = display_y(sp, mode)
        sel = (sp["wn"] >= x0) & (sp["wn"] <= x1)
        manual = None if st.get("y_auto", True) else (st["y_min"], st["y_max"])
        cfg["ylim"], rejected = y_limits(y[sel], mode, manual)
        if rejected:
            self.add_note(T("ir_yrange_bad"))
        cfg["xlabel"] = "wavenumber [cm$^{-1}$]"
        cfg["ylabel"] = "transmittance [%]" if mode == "T" else "absorbance"
        cfg["legend"] = False
        curves = [{"x": sp["wn"], "y": y, "color": st.get("ir_color") or IR_COLOR, "label": None, "ls": "-", "lw": min(20.0, max(0.05, float(st.get("ir_lw", 1.0))))}]
        self._irc_drawn = None
        r_c = self.calc_modes()
        if r_c is not None:                              # berechnetes Spektrum in der Darstellung der Messung
            fw = st.get("irc_fwhm") if st.get("irc_fwhm_on", True) else 0.0
            prof = calc_ir_profile(r_c["modes"], st.get("irc_scale", 1.0), fw, x0, x1)
            if prof is None:
                self.add_note(T("ir_calc_out_of_range"))
            elif sel.any():
                curves[0]["label"] = "exp."
                curves.append({"x": prof[0], "y": calc_ir_display(prof[1], y[sel], mode),
                               "color": st.get("irc_color") or IRC_COLOR, "ls": "-", "label": "calc.",
                               "lw": min(20.0, max(0.05, float(st.get("ir_lw", 1.0))))})
                cfg["legend"] = True
                cfg["legend_beside"] = True              # keine freie Stelle: neben die Achse, nie über die Kurven
                self._irc_drawn = fw
        elif st.get("irc_file"):
            self.add_note(T("ir_calc_unreadable"))
        labels = []
        if getattr(self, "_preview", False) and self.btn_thr.isChecked() and st.get("ir_thr"):   # nur Vorschau
            px_, py_ = np.array(sorted(st["ir_thr"])).T
            # dicht abgetastet: in %T ist die (in A lineare) ausgewertete Linie gekrümmt – Bild = Auswertung
            lx = np.union1d(np.linspace(min(x0, px_.min()), max(x1, px_.max()), 400), px_)
            ly = np.interp(lx, px_, py_)
            yv = (lambda a: a) if mode == "A" else to_transmission
            curves += [{"x": lx, "y": yv(ly), "color": "#d0021b", "ls": "--", "lw": 0.8, "label": None, "aux": True},
                       {"x": px_, "y": yv(py_), "color": "#d0021b", "ls": "None", "marker": "o", "ms": 3,
                        "label": None, "aux": True}]
        if use:
            px = np.array([p["wn"] for p in use])
            o = np.argsort(sp["wn"])
            py = np.interp(px, sp["wn"][o], y[o])
            vis = (py >= cfg["ylim"][0]) & (py <= cfg["ylim"][1])   # fester y-Bereich: Peaks außerhalb ohne Marke/Label
            use = [p for p, v in zip(use, vis) if v]
            px, py = px[vis], py[vis]
            if st.get("ir_labels"):                     # Labels am Peak: unter dem Minimum bzw. über dem Maximum
                for p, yv in zip(use, py):
                    if x0 <= p["wn"] <= x1 and np.isfinite(yv):
                        labels.append({"key": f"label_ir_{round(p['wn'])}", "lam": p["wn"], "y": float(yv),
                                       "side": "below" if mode == "T" else "above",
                                       "text": wn_text(p["wn"])})
        sp_ = (self.main.compound or {}).get("structure")
        if st.get("ir_struct") and PRJ.has_structure(sp_):   # wie im ε-Tab: Vektorbild, Seitenverhältnis fest
            cfg["images"] = [{"file": sp_, "id": "struktur", "width": st.get("struct_w", 20.0) / 100,
                              "prefer": "auto", "_asset": self.structure_asset(sp_)}]
        self._ir_fig = {"side": "below" if mode == "T" else "above",
                        "fixed": manual is not None and not rejected}
        return cfg, curves, labels, []

    def build(self, fig):
        quiet = TABS.core.LOG
        TABS.core.LOG = lambda *a: None
        try:
            spec = self.figure_spec()
        finally:
            TABS.core.LOG = quiet
        if spec is None:
            return None
        cfg, curves, labels, sticks = spec
        TABS.core.setup_fonts(TABS.plt, cfg)
        F = IRFigure(TABS.plt, cfg, curves, labels, self.layout(), fig=fig, sticks=sticks, **self._ir_fig)
        if F.ir_clamped:
            self.add_note(T("ir_labels_clamped", n=len(F.ir_clamped)))
        return F

    def render(self):
        self._preview = True                             # Schwellenlinie nur in der Vorschau, nie in Export/SI
        try:
            super().render()
        finally:
            self._preview = False
        if getattr(self, "_thr_cid", None) is not None:
            self.canvas.mpl_disconnect(self._thr_cid)
            self._thr_cid = None
        if self.F is not None and self.btn_thr.isChecked():
            self._thr_cid = self.canvas.mpl_connect("button_press_event", self.threshold_clicked)

    def threshold_clicked(self, ev):
        """Schwellenmodus: Linksklick = Stützpunkt (in Datenkoordinaten, gespeichert als Absorbanz), Rechtsklick =
        nächsten Stützpunkt entfernen. Klicks auf Labels bleiben beim Verschieben."""
        F = self.F
        if F is None or ev.inaxes is not F.ax or ev.dblclick or ev.xdata is None or ev.button not in (1, 3):
            return
        if any(a.contains(ev)[0] for a in F.ann_items.values()):
            return
        thr = [list(p) for p in self.st.get("ir_thr") or []]
        if ev.button == 1:
            a = float(ev.ydata) if self.mode() == "A" else float(to_absorbance([ev.ydata])[0])
            if not np.isfinite(a):
                return
            thr.append([round(float(ev.xdata), 2), a])
        elif thr:
            yv = lambda a: a if self.mode() == "A" else float(to_transmission(a))        # noqa: E731
            pix = F.ax.transData.transform([(x_, yv(a_)) for x_, a_ in thr])
            thr.pop(int(np.argmin(np.hypot(pix[:, 0] - ev.x, pix[:, 1] - ev.y))))
        else:
            return
        self.st["ir_thr"] = sorted(thr)
        self.sync_widgets()
        self.render()

    def clear_threshold(self):
        self.st["ir_thr"] = []
        self.sync_widgets()
        self.render()

    def hover_text(self, x, val, name):
        fmt = ".1f" if self.mode() == "T" else ".3f"
        return f"ṽ = {x:.0f} cm⁻¹" + (f"    {val:{fmt}}" if val is not None else "")

    def export_to(self, base: Path):
        """Abbildung (falls Spektrum) und die SI-Zeilen als Text."""
        base = Path(base)
        files = []
        if self.spectrum() is not None or self.raman_spectrum() is not None:
            files = super().export_to(base)
        else:
            self.figure_spec()
        p = base.with_name(base.name + "_SI.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(x for x in (self._ir_line[0], self._ram_line[0], self._ea_line[0]) if x) + "\n",
                     encoding="utf-8")
        return files + [p]
