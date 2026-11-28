"""3D-Orbitalshader (assets/shaders/orb.vert, orb.frag) -> .qsb für QRhi (elucida/core/gpu3d.py).
python tools/make_shaders.py   (qsb liegt im PySide6-Paket; nach jeder Änderung an den Shadern ausführen, .qsb einchecken)"""
import subprocess
import sys
from pathlib import Path

import PySide6

ROOT = Path(__file__).resolve().parent.parent
SH = ROOT / "assets" / "shaders"
QSB = Path(PySide6.__file__).parent / ("qsb.exe" if sys.platform.startswith("win") else "qsb")
TARGETS = ["--glsl", "300 es,330", "--hlsl", "50", "--msl", "12"]      # GL 3.3/ES 3 (3D-Texturen), D3D11, Metal; SPIR-V immer


def main():
    jobs = [("orb.vert", "orb.vert.qsb", []), ("orb.frag", "orb1.frag.qsb", []), ("orb.frag", "orb2.frag.qsb", ["-DPASS2"])]
    for src, dst, extra in jobs:
        subprocess.run([str(QSB), *TARGETS, *extra, "-o", str(SH / dst), str(SH / src)], check=True)
        print(dst)


if __name__ == "__main__":
    main()
