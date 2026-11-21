"""HRMS: Bericht der Massenabteilung (docx) und Bruker-Rohdaten (.d) – Chromatogramm mit wählbarem LC-Bereich,
gemitteltes Spektrum (Linienspektren des Geräts), Peak per Klick als found, berechnetes Isotopenmuster aus der
Summenformel (gespiegelt), SI-Zeile. Leser und Ionenmassen stehen in tabs/ir_ea.py."""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
from elucida.app.canvas_theme import register as register_canvas
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from matplotlib.widgets import SpanSelector
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QSizePolicy, QTableWidget,
                               QTableWidgetItem, QTextBrowser, QWidget)

from elucida.tabs import base as TABS
from elucida.core import uvvis as core
from elucida.app.i18n import T, T_en
from elucida.core import tables as TBL
from elucida.app import project as PRJ
from elucida.tabs.ir_ea import (ADDUCTS, ELECTRON, copy_rich, ion, is_bruker_d, lc_found, ms_line, nearest, parse_formula,
                        ppm, read_bruker_d)
from elucida.app.style import HINT_CSS, WARN_CSS, HintLabel, make_form
from elucida.formats.bruker_ms import spectra_of
from elucida.formats.ms_report import pdf_image_array, pdf_image_png, read_ms_report
from elucida.tabs.ir_ea import mono_mass
from elucida.si.lines import chem_plain

MEASURED_COLOR, CALC_COLOR = "#111111", "#c0392b"
IMG_CAPTION = " (image from the instrument report)"     # SI-Unterschrift, wenn das Bild aus dem PDF-Bericht stammt
CAND_WINDOW_DA = 2.0          # unbekannte PDFs: Kandidaten nur bis ± 2 Da um calc. (Isotope M+1/M+2 bleiben sichtbar)


# ---------------------------------------------------------------------------- Isotopenmuster
def _isotopes(el):
    """[(Masse, Anteil)] eines Elements aus der Isotopentabelle von RDKit (D = reines ²H)."""
    if el == "D":
        return [(2.0141017781, 1.0)]
    if el.startswith("["):                            # Isotop wie RDKit: [13C]
        return [(mono_mass(el), 1.0)]
    from rdkit import Chem
    pt = Chem.GetPeriodicTable()
    z = pt.GetAtomicNumber(el)
    a0 = pt.GetMostCommonIsotope(z)
    out = []
    for a in range(max(1, a0 - 12), a0 + 13):
        ab = pt.GetAbundanceForIsotope(z, a)
        if ab > 0:
            out.append((pt.GetMassForIsotope(z, a), ab))
    if not out:
        raise ValueError(f"Element {el} ohne natürliche Isotope")
    tot = sum(p for _, p in out) or 1.0
    return [(m, p / tot) for m, p in out]


def isotope_pattern(formula, z=1, resolution=20000, min_rel=0.05):
    """Ion (Formel ohne Ladung, z = Ladung) -> [(m/z, rel. Intensität in % vom höchsten Peak)]. Feinstruktur, die bei
    der Auflösung (m/Δm) nicht getrennt wird (z. B. ¹³C/¹⁵N), wird zusammengefasst (gewichtetes Mittel);
    Elektronenmasse berücksichtigt."""
    counts = parse_formula(formula) if isinstance(formula, str) else dict(formula)
    dist = {0.0: 1.0}
    for el, n in counts.items():
        iso = _isotopes(el)
        for _ in range(int(round(n))):
            new = {}
            for m, p in dist.items():
                for mi, pi in iso:
                    k = round(m + mi, 7)
                    new[k] = new.get(k, 0.0) + p * pi
            mx = max(new.values())
            dist = {m: p for m, p in new.items() if p >= mx * 1e-7}
    pts = sorted(dist.items())
    out = []
    for m, p in pts:                                   # benachbarte (Feinstruktur) zusammenfassen
        if out and m - out[-1][0] <= m / resolution:
            m0, p0 = out[-1]
            out[-1] = ((m0 * p0 + m * p) / (p0 + p), p0 + p)
        else:
            out.append((m, p))
    mx = max(p for _, p in out)
    zz = abs(int(z)) or 1
    return [((m - z * ELECTRON) / zz, 100 * p / mx) for m, p in out if 100 * p / mx >= min_rel]


def averaged_spectrum(spectra, rt_lo, rt_hi, lo, hi, tol_ppm=5.0):
    """Linienspektren im RT-Bereich [s] gemittelt: Linien aller Scans innerhalb tol_ppm zusammengefasst
    (m/z intensitätsgewichtet, Intensität gemittelt über die Scans). -> (mz, int, n_scans)."""
    mzs, ins, n = [], [], 0
    for t, mz, inten in spectra:
        if rt_lo <= t <= rt_hi:
            n += 1
            sel = (mz >= lo) & (mz <= hi)
            mzs.append(mz[sel])
            ins.append(inten[sel])
    if not n or not sum(len(m) for m in mzs):
        return np.zeros(0), np.zeros(0), n
    mz = np.concatenate(mzs)
    it = np.concatenate(ins)
    o = np.argsort(mz)
    mz, it = mz[o], it[o]
    brk = np.where(np.diff(mz) > tol_ppm * 1e-6 * mz[1:])[0] + 1
    groups = np.split(np.arange(len(mz)), brk)
    out_m = np.array([np.average(mz[g], weights=np.maximum(it[g], 1e-12)) for g in groups])
    out_i = np.array([it[g].sum() / n for g in groups])
    return out_m, out_i, n


def chromatogram(spectra):
    """Gesamt-Ionenstrom je Scan -> (t [min], TIC)."""
    t = np.array([s[0] for s in spectra]) / 60.0
    tic = np.array([float(np.sum(s[2])) for s in spectra])
    return t, tic


# ---------------------------------------------------------------------------- Tab
def dev_text(dev):
    """Abweichung found − calc in ppm, eine Stelle, echtes Minus, nie „−0.0“."""
    return core.fmt_num(dev, 1, sign=True)


def same_formula(a, b):
    """Gleiche Summenformel (Reihenfolge und Ladungszeichen egal); nicht lesbar -> False."""
    try:
        return parse_formula(a) == parse_formula(b)
    except ValueError:
        return False


class WrapHint(HintLabel):
    """Mehrzeiliger Hinweis unter einer Tabelle: mindestens so hoch wie sein umbrochener Text (heightForWidth). Das
    Formular gab ihm sonst bei Skalierung 1.25 zu wenig Höhe (oben unter der Tabelle, unten abgeschnitten); so rollt
    stattdessen die linke Spalte."""

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        h = self.heightForWidth(self.width())
        if h > 0 and h != self.minimumHeight():
            self.setMinimumHeight(h)

    def setText(self, text):
        super().setText(text)
        if self.width() > 0:
            h = self.heightForWidth(self.width())
            if h > 0:
                self.setMinimumHeight(h)


class FileLabel(QLabel):
    """Dateiname in einer Zeile, am Ende gekürzt (ganz im Tooltip), die Art in Klammern bleibt stehen: bricht nie um und
    macht die Spalte nie breiter, auch nicht mit langen Namen."""

    def __init__(self, tip):
        super().__init__("–")
        self._full, self._tag, self._tip = "–", "", tip
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.setToolTip(tip)

    def set_full(self, text, tag=""):
        self._full, self._tag = text, (f"  ({tag})" if tag else "")
        self.setToolTip(text + self._tag + "\n" + self._tip if text != "–" else self._tip)
        self._elide()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._elide()

    def _elide(self):
        fm = self.fontMetrics()
        room = max(10, self.contentsRect().width() - 2 * max(0, self.margin()) - max(0, self.indent())
                   - fm.horizontalAdvance(self._tag) - 2)              # Innenabstand des Stylesheets: Klammer nie abgeschnitten
        QLabel.setText(self, fm.elidedText(self._full, Qt.ElideRight, room) + self._tag)


def dev_ok(dev):
    """≤ 5 ppm an der gedruckten Zahl geprüft (wie die EA): „+5.0“ ist immer gleich bewertet."""
    return abs(float(f"{dev:.1f}")) <= 5


class HRMSTab(TABS.FigureTab):
    LABEL_CARD = True                    # Karte „Beschriftungen im Bild“
    COLOR_ROLES = (("col_meas", MEASURED_COLOR, "tf_col_meas"), ("col_calc", CALC_COLOR, "tf_col_calc"))   # Stilkarte
    STATE_KEY = "hrms"
    GUIDE, GUIDE_ACTION = "hrms", ("guide_add", "choose_ms")
    MAIN_SI = True                                       # Ergebnis ist die HR-MS-Zeile der SI (Nutzerwunsch)
    SI_CAPTION = "HR-MS spectrum of {name}."
    X_RANGE = (10.0, 5000.0, 2, 0.5)
    XRANGE_TEXT = "ms_xrange"
    RESET_KEEP = ("ms_file", "ms_raw", "ms_rt", "adduct", "found", "found_pick", "found_pdf", "found_manual", "ms_img",
                  "mz_labels")                                 # welche m/z im Bild stehen
    # found: None | m/z aus dem Bericht | "raw" | "pick" (found_pick) | "pdf" (found_pdf: per Klick aus der Kandidatenliste
    # eines unbekannten PDF) | "manual" (found_manual: von Hand); ms_img: Nummer des Bildes aus dem PDF-Bericht (0 = keins)
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=100.0, x_max=1000.0, ymax=0.0, ms_file=None, ms_raw=None,
                         ms_rt=None, adduct="M+H", found=None, found_pick=None, found_pdf=None, found_manual=None,
                         ms_img=0, show_calc=True, mz_labels=True)

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("ms_group"))
        f = make_form(g)
        self._form = f
        row = QHBoxLayout()
        self.lbl_ms = FileLabel(T("ms_file_tip"))
        b = QPushButton(T("choose"))
        b.setToolTip(T("ms_file_tip"))
        b.clicked.connect(self.choose_ms)
        row.addWidget(self.lbl_ms, 1)
        row.addWidget(b)
        f.addRow(T("ms_file"), row)
        self.cmb_img = QComboBox()                           # eingebettete Bilder des PDF-Berichts (nie ganze Seiten)
        self.cmb_img.setToolTip(T("ms_img_tip"))
        f.addRow(T("ms_img"), self.cmb_img)
        row = QHBoxLayout()
        self.lbl_raw = FileLabel(T("ms_raw_tip"))
        b = QPushButton(T("choose"))
        b.setToolTip(T("ms_raw_tip"))
        b.clicked.connect(self.choose_raw)
        b2 = QPushButton(T("remove"))
        b2.clicked.connect(self.clear_raw)
        row.addWidget(self.lbl_raw, 1)
        row.addWidget(b)
        row.addWidget(b2)
        f.addRow(T("ms_raw"), row)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.cb_rt_auto = QCheckBox(T("ms_rt_auto"))
        self.cb_rt_auto.setToolTip(T("ms_rt_auto_tip"))
        self.sp_rt_lo = QDoubleSpinBox(decimals=2, minimum=0, maximum=999, singleStep=0.05, suffix=" min")
        self.sp_rt_hi = QDoubleSpinBox(decimals=2, minimum=0, maximum=999, singleStep=0.05, suffix=" min")
        for w_ in (self.cb_rt_auto, self.sp_rt_lo, QLabel("–"), self.sp_rt_hi):
            row.addWidget(w_)
        self.rt_row = row                                    # als Layout: tidy setzt das Paar ins Raster (Feld A – Feld B)
        f.addRow(T("ms_rt"), self.rt_row)
        # Chromatogramm (Werkzeug, nicht Teil der Abbildung): Ziehen setzt den LC-Bereich
        self.cfig = MplFigure(figsize=(4.2, 1.5), dpi=100)
        self.ccanvas = register_canvas(FigureCanvasQTAgg(self.cfig))
        self.ccanvas.setMinimumHeight(140)
        self.ccanvas.setMaximumHeight(170)
        self.ccanvas.setToolTip(T("ms_chrom_tip"))
        self.cax = self.cfig.add_axes([0.1, 0.27, 0.87, 0.68])
        self._span = None
        f.addRow(T("ms_chrom"), self.ccanvas)
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
        # unbekanntes PDF: Zahlen mit Textzeile und ppm gegen calc.; übernommen wird nur ein angeklickter Wert
        self.tbl_cand = QTableWidget(0, 3)
        self.tbl_cand.setHorizontalHeaderLabels([T("ms_cand_mz"), T("ms_cand_ppm"), T("ms_cand_line")])
        self.tbl_cand.verticalHeader().setVisible(False)
        self.tbl_cand.verticalHeader().setDefaultSectionSize(TABS.STYLE.CHECK_ROW_H)   # wie fit_check_table rechnet
        self.tbl_cand.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_cand.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_cand.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_cand.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_cand.setToolTip(T("ms_cand_tip"))
        self.tbl_cand.cellClicked.connect(self.candidate_clicked)
        self.cand_head = TABS.STYLE.text_head(T("ms_cand_head"))
        f.addRow(self.cand_head)
        f.addRow(self.tbl_cand)
        self.cmb_found = QComboBox()
        self.cmb_found.setToolTip(T("ms_found_tip"))
        self.cmb_found.setPlaceholderText(T("ms_found_none"))       # nichts gewählt (unbekanntes PDF vor dem Klick)
        f.addRow(T("ms_found"), self.cmb_found)
        self.sp_manual = QDoubleSpinBox(decimals=4, minimum=0.0, maximum=9999.9999, singleStep=0.0001)
        self.sp_manual.setSpecialValueText(T("ms_manual_none"))    # 0 = kein Wert (Rücksetz-Symbol über tidy)
        self.sp_manual.setToolTip(T("ms_manual_tip"))
        self.sp_manual.editingFinished.connect(self.manual_edited)
        f.addRow(T("ms_manual"), self.sp_manual)
        # Prüfung found − calc gegen 5 ppm (Angew.) als kleine Tabelle, Abweichung in der Warnfarbe
        self.tbl_ms = TABS.STYLE.summary_grid([T("ea_chk_ms_ion"), T("ea_calc"), T("ea_chk_f1"), T("ea_chk_ms_dev"),
                                               T("ea_chk_ms_status")])
        self.tbl_ms.setToolTip(T("ea_chk_ms_tip"))
        TABS.STYLE.name_table(self.tbl_ms, "check", "HRMS check", csv=True)
        self._ms_head = TABS.STYLE.table_head(T("tbl_head_check"), self.tbl_ms)
        f.addRow(self._ms_head)
        f.addRow(self.tbl_ms)
        self.lbl_ms_info = WrapHint("")
        self.lbl_ms_info.setWordWrap(True)
        self.lbl_ms_info.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_ms_info)
        self.lbl_ms_warn = WrapHint("")                  # Warnungen in eigener Zeile, nur sie in der Warnfarbe
        self.lbl_ms_warn.setWordWrap(True)
        self.lbl_ms_warn.setStyleSheet(WARN_CSS)
        f.addRow(self.lbl_ms_warn)
        b = TABS.STYLE.copy_button(T("ms_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ms_line))
        f.addRow(TABS.STYLE.text_head(T("line_ms"), b))    # „Kopieren“ direkt an der Zeile, die es kopiert
        self.txt_ms = QTextBrowser()
        self.txt_ms.setMaximumHeight(70)
        f.addRow(self.txt_ms)
        self.lv.addWidget(g)

        g = QGroupBox(T("ms_display"))
        f = make_form(g)
        self.cb_calc = QCheckBox(T("ms_show_calc"))
        self.cb_calc.setChecked(st.get("show_calc", True))
        self.cb_mzlab = QCheckBox(T("ms_mz_labels"))
        self.cb_mzlab.setChecked(st.get("mz_labels", True))
        f.addRow(self.cb_calc)
        f.addRow(self.cb_mzlab)
        self.lv.addWidget(g)
        hint = QLabel(T("ms_pick_hint"), alignment=Qt.AlignHCenter)   # Fußnote unter den Karten (wie der Maus-Hinweis),
        hint.setWordWrap(True)                                        # nicht unter den Chips
        hint.setStyleSheet(HINT_CSS)
        self.lv.addWidget(hint)

        self._ms_line = ("", "")
        self._ms_vals = None                          # (Addukt, calc, found) der letzten SI-Zeile (Austauschdatei)
        self._ion = self._lc = self._found = None
        self._sticks = (np.zeros(0), np.zeros(0))
        self._pick_cid = None
        self._cands = []
        self.cb_rt_auto.toggled.connect(self.changed)
        for w_ in (self.sp_rt_lo, self.sp_rt_hi):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_calc, self.cb_mzlab):
            w_.toggled.connect(self.changed)
        self.cmb_adduct.currentIndexChanged.connect(self.adduct_changed)
        self.cmb_found.currentIndexChanged.connect(self.changed)
        self.cmb_img.currentIndexChanged.connect(self.changed)
        self.sync_widgets()

    def compound_changed(self):
        self.sync_widgets()
        self.timer.start()

    def sync_widgets(self):
        st = self.st
        self._loading = True
        rep = self.ms_report()
        tag = (T("ms_pdf_kind_" + rep["kind"]) if rep.get("kind") else rep.get("sample")) if rep else ""
        self.lbl_ms.set_full(Path(st["ms_file"]).name if st.get("ms_file") else "–", tag if st.get("ms_file") else "")
        imgs = (rep or {}).get("images") or []
        self.cmb_img.blockSignals(True)
        self.cmb_img.clear()
        self.cmb_img.addItem(T("ms_img_none"), 0)
        for k, im in enumerate(imgs, 1):
            self.cmb_img.addItem(T("ms_img_item", k=k, page=im["page"], w=im["w"], h=im["h"]), k)
        self.cmb_img.setCurrentIndex(max(0, self.cmb_img.findData(int(st.get("ms_img") or 0))))
        self.cmb_img.blockSignals(False)
        self._form.setRowVisible(self.cmb_img, bool(imgs))
        self.sp_manual.blockSignals(True)
        self.sp_manual.setValue(float(st.get("found_manual") or 0.0))
        self.sp_manual.blockSignals(False)
        raw = self.ms_raw()
        self.lbl_raw.set_full((Path(st["ms_raw"]).name + (f"  ({raw['instrument']})" if raw and raw.get("instrument")
                                                           else "")) if st.get("ms_raw") else "–")
        self._form.setRowVisible(self.rt_row, raw is not None)     # LC-Bereich nur mit .d (wie das Chromatogramm)
        self._form.setRowVisible(self.ccanvas, raw is not None)     # mit Beschriftung, sonst bleibt sie allein
        rt = st.get("ms_rt")
        self.cb_rt_auto.setChecked(not rt)
        if rt:
            self.sp_rt_lo.setValue(rt[0])
            self.sp_rt_hi.setValue(rt[1])
        self.sp_rt_lo.setEnabled(bool(rt))
        self.sp_rt_hi.setEnabled(bool(rt))
        self.cb_calc.setChecked(st.get("show_calc", True))
        self.cb_mzlab.setChecked(st.get("mz_labels", True))
        self._loading = False

    def collect(self):
        st = self.st
        if self.cb_rt_auto.isChecked() or self.ms_raw() is None:
            st["ms_rt"] = None
        else:                                        # beim Umschalten steht in den Feldern der automatische Bereich
            prev = st.get("ms_rt") or ([self._lc["rt_lo"] / 60, self._lc["rt_hi"] / 60] if self._lc else None)
            vals = [self.sp_rt_lo.value(), self.sp_rt_hi.value()]
            if prev:                                 # Felder runden auf 0.01 min: nur das bearbeitete Feld übernehmen
                src = self.sender()
                vals = [v if src is sp else p for p, v, sp in zip(sorted(prev), vals, (self.sp_rt_lo, self.sp_rt_hi))]
            st["ms_rt"] = sorted(vals)
        st.update(adduct=self.cmb_adduct.currentData(), found=self.cmb_found.currentData(),
                  ms_img=int(self.cmb_img.currentData() or 0) if self.cmb_img.count() else int(st.get("ms_img") or 0),
                  show_calc=self.cb_calc.isChecked(), mz_labels=self.cb_mzlab.isChecked())
        self.sync_widgets()

    def choose_ms(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("ms_file"), self.main.settings.value("last_dir", ""),
                                           f"{T('ms_file')} (*.docx *.pdf);;Word (*.docx);;PDF (*.pdf);;{T('flt_all')}")
        if p:
            self.load_ms(p)

    def load_ms(self, p):
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        try:
            read_ms_report(p)
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ms_file=p, found=None, found_pdf=None, ms_img=0)    # neuer Bericht: Auswahl daraus neu
        self.sync_widgets()
        self.timer.start()

    def choose_raw(self):
        if not self.main.ensure_project():
            return
        p = QFileDialog.getExistingDirectory(self, T("ms_raw"), self.main.settings.value("last_dir", ""))
        if p:
            self.load_raw(p)

    def load_raw(self, p):
        """Bruker-Messordner (.d); ins Projekt kommen nur analysis.baf und analysis.sqlite."""
        if not is_bruker_d(p):
            self.main.error(f"{Path(p).name}: {T('ms_raw_bad')}")
            return
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        try:
            self.cache(("brukerd", p), lambda: read_bruker_d(p))
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ms_raw=p, ms_rt=None, found=None, found_pick=None)
        self.sync_widgets()
        self.timer.start()

    def clear_raw(self):
        self.st.update(ms_raw=None, ms_rt=None, found_pick=None,          # angeklickter Peak gehörte zu den Rohdaten
                       found=None if self.st.get("found") in ("raw", "pick") else self.st.get("found"))
        self.sync_widgets()
        self.timer.start()

    def ms_report(self):
        p = self.st.get("ms_file")
        if not p or not Path(p).exists():
            return None
        try:
            return self.cache(("msreport", p), lambda: read_ms_report(p))
        except Exception as ex:                # gespeicherter Bericht, den der Leser ablehnt: Tab bleibt bedienbar
            self.main.skip_part(ex, p)
            self._ms_error = str(ex)
            return None

    def ms_raw(self):
        p = self.st.get("ms_raw")
        if not p or not is_bruker_d(p):
            return None
        try:
            return self.cache(("brukerd", p), lambda: read_bruker_d(p))
        except Exception:
            return None

    def raw_spectra(self, raw):
        """Scans in der Polarität des gewählten Addukts (Messungen mit Polaritätswechsel nie mischen)."""
        return spectra_of(raw, "+" if ADDUCTS[self.st["adduct"]][2] > 0 else "-")

    def raw_found(self, calc):
        """Mittel über den LC-Peak (automatisch oder gewählter RT-Bereich in min) oder None."""
        raw = self.ms_raw()
        if raw is None:
            return None
        rt = self.st.get("ms_rt")
        spectra = self.raw_spectra(raw)
        if not spectra:
            return None
        return lc_found(spectra, calc, rt=[60 * rt[0], 60 * rt[1]] if rt else None)

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
        new = {"name": c.get("name") or name, "formula": rep["structure"]["formula"],
               "mw": round(rep["structure"]["mw"], 2)}
        if rep["structure"].get("cdxml"):                 # ohne CDXML-Schreiber (ältere RDKit): nur Formel/Molmasse
            dst = Path(self.main.project_dir) / PRJ.STRUCTURES / f"{safe}_aus_MS-Bericht.cdxml"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(rep["structure"]["cdxml"], encoding="utf-8")
            new["structure"] = str(dst)
        elif c.get("structure"):
            new["structure"] = c["structure"]
        self.main.set_compound(new)

    def adduct_changed(self, *_):
        if not self._loading:
            self.st["found"] = None                  # neu zuordnen
            self.cmb_found.blockSignals(True)        # sonst übernimmt collect die alte Auswahl wieder
            self.cmb_found.clear()
            self.cmb_found.blockSignals(False)
        self.changed()

    def update_ms(self):
        self._update_ms()
        QTimer.singleShot(0, self._form, self._form.invalidate)

    def _update_ms(self):
        """Hinweise, Kandidaten- und Prüftabelle ändern Text, Höhe und Sichtbarkeit; danach (update_ms) das Formular nach
        der Ereignisschleife neu aufteilen: QFormLayout mit umbrechenden Zeilen behielt sonst die alte Aufteilung und die
        Kandidatentabelle ragte über die Zeile „found“ (gemessen: sofort invalidiert half nicht)."""
        st = self.st
        self._ion, self._lc, self._found = None, None, None
        self._ms_error = None
        rep = self.ms_report()
        formula, src = self.formula()
        notes = [self._ms_error] if self._ms_error else []      # Bericht nicht lesbar: Grund mit Dateinamen
        self._ms_line = ("", "")
        self._ms_vals = None
        TABS.STYLE.fill_summary(self.tbl_ms, [])
        self._form.setRowVisible(self._ms_head, False)        # Kopf „Prüfung“ nur mit Tabelle
        self.fill_candidates(rep, None)
        self.cmb_found.blockSignals(True)
        self.cmb_found.clear()
        if not formula:
            self.lbl_formula.setText(T("ms_no_formula"))
            self.txt_ms.setHtml("")
            self.cmb_found.blockSignals(False)
            self.lbl_ms_info.setText("")
            if rep and rep.get("kind") == "text":
                notes.append(T("ms_cand_need_formula"))
            self.lbl_ms_warn.setText("\n".join(notes))
            return
        self.lbl_formula.setText(f"{chem_plain(formula)}  ({T('ms_src_' + src)})")
        try:
            _, z, calc, _ = ion(formula, st["adduct"])
        except ValueError as e:
            self.lbl_ms_info.setText("")
            self.lbl_ms_warn.setText(str(e))
            self.cmb_found.blockSignals(False)
            return
        found = None
        self._ion = (formula, z, calc)
        self.btn_take.setVisible(bool(rep and rep.get("structure")))
        raw = self.ms_raw()
        lc = self.raw_found(calc) if raw else None
        self._lc = lc
        rep_found = None
        info = []                                    # Hinweise ohne Warnung
        kind = (rep or {}).get("kind", "docx")
        f_ion = ion(formula, st["adduct"])[0]
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
            ion_of = {r["meas"]: r["formula"] for r in rep.get("rows") or []}      # SmartFormula: Ionenformel je Zeile
            for v in rep["mz"]:
                if v in ion_of and not same_formula(ion_of[v], f_ion):     # Zeile eines anderen Ions: kein ppm
                    self.cmb_found.addItem(f"{v:.4f}  ({chem_plain(ion_of[v].rstrip('+-'))})", v)
                    continue
                tail = f", {chem_plain(ion_of[v].rstrip('+-'))}" if v in ion_of else ""
                self.cmb_found.addItem(f"{v:.4f}  ({dev_text(ppm(v, calc))} ppm{tail})", v)
            if kind == "smartformula":               # Zeile mit der Ionenformel des gewählten Ions, sonst die nächste
                rep_found = next((r["meas"] for r in rep["rows"] if same_formula(r["formula"], f_ion)), None)
                if rep_found is None:
                    rep_found = nearest(rep["mz"], calc)
                    if rep_found is not None:
                        notes.append(T("ms_sf_ion_differs", rep=chem_plain(ion_of[rep_found].rstrip("+-")),
                                       own=chem_plain(f_ion)))
            elif kind == "docx":
                rep_found = nearest(rep["mz"], calc)
            if kind == "text":
                self.fill_candidates(rep, calc)
                if not self._cands:
                    notes.append(T("ms_cand_none", d=f"{CAND_WINDOW_DA:g}"))
            elif rep_found is None:
                notes.append(T("ms_no_match"))
            pol = "+" if z > 0 else "-"
            if rep.get("polarity") and rep["polarity"] != pol:
                notes.append(T("ms_polarity", rep=rep["polarity"]))
        if raw:
            if raw["polarity"] not in ("+" if z > 0 else "-", "±"):
                notes.append(T("ms_polarity_raw", rep=raw["polarity"]))
            if lc is None:
                notes.append(T("ms_raw_none"))
            else:
                self.cmb_found.addItem(T("ms_raw_entry", mz=f"{lc['mz']:.4f}", n=lc["n"],
                                         ppm=dev_text(ppm(lc["mz"], calc))), "raw")
                sd_ppm = lc["std_mda"] / 1000 / calc * 1e6
                info.append(T("ms_raw_info", n=lc["n"], rt0=f"{lc['rt_lo'] / 60:.2f}", rt1=f"{lc['rt_hi'] / 60:.2f}",
                              lo=f"{lc['lo']:.4f}", hi=f"{lc['hi']:.4f}", sd=f"{lc['std_mda']:.2f}",
                              sdp=f"{sd_ppm:.1f}"))
                if lc["n"] < 3:
                    notes.append(T("ms_raw_few", n=lc["n"]))
                if rep_found is not None and abs(lc["mz"] - rep_found) * 1000 > max(2 * lc["std_mda"], 0.5):
                    info.append(T("ms_raw_vs_rep", d=f"{(lc['mz'] - rep_found) * 1000:+.2f}"))
                if not st.get("ms_rt"):                  # Felder zeigen den automatischen Bereich
                    self._loading = True
                    for sp_, v in ((self.sp_rt_lo, lc["rt_lo"]), (self.sp_rt_hi, lc["rt_hi"])):
                        sp_.blockSignals(True)
                        sp_.setValue(v / 60)
                        sp_.blockSignals(False)
                    self._loading = False
        pick = st.get("found_pick")
        if pick:                                     # im Spektrum angeklickt
            self.cmb_found.addItem(T("ms_pick_entry", mz=f"{pick:.4f}", ppm=dev_text(ppm(pick, calc))), "pick")
        pdf_v = st.get("found_pdf")                  # aus der Kandidatenliste angeklickt: gilt, solange das PDF ihn nennt
        pdf_ok = pdf_v is not None and kind == "text" and any(v == pdf_v for v, _ in rep["candidates"])
        if pdf_ok:
            self.cmb_found.addItem(T("ms_pdf_entry", mz=f"{pdf_v:.4f}", ppm=dev_text(ppm(pdf_v, calc))), "pdf")
        man = st.get("found_manual")                 # von Hand eingetragen
        if man:
            self.cmb_found.addItem(T("ms_manual_entry", mz=f"{man:.4f}", ppm=dev_text(ppm(man, calc))), "manual")
        # Auswahl: gespeicherte Wahl, sonst Wert aus dem Bericht, sonst Mittel aus den Rohdaten (unbekanntes PDF: nichts)
        want = st.get("found")
        if not ((want == "raw" and lc is not None) or (rep and want in rep["mz"]) or (want == "pick" and pick)
                or (want == "pdf" and pdf_ok) or (want == "manual" and man)):
            want = rep_found if rep_found is not None else ("raw" if lc else None)
        if self._ms_error and st.get("found") not in ("raw", "pick", "manual"):   # Wert käme aus dem unlesbaren
            want = None                                                  # Bericht: nie still durch die Rohdaten ersetzen
        found = {"raw": lc["mz"] if lc else None, "pick": pick, "pdf": pdf_v, "manual": man}.get(want, want)
        if kind == "text" and want is None:
            info.append(T("ms_cand_choose"))
        row = next((r for r in (rep or {}).get("rows") or () if r["meas"] == found), None) if want == found else None
        if row is not None and row.get("calc") is not None and abs(row["calc"] - calc) >= 0.5e-4:
            notes.append(T("ms_sf_calc_differs", rep=f"{row['calc']:.4f}", own=f"{calc:.4f}"))
        # ohne Zuordnung keine Vorauswahl (sonst würde der erste Eintrag beim nächsten collect zu found)
        self.cmb_found.setCurrentIndex(max(0, self.cmb_found.findData(want)) if want is not None else -1)
        self.cmb_found.blockSignals(False)
        ionis = (rep or {}).get("ionisation") or (raw["ionisation"] if raw else "ESI")
        if rep and not rep.get("ionisation"):        # unbekanntes PDF ohne eindeutige Ionisierung: Annahme nennen
            notes.append(T("ms_pdf_ionis", ion=ionis))
        plain, html, calc = ms_line(formula, st["adduct"], found, ionis)
        self._ms_line = (plain, html)
        self._ms_vals = (st["adduct"], calc, found)
        self.txt_ms.setHtml(html)
        if found is not None:
            dev = ppm(found, calc)
            notes.insert(0, T("ms_dev", ppm=dev_text(dev)))
            if not dev_ok(dev):
                notes.append(T("ms_dev_high"))
            self.fill_ms_table(st["adduct"], calc, found, dev)
        self._found = found
        head = notes[:1] if found is not None else []    # „Abweichung found − calc“: Information, keine Warnung
        self.lbl_ms_info.setText("\n".join(head + info))
        self.lbl_ms_warn.setText("\n".join(notes[len(head):]))

    def fill_candidates(self, rep, calc):
        """Kandidaten eines unbekannten PDF (± CAND_WINDOW_DA um calc.) in die Tabelle; nichts wird gewählt, nur der schon
        angeklickte Wert ist markiert. Ein Kandidat gleich calc. auf 4 Stellen ist vermutlich der berechnete Wert."""
        from PySide6.QtGui import QBrush, QColor
        show = bool(rep) and rep.get("kind") == "text" and calc is not None
        self._cands = [(v, line) for v, line in (rep or {}).get("candidates") or () if show and abs(v - calc) <= CAND_WINDOW_DA]
        t = self.tbl_cand
        t.blockSignals(True)
        t.clearSelection()
        t.setRowCount(len(self._cands))
        chosen = self.st.get("found_pdf") if self.st.get("found") == "pdf" else None
        for r, (v, line) in enumerate(self._cands):
            same = f"{v:.4f}" == f"{calc:.4f}"
            cells = (f"{v:.4f}", T("ms_cand_is_calc") if same else dev_text(ppm(v, calc)), line)
            for c, txt in enumerate(cells):
                it = QTableWidgetItem(txt)
                if c == 2:
                    it.setToolTip(line)
                if same:
                    it.setForeground(QBrush(QColor(TABS.STYLE.WARN_COLOR)))
                    it.setToolTip(T("ms_cand_is_calc_tip"))
                t.setItem(r, c, it)
            if v == chosen:
                t.selectRow(r)
        t.blockSignals(False)
        TABS.STYLE.fit_columns(t)
        TABS.STYLE.fit_check_table(t, 6)
        self._form.setRowVisible(t, show)
        self._form.setRowVisible(self.cand_head, show)

    def candidate_clicked(self, r, _c=None):
        """Kandidat übernehmen (nur per Klick): found = "pdf", Wert in found_pdf (Herkunft „aus PDF gewählt“)."""
        if 0 <= r < len(self._cands):
            self.st.update(found="pdf", found_pdf=self._cands[r][0])
            self.render()

    def manual_edited(self):
        """Eigener found-Wert (Herkunft „manuell“); geleert (0) nimmt ihn zurück. Nur bei Änderung ein Schritt."""
        v = round(self.sp_manual.value(), 4) or None
        if v == self.st.get("found_manual"):
            return
        found = "manual" if v else (None if self.st.get("found") == "manual" else self.st.get("found"))
        self.st.update(found_manual=v, found=found)
        self.render()

    def report_image(self):
        """Gewähltes Bild aus dem PDF-Bericht -> dict(page, xref, w, h, w_cm, h_cm, k) oder None."""
        k = int(self.st.get("ms_img") or 0)
        rep = self.ms_report() if k else None
        imgs = (rep or {}).get("images") or []
        return dict(imgs[k - 1], k=k) if 0 < k <= len(imgs) else None

    def image_size_cm(self, im):
        w, h = im["w_cm"], im["h_cm"]
        return (TABS.SI_MAX_W_CM, h * TABS.SI_MAX_W_CM / w) if w > TABS.SI_MAX_W_CM else (w, h)

    def si_parts(self):
        """HR-MS-Zeile für den SI-Export (leer, wenn nichts da ist)."""
        self.update_ms()
        return [self._ms_line] if self._ms_line and self._ms_line[0] else []

    # -- Abbildung ------------------------------------------------------------------
    def view_range(self):
        """m/z-Bereich: automatisch um das Ion (bis zum letzten Isotopenpeak ≥ 1 %), sonst wie eingestellt."""
        st = self.st
        if self._ion is None:
            return None
        formula, z, calc = self._ion
        if not st["x_auto"]:
            return min(st["x_min"], st["x_max"]), max(st["x_min"], st["x_max"])
        pat = self.pattern()
        top = max([m for m, r in pat if r >= 1.0] or [calc])
        bot = min([m for m, r in pat if r >= 1.0] or [calc])          # Isotope unter calc (Pt, Sn, Se …) mit
        d = 1.5 / (abs(z) or 1)
        return min(calc, bot) - d, top + d

    def pattern(self):
        if self._ion is None:
            return []
        formula, z, calc = self._ion
        f_ion = ion(formula, self.st["adduct"])[0]
        return self.cache(("isopat", f_ion, z), lambda: isotope_pattern(f_ion, z))

    def draw_chromatogram(self):
        raw = self.ms_raw()
        ax = self.cax
        ax.cla()
        if raw is None:
            self.ccanvas.draw_idle()
            return
        spectra = self.raw_spectra(raw)
        if not spectra:
            self.ccanvas.draw_idle()
            return
        t, tic = self.cache(("tic", self.st.get("ms_raw"), raw["polarity"] == "±" and self.st["adduct"]),
                            lambda: chromatogram(spectra))
        sc = (tic.max() or 1.0)
        ax.plot(t, tic / sc, color="0.55", lw=0.8, label="TIC")
        lc = self._lc
        if lc is not None:
            xic = lc["xic"]
            xm = xic[:, 2].max() or 1.0
            ax.plot(xic[:, 0] / 60, xic[:, 2] / xm, color=CALC_COLOR, lw=1.0, label="XIC")
            ax.axvspan(lc["rt_lo"] / 60, lc["rt_hi"] / 60, color="#3b6fd4", alpha=0.2, lw=0)
        ax.set_yticks([])
        ax.set_xlim(t.min(), t.max())
        ax.set_ylim(0, 1.08)
        ax.tick_params(labelsize=7, length=2)
        ax.set_xlabel(TABS.core.math_symbols("t [min]"), fontsize=7, labelpad=1)
        ax.legend(fontsize=6, frameon=False, loc="upper right", handlelength=1.2)
        self._span = SpanSelector(ax, self.rt_selected, "horizontal", useblit=False, minspan=0.005,
                                  props=dict(alpha=0.25, facecolor="#3b6fd4"), interactive=False)
        self.ccanvas.draw_idle()

    def rt_selected(self, x0, x1):
        if x1 - x0 < 1e-3:
            return
        self.st["ms_rt"] = [round(float(x0), 3), round(float(x1), 3)]
        self.st["found"] = None if self.st.get("found") == "pick" else self.st.get("found")
        self.sync_widgets()
        self.render()

    def figure_spec(self):
        st = self.st
        self.roles_idle = {"col_calc": "tf_idle_calc"}    # Stilkarte: bis ein berechnetes Muster gezeichnet ist
        self.update_ms()
        self.draw_chromatogram()
        raw = self.ms_raw()
        if raw is None or self._ion is None or self._lc is None:
            self._sticks = (np.zeros(0), np.zeros(0))
            return None
        formula, z, calc = self._ion
        lo, hi = self.view_range()
        lc = self._lc
        mz, it, n = averaged_spectrum(self.raw_spectra(raw), lc["rt_lo"], lc["rt_hi"], lo, hi)
        if not len(mz):
            return None
        rel = 100 * it / it.max()
        self._sticks = (mz, rel)
        cfg = self.base_cfg()
        cfg["xlim"] = [lo, hi]
        show_calc = st.get("show_calc", True)
        ytop = st["ymax"] if st["ymax"] > 0 else 112
        cfg["ylim"] = [-ytop if show_calc else 0, ytop]
        cfg["xlabel"] = "$m/z$"
        cfg["ylabel"] = "relative intensity [%]"
        cfg["zero_lines"] = [0.0] if show_calc else []
        f_ion = ion(formula, st["adduct"])[0]
        sign = "+" if z > 0 else "−"
        curves = [{"x": np.zeros(0), "y": np.zeros(0), "color": TABS.role_color(self.st, "col_meas", MEASURED_COLOR), "label": "measured"}]
        sticks = [{"x": mz, "h": rel, "color": TABS.role_color(self.st, "col_meas", MEASURED_COLOR)}]
        pat = self.pattern()
        if show_calc and pat:
            pm = np.array([m for m, _ in pat])
            pr = np.array([r for _, r in pat])
            sticks.append({"x": pm, "h": -pr, "color": TABS.role_color(self.st, "col_calc", CALC_COLOR)})
            self.roles_idle = {}
            f_tex = re.sub(r"(\d+)", r"$_{\1}$", f_ion)
            curves.append({"x": np.zeros(0), "y": np.zeros(0), "color": TABS.role_color(self.st, "col_calc", CALC_COLOR),
                           "label": f"calculated ({f_tex}$^{{{sign}}}$)"})
        labels = []
        if st.get("mz_labels", True):
            vis = (mz >= lo) & (mz <= hi) & (rel >= 8)
            for k in np.argsort(-rel)[:12]:
                if vis[k] and len(labels) < 6:
                    labels.append({"key": f"label_mz_{mz[k]:.3f}", "lam": float(mz[k]), "y": float(rel[k]),
                                   "text": f"{mz[k]:.4f}", "side": "above"})
        self.isotope_info(mz, rel, pat)
        return cfg, curves, labels, sticks

    def isotope_info(self, mz, rel, pat):
        """Gemessene gegen berechnete Isotopenverhältnisse (relativ zum monoisotopischen Peak) an die Hinweise."""
        if not pat or not len(mz):
            return
        items = []
        mono = None
        for i, (m, r) in enumerate(pat[:4]):
            j = int(np.argmin(np.abs(mz - m)))
            if abs(ppm(mz[j], m)) > 10:
                continue
            if i == 0:
                mono = (rel[j], r)
                continue
            if mono:
                items.append(f"M+{i} {100 * rel[j] / mono[0]:.0f} % / {100 * r / mono[1]:.0f} %")
        if items:
            txt = self.lbl_ms_info.text()
            self.lbl_ms_info.setText((txt + "\n" if txt else "") + T("ms_iso_info", items=", ".join(items)))
            QTimer.singleShot(0, self._form, self._form.invalidate)

    def fill_ms_table(self, adduct, calc, found, dev):
        from PySide6.QtGui import QBrush, QColor
        ok = dev_ok(dev)
        lab, _, z = ADDUCTS[adduct]
        N = TABS.STYLE.num                                # CSV: Rohwerte, Status englisch
        TABS.STYLE.fill_summary(self.tbl_ms, [[lab.replace("$_4$", "₄") + ("⁺" if z > 0 else "⁻"), N(f"{calc:.4f}", calc),
                                               N(f"{found:.4f}", found), N(dev_text(dev), dev),
                                               N(("✓ " if ok else "⚠ ") + T("ea_chk_ms_ok" if ok else "ea_chk_ms_bad"),
                                                 T_en("ea_chk_ms_ok" if ok else "ea_chk_ms_bad"))]])
        self._form.setRowVisible(self._ms_head, True)
        if not ok:
            for c in range(self.tbl_ms.columnCount()):
                self.tbl_ms.item(0, c).setForeground(QBrush(QColor(TABS.STYLE.WARN_COLOR)))

    def kpis(self):
        txt = self.cmb_found.currentText().strip()
        out = [(T("kpi_found"), txt)] if txt else []
        v = getattr(self, "_ms_vals", None)
        if out and v and v[2] is not None:          # Abweichung als eigene Kachel, über 5 ppm in der Warnfarbe
            dev = ppm(v[2], v[1])
            out = [(T("kpi_found"), f"{v[2]:.4f}"),
                   (T("ea_chk_ms_kpi"), f"{dev_text(dev)} ppm", not dev_ok(dev))]
        return out

    def build(self, fig):
        F = super().build(fig)
        if F is not None and self.st.get("show_calc", True):     # gespiegelt: Beträge an der y-Achse
            from matplotlib.ticker import FuncFormatter
            F.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{abs(v):g}"))
        return F

    def render(self):
        if self._pick_cid is not None:
            self.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = None
        im = self.report_image()
        if im is None:
            super().render()
            if self.F is not None:
                self._pick_cid = self.canvas.mpl_connect("button_press_event", self.spectrum_clicked)
            self.sync_empty()
            return
        # Bild aus dem PDF-Bericht unverändert zeigen (wie im Tab „Weitere“), gekennzeichnet als Bild aus dem Bericht
        self.notes_begin()
        for attr in ("dragger", "hover"):
            if getattr(self, attr):
                getattr(self, attr).disconnect()
                setattr(self, attr, None)
        self.fig.clear()
        self.F = None
        try:
            self.update_ms()
            self.draw_chromatogram()
            p = self.st["ms_file"]
            arr = self.cache(("msimg", p, im["xref"], os.path.getmtime(p)), lambda: pdf_image_array(p, im["xref"]))
            w, h = self.image_size_cm(im)
            self.host.set_figure_size(w / 2.54, h / 2.54)
            ax = self.fig.add_axes([0, 0, 1, 1])
            ax.imshow(arr)
            ax.set_axis_off()
            self.F = ax
            self.preview_stack.setCurrentIndex(1)
            self.show_caption()
            self.canvas.draw_idle()
            self.notes_show()
        except Exception as ex:
            self.preview_stack.setCurrentIndex(0)
            self.notes_show(error=ex)
        if self.label_card is not None:
            self.label_card.fill(())
        self.main.push_undo()

    def sync_empty(self):
        """PDF-Bericht geladen, aber kein Bild daraus gewählt und keine .d-Daten: ein Satz statt der allgemeinen
        Anleitung (Nutzerwunsch); sonst die Anleitung."""
        g = self.empty_guide
        if g is None:
            return
        p = self.st.get("ms_file")
        only = self.F is None and bool(p) and Path(p).suffix.lower() == ".pdf" and not self.st.get("ms_raw")
        g.label.setText(f"<p style='font-size:15px'>{T('hrms_no_spectrum')}</p>" if only else TABS.guide_html(self.GUIDE))
        if g.btn is not None:
            g.btn.setVisible(not only)
        g.fit_width()

    def copy_figure(self, tmp):
        if self.report_image() is not None:      # Bild aus dem Bericht: kein eigenes SVG (wie Tab „Weitere“)
            return T("copy_fig_none")
        return super().copy_figure(tmp)

    def si_caption(self, name):
        cap = super().si_caption(name)
        return cap[:-1] + IMG_CAPTION + "." if self.report_image() is not None else cap

    def si_figure(self, out_dir, name):
        im = self.report_image()
        if im is None:
            return super().si_figure(out_dir, name)
        png = pdf_image_png(self.st["ms_file"], im["xref"], Path(out_dir) / f"{core.safe_name(name)}_hrms_report.png")
        w, h = self.image_size_cm(im)
        return [("image", str(png), w, h, None), ("figcap", self.si_caption(name))]

    def spectrum_clicked(self, ev):
        """Klick auf einen Peak (nicht auf ein Label) -> als found übernehmen."""
        F = self.F
        if F is None or ev.inaxes is not F.ax or ev.button != 1 or ev.dblclick:
            return
        if any(a.contains(ev)[0] for a in F.ann_items.values()):
            return
        mz, rel = self._sticks
        if not len(mz):
            return
        px = F.ax.transData.transform(np.column_stack([mz, np.zeros_like(mz)]))[:, 0]
        j = int(np.argmin(np.abs(px - ev.x)))
        if abs(px[j] - ev.x) > 6 * self.fig.dpi / 72:
            return
        self.st.update(found="pick", found_pick=round(float(mz[j]), 5))
        self.render()

    def hover_text(self, x, val, name):
        return f"m/z = {x:.4f}"

    def export_to(self, base: Path):
        """Abbildung (falls Rohdaten), Strichspektrum + Isotopenmuster als CSV und die SI-Zeile als Text."""
        base = Path(base)
        files = []
        im = self.report_image()
        if im is not None:                           # Bild aus dem PDF-Bericht unverändert als PNG
            base.parent.mkdir(parents=True, exist_ok=True)
            files = [pdf_image_png(self.st["ms_file"], im["xref"], PRJ.with_ext(base, ".png"))]
            self.update_ms()
        elif self.ms_raw() is not None:
            files = super().export_to(base)
            for f_ in [f_ for f_ in files if f_.name.endswith("_data.csv")]:   # Linienspektren sind keine Kurven:
                f_.unlink(missing_ok=True)                                     # die Daten stehen in _sticks.csv
                files.remove(f_)
            mz, rel = self._sticks
            p = base.with_name(base.name + "_sticks.csv")
            pat = self.pattern()
            n = max(len(mz), len(pat))
            TBL.write_csv(p, ["measured m/z", "measured rel. int. [%]", "calculated m/z", "calculated rel. int. [%]"],
                          [([float(mz[i]), float(rel[i])] if i < len(mz) else [None, None])
                           + ([float(pat[i][0]), float(pat[i][1])] if i < len(pat) else [None, None]) for i in range(n)])
            files.append(p)
        else:
            self.update_ms()
        p = base.with_name(base.name + "_SI.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((self._ms_line[0] or "") + "\n", encoding="utf-8")
        return files + [p]
