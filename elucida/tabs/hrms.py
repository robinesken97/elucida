"""HRMS: Bericht der Massenabteilung (docx) und Bruker-Rohdaten (.d) – Chromatogramm mit wählbarem LC-Bereich,
gemitteltes Spektrum (Linienspektren des Geräts), Peak per Klick als found, berechnetes Isotopenmuster aus der
Summenformel (gespiegelt), SI-Zeile. Leser und Ionenmassen stehen in tabs/ir_ea.py."""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from matplotlib.widgets import SpanSelector
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QTextBrowser, QWidget)

from elucida.tabs import base as TABS
from elucida.app.i18n import T
from elucida.app import project as PRJ
from elucida.tabs.ir_ea import (ADDUCTS, ELECTRON, copy_rich, ion, is_bruker_d, lc_found, ms_line, nearest, parse_formula,
                        ppm, read_bruker_d, read_ms_docx)
from elucida.app.style import HINT_CSS, WARN_CSS, make_form
from elucida.formats.bruker_ms import spectra_of
from elucida.tabs.ir_ea import mono_mass

MEASURED_COLOR, CALC_COLOR = "#111111", "#c0392b"


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
class HRMSTab(TABS.FigureTab):
    STATE_KEY = "hrms"
    GUIDE, GUIDE_ACTION = "hrms", ("guide_add", "choose_ms")
    SI_CAPTION = "HR-MS spectrum of {name}."
    X_RANGE = (10.0, 5000.0, 2, 0.5)
    XRANGE_TEXT = "ms_xrange"
    RESET_KEEP = ("ms_file", "ms_raw", "ms_rt", "adduct", "found", "found_pick")
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=100.0, x_max=1000.0, ymax=0.0, ms_file=None, ms_raw=None,
                         ms_rt=None, adduct="M+H", found=None, found_pick=None, show_calc=True, mz_labels=True)

    def build_controls(self):
        st = self.st
        g = QGroupBox(T("ms_group"))
        f = make_form(g)
        self._form = f
        row = QHBoxLayout()
        self.lbl_ms = QLabel("–")
        self.lbl_ms.setWordWrap(True)
        self.lbl_ms.setToolTip(T("ms_file_tip"))
        b = QPushButton(T("choose"))
        b.setToolTip(T("ms_file_tip"))
        b.clicked.connect(self.choose_ms)
        row.addWidget(self.lbl_ms, 1)
        row.addWidget(b)
        f.addRow(T("ms_file"), row)
        row = QHBoxLayout()
        self.lbl_raw = QLabel("–")
        self.lbl_raw.setWordWrap(True)
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
        self.rt_row = QWidget()
        self.rt_row.setLayout(row)
        f.addRow(T("ms_rt"), self.rt_row)
        # Chromatogramm (Werkzeug, nicht Teil der Abbildung): Ziehen setzt den LC-Bereich
        self.cfig = MplFigure(figsize=(4.2, 1.5), dpi=100)
        self.ccanvas = FigureCanvasQTAgg(self.cfig)
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
        self.cmb_found = QComboBox()
        self.cmb_found.setToolTip(T("ms_found_tip"))
        f.addRow(T("ms_found"), self.cmb_found)
        self.lbl_ms_info = QLabel("")
        self.lbl_ms_info.setWordWrap(True)
        f.addRow(self.lbl_ms_info)
        self.txt_ms = QTextBrowser()
        self.txt_ms.setMaximumHeight(70)
        f.addRow(self.txt_ms)
        b = QPushButton(T("ms_copy"))
        b.clicked.connect(lambda: copy_rich(*self._ms_line))
        f.addRow(b)
        self.lv.addWidget(g)

        g = QGroupBox(T("ms_display"))
        f = make_form(g)
        self.cb_calc = QCheckBox(T("ms_show_calc"))
        self.cb_calc.setChecked(st.get("show_calc", True))
        self.cb_mzlab = QCheckBox(T("ms_mz_labels"))
        self.cb_mzlab.setChecked(st.get("mz_labels", True))
        f.addRow(self.cb_calc)
        f.addRow(self.cb_mzlab)
        hint = QLabel(T("ms_pick_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(HINT_CSS)
        f.addRow(hint)
        self.lv.addWidget(g)

        self._ms_line = ("", "")
        self._ms_vals = None                          # (Addukt, calc, found) der letzten SI-Zeile (Austauschdatei)
        self._ion = self._lc = self._found = None
        self._sticks = (np.zeros(0), np.zeros(0))
        self._pick_cid = None
        self.cb_rt_auto.toggled.connect(self.changed)
        for w_ in (self.sp_rt_lo, self.sp_rt_hi):
            w_.valueChanged.connect(self.changed)
        for w_ in (self.cb_calc, self.cb_mzlab):
            w_.toggled.connect(self.changed)
        self.cmb_adduct.currentIndexChanged.connect(self.adduct_changed)
        self.cmb_found.currentIndexChanged.connect(self.changed)
        self.sync_widgets()

    def compound_changed(self):
        self.sync_widgets()
        self.timer.start()

    def sync_widgets(self):
        st = self.st
        self._loading = True
        rep = self.ms_report()
        self.lbl_ms.setText((Path(st["ms_file"]).name + (f"  ({rep['sample']})" if rep and rep.get("sample") else ""))
                            if st.get("ms_file") else "–")
        raw = self.ms_raw()
        self.lbl_raw.setText((Path(st["ms_raw"]).name + (f"  ({raw['instrument']})" if raw and raw.get("instrument")
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
                  show_calc=self.cb_calc.isChecked(), mz_labels=self.cb_mzlab.isChecked())
        self.sync_widgets()

    def choose_ms(self):
        if not self.main.ensure_project():
            return
        p, _ = QFileDialog.getOpenFileName(self, T("ms_file"), self.main.settings.value("last_dir", ""),
                                           f"Word (*.docx);;{T('flt_all')}")
        if p:
            self.load_ms(p)

    def load_ms(self, p):
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        try:
            read_ms_docx(p)
        except Exception as e:
            self.main.error(f"{Path(p).name}: {e}")
            return
        self.st.update(ms_file=p, found=None)
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
        return self.cache(("msdocx", p), lambda: read_ms_docx(p))

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
        st = self.st
        self._ion, self._lc, self._found = None, None, None
        rep = self.ms_report()
        formula, src = self.formula()
        notes = []
        self._ms_line = ("", "")
        self._ms_vals = None
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
        self._ion = (formula, z, calc)
        self.btn_take.setVisible(bool(rep and rep.get("structure")))
        raw = self.ms_raw()
        lc = self.raw_found(calc) if raw else None
        self._lc = lc
        rep_found = None
        info = []                                    # Hinweise ohne Warnung
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
            rep_found = nearest(rep["mz"], calc)
            if rep_found is None:
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
                                         ppm=f"{ppm(lc['mz'], calc):+.1f}"), "raw")
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
            self.cmb_found.addItem(T("ms_pick_entry", mz=f"{pick:.4f}", ppm=f"{ppm(pick, calc):+.1f}"), "pick")
        # Auswahl: gespeicherte Wahl, sonst Wert aus dem Bericht, sonst Mittel aus den Rohdaten
        want = st.get("found")
        if not ((want == "raw" and lc is not None) or (rep and want in rep["mz"]) or (want == "pick" and pick)):
            want = rep_found if rep_found is not None else ("raw" if lc else None)
        found = lc["mz"] if want == "raw" else (pick if want == "pick" else want)
        # ohne Zuordnung keine Vorauswahl (sonst würde der erste Eintrag beim nächsten collect zu found)
        self.cmb_found.setCurrentIndex(max(0, self.cmb_found.findData(want)) if want is not None else -1)
        self.cmb_found.blockSignals(False)
        ionis = rep["ionisation"] if rep else (raw["ionisation"] if raw else "ESI")
        plain, html, calc = ms_line(formula, st["adduct"], found, ionis)
        self._ms_line = (plain, html)
        self._ms_vals = (st["adduct"], calc, found)
        self.txt_ms.setHtml(html)
        if found is not None:
            dev = ppm(found, calc)
            notes.insert(0, T("ms_dev", ppm=f"{dev:+.1f}"))
            if abs(dev) > 5:
                notes.append(T("ms_dev_high"))
        warn = len(notes) > 1 or (found is None and bool(rep or raw))
        self._found = found
        self.lbl_ms_info.setText("\n".join(notes[:1] + info + notes[1:]))
        self.lbl_ms_info.setStyleSheet(WARN_CSS if warn else HINT_CSS)

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
        ax.set_xlabel("t [min]", fontsize=7, labelpad=1)
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
        curves = [{"x": np.zeros(0), "y": np.zeros(0), "color": MEASURED_COLOR, "label": "measured"}]
        sticks = [{"x": mz, "h": rel, "color": MEASURED_COLOR}]
        pat = self.pattern()
        if show_calc and pat:
            pm = np.array([m for m, _ in pat])
            pr = np.array([r for _, r in pat])
            sticks.append({"x": pm, "h": -pr, "color": CALC_COLOR})
            f_tex = re.sub(r"(\d+)", r"$_{\1}$", f_ion)
            curves.append({"x": np.zeros(0), "y": np.zeros(0), "color": CALC_COLOR,
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

    def build(self, fig):
        F = super().build(fig)
        if F is not None and self.st.get("show_calc", True):     # gespiegelt: Beträge an der y-Achse
            from matplotlib.ticker import FuncFormatter
            F.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{abs(v):g}"))
        return F

    def render(self):
        super().render()
        if self._pick_cid is not None:
            self.canvas.mpl_disconnect(self._pick_cid)
            self._pick_cid = None
        if self.F is not None:
            self._pick_cid = self.canvas.mpl_connect("button_press_event", self.spectrum_clicked)

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
        if self.ms_raw() is not None:
            files = super().export_to(base)
            mz, rel = self._sticks
            p = base.with_name(base.name + "_sticks.csv")
            pat = self.pattern()
            n = max(len(mz), len(pat))
            with open(p, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write("measured m/z,measured rel. int. [%],calculated m/z,calculated rel. int. [%]\n")
                for i in range(n):
                    a = f"{mz[i]:.5f},{rel[i]:.3f}" if i < len(mz) else ","
                    b = f"{pat[i][0]:.5f},{pat[i][1]:.3f}" if i < len(pat) else ","
                    fh.write(f"{a},{b}\n")
            files.append(p)
        else:
            self.update_ms()
        p = base.with_name(base.name + "_SI.txt")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((self._ms_line[0] or "") + "\n", encoding="utf-8")
        return files + [p]
