"""
elucida/exchange/datapack.py - Datenpaket je Verbindung (Zip) für Repositorien wie TUDOdata.

Aufbau wie die veröffentlichten Datensätze der Gruppe (je Verbindung ein Zip <Name>.zip mit Ordner <Name>/):
    NMR/1H/10/, NMR/13C/11/, NMR/HSQC + HMBC/12/ …   TopSpin-Experimente vollständig, Ordner = Experimentnummer
    NMR/<Datei>.mnova                               Mnova-Dokumente
    IR/        OPUS-Datei und -PDF
    MS/        Bericht der Massenabteilung, Bruker-.d
    UV-Vis/    Messdateien des ε-Tabs
    Fluorescence/, CV/<Lösungsmittel>/, SEC/, EPR/ (BES3T-Partnerdateien mit)
    DFT/, Elucida/ (Abbildungen, SI)           wählbar, Standard aus
X-Ray (CCDC) und Synthese gehören nicht hinein. Nur Dateien, auf die der Projektzustand zeigt (nichts Internes).

Laborkürzel (z. B. „RE-3-150“) werden ersetzt: in Datei- und Ordnernamen immer, im Inhalt aller Textdateien wahlweise
(Nutzerwunsch: auch TopSpin-Parameter, title, audita.txt – Mnova zeigt sonst den Messnamen). Text = keine Nullbytes;
Binärdateien (fid/ser/1r, OPUS, PDF, .mnova) bleiben bytegleich, wo dort ein Kürzel steckt, nennt der Bericht die Datei.
Ohne Qt (Dialog: elucida/app/datapack_dialog.py).
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Laborkürzel „Initialen-Buch-Seite“, z. B. RE-3-150, RE-12-7a
CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,4}-\d{1,3}-\d{1,4}[a-z]?)(?![A-Za-z0-9])")
TEXT_MAX = 50_000_000            # größere Dateien nie als Text behandeln
BINARY_EXT = {".pdf", ".0", ".1", ".2", ".mnova", ".docx", ".xlsx", ".png", ".jpg", ".emf", ".baf", ".sqlite", ".gbw",
              ".zip"}
# Reihenfolge und Ordner im Zip; on = Standardauswahl
GROUPS = (("nmr", "NMR", True), ("ir", "IR", True), ("ms", "MS", True), ("uvvis", "UV-Vis", True),
          ("overlay", "UV-Vis", False), ("fluo", "Fluorescence", True), ("cv", "CV", True), ("sec", "SEC", True),
          ("epr", "EPR", True), ("dft", "DFT", False), ("elucida", "Elucida", False))
GROUP_ON = {g: on for g, _, on in GROUPS}
BES3T = (".dsc", ".dta", ".ygf", ".xml")


@dataclass
class Item:
    group: str                 # Schlüssel aus GROUPS
    src: Path                  # Datei oder Ordner (TopSpin, Bruker .d)
    arc: str                   # Pfad im Zip unterhalb von <Name>/ (Kürzel noch nicht ersetzt)
    on: bool = True
    size: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def key(self):
        return f"{self.group}|{self.arc}"


def _size(p: Path) -> int:
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return p.stat().st_size if p.exists() else 0


def _two_d_folder(kinds):
    """Ordner für die 2D-Experimente wie in den Datensätzen der Gruppe: „HSQC + HMBC“ (vorhandene Arten)."""
    order = ("COSY", "TOCSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "HOESY", "INADEQUATE", "2D")
    ks = sorted(set(kinds), key=lambda k: order.index(k) if k in order else 99)
    return " + ".join(ks) if ks else "2D"


def collect(state, project_dir) -> list[Item]:
    """Alle Dateien eines Projekts, die in ein Datenpaket gehören können, mit Ziel im Zip und Standardauswahl."""
    from elucida.tabs.nmr import KINDS_2D
    pdir = Path(project_dir).resolve() if project_dir else None
    items, seen = [], set()

    def add(group, src, arc, **extra):
        if not src:
            return
        p = Path(src)
        if not p.is_absolute() and pdir is not None:
            p = pdir / p
        if not p.exists() or str(p.resolve()) in seen:
            return
        seen.add(str(p.resolve()))
        items.append(Item(group, p, arc, GROUP_ON[group], _size(p), extra))

    nmr = state.get("nmr") or {}
    raws = [r for r in nmr.get("raw") or [] if r.get("path")]
    two_d = _two_d_folder([r["kind"] for r in raws if r.get("kind") in KINDS_2D])
    used = {}
    for r in raws:
        kind = r.get("kind") or "other"
        folder = two_d if kind in KINDS_2D else kind
        name = Path(r["path"]).name
        no = name.rsplit("_", 1)[1] if "_" in name and name.rsplit("_", 1)[1].isdigit() else name
        if (folder, no) in used:                       # gleiche Nummer aus zwei Datensätzen: vollen Namen behalten
            no = name
        used[(folder, no)] = True
        add("nmr", r["path"], f"NMR/{folder}/{no}")
    for m in nmr.get("mnova") or []:
        add("nmr", m, f"NMR/{Path(m).name}")
    for s in nmr.get("spectra") or []:                 # Mnova-Exporte (Abbildungen): wählbar, Standard aus
        add("nmr", s.get("file"), f"NMR/Spectra/{Path(s.get('file') or '').name}", )
        if items and items[-1].arc.startswith("NMR/Spectra/"):
            items[-1].on = False

    ir = state.get("irms") or {}
    for k in ("ir_file", "ir_pdf"):
        add("ir", ir.get(k), f"IR/{Path(ir.get(k) or '').name}")
    hr = state.get("hrms") or {}
    for d in (hr, ir):                                 # alte Projekte: MS im Tab IR + MS
        for k in ("ms_file", "ms_raw"):
            add("ms", d.get(k), f"MS/{Path(d.get(k) or '').name}")

    for f in (state.get("eps") or {}).get("files") or []:
        add("uvvis", f, f"UV-Vis/{Path(f).name}")
    for e in (state.get("overlay") or {}).get("entries") or []:   # Vergleichsspektren, ggf. anderer Verbindungen
        for f in [e.get("file")] + list(e.get("files") or []) + [x.get("file") for x in e.get("sources") or []]:
            if f:
                tddft = Path(f).suffix.lower() in (".out", ".log")
                add("dft" if tddft else "overlay", f, f"{'DFT' if tddft else 'UV-Vis'}/{Path(f).name}")

    fl = state.get("fluo") or {}
    for k in ("abs_file", "em_file"):
        add("fluo", fl.get(k), f"Fluorescence/{Path(fl.get(k) or '').name}")

    for e in (state.get("cv") or {}).get("files") or []:
        grp = re.sub(r'[\\/:*?"<>|]', "_", (e.get("group") or "").strip())
        add("cv", e.get("file"), "CV/" + (grp + "/" if grp else "") + Path(e.get("file") or "").name)

    sec = state.get("sec") or {}
    add("sec", sec.get("dta"), f"SEC/{Path(sec.get('dta') or '').name}")
    for f in sec.get("spec_files") or []:
        add("sec", f, f"SEC/{Path(f).name}")

    for e in (state.get("epr") or {}).get("entries") or []:
        for f in (e.get("file"), e.get("params")):
            if not f:
                continue
            add("epr", f, f"EPR/{Path(f).name}")
            p = Path(f)
            if p.suffix.lower() in BES3T:              # Bruker BES3T: Partnerdateien mit
                for sib in p.parent.glob(p.stem + ".*"):
                    if sib.suffix.lower() in BES3T:
                        add("epr", sib, f"EPR/{sib.name}")

    for e in (state.get("dft") or {}).get("entries") or []:
        for f in [e.get("file"), e.get("molden")] + [o.get("file") for o in e.get("orbitals") or []]:
            if f:
                add("dft", f, f"DFT/{Path(f).name}")
                xyz = Path(f).with_suffix(".xyz")
                if Path(f).suffix.lower() in (".out", ".log") and xyz.exists():
                    add("dft", xyz, f"DFT/{xyz.name}")

    if pdir is not None:                               # Ergebnisse von Elucida (Exporte)
        from elucida.app import project as PRJ
        for sub in (PRJ.SI_DIR, PRJ.FIGURES, PRJ.TABLES):
            d = pdir / sub
            if d.is_dir():
                for f in sorted(d.rglob("*")):
                    if f.is_file():
                        add("elucida", f, f"Elucida/{f.relative_to(pdir).as_posix()}")
    return items


def find_codes(items, read_text=True, limit=2_000_000) -> list[str]:
    """Laborkürzel in Namen (und im Inhalt kleiner Textdateien) aller Einträge, sortiert."""
    found = set()
    for it in items:
        found |= set(CODE_RE.findall(it.arc)) | set(CODE_RE.findall(it.src.name))   # Ordner im Projekt: RE-3-150_10
        files = [it.src] if it.src.is_file() else [f for f in it.src.rglob("*") if f.is_file()]
        for f in files:
            found |= set(CODE_RE.findall(f.name))
            if read_text and f.stat().st_size <= limit and _is_text(f):
                found |= set(CODE_RE.findall(f.read_bytes().decode("latin-1")))
    return sorted(found)


def _is_text(f: Path, head: bytes | None = None) -> bool:
    """Textdatei (Inhalt ersetzbar): bekannte Binärformate nie, sonst keine Nullbytes in den ersten 64 kB."""
    if f.suffix.lower() in BINARY_EXT or f.stat().st_size > TEXT_MAX:
        return False
    if head is None:
        with open(f, "rb") as fh:
            head = fh.read(65536)
    return b"\0" not in head[:65536]


def replace_codes(s: str, repl: dict) -> str:
    """Kürzel im Text ersetzen (längste zuerst, nur ganze Kürzel)."""
    for code in sorted(repl, key=len, reverse=True):
        if repl[code] is not None:
            s = re.sub(rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])", repl[code], s)
    return s


def _safe_name(s: str) -> str:
    return re.sub(r'[\\:*?"<>|]', "_", s).strip() or "_"


def _decode(data: bytes):
    """Text -> (str, Kodierung) so, dass er beim Zurückschreiben bytegleich bleibt (UTF-8, sonst Latin-1)."""
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def write_zip(items, path, root, name_repl=None, text_repl=None, progress=None) -> dict:
    """Ausgewählte Einträge als <path> schreiben (Ordner <root>/ darin). name_repl/text_repl: Kürzel -> Ersatz in
    Namen bzw. im Inhalt von Textdateien (None = Inhalt nicht ändern). -> Bericht: Dateien, Größe, ersetzte
    Textdateien, Dateien, in denen ein Kürzel unverändert bleibt (binär oder TopSpin-Parameter)."""
    name_repl, codes = name_repl or {}, set(name_repl or {}) | set(text_repl or {})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    files = []
    for it in (i for i in items if i.on):
        base = "/".join(_safe_name(replace_codes(p, name_repl)) for p in it.arc.split("/"))
        if it.src.is_dir():
            for f in sorted(it.src.rglob("*")):
                if f.is_file():
                    rel = "/".join(_safe_name(replace_codes(p, name_repl)) for p in f.relative_to(it.src).parts)
                    files.append((f, f"{base}/{rel}", it.group))
        else:
            files.append((it.src, base, it.group))
    report = dict(files=0, bytes=0, text_replaced=[], kept=[])
    root = _safe_name(replace_codes(root, name_repl))
    seen = set()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n, (f, arc, group) in enumerate(files):
            arc = f"{root}/{arc}"
            k = 2
            while arc in seen:                          # gleicher Name nach dem Ersetzen: nummerieren
                stem, dot, ext = arc.rpartition(".")
                arc = f"{stem}_{k}.{ext}" if dot else f"{arc}_{k}"
                k += 1
            seen.add(arc)
            data = f.read_bytes()
            if codes and text_repl is not None and _is_text(f, data[:65536]):
                txt, enc = _decode(data)
                new = replace_codes(txt, text_repl)
                if new != txt:
                    data = new.encode(enc, errors="replace")
                    report["text_replaced"].append(arc)
            if codes and any(c.encode() in data or c.encode("utf-16-le") in data for c in codes):
                report["kept"].append(arc)
            z.writestr(zipfile.ZipInfo.from_file(f, arc), data, compress_type=zipfile.ZIP_DEFLATED)
            report["files"] += 1
            report["bytes"] += len(data)
            if progress is not None and progress(n + 1, len(files)) is False:
                report["cancelled"] = True
                break
    if report.get("cancelled"):
        tmp.unlink(missing_ok=True)
        return report
    tmp.replace(path)
    report["path"] = str(path)
    return report
