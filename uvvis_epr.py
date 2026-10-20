"""uvvis_epr.py - CW-EPR: Bruker BES3T (ESR5000/ESRStudio, Elexsys), Magnettech-MS400-Text, EasySpin-Simulationen.

Verarbeitung einer Messung (Reihenfolge): Dunkelspektrum abziehen (hell − k·dunkel, auf das Feldraster der
Messung interpoliert) -> Basislinie (Polynom an den Rändern des Sweeps oder in gewählten Bereichen) ->
Bereiche ausblenden (z. B. scharfes Radikalsignal) -> Glätten (gleitender Mittelwert über ein Feldintervall)
-> optional normieren. Simulationen: Feldverschiebung, Skalierung von Hand oder per kleinsten Quadraten an
eine Messung angepasst. Felder intern in mT.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

import uvvis_tabs as TABS
from uvvis_i18n import T

MHZ_PER_CM = 29979.2458                       # 1 cm⁻¹ in MHz
MU_B_H = 13.996245                             # µ_B/h in GHz/T  -> g = ν / (µ_B/h · B)


# ----------------------------------------------------------------------------
# Lesen
# ----------------------------------------------------------------------------
def _dsc(path):
    out = {}
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_]{1,15})\s+(.*)$", ln.strip())
        if m and not ln.startswith(("*", "#", ".")):
            out[m.group(1)] = m.group(2).strip().strip("'")
    return out


def _f(h, key, default=None):
    try:
        return float(h[key])
    except (KeyError, ValueError, TypeError):
        return default


def read_bes3t(path) -> list:
    """Bruker BES3T (.DSC/.dsc + .DTA): -> [dict(B [mT], I, meta)], bei 2D je Zeile ein Spektrum.
    Unterstützt: reelle Daten, lineare x-Achse (IDX), D/F/I-Formate, Byte-Reihenfolge LIT/BIG."""
    p = Path(path)
    dsc = next((p.with_suffix(s) for s in (".dsc", ".DSC") if p.with_suffix(s).exists()), None)
    dta = next((p.with_suffix(s) for s in (".DTA", ".dta") if p.with_suffix(s).exists()), None)
    if dsc is None or dta is None:
        raise ValueError(f"{p.name}: .dsc und .DTA werden zusammen gebraucht")
    h = _dsc(dsc)
    if h.get("IKKF", "REAL") != "REAL":
        raise ValueError(f"{p.name}: komplexe Daten werden nicht unterstützt")
    nx, ny = int(_f(h, "XPTS", 0)), int(_f(h, "YPTS", 1) or 1)
    fmt = {"D": "f8", "F": "f4", "I": "i4", "S": "i2"}.get(h.get("IRFMT", "D"), "f8")
    order = "<" if h.get("BSEQ", "BIG") == "LIT" else ">"
    y = np.fromfile(dta, dtype=order + fmt).astype(float)
    if nx <= 1 or len(y) < nx * ny:
        raise ValueError(f"{p.name}: Datengröße passt nicht zur Beschreibung")
    if h.get("XTYP", "IDX") != "IDX":
        raise ValueError(f"{p.name}: nur lineare Feldachsen (XTYP IDX) werden unterstützt")
    B = _f(h, "XMIN", 0.0) + np.arange(nx) * _f(h, "XWID", 1.0) / (nx - 1)
    unit = h.get("XUNI", "G").strip().lower()
    B = B / 10.0 if unit == "g" else (B * 1000.0 if unit == "t" else B)
    yvals = None
    if ny > 1 and h.get("YTYP") == "IGD":
        ygf = next((p.with_suffix(s) for s in (".YGF", ".ygf") if p.with_suffix(s).exists()), None)
        if ygf is not None:
            yvals = np.fromfile(ygf, dtype=order + "f8")
    meta = {"mw_GHz": (_f(h, "MWFQ") or 0) / 1e9 or None, "T_K": _f(h, "STMP"),
            "mod_mT": (_f(h, "B0MA") or 0) * 1000 or None, "power_mW": (_f(h, "MWPW") or 0) * 1000 or None,
            "date": h.get("DATE", ""), "time": h.get("TIME", ""), "title": h.get("TITL", p.stem),
            "device": "Bruker BES3T"}
    out = []
    for k in range(ny):
        m = dict(meta)
        if yvals is not None and k < len(yvals):
            m["y"], m["y_name"], m["y_unit"] = float(yvals[k]), h.get("YNAM", ""), h.get("YUNI", "")
        out.append({"B": B, "I": y[k * nx:(k + 1) * nx], "meta": m})
    return out


def _ascii_xy(path):
    rows = []
    for ln in Path(path).read_text(encoding="latin-1", errors="replace").splitlines():
        parts = re.split(r"[\s,;]+", ln.strip().replace("−", "-"))
        try:
            vals = [float(v) for v in parts if v]
        except ValueError:
            continue                                   # Kopfzeile
        if len(vals) >= 2:
            rows.append(vals[:2])
    if len(rows) < 10:
        raise ValueError(f"{Path(path).name}: keine zweispaltigen Daten gefunden")
    a = np.array(rows)
    return a[:, 0], a[:, 1]


def read_ascii(path, unit=None) -> dict:
    """Zweispaltiger Text (MS400-Export, EasySpin-Simulation): B, I. Einheit aus der Kopfzeile ('[mT]', '[G]')
    oder geschätzt (Median > 1500 -> G). Mikrowellenfrequenz aus Dateinamen wie '…-9p404368-…' (GHz)."""
    p = Path(path)
    B, I = _ascii_xy(p)
    head = p.read_text(encoding="latin-1", errors="replace")[:300].lower()
    if unit is None:
        unit = "g" if ("[g]" in head or "(g)" in head) else ("mt" if "mt" in head else
                                                          ("g" if np.median(B) > 1500 else "mt"))
    B = B / 10.0 if unit == "g" else B
    o = np.argsort(B)
    mw = None
    for m in re.finditer(r"(?<![\d.])(\d{1,3})p(\d+)(?![\d])", p.stem):
        v = float(f"{m.group(1)}.{m.group(2)}")
        if 1 <= v <= 100:
            mw = v
            break
    return {"B": B[o], "I": I[o], "meta": {"mw_GHz": mw, "title": p.stem, "device": "ASCII"}}


def read_any(path) -> list:
    p = Path(path)
    if p.suffix.lower() in (".dsc", ".dta"):
        return read_bes3t(p)
    return [read_ascii(p)]


# ----------------------------------------------------------------------------
# EasySpin-Parameter
# ----------------------------------------------------------------------------
def parse_easyspin(text) -> dict:
    """MATLAB-Zeilen wie 'Sys.D = [1100 160];' -> {'Sys.D': [1100.0, 160.0], …} (nur Zahlen/Vektoren).
    Kommentare (%) werden entfernt; Zeichenketten und Funktionsaufrufe bleiben als Text."""
    out = {}
    for ln in str(text).splitlines():
        ln = ln.split("%")[0].strip().rstrip(";")
        m = re.match(r"^((?:Sys|Exp|Opt|Fit\w*|Vary)\w*\.\w+)\s*=\s*(.+)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val)
        if val.startswith("[") or re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", val):
            out[key] = [float(x) for x in nums]
        else:
            out[key] = val
    return out


def zfs_summary(params) -> str | None:
    """D und E (EasySpin: MHz) in cm⁻¹ und MHz; None ohne Sys.D."""
    d = params.get("Sys.D")
    if not isinstance(d, list) or not d:
        return None
    D, E = d[0], (d[1] if len(d) > 1 else 0.0)
    return (f"D = {D / MHZ_PER_CM:.4f} cm⁻¹ ({D:.0f} MHz), |E| = {abs(E) / MHZ_PER_CM:.4f} cm⁻¹ "
            f"({abs(E):.0f} MHz), E/D = {abs(E / D) if D else 0:.3f}")


# ----------------------------------------------------------------------------
# Verarbeitung
# ----------------------------------------------------------------------------
def ranges(text):
    """'330-340, 480–485' -> [(330, 340), (480, 485)] (mT)."""
    out = []
    for part in str(text).replace(";", ",").split(","):
        m = re.match(r"^\s*([-+]?\d*\.?\d+)\s*[-–—]\s*([-+]?\d*\.?\d+)\s*$", part.replace("−", "-"))
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            out.append((min(a, b), max(a, b)))
    return out


def baseline(B, I, order=1, edge=0.05, regions=None):
    """Polynom der Ordnung order an signalfreie Punkte: gewählte Bereiche oder die äußeren edge-Anteile."""
    if order < 0:
        return np.zeros_like(I)
    if regions:
        m = np.zeros(len(B), bool)
        for a, b in regions:
            m |= (B >= a) & (B <= b)
    else:
        n = max(3, int(edge * len(B)))
        m = np.zeros(len(B), bool)
        m[:n] = m[-n:] = True
    m &= np.isfinite(I)
    if m.sum() <= order + 1:
        return np.zeros_like(I)
    x0, s = B.mean(), (np.ptp(B) or 1.0)
    c = np.polyfit((B[m] - x0) / s, I[m], order)
    return np.polyval(c, (B - x0) / s)


def smooth(B, I, width_mT):
    """Gleitender Mittelwert über width_mT (ungerade Punktzahl), NaN-sicher."""
    if not width_mT or len(B) < 3:
        return I
    step = float(np.median(np.diff(B))) or 1.0
    n = int(round(width_mT / step)) | 1
    if n < 3:
        return I
    ok = np.isfinite(I).astype(float)
    k = np.ones(n)
    num = np.convolve(np.nan_to_num(I), k, "same")
    den = np.convolve(ok, k, "same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[~np.isfinite(I)] = np.nan
    return out


def decimate(B, I, max_points=6000):
    """Für die Abbildung auf höchstens max_points mitteln (60 000 Punkte pro Spektrum sind üblich)."""
    if len(B) <= max_points:
        return B, I
    f = int(np.ceil(len(B) / max_points))
    n = len(B) // f * f
    with np.errstate(invalid="ignore"):
        return B[:n].reshape(-1, f).mean(1), np.nanmean(I[:n].reshape(-1, f), 1)


def fit_scale(B_ref, I_ref, B, I):
    """Skalierung s, sodass s·I (auf B_ref interpoliert) am besten zu I_ref passt (kleinste Quadrate)."""
    yi = np.interp(B_ref, B, I, left=np.nan, right=np.nan)
    ok = np.isfinite(yi) & np.isfinite(I_ref)
    den = float(np.sum(yi[ok] ** 2))
    return float(np.sum(yi[ok] * I_ref[ok]) / den) if den > 0 else 1.0


def g_value(mw_GHz, B_mT):
    return mw_GHz / (MU_B_H * B_mT / 1000.0)


# ----------------------------------------------------------------------------
# EPR-Tab
# ----------------------------------------------------------------------------
def _labels(text):
    """'Z⁻@122, Y⁺@400' -> [('Z⁻', 122.0), ('Y⁺', 400.0)] (Feld in der Achseneinheit)."""
    out = []
    for part in str(text).split(","):
        if "@" in part:
            name, _, pos = part.rpartition("@")
            try:
                out.append((name.strip(), float(pos.strip().replace("\u2212", "-"))))
            except ValueError:
                pass
    return out


class EPRTab(TABS.FigureTab):
    STATE_KEY = "epr"
    X_RANGE = (0.0, 20000.0, 1, 1.0)
    XRANGE_TEXT = "epr_xrange"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=300.0, x_max=360.0, ymax=0.0, entries=[], unit="mT",
                         bl_order=1, bl_edge=5.0, bl_regions="", exclude="", smooth=0.0, normalize=True,
                         stack=False, gap=1.2, labels="", show_params=False, y_axis="no_numbers")

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("epr_entries"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("epr_add_exp"), self.add_exp), (T("epr_add_sim"), self.add_sim),
                        ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)), (T("remove"), self.remove)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), T("ov_type"), "T [K]"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(150)
        self.table.itemChanged.connect(self.table_edited)
        self.table.itemSelectionChanged.connect(self.show_details)
        v.addWidget(self.table)
        self.lv.addWidget(g)

        self.det = QGroupBox(T("ov_details"))
        f = QFormLayout(self.det)
        row = QHBoxLayout()
        self.cmb_dark = QComboBox()
        self.cmb_dark.setToolTip(T("epr_dark_tip"))
        self.sp_dark_k = QDoubleSpinBox(decimals=3, minimum=0, maximum=100, singleStep=0.05, value=1.0)
        row.addWidget(self.cmb_dark, 1)
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_dark_k)
        self.lbl_dark = QLabel(T("epr_dark"))
        f.addRow(self.lbl_dark, row)
        self.cmb_fit = QComboBox()
        self.cmb_fit.setToolTip(T("epr_fit_tip"))
        self.lbl_fit = QLabel(T("epr_fit_to"))
        f.addRow(self.lbl_fit, self.cmb_fit)
        row = QHBoxLayout()
        self.sp_scale = QDoubleSpinBox(decimals=4, minimum=-1e9, maximum=1e9, singleStep=0.1, value=1.0)
        self.sp_shift = QDoubleSpinBox(decimals=3, minimum=-100, maximum=100, singleStep=0.05, value=0.0,
                                       suffix=" mT")
        row.addWidget(QLabel("×"))
        row.addWidget(self.sp_scale)
        row.addWidget(QLabel(T("epr_shift")))
        row.addWidget(self.sp_shift)
        self.lbl_scale = QLabel(T("epr_scale"))
        f.addRow(self.lbl_scale, row)
        row = QHBoxLayout()
        self.lbl_params = QLabel("–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        b1.clicked.connect(self.choose_params)
        b2.clicked.connect(lambda: self.set_params(None))
        for w_ in (self.lbl_params, b1, b2):
            row.addWidget(w_, 1 if w_ is self.lbl_params else 0)
        self.lbl_params_row = QLabel(T("epr_params"))
        f.addRow(self.lbl_params_row, row)
        self.lbl_meta = QLabel("")
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_meta.setStyleSheet("color: gray;")
        f.addRow(self.lbl_meta)
        for w_ in (self.sp_dark_k, self.sp_scale, self.sp_shift):
            w_.valueChanged.connect(self.detail_changed)
        for w_ in (self.cmb_dark, self.cmb_fit):
            w_.currentIndexChanged.connect(self.detail_changed)
        self.lv.addWidget(self.det)

        g = QGroupBox(T("epr_processing"))
        f = QFormLayout(g)
        row = QHBoxLayout()
        self.sp_bl_order = QSpinBox(minimum=-1, maximum=5, value=st["bl_order"])
        self.sp_bl_order.setSpecialValueText(T("off"))
        self.sp_bl_edge = QDoubleSpinBox(decimals=1, minimum=1, maximum=45, singleStep=1, value=st["bl_edge"],
                                         suffix=" %")
        row.addWidget(self.sp_bl_order)
        row.addWidget(QLabel(T("epr_bl_edge")))
        row.addWidget(self.sp_bl_edge)
        f.addRow(T("epr_bl_order"), row)
        self.ed_bl_regions = QLineEdit(st["bl_regions"])
        self.ed_bl_regions.setPlaceholderText(T("epr_regions_ph"))
        self.ed_bl_regions.setToolTip(T("epr_bl_regions_tip"))
        f.addRow(T("epr_bl_regions"), self.ed_bl_regions)
        self.ed_exclude = QLineEdit(st["exclude"])
        self.ed_exclude.setPlaceholderText(T("epr_regions_ph"))
        self.ed_exclude.setToolTip(T("epr_exclude_tip"))
        f.addRow(T("epr_exclude"), self.ed_exclude)
        self.sp_smooth = QDoubleSpinBox(decimals=2, minimum=0, maximum=50, singleStep=0.05, value=st["smooth"],
                                        suffix=" mT")
        self.sp_smooth.setSpecialValueText(T("off"))
        f.addRow(T("epr_smooth"), self.sp_smooth)
        self.lv.addWidget(g)

        g = QGroupBox(T("epr_display"))
        f = QFormLayout(g)
        self.cmb_unit = QComboBox()
        for u in ("mT", "G"):
            self.cmb_unit.addItem(u, u)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["unit"])))
        f.addRow(T("epr_unit"), self.cmb_unit)
        self.cb_norm = QCheckBox(T("epr_normalize"))
        self.cb_norm.setChecked(st["normalize"])
        f.addRow(self.cb_norm)
        row = QHBoxLayout()
        self.cb_stack = QCheckBox(T("ov_stack"))
        self.cb_stack.setChecked(st["stack"])
        self.sp_gap = QDoubleSpinBox(decimals=2, minimum=0, maximum=1e6, singleStep=0.1, value=st["gap"])
        row.addWidget(self.cb_stack)
        row.addWidget(QLabel(T("ov_gap")))
        row.addWidget(self.sp_gap)
        row.addStretch(1)
        f.addRow(row)
        self.cmb_yaxis = QComboBox()
        for key in ("numbers", "no_numbers", "off"):
            self.cmb_yaxis.addItem(T("yaxis_" + key), key)
        self.cmb_yaxis.setCurrentIndex(max(0, self.cmb_yaxis.findData(st["y_axis"])))
        f.addRow(T("ov_yaxis"), self.cmb_yaxis)
        self.ed_labels = QLineEdit(st["labels"])
        self.ed_labels.setPlaceholderText(T("epr_labels_ph"))
        self.ed_labels.setToolTip(T("epr_labels_tip"))
        f.addRow(T("epr_labels"), self.ed_labels)
        self.cb_params = QCheckBox(T("epr_show_params"))
        self.cb_params.setChecked(st["show_params"])
        f.addRow(self.cb_params)
        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.lbl_info)
        self.lv.addWidget(g)
        for w_ in (self.sp_bl_order, self.sp_bl_edge, self.sp_smooth, self.sp_gap):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_norm, self.cb_stack, self.cb_params):
            w_.toggled.connect(self.changed)
        for w_ in (self.cmb_unit, self.cmb_yaxis):
            w_.currentIndexChanged.connect(self.changed)
        for ed in (self.ed_bl_regions, self.ed_exclude, self.ed_labels):
            ed.editingFinished.connect(self.changed)
        self.fill_table()
        self.show_details()

    def collect(self):
        self.st.update(unit=self.cmb_unit.currentData(), bl_order=self.sp_bl_order.value(),
                       bl_edge=self.sp_bl_edge.value(), bl_regions=self.ed_bl_regions.text().strip(),
                       exclude=self.ed_exclude.text().strip(), smooth=self.sp_smooth.value(),
                       normalize=self.cb_norm.isChecked(), stack=self.cb_stack.isChecked(), gap=self.sp_gap.value(),
                       y_axis=self.cmb_yaxis.currentData(), labels=self.ed_labels.text().strip(),
                       show_params=self.cb_params.isChecked())

    # -- Einträge ------------------------------------------------------------------
    def data(self, path):
        return self.cache(("epr", path), lambda: read_any(path))

    def spectrum(self, e):
        d = self.data(e["file"])
        return d[min(e.get("slice", 0), len(d) - 1)]

    def _new(self, kind, path, k=0, n=1):
        d = self.data(path)[k]
        name = Path(path).stem if n == 1 else f"{Path(path).stem} [{k + 1}]"
        return {"uid": uuid.uuid4().hex[:8], "kind": kind, "file": path, "slice": k, "label": name,
                "color": "#000000" if kind == "exp" else "#e8238a", "visible": True, "dark": None, "dark_k": 1.0,
                "fit_to": None, "scale": 1.0, "shift": 0.0, "params": None, "T": d["meta"].get("T_K")}

    def _pick(self, title, flt):
        if not self.main.ensure_project():
            return []
        ps, _ = QFileDialog.getOpenFileNames(self, title, self.main.settings.value("last_dir", ""), flt)
        return ps

    def add_exp(self):
        ps = self._pick(T("epr_add_exp"), "EPR (*.dsc *.DSC *.DTA *.txt *.asc *.csv);;" + T("flt_all"))
        seen = set()
        for p in ps:
            stem = str(Path(p).with_suffix(""))
            if stem in seen:                               # .dsc und .DTA derselben Messung nur einmal
                continue
            seen.add(stem)
            try:
                if Path(p).suffix.lower() in (".dsc", ".dta"):
                    for ext in (".dsc", ".DSC", ".DTA", ".dta", ".YGF", ".ygf", ".xml"):
                        if Path(stem + ext).exists() and ext.lower() != Path(p).suffix.lower():
                            self.main.import_file(stem + ext, "data")
                p = self.main.import_file(p, "data")
                d = self.data(p)
            except Exception as ex:
                self.main.error(str(ex))
                continue
            for k in range(len(d)):
                self.st["entries"].append(self._new("exp", p, k, len(d)))
        self.fill_table()
        self.timer.start()

    def add_sim(self):
        for p in self._pick(T("epr_add_sim"), "ASCII (*.txt *.asc *.dat *.csv);;" + T("flt_all")):
            try:
                p = self.main.import_file(p, "data")
                self.data(p)
            except Exception as ex:
                self.main.error(str(ex))
                continue
            e = self._new("sim", p)
            exp = [x for x in self.st["entries"] if x["kind"] == "exp"]
            e["fit_to"] = exp[-1]["uid"] if exp else None
            self.st["entries"].append(e)
        self.fill_table()
        self.timer.start()

    def move(self, d):
        r, es = self.table.currentRow(), self.st["entries"]
        if 0 <= r < len(es) and 0 <= r + d < len(es):
            es[r], es[r + d] = es[r + d], es[r]
            self.fill_table()
            self.table.selectRow(r + d)
            self.timer.start()

    def remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["entries"]):
            uid = self.st["entries"][r]["uid"]
            del self.st["entries"][r]
            for e in self.st["entries"]:                  # Verweise aufheben
                e["dark"] = None if e.get("dark") == uid else e.get("dark")
                e["fit_to"] = None if e.get("fit_to") == uid else e.get("fit_to")
            self.fill_table()
            self.timer.start()

    def fill_table(self):
        self._loading = True
        es = self.st["entries"]
        self.table.setRowCount(len(es))
        for i, e in enumerate(es):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(e["color"], lambda c, e=e: self._set_color(e, c)))
            for j, txt in ((3, T("epr_kind_" + e["kind"])), (4, f"{e['T']:.0f}" if e.get("T") else "–")):
                it = QTableWidgetItem(txt)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, it)
        self.table.resizeColumnToContents(0)
        self._loading = False

    def _set_color(self, e, c):
        e["color"] = c
        self.timer.start()

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["entries"][item.row()]
        if item.column() == 0:
            e["visible"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text()
        self.timer.start()

    def current(self):
        r = self.table.currentRow()
        return self.st["entries"][r] if 0 <= r < len(self.st["entries"]) else None

    def show_details(self):
        e = self.current()
        self.det.setEnabled(e is not None)
        self._loading = True
        exp = e is not None and e["kind"] == "exp"
        for w_ in (self.lbl_dark, self.cmb_dark, self.sp_dark_k):
            w_.setVisible(exp or e is None)
        for w_ in (self.lbl_fit, self.cmb_fit, self.lbl_scale, self.sp_scale, self.sp_shift, self.lbl_params_row,
                   self.lbl_params):
            w_.setVisible(e is not None and not exp)
        others = [x for x in self.st["entries"] if e is None or x["uid"] != e["uid"]]
        for cmb, key in ((self.cmb_dark, "dark"), (self.cmb_fit, "fit_to")):
            cmb.clear()
            cmb.addItem(T("epr_none"), None)
            for x in others:
                if x["kind"] == "exp":
                    cmb.addItem(x["label"], x["uid"])
            cmb.setCurrentIndex(max(0, cmb.findData(e.get(key) if e else None)))
        if e:
            self.sp_dark_k.setValue(e.get("dark_k", 1.0))
            self.sp_scale.setValue(e.get("scale", 1.0))
            self.sp_scale.setEnabled(not e.get("fit_to"))
            self.sp_shift.setValue(e.get("shift", 0.0))
            self.lbl_params.setText(Path(e["params"]).name if e.get("params") else "–")
            self.lbl_meta.setText(self.meta_text(e))
        self._loading = False

    def meta_text(self, e):
        m = self.spectrum(e)["meta"]
        parts = []
        for key, fmt in (("mw_GHz", "ν = {:.5f} GHz"), ("T_K", "T = {:.1f} K"), ("mod_mT", "B_mod = {:.3f} mT"),
                         ("power_mW", "P = {:.3g} mW")):
            if m.get(key):
                parts.append(fmt.format(m[key]))
        if m.get("date") or m.get("time"):
            parts.append(f"{m.get('date', '')} {m.get('time', '')}".strip())
        txt = ", ".join(parts)
        if e.get("params"):
            try:
                pr = parse_easyspin(Path(e["params"]).read_text(encoding="utf-8", errors="replace"))
                z = zfs_summary(pr)
                txt += ("\n" + z) if z else ""
                g = pr.get("Sys.g")
                if isinstance(g, list) and g:
                    txt += "\n" + "g = " + ", ".join(f"{v:.4f}" for v in g)
            except OSError:
                pass
        return txt

    def detail_changed(self, *_):
        e = self.current()
        if self._loading or e is None:
            return
        if e["kind"] == "exp":
            e.update(dark=self.cmb_dark.currentData(), dark_k=self.sp_dark_k.value())
        else:
            e.update(fit_to=self.cmb_fit.currentData(), scale=self.sp_scale.value(), shift=self.sp_shift.value())
            self.sp_scale.setEnabled(not e["fit_to"])
        self.timer.start()

    def choose_params(self):
        e = self.current()
        if e is None or not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("epr_params"), self.main.settings.value("last_dir", ""),
                                           "EasySpin (*.txt *.m);;" + T("flt_all"))
        if p:
            self.set_params(self.main.import_file(p, "data"))

    def set_params(self, p):
        e = self.current()
        if e is None:
            return
        e["params"] = p
        self.show_details()
        self.timer.start()

    # -- Verarbeitung und Abbildung -----------------------------------------------------
    def processed(self, e, cache):
        """Messung oder Simulation nach allen Schritten -> (B [mT], I) auf dem Raster der Datei."""
        if e["uid"] in cache:
            return cache[e["uid"]]
        st = self.st
        s = self.spectrum(e)
        B, I = s["B"].astype(float), s["I"].astype(float).copy()
        if e["kind"] == "exp":
            dark = next((x for x in st["entries"] if x["uid"] == e.get("dark")), None)
            if dark is not None:
                ds = self.spectrum(dark)
                I = I - e.get("dark_k", 1.0) * np.interp(B, ds["B"], ds["I"], left=np.nan, right=np.nan)
            I = I - baseline(B, I, st["bl_order"], st["bl_edge"] / 100.0, ranges(st["bl_regions"]) or None)
            for a, b in ranges(st["exclude"]):
                I[(B >= a) & (B <= b)] = np.nan
            I = smooth(B, I, st["smooth"])
        else:
            B = B + e.get("shift", 0.0)
            target = next((x for x in st["entries"] if x["uid"] == e.get("fit_to")), None)
            if target is not None:
                tb, ti = self.processed(target, cache)
                I = I * fit_scale(tb, ti, B, I)
            else:
                I = I * e.get("scale", 1.0)
        cache[e["uid"]] = (B, I)
        return B, I

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["entries"] if e["visible"]]
        if not vis:
            self.lbl_info.setText("")
            return None
        cfg = self.base_cfg()
        fac = 10.0 if st["unit"] == "G" else 1.0
        cache, curves, info = {}, [], []
        # Normierung: Messung auf max |I| = 1; Simulation mit dem Faktor ihrer Messung (Verhältnis bleibt)
        norm = {}
        for e in vis:
            B, I = self.processed(e, cache)
            ref = e if e["kind"] == "exp" else next((x for x in st["entries"] if x["uid"] == e.get("fit_to")), e)
            rb, ri = self.processed(ref, cache)
            norm[e["uid"]] = (1.0 / np.nanmax(np.abs(ri))) if (st["normalize"] and np.nanmax(np.abs(ri)) > 0) else 1.0
        levels, lev = {}, -1
        for e in vis:                                     # Simulation auf der Ebene ihrer Messung
            if e["kind"] == "sim" and e.get("fit_to") in levels:
                levels[e["uid"]] = levels[e["fit_to"]]
            else:
                lev += 1
                levels[e["uid"]] = lev
        n_lev = lev + 1
        span = st["gap"] if st["normalize"] else st["gap"] * max(np.nanmax(np.abs(self.processed(e, cache)[1])) for e in vis)
        for e in vis:
            B, I = self.processed(e, cache)
            Bd, Id = decimate(B * fac, I * norm[e["uid"]])
            off = (n_lev - 1 - levels[e["uid"]]) * span if st["stack"] else 0.0
            curves.append({"x": Bd, "y": Id + off, "val": Id, "color": e["color"], "label": e["label"],
                           "ls": "--" if e["kind"] == "sim" else "-", "lw": 1.2 if e["kind"] == "sim" else 1.0})
            if e["kind"] == "exp" and e.get("dark"):
                m1, m2 = self.spectrum(e)["meta"], self.spectrum(
                    next(x for x in st["entries"] if x["uid"] == e["dark"]))["meta"]
                for key, tol, name in (("mw_GHz", 2e-4, "ν"), ("mod_mT", 1e-6, "B_mod"), ("power_mW", 1e-6, "P")):
                    if m1.get(key) and m2.get(key) and abs(m1[key] - m2[key]) > tol * max(1, abs(m1[key])):
                        info.append(T("epr_dark_mismatch", name=e["label"], what=name))
        allx = np.concatenate([c["x"] for c in curves])
        cfg["xlim"] = [float(np.nanmin(allx)), float(np.nanmax(allx))] if st["x_auto"] else [st["x_min"], st["x_max"]]
        ally = np.concatenate([c["y"] for c in curves])
        lo_, hi_ = float(np.nanmin(ally)), float(np.nanmax(ally))
        pad = 0.08 * ((hi_ - lo_) or 1.0)
        cfg["ylim"] = [lo_ - pad, st["ymax"] if st["ymax"] > 0 else hi_ + 2 * pad]
        cfg["xlabel"] = f"magnetic field [{st['unit']}]"
        cfg["ylabel"] = ("normalized " if st["normalize"] else "") + "EPR intensity [arb. u.]"
        cfg["y_axis"] = st["y_axis"]
        labels = [{"key": f"label_epr_{k}", "lam": pos, "text": name} for k, (name, pos) in enumerate(_labels(st["labels"]))]
        if st["show_params"]:
            for e in vis:
                if e["kind"] == "sim" and e.get("params") and Path(e["params"]).exists():
                    pr = parse_easyspin(Path(e["params"]).read_text(encoding="utf-8", errors="replace"))
                    d = pr.get("Sys.D")
                    if isinstance(d, list) and d:
                        txt = f"D = {d[0] / MHZ_PER_CM:.3f} cm$^{{-1}}$"
                        if len(d) > 1:
                            txt += f"\n|E| = {abs(d[1]) / MHZ_PER_CM:.4f} cm$^{{-1}}$"
                        labels.append({"key": f"label_zfs_{e['uid']}", "lam": float(np.mean(cfg["xlim"])), "text": txt,
                                       "color": e["color"]})
        self.lbl_info.setText("\n".join(dict.fromkeys(info)))
        self._mw = next((self.spectrum(e)["meta"].get("mw_GHz") for e in vis if e["kind"] == "exp"
                         and self.spectrum(e)["meta"].get("mw_GHz")), None)
        return cfg, curves, labels, []

    def hover_text(self, x, val, name):
        unit = self.st["unit"]
        B_mT = x / (10.0 if unit == "G" else 1.0)
        g = f"    g = {g_value(self._mw, B_mT):.4f}" if getattr(self, "_mw", None) and B_mT > 0 else ""
        if val is None:
            return f"B = {x:.2f} {unit}{g}"
        return f"B = {x:.2f} {unit}{g}    I = {val:.3g}    {name}"
