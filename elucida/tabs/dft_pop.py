"""elucida/tabs/dft_pop.py - DFT-Tab, Reiter „Ladungen“: atomare Ladungen und Spinpopulationen aus der Rechnung.

Leser `formats.calc.parse_populations` (nur geprüfte Layouts: ORCA Mulliken/Löwdin, Gaussian Mulliken). Tabelle Atom +
je vorhandenem Schema eine Spalte (Spinpopulation nur, wo gedruckt), keine leeren Spalten; dieselben Zahlen (3
Nachkommastellen) in App, Zwischenablage und SI, die CSV behält die gedruckten Werte. In die SI nur auf Wunsch je
Rechnung (`pop_si`, Chip wie „Multireferenz“), weil ORCA Mulliken und Löwdin immer druckt und lange Tabellen die SI füllen.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QGroupBox, QStackedWidget, QVBoxLayout

from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.formats.calc import POP_SCHEMES, parse_populations, read_text

SCHEME_NAME = {"mulliken": "Mulliken", "loewdin": "Löwdin"}       # Ausgabe (englisch, wie in der SI üblich)


def _fmt(v):
    t = f"{v:.3f}"
    return ("0.000" if float(t) == 0 else t).replace("-", "−")


def columns(pop):
    """[(Schema, Art „charge“/„spin“, Kopf)] in fester Reihenfolge, nur vorhandene Werte."""
    out = []
    for k in POP_SCHEMES:
        if k in pop:
            out.append((k, "charge", f"{SCHEME_NAME[k]} charge"))
            if pop[k].get("spin") is not None:
                out.append((k, "spin", f"{SCHEME_NAME[k]} spin population"))
    return out


def table(tab, e):
    """-> (Kopf, Zeilen als Text, Zeilen als Zahlen) der Rechnung eines Eintrags; ([], [], []) ohne Werte. Reihenfolge
    und Labels wie die Nummerierung im Tab; passt die Atomzahl nicht zur Geometrie, nichts (nie falsch zuordnen)."""
    p = (e or {}).get("file")
    g = tab.geometry(e) if p and tab.calc_of(e) is not None else None
    if g is None:
        return [], [], []
    pop = tab.cache(("pop", p), lambda: parse_populations(read_text(p)))
    els = g[1]
    pop = {k: v for k, v in pop.items() if v["els"] == list(els)}
    cols = columns(pop)
    if not cols:
        return [], [], []
    from elucida.tabs.dft import number_of
    order = tab.order(e, len(els))
    num = number_of(order, tab.base())
    rows_t, rows_v = [], []
    for k in order:
        vals = [pop[s][kind][k] for s, kind, _ in cols]
        lab = tab.label_text(els[k], num[k], k, e)
        rows_t.append([lab] + [_fmt(v) for v in vals])
        rows_v.append([lab] + vals)
    return ["Atom"] + [h for *_, h in cols], rows_t, rows_v


def caption(head):
    """„Mulliken and Löwdin atomic charges and spin populations of“ aus den Spalten."""
    names = list(dict.fromkeys(h.split(" ")[0] for h in head[1:]))
    what = "atomic charges and spin populations" if any("spin" in h for h in head) else "atomic charges"
    return f"{' and '.join(names)} {what} of"


def si_blocks(tab):
    """Word: je Rechnung mit `pop_si` eine Tabelle (einspaltig, nach der Energietabelle)."""
    out = []
    for e in tab.entries():
        if not e.get("pop_si"):
            continue
        head, rows, _ = table(tab, e)
        if rows:
            from elucida.tabs import xray as XRAY
            name = e.get("name") or Path(e["file"]).stem
            out += [("tabcap", caption(head), name),
                    ("params", head, [[XRAY.esc_markup(c) for c in r] for r in rows], {"fit": True})]
    return [("columns", 1)] + out if out else []


def write_csv(tab, path):
    """Alle Rechnungen mit Werten in einer CSV (Name, Atom, Schemata; gedruckte Werte). -> Pfad oder None."""
    data = [(e.get("name") or Path(e["file"]).stem, table(tab, e)) for e in tab.entries()]
    data = [(n, t) for n, t in data if t[1]]
    if not data:
        return None
    heads = list(dict.fromkeys(h for _, (head, _, _) in data for h in head[1:]))
    from elucida.core import tables as TBL
    rows = []
    for n, (head, _, vals) in data:
        for r in vals:                                   # ORCA und Gaussian drucken Ladungen mit 6 Nachkommastellen
            d = dict(zip(head[1:], r[1:]))              # (repr ergab „1e-05“ und kürzte „-0.120000“)
            rows.append([n, r[0]] + [f"{d[h]:.6f}" if h in d else "" for h in heads])
    TBL.write_csv(path, ["Calculation", "Atom"] + heads, rows)
    return Path(path)


class PopulationPage(QGroupBox):
    """Ergebnisseite „Ladungen“ der gewählten Rechnung: Tabelle über `STYLE.FitGrid`, Chip „In die SI“, Kopieren."""

    def __init__(self, tab):
        super().__init__(T("dft_pop_tab"))
        self.tab, self.loading = tab, False
        v = QVBoxLayout(self)
        self.si = QCheckBox(T("dft_pop_si"))
        self.si.setProperty("chip", True)
        self.si.setToolTip(T("dft_pop_si_tip"))
        self.si.toggled.connect(self.changed)
        from PySide6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()                                  # Chip in natürlicher Breite (nicht über die ganze Karte)
        row.addWidget(self.si)
        row.addStretch(1)
        v.addLayout(row)
        self.grid = STYLE.name_table(STYLE.FitGrid(0, 1), "charges", "Atomic charges")   # Rohwerte: _charges.csv
        self.grid.verticalHeader().setVisible(False)
        from PySide6.QtWidgets import QAbstractItemView
        self.grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.none = STYLE.SciLabel("", T("dft_pop_none"))
        self.none.setWordWrap(True)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.none)
        self.stack.addWidget(self.grid)
        v.addWidget(self.stack, 1)
        self.note = STYLE.SciLabel("")
        self.note.setWordWrap(True)
        v.addWidget(self.note)
        self.btn_copy = STYLE.copy_button(T("dft_pop_copy_tip"))
        self.btn_copy.setProperty("tablecopy", True)
        self.btn_copy.clicked.connect(self.copy)
        STYLE.card_actions(self, self.btn_copy)

    def sync(self):
        from PySide6.QtWidgets import QTableWidgetItem
        self.loading = True
        try:
            e = self.tab.entry() or {}
            head, rows, _ = table(self.tab, e) if e else ([], [], [])
            self.si.setChecked(bool(e.get("pop_si")))
            self.si.setEnabled(bool(rows))
            self.grid.setColumnCount(len(head) or 1)
            self.grid.setHorizontalHeaderLabels(self.display_head(head) or [""])
            self.grid.setRowCount(len(rows))
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    self.grid.setItem(i, j, QTableWidgetItem(c))
            self.grid.fit()
            self.stack.setCurrentIndex(1 if rows else 0)
            self.btn_copy.setEnabled(bool(rows))
            self.note.setText(T("dft_pop_note") if rows else "", plain=True)
        finally:
            self.loading = False

    @staticmethod
    def display_head(head):
        """Kopf in der Sprache der Oberfläche (SI, Kopieren und CSV bleiben englisch)."""
        out = [T("dft_pop_atom")] if head else []
        for h in head[1:]:
            name = h.split(" ")[0]
            out.append(T("dft_pop_h_spin" if "spin" in h else "dft_pop_h_charge", s=name))
        return out

    def changed(self, *_):
        e = self.tab.entry()
        if self.loading or not e:
            return
        e["pop_si"] = self.si.isChecked()
        self.tab.main.push_undo()

    def copy(self):
        e = self.tab.entry() or {}
        head, rows, _ = table(self.tab, e)
        if not rows:
            return
        STYLE.copy_tables([self.grid])                  # Word (HTML, U+2212) und Excel (TSV, ASCII-Minus) zugleich
        self.tab.main.statusBar().showMessage(T("dft_pop_copied"), 4000)
