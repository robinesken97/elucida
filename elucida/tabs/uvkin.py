"""elucida/tabs/uvkin.py - UV-Vis-Kinetik: wie sich die Spektren einer Lösung über die Zeit ändern (Stabilität über Tage,
Reaktion). Spektren aus einer oder mehreren Cary-Dateien, je Zeile eine Reihe (z. B. Konzentration); Zeit nur aus der
Messdatei („Collection Time“ des Cary-CSV-Exports), nie aus Dateinamen oder Dateizeiten.

Ansichten: Spektren einer Reihe im Farbverlauf der Zeit; Absorbanz bei λ (oder Maximum im Fenster ± n nm) gegen die
Zeit seit dem ersten Spektrum der Reihe, wie gemessen oder relativ zum ersten Spektrum; optional Zerfall erster Ordnung
A(t) = A0·exp(−k·t) je Reihe (`EPR.fit_first_order`, kleinste Quadrate auf den gemessenen Werten).

Titration (Auftrag 2026-11-13, SI-Lückenanalyse Punkt 8): Zeilen mit Äquivalenten (Spalte „Äq.“, aus dem Namen
vorgeschlagen, wenn eindeutig) bilden eine Spektrenschar gegen die zugegebenen Äquivalente (Farbverlauf in der
Reihenfolge der Äquivalente, isosbestische Punkte nur, wo alle Spektren innerhalb der Toleranz übereinstimmen und sich die
Änderung umkehrt) und die Absorbanz bei λ gegen die Äquivalente. Keine Bindungskonstanten, keine Verdünnungskorrektur.
"""
from __future__ import annotations

import html
import re
import uuid
from pathlib import Path

import numpy as np
from PySide6.QtCore import QItemSelectionModel, Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from elucida.core import uvvis as core
from elucida.tabs import base as TABS
from elucida.tabs.epr import fit_first_order, sci_range, sci_signed
from elucida.app.i18n import T, T_en
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


_EQ_RE = re.compile(r"(?<![\d.,p])(\d+(?:[.,p]\d+)?)\s*-?\s*(?:eq|equiv|äq|aeq)\.?(?![a-z])", re.IGNORECASE)
TITR_VIEWS = ("titr", "titr_trace")


def eq_from_name(name):
    """Äquivalente aus einem Namen („…_0.5eq“, „1,5 equiv“, „0p25eq“) nur bei genau einem Treffer, sonst None."""
    hits = _EQ_RE.findall(str(name))
    return float(hits[0].replace(",", ".").replace("p", ".")) if len(hits) == 1 else None


def fmt_eq(v):
    return f"{core.round_half_up(v, 3):g}"


def isosbestic(rows, tol, lo=None, hi=None, reach=20.0):
    """Isosbestische Punkte einer Spektrenschar (mindestens drei Spektren, Liste dict(x, y) in Reihenfolge).
    Kandidaten: Nulldurchgänge der Änderung letztes − erstes Spektrum. Ein Punkt gilt nur, wenn (1) dort alle Spektren
    innerhalb `tol` (Spannweite max − min, Absorbanz) übereinstimmen und (2) die Änderung beiderseits innerhalb `reach`
    nm deutlich (> 3·tol) und mit entgegengesetztem Vorzeichen ist – sonst keiner (Grundlinie, Rauschen).
    -> [dict(lam, A, spread)] aufsteigend nach λ."""
    if tol <= 0 or len(rows) < 3:
        return []
    xs = [np.asarray(r["x"], float) for r in rows]
    a, b = max(x.min() for x in xs), min(x.max() for x in xs)
    if lo is not None:
        a, b = max(a, lo), min(b, hi)
    x0 = np.sort(xs[0])
    grid = x0[(x0 >= a) & (x0 <= b)]
    if len(grid) < 5:
        return []
    Y = np.array([np.interp(grid, np.sort(x), np.asarray(r["y"], float)[np.argsort(x)]) for x, r in zip(xs, rows)])
    spread = Y.max(axis=0) - Y.min(axis=0)
    d = Y[-1] - Y[0]
    step = float(np.median(np.diff(grid)))
    near = max(2.0, 2 * step)
    out = []
    for j in np.flatnonzero(np.sign(d[:-1]) * np.sign(d[1:]) < 0):
        w = (grid >= grid[j] - near) & (grid <= grid[j + 1] + near)
        k = np.flatnonzero(w)[np.argmin(spread[w])]
        if spread[k] > tol:
            continue
        left = (grid >= grid[k] - reach) & (grid < grid[k])
        right = (grid > grid[k]) & (grid <= grid[k] + reach)
        if not left.any() or not right.any():
            continue
        dl, dr = d[left][np.argmax(np.abs(d[left]))], d[right][np.argmax(np.abs(d[right]))]
        if abs(dl) <= 3 * tol or abs(dr) <= 3 * tol or np.sign(dl) == np.sign(dr):
            continue
        p = {"lam": float(grid[k]), "A": float(Y[:, k].mean()), "spread": float(spread[k])}
        if out and p["lam"] - out[-1]["lam"] < 5.0:          # derselbe Schnittpunkt: der engere bleibt
            if p["spread"] < out[-1]["spread"]:
                out[-1] = p
            continue
        out.append(p)
    return out


def is_baseline(name):
    """Gerätebasislinien („Baseline 100%T“, „Baseline 0%T“) sind keine Spektren (wie read_binary_samples)."""
    return str(name).strip().lower().startswith("baseline")


def series_from_name(name):
    """Reihe nur, wenn der Probenname eine Konzentration eindeutig nennt (core.parse_sample_name), sonst ''."""
    p = core.parse_sample_name(str(name))
    return f"{p[1]:g} {core.unit_text(p[2])}" if p else ""


class UVKinTab(TABS.FigureTab):
    LABEL_CARD = True                    # Karte „Beschriftungen im Bild“ (eigene Labels; Entscheidung 169: alle Tabs)

    def label_view(self):
        return self.st.get("view") or ""
    STATE_KEY = "uvkin"
    GUIDE, GUIDE_ACTION = "uvkin", ("guide_add", "add_files")
    TEXT_OPTS = ("fonts", "axes_frame")
    CAP_FIELDS = ("solvent", "conc", "reagent")
    SI_CAPTION = "UV-Vis spectra of {name}."
    X_RANGE = (100, 3500, 0, 10)
    RESET_KEEP = ("entries",                        # Spektren samt Reihe, Name und Häkchen
                  "view", "series", "lam", "win", "y", "t_unit", "fit", "iso_tol",   # Auswertung
                  "x_auto", "x_min", "x_max")       # Bereich: λ ohne Eingabe und isosbestische Punkte darin
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=250.0, x_max=800.0, ymax=0.0, entries=[], view="", series="",
                         lam=0.0, win=0.0, y="abs", t_unit="auto", fit=False, cap_solvent="", cap_conc="",
                         iso_tol=0.01, cap_reagent="")

    def arrange(self):
        super().arrange()
        self.to_right(self.grp_results, T("tab_results"))

    # -- linke Spalte ---------------------------------------------------------------
    def build_controls(self):
        st = self.st
        self.rows_data, self.fits, self.notes = [], {}, []
        g = QGroupBox(T("uvkin_spectra"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()                                    # eine Reihe wie in CV, H-Cell und X-Ray
        for txt, fn in ((T("guide_add"), self.add_files), ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                        (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("uvkin_series"), T("uvkin_time"), T("uvtit_eq_col")])
        self.table.horizontalHeaderItem(2).setToolTip(T("uvkin_series_tip"))
        self.table.horizontalHeaderItem(3).setToolTip(T("uvkin_time_tip"))
        self.table.horizontalHeaderItem(4).setToolTip(T("uvtit_eq_tip"))
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
        for key in TITR_VIEWS:
            self.cmb_view.addItem(T("uvtit_view_" + key), key)
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
        self.sp_tol = QDoubleSpinBox(decimals=3, minimum=0, maximum=0.5, singleStep=0.001, value=st["iso_tol"])
        self.sp_tol.setSpecialValueText(T("off"))
        self.sp_tol.setToolTip(T("uvtit_tol_tip"))
        self._rows = {}
        for key_, lab_, w_ in (("series", "uvkin_series", self.cmb_series), ("lam", "uvkin_lam", self.sp_lam),
                               ("win", "uvkin_win", self.sp_win), ("y", "uvkin_y", self.cmb_y),
                               ("unit", "uvkin_unit", self.cmb_unit), ("tol", "uvtit_tol", self.sp_tol)):
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
        self.res_table = STYLE.name_table(STYLE.FitGrid(0, 5), "results", "Measurements")   # CSV: _results/_titration
        self.res_table.verticalHeader().setVisible(False)
        self.res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        STYLE.empty_note(self.res_table, T("uvkin_results_none"))
        rv.addWidget(self.res_table)
        self.tbl_summary = STYLE.name_table(STYLE.summary_grid(self._sum_heads("s"), rich=(6, 7)), "summary",
                                            "Summary per series", csv=True)   # je Reihe: Verlauf und Zerfall; k wie im Methodentext
        rv.addWidget(self.tbl_summary)
        self.tbl_iso = STYLE.name_table(STYLE.summary_grid(["λ_iso [nm]", "A" + STYLE.QTY, T("uvtit_col_spread")]),
                                        "isosbestic", "Isosbestic points", csv=True)   # Titration
        rv.addWidget(self.tbl_iso)
        self.lv.addWidget(self.grp_results)
        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export (Reiter SI-Text)

        self.fill_table()
        self.fill_series()
        self._sync_view_combo()
        for w_ in (self.sp_lam, self.sp_win, self.sp_tol):
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
        if v in ("spectra", "trace") + TITR_VIEWS:
            return v
        return "trace" if any(len([r for r in rows if r["time"] is not None]) >= 2
                              for rows in self.series_rows().values()) else "spectra"

    def _sync_view_combo(self):
        self.cmb_view.blockSignals(True)
        self.cmb_view.setCurrentIndex(max(0, self.cmb_view.findData(self.view())))
        self.cmb_view.blockSignals(False)

    def _view_fields(self, *_):
        v = self.cmb_view.currentData()
        lam = v in ("trace", "titr_trace")
        show = {"series": v == "spectra", "lam": lam, "win": lam, "y": v == "trace", "unit": v in ("spectra", "trace"),
                "tol": v == "titr"}
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
                       y=self.cmb_y.currentData(), t_unit=self.cmb_unit.currentData(), fit=self.cb_fit.isChecked(),
                       iso_tol=self.sp_tol.value())

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
            real = [s_ for s_ in smp if not is_baseline(s_["name"])]
            for k, s_ in enumerate(smp):
                if is_baseline(s_["name"]) or (q, k) in have:
                    continue
                eq = eq_from_name(s_["name"])
                if eq is None and len(real) == 1:           # eine Probe je Datei: Dateiname darf es nennen
                    eq = eq_from_name(Path(p).stem)
                es.append({"uid": uuid.uuid4().hex[:8], "file": q, "idx": k, "label": s_["name"],
                           "series": "" if eq is not None else series_from_name(s_["name"]), "use": True, "eq": eq})
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
            self.table.setItem(i, 4, QTableWidgetItem(fmt_eq(e["eq"]) if e.get("eq") is not None else ""))
        self.sync_columns()
        # so hoch wie die Zeilen (3 bis 8, darüber scrollen): nie eine halb sichtbare Zeile
        self.table.setFixedHeight(self.table.horizontalHeader().sizeHint().height()
                                  + max(3, min(len(es), 8)) * STYLE.CHECK_ROW_H + 2)
        self._loading = False
        self.show_details()
        self.show_row_hint()

    def show_row_hint(self):
        es = [e for e in self.st["entries"] if e.get("use", True) and e.get("eq") is None]   # Titration: ohne Reihe
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
        elif item.column() == 4:                          # Äquivalente: Zahl (auch mit Komma) oder leer
            txt = item.text().strip().replace(",", ".")
            v = TABS.parse_num(txt) if txt else None
            if txt and (v is None or v < 0):
                self._loading = True
                item.setText(fmt_eq(e["eq"]) if e.get("eq") is not None else "")
                self._loading = False
                return
            e["eq"] = v
            self.show_row_hint()
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
        self.titr_data, self.iso = [], []
        if not st["entries"]:
            self.show_results()
            return None
        titr = self.view() in TITR_VIEWS
        n_off = sum(1 for e in st["entries"] if e.get("use", True) and e.get("eq") is None
                    and not str(e.get("series", "")).strip())
        if n_off and not titr:
            self.add_note(T("uvkin_no_series", n=n_off))
        gone = sum(1 for e in st["entries"] if self.sample_of(e) is None)
        if gone:
            self.add_note(T("uvkin_gone", n=gone))
        data, lam, unit = self.trace()
        self.rows_data, self.lam_used, self.unit_used = data, lam, unit
        self.fits = self.fit_series(data) if st["fit"] else {}
        self.titr_data, self.iso = [], []
        if titr:
            spec = self.titr_spec()
        else:
            spec = self.spectra_spec() if self.view() == "spectra" else self.trace_spec(data, lam, unit)
        self.show_results()
        return spec

    # -- Titration --------------------------------------------------------------------
    def titr_rows(self):
        """Benutzte Zeilen mit Äquivalenten und lesbarer Datei, nach Äquivalenten (bei Gleichstand Listenreihenfolge)."""
        out = []
        for e in self.st["entries"]:
            if not e.get("use", True) or e.get("eq") is None:
                continue
            s_ = self.sample_of(e)
            if s_ is not None:
                out.append({"e": e, "x": s_["x"], "y": s_["y"], "eq": float(e["eq"])})
        return sorted(out, key=lambda r: r["eq"])

    def titr_spec(self):
        """Spektrenschar gegen Äquivalente (Ansicht „titr“) oder A(λ) gegen Äquivalente („titr_trace“)."""
        st = self.st
        rows = self.titr_data = self.titr_rows()
        if not rows:
            self.add_note(T("uvtit_none"))
            return None
        self.lam_used = st["lam"] if st["lam"] > 0 else self.auto_lam(rows)
        cfg = self.base_cfg()
        if self.view() == "titr_trace":
            eq = np.array([r["eq"] for r in rows])
            A = np.array([value_at(r["x"], r["y"], self.lam_used, st["win"]) for r in rows])
            for r, a in zip(rows, A):
                r["A"] = a
            ok = np.isfinite(A)
            if not ok.any():
                self.add_note(T("uvtit_lam_out", lam=core.fmt_lam(self.lam_used)))
                return None
            curves = [{"x": eq[ok], "y": A[ok], "color": "#000000", "label": None, "ls": "-", "lw": 0.8, "marker": "o",
                       "ms": 6}]
            pad = 0.05 * (float(np.ptp(eq)) or 1.0)
            cfg["xlim"] = [float(eq.min()) - pad, float(eq.max()) + pad]
            lo, hi = float(np.nanmin(A)), float(np.nanmax(A))
            span = (hi - lo) or 1.0
            cfg["ylim"] = [min(0.0, lo - 0.1 * span), st["ymax"] if st["ymax"] > 0 else hi + 0.15 * span]
            cfg["xlabel"], cfg["ylabel"] = "equivalents", f"absorbance at {core.fmt_lam(self.lam_used)} nm"
            cfg["legend"] = False
            cfg["y_axis"] = "numbers"
            return cfg, curves, [], []
        from matplotlib import colormaps
        from matplotlib.colors import to_hex
        curves = []
        for k, r in enumerate(rows):
            col = to_hex(colormaps["viridis"](0.85 * k / max(1, len(rows) - 1))) if len(rows) > 1 else "#000000"
            curves.append({"x": r["x"], "y": r["y"], "color": col, "label": f"{fmt_eq(r['eq'])} equiv", "ls": "-",
                           "lw": 1.2})
        xs = np.concatenate([c["x"] for c in curves])
        x0, x1 = (float(xs.min()), float(xs.max())) if st["x_auto"] else (st["x_min"], st["x_max"])
        cfg["xlim"] = [x0, x1]
        self.iso = isosbestic(rows, st["iso_tol"], x0, x1)
        # Kreis am Schnittpunkt; λ steht in Unterschrift, Tabelle und Kachel (ein Label läge zwischen den Kurven)
        for p_ in self.iso:
            curves.append({"x": np.array([p_["lam"]]), "y": np.array([p_["A"]]), "color": "#000000", "label": None,
                           "ls": "none", "marker": "o", "ms": 6, "aux": True})
        vals = np.concatenate([c["y"][(c["x"] >= x0) & (c["x"] <= x1)] for c in curves])
        vals = vals[np.isfinite(vals)]
        top = float(vals.max()) if len(vals) else 1.0
        bot = min(0.0, float(vals.min())) if len(vals) else 0.0
        span_y = (top - bot) or 1.0
        cfg["ylim"] = [bot - 0.03 * span_y, st["ymax"] if st["ymax"] > 0 else top + 0.08 * span_y]
        cfg["xlabel"], cfg["ylabel"] = "wavelength [nm]", "absorbance"
        cfg["legend"], cfg["legend_beside"] = True, True
        return cfg, curves, [], []

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

    @staticmethod
    def _sum_heads(unit):
        return [T("uvkin_series"), T("uvkin_col_a0"), T("uvkin_col_a1"), T("uvkin_col_rest"),
                f"{T('uvkin_col_dur')} [{unit}]", T("uvkin_col_n"), f"k [{unit}⁻¹]", T("uvkin_col_ci"), f"t½ [{unit}]",
                T("col_warn")]

    def show_titr_results(self):
        """Titration: je Spektrum Äquivalente, Name, A(λ); darunter die isosbestischen Punkte."""
        rows = self.titr_data or []
        lam = core.fmt_lam(self.lam_used) if self.lam_used else "–"
        self.res_table.setHorizontalHeaderLabels([T("uvtit_eq_col"), T("ov_name"), f"A ({lam} nm)", "", ""])
        self.res_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            a = r.get("A", value_at(r["x"], r["y"], self.lam_used, self.st["win"]) if self.lam_used else float("nan"))
            for j, txt in enumerate((fmt_eq(r["eq"]), r["e"]["label"], f"{a:.3f}" if np.isfinite(a) else "–")):
                self.res_table.setItem(i, j, QTableWidgetItem(txt))
        for c in (3, 4):
            self.res_table.setColumnHidden(c, True)
        self.res_table.fit()
        STYLE.fill_summary(self.tbl_summary, [])
        STYLE.fill_summary(self.tbl_iso, [[STYLE.num(core.fmt_lam(p_["lam"]), p_["lam"]), STYLE.num(f"{p_['A']:.3f}", p_["A"]),
                                           STYLE.num(f"{p_['spread']:.3f}", p_["spread"])]
                                          for p_ in self.iso] if self.view() == "titr" else [])

    def sync_columns(self):
        """Keine dauerhaft leere Spalte: „Reihe“ nicht in der Titration, „Äq.“ nicht in der Kinetik, solange leer."""
        es, titr = self.st["entries"], self.view() in TITR_VIEWS
        self.table.setColumnHidden(2, titr and not any(e.get("series") for e in es))
        self.table.setColumnHidden(4, not titr and not any(e.get("eq") is not None for e in es))
        STYLE.fit_columns(self.table)

    def show_results(self):
        """Ergebnisseite: Messpunkte je Reihe (Reihe, Name, t, A, relativ) und Zusammenfassung je Reihe."""
        if not hasattr(self, "res_table"):
            return
        self.sync_columns()
        if self.view() in TITR_VIEWS:
            return self.show_titr_results()
        for c in (3, 4):
            self.res_table.setColumnHidden(c, False)
        STYLE.fill_summary(self.tbl_iso, [])
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
        self.res_table.fit()
        srows, notes = [], False
        for n in data:
            s = self.series_summary(n)
            if s is None:
                srows.append([n] + ["–"] * 8 + [STYLE.num(T("uvkin_sum_none"), T_en("uvkin_sum_none"))])
                notes = True
                continue
            f, note = s["fit"], ""
            if f is None and self.st["fit"]:
                note = STYLE.num(T("uvkin_sum_nofit"), T_en("uvkin_sum_nofit"))
            elif f is not None and f["half"] is None:
                note = STYLE.num(T("uvkin_sum_rise"), T_en("uvkin_sum_rise"))
            notes = notes or bool(note)
            N = STYLE.num
            srows.append([n, N(f"{s['A0']:.3f}", s["A0"]), N(f"{s['A1']:.3f}", s["A1"]), N(fmt_pct(s["rest"]), s["rest"]),
                          N(fmt_t(s["dur"]), s["dur"]), str(s["n"]),
                          N(sci_signed(f["k"]), f["k"]) if f else "–",
                          sci_range(*f["ci"]) if f and f["ci"] else "–",
                          N(f"{f['half']:.3g}", f["half"]) if f and f["half"] is not None else "–", note])
        self.tbl_summary.setHorizontalHeaderLabels(self._sum_heads(unit))
        STYLE.rich_header(self.tbl_summary)
        fitted = any(r[6] != "–" for r in srows)
        STYLE.fill_summary(self.tbl_summary, srows, hidden=(() if fitted else (6, 7, 8)) + (() if notes else (9,)))

    def kpis(self):
        if self.view() in TITR_VIEWS:
            out = [(T("uvtit_kpi_n"), str(len(self.titr_data or [])))]
            if self.view() == "titr":
                out.append(("λ_iso", " / ".join(core.fmt_lam(p_["lam"]) for p_ in self.iso) + " nm" if self.iso
                            else T("uvtit_kpi_none")))
            return out
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
        if self.view() == "titr_trace":
            return f"{fmt_eq(x)} equiv    A = {val:.4g}" if val is not None else f"{fmt_eq(x)} equiv"
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

    def _reagent(self):
        from elucida.si.lines import chem_html
        r = (self.st.get("cap_reagent") or "").strip()
        return chem_html(r) if r else ""

    def titr_caption(self, name, view):
        n = "<b>" + html.escape(name) + "</b>"
        rows = self.titr_data or []
        rng = f"{fmt_eq(rows[0]['eq'])}–{fmt_eq(rows[-1]['eq'])} equiv" if len(rows) > 1 else ""
        reag = self._reagent()
        add = f" of {reag}" if reag else ""
        if view == "titr_trace":
            lam = core.fmt_lam(self.lam_used) if self.lam_used else "–"
            what = (f"Maximum absorbance of {n} within {lam} ± {self.st['win']:g} nm" if self.st["win"] > 0
                    else f"Absorbance of {n} at {lam} nm")
            return what + self._cap_tail() + f" against the equivalents{add} added."
        h = f"UV-Vis spectra of {n}" + self._cap_tail() + f" upon addition of {rng or 'equivalents'}{add}."
        if self.view() == "titr" and self.iso:
            lams = [core.fmt_lam(p_["lam"]) for p_ in self.iso]
            h += (" Isosbestic point at " if len(lams) == 1 else " Isosbestic points at ") + (
                ", ".join(lams[:-1]) + " and " + lams[-1] if len(lams) > 1 else lams[0]) + " nm (circles)."
        return h

    def si_caption(self, name):
        n = "<b>" + html.escape(name) + "</b>"
        if self.view() in TITR_VIEWS:
            return self.titr_caption(name, self.view())
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

    def titr_methods(self):
        st, rows = self.st, self.titr_data or []
        if not rows:
            return ""
        m = ["Spectra are shown as measured against the equivalents added (no correction for dilution)."]
        lam = core.fmt_lam(self.lam_used) if self.lam_used else None
        if lam and self.view() == "titr_trace":
            m.append(f"For each spectrum, the maximum absorbance within {lam} ± {st['win']:g} nm was used." if st["win"] > 0
                     else f"The absorbance was read at {lam} nm (linear interpolation between data points).")
        res = ""
        if self.view() == "titr":
            if st["iso_tol"] > 0 and len(rows) >= 3:
                m.append(f"Isosbestic points were taken as wavelengths at which the absorbances of all {len(rows)} "
                         f"spectra agree within {st['iso_tol']:g} (maximum − minimum) and the change between the first "
                         "and the last spectrum reverses its sign.")
                res = ("Isosbestic points: " + ", ".join(f"{core.fmt_lam(p_['lam'])} nm (A = {p_['A']:.3f})"
                                                         for p_ in self.iso) + "." if self.iso
                       else "No isosbestic point was found within this tolerance.")
        return " ".join(m) + ("\n\n" + res if res else "")

    def methods_text(self):
        """Englisch, nur die benutzten Schritte: wo die Absorbanz abgelesen wurde, Bezug, Fit, Ergebnisse je Reihe."""
        st = self.st
        if self.view() in TITR_VIEWS:
            return self.titr_methods()
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
                r += f", k = {sci_signed(f['k'])} {unit}-1"
                if f["ci"]:
                    r += f" (95% interval {sci_signed(f['ci'][0])} to {sci_signed(f['ci'][1])} {unit}-1)"
                r += (f", t1/2 = {f['half']:.3g} {unit}" if f["half"] is not None
                      else " (absorbance increased; no half-life)")
            res.append(r)
        return " ".join(m) + ("\n\n" + "; ".join(res) + "." if res else "")

    def si_figure(self, out_dir, name):
        """Titration: Spektrenschar und A(λ) gegen Äquivalente als zwei Abbildungen; sonst die gezeigte Ansicht."""
        v = self.view()
        if v not in TITR_VIEWS:
            return super().si_figure(out_dir, name)
        out = []
        try:
            for view in TITR_VIEWS:
                self.st["view"] = view
                fig = TABS.MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
                TABS.FigureCanvasAgg(fig)
                F = self.build(fig)
                if F is None:
                    continue
                svg = Path(out_dir) / f"{core.safe_name(name)}_{self.STATE_KEY}_{view}.svg"
                out += [TABS.si_image(F, svg), ("figcap", self.titr_caption(name, view))]
        finally:
            self.st["view"] = v
            self.figure_spec()                            # Ergebnisse wieder für die gezeigte Ansicht
        return out

    def export_to(self, base: Path):
        """Abbildung + Kurvendaten wie überall, dazu eine CSV je Messpunkt (Reihe, Name, Zeit, A, relativ; Rohwerte)."""
        files = super().export_to(base)
        base = Path(base).resolve()
        from elucida.core import tables as TBL
        if self.view() in TITR_VIEWS:                    # Titration: Äquivalente, Name, A(λ)
            lam = self.lam_used or self.auto_lam(self.titr_rows())
            files.append(TBL.write_csv(base.with_name(base.name + "_titration.csv"),
                                       ["equiv", "name", f"A ({core.fmt_lam(lam)} nm)"],
                                       [[r["eq"], r["e"]["label"], value_at(r["x"], r["y"], lam, self.st["win"])]
                                        for r in self.titr_rows()]))
            return files
        unit = self.unit_used                            # <Verbindung>_UV-Vis-kinetics_results.csv (bis 1.3: _kinetics)
        lam = core.fmt_lam(self.lam_used) if self.lam_used else ""
        p = TBL.write_csv(base.with_name(base.name + "_results.csv"),
                          ["series", "name", f"t [{unit}]", "t [s]", f"A ({lam} nm)", "relative [%]"],
                          [[n, lab, t / UNIT_S[unit], t, a, r] for n, d in (self.rows_data or {}).items()
                           for lab, t, a, r in zip(d["labels"], d["t"], d["A"], d["rel"])])
        files.append(p)
        return files
