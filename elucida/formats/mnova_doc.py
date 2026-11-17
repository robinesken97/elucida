"""
elucida/formats/mnova_doc.py - Mnova-Dokument (.mnova) lesen (ohne Qt): je 1D-Spektrum den eingebetteten Bruker-FID mit
acqus/procs, in derselben Form wie `formats/bruker_nmr` für einen TopSpin-Ordner (`read_fid` -> (FID, acqus), `procs`),
damit die eigene Verarbeitung unverändert rechnet. Mnovas Umreferenzierung nur als Vorschlag (`ref_shift`, gilt nie ohne
Bestätigung). 2D, ungeprüfte Versionen und alles, was nicht genau passt, wird mit Meldung abgelehnt. Mnovas eigenes
Spektrum (JPEG 2000) wird nicht gelesen.
"""
from __future__ import annotations

import re
import struct
import tempfile
import zlib
from pathlib import Path

import numpy as np

from elucida.app.i18n import T
from elucida.formats import bruker_nmr as BN

# Belegt (Machbarkeitsstudie 2026-11-15, Entscheidung 95; Qt QDataStream: big endian, QString = u32 Bytelänge + UTF-16BE):
#   Kopf „Mestrelab Research S.L.“ + f1e2d3c4 + u32-Tabelle; Ende des Versionstexts = 31 + erster Tabellenwert.
#   Eingebettete Datei: QString Name | u32, u32, 3 × (u32 Tag, u32 ms, u8) | qint64 n | n Bytes qCompress (u32 Länge + zlib)
#   | QString Pfad. Rohdaten: 0f 00000000 01 u32(L >> 8) 05 u32(L) 01 | L Bytes float32 LE = Bruker-FID als float32
#   (DTYPA 0: ganze Zahlen; DTYPA 2: float64 auf float32 gerundet, Spektrum relativ ≤ 3e-9 daneben); davor die
#   Dateien seines Experiments (acqus/procs je zweimal).
#   Achse: BE double [Frequenz des letzten Punkts in Hz, SFO1, SW]; je Spektrum mehrfach, Mnovas Umreferenzierung ist
#   der eine abweichende Wert (übrige = Bruker: Hz + SW = OFFSET · SF).
MAGIC = b"Mestrelab Research S.L.\xf1\xe2\xd3\xc4"
# Versionslinien (Haupt.Neben, Build egal) nur mit Beleg: FID + acqus/procs gleich dem TopSpin-Ordner derselben Messung
# (10.0, 12.0, 14.1, 14.2; 10.0 nur FID + acqus, Ordner ohne pdata) oder, ohne Ordner, eigene Verarbeitung + Vorschlag
# trifft Mnovas Peaklabels (15.0: SVG-Labels an 101 Dokumenten). Ohne Beleg abgelehnt: 11.0, 14.0, 16, 17 (Peakliste im
# Dokument nicht eindeutig zuordenbar, kein Rohdatensatz), 6.x (anderer Aufbau) und alle übrigen.
CHECKED_LINES = ("10.0", "12.0", "14.1", "14.2", "15.0")
_FILE_RE = re.compile(rb"\x00\x00\x00\x00(....)(....)\x78[\x01\x5e\x9c\xda]", re.S)
_ARRAY_RE = re.compile(rb"\x0f\x00\x00\x00\x00\x01(....)\x05(....)\x01", re.S)
_STAMP = struct.Struct(">II" + "IIB" * 3)          # 35 Bytes zwischen Name und Länge
DAY_MIN, DAY_MAX = 2415021, 2488070                # julianischer Tag 1900 … 2100
BRUKER_TOL_HZ = 0.01                               # Bruker-Eintrag vs. OFFSET · SF − SW: gesehen ≤ 0.006 Hz (306 Spektren)
USED_FILES = ("acqus", "procs", "acqu2s", "proc2s")  # nur diese werden entpackt, übrige nur als Rahmen erkannt
FILE_MAX = 4 << 20                                 # Bytes je Parameterdatei (echte acqus ~9 kB): Schutz vor Zip-Bomben
ZCHUNK = 64 << 10                                  # Bytes komprimierter Eingabe je zlib-Aufruf
UNPACK_MAX = 64 << 20                              # Bytes entpackt je Dokument (echte Dokumente höchstens 0.4 MB)
GRPDLY_MAX = 200                                   # Gruppenlaufzeit in Punkten (gesehen 68 … 76, Tabelle bis 72.4)
DSP_KEYS = ("GRPDLY", "DECIM", "DSPFVS", "DIGMOD")  # gehen in nmr_proc.group_delay: vorher endlich, |x| ≤ DSP_ABS_MAX
DSP_ABS_MAX = 1e6
REF_MAX_PPM = 10                                   # Vorschlag größer: keiner (gesehen höchstens 2.94 ppm, 202 Spektren)
SI_MAX = 1 << 22                                   # Punkte (echte 1D bis 2^18)
INT_EXACT = 2 ** 24                                # float32 hält ganze Zahlen nur bis hier genau
# FID statt verarbeiteter Daten (gleiche Länge möglich: TD = SI in 123, TD = 2·SI in 128 von 304 Spektren): Betrag maximal
# bis 4 · Gruppenlaufzeit + 16 Punkte. Gesehen: 298 von 299 FIDs ≤ 2 ·, verarbeitete TopSpin-1r/1i (972) alle ≥ 14 ·.
FID_PEAK_GRPDLY = 4


def _qstring_ending(b, end):
    """QString, der genau bei `end` endet -> Text, sonst None."""
    for n in range(2, 512, 2):
        s = end - n
        if s < 4:
            break
        if struct.unpack(">I", b[s - 4:s])[0] == n:
            try:
                t = b[s:end].decode("utf-16-be")
            except UnicodeDecodeError:
                return None
            return t if t.isprintable() else None
    return None


def _stamp_ok(raw):
    """Die 35 Bytes vor der Länge: drei Zeitstempel (Tag 0 oder 1900–2100, ms < 1 Tag)."""
    v = _STAMP.unpack(raw)
    return all((d == 0 or DAY_MIN <= d <= DAY_MAX) and ms < 86_400_000 for d, ms in zip(v[2::3], v[3::3]))


def _embedded(b, m, budget):
    """Treffer von _FILE_RE -> ((Name, Inhalt, Ende) oder None, wenn ein Rahmenteil nicht genau passt; entpackte Bytes,
    auch bei Fehlschlag, bei zlib-Fehler die Obergrenze). Inhalt nur für USED_FILES bis FILE_MAX (größer: None, die
    Datei wird abgelehnt); übrige Dateien nur am Anfang des zlib-Stroms geprüft. Ohne Kopie (memoryview): viele falsche
    Rahmen bis Dateiende kosten nichts."""
    n, raw_len = struct.unpack(">I", m.group(1))[0], struct.unpack(">I", m.group(2))[0]
    z0, end = m.start() + 12, m.start() + 8 + n
    if n < 6 or end > len(b) or m.start() < 39 or not _stamp_ok(b[m.start() - 35:m.start()]):
        return None, 0
    name = _qstring_ending(b, m.start() - 35)
    if not name:
        return None, 0
    d = zlib.decompressobj()
    used = name in USED_FILES and raw_len <= FILE_MAX
    limit = raw_len + 1 if used else 64
    if limit > budget:
        raise OverflowError
    src, raw, pos = memoryview(b)[z0:end], b"", 0
    try:                                                    # stückweise: zlib kopiert sonst den ganzen Rest je Rahmen
        while pos < len(src) and not d.eof and len(raw) < limit:
            raw += d.decompress(src[pos:pos + ZCHUNK], limit - len(raw))
            if d.unconsumed_tail:                            # Ausgabegrenze erreicht
                break
            pos += ZCHUNK
    except zlib.error:
        return None, limit                                  # Ausgabe bis zum Fehler unbekannt: Obergrenze anrechnen
    if not used:
        return (name, None, end), len(raw)
    if not d.eof or d.unused_data or d.unconsumed_tail or pos < len(src) or len(raw) != raw_len:
        return None, len(raw)
    return (name, raw, end), len(raw)


def _items(b, name=""):
    """Eingebettete Dateien und Rohdatenfelder in Dateireihenfolge: ("file", Lage, Name, Inhalt) / ("array", Lage, Punkte).
    Treffer innerhalb eines schon gelesenen Teils (Daten können das Muster enthalten) zählen nicht. Mehr als UNPACK_MAX
    entpackt: ValueError (ganzes Dokument)."""
    hits = sorted([(m.start(), 0, m) for m in _FILE_RE.finditer(b)] + [(m.start(), 1, m) for m in _ARRAY_RE.finditer(b)],
                  key=lambda h: h[0])
    out, done, total = [], 0, 0
    for pos, kind, m in hits:
        if pos < done:
            continue
        if kind == 0:
            try:
                r, used = _embedded(b, m, UNPACK_MAX - total)
            except OverflowError:
                raise ValueError(T("mnovadoc_unpack_total", name=name, mb=UNPACK_MAX >> 20)) from None
            total += used                                   # auch Rahmen, die danach scheitern
            if r:
                out.append(("file", pos, r[0], r[1]))
                done = r[2]
        else:
            a, size = struct.unpack(">I", m.group(1))[0], struct.unpack(">I", m.group(2))[0]
            if a == size >> 8 and size % 4 == 0 and size >= 16 and m.end() + size <= len(b):
                out.append(("array", m.end(), size // 4))
                done = m.end() + size
    return out


def version(b):
    """Versionstext („14.2.1-27684“) aus dem Kopf, sonst None."""
    if not b.startswith(MAGIC) or len(b) < 31:
        return None
    end = 31 + struct.unpack(">I", b[27:31])[0]
    v = _qstring_ending(b, end) if end <= len(b) else None
    return v if v and re.fullmatch(r"\d+\.\d+\.\d+-\d+", v) else None


def _params(raw, name):
    """Bruker-Parameterdatei (Bytes) -> dict über `bruker_nmr.read_params` (ein Leser für beide Quellen)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / name
        p.write_bytes(raw)
        return BN.read_params(p)


def axis_start(a, p):
    """Erster Punkt der unkalibrierten Achse (= `nmr_analysis.axis_uncalibrated(a, p)[0]`, ohne die ganze Achse)."""
    return (a["SFO1"] / a["BF1"] - 1) * 1e6 + 0.5 * p["SW_p"] / a["BF1"]


def _ref_shift(b, lo, hi, a, p):
    """Mnovas Umreferenzierung als Verschiebung auf der unkalibrierten Achse (`nmr_analysis.axis_uncalibrated`, wie
    `suggest_reference` „shift“) -> (ppm oder None, Meldung oder None). Nur ein einziger abweichender Achseneintrag
    zählt; mehrere -> kein Vorschlag (nichts raten). a/p mit geprüften Werten (endlich, > 0)."""
    sw = a["SW_h"]
    lows = []
    for m in re.finditer(re.escape(struct.pack(">d", float(a["SFO1"]))), b[lo:hi]):
        j = lo + m.start()
        if j - 8 < lo or j + 16 > hi:
            continue
        low, w = struct.unpack(">d", b[j - 8:j])[0], struct.unpack(">d", b[j + 8:j + 16])[0]
        if abs(w - sw) <= 1e-9 * sw and np.isfinite(low):
            lows.append(low)
    groups = []
    for x in lows:                                          # gleiche Werte (letzte Stellen schwanken) zusammenfassen
        g = next((g for g in groups if abs(g[0] - x) < 1e-3), None)
        g.append(x) if g else groups.append([x])
        if len(groups) > 2:
            return None, T("mnovadoc_ref_ambiguous")
    if len(groups) <= 1:
        return None, None
    single = [g for g in groups if len(g) == 1]
    if len(single) != 1:
        return None, T("mnovadoc_ref_ambiguous")
    try:                                                    # Mehrheit muss Brukers Referenzierung sein, sonst nichts
        bruker = BN.num(p, "OFFSET", "procs") * BN.num(p, "SF", "procs") - sw
    except ValueError:
        bruker = None
    if bruker is None or not abs(next(g for g in groups if len(g) > 1)[0] - bruker) <= BRUKER_TOL_HZ:   # auch NaN
        return None, T("mnovadoc_ref_unmatched")
    shift = float((single[0][0] + sw) / a["BF1"] - axis_start(a, p))   # erster Punkt; Teiler BF1 (SF/BF1 − 1 < 1e-5)
    if not abs(shift) <= REF_MAX_PPM:                                    # auch NaN/unendlich
        return None, T("mnovadoc_ref_large", v=f"{shift:.4g}", max=REF_MAX_PPM)
    return shift, None


def write_experiment(spec, folder):
    """Spektrum aus `read_document` als TopSpin-Ordner (acqus, fid nach DTYPA/BYTORDA, pdata/1/procs)."""
    d = Path(folder)
    (d / "pdata" / "1").mkdir(parents=True, exist_ok=True)
    (d / "acqus").write_bytes(spec["files"]["acqus"])
    (d / "pdata" / "1" / "procs").write_bytes(spec["files"]["procs"])
    bo = ">" if spec["acqus"].get("BYTORDA") == 1 else "<"
    raw = np.empty(2 * spec["fid"].size)
    raw[0::2], raw[1::2] = spec["fid"].real, spec["fid"].imag
    raw.astype(bo + ("f8" if spec["acqus"].get("DTYPA") == 2 else "i4")).tofile(d / "fid")
    return d


def _item(b, g, off, n, span, where):
    """Ein Rohdatenfeld mit den Dateien davor -> ("spec", Spektrum) / ("rej", Meldung) / ("skip", Meldung)."""
    from elucida.core import nmr_proc as NP                 # hier: core importiert formats
    if "acqus" not in g or "procs" not in g:
        return "skip", T("mnovadoc_no_params", where=where)
    big = next((f for f in USED_FILES if None in g.get(f, ())), None)
    if big:
        return "rej", T("mnovadoc_file_big", where=where, file=big, mb=FILE_MAX >> 20)
    if any(len(set(g[f])) > 1 for f in ("acqus", "procs", "acqu2s", "proc2s") if f in g):
        return "rej", T("mnovadoc_copies", where=where)
    a, p = _params(g["acqus"][0], "acqus"), _params(g["procs"][0], "procs")
    label = f"{a.get('NUC1', '?')}, {a.get('PULPROG', '?')}"
    if "acqu2s" in g or "proc2s" in g or a.get("PARMODE", 0) != 0:
        pseudo = any(x in str(a.get("PULPROG", "")).lower() for x in NP.PSEUDO_2D)
        return ("skip", T("mnovadoc_pseudo", where=where, what=label)) if pseudo else \
            ("rej", T("mnovadoc_2d", where=where, what=label))
    td = BN._td(a, where)                              # dieselben Prüfungen wie read_fid (ValueError mit Meldung)
    BN._dtype(a, "DTYPA", "BYTORDA", where, big=True)
    for par, keys in ((a, ("SFO1", "BF1", "SW_h")), (p, ("SW_p", "SI"))):
        for key in keys:                           # Achse und Vorschlag teilen durch diese Werte
            x = BN.num(par, key, where)
            if not (np.isfinite(x) and x > 0) or key == "SI" and (not isinstance(x, int) or x > SI_MAX):
                raise ValueError(T("mnovadoc_param", name=where, key=key, v=x))
    for key in DSP_KEYS:                           # nmr_proc.group_delay rechnet int(DECIM) usw.: nur endliche Zahlen
        x = a.get(key)
        if x is not None and (isinstance(x, bool) or not isinstance(x, (int, float)) or not abs(x) <= DSP_ABS_MAX):
            raise ValueError(T("mnovadoc_param_dsp", name=where, key=key, v=x))
    dt = a["DTYPA"]
    if dt == 2 and a["BYTORDA"] == 1:                  # nicht gesehen: ungeprüft
        return "rej", T("b1nmr_unchecked", name=where, key="BYTORDA (DTYPA 2)", v=1)
    if td != n:
        return "rej", T("b1nmr_size", name=where, n=n, m=td)
    v = np.frombuffer(b, "<f4", count=n, offset=off).astype(float)
    if not np.all(np.isfinite(v)):
        return "rej", T("mnovadoc_not_finite", where=where)
    if dt == 0 and np.any(v != np.round(v)):
        return "rej", T("mnovadoc_not_raw", where=where)
    if dt == 0 and np.abs(v).max() >= INT_EXACT:     # dort ist jede float32-Zahl ganz: Prüfung ohne Aussage
        return "rej", T("mnovadoc_int_range", where=where)
    g_ = NP.group_delay(a)
    peak = int(np.argmax(np.hypot(v[0::2], v[1::2])))
    if g_ is None or not 0 < g_ <= GRPDLY_MAX or peak > FID_PEAK_GRPDLY * g_ + 16:
        return "rej", T("mnovadoc_not_fid", where=where, i=peak, g="–" if g_ is None else round(g_, 2))
    shift, note = _ref_shift(b, *span, a, p)
    spec = dict(fid=v[0::2] + 1j * v[1::2], acqus=None, procs=None, nucleus=str(a.get("NUC1", "")),
                pulprog=str(a.get("PULPROG", "")), ref_shift=shift, notes=[note] if note else [], copies=1,
                files=dict(acqus=g["acqus"][0], procs=g["procs"][0]))
    with tempfile.TemporaryDirectory() as d:         # über bruker_nmr gelesen: dieselbe Form wie ein TopSpin-Ordner
        exp = write_experiment(dict(spec, acqus=a), Path(d) / "1")
        spec["fid"], spec["acqus"] = BN.read_fid(exp)
        spec["procs"] = BN.procs(exp / "pdata" / "1")
    return "spec", spec


def _item_safe(b, g, off, n, span, where):
    """_item; jede Ausnahme lehnt nur dieses Element ab. Speicher und Zeit begrenzen die Prüfungen in _item, nicht dies."""
    try:
        return _item(b, g, off, n, span, where)
    except ValueError as ex:
        return "rej", str(ex)
    except (MemoryError, OSError):                          # Rechner/Temp-Ordner: nicht je Datensatz wiederholen
        raise
    except Exception as ex:                                 # unerwartet: nie das Dokument abbrechen
        return "rej", T("mnovadoc_item_error", where=where, err=type(ex).__name__)


def read_document(path):
    """Mnova-Dokument -> dict(version, spectra, rejected, skipped). spectra: je 1D-Spektrum mit Rohdaten dict(fid,
    acqus, procs wie `bruker_nmr.read_fid`/`procs`, nucleus, pulprog, ref_shift (Vorschlag oder None), notes, copies =
    gleiche Kopien im Dokument, files = acqus/procs als Bytes). rejected: Meldungen zu nicht gelesenen Messspektren (ohne
    lesbares Spektrum zuerst `mnovadoc_none`); skipped: „nicht übernommen (kein Messspektrum)“.
    Kein Mnova-Dokument, ungeprüfte Version oder mehr als UNPACK_MAX entpackt: ValueError mit Meldung."""
    name = Path(path).name
    b = Path(path).read_bytes()
    if not b.startswith(MAGIC):
        raise ValueError(T("mnovadoc_not_mnova", name=name))
    ver = version(b)
    if ver is None or ".".join(ver.split(".")[:2]) not in CHECKED_LINES:
        raise ValueError(T("mnovadoc_version", name=name, v=ver or "?", ok=", ".join(CHECKED_LINES)))
    try:
        return _read_items(b, name, ver)
    except OSError as ex:                                   # Temp-Ordner nicht schreibbar: einmal fürs Dokument
        raise ValueError(T("mnovadoc_temp", name=name, err=ex.strerror or type(ex).__name__)) from None


def _read_items(b, name, ver):
    spectra, rejected, skipped, group, lo, k = [], [], [], {}, 0, 0
    for it in _items(b, name):
        if it[0] == "file":
            if it[2] in USED_FILES:
                group.setdefault(it[2], []).append(it[3])
            continue
        _, off, n = it
        k += 1
        g, span, group, lo = group, (lo, off), {}, off + 4 * n
        where = T("mnovadoc_where", name=name, k=k)
        kind, spec = _item_safe(b, g, off, n, span, where)
        if kind != "spec":
            (skipped if kind == "skip" else rejected).append(spec)
            continue
        shift = spec["ref_shift"]
        same = next((s for s in spectra if s["files"] == spec["files"] and s["ref_shift"] == shift
                     and s["notes"] == spec["notes"] and np.array_equal(s["fid"], spec["fid"])), None)
        if same:
            same["copies"] += 1
        else:
            spectra.append(spec)
    if not spectra:
        rejected.insert(0, T("mnovadoc_none", name=name))
    return dict(version=ver, spectra=spectra, rejected=rejected, skipped=skipped)
