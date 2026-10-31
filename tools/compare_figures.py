"""Abbildungen zweier Selbsttest-Läufe pixelgenau vergleichen (UI-Änderungen dürfen die Abbildungen nie ändern).

    QT_QPA_PLATFORM=offscreen python Elucida.py --selftest vorher      # vor der Änderung (z. B. git stash)
    QT_QPA_PLATFORM=offscreen python Elucida.py --selftest nachher
    python tools/compare_figures.py vorher nachher

Vergleicht alle PNG (Pixel, sonst Bytes). Bekannt schwankend auch ohne Änderung: epr_p6.png (Fit-Startwerte).
xray_test_xtest_a.png hängt von der Vorschaugröße ab (simuliertes Drehen um 40 px), also von der Spaltenbreite.
Exit-Code 1 bei Abweichungen.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FLAKY = {"epr_p6.png"}


def pixels(p):
    try:
        return np.asarray(Image.open(p).convert("RGBA"))
    except Exception:                                  # Test-Attrappen mit .png-Endung
        return np.frombuffer(p.read_bytes(), np.uint8)


def main(a, b):
    a, b = Path(a), Path(b)
    same, diff, miss = 0, [], []
    for p in sorted(a.rglob("*.png")):
        rel = p.relative_to(a)
        q = b / rel
        if not q.exists():
            miss.append(rel)
            continue
        x, y = pixels(p), pixels(q)
        if x.shape == y.shape and (x == y).all():
            same += 1
        else:
            n = int((x != y).any(axis=-1).sum()) if x.ndim == 3 and x.shape == y.shape else -1
            diff.append((rel, n))
    for rel, n in diff:
        print(f"DIFF {rel} ({n} px){'  [bekannt schwankend]' if rel.name in FLAKY else ''}")
    for rel in miss:
        print(f"FEHLT {rel}")
    print(f"gleich {same}, verschieden {len(diff)}, fehlend {len(miss)}")
    return 1 if miss or any(rel.name not in FLAKY for rel, _ in diff) else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
