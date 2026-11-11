"""Tab „Verbindung“: Bezeichnung, Angaben für die SI und Struktur der offenen Verbindung.

Früher ein Dialog mit OK/Abbrechen (Nutzerwunsch 2026-11-11: keine Popups). Im Tab gilt jede Änderung sofort: Felder beim
Verlassen, Chips beim Klick, die Zeichnung speichert sich selbst wie das Schema im Synthese-Tab; Rückgängig stellt zurück.
Der Zustand ist `main.compound` (set_compound ersetzt das Objekt, deshalb hält der Tab keine eigene Kopie)."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFontComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget)

import elucida
from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register as register_canvas
from elucida.app.i18n import T
from elucida.core import images as IMG
from elucida.tabs import base as TABS

TEXT_KEYS = ("name", "labbook", "note", "sample_no", "formula", "mp", "lit")     # Textfelder = Schlüssel der Verbindung
# Abbildungen im SI-Export je Tab (Schlüssel wie MainWindow.si_figure_choices, Reihenfolge wie die SI)
SI_FIG_KEYS = ("eps", "irms", "hrms", "overlay", "fluo", "cv", "sec", "epr", "other", "dft")


def _filled(comp):
    """Verbindung ohne leere Einträge: ein fehlender und ein leerer Wert sind dasselbe (kein Rückgängig-Schritt dafür)."""
    return {k: v for k, v in comp.items() if v not in ("", None, False)}


class CompoundTab(QWidget):
    STATE_KEY = "compound"
    STEP_LABELS = ("step_details",)
    MAIN_SI = True                      # nichts Eigenes zu exportieren: „SI (Word)“ in der Leiste ist der Hauptknopf

    def __init__(self, main, state):
        super().__init__()
        self.main = main
        self._loading = False
        self._draw = False              # „In Elucida zeichnen“ gedrückt, obwohl die Struktur eine Bilddatei ist
        left = QWidget()
        self.lv = QVBoxLayout(left)
        self.build_controls()
        self.lv.addStretch(1)
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Seite 0: Struktur als Bilddatei (oder ohne Zeichner) auf Weiß wie in Word, Seite 1: der Zeichner
        self.lbl_preview = register_canvas(QLabel(alignment=Qt.AlignCenter))
        self.lbl_hint = QLabel(TABS.guide_html("compound"))        # ohne Zeichner bzw. unter dem Bild: Kurzanleitung
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setOpenExternalLinks(True)
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.addWidget(self.lbl_preview)
        pv.addWidget(self.lbl_hint)
        pv.addStretch(1)
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(page)
        right = QWidget()
        ro = QVBoxLayout(right)                           # Seite + Fußleiste wie in allen Tabs
        ro.setContentsMargins(0, 0, 0, 0)
        ro.setSpacing(0)
        inner = QWidget()
        rl = QVBoxLayout(inner)
        rl.setContentsMargins(TABS.PAGE_INSET[0], TABS.PAGE_TOP, TABS.PAGE_INSET[2], TABS.PAGE_INSET[3])
        rl.addWidget(self.preview_stack)
        ro.addWidget(inner, 1)
        self.drawing_editor = None
        if elucida.octet_enabled() and main.project_dir:
            from elucida.app.drawing_editor import DrawingEditor
            ed = self.drawing_editor = DrawingEditor(right, scheme_actions=False)
            ed.export_directory = Path(main.project_dir) / PRJ.STRUCTURES
            self.preview_stack.addWidget(ed)
            ed.saved.connect(self._drawing_saved)
            ed.set_canvas_dark(main.canvas_is_dark())
            ed.external_requested.connect(lambda: main.edit_in_chemdraw("structure"))
            ed.status_to(lambda t: main.statusBar().showMessage(t, 8000))
        split = QSplitter(Qt.Horizontal)
        split.addWidget(TABS.footer(self, ls))
        self.btn_export.setParent(self)                   # kein eigener Export: der Knopf der Fußleiste entfällt
        self.btn_export.hide()
        right_bar = TABS.side_bar(stretch_at=0)
        ro.addWidget(right_bar)
        split.addWidget(right)
        split.setSizes([620, 800])
        TABS.fit_footer_column(self, split)
        self._footer_parts[1].hide()                      # ein Schritt, kein Export: leere Fußleisten entfallen
        right_bar.hide()
        lay = QHBoxLayout(self)                           # kein QVBoxLayout: tidy(Tab) rückt sonst alles ein
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self.sync_widgets()
        self._load_drawing()

    # -- Bedienelemente -------------------------------------------------------------------
    def _line(self, form, key, label, placeholder="", tip=""):
        ed = STYLE.ChemEdit() if key == "formula" else QLineEdit()      # Summenformel mit tiefgestellten Ziffern
        ed.setPlaceholderText(placeholder)
        ed.setToolTip(tip)
        ed.editingFinished.connect(self.apply)
        form.addRow(T(label), ed)
        self.fields[key] = ed
        return ed

    def _chip(self, form, key, label, tip):
        cb = QCheckBox(T(label))
        cb.setToolTip(T(tip))
        cb.setProperty("chip_here", True)                 # gehört zum Feld direkt darunter
        cb.toggled.connect(self.apply)
        form.addRow("", cb)
        self.checks[key] = cb
        return cb

    def build_controls(self):
        self.fields, self.checks = {}, {}
        g = QGroupBox(T("compound_grp_name"))
        f = STYLE.make_form(g)
        self._line(f, "name", "compound_name", T("compound_name_ph"))
        self._line(f, "labbook", "compound_labbook", T("compound_labbook_ph"), T("compound_labbook_tip"))
        self._line(f, "note", "compound_note", T("compound_note_ph"), T("compound_note_tip"))
        self._chip(f, "sample", "compound_sample", "compound_sample_tip")
        self._line(f, "sample_no", "compound_sample_no", T("compound_sample_ph"))
        self.lv.addWidget(g)

        g = QGroupBox(T("structure"))
        f = STYLE.make_form(g)
        self._line(f, "formula", "compound_formula", "C18H18N2O")
        self.ed_mw = QLineEdit()
        self.ed_mw.setPlaceholderText(T("compound_mw_ph"))
        self.ed_mw.editingFinished.connect(self.apply)
        f.addRow(T("molar_mass"), self.ed_mw)
        row = QHBoxLayout()
        self.lbl_struct = QLabel("–")
        self.lbl_struct.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        b = QPushButton(T("choose"))
        b.clicked.connect(self.choose)
        row.addWidget(self.lbl_struct, 1)
        row.addWidget(b)
        f.addRow(T("compound_file"), row)
        self.lbl_several = STYLE.HintLabel("")            # mehrere Moleküle gezeichnet (kein Salz): Hinweis, kein Fehler
        self.lbl_several.setWordWrap(True)
        self.lbl_several.setStyleSheet(STYLE.WARN_CSS)
        f.addRow(self.lbl_several)
        self.btn_draw = QPushButton(T("draw_open"))       # nur bei einer Bilddatei: stattdessen zeichnen
        self.btn_draw.clicked.connect(self.draw_instead)
        f.addRow(self.btn_draw)
        self.btn_chemdraw = QPushButton(T("chemdraw_edit"))    # ohne Zeichner; mit ihm steht das im Menü des Zeichners
        self.btn_chemdraw.setToolTip(T("chemdraw_edit_tip"))
        self.btn_chemdraw.clicked.connect(lambda: self.main.edit_in_chemdraw("structure"))
        self.btn_chemdraw.setVisible(not elucida.octet_enabled())
        f.addRow(self.btn_chemdraw)
        self.lv.addWidget(g)

        g = QGroupBox(T("compound_grp_si"))
        f = STYLE.make_form(g)
        row = QHBoxLayout()
        ed = self.fields["mp"] = QLineEdit()
        ed.setPlaceholderText(T("compound_mp_ph"))
        ed.editingFinished.connect(self.apply)
        cb = self.checks["oil"] = QCheckBox(T("compound_oil"))        # Öl: m.p. <25 °C
        cb.setToolTip(T("compound_oil_tip"))
        cb.toggled.connect(self.apply)
        row.addWidget(ed, 1)
        f.addRow(T("compound_mp"), row)
        cb.setProperty("chip_here", True)
        kn = self.checks["known"] = QCheckBox(T("compound_known"))         # Projekt: Checkliste nur 1H/13C
        kn.setToolTip(T("compound_known_tip"))
        kn.setProperty("chip_here", True)
        kn.toggled.connect(self.apply)
        chips = QHBoxLayout()                              # „Öl“ und „Literaturbekannt“ in einer Zeile (Nutzerwunsch)
        chips.addWidget(cb)
        chips.addWidget(kn)
        chips.addStretch(1)
        f.addRow("", chips)
        self._line(f, "lit", "compound_lit", T("compound_lit_ph"))
        self.lv.addWidget(g)
        self.lv.addWidget(self.si_export_card())

    # -- SI-Export (früher Auswahl-Dialog vor „SI (Word)“, Nutzerwunsch: keine Popups) ---------------------------------
    def si_export_card(self):
        """Teile des Word-Exports, Abbildungen je Tab und Schriftart: gemerkt in QSettings (`si_parts`, `si_figs_off`,
        `si_font`) wie bisher im Dialog; jede Änderung gilt sofort, „SI (Word)“ exportiert damit direkt."""
        from elucida.app.main_window import SI_PARTS
        g = QGroupBox(T("si_export_grp"))
        f = STYLE.make_form(g)
        self.si_parts, self.si_figs = {}, {}
        row = QHBoxLayout()
        for k in SI_PARTS:
            cb = self.si_parts[k] = QCheckBox(T("si_chip_" + k))
            cb.toggled.connect(self._si_parts_changed)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("si_export_parts"), row)
        row = QHBoxLayout()
        for k in SI_FIG_KEYS:
            cb = self.si_figs[k] = QCheckBox(T("tab_eps" if k == "eps" else self.main._tab_spec(k)[3]))
            cb.setToolTip(T("si_figs_tip"))
            cb.toggled.connect(self._si_figs_changed)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("si_export_figs"), row)
        self.cmb_si_font = QFontComboBox()
        self.cmb_si_font.setToolTip(T("si_font_tip"))
        self.cmb_si_font.currentFontChanged.connect(self._si_font_changed)
        f.addRow(T("si_font"), self.cmb_si_font)
        hint = STYLE.HintLabel(T("si_export_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)                # Hinweise grau wie überall
        f.addRow(hint)
        self._si_loading = False
        self.sync_si_export()
        return g

    def sync_si_export(self):
        """Gemerkte Auswahl -> Chips; Abbildungs-Chips nur für Tabs mit Daten (wie im früheren Dialog)."""
        self._si_loading = True
        try:
            saved, off = self.main.si_parts_saved(), self.main.si_figs_off()
            for k, cb in self.si_parts.items():
                cb.setChecked(k in saved)
            nav, keys = getattr(self.main, "nav_buttons", {}), list(getattr(self.main, "_tab_keys", []))
            for k, cb in self.si_figs.items():
                cb.setChecked(k not in off)
                cb.setEnabled("figs" in saved)
                b = nav.get(keys.index(k)) if k in keys else None
                cb.setVisible(bool(getattr(b, "has_data", False)))
            self.cmb_si_font.setCurrentFont(QFont(str(self.main.settings.value("si_font", "Arial") or "Arial")))
        finally:
            self._si_loading = False

    def _si_parts_changed(self, *_):
        if self._si_loading:
            return
        self.main.set_si_parts([k for k, cb in self.si_parts.items() if cb.isChecked()])
        for cb in self.si_figs.values():
            cb.setEnabled(self.si_parts["figs"].isChecked())

    def _si_figs_changed(self, *_):
        if self._si_loading:
            return
        off = (self.main.si_figs_off() - set(self.si_figs)) | {k for k, cb in self.si_figs.items() if not cb.isChecked()}
        self.main.settings.setValue("si_figs_off", ",".join(sorted(off)))

    def _si_font_changed(self, font):
        if self._si_loading:
            return
        from elucida.si import lines as SI
        self.main.settings.setValue("si_font", font.family())
        SI.set_font(font.family())

    def showEvent(self, ev):
        super().showEvent(ev)
        self.sync_si_export()                             # Daten in anderen Tabs können sich geändert haben

    # -- Zustand --------------------------------------------------------------------------
    def sync_widgets(self):
        """Verbindung -> Felder. Ein Feld, in dem gerade getippt wird, bleibt: die Zeichnung speichert sich nebenher."""
        c = self.main.compound
        self._loading = True
        mw = f"{c['mw']:.2f}" if c.get("mw") else ""       # Molmasse überall mit zwei Nachkommastellen
        for ed, text in [(self.fields[k], c.get(k) or "") for k in TEXT_KEYS] + [(self.ed_mw, mw)]:
            if not (ed.hasFocus() and ed.isModified()):
                ed.setText(text)
        for k, cb in self.checks.items():
            cb.setChecked(bool(c.get(k)))
        self.fields["mp"].setEnabled(not c.get("oil"))
        self.fields["lit"].setEnabled(bool(c.get("known")))
        p = c.get("structure")
        self.lbl_struct.setText(Path(p).name if p else "–")
        self.lbl_struct.setToolTip(str(p) if p else "")
        self.lbl_several.setText(self.several_molecules(p))
        self._loading = False

    @staticmethod
    def several_molecules(path):
        """Hinweis, wenn die Zeichnung mehr als ein Molekül enthält und kein Salz ist (Nutzerwunsch 2026-11-11):
        Summenformel und Molmasse gelten dann für alle zusammen. Salz = geladene Teile, die sich zu null ergänzen."""
        src = Path(path).with_suffix(".cdxml") if path else None
        if src is None or not src.exists() or not PRJ.cdxml_has_content(src):
            return ""
        try:
            from elucida.core import chem as CHEM
            c = CHEM.load_cdxml(src, render=False)
        except Exception:
            return ""
        q = c.get("charges") or []
        if c.get("n_fragments", 1) < 2 or (any(q) and sum(q) == 0):
            return ""
        return T("compound_several", n=c["n_fragments"])

    def compound_changed(self):
        self.sync_widgets()
        self._load_drawing()

    def _drawn(self, comp):
        """Was die Zeichnung der Verbindung zuletzt ergab ({} ohne auswertbare Zeichnung)."""
        p = comp.get("structure")
        return (self.main._drawn.get(str(Path(p).resolve())) if p else None) or {}

    def apply(self, *_):
        """Felder -> Verbindung. Geleerte Summenformel/Molmasse kommen wieder aus der Zeichnung; eine ungültige Molmasse
        bleibt beim alten Wert."""
        if self._loading:
            return
        from elucida.app.main_window import parse_float
        comp = dict(self.main.compound)
        for k in TEXT_KEYS:
            comp[k] = self.fields[k].text().strip()
        comp["formula"] = comp["formula"].replace(" ", "")
        for k, cb in self.checks.items():
            comp[k] = cb.isChecked()
        if not comp["known"]:
            comp["lit"] = ""
        if self.ed_mw.isModified():                       # unverändertes Feld: gespeicherten Wert nie über die Anzeige runden
            try:
                comp["mw"] = parse_float(self.ed_mw.text())
            except ValueError:
                self.main.statusBar().showMessage(T("draw_invalid_mw"), 8000)
        for k, v in self._drawn(comp).items():
            if v and not comp.get(k):
                comp[k] = v
        for ed in list(self.fields.values()) + [self.ed_mw]:
            ed.setModified(False)                         # Eingabe ist übernommen: das Feld zeigt wieder den Zustand
        if _filled(comp) != _filled(self.main.compound):
            self.main.set_compound(comp)                  # ruft compound_changed -> sync_widgets
        else:
            self.sync_widgets()

    # -- Struktur --------------------------------------------------------------------------
    def choose(self):
        p, _ = QFileDialog.getOpenFileName(self, T("dlg_structure"), self.main.settings.value("last_img_dir", ""),
                                           f"{T('flt_struct')};;{T('flt_all')}")
        if p:
            self.main.settings.setValue("last_img_dir", str(Path(p).parent))
            self.set_structure(p)

    def set_structure(self, p):
        """Andere Strukturdatei: Summenformel und Molmasse kommen wieder aus ihr, ein leerer Name aus dem Dateinamen."""
        from elucida.app.main_window import compound_from_structure
        ed = self.drawing_editor
        if ed is not None and ed.dirty and not ed.save_sync():
            return
        comp = dict(self.main.compound, structure=str(p))
        comp.update({k: v for k, v in compound_from_structure(p).items() if v})
        if not comp.get("name"):
            comp["name"] = Path(p).stem
        self._draw = False
        self.main.set_compound(comp)

    def draw_instead(self):
        self._draw = True
        self._load_drawing()

    def _preview(self):
        from elucida.app.main_window import rgba_to_pixmap
        p = self.main.compound.get("structure")
        pm = None
        if p and Path(p).exists() and (Path(p).suffix.lower() != ".cdxml" or PRJ.cdxml_has_content(p)):
            try:
                pm = rgba_to_pixmap(IMG.load_structure(p, target_px=1200)["rgba"], 360).scaled(
                    640, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pm = None
        self.lbl_preview.setVisible(pm is not None)
        if pm is not None:
            self.lbl_preview.setPixmap(pm)
            self.lbl_preview.setStyleSheet("background: #ffffff; padding: 12px;")     # wie das Schema im Synthese-Tab

    def _load_drawing(self):
        """Zeichner auf die CDXML der Verbindung (sonst die leere Vorlage); eine Bilddatei zeigt die Vorschau."""
        from elucida.app.main_window import compound_from_structure
        cur = self.main.compound.get("structure")
        image = bool(cur) and Path(cur).suffix.lower() != ".cdxml" and Path(cur).exists()
        ed = self.drawing_editor
        self.btn_draw.setVisible(ed is not None and image and not self._draw)
        if ed is None or (image and not self._draw):
            self._preview()
            self.preview_stack.setCurrentIndex(0)
            return
        path = Path(self.main.chemdraw_file("structure")).resolve()
        if ed.path != path:
            if ed.dirty and not ed.save_sync():
                return
            if not ed.open_path(path):
                return
            self.main._drawn[str(path)] = compound_from_structure(path)
        self.preview_stack.setCurrentWidget(ed)

    def _drawing_saved(self, path):
        # Eine verspätete Bestätigung der vorigen Datei darf einen Dateiwechsel nicht rückgängig machen.
        if self.drawing_editor.path != Path(path).resolve():
            return
        key = str(Path(path).resolve())
        if self.main.chemdraw_saved(key, quiet=True):
            drawn = self.main._drawn.get(key) or {}
            if not (drawn.get("formula") and drawn.get("mw")):       # z. B. Abkürzungen: vorhandene Werte bleiben
                self.main.statusBar().showMessage(T("draw_properties_unavailable"), 8000)
            return
        if PRJ.cdxml_has_content(key):
            return
        comp = dict(self.main.compound)                   # leere Zeichnung: berechnete Werte weg, eingetragene bleiben
        if comp.get("structure") and Path(comp["structure"]).resolve() == Path(key):
            for k, v in self._drawn(comp).items():
                if v and comp.get(k) == v:
                    comp[k] = "" if k == "formula" else None
            self.main._drawn[key] = {}
            if _filled(comp) != _filled(self.main.compound):
                self.main.set_compound(comp)

    def export_dialog(self):
        return self.main.export_si_dialog()

