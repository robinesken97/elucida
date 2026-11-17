"""
elucida/app/publication_view.py - Oberfläche der Publikation (elucida/app/publication.py): Seite mit den Verbindungen,
Angaben (README), Datenpakete aller Verbindungen, Gesamt-SI; Zeile für den Startbildschirm.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar,
                               QPushButton, QSizePolicy,
                               QScrollArea, QVBoxLayout, QWidget,
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


PATH_CARD_H = 212                 # Karten der Reaktionspfade und Vergleiche (Bild THUMB_H + Name und Stand), auch „neu“


class PathCard(WEL.ClickCard):
    """Reaktionspfad als Karte: Vorschau des Profils, Name, Stand."""

    def __init__(self, item, preview):
        super().__init__()
        self._setup(dict(path=item["uid"]))
        self.item = item
        self.setFixedHeight(PATH_CARD_H)
        self.setMinimumWidth(WEL.CARD_W)
        v = QVBoxLayout(self)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)
        # Vorschau so groß wie die Strukturbilder der Verbindungskarten, 12 px Luft oben und unten, mindestens 16 seitlich
        # (Nutzerhinweis 2026-11-13: vorher 84 px hoch, zu klein)
        v.addWidget(WEL.card_picture(str(preview) if preview.exists() else None, WEL.THUMB_H, WEL.CARD_W - 32, 24))
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


IN = STYLE.COL_PAD                # Einzug der Projektseite: Kopf, Reiter und Seiten bündig mit den Karten des Vergleichs
PAGE_MARGINS = (28 - IN, 24, 28 - IN, 16)    # (der eingebettete Tab bringt seinen Spaltenrand selbst mit)
HEAD_GAP = 14                     # Abstand Tabelle – nächste Gruppenüberschrift (mit dem Listenabstand 20)


class GroupHeader(QWidget):
    """Überschrift einer Gruppe auf der Projektseite (Name, Anzahl, vollständig); Rechtsklick: umbenennen, verschieben,
    auflösen. Auch Ziel beim Ziehen (alles unterhalb gehört zur Gruppe)."""

    def __init__(self, group, n, first=True):
        super().__init__()
        self.group = group
        h = QHBoxLayout(self)
        # bündig mit „Verbindungen“ und den Zeilen; senkrecht ein Raster (Nutzerwunsch 2026-11-12): Überschrift –
        # Tabelle 8, Tabelle – nächste Überschrift 20, wie Reiter – Seitenkopf und Seitenkopf – erste Überschrift
        h.setContentsMargins(0, 0 if first else HEAD_GAP, 4, 2)
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
        layout.setContentsMargins(*PAGE_MARGINS)
        layout.setSpacing(12)                               # Fortschrittszeile – Reiter sichtbar 16, wie Untertitel – Fortschritt
        # Kopf: Titel, Autoren, Fortschritt; rechts die beiden Exporte (nur der wichtigste blau)
        self.head = QWidget()
        hd = QHBoxLayout(self.head)
        hd.setContentsMargins(IN, 0, IN, 0)
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
        self.lbl_progress.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # darf abgeschnitten werden: sonst
        pr.addWidget(self.lbl_progress, 1)                                             # bestimmt er die Fensterbreite mit
        tv.addSpacing(10)
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
        self.project_tabs.setObjectName("projectTabs")      # ohne Rahmenlinie über den Reitern (war an den Knöpfen
        self.project_tabs.tabBar().setDrawBase(False)       # rechts gebrochen und versetzt)
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
        overview = QWidget()
        self.project_tabs.addTab(overview, T('pub_compounds'))
        v = QVBoxLayout(overview)
        v.setContentsMargins(IN, 12, IN, 0)
        v.setSpacing(8)
        from elucida.app.reaction_paths import PathPanel
        self.paths_page = QWidget()
        self.project_tabs.addTab(self.paths_page, T('rp_computational_chemistry'))
        from elucida.app.comparison import ComparePage
        self.compare_page = ComparePage(self)               # Vergleich über die Verbindungen (vor „Angaben“)
        self.project_tabs.addTab(self.compare_page, T("pub_compare_tab"))
        self.info_page = PublicationInfoPage(self)          # Angaben (früher Dialog)
        self.project_tabs.addTab(self.info_page, T("pub_details_tab"))
        from elucida.app.publication_export import PublicationExportPage
        self.export_page = PublicationExportPage(self)      # Gesamt-SI und Datensätze als Karten (Entscheidung 69)
        self.project_tabs.addTab(self.export_page, T("pub_export_tab"))
        STYLE.center_corner(self.project_tabs)              # erst mit Reitern: vorher ist die Leiste 0 hoch und die
        # Knöpfe rechts (SI-Texte, Vorschriften, Ordner) blieben unsichtbar
        corner.layout().setContentsMargins(0, 0, IN, 8)     # 8: Schrift auf der Mittellinie der Reiter
        paths_layout = QHBoxLayout(self.paths_page)
        paths_layout.setContentsMargins(IN, 12, IN, 0)
        self.paths_layout = paths_layout
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
        self.b_new_path = add_card(T("rp_new_path"), T("rp_energy_profiles_and_irc_across_multiple_compounds"), PATH_CARD_H)
        self.b_new_path.clicked.connect(self.path_panel.new)
        top = QWidget()                                     # Karten oben, nicht mittig in der Höhe
        tv2 = QVBoxLayout(top)
        tv2.setContentsMargins(0, 0, 0, 0)
        tv2.addWidget(self.path_gallery)
        tv2.addStretch(1)
        lv.addWidget(scrolled(top), 1)
        ln.addLayout(lv, 1)
        self.cluster_page = ClusterPage(self)
        # Spalte „Cluster“ genau so breit wie die beiden Knöpfe im Kopf darüber (gleich breit, selbe Außenkanten):
        # vorher 360 px unter 380 px Knöpfen, die Knöpfe standen links über (Nutzerhinweis 2026-11-13)
        for b_ in (self.b_pack, self.b_si):
            b_.ensurePolished()
        bw_ = max(self.b_pack.sizeHint().width(), self.b_si.sizeHint().width())
        for b_ in (self.b_pack, self.b_si):
            b_.setFixedWidth(bw_)
        self.cluster_page.setFixedWidth(max(360, 2 * bw_ + self.head.layout().spacing()))
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
        self.box.setContentsMargins(0, 4, 0, 0)             # Seitenkopf – erste Überschrift/Tabelle wie Reiter – Seitenkopf
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
        self.project_tabs.currentChanged.connect(self.sync_main_button)

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
        self.outer.setContentsMargins(*((0, 0, 0, 0) if on else PAGE_MARGINS))       # Pfad: Ränder wie in den Tabs (PathWorkspace)
        self.paths_layout.setContentsMargins(*((0, 12, 0, 0) if on else (IN, 12, IN, 0)))
        self.main._update_crumbs()

    def compare_mode(self, on):
        """Offener Vergleich wie ein offener Pfad: Kopf, Reiter und Seitenleiste weg, zurück über die Pfadleiste."""
        if on:
            self.project_tabs.setCurrentWidget(self.compare_page)
        if on != getattr(self, "_cmp_full", False):
            self._cmp_full = on
            self._set_full(on or bool(self.path_workspace))
        else:
            self.main._update_crumbs()

    def sync_main_button(self, *_):
        """Ein Hauptknopf (blau) je Ansicht: mit offenem Vergleich ist es dessen „Exportieren“, sonst die Gesamt-SI."""
        cmp_open = self.project_tabs.currentWidget() is self.compare_page and self.compare_page.item is not None
        if bool(self.b_si.property("accent")) == cmp_open:
            STYLE.set_accent(self.b_si, not cmp_open, "export")
        exp = self.project_tabs.currentWidget() is getattr(self, "export_page", None)   # dort unten rechts (v4)
        self.b_si.setVisible(not exp)
        self.b_pack.setVisible(not exp)

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
        self.export_page.set_publication(self.pdir)
        if self.pdir is None:
            self.compare_page.set_publication(None)
            return
        data = PUB.load(self.pdir)
        self.path_panel.refresh()
        self._fill_paths(data)
        self.compare_page.set_publication(self.pdir)
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
                head = GroupHeader(g, len(ds), first=not self.headers)
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
        """„Datenpakete“ im Kopf: mit der Auswahl der Karte „Datensätze“ im Reiter „Export“ (früher ein Dialog)."""
        return self.export_page.dp_card.export()

    def export_si(self):
        """„Gesamt-SI“ (Hauptknopf): mit der Auswahl der Karte „Gesamt-SI“ im Reiter „Export“ (früher ein Dialog)."""
        return self.export_page.si_card.export()

    def show_export(self):
        """Klick aus der Exportmeldung: Reiter „Export“ mit beiden Karten."""
        self.project_tabs.setCurrentWidget(self.export_page)




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
        # CV-Messaufbau des Projekts (Nutzerentscheidung 2026-11-13): einmal erfasst, erster Absatz des Kapitels
        # „Cyclic Voltammetry“ der Gesamt-SI statt in jeder Bildunterschrift
        g2 = QGroupBox(T("pub_cv_grp"))
        g2.setMaximumWidth(2 * STYLE.COLUMN_W)
        g2.setProperty("widefields", True)
        f2 = STYLE.make_form(g2)
        hint2 = STYLE.HintLabel(T("pub_cv_hint"))
        hint2.setWordWrap(True)
        hint2.setStyleSheet(STYLE.HINT_CSS)
        hint2.setProperty("plaintext", True)
        hint2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        f2.addRow(hint2)
        self.cv_eds = {}
        for key in PUB.CV_SETUP:
            if key == "conv":                              # Konvention der Auftragung: Auswahl, kein Freitext
                self.cmb_cv_conv = QComboBox()
                for k_, lab_ in (("", T("pub_cv_conv_none")), ("iupac", T("pub_cv_conv_iupac")),
                                 ("polar", T("pub_cv_conv_polar"))):
                    self.cmb_cv_conv.addItem(lab_, k_)
                self.cmb_cv_conv.currentIndexChanged.connect(self.apply)
                f2.addRow(T("pub_cv_conv"), self.cmb_cv_conv)
                continue
            ed = STYLE.ChemEdit("")
            ed.setPlaceholderText(T("pub_cv_ph_" + key))
            ed.editingFinished.connect(self.apply)
            self.cv_eds[key] = ed
            f2.addRow(T("pub_cv_" + key), ed)
        g3, g4 = self._naming_card(), self._das_card()
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.addWidget(g)
        v.addWidget(g2)
        v.addWidget(g3)
        v.addWidget(g4)
        v.addStretch(1)
        STYLE.tidy(inner)
        v.setContentsMargins(IN, 12, IN, 0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scrolled(inner))
        self._loading = False

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.FocusOut:
            self.apply()
        return False

    # -- Bezeichner der Gesamt-SI (Nature: „Supplementary Figure 1“) und Data Availability Statement ------------------
    @staticmethod
    def _hint(text):
        h = STYLE.HintLabel(text)
        h.setWordWrap(True)
        h.setStyleSheet(STYLE.HINT_CSS)
        h.setProperty("plaintext", True)
        h.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        return h

    def _naming_card(self):
        g = QGroupBox(T("sinames_grp"))
        g.setMaximumWidth(2 * STYLE.COLUMN_W)
        g.setProperty("widefields", True)
        f = STYLE.make_form(g)
        f.addRow(self._hint(T("sinames_hint")))
        self.cmb_naming = QComboBox()
        for k in ("", "s", "supplementary"):
            self.cmb_naming.addItem(T("sinames_" + (k or "tpl")), k)
        self.cmb_naming.currentIndexChanged.connect(self.apply)
        f.addRow(T("sinames_label"), self.cmb_naming)
        return g

    def _das_card(self):
        """Bausteine nur aus Angaben des Nutzers (publication.DAS_KEYS); der Text steht darunter zum Kopieren und gehört
        ins Manuskript (ACS: unter „Associated Content“), nicht in die SI."""
        g = QGroupBox(T("das_grp"))
        g.setMaximumWidth(2 * STYLE.COLUMN_W)
        g.setProperty("widefields", True)
        f = STYLE.make_form(g)
        f.addRow(self._hint(T("das_hint")))
        self.das_eds = {}
        for k in ("repo", "link"):
            ed = QLineEdit()
            ed.setPlaceholderText(T("das_ph_" + k))
            ed.editingFinished.connect(self.apply)
            self.das_eds[k] = ed
            f.addRow(T("das_" + k), ed)
        row = QHBoxLayout()
        self.das_cbs = {}
        for k in ("ccdc", "fid"):
            cb = QCheckBox(T("das_cb_" + k))
            cb.setToolTip(T("das_cb_" + k + "_tip"))
            cb.setProperty("chip_here", True)
            cb.toggled.connect(self.apply)
            self.das_cbs[k] = cb
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("das_auto"), row)
        ed = QPlainTextEdit()
        ed.setFixedHeight(56)
        ed.setPlaceholderText(T("das_ph_extra"))
        ed.installEventFilter(self)
        self.das_eds["extra"] = ed
        f.addRow(T("das_extra"), ed)
        b = STYLE.copy_button(T("das_copy_tip"))
        b.clicked.connect(self.copy_das)
        self.btn_das_copy = b
        f.addRow(STYLE.text_head(T("das_out"), b))
        self.txt_das = STYLE.SiText("", T("das_empty"))
        f.addRow(self.txt_das)
        return g

    def das_values(self):
        out = {k: self._text(ed) for k, ed in self.das_eds.items() if self._text(ed)}
        out.update({k: "0" for k, cb in self.das_cbs.items() if not cb.isChecked()})   # Standard an: nur „aus“ merken
        return out

    def sync_das(self, data):
        pdir = self.page.pdir
        ccdc = PUB.ccdc_numbers(pdir) if pdir else []
        self.das_cbs["ccdc"].setEnabled(bool(ccdc))
        self.das_cbs["fid"].setEnabled(bool((data.get("fidpack") or {}).get("compounds")))
        self._das = PUB.das_text(data, ccdc)
        self.txt_das.setText(self._das)
        self.btn_das_copy.setEnabled(bool(self._das))

    def showEvent(self, ev):
        """Beim Anzeigen neu bilden: CCDC-Nummern und FID-Paket hängen an den Verbindungen, die sich seit dem Laden der
        Seite geändert haben können."""
        super().showEvent(ev)
        if self.page.pdir is not None and not self._loading:
            try:
                self.sync_das(PUB.load(self.page.pdir))
            except Exception:                                 # Anzeige: nie die Seite blockieren
                pass

    def copy_das(self):
        if getattr(self, "_das", ""):
            from elucida.tabs.ir_ea import copy_rich
            import html as _h
            copy_rich(self._das, _h.escape(self._das))
            self.page.main.statusBar().showMessage(T("das_copied"), 4000)

    @staticmethod
    def _text(ed):
        return (ed.toPlainText() if isinstance(ed, QPlainTextEdit) else ed.text()).strip()

    def values(self):
        out = {k: self._text(ed) for k, ed in self.eds.items()}
        out["license"] = self.cmb_lic.currentData()
        out["cv_setup"] = {k: ed.text().strip() for k, ed in self.cv_eds.items() if ed.text().strip()}
        if self.cmb_cv_conv.currentData():
            out["cv_setup"]["conv"] = self.cmb_cv_conv.currentData()
        out["si_naming"] = self.cmb_naming.currentData() or ""
        out["das"] = self.das_values()
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
            for k, ed in self.cv_eds.items():
                v = str((data.get("cv_setup") or {}).get(k) or "")
                if not ed.hasFocus() and ed.text().strip() != v:
                    ed.setText(v)
            self.cmb_cv_conv.setCurrentIndex(max(0, self.cmb_cv_conv.findData((data.get("cv_setup") or {}).get("conv") or "")))
            self.cmb_naming.setCurrentIndex(max(0, self.cmb_naming.findData(data.get("si_naming") or "")))
            das = data.get("das") or {}
            for k, ed in self.das_eds.items():
                if not ed.hasFocus() and self._text(ed) != das.get(k, ""):
                    ed.setPlainText(das.get(k, "")) if isinstance(ed, QPlainTextEdit) else ed.setText(das.get(k, ""))
            for k, cb in self.das_cbs.items():
                cb.setChecked(das.get(k) != "0")
            self.sync_das(data)
        finally:
            self._loading = False

    def apply(self, *_):
        """Felder -> publication.elucida, nur bei einer Änderung; Kopf der Seite und Fenstertitel ziehen nach."""
        pdir = self.page.pdir
        if self._loading or pdir is None:
            return
        data = PUB.load(pdir)
        new = self.values()
        if all((data.get(k) or ({} if k in ("cv_setup", "das") else "")) == v for k, v in new.items()):
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


def _mb(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e5 else f"{n / 1e3:.0f} kB"


def _fid_write(main, pdir, plans, out_dir, names, texts):
    """„FID for Publication“ der gewählten Verbindungen schreiben und im Projekt vermerken (Statement)."""
    from elucida.app import project as PRJ
    from elucida.exchange import datapack as DP
    groups = [(pl.name, DP.fid_items(PRJ.load(pl.pdir), pl.pdir, pl.name, names=names,     # Abwahl im Dialog gilt
                                     only={str(Path(it.src).resolve()) for it in pl.items if it.on and it.group == "nmr"}))
              for pl in plans]
    rep = DP.write_fid_package(groups, out_dir, names, texts)
    if rep.get("files"):
        data = PUB.load(pdir)
        data["fidpack"] = dict(name=Path(rep["path"]).name, compounds=list(rep["compounds"]),   # Namen fürs Statement,
                               entries=[PUB.entry_key(pdir, pl.pdir, data) for (_, its), pl in zip(groups, plans) if its])
        PUB.save(pdir, data)
        main.log_signal.emit(T("fidpack_done", p=rep["path"], n=len(rep["compounds"])))
    return rep
