"""elucida/tabs/fluo_tau.py - Fluoreszenz-Tab, zeitaufgelöst: Abklingkurve (+ IRF) laden, Lebensdauer mit ein oder zwei
Exponentialen fitten (`core.lifetime`), Abbildung mit Residuen und die Kennwerte λabs, ε, λem, Φ, τ, k_r, k_nr.

Karten links: „Abklingkurve“ (Dateien, Zeiteinheit, λex/λem der Messung) im Schritt Daten, „Lebensdauer“ (Modell,
Start, τ für k_r/k_nr, Φ) im Schritt Auswertung. Rechts zwei Reiter: „Abklingkurve“ (Bild + Fitparameter) und
„Kennwerte“. Zustand in den flachen Schlüsseln des Fluoreszenz-Tabs (`decay_file`, `irf_file`, `tau_*`, `phi`).
"""
from __future__ import annotations

import html
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register as register_canvas
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS, WARN_CSS, make_form
from elucida.core import lifetime as LT
from elucida.core import tables as TBL
from elucida.core import uvvis as core
from elucida.formats.decay import TIME_UNITS, read_decay
from elucida.tabs import base as TABS

C_DATA, C_IRF, C_RES = "#7f7f7f", "#b0b0b0", "#000000"


def fmt_tau(v, us=False, sig=3):
    """τ (ns) als Text ohne Exponent („1.5e+03“ war in Bild/Tabelle/SI unlesbar); `us`: in µs (`TauPart.us`)."""
    v = v / 1000 if us else v
    s = f"{v:.{sig}g}"
    if "e" in s:
        s = f"{v:.{max(0, sig - 1 - int(np.floor(np.log10(abs(v)))))}f}"
    return s


def fmt_ci(ci, us=False):
    """Grenzen des Intervalls mit so vielen Stellen, dass sie nicht zusammenfallen (3 bis 8 signifikante)."""
    for sig in range(3, 9):
        lo, hi = fmt_tau(ci[0], us, sig), fmt_tau(ci[1], us, sig)
        if lo != hi:
            break
    return lo, hi


def parse_phi(txt):
    """Φ aus dem Feld: Zahl in (0, 1] oder None; „42 %“ gilt als 0.42."""
    s = str(txt or "").strip().replace(",", ".")
    pct = s.endswith("%")
    v = TABS.parse_num(s.rstrip("% "))
    if v is None:
        return None
    v = v / 100 if pct else v
    return v if 0 < v <= 1 else None


class TauPart:
    """Lebensdauer im Fluoreszenz-Tab (Karten, Reiter, Fit, SI)."""

    fmt_tau = staticmethod(fmt_tau)

    def __init__(self, tab):
        self.tab = tab
        self.res = self.err = self.data = self.irf = None
        self.text_rows = []

    @property
    def st(self):
        return self.tab.st

    # -- linke Spalte --------------------------------------------------------------
    def build_cards(self, lv):
        st = self.st
        g = QGroupBox(T("fluo_tau_data"))
        f = make_form(g)
        self.lbl_decay = self._file_row(f, T("fluo_tau_decay"), "decay_file")
        self.lbl_irf = self._file_row(f, T("fluo_tau_irf"), "irf_file")
        self.cmb_unit = QComboBox()
        for u in TIME_UNITS:
            self.cmb_unit.addItem("µs" if u == "us" else u, u)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["tau_unit"])))
        self.cmb_unit.setToolTip(T("fluo_tau_unit_tip"))
        f.addRow(T("fluo_tau_unit"), self.cmb_unit)
        self.sp_ex, self.sp_em = (self._lam_spin(st[k]) for k in ("tau_ex", "tau_em"))
        f.addRow(T("fluo_tau_ex"), self.sp_ex)
        f.addRow(T("fluo_tau_em"), self.sp_em)
        self.lbl_info = STYLE.HintLabel("")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_info)
        lv.addWidget(g)

        g = QGroupBox(T("fluo_tau_fit"))
        f = make_form(g)
        self.cmb_n = QComboBox()
        for n in (1, 2):
            self.cmb_n.addItem(T(f"fluo_tau_n{n}"), n)
        self.cmb_n.setCurrentIndex(max(0, self.cmb_n.findData(st["tau_n"])))
        self.cmb_n.setToolTip(T("fluo_tau_n_tip"))
        f.addRow(T("fluo_tau_model"), self.cmb_n)
        self.sp_start = QDoubleSpinBox(decimals=2, minimum=0, maximum=1e5, singleStep=0.1, suffix=" ns",
                                       value=st["tau_start"])
        self.sp_start.setToolTip(T("fluo_tau_start_tip"))
        self.lab_start = QLabel(T("fluo_tau_start"))
        f.addRow(self.lab_start, self.sp_start)
        self.cmb_avg = QComboBox()
        for k in ("amp", "int"):
            self.cmb_avg.addItem(T("fluo_tau_avg_" + k), k)
        self.cmb_avg.setCurrentIndex(max(0, self.cmb_avg.findData(st["tau_avg"])))
        self.cmb_avg.setToolTip(T("fluo_tau_avg_tip"))
        self.lab_avg = QLabel(T("fluo_tau_avg"))
        f.addRow(self.lab_avg, self.cmb_avg)
        self.ed_phi = QLineEdit(st["phi"])
        self.ed_phi.setPlaceholderText(T("fluo_tau_phi_ph"))
        self.ed_phi.setToolTip(T("fluo_tau_phi_tip"))
        f.addRow(T("fluo_tau_phi"), self.ed_phi)
        lv.addWidget(g)
        for w in (self.sp_ex, self.sp_em, self.sp_start):
            w.valueChanged.connect(self.tab.changed)
        for w in (self.cmb_unit, self.cmb_n, self.cmb_avg):
            w.currentIndexChanged.connect(self.tab.changed)
        self.ed_phi.editingFinished.connect(self.tab.changed)
        self.texts = TABS.PageTexts(self.tab, lambda: "decay", self.show_page, "lab_card_decay")   # feste Texte
        lv.addWidget(self.texts.box)
        self.texts.box.hide()                              # erst mit Abklingkurve
        self.sync_rows()

    @staticmethod
    def _lam_spin(v):
        sp = QDoubleSpinBox(decimals=0, minimum=0, maximum=1500, singleStep=1, suffix=" nm", value=v)
        sp.setSpecialValueText(T("fluo_tau_none"))
        return sp

    def _file_row(self, form, label, key):
        tab = self.tab
        row = QHBoxLayout()
        lbl = QLabel(Path(self.st[key]).name if self.st.get(key) else "–")
        b1, b2 = QPushButton(T("choose")), QPushButton(T("remove"))
        row.addWidget(lbl, 1)
        row.addWidget(b1)
        row.addWidget(b2)
        form.addRow(label, row)

        def choose():
            if not tab.main.ensure_project():
                return
            p, _ = QFileDialog.getOpenFileName(tab, label, tab.main.settings.value("last_dir", ""),
                                               f"{T('fluo_tau_flt')};;{T('flt_all')}")
            if not p:
                return
            try:
                d = read_decay(p)
                p = tab.main.import_file(p, PRJ.data_sub(tab.STATE_KEY))
            except Exception as e:
                return tab.main.error(f"{Path(p).name}: {e}")
            self.st[key] = p
            if d["unit"] and key == "decay_file":          # Einheit aus dem Spaltenkopf übernehmen
                self.st["tau_unit"] = d["unit"]
                self.cmb_unit.blockSignals(True)
                self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(d["unit"])))
                self.cmb_unit.blockSignals(False)
            lbl.setText(Path(p).name)
            self.sync_rows()
            tab.timer.start()

        def remove():
            self.st[key] = None
            lbl.setText("–")
            self.sync_rows()
            tab.timer.start()
        b1.clicked.connect(choose)
        b2.clicked.connect(remove)
        return lbl

    def sync_rows(self):
        """Start nur ohne IRF, „τ für k_r, k_nr“ nur bei zwei Exponentialen (Zeile samt Beschriftung)."""
        tail = not self.st.get("irf_file")
        for w in (self.lab_start, self.sp_start):
            w.setVisible(tail)
        two = self.cmb_n.currentData() == 2
        for w in (self.lab_avg, self.cmb_avg):
            w.setVisible(two)

    def collect(self):
        self.st.update(tau_unit=self.cmb_unit.currentData(), tau_ex=self.sp_ex.value(), tau_em=self.sp_em.value(),
                       tau_n=self.cmb_n.currentData(), tau_start=self.sp_start.value(),
                       tau_avg=self.cmb_avg.currentData(), phi=self.ed_phi.text().strip())
        self.sync_rows()

    # -- rechte Seite -----------------------------------------------------------------
    def build_pages(self):
        """-> [(Karte, Titel)] für `to_right`: Abklingkurve (Bild + Parameter) und Kennwerte."""
        g = QGroupBox(T("fluo_tau_page"))
        v = QVBoxLayout(g)
        self.stack = QStackedWidget()
        none = STYLE.SciLabel("", T("fluo_tau_empty"))
        none.setWordWrap(True)
        self.stack.addWidget(none)
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        self.fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
        self.canvas = register_canvas(FigureCanvasQTAgg(self.fig))
        self.host = TABS.CanvasHost(self.canvas, self.fig, margin=0)
        self.host.setMinimumHeight(260)
        cv.addWidget(self.host, 4)                         # das Bild hat Vorrang
        self.tbl_fit = STYLE.name_table(STYLE.summary_grid(self._fit_heads("ns")), "lifetime_fit", "Lifetime fit", csv=True)
        cv.addWidget(self.tbl_fit)
        self.tbl_fit2 = STYLE.name_table(STYLE.summary_grid(self._fit2_heads("ns")), "lifetime_summary",
                                         "Lifetime fit summary", csv=True)
        cv.addWidget(self.tbl_fit2)
        self.lbl_fit = STYLE.SciLabel("")
        self.lbl_fit.setWordWrap(True)
        cv.addWidget(self.lbl_fit)
        self.stack.addWidget(content)
        v.addWidget(self.stack, 1)

        g2 = QGroupBox(T("fluo_tau_props"))
        g2.setProperty("hug", True)                          # eine Zeile: Karte so hoch wie ihr Inhalt
        v2 = QVBoxLayout(g2)
        self.tbl_props = STYLE.name_table(STYLE.summary_grid(self._prop_heads("τ [ns]"), rich=(5, 6)),
                                          "photophysics", "Photophysical properties", csv=True)
        v2.addWidget(self.tbl_props)
        self.lbl_props = STYLE.SciLabel("", T("fluo_tau_props_empty"))
        self.lbl_props.setWordWrap(True)
        v2.addWidget(self.lbl_props)
        return [(g, T("fluo_tau_page")), (g2, T("fluo_tau_props"))]

    @staticmethod
    def _fit_heads(u):
        return [T("fluo_tau_col_comp"), f"τ [{u}]", T("fluo_tau_col_ci"), "A" + STYLE.QTY, T("fluo_tau_col_frac")]

    @staticmethod
    def _fit2_heads(u):
        return [f"τ_amp [{u}]", f"τ_int [{u}]", T("fluo_tau_bg") + STYLE.QTY, T("fluo_tau_shift"), "χ²_red",
                T("fluo_tau_npts")]

    @staticmethod
    def _prop_heads(tau_head):
        return ["λ_abs [nm]", "ε [M⁻¹ cm⁻¹]", "λ_em [nm]", "Φ", tau_head, "k_r [s⁻¹]", "k_nr [s⁻¹]"]

    # -- Daten und Fit ------------------------------------------------------------------
    def _read(self, key):
        p = self.st.get(key)
        if not p or not Path(p).exists():
            return None
        d = self.tab.cache(("decay", p), lambda: read_decay(p))
        unit = d["unit"] if key == "irf_file" and d["unit"] else self.st.get("tau_unit")   # IRF: eigene Einheit zählt
        return dict(d, t=d["t"] * TIME_UNITS.get(unit, 1.0))

    def update(self):
        """Kurven lesen und fitten (Ergebnis zwischengespeichert), Reiter und Tabellen füllen."""
        st = self.st
        self.res = self.err = self.data = self.irf = None
        info = []
        try:
            self.data = self._read("decay_file")
            self.irf = self._read("irf_file") if self.data is not None else None
        except Exception as e:
            self.err = str(e)
            self.tab.main.skip_part(e, part=Path(st.get("decay_file") or "").name)   # Export: Datei und Grund melden
        if self.data is not None:
            d = self.data
            if d["ncols"] > 2:
                info.append(T("fluo_tau_cols", n=d["ncols"]))
            u = "µs" if st.get("tau_unit") == "us" else st.get("tau_unit")
            if not d["unit"]:                              # nie still ns annehmen: Einheit sichtbar prüfen lassen
                info.append(T("fixr_decay_unit", u=u))
            if self.irf is not None and not self.irf["unit"]:
                info.append(T("fixr_irf_unit", u=u))
            key = ("tau_fit", st.get("decay_file"), st.get("irf_file"), st.get("tau_unit"), st.get("tau_n"),
                   st.get("tau_start"))
            try:
                irf = (self.irf["t"], self.irf["y"]) if self.irf is not None else None
                self.res = self.tab.cache(key, lambda: LT.fit_decay(d["t"], d["y"], st["tau_n"], irf, st["tau_start"]))
            except Exception as e:
                self.err = T("fluo_tau_fit_fail", e=e)
                self.tab.main.skip_part(self.err, st.get("decay_file"))
        if self.err:
            info.append(self.err)
        if self.res is not None and self.res["at_bound"]:
            info.append(T("fluo_tau_bound"))
        if hasattr(self, "lbl_info"):
            self.lbl_info.setText("\n".join(info))
            warn = self.err or (self.res and self.res["at_bound"]) or (self.data is not None and not self.data["unit"])
            self.lbl_info.setStyleSheet(WARN_CSS if warn else HINT_CSS)
        if hasattr(self, "stack"):
            self.show_page()
            self.show_props()

    def us(self):
        """τ in µs, sobald die längste Lebensdauer ≥ 1000 ns ist (dann überall: Bild, Tabellen, Kennwerte, SI)."""
        return self.res is not None and max(self.res["tau"]) >= 1000

    def tau_unit(self):
        return "µs" if self.us() else "ns"

    def tau_used(self):
        """(τ für k_r/k_nr in ns, Art: 'single'|'amp'|'int') oder (None, None)."""
        r = self.res
        if r is None:
            return None, None
        if r["n_exp"] == 1:
            return r["tau"][0], "single"
        k = self.st.get("tau_avg", "amp")
        return r["tau_" + k], k

    # -- Abbildung ----------------------------------------------------------------------
    def draw(self, fig):
        """Abklingkurve (log) mit Fit und IRF, darunter die Residuen; Größe und Schrift wie die Abbildung des Tabs."""
        r, d = self.res, self.data
        cfg = self.tab.base_cfg()
        cfg.pop("extra_labels", None)                     # eigene Labels gehören zur Hauptabbildung des Tabs
        core.setup_fonts(plt, cfg)
        fs, lw, sc = cfg["font_size"], cfg["line_width"], cfg.get("scale", 1.0)
        fig.clear()
        fig.set_size_inches(cfg["figsize_in"], forward=False)
        ax, axr = fig.subplots(2, 1, sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
        y = np.asarray(d["y"], float)
        pos = y[y > 0]
        floor = max(float(pos.min()) if len(pos) else 1.0, float(y.max()) * 1e-4)
        ax.semilogy(d["t"], np.clip(y, floor, None), ".", ms=2.0 * sc, color=C_DATA, zorder=1)
        if self.irf is not None:
            yi = np.asarray(self.irf["y"], float)
            ax.semilogy(self.irf["t"], np.clip(yi / yi.max() * y.max(), floor, None), color=C_IRF,
                        lw=lw * 1.2, zorder=2)
        ax.semilogy(r["t"], np.clip(r["fit"], floor, None), color=self.st["c_em"], lw=lw * 1.6, zorder=3)
        ax.set_ylim(floor * 0.8, float(y.max()) * 2.0)
        axr.plot(r["t"], r["resid"], color=C_RES, lw=lw * 0.8)
        axr.axhline(0, color=C_IRF, lw=lw)
        m = float(np.nanmax(np.abs(r["resid"]))) or 1.0
        axr.set_ylim(-1.15 * m, 1.15 * m)
        ax.set_xlim(float(d["t"][0]), float(d["t"][-1]))
        ax.set_ylabel(core.fmt_text("counts" if r["weighted"] else "intensity [arb. u.]", cfg),
                      fontsize=core.axis_title_size(cfg))
        axr.set_ylabel(core.fmt_text("res.", cfg), fontsize=core.axis_title_size(cfg))
        axr.set_xlabel(core.fmt_text("t [ns]", cfg), fontsize=core.axis_title_size(cfg))
        for a in (ax, axr):
            a.tick_params(which="both", direction=cfg.get("tick_direction", "out"), labelsize=core.tick_size(cfg))
            a.tick_params(which="major", length=6 * sc, width=max(0.6, sc))
            a.tick_params(which="minor", length=3 * sc, width=max(0.5, 0.8 * sc))
            if not cfg.get("frame", True):
                a.spines["top"].set_visible(False)
                a.spines["right"].set_visible(False)
        us, u = self.us(), self.tau_unit()
        lines = [core.fmt_text(f"τ$_{{{i + 1}}}$ = {fmt_tau(t, us)} {u}" if r["n_exp"] == 2 else f"τ = {fmt_tau(t, us)} {u}",
                               cfg) for i, t in enumerate(r["tau"])]
        if r["chi2_red"] is not None:
            lines.append(core.fmt_text(f"χ$^2_{{\\mathrm{{red}}}}$ = {r['chi2_red']:.2f}", cfg))
        ax.text(0.97, 0.95, "\n".join(lines), transform=ax.transAxes, ha="right", va="top", fontsize=fs * 1.1,
                linespacing=1.4)
        # eigene feste Texte (Karte „Beschriftungen: Abklingkurve“) vor dem Einpassen; gilt auch für Export und SI
        self.text_rows = TABS.FT.apply(fig, None, self.st.get("text_over"), cfg)
        fig.tight_layout(pad=0.6, h_pad=0.3)
        if self.tab.LINE_STYLE:                         # Linienbreiten der Stilkarte wie im Spektrenbild
            TABS.apply_lines(fig, self.tab.main.text_format(self.tab.STATE_KEY))
        return fig

    def show_page(self):
        ok = self.res is not None
        self.stack.setCurrentIndex(1 if ok else 0)
        self.stack.widget(0).setText(self.err or T("fluo_tau_empty"))
        self.texts.box.setVisible(ok)
        if not ok:
            STYLE.fill_summary(self.tbl_fit, [])
            STYLE.fill_summary(self.tbl_fit2, [])
            return
        cfg = self.tab.base_cfg()
        cfg.pop("extra_labels", None)                     # eigene Labels gehören zur Hauptabbildung des Tabs
        self.host.set_figure_size(*cfg["figsize_in"])
        self.draw(self.fig)
        self.canvas.draw_idle()
        self.texts.card.fill(self.text_rows)
        rows, row2 = self.fit_rows()
        for t, heads in ((self.tbl_fit, self._fit_heads), (self.tbl_fit2, self._fit2_heads)):
            t.setHorizontalHeaderLabels(heads(self.tau_unit()))
            STYLE.rich_header(t)
        STYLE.fill_summary(self.tbl_fit, rows, hidden=() if self.res["n_exp"] == 2 else (4,))
        STYLE.fill_summary(self.tbl_fit2, [row2], hidden=[i for i, v in enumerate(row2) if not v])
        self.lbl_fit.setText(self.fit_note(), plain=True)

    def fit_rows(self):
        """Je Komponente (τ, 95 %, A, Anteil an der Intensität) und eine Zeile mit Mitteln, Untergrund, χ², n."""
        r, rows, us = self.res, [], self.us()
        u = 1000 if us else 1                            # Rohwerte (CSV) in der Einheit des Kopfes
        for i, (a, t, ci) in enumerate(zip(r["A"], r["tau"], r["ci_tau"])):
            rows.append([str(i + 1), STYLE.num(fmt_tau(t, us), t / u), " … ".join(fmt_ci(ci, us)) if ci else "–",
                         STYLE.num(f"{a:.4g}".replace("-", "−"), a),
                         STYLE.num(f"{core.round_half_up(100 * r['frac'][i]):.0f}", 100 * r["frac"][i]) if r["frac"] else "–"])
        two = r["n_exp"] == 2
        row2 = [STYLE.num(fmt_tau(r["tau_amp"], us), r["tau_amp"] / u) if two and r["tau_amp"] else "",
                STYLE.num(fmt_tau(r["tau_int"], us), r["tau_int"] / u) if two and r["tau_int"] else "",
                STYLE.num(f"{r['B']:.3g}".replace("-", "−"), r["B"]),                   # Versatz in ps (ns zeigte −0.000583)
                STYLE.num(f"{r['shift'] * 1000:.3g}".replace("-", "−"), r["shift"] * 1000) if r["irf"] else "",
                STYLE.num(f"{r['chi2_red']:.2f}", r["chi2_red"]) if r["chi2_red"] is not None else "", str(r["n"])]
        return rows, row2

    def fit_note(self):
        r = self.res
        how = T("fluo_tau_note_irf") if r["irf"] else T("fluo_tau_note_tail", s=f"{r['start']:g}")
        w = T("fluo_tau_note_w") if r["weighted"] else T("fluo_tau_note_unw")
        return how + " " + w

    # -- Kennwerte ------------------------------------------------------------------------
    def props(self):
        """Eine Zeile Kennwerte (Texte, leer = nicht vorhanden) und die Kopfzeile von τ."""
        info = getattr(self.tab, "info", None) or {}
        phi = parse_phi(self.st.get("phi"))
        eps = TABS.parse_num(self.st.get("eps", ""))
        tau, kind = self.tau_used()
        kr, knr = LT.rates(phi, tau)
        row = [STYLE.num(core.fmt_lam(info["lam_abs"]), info["lam_abs"]) if info.get("lam_abs") else "",
               STYLE.num(f"{core.round_half_up(eps):.0f}", eps) if eps else "",
               STYLE.num(core.fmt_lam(info["lam_em"]), info["lam_em"]) if info.get("lam_em") else "",
               STYLE.num(f"{phi:g}", phi) if phi is not None else "",
               STYLE.num(fmt_tau(tau, self.us()), tau / (1000 if self.us() else 1)) if tau else "",
               STYLE.num(core.sci_text(kr), kr) if kr else "", STYLE.num(("0" if knr == 0 else core.sci_text(knr)), knr) if knr is not None else ""]
        head = {"amp": "τ_amp", "int": "τ_int"}.get(kind, "τ") + f" [{self.tau_unit()}]"
        return row, head, kind, phi

    def show_props(self):
        row, head, kind, phi = self.props()
        self.tbl_props.setHorizontalHeaderLabels(self._prop_heads(head))
        STYLE.rich_header(self.tbl_props)
        any_ = any(row)
        STYLE.fill_summary(self.tbl_props, [row] if any_ else [], hidden=[i for i, v in enumerate(row)
                                                                          if not v])
        notes = []
        if self.st.get("phi") and phi is None:
            notes.append(T("fluo_tau_phi_bad"))
        if kind in ("amp", "int") and row[5]:
            notes.append(T("fluo_tau_rates_" + kind))
        if self.res is not None and self.res["n_exp"] == 2 and not row[4]:
            notes.append(T("fluo_tau_neg_amp"))
        self.prop_notes = notes
        if any_:
            self.lbl_props.setText(" ".join(notes), plain=True)
            self.lbl_props.setStyleSheet(WARN_CSS if self.st.get("phi") and phi is None else HINT_CSS)
        else:
            self.lbl_props.setText("")
            self.lbl_props.setStyleSheet(HINT_CSS)

    # -- SI, Export -----------------------------------------------------------------------
    def caption(self, name):
        from elucida.si.lines import chem_html
        st, r = self.st, self.res
        model = "biexponential" if r["n_exp"] == 2 else "monoexponential"
        cond = [f"<i>λ</i><sub>ex</sub> = {st['tau_ex']:.0f} nm" if st.get("tau_ex") else "",
                f"<i>λ</i><sub>em</sub> = {st['tau_em']:.0f} nm" if st.get("tau_em") else ""]
        cond = ", ".join(c for c in cond if c)
        h = f"Fluorescence decay of <b>{html.escape(name)}</b>" + (f" ({cond})" if cond else "")
        if st.get("cap_solvent"):
            h += " in " + chem_html(st["cap_solvent"])
        if st.get("cap_conc"):
            h += f" ({chem_html(st['cap_conc'])})"
        h += f" with {model} fit ({TABS.color_name(st['c_em'])}"
        h += "; reconvolution with the instrument response function, light grey)" if r["irf"] else ")"
        h += " and " + ("weighted residuals" if r["weighted"] else "residuals") + " (bottom)."
        return h

    def si_figures(self, out_dir, name):
        if self.res is None:
            return []
        fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
        FigureCanvasAgg(fig)
        self.draw(fig)
        svg = Path(out_dir) / f"{core.safe_name(name)}_fluorescence_decay.svg"
        svg.parent.mkdir(parents=True, exist_ok=True)
        with matplotlib.rc_context({"svg.fonttype": "path"}):
            fig.savefig(svg, facecolor="white")
            fig.savefig(svg.with_suffix(".png"), dpi=600, facecolor="white", pil_kwargs={"compress_level": 1})
        w, h = fig.get_size_inches()
        sc = min(1.0, TABS.SI_MAX_W_CM / (w * 2.54))
        return [("image", str(svg.with_suffix(".png")), w * 2.54 * sc, h * 2.54 * sc, str(svg)),
                ("figcap", self.caption(name))]

    def figure(self):
        fig = MplFigure(figsize=(8, 6), dpi=TABS.PREVIEW_DPI)
        FigureCanvasAgg(fig)
        self.draw(fig)
        return fig

    def copy_figure(self, tmp):
        """Abbildung kopieren (Seite „Abklingkurve“): SVG wie im Export -> (SVG, PNG) oder None."""
        if self.res is None:
            return None
        fig, svg = self.figure(), Path(tmp) / "fluorescence_decay.svg"
        fig.savefig(svg, facecolor="white")
        fig.savefig(svg.with_suffix(".png"), dpi=300, facecolor="white")
        return svg, svg.with_suffix(".png")

    def export_to(self, base: Path):
        """<base>_decay in den Formaten des Tabs und <base>_decay.csv (Zeit, Messwert, Fit, Residuum)."""
        if self.res is None:
            return []
        fig = self.figure()
        cfg = self.tab.base_cfg()
        cfg.pop("extra_labels", None)                     # eigene Labels gehören zur Hauptabbildung des Tabs
        out = base.with_name(base.name + "_decay")
        files = []
        for e in [cfg["_main_fmt"]] + cfg["extra_formats"]:
            p = PRJ.with_ext(out, "." + e)
            fig.savefig(p, facecolor="white", dpi=300 if e == "png" else None)
            files.append(p)
        p = PRJ.with_ext(out, ".csv")
        r = self.res
        from elucida.core import tables as TBL
        fit = dict(zip(np.round(r["t"], 9), zip(r["fit"], r["resid"])))
        rows = []
        for t, y in zip(self.data["t"], self.data["y"]):
            f = fit.get(np.round(t, 9))
            rows.append([float(t), float(y)] + ([float(f[0]), float(f[1])] if f else [None, None]))
        files.append(TBL.write_csv(p, ["t [ns]", "measured", "fit", "weighted residual" if r["weighted"] else "residual"],
                                   rows))
        return files

    @TBL.marks
    def methods_text(self):
        """Englisch, nur die benutzten Schritte, dann die Ergebnisse (Größen `x` markiert, si.lines.MARK)."""
        r, st = self.res, self.st
        if r is None:
            return ""
        two = r["n_exp"] == 2
        model = ("a biexponential model, `I`(`t`) = A_1·exp(−`t`/τ_1) + A_2·exp(−`t`/τ_2) + `B`," if two
                 else "a monoexponential model, `I`(`t`) = `A`·exp(−`t`/τ) + `B`,")
        m = [f"The fluorescence decay was fitted with {model} with a constant background `B`"]
        if r["irf"]:
            m[0] += (" by iterative reconvolution with the measured instrument response function (normalized to unit "
                     "area; its temporal shift was fitted) over the whole decay.")
        else:
            m[0] += (f" to the tail of the decay, starting {r['start']:g} ns after the intensity maximum (without "
                     "deconvolution of the instrument response).")
        if r["weighted"]:
            m.append("Least squares were weighted with Poisson weights 1/max(`N`, 1) (`N`: counts per channel); the "
                     "quality of the fit is given as reduced χ² with `n` − `p` degrees of freedom.")
        else:
            m.append("The data are not photon counts; the fit was unweighted and no χ² is given.")
        m.append("95% confidence intervals of the lifetimes were obtained from the covariance matrix `s`²(`J`ᵀ`W``J`)⁻¹ "
                 "(`s`² = weighted SSR/(`n` − `p`)) and `t`(0.975; `n` − `p`).")
        if two:
            m.append("Average lifetimes are given amplitude-weighted, τ_amp = Σ(A_i·τ_i)/ΣA_i, and intensity-weighted, "
                     "τ_int = Σ(A_i·τ_i²)/Σ(A_i·τ_i) (no confidence intervals).")
        row, _, kind, phi = self.props()
        if row[5]:
            which = {"single": "the lifetime τ", "amp": "the amplitude-weighted average lifetime τ_amp",
                     "int": "the intensity-weighted average lifetime τ_int"}[kind]
            m.append(f"Radiative and non-radiative rate constants were calculated as k_r = Φ/τ and k_nr = (1 − Φ)/τ "
                     f"with the fluorescence quantum yield Φ and {which}.")
        res, us, u = [], self.us(), self.tau_unit()
        for i, (t, ci) in enumerate(zip(r["tau"], r["ci_tau"])):
            s = f"τ{f'_{i + 1}' if two else ''} = {fmt_tau(t, us)} {u}"
            if ci:
                s += " (95% interval {} to {} {}".format(*fmt_ci(ci, us), u)
                s += f"; {core.round_half_up(100 * r['frac'][i]):.0f}% of the intensity)" if two and r["frac"] else ")"
            res.append(s)
        if two and r["tau_amp"]:
            res.append(f"τ_amp = {fmt_tau(r['tau_amp'], us)} {u}, τ_int = {fmt_tau(r['tau_int'], us)} {u}")
        if r["chi2_red"] is not None:
            res.append(f"χ²_red = {r['chi2_red']:.2f} (`n` = {r['n']})")
        if row[5]:
            res.append(f"Φ = {row[3]}, k_r = {row[5]} s-1, k_nr = {row[6]} s-1")
        return " ".join(m) + "\n\n" + "; ".join(res) + "."
