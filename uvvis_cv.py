"""uvvis_cv.py - Cyclovoltammetrie: Gamry-Dateien lesen, Redoxpaare auswerten, CV-Tab.

Auswertung je Redoxpaar in einem Potentialfenster [lo, hi]:
  E_pa = Maximum des Stroms im Hinlauf (dE/dt > 0), E_pc = Minimum im Rücklauf (dE/dt < 0),
  Peaklage per Parabel über ±3 Punkte verfeinert; E½ = (E_pa + E_pc)/2, ΔE_p = E_pa − E_pc.
  i_pa, i_pc = Ströme am Peak, gemessen von null. Der Rückpeak sitzt auf dem abklingenden Strom des
  Hinlaufs, daher das Verhältnis nach Nicholson (Anal. Chem. 38 (1966) 1406):
  i_r/i_f = (i_r)₀/i_f + 0.485·(i_sp)₀/i_f + 0.086 (i_sp = Strom am Umkehrpotential).
Referenzierung: E vs. Fc⁺/Fc = E_gemessen − (E½(Referenz, gemessen) − E°(Referenz vs. Fc⁺/Fc)).
Ströme: IUPAC-Konvention wie aufgezeichnet (Gamry: anodisch positiv); optional invertierbar.
"""
from __future__ import annotations

import csv
import re
import uuid
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout)

import uvvis_tabs as TABS
from uvvis_i18n import T
import uvvis_style as STYLE
from uvvis_style import make_form

# Referenzverbindungen: E½ gegen Fc⁺/Fc [V]. Ac₂Fc = 1,1'-Diacetylferrocen; Wert im Programm änderbar
# (lösungsmittelabhängig, gegen Literatur prüfen).
REFERENCES = {"fc": ("Fc", 0.0), "ac2fc": ("Ac₂Fc", 0.49)}


def read_gamry(path) -> dict:
    """Gamry .DTA (Framework 6/7): -> dict(meta, cycles=[dict(E, I, T)]).
    Zwei Varianten: mehrere Tabellen CURVE1, CURVE2, … (je Zyklus) oder eine Tabelle 'CURVE' mit
    Spalte 'Cycle'. Sehr kurze Tabellen (Endpunkt) werden verworfen."""
    lines = Path(path).read_text(encoding="latin-1", errors="replace").splitlines()
    meta = {"scanrate": None, "area": None, "date": "", "time": "", "convention": None}
    tables = []
    i = 0
    while i < len(lines):
        parts = lines[i].split("\t")
        key = parts[0]
        if key == "SCANRATE" and len(parts) > 2:
            meta["scanrate"] = float(parts[2])                 # mV/s
        elif key == "AREA" and len(parts) > 2:
            meta["area"] = float(parts[2])                     # cm²
        elif key == "DATE" and len(parts) > 2:
            meta["date"] = parts[2]
        elif key == "TIME" and len(parts) > 2:
            meta["time"] = parts[2]
        elif key == "CONVENTION" and len(parts) > 2:
            meta["convention"] = int(float(parts[2]))
        if re.match(r"CURVE\d*$", key) and len(parts) > 1 and parts[1] == "TABLE":
            hdr = lines[i + 1].strip().split("\t")
            i += 3
            rows = []
            while i < len(lines) and lines[i].startswith("\t"):
                rows.append(lines[i].split("\t")[1:])
                i += 1
            tables.append((hdr, rows))
            continue
        i += 1
    cycles = []
    for hdr, rows in tables:
        if len(rows) < 10 or "Vf" not in hdr or "Im" not in hdr:
            continue
        col = {h: k for k, h in enumerate(hdr)}
        arr = np.array([[float(r[col["Vf"]]), float(r[col["Im"]]), float(r[col["T"]]) if "T" in col else 0.0,
                         float(r[col["Cycle"]]) if "Cycle" in col else 0.0] for r in rows if len(r) >= len(hdr) - 1])
        if "Cycle" in col:
            for c in np.unique(arr[:, 3]):
                sel = arr[:, 3] == c
                if sel.sum() >= 10:
                    cycles.append({"E": arr[sel, 0], "I": arr[sel, 1], "T": arr[sel, 2]})
        else:
            cycles.append({"E": arr[:, 0], "I": arr[:, 1], "T": arr[:, 2]})
    if not cycles:
        raise ValueError(f"{Path(path).name}: keine CV-Daten (Gamry .DTA) gefunden")
    return {"meta": meta, "cycles": cycles}


def _refine(E, I, k):
    """Peaklage per Parabel durch ±3 Punkte (Raster der Messung ist meist 2–4 mV)."""
    lo, hi = max(0, k - 3), min(len(E), k + 4)
    if hi - lo < 5:
        return float(E[k]), float(I[k])
    try:
        a, b, c = np.polyfit(E[lo:hi], I[lo:hi], 2)
    except (np.linalg.LinAlgError, ValueError):
        return float(E[k]), float(I[k])
    if a == 0:
        return float(E[k]), float(I[k])
    e = -b / (2 * a)
    if not (min(E[lo:hi]) <= e <= max(E[lo:hi])):
        return float(E[k]), float(I[k])
    return float(e), float(np.polyval([a, b, c], e))


def analyze_couple(E, I, lo, hi):
    """Redoxpaar im Fenster [lo, hi] -> dict(epa, epc, e12, dep, ipa, ipc, ratio, edge) oder None.
    ratio = Rückpeak/Hinpeak nach Nicholson (1 = chemisch reversibel); Hinlauf = erste Scanrichtung.
    edge = True, wenn ein Peak am Fensterrand liegt (Fenster zu eng oder kein echter Peak)."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    dE = np.gradient(E)
    lo, hi = min(lo, hi), max(lo, hi)
    win = (E >= lo) & (E <= hi)
    fw, bw = win & (dE > 0), win & (dE < 0)
    if fw.sum() < 5 or bw.sum() < 5:
        return None
    ka = int(np.flatnonzero(fw)[np.argmax(I[fw])])
    kc = int(np.flatnonzero(bw)[np.argmin(I[bw])])
    epa, ipa = _refine(E, I, ka)
    epc, ipc = _refine(E, I, kc)
    edge_tol = 0.01 * (hi - lo) + 0.004
    edge = any(abs(e - b) < edge_tol for e in (E[ka], E[kc]) for b in (lo, hi))
    # Nicholson: Hinlauf = erste Scanrichtung, i_sp = Strom am ersten Umkehrpunkt
    k0 = int(np.argmax(np.abs(dE) > 0))
    anodic_first = dE[k0] > 0
    turn = int(np.argmax(E) if anodic_first else np.argmin(E))
    i_sp = abs(float(I[turn]))
    i_f, i_r = (abs(ipa), abs(ipc)) if anodic_first else (abs(ipc), abs(ipa))
    ratio = (i_r / i_f + 0.485 * i_sp / i_f + 0.086) if i_f > 0 else float("nan")
    return {"epa": epa, "epc": epc, "e12": (epa + epc) / 2, "dep": epa - epc, "ipa": ipa, "ipc": ipc,
            "ratio": ratio, "edge": bool(edge)}


def suggest_couples(E, I, min_rel=0.03, max_sep=0.25):
    """Vorschläge für Redoxpaare: anodische Peaks im Hinlauf mit passendem kathodischen Peak im Rücklauf.
    -> [(lo, hi)] (Fenster ±0.25 V um E½)."""
    E, I = np.asarray(E, float), np.asarray(I, float)
    dE = np.gradient(E)
    scale = np.nanmax(np.abs(I)) or 1.0

    def peaks(mask, sign, half_width=0.15):
        """Lokale Maxima von sign·I im Lauf; Prominenz gegen die Minima in ±half_width V (breite Peaks)."""
        idx = np.flatnonzero(mask)
        y = sign * np.convolve(I, np.ones(5) / 5, mode="same")
        out = []
        for j in range(3, len(idx) - 3):
            k = idx[j]
            if y[k] < y[idx[j - 3:j + 4]].max():
                continue
            left = idx[(E[idx] >= E[k] - half_width) & (E[idx] <= E[k])]
            right = idx[(E[idx] <= E[k] + half_width) & (E[idx] >= E[k])]
            if len(left) < 3 or len(right) < 3:
                continue
            prom = y[k] - max(y[left].min(), y[right].min())
            if prom > min_rel * scale:
                out.append(float(E[k]))
        return out
    an, ca = peaks(dE > 0, 1), peaks(dE < 0, -1)
    out = []
    for a in an:
        cs = [c for c in ca if 0 <= a - c <= max_sep]
        if cs:
            c = max(cs)
            mid = (a + c) / 2
            if not any(lo <= mid <= hi for lo, hi in out):
                out.append((round(mid - 0.25, 2), round(mid + 0.25, 2)))
    return out


def randles_sevcik(rates_mVs, ipa):
    """i_pa gegen √v (v in V/s): lineare Regression -> (Steigung, Achsenabschnitt, R²) oder None."""
    v = np.sqrt(np.asarray(rates_mVs, float) / 1000.0)
    y = np.asarray(ipa, float)
    ok = np.isfinite(v) & np.isfinite(y)
    if ok.sum() < 3:
        return None
    m, b = np.polyfit(v[ok], y[ok], 1)
    pred = m * v[ok] + b
    ss = np.sum((y[ok] - y[ok].mean()) ** 2)
    r2 = 1 - np.sum((y[ok] - pred) ** 2) / ss if ss > 0 else float("nan")
    return float(m), float(b), float(r2)


# ----------------------------------------------------------------------------
# CV-Tab
# ----------------------------------------------------------------------------
# hellblau -> blau -> violett -> dunkelrot -> rot (wie übliche Scanraten-Serien)
RATE_CMAP = LinearSegmentedColormap.from_list("rates", ["#56c1f0", "#1a4fd6", "#8a2be2", "#b0102a", "#e8231b"])


_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def axis_ref(text):
    """Referenzelektrode für die Achsenbeschriftung: tiefgestellte Unicode-Ziffern (AgNO₃) fehlen in vielen
    Schriften -> als Mathtext-Index setzen (AgNO$_3$)."""
    return re.sub("[₀-₉]+", lambda m: "$_{" + m.group().translate(_SUB) + "}$", str(text))


def _fmt_e(v, nd=3):
    return f"{v:+.{nd}f}".replace("-", "−")


class CVTab(TABS.FigureTab):
    STATE_KEY = "cv"
    X_RANGE = (-10.0, 10.0, 2, 0.1)
    XRANGE_TEXT = "cv_xrange"
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=-1.5, x_max=-0.5, ymax=0.0, files=[], couples=[], cycle=1,
                         ref_mode="none", ref_uid=None, ref_lo=0.3, ref_hi=0.8, ref_compound="ac2fc",
                         ref_value=REFERENCES["ac2fc"][1], ref_offset=0.0, ref_electrode="Ag/AgNO₃",
                         gradient=True, density=False, show_e12=True, arrow=True, invert=False)

    # -- Bedienelemente ------------------------------------------------------------
    def build_controls(self):
        st = self.st
        self._offset = 0.0
        self.results = []
        g = QGroupBox(T("cv_files"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("cv_add"), self.add_files), ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                        (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), "v [mV/s]"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(140)
        self.table.itemChanged.connect(self.table_edited)
        v.addWidget(self.table)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_analysis"))
        f = make_form(g)
        self.sp_cycle = QSpinBox(minimum=1, maximum=100, value=st["cycle"])
        self.sp_cycle.setToolTip(T("cv_cycle_tip"))
        f.addRow(T("cv_cycle"), self.sp_cycle)
        self.tbl_couples = QTableWidget(0, 2)
        self.tbl_couples.setHorizontalHeaderLabels([T("cv_from"), T("cv_to")])
        self.tbl_couples.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_couples.verticalHeader().setVisible(True)
        self.tbl_couples.setMaximumHeight(110)
        self.tbl_couples.setToolTip(T("cv_couples_tip"))
        self.tbl_couples.itemChanged.connect(self.couples_edited)
        f.addRow(T("cv_couples"), self.tbl_couples)
        row = QHBoxLayout()
        for txt, fn in (("+", self.add_couple), ("−", self.remove_couple), (T("cv_suggest"), self.suggest)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        f.addRow("", row)
        self.cmb_ref = QComboBox()
        for key in ("none", "internal", "manual"):
            self.cmb_ref.addItem(T("cv_ref_" + key), key)
        self.cmb_ref.setCurrentIndex(max(0, self.cmb_ref.findData(st["ref_mode"])))
        f.addRow(T("cv_ref"), self.cmb_ref)
        self.cmb_ref_file = QComboBox()
        self.lbl_ref_file = QLabel(T("cv_ref_file"))
        f.addRow(self.lbl_ref_file, self.cmb_ref_file)
        row = QHBoxLayout()
        self.sp_ref_lo = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=st["ref_lo"])
        self.sp_ref_hi = QDoubleSpinBox(decimals=2, minimum=-10, maximum=10, singleStep=0.05, value=st["ref_hi"])
        for w_ in (self.sp_ref_lo, QLabel("–"), self.sp_ref_hi):
            row.addWidget(w_)
        self.lbl_ref_win = QLabel(T("cv_ref_window"))
        f.addRow(self.lbl_ref_win, row)
        row = QHBoxLayout()
        self.cmb_compound = QComboBox()
        for key, (name, _) in REFERENCES.items():
            self.cmb_compound.addItem(name, key)
        self.cmb_compound.addItem(T("cv_ref_custom"), "custom")
        self.cmb_compound.setCurrentIndex(max(0, self.cmb_compound.findData(st["ref_compound"])))
        self.sp_ref_value = QDoubleSpinBox(decimals=3, minimum=-3, maximum=3, singleStep=0.01, value=st["ref_value"],
                                           suffix=" V")
        self.sp_ref_value.setToolTip(T("cv_ref_value_tip"))
        row.addWidget(self.cmb_compound, 1)
        row.addWidget(self.sp_ref_value)
        self.lbl_compound = QLabel(T("cv_ref_compound"))
        f.addRow(self.lbl_compound, row)
        self.sp_offset = QDoubleSpinBox(decimals=3, minimum=-5, maximum=5, singleStep=0.01, value=st["ref_offset"],
                                        suffix=" V")
        self.sp_offset.setToolTip(T("cv_offset_tip"))
        self.lbl_offset = QLabel(T("cv_offset"))
        f.addRow(self.lbl_offset, self.sp_offset)
        self.ed_electrode = QLineEdit(st["ref_electrode"])
        f.addRow(T("cv_electrode"), self.ed_electrode)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_display"))
        f = make_form(g)
        self.cb_gradient = QCheckBox(T("cv_gradient"))
        self.cb_density = QCheckBox(T("cv_density"))
        self.cb_e12 = QCheckBox(T("cv_show_e12"))
        self.cb_arrow = QCheckBox(T("cv_arrow"))
        self.cb_invert = QCheckBox(T("cv_invert"))
        self.cb_invert.setToolTip(T("cv_invert_tip"))
        for cb, key in ((self.cb_gradient, "gradient"), (self.cb_density, "density"), (self.cb_e12, "show_e12"),
                        (self.cb_arrow, "arrow"), (self.cb_invert, "invert")):
            cb.setChecked(st[key])
            f.addRow(cb)
            cb.toggled.connect(self.changed)
        self.lv.addWidget(g)

        g = QGroupBox(T("cv_results"))
        v = QVBoxLayout(g)
        self.tbl_res = QTableWidget(0, 9)
        self.tbl_res.setHorizontalHeaderLabels(
            [T("ov_name"), "#", "E_pa [V]", "E_pc [V]", "E½ [V]", "ΔE_p [mV]", "i_pa [µA]", "i_pc [µA]",
             "i_pc/i_pa"])
        self.tbl_res.horizontalHeaderItem(8).setToolTip(T("cv_ratio_tip"))
        self.tbl_res.verticalHeader().setVisible(False)
        self.tbl_res.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_res.setMinimumHeight(140)
        v.addWidget(self.tbl_res)
        self.lbl_res = QLabel("")
        self.lbl_res.setWordWrap(True)
        self.lbl_res.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_res)
        self.lv.addWidget(g)

        self.sp_cycle.valueChanged.connect(self.changed)
        for w_ in (self.sp_ref_lo, self.sp_ref_hi, self.sp_ref_value, self.sp_offset):
            w_.valueChanged.connect(self.changed)
        self.cmb_ref.currentIndexChanged.connect(self.changed)
        self.cmb_ref_file.currentIndexChanged.connect(self.changed)
        self.cmb_compound.currentIndexChanged.connect(self.compound_changed)
        self.ed_electrode.editingFinished.connect(self.changed)
        self.fill_table()
        self.fill_couples()
        self._sync_ref_widgets()

    def _sync_ref_widgets(self):
        mode = self.st["ref_mode"]
        for w_ in (self.lbl_ref_file, self.cmb_ref_file, self.lbl_ref_win, self.sp_ref_lo, self.sp_ref_hi,
                   self.lbl_compound, self.cmb_compound, self.sp_ref_value):
            w_.setVisible(mode == "internal")
        for w_ in (self.lbl_offset, self.sp_offset):
            w_.setVisible(mode == "manual")

    def compound_changed(self, *_):
        key = self.cmb_compound.currentData()
        if key in REFERENCES and not self._loading:
            self.sp_ref_value.blockSignals(True)
            self.sp_ref_value.setValue(REFERENCES[key][1])
            self.sp_ref_value.blockSignals(False)
        self.changed()

    def collect(self):
        st = self.st
        st.update(cycle=self.sp_cycle.value(), ref_mode=self.cmb_ref.currentData(),
                  ref_uid=self.cmb_ref_file.currentData(), ref_lo=self.sp_ref_lo.value(),
                  ref_hi=self.sp_ref_hi.value(), ref_compound=self.cmb_compound.currentData(),
                  ref_value=self.sp_ref_value.value(), ref_offset=self.sp_offset.value(),
                  ref_electrode=self.ed_electrode.text().strip() or "Ag/AgNO₃",
                  gradient=self.cb_gradient.isChecked(), density=self.cb_density.isChecked(),
                  show_e12=self.cb_e12.isChecked(), arrow=self.cb_arrow.isChecked(),
                  invert=self.cb_invert.isChecked())
        self._sync_ref_widgets()

    # -- Dateien -------------------------------------------------------------------
    def data(self, path):
        return self.cache(("cv", path), lambda: read_gamry(path))

    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("cv_add"), self.main.settings.value("last_dir", ""),
                                             "Gamry (*.DTA *.dta);;" + T("flt_all"))
        for p in ps:
            try:
                p = self.main.import_file(p, "data")
                d = self.data(p)
            except Exception as e:
                self.main.error(str(e))
                continue
            rate = d["meta"]["scanrate"]
            self.st["files"].append({"file": p, "uid": uuid.uuid4().hex[:8], "visible": True, "color": "#000000",
                                     "label": f"{round(rate, 1):g} mV/s" if rate else Path(p).stem})
        if ps and not self.st["couples"]:
            self.suggest()
        self.fill_table()
        self.timer.start()

    def move(self, d):
        r = self.table.currentRow()
        fs = self.st["files"]
        if 0 <= r < len(fs) and 0 <= r + d < len(fs):
            fs[r], fs[r + d] = fs[r + d], fs[r]
            self.fill_table()
            self.table.selectRow(r + d)
            self.timer.start()

    def remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["files"]):
            del self.st["files"][r]
            self.fill_table()
            self.timer.start()

    def fill_table(self):
        self._loading = True
        fs = self.st["files"]
        self.table.setRowCount(len(fs))
        for i, e in enumerate(fs):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e["visible"] else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(e["color"], lambda c, e=e: self._set_color(e, c)))
            try:
                rate = self.data(e["file"])["meta"]["scanrate"]
            except Exception:
                rate = None
            it = QTableWidgetItem(f"{round(rate, 1):g}" if rate else "–")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, it)
        self.table.resizeColumnToContents(0)
        cur = self.st.get("ref_uid")
        self.cmb_ref_file.blockSignals(True)
        self.cmb_ref_file.clear()
        for e in fs:
            self.cmb_ref_file.addItem(e["label"], e["uid"])
        self.cmb_ref_file.setCurrentIndex(max(0, self.cmb_ref_file.findData(cur)))
        self.cmb_ref_file.blockSignals(False)
        self._loading = False

    def _set_color(self, e, c):
        e["color"] = c
        self.timer.start()

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["files"][item.row()]
        if item.column() == 0:
            e["visible"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text()
            self.fill_table()
        self.timer.start()

    # -- Redoxpaare (gespeichert in gemessenen Potentialen, angezeigt in der Achsenskala) -----------------
    def fill_couples(self):
        self._loading = True
        cs = self.st["couples"]
        self.tbl_couples.setRowCount(len(cs))
        for i, (lo, hi) in enumerate(cs):
            for j, v in enumerate((lo, hi)):
                self.tbl_couples.setItem(i, j, QTableWidgetItem(f"{v - self._offset:.3f}"))
        self._loading = False

    def couples_edited(self, item):
        if self._loading:
            return
        try:
            v = float(item.text().replace(",", ".").replace("−", "-")) + self._offset
        except ValueError:
            return self.fill_couples()
        self.st["couples"][item.row()][item.column()] = v
        self.timer.start()

    def add_couple(self):
        x0, x1 = (self.st["x_min"], self.st["x_max"]) if not self.st["x_auto"] else (-0.25, 0.25)
        mid = (x0 + x1) / 2 + self._offset
        self.st["couples"].append([round(mid - 0.25, 3), round(mid + 0.25, 3)])
        self.fill_couples()
        self.timer.start()

    def remove_couple(self):
        r = self.tbl_couples.currentRow()
        if 0 <= r < len(self.st["couples"]):
            del self.st["couples"][r]
        elif self.st["couples"]:
            self.st["couples"].pop()
        self.fill_couples()
        self.timer.start()

    def suggest(self):
        """Redoxpaare aus der ersten sichtbaren Messung vorschlagen (ersetzt die Liste)."""
        vis = [e for e in self.st["files"] if e["visible"]]
        if not vis:
            return
        c = self.cycle_of(vis[0])
        self.st["couples"] = [list(w) for w in suggest_couples(c["E"], c["I"])]
        self.fill_couples()
        self.timer.start()

    # -- Auswertung und Abbildung -------------------------------------------------------
    def cycle_of(self, e):
        cyc = self.data(e["file"])["cycles"]
        return cyc[min(self.st["cycle"], len(cyc)) - 1]

    def reference_offset(self):
        """-> (Offset in V: E_Achse = E_gemessen − Offset, Achsenbeschriftung der Referenz, Hinweis)."""
        st = self.st
        if st["ref_mode"] == "manual":
            return st["ref_offset"], "Fc$^{0/+}$", ""
        if st["ref_mode"] == "internal":
            e = next((x for x in st["files"] if x["uid"] == st.get("ref_uid")), None)
            if e is not None:
                c = self.cycle_of(e)
                r = analyze_couple(c["E"], c["I"], st["ref_lo"], st["ref_hi"])
                if r is not None:
                    name = REFERENCES.get(st["ref_compound"], (T("cv_ref_custom"), 0))[0]
                    note = T("cv_ref_note", name=name, e12=_fmt_e(r["e12"]), el=st["ref_electrode"],
                             dep=f"{r['dep'] * 1000:.0f}", val=_fmt_e(st["ref_value"], 2))
                    if r["edge"]:
                        note += "  " + T("cv_edge")
                    return r["e12"] - st["ref_value"], "Fc$^{0/+}$", note
            return 0.0, st["ref_electrode"], T("cv_ref_missing")
        return 0.0, st["ref_electrode"], ""

    def figure_spec(self):
        st = self.st
        vis = [e for e in st["files"] if e["visible"]]
        if not vis:
            self.results = []
            self.show_results()
            return None
        cfg = self.base_cfg()
        off, ref_label, note = self.reference_offset()
        if abs(off - self._offset) > 1e-12:
            self._offset = off
            self.fill_couples()
        sign = -1.0 if st["invert"] else 1.0
        rates = [self.data(e["file"])["meta"]["scanrate"] or 0.0 for e in vis]
        order = np.argsort(np.argsort(rates))
        curves, self.results, xs = [], [], []
        for k, e in enumerate(vis):
            d = self.data(e["file"])
            c = self.cycle_of(e)
            E = c["E"] - off
            if st["density"] and d["meta"]["area"]:
                y, unit = sign * c["I"] * 1e3 / d["meta"]["area"], "mA"       # mA cm⁻²
            else:
                y, unit = sign * c["I"] * 1e6, "µA"
            color = (RATE_CMAP(order[k] / max(1, len(vis) - 1)) if st["gradient"] and len(vis) > 1 else e["color"])
            color = color if isinstance(color, str) else "#%02x%02x%02x" % tuple(int(255 * v) for v in color[:3])
            curves.append({"x": E, "y": y, "color": color, "label": e["label"], "ls": "-", "lw": 1.3})
            xs.append(E)
            for n, (lo, hi) in enumerate(st["couples"], 1):
                r = analyze_couple(c["E"], c["I"], lo, hi)
                if r is not None:
                    self.results.append(dict(r, label=e["label"], n=n, rate=d["meta"]["scanrate"],
                                             epa=r["epa"] - off, epc=r["epc"] - off, e12=r["e12"] - off))
        allx = np.concatenate(xs)
        cfg["xlim"] = [float(allx.min()), float(allx.max())] if st["x_auto"] else [st["x_min"], st["x_max"]]
        ally = np.concatenate([c_["y"] for c_ in curves])
        span = float(ally.max() - ally.min()) or 1.0
        cfg["ylim"] = [float(ally.min()) - 0.08 * span, st["ymax"] if st["ymax"] > 0 else float(ally.max()) + 0.12 * span]
        cfg["xlabel"] = f"E [V vs. {axis_ref(ref_label)}]"
        cfg["ylabel"] = "j [mA cm$^{-2}$]" if (st["density"] and unit == "mA") else "I [µA]"
        labels = []
        if st["show_e12"]:
            for n in range(1, len(st["couples"]) + 1):
                vals = [r["e12"] for r in self.results if r["n"] == n and not r["edge"]]
                if vals:
                    e12 = float(np.mean(vals))
                    labels.append({"key": f"label_e12_{n}", "lam": e12,
                                   "text": "E$_{1/2}$ =\n" + _fmt_e(e12, 2) + " V"})
        if st["arrow"]:
            c0 = curves[0]
            xr = cfg["xlim"][1] - cfg["xlim"][0]
            direction = 1.0 if np.gradient(c0["x"])[:5].mean() >= 0 else -1.0
            x0, y0 = float(c0["x"][0]), float(c0["y"][0])
            cfg["arrows"] = [(x0, y0, x0 + direction * 0.08 * xr, y0)]
        self.note = note
        self.show_results()
        return cfg, curves, labels, []

    def show_results(self):
        if not hasattr(self, "tbl_res"):
            return
        res = self.results
        self.tbl_res.setRowCount(len(res))
        for i, r in enumerate(res):
            vals = [r["label"], str(r["n"]), _fmt_e(r["epa"]), _fmt_e(r["epc"]), _fmt_e(r["e12"]),
                    f"{r['dep'] * 1000:.0f}", f"{r['ipa'] * 1e6:.1f}", f"{r['ipc'] * 1e6:.1f}", f"{r['ratio']:.2f}"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if r["edge"]:
                    it.setForeground(Qt.red)
                    it.setToolTip(T("cv_edge"))
                self.tbl_res.setItem(i, j, it)
        self.tbl_res.resizeColumnsToContents()
        lines = [self.note] if getattr(self, "note", "") else []
        for n in range(1, len(self.st["couples"]) + 1):
            rr = [r for r in res if r["n"] == n and r["rate"]]
            if len({r["rate"] for r in rr}) >= 3:
                fit = randles_sevcik([r["rate"] for r in rr], [r["ipa"] * 1e6 for r in rr])
                if fit:
                    lines.append(T("cv_randles", n=n, m=f"{fit[0]:.1f}", r2=f"{fit[2]:.4f}"))
        self.lbl_res.setText("\n".join(lines))

    def hover_text(self, x, val, name):
        if val is None:
            return f"E = {x:.3f} V"
        unit = "mA cm⁻²" if self.st["density"] else "µA"
        return f"E = {x:.3f} V    {'j' if self.st['density'] else 'I'} = {val:.2f} {unit}    {name}"

    def export_to(self, base: Path):
        """Abbildung wie die anderen Tabs, dazu die Ergebnisse als CSV (UTF-8, Semikolon)."""
        files = super().export_to(base)
        p = Path(base).with_name(Path(base).name + "_results.csv")
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["file", "couple", "scan_rate_mV_s", "E_pa_V", "E_pc_V", "E_half_V", "dE_p_mV",
                        "i_pa_uA", "i_pc_uA", "ratio_Nicholson", "peak_at_window_edge", "reference"])
            for r in self.results:
                w.writerow([r["label"], r["n"], r["rate"], f"{r['epa']:.4f}", f"{r['epc']:.4f}", f"{r['e12']:.4f}",
                            f"{r['dep'] * 1000:.1f}", f"{r['ipa'] * 1e6:.3f}", f"{r['ipc'] * 1e6:.3f}",
                            f"{r['ratio']:.3f}", int(r["edge"]), getattr(self, "note", "")])
        return files + [p]
