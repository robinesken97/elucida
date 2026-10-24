"""
elucida/app/publication_view.py - Oberfläche der Publikation (elucida/app/publication.py): Seite mit den Verbindungen,
Angaben (README), Datenpakete aller Verbindungen, Gesamt-SI; Zeile für den Startbildschirm.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton,
                               QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication)
from PySide6.QtCore import QUrl

from elucida.app import publication as PUB
from elucida.app import style as STYLE
from elucida.app import welcome as WEL
from elucida.app.i18n import T
from elucida.app.style import HINT_CSS


def publication_info(path) -> dict | None:
    """Kurzinfo für den Startbildschirm: Titel, Ordner, Verbindungen (Namen, Vorschaubilder), zuletzt geändert."""
    pdir = PUB.is_publication(path)
    if pdir is None:
        return None
    data = PUB.load(pdir)
    dirs, _ = PUB.sync(pdir)
    thumbs = [str(WEL.thumb_path(d)) for d in dirs if WEL.thumb_path(d).exists()]
    times = [(d / "project.elucida").stat().st_mtime for d in dirs if (d / "project.elucida").exists()]
    times.append((pdir / PUB.PUB_FILE).stat().st_mtime)
    import datetime as dt
    import re
    title = re.sub(r"<[^>]+>", "", PUB.paper_title(data)) or data.get("title") or pdir.name
    return dict(path=str(pdir), folder=pdir.name, title=title,
                compounds=[PUB.compound_name(d) for d in dirs], thumbs=thumbs[:4],
                modified=dt.datetime.fromtimestamp(max(times)))


class PublicationRow(QWidget):
    """Zeile „Publikation“ auf dem Startbildschirm: bis zu vier Strukturen, Titel, Verbindungen als Abzeichen."""
    opened = Signal(str)

    def __init__(self, info):
        super().__init__()
        self.info = info
        self.setObjectName("recentRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(14)
        tile = QFrame(objectName="recentThumb")          # weiße Kachel wie bei Verbindungen (auch im dunklen Modus)
        tile.setAttribute(Qt.WA_StyledBackground, True)
        tile.setFixedSize(64, 64)
        g = QGridLayout(tile)
        g.setContentsMargins(2, 2, 2, 2)
        g.setSpacing(0)
        dpr = max(1.0, self.devicePixelRatioF())
        for k, t in enumerate(info["thumbs"]):
            lb = QLabel(alignment=Qt.AlignCenter)
            pm = QPixmap(t).scaled(int(29 * dpr), int(29 * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            lb.setPixmap(pm)
            g.addWidget(lb, k // 2, k % 2)
        if not info["thumbs"]:
            g.addWidget(QLabel(T("pub_mono"), objectName="recentMono", alignment=Qt.AlignCenter), 0, 0)
        h.addWidget(tile)
        v = QVBoxLayout()
        v.setSpacing(2)
        v.addWidget(WEL.ElidedLabel(info["title"], objectName="recentTitle"))
        sub = WEL.ElidedLabel(T("pub_n_compounds", n=len(info["compounds"])) + "  ·  " + WEL.short_path(info["path"]),
                              objectName="recentSub")
        sub.setToolTip(info["path"])
        v.addWidget(sub)
        badges = QHBoxLayout()
        badges.setSpacing(4)
        names = info["compounds"]
        for n in names[:10]:
            badges.addWidget(QLabel(n, objectName="recentBadge"))
        if len(names) > 10:
            badges.addWidget(QLabel(f"+{len(names) - 10}", objectName="recentSub"))
        badges.addStretch(1)
        v.addLayout(badges)
        h.addLayout(v, 1)
        when = QLabel(WEL.relative_time(info["modified"]), objectName="recentWhen", alignment=Qt.AlignRight | Qt.AlignTop)
        h.addWidget(when, 0, Qt.AlignTop)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.opened.emit(self.info["path"])
        super().mouseReleaseEvent(ev)

    def matches(self, text):
        t = text.strip().lower()
        return not t or any(t in s.lower() for s in [self.info["title"], self.info["path"]] + self.info["compounds"])


class _DropArea(QWidget):
    """Liste der Verbindungen: nimmt gezogene Zeilen an und meldet (Pfad, y) für die neue Position."""

    def __init__(self, on_drop):
        super().__init__()
        self.on_drop = on_drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasFormat(WEL.RecentRow.DRAG_MIME):
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasFormat(WEL.RecentRow.DRAG_MIME):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        path = bytes(ev.mimeData().data(WEL.RecentRow.DRAG_MIME)).decode("utf-8")
        ev.acceptProposedAction()
        self.on_drop(path, ev.position().toPoint().y())


class PublicationPage(QWidget):
    """Seite einer Publikation: Angaben, Verbindungen (Reihenfolge = SI und Datensatz), Exporte."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pdir = None
        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 28, 24, 20)
        col = QWidget()
        col.setMaximumWidth(920)
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        crumb = QHBoxLayout()                               # Pfad wie in der Tab-Leiste: ⌂ Übersicht ›
        b_home = QPushButton("⌂ " + T("nav_home") + "  ›", objectName="navTab")
        b_home.setToolTip(T("act_to_overview"))
        b_home.clicked.connect(main.go_home)
        crumb.addWidget(b_home)
        crumb.addStretch(1)
        v.addLayout(crumb)
        head = QHBoxLayout()
        self.lbl_title = QLabel(wordWrap=True)
        self.lbl_title.setTextFormat(Qt.RichText)
        head.addWidget(self.lbl_title, 1)
        for text, slot, icon in ((T("pub_info"), self.edit_info, "compound"), (T("pub_texts"), self.edit_texts, None),
                                 (T("recent_reveal"), self.reveal, "reveal")):
            b = QPushButton(STYLE.icon(icon), text) if icon else QPushButton(text)
            b.clicked.connect(slot)
            head.addWidget(b, 0, Qt.AlignTop)
        v.addLayout(head)
        row = QHBoxLayout()
        b_new = QPushButton(STYLE.icon("new", "#FFFFFF"), T("pub_new_compound"))
        b_new.setProperty("accent", True)
        b_new.clicked.connect(main.new_compound_in_publication)
        b_add = QPushButton(STYLE.icon("open"), T("pub_add_project"))
        b_add.setToolTip(T("pub_add_project_tip"))
        b_add.clicked.connect(self.add_project)
        row.addWidget(b_new)
        row.addWidget(b_add)
        row.addStretch(1)
        b_pack = QPushButton(STYLE.icon("export"), T("pub_datapack"))
        b_pack.setToolTip(T("pub_datapack_tip"))
        b_pack.clicked.connect(self.export_datapack)
        b_si = QPushButton(STYLE.icon("export", "#FFFFFF"), T("pub_si"))
        b_si.setProperty("accent", True)
        b_si.setToolTip(T("pub_si_tip"))
        b_si.clicked.connect(self.export_si)
        row.addWidget(b_pack)
        row.addWidget(b_si)
        self.b_pack, self.b_si = b_pack, b_si
        v.addLayout(row)
        hrow = QHBoxLayout()
        self.lbl_head = QLabel(objectName="recentHead")
        hrow.addWidget(self.lbl_head, 1)
        self.b_sort = QPushButton(T("pub_sort_name"))
        self.b_sort.setToolTip(T("pub_sort_tip"))
        self.b_sort.clicked.connect(self.sort_by_name)
        hrow.addWidget(self.b_sort)
        v.addLayout(hrow)
        self.box = QVBoxLayout()
        self.box.setContentsMargins(0, 0, 4, 0)
        self.box.setSpacing(8)
        inner = _DropArea(self._dropped)               # Verbindungen per Ziehen umsortieren
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.addLayout(self.box)
        iv.addStretch(1)
        sa = QScrollArea()
        sa.setWidget(inner)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(sa, 1)
        self.lbl_empty = QLabel(T("pub_empty"), wordWrap=True, alignment=Qt.AlignCenter)
        self.lbl_empty.setStyleSheet(HINT_CSS + " padding: 24px;")
        v.addWidget(self.lbl_empty)
        self.lbl_missing = QLabel(wordWrap=True)
        self.lbl_missing.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_missing)
        hint = QLabel(T("pub_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        outer.addStretch(1)
        outer.addWidget(col, 12)
        outer.addStretch(1)
        self.rows = []

    # -- Inhalt -----------------------------------------------------------------------
    def set_publication(self, pdir):
        self.pdir = Path(pdir) if pdir else None
        self.refresh()

    def compound_dirs(self):
        return PUB.sync(self.pdir)[0] if self.pdir else []

    def refresh(self):
        for r in self.rows:
            r.setParent(None)
            r.deleteLater()
        self.rows = []
        if self.pdir is None:
            return
        data = PUB.load(self.pdir)
        dirs, missing = PUB.sync(self.pdir)
        title = PUB.paper_title(data) or data.get("title") or self.pdir.name
        sub = " · ".join(x for x in (data.get("authors", ""), data.get("doi", "")) if x)
        self.lbl_title.setText(f"<span style='font-size:22px; font-weight:bold'>{_keep_i(title)}</span>"
                               + (f"<br><span style='color:gray'>{_esc(sub)}</span>" if sub else
                                  f"<br><span style='color:gray'>{T('pub_info_missing')}</span>"))
        complete, gaps = 0, {}
        for i, d in enumerate(dirs):
            info = WEL.project_info(d)
            if info is None:
                continue
            ck = PUB.checklist(d)
            complete += not ck["missing"]
            for k in ck["missing"]:
                gaps[k] = gaps.get(k, 0) + 1
            row = WEL.RecentRow(info, number=i + 1, extra=check_label(ck))
            row.draggable = True
            row.opened.connect(lambda p: self.main.open_project(p))
            row.setContextMenuPolicy(Qt.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, r=row: self._menu(r, pos))
            self.box.addWidget(row)
            self.rows.append(row)
        summary = T("pub_check_summary", ok=complete, n=len(self.rows))
        if gaps:
            summary += " · " + T("pub_check_gaps", gaps=", ".join(f"{PUB.check_label(k)} ({n})" for k, n in
                                                               sorted(gaps.items(), key=lambda x: [c for c, _ in
                                                                      PUB.CHECKS].index(x[0]))))
        self.lbl_head.setText(f"<b>{T('pub_compounds')}</b>  <span style='color:gray'>{len(self.rows)} · "
                              f"{_esc(summary)}</span>")
        self.lbl_empty.setVisible(not self.rows)
        self.lbl_missing.setVisible(bool(missing))
        self.lbl_missing.setText(T("pub_missing", p=", ".join(missing)))
        self.b_pack.setEnabled(bool(self.rows))
        self.b_si.setEnabled(bool(self.rows))

    def _menu(self, row, pos):
        p = row.info["path"]
        m = QMenu(self)
        m.addAction(T("act_open_project"), lambda: self.main.open_project(p))
        m.addAction(T("pub_up"), lambda: self._move(p, -1))
        m.addAction(T("pub_down"), lambda: self._move(p, 1))
        m.addAction(T("recent_reveal"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        m.addSeparator()
        m.addAction(T("move_title"), lambda: self.main.move_compound(p))
        m.addAction(T("move_copy_title"), lambda: self.main.move_compound(p, copy=True))
        m.addAction(T("pub_remove"), lambda: self._remove(p))
        m.exec(row.mapToGlobal(pos))

    def sort_by_name(self):
        PUB.sort_by_name(self.pdir)
        self.refresh()

    def _dropped(self, path, y):
        """Abgelegte Verbindung vor die erste Zeile setzen, deren Mitte unterhalb der Ablagestelle liegt."""
        idx = len(self.rows)
        for i, r in enumerate(self.rows):
            if y < r.geometry().center().y():
                idx = i
                break
        PUB.place_compound(self.pdir, path, idx)
        self.refresh()

    def _move(self, p, delta):
        PUB.move_compound(self.pdir, p, delta)
        self.refresh()

    def _remove(self, p):
        PUB.remove_compound(self.pdir, p)
        self.refresh()

    def reveal(self):
        if self.pdir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.pdir)))

    def add_project(self):
        d = QFileDialog.getExistingDirectory(self, T("pub_add_project"), str(self.pdir))
        if not d:
            return
        from elucida.app import project as PRJ
        if PRJ.is_project(d) is None:
            return self.main.error(T("no_project", p=d))
        if Path(d).resolve().parent != self.pdir.resolve():   # Zugehörigkeit = Ordner im Projekt
            box = QMessageBox(QMessageBox.Question, T("pub_add_project"), T("add_move_copy_q", p=d), parent=self)
            b_move = box.addButton(T("add_move"), QMessageBox.AcceptRole)
            b_copy = box.addButton(T("add_copy"), QMessageBox.AcceptRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() not in (b_move, b_copy):
                return
            self.main.move_compound(d, copy=box.clickedButton() is b_copy, target=self.pdir)
        else:
            PUB.add_compound(self.pdir, d)
        self.refresh()

    def edit_info(self):
        dlg = PublicationInfoDialog(self, PUB.load(self.pdir))
        if dlg.exec() == QDialog.Accepted:
            data = PUB.load(self.pdir)
            data.update(dlg.result())
            PUB.save(self.pdir, data)
            self.refresh()
            self.main.update_title()

    def edit_texts(self):
        data = PUB.load(self.pdir)
        dlg = PublicationTextsDialog(self, data.get("si_texts") or {}, self.main.settings)
        if dlg.exec() == QDialog.Accepted:
            data = PUB.load(self.pdir)
            data["si_texts"] = dlg.result()
            PUB.save(self.pdir, data)

    def export_datapack(self):
        self.main.maybe_save()
        dlg = PublicationPackDialog(self.main, self.pdir)
        dlg.exec()
        return dlg.report

    def export_si(self):
        dlg = PublicationSIDialog(self.main, self.pdir)
        if dlg.exec() == QDialog.Accepted:
            return self.main.export_publication_si(self.pdir, dlg.compounds(), dlg.sections(), toc=dlg.toc(),
                                                   methods=dlg.methods(), template=dlg.template())
        return None


OK_COLOR, MISSING_COLOR = "#3a9a4a", "#d9534f"


def check_label(ck) -> QLabel:
    """Checkliste einer Verbindung: Pflichtteile ✓/✗ (literaturbekannt: nur ¹H/¹³C), vorhandene optionale Teile grau."""
    req = PUB.REQUIRED_KNOWN if ck["known"] else PUB.REQUIRED_NEW
    parts = []
    for k, lab in PUB.CHECKS:
        if k in req:
            ok = k in ck["have"]
            parts.append(f"<span style='color:{OK_COLOR if ok else MISSING_COLOR}'>{'✓' if ok else '✗'}&nbsp;{lab}</span>")
        elif k in ck["extra"]:
            parts.append(f"<span style='color:gray'>+&nbsp;{lab}</span>")
    head = ""
    if ck["known"]:
        head = f"<i>{T('pub_check_known')}</i>" + (f" ({_esc(ck['lit'])})" if ck["lit"] else "") + " · "
    lb = QLabel(head + " &nbsp; ".join(parts), objectName="recentSub")
    lb.setTextFormat(Qt.RichText)
    lb.setWordWrap(True)
    lb.setToolTip(T("pub_check_tip"))
    return lb


def _esc(s):
    import html
    return html.escape(str(s))


def _keep_i(s):
    """Escapen, kursive Teile (<i>…</i>) des Titels erhalten."""
    return _esc(s).replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")


class PublicationInfoDialog(QDialog):
    """Angaben der Publikation (für README.txt und die Titelseite der Gesamt-SI)."""

    def __init__(self, parent, data):
        super().__init__(parent)
        self.setWindowTitle(T("pub_info"))
        self.resize(640, 680)
        v = QVBoxLayout(self)
        hint = QLabel(T("pub_info_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        f = QFormLayout()
        self.eds = {}
        for key, multi in PUB.FIELDS:
            ed = QPlainTextEdit() if multi else QLineEdit()
            if multi:
                ed.setPlainText(str(data.get(key) or ""))
                ed.setFixedHeight(90 if key in ("project_description", "dataset_description") else 56)
            else:
                ed.setText(str(data.get(key) or ""))
            ph = T("pub_ph_" + key)
            if ph != "pub_ph_" + key:
                ed.setPlaceholderText(ph)
            self.eds[key] = ed
            f.addRow(T("pub_f_" + key), ed)
        self.cmb_lic = QComboBox()
        for k, (name, *_rest) in PUB.LICENSES.items():
            self.cmb_lic.addItem(name, k)
        self.cmb_lic.setCurrentIndex(max(0, self.cmb_lic.findData(data.get("license") or "CC-BY-4.0")))
        f.addRow(T("pub_f_license"), self.cmb_lic)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def result(self):
        out = {k: (ed.toPlainText() if isinstance(ed, QPlainTextEdit) else ed.text()).strip()
               for k, ed in self.eds.items()}
        out["license"] = self.cmb_lic.currentData()
        return out


class PublicationTextsDialog(QDialog):
    """Texte der Gesamt-SI, die zur Publikation gehören: Materials and Methods und je Kapitel eine Einleitung
    (stehen unter der Kapitelüberschrift vor den Verbindungen). Absätze durch Leerzeilen; Formeln wie CH2Cl2 und
    Exponenten („cm-1“) wie in den Unterschriften."""

    def __init__(self, parent, texts, settings):
        super().__init__(parent)
        from PySide6.QtWidgets import QTabWidget
        from elucida.si import publication_si as PSI
        self.settings = settings
        self.setWindowTitle(T("pub_texts"))
        self.resize(720, 560)
        v = QVBoxLayout(self)
        hint = QLabel(T("pub_texts_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.tabs = QTabWidget()
        self.eds = {}
        for k, title, _ in PSI.SECTIONS:
            w = QWidget()
            wl = QVBoxLayout(w)
            ed = QPlainTextEdit()
            ed.setPlainText(texts.get(k, ""))
            ed.setPlaceholderText(T("pub_texts_ph_methods") if k == "methods" else T("pub_texts_ph"))
            wl.addWidget(ed)
            if k == "methods":
                b = QPushButton(T("pub_texts_setup"))
                b.setToolTip(T("pub_texts_setup_tip"))
                b.clicked.connect(lambda _=False, ed=ed: self._from_setup(ed))
                wl.addWidget(b, 0, Qt.AlignLeft)
            self.eds[k] = ed
            self.tabs.addTab(w, title)
        v.addWidget(self.tabs, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _from_setup(self, ed):
        """Aufbau-Texte der Tabs (lokal hinterlegt, si_setup/<Tab>) anhängen."""
        from elucida.si import publication_si as PSI
        parts = [str(self.settings.value(f"si_setup/{k}", "") or "").strip() for k in PSI.SETUP_KEYS]
        parts = [p for p in parts if p and p not in ed.toPlainText()]
        if parts:
            cur = ed.toPlainText().strip()
            ed.setPlainText("\n\n".join(([cur] if cur else []) + parts))

    def result(self):
        return {k: ed.toPlainText().strip() for k, ed in self.eds.items() if ed.toPlainText().strip()}


def _check_list(names, checked=True):
    lw = QListWidget()
    lw.setSelectionMode(QAbstractItemView.NoSelection)
    for n in names:
        it = QListWidgetItem(n)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        lw.addItem(it)
    return lw


def _mb(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e5 else f"{n / 1e3:.0f} kB"


class PublicationPackDialog(QDialog):
    """Datenpakete aller Verbindungen wie der Datensatz der Gruppe: <Name>.zip je Verbindung, CompChem.zip, README."""

    def __init__(self, main, pdir):
        super().__init__(main)
        from elucida.app import project as PRJ
        from elucida.app.datapack_dialog import saved_selection
        from elucida.exchange import datapack as DP
        self.main, self.pdir, self.report = main, Path(pdir), None
        self.setWindowTitle(T("pub_datapack"))
        self.resize(780, 720)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.plans = []
            for d in PUB.sync(self.pdir)[0]:
                items = DP.collect(PRJ.load(d), d)
                saved = saved_selection(main.settings, d)           # Auswahl aus dem Einzeldialog gilt weiter
                for it in items:
                    it.on = bool(saved.get(it.key, it.on if it.group != "dft" else True))
                self.plans.append(DP.Plan(PUB.compound_name(d), d, items))
            self.codes = DP.assign_codes(self.plans)
        finally:
            QApplication.restoreOverrideCursor()
        v = QVBoxLayout(self)
        hint = QLabel(T("pub_dp_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        top = QHBoxLayout()
        cv = QVBoxLayout()
        cv.addWidget(QLabel(f"<b>{T('pub_compounds')}</b>"))
        self.lst = _check_list([p.name for p in self.plans])
        self.lst.itemChanged.connect(self._update)
        cv.addWidget(self.lst)
        top.addLayout(cv, 1)
        gv = QVBoxLayout()
        gv.addWidget(QLabel(f"<b>{T('pub_dp_groups')}</b>"))
        self.cb_groups = {}
        present = {it.group for p in self.plans for it in p.items}
        for g, _, on in DP.GROUPS:
            if g not in present:
                continue
            cb = QCheckBox(T("pub_dp_dft") if g == "dft" else T("dp_grp_" + g))
            cb.setChecked(on or g == "dft")
            cb.toggled.connect(self._update)
            self.cb_groups[g] = cb
            gv.addWidget(cb)
        gv.addStretch(1)
        top.addLayout(gv, 1)
        v.addLayout(top, 2)
        v.addWidget(QLabel(f"<b>{T('dp_codes')}</b>"))
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([T("dp_code"), T("dp_code_name"), T("dp_code_text")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for code, name in self.codes.items():
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            for c, val in enumerate((code, name, f"Compound {name}")):
                self.tbl.setItem(r, c, QTableWidgetItem(val))
        v.addWidget(self.tbl, 2)
        row = QHBoxLayout()
        b = QPushButton(T("dp_code_add"))
        b.clicked.connect(lambda: self.tbl.insertRow(self.tbl.rowCount()))
        row.addWidget(b)
        self.cb_text = QCheckBox(T("dp_text"))
        self.cb_text.setToolTip(T("dp_text_tip"))
        self.cb_text.setChecked(True)
        row.addWidget(self.cb_text)
        self.cb_readme = QCheckBox(T("pub_dp_readme"))
        self.cb_readme.setChecked(True)
        row.addWidget(self.cb_readme)
        row.addStretch(1)
        v.addLayout(row)
        f = QFormLayout()
        self.ed_dir = QLineEdit(str(self.pdir / PUB.PACK_DIR))
        b_dir = QPushButton("…")
        b_dir.clicked.connect(self._choose_dir)
        dr = QHBoxLayout()
        dr.addWidget(self.ed_dir, 1)
        dr.addWidget(b_dir)
        f.addRow(T("pub_dp_dir"), dr)
        v.addLayout(f)
        self.lbl_size = QLabel("")
        v.addWidget(self.lbl_size)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = bb.addButton(T("dp_export"), QDialogButtonBox.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        bb.accepted.connect(self.export)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._update()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, T("pub_dp_dir"), self.ed_dir.text())
        if d:
            self.ed_dir.setText(d)

    def selected_plans(self):
        """Gewählte Verbindungen; Einträge abgewählter Datenarten aus."""
        from dataclasses import replace
        on_groups = {g for g, cb in self.cb_groups.items() if cb.isChecked()}
        out = []
        for i, pl in enumerate(self.plans):
            if self.lst.item(i).checkState() != Qt.Checked:
                continue
            out.append(replace(pl, items=[replace(it, on=it.on and it.group in on_groups) for it in pl.items]))
        return out

    def _update(self, *_):
        plans = self.selected_plans()
        on = [it for p in plans for it in p.items if it.on]
        self.lbl_size.setText(T("pub_dp_size", z=len(plans) + ("dft" in {i.group for i in on}), n=len(on),
                                size=_mb(sum(i.size for i in on))))
        self.btn_ok.setEnabled(bool(on))

    def replacements(self):
        names, texts = {}, {}
        for r in range(self.tbl.rowCount()):
            cell = lambda c: (self.tbl.item(r, c).text() if self.tbl.item(r, c) else "").strip()   # noqa: E731
            code = cell(0)
            if code:
                names[code] = cell(1) or code
                texts[code] = cell(2) or names[code]
        return names, texts

    def export(self, out_dir=None):
        from elucida.exchange import datapack as DP
        from elucida.app.main_window import resource_path
        out_dir = Path(out_dir or self.ed_dir.text())
        plans = self.selected_plans()
        names, texts = self.replacements()
        data = PUB.load(self.pdir)
        kinds = {it.group for p in plans for it in p.items if it.on}
        readme = PUB.readme_text(data, kinds, [p.name for p in plans]) if self.cb_readme.isChecked() else ""
        lic = PUB.license_file(data, resource_path("assets")) if self.cb_readme.isChecked() else None
        dlg = QProgressDialog(T("dp_writing"), T("cancel"), 0, 100, self)
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
        rep = self.report
        self.main.log_signal.emit(T("pub_dp_done", p=str(out_dir), z=len(rep["zips"]), n=rep["files"],
                                    size=_mb(rep["bytes"])))
        if rep["kept"]:
            self.main.log_signal.emit(T("dp_kept", files="\n  ".join(rep["kept"][:30])))
        self.accept()
        self.main.exported([out_dir])
        return rep


class PublicationSIDialog(QDialog):
    """Gesamt-SI: Kapitel und Verbindungen wählen (Aufbau wie die SI der Gruppe)."""

    def __init__(self, main, pdir):
        super().__init__(main)
        from elucida.si import publication_si as PSI
        self.main = main
        self.dirs = PUB.sync(pdir)[0]
        self.setWindowTitle(T("pub_si"))
        self.resize(560, 620)
        v = QVBoxLayout(self)
        hint = QLabel(T("pub_si_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        saved = str(main.settings.value("pub_si_sections", "") or "")
        chosen = set(saved.split(",")) if saved else {k for k, _, on in PSI.SECTIONS if on}
        h = QHBoxLayout()
        sv = QVBoxLayout()
        sv.addWidget(QLabel(f"<b>{T('pub_si_sections')}</b>"))
        self.cbs = {}
        for k, title, _ in PSI.SECTIONS:
            cb = QCheckBox(title)
            cb.setChecked(k in chosen)
            self.cbs[k] = cb
            sv.addWidget(cb)
        sv.addSpacing(8)
        from elucida.si import lines as SI
        tr = QHBoxLayout()
        tr.addWidget(QLabel(T("pub_si_template")))
        self.cmb_tpl = QComboBox()
        for k in SI.TEMPLATES:
            self.cmb_tpl.addItem(T("pub_tpl_" + k), k)
        self.cmb_tpl.setCurrentIndex(max(0, self.cmb_tpl.findData(str(main.settings.value("pub_si_template", "group")))))
        self.cmb_tpl.setToolTip(T("pub_si_template_tip"))
        tr.addWidget(self.cmb_tpl, 1)
        sv.addLayout(tr)
        self.cb_toc = QCheckBox(T("pub_si_toc"))
        self.cb_toc.setChecked(str(main.settings.value("pub_si_toc", "1")) not in ("0", "false"))
        self.cb_methods = QCheckBox(T("pub_si_methods"))
        self.cb_methods.setChecked(str(main.settings.value("pub_si_methods", "1")) not in ("0", "false"))
        sv.addWidget(self.cb_toc)
        sv.addWidget(self.cb_methods)
        sv.addStretch(1)
        h.addLayout(sv, 1)
        cv = QVBoxLayout()
        cv.addWidget(QLabel(f"<b>{T('pub_compounds')}</b>"))
        self.lst = _check_list([PUB.compound_name(d) for d in self.dirs])
        cv.addWidget(self.lst)
        h.addLayout(cv, 1)
        v.addLayout(h, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        ok = bb.addButton(T("pub_si_write"), QDialogButtonBox.AcceptRole)
        ok.setProperty("accent", True)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _accept(self):
        s = self.main.settings
        s.setValue("pub_si_sections", ",".join(self.sections()))
        s.setValue("pub_si_toc", int(self.toc()))
        s.setValue("pub_si_methods", int(self.methods()))
        s.setValue("pub_si_template", self.template())
        self.accept()

    def sections(self):
        return [k for k, cb in self.cbs.items() if cb.isChecked()]

    def compounds(self):
        return [d for i, d in enumerate(self.dirs) if self.lst.item(i).checkState() == Qt.Checked]

    def toc(self):
        return self.cb_toc.isChecked()

    def methods(self):
        return self.cb_methods.isChecked()

    def template(self):
        return self.cmb_tpl.currentData()
