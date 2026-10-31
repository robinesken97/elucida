"""
elucida/app/publication.py - Publikation: übergeordneter Ordner mit den Verbindungsprojekten (seit 2.3).

<Publikation>/
    publication.elucida   Angaben (Titel, Autoren, DOI, Lizenz, Beschreibungen), Reihenfolge der Verbindungen und
                          Texte der Gesamt-SI (Materials and Methods, Einleitung je Kapitel) (YAML)
    1a/, 6m/ …            Verbindungsprojekte wie bisher (project.elucida), jedes für sich lauffähig
    SI/                   Gesamt-SI (Word)
    datapack/             Datenpakete: je Verbindung <Name>.zip, CompChem.zip, README.txt, Lizenz

Die Publikation ist nur eine Klammer: Verbindungen kennen sie nicht, Pfade im Index relativ (auch außerhalb erlaubt).
Unterordner mit Projekt, die (noch) nicht im Index stehen, werden beim Laden hinten angefügt. Name einer Verbindung =
Verbindung des Projekts („compound“), sonst der Ordnername. README.txt wie die Datensätze der Gruppe auf TUDOdata.
Ohne Qt.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

import yaml

from elucida.app import project as PRJ

PUB_FILE = "publication.elucida"
FORMAT_VERSION = 1
SI_DIR, PACK_DIR = "SI", "datapack"
# Angaben (Schlüssel, mehrzeilig) in der Reihenfolge des Dialogs
FIELDS = (("paper_title", False), ("title", False), ("authors", False), ("affiliation", True), ("contact", False), ("orcid", False),
          ("doi", False), ("related", True), ("project_description", True), ("dataset_description", True))
LICENSES = {   # Schlüssel -> (Name, URL, Datei in assets/licenses, Erklärung wie in den Datensätzen der Gruppe)
    "CC-BY-4.0": ("Creative Commons Attribution 4.0 International (CC-BY 4.0)",
                  "https://creativecommons.org/licenses/by/4.0/", "CC_BY_4.0_en.txt",
                  "This license requires that reusers give credit to the creator. It allows reusers to distribute, "
                  "remix, adapt, and build upon the material in any medium or format, even for commercial purposes."),
    "CC0-1.0": ("Creative Commons CC0 1.0 Universal (CC0 1.0)",
                "https://creativecommons.org/publicdomain/zero/1.0/", "CC0_1.0_en.txt",
                "The creator has waived all copyright and related rights to the extent possible under law. Reusers "
                "may copy, modify and distribute the material, even for commercial purposes, without asking "
                "permission."),
}
# Datenarten im Paket (Gruppen aus exchange/datapack) -> Satzteil der Datensatzbeschreibung und Programme
KIND_TEXT = {"nmr": "NMR spectra (NMR)", "ir": "IR spectra (IR)", "ms": "mass spectra (MS)",
             "uvvis": "UV-Vis data (UV-Vis)", "overlay": "UV-Vis data (UV-Vis)",
             "fluo": "fluorescence data (Fluorescence)", "cv": "cyclic voltammograms (CV)",
             "sec": "spectroelectrochemical data (SEC)", "epr": "EPR data (EPR)", "dft": "DFT output files (CompChem)"}
KIND_PROGRAMS = {"nmr": "NMR -> TopSpin, MestReNova", "ir": "IR -> Spectragryph, Bruker OPUS",
                 "ms": "MS -> Bruker DataAnalysis, OpenMS", "cv": "CV -> Gamry Echem Analyst",
                 "epr": "EPR -> Bruker Xenon, EasySpin", "dft": "DFT -> ORCA, Avogadro, Chemcraft"}


def default() -> dict:
    d = {k: "" for k, _ in FIELDS}
    d.update(format=FORMAT_VERSION, license="CC-BY-4.0", compounds=[], excluded=[], si_texts={}, groups=[], group_of={},
             procedures=[], group_headings=True, mnova=[])
    return d


def is_publication(path) -> Path | None:
    """Publikationsordner oder publication.elucida -> Ordner, sonst None."""
    p = Path(path)
    if p.is_file() and p.name == PUB_FILE:
        return p.parent
    if p.is_dir() and (p / PUB_FILE).exists():
        return p
    return None


def load(pdir) -> dict:
    data = default()
    f = Path(pdir) / PUB_FILE
    if f.exists():
        raw = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict):
            data.update({k: v for k, v in raw.items() if v is not None})
    data["compounds"] = [str(c) for c in data.get("compounds") or []]
    data["excluded"] = [str(c) for c in data.get("excluded") or []]
    data["si_texts"] = {str(k): str(v) for k, v in (data.get("si_texts") or {}).items() if v}
    data["groups"] = [str(g) for g in data.get("groups") or [] if str(g).strip()]       # Reihenfolge der Gruppen
    data["group_of"] = {str(k): str(v) for k, v in (data.get("group_of") or {}).items()  # Eintrag -> Gruppe
                        if str(v) in data["groups"]}
    # Allgemeine Vorschriften (GP A …): Kürzel, Titel, Text; je Verbindung im Synthese-Tab gewählt (syn.gp)
    data["procedures"] = [{k: str(p.get(k) or "").strip() for k in ("key", "title", "text")}
                          for p in data.get("procedures") or [] if isinstance(p, dict) and str(p.get("key") or "").strip()]
    data["group_headings"] = data.get("group_headings") is not False
    data["mnova"] = [str(m) for m in data.get("mnova") or []]          # Mnova-Dokumente des Projekts (FB-10)
    return data


def save(pdir, data):
    pdir = Path(pdir)
    pdir.mkdir(parents=True, exist_ok=True)
    out = {"format": FORMAT_VERSION}
    out.update({k: data.get(k, "") for k, _ in FIELDS})
    out["license"] = data.get("license") or "CC-BY-4.0"
    out["compounds"] = list(data.get("compounds") or [])
    if data.get("excluded"):
        out["excluded"] = list(data["excluded"])
    if data.get("groups"):                 # Gruppen im Projekt (Precursor, Salze …), Zuordnung je Eintrag
        out["groups"] = list(data["groups"])
        gof = {k: v for k, v in (data.get("group_of") or {}).items() if k in out["compounds"] and v in out["groups"]}
        if gof:
            out["group_of"] = gof
    if data.get("procedures"):
        out["procedures"] = [dict(p) for p in data["procedures"]]
    if data.get("group_headings") is False:   # Gruppen nur zur Orientierung, keine Unterkapitel in der Gesamt-SI
        out["group_headings"] = False
    if data.get("mnova"):                  # Mnova-Dokumente für alle Spektren des Papers (relativ, „mnova/…“)
        out["mnova"] = list(data["mnova"])
    texts = {k: v for k, v in (data.get("si_texts") or {}).items() if str(v).strip()}
    if texts:                              # Gesamt-SI: Materials and Methods, Einleitung je Kapitel
        out["si_texts"] = texts
    tmp = pdir / (PUB_FILE + ".tmp")
    tmp.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(pdir / PUB_FILE)


def create(pdir, title="") -> Path:
    """Neuen Publikationsordner anlegen (oder vorhandenen Ordner dazu machen); vorhandene Projekte darin übernehmen."""
    pdir = Path(pdir)
    if PRJ.is_project(pdir):
        raise ValueError(f"{pdir} is a compound project")
    data = load(pdir) if is_publication(pdir) else default()
    if title and not data.get("title"):
        data["title"] = title
    save(pdir, data)
    sync(pdir)
    return pdir


def natural_key(s: str):
    """1a < 2b < 10a; Buchstaben vor Zahlen getrennt (S10 nach S9)."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def _rel(pdir: Path, cdir: Path) -> str:
    try:
        return Path(os.path.relpath(Path(cdir).resolve(), Path(pdir).resolve())).as_posix()
    except ValueError:                                     # anderes Laufwerk (Windows): absolut
        return str(Path(cdir).resolve())


def _abs(pdir: Path, entry: str) -> Path:
    p = Path(entry)
    return p if p.is_absolute() else (Path(pdir) / p).resolve()


def sync(pdir) -> tuple[list[Path], list[str]]:
    """Verbindungen der Publikation -> (Projektordner in Reihenfolge, fehlende Einträge). Neue Projekt-Unterordner
    hinten anfügen (natürlich sortiert) und den Index dann speichern; fehlende Einträge bleiben im Index."""
    pdir = Path(pdir)
    data = load(pdir)
    dirs, missing = [], []
    for c in data["compounds"]:
        p = _abs(pdir, c)
        (dirs if PRJ.is_project(p) else missing).append(p if PRJ.is_project(p) else c)
    known = {d.resolve() for d in dirs}
    excluded = {_abs(pdir, c) for c in data["excluded"]}
    new = sorted((d for d in pdir.iterdir() if d.is_dir() and not d.name.startswith(".") and PRJ.is_project(d)
                  and d.resolve() not in known and d.resolve() not in excluded), key=lambda d: natural_key(d.name)) if pdir.is_dir() else []
    if new:
        data["compounds"] += [_rel(pdir, d) for d in new]
        save(pdir, data)
        dirs += new
    if data["groups"]:                     # Reihenfolge: Gruppen nacheinander, ohne Gruppe am Ende
        rank = {g: i for i, g in enumerate(data["groups"])}
        entry = {_abs(pdir, c): c for c in data["compounds"]}
        pos = {d: i for i, d in enumerate(dirs)}
        dirs.sort(key=lambda d: (rank.get(data["group_of"].get(entry.get(d.resolve(), entry.get(d, ""))),
                                           len(rank)), pos[d]))
    return dirs, missing


def add_compound(pdir, cdir):
    data = load(pdir)
    rel = _rel(Path(pdir), Path(cdir))
    data["excluded"] = [c for c in data["excluded"] if c != rel]
    if rel not in data["compounds"]:
        data["compounds"].append(rel)
    save(pdir, data)


def remove_compound(pdir, cdir):
    """Aus dem Index nehmen (Ordner bleibt). Unterordner der Publikation als ausgeschlossen vermerken, sonst kämen
    sie beim nächsten sync zurück."""
    data = load(pdir)
    target = Path(cdir).resolve()
    for c in [c for c in data["compounds"] if _abs(Path(pdir), c) == target]:
        data["group_of"].pop(c, None)
    data["compounds"] = [c for c in data["compounds"] if _abs(Path(pdir), c) != target]
    rel = _rel(Path(pdir), target)
    if target.parent == Path(pdir).resolve() and rel not in data["excluded"]:
        data["excluded"].append(rel)
    save(pdir, data)


def move_compound(pdir, cdir, delta):
    """Verbindung in der Reihenfolge um delta verschieben."""
    data = load(pdir)
    target = Path(cdir).resolve()
    idx = next((i for i, c in enumerate(data["compounds"]) if _abs(Path(pdir), c) == target), None)
    if idx is None:
        return
    j = max(0, min(len(data["compounds"]) - 1, idx + delta))
    data["compounds"].insert(j, data["compounds"].pop(idx))
    save(pdir, data)


def publication_of(project_dir) -> Path | None:
    """Publikation, zu der ein Verbindungsprojekt gehört: übergeordneter Ordner mit publication.elucida, der es
    aufführt (oder es beim nächsten sync aufnehmen würde)."""
    if not project_dir:
        return None
    cdir = Path(project_dir).resolve()
    pdir = cdir.parent
    if not is_publication(pdir):
        return None
    data = load(pdir)
    if any(_abs(pdir, c) == cdir for c in data["compounds"]):
        return pdir
    return None if _rel(pdir, cdir) in (data.get("excluded") or []) else pdir


def compound_name(cdir) -> str:
    """Name der Verbindung (wie im Projekt eingetragen), sonst Ordnername – Zip-/Abschnittsname."""
    try:
        st = yaml.safe_load(PRJ.project_file(cdir).read_text(encoding="utf-8")) or {}
        name = ((st.get("compound") or {}).get("name") or (st.get("syn") or {}).get("name") or "").strip()
    except Exception:
        name = ""
    return name or Path(cdir).name


# -- README.txt (Aufbau wie die Datensätze der Gruppe auf TUDOdata) ---------------------------------------------
def dataset_description(kinds, compounds) -> str:
    """Standardbeschreibung aus den Datenarten im Paket."""
    seen, parts = set(), []
    for k in KIND_TEXT:
        if k in kinds and KIND_TEXT[k] not in seen:
            seen.add(KIND_TEXT[k])
            parts.append(KIND_TEXT[k])
    txt = "The dataset contains " + (", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else
                                     (parts[0] if parts else "raw data")) + ". "
    txt += ("The data is structured according to the compounds of the related publication (one archive per "
            "compound: " + ", ".join(compounds) + ")" if compounds else "The data is structured by compound")
    txt += "; computational data for all compounds is collected in CompChem.zip. " if "dft" in kinds else ". "
    progs = [KIND_PROGRAMS[k] for k in KIND_PROGRAMS if k in kinds]
    if progs:
        txt += "The files can be opened with standard programs (e.g. " + "; ".join(progs) + ")."
    return txt.strip()


def paper_title(data) -> str:
    """Titel des Artikels (Titelblatt der Gesamt-SI); kursive Teile als <i>…</i>."""
    return str(data.get("paper_title") or "").strip() or str(data.get("title") or "").strip().removeprefix(
        "Electronic supplement to ").strip()


def dataset_title(data) -> str:
    """Titel des Datensatzes wie auf TUDOdata: eigener Titel, sonst „Electronic supplement to <Artikel>“."""
    t = str(data.get("title") or "").strip()
    if t:
        return t
    pt = re.sub(r"<[^>]+>", "", paper_title(data))
    return f"Electronic supplement to {pt}" if pt else ""


# Hinweis im README, wenn der Inhalt bereinigt wurde (Nutzerwunsch P8 R2: transparent, aber ohne Projektverlauf)
SCRUB_NOTE = ("For privacy, calendar dates in the raw files were replaced by 1 January 1980 in their original format "
              "(times of day unchanged), and user and account names by \"user\". All measured values are unchanged.")


def readme_text(data, kinds=(), compounds=(), scrubbed=False) -> str:
    """README.txt: TITLE, AUTHORS (+ Adresse), CONTACT, ORCID, DOI, CITATION, RELATED PUBLICATION, PROJECT
    DESCRIPTION, DATASET DESCRIPTION, LICENSE – leere Angaben fallen weg. scrubbed: Inhalt bereinigt (Hinweis)."""
    g = lambda k: str(data.get(k) or "").strip()            # noqa: E731
    out = []

    def sec(head, body):
        if body:
            out.append(f"{head}:\n{body}\n")
    title = dataset_title(data)
    sec("TITLE", title)
    sec("AUTHORS", g("authors") + ("\n\n" + g("affiliation") if g("affiliation") else ""))
    sec("CONTACT", g("contact"))
    sec("ORCID", g("orcid"))
    doi = g("doi")
    if doi and not doi.startswith("http"):
        doi = "https://doi.org/" + doi.removeprefix("doi:")
    sec("DOI", doi)
    if g("authors") and title:
        first = g("authors").split(",")[0].strip()
        sec("CITATION", f"{first} et al., \"{title}\"" + (f", {doi}" if doi else ""))
    sec("RELATED PUBLICATION", g("related"))
    sec("PROJECT DESCRIPTION", g("project_description"))
    sec("DATASET DESCRIPTION", (g("dataset_description") or dataset_description(kinds, compounds))
        + ("\n\n" + SCRUB_NOTE if scrubbed else ""))
    lic = LICENSES.get(data.get("license") or "CC-BY-4.0", LICENSES["CC-BY-4.0"])
    sec("LICENSE", f"This work is licensed under {lic[0]}. To view a copy of this license, visit {lic[1]}\n\n{lic[3]}")
    return "\n".join(out)


def license_file(data, assets_dir) -> tuple[str, Path] | None:
    """(Name im Datensatz, Quelldatei) des Lizenztexts, z. B. LICENSE-CC_BY_4.0_en.txt."""
    lic = LICENSES.get(data.get("license") or "CC-BY-4.0")
    if lic is None:
        return None
    src = Path(assets_dir) / "licenses" / lic[2]
    return ("LICENSE-" + lic[2], src) if src.exists() else None


# -- Checkliste je Verbindung (Seite der Publikation) -----------------------------------------------------------
# (Schlüssel, Anzeige); Pflicht je nach „literaturbekannt“ (Nutzerwunsch: dann nur ¹H/¹³C), Rest optional
CHECKS = (("1H", "¹H NMR"), ("13C", "¹³C NMR"), ("2D", "2D NMR"), ("ms", "HRMS"), ("ir", "IR"), ("mp", "m.p."),
          ("ea", "EA"), ("uvvis", "UV-Vis"), ("xray", "X-Ray"))
REQUIRED_KNOWN = ("1H", "13C")
REQUIRED_NEW = ("1H", "13C", "2D", "ms", "ir", "mp")
NMR_2D = ("COSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "TOCSY", "HOESY", "INADEQUATE", "2D")


def checklist(cdir) -> dict:
    """Was liegt für eine Verbindung vor (aus der Projektdatei, ohne sie zu öffnen)? -> known, lit, have (Menge der
    CHECKS-Schlüssel), missing (fehlende Pflichtteile in CHECKS-Reihenfolge), extra (vorhandene optionale Teile)."""
    try:
        st = yaml.safe_load(PRJ.project_file(cdir).read_text(encoding="utf-8")) or {}
    except Exception:
        st = {}
    g = lambda k: st.get(k) or {}                          # noqa: E731
    comp, nmr, ir, hr = g("compound"), g("nmr"), g("irms"), g("hrms")
    nuclei, two_d = set(), False
    for sp in nmr.get("spectra") or []:
        if (sp.get("kind") or "1D") != "1D":
            two_d = True
        elif sp.get("nuclei"):
            nuclei.add(sp["nuclei"][0])
    for r in nmr.get("raw") or []:
        k = r.get("kind") or ""
        two_d |= k in NMR_2D
        if k in ("1H", "13C"):
            nuclei.add(k)
    txt = nmr.get("text") or ""                            # NMR-Zeilen aus dem Mnova-Bericht
    for nuc in ("1H", "13C"):
        if re.search(rf"(?<!\d){nuc[:-1]}\s*{nuc[-1]}\s*NMR|{'¹H' if nuc == '1H' else '¹³C'}\s*NMR", txt):
            nuclei.add(nuc)
    have = {k for k, ok in (("1H", "1H" in nuclei), ("13C", "13C" in nuclei), ("2D", two_d),
                            ("ms", bool(hr.get("ms_file") or hr.get("ms_raw") or ir.get("ms_file") or ir.get("ms_raw"))),
                            ("ir", bool(ir.get("ir_file") or ir.get("ir_pdf"))), ("mp", bool(comp.get("mp") or comp.get("oil"))),
                            ("ea", bool(ir.get("ea_found"))), ("uvvis", bool(g("eps").get("files"))),
                            ("xray", bool(g("xray").get("entries")))) if ok}
    known = bool(comp.get("known"))
    req = REQUIRED_KNOWN if known else REQUIRED_NEW
    return dict(known=known, lit=comp.get("lit") or "", have=have, sample=bool(comp.get("sample")),
                missing=[k for k, _ in CHECKS if k in req and k not in have],
                extra=[k for k, _ in CHECKS if k not in req and k in have])


def check_label(key) -> str:
    return dict(CHECKS)[key]


# -- Verbindungen zwischen Projekten verschieben/kopieren (Zugehörigkeit = Ordner im Projekt) --------------------
def rename_gp_in(syn, mapping) -> bool:
    """Synthese-Zustand einer Verbindung an umbenannte GP-Kürzel anpassen (gleichzeitig, Tausch A <-> B):
    Zuordnung `gp` und jedes „GP A“ im Vorschrifttext. -> geändert?"""
    mapping = {o: n for o, n in (mapping or {}).items() if o and n and o != n}
    if not mapping or not isinstance(syn, dict):
        return False
    changed = False
    if syn.get("gp") in mapping:
        syn["gp"] = mapping[syn["gp"]]
        changed = True
    pat = re.compile(r"\bGP (" + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True))) + r")\b")
    txt = syn.get("proc") or ""
    new = pat.sub(lambda m: "GP " + mapping[m.group(1)], txt)
    if new != txt:
        syn["proc"] = new
        changed = True
    return changed


def rename_procedures(pdir, mapping, skip=None) -> list[Path]:
    """Umbenannte GP-Kürzel in allen (geschlossenen) Verbindungen des Projekts nachziehen; skip = offene Verbindung
    (folgt über ihren Zustand). Projektdatei atomar. -> geänderte Ordner."""
    out = []
    for cdir in sync(pdir)[0] if mapping else []:
        if skip and Path(cdir).resolve() == Path(skip).resolve():
            continue
        pf = PRJ.project_file(cdir)
        try:
            st = yaml.safe_load(pf.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if rename_gp_in(st.get("syn"), mapping):
            tmp = pf.with_name(pf.name + ".tmp")
            tmp.write_text(yaml.safe_dump(st, allow_unicode=True, sort_keys=False), encoding="utf-8")
            os.replace(tmp, pf)
            out.append(Path(cdir))
    return out


MNOVA_DIR = "mnova"


def add_mnova(pdir, src) -> Path:
    """Mnova-Dokument im Projekt ablegen (Kopie nach <Projekt>/mnova/, Original bleibt) und im Index vermerken."""
    pdir, src = Path(pdir), Path(src)
    try:
        inside = src.resolve().is_relative_to(pdir.resolve())
    except OSError:
        inside = False
    if inside:
        dst = src
    else:
        dst = pdir / MNOVA_DIR / src.name
        k = 2
        while dst.exists() and dst.read_bytes() != src.read_bytes():   # anderes Dokument gleichen Namens: nie überschreiben
            dst = pdir / MNOVA_DIR / f"{src.stem}_{k}{src.suffix}"
            k += 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
    data = load(pdir)
    rel = dst.resolve().relative_to(pdir.resolve()).as_posix()
    if rel not in data["mnova"]:
        data["mnova"].append(rel)
        save(pdir, data)
    return dst


def mnova_files(pdir) -> list[Path]:
    return [Path(pdir) / m for m in load(pdir)["mnova"] if (Path(pdir) / m).exists()]


def unique_dest(pdir, name) -> Path:
    """Freier Zielordner <pdir>/<name>, sonst <name>_2, <name>_3 …"""
    d = Path(pdir) / name
    k = 2
    while d.exists():
        d = Path(pdir) / f"{name}_{k}"
        k += 1
    return d


def _drop_from_index(cdir):
    """Verbindung aus dem Index ihres bisherigen Projekts nehmen (falls es eins gibt)."""
    src = publication_of(cdir)
    if src is None:
        return
    data = load(src)
    target = Path(cdir).resolve()
    for c in [c for c in data["compounds"] if _abs(src, c) == target]:
        data["group_of"].pop(c, None)
    data["compounds"] = [c for c in data["compounds"] if _abs(src, c) != target]
    save(src, data)


def move_compound_to(cdir, target_pub) -> Path:
    """Verbindungsordner in ein anderes Projekt verschieben (Index beider Projekte nachgeführt). -> neuer Ordner."""
    import shutil
    cdir, target_pub = Path(cdir).resolve(), Path(target_pub).resolve()
    if cdir.parent == target_pub:
        return cdir
    dest = unique_dest(target_pub, cdir.name)
    shutil.move(str(cdir), str(dest))
    _drop_from_index(cdir)                             # erst nach dem Verschieben (scheitert es, bleibt der Index)
    add_compound(target_pub, dest)
    return dest


def copy_compound_to(cdir, target_pub) -> Path:
    """Verbindung in ein (anderes) Projekt kopieren – z. B. dieselbe Verbindung in zwei Papern; danach unabhängig.
    Sicherungen/Zwischenbilder (.elucida) bleiben weg, sie entstehen neu. -> neuer Ordner."""
    import shutil
    cdir, target_pub = Path(cdir).resolve(), Path(target_pub).resolve()
    dest = unique_dest(target_pub, cdir.name)
    shutil.copytree(cdir, dest, ignore=shutil.ignore_patterns(PRJ.WORK))
    add_compound(target_pub, dest)
    return dest


def place_compound(pdir, cdir, index):
    """Verbindung an Position index der Reihenfolge setzen (Ziehen mit der Maus auf der Projektseite)."""
    data = load(pdir)
    target = Path(cdir).resolve()
    items = data["compounds"]
    k = next((i for i, c in enumerate(items) if _abs(Path(pdir), c) == target), None)
    if k is None:
        return
    entry = items.pop(k)
    items.insert(max(0, min(len(items), index - (1 if index > k else 0))), entry)
    save(pdir, data)


def sort_by_name(pdir):
    """Reihenfolge nach dem Namen der Verbindung, natürlich sortiert (1a, 1b, 2a … 10a, S1, S2)."""
    data = load(pdir)
    data["compounds"].sort(key=lambda c: natural_key(compound_name(_abs(Path(pdir), c))))
    save(pdir, data)



# -- Gruppen im Projekt (frei benannt, z. B. „Precursor“, „Salze“, „NHOs“) ----------------------------------------
def _entry(pdir, data, cdir):
    target = Path(cdir).resolve()
    return next((c for c in data["compounds"] if _abs(Path(pdir), c) == target), None)


def group_name(pdir, cdir, data=None):
    """Gruppe einer Verbindung im Projekt, sonst None."""
    data = data or load(pdir)
    e = _entry(pdir, data, cdir)
    return data["group_of"].get(e) if e else None


def grouped(pdir):
    """-> [(Gruppe oder None, [Ordner])] in der Reihenfolge des Projekts; leere Gruppen mit []; ohne Gruppe am Ende
    (nur, wenn es solche Verbindungen gibt oder gar keine Gruppen)."""
    data = load(pdir)
    dirs, _ = sync(pdir)
    data = load(pdir)
    out = [(g, []) for g in data["groups"]]
    idx = {g: i for i, g in enumerate(data["groups"])}
    rest = []
    for d in dirs:
        g = group_name(pdir, d, data)
        (out[idx[g]][1] if g in idx else rest).append(d)
    if rest or not out:
        out.append((None, rest))
    return out


def add_group(pdir, name) -> str:
    name = str(name).strip()
    data = load(pdir)
    if name and name not in data["groups"]:
        data["groups"].append(name)
        save(pdir, data)
    return name


def set_group(pdir, cdir, name):
    """Verbindung einer Gruppe zuordnen (neu angelegt, wenn nötig); None/"" = ohne Gruppe."""
    data = load(pdir)
    e = _entry(pdir, data, cdir)
    if e is None:
        return
    name = str(name or "").strip()
    if name:
        if name not in data["groups"]:
            data["groups"].append(name)
        data["group_of"][e] = name
    else:
        data["group_of"].pop(e, None)
    save(pdir, data)


def rename_group(pdir, old, new):
    data = load(pdir)
    new = str(new).strip()
    if not new or old not in data["groups"] or (new != old and new in data["groups"]):
        return False
    data["groups"] = [new if g == old else g for g in data["groups"]]
    data["group_of"] = {k: (new if v == old else v) for k, v in data["group_of"].items()}
    save(pdir, data)
    return True


def delete_group(pdir, name):
    """Gruppe auflösen: die Verbindungen bleiben, nur ohne Gruppe."""
    data = load(pdir)
    data["groups"] = [g for g in data["groups"] if g != name]
    data["group_of"] = {k: v for k, v in data["group_of"].items() if v != name}
    save(pdir, data)


def move_group(pdir, name, delta):
    data = load(pdir)
    if name not in data["groups"]:
        return
    i = data["groups"].index(name)
    j = max(0, min(len(data["groups"]) - 1, i + delta))
    data["groups"].insert(j, data["groups"].pop(i))
    save(pdir, data)
