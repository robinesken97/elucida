"""
elucida/formats/ms_report.py - Bericht der Massenabteilung (.docx): Text, Beschriftungen der EMF-Spektren, ChemDraw-Objekt (CDX).
"""
from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path


def _emf_texts(data: bytes) -> list[str]:
    """Alle EMR_EXTTEXTOUTW-Texte eines EMF (Beschriftungen der Spektren aus der Massenabteilung)."""
    out, p = [], 0
    while p + 8 <= len(data):
        typ, size = struct.unpack_from("<II", data, p)
        if size < 8 or p + size > len(data):
            break
        if typ == 84 and size >= 76:
            n, off = struct.unpack_from("<II", data, p + 44)
            if 0 < n < 4096 and p + off + 2 * n <= len(data):
                out.append(data[p + off:p + off + 2 * n].decode("utf-16-le", "replace"))
        p += size
    return out


def cdx_structure(blob: bytes) -> dict | None:
    """ChemDraw-Objekt (CDX-Binärdaten) -> dict(formula, mw, cdxml) über RDKit; None, wenn nicht lesbar.
    cdxml ist eine RDKit-Umwandlung (Ersatzzeichnung), nicht ChemDraws eigene Darstellung."""
    import tempfile
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        if not Chem.HasChemDrawCDXSupport():
            return None
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "obj.cdx"
            f.write_bytes(blob)
            prm = Chem.CDXMLParserParams()
            prm.format = Chem.CDXMLFormat.CDX
            mols = [m for m in Chem.MolsFromCDXMLFile(str(f), prm) if m is not None]
    except Exception:
        return None
    if not mols:
        return None
    mol = mols[0]
    for m in mols[1:]:
        mol = Chem.CombineMols(mol, m)
    return {"formula": rdMolDescriptors.CalcMolFormula(mol, True, True), "mw": float(Descriptors.MolWt(mol)),
            "cdxml": Chem.MolToCDXMLBlock(mol) if hasattr(Chem, "MolToCDXMLBlock") else None,   # ältere RDKit
            "n_fragments": len(mols)}


def _docx_cdx(z: zipfile.ZipFile) -> bytes | None:
    """Erstes eingebettetes ChemDraw-Objekt (OLE-Container mit Stream CONTENTS = CDX) eines docx."""
    import io
    try:
        import olefile
    except ImportError:
        return None
    for n in z.namelist():
        if n.startswith("word/embeddings/") and n.lower().endswith(".bin"):
            try:
                ole = olefile.OleFileIO(io.BytesIO(z.read(n)))
                if ole.exists("CONTENTS"):
                    data = ole.openstream("CONTENTS").read()
                    if data[:8] == b"VjCD0100":
                        return data
            except Exception:
                continue
    return None


def read_ms_docx(path) -> dict:
    """Auftragsformular (docx) -> dict(sample, formula, exact_mass, ionisation, polarity, mz [found], remark,
    structure = Formel/Molmasse aus dem eingebetteten ChemDraw-Objekt oder None)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
        emf = [z.read(n) for n in z.namelist() if n.startswith("word/media/") and n.lower().endswith(".emf")]
        cdx = _docx_cdx(z)
    paras = [re.sub(r"<[^>]+>", "", p) for p in xml.split("</w:p>")]
    paras = [re.sub(r"\s+", " ", p.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")).strip()
             for p in paras]
    paras = [p for p in paras if p]

    def field(key):
        for i, p in enumerate(paras):
            if p.lower().startswith(key):
                rest = p[len(key):].strip(" :")
                return rest or (paras[i + 1] if i + 1 < len(paras) else "")
        return ""
    ionisation = ""
    for p in paras:
        if p.lower().startswith("method of ionisation") or "ESI" in p and "☒" in p:
            m = re.search(r"(ESI|APCI|HESI|EI|MALDI)\s*☒", p)
            if m:
                ionisation = m.group(1)
                break
    texts, mz, polarity = [], [], ""
    for blob in emf:
        tt = _emf_texts(blob)
        texts.append(tt)
        if "m/z" not in tt:                          # nur Spektren, nicht das Formelbild (exakte Masse, Molmasse)
            continue
        for t in tt:
            if re.search(r"\+MS", t):
                polarity = "+"
            elif re.search(r"-MS", t):
                polarity = polarity or "-"
            s = t.strip().replace(",", ".")
            if re.fullmatch(r"\d{2,5}\.\d{3,5}", s):
                mz.append(float(s))
        # Formelbild (ChemDraw im Formular): „C | 31 | H | 21 | N | 3“ -> Formel
    formula = re.sub(r"\s", "", field("molecular formula"))
    if not formula:
        for tt in texts:
            j = " ".join(tt)
            m = re.search(r"Formula:\s*((?:[A-Z][a-z]?\s*\d*\s*)+)", j)
            if m:
                formula = re.sub(r"\s", "", m.group(1))
                break
    exact = field("exact mass").replace(",", ".")
    struct_ = cdx_structure(cdx) if cdx else None
    return {"sample": field("sample name"), "formula": formula, "structure": struct_,
            "exact_mass": float(exact) if re.fullmatch(r"\d+(\.\d+)?", exact) else None,
            "ionisation": ionisation or "ESI", "polarity": polarity or "+",
            "mz": sorted(set(mz)), "remark": field("magnification") or field("remarks")}
