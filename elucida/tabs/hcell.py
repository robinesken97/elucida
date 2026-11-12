"""elucida/tabs/hcell.py - H-Zelle: galvanostatisches Laden/Entladen (Gamry Cyclic Charge Discharge), Tab „H-Cell“.

Kapazität je Halbzyklus = Spalte Charge der Kapazitätstabelle (C -> mAh: /3.6); Anteil an der theoretischen Kapazität
(Kopf CAPACITY oder eingegeben); Coulomb-Effizienz = Q_Entladen / Q_Laden desselben Zyklus. Keine Glättung, keine
Fits, keine Unsicherheiten. Zweite Ansicht: Potential gegen die echte Zeit aus den Schrittdateien, Zeitachse zwischen
nicht benachbarten Zyklen unterbrochen.
"""
from __future__ import annotations

import csv
import filecmp
import re
import uuid
from pathlib import Path

import numpy as np
from matplotlib.ticker import MaxNLocator, NullLocator
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout)

from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS, make_form
from elucida.core import tddft as X
from elucida.core import uvvis as core
from elucida.formats.gamry_cycling import STEP_DIR, read_cycling, read_step, step_files, step_key
from elucida.tabs import base as TABS
from elucida.tabs import cv as CV

C_PER_MAH = 3.6
# eine Messung wie die SI der Gruppe: Laden schwarze Quadrate, Entladen rote Kreise, Effizienz blaue Dreiecke
SI_LOOK = {"charge": ("#000000", "s", None), "discharge": ("#e8231b", "o", None), "ce": ("#1764e8", "^", None)}
# mehrere Messungen (oder eigene Farbe): Farbe je Messung, Größe über das Zeichen (voll, offen, Dreieck)
OWN_LOOK = {"charge": ("o", None), "discharge": ("o", "none"), "ce": ("^", None)}
LEGEND = {"charge": "charge", "discharge": "discharge", "ce": "Coulombic efficiency"}


def cycle_rows(halves, q_theo_mAh=None):
    """Halbzyklen -> je Zyklus dict(cycle, q_ch, q_dis [mAh], pct_ch, pct_dis [%], ce [%]); fehlt eine Hälfte, bleibt
    sie None und der Zyklus hat keine Effizienz."""
    per = {}
    for h in halves:
        per.setdefault(h["cycle"], {})[h["kind"]] = h["charge_C"] / C_PER_MAH
    out = []
    for n in sorted(per):
        q_ch, q_dis = per[n].get("charge"), per[n].get("discharge")
        pct = (lambda q: 100.0 * q / q_theo_mAh if q is not None and q_theo_mAh else None)   # noqa: E731
        out.append({"cycle": n, "q_ch": q_ch, "q_dis": q_dis, "pct_ch": pct(q_ch), "pct_dis": pct(q_dis),
                    "ce": 100.0 * q_dis / q_ch if q_ch and q_dis is not None else None})
    return out


def summary(rows, halves):
    """Erste/letzte Entladekapazität, Erhalt (letzte/erste), mittlere Effizienz, Dauer [h]."""
    dis = [r for r in rows if r["q_dis"] is not None]
    ces = [r["ce"] for r in rows if r["ce"] is not None]
    first, last = (dis[0], dis[-1]) if dis else (None, None)
    return {"first": first, "last": last, "n": len(rows),
            "retention": 100.0 * last["q_dis"] / first["q_dis"] if dis and first["q_dis"] else None,
            "ce_mean": float(np.mean(ces)) if ces else None,
            "hours": max(h["end_s"] for h in halves) / 3600.0 if halves else None}


def auto_cycles(n_max):
    """Automatische Auswahl: erster, zweiter, dann gleichmäßig bis zum letzten, höchstens fünf."""
    if n_max <= 5:
        return list(range(1, n_max + 1))
    return sorted({1, 2} | {int(round(x)) for x in np.linspace(2, n_max, 4)[1:]})


def parse_cycles(text):
    """„1, 2, 50-52“ -> ([1, 2, 50, 51, 52], ungültige Teile)."""
    out, bad = [], []
    for tok in re.split(r"[,;\s]+", str(text).strip()):
        if not tok:
            continue
        m = re.fullmatch(r"(\d+)(?:[-–](\d+))?", tok)
        if not m:
            bad.append(tok)
            continue
        a, b = int(m[1]), int(m[2] or m[1])
        out += [n for n in range(min(a, b), max(a, b) + 1) if n > 0 and n not in out]
    return sorted(out), bad


def ref_axis(ref):
    """Referenz für die Achse wie CV/SEC: „Ag0/+“ -> Ag$^{0/+}$, Ziffern in Formeln tief (AgNO$_3$)."""
    ref = str(ref).strip()
    m = re.fullmatch(r"(.*?[A-Za-z)\]])([0-9]?[+−-]?/[+−-][0-9]?|[+−-]/[0-9]?)", ref)
    if m:
        return CV.axis_ref(m[1]) + "$^{" + m[2].replace("−", "-") + "}$"
    return CV.axis_ref(ref)


def _num(v):
    return f"{v:.4g}".replace("-", "−")


class HCellFigure(X.SimpleFigure):
    """SimpleFigure + zweite Skala rechts (Effizienz auf die linke Achse umgerechnet, ein Faktor) bzw. unterbrochene
    Zeitachse (Teilstriche mit der echten Zeit, Bruchzeichen in den Lücken). Punkte ohne Linien: Legende meidet nur
    die Punkte, nicht die Fläche darunter."""

    def _plot(self, sticks):
        super()._plot(sticks)
        cfg, ax = self.cfg, self.ax
        for line, c in zip(ax.get_lines(), self.curves):      # offene Zeichen (Entladen bei Farbe je Messung)
            if c.get("mfc"):
                line.set_markerfacecolor(c["mfc"])
        sc = cfg.get("scale", 1.0)
        if cfg.get("right_axis"):
            r1, label = cfg["right_axis"]
            y0, y1 = ax.get_ylim()
            ax2 = ax.twinx()
            ax2.set_ylim(y0 * r1 / y1, r1)
            ax2.set_ylabel(core.fmt_text(label, cfg), fontsize=cfg["font_size"] * 1.3)
            ax2.minorticks_on()
            ax2.tick_params(which="both", direction=cfg["tick_direction"])
            ax2.tick_params(which="major", length=6 * sc, width=max(0.6, sc))
            ax2.tick_params(which="minor", length=3 * sc, width=max(0.5, 0.8 * sc))
            ax2.spines["top"].set_visible(False)
            ax.tick_params(which="both", right=False)
            self.ax2 = ax2
        if cfg.get("xticks"):
            pos, labels = cfg["xticks"]
            ax.xaxis.set_minor_locator(NullLocator())        # Nebenstriche gälten der gestauchten Achse
            ax.set_xticks(pos)
            ax.set_xticklabels(labels, fontsize=cfg["font_size"])
        for xg in cfg.get("xbreaks") or []:                  # Bruchzeichen auf der unteren (und oberen) Achse
            tr = ax.get_xaxis_transform()
            d = 0.006 * (ax.get_xlim()[1] - ax.get_xlim()[0])
            for yb in ((0.0, 1.0) if cfg["frame"] else (0.0,)):
                ax.plot([xg - 2 * d, xg + 2 * d], [yb, yb], transform=tr, color="white", lw=3 * sc, clip_on=False,
                        zorder=6, solid_capstyle="butt")
                for s in (-1, 1):
                    ax.plot([xg + s * d - d, xg + s * d + d], [yb - 0.015, yb + 0.015], transform=tr, color="black",
                            lw=max(0.6, sc), clip_on=False, zorder=7)

    def _envelope(self, n):
        if self.cfg.get("scatter"):
            return np.full(n, -1.0)
        # Potentialkurven enden mit einem fast senkrechten Sprung zum Abbruchpotential: das Abtasten der Basisklasse
        # verfehlte ihn (Legende lag darauf). Hier zählt jede Strecke zwischen zwei Messpunkten.
        (x0, x1), (y0, y1) = self.ax.get_xlim(), self.ax.get_ylim()
        env = np.full(n, -1.0)
        for s in self.spectra:
            k = np.clip(((np.asarray(s["x"], float) - x0) / (x1 - x0) * n).astype(int), -1, n)
            y = (np.asarray(s["y"], float) - y0) / (y1 - y0)
            for a, b, ya, yb in zip(k[:-1], k[1:], y[:-1], y[1:]):
                lo, hi = max(min(a, b), 0), min(max(a, b), n - 1)
                if lo <= hi:
                    env[lo:hi + 1] = np.maximum(env[lo:hi + 1], max(ya, yb))
        env = np.clip(env, -1, 1)
        return np.maximum.reduce([env, np.roll(env, 1), np.roll(env, -1)]) + 0.02

    def _extra_blocks(self, rend):
        out = super()._extra_blocks(rend)
        if self.cfg.get("scatter"):
            (x0, x1), (y0, y1) = self.ax.get_xlim(), self.ax.get_ylim()
            for c in self.curves:
                for x, y in zip(c["x"], c["y"]):
                    out.append(((x - x0) / (x1 - x0) - 0.012, (y - y0) / (y1 - y0) - 0.02, 0.024, 0.04))
        return out


class HCellTab(TABS.FigureTab):
    STATE_KEY = "hcell"
    GUIDE, GUIDE_ACTION = "hcell", ("guide_add", "add_files")
    CAP_FIELDS = ("conc", "solvent")
    X_RANGE = (0.0, 100000.0, 0, 1.0)
    XRANGE_TEXT = "hcell_xrange"
    RESET_KEEP = ("entries", "current", "cycles", "ref")         # Messungen (mit Q_theo je Messung), gewählte Zyklen
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, x_min=1.0, x_max=100.0, ymax=0.0, entries=[], current=None,
                         view="capacity", unit="pct", show_ce=True, cycles="", ref="", cap_conc="", cap_solvent="")

    def arrange(self):
        super().arrange()
        self.to_right(self.group_titled("hcell_results"), T("tab_results"))

    def build_controls(self):
        st = self.st
        self._results, self._segs = [], []
        g = QGroupBox(T("hcell_data"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("hcell_add"), self.add_files), ("↑", lambda: self.move(-1)), ("↓", lambda: self.move(1)),
                        (T("remove"), self.remove)):
            b = STYLE.list_button(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", T("ov_name"), T("ov_color"), T("hcell_n_cycles")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(120)
        self.table.itemChanged.connect(self.table_edited)
        self.table.currentCellChanged.connect(self.select_changed)
        TABS.RowDrag(self.table, self.move_row)
        v.addWidget(self.table)
        STYLE.hide_when_empty(self.table)
        self.lv.addWidget(g)

        # Auswertung: eine Ansichtswahl oben, darunter nur die Felder der gewählten Ansicht (_view_fields)
        g = QGroupBox(T("hcell_eval"))
        f = make_form(g)
        self.cmb_view = QComboBox()
        for key in ("capacity", "potential"):
            self.cmb_view.addItem(T("hcell_view_" + key), key)
        self.cmb_view.setCurrentIndex(max(0, self.cmb_view.findData(st["view"])))
        f.addRow(T("sec_mode"), self.cmb_view)
        self.sp_qtheo = QDoubleSpinBox(decimals=3, minimum=0.0, maximum=100000.0, singleStep=0.01, suffix=" mAh",
                                       value=0.0)
        self.sp_qtheo.setSpecialValueText(T("hcell_from_file"))
        self.sp_qtheo.setToolTip(T("hcell_qtheo_tip"))
        self.cmb_unit = QComboBox()
        for key, txt in (("pct", "%"), ("mAh", "mAh")):
            self.cmb_unit.addItem(txt, key)
        self.cmb_unit.setCurrentIndex(max(0, self.cmb_unit.findData(st["unit"])))
        self.ed_cycles = QLineEdit(st["cycles"])
        self.ed_cycles.setPlaceholderText(T("hcell_cycles_ph"))
        self.ed_cycles.setToolTip(T("hcell_cycles_tip"))
        self.ed_ref = STYLE.ChemEdit(st["ref"])
        self.ed_ref.setPlaceholderText(T("hcell_ref_ph"))
        self.ed_ref.setToolTip(T("hcell_ref_tip"))
        self._rows = {}
        for key, lab, w_ in (("qtheo", "hcell_qtheo", self.sp_qtheo), ("unit", "hcell_unit", self.cmb_unit),
                             ("cycles", "hcell_cycles", self.ed_cycles), ("ref", "hcell_ref", self.ed_ref)):
            l_ = QLabel(T(lab))
            f.addRow(l_, w_)
            self._rows[key] = (l_, w_)
        self.cb_ce = QCheckBox(T("hcell_show_ce"))
        self.cb_ce.setChecked(st["show_ce"])
        f.addRow(self.cb_ce)
        self.lv.addWidget(g)

        g = QGroupBox(T("hcell_results"))
        v = QVBoxLayout(g)
        self.tbl_res = QTableWidget(0, 6)
        STYLE.empty_note(self.tbl_res, T("hcell_results_none"))
        self.tbl_res.setHorizontalHeaderLabels([T("hcell_meas"), "#", "Q_charge [mAh]", "Q_discharge [mAh]",
                                                T("hcell_pct_col"), "CE [%]"])
        self.tbl_res.horizontalHeaderItem(4).setToolTip(T("hcell_pct_tip"))
        self.tbl_res.horizontalHeaderItem(5).setToolTip(T("hcell_ce_tip"))
        self.tbl_res.verticalHeader().setVisible(False)
        self.tbl_res.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_res.setMinimumHeight(140)
        v.addWidget(self.tbl_res)
        self.lbl_res = STYLE.SciLabel("")
        self.lbl_res.setWordWrap(True)
        self.lbl_res.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.lbl_res)
        self.lv.addWidget(g)
        self.lv.addWidget(self.caption_box())

        self.cmb_view.currentIndexChanged.connect(self._view_fields)
        for w_ in (self.cmb_view, self.cmb_unit):
            w_.currentIndexChanged.connect(self.changed)
        self.sp_qtheo.valueChanged.connect(self.qtheo_changed)
        self.cb_ce.toggled.connect(self.changed)
        for ed in (self.ed_cycles, self.ed_ref):
            ed.editingFinished.connect(self.changed)
        self._view_fields()
        QTimer.singleShot(0, self._view_fields)           # noch einmal nach tidy: erst dann gibt es die Chip-Zeile
        self.fill_table()

    def _view_fields(self, *_):
        """Nur die Felder der gewählten Ansicht zeigen (auch die Zeile „Optionen“ mit dem Effizienz-Chip)."""
        cap = self.cmb_view.currentData() == "capacity"
        show = {"qtheo": cap, "unit": cap, "cycles": not cap, "ref": not cap}
        for key, (l_, w_) in self._rows.items():
            form = w_.parentWidget().layout() if w_.parentWidget() else None
            if hasattr(form, "setRowVisible") and form.indexOf(w_) >= 0:
                form.setRowVisible(w_, show[key])
            else:
                l_.setVisible(show[key])
                w_.setVisible(show[key])
        self.cb_ce.setVisible(cap)
        row = self.cb_ce.parentWidget()                   # Zeile „Optionen“ (tidy): ohne sichtbaren Chip ganz weg
        form = row.parentWidget().layout() if isinstance(row, STYLE.ChipRow) else None
        if hasattr(form, "setRowVisible") and form.indexOf(row) >= 0:
            form.setRowVisible(row, cap)                  # samt Zeilenabstand (verborgene Widgets ließen eine Lücke)
        card = self.cmb_view.parentWidget()
        if card is not None and card.layout() is not None:   # Höhe der Karte neu (Qt hielt die alte Höhe fest)
            card.layout().invalidate()
            card.updateGeometry()

    def collect(self):
        self.st.update(view=self.cmb_view.currentData(), unit=self.cmb_unit.currentData(),
                       show_ce=self.cb_ce.isChecked(), cycles=self.ed_cycles.text().strip(),
                       ref=self.ed_ref.text().strip())

    # -- Messungen ---------------------------------------------------------------------
    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("hcell_add"), self.main.settings.value("last_dir", ""),
                                             "Gamry (*.DTA *.dta);;" + T("flt_all"))
        self.load_files(ps)

    def _folder(self, p):
        """Eigener Unterordner je Messung (Hauptdatei + CHARGE_DISCHARGE/), damit die Schrittdateien zweier Messungen
        sich nicht mischen; dieselbe Hauptdatei landet wieder im selben Ordner."""
        base = f"{PRJ.data_sub(self.STATE_KEY)}/{core.safe_name(Path(p).stem)}"
        pdir = self.main.project_dir
        sub, n = base, 2
        while pdir and (Path(pdir) / sub).exists():
            t = Path(pdir) / sub / Path(p).name
            if t.is_file() and filecmp.cmp(t, p, shallow=False):
                break
            sub, n = f"{base}_{n}", n + 1
        return sub

    def load_files(self, ps):
        """Hauptdateien übernehmen (mit ihren Schrittdateien CHARGE_#n/DISCHARGE_#n); Unlesbares wird gemeldet."""
        for p in ps:
            try:
                read_cycling(p)
            except (OSError, ValueError) as ex:
                self.main.error(str(ex))
                continue
            sub = self._folder(p)
            steps = [self.main.import_file(s, f"{sub}/{STEP_DIR}") for s in step_files(p)]
            self.st["entries"].append({"uid": uuid.uuid4().hex[:8], "file": self.main.import_file(p, sub),
                                       "steps": steps, "sub": sub, "label": Path(p).stem, "visible": True,
                                       "color": None, "q_theo": 0.0})
        self.fill_table()
        self.timer.start()

    def data(self, e):
        return self.cache(("hcell", e["file"]), lambda: read_cycling(e["file"]))

    def step(self, p):
        return self.cache(("hcell_step", p), lambda: read_step(p))

    @staticmethod
    def steps_of(e):
        return {step_key(p): p for p in e.get("steps") or [] if step_key(p)}

    def move(self, d):
        self.move_row(self.table.currentRow(), self.table.currentRow() + d)

    def move_row(self, src, dst):
        if TABS.move_item(self.st["entries"], src, dst):
            self.fill_table()
            self.table.selectRow(dst)
            self.timer.start()

    def remove(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.st["entries"]):
            del self.st["entries"][r]
            self.fill_table()
            self.timer.start()

    def fill_table(self):
        self._loading = True
        es = self.st["entries"]
        self.table.setRowCount(len(es))
        for i, e in enumerate(es):
            it = QTableWidgetItem()
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            it.setCheckState(Qt.Checked if e.get("visible", True) else Qt.Unchecked)
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(e["label"]))
            self.table.setCellWidget(i, 2, TABS.color_button(self.color_of(e), lambda c, e=e: self._set_color(e, c),
                                                              cell=True))
            try:
                n = str(len({h["cycle"] for h in self.data(e)["halves"]}))
            except Exception:
                n = "–"
            it = QTableWidgetItem(n)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, it)
        self.table.resizeColumnToContents(0)
        uids = [e["uid"] for e in es]
        if es:                                            # gewählte Messung: gespeichert, sonst die erste
            self.table.setCurrentCell(uids.index(self.st["current"]) if self.st["current"] in uids else 0, 1)
        self._loading = False
        self.select_changed()

    def color_of(self, e):
        """Farbe einer Messung: eigene, sonst nach Position in der Liste (eine Messung ohne eigene Farbe zeichnet im
        Stil der SI, das Feld zeigt dann Schwarz)."""
        if e.get("color"):
            return e["color"]
        return TABS.PALETTE[self.st["entries"].index(e) % len(TABS.PALETTE)] if e in self.st["entries"] else "#000000"

    def _set_color(self, e, c):
        e["color"] = c
        self.timer.start()

    def selected(self):
        """Gewählte Messung (Zeile der Liste), sonst None."""
        r = self.table.currentRow()
        return self.st["entries"][r] if 0 <= r < len(self.st["entries"]) else None

    def select_changed(self, *_):
        """Q_theo gilt je Messung: Feld zeigt den Wert der gewählten; Potential-Ansicht und Tabelle folgen ihr."""
        e = self.selected()
        self.sp_qtheo.blockSignals(True)
        self.sp_qtheo.setValue(e.get("q_theo", 0.0) if e else 0.0)
        self.sp_qtheo.blockSignals(False)
        self.sp_qtheo.setEnabled(e is not None)
        if self._loading or e is None or e["uid"] == self.st["current"]:
            return
        self.st["current"] = e["uid"]
        self.timer.start()

    def qtheo_changed(self, v):
        e = self.selected()
        if e is not None and not self._loading:
            e["q_theo"] = float(v)
            self.timer.start()

    def table_edited(self, item):
        if self._loading:
            return
        e = self.st["entries"][item.row()]
        if item.column() == 0:
            e["visible"] = item.checkState() == Qt.Checked
        elif item.column() == 1:
            e["label"] = item.text().strip() or Path(e["file"]).stem
        self.timer.start()

    # -- Auswertung --------------------------------------------------------------------
    @staticmethod
    def q_theo(e, d):
        """-> (Q_theo [mAh] oder None, Herkunft „entered“/„file“/None) dieser Messung."""
        if (e.get("q_theo") or 0) > 0:
            return float(e["q_theo"]), "entered"
        q = d["meta"].get("capacity_mAh")
        return (q, "file") if q else (None, None)

    def evaluate(self):
        """Sichtbare, lesbare Messungen -> [(Eintrag, Daten, Zeilen, Zusammenfassung, Q_theo, Herkunft)]."""
        out = []
        for e in self.st["entries"]:
            if not e.get("visible", True):
                continue
            if not Path(e["file"]).exists():
                self.add_note(T("hcell_gone", f=Path(e["file"]).name))
                continue
            try:
                d = self.data(e)
            except (OSError, ValueError) as ex:
                self.add_note(str(ex))
                continue
            q, src = self.q_theo(e, d)
            rows = cycle_rows(d["halves"], q)
            out.append((e, d, rows, summary(rows, d["halves"]), q, src))
        return out

    def focus(self):
        """Ergebnis der gewählten Messung, sonst der ersten sichtbaren (Potential-Ansicht, Tabelle, Kacheln)."""
        res = self._results
        return next((r for r in res if r[0]["uid"] == self.st["current"]), res[0] if res else None)

    def figure_spec(self):
        self._segs = []
        res = self._results = self.evaluate()
        self.show_results()
        if not res:
            return None
        cfg = self.base_cfg()
        if self.st["view"] == "potential":
            return self.potential_spec(cfg, res)
        return self.capacity_spec(cfg, res)

    def capacity_spec(self, cfg, res):
        """Alle sichtbaren Messungen in einem Bild; Prozent je Messung mit ihrer eigenen theoretischen Kapazität."""
        st = self.st
        pct = st["unit"] == "pct" and all(r[4] for r in res)
        if st["unit"] == "pct" and not pct:
            self.add_note(T("hcell_no_qtheo"))
        many = len(res) > 1
        series = []                                         # (Messung k, Größe, Zyklen, Werte)
        for k, (_e, _d, rows, _s, _q, _src) in enumerate(res):
            for kind, key in (("charge", "q_ch"), ("discharge", "q_dis"), ("ce", "ce")):
                if kind == "ce" and not st["show_ce"]:
                    continue
                vkey = {"q_ch": "pct_ch", "q_dis": "pct_dis"}.get(key) if pct else key
                pts = [(r["cycle"], r[vkey or key]) for r in rows if r[key] is not None]
                if pts:
                    series.append((k, kind, *(np.array(v, float) for v in zip(*pts))))
        caps = [y for _, kind, _, y in series if kind != "ce"]
        ces = [y for _, kind, _, y in series if kind == "ce"]
        top = float(max((y.max() for y in caps), default=1.0))
        y1 = st["ymax"] if st["ymax"] > 0 else (max(105.0, 1.05 * top) if pct else 1.15 * top)
        r1 = max(105.0, 1.05 * max(float(y.max()) for y in ces)) if ces else None
        curves = []
        for k, kind, x, y in series:
            e = res[k][0]
            if kind == "charge" and many:                   # Block je Messung in der Legende: Name als Kopfzeile
                curves.append({"x": np.array([]), "y": np.array([]), "label": e["label"], "ls": "none",
                               "aux": True})
            if many or e.get("color"):
                col = self.color_of(e)
                marker, mfc = OWN_LOOK[kind]
            else:
                col, marker, mfc = SI_LOOK[kind]
            c = {"x": x, "y": y * y1 / r1 if kind == "ce" else y, "color": col, "label": LEGEND[kind], "ls": "none",
                 "marker": marker, "mfc": mfc, "ms": 3.5 if len(x) > 60 else 4.5}
            if kind == "ce":
                c["val"] = y
            curves.append(c)
        if r1:
            cfg["right_axis"] = (r1, "efficiency [%]")
        nmax = max((float(x.max()) for _, _, x, _ in series), default=1.0)
        cfg["xlim"] = [0.0, nmax + max(1.0, 0.03 * nmax)] if st["x_auto"] else [st["x_min"], st["x_max"]]
        cfg["ylim"] = [0.0, y1]
        cfg["xlabel"] = "cycle number"
        cfg["ylabel"] = "capacity [%]" if pct else "capacity [mAh]"
        cfg["scatter"] = cfg["legend_beside"] = True
        return cfg, curves, [], []

    def selected_cycles(self, n_max):
        if not self.st["cycles"]:
            return auto_cycles(n_max)
        sel, bad = parse_cycles(self.st["cycles"])
        if bad:
            self.add_note(T("hcell_cycles_bad", t=", ".join(bad)))
        return sel

    def potential_spec(self, cfg, res):
        st = self.st
        e, d = self.focus()[:2]
        if len(res) > 1:
            self.add_note(T("hcell_first_only", name=e["label"]))
        steps = self.steps_of(e)
        have = {h["cycle"] for h in d["halves"]} | {n for _, n in steps}
        parts = []                                          # (Zyklus, Art, t [h], E [V])
        for n in self.selected_cycles(max(have) if have else 0):
            if n not in have:
                self.add_note(T("hcell_no_cycle", n=n))
                continue
            for kind in ("charge", "discharge"):
                p = steps.get((kind, n))
                if p is None or not Path(p).exists():       # nie rekonstruieren: fehlt die Datei, fehlt die Kurve
                    self.add_note(T("hcell_step_missing", n=n, kind=T("hcell_" + kind),
                                    f=f"{kind.upper()}_#{n}.DTA"))
                    continue
                try:
                    s = self.step(p)
                except (OSError, ValueError) as ex:
                    self.add_note(str(ex))
                    continue
                parts.append((n, kind, s["t_s"] / 3600.0, s["E"]))
        if not parts:
            self.add_note(T("hcell_no_curves"))
            return None
        runs = []                                           # benachbarte Zyklen = ein Abschnitt der Zeitachse
        for n in sorted({p[0] for p in parts}):
            if runs and n == runs[-1][-1] + 1:
                runs[-1].append(n)
            else:
                runs.append([n])
        spans = [(min(p[2].min() for p in parts if p[0] in r), max(p[2].max() for p in parts if p[0] in r))
                 for r in runs]
        total = sum(t1 - t0 for t0, t1 in spans) or 1.0
        gap = 0.06 * total if len(runs) > 1 else 0.0
        x0, segs = 0.0, []
        for t0, t1 in spans:
            segs.append((x0, x0 + t1 - t0, t0))
            x0 += t1 - t0 + gap
        self._segs = segs
        seg_of = {n: segs[i] for i, r in enumerate(runs) for n in r}
        curves, labels, named, Es = [], [], set(), []
        for n, kind, t, E in parts:
            xs, xe, t0 = seg_of[n]
            curves.append({"x": t - t0 + xs, "y": E, "color": SI_LOOK[kind][0], "ls": "-", "lw": 1.3,
                           "label": kind if kind not in named else None})
            named.add(kind)
            Es.append(E)
        for n in sorted({p[0] for p in parts}):
            xs = np.concatenate([c["x"] for c, p in zip(curves, parts) if p[0] == n])
            labels.append({"key": f"label_cyc_{n}", "lam": float((xs.min() + xs.max()) / 2), "text": f"#{n}"})
        pos, texts = [], []
        for k, ((xs, xe, t0), (a, b)) in enumerate(zip(segs, spans)):
            frac = (b - a) / (total + gap * (len(segs) - 1))
            # neben einem Bruch Abstand zur Kante: sonst stoßen die Zahlen zweier Abschnitte aneinander
            lo = a + (0.15 * (b - a) if k > 0 else 0.0)
            hi = b - (0.15 * (b - a) if k < len(segs) - 1 else 0.0)
            ticks = [v for v in MaxNLocator(nbins=max(1, int(round(7 * frac))), steps=[1, 2, 2.5, 5, 10])
                     .tick_values(a, b) if lo <= v <= hi]
            if not ticks:
                ticks = [(a + b) / 2]
            step = np.diff(ticks).min() if len(ticks) > 1 else max(b - a, 1e-3)
            dec = max(0, int(-np.floor(np.log10(step) + 1e-9)))
            for v in ticks:
                pos.append(v - t0 + xs)
                texts.append(f"{v:.{dec}f}")
        cfg["xticks"] = (pos, texts)
        cfg["xbreaks"] = [segs[i][1] + gap / 2 for i in range(len(segs) - 1)]
        span = segs[-1][1] - segs[0][0] or 1.0
        cfg["xlim"] = [segs[0][0] - 0.01 * span, segs[-1][1] + 0.01 * span]
        allE = np.concatenate(Es)
        lo, hi = float(np.nanmin(allE)), float(np.nanmax(allE))
        rng = (hi - lo) or 0.1
        cfg["ylim"] = [lo - 0.08 * rng, st["ymax"] if st["ymax"] > 0 else hi + 0.2 * rng]
        cfg["xlabel"] = "t [h]"
        cfg["ylabel"] = f"E [V vs. {ref_axis(st['ref'])}]" if st["ref"] else "E [V]"
        cfg["legend_beside"] = True
        return cfg, curves, labels, []

    def build(self, fig):
        quiet = core.LOG
        core.LOG = lambda *a: None
        try:
            spec = self.figure_spec()
        finally:
            core.LOG = quiet
        if spec is None:
            return None
        cfg, curves, labels, sticks = spec
        core.setup_fonts(TABS.plt, cfg)
        return HCellFigure(TABS.plt, cfg, curves, labels, self.layout(), fig=fig, sticks=sticks)

    def hover_text(self, x, val, name):
        if self.st["view"] == "potential":
            seg = next((s for s in self._segs if s[0] - 1e-9 <= x <= s[1] + 1e-9), None)
            t = f"t = {x - seg[0] + seg[2]:.3f} h" if seg else ""
            return f"{t}    E = {val:.3f} V    {name}" if val is not None else t
        return f"#{x:.0f}    {val:.3f}    {name}" if val is not None else f"#{x:.0f}"

    # -- Ergebnisse ----------------------------------------------------------------------
    @staticmethod
    def _f(v, fmt):
        return "–" if v is None else format(v, fmt)

    def show_results(self):
        """Tabelle je Zyklus der gewählten Messung, Zusammenfassung für jede sichtbare."""
        res = self._results
        foc = self.focus()
        many = len(res) > 1
        rows = foc[2] if foc else []
        self.tbl_res.setRowCount(len(rows))
        self.tbl_res.setColumnHidden(0, not many)
        f = self._f
        for i, r in enumerate(rows):
            for j, v in enumerate((foc[0]["label"], str(r["cycle"]), f(r["q_ch"], ".3f"), f(r["q_dis"], ".3f"),
                                   f(r["pct_dis"], ".1f"), f(r["ce"], ".1f"))):
                self.tbl_res.setItem(i, j, QTableWidgetItem(v))
        lines = []
        for e, _d, _rs, s, q, src in res:
            head = f"{e['label']}: " if many else ""
            part = [T("hcell_sum_qtheo", q=f"{q:.3f}", src=T("hcell_src_" + src))] if q else []
            if s["first"] is not None:
                part.append(T("hcell_sum_dis", a=s["first"]["cycle"], qa=f"{s['first']['q_dis']:.3f}",
                              pa=f(s["first"]["pct_dis"], ".1f"), b=s["last"]["cycle"],
                              qb=f"{s['last']['q_dis']:.3f}", pb=f(s["last"]["pct_dis"], ".1f")))
            part.append(T("hcell_sum_rest", ret=f(s["retention"], ".1f"), ce=f(s["ce_mean"], ".1f"),
                          n=s["n"], h=f(s["hours"], ".1f")))
            lines.append(head + "; ".join(part))
        self.lbl_res.setText("\n".join(lines))

    def kpis(self):
        foc = self.focus()
        if foc is None:
            return []
        s = foc[3]
        return [(T("hcell_kpi_ret"), f"{s['retention']:.1f} %" if s["retention"] is not None else "–"),
                (T("hcell_kpi_ce"), f"{s['ce_mean']:.1f} %" if s["ce_mean"] is not None else "–")]

    def export_to(self, base: Path):
        """Abbildung wie die anderen Tabs, dazu die Tabelle je Zyklus als CSV (die Kurven-CSV entfällt: Effizienz auf
        die linke Achse umgerechnet bzw. gestauchte Zeitachse wären dort irreführend)."""
        files = super().export_to(base)
        data = Path(base).resolve().with_name(Path(base).name + "_data.csv")
        data.unlink(missing_ok=True)
        files = [f for f in files if f != data]
        p = Path(base).resolve().with_name(Path(base).name + "_cycles.csv")
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["measurement", "cycle", "Q_charge_mAh", "Q_discharge_mAh", "Q_charge_percent",
                        "Q_discharge_percent", "coulombic_efficiency_percent", "Q_theo_mAh", "Q_theo_source"])
            for e, _d, rows, _s, q, src in self._results:
                for r in rows:
                    w.writerow([e["label"], r["cycle"]] + ["" if r[k] is None else f"{r[k]:.6g}" for k in
                                                           ("q_ch", "q_dis", "pct_ch", "pct_dis", "ce")]
                               + [f"{q:.6g}" if q else "", src or ""])
        return files + [p]

    # -- SI ---------------------------------------------------------------------------------
    def si_caption(self, name):
        """Kapazität: „Symmetric charge–discharge H-cell cycling of **X** (c active material in Elektrolyt).“
        Potential: Abbruchpotentiale und Strom aus der Datei."""
        import html
        from elucida.si.lines import chem_html
        st = self.st
        res = self._results or self.evaluate()
        names = [r[0]["label"] for r in res] if len(res) > 1 and st["view"] != "potential" else [name]
        bs = [f"<b>{html.escape(n)}</b>" for n in names]
        b = ", ".join(bs[:-1]) + " and " + bs[-1] if len(bs) > 1 else bs[0]
        if st["view"] == "potential":
            foc = next((r for r in res if r[0]["uid"] == st["current"]), res[0] if res else None)
            m = foc[1]["meta"] if foc else {}
            h = f"Potential over time during the cycling of {b}"
            cuts = []
            if m.get("charge_cut_V") is not None:
                cuts.append(f"charge {_num(m['charge_cut_V'])} V")
            if m.get("discharge_cut_V") is not None:
                cuts.append(f"discharge {_num(m['discharge_cut_V'])} V")
            if cuts:
                h += "; cut-off potentials for " + " and ".join(cuts)
            ic, idis = m.get("charge_A"), m.get("discharge_A")
            if ic is not None and idis is not None:
                cur = (f"{_num(ic * 1000)} mA" if abs(ic - idis) < 1e-12 else
                       f"{_num(ic * 1000)} mA (charge) and {_num(idis * 1000)} mA (discharge)")
                h += f", constant-current electrolysis with {cur}"
            return h + "."
        conc, solv = st.get("cap_conc", "").strip(), st.get("cap_solvent", "").strip()
        inner = " ".join(x for x in ((chem_html(conc) + " active material") if conc else "",
                                     ("in " + chem_html(solv)) if solv else "") if x)
        return f"Symmetric charge–discharge H-cell cycling of {b}" + (f" ({inner})" if inner else "") + "."

    def methods_text(self):
        """Englisch, nur benutzte Schritte, ohne Programmnamen; danach die Ergebnisse."""
        res = self._results
        if not res:
            return ""
        how = {"file": "as set in the cycling method", "entered": "as entered"}
        qs = [(r[0]["label"], f"{r[4]:.3f} mAh, {how[r[5]]}") for r in res if r[4]]
        m = ["Charge and discharge capacities were taken for each half cycle from the charge passed during the "
             "constant-current step as recorded by the potentiostat (1 mAh = 3.6 C)."]
        if len(qs) == 1:
            m.append(f"Capacities in percent refer to the theoretical capacity Q_theo = {qs[0][1].split(', ')[0]} "
                     f"({qs[0][1].split(', ')[1]}).")
        elif qs:
            m.append("Capacities in percent refer to the theoretical capacity Q_theo of each measurement ("
                     + "; ".join(f"{n}: {t}" for n, t in qs) + ").")
        m.append("The Coulombic efficiency of each cycle was calculated as Q_discharge/Q_charge of the same cycle; "
                 "cycles with only one half cycle were excluded. No smoothing or fitting was applied.")
        if self.st["view"] == "potential":
            m.append("Potential–time curves are shown as recorded; the time axis is interrupted between "
                     "non-consecutive cycles.")
        out = []
        for e, _d, _rows, s, _q, _src in res:
            if s["first"] is None:
                continue
            pa = f" ({s['first']['pct_dis']:.1f}%)" if s["first"]["pct_dis"] is not None else ""
            pb = f" ({s['last']['pct_dis']:.1f}%)" if s["last"]["pct_dis"] is not None else ""
            t = (f"{s['n']} cycles over {s['hours']:.1f} h: discharge capacity {s['first']['q_dis']:.3f} mAh{pa} in "
                 f"cycle {s['first']['cycle']} and {s['last']['q_dis']:.3f} mAh{pb} in cycle {s['last']['cycle']} "
                 f"(retention {s['retention']:.1f}%)")
            if s["ce_mean"] is not None:
                t += f", mean Coulombic efficiency {s['ce_mean']:.1f}%"
            out.append((f"{e['label']}: " if len(res) > 1 else "") + t)
        return " ".join(m) + ("\n\n" + "; ".join(out) + "." if out else "")
