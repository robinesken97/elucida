"""Explicit MR result selection, shared by preview and SI."""
import html
import re
from decimal import Decimal
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel, QTextBrowser, QFormLayout,
                               QStackedWidget)
from elucida.app.i18n import T
from elucida.app import style as STYLE
from elucida.formats.multireference import report_lines, result_label, spin_gap


def selected_result(calc, entry):
    return next((r for r in calc.get("multireference", []) if r["id"] == entry.get("mr_result")), None)


def si_extra(calc, entry):
    r = selected_result(calc, entry)
    if not entry.get("mr_si") or r is None:
        return []
    lines = [re.sub(r"(?<!\w)-(?=\d)", "−", t) for t in display_lines(r, entry)]
    return [(t, html.escape(t)) for t in lines]


def _kcal_text(kcal):
    text = f"{kcal:.1f}"
    return "0.0" if float(text) == 0 else text.replace("-", "−")


def display_lines(r, entry):
    lines = report_lines(r)
    try:
        s, t = entry["mr_singlet"], entry["mr_triplet"]
        if not isinstance(s, int) or not isinstance(t, int) or min(s, t) < 0:
            return lines
        sign = entry.get("mr_gap_sign", "S-T")
        gap = spin_gap(r, s, t, sign)
        formula = "E(S) − E(T)" if sign == "S-T" else "E(T) − E(S)"
        kcal = gap * Decimal("627.5094740631")
        sval, tval = r["states"][s], r["states"][t]
        lines += [f"Same-geometry electronic gap ΔE_ST = {formula} = {_kcal_text(kcal)} kcal mol−1 "
                  f"(calculated from printed energies; S root {sval['root']} {sval.get('irrep', '')}; "
                  f"T root {tval['root']} {tval.get('irrep', '')})."]
    except (KeyError, IndexError, ValueError):
        pass
    return lines


class MultireferencePage(QGroupBox):
    def __init__(self, tab):
        super().__init__(tab)
        self.tab, self.loading = tab, False
        # Seite wie die übrigen Ergebnisseiten (Sichtung 2026-11-11): keine Karte in der Karte, Felder im Raster der Tabs
        # (Beschriftung gedämpft, Felder gleich breit), „in SI“ als Chip statt Kästchen
        v = QVBoxLayout(self); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)
        form = STYLE.make_form()
        form.setVerticalSpacing(STYLE.ROW_GAP); form.setHorizontalSpacing(STYLE.FORM_GAP)
        self.choice = QComboBox()
        self.si = QCheckBox(T('rp_include_selected_result_in_si'))
        self.si.setProperty("chip", True)
        self.singlet, self.triplet, self.sign = QComboBox(), QComboBox(), QComboBox()
        self.sign.addItem("ΔE_ST = E(S) − E(T)", "S-T")
        self.sign.addItem("ΔE_ST = E(T) − E(S)", "T-S")
        self.sign.setToolTip(T('rp_gap_convention'))
        for w in (self.singlet, self.triplet, self.sign):
            w.currentIndexChanged.connect(self.changed)

        def label(text):
            lb = QLabel(text)
            lb.setProperty("formlabel", True)
            lb.setFixedWidth(STYLE.LABEL_W)
            return lb
        for text, w in ((T('mr_result'), self.choice), ("", self.si), (T('mr_singlet'), self.singlet),
                        (T('mr_triplet'), self.triplet), (T('mr_sign'), self.sign)):
            if isinstance(w, QComboBox):
                w.setFixedSize(STYLE.VALUE_W, STYLE.CONTROL_H)
            form.addRow(label(text), w)
        v.addLayout(form)
        hint = QLabel(T('rp_select_a_method_and_result_block_explicitly_energies_and_weights_retai'))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)
        v.addWidget(hint)
        STYLE.sci_widgets(self)                              # ΔE_ST in der Auswahlliste wie im Satz
        self.text = QTextBrowser()
        # ohne gewähltes Ergebnis: Platzhalter groß in der Mitte statt eines leeren Textfelds (wie die anderen Seiten)
        self.none = STYLE.SciLabel("", T('rp_no_multireference_result_selected_supported_orca_6_casscf_sc_nevpt2_an'))
        self.none.setWordWrap(True)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.none)
        self.stack.addWidget(self.text)
        v.addWidget(self.stack, 1)
        self.choice.currentIndexChanged.connect(self.changed)
        self.si.toggled.connect(self.changed)

    def sync(self):
        self.loading = True
        e = self.tab.entry() or {}
        c = self.tab.calc_of(e) if e else None
        self.choice.clear()
        self.choice.addItem(T('rp_select_result'), None)
        for r in (c or {}).get("multireference", []):
            self.choice.addItem(result_label(r), r["id"])
        self.choice.setCurrentIndex(max(0, self.choice.findData(e.get("mr_result"))))
        self.si.setChecked(bool(e.get("mr_si")))
        r = selected_result(c or {}, e)
        for combo, mult, key in ((self.singlet, 1, "mr_singlet"), (self.triplet, 3, "mr_triplet")):
            combo.clear()
            combo.addItem(T('rp_select_singlet') if mult == 1 else
                          T('rp_select_triplet'), None)
            for j, s in enumerate((r or {}).get("states", [])):
                if s["multiplicity"] == mult:
                    combo.addItem(f"root {s['root']} {s.get('irrep', '')} · {s['energy']} Eh", j)
            combo.setCurrentIndex(max(0, combo.findData(e.get(key))))
        self.sign.setCurrentIndex(max(0, self.sign.findData(e.get("mr_gap_sign", "S-T"))))
        self.si.setEnabled(r is not None)
        self.text.setPlainText("\n\n".join(display_lines(r, e)) if r else "")
        self.stack.setCurrentIndex(1 if r else 0)
        self.loading = False

    def changed(self, *_):
        e = self.tab.entry()
        if self.loading or not e:
            return
        changed_result = e.get("mr_result") != self.choice.currentData()
        e.update(mr_result=self.choice.currentData(), mr_si=self.si.isChecked(), mr_gap_sign=self.sign.currentData(),
                 mr_singlet=None if changed_result else self.singlet.currentData(),
                 mr_triplet=None if changed_result else self.triplet.currentData())
        self.sync()
        self.tab.update_si()
        self.tab.main.push_undo()
