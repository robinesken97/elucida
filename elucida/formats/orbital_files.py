"""
elucida/formats/orbital_files.py - Orbitaldateien: Gaussian-Cube (Gitter, Atome; ORCA orca_plot, Gaussian cubegen) und Molden (Atome, Basis, MOs; ORCA orca_2mkl). Auswertung der Basis in elucida/core/orbitals.py.
"""
from __future__ import annotations

import numpy as np
from elucida.formats.elements import BOHR, ELEMENTS


def read_cube(path) -> dict:
    """Gaussian-Cube -> dict(title, comment, els, xyz (Å), origin (Å), axes (3×3 Å, Zeile = Schritt), data [Gitter],
    mos [Nummern oder None]). Mehrere Orbitale (Atomzahl negativ, MO-Liste) werden alle gelesen."""
    with open(path, "r", errors="replace") as f:
        title = f.readline().rstrip("\n")
        comment = f.readline().rstrip("\n")
        t = f.readline().split()
        nat = int(t[0])
        origin = np.array([float(x) for x in t[1:4]])
        nval = int(t[4]) if len(t) > 4 else 1
        n, axes = [], []
        for _ in range(3):
            t = f.readline().split()
            n.append(int(t[0]))
            axes.append([float(x) for x in t[1:4]])
        unit = BOHR if n[0] > 0 else 1.0                      # negative Punktzahl: Ångström
        n = [abs(x) for x in n]
        axes = np.array(axes) * unit
        origin = origin * unit
        els, xyz = [], []
        for _ in range(abs(nat)):
            t = f.readline().split()
            z = int(float(t[0]))
            els.append(ELEMENTS[z - 1] if 0 < z <= len(ELEMENTS) else "X")
            xyz.append([float(x) * unit for x in t[2:5]])
        mos = [None]
        rest = f.read().split()
    vals = rest
    if nat < 0:                                              # MO-Liste: Anzahl, dann Nummern
        nm = int(rest[0])
        mos = [int(x) for x in rest[1:1 + nm]]
        vals = rest[1 + nm:]
    elif nval > 1:
        mos = [None] * nval
    m = len(mos)
    need = n[0] * n[1] * n[2] * m
    if len(vals) < need:
        raise ValueError(f"cube: {len(vals)} values, expected {need}")
    a = np.array(vals[:need], dtype=np.float32).reshape(n[0], n[1], n[2], m)
    data = [np.ascontiguousarray(a[..., j]) for j in range(m)]
    return dict(title=title, comment=comment, els=els, xyz=np.array(xyz, float).reshape(-1, 3), origin=origin,
                axes=axes, data=data, mos=mos)


_L = {"s": 0, "p": 1, "d": 2, "f": 3, "g": 4, "sp": -1}


def parse_molden(text) -> dict:
    """Molden-Datei -> dict(title, els, xyz (Bohr), shells [(Atom, l, Exponenten, Koeffizienten)], pure {l: bool},
    mos [dict(sym, energy (Eh), spin "a"/"b", occ, c (Array))], orca)."""
    sec, out = None, dict(title="", els=[], xyz=[], shells=[], pure={2: False, 3: False, 4: False}, mos=[])
    lines = text.splitlines()
    unit = 1.0
    i = 0
    atom_ix = {}
    while i < len(lines):
        ln = lines[i].strip()
        low = ln.lower()
        if ln.startswith("["):
            tag = low.split("]")[0] + "]"
            sec = tag
            if tag == "[atoms]":
                unit = 1.0 if "au" in low.split("]")[1] else 1.0 / BOHR
            for flag, ls in (("[5d]", {2: True, 3: True}), ("[5d7f]", {2: True, 3: True}),
                             ("[5d10f]", {2: True, 3: False}), ("[7f]", {3: True}), ("[9g]", {4: True})):
                if tag == flag:
                    out["pure"].update(ls)
            i += 1
            continue
        if sec == "[title]" and ln:
            out["title"] += ln + " "
        elif sec == "[atoms]" and ln:
            t = ln.split()
            atom_ix[int(t[1])] = len(out["els"])
            z = int(t[2])
            out["els"].append(ELEMENTS[z - 1] if 0 < z <= len(ELEMENTS) else t[0])
            out["xyz"].append([float(v) * unit for v in t[3:6]])
        elif sec == "[gto]" and ln:
            t = ln.split()
            at = atom_ix.get(int(t[0]), int(t[0]) - 1)
            i += 1
            while i < len(lines) and lines[i].strip():
                t = lines[i].split()
                if not t[0].isalpha():
                    break
                if t[0].lower() not in _L:
                    raise ValueError(f"Molden: shell type '{t[0]}' not supported (s–g)")
                l, n = _L[t[0].lower()], int(t[1])
                ex, co = [], []
                for j in range(n):
                    v = lines[i + 1 + j].replace("D", "E").replace("d", "e").split()
                    ex.append(float(v[0]))
                    co.append([float(x) for x in v[1:]])
                if l == -1:                                       # sp-Schale: s und p mit eigenen Koeffizienten
                    out["shells"].append((at, 0, np.array(ex), np.array([c[0] for c in co])))
                    out["shells"].append((at, 1, np.array(ex), np.array([c[1] for c in co])))
                else:
                    out["shells"].append((at, l, np.array(ex), np.array([c[0] for c in co])))
                i += 1 + n
            continue
        elif sec == "[mo]" and "=" in ln:
            mo = dict(sym="", energy=0.0, spin="a", occ=0.0)
            while i < len(lines) and "=" in lines[i]:
                k, v = lines[i].split("=", 1)
                k, v = k.strip().lower(), v.strip()
                if k == "sym":
                    mo["sym"] = v
                elif k == "ene":
                    mo["energy"] = float(v.replace("D", "E"))
                elif k == "spin":
                    mo["spin"] = "b" if v.lower().startswith("beta") else "a"
                elif k == "occup":
                    mo["occ"] = float(v.replace("D", "E"))
                i += 1
            c = {}
            while i < len(lines) and lines[i].strip() and "=" not in lines[i] and not lines[i].lstrip().startswith("["):
                t = lines[i].split()
                c[int(t[0])] = float(t[1].replace("D", "E"))
                i += 1
            n = max(c) if c else 0
            mo["c"] = np.array([c.get(j + 1, 0.0) for j in range(n)])
            out["mos"].append(mo)
            continue
        i += 1
    out["xyz"] = np.array(out["xyz"], float).reshape(-1, 3)
    out["orca"] = "orca" in out["title"].lower()
    if not out["els"] or not out["shells"] or not out["mos"]:
        raise ValueError("Molden: [Atoms], [GTO] or [MO] missing")
    return out
