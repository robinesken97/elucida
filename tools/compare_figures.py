"""Abbildungen zweier Selbsttest-Läufe pixelgenau vergleichen (UI-Änderungen dürfen die Abbildungen nie ändern).

    QT_QPA_PLATFORM=offscreen python Elucida.py --selftest vorher      # vor der Änderung (z. B. git stash)
    QT_QPA_PLATFORM=offscreen python Elucida.py --selftest nachher
    python tools/compare_figures.py vorher nachher

Vergleicht alle PNG (Pixel, sonst Bytes). Bekannt schwankend auch ohne Änderung: epr_p6.png (Fit-Startwerte),
demo00table.png (Vorschau der Vergleichstabelle, wechselt zwischen zwei Ständen), `.elucida/thumbs/*.png`
(Vorschaubilder der Verbindungen, Robin 2026-11-21).
Dateien, deren Pfad sich nur in einem Hash/einer uid unterscheidet (Hex-Folge ab 8 Zeichen: uid eines Vergleichs,
uuid eines Reaktionspfads, NMR-Cache), werden über den Inhalt gepaart: gleich, wenn ein Kandidat mit demselben Muster
pixelgleich ist, sonst verschieden (kleinste Abweichung).
xray_test_xtest_a.png hängt von der Vorschaugröße ab (simuliertes Drehen um 40 px), also von der Spaltenbreite.
Exit-Code 1 bei Abweichungen.
"""
import collections
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FLAKY = {"epr_p6.png", "demo00table.png"}
HEX = re.compile(r"[0-9a-f]{8,}")


def flaky(rel):
    return rel.name in FLAKY or rel.parent.parts[-2:] == (".elucida", "thumbs")


def ndiff(x, y):
    """Anzahl abweichender Pixel; -1 bei anderer Größe oder ohne Bild."""
    if x.shape == y.shape and (x == y).all():
        return 0
    return int((x != y).any(axis=-1).sum()) if x.ndim == 3 and x.shape == y.shape else -1


def pixels(p):
    try:
        return np.asarray(Image.open(p).convert("RGBA"))
    except Exception:                                  # Test-Attrappen mit .png-Endung
        return np.frombuffer(p.read_bytes(), np.uint8)


def main(a, b):
    a, b = Path(a), Path(b)
    same, diff, miss = 0, [], []
    cand = collections.defaultdict(list)               # Pfadmuster (Hash -> #) -> Dateien in b
    for q in b.rglob("*.png"):
        cand[HEX.sub("#", q.relative_to(b).as_posix())].append(q)
    for p in sorted(a.rglob("*.png")):
        rel = p.relative_to(a)
        q = b / rel
        if not q.exists():
            qs = cand.get(HEX.sub("#", rel.as_posix()), []) if HEX.search(rel.as_posix()) else []
            if not qs:
                miss.append(rel)
                continue
            x, best = pixels(p), None                  # über den Inhalt gepaart: bester Kandidat zählt
            for q in qs:
                n = ndiff(x, pixels(q))
                if best is None or (n >= 0 and (best < 0 or n < best)):
                    best = n
                if n == 0:
                    break
            if best == 0:
                same += 1
            else:
                diff.append((rel, best, " [gepaart ueber Hash]"))
            continue
        n = ndiff(pixels(p), pixels(q))
        if n == 0:
            same += 1
        else:
            diff.append((rel, n, ""))
    for rel, n, how in diff:
        print(f"DIFF {rel} ({n} px){how}{'  [bekannt schwankend]' if flaky(rel) else ''}")
    for rel in miss:
        print(f"FEHLT {rel}")
    print(f"gleich {same}, verschieden {len(diff)}, fehlend {len(miss)}")
    return 1 if miss or any(not flaky(rel) for rel, _, _ in diff) else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
