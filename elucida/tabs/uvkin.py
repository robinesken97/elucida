"""elucida/tabs/uvkin.py - UV-Vis-Kinetik: wie sich die Spektren einer Lösung über die Zeit ändern (Stabilität über Tage,
Reaktion). Spektren aus einer oder mehreren Cary-Dateien, je Zeile eine Reihe (z. B. Konzentration); Zeit nur aus der
Messdatei („Collection Time“ des Cary-CSV-Exports), nie aus Dateinamen oder Dateizeiten.

Ansichten: Spektren einer Reihe im Farbverlauf der Zeit; Absorbanz bei λ (oder Maximum im Fenster ± n nm) gegen die
Zeit seit dem ersten Spektrum der Reihe, wie gemessen oder relativ zum ersten Spektrum; optional Zerfall erster Ordnung
A(t) = A0·exp(−k·t) je Reihe (`EPR.fit_first_order`, kleinste Quadrate auf den gemessenen Werten).
"""
from __future__ import annotations

import csv
import html
import uuid
from pathlib import Path

import numpy as np
from PySide6.QtCore import QItemSelectionModel, Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from elucida.core import uvvis as core
from elucida.tabs import base as TABS
from elucida.tabs.epr import fit_first_order, sci_text
from elucida.app.i18n import T
from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.style import HINT_CSS, make_form

UNIT_S = {"min": 60.0, "h": 3600.0, "d": 86400.0}


def auto_unit(seconds):
    """Zeiteinheit nach der Gesamtdauer: bis 2 h Minuten, bis 2 d Stunden, sonst Tage."""
    return "min" if seconds <= 2 * 3600 else "h" if seconds <= 2 * 86400 else "d"


def fmt_t(v):
    """Zeit in der gewählten Einheit: höchstens zwei Nachkommastellen, ohne Nullen am Ende."""
    return f"{round(float(v), 2):g}"


def fmt_pct(v):
    return f"{v:.1f}" if np.isfinite(v) else "–"


def value_at(x, y, lam, win=0.0):
    """Absorbanz bei lam (linear interpoliert) oder, mit win > 0, das Maximum in lam ± win; außerhalb NaN."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if not len(x) or lam < x.min() or lam > x.max():
        return float("nan")
    if win > 0:
        sel = (x >= lam - win) & (x <= lam + win)
        return float(np.nanmax(y[sel])) if sel.any() else float("nan")
    return float(np.interp(lam, x, y))


def is_baseline(name):
    """Gerätebasislinien („Baseline 100%T“, „Baseline 0%T“) sind keine Spektren (wie read_binary_samples)."""
    return str(name).strip().lower().startswith("baseline")


def series_from_name(name):
    """Reihe nur, wenn der Probenname eine Konzentration eindeutig nennt (core.parse_sample_name), sonst ''."""
    p = core.parse_sample_name(str(name))
    return f"{p[1]:g} {core.unit_text(p[2])}" if p else ""


class UVKinTab(TABS.FigureTab):
    STATE_KEY = "uvkin"
    GUIDE, GUIDE_ACTION = "uvkin", ("guide_add", "add_files")
    TEXT_OPTS = ("fonts", "axes_frame")
    CAP_FIELDS = ("solvent", "conc")
    SI_CAPTION = "UV-Vis spectra of {name}."
    X_RANGE = (100, 3500, 0, 10)
    RESET_KEEP = ("entries",)                       # Spektren samt Reihe, Name und Häkchen
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=250.0, x_max=800.0, ymax=0.0, entries=[], view="", series="",
                         lam=0.0, win=0.0, y="abs", t_unit="auto", fit=False, cap_solvent="", cap_conc="")

    def arrange(self):
        super().arrange()
        self.to_right(self.grp_results, T("tab_results"))

    # -- linke Spalte ---------------------------------------------------------------
    def build_controls(self):
        st = self.st
        self.rows_data, self.fits, self.notes = [], {}, []
        g = QGroupBox(T("uvkin_spectra"))
        v = QVBoxLayout(g)
        row, row2 = QHBoxLayout(), QHBoxLayout()               # Hinzufügen / Auswahl: zwei Reihen
        for txt, fn in ((T("guide_add"), self.add_files), ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                        (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            (row if txt.endswith("…") else row2).addWidget(b)
        row.addStretch(1)
        row2.addStretch(1)
        v.addLayout(row)
        v.addLayout(row2)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("uvkin_series"), T("uvkin_time")])
        self.table.horizontalHeaderItem(2).setToolTip(T("uvkin_series_tip"))
        self.table.horizontalHeaderItem(3).setToolTip(T("uvkin_time_tip"))
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        TABS.RowDrag(self.table, self.move_row)
        self.table.itemChanged.connect(self.table_edited)
        self.table.itemSelectionChanged.connect(self.show_details)
        v.addWidget(self.table)
        STYLE.hide_when_empty(self.table)
        self.lbl_rows = STYLE.HintLabel("")
        self.lbl_rows.setWordWrap(True)
        self.lbl_rows.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_rows)
        self.lv.addWidget(g)

        # Reihe für mehrere Zeilen auf einmal (statt eines Dialogs)
        self.det = QGroupBox(T("uvkin_sel"))
        f = make_form(self.det)
        self.ed_series = QLineEdit()
        self.ed_series.setPlaceholderText(T("uvkin_series_ph"))
        self.ed_series.returnPressed.connect(self.apply_series)
        f.addRow(T("uvkin_series"), self.ed_series)
        self.btn_series = QPushButton(T("uvkin_series_apply"))
        self.btn_series.setToolTip(T("uvkin_series_apply_tip"))
        self.btn_series.clicked.connect(self.apply_series)
        self.btn_series.setFixedWidth(STYLE.VALUE_W)        # einzelner Knopf: ganze Wertespalte
        f.addRow("", self.btn_series)
        self.lv.addWidget(self.det)

        # Auswertung: eine Ansichtswahl oben, darunter nur die Felder der Ansicht (_view_fields)
        g = QGroupBox(T("uvkin_eval"))
        f = make_form(g)
        self.cmb_view = QComboBox()
        for key in ("spectra", "trace"):
            self.cmb_view.addItem(T("uvkin_view_" + key), key)
        self.cmb_view.setToolTip(T("uvkin_view_tip"))
        f.addRow(T("sec_mode"), self.cmb_view)
        self.cmb_series = QComboBox()
        self.cmb_series.setToolTip(T("uvkin_series_pick_tip"))
        self.sp_lam = QDoubleSpinBox(decimals=0, minimum=0, maximum=3500, singleStep=1, suffix=" nm", value=st["lam"])
        self.sp_lam.setSpecialValueText(T("auto"))
        self.sp_lam.setToolTip(T("uvkin_lam_tip"))
        self.sp_win = QDoubleSpinBox(decimals=0, minimum=0, maximum=200, singleStep=1, prefix="± ", suffix=" nm",
                                     value=st["win"])
        self.sp_win.setSpecialValueText(T("off"))
        self.sp_win.setToolTip(T("uvkin_win_tip"))
        self.cmb_y = QComboBox()
        for key in ("abs", "rel"):
            self.cmb_y.addItem(T("uvkin_y_" + key), key)
        self.cmb_y.setCurrentIndex(max(0, self.cmb_y.findData(st["y"])))
        self.cmb_unit = QComboBox()
        for key in ("auto", "min", "h", "d"):
            self.cmb_unit.addItem(T("auto") if key == "auto" else key, key)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["t_unit"])))
        self._rows = {}
        for key_, lab_, w_ in (("series", "uvkin_series", self.cmb_series), ("lam", "uvkin_lam", self.sp_lam),
                               ("win", "uvkin_win", self.sp_win), ("y", "uvkin_y", self.cmb_y),
                               ("unit", "uvkin_unit", self.cmb_unit)):
            l_ = QLabel(T(lab_))
            f.addRow(l_, w_)
            self._rows[key_] = (l_, w_)
        self.cb_fit = QCheckBox(T("epr_kin_fit"))
        self.cb_fit.setToolTip(T("uvkin_fit_tip"))
        self.cb_fit.setChecked(st["fit"])
        f.addRow(self.cb_fit)
        self.lv.addWidget(g)

        # Ergebnisse (Reiter rechts, arrange): Tabelle je Messpunkt + Zusammenfassung je Reihe
        self.grp_results = QGroupBox(T("tab_results"))
        rv = QVBoxLayout(self.grp_results)
        self.res_table = QTableWidget(0, 5)
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        STYLE.empty_note(self.res_table, T("uvkin_results_none"))
        rv.addWidget(self.res_table)
        self.lbl_summary = STYLE.SciLabel("")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rv.addWidget(self.lbl_summary)
        self.lv.addWidget(self.grp_results)
        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export (Reiter SI-Text)

        self.fill_table()
        self.fill_series()
        self._sync_view_combo()
        for w_ in (self.sp_lam, self.sp_win):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cmb_series, self.cmb_y, self.cmb_unit):
            w_.currentIndexChanged.connect(self.changed)
        self.cmb_view.currentIndexChanged.connect(self._view_changed)
        self.cb_fit.toggled.connect(self.changed)
        self._view_fields()
        QTimer.singleShot(0, self._view_fields)           # noch einmal nach tidy: erst dann gibt es die Chip-Zeile

    # -- Ansicht ------------------------------------------------------------------
    def view(self):
        """Gewählte Ansicht; ohne Wahl „gegen Zeit“, sobald eine Reihe zwei Spektren mit Zeit hat."""
        v = self.st.get("view") or ""
        if v in ("spectra", "trace"):
            return v
        return "trace" if any(len([r for r in rows if r["time"] is not None]) >= 2
                              for rows in self.series_rows().values()) else "spectra"

    def _sync_view_combo(self):
        self.cmb_view.blockSignals(True)
        self.cmb_view.setCurrentIndex(max(0, self.cmb_view.findData(self.view())))
        self.cmb_view.blockSignals(False)

    def _view_fields(self, *_):
        v = self.cmb_view.currentData()
        show = {"series": v == "spectra", "lam": v == "trace", "win": v == "trace", "y": v == "trace", "unit": True}
        for key_, pair in self._rows.items():
            for w_ in pair:
                w_.setVisible(show[key_])
        self.cb_fit.setVisible(v == "trace")
        row = self.cb_fit.parentWidget()                  # Zeile „Optionen“ (tidy): ohne sichtbaren Chip ganz weg
        if isinstance(row, STYLE.ChipRow) and hasattr(row.parentWidget().layout(), "labelForField"):
            for w_ in (row, row.parentWidget().layout().labelForField(row)):
                if w_ is not None:
                    w_.setVisible(v == "trace")

    def _view_changed(self, *_):
        if self._loading:
            return
        self.st["view"] = self.cmb_view.currentData()
        self._view_fields()
        self.changed()

    def collect(self):
        self.st.update(series=self.cmb_series.currentData() or "", lam=self.sp_lam.value(), win=self.sp_win.value(),
                       y=self.cmb_y.currentData(), t_unit=self.cmb_unit.currentData(), fit=self.cb_fit.isChecked())

    # -- Liste --------------------------------------------------------------------
    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("guide_add"), self.main.settings.value("last_dir", ""),
                                             T("flt_csv") + ";;" + T("flt_all"))
        if ps:
            self.load_files(ps)

    def load_files(self, ps):
        """Dateien ins Projekt kopieren (die eigenen bleiben unverändert), jedes Spektrum eine Zeile."""
        es, bad = self.st["entries"], []
        have = {(e["file"], e["idx"]) for e in es}
        for p in ps:
            try:
                q = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
                smp = self.samples(q)
            except Exception as ex:
                bad.append(f"{Path(p).name}: {ex}")
                continue
            for k, s_ in enumerate(smp):
                if is_baseline(s_["name"]) or (q, k) in have:
                    continue
                es.append({"uid": uuid.uuid4().hex[:8], "file": q, "idx": k, "label": s_["name"],
                           "series": series_from_name(s_["name"]), "use": True})
        if bad:
            self.main.error(T("uvkin_read_fail", files="\n".join(bad)))
        self.fill_table()
        self.fill_series()
        self._sync_view_combo()
        self._view_fields()
        self.timer.start()

    def sample_of(self, e):
        """Probe einer Zeile (Spektrum und Zeit aus der Datei) oder None (Datei fehlt/unlesbar)."""
        try:
            smp = self.samples(e["file"]) if Path(e["file"]).exists() else []
        except Exception:
            return None
        return smp[e["idx"]] if 0 <= e["idx"] < len(smp) else None

    def move(self, d):
        self.move_row(self.table.currentRow(), self.table.currentRow() + d)

    def move_row(self, src, dst):
        if TABS.move_item(self.st["entries"], src, dst):
            self.fill_table()
            self.table.selectRow(dst)
            self.timer.start()

    def selected_rows(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def remove(self):
        rows = self.selected_rows()
        if not rows:
            return
        for r in reversed(rows):
            del self.st["entries"][r]
        self.fill_table()
        self.fill_series()
        self.timer.start()

    def apply_series(self):
        """Reihe für alle markierten Zeilen auf einmal (Feld + Knopf statt Dialog)."""
        rows = self.selected_rows()
        if not rows:
            return
        for r in rows:
            self.st["entries"][r]["series"] = self.ed_series.text().strip()
        self.fill_table()
        for r in rows:
            self.table.selectionModel().select(self.table.model().index(r, 0),
                                               QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.fill_series()
        self._sync_view_combo()
        self._view_fields()
        self.timer.start()

    def fill_table(self):
        self._loading = True
        es = self.st["entries"]
        self.table.setRowCount(len(es))
        for i, e in enumerate(es):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e.get("use", True) else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setItem(i, 2, QTableWidgetItem(e.get("series", "")))
            s_ = self.sample_of(e)
            t = s_.get("time") if s_ else None
            it = QTableWidgetItem(t.strftime("%Y-%m-%d %H:%M") if t else "–")
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            if s_ is None:
                it.setToolTip(T("uvkin_missing"))
            self.table.setItem(i, 3, it)
        self.table.resizeColumnToContents(2)
        self.table.resizeColumnToContents(3)
        STYLE.check_columns(self.table)
        # so hoch wie die Zeilen (3 bis 8, darüber scrollen): nie eine halb sichtbare Zeile
        self.table.setFixedHeight(self.table.horizontalHeader().sizeHint().height()
                                  + max(3, min(len(es), 8)) * STYLE.CHECK_ROW_H + 2)
        self._loading = False
        self.show_details()
        self.show_row_hint()

    def show_row_hint(self):
        es = [e for e in self.st["entries"] if e.get("use", True)]
        n = sum(1 for e in es if not str(e.get("series", "")).strip())
        self.lbl_rows.setText(T("uvkin_no_series", n=n) if n else "")

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["entries"][item.row()]
        if item.column() == 0:
            e["use"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text()
        elif item.column() == 2:
            e["series"] = item.text().strip()
            self.fill_series()
            self._sync_view_combo()
            self._view_fields()
        self.show_row_hint()
        self.timer.start()

    def show_details(self):
        rows = self.selected_rows()
        self.det.setEnabled(bool(rows))
        if rows:
            vals = {self.st["entries"][r].get("series", "") for r in rows if r < len(self.st["entries"])}
            self.ed_series.setText(vals.pop() if len(vals) == 1 else "")

    def fill_series(self):
        names = list(self.series_rows())
        cur = self.st.get("series", "")
        self.cmb_series.blockSignals(True)
        self.cmb_series.clear()
        for n in names:
            self.cmb_series.addItem(n, n)
        self.cmb_series.setCurrentIndex(max(0, self.cmb_series.findData(cur)))
        self.cmb_series.blockSignals(False)

    # -- Daten ----------------------------------------------------------------------
    def series_rows(self):
        """{Reihe: [dict(e, x, y, time)]} in Listenreihenfolge, nur benutzte Zeilen mit Reihe und lesbarer Datei."""
        out = {}
        for e in self.st["entries"]:
            name = str(e.get("series", "")).strip()
            if not (e.get("use", True) and name):
                continue
            s_ = self.sample_of(e)
            if s_ is None:
                continue
            out.setdefault(name, []).append({"e": e, "x": s_["x"], "y": s_["y"], "time": s_.get("time")})
        for rows in out.values():                         # nach Zeit; ohne Zeit am Ende in Listenreihenfolge
            rows.sort(key=lambda r: (r["time"] is None, r["time"] or 0))
        return out

    def auto_lam(self, rows):
        """λ ohne Eingabe: Maximum des ersten Spektrums der ersten Reihe im gezeigten Bereich (sonst ab 300 nm)."""
        x, y = rows[0]["x"], rows[0]["y"]
        lo, hi = (self.st["x_min"], self.st["x_max"]) if not self.st["x_auto"] else (300.0, float(x.max()))
        sel = (x >= lo) & (x <= hi) & np.isfinite(y)
        return float(round(x[sel][np.argmax(y[sel])])) if sel.any() else float(x[np.nanargmax(y)])

    def unit(self, seconds):
        u = self.st.get("t_unit", "auto")
        return u if u in UNIT_S else auto_unit(seconds)

    def trace(self):
        """Absorbanz gegen Zeit je Reihe -> (Reihen {name: dict(t_s, A, rel, labels, n_untimed)}, λ, Einheit)."""
        st = self.st
        series = self.series_rows()
        if not series:
            return {}, None, "min"
        first = next(iter(series.values()))
        lam = st["lam"] if st["lam"] > 0 else self.auto_lam(first)
        out, span = {}, 0.0
        for name, rows in series.items():
            timed = [r for r in rows if r["time"] is not None]
            if not timed:
                out[name] = {"t": np.array([]), "A": np.array([]), "rel": np.array([]), "labels": [],
                             "untimed": len(rows)}
                continue
            t0 = timed[0]["time"]
            t = np.array([(r["time"] - t0).total_seconds() for r in timed])
            A = np.array([value_at(r["x"], r["y"], lam, st["win"]) for r in timed])
            rel = 100.0 * A / A[0] if np.isfinite(A[0]) and A[0] != 0 else np.full(len(A), np.nan)
            out[name] = {"t": t, "A": A, "rel": rel, "labels": [r["e"]["label"] for r in timed],
                         "untimed": len(rows) - len(timed)}
            span = max(span, float(t.max()))
        return out, lam, self.unit(span)

    def fit_series(self, data):
        """Zerfall erster Ordnung je Reihe auf den gemessenen Absorbanzen (Zeit in s); None = weniger als drei Punkte."""
        fits = {}
        for name, d in data.items():
            ok = np.isfinite(d["A"])
            fits[name] = fit_first_order(d["t"][ok], d["A"][ok]) if ok.sum() >= 3 else None
        return fits

    # -- Abbildung --------------------------------------------------------------------
    def figure_spec(self):
        st = self.st
        self.rows_data, self.fits, self.lam_used, self.unit_used = {}, {}, None, "min"
        if not st["entries"]:
            self.show_results()
            return None
        n_off = sum(1 for e in st["entries"] if e.get("use", True) and not str(e.get("series", "")).strip())
        if n_off:
            self.add_note(T("uvkin_no_series", n=n_off))
        gone = sum(1 for e in st["entries"] if self.sample_of(e) is None)
        if gone:
            self.add_note(T("uvkin_gone", n=gone))
        data, lam, unit = self.trace()
        self.rows_data, self.lam_used, self.unit_used = data, lam, unit
        self.fits = self.fit_series(data) if st["fit"] else {}
        spec = self.spectra_spec() if self.view() == "spectra" else self.trace_spec(data, lam, unit)
        self.show_results()
        return spec

    def shown_series(self):
        series = self.series_rows()
        name = self.st.get("series") or ""
        return (name if name in series else next(iter(series), None)), series

    def spectra_spec(self):
        st = self.st
        name, series = self.shown_series()
        if name is None:
            return None
        rows = series[name]
        timed = [r for r in rows if r["time"] is not None]
        span = (timed[-1]["time"] - timed[0]["time"]).total_seconds() if timed else 0.0
        unit = self.unit(span)
        from matplotlib import colormaps
        from matplotlib.colors import to_hex
        curves = []
        for k, r in enumerate(timed):
            dt = (r["time"] - timed[0]["time"]).total_seconds() / UNIT_S[unit]
            col = to_hex(colormaps["viridis"](0.85 * k / max(1, len(timed) - 1))) if len(timed) > 1 else "#000000"
            curves.append({"x": r["x"], "y": r["y"], "color": col, "label": f"{fmt_t(dt)} {unit}", "ls": "-",
                           "lw": 1.2})
        for r in rows:                                    # ohne Zeit: grau, mit Namen
            if r["time"] is None:
                curves.append({"x": r["x"], "y": r["y"], "color": "#808080", "label": r["e"]["label"], "ls": "--",
                               "lw": 1.0})
        cfg = self.base_cfg()
        xs = np.concatenate([c["x"] for c in curves])
        x0, x1 = (float(xs.min()), float(xs.max())) if st["x_auto"] else (st["x_min"], st["x_max"])
        cfg["xlim"] = [x0, x1]
        vals = np.concatenate([c["y"][(c["x"] >= x0) & (c["x"] <= x1)] for c in curves])
        vals = vals[np.isfinite(vals)]
        top = float(vals.max()) if len(vals) else 1.0
        bot = min(0.0, float(vals.min())) if len(vals) else 0.0
        span_y = (top - bot) or 1.0
        cfg["ylim"] = [bot - 0.03 * span_y, st["ymax"] if st["ymax"] > 0 else top + 0.08 * span_y]
        cfg["xlabel"], cfg["ylabel"] = "wavelength [nm]", "absorbance"
        cfg["legend"], cfg["legend_beside"] = True, True
        return cfg, curves, [], []

    def trace_spec(self, data, lam, unit):
        st = self.st
        rel = st["y"] == "rel"
        untimed = sum(d["untimed"] for d in data.values())
        if untimed:
            self.add_note(T("uvkin_untimed", n=untimed))
        curves = []
        for k, (name, d) in enumerate(data.items()):
            if not len(d["t"]):
                continue
            col = TABS.PALETTE[k % len(TABS.PALETTE)]
            t = d["t"] / UNIT_S[unit]
            y = d["rel"] if rel else d["A"]
            curves.append({"x": t, "y": y, "color": col, "label": name, "ls": "-", "lw": 0.8, "marker": "o"})
            f = self.fits.get(name)
            if f is not None:
                tf = np.linspace(0.0, float(d["t"].max()), 200)
                yf = f["I0"] * np.exp(-f["k"] * tf)
                if rel:
                    yf = 100.0 * yf / d["A"][0]
                curves.append({"x": tf / UNIT_S[unit], "y": yf, "color": col, "label": None, "ls": "--", "lw": 1.2})
            elif st["fit"]:
                self.add_note(T("uvkin_fit_short", s=name, n=int(np.isfinite(d["A"]).sum())))
        if not curves:
            self.add_note(T("uvkin_no_time"))
            return None
        cfg = self.base_cfg()
        xs = np.concatenate([c["x"] for c in curves])
        ys = np.concatenate([c["y"] for c in curves])
        ys = ys[np.isfinite(ys)]
        pad = 0.05 * (float(np.ptp(xs)) or 1.0)
        cfg["xlim"] = [float(xs.min()) - pad, float(xs.max()) + pad]
        top = float(ys.max()) if len(ys) else 1.0
        bot = min(0.0, float(ys.min())) if len(ys) else 0.0
        cfg["ylim"] = [bot - 0.03 * ((top - bot) or 1.0), st["ymax"] if st["ymax"] > 0 else top + 0.1 * ((top - bot) or 1.0)]
        cfg["xlabel"] = f"t [{unit}]"
        cfg["ylabel"] = "relative absorbance [%]" if rel else "absorbance"
        cfg["legend"], cfg["legend_beside"] = True, True
        cfg["y_axis"] = "numbers"
        return cfg, curves, [], []

    # -- Ergebnisse -----------------------------------------------------------------
    def series_summary(self, name):
        """Kennwerte einer Reihe (dieselben Zahlen in Tabelle, Kacheln, Methodentext) oder None ohne Zeitpunkte."""
        d = (self.rows_data or {}).get(name)
        if not d or not len(d["t"]):
            return None
        u = UNIT_S[self.unit_used]
        out = {"A0": d["A"][0], "A1": d["A"][-1], "rest": d["rel"][-1], "dur": d["t"][-1] / u, "n": len(d["t"]),
               "fit": None}
        f = self.fits.get(name)
        if f is not None:
            ci = f["ci_k"]
            out["fit"] = {"k": f["k"] * u, "ci": (ci[0] * u, ci[1] * u) if ci else None,
                          "half": np.log(2) / (f["k"] * u) if f["k"] > 0 else None, "n": f["n"]}
        return out

    def show_results(self):
        """Ergebnisseite: Messpunkte je Reihe (Reihe, Name, t, A, relativ) und Zusammenfassung je Reihe."""
        if not hasattr(self, "res_table"):
            return
        data, unit = self.rows_data or {}, self.unit_used
        rows = [(n, lab, t / UNIT_S[unit], a, r) for n, d in data.items()
                for lab, t, a, r in zip(d["labels"], d["t"], d["A"], d["rel"])]
        lam = core.fmt_lam(self.lam_used) if self.lam_used else "–"
        self.res_table.setHorizontalHeaderLabels([T("uvkin_series"), T("ov_name"), f"t [{unit}]",
                                                  f"A ({lam} nm)", T("uvkin_rel_col")])
        self.res_table.setRowCount(len(rows))
        for i, (n, lab, t, a, r) in enumerate(rows):
            for j, txt in enumerate((n, lab, fmt_t(t), f"{a:.3f}" if np.isfinite(a) else "–", fmt_pct(r))):
                self.res_table.setItem(i, j, QTableWidgetItem(txt))
        lines = []
        for n in data:
            s = self.series_summary(n)
            if s is None:
                lines.append(T("uvkin_sum_none", s=n))
                continue
            txt = T("uvkin_sum", s=n, a0=f"{s['A0']:.3f}", a1=f"{s['A1']:.3f}", rest=fmt_pct(s["rest"]),
                    dur=fmt_t(s["dur"]), u=unit, n=s["n"])
            f = s["fit"]
            if f is not None:
                ci = f"{f['ci'][0]:.3g} … {f['ci'][1]:.3g}" if f["ci"] else "–"
                txt += "; " + T("uvkin_sum_fit", k=f"{f['k']:.3g}", ci=ci, u=unit)
                txt += "; " + (T("uvkin_sum_half", h=f"{f['half']:.3g}", u=unit) if f["half"] is not None
                               else T("uvkin_sum_rise"))
            elif self.st["fit"]:
                txt += "; " + T("uvkin_sum_nofit")
            lines.append(txt)
        self.lbl_summary.setText("\n".join(lines))

    def kpis(self):
        data = self.rows_data or {}
        name = next((n for n in data if len(data[n]["t"])), None)
        s = self.series_summary(name) if name else None
        if s is None:
            return []
        out = [(T("uvkin_kpi_rest", s=name), f"{fmt_pct(s['rest'])} %")]
        if s["fit"] is not None and s["fit"]["half"] is not None:
            out.append(("t½", f"{s['fit']['half']:.3g} {self.unit_used}"))
        return out

    def hover_text(self, x, val, name):
        if self.view() == "trace":
            return f"t = {x:.3g} {self.unit_used}    A = {val:.4g}    {name}" if val is not None else f"t = {x:.3g}"
        return super().hover_text(x, val, name)

    # -- SI ---------------------------------------------------------------------------
    def _cap_tail(self):
        from elucida.si.lines import chem_html
        st, h = self.st, ""
        if st.get("cap_solvent"):
            h += " in " + chem_html(st["cap_solvent"])
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        return h

    def si_caption(self, name):
        n = "<b>" + html.escape(name) + "</b>"
        if self.view() == "trace":
            lam = core.fmt_lam(self.lam_used) if self.lam_used else "–"
            h = f"Absorbance of {n} at {lam} nm"
            if self.st["win"] > 0:
                h = f"Maximum absorbance of {n} within {lam} ± {self.st['win']:g} nm"
            h += self._cap_tail() + " against time"
            if self.st["y"] == "rel":
                h += ", relative to the first spectrum of each series"
            h += "."
            if any(f is not None for f in self.fits.values()):
                h += " Dashed lines: first-order fits."
            return h
        h = f"UV-Vis spectra of {n}" + self._cap_tail()
        sname, series = self.shown_series()
        timed = [r for r in series.get(sname, []) if r["time"] is not None]
        if len(timed) > 1:
            span = (timed[-1]["time"] - timed[0]["time"]).total_seconds()
            u = self.unit(span)
            h += f" recorded over {fmt_t(span / UNIT_S[u])} {u}"
        return h + "."

    def methods_text(self):
        """Englisch, nur die benutzten Schritte: wo die Absorbanz abgelesen wurde, Bezug, Fit, Ergebnisse je Reihe."""
        st = self.st
        if self.view() != "trace" or not self.rows_data or self.lam_used is None:
            return ""
        lam, unit = core.fmt_lam(self.lam_used), self.unit_used
        m = ["Times were taken from the acquisition times recorded in the spectrometer files and are given relative "
             "to the first spectrum of each series."]
        if st["win"] > 0:
            m.append(f"For each spectrum, the maximum absorbance as measured within {lam} ± {st['win']:g} nm was used.")
        else:
            m.append(f"The absorbance as measured was read at {lam} nm (linear interpolation between data points).")
        if st["y"] == "rel":
            m.append("Relative values are given in percent of the absorbance of the first spectrum of the series.")
        if any(f is not None for f in self.fits.values()):
            m.append("Each series was fitted with a first-order decay, A(t) = A0·exp(−k·t), by least squares on the "
                     "measured absorbances (A0 determined linearly); 95% confidence intervals of k were obtained from "
                     "s²(JᵀJ)⁻¹ with s² = SSR/(n − 2) and t(0.975; n − 2), and half-lives as t1/2 = ln 2/k.")
        res = []
        for n in self.rows_data:
            s = self.series_summary(n)
            if s is None:
                continue
            r = (f"{n}: A = {s['A0']:.3f} to {s['A1']:.3f} ({fmt_pct(s['rest'])}% remaining after "
                 f"{fmt_t(s['dur'])} {unit}, n = {s['n']})")
            f = s["fit"]
            if f is not None:
                r += f", k = {sci_text(f['k'])} {unit}-1"
                if f["ci"]:
                    r += f" (95% interval {sci_text(f['ci'][0])} to {sci_text(f['ci'][1])} {unit}-1)"
                r += (f", t1/2 = {f['half']:.3g} {unit}" if f["half"] is not None
                      else " (absorbance increased; no half-life)")
            res.append(r)
        return " ".join(m) + ("\n\n" + "; ".join(res) + "." if res else "")

    def export_to(self, base: Path):
        """Abbildung + Kurvendaten wie überall, dazu eine CSV je Messpunkt (Reihe, Name, Zeit, A, relativ; Rohwerte)."""
        files = super().export_to(base)
        base = Path(base).resolve()
        p = base.with_name(base.name + "_kinetics.csv")
        unit = self.unit_used
        lam = core.fmt_lam(self.lam_used) if self.lam_used else ""
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["series", "name", f"t [{unit}]", "t [s]", f"A ({lam} nm)", "relative [%]"])
            for n, d in (self.rows_data or {}).items():
                for lab, t, a, r in zip(d["labels"], d["t"], d["A"], d["rel"]):
                    w.writerow([n, lab, f"{t / UNIT_S[unit]:.6g}", f"{t:.0f}", f"{a:.6g}", f"{r:.6g}"])
        files.append(p)
        return files
