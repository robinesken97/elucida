"""
elucida/exchange/datapack.py - Datenpaket je Verbindung (Zip) für Repositorien wie TUDOdata.

Aufbau wie die veröffentlichten Datensätze der Gruppe (je Verbindung ein Zip <Name>.zip mit Ordner <Name>/):
    NMR/1H/10/, NMR/13C/11/, NMR/HSQC + HMBC/12/ …   TopSpin-Experimente vollständig, Ordner = Experimentnummer
    IR/        OPUS-Datei und -PDF
    MS/        Bericht der Massenabteilung, Bruker-.d
    UV-Vis/    Messdateien des ε-Tabs
    Fluorescence/, CV/<Lösungsmittel>/, SEC/, EPR/ (BES3T-Partnerdateien mit)
    DFT/, Elucida/ (Abbildungen, SI)           wählbar, Standard aus
X-Ray (CCDC) und Synthese gehören nicht hinein. Nur Dateien, auf die der Projektzustand zeigt (nichts Internes).

Nutzerwunsch: außer „Compound XX“ und ohne Datum unveränderte Rohdaten, überall. Laborkürzel (z. B. „RE-3-150“) in
Datei- und Ordnernamen immer ersetzt; im Inhalt (wahlweise, Standard an) Kürzel -> „Compound XX“ und Datum/Uhrzeit
gelöscht: alle Textdateien (keine Nullbytes; auch TopSpin-Parameter, title, audita.txt, ##$DATE= -> 0), Word-Berichte
(Absätze, Dateieigenschaften, EMF-Beschriftungen), OPUS-Binärdateien auf gleicher Länge (Strings mit Leerzeichen).
Messwerte (fid/ser/1r …) bytegleich; nicht bearbeitbar (PDF, .mnova, Bruker .d): Kürzel darin im Bericht.
Ohne Qt (Dialog: elucida/app/datapack_dialog.py).
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Laborkürzel „Initialen-Buch-Seite“, z. B. RE-3-150, RE-12-7a, RE-2-142FC (TopSpin-Datensatz „OCM-RE-2-142FC_…“)
CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,4}-\d{1,3}-\d{1,4}(?:[a-z]|[A-Z]{1,3})?)(?![A-Za-z0-9])")
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
    # Mnova-Dokumente (.mnova) nie im Datenpaket (FB-10): Arbeitsdateien, Rohdaten liegen als TopSpin-Experimente bei
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

    dft = state.get("dft") or {}
    prof = dft.get("profile") or {}
    extra = [{"file": f} for f in (prof.get("sp") or []) + ((dft.get("nics") or {}).get("files") or [])]
    extra += [{"file": d.get("file"), "molden": d.get("trj")} for d in prof.get("irc") or []]   # IRC + Trajektorie
    for e in (dft.get("entries") or []) + extra:
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
            if read_text and f.suffix.lower() == ".docx" and zipfile.is_zipfile(f):
                try:
                    found |= set(CODE_RE.findall(docx_text(f.read_bytes())))
                except (zipfile.BadZipFile, KeyError):
                    pass
            elif read_text and f.suffix.lower() == ".pdf" and f.stat().st_size <= TEXT_MAX:
                try:                                   # Text meist komprimiert
                    found |= set(CODE_RE.findall(pdf_text(f.read_bytes())))
                except Exception:
                    pass
            elif read_text and f.stat().st_size <= limit and _is_text(f):
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


# Datumsangaben (MS-Bericht): 12.03.2024, 12.3.24, 2024-03-12, 12/03/2024, 12 March 2024, 12. März 2024; mit Uhrzeit;
# TopSpin: „Fri Mar  8 08:29:16 2024“ (ctime), Datensatzordner „…_2024-04-11_13-23-37_AV500“
_MONTHS = ("Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Mär|Mai|Okt|Dez|January|February|March|April|June|July|"
           "August|September|October|November|December|Januar|Februar|März|Juni|Juli|Oktober|Dezember")
DATE_RE = re.compile(r"(?<![\d.])(?:\d{1,2}(?P<sep>[./])\d{1,2}(?P=sep)(?:\d{4}|\d{2})|\d{4}-\d{2}-\d{2}|"
                     rf"\d{{1,2}}\.?\s(?:{_MONTHS})\.?\s\d{{4}}|"
                     rf"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(?:{_MONTHS})\s+\d{{1,2}}\s+\d{{1,2}}:\d{{2}}:\d{{2}}\s+\d{{4}}|"
                     rf"(?:{_MONTHS})\d{{1,2}}-\d{{4}})"                    # TopSpin-Probenwechsler „Apr11-2024-0602“
                     r"(?:[ T,]+\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?[AP]M)?(?:\s?[+-]\d{2}:?\d{2})?|_\d{2}-\d{2}-\d{2})?"
                     r"(?!\d|\.\d)")                                # Punkt am Satzende/vor der Endung zählt nicht
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)                            # Zeitstempel im Zip (sonst Messdatum als mtime)
# Im Inhalt wird das Datum nicht gelöscht, sondern durch 1980-01-01 im selben Format ersetzt (Nutzerwunsch P8 R2):
# Dateien bleiben lesbar (Gamry DATE+TIME, BWSpec-Zeitstempel), Uhrzeiten und damit Abstände innerhalb einer
# Messung bleiben, ein Projektverlauf über Kalendertage nicht. Zahlenfelder behalten ihre Breite.
_KEEP_IN_DATE = re.compile(r"\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?[AP]M)?(?:\s?[+-]\d{2}:?\d{2})?|_\d{2}-\d{2}-\d{2}$")
_MONTH_ANY = re.compile("|".join(sorted(_MONTHS.split("|"), key=len, reverse=True)))


def date_placeholder(m) -> str:
    """Treffer von DATE_RE -> 1980-01-01 im selben Format, Uhrzeit/Zeitzone bleiben."""
    s = m.group(0)
    keep = [k.span() for k in _KEEP_IN_DATE.finditer(s)]
    runs = [r for r in re.finditer(r"\d+", s) if not any(a <= r.start() < b for a, b in keep)]
    year = runs[0] if re.match(r"\d{4}-", s) else runs[-1]
    for r in reversed(runs):                           # gleiche Breite: Positionen bleiben gültig
        n = len(r.group())
        new = ("1980" if n == 4 else "80"[-n:].rjust(n, "0")) if r is year else "1".rjust(n, "0")
        s = s[:r.start()] + new + s[r.end():]
    s = re.sub(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", "Tue", s)        # 1980-01-01 war ein Dienstag
    return _MONTH_ANY.sub(lambda m: "Jan" if len(m.group()) == 3 else "January", s)


# Verweise auf Nutzer (Nutzerwunsch P8 R1: alle weg) – Namen aus diesen Feldern werden überall im Paket ersetzt
USER = "user"
_USER_RES = (re.compile(r"^##OWNER=[ \t]*([^\s<>]+)[ \t]*$", re.M),                 # TopSpin-Parameter
             re.compile(r"^(?:\$\$|#)\s.*?\s([^\s@]+)@[^\s@]+\s*$", re.M),       # „$$ <Zeit>  nmrsu@AV500“
             re.compile(r"^\(\s*\d+,<[^>]*>,<([^<>]+)>,", re.M),                    # audita.txt
             re.compile(r"^User\s*:\s*(\S+)", re.M),                                # uxnmr.info
             re.compile(r'\b(?:creator|owner)="([^"]+)"'),                           # peaklist.xml
             re.compile(r"^OPER\s+(\S.*?)\s*$", re.M),                               # BES3T .dsc
             re.compile(r"(?i)[A-Z]:\\Users\\([^\\\s\x00]+)\\"),                 # Windows-Benutzerordner
             re.compile(r"/(?:Users|home)/([^/\s]+)/"),
             re.compile(r"/data/([^/\s]+)/nmr/"))                                   # TopSpin-Datenpfad
_NOT_USERS = {"user", "public", "shared", "default", "all users"}
_USER_LINE = re.compile(r"^(User\s*:\s*)\S.*$", re.M)                                # „nmrsu (NMR Administrator …)“
_OPUS_OPERATOR = re.compile(rb"CNM\x00\x02\x00(.)\x00", re.S)                       # OPUS: Operator (Text, n Wörter)


def find_users(texts) -> list[str]:
    """Nutzer-/Kontonamen aus TopSpin-, BES3T-, Pfadangaben usw. (Texte als str)."""
    found = set()
    for t in texts:
        for rx in _USER_RES:
            found |= {u.strip() for u in rx.findall(t)}
    return sorted(u for u in found if len(u) >= 2 and u.lower() not in _NOT_USERS)
JCAMP_DATE = re.compile(r"^(##\$DATE=\s*)\d+", re.M)          # TopSpin: Messzeit als Sekunden seit 1970
OPUS_RE = re.compile(r"\.\d+$")                              # Bruker OPUS: name.0, name.1 …
# Dateieigenschaften eines Word-Dokuments mit Personen/Zeitpunkten (docProps/core.xml, app.xml)
_DOCPROPS = ("dc:creator", "cp:lastModifiedBy", "dcterms:created", "dcterms:modified", "cp:lastPrinted", "Company",
             "Manager")


def scrub_text(s: str, repl: dict, dates: bool) -> str:
    s = replace_codes(s, repl)
    if not dates:
        return s
    return _USER_LINE.sub(rf"\g<1>{USER}", JCAMP_DATE.sub(r"\g<1>0", DATE_RE.sub(date_placeholder, s)))


def scrub_binary_strings(data: bytes, repl: dict, dates: bool) -> bytes:
    """Binärdatei mit Textfeldern (OPUS): Kürzel und Datum auf gleicher Länge (ASCII und UTF-16) ersetzen, damit
    alle Längen und Versätze stimmen; übrige Bytes unverändert."""
    b = bytearray(data)
    for code, new in repl.items():
        for enc in ("latin-1", "utf-16-le"):
            old_b, new_b = code.encode(enc), new[:len(code)].ljust(len(code)).encode(enc)
            b = bytearray(bytes(b).replace(old_b, new_b))
    if dates:
        txt = bytes(b).decode("latin-1")
        for m in DATE_RE.finditer(txt):
            new = date_placeholder(m)
            b[m.start():m.end()] = new[:len(m.group())].ljust(len(m.group())).encode("latin-1")
        for m in _OPUS_OPERATOR.finditer(bytes(b)):
            n = 2 * m.group(1)[0]
            b[m.end():m.end() + n] = USER.encode()[:n].ljust(n, b"\0")
    return bytes(b)


def scrub_pdf(data: bytes) -> bytes:
    """PDF (nicht bearbeitbar): nur Dateieigenschaften auf gleicher Länge – Datum (Info, XMP) -> 1980-01-01,
    Autor/Ersteller-Person leer; Inhalt, Versätze und xref bleiben."""
    data = re.sub(rb"(/(?:CreationDate|ModDate)\s*\(D:)\d{8}", rb"\g<1>19800101", data)
    data = re.sub(rb"((?:xmp:\w*Date|xap:\w*Date)(?:>|=\"))\d{4}-\d{2}-\d{2}", rb"\g<1>1980-01-01", data)
    return re.sub(rb"(/Author\s*\()([^()\\]*)(\))", lambda m: m[1] + b" " * len(m[2]) + m[3], data)


def _scrub_word_xml(xml: str, repl: dict, dates: bool) -> str:
    """Absätze eines WordprocessingML-Teils: Text je Absatz zusammensetzen (Word teilt ihn in Runs, z. B. „RE-3-“ +
    „150“), Kürzel/Datum ersetzen; geänderter Absatz -> ganzer Text im ersten Run, übrige Runs leer."""
    import html as _h

    def runs(tag):
        t_re = re.compile(rf"(<{tag}(?:\s[^>]*)?>)(.*?)(</{tag}>)", re.S)

        def block(m):
            p = m.group(0)
            parts = t_re.findall(p)
            if not parts:
                return p
            old = "".join(_h.unescape(t) for _, t, _ in parts)
            new = scrub_text(old, repl, dates)
            if new == old:
                return p
            k = [0]

            def run(mt):
                k[0] += 1
                text = _h.escape(new, quote=False) if k[0] == 1 else ""
                return f'<{tag} xml:space="preserve">' + text + f"</{tag}>"
            return t_re.sub(run, p)
        return block
    xml = re.sub(r"<w:p[ >].*?</w:p>", runs("w:t"), xml, flags=re.S)
    xml = re.sub(r"<w:del[ >].*?</w:del>", runs("w:delText"), xml, flags=re.S)   # gelöschter Text (Änderungen)
    xml = re.sub(r'(\sw:(?:author|initials)=")[^"]*(")', r"\1\2", xml)   # Personen an Änderungen/Kommentaren
    return re.sub(r'\sw:date="[^"]*"', "", xml) if dates else xml


def _scrub_emf(data: bytes, repl: dict, dates: bool) -> bytes:
    """Beschriftungen in EMF (UTF-16, EMR_EXTTEXTOUTW): auf gleicher Länge ersetzen (Zeichenzahl/Abstände bleiben)."""
    for code, new in repl.items():
        data = data.replace(code.encode("utf-16-le"), new[:len(code)].ljust(len(code)).encode("utf-16-le"))
    if dates:
        for off in (0, 1):                             # Texte beginnen auf gerader oder ungerader Position
            seg = data[off:]
            txt = seg[:len(seg) // 2 * 2].decode("utf-16-le", errors="replace")
            for m in DATE_RE.finditer(txt):            # Platzhalter gleicher Länge (R2)
                old = m.group(0)
                data = data.replace(old.encode("utf-16-le"),
                                    date_placeholder(m)[:len(old)].ljust(len(old)).encode("utf-16-le"))
    return data


def scrub_docx(data: bytes, repl: dict, dates=True) -> bytes:
    """Word-Bericht (z. B. der Massenabteilung) ohne Laborkürzel, Datumsangaben und Personennamen in den
    Dateieigenschaften; Spektren-Bilder (EMF) auf gleicher Länge. Übrige Teile bytegleich."""
    import io
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():
            b = src.read(info.filename)
            n = info.filename
            if n.startswith("word/") and n.endswith(".xml"):
                b = _scrub_word_xml(b.decode("utf-8"), repl, dates).encode("utf-8")
            elif n.startswith("docProps/") and n.endswith(".xml"):
                x = b.decode("utf-8")
                for tag in _DOCPROPS:
                    x = re.sub(rf"<{tag}(?:\s[^>]*)?>.*?</{tag}>|<{tag}(?:\s[^>]*)?/>", "", x, flags=re.S)
                b = scrub_text(x, _xml_repl(repl), dates).encode("utf-8")    # Titel/Betreff/eigene Felder
            elif n.lower().endswith(".emf"):
                b = _scrub_emf(b, repl, dates)
            if dates:
                info.date_time = _ZIP_TIME
            z.writestr(info, b)
    return out.getvalue()


def docx_text(data: bytes) -> str:
    """Gesamter Text eines Word-Dokuments (Teile word/*.xml, Dateieigenschaften, EMF-Beschriftungen) zum Prüfen."""
    import html as _h
    import io
    parts = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            b = z.read(n)
            if n.endswith(".xml"):
                x = b.decode("utf-8", errors="replace")
                for p in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S) or [x]:
                    parts.append("".join(_h.unescape(t) for t in re.findall(
                        r"<w:(?:t|delText)(?:\s[^>]*)?>(.*?)</w:(?:t|delText)>", p, re.S)) or re.sub(r"<[^>]+>", " ", p))
            elif n.lower().endswith(".emf") and len(b) % 2 == 0:
                parts.append(b.decode("utf-16-le", errors="replace"))
    return "\n".join(parts)


def pdf_text(data: bytes) -> str:
    """Text und Dateieigenschaften einer PDF (Inhalt meist komprimiert) zum Prüfen auf Kürzel."""
    import pymupdf
    with pymupdf.open(stream=data, filetype="pdf") as d:
        return "\n".join([v for v in d.metadata.values() if v] + [p.get_text() for p in d])


def _safe_name(s: str) -> str:
    return re.sub(r'[\\:*?"<>|]', "_", s).strip() or "_"


def _clean_name(p: str, repl: dict) -> str:
    """Datei-/Ordnername im Zip: Kürzel ersetzt, Datum weg (vor der Endung, auch OPUS „….0“)."""
    p = replace_codes(p, repl)
    stem, dot, ext = p.rpartition(".")
    if dot and stem and re.fullmatch(r"[A-Za-z0-9]{1,5}", ext) and not (ext.isdigit() and len(ext) > 2):
        return _safe_name(DATE_RE.sub("", stem) + dot + ext)
    return _safe_name(DATE_RE.sub("", p))


def _xml_repl(repl: dict) -> dict:
    """Ersatztexte für XML-Inhalt maskieren („Compound A&B“)."""
    import html as _h
    return {k: (_h.escape(v, quote=False) if v is not None else v) for k, v in repl.items()}


_XML_EXT = {".xml", ".svg", ".html", ".htm", ".xhtml"}


def _decode(data: bytes):
    """Text -> (str, Kodierung) so, dass er beim Zurückschreiben bytegleich bleibt (UTF-8, sonst Latin-1)."""
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def write_zip(items, path, root, name_repl=None, text_repl=None, progress=None, docx_scrub=True) -> dict:
    """Ausgewählte Einträge als <path> schreiben (Ordner <root>/ darin). name_repl/text_repl: Kürzel -> Ersatz in
    Namen bzw. im Inhalt von Textdateien (None = Inhalt nicht ändern). docx_scrub: Word-Berichte (MS) ohne Kürzel,
    Datum und Personennamen. -> Bericht: Dateien, Größe, ersetzte Textdateien, Dateien, in denen ein Kürzel
    unverändert bleibt (Binärdateien)."""
    name_repl, codes = name_repl or {}, set(name_repl or {}) | set(text_repl or {})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    files, bases = [], set()
    for it in (i for i in items if i.on):
        base = "/".join(_clean_name(p, name_repl) for p in it.arc.split("/"))
        k = 2
        while base in bases:                           # zwei Messordner gleich nach dem Ersetzen: getrennt halten
            stem, dot, ext = base.rpartition(".")
            base = f"{stem}_{k}.{ext}" if dot and "/" not in ext else f"{base}_{k}"
            k += 1
        bases.add(base)
        if it.src.is_dir():
            for f in sorted(it.src.rglob("*")):
                if f.is_file():
                    rel = "/".join(_clean_name(p, name_repl) for p in f.relative_to(it.src).parts)
                    files.append((f, f"{base}/{rel}", it.group))
        else:
            files.append((it.src, base, it.group))
    if text_repl is not None:                          # Nutzer-/Kontonamen aus allen Dateien des Pakets (R1)
        texts = []
        for f, _, group in files:
            if f.stat().st_size <= TEXT_MAX and (_is_text(f) or group == "ir" and OPUS_RE.search(f.name)):
                texts.append(f.read_bytes().decode("latin-1"))
        text_repl = {**dict.fromkeys(find_users(texts), USER), **text_repl}
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
            is_docx = f.suffix.lower() == ".docx" and zipfile.is_zipfile(f)
            if is_docx and docx_scrub and text_repl is not None:
                try:
                    new_ = scrub_docx(data, text_repl or name_repl or {}, dates=True)
                    if new_ != data:
                        data = new_
                        report["text_replaced"].append(arc)
                except (zipfile.BadZipFile, UnicodeDecodeError, KeyError):
                    pass
            elif text_repl is not None and _is_text(f, data[:65536]):
                txt, enc = _decode(data)
                new = scrub_text(txt, _xml_repl(text_repl) if f.suffix.lower() in _XML_EXT else text_repl, dates=True)
                if new != txt:
                    data = new.encode(enc, errors="replace")
                    report["text_replaced"].append(arc)
            elif text_repl is not None and group == "ir" and OPUS_RE.search(f.name):
                new_b = scrub_binary_strings(data, {**text_repl, **name_repl}, dates=True)
                if new_b != data:
                    data = new_b
                    report["text_replaced"].append(arc)
            elif text_repl is not None and f.suffix.lower() == ".pdf":
                new_b = scrub_pdf(data)
                if new_b != data:
                    data = new_b
                    report["text_replaced"].append(arc)
            check = data
            if is_docx:
                check = docx_text(data).encode("utf-8")
            elif f.suffix.lower() == ".pdf" and codes:
                try:
                    check = data + pdf_text(data).encode("utf-8")
                except Exception:                      # beschädigte PDF: nur die Rohbytes prüfen
                    pass
            if codes and any(c.encode() in check or c.encode("utf-16-le") in check for c in codes):
                report["kept"].append(arc)
            zi = zipfile.ZipInfo(arc, _ZIP_TIME)       # nicht from_file: mtime vor 1980 wirft dort ValueError
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED)
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


# -- Publikation: alle Verbindungen auf einmal (elucida/app/publication.py) ---------------------------------------
@dataclass
class Plan:
    name: str                  # Name der Verbindung = Zip-Name (z. B. „6m“)
    pdir: Path
    items: list


def assign_codes(plans, read_text=True) -> dict:
    """Laborkürzel -> Verbindung: steht ein Kürzel in Datei-/Ordnernamen eines Projekts, gehört es zu dieser
    Verbindung; Kürzel nur im Inhalt gehören zur ersten Verbindung, in der sie vorkommen (wie beim Einzelpaket)."""
    out = {}
    for pl in plans:
        for c in find_codes(pl.items, read_text=False):
            out.setdefault(c, pl.name)
    if read_text:
        for pl in plans:
            for c in find_codes(pl.items, read_text=True):
                out.setdefault(c, pl.name)
    return dict(sorted(out.items()))


def write_publication(plans, out_dir, names, texts=None, compchem=True, readme="", license=None,
                      progress=None) -> dict:
    """Datensatz wie auf TUDOdata: je Verbindung <Name>.zip, DFT aller Verbindungen in CompChem.zip (Ordner je
    Verbindung), README.txt, Lizenztext. names/texts: Kürzel -> Ersatz in Namen/Inhalt (texts None = Inhalt
    unverändert). progress(Text, i, n) -> False bricht ab. -> Bericht je Zip + Summe."""
    from dataclasses import replace
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    chem = []
    for pl in plans:
        own = [i for i in pl.items if i.on and not (compchem and i.group == "dft")]
        if own:
            jobs.append((pl.name, own))
        if compchem:
            chem += [replace(i, arc=f"{pl.name}/{Path(i.arc).name}") for i in pl.items if i.on and i.group == "dft"]
    if chem:
        jobs.append(("CompChem", chem))
    report = dict(zips=[], files=0, bytes=0, text_replaced=0, kept=[], dir=str(out_dir))
    for k, (root, items) in enumerate(jobs):
        def prog(i, n, root=root, k=k):
            return progress is None or progress(root, k * 1000 + int(1000 * i / max(1, n)), 1000 * len(jobs))
        rep = write_zip(items, out_dir / f"{_safe_name(replace_codes(root, names))}.zip", root, names, texts, prog)
        if rep.get("cancelled"):
            report["cancelled"] = True
            return report
        report["zips"].append(rep["path"])
        report["files"] += rep["files"]
        report["bytes"] += rep["bytes"]
        report["text_replaced"] += len(rep["text_replaced"])
        report["kept"] += rep["kept"]
    if readme:
        (out_dir / "README.txt").write_text(readme, encoding="utf-8", newline="\n")
    if license is not None:
        name, src = license
        (out_dir / name).write_bytes(Path(src).read_bytes())
    return report
