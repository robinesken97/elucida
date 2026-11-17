"""elucida/formats/aicd.py - POV-Ray-Dateien des AICD-Programms (Herges, AICD 3.0.4, Aufruf mit `--povrayinput -c`,
Ordner `<Name>.d`): `Isoober.inc` (Isofläche als `mesh` aus `smooth_triangle`, Stromdichtepfeile `Pfeile` als
Zylinder + Kegel, `Magnetfeldvektor`, `Aufrufzeile`) und `Molekuel.inc` (Atome von PovChem).

Layout geprüft an einer öffentlichen echten Ausgabe (AICD-3.0.4 mit `-s`, GitHub LRG-computational/deloc-vis,
2026-11-14); anderes (z. B. `triangle` statt `smooth_triangle`, Pfeilzeilen in anderer Form) wird abgelehnt.
Gelesen wird nur, was in den Dateien steht; nichts wird nachgerechnet.
"""
from __future__ import annotations

import re

import numpy as np
from elucida.app.i18n import T

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_VEC = rf"<\s*({_NUM})\s*,\s*({_NUM})\s*,\s*({_NUM})\s*>"
_ARROW = re.compile(rf"cylinder\s*\{{\s*{_VEC}\s*,\s*{_VEC}\s*,\s*({_NUM})\s*pigment\s*\{{\s*(\w+)\s*\}}\s*\}}\s*"
                    rf"cone\s*\{{\s*{_VEC}\s*,\s*({_NUM})\s*,\s*{_VEC}\s*,\s*0\s*pigment\s*\{{\s*(\w+)\s*\}}\s*\}}"
                    rf"\s*//\s*L\S*nge:\s*({_NUM})")
_FIELD = re.compile(rf"cylinder\s*\{{\s*{_VEC}\s*,\s*{_VEC}\s*,\s*({_NUM})\s*\}}\s*cone\s*\{{\s*{_VEC}\s*,\s*({_NUM})"
                    rf"\s*,\s*{_VEC}\s*,\s*{_NUM}\s*\}}")
# PovChem schreibt englische Elementnamen; RDKit kennt die IUPAC-Schreibweise, dazu die amerikanische
_NAME_ALIAS = {"Aluminum": "Al", "Cesium": "Cs", "Sulphur": "S"}


def _section(text, name):
    """Inhalt von `#declare <name> = <typ> { … }` (Klammern gezählt) oder None."""
    m = re.search(rf"#declare\s+{name}\s*=\s*\w+\s*\{{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth and i < len(text):
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    if depth:
        raise ValueError(T("acid_bad_inc"))
    return text[m.end():i - 1]


def read_isoober(text) -> dict:
    """Isoober.inc -> dict(tri [N,3,3] Ecken, nrm [N,3,3] Normalen, arrows [M,3,3] (Anfang, Ende Zylinder, Spitze),
    r_shaft/r_head [M], colors (Zylinder, Kegel; POV-Namen), current [M] („Länge“ = Betrag laut AICD), field
    (Einheitsvektor oder None), field_geom (Anfang, Zylinderende, Spitze, r, r_Kegel) oder None, command, iso oder None)."""
    mesh = _section(text, "Isooberflaeche")
    if mesh is None:
        raise ValueError(T("acid_bad_inc"))
    n = mesh.count("smooth_triangle")
    if not n or mesh.count("triangle") != n:                       # nur smooth_triangle (geprüftes Layout)
        raise ValueError(T("acid_bad_inc"))
    nums = re.findall(_NUM, re.sub(r"smooth_triangle", " ", mesh))
    if len(nums) != 18 * n:
        raise ValueError(T("acid_bad_inc"))
    v = np.array(nums, float).reshape(n, 3, 2, 3)
    tri, nrm = v[:, :, 0], v[:, :, 1]
    arrows = np.zeros((0, 3, 3))
    r_shaft = r_head = current = np.zeros(0)
    colors = ("Green", "Red")
    pf = _section(text, "Pfeile")
    if pf is not None:
        rows = _ARROW.findall(pf)
        if len(rows) != pf.count("cylinder") or len(rows) != pf.count("cone"):
            raise ValueError(T("acid_bad_inc"))
        if rows:
            a = np.array([[float(x) for x in r[:6] + r[8:11] + r[12:15]] for r in rows]).reshape(-1, 4, 3)
            if np.abs(a[:, 1] - a[:, 2]).max() > 1e-6:                 # Kegel beginnt am Ende des Zylinders
                raise ValueError(T("acid_bad_inc"))
            arrows = a[:, [0, 1, 3]]
            r_shaft = np.array([float(r[6]) for r in rows])
            r_head = np.array([float(r[11]) for r in rows])
            current = np.array([float(r[16]) for r in rows])
            colors = (rows[0][7], rows[0][15])
    field = field_geom = None
    fv = _section(text, "Magnetfeldvektor")
    if fv is not None:
        m = _FIELD.search(fv)
        if m:
            g = [float(x) for x in m.groups()]
            p0, p1, p2 = np.array(g[0:3]), np.array(g[3:6]), np.array(g[11:14])
            d = p2 - p0
            if np.linalg.norm(d) > 0:
                field = d / np.linalg.norm(d)
                field_geom = (p0, p1, p2, g[6], g[10])
    cmd = re.search(r'#declare\s+Aufrufzeile\s*=\s*text\s*\{\s*ttf\s+"[^"]*"\s+"([^"]*)"', text)
    command = cmd.group(1).strip() if cmd else ""
    iso = None
    # interner Aufruf „… -- <Isowert> <Bx> <By> <Bz> …“: Isowert nur, wenn B dort zum Magnetfeldvektor passt
    m = re.search(rf"\s--\s+({_NUM})\s+({_NUM})\s+({_NUM})\s+({_NUM})(\s|$)", command)
    if m and field is not None:
        b = np.array([float(x) for x in m.groups()[1:4]])
        if np.linalg.norm(b) > 0 and np.allclose(b / np.linalg.norm(b), field, atol=1e-3):
            iso = float(m.group(1))
    return dict(tri=tri, nrm=nrm, arrows=arrows, r_shaft=r_shaft, r_head=r_head, colors=colors, current=current,
                field=field, field_geom=field_geom, command=command, iso=iso)


def read_molekuel(text) -> dict:
    """Molekuel.inc (PovChem) -> dict(els, xyz [Å]); Atome aus „object { Atom_<Name> translate <x, y, z> }“."""
    if "PovChem" not in text:
        raise ValueError(T("acid_bad_mol"))
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    names = {pt.GetElementName(z): pt.GetElementSymbol(z) for z in range(1, 119)}
    names.update(_NAME_ALIAS)
    els, xyz = [], []
    for name, x, y, z in re.findall(rf"object\s*\{{\s*Atom_(\w+)\s+translate\s*{_VEC}\s*\}}", text):
        if name not in names:
            raise ValueError(T("acid_bad_mol"))
        els.append(names[name])
        xyz.append([float(x), float(y), float(z)])
    if not els:
        raise ValueError(T("acid_bad_mol"))
    return dict(els=els, xyz=np.array(xyz))


def write_aicd_files(folder, els, xyz, tri, nrm, arrows, field, iso, current=None):
    """Isoober.inc + Molekuel.inc im Layout der geprüften AICD-Ausgabe schreiben (nur für erfundene Test- und
    Beispieldaten). arrows [M,3,3]: Anfang, Zylinderende, Spitze."""
    from pathlib import Path
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    f = np.asarray(field, float) / np.linalg.norm(field)
    g = lambda v: ",".join(f"{x:.5g}" for x in v)                          # noqa: E731
    L = ["// invented example data in the layout of AICD 3.0.4 (not a real calculation)",
         "#declare Magnetfeldvektor=", "union",
         f"{{ cylinder {{ < {g(-5 * f)} >,< {g(2.5 * f)} >,0.15 }}",
         f"  cone {{ < {g(2.5 * f)} >,0.3,< {g(5 * f)} >,0.0 }}", "}",
         "#declare Aufrufzeile=", "text",
         f'{{ ttf "timrom.ttf" "AICD-smooth_isosurface -s -m 0 -x 1.5 -- {iso:g} {f[0]:g} {f[1]:g} {f[2]:g} '
         f'symmaniso example.icd40000 " 1, 0', "  pigment { color Black }", "}",
         "#declare Isooberflaeche =", "mesh"]
    for k, (t, n) in enumerate(zip(tri, nrm)):
        L.append(("{  " if k == 0 else "  ") + "smooth_triangle { "
                 + ",".join(f"<{g(t[i])}>,<{g(n[i])}>" for i in range(3)) + " }")
    L += ["}", "", "#declare Pfeile =", "union"]
    cur = np.linalg.norm(arrows[:, 2] - arrows[:, 0], axis=1) if current is None else current
    for k, (a, c) in enumerate(zip(arrows, cur)):
        L.append(("{  " if k == 0 else "  ") + f"cylinder {{ <{g(a[0])}>,<{g(a[1])}>,0.0104 pigment {{ Green }}}} "
                 f"cone {{ <{g(a[1])}>,0.0208,<{g(a[2])}>,0 pigment {{ Red }}}}  // Länge: {c:g}")
    L.append("}")
    (folder / "Isoober.inc").write_text("\n".join(L) + "\n", encoding="utf-8", newline="")
    M = ["// This file was created by PovChem version 1.00", ""]
    M += [f"object {{ Atom_{pt.GetElementName(pt.GetAtomicNumber(e))} translate <{x:.4g}, {y:.4g}, {z:.4g}> }}"
          for e, (x, y, z) in zip(els, xyz)]
    (folder / "Molekuel.inc").write_text("\n".join(M) + "\n", encoding="utf-8", newline="")
    return folder / "Isoober.inc", folder / "Molekuel.inc"
