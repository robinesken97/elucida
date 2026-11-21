"""elucida/core/ms_flags.py - Hinweise auf Fremdpeaks im HRMS-Tab: bekannte Untergrund-Ionen (assets/ms/contaminants.tsv,
Keller et al. 2008), eigene Einträge (je Computer in den Einstellungen, nie im Projekt), Edukte/Reagenzien des
Syntheseschemas und Bruchstücke der Verbindung (−N2, −H2O, −CO, −CO2). Alle m/z rechnet Elucida selbst (ir_ea.ion).
Nur Hinweise: nichts wird ausgeblendet, nichts kommt in SI-Zeile, SI-Abbildung oder Export."""
from __future__ import annotations

import json
import re

import numpy as np

from elucida import ROOT
from elucida.tabs.ir_ea import ADDUCTS, adduct_ui, formula_str, ion, parse_formula, parse_ion, ppm

SHIPPED = ROOT / "assets" / "ms" / "contaminants.tsv"
OWN_KEY = "ms_contaminants_own"            # QSettings: JSON-Liste [{name, formula, ions}]
WINDOW_PPM = 5.0                           # Vorgabe des Fensters (im Tab einstellbar, `cont_ppm`)
LOSSES = ("N2", "H2O", "CO", "CO2")        # Bruchstücke der Verbindung
PEAK_FLOOR = 0.01                          # Rohdaten: nur Linien ab 1 % der stärksten im gemittelten Spektrum


def shipped() -> list[dict]:
    """Mitgelieferte Liste -> [dict(key, name_en, name_de, formula, kind, series_unit, n_range, typical_ions, polarity,
    source)]; Kommentarzeilen (#) und Kopf übersprungen."""
    rows, head = [], None
    for line in SHIPPED.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if head is None:
            head = cells
            continue
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return rows


def own_entries(settings) -> list[dict]:
    """Eigene Einträge dieses Computers [dict(name, formula, ions)] (fehlend/kaputt -> [])."""
    try:
        rows = json.loads(settings.value(OWN_KEY, "[]") or "[]")
        return [dict(name=str(r.get("name", "")), formula=str(r.get("formula", "")), ions=str(r.get("ions", "")))
                for r in rows if isinstance(r, dict)]
    except (TypeError, ValueError):
        return []


def save_own(settings, rows):
    """Eigene Einträge speichern; leere Liste entfernt den Schlüssel (= nur die mitgelieferte Liste)."""
    if rows:
        settings.setValue(OWN_KEY, json.dumps(rows, ensure_ascii=False))
    else:
        settings.remove(OWN_KEY)


def _charge_of(formula: str) -> int:
    m = re.search(r"([+\-−]+)(\d*)$", formula.strip())
    if not m:
        return 0
    return (1 if m.group(1)[0] == "+" else -1) * int(m.group(2) or len(m.group(1)))


def _ion_z(spec: str, formula: str, polarity: str) -> int:
    """Ladung eines Ions: aus den Gruppen (+Na: +1, −H: −1, +HCOO: −1), sonst aus der Ladung der Formel, sonst aus
    der Polarität der Liste (nur eindeutig + oder −)."""
    _, _, z, _ = parse_ion(spec)
    z = z + _charge_of(formula)
    if z == 0 and polarity in ("+", "−", "-"):
        z = 1 if polarity == "+" else -1
    return z


def _members(entry):
    """[(Formel, n oder None)]: Einzelstoff oder Reihe Endgruppe + n·Einheit."""
    f = entry.get("formula", "").strip()
    if entry.get("kind") != "series" or not entry.get("series_unit"):
        return [(f, None)] if f else []
    a, _, b = (entry.get("n_range") or "1-1").partition("-")
    unit = parse_formula(entry["series_unit"])
    end = parse_formula(f) if f else {}
    out = []
    for n in range(int(a), int(b or a) + 1):
        c = dict(end)
        for el, k in unit.items():
            c[el] = c.get(el, 0) + n * k
        out.append((formula_str(c) + ("+" if _charge_of(f) > 0 else "-" if _charge_of(f) < 0 else ""), n))
    return out


def reference_ions(entries, lang="en", kind="list"):
    """Alle Ionen der Einträge -> [(m/z, z, Text, Art)]; Text z. B. „Siloxan … (n = 5) [M+H]⁺“. Einträge oder Ionen,
    die sich nicht rechnen lassen, fallen still weg (eigene Einträge zeigt die Karte mit Hinweis)."""
    out = []
    for e in entries:
        name = (e.get("name_de") if lang == "de" else e.get("name_en")) or e.get("name") or e.get("formula", "")
        for f, n in _members(e):
            for spec in (s.strip() for s in (e.get("typical_ions") or e.get("ions") or "").split(";")):
                if not spec:
                    continue
                try:
                    z = _ion_z(spec, f, e.get("polarity", ""))
                    if not z:
                        continue
                    spec_ = re.sub(r"^n(?=M)", "", spec)
                    mz = ion(f, (spec_, z))[2]
                except ValueError:
                    continue
                label = name + (f" (n = {n})" if n is not None else "")
                out.append((mz, z, f"{label} {adduct_ui((spec_, z))}", kind))
    return out


def own_problem(row) -> str:
    """Eigener Eintrag: '' wenn rechenbar, sonst der nicht lesbare Teil (Formel oder Ion)."""
    try:
        parse_formula(row.get("formula", ""))
    except ValueError:
        return row.get("formula", "") or "–"
    for spec in (s.strip() for s in (row.get("ions") or "").split(";")):
        try:
            if spec and not _ion_z(spec, row["formula"], ""):
                return spec
            if spec:
                ion(row["formula"], (re.sub(r"^n(?=M)", "", spec), _ion_z(spec, row["formula"], "")))
        except ValueError:
            return spec
    return "" if (row.get("ions") or "").strip() else "–"


def reagent_ions(rows, compound_formula, polarity, lang="en"):
    """Edukte/Reagenzien des Syntheseschemas (Zeilen mit lesbarer Summenformel, ohne Produkt und ohne die Verbindung
    selbst) mit allen Addukten der Polarität (ohne [M]⁺/[M]⁻ ungeladener Stoffe); dazu die Verbindung minus N2, H2O,
    CO, CO2 (+H/+Na bzw. −H) als mögliches Bruchstück -> [(m/z, z, Text, Art)]."""
    sign = 1 if polarity == "+" else -1
    own = None
    try:
        own = parse_formula(compound_formula) if compound_formula else None
    except ValueError:
        pass
    out = []
    for r in rows or ():
        f = str(r.get("M") or "").strip()
        if r.get("role") == "product" or not re.search(r"[A-Z]", f):
            continue
        try:
            counts = parse_formula(f)
        except ValueError:
            continue
        if own is not None and counts == own:
            continue
        name = str(r.get("name") or "").strip() or f
        charged = _charge_of(f)
        for key, (_, _, z, _) in ADDUCTS.items():
            if z * sign <= 0 or (key in ("M", "M-") and not charged):
                continue
            try:
                out.append((ion(f, key)[2], z, ("Reagenz" if lang == "de" else "reagent") + f" {name} {adduct_ui(key)}",
                            "reagent"))
            except ValueError:
                continue
    if own is not None:
        word = "mögliches Bruchstück der Verbindung" if lang == "de" else "possible fragment of the compound"
        adds = ("H", "Na") if sign > 0 else ("H",)
        for loss in LOSSES:
            for a in adds:
                spec = f"M-{loss}+{a}" if sign > 0 else f"M-{loss}-{a}"
                try:
                    mz = ion(compound_formula, (spec, sign))[2]
                except ValueError:
                    continue
                out.append((mz, sign, f"{word} {adduct_ui((spec, sign))}", "fragment"))
    return out


def flag(mzs, refs, window_ppm=WINDOW_PPM, polarity="+", skip=()):
    """Gemessene m/z gegen Referenz-Ionen der Polarität -> {Index: (Text, found − calc in ppm, Art)}; die nächste im Fenster
    gewinnt. skip: m/z, die nie markiert werden (Ion der Verbindung samt Isotopen)."""
    sign = 1 if polarity == "+" else -1
    ref = sorted((m, t, k) for m, z, t, k in refs if z * sign > 0)
    if not ref:
        return {}
    rm = np.array([r[0] for r in ref])
    sk = np.array(sorted(skip), float)
    out = {}
    for i, v in enumerate(mzs):
        v = float(v)
        if len(sk) and np.min(np.abs(sk - v)) <= v * window_ppm * 1e-6:
            continue
        j = int(np.searchsorted(rm, v))
        best = min((k for k in (j - 1, j) if 0 <= k < len(rm)), key=lambda k: abs(rm[k] - v))
        d = ppm(v, rm[best])
        if abs(d) <= window_ppm:
            out[i] = (ref[best][1], d, ref[best][2])
    return out


def strong_lines(mz, it, floor=PEAK_FLOOR):
    """Linien eines gemittelten Spektrums ab `floor` der stärksten -> (m/z, rel. Intensität %) nach Intensität."""
    mz, it = np.asarray(mz, float), np.asarray(it, float)
    if not len(mz) or not it.max() > 0:
        return np.zeros(0), np.zeros(0)
    rel = 100 * it / it.max()
    o = np.argsort(-rel)
    o = o[rel[o] >= 100 * floor]
    return mz[o], rel[o]


def hint_text(text, dev) -> str:
    """„TPPO [M+H]⁺, +0.8 ppm“ (echtes Minus)."""
    return f"{text}, {f'{dev:+.1f}'.replace('-', '−')} ppm"
