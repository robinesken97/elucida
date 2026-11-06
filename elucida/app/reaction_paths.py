"""Publication-owned reaction paths, independent of any compound's DFT state.

Each path is a portable project under reaction_paths/<uuid>; the publication
index stores its name/ID. Imports are copies, with descriptive provenance.
No live references to another compound's geometry or viewer settings.
"""
import elucida
from copy import deepcopy
import os
from pathlib import Path
from elucida.app.i18n import T
import re
import uuid

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QDialogButtonBox, QListWidget, QListWidgetItem, QAbstractItemView,
                               QGroupBox, QTabWidget, QWidget, QLineEdit, QComboBox, QGridLayout, QMenu)
from elucida.app import project as PRJ, publication as PUB, style as STYLE


def directory(pdir, uid):
    if not re.fullmatch(r"[a-f0-9]{32}", uid):
        raise ValueError("Invalid reaction-path ID")
    return Path(pdir).resolve() / "reaction_paths" / uid


def create(pdir, name):
    from elucida.tabs.dft import DFTTab
    item = dict(uid=uuid.uuid4().hex, name=name.strip())
    st = deepcopy(DFTTab.DEFAULT_STATE)
    st.setdefault("profile", {}).update(size_cm=[24., 15.])
    PRJ.save(directory(pdir, item['uid']), dict(dft=st))
    meta = PUB.load(pdir)
    meta.setdefault("reaction_paths", []).append(item)
    PUB.save(pdir, meta)
    return item


def import_entry(host, entry, origin):
    """Copy every required source; retain orbital choices/camera but use a new ID."""
    entry = deepcopy(entry)
    entry.update(uid=uuid.uuid4().hex[:8], origin=origin)
    for key in ("file", "molden"):
        if entry.get(key):
            entry[key] = host.import_file(entry[key], PRJ.data_sub("dft"))
    for orb in entry.get("orbitals") or []:
        orb["file"] = host.import_file(orb["file"], PRJ.data_sub("dft"))
    host.state['dft'].setdefault('entries', []).append(entry)
    host.state['dft']['current'] = entry['uid']
    return entry


def set_removed(pdir, uid, removed):
    """Move an index entry only; both actions preserve every source file."""
    meta = PUB.load(pdir)
    source, target = ('reaction_paths', 'removed_reaction_paths') if removed else ('removed_reaction_paths', 'reaction_paths')
    item = next((x for x in meta.get(source, []) if x['uid'] == uid), None)
    if item is None:
        return
    meta[source] = [x for x in meta.get(source, []) if x['uid'] != uid]
    meta.setdefault(target, []).append(item)
    PUB.save(pdir, meta)


class PathHost(QMainWindow):
    """Small explicit host for the existing DFT tab; no main-window state swapping."""
    changed = Signal()
    def __init__(self, main, pdir, item, readonly=False):
        super().__init__(main)
        self.owner, self.pdir, self.item, self.readonly = main, Path(pdir), item, readonly
        self.project_dir = directory(pdir, item['uid'])
        self.state = PRJ.load(self.project_dir)
        self.state.setdefault('dft', {})
        self.extra_cache, self.compound, self.xray_tab = {}, {}, None
        self.settings, self.log_signal = main.settings, main.log_signal
        self._format = deepcopy(main.text_format('dft'))
        self.restoring, self.tab = True, None
        self.history, self.cursor = [], -1
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.save)
        from elucida.tabs.dft import DFTTab
        self.tab = DFTTab(self, self.state['dft'])
        self.tab.setParent(self)
        self.tab.sync_widgets()
        self.restoring = False
        if not readonly:
            self.push_undo()

    def ensure_project(self): return True
    def text_format(self, _key): return deepcopy(self._format)
    def canvas_is_dark(self): return self.owner.canvas_is_dark()
    def import_file(self, path, sub): return PRJ.import_file(self.project_dir, path, sub)
    def export_name(self): return self.item['name']
    def show_hover(self, text): self.statusBar().showMessage(text)
    def error(self, text): self.owner.error(text)
    def exported(self, dirs): self.owner.exported(dirs)
    def place_exports(self, files): return PRJ.place_exports(self.project_dir, files)
    def tab_key_of(self, tab): return 'dft' if tab is self.tab else None
    def replace_tab(self, _key): self.rebuild_tabs()
    def rebuild_tabs(self):
        self.tab.sync_widgets(); self.tab.render(push=False)

    def push_undo(self):
        if self.restoring or self.readonly: return
        snap = deepcopy(self.state)
        if self.cursor >= 0 and snap == self.history[self.cursor]: return
        self.history = self.history[:self.cursor+1] + [snap]
        self.cursor += 1
        self.timer.start()
        self.changed.emit()

    def restore(self, delta):
        target = self.cursor + delta
        if not 0 <= target < len(self.history): return
        self.restoring = True
        try:
            self.cursor = target
            # The composition has its own Octet undo history. Retain immutable
            # image revisions even when calculation edits are undone.
            composition = {k: v for k, v in self.tab.pages.prof.items() if k.startswith('composition')}
            self.state['dft'].clear(); self.state['dft'].update(deepcopy(self.history[target]['dft']))
            self.tab.pages.prof.update(composition)
            self.tab.sync_widgets(); self.tab.render(push=False)
        finally:
            self.restoring = False
        self.save()

    def save(self):
        if self.readonly: return True
        try:
            PRJ.save(self.project_dir, self.state)
            return True
        except Exception as ex:
            self.error(str(ex))
            return False

    def dispose(self):
        self.timer.stop()
        self.tab.timer.stop()
        for dragger in (self.tab.dragger, getattr(self.tab.pages, 'profile_dragger', None)):
            if dragger: dragger.disconnect()
        self.tab.deleteLater()
        self.deleteLater()


class PathWorkspace(QWidget):
    closed = Signal()

    def __init__(self, main, pdir, item):
        super().__init__(main)
        self.main, self.pdir, self.item = main, Path(pdir), item
        self.host = PathHost(main, pdir, item)
        self._disposed = False
        self.setWindowTitle(item['name'] + ' · ' + T('rp_reaction_path'))
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0); v.setSpacing(6)
        # Alle Aktionen neben den Reitern statt in eigenen Zeilen: die Höhe gehört dem Canvas (Nutzerwunsch).
        corner = QWidget()
        row = QHBoxLayout(corner); row.setContentsMargins(0, 0, 0, 2); row.setSpacing(6)
        b = QPushButton('☰'); b.setFixedWidth(34)
        b.setToolTip(T('rp_toggle_list')); b.setAccessibleName(T('rp_toggle_list'))
        b.clicked.connect(lambda: main.pub_page.path_rail.setVisible(not main.pub_page.path_rail.isVisible()))
        row.addWidget(b)
        b = QPushButton(T('rp_data')); b.setIcon(STYLE.icon('open'))
        b.setToolTip(T('rp_saved_automatically_in_the_project_imports_are_independent_copies'))
        menu = QMenu(b)
        menu.addAction(T('rp_import_from_compounds'), self.from_compounds)
        menu.addAction(T('rp_load_calculation_files'), self.host.tab.add_xyz)
        b.setMenu(menu); row.addWidget(b)
        for key, step in (('act_undo', -1), ('act_redo', 1)):
            b = QPushButton(); b.clicked.connect(lambda _=False, s=step: self.undo(s))
            b.setToolTip(T(key)); b.setAccessibleName(T(key))
            b.setIcon(STYLE.icon('undo' if step < 0 else 'redo')); b.setFixedWidth(34)
            row.addWidget(b)
        b = QPushButton(T('rp_export_profile')); b.clicked.connect(self.export)
        b.setIcon(STYLE.icon('export')); b.setProperty('accent', True)
        row.addWidget(b)
        close = QPushButton(T('rp_back_to_paths')); close.clicked.connect(self.accept); row.addWidget(close)
        self.import_panel = QGroupBox(T('rp_import_calculations'))
        iv = QVBoxLayout(self.import_panel)
        self.import_list = QListWidget()
        self.import_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.import_list.setMaximumHeight(160); iv.addWidget(self.import_list)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.import_selected)
        buttons.rejected.connect(self.import_panel.hide); iv.addWidget(buttons)
        self.import_panel.hide(); v.addWidget(self.import_panel)
        self.profile = self.host.tab.pages.prof_group
        self.composition = None
        self.tabs = QTabWidget()
        # Remove the old profile's now-empty wrapper from the compound-style DFT view.
        right = self.host.tab.right_tabs
        wrapper = self.profile.parentWidget()
        while wrapper and right and right.indexOf(wrapper) < 0 and wrapper is not right:
            wrapper = wrapper.parentWidget()
        if right and right.indexOf(wrapper) >= 0: right.removeTab(right.indexOf(wrapper))
        if elucida.octet_enabled():
            from elucida.app.path_composition import CompositionEditor
            self.composition = CompositionEditor(self.host, self)
            self.tabs.addTab(self.composition, T('rp_compose'))
            # All drawing belongs to the common canvas, not nested popup editors.
            pg = self.host.tab.pages
            pg.btn_images.hide(); pg.btn_workspace.hide(); pg.tbl_sp.setColumnHidden(5, True)
        self.tabs.addTab(self.profile, T('rp_calculation_data'))
        self.tabs.addTab(self.host.tab, T('rp_3d_orbitals'))
        self.tabs.currentChanged.connect(self.tab_changed)
        self.host.changed.connect(self.tab_changed)
        self.tabs.setCornerWidget(corner, Qt.TopRightCorner)
        v.addWidget(self.tabs, 1)
        self.profile.setTitle("")

    def undo(self, delta):
        if self.composition and (self.composition.view_editor or self.composition.diagram_editor): return
        if self.composition and self.tabs.currentWidget() is self.composition:
            self.composition.editor.command('undo' if delta < 0 else 'redo')
        else:
            self.host.restore(delta)

    def from_compounds(self):
        candidates = []
        for d in PUB.sync(self.pdir)[0]:
            state = self.main.get_state() if self.main.project_dir and Path(self.main.project_dir).resolve() == d.resolve() else PRJ.load(d)
            name = (state.get('compound') or {}).get('name') or d.name
            for e in (state.get('dft') or {}).get('entries', []):
                candidates.append((name, e))
        if not candidates:
            self.host.error(T('rp_no_dft_calculations_have_been_loaded_in_the_compounds_yet'))
            return
        self.import_candidates = candidates
        self.import_list.clear()
        for name, e in candidates:
            self.import_list.addItem(f"{name} · {e.get('name') or Path(e['file']).stem}")
        self.import_panel.show()

    def import_selected(self):
        dft = self.host.state['dft']
        entries, current = list(dft.get('entries', [])), dft.get('current')
        try:                                             # alles oder nichts: sonst Einträge außerhalb des Undo-Verlaufs
            for row in sorted(self.import_list.row(x) for x in self.import_list.selectedItems()):
                name, e = self.import_candidates[row]
                import_entry(self.host, e, dict(compound=name, calculation=e.get('name') or Path(e['file']).stem))
        except OSError as ex:
            dft['entries'], dft['current'] = entries, current
            self.main.error(T('rp_import_failed', name=name, error=ex))
            return
        self.host.tab.sync_widgets(); self.host.push_undo()
        self.import_panel.hide(); self.tab_changed()

    def tab_changed(self, *_):
        if self.composition: self.composition.refresh_sources()
        if self.tabs.currentWidget() is self.profile: self.host.tab.pages.refresh()
        self.main._update_undo_actions()

    def calculations(self):
        self.tabs.setCurrentWidget(self.host.tab)

    def export(self):
        from elucida.core.uvvis import safe_name
        try:
            if self.composition:
                files = self.composition.export()
                if files: self.host.exported({p.parent for p in files})
                return
            files = self.host.tab.pages.export_to(PRJ.staging(self.host.project_dir, 'dft') / safe_name(self.item['name']))
            files = self.host.place_exports(files)
            self.host.exported({p.parent for p in files})
        except Exception as ex: self.host.error(str(ex))

    def save(self):
        if self._disposed: return True
        return (not self.composition or self.composition.save()) and self.host.save()

    def dispose(self):
        if self._disposed:
            return
        # Small neutral preview is disposable; editing sources always stay authoritative.
        try:
            if self.composition and self.composition.editor.path:
                import pymupdf
                with pymupdf.open(str(self.composition.editor.path.with_suffix('.svg'))) as doc:
                    doc[0].get_pixmap(dpi=40, alpha=False).save(str(self.host.project_dir/'preview.png'))
            else:
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_agg import FigureCanvasAgg
                fig = Figure(); FigureCanvasAgg(fig)
                F, _ = self.host.tab.pages.build(fig)
                if F: fig.savefig(self.host.project_dir/'preview.png', dpi=70, facecolor='white')
        except Exception:
            pass
        self.host.dispose()
        self._disposed = True
        self.hide()

    def accept(self):
        if not self.save(): return
        self.dispose()
        self.closed.emit()


class PathPanel(QGroupBox):
    def __init__(self, page):
        super().__init__(T('rp_reaction_paths'), page)
        self.page = page
        v = QVBoxLayout(self)
        hint = QLabel(T('rp_energy_profiles_and_irc_across_multiple_compounds'))
        v.setContentsMargins(16, 12, 16, 16); v.setSpacing(10)
        hint.setWordWrap(True); hint.setProperty('formlabel', True)
        v.addWidget(hint)
        self.list = QListWidget(); self.list.setSpacing(4)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self.name_selected)
        self.list.itemDoubleClicked.connect(self.open); v.addWidget(self.list)
        self.name = QLineEdit(); self.name.setPlaceholderText(T('ov_name')); v.addWidget(self.name)
        row = QGridLayout()
        pos = 0
        for key, fn in (('rp_new_path', self.new), ('rp_open', self.open),
                           ('group_rename', self.rename), ('remove', self.remove)):
            b = STYLE.list_button(T(key)) if key in ('rp_new_path', 'remove') else QPushButton(T(key))
            b.clicked.connect(fn)
            if key == 'rp_new_path': b.setProperty('accent', True)
            row.addWidget(b, pos // 2, pos % 2); pos += 1
        v.addLayout(row)
        self.removed = QComboBox(); v.addWidget(self.removed)
        self.restore_button = QPushButton(T('rp_restore')); self.restore_button.setIcon(STYLE.icon('reset'))
        self.restore_button.clicked.connect(self.restore); v.addWidget(self.restore_button)

    def refresh(self):
        selected = self.selected()
        self.list.clear()
        if not self.page.pdir: return
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtCore import QSize
        self.list.setIconSize(QSize(72,54))
        for item in PUB.load(self.page.pdir).get('reaction_paths', []):
            row = QListWidgetItem(item['name']); row.setData(Qt.UserRole, item)
            row.setToolTip(item['name'])
            preview = directory(self.page.pdir, item['uid']) / 'preview.png'
            if preview.exists(): row.setIcon(QIcon(QPixmap(str(preview))))
            self.list.addItem(row)
            if selected and selected['uid'] == item['uid']: self.list.setCurrentItem(row)
        self.removed.clear()
        for item in PUB.load(self.page.pdir).get('removed_reaction_paths', []):
            self.removed.addItem(item['name'], item['uid'])
        self.removed.setVisible(self.removed.count() > 0)
        self.restore_button.setVisible(self.removed.count() > 0)

    def name_selected(self, row, *_):
        if row: self.name.setText(row.data(Qt.UserRole)['name'])

    def selected(self):
        row = self.list.currentItem()
        return row.data(Qt.UserRole) if row else None

    def new(self):
        name = self.name.text().strip() or T('rp_new_reaction_path')
        item = create(self.page.pdir, name)
        self.page.refresh(); self.open_item(item)

    def open(self, *_):
        item = self.selected()
        if item: self.open_item(item)

    def open_item(self, item):
        try:
            self.page.open_path(item)
        except Exception as ex: self.page.main.error(str(ex))
        self.page.refresh()

    def rename(self):
        item = self.selected()
        if not item: return
        name = self.name.text().strip()
        if name:
            meta = PUB.load(self.page.pdir)
            for x in meta.get('reaction_paths', []):
                if x['uid'] == item['uid']: x['name'] = name.strip()
            if self.page.path_workspace and self.page.path_workspace.item['uid'] == item['uid']:
                self.page.path_workspace.item['name'] = name
            PUB.save(self.page.pdir, meta); self.page.refresh()

    def remove(self):
        item = self.selected()
        if not item: return
        if self.page.path_workspace and self.page.path_workspace.item['uid'] == item['uid']:
            if not self.page.close_path(): return
        set_removed(self.page.pdir, item['uid'], True)
        self.page.refresh()

    def restore(self):
        uid = self.removed.currentData()
        if uid:
            set_removed(self.page.pdir, uid, False)
            self.page.refresh()


def si_blocks(main, pdir):
    """Called once per publication, not once per compound."""
    from elucida.si import lines as SI
    meta = PUB.load(pdir)
    opts = meta.get('reaction_paths_si') or {}
    if opts.get('include') is False: return []
    blocks = []
    for item in meta.get('reaction_paths', []):
        host = PathHost(main, pdir, item, readonly=True)
        try:
            from elucida.app.path_composition import composition_blocks
            try:
                images = composition_blocks(host)
                if images is None:
                    images = host.tab.pages.si_figures(PRJ.work_dir(host.project_dir, 'dft'), item['name'])
            except Exception as ex:                        # die Meldung muss den Pfad nennen
                raise ValueError(f"{item['name']}: {ex}") from ex
            if images: blocks += [('heading', item['name'])] + images
        finally:
            host.dispose()
    return SI.two_per_page(blocks)
