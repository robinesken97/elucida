"""elucida/tabs/sec.py - Spektroelektrochemie: Spektrenserie (B&W Tek BWSpec) + Potential (Gamry), SEC-Tab.

Zuordnung Spektrum -> Potential über die Uhrzeit: t = Aufnahmezeit des Spektrums − Startzeit der Gamry-Messung
(+ einstellbarer Versatz, z. B. für Wartezeiten vor dem Scan); E = E(t) aus der Gamry-Tabelle interpoliert.
Spektren vor Beginn bzw. nach Ende des Scans behalten das Start- bzw. Endpotential (Ruhepotential).

Nernst-Fit für A(λ, E): A = A_red + (A_ox − A_red) / (1 + exp(−n·F·(E − E½)/(R·T))); E½ und n per Raster,
A_red/A_ox jeweils linear (kleinste Quadrate).
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox)

from elucida.tabs import cv as CV
from elucida.tabs import base as TABS
from elucida.app.i18n import T
from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.style import HINT_CSS, make_form
from elucida.formats.bwspec import (read_bwspec, is_bwspec, is_merged, merged_quantity,  # noqa: E402,F401
                                    read_spectrum)                                   # (Leser in elucida/formats)

F_RT = 96485.332 / (8.314462 * 298.15)          # 1/V bei 25 °C


def gamry_start(meta) -> dt.datetime | None:
    """Startzeit einer Gamry-Messung aus DATE (M/D/YYYY) und TIME (H:MM:SS)."""
    for fmt in ("%m/%d/%Y %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(f"{meta.get('date', '')} {meta.get('time', '')}".strip(), fmt)
        except ValueError:
            continue
    return None


def potentials(spectra, gamry, offset_s=0.0, with_outside=False):
    """Potential je Spektrum (V vs. Referenzelektrode) über die Uhrzeit; None, wenn keine Zeiten.
    with_outside: (Potentiale, Anzahl Spektren außerhalb der Messung)."""
    t0 = gamry_start(gamry["meta"])
    if t0 is None or any(s["time"] is None for s in spectra):
        return (None, 0) if with_outside else None
    E = np.concatenate([c["E"] for c in gamry["cycles"]])
    T = np.concatenate([c["T"] for c in gamry["cycles"]])
    if not np.isfinite(T).all():                      # Datei ohne Zeitspalte
        return (None, 0) if with_outside else None
    o = np.argsort(T)
    ts = np.array([(s["time"] - t0).total_seconds() + offset_s for s in spectra])
    out = np.interp(ts, T[o], E[o])                   # außerhalb: Start- bzw. Endpotential
    return (out, int(np.sum((ts < T.min() - 30) | (ts > T.max() + 30)))) if with_outside else out


def file_number(name):
    """Laufende Nummer im Dateinamen („Merge_0012.Abs8“ -> 12) oder None."""
    m = re.search(r"(\d+)(?:\.[A-Za-z]+\d*)?$", name)
    return int(m[1]) if m else None


def parse_map(text):
    """Zuordnungstabelle -> {Nr.: Wert}. Zeilen „Nr; Wert“ oder „von-bis; Wert“ (Spektren-Nr. wie im Tab)."""
    out = {}
    for n, ln in enumerate(text.splitlines(), 1):
        if not ln.strip():
            continue
        m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*[;:\t ]\s*([-+−]?\d+(?:[.,]\d+)?)\s*", ln)
        if not m:
            raise ValueError(T("sec_map_bad", n=n))
        v = float(m[3].replace(",", ".").replace("−", "-"))
        out.update({k: v for k in range(int(m[1]), int(m[2] or m[1]) + 1)})
    return out


def assign_potentials(sp, gamry, st):
    """Serien ohne Zeitstempel -> (E, Maske zugeordnet, Hinweise) oder (None, None, Hinweise).
    Nur bestätigte Angaben zählen: nie Dateizeiten, nie gleichmäßig über die Laufzeit verteilen. Außerhalb der Messung
    gibt es kein Potential (kein Klemmen auf Start-/Endwert wie bei echten Zeitstempeln)."""
    mode = st["map_mode"]
    if mode == "none" or not st["map_ok"]:
        return None, None, []
    n = len(sp)
    try:
        table = parse_map(st["map_table"]) if mode in ("time", "potential") else {}
    except ValueError as ex:
        return None, None, [str(ex)]
    nums = [file_number(s["name"]) for s in sp]
    keys = nums if None not in nums else list(range(1, n + 1))    # Dateinummer: Lücken verschieben nichts
    if mode == "potential":
        E = np.array([table.get(k, np.nan) for k in keys])
        keep = np.isfinite(E)
    else:
        if gamry is None:
            return None, None, [T("sec_map_no_dta")]
        Eg = np.concatenate([c["E"] for c in gamry["cycles"]])
        Tg = np.concatenate([c["T"] for c in gamry["cycles"]])
        if not np.isfinite(Tg).all():
            return None, None, [T("sec_no_time")]
        if mode == "interval":
            if st["map_step"] <= 0:
                return None, None, [T("sec_map_no_step")]
            t = st["map_start"] + (np.array(keys, float) - keys[0]) * st["map_step"]
        else:
            t = np.array([table.get(k, np.nan) for k in keys])
        keep = np.isfinite(t) & (t >= Tg.min()) & (t <= Tg.max())
        o = np.argsort(Tg)
        E = np.interp(np.nan_to_num(t), Tg[o], Eg[o])
    notes = [T("sec_map_partial", k=int(keep.sum()), n=n)] if not keep.all() else []
    return (E, keep, notes) if keep.any() else (None, None, notes + [T("sec_map_empty")])


def nernst_fit(E, A, n_range=(0.3, 3.0)):
    """A(E) sigmoidal anpassen -> dict(e12, n, a_red, a_ox, r2, bound) oder None.
    bound = True: Optimum am Rand des Rasters (E½ am Rand der Messpunkte oder n an einer Grenze von n_range) –
    dann nicht bestimmbar, nicht als Ergebnis angeben."""
    E, A = np.asarray(E, float), np.asarray(A, float)
    ok = np.isfinite(E) & np.isfinite(A)
    E, A = E[ok], A[ok]
    if len(E) < 5 or np.ptp(A) <= 0 or len(np.unique(np.round(E, 4))) < 3:   # ohne Potentialänderung unbestimmt
        return None
    best = None
    for n in np.arange(n_range[0], n_range[1] + 1e-9, 0.05):
        for e12 in np.arange(E.min(), E.max() + 1e-9, 0.002):
            s = 1.0 / (1.0 + np.exp(-n * F_RT * (E - e12)))
            M = np.column_stack([1 - s, s])
            coef, *_ = np.linalg.lstsq(M, A, rcond=None)
            res = float(np.sum((M @ coef - A) ** 2))
            if best is None or res < best[0]:
                best = (res, e12, n, coef)
    res, e12, n, (a_red, a_ox) = best
    ss = float(np.sum((A - A.mean()) ** 2))
    bound = bool(e12 - E.min() < 0.003 or E.max() - e12 < 0.003 or n < n_range[0] + 0.025
                 or n > n_range[1] - 0.025)
    return {"e12": float(e12), "n": float(n), "a_red": float(a_red), "a_ox": float(a_ox),
            "r2": 1 - res / ss if ss > 0 else float("nan"), "bound": bound}


# ----------------------------------------------------------------------------
# SEC-Tab
# ----------------------------------------------------------------------------
POT_CMAP = LinearSegmentedColormap.from_list("pot", ["#1764e8", "#8a2be2", "#e8231b"])
START_COLOR, END_COLOR = "#1764e8", "#e8231b"          # wie üblich: Ausgangsspektrum blau, Endspektrum rot
# Zwischenspektren (Zwischenstufe, z. B. Radikalkation) wie in der SI grün, weitere aus fester Palette;
# die englischen Namen stehen in der Bildunterschrift
MID_COLORS = (("#2e9e3e", "green"), ("#f28e1c", "orange"), ("#8a2be2", "purple"), ("#17a2b8", "teal"))
LAM_RANGE = (250.0, 850.0)                              # brauchbarer Bereich des Spektrometers (Ränder verrauscht)


def _hex(c):
    return c if isinstance(c, str) else "#%02x%02x%02x" % tuple(int(255 * v) for v in c[:3])


def _natural(name):
    """Sortierschlüssel mit Zahlen als Zahlen (s_2 vor s_10)."""
    return [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.split(r"(\d+)", str(name)) if x]


def _floats(text):
    out = []
    for x in str(text).replace(";", ",").split(","):
        try:
            out.append(float(x.strip().replace("−", "-")))
        except ValueError:
            pass
    return out


class SECTab(TABS.FigureTab):
    STATE_KEY = "sec"
    GUIDE, GUIDE_ACTION = "sec", ("guide_add", "choose_spectra")
    TEXT_OPTS = ("fonts", "greek", "labels", "label_size", "axes_frame")
    CAP_FIELDS = ("solvent", "start", "mid", "end")
    SI_CAPTION = "UV-Vis spectroelectrochemistry of {name}."
    RESET_KEEP = ("spec_files", "dta", "offset_s", "e_shift", "electrode", "ref_from_cv", "mid", "quantity",
                  "map_mode", "map_start", "map_step", "map_table", "map_ok", "import_note")  # Daten, Zeit, Referenz
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=250.0, x_max=850.0, ymax=0.0, spec_files=[], dta=None,
                         mode="spectra", first=1, last=0, highlight=True, mid="", gradient=False, diff=False,
                         baseline=False, bands="", trace_lams="", fit=True, offset_s=0.0, e_shift=0.0,
                         electrode="Ag/AgNO₃", ref_from_cv=False, cap_solvent="", cap_start="", cap_mid="",
                         cap_end="", quantity="abs", map_mode="none", map_start=0.0, map_step=0.0, map_table="",
                         map_ok=False, import_note="")


    def arrange(self):
        super().arrange()
        # Fit-Ergebnis + „SI-Text kopieren“ als Reiter neben der Abbildung wie in CV (nicht mitten in „Darstellung“)
        self.to_right(STYLE.split_group(self.group_titled("sec_display"), self.lbl_info, None, T("tab_results"), n=2),
                      T("tab_results"))
        g = STYLE.split_group(self.group_titled("sec_display"), self.cb_highlight, self.ed_bands, T("grp_highlight"))
        self.fold(g, "highlight", ("highlight", "mid", "gradient", "diff", "baseline", "bands"))
    def build_controls(self):
        st = self.st
        self.info = {}
        g = QGroupBox(T("sec_data"))
        f = make_form(g)
        row = QHBoxLayout()
        self.lbl_spec = QLabel("–")
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose_spectra)
        row.addWidget(self.lbl_spec, 1)
        row.addWidget(b)
        f.addRow(T("sec_spectra"), row)
        row = QHBoxLayout()
        self.lbl_dta = QLabel(Path(st["dta"]).name if st["dta"] else "–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        b1.clicked.connect(self.choose_dta)
        b2.clicked.connect(lambda: self._set("dta", None))
        for w_ in (self.lbl_dta, b1, b2):
            row.addWidget(w_, 1 if w_ is self.lbl_dta else 0)
        f.addRow(T("sec_potential"), row)
        self.sp_offset_s = QDoubleSpinBox(decimals=1, minimum=-600, maximum=600, singleStep=1, suffix=" s",
                                          value=st["offset_s"])
        self.sp_offset_s.setToolTip(T("sec_offset_tip"))
        f.addRow(T("sec_offset"), self.sp_offset_s)
        row = QHBoxLayout()
        self.sp_shift = QDoubleSpinBox(decimals=3, minimum=-5, maximum=5, singleStep=0.01, suffix=" V",
                                       value=st["e_shift"])
        self.sp_shift.setToolTip(T("sec_shift_tip"))
        self.cb_from_cv = QCheckBox(T("sec_from_cv"))
        self.cb_from_cv.setChecked(st["ref_from_cv"])
        row.addWidget(self.sp_shift)
        row.addWidget(self.cb_from_cv)
        f.addRow(T("sec_shift"), row)
        self.ed_electrode = QLineEdit(st["electrode"])
        f.addRow(T("cv_electrode"), self.ed_electrode)
        self.lv.addWidget(g)

        self.map_group = g = QGroupBox(T("sec_map"))
        f = make_form(g)
        self.cmb_map = QComboBox()
        for key in ("none", "interval", "time", "potential"):
            self.cmb_map.addItem(T("sec_map_" + key), key)
        self.cmb_map.setCurrentIndex(max(0, self.cmb_map.findData(st["map_mode"])))
        f.addRow(T("sec_map_mode"), self.cmb_map)
        self.sp_map_start = QDoubleSpinBox(decimals=1, minimum=-100000, maximum=100000, singleStep=1, suffix=" s",
                                           value=st["map_start"])
        self.sp_map_start.setToolTip(T("sec_map_start_tip"))
        f.addRow(T("sec_map_start"), self.sp_map_start)
        self.sp_map_step = QDoubleSpinBox(decimals=2, minimum=0, maximum=100000, singleStep=1, suffix=" s",
                                          value=st["map_step"])
        self.sp_map_step.setToolTip(T("sec_map_step_tip"))
        f.addRow(T("sec_map_step"), self.sp_map_step)
        self.ed_map = QPlainTextEdit(st["map_table"])
        self.ed_map.setPlaceholderText(T("sec_map_table_ph"))
        self.ed_map.setFixedHeight(84)
        f.addRow(self.ed_map)
        self.cb_map_ok = QCheckBox(T("sec_map_ok"))
        self.cb_map_ok.setToolTip(T("sec_map_ok_tip"))
        self.cb_map_ok.setChecked(st["map_ok"])
        f.addRow(self.cb_map_ok)
        self.lv.addWidget(g)
        self.cmb_map.currentIndexChanged.connect(self._map_mode_changed)
        for w_ in (self.sp_map_start, self.sp_map_step):
            w_.valueChanged.connect(self.changed)
        self.cb_map_ok.toggled.connect(self.changed)
        self.ed_map.textChanged.connect(self.timer.start)

        g = QGroupBox(T("sec_display"))
        f = make_form(g)
        self.cmb_mode = QComboBox()
        for key in ("spectra", "trace"):
            self.cmb_mode.addItem(T("sec_mode_" + key), key)
        self.cmb_mode.setCurrentIndex(max(0, self.cmb_mode.findData(st["mode"])))
        f.addRow(T("sec_mode"), self.cmb_mode)
        row = QHBoxLayout()
        self.sp_first = QSpinBox(minimum=1, maximum=9999, value=st["first"])
        self.sp_last = QSpinBox(minimum=0, maximum=9999, value=st["last"])
        self.sp_last.setSpecialValueText(T("sec_last_all"))
        for w_ in (self.sp_first, QLabel("–"), self.sp_last):
            row.addWidget(w_)
        f.addRow(T("sec_range"), row)
        self.lbl_range = STYLE.HintLabel("")
        self.lbl_range.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_range)
        self.cb_highlight = QCheckBox(T("sec_highlight"))
        self.cb_gradient = QCheckBox(T("sec_gradient"))
        self.cb_diff = QCheckBox(T("sec_diff"))
        self.cb_baseline = QCheckBox(T("sec_baseline"))
        for cb, key in ((self.cb_highlight, "highlight"), (self.cb_gradient, "gradient"), (self.cb_diff, "diff"),
                        (self.cb_baseline, "baseline")):
            cb.setChecked(st[key])
            f.addRow(cb)
            cb.toggled.connect(self.changed)
            if cb is self.cb_highlight:
                self.ed_mid = QLineEdit(st["mid"])
                self.ed_mid.setPlaceholderText(T("sec_mid_ph_e"))
                self.ed_mid.setToolTip(T("sec_mid_tip"))
                f.addRow(T("sec_mid"), self.ed_mid)
        self.ed_bands = QLineEdit(st["bands"])
        self.ed_bands.setPlaceholderText(T("sec_bands_ph"))
        f.addRow(T("sec_bands"), self.ed_bands)
        self.ed_trace = QLineEdit(st["trace_lams"])
        self.ed_trace.setPlaceholderText(T("sec_trace_ph"))
        f.addRow(T("sec_trace"), self.ed_trace)
        self.cb_fit = QCheckBox(T("sec_fit"))
        self.cb_fit.setToolTip(T("sec_fit_tip"))
        self.cb_fit.setChecked(st["fit"])
        self.cb_fit.toggled.connect(self.changed)
        f.addRow(self.cb_fit)
        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f.addRow(self.lbl_info)
        f.addRow(self.methods_button())
        self.lv.addWidget(g)
        self.lv.addWidget(self.caption_box())            # Bildunterschrift für den SI-Export
        for w_ in (self.sp_offset_s, self.sp_shift):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.sp_first, self.sp_last):
            w_.valueChanged.connect(self.changed)
        self.cb_from_cv.toggled.connect(self.changed)
        self.cmb_mode.currentIndexChanged.connect(self.changed)
        for ed in (self.ed_mid, self.ed_bands, self.ed_trace, self.ed_electrode):
            ed.editingFinished.connect(self.changed)
        self._show_files()

    def _set(self, k, v):
        self.st[k] = v
        self._show_files()
        self.timer.start()

    def _show_files(self):
        n = len(self.st["spec_files"])
        merged = self.is_merged_series()
        text = T("sec_n_spectra", n=n) if n else "–"
        self.lbl_spec.setText(f"{text} ({T('sec_q_' + self.st['quantity'])})" if merged else text)
        self.lbl_dta.setText(Path(self.st["dta"]).name if self.st.get("dta") else "–")
        self.map_group.setVisible(merged)
        self.sp_offset_s.setEnabled(not merged)
        self._map_mode_changed()

    def is_merged_series(self):
        files = self.st["spec_files"]
        return bool(files) and Path(files[0]).exists() and is_merged(files[0])

    def _map_mode_changed(self, *_):
        mode = self.cmb_map.currentData()
        for w_, on in ((self.sp_map_start, mode == "interval"), (self.sp_map_step, mode == "interval"),
                       (self.ed_map, mode in ("time", "potential")), (self.cb_map_ok, mode != "none")):
            w_.setVisible(on)
            lab = w_.parentWidget().layout().labelForField(w_)
            if lab:
                lab.setVisible(on)
        if _:
            self.changed()

    def collect(self):
        self.st.update(offset_s=self.sp_offset_s.value(), e_shift=self.sp_shift.value(),
                       ref_from_cv=self.cb_from_cv.isChecked(), electrode=self.ed_electrode.text().strip() or "Ag/AgNO₃",
                       mode=self.cmb_mode.currentData(), first=self.sp_first.value(), last=self.sp_last.value(),
                       highlight=self.cb_highlight.isChecked(), mid=self.ed_mid.text().strip(),
                       gradient=self.cb_gradient.isChecked(),
                       diff=self.cb_diff.isChecked(), baseline=self.cb_baseline.isChecked(),
                       bands=self.ed_bands.text().strip(), trace_lams=self.ed_trace.text().strip(),
                       fit=self.cb_fit.isChecked(), map_mode=self.cmb_map.currentData(),
                       map_start=self.sp_map_start.value(), map_step=self.sp_map_step.value(),
                       map_table=self.ed_map.toPlainText(), map_ok=self.cb_map_ok.isChecked())

    def choose_spectra(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("sec_spectra"), self.main.settings.value("last_dir", ""),
                                             T("sec_flt") + " (*.txt *.TXT);;" + T("flt_all"))
        if ps:
            self.load_spectra(ps)

    def load_spectra(self, ps):
        """Auswahl oder abgelegte Dateien; was nicht gelesen wird, wird immer gemeldet."""
        bw, merged = [p for p in ps if is_bwspec(p)], [p for p in ps if is_merged(p)]
        rest = len(ps) - len(bw) - len(merged)
        if not bw and not merged:
            self.main.error(T("sec_none_read", n=rest))
            return
        if bw and merged:
            self.main.error(T("sec_mixed"))
            return
        quantity = "abs"
        if merged:
            kinds = {merged_quantity(p) for p in merged}
            quantity = kinds.pop() if len(kinds) == 1 and None not in kinds else self._ask_quantity()
            if quantity is None:
                return
            merged = [p for p in merged if merged_quantity(p) in (quantity, None)]   # nie Abs und Raw in einer Serie
        chosen = sorted(bw or merged, key=lambda p: _natural(Path(p).name))
        notes = [T("sec_skipped", n=rest)] if rest else []
        notes += self._file_warnings(chosen) if merged else []
        self.st["spec_files"] = [self.main.import_file(p, PRJ.data_sub(self.STATE_KEY)) for p in chosen]
        self.st.update(quantity=quantity, import_note="\n".join(notes))
        self._show_files()
        self.timer.start()

    def _ask_quantity(self):
        names = [T("sec_q_abs"), T("sec_q_raw")]
        name, ok = QInputDialog.getItem(self, T("sec_spectra"), T("sec_q_ask"), names, 0, False)
        return ("abs", "raw")[names.index(name)] if ok else None

    @staticmethod
    def _file_warnings(paths):
        """Nur Warnungen, keine Zuordnung: Lücken in den Nummern und Dateizeiten, die rückwärts oder weit springen
        (Zähler neu gestartet, zwei Messungen in einem Ordner)."""
        out = []
        nums = [file_number(Path(p).stem) for p in paths]
        if None not in nums and nums[-1] - nums[0] + 1 != len(set(nums)):
            out.append(T("sec_gap", n=nums[-1] - nums[0] + 1 - len(set(nums))))
        times = [Path(p).stat().st_mtime for p in paths]
        for a, b, t0, t1 in zip(paths, paths[1:], times, times[1:]):
            if t1 < t0 or t1 - t0 > 600:
                out.append(T("sec_time_break", a=Path(a).stem, b=Path(b).stem))
        return out

    def choose_dta(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("sec_potential"), self.main.settings.value("last_dir", ""),
                                           "Gamry (*.DTA *.dta);;" + T("flt_all"))
        if p:
            self._set("dta", self.main.import_file(p, PRJ.data_sub(self.STATE_KEY)))

    # -- Daten ---------------------------------------------------------------------
    def series(self):
        """-> (Spektren nach Zeit sortiert, Potentiale in V vs. Referenzelektrode oder None)."""
        st = self.st
        files = [p for p in st["spec_files"] if Path(p).exists()]
        self.gone = len(st["spec_files"]) - len(files)     # verschoben/gelöscht: melden, nicht still weglassen
        sp = [self.cache(("bws", p), lambda p=p: read_spectrum(p)) for p in files]
        sp.sort(key=lambda s: (s["time"] is None, s["time"] or 0, _natural(s["name"])))
        E, self.outside, self.map_notes = None, 0, []
        g = None
        if st.get("dta") and Path(st["dta"]).exists() and sp:
            g = self.cache(("cv", st["dta"]), lambda: CV.read_gamry(st["dta"]))
        if sp and sp[0].get("merged"):
            E, keep, self.map_notes = assign_potentials(sp, g, st)
            if E is not None:                              # ohne Potential nicht zeigen, statt eines falschen Werts
                sp, E = [s for s, k in zip(sp, keep) if k], E[keep]
        elif g is not None:
            E, self.outside = potentials(sp, g, st["offset_s"], with_outside=True)
        return sp, E

    def map_sentence(self):
        """Herkunft der Potentiale einer Serie ohne Zeitstempel (Methodentext, Unterschrift)."""
        st = self.st
        return {"interval": f"The spectra files carry no timestamps; potentials were taken from the potentiostat "
                            f"record using a confirmed acquisition schedule (first spectrum at t = "
                            f"{st['map_start']:g} s, one spectrum every {st['map_step']:g} s).".replace("= -", "= −"),
                "time": "The spectra files carry no timestamps; potentials were taken from the potentiostat record "
                        "using a confirmed table of acquisition times.",
                "potential": "The spectra files carry no timestamps; potentials were assigned from a confirmed table "
                             "of applied potentials."}.get(st["map_mode"], "") if st["map_ok"] else ""

    def e_offset(self):
        """Verschiebung der Potentialachse (E_Achse = E − Offset) und Achsenbeschriftung der Referenz."""
        st = self.st
        if st["ref_from_cv"]:
            off, label, _ = self.main.cv_tab.reference_offset()
            return off, label
        return st["e_shift"], ("Fc$^{0/+}$" if st["e_shift"] else st["electrode"])

    def selection(self, n):
        """Indizes der gezeigten Spektren (Bereich erstes–letztes, 0-basiert)."""
        st = self.st
        i0 = min(max(st["first"], 1), n) - 1
        i1 = n - 1 if not st["last"] else min(max(st["last"], i0 + 1), n) - 1
        return list(range(i0, i1 + 1))

    def mid_indices(self, sel, Eax, with_pos=False):
        """Zwischenspektren aus st["mid"]: Potentiale (Achsenskala) -> gezeigtes Spektrum mit dem nächstliegenden
        Potential (bei gleichem Abstand das erste); ohne Potentiale Nummern der Spektren (wie „Spektren (Nr.)“).
        Erstes/letztes und Doppelte fallen weg, Reihenfolge wie eingegeben. with_pos: [(Index, Position der Eingabe)]
        (Namen in cap_mid gehören zur Eingabe, nicht zur gefilterten Liste)."""
        out, pos = [], []
        for k, x in enumerate(str(self.st.get("mid", "")).replace(";", ",").split(",")):
            v = _floats(x)                                 # leere/ungültige Einträge behalten ihre Position
            if not v:
                continue
            v = v[0]
            if Eax is not None:
                i = sel[int(np.argmin(np.abs(Eax[sel] - v)))]
            else:
                i = int(round(v)) - 1
                if i not in sel:
                    continue
            if i not in (sel[0], sel[-1]) and i not in out:
                out.append(i)
                pos.append(k)
        n = len(MID_COLORS)
        return list(zip(out[:n], pos[:n])) if with_pos else out[:n]

    def figure_spec(self):
        st = self.st
        sp, E = self.series()
        self.fits = []                                     # (λ, Nernst-Fit) für den SI-Text
        self.ref_label = None
        if not sp:
            self.lbl_info.setText("")
            return None
        sel = self.selection(len(sp))
        i0, i1 = sel[0], sel[-1]
        off, ref_label = self.e_offset()
        self.ref_label = ref_label
        Eax = None if E is None else E - off
        self.ed_mid.setPlaceholderText(T("sec_mid_ph_e" if Eax is not None else "sec_mid_ph_n"))
        cfg = self.base_cfg()
        lam0 = sp[sel[0]]["lam"]
        bl_win = (lam0 >= 780) & (lam0 <= 820)              # Nullpunkt: Mittel 780–820 nm

        def on_grid(s):
            y = np.interp(lam0, s["lam"], s["A"])
            return y - float(np.mean(y[bl_win])) if (st["baseline"] and bl_win.any()) else y
        self._bl_applied = bool(st["baseline"] and bl_win.any())   # für den Methodentext
        ref_y = on_grid(sp[sel[0]])

        def ys(s):
            return on_grid(s) - ref_y if st["diff"] else on_grid(s)
        rng = (T("sec_range_info_e", a=CV._fmt_e(Eax[i0]), b=CV._fmt_e(Eax[i1]), n=len(sel))
               if Eax is not None else T("sec_range_info", n=len(sel)))
        self.lbl_range.setText(rng)
        info = []
        if st["mode"] == "trace":
            lams = _floats(st["trace_lams"]) or [float(lam0[np.argmax(np.abs(ys(sp[sel[-1]]) - ys(sp[sel[0]])))])]
            xs = Eax[sel] if Eax is not None else np.arange(1, len(sel) + 1, dtype=float)
            curves, labels = [], []
            for k, lam in enumerate(lams[:6]):
                a = np.array([float(np.interp(lam, lam0, ys(sp[i]))) for i in sel])
                col = TABS.PALETTE[(k + 1) % len(TABS.PALETTE)] if len(lams) > 1 else "#000000"
                curves.append({"x": xs, "y": a, "color": col, "label": f"{lam:g} nm", "ls": "-", "lw": 1.3,
                               "marker": "o"})
                if st["fit"] and Eax is not None and st["quantity"] == "abs" and len(np.unique(np.round(xs, 2))) >= 5:
                    fit = nernst_fit(xs, a)
                    if fit and fit["bound"]:
                        info.append(T("sec_fit_bound", lam=f"{lam:g}"))
                    elif fit:
                        xf = np.linspace(xs.min(), xs.max(), 300)
                        s_ = 1 / (1 + np.exp(-fit["n"] * F_RT * (xf - fit["e12"])))
                        curves.append({"x": xf, "y": fit["a_red"] + (fit["a_ox"] - fit["a_red"]) * s_, "color": col,
                                       "label": None, "ls": "--", "lw": 1.0})
                        info.append(T("sec_fit_info", lam=f"{lam:g}", e12=CV._fmt_e(fit["e12"]), n=f"{fit['n']:.2f}",
                                      r2=f"{fit['r2']:.3f}"))
                        self.info[lam] = fit
                        self.fits.append((lam, fit))
            cfg["xlim"] = [float(xs.min()), float(xs.max())]
            span = float(np.ptp(np.concatenate([c["y"] for c in curves]))) or 1.0
            ymin = float(min(c["y"].min() for c in curves))
            cfg["ylim"] = [ymin - 0.08 * span, st["ymax"] if st["ymax"] > 0 else ymin + 1.15 * span]
            cfg["xlabel"] = f"E [V vs. {CV.axis_ref(ref_label)}]" if Eax is not None else T("sec_index")
            cfg["ylabel"] = (("Δ raw signal" if st["diff"] else "raw signal") if st["quantity"] == "raw"
                             else ("ΔA" if st["diff"] else "A")) + " [a.u.]"
        else:
            curves, labels = [], []
            mids = self.mid_indices(sel, Eax) if st["highlight"] else []
            if mids:
                info.append(T("sec_mid_info", items=", ".join(
                    f"{T('sec_index')} {i + 1}" + (f" ({CV._fmt_e(Eax[i], 2)} V)" if Eax is not None else "")
                    for i in mids)))
            # hervorgehoben: (Index, Farbe) – Start, Zwischenstufen, Ende
            marked = [(sel[0], START_COLOR)] + [(i, MID_COLORS[k][0]) for k, i in enumerate(mids)] + \
                [(sel[-1], END_COLOR)]
            mcol = dict(marked)
            for j, i in enumerate(sel):
                hi = i in mcol
                if st["gradient"]:
                    col = _hex(POT_CMAP(j / max(1, len(sel) - 1)))
                    lw = 1.6 if (st["highlight"] and hi) else 0.8
                elif st["highlight"] and hi:
                    col, lw = mcol[i], 1.6
                else:
                    col, lw = "#b0b0b0", 0.5
                lab = None
                if hi and Eax is not None:
                    lab = CV._fmt_e(Eax[i], 2) + " V"
                curves.append({"x": lam0, "y": ys(sp[i]), "color": col, "label": lab, "ls": "-", "lw": lw,
                               "z": 3 if hi else 2})
            # Hervorgehobene Spektren zuletzt zeichnen (oben)
            curves.sort(key=lambda c: c.get("z", 2))
            ys_marked = [(ys(sp[i]), c) for i, c in marked]
            for lam in _floats(st["bands"]):
                # Farbe der hervorgehobenen Kurve mit der größten |A| an dieser Wellenlänge
                col = max(ys_marked, key=lambda yc: abs(float(np.interp(lam, lam0, yc[0]))))[1]
                labels.append({"key": f"label_sec_{lam:g}", "lam": lam, "text": f"λ =  {lam:g} nm", "color": col})
            lim = (lam0.min(), lam0.max()) if sp[0].get("merged") else LAM_RANGE   # NIR nicht abschneiden
            x0, x1 = (st["x_min"], st["x_max"]) if not st["x_auto"] else (max(lim[0], lam0.min()),
                                                                          min(lim[1], lam0.max()))
            cfg["xlim"] = [x0, x1]
            win = (lam0 >= x0) & (lam0 <= x1)
            vals = np.concatenate([c["y"][win] for c in curves])
            span = float(np.ptp(vals)) or 1.0
            ymin = min(0.0, float(vals.min()))
            cfg["ylim"] = [ymin - 0.03 * span, st["ymax"] if st["ymax"] > 0 else float(vals.max()) + 0.1 * span]
            cfg["xlabel"] = "wavelength [nm]"
            cfg["ylabel"] = (("Δ raw signal" if st["diff"] else "raw signal") if st["quantity"] == "raw"
                             else ("ΔA" if st["diff"] else "absorbance")) + " [a.u.]"
        if self.gone:
            info.append(T("sec_gone", n=self.gone))
        if sp[0].get("merged"):
            info += ([st["import_note"]] if st["import_note"] else []) + self.map_notes
            if E is None:
                info.append(T("sec_no_map"))
        elif E is None and st.get("dta"):
            info.append(T("sec_no_time"))
        elif E is not None and self.outside:              # > 30 s außerhalb (Ruhepotential davor ist normal)
            info.append(T("sec_outside", n=self.outside))
        self.lbl_info.setText("\n".join(info))
        return cfg, curves, labels, []

    def si_caption(self, name):
        """Wie in der SI: „UV-vis-SEC of <b>3b</b> in THF. Color coding: <b>neutral</b> (blue), <b>dication</b> (red).
        Starting potential (vs. Ag/AgNO3): −1.30 V; End potential (vs. Ag/AgNO3): 0.70 V.“ Potentiale aus dem Scan
        (erstes/letztes gezeigtes Spektrum), Namen der Spezies und Lösungsmittel aus den Feldern."""
        import html
        from elucida.si.lines import chem_html
        st = self.st
        sp, E = [], None
        try:
            sp, E = self.series()
        except Exception as ex:                            # Unterschrift ohne Potentiale, aber nicht unbemerkt
            self.main.log_signal.emit(f"SEC: {ex}")
        method = "UV-vis-NIR-SEC" if sp and sp[0]["lam"].max() > 1100 else "UV-vis-SEC"
        title = method if st["mode"] != "trace" else f"Absorbance at selected wavelengths during {method}"
        if st["quantity"] == "raw":
            title = f"Raw detector signal during {method}"
        h = f"{title} of <b>{html.escape(name)}</b>"
        if st.get("cap_solvent"):
            h += " in " + chem_html(st["cap_solvent"])
        h += "."
        sel = self.selection(len(sp)) if sp else []
        off, lab = self.e_offset()
        if st["mode"] != "trace" and st["highlight"] and not st["gradient"]:
            # nur Farben, die im Bild vorkommen: Zwischenspektren nur, wenn sie hervorgehoben sind
            mids = self.mid_indices(sel, None if E is None else E - off, with_pos=True) if sel else []
            names = [x.strip() for x in st.get("cap_mid", "").split(";")]
            # ein einziges Spektrum ist zugleich Ende (rot) – Blau kommt dann nicht vor
            items = [(st.get("cap_start", ""), "blue")] if len(sel) > 1 else []
            items += [(names[p] if p < len(names) else "", MID_COLORS[k][1]) for k, (_, p) in enumerate(mids)]
            items.append((st.get("cap_end", ""), "red"))
            cols = [f"<b>{chem_html(t)}</b> ({c})" for t, c in items if t]
            if cols:
                h += " Color coding: " + ", ".join(cols) + "."
        if sp and E is not None:
            i0, i1 = sel[0], sel[-1]
            ref = ("Fc<sup>0/+</sup>" if str(lab) == "Fc$^{0/+}$" else chem_html(str(lab)))   # wie die Achse
            fe = lambda v: f"{v:.2f}".replace("-", "−")                               # noqa: E731
            h += (f" Starting potential (vs. {ref}): {fe(E[i0] - off)} V; End potential (vs. {ref}): "
                  f"{fe(E[i1] - off)} V.")
            if sp[0].get("merged"):
                h += " " + self.map_sentence()
        return h

    def methods_text(self):
        """SI-Text zum scheinbaren Nernst-Fit (nur wenn gefittet). Ausdrücklich „apparent“: Im kontinuierlichen
        Scan hinkt die Dünnschichtzelle nach, E½ und n weichen vom CV ab; CV-Werte haben Vorrang."""
        fits = getattr(self, "fits", [])
        st = self.st
        source = self.map_sentence() if self.is_merged_series() else ""
        if not fits:
            return source
        ref = str(self.ref_label or st["electrode"]).replace("Fc$^{0/+}$", "Fc0/+")
        m = [source or "Each spectrum was assigned the potential at its acquisition time, interpolated from the "
             "time-resolved potentiostat record" + (f" (time offset {st['offset_s']:g} s)" if st["offset_s"] else "") + ".",
             ("Each spectrum was corrected by subtracting its mean absorbance between 780 and 820 nm. "
              if getattr(self, "_bl_applied", False) else "")
             + ("Difference spectra were obtained by subtracting the first spectrum shown. "
                if st["diff"] else "")
             + "Absorbance–potential traces at the indicated wavelengths were fitted with a Nernst-type sigmoid, "
             "A(E) = A_red + (A_ox − A_red)/[1 + exp(−nF(E − E1/2)/RT)] (T = 298.15 K); E1/2 and n were obtained by a "
             "grid search (E1/2 in 2 mV steps, n = 0.30–3.00 in steps of 0.05) with A_red and A_ox determined by "
             "linear least squares at each grid point.",
             "As the potential was swept continuously in a thin-layer cell, the electrolysis lags behind the "
             "applied potential; E1/2 and n are therefore apparent values (E1/2,app, n_app), and the half-wave "
             "potentials from cyclic voltammetry are considered more reliable."]
        res = [f"λ = {lam:g} nm: E1/2,app = {CV._fmt_e(f['e12'], 3)} V vs. {ref}, n_app = {f['n']:.2f}, "
               f"R² = {f['r2']:.3f}" for lam, f in fits]
        return " ".join(m) + "\n\n" + "; ".join(res) + "."

    def hover_text(self, x, val, name):
        if self.st["mode"] == "trace":
            return f"E = {x:.3f} V    A = {val:.4f}    {name}" if val is not None else f"E = {x:.3f} V"
        return super().hover_text(x, val, name)
