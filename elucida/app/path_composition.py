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
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QDialog, QMenu, QLineEdit, QLabel, QComboBox, QStackedWidget, QDialogButtonBox
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
            F, notes = DL.build_levels(pg, fig, layout)
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
        if mode == 'levels' and not frame:
            for spine in F.ax.spines.values(): spine.set_visible(False)
            F.ax.set_yticks([])
            F.ax.set_xlabel('')
            label = F.ax.get_ylabel()
            F.ax.set_ylabel('')
            F.ax.annotate('', xy=(-.025, .87), xytext=(-.025, .56), xycoords='axes fraction',
                          arrowprops=dict(arrowstyle='-|>', color='black', lw=1.2), annotation_clip=False)
            F.ax.text(-.04, .90, label, transform=F.ax.transAxes, ha='left', va='bottom', fontsize=9)
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

    def open_path(self, path):
        loaded = super().open_path(path)
        if loaded and self.ready and self.path:
            self.command('zoom_fit')
        return loaded


class CompositionEditor(QWidget):
    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.host = host
        self.view_editor = None
        self.diagram_editor = None
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 6, 4, 4); v.setSpacing(6)
        # Eine Zeile: Höhe gehört dem Canvas (Nutzerwunsch), Hilfetext als Tooltip.
        row = QHBoxLayout(); v.addLayout(row)
        self.actions = []
        insert = QPushButton(T('rp_insert')); insert.setIcon(STYLE.icon('add'))
        menu = QMenu(insert)
        menu.addAction(T('rp_insert_diagram'), self.insert_profile)
        menu.addAction(T('rp_insert_orbital'), self.add_orbital)
        insert.setMenu(menu); row.addWidget(insert); self.actions.append(insert)
        for key, fn, icon in [('rp_update_diagrams', self.update_profiles, 'reset'),
                              ('rp_edit_selected', self.edit_selected, 'open')]:
            button = QPushButton(T(key)); button.setIcon(STYLE.icon(icon))
            button.clicked.connect(fn); row.addWidget(button); self.actions.append(button)
        label = QLabel(T('rp_view_source')); label.setProperty('formlabel', True); row.addWidget(label)
        self.sources = QComboBox(); self.sources.setMinimumWidth(100)
        self.sources.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        row.addWidget(self.sources, 1)
        self.frame = QCheckBox(T('rp_show_diagram_frame')); row.addWidget(self.frame)
        insert.setToolTip(T('rp_composition_hint'))
        self.editor = CompositionDrawingEditor(self, scheme_actions=False)
        self.editor.set_canvas_dark(host.canvas_is_dark())
        self.editor.asset_edit_requested.connect(self.edit_asset)
        self.views = QStackedWidget(); self.views.addWidget(self.editor); v.addWidget(self.views, 1)
        row = QHBoxLayout(); row.addWidget(QLabel(T('rp_composition_caption')))
        self.caption = QLineEdit(host.tab.pages.prof.get('composition_caption', ''))
        self.caption.setPlaceholderText(T('rp_caption_auto'))
        self.caption.editingFinished.connect(self.save_caption); row.addWidget(self.caption, 1); v.addLayout(row)
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
                payload, record = profile_asset(self.host, rec['mode'], rec.get('frame', False), rec.get('layout'))
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
        if self.view_editor or self.diagram_editor: return
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
        if self.view_editor or self.diagram_editor: return
        from elucida.tabs.diagram_layout import DiagramLayoutEditor
        self.diagram_editor = DiagramLayoutEditor(self.host, rec['mode'], rec.get('layout', {}), rec.get('frame', False))
        self.diagram_target = target
        self.diagram_editor.finished.connect(self.finish_diagram)
        self.views.addWidget(self.diagram_editor); self.views.setCurrentWidget(self.diagram_editor)
        for button in self.actions: button.setEnabled(False)

    def finish_diagram(self, accept):
        panel = self.diagram_editor
        if panel is None: return True
        if accept:
            if not panel.buttons.button(QDialogButtonBox.Ok).isEnabled(): return False
            try:
                payload, rec = profile_asset(self.host, panel.mode, panel.frame.isChecked(), panel.data)
                if self.put(payload, rec, self.diagram_target) is None: return False
            except Exception as ex:
                panel.error.setText(str(ex)); return False
        self.diagram_editor = None
        self.views.setCurrentWidget(self.editor); self.views.removeWidget(panel); panel.deleteLater()
        for button in self.actions: button.setEnabled(True)
        return True

    def save(self):
        if not self.finish_diagram(True): return False
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
