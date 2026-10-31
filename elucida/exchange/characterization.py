"""elucida/exchange/characterization.py - Austauschdatei elucida.json für das Programm Characterization (Schema v1).

Characterization liest nur diese Datei (nie project.elucida) und schreibt nie in den Projektordner. Grundsätze:
- Werte als Text, so gerundet wie in Elucidas SI (found „118.0649“); der Leser rechnet nichts nach.
- Pfade relativ zum Projektordner mit „/“; nur Dateien, die im Projekt liegen und existieren.
- Felder ohne Daten fehlen ganz; neue Felder kommen ohne Versionssprung dazu (Leser ignoriert unbekannte).
- Atomar: erst elucida.json.tmp, dann umbenennen. UTF-8 ohne BOM.
Gebaut wird nur aus dem, was die Tabs ohnehin für den SI-Export liefern (si_char_parts, Zustände der Tabs).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from elucida import APP_NAME, APP_VERSION
from elucida.app import project as PRJ

FILE = "elucida.json"
FORMAT = "elucida-exchange"
SCHEMA_VERSION = 1
_IDS = {}                       # (Pfad, mtime) -> {smiles, inchikey}: RDKit nicht bei jedem Schreiben


def rel(pdir, p):
    """Pfad relativ zum Projekt („data/cv/x.DTA“) oder None, wenn außerhalb/fehlend."""
    if not p:
        return None
    try:
        p = Path(p).resolve()
        r = p.relative_to(Path(pdir).resolve())
    except (ValueError, OSError):
        return None
    return r.as_posix() if p.exists() else None


def _files(pdir, paths):
    return [r for r in (rel(pdir, p) for p in paths) if r]


def structure_ids(path) -> dict:
    """SMILES und InChIKey aus der ChemDraw-Struktur; leer bei Abkürzungen (TMS, Dipp …: Platzhalteratome) oder
    wenn RDKit die Datei nicht lesen kann – lieber kein Wert als ein falscher."""
    p = Path(path)
    if p.suffix.lower() != ".cdxml" or not p.exists():
        return {}
    key = (str(p), p.stat().st_mtime)
    if key not in _IDS:
        out = {}
        try:
            from rdkit import Chem, RDLogger
            RDLogger.DisableLog("rdApp.*")
            from elucida.core.chem import drop_label_dummies
            mols = [drop_label_dummies(m) for m in Chem.MolsFromCDXMLFile(str(p), sanitize=True, removeHs=False) if m]
            if mols:
                mol = mols[0]
                for m in mols[1:]:
                    mol = Chem.CombineMols(mol, m)
                if not any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
                    mol = Chem.RemoveHs(mol)
                    out["smiles"] = Chem.MolToSmiles(mol)
                    ik = Chem.MolToInchiKey(mol)
                    if ik:
                        out["inchikey"] = ik
        except Exception:
            out = {}
        _IDS[key] = out
    return dict(_IDS[key])


def _compound(w, pdir):
    c = w.compound or {}
    out = {}
    if c.get("name"):
        out["name"] = c["name"]
    if c.get("note"):                                  # Notiz im laufenden Projekt (z. B. „Radikalkation von 6m“)
        out["note"] = c["note"]
    if c.get("sample"):                                # Substanz übrig (Characterization: sample_available/_number)
        out["sample"] = {"available": True, **({"number": c["sample_no"]} if c.get("sample_no") else {})}
    if c.get("known"):                                 # literaturbekannt (+ Zitat/DOI)
        out["known"] = True
        if c.get("lit"):
            out["lit"] = c["lit"]
    if c.get("formula"):
        out["formula"] = c["formula"]
    if c.get("mw"):
        out["mw"] = f"{float(c['mw']):.2f}"
    s = rel(pdir, c.get("structure"))
    if s:
        out["structure"] = s
        out.update(structure_ids(c["structure"]))
    return out


def _analytics(w, pdir):
    from elucida.si import lines as SI
    a = {}
    syn = w.syn_tab
    if syn.has_content():
        d = {}
        if (syn.st.get("proc") or "").strip():
            d["procedure_html"] = syn.st["proc"]
        if rel(pdir, syn.st.get("scheme")):
            d["scheme"] = rel(pdir, syn.st["scheme"])
        a["synthesis"] = d
    if (w.compound or {}).get("oil"):                  # Öl: m.p. <25 °C
        a["mp"] = {"text": "<25 °C", "oil": True}
    elif (w.compound or {}).get("mp"):
        a["mp"] = {"text": SI.mp_text(w.compound["mp"])}   # wie in der SI (mit °C)
    nmr = []
    for s in w.nmr_tab.spectra():
        e = {"nuclei": list(s.get("nuclei") or []), "kind": s.get("kind") or "1D"}
        if len(e["nuclei"]) == 1:
            e["nucleus"] = e["nuclei"][0]
        if s.get("solvent"):
            e["solvent"] = s["solvent"]
        if s.get("temp"):
            e["temp_k"] = round(float(s["temp"]))
        for k, key in (("emf" if str(s.get("file", "")).lower().endswith(".emf") else "svg", "file"),
                       ("bruker", "bruker")):                    # Bruker: ganzer Experimentordner (seit 2.1)
            r = rel(pdir, s.get(key))
            if r:
                e[k] = r
        nmr.append(e)
    if nmr:
        a["nmr"] = nmr
    raw = [{"kind": r["kind"], "path": rel(pdir, r["path"])} for r in w.nmr_tab.st.get("raw") or [] if rel(pdir, r["path"])]
    raw += [{"kind": "mnova", "path": rel(pdir, m)} for m in w.nmr_tab.st.get("mnova") or [] if rel(pdir, m)]
    if raw:
        a["nmr_raw"] = raw
    ir = w.irms_tab.st
    if rel(pdir, ir.get("ir_file")) or rel(pdir, ir.get("ir_pdf")):
        a["ir"] = {k: rel(pdir, ir.get(src)) for k, src in (("file", "ir_file"), ("opus_pdf", "ir_pdf"))
                   if rel(pdir, ir.get(src))}
    hr = w.hrms_tab
    vals = getattr(hr, "_ms_vals", None)
    if vals or rel(pdir, hr.st.get("ms_raw")) or rel(pdir, hr.st.get("ms_file")):
        d = {}
        if vals:
            from elucida.tabs.ir_ea import ion
            adduct, calc, found = vals
            _, z, _, label = ion(hr.formula()[0], adduct)
            d["ion"] = label.replace("$_4$", "4") + ("+" if z > 0 else "−")
            d["calc"] = f"{calc:.4f}"
            if found is not None:
                d["found"] = f"{found:.4f}"
        for k, src in (("file", "ms_raw"), ("report", "ms_file")):
            if rel(pdir, hr.st.get(src)):
                d[k] = rel(pdir, hr.st[src])
        a["hrms"] = d
    if getattr(w.irms_tab, "_ea_line", ("", ""))[0]:
        formula, _ = w.irms_tab.formula()
        comp = SI.ea_composition(formula, ir.get("ea_solvate", ""))
        found = {el: str(v).strip().replace(",", ".") for el, v in (ir.get("ea_found") or {}).items()
                 if str(v).strip()}
        a["ea"] = {"calc": {el: f"{comp[el]:.2f}" for el in SI.EA_ELEMENTS if el in comp},
                   "found": {el: f"{float(v):.2f}" for el, v in found.items()}}
    if w.groups:
        a["uvvis"] = [dict(name=g, **({"solvent": (w.series.get(g) or {}).get("solvent")}
                                      if (w.series.get(g) or {}).get("solvent") else {})) for g in w.groups]
    tabs = (("cv", [e.get("file") for e in w.cv_tab.st.get("files") or []]),
            ("sec", list(w.sec_tab.st.get("spec_files") or []) + [w.sec_tab.st.get("dta")]),
            ("epr", [e.get("file") for e in w.epr_tab.st.get("entries") or []]),
            ("fluorescence", [w.fl_tab.st.get("abs_file"), w.fl_tab.st.get("em_file")]),
            ("overlay", [e.get("file") for e in w.ov_tab.st.get("entries") or []]),
            ("dft", [e.get("file") for e in w.dft_tab.entries()]))
    for key, paths in tabs:
        fs = _files(pdir, paths)
        if fs:
            a[key] = {"files": fs}
    xr = []
    xt = w.xray_tab
    for e in xt.entries():
        r = rel(pdir, e.get("file"))
        if not r:
            continue
        d = {"cif": r, "name": e.get("name") or e.get("block") or ""}
        ccdc = e.get("ccdc") or ""
        if not ccdc:
            try:
                from elucida.tabs.xray import crystal_values
                S = xt.structure(e)
                ccdc = crystal_values(S.block)["ccdc"] if S is not None else ""
            except Exception:
                ccdc = ""
        if ccdc:
            d["ccdc"] = ccdc
        xr.append(d)
    if xr:
        a["xray"] = xr
    return a


def _si(w, pdir):
    from elucida.si import lines as SI
    parts, _ = w.si_char_parts(w.compound or {})
    out = {}
    if parts:
        series = iter(g for g, _ in w.uvvis_si_parts_by_series())       # gleiche Reihenfolge wie in parts
        out["lines"] = [dict(kind=k, text=p, html=h, **({"series": next(series, "")} if k == "uvvis" else {}))
                        for k, p, h in parts]
        out["paragraph_html"] = SI.join_lines([(p, h) for _, p, h in parts])[1]
    from elucida.core.uvvis import safe_name
    docx = rel(pdir, Path(pdir) / PRJ.SI_DIR / f"{safe_name(w.export_name())}_SI.docx")
    if docx:
        out["docx"] = docx
    return out


def _figures(w, pdir):
    """Letzte Exporte in figures/: je Name ein Eintrag mit den vorhandenen Formaten und der Bildunterschrift."""
    d = Path(pdir) / PRJ.FIGURES
    if not d.is_dir():
        return []
    by_label = {lab: key for key, lab in PRJ.EXPORT_LABEL.items()}
    tabs = {t.STATE_KEY: t for t in w.figure_tabs()}
    groups = {}
    for f in sorted(d.iterdir()):
        if f.suffix.lower() in (".pdf", ".svg", ".png"):
            groups.setdefault(f.stem, {})[f.suffix.lower()[1:]] = rel(pdir, f)
    out = []
    for stem, fmts in groups.items():
        key = next((k for lab, k in by_label.items() if stem.endswith("_" + lab) or f"_{lab}_" in stem), None)
        e = {"tab": key or ""}
        e.update(fmts)
        t = tabs.get(key)
        if t is not None:
            try:
                e["caption_html"] = t.si_caption(w.export_name())
            except Exception:
                pass
        out.append(e)
    return out


def build(w) -> dict:
    """Inhalt von elucida.json aus dem Hauptfenster (Projekt muss offen sein)."""
    pdir = Path(w.project_dir)
    data = {"format": FORMAT, "schema_version": SCHEMA_VERSION,
            "app": {"name": APP_NAME, "version": APP_VERSION},
            "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for key, fn in (("compound", _compound), ("analytics", _analytics), ("si", _si), ("figures", _figures)):
        v = fn(w, pdir)
        if v:
            data[key] = v
    return data


def write(project_dir, data) -> Path:
    """Atomar schreiben. Hält Characterization die Datei gerade offen (Windows), kurz wiederholen;
    danach PermissionError (Aufrufer protokolliert nur, das Projekt ist schon gespeichert)."""
    pdir = Path(project_dir)
    dst, tmp = pdir / FILE, pdir / (FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    for k in range(5):
        try:
            os.replace(tmp, dst)
            return dst
        except PermissionError:
            if k == 4:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.1)
    return dst
