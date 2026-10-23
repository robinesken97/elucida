"""
elucida/app/project.py - Projektordner: Zustand aller Tabs in einer Datei, Eingabedateien als Kopie.

<Projekt>/                (seit 2.1; Ordner entstehen erst, wenn etwas hineinkommt)
    project.uvvis      Zustand (YAML), Pfade relativ zum Projektordner
    elucida.json       Austausch mit Characterization (elucida/exchange)
    SI/                Word-Dateien und SI-Texte (<Name>_SI.docx, _methods.txt …)
    figures/           Abbildungen (<Name>_CV.pdf/.svg/.png …), werden beim Export überschrieben
    tables/            Tabellen und Datendateien (CSV, Excel, xyz, EasySpin-Text)
    data/<Analytik>/   Messdaten je Tab (nmr, ir, hrms, uvvis, cv, sec, epr, xray, dft …)
    structures/        ChemDraw-Strukturen (mit gleichnamigen Exporten), Schemata, Fotos
    .elucida/          Zwischenbilder für Word, Cache, Sicherung (versteckt)

Alte Projekte (data/, images/, exports/) bleiben lesbar: gespeicherte Pfade gelten weiter, nur neue Dateien und Exporte
kommen in die neue Struktur.
"""
from __future__ import annotations

import copy
import hashlib
import os
import shutil
import sys
from pathlib import Path

import yaml

PROJECT_FILE = "project.uvvis"
FORMAT_VERSION = 1
STRUCTURES = "structures"
SI_DIR, FIGURES, TABLES, WORK = "SI", "figures", "tables", ".elucida"
# Unterordner von data/ je Tab (Schlüssel = STATE_KEY, ε-Tab „eps“)
DATA_SUB = {"eps": "uvvis", "overlay": "overlay", "fluorescence": "fluorescence", "cv": "cv", "sec": "sec",
            "epr": "epr", "irms": "ir", "hrms": "hrms", "nmr": "nmr", "xray": "xray", "dft": "dft", "syn": "synthesis"}
# Teil der Exportnamen je Tab: <Verbindung>_<Label>.*
EXPORT_LABEL = {"eps": "UV-Vis", "overlay": "Overlay", "fluorescence": "Fluorescence", "cv": "CV", "sec": "SEC",
                "epr": "EPR", "irms": "IR", "hrms": "HRMS", "nmr": "NMR", "xray": "X-ray", "dft": "DFT",
                "syn": "Synthesis"}
FIGURE_EXT = {".pdf", ".svg", ".png", ".tif", ".tiff", ".jpg", ".jpeg", ".emf", ".eps"}
SI_SUFFIXES = ("_SI.txt", "_methods.txt", "_captions.txt", "_NMR.txt")


def data_sub(key) -> str:
    """Ziel für Messdaten eines Tabs, z. B. „data/cv“ (für import_file)."""
    return "data/" + DATA_SUB.get(key, key)


def is_project(path) -> Path | None:
    """Projektordner oder project.uvvis -> Projektordner, sonst None."""
    p = Path(path)
    if p.is_file() and p.name == PROJECT_FILE:
        return p.parent
    if p.is_dir() and (p / PROJECT_FILE).exists():
        return p
    return None


def _path_slots(state):
    """Alle Stellen im Zustand, an denen ein Dateipfad steht: (Container, Schlüssel, Unterordner)."""
    slots = []
    eps = state.get("eps") or {}
    files = eps.get("files") or []
    for i in range(len(files)):
        slots.append((files, i, data_sub("eps")))
    for st in (eps.get("series") or {}).values():
        slots += [(st, "structure", STRUCTURES), (st, "photo", STRUCTURES)]
    ov = state.get("overlay") or {}
    for e in ov.get("entries") or []:
        slots.append((e, "file", data_sub("overlay")))
        slots.append((e, "structure", STRUCTURES))
        files = e.get("files") or []                  # SEC-Serie: eine Datei je Spektrum
        slots += [(files, i, data_sub("overlay")) for i in range(len(files))]
        for src in e.get("sources") or []:            # kombinierte TD-DFT-Einträge
            slots.append((src, "file", data_sub("overlay")))
    slots.append((ov, "structure", STRUCTURES))
    for e in (state.get("cv") or {}).get("files") or []:
        slots.append((e, "file", data_sub("cv")))
        slots.append((e, "structure", STRUCTURES))
    sec = state.get("sec") or {}
    specs = sec.get("spec_files") or []
    slots += [(specs, i, data_sub("sec")) for i in range(len(specs))]
    slots.append((sec, "dta", data_sub("sec")))
    for e in (state.get("epr") or {}).get("entries") or []:
        slots += [(e, "file", data_sub("epr")), (e, "params", data_sub("epr"))]
    slots.append((state.get("compound") or {}, "structure", STRUCTURES))
    ir = state.get("irms") or {}
    slots += [(ir, k, data_sub("irms")) for k in ("ir_file", "ir_pdf", "ms_file", "ms_raw")]
    hr = state.get("hrms") or {}
    slots += [(hr, "ms_file", data_sub("hrms")), (hr, "ms_raw", data_sub("hrms"))]
    for e in (state.get("xray") or {}).get("entries") or []:
        slots.append((e, "file", data_sub("xray")))
    for e in (state.get("dft") or {}).get("entries") or []:
        slots.append((e, "file", data_sub("dft")))
    slots.append((state.get("nmr") or {}, "structure", STRUCTURES))
    slots.append((state.get("syn") or {}, "scheme", STRUCTURES))
    for e in (state.get("nmr") or {}).get("spectra") or []:
        slots += [(e, "file", data_sub("nmr")), (e, "bruker", data_sub("nmr"))]
    fl = state.get("fluo") or {}
    slots += [(fl, "abs_file", data_sub("fluorescence")), (fl, "em_file", data_sub("fluorescence")),
              (fl, "structure", STRUCTURES), (fl, "photo_day", STRUCTURES), (fl, "photo_uv", STRUCTURES)]
    return slots


def _get(cont, key):
    try:
        return cont[key]
    except (KeyError, IndexError, TypeError):
        return None


def _digest(p: Path):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save(project_dir, state) -> dict:
    """Kopiert alle referenzierten Dateien in den Projektordner und schreibt project.uvvis.
    Gibt den Zustand mit absoluten Pfaden auf die Kopien zurück."""
    pdir = Path(project_dir).resolve()
    pdir.mkdir(parents=True, exist_ok=True)
    abs_state = copy.deepcopy(state)
    copied = {}                                        # Quelle -> Ziel (gleiche Datei nur einmal)
    for cont, key, sub in _path_slots(abs_state):
        src = _get(cont, key)
        if not src:
            continue
        src = Path(src).resolve()
        if not src.exists():
            continue
        if pdir in src.parents:                        # liegt schon im Projekt
            cont[key] = str(src)
            continue
        if str(src) not in copied:
            copied[str(src)] = str(_copy_unique(src, pdir / sub))
            # zur CDXML gehörige ChemDraw-Exporte (gleicher Name) mitnehmen
            sibs = {".cdxml": (".svg", ".pdf", ".png", ".tif", ".tiff"),           # ChemDraw-Exporte
                    ".dsc": (".dta", ".ygf", ".xml"), ".dta": (".dsc", ".ygf", ".xml")}   # Bruker BES3T
            if src.suffix.lower() in sibs:
                target = Path(copied[str(src)])
                for sib in src.parent.glob(src.stem + ".*"):
                    if sib.stem == src.stem and sib.suffix.lower() in sibs[src.suffix.lower()]:
                        shutil.copy2(sib, target.with_suffix(sib.suffix))
        cont[key] = copied[str(src)]
    rel_state = copy.deepcopy(abs_state)
    for cont, key, _ in _path_slots(rel_state):
        v = _get(cont, key)
        if v and Path(v).is_absolute() and pdir in Path(v).parents:
            cont[key] = Path(v).relative_to(pdir).as_posix()
    rel_state["format_version"] = FORMAT_VERSION
    (pdir / PROJECT_FILE).write_text(yaml.safe_dump(rel_state, allow_unicode=True, sort_keys=False),
                                     encoding="utf-8")
    return abs_state


BRUKER_D_FILES = ("analysis.baf", "analysis.sqlite")      # aus einem .d-Ordner nur das, was gelesen wird
NMR_EXP_FILES = ("acqus", "acqu2s", "pulseprogram")         # Bruker-NMR-Experiment: nur die Parameter (kein FID)


def _copy_dir(src: Path, dest_dir: Path) -> Path:
    """Messordner (z. B. Bruker .d) übernehmen; bei .d nur die gelesenen Dateien (Rohdaten + Index)."""
    names = [n for n in BRUKER_D_FILES if (src / n).exists()] if src.suffix.lower() == ".d" else None
    if names is None and (src / "acqus").is_file():
        names = [n for n in NMR_EXP_FILES if (src / n).exists()]
    target, n = dest_dir / src.name, 2
    while target.exists():
        if names and all((target / x).exists() and (target / x).stat().st_size == (src / x).stat().st_size
                         for x in names):
            return target                              # derselbe Messordner ist schon da
        target = dest_dir / f"{src.stem}_{n}{src.suffix}"
        n += 1
    if names:
        target.mkdir(parents=True)
        for x in names:
            shutil.copy2(src / x, target / x)
    else:
        shutil.copytree(src, target)
    return target


def _copy_unique(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        return _copy_dir(src, dest_dir)
    target = dest_dir / src.name
    n = 2
    while target.exists():
        if target.stat().st_size == src.stat().st_size and _digest(target) == _digest(src):
            return target                              # identische Datei bereits vorhanden
        target = dest_dir / f"{src.stem}_{n}{src.suffix}"
        n += 1
    shutil.copy2(src, target)
    return target


def load(project_dir) -> dict:
    """project.uvvis lesen, relative Pfade auf den Projektordner beziehen."""
    pdir = Path(project_dir).resolve()
    state = yaml.safe_load((pdir / PROJECT_FILE).read_text(encoding="utf-8")) or {}
    for cont, key, _ in _path_slots(state):
        v = _get(cont, key)
        if v and not Path(v).is_absolute():
            cont[key] = str((pdir / v).resolve())
    return state


def missing_files(state) -> list:
    return [_get(c, k) for c, k, _ in _path_slots(state) if _get(c, k) and not Path(_get(c, k)).exists()]


def import_file(project_dir, src, sub) -> str:
    """Datei ins Projekt übernehmen (Kopie nach data/ bzw. images/), falls sie nicht schon darin liegt.
    Bei CDXML werden gleichnamige ChemDraw-Exporte (SVG/PDF/PNG/TIFF) mitkopiert."""
    pdir = Path(project_dir).resolve()
    src = Path(src).resolve()
    if pdir == src.parent or pdir in src.parents:
        return str(src)
    dest_dir = pdir / sub
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = _copy_unique(src, dest_dir)
    if src.suffix.lower() in (".out", ".log") and src.with_suffix(".xyz").is_file():   # ORCA: Endgeometrie, 14 Stellen
        shutil.copy2(src.with_suffix(".xyz"), target.with_suffix(".xyz"))
    if src.suffix.lower() == ".cdxml":
        for sib in src.parent.glob(src.stem + ".*"):
            if sib.stem == src.stem and sib.suffix.lower() in (".svg", ".pdf", ".png", ".tif", ".tiff"):
                shutil.copy2(sib, target.with_suffix(sib.suffix))
    return str(target)


def write(project_dir, state):
    """Zustand speichern (automatisch). Dateien außerhalb des Projekts werden dabei noch übernommen."""
    return save(project_dir, state)


def create(project_dir):
    """Projektordner anlegen bzw. einen vorhandenen Ordner zum Projekt machen (Unterordner erst bei Bedarf)."""
    pdir = Path(project_dir).resolve()
    pdir.mkdir(parents=True, exist_ok=True)
    if not (pdir / PROJECT_FILE).exists():
        save(pdir, {})
    return pdir


def backup(project_dir):
    """Sicherung vor dem Öffnen: .elucida/project.uvvis.bak."""
    pf = Path(project_dir) / PROJECT_FILE
    if pf.exists():
        shutil.copy2(pf, work_dir(project_dir) / (PROJECT_FILE + ".bak"))


def _hide(d: Path):
    """Ordner unter Windows verstecken (unter macOS/Linux reicht der Punkt am Anfang)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(d), 0x02)       # FILE_ATTRIBUTE_HIDDEN
        except Exception:
            pass


def work_dir(project_dir, *parts) -> Path:
    """Arbeitsordner .elucida/… (Zwischenbilder für Word, Cache, Sicherung); nichts für den Nutzer."""
    root = Path(project_dir) / WORK
    if not root.exists():
        root.mkdir(parents=True)
        _hide(root)
    d = root.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_dir(project_dir, kind) -> Path:
    """Exportziel SI/, figures/ oder tables/ (wird angelegt)."""
    assert kind in (SI_DIR, FIGURES, TABLES), kind
    d = Path(project_dir) / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_stem(name, key) -> str:
    """Dateiname ohne Endung: <Verbindung>_<Tab>, z. B. „S2_CV“."""
    from elucida.core.uvvis import safe_name
    return f"{safe_name(name)}_{EXPORT_LABEL.get(key, key)}"


def export_kind(path) -> str:
    """Zielordner einer Exportdatei nach Art: Abbildung, SI-Text/Word oder Tabelle/Daten."""
    p = Path(path)
    if p.suffix.lower() in FIGURE_EXT:
        return FIGURES
    if p.suffix.lower() == ".docx" or p.name.endswith(SI_SUFFIXES):
        return SI_DIR
    return TABLES


def staging(project_dir, key) -> Path:
    """Leerer Zwischenordner für einen Export; place_exports verteilt die Dateien danach."""
    d = work_dir(project_dir, "export", key)
    for f in d.iterdir():
        shutil.rmtree(f) if f.is_dir() else f.unlink()
    return d


def place_exports(project_dir, files) -> list:
    """Geschriebene Exportdateien nach SI/, figures/, tables/ verschieben (gleichnamige werden überschrieben).
    PermissionError, wenn eine Zieldatei gerade offen ist (Windows/Excel)."""
    out = []
    for f in files:
        f = Path(f)
        if not f.exists():
            continue
        dst = export_dir(project_dir, export_kind(f)) / f.name
        os.replace(f, dst)
        out.append(dst)
        if f.parent.parent.name == "export" and not any(f.parent.iterdir()):
            f.parent.rmdir()                           # leerer Zwischenordner (.elucida/export/<Tab>)
    return out
