"""
elucida/app/project.py - Projektordner: Zustand aller Tabs in einer Datei, Eingabedateien als Kopie.

<Projekt>/                (seit 2.1; Ordner entstehen erst, wenn etwas hineinkommt)
    project.elucida    Zustand (YAML), Pfade relativ zum Projektordner (bis 2.0: project.uvvis, weiter lesbar)
    elucida.json       Austausch mit Characterization (elucida/exchange)
    SI/                Word-Dateien und SI-Texte (<Name>_SI.docx, _methods.txt …)
    figures/           Abbildungen (<Name>_CV.pdf/.svg/.png …), werden beim Export überschrieben
    tables/            Tabellen und Datendateien (CSV, Excel, xyz, EasySpin-Text)
    data/<Analytik>/   Messdaten je Tab (nmr, ir, hrms, uvvis, cv, sec, epr, xray, dft …)
    structures/        ChemDraw-Strukturen (mit gleichnamigen Exporten), Schemata, Fotos
    .elucida/          Zwischenbilder für Word, Cache, Sicherung (versteckt)

Alte Projekte (data/, images/, exports/) bleiben lesbar: gespeicherte Pfade gelten weiter, nur neue Dateien und Exporte
kommen in die neue Struktur. project.uvvis wird gelesen; beim ersten Speichern entsteht project.elucida und die alte
Datei wandert als Sicherung nach .elucida/project.uvvis.old.
"""
from __future__ import annotations

import copy
import hashlib
import os
import shutil
import sys
from pathlib import Path

import yaml

PROJECT_FILE = "project.elucida"
OLD_PROJECT_FILES = ("project.uvvis",)          # bis 2.0 (UVVisTool/Spectravolt/Elucida 2.0): lesen, nie schreiben
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


def project_file(project_dir) -> Path:
    """Projektdatei eines Ordners: project.elucida, sonst die alte project.uvvis, sonst der neue Name (zum Anlegen)."""
    pdir = Path(project_dir)
    for name in (PROJECT_FILE,) + OLD_PROJECT_FILES:
        if (pdir / name).exists():
            return pdir / name
    return pdir / PROJECT_FILE


def is_project(path) -> Path | None:
    """Projektordner oder Projektdatei (project.elucida, alt project.uvvis) -> Projektordner, sonst None."""
    p = Path(path)
    if p.is_file() and p.name in (PROJECT_FILE,) + OLD_PROJECT_FILES:
        return p.parent
    if p.is_dir() and any((p / n).exists() for n in (PROJECT_FILE,) + OLD_PROJECT_FILES):
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
        slots.append((e, "molden", data_sub("dft")))         # Orbitale: Molden-Datei der Rechnung
        slots += [(o, "file", data_sub("dft")) for o in e.get("orbitals") or []]   # je Orbital Cube oder Molden
    slots.append((state.get("nmr") or {}, "structure", STRUCTURES))
    slots.append((state.get("syn") or {}, "scheme", STRUCTURES))
    for e in (state.get("nmr") or {}).get("spectra") or []:
        slots += [(e, "file", data_sub("nmr")), (e, "bruker", data_sub("nmr"))]
    for r in (state.get("nmr") or {}).get("raw") or []:      # TopSpin-Experimente, nach Art sortiert
        slots.append((r, "path", data_sub("nmr") + "/" + (r.get("kind") or "other")))
    mn = (state.get("nmr") or {}).get("mnova") or []          # Mnova-Dokumente
    slots += [(mn, i, data_sub("nmr") + "/mnova") for i in range(len(mn))]
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
    """Kopiert alle referenzierten Dateien in den Projektordner und schreibt project.elucida (alte project.uvvis
    danach als Sicherung nach .elucida/project.uvvis.old).
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
    tmp = pdir / (PROJECT_FILE + ".tmp")               # atomar: Abbruch beim Schreiben lässt die alte Datei stehen
    tmp.write_text(yaml.safe_dump(rel_state, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, pdir / PROJECT_FILE)
    for name in OLD_PROJECT_FILES:                     # alter Name: nicht zwei Projektdateien nebeneinander
        if (pdir / name).exists():
            os.replace(pdir / name, work_dir(pdir) / (name + ".old"))
    return abs_state


BRUKER_D_FILES = ("analysis.baf", "analysis.sqlite")      # aus einem .d-Ordner nur das, was gelesen wird
# Bruker-NMR-Experiment (TopSpin): ganzer Ordner (FID/ser, pdata …, Nutzerwunsch seit 2.1); gleich = diese Dateien
NMR_SAME_FILES = ("acqus", "acqu2s", "fid", "ser", "pulseprogram")


def _copy_dir(src: Path, dest_dir: Path, name=None) -> Path:
    """Messordner übernehmen: bei Bruker .d nur die gelesenen Dateien (Rohdaten + Index), NMR-Experimente ganz."""
    names = [n for n in BRUKER_D_FILES if (src / n).exists()] if src.suffix.lower() == ".d" else None
    same = names
    if names is None and (src / "acqus").is_file():
        same = [n for n in NMR_SAME_FILES if (src / n).exists()]
    base = Path(name or src.name)
    target, n = dest_dir / base.name, 2
    while target.exists():
        if same and all((target / x).exists() and (target / x).stat().st_size == (src / x).stat().st_size
                        and _digest(target / x) == _digest(src / x) for x in same):
            return target                              # derselbe Messordner ist schon da
        target = dest_dir / f"{base.stem}_{n}{base.suffix}"
        n += 1
    if names:
        target.mkdir(parents=True)
        for x in names:
            shutil.copy2(src / x, target / x)
    else:
        shutil.copytree(src, target)
    return target


def _copy_unique(src: Path, dest_dir: Path, name=None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        return _copy_dir(src, dest_dir, name)
    target = dest_dir / src.name
    n = 2
    while target.exists():
        if target.stat().st_size == src.stat().st_size and _digest(target) == _digest(src):
            return target                              # identische Datei bereits vorhanden
        target = dest_dir / f"{src.stem}_{n}{src.suffix}"
        n += 1
    shutil.copy2(src, target)
    return target


def import_group(project_dir, srcs, sub) -> list:
    """Zusammengehörige Dateien (gleicher Stamm, z. B. BES3T .dsc/.DTA/.YGF/.xml) unter einem gemeinsamen freien Stamm
    übernehmen – einzeln umbenannt passten Beschreibung und Daten sonst nicht mehr zusammen. -> Zielpfade."""
    pdir = Path(project_dir).resolve()
    srcs = [Path(s).resolve() for s in srcs]
    if all(pdir == s.parent or pdir in s.parents for s in srcs):
        return [str(s) for s in srcs]
    dest_dir = pdir / sub
    dest_dir.mkdir(parents=True, exist_ok=True)

    def same(q, s):
        return q.stat().st_size == s.stat().st_size and _digest(q) == _digest(s)
    base, stem, n = srcs[0].stem, srcs[0].stem, 2
    while True:
        # Groß-/Kleinschreibung egal (same.DSC neben same.dsc: der Leser nähme die falsche); frei nur, wenn jede
        # vorhandene Datei dieses Stamms gleich einer der neuen ist (keine fremden Partner wie alte .YGF)
        want = {(stem + s.suffix).lower(): s for s in srcs}
        have = {q.name.lower(): q for q in dest_dir.iterdir() if q.stem.lower() == stem.lower()}
        if all(k in want and same(q, want[k]) for k, q in have.items()):
            break
        stem, n = f"{base}_{n}", n + 1
    targets = []
    for s in srcs:
        t = have.get((stem + s.suffix).lower())
        if t is None:
            t = dest_dir / (stem + s.suffix)
            shutil.copy2(s, t)
        targets.append(t)
    return [str(t) for t in targets]


def load(project_dir) -> dict:
    """Projektdatei lesen (project.elucida oder alte project.uvvis), relative Pfade auf den Projektordner beziehen."""
    pdir = Path(project_dir).resolve()
    state = yaml.safe_load(project_file(pdir).read_text(encoding="utf-8")) or {}
    for cont, key, _ in _path_slots(state):
        v = _get(cont, key)
        if v and not Path(v).is_absolute():
            cont[key] = str((pdir / v).resolve())
    return state


def missing_files(state) -> list:
    return [_get(c, k) for c, k, _ in _path_slots(state) if _get(c, k) and not Path(_get(c, k)).exists()]


def import_file(project_dir, src, sub, name=None) -> str:
    """Datei ins Projekt übernehmen (Kopie nach data/ bzw. images/), falls sie nicht schon darin liegt.
    Bei CDXML werden gleichnamige ChemDraw-Exporte (SVG/PDF/PNG/TIFF) mitkopiert. name: Zielname eines Ordners
    (NMR-Experimente: <Datensatz>_<Nummer>, sonst hießen alle „10“, „11“ …)."""
    pdir = Path(project_dir).resolve()
    src = Path(src).resolve()
    if pdir == src.parent or pdir in src.parents:
        return str(src)
    dest_dir = pdir / sub
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = _copy_unique(src, dest_dir, name)
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
    if not is_project(pdir):
        save(pdir, {})
    return pdir


def backup(project_dir):
    """Sicherung vor dem Öffnen: .elucida/project.elucida.bak (bzw. project.uvvis.bak bei alten Projekten)."""
    pf = project_file(project_dir)
    try:
        ok = isinstance(yaml.safe_load(pf.read_text(encoding="utf-8")), dict)
    except (OSError, ValueError, yaml.YAMLError):
        ok = False
    if ok:                                             # leere/kaputte Datei nie über die letzte gute Sicherung
        shutil.copy2(pf, work_dir(project_dir) / (pf.name + ".bak"))


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


# -- Leere ChemDraw-Dateien je Verbindung (Nutzerwunsch: sofort in ChemDraw bearbeitbar, ohne erst eine anzulegen) ----
# Dokumenteinstellungen wie ChemDraw-Stil „ACS Document 1996“: Bindungslänge 14.4 pt, Abstand 18 %, Linie 0.6 pt,
# fett 2 pt, Rand 1.6 pt, Schraffur 2.5 pt, Kettenwinkel 120°, Arial 10 (Labels im Formelstil)
EMPTY_CDXML = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML CreationProgram="Elucida" BoundingBox="0 0 0 0" FractionalWidths="yes" InterpretChemically="yes"
 ShowAtomQuery="yes" ShowAtomStereo="no" ShowAtomEnhancedStereo="yes" ShowAtomNumber="no" ShowBondQuery="yes"
 ShowBondRxn="yes" ShowBondStereo="no" ShowTerminalCarbonLabels="no" ShowNonTerminalCarbonLabels="no"
 HideImplicitHydrogens="no" LabelFont="3" LabelSize="10" LabelFace="96" CaptionFont="3" CaptionSize="10"
 HashSpacing="2.50" MarginWidth="1.60" LineWidth="0.60" BoldWidth="2" BondLength="14.40" BondSpacing="18"
 ChainAngle="120" LabelJustification="Auto" CaptionJustification="Left" PrintMargins="36 36 36 36" color="0"
 bgcolor="1"><colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/></colortable><fonttable><font id="3"
 charset="iso-8859-1" name="Arial"/></fonttable><page id="1" BoundingBox="0 0 540 720" HeaderPosition="36"
 FooterPosition="36" HeightPages="1" WidthPages="1"/></CDXML>
"""


def template_paths(project_dir) -> tuple[Path, Path]:
    """(Struktur, Reaktionsschema) als CDXML in structures/, benannt nach dem Ordner der Verbindung."""
    pdir = Path(project_dir)
    d = pdir / STRUCTURES
    return d / f"{pdir.name}.cdxml", d / f"{pdir.name}_scheme.cdxml"


def ensure_templates(project_dir) -> tuple[Path, Path]:
    """Leere ChemDraw-Dateien anlegen, falls sie fehlen (vorhandene bleiben unangetastet)."""
    paths = template_paths(project_dir)
    for p in paths:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(EMPTY_CDXML, encoding="utf-8")
    return paths


def cdxml_has_content(path) -> bool:
    """Enthält die CDXML schon etwas (Atome, Texte, Pfeile)? Leere Vorlagen zählen nicht als Struktur."""
    try:
        txt = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(tag in txt for tag in ("<n ", "<n>", "<fragment", "<t ", "<arrow", "<graphic"))
