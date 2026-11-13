"""
elucida/app/comparison.py - Projektseite „Vergleich“: benannte Vergleiche über die Verbindungen eines Projekts
(CV-Stapel, Spektren, Eigenschaftstabelle).

Nichts wird ein zweites Mal ausgewertet: jede Verbindung schreibt beim Speichern einen kleinen Stand ihrer Tabs nach
`.elucida/compare.json` (`write_snapshot`, Kurven ausgedünnt, Werte als Text wie im Tab). Jeder Eintrag trägt einen
Fingerabdruck des gespeicherten Tab-Zustands; passt er nicht mehr zur Projektdatei, gilt der Eintrag als veraltet und
wird nicht gezeigt. „Aktualisieren“ öffnet die betroffenen Verbindungen kurz (wie die Gesamt-SI) und schreibt den Stand
neu. Die Seite selbst ist ein `FigureTab` (Schritte, Vorschau, Ziehen, Export) in einem kleinen Gastgeber wie der
Reaktionspfad (`CompareHost`); die Vergleiche stehen in `publication.elucida` unter `comparisons`.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import html
import json
import os
import re
import uuid
from pathlib import Path

import numpy as np
import yaml
from PySide6.QtCore import QMimeData, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox,
                               QHBoxLayout, QHeaderView, QLineEdit,
                               QMainWindow, QMenu, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app import publication as PUB
from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS, make_form
from elucida.core import uvvis as core
from elucida.tabs import base as TABS

SNAP_FILE = "compare.json"
SNAP_VERSION = 1
SOURCES = ("eps", "cv", "fluo", "epr", "irms", "xray", "dft", "nmr")   # Zustandsschlüssel der Tabs mit Stand
MAX_POINTS = 1500                                  # Kurven im Stand: höchstens so viele Punkte (Datei bleibt klein)
MAX_CYCLES = 10                                    # CV: Zyklen 1 … 10 je Messung im Stand (dazu der ausgewertete)
KINDS = ("cv", "spectra", "table")
EPR_NU_TOL = 2e-4                                  # gleiche Mikrowellenfrequenz (relativ), wie der EPR-Tab beim Dunkelspektrum


# ============================================================================ Stand je Verbindung (Schreiben)
def _rel_strings(obj, root):
    """Absolute Pfade im Projektordner -> relativ (wie in der Projektdatei); Verschieben des Ordners ändert nichts."""
    if isinstance(obj, dict):
        return {str(k): _rel_strings(v, root) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_rel_strings(v, root) for v in obj]
    if isinstance(obj, str) and obj.startswith(root):
        return Path(obj).relative_to(root).as_posix()
    return obj


def fingerprint(part, pdir) -> str:
    """Fingerabdruck eines gespeicherten Tab-Zustands (Projektdatei oder Zustand beim Speichern: gleiche Zahl)."""
    root = str(Path(pdir).resolve()) + os.sep
    txt = json.dumps(_rel_strings(part, root), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(txt.encode("utf-8")).hexdigest()[:16]


def has_data(key, st) -> bool:
    """Hat der gespeicherte Tab überhaupt Daten (sonst gehört kein Stand dazu)?"""
    st = st or {}
    if key == "eps":
        return bool(st.get("files"))
    if key == "cv":
        return any(e.get("visible", True) for e in st.get("files") or [])
    if key == "fluo":
        return bool(st.get("abs_file") or st.get("em_file"))
    if key in ("epr", "xray", "dft"):
        return bool(st.get("entries"))
    if key == "irms":
        return bool(st.get("ir_file") or st.get("ir_pdf"))
    if key == "nmr":
        return bool((st.get("text") or "").strip())
    return False


def _num(v):
    return float(f"{float(v):.6g}")


def _thin(x, y, n=MAX_POINTS):
    """Kurve auf höchstens n Punkte ausdünnen (jeder k-te Punkt, Enden bleiben) -> Listen."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    k = max(1, int(np.ceil(len(x) / n)))
    idx = np.r_[np.arange(0, len(x), k), len(x) - 1] if len(x) else np.array([], int)
    idx = np.unique(idx)
    return [_num(v) for v in x[idx]], [_num(v) if np.isfinite(v) else None for v in y[idx]]


class _EpsView:
    """Die Übernahme einer ε-Serie wie im Overlay (`OverlayTab.eps_linked`) ohne den Overlay-Tab zu bauen."""
    eps_series = TABS.OverlayTab.eps_series
    eps_linked = TABS.OverlayTab.eps_linked

    def __init__(self, main):
        self.main = main


def _eps_entry(main):
    """ε-Tab: je Serie die Banden des Bildes (λ, ε wie Tabelle/SI-Zeile) und das Spektrum wie im Overlay (Messung der
    Serie, Basislinie wie dort, Absorbanz und Faktor auf ε)."""
    if not getattr(main, "csv_paths", None):
        return None
    view, out = _EpsView(main), []
    bl = dict(core.deep_merge(core.DEFAULTS, {}), baseline_nm="auto", baseline_mode="simple", conc_unit="mM")
    for g in main.groups:
        cfg2, _, results = core.prepare_series(main.make_cfg(g), main.groups[g], g)
        molar = bool(core.conc_factor(cfg2))
        xl, bands = cfg2.get("xlim"), []
        mark_sh = (cfg2.get("labels") or {}).get("mark_shoulders")
        for r in sorted(results, key=lambda r: r["lam"]):           # wie SI.uvvis_line: nur Banden des Bildes
            if not r.get("fit") or r.get("hidden") or (xl and not min(xl) <= r["lam"] <= max(xl)):
                continue
            v, _ = core.fmt_ve(r["eps"], r["eps_err"], max_decimals=core.eps_max_decimals(cfg2))
            bands.append({"lam": core.fmt_lam(r["lam"]), "coef": v, "sh": bool(r.get("shoulder") and mark_sh)})
        curve = None
        s_, e = view.eps_linked({"series": g, "sample": None})
        if s_ is not None:
            tmp = [{"x": np.asarray(s_["x"], float).copy(), "y": np.asarray(s_["y"], float).copy(), "c": 1.0}]
            core.apply_baseline(tmp, bl)
            fac = (1 / e["mw"] if e.get("mw") else None) if e.get("unit") == "mg/mL" else core.CONC_TO_M.get(e.get("unit"))
            x, a = _thin(tmp[0]["x"], tmp[0]["y"])
            curve = {"x": x, "a": a, "eps_fac": (1.0 / (e["conc"] * fac * e.get("d", 1.0))
                                                 if e.get("conc") and fac else None)}
        out.append({"name": g, "solvent": (main.series.get(g) or {}).get("solvent", ""), "molar": molar,
                    "bands": bands, "curve": curve})
    return {"series": out}


def _quiet(fn):
    quiet = core.LOG
    core.LOG = lambda *a: None
    try:
        return fn()
    finally:
        core.LOG = quiet


def _cv_entry(main):
    """CV-Tab: je sichtbarer Messung die Kurve des gewählten Zyklus auf der Achse des Tabs (Referenz wie dort, Strom in
    µA wie aufgezeichnet bzw. umgekehrt wie im Tab) und die Redoxpaare mit den Zahlen der Ergebnistabelle."""
    from elucida.tabs import cv as CV
    tab = main.cv_tab
    st = tab.st
    vis = [e for e in st["files"] if e.get("visible", True)]
    if not vis:
        return None
    _quiet(tab.figure_spec)                                 # Ergebnisse wie in der Tabelle (tab.results)
    sign = -1.0 if st.get("invert") else 1.0
    files = []
    for e in vis:
        d = tab.data(e["file"])
        c = tab.cycle_of(e)
        off, lab, _ = tab.file_offset(e)
        x, y = _thin(np.asarray(c["E"]) - off, sign * 1e6 * np.asarray(c["I"]))
        ev = min(st["cycle"], len(d["cycles"]))
        others = []                                         # weitere Zyklen (nur Kurve, ohne Auswertung)
        for n, c2 in enumerate(d["cycles"][:MAX_CYCLES], 1):
            if n != ev:
                x2, y2 = _thin(np.asarray(c2["E"]) - off, sign * 1e6 * np.asarray(c2["I"]))
                others.append({"n": n, "x": x2, "y": y2})
        couples = [{"n": r["n"], "epa": r["epa"], "epc": r["epc"], "e12": r["e12"], "dep": r["dep"],
                    "ipa": sign * 1e6 * r["ipa_raw"], "ipc": sign * 1e6 * r["ipc_raw"], "edge": bool(r["edge"]),
                    "fwd": "epa" if r.get("anodic_first", True) else "epc",
                    "t_epa": CV._fmt_e(r["epa"]), "t_epc": CV._fmt_e(r["epc"]), "t_e12": CV._fmt_e(r["e12"]),
                    "t_dep": f"{r['dep'] * 1000:.0f}"} for r in tab.results if r["uid"] == e["uid"]]
        files.append({"uid": e["uid"], "label": e["label"], "rate": d["meta"].get("scanrate"),
                      "cycle": ev, "n_cycles": len(d["cycles"]), "ref": lab, "group": e.get("group", ""),
                      "x": x, "y": y, "couples": couples, "cycles": others})
    return {"files": files, "cap": {k: st.get("cap_" + k, "") for k in ("conc", "solvent", "el", "temp")}}


def _fluo_entry(main):
    """Fluoreszenz-Tab: Emission normiert wie im Bild, λem/λabs/Stokes wie die Kennwerte des Tabs."""
    tab = main.fl_tab
    st = tab.st
    if not (st.get("abs_file") or st.get("em_file")):
        return None
    spec = _quiet(tab.figure_spec)
    info = getattr(tab, "info", None) or {}
    em_ok = bool(st.get("em_file")) and tab.sample(st["em_file"], st.get("em_sample")) is not None
    out = {"lam_em": f"{info['lam_em']:.0f}" if info.get("lam_em") else "",
           "lam_abs": f"{info['lam_abs']:.0f}" if info.get("lam_abs") else "",
           "stokes": TABS.fmt_stokes(info["stokes_cm"]) if info.get("stokes_cm") is not None else "",
           "ex": st.get("ex"), "solvent": st.get("cap_solvent", ""), "em": None}
    if spec is not None and em_ok:
        em = [c for c in spec[1] if c.get("ls") != "--"][-1]        # Reihenfolge im Tab: Absorption, Emission
        x, y = _thin(em["x"], em["y"])
        out["em"] = {"x": x, "y": y}
    return out


def _epr_entry(main):
    """EPR-Tab: g und Kopplungen nur aus eigenen, gültigen S = ½-Fits (wie die Unterschrift), D und |E|/D aus den
    EasySpin-Parametern der Simulationen (Stellen wie die Anzeige im Tab)."""
    from elucida.tabs import epr as EPR
    tab = main.epr_tab
    st = tab.st
    if not st.get("entries"):
        return None
    vis = [e for e in st["entries"] if e.get("visible", True)]
    dB, calib_t = tab.calibration_shift()
    species, zfs = [], []
    for e in vis:
        if e["kind"] == "iso" and tab.fit_ok(e) and not (dB and e.get("fit_to") == calib_t):
            hfc = [[n, nm, EPR.hfc_texts(a, e["g"])[1]]
                   for (n, _, a), nm in zip(tab.iso_groups(e), EPR.nuclei_names(e.get("nuclei", "")))]
            species.append({"label": e.get("label", ""), "g": EPR.g_text(e["g"]), "hfc": hfc})
        elif e["kind"] == "sim" and e.get("params") and Path(e["params"]).exists():
            pr = EPR.parse_easyspin(Path(e["params"]).read_text(encoding="utf-8", errors="replace"))
            d = pr.get("Sys.D")
            if isinstance(d, list) and d:
                D, E = EPR.zfs_DE(d)
                zfs.append({"label": e.get("label", ""), "D": f"{D / EPR.MHZ_PER_CM:.4f}".replace("-", "−"),
                            "ED": f"{abs(E / D) if D else 0:.3f}"})
    # Messungen wie im Bild verarbeitet (Feld in mT nach Skalierung/Kalibrierung des Tabs), dazu die Frequenz der Achse
    traces, cache = [], {}
    for e in vis:
        if e["kind"] != "exp":
            continue
        B, I = tab.processed(e, cache)
        if not len(B):
            continue
        x, y = _thin(B, I)
        nu = tab.axis_mw(e)
        traces.append({"uid": e["uid"], "label": e.get("label", ""), "x": x, "y": y,
                       "nu": float(nu) if nu else None})
    return {"species": species, "zfs": zfs, "traces": traces, "unit": st.get("unit", "mT")}


def _ir_entry(main):
    """IR-Tab: Banden der Liste des Tabs (ohne abgewählte, Text wie dort) und das Spektrum wie im Bild (%T oder A)."""
    from elucida.tabs import ir_ea as IR
    tab = main.irms_tab
    st = tab.st
    off = set(st.get("ir_off") or [])
    use = [p for p in tab.peaks() if round(p["wn"]) not in off]
    out = {"peaks": [{"wn": _num(p["wn"]), "t": IR.wn_text(p["wn"])} for p in sorted(use, key=lambda p: -p["wn"])],
           "curve": None}
    sp = tab.spectrum()
    if sp is not None:
        mode = tab.mode()
        x, y = _thin(sp["wn"], IR.display_y(sp, mode))
        out["curve"] = {"x": x, "y": y, "mode": mode}
    return out


def _xray_entry(main):
    """X-Ray-Tab: je Struktur die „Ausgewählten Parameter“ (Text wie in der CIF, echtes Minus; selbst gerechnete ohne
    esd) mit dem Zeilennamen aus den Atomlabels (`param_label`), dazu Raumgruppe und Kristallsystem."""
    from elucida.tabs import xray as XRAY
    tab = main.xray_tab
    out = []
    for e in tab.entries():
        S = tab.structure(e)
        if S is None:
            continue
        mol = tab.molecule(e)
        params = []
        for p in e.get("params") or []:
            m = XRAY.measure(mol, p["atoms"]) if mol else None
            if m is not None:
                params.append({"kind": m["kind"], "label": XRAY.param_label(p["atoms"]), "t": XRAY.minus(m["text"]),
                               "cif": m["source"] == "cif"})
        cv = XRAY.crystal_values(S.block)
        out.append({"name": e.get("name") or e["block"], "params": params, "sg": cv["sg"], "system": cv["system"]})
    return {"structures": out}


def _frontier(table):
    """HOMO/LUMO in eV wie der DFT-Tab sie zeigt (zwei Stellen, echtes Minus); nur geschlossenschalig mit ganzen
    Besetzungen, sonst leer."""
    rows = table.get("")
    if not rows or "a" in table or any(min(abs(o - k) for k in (0, 1, 2)) > 1e-3 for _, o, _ in rows):
        return "", ""
    homo = max((n for n, o, _ in rows if o > 0.5), default=None)
    by = {n: en for n, _, en in rows}
    fmt = lambda v: f"{v:.2f}".replace("-", "−") if v is not None and v == v else ""      # noqa: E731
    return (fmt(by.get(homo)), fmt(by.get(homo + 1))) if homo is not None else ("", "")


def _dft_entry(main):
    """DFT-Tab: je Rechnung Eingabezeile, E(el), G (Text wie in der Ausgabe) und HOMO/LUMO wie der Tab sie zeigt."""
    from elucida.tabs import xray as XRAY
    tab = main.dft_tab
    calcs = []
    for e in tab.st.get("entries") or []:
        c = tab.calc_of(e)
        if c is None:
            continue
        th = c["thermo"]
        mr = bool(c.get("multireference"))          # wie die SI: allgemeine Energie bezeichnet keinen MR-Zustand
        e_el = "" if mr else (th.get("E_el") or c.get("energy") or "")
        homo, lumo = _frontier(tab.orb_table(e))
        calcs.append({"uid": e.get("uid") or e["file"], "name": e.get("name") or Path(e["file"]).stem,
                      "method": " ".join(c["keywords"]), "e_el": XRAY.minus(str(e_el)) if e_el else "",
                      "g": XRAY.minus(str(th["G"])) if th.get("G") and not mr else "", "homo": homo, "lumo": lumo})
    return {"calcs": calcs}


def _shift_range(t):
    v = [float(x.replace("−", "-")) for x in re.findall(r"[−-]?\d+(?:\.\d+)?", t)]
    return (min(v), max(v)) if v else None


def _nmr_entry(main):
    """NMR: Signale des Multiplettberichts im Tab (Verschiebung als Text wie in der NMR-Zeile)."""
    from elucida.tabs import nmr as NMR
    from elucida.tabs import xray as XRAY
    sigs = []
    for b in NMR.parse_mnova((main.nmr_state or {}).get("text") or ""):
        for s in b["signals"]:
            r = _shift_range(s["shift"])
            if r is not None:
                sigs.append({"nuc": b["nucleus"], "t": XRAY.minus(s["shift"]), "lo": r[0], "hi": r[1]})
    return {"signals": sigs}


ENTRY = {"eps": _eps_entry, "cv": _cv_entry, "fluo": _fluo_entry, "epr": _epr_entry, "irms": _ir_entry,
         "xray": _xray_entry, "dft": _dft_entry, "nmr": _nmr_entry}
TAB_KEY = {"cv": "cv", "fluo": "fluo", "epr": "epr", "irms": "irms", "xray": "xray", "dft": "dft"}   # -> Tab (gebaut?)


def snapshot_path(pdir) -> Path:
    return Path(pdir) / PRJ.WORK / SNAP_FILE


def load_snapshot(pdir) -> dict:
    try:
        data = json.loads(snapshot_path(pdir).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("version") == SNAP_VERSION else {}
    except (OSError, ValueError):
        return {}


def write_snapshot(main, state):
    """Stand der Verbindung nach `.elucida/compare.json` (beim Speichern, `MainWindow.autosave`): nur Tabs, deren
    gespeicherter Zustand sich seit dem letzten Stand geändert hat und die in dieser Sitzung gebaut sind, werden neu
    ausgelesen; ein nicht gebauter Tab behält seinen alten Eintrag (gilt dann als veraltet). -> geschriebene Tabs."""
    pdir = Path(main.project_dir).resolve()
    old = load_snapshot(pdir).get("tabs") or {}
    tabs, done = {}, []
    for key in SOURCES:
        fp = fingerprint(state.get(key), pdir)
        prev = old.get(key)
        if prev and prev.get("fp") == fp:
            tabs[key] = prev
            continue
        built = key not in TAB_KEY or main._built(TAB_KEY[key])          # ε und NMR: nur der Zustand
        if not built:
            if prev:
                tabs[key] = prev
            continue
        try:                                                # ein Tab mit Fehler nimmt den anderen ihren Stand nicht
            entry = ENTRY[key](main) if has_data(key, state.get(key)) else None
        except Exception:
            import traceback
            main.log_signal.emit(T("cmp_snapshot_failed") + f" ({key})\n" + traceback.format_exc())
            if prev:
                tabs[key] = prev
            continue
        tabs[key] = dict(entry or {}, fp=fp)
        done.append(key)
    if tabs == old:
        return done
    p = snapshot_path(pdir)
    PRJ.work_dir(pdir)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": SNAP_VERSION, "tabs": tabs}, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    os.replace(tmp, p)
    return done


# ============================================================================ Stand je Verbindung (Lesen)
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def read_compound(cdir, rel=None) -> dict:
    """Verbindung für den Vergleich: Name, Formel, Molmasse, Schmelzpunkt, Struktur aus der Projektdatei; gültige Einträge
    des Stands (`tabs`), veraltete (`stale`) und fehlende (`missing`: Daten im Tab, aber kein Stand)."""
    cdir = Path(cdir).resolve()
    try:
        state = yaml.load(PRJ.project_file(cdir).read_text(encoding="utf-8"), Loader=_LOADER) or {}
    except Exception:
        state = {}
    comp = state.get("compound") or {}
    struct = comp.get("structure")
    if struct and not Path(struct).is_absolute():
        struct = str((cdir / struct).resolve())
    snap = load_snapshot(cdir).get("tabs") or {}
    tabs, stale, missing = {}, [], []
    for key in SOURCES:
        if not has_data(key, state.get(key)):
            continue
        e = snap.get(key)
        if e is None:
            missing.append(key)
        elif e.get("fp") != fingerprint(state.get(key), cdir):
            stale.append(key)
        else:
            tabs[key] = e
    return {"dir": cdir, "rel": rel or cdir.name, "name": comp.get("name") or cdir.name,
            "formula": comp.get("formula") or "", "mw": comp.get("mw"), "mp": comp.get("mp") or "",
            "oil": bool(comp.get("oil")), "structure": struct if struct and Path(struct).exists() else None,
            "tabs": tabs, "stale": stale, "missing": missing}


def needs(kind) -> tuple:
    return {"cv": ("cv",), "spectra": ("eps", "fluo", "irms", "epr"), "table": SOURCES}.get(kind, ())


def status(rec, kind) -> str:
    """„ok“, „outdated“ (Stand passt nicht mehr), „missing“ (Daten ohne Stand) oder „none“ (keine Daten)."""
    keys = needs(kind)
    if any(k in rec["stale"] for k in keys):
        return "outdated"
    if any(k in rec["missing"] for k in keys):
        return "missing"
    return "ok" if any(k in rec["tabs"] for k in keys) else "none"


def refresh_compounds(main, pdir, dirs, keys=SOURCES):
    """Verbindungen ohne oder mit veraltetem Stand kurz öffnen, die Tabs bauen und speichern (schreibt den Stand), danach
    den vorherigen Zustand wiederherstellen – wie `MainWindow.export_publication_si`. -> Zahl erneuerter Verbindungen."""
    if not dirs or not main.maybe_save():
        return 0
    prev, n = main.project_dir, 0
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        for d in dirs:
            if not main.open_project(d, recent=False):
                continue
            for key in keys:
                if key in TAB_KEY:
                    getattr(main, main._tab_spec(TAB_KEY[key])[0])        # baut den Tab
            main.autosave(force=True)
            n += 1
    finally:
        if prev:
            main.open_project(prev, recent=False)
        else:
            main.close_project()
            main.open_publication(pdir)
        QApplication.restoreOverrideCursor()
    return n


# ============================================================================ Satz: Kopf, Zellen, Unterschrift
_MINUS = "−"


def _esc(s):
    from elucida.tabs import xray as XRAY
    return XRAY.esc_markup(str(s))


def unit_markup(u):
    """Einheit wie getippt -> Markup: „cm-1“ -> cm^{−1}, „M-1 cm-1“ ebenso."""
    return re.sub(r"(?<=[A-Za-zµÅ])-(\d+)", lambda m: "^{" + _MINUS + m.group(1) + "}", _esc(u.strip()))


def head_markup(quantity, unit=""):
    """Kopf in Normschreibweise „Größe / Einheit“: ein einzelnes Formelzeichen am Anfang kursiv, Einheit steil."""
    q = _esc(quantity.strip())
    q = re.sub(r"^([A-Za-zα-ωΔ])(?=$|[\s(_^])", lambda m: m.group(1) if m.group(1) == "Δ" else f"*{m.group(1)}*", q)
    return q + (" / " + unit_markup(unit) if unit.strip() else "")


# Werte aus den Tabs: Schlüssel -> (Kopf als Markup, Auswahltext)
def _cv_heads(n):
    sup = f"^{{({n})}}" if n > 1 else ""
    return {f"cv{n}_e12": (f"*E*_{{1/2}}{sup} / V", T("cmp_col_e12", n=n)),
            f"cv{n}_epa": (f"*E*_{{pa}}{sup} / V", T("cmp_col_epa", n=n)),
            f"cv{n}_epc": (f"*E*_{{pc}}{sup} / V", T("cmp_col_epc", n=n)),
            f"cv{n}_dep": (f"Δ*E*_{{p}}{sup} / mV", T("cmp_col_dep", n=n))}


def auto_columns(records) -> dict:
    """Werte, die die Stände der Verbindungen anbieten (Reihenfolge wie die Tabs) -> {Schlüssel: (Kopf, Auswahltext)}."""
    out = {"formula": ("Formula", T("cmp_col_formula")), "mw": ("*M* / g mol^{−1}", T("cmp_col_mw")),
           "mp": ("m.p.", T("cmp_col_mp"))}
    have = {k for r in records for k in r["tabs"]}
    if "eps" in have:
        out.update(uv_lam=("*λ*_{max} / nm", T("cmp_col_uv_lam")),
                   uv_eps=("*ε* / M^{−1} cm^{−1}", T("cmp_col_uv_eps")),
                   uv_solv=("Solvent (UV-Vis)", T("cmp_col_uv_solv")))
    if "fluo" in have:
        out.update(fl_abs=("*λ*_{abs} / nm", T("cmp_col_fl_abs")), fl_em=("*λ*_{em} / nm", T("cmp_col_fl_em")),
                   fl_stokes=("Δ*ṽ* / cm^{−1}", T("cmp_col_fl_stokes")))
    if "cv" in have:
        n_max = max((c["n"] for r in records for f in (r["tabs"].get("cv") or {}).get("files", [])
                     for c in f["couples"]), default=1)
        for n in range(1, n_max + 1):
            out.update(_cv_heads(n))
        out["cv_ref"] = ("Reference (CV)", T("cmp_col_cv_ref"))
    if "epr" in have:
        out.update(epr_g=("*g*", T("cmp_col_epr_g")), epr_a=("*a* / MHz", T("cmp_col_epr_a")),
                   epr_D=("*D* / cm^{−1}", T("cmp_col_epr_D")), epr_ED=("|*E*/*D*|", T("cmp_col_epr_ED")))
    if "irms" in have:
        out["ir_band"] = (FIXED_HEADS["ir_band"], T("cmp_col_ir_band"))
    if "nmr" in have:
        out["nmr_shift"] = ("*δ* / ppm", T("cmp_col_nmr_shift"))
    if "xray" in have:
        params = {}
        for r in records:
            for s in (r["tabs"].get("xray") or {}).get("structures", []):
                for p in s["params"]:
                    params.setdefault(xr_key(p["kind"], p["label"]), p["label"])
        for k, lab in params.items():
            out[k] = (_auto_head(k), T("cmp_col_xr_param", p=lab))
        out.update(xr_sg=("Space group", T("cmp_col_xr_sg")), xr_system=("Crystal system", T("cmp_col_xr_system")))
    if "dft" in have:
        out.update({k: (FIXED_HEADS[k], T("cmp_col_" + k)) for k in ("dft_method", "dft_eel", "dft_g", "dft_homo",
                                                                      "dft_lumo")})
    return out


# Köpfe der neuen Tab-Werte (englisch wie die Ausgabe)
FIXED_HEADS = {"ir_band": "*ṽ* / cm^{−1}", "dft_method": "Method (DFT)", "dft_eel": "*E*_{el} / E_{h}",
               "dft_g": "*G* / E_{h}", "dft_homo": "*E*_{HOMO} / eV", "dft_lumo": "*E*_{LUMO} / eV",
               "xr_sg": "Space group", "xr_system": "Crystal system"}
XR_UNIT = {"bond": "Å", "angle": "°", "torsion": "°"}
MARKUP_KEYS = ("xr_sg",)                             # Tab-Werte, die schon Markup sind (Raumgruppe kursiv, tiefgestellt)
IR_TOL, NMR_TOL_H, NMR_TOL = 15.0, 0.5, 2.0          # Vorgaben der Toleranz (cm⁻¹, ppm ¹H, ppm andere Kerne)


def xr_key(kind, label):
    """Spalte eines X-Ray-Parameters: gleiche Atomlabels in beiden Richtungen = dieselbe Spalte."""
    parts = label.split("–")
    return f"xr:{kind}:" + "–".join(min(parts, parts[::-1]))


def _auto_head(key, col=None):
    """Kopf einer Tab-Spalte, auch wenn keine Verbindung sie gerade anbietet."""
    col = col or {}
    if key.startswith("xr:"):
        _, kind, lab = key.split(":", 2)
        return f"{_esc(lab)} / {XR_UNIT.get(kind, '')}"
    if key == "nmr_shift":
        from elucida.tabs import nmr as NMR
        return f"*δ*({NMR.nuc_markup(col.get('nuc') or '1H')}) / ppm"
    if key in FIXED_HEADS:
        return FIXED_HEADS[key]
    m = re.fullmatch(r"cv(\d+)_\w+", key)
    return (_cv_heads(int(m.group(1))).get(key) or ("", ""))[0] if m else key


def head_of(col, records=()):
    if col.get("kind") == "auto":
        if col["key"].startswith("xr:") or col["key"] in FIXED_HEADS or col["key"] == "nmr_shift":
            return _auto_head(col["key"], col)
        known = auto_columns(records)
        if col["key"] in known:
            return known[col["key"]][0]
        return _auto_head(col["key"], col)
    return head_markup(col.get("head", ""), col.get("unit", ""))


def target_text(col):
    """„2100 ± 15“ für IR-/NMR-Spalten (Herkunft in der Liste der Größen), leer ohne Ziel."""
    if col.get("target") is None:
        return ""
    return f"{col['target']:g} ± {col.get('tol', 0):g}".replace("-", "−")


def default_tol(col):
    if col.get("key") == "ir_band":
        return IR_TOL
    return NMR_TOL_H if (col.get("nuc") or "1H") == "1H" else NMR_TOL


def xr_structure(rec, member):
    ss = (rec["tabs"].get("xray") or {}).get("structures") or []
    return next((s for s in ss if s["name"] == member.get("xr_struct")), ss[0] if ss else None)


def dft_calc(rec, member):
    cs = (rec["tabs"].get("dft") or {}).get("calcs") or []
    return next((c for c in cs if c["uid"] == member.get("dft_calc")), cs[0] if cs else None)


def nearest(items, target, tol, dist):
    """Eintrag mit dem kleinsten Abstand zum Ziel innerhalb der Toleranz (Grenze eingeschlossen), sonst None."""
    if target is None:
        return None
    best = min(items, key=dist, default=None)
    return best if best is not None and dist(best) <= tol + 1e-9 else None


def ref_plain(ref):
    """Referenz der CV-Achse („Fc$^{0/+}$“) als Text: „Fc⁰/⁺“."""
    return str(ref or "").replace("$^{0/+}$", "⁰/⁺").replace("$", "")


def default_chapter(item):
    """Kapitel der Gesamt-SI nach Art: CV-Stapel → Cyclic Voltammetry, Spektren nach Inhalt (UV-Vis, IR, EPR),
    Tabelle → eigene Überschrift am Ende (wie „Weitere“ mit `new:<Überschrift>`)."""
    if item.get("kind") == "cv":
        return "cv"
    if item.get("kind") == "spectra":
        c = (item.get("st") or {}).get("content", "eps")
        return "irms" if c == "ir" else "epr" if c in ("epr", "epr_g") else "uvvis"
    return "new"


def si_chapter(item):
    return (item.get("si") or {}).get("chapter") or default_chapter(item)


def si_key(item):
    """Schlüssel für `publication_si.assemble`: Kapitel oder „new:<Überschrift>“ (Standard: Name des Vergleichs)."""
    ch = si_chapter(item)
    return ch if ch != "new" else "new:" + ((item.get("si") or {}).get("heading") or item["name"]).strip()


def cv_file(rec, member):
    files = (rec["tabs"].get("cv") or {}).get("files") or []
    return next((f for f in files if f["uid"] == member.get("file")), files[0] if files else None)


def cycle_of(f, member):
    """Kurve des gewählten Zyklus einer CV-Messung -> (x, y, ausgewertet?, Nummer); ohne Wahl oder wenn der Zyklus nicht
    im Stand liegt, der Zyklus, den der CV-Tab ausgewertet hat."""
    n = (member or {}).get("cycle")
    if n and n != f.get("cycle"):
        c = next((c for c in f.get("cycles") or [] if c["n"] == n), None)
        if c is not None:
            return c["x"], c["y"], False, n
    return f["x"], f["y"], True, f.get("cycle")


def eps_series(rec, member):
    ser = (rec["tabs"].get("eps") or {}).get("series") or []
    return next((s for s in ser if s["name"] == member.get("series")), ser[0] if ser else None)


def auto_value(key, rec, member, col=None) -> str:
    """Wert eines Tabs als Text, genau wie der Tab ihn zeigt; fehlt er, leer (nie geschätzt oder umgerechnet).
    col: die Spalte (IR/NMR: Ziel, Toleranz, Kern)."""
    t = rec["tabs"]
    col = col or {}
    if key == "ir_band":                                  # Bande der Liste des Tabs, die dem Ziel am nächsten liegt
        p = nearest((t.get("irms") or {}).get("peaks") or [], col.get("target"),
                    col.get("tol", IR_TOL), lambda p: abs(p["wn"] - col["target"]))
        return p["t"] if p else ""
    if key == "nmr_shift":                                # Signal (auch Bereich) des Kerns am nächsten am Ziel
        nuc = col.get("nuc") or "1H"
        sigs = [s for s in (t.get("nmr") or {}).get("signals") or [] if s["nuc"] == nuc]
        tg = col.get("target")
        s = nearest(sigs, tg, col.get("tol", default_tol(col)),
                    lambda s: 0.0 if s["lo"] <= tg <= s["hi"] else min(abs(tg - s["lo"]), abs(tg - s["hi"])))
        return s["t"] if s else ""
    if key.startswith("xr"):
        s = xr_structure(rec, member)
        if s is None:
            return ""
        if key in ("xr_sg", "xr_system"):
            return s["sg" if key == "xr_sg" else "system"]
        p = next((p for p in s["params"] if xr_key(p["kind"], p["label"]) == key), None)
        return p["t"] if p else ""
    if key.startswith("dft_"):
        c = dft_calc(rec, member)
        return (c or {}).get({"dft_method": "method", "dft_eel": "e_el", "dft_g": "g", "dft_homo": "homo",
                              "dft_lumo": "lumo"}[key], "")
    if key == "formula":
        from elucida.si import lines as SI
        return SI.chem_plain(rec["formula"]) if rec["formula"] else ""
    if key == "mw":
        return f"{float(rec['mw']):.2f}" if rec.get("mw") else ""
    if key == "mp":
        from elucida.si import lines as SI
        return "<25 °C" if rec.get("oil") else (SI.mp_text(rec["mp"]) if rec["mp"] else "")
    if key.startswith("uv_"):
        s = eps_series(rec, member)
        if s is None:
            return ""
        if key == "uv_solv":
            return s.get("solvent", "")
        if key == "uv_lam":
            return ", ".join(b["lam"] + (" (sh)" if b.get("sh") else "") for b in s["bands"])
        return ", ".join(b["coef"] for b in s["bands"]) if s.get("molar") else ""
    if key.startswith("fl_"):
        f = t.get("fluo") or {}
        return f.get({"fl_abs": "lam_abs", "fl_em": "lam_em", "fl_stokes": "stokes"}[key], "")
    if key == "cv_ref":
        f = cv_file(rec, member)
        return ref_plain(f["ref"]) if f else ""
    m = re.fullmatch(r"cv(\d+)_(e12|epa|epc|dep)", key)
    if m:
        f = cv_file(rec, member)
        c = next((c for c in (f or {}).get("couples", []) if c["n"] == int(m.group(1))), None)
        return "" if c is None or c["edge"] else c["t_" + m.group(2)]     # Peak am Fensterrand: kein Ergebnis
    e = t.get("epr") or {}
    if key == "epr_g":
        return ", ".join(s["g"] for s in e.get("species", []))
    if key == "epr_a":
        return "; ".join(", ".join(f"{n}×{nm} {a}" for n, nm, a in s["hfc"]) for s in e.get("species", []) if s["hfc"])
    if key in ("epr_D", "epr_ED"):
        return ", ".join(z[key[4:]] for z in e.get("zfs", []))
    return ""


def _join_names(names):
    names = [f"<b>{html.escape(n)}</b>" for n in names]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _per_compound(values, fmt):
    """Angabe aus den Feldern der Verbindungen: gleich für alle -> einmal, sonst je Verbindung („X (A), Y (B)“)."""
    vals = [(n, v) for n, v in values if v]
    if not vals:
        return ""
    if len({v for _, v in vals}) == 1 and len(vals) == len(values):
        return fmt(vals[0][1])
    groups = {}
    for n, v in vals:
        groups.setdefault(v, []).append(n)
    return ", ".join(f"{fmt(v)} ({_join_names(ns)})" for v, ns in groups.items())


# ============================================================================ Gastgeber und Tabs
class GroupRule(STYLE.RichDelegate):
    """Vorschau der Tabelle: die Linie unter dem Gruppenkopf steht nur unter den Spalten der Gruppe (eingerückt, wie
    in gedruckten Tabellen und im Word-Export), leere Zellen der Gruppenzeile haben keine – der Kopf gehört so sichtbar
    zu seinen Spalten statt lose in der Zeile zu stehen (Nutzerwunsch 2026-11-12)."""

    def paint(self, painter, option, index):
        role = (index.data(Qt.UserRole) or ("",))[0]
        if role != "group":
            return super().paint(painter, option, index)
        self._paint(painter, option, index)
        if index.data(Qt.DisplayRole):
            painter.save()
            painter.setPen(QColor(STYLE.colors()["text2"]))
            r = option.rect
            painter.drawLine(r.left() + self.PAD, r.bottom(), r.right() - self.PAD, r.bottom())
            painter.restore()


class _FitGrid(QTableWidget):
    """Vorschau der Tabelle: Spalten gleich breit über die ganze Seite, solange alles hineinpasst; sonst nach Inhalt mit
    Bildlaufleiste (nie abgeschnittene Zellen)."""

    def fit(self):
        hh = self.horizontalHeader()
        if not self.columnCount():
            return hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        need = sum(hh.sectionSize(i) for i in range(self.columnCount()))
        fits = need <= self.viewport().width()
        hh.setSectionResizeMode(QHeaderView.Stretch if fits else QHeaderView.ResizeToContents)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.fit()


class CompareHost(QMainWindow):
    """Kleiner Gastgeber für den Tab eines Vergleichs (statt des Hauptfensters), wie `reaction_paths.PathHost`."""

    def __init__(self, page):
        super().__init__(page.main)
        self.page, self.owner = page, page.main
        self.settings, self.log_signal, self.extra_cache = self.owner.settings, self.owner.log_signal, self.owner.extra_cache
        self.compound, self.project_dir = {}, None

    def statusBar(self): return self.owner.statusBar()                          # noqa: E704
    def text_format(self, key): return self.owner.text_format(key)              # noqa: E704
    def show_hover(self, text): self.owner.show_hover(text)                     # noqa: E704
    def error(self, text): self.owner.error(text)                               # noqa: E704
    def exported(self, dirs): self.owner.exported(dirs)                         # noqa: E704
    def push_undo(self): self.page.changed()                                    # noqa: E704
    def ensure_project(self): return self.page.pdir is not None                 # noqa: E704
    def export_name(self): return (self.page.item or {}).get("name", "")        # noqa: E704
    def tab_key_of(self, _tab): return None                                     # noqa: E704
    def replace_tab(self, _key): self.page.build()                              # noqa: E704
    def rebuild_tabs(self): self.page.build()                                   # noqa: E704
    def ensure_model(self): return self.owner.ensure_model()                    # noqa: E704
    def cache_dir(self, path): return self.owner.cache_dir(path)                # noqa: E704
    def sync_main_button(self, *_): pass                                        # noqa: E704


class CompareTab(TABS.FigureTab):
    """Gemeinsamer Rahmen aller Vergleiche: Karte „Vergleiche“ (Liste, neu, umbenennen, entfernen), Karte
    „Verbindungen“ (Auswahl, Reihenfolge, Stand, Aktualisieren); die Arten ergänzen ihre Karten und das Bild."""
    STATE_KEY = "comparison"
    KIND = None
    GUIDE = "compare"
    TEXT_OPTS = ()
    SI_PAGE = False
    COLORED = True                     # Farbe je Verbindung (Kurven)
    ORDERED = True                     # Reihenfolge = Liste (Tabelle: Reihenfolge des Projekts)
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, ymax=0.0, members=[])
    RESET_KEEP = ("members", "table")  # „Alles auf Standard“/Vorlagen: Auswahl, Spalten und Zellen bleiben

    @property
    def page(self):
        return self.main.page

    # -- Karten -----------------------------------------------------------------------
    def build_controls(self):
        page = self.page
        g = QGroupBox(T("cmp_list"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for kind in KINDS:
            b = QPushButton(STYLE.icon("add"), T("cmp_new_" + kind))
            b.setToolTip(T("cmp_new_" + kind + "_tip"))
            b.clicked.connect(lambda _=False, k=kind: page.add(k))
            row.addWidget(b, 1)
        if page.item is not None:                             # Knopfreihe wie über allen Listen: [+ …] [Entfernen]
            b = STYLE.list_button(T("remove"))
            b.setToolTip(T("cmp_remove_tip"))
            b.clicked.connect(page.remove)
            row.addWidget(b, 1)
        v.addLayout(row)
        # Liste als Tabelle wie in den anderen Tabs (Name, Art); gewählt = offen
        self.lst = QTableWidget(0, 2)
        self.lst.setHorizontalHeaderLabels([T("cmp_name"), T("cmp_kind")])
        self.lst.verticalHeader().setVisible(False)
        self.lst.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lst.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lst.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lst.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)      # Spalten gleich breit (Nutzerwunsch)
        items = page.items()
        self.lst.setRowCount(len(items))
        for i, it in enumerate(items):
            x = QTableWidgetItem(it["name"])
            x.setData(Qt.UserRole, it["uid"])
            self.lst.setItem(i, 0, x)
            self.lst.setItem(i, 1, QTableWidgetItem(T("cmp_kind_" + it["kind"])))
            if page.item and it["uid"] == page.item["uid"]:
                self.lst.setCurrentCell(i, 0)
        STYLE.fit_check_table(self.lst, 6)
        self.lst.setFixedHeight(max(self.lst.height(), self.lst.horizontalHeader().sizeHint().height()
                                    + STYLE.CHECK_ROW_H + 2))
        self.lst.currentCellChanged.connect(lambda r, *_: r >= 0 and QTimer.singleShot(
            0, lambda u=self.lst.item(r, 0).data(Qt.UserRole): page.open(u)))
        STYLE.empty_note(self.lst, T("cmp_list_empty"))
        v.addWidget(self.lst)
        if page.item is not None:
            f = make_form()
            self.ed_name = QLineEdit(page.item["name"])
            self.ed_name.editingFinished.connect(lambda: page.rename(self.ed_name.text()))
            f.addRow(T("cmp_name"), self.ed_name)
            # Gesamt-SI: aufnehmen (Standard aus), Kapitel wie im Tab „Weitere“ (SI-Kapitel oder eigene Überschrift)
            from elucida.tabs import other as OTHER
            si = page.item.get("si") or {}
            self.cb_si = QCheckBox(T("cmp_si_on"))
            self.cb_si.setToolTip(T("cmp_si_on_tip"))
            self.cb_si.setChecked(bool(si.get("on")))
            self.cmb_si = QComboBox()
            for k, title in OTHER.CHAPTERS:
                self.cmb_si.addItem(title or T("other_new_heading"), k)
            self.cmb_si.setCurrentIndex(max(0, self.cmb_si.findData(si_chapter(page.item))))
            self.ed_si_head = QLineEdit(si.get("heading") or "")
            self.ed_si_head.setPlaceholderText(page.item["name"])
            self.ed_si_head.setToolTip(T("cmp_si_heading_tip"))
            f.addRow(T("cmp_si"), self.cb_si)
            f.addRow(T("other_chapter"), self.cmb_si)
            f.addRow(T("other_heading"), self.ed_si_head)
            self.form_si = f
            self.cb_si.toggled.connect(self.si_changed)
            self.cmb_si.currentIndexChanged.connect(self.si_changed)
            self.ed_si_head.editingFinished.connect(self.si_changed)
            v.addLayout(f)
            self.sync_si()
        self.lv.addWidget(g)
        if self.KIND is None:
            return
        self._members_card()
        self.kind_controls()
        self.show_member()                                    # Karten der Art entstehen nach der Liste

    def sync_si(self):
        """Kapitel nur, wenn der Vergleich in die Gesamt-SI kommt; die Überschrift nur beim eigenen Kapitel."""
        on = self.cb_si.isChecked()
        self.form_si.setRowVisible(self.cmb_si, on)
        self.form_si.setRowVisible(self.ed_si_head, on and self.cmb_si.currentData() == "new")

    def si_changed(self, *_):
        item = self.page.item
        if item is None:
            return
        new = {"on": self.cb_si.isChecked(), "chapter": self.cmb_si.currentData(),
               "heading": self.ed_si_head.text().strip()}
        if new["chapter"] == default_chapter(item):            # Vorgabe der Art nicht festschreiben (folgt dem Inhalt)
            new.pop("chapter")
        if not new["heading"]:
            new.pop("heading")
        self.sync_si()
        if new != (item.get("si") or {}):
            item["si"] = new
            self.page.changed()

    def _members_card(self):
        g = QGroupBox(T("cmp_compounds"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()                                   # eine Knopfzeile über der Liste wie in den Tabs: ↑ ↓ Aktualisieren
        if self.ORDERED:
            for txt, d in (("↑", -1), ("↓", 1)):
                b = STYLE.list_button(txt)
                b.clicked.connect(lambda _=False, d=d: self.move_row(self.tbl.currentRow(), self.tbl.currentRow() + d))
                row.addWidget(b)
        self.btn_refresh = QPushButton(STYLE.icon("reset"), T("cmp_refresh"))
        self.btn_refresh.setToolTip(T("cmp_refresh_tip"))
        self.btn_refresh.clicked.connect(self.page.refresh_snapshots)
        row.addWidget(self.btn_refresh, 1)
        row.addStretch(0)
        v.addLayout(row)
        self._refresh_row = row
        heads = ["", T("cmp_compound")] + ([T("ov_color")] if self.COLORED else []) + [T("cmp_status")]
        self.tbl = QTableWidget(0, len(heads))
        self.tbl.setHorizontalHeaderLabels(heads)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)      # Datenspalten gleich breit; die
        # Häkchenspalte bleibt schmal (check_columns)
        self.tbl.itemChanged.connect(self._member_edited)
        self.tbl.currentCellChanged.connect(lambda *_: self.show_member())
        v.addWidget(self.tbl)
        if self.ORDERED:
            TABS.RowDrag(self.tbl, self.move_row)
        self.lbl_status = STYLE.HintLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_status)
        self.lv.addWidget(g)
        self.fill_members()

    def kind_controls(self):
        pass

    def members(self):
        """Mitglieder dieses Vergleichs, die zum Projekt gehören (in Listen- bzw. Projektreihenfolge)."""
        recs = self.page.records
        ms = [m for m in self.st["members"] if m["dir"] in recs]
        if not self.ORDERED:
            order = list(recs)
            ms.sort(key=lambda m: order.index(m["dir"]))
        return ms

    def drawn(self):
        return [m for m in self.members() if m.get("on", True)]

    def fill_members(self):
        self._loading = True
        ms, recs = self.members(), self.page.records
        self.tbl.setRowCount(len(ms))
        for i, m in enumerate(ms):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if m.get("on", True) else Qt.Unchecked)
            self.tbl.setItem(i, 0, it)
            it = QTableWidgetItem(recs[m["dir"]]["name"])
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tbl.setItem(i, 1, it)
            c = 2
            if self.COLORED:
                self.tbl.setCellWidget(i, 2, TABS.color_button(m["color"], lambda col, m=m: self._set_color(m, col),
                                                                cell=True))
                c = 3
            stt = status(recs[m["dir"]], self.KIND)
            it = QTableWidgetItem(T("cmp_st_" + stt))
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if stt in ("outdated", "missing"):
                it.setForeground(QColor("#c77c0e"))
                it.setToolTip(T("cmp_st_tip"))
            self.tbl.setItem(i, c, it)
        self.tbl.resizeColumnToContents(0)
        if ms and self.tbl.currentRow() < 0:                  # erste Verbindung mit Daten gewählt
            first = next((i for i, m in enumerate(ms) if status(recs[m["dir"]], self.KIND) != "none"), 0)
            self.tbl.setCurrentCell(first, 1)
        STYLE.check_columns(self.tbl)
        STYLE.fit_check_table(self.tbl, 8)
        bad = [recs[m["dir"]]["name"] for m in ms if status(recs[m["dir"]], self.KIND) in ("outdated", "missing")]
        self.lbl_status.setText(T("cmp_need_refresh", names=", ".join(bad)) if bad else "")
        self.btn_refresh.setVisible(bool(bad))                # nur wenn etwas zu erneuern ist (sonst ein toter Balken)
        self._refresh_row.setStretch(self._refresh_row.count() - 1, 0 if bad else 1)
        self._loading = False
        self.show_member()

    def _set_color(self, m, c):
        m["color"] = c
        self.timer.start()

    def _member_edited(self, item):
        if self._loading or item.column() != 0:
            return
        ms = self.members()
        if 0 <= item.row() < len(ms):
            ms[item.row()]["on"] = item.checkState() == Qt.Checked
            self.member_changed()

    def member_changed(self):
        self.timer.start()

    def move_row(self, src, dst):
        ms = self.members()
        if not (0 <= src < len(ms) and 0 <= dst < len(ms)) or src == dst:
            return
        all_ = self.st["members"]
        a, b = all_.index(ms[src]), all_.index(ms[dst])
        all_.insert(b, all_.pop(a))
        self.fill_members()
        self.tbl.selectRow(dst)
        self.timer.start()

    def current_member(self):
        ms = self.members()
        r = self.tbl.currentRow() if hasattr(self, "tbl") else -1
        return ms[r] if 0 <= r < len(ms) else None

    def show_member(self):
        pass

    def rec(self, m):
        return self.page.records[m["dir"]]

    # -- Gesamt-SI -----------------------------------------------------------------------
    def si_blocks(self, out_dir, item):
        """Abbildung + „Figure Sn“-Unterschrift wie jede Abbildung der SI (leer ohne Bild)."""
        self.notes_begin()
        return self.si_figure(out_dir, "comparison_" + item["uid"])

    # -- Export -----------------------------------------------------------------------
    def export_dialog(self):
        """Ins Projekt: <Projekt>/comparisons/figures|tables|SI, Dateiname = Name des Vergleichs (wird überschrieben)."""
        page = self.page
        if page.item is None or page.pdir is None:
            return None
        out_dir = page.out_dir()
        base = PRJ.staging(out_dir, self.STATE_KEY) / core.safe_name(page.item["name"])
        try:
            out = PRJ.place_exports(out_dir, self.export_to(base))
        except PermissionError as e:
            return self.main.error(T("report_locked", p=getattr(e, "filename", "") or ""))
        except Exception as e:
            return self.main.error(str(e))
        self.main.exported(p.parent for p in out)
        return out


class CompareEmpty(CompareTab):
    """Noch kein Vergleich gewählt: Liste und Anleitung."""
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, ymax=0.0)

    def figure_spec(self):
        return None


def _fit_y(curves, lo_pad=0.08, hi_pad=0.12):
    ally = np.concatenate([np.asarray(c["y"], float) for c in curves])
    ally = ally[np.isfinite(ally)]
    span = float(ally.max() - ally.min()) or 1.0
    return [float(ally.min()) - lo_pad * span, float(ally.max()) + hi_pad * span]


class CVStackTab(CompareTab):
    """CV-Stapel: eine Kurve je Verbindung (oberster Eintrag = oberste Kurve), Peakpotential als Zahl am Peak, Struktur
    neben der Kurve, Pfeil der Messrichtung je Kurve. Verbindungen auf einer anderen Referenzskala als die erste werden
    abgelehnt, nie umgerechnet."""
    KIND = "cv"
    X_RANGE = (-10.0, 10.0, 2, 0.1)
    XRANGE_TEXT = "cv_xrange"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=-1.5, x_max=1.0, ymax=0.0, members=[], stack_gap=1.0,
                         normalize=False, arrow=True, structures=True, struct_color=False, struct_w=14.0, legend=False)
    LABELS = ("fwd", "epa", "epc", "e12", "none")

    def kind_controls(self):
        st = self.st
        self.det = QGroupBox(T("cmp_member"))
        f = make_form(self.det)
        self.cmb_file = QComboBox()
        self.cmb_cycle = QComboBox()
        self.cmb_cycle.setToolTip(T("cmp_cycle_tip", n=MAX_CYCLES))
        self.cmb_couple = QComboBox()
        self.cmb_label = QComboBox()
        for k in self.LABELS:
            self.cmb_label.addItem(T("cmp_lab_" + k), k)
        f.addRow(T("cmp_measurement"), self.cmb_file)
        f.addRow(T("cmp_cycle"), self.cmb_cycle)
        f.addRow(T("cmp_couple"), self.cmb_couple)
        f.addRow(T("cmp_label"), self.cmb_label)
        self.lbl_cycle = STYLE.HintLabel("")                  # anderer Zyklus: keine Zahl am Peak (nur der ausgewertete)
        self.lbl_cycle.setWordWrap(True)
        self.lbl_cycle.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_cycle)
        for w in (self.cmb_file, self.cmb_cycle, self.cmb_couple, self.cmb_label):
            w.currentIndexChanged.connect(self.detail_changed)
        self.lv.addWidget(self.det)
        g = QGroupBox(T("cv_display"))
        f = make_form(g)
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=5.0, singleStep=0.1, value=st["stack_gap"])
        self.sp_gap.setToolTip(T("cmp_gap_tip"))
        f.addRow(T("cmp_gap"), self.sp_gap)
        self.sp_sw = QDoubleSpinBox(decimals=0, minimum=4, maximum=40, singleStep=1, suffix=" %", value=st["struct_w"])
        f.addRow(T("img_size"), self.sp_sw)
        self.cb = {}
        for key in ("normalize", "arrow", "structures", "struct_color", "legend"):
            cb = QCheckBox(T("cmp_" + key))
            cb.setChecked(bool(st[key]))
            cb.toggled.connect(self.changed)
            f.addRow(cb)
            self.cb[key] = cb
        self.sp_gap.valueChanged.connect(self.changed)
        self.sp_sw.valueChanged.connect(self.changed)
        self.lv.addWidget(g)

    def collect(self):
        self.st.update(stack_gap=self.sp_gap.value(), struct_w=self.sp_sw.value(),
                       **{k: cb.isChecked() for k, cb in self.cb.items()})

    def show_member(self):
        if not hasattr(self, "cmb_file"):
            return
        m = self.current_member()
        self._loading = True
        for w in (self.cmb_file, self.cmb_cycle, self.cmb_couple):
            w.clear()
        cv = (self.rec(m)["tabs"].get("cv") if m else None) or {}
        for fl in cv.get("files", []):
            rate = f" ({fl['rate']:g} mV s⁻¹)" if fl.get("rate") and f"{fl['rate']:g} mV" not in fl["label"] else ""
            self.cmb_file.addItem(fl["label"] + rate, fl["uid"])
        f = cv_file(self.rec(m), m) if m and cv else None
        if f is not None:
            self.cmb_file.setCurrentIndex(max(0, self.cmb_file.findData(f["uid"])))
            for c in f["couples"]:
                self.cmb_couple.addItem(str(c["n"]), c["n"])
            self.cmb_couple.setCurrentIndex(max(0, self.cmb_couple.findData(m.get("couple", 1))))
            for n in sorted({f["cycle"]} | {c["n"] for c in f.get("cycles") or []}):
                self.cmb_cycle.addItem(T("cmp_cycle_eval", n=n) if n == f["cycle"] else str(n), n)
            self.cmb_cycle.setCurrentIndex(max(0, self.cmb_cycle.findData(cycle_of(f, m)[3])))
            self.cmb_cycle.setEnabled(self.cmb_cycle.count() > 1)
        n_ = cycle_of(f, m)[3] if f is not None else None
        self.lbl_cycle.setText(T("cmp_cycle_hint", n=f["cycle"]) if f is not None and n_ != f["cycle"] else "")
        if m:
            self.cmb_label.setCurrentIndex(max(0, self.cmb_label.findData(m.get("label", "fwd"))))
        self.det.setEnabled(m is not None and f is not None)
        self._loading = False

    def detail_changed(self, *_):
        m = self.current_member()
        if self._loading or m is None:
            return
        f = cv_file(self.rec(m), m)
        if f is not None and self.cmb_file.currentData() != f["uid"]:   # andere Messung: deren ausgewerteter Zyklus
            m.pop("cycle", None)
        else:
            m["cycle"] = self.cmb_cycle.currentData()
        m.update(file=self.cmb_file.currentData(), couple=self.cmb_couple.currentData() or 1,
                 label=self.cmb_label.currentData())
        self.show_member()
        self.timer.start()

    def rows(self):
        """[(Mitglied, Verbindung, Messung)] und abgelehnte Namen (andere Referenz), fehlende Namen."""
        rows, refused, missing, ref0 = [], [], [], None
        for m in self.drawn():
            rec = self.rec(m)
            f = cv_file(rec, m)
            if f is None:
                if status(rec, "cv") != "none":
                    missing.append(rec["name"])
                continue
            if ref0 is None:
                ref0 = f["ref"]
            elif f["ref"] != ref0:
                refused.append(rec["name"])
                continue
            rows.append((m, rec, f))
        return rows, refused, missing, ref0

    def figure_spec(self):
        from elucida.tabs import cv as CV
        st = self.st
        rows, refused, missing, ref0 = self.rows()
        if missing:
            self.add_note(T("cmp_missing_note", names=", ".join(missing)))
        if refused:
            self.add_note(T("cmp_ref_refused", names=", ".join(refused), ref=ref_plain(ref0)))
        if not rows:
            return None
        cfg = self.base_cfg()
        data = []
        for m, rec, f in rows:
            x, y, evaluated, n = cycle_of(f, m)
            if m.get("cycle") and n != m["cycle"]:            # Zyklus nicht (mehr) im Stand: der ausgewertete
                self.add_note(T("cmp_cycle_gone", name=rec["name"], n=m["cycle"], ev=n))
            x = np.asarray(x, float)
            y = np.asarray([np.nan if v is None else v for v in y], float)
            fac = 1.0 / np.nanmax(np.abs(y)) if st["normalize"] and np.nanmax(np.abs(y)) > 0 else 1.0
            data.append((m, rec, dict(f, _evaluated=evaluated), x, y * fac, fac))
        span = max(float(np.nanmax(y) - np.nanmin(y)) for *_, y, _f in data) or 1.0
        n = len(data)
        curves, labels, arrows, imgs = [], [], [], []
        for k, (m, rec, f, x, y, fac) in enumerate(data):
            off = (n - 1 - k) * st["stack_gap"] * span
            curves.append({"x": x, "y": y + off, "val": y, "color": m["color"], "label": rec["name"], "lw": 1.3,
                           "_off": off})
        cfg["xlim"] = [float(min(np.nanmin(d[3]) for d in data)), float(max(np.nanmax(d[3]) for d in data))]
        if not st["x_auto"]:
            cfg["xlim"] = [st["x_min"], st["x_max"]]
        w = st["struct_w"] / 100
        structs = st["structures"] and any(d[1]["structure"] for d in data)
        if structs and st["x_auto"]:                          # Platz rechts neben den Kurven für die Strukturen
            lo, hi = cfg["xlim"]
            cfg["xlim"] = [lo, hi + (hi - lo) * (w + 0.04) / (1 - w - 0.04)]
        cfg["ylim"] = _fit_y(curves)
        if st["ymax"] > 0:
            cfg["ylim"][1] = st["ymax"]
        y0, y1 = cfg["ylim"]
        for k, (m, rec, f, x, y, fac) in enumerate(data):
            off = curves[k]["_off"]
            c = next((c for c in f["couples"] if c["n"] == m.get("couple", 1)), None)
            kind = m.get("label", "fwd")
            if c is not None and kind != "none" and f["_evaluated"]:   # Zahlen nur aus dem ausgewerteten Zyklus
                if c["edge"]:
                    self.add_note(T("cmp_edge_note", name=rec["name"]))
                else:
                    kind = c["fwd"] if kind == "fwd" else kind
                    key = "e12" if kind == "e12" else kind
                    ip = c["ipa"] if kind in ("epa", "e12") else c["ipc"]
                    v = c[key]
                    txt = (f"E$_{{1/2}}$ = {v:.2f} V" if kind == "e12" else f"{v:.2f} V").replace("-", "−")
                    labels.append({"key": f"label_{m['key']}", "lam": v, "y": ip * fac + off, "text": txt,
                                   "side": "below" if kind == "epc" else "above", "color": m["color"]})
            if st["arrow"] and len(x) > 5:
                xr = cfg["xlim"][1] - cfg["xlim"][0]
                direction = 1.0 if np.gradient(x)[:5].mean() >= 0 else -1.0
                arrows.append((f"arrow_scan_{m['key']}", float(x[0]), float(y[0] + off),
                               float(x[0] + direction * 0.08 * xr), m["color"]))
            if structs and rec["structure"]:
                try:
                    asset = self.structure_asset(rec["structure"], m["color"] if st["struct_color"] else None)
                except Exception as ex:
                    self.add_note(f"{Path(rec['structure']).name}: {ex}")
                    continue
                yc = (float(np.nanmedian(y)) + off - y0) / ((y1 - y0) or 1.0)

                def near(X, Y, w_, h_, yc=yc):                    # neben der eigenen Kurve, rechts
                    return np.abs(Y + h_ / 2 - yc) + 0.5 * np.abs(1 - X - w_)
                imgs.append({"file": rec["structure"], "id": f"struktur_{m['key']}", "width": w, "prefer": near,
                             "_asset": asset})
        cfg["images"] = imgs
        cfg["scan_arrows"] = arrows
        cfg["y_axis"] = "no_numbers"
        cfg["legend"] = bool(st["legend"])
        cfg["legend_beside"] = True
        cfg["xlabel"] = f"E [V vs. {CV.axis_ref(ref0)}]"
        cfg["ylabel"] = "normalized current [a.u.]" if st["normalize"] else "I [µA]"
        for c in curves:
            c.pop("_off", None)
        return cfg, curves, labels, []

    def hover_text(self, x, val, name):
        return f"E = {x:.3f} V" + (f"  ·  {name}" if name else "")

    def si_caption(self, name):
        """„Cyclic voltammograms of A, B and C (from top to bottom) in CH2Cl2 (0.1 M n-Bu4NPF6) at rt; scan rate …“ –
        nur aus den Feldern und Daten der Verbindungen: gleiche Angaben einmal, verschiedene je Verbindung."""
        from elucida.si.lines import chem_html
        st = self.st
        rows, *_r = self.rows()
        if not rows:
            return ""
        names = [rec["name"] for _, rec, _ in rows]
        caps = [(rec["name"], (rec["tabs"]["cv"].get("cap") or {})) for _, rec, _ in rows]
        h = "Cyclic voltammograms of " + _join_names(names) + (" (from top to bottom)" if len(names) > 1 else "")
        conc = _per_compound([(n, c.get("conc", "")) for n, c in caps], chem_html)
        h += f" ({conc})" if conc else ""                    # wie im CV-Tab: Konzentration hinter den Namen
        solv = _per_compound([(n, c.get("solvent") or f.get("group", "")) for (n, c), (_, _, f) in zip(caps, rows)],
                             chem_html)
        h += (" in " + solv) if solv else ""
        el = _per_compound([(n, c.get("el", "")) for n, c in caps], chem_html)
        h += f" ({el})" if el else ""
        h += " at " + (_per_compound([(n, c.get("temp") or "rt") for n, c in caps], chem_html) or "rt")
        rates = _per_compound([(rec["name"], f"{f['rate']:g} mV s-1" if f.get("rate") else "") for _, rec, f in rows],
                              chem_html)
        h += f"; scan rate {rates}" if rates else ""
        ref = rows[0][2]["ref"]
        if ref == "Fc$^{0/+}$":
            h += "; potentials vs. Fc<sup>0/+</sup>"
        if st["normalize"]:
            h += "; currents normalized to the maximum absolute current of each voltammogram"
        if st["arrow"]:
            h += " (arrows indicate scanning direction)"
        return h + "."


class SpectraTab(CompareTab):
    """Spektren mehrerer Verbindungen in einem Bild (UV-Vis als ε wie im Overlay oder auf das Maximum normiert,
    Emission normiert wie im Fluoreszenz-Tab), übereinander oder gestapelt, ein Legendeneintrag je Verbindung."""
    KIND = "spectra"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, ymax=0.0, members=[], content="eps", stack=False, stack_gap=1.0,
                         ref_freq=0.0)
    CONTENTS = ("eps", "abs_norm", "em", "abs_em", "ir", "epr", "epr_g")
    RESET_KEEP = CompareTab.RESET_KEEP + ("ref_freq",)      # Referenzfrequenz wie im EPR-Tab: bleibt beim Zurücksetzen
    EPR = ("epr", "epr_g")

    def kind_controls(self):
        st = self.st
        self.box_series = QGroupBox(T("cmp_member"))         # nicht `det`: kein „erst wählen“-Hinweis (nur Sichtbarkeit)
        self.form_series = f = make_form(self.box_series)
        self.cmb_series = QComboBox()
        self.cmb_series.currentIndexChanged.connect(self.detail_changed)
        f.addRow(T("cmp_series"), self.cmb_series)
        self.cmb_trace = QComboBox()                          # EPR: welche Messung der Verbindung
        self.cmb_trace.currentIndexChanged.connect(self.detail_changed)
        f.addRow(T("cmp_epr_trace"), self.cmb_trace)
        self.lv.addWidget(self.box_series)
        g = QGroupBox(T("cv_display"))
        self.form_display = f = make_form(g)
        self.cmb_content = QComboBox()
        for k in self.CONTENTS:
            self.cmb_content.addItem(T("cmp_content_" + k), k)
        self.cmb_content.setCurrentIndex(max(0, self.cmb_content.findData(st["content"])))
        f.addRow(T("cmp_content"), self.cmb_content)
        # EPR-Feldachse: wie der EPR-Tab auf eine Referenzfrequenz skalieren (B·ν_ref/ν), sonst nur gleiche Frequenzen
        self.sp_ref = QDoubleSpinBox(decimals=4, minimum=0.0, maximum=500.0, singleStep=0.1, suffix=" GHz",
                                     value=st["ref_freq"])
        self.sp_ref.setSpecialValueText(T("off"))
        self.sp_ref.setToolTip(T("cmp_ref_freq_tip"))
        f.addRow(T("epr_ref_freq"), self.sp_ref)
        self.sp_ref.valueChanged.connect(self.changed)
        row = QHBoxLayout()                                   # Stapeln mit Abstand in einer Zeile wie im CV-Tab
        self.cb_stack = QCheckBox(T("cmp_stack"))
        self.cb_stack.setChecked(st["stack"])
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=5.0, singleStep=0.1, value=st["stack_gap"])
        self.sp_gap.setToolTip(T("cmp_gap_tip"))
        row.addWidget(self.cb_stack)
        row.addWidget(self.sp_gap)
        row.addStretch(1)
        f.addRow(row)
        self.cmb_content.currentIndexChanged.connect(self.content_changed)
        self.sp_gap.valueChanged.connect(self.changed)
        self.cb_stack.toggled.connect(self.changed)
        self.lv.addWidget(g)
        self.form_display.setRowVisible(self.sp_ref, st["content"] == "epr")

    def content_changed(self, *_):
        """EPR: normiert und gestapelt als Vorgabe; Referenzfrequenz nur bei der Feldachse."""
        k = self.cmb_content.currentData()
        self.form_display.setRowVisible(self.sp_ref, k == "epr")
        if k in self.EPR and self.st["content"] not in self.EPR and not self.cb_stack.isChecked():
            self.cb_stack.setChecked(True)
        self.changed()
        self.show_member()
        if hasattr(self, "cmb_si") and not (self.page.item.get("si") or {}).get("chapter"):
            self.cmb_si.blockSignals(True)                    # Kapitel der Gesamt-SI folgt dem Inhalt (Vorgabe)
            self.cmb_si.setCurrentIndex(max(0, self.cmb_si.findData(default_chapter(self.page.item))))
            self.cmb_si.blockSignals(False)
            self.sync_si()

    def collect(self):
        self.st.update(content=self.cmb_content.currentData(), stack_gap=self.sp_gap.value(),
                       stack=self.cb_stack.isChecked(), ref_freq=self.sp_ref.value())

    def show_member(self):
        if not hasattr(self, "cmb_series"):
            return
        m = self.current_member()
        self._loading = True
        self.cmb_series.clear()
        ser = ((self.rec(m)["tabs"].get("eps") or {}).get("series") if m else None) or []
        for s in ser:
            self.cmb_series.addItem(s["name"], s["name"])
        if m and ser:
            self.cmb_series.setCurrentIndex(max(0, self.cmb_series.findData(eps_series(self.rec(m), m)["name"])))
        self.cmb_trace.clear()
        trs = ((self.rec(m)["tabs"].get("epr") or {}).get("traces") if m else None) or []
        for t in trs:
            self.cmb_trace.addItem(t["label"], t["uid"])
        if m and trs:
            self.cmb_trace.setCurrentIndex(max(0, self.cmb_trace.findData(epr_trace(self.rec(m), m)["uid"])))
        # nur wählbar, was zum Inhalt gehört und bei einer Verbindung mehrfach vorkommt
        content = self.st["content"]
        many = lambda tab, k: any(len((self.rec(x)["tabs"].get(tab) or {}).get(k) or []) > 1     # noqa: E731
                                  for x in self.members())
        show_s = content in ("eps", "abs_norm", "abs_em") and many("eps", "series")
        show_t = content in self.EPR and many("epr", "traces")
        self.form_series.setRowVisible(self.cmb_series, show_s)
        self.form_series.setRowVisible(self.cmb_trace, show_t)
        self.box_series.setVisible(show_s or show_t)
        self._loading = False

    def detail_changed(self, *_):
        m = self.current_member()
        if self._loading or m is None:
            return
        if self.cmb_series.count():
            m["series"] = self.cmb_series.currentData()
        if self.cmb_trace.count():
            m["epr"] = self.cmb_trace.currentData()
        self.timer.start()

    def figure_spec(self):
        st = self.st
        content = st["content"]
        if content == "ir":
            return self._ir_spec()
        if content in self.EPR:
            return self._epr_spec()
        uv, em = content in ("eps", "abs_norm", "abs_em"), content in ("em", "abs_em")
        eps_mode = content == "eps"
        lo = core.DEFAULTS["peak_range_nm"][0]
        groups, no_eps, missing = [], [], []
        for m in self.drawn():
            rec = self.rec(m)
            cs = []
            s = eps_series(rec, m) if uv else None
            if uv and s is not None and s.get("curve"):
                cu = s["curve"]
                x = np.asarray(cu["x"], float)
                a = np.asarray([np.nan if v is None else v for v in cu["a"]], float)
                if eps_mode:
                    if cu.get("eps_fac"):
                        cs.append((x, a * cu["eps_fac"] / 1000.0, "-"))     # wie das Overlay: 10³ M⁻¹ cm⁻¹
                    else:
                        no_eps.append(rec["name"])
                else:
                    mx = np.nanmax(np.where(x >= lo, a, np.nan)) if (x >= lo).any() else np.nanmax(a)
                    if mx > 0:
                        cs.append((x, a / mx, "-"))
            fl = rec["tabs"].get("fluo") if em else None
            if em and fl and fl.get("em"):
                cs.append((np.asarray(fl["em"]["x"], float),
                           np.asarray([np.nan if v is None else v for v in fl["em"]["y"]], float),
                           "--" if uv else "-"))
            if cs:
                groups.append((m, rec, cs))
            elif status(rec, "spectra") in ("outdated", "missing"):
                missing.append(rec["name"])
        if missing:
            self.add_note(T("cmp_missing_note", names=", ".join(missing)))
        if no_eps:
            self.add_note(T("cmp_no_eps", names=", ".join(no_eps)))
        if not groups:
            return None
        cfg = self.base_cfg()
        n = len(groups)
        top = max(float(np.nanmax(y)) for _, _, cs in groups for _x, y, _l in cs) or 1.0
        curves = []
        for k, (m, rec, cs) in enumerate(groups):
            off = (n - 1 - k) * st["stack_gap"] * (top if eps_mode else 1.0) if st["stack"] else 0.0
            for j, (x, y, ls) in enumerate(cs):
                curves.append({"x": x, "y": y + off, "val": y, "color": m["color"], "ls": ls, "lw": 1.3,
                               "label": rec["name"] if j == 0 else None})
        xs = np.concatenate([c["x"] for c in curves])
        cfg["xlim"] = [float(np.nanmin(xs)), float(np.nanmax(xs))] if st["x_auto"] else [st["x_min"], st["x_max"]]
        lo_x, hi_x = cfg["xlim"]
        mx = max(float(np.nanmax(np.where((c["x"] >= lo_x) & (c["x"] <= hi_x), c["y"], np.nan))) for c in curves)
        mn = min(0.0, min(float(np.nanmin(np.where((c["x"] >= lo_x) & (c["x"] <= hi_x), c["y"], np.nan)))
                          for c in curves))
        cfg["ylim"] = [mn, st["ymax"] if st["ymax"] > 0 else 1.1 * mx]
        cfg["y_axis"] = "no_numbers" if st["stack"] else "numbers"
        cfg["legend_beside"] = True
        cfg["ylabel"] = (r"$\varepsilon$ [10$^3$ M$^{-1}$ cm$^{-1}$]" if eps_mode else
                         "normalized emission [a.u.]" if content == "em" else "normalized intensity [a.u.]")
        cfg["images"] = []
        return cfg, curves, [], []

    def _stacked(self, groups, cfg, span):
        """[(Mitglied, Verbindung, x, y)] -> Kurven, übereinander oder gestapelt (oberster Eintrag oben)."""
        st, n, curves = self.st, len(groups), []
        for k, (m, rec, x, y) in enumerate(groups):
            off = (n - 1 - k) * st["stack_gap"] * span if st["stack"] else 0.0
            curves.append({"x": x, "y": y + off, "val": y, "color": m["color"], "ls": "-", "lw": 1.0,
                           "label": rec["name"]})
        cfg["ylim"] = _fit_y(curves)
        if st["ymax"] > 0:
            cfg["ylim"][1] = st["ymax"]
        cfg["y_axis"] = "no_numbers" if st["stack"] else "numbers"
        cfg["legend_beside"] = True
        cfg["images"] = []
        return curves

    def _xlim(self, xs, reverse):
        """Achse wie im Tab: IR-Wellenzahl und g fallen nach rechts."""
        st = self.st
        lo, hi = (float(np.nanmin(xs)), float(np.nanmax(xs))) if st["x_auto"] else sorted((st["x_min"], st["x_max"]))
        return [hi, lo] if reverse else [lo, hi]

    def _refused_notes(self, missing, refused_key=None, refused=(), **kw):
        if missing:
            self.add_note(T("cmp_missing_note", names=", ".join(missing)))
        if refused:
            self.add_note(T(refused_key, names=", ".join(refused), **kw))

    def _ir_spec(self):
        """IR: Transmission oder Absorbanz wie im IR-Tab der ersten Verbindung; eine andere Darstellung wird
        abgelehnt (nie umgerechnet)."""
        groups, missing, refused, mode0 = [], [], [], None
        for m in self.drawn():
            rec = self.rec(m)
            cu = (rec["tabs"].get("irms") or {}).get("curve")
            if not cu:
                if status(rec, "spectra") in ("outdated", "missing"):
                    missing.append(rec["name"])
                continue
            if mode0 is None:
                mode0 = cu["mode"]
            elif cu["mode"] != mode0:
                refused.append(rec["name"])
                continue
            groups.append((m, rec, np.asarray(cu["x"], float),
                           np.asarray([np.nan if v is None else v for v in cu["y"]], float)))
        self._refused_notes(missing, "cmp_ir_refused", refused, mode=T("cmp_ir_mode_" + (mode0 or "T")))
        if not groups:
            return None
        cfg = self.base_cfg()
        span = max(float(np.nanmax(y) - np.nanmin(y)) for *_, y in groups) or 1.0
        curves = self._stacked(groups, cfg, span)
        cfg["xlim"] = self._xlim(np.concatenate([g[2] for g in groups]), True)
        cfg["xlabel"] = "wavenumber [cm$^{-1}$]"
        cfg["ylabel"] = "transmittance [%]" if mode0 == "T" else "absorbance"
        return cfg, curves, [], []

    def _epr_spec(self):
        """EPR normiert: Feldachse nur bei gleicher Mikrowellenfrequenz oder wie der EPR-Tab auf eine Referenzfrequenz
        skaliert (B·ν_ref/ν), sonst g-Achse (g = hν/µ_B·B); was nicht passt, wird abgelehnt (nie still gemischt)."""
        from elucida.tabs import epr as EPR
        st = self.st
        g_axis, ref = st["content"] == "epr_g", st["ref_freq"]
        groups, missing, no_nu, other_nu, nu0, units = [], [], [], [], None, set()
        for m in self.drawn():
            rec = self.rec(m)
            ep = rec["tabs"].get("epr") or {}
            tr = epr_trace(rec, m)
            if tr is None:
                if status(rec, "spectra") in ("outdated", "missing"):
                    missing.append(rec["name"])
                continue
            B = np.asarray(tr["x"], float)
            y = np.asarray([np.nan if v is None else v for v in tr["y"]], float)
            nu = tr.get("nu")
            if g_axis or ref:
                if not nu:
                    no_nu.append(rec["name"])
                    continue
                x = nu / (EPR.MU_B_H * B / 1000.0) if g_axis else B * ref / nu
            else:
                if not groups:
                    nu0 = nu
                elif not nu or not nu0 or abs(nu - nu0) > EPR_NU_TOL * nu0:
                    other_nu.append(rec["name"])
                    continue
                x = B
            mx = np.nanmax(np.abs(y)) if np.isfinite(y).any() else 0
            units.add(ep.get("unit", "mT"))
            groups.append((m, rec, x, y / mx if mx > 0 else y))
        self._refused_notes(missing, "cmp_epr_no_nu", no_nu)
        if other_nu:
            self.add_note(T("cmp_epr_other_nu", names=", ".join(other_nu), nu=f"{nu0:.4f}" if nu0 else "?"))
        if not groups:
            return None
        cfg = self.base_cfg()
        unit = "G" if units == {"G"} and not g_axis else "mT"
        if unit == "G":
            groups = [(m, rec, x * 10.0, y) for m, rec, x, y in groups]
        curves = self._stacked(groups, cfg, 2.0)
        cfg["xlim"] = self._xlim(np.concatenate([g[2] for g in groups]), g_axis)
        cfg["xlabel"] = "g" if g_axis else f"magnetic field [{unit}]"
        cfg["ylabel"] = "normalized EPR intensity [arb. u.]"
        self._epr_nu = (ref or nu0) if not g_axis else None
        return cfg, curves, [], []

    def si_caption(self, name):
        from elucida.si.lines import chem_html
        st = self.st
        if st["content"] == "ir" or st["content"] in self.EPR:
            return self._caption_ir_epr()
        ms = [m for m in self.drawn()]
        names = [self.rec(m)["name"] for m in ms]
        if not names:
            return ""
        what = {"eps": "UV-Vis absorption spectra (molar absorption coefficient)",
                "abs_norm": "Normalized UV-Vis absorption spectra",
                "em": "Normalized fluorescence emission spectra",
                "abs_em": "Normalized UV-Vis absorption (solid) and fluorescence emission spectra (dashed)"}[st["content"]]
        h = f"{what} of " + _join_names(names)
        solv = []
        for m in ms:
            rec = self.rec(m)
            s = eps_series(rec, m) if st["content"] != "em" else None
            fl = rec["tabs"].get("fluo") or {}
            solv.append((rec["name"], (s or {}).get("solvent") or fl.get("solvent", "")))
        sv = _per_compound(solv, chem_html)
        return h + (f" in {sv}" if sv else "") + (" (stacked)" if st["stack"] else "") + "."


    def _caption_ir_epr(self):
        """Unterschrift IR/EPR: nur Verbindungen, die das Bild zeigt; Achse der EPR-Spektren ausdrücklich."""
        spec = _quiet(self.figure_spec)
        if spec is None:
            return ""
        names = [c["label"] for c in spec[1] if c.get("label")]
        st = self.st
        h = ("IR spectra of " if st["content"] == "ir" else "Normalized EPR spectra of ") + _join_names(names)
        h += " (stacked)" if st["stack"] and len(names) > 1 else ""
        if st["content"] == "epr_g":
            h += ", plotted against the g value"
        elif st["content"] == "epr" and st["ref_freq"]:
            h += f"; magnetic field scaled to a microwave frequency of {st['ref_freq']:.4f} GHz"
        elif st["content"] == "epr" and getattr(self, "_epr_nu", None):
            h += f"; microwave frequency {self._epr_nu:.4f} GHz"
        return h + "."


def epr_trace(rec, member):
    trs = (rec["tabs"].get("epr") or {}).get("traces") or []
    return next((t for t in trs if t["uid"] == member.get("epr")), trs[0] if trs else None)


class TableTab(CompareTab):
    """Eigenschaftstabelle: Zeilen = Verbindungen (Reihenfolge des Projekts) und freie Zeilen, Spalten = Werte aus den
    Tabs (Stand) und freie Spalten; Zellen der Tab-Spalten lassen sich überschreiben (sichtbar markiert,
    zurücksetzbar); Gruppenkopf je Spalte; „Verbindungen als Spalten“ dreht die Tabelle."""
    KIND = "table"
    DRAG_HINT = ""                     # nichts zu ziehen: keine Fußnote
    COLORED = False
    ORDERED = False
    STEP_LABELS = ("step_data", "cmp_step_table", "step_display")
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, ymax=0.0, members=[], table={})

    def __init__(self, main, state):
        tb = state.setdefault("table", {})
        for k, v in (("cols", []), ("rows", []), ("cells", {}), ("transpose", False)):
            tb.setdefault(k, copy.deepcopy(v))
        super().__init__(main, state)
        # Tabelle statt Abbildung: Reiter „Abbildung“ und die Größenkarte gehören nicht dazu; „Exportieren“ bleibt blau
        self.right_tabs.removeTab(self.right_tabs.indexOf(self.preview_stack))
        self.grp_common.setVisible(False)
        if self.empty_guide is not None:
            self.empty_guide.export = None
        STYLE.set_accent(self.btn_export, True, "export")
        for b in (self.btn_reset, self.btn_presets):            # kein Bild: nichts zurückzusetzen, keine Vorlagen
            b.hide()
        self.fill_grid()

    @property
    def tb(self):
        return self.st["table"]

    def _plain_table(self, heads, empty):
        """Liste als Tabelle wie in den anderen Tabs: zeigt und wählt nur, bearbeitet wird in den Feldern darunter."""
        t = QTableWidget(0, len(heads))
        t.setHorizontalHeaderLabels(heads)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)   # alle Spalten gleich breit (Nutzerwunsch)
        t.setItemDelegate(STYLE.RichDelegate(t, self._cell_html))
        STYLE.empty_note(t, empty)
        return t

    def kind_controls(self):
        # Gewählte Verbindung: welche Struktur (X-Ray) und welche Rechnung (DFT) ihre Werte liefert – nur bei mehreren
        self.box_member = QGroupBox(T("cmp_member"))
        self.form_member = make_form(self.box_member)
        self.cmb_xr, self.cmb_dft = QComboBox(), QComboBox()
        self.cmb_xr.setToolTip(T("cmp_xr_struct_tip"))
        self.cmb_dft.setToolTip(T("cmp_dft_calc_tip"))
        self.form_member.addRow(T("cmp_xr_struct"), self.cmb_xr)
        self.form_member.addRow(T("cmp_dft_calc"), self.cmb_dft)
        for w in (self.cmb_xr, self.cmb_dft):
            w.currentIndexChanged.connect(self.member_detail_changed)
        self.lv.addWidget(self.box_member)
        # Größen (Spalten der Tabelle, gedreht ihre Zeilen): Knopfzeile – Tabelle – Felder der gewählten Größe
        g = QGroupBox(T("cmp_columns"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        self.btn_auto = QPushButton(STYLE.icon("add"), T("cmp_add_auto"))
        self.btn_auto.setToolTip(T("cmp_add_auto_tip"))
        menu = QMenu(self.btn_auto)                              # Werte, die die Tabs der Verbindungen anbieten
        for key, (_h, label) in auto_columns(list(self.page.records.values())).items():
            menu.addAction(label, lambda k=key: self.add_auto(k))
        self.btn_auto.setMenu(menu)
        b = QPushButton(STYLE.icon("add"), T("cmp_add_free"))
        b.setToolTip(T("cmp_add_free_tip"))
        b.clicked.connect(self.add_free)
        row.addWidget(self.btn_auto, 1)
        row.addWidget(b, 1)
        for txt, d in (("↑", -1), ("↓", 1)):
            b = STYLE.list_button(txt)
            b.clicked.connect(lambda _=False, d=d: self.move_col(d))
            row.addWidget(b)
        b = STYLE.list_button(T("remove"))
        b.clicked.connect(self.remove_col)
        row.addWidget(b, 1)
        v.addLayout(row)
        self.tbl_cols = self._plain_table([T("cmp_head"), T("cmp_unit"), T("cmp_group_head"), T("cmp_source")],
                                          T("cmp_cols_empty"))
        self.tbl_cols.currentCellChanged.connect(lambda *_: self.show_col())
        TABS.RowDrag(self.tbl_cols, self.move_col_to)
        v.addWidget(self.tbl_cols)
        f = make_form()
        self.ed_head, self.ed_unit, self.ed_group = QLineEdit(), QLineEdit(), QLineEdit()
        self.ed_head.setPlaceholderText(T("cmp_head_ph"))
        self.ed_unit.setPlaceholderText(T("cmp_unit_ph"))
        self.ed_group.setPlaceholderText(T("cmp_group_ph"))
        f.addRow(T("cmp_head"), self.ed_head)
        f.addRow(T("cmp_unit"), self.ed_unit)
        f.addRow(T("cmp_group_head"), self.ed_group)
        for ed in (self.ed_head, self.ed_unit, self.ed_group):
            ed.editingFinished.connect(self.col_edited)
        # IR-Bande / NMR-Verschiebung: Ziel und Toleranz (Zelle = nächster Wert der Liste des Tabs innerhalb der Toleranz)
        self.cmb_nuc = QComboBox()
        self.ed_target = QLineEdit()
        self.ed_target.setToolTip(T("cmp_target_tip"))
        self.sp_tol = QDoubleSpinBox(decimals=2, minimum=0.0, maximum=1000.0, singleStep=0.1)
        self.sp_tol.setToolTip(T("cmp_tol_tip"))
        f.addRow(T("cmp_nuc"), self.cmb_nuc)
        f.addRow(T("cmp_target"), self.ed_target)
        f.addRow(T("cmp_tol"), self.sp_tol)
        self.ed_target.editingFinished.connect(self.col_edited)
        self.sp_tol.editingFinished.connect(self.col_edited)
        self.cmb_nuc.currentIndexChanged.connect(self.col_edited)
        self.form_cols = f
        v.addLayout(f)
        self.lv.addWidget(g)
        # Weitere Verbindungen (nicht im Projekt, z. B. aus der Literatur): eigene Zeilen, Werte von Hand
        g = QGroupBox(T("cmp_rows"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        b = QPushButton(STYLE.icon("add"), T("cmp_add_row"))
        b.setToolTip(T("cmp_add_row_tip"))
        b.clicked.connect(self.add_row)
        row.addWidget(b, 1)
        b = STYLE.list_button(T("remove"))
        b.clicked.connect(self.remove_row)
        row.addWidget(b, 1)
        v.addLayout(row)
        self.tbl_rows = self._plain_table([T("cmp_name")], T("cmp_rows_empty"))
        self.tbl_rows.currentCellChanged.connect(lambda *_: self.show_row())
        v.addWidget(self.tbl_rows)
        f = make_form()
        self.ed_row = QLineEdit()
        self.ed_row.setPlaceholderText(T("cmp_row_ph"))
        self.ed_row.editingFinished.connect(self.rename_row)
        f.addRow(T("cmp_name"), self.ed_row)
        v.addLayout(f)
        self.lv.addWidget(g)
        # Zellen und Anordnung: Tab-Wert zurückholen, Tabelle drehen
        g = QGroupBox(T("cmp_cells"))
        f = make_form(g)
        self.cb_transpose = QCheckBox(T("cmp_transpose"))    # Aufbau der Tabelle: hier, keine eigene Stufe dafür
        self.cb_transpose.setChecked(bool(self.tb.get("transpose")))
        self.cb_transpose.toggled.connect(self.transpose_toggled)
        f.addRow(T("cmp_layout"), self.cb_transpose)
        self.btn_reset_cell = QPushButton(STYLE.icon("reset"), T("cmp_reset_cell"))
        self.btn_reset_cell.clicked.connect(self.reset_cell)
        f.addRow(T("cmp_cell"), self.btn_reset_cell)
        self.lbl_cell = STYLE.HintLabel("")
        self.lbl_cell.setWordWrap(True)
        self.lbl_cell.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_cell)
        self.lv.addWidget(g)
        # Vorschau: die Tabelle selbst (Kopfzeilen als Zeilen gesetzt, Zellen bearbeitbar)
        res = QGroupBox(T("cmp_table"))
        rv = QVBoxLayout(res)
        self.grid = _FitGrid(0, 0)
        self.grid.horizontalHeader().hide()
        self.grid.verticalHeader().hide()
        self.grid.setShowGrid(False)                          # wie alle Tabellen: nur Linien unter den Zeilen
        self.grid.setItemDelegate(GroupRule(self.grid, self._cell_html))
        self.grid.itemChanged.connect(self.cell_edited)
        self.grid.currentCellChanged.connect(lambda *_: self.show_cell())
        rv.addWidget(self.grid)
        brow = QHBoxLayout()
        b = STYLE.copy_button(T("cmp_copy_tip"))
        b.clicked.connect(self.copy_table)
        brow.addWidget(b)
        rv.addLayout(brow)
        self._res_card = res
        self.fill_cols()

    def arrange(self):
        super().arrange()
        self.to_right(self._res_card, T("cmp_table"))           # Tabelle als Seite rechts (wie Ergebnisse)
        self.lv.removeWidget(self.grp_common)                   # Achsen und Bildgröße: kein Bild, also auch kein
        self.grp_common.setParent(None)                         # Schritt „Darstellung“ (Felder bleiben für collect)

    @staticmethod
    def _cell_html(text):
        from elucida.tabs import xray as XRAY
        return XRAY.to_html(text)

    # -- Spalten und Zeilen ---------------------------------------------------------------
    def fill_cols(self):
        """Tabellen „Größen“ und „Weitere Verbindungen“ aus dem Zustand (Auswahl bleibt)."""
        known = auto_columns(list(self.page.records.values()))
        self._fill(self.tbl_cols, [self._col_cells(c, known) for c in self.tb["cols"]])
        self._fill(self.tbl_rows, [[r["name"]] for r in self.tb["rows"]])
        self.show_col()
        self.show_row()

    @staticmethod
    def _fill(table, rows):
        cur = table.currentRow()
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for i, cells in enumerate(rows):
            for j, text in enumerate(cells):
                it = QTableWidgetItem(text)
                it.setToolTip(text)
                table.setItem(i, j, it)
        table.blockSignals(False)
        STYLE.fit_check_table(table, 6)
        table.setFixedHeight(max(table.height(), table.horizontalHeader().sizeHint().height() + STYLE.CHECK_ROW_H + 2))
        if rows:
            table.setCurrentCell(min(max(cur, 0), len(rows) - 1), 0)

    @staticmethod
    def _col_cells(c, known):
        """Größe, Einheit, Gruppenkopf, Herkunft einer Spalte (Markup wie der Tabellenkopf)."""
        if c["kind"] == "auto":
            head, label = known.get(c.get("key"), (head_of(c), c.get("key", "")))
            head = head_of(c) if c.get("key") == "nmr_shift" else head          # Kern gehört zur Spalte
            q, _sep, u = head.partition(" / ")
            src = label.split(":")[0] if ":" in label else T("cmp_src_compound")
            if c.get("key") in ("ir_band", "nmr_shift"):                       # Ziel ± Toleranz statt Herkunft allein
                src = f"{src} · {target_text(c) or T('cmp_no_target')}"
        else:
            q, u, src = _esc(c.get("head") or T("cmp_free_col")), unit_markup(c.get("unit", "")), T("cmp_src_own")
        return [q, u, c.get("group", ""), src]

    def current_col(self):
        r = self.tbl_cols.currentRow()
        return self.tb["cols"][r] if 0 <= r < len(self.tb["cols"]) else None

    def show_col(self):
        """Felder der gewählten Größe: eigene Größen frei, Tab-Werte zeigen Kopf und Einheit nur an."""
        c = self.current_col()
        free = c is not None and c["kind"] == "free"
        q, u = "", ""
        if c is not None and not free:
            q, _sep, u = re.sub(r"[*_^{}]", "", head_of(c, list(self.page.records.values()))).partition(" / ")
        self.ed_head.setText(c.get("head", "") if free else q)
        self.ed_unit.setText(c.get("unit", "") if free else u)
        self.ed_group.setText(c.get("group", "") if c else "")
        self.ed_head.setEnabled(free)
        self.ed_unit.setEnabled(free)
        self.ed_group.setEnabled(c is not None)
        tip = "" if free or c is None else T("cmp_auto_fixed")
        self.ed_head.setToolTip(tip)
        self.ed_unit.setToolTip(tip)
        # Ziel/Toleranz nur für IR-Bande und NMR-Verschiebung, der Kern nur für NMR (sonst samt Beschriftung weg)
        key = (c or {}).get("key") if c is not None and not free else None
        self._col_loading = True
        self.form_cols.setRowVisible(self.cmb_nuc, key == "nmr_shift")
        for w in (self.ed_target, self.sp_tol):
            self.form_cols.setRowVisible(w, key in ("ir_band", "nmr_shift"))
        if key == "nmr_shift":
            nucs = sorted({s["nuc"] for r in self.page.records.values()
                           for s in (r["tabs"].get("nmr") or {}).get("signals", [])} | {c.get("nuc") or "1H"},
                          key=lambda n: (n != "1H", n != "13C", n))
            self.cmb_nuc.clear()
            from elucida.tabs import nmr as NMR
            for n in nucs:
                self.cmb_nuc.addItem(NMR.sup_nuclei(n), n)
            self.cmb_nuc.setCurrentIndex(max(0, self.cmb_nuc.findData(c.get("nuc") or "1H")))
        if key in ("ir_band", "nmr_shift"):
            unit = " cm⁻¹" if key == "ir_band" else " ppm"
            self.ed_target.setText("" if c.get("target") is None else f"{c['target']:g}")
            self.ed_target.setPlaceholderText(T("cmp_target_ph_ir" if key == "ir_band" else "cmp_target_ph_nmr"))
            self.sp_tol.setDecimals(0 if key == "ir_band" else 2)
            self.sp_tol.setSuffix(unit)
            self.sp_tol.setValue(c.get("tol", default_tol(c)))
        self._col_loading = False

    def col_edited(self, *_):
        c = self.current_col()
        if c is None or getattr(self, "_col_loading", False):
            return
        new = dict(c, group=self.ed_group.text().strip())
        if c["kind"] == "free":
            new.update(head=self.ed_head.text().strip(), unit=self.ed_unit.text().strip())
        elif c.get("key") in ("ir_band", "nmr_shift"):
            txt = self.ed_target.text().strip().replace(",", ".").replace("−", "-")
            try:
                new["target"] = float(txt) if txt else None
            except ValueError:                                     # kein Zahlentext: altes Ziel bleibt
                self.ed_target.setText("" if c.get("target") is None else f"{c['target']:g}")
            new["tol"] = self.sp_tol.value()
            if c["key"] == "nmr_shift":
                new["nuc"] = self.cmb_nuc.currentData() or c.get("nuc") or "1H"
                if new["nuc"] != c.get("nuc") and c.get("tol") == default_tol(c):   # Vorgabe folgt dem Kern
                    new["tol"] = default_tol(new)
        if new != c:
            c.update(new)
            self.table_changed(cols=True)

    def add_auto(self, key):
        if key:
            col = {"id": uuid.uuid4().hex[:8], "kind": "auto", "key": key, "group": ""}
            if key == "nmr_shift":
                col["nuc"] = "1H"
            if key in ("ir_band", "nmr_shift"):
                col.update(target=None, tol=default_tol(col))
            self.tb["cols"].append(col)
            self.table_changed(cols=True, select=len(self.tb["cols"]) - 1)
            if key in ("ir_band", "nmr_shift"):                 # gleich das Ziel eintippen
                self.steps.reveal(self.ed_target)
                self.ed_target.setFocus()

    # -- Gewählte Verbindung (X-Ray-Struktur, DFT-Rechnung) ----------------------------------
    def show_member(self):
        if not hasattr(self, "cmb_xr"):
            return
        m = self.current_member()
        self._loading = True
        lists = []
        for cmb, tab, items, attr, sel in ((self.cmb_xr, "xray", "structures", "name", xr_structure),
                                           (self.cmb_dft, "dft", "calcs", "uid", dft_calc)):
            cmb.clear()
            its = ((self.rec(m)["tabs"].get(tab) or {}).get(items) if m else None) or []
            for it in its:
                cmb.addItem(it["name"], it[attr])
            if its:
                cmb.setCurrentIndex(max(0, cmb.findData(sel(self.rec(m), m)[attr])))
            many = any(len((self.rec(x)["tabs"].get(tab) or {}).get(items) or []) > 1 for x in self.members())
            self.form_member.setRowVisible(cmb, many)
            cmb.setEnabled(len(its) > 1)
            lists.append(many)
        self.box_member.setVisible(any(lists))                  # nur wenn es etwas zu wählen gibt
        self._loading = False

    def member_detail_changed(self, *_):
        m = self.current_member()
        if self._loading or m is None:
            return
        m.update(xr_struct=self.cmb_xr.currentData(), dft_calc=self.cmb_dft.currentData())
        self.table_changed()

    def add_free(self):
        self.tb["cols"].append({"id": uuid.uuid4().hex[:8], "kind": "free", "head": T("cmp_free_col"), "unit": "",
                                "group": ""})
        self.table_changed(cols=True, select=len(self.tb["cols"]) - 1)
        self.ed_head.setFocus()                                  # gleich benennen
        self.ed_head.selectAll()

    def move_col(self, d):
        r = self.tbl_cols.currentRow()
        self.move_col_to(r, r + d)

    def move_col_to(self, src, dst):
        if TABS.move_item(self.tb["cols"], src, dst):
            self.table_changed(cols=True, select=dst)

    def remove_col(self):
        c = self.current_col()
        if c is None:
            return
        self.tb["cols"].remove(c)
        self.tb["cells"] = {k: v for k, v in self.tb["cells"].items() if not k.endswith("|" + c["id"])}
        self.table_changed(cols=True)

    def current_row(self):
        r = self.tbl_rows.currentRow()
        return self.tb["rows"][r] if 0 <= r < len(self.tb["rows"]) else None

    def show_row(self):
        r = self.current_row()
        self.ed_row.setText(r["name"] if r else "")
        self.ed_row.setEnabled(r is not None)

    def add_row(self):
        """Weitere Verbindung (nicht im Projekt): Zeile mit vorläufigem Namen, gleich im Feld „Name“ zu ändern."""
        names = {r["name"] for r in self.tb["rows"]}
        n = next(k for k in range(1, len(names) + 2) if f"{T('cmp_row_name')} {k}" not in names)
        self.tb["rows"].append({"id": "r" + uuid.uuid4().hex[:8], "name": f"{T('cmp_row_name')} {n}"})
        self.table_changed(cols=True)
        self.tbl_rows.setCurrentCell(len(self.tb["rows"]) - 1, 0)
        self.ed_row.setFocus()
        self.ed_row.selectAll()

    def rename_row(self):
        r, name = self.current_row(), self.ed_row.text().strip()
        if r is not None and name and name != r["name"]:
            r["name"] = name
            self.table_changed(cols=True)

    def remove_row(self):
        r = self.current_row()
        if r is not None:
            self.tb["rows"].remove(r)
            self.tb["cells"] = {k: v for k, v in self.tb["cells"].items() if not k.startswith(r["id"] + "|")}
            self.table_changed(cols=True)

    def transpose_toggled(self, on):
        self.tb["transpose"] = bool(on)
        self.table_changed()

    def member_changed(self):
        self.table_changed()

    def table_changed(self, cols=False, select=None):
        if cols:
            self.fill_cols()
            if select is not None:
                self.tbl_cols.setCurrentCell(select, 0)
        self.fill_grid()
        self.main.push_undo()

    # -- Inhalt ---------------------------------------------------------------------------
    def logical(self):
        """Tabelle ohne Drehung -> (Gruppen je Spalte oder None, Köpfe, Zeilen [(Schlüssel, Name, [(Text, Art, Tabwert)])]).
        Art: auto | over (von Hand überschrieben) | free."""
        recs = list(self.page.records.values())
        cols, cells = self.tb["cols"], self.tb["cells"]
        groups = [c.get("group", "") for c in cols]
        heads = [head_of(c, recs) for c in cols]
        rows = []
        for m in self.drawn():
            rec = self.rec(m)
            vals = []
            for c in cols:
                k = f"{m['key']}|{c['id']}"
                if c["kind"] == "auto":
                    tv = auto_value(c["key"], rec, m, c)
                    vals.append((cells[k], "over", tv) if k in cells else (tv, "auto", tv))
                else:
                    vals.append((cells.get(k, ""), "free", None))
            rows.append((m["key"], rec["name"], vals))
        for r in self.tb["rows"]:
            rows.append((r["id"], r["name"], [(cells.get(f"{r['id']}|{c['id']}", ""), "free", None) for c in cols]))
        return (groups if any(groups) else None), heads, rows

    def matrix(self, english=True):
        """Gedrehte oder ungedrehte Tabelle als Markup-Raster -> (Zeilen [[(Markup, Rolle, Zeile, Spalte)]], Kopfzeilen).
        Rolle: group | head | name | cell; Zeile/Spalte = Schlüssel für Zellen."""
        groups, heads, rows = self.logical()
        corner = "" if self.tb.get("transpose") else "Compound" if english else T("cmp_compound")
        top = [[("", "group", None, None)] + [(_esc(g), "group", None, c["id"]) for g, c in zip(groups, self.tb["cols"])]] \
            if groups else []
        head = [[(corner, "head", None, None)] + [(h, "head", None, c["id"]) for h, c in zip(heads, self.tb["cols"])]]
        body = [[(_esc(name), "name", rk, None)] + [(t if kind == "auto" and c.get("key") in MARKUP_KEYS else _esc(t),
                                                       kind, rk, c["id"]) for (t, kind, _tv), c in
                                                      zip(vals, self.tb["cols"])] for rk, name, vals in rows]
        mat = top + head + body
        n_head = len(top) + 1
        if self.tb.get("transpose"):
            mat = [list(r) for r in zip(*mat)]
            # gedreht: Namen bilden die Kopfzeile, Spaltenköpfe die erste(n) Spalte(n)
            mat = [[(t, {"name": "head", "head": "name"}.get(role, role), rk, ck) for t, role, rk, ck in r] for r in mat]
            n_head = 1
        return mat, n_head

    def fill_grid(self):
        if not hasattr(self, "grid"):
            return
        mat, n_head = self.matrix()
        _g, _h, rows = self.logical()
        tv = {(rk, c["id"]): v for rk, _n, vals in rows for v, c in zip(vals, self.tb["cols"])}
        self._loading = True
        self.grid.blockSignals(True)
        self.grid.clearSpans()
        self.grid.setRowCount(len(mat))
        self.grid.setColumnCount(max((len(r) for r in mat), default=0))
        bold = QFont(self.grid.font())
        bold.setBold(True)
        for i, r in enumerate(mat):
            for j, (t, role, rk, ck) in enumerate(r):
                it = QTableWidgetItem(t)
                it.setData(Qt.UserRole, (role, rk, ck))
                flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
                if role in ("auto", "over", "free"):
                    flags |= Qt.ItemIsEditable
                if role == "name" and rk and rk.startswith("r"):
                    flags |= Qt.ItemIsEditable                    # freie Zeile: Name hier änderbar
                it.setFlags(flags)
                if role in ("head", "group"):
                    it.setForeground(QColor(STYLE.colors()["text2"]))
                if role == "name" or (role == "head" and self.tb.get("transpose") and j > 0):
                    it.setFont(bold)
                if role == "over":
                    it.setForeground(QColor("#c77c0e"))
                    it.setToolTip(T("cmp_over_tip", v=(tv.get((rk, ck)) or ("", "", ""))[2] or "–"))
                self.grid.setItem(i, j, it)
        # gleiche Gruppen nebeneinander (bzw. untereinander, gedreht) zusammenfassen
        if self.tb.get("transpose"):
            col = [mat[i][0][0] for i in range(len(mat))] if mat and self.logical()[0] else []
            self._spans(col, lambda a, n: self.grid.setSpan(a, 0, n, 1))
        elif self.logical()[0] and mat:
            self._spans([t for t, *_ in mat[0]], lambda a, n: self.grid.setSpan(0, a, 1, n))
        self.grid.fit()
        self.grid.blockSignals(False)
        self._loading = False
        self.show_cell()

    @staticmethod
    def _spans(texts, setter):
        a = 0
        while a < len(texts):
            b = a + 1
            while b < len(texts) and texts[b] == texts[a] and texts[a]:
                b += 1
            if b - a > 1:
                setter(a, b - a)
            a = b

    def _cell_key(self, item):
        role, rk, ck = item.data(Qt.UserRole) if item is not None else (None, None, None)
        return role, rk, ck

    def cell_edited(self, item):
        if self._loading:
            return
        role, rk, ck = self._cell_key(item)
        text = re.sub(r"\\(.)", r"\1", item.text()).strip()
        if role == "name":
            for r in self.tb["rows"]:
                if r["id"] == rk and text:
                    r["name"] = text
            return self.table_changed(cols=True)
        if role not in ("auto", "over", "free"):
            return
        k = f"{rk}|{ck}"
        col = next(c for c in self.tb["cols"] if c["id"] == ck)
        if col["kind"] == "auto":
            m = next((m for m in self.members() if m["key"] == rk), None)
            tv = auto_value(col["key"], self.rec(m), m, col) if m else ""
            if text == tv:
                self.tb["cells"].pop(k, None)
            else:
                self.tb["cells"][k] = text
        elif text:
            self.tb["cells"][k] = text
        else:
            self.tb["cells"].pop(k, None)
        QTimer.singleShot(0, self.table_changed)

    def show_cell(self):
        if not hasattr(self, "btn_reset_cell"):
            return
        role, rk, ck = self._cell_key(self.grid.currentItem())
        over = role == "over"
        self.btn_reset_cell.setEnabled(over)
        if role in ("auto", "over"):
            col = next(c for c in self.tb["cols"] if c["id"] == ck)
            m = next((m for m in self.members() if m["key"] == rk), None)
            tv = auto_value(col["key"], self.rec(m), m, col) if m else ""
            self.lbl_cell.setText(T("cmp_cell_tab", v=tv or "–") + ("  ·  " + T("cmp_cell_over") if over else ""))
        else:
            self.lbl_cell.setText(T("cmp_cell_hint"))

    def reset_cell(self):
        role, rk, ck = self._cell_key(self.grid.currentItem())
        if role == "over":
            self.tb["cells"].pop(f"{rk}|{ck}", None)
            self.table_changed()

    def figure_spec(self):
        return None

    # -- Ausgabe ----------------------------------------------------------------------------
    def export_table(self):
        """-> (Kopf, Zeilen, Gruppenzeile [(Text, Spalten)] oder None, fette Spalten) als Markup, englisch."""
        mat, n_head = self.matrix(english=True)
        if self.tb.get("transpose"):
            header = [t for t, *_ in mat[0]]
            rows = [[t for t, *_ in r] for r in mat[1:]]
            if self.logical()[0]:                              # Gruppe nur in der ersten Zeile ihres Blocks
                prev = None
                for r in rows:
                    r[0], prev = ("" if r[0] == prev else r[0]), r[0]
            return header, rows, None, ()
        top = None
        if n_head == 2:
            top, texts = [], [t for t, *_ in mat[0]]
            a = 0
            while a < len(texts):
                b = a + 1
                while b < len(texts) and texts[b] == texts[a] and texts[a]:
                    b += 1
                top.append((texts[a], b - a))
                a = b
        return [t for t, *_ in mat[n_head - 1]], [[t for t, *_ in r] for r in mat[n_head:]], top, (0,)

    def si_blocks(self, out_dir, item):
        """„Table Sn: <Name>.“ und die Tabelle mit dem Schreiber des Word-Exports (Spaltenbreiten nach Inhalt)."""
        header, rows, top, bold = self.export_table()
        if not rows or len(header) < 2:
            return []
        return [("tabcap", _esc(item["name"]), ""), ("params", header, rows, dict(bold_cols=bold, top=top, fit=True))]

    def table_html(self):
        from elucida.tabs import xray as XRAY
        header, rows, top, bold = self.export_table()
        tb = "border-top:1px solid black;"
        bb = "border-bottom:1px solid black;"
        h = '<table cellspacing="0" cellpadding="4" style="border-collapse:collapse">'
        if top:
            h += "<tr>" + "".join(f'<th colspan="{n}" style="{tb}{bb if t else ""}">{XRAY.to_html(t)}</th>'
                                  for t, n in top) + "</tr>"
        h += "<tr>" + "".join(f'<th style="{"" if top else tb}{bb}">{XRAY.to_html(t)}</th>' for t in header) + "</tr>"
        for i, r in enumerate(rows):
            st = bb if i == len(rows) - 1 else ""
            h += "<tr>" + "".join(f'<td style="text-align:center;{st}">' + (f"<b>{XRAY.to_html(c)}</b>" if j in bold
                                                                              else XRAY.to_html(c)) + "</td>"
                                  for j, c in enumerate(r)) + "</tr>"
        return h + "</table>"

    def copy_table(self):
        from elucida.si import lines as SI
        from elucida.tabs import xray as XRAY
        header, rows, *_ = self.export_table()
        md = QMimeData()
        md.setText(XRAY.table_plain(header, rows))
        md.setHtml(SI.nbsp(self.table_html()))
        QApplication.clipboard().setMimeData(md)
        self.main.statusBar().showMessage(T("cmp_copied"), 4000)

    def export_to(self, base: Path):
        from elucida.si import excel as XL
        from elucida.si import lines as SI
        from elucida.tabs import xray as XRAY
        base = Path(base).resolve()
        header, rows, top, bold = self.export_table()
        if not rows or len(header) < 2:
            raise RuntimeError(T("cmp_table_empty"))
        name = self.page.item["name"]
        docx = base.with_suffix(".docx")
        SI.write_docx(docx, [("tabcap", _esc(name), ""), ("params", header, rows, dict(bold_cols=bold, top=top, fit=True))])
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Comparison"
        XL._sheet(ws, [2, 26] + [22] * (len(header) - 1) + [2])
        XL._put(ws, 2, 2, name, XL.F_TITLE, align=XL.LEFT)
        r0 = 4
        if top:
            c0 = 2
            for t, n in top:
                XL._put(ws, r0, c0, XRAY.to_rich_xlsx(t) if t else None, XL.F_BOLD, fill=XL.HEAD_FILL,
                        border=XL.HEAD_LINE if t else None)
                if n > 1:
                    ws.merge_cells(start_row=r0, start_column=c0, end_row=r0, end_column=c0 + n - 1)
                c0 += n
            r0 += 1
        for c, v in enumerate(header):
            XL._put(ws, r0, 2 + c, XRAY.to_rich_xlsx(v) if v else None, XL.F_BOLD,
                    align=XL.LEFT if c == 0 else XL.CENTER, fill=XL.HEAD_FILL, border=XL.HEAD_LINE)
        for ri, row in enumerate(rows, r0 + 1):
            for c, v in enumerate(row):
                XL._put(ws, ri, 2 + c, XRAY.to_rich_xlsx(v) if v else None, XL.F_BOLD if c in bold else XL.F_BASE,
                        align=XL.LEFT if c == 0 else XL.CENTER, border=XL.ROW_LINE)
        xlsx = base.with_suffix(".xlsx")
        wb.save(xlsx)
        csv_p = base.with_suffix(".csv")
        with open(csv_p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            if top:
                w.writerow([XRAY.to_plain(t) for t, n in top for _ in range(n)])
            for r in [header] + rows:
                w.writerow([XRAY.to_plain(c) for c in r])
        return [docx, xlsx, csv_p]


TAB_CLASS = {None: CompareEmpty, "cv": CVStackTab, "spectra": SpectraTab, "table": TableTab}


# ============================================================================ Seite „Vergleich“ der Projektseite
class ComparePage(QWidget):
    """Reiter „Vergleich“ der Projektseite: ein Tab für den gewählten Vergleich (wird beim Wechsel neu gebaut)."""

    def __init__(self, pub_page):
        super().__init__()
        self.pub, self.main = pub_page, pub_page.main
        self.pdir, self.item, self.tab, self.records, self._dirty = None, None, None, {}, True
        self._saved = None
        self.history, self.cursor, self._restoring = [], -1, False   # Rückgängig je offenem Vergleich (wie PathHost)
        self.host = CompareHost(self)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.timer = QTimer(self, singleShot=True, interval=300)
        self.timer.timeout.connect(self.save)

    # -- Projekt ---------------------------------------------------------------------------
    def set_publication(self, pdir):
        self.save()
        self.pdir = Path(pdir) if pdir else None
        self._dirty = True
        if self.isVisible():
            self.load()

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._dirty:
            QTimer.singleShot(0, self.load)

    def items(self):
        return PUB.load(self.pdir).get("comparisons") or [] if self.pdir else []

    def out_dir(self) -> Path:
        return self.pdir / "comparisons"

    def load(self, uid=None):
        """Stände der Verbindungen lesen (nur Dateien, nichts öffnen) und den gewählten Vergleich zeigen."""
        if not self._dirty and uid is None and self.tab is not None:
            return
        self._dirty = False
        self.read_records()
        if self.pdir is not None:
            data = PUB.load(self.pdir)
            items = data.get("comparisons") or []
            uid = uid or (self.item or {}).get("uid")
            self.item = next((x for x in items if x["uid"] == uid), items[0] if items else None)
        else:
            self.item = None
        if self.item is not None:
            self.sync_members(self.item)
        self._saved = json.dumps(self.item, sort_keys=True, default=str)
        self.build()
        self.reset_history()

    def read_records(self):
        """Stände aller Verbindungen des Projekts (nur Dateien lesen, nichts öffnen)."""
        self.records = {}
        if self.pdir is not None:
            for d in PUB.sync(self.pdir)[0]:
                rel = PUB._rel(self.pdir.resolve(), d.resolve())
                self.records[rel] = read_compound(d, rel)

    # -- Rückgängig/Wiederholen ------------------------------------------------------------------
    # Wie der Reaktionspfad (`PathHost`): eigene Schnappschüsse des offenen Vergleichs, das Hauptfenster leitet
    # Rückgängig/Wiederholen hierher, solange der Reiter offen ist. Nur der Eintrag in publication.elucida ändert sich,
    # nie die Daten der Verbindungen.
    def _snap(self):
        return json.dumps(self.item, sort_keys=True, default=str)

    def reset_history(self):
        """Neuer Verlauf nach dem Öffnen; erst nach dem ersten Zeichnen (der Tab ergänzt dabei Vorgaben im Zustand)."""
        self._restoring = True
        self.history, self.cursor = [], -1
        QTimer.singleShot(400, self._end_restore)

    def _end_restore(self):
        self._restoring = False
        if self.item is None:
            self.history, self.cursor = [], -1
        elif self.cursor < 0:
            self.history, self.cursor = [self._snap()], 0
        else:
            self.history[self.cursor] = self._snap()           # tatsächlichen Zustand übernehmen
        self.main._update_undo_actions()

    def record(self):
        if self._restoring or self.item is None or self.cursor < 0:
            return
        snap = self._snap()
        if snap == self.history[self.cursor]:
            return
        self.history = self.history[:self.cursor + 1] + [snap]
        del self.history[:-200]
        self.cursor = len(self.history) - 1
        self.main._update_undo_actions()

    def can_undo(self, delta):
        return self.item is not None and 0 <= self.cursor + delta < len(self.history)

    def undo(self, delta):
        if self.tab is not None and self.tab.timer.isActive():   # Änderung, deren Vorschau noch aussteht, zuerst erfassen
            self.tab.timer.stop()
            self.tab.render()
        if not self.can_undo(delta) or self._restoring:
            return
        self.cursor += delta
        self._restoring = True
        self.item = json.loads(self.history[self.cursor])
        self.save()
        self.build()
        QTimer.singleShot(400, self._end_restore)

    def sync_members(self, item):
        """Neue Verbindungen des Projekts anhängen (in neuen Vergleichen gewählt, sonst abgewählt), Farbe und Schlüssel."""
        st = item.setdefault("st", {})
        ms = st.setdefault("members", [])
        known = {m["dir"] for m in ms}
        fresh = not ms
        for rel in self.records:
            if rel not in known:
                ms.append({"dir": rel, "on": fresh})
        for k, m in enumerate(ms):
            m.setdefault("key", uuid.uuid4().hex[:8])
            m.setdefault("color", TABS.PALETTE[k % len(TABS.PALETTE)])

    def _drop_tab(self):
        if self.tab is not None:
            self.tab.timer.stop()
            for x in (self.tab.dragger, self.tab.hover):
                if x is not None:
                    x.disconnect()
            self.lay.removeWidget(self.tab)
            self.tab.hide()
            self.tab.deleteLater()
            self.tab = None

    def dispose(self):
        """Seite für die Gesamt-SI wieder abbauen (speichert nichts)."""
        self.timer.stop()
        self.pdir = None
        self._drop_tab()
        self.host.deleteLater()
        self.deleteLater()

    def build(self):
        self._drop_tab()
        kind = (self.item or {}).get("kind")
        st = self.item.setdefault("st", {}) if self.item is not None else {}
        self.tab = TAB_CLASS.get(kind, CompareEmpty)(self.host, st)
        self.lay.addWidget(self.tab)
        self.tab.btn_export.setEnabled(self.item is not None)
        self.pub.sync_main_button()

    def open(self, uid):
        if self.item is not None and self.item["uid"] == uid:
            return
        self.save()
        self.load(uid)

    # -- Ändern ----------------------------------------------------------------------------
    def changed(self):
        self.record()
        self.timer.start()

    def save(self):
        """Gewählten Vergleich in publication.elucida (nur bei einer Änderung)."""
        self.timer.stop()
        if self.pdir is None or self.item is None:
            return
        snap = json.dumps(self.item, sort_keys=True, default=str)
        if snap == self._saved:
            return
        data = PUB.load(self.pdir)
        items = data.get("comparisons") or []
        for k, x in enumerate(items):
            if x["uid"] == self.item["uid"]:
                items[k] = json.loads(snap)
        data["comparisons"] = items
        PUB.save(self.pdir, data)
        self._saved = snap

    def add(self, kind):
        if self.pdir is None:
            return
        self.save()
        data = PUB.load(self.pdir)
        items = data.get("comparisons") or []
        n = 1 + sum(1 for x in items if x["kind"] == kind)
        item = {"uid": uuid.uuid4().hex[:12], "name": f"{T('cmp_kind_' + kind)} {n}", "kind": kind, "st": {}}
        if kind == "table":
            item["st"]["table"] = {"cols": [{"id": uuid.uuid4().hex[:8], "kind": "auto", "key": "formula", "group": ""}],
                                   "rows": [], "cells": {}, "transpose": False}
        self.item = item
        self.sync_members(item)
        data["comparisons"] = items + [item]
        PUB.save(self.pdir, data)
        self._saved = json.dumps(item, sort_keys=True, default=str)
        self.build()
        self.reset_history()

    def rename(self, name):
        name = name.strip()
        if self.item is None or not name or name == self.item["name"]:
            return
        self.item["name"] = name
        self.record()
        self.save()
        QTimer.singleShot(0, self.build)                     # Liste zeigt den neuen Namen

    def remove(self):
        """Nur den Eintrag aus der Projektdatei nehmen (Exporte im Ordner bleiben)."""
        if self.item is None:
            return
        data = PUB.load(self.pdir)
        data["comparisons"] = [x for x in data.get("comparisons") or [] if x["uid"] != self.item["uid"]]
        PUB.save(self.pdir, data)
        self.item = None
        self._dirty = True
        self.history, self.cursor = [], -1
        self.main._update_undo_actions()
        QTimer.singleShot(0, self.load)

    def refresh_snapshots(self):
        """„Aktualisieren“: Verbindungen ohne oder mit veraltetem Stand kurz öffnen und den Stand neu schreiben."""
        self.save()
        kind = (self.item or {}).get("kind")
        dirs = [r["dir"] for r in self.records.values() if status(r, kind) in ("outdated", "missing")]
        uid = (self.item or {}).get("uid")
        pdir = self.pdir
        n = refresh_compounds(self.main, pdir, dirs, needs(kind))
        self.pub.project_tabs.setCurrentWidget(self)
        self._dirty = True
        self.load(uid)
        self.main.statusBar().showMessage(T("cmp_refreshed", n=n), 5000)
        return n


# ============================================================================ Gesamt-SI
def si_blocks(main, pdir, out_dir, sections):
    """Vergleiche mit „In die Gesamt-SI“ -> [(Kapitelschlüssel bzw. „new:<Überschrift>“, Blöcke)] in der Reihenfolge der
    Projektdatei. Gezeichnet wird mit demselben Tab und denselben Ständen wie auf der Projektseite (nichts neu
    ausgewertet): Abbildungen als Bild + „Figure Sn“, Tabellen als „Table Sn“ mit dem Tabellenschreiber des Exports."""
    items = [x for x in PUB.load(pdir).get("comparisons") or [] if (x.get("si") or {}).get("on")]
    if not items:
        return []
    page = ComparePage(main.pub_page)                       # eigene, nie gezeigte Seite: die offene bleibt, wie sie ist
    page.pdir = Path(pdir)
    page._restoring = True                                  # kein Rückgängig-Schritt, nichts speichern
    page.read_records()
    out = []
    try:
        for it in items:
            key = si_key(it)
            key = "dft_figs" if key == "dft" else key
            if not (key.startswith("new:") or key in sections or (key == "dft_figs" and "dft" in sections)):
                continue
            page.item = copy.deepcopy(it)
            page.sync_members(page.item)
            page.build()
            bl = page.tab.si_blocks(out_dir, it)
            if bl:
                out.append((key, bl))
    finally:
        page.item = None
        page.dispose()
    return out
