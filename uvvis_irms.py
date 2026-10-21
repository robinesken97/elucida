"""uvvis_irms.py - IR-Peakliste und HRMS-Zeile für die SI, Tab „IR + MS“.

IR:  Bruker OPUS (Binärdatei *.0, *.1 …: Spektrum + Parameterblock) oder OPUS-PDF-Ausdruck (Peakwerte als Text).
     Peaksuche in Rohdaten: Minima der Transmission (bzw. Maxima der Absorbanz) mit Mindest-Prominenz relativ zur
     stärksten Bande; Intensität optional w/m/s nach relativer Tiefe, br bei Halbwertsbreite > BROAD_CM.
MS:  Auftragsformular der Massenabteilung (Word, *.docx): Formel und Ionisierung aus dem Text, gemessene m/z aus den
     Beschriftungen der eingebetteten Spektren (EMF, EMR_EXTTEXTOUTW). calc. = monoisotopische Masse des Ions mit
     Elektronenmasse (z. B. [M+H]⁺ = M + m(H) − mₑ = M + 1.007276).
"""
from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------- Massen
ELECTRON = 0.000548579909
MONO = {  # häufigstes Isotop, IUPAC/AME
    "H": 1.00782503207, "D": 2.0141017778, "B": 11.0093054, "C": 12.0, "N": 14.0030740048, "O": 15.99491461956,
    "F": 18.99840322, "Na": 22.9897692809, "Mg": 23.985041700, "Al": 26.98153863, "Si": 27.9769265325,
    "P": 30.97376163, "S": 31.97207100, "Cl": 34.96885268, "K": 38.96370668, "Ca": 39.96259098,
    "Fe": 55.9349375, "Co": 58.9331950, "Ni": 57.9353429, "Cu": 62.9295975, "Zn": 63.9291422, "Se": 79.9165213,
    "Br": 78.9183371, "Ru": 101.9043493, "Rh": 102.905504, "Pd": 105.903486, "Ag": 106.905097, "Sn": 119.9021947,
    "I": 126.904473, "Pt": 194.9647911, "Au": 196.9665687, "Li": 7.01600455, "Cs": 132.905451933, "Ge": 73.9211778,
    "Te": 129.9062244, "Bi": 208.9803987, "Ti": 47.9479463, "Mn": 54.9380451, "Cr": 51.9405075,
}
# Addukt: (Anzeige, Änderung der Formel, Ladung)
ADDUCTS = {
    "M+H": ("[M+H]", {"H": 1}, 1), "M+Na": ("[M+Na]", {"Na": 1}, 1), "M+K": ("[M+K]", {"K": 1}, 1),
    "M+NH4": ("[M+NH$_4$]", {"N": 1, "H": 4}, 1), "M": ("[M]", {}, 1), "M-H": ("[M−H]", {"H": -1}, -1),
    "M+Cl": ("[M+Cl]", {"Cl": 1}, -1), "M-": ("[M]", {}, -1),
}


def parse_formula(text: str) -> dict:
    """'C31H21N3' / 'C18H20N2+' -> {'C': 31, …}; Ladung am Ende wird ignoriert (kommt vom Addukt)."""
    text = re.sub(r"[+\-−]+\d*$", "", str(text).replace(" ", ""))
    out = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", text):
        if el not in MONO:
            raise ValueError(f"Element {el} nicht bekannt")
        out[el] = out.get(el, 0) + (int(n) if n else 1)
    if not out:
        raise ValueError("keine Summenformel")
    return out


def formula_str(counts: dict) -> str:
    """Hill-Reihenfolge: C, H, dann alphabetisch."""
    keys = [k for k in ("C", "H", "D") if counts.get(k)] + sorted(k for k in counts if k not in ("C", "H", "D") and counts[k])
    return "".join(f"{k}{counts[k] if counts[k] != 1 else ''}" for k in keys)


def ion(formula: str, adduct: str = "M+H"):
    """-> (Ionenformel ohne Ladung, Ladung ±1, m/z calc, Addukt-Anzeige)."""
    counts = parse_formula(formula)
    label, delta, z = ADDUCTS[adduct]
    for el, n in delta.items():
        counts[el] = counts.get(el, 0) + n
    if any(v < 0 for v in counts.values()):
        raise ValueError("Addukt passt nicht zur Formel")
    m = sum(MONO[el] * n for el, n in counts.items()) - z * ELECTRON
    return formula_str(counts), z, m / abs(z), label


def ppm(found, calc):
    return (found - calc) / calc * 1e6


# ---------------------------------------------------------------------------- IR: OPUS
def _opus_params(b, off, ln):
    out, p = {}, off
    while p < off + 4 * ln and p + 8 <= len(b):
        name = b[p:p + 3].decode("latin-1")
        typ, size = struct.unpack_from("<hh", b, p + 4)
        if name == "END":
            break
        raw = b[p + 8:p + 8 + 2 * size]
        try:
            if typ == 0:
                out[name] = struct.unpack_from("<i", raw)[0]
            elif typ == 1:
                out[name] = struct.unpack_from("<d", raw)[0]
            else:
                out[name] = raw.split(b"\0")[0].decode("latin-1")
        except struct.error:
            pass
        p += 8 + 2 * size
    return out


def read_opus(path) -> dict:
    """Bruker OPUS -> dict(wn, y, kind 'T'|'A', name). Nimmt das prozessierte Spektrum (Transmission oder Absorbanz
    mit eigenem Parameterblock), sonst das erste Datenfeld mit passender Punktzahl."""
    b = Path(path).read_bytes()
    if b[:4] != b"\x0a\x0a\xfe\xfe":
        raise ValueError(f"{Path(path).name}: keine OPUS-Datei")
    n = struct.unpack_from("<i", b, 20)[0]
    blocks = [struct.unpack_from("<BBBBii", b, 24 + 12 * i) for i in range(n)]
    blocks = [((t0, t1, t2, t3), ln, off) for t0, t1, t2, t3, ln, off in blocks]
    params = {}
    for t, ln, off in blocks:                       # Parameterblöcke der Daten: Typ mit 2. Byte = 20 (Datenpar.)
        pr = _opus_params(b, off, ln) if t[0] in (31, 23, 27) or t[0] == 15 and t[1] == 0 else {}
        if "NPT" in pr and "FXV" in pr:
            params[t] = pr
    # bevorzugt: Transmission (Typ 15/20) bzw. Absorbanz, mit gleicher Kennung im Parameterblock (31,20,…)
    cands = []
    for t, ln, off in blocks:
        if t[0] in (15, 7, 11) and ln > 100:
            key = (31, t[1], t[2], t[3])
            pr = params.get(key) or params.get((23, t[1], t[2], t[3])) or params.get((27, t[1], t[2], t[3]))
            if pr:
                cands.append((t, ln, off, pr))
    if not cands:
        raise ValueError(f"{Path(path).name}: kein Spektrum gefunden")
    cands.sort(key=lambda c: (c[0][1] not in (20, 16), c[0][1] != 20, c[0][2] != 0))   # erst T, dann A
    t, ln, off, pr = cands[0]
    npt = int(pr["NPT"])
    y = np.frombuffer(b, dtype="<f4", count=npt, offset=off).astype(float) * float(pr.get("CSF", 1.0))
    wn = np.linspace(pr["FXV"], pr["LXV"], npt)
    # 2. Kennbyte 20 = Transmission (OPUS speichert sie als Anteil 0–1), 16 = Absorbanz
    kind = "A" if t[1] == 16 else "T"
    if kind == "T" and np.nanmax(y) <= 1.5:
        y = y * 100.0                                # in % wie im OPUS-Ausdruck
    return {"wn": wn, "y": y, "kind": kind, "name": Path(path).stem}


def is_opus(path) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x0a\x0a\xfe\xfe"
    except OSError:
        return False


# ---------------------------------------------------------------------------- IR: PDF
AXIS_TICKS = {0, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 100}


def read_ir_pdf(path) -> list[float]:
    """OPUS-PDF-Ausdruck -> Peaklagen [cm⁻¹] aus den Textbeschriftungen. Achsenwerte (runde Hunderter/Prozente)
    werden verworfen; Peakwerte tragen in OPUS Nachkommastellen."""
    import pymupdf
    vals = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            for w in page.get_text("words"):
                s = w[4].replace(",", ".")
                if re.fullmatch(r"\d{3,4}\.\d{1,3}", s):
                    v = float(s)
                    if 350 <= v <= 8000:
                        vals.append(v)
    return sorted(set(vals), reverse=True)


# ---------------------------------------------------------------------------- IR: Peaksuche und Text
BROAD_CM = 120.0                                    # Halbwertsbreite, ab der eine Bande „br“ heißt (O–H, N–H)


def pick_peaks(wn, y, kind="T", lo=None, hi=None, prominence=0.05, min_dist=4.0):  # noqa: C901
    """Banden im Bereich [lo, hi] (cm⁻¹): Tiefe d = 100 − T (bzw. A), lokale Maxima von d mit Prominenz
    ≥ prominence · max(d). -> [dict(wn, depth, rel, width)] absteigend nach Wellenzahl."""
    wn, y = np.asarray(wn, float), np.asarray(y, float)
    d = (100.0 - y) if kind == "T" else y.copy()
    lo = float(np.nanmin(wn)) if lo is None else lo
    hi = float(np.nanmax(wn)) if hi is None else hi
    sel = (wn >= min(lo, hi)) & (wn <= max(lo, hi)) & np.isfinite(d)
    if sel.sum() < 5:
        return []
    o = np.argsort(wn[sel])
    x, dd = wn[sel][o], d[sel][o]
    base = float(np.percentile(dd, 5))
    dd = dd - base
    dmax = float(dd.max()) or 1.0
    step = float(np.median(np.diff(x))) or 1.0
    win = max(1, int(round(min_dist / step)))
    out = []
    for i in range(1, len(x) - 1):
        a, b = max(0, i - win), min(len(x), i + win + 1)
        if dd[i] < dd[a:b].max() or dd[i] <= 0:
            continue
        # Prominenz: Tiefe über dem höheren der beiden seitlichen Minima bis zur nächsten tieferen Bande
        left = dd[:i][::-1]
        right = dd[i + 1:]
        def side_min(arr):
            m = dd[i]
            for v in arr:
                if v > dd[i]:
                    break
                m = min(m, v)
            return m
        prom = dd[i] - max(side_min(left), side_min(right))
        if prom < prominence * dmax:
            continue
        half = dd[i] / 2                             # Halbwertsbreite für „br“
        l_, r_ = i, i
        while l_ > 0 and dd[l_] > half:
            l_ -= 1
        while r_ < len(x) - 1 and dd[r_] > half:
            r_ += 1
        xi = float(x[i])                             # Lage zwischen den Messpunkten per Parabel (wie OPUS)
        den = dd[i - 1] - 2 * dd[i] + dd[i + 1]
        if den < 0:
            xi += 0.5 * (dd[i - 1] - dd[i + 1]) / den * (x[i + 1] - x[i - 1]) / 2
        out.append({"wn": xi, "depth": float(dd[i]), "rel": float(dd[i] / dmax),
                    "width": float(x[r_] - x[l_])})
    # gleiche Wellenzahl nach Rundung nur einmal
    seen, uniq = set(), []
    for p in sorted(out, key=lambda p: -p["wn"]):
        k = round(p["wn"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def intensity_tag(p, broad=BROAD_CM):
    """w/m/s nach relativer Tiefe (≥ 0.6 s, ≥ 0.3 m), „br“ bei breiten Banden."""
    t = "s" if p["rel"] >= 0.6 else ("m" if p["rel"] >= 0.3 else "w")
    return ("br " + t) if p.get("width", 0) > broad else t


def ir_line(peaks, with_intensity=False):
    """-> (Klartext, HTML) wie in der SI: IR [cm⁻¹]: ṽ = 2961, 2866, … (ganze Zahlen, absteigend)."""
    vals = sorted(peaks, key=lambda p: -p["wn"])
    items = [f"{round(p['wn']):d}" + (f" ({intensity_tag(p)})" if with_intensity and "rel" in p else "") for p in vals]
    body = ", ".join(items)
    plain = f"IR [cm-1]: ṽ = {body}"
    html = f"<b>IR</b> [cm<sup>−1</sup>]: ṽ = {body}"
    return plain, html


# ---------------------------------------------------------------------------- MS-Bericht
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
            "cdxml": Chem.MolToCDXMLBlock(mol), "n_fragments": len(mols)}


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


def nearest(mz_list, calc, max_ppm=20.0):
    """Gemessenes m/z, das am nächsten an calc liegt (innerhalb max_ppm), sonst None."""
    best = min(mz_list, key=lambda v: abs(v - calc), default=None)
    return best if best is not None and abs(ppm(best, calc)) <= max_ppm else None


def ms_line(formula, adduct, found, ionisation="ESI"):
    """-> (Klartext, HTML): HR-MS-ESI(+) calc. C18H21N2+ [M+H]+ 265.1699; found 265.1703."""
    f_ion, z, calc, label = ion(formula, adduct)
    sign = "+" if z > 0 else "−"
    lab_plain = label.replace("$_4$", "4")
    lab_html = label.replace("$_4$", "<sub>4</sub>")
    f_html = re.sub(r"(\d+)", r"<sub>\1</sub>", f_ion)
    tail = f"; found {found:.4f}." if found is not None else "; found –."
    plain = f"HR-MS-{ionisation}({sign}) calc. {f_ion}{sign} {lab_plain}{sign} {calc:.4f}{tail}"
    html = (f"<b>HR-MS-{ionisation}({sign})</b> calc. {f_html}<sup>{sign}</sup> {lab_html}<sup>{sign}</sup> "
            f"{calc:.4f}{tail}")
    return plain, html, calc


# ----------------------------------------------------------------------------
# Tab „IR + MS“
# ----------------------------------------------------------------------------
from PySide6.QtCore import QMimeData, Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,  # noqa: E402
                               QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QVBoxLayout)
import os  # noqa: E402

import uvvis_tabs as TABS  # noqa: E402
from uvvis_i18n import T  # noqa: E402
from uvvis_style import HINT_CSS, WARN_CSS, make_form  # noqa: E402

IR_COLOR = "#7a1a12"


def copy_rich(plain, html):
    """Zeile mit Formatierung (fett, hoch-/tiefgestellt) in die Zwischenablage – bleibt beim Einfügen in Word."""
    md = QMimeData()
    md.setText(plain)
    md.setHtml(html)
    QApplication.clipboard().setMimeData(md)


class IRMSTab(TABS.FigureTab):
    STATE_KEY = "irms"
    X_RANGE = (100.0, 8000.0, 0, 50.0)
    XRANGE_TEXT = "ir_xrange"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=400.0, x_max=4000.0, ymax=0.0, ir_file=None, ir_pdf=None,
                         ms_file=None, ir_lo=None, ir_hi=None, prominence=5.0, with_int=False, ir_off=[],
                         adduct="M+H", found=None, ir_labels=False)

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("ir_group"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_ir = QLabel("–")
        self.lbl_ir.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_ir)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(self.clear_ir)
        row.addWidget(self.lbl_ir, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("ir_files"), row)
        row = QHBoxLayout()
        self.sp_lo = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.sp_hi = QDoubleSpinBox(decimals=0, minimum=0, maximum=10000, singleStep=50, suffix=" cm⁻¹")
        self.cb_full = QCheckBox(T("ir_full"))
        for w_ in (self.cb_full, self.sp_lo, QLabel("–"), self.sp_hi):
            row.addWidget(w_)
        f.addRow(T("ir_range"), row)
        self.sp_prom = QDoubleSpinBox(decimals=1, minimum=0.5, maximum=50, singleStep=0.5, suffix=" %",
                                      value=st["prominence"])
        self.sp_prom.setToolTip(T("ir_prom_tip"))
        f.addRow(T("ir_prom"), self.sp_prom)
        self.cb_int = QCheckBox(T("ir_with_int"))
        self.cb_int.setToolTip(T("ir_with_int_tip"))
        self.cb_int.setChecked(st["with_int"])
        f.addRow(self.cb_int)
        self.cb_irlab = QCheckBox(T("ir_labels"))
        self.cb_irlab.setChecked(st["ir_labels"])
        f.addRow(self.cb_irlab)
        self.tbl_ir = QTableWidget(0, 3)
        self.tbl_ir.setHorizontalHeaderLabels(["", "ṽ [cm⁻¹]", T("ir_intensity")])
        self.tbl_ir.verticalHeader().setVisible(False)
        self.tbl_ir.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_ir.setMinimumHeight(160)
        self.tbl_ir.itemChanged.connect(self.ir_toggled)
        f.addRow(self.tbl_ir)
        self.txt_ir = QTextBrowser()
        self.txt_ir.setMaximumHeight(90)
        f.addRow(self.txt_ir)
        b = QPushButton(T("si_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ir_line))
        f.addRow(b)
        self.lv.addWidget(g)

        g = QGroupBox(T("ms_group"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_ms = QLabel("–")
        self.lbl_ms.setWordWrap(True)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_ms)
        row.addWidget(self.lbl_ms, 1)
        row.addWidget(b)
        f.addRow(T("ms_file"), row)
        self.lbl_formula = QLabel("–")
        self.lbl_formula.setWordWrap(True)
        f.addRow(T("compound_formula"), self.lbl_formula)
        self.btn_take = QPushButton(T("ms_take_compound"))
        self.btn_take.setToolTip(T("ms_take_compound_tip"))
        self.btn_take.clicked.connect(self.take_compound)
        f.addRow(self.btn_take)
        self.cmb_adduct = QComboBox()
        for key, (lab, _, z) in ADDUCTS.items():
            self.cmb_adduct.addItem(lab.replace("$_4$", "₄") + ("⁺" if z > 0 else "⁻"), key)
        self.cmb_adduct.setCurrentIndex(max(0, self.cmb_adduct.findData(st["adduct"])))
        f.addRow(T("ms_adduct"), self.cmb_adduct)
        self.cmb_found = QComboBox()
        self.cmb_found.setToolTip(T("ms_found_tip"))
        f.addRow(T("ms_found"), self.cmb_found)
        self.lbl_ms_info = QLabel("")
        self.lbl_ms_info.setWordWrap(True)
        f.addRow(self.lbl_ms_info)
        self.txt_ms = QTextBrowser()
        self.txt_ms.setMaximumHeight(70)
        f.addRow(self.txt_ms)
        b = QPushButton(T("si_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ms_line))
        f.addRow(b)
        self.lv.addWidget(g)

        self._ir_line = self._ms_line = ("", "")
        self.cb_full.toggled.connect(self.changed)
        for w_ in (self.sp_lo, self.sp_hi, self.sp_prom):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_int, self.cb_irlab):
            w_.toggled.connect(self.changed)
        self.cmb_adduct.currentIndexChanged.connect(self.adduct_changed)
        self.cmb_found.currentIndexChanged.connect(self.changed)
        self.sync_widgets()

    # -- Dateien --------------------------------------------------------------------
    def choose_ir(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("ir_files"), self.main.settings.value("last_dir", ""),
                                             f"{T('flt_ir')};;{T('flt_all')}")
        for p in ps:
            self.load_ir(p)

    def load_ir(self, p):
        """PDF -> Peakliste aus OPUS, OPUS-Datei -> Spektrum (eigene Peaksuche); beides darf gleichzeitig da sein."""
        p = self.main.import_file(p, "data")
        try:
            if Path(p).suffix.lower() == ".pdf":
                if not read_ir_pdf(p):
                    raise ValueError(T("ir_pdf_empty"))
                self.st["ir_pdf"] = p
            else:
                read_opus(p)
                self.st["ir_file"] = p
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ir_lo=None, ir_hi=None, ir_off=[])
        self.sync_widgets()
        self.timer.start()

    def clear_ir(self):
        self.st.update(ir_file=None, ir_pdf=None, ir_lo=None, ir_hi=None, ir_off=[])
        self.sync_widgets()
        self.timer.start()

    def choose_ms(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("ms_file"), self.main.settings.value("last_dir", ""),
                                           f"Word (*.docx);;{T('flt_all')}")
        if p:
            self.load_ms(p)

    def load_ms(self, p):
        p = self.main.import_file(p, "data")
        try:
            read_ms_docx(p)
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ms_file=p, found=None)
        self.sync_widgets()
        self.timer.start()

    def compound_changed(self):
        self.sync_widgets()
        self.timer.start()

    # -- Daten ------------------------------------------------------------------------
    def spectrum(self):
        p = self.st.get("ir_file")
        if not p or not Path(p).exists():
            return None
        return self.cache(("opus", p), lambda: read_opus(p))

    def ms_report(self):
        p = self.st.get("ms_file")
        if not p or not Path(p).exists():
            return None
        return self.cache(("msdocx", p), lambda: read_ms_docx(p))

    def ir_range(self):
        sp = self.spectrum()
        full = (float(sp["wn"].min()), float(sp["wn"].max())) if sp else (400.0, 4000.0)
        lo, hi = self.st.get("ir_lo"), self.st.get("ir_hi")
        return (full[0] if lo is None else lo, full[1] if hi is None else hi), full

    def peaks(self):
        """Peakliste im Bereich: aus dem OPUS-PDF (exakt die OPUS-Werte) oder eigene Suche im Spektrum.
        Intensitäten kommen immer aus dem Spektrum, falls vorhanden."""
        st = self.st
        (lo, hi), _ = self.ir_range()
        sp = self.spectrum()
        found = pick_peaks(sp["wn"], sp["y"], sp["kind"], lo, hi, st["prominence"] / 100) if sp else []
        if st.get("ir_pdf") and Path(st["ir_pdf"]).exists():
            vals = self.cache(("irpdf", st["ir_pdf"]), lambda: read_ir_pdf(st["ir_pdf"]))
            out = []
            for v in vals:
                if min(lo, hi) <= v <= max(lo, hi):
                    near = min(found, key=lambda q: abs(q["wn"] - v), default=None)
                    p = dict(near) if near is not None and abs(near["wn"] - v) < 3 else {}
                    p["wn"] = v
                    out.append(p)
            return out
        return found

    def formula(self):
        """Formel: Verbindung des Projekts, sonst die Struktur im MS-Bericht, sonst dessen Formelfeld."""
        c = self.main.compound
        if c.get("formula"):
            return c["formula"], "project"
        rep = self.ms_report()
        if rep and rep.get("structure"):
            return rep["structure"]["formula"], "report_struct"
        return (rep["formula"], "report") if rep and rep.get("formula") else (None, None)

    def take_compound(self):
        """Verbindung des Projekts aus dem ChemDraw-Objekt im Bericht (nur Ersatzzeichnung über RDKit)."""
        rep = self.ms_report()
        if not rep or not rep.get("structure"):
            return
        c = self.main.compound
        if c.get("structure") and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            if QMessageBox.question(self, T("compound_title"), T("ms_take_replace")) != QMessageBox.Yes:
                return
        name = rep.get("sample") or Path(self.st["ms_file"]).stem
        safe = re.sub(r"[^\w.-]+", "_", name) or "compound"
        dst = Path(self.main.project_dir) / "images" / f"{safe}_aus_MS-Bericht.cdxml"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rep["structure"]["cdxml"], encoding="utf-8")
        self.main.set_compound({"name": c.get("name") or name, "structure": str(dst),
                                "formula": rep["structure"]["formula"], "mw": round(rep["structure"]["mw"], 2)})

    # -- Oberfläche -----------------------------------------------------------------
    def sync_widgets(self):
        st = self.st
        self._loading = True
        names = [Path(p).name for p in (st.get("ir_file"), st.get("ir_pdf")) if p]
        self.lbl_ir.setText(", ".join(names) or "–")
        (lo, hi), full = self.ir_range()
        auto = st.get("ir_lo") is None and st.get("ir_hi") is None
        self.cb_full.setChecked(auto)
        self.sp_lo.setValue(lo)
        self.sp_hi.setValue(hi)
        self.sp_lo.setEnabled(not auto)
        self.sp_hi.setEnabled(not auto)
        self.sp_prom.setEnabled(self.spectrum() is not None and not st.get("ir_pdf"))
        self.cb_int.setChecked(bool(st.get("with_int")))
        self.cb_irlab.setChecked(bool(st.get("ir_labels")))
        self.sp_prom.setValue(st.get("prominence", 5.0))
        rep = self.ms_report()
        self.lbl_ms.setText((Path(st["ms_file"]).name + (f"  ({rep['sample']})" if rep and rep.get("sample") else ""))
                            if st.get("ms_file") else "–")
        self._loading = False

    def collect(self):
        st = self.st
        if self.cb_full.isChecked():
            st.update(ir_lo=None, ir_hi=None)
        else:
            st.update(ir_lo=self.sp_lo.value(), ir_hi=self.sp_hi.value())
        st.update(prominence=self.sp_prom.value(), with_int=self.cb_int.isChecked(), ir_labels=self.cb_irlab.isChecked(),
                  adduct=self.cmb_adduct.currentData(), found=self.cmb_found.currentData())
        self.sync_widgets()

    def adduct_changed(self, *_):
        if not self._loading:
            self.st["found"] = None                  # neu zuordnen
        self.changed()

    def ir_toggled(self, item):
        if self._loading or item.column() != 0:
            return
        k = item.data(Qt.UserRole)
        off = set(self.st.get("ir_off") or [])
        off.discard(k) if item.checkState() == Qt.Checked else off.add(k)
        self.st["ir_off"] = sorted(off)
        self.timer.start()

    def fill_ir_table(self, peaks):
        self._loading = True
        off = set(self.st.get("ir_off") or [])
        self.tbl_ir.setRowCount(len(peaks))
        for i, p in enumerate(peaks):
            k = round(p["wn"])
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked if k in off else Qt.Checked)
            it.setData(Qt.UserRole, k)
            self.tbl_ir.setItem(i, 0, it)
            for j, v in ((1, f"{p['wn']:.1f}"), (2, intensity_tag(p) if "rel" in p else "–")):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled)
                self.tbl_ir.setItem(i, j, it)
        self.tbl_ir.resizeColumnsToContents()
        self._loading = False

    def update_ms(self):
        st = self.st
        rep = self.ms_report()
        formula, src = self.formula()
        notes = []
        self._ms_line = ("", "")
        self.cmb_found.blockSignals(True)
        self.cmb_found.clear()
        if not formula:
            self.lbl_formula.setText(T("ms_no_formula"))
            self.txt_ms.setHtml("")
            self.cmb_found.blockSignals(False)
            self.lbl_ms_info.setText("")
            return
        self.lbl_formula.setText(f"{formula}  ({T('ms_src_' + src)})")
        try:
            _, z, calc, _ = ion(formula, st["adduct"])
        except ValueError as e:
            self.lbl_ms_info.setText(str(e))
            self.lbl_ms_info.setStyleSheet(WARN_CSS)
            self.cmb_found.blockSignals(False)
            return
        found = None
        self.btn_take.setVisible(bool(rep and rep.get("structure")))
        if rep:
            # Abgleich bevorzugt gegen die Struktur im Bericht (das Formelfeld ist von Hand getippt)
            ref_f = rep["structure"]["formula"] if rep.get("structure") else rep.get("formula")
            if ref_f and src == "project":
                try:
                    if parse_formula(ref_f) != parse_formula(formula):
                        notes.append(T("ms_formula_mismatch", rep=ref_f, prj=formula))
                except ValueError:
                    pass
            if rep.get("structure") and rep.get("formula"):
                try:
                    if parse_formula(rep["formula"]) != parse_formula(rep["structure"]["formula"]):
                        notes.append(T("ms_form_vs_struct", f=rep["formula"], s=rep["structure"]["formula"]))
                except ValueError:
                    pass
            for v in rep["mz"]:
                self.cmb_found.addItem(f"{v:.4f}  ({ppm(v, calc):+.1f} ppm)", v)
            auto = nearest(rep["mz"], calc)
            found = st.get("found") if st.get("found") in rep["mz"] else auto
            if found is not None:
                self.cmb_found.setCurrentIndex(self.cmb_found.findData(found))
            else:
                notes.append(T("ms_no_match"))
            pol = "+" if z > 0 else "-"
            if rep.get("polarity") and rep["polarity"] != pol:
                notes.append(T("ms_polarity", rep=rep["polarity"]))
        self.cmb_found.blockSignals(False)
        ionis = rep["ionisation"] if rep else "ESI"
        plain, html, calc = ms_line(formula, st["adduct"], found, ionis)
        self._ms_line = (plain, html)
        self.txt_ms.setHtml(html)
        if found is not None:
            dev = ppm(found, calc)
            notes.insert(0, T("ms_dev", ppm=f"{dev:+.1f}"))
            if abs(dev) > 5:
                notes.append(T("ms_dev_high"))
        self.lbl_ms_info.setText("\n".join(notes))
        self.lbl_ms_info.setStyleSheet(WARN_CSS if len(notes) > 1 or (found is None and rep) else HINT_CSS)

    # -- Abbildung ------------------------------------------------------------------
    def figure_spec(self):
        st = self.st
        peaks = self.peaks()
        self.fill_ir_table(peaks)
        off = set(st.get("ir_off") or [])
        use = [p for p in peaks if round(p["wn"]) not in off]
        self._ir_line = ir_line(use, st["with_int"]) if use else ("", "")
        self.txt_ir.setHtml(self._ir_line[1])
        self.update_ms()
        sp = self.spectrum()
        if sp is None:
            return None
        cfg = self.base_cfg()
        (lo, hi), _ = self.ir_range()
        x0, x1 = (st["x_min"], st["x_max"]) if not st["x_auto"] else (min(lo, hi), max(lo, hi))
        cfg["xlim"] = [x1, x0]                           # Wellenzahl fällt nach rechts (IR-Konvention)
        y = sp["y"]
        sel = (sp["wn"] >= x0) & (sp["wn"] <= x1)
        ymin, ymaxv = float(np.nanmin(y[sel])), float(np.nanmax(y[sel]))
        span = ymaxv - ymin or 1.0
        cfg["ylim"] = [ymin - 0.08 * span, st["ymax"] if st["ymax"] > 0 else ymaxv + 0.05 * span]
        cfg["xlabel"] = "wavenumber [cm$^{-1}$]"
        cfg["ylabel"] = "transmittance [%]" if sp["kind"] == "T" else "absorbance"
        cfg["legend"] = False
        curves = [{"x": sp["wn"], "y": y, "color": IR_COLOR, "label": None, "ls": "-", "lw": 1.0}]
        if use:
            px = np.array([p["wn"] for p in use])
            py = np.interp(px, sp["wn"][::-1], y[::-1])
            dy = -0.03 * span if sp["kind"] == "T" else 0.03 * span
            curves.append({"x": px, "y": py + dy, "color": "#14247a", "ls": "None", "marker": "^" if sp["kind"] == "T"
                           else "v", "ms": 3, "label": None})
        labels = []
        if st.get("ir_labels"):
            for p in use:
                labels.append({"key": f"label_ir_{round(p['wn'])}", "lam": p["wn"], "text": f"{round(p['wn'])}"})
        return cfg, curves, labels, []

    def hover_text(self, x, val, name):
        return f"ṽ = {x:.0f} cm⁻¹" + (f"    {val:.1f}" if val is not None else "")

    def export_to(self, base: Path):
        """Abbildung (falls Spektrum) und die SI-Zeilen als Text."""
        base = Path(base)
        files = []
        if self.spectrum() is not None:
            files = super().export_to(base)
        else:
            self.figure_spec()
        p = base.with_name(base.name + "_SI.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(x for x in (self._ir_line[0], self._ms_line[0]) if x) + "\n", encoding="utf-8")
        return files + [p]
