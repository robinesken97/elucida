"""
elucida/app/publication_view.py - Oberfläche der Publikation (elucida/app/publication.py): Seite mit den Verbindungen,
Angaben (README), Datenpakete aller Verbindungen, Gesamt-SI; Zeile für den Startbildschirm.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar,
                               QProgressDialog, QPushButton, QSizePolicy,
                               QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication,
                               QTabWidget, QStackedWidget)
from PySide6.QtCore import QUrl

from elucida.app.canvas_theme import register as register_canvas
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
                complete=sum(1 for d in dirs if not PUB.checklist(d)["missing"]),      # vollständig laut Checkliste
                modified=dt.datetime.fromtimestamp(max(times)))


def open_mnova(parent, paths):
    """„In Mnova öffnen“: mit dem Standardprogramm des Systems; mehrere -> Auswahl, keins/keine Zuordnung -> Hinweis."""
    from PySide6.QtWidgets import QInputDialog
    paths = [Path(p) for p in paths if Path(p).exists()]
    if not paths:
        return QMessageBox.information(parent, "Mnova", T("mnova_none"))
    p = paths[0]
    if len(paths) > 1:
        name, ok = QInputDialog.getItem(parent, "Mnova", T("mnova_pick"), [x.name for x in paths], 0, False)
        if not ok:
            return None
        p = next(x for x in paths if x.name == name)
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(p))):
        QMessageBox.warning(parent, "Mnova", T("mnova_noapp", name=p.name))
    return p


class PublicationTile(WEL.SideRow):
    """Projekt in der Seitenleiste: Fortschritt laut Checkliste als Ring, Titel, vollständig/alle."""
    opened = Signal(str)

    def __init__(self, info):
        n, k = len(info["compounds"]), info.get("complete", 0)
        super().__init__(info["title"], f"{k}/{n}", lead=WEL.Ring(k, n))
        self.info = info
        self.setToolTip(info["title"] + "\n" + T("pub_tile_progress", n=n, k=k))
        self.clicked.connect(lambda: self.opened.emit(self.info["path"]))

    def matches(self, text):
        t = text.strip().lower()
        return not t or any(t in s.lower() for s in [self.info["title"], self.info["path"]] + self.info["compounds"])


class PathCard(WEL.ClickCard):
    """Reaktionspfad als Karte: Vorschau des Profils, Name, Stand."""

    def __init__(self, item, preview):
        super().__init__()
        self._setup(dict(path=item["uid"]))
        self.item = item
        self.setFixedHeight(190)
        self.setMinimumWidth(WEL.CARD_W)
        v = QVBoxLayout(self)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)
        v.addWidget(WEL.card_picture(str(preview) if preview.exists() else None, 128))
        b = QVBoxLayout()
        b.setContentsMargins(12, 9, 12, 10)
        b.setSpacing(2)
        b.addWidget(WEL.EndElided(item["name"], objectName="cardName"))
        if preview.exists():
            import datetime as dt
            t = dt.datetime.fromtimestamp(preview.stat().st_mtime)
            b.addWidget(QLabel(T("rp_changed", t=WEL.relative_time(t)), objectName="recentSub"))
        b.addStretch(1)
        v.addLayout(b, 1)


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
            register_canvas(lb)
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


class GroupHeader(QWidget):
    """Überschrift einer Gruppe auf der Projektseite (Name, Anzahl, vollständig); Rechtsklick: umbenennen, verschieben,
    auflösen. Auch Ziel beim Ziehen (alles unterhalb gehört zur Gruppe)."""

    def __init__(self, group, n):
        super().__init__()
        self.group = group
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 10, 4, 2)                   # bündig mit „Verbindungen“ und den Zeilen
        self.lbl = QLabel(objectName="recentHead")
        h.addWidget(self.lbl, 1)
        self.set_count(n, 0)

    def set_count(self, n, done):
        name = _esc(self.group) if self.group is not None else T("group_none")
        self.lbl.setText(f"<b>{name}</b>&nbsp;&nbsp;&nbsp;<span style='color:gray'>{n}"
                         + (f" · {T('pub_check_summary', ok=done, n=n)}" if n else "") + "</span>")


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


def scrolled(widget):
    sa = QScrollArea()
    sa.setWidget(widget)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return sa


def add_card(title, hint, height):
    """Gestrichelte Karte „Neu …“ am Ende einer Galerie."""
    b = QPushButton(objectName="addCard")
    v = QVBoxLayout(b)
    v.setContentsMargins(16, 12, 16, 12)
    v.setSpacing(4)
    v.addStretch(1)
    pic = QLabel(alignment=Qt.AlignCenter)
    pic.setPixmap(STYLE.pixmap("add", 22, STYLE.colors()["text2"]))
    v.addWidget(pic)
    v.addWidget(QLabel(f"<b>{title}</b>", alignment=Qt.AlignCenter))
    lab = QLabel(hint, objectName="recentSub", alignment=Qt.AlignCenter, wordWrap=True)
    v.addWidget(lab)
    v.addStretch(1)
    for x in (pic, lab, b.findChildren(QLabel)[1]):
        x.setAttribute(Qt.WA_TransparentForMouseEvents)
    b.setFixedHeight(height)
    b.setMinimumWidth(WEL.CARD_W)
    b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    b.setCursor(Qt.PointingHandCursor)
    return b


class PublicationPage(QWidget):
    """Seite einer Publikation: Angaben, Verbindungen (Reihenfolge = SI und Datensatz), Exporte."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pdir = None
        self.path_workspace = None
        layout = QVBoxLayout(self)
        self.outer = layout
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(18)
        # Kopf: Titel, Autoren, Fortschritt; rechts die beiden Exporte (nur der wichtigste blau)
        self.head = QWidget()
        hd = QHBoxLayout(self.head)
        hd.setContentsMargins(0, 0, 0, 0)
        hd.setSpacing(24)
        tv = QVBoxLayout()
        tv.setSpacing(4)
        self.lbl_title = QLabel(wordWrap=True, objectName="pageTitle")
        self.lbl_title.setTextFormat(Qt.RichText)
        tv.addWidget(self.lbl_title)
        self.lbl_sub = QLabel(wordWrap=True, objectName="pageSub")
        tv.addWidget(self.lbl_sub)
        pr = QHBoxLayout()
        pr.setSpacing(10)
        self.bar_progress = QProgressBar(objectName="pubProgress", textVisible=False)
        self.bar_progress.setFixedSize(220, 6)
        pr.addWidget(self.bar_progress)
        self.lbl_progress = QLabel(objectName="recentSub")
        pr.addWidget(self.lbl_progress)
        pr.addStretch(1)
        tv.addSpacing(8)
        tv.addLayout(pr)
        hd.addLayout(tv, 1)
        b_pack = QPushButton(STYLE.icon("export"), T("pub_datapack"), objectName="barBtn")
        b_pack.setToolTip(T("pub_datapack_tip"))
        b_pack.clicked.connect(self.export_datapack)
        b_si = QPushButton(STYLE.icon("export", "#FFFFFF"), T("pub_si"), objectName="barBtn")
        b_si.setProperty("accent", True)
        b_si.setToolTip(T("pub_si_tip"))
        b_si.clicked.connect(self.export_si)
        hd.addWidget(b_pack, 0, Qt.AlignTop)
        hd.addWidget(b_si, 0, Qt.AlignTop)
        self.b_pack, self.b_si = b_pack, b_si
        layout.addWidget(self.head)
        self.project_tabs = QTabWidget()
        self.project_tabs.setDocumentMode(True)
        layout.addWidget(self.project_tabs, 1)
        corner = QWidget()
        cr = QHBoxLayout(corner)
        cr.setContentsMargins(0, 0, 0, 6)
        cr.setSpacing(2)
        for text, slot in ((T("pub_texts"), self.edit_texts),
                           (T("pub_procs"), lambda *_: edit_procedures(self, self.pdir)), (T("recent_reveal"), self.reveal)):
            b = QPushButton(text, objectName="ghost")
            b.clicked.connect(slot)
            cr.addWidget(b)
        self.project_tabs.setCornerWidget(corner, Qt.TopRightCorner)
        STYLE.center_corner(self.project_tabs)
        overview = QWidget()
        self.project_tabs.addTab(overview, T('pub_compounds'))
        v = QVBoxLayout(overview)
        v.setContentsMargins(0, 12, 0, 0)
        v.setSpacing(8)
        from elucida.app.reaction_paths import PathPanel
        self.paths_page = QWidget()
        self.project_tabs.addTab(self.paths_page, T('rp_computational_chemistry'))
        self.info_page = PublicationInfoPage(self)          # Angaben (früher Dialog): dritte Seite
        self.project_tabs.addTab(self.info_page, T("pub_details_tab"))
        paths_layout = QHBoxLayout(self.paths_page)
        paths_layout.setContentsMargins(0, 12, 0, 0)
        from elucida.app.cluster import ClusterCard, ClusterPage
        self.path_panel = PathPanel(self)
        self.path_rail = QWidget()
        self.path_rail.setMaximumWidth(285)
        rail = QVBoxLayout(self.path_rail)
        rail.setContentsMargins(STYLE.COL_PAD, 0, 0, STYLE.COL_PAD)   # nur bei offenem Pfad sichtbar: dort ohne Seitenrand
        rail.addWidget(self.path_panel, 1)
        self.path_rail.hide()                               # nur bei offenem Pfad über ☰; sonst Karten
        self.path_stack = QStackedWidget()
        self.path_landing = QWidget()
        ln = QHBoxLayout(self.path_landing)
        ln.setContentsMargins(0, 0, 0, 0)
        ln.setSpacing(24)
        lv = QVBoxLayout()
        lv.setSpacing(8)
        lh = QHBoxLayout()
        lh.addWidget(QLabel(f"<b>{T('rp_reaction_paths')}</b>", objectName="recentHead"))
        lh.addStretch(1)
        self.b_restore = QPushButton(STYLE.icon("reset"), T("rp_restore"), objectName="ghost")
        self.b_restore.setMenu(QMenu(self.b_restore))
        lh.addWidget(self.b_restore)
        lv.addLayout(lh)
        self.path_gallery = WEL.Gallery()
        self.path_cards = []
        self.b_new_path = add_card(T("rp_new_path"), T("rp_energy_profiles_and_irc_across_multiple_compounds"), 190)
        self.b_new_path.clicked.connect(self.path_panel.new)
        top = QWidget()                                     # Karten oben, nicht mittig in der Höhe
        tv2 = QVBoxLayout(top)
        tv2.setContentsMargins(0, 0, 0, 0)
        tv2.addWidget(self.path_gallery)
        tv2.addStretch(1)
        lv.addWidget(scrolled(top), 1)
        ln.addLayout(lv, 1)
        self.cluster_page = ClusterPage(self)
        self.cluster_page.setFixedWidth(360)
        ln.addWidget(self.cluster_page)
        self.path_stack.addWidget(self.path_landing)
        self.cluster_card = ClusterCard(self)
        rail.addWidget(self.cluster_card)
        paths_layout.addWidget(self.path_rail)
        paths_layout.addWidget(self.path_stack, 1)
        hrow = QHBoxLayout()
        hrow.setSpacing(6)
        self.lbl_head = QLabel(objectName="recentHead")
        # Lange Zusammenfassung ("fehlt: …") darf abgeschnitten werden, sonst bestimmt sie die Mindestbreite des Fensters
        self.lbl_head.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        hrow.addWidget(self.lbl_head, 1)
        self.ed_filter = QLineEdit()                        # Eingabe kommt aus der Suche der Werkzeugleiste
        self.ed_filter.hide()
        self.ed_filter.textChanged.connect(self._filter)
        for text, tip, slot in ((T("pub_sort_name"), T("pub_sort_tip"), self.sort_by_name),
                                (T("group_new") + " …", T("group_tip"), self.new_group)):
            b = QPushButton(text, objectName="ghost", toolTip=tip)
            b.clicked.connect(slot)
            hrow.addWidget(b)
        b_add = QPushButton(STYLE.icon("open"), T("pub_add_project"))
        b_add.setToolTip(T("pub_add_project_tip"))
        b_add.clicked.connect(self.add_project)
        hrow.addWidget(b_add)
        b_new = QPushButton(STYLE.icon("new"), T("pub_new_compound"))
        b_new.clicked.connect(lambda: main.new_compound_in_publication())
        hrow.addWidget(b_new)
        v.addLayout(hrow)
        self.box = QVBoxLayout()
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(6)
        inner = self.drop_area = _DropArea(self._dropped)   # Verbindungen per Ziehen umsortieren
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.addLayout(self.box)
        iv.addStretch(1)
        v.addWidget(scrolled(inner), 1)
        self.lbl_empty = QLabel(T("pub_empty"), wordWrap=True, alignment=Qt.AlignCenter)
        self.lbl_empty.setStyleSheet(HINT_CSS + " padding: 24px;")
        v.addWidget(self.lbl_empty)
        self.lbl_missing = QLabel(wordWrap=True)
        self.lbl_missing.setStyleSheet(HINT_CSS)
        v.addWidget(self.lbl_missing)
        hint = QLabel(T("pub_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        hint.setAlignment(Qt.AlignHCenter)                  # Hinweise mittig wie in den Tabs (Nutzerwunsch)
        v.addWidget(hint)
        self.rows = []
        self.project_tabs.currentChanged.connect(main._update_undo_actions)

    # -- Inhalt -----------------------------------------------------------------------
    def set_publication(self, pdir):
        if self.pdir != (Path(pdir) if pdir else None) and not self.close_path(): return False
        self.pdir = Path(pdir) if pdir else None
        self.refresh()
        return True

    def save_paths(self):
        return not self.path_workspace or self.path_workspace.save()

    def close_path(self):
        workspace = self.path_workspace
        if not workspace: return True
        if not workspace.save(): return False
        workspace.dispose()
        self.path_stack.removeWidget(workspace)
        workspace.deleteLater()
        self.path_workspace = None
        self.path_rail.hide()
        self.path_stack.setCurrentIndex(0)
        self._set_full(False)
        self.cluster_page.btn_back.hide()
        self.path_panel.refresh()
        self._fill_paths(PUB.load(self.pdir))
        self.main._update_undo_actions()
        return True

    def _set_full(self, on):
        """Offener Pfad: Kopf und Ränder weg, die Höhe gehört dem Canvas."""
        self.head.setVisible(not on)
        self.project_tabs.tabBar().setVisible(not on)
        if self.project_tabs.cornerWidget(Qt.TopRightCorner) is not None:
            self.project_tabs.cornerWidget(Qt.TopRightCorner).setVisible(not on)
        self.outer.setContentsMargins(*((0, 0, 0, 0) if on else (28, 24, 28, 16)))   # Pfad: Ränder wie in den Tabs (PathWorkspace)
        self.main._update_crumbs()

    def open_path(self, item):
        from elucida.app.reaction_paths import PathWorkspace
        if self.path_workspace and self.path_workspace.item['uid'] == item['uid']:
            self.project_tabs.setCurrentWidget(self.paths_page)
            self.path_stack.setCurrentWidget(self.path_workspace)
            return
        if not self.close_path(): return
        workspace = PathWorkspace(self.main, self.pdir, item)
        self.path_workspace = workspace
        workspace.closed.connect(self.close_path)
        self.path_stack.addWidget(workspace)
        self.path_stack.setCurrentWidget(workspace)
        self.path_rail.hide()                               # offener Pfad: volle Breite, ☰ blendet die Liste wieder ein
        self._set_full(True)
        self.project_tabs.setCurrentWidget(self.paths_page)
        for i in range(self.path_panel.list.count()):
            row = self.path_panel.list.item(i)
            if row.data(Qt.UserRole)['uid'] == item['uid']: self.path_panel.list.setCurrentItem(row)
        self.main._update_undo_actions()

    def show_cluster(self):
        self.path_stack.setCurrentWidget(self.path_landing)

    def compound_dirs(self):
        return PUB.sync(self.pdir)[0] if self.pdir else []

    def refresh(self):
        for r in self.rows + [h for h, _ in getattr(self, "headers", [])] + [p for p, _ in getattr(self, "panels", [])]:
            r.setParent(None)
            r.deleteLater()
        self.rows, self.headers, self.panels = [], [], []
        if self.pdir is None:
            return
        data = PUB.load(self.pdir)
        self.path_panel.refresh()
        self._fill_paths(data)
        dirs, missing = PUB.sync(self.pdir)
        title = PUB.paper_title(data) or data.get("title") or self.pdir.name
        sub = " · ".join(x for x in (data.get("authors", ""), data.get("doi", "")) if x)
        self.lbl_title.setText(_keep_i(title))
        self.lbl_sub.setText(sub or T("pub_info_missing"))
        self.info_page.load(data)
        complete, gaps = 0, {}
        groups = PUB.grouped(self.pdir)
        with_heads = any(g is not None for g, _ in groups)   # Überschriften nur, wenn es Gruppen gibt
        num = 0
        for g, ds in groups:
            head = None
            if with_heads:
                head = GroupHeader(g, len(ds))
                head.setContextMenuPolicy(Qt.CustomContextMenu)
                head.customContextMenuRequested.connect(lambda pos, h=head: self._group_menu(h, pos))
                self.box.addWidget(head)
                self.headers.append((head, g))
            done_g = 0
            panel = QFrame(objectName="matrixPanel")          # je Gruppe eine Tabelle mit eigener Kopfzeile
            pv = QVBoxLayout(panel)
            pv.setContentsMargins(1, 1, 1, 1)
            pv.setSpacing(0)
            pv.addWidget(WEL.MatrixHeader(numbered=True))
            self.box.addWidget(panel)
            self.panels.append((panel, g))
            for d in ds:
                info = WEL.project_info(d)
                if info is None:
                    continue
                if g:
                    info["group"] = g
                ck = PUB.checklist(d)
                complete += not ck["missing"]
                done_g += not ck["missing"]
                for k in ck["missing"]:
                    gaps[k] = gaps.get(k, 0) + 1
                num += 1
                row = WEL.RecentRow(info, number=num)
                row.draggable = True
                row.group = g
                row.opened.connect(lambda p: self.main.open_project(p))
                row.setContextMenuPolicy(Qt.CustomContextMenu)
                row.customContextMenuRequested.connect(lambda pos, r=row: self._menu(r, pos))
                pv.addWidget(row)
                self.rows.append(row)
            if head is not None:
                head.set_count(len(ds), done_g)
        summary = T("pub_check_summary", ok=complete, n=len(self.rows))
        if gaps:
            summary += " · " + T("pub_check_gaps", gaps=", ".join(f"{PUB.check_label(k)} ({n})" for k, n in
                                                               sorted(gaps.items(), key=lambda x: [c for c, _ in
                                                                      PUB.CHECKS].index(x[0]))))
        self.lbl_head.setText(f"<b>{T('pub_compounds')}</b>&nbsp;&nbsp;&nbsp;<span style='color:gray'>{len(self.rows)} · "
                              f"{_esc(summary)}</span>")
        self.bar_progress.setRange(0, max(1, len(self.rows)))
        self.bar_progress.setValue(complete)
        self.lbl_progress.setText(T("pub_progress", k=complete, n=len(self.rows)))
        self.lbl_empty.setVisible(not self.rows)
        self.lbl_missing.setVisible(bool(missing))
        self.lbl_missing.setText(T("pub_missing", p=", ".join(missing)))
        self.b_pack.setEnabled(bool(self.rows))
        self._filter(self.ed_filter.text())
        self.b_si.setEnabled(bool(self.rows) or bool(data.get("reaction_paths")))

    def _fill_paths(self, data):
        from elucida.app.reaction_paths import directory
        self.path_gallery.remove_all()
        for c in self.path_cards:
            c.setParent(None)
            c.deleteLater()
        self.path_cards = []
        for item in data.get('reaction_paths', []):
            c = PathCard(item, directory(self.pdir, item['uid']) / 'preview.png')
            c.opened.connect(lambda _=None, it=item: self.path_panel.open_item(it))
            c.setContextMenuPolicy(Qt.CustomContextMenu)
            c.customContextMenuRequested.connect(lambda pos, c=c: self._path_menu(c, pos))
            self.path_cards.append(c)
            self.path_gallery.add(c)
        self.path_gallery.add(self.b_new_path)
        panel, menu = self.path_panel, self.b_restore.menu()
        menu.clear()
        for i in range(panel.removed.count()):
            menu.addAction(panel.removed.itemText(i), lambda i=i: (panel.removed.setCurrentIndex(i), panel.restore()))
        self.b_restore.setVisible(panel.removed.count() > 0)

    def _path_menu(self, card, pos):
        panel, item = self.path_panel, card.item

        def select():
            for i in range(panel.list.count()):
                if panel.list.item(i).data(Qt.UserRole)['uid'] == item['uid']:
                    panel.list.setCurrentRow(i)

        def rename():
            name, ok = QInputDialog.getText(self, T('rp_rename_path'), T('rp_rename_q'), text=item['name'])
            if ok and name.strip():
                select()
                panel.name.setText(name.strip())
                panel.rename()
        m = QMenu(self)
        m.addAction(T('rp_open'), lambda: panel.open_item(item))
        m.addAction(T('group_rename'), rename)
        m.addSeparator()
        m.addAction(T('remove'), lambda: (select(), panel.remove()))
        m.exec(card.mapToGlobal(pos))

    def _menu(self, row, pos):
        p = row.info["path"]
        m = QMenu(self)
        m.addAction(T("act_open_project"), lambda: self.main.open_project(p))
        m.addAction(T("pub_up"), lambda: self._move(p, -1))
        m.addAction(T("pub_down"), lambda: self._move(p, 1))
        m.addAction(T("recent_reveal"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        gm = m.addMenu(T("group_menu"))                  # Gruppe: vorhandene, neue, keine
        cur = getattr(row, "group", None)
        for g in PUB.load(self.pdir)["groups"]:
            a = gm.addAction(g, lambda g=g: self._set_group(p, g))
            a.setCheckable(True)
            a.setChecked(g == cur)
        gm.addSeparator()
        gm.addAction(T("group_new") + " …", lambda: self._new_group_for(p))
        a = gm.addAction(T("group_none"), lambda: self._set_group(p, None))
        a.setEnabled(cur is not None)
        m.addSeparator()
        m.addAction(T("move_title"), lambda: self.main.move_compound(p))
        m.addAction(T("move_copy_title"), lambda: self.main.move_compound(p, copy=True))
        m.addAction(T("pub_remove"), lambda: self._remove(p))
        m.exec(row.mapToGlobal(pos))

    def _filter(self, text):
        for r in self.rows:
            r.setVisible(r.matches(text))
        for h, g in getattr(self, "headers", []):     # Überschrift nur, wenn in der Gruppe etwas übrig ist
            h.setVisible(not text.strip() or any(r.matches(text) for r in self.rows if getattr(r, "group", None) == g))
        for p, g in getattr(self, "panels", []):
            p.setVisible(not text.strip() or any(r.matches(text) for r in self.rows if getattr(r, "group", None) == g))

    # -- Gruppen ---------------------------------------------------------------------------
    def _ask_group_name(self, old=""):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, T("group_new"), T("group_name_q"), text=old)
        return name.strip() if ok and name.strip() else None

    def new_group(self):
        name = self._ask_group_name()
        if name:
            PUB.add_group(self.pdir, name)
            self.refresh()

    def _set_group(self, path, name):
        PUB.set_group(self.pdir, path, name)
        self.refresh()

    def _new_group_for(self, path):
        name = self._ask_group_name()
        if name:                                   # Abbrechen lässt die Zuordnung, wie sie ist
            self._set_group(path, name)

    def _group_menu(self, head, pos):
        g = head.group
        if g is None:
            return
        m = QMenu(self)
        m.addAction(T("group_rename"), lambda: self._rename_group(g))
        m.addAction(T("pub_up"), lambda: (PUB.move_group(self.pdir, g, -1), self.refresh()))
        m.addAction(T("pub_down"), lambda: (PUB.move_group(self.pdir, g, 1), self.refresh()))
        m.addSeparator()
        m.addAction(T("group_delete"), lambda: (PUB.delete_group(self.pdir, g), self.refresh()))
        m.exec(head.mapToGlobal(pos))

    def _rename_group(self, g):
        new = self._ask_group_name(g)
        if new and not PUB.rename_group(self.pdir, g, new):
            self.main.error(T("group_exists", g=new))
        self.refresh()

    def sort_by_name(self):
        PUB.sort_by_name(self.pdir)
        self.refresh()

    def _dropped(self, path, y):
        """Abgelegte Verbindung: Gruppe = Überschrift oberhalb der Ablagestelle; Platz vor der ersten Zeile dieser
        Gruppe, deren Mitte unterhalb liegt (sonst ans Ende der Gruppe)."""
        g = None
        if self.headers:
            above = [hg for h, hg in self.headers if h.geometry().top() <= y]
            g = above[-1] if above else self.headers[0][1]
            PUB.set_group(self.pdir, path, g)
        rows_g = [r for r in self.rows if getattr(r, "group", None) == g and r.info["path"] != path]
        data = PUB.load(self.pdir)
        ent = {PUB._abs(self.pdir, c): i for i, c in enumerate(data["compounds"])}
        before = next((r for r in rows_g if y < r.mapTo(self.drop_area, r.rect().center()).y()), None)
        if before is not None:
            idx = ent.get(Path(before.info["path"]).resolve(), len(data["compounds"]))
        elif rows_g:
            idx = ent.get(Path(rows_g[-1].info["path"]).resolve(), len(data["compounds"]) - 1) + 1
        else:
            idx = len(data["compounds"])
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
        """Angaben: zeigt die Seite „Angaben“ (früher ein Dialog, Nutzerwunsch: keine Popups)."""
        self.project_tabs.setCurrentWidget(self.info_page)
        self.info_page.eds[PUB.FIELDS[0][0]].setFocus()

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




def _esc(s):
    import html
    return html.escape(str(s))


def _keep_i(s):
    """Escapen, kursive Teile (<i>…</i>) des Titels erhalten."""
    return _esc(s).replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")


class PublicationInfoPage(QWidget):
    """Seite „Angaben“ der Projektseite (für README.txt und die Titelseite der Gesamt-SI), früher ein Dialog
    (Nutzerwunsch 2026-11-11: keine Popups). Ein Feld gilt beim Verlassen, die Lizenz sofort; gespeichert wird in
    `publication.elucida` wie bisher."""

    def __init__(self, page):
        super().__init__()
        self.page = page
        g = QGroupBox(T("pub_details_grp"))
        g.setMaximumWidth(2 * STYLE.COLUMN_W)             # Lesebreite: Felder nicht über die ganze Seite
        g.setProperty("widefields", True)                 # Felder reichen bis zum Kartenrand
        f = STYLE.make_form(g)
        hint = STYLE.HintLabel(T("pub_info_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)                # Hinweise grau wie überall
        hint.setProperty("plaintext", True)               # linksbündig am Kartenrand, nicht mittig
        hint.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        f.addRow(hint)
        self.eds = {}
        for key, multi in PUB.FIELDS:
            ed = QPlainTextEdit() if multi else QLineEdit()
            if multi:                                       # Höhen wie im früheren Dialog
                ed.setFixedHeight(90 if key in ("project_description", "dataset_description") else 56)
                ed.installEventFilter(self)
            else:
                ed.editingFinished.connect(self.apply)
            ph = T("pub_ph_" + key)
            if ph != "pub_ph_" + key:
                ed.setPlaceholderText(ph)
            self.eds[key] = ed
            f.addRow(T("pub_f_" + key), ed)
        self.cmb_lic = QComboBox()
        for k, (name, *_rest) in PUB.LICENSES.items():
            self.cmb_lic.addItem(name, k)
        self.cmb_lic.currentIndexChanged.connect(self.apply)
        f.addRow(T("pub_f_license"), self.cmb_lic)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.addWidget(g)
        v.addStretch(1)
        STYLE.tidy(inner)
        v.setContentsMargins(0, 12, 0, 0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scrolled(inner))
        self._loading = False

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.FocusOut:
            self.apply()
        return False

    @staticmethod
    def _text(ed):
        return (ed.toPlainText() if isinstance(ed, QPlainTextEdit) else ed.text()).strip()

    def values(self):
        out = {k: self._text(ed) for k, ed in self.eds.items()}
        out["license"] = self.cmb_lic.currentData()
        return out

    def load(self, data):
        """publication.elucida -> Felder; ein Feld mit Fokus bleibt (dort wird gerade getippt)."""
        self._loading = True
        try:
            for k, ed in self.eds.items():
                if ed.hasFocus():
                    continue
                v = str(data.get(k) or "")
                if self._text(ed) != v.strip():
                    ed.setPlainText(v) if isinstance(ed, QPlainTextEdit) else ed.setText(v)
            self.cmb_lic.setCurrentIndex(max(0, self.cmb_lic.findData(data.get("license") or "CC-BY-4.0")))
        finally:
            self._loading = False

    def apply(self, *_):
        """Felder -> publication.elucida, nur bei einer Änderung; Kopf der Seite und Fenstertitel ziehen nach."""
        pdir = self.page.pdir
        if self._loading or pdir is None:
            return
        data = PUB.load(pdir)
        new = self.values()
        if all((data.get(k) or "") == v for k, v in new.items()):
            return
        data.update(new)
        PUB.save(pdir, data)
        self.page.refresh()
        self.page.main.update_title()


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


def edit_procedures(parent, pdir):
    """Allgemeine Vorschriften des Projekts bearbeiten (Projektseite, GP-Menü des Synthese-Tabs)."""
    if not pdir:
        return
    dlg = ProceduresDialog(parent, PUB.load(pdir)["procedures"])
    if dlg.exec() == QDialog.Accepted:
        apply_procedures(getattr(parent, "main", None), pdir, dlg.result(), dlg.renames())


def apply_procedures(main, pdir, procs, renames):
    """Vorschriften speichern; umbenannte Kürzel wirken wie Variablen (Robin, F-Review): alle Verbindungen des
    Projekts folgen (Zuordnung und „GP A“ im Text), die offene über ihren Zustand (ein Rückgängig-Schritt)."""
    data = PUB.load(pdir)
    data["procedures"] = procs
    PUB.save(pdir, data)
    open_dir = getattr(main, "project_dir", None)
    PUB.rename_procedures(pdir, renames, skip=open_dir)
    if open_dir and PUB.publication_of(open_dir) == Path(pdir).resolve() and \
            PUB.rename_gp_in(main.syn_state, renames):
        if main._built("syn"):
            main.replace_tab("syn")
        main.push_undo()


class ProceduresDialog(QDialog):
    """GP A, GP B …: Kürzel, Titel und Text (Absätze durch Leerzeilen, Formeln wie in den SI-Texten). In der
    Gesamt-SI einmal direkt vor der ersten Verbindung, die die Vorschrift benutzt."""

    def __init__(self, parent, procs):
        super().__init__(parent)
        self.setWindowTitle(T("pub_procs"))
        self.resize(720, 520)
        self.procs = [dict(p, _orig=p["key"]) for p in procs]      # _orig: Umbenennen an Verbindungen weitergeben
        v = QVBoxLayout(self)
        hint = QLabel(T("pub_procs_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        h = QHBoxLayout()
        lv = QVBoxLayout()
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._show)
        lv.addWidget(self.lst, 1)
        br = QHBoxLayout()
        b = QPushButton(T("pub_procs_add"))
        b.clicked.connect(self._add)
        br.addWidget(b)
        b = QPushButton(T("remove"))
        b.clicked.connect(self._remove)
        br.addWidget(b)
        lv.addLayout(br)
        h.addLayout(lv, 1)
        f = QFormLayout()
        self.ed_key, self.ed_title, self.ed_text = QLineEdit(), QLineEdit(), QPlainTextEdit()
        self.ed_key.setMaximumWidth(80)
        self.ed_title.setPlaceholderText(T("pub_procs_title_ph"))
        self.ed_text.setPlaceholderText(T("pub_procs_text_ph"))
        f.addRow(T("pub_procs_key"), self.ed_key)
        f.addRow(T("pub_procs_title"), self.ed_title)
        f.addRow(self.ed_text)
        for ed in (self.ed_key, self.ed_title):
            ed.textEdited.connect(self._store)
        self.ed_text.textChanged.connect(self._store)
        h.addLayout(f, 3)
        v.addLayout(h, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._fill()
        self.lst.setCurrentRow(0 if self.procs else -1)
        self._show(self.lst.currentRow())

    def _label(self, p):
        return f"GP {p['key']}" + (f" – {p['title']}" if p.get("title") else "")

    def _fill(self):
        self.lst.blockSignals(True)
        self.lst.clear()
        self.lst.addItems([self._label(p) for p in self.procs])
        self.lst.blockSignals(False)

    def _show(self, i):
        on = 0 <= i < len(self.procs)
        p = self.procs[i] if on else {}
        for ed in (self.ed_key, self.ed_title, self.ed_text):
            ed.blockSignals(True)
            ed.setEnabled(on)
        self.ed_key.setText(p.get("key", ""))
        self.ed_title.setText(p.get("title", ""))
        self.ed_text.setPlainText(p.get("text", ""))
        for ed in (self.ed_key, self.ed_title, self.ed_text):
            ed.blockSignals(False)

    def _store(self, *_):
        i = self.lst.currentRow()
        if 0 <= i < len(self.procs):
            self.procs[i].update(key=self.ed_key.text().strip(), title=self.ed_title.text().strip(),
                                 text=self.ed_text.toPlainText().strip())
            self.lst.item(i).setText(self._label(self.procs[i]))

    def _add(self):
        used = {p["key"] for p in self.procs}
        key = next(c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "".join(map(str, range(100))) if c not in used)
        self.procs.append(dict(key=key, title="", text=""))
        self._fill()
        self.lst.setCurrentRow(len(self.procs) - 1)

    def _remove(self):
        i = self.lst.currentRow()
        if 0 <= i < len(self.procs):
            del self.procs[i]
            self._fill()
            self.lst.setCurrentRow(min(i, len(self.procs) - 1))
            self._show(self.lst.currentRow())

    def result(self):
        """Ohne Kürzel fällt eine Vorschrift weg; doppelte Kürzel: die erste gilt."""
        out, seen = [], set()
        for p in self.procs:
            if p["key"] and p["key"] not in seen:
                seen.add(p["key"])
                out.append({k: v for k, v in p.items() if k != "_orig"})
        return out

    def renames(self):
        """Umbenannte Kürzel {alt: neu} (Tausch A <-> B möglich)."""
        keys = {p["key"] for p in self.result()}
        return {p["_orig"]: p["key"] for p in self.procs
                if p.get("_orig") and p["key"] and p["key"] != p["_orig"] and p["key"] in keys}


def _check_list(names, checked=True):
    t = STYLE.check_table((T("col_compound"),))
    for n in names:
        STYLE.check_row(t, n, (n,), checked)
    return t


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
            gone = []
            for d in PUB.sync(self.pdir)[0]:
                items = DP.collect(PRJ.load(d), d, gone)
                saved = saved_selection(main.settings, d)           # Auswahl aus dem Einzeldialog gilt weiter
                for it in items:
                    it.on = bool(saved.get(it.key, it.on if it.group != "dft" else True))
                self.plans.append(DP.Plan(PUB.compound_name(d), d, items))
            self.codes = DP.assign_codes(self.plans)
        finally:
            QApplication.restoreOverrideCursor()
        if gone:
            main.error(T("dp_missing", n=len(gone), names=", ".join(gone[:8])))
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
            if self.lst.item(i, 0).checkState() != Qt.Checked:
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
        readme = PUB.readme_text(data, kinds, [p.name for p in plans], scrubbed=self.cb_text.isChecked()) \
            if self.cb_readme.isChecked() else ""
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
        self.cb_groups = QCheckBox(T("pub_si_groups"))       # Gruppen sonst nur Orientierung auf der Projektseite
        self.cb_groups.setToolTip(T("pub_si_groups_tip"))
        self.cb_groups.setChecked(PUB.load(pdir)["group_headings"])
        rp_opts = PUB.load(pdir).get("reaction_paths_si") or {}
        self.cb_paths = QCheckBox(T('rp_reaction_paths_in_computational_section'))
        self.cb_paths.setChecked(rp_opts.get("include") is not False)
        self.cmb_paths = QComboBox()
        self.cmb_paths.addItem(T('rp_before_individual_calculations'), "before")
        self.cmb_paths.addItem(T('rp_after_individual_calculations'), "after")
        self.cmb_paths.setCurrentIndex(max(0, self.cmb_paths.findData(rp_opts.get("position", "before"))))
        sv.addWidget(self.cb_paths); sv.addWidget(self.cmb_paths)
        def paths_enabled():
            self.cb_paths.setEnabled(self.cbs["dft"].isChecked())
            self.cmb_paths.setEnabled(self.cbs["dft"].isChecked() and self.cb_paths.isChecked())
        self.cbs["dft"].toggled.connect(paths_enabled)
        self.cb_paths.toggled.connect(paths_enabled)
        paths_enabled()
        self.pdir = pdir
        sv.addWidget(self.cb_toc)
        sv.addWidget(self.cb_methods)
        sv.addWidget(self.cb_groups)
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
        data = PUB.load(self.pdir)
        data["group_headings"] = self.cb_groups.isChecked()
        data["reaction_paths_si"] = dict(include=self.cb_paths.isChecked(), position=self.cmb_paths.currentData())
        PUB.save(self.pdir, data)
        self.accept()

    def sections(self):
        return [k for k, cb in self.cbs.items() if cb.isChecked()]

    def compounds(self):
        return [d for i, d in enumerate(self.dirs) if self.lst.item(i, 0).checkState() == Qt.Checked]

    def toc(self):
        return self.cb_toc.isChecked()

    def methods(self):
        return self.cb_methods.isChecked()

    def template(self):
        return self.cmb_tpl.currentData()
