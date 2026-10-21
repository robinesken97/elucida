"""Release Notes aus CHANGELOG.md und CHANGELOG.de.md erzeugen (für den Release-Job in build.yml).

    python release_notes.py 1.16.0 > notes.md

Nimmt den Abschnitt „## <Version> – …“ aus beiden Changelogs (bis zum nächsten „## “) und setzt ihn unter
„## English“ bzw. „## Deutsch“, danach die Download-Tabelle. Fehlt die Version in einem Changelog, bricht das
Skript mit Fehler ab – so erscheint kein Release ohne Beschreibung.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

APP = "Spectravolt"
HERE = Path(__file__).resolve().parent


def section(text: str, version: str) -> str | None:
    """Inhalt unter „## <version> …“ ohne die Überschrift; None, wenn es den Abschnitt nicht gibt."""
    m = re.search(rf"^## {re.escape(version)}\b.*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return (rest[:nxt.start()] if nxt else rest).strip()


def unwrap(text: str) -> str:
    """Feste Zeilenumbrüche der Changelogs zusammenfügen: GitHub zeigt in Release Notes jeden Umbruch an."""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        cont = out and out[-1].strip() and s and not s.startswith(("-", "#", "|", "*")) \
            and not out[-1].lstrip().startswith(("#", "|"))
        if cont:
            out[-1] = out[-1].rstrip() + " " + s
        else:
            out.append(ln.rstrip())
    return "\n".join(out)


def download_table(app: str = APP) -> str:
    rows = [("Windows", "windows-x64.zip"), ("macOS Apple Silicon (M1+)", "macos-arm64.zip"),
            ("macOS Intel (macOS 14+)", "macos-x64.zip"), ("Linux (AppImage)", "linux-x64.AppImage"),
            ("Linux (folder / Ordner)", "linux-x64.tar.gz")]
    lines = ["## Download", "", "| System | File / Datei |", "|---|---|"]
    lines += [f"| {s} | `{app}-{f}` |" for s, f in rows]
    lines += ["", "The app is not code-signed; see the README for the first launch. Linux AppImage: `chmod +x`, "
              "then start. · Die App ist nicht signiert; erster Start siehe README. Linux-AppImage: `chmod +x`, "
              "dann starten."]
    return "\n".join(lines)


def notes(version: str, en: str, de: str) -> str:
    s_en, s_de = (unwrap(s) if s else s for s in (section(en, version), section(de, version)))
    missing = [n for n, s in (("CHANGELOG.md", s_en), ("CHANGELOG.de.md", s_de)) if not s]
    if missing:
        raise ValueError(f"Version {version} fehlt in {', '.join(missing)}")
    return f"## English\n\n{s_en}\n\n## Deutsch\n\n{s_de}\n\n{download_table()}\n"


def main(argv):
    version = argv[1].lstrip("v")
    en = (HERE / "CHANGELOG.md").read_text(encoding="utf-8")
    de = (HERE / "CHANGELOG.de.md").read_text(encoding="utf-8")
    sys.stdout.write(notes(version, en, de))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (IndexError, ValueError) as e:
        sys.exit(f"release_notes.py: {e}")
