"""Schnellvergleich (1.5.0): abgelegte Dateien vergleichen, ohne vorher Verbindungen anzulegen.

Jede Datei wird eine Verbindung im internen Projekt „Einzelauswertungen“ (wie die Schnellauswertung) und dort mit dem
Lader ihres Tabs gelesen; beim Speichern entsteht ihr Vergleichsstand. Die Art erkennt nur der Inhalt (wie das
Ablegen im Hauptfenster, aber unabhängig vom offenen Tab); was nicht eindeutig ist, bleibt „nicht erkannt“ mit Grund.
"""
from __future__ import annotations

from pathlib import Path

from elucida.app import comparison as CMP
from elucida.app import publication as PUB
from elucida.core import uvvis as core

# Quelle des Stands -> Vergleichsart, in der die Datei gezeigt wird (gleiche Art = ein gemeinsames Bild)
KIND = {"cv": "cv", "hcell": "hcell", "epr": "spectra", "irms": "spectra", "sec": "spectra", "eps": "spectra",
        "nmr": "table", "xray": "table", "dft": "table", "hrms": "table"}


KEEP = ("recent_projects", "last_dir")                # Einstellungen, die das Anlegen und Laden je Datei verstellt


GROUPS = "quick_groups"                             # publication.elucida von „Einzelauswertungen“: {gid: Gruppe}
# Art des Schnellvergleichs je Quelle -> (Vergleichsart, Vorgaben des Zustands); Spektren je Messart getrennt
PART = {"cv": ("cv", {}), "hcell": ("hcell", {}), "eps": ("spectra", {"content": "eps"}),
        "irms": ("spectra", {"content": "ir"}), "epr": ("spectra", {"content": "epr"}),
        "nmr": ("table", {}), "xray": ("table", {}), "dft": ("table", {}), "hrms": ("table", {}), "sec": ("spectra", {"content": "sec"})}
PART_ORDER = ("cv", "hcell", "eps", "sec", "irms", "epr", "table")      # Reihenfolge der Reiter
TABLE_COLS = {"xray": ("xr_sg", "xr_system"), "dft": ("dft_method", "dft_eel", "dft_homo", "dft_lumo"),
              "hrms": ("hrms_ion", "hrms_calc", "hrms_found", "hrms_dev"), "sec": ("sec_e12", "sec_ref"),
              "nmr": ("nmr_shift",)}


def part_of(src) -> str:
    """Reiter einer Quelle: gleiche Art = ein gemeinsames Bild (Tabellenquellen teilen eine Tabelle)."""
    return "table" if PART[src][0] == "table" else src


def file_dirs(q) -> set[Path]:
    """Verbindungen aus Dateien eines Schnellvergleichs (die Übersicht zeigt statt ihrer den Vergleich)."""
    q = Path(q).resolve()
    data = PUB.load(q)
    live = {x.get("quick") for x in data.get("comparisons") or []}     # Karte entfernt: Dateien wieder sichtbar
    return {(q / f["dir"]).resolve() for gid, g in (data.get(GROUPS) or {}).items() if gid in live
            for f in g.get("files") or []}


def _hcell_main(d: Path):
    """Ordner einer Lade/Entlade-Messung: die Hauptdatei (Gamry, TAG PWR800…) neben CHARGE_DISCHARGE/."""
    from elucida.formats.gamry import gamry_tag
    if not (d / "CHARGE_DISCHARGE").is_dir():
        return None
    mains = [p for p in sorted(d.iterdir()) if p.is_file() and p.suffix.lower() == ".dta"
             and (gamry_tag(p) or "").startswith("PWR800")]
    return mains[0] if len(mains) == 1 else None


def detect(path) -> tuple[str | None, str, Path]:
    """Datei oder Ordner -> (Quelle, Grund-Schlüssel falls nicht erkannt, zu ladender Pfad). Nie nach Endung raten,
    wo der Inhalt entscheidet; nie nach dem offenen Tab."""
    from elucida.formats.gamry import gamry_tag
    from elucida.tabs import dft as DFT, ir_ea as IRMS, nmr as NMR, sec as SECMOD, xray as XRAY
    p = Path(path)
    ext = p.suffix.lower()
    if p.is_dir():
        if IRMS.is_bruker_d(p):
            return "hrms", "", p
        if NMR.find_experiments(p):
            return "nmr", "", p
        m = _hcell_main(p)
        if m is not None:
            return "hcell", "", m
        return None, "qc_why_folder", p
    if not p.is_file():
        return None, "qc_why_missing", p
    if SECMOD.is_bwspec(p) or SECMOD.is_merged(p):
        return "sec", "", p
    if XRAY.is_cif(p):
        return "xray", "", p
    if NMR.is_nmr_svg(p) or ext == ".mnova":
        return "nmr", "", p
    if DFT.is_xyz(p) or DFT.is_calc(p):
        return "dft", "", p
    if ext == ".docx":
        return "hrms", "", p
    if IRMS.is_opus(p):
        return "irms", "", p
    if ext == ".dta" or ext == ".dsc":
        tag = gamry_tag(p) if ext == ".dta" else None
        if tag is None:
            return "epr", "", p
        if tag.startswith("PWR800"):                     # Kapazität ohne Schrittdateien: der Ordner gehört dazu
            return (("hcell", "", p) if (p.parent / "CHARGE_DISCHARGE").is_dir() else (None, "qc_why_hcell", p))
        return "cv", "", p
    if ext == ".pdf":
        return None, "qc_why_pdf", p                    # HRMS-Bericht oder IR? Im Hauptfenster entscheidet der Tab
    if ext in {".csv", ".txt"} | core.BINARY_EXT:
        return "eps", "", p                             # Absorptionsspektren; Kinetik/Fluoreszenz über „Art wählen“
    return None, "qc_why_unknown", p


def _load(main, src, p: Path) -> None:
    """Datei mit dem Lader ihres Tabs lesen (wie `MainWindow._drop`; Unlesbares meldet der Tab selbst)."""
    from elucida.tabs import ir_ea as IRMS, nmr as NMR
    if src == "eps":
        main.open_files([str(p)])
    elif src == "nmr":
        if p.is_dir():
            main.nmr_tab.import_topspin(str(p))
        elif p.suffix.lower() == ".mnova":
            main.nmr_tab.add_mnova_file(str(p))
        elif NMR.is_nmr_svg(p):
            main.nmr_tab.load_svg(str(p))
    elif src == "hrms":
        (main.hrms_tab.load_raw if IRMS.is_bruker_d(p) else main.hrms_tab.load_ms)(str(p))
    elif src == "xray":
        main.xray_tab.load_cif(str(p))
    elif src == "dft":
        main.dft_tab.load_xyz(str(p))
    else:
        tab, fn = {"cv": ("cv_tab", "load_files"), "hcell": ("hcell_tab", "load_files"), "epr": ("epr_tab", "load_exp"),
                   "irms": ("irms_tab", "load_ir_files"), "sec": ("sec_tab", "load_spectra")}[src]
        getattr(getattr(main, tab), fn)([str(p)])


def add_files(main, q, group, paths, force=None) -> list[dict]:
    """Dateien als je eine Verbindung in `q` (Einzelauswertungen) anlegen, laden, speichern (schreibt den Stand) und in
    der Gruppe des Schnellvergleichs eintragen (`files`; nicht erkannte in `unrec` mit Grund und Pfad für „Art
    wählen“). force: Quelle, die der Nutzer für eine nicht erkannte Datei gewählt hat. -> neu nicht erkannte."""
    files, unrec = group.setdefault("files", []), []
    keep = {k: main.settings.value(k) for k in KEEP}    # 20 Dateien verdrängten sonst die zuletzt geöffneten
    for path in paths:
        src, why, lp = (force, "", Path(path)) if force else detect(path)
        name = Path(path).name
        if src is None:
            unrec.append({"file": name, "why": why, "path": str(path)})
            continue
        if not main.open_publication(q):
            break
        stem = Path(path).stem if Path(path).is_file() else Path(path).name
        title = stem.replace("_", " ")                  # Beschriftung: „_“ wäre in Unterschrift/Bild ein Index
        cname = PUB.unique_dest(q, core.safe_name(stem)).name
        if not main.new_compound_in_publication(cname):
            unrec.append({"file": name, "why": "qc_why_create"})
            continue
        cdir = Path(main.project_dir)
        _load(main, src, lp)
        main.autosave(force=True)
        rel = PUB._rel(Path(q).resolve(), cdir.resolve())
        entry = CMP.read_compound(cdir, rel)["tabs"].get(src)
        files.append({"dir": rel, "file": name, "src": src, "title": title, "why": "" if entry and (
            src != "eps" or entry.get("series")) else "qc_why_eps_conc" if src == "eps" else "qc_why_novalues"})
    for k, v in keep.items():
        main.settings.remove(k) if v is None else main.settings.setValue(k, v)
    main.fill_recent_menu()
    if paths:
        main.close_project()
        main.open_publication(q)
    group.setdefault("unrec", []).extend(unrec)
    return unrec


def remove_file(main, q, group, rel) -> bool:
    """Datei aus dem Schnellvergleich nehmen: ihre Verbindung in den Papierkorb (nie endgültig), Eintrag weg (die
    Zeilen der Reiter räumt `sync_items` ab). Rückgängig holt sie nicht zurück."""
    d = Path(q) / rel
    if not main.trash_folder(d, confirm=False) and d.exists():
        return False
    PUB.remove_compound(q, d)
    group["files"] = [f for f in group.get("files") or [] if f["dir"] != rel]
    return True


def sync_items(data, gid, name):
    """Vergleiche der Gruppe nach ihren Dateien: je Art ein normaler Vergleich (Export, SI-Text, Rückgängig wie jeder),
    Zeilen nur aus den eigenen Dateien (Beschriftung = Dateiname ohne Endung); ohne Dateien ein leerer Vergleich mit
    Ablagefläche. Ändert `data` (publication.elucida) -> Vergleiche der Gruppe in Reiterreihenfolge."""
    import uuid
    from elucida.app.i18n import T
    from elucida.tabs import base as TABS
    group = data.setdefault(GROUPS, {}).setdefault(gid, {"files": [], "unrec": []})
    items = data.setdefault("comparisons", [])
    mine = [x for x in items if x.get("quick") == gid]
    want = {}
    for f in group["files"]:
        want.setdefault(part_of(f["src"]), []).append(f)
    for x in mine:                                        # leerer Platzhalter wird der erste Reiter
        if x.get("part") is None and want:
            x["part"] = next(k for k in PART_ORDER if k in want)
    have = {x.get("part"): x for x in mine}
    for part in want:
        if part not in have:
            kind, st = PART["nmr" if part == "table" else part]
            have[part] = {"uid": uuid.uuid4().hex[:12], "quick": gid, "part": part, "kind": kind, "st": dict(st)}
            items.append(have[part])
    if not want and None not in have:
        have[None] = {"uid": uuid.uuid4().hex[:12], "quick": gid, "part": None, "kind": None, "st": {}}
        items.append(have[None])
    for part, x in have.items():
        x["name"] = name if part is None else f"{name} · {T('qc_part_' + part)}"
        if part is None:
            continue
        x["kind"] = PART["nmr" if part == "table" else part][0]
        st = x.setdefault("st", {})
        if x["kind"] == "spectra":
            st.setdefault("content", PART[part][1]["content"])
        ms = st.setdefault("members", [])
        fs = want.get(part, [])
        dirs = {f["dir"] for f in fs}
        ms[:] = [m for m in ms if m["dir"] in dirs]
        known = {m["dir"] for m in ms}
        for f in fs:
            if f["dir"] not in known:
                ms.append({"dir": f["dir"], "on": True, "title": f["title"]})
        used = {m.get("color") for m in ms}
        for m in ms:
            m.setdefault("key", uuid.uuid4().hex[:8])
            if not m.get("color"):
                m["color"] = next((c for c in TABS.PALETTE if c not in used), TABS.PALETTE[len(used) % len(TABS.PALETTE)])
                used.add(m["color"])
        if x["kind"] == "table":                          # Spalten der vorhandenen Quellen, eigene bleiben
            tb = st.setdefault("table", {"cols": [], "rows": [], "cells": {}, "transpose": False})
            keys = {c["key"] for c in tb["cols"] if c.get("kind") == "auto"}
            for src in dict.fromkeys(f["src"] for f in fs):
                for k in TABLE_COLS.get(src, ()):
                    if k not in keys:
                        col = {"id": uuid.uuid4().hex[:8], "kind": "auto", "key": k, "group": ""}
                        if k == "nmr_shift":                  # wie „Aus den Tabs“: Ziel tippt der Nutzer
                            col.update(nuc="1H", target=None, tol=CMP.default_tol({"key": k}))
                        tb["cols"].append(col)
                        keys.add(k)
    gone = [x for p_, x in have.items() if p_ is not None and p_ not in want]
    data["comparisons"] = [x for x in items if x not in gone]
    return sorted((x for x in data["comparisons"] if x.get("quick") == gid),
                  key=lambda x: PART_ORDER.index(x["part"]) if x.get("part") in PART_ORDER else -1)


def new_quick(main):
    """Startbildschirm „Neu“ → „Schnellvergleich“ (und „Neuer Vergleich …“ in Projekten): leerer Schnellvergleich mit
    Ablagefläche im internen Projekt „Einzelauswertungen“."""
    import datetime as _dt
    import uuid
    from elucida.app.i18n import T
    q = main.quick_dir()
    if PUB.is_publication(q) is None:
        q.mkdir(parents=True, exist_ok=True)
        PUB.create(q, T("quick_title"))
    if not main.maybe_save() or not main.open_publication(q):
        return False
    main.add_recent_publication(q)
    data = PUB.load(q)
    groups = data.setdefault(GROUPS, {})
    base = T("qc_name", date=_dt.date.today().isoformat())
    names = {g.get("name") for g in groups.values()}
    name = next(n for n in (base if k == 1 else f"{base} ({k})" for k in range(1, len(names) + 2)) if n not in names)
    gid = uuid.uuid4().hex[:12]
    groups[gid] = {"name": name, "files": [], "unrec": []}
    items = sync_items(data, gid, name)
    PUB.save(q, data)
    page = main.pub_page
    cp = page.compare_page
    page.project_tabs.setCurrentWidget(cp)
    cp._dirty = True
    cp.load(items[0]["uid"])
    return True
