"""
elucida/formats/mnova_cli.py - MNova finden und ein MNova-Dokument headless exportieren lassen (ohne Qt): je Seite SVG,
je Spektrum Kern, dim und die Berichte (Skript `assets/mnova/elucida_export.qs`). MNova arbeitet nur auf einer Kopie
in Elucidas eigenem Temp-Ordner; das Skript schreibt `manifest.json` als Letztes (Fertig-Marke).

Belegt (MNova 14.2.1, macOS, 2026-11-16): `MestReNova -nogui <skript.qs> -sf "funktion,a,b"` startet eine eigene
Instanz (gui=false) und ruft die Funktion; Pfade mit Leerzeichen/Umlauten gehen, **Kommas nicht** (auch nicht in
Anführungszeichen); MNova beendet sich nach `Application.exit` nicht immer -> der Aufrufer beendet seinen Prozess.
Windows ungeprüft (Programmsuche nach Muster, das Skript bricht ab, wenn es in einer Sitzung mit Oberfläche läuft).
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from elucida import ROOT

SCRIPT = ROOT / "assets" / "mnova" / "elucida_export.qs"
FUNCTION = "elucida_export"
TIMEOUT_S = 300                 # gemessen 3-4 s je Dokument (5 Testdokumente); großzügig, Fortschritt sichtbar
MAC_EXE = Path("/Applications/MestReNova.app/Contents/MacOS/MestReNova")


def find_mnova():
    """Pfad zu MestReNova oder None. macOS: fester Programmpfad; Windows: `MestReNova.exe` unter %ProgramFiles% und
    %ProgramFiles(x86)% (`Mestrelab Research S.L*/MestReNova/`, keine Versionspfade). Linux: nicht unterstützt."""
    if sys.platform == "darwin":
        return MAC_EXE if MAC_EXE.is_file() else None
    if sys.platform.startswith("win"):
        for var in ("ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(var)
            hits = sorted(Path(base).glob("Mestrelab Research S.L*/MestReNova/MestReNova.exe")) if base else []
            if hits:
                return hits[-1]
    return None


def has_comma(*paths):
    """MNova trennt die Argumente von -sf an Kommas: ein Pfad mit Komma geht nie (auch nicht in Anführungszeichen)."""
    return any("," in str(p) for p in paths)


def launch(args):
    """Prozess starten (im Selbsttest durch eine Attrappe ersetzt). Ohne Elucidas Qt-Umgebung (QT_QPA_PLATFORM=offscreen,
    Pluginpfade des gebauten Programms): MNova ist selbst ein Qt-Programm und endete damit ohne Ergebnis (gemessen)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("QT_", "QML"))}
    return subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=env)


def start(exe, doc, work):
    """Kopie von `doc` und des Skripts nach `work` (Elucidas eigener Temp-Ordner; nur dort schreibt MNova) und MNova
    darauf starten -> (Prozess, Ausgabeordner, Kennung). Das Skript läuft aus `work` (ein Programmpfad mit Leerzeichen
    ist ungeprüft). ValueError, wenn der Pfad ein Komma enthält (der Aufrufer fällt dann zurück)."""
    token = "elucida" + uuid.uuid4().hex[:12]
    work = Path(work)
    copy, out, script = work / f"{token}.mnova", work / "out", work / SCRIPT.name
    if has_comma(copy, out, script):
        raise ValueError("comma")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(doc, copy)
    shutil.copy2(SCRIPT, script)
    proc = launch([str(exe), "-nogui", str(script), "-sf", f"{FUNCTION},{copy},{out},{token}"])
    return proc, out, token


def read_manifest(out, token):
    """Manifest des Skripts -> dict oder None (noch nicht da, unvollständig oder von einem anderen Lauf)."""
    try:
        m = json.loads((Path(out) / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(m, dict) or m.get("token") != token:
        return None
    return m


def report_text(rep):
    """Bericht von MNova (HTML: „<sup>1</sup>H NMR (501 MHz, CDCl<sub>3</sub>) &delta; …“) -> Text wie aus der
    Zwischenablage („1H NMR (501 MHz, CDCl3) δ …“), leer ohne Bericht."""
    t = re.sub(r"(?is)<head\b.*?</head>", "", rep or "")
    t = re.sub(r"(?i)<br\s*/?>|</p>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines() if ln.strip())


def _identity(sp):
    """Gleiches Spektrum = gleicher Kern/dim/Multiplettbericht; außer bei ¹H auch derselbe Peakbericht (¹³C ohne
    Multipletts: zwei verschiedene Spektren hätten sonst denselben leeren Bericht; Insets haben denselben, geprüft)."""
    key = (sp.get("nucleus"), sp.get("dim"), report_text(sp.get("mreport")))
    return key if sp.get("nucleus") == "1H" else key + (report_text(sp.get("preport")),)


def page_spectra(page):
    """Spektren einer Seite zusammengefasst -> Liste verschiedener Spektren (`_identity`). Mehrere gleiche Objekte
    (Ausschnitt/Inset) sind eins."""
    seen = []
    for sp in page.get("spectra") or []:
        if _identity(sp) not in [_identity(s) for s in seen]:
            seen.append(sp)
    return seen
