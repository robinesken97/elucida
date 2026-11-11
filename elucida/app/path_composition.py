"""Free Octet composition of data-backed energy diagrams and independent orbital views."""
from copy import deepcopy
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import uuid
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QDialog, QSizePolicy, QMenu, QLineEdit, QLabel, QComboBox, QStackedWidget, QDialogButtonBox
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image

from elucida.app import project as PRJ, style as STYLE
from elucida.app.drawing_editor import DrawingEditor, fingerprint, asset_references
from elucida.app.i18n import T
from elucida.tabs import profile_orbitals as PO


def profile_stamp(host, mode):
    """Hash plotted values/settings, independent of absolute paths after project copy."""
    pg = host.tab.pages
    if mode == 'levels':
        rows, paths, notes = pg.levels_spec()
        data = [{k: r[k] for k in ('uid', 'label', 'value', 'step', 'paths')} for r in rows]
        caption = pg.levels_caption('')
    else:
        curves, notes = pg.irc_data()
        data = [dict(uid=c['uid'], label=c['label'], s=c['s'].tolist(), E=c['E'].tolist(),
                     ts=c['ts'], method=c['method'], cols={k: v.tolist() for k,v in c['cols'].items()}) for c in curves]
        caption = pg.irc_caption('')
    if not data:
        raise ValueError(T('dft_prof_empty'))
    # Missing/mixed calculations must never silently yield a partial final diagram.
    if notes:
        raise ValueError('\n'.join(notes))
    options = {k: pg.prof.get(k) for k in ('y', 'irc_x', 'irc_ref', 'colors', 'size_cm')}
    options.update({k: pg.prof[k] for k in ('edges', 'layout', 'layout_irc') if pg.prof.get(k)})   # nur wenn gesetzt:
    # alte Stempel bleiben gültig
    # Daten, nicht Aussehen: das globale Textformat darf die Gesamt-SI nicht als „veraltet“ stoppen.
    raw = json.dumps([data, caption, options], sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def profile_figure(host, mode, frame, layout, fig):
    pg = host.tab.pages
    # Images are placed freely in Octet; generate this object from the energy data only.
    old = host.tab.st['profile']
    clean = deepcopy(old)
    clean['annotations'] = []
    for spec in clean.get('species', {}).values():
        spec.pop('structure', None)
    host.tab.st['profile'] = clean
    try:
        from elucida.tabs import diagram_layout as DL
        if mode == 'levels':
            F, notes = DL.build_levels(pg, fig, dict(layout or {}, frame=bool(frame)))
        else:
            F, notes = pg.build(fig, mode)
            if F:
                for line in F.ax.lines:
                    if line.get_linestyle() != 'None':
                        line.set_linewidth(DL.number(layout, 'line_width', 1.2, .1, 10))
                        line.set_color(layout.get('color', 'black'))
                        # IRC: die Kurve sind die Daten, „keine Linie“ gilt nur für Verbinder
                        line.set_linestyle(layout.get('connector_style', '-').replace('none', '-'))
                fs = DL.number(layout, 'font_size', F.cfg['labels']['font_size'], 4, 40)
                for label in [*F.ax.texts, F.ax.xaxis.label, F.ax.yaxis.label,
                              *F.ax.get_xticklabels(), *F.ax.get_yticklabels()]:
                    label.set_fontsize(fs)
        if F is None or notes:
            raise ValueError('\n'.join(notes) or T('dft_prof_empty'))
        return F, notes
    finally:
        host.tab.st['profile'] = old


def profile_asset(host, mode, frame=False, layout=None):
    pg = host.tab.pages
    stamp = profile_stamp(host, mode)
    layout = deepcopy(layout or {})
    fig = Figure(); FigureCanvasAgg(fig)
    F, _ = profile_figure(host, mode, frame, layout, fig)
    base = PRJ.work_dir(host.project_dir, 'composition') / ('profile_' + uuid.uuid4().hex)
    F.cfg.update(output=str(base.with_suffix('.svg')), extra_formats=['png'], dpi=180)
    F.export()
    width, height = F.fig.get_size_inches() * 72
    payload = dict(kind='profile', svg=base.with_suffix('.svg').read_text(encoding='utf-8'),
                   png=base.with_suffix('.png').read_bytes().hex(), width=float(width), height=float(height))
    record = dict(kind='profile', mode=mode, frame=frame, layout=layout, stamp=stamp,
                  caption=pg.levels_caption(host.item['name']) if mode == 'levels' else pg.irc_caption(host.item['name']))
    return payload, record


def orbital_asset(host, view):
    rgba = PO.asset(host.tab, view)['rgba']
    stream = io.BytesIO(); Image.fromarray(rgba).save(stream, format='PNG')
    return (dict(kind='orbital', png=stream.getvalue().hex(), width=140., height=140.*rgba.shape[0]/rgba.shape[1]),
            dict(kind='orbital', orbital=deepcopy(view)))


def composition_metadata(host):
    path = host.tab.pages.prof.get('composition')
    if not path: return None
    p = Path(path)
    meta_path = p.with_suffix('.elucida-drawing.json')
    if not p.exists() or not meta_path.exists(): return None  # not saved yet
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta.get('source_sha') != fingerprint(p) or not p.with_suffix('.svg').is_file():
        raise ValueError(T('rp_composition_reopen'))
    meta['assets'] = asset_references(meta.get('assets', []))
    for ref in meta['assets']:
        record = host.tab.pages.prof.get('composition_assets', {}).get(ref['key'])
        if not record or record.get('kind') != ref['kind']:
            raise ValueError(T('rp_composition_missing_source'))
        if record['kind'] == 'profile' and record['stamp'] != profile_stamp(host, record['mode']):
            raise ValueError(T('rp_composition_stale'))
    return p, meta


def composition_blocks(host):
    info = composition_metadata(host)
    if not info: return None
    from elucida.tabs.other import word_image
    p, meta = info
    # A deliberately cleared canvas must not resurrect the old automatic plot.
    if not any(el.tag in ('n', 't', 'arrow', 'graphic', 'embeddedobject') for el in ET.parse(p).iter()): return []
    captions = []
    for ref in meta.get('assets', []):
        rec = host.tab.pages.prof['composition_assets'][ref['key']]
        if rec.get('caption') and rec['caption'] not in captions: captions.append(rec['caption'])
    own = host.tab.pages.prof.get('composition_caption', '').strip()
    caption = html.escape(own) if own else ' '.join(captions) or html.escape(host.item['name'])
    if any(host.tab.pages.prof['composition_assets'][r['key']].get('layout', {}).get('mode') == 'schematic'
           and host.tab.pages.prof['composition_assets'][r['key']].get('mode') == 'levels' for r in meta.get('assets', [])):
        from elucida.tabs.diagram_layout import SCHEMATIC_NOTE
        caption += ' ' + SCHEMATIC_NOTE
    figure = word_image(p.with_suffix('.svg'), PRJ.work_dir(host.project_dir, 'composition'), 'SI_composition')
    # Keep vector Word graphics and portable editable drawings side by side.
    cdx = p.with_suffix('.cdx')
    return [(*figure, str(cdx) if cdx.exists() else None), ('figcap', caption)]


class CompositionDrawingEditor(DrawingEditor):
    """Fit the entire composition on load, including plots and orbital images."""
    fit_view = True


class CompositionEditor(QWidget):
    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.host = host
        self.workspace = parent                             # PathWorkspace: Seite „Rechendaten“ mit dem Energiediagramm
        self.view_editor = None
        from elucida.tabs.base import PAGE_INSET
        v = QVBoxLayout(self)                               # Seite wie rechts in den Tabs: Karte mit Zeichenfläche, darunter die Unterschrift
        v.setContentsMargins(*PAGE_INSET); v.setSpacing(STYLE.FORM_GAP)
        # Werkzeuge rechts neben den Reitern (PathWorkspace): die Höhe gehört dem Canvas (Nutzerwunsch), Hilfetext als Tooltip.
        self.tool_row = QWidget()
        row = QHBoxLayout(self.tool_row); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(4)
        self.actions = []
        insert = QPushButton(T('rp_insert'), objectName='ghost')
        menu = QMenu(insert)
        menu.addAction(T('rp_insert_diagram'), self.insert_profile)
        menu.addAction(T('rp_insert_orbital'), self.add_orbital)
        insert.setMenu(menu); row.addWidget(insert); self.actions.append(insert)
        for key, fn, tip in [('rp_update_diagrams', self.update_profiles, None),
                             ('rp_edit_figure', self.edit_selected, 'rp_edit_selected')]:
            button = QPushButton(T(key), objectName='ghost')
            if tip: button.setToolTip(T(tip))
            button.clicked.connect(fn); row.addWidget(button); self.actions.append(button)
        # 3D-Quelle als Menü statt Feld fester Breite (Entwurf): die Auswahl gilt für „3D-/Orbitalansicht einfügen“
        self.sources = QComboBox(self); self.sources.hide()
        source = QPushButton(T('rp_view_source'), objectName='ghost'); source.setMenu(QMenu(source))
        source.menu().aboutToShow.connect(self.fill_sources); row.addWidget(source)
        insert.setToolTip(T('rp_composition_hint'))
        self.editor = CompositionDrawingEditor(self, scheme_actions=False)
        self.editor.set_canvas_dark(host.canvas_is_dark())
        self.editor.action_bar.hide()                       # Octet-Befehle im Menü „⋯“ der Werkzeugzeile
        menu_ = self.editor.more_menu
        first = menu_.actions()[0]
        for key_, cmd in (('draw_check', 'check_structure'), ('draw_cleanup', 'clean_up'), ('draw_name', 'name_to_structure')):
            act = menu_.addAction(T(key_), lambda c=cmd: self.editor.command(c))
            menu_.removeAction(act)
            menu_.insertAction(first, act)
        self.frame = menu_.addAction(T('rp_show_diagram_frame')); self.frame.setCheckable(True)
        menu_.removeAction(self.frame); menu_.insertAction(first, self.frame)
        menu_.insertSeparator(first)
        more_ = QPushButton('⋯', objectName='ghost'); more_.setMenu(menu_); row.addWidget(more_)
        self.editor.asset_edit_requested.connect(self.edit_asset)
        # Meldungen als Einblendung (rules/ui.md), keine ständige Zeile unter dem Canvas
        self.editor.status.hide(); self.editor.status.changed.connect(self.notify)
        self.views = QStackedWidget(); self.views.addWidget(self.editor)
        card = QFrame(objectName='card')
        cv = QVBoxLayout(card); cv.setContentsMargins(*[STYLE.FORM_GAP] * 4); cv.addWidget(self.views)
        v.addWidget(card, 1)
        # SI-Unterschrift: Zeile an den Kanten der Karte, Beschriftung und Feld wie in den Formularen
        row = QHBoxLayout(); row.setSpacing(STYLE.FORM_GAP); v.addLayout(row)
        label = QLabel(T('rp_composition_caption')); label.setProperty('formlabel', True); row.addWidget(label)
        self.caption = QLineEdit(host.tab.pages.prof.get('composition_caption', ''))
        self.caption.setPlaceholderText(T('rp_caption_auto'))
        # so hoch wie die Felder der Spalten; über die Zeile, weil das Stylesheet die Mindesthöhe des Felds selbst setzt
        row.addStrut(STYLE.CONTROL_H); self.caption.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.caption.editingFinished.connect(self.save_caption); row.addWidget(self.caption, 1)
        label.setBuddy(self.caption)
        path = host.tab.pages.prof.get('composition')
        if not path:
            path = str(host.project_dir / PRJ.STRUCTURES / 'reaction_path.cdxml')
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            # Do not overwrite an existing canvas after an interrupted state save.
            if not Path(path).exists(): Path(path).write_text(PRJ.EMPTY_CDXML, encoding='utf-8')
            host.tab.pages.prof['composition'] = path
            host.save()
        self.editor.open_path(path)
        self.refresh_sources()

    def notify(self, text):
        # Gespeichert/ungespeichert/speichert wechseln ständig (Autosave): nur Hinweise und Fehler einblenden
        if text and text not in (self.editor.saved_message, T('draw_unsaved'), T('draw_saving')):
            self.host.owner.statusBar().showMessage(text, 8000)

    def fill_sources(self):
        self.refresh_sources()
        menu = self.sender(); menu.clear()
        for i in range(self.sources.count()):
            act = menu.addAction(self.sources.itemText(i), lambda i=i: self.sources.setCurrentIndex(i))
            act.setCheckable(True); act.setChecked(i == self.sources.currentIndex())
        if not self.sources.count():
            menu.addAction(T('rp_load_view_source')).setEnabled(False)

    def save_caption(self):
        self.host.tab.pages.prof['composition_caption'] = self.caption.text()
        self.host.save()

    def put(self, payload, record, target=None):
        key = uuid.uuid4().hex
        # Immutable revisions let Octet undo restore the previous image AND settings.
        self.host.tab.pages.prof.setdefault('composition_assets', {})[key] = record
        if not self.host.save(): return
        payload['key'] = key
        shape = self.editor._js(f'window.elucida.putAsset({json.dumps(payload)}, {json.dumps(target) if target is not None else "undefined"})')
        if not self.editor.save_sync(): return
        if target is None: self.editor.command('zoom_fit')
        return shape

    def require_ready(self):
        if not self.editor.ready or not self.editor.path:
            raise ValueError(T('draw_loading'))

    def insert_profile(self):
        try:
            self.require_ready()
            payload, record = profile_asset(self.host, self.host.tab.pages.prof['mode'], self.frame.isChecked())
            self.put(payload, record)
        except Exception as ex: self.host.error(str(ex))

    def update_profiles(self):
        try:
            self.require_ready()
            for ref in self.editor._js('window.elucida.assets()'):
                if ref['kind'] != 'profile': continue
                rec = self.host.tab.pages.prof.get('composition_assets', {}).get(ref['key'])
                if not rec: raise ValueError(T('rp_composition_missing_source'))
                payload, record = profile_asset(self.host, rec['mode'], *self.host.tab.pages.style_of(rec['mode'], rec))
                self.put(payload, record, ref['shapeId'])
        except Exception as ex: self.host.error(str(ex))

    def add_orbital(self):
        try:
            self.require_ready()
            self.refresh_sources()
            source = self.sources.currentData()
            if not source: raise ValueError(T('rp_load_view_source'))
            uid, k = source
            e = next(e for e in self.host.tab.entries() if e['uid'] == uid)
            self.edit_view(PO.snapshot(self.host.tab, e, k))
        except Exception as ex: self.host.error(str(ex))

    def refresh_sources(self):
        selected = self.sources.currentData()
        self.sources.clear()
        for e in self.host.tab.entries():
            self.sources.addItem(f"{e.get('name', '')} · {T('rp_geometry_only')}", [e['uid'], None])
            for k, orb in enumerate(e.get('orbitals', [])):
                self.sources.addItem(f"{e.get('name', '')} · {self.host.tab.orb_name(e, orb)}", [e['uid'], k])
        idx = self.sources.findData(selected)
        if idx >= 0: self.sources.setCurrentIndex(idx)

    def edit_view(self, view, target=None):
        if self.view_editor: return
        dialog = PO.OrbitalViewDialog(self.host.tab, view)
        # Reuse the existing view controls as an embedded page, never as a window.
        dialog.setParent(self.views); dialog.setWindowFlags(Qt.Widget)
        self.view_editor, self.view_target = dialog, target
        dialog.buttons.button(QDialogButtonBox.Ok).setText(T('rp_apply_view'))
        dialog.finished.connect(self.finish_view)
        self.views.addWidget(dialog); self.views.setCurrentWidget(dialog)
        for button in self.actions: button.setEnabled(False)

    def finish_view(self, result):
        dialog = self.view_editor
        if dialog is None: return True
        if result == QDialog.Accepted:
            if not dialog.buttons.button(QDialogButtonBox.Ok).isEnabled(): return False
            try:
                if self.put(*orbital_asset(self.host, dialog.data), target=self.view_target) is None: return False
            except Exception as ex:
                dialog.error.setText(str(ex)); dialog.show(); return False
        if dialog.dragger: dialog.dragger.disconnect()
        self.view_editor = None
        self.views.setCurrentWidget(self.editor); self.views.removeWidget(dialog); dialog.deleteLater()
        for button in self.actions: button.setEnabled(True)
        return True

    def edit_selected(self):
        try:
            self.require_ready()
            ref = self.editor._js('window.elucida.selectedAsset()')
            if not ref: raise ValueError(T('rp_select_figure'))
            self.edit_asset(ref['key'], ref['shapeId'])
        except Exception as ex: self.host.error(str(ex))

    def edit_asset(self, key, shape_id):
        try:
            rec = self.host.tab.pages.prof.get('composition_assets', {}).get(key)
            if not rec: raise ValueError(T('rp_composition_missing_source'))
            if rec['kind'] == 'orbital': self.edit_view(rec['orbital'], shape_id)
            else:
                self.edit_diagram(rec, shape_id)
        except Exception as ex: self.host.error(str(ex))

    def edit_diagram(self, rec, target):
        """Lage, Breite und Farbe der Plateaus und der Stil gehören zum Profil: auf dessen Seite einstellen, dann
        „Profile aktualisieren“ (früher eigener Layout-Editor mit Übernehmen/Abbrechen)."""
        if self.view_editor: return
        self.workspace.tabs.setCurrentWidget(self.workspace.calc_page)

    def save(self):
        if not self.finish_view(QDialog.Accepted): return False
        self.save_caption()
        return not self.editor.dirty or self.editor.save_sync()

    def export(self):
        if not self.save(): return []
        info = composition_metadata(self.host)
        if not info: raise ValueError(T('dft_prof_empty'))
        import pymupdf
        p, _ = info
        from elucida.core.uvvis import safe_name
        base = self.host.project_dir / PRJ.FIGURES / safe_name(self.host.item['name'])
        base.parent.mkdir(parents=True, exist_ok=True)
        files = []
        for ext in ('.svg', '.cdxml', '.cdx'):
            target = base.with_suffix(ext); shutil.copy2(p.with_suffix(ext), target); files.append(target)
        with pymupdf.open(str(p.with_suffix('.svg'))) as drawing:
            drawing[0].get_pixmap(dpi=300, alpha=False).save(str(base.with_suffix('.png')))
            base.with_suffix('.pdf').write_bytes(drawing.convert_to_pdf())
        files += [base.with_suffix('.png'), base.with_suffix('.pdf')]
        return files
