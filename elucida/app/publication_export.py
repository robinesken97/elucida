"""Reiter „Export“ der Projektseite (Entscheidung 69): „Gesamt-SI“ und „Datensätze“ als Karten statt Dialoge, gleicher
Aufbau wie im Tab „Export“ einer Verbindung (Auswahl → eigener Knopf, nicht blau → Hinweis). Die Auswahl gilt sofort und
wird wie bisher gemerkt (QSettings `pub_si_*`, `pub_dp_fid`; `publication.elucida` für Gruppen/Reaktionspfade);
„Gesamt-SI“ im Kopf der Projektseite bleibt der blaue Hauptknopf und schreibt mit dieser Auswahl."""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QProgressDialog, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from elucida.app import publication as PUB
from elucida.app import style as STYLE
from elucida.app.i18n import T


def _hint(text):
    h = STYLE.HintLabel(text)
    h.setWordWrap(True)
    h.setStyleSheet(STYLE.HINT_CSS)
    return h


def _flag(settings, key, default="1"):
    return str(settings.value(key, default)) not in ("0", "false")


class WholeSICard(QGroupBox):
    """Gesamt-SI: Vorlage, Kapitel, Optionen, Verbindungen (früher `PublicationSIDialog`)."""

    def __init__(self, page):
        super().__init__(T("pub_exp_si_grp"))
        from elucida.si import lines as SI
        from elucida.si import publication_si as PSI
        self.page, self.main, self.pdir, self._loading = page, page.main, None, True
        s = self.main.settings
        self.setFixedWidth(STYLE.INNER_W + 2 * STYLE.CARD_PAD)  # wie eine Karte der linken Spalte (Raster)
        f = STYLE.make_form(self)
        self.cmb_tpl = QComboBox()
        for i, k in enumerate(SI.TEMPLATES):              # eine Wahl, kurze Namen; Bezeichnungen im Tooltip
            self.cmb_tpl.addItem(T("pub_tpl_" + k), k)
            self.cmb_tpl.setItemData(i, T("pub_tpl_" + k + "_long"), Qt.ToolTipRole)
        self.cmb_tpl.setCurrentIndex(max(0, self.cmb_tpl.findData(str(s.value("pub_si_template", "group")))))
        self.cmb_tpl.currentIndexChanged.connect(self.save)
        self.cmb_tpl.currentIndexChanged.connect(self._tpl_tip)
        self._tpl_tip()
        f.addRow(T("pub_si_template"), self.cmb_tpl)
        saved = str(s.value("pub_si_sections", "") or "")
        chosen = set(saved.split(",")) if saved else {k for k, _, on in PSI.SECTIONS if on}
        row = QHBoxLayout()
        self.cbs = {}
        for k, title, _ in PSI.SECTIONS:
            cb = self.cbs[k] = QCheckBox(title)
            cb.setChecked(k in chosen)
            cb.toggled.connect(self.save)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("pub_si_sections"), row)
        row = QHBoxLayout()
        self.cb_toc = QCheckBox(T("pub_exp_toc"))
        self.cb_toc.setToolTip(T("pub_si_toc"))
        self.cb_toc.setChecked(_flag(s, "pub_si_toc"))
        self.cb_methods = QCheckBox(T("pub_exp_methods"))
        self.cb_methods.setToolTip(T("pub_si_methods"))
        self.cb_methods.setChecked(_flag(s, "pub_si_methods"))
        self.cb_groups = QCheckBox(T("pub_si_groups"))
        self.cb_groups.setToolTip(T("pub_si_groups_tip"))
        for cb in (self.cb_toc, self.cb_methods, self.cb_groups):
            cb.toggled.connect(self.save)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("pub_exp_options"), row)
        self.cmb_paths = QComboBox()                              # Reaktionspfade im Kapitel Rechnungen: aus/vor/nach
        for text, key in ((T("pub_exp_paths_off"), "off"), (T("rp_before_individual_calculations"), "before"),
                          (T("rp_after_individual_calculations"), "after")):
            self.cmb_paths.addItem(text, key)
        self.cmb_paths.setToolTip(T("rp_reaction_paths_in_computational_section"))
        self.cmb_paths.currentIndexChanged.connect(self.save)
        f.addRow(T("pub_exp_paths"), self.cmb_paths)
        f.addRow(_hint(T("pub_si_hint")))
        self._loading = False

    def set_publication(self, pdir):
        """Verbindungen und die Angaben des Projekts (Gruppen, Reaktionspfade) neu lesen; alle Verbindungen gewählt."""
        self._loading = True
        try:
            self.pdir = Path(pdir) if pdir else None
            self.dirs = PUB.sync(self.pdir)[0] if self.pdir else []
            data = PUB.load(self.pdir) if self.pdir else {}
            self.cb_groups.setChecked(bool(data.get("group_headings")))
            rp = data.get("reaction_paths_si") or {}
            self.cmb_paths.setCurrentIndex(self.cmb_paths.findData(
                "off" if rp.get("include") is False else rp.get("position", "before")))
            self.cmb_paths.setEnabled(self.cbs["dft"].isChecked())
        finally:
            self._loading = False

    def save(self, *_):
        """Jede Änderung gilt sofort (wie bisher beim OK des Dialogs gemerkt)."""
        if self._loading:
            return
        s = self.main.settings
        s.setValue("pub_si_sections", ",".join(self.sections()))
        s.setValue("pub_si_toc", int(self.toc()))
        s.setValue("pub_si_methods", int(self.methods()))
        s.setValue("pub_si_template", self.template())
        self.cmb_paths.setEnabled(self.cbs["dft"].isChecked())
        if self.pdir:
            data = PUB.load(self.pdir)
            data["group_headings"] = self.cb_groups.isChecked()
            p = self.cmb_paths.currentData()
            data["reaction_paths_si"] = dict(include=p != "off", position=p if p != "off" else
                                             (data.get("reaction_paths_si") or {}).get("position", "before"))
            PUB.save(self.pdir, data)

    def sections(self):
        return [k for k, cb in self.cbs.items() if cb.isChecked()]

    def compounds(self):
        """Alle Verbindungen des Projekts (Kacheln rechts; herausnehmen über die Projektseite)."""
        return list(self.dirs)

    def toc(self):
        return self.cb_toc.isChecked()

    def methods(self):
        return self.cb_methods.isChecked()

    def _tpl_tip(self, *_):
        self.cmb_tpl.setToolTip(T("pub_tpl_" + self.template() + "_long") + "\n" + T("pub_si_template_tip"))

    def template(self):
        return self.cmb_tpl.currentData()

    def export(self, *_):
        self.save()
        return self.main.export_publication_si(self.pdir, self.compounds(), self.sections(), toc=self.toc(),
                                               methods=self.methods(), template=self.template())


class DatasetsCard(QGroupBox):
    """Datensätze aller Verbindungen wie der Datensatz der Gruppe (früher `PublicationPackDialog`): <Name>.zip je
    Verbindung, CompChem.zip, README. Die Dateien werden erst beim ersten Zeigen gelesen (nicht beim Öffnen der Seite)."""

    def __init__(self, page):
        super().__init__(T("pub_exp_dp_grp"))
        from elucida.exchange import datapack as DP
        self.page, self.main, self.pdir, self.plans, self.report = page, page.main, None, None, None
        self.setFixedWidth(STYLE.INNER_W + 2 * STYLE.CARD_PAD)
        f = STYLE.make_form(self)
        row = QHBoxLayout()
        self.cb_groups = {}
        for g, _, on in DP.GROUPS:
            cb = self.cb_groups[g] = QCheckBox(T("pub_dp_dft") if g == "dft" else T("dp_grp_" + g))
            cb.setChecked(on or g == "dft")
            cb.toggled.connect(self._update)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("pub_dp_groups"), row)
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([T("dp_code"), T("dp_code_name"), T("dp_code_text")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setFixedHeight(self.tbl.horizontalHeader().sizeHint().height() + 3 * STYLE.CHECK_ROW_H + 2)
        STYLE.empty_note(self.tbl, T("pub_exp_no_codes"))
        f.addRow(T("dp_codes"), self.tbl)
        b = QPushButton(T("dp_code_add"))
        b.clicked.connect(lambda: self.tbl.insertRow(self.tbl.rowCount()))
        f.addRow("", b)
        row = QHBoxLayout()
        s = self.main.settings
        self.cb_text = QCheckBox(T("pub_exp_text"))
        self.cb_text.setToolTip(T("dp_text") + "\n" + T("dp_text_tip"))
        self.cb_text.setChecked(True)
        self.cb_readme = QCheckBox(T("pub_dp_readme"))
        self.cb_readme.setChecked(True)
        self.cb_fid = QCheckBox(T("fidpack_cb"))                # ACS: „FID for Publication“
        self.cb_fid.setToolTip(T("fidpack_cb_tip"))
        self.cb_fid.setChecked(_flag(s, "pub_dp_fid"))
        for cb in (self.cb_text, self.cb_readme, self.cb_fid):
            cb.toggled.connect(self._update)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("pub_exp_options"), row)
        dr = QHBoxLayout()
        self.ed_dir = QLineEdit()
        b_dir = QPushButton("…")
        b_dir.clicked.connect(self._choose_dir)
        dr.addWidget(self.ed_dir, 1)
        dr.addWidget(b_dir)
        f.addRow(T("pub_dp_dir"), dr)
        self.lbl_size = _hint("")
        f.addRow(self.lbl_size)
        f.addRow(_hint(T("pub_dp_hint")))

    def set_publication(self, pdir):
        self.pdir, self.plans = (Path(pdir) if pdir else None), None   # Dateien erst beim Zeigen lesen
        self.ed_dir.setText(str(self.pdir / PUB.PACK_DIR) if self.pdir else "")

    def load(self):
        """Dateien aller Verbindungen lesen (gespeicherte Auswahl je Verbindung gilt weiter), Kürzel zuordnen."""
        if self.plans is not None or not self.pdir:
            return
        from elucida.app import project as PRJ
        from elucida.app.datapack_dialog import saved_selection
        from elucida.exchange import datapack as DP
        QApplication.setOverrideCursor(Qt.WaitCursor)
        gone = []
        try:
            self.plans = []
            for d in PUB.sync(self.pdir)[0]:
                items = DP.collect(PRJ.load(d), d, gone)
                saved = saved_selection(self.main.settings, d)
                for it in items:
                    it.on = bool(saved.get(it.key, it.on if it.group != "dft" else True))
                self.plans.append(DP.Plan(PUB.compound_name(d), d, items))
            codes = DP.assign_codes(self.plans)
        finally:
            QApplication.restoreOverrideCursor()
        if gone:
            self.main.error(T("dp_missing", n=len(gone), names=", ".join(gone[:8])))
        self.tbl.setRowCount(0)
        for code, name in codes.items():
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            for c, val in enumerate((code, name, f"Compound {name}")):
                self.tbl.setItem(r, c, QTableWidgetItem(val))
        present = {it.group for p in self.plans for it in p.items}
        for g, cb in self.cb_groups.items():
            cb.setVisible(g in present)
        self.cb_fid.setVisible(any(it.group == "nmr" and it.src.is_dir() for p in self.plans for it in p.items))
        self._update()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.load()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, T("pub_dp_dir"), self.ed_dir.text())
        if d:
            self.ed_dir.setText(d)

    def selected_plans(self):
        """Gewählte Verbindungen (Pille „Zip“ der Kachel, gespeichert im Projekt: 118/120); Einträge abgewählter
        Datenarten aus. Eine abgewählte Verbindung kommt in KEINE Ausgabe (eigene Zip, CompChem, FID, README)."""
        self.load()
        on_groups = {g for g, cb in self.cb_groups.items() if cb.isChecked()}
        data = PUB.load(self.pdir) if self.pdir else None
        return [replace(pl, items=[replace(it, on=it.on and it.group in on_groups) for it in pl.items])
                for pl in self.plans or [] if data is None or PUB.pack_on(self.pdir, pl.pdir, data)]

    def _fid_on(self):
        return not self.cb_fid.isHidden() and self.cb_fid.isChecked()

    def _update(self, *_):
        if self.plans is None:
            return
        from elucida.app.publication_view import _mb
        plans = self.selected_plans()
        on = [it for p in plans for it in p.items if it.on]
        fid = [it for it in on if it.group == "nmr" and it.src.is_dir()] if self._fid_on() else []
        self.lbl_size.setText(T("pub_dp_size", z=len(plans) + ("dft" in {i.group for i in on}) + bool(fid), n=len(on),
                                size=_mb(sum(i.size for i in on) + sum(i.size for i in fid))))
        self.page.export_page.btn_dp.setEnabled(bool(on))
        self.page.export_page.sync_dp_button()

    def replacements(self):
        names, texts = {}, {}                             # Kürzel ALLER Verbindungen (auch abgewählter, 135)
        for r in range(self.tbl.rowCount()):
            cell = lambda c: (self.tbl.item(r, c).text() if self.tbl.item(r, c) else "").strip()   # noqa: E731
            code = cell(0)
            if code:
                names[code] = cell(1) or code
                texts[code] = cell(2) or names[code]
        return names, texts

    def off_names(self, names):
        """Namen abgewählter Verbindungen, wie sie in Ausgaben stehen (Zip, Ordner, README, fidpack)."""
        from elucida.exchange import datapack as DP
        return {n for pl in self.plans or [] if not PUB.pack_on(self.pdir, pl.pdir)
                for n in (pl.name, DP._safe_name(DP.replace_codes(pl.name, names)), DP._clean_name(pl.name, names))}

    def leftovers(self, out_dir, names, written):
        """Ältere Dateien im Ordner mit Inhalt abgewählter Verbindungen (eigene Zip, Ordner in CompChem/FID, README):
        nur nennen, nie löschen (135)."""
        import zipfile
        out = self.off_names(names)
        left = []
        rd = Path(out_dir) / "README.txt"
        if out and rd.is_file() and str(rd.resolve()) not in written:
            # nur die Liste „(one archive per compound: …)“ (README nur englisch); sonst träfe „1“ das Datum der
            # Datenschutzzeile oder „4“ „CC BY 4.0“
            txt = re.sub(r"\s+", " ", rd.read_text(encoding="utf-8", errors="replace"))
            m = re.search(r"\(one archive per compound: (.*?)\)(?:;| *\.|$)", txt)
            if m and set(m.group(1).split(", ")) & out:
                left.append(rd.name)
        for z in sorted(Path(out_dir).glob("*.zip")) if out else []:
            if str(z.resolve()) in written:
                continue
            try:
                with zipfile.ZipFile(z) as zf:
                    roots = {r for n in zf.namelist() for r in n.split("/")[:2]}   # CompChem/<Verbindung>/…
            except (OSError, zipfile.BadZipFile):
                roots = set()
            if z.stem in out or roots & out:
                left.append(z.name)
        return left

    def export(self, out_dir=None):
        from elucida.app.main_window import resource_path
        from elucida.app.publication_view import _fid_write, _mb
        from elucida.exchange import datapack as DP
        self.main.maybe_save()
        self.load()
        out_dir = Path(out_dir or self.ed_dir.text())
        plans = self.selected_plans()
        if not any(it.on for p in plans for it in p.items):
            return None
        names, texts = self.replacements()
        data = PUB.load(self.pdir)
        kinds = {it.group for p in plans for it in p.items if it.on}
        readme = PUB.readme_text(data, kinds, [p.name for p in plans], scrubbed=self.cb_text.isChecked()) \
            if self.cb_readme.isChecked() else ""
        lic = PUB.license_file(data, resource_path("assets")) if self.cb_readme.isChecked() else None
        dlg = QProgressDialog(T("dp_writing"), T("cancel"), 0, 100, self.main)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(400)

        def progress(root, i, n):
            dlg.setLabelText(T("pub_dp_writing", name=root))
            dlg.setMaximum(n)
            dlg.setValue(i)
            QApplication.processEvents()
            return not dlg.wasCanceled()
        try:
            self.report = DP.write_publication(plans, out_dir, names, texts if self.cb_text.isChecked() else None,
                                               compchem=True, readme=readme, license=lic, progress=progress)
        except PermissionError as e:
            self.main.error(T("report_locked", p=getattr(e, "filename", "")))
            return None
        finally:
            dlg.close()
        if self.report.get("cancelled"):
            return None
        self.main.settings.setValue("pub_dp_fid", int(self.cb_fid.isChecked()))
        fid = _fid_write(self.main, self.pdir, plans, out_dir, names, texts if self.cb_text.isChecked() else None) \
            if self._fid_on() else {}
        data = PUB.load(self.pdir)                        # älteres FID-Paket mit abgewählter Verbindung: nicht mehr
        fp = data.get("fidpack") or {}                    # im Statement nennen (135); sonst bleibt es gültig
        if "entries" in fp:                               # fester Schlüssel: auch nach Umbenennen in der Tabelle
            hit = set(fp["entries"]) & {PUB.entry_key(self.pdir, pl.pdir, data) for pl in self.plans or []
                                        if not PUB.pack_on(self.pdir, pl.pdir, data)}
        else:                                             # ältere Einträge nur mit Namen
            hit = set(fp.get("compounds") or []) & self.off_names(names)
        if not fid.get("files") and hit:
            data.pop("fidpack")
            PUB.save(self.pdir, data)
        rep = self.report
        self.main.log_signal.emit(T("pub_dp_done", p=str(out_dir), z=len(rep["zips"]), n=rep["files"],
                                    size=_mb(rep["bytes"])))
        if rep["kept"]:
            self.main.log_signal.emit(T("dp_kept", files="\n  ".join(rep["kept"][:30])))
        if rep.get("pdf_check"):
            self.main.log_signal.emit(T("dp_pdf_check", files="\n  ".join(rep["pdf_check"][:30])))
        off = [f"{pl.name}: {n}" for pl in plans if (n := sum(1 for i in pl.items if not i.on))]
        notes = [T("pub_dp_used_off", items=", ".join(off))] if off else []
        new = rep["zips"] + [fid.get("path") or ""] + ([str(Path(out_dir) / "README.txt")] if readme else [])
        left = self.leftovers(out_dir, names, {str(Path(p_).resolve()) for p_ in new})
        if left:
            notes.append(T("pub_dp_leftover", files=", ".join(left)))
        self.main.exported([out_dir], [], notes,
                           [(T("pub_exp_change"), self.page.show_export)])
        return rep


SLOTS = (("nmr", "nmr"), ("ir", "irms"), ("ms", "hrms"), ("uvvis", "eps"), ("uvkin", "uvkin"), ("fluo", "fluo"),
         ("cv", "cv"), ("sec", "sec"), ("hcell", "hcell"), ("epr", "epr"), ("xray", "xray"), ("dft", "dft"))
# Plätze des Farbstreifens der Projektkacheln (Entscheidung 100): Abzeichen (welcome.BADGES) -> Farbe der Datenart,
# feste Reihenfolge der Spalten der Verbindungsmatrix


class _WholeOrNone(QLabel):
    """Zähltext in der Fußleiste: ganz oder gar nicht (nie „Gesa…“, steht auch über den Kacheln), ganz im Tooltip;
    gibt nie eine Mindestbreite vor (verborgene Seite im Stapel, ui.md)."""

    def __init__(self):
        super().__init__(objectName="recentSub")
        self._full = ""
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def set_full(self, text):
        self._full = text
        self.setToolTip(text)
        self._sync()

    def _sync(self):
        QLabel.setText(self, self._full if self.fontMetrics().horizontalAdvance(self._full) <= self.width() else "")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._sync()


class PublicationExportPage(QWidget):
    """Reiter „Export“ der Projektseite (Entscheidungen 96–97): links „Gesamt-SI“ und „Datensätze“, rechts dasselbe
    Kachelraster wie Verbindung › Export – Kopfzeilen der Gruppen, je Verbindung eine Kachel (Strukturbild, Nummer +
    Summenformel, Kürzel der vorhandenen Daten, Zahl der Abbildungen in der SI); Klick öffnet ihren Export-Tab. Unten
    „Datensätze“ (grau) und „Gesamt-SI (Word)“ (blau). Liest nur Projektdateien, öffnet keine Verbindung."""

    def __init__(self, page):
        super().__init__()
        from elucida.app.publication_view import IN, scrolled
        from elucida.app.tiles import TileGrid
        from elucida.tabs import base as TABS
        self.page, self.main, self.pdir = page, page.main, None
        self.si_card, self.dp_card = WholeSICard(page), DatasetsCard(page)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.si_card)
        lv.addWidget(self.dp_card)
        lv.addStretch(1)
        STYLE.tidy(left)
        ls = scrolled(left)
        ls.setFixedWidth(STYLE.INNER_W + 2 * STYLE.CARD_PAD + 20)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(STYLE.ROW_GAP)
        top = QHBoxLayout()
        hint = STYLE.HintLabel(T("pub_exp_tiles_hint"))
        hint.setStyleSheet(STYLE.HINT_CSS)
        hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hint.setProperty("plaintext", True)
        hint.setWordWrap(True)                                    # macht das Fenster nie breiter
        from elucida.app.tiles import EDGE, Legend
        top.setContentsMargins(EDGE, 0, 0, 0)                    # dieselbe linke Kante wie Karten und Kopfzeilen
        top.addWidget(hint, 1)
        self.lbl_zip = QLabel(T("pub_exp_zip_links"), objectName="tileGroupLinks")   # ohne Gruppen: für alle
        self.lbl_zip.setTextFormat(Qt.RichText)
        self.lbl_zip.linkActivated.connect(lambda h: self.set_pack([t.path for t in self.grid.tiles], h == "all"))
        top.addWidget(self.lbl_zip)
        self.lbl_n = QLabel(objectName="recentSub")
        top.addWidget(self.lbl_n)
        rv.addLayout(top)
        self.legend = Legend([(T("slot_" + b), k) for b, k in SLOTS])
        # Legende in einer Zeile darf die Mindestbreite nicht vorgeben (verborgene Seite zählt im Stapel mit: Fenster
        # unter Windows sonst breiter als 1440 px); bei schmalem Fenster wird sie rechts abgeschnitten
        from PySide6.QtWidgets import QSizePolicy
        self.legend.setSizePolicy(QSizePolicy.Ignored, self.legend.sizePolicy().verticalPolicy())
        rv.addWidget(self.legend)
        self.grid = TileGrid()
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.addWidget(self.grid)
        iv.addStretch(1)
        rv.addWidget(scrolled(inner), 1)
        self.lbl_count = _WholeOrNone()                           # eine Zeile, ganz oder gar nicht (steht auch oben):
                                                                  # verborgene Seite macht das Fenster nie breiter (ui.md)
        self.btn_dp = QPushButton(T("pub_exp_dp_btn"))
        self.btn_dp.setToolTip(T("pub_datapack_tip"))
        self.btn_dp.clicked.connect(lambda: self.dp_card.export())
        self.btn_si = QPushButton(STYLE.icon("export", "#FFFFFF"), T("pub_si"))
        self.btn_si.setProperty("accent", True)                  # Hauptknopf dieser Ansicht
        self.btn_si.setToolTip(T("pub_si_tip"))
        self.btn_si.clicked.connect(lambda: self.si_card.export())
        bar = TABS.side_bar(self.lbl_count, self.btn_dp, self.btn_si)
        bar.layout().setStretchFactor(self.lbl_count, 1)         # Text nimmt den freien Platz, Knöpfe rechts
        bar.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(bar)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(IN, 12, IN, 0)
        lay.setSpacing(STYLE.COL_PAD)
        lay.addWidget(ls)
        lay.addWidget(right, 1)

    def set_publication(self, pdir):
        self.pdir = Path(pdir) if pdir else None
        self.si_card.set_publication(pdir)
        self.dp_card.set_publication(pdir)
        self.fill()

    def tiles(self):
        return list(self.grid.tiles)

    def fill(self):
        """Kacheln aus den Projektdateien (welcome.project_info, gespeicherte SI-Auswahl); baut und öffnet nichts."""
        from elucida.app import project as PRJ
        from elucida.app import welcome as WEL
        from elucida.app.tiles import Tile
        from elucida.si import lines as SI
        from elucida.tabs.compound import SI_FIG_KEYS
        rows, n = [], 0
        if self.pdir is not None:
            data = PUB.load(self.pdir)
            groups = PUB.grouped(self.pdir)
            named = any(g for g, _ in groups)
            for g, dirs in groups:
                tiles = []
                for d in dirs:
                    info = WEL.project_info(d)
                    if info is None:
                        continue
                    have = set(info["badges"])                # Farbstreifen: feste Plätze (Entscheidung 100)
                    slots = [(T("slot_" + b), k, b in have) for b, k in SLOTS]
                    try:
                        st = PRJ.load(d)
                    except Exception:
                        st = {}
                    ex = st.get("export") or {}               # wie beim Öffnen: ohne eigene Auswahl die frühere (B2)
                    off = set(ex["si_off"]) if "si_off" in ex else self.main.legacy_si_off()
                    keys = {WEL.TAB_OF.get(b) for b in info["badges"]} & set(SI_FIG_KEYS)
                    name = f"<b>{html_escape(info['name'])}</b>"
                    if info.get("formula"):                   # Summenformel tiefgestellt wie überall
                        name += f" <span style='font-size:10px'>{SI.chem_name_html(info['formula'])}</span>"
                    present = ", ".join(lab for lab, _, on in slots if on) or "–"
                    t = Tile(None, name, str(len(keys - off)), rich_name=True, slots=slots,
                             tip=T("pub_exp_tile_tip", name=info["name"]) + "\n" + present,
                             zip_pill=(lambda d=d: PUB.pack_on(self.pdir, d, data), lambda on, d=d: self.set_pack([d], on)))
                    t.zip.setToolTip(T("pub_exp_zip_tip"))
                    t.pill.setToolTip(T("pub_exp_count_tip"))
                    from elucida.app.tiles import tile_pixmap      # Strukturbild der Übersicht (.elucida/thumb.png)
                    t.set_thumb(tile_pixmap(info["thumb"], t.pic, structure=True) if info.get("thumb") else None, "molecule", "syn")
                    t.path = d
                    t.clicked.connect(lambda t_, _e, d=d: self.open_compound(d))
                    tiles.append(t)
                n += len(tiles)
                if tiles:                                 # leere Gruppen ohne Kopfzeile; rechts „Zip: Alle · Keine“
                    head = (f"{g} · {len(tiles)}" if g else T("pub_exp_no_group"))
                    rows.append(((head, T("pub_exp_zip_links"), lambda h, ds=tuple(t.path for t in tiles):
                                  self.set_pack(ds, h == "all")) if named else None, tiles))
        self.grid.set_rows(rows)
        for t in self.grid.tiles:
            self._dim(t)
        self.lbl_zip.setVisible(bool(rows) and rows[0][0] is None)   # Gruppen haben ihre eigenen Verweise
        self.sync_dp_button()
        self.lbl_n.setText(T("pub_exp_n", n=n))
        self.lbl_count.set_full(T("pub_exp_count", n=n))
        self.btn_si.setEnabled(bool(n))

    def set_pack(self, dirs, on):
        """Pille „Zip“ / „Zip: Alle · Keine“: Verbindungen in den Datensatz (gespeichert im Projekt, 120)."""
        if self.pdir is None:
            return
        PUB.set_pack_on(self.pdir, dirs, on)
        ds = {Path(d).resolve() for d in dirs}
        for t in self.grid.tiles:
            if Path(t.path).resolve() in ds and t.zip is not None:
                t.zip.blockSignals(True)
                t.zip.setChecked(on)
                t.zip.blockSignals(False)
                self._dim(t)
        self.dp_card._update()
        self.sync_dp_button()

    def _dim(self, t):
        """Abgewählte Kachel gedimmt (die Pille bleibt lesbar zum Wiedereinschalten)."""
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        off = t.zip is not None and not t.zip.isChecked()
        for w_ in (t.name, t.pic, t.findChild(QLabel, "tileCount")):
            ef = w_.graphicsEffect() if w_ is not None else None
            if w_ is None or (ef is not None and not isinstance(ef, QGraphicsOpacityEffect)):
                continue                                  # dunkler Canvas: dessen Effekt bleibt
            if off:
                e_ = QGraphicsOpacityEffect(w_)
                e_.setOpacity(0.35)
                w_.setGraphicsEffect(e_)
            else:
                w_.setGraphicsEffect(None)

    def sync_dp_button(self):
        """Knopf „Datensätze (n von m)“, sobald eine Verbindung abgewählt ist."""
        tiles = [t for t in self.grid.tiles if t.zip is not None]
        on = sum(1 for t in tiles if t.zip.isChecked())
        self.btn_dp.setText(T("pub_exp_dp_btn") if on == len(tiles) else T("pub_exp_dp_btn_n", n=on, m=len(tiles)))
        if tiles and not on:                              # „0 von m“: nichts zu schreiben
            self.btn_dp.setEnabled(False)
        elif self.dp_card.plans is None:                  # Dateien noch nicht gelesen: _update prüft beim Laden
            self.btn_dp.setEnabled(True)

    def open_compound(self, d):
        """Klick auf eine Kachel: Verbindung öffnen und ihren Export-Tab zeigen."""
        if self.main.open_project(d, recent=False):
            self.main.show_tab("export")


def html_escape(text):
    import html
    return html.escape(str(text))
